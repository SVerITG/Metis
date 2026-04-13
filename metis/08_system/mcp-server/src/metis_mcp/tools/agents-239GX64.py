"""Agent context retrieval and run logging."""

import datetime

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_AGENT_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_slug TEXT NOT NULL,
    task_summary TEXT NOT NULL,
    input_path TEXT DEFAULT '',
    output_path TEXT DEFAULT '',
    complexity TEXT DEFAULT 'standard',
    timestamp TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    model TEXT DEFAULT ''
)
"""

_AGENT_RUNS_MIGRATE = [
    "ALTER TABLE agent_runs ADD COLUMN input_tokens INTEGER DEFAULT 0",
    "ALTER TABLE agent_runs ADD COLUMN output_tokens INTEGER DEFAULT 0",
    "ALTER TABLE agent_runs ADD COLUMN model TEXT DEFAULT ''",
]


@app.tool()
async def get_agent_context(agent_slug: str) -> list[TextContent]:
    """Load an agent's system prompt and contract from the PKM.

    Reads system-prompt.md and contract.md from 02_agents/{agent_slug}/.
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
) -> list[TextContent]:
    """Log an agent run to the SQLite database.

    Records that an agent executed a task, for audit and dashboard tracking.

    Args:
        agent_slug: Which agent performed the work.
        task_summary: Brief description of what was done.
        input_path: Path to input file(s), if any.
        output_path: Path to output file(s), if any.
        complexity: Task complexity -- "trivial", "standard", or "complex".
        input_tokens: Input tokens consumed (for cost tracking).
        output_tokens: Output tokens produced (for cost tracking).
        model: Model used (e.g. "claude-sonnet-4-6", "claude-haiku-4-5").
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
                   (agent_slug, task_summary, input_path, output_path, complexity, timestamp,
                    input_tokens, output_tokens, model)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                ),
            )
            conn.commit()

        return [
            TextContent(
                type="text",
                text=f"Logged run for agent '{agent_slug}': {task_summary}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error logging agent run: {e}")]
