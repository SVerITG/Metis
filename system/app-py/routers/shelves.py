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


def shelves(kind: str = "", stream: str = "") -> list[dict]:
    """Live categories, with how many items each holds.

    `stream` is 'news' or 'paper' and filters to the categories that serve it.
    Reported 2026-09-05: the interests differ by stream, and offering all 29 for
    every item makes the reader do the filtering the category system exists to
    have already done.

    Matched on the comma-separated list rather than with LIKE: a bare
    `applies_to LIKE '%news%'` would also match a category serving a stream
    called "newsletters", and the bug would not appear until such a stream
    existed.
    """
    where = "WHERE s.archived = 0" + (" AND s.kind = ?" if kind else "")
    params: list = [kind] if kind else []
    if stream:
        where += (" AND (',' || REPLACE(COALESCE(s.applies_to,'news,paper'), ' ', '') || ',') "
                  "LIKE ('%,' || ? || ',%')")
        params.append(stream)
    rows = db_query(
        "SELECT s.slug, s.name, s.kind, s.blurb, s.ref, s.sort_order, "
        "       COALESCE(s.applies_to,'news,paper') AS applies_to, "
        "       (SELECT COUNT(*) FROM library_shelf_items i WHERE i.shelf = s.slug) AS n "
        "FROM library_shelves s " + where + " "
        "ORDER BY s.kind, s.sort_order, s.name",
        tuple(params), default=[]) or []
    return [dict(r) for r in rows]


def shelves_for(kind: str, item_id: str) -> set[str]:
    """Which shelves this item is already on — so the picker can show it."""
    rows = db_query(
        "SELECT shelf FROM library_shelf_items WHERE kind=? AND item_id=?",
        (kind, str(item_id)), default=[]) or []
    return {r["shelf"] for r in rows}


def kept_by_ref() -> dict[str, dict]:
    """{ref: {slug, name, n}} for every ATTACHMENT category holding something.

    Used by the project card and the course page, so the count appears where the
    work is rather than only on the Library surface. This is the half of the
    model that makes an attachment category worth having: evidence filed against
    a project that never shows up on the project is evidence you will not find
    when you need it.

    Refs with nothing filed are OMITTED, so a card shows the line only when
    there is something behind it — a "0 kept" on nineteen cards is nineteen rows
    of noise.
    """
    rows = db_query(
        "SELECT s.ref, s.slug, s.name, COUNT(i.item_id) AS n "
        "FROM library_shelves s "
        "JOIN library_shelf_items i ON i.shelf = s.slug "
        "WHERE s.kind = 'attachment' AND s.archived = 0 AND COALESCE(s.ref,'') <> '' "
        "GROUP BY s.ref, s.slug, s.name",
        default=[]) or []
    return {r["ref"]: dict(r) for r in rows}


@router.get("/api/partial/library/shelf-picker", response_class=HTMLResponse)
async def shelf_picker(request: Request, kind: str, item_id: str, back: str = "",
                       target: str = "closest .fw-row", swap: str = "outerHTML"):
    """The shelf chooser for one item.

    Rendered on demand rather than inlined into every row: the digest shows nine
    items and there are 29 shelves, so inlining would put 261 options into a
    panel whose entire redesign this week was about spending less markup.
    """
    from main import templates
    return templates.TemplateResponse(
        request, "partials/library_shelf_picker.html",
        {"kind": kind, "item_id": str(item_id), "back": back,
         "target": target, "swap": swap,
         # SCOPED TO THIS ITEM'S STREAM. A news item is not filed under
         # "Methodology"; a paper can be filed under anything.
         "groups": [(k, KIND_LEAD[k],
                     [s for s in shelves(stream=kind) if s["kind"] == k])
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
    all_shelves = shelves()
    return templates.TemplateResponse(
        request, "partials/library_shelves.html",
        {"groups": [(k, KIND_LEAD[k], [s for s in all_shelves if s["kind"] == k])
                    for k in KINDS]},
    )


# What each kind is ordered BY, and what it is ordered by is the whole point of
# having kinds at all. While every kind sorted by `added_at` the kind was a
# label, which was the original complaint about the column this replaces.
#
#   tracking    the item's OWN date — a timeline of the field, not of your
#               filing. Sorting a timeline by when you happened to save each
#               piece produces an order that means nothing about the subject.
#   purpose     when you kept it, because a reference has no intrinsic order
#               and the most recent thing you thought worth keeping is the best
#               available guess at what is on your mind. Never a queue.
#   attachment  the item's own date too: evidence for a project reads as a
#               record of what the evidence said, in the order it appeared.
_ORDER = {
    "tracking":   "COALESCE(NULLIF(pub_on,''), NULLIF(news_on,''), i.added_at) DESC",
    "attachment": "COALESCE(NULLIF(pub_on,''), NULLIF(news_on,''), i.added_at) DESC",
    "purpose":    "i.added_at DESC",
}


@router.get("/library/shelf/{slug}", response_class=HTMLResponse)
async def shelf_page(request: Request, slug: str):
    """One category, ordered the way its KIND wants to be read.

    A tracking category is a timeline: it reads by the items' own dates, and it
    is the only kind that can say "new since you last looked" — so it carries a
    since-marker and the others do not. A purpose category is a reference you
    raid: it has no unread count, nothing on it is overdue, and it is ordered
    by what you last thought worth keeping only because nothing better exists.
    """
    from main import templates
    sh = db_query("SELECT * FROM library_shelves WHERE slug=?", (slug,), default=[]) or []
    if not sh:
        return HTMLResponse("<p>No such category.</p>", status_code=404)
    sh = dict(sh[0])
    kind = sh.get("kind") or "purpose"

    items = db_query(
        "SELECT i.kind, i.item_id, i.note, i.added_at, "
        "       COALESCE(p.title, b.title, '') AS title, "
        "       COALESCE(p.journal, '') AS journal, "
        "       COALESCE(p.source_url, b.source_url, '') AS url, "
        "       COALESCE(p.authors, '') AS authors, "
        "       COALESCE(NULLIF(p.pub_iso,''), NULLIF(p.pub_date,'')) AS pub_on, "
        "       COALESCE(b.brief_date,'') AS news_on "
        "FROM library_shelf_items i "
        "LEFT JOIN new_publications p ON i.kind='paper' AND CAST(p.id AS TEXT)=i.item_id "
        "LEFT JOIN news_briefs      b ON i.kind='news'  AND b.brief_id=i.item_id "
        "WHERE i.shelf=? ORDER BY " + _ORDER.get(kind, _ORDER["purpose"]),
        (slug,), default=[]) or []
    items = [dict(r) for r in items]

    # THE SINCE-MARKER, on tracking categories only. `last_seen_at` is stamped
    # when the page is opened, so "new since you last looked" means since the
    # last time this category was actually read — not since a scan ran, which
    # is a fact about the machine rather than about the reader.
    n_new, seen_before = 0, ""
    if kind == "tracking":
        seen_before = str(sh.get("last_seen_at") or "")
        if seen_before:
            n_new = sum(1 for it in items if str(it.get("added_at") or "") > seen_before)
        db_execute("UPDATE library_shelves SET last_seen_at=? WHERE slug=?",
                   (_now(), slug))

    for it in items:
        it["_on"] = (str(it.get("pub_on") or it.get("news_on") or it.get("added_at") or ""))[:10]
        it["_is_new"] = bool(seen_before and str(it.get("added_at") or "") > seen_before)

    return templates.TemplateResponse(
        request, "library_shelf.html",
        {"shelf": sh, "items": items, "kind": kind,
         "is_timeline": kind in ("tracking", "attachment"),
         "n_new": n_new, "seen_before": seen_before[:10],
         "lead": KIND_LEAD.get(kind, "")},
    )
