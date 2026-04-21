"""
routers/meetings.py — Meetings tab routes.
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


@router.get("/tab/meetings", response_class=HTMLResponse)
async def meetings_tab(request: Request):
    return templates.TemplateResponse(
     request, "meetings.html", {"active_tab": "meetings"}
 )


@router.get("/api/tab/meetings", response_class=HTMLResponse)
async def meetings_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "meetings.html", {"active_tab": "meetings"}
 )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/stats", response_class=HTMLResponse)
async def meetings_stats(request: Request):
    total = db_scalar("SELECT COUNT(*) FROM meetings", default=0)
    month_start = datetime.date.today().replace(day=1).isoformat()
    this_month = db_scalar(
        "SELECT COUNT(*) FROM meetings WHERE date >= ?", (month_start,), default=0
    )
    open_actions = db_scalar(
        "SELECT COUNT(*) FROM meeting_actions WHERE status != 'done'", default=0
    )
    avg_dur = db_scalar(
        "SELECT ROUND(AVG(duration_minutes)) FROM meetings WHERE duration_minutes IS NOT NULL",
        default=0,
    )
    return templates.TemplateResponse(
        request,
        "partials/meetings_stats.html",
        {
            "total": total,
            "this_month": this_month,
            "open_actions": open_actions,
            "avg_dur": avg_dur,
        },
    )


# ---------------------------------------------------------------------------
# Meeting list
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/list", response_class=HTMLResponse)
async def meetings_list(request: Request, filter: str = "month"):
    if filter == "week":
        cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    elif filter == "month":
        cutoff = datetime.date.today().replace(day=1).isoformat()
    else:
        cutoff = "2000-01-01"

    meetings = db_query(
        "SELECT id, date, title, participants, duration_minutes, status "
        "FROM meetings WHERE date >= ? ORDER BY date DESC LIMIT 100",
        (cutoff,),
    )
    return templates.TemplateResponse(
        request,
        "partials/meetings_list.html",
        {
            "meetings": meetings
        },
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/search", response_class=HTMLResponse)
async def meetings_search(request: Request, q: str = ""):
    if not q or len(q) < 2:
        # Return full list on empty search
        meetings = db_query(
            "SELECT id, date, title, participants, duration_minutes, status "
            "FROM meetings ORDER BY date DESC LIMIT 100"
        )
    else:
        pattern = f"%{q}%"
        meetings = db_query(
            "SELECT id, date, title, participants, duration_minutes, status "
            "FROM meetings WHERE title LIKE ? OR participants LIKE ? "
            "ORDER BY date DESC LIMIT 50",
            (pattern, pattern),
        )
    return templates.TemplateResponse(
        request,
        "partials/meetings_list.html",
        {
            "meetings": meetings
        },
    )
