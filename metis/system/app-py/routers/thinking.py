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
     request, "thinking.html", {"active_tab": "thinking"}
 )


@router.get("/api/tab/thinking", response_class=HTMLResponse)
async def thinking_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "thinking.html", {"active_tab": "thinking"}
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
        request,
        "partials/thinking_ideas.html",
        {
            "ideas": ideas
        },
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
        request,
        "partials/thinking_notes.html",
        {
            "notes": notes
        },
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
        request,
        "partials/thinking_questions.html",
        {
            "questions": questions
        },
    )


# ---------------------------------------------------------------------------
# Brainstorm sessions (Phase 8)
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/brainstorm-sessions", response_class=HTMLResponse)
async def thinking_brainstorm_sessions(request: Request):
    sessions = db_query(
        "SELECT bs.session_uuid, bs.title, bs.status, bs.started_at, bs.updated_at, "
        "COUNT(bt.id) as turn_count "
        "FROM brainstorm_sessions bs "
        "LEFT JOIN brainstorm_turns bt ON bs.session_uuid = bt.session_uuid "
        "GROUP BY bs.id ORDER BY bs.updated_at DESC LIMIT 10",
        default=[],
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_brainstorm_sessions.html",
        {"sessions": [dict(s) for s in (sessions or [])]},
    )
