"""Multi-layered vector memory for Metis (Phase 5, M5.1–M5.8).

Five memory layers:
  episodic   — raw events (ideas, notes, papers, agent runs)
  semantic   — distilled concepts and knowledge nodes
  procedural — successful workflows and how-to patterns
  working    — ephemeral per-session scratchpad (key/value)
  reflexive  — alias to reflexion_log (agent self-critiques)

Retrieval uses Reciprocal Rank Fusion (RRF) to merge vector similarity
and keyword matches.

Requires: sqlite-vec (M5.1) and fastembed (M5.2).
Vector dimension: 768 (nomic-ai/nomic-embed-text-v1.5-Q).
"""

from __future__ import annotations

import datetime
import json
import struct
from typing import List

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

# ── Schema DDL ────────────────────────────────────────────────────────────────

_EPISODIC_DDL = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT DEFAULT '',
    event_type  TEXT DEFAULT 'note',
    content     TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL,
    agent_id    TEXT DEFAULT '',
    project_id  TEXT DEFAULT '',
    scope       TEXT DEFAULT 'global'
)
"""

_SEMANTIC_DDL = """
CREATE TABLE IF NOT EXISTS semantic_memory (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    concept          TEXT NOT NULL,
    definition       TEXT NOT NULL,
    related_concepts TEXT DEFAULT '',
    source_type      TEXT DEFAULT 'user_defined',
    source_id        TEXT DEFAULT '',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    agent_id         TEXT DEFAULT '',
    project_id       TEXT DEFAULT '',
    scope            TEXT DEFAULT 'global'
)
"""

_PROCEDURAL_DDL = """
CREATE TABLE IF NOT EXISTS procedural_memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_name  TEXT NOT NULL,
    trigger_context TEXT DEFAULT '',
    steps           TEXT NOT NULL,
    success_count   INTEGER DEFAULT 1,
    last_used       TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    agent_id        TEXT DEFAULT '',
    project_id      TEXT DEFAULT '',
    scope           TEXT DEFAULT 'global'
)
"""

_WORKING_DDL = """
CREATE TABLE IF NOT EXISTS working_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    created_at  TEXT NOT NULL
)
"""

_VEC_EPISODIC_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_episodic USING vec0(
    embedding float[768]
)
"""

_VEC_SEMANTIC_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_semantic USING vec0(
    embedding float[768]
)
"""

_VEC_PROCEDURAL_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_procedural USING vec0(
    embedding float[768]
)
"""


def _migrate_vec_table(conn, table: str, ddl: str) -> None:
    """Drop and recreate a vec0 table if its embedding dimension has changed.

    Probes by attempting a test insert with the current EMBEDDING_DIM.
    Safe because vec0 tables are rebuilt from source tables when needed.
    """
    from metis_mcp.embeddings import EMBEDDING_DIM
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not row:
        return  # doesn't exist yet — CREATE IF NOT EXISTS will handle it
    test_bytes = struct.pack(f"{EMBEDDING_DIM}f", *([0.0] * EMBEDDING_DIM))
    try:
        conn.execute(f"INSERT INTO {table} (rowid, embedding) VALUES (-9999, ?)", (test_bytes,))
        conn.execute(f"DELETE FROM {table} WHERE rowid = -9999")
    except Exception:
        # Dimension mismatch — drop and recreate with correct dim
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(ddl)


_SCOPE_MIGRATIONS = [
    "ALTER TABLE episodic_memory ADD COLUMN agent_id TEXT DEFAULT ''",
    "ALTER TABLE episodic_memory ADD COLUMN project_id TEXT DEFAULT ''",
    "ALTER TABLE episodic_memory ADD COLUMN scope TEXT DEFAULT 'global'",
    "ALTER TABLE semantic_memory ADD COLUMN agent_id TEXT DEFAULT ''",
    "ALTER TABLE semantic_memory ADD COLUMN project_id TEXT DEFAULT ''",
    "ALTER TABLE semantic_memory ADD COLUMN scope TEXT DEFAULT 'global'",
    "ALTER TABLE procedural_memory ADD COLUMN agent_id TEXT DEFAULT ''",
    "ALTER TABLE procedural_memory ADD COLUMN project_id TEXT DEFAULT ''",
    "ALTER TABLE procedural_memory ADD COLUMN scope TEXT DEFAULT 'global'",
]


def _setup_tables(conn) -> None:
    """Ensure all memory tables and vec0 virtual tables exist."""
    import sqlite_vec
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    conn.execute(_EPISODIC_DDL)
    conn.execute(_SEMANTIC_DDL)
    conn.execute(_PROCEDURAL_DDL)
    conn.execute(_WORKING_DDL)

    # Migrate: add scope columns to existing tables
    for stmt in _SCOPE_MIGRATIONS:
        try:
            conn.execute(stmt)
        except Exception:
            pass  # Column already exists

    # Migrate vec0 tables if dimension changed (e.g. 384→768 upgrade)
    _migrate_vec_table(conn, "vec_episodic", _VEC_EPISODIC_DDL)
    _migrate_vec_table(conn, "vec_semantic", _VEC_SEMANTIC_DDL)
    _migrate_vec_table(conn, "vec_procedural", _VEC_PROCEDURAL_DDL)

    conn.execute(_VEC_EPISODIC_DDL)
    conn.execute(_VEC_SEMANTIC_DDL)
    conn.execute(_VEC_PROCEDURAL_DDL)
    conn.commit()


def _encode_vec(vector: List[float]) -> bytes:
    """Pack a float list to sqlite-vec binary format."""
    return struct.pack(f"{len(vector)}f", *vector)


# ── Episodic memory ───────────────────────────────────────────────────────────

@app.tool()
async def store_episodic_memory(
    content: str,
    event_type: str = "note",
    session_id: str = "",
    metadata: str = "{}",
) -> list[TextContent]:
    """Store an event in episodic memory and index it for vector search.

    Logs a time-stamped EVENT (something that happened) and indexes it for vector
    search. For a distilled, timeless concept/definition use store_semantic_memory;
    for a human-curated palace note use add_memory_entry.

    Episodic memory is a chronological log of things that happened — ideas,
    notes, papers read, tasks completed, agent runs.

    Args:
        content: The text content of the event to remember.
        event_type: One of 'idea', 'note', 'task', 'paper', 'meeting', or
            'agent_run'.
        session_id: Current pipeline session ID (optional).
        metadata: JSON string with extra fields such as title, tags, or source.

    Returns:
        A single TextContent confirming the stored event (its row id and type),
        or an error message if the database is missing, fastembed is not
        installed, or the write fails.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        from metis_mcp.embeddings import embed_document
        vector = embed_document(content)
    except ImportError:
        return [TextContent(type="text", text="fastembed not installed. Run: pip install fastembed")]

    try:
        with connect(paths.db) as conn:
            _setup_tables(conn)

            cur = conn.execute(
                """INSERT INTO episodic_memory (session_id, event_type, content, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, event_type, content, metadata, now),
            )
            row_id = cur.lastrowid

            conn.execute(
                "INSERT INTO vec_episodic (rowid, embedding) VALUES (?, ?)",
                (row_id, _encode_vec(vector)),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Episodic memory stored (id={row_id}, type={event_type}).")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error storing episodic memory: {e}")]


# ── Semantic memory ───────────────────────────────────────────────────────────

@app.tool()
async def store_semantic_memory(
    concept: str,
    definition: str,
    related_concepts: str = "",
    source_type: str = "user_defined",
    source_id: str = "",
) -> list[TextContent]:
    """Store a distilled knowledge node in semantic memory.

    Stores a distilled CONCEPT/definition (timeless 'what I know'). For a
    time-stamped event use store_episodic_memory; for a human-curated palace
    note use add_memory_entry.

    Semantic memory holds the 'what I know' layer — concepts, definitions,
    and their relationships. Used by retrieval to surface relevant knowledge
    without relying on raw event history.

    Args:
        concept: Short name for the concept, e.g. 'RDT sensitivity' or
            'fAChE inhibition'.
        definition: A one-to-three-sentence definition or explanation.
        related_concepts: Comma-separated names of related concepts.
        source_type: Where this came from: 'paper', 'note', 'idea', or
            'user_defined'.
        source_id: ID of the source record, e.g. a paper DOI or idea_id.

    Returns:
        A single TextContent confirming the stored node (its row id and concept
        name), or an error message if the database is missing, fastembed is not
        installed, or the write fails.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    embed_text = f"{concept}: {definition}"

    try:
        from metis_mcp.embeddings import embed_document
        vector = embed_document(embed_text)
    except ImportError:
        return [TextContent(type="text", text="fastembed not installed.")]

    try:
        with connect(paths.db) as conn:
            _setup_tables(conn)

            cur = conn.execute(
                """INSERT INTO semantic_memory
                   (concept, definition, related_concepts, source_type, source_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (concept, definition, related_concepts, source_type, source_id, now, now),
            )
            row_id = cur.lastrowid

            conn.execute(
                "INSERT INTO vec_semantic (rowid, embedding) VALUES (?, ?)",
                (row_id, _encode_vec(vector)),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Semantic memory stored (id={row_id}, concept='{concept}').")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error storing semantic memory: {e}")]


# ── Procedural memory ─────────────────────────────────────────────────────────

@app.tool()
async def store_procedural_memory(
    procedure_name: str,
    steps: str,
    trigger_context: str = "",
) -> list[TextContent]:
    """Store a successful workflow pattern in procedural memory.

    Procedural memory captures 'how to do things' — repeatable processes,
    workflows that worked well, or step-by-step patterns for recurring tasks.

    Args:
        procedure_name: Short name for this procedure (e.g. 'Domain literature search').
        steps: Markdown-formatted steps for the procedure.
        trigger_context: What situation should trigger using this procedure.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    embed_text = f"{procedure_name}. {trigger_context}. {steps[:500]}"

    try:
        from metis_mcp.embeddings import embed_document
        vector = embed_document(embed_text)
    except ImportError:
        return [TextContent(type="text", text="fastembed not installed.")]

    try:
        with connect(paths.db) as conn:
            _setup_tables(conn)

            cur = conn.execute(
                """INSERT INTO procedural_memory
                   (procedure_name, trigger_context, steps, last_used, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (procedure_name, trigger_context, steps, now, now),
            )
            row_id = cur.lastrowid

            conn.execute(
                "INSERT INTO vec_procedural (rowid, embedding) VALUES (?, ?)",
                (row_id, _encode_vec(vector)),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Procedural memory stored (id={row_id}, name='{procedure_name}').")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error storing procedural memory: {e}")]


# ── Working memory ────────────────────────────────────────────────────────────

@app.tool()
async def set_working_memory(
    session_id: str,
    key: str,
    value: str,
) -> list[TextContent]:
    """Write a key/value pair to the current session's working memory.

    Working memory is an ephemeral scratchpad — it persists for the session
    but is not indexed for vector search. Use it for state that agents need
    mid-pipeline (e.g. intermediate results, decisions made so far).

    Args:
        session_id: Pipeline session ID from session_bootstrap().
        key: Variable name (e.g. 'current_article', 'user_intent').
        value: Value to store (any string, JSON, or text).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as conn:
            conn.execute(_WORKING_DDL)
            # Upsert: replace existing key for this session
            conn.execute(
                """INSERT OR REPLACE INTO working_memory (session_id, key, value, created_at)
                   VALUES (?, ?, ?, ?)""",
                (session_id, key, value, now),
            )
            conn.commit()
        return [TextContent(type="text", text=f"Working memory set: {key} = {value[:80]}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error setting working memory: {e}")]


@app.tool()
async def get_working_memory(session_id: str = "") -> list[TextContent]:
    """Retrieve working memory for a session, or the most recent entries if no session given.

    Args:
        session_id: Pipeline session ID. Leave empty to get the 20 most recent entries
                    across all sessions.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_WORKING_DDL)
            if session_id:
                rows = conn.execute(
                    "SELECT session_id, key, value FROM working_memory "
                    "WHERE session_id = ? ORDER BY created_at",
                    (session_id,),
                ).fetchall()
                label = f"session {session_id[:8]}…"
            else:
                rows = conn.execute(
                    "SELECT session_id, key, value FROM working_memory "
                    "ORDER BY created_at DESC LIMIT 20",
                ).fetchall()
                label = "recent sessions"

        if not rows:
            return [TextContent(type="text", text=f"No working memory found ({label}).")]

        lines = [f"Working memory ({label}):\n"]
        for row in rows:
            prefix = f"[{row['session_id'][:8]}] " if not session_id else ""
            lines.append(f"- {prefix}**{row['key']}**: {row['value'][:200]}")
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error reading working memory: {e}")]


# ── Backfill / reindex missing vectors ────────────────────────────────────────

@app.tool()
async def reindex_memory(
    layers: str = "episodic,semantic,procedural",
    batch_size: int = 50,
) -> list[TextContent]:
    """Re-embed memory entries that are missing vector indexes.

    Scans each requested layer for rows without a corresponding vector in the
    vec_* table, generates embeddings, and inserts them. Safe to run repeatedly
    — only processes gaps, never overwrites existing vectors.

    Use this to recover from embedding failures, or after importing memories
    via raw SQL. Can be scheduled nightly via APScheduler.

    Args:
        layers: Comma-separated layers to reindex: 'episodic', 'semantic',
            'procedural' (default: all three).
        batch_size: How many entries to embed per batch (default 50).
            Lower values use less memory; higher values are faster.

    Returns:
        Summary of how many entries were reindexed per layer.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    requested = {l.strip() for l in layers.split(",") if l.strip()}

    try:
        from metis_mcp.embeddings import embed_document
    except ImportError:
        return [TextContent(type="text", text="fastembed not installed — cannot reindex.")]

    stats: dict[str, dict] = {}

    try:
        with connect(paths.db) as conn:
            _setup_tables(conn)

            if "episodic" in requested:
                missing = conn.execute(
                    """SELECT e.id, e.content FROM episodic_memory e
                       WHERE e.id NOT IN (SELECT rowid FROM vec_episodic)
                       ORDER BY e.id"""
                ).fetchall()
                embedded = 0
                for row in missing:
                    try:
                        vec = embed_document(row["content"][:2000])
                        conn.execute(
                            "INSERT INTO vec_episodic (rowid, embedding) VALUES (?, ?)",
                            (row["id"], _encode_vec(vec)),
                        )
                        embedded += 1
                        if embedded % batch_size == 0:
                            conn.commit()
                    except Exception:
                        pass
                conn.commit()
                stats["episodic"] = {"missing": len(missing), "embedded": embedded}

            if "semantic" in requested:
                missing = conn.execute(
                    """SELECT s.id, s.concept, s.definition FROM semantic_memory s
                       WHERE s.id NOT IN (SELECT rowid FROM vec_semantic)
                       ORDER BY s.id"""
                ).fetchall()
                embedded = 0
                for row in missing:
                    try:
                        text = f"{row['concept']}: {row['definition']}"
                        vec = embed_document(text[:2000])
                        conn.execute(
                            "INSERT INTO vec_semantic (rowid, embedding) VALUES (?, ?)",
                            (row["id"], _encode_vec(vec)),
                        )
                        embedded += 1
                        if embedded % batch_size == 0:
                            conn.commit()
                    except Exception:
                        pass
                conn.commit()
                stats["semantic"] = {"missing": len(missing), "embedded": embedded}

            if "procedural" in requested:
                missing = conn.execute(
                    """SELECT p.id, p.procedure_name, p.trigger_context, p.steps
                       FROM procedural_memory p
                       WHERE p.id NOT IN (SELECT rowid FROM vec_procedural)
                       ORDER BY p.id"""
                ).fetchall()
                embedded = 0
                for row in missing:
                    try:
                        text = f"{row['procedure_name']}. {row['trigger_context']}. {row['steps'][:500]}"
                        vec = embed_document(text[:2000])
                        conn.execute(
                            "INSERT INTO vec_procedural (rowid, embedding) VALUES (?, ?)",
                            (row["id"], _encode_vec(vec)),
                        )
                        embedded += 1
                        if embedded % batch_size == 0:
                            conn.commit()
                    except Exception:
                        pass
                conn.commit()
                stats["procedural"] = {"missing": len(missing), "embedded": embedded}

    except Exception as e:
        return [TextContent(type="text", text=f"Error during reindex: {e}")]

    lines = ["**Memory reindex complete:**\n"]
    total_missing = 0
    total_embedded = 0
    for layer, s in stats.items():
        lines.append(f"- **{layer}**: {s['embedded']}/{s['missing']} entries embedded")
        total_missing += s["missing"]
        total_embedded += s["embedded"]
    lines.append(f"\nTotal: {total_embedded}/{total_missing} gaps filled.")
    return [TextContent(type="text", text="\n".join(lines))]


# ── Unified semantic search (M5.8 — RRF retrieval) ───────────────────────────

@app.tool()
async def semantic_search(
    query: str,
    layers: str = "episodic,semantic,procedural",
    top_k: int = 5,
) -> list[TextContent]:
    """Search across memory layers using vector similarity + keyword RRF fusion.

    Searches your personal MEMORY layers (episodic/semantic/procedural — things
    you or Metis recorded), NOT your document library. For documents/PDFs use
    search_pdf_knowledge; for reference metadata use search_library.

    Retrieval pipeline (M5.8):
    1. Embed the query.
    2. Run vector similarity search on each requested layer.
    3. Run keyword LIKE search on each layer.
    4. Fuse results using Reciprocal Rank Fusion (RRF, k=60).
    5. Return top_k deduplicated results ranked by fused score.

    Args:
        query: Natural language search query to embed and keyword-match.
        layers: Comma-separated memory layers to search, drawn from 'episodic',
            'semantic', and 'procedural'.
        top_k: Number of fused results to return (default 5).

    Returns:
        A single TextContent listing the top fused results (layer, title, score,
        timestamp, and a content preview), or a "no results" / error message.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    requested = {l.strip() for l in layers.split(",") if l.strip()}

    try:
        from metis_mcp.embeddings import embed_query
        query_vec = embed_query(query)
    except ImportError:
        return [TextContent(type="text", text="fastembed not installed. Run: pip install fastembed")]

    results = []  # list of (score, layer, content_preview, id)
    RRF_K = 60

    def rrf_score(rank: int) -> float:
        return 1.0 / (RRF_K + rank)

    try:
        with connect(paths.db) as conn:
            import sqlite_vec
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            _setup_tables(conn)
            vec_bytes = _encode_vec(query_vec)
            like = f"%{query}%"

            if "episodic" in requested:
                # Vector search
                vec_rows = conn.execute(
                    """SELECT e.id, e.event_type, e.content, e.created_at,
                              distance
                         FROM vec_episodic v
                         JOIN episodic_memory e ON e.id = v.rowid
                        WHERE embedding MATCH ?
                          AND k = ?
                        ORDER BY distance""",
                    (vec_bytes, top_k * 2),
                ).fetchall()

                # Keyword search
                kw_rows = conn.execute(
                    """SELECT id, event_type, content, created_at
                         FROM episodic_memory
                        WHERE content LIKE ?
                        ORDER BY created_at DESC
                        LIMIT ?""",
                    (like, top_k * 2),
                ).fetchall()

                # Build RRF combined scores
                vec_ids = {r["id"]: rank + 1 for rank, r in enumerate(vec_rows)}
                kw_ids = {r["id"]: rank + 1 for rank, r in enumerate(kw_rows)}
                all_ids = set(vec_ids) | set(kw_ids)

                row_map = {r["id"]: r for r in vec_rows}
                row_map.update({r["id"]: r for r in kw_rows})

                for rid in all_ids:
                    score = rrf_score(vec_ids.get(rid, top_k * 4)) + rrf_score(kw_ids.get(rid, top_k * 4))
                    r = row_map[rid]
                    results.append((score, "episodic", r["event_type"], r["content"][:300], r["created_at"]))

            if "semantic" in requested:
                vec_rows = conn.execute(
                    """SELECT s.id, s.concept, s.definition, s.created_at,
                              distance
                         FROM vec_semantic v
                         JOIN semantic_memory s ON s.id = v.rowid
                        WHERE embedding MATCH ?
                          AND k = ?
                        ORDER BY distance""",
                    (vec_bytes, top_k * 2),
                ).fetchall()

                kw_rows = conn.execute(
                    """SELECT id, concept, definition, created_at
                         FROM semantic_memory
                        WHERE concept LIKE ? OR definition LIKE ?
                        ORDER BY updated_at DESC LIMIT ?""",
                    (like, like, top_k * 2),
                ).fetchall()

                vec_ids = {r["id"]: rank + 1 for rank, r in enumerate(vec_rows)}
                kw_ids = {r["id"]: rank + 1 for rank, r in enumerate(kw_rows)}
                all_ids = set(vec_ids) | set(kw_ids)
                row_map = {r["id"]: r for r in vec_rows}
                row_map.update({r["id"]: r for r in kw_rows})

                for rid in all_ids:
                    score = rrf_score(vec_ids.get(rid, top_k * 4)) + rrf_score(kw_ids.get(rid, top_k * 4))
                    r = row_map[rid]
                    results.append((score, "semantic", r["concept"], r["definition"][:300], r["created_at"]))

            if "procedural" in requested:
                vec_rows = conn.execute(
                    """SELECT p.id, p.procedure_name, p.steps, p.trigger_context, p.last_used,
                              distance
                         FROM vec_procedural v
                         JOIN procedural_memory p ON p.id = v.rowid
                        WHERE embedding MATCH ?
                          AND k = ?
                        ORDER BY distance""",
                    (vec_bytes, top_k * 2),
                ).fetchall()

                kw_rows = conn.execute(
                    """SELECT id, procedure_name, steps, trigger_context, last_used
                         FROM procedural_memory
                        WHERE procedure_name LIKE ? OR trigger_context LIKE ? OR steps LIKE ?
                        ORDER BY last_used DESC LIMIT ?""",
                    (like, like, like, top_k * 2),
                ).fetchall()

                vec_ids = {r["id"]: rank + 1 for rank, r in enumerate(vec_rows)}
                kw_ids = {r["id"]: rank + 1 for rank, r in enumerate(kw_rows)}
                all_ids = set(vec_ids) | set(kw_ids)
                row_map = {r["id"]: r for r in vec_rows}
                row_map.update({r["id"]: r for r in kw_rows})

                for rid in all_ids:
                    score = rrf_score(vec_ids.get(rid, top_k * 4)) + rrf_score(kw_ids.get(rid, top_k * 4))
                    r = row_map[rid]
                    results.append((score, "procedural", r["procedure_name"], r["steps"][:300], r["last_used"]))

    except Exception as e:
        return [TextContent(type="text", text=f"Error during semantic search: {e}")]

    # Sort by RRF score descending, take top_k
    results.sort(key=lambda x: x[0], reverse=True)
    top = results[:top_k]

    if not top:
        return [TextContent(type="text", text=f"No results found for '{query}' in layers: {layers}.")]

    lines = [f"**Top {len(top)} results for '{query}'** (layers: {layers}):\n"]
    for i, (score, layer, title, preview, ts) in enumerate(top, 1):
        lines.append(f"### {i}. [{layer}] {title}")
        lines.append(f"*Score: {score:.4f} | {ts[:10]}*")
        lines.append(preview)
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]
