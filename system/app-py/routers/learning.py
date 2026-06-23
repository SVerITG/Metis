"""
routers/learning.py — Learning tab routes.
"""

import datetime
import json
import os
import re
from pathlib import Path

import markdown as _md
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar, db_execute

_RC_ROOT = Path(os.environ.get("METIS_RC_ROOT", Path(__file__).parents[4]))
_COURSES_DIR = _RC_ROOT / "knowledge" / "courses"

_md_renderer = _md.Markdown(extensions=["fenced_code", "tables", "nl2br"])

router = APIRouter()
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
    }


@router.get("/tab/learning", response_class=HTMLResponse)
async def learning_tab(request: Request):
    return templates.TemplateResponse(request, "learning.html", _learning_context())


@router.get("/api/tab/learning", response_class=HTMLResponse)
async def learning_tab_partial(request: Request):
    return templates.TemplateResponse(request, "learning.html", _learning_context())


@router.get("/course/{slug}", response_class=HTMLResponse)
async def course_reader_page(slug: str, request: Request):
    """Standalone course reader — opens in its own browser tab."""
    course = db_query(
        "SELECT title FROM learning_courses WHERE slug=? LIMIT 1",
        (slug,), default=[],
    )
    title = course[0]["title"] if course else slug.replace("-", " ").title()
    return templates.TemplateResponse(
        request,
        "course_reader.html",
        {"slug": slug, "course_title": title},
    )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/meta", response_class=HTMLResponse)
async def learning_meta(request: Request):
    total = db_scalar("SELECT COUNT(*) FROM learning_courses", default=0) or 0
    today = str(datetime.date.today())
    due = db_scalar("SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= ?", (today,), default=0) or 0
    return HTMLResponse(f"{total} COURSES · {due} DUE TODAY")


@router.get("/api/partial/learning/courses-archive", response_class=HTMLResponse)
async def learning_courses_archive(request: Request):
    courses = db_query(
        "SELECT id, title, category, progress_pct, total_modules, completed_modules, status, slug, "
        "project_id, current_lesson, next_lesson, course_url, lesson_notes "
        "FROM learning_courses WHERE status IN ('active','in_progress','building') "
        "ORDER BY CASE status WHEN 'building' THEN 0 ELSE 1 END, progress_pct DESC LIMIT 6"
    ) or []

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
        {"courses": courses},
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
        "ORDER BY next_review LIMIT 20",
        (today,),
    )
    # Streak: consecutive calendar days with at least one completed review
    streak = _compute_streak()
    return templates.TemplateResponse(
        request,
        "partials/learning_due.html",
        {"due": due, "today": today, "streak": streak},
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


@router.post("/api/learning/review/{sr_id}", response_class=HTMLResponse)
async def mark_review_done(sr_id: int, request: Request):
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

    return templates.TemplateResponse(
        request,
        "partials/learning_course_overview.html",
        {"course": course_row, "modules": data.get("modules", []),
         "lessons": lessons, "slug": slug},
    )


@router.get("/api/course/{slug}/lesson/{lesson_id}", response_class=HTMLResponse)
async def serve_lesson(slug: str, lesson_id: str, request: Request):
    """Render a lesson markdown file as HTML inside the course reader."""
    path = _lesson_path(slug, lesson_id)
    if path is None or not path.exists():
        return HTMLResponse("<p style='color:var(--m-danger)'>Lesson not found.</p>", status_code=404)

    raw = path.read_text(encoding="utf-8")
    _md_renderer.reset()
    body_html = _md_renderer.convert(raw)

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
        },
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

    # Completed modules = modules where all lessons are done
    modules = data.get("modules", [])
    n_modules_done = sum(
        1 for m in modules
        if all(lid in completed_ids for lid in m.get("lessons", []))
    )

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


def _seed_spaced_rep_card(slug: str, lesson: dict) -> int:
    """Insert a spaced-rep card for one lesson. Returns 1 if inserted, 0 if already existed."""
    lesson_id = lesson.get("id", "")
    title = lesson.get("title", lesson_id)
    if not lesson_id:
        return 0
    today = str(datetime.date.today())
    try:
        existing = db_scalar(
            "SELECT COUNT(*) FROM spaced_repetition WHERE source_id=? AND source_table=?",
            (lesson_id, slug), default=0
        )
        if existing:
            return 0
        db_execute(
            "INSERT INTO spaced_repetition "
            "(front_text, back_text, source_id, source_table, next_review, interval_days, ease_factor, repetitions, created_at) "
            "VALUES (?,?,?,?,?,1,2.5,0,datetime('now'))",
            (title, lesson.get("description", ""), lesson_id, slug, today),
        )
        return 1
    except Exception:
        return 0
