"""
tools/observability.py — Phase 5.9: Agent span tracing.

Four MCP tools for lightweight distributed tracing inside the Metis pipeline:

  start_span(name, kind, session_id, run_id, parent_id, tags)
      Open a span. Returns span_id. Agent must call end_span() when done.

  end_span(span_id, status, error)
      Close an open span. Computes duration_ms. Returns summary.

  log_span(name, duration_ms, kind, session_id, run_id, parent_id, tags)
      One-shot: record a completed span in a single call.

  get_spans(session_id, run_id, limit)
      Fetch recent spans, optionally filtered by session or run.

The agent_spans table stores traces that the dashboard waterfall renders.
Calling start_span/end_span from pipeline stages gives full step visibility.
"""

import json
import time
from uuid import uuid4

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS agent_spans (
    span_id     TEXT PRIMARY KEY,
    parent_id   TEXT,
    run_id      INTEGER,
    session_id  TEXT,
    name        TEXT    NOT NULL,
    kind        TEXT    NOT NULL DEFAULT 'internal',
    status      TEXT    NOT NULL DEFAULT 'running',
    start_ms    INTEGER NOT NULL,
    end_ms      INTEGER,
    duration_ms INTEGER,
    error       TEXT,
    tags        TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_spans_session  ON agent_spans(session_id);
CREATE INDEX IF NOT EXISTS idx_spans_run      ON agent_spans(run_id);
CREATE INDEX IF NOT EXISTS idx_spans_parent   ON agent_spans(parent_id);
CREATE INDEX IF NOT EXISTS idx_spans_created  ON agent_spans(created_at DESC);
"""


def _ensure_table(conn):
    for stmt in _DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()


# ---------------------------------------------------------------------------
# M5.9.1 — start_span
# ---------------------------------------------------------------------------

@app.tool()
async def start_span(
    name: str,
    kind: str = "internal",
    session_id: str = "",
    run_id: int = 0,
    parent_id: str = "",
    tags: str = "",
) -> list[TextContent]:
    """Open a new tracing span. Returns the span_id to pass to end_span().

    Args:
        name:       Human-readable span label (e.g. 'stage_1_bootstrap', 'tool:search_library').
        kind:       Span type — 'internal' | 'tool' | 'agent' | 'llm'. Default: 'internal'.
        session_id: Session identifier (from session_bootstrap). Optional.
        run_id:     FK to agent_runs.run_id. Optional.
        parent_id:  Parent span_id for nested spans. Optional.
        tags:       JSON string of extra key/value metadata. Optional.

    Returns the span_id string — pass it to end_span() when the work is done.
    """
    span_id = str(uuid4())
    start_ms = int(time.time() * 1000)

    with connect(paths.db) as conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT INTO agent_spans
               (span_id, parent_id, run_id, session_id, name, kind, status, start_ms, tags)
               VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)""",
            (
                span_id,
                parent_id or None,
                run_id or None,
                session_id or None,
                name,
                kind,
                start_ms,
                tags or None,
            ),
        )
        conn.commit()

    return [TextContent(type="text", text=span_id)]


# ---------------------------------------------------------------------------
# M5.9.1 — end_span
# ---------------------------------------------------------------------------

@app.tool()
async def end_span(
    span_id: str,
    status: str = "ok",
    error: str = "",
) -> list[TextContent]:
    """Close an open span. Computes duration from start_ms to now.

    Args:
        span_id: The span_id returned by start_span().
        status:  'ok' | 'error'. Default: 'ok'.
        error:   Error message if status='error'. Optional.

    Returns a summary line: '{name} — {duration_ms}ms [{status}]'
    """
    end_ms = int(time.time() * 1000)

    with connect(paths.db) as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT name, start_ms FROM agent_spans WHERE span_id = ?",
            (span_id,),
        ).fetchone()

        if not row:
            return [TextContent(type="text", text=f"ERROR: span_id not found: {span_id}")]

        name = row["name"]
        duration_ms = end_ms - row["start_ms"]

        conn.execute(
            """UPDATE agent_spans
               SET end_ms = ?, duration_ms = ?, status = ?, error = ?
               WHERE span_id = ?""",
            (end_ms, duration_ms, status, error or None, span_id),
        )
        conn.commit()

    summary = f"{name} — {duration_ms}ms [{status}]"
    if error:
        summary += f"\n  error: {error}"
    return [TextContent(type="text", text=summary)]


# ---------------------------------------------------------------------------
# M5.9.1 — log_span (one-shot)
# ---------------------------------------------------------------------------

@app.tool()
async def log_span(
    name: str,
    duration_ms: int,
    kind: str = "internal",
    session_id: str = "",
    run_id: int = 0,
    parent_id: str = "",
    status: str = "ok",
    tags: str = "",
) -> list[TextContent]:
    """Record a completed span in one call (no separate start/end needed).

    Useful for logging retrospective timing data (e.g. 'that DB query took 42ms').

    Args:
        name:        Span label.
        duration_ms: How long the work took in milliseconds.
        kind:        'internal' | 'tool' | 'agent' | 'llm'. Default: 'internal'.
        session_id:  Session identifier. Optional.
        run_id:      FK to agent_runs. Optional.
        parent_id:   Parent span_id. Optional.
        status:      'ok' | 'error'. Default: 'ok'.
        tags:        JSON string of metadata. Optional.

    Returns the new span_id.
    """
    span_id = str(uuid4())
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - max(0, duration_ms)

    with connect(paths.db) as conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT INTO agent_spans
               (span_id, parent_id, run_id, session_id, name, kind, status,
                start_ms, end_ms, duration_ms, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                span_id,
                parent_id or None,
                run_id or None,
                session_id or None,
                name,
                kind,
                status,
                start_ms,
                end_ms,
                duration_ms,
                tags or None,
            ),
        )
        conn.commit()

    return [TextContent(type="text", text=span_id)]


# ---------------------------------------------------------------------------
# M5.9.1 — get_spans
# ---------------------------------------------------------------------------

@app.tool()
async def get_spans(
    session_id: str = "",
    run_id: int = 0,
    limit: int = 50,
) -> list[TextContent]:
    """Fetch recent agent spans, optionally filtered by session or run.

    Args:
        session_id: Filter to this session. Optional.
        run_id:     Filter to this agent_runs.run_id. Optional.
        limit:      Max rows to return. Default: 50.

    Returns a JSON array of span objects.
    """
    with connect(paths.db) as conn:
        _ensure_table(conn)

        clauses = []
        params = []
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM agent_spans {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()

    spans = [dict(r) for r in rows]
    return [TextContent(type="text", text=json.dumps(spans, indent=2))]
