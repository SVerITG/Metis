"""
routers/learning.py — Learning tab routes.
"""

import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar

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
        "SELECT id, title, category, progress_pct, total_modules, completed_modules, status, slug "
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
    due = db_query(
        "SELECT sr_id as id, front_text as topic, source_table as course_title, "
        "next_review as next_review_date, interval_days "
        "FROM spaced_repetition WHERE next_review <= ? "
        "ORDER BY next_review LIMIT 20",
        (today,),
    )
    return templates.TemplateResponse(
        request,
        "partials/learning_due.html",
        {
            "due": due, "today": today
        },
    )


# ---------------------------------------------------------------------------
# Active courses
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/courses", response_class=HTMLResponse)
async def learning_courses(request: Request):
    courses = db_query(
        "SELECT id, slug, title, category, progress_pct, total_modules, completed_modules, project_id "
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
