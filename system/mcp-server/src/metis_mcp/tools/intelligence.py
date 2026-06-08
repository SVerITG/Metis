"""Daily insight generation and publication tracking tools."""

import datetime

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_DAILY_INSIGHTS_DDL = """
CREATE TABLE IF NOT EXISTS daily_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_date TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    sources TEXT DEFAULT '',
    generated_at TEXT NOT NULL,
    model TEXT DEFAULT ''
)
"""

_NEW_PUBLICATIONS_DDL = """
CREATE TABLE IF NOT EXISTS new_publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    journal TEXT DEFAULT '',
    pub_date TEXT DEFAULT '',
    doi TEXT DEFAULT '',
    topic_tag TEXT DEFAULT '',
    relevance_note TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    read_at TEXT DEFAULT '',
    discovered_at TEXT NOT NULL
)
"""

_USER_TOPICS_DDL = """
CREATE TABLE IF NOT EXISTS user_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
)
"""


def _ensure_tables(conn):
    """Create all intelligence tables if they don't exist."""
    conn.execute(_DAILY_INSIGHTS_DDL)
    conn.execute(_NEW_PUBLICATIONS_DDL)
    conn.execute(_USER_TOPICS_DDL)


@app.tool()
async def generate_daily_insight() -> list[TextContent]:
    """Assemble recent activity into context for the daily insight.

    Gathers the raw material for a "what's happening across your research"
    digest: the last 7 days of agent_runs summaries, last 3 days of high-signal
    news_briefs, last 14 days of meeting titles, and last 7 days of new library
    additions. It stores a placeholder row in daily_insights; the Metis agent
    does the actual synthesis from the returned context. Read the stored result
    later with get_daily_insight.

    Takes no arguments.

    Returns:
        A text block of the assembled recent context (and the sources drawn on)
        for the agent to synthesize into a daily insight.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    d7 = (now - datetime.timedelta(days=7)).isoformat()
    d3 = (now - datetime.timedelta(days=3)).isoformat()
    d14 = (now - datetime.timedelta(days=14)).isoformat()

    sources_used = []
    context_parts = []

    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)

            # 1. Agent runs (last 7 days)
            _table_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_runs'"
            ).fetchone()
            if _table_exists:
                cur = conn.execute(
                    "SELECT agent_slug, task_summary, created_at FROM agent_runs "
                    "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 30",
                    (d7,),
                )
                rows = cur.fetchall()
                if rows:
                    lines = ["## Recent Agent Activity (7d)\n"]
                    for r in rows:
                        lines.append(f"- [{r['agent_slug']}] {r['task_summary']}")
                    context_parts.append("\n".join(lines))
                    sources_used.append(f"agent_runs:{len(rows)}")

            # 2. News briefs (last 3 days)
            _table_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='news_briefs'"
            ).fetchone()
            if _table_exists:
                cur = conn.execute(
                    "SELECT title, summary FROM news_briefs "
                    "WHERE rowid IN (SELECT rowid FROM news_briefs ORDER BY rowid DESC LIMIT 20) "
                    "LIMIT 10",
                )
                rows = cur.fetchall()
                if rows:
                    lines = ["## Recent News (3d)\n"]
                    for r in rows:
                        title = r["title"] or ""
                        summary = str(r["summary"] or "")[:200]
                        lines.append(f"- **{title}**: {summary}")
                    context_parts.append("\n".join(lines))
                    sources_used.append(f"news_briefs:{len(rows)}")

            # 3. Meetings (last 14 days)
            _table_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='meetings'"
            ).fetchone()
            if _table_exists:
                cur = conn.execute(
                    "SELECT title, date FROM meetings ORDER BY date DESC LIMIT 15",
                )
                rows = cur.fetchall()
                if rows:
                    lines = ["## Recent Meetings (14d)\n"]
                    for r in rows:
                        lines.append(f"- {r['title']} ({r['date']})")
                    context_parts.append("\n".join(lines))
                    sources_used.append(f"meetings:{len(rows)}")

            # 4. Library additions (last 7 days)
            _table_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='library_seeded'"
            ).fetchone()
            if _table_exists:
                cur = conn.execute(
                    "SELECT title, relevance_note FROM library_seeded "
                    "ORDER BY rowid DESC LIMIT 10",
                )
                rows = cur.fetchall()
                if rows:
                    lines = ["## Recent Library Additions\n"]
                    for r in rows:
                        note = str(r["relevance_note"] or "")[:150]
                        lines.append(f"- {r['title']}: {note}")
                    context_parts.append("\n".join(lines))
                    sources_used.append(f"library_seeded:{len(rows)}")

            # Store placeholder
            assembled = "\n\n".join(context_parts) if context_parts else "No recent context available."
            sources_str = ", ".join(sources_used)

            conn.execute(
                """INSERT INTO daily_insights (insight_date, content, sources, generated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(insight_date) DO UPDATE SET
                       content = excluded.content,
                       sources = excluded.sources,
                       generated_at = excluded.generated_at""",
                (today, assembled, sources_str, now.isoformat()),
            )
            conn.commit()

        result = {
            "date": today,
            "context_assembled": assembled,
            "sources_used": sources_used,
        }

        lines = [
            f"**Daily insight context assembled for {today}**",
            f"Sources: {sources_str or 'none'}",
            f"Context length: {len(assembled)} chars",
            "",
            assembled[:2000] + ("..." if len(assembled) > 2000 else ""),
        ]

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error generating daily insight: {e}")]


def assemble_daily_context(db_path) -> dict:
    """Assemble daily briefing context from the database. Pure function, no MCP.

    Returns a dict with keys: ``date``, ``context`` (assembled prose), ``sources``.
    Callable directly from the FastAPI dashboard without going through MCP.
    """
    import sqlite3 as _sqlite3
    import json as _json
    import yaml as _yaml

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    d7 = (now - datetime.timedelta(days=7)).isoformat()
    d3 = (now - datetime.timedelta(days=3)).isoformat()
    d30 = (now - datetime.timedelta(days=30)).isoformat()

    sources_used: list[str] = []
    context_parts: list[str] = []

    def _q(conn, sql, params=()):
        try:
            cur = conn.execute(sql, params)
            return cur.fetchall()
        except Exception:
            return []

    # Load user profile for personalised context header
    researcher_name = "Researcher"
    research_field = ""
    monitored_topics: list[str] = []
    try:
        rc_root = paths.root
        cfg_path = rc_root / "system" / "config" / "user-config.yaml"
        prefs_path = rc_root / "system" / "config" / "user-preferences.json"
        if cfg_path.exists():
            cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            researcher_name = cfg.get("user", {}).get("name", "Researcher") or "Researcher"
            research_field = cfg.get("research", {}).get("field", "")
        if prefs_path.exists():
            prefs = _json.loads(prefs_path.read_text(encoding="utf-8"))
            monitored_topics = prefs.get("news_topics", [])
    except Exception:
        pass

    if research_field or monitored_topics:
        header_parts = []
        if research_field:
            header_parts.append(f"Researcher field: {research_field}")
        if monitored_topics:
            header_parts.append(f"Monitoring topics: {', '.join(monitored_topics[:8])}")
        context_parts.append("## Researcher Profile\n" + "\n".join(header_parts))

    try:
        conn = _sqlite3.connect(str(db_path))
        conn.row_factory = _sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")

        # News briefs + literature alerts (3d) — recency-first, signal breaks ties.
        # Items from the last 24h always lead regardless of signal_strength.
        d1 = (now - datetime.timedelta(days=1)).isoformat()
        rows = _q(conn,
            "SELECT title, summary, domain, source_type FROM news_briefs "
            "WHERE created_at >= ? ORDER BY "
            "CASE WHEN created_at >= ? THEN 0 ELSE 1 END, "
            "CASE WHEN signal_strength='high' THEN 1 WHEN signal_strength='medium' THEN 2 ELSE 3 END, "
            "created_at DESC LIMIT 15", (d3, d1))
        if rows:
            news_items = [r for r in rows if (r["source_type"] or "news") == "news"]
            lit_items  = [r for r in rows if r["source_type"] == "article"]
            if news_items:
                lines = ["## Field News (last 3 days)"]
                for r in news_items:
                    tag = f"[{r['domain'].upper()}] " if r["domain"] else ""
                    lines.append(f"- {tag}{r['title']}: {str(r['summary'] or '')[:200]}")
                context_parts.append("\n".join(lines))
                sources_used.append(f"news:{len(news_items)}")
            if lit_items:
                lines = ["## New Literature Alerts"]
                for r in lit_items:
                    lines.append(f"- {r['title']}: {str(r['summary'] or '')[:200]}")
                context_parts.append("\n".join(lines))
                sources_used.append(f"literature_alerts:{len(lit_items)}")
        else:
            # No news in DB — note this so the brief can acknowledge it
            context_parts.append(
                "## Field News\n"
                "No news scan has run yet today. "
                "The researcher can trigger a scan via the dashboard 'Scan now' button."
            )

        # Recent literature additions (30d) — papers added to the library
        rows = _q(conn,
            "SELECT title, abstract, year FROM literature_metadata "
            "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 8", (d30,))
        if rows:
            lines = ["## Recently Added Papers"]
            for r in rows:
                year = f" ({r['year']})" if r.get("year") else ""
                snippet = str(r["abstract"] or "")[:150]
                lines.append(f"- {r['title']}{year}" + (f": {snippet}" if snippet else ""))
            context_parts.append("\n".join(lines))
            sources_used.append(f"papers:{len(rows)}")

        # Ideas (7d)
        rows = _q(conn,
            "SELECT text FROM ideas "
            "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 6", (d7,))
        if rows:
            lines = ["## Recent Research Ideas"]
            for r in rows:
                lines.append(f"- {str(r['text'] or '')[:120]}")
            context_parts.append("\n".join(lines))
            sources_used.append(f"ideas:{len(rows)}")

        # Open tasks (priority-ordered)
        rows = _q(conn,
            "SELECT title, priority FROM tasks WHERE status IN ('open','in_progress','blocked') "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 5")
        if rows:
            lines = ["## Open Tasks"]
            for r in rows:
                lines.append(f"- [{r['priority']}] {r['title']}")
            context_parts.append("\n".join(lines))
            sources_used.append(f"tasks:{len(rows)}")

        # Active projects
        rows = _q(conn,
            "SELECT title, description FROM projects WHERE status='active' "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 3")
        if rows:
            lines = ["## Active Projects"]
            for r in rows:
                desc = str(r["description"] or "")[:100]
                lines.append(f"- {r['title']}" + (f": {desc}" if desc else ""))
            context_parts.append("\n".join(lines))
            sources_used.append(f"projects:{len(rows)}")

        # Recent agent runs (7d) — brief log of what was worked on
        rows = _q(conn,
            "SELECT agent_slug, task_summary FROM agent_runs "
            "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 8", (d7,))
        if rows:
            lines = ["## Recent AI Activity"]
            for r in rows:
                lines.append(f"- [{r['agent_slug']}] {r['task_summary']}")
            context_parts.append("\n".join(lines))
            sources_used.append(f"agent_runs:{len(rows)}")

        conn.close()
    except Exception:
        pass

    return {
        "date": today,
        "context": "\n\n".join(context_parts) if context_parts else "",
        "sources": ", ".join(sources_used),
    }


@app.tool()
async def get_daily_insight(date: str = "") -> list[TextContent]:
    """Retrieve a stored daily insight.

    Args:
        date: Date in YYYY-MM-DD format. Empty = today.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    if not date:
        date = datetime.date.today().isoformat()

    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            cur = conn.execute(
                "SELECT * FROM daily_insights WHERE insight_date = ?", (date,)
            )
            row = cur.fetchone()

            if not row:
                return [TextContent(type="text", text=f"No insight found for {date}.")]

            lines = [
                f"**Daily Insight: {row['insight_date']}**",
                f"Generated: {row['generated_at'][:16]}",
                f"Sources: {row['sources']}",
                f"Model: {row['model'] or 'n/a'}",
                "",
                row["content"],
            ]
            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving insight: {e}")]


@app.tool()
async def get_new_publications(
    topic: str = "",
    limit: int = 20,
    unread_only: bool = True,
) -> list[TextContent]:
    """Retrieve new publications, optionally filtered by topic.

    Args:
        topic: Filter by topic tag. Empty = all topics.
        limit: Maximum results (default 20).
        unread_only: If True, only return unread publications (default True).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)

            clauses = []
            params: list = []
            if topic:
                clauses.append("topic_tag LIKE ?")
                params.append(f"%{topic}%")
            if unread_only:
                clauses.append("(read_at IS NULL OR read_at = '')")

            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            sql = f"SELECT * FROM new_publications{where} ORDER BY discovered_at DESC LIMIT ?"
            params.append(limit)

            cur = conn.execute(sql, params)
            rows = cur.fetchall()

            if not rows:
                return [TextContent(type="text", text="No publications found matching criteria.")]

            lines = [f"**{len(rows)} publications:**\n"]
            for row in rows:
                read_marker = "" if not row["read_at"] else " [read]"
                doi = f" DOI:{row['doi']}" if row["doi"] else ""
                lines.append(
                    f"- **[{row['id']}]** {row['title']}{read_marker}\n"
                    f"  {row['journal']} ({row['pub_date']}){doi}\n"
                    f"  Topic: {row['topic_tag'] or 'untagged'}"
                )

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving publications: {e}")]


@app.tool()
async def mark_publications_read(ids: list[int]) -> list[TextContent]:
    """Mark new publications as read by their IDs.

    Clears items from the "new publications" queue once the user has seen them,
    stamping each with a read time so they stop resurfacing. Use the IDs
    returned by get_new_publications.

    Args:
        ids: List of new_publications row IDs to mark as read; an empty list is
            a no-op.

    Returns:
        A confirmation message with the count of publications marked as read.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    if not ids:
        return [TextContent(type="text", text="No IDs provided.")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"UPDATE new_publications SET read_at = ? WHERE id IN ({placeholders})",
                [now] + list(ids),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Marked {len(ids)} publication(s) as read.")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error marking publications: {e}")]


@app.tool()
async def get_user_topics() -> list[TextContent]:
    """Return all active topics from user_topics."""
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            cur = conn.execute(
                "SELECT * FROM user_topics WHERE active = 1 ORDER BY topic"
            )
            rows = cur.fetchall()

            if not rows:
                return [TextContent(type="text", text="No active topics. Use add_user_topic to add one.")]

            lines = [f"**{len(rows)} active topics:**\n"]
            for row in rows:
                desc = row["description"] or "no description"
                lines.append(f"- **{row['topic']}**: {desc}")

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving topics: {e}")]


@app.tool()
async def add_user_topic(
    topic: str,
    description: str = "",
) -> list[TextContent]:
    """Add a topic to track for new publications.

    Args:
        topic: Topic name (unique).
        description: Optional description of what to look for.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            conn.execute(
                """INSERT INTO user_topics (topic, description, active, created_at)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(topic) DO UPDATE SET
                       description = CASE WHEN excluded.description != '' THEN excluded.description ELSE user_topics.description END,
                       active = 1""",
                (topic, description, now),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Topic added: **{topic}**")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error adding topic: {e}")]
