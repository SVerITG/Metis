"""DHIS2 live API connector — authenticated queries to a configured DHIS2 instance.

Reads connection details from system/.env or environment variables:
  DHIS2_BASE_URL  — e.g. https://dhis.example.org
  DHIS2_USERNAME  — API user (read-only recommended)
  DHIS2_PASSWORD  — API password

Tools exposed:
  dhis2_query(endpoint, params, method) — authenticated DHIS2 API call
  dhis2_metadata(resource, filters)     — convenience wrapper for metadata queries
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths


def _load_dhis2_config() -> tuple[str, str, str]:
    """Return (base_url, username, password) from env or system/.env."""
    env_file = paths.root / "system" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    base_url = os.environ.get("DHIS2_BASE_URL", "").rstrip("/")
    username = os.environ.get("DHIS2_USERNAME", "")
    password = os.environ.get("DHIS2_PASSWORD", "")
    return base_url, username, password


def _check_config() -> str | None:
    """Return an error message if DHIS2 is not configured, else None."""
    base_url, username, password = _load_dhis2_config()
    if not base_url:
        return (
            "DHIS2_BASE_URL not set. Add to system/.env:\n"
            "  DHIS2_BASE_URL=https://your-dhis2-server.org\n"
            "  DHIS2_USERNAME=api_user\n"
            "  DHIS2_PASSWORD=your_password"
        )
    if not username or not password:
        return "DHIS2_USERNAME and DHIS2_PASSWORD must both be set in system/.env."
    return None


@app.tool()
async def dhis2_query(
    endpoint: str,
    params: dict[str, Any] | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> list[TextContent]:
    """Make an authenticated API call to the configured DHIS2 instance.

    Returns the JSON response as formatted text. Use for live metadata
    validation, data element lookup, indicator queries, and data quality checks.

    Args:
        endpoint: API path relative to /api/, e.g. "dataElements" or "organisationUnits.json".
                  If it does not start with "/api/", that prefix is added automatically.
        params:   Query parameters as a dict, e.g. {"fields": "id,name", "paging": "false"}.
        method:   HTTP method — "GET" (default), "POST", or "PUT".
        body:     Request body for POST/PUT (serialised to JSON).

    Examples:
        dhis2_query("dataElements", {"fields": "id,name,valueType", "paging": "false"})
        dhis2_query("system/info")
        dhis2_query("organisationUnits", {"filter": "level:eq:2", "fields": "id,name,level"})
    """
    err = _check_config()
    if err:
        return [TextContent(type="text", text=err)]

    try:
        import httpx
    except ImportError:
        return [TextContent(type="text", text="httpx not installed. Run: pip install httpx")]

    base_url, username, password = _load_dhis2_config()

    # Normalise endpoint
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    if not endpoint.startswith("/api/"):
        endpoint = "/api" + endpoint

    url = base_url + endpoint
    auth = (username, password)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            if method.upper() == "GET":
                resp = await client.get(url, params=params or {}, auth=auth, headers=headers)
            elif method.upper() == "POST":
                resp = await client.post(url, params=params or {}, json=body, auth=auth, headers=headers)
            elif method.upper() == "PUT":
                resp = await client.put(url, params=params or {}, json=body, auth=auth, headers=headers)
            else:
                return [TextContent(type="text", text=f"Unsupported method: {method}")]

        if resp.status_code == 401:
            return [TextContent(type="text", text="DHIS2 authentication failed. Check DHIS2_USERNAME and DHIS2_PASSWORD in system/.env.")]
        if resp.status_code == 403:
            return [TextContent(type="text", text=f"Access denied to {endpoint}. The API user may lack required permissions.")]
        if resp.status_code >= 400:
            return [TextContent(type="text", text=f"DHIS2 returned HTTP {resp.status_code}:\n{resp.text[:500]}")]

        try:
            data = resp.json()
        except Exception:
            return [TextContent(type="text", text=resp.text[:2000])]

        # Summarise paged responses
        total = data.get("pager", {}).get("total")
        page_count = data.get("pager", {}).get("pageCount")
        summary = ""
        if total is not None:
            summary = f"Total: {total} records"
            if page_count and page_count > 1:
                summary += f" across {page_count} pages (showing page 1)"
            summary += "\n\n"

        return [TextContent(type="text", text=summary + json.dumps(data, indent=2, ensure_ascii=False)[:4000])]

    except httpx.ConnectError:
        return [TextContent(type="text", text=f"Cannot connect to DHIS2 at {base_url}. Check DHIS2_BASE_URL and network connectivity.")]
    except httpx.TimeoutException:
        return [TextContent(type="text", text=f"Request to {url} timed out after 30 seconds.")]
    except Exception as exc:
        return [TextContent(type="text", text=f"DHIS2 query failed: {exc}")]


@app.tool()
async def dhis2_metadata(
    resource: str,
    filters: list[str] | None = None,
    fields: str = "id,name,shortName",
    paging: bool = False,
) -> list[TextContent]:
    """Query DHIS2 metadata with a simplified interface.

    Convenience wrapper around dhis2_query() for common metadata lookups.

    Args:
        resource: Metadata resource type — e.g. "dataElements", "indicators",
                  "organisationUnits", "programs", "dataSets", "trackedEntityTypes".
        filters:  Filter expressions in DHIS2 format, e.g. ["name:ilike:malaria", "valueType:eq:NUMBER"].
        fields:   Comma-separated field list (default: "id,name,shortName").
        paging:   Set True to get only the first page (faster for large resources).

    Examples:
        dhis2_metadata("dataElements", ["name:ilike:HAT", "valueType:eq:INTEGER"])
        dhis2_metadata("programs", fields="id,name,programType,trackedEntityType[id,name]")
        dhis2_metadata("organisationUnits", ["level:eq:3"], fields="id,name,level,parent[id,name]")
    """
    params: dict[str, Any] = {
        "fields": fields,
        "paging": str(paging).lower(),
    }
    if filters:
        params["filter"] = filters

    return await dhis2_query(resource, params=params)
