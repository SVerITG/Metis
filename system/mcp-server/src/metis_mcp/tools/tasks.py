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

            lines.append("\n[Open Metis Dashboard](http://localhost:8080)")
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


@app.tool()
async def update_task(
    task_id: str,
    status: str = "",
    title: str = "",
    owner: str = "",
    notes: str = "",
    due_date: str = "",
    recurrence: str = "",
) -> list[TextContent]:
    """Update an existing task — its status, title, owner, notes, due date, or recurrence.

    The companion to create_task and get_tasks: use this to mark a task done or
    blocked, reschedule it, reassign it, or edit its details. Only the fields you
    pass are changed; empty arguments leave the existing value untouched. Marking
    a recurring task "done" automatically creates its next occurrence. Find a
    task_id with get_tasks; use delete_task to remove a task entirely.

    Args:
        task_id: ID of the task to update (as shown by get_tasks). Required.
        status: New status — "open", "done", or "blocked". Empty = unchanged.
        title: New title. Empty = unchanged.
        owner: New owner. Empty = unchanged.
        notes: New notes/details. Empty = unchanged.
        due_date: New due date in "YYYY-MM-DD" format. Empty = unchanged.
        recurrence: New repeat — "daily", "weekly", "monthly", or "yearly".
            Empty = unchanged; pass "none" to clear an existing recurrence.

    Returns:
        A confirmation listing the changed fields (and the next-occurrence id if a
        recurring task was completed), or a note if the task_id was not found.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    status = (status or "").strip().lower()
    if status and status not in {"open", "done", "blocked"}:
        return [TextContent(type="text", text=(
            f"Invalid status '{status}'. Use one of: open, done, blocked."
        ))]

    # recurrence: "" = unchanged, "none" = clear, otherwise validate.
    set_recurrence = False
    new_recurrence = ""
    raw_rec = (recurrence or "").strip().lower()
    if raw_rec:
        set_recurrence = True
        new_recurrence = "" if raw_rec == "none" else raw_rec
        if new_recurrence not in _VALID_RECURRENCE:
            return [TextContent(type="text", text=(
                f"Invalid recurrence '{recurrence}'. Use daily, weekly, monthly, yearly, or none."
            ))]

    fields: list[str] = []
    params: list = []
    if status:
        fields.append("status = ?"); params.append(status)
    if title:
        fields.append("title = ?"); params.append(title)
    if owner:
        fields.append("owner = ?"); params.append(owner)
    if notes:
        fields.append("notes = ?"); params.append(notes)
    if due_date:
        fields.append("due_date = ?"); params.append(due_date)
    if set_recurrence:
        fields.append("recurrence = ?"); params.append(new_recurrence)

    if not fields:
        return [TextContent(type="text", text=(
            "Nothing to update — pass at least one field (status, title, owner, notes, due_date, recurrence)."
        ))]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fields.append("updated_at = ?"); params.append(now)
    params.append(task_id)

    try:
        with connect(paths.db) as conn:
            _ensure_task_columns(conn)
            cur = conn.execute(
                f"UPDATE tasks SET {', '.join(fields)} WHERE task_id = ?", params
            )
            if cur.rowcount == 0:
                conn.rollback()
                return [TextContent(type="text", text=f"Task not found: {task_id}")]

            # Continue a recurring series when it's completed.
            spawned = None
            if status == "done":
                spawned = spawn_next_occurrence(conn, task_id)
            conn.commit()

        changed = [f.split(" =")[0] for f in fields if not f.startswith("updated_at")]
        msg = f"Task updated: **{task_id}**\n- Changed: {', '.join(changed)}"
        if spawned:
            msg += f"\n- Next occurrence created: {spawned}"
        return [TextContent(type="text", text=msg)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error updating task: {e}")]


@app.tool()
async def delete_task(task_id: str) -> list[TextContent]:
    """Permanently delete a task from the database.

    The destructive complement to create_task — removes the task row entirely.
    Use this for tasks created in error or no longer relevant; to instead mark
    work finished (and continue a recurring series), use update_task with
    status="done". Find the task_id with get_tasks. This cannot be undone.

    Args:
        task_id: ID of the task to delete (as shown by get_tasks). Required.

    Returns:
        A confirmation that the task was deleted, or a note if no task with that
        id exists.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            _ensure_task_columns(conn)
            cur = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            if cur.rowcount == 0:
                return [TextContent(type="text", text=f"Task not found: {task_id}")]
        return [TextContent(type="text", text=f"Task deleted: **{task_id}**")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting task: {e}")]
