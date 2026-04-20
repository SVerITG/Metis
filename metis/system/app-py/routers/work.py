"""
routers/work.py — Work tab routes.
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


@router.get("/tab/work", response_class=HTMLResponse)
async def work_tab(request: Request):
    return templates.TemplateResponse(
        "work.html", {"request": request, "active_tab": "work"}
    )


@router.get("/api/tab/work", response_class=HTMLResponse)
async def work_tab_partial(request: Request):
    return templates.TemplateResponse(
        "work.html", {"request": request, "active_tab": "work"}
    )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/stats", response_class=HTMLResponse)
async def work_stats(request: Request):
    today = str(datetime.date.today())
    week_start = (
        datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    ).isoformat()

    open_tasks = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done', 'cancelled')", default=0
    )
    overdue = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done', 'cancelled') "
        "AND due_date IS NOT NULL AND due_date < ?",
        (today,),
        default=0,
    )
    done_week = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE status = 'done' AND updated_at >= ?",
        (week_start,),
        default=0,
    )
    active_projects = db_scalar(
        "SELECT COUNT(*) FROM projects WHERE status = 'active'", default=0
    )
    return templates.TemplateResponse(
        "partials/work_stats.html",
        {
            "request": request,
            "open_tasks": open_tasks,
            "overdue": overdue,
            "done_week": done_week,
            "active_projects": active_projects,
        },
    )


# ---------------------------------------------------------------------------
# Tasks list
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/tasks", response_class=HTMLResponse)
async def work_tasks(request: Request, status: str = "open"):
    if status == "open":
        where = "status NOT IN ('done', 'cancelled')"
        params: tuple = ()
    elif status == "all":
        where = "1=1"
        params = ()
    else:
        where = "status = ?"
        params = (status,)

    tasks = db_query(
        f"SELECT id, title, project, priority, status, due_date "
        f"FROM tasks WHERE {where} "
        f"ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date "
        f"LIMIT 50",
        params,
    )
    return templates.TemplateResponse(
        "partials/work_tasks.html",
        {"request": request, "tasks": tasks, "status_filter": status},
    )


# ---------------------------------------------------------------------------
# Active projects
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/projects", response_class=HTMLResponse)
async def work_projects(request: Request):
    projects = db_query(
        "SELECT id, title, domain, priority, next_step, status "
        "FROM projects WHERE status = 'active' ORDER BY priority DESC LIMIT 10"
    )
    return templates.TemplateResponse(
        "partials/work_projects.html",
        {"request": request, "projects": projects},
    )
