"""connections.py — ambient cross-pollination, surfaced everywhere.

THE PROBLEM (surface review, 2026-07-14)
    The README's central promise is cross-pollination: "it connects everything you
    know… surfaces links without you searching." The engine for this
    (_cross_pollinate_core: hybrid vector + keyword, RRF-merged) is genuinely good
    and, since today's embedding backfill, actually works over the whole corpus.

    But it was invoked in exactly ONE place — the capture modal. So the flagship
    feature of the product was invisible on every surface where it would matter.
    You had to open a Thinking tab (8 ideas) to see connections, instead of the
    connection appearing next to the paper / task / meeting you're already looking
    at.

THE FIX
    One reusable endpoint. Any surface drops in a lazy-loaded HTMX strip:

        <div hx-get="/api/partial/connections/project/{id}" hx-trigger="revealed"></div>

    The server looks up the seed text for that entity, runs the connection engine,
    excludes the entity itself, and renders a consistent, token-styled strip. The
    connection comes to you, on the surface you're already on — which is the whole
    thesis of the product.
"""

from __future__ import annotations

import logging
import os
import sys

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

log = logging.getLogger("metis.connections")

router = APIRouter()
_TEMPLATES = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

# Make the MCP tools importable (same trick main.py uses).
_MCP_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "mcp-server", "src")
if _MCP_SRC not in sys.path:
    sys.path.insert(0, _MCP_SRC)


# Each entity maps to (table, id-column, [text-columns to build the seed from]).
# The seed is what the engine matches against; richer seed → better connections.
_ENTITY_SEED = {
    "project": ("projects", "project_id", ["title", "description", "next_step"]),
    "task":    ("tasks", "task_id", ["title", "description", "category"]),
    "paper":   ("literature_metadata", "id", ["title", "abstract", "tags"]),
    "meeting": ("meetings", "id", ["title", "decisions", "transcript"]),
    "idea":    ("ideas", "idea_id", ["title", "content"]),
    "note":    ("personal_notes", "note_id", ["title", "content"]),
}

# The entity's OWN source label, so we never show a thing as its own connection.
_SELF_SOURCE = {
    "project": "project", "task": "task", "paper": "library",
    "meeting": "meeting", "idea": "idea", "note": "note",
}


def _seed_text(entity: str, entity_id: str) -> str | None:
    """Build the match seed for an entity from its own text columns."""
    spec = _ENTITY_SEED.get(entity)
    if not spec:
        return None
    table, id_col, cols = spec
    try:
        from metis_mcp.config import paths
        from metis_mcp.db import connect

        with connect(paths.db) as conn:
            row = conn.execute(
                f"SELECT {', '.join(cols)} FROM {table} WHERE {id_col} = ? LIMIT 1",
                (entity_id,),
            ).fetchone()
        if not row:
            return None
        parts = [str(row[c]) for c in cols if row[c]]
        # Transcripts can be huge; the engine only needs a representative seed.
        return " ".join(parts)[:2000] or None
    except Exception as exc:
        log.warning("connections: could not build seed for %s/%s: %s", entity, entity_id, exc)
        return None


def connections_for(seed: str, exclude_title: str = "", limit: int = 5) -> list[dict]:
    """Run the shared cross-pollination engine and clean up the result.

    Reuses _cross_pollinate_core (the same engine the capture modal uses), so
    there is ONE definition of "what connects to what" across the whole app.
    """
    if not seed or not seed.strip():
        return []
    try:
        from metis_mcp.tools.ideas import _cross_pollinate_core
    except Exception as exc:
        log.warning("connections: engine unavailable: %s", exc)
        return []

    try:
        matches = _cross_pollinate_core(seed, max_results=limit + 2)
    except Exception as exc:
        log.warning("connections: engine errored: %s", exc)
        return []

    # Drop the entity matching itself (same title), then cap.
    ex = (exclude_title or "").strip().lower()[:40]
    out = [m for m in matches if (m.get("title") or "").strip().lower()[:40] != ex]
    return out[:limit]


@router.get("/api/partial/connections/today", response_class=HTMLResponse)
async def connections_today(request: Request):
    """Connections for what you're working on right now — for the Today cockpit.

    Seeds from your most recently touched project, so cross-pollination greets you
    daily on the surface you actually open, not in a tab you have to remember.
    Kept in THIS router (not the 4,600-line today.py) so it stays isolated.
    """
    seed, own_title = "", ""
    try:
        from metis_mcp.config import paths
        from metis_mcp.db import connect

        with connect(paths.db) as conn:
            row = conn.execute(
                "SELECT title, description, next_step FROM projects "
                "WHERE status IS NULL OR status NOT IN ('archived','done') "
                "ORDER BY COALESCE(last_session_at, created_at) DESC LIMIT 1"
            ).fetchone()
        if row:
            own_title = str(row["title"] or "")
            seed = " ".join(str(row[c]) for c in ("title", "description", "next_step") if row[c])[:2000]
    except Exception as exc:
        log.warning("connections/today: could not pick active project: %s", exc)

    matches = connections_for(seed, exclude_title=own_title) if seed else []
    return _TEMPLATES.TemplateResponse(
        request,
        "partials/connections_strip.html",
        {"matches": matches, "entity": "today", "seed_title": own_title},
    )


@router.get("/api/partial/connections/{entity}/{entity_id:path}", response_class=HTMLResponse)
async def connections_partial(request: Request, entity: str, entity_id: str):
    """The one endpoint every surface calls. Lazy-loaded via hx-trigger=revealed."""
    seed = _seed_text(entity, entity_id)
    own_title = ""
    if seed:
        # First column of the seed is the title; use it to exclude self-matches.
        own_title = seed.split()[0:12] and seed[:80] or ""
    matches = connections_for(seed or "", exclude_title=own_title) if seed else []
    return _TEMPLATES.TemplateResponse(
        request,
        "partials/connections_strip.html",
        {"matches": matches, "entity": entity},
    )
