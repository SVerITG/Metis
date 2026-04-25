"""Content scan tools — RSS feed ingestion + literature discovery.
No LLM calls. Pure data fetching and dedup against news_briefs / literature_metadata.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import feedparser

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
    created_at TEXT
)
"""


def _connect():
    conn = sqlite3.connect(str(paths.db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def scan_news_feeds(max_per_feed: int = 10) -> dict:
    """Fetch allowed RSS feeds, insert deduped entries into news_briefs."""
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
                    exists = conn.execute(
                        "SELECT 1 FROM news_briefs WHERE source_url=? LIMIT 1", (link,)
                    ).fetchone()
                    if exists:
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

    return {"status": "ok" if not errors else "partial", "news_added": added, "errors": errors}


def scan_literature_folder() -> dict:
    """Scan inputs/literature/ for new PDFs and register any not yet in literature_metadata."""
    lit_path = paths.root / "inputs" / "literature"
    if not lit_path.exists():
        return {"status": "ok", "papers_added": 0, "note": "no literature folder"}

    added = 0
    with _connect() as conn:
        conn.execute(_DDL_LIT)
        conn.commit()

        for pdf in lit_path.rglob("*.pdf"):
            stem = pdf.stem
            exists = conn.execute(
                "SELECT 1 FROM literature_metadata WHERE title=? LIMIT 1", (stem,)
            ).fetchone()
            if exists:
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

    return {"status": "ok", "papers_added": added}
