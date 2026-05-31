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
    recurrence TEXT DEFAULT '',
    parent_task_id TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_VALID_RECURRENCE = {"", "daily", "weekly", "monthly", "yearly"}


def _ensure_task_columns(conn) -> None:
    """Add recurrence / parent_task_id columns to an existing tasks table."""
    conn.execute(_TASKS_DDL)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
    if "recurrence" not in existing:
        conn.execute("ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT ''")
    if "parent_task_id" not in existing:
        conn.execute("ALTER TABLE tasks ADD COLUMN parent_task_id TEXT DEFAULT ''")


def _next_due(due_date: str, recurrence: str) -> str:
    """Advance a YYYY-MM-DD due date by one recurrence period. Empty if not derivable."""
    if recurrence not in _VALID_RECURRENCE or not recurrence:
        return ""
    try:
        d = datetime.date.fromisoformat(due_date[:10])
    except Exception:
        d = datetime.date.today()
    if recurrence == "daily":
        d = d + datetime.timedelta(days=1)
    elif recurrence == "weekly":
        d = d + datetime.timedelta(weeks=1)
    elif recurrence == "monthly":
        month = d.month + 1
        year = d.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                          31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        d = datetime.date(year, month, day)
    elif recurrence == "yearly":
        d = d.replace(year=d.year + 1)
    return d.isoformat()


def spawn_next_occurrence(conn, task_id: str) -> str | None:
    """If task_id is recurring, create its next occurrence. Returns new id or None.

    Call this when a recurring task is marked done so the series continues.
    """
    row = conn.execute(
        "SELECT title, project_id, owner, notes, due_date, recurrence, parent_task_id "
        "FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    if not row:
        return None
    recurrence = (row[5] if not isinstance(row, dict) else row["recurrence"]) or ""
    if recurrence not in _VALID_RECURRENCE or not recurrence:
        return None
    title, project_id, owner, notes, due_date = row[0], row[1], row[2], row[3], row[4]
    new_due = _next_due(due_date, recurrence)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_id = f"{project_id}-{_slugify(title)}-{new_due or now[:10]}"
    conn.execute(
        """INSERT OR REPLACE INTO tasks
           (task_id, title, project_id, owner, status, notes, due_date, recurrence, parent_task_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)""",
        (new_id, title, project_id, owner, notes, new_due, recurrence, task_id, now, now),
    )
    return new_id


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
    recurrence: str = "",
    parent_task_id: str = "",
) -> list[TextContent]:
    """Create a new task in the SQLite database.

    Args:
        title: Short task description.
        project_id: Which project this task belongs to.
        owner: Who is responsible (default "Metis").
        notes: Additional details or context.
        due_date: Optional due date in YYYY-MM-DD format.
        recurrence: Optional repeat — "daily", "weekly", "monthly", or "yearly".
                    When a recurring task is completed, the next occurrence is created automatically.
        parent_task_id: Optional parent task — set this to make this a subtask.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    recurrence = (recurrence or "").strip().lower()
    if recurrence not in _VALID_RECURRENCE:
        return [TextContent(type="text", text=(
            f"Invalid recurrence '{recurrence}'. Use one of: daily, weekly, monthly, yearly (or leave empty)."
        ))]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    task_id = f"{project_id}-{_slugify(title)}"

    try:
        with connect(paths.db) as conn:
            _ensure_task_columns(conn)
            conn.execute(
                """INSERT INTO tasks
                   (task_id, title, project_id, owner, status, notes, due_date, recurrence, parent_task_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)""",
                (task_id, title, project_id, owner, notes, due_date, recurrence, parent_task_id, now, now),
            )
            conn.commit()

        extra = ""
        if recurrence:
            extra += f"\n- Repeats: {recurrence}"
        if parent_task_id:
            extra += f"\n- Subtask of: {parent_task_id}"
        return [
            TextContent(
                type="text",
                text=f"Task created: **{task_id}**\n- Title: {title}\n- Project: {project_id}\n- Owner: {owner}{extra}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating task: {e}")]
