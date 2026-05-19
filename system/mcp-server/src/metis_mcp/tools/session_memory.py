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
    recall what was discussed, decided, or built.

    Args:
        summary: 2–5 sentence plain-English summary of what happened.
        key_topics: Optional list of topic tags (e.g. ["phase-10", "APScheduler"]).
        decisions: Optional list of key decisions made (e.g. ["switched to AGPL-3.0"]).
        session_id: Optional session identifier for grouping.
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
