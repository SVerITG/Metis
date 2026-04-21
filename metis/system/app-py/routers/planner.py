"""
routers/planner.py — Planner tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_query

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/planner", response_class=HTMLResponse)
async def planner_tab(request: Request):
    return templates.TemplateResponse(
     request, "planner.html", {"active_tab": "planner"}
 )


@router.get("/api/tab/planner", response_class=HTMLResponse)
async def planner_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "planner.html", {"active_tab": "planner"}
 )


# ---------------------------------------------------------------------------
# Kanban board
# ---------------------------------------------------------------------------


@router.get("/api/partial/planner/kanban", response_class=HTMLResponse)
async def planner_kanban(request: Request):
    someday = db_query(
        "SELECT project_id as id, title, domain, priority FROM projects WHERE status = 'someday' ORDER BY priority DESC"
    )
    incubating = db_query(
        "SELECT project_id as id, title, domain, priority FROM projects WHERE status = 'incubating' ORDER BY priority DESC"
    )
    active = db_query(
        "SELECT project_id as id, title, domain, priority, next_step FROM projects WHERE status = 'active' ORDER BY priority DESC"
    )
    return templates.TemplateResponse(
        request,
        "partials/planner_kanban.html",
        {
            "someday": someday,
            "incubating": incubating,
            "active": active,
        },
    )


# ---------------------------------------------------------------------------
# Focus board (PhD-centric)
# ---------------------------------------------------------------------------


@router.get("/api/partial/planner/focus", response_class=HTMLResponse)
async def planner_focus(request: Request):
    phd = db_query(
        "SELECT project_id as id, title, domain, priority, next_step "
        "FROM projects WHERE status = 'active' AND domain LIKE '%PhD%' "
        "ORDER BY priority DESC"
    )
    tasks_phd = db_query(
        "SELECT task_id as id, title, COALESCE(category,'') as project, "
        "'medium' as priority, due_date "
        "FROM tasks WHERE status NOT IN ('done','cancelled') "
        "AND (COALESCE(category,'') LIKE '%PhD%' OR title LIKE '%Article%' OR title LIKE '%article%') "
        "ORDER BY due_date NULLS LAST LIMIT 10"
    )
    return templates.TemplateResponse(
        request,
        "partials/planner_focus.html",
        {
            "phd": phd, "tasks_phd": tasks_phd
        },
    )


# ---------------------------------------------------------------------------
# Timeline (simple project list with due dates)
# ---------------------------------------------------------------------------


@router.get("/api/partial/planner/timeline", response_class=HTMLResponse)
async def planner_timeline(request: Request):
    projects = db_query(
        "SELECT project_id as id, title, domain, status, priority, "
        "created_at as start_date, NULL as target_date "
        "FROM projects WHERE status IN ('active','incubating') "
        "ORDER BY priority DESC"
    )
    return templates.TemplateResponse(
        request,
        "partials/planner_timeline.html",
        {
            "projects": projects
        },
    )
