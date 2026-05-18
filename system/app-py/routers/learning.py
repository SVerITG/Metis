"""
routers/learning.py — Learning tab routes.
"""

import datetime
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar, db_execute

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/learning", response_class=HTMLResponse)
async def learning_tab(request: Request):
    return templates.TemplateResponse(
     request, "learning.html", {"active_tab": "learning"}
 )


@router.get("/api/tab/learning", response_class=HTMLResponse)
async def learning_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "learning.html", {"active_tab": "learning"}
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
        "FROM learning_courses WHERE status IN ('active','in_progress') ORDER BY progress_pct DESC LIMIT 6"
    ) or []
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
    # Ensure reviewed_at column exists (added in this phase)
    try:
        db_execute("ALTER TABLE spaced_repetition ADD COLUMN reviewed_at TEXT")
    except Exception:
        pass
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
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    # Ensure slug uniqueness
    existing = db_scalar("SELECT COUNT(*) FROM learning_courses WHERE slug=?", (slug,), default=0) or 0
    if existing:
        slug = f"{slug}-{existing}"
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
    prompt = f"/course-builder\ncourse-slug: {slug}\nPlease walk me through the questionnaire at metis/system/config/course-builder-questionnaire.md and build this course: {title}"
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
    questionnaire = "metis/system/config/course-builder-questionnaire.md"

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
# Competencies
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/competencies", response_class=HTMLResponse)
async def learning_competencies(request: Request):
    skills = db_query(
        "SELECT topic as name, level, domain FROM learning_competencies ORDER BY domain, level DESC LIMIT 20"
    )
    return templates.TemplateResponse(
        request,
        "partials/learning_competencies.html",
        {
            "skills": skills
        },
    )
