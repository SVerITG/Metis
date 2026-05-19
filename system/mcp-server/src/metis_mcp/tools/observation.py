"""Structured observation capture and progressive-context recall.

Two tools:
  capture_observation  — log a typed observation during any agent run
                         (discovery / decision / implementation / issue / note)
  get_context          — recall relevant prior context within a token budget
                         (progressive disclosure: index → preview → full)

These extend episodic_memory with explicit classification and auto-extracted
concept tags so retrieval is precise rather than fuzzy. Classification is
stored in the existing `metadata` JSON field — no schema migration needed.
"""

from __future__ import annotations

import datetime
import json
import re
from collections import Counter

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# ── Constants ─────────────────────────────────────────────────────────────────

OBSERVATION_TYPES = ("discovery", "decision", "implementation", "issue", "note")

_TYPE_LABELS = {
    "discovery":      "DISCOVERY",
    "decision":       "DECISION",
    "implementation": "IMPLEMENTATION",
    "issue":          "ISSUE",
    "note":           "NOTE",
}

_STOP_WORDS = frozenset("""
a an and the of to for in on at by with as is was are were be been being it
this that these those i me my we our you your they them their he she him
her his hers but or if so not no yes do does did done can could should would
will may might must have has had there here when where why how what which who
all any some many few more most less least other another such same own about
into off out over under up down before after during while because since
though although however therefore thus also too very just only than then now
each both either neither none every much such
""".split())

# Chars per token — rough estimate for token-budget calculation
_CHARS_PER_TOKEN = 4


# ── Concept extraction ────────────────────────────────────────────────────────

def _extract_concepts(text: str, top_n: int = 6) -> list[str]:
    """Extract top noun-ish phrases from text via word-frequency."""
    if not text:
        return []
    tokens = re.findall(r"[a-z][a-z\-]{2,}", text.lower())
    counter: Counter[str] = Counter(
        tok for tok in tokens if tok not in _STOP_WORDS
    )
    return [word for word, _ in counter.most_common(top_n)]


# ── MCP tools ─────────────────────────────────────────────────────────────────

@app.tool()
async def capture_observation(
    observation_type: str,
    content: str,
    agent_slug: str = "",
    session_id: str = "",
    concepts: str = "",
    related_files: str = "",
) -> list[TextContent]:
    """Record a typed observation during an agent run.

    Use this throughout a run to capture what you are learning so it can be
    recalled in future sessions without re-reading history.

    Args:
        observation_type: One of: discovery, decision, implementation, issue, note.
          - discovery:      something new you found out
          - decision:       a choice made and the reasoning behind it
          - implementation: what was built or changed
          - issue:          a bug, blocker, or failure found
          - note:           a general observation that doesn't fit above
        content:        The observation in 1–3 sentences.
        agent_slug:     Which agent is recording (e.g. 'librarian').
        session_id:     Current pipeline session ID (optional).
        concepts:       Comma-separated concept tags — auto-extracted if blank.
        related_files:  Comma-separated file paths this observation relates to.
    """
    if observation_type not in OBSERVATION_TYPES:
        return [TextContent(
            type="text",
            text=f"Unknown type '{observation_type}'. Use one of: {', '.join(OBSERVATION_TYPES)}",
        )]

    if not content or not content.strip():
        return [TextContent(type="text", text="content cannot be empty.")]

    auto_concepts = (
        concepts.split(",")
        if concepts.strip()
        else _extract_concepts(content)
    )
    auto_concepts = [c.strip() for c in auto_concepts if c.strip()]

    metadata = json.dumps({
        "classification": observation_type,
        "agent_slug":     agent_slug,
        "concepts":       auto_concepts,
        "related_files":  [f.strip() for f in related_files.split(",") if f.strip()],
    })

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        vector = None
        try:
            from metis_mcp.embeddings import embed_one
            vector = embed_one(content)
        except Exception:
            pass

        with connect(paths.db) as conn:
            # Ensure table exists (mirrors vector_memory.py DDL)
            conn.execute("""CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT DEFAULT '',
                event_type TEXT DEFAULT 'note',
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )""")
            cur = conn.execute(
                """INSERT INTO episodic_memory
                   (session_id, event_type, content, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, observation_type, content.strip(), metadata, now),
            )
            row_id = cur.lastrowid

            if vector is not None:
                import struct, sqlite_vec
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
                conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS vec_episodic
                    USING vec0(embedding float[384])""")
                blob = struct.pack(f"{len(vector)}f", *vector)
                conn.execute(
                    "INSERT INTO vec_episodic(rowid, embedding) VALUES (?, ?)",
                    (row_id, blob),
                )
            conn.commit()

        label = _TYPE_LABELS.get(observation_type, observation_type.upper())
        tag_str = ", ".join(auto_concepts[:4]) if auto_concepts else "—"
        return [TextContent(
            type="text",
            text=(
                f"[{label}] Recorded (id={row_id}). "
                f"Concepts: {tag_str}. "
                "Recallable via get_context() in future sessions."
            ),
        )]

    except Exception as e:
        return [TextContent(type="text", text=f"Error storing observation: {e}")]


@app.tool()
async def get_context(
    query: str,
    budget_tokens: int = 2000,
    agent_slug: str = "",
    days: int = 90,
) -> list[TextContent]:
    """Recall relevant prior context within a token budget.

    Progressive disclosure: returns more detail when budget allows.
      ≤ 500 tokens  → index only   (type + first 12 words per entry)
      ≤ 2000 tokens → preview      (type + first 40 words)
      >  2000 tokens → full         (complete content)

    Combines semantic vector search (if fastembed available) with keyword
    fallback, filtered to the last `days` days.

    Args:
        query:        What you are looking for — natural language.
        budget_tokens: How many tokens you can spend on context (default 2000).
        agent_slug:   Restrict to a specific agent's observations (optional).
        days:         How far back to search (default 90 days).
    """
    if not query.strip():
        return [TextContent(type="text", text="query cannot be empty.")]

    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=days)
    ).isoformat()

    # ── Try vector search first ────────────────────────────────────────────
    results: list[dict] = []
    try:
        from metis_mcp.embeddings import embed_one
        import struct, sqlite_vec

        query_vec = embed_one(query)
        blob = struct.pack(f"{len(query_vec)}f", *query_vec)

        with connect(paths.db) as conn:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            rows = conn.execute(
                """SELECT e.id, e.event_type, e.content, e.metadata, e.agent_slug_fk,
                          e.created_at, v.distance
                   FROM vec_episodic v
                   JOIN episodic_memory e ON e.id = v.rowid
                   WHERE e.created_at >= ?
                   ORDER BY v.distance ASC
                   LIMIT 20""",
                (cutoff,),
            ).fetchall()
            results = [dict(r) for r in rows]
    except Exception:
        pass

    # ── Fallback: keyword LIKE search ─────────────────────────────────────
    if not results:
        like = f"%{query}%"
        try:
            with connect(paths.db) as conn:
                rows = conn.execute(
                    """SELECT id, event_type, content, metadata, '' as agent_slug_fk,
                              created_at, 0 as distance
                       FROM episodic_memory
                       WHERE created_at >= ?
                         AND content LIKE ?
                       ORDER BY created_at DESC
                       LIMIT 20""",
                    (cutoff, like),
                ).fetchall()
                results = [dict(r) for r in rows]
        except Exception:
            pass

    # ── Filter by agent_slug ───────────────────────────────────────────────
    if agent_slug:
        filtered = []
        for r in results:
            meta = {}
            try:
                meta = json.loads(r.get("metadata") or "{}")
            except Exception:
                pass
            if meta.get("agent_slug") == agent_slug:
                filtered.append(r)
        results = filtered

    if not results:
        return [TextContent(
            type="text",
            text=f"No prior observations found for '{query}' in the last {days} days.",
        )]

    # ── Progressive disclosure ─────────────────────────────────────────────
    if budget_tokens <= 500:
        detail = "index"      # type + 12 words
    elif budget_tokens <= 2000:
        detail = "preview"    # type + 40 words
    else:
        detail = "full"       # complete content

    lines = [
        f"Prior context for '{query}' — {len(results)} entries "
        f"(detail={detail}, budget={budget_tokens} tokens):",
        "",
    ]

    chars_used = sum(len(l) for l in lines)
    budget_chars = budget_tokens * _CHARS_PER_TOKEN

    for r in results:
        meta = {}
        try:
            meta = json.loads(r.get("metadata") or "{}")
        except Exception:
            pass

        cls = meta.get("classification") or r.get("event_type") or "note"
        label = _TYPE_LABELS.get(cls, cls.upper())
        concepts = meta.get("concepts") or []
        when = (r.get("created_at") or "")[:10]
        slug = meta.get("agent_slug") or ""

        content = r.get("content") or ""
        words = content.split()

        if detail == "index":
            snippet = " ".join(words[:12])
            if len(words) > 12:
                snippet += "…"
            row = f"[{label}] {when} — {snippet}"
        elif detail == "preview":
            snippet = " ".join(words[:40])
            if len(words) > 40:
                snippet += "…"
            tag_str = ", ".join(concepts[:3]) if concepts else ""
            row = f"[{label}] {when}{' · ' + slug if slug else ''}"
            if tag_str:
                row += f" ({tag_str})"
            row += f"\n  {snippet}"
        else:  # full
            tag_str = ", ".join(concepts) if concepts else ""
            row = f"[{label}] {when}{' · ' + slug if slug else ''}"
            if tag_str:
                row += f" [{tag_str}]"
            row += f"\n{content}"

        row_chars = len(row) + 2
        if chars_used + row_chars > budget_chars:
            lines.append(f"… {len(results) - lines.count('') + 2} more entries truncated by budget")
            break
        lines.append(row)
        lines.append("")
        chars_used += row_chars

    return [TextContent(type="text", text="\n".join(lines))]
