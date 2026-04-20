"""
routers/work.py — Work tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
