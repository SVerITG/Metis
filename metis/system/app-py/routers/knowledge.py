"""
routers/knowledge.py — Knowledge tab routes.
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar, get_db_path

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
        f"{total} CARDS · {domain_count or 0} COLLECTIONS · {added_week or 0} SOURCES ADDED THIS WEEK"
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


_SORT_MAP = {
    "newest": "CAST(year AS INTEGER) DESC, title ASC",
    "oldest": "CAST(year AS INTEGER) ASC, title ASC",
    "author":  "authors ASC, title ASC",
    "title":   "title ASC",
    "added":   "created_at DESC",
}


def _fetch_library_items(
    q: str = "",
    search_in: str = "all",
    author: str = "",
    year_from: str = "",
    year_to: str = "",
    journal_q: str = "",
    collection: str = "",
    item_type: str = "",
    sort: str = "newest",
    per_page: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Query literature_metadata with PubMed-style filters. Returns (items, total)."""
    where_parts: list[str] = []
    params: list = []

    if q and len(q.strip()) >= 2:
        like = f"%{q.strip()}%"
        if search_in == "title":
            where_parts.append("title LIKE ?")
            params.append(like)
        elif search_in == "authors":
            where_parts.append("authors LIKE ?")
            params.append(like)
        elif search_in == "abstract":
            where_parts.append("abstract LIKE ?")
            params.append(like)
        else:
            where_parts.append(
                "(title LIKE ? OR authors LIKE ? OR abstract LIKE ? OR source LIKE ? OR tags LIKE ?)"
            )
            params.extend([like, like, like, like, like])

    if author and len(author.strip()) >= 2:
        where_parts.append("authors LIKE ?")
        params.append(f"%{author.strip()}%")

    if year_from:
        try:
            where_parts.append("CAST(year AS INTEGER) >= ?")
            params.append(int(year_from))
        except ValueError:
            pass

    if year_to:
        try:
            where_parts.append("CAST(year AS INTEGER) <= ?")
            params.append(int(year_to))
        except ValueError:
            pass

    if journal_q and len(journal_q.strip()) >= 2:
        jlike = f"%{journal_q.strip()}%"
        where_parts.append("(journal LIKE ? OR source LIKE ?)")
        params.extend([jlike, jlike])

    if collection:
        where_parts.append("collection LIKE ?")
        params.append(f"%{collection}%")

    if item_type:
        where_parts.append("item_type = ?")
        params.append(item_type)

    base_filter = (
        "title IS NOT NULL AND title != '' AND title != '[No title found]' "
        "AND id IN (SELECT MAX(id) FROM literature_metadata GROUP BY lower(title))"
    )
    where_sql = "WHERE " + base_filter
    if where_parts:
        where_sql += " AND " + " AND ".join(where_parts)
    p = tuple(params)

    order = _SORT_MAP.get(sort, _SORT_MAP["newest"])

    total = db_scalar(
        f"SELECT COUNT(*) FROM literature_metadata {where_sql}", p, default=0
    )

    rows = db_query(
        f"SELECT id, title, authors, year, source, journal, collection, "
        f"item_type, doi, url, abstract "
        f"FROM literature_metadata {where_sql} "
        f"ORDER BY {order} "
        f"LIMIT {per_page} OFFSET {offset}",
        p,
    ) or []

    items: list[dict] = []
    for r in rows:
        col_str = r.get("collection") or ""
        col_tags = [t.strip() for t in col_str.split(",") if t.strip()] if col_str else []
        src = r.get("source") or r.get("journal") or ""
        abstract = r.get("abstract") or ""
        items.append(
            {
                "id": r.get("id"),
                "title": r.get("title") or "Untitled",
                "authors": r.get("authors") or "",
                "year": r.get("year") or "",
                "source": src,
                "collection_tags": col_tags[:4],
                "item_type": r.get("item_type") or "",
                "doi": r.get("doi") or "",
                "url": r.get("url") or "",
                "abstract": abstract,
                "has_abstract": bool(abstract.strip()),
            }
        )

    return items, total or 0


@router.get("/api/partial/knowledge/library-browser", response_class=HTMLResponse)
async def knowledge_library_browser_panel(
    request: Request,
    q: str = "",
    search_in: str = "all",
    author: str = "",
    year_from: str = "",
    year_to: str = "",
    journal_q: str = "",
    collection: str = "",
    item_type: str = "",
    sort: str = "newest",
):
    """Full library browser: collection chips + search + table. Initial load."""
    coll_rows = db_query(
        "SELECT collection FROM literature_metadata "
        "WHERE collection IS NOT NULL AND collection != ''"
    ) or []
    tag_counts: dict[str, int] = {}
    for r in coll_rows:
        for tag in (r.get("collection") or "").split(","):
            tag = tag.strip()
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    collections = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))

    type_rows = db_query(
        "SELECT DISTINCT item_type FROM literature_metadata "
        "WHERE item_type IS NOT NULL AND item_type != '' ORDER BY item_type"
    ) or []
    item_types = [r.get("item_type", "") for r in type_rows if r.get("item_type")]

    # Top journals for the journal quick-select
    journal_rows = db_query(
        "SELECT journal, COUNT(*) as cnt FROM literature_metadata "
        "WHERE journal IS NOT NULL AND journal != '' "
        "GROUP BY journal ORDER BY cnt DESC LIMIT 12"
    ) or []
    top_journals = [r.get("journal", "") for r in journal_rows if r.get("journal")]

    items, total = _fetch_library_items(
        q=q, search_in=search_in, author=author,
        year_from=year_from, year_to=year_to,
        journal_q=journal_q, collection=collection,
        item_type=item_type, sort=sort,
    )

    active_filter_count = sum(bool(v) for v in [q, author, year_from, year_to, journal_q, collection, item_type])

    return templates.TemplateResponse(
        request,
        "partials/knowledge_library_browser.html",
        {
            "collections": collections,
            "items": items,
            "total": total,
            "q": q,
            "search_in": search_in,
            "author": author,
            "year_from": year_from,
            "year_to": year_to,
            "journal_q": journal_q,
            "active_collection": collection,
            "active_type": item_type,
            "active_sort": sort,
            "item_types": item_types,
            "top_journals": top_journals,
            "active_filter_count": active_filter_count,
        },
    )


@router.get("/api/partial/knowledge/library-table", response_class=HTMLResponse)
async def knowledge_library_table_partial(
    request: Request,
    q: str = "",
    search_in: str = "all",
    author: str = "",
    year_from: str = "",
    year_to: str = "",
    journal_q: str = "",
    collection: str = "",
    item_type: str = "",
    sort: str = "newest",
):
    """Table rows only — swapped in for live search/filter updates."""
    items, total = _fetch_library_items(
        q=q, search_in=search_in, author=author,
        year_from=year_from, year_to=year_to,
        journal_q=journal_q, collection=collection,
        item_type=item_type, sort=sort,
    )
    active_filter_count = sum(bool(v) for v in [q, author, year_from, year_to, journal_q, collection, item_type])
    return templates.TemplateResponse(
        request,
        "partials/knowledge_library_table.html",
        {
            "items": items,
            "total": total,
            "q": q,
            "collection": collection,
            "item_type": item_type,
            "sort": sort,
            "active_filter_count": active_filter_count,
        },
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


@router.get("/api/partial/knowledge/sync-status", response_class=HTMLResponse)
async def knowledge_sync_status(request: Request):
    """Sync status bar for the Zotero library browser."""
    zotero_count = db_scalar(
        "SELECT COUNT(*) FROM literature_metadata WHERE library_source='zotero'", default=0
    ) or 0
    manual_count = db_scalar(
        "SELECT COUNT(*) FROM literature_metadata WHERE library_source NOT IN ('zotero') AND library_source IS NOT NULL",
        default=0,
    ) or 0
    sync_info = {"last_synced": None, "last_version": 0}
    try:
        row = db_query("SELECT last_version, last_synced FROM zotero_sync_state LIMIT 1")
        if row:
            sync_info = row[0]
    except Exception:
        pass
    last = (sync_info.get("last_synced") or "")[:16].replace("T", " ")
    return templates.TemplateResponse(
        request,
        "partials/knowledge_sync_status.html",
        {
            "zotero_count": zotero_count,
            "manual_count": manual_count,
            "last_synced": last or "Never",
            "version": sync_info.get("last_version") or 0,
        },
    )


@router.post("/api/knowledge/sync-zotero")
async def trigger_zotero_sync():
    """Trigger an incremental Zotero sync. Runs the sync logic inline."""
    import re
    from datetime import datetime

    rc_root = os.environ.get("METIS_RC_ROOT", "")
    env_path = Path(rc_root) / "system" / ".env" if rc_root else None
    if env_path and env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    api_key = os.environ.get("ZOTERO_API_KEY", "")
    user_id = os.environ.get("ZOTERO_USER_ID", "")
    group_id = os.environ.get("ZOTERO_GROUP_ID", "")

    if not api_key:
        return JSONResponse(
            {"status": "error", "message": "ZOTERO_API_KEY not set in system/.env"},
            status_code=400,
        )
    if not user_id and not group_id:
        return JSONResponse(
            {"status": "error", "message": "ZOTERO_USER_ID not set in system/.env"},
            status_code=400,
        )

    try:
        from pyzotero import zotero as pyz
    except ImportError:
        return JSONResponse(
            {"status": "error", "message": "pyzotero not installed — run: pip install pyzotero"},
            status_code=500,
        )

    try:
        zot = pyz.Zotero(group_id or user_id, "group" if group_id else "user", api_key)

        _SYNC_DDL = """CREATE TABLE IF NOT EXISTS zotero_sync_state (
            id INTEGER PRIMARY KEY, last_version INTEGER DEFAULT 0,
            last_synced TEXT, item_count INTEGER DEFAULT 0)"""
        _LIT_EXTRA = {
            "abstract": "TEXT DEFAULT ''", "journal": "TEXT DEFAULT ''",
            "item_type": "TEXT DEFAULT ''", "url": "TEXT DEFAULT ''",
            "zotero_key": "TEXT DEFAULT ''", "zotero_version": "INTEGER DEFAULT 0",
            "collection": "TEXT DEFAULT ''", "library_source": "TEXT DEFAULT 'manual'",
        }

        import sqlite3 as _sq3
        db_path = Path(rc_root) / "system" / "app" / "data" / "metis.sqlite" if rc_root else None
        if not db_path or not db_path.exists():
            return JSONResponse({"status": "error", "message": "Database not found."}, status_code=500)

        con = _sq3.connect(str(db_path))
        con.row_factory = _sq3.Row
        con.execute(_SYNC_DDL)
        existing_cols = {r[1] for r in con.execute("PRAGMA table_info(literature_metadata)")}
        for col, dtype in _LIT_EXTRA.items():
            if col not in existing_cols:
                con.execute(f"ALTER TABLE literature_metadata ADD COLUMN {col} {dtype}")
        con.commit()

        row = con.execute("SELECT last_version FROM zotero_sync_state LIMIT 1").fetchone()
        last_version = row["last_version"] if row else 0

        items = zot.everything(zot.items(since=last_version, itemType="-attachment || -note")) if last_version else zot.everything(zot.items(itemType="-attachment || -note"))

        added = updated = skipped = 0
        for item in items:
            data = item.get("data", {})
            if data.get("itemType") in ("attachment", "note"):
                skipped += 1
                continue
            title = (data.get("title") or "")[:500]
            if not title:
                skipped += 1
                continue

            creators = data.get("creators", [])
            authors = "; ".join(
                (c["lastName"] + (f", {c['firstName'][0]}." if c.get("firstName") else ""))
                if c.get("lastName") else c.get("name", "")
                for c in creators[:8]
                if c.get("lastName") or c.get("name")
            )[:300]

            raw_date = data.get("date", "") or ""
            ym = re.search(r"\b(19|20)\d{2}\b", raw_date)
            year = int(ym.group()) if ym else None
            journal = data.get("publicationTitle") or ""
            source = journal or data.get("bookTitle") or data.get("publisher") or ""
            doi = data.get("DOI") or ""
            abstract = (data.get("abstractNote") or "")[:2000]
            url = data.get("url") or (f"https://doi.org/{doi}" if doi else "")
            item_type = data.get("itemType") or ""
            zotero_key = data.get("key") or ""
            zotero_version = item.get("version") or 0
            tags = ",".join(t.get("tag", "") for t in data.get("tags", [])[:12])
            collection = ",".join(
                c for c in (data.get("_collections_names") or [])
            ) if data.get("_collections_names") else ""

            existing = con.execute(
                "SELECT id FROM literature_metadata WHERE zotero_key=?", (zotero_key,)
            ).fetchone()
            if existing:
                con.execute(
                    """UPDATE literature_metadata SET title=?,authors=?,year=?,source=?,journal=?,
                       tags=?,doi=?,abstract=?,url=?,item_type=?,zotero_version=?,library_source=?
                       WHERE zotero_key=?""",
                    (title, authors, year, source, journal, tags, doi, abstract, url,
                     item_type, zotero_version, "zotero", zotero_key),
                )
                updated += 1
            else:
                con.execute(
                    """INSERT INTO literature_metadata
                       (title,authors,year,source,journal,tags,doi,abstract,url,
                        item_type,zotero_key,zotero_version,library_source,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (title, authors, year, source, journal, tags, doi, abstract, url,
                     item_type, zotero_key, zotero_version, "zotero", datetime.now().isoformat()),
                )
                added += 1

        try:
            new_version = zot.last_modified_version()
            total = con.execute(
                "SELECT COUNT(*) FROM literature_metadata WHERE library_source='zotero'"
            ).fetchone()[0]
            con.execute("DELETE FROM zotero_sync_state")
            con.execute(
                "INSERT INTO zotero_sync_state (last_version,last_synced,item_count) VALUES (?,?,?)",
                (new_version, datetime.now().isoformat(), total),
            )
        except Exception:
            pass
        con.commit()
        con.close()

        msg = f"Sync complete — {added} added, {updated} updated, {skipped} skipped."
        return JSONResponse({"status": "ok", "message": msg, "added": added, "updated": updated})

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/api/partial/knowledge/news-signals", response_class=HTMLResponse)
async def knowledge_news_signals(request: Request):
    """Recent news signals from news_briefs, shown in the Knowledge tab."""
    signals: list[dict] = db_query(
        "SELECT title, domain, signal_strength, summary, source_url, created_at "
        "FROM news_briefs ORDER BY created_at DESC LIMIT 40"
    ) or []

    domains: dict[str, list[dict]] = {}
    for s in signals:
        d = s.get("domain") or "General"
        domains.setdefault(d, []).append(s)

    return templates.TemplateResponse(
        request,
        "partials/knowledge_news_signals.html",
        {"domains": domains, "total": len(signals)},
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


@router.get("/api/partial/knowledge/memory-search", response_class=HTMLResponse)
async def knowledge_memory_search(request: Request, q: str = ""):
    """Semantic search across episodic, semantic, and procedural memory layers."""
    if not q or len(q.strip()) < 2:
        return HTMLResponse(
            '<div class="empty-row">Type at least 2 characters to search your memory.</div>'
        )

    import json as _json

    results: list[dict] = []

    # Try vector search via observation/vector_memory layer
    try:
        from metis_mcp.embeddings import embed_one
        import struct, sqlite_vec

        query_vec = embed_one(q.strip())
        blob = struct.pack(f"{len(query_vec)}f", *query_vec)
        db_path = get_db_path() if callable(get_db_path) else None

        if db_path:
            import sqlite3
            con = sqlite3.connect(str(db_path))
            con.row_factory = sqlite3.Row
            con.enable_load_extension(True)
            sqlite_vec.load(con)
            con.enable_load_extension(False)

            rows = con.execute(
                """SELECT e.id, e.event_type, e.content, e.metadata, e.created_at,
                          v.distance
                   FROM vec_episodic v
                   JOIN episodic_memory e ON e.id = v.rowid
                   ORDER BY v.distance ASC LIMIT 12""",
                (blob,),
            ).fetchall()
            for r in rows:
                row = dict(r)
                meta = {}
                try:
                    meta = _json.loads(row.get("metadata") or "{}")
                except Exception:
                    pass
                row["classification"] = meta.get("classification") or row.get("event_type") or "note"
                row["concepts"]       = meta.get("concepts") or []
                row["agent_slug"]     = meta.get("agent_slug") or ""
                row["score"]          = round(1 - float(row.get("distance") or 1), 3)
                results.append(row)
            con.close()
    except Exception:
        pass

    # Fallback: keyword LIKE across all memory tables
    if not results:
        like = f"%{q}%"
        raw = db_query(
            "SELECT id, event_type, content, metadata, created_at, 0 as distance "
            "FROM episodic_memory WHERE content LIKE ? ORDER BY created_at DESC LIMIT 12",
            (like,),
            default=[],
        ) or []
        for r in raw:
            row = dict(r)
            meta = {}
            try:
                meta = _json.loads(row.get("metadata") or "{}")
            except Exception:
                pass
            row["classification"] = meta.get("classification") or row.get("event_type") or "note"
            row["concepts"]       = meta.get("concepts") or []
            row["agent_slug"]     = meta.get("agent_slug") or ""
            row["score"]          = None
            results.append(row)

    return templates.TemplateResponse(
        request,
        "partials/knowledge_memory_search.html",
        {"results": results, "q": q},
    )
