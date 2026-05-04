"""Content scan tools — RSS feed ingestion, literature discovery, inbox scan.
No LLM calls. Pure data fetching and dedup.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import feedparser

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

FEED_ALLOWLIST = [
    ("WHO outbreak news",  "https://www.who.int/feeds/entity/csr/don/en/rss.xml",           "HAT,public-health"),
    ("CDC EID journal",    "https://wwwnc.cdc.gov/eid/rss/ahead-of-print.xml",              "methods,public-health"),
    ("PLOS NTDs latest",   "https://journals.plos.org/plosntds/feed/atom",                   "HAT,public-health,methods"),
    ("Anthropic News",     "https://www.anthropic.com/news/rss.xml",                         "AI"),
]

_DDL_NEWS = """
CREATE TABLE IF NOT EXISTS news_briefs (
    brief_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT,
    domain         TEXT,
    signal_strength TEXT,
    summary        TEXT,
    source_url     TEXT,
    created_at     TEXT,
    tags           TEXT,
    brief_date     TEXT
)
"""

_DDL_LIT = """
CREATE TABLE IF NOT EXISTS literature_metadata (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT,
    authors    TEXT,
    year       INTEGER,
    source     TEXT,
    tags       TEXT,
    doi        TEXT,
    created_at TEXT
)
"""


def _connect():
    conn = sqlite3.connect(str(paths.db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _scan_news_feeds(max_per_feed: int = 10) -> dict:
    added = 0
    errors = []
    with _connect() as conn:
        conn.execute(_DDL_NEWS)
        conn.commit()
        for name, url, tags in FEED_ALLOWLIST:
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries[:max_per_feed]:
                    link = entry.get("link", "")
                    title = entry.get("title", "").strip()
                    if not link or not title:
                        continue
                    if conn.execute(
                        "SELECT 1 FROM news_briefs WHERE source_url=? LIMIT 1", (link,)
                    ).fetchone():
                        continue
                    summary_raw = entry.get("summary", "")[:800]
                    primary_domain = tags.split(",")[0]
                    conn.execute(
                        """INSERT INTO news_briefs
                           (title, domain, signal_strength, summary, source_url, created_at, tags, brief_date)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (title, primary_domain, "medium", summary_raw, link,
                         datetime.now().isoformat(), tags, datetime.now().date().isoformat()),
                    )
                    added += 1
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
        conn.commit()
    return {"news_added": added, "errors": errors}


def _scan_literature_folder() -> dict:
    """Scan inputs/literature/ for new PDFs not yet in literature_metadata."""
    lit_path = paths.root / "inputs" / "literature"
    if not lit_path.exists():
        return {"papers_added": 0, "note": "no literature folder"}
    added = 0
    with _connect() as conn:
        conn.execute(_DDL_LIT)
        conn.commit()
        for pdf in lit_path.rglob("*.pdf"):
            stem = pdf.stem
            if conn.execute(
                "SELECT 1 FROM literature_metadata WHERE title=? LIMIT 1", (stem,)
            ).fetchone():
                continue
            domain_hint = pdf.parent.name
            conn.execute(
                """INSERT INTO literature_metadata
                   (title, authors, year, source, tags, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (stem, "unknown", None, "local-pdf", domain_hint, datetime.now().isoformat()),
            )
            added += 1
        conn.commit()
    return {"papers_added": added}


def _scan_inbox() -> dict:
    """Count files in inbox/ that haven't been processed."""
    inbox = paths.root / "inbox"
    if not inbox.exists():
        return {"inbox_items": 0}
    items = [f for f in inbox.iterdir() if f.is_file() and not f.name.startswith(".")]
    return {"inbox_items": len(items), "files": [f.name for f in items[:10]]}


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@app.tool()
async def scan_news() -> list[TextContent]:
    """Fetch RSS feeds and add new items to news_briefs.

    Checks WHO outbreak news, CDC EID journal, PLOS NTDs, and Anthropic news.
    Deduplicates by URL so running multiple times is safe.
    """
    result = _scan_news_feeds()
    errors = result.get("errors", [])
    msg = f"News scan complete. {result['news_added']} new items added."
    if errors:
        msg += f"\nErrors ({len(errors)}): " + "; ".join(errors[:3])
    return [TextContent(type="text", text=msg)]


@app.tool()
async def scan_literature() -> list[TextContent]:
    """Scan inputs/literature/ for new PDFs and register them in literature_metadata.

    Walks all subdirectories. Uses the parent folder name as a domain tag.
    Deduplicates by title so running multiple times is safe.
    """
    result = _scan_literature_folder()
    note = result.get("note", "")
    msg = f"Literature scan complete. {result['papers_added']} new papers registered."
    if note:
        msg += f" ({note})"
    return [TextContent(type="text", text=msg)]


@app.tool()
async def scan_inbox() -> list[TextContent]:
    """Report unprocessed files sitting in the inbox/ folder."""
    result = _scan_inbox()
    n = result["inbox_items"]
    if n == 0:
        return [TextContent(type="text", text="Inbox is clear.")]
    files = result.get("files", [])
    lines = [f"Inbox: {n} unprocessed item(s)."]
    for f in files:
        lines.append(f"  · {f}")
    if n > 10:
        lines.append(f"  · ... and {n - 10} more")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def full_scan() -> list[TextContent]:
    """Run all Metis update scans in sequence and return a combined report.

    Runs:
    1. News feeds (RSS) — new items added to news_briefs
    2. Literature folder — new PDFs registered in literature_metadata
    3. Inbox — unprocessed items flagged
    4. Tracked files — changed files reported

    No LLM calls. Safe to run at any time.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"── Metis Full Scan ── {now} ──\n"]

    # 1. News
    try:
        news = _scan_news_feeds()
        err_note = f" ({len(news['errors'])} feed errors)" if news["errors"] else ""
        lines.append(f"NEWS       {news['news_added']:>4} new items{err_note}")
    except Exception as e:
        lines.append(f"NEWS       ERROR: {e}")

    # 2. Literature
    try:
        lit = _scan_literature_folder()
        note = f" ({lit.get('note', '')})" if lit.get("note") else ""
        lines.append(f"LITERATURE {lit['papers_added']:>4} new papers{note}")
    except Exception as e:
        lines.append(f"LITERATURE ERROR: {e}")

    # 3. Inbox
    try:
        inbox = _scan_inbox()
        n = inbox["inbox_items"]
        lines.append(f"INBOX      {n:>4} unprocessed item(s)")
        if n and inbox.get("files"):
            for f in inbox["files"][:5]:
                lines.append(f"             · {f}")
    except Exception as e:
        lines.append(f"INBOX      ERROR: {e}")

    # 4. Tracked files
    try:
        from metis_mcp.db import connect
        import datetime as _dt
        utcnow = _dt.datetime.now(_dt.timezone.utc).isoformat()
        changed = []
        with connect(paths.db) as conn:
            rows = conn.execute(
                "SELECT path, last_modified FROM tracked_files WHERE watch = 1"
            ).fetchall()
            for row in rows:
                fp = Path(row["path"])
                if fp.exists():
                    mtime = _dt.datetime.fromtimestamp(
                        fp.stat().st_mtime, tz=_dt.timezone.utc
                    ).isoformat()
                    if mtime > (row["last_modified"] or ""):
                        changed.append(fp.name)
                        conn.execute(
                            "UPDATE tracked_files SET last_modified=? WHERE path=?",
                            (mtime, row["path"]),
                        )
            conn.commit()
        lines.append(f"FILES      {len(changed):>4} changed since last scan")
        for f in changed[:5]:
            lines.append(f"             · {f}")
    except Exception as e:
        lines.append(f"FILES      ERROR: {e}")

    lines.append("\nDashboard: http://127.0.0.1:8000")
    return [TextContent(type="text", text="\n".join(lines))]
