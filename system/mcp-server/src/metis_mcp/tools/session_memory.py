"""Conversation memory layer — store and search past session summaries."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from metis_mcp.app_instance import app
from metis_mcp.config import paths


def _db_path() -> Path:
    return Path(paths.db)


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_summaries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT,
            summary     TEXT    NOT NULL,
            key_topics  TEXT,
            decisions   TEXT,
            created_at  TEXT    NOT NULL
        )
    """)
    conn.commit()


@app.tool()
async def save_session_summary(
    summary: str,
    key_topics: list[str] | None = None,
    decisions: list[str] | None = None,
    session_id: str | None = None,
) -> dict:
    """Save a summary of the current session to persistent memory.

    Call this at the end of any substantive session so future sessions can
    recall what was discussed, decided, or built — the core of Metis's
    cross-session continuity. The saved summary is searchable later via
    search_session_memory and surfaces when you resume related work.

    Args:
        summary: A 2–5 sentence, plain-English summary of what happened this
            session. Required.
        key_topics: Optional list of short topic tags for retrieval
            (e.g. ["phase-10", "APScheduler"]).
        decisions: Optional list of key decisions made
            (e.g. ["switched to AGPL-3.0"]).
        session_id: Optional identifier used to group related summaries; if
            omitted, the summary is stored on its own.

    Returns:
        A dict with the saved record's id and a confirmation status.
    """
    try:
        with sqlite3.connect(_db_path()) as conn:
            _ensure_table(conn)
            conn.execute(
                """
                INSERT INTO session_summaries
                    (session_id, summary, key_topics, decisions, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id or "",
                    summary,
                    json.dumps(key_topics or []),
                    json.dumps(decisions or []),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        return {"ok": True, "message": "Session summary saved."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
async def search_session_memory(
    query: str,
    limit: int = 10,
) -> list[dict]:
    """Search past session summaries for a topic or keyword.

    Use this to recall what was discussed in previous sessions — e.g.
    "what did we decide about the installer?" or "when did we build APScheduler?".

    Args:
        query: Keyword or phrase to search for.
        limit: Maximum number of results to return (default 10).
    """
    try:
        with sqlite3.connect(_db_path()) as conn:
            _ensure_table(conn)
            q = f"%{query.lower()}%"
            rows = conn.execute(
                """
                SELECT id, session_id, summary, key_topics, decisions, created_at
                FROM session_summaries
                WHERE lower(summary)    LIKE ?
                   OR lower(key_topics) LIKE ?
                   OR lower(decisions)  LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (q, q, q, limit),
            ).fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "session_id": row[1],
                "summary": row[2],
                "key_topics": json.loads(row[3] or "[]"),
                "decisions": json.loads(row[4] or "[]"),
                "created_at": row[5],
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


@app.tool()
async def commit_session_decisions(
    decisions: list[str],
    summary: str = "",
    key_topics: list[str] | None = None,
    session_id: str | None = None,
) -> dict:
    """Commit key decisions from this session to permanent memory.

    This is the mandatory recording checkpoint — call it at the end of every
    agent-routed session, before delivering the final result to the user.
    Unlike save_session_summary (which accepts any summary), this tool enforces
    that at least one concrete decision is captured, and writes each decision
    separately to episodic_memory for future retrieval.

    Args:
        decisions: 1-5 plain-English decisions made this session. Be specific:
            "Chose logistic regression over mixed model due to data sparsity in
            Zone de Santé X" not "made a modelling decision".
        summary: 1-3 sentence summary of the session context (optional but useful).
        key_topics: Topic tags e.g. ["DHIS2", "domain surveillance", "tracker design"].
        session_id: Optional session identifier.
    """
    if not decisions:
        return {"ok": False, "error": "No decisions provided — pass at least one."}

    now = datetime.now(timezone.utc).isoformat()
    today = now[:10]
    sid = session_id or today
    full_summary = summary or f"Session {today}: {len(decisions)} decision(s) recorded."
    topics_json = json.dumps(key_topics or [])
    decisions_json = json.dumps(decisions)

    stored_summary = False
    stored_episodic = 0

    try:
        with sqlite3.connect(_db_path()) as conn:
            _ensure_table(conn)

            # Ensure episodic_memory table exists (mirrors vector_memory DDL without vec)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT    DEFAULT '',
                    event_type TEXT    DEFAULT 'decision',
                    content    TEXT    NOT NULL,
                    metadata   TEXT    DEFAULT '{}',
                    created_at TEXT    NOT NULL
                )
            """)

            # 1. Write consolidated row to session_summaries
            conn.execute(
                """INSERT INTO session_summaries
                   (session_id, summary, key_topics, decisions, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (sid, full_summary, topics_json, decisions_json, now),
            )
            stored_summary = True

            # 2. Write each decision individually to episodic_memory
            for decision in decisions:
                meta = json.dumps({
                    "session_id": sid,
                    "topics": key_topics or [],
                    "source": "commit_session_decisions",
                })
                conn.execute(
                    """INSERT INTO episodic_memory
                       (session_id, event_type, content, metadata, created_at)
                       VALUES (?, 'decision', ?, ?, ?)""",
                    (sid, decision, meta, now),
                )
                stored_episodic += 1

            conn.commit()

        return {
            "ok": True,
            "summary_saved": stored_summary,
            "decisions_saved": stored_episodic,
            "message": f"{stored_episodic} decision(s) committed to permanent memory.",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
async def list_recent_sessions(limit: int = 20) -> list[dict]:
    """List the most recent session summaries in reverse chronological order.

    Args:
        limit: How many to return (default 20).
    """
    try:
        with sqlite3.connect(_db_path()) as conn:
            _ensure_table(conn)
            rows = conn.execute(
                """
                SELECT id, session_id, summary, key_topics, decisions, created_at
                FROM session_summaries
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            {
                "id": r[0],
                "session_id": r[1],
                "summary": r[2],
                "key_topics": json.loads(r[3] or "[]"),
                "decisions": json.loads(r[4] or "[]"),
                "created_at": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        return [{"error": str(e)}]
