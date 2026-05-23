"""
Model registry loader for the Metis MCP server.

Mirrors `system/app-py/models.py` so MCP tools can also resolve Claude model
IDs from `system/config/models.yaml` instead of hardcoding them.

Single source of truth for both the dashboard and the MCP server.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

_cache: dict[str, tuple[str, float]] = {}
_config: dict[str, Any] | None = None


def _config_path() -> Path:
    rc = os.environ.get("METIS_RC_ROOT", "")
    if rc:
        p = Path(rc) / "system" / "config" / "models.yaml"
        if p.exists():
            return p
    # Repo-relative fallback: this file at system/mcp-server/src/metis_mcp/models.py
    return Path(__file__).parent.parent.parent.parent / "config" / "models.yaml"


def _load_config() -> dict[str, Any]:
    global _config
    if _config is not None:
        return _config
    try:
        import yaml
        p = _config_path()
        _config = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        _config = {}
    return _config


def _resolve_alias(name: str) -> str:
    aliases = (_load_config().get("aliases") or {})
    return aliases.get(name, name)


def _chain_for(role: str) -> list[str]:
    roles = (_load_config().get("roles") or {})
    entry = roles.get(role)
    if not entry:
        return ["claude-sonnet-4-6", "claude-3-5-sonnet-latest"]
    chain: list[str] = []
    if entry.get("primary"):
        chain.append(entry["primary"])
    chain.extend(entry.get("fallback", []) or [])
    return chain or ["claude-sonnet-4-6"]


def model_for(name: str) -> str:
    """Return the model ID for an alias or role."""
    role = _resolve_alias(name)
    cached = _cache.get(role)
    if cached and cached[1] > time.time():
        return cached[0]
    chain = _chain_for(role)
    picked = chain[0]
    ttl = ((_load_config().get("availability") or {}).get("cache_minutes", 60)) * 60
    _cache[role] = (picked, time.time() + ttl)
    return picked


def reload_config() -> None:
    global _config
    _config = None
    _cache.clear()
