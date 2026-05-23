"""
routers/planner.py — Planner tab routes.
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


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/planner/meta", response_class=HTMLResponse)
async def planner_meta(request: Request):
    today = datetime.date.today()
    week_num = today.isocalendar()[1]
    quarter = (today.month - 1) // 3 + 1
    quarter_end = datetime.date(today.year, [3, 6, 9, 12][quarter - 1], [31, 30, 30, 31][quarter - 1])
    weeks_left = max(0, (quarter_end - today).days // 7)
    return HTMLResponse(f"WEEK {week_num} · Q{quarter} · {weeks_left} WEEKS REMAINING")


@router.get("/api/partial/planner/week-label", response_class=HTMLResponse)
async def planner_week_label(request: Request):
    today = datetime.date.today()
    week_num = today.isocalendar()[1]
    mon = today - datetime.timedelta(days=today.weekday())
    sun = mon + datetime.timedelta(days=6)
    return HTMLResponse(f"WEEK {week_num} · {mon.strftime('%b %-d').upper()} → {sun.strftime('%b %-d').upper()}")


@router.get("/api/partial/planner/horizon", response_class=HTMLResponse)
async def planner_horizon(request: Request):
    today = datetime.date.today()
    week_num = today.isocalendar()[1]
    quarter = (today.month - 1) // 3 + 1
    quarter_end = datetime.date(today.year, [3, 6, 9, 12][quarter - 1], [31, 30, 30, 31][quarter - 1])
    weeks_left = max(0, (quarter_end - today).days // 7)

    open_tasks = db_scalar("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','cancelled')", default=0) or 0
    done_tasks = db_scalar("SELECT COUNT(*) FROM tasks WHERE status='done'", default=0) or 0
    total_tasks = open_tasks + done_tasks
    q_pct = round(done_tasks / max(total_tasks, 1) * 100)

    week_start = (today - datetime.timedelta(days=today.weekday())).isoformat()
    week_done = db_scalar("SELECT COUNT(*) FROM tasks WHERE status='done' AND updated_at >= ?", (week_start,), default=0) or 0
    week_open = db_scalar("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','cancelled') AND due_date >= ?", (week_start,), default=0) or 0

    today_tasks = db_query(
        "SELECT title FROM tasks WHERE status NOT IN ('done','cancelled') AND due_date = ? ORDER BY priority DESC LIMIT 3",
        (today.isoformat(),)
    ) or []
    today_title = today_tasks[0]["title"] if today_tasks else "No tasks due today"

    cards = [
        {
            "label": f"QUARTER · Q{quarter} {['JAN–MAR','APR–JUN','JUL–SEP','OCT–DEC'][quarter-1]}",
            "title": f"{weeks_left} weeks remaining",
            "body": f"{done_tasks} tasks done · {open_tasks} open",
            "pct": q_pct,
            "meta": f"{done_tasks} of {total_tasks} tasks · Q{quarter} target",
        },
        {
            "label": f"WEEK · {week_num}",
            "title": f"{week_open} tasks this week",
            "body": f"{week_done} done since Monday",
            "pct": round(week_done / max(week_done + week_open, 1) * 100),
            "meta": f"{week_done} done · {week_open} open",
        },
        {
            "label": f"TODAY · {today.strftime('%a %-d').upper()}",
            "title": today_title[:60] if today_title != "No tasks due today" else "No tasks due today",
            "body": f"{len(today_tasks)} task{'s' if len(today_tasks) != 1 else ''} due today" if today_tasks else "Clear slate.",
            "pct": 0,
            "meta": today.strftime("%A, %-d %B").upper(),
        },
    ]
    return templates.TemplateResponse(
        request,
        "partials/planner_horizon.html",
        {"cards": cards},
    )


@router.get("/api/partial/planner/week", response_class=HTMLResponse)
async def planner_week(request: Request):
    today = datetime.date.today()
    mon = today - datetime.timedelta(days=today.weekday())
    days = [mon + datetime.timedelta(days=i) for i in range(7)]
    day_tasks = {}
    for d in days:
        rows = db_query(
            "SELECT title, priority FROM tasks WHERE status NOT IN ('done','cancelled') AND due_date = ? ORDER BY priority DESC LIMIT 5",
            (d.isoformat(),)
        ) or []
        day_tasks[d.isoformat()] = rows
    return templates.TemplateResponse(
        request,
        "partials/planner_week.html",
        {"days": days, "day_tasks": day_tasks, "today": today},
    )


@router.get("/api/partial/planner/intentions", response_class=HTMLResponse)
async def planner_intentions(request: Request):
    projects = db_query(
        "SELECT project_id as id, title, priority FROM projects WHERE status IN ('active','incubating') ORDER BY priority DESC LIMIT 5"
    ) or []
    return templates.TemplateResponse(
        request,
        "partials/planner_intentions.html",
        {"projects": projects},
    )


@router.get("/api/partial/planner/notes", response_class=HTMLResponse)
async def planner_notes(request: Request):
    overdue = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','cancelled') AND due_date < ?",
        (datetime.date.today().isoformat(),),
        default=0,
    ) or 0
    old_open = db_query(
        "SELECT title FROM tasks WHERE status NOT IN ('done','cancelled') AND created_at < ? ORDER BY created_at LIMIT 1",
        ((datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),),
    ) or []
    note_title = old_open[0]["title"] if old_open else None
    return templates.TemplateResponse(
        request,
        "partials/planner_notes.html",
        {"overdue": overdue, "stale_task": note_title},
    )


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
    done = db_query(
        "SELECT project_id as id, title, domain, priority FROM projects WHERE status = 'done' ORDER BY updated_at DESC LIMIT 8"
    )
    return templates.TemplateResponse(
        request,
        "partials/planner_kanban.html",
        {
            "someday": someday,
            "incubating": incubating,
            "active": active,
            "done": done,
        },
    )


# ---------------------------------------------------------------------------
# Focus board (research-centric)
# ---------------------------------------------------------------------------


@router.get("/api/partial/planner/focus", response_class=HTMLResponse)
async def planner_focus(request: Request):
    phd = db_query(
        "SELECT project_id, title, next_step FROM projects "
        "WHERE status = 'active' AND COALESCE(domain,'') NOT LIKE '%phd%' "
        "  AND project_id NOT IN ('personal','phd-framework') "
        "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 6"
    )
    tasks_phd = db_query(
        "SELECT t.task_id as id, t.title, t.status, t.due_date "
        "FROM tasks t JOIN projects p ON p.project_id = t.project_id "
        "WHERE t.status NOT IN ('done','cancelled') "
        "  AND p.status = 'active' "
        "  AND COALESCE(p.domain,'') NOT LIKE '%phd%' "
        "  AND t.project_id NOT IN ('personal','phd-framework') "
        "ORDER BY CASE COALESCE(t.priority,'medium') WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 10"
    )
    return templates.TemplateResponse(
        request,
        "partials/planner_focus.html",
        {
            "phd": phd, "tasks_phd": tasks_phd
        },
    )


# ---------------------------------------------------------------------------
# Focus board — top 3 active projects with open task counts
# ---------------------------------------------------------------------------


@router.get("/api/partial/planner/focus-board", response_class=HTMLResponse)
async def planner_focus_board(request: Request):
    """Top 3 active projects with their open task count."""
    projects = db_query(
        "SELECT project_id, title, domain, priority, next_step "
        "FROM projects WHERE status = 'active' "
        "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
        "         updated_at DESC NULLS LAST LIMIT 3",
        default=[],
    ) or []

    cards = []
    for p in projects:
        pid = p.get("project_id")
        open_tasks = db_scalar(
            "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status NOT IN ('done','cancelled')",
            (pid,),
            default=0,
        ) or 0
        cards.append({
            "id": pid,
            "title": p.get("title") or "Untitled project",
            "domain": p.get("domain") or "",
            "priority": p.get("priority") or "medium",
            "next_step": p.get("next_step") or "",
            "open_tasks": open_tasks,
        })

    return templates.TemplateResponse(
        request,
        "partials/planner_focus_board.html",
        {"cards": cards},
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
