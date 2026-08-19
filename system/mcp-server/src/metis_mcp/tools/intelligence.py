"""Daily insight generation and publication tracking tools."""

import datetime

try:
    from mcp.types import TextContent
except ImportError:
    # Stub for non-MCP callers (e.g. FastAPI dashboard importing assemble_* functions).
    # The actual MCP tool handlers are never called in that context.
    TextContent = None                                  # type: ignore[assignment,misc]

from metis_mcp.config import paths
from metis_mcp.db import connect

try:
    from metis_mcp.app_instance import app
except ImportError:
    # Provide a no-op @app.tool() decorator so the module loads without the MCP runtime.
    class _NoopApp:                                     # type: ignore[no-redef]
        def tool(self, *a, **kw):
            def _dec(fn): return fn
            return _dec
    app = _NoopApp()                                    # type: ignore[assignment]

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


@app.tool()
async def save_daily_brief(
    content: str,
    sources: str = "",
    date: str = "",
    model: str = "desktop-brief",
) -> list[TextContent]:
    """Save a composed daily brief so the dashboard widget shows it.

    This is the write-back half of the daily-brief round-trip. Claude Desktop (or
    Claude Code) composes the brief from generate_daily_insight() context, then
    calls this to upsert the finished prose into the daily_insights table — the
    same table the dashboard's morning-brief widget reads via get_daily_insight().
    Desktop and the dashboard share one database, so no files are involved: once
    saved, the brief appears in the dashboard on next load.

    Args:
        content: The finished daily-brief prose (markdown ok). Required.
        sources: Comma-separated list of what the brief drew on (optional).
        date: YYYY-MM-DD; empty = today.
        model: Model identifier that composed it, for provenance (optional).

    Returns:
        Confirmation with the date saved and a pointer to the dashboard widget.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]
    if not (content or "").strip():
        return [TextContent(type="text", text="Nothing saved: `content` is empty.")]

    now = datetime.datetime.now(datetime.timezone.utc)
    if not date:
        date = now.strftime("%Y-%m-%d")

    try:
        with connect(paths.db) as conn:
            _ensure_tables(conn)
            conn.execute(
                """INSERT INTO daily_insights (insight_date, content, sources, generated_at, model)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(insight_date) DO UPDATE SET
                       content = excluded.content,
                       sources = excluded.sources,
                       generated_at = excluded.generated_at,
                       model = excluded.model""",
                (date, content, sources, now.isoformat(), model),
            )
            conn.commit()
        return [TextContent(type="text", text=(
            f"Daily brief saved for {date} ({len(content)} chars). "
            f"It will appear in the dashboard's morning-brief widget on next load."
        ))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error saving daily brief: {e}")]


@app.tool()
async def mark_brief_read(date: str = "", period: str = "daily") -> list[TextContent]:
    """Mark a briefing as read, so its story threads go quiet in the next ones.

    This is what stops the same long-running story leading every morning. Metis
    only puts a thread on cooldown once the brief that carried it was actually
    marked read — a brief that was generated but never read delivered nothing, so
    it must not silence anything. Call this when you have delivered a briefing to
    the researcher in conversation, or when they say they have read it.

    Args:
        date: YYYY-MM-DD of the brief. Empty = today.
        period: "daily", "weekly" or "catchup". Default "daily".

    Returns:
        Confirmation, plus which threads that brief had covered.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    suffix = {"weekly": "-weekly", "catchup": "-catchup"}.get(period, "")
    key = f"{date}{suffix}"
    now = datetime.datetime.now().isoformat()

    try:
        from metis_mcp.tools import news_threads as nt
        with connect(paths.db) as conn:
            nt.ensure_tables(conn)
            row = conn.execute(
                "SELECT insight_date, read_at FROM daily_insights WHERE insight_date = ?",
                (key,),
            ).fetchone()
            if row is None:
                return [TextContent(type="text", text=(
                    f"No {period} brief stored for {date}. Nothing to mark."
                ))]
            already = bool(row["read_at"])
            conn.execute("UPDATE daily_insights SET read_at = ? WHERE insight_date = ?",
                         (now, key))
            covered = conn.execute(
                "SELECT m.thread_id, m.role, m.angle, t.label "
                "FROM news_thread_mentions m "
                "LEFT JOIN news_threads t ON t.thread_id = m.thread_id "
                "WHERE m.insight_key = ? ORDER BY m.role DESC", (key,),
            ).fetchall()
            conn.commit()
    except Exception as e:
        return [TextContent(type="text", text=f"Error marking brief read: {e}")]

    lines = [
        f"{'Already marked read; timestamp refreshed' if already else 'Marked read'}: "
        f"{period} brief for {date}."
    ]
    if covered:
        lines.append("")
        lines.append("Threads now on cooldown:")
        for c in covered:
            label = c["label"] or c["thread_id"]
            angle = f", angle: {c['angle']}" if c["angle"] else ""
            stage = "led" if c["role"] == "lead" else "mentioned"
            lines.append(f"  · {label} — {stage}{angle}")
        lines.append("")
        lines.append(
            "A thread that led goes quiet for 3 days, then 5, then 7 on each "
            "further lead — unless something materially changes."
        )
    else:
        lines.append(
            "\nNo threads were recorded for this brief, so nothing goes on cooldown. "
            "That happens when the brief was composed without the coverage footer."
        )
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def get_briefing_coverage(days: int = 7, show_all: bool = False) -> list[TextContent]:
    """Show which news stories the briefings have covered, and what is on cooldown.

    Answers "why didn't today's brief mention X?" and "what has Metis been
    holding back?". Story threads group many news items into one running story
    (an epidemic, a funding shift), so a long-running event can be surfaced once
    and then held quiet instead of leading every single morning.

    Args:
        days: Window of news activity to consider. Default 7.
        show_all: Include threads with only one item. Default False (recurring only).

    Returns:
        Per thread: size, age, whether it may lead, how long it stays quiet, and
        which analytical angles have already been used on it.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]
    try:
        from metis_mcp.tools import news_threads as nt
        since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        with connect(paths.db) as conn:
            threads = nt.thread_window(conn, since)
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading briefing coverage: {e}")]

    if not threads:
        return [TextContent(type="text", text=f"No news activity in the last {days} days.")]

    if not show_all:
        threads = [t for t in threads if len(t["items"]) > 1] or threads[:10]

    eligible = [t for t in threads if not t["blocked_from_lead"]]
    held = [t for t in threads if t["blocked_from_lead"]]

    lines = [f"**Briefing coverage — last {days} days, {len(threads)} story thread(s)**", ""]
    if eligible:
        lines.append(f"CAN LEAD THE NEXT BRIEF ({len(eligible)}):")
        for t in eligible:
            extra = f" · ESCALATION: {t['material_reason']}" if t["material"] else ""
            hist = (f" · led {t['read_leads']}× before" if t["read_leads"] else " · never covered")
            lines.append(f"  · {t['label']} — {len(t['items'])} item(s), "
                         f"signal {t['top_signal']}{hist}{extra}")
    if held:
        lines.append("")
        lines.append(f"HELD BACK — already delivered ({len(held)}):")
        for t in held:
            if t["read_leads"]:
                why = (f"led {t['days_since_read_lead']}d ago, quiet for "
                       f"{t['cooldown_days']}d")
            else:
                why = f"mentioned {t['days_since_read_mention']}d ago"
            used = ", ".join(t["angles_used"]) or "none yet"
            lines.append(f"  · {t['label']} — {why} · {len(t['items'])} new item(s) "
                         f"· angles used: {used}")
    lines.append("")
    lines.append(
        "Cooldown counts only briefs marked READ. If a brief was never marked "
        "read, its threads stay eligible — nothing was actually delivered."
    )
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def get_missed_news(days: int = 14, min_signal: str = "medium") -> list[TextContent]:
    """Show news that never reached you in a briefing you read.

    "Missed" means never delivered — not merely old. A brief that was generated
    but never marked read delivered nothing, so its stories still count as
    missed. This is what a catch-up briefing should be built from.

    Args:
        days: How far back to look. Default 14.
        min_signal: Minimum signal strength — "high", "medium" or "low". Default "medium".

    Returns:
        Story threads with recent activity that no read briefing ever carried.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]
    try:
        from metis_mcp.tools import news_threads as nt
        with connect(paths.db) as conn:
            missed = nt.missed_threads(conn, days=days, min_signal=min_signal)
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading missed news: {e}")]

    if not missed:
        return [TextContent(type="text", text=(
            f"Nothing missed: every {min_signal}-or-higher story from the last "
            f"{days} days reached you in a briefing you marked read."
        ))]

    lines = [f"**Never delivered — last {days} days, {len(missed)} story thread(s)**", ""]
    for t in missed:
        extra = f" · ESCALATION: {t['material_reason']}" if t["material"] else ""
        lines.append(f"· {t['label']} — {len(t['items'])} item(s), signal "
                     f"{t['top_signal']}{extra}")
        for it in t["items"][:2]:
            lines.append(f"    - {it['title'][:110]}")
    return [TextContent(type="text", text="\n".join(lines))]


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

        # News is grouped into STORY THREADS with read-aware coverage state, so a
        # long-running epidemic cannot lead every morning just because it emits
        # fresh wire items every morning. See tools/news_threads.py for the full
        # rationale. Literature alerts stay a flat list — a paper alert is a
        # discrete event, not a running story, and gets its own slots so
        # higher-recency news can't crowd it out of a shared limit.
        d1 = (now - datetime.timedelta(days=1)).isoformat()
        _order = (
            "ORDER BY CASE WHEN created_at >= ? THEN 0 ELSE 1 END, "
            "CASE WHEN signal_strength='high' THEN 1 WHEN signal_strength='medium' THEN 2 ELSE 3 END, "
            "created_at DESC"
        )
        news_section = ""
        news_threads_n = 0
        try:
            from metis_mcp.tools import news_threads as _nt
            _threads = _nt.thread_window(conn, d3)
            if _threads:
                news_section, _eligible = _nt.render_daily_section(_threads)
                news_threads_n = len(_threads)
        except Exception:
            news_section = ""

        lit_items = _q(conn,
            "SELECT title, summary, domain FROM news_briefs "
            "WHERE created_at >= ? AND source_type = 'article' "
            + _order + " LIMIT 8", (d3, d1))
        if news_section or lit_items:
            if news_section:
                context_parts.append(news_section)
                sources_used.append(f"news_threads:{news_threads_n}")
            if lit_items:
                lines = ["## New Literature Alerts (last 3 days)"]
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

        # Recent literature additions (last 7 days) — papers genuinely added to
        # the library recently. A one-time bulk import (e.g. an initial Zotero
        # sync of hundreds of papers) is NOT "news" — if a single add-date holds
        # a large batch, skip it so the brief doesn't resurface the same old
        # import every day. Within real additions, lead with the newest
        # publication years so old papers don't dominate.
        bulk_dates = {
            r["d"] for r in _q(conn,
                "SELECT substr(created_at,1,10) AS d, COUNT(*) AS n FROM literature_metadata "
                "GROUP BY d HAVING n >= 50")
        }
        rows = _q(conn,
            "SELECT title, abstract, year, substr(created_at,1,10) AS add_day "
            "FROM literature_metadata WHERE created_at >= ? "
            "ORDER BY COALESCE(year,0) DESC, created_at DESC LIMIT 30", (d7,))
        rows = [r for r in rows if r["add_day"] not in bulk_dates][:6]
        if rows:
            lines = ["## Recently Added Papers"]
            for r in rows:
                year = f" ({r['year']})" if r.get("year") else ""
                snippet = str(r["abstract"] or "")[:150]
                lines.append(f"- {r['title']}{year}" + (f": {snippet}" if snippet else ""))
            context_parts.append("\n".join(lines))
            sources_used.append(f"papers:{len(rows)}")

        # Framing context: projects + ideas (relevance anchors, NOT briefing topics)
        framing_parts: list[str] = []
        rows = _q(conn,
            "SELECT title FROM projects WHERE status='active' "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 3")
        if rows:
            framing_parts.append("Active projects: " + ", ".join(r['title'] for r in rows))
            sources_used.append(f"projects:{len(rows)}")

        rows = _q(conn,
            "SELECT text FROM ideas "
            "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 6", (d7,))
        if rows:
            snippets = [str(r['text'] or '')[:80] for r in rows]
            framing_parts.append("Recent ideas: " + "; ".join(snippets))
            sources_used.append(f"ideas:{len(rows)}")

        if framing_parts:
            context_parts.append(
                "## Framing Context (connect external signals to these if relevant "
                "— do not report on them)\n" + "\n".join(framing_parts)
            )

        conn.close()
    except Exception:
        pass

    return {
        "date": today,
        "context": "\n\n".join(context_parts) if context_parts else "",
        "sources": ", ".join(sources_used),
    }


def assemble_weekly_context(db_path) -> dict:
    """Assemble weekly briefing context — wider windows, more items, memory connections.

    Same return shape as assemble_daily_context: {date, context, sources}.
    """
    import sqlite3 as _sqlite3
    import json as _json
    import yaml as _yaml

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    d7 = (now - datetime.timedelta(days=7)).isoformat()
    d14 = (now - datetime.timedelta(days=14)).isoformat()
    d30 = (now - datetime.timedelta(days=30)).isoformat()

    sources_used: list[str] = []
    context_parts: list[str] = []

    def _q(conn, sql, params=()):
        try:
            return conn.execute(sql, params).fetchall()
        except Exception:
            return []

    # Researcher profile header (reuse daily logic)
    try:
        rc_root = paths.root
        cfg_path = rc_root / "system" / "config" / "user-config.yaml"
        prefs_path = rc_root / "system" / "config" / "user-preferences.json"
        researcher_name = "Researcher"
        research_field = ""
        monitored_topics: list[str] = []
        if cfg_path.exists():
            cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            researcher_name = cfg.get("user", {}).get("name", "Researcher") or "Researcher"
            research_field = cfg.get("research", {}).get("field", "")
        if prefs_path.exists():
            prefs = _json.loads(prefs_path.read_text(encoding="utf-8"))
            monitored_topics = prefs.get("news_topics", [])
        if research_field or monitored_topics:
            header_parts = []
            if research_field:
                header_parts.append(f"Researcher field: {research_field}")
            if monitored_topics:
                header_parts.append(f"Monitoring topics: {', '.join(monitored_topics[:8])}")
            context_parts.append("## Researcher Profile\n" + "\n".join(header_parts))
    except Exception:
        pass

    try:
        conn = _sqlite3.connect(str(db_path))
        conn.row_factory = _sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")

        # News (7-day window, limit 20)
        d1 = (now - datetime.timedelta(days=1)).isoformat()
        _order = (
            "ORDER BY CASE WHEN created_at >= ? THEN 0 ELSE 1 END, "
            "CASE WHEN signal_strength='high' THEN 1 WHEN signal_strength='medium' THEN 2 ELSE 3 END, "
            "created_at DESC"
        )
        # The weekly is COMPLETE by design — it carries threads the dailies
        # suppressed, because the researcher reads it as an overview, not a diff. What the
        # thread state changes here is the TREATMENT: an already-seen thread gets
        # its week-long trajectory, a never-delivered one gets reported properly.
        news_section = ""
        news_threads_n = 0
        try:
            from metis_mcp.tools import news_threads as _nt
            _threads = _nt.thread_window(conn, d7)
            if _threads:
                news_section = _nt.render_weekly_section(_threads)
                news_threads_n = len(_threads)
        except Exception:
            news_section = ""

        lit_items = _q(conn,
            "SELECT title, summary, domain FROM news_briefs "
            "WHERE created_at >= ? AND source_type = 'article' "
            + _order + " LIMIT 12", (d7, d1))
        if news_section:
            context_parts.append(news_section)
            sources_used.append(f"news_threads:{news_threads_n}")
        if lit_items:
            lines = ["## New Literature Alerts (last 7 days)"]
            for r in lit_items:
                lines.append(f"- {r['title']}: {str(r['summary'] or '')[:200]}")
            context_parts.append("\n".join(lines))
            sources_used.append(f"literature_alerts:{len(lit_items)}")
        if not news_section and not lit_items:
            context_parts.append(
                "## Field News\nNo news signals found for the past week."
            )

        # Papers (14-day window, limit 10)
        bulk_dates = {
            r["d"] for r in _q(conn,
                "SELECT substr(created_at,1,10) AS d, COUNT(*) AS n FROM literature_metadata "
                "GROUP BY d HAVING n >= 50")
        }
        rows = _q(conn,
            "SELECT title, abstract, year, substr(created_at,1,10) AS add_day "
            "FROM literature_metadata WHERE created_at >= ? "
            "ORDER BY COALESCE(year,0) DESC, created_at DESC LIMIT 40", (d14,))
        rows = [r for r in rows if r["add_day"] not in bulk_dates][:10]
        if rows:
            lines = ["## Recently Added Papers (14 days)"]
            for r in rows:
                year = f" ({r['year']})" if r.get("year") else ""
                snippet = str(r["abstract"] or "")[:150]
                lines.append(f"- {r['title']}{year}" + (f": {snippet}" if snippet else ""))
            context_parts.append("\n".join(lines))
            sources_used.append(f"papers:{len(rows)}")

        # Framing context: projects (5) + ideas (30-day, limit 10)
        framing_parts: list[str] = []
        rows = _q(conn,
            "SELECT title FROM projects WHERE status='active' "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 5")
        if rows:
            framing_parts.append("Active projects: " + ", ".join(r['title'] for r in rows))
            sources_used.append(f"projects:{len(rows)}")

        rows = _q(conn,
            "SELECT text FROM ideas "
            "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 10", (d30,))
        if rows:
            snippets = [str(r['text'] or '')[:80] for r in rows]
            framing_parts.append("Recent ideas: " + "; ".join(snippets))
            sources_used.append(f"ideas:{len(rows)}")

        if framing_parts:
            context_parts.append(
                "## Framing Context (connect external signals to these if relevant "
                "— do not report on them)\n" + "\n".join(framing_parts)
            )

        # Memory connections: keyword search against semantic_memory using top signal titles
        try:
            top_titles = _q(conn,
                "SELECT title FROM news_briefs WHERE created_at >= ? "
                "ORDER BY CASE WHEN signal_strength='high' THEN 1 ELSE 2 END, "
                "created_at DESC LIMIT 5", (d7,))
            if top_titles:
                memory_hits: list[str] = []
                for tt in top_titles:
                    kw = str(tt['title'] or '')[:60]
                    if not kw:
                        continue
                    mem_rows = _q(conn,
                        "SELECT content FROM semantic_memory "
                        "WHERE content LIKE ? LIMIT 2",
                        (f"%{kw.split()[0]}%",))
                    for mr in mem_rows:
                        snippet = str(mr['content'] or '')[:120]
                        if snippet and snippet not in memory_hits:
                            memory_hits.append(snippet)
                if memory_hits:
                    lines = ["## Memory Connections"]
                    for h in memory_hits[:6]:
                        lines.append(f"- {h}")
                    context_parts.append("\n".join(lines))
                    sources_used.append(f"memory:{len(memory_hits)}")
        except Exception:
            pass

        conn.close()
    except Exception:
        pass

    return {
        "date": today,
        "context": "\n\n".join(context_parts) if context_parts else "",
        "sources": ", ".join(sources_used),
    }


def assemble_catchup_context(db_path, since_iso: str, previous_brief: str = "") -> dict:
    """Assemble catch-up briefing context — dynamic window from since_iso to now.

    Same return shape: {date, context, sources}.
    Adds a '## Previous Brief (for contrast)' section with truncated prior brief.
    """
    import sqlite3 as _sqlite3
    import json as _json
    import yaml as _yaml

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    d14_fallback = (now - datetime.timedelta(days=14)).isoformat()

    # Use since_iso as the window start, or 14 days if not provided
    window_start = since_iso if since_iso else d14_fallback

    sources_used: list[str] = []
    context_parts: list[str] = []

    def _q(conn, sql, params=()):
        try:
            return conn.execute(sql, params).fetchall()
        except Exception:
            return []

    # Researcher profile
    try:
        rc_root = paths.root
        cfg_path = rc_root / "system" / "config" / "user-config.yaml"
        prefs_path = rc_root / "system" / "config" / "user-preferences.json"
        researcher_name = "Researcher"
        research_field = ""
        monitored_topics: list[str] = []
        if cfg_path.exists():
            cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            researcher_name = cfg.get("user", {}).get("name", "Researcher") or "Researcher"
            research_field = cfg.get("research", {}).get("field", "")
        if prefs_path.exists():
            prefs = _json.loads(prefs_path.read_text(encoding="utf-8"))
            monitored_topics = prefs.get("news_topics", [])
        if research_field or monitored_topics:
            header_parts = []
            if research_field:
                header_parts.append(f"Researcher field: {research_field}")
            if monitored_topics:
                header_parts.append(f"Monitoring topics: {', '.join(monitored_topics[:8])}")
            context_parts.append("## Researcher Profile\n" + "\n".join(header_parts))
    except Exception:
        pass

    # Previous brief for contrast
    if previous_brief:
        context_parts.append(
            "## Previous Brief (for contrast)\n"
            + previous_brief[:600]
        )

    try:
        conn = _sqlite3.connect(str(db_path))
        conn.row_factory = _sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")

        d1 = (now - datetime.timedelta(days=1)).isoformat()
        _order = (
            "ORDER BY CASE WHEN created_at >= ? THEN 0 ELSE 1 END, "
            "CASE WHEN signal_strength='high' THEN 1 WHEN signal_strength='medium' THEN 2 ELSE 3 END, "
            "created_at DESC"
        )

        # Catch-up is where read-state earns its keep: "what you missed" is not
        # "what arrived in this window" but "what never reached you in a brief you
        # read". A generated-but-unread brief delivered nothing, so its threads
        # are still missed news. That distinction is impossible with a plain
        # time window and is the whole point of the thread layer here.
        news_section = ""
        news_threads_n = 0
        try:
            from metis_mcp.tools import news_threads as _nt
            _threads = _nt.thread_window(conn, window_start)
            if _threads:
                news_section = _nt.render_catchup_section(_threads)
                news_threads_n = len(_threads)
        except Exception:
            news_section = ""

        lit_items = _q(conn,
            "SELECT title, summary, domain FROM news_briefs "
            "WHERE created_at >= ? AND source_type = 'article' "
            + _order + " LIMIT 12", (window_start, d1))

        if news_section:
            context_parts.append(news_section)
            sources_used.append(f"news_threads:{news_threads_n}")
        if lit_items:
            lines = ["## New Literature Alerts (since last brief)"]
            for r in lit_items:
                lines.append(f"- {r['title']}: {str(r['summary'] or '')[:200]}")
            context_parts.append("\n".join(lines))
            sources_used.append(f"literature_alerts:{len(lit_items)}")
        if not news_section and not lit_items:
            context_parts.append("## Field News\nNo news signals found since last brief.")

        # Papers (dynamic window, limit 10)
        bulk_dates = {
            r["d"] for r in _q(conn,
                "SELECT substr(created_at,1,10) AS d, COUNT(*) AS n FROM literature_metadata "
                "GROUP BY d HAVING n >= 50")
        }
        rows = _q(conn,
            "SELECT title, abstract, year, substr(created_at,1,10) AS add_day "
            "FROM literature_metadata WHERE created_at >= ? "
            "ORDER BY COALESCE(year,0) DESC, created_at DESC LIMIT 40", (window_start,))
        rows = [r for r in rows if r["add_day"] not in bulk_dates][:10]
        if rows:
            lines = ["## Recently Added Papers"]
            for r in rows:
                year = f" ({r['year']})" if r.get("year") else ""
                snippet = str(r["abstract"] or "")[:150]
                lines.append(f"- {r['title']}{year}" + (f": {snippet}" if snippet else ""))
            context_parts.append("\n".join(lines))
            sources_used.append(f"papers:{len(rows)}")

        # Framing context (same as weekly: 5 projects, 10 ideas from 30d)
        d30 = (now - datetime.timedelta(days=30)).isoformat()
        framing_parts: list[str] = []
        rows = _q(conn,
            "SELECT title FROM projects WHERE status='active' "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 5")
        if rows:
            framing_parts.append("Active projects: " + ", ".join(r['title'] for r in rows))
            sources_used.append(f"projects:{len(rows)}")

        rows = _q(conn,
            "SELECT text FROM ideas "
            "WHERE created_at >= ? ORDER BY created_at DESC LIMIT 10", (d30,))
        if rows:
            snippets = [str(r['text'] or '')[:80] for r in rows]
            framing_parts.append("Recent ideas: " + "; ".join(snippets))
            sources_used.append(f"ideas:{len(rows)}")

        if framing_parts:
            context_parts.append(
                "## Framing Context (connect external signals to these if relevant "
                "— do not report on them)\n" + "\n".join(framing_parts)
            )

        # Memory connections (same as weekly)
        try:
            top_titles = _q(conn,
                "SELECT title FROM news_briefs WHERE created_at >= ? "
                "ORDER BY CASE WHEN signal_strength='high' THEN 1 ELSE 2 END, "
                "created_at DESC LIMIT 5", (window_start,))
            if top_titles:
                memory_hits: list[str] = []
                for tt in top_titles:
                    kw = str(tt['title'] or '')[:60]
                    if not kw:
                        continue
                    mem_rows = _q(conn,
                        "SELECT content FROM semantic_memory "
                        "WHERE content LIKE ? LIMIT 2",
                        (f"%{kw.split()[0]}%",))
                    for mr in mem_rows:
                        snippet = str(mr['content'] or '')[:120]
                        if snippet and snippet not in memory_hits:
                            memory_hits.append(snippet)
                if memory_hits:
                    lines = ["## Memory Connections"]
                    for h in memory_hits[:6]:
                        lines.append(f"- {h}")
                    context_parts.append("\n".join(lines))
                    sources_used.append(f"memory:{len(memory_hits)}")
        except Exception:
            pass

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
