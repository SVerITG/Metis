"""focus.py — the dashboard surface for a focus area.

ONE TEMPLATE, MANY SURFACES
    Every other surface in Metis is a bespoke template: `today.html`,
    `knowledge.html`, `work.html`. A focus surface cannot work that way — the
    whole point is that the researcher adds and removes them himself, and a surface that
    needs a developer to exist is not a surface a user can add.

    So there is exactly one template, driven by one row. `/focus/ai-in-health-
    epidemiology` and `/focus/anything-else` render the same file against
    different data. That is what makes "custom pages a user can add or remove"
    a real feature rather than a promise.

THE FIVE COMPONENTS
    Taken from what the researcher asked for, and each one reads a table that already owns
    its rows — the focus writes no copies:

      pulse     what is new since the last visit, and how stale the feed is
      overview  the standing narrative — the orientation that survives the feed
      feed      news through the lens              (news_briefs)
      reading   literature through the lens        (new_publications)
      thinking  notes and ideas written here       (personal_notes, ideas)

    `pulse` is first on purpose. Opening a focus you have not seen for a week,
    the first question is "what happened", not "what is this".
"""
from __future__ import annotations

import datetime
import logging
import uuid

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter()
log = logging.getLogger("metis.focus")


def _f():
    """Import the shared focus logic lazily so a broken MCP tree cannot break boot."""
    from metis_mcp.tools import focus as F
    return F


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------
@router.get("/focus/{slug}", response_class=HTMLResponse)
async def focus_page(request: Request, slug: str):
    """One template, rendered against one focus row."""
    from main import templates
    F = _f()
    area = F.get_focus(slug)
    if not area:
        return RedirectResponse(url="/", status_code=302)

    # Read the pulse BEFORE stamping the visit, or "new since last visit" is
    # always zero — the surface would mark everything read by being opened.
    pulse = F.focus_pulse(slug)
    F.touch_visit(slug)

    return templates.TemplateResponse(request, "focus.html", {
        "active_tab": f"focus:{slug}",
        "area": area,
        "pulse": pulse,
        "corpus": F.focus_corpus(slug),
        "news": F.focus_news(slug, 14),
        "reading": F.focus_reading(slug, 14),
        "thinking": F.focus_thinking(slug),
        "shelf": F.list_focus("active"),
        "all_areas": F.list_focus(),
        "max_shelf": F.MAX_SHELF,
        "today": datetime.date.today().isoformat(),
    })


# ---------------------------------------------------------------------------
# Shelf management
# ---------------------------------------------------------------------------
@router.post("/api/focus/{slug}/state")
async def set_state(slug: str, state: str = Form(...)):
    """Put a focus on the shelf, take it off, or archive it."""
    F = _f()
    import asyncio
    res = await F.set_focus_state(slug, state)
    return JSONResponse({"ok": True, "message": res[0].text})


@router.get("/api/focus/shelf")
async def shelf():
    """The active shelf — what the navbar renders."""
    F = _f()
    return JSONResponse({
        "ok": True,
        "max": F.MAX_SHELF,
        "active": [
            {"slug": a["slug"], "title": a["title"], "slot": a["shelf_slot"]}
            for a in F.list_focus("active")
        ],
    })


# ---------------------------------------------------------------------------
# Writing on a focus — the "brainstorm" half
# ---------------------------------------------------------------------------
# Notes and ideas are tagged `focus:<slug>` and written to the tables that own
# them. That tag is the ONLY association, and it is why archiving a focus loses
# nothing: the row stays in `personal_notes` / `ideas` with its tag intact,
# findable by search whether or not the lens still exists.
@router.post("/api/focus/{slug}/note", response_class=HTMLResponse)
async def add_note(request: Request, slug: str, content: str = Form(...),
                   title: str = Form("")):
    """Record a note against this focus."""
    from db import db_execute
    from main import templates
    F = _f()
    if content.strip():
        db_execute(
            "INSERT INTO personal_notes (note_id, content, title, tags, created_at, "
            "updated_at) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4())[:8], content.strip(), title.strip(),
             f"focus:{slug}", _now(), _now()))
    return templates.TemplateResponse(
        request, "partials/focus_thinking.html",
        {"area": F.get_focus(slug), "thinking": F.focus_thinking(slug)})


@router.post("/api/focus/{slug}/idea", response_class=HTMLResponse)
async def add_idea(request: Request, slug: str, text: str = Form(...)):
    """Capture an idea against this focus."""
    from db import db_execute
    from main import templates
    F = _f()
    if text.strip():
        db_execute(
            "INSERT INTO ideas (idea_id, text, idea_type, tags, created_at, domain) "
            "VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4())[:8], text.strip(), "focus", f"focus:{slug}",
             _now(), slug))
    return templates.TemplateResponse(
        request, "partials/focus_thinking.html",
        {"area": F.get_focus(slug), "thinking": F.focus_thinking(slug)})


# ---------------------------------------------------------------------------
# Partials — so a refresh does not reload the page
# ---------------------------------------------------------------------------
@router.get("/api/partial/focus/{slug}/feed", response_class=HTMLResponse)
async def feed_partial(request: Request, slug: str):
    from main import templates
    F = _f()
    return templates.TemplateResponse(request, "partials/focus_feed.html", {
        "area": F.get_focus(slug), "news": F.focus_news(slug, 14),
        "today": datetime.date.today().isoformat()})


@router.get("/api/partial/focus/{slug}/reading", response_class=HTMLResponse)
async def reading_partial(request: Request, slug: str):
    from main import templates
    F = _f()
    return templates.TemplateResponse(request, "partials/focus_reading.html", {
        "area": F.get_focus(slug), "reading": F.focus_reading(slug, 14),
        "today": datetime.date.today().isoformat()})


@router.post("/api/focus/{slug}/refresh", response_class=HTMLResponse)
async def refresh(request: Request, slug: str):
    """Re-scan the sources this focus reads, then re-render the pulse.

    Deliberately reuses the SAME scan jobs the rest of Metis uses rather than
    fetching on its own — a focus is a lens over the shared collection, so a
    focus-specific fetch path would produce items only this surface could see.
    """
    from main import templates
    F = _f()
    errors = []
    try:
        from metis_mcp.tools.content_scan import scan_news_feeds
        scan_news_feeds(max_per_feed=8)
    except Exception as exc:
        errors.append(f"news: {type(exc).__name__}")
    try:
        from db import db_execute
        db_execute("UPDATE focus_areas SET last_refreshed_at=? WHERE slug=?",
                   (_now(), slug))
    except Exception as exc:
        errors.append(f"stamp: {type(exc).__name__}")
    if errors:
        log.warning("[focus] refresh %s: %s", slug, "; ".join(errors))
    return templates.TemplateResponse(request, "partials/focus_pulse.html", {
        "area": F.get_focus(slug), "pulse": F.focus_pulse(slug),
        "corpus": F.focus_corpus(slug),
        "today": datetime.date.today().isoformat()})


# ---------------------------------------------------------------------------
# The index — where focus areas are created, and where the non-active ones live
# ---------------------------------------------------------------------------
# Two gaps this closes.
#
# 1. THERE WAS NO WAY TO CREATE A FOCUS FROM THE DASHBOARD. It took an MCP call,
#    which quietly contradicts the whole premise: a surface is not one a user
#    can add if adding one requires a tool call.
#
# 2. `following` AND `archived` AREAS WERE UNREACHABLE. Only active areas appear
#    in the navbar, so anything taken off the shelf could be opened only by typing
#    its URL. An interest you set aside is exactly the one you will not remember
#    the slug for.
#
# The form asks for keyword GROUPS as separate fields — "must mention one of" AND
# "and one of" — rather than asking for JSON. That teaches the conjunction by
# construction, which matters because the conjunction is the one thing a user has
# to understand for the lens to behave.
@router.get("/focus", response_class=HTMLResponse)
async def focus_index(request: Request):
    from main import templates
    F = _f()
    areas = F.list_focus()
    enriched = []
    for a in areas:
        t = F.focus_thinking(a["slug"])
        enriched.append({**a,
                         "n_news": len(F.focus_news(a["slug"], limit=500)),
                         "n_reading": len(F.focus_reading(a["slug"], limit=500)),
                         "n_thinking": len(t["notes"]) + len(t["ideas"])})
    return templates.TemplateResponse(request, "focus_index.html", {
        "active_tab": "focus-index",
        "areas": enriched,
        "n_active": sum(1 for a in areas if a["state"] == "active"),
        "max_shelf": F.MAX_SHELF,
        "layers": _layer_slugs(),
    })


def _layer_slugs() -> list[dict]:
    try:
        from db import db_query
        return [dict(r) for r in (db_query(
            "SELECT k.slug, k.name, COUNT(DISTINCT p.source_file) AS docs "
            "FROM knowledge_databases k "
            "LEFT JOIN pdf_chunks p ON p.db_id = k.id "
            "GROUP BY k.slug ORDER BY 3 DESC") or [])]
    except Exception:
        return []


def _parse_group(raw: str) -> list[str]:
    """A comma-separated field becomes one keyword group."""
    return [w.strip().lower() for w in (raw or "").split(",") if w.strip()]


@router.post("/api/focus/preview", response_class=HTMLResponse)
async def preview(request: Request, group1: str = Form(""), group2: str = Form(""),
                  group3: str = Form("")):
    """Live preview of a candidate lens — the answer to blind lens tuning.

    Fires as the form is typed. Before this, the only way to learn a lens caught
    nothing was to create the focus, open the surface and find it empty.
    """
    from main import templates
    F = _f()
    groups = [g for g in (_parse_group(group1), _parse_group(group2),
                          _parse_group(group3)) if g]
    return templates.TemplateResponse(request, "partials/focus_preview.html",
                                      {"p": F.preview_lens(groups) if groups else None})


@router.post("/api/focus/create")
async def create(request: Request, title: str = Form(...), subtitle: str = Form(""),
                 group1: str = Form(""), group2: str = Form(""),
                 group3: str = Form(""), layers: str = Form(""),
                 activate: str = Form("")):
    """Create a focus from the form, then open it."""
    import json as _json
    F = _f()
    groups = [g for g in (_parse_group(group1), _parse_group(group2),
                          _parse_group(group3)) if g]
    if not title.strip() or not groups:
        return RedirectResponse(url="/focus", status_code=302)
    res = await F.create_focus_area(
        title=title.strip(), keyword_groups=_json.dumps(groups),
        subtitle=subtitle.strip(), layers=layers.strip(),
        activate=bool(activate))
    slug = F.slugify(title)
    if F.get_focus(slug):
        return RedirectResponse(url=f"/focus/{slug}", status_code=302)
    log.warning("[focus] create failed: %s", res[0].text[:160])
    return RedirectResponse(url="/focus", status_code=302)
