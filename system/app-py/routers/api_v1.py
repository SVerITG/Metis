"""api_v1.py — a JSON API over the Metis brain, for clients that are not Claude.

WHY (Keystone P5.1)
    The MCP server is stdio and request/response: it can only ever serve a Claude
    client. PowerPoint, Excel, a Shiny app or a script cannot reach it at all. The
    dashboard, though, is already an always-on local HTTP service over the same
    SQLite brain — but almost every endpoint returns HTML partials for HTMX, which
    is unusable as an API.

    So this is the attach point for everything non-Claude: a small, versioned,
    JSON-only surface over the same data.

SECURITY — why this needs its own gate
    The dashboard's OriginCheckMiddleware protects mutating requests from other
    websites by rejecting non-localhost Origins. That is right for a browser, and
    NOT ENOUGH here, for two reasons:

      · An Office add-in runs in a webview with its OWN origin, so it would be
        rejected by exactly the rule that protects the dashboard.
      · A GET carries no Origin check at all, and these endpoints read the
        researcher's library, notes and projects. Any local process — or any web
        page doing a no-cors fetch to 127.0.0.1 — could read them.

    Therefore every /api/v1 route requires a bearer token, generated once into
    `system/config/api-token.txt` (gitignored, 0600). Localhost is treated as a
    shared bus, not a trusted boundary — the same reasoning the Data Guardian
    applies to files.

WHAT IT DELIBERATELY DOES NOT DO
    No write endpoints beyond capture, and no tool execution. An HTTP surface that
    can run arbitrary Metis tools is a remote-code path into the researcher's
    machine; capture is additive and harmless, everything else is read-only.
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from db import db_query, db_scalar, db_execute

router = APIRouter(prefix="/api/v1")

API_VERSION = "1.0.0"


def _token_path() -> Path:
    root = Path(os.environ.get("METIS_RC_ROOT", "."))
    return root / "system" / "config" / "api-token.txt"


def api_token() -> str:
    """The local API token, created on first use.

    Generated rather than configured: a default or blank token is one nobody
    changes, and this endpoint reads the researcher's library.
    """
    p = _token_path()
    try:
        if p.is_file():
            tok = p.read_text(encoding="utf-8").strip()
            if tok:
                return tok
        tok = secrets.token_urlsafe(32)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(tok, encoding="utf-8")
        try:
            os.chmod(p, 0o600)
        except Exception:
            pass          # Windows / DrvFs may not support it; the token is still local
        return tok
    except Exception:
        # Never fabricate a token that would silently accept everything.
        return ""


def _require(authorization: str | None) -> None:
    expected = api_token()
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not expected or not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="A valid API token is required.")


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get("/health")
async def v1_health():
    """Liveness + version. The ONLY unauthenticated route, so a client can tell
    Metis is running before it has a token."""
    return {"ok": True, "service": "metis", "api_version": API_VERSION}


@router.get("/projects")
async def v1_projects(authorization: str | None = Header(None)):
    _require(authorization)
    rows = db_query(
        "SELECT project_id, title, status, next_step FROM projects "
        "WHERE COALESCE(status,'active') != 'archived' ORDER BY title"
    ) or []
    return {"projects": [dict(r) for r in rows]}


@router.get("/tasks")
async def v1_tasks(status: str = "open", limit: int = 50,
                   authorization: str | None = Header(None)):
    _require(authorization)
    rows = db_query(
        "SELECT task_id, title, status, project_id, due_date FROM tasks "
        "WHERE (?='' OR status=?) ORDER BY COALESCE(due_date,'9999') LIMIT ?",
        (status, status, min(limit, 200)),
    ) or []
    return {"tasks": [dict(r) for r in rows]}


@router.get("/search")
async def v1_search(q: str, limit: int = 8, authorization: str | None = Header(None)):
    """Search the researcher's indexed library and return cited passages.

    This is the endpoint that makes an Office add-in worth having: a slide or a
    sheet can be grounded in the researcher's own sources, with citations.
    """
    _require(authorization)
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required")
    try:
        import asyncio
        from metis_mcp.tools.knowledge_db import search_pdf_knowledge  # type: ignore

        res = await search_pdf_knowledge(q, top_k=min(limit, 20))
        text = res[0].text if res else ""
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"search unavailable: {exc}")
    return {"query": q, "results_markdown": text}


@router.get("/library")
async def v1_library(q: str = "", limit: int = 25,
                     authorization: str | None = Header(None)):
    _require(authorization)
    if q:
        rows = db_query(
            "SELECT id, title, authors, year, journal, doi FROM literature_metadata "
            "WHERE title LIKE ? OR authors LIKE ? ORDER BY year DESC LIMIT ?",
            (f"%{q}%", f"%{q}%", min(limit, 100)),
        ) or []
    else:
        rows = db_query(
            "SELECT id, title, authors, year, journal, doi FROM literature_metadata "
            "ORDER BY created_at DESC LIMIT ?", (min(limit, 100),),
        ) or []
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.post("/capture")
async def v1_capture(request: Request, authorization: str | None = Header(None)):
    """Capture an idea or note from another application.

    The only write. Additive and harmless by design — see the module docstring on
    why no tool-execution endpoint exists.
    """
    _require(authorization)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="expected a JSON body")
    text = (body.get("text") or "").strip()
    kind = (body.get("kind") or "idea").strip().lower()
    source = (body.get("source") or "api").strip()[:60]
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if kind not in ("idea", "note"):
        raise HTTPException(status_code=400, detail="kind must be 'idea' or 'note'")

    import datetime
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        if kind == "note":
            db_execute(
                "INSERT INTO personal_notes (note_id, content, title, tags, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (f"api-{secrets.token_hex(6)}", text, "", source, now, now),
            )
        else:
            db_execute("INSERT INTO ideas (text, idea_type, created_at) VALUES (?,?,?)",
                       (text, "idea", now))
        # Vector-index it so an idea captured from Excel is as findable as one
        # typed into Metis — the same reasoning as Keystone P3.10.
        try:
            from metis_mcp.tools.ideas import _embed_episodic  # type: ignore
            _embed_episodic(text, kind)
        except Exception:
            pass
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"could not save: {exc}")
    return {"ok": True, "kind": kind, "saved_at": now}


# ── CORS for Office add-ins (P5.4) ───────────────────────────────────────────
# An add-in taskpane runs in a webview with an Office origin, so a browser
# preflights every call. Without an OPTIONS handler and the matching headers the
# request never reaches the routes above — and the add-in reports nothing more
# useful than "failed to fetch".
#
# Scoped to the Office hosts only, and it grants nothing on its own: every route
# still demands the bearer token. CORS decides who may ASK; the token decides who
# may READ.
_ADDIN_ORIGINS = (
    "https://localhost", "https://127.0.0.1",
    "https://appsforoffice.microsoft.com",
    "https://excel.officeapps.live.com",
    "https://powerpoint.officeapps.live.com",
    "https://word.officeapps.live.com",
)


def _cors_headers(origin: str) -> dict:
    if not origin or not origin.startswith(_ADDIN_ORIGINS):
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Max-Age": "600",
    }


@router.options("/{rest_of_path:path}")
async def v1_preflight(rest_of_path: str, request: Request):
    return JSONResponse({}, headers=_cors_headers(request.headers.get("origin", "")))
