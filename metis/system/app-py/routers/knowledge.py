"""
routers/knowledge.py — Knowledge tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/knowledge", response_class=HTMLResponse)
async def knowledge_tab(request: Request):
    return templates.TemplateResponse(
        "knowledge.html", {"request": request, "active_tab": "knowledge"}
    )


@router.get("/api/tab/knowledge", response_class=HTMLResponse)
async def knowledge_tab_partial(request: Request):
    return templates.TemplateResponse(
        "knowledge.html", {"request": request, "active_tab": "knowledge"}
    )
