"""routers/presentation.py — the Presentation surface.

WHAT THIS REPLACED, AND WHY. The Teach tab built courses from scratch: an intake
form, past builds, knowledge-base statistics, a question bank. That is a real
job, but it is not the one that comes up most weeks — which is assembling a
training or a talk out of material that already exists — and it duplicates work
that already has a home on Learning. Meanwhile nothing in the dashboard knew
that eight hundred decks existed.

THE QUESTION THE SURFACE ANSWERS. Not "where is the file" — the folders answer
that. It is: what have we already said about this, to whom, and how did we say
it differently last time. That question needs the same lesson recognised across
the collections it was delivered in, which is why `decks.lesson_key` exists and
why the lineage view is the centre of the surface rather than a feature on it.

THREE TABS, ONE QUESTION.
    Repository   everything delivered, by collection, with lineage
    Templates    the master slides, as named styles
    Builder      the next deck: a style, a starting point, a hand-off

WHAT THE SCANNER OWNS AND WHAT THE PERSON OWNS. The scanner writes path, name,
collection, event, slide count, style and size. Author, language register,
audience and what changed about a delivery are written here, by hand, and the
scanner's upsert names its own columns so a rescan cannot erase them. Those four
fields are the whole value of the index — they are the ones no file can tell you.
"""
from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates"))

# A delivery is a deck that was actually given. Snapshots kept beside a deck and
# copies on portable media are indexed — they are real work and sometimes what
# you want — but counting them as deliveries would put one lesson in the lineage
# four times, and the lineage count is the number this surface exists to produce.
LIVE = "COALESCE(variant,'') = ''"

REGISTERS = ["technical", "simplified", "lay"]


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _overview() -> dict:
    """The counts across the top. Every one is a count of rows in `decks`."""
    total = db_scalar("SELECT COUNT(*) FROM decks", default=0) or 0
    live = db_scalar(f"SELECT COUNT(*) FROM decks WHERE {LIVE}", default=0) or 0
    lessons = db_scalar(
        f"SELECT COUNT(*) FROM (SELECT lesson_key FROM decks WHERE {LIVE} "
        f"AND COALESCE(lesson_key,'') != '' GROUP BY lesson_key)", default=0) or 0
    # The one worth knowing: a lesson that exists in more than one collection has
    # been re-pitched for a different room, and the difference is the asset.
    redelivered = db_scalar(
        f"SELECT COUNT(*) FROM (SELECT lesson_key FROM decks WHERE {LIVE} "
        f"AND COALESCE(lesson_key,'') != '' GROUP BY lesson_key "
        f"HAVING COUNT(DISTINCT collection) > 1)", default=0) or 0
    return {
        "total": total, "live": live, "lessons": lessons,
        "redelivered": redelivered,
        "masters": db_scalar("SELECT COUNT(*) FROM decks WHERE is_master = 1",
                             default=0) or 0,
        "events": db_scalar(
            f"SELECT COUNT(DISTINCT event) FROM decks WHERE {LIVE} "
            f"AND COALESCE(event,'') != ''", default=0) or 0,
        "described": db_scalar(
            f"SELECT COUNT(*) FROM decks WHERE {LIVE} AND ("
            f"COALESCE(register,'') != '' OR COALESCE(audience,'') != '' "
            f"OR COALESCE(changed_note,'') != '')", default=0) or 0,
        "scanned_at": (db_scalar("SELECT MAX(scanned_at) FROM decks",
                                 default="") or "")[:16],
    }


@router.get("/tab/presentation", response_class=HTMLResponse)
@router.get("/api/tab/presentation", response_class=HTMLResponse)
async def presentation_tab(request: Request):
    return templates.TemplateResponse(
        request, "presentation.html",
        {"active_tab": "presentation", "ov": _overview()})


# ── Repository ───────────────────────────────────────────────────────────────
@router.get("/api/partial/presentation/repository", response_class=HTMLResponse)
async def repository(request: Request, q: str = "", collection: str = ""):
    collections = db_query(
        f"SELECT COALESCE(collection,'(unfiled)') AS name, COUNT(*) AS n, "
        f"       MAX(modified_at) AS latest "
        f"FROM decks WHERE {LIVE} GROUP BY collection "
        f"ORDER BY n DESC", default=[]) or []

    where, params = [LIVE], []
    if q.strip():
        where.append("(LOWER(title) LIKE ? OR LOWER(rel_path) LIKE ?)")
        params += [f"%{q.strip().lower()}%"] * 2
    if collection:
        where.append("COALESCE(collection,'') = ?")
        params.append(collection)
    decks = db_query(
        "SELECT deck_id, title, collection, event, slide_count, style, "
        "       COALESCE(register,'') AS register, COALESCE(author,'') AS author, "
        "       modified_at, lesson_key "
        "FROM decks WHERE " + " AND ".join(where) +
        " ORDER BY modified_at DESC LIMIT 60", tuple(params), default=[]) or []

    # Lessons delivered more than once, newest first. This is the lineage list:
    # each row is one lesson and the collections it has been given in.
    lineage = db_query(
        f"SELECT lesson_key, MAX(title) AS title, COUNT(*) AS n, "
        f"       COUNT(DISTINCT collection) AS n_col, MAX(modified_at) AS latest, "
        f"       GROUP_CONCAT(DISTINCT collection) AS cols "
        f"FROM decks WHERE {LIVE} AND COALESCE(lesson_key,'') != '' "
        f"GROUP BY lesson_key HAVING n_col > 1 "
        f"ORDER BY n_col DESC, latest DESC LIMIT 40", default=[]) or []

    return templates.TemplateResponse(
        request, "partials/presentation_repository.html",
        {"collections": collections, "decks": decks, "lineage": lineage,
         "q": q, "collection": collection, "ov": _overview()})


@router.get("/api/partial/presentation/lesson", response_class=HTMLResponse)
async def lesson(request: Request, key: str):
    """One lesson, and every time it was delivered.

    The deliveries are shown side by side because the comparison IS the feature:
    next time you teach somewhere new, the question is never "where is the deck",
    it is "which of these is closest to this room, and what did I change last
    time I moved between those two".
    """
    rows = db_query(
        f"SELECT deck_id, title, rel_path, collection, event, slide_count, "
        f"       COALESCE(style,'') AS style, COALESCE(author,'') AS author, "
        f"       COALESCE(register,'') AS register, COALESCE(audience,'') AS audience, "
        f"       COALESCE(changed_note,'') AS changed_note, modified_at "
        f"FROM decks WHERE lesson_key = ? AND {LIVE} "
        f"ORDER BY modified_at ASC", (key,), default=[]) or []
    if not rows:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request, "partials/presentation_lesson.html",
        {"key": key, "title": rows[-1]["title"], "deliveries": rows,
         "registers": REGISTERS})


@router.post("/api/presentation/deck", response_class=HTMLResponse)
async def edit_deck(request: Request, deck_id: str = Form(...),
                    key: str = Form(""), author: str = Form(""),
                    register: str = Form(""), audience: str = Form(""),
                    changed_note: str = Form("")):
    """The four fields no file can tell you.

    Written straight through; a rescan cannot erase them because the scanner's
    upsert lists the columns it owns and these are not among them.
    """
    db_execute(
        "UPDATE decks SET author=?, register=?, audience=?, changed_note=? "
        "WHERE deck_id=?",
        (author.strip(), register.strip(), audience.strip(),
         changed_note.strip(), deck_id))
    return await lesson(request, key=key)


# ── Templates: master slides as named styles ─────────────────────────────────
# The two that exist on disk are seeded from what the scanner found, so the list
# cannot claim a master the library does not have. The rest are PROPOSED and say
# so — a style with no file behind it is a suggestion, and presenting it as
# available is how someone ends up looking for a template that was never made.
PROPOSED_STYLES = [
    ("workshop", "Workshop", "Participatory. Big type, few words, built to be "
     "argued with in a room.", 30),
    ("lecture", "Institutional lecture", "Branded, academic register, for "
     "teaching and seminars.", 40),
    ("conference", "Conference talk", "Twelve minutes. One idea a slide, "
     "figure-led, no bullet lists.", 50),
    ("neutral", "Partner neutral", "Unbranded, for work delivered with a "
     "ministry or an NGO, where no logo should lead.", 60),
]


def _sync_styles() -> None:
    """Every master the scanner found becomes a style; the proposals fill the gaps.

    READS FIRST, WRITES ONLY ON A DIFFERENCE. This runs whenever the Templates or
    Builder tab is opened, and an unconditional UPDATE there would take a write
    transaction on a render path — on WAL that is an exclusive lock, taken
    several times, every time someone looks at a tab. Once the styles match the
    masters this function does nothing at all, which is the common case.
    """
    have = {r["style_id"]: r for r in db_query(
        "SELECT style_id, master_path, state FROM deck_styles", default=[]) or []}

    for r in db_query("SELECT title, rel_path, style FROM decks WHERE is_master = 1",
                      default=[]) or []:
        name = (r["style"] or r["title"] or "").strip()
        if not name:
            continue
        sid = name.lower().replace(" ", "-")[:40]
        row = have.get(sid)
        if row is None:
            db_execute(
                "INSERT INTO deck_styles (style_id, name, description, "
                "master_path, state, sort_order) VALUES (?,?,?,?,'on-disk',?)",
                (sid, name, "", r["rel_path"], 10))
        elif row["master_path"] != r["rel_path"] or row["state"] != "on-disk":
            db_execute("UPDATE deck_styles SET master_path=?, state='on-disk' "
                       "WHERE style_id=?", (r["rel_path"], sid))

    for sid, name, desc, order in PROPOSED_STYLES:
        if sid not in have:
            db_execute(
                "INSERT INTO deck_styles (style_id, name, description, "
                "master_path, state, sort_order) VALUES (?,?,?,'','proposed',?)",
                (sid, name, desc, order))


@router.get("/api/partial/presentation/templates", response_class=HTMLResponse)
async def styles_partial(request: Request):
    _sync_styles()
    rows = db_query(
        "SELECT style_id, name, description, master_path, state, sort_order "
        "FROM deck_styles ORDER BY sort_order, name", default=[]) or []
    # How many decks already follow each style — the number that tells you
    # whether a style is a convention or an aspiration.
    for r in rows:
        r["n_decks"] = db_scalar(
            f"SELECT COUNT(*) FROM decks WHERE {LIVE} AND LOWER(COALESCE(style,'')) = ?",
            (r["name"].lower(),), default=0) or 0
    return templates.TemplateResponse(
        request, "partials/presentation_templates.html", {"styles": rows})


@router.post("/api/presentation/style", response_class=HTMLResponse)
async def edit_style(request: Request, style_id: str = Form(...),
                     description: str = Form("")):
    db_execute("UPDATE deck_styles SET description = ? WHERE style_id = ?",
               (description.strip(), style_id))
    return await styles_partial(request)


# ── Builder ──────────────────────────────────────────────────────────────────
@router.get("/api/partial/presentation/builder", response_class=HTMLResponse)
async def builder(request: Request):
    _sync_styles()
    return templates.TemplateResponse(
        request, "partials/presentation_builder.html",
        {"styles": db_query("SELECT style_id, name, state, master_path "
                            "FROM deck_styles ORDER BY sort_order, name",
                            default=[]) or [],
         "collections": db_query(
             f"SELECT DISTINCT collection AS name FROM decks WHERE {LIVE} "
             f"AND COALESCE(collection,'') != '' ORDER BY collection",
             default=[]) or [],
         "recent": db_query(
             f"SELECT deck_id, title, collection, slide_count FROM decks "
             f"WHERE {LIVE} ORDER BY modified_at DESC LIMIT 12", default=[]) or []})


@router.post("/api/presentation/brief")
async def builder_brief(request: Request, topic: str = Form(""),
                        style_id: str = Form(""), source_deck: str = Form(""),
                        audience: str = Form(""), register: str = Form(""),
                        collection: str = Form("")):
    """Hand the next deck to Claude with the style already decided.

    Returns text, not a file. Metis has no model and does not make slides; what
    it can do — and what a chat window cannot — is say WHICH master, WHICH deck
    to start from and what was changed the last two times the lesson was given.
    Passing that across is the difference between a style being an instruction
    and a style being a hope.
    """
    style = (db_query("SELECT name, master_path, state FROM deck_styles "
                      "WHERE style_id = ?", (style_id,), default=[]) or [{}])
    style = style[0] if style else {}
    src = (db_query("SELECT title, rel_path, slide_count, lesson_key "
                    "FROM decks WHERE deck_id = ?", (source_deck,),
                    default=[]) or [{}])
    src = src[0] if src else {}

    prior = []
    if src.get("lesson_key"):
        prior = db_query(
            f"SELECT collection, slide_count, COALESCE(register,'') AS register, "
            f"       COALESCE(audience,'') AS audience, "
            f"       COALESCE(changed_note,'') AS changed_note "
            f"FROM decks WHERE lesson_key = ? AND {LIVE} ORDER BY modified_at",
            (src["lesson_key"],), default=[]) or []

    lines = [f"Build a presentation: {topic or src.get('title') or 'untitled'}."]
    if style.get("name"):
        lines.append(
            f"Style: {style['name']}."
            + (f" Master slides: {style['master_path']}."
               if style.get("master_path") else
               " No master exists for this style yet — propose one.")
        )
    if src.get("rel_path"):
        lines.append(f"Start from: {src['rel_path']} "
                     f"({src.get('slide_count') or '?'} slides).")
    if audience:
        lines.append(f"Audience: {audience}.")
    if register:
        lines.append(f"Language register: {register}.")
    if collection:
        lines.append(f"File it in: {collection}.")
    if len(prior) > 1:
        lines.append("")
        lines.append("This lesson has been delivered before. What changed each time:")
        for p in prior:
            bits = [p["collection"] or "—", f"{p['slide_count']} slides"]
            if p["register"]:
                bits.append(p["register"])
            if p["audience"]:
                bits.append(p["audience"])
            lines.append("  · " + " · ".join(bits)
                         + (f" — {p['changed_note']}" if p["changed_note"] else ""))
    return JSONResponse({"status": "ok", "brief": "\n".join(lines),
                         "n_prior": len(prior)})


@router.post("/api/presentation/rescan")
async def rescan(request: Request):
    """Run the scanner. Kept as a request rather than a schedule on purpose.

    Walking a large synced folder takes minutes and is I/O the machine notices.
    It is also not urgent: decks do not change while you are reading about them.
    """
    import subprocess
    import sys
    root = Path(__file__).resolve().parent.parent.parent.parent
    script = root / "tools" / "scan_decks.py"
    if not script.exists():
        return JSONResponse({"status": "error",
                             "message": "The deck scanner is not installed."})
    try:
        p = subprocess.run([sys.executable, str(script), "--apply"],
                           capture_output=True, text=True, timeout=900)
        return JSONResponse({"status": "ok" if p.returncode == 0 else "error",
                             "message": (p.stdout or p.stderr or "").strip()[-600:]})
    except subprocess.TimeoutExpired:
        return JSONResponse({"status": "error",
                             "message": "The scan did not finish within 15 minutes."})
