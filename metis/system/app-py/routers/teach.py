"""
routers/teach.py — Teach tab routes.
"""

import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


# ---------------------------------------------------------------------------
# Full-page + HTMX swap for the Teach tab
# ---------------------------------------------------------------------------


@router.get("/tab/teach", response_class=HTMLResponse)
async def teach_tab(request: Request):
    return templates.TemplateResponse(
     request, "teach.html", {"active_tab": "teach"}
 )


@router.get("/api/tab/teach", response_class=HTMLResponse)
async def teach_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "teach.html", {"active_tab": "teach"}
 )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/teach/meta", response_class=HTMLResponse)
async def teach_meta(request: Request):
    total = db_scalar("SELECT COUNT(*) FROM learning_courses", default=0) or 0
    active = db_scalar("SELECT COUNT(*) FROM learning_courses WHERE status='active'", default=0) or 0
    done = db_scalar("SELECT COUNT(*) FROM learning_courses WHERE status='completed'", default=0) or 0
    return HTMLResponse(f"{active} COURSES · {done} PUBLISHED · {total - active - done} IN PROGRESS")


@router.get("/api/partial/teach/active-label", response_class=HTMLResponse)
async def teach_active_label(request: Request):
    row = db_query(
        "SELECT title, progress_pct FROM learning_courses WHERE status='active' ORDER BY progress_pct DESC LIMIT 1"
    )
    if row:
        title = row[0].get("title", "Active course")[:40]
        pct = row[0].get("progress_pct") or 0
        return HTMLResponse(
            f'<span>{title}</span><span class="tail">IN PROGRESS · {pct}%</span>'
        )
    return HTMLResponse('<span>Active course</span><span class="tail">IN PROGRESS</span>')


@router.get("/api/partial/teach/active-draft", response_class=HTMLResponse)
async def teach_active_draft(request: Request):
    rows = db_query(
        "SELECT id, title, category, progress_pct, total_modules, completed_modules, status, slug "
        "FROM learning_courses WHERE status='active' ORDER BY progress_pct DESC LIMIT 1"
    ) or []
    course = rows[0] if rows else None
    return templates.TemplateResponse(
        request,
        "partials/teach_active_draft.html",
        {"course": course},
    )


@router.get("/api/partial/teach/courses-list", response_class=HTMLResponse)
async def teach_courses_list(request: Request):
    rows = db_query(
        "SELECT id, title, category, progress_pct, status FROM learning_courses ORDER BY status DESC, progress_pct DESC LIMIT 10"
    ) or []
    return templates.TemplateResponse(
        request,
        "partials/teach_courses_list.html",
        {"courses": rows},
    )


@router.get("/api/partial/teach/suggested", response_class=HTMLResponse)
async def teach_suggested(request: Request):
    rows = db_query(
        "SELECT title, category FROM learning_courses WHERE status='placeholder' ORDER BY id LIMIT 1"
    ) or []
    course = rows[0] if rows else None
    return templates.TemplateResponse(
        request,
        "partials/teach_suggested.html",
        {"course": course},
    )


# ---------------------------------------------------------------------------
# Course list partial
# ---------------------------------------------------------------------------


@router.get("/api/partial/teach/courses", response_class=HTMLResponse)
async def teach_courses(request: Request):
    courses = db_query(
        "SELECT id, title, code, semester, description, student_count "
        "FROM courses ORDER BY semester DESC, title"
    )
    return templates.TemplateResponse(
        request,
        "partials/teach_courses.html",
        {
            "courses": courses
        },
    )


# ---------------------------------------------------------------------------
# Literature alerts for a course
# ---------------------------------------------------------------------------


@router.get("/api/partial/teach/lit-alerts/{course_id}", response_class=HTMLResponse)
async def teach_lit_alerts(request: Request, course_id: int):
    since = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    alerts = db_query(
        "SELECT l.title, l.authors, l.year, l.source "
        "FROM literature_metadata l "
        "JOIN course_topics ct ON ct.course_id = ? "
        "WHERE l.tags LIKE '%' || ct.keyword || '%' "
        "  AND l.created_at >= ? "
        "ORDER BY l.created_at DESC LIMIT 5",
        (course_id, since),
    )
    return templates.TemplateResponse(
        request,
        "partials/teach_lit_alerts.html",
        {
            "alerts": alerts, "course_id": course_id
        },
    )


# ---------------------------------------------------------------------------
# News alerts for a course
# ---------------------------------------------------------------------------


@router.get("/api/partial/teach/news-alerts/{course_id}", response_class=HTMLResponse)
async def teach_news_alerts(request: Request, course_id: int):
    since = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    alerts = db_query(
        "SELECT n.headline, n.source, n.published_at, n.signal_tag "
        "FROM news_items n "
        "JOIN course_topics ct ON ct.course_id = ? "
        "WHERE n.headline LIKE '%' || ct.keyword || '%' "
        "  AND n.published_at >= ? "
        "ORDER BY n.published_at DESC LIMIT 5",
        (course_id, since),
    )
    return templates.TemplateResponse(
        request,
        "partials/teach_news_alerts.html",
        {
            "alerts": alerts, "course_id": course_id
        },
    )


# ---------------------------------------------------------------------------
# Add course
# ---------------------------------------------------------------------------


@router.post("/api/teach/add-course", response_class=HTMLResponse)
async def teach_add_course(
    request: Request,
    title: str = Form(...),
    code: str = Form(""),
    semester: str = Form(""),
    description: str = Form(""),
    student_count: int = Form(0),
):
    now = datetime.datetime.now().isoformat()
    db_execute(
        "INSERT INTO courses (title, code, semester, description, student_count, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (title, code, semester, description, student_count, now),
    )
    # Return updated course list
    courses = db_query(
        "SELECT id, title, code, semester, description, student_count "
        "FROM courses ORDER BY semester DESC, title"
    )
    return templates.TemplateResponse(
        request,
        "partials/teach_courses.html",
        {
            "courses": courses
        },
    )
