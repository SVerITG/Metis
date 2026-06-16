"""Literature monitoring tools — PubMed and OpenAlex daily alerts.

Both tools use free public APIs requiring no API key. Results are inserted
into news_briefs with source_type='article' so the news rail can distinguish
them from RSS items.

PubMed: NCBI E-utilities (Esearch + Esummary)
OpenAlex: OpenAlex REST API (https://api.openalex.org)
"""

import datetime
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

_DDL_NEWS = """
CREATE TABLE IF NOT EXISTS news_briefs (
    brief_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT,
    domain          TEXT,
    signal_strength TEXT,
    summary         TEXT,
    source_url      TEXT,
    created_at      TEXT,
    tags            TEXT,
    brief_date      TEXT,
    source_type     TEXT DEFAULT 'news',
    surprise_flag   INTEGER DEFAULT 0,
    project_link    TEXT
)
"""

_DEFAULT_PUBMED_QUERY = (
    "global health[Title/Abstract] OR public health surveillance[Title/Abstract] "
    "OR epidemiology methods[Title/Abstract]"
    # Override via user-preferences.json: {"pubmed_query": "your search terms"}
)

_DEFAULT_OPENALEX_QUERY = (
    "global health OR epidemiology OR public health surveillance"
    # Override via user-preferences.json: {"openalex_query": "your search terms"}
)


def _user_pubmed_query() -> str:
    """Return user-configured PubMed query, falling back to field+topics from user-config."""
    try:
        import json, yaml
        prefs_path = paths.config / "user-preferences.json"
        if prefs_path.exists():
            q = json.loads(prefs_path.read_text()).get("pubmed_query", "")
            if q:
                return q
        cfg_path = paths.config / "user-config.yaml"
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text()) or {}
            field = cfg.get("research_field") or cfg.get("field", "")
            topics = cfg.get("topics", "")
            if field or topics:
                parts = []
                if field:
                    parts.append(f"{field}[Title/Abstract]")
                if topics:
                    for t in str(topics).split(",")[:3]:
                        t = t.strip()
                        if t:
                            parts.append(f"{t}[Title/Abstract]")
                if parts:
                    return " OR ".join(parts)
    except Exception:
        pass
    return _DEFAULT_PUBMED_QUERY


def _user_openalex_query() -> str:
    """Return user-configured OpenAlex query, falling back to field+topics from user-config."""
    try:
        import json, yaml
        prefs_path = paths.config / "user-preferences.json"
        if prefs_path.exists():
            q = json.loads(prefs_path.read_text()).get("openalex_query", "")
            if q:
                return q
        cfg_path = paths.config / "user-config.yaml"
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text()) or {}
            field = cfg.get("research_field") or cfg.get("field", "")
            topics = cfg.get("topics", "")
            if field or topics:
                parts = [p.strip() for p in f"{field},{topics}".split(",") if p.strip()]
                if parts:
                    return " OR ".join(parts[:4])
    except Exception:
        pass
    return _DEFAULT_OPENALEX_QUERY


def _insert_article(con, title: str, summary: str, url: str, domain: str, tags: str) -> bool:
    """Insert one article into news_briefs if not already present. Returns True if inserted."""
    con.execute(_DDL_NEWS)
    existing = con.execute(
        "SELECT brief_id FROM news_briefs WHERE source_url = ? AND source_type = 'article' LIMIT 1",
        (url,),
    ).fetchone()
    if existing:
        return False
    now = datetime.datetime.now().isoformat()
    con.execute(
        """INSERT INTO news_briefs
               (title, domain, signal_strength, summary, source_url,
                created_at, tags, brief_date, source_type, surprise_flag)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'article', 0)""",
        (
            title[:500],
            domain,
            "medium",
            summary[:1500],
            url,
            now,
            tags,
            now[:10],
        ),
    )
    return True


# ── PubMed ────────────────────────────────────────────────────────────────────

def _pubmed_esearch(query: str, reldate: int, max_results: int = 15) -> list[str]:
    """Return list of PMIDs matching query in the last reldate days."""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "reldate": reldate,
        "datetype": "edat",
        "retmax": max_results,
        "retmode": "json",
        "tool": "metis-rc",
        "email": "metis@research-cortex.local",
    })
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MetisRC/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return data.get("esearchresult", {}).get("idlist", [])


def _pubmed_esummary(pmids: list[str]) -> list[dict]:
    """Fetch title + abstract snippet for a list of PMIDs."""
    if not pmids:
        return []
    ids = ",".join(pmids)
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ids,
        "retmode": "json",
        "tool": "metis-rc",
        "email": "metis@research-cortex.local",
    })
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MetisRC/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    result = data.get("result", {})
    rows = []
    for pmid in pmids:
        item = result.get(pmid)
        if not item or not isinstance(item, dict):
            continue
        rows.append({
            "pmid": pmid,
            "title": item.get("title", "Untitled"),
            "source": item.get("source", ""),
            "authors": "; ".join(
                a.get("name", "") for a in item.get("authors", [])[:4]
            ),
            "pubdate": item.get("pubdate", ""),
        })
    return rows


@app.tool()
async def scan_pubmed_alerts(
    query: str = "",
    reldate: int = 1,
    max_results: int = 15,
) -> list[TextContent]:
    """Scan PubMed for recent papers matching a query.

    Uses NCBI E-utilities (free, no API key required). Results are inserted
    into news_briefs with source_type='article'. Safe to call daily from the
    morning scan scheduler job.

    Args:
        query: PubMed search query. Defaults to the query in user-preferences.json
               (pubmed_query field), then to your configured research field from
               user-config.yaml, then to a generic global-health fallback.
        reldate: Look back this many days (default: 1 = yesterday + today).
        max_results: Maximum papers to retrieve (default: 15).
    """
    if not query:
        query = _user_pubmed_query()
    import sqlite3

    try:
        pmids = _pubmed_esearch(query, reldate, max_results)
    except Exception as e:
        return [TextContent(type="text", text=f"PubMed search error: {e}")]

    if not pmids:
        return [TextContent(type="text", text="PubMed: no new papers found.")]

    try:
        summaries = _pubmed_esummary(pmids)
    except Exception as e:
        return [TextContent(type="text", text=f"PubMed fetch error: {e}")]

    added = 0
    try:
        con = sqlite3.connect(str(paths.db))
        for item in summaries:
            pmid = item["pmid"]
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            title = item["title"]
            journal = item.get("source", "PubMed")
            authors = item.get("authors", "")
            summary_text = f"{authors} ({item.get('pubdate', '')}). {journal}."
            if _insert_article(con, title, summary_text, url, "PubMed", "pubmed,article"):
                added += 1
        con.commit()
        con.close()
    except Exception as e:
        return [TextContent(type="text", text=f"PubMed DB insert error: {e}")]

    return [TextContent(
        type="text",
        text=f"PubMed: {added} new papers added from {len(pmids)} results (reldate={reldate}d).",
    )]


# ── OpenAlex ──────────────────────────────────────────────────────────────────

def _openalex_search(query: str, from_date: str, max_results: int = 10) -> list[dict]:
    """Return list of work dicts from OpenAlex matching query since from_date."""
    params = urllib.parse.urlencode({
        "search": query,
        "filter": f"from_publication_date:{from_date}",
        "per-page": max_results,
        "sort": "publication_date:desc",
        "select": "id,title,doi,publication_date,primary_location,authorships,abstract_inverted_index",
        "mailto": "metis@research-cortex.local",
    })
    url = f"https://api.openalex.org/works?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "MetisRC/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return data.get("results", [])


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            positions.append((pos, word))
    positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in positions[:200])


@app.tool()
async def scan_openalex(
    query: str = "",
    days_back: int = 1,
    max_results: int = 10,
) -> list[TextContent]:
    """Scan OpenAlex for recent papers matching a query.

    OpenAlex covers 474M papers including preprints. Free API, no key required.
    Results are inserted into news_briefs with source_type='article'.

    Args:
        query: Free-text search query. Defaults to the query in user-preferences.json
               (openalex_query field), then to your configured research topics from
               user-config.yaml, then to a generic global-health fallback.
        days_back: How many days back to search (default: 1).
        max_results: Maximum papers to retrieve (default: 10).
    """
    if not query:
        query = _user_openalex_query()
    import sqlite3

    from_date = (
        datetime.date.today() - datetime.timedelta(days=days_back)
    ).isoformat()

    try:
        items = _openalex_search(query, from_date, max_results)
    except Exception as e:
        return [TextContent(type="text", text=f"OpenAlex search error: {e}")]

    if not items:
        return [TextContent(type="text", text=f"OpenAlex: no papers since {from_date}.")]

    added = 0
    try:
        con = sqlite3.connect(str(paths.db))
        for item in items:
            title = item.get("title") or "Untitled"
            doi = item.get("doi") or ""
            url = doi if doi else item.get("id") or ""
            if not url:
                continue
            # Journal name from primary location
            journal = ""
            try:
                pl = item.get("primary_location") or {}
                src = pl.get("source") or {}
                journal = src.get("display_name", "") or ""
            except Exception:
                pass
            # Authors (first 4)
            author_names = []
            for a in (item.get("authorships") or [])[:4]:
                name = (a.get("author") or {}).get("display_name", "")
                if name:
                    author_names.append(name)
            authors = "; ".join(author_names)
            # Abstract
            abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
            pub_date = item.get("publication_date", "")
            summary_text = f"{authors} ({pub_date}). {journal}. {abstract[:300]}".strip()
            if _insert_article(con, title, summary_text, url, "OpenAlex", "openalex,article"):
                added += 1
        con.commit()
        con.close()
    except Exception as e:
        return [TextContent(type="text", text=f"OpenAlex DB insert error: {e}")]

    return [TextContent(
        type="text",
        text=f"OpenAlex: {added} new papers added from {len(items)} results (since {from_date}).",
    )]


def _s2_api_key() -> str:
    """Optional Semantic Scholar API key (env or system/.env). Moves off the
    heavily-throttled keyless shared pool. Get one free at semanticscholar.org."""
    import os
    key = os.environ.get("S2_API_KEY", "") or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    if not key:
        try:
            env_path = paths.root / "system" / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("S2_API_KEY") and "=" in line:
                        key = line.partition("=")[2].strip()
                        break
        except Exception:
            pass
    return key


def _semanticscholar_search(query: str, limit: int) -> list:
    """Query the Semantic Scholar Graph API. Uses S2_API_KEY if set (recommended —
    the keyless pool is heavily rate-limited). Retries once on HTTP 429."""
    import time
    fields = "title,abstract,year,venue,url,externalIds,citationCount,authors"
    params = urllib.parse.urlencode({
        "query": query,
        "limit": max(1, min(limit, 100)),
        "fields": fields,
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    headers = {"User-Agent": "MetisRC/1.0"}
    key = _s2_api_key()
    if key:
        headers["x-api-key"] = key

    last_err = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read().decode("utf-8"))
            return data.get("data", []) or []
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt == 0:
                time.sleep(3)  # brief backoff, then one retry
                continue
            raise
    if last_err:
        raise last_err
    return []


@app.tool()
async def search_semantic_scholar(
    query: str = "",
    max_results: int = 10,
) -> list[TextContent]:
    """Search Semantic Scholar for papers on a topic (citation-graph discovery).

    Complements PubMed (scan_pubmed_alerts) and OpenAlex (scan_openalex) with
    Semantic Scholar's 200M+ paper graph and citation counts. Free public Graph
    API, no key required. Matched papers are inserted into news_briefs with
    source_type='article' (domain 'Semantic Scholar') so the Librarian and the
    dashboard surface them like any other discovered paper.

    Args:
        query: Free-text topic to search (e.g. "HAT elimination surveillance").
               Defaults to your configured PubMed/topic query if empty.
        max_results: Maximum papers to retrieve (default 10, max 100).
    """
    if not query:
        query = _user_pubmed_query()
    import sqlite3

    try:
        items = _semanticscholar_search(query, max_results)
    except Exception as e:
        return [TextContent(type="text", text=f"Semantic Scholar search error: {e}")]

    if not items:
        return [TextContent(type="text", text=f"Semantic Scholar: no papers for '{query}'.")]

    added = 0
    try:
        con = sqlite3.connect(str(paths.db))
        for item in items:
            title = item.get("title") or "Untitled"
            ext = item.get("externalIds") or {}
            doi = ext.get("DOI") or ""
            url = (f"https://doi.org/{doi}" if doi else "") or item.get("url") or ""
            if not url:
                continue
            authors = "; ".join(
                a.get("name", "") for a in (item.get("authors") or [])[:4] if a.get("name")
            )
            year = item.get("year") or ""
            venue = item.get("venue") or ""
            cites = item.get("citationCount")
            abstract = (item.get("abstract") or "")[:300]
            cite_str = f" · {cites} citations" if isinstance(cites, int) else ""
            summary_text = f"{authors} ({year}). {venue}{cite_str}. {abstract}".strip()
            if _insert_article(con, title, summary_text, url, "Semantic Scholar", "semanticscholar,article"):
                added += 1
        con.commit()
        con.close()
    except Exception as e:
        return [TextContent(type="text", text=f"Semantic Scholar DB insert error: {e}")]

    return [TextContent(
        type="text",
        text=f"Semantic Scholar: {added} new papers added from {len(items)} results for '{query}'.",
    )]
