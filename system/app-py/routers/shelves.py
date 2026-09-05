"""Library shelves — the reason something was kept.

A shelf is not a topic label. Asked for 2026-09-05: "if I put an article in
Methodology, I like the article for its methodology that interests me, maybe not
straight away. If I put something in AI it's because I am making an AI library to
follow up its development."

Those are two different objects, and that is why one flat `collection` column sat
NULL on all 1,144 library rows: a single list cannot behave two ways. So a shelf
has a KIND, and the kind decides how it reads:

    purpose     why the work is good — timeless, raided when you need it, and
                explicitly NOT a queue. Ordered by what you kept most recently
                only because nothing better is known; never by "unread".
    tracking    a field as it develops — chronological, and the only kind where
                "what is new since I last looked" is a sensible question.
    attachment  evidence bound to one project or course. Derived from the
                projects and courses that already exist, never typed, so two
                spellings of one project cannot appear.

Saving is ADDITIVE across shelves. One paper legitimately belongs on several —
kept for its methods, filed against a project, and part of a subject being
tracked — and the standing preference here is that overlap between narrow
categories costs nothing while a category broad enough to need filtering costs
time on every visit.
"""
from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from db import db_execute, db_query, db_scalar

router = APIRouter()
_log = logging.getLogger(__name__)

KINDS = ("purpose", "tracking", "attachment")
KIND_LEAD = {
    "purpose":    "Kept for how it was done",
    "tracking":   "Following a field",
    "attachment": "Evidence for a piece of work",
}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def shelves(kind: str = "") -> list[dict]:
    """Live shelves, with how many items each holds."""
    where = "WHERE s.archived = 0" + (" AND s.kind = ?" if kind else "")
    rows = db_query(
        "SELECT s.slug, s.name, s.kind, s.blurb, s.ref, s.sort_order, "
        "       (SELECT COUNT(*) FROM library_shelf_items i WHERE i.shelf = s.slug) AS n "
        "FROM library_shelves s " + where + " "
        "ORDER BY s.kind, s.sort_order, s.name",
        (kind,) if kind else (), default=[]) or []
    return [dict(r) for r in rows]


def shelves_for(kind: str, item_id: str) -> set[str]:
    """Which shelves this item is already on — so the picker can show it."""
    rows = db_query(
        "SELECT shelf FROM library_shelf_items WHERE kind=? AND item_id=?",
        (kind, str(item_id)), default=[]) or []
    return {r["shelf"] for r in rows}


@router.get("/api/partial/library/shelf-picker", response_class=HTMLResponse)
async def shelf_picker(request: Request, kind: str, item_id: str, back: str = ""):
    """The shelf chooser for one item.

    Rendered on demand rather than inlined into every row: the digest shows nine
    items and there are 29 shelves, so inlining would put 261 options into a
    panel whose entire redesign this week was about spending less markup.
    """
    from main import templates
    return templates.TemplateResponse(
        request, "partials/library_shelf_picker.html",
        {"kind": kind, "item_id": str(item_id), "back": back,
         "groups": [(k, KIND_LEAD[k], [s for s in shelves() if s["kind"] == k])
                    for k in KINDS],
         "already": shelves_for(kind, item_id)},
    )


@router.post("/api/library/shelf/add", response_class=HTMLResponse)
async def shelf_add(request: Request, kind: str = Form(...), item_id: str = Form(...),
                    shelf: str = Form(...), back: str = Form("")):
    """Put an item on a shelf, and record that it was kept.

    TWO WRITES, and both are needed. The shelf row says WHY it was kept; the
    stack verdict says it WAS kept, which is what clears it from every unjudged
    queue. Writing only the shelf would leave the item sitting in the digest
    after it had been filed — the same defect the Stack button had.
    """
    item_id = str(item_id)
    if not db_scalar("SELECT 1 FROM library_shelves WHERE slug=? AND archived=0",
                     (shelf,), default=0):
        _log.warning("shelf %r does not exist; nothing filed", shelf)
        return HTMLResponse("", status_code=204)

    db_execute(
        "INSERT INTO library_shelf_items (shelf, kind, item_id, added_at) "
        "VALUES (?,?,?,?) ON CONFLICT(shelf, kind, item_id) DO NOTHING",
        (shelf, kind, item_id, _now()))
    try:
        from metis_mcp.tools import stack as S
        S.set_state(kind, item_id, "saved")
    except Exception:
        _log.warning("could not record the 'saved' verdict for %s/%s",
                     kind, item_id, exc_info=True)

    # Re-render whatever the click came from, so the row leaves the queue in
    # front of the reader rather than on the next page load.
    from routers.stack import _rerender
    return HTMLResponse(await _rerender(request, back or "today-field"))


@router.post("/api/library/shelf/remove", response_class=HTMLResponse)
async def shelf_remove(request: Request, kind: str = Form(...), item_id: str = Form(...),
                       shelf: str = Form(...)):
    """Take an item off a shelf. The item and its verdict are untouched."""
    db_execute("DELETE FROM library_shelf_items WHERE shelf=? AND kind=? AND item_id=?",
               (shelf, kind, str(item_id)))
    return await shelf_picker(request, kind=kind, item_id=str(item_id))


@router.get("/api/partial/library/shelves", response_class=HTMLResponse)
async def shelves_panel(request: Request):
    """Every shelf, grouped by what kind of shelf it is."""
    from main import templates
    return templates.TemplateResponse(
        request, "partials/library_shelves.html",
        {"groups": [(k, KIND_LEAD[k], [s for s in shelves() if s["kind"] == k])
                    for k in KINDS]},
    )


@router.get("/library/shelf/{slug}", response_class=HTMLResponse)
async def shelf_page(request: Request, slug: str):
    """One shelf, ordered the way its KIND wants to be read.

    A tracking shelf is a timeline and reads newest-first. A purpose shelf is a
    reference and reads by what you kept most recently only because nothing
    better is known — it is explicitly not a queue, so it carries no unread
    count and nothing on it is ever "overdue".
    """
    from main import templates
    sh = db_query("SELECT * FROM library_shelves WHERE slug=?", (slug,), default=[]) or []
    if not sh:
        return HTMLResponse("<p>No such shelf.</p>", status_code=404)
    sh = dict(sh[0])

    items = db_query(
        "SELECT i.kind, i.item_id, i.note, i.added_at, "
        "       COALESCE(p.title, b.title, '') AS title, "
        "       COALESCE(p.journal, '') AS journal, "
        "       COALESCE(p.source_url, b.source_url, '') AS url, "
        "       COALESCE(p.authors, '') AS authors "
        "FROM library_shelf_items i "
        "LEFT JOIN new_publications p ON i.kind='paper' AND CAST(p.id AS TEXT)=i.item_id "
        "LEFT JOIN news_briefs      b ON i.kind='news'  AND b.brief_id=i.item_id "
        "WHERE i.shelf=? ORDER BY i.added_at DESC",
        (slug,), default=[]) or []

    return templates.TemplateResponse(
        request, "library_shelf.html",
        {"shelf": sh, "items": [dict(r) for r in items],
         "lead": KIND_LEAD.get(sh["kind"], "")},
    )
