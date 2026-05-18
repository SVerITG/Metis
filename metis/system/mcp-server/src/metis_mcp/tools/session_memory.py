"""Conversation memory layer (Phase M).

Stores end-of-session summaries in episodic_memory (event_type='session_summary')
and exposes semantic search over past sessions.

No new schema needed — reuses vec_episodic + episodic_memory.
Embeddings: nomic-embed-text-v1.5-Q, 768 dims (same as rest of memory stack).
"""

from __future__ import annotations

import datetime
import json
import struct

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect


def _encode_vec(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _age(iso: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso)
        delta = datetime.datetime.now() - dt
        if delta.days >= 7:
            return f"{delta.days // 7}w ago"
        if delta.days >= 1:
            return f"{delta.days}d ago"
        h = delta.seconds // 3600
        return f"{h}h ago" if h >= 1 else "recently"
    except Exception:
        return ""


@app.tool()
async def store_session_summary(
    summary: str,
    key_topics: str = "",
    decisions: str = "",
    agent_slugs: str = "",
    session_id: str = "",
) -> list[TextContent]:
    """Store a summary of the current session in long-term conversation memory.

    Call this at the end of any substantive session so future sessions can
    retrieve what was discussed via search_session_memory().

    Args:
        summary:      2-5 sentence plain-English summary of what was discussed
                      and decided. Include specific feature names, file paths,
                      or decisions — these become the searchable content.
        key_topics:   Comma-separated topics (e.g. "installer, Phase 11, Inno Setup").
        decisions:    Comma-separated key decisions made (e.g. "use mem0, skip dark mode").
        agent_slugs:  Comma-separated agents that ran (e.g. "software-engineer, librarian").
        session_id:   Optional session identifier. Leave blank to auto-generate.
    """
    if not summary.strip():
        return [TextContent(type="text", text="Error: summary cannot be empty.")]

    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    sid = session_id.strip() or f"session-{_now()}"
    metadata = {
        "key_topics": [t.strip() for t in key_topics.split(",") if t.strip()],
        "decisions":  [d.strip() for d in decisions.split(",") if d.strip()],
        "agent_slugs": [a.strip() for a in agent_slugs.split(",") if a.strip()],
        "session_id": sid,
    }

    # Build embeddable content: summary + topics so search hits on either
    embed_text = summary
    if key_topics:
        embed_text += f"\nTopics: {key_topics}"
    if decisions:
        embed_text += f"\nDecisions: {decisions}"

    try:
        from metis_mcp.embeddings import embed_document
        vec = embed_document(embed_text)
        vec_bytes = _encode_vec(vec)
    except ImportError:
        vec_bytes = None

    try:
        with connect(paths.db) as conn:
            # Ensure tables exist
            conn.execute(
                "CREATE TABLE IF NOT EXISTS episodic_memory ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "session_id TEXT DEFAULT '', "
                "event_type TEXT DEFAULT 'note', "
                "content TEXT NOT NULL, "
                "metadata TEXT DEFAULT '{}', "
                "created_at TEXT NOT NULL)"
            )

            cur = conn.execute(
                "INSERT INTO episodic_memory (session_id, event_type, content, metadata, created_at) "
                "VALUES (?, 'session_summary', ?, ?, ?)",
                (sid, summary, json.dumps(metadata), _now()),
            )
            row_id = cur.lastrowid

            # Index in vec_episodic if embeddings available
            if vec_bytes:
                try:
                    import sqlite_vec
                    conn.enable_load_extension(True)
                    sqlite_vec.load(conn)
                    conn.enable_load_extension(False)
                    conn.execute(
                        "CREATE VIRTUAL TABLE IF NOT EXISTS vec_episodic USING vec0(embedding float[768])"
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO vec_episodic (rowid, embedding) VALUES (?, ?)",
                        (row_id, vec_bytes),
                    )
                except Exception:
                    pass  # sqlite-vec unavailable — text search still works

            conn.commit()

    except Exception as e:
        return [TextContent(type="text", text=f"Error storing session summary: {e}")]

    topics_str = f" Topics: {key_topics}." if key_topics else ""
    return [TextContent(
        type="text",
        text=f"Session summary stored (id={row_id}).{topics_str} "
             f"Retrieve with: search_session_memory('<query>')",
    )]


@app.tool()
async def search_session_memory(
    query: str,
    top_k: int = 5,
) -> list[TextContent]:
    """Search past session summaries using semantic similarity.

    Answers questions like:
      - "what did we discuss about the installer?"
      - "when did we decide to use mem0?"
      - "what features were planned for the news rail?"

    Args:
        query: Natural language question about past conversations.
        top_k: Number of sessions to return (default 5).
    """
    if not query.strip():
        return [TextContent(type="text", text="Error: query cannot be empty.")]

    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        from metis_mcp.embeddings import embed_query as _embed_q
        query_vec = _embed_q(query)
        query_bytes = _encode_vec(query_vec)
        has_vec = True
    except ImportError:
        has_vec = False

    results: list[dict] = []

    try:
        with connect(paths.db) as conn:
            if has_vec:
                try:
                    import sqlite_vec
                    conn.enable_load_extension(True)
                    sqlite_vec.load(conn)
                    conn.enable_load_extension(False)

                    vec_rows = conn.execute(
                        """SELECT e.id, e.content, e.metadata, e.created_at, v.distance
                             FROM vec_episodic v
                             JOIN episodic_memory e ON e.id = v.rowid
                            WHERE e.event_type = 'session_summary'
                              AND v.embedding MATCH ?
                              AND k = ?
                            ORDER BY v.distance""",
                        (query_bytes, top_k * 2),
                    ).fetchall()

                    seen = set()
                    for r in vec_rows:
                        if r["id"] not in seen:
                            results.append(dict(r))
                            seen.add(r["id"])
                except Exception:
                    has_vec = False

            if not has_vec or not results:
                # Keyword fallback
                like = f"%{query}%"
                kw_rows = conn.execute(
                    "SELECT id, content, metadata, created_at "
                    "FROM episodic_memory "
                    "WHERE event_type = 'session_summary' AND content LIKE ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (like, top_k),
                ).fetchall()
                for r in kw_rows:
                    results.append(dict(r))

    except Exception as e:
        return [TextContent(type="text", text=f"Search error: {e}")]

    if not results:
        return [TextContent(
            type="text",
            text="No matching session summaries found. "
                 "Store summaries using store_session_summary() at the end of sessions.",
        )]

    lines = [f"Found {len(results[:top_k])} session(s) matching '{query}':\n"]
    for i, r in enumerate(results[:top_k], 1):
        age = _age(r.get("created_at", ""))
        meta: dict = {}
        try:
            meta = json.loads(r.get("metadata") or "{}")
        except Exception:
            pass
        topics = ", ".join(meta.get("key_topics", [])) or "—"
        decisions = "; ".join(meta.get("decisions", [])) or "—"
        score = f"  distance={r['distance']:.4f}" if "distance" in r else ""
        lines.append(
            f"{i}. [{age}]{score}\n"
            f"   Summary: {r['content']}\n"
            f"   Topics: {topics}\n"
            f"   Decisions: {decisions}"
        )

    return [TextContent(type="text", text="\n\n".join(lines))]


@app.tool()
async def list_recent_sessions(limit: int = 10) -> list[TextContent]:
    """List the most recent stored session summaries.

    Args:
        limit: Number of sessions to return (default 10).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            rows = conn.execute(
                "SELECT id, content, metadata, created_at "
                "FROM episodic_memory "
                "WHERE event_type = 'session_summary' "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]

    if not rows:
        return [TextContent(
            type="text",
            text="No session summaries stored yet. Use store_session_summary() at session end.",
        )]

    lines = [f"{len(rows)} most recent session summaries:\n"]
    for r in rows:
        age = _age(r["created_at"])
        meta: dict = {}
        try:
            meta = json.loads(r.get("metadata") or "{}")
        except Exception:
            pass
        topics = ", ".join(meta.get("key_topics", [])) or "—"
        preview = r["content"][:120] + ("…" if len(r["content"]) > 120 else "")
        lines.append(f"[{age}] Topics: {topics}\n  {preview}")

    return [TextContent(type="text", text="\n\n".join(lines))]
