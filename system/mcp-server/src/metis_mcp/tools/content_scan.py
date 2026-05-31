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
    # Disease surveillance & outbreak monitoring
    ("WHO outbreak news",      "https://www.who.int/feeds/entity/csr/don/en/rss.xml",                                    "surveillance,public-health"),
    ("ProMED-mail",            "https://promedmail.org/feed/",                                                            "surveillance,infectious-disease,public-health"),
    ("ECDC Threat Reports",    "https://www.ecdc.europa.eu/en/rss.xml",                                                  "surveillance,public-health"),
    ("Africa CDC",             "https://africacdc.org/feed/",                                                             "surveillance,public-health,africa"),
    # Infectious disease & NTD research
    ("PLOS NTDs",              "https://journals.plos.org/plosntds/feed/atom",                                            "ntd,tropical-medicine,public-health"),
    ("CDC EID journal",        "https://wwwnc.cdc.gov/eid/rss/ahead-of-print.xml",                                       "methods,surveillance"),
    ("Lancet Inf. Diseases",   "https://www.thelancet.com/rssFeed/laninf_current.xml",                                   "infectious-disease,public-health,methods"),
    ("MSF Science",            "https://www.msf.org/rss.xml",                                                            "field-research,public-health,tropical-medicine"),
    ("Eurosurveillance",       "https://www.eurosurveillance.org/content/rss.xml",                                       "surveillance,methods,public-health"),
    # Global health research
    ("PLOS Medicine",          "https://journals.plos.org/plosmedicine/feed/atom",                                        "public-health,methods"),
    ("BMJ Global Health",      "https://gh.bmj.com/rss/current.xml",                                                     "public-health,methods"),
    ("Nature Medicine",        "https://www.nature.com/nm.rss",                                                           "methods,biomedical"),
    ("Tropical Med & IH",      "https://onlinelibrary.wiley.com/action/showFeed?jc=13653156&type=etoc&feed=rss",         "tropical-medicine,methods,public-health"),
    # Global health policy
    ("IHP Newsletter",         "https://www.internationalhealthpolicies.org/feed/",                                       "policy,public-health"),
    ("DEVEX Global Health",    "https://www.devex.com/news/rss.xml",                                                     "policy,public-health"),
    ("The New Humanitarian",   "https://www.thenewhumanitarian.org/rss.xml",                                              "policy,public-health,africa"),
    ("Reliefweb",              "https://reliefweb.int/updates/rss.xml",                                                  "policy,public-health"),
    # World / general context
    ("BBC World",              "https://feeds.bbci.co.uk/news/world/rss.xml",                                             "world-news"),
    ("Reuters World",          "https://feeds.reuters.com/Reuters/worldNews",                                             "world-news"),
    # AI & methods
    ("Anthropic News",         "https://www.anthropic.com/news/rss.xml",                                                  "AI"),
    ("arXiv cs.AI",            "https://rss.arxiv.org/rss/cs.AI",                                                         "AI,methods"),
    ("arXiv q-bio (epi)",      "https://rss.arxiv.org/rss/q-bio.PE",                                                      "epidemiology,methods"),
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


_TRYPANOSOMIASIS_KEYWORDS = {
    "trypanosomiasis", "trypanosoma", "sleeping sickness", "tsetse",
    "gambiense", "rhodesiense",
}
_NTD_KEYWORDS = {
    "neglected tropical", "ntd", "leishmaniasis", "schistosomiasis", "onchocerciasis",
    "lymphatic filariasis", "soil-transmitted helminths", "chagas",
}
_DOMAIN_OVERRIDE: list[tuple[set[str], str]] = [
    (_TRYPANOSOMIASIS_KEYWORDS, "NTD"),
    (_NTD_KEYWORDS,             "NTD"),
    ({"malaria", "plasmodium", "artemisinin", "bed net"}, "MALARIA"),
    ({"dhis2", "dhis 2", "health information system", "his implementation"}, "DHIS2"),
    ({"surveillance system", "disease surveillance", "outbreak detection",
      "epidemic intelligence", "who alert"}, "surveillance"),
    ({"llm", "large language model", "machine learning", "neural network",
      "artificial intelligence", "deep learning", "transformer", "gpt", "claude",
      "gemini", "generative ai", "agentic", "agent framework"}, "AI"),
]


def _classify_domain(title: str, summary: str, feed_tags: str) -> str:
    """Return the most specific domain for an article.

    Checks title + summary text against keyword sets first. If a keyword matches,
    that domain wins over the feed-level tag. Falls back to the first feed tag so
    we never return an empty string.
    """
    haystack = (title + " " + summary).lower()
    for keywords, domain in _DOMAIN_OVERRIDE:
        if any(kw in haystack for kw in keywords):
            return domain
    # No keyword match — fall back to first feed tag
    return feed_tags.split(",")[0].strip()


# High-authority sources — a hit here lifts the signal one level.
_AUTHORITY_SOURCES = {
    "who outbreak news", "lancet inf. diseases", "nature medicine",
    "plos medicine", "plos ntds", "eurosurveillance", "cdc eid journal",
    "africa cdc", "ecdc threat reports", "bmj global health",
}
# Words that mark a genuinely high-signal development (not routine coverage).
_URGENCY_WORDS = {
    "outbreak", "emergency", "alert", "elimination", "eliminated", "breakthrough",
    "first case", "resurgence", "epidemic", "pandemic", "recall", "withdrawn",
    "approval", "approved", "vaccine", "resistance", "novel", "emerging",
}


def _user_topics() -> set[str]:
    """Lower-cased research topics/field from user-config.yaml, for relevance scoring."""
    try:
        import yaml
        cfg_path = paths.config / "user-config.yaml"
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            research = cfg.get("research", {}) if isinstance(cfg.get("research"), dict) else {}
            topics = research.get("topics") or cfg.get("topics") or []
            if isinstance(topics, str):
                topics = [t.strip() for t in topics.split(",")]
            field = research.get("field") or cfg.get("field") or ""
            out = {str(t).strip().lower() for t in topics if str(t).strip()}
            if field:
                out.add(str(field).strip().lower())
            return out
    except Exception:
        pass
    return set()


def _score_signal(title: str, summary: str, feed_name: str, user_topics: set[str]) -> str:
    """Heuristic signal strength: 'high' | 'medium' | 'low'.

    Replaces the old hardcoded 'medium'. Combines source authority, urgency
    vocabulary, and relevance to the user's configured research topics so the
    stored value is meaningful even before an agent re-scores at read time.
    """
    haystack = (title + " " + summary).lower()
    score = 0
    if feed_name.lower() in _AUTHORITY_SOURCES:
        score += 1
    if any(w in haystack for w in _URGENCY_WORDS):
        score += 2  # an outbreak / approval / elimination is a strong signal on its own
    if user_topics and any(t in haystack for t in user_topics):
        score += 2  # direct relevance to the researcher's own topics matters most
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def scan_news_feeds(max_per_feed: int = 10) -> dict:
    added = 0
    errors = []
    user_topics = _user_topics()
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
                    primary_domain = _classify_domain(title, summary_raw, tags)
                    signal = _score_signal(title, summary_raw, name, user_topics)
                    conn.execute(
                        """INSERT INTO news_briefs
                           (title, domain, signal_strength, summary, source_url, created_at, tags, brief_date)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (title, primary_domain, signal, summary_raw, link,
                         datetime.now().isoformat(), tags, datetime.now().date().isoformat()),
                    )
                    added += 1
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
        conn.commit()
    return {"news_added": added, "errors": errors}


def scan_literature_folder() -> dict:
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


AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".aac", ".opus", ".webm"}
DOC_EXTS   = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx"}


def _scan_inbox() -> dict:
    """Count and categorise files in inbox/ that haven't been processed."""
    inbox = paths.root / "inbox"
    if not inbox.exists():
        return {"inbox_items": 0, "audio": [], "docs": [], "other": []}
    items = [f for f in inbox.iterdir() if f.is_file() and not f.name.startswith(".")]
    audio = [f for f in items if f.suffix.lower() in AUDIO_EXTS]
    docs  = [f for f in items if f.suffix.lower() in DOC_EXTS]
    other = [f for f in items if f not in audio and f not in docs]
    return {
        "inbox_items": len(items),
        "audio": [str(f) for f in audio],
        "docs":  [f.name for f in docs],
        "other": [f.name for f in other],
        "files": [f.name for f in items[:10]],
    }


def _transcribe_inbox_audio(audio_path: str, model_size: str = "base") -> str | None:
    """Transcribe a single audio file with faster-whisper. Returns text or None."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, beam_size=3)
        return " ".join(seg.text.strip() for seg in segments).strip() or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@app.tool()
async def scan_news() -> list[TextContent]:
    """Fetch RSS feeds and add new items to news_briefs.

    Checks WHO outbreak news, CDC EID journal, PLOS NTDs, and Anthropic news.
    Deduplicates by URL so running multiple times is safe.
    """
    result = scan_news_feeds()
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
    result = scan_literature_folder()
    note = result.get("note", "")
    msg = f"Literature scan complete. {result['papers_added']} new papers registered."
    if note:
        msg += f" ({note})"
    return [TextContent(type="text", text=msg)]


@app.tool()
async def scan_inbox(auto_transcribe_audio: bool = True) -> list[TextContent]:
    """Scan the inbox/ folder and auto-transcribe any audio files to ideas.

    Detects audio files (.m4a, .mp3, .wav, .ogg, .flac, .aac) and, when
    auto_transcribe_audio=True (default), transcribes each one with faster-whisper
    and captures the transcript as an idea. The audio file is moved to
    inbox/processed/ after successful transcription.

    Non-audio files are listed but left for manual review.

    Args:
        auto_transcribe_audio: When True (default), automatically transcribe
            audio files found in the inbox. Set to False to just list them.
    """
    import os
    import shutil
    result = _scan_inbox()
    n = result["inbox_items"]
    if n == 0:
        return [TextContent(type="text", text="Inbox is clear.")]

    lines: list[str] = [f"Inbox: {n} item(s) found."]
    audio_paths = result.get("audio", [])
    docs  = result.get("docs", [])
    other = result.get("other", [])

    # ── Audio files: auto-transcribe ─────────────────────────────────────────
    transcribed, failed = 0, 0
    if audio_paths and auto_transcribe_audio:
        lines.append(f"\n🎙 Audio files ({len(audio_paths)}) — transcribing with Whisper:")
        processed_dir = paths.root / "inbox" / "processed"
        processed_dir.mkdir(exist_ok=True)

        for audio_path_str in audio_paths:
            audio_path = Path(audio_path_str)
            fname = audio_path.name
            text = _transcribe_inbox_audio(str(audio_path))
            if text:
                # Capture as idea via cross-pollination
                try:
                    from metis_mcp.tools.ideas import _cross_pollinate_core
                    from metis_mcp.db import connect
                    now = datetime.now().isoformat()
                    with connect(paths.db) as conn:
                        conn.execute(
                            "INSERT INTO ideas (content, tags, created_at) VALUES (?, ?, ?)",
                            (text, f"voice-note,inbox,auto-transcribed", now),
                        )
                    connections = _cross_pollinate_core(text[:400], max_results=3) or []
                except Exception:
                    connections = []

                conn_summary = ""
                if connections:
                    conn_summary = " → " + ", ".join(c.get("title", "")[:40] for c in connections[:2])

                lines.append(f"  ✓ {fname}: \"{text[:80]}…\"{conn_summary}")
                transcribed += 1

                # Move to processed/
                try:
                    shutil.move(str(audio_path), str(processed_dir / fname))
                except Exception:
                    pass
            else:
                lines.append(f"  ✗ {fname}: transcription failed (faster-whisper not installed or empty audio)")
                failed += 1

    elif audio_paths:
        lines.append(f"\n🎙 Audio files ({len(audio_paths)}) — set auto_transcribe_audio=True to process:")
        for p in audio_paths:
            lines.append(f"  · {Path(p).name}")

    # ── Documents ─────────────────────────────────────────────────────────────
    if docs:
        lines.append(f"\n📄 Documents ({len(docs)}) — route manually:")
        for f in docs[:5]:
            lines.append(f"  · {f}")
        if len(docs) > 5:
            lines.append(f"  · … and {len(docs) - 5} more")

    # ── Other ─────────────────────────────────────────────────────────────────
    if other:
        lines.append(f"\n📦 Other ({len(other)}):")
        for f in other[:5]:
            lines.append(f"  · {f}")

    if transcribed:
        lines.append(f"\n✓ {transcribed} voice note(s) captured as ideas. Audio moved to inbox/processed/.")
    if failed:
        lines.append(f"⚠ {failed} audio file(s) could not be transcribed — install faster-whisper if missing.")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def get_news_briefs(
    limit: int = 10,
    source_type: str = "",
    domain: str = "",
    since: str = "",
) -> list[TextContent]:
    """Retrieve recent news briefs from the database.

    Args:
        limit: Maximum number of briefs to return (default 10).
        source_type: Filter by type — "news" for RSS items, "article" for scientific papers. Empty = all.
        domain: Filter by domain tag (e.g. "HAT", "AI", "public-health"). Empty = all.
        since: ISO date string — only return briefs created after this date. Empty = all.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="Database not found.")]

    conditions: list[str] = []
    params: list = []
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)
    if domain:
        conditions.append("domain = ?")
        params.append(domain)
    if since:
        conditions.append("created_at >= ?")
        params.append(since)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    with _connect() as conn:
        conn.execute(_DDL_NEWS)
        rows = conn.execute(
            f"SELECT brief_id, title, domain, signal_strength, summary, source_url, "
            f"source_type, created_at, tags "
            f"FROM news_briefs {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()

    if not rows:
        return [TextContent(type="text", text="No news briefs found.")]

    lines = [f"{len(rows)} brief(s):\n"]
    for r in rows:
        tag = f"[{(r['domain'] or '').upper()}]" if r["domain"] else "[—]"
        src = f"\n  {r['source_url']}" if r["source_url"] else ""
        summary = (r["summary"] or "")[:200]
        lines.append(f"{tag} {r['title']}\n  {summary}{src}")
    return [TextContent(type="text", text="\n\n".join(lines))]


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
        news = scan_news_feeds()
        err_note = f" ({len(news['errors'])} feed errors)" if news["errors"] else ""
        lines.append(f"NEWS       {news['news_added']:>4} new items{err_note}")
    except Exception as e:
        lines.append(f"NEWS       ERROR: {e}")

    # 2. Literature
    try:
        lit = scan_literature_folder()
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
