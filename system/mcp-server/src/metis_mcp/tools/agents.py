"""Agent context retrieval and run logging."""

import datetime
import json
import struct
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_AGENT_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_slug TEXT NOT NULL,
    task_summary TEXT NOT NULL,
    input_path TEXT DEFAULT '',
    output_path TEXT DEFAULT '',
    status TEXT DEFAULT 'completed',
    created_at TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    model TEXT DEFAULT ''
)
"""

_AGENT_RUNS_MIGRATE = [
    "ALTER TABLE agent_runs ADD COLUMN input_tokens INTEGER DEFAULT 0",
    "ALTER TABLE agent_runs ADD COLUMN output_tokens INTEGER DEFAULT 0",
    "ALTER TABLE agent_runs ADD COLUMN model TEXT DEFAULT ''",
    "ALTER TABLE agent_runs ADD COLUMN session_id TEXT DEFAULT ''",
]


@app.tool()
async def get_agent_context(agent_slug: str) -> list[TextContent]:
    """Load an agent's system prompt and contract from the RC.

    Reads system-prompt.md and contract.md from agents/{agent_slug}/.
    If the agent is not found, lists all available agents.

    Args:
        agent_slug: Folder name of the agent (e.g. "archivist", "librarian").
    """
    agent_dir = paths.agents / agent_slug

    if not agent_dir.is_dir():
        # List available agents
        try:
            available = sorted(
                d.name for d in paths.agents.iterdir() if d.is_dir() and not d.name.startswith(".")
            )
        except FileNotFoundError:
            return [TextContent(type="text", text=f"Agents directory not found: {paths.agents}")]

        return [
            TextContent(
                type="text",
                text=f"Agent '{agent_slug}' not found.\n\nAvailable agents:\n"
                + "\n".join(f"- {a}" for a in available),
            )
        ]

    parts = []
    for filename in ("system-prompt.md", "contract.md"):
        fp = agent_dir / filename
        if fp.exists():
            try:
                parts.append(f"# {filename}\n\n{fp.read_text(encoding='utf-8')}")
            except Exception as e:
                parts.append(f"# {filename}\n\nError reading file: {e}")

    if not parts:
        return [
            TextContent(
                type="text",
                text=f"No system-prompt.md or contract.md found in {agent_dir}",
            )
        ]

    return [TextContent(type="text", text="\n\n---\n\n".join(parts))]


@app.tool()
async def log_agent_run(
    agent_slug: str,
    task_summary: str,
    input_path: str = "",
    output_path: str = "",
    complexity: str = "standard",
    input_tokens: int = 0,
    output_tokens: int = 0,
    model: str = "",
    session_id: str = "",
) -> list[TextContent]:
    """Log a completed agent run to the database for audit and dashboard tracking.

    Records that an agent did a piece of work so it appears in the dashboard's
    Agents view and in get_agent_runs. Call it after writing an output file, per
    the output contract. When a session_id is supplied it also writes a "result"
    event to session_events, closing the loop for /metis pipeline calls.

    Args:
        agent_slug: Slug of the agent that performed the work (e.g. "librarian").
        task_summary: Brief description of what the agent did.
        input_path: Path to the input file(s), if any (default empty string).
        output_path: Path to the output file(s) produced, if any (default empty).
        complexity: The run status stored in the `status` column — typically
            "completed", "partial", or "failed" (default "standard").
        input_tokens: Input tokens consumed, for cost tracking (default 0).
        output_tokens: Output tokens produced, for cost tracking (default 0).
        model: Model identifier used, e.g. "claude-sonnet-4-6" (default empty).
        session_id: Pipeline session ID from session_bootstrap(); when set, also
            records a result event in session_events (default empty string).

    Returns:
        A confirmation message naming the agent and task that were logged.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_AGENT_RUNS_DDL)
            # Migrate existing tables that predate token tracking columns
            for stmt in _AGENT_RUNS_MIGRATE:
                try:
                    conn.execute(stmt)
                except Exception:
                    pass  # Column already exists
            conn.execute(
                """INSERT INTO agent_runs
                   (agent_slug, task_summary, input_path, output_path, status, created_at,
                    input_tokens, output_tokens, model, session_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent_slug,
                    task_summary,
                    input_path,
                    output_path,
                    complexity,
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    input_tokens,
                    output_tokens,
                    model,
                    session_id,
                ),
            )
            conn.commit()

            # Also write to session_events when this run is part of a pipeline session.
            # This closes the loop for /metis calls: run_metis writes turn + routing events,
            # the executing agent then calls log_agent_run which writes the result event.
            if session_id:
                try:
                    conn.execute(
                        """INSERT INTO session_events (session_id, event_type, content, created_at)
                           VALUES (?, 'result', ?, ?)""",
                        (
                            session_id,
                            f"[{agent_slug}] {task_summary[:500]}",
                            datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        ),
                    )
                    conn.commit()
                except Exception:
                    pass  # session_events write is best-effort — don't fail the log

        # ── Phase B: Automatic memory extraction ──────────────────────────
        # Write an episodic memory entry immediately so findings are
        # searchable right away — don't wait for nightly consolidation.
        try:
            _auto_extract_memory(
                conn, agent_slug, task_summary, output_path, session_id
            )
        except Exception:
            pass  # Memory extraction is best-effort — never fail the log

        return [
            TextContent(
                type="text",
                text=f"Logged run for agent '{agent_slug}': {task_summary}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error logging agent run: {e}")]


def _auto_extract_memory(
    conn, agent_slug: str, task_summary: str,
    output_path: str, session_id: str,
) -> None:
    """Extract and store an episodic memory entry from an agent run.

    Writes to episodic_memory with agent_id scope so the agent accumulates
    its own searchable history. If the run produced an output file, reads
    its first 1500 chars and indexes those too.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Build the content to remember
    content_parts = [f"Agent run: {agent_slug}"]
    content_parts.append(f"Task: {task_summary}")

    # Read output file excerpt if it exists
    output_excerpt = ""
    if output_path:
        try:
            fp = paths.root / output_path
            if fp.exists() and fp.suffix in (".md", ".txt", ".json", ".yaml", ".yml"):
                raw = fp.read_text(encoding="utf-8", errors="ignore")[:1500]
                output_excerpt = raw
                content_parts.append(f"Output excerpt: {raw[:500]}")
        except Exception:
            pass

    content = "\n".join(content_parts)
    metadata = json.dumps({
        "agent_slug": agent_slug,
        "output_path": output_path,
        "auto_extracted": True,
    })

    # Ensure vector memory tables exist
    try:
        from metis_mcp.tools.vector_memory import _setup_tables
        _setup_tables(conn)
    except Exception:
        return

    # Insert episodic memory with agent scope
    cur = conn.execute(
        """INSERT INTO episodic_memory
           (session_id, event_type, content, metadata, created_at,
            agent_id, project_id, scope)
           VALUES (?, 'agent_run', ?, ?, ?, ?, '', 'agent')""",
        (session_id, content, metadata, now, agent_slug),
    )
    row_id = cur.lastrowid

    # Embed and index for vector search
    try:
        from metis_mcp.embeddings import embed_document
        vector = embed_document(content[:2000])
        conn.execute(
            "INSERT INTO vec_episodic (rowid, embedding) VALUES (?, ?)",
            (row_id, struct.pack(f"{len(vector)}f", *vector)),
        )
    except (ImportError, Exception):
        pass  # Store without embedding — still keyword-searchable

    conn.commit()


@app.tool()
async def get_agent_runs(
    limit: int = 10,
    since: str = "",
    agent_slug: str = "",
) -> list[TextContent]:
    """Retrieve recent agent run history from the database.

    Returns the log of past agent work — what ran, when, its status, and token
    usage — for the dashboard or for reviewing recent activity. These rows are
    written by log_agent_run. Results come back newest first.

    Args:
        limit: Maximum number of runs to return, newest first (default 10).
        since: ISO date or datetime string; only runs at or after this time are
            returned. Empty string (default) returns runs from all dates.
        agent_slug: Filter to a single agent by slug, e.g. "librarian" or
            "metis". Empty string (default) returns all agents.

    Returns:
        A text block listing the matching runs (run_id, agent, task summary,
        status, timestamp, token counts, model).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="Database not found.")]

    conditions: list[str] = []
    params: list = []
    if since:
        conditions.append("created_at >= ?")
        params.append(since)
    if agent_slug:
        conditions.append("agent_slug = ?")
        params.append(agent_slug)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    try:
        with connect(paths.db) as conn:
            conn.execute(_AGENT_RUNS_DDL)
            rows = conn.execute(
                f"SELECT run_id, agent_slug, task_summary, status, created_at, "
                f"input_tokens, output_tokens, model "
                f"FROM agent_runs {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading agent runs: {e}")]

    if not rows:
        return [TextContent(type="text", text="No agent runs found.")]

    lines = [f"{len(rows)} run(s):\n"]
    for r in rows:
        tokens = (r["input_tokens"] or 0) + (r["output_tokens"] or 0)
        tok_str = f" · {tokens:,} tok" if tokens else ""
        model_str = f" · {r['model']}" if r["model"] else ""
        lines.append(
            f"[{r['agent_slug']}] {(r['task_summary'] or '')[:80]}\n"
            f"  {(r['created_at'] or '')[:16]} · {r['status']}{tok_str}{model_str}"
        )
    return [TextContent(type="text", text="\n\n".join(lines))]
