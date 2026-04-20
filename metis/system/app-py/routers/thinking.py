"""
routers/thinking.py — Thinking tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
