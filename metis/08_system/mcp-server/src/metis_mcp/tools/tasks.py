"""Task querying and creation in the SQLite database."""

import datetime
import re

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_TASKS_DDL = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    project_id TEXT NOT NULL,
    owner TEXT DEFAULT 'Metis',
    status TEXT DEFAULT 'open',
    notes TEXT DEFAULT '',
    due_date TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:60].strip("-")


@app.tool()
async def get_tasks(
    status: str = "open",
    project_id: str = "",
    owner: str = "",
    limit: int = 25,
) -> list[TextContent]:
    """Query tasks from the SQLite database with optional filters.

    Args:
        status: Filter by status -- "open", "done", "blocked", or "" for all.
        project_id: Filter by project. Empty = all projects.
        owner: Filter by owner. Empty = all owners.
        limit: Maximum results (default 25).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
            )
            if not cur.fetchone():
                return [TextContent(type="text", text="No tasks table found in database.")]

            clauses = []
            params: list = []
            if status:
                clauses.append("status = ?")
                params.append(status)
            if project_id:
                clauses.append("project_id = ?")
                params.append(project_id)
            if owner:
                clauses.append("owner = ?")
                params.append(owner)

            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            sql = f"SELECT * FROM tasks{where} ORDER BY due_date, created_at LIMIT ?"
            params.append(limit)

            cur = conn.execute(sql, params)
            rows = cur.fetchall()

            if not rows:
                filters = []
                if status:
                    filters.append(f"status={status}")
                if project_id:
                    filters.append(f"project={project_id}")
                if owner:
                    filters.append(f"owner={owner}")
                desc = ", ".join(filters) if filters else "no filters"
                return [
                    TextContent(type="text", text=f"No tasks found ({desc}).")
                ]

            # Markdown table
            cols = ["task_id", "title", "project_id", "owner", "status", "due_date"]
            lines = ["| " + " | ".join(cols) + " |"]
            lines.append("| " + " | ".join("---" for _ in cols) + " |")
            for row in rows:
                vals = [str(row[c] or "") for c in cols]
                lines.append("| " + " | ".join(vals) + " |")

            lines.append("\n[Open Metis Dashboard](http://localhost:3939)")
            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error querying tasks: {e}")]


@app.tool()
async def create_task(
    title: str,
    project_id: str,
    owner: str = "Metis",
    notes: str = "",
    due_date: str = "",
) -> list[TextContent]:
    """Create a new task in the SQLite database.

    Args:
        title: Short task description.
        project_id: Which project this task belongs to.
        owner: Who is responsible (default "Metis").
        notes: Additional details or context.
        due_date: Optional due date in YYYY-MM-DD format.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    task_id = f"{project_id}-{_slugify(title)}"

    try:
        with connect(paths.db) as conn:
            conn.execute(_TASKS_DDL)
            conn.execute(
                """INSERT INTO tasks
                   (task_id, title, project_id, owner, status, notes, due_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?)""",
                (task_id, title, project_id, owner, notes, due_date, now, now),
            )
            conn.commit()

        return [
            TextContent(
                type="text",
                text=f"Task created: **{task_id}**\n- Title: {title}\n- Project: {project_id}\n- Owner: {owner}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating task: {e}")]
