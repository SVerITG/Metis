"""
routers/learning.py — Learning tab routes.
"""

import datetime
import json
import logging
import os
import re
from pathlib import Path

import markdown as _md
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar, db_execute

_RC_ROOT = Path(os.environ.get("METIS_RC_ROOT", Path(__file__).parents[4]))
_COURSES_DIR = _RC_ROOT / "knowledge" / "courses"

_md_renderer = _md.Markdown(extensions=["fenced_code", "tables", "nl2br"])


# ---------------------------------------------------------------------------
# Lesson links
# ---------------------------------------------------------------------------

_LINKIFY_SKIP = re.compile(r"(<a\b[^>]*>.*?</a>|<code\b[^>]*>.*?</code>|<pre\b[^>]*>.*?</pre>|<[^>]+>)", re.S | re.I)
_LINKIFY_URL = re.compile(r"""(?<![\w@/])(
      https?://[^\s<>"'()\[\]]+[^\s<>"'()\[\].,;:!?]
    | www\.[^\s<>"'()\[\]]+[^\s<>"'()\[\].,;:!?]
    | doi:\s*10\.\d{4,9}/[^\s<>"'()\[\],;]+
)""", re.X | re.I)


def _linkify(html: str) -> str:
    """Turn plain-text URLs and DOIs in rendered lesson HTML into real links.

    Reading lists were written as prose — "doi:10.1126/science.aax2342",
    "https://alliblk.github.io/genepi-book/" — and Python-Markdown does not
    autolink anything that is not already `[text](url)` or `<url>`. So every
    source in every reading list rendered as dead text. Authors will keep
    writing them that way, so this is fixed at render time rather than by
    editing prose.

    Only unambiguous forms are linked: an explicit scheme, a `www.` host, or a
    `doi:` prefix. Bare hostnames like "pathoplexus.org" are deliberately NOT
    matched — the false-positive rate on ordinary prose ("Fig. 2", "et al.",
    abbreviations) is not worth it, and an author who wants that link can write
    it properly.

    Anything already inside an <a>, <code> or <pre>, and every tag's own
    attributes, is left alone — those regions are split out first, so a href
    can never be rewritten into itself.
    """
    def link(m: "re.Match[str]") -> str:
        raw = m.group(1)
        if raw.lower().startswith("doi:"):
            doi = raw.split(":", 1)[1].strip()
            href = f"https://doi.org/{doi}"
        elif raw.lower().startswith("www."):
            href = f"https://{raw}"
        else:
            href = raw
        return (f'<a href="{href}" target="_blank" rel="noopener noreferrer">{raw}</a>')

    out = []
    for i, part in enumerate(_LINKIFY_SKIP.split(html)):
        # split() with one capturing group alternates text / delimiter,
        # so odd indices are the protected regions and go through untouched.
        out.append(part if i % 2 else _LINKIFY_URL.sub(link, part))
    return "".join(out)




_DEEP_DIVE_SECTION = "Deep dives"


def _load_methodologies(slug: str) -> list[dict]:
    """Generalised method recipes extracted from published analyses.

    Optional per course: a course with no methodologies.json simply does not
    show the tab. The file is a sibling of lessons.json rather than a section
    inside it, because a methodology is not a lesson — it has no order, no
    completion state and no place in a reading sequence.
    """
    p = _COURSES_DIR / slug / "methodologies.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("methodologies", []) or []
    except Exception:
        return []


def _course_tabs(slug: str) -> list[dict]:
    """Which tabs this course actually has. Nothing is shown that is empty."""
    lessons = _load_lessons_json(slug).get("lessons", []) or []
    tabs = []
    if any(l.get("section") != _DEEP_DIVE_SECTION for l in lessons):
        tabs.append({"id": "course", "label": "Course"})
    if any(l.get("section") == _DEEP_DIVE_SECTION for l in lessons):
        tabs.append({"id": "deepdives", "label": "Deep dives"})
    if _load_methodologies(slug):
        tabs.append({"id": "methodology", "label": "Methodology"})
    return tabs

_CALLOUT = re.compile(r"<p>(\s*)(⚠|✱)\s*", re.U)


def _enrich_lesson_html(html: str) -> str:
    """Give the rendered lesson the structure its CSS needs.

    Three things markdown cannot express and the course content relies on:

    1. Links. See _linkify.
    2. Callouts. The lessons mark warnings with "⚠" and asides with "✱" at the
       start of a paragraph — 281 of them across the two written courses. CSS
       cannot select on text content, so the marker is converted into a class
       here and the glyph kept as the visual bullet.
    3. Wide tables. There are 462 table rows in these courses and several are
       far wider than the reading measure. Without a scroll container they
       either overflow the column or force the whole page to scroll sideways.
    """
    html = _linkify(html)
    html = _CALLOUT.sub(lambda m: f'<p class="cx cx--{"warn" if m.group(2) == "⚠" else "note"}">', html)
    html = html.replace("<table>", '<div class="lesson-tablewrap"><table>')
    html = html.replace("</table>", "</table></div>")
    return html

router = APIRouter()
_log = logging.getLogger(__name__)
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


# ── One-time data migrations (idempotent) ────────────────────────────────────
def _run_learning_migrations() -> None:
    """Fix legacy data on startup. Each migration is idempotent."""
    try:
        # Rename "Multilevel Analysis Course" → "Statistics for Epidemiology"
        # and fix the slug to match the filesystem (knowledge/courses/statistics/)
        db_execute(
            "UPDATE learning_courses SET title='Statistics for Epidemiology', "
            "slug='statistics', category='statistics' "
            "WHERE title IN ('Multilevel Analysis Course', 'Statistics for Epidemiology') "
            "AND slug='multilevel-analysis-course'"
        )
    except Exception:
        pass

    # Ensure updated_at column exists (added after initial schema)
    try:
        db_execute("ALTER TABLE learning_courses ADD COLUMN updated_at TEXT")
    except Exception:
        pass

    # Ensure reviewed_at column exists on spaced_repetition
    try:
        db_execute("ALTER TABLE spaced_repetition ADD COLUMN reviewed_at TEXT")
    except Exception:
        pass


    # Which course the Today surface shows. A column rather than a new table: it
    # is one value per course and the "focused" one is simply the row with a 1.
    # Added here because CREATE TABLE / ALTER on a render path takes a WAL write
    # lock and blocks every other writer.
    try:
        db_execute("ALTER TABLE learning_courses ADD COLUMN focused_today INTEGER DEFAULT 0")
    except Exception:
        pass

    # Remove duplicate course ideas (keep lowest id for each title)
    try:
        db_execute(
            "DELETE FROM learning_courses WHERE id NOT IN "
            "(SELECT MIN(id) FROM learning_courses GROUP BY title, status)"
        )
    except Exception:
        pass


_run_learning_migrations()


def _streak_cells(days: int = 40) -> list[dict]:
    """Return a real review-activity map for the last `days` days.

    Each cell: {"date": iso, "active": bool, "is_today": bool}. Driven by
    spaced_repetition.reviewed_at — no hardcoded placeholder data.
    """
    today = datetime.date.today()
    active_days: set[str] = set()
    try:
        rows = db_query(
            "SELECT DISTINCT date(reviewed_at) AS d FROM spaced_repetition "
            "WHERE reviewed_at IS NOT NULL AND reviewed_at != ''"
        )
        active_days = {r["d"] for r in (rows or []) if r.get("d")}
    except Exception:
        active_days = set()
    cells = []
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        iso = d.isoformat()
        cells.append({"date": iso, "active": iso in active_days, "is_today": i == 0})
    return cells


def _learning_context(active_tab: str = "learning") -> dict:
    cells = _streak_cells()
    return {
        "active_tab": active_tab,
        "streak_cells": cells,
        "streak_has_data": any(c["active"] for c in cells),
        # The streak panel used to say "No reviews yet" while 234 cards
        # were overdue. It meant "you have not reviewed", but it READ as
        # "there is nothing to review" — an empty state describing an
        # empty world rather than an untouched one. It needs the count to
        # say the true thing.
        "streak_waiting": int(db_scalar(
            "SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= date('now')",
            default=0) or 0),
    }


@router.get("/tab/learning", response_class=HTMLResponse)
async def learning_tab(request: Request):
    return templates.TemplateResponse(request, "learning.html", _learning_context())


@router.get("/api/tab/learning", response_class=HTMLResponse)
async def learning_tab_partial(request: Request):
    return templates.TemplateResponse(request, "learning.html", _learning_context())


@router.get("/course/{slug}", response_class=HTMLResponse)
async def course_reader_page(slug: str, request: Request):
    """Standalone course reader — opens in its own browser tab.

    The 'statistics' course is a full Quarto site mounted as static files
    at /course/statistics/. Redirect there so the mount handles it.
    """
    if slug == "statistics":
        return RedirectResponse("http://127.0.0.1:3000/", status_code=302)
    course = db_query(
        "SELECT title FROM learning_courses WHERE slug=? LIMIT 1",
        (slug,), default=[],
    )
    title = course[0]["title"] if course else slug.replace("-", " ").title()

    # ?lesson=<id> opens that lesson directly. Today's "Continue" links here, and
    # landing on the course index instead would make you find your place again —
    # which is the whole thing that link exists to save. Resolved server-side so
    # the correct tab is lit on first paint rather than after a flash.
    want = (request.query_params.get("lesson") or "").strip()
    initial_lesson, initial_tab = "", ""
    if want:
        lessons = _load_lessons_json(slug).get("lessons") or []
        match = next((l for l in lessons if l.get("id") == want), None)
        if match:
            initial_lesson = want
            initial_tab = ("deepdives" if match.get("section") == _DEEP_DIVE_SECTION
                           else "course")

    return templates.TemplateResponse(
        request,
        "course_reader.html",
        {"tabs": _course_tabs(slug), "slug": slug, "course_title": title,
         "initial_lesson": initial_lesson, "initial_tab": initial_tab},
    )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/meta", response_class=HTMLResponse)
async def learning_meta(request: Request):
    # "Courses" means courses you can open. Ideas are counted separately —
    # calling an idea a course made the surface claim 12 when 7 were real.
    total = db_scalar(
        "SELECT COUNT(*) FROM learning_courses WHERE status IN ('active','in_progress','building')",
        default=0,
    ) or 0
    ideas = db_scalar("SELECT COUNT(*) FROM learning_courses WHERE status='idea'", default=0) or 0
    today = str(datetime.date.today())
    due = db_scalar("SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= ?", (today,), default=0) or 0
    return HTMLResponse(f"{total} COURSES · {ideas} IDEAS · {due} DUE")


# ---------------------------------------------------------------------------
# Launch targets — one button, guaranteed to open the actual course
# ---------------------------------------------------------------------------

# Courses delivered by their own app rather than by this dashboard.
# (mlm-app is an Express application, so it cannot be served as static files.)
_EXTERNAL_APPS: dict[str, str] = {
    "statistics": "http://127.0.0.1:3000/",
}

# Courses whose rendered static site is mounted by main.py at /coursesite/<key>.
_MOUNTED_SITES: dict[str, str] = {
    "hat-diagnostics": "/coursesite/hat-diagnostics/",
    "hat-history": "/coursesite/hat-history/",
}


def _launch_target(slug: str, course_url: str | None) -> str:
    """The single URL a course's Open button uses. Never a repo, never a file path.

    Launch targets used to come straight from the `course_url` column, so
    whatever happened to be stored got opened: one course pointed at a GitHub
    repository, another at a bare filesystem path ("knowledge/courses/…") that
    resolved to a 404. A course card's Open button must open the course, so the
    value is validated here rather than trusted, and the template gets one
    already-checked URL.

    Order of preference:
      1. a course delivered by its own app  -> that app
      2. a rendered site mounted by main.py -> that mount
      3. a stored course_url that is genuinely a course target
      4. the in-app markdown reader
    """
    if slug in _EXTERNAL_APPS:
        return _EXTERNAL_APPS[slug]
    if slug in _MOUNTED_SITES:
        return _MOUNTED_SITES[slug]

    url = (course_url or "").strip()
    if url:
        low = url.lower()
        # Source repositories and issue trackers are not the course.
        bad_host = any(h in low for h in (
            "github.com", "gitlab.com", "bitbucket.org", "docs.google.com",
            "dropbox.com", "onedrive", "sharepoint",
        ))
        # A same-origin path, or an explicitly local server, is acceptable.
        ok_shape = url.startswith("/") or low.startswith((
            "http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost",
        ))
        if ok_shape and not bad_host:
            return url
        # Anything else — a bare relative path like "knowledge/courses/x/", a
        # remote host, a file:// URL — is not launched. Fall through.

    return f"/course/{slug}"


@router.get("/api/partial/learning/nav-meta", response_class=HTMLResponse)
async def learning_nav_meta(request: Request):
    """Tiny badge for the sidebar: how many cards are waiting.

    Every nav item shipped with a hardcoded "—", so the sidebar carried no
    information at all. This is the Learning one.
    """
    today = str(datetime.date.today())
    due = db_scalar(
        "SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= ?", (today,), default=0
    ) or 0
    if not due:
        n = db_scalar(
            "SELECT COUNT(*) FROM learning_courses "
            "WHERE status IN ('active','in_progress','building')", default=0
        ) or 0
        return HTMLResponse(f"{n} courses" if n else "—")
    return HTMLResponse(f"{due} due")


@router.get("/api/partial/learning/courses-archive", response_class=HTMLResponse)
async def learning_courses_archive(request: Request):
    courses = db_query(
        "SELECT id, title, category, progress_pct, total_modules, completed_modules, status, slug, "
        "project_id, current_lesson, next_lesson, course_url, lesson_notes "
        "FROM learning_courses WHERE status IN ('active','in_progress','building','paused') "
        # Paused courses sort LAST. They are here so that stopping one on Today
        # is reversible — a status no query selected would have made the course
        # vanish with its progress and no way back — but they are not what this
        # surface is for, so they sit under the courses you are still taking.
        "ORDER BY CASE status WHEN 'building' THEN 0 WHEN 'paused' THEN 2 ELSE 1 END, "
        "         progress_pct DESC, id DESC LIMIT 24"
    ) or []
    # Was LIMIT 6. With 7 active courses one vanished with no indicator, and
    # because every course sat at 0% which one vanished was arbitrary. If the
    # cap is ever hit again, say so rather than truncating silently.
    n_active = db_scalar(
        "SELECT COUNT(*) FROM learning_courses WHERE status IN ('active','in_progress','building')",
        default=0,
    ) or 0
    truncated = max(0, n_active - len(courses))

    for _c in courses:
        _c["launch_url"] = _launch_target(_c.get("slug") or "", _c.get("course_url"))

    # Annotate building courses with their pipeline step from course_builds
    for c in courses:
        if c.get("status") == "building" and c.get("slug"):
            try:
                build = db_query(
                    "SELECT step, status as build_status FROM course_builds WHERE slug=? LIMIT 1",
                    (c["slug"],), default=[],
                )
                if build:
                    c["build_step"] = build[0].get("step", 1)
                    c["build_status"] = build[0].get("build_status", "intake")
                else:
                    c["build_step"] = 1
                    c["build_status"] = "intake"
            except Exception:
                c["build_step"] = 1
                c["build_status"] = "intake"

    return templates.TemplateResponse(
        request,
        "partials/learning_courses.html",
        {"courses": courses, "truncated": truncated, "n_active": n_active},
    )


# ---------------------------------------------------------------------------
# Due for review today
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/due-today", response_class=HTMLResponse)
async def learning_due_today(request: Request):
    today = str(datetime.date.today())
    due = db_query(
        "SELECT sr_id as id, front_text as topic, source_table as course_title, "
        "next_review as next_review_date, interval_days "
        "FROM spaced_repetition WHERE next_review <= ? "
        "ORDER BY next_review LIMIT 10",
        (today,),
    )
    # A session, not a pile. 45 undifferentiated cards is not reviewable; ten is.
    # The remainder is reported, never hidden.
    total_due = db_scalar(
        "SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= ?", (today,), default=0
    ) or 0
    # How LATE each card is, in days. The row used to carry a flat "OVERDUE"
    # chip, which on real data appeared on 10 of 10 rows — a mark on every row
    # cannot rank rows, and ranking is the only thing the reader wants here
    # ("which of these have I been avoiding longest?"). A number varies, so it
    # informs; the word did not. 0 means due today, not late.
    today_d = datetime.date.today()
    for row in (due or []):
        try:
            row["days_late"] = max(
                0, (today_d - datetime.date.fromisoformat(str(row["next_review_date"])[:10])).days
            )
        except Exception:
            row["days_late"] = 0

    # Streak: consecutive calendar days with at least one completed review
    streak = _compute_streak()
    return templates.TemplateResponse(
        request,
        "partials/learning_due.html",
        {"due": due, "today": today, "streak": streak,
         "total_due": total_due, "remaining": max(0, total_due - len(due or []))},
    )


def _compute_streak() -> int:
    """Count consecutive days (backwards from today) where at least one card was reviewed."""
    rows = db_query(
        "SELECT DISTINCT date(reviewed_at) as d FROM spaced_repetition "
        "WHERE reviewed_at IS NOT NULL ORDER BY d DESC LIMIT 60",
        default=[],
    )
    if not rows:
        return 0
    reviewed_days = {r["d"] for r in rows}
    streak = 0
    check = datetime.date.today()
    while str(check) in reviewed_days:
        streak += 1
        check -= datetime.timedelta(days=1)
    return streak


# ── SPACED REPETITION, GATED ON WHAT YOU HAVE ACTUALLY READ ──────────────────
# Asked for 2026-09-04: a small box on Today drawing cards from the courses in
# progress, "for the content up until the point that you reached... Show 1 card,
# only show a next card when asked."
#
# The gate is the part that did not exist. A card's `source_id` IS its lesson
# ('lesson-01'), so eligibility is a join against `lesson_completions` — and
# measured on 2026-09-04 that yields ZERO of 226 course cards, because no lesson
# is marked complete yet. The Learning surface's "234 cards due" is the ungated
# count, which is why it disagrees. An empty box here is the honest answer and
# it says how to fill it, rather than quizzing on material never opened.
def _sm2(interval: int, ef: float, reps: int, quality: int) -> tuple[int, float, int, str]:
    """One implementation of the schedule. Two copies would drift apart."""
    if quality < 3:
        reps, interval = 0, 1
    else:
        interval = 1 if reps == 0 else (6 if reps == 1 else round(interval * ef))
        reps += 1
    ef = max(1.3, ef + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return interval, ef, reps, str(datetime.date.today() + datetime.timedelta(days=interval))


def _eligible_cards(limit: int = 1, exclude: str = "") -> list[dict]:
    """Cards from lessons the researcher has actually completed, due first."""
    today = str(datetime.date.today())
    rows = db_query(
        "SELECT s.sr_id, s.front_text, s.back_text, s.source_table AS slug, "
        "       s.source_id AS lesson, s.next_review, s.repetitions, "
        "       c.title AS course_title "
        "FROM spaced_repetition s "
        "JOIN lesson_completions lc "
        "  ON lc.course_slug = s.source_table AND lc.lesson_id = s.source_id "
        "LEFT JOIN learning_courses c ON c.slug = s.source_table "
        "WHERE s.next_review <= ? AND s.sr_id != ? "
        "ORDER BY s.next_review, s.repetitions LIMIT ?",
        (today, exclude or "\x00", limit), default=[]) or []
    return [dict(r) for r in rows]


def _eligible_count() -> tuple[int, int, int]:
    """(eligible now, total course cards, lessons completed) — always with its denominator."""
    today = str(datetime.date.today())
    elig = db_scalar(
        "SELECT COUNT(*) FROM spaced_repetition s JOIN lesson_completions lc "
        "ON lc.course_slug = s.source_table AND lc.lesson_id = s.source_id "
        "WHERE s.next_review <= ?", (today,), default=0) or 0
    total = db_scalar(
        "SELECT COUNT(*) FROM spaced_repetition WHERE source_table IN "
        "(SELECT slug FROM learning_courses WHERE slug IS NOT NULL)", default=0) or 0
    done = db_scalar("SELECT COUNT(*) FROM lesson_completions", default=0) or 0
    return elig, total, done


def _review_ctx(exclude: str = "") -> dict:
    cards = _eligible_cards(1, exclude)
    elig, total, done = _eligible_count()
    nxt = db_query(
        "SELECT slug, title, next_lesson FROM learning_courses "
        "WHERE status IN ('active','in_progress') AND COALESCE(next_lesson,'') != '' "
        "ORDER BY progress_pct DESC LIMIT 1", default=[]) or []
    return {"card": cards[0] if cards else None, "eligible": elig,
            "total_cards": total, "lessons_done": done,
            "start": dict(nxt[0]) if nxt else None}


@router.get("/api/partial/today/review", response_class=HTMLResponse)
async def today_review(request: Request):
    """One card, from a lesson already completed."""
    return templates.TemplateResponse(
        request, "partials/today_review.html", _review_ctx())


@router.post("/api/today/review/{sr_id}", response_class=HTMLResponse)
async def today_review_grade(sr_id: str, request: Request, quality: int = Form(4)):
    """Grade this card, then hand back the NEXT one — never before it is asked for."""
    row = db_query("SELECT interval_days, ease_factor, repetitions FROM spaced_repetition "
                   "WHERE sr_id=?", (sr_id,), default=[])
    if row:
        r = row[0]
        iv, ef, reps, nxt = _sm2(r["interval_days"] or 1, r["ease_factor"] or 2.5,
                                 r["repetitions"] or 0, max(0, min(5, quality)))
        db_execute("UPDATE spaced_repetition SET interval_days=?, ease_factor=?, "
                   "repetitions=?, next_review=?, reviewed_at=datetime('now') WHERE sr_id=?",
                   (iv, ef, reps, nxt, sr_id))
    return templates.TemplateResponse(
        request, "partials/today_review.html", _review_ctx(exclude=sr_id))


@router.get("/api/partial/today/review/next", response_class=HTMLResponse)
async def today_review_next(request: Request, after: str = ""):
    """Skip to the next card without grading this one."""
    return templates.TemplateResponse(
        request, "partials/today_review.html", _review_ctx(exclude=after))


@router.post("/api/learning/review/{sr_id}", response_class=HTMLResponse)
async def mark_review_done(sr_id: str, request: Request):
    """Mark a spaced-repetition card as reviewed and apply SM-2 scheduling."""
    data = await request.json()
    quality = int(data.get("quality", 4))  # 0-5; 4 = "got it"

    row = db_query(
        "SELECT interval_days, ease_factor, repetitions FROM spaced_repetition WHERE sr_id=?",
        (sr_id,),
        default=[],
    )
    if not row:
        return HTMLResponse("", status_code=404)

    r = row[0]
    interval = r["interval_days"] or 1
    ef = r["ease_factor"] or 2.5
    reps = r["repetitions"] or 0

    # SM-2 algorithm
    if quality < 3:
        reps = 0
        interval = 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        reps += 1
    ef = max(1.3, ef + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    next_review = str(datetime.date.today() + datetime.timedelta(days=interval))

    db_execute(
        "UPDATE spaced_repetition SET interval_days=?, ease_factor=?, repetitions=?, "
        "next_review=?, reviewed_at=datetime('now') WHERE sr_id=?",
        (interval, ef, reps, next_review, sr_id),
    )

    today = str(datetime.date.today())
    due = db_query(
        "SELECT sr_id as id, front_text as topic, source_table as course_title, "
        "next_review as next_review_date, interval_days "
        "FROM spaced_repetition WHERE next_review <= ? ORDER BY next_review LIMIT 20",
        (today,),
    )
    streak = _compute_streak()
    return templates.TemplateResponse(
        request, "partials/learning_due.html", {"due": due, "today": today, "streak": streak}
    )


# ---------------------------------------------------------------------------
# Active courses
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/courses", response_class=HTMLResponse)
async def learning_courses(request: Request):
    courses = db_query(
        "SELECT id, slug, title, category, progress_pct, total_modules, completed_modules, project_id, "
        "current_lesson, next_lesson, course_url, lesson_notes "
        "FROM learning_courses WHERE status = 'active' ORDER BY progress_pct DESC",
        default=[],
    )
    for _c in (courses or []):
        _c["launch_url"] = _launch_target(_c.get("slug") or "", _c.get("course_url"))

    return templates.TemplateResponse(
        request,
        "partials/learning_courses.html",
        {
            "courses": courses
        },
    )


# ---------------------------------------------------------------------------
# Recently completed
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/completed", response_class=HTMLResponse)
async def learning_completed(request: Request):
    items = db_query(
        "SELECT id, title, category, completed_at "
        "FROM learning_courses WHERE status = 'completed' "
        "ORDER BY completed_at DESC LIMIT 10",
        default=[],
    )
    return templates.TemplateResponse(
        request,
        "partials/learning_completed.html",
        {
            "items": items
        },
    )


# ---------------------------------------------------------------------------
# Placeholder courses (catalog to build)
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/placeholder-courses", response_class=HTMLResponse)
async def learning_placeholder_courses(request: Request):
    courses = db_query(
        "SELECT id, slug, title, category FROM learning_courses WHERE status = 'idea' ORDER BY category, title",
        default=[],
    )
    return templates.TemplateResponse(
        request,
        "partials/learning_ideas.html",
        {"courses": courses},
    )


# ---------------------------------------------------------------------------
# Course idea CRUD
# ---------------------------------------------------------------------------


@router.delete("/api/course/idea/{course_id}", response_class=HTMLResponse)
async def delete_course_idea(course_id: int, request: Request):
    db_execute("DELETE FROM learning_courses WHERE id=? AND status='idea'", (course_id,))
    # Return refreshed ideas list
    courses = db_query(
        "SELECT id, slug, title, category FROM learning_courses WHERE status = 'idea' ORDER BY category, title",
        default=[],
    )
    return templates.TemplateResponse(request, "partials/learning_ideas.html", {"courses": courses})


@router.post("/api/course/idea/add", response_class=HTMLResponse)
async def add_course_idea(request: Request):
    data = await request.form()
    title = (data.get("title") or "").strip()
    category = (data.get("category") or "general").strip()
    if not title:
        return HTMLResponse("<div class='error-msg' style='color:var(--m-danger);font-size:13px;padding:6px 0;'>Title is required.</div>")
    # Reject duplicate titles (case-insensitive) among ideas
    dup = db_scalar(
        "SELECT COUNT(*) FROM learning_courses WHERE LOWER(title)=LOWER(?) AND status='idea'",
        (title,), default=0,
    ) or 0
    if dup:
        return HTMLResponse(
            "<div class='error-msg' style='color:var(--m-danger);font-size:13px;padding:6px 0;'>"
            "A course idea with that title already exists.</div>"
        )
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    # Ensure slug uniqueness — loop until we find a free slug
    base_slug = slug
    suffix = 1
    while db_scalar("SELECT COUNT(*) FROM learning_courses WHERE slug=?", (slug,), default=0):
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    db_execute(
        "INSERT INTO learning_courses (title, slug, category, status, progress_pct, created_at) "
        "VALUES (?,?,?,'idea',0,datetime('now'))",
        (title, slug, category),
    )
    courses = db_query(
        "SELECT id, slug, title, category FROM learning_courses WHERE status = 'idea' ORDER BY category, title",
        default=[],
    )
    return templates.TemplateResponse(request, "partials/learning_ideas.html", {"courses": courses})


@router.post("/api/course/idea/{course_id}/update", response_class=HTMLResponse)
async def update_course_idea(course_id: int, request: Request):
    data = await request.form()
    title = (data.get("title") or "").strip()
    category = (data.get("category") or "general").strip()
    if title:
        db_execute(
            "UPDATE learning_courses SET title=?, category=? WHERE id=? AND status='idea'",
            (title, category, course_id),
        )
    courses = db_query(
        "SELECT id, slug, title, category FROM learning_courses WHERE status = 'idea' ORDER BY category, title",
        default=[],
    )
    return templates.TemplateResponse(request, "partials/learning_ideas.html", {"courses": courses})


@router.post("/api/course/{course_id}/update-progress", response_class=JSONResponse)
async def update_course_progress(course_id: int, request: Request):
    data = await request.json()
    fields, vals = [], []
    for col in ("current_lesson", "next_lesson", "course_url", "lesson_notes", "completed_modules", "progress_pct"):
        if col in data:
            fields.append(f"{col}=?")
            vals.append(data[col])
    if not fields:
        return JSONResponse({"status": "no_change"})
    vals.append(course_id)
    db_execute(f"UPDATE learning_courses SET {','.join(fields)} WHERE id=?", tuple(vals))
    return JSONResponse({"status": "ok"})


@router.post("/api/course/build-request")
async def course_build_request(request: Request):
    data = await request.json()
    course_id = data.get("courseId", "unknown")
    course = db_query(
        "SELECT id, slug, title, category FROM learning_courses WHERE id=? OR slug=? LIMIT 1",
        (course_id, course_id),
        default=[],
    )
    title = course[0]["title"] if course else course_id
    slug = course[0]["slug"] if course else course_id
    prompt = f"/course-builder\ncourse-slug: {slug}\nPlease walk me through the questionnaire at system/config/course-builder-questionnaire.md and build this course: {title}"
    return {"status": "ok", "prompt": prompt, "title": title}


@router.post("/api/course/build-idea")
async def course_build_idea(request: Request):
    """Generate a context-rich course-builder prompt for a course idea."""
    data = await request.json()
    slug = data.get("slug", "")
    title = data.get("title", slug)
    adaptive = data.get("adaptive", False)
    topic_hint = data.get("topicHint", "")
    research_question = data.get("researchQuestion", "").strip()

    mlm_ref = "Statistics for Epidemiology course (id=6, slug=statistics-full)"
    mlm_path = ""  # set via user-config.yaml: course_reference_path
    questionnaire = "system/config/course-builder-questionnaire.md"

    if adaptive:
        topic = topic_hint or title
        project_name = f"{topic} Course"
        rq_section = f"\nResearch question context:\n{research_question}\n" if research_question else ""
        prompt = (
            f"/course-builder\n"
            f"Project: {project_name}\n\n"
            f"Build an adaptive statistics course on: {topic}\n"
            f"{rq_section}"
            f"Use {mlm_ref} as the structural template.\n"
            f"MLM course reference files: {mlm_path}\n\n"
            f"Walk me through the questionnaire at {questionnaire} "
            f"and adapt the course specifically for \"{topic}\" — "
            f"same modular structure, learning objectives format, and spaced repetition design."
        )
    else:
        project_name = f"{title} Course"
        rq_section = f"\nResearch question context:\n{research_question}\n" if research_question else ""
        prompt = (
            f"/course-builder\n"
            f"Project: {project_name}\n\n"
            f"Build a new course: {title}\n"
            f"{rq_section}"
            f"Reference template: {mlm_ref}\n"
            f"MLM course reference files: {mlm_path}\n\n"
            f"Walk me through the questionnaire at {questionnaire} "
            f"and build this course following the same principles and structure."
        )

    return {"status": "ok", "prompt": prompt, "title": title, "slug": slug}


# ---------------------------------------------------------------------------
# Course wizard — build with intake
# ---------------------------------------------------------------------------


def _parse_duration(time_budget: str) -> int:
    """Map wizard time-budget labels to estimated hours."""
    return {"< 2 hours": 2, "1 weekend": 8, "1 month": 40, "open-ended": 0}.get(
        time_budget, 0
    )


def _generate_intake_prompt(slug: str, title: str, intake: dict) -> str:
    """Build a context-rich prompt from wizard intake answers."""
    mlm_ref = "Statistics for Epidemiology course (id=6, slug=statistics-full)"
    questionnaire = "system/config/course-builder-questionnaire.md"

    sections = [
        f"/course-builder",
        f"Project: {title} Course",
        "",
        "## Intake (completed via dashboard wizard)",
        "",
        f"**Title:** {title}",
        f"**Learner:** {intake.get('learner', 'yourself')}",
        f"**Prior level:** {intake.get('level', 'working')}",
        f"**Time budget:** {intake.get('time_budget', '1 weekend')}",
        f"**Scope:** {intake.get('scope', 'practical')}",
        f"**Format:** {intake.get('format', 'reading')}",
        f"**Tone:** {intake.get('tone', 'friendly')}",
        f"**Module length:** {intake.get('module_length', '30 min')}",
    ]

    includes = intake.get("includes", [])
    if includes:
        sections.append(f"**Include:** {', '.join(includes)}")

    questions = (intake.get("key_questions") or "").strip()
    if questions:
        sections += ["", "### Key questions", questions]

    materials = (intake.get("materials") or "").strip()
    if materials:
        sections += ["", "### Materials to import", materials]

    out_of_scope = (intake.get("out_of_scope") or "").strip()
    if out_of_scope:
        sections += ["", "### Out of scope", out_of_scope]

    sections += [
        "",
        "---",
        "",
        "The user has already completed the intake questionnaire via the dashboard wizard. "
        "Skip intake and proceed directly to **Step 2: Scope Plan**.",
        "",
        f"Reference template: {mlm_ref}",
        f"Questionnaire path: {questionnaire}",
    ]

    return "\n".join(sections)


@router.post("/api/course/build-with-intake")
async def course_build_with_intake(request: Request):
    """Wizard endpoint: save intake, set status to building, return prompt."""
    data = await request.json()
    title = (data.get("title") or "").strip()
    slug = (data.get("slug") or "").strip()
    intake = data.get("intake", {})

    if not title:
        return JSONResponse({"status": "error", "message": "Title is required."}, status_code=400)

    # Generate slug from title if not provided
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    # Check for existing build that isn't cancelled
    existing = db_query(
        "SELECT status FROM course_builds WHERE slug=? LIMIT 1",
        (slug,), default=[],
    )
    if existing and existing[0].get("status") not in (None, "", "cancelled", "intake"):
        return JSONResponse({
            "status": "error",
            "message": f"A course build for '{title}' is already in progress.",
        }, status_code=409)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    duration = _parse_duration(intake.get("time_budget", ""))

    # Upsert course_builds row
    db_execute(
        "INSERT INTO course_builds (slug, title, topic, target_audience, duration_hours, "
        "status, step, intake_json, created_at, updated_at) "
        "VALUES (?,?,?,?,?, 'intake', 1, ?,?,?) "
        "ON CONFLICT(slug) DO UPDATE SET "
        "title=excluded.title, topic=excluded.topic, target_audience=excluded.target_audience, "
        "duration_hours=excluded.duration_hours, status='intake', step=1, "
        "intake_json=excluded.intake_json, updated_at=excluded.updated_at",
        (slug, title, title, intake.get("learner", "yourself"), duration,
         json.dumps(intake), now, now),
    )

    # Ensure a learning_courses row exists and set status to 'building'
    lc_exists = db_scalar(
        "SELECT COUNT(*) FROM learning_courses WHERE slug=?", (slug,), default=0,
    )
    if lc_exists:
        db_execute(
            "UPDATE learning_courses SET status='building', updated_at=? WHERE slug=?",
            (now, slug),
        )
    else:
        category = "general"
        # Try to pull category from an existing idea row
        idea_row = db_query(
            "SELECT category FROM learning_courses WHERE slug=? AND status='idea' LIMIT 1",
            (slug,), default=[],
        )
        if idea_row:
            category = idea_row[0].get("category", "general")
        db_execute(
            "INSERT INTO learning_courses (title, slug, category, status, progress_pct, created_at, updated_at) "
            "VALUES (?,?,?,'building',0,?,?)",
            (title, slug, category, now, now),
        )

    prompt = _generate_intake_prompt(slug, title, intake)
    return {"status": "ok", "prompt": prompt, "title": title, "slug": slug}


# ---------------------------------------------------------------------------
# Competencies
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/competencies", response_class=HTMLResponse)
async def learning_competencies(request: Request):
    raw = db_query(
        "SELECT topic as name, level, domain FROM learning_competencies ORDER BY domain LIMIT 20"
    )
    level_map = {"beginner": 1, "novice": 2, "intermediate": 3, "advanced": 4, "expert": 5}
    skills = []
    for r in raw:
        d = dict(r)
        lvl = d.get("level")
        if isinstance(lvl, str):
            d["level"] = level_map.get(lvl.strip().lower(), 1)
        elif lvl is None:
            d["level"] = 0
        skills.append(d)
    return templates.TemplateResponse(
        request,
        "partials/learning_competencies.html",
        {"skills": skills},
    )


# ---------------------------------------------------------------------------
# Velocity — lessons completed in last 7 / 30 / 90 days
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/velocity", response_class=HTMLResponse)
async def learning_velocity(request: Request):
    """Show how many lessons have been completed in recent windows + streak + spark."""
    today = datetime.date.today()

    # Which completion tables exist?
    completion_sources: list[tuple[str, str]] = []
    for table, ts_col in (("course_progress", "completed_at"),
                          ("lesson_completions", "completed_at")):
        if db_scalar(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,), default=None,
        ):
            completion_sources.append((table, ts_col))

    has_sr = bool(db_scalar(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='spaced_repetition'",
        default=None,
    ))

    def _count_on(date_iso: str) -> int:
        """Count completions on a single calendar day."""
        total = 0
        for table, ts_col in completion_sources:
            try:
                n = db_scalar(
                    f"SELECT COUNT(*) FROM {table} WHERE date({ts_col}) = ?",
                    (date_iso,), default=0,
                ) or 0
                total += n
            except Exception:
                continue
        if has_sr:
            try:
                n = db_scalar(
                    "SELECT COUNT(*) FROM spaced_repetition WHERE date(reviewed_at) = ?",
                    (date_iso,), default=0,
                ) or 0
                total += n
            except Exception:
                pass
        return total

    def _count_since(days: int) -> int:
        cutoff = (today - datetime.timedelta(days=days)).isoformat()
        total = 0
        for table, ts_col in completion_sources:
            try:
                n = db_scalar(
                    f"SELECT COUNT(*) FROM {table} WHERE {ts_col} >= ?",
                    (cutoff,), default=0,
                ) or 0
                total += n
            except Exception:
                continue
        if has_sr:
            try:
                n = db_scalar(
                    "SELECT COUNT(*) FROM spaced_repetition WHERE reviewed_at >= ?",
                    (cutoff,), default=0,
                ) or 0
                total += n
            except Exception:
                pass
        return total

    def _count_all() -> int:
        total = 0
        for table, _ in completion_sources:
            try:
                n = db_scalar(f"SELECT COUNT(*) FROM {table}", default=0) or 0
                total += n
            except Exception:
                continue
        if has_sr:
            try:
                n = db_scalar(
                    "SELECT COUNT(*) FROM spaced_repetition WHERE reviewed_at IS NOT NULL",
                    default=0,
                ) or 0
                total += n
            except Exception:
                pass
        return total

    # 14-day sparkline (oldest first)
    spark_days = []
    for offset in range(13, -1, -1):
        d = today - datetime.timedelta(days=offset)
        spark_days.append({"date": d.isoformat(), "count": _count_on(d.isoformat())})
    max_count = max((s["count"] for s in spark_days), default=0)

    d7 = _count_since(7)
    d30 = _count_since(30)
    d_all = _count_all()

    # Trend: last 7 vs prior 7
    prior7 = 0
    for offset in range(7, 14):
        d = today - datetime.timedelta(days=offset)
        prior7 += _count_on(d.isoformat())
    if d7 > prior7:
        trend_glyph = "&#9650;"   # ▲
        trend_label = "up vs last week"
    elif d7 < prior7:
        trend_glyph = "&#9660;"   # ▼
        trend_label = "down vs last week"
    else:
        trend_glyph = "&rarr;"
        trend_label = "steady"

    # Streak = consecutive days back from today with >=1 completion
    streak = 0
    for offset in range(0, 365):
        d = today - datetime.timedelta(days=offset)
        if _count_on(d.isoformat()) > 0:
            streak += 1
        else:
            break

    any_data = bool(d7 or d30 or d_all or max_count)

    return templates.TemplateResponse(
        request,
        "partials/learning_velocity.html",
        {
            "d7": d7,
            "d30": d30,
            "d_all": d_all,
            "prior7": prior7,
            "streak": streak,
            "trend_glyph": trend_glyph,
            "trend_label": trend_label,
            "spark_days": spark_days,
            "max_count": max_count,
            "any_data": any_data,
        },
    )



# ---------------------------------------------------------------------------
# Today surface — course progress
# ---------------------------------------------------------------------------

def _course_state(row: dict) -> dict:
    """Progress and the NEXT LESSON for one course, derived where possible.

    `learning_courses.next_lesson` holds a lesson *title*, which cannot be
    linked to. Where the course has a manifest, the next lesson is derived
    instead as the first one not in `lesson_completions` — which yields an id,
    so "Continue" opens that lesson rather than dropping you at the course and
    making you find your place again.

    Courses delivered by their own app (statistics, hat-diagnostics) have no
    manifest; they keep the stored title and their launch URL.
    """
    slug = row.get("slug") or ""
    out = dict(row)
    lessons = (_load_lessons_json(slug).get("lessons") or []) if slug else []

    done_ids: set[str] = set()
    if slug:
        try:
            rows = db_query("SELECT lesson_id FROM lesson_completions WHERE course_slug=?",
                            (slug,), default=[]) or []
            done_ids = {r["lesson_id"] for r in rows}
        except Exception:
            pass

    if lessons:
        total = len(lessons)
        done = sum(1 for l in lessons if l["id"] in done_ids)
        nxt = next((l for l in lessons if l["id"] not in done_ids), None)
        out.update({
            "n_done": done,
            "n_total": total,
            "pct": round(100 * done / total) if total else 0,
            "next_id": nxt["id"] if nxt else None,
            "next_title": (nxt.get("title") if nxt else None),
            "next_time": (nxt.get("time") if nxt else None),
            "next_section": (nxt.get("section") if nxt else None),
            "finished": nxt is None and total > 0,
            "has_manifest": True,
        })
    else:
        total = row.get("total_modules") or 0
        done = row.get("completed_modules") or 0
        out.update({
            "n_done": done,
            "n_total": total,
            "pct": round(row.get("progress_pct") or 0),
            "next_id": None,
            "next_title": row.get("next_lesson") or None,
            "next_time": None,
            "next_section": None,
            "finished": False,
            "has_manifest": False,
        })
    out["launch"] = _launch_target(slug, row.get("course_url"))
    return out


def _active_courses() -> list[dict]:
    rows = db_query(
        "SELECT id, slug, title, category, progress_pct, total_modules, completed_modules, "
        "next_lesson, course_url, updated_at, "
        "COALESCE(focused_today, 0) AS focused_today "
        "FROM learning_courses WHERE status IN ('active','in_progress') "
        "ORDER BY title", default=[]) or []
    return [_course_state(r) for r in rows]


LEARNING_SLOTS = 3


@router.get("/api/partial/today/learning", response_class=HTMLResponse)
async def today_learning(request: Request):
    """Three slots. Each holds a course you chose, and shows the next lesson.

    Asked for 2026-09-05: "three small boxes next to each other that are
    placeholders for courses, each one you can select one of your courses and it
    will display the next lesson to do and just a button that says continue
    learning".

    What stood here was one wide panel with a chip per course and exactly ONE of
    them expanded — so the four courses you were not looking at showed a title
    and a percentage, and the next lesson was visible for one course at a time.
    Three slots show three next-lessons at once, which is the thing you actually
    choose between at the start of a session.

    `focused_today` carried the old single pin as 0/1. It is an INTEGER column,
    so it now carries the SLOT NUMBER (1..3) and 0 still means "not on Today".
    No new table, and the old value 1 keeps meaning slot 1.
    """
    courses = _active_courses()
    if not courses:
        return HTMLResponse('<div id="today-learning"></div>')

    by_slot: dict[int, dict] = {}
    for c in courses:
        try:
            n = int(c.get("focused_today") or 0)
        except (TypeError, ValueError):
            n = 0
        # First writer wins if two courses somehow claim one slot: a duplicate
        # would otherwise silently drop the other course out of the picker.
        if 1 <= n <= LEARNING_SLOTS and n not in by_slot:
            by_slot[n] = c

    # Fill empty slots with the courses you have actually been moving through,
    # rather than leaving three empty boxes on a first visit. Anything auto-filled
    # is NOT written back — a slot is only remembered once you choose it, so an
    # automatic guess never becomes a decision you did not make.
    unplaced = [c for c in courses if c not in by_slot.values()]
    unplaced.sort(key=lambda c: (-(c.get("n_done") or 0), c.get("title") or ""))
    slots = []
    for n in range(1, LEARNING_SLOTS + 1):
        c = by_slot.get(n)
        auto = False
        if c is None and unplaced:
            c, auto = unplaced.pop(0), True
        slots.append({"n": n, "course": c, "auto": auto})

    today_str = datetime.date.today().isoformat()
    due_all = db_scalar(
        "SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= ?",
        (today_str,), default=0) or 0
    for sl in slots:
        c = sl["course"]
        sl["due"] = (db_scalar(
            "SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= ? AND source_table = ?",
            (today_str, c["slug"]), default=0) or 0) if c else 0

    return templates.TemplateResponse(
        request, "partials/today_learning.html",
        {"slots": slots, "courses": courses, "due_all": due_all},
    )


@router.post("/api/today/learning/slot/{n}", response_class=HTMLResponse)
async def today_learning_slot_set(n: int, request: Request):
    """Put a course in slot n, or empty the slot when no course is named."""
    if not 1 <= n <= LEARNING_SLOTS:
        return await today_learning(request)
    form = await request.form()
    slug = (form.get("slug") or "").strip()
    try:
        # Free the slot, and free this course from whatever slot it was in — a
        # course in two boxes would show the same next lesson twice and quietly
        # cost a third of the panel.
        db_execute("UPDATE learning_courses SET focused_today = 0 WHERE focused_today = ?", (n,))
        if slug:
            db_execute("UPDATE learning_courses SET focused_today = 0 WHERE slug = ?", (slug,))
            db_execute("UPDATE learning_courses SET focused_today = ? WHERE slug = ?", (n, slug))
    except Exception:
        _log.warning("could not set learning slot %s", n, exc_info=True)
    return await today_learning(request)


@router.post("/api/today/learning/stop/{slug}", response_class=HTMLResponse)
async def today_learning_stop(slug: str, request: Request):
    """Stop a course you no longer want to follow.

    "You can also decide to stop a course if it doesn't interest you anymore."

    PAUSED, NOT DELETED, and deliberately still listed on the Learning surface
    with a Resume control. Stopping is a statement about your attention, not
    about the course — the lessons, the progress and the completions are all
    still there, and a status nothing queries would have made the course
    disappear with no way back.
    """
    try:
        db_execute(
            "UPDATE learning_courses SET status='paused', focused_today=0, updated_at=? "
            "WHERE slug=?", (datetime.datetime.now().isoformat(), slug))
    except Exception:
        _log.warning("could not stop course %s", slug, exc_info=True)
    return await today_learning(request)


@router.post("/api/today/learning/resume/{slug}", response_class=HTMLResponse)
async def today_learning_resume(slug: str, request: Request):
    """Put a stopped course back among the active ones."""
    try:
        db_execute(
            "UPDATE learning_courses SET status='active', updated_at=? WHERE slug=? AND status='paused'",
            (datetime.datetime.now().isoformat(), slug))
    except Exception:
        _log.warning("could not resume course %s", slug, exc_info=True)
    return await learning_courses_archive(request)


@router.post("/api/today/learning/focus/{slug}", response_class=HTMLResponse)
async def today_learning_focus(slug: str, request: Request):
    """Kept so an older cached page cannot 404: it now fills slot 1."""
    try:
        db_execute("UPDATE learning_courses SET focused_today = 0 WHERE focused_today = 1")
        db_execute("UPDATE learning_courses SET focused_today = 1 WHERE slug = ?", (slug,))
    except Exception:
        pass
    return await today_learning(request)


# ---------------------------------------------------------------------------
# Course reader — Part A
# ---------------------------------------------------------------------------

def _load_lessons_json(slug: str) -> dict:
    p = _COURSES_DIR / slug / "lessons.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _lesson_path(slug: str, lesson_id: str) -> Path | None:
    """Resolve the markdown file for a lesson id."""
    lessons_dir = _COURSES_DIR / slug / "lessons"
    # Expect filename like "01-descriptive-statistics.md" matching order
    prefix = lesson_id.split("-")[-1]  # "01", "02", …
    if not prefix.isdigit():
        prefix = lesson_id
    for f in sorted(lessons_dir.glob("*.md")):
        num = f.name.split("-")[0]
        if num == prefix.zfill(2) or f.stem.startswith(prefix):
            return f
    return None


def _lesson_seq(slug: str, lesson_id: str) -> tuple[str | None, str | None]:
    """Return (prev_id, next_id) for a lesson within its course."""
    data = _load_lessons_json(slug)
    lessons = data.get("lessons", [])
    ids = [l["id"] for l in lessons]
    if lesson_id not in ids:
        return None, None
    idx = ids.index(lesson_id)
    prev_id = ids[idx - 1] if idx > 0 else None
    next_id = ids[idx + 1] if idx < len(ids) - 1 else None
    return prev_id, next_id


@router.get("/api/course/{slug}/overview", response_class=HTMLResponse)
async def course_overview(slug: str, request: Request):
    """Return module + lesson list for a course (sidebar/overview panel)."""
    data = _load_lessons_json(slug)
    course = db_query(
        "SELECT id, title, slug, category, progress_pct, total_modules, completed_modules, "
        "current_lesson, next_lesson FROM learning_courses WHERE slug=? LIMIT 1",
        (slug,),
        default=[],
    )
    course_row = course[0] if course else {}

    # Annotate lessons with completion state from lesson_completions table
    completed_ids: set[str] = set()
    try:
        rows = db_query(
            "SELECT lesson_id FROM lesson_completions WHERE course_slug=?", (slug,), default=[]
        )
        completed_ids = {r["lesson_id"] for r in (rows or [])}
    except Exception:
        pass

    lessons = data.get("lessons", [])
    for lesson in lessons:
        lesson["done"] = lesson["id"] in completed_ids

    # The sidebar is scoped to the active tab: the Course tab should not list
    # six deep dives under the day-by-day track, and the Deep dives tab should
    # not make you scroll past sixteen lessons to reach them.
    tab = (request.query_params.get("tab") or "course").strip()
    if tab == "deepdives":
        shown = [l for l in lessons if l.get("section") == _DEEP_DIVE_SECTION]
    elif tab == "methodology":
        shown = []
    else:
        tab = "course"
        shown = [l for l in lessons if l.get("section") != _DEEP_DIVE_SECTION]

    return templates.TemplateResponse(
        request,
        "partials/learning_course_overview.html",
        {"course": course_row, "modules": data.get("modules", []),
         "lessons": shown, "slug": slug, "tab": tab,
         "methodologies": _load_methodologies(slug) if tab == "methodology" else [],
         "n_done": len(completed_ids), "n_total": len(lessons)},
    )


@router.get("/api/course/{slug}/lesson/{lesson_id}", response_class=HTMLResponse)
async def serve_lesson(slug: str, lesson_id: str, request: Request):
    """Render a lesson markdown file as HTML inside the course reader."""
    path = _lesson_path(slug, lesson_id)
    if path is None or not path.exists():
        return HTMLResponse("<p style='color:var(--m-danger)'>Lesson not found.</p>", status_code=404)

    raw = path.read_text(encoding="utf-8")
    _md_renderer.reset()
    body_html = _enrich_lesson_html(_md_renderer.convert(raw))

    data = _load_lessons_json(slug)
    lessons = data.get("lessons", [])
    lesson_meta = next((l for l in lessons if l["id"] == lesson_id), {})
    prev_id, next_id = _lesson_seq(slug, lesson_id)

    # Check completion
    done = False
    try:
        count = db_scalar(
            "SELECT COUNT(*) FROM lesson_completions WHERE course_slug=? AND lesson_id=?",
            (slug, lesson_id), default=0
        )
        done = bool(count)
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/learning_lesson_reader.html",
        {
            "slug": slug,
            "lesson_id": lesson_id,
            "lesson": lesson_meta,
            "body_html": body_html,
            "prev_id": prev_id,
            "next_id": next_id,
            "done": done,
            # A reading course does not present homework. Default False, so a
            # course must opt IN — the drill format cannot leak into a course
            # that was never meant to have it.
            "show_exercises": bool(_load_course_meta(slug).get("exercises_shown", False)),
        },
    )




def _load_course_meta(slug: str) -> dict:
    """course.json — the spine, the counts, the pedagogy note."""
    p = _COURSES_DIR / slug / "course.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


@router.get("/api/course/{slug}/tab/{tab}", response_class=HTMLResponse)
async def serve_tab_overview(slug: str, tab: str, request: Request):
    """The landing page for a tab.

    Clicking a tab used to leave the reading panel on a "choose something"
    placeholder, so the tab appeared to do nothing until you also picked an item
    from the sidebar. Each tab now opens on an index you can actually choose
    from — which is also the only place the course's spine, its shape and its
    counts are visible.
    """
    data = _load_lessons_json(slug)
    lessons = data.get("lessons", []) or []
    meta = _load_course_meta(slug)

    completed: set[str] = set()
    try:
        rows = db_query("SELECT lesson_id FROM lesson_completions WHERE course_slug=?",
                        (slug,), default=[]) or []
        completed = {r["lesson_id"] for r in rows}
    except Exception:
        pass
    for l in lessons:
        l["done"] = l["id"] in completed

    if tab == "methodology":
        items, sections = [], []
    elif tab == "deepdives":
        items = [l for l in lessons if l.get("section") == _DEEP_DIVE_SECTION]
        sections = []
    else:
        tab = "course"
        items = [l for l in lessons if l.get("section") != _DEEP_DIVE_SECTION]
        sections = []
        for l in items:
            if l.get("section") not in sections:
                sections.append(l.get("section"))

    return templates.TemplateResponse(
        request,
        "partials/learning_tab_overview.html",
        {"slug": slug, "tab": tab, "meta": meta, "items": items, "sections": sections,
         "methodologies": _load_methodologies(slug) if tab == "methodology" else [],
         "n_done": len(completed), "n_total": len(lessons),
         "course_title": meta.get("title") or slug},
    )

@router.get("/api/course/{slug}/methodology/{mid}", response_class=HTMLResponse)
async def serve_methodology(slug: str, mid: str, request: Request):
    """One generalised methodology."""
    items = _load_methodologies(slug)
    item = next((m for m in items if m.get("id") == mid), None)
    if item is None:
        return HTMLResponse(
            "<div class='card' style='padding:28px'>That methodology is not in this course.</div>",
            status_code=404,
        )
    ids = [m.get("id") for m in items]
    i = ids.index(mid)
    return templates.TemplateResponse(
        request,
        "partials/learning_methodology.html",
        {"slug": slug, "m": item,
         "prev_id": ids[i - 1] if i > 0 else None,
         "next_id": ids[i + 1] if i < len(ids) - 1 else None},
    )

@router.post("/api/course/{slug}/lesson/{lesson_id}/complete", response_class=JSONResponse)
async def complete_lesson(slug: str, lesson_id: str, request: Request):
    """Mark a lesson as complete and update course progress."""
    _ensure_lesson_completions_table()

    # Insert completion record (ignore if already exists)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        db_execute(
            "INSERT OR IGNORE INTO lesson_completions (course_slug, lesson_id, completed_at) "
            "VALUES (?, ?, ?)",
            (slug, lesson_id, now),
        )
    except Exception:
        pass

    # Recalculate progress
    data = _load_lessons_json(slug)
    lessons = data.get("lessons", [])
    total = len(lessons)

    completed_rows = db_query(
        "SELECT lesson_id FROM lesson_completions WHERE course_slug=?", (slug,), default=[]
    ) or []
    completed_ids = {r["lesson_id"] for r in completed_rows}
    n_done = sum(1 for l in lessons if l["id"] in completed_ids)
    pct = round(n_done / total * 100, 1) if total else 0

    # Determine next uncompleted lesson
    next_lesson = ""
    for lesson in lessons:
        if lesson["id"] not in completed_ids:
            next_lesson = lesson["title"]
            break

    # Completed modules = modules where all of that module's lessons are done.
    #
    # The previous version read m["lessons"], a key no course-builder emits, so
    # the generator expression became all([]) — which is True — and EVERY module
    # counted as complete on the first lesson finished. Where `modules` was
    # absent it silently reported 0 forever instead. Both were wrong.
    #
    # Map modules to lessons from what manifests actually contain: an explicit
    # lesson list if present, else a shared `section`, else order == module.
    modules = data.get("modules", []) or []
    n_modules_done = 0
    for m in modules:
        ids = [str(x) for x in (m.get("lessons") or [])]
        if not ids:
            ids = [l["id"] for l in lessons if l.get("section") == m.get("section")]
        if not ids:
            ids = [l["id"] for l in lessons if l.get("order") == m.get("module")]
        if ids and all(i in completed_ids for i in ids):
            n_modules_done += 1

    db_execute(
        "UPDATE learning_courses SET completed_modules=?, progress_pct=?, "
        "current_lesson=?, next_lesson=? WHERE slug=?",
        (n_modules_done, pct, lesson_id, next_lesson, slug),
    )

    # Seed a spaced-rep card if not already present
    lesson_meta = next((l for l in lessons if l["id"] == lesson_id), {})
    _seed_spaced_rep_card(slug, lesson_meta)

    _, next_id = _lesson_seq(slug, lesson_id)
    return JSONResponse({
        "status": "ok",
        "progress_pct": pct,
        "completed_lessons": n_done,
        "total_lessons": total,
        "next_lesson_id": next_id,
    })


@router.post("/api/course/{slug}/seed-spaced-rep", response_class=JSONResponse)
async def seed_course_spaced_rep(slug: str, request: Request):
    """Seed spaced-repetition cards for all lessons in a course (idempotent)."""
    _ensure_lesson_completions_table()
    data = _load_lessons_json(slug)
    lessons = data.get("lessons", [])
    seeded = 0
    for lesson in lessons:
        seeded += _seed_spaced_rep_card(slug, lesson)
    return JSONResponse({"status": "ok", "seeded": seeded, "total": len(lessons)})


def _generate_card(domain: str, topic: str) -> tuple[str, str] | None:
    """Generate a real Q/A flashcard for a competency topic via Claude.

    A competency ("statistics / Spatial scan statistics") is a topic, not a card.
    Without a real question and answer, seeding it produces "Explain: X" stubs that
    teach nothing. Since the dashboard now loads ANTHROPIC_API_KEY, we generate a
    genuine domain flashcard. Returns None on any failure → caller uses a plain
    fallback card, so this never blocks seeding.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        from models import model_for

        prompt = (
            f"Write one spaced-repetition flashcard for a senior epidemiologist "
            f"studying '{topic}' (domain: {domain}). Return ONLY JSON: "
            '{"front": "a specific recall question", "back": "a concise, correct '
            'answer (2-4 sentences, technical, no fluff)"}. '
            "The question must test understanding, not definitions."
        )
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": model_for("brief"), "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30.0,
        )
        if resp.status_code != 200:
            return None
        _payload = resp.json()
        try:  # record real token usage for the monitor (Keystone B6.3)
            from db import record_token_usage
            _u = _payload.get("usage", {}) or {}
            record_token_usage("learning-coach", model_for("brief"),
                               _u.get("input_tokens", 0), _u.get("output_tokens", 0),
                               task_summary="Flashcard generation")
        except Exception:
            pass
        raw = _payload["content"][0]["text"].strip()
        s, e = raw.find("{"), raw.rfind("}") + 1
        if s < 0 or e <= s:
            return None
        d = json.loads(raw[s:e])
        front, back = str(d.get("front", "")).strip(), str(d.get("back", "")).strip()
        return (front, back) if front and back else None
    except Exception:
        return None


@router.post("/api/learning/seed-from-competencies", response_class=JSONResponse)
async def seed_from_competencies(request: Request):
    """Build the review deck from the user's competencies.

    The whole spaced-repetition machine (SM-2 scheduler, grade buttons, streak,
    heatmap) was fully built and correct — it had simply never been given a single
    card, because cards only came from course lesson JSONs that don't exist. The 8
    competencies ARE real content, so this turns each into a genuine flashcard,
    due immediately. Idempotent (dedup on source_table='competency' + source_id).
    """
    rows = db_query(
        "SELECT competency_id, domain, topic FROM learning_competencies", default=[]
    ) or []
    today = str(datetime.date.today())
    seeded = 0
    for r in rows:
        cid = r["competency_id"]
        exists = db_scalar(
            "SELECT COUNT(*) FROM spaced_repetition WHERE source_id=? AND source_table='competency'",
            (cid,), default=0,
        )
        if exists:
            continue
        card = _generate_card(r["domain"] or "", r["topic"] or "")
        if card:
            front, back = card
        else:
            front = f"{r['topic']} — explain the core idea and when you'd use it."
            back = f"Self-assess your grasp of {r['topic']} ({r['domain']})."
        try:
            # sr_id is TEXT PRIMARY KEY and is NOT auto-assigned — it must be set
            # explicitly, or the row gets a NULL id and every review call 422s.
            db_execute(
                "INSERT INTO spaced_repetition "
                "(sr_id, front_text, back_text, source_id, source_table, next_review, "
                "interval_days, ease_factor, repetitions, created_at) "
                "VALUES (?,?,?,?,'competency',?,1,2.5,0,datetime('now'))",
                (f"comp-{cid}", front, back, cid, today),
            )
            seeded += 1
        except Exception:
            pass
    return JSONResponse({"status": "ok", "seeded": seeded, "total": len(rows)})


def _ensure_lesson_completions_table() -> None:
    try:
        db_execute(
            """CREATE TABLE IF NOT EXISTS lesson_completions (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               course_slug TEXT NOT NULL,
               lesson_id TEXT NOT NULL,
               completed_at TEXT NOT NULL,
               UNIQUE(course_slug, lesson_id)
            )"""
        )
    except Exception:
        pass


def _load_qbank(slug: str) -> dict:
    """Authored spaced-repetition cards for a course, from knowledge/courses/<slug>/qbank.json."""
    p = _COURSES_DIR / slug / "qbank.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _seed_spaced_rep_card(slug: str, lesson: dict) -> int:
    """Insert spaced-rep card(s) for one lesson. Returns the number inserted.

    Prefers *authored* cards from the course's qbank.json. Falling back to
    (title, description) produces a table-of-contents entry, not a flashcard —
    the same "stub teaches nothing" problem _generate_card() was written to
    avoid for competencies. Authored cards win whenever they exist.
    """
    lesson_id = lesson.get("id", "")
    if not lesson_id:
        return 0
    today = str(datetime.date.today())

    authored = (_load_qbank(slug).get(lesson_id) or {}).get("cards") or []
    if authored:
        cards = [
            (f"{slug}:{lesson_id}:{i}", c.get("front", ""), c.get("back", ""))
            for i, c in enumerate(authored, start=1)
            if c.get("front") and c.get("back")
        ]
    else:
        cards = [(f"{slug}:{lesson_id}",
                  lesson.get("title", lesson_id),
                  lesson.get("description", ""))]

    inserted = 0
    for sr_id, front, back in cards:
        try:
            if db_scalar("SELECT COUNT(*) FROM spaced_repetition WHERE sr_id=?",
                         (sr_id,), default=0):
                continue
            db_execute(
                "INSERT INTO spaced_repetition "
                "(sr_id, front_text, back_text, source_id, source_table, next_review, interval_days, ease_factor, repetitions, created_at) "
                "VALUES (?,?,?,?,?,?,1,2.5,0,datetime('now'))",
                (sr_id, front, back, lesson_id, slug, today),
            )
            inserted += 1
        except Exception:
            continue
    return inserted
