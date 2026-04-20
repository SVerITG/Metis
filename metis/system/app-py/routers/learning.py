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
        "learning.html", {"request": request, "active_tab": "learning"}
    )


@router.get("/api/tab/learning", response_class=HTMLResponse)
async def learning_tab_partial(request: Request):
    return templates.TemplateResponse(
        "learning.html", {"request": request, "active_tab": "learning"}
    )


# ---------------------------------------------------------------------------
# Due for review today
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/due-today", response_class=HTMLResponse)
async def learning_due_today(request: Request):
    today = str(datetime.date.today())
    due = db_query(
        "SELECT id, topic, course_title, next_review_date, interval_days "
        "FROM spaced_repetition WHERE next_review_date <= ? "
        "ORDER BY next_review_date LIMIT 20",
        (today,),
    )
    return templates.TemplateResponse(
        "partials/learning_due.html",
        {"request": request, "due": due, "today": today},
    )


# ---------------------------------------------------------------------------
# Active courses
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/courses", response_class=HTMLResponse)
async def learning_courses(request: Request):
    courses = db_query(
        "SELECT id, title, category, progress_pct, total_modules, completed_modules "
        "FROM learning_courses WHERE status = 'active' ORDER BY progress_pct DESC"
    )
    return templates.TemplateResponse(
        "partials/learning_courses.html",
        {"request": request, "courses": courses},
    )


# ---------------------------------------------------------------------------
# Recently completed
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/completed", response_class=HTMLResponse)
async def learning_completed(request: Request):
    items = db_query(
        "SELECT id, title, category, completed_at "
        "FROM learning_courses WHERE status = 'completed' "
        "ORDER BY completed_at DESC LIMIT 10"
    )
    return templates.TemplateResponse(
        "partials/learning_completed.html",
        {"request": request, "items": items},
    )


# ---------------------------------------------------------------------------
# Competencies
# ---------------------------------------------------------------------------


@router.get("/api/partial/learning/competencies", response_class=HTMLResponse)
async def learning_competencies(request: Request):
    skills = db_query(
        "SELECT name, level, domain FROM competencies ORDER BY domain, level DESC LIMIT 20"
    )
    return templates.TemplateResponse(
        "partials/learning_competencies.html",
        {"request": request, "skills": skills},
    )
