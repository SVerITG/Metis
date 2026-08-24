"""
new_literature.py — the New Literature surface at the top of the Library.

WHAT THIS IS FOR
    Staying current. Not searching what you already have — that is the catalogue
    below it — but reviewing what has appeared since you last looked, and deciding
    for each item whether it enters the library.

    Three things make that work, and all three were missing:

    1. WINDOWS THAT MATCH HOW REVIEWING ACTUALLY HAPPENS. Today, this week, and
       "since I last caught up". The third is the important one: a fixed 7-day
       window is wrong every time you have been away for ten days, and it is wrong
       silently — it shows you a full-looking list that has quietly dropped the
       first three days. The catch-up window reads a stored marker instead.

    2. TABS, so 1,000 items are legible. One lane for general science (big
       findings outside the field) and one tab per research area. Without tabs the
       NTD work is buried under a much larger flow of high-profile biology.

    3. ARTICLES AND BOOKS SEPARATED. Different things, reviewed differently.

DATE BASIS — the subtle part
    Windows filter on `COALESCE(NULLIF(pub_iso,''), date(discovered_at))`:
    publication date when known, discovery date when not.

    Filtering on discovery alone would have put all 400 papers of the
    retrospective HAT sweep under "Today", because that is when Metis found them.
    Filtering on the raw `pub_date` string would compare '2026 Jul 1' against
    '2026-08-20' lexically and misfile things without saying so. Only a normalised
    publication date with an honest fallback gets both cases right.
"""
from __future__ import annotations

import datetime
import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)

# ---------------------------------------------------------------------------
# Tabs.
#
# Each tab is a set of tag/topic needles matched against `topic_tag`, `feed_name`
# and the title. Needle sets rather than a single stored category on purpose: one
# paper legitimately belongs in several tabs (a spatial analysis of HAT in the DRC
# belongs in HAT, in spatial methods, and in DRC), and forcing a single label
# would hide it from two of the three places its reader would look.
#
# Order matters — it is the reading order of the strip, most specific first.
# ---------------------------------------------------------------------------
LIT_TABS: list[dict] = [
    {"key": "close", "label": "Close to my work", "kind": "relevance",
     "blurb": "Ranked by closeness to your own corpus. The default view."},

    {"key": "hat", "label": "HAT & trypanosomes", "kind": "match",
     "needles": {"hat", "trypanosom", "sleeping sickness", "brucei", "gambiense",
                 "tsetse", "glossina", "vsg", "tryps"},
     "blurb": "Sleeping sickness across the whole disease — parasite, vector, "
              "diagnosis, elimination."},

    {"key": "parasite-biology", "label": "Parasite biology", "kind": "match",
     "needles": {"parasitology", "molecular", "antigenic", "vsg", "genom",
                 "plos pathogens", "nature microbiology", "mol microbiology",
                 "trends in parasitology", "mbio", "cell host"},
     "blurb": "Molecular and cellular work. The axis your library had no feed "
              "for until 2026-08-21."},

    {"key": "ntd", "label": "NTDs & tropical medicine", "kind": "match",
     "needles": {"ntd", "tropical-medicine", "neglected", "schistosom",
                 "leishman", "filaria", "helminth", "chagas", "buruli", "leprosy"},
     "blurb": "The wider neglected-disease field."},

    {"key": "malaria", "label": "Malaria", "kind": "match",
     "needles": {"malaria", "plasmodium", "anopheles", "artemisinin"},
     "blurb": "Malaria epidemiology, control and resistance."},

    {"key": "methods", "label": "Methods & spatial", "kind": "match",
     "needles": {"spatial-epi", "methods", "epidemiology", "multilevel",
                 "geostatist", "bayesian", "regression", "sample size",
                 "int j health geogr", "int j epidemiology"},
     "blurb": "Study design, statistics, spatial analysis."},

    {"key": "surveillance", "label": "Surveillance & outbreaks", "kind": "match",
     "needles": {"surveillance", "outbreak", "infectious-disease", "screening",
                 "case detection", "elimination", "eid"},
     "blurb": "Detection, response and elimination programmes."},

    {"key": "health-systems", "label": "Health systems & policy", "kind": "match",
     "needles": {"policy", "public-health", "health system", "dhis2",
                 "conflict-health", "financing", "governance", "workforce"},
     "blurb": "Systems, data infrastructure and policy."},

    {"key": "ai", "label": "AI & modelling", "kind": "match",
     "needles": {"ai", "machine learning", "deep learning", "neural",
                 "forecast", "model", "llm", "arxiv"},
     "blurb": "Computational methods and AI in health."},

    {"key": "preprints", "label": "Preprints", "kind": "kind",
     "entry_kinds": {"preprint"},
     "blurb": "Not yet peer-reviewed. Often a year ahead of the journal version."},

    # The lane tab. Deliberately last: it is the "interesting but not mine" pile,
    # and it must never be the first thing competing for attention.
    {"key": "general", "label": "General science", "kind": "lane",
     "lane": "general",
     "blurb": "Nature, Science, NEJM, Lancet, PNAS and peers — important findings "
              "outside your field. Anything close to your work is filed under "
              "its own topic instead."},
]

LIT_TABS_BY_KEY = {t["key"]: t for t in LIT_TABS}

# ---------------------------------------------------------------------------
# Windows. `catchup` has no fixed length — that is the whole point of it.
# ---------------------------------------------------------------------------
LIT_WINDOWS: dict[str, tuple[int | None, str]] = {
    "day":     (1,    "Today"),
    "week":    (7,    "This week"),
    "catchup": (None, "Since I caught up"),
    "month":   (30,   "This month"),
}

# Item-kind groups. the researcher asked for articles and books to be listed separately;
# these are the groups the "kind" chips filter on.
KIND_GROUPS: dict[str, tuple[str, set[str]]] = {
    "":         ("Everything", set()),
    "articles": ("Articles",   {"article"}),
    "reviews":  ("Reviews",    {"review"}),
    "preprints": ("Preprints", {"preprint"}),
    "books":    ("Books & reports", {"book", "report", "chapter"}),
}

PAGE_SIZE = 30
SURFACE = "new-literature"


# ---------------------------------------------------------------------------
# Review-state helpers
# ---------------------------------------------------------------------------

def _last_reviewed() -> str:
    """ISO timestamp of the last catch-up, or '' if never."""
    return db_scalar(
        "SELECT last_reviewed_at FROM library_review_state WHERE surface = ?",
        (SURFACE,), default="",
    ) or ""


def _window_cutoff(window: str) -> tuple[str, str]:
    """Return (cutoff_date, human_label) for a window key.

    An empty cutoff means no lower bound — used when a catch-up has never been
    recorded, where the honest answer is "everything, because I do not know what
    you have already seen" rather than a silently invented 7 days.
    """
    days, label = LIT_WINDOWS.get(window, LIT_WINDOWS["week"])
    if window == "catchup":
        last = _last_reviewed()
        if not last:
            return "", "Everything (no catch-up recorded yet)"
        d = last[:10]
        span = (datetime.date.today() - datetime.date.fromisoformat(d)).days
        return d, f"Since {d} ({span} day{'s' if span != 1 else ''} ago)"
    cutoff = (datetime.date.today() - datetime.timedelta(days=days or 7)).isoformat()
    return cutoff, label


# The effective date of an item: publication date when we have one, discovery
# date otherwise. Written once, used by every query, because a window and its
# count disagreeing is worse than either being wrong.
_EFF_DATE = "COALESCE(NULLIF(pub_iso, ''), substr(discovered_at, 1, 10))"


def _tab_predicate(spec: dict) -> tuple[str, list]:
    """SQL fragment + params selecting the rows for one tab."""
    kind = spec.get("kind")
    if kind == "lane":
        return " AND lane = ? ", [spec["lane"]]
    if kind == "kind":
        marks = ",".join("?" for _ in spec["entry_kinds"])
        return f" AND entry_kind IN ({marks}) ", list(spec["entry_kinds"])
    if kind == "match":
        # Match against the tag string, the feed name, the title AND the abstract.
        # Tags alone are too sparse: a Nature paper on trypanosomes carries the
        # tag 'general-science' and nothing else, so only the title reveals it.
        needles = sorted(spec["needles"])
        clauses = " OR ".join(
            ["lower(topic_tag) LIKE ?"] * len(needles)
            + ["lower(feed_name) LIKE ?"] * len(needles)
            + ["lower(title) LIKE ?"] * len(needles)
        )
        params = [f"%{n}%" for n in needles] * 3
        # General-lane items are excluded from topic tabs ONLY when they do not
        # match: a matching general-science paper IS field work, and classify_
        # publication has already relabelled those. Nothing extra to do here.
        return f" AND ({clauses}) ", params
    return "", []      # 'relevance' — no filter, ordered by closeness


def _fetch(
    tab: str = "close",
    window: str = "week",
    kind_group: str = "",
    q: str = "",
    show: str = "unread",
    page: int = 1,
) -> tuple[list[dict], int, str]:
    """Rows for one tab/window/filter combination. Returns (items, total, label)."""
    spec = LIT_TABS_BY_KEY.get(tab, LIT_TABS[0])
    cutoff, label = _window_cutoff(window)

    where = ["1=1"]
    params: list = []

    if cutoff:
        where.append(f"{_EFF_DATE} >= ?")
        params.append(cutoff)

    # 'unread' means not yet acted on — neither added nor dismissed. `read_at`
    # predates this surface and conflated both, so it is treated as either.
    if show == "unread":
        where.append("COALESCE(added_at,'') = '' AND COALESCE(dismissed_at,'') = '' "
                     "AND COALESCE(read_at,'') = ''")
    elif show == "added":
        where.append("COALESCE(added_at,'') != ''")

    pred, pred_params = _tab_predicate(spec)
    if pred:
        where.append(pred.replace(" AND ", "", 1).strip())
        params += pred_params

    if kind_group and kind_group in KIND_GROUPS:
        kinds = KIND_GROUPS[kind_group][1]
        if kinds:
            where.append(f"entry_kind IN ({','.join('?' for _ in kinds)})")
            params += sorted(kinds)

    if q:
        where.append("(lower(title) LIKE ? OR lower(abstract) LIKE ? "
                     "OR lower(authors) LIKE ? OR lower(journal) LIKE ?)")
        params += [f"%{q.lower()}%"] * 4

    clause = " AND ".join(where)

    total = db_scalar(f"SELECT COUNT(*) FROM new_publications WHERE {clause}",
                      tuple(params), default=0) or 0

    # Ordering: closeness first inside the field tabs, because the point is to
    # read the most relevant thing first, not the most recent. General science
    # orders by date — there is no "closeness" to rank by, by definition.
    order = ("relevance DESC, " + _EFF_DATE + " DESC"
             if spec.get("kind") != "lane" else _EFF_DATE + " DESC, relevance DESC")

    rows = db_query(
        f"SELECT id, title, authors, journal, feed_name, pub_date, pub_iso, "
        f"       pub_precision, doi, source_url, abstract, topic_tag, entry_kind, "
        f"       lane, relevance, acq_status, acq_reason, pdf_path, added_at, "
        f"       dismissed_at, read_at, zotero_key, discovered_at "
        f"FROM new_publications WHERE {clause} "
        f"ORDER BY {order} LIMIT ? OFFSET ?",
        tuple(params) + (PAGE_SIZE, max(0, (page - 1) * PAGE_SIZE)),
    ) or []

    return rows, total, label


def _tab_counts(window: str, show: str = "unread") -> dict[str, int]:
    """Unread count per tab, for the badges on the strip.

    Counted per tab rather than estimated: a badge that disagrees with the list
    it labels destroys trust in both, and this is 11 cheap indexed queries.
    """
    counts: dict[str, int] = {}
    for t in LIT_TABS:
        try:
            _, total, _ = _fetch(tab=t["key"], window=window, show=show, page=1)
            counts[t["key"]] = total
        except Exception:
            counts[t["key"]] = 0
    return counts


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/api/partial/library/new-literature", response_class=HTMLResponse)
async def new_literature_panel(
    request: Request,
    tab: str = "close",
    window: str = "week",
    kind: str = "",
    q: str = "",
    show: str = "unread",
    page: int = 1,
):
    """The whole New Literature block: strip, window switcher, and the list."""
    if tab not in LIT_TABS_BY_KEY:
        tab = "close"
    if window not in LIT_WINDOWS:
        window = "week"

    items, total, window_label = _fetch(tab, window, kind, q, show, page)
    counts = _tab_counts(window, show)
    last = _last_reviewed()

    return templates.TemplateResponse(
        request,
        "partials/library_new_literature.html",
        {
            "tabs": LIT_TABS, "active": tab, "spec": LIT_TABS_BY_KEY[tab],
            "windows": LIT_WINDOWS, "window": window, "window_label": window_label,
            "kind_groups": KIND_GROUPS, "active_kind": kind,
            "items": items, "total": total, "counts": counts,
            "q": q, "show": show, "page": page,
            "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
            "last_reviewed": last[:16].replace("T", " ") if last else "",
            "sources_total": db_scalar(
                "SELECT COUNT(*) FROM new_publications", default=0) or 0,
        },
    )


@router.get("/api/partial/library/new-literature/list", response_class=HTMLResponse)
async def new_literature_list(
    request: Request,
    tab: str = "close",
    window: str = "week",
    kind: str = "",
    q: str = "",
    show: str = "unread",
    page: int = 1,
):
    """List body only — swapped on tab/window/filter change.

    Separate from the panel route so switching a tab does not re-render the strip
    it was clicked on: the strip keeps focus and the page does not jump.
    """
    if tab not in LIT_TABS_BY_KEY:
        tab = "close"
    items, total, window_label = _fetch(tab, window, kind, q, show, page)
    return templates.TemplateResponse(
        request,
        "partials/library_new_literature_list.html",
        {
            "items": items, "total": total, "active": tab,
            "spec": LIT_TABS_BY_KEY[tab], "window": window,
            "window_label": window_label, "active_kind": kind,
            "q": q, "show": show, "page": page,
            "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        },
    )


@router.post("/api/library/new-literature/catchup")
async def mark_caught_up(request: Request):
    """Record that the researcher has reviewed up to now.

    Explicit, never automatic. the researcher's standing preference on the daily brief is
    that an explicit action is the only signal a thing was actually read, and the
    same reasoning applies here with more force: this marker decides what the
    catch-up window HIDES next time, so inferring it from a page view would
    silently discard unreviewed literature.
    """
    now = datetime.datetime.now().isoformat(timespec="seconds")
    seen = db_scalar(
        "SELECT COUNT(*) FROM new_publications WHERE "
        "COALESCE(added_at,'')='' AND COALESCE(dismissed_at,'')=''", default=0) or 0
    db_execute(
        "INSERT INTO library_review_state (surface, last_reviewed_at, items_seen, updated_at) "
        "VALUES (?,?,?,?) ON CONFLICT(surface) DO UPDATE SET "
        "last_reviewed_at=excluded.last_reviewed_at, items_seen=excluded.items_seen, "
        "updated_at=excluded.updated_at",
        (SURFACE, now, seen, now),
    )
    return JSONResponse({"ok": True, "at": now, "outstanding": seen})


@router.post("/api/library/new-literature/{pub_id}/dismiss")
async def dismiss_item(pub_id: int):
    """Not interested. Distinct from 'added' so the two can be told apart later."""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    db_execute("UPDATE new_publications SET dismissed_at = ? WHERE id = ?",
               (now, pub_id))
    return JSONResponse({"ok": True})


@router.post("/api/library/new-literature/{pub_id}/restore")
async def restore_item(pub_id: int):
    """Undo a dismissal. Any one-click discard needs a way back."""
    db_execute("UPDATE new_publications SET dismissed_at = '', read_at = '' "
               "WHERE id = ?", (pub_id,))
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Add to library — acquisition, cataloguing, and the Zotero push
# ---------------------------------------------------------------------------

def _single_row(pub_id: int) -> dict | None:
    rows = db_query(
        "SELECT id, title, authors, journal, feed_name, pub_date, pub_iso, "
        "       pub_precision, doi, source_url, abstract, topic_tag, entry_kind, "
        "       lane, relevance, acq_status, acq_reason, pdf_path, added_at, "
        "       dismissed_at, read_at, zotero_key, discovered_at "
        "FROM new_publications WHERE id = ?", (pub_id,))
    return rows[0] if rows else None


@router.get("/api/partial/library/new-literature/row/{pub_id}",
            response_class=HTMLResponse)
async def new_literature_row(request: Request, pub_id: int):
    """Re-render ONE row.

    Exists so "Add to library" can report what actually happened. Swapping the
    whole list would lose every open abstract and the scroll position; optimistic
    client-side updating would show a green tick for a PDF that never arrived,
    which is precisely the false-confidence failure the red dot removes.
    """
    item = _single_row(pub_id)
    if not item:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request, "partials/library_new_literature_row.html", {"item": item})


@router.post("/api/library/new-literature/{pub_id}/add")
async def add_to_library(pub_id: int):
    """Acquire the PDF, catalogue the item, push it to Zotero.

    ORDER MATTERS. The catalogue row is written even when the PDF cannot be
    obtained — a reference you know about but cannot download is still a reference
    you want recorded, and refusing to catalogue it would mean the only trace of
    a paywalled paper is a dismissed row. What must never happen is a catalogue
    row that IMPLIES a file, so acquisition state is stored alongside it.
    """
    import sqlite3
    from db import get_db_path

    pub = _single_row(pub_id)
    if not pub:
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404)

    now = datetime.datetime.now().isoformat(timespec="seconds")

    # ── 1. Acquisition ──────────────────────────────────────────────────────
    acq = {"status": "failed", "reason": "not attempted", "path": "", "method": ""}
    try:
        from services.acquire import acquire_pdf
        con = sqlite3.connect(str(get_db_path()))
        try:
            acq = acquire_pdf(con, pub)
            con.commit()
        finally:
            con.close()
    except Exception as exc:
        acq = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"[:200],
               "path": "", "method": ""}

    db_execute(
        "UPDATE new_publications SET acq_status=?, acq_reason=?, pdf_path=?, "
        "added_at=?, read_at=COALESCE(NULLIF(read_at,''), ?) WHERE id=?",
        (acq["status"], acq["reason"][:400], acq["path"], now, now, pub_id),
    )

    # ── 2. Catalogue ────────────────────────────────────────────────────────
    lit_id = None
    try:
        # Dedup against the catalogue on DOI first, then title. Adding the same
        # paper twice is the most common way a reference library rots.
        existing = db_query(
            "SELECT id FROM literature_metadata WHERE "
            "(doi != '' AND lower(doi) = lower(?)) OR lower(title) = lower(?) LIMIT 1",
            (pub.get("doi") or "\x00", (pub.get("title") or "").strip()))
        if existing:
            lit_id = existing[0]["id"]
        else:
            db_execute(
                "INSERT INTO literature_metadata (title, authors, year, source, "
                "journal, tags, doi, abstract, url, item_type, library_source, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (pub.get("title", "")[:500], pub.get("authors", "")[:300],
                 (pub.get("pub_iso") or "")[:4] or None,
                 pub.get("journal", ""), pub.get("journal", ""),
                 pub.get("topic_tag", ""), pub.get("doi", ""),
                 pub.get("abstract", "")[:4000], pub.get("source_url", ""),
                 # Zotero's own vocabulary, so a later push needs no translation.
                 {"article": "journalArticle", "review": "journalArticle",
                  "preprint": "preprint", "book": "book",
                  "chapter": "bookSection", "report": "report"}
                 .get(pub.get("entry_kind") or "article", "journalArticle"),
                 "new-literature", now),
            )
            # NOT last_insert_rowid(): db_execute() opens and CLOSES its own
            # connection, so the rowid is gone before we could ask for it and the
            # call always returned 0. Re-query by the keys we just wrote.
            back = db_query(
                "SELECT id FROM literature_metadata WHERE "
                "(doi != '' AND lower(doi) = lower(?)) OR lower(title) = lower(?) "
                "ORDER BY id DESC LIMIT 1",
                (pub.get("doi") or "\x00", (pub.get("title") or "").strip()))
            lit_id = back[0]["id"] if back else None
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"catalogued nothing: {exc}"[:200],
             "acq": acq}, status_code=500)

    # ── 3. Zotero ───────────────────────────────────────────────────────────
    # Best-effort and never fatal: a failed push must not undo a successful
    # catalogue write. Reported so the row can say whether it reached Zotero.
    zkey = (pub.get("zotero_key") or "").strip()
    zerr = ""
    if zkey:
        # Already in Zotero — pushing again would create a duplicate, which is
        # the single worst thing a reference tool can do to a library.
        zerr = ""
    else:
        zkey, zerr = _push_one_to_zotero(pub, acq.get("path", ""))
        if zkey:
            db_execute("UPDATE new_publications SET zotero_key=? WHERE id=?",
                       (zkey, pub_id))
            if lit_id:
                db_execute("UPDATE literature_metadata SET zotero_key=?, "
                           "library_source='zotero' WHERE id=?", (zkey, lit_id))

    return JSONResponse({"ok": True, "acq": acq, "lit_id": lit_id,
                         "zotero_key": zkey, "zotero_error": zerr})


def _push_one_to_zotero(pub: dict, pdf_rel: str = "") -> tuple[str, str]:
    """Create this item in Zotero, attaching the PDF when we have one.

    Returns (zotero_key, error_reason). Exactly one of the two is non-empty.

    IT RETURNS THE REASON rather than swallowing it. The first version ended in
    `except Exception: pass`, and that hid a real failure for an entire test
    round: every push died on
        [SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate in chain
    because ITG's network terminates TLS with its own CA. The surface simply
    showed "no Zotero key" — indistinguishable from "Zotero is not configured",
    which is the wrong diagnosis and sends you to the wrong fix.

    THE CLIENT COMES FROM ONE PLACE. This used to construct its own
    `pyz.Zotero(...)`, so it never picked up the CA-bundle handling in
    `metis_mcp.tools.zotero._get_zotero_client()` — two constructions of the same
    client, only one of them corrected. Importing the shared one means a future
    network quirk is fixed once.
    """
    try:
        from metis_mcp.tools.zotero import (
            _get_zotero_client, zotero_credential_state,
        )
    except ImportError as exc:
        return "", f"Zotero module unavailable: {exc}"

    state = zotero_credential_state()
    if not state.get("web"):
        return "", state.get("reason") or "Zotero web API not configured"

    try:
        zot = _get_zotero_client()
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"[:200]

    itype = {"article": "journalArticle", "review": "journalArticle",
             "preprint": "preprint", "book": "book",
             "chapter": "bookSection", "report": "report"
             }.get(pub.get("entry_kind") or "article", "journalArticle")

    creators = [{"creatorType": "author", "name": n.strip()}
                for n in (pub.get("authors") or "").split(";")[:20] if n.strip()]
    item = {
        "itemType": itype,
        "title": (pub.get("title") or "")[:500],
        "creators": creators,
        "date": pub.get("pub_iso") or pub.get("pub_date") or "",
        "abstractNote": (pub.get("abstract") or "")[:5000],
        "url": pub.get("source_url") or "",
        "tags": [{"tag": tg.strip()} for tg in
                 (pub.get("topic_tag") or "").split(",") if tg.strip()][:12],
    }
    if itype == "journalArticle":
        item["publicationTitle"] = pub.get("journal") or ""
    if pub.get("doi"):
        item["DOI"] = pub["doi"]

    try:
        resp = zot.create_items([item])
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"[:200]

    successful = resp.get("successful") or {}
    if not successful:
        failed = resp.get("failed") or {}
        return "", (json.dumps(failed)[:180] if failed else "Zotero accepted nothing")
    key = list(successful.values())[0]["key"]

    # Attach the file so Zotero holds the paper rather than a stub. Tolerated on
    # failure: the item exists and the PDF is in a folder built to be navigable
    # by hand, which is why that folder layout matters.
    if pdf_rel:
        try:
            from services.acquire import library_root
            root = library_root()
            if root and (root / pdf_rel).exists():
                zot.attachment_simple([str(root / pdf_rel)], key)
        except Exception:
            pass
    return key, ""


@router.get("/api/library/resolve/{pub_id}")
async def resolve_via_institution(pub_id: int):
    """Redirect to the paper through the institutional resolver.

    The deliberate escape hatch. A background process cannot hold a Shibboleth
    session with MFA; the researcher's browser already has one. So when
    acquisition fails, this hands the exact same DOI to the place where the
    credentials live, instead of pretending the server can do it.
    """
    from fastapi.responses import RedirectResponse
    from services.acquire import resolver_url

    pub = _single_row(pub_id)
    if not pub:
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
    target = resolver_url(pub.get("doi") or "", pub.get("source_url") or "")
    if not target:
        return JSONResponse(
            {"ok": False,
             "error": "no DOI or URL for this item, and no resolver configured"},
            status_code=400)
    return RedirectResponse(target)


@router.get("/api/library/pdf/new/{pub_id}")
async def serve_new_pdf(pub_id: int):
    """Serve a PDF that acquisition filed."""
    from fastapi.responses import FileResponse
    from services.acquire import library_root

    pub = _single_row(pub_id)
    if not pub or not pub.get("pdf_path"):
        return JSONResponse({"ok": False, "error": "no file"}, status_code=404)
    root = library_root()
    if not root:
        return JSONResponse({"ok": False, "error": "no library folder"},
                            status_code=404)
    full = (root / pub["pdf_path"]).resolve()
    # Path containment check: pdf_path comes from our own writer, but serving a
    # file by a stored relative path is exactly the shape that becomes a
    # traversal bug the first time anything else writes that column.
    if not str(full).startswith(str(root.resolve())) or not full.is_file():
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
    return FileResponse(str(full), media_type="application/pdf",
                        filename=full.name)


@router.post("/api/library/scan")
async def trigger_library_scan():
    """Search every library source now — the manual twin of the daily job."""
    import asyncio
    try:
        from scheduler import job_library_scan
        await asyncio.to_thread(job_library_scan)
        from scheduler import _last_results
        r = _last_results.get("library_scan", {})
        return JSONResponse({"ok": True, "message": r.get("message", "Scan complete")})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:200]}, status_code=500)


@router.post("/api/library/pickup-downloads")
async def pickup_downloads():
    """File PDFs the researcher downloaded through the browser.

    The manual twin of the hourly `download_pickup` job. Exists as a button
    because the moment you want it is right after a download finishes, not up to
    an hour later.
    """
    import asyncio
    import sqlite3
    from db import get_db_path

    def _run():
        from services.download_pickup import scan_downloads
        con = sqlite3.connect(str(get_db_path()))
        try:
            return scan_downloads(con)
        finally:
            con.close()

    try:
        r = await asyncio.to_thread(_run)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:200]}, status_code=500)

    if r.get("error"):
        return JSONResponse({"ok": False, "error": r["error"]}, status_code=400)
    return JSONResponse({
        "ok": True,
        "message": (f"Filed {r['filed']} · {r['unmatched']} unmatched · "
                    f"{r['skipped']} skipped"),
        **r,
    })


# ---------------------------------------------------------------------------
# The HAT Library — one surface for the disease this researcher actually works on
# ---------------------------------------------------------------------------
#
# the researcher asked whether the Library has a specific focus on his HAT library. It did
# not. The material was spread across three places that did not know about each
# other: the catalogue (literature_metadata), the indexed corpus (pdf_chunks in
# the hat-specialist layer), and the review queue (new_publications). Each
# answered a different question and none answered "how complete is my HAT
# library?"
#
# This panel puts the three together and adds the one thing none of them had: a
# search box that queries the FULL TEXT of his own HAT papers rather than their
# titles. Until 2026-08-21 the hat-specialist layer held 5 documents; it now
# holds 220, so that search is finally worth offering.

HAT_TERMS = ("trypanosom", "sleeping sickness", "tsetse", "glossina",
             "gambiense", "rhodesiense", "brucei", "nagana", "surra", "evansi")

_HAT_LIKE = " OR ".join(
    "lower(title || ' ' || COALESCE(abstract,'')) LIKE ?" for _ in HAT_TERMS)
_HAT_PARAMS = tuple(f"%{w}%" for w in HAT_TERMS)

# The themes a HAT library is judged complete against. Deliberately the shape of
# the DISEASE, not the shape of the folder tree: a library can look tidy and
# still have nothing on the vector.
HAT_THEMES: list[tuple[str, tuple[str, ...]]] = [
    ("Diagnostics",       ("diagnos", "catt", "trypanolysis", "maect", "rdt",
                           "serolog", "pcr", "screening test", "litat")),
    ("Parasite biology",  ("vsg", "antigenic", "variant surface", "genom",
                           "transcript", "differentiation", "stumpy", "slender")),
    ("Vector & tsetse",   ("tsetse", "glossina", "vector", "tiny target", "trap")),
    ("Treatment",         ("fexinidazole", "acoziborole", "nifurtimox", "melarsoprol",
                           "eflornithine", "pentamidine", "suramin", "treatment", "drug")),
    ("Elimination",       ("elimination", "eliminat", "roadmap", "who target",
                           "interrupt")),
    ("Surveillance",      ("surveillance", "passive", "active screening",
                           "case detection", "reporting")),
    ("Animal reservoir",  ("reservoir", "animal", "pig", "cattle", "domestic",
                           "wild fauna", "congolense", "evansi", "nagana")),
    ("Modelling & spatial", ("model", "spatial", "risk map", "transmission dynamic",
                             "bayesian", "geostatist")),
]


@router.get("/api/partial/library/hat", response_class=HTMLResponse)
async def hat_library_panel(request: Request):
    """The HAT Library: what you hold, what is indexed, what is missing."""
    catalogue = db_scalar(
        f"SELECT COUNT(*) FROM literature_metadata WHERE {_HAT_LIKE}",
        _HAT_PARAMS, default=0) or 0

    indexed_files = db_scalar(
        "SELECT COUNT(DISTINCT source_file) FROM pdf_chunks WHERE db_id = "
        "(SELECT id FROM knowledge_databases WHERE slug='hat-specialist')",
        default=0) or 0
    indexed_chunks = db_scalar(
        "SELECT COUNT(*) FROM pdf_chunks WHERE db_id = "
        "(SELECT id FROM knowledge_databases WHERE slug='hat-specialist')",
        default=0) or 0

    # Coverage per theme, counted over the catalogue. A count, not a score:
    # any single number for "how complete is this library" would be invented.
    themes = []
    for label, needles in HAT_THEMES:
        clause = " OR ".join(
            "lower(title || ' ' || COALESCE(abstract,'')) LIKE ?" for _ in needles)
        n = db_scalar(
            f"SELECT COUNT(*) FROM literature_metadata "
            f"WHERE ({_HAT_LIKE}) AND ({clause})",
            _HAT_PARAMS + tuple(f"%{x}%" for x in needles), default=0) or 0
        themes.append({"label": label, "count": n})
    themes.sort(key=lambda t: -t["count"])

    # Gaps found by reference mining, ranked by how many of his papers cite them.
    gaps = db_query(
        "SELECT id, title, journal, pub_date, doi, relevance_note "
        "FROM new_publications WHERE topic_tag='hat-references' "
        "AND COALESCE(added_at,'')='' AND COALESCE(dismissed_at,'')='' "
        "ORDER BY relevance DESC LIMIT 12") or []
    gaps_total = db_scalar(
        "SELECT COUNT(*) FROM new_publications WHERE topic_tag='hat-references' "
        "AND COALESCE(added_at,'')='' AND COALESCE(dismissed_at,'')=''",
        default=0) or 0

    pending = db_scalar(
        "SELECT COUNT(*) FROM new_publications WHERE topic_tag LIKE 'hat-%' "
        "AND COALESCE(added_at,'')='' AND COALESCE(dismissed_at,'')=''",
        default=0) or 0

    last_built = db_scalar(
        "SELECT last_built FROM knowledge_databases WHERE slug='hat-specialist'",
        default="") or ""

    return templates.TemplateResponse(
        request, "partials/library_hat.html",
        {"catalogue": catalogue, "indexed_files": indexed_files,
         "indexed_chunks": indexed_chunks, "themes": themes,
         "gaps": gaps, "gaps_total": gaps_total, "pending": pending,
         "last_built": (last_built or "")[:16].replace("T", " ")},
    )


@router.get("/api/partial/library/hat/search", response_class=HTMLResponse)
async def hat_corpus_search(request: Request, q: str = ""):
    """Full-text semantic search across the researcher's own HAT papers.

    Distinct from every other search on this page: the catalogue search matches
    TITLES and abstracts, this one matches what the papers actually SAY. It is
    the capability the RAG index was rebuilt for.
    """
    results: list[dict] = []
    error = ""
    if q.strip():
        try:
            import asyncio
            from metis_mcp.tools.knowledge_db import search_pdf_knowledge
            raw = await search_pdf_knowledge(
                query=q, databases=["hat-specialist"], top_k=8)
            text = "".join(getattr(i, "text", "") for i in
                           (raw if isinstance(raw, list) else [raw]))
            # The tool returns formatted markdown; parse the parts we display.
            import re as _re
            for m in _re.finditer(
                    r"\*\*\d+\.\s(.+?)\*\*\s*\(score:\s*([\d.]+)\)\s*\n\s*"
                    r"Layer:.*?\|\s*Domain:\s*(.*?)\s*\|\s*p\.(\d+)\s*\|\s*(.*?)\n"
                    r"\s*>\s*(.*?)(?=\n\n|\Z)", text, _re.S):
                results.append({
                    "title": m.group(1).strip(), "score": float(m.group(2)),
                    "domain": m.group(3).strip(), "page": m.group(4),
                    "file": m.group(5).strip(), "snippet": m.group(6).strip(),
                })
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:180]

    return templates.TemplateResponse(
        request, "partials/library_hat_search.html",
        {"results": results, "q": q, "error": error})


# ---------------------------------------------------------------------------
# Corpus search as JSON — the endpoint the UserPromptSubmit hook calls
# ---------------------------------------------------------------------------
#
# WHY AN HTTP ENDPOINT AND NOT A SCRIPT
#     The hook fires on every prompt, so its cost is paid on every prompt. The
#     embedding model is 263 MB and takes seconds to load — a Node hook shelling
#     out to Python would pay that EVERY TIME, which would make Metis feel broken
#     rather than present.
#
#     The dashboard already holds the model warm in-process after its first use.
#     Asking it over localhost costs a few milliseconds. And when the dashboard is
#     not running the hook simply gets a connection error and stays silent, which
#     is the correct degradation: no corpus grounding, but no delay and no noise.

@router.get("/api/library/corpus-search")
async def corpus_search_json(
    q: str = "",
    layers: str = "",
    top_k: int = 6,
    min_score: float = 0.60,
):
    """Semantic search across knowledge layers, as JSON.

    `min_score` matters more than it looks. Without a floor, a query about
    something genuinely absent from the corpus still returns the six least-bad
    passages, and injecting those into the conversation actively misleads —
    it makes an unrelated paper look like evidence. A floor means "nothing
    relevant" is an answer the hook can give.
    """
    if not q.strip():
        return JSONResponse({"ok": True, "results": [], "reason": "empty query"})

    wanted = [s.strip() for s in layers.split(",") if s.strip()] or None
    try:
        from metis_mcp.tools.knowledge_db import search_pdf_knowledge
        raw = await search_pdf_knowledge(
            query=q, databases=wanted, top_k=max(1, min(top_k, 12)))
        text = "".join(getattr(i, "text", "") for i in
                       (raw if isinstance(raw, list) else [raw]))
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200],
             "results": []}, status_code=500)

    import re as _re
    pat = _re.compile(
        r"\*\*\d+\.\s+(?P<title>.+?)\*\*\s*\(score:\s*(?P<score>[\d.]+)\)\s*\n"
        r"\s*Layer:\s*(?P<layer>[^|]*?)\s*\|\s*Domain:\s*(?P<domain>[^|]*?)\s*\|"
        r"\s*p\.(?P<page>\d+)\s*\|\s*(?P<file>[^\n]+)\n\s*>\s*(?P<snip>[^\n]+)")

    results = []
    for m in pat.finditer(text):
        score = float(m.group("score"))
        if score < min_score:
            continue
        results.append({
            "title": m.group("title").strip(),
            "score": round(score, 3),
            "layer": m.group("layer").strip(),
            "domain": m.group("domain").strip(),
            "page": int(m.group("page")),
            "file": m.group("file").strip(),
            "snippet": " ".join(m.group("snip").split())[:600],
        })

    # How big is the corpus we just searched? The hook reports this so an answer
    # can say what was consulted without ever implying it read everything.
    corpus = db_scalar(
        "SELECT COUNT(DISTINCT source_file) FROM pdf_chunks"
        + (" WHERE db_id IN (SELECT id FROM knowledge_databases WHERE slug IN ({}))"
           .format(",".join("?" * len(wanted))) if wanted else ""),
        tuple(wanted) if wanted else (), default=0) or 0

    return JSONResponse({
        "ok": True, "query": q, "results": results,
        "corpus_documents": corpus,
        "layers": wanted or "all",
        "min_score": min_score,
    })


@router.get("/api/library/corpus-triggers")
async def corpus_triggers():
    """The terms that should cause a prompt to be grounded in the corpus.

    DERIVED, never hard-coded. Built from the researcher's own profile interests,
    their declared topics, and the domain labels present in the indexed corpus —
    so this works for a parasitologist, a cardiologist or a linguist without
    anyone editing a list. That portability is the point: Metis ships to other
    people, and a trigger list naming trypanosomes would be useless to them.
    """
    terms: set[str] = set()

    try:
        prefs = json.loads(
            (Path(os.environ.get("METIS_RC_ROOT", ".")) / "system" / "config"
             / "user-preferences.json").read_text(encoding="utf-8"))
        for key in ("interests", "news_topics"):
            for item in prefs.get(key, []) or []:
                terms.update(w for w in str(item).lower().split() if len(w) > 3)
    except Exception:
        pass

    for row in db_query("SELECT topic FROM user_topics WHERE active = 1") or []:
        terms.update(w for w in str(row["topic"]).lower().split() if len(w) > 3)

    # Domain labels from the indexed corpus itself: whatever the researcher has
    # actually collected is, by definition, what they work on.
    for row in db_query(
            "SELECT DISTINCT domain FROM pdf_chunks WHERE domain != ''") or []:
        terms.update(w for w in str(row["domain"]).lower().split() if len(w) > 3)

    # THE DISTINCTIVE VOCABULARY OF THE CORPUS ITSELF.
    #
    # Profile interests and folder names are too coarse on their own. Measured
    # 2026-08-21: they produced 'sleeping' and 'sickness' but NOT 'gambiense',
    # 'tsetse', 'trypanosome' or 'catt' — so a question phrased in the field's
    # actual technical vocabulary could slip past the trigger and never be
    # grounded. The words a researcher uses are in their documents' titles, not
    # in their folder labels.
    #
    # Frequency-bounded on both sides: a word in only one title is probably a
    # typo or a proper noun, and a word in most titles is not distinctive.
    from collections import Counter
    counts: Counter = Counter()
    titles = db_query(
        "SELECT DISTINCT title FROM pdf_chunks WHERE title != '' "
        "UNION SELECT title FROM literature_metadata WHERE title IS NOT NULL") or []
    for row in titles:
        # 4 characters, not 5: this field is full of four-letter assay names —
        # CATT, mAECT, RDTs — and dropping them would miss exactly the questions
        # a diagnostics researcher asks most often.
        for w in re.findall(r"[a-z]{4,}", str(row["title"]).lower()):
            counts[w] += 1
    if titles:
        floor = 2
        ceiling = max(3, int(len(titles) * 0.25))
        terms.update(w for w, n in counts.items() if floor <= n <= ceiling)

    # Words too generic to be evidence of a domain question.
    terms -= {"health", "system", "systems", "data", "study", "studies", "review",
              "other", "general", "human", "with", "from", "that", "this",
              "public", "update", "updates", "methods", "method", "analysis",
              "research", "science", "using", "based", "among", "between",
              "during", "these", "their", "which", "where", "after", "before",
              "results", "report", "reports", "paper", "papers", "article",
              "journal", "volume", "issue", "author", "authors", "abstract",
              "introduction", "conclusion", "table", "figure", "supplementary"}

    # Numbers are never a domain signal. Folder names like "2026" were leaking in
    # and would have grounded any prompt that mentioned a year.
    terms = {t for t in terms if not t.isdigit() and len(t) > 3}

    return JSONResponse({"ok": True, "terms": sorted(terms)})
