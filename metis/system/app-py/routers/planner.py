"""
routers/planner.py — Planner tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/planner", response_class=HTMLResponse)
async def planner_tab(request: Request):
    return templates.TemplateResponse(
        "planner.html", {"request": request, "active_tab": "planner"}
    )


@router.get("/api/tab/planner", response_class=HTMLResponse)
async def planner_tab_partial(request: Request):
    return templates.TemplateResponse(
        "planner.html", {"request": request, "active_tab": "planner"}
    )
