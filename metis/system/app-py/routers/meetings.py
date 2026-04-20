"""
routers/meetings.py — Meetings tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/meetings", response_class=HTMLResponse)
async def meetings_tab(request: Request):
    return templates.TemplateResponse(
        "meetings.html", {"request": request, "active_tab": "meetings"}
    )


@router.get("/api/tab/meetings", response_class=HTMLResponse)
async def meetings_tab_partial(request: Request):
    return templates.TemplateResponse(
        "meetings.html", {"request": request, "active_tab": "meetings"}
    )
