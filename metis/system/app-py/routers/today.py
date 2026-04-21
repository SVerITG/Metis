"""
routers/today.py — Today tab routes and all today-related partials.
"""

import datetime
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


# ---------------------------------------------------------------------------
# Full-page + HTMX partial for the Today tab
# ---------------------------------------------------------------------------


@router.get("/tab/today", response_class=HTMLResponse)
async def today_tab(request: Request):
    return templates.TemplateResponse(
     request, "today.html", {"active_tab": "today"}
 )


@router.get("/api/tab/today", response_class=HTMLResponse)
async def today_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "today.html", {"active_tab": "today"}
 )


# ---------------------------------------------------------------------------
# Greeting partial
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/greeting", response_class=HTMLResponse)
async def today_greeting(request: Request):
    today = datetime.date.today()
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    today_label = today.strftime("%A, %d %B %Y")

    try:
        open_tasks = db_scalar("SELECT COUNT(*) FROM tasks WHERE status != 'done'")
        overdue = db_scalar(
            "SELECT COUNT(*) FROM tasks WHERE status != 'done' AND due_date <= ?",
            (str(today),),
        )
        morning_runs = db_query(
            "SELECT agent_slug FROM agent_runs "
            "WHERE agent_slug IN ('news-radar','librarian') AND DATE(started_at) = ?",
            (str(today),),
        )
    except Exception:
        open_tasks = 0
        overdue = 0
        morning_runs = []

    return templates.TemplateResponse(
        request,
        "partials/today_greeting.html",
        {
            "greeting": greeting,
            "today_label": today_label,
            "open_tasks": open_tasks,
            "overdue": overdue,
            "morning_runs": morning_runs,
        },
    )


# ---------------------------------------------------------------------------
# Overnight summary partial
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/overnight", response_class=HTMLResponse)
async def today_overnight(request: Request):
    since = (
        datetime.datetime.now() - datetime.timedelta(hours=24)
    ).isoformat()

    try:
        news = db_scalar(
            "SELECT COUNT(*) FROM news_briefs WHERE created_at >= ?", (since,)
        )
        ideas = db_scalar(
            "SELECT COUNT(*) FROM ideas WHERE created_at >= ?", (since,)
        )
        meetings = db_scalar(
            "SELECT COUNT(*) FROM meetings WHERE created_at >= ?", (since,)
        )
    except Exception:
        news = 0
        ideas = 0
        meetings = 0

    return templates.TemplateResponse(
        request,
        "partials/today_overnight.html",
        {
            "news": news,
            "ideas": ideas,
            "meetings": meetings,
        },
    )


# ---------------------------------------------------------------------------
# Focus partial
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/focus", response_class=HTMLResponse)
async def today_focus(request: Request):
    try:
        projects = db_query(
            "SELECT title, domain, priority, next_step "
            "FROM projects WHERE status='active' ORDER BY priority DESC LIMIT 1"
        )
        project = projects[0] if projects else None
    except Exception:
        project = None

    return templates.TemplateResponse(
        request,
        "partials/today_focus.html",
        {
            "project": project
        },
    )


# ---------------------------------------------------------------------------
# Scan partial
# ---------------------------------------------------------------------------


@router.post("/api/partial/today/scan", response_class=HTMLResponse)
async def today_scan(request: Request):
    scan_results = []
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=rc_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                scan_results.append(
                    {
                        "type": "git",
                        "message": "Uncommitted changes in Research Cortex",
                    }
                )
            else:
                scan_results.append(
                    {"type": "ok", "message": "Research Cortex is clean"}
                )
        except Exception:
            scan_results.append(
                {"type": "info", "message": "Could not run git status"}
            )

    if not scan_results:
        scan_results.append({"type": "ok", "message": "Nothing to report"})

    return templates.TemplateResponse(
        request,
        "partials/today_scan.html",
        {
            "results": scan_results
        },
    )


# ---------------------------------------------------------------------------
# Token footer partial
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/token-footer", response_class=HTMLResponse)
async def today_token_footer(request: Request):
    today = str(datetime.date.today())
    try:
        total_tokens = db_scalar(
            "SELECT COALESCE(SUM(tokens_used), 0) FROM agent_runs "
            "WHERE DATE(started_at) = ?",
            (today,),
        )
        runs_today = db_scalar(
            "SELECT COUNT(*) FROM agent_runs WHERE DATE(started_at) = ?",
            (today,),
        )
    except Exception:
        total_tokens = 0
        runs_today = 0

    return templates.TemplateResponse(
        request,
        "partials/today_token_footer.html",
        {
            "total_tokens": total_tokens,
            "runs_today": runs_today,
        },
    )
