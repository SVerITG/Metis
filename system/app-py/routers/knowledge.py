"""
routers/knowledge.py — Knowledge tab routes.
"""

import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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


@router.get("/api/search", response_class=HTMLResponse)
async def global_search(request: Request, q: str = ""):
    """Global search across papers, projects, news, and tasks."""
    q = q.strip()
    if len(q) < 2:
        return HTMLResponse("")
    like = f"%{q}%"
    papers, projects, news, tasks = [], [], [], []
    try:
        papers = db_query(
            "SELECT id, title, authors, year FROM literature_metadata "
            "WHERE title LIKE ? OR authors LIKE ? ORDER BY created_at DESC LIMIT 7",
            (like, like),
        ) or []
    except Exception:
        pass
    try:
        projects = db_query(
            "SELECT id, title, description FROM projects "
            "WHERE title LIKE ? OR description LIKE ? ORDER BY updated_at DESC LIMIT 5",
            (like, like),
        ) or []
    except Exception:
        pass
    try:
        news = db_query(
            "SELECT rowid as id, title, domain, source_url, COALESCE(relevance,0) as relevance "
            "FROM news_briefs WHERE title LIKE ? "
            "ORDER BY COALESCE(relevance,0) DESC, created_at DESC LIMIT 5",
            (like,),
        ) or []
    except Exception:
        pass
    try:
        tasks = db_query(
            "SELECT task_id, title, status FROM tasks "
            "WHERE title LIKE ? ORDER BY created_at DESC LIMIT 5",
            (like,),
        ) or []
    except Exception:
        pass
    total = len(papers) + len(projects) + len(news) + len(tasks)
    if total == 0:
        import html as _html
        q_safe = _html.escape(q)  # reflected-XSS guard: never echo raw user input into HTML
        return HTMLResponse(
            f'<div style="padding:20px 24px;font-family:var(--m-mono);font-size:11px;'
            f'color:var(--m-muted);">No results for <em style="color:var(--m-ink);">{q_safe}</em></div>'
        )
    return templates.TemplateResponse(
        request,
        "partials/search_results.html",
        {"q": q, "papers": papers, "projects": projects, "news": news, "tasks": tasks},
    )


@router.get("/api/partial/knowledge/stats", response_class=HTMLResponse)
async def knowledge_stats(request: Request):
    import datetime

    cards = db_scalar("SELECT COUNT(*) FROM library_cards", default=0)
    domains = db_scalar("SELECT COUNT(DISTINCT domain) FROM library_cards", default=0)
    lit = db_scalar("SELECT COUNT(*) FROM literature_metadata", default=0)
    pdf_chunks = db_scalar("SELECT COUNT(*) FROM pdf_chunks", default=0)
    pdf_docs = db_scalar("SELECT COUNT(*) FROM pdf_index_state", default=0)
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
            "pdf_chunks": pdf_chunks,
            "pdf_docs": pdf_docs,
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
# PDF knowledge search (keyword + snippet from indexed chunks)
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/pdf-search", response_class=HTMLResponse)
async def knowledge_pdf_search(request: Request, q: str = "", domain: str = ""):
    """Full-text keyword search across indexed PDF chunks."""
    if not q or len(q) < 2:
        return HTMLResponse(
            '<p class="text-muted small">Type at least 2 characters to search the document library.</p>'
        )
    pattern = f"%{q}%"
    params: list = [pattern, pattern]
    domain_clause = ""
    if domain:
        domain_clause = " AND domain LIKE ?"
        params.append(f"%{domain}%")

    results = db_query(
        f"""SELECT title, domain, source_file, page_start, page_end,
               substr(chunk_text, 1, 300) as excerpt
            FROM pdf_chunks
            WHERE (chunk_text LIKE ? OR title LIKE ?){domain_clause}
            GROUP BY source_file
            ORDER BY title
            LIMIT 20""",
        params,
    )

    # Highlight query term in excerpt
    for r in results:
        if r.get("excerpt"):
            hi = r["excerpt"].replace(q, f"<mark>{q}</mark>")
            r["excerpt_html"] = hi
        r["filename"] = (r.get("source_file") or "").split("/")[-1]

    return templates.TemplateResponse(
        request,
        "partials/knowledge_pdf_search.html",
        {"results": results, "q": q, "domain": domain},
    )


@router.get("/api/partial/knowledge/pdf-stats", response_class=HTMLResponse)
async def knowledge_pdf_stats(request: Request):
    """Per-domain stats for the indexed PDF knowledge base."""
    rows = db_query(
        """SELECT domain, COUNT(*) as docs, SUM(chunk_count) as chunks
           FROM pdf_index_state
           GROUP BY domain ORDER BY chunks DESC""",
    )
    total_chunks = db_scalar("SELECT COUNT(*) FROM pdf_chunks", default=0)
    total_docs = db_scalar("SELECT COUNT(*) FROM pdf_index_state", default=0)
    return templates.TemplateResponse(
        request,
        "partials/knowledge_pdf_stats.html",
        {"rows": rows, "total_chunks": total_chunks, "total_docs": total_docs},
    )


@router.post("/api/knowledge/build-index", response_class=HTMLResponse)
async def knowledge_build_index(request: Request):
    """Trigger PDF indexing via build_knowledge_db.py as a background subprocess."""
    import subprocess, sys, os
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if not rc_root:
        return HTMLResponse(
            '<span class="text-danger small">METIS_RC_ROOT not set — cannot locate build script.</span>'
        )
    script = Path(rc_root) / "system" / "install" / "build_knowledge_db.py"
    if not script.exists():
        return HTMLResponse(
            f'<span class="text-danger small">build_knowledge_db.py not found at {script}</span>'
        )
    try:
        subprocess.Popen(
            [sys.executable, str(script), "--quiet"],
            env={**os.environ, "METIS_RC_ROOT": rc_root},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return HTMLResponse(
            '<span class="text-success small">'
            '✓ Indexing started in background (5–20 min). '
            'Refresh this panel when done.'
            '</span>'
        )
    except Exception as e:
        return HTMLResponse(f'<span class="text-danger small">I couldn\'t start the indexer: {e}</span>')


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
async def knowledge_cards(request: Request, domain: str = ""):
    """3-column index card grid from library_cards, optionally filtered by domain."""
    if domain:
        cards = db_query(
            "SELECT id, title, domain, summary, tags, created_at "
            "FROM library_cards WHERE domain = ? ORDER BY created_at DESC LIMIT 12",
            (domain,),
        )
        total_cards = db_scalar(
            "SELECT COUNT(*) FROM library_cards WHERE domain = ?", (domain,), default=0
        )
        first_domain = domain
    else:
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

# ---------------------------------------------------------------------------
# PDF match cache  (literature_metadata.id → library_inventory relative_path)
# ---------------------------------------------------------------------------

_lit_pdf_cache: dict[int, str] = {}   # lit_id -> relative_path
_lib_pdf_base: Path | None = None     # base directory for library_inventory paths
_LIB_STOPWORDS = frozenset(
    "a an the and or of in to is on for with at by as from its be are that this "
    "1 2 3 4 5 6 7 8 9 0 study results using".split()
)


def _word_set(text: str) -> frozenset[str]:
    # Normalize dashes, underscores, and dots as spaces before tokenizing
    text = re.sub(r"[-_.]", " ", text)
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return frozenset(w for w in words if w not in _LIB_STOPWORDS and len(w) > 1 and not w.isdigit())


def _get_lib_base() -> Path | None:
    global _lib_pdf_base
    if _lib_pdf_base is not None:
        return _lib_pdf_base
    # 1. Try env var
    env_path = os.environ.get("METIS_LIBRARY_PATH", "")
    if env_path and Path(env_path).is_dir():
        _lib_pdf_base = Path(env_path)
        return _lib_pdf_base
    # 2. Try user-preferences.json
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        prefs_path = Path(rc_root) / "system" / "config" / "user-preferences.json"
        try:
            prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
            lib_path = prefs.get("library_path", "")
            if lib_path and Path(lib_path).is_dir():
                _lib_pdf_base = Path(lib_path)
                return _lib_pdf_base
        except Exception:
            pass
    return None


def _ensure_pdf_cache() -> None:
    global _lit_pdf_cache
    if _lit_pdf_cache:
        return
    lib_rows = db_query("SELECT relative_path, basename FROM library_inventory") or []
    if not lib_rows:
        return
    # Build word-set index for library entries
    lib_index: list[tuple[frozenset, str]] = []
    for r in lib_rows:
        name = (r.get("basename") or "").replace(".pdf", "").replace(".PDF", "")
        if name:
            lib_index.append((_word_set(name), r["relative_path"]))

    lit_rows = db_query("SELECT id, title FROM literature_metadata") or []
    for r in lit_rows:
        lit_id = r.get("id")
        title = (r.get("title") or "").replace("-", " ").replace("_", " ")
        if not lit_id or not title:
            continue
        lit_words = _word_set(title)
        if not lit_words:
            continue
        best_score = 0.0
        best_path = ""
        for lib_words, rel_path in lib_index:
            if not lib_words:
                continue
            intersection = len(lit_words & lib_words)
            union = len(lit_words | lib_words)
            score = intersection / union if union else 0.0
            if score > best_score:
                best_score = score
                best_path = rel_path
        if best_score >= 0.28 and best_path:
            _lit_pdf_cache[lit_id] = best_path


# Run cache build at import time (non-blocking — errors are silently swallowed)
# Cache matches Zotero paper titles → local PDF filenames via Jaccard similarity.
try:
    _ensure_pdf_cache()
except Exception:
    pass

# Ensure is_read column exists in literature_metadata (migration)
try:
    import sqlite3 as _sq3
    _db = get_db_path()
    if _db and Path(_db).exists():
        with _sq3.connect(str(_db)) as _c:
            cols = {r[1] for r in _c.execute("PRAGMA table_info(literature_metadata)")}
            if "is_read" not in cols:
                _c.execute("ALTER TABLE literature_metadata ADD COLUMN is_read INTEGER DEFAULT 0")
                _c.commit()
except Exception:
    pass

# Create unified library_items_view across all three silos
try:
    import sqlite3 as _sq3v
    _dbv = get_db_path()
    if _dbv and Path(_dbv).exists():
        with _sq3v.connect(str(_dbv)) as _cv:
            _cv.execute("""
                CREATE VIEW IF NOT EXISTS library_items_view AS
                SELECT
                  'card'           AS source_type,
                  CAST(id AS TEXT) AS item_key,
                  title,
                  domain           AS collection,
                  summary          AS abstract,
                  NULL             AS authors,
                  NULL             AS year,
                  NULL             AS doi,
                  NULL             AS method,
                  status,
                  created_at
                FROM library_cards
                UNION ALL
                SELECT
                  'seeded'         AS source_type,
                  relative_path    AS item_key,
                  REPLACE(REPLACE(basename,'.pdf',''),'.PDF','') AS title,
                  top_folder       AS collection,
                  relevance_note   AS abstract,
                  phd_article_link AS authors,
                  NULL             AS year,
                  NULL             AS doi,
                  method,
                  status,
                  NULL             AS created_at
                FROM library_seeded WHERE extension='pdf'
                UNION ALL
                SELECT
                  'zotero'         AS source_type,
                  CAST(id AS TEXT) AS item_key,
                  title,
                  collection,
                  abstract,
                  authors,
                  year,
                  doi,
                  NULL             AS method,
                  'zotero'         AS status,
                  created_at
                FROM literature_metadata
                WHERE library_source='zotero'
                  AND title IS NOT NULL AND title!='' AND title!='[No title found]'
            """)
            _cv.commit()
except Exception:
    pass


def _rebuild_pdf_cache() -> int:
    """Force-rebuild the PDF match cache. Returns number of matches found."""
    global _lit_pdf_cache
    _lit_pdf_cache = {}
    try:
        _ensure_pdf_cache()
    except Exception:
        pass
    return len(_lit_pdf_cache)


# ---------------------------------------------------------------------------
# Seeded library browser  (library_seeded + library_inventory fallback)
# Uses real paper titles and direct PDF paths — no fuzzy matching needed.
# ---------------------------------------------------------------------------

def _fetch_seeded_items(
    q: str = "",
    collection: str = "",
    phd_filter: str = "",
    sort: str = "title",
    per_page: int = 500,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return items from library_seeded (rich metadata) plus any inventory-only PDFs."""
    lib_base = _get_lib_base()

    where_parts: list[str] = ["extension = 'pdf'"]
    params: list = []

    if q and len(q.strip()) >= 2:
        like = f"%{q.strip()}%"
        where_parts.append(
            "(basename LIKE ? OR disease LIKE ? OR surveillance_mode LIKE ? OR relevance_note LIKE ?)"
        )
        params.extend([like, like, like, like])

    if collection:
        where_parts.append("top_folder = ?")
        params.append(collection)

    if phd_filter:
        where_parts.append("phd_article_link LIKE ?")
        params.append(f"%{phd_filter}%")

    where_sql = "WHERE " + " AND ".join(where_parts)
    order_map = {
        "title": "basename ASC",
        "folder": "top_folder ASC, basename ASC",
        "added": "modified_date DESC",
        "status": "status ASC, basename ASC",
    }
    order = order_map.get(sort, "basename ASC")

    total_seeded = db_scalar(f"SELECT COUNT(*) FROM library_seeded {where_sql}", tuple(params), default=0)

    rows = db_query(
        f"SELECT relative_path, basename, top_folder, disease, method, surveillance_mode, "
        f"elimination_phase, phd_article_link, relevance_note, status, modified_date "
        f"FROM library_seeded {where_sql} ORDER BY {order} "
        f"LIMIT {per_page} OFFSET {offset}",
        tuple(params),
    ) or []

    items: list[dict] = []
    for r in rows:
        basename = r.get("basename") or ""
        title = basename[:-4] if basename.lower().endswith(".pdf") else basename
        rel_path = r.get("relative_path") or ""
        tags = [t for t in [
            r.get("top_folder") or "",
            r.get("disease") or "",
            r.get("surveillance_mode") or "",
            r.get("elimination_phase") or "",
        ] if t][:4]
        pdf_exists = lib_base and (lib_base / rel_path).exists() if rel_path else False
        items.append({
            "id": rel_path,
            "title": title,
            "authors": r.get("phd_article_link") or "",
            "year": (r.get("modified_date") or "")[:4],
            "source": r.get("disease") or r.get("surveillance_mode") or "",
            "collection_tags": tags,
            "item_type": r.get("status") or "paper",
            "doi": "",
            "url": "",
            "abstract": r.get("relevance_note") or "",
            "has_abstract": bool((r.get("relevance_note") or "").strip()),
            "pdf_url": f"/api/library/pdf/seeded/{rel_path}" if pdf_exists else "",
            "phd_link": r.get("phd_article_link") or "",
            "method": r.get("method") or "",
        })

    return items, total_seeded


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
        f"item_type, doi, url, abstract, COALESCE(is_read, 0) as is_read "
        f"FROM literature_metadata {where_sql} "
        f"ORDER BY {order} "
        f"LIMIT {per_page} OFFSET {offset}",
        p,
    ) or []

    _ensure_pdf_cache()
    lib_base_available = _get_lib_base() is not None

    items: list[dict] = []
    for r in rows:
        col_str = r.get("collection") or ""
        col_tags = [t.strip() for t in col_str.split(",") if t.strip()] if col_str else []
        src = r.get("source") or r.get("journal") or ""
        abstract = r.get("abstract") or ""
        lit_id = r.get("id")
        pdf_rel = _lit_pdf_cache.get(lit_id, "") if lib_base_available else ""
        items.append(
            {
                "id": lit_id,
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
                "pdf_url": f"/api/library/pdf/{lit_id}" if pdf_rel else "",
                "is_read": bool(r.get("is_read", 0)),
            }
        )

    return items, total or 0


@router.get("/api/partial/knowledge/hat-corpus", response_class=HTMLResponse)
async def knowledge_hat_corpus(
    request: Request,
    q: str = "",
    collection: str = "",
    sort: str = "title",
):
    """Domain knowledge corpus browser — reads from library_seeded."""
    items, total = _fetch_seeded_items(q=q, collection=collection, sort=sort, per_page=200)
    # Collection filter chips
    collection_rows = db_query(
        "SELECT top_folder, COUNT(*) as cnt FROM library_seeded "
        "WHERE extension='pdf' GROUP BY top_folder ORDER BY cnt DESC LIMIT 10"
    ) or []
    collections = [(r.get("top_folder", ""), r.get("cnt", 0)) for r in collection_rows if r.get("top_folder")]
    # Status summary
    seeded_count = db_scalar(
        "SELECT COUNT(*) FROM library_seeded WHERE status='seeded' AND extension='pdf'", default=0
    ) or 0
    triage_count = db_scalar(
        "SELECT COUNT(*) FROM library_seeded WHERE status='to_triage' AND extension='pdf'", default=0
    ) or 0
    return templates.TemplateResponse(
        request,
        "partials/knowledge_hat_corpus.html",
        {
            "items": items,
            "total": total,
            "q": q,
            "active_collection": collection,
            "active_sort": sort,
            "collections": collections,
            "seeded_count": seeded_count,
            "triage_count": triage_count,
        },
    )


@router.get("/api/partial/knowledge/hat-corpus-table", response_class=HTMLResponse)
async def knowledge_hat_corpus_table(
    request: Request,
    q: str = "",
    collection: str = "",
    sort: str = "title",
):
    """Table rows only — swapped in for domain corpus live search/filter."""
    items, total = _fetch_seeded_items(q=q, collection=collection, sort=sort, per_page=200)
    return templates.TemplateResponse(
        request,
        "partials/knowledge_hat_corpus_table.html",
        {"items": items, "total": total, "q": q},
    )


@router.get("/api/partial/knowledge/library-browser", response_class=HTMLResponse)
async def knowledge_library_browser_panel(
    request: Request,
    q: str = "",
    item_type: str = "",
    sort: str = "newest",
):
    """Full library browser using Zotero-synced literature_metadata."""
    # Item type chips
    type_rows = db_query(
        "SELECT item_type, COUNT(*) as cnt FROM literature_metadata "
        "WHERE library_source='zotero' AND item_type != '' "
        "GROUP BY item_type ORDER BY cnt DESC"
    ) or []
    item_types = [(r.get("item_type", ""), r.get("cnt", 0)) for r in type_rows if r.get("item_type")]

    items, total = _fetch_library_items(
        q=q, item_type=item_type, sort=sort, per_page=300
    )
    # Exclude manual/garbage entries from browser display
    items = [i for i in items if i.get("title") and not i["title"].startswith(("19", "20"))]
    active_filter_count = sum(bool(v) for v in [q, item_type])

    return templates.TemplateResponse(
        request,
        "partials/knowledge_library_browser.html",
        {
            "item_types": item_types,
            "items": items,
            "total": total,
            "q": q,
            "active_type": item_type,
            "active_sort": sort,
            "active_filter_count": active_filter_count,
        },
    )


@router.get("/api/partial/knowledge/library-table", response_class=HTMLResponse)
async def knowledge_library_table_partial(
    request: Request,
    q: str = "",
    item_type: str = "",
    sort: str = "newest",
    year_from: str = "",
    year_to: str = "",
):
    """Table rows only — swapped in for live search/filter updates."""
    items, total = _fetch_library_items(
        q=q, item_type=item_type, sort=sort, per_page=300,
        year_from=year_from, year_to=year_to,
    )
    items = [i for i in items if i.get("title") and not i["title"].startswith(("19", "20"))]
    active_filter_count = sum(bool(v) for v in [q, item_type, year_from, year_to])
    return templates.TemplateResponse(
        request,
        "partials/knowledge_library_table.html",
        {
            "items": items,
            "total": total,
            "q": q,
            "collection": "",
            "item_type": item_type,
            "sort": sort,
            "active_filter_count": active_filter_count,
            "library_mode": "seeded",
        },
    )


@router.get("/api/library/pdf/seeded/{rel_path:path}", response_class=FileResponse)
async def serve_seeded_pdf(rel_path: str):
    """Serve a PDF from the local library by its relative path (library_seeded)."""
    from fastapi import HTTPException
    base = _get_lib_base()
    if base is None:
        raise HTTPException(status_code=503, detail="Library path not configured")
    full_path = (base / rel_path).resolve()
    # Path traversal guard
    if not str(full_path).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(str(full_path), media_type="application/pdf")


@router.get("/api/library/pdf/{item_id}", response_class=FileResponse)
async def serve_library_pdf(item_id: int):
    """Serve a PDF from the local library for a given literature_metadata id."""
    from fastapi import HTTPException
    _ensure_pdf_cache()
    rel_path = _lit_pdf_cache.get(item_id, "")
    if not rel_path:
        raise HTTPException(status_code=404, detail="No PDF found for this paper")
    base = _get_lib_base()
    if base is None:
        raise HTTPException(status_code=503, detail="Library path not configured")
    full_path = base / rel_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(str(full_path), media_type="application/pdf")


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
    duplicate_count = 0
    try:
        duplicate_count = db_scalar("SELECT COUNT(*) FROM library_duplicates", default=0) or 0
    except Exception:
        pass
    last = (sync_info.get("last_synced") or "")[:16].replace("T", " ")

    # Detect unconfigured Zotero — ZOTERO_USER_ID absent or still the placeholder
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    env_path = Path(rc_root) / "system" / ".env" if rc_root else None
    if env_path and env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    user_id = os.environ.get("ZOTERO_USER_ID", "")
    zotero_unconfigured = (
        not user_id
        or user_id.strip() in ("", "your_zotero_user_id", "YOUR_ZOTERO_USER_ID", "0")
        or user_id.strip().startswith("your_")
    )

    return templates.TemplateResponse(
        request,
        "partials/knowledge_sync_status.html",
        {
            "zotero_count": zotero_count,
            "manual_count": manual_count,
            "last_synced": last or "Never",
            "version": sync_info.get("last_version") or 0,
            "duplicate_count": duplicate_count,
            "zotero_unconfigured": zotero_unconfigured,
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
        from db import get_db_path
        db_path = get_db_path()
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
        "FROM news_briefs ORDER BY created_at DESC LIMIT 500"
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


# ---------------------------------------------------------------------------
# Recently added strip
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/recently-added", response_class=HTMLResponse)
async def knowledge_recently_added(request: Request):
    """Horizontal strip of 6 most recently added library items."""
    import datetime as _dt
    items = []
    try:
        rows = db_query(
            "SELECT title, authors, year, created_at FROM literature_metadata "
            "WHERE title IS NOT NULL AND title != '' AND library_source='zotero' "
            "ORDER BY created_at DESC LIMIT 6"
        ) or []
        now = _dt.datetime.now()
        for r in rows:
            created = r.get("created_at") or ""
            try:
                dt = _dt.datetime.fromisoformat(created[:19])
                delta = now - dt
                if delta.days == 0:
                    age = "today"
                elif delta.days == 1:
                    age = "1d ago"
                elif delta.days < 7:
                    age = f"{delta.days}d ago"
                elif delta.days < 31:
                    age = f"{delta.days // 7}w ago"
                else:
                    age = f"{delta.days // 30}mo ago"
            except Exception:
                age = created[:10] if created else "—"
            title = r.get("title") or "Untitled"
            short_title = title[:48] + "…" if len(title) > 50 else title
            items.append({"title": short_title, "age": age, "year": r.get("year") or ""})
    except Exception:
        pass
    return templates.TemplateResponse(
        request,
        "partials/knowledge_recently_added.html",
        {"items": items},
    )


# ---------------------------------------------------------------------------
# Unified search  (library_cards + literature_metadata + episodic_memory)
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/unified-search", response_class=HTMLResponse)
async def knowledge_unified_search(request: Request, q: str = ""):
    """Fan-out search across all three library silos + episodic memory."""
    if not q or len(q.strip()) < 2:
        return HTMLResponse(
            '<div style="font-family:var(--m-display);font-style:italic;font-size:13px;'
            'color:var(--m-muted);padding:12px 0;">Type at least 2 characters to search across your entire library.</div>'
        )
    like = f"%{q.strip()}%"

    # 1. Library cards (open-access books)
    cards = db_query(
        "SELECT title, domain, summary FROM library_cards "
        "WHERE title LIKE ? OR summary LIKE ? OR tags LIKE ? "
        "ORDER BY created_at DESC LIMIT 6",
        (like, like, like),
    ) or []

    # 2. Zotero / literature_metadata
    papers = db_query(
        "SELECT id, title, authors, year, source, doi, abstract FROM literature_metadata "
        "WHERE title IS NOT NULL AND title != '' "
        "AND (title LIKE ? OR authors LIKE ? OR abstract LIKE ? OR tags LIKE ?) "
        "ORDER BY created_at DESC LIMIT 10",
        (like, like, like, like),
    ) or []
    _ensure_pdf_cache()
    for p in papers:
        lit_id = p.get("id")
        pdf_rel = _lit_pdf_cache.get(lit_id, "") if lit_id else ""
        p["pdf_url"] = f"/api/library/pdf/{lit_id}" if pdf_rel else ""

    # 3. Seeded domain corpus
    seeded = db_query(
        "SELECT REPLACE(REPLACE(basename,'.pdf',''),'.PDF','') as title, "
        "top_folder, method, relevance_note FROM library_seeded "
        "WHERE (basename LIKE ? OR relevance_note LIKE ? OR top_folder LIKE ?) "
        "AND extension='pdf' "
        "ORDER BY basename LIMIT 6",
        (like, like, like),
    ) or []

    # 4. Episodic memory (keyword fallback)
    memory = db_query(
        "SELECT content, event_type, created_at FROM episodic_memory "
        "WHERE content LIKE ? ORDER BY created_at DESC LIMIT 5",
        (like,),
    ) or []

    total = len(cards) + len(papers) + len(seeded) + len(memory)
    return templates.TemplateResponse(
        request,
        "partials/knowledge_unified_search.html",
        {"cards": cards, "papers": papers, "seeded": seeded, "memory": memory,
         "q": q, "total": total},
    )


# ---------------------------------------------------------------------------
# Unified search — semantic path (sqlite-vec on memory + pdf_chunks)
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/unified-search-semantic", response_class=HTMLResponse)
async def knowledge_unified_search_semantic(request: Request, q: str = ""):
    """Semantic counterpart to /api/partial/knowledge/unified-search.

    Tries the local sqlite-vec layer over episodic/semantic memory and PDF
    chunks. If embeddings or vec tables aren't available, falls back gracefully
    to the keyword path.
    """
    if not q or len(q.strip()) < 2:
        return HTMLResponse(
            '<div style="font-family:var(--m-display);font-style:italic;font-size:13px;'
            'color:var(--m-muted);padding:12px 0;">Type at least 2 characters to search semantically across your library.</div>'
        )

    q = q.strip()
    semantic_hits: list[dict] = []
    used_semantic = False

    try:
        from metis_mcp.embeddings import embed_one  # type: ignore
        import struct
        import sqlite_vec  # type: ignore
        import sqlite3

        query_vec = embed_one(q)
        blob = struct.pack(f"{len(query_vec)}f", *query_vec)

        try:
            db_path = get_db_path()
        except Exception:
            db_path = None

        if db_path:
            con = sqlite3.connect(str(db_path))
            con.row_factory = sqlite3.Row
            try:
                con.enable_load_extension(True)
                sqlite_vec.load(con)
                con.enable_load_extension(False)
            except Exception:
                con.close()
                con = None

            if con is not None:
                # 1. PDF chunks
                try:
                    rows = con.execute(
                        "SELECT c.text, c.page, c.pdf_path, v.distance "
                        "FROM vec_pdf_chunks v JOIN pdf_chunks c ON c.id = v.rowid "
                        "ORDER BY v.distance ASC LIMIT 8",
                        (blob,),
                    ).fetchall()
                    for r in rows:
                        row = dict(r)
                        semantic_hits.append({
                            "kind": "pdf",
                            "title": (Path(row.get("pdf_path") or "").name)[:80] or "PDF chunk",
                            "snippet": (row.get("text") or "")[:200],
                            "score": round(1 - float(row.get("distance") or 1), 3),
                            "extra": f"p. {row.get('page')}" if row.get("page") else "",
                        })
                    used_semantic = True
                except Exception:
                    pass

                # 2. Episodic memory
                try:
                    rows = con.execute(
                        "SELECT e.content, e.event_type, e.created_at, v.distance "
                        "FROM vec_episodic v JOIN episodic_memory e ON e.id = v.rowid "
                        "ORDER BY v.distance ASC LIMIT 6",
                        (blob,),
                    ).fetchall()
                    for r in rows:
                        row = dict(r)
                        semantic_hits.append({
                            "kind": "memory",
                            "title": (row.get("event_type") or "memory").upper(),
                            "snippet": (row.get("content") or "")[:200],
                            "score": round(1 - float(row.get("distance") or 1), 3),
                            "extra": (row.get("created_at") or "")[:10],
                        })
                    used_semantic = True
                except Exception:
                    pass

                con.close()
    except Exception:
        used_semantic = False

    # Graceful fallback if retrieval is unavailable
    if not used_semantic:
        like = f"%{q}%"
        rows = db_query(
            "SELECT title, abstract FROM literature_metadata "
            "WHERE title LIKE ? OR abstract LIKE ? ORDER BY created_at DESC LIMIT 8",
            (like, like),
            default=[],
        ) or []
        for r in rows:
            semantic_hits.append({
                "kind": "paper",
                "title": (r.get("title") or "")[:80],
                "snippet": (r.get("abstract") or "")[:200],
                "score": None,
                "extra": "",
            })

    # Rank by score where present
    def _sort_key(h):
        return -(h.get("score") or 0)
    semantic_hits.sort(key=_sort_key)
    semantic_hits = semantic_hits[:12]

    # Highlight query terms in each snippet and group by source kind
    import re as _re
    terms = [t for t in _re.findall(r"\w{3,}", q.lower()) if t]
    pat = None
    if terms:
        pat = _re.compile("(" + "|".join(_re.escape(t) for t in terms) + ")", _re.IGNORECASE)

    label_map = {
        "pdf": "Papers",
        "paper": "Papers",
        "memory": "Past sessions",
        "idea": "Ideas",
        "note": "Notes",
    }
    grouped: dict[str, list[dict]] = {}
    for h in semantic_hits:
        kind = (h.get("kind") or "other").lower()
        group = label_map.get(kind, kind.title() or "Other")
        snippet = h.get("snippet") or ""
        if pat and snippet:
            snippet_html = pat.sub(r"<mark>\1</mark>", snippet)
        else:
            snippet_html = snippet
        # Score is 0..1 (cosine-ish). Normalise to 0..100 width.
        raw = h.get("score")
        try:
            pct = max(0, min(100, int(round(float(raw) * 100)))) if raw is not None else None
        except Exception:
            pct = None
        grouped.setdefault(group, []).append({
            **h,
            "snippet_html": snippet_html,
            "score_pct": pct,
            "score_label": (f"{pct}% match" if pct is not None else "—"),
        })

    # Preserve a sensible group order
    group_order = ["Papers", "Past sessions", "Ideas", "Notes"]
    grouped_ordered = []
    for name in group_order:
        if name in grouped:
            grouped_ordered.append((name, grouped[name]))
    for name, items in grouped.items():
        if name not in group_order:
            grouped_ordered.append((name, items))

    return templates.TemplateResponse(
        request,
        "partials/knowledge_unified_search_semantic.html",
        {
            "hits": semantic_hits,
            "groups": grouped_ordered,
            "q": q,
            "used_semantic": used_semantic,
            "total": len(semantic_hits),
        },
    )


# ---------------------------------------------------------------------------
# Topic Coverage Map  (visual grid: good / partial / gap per research topic)
# ---------------------------------------------------------------------------

# Canonical topic definitions for the research landscape.
# Each entry: (label, keywords_for_lit_search, description_for_card)
_TOPIC_DEFINITIONS: list[tuple[str, list[str], str]] = [
    ("Infectious Diseases",       ["infectious disease", "infection", "pathogen", "epidemic", "outbreak"], "Burden, transmission, and outbreak dynamics"),
    ("Surveillance Systems",      ["surveillance", "reporting system", "sentinel", "monitoring"], "Active/passive surveillance design & evaluation"),
    ("Elimination & Control",     ["elimination", "control", "eradication", "prevention programme"], "WHO targets, control strategies, validation"),
    ("Diagnostics",               ["diagnostic", "RDT", "sensitivity", "specificity", "test accuracy"], "Diagnostic tools, accuracy, and deployment"),
    ("Spatial Epidemiology",      ["spatial", "geograph", "mapping", "GIS", "geospatial"], "Disease mapping, spatial modelling, hotspots"),
    ("Multilevel Methods",        ["multilevel", "mixed model", "random effect", "hierarchical"], "Clustered data, nested designs"),
    ("NTD & Tropical Diseases",   ["NTD", "neglected tropical", "ESPEN", "tropical disease", "parasitic"], "Neglected tropical disease programmes & reporting"),
    ("Health Information Systems",["DHIS2", "health information system", "HIS", "OpenMRS", "HMIS"], "Health information systems implementation"),
    ("Mathematical Modelling",    ["model", "mathematical model", "transmission model", "stochastic"], "Transmission dynamics, intervention impact"),
    ("Health Systems",            ["health system", "health financing", "UHC", "coverage", "access"], "Health system strengthening & universal coverage"),
    ("Maternal & Child Health",   ["maternal", "child health", "MCH", "RMNCH", "neonatal", "nutrition"], "Maternal, newborn, and child health outcomes"),
    ("Environmental & One Health",["environment", "climate", "WASH", "water sanitation", "One Health", "zoonotic"], "Environment-health linkages & One Health"),
]

_GOOD_THRESHOLD    = 12   # ≥12 papers → good
_PARTIAL_THRESHOLD = 3    # 3–11 → partial; <3 → gap


def _coverage_level(count: int) -> str:
    if count >= _GOOD_THRESHOLD:
        return "good"
    if count >= _PARTIAL_THRESHOLD:
        return "partial"
    return "gap"


@router.get("/api/partial/knowledge/topic-coverage", response_class=HTMLResponse)
async def knowledge_topic_coverage(request: Request):
    """Visual topic coverage grid: research landscape at a glance."""

    # Pull user-configured topics from DB (for any custom additions)
    user_topic_rows = db_query(
        "SELECT topic, description FROM user_topics WHERE active = 1 ORDER BY id"
    ) or []

    # Merge canonical topics with any user-defined ones not already covered
    canonical_labels = {label.lower() for label, _, _ in _TOPIC_DEFINITIONS}
    topic_defs: list[tuple[str, list[str], str]] = list(_TOPIC_DEFINITIONS)
    for r in user_topic_rows:
        label = (r.get("topic") or "").strip()
        if label and label.lower() not in canonical_labels:
            desc = (r.get("description") or "").replace(",", " ").strip()
            keywords = [kw.strip() for kw in desc.split() if len(kw.strip()) > 2][:4]
            topic_defs.append((label.title(), keywords or [label], desc))

    # Count papers per topic
    total_papers_scalar = db_scalar("SELECT COUNT(*) FROM literature_metadata", default=0) or 0
    seeded_total = db_scalar("SELECT COUNT(*) FROM library_seeded WHERE extension='pdf'", default=0) or 0
    total_papers = (total_papers_scalar or 0) + (seeded_total or 0)

    topics: list[dict] = []
    for label, keywords, description in topic_defs:
        # Build LIKE conditions for literature_metadata
        where_clauses = " OR ".join(
            "(title LIKE ? OR tags LIKE ? OR abstract LIKE ?)" for _ in keywords
        )
        params_lit: list = []
        for kw in keywords:
            like = f"%{kw}%"
            params_lit.extend([like, like, like])

        lit_count = 0
        seeded_count = 0
        try:
            if where_clauses:
                lit_count = db_scalar(
                    f"SELECT COUNT(*) FROM literature_metadata WHERE {where_clauses}",
                    tuple(params_lit),
                    default=0,
                ) or 0
        except Exception:
            pass

        try:
            if keywords:
                seeded_where = " OR ".join("(basename LIKE ? OR relevance_note LIKE ?)" for _ in keywords)
                params_seeded: list = []
                for kw in keywords:
                    like = f"%{kw}%"
                    params_seeded.extend([like, like])
                seeded_count = db_scalar(
                    f"SELECT COUNT(*) FROM library_seeded WHERE extension='pdf' AND ({seeded_where})",
                    tuple(params_seeded),
                    default=0,
                ) or 0
        except Exception:
            pass

        paper_count = lit_count + seeded_count
        level = _coverage_level(paper_count)

        # Source breakdown pills (max 2)
        sources: list[tuple[str, int]] = []
        if lit_count:
            sources.append(("zotero", lit_count))
        if seeded_count:
            sources.append(("corpus", seeded_count))

        # Coverage bar fill percentage (capped at 100, scaled so 40 papers = full bar)
        bar_pct = min(100, int(paper_count * 100 / 40)) if paper_count else 0

        topics.append({
            "label": label,
            "description": description,
            "paper_count": paper_count,
            "level": level,
            "sources": sources,
            "bar_pct": bar_pct,
        })

    # Sort: gap first, then partial, then good — worst coverage at the top
    _level_order = {"gap": 0, "partial": 1, "good": 2}
    topics.sort(key=lambda t: (_level_order.get(t["level"], 3), -t["paper_count"]))

    return templates.TemplateResponse(
        request,
        "partials/knowledge_topic_coverage.html",
        {"topics": topics, "total_papers": total_papers},
    )


# ---------------------------------------------------------------------------
# Coverage gap detector  (Zotero vs. OpenAlex)
# ---------------------------------------------------------------------------


@router.get("/api/partial/knowledge/coverage-gap", response_class=HTMLResponse)
async def knowledge_coverage_gap_panel(request: Request):
    """Coverage gap detector UI panel."""
    return templates.TemplateResponse(
        request,
        "partials/knowledge_coverage_gap.html",
        {"results": None, "query": "", "error": None},
    )


@router.post("/api/knowledge/gap-check", response_class=HTMLResponse)
async def knowledge_gap_check(request: Request):
    """Compare OpenAlex search results against local Zotero collection.

    Returns papers found on OpenAlex that are NOT already in literature_metadata.
    """
    import json as _json
    import urllib.parse
    import urllib.request

    form = await request.form()
    query = (form.get("query") or "").strip()
    max_results = int(form.get("max_results") or 20)

    if not query:
        return templates.TemplateResponse(
            request,
            "partials/knowledge_coverage_gap.html",
            {"results": None, "query": query, "error": "Please enter a search query."},
        )

    # Fetch from OpenAlex
    try:
        params = urllib.parse.urlencode({
            "search": query,
            "per-page": max_results,
            "sort": "cited_by_count:desc",
            "select": "id,title,doi,publication_date,primary_location,authorships,"
                      "cited_by_count,abstract_inverted_index",
            "mailto": "metis@research-cortex.local",
        })
        url = f"https://api.openalex.org/works?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "MetisRC/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())
        oa_works = data.get("results", [])
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "partials/knowledge_coverage_gap.html",
            {"results": None, "query": query, "error": f"OpenAlex error: {e}"},
        )

    # Load existing DOIs + title word-sets from literature_metadata
    existing_dois: set[str] = set()
    existing_title_words: list[frozenset] = []
    try:
        rows = db_query("SELECT doi, title FROM literature_metadata WHERE doi != '' OR title != ''") or []
        for r in rows:
            doi = (r.get("doi") or "").strip().lower().replace("https://doi.org/", "")
            if doi:
                existing_dois.add(doi)
            t = r.get("title") or ""
            if t:
                existing_title_words.append(_word_set(t))
    except Exception:
        pass

    # Also check library_seeded (domain corpus)
    try:
        seeded_rows = db_query("SELECT basename FROM library_seeded WHERE extension='pdf'") or []
        for r in seeded_rows:
            name = (r.get("basename") or "").replace(".pdf", "").replace(".PDF", "")
            if name:
                existing_title_words.append(_word_set(name))
    except Exception:
        pass

    def _reconstruct_abstract(inv: dict | None) -> str:
        if not inv:
            return ""
        positions: list[tuple[int, str]] = []
        for word, pos_list in (inv or {}).items():
            for p in pos_list:
                positions.append((p, word))
        positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in positions[:100])

    missing = []
    for work in oa_works:
        title = (work.get("title") or "").strip()
        if not title:
            continue
        doi_raw = (work.get("doi") or "").replace("https://doi.org/", "").lower().strip()

        # Check by DOI first (exact)
        if doi_raw and doi_raw in existing_dois:
            continue

        # Check by title similarity (Jaccard)
        work_words = _word_set(title)
        already_have = False
        for existing in existing_title_words:
            if not existing or not work_words:
                continue
            overlap = len(work_words & existing) / len(work_words | existing)
            if overlap >= 0.4:
                already_have = True
                break
        if already_have:
            continue

        # Get journal
        journal = ""
        try:
            pl = work.get("primary_location") or {}
            src = pl.get("source") or {}
            journal = (src.get("display_name") or "")[:60]
        except Exception:
            pass

        # Authors (first 3)
        author_names = []
        for a in (work.get("authorships") or [])[:3]:
            name = (a.get("author") or {}).get("display_name", "")
            if name:
                author_names.append(name.split()[-1])  # last name only
        authors_str = "; ".join(author_names)

        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))

        missing.append({
            "title": title,
            "authors": authors_str,
            "year": (work.get("publication_date") or "")[:4],
            "journal": journal,
            "doi": doi_raw,
            "doi_url": f"https://doi.org/{doi_raw}" if doi_raw else "",
            "citations": work.get("cited_by_count") or 0,
            "abstract": abstract[:300] if abstract else "",
        })

    # Sort by citation count
    missing.sort(key=lambda x: x["citations"], reverse=True)

    return templates.TemplateResponse(
        request,
        "partials/knowledge_coverage_gap.html",
        {"results": missing, "query": query,
         "error": None, "checked": len(oa_works)},
    )


# ---------------------------------------------------------------------------
# Domain corpus semantic index trigger
# ---------------------------------------------------------------------------


@router.post("/api/knowledge/build-hat-index", response_class=HTMLResponse)
async def knowledge_build_hat_index(request: Request):
    """Trigger domain corpus PDF indexing as a background subprocess."""
    import subprocess
    import sys

    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if not rc_root:
        return HTMLResponse(
            '<span style="font-family:var(--m-mono);font-size:11px;color:var(--m-warn);">METIS_RC_ROOT not set.</span>'
        )
    script = Path(rc_root) / "system" / "install" / "build_knowledge_db.py"
    if not script.exists():
        return HTMLResponse(
            f'<span style="font-family:var(--m-mono);font-size:11px;color:var(--m-warn);">build_knowledge_db.py not found at {script}</span>'
        )

    # Read library path from user-preferences
    lib_path = ""
    try:
        prefs_path = Path(rc_root) / "system" / "config" / "user-preferences.json"
        prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
        lib_path = prefs.get("library_path", "")
    except Exception:
        pass

    if not lib_path or not Path(lib_path).exists():
        return HTMLResponse(
            '<span style="font-family:var(--m-mono);font-size:11px;color:var(--m-warn);">Library path not found in user-preferences.json → library_path</span>'
        )

    from db import get_db_path
    db_path = get_db_path()
    try:
        subprocess.Popen(
            [sys.executable, str(script), "--database", "hat-specialist",
             "--library-dir", lib_path, "--db", str(db_path), "--batch-size", "2"],
            env={**os.environ, "METIS_RC_ROOT": rc_root},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return HTMLResponse(
            '<span style="font-family:var(--m-mono);font-size:11px;color:var(--m-ok);">'
            'Indexing started in background (10–40 min depending on corpus size). '
            'Refresh the PDF stats panel when done.</span>'
        )
    except Exception as e:
        return HTMLResponse(
            f"<span style=\"font-family:var(--m-mono);font-size:11px;color:var(--m-warn);\">I couldn't start the indexer: {e}</span>"
        )
