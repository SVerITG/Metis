"""
routers/knowledge.py — Knowledge tab routes.
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/knowledge", response_class=HTMLResponse)
async def knowledge_tab(request: Request):
    return templates.TemplateResponse(
     request, "knowledge.html", {"active_tab": "knowledge"}
 )


@router.get("/api/tab/knowledge", response_class=HTMLResponse)
async def knowledge_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "knowledge.html", {"active_tab": "knowledge"}
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
        request,
        "partials/knowledge_stats.html",
        {
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
        request,
        "partials/knowledge_library.html",
        {
            "cards": cards
        },
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
        request,
        "partials/knowledge_literature.html",
        {
            "items": items
        },
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
        request,
        "partials/knowledge_domains.html",
        {
            "domains": domains
        },
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
        request,
        "partials/knowledge_search.html",
        {
            "results": results, "q": q
        },
    )


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter parser — same logic as knowledge_graph.py tool."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    result: dict = {}
    current_key = None
    current_list = None
    for line in block.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- "):
            val = s[2:].strip().strip('"').strip("'")
            if current_list is not None:
                current_list.append(val)
            continue
        if ":" in s:
            colon = s.index(":")
            key = s[:colon].strip()
            val = s[colon + 1:].strip().strip('"').strip("'")
            current_key = key
            if val == "":
                current_list = []
                result[key] = current_list
            else:
                result[key] = val
                current_list = None
    return result


# ---------------------------------------------------------------------------
# Archive-layout partials (v8.1 — Knowledge surface redesign)
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/stats-meta", response_class=HTMLResponse)
async def knowledge_stats_meta(request: Request):
    """Returns a one-liner for the page-head meta area."""
    import datetime as _dt

    card_count = db_scalar("SELECT COUNT(*) FROM library_cards", default=0)
    domain_count = db_scalar("SELECT COUNT(DISTINCT domain) FROM library_cards", default=0)
    lit_count = db_scalar("SELECT COUNT(*) FROM literature_metadata", default=0)
    week_ago = (_dt.datetime.now() - _dt.timedelta(days=7)).isoformat()
    added_week = db_scalar(
        "SELECT COUNT(*) FROM literature_metadata WHERE created_at >= ?",
        (week_ago,),
        default=0,
    )
    total = (card_count or 0) + (lit_count or 0)
    return HTMLResponse(
        f"{total} CARDS · {domain_count or 0} SLIPCASES · {added_week or 0} SOURCES ADDED THIS WEEK"
    )


@router.get("/api/partial/knowledge/slipcases", response_class=HTMLResponse)
async def knowledge_slipcases(request: Request):
    """Slipcase sidebar: domain list with card counts."""
    domains = []
    try:
        rows = db_query(
            "SELECT domain, COUNT(*) as count FROM library_cards "
            "GROUP BY domain ORDER BY count DESC"
        ) or []
        for r in rows:
            domains.append({"name": r.get("domain") or "Unfiled", "count": r.get("count") or 0})
    except Exception:
        pass

    # Also add literature buckets if no library_cards domains
    if not domains:
        try:
            rows = db_query(
                "SELECT source as domain, COUNT(*) as count FROM literature_metadata "
                "GROUP BY source ORDER BY count DESC LIMIT 8"
            ) or []
            for r in rows:
                domains.append({"name": r.get("domain") or "General", "count": r.get("count") or 0})
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "partials/knowledge_slipcases.html",
        {"domains": domains},
    )


@router.get("/api/partial/knowledge/cards", response_class=HTMLResponse)
async def knowledge_cards(request: Request):
    """3-column index card grid from library_cards."""
    cards = db_query(
        "SELECT id, title, domain, summary, tags, created_at "
        "FROM library_cards ORDER BY created_at DESC LIMIT 12"
    )
    total_cards = db_scalar("SELECT COUNT(*) FROM library_cards", default=0)
    first_domain = None
    try:
        row = db_query(
            "SELECT domain, COUNT(*) as cnt FROM library_cards GROUP BY domain ORDER BY cnt DESC LIMIT 1"
        )
        if row:
            first_domain = row[0].get("domain")
    except Exception:
        pass
    return templates.TemplateResponse(
        request,
        "partials/knowledge_cards.html",
        {"cards": cards, "total_cards": total_cards, "first_domain": first_domain},
    )


@router.get("/api/partial/knowledge/sources", response_class=HTMLResponse)
async def knowledge_sources(request: Request):
    """Sources table from literature_metadata, recently clipped."""
    _tag_colors = {
        "book": "var(--m-accent)",
        "paper": "var(--m-info)",
        "lecture": "var(--m-ochre-deep)",
        "essay": "var(--m-accent)",
        "article": "var(--m-accent)",
    }
    sources = []
    try:
        rows = db_query(
            "SELECT id, title, authors, year, source, tags, doi, created_at "
            "FROM literature_metadata ORDER BY created_at DESC LIMIT 8"
        ) or []
        for r in rows:
            journal = r.get("source") or "ARTICLE"
            tag = "PAPER" if journal else "ARTICLE"
            tag_key = tag.lower()
            by_parts = []
            if r.get("authors"):
                by_parts.append(r["authors"][:50])
            if r.get("year"):
                by_parts.append(str(r["year"])[:4])
            if journal:
                by_parts.append(journal[:30])
            created = r.get("created_at") or ""
            when = created[:10] if created else "—"
            sources.append({
                "title": r.get("title") or "Untitled",
                "by": " · ".join(by_parts),
                "tag": tag,
                "tag_color": _tag_colors.get(tag_key, "var(--m-muted)"),
                "when": when,
                "doi": r.get("doi") or "",
            })
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/knowledge_sources.html",
        {"sources": sources},
    )


@router.get("/api/knowledge/graph-data")
async def knowledge_graph_data():
    """Return graph nodes + edges as JSON for D3 rendering."""
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    library_root = Path(rc_root) / "knowledge" / "library" if rc_root else None

    nodes = []
    links = []
    seen_links: set = set()

    if library_root and library_root.exists():
        for md_file in sorted(library_root.rglob("*.md")):
            rel = str(md_file.relative_to(library_root))
            try:
                text = md_file.read_text(encoding="utf-8", errors="replace")
                fm = _parse_frontmatter(text)
                if not fm:
                    continue
                tags = fm.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]
                related = fm.get("related", [])
                if isinstance(related, str):
                    related = [related]
                nodes.append({
                    "id": rel,
                    "title": fm.get("title", md_file.stem),
                    "domain": fm.get("domain", "unknown"),
                    "tags": tags[:6],
                    "phd_relevance": fm.get("phd_relevance", "medium"),
                    "status": fm.get("status", "current"),
                })
                for target in related:
                    t = target.strip().strip('"').strip("'")
                    key = tuple(sorted([rel, t]))
                    if key not in seen_links:
                        seen_links.add(key)
                        links.append({"source": rel, "target": t})
            except Exception:
                continue

    return JSONResponse({"nodes": nodes, "links": links})


@router.get("/api/partial/knowledge/graph", response_class=HTMLResponse)
async def knowledge_graph_partial(request: Request):
    """Return the graph view partial (D3 force-directed graph)."""
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    library_root = Path(rc_root) / "knowledge" / "library" if rc_root else None

    # Count indexed edges
    edge_count = db_scalar("SELECT COUNT(*) FROM note_links", default=0)
    node_count = 0
    if library_root and library_root.exists():
        node_count = sum(1 for f in library_root.rglob("*.md"))

    return templates.TemplateResponse(
        request,
        "partials/knowledge_graph.html",
        {"node_count": node_count, "edge_count": edge_count},
    )
