"""
routers/knowledge.py — Knowledge tab routes.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar

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


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/stats", response_class=HTMLResponse)
async def knowledge_stats(request: Request):
    import datetime

    cards = db_scalar("SELECT COUNT(*) FROM library_cards", default=0)
    domains = db_scalar("SELECT COUNT(DISTINCT domain) FROM library_cards", default=0)
    lit = db_scalar("SELECT COUNT(*) FROM literature_metadata", default=0)
    month_start = datetime.date.today().replace(day=1).isoformat()
    new_this_month = db_scalar(
        "SELECT COUNT(*) FROM literature_metadata WHERE created_at >= ?",
        (month_start,),
        default=0,
    )
    return templates.TemplateResponse(
        "partials/knowledge_stats.html",
        {
            "request": request,
            "cards": cards,
            "domains": domains,
            "lit": lit,
            "new_this_month": new_this_month,
        },
    )


# ---------------------------------------------------------------------------
# Library cards
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/library", response_class=HTMLResponse)
async def knowledge_library(request: Request):
    cards = db_query(
        "SELECT id, title, domain, tags, summary, created_at "
        "FROM library_cards ORDER BY created_at DESC LIMIT 50"
    )
    return templates.TemplateResponse(
        "partials/knowledge_library.html",
        {"request": request, "cards": cards},
    )


# ---------------------------------------------------------------------------
# Literature
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/literature", response_class=HTMLResponse)
async def knowledge_literature(request: Request):
    items = db_query(
        "SELECT id, title, authors, year, source, tags, created_at "
        "FROM literature_metadata ORDER BY created_at DESC LIMIT 50"
    )
    return templates.TemplateResponse(
        "partials/knowledge_literature.html",
        {"request": request, "items": items},
    )


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/domains", response_class=HTMLResponse)
async def knowledge_domains(request: Request):
    domains = db_query(
        "SELECT domain, COUNT(*) as card_count "
        "FROM library_cards GROUP BY domain ORDER BY card_count DESC"
    )
    return templates.TemplateResponse(
        "partials/knowledge_domains.html",
        {"request": request, "domains": domains},
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/search", response_class=HTMLResponse)
async def knowledge_search(request: Request, q: str = ""):
    if not q or len(q) < 2:
        return HTMLResponse(
            '<p class="text-muted small">Type at least 2 characters to search.</p>'
        )
    pattern = f"%{q}%"
    results = db_query(
        "SELECT 'library' as source_type, id, title, domain as subtitle, created_at "
        "FROM library_cards WHERE title LIKE ? OR tags LIKE ? OR summary LIKE ? "
        "UNION ALL "
        "SELECT 'literature' as source_type, id, title, authors as subtitle, created_at "
        "FROM literature_metadata WHERE title LIKE ? OR authors LIKE ? OR tags LIKE ? "
        "ORDER BY created_at DESC LIMIT 30",
        (pattern, pattern, pattern, pattern, pattern, pattern),
    )
    return templates.TemplateResponse(
        "partials/knowledge_search.html",
        {"request": request, "results": results, "q": q},
    )
