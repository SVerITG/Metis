"""
routers/learning.py — Learning tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/learning", response_class=HTMLResponse)
async def learning_tab(request: Request):
    return templates.TemplateResponse(
        "learning.html", {"request": request, "active_tab": "learning"}
    )


@router.get("/api/tab/learning", response_class=HTMLResponse)
async def learning_tab_partial(request: Request):
    return templates.TemplateResponse(
        "learning.html", {"request": request, "active_tab": "learning"}
    )
