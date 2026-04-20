"""
routers/metis_tab.py — Metis tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/metis", response_class=HTMLResponse)
async def metis_tab(request: Request):
    return templates.TemplateResponse(
        "metis_tab.html", {"request": request, "active_tab": "metis"}
    )


@router.get("/api/tab/metis", response_class=HTMLResponse)
async def metis_tab_partial(request: Request):
    return templates.TemplateResponse(
        "metis_tab.html", {"request": request, "active_tab": "metis"}
    )
