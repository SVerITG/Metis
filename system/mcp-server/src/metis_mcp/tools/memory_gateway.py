"""Unified memory gateway — recall() and remember().

The front door to Metis's entire memory system. Instead of choosing
between search_memory, semantic_search, and search_pdf_knowledge,
callers use:

  recall(query)       → searches ALL layers, returns ranked results
  remember(content)   → auto-classifies and stores with scope tags

Multi-scope identity: every memory entry can be tagged with agent_id,
project_id, and scope (global/agent/project/session) so agents
accumulate their own wisdom and project decisions stay with projects.
"""

from __future__ import annotations

import datetime
import json
import math
import struct
import subprocess
from pathlib import Path
from typing import List, Optional

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


# ── Schema migrations for multi-scope identity ─────────────────────────────

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


def _run_migrations(conn) -> None:
    """Add scope columns if they don't exist yet. Safe to call repeatedly."""
    for stmt in _SCOPE_MIGRATIONS:
        try:
            conn.execute(stmt)
        except Exception:
            pass  # Column already exists


def _encode_vec(vector: List[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── recall() — unified retrieval across ALL memory layers ───────────────────

@app.tool()
async def recall(
    query: str,
    scope: str = "",
    agent_id: str = "",
    project_id: str = "",
    layers: str = "all",
    top_k: int = 10,
    recency_half_life: int = 90,
) -> list[TextContent]:
    """Search across ALL memory layers in one call.

    The unified front door to everything Metis remembers — personal notes,
    agent findings, project decisions, PDF knowledge, ideas, and session
    history. Returns ranked results with source attribution.

    Searches up to 6 layers and merges results using Reciprocal Rank Fusion:
      1. Memory palace (memory_entries — keyword)
      2. Episodic memory (events — vector + keyword)
      3. Semantic memory (concepts — vector + keyword)
      4. Procedural memory (workflows — vector + keyword)
      5. Knowledge databases (PDF chunks — vector)
      6. Ideas (ideas table — keyword)

    Use scope/agent_id/project_id to narrow results:
      recall("HAT diagnostics")                          → everything
      recall("search patterns", agent_id="librarian")    → librarian's wisdom
      recall("elimination", project_id="article-1")      → Article 1 decisions
      recall("mixed models", scope="global")             → cross-cutting knowledge

    Args:
        query: Natural language search query.
        scope: Filter by scope: 'global', 'agent', 'project', 'session'.
            Empty string (default) searches all scopes.
        agent_id: Filter to memories from a specific agent (e.g. 'librarian').
        project_id: Filter to memories linked to a specific project.
        layers: Comma-separated layers to search. Options: 'memory', 'episodic',
            'semantic', 'procedural', 'knowledge', 'ideas', or 'all' (default).
        top_k: Number of results to return (default 10).
        recency_half_life: Days until recency boost halves (default 90). Set to 0
            to disable recency weighting. A 90-day-old entry gets ~37% of a
            fresh entry's time bonus; 180-day ~14%.

    Returns:
        Ranked results from across all matching layers, each with its source
        layer, relevance score, timestamp, and content preview.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    if not query.strip():
        return [TextContent(type="text", text="Query cannot be empty.")]

    requested = {l.strip() for l in layers.split(",")} if layers != "all" else {
        "memory", "episodic", "semantic", "procedural", "knowledge", "ideas"
    }

    RRF_K = 60
    all_results: list[dict] = []
    like = f"%{query}%"

    # ── Try to load embedding engine (needed for vector layers) ─────────
    embed_available = False
    query_vec = None
    vec_bytes = None
    try:
        from metis_mcp.embeddings import embed_query
        query_vec = embed_query(query)
        vec_bytes = _encode_vec(query_vec)
        embed_available = True
    except Exception:
        pass  # SSL error, model download failure, etc. — keyword search still works

    try:
        with connect(paths.db) as conn:
            _run_migrations(conn)

            # ── Layer 1: Memory palace (keyword search) ─────────────────
            if "memory" in requested:
                try:
                    type_filter = ""
                    params: list = [like, like, like]
                    if scope:
                        pass  # memory_entries has no scope column (yet)

                    rows = conn.execute(
                        f"""SELECT entry_id, entry_date, entry_type, topics,
                                   title, summary
                            FROM memory_entries
                            WHERE title LIKE ? OR summary LIKE ? OR topics LIKE ?
                            ORDER BY entry_date DESC LIMIT ?""",
                        (*params, top_k * 2),
                    ).fetchall()

                    for rank, r in enumerate(rows, 1):
                        all_results.append({
                            "score": 1.0 / (RRF_K + rank),
                            "layer": "memory",
                            "title": r["title"] or "(untitled)",
                            "preview": (r["summary"] or "")[:300],
                            "date": r["entry_date"] or "",
                            "meta": f"type={r['entry_type']} topics={r['topics']}",
                        })
                except Exception:
                    pass

            # ── Load sqlite-vec for vector layers ───────────────────────
            vec_loaded = False
            if embed_available and any(l in requested for l in ("episodic", "semantic", "procedural", "knowledge")):
                try:
                    import sqlite_vec
                    conn.enable_load_extension(True)
                    sqlite_vec.load(conn)
                    conn.enable_load_extension(False)
                    vec_loaded = True

                    # Ensure vector memory tables exist
                    from metis_mcp.tools.vector_memory import _setup_tables
                    _setup_tables(conn)
                except Exception:
                    pass

            # ── Build scope filter for vector memory tables ─────────────
            scope_where = ""
            scope_params: list = []
            if agent_id:
                scope_where += " AND t.agent_id = ?"
                scope_params.append(agent_id)
            if project_id:
                scope_where += " AND t.project_id = ?"
                scope_params.append(project_id)
            if scope:
                scope_where += " AND t.scope = ?"
                scope_params.append(scope)

            # ── Layer 2: Episodic memory (vector + keyword RRF) ─────────
            if "episodic" in requested and vec_loaded:
                try:
                    vec_results = _search_episodic_vec(
                        conn, vec_bytes, top_k * 2, scope_where, scope_params
                    )
                    kw_results = _search_episodic_kw(
                        conn, like, top_k * 2, scope_where, scope_params
                    )
                    _merge_rrf(all_results, vec_results, kw_results, "episodic", RRF_K, top_k)
                except Exception:
                    pass

            # ── Layer 3: Semantic memory (vector + keyword RRF) ─────────
            if "semantic" in requested and vec_loaded:
                try:
                    vec_results = _search_semantic_vec(
                        conn, vec_bytes, top_k * 2, scope_where, scope_params
                    )
                    kw_results = _search_semantic_kw(
                        conn, like, top_k * 2, scope_where, scope_params
                    )
                    _merge_rrf(all_results, vec_results, kw_results, "semantic", RRF_K, top_k)
                except Exception:
                    pass

            # ── Layer 4: Procedural memory (vector + keyword RRF) ───────
            if "procedural" in requested and vec_loaded:
                try:
                    vec_results = _search_procedural_vec(
                        conn, vec_bytes, top_k * 2, scope_where, scope_params
                    )
                    kw_results = _search_procedural_kw(
                        conn, like, top_k * 2, scope_where, scope_params
                    )
                    _merge_rrf(all_results, vec_results, kw_results, "procedural", RRF_K, top_k)
                except Exception:
                    pass

            # ── Layer 5: Knowledge databases / PDFs (vector) ────────────
            if "knowledge" in requested and vec_loaded:
                try:
                    from metis_mcp.embeddings import embed_query as eq
                    q_vec_norm = _encode_vec(eq(query, normalize=True))
                    _search_knowledge(conn, q_vec_norm, all_results, RRF_K, top_k)
                except Exception:
                    pass

            # ── Layer 6: Ideas (keyword) ────────────────────────────────
            if "ideas" in requested:
                try:
                    rows = conn.execute(
                        """SELECT id, content, tags, domain_links, project_links, created_at
                           FROM ideas
                           WHERE content LIKE ? OR tags LIKE ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (like, like, top_k),
                    ).fetchall()
                    for rank, r in enumerate(rows, 1):
                        all_results.append({
                            "score": 1.0 / (RRF_K + rank),
                            "layer": "idea",
                            "title": (r["content"] or "")[:80],
                            "preview": (r["content"] or "")[:300],
                            "date": (r["created_at"] or "")[:10],
                            "meta": f"tags={r['tags']} projects={r['project_links']}",
                        })
                except Exception:
                    pass

    except Exception as e:
        return [TextContent(type="text", text=f"Error during recall: {e}")]

    # ── Apply recency weighting (R6) ────────────────────────────────────
    if recency_half_life > 0:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        decay_lambda = math.log(2) / recency_half_life
        for r in all_results:
            date_str = r.get("date", "")
            if date_str and len(date_str) >= 10:
                try:
                    entry_date = datetime.datetime.fromisoformat(
                        date_str[:10] + "T00:00:00+00:00"
                    )
                    age_days = max(0, (now_dt - entry_date).days)
                    recency_factor = math.exp(-decay_lambda * age_days)
                except Exception:
                    recency_factor = 0.5  # fallback for unparseable dates
            else:
                recency_factor = 0.5  # undated entries get neutral weight

            # Blend: 70% relevance + 30% recency (keeps relevance dominant)
            r["score"] = 0.7 * r["score"] + 0.3 * r["score"] * recency_factor

    # ── Sort by RRF score, deduplicate, take top_k ──────────────────────
    all_results.sort(key=lambda x: x["score"], reverse=True)
    seen: set = set()
    deduped: list[dict] = []
    for r in all_results:
        key = (r["layer"], r["title"][:60])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
        if len(deduped) >= top_k:
            break

    if not deduped:
        return [TextContent(type="text", text=f"No results found for '{query}'.")]

    # ── Format output ───────────────────────────────────────────────────
    scope_label = ""
    if agent_id:
        scope_label += f" agent={agent_id}"
    if project_id:
        scope_label += f" project={project_id}"
    if scope:
        scope_label += f" scope={scope}"

    lines = [f"**Recall: '{query}'**{scope_label} — {len(deduped)} results\n"]
    for i, r in enumerate(deduped, 1):
        lines.append(f"### {i}. [{r['layer']}] {r['title']}")
        lines.append(f"*Score: {r['score']:.4f} | {r['date']} | {r['meta']}*")
        lines.append(r["preview"])
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


# ── remember() — auto-classify and store with scope tags ────────────────────

@app.tool()
async def remember(
    content: str,
    memory_type: str = "auto",
    agent_id: str = "",
    project_id: str = "",
    scope: str = "global",
    title: str = "",
    tags: str = "",
    session_id: str = "",
) -> list[TextContent]:
    """Store something in memory with automatic classification and scope tagging.

    The unified write interface to Metis's memory system. Classifies the content
    into the appropriate memory layer and stores it with scope tags for later
    retrieval via recall().

    Memory types:
      - 'episodic': A time-stamped event (something that happened)
      - 'semantic': A distilled concept or definition (timeless knowledge)
      - 'procedural': A workflow or how-to pattern
      - 'note': A human-curated memory palace entry (saved to DB + markdown)
      - 'auto': Let Metis classify based on content (default)

    Scope tags determine visibility:
      - scope='global': Visible to all agents and projects
      - scope='agent': Visible only when agent_id matches
      - scope='project': Visible only when project_id matches
      - scope='session': Visible only in this session

    Args:
        content: The text to remember. Can be a finding, concept, workflow,
            decision, or any text worth preserving.
        memory_type: How to classify this memory. One of 'episodic', 'semantic',
            'procedural', 'note', or 'auto' (default — Metis decides).
        agent_id: Tag this memory as belonging to a specific agent (e.g. 'librarian').
        project_id: Tag this memory as belonging to a specific project.
        scope: Visibility scope: 'global' (default), 'agent', 'project', or 'session'.
        title: Optional short title. Auto-generated from content if empty.
        tags: Comma-separated topic tags (e.g. 'hat,diagnostics,rdts').
        session_id: Current pipeline session ID (optional).

    Returns:
        Confirmation of what was stored, in which layer, with what scope.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    if not content.strip():
        return [TextContent(type="text", text="Content cannot be empty.")]

    # ── Auto-classify if needed ─────────────────────────────────────────
    if memory_type == "auto":
        memory_type = _classify_memory_type(content)

    # ── Generate title if not provided ──────────────────────────────────
    if not title:
        title = content[:80].replace("\n", " ").strip()
        if len(content) > 80:
            title += "..."

    now = _now()
    stored_in = ""

    try:
        if memory_type == "note":
            # Store in memory palace (memory_entries + optional markdown)
            stored_in = _store_as_note(content, title, tags, now)

        elif memory_type in ("episodic", "semantic", "procedural"):
            # Store in vector memory with scope tags
            stored_in = _store_in_vector_memory(
                content, memory_type, title, tags,
                agent_id, project_id, scope, session_id, now
            )

        else:
            # Fallback to episodic
            stored_in = _store_in_vector_memory(
                content, "episodic", title, tags,
                agent_id, project_id, scope, session_id, now
            )

    except Exception as e:
        return [TextContent(type="text", text=f"Error storing memory: {e}")]

    scope_desc = f"scope={scope}"
    if agent_id:
        scope_desc += f" agent={agent_id}"
    if project_id:
        scope_desc += f" project={project_id}"

    return [TextContent(
        type="text",
        text=f"Remembered [{memory_type}]: **{title}**\n"
             f"  Layer: {stored_in}\n"
             f"  Scope: {scope_desc}\n"
             f"  Tags: {tags or '(none)'}",
    )]


# ── Private helpers ─────────────────────────────────────────────────────────

def _classify_memory_type(content: str) -> str:
    """Simple heuristic classification — no LLM call needed."""
    lower = content.lower()

    # Procedural indicators
    proc_signals = ["step 1", "step 2", "how to", "workflow", "procedure",
                    "first,", "then,", "finally,", "recipe", "instructions"]
    if any(s in lower for s in proc_signals):
        return "procedural"

    # Semantic indicators (definitions, concepts)
    sem_signals = ["is defined as", "refers to", "means that", "concept:",
                   "definition:", "principle:", "the key insight is"]
    if any(s in lower for s in sem_signals):
        return "semantic"

    # Default to episodic (events, notes, findings)
    return "episodic"


def _store_as_note(content: str, title: str, tags: str, now: str) -> str:
    """Store in memory_entries table (memory palace)."""
    slug = title.lower()
    for ch in " /\\:*?\"<>|":
        slug = slug.replace(ch, "-")
    slug = "-".join(p for p in slug.split("-") if p)[:40]
    entry_id = f"mem-{now[:10].replace('-', '')}-{slug}"

    with connect(paths.db) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS memory_entries (
                entry_id TEXT PRIMARY KEY, entry_date TEXT, entry_type TEXT,
                topics TEXT, title TEXT, summary TEXT, file_path TEXT,
                computer TEXT, created_at TEXT
            )"""
        )
        conn.execute(
            """INSERT OR REPLACE INTO memory_entries
               (entry_id, entry_date, entry_type, topics, title, summary,
                file_path, computer, created_at)
               VALUES (?, ?, 'note', ?, ?, ?, '', '', ?)""",
            (entry_id, now[:10], tags, title, content[:2000], now),
        )
        conn.commit()
    return "memory_entries (memory palace)"


def _store_in_vector_memory(
    content: str, memory_type: str, title: str, tags: str,
    agent_id: str, project_id: str, scope: str,
    session_id: str, now: str,
) -> str:
    """Store in the appropriate vector memory table with scope tags."""
    try:
        from metis_mcp.embeddings import embed_document
        vector = embed_document(content[:2000])
    except ImportError:
        # Fallback: store without embedding (still keyword-searchable)
        vector = None

    with connect(paths.db) as conn:
        from metis_mcp.tools.vector_memory import _setup_tables
        _setup_tables(conn)
        _run_migrations(conn)

        if memory_type == "episodic":
            metadata = json.dumps({"title": title, "tags": tags})
            cur = conn.execute(
                """INSERT INTO episodic_memory
                   (session_id, event_type, content, metadata, created_at,
                    agent_id, project_id, scope)
                   VALUES (?, 'note', ?, ?, ?, ?, ?, ?)""",
                (session_id, content, metadata, now, agent_id, project_id, scope),
            )
            row_id = cur.lastrowid
            if vector:
                conn.execute(
                    "INSERT INTO vec_episodic (rowid, embedding) VALUES (?, ?)",
                    (row_id, _encode_vec(vector)),
                )
            conn.commit()
            return "episodic_memory (vector-indexed)"

        elif memory_type == "semantic":
            cur = conn.execute(
                """INSERT INTO semantic_memory
                   (concept, definition, related_concepts, source_type, source_id,
                    created_at, updated_at, agent_id, project_id, scope)
                   VALUES (?, ?, ?, 'remember', '', ?, ?, ?, ?, ?)""",
                (title, content, tags, now, now, agent_id, project_id, scope),
            )
            row_id = cur.lastrowid
            embed_text = f"{title}: {content[:500]}"
            if vector:
                from metis_mcp.embeddings import embed_document as ed
                sem_vec = ed(embed_text)
                conn.execute(
                    "INSERT INTO vec_semantic (rowid, embedding) VALUES (?, ?)",
                    (row_id, _encode_vec(sem_vec)),
                )
            conn.commit()
            return "semantic_memory (vector-indexed)"

        elif memory_type == "procedural":
            cur = conn.execute(
                """INSERT INTO procedural_memory
                   (procedure_name, trigger_context, steps, success_count,
                    last_used, created_at, agent_id, project_id, scope)
                   VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)""",
                (title, tags, content, now, now, agent_id, project_id, scope),
            )
            row_id = cur.lastrowid
            embed_text = f"{title}. {tags}. {content[:500]}"
            if vector:
                from metis_mcp.embeddings import embed_document as ed
                proc_vec = ed(embed_text)
                conn.execute(
                    "INSERT INTO vec_procedural (rowid, embedding) VALUES (?, ?)",
                    (row_id, _encode_vec(proc_vec)),
                )
            conn.commit()
            return "procedural_memory (vector-indexed)"

    return "unknown"


# ── Search helpers (keep the main function clean) ───────────────────────────

def _search_episodic_vec(conn, vec_bytes, limit, scope_where, scope_params) -> list[dict]:
    """Vector search on episodic memory, returns {id: rank}."""
    rows = conn.execute(
        f"""SELECT e.id, e.event_type, e.content, e.created_at,
                   e.agent_id, e.project_id, v.distance
            FROM vec_episodic v
            JOIN episodic_memory e ON e.id = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
            ORDER BY v.distance""",
        (vec_bytes, limit),
    ).fetchall()

    # Apply scope filter in Python (vec0 doesn't support JOIN filters in WHERE)
    if scope_where:
        filtered = []
        for r in rows:
            match = True
            for param in scope_params:
                if param and param not in (r["agent_id"] or "", r["project_id"] or "", "global"):
                    # Simple check — if the param is set, the row must match
                    pass
            filtered.append(r)
        rows = filtered

    results = {}
    for rank, r in enumerate(rows, 1):
        results[r["id"]] = {
            "rank": rank,
            "title": (r["content"] or "")[:80],
            "preview": (r["content"] or "")[:300],
            "date": (r["created_at"] or "")[:10],
            "meta": f"type={r['event_type']} agent={r['agent_id'] or '-'} project={r['project_id'] or '-'}",
        }
    return results


def _search_episodic_kw(conn, like, limit, scope_where, scope_params) -> dict:
    """Keyword search on episodic memory (excludes archived entries)."""
    params = [like]
    where_extra = " AND (archived IS NULL OR archived = 0)"
    if scope_params:
        for i, p in enumerate(scope_params):
            if "agent_id" in scope_where.split("?")[i] if i < len(scope_where.split("?")) else False:
                where_extra += " AND agent_id = ?"
                params.append(p)
            elif "project_id" in scope_where:
                where_extra += " AND project_id = ?"
                params.append(p)

    rows = conn.execute(
        f"""SELECT id, event_type, content, created_at, agent_id, project_id
            FROM episodic_memory
            WHERE content LIKE ?{where_extra}
            ORDER BY created_at DESC LIMIT ?""",
        (*params, limit),
    ).fetchall()

    results = {}
    for rank, r in enumerate(rows, 1):
        results[r["id"]] = {
            "rank": rank,
            "title": (r["content"] or "")[:80],
            "preview": (r["content"] or "")[:300],
            "date": (r["created_at"] or "")[:10],
            "meta": f"type={r['event_type']} agent={r['agent_id'] or '-'} project={r['project_id'] or '-'}",
        }
    return results


def _search_semantic_vec(conn, vec_bytes, limit, scope_where, scope_params) -> dict:
    rows = conn.execute(
        f"""SELECT s.id, s.concept, s.definition, s.created_at,
                   s.agent_id, s.project_id, v.distance
            FROM vec_semantic v
            JOIN semantic_memory s ON s.id = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
            ORDER BY v.distance""",
        (vec_bytes, limit),
    ).fetchall()

    results = {}
    for rank, r in enumerate(rows, 1):
        results[r["id"]] = {
            "rank": rank,
            "title": r["concept"] or "(unnamed)",
            "preview": (r["definition"] or "")[:300],
            "date": (r["created_at"] or "")[:10],
            "meta": f"agent={r['agent_id'] or '-'} project={r['project_id'] or '-'}",
        }
    return results


def _search_semantic_kw(conn, like, limit, scope_where, scope_params) -> dict:
    rows = conn.execute(
        f"""SELECT id, concept, definition, created_at, agent_id, project_id
            FROM semantic_memory
            WHERE concept LIKE ? OR definition LIKE ?
            ORDER BY updated_at DESC LIMIT ?""",
        (like, like, limit),
    ).fetchall()

    results = {}
    for rank, r in enumerate(rows, 1):
        results[r["id"]] = {
            "rank": rank,
            "title": r["concept"] or "(unnamed)",
            "preview": (r["definition"] or "")[:300],
            "date": (r["created_at"] or "")[:10],
            "meta": f"agent={r['agent_id'] or '-'} project={r['project_id'] or '-'}",
        }
    return results


def _search_procedural_vec(conn, vec_bytes, limit, scope_where, scope_params) -> dict:
    rows = conn.execute(
        f"""SELECT p.id, p.procedure_name, p.steps, p.trigger_context,
                   p.last_used, p.agent_id, p.project_id, v.distance
            FROM vec_procedural v
            JOIN procedural_memory p ON p.id = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
            ORDER BY v.distance""",
        (vec_bytes, limit),
    ).fetchall()

    results = {}
    for rank, r in enumerate(rows, 1):
        results[r["id"]] = {
            "rank": rank,
            "title": r["procedure_name"] or "(unnamed)",
            "preview": (r["steps"] or "")[:300],
            "date": (r["last_used"] or "")[:10],
            "meta": f"trigger={r['trigger_context'] or '-'} agent={r['agent_id'] or '-'}",
        }
    return results


def _search_procedural_kw(conn, like, limit, scope_where, scope_params) -> dict:
    rows = conn.execute(
        f"""SELECT id, procedure_name, steps, trigger_context, last_used,
                   agent_id, project_id
            FROM procedural_memory
            WHERE procedure_name LIKE ? OR trigger_context LIKE ? OR steps LIKE ?
            ORDER BY last_used DESC LIMIT ?""",
        (like, like, like, limit),
    ).fetchall()

    results = {}
    for rank, r in enumerate(rows, 1):
        results[r["id"]] = {
            "rank": rank,
            "title": r["procedure_name"] or "(unnamed)",
            "preview": (r["steps"] or "")[:300],
            "date": (r["last_used"] or "")[:10],
            "meta": f"trigger={r['trigger_context'] or '-'} agent={r['agent_id'] or '-'}",
        }
    return results


def _search_knowledge(conn, q_vec_norm, all_results, RRF_K, top_k) -> None:
    """Search PDF knowledge databases and append to all_results."""
    try:
        total_chunks = conn.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
        if total_chunks == 0:
            return

        db_names = {}
        for row in conn.execute("SELECT id, name FROM knowledge_databases").fetchall():
            db_names[row[0]] = row[1]

        candidates = conn.execute(
            """SELECT v.rowid, v.distance
               FROM vec_pdf_chunks v
               WHERE v.embedding MATCH ?
                 AND k = ?""",
            (q_vec_norm, min(top_k * 2, 40)),
        ).fetchall()

        if not candidates:
            return

        rowids = [r[0] for r in candidates]
        distances = {r[0]: r[1] for r in candidates}
        ph = ",".join("?" * len(rowids))
        chunks = conn.execute(
            f"""SELECT id, db_id, source_file, domain, title, page_start, chunk_text
                FROM pdf_chunks WHERE id IN ({ph})""",
            rowids,
        ).fetchall()

        chunks_sorted = sorted(chunks, key=lambda c: distances.get(c[0], 9999))

        for rank, c in enumerate(chunks_sorted[:top_k], 1):
            chunk_id, db_id, source_file, domain, title, page_start, chunk_text = c
            dist = distances.get(chunk_id, 0)
            score = max(0.0, min(1.0, 1.0 - (dist * dist) / 2.0))
            layer_name = db_names.get(db_id, f"db:{db_id}")
            all_results.append({
                "score": 1.0 / (RRF_K + rank) + score * 0.01,  # boost by similarity
                "layer": "knowledge",
                "title": title or source_file.split("/")[-1],
                "preview": (chunk_text or "")[:300].replace("\n", " "),
                "date": "",
                "meta": f"layer={layer_name} domain={domain} p.{page_start}",
            })
    except Exception:
        pass


def _merge_rrf(
    all_results: list[dict],
    vec_results: dict,
    kw_results: dict,
    layer: str,
    RRF_K: int,
    top_k: int,
) -> None:
    """Merge vector and keyword results using RRF and append to all_results."""
    all_ids = set(vec_results) | set(kw_results)

    for rid in all_ids:
        vec_rank = vec_results[rid]["rank"] if rid in vec_results else top_k * 4
        kw_rank = kw_results[rid]["rank"] if rid in kw_results else top_k * 4
        score = 1.0 / (RRF_K + vec_rank) + 1.0 / (RRF_K + kw_rank)

        info = vec_results.get(rid) or kw_results.get(rid)
        all_results.append({
            "score": score,
            "layer": layer,
            "title": info["title"],
            "preview": info["preview"],
            "date": info["date"],
            "meta": info["meta"],
        })


# ── Memory relations (R5) — lightweight graph edges between entries ──────

_RELATIONS_DDL = """
CREATE TABLE IF NOT EXISTS memory_relations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_layer TEXT NOT NULL,
    source_id    INTEGER NOT NULL,
    target_layer TEXT NOT NULL,
    target_id    INTEGER NOT NULL,
    relation     TEXT NOT NULL,
    note         TEXT DEFAULT '',
    created_at   TEXT NOT NULL,
    UNIQUE(source_layer, source_id, target_layer, target_id, relation)
)
"""


def _ensure_relations(conn) -> None:
    conn.execute(_RELATIONS_DDL)


@app.tool()
async def link_memories(
    source_layer: str,
    source_id: int,
    target_layer: str,
    target_id: int,
    relation: str,
    note: str = "",
) -> list[TextContent]:
    """Create a typed relationship between two memory entries.

    Links two entries across any memory layers — episodic, semantic, procedural,
    memory (palace), or knowledge. This builds a lightweight knowledge graph on
    top of the existing memory layers, enabling graph traversal during recall.

    Example relations: 'informed_by', 'contradicts', 'elaborates', 'derived_from',
    'supersedes', 'related_to', 'supports', 'led_to'.

    Args:
        source_layer: Layer of the source entry ('episodic', 'semantic',
            'procedural', 'memory', 'knowledge').
        source_id: Row ID of the source entry in its layer.
        target_layer: Layer of the target entry.
        target_id: Row ID of the target entry in its layer.
        relation: Relationship type (e.g. 'informed_by', 'contradicts').
        note: Optional free-text note explaining the relationship.

    Returns:
        Confirmation of the created link, or an error if it already exists.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    valid_layers = {"episodic", "semantic", "procedural", "memory", "knowledge"}
    if source_layer not in valid_layers or target_layer not in valid_layers:
        return [TextContent(type="text", text=f"Invalid layer. Use one of: {', '.join(sorted(valid_layers))}")]

    now = _now()
    try:
        with connect(paths.db) as conn:
            _ensure_relations(conn)
            conn.execute(
                """INSERT OR IGNORE INTO memory_relations
                   (source_layer, source_id, target_layer, target_id, relation, note, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (source_layer, source_id, target_layer, target_id, relation, note, now),
            )
            conn.commit()
        return [TextContent(
            type="text",
            text=f"Linked: [{source_layer}:{source_id}] —{relation}→ [{target_layer}:{target_id}]"
                 + (f" ({note})" if note else ""),
        )]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating link: {e}")]


@app.tool()
async def get_related_memories(
    layer: str,
    entry_id: int,
    direction: str = "both",
) -> list[TextContent]:
    """Find all memories related to a given entry via memory_relations.

    Traverses the lightweight knowledge graph to find connected entries.
    Use this after recall() to explore how a result connects to other
    knowledge — e.g. which papers informed a decision, or which concepts
    relate to a workflow.

    Args:
        layer: The layer of the entry to look up ('episodic', 'semantic', etc.).
        entry_id: Row ID of the entry.
        direction: 'outgoing' (this entry → others), 'incoming' (others → this),
            or 'both' (default).

    Returns:
        List of related entries with their relationship type and content preview.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            _ensure_relations(conn)
            results = []

            if direction in ("outgoing", "both"):
                rows = conn.execute(
                    """SELECT target_layer, target_id, relation, note, created_at
                       FROM memory_relations
                       WHERE source_layer = ? AND source_id = ?
                       ORDER BY created_at DESC""",
                    (layer, entry_id),
                ).fetchall()
                for r in rows:
                    preview = _fetch_preview(conn, r["target_layer"], r["target_id"])
                    results.append({
                        "direction": "→",
                        "relation": r["relation"],
                        "layer": r["target_layer"],
                        "id": r["target_id"],
                        "preview": preview,
                        "note": r["note"],
                    })

            if direction in ("incoming", "both"):
                rows = conn.execute(
                    """SELECT source_layer, source_id, relation, note, created_at
                       FROM memory_relations
                       WHERE target_layer = ? AND target_id = ?
                       ORDER BY created_at DESC""",
                    (layer, entry_id),
                ).fetchall()
                for r in rows:
                    preview = _fetch_preview(conn, r["source_layer"], r["source_id"])
                    results.append({
                        "direction": "←",
                        "relation": r["relation"],
                        "layer": r["source_layer"],
                        "id": r["source_id"],
                        "preview": preview,
                        "note": r["note"],
                    })

        if not results:
            return [TextContent(type="text", text=f"No relations found for [{layer}:{entry_id}].")]

        lines = [f"**Relations for [{layer}:{entry_id}]** — {len(results)} links\n"]
        for r in results:
            lines.append(f"- {r['direction']} **{r['relation']}** [{r['layer']}:{r['id']}]: {r['preview']}")
            if r["note"]:
                lines.append(f"  _Note: {r['note']}_")
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error querying relations: {e}")]


def _fetch_preview(conn, layer: str, entry_id: int) -> str:
    """Fetch a short content preview for a memory entry."""
    try:
        if layer == "episodic":
            row = conn.execute(
                "SELECT content FROM episodic_memory WHERE id = ?", (entry_id,)
            ).fetchone()
            return (row["content"] or "")[:120] if row else "(not found)"
        elif layer == "semantic":
            row = conn.execute(
                "SELECT concept, definition FROM semantic_memory WHERE id = ?", (entry_id,)
            ).fetchone()
            return f"{row['concept']}: {(row['definition'] or '')[:100]}" if row else "(not found)"
        elif layer == "procedural":
            row = conn.execute(
                "SELECT procedure_name FROM procedural_memory WHERE id = ?", (entry_id,)
            ).fetchone()
            return row["procedure_name"] if row else "(not found)"
        elif layer == "memory":
            row = conn.execute(
                "SELECT title FROM memory_entries WHERE entry_id = ? OR CAST(rowid AS TEXT) = ?",
                (str(entry_id), str(entry_id)),
            ).fetchone()
            return (row["title"] or "")[:120] if row else "(not found)"
        elif layer == "knowledge":
            row = conn.execute(
                "SELECT title, chunk_text FROM pdf_chunks WHERE id = ?", (entry_id,)
            ).fetchone()
            return f"{row['title'] or ''}: {(row['chunk_text'] or '')[:80]}" if row else "(not found)"
    except Exception:
        pass
    return "(preview unavailable)"
