"""
routers/thinking.py — Thinking tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/thinking", response_class=HTMLResponse)
async def thinking_tab(request: Request):
    return templates.TemplateResponse(
        "thinking.html", {"request": request, "active_tab": "thinking"}
    )


@router.get("/api/tab/thinking", response_class=HTMLResponse)
async def thinking_tab_partial(request: Request):
    return templates.TemplateResponse(
        "thinking.html", {"request": request, "active_tab": "thinking"}
    )


# ---------------------------------------------------------------------------
# Ideas
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/ideas", response_class=HTMLResponse)
async def thinking_ideas(request: Request):
    ideas = db_query(
        "SELECT id, content, tags, created_at "
        "FROM ideas ORDER BY created_at DESC LIMIT 30"
    )
    return templates.TemplateResponse(
        "partials/thinking_ideas.html",
        {"request": request, "ideas": ideas},
    )


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/notes", response_class=HTMLResponse)
async def thinking_notes(request: Request):
    notes = db_query(
        "SELECT id, content, tags, created_at "
        "FROM personal_notes ORDER BY created_at DESC LIMIT 20"
    )
    return templates.TemplateResponse(
        "partials/thinking_notes.html",
        {"request": request, "notes": notes},
    )


# ---------------------------------------------------------------------------
# Open questions
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/questions", response_class=HTMLResponse)
async def thinking_questions(request: Request):
    questions = db_query(
        "SELECT id, content, created_at "
        "FROM ideas WHERE tags LIKE '%question%' "
        "ORDER BY created_at DESC LIMIT 15"
    )
    return templates.TemplateResponse(
        "partials/thinking_questions.html",
        {"request": request, "questions": questions},
    )
