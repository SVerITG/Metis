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


# ── Calendar reminders ───────────────────────────────────────────────────────
# The researcher, 2026-08-25: "if I need to remember something you can put it
# there, in the appropriate project or not linked to a project."
#
# Reminders live in `day_plan`, the table the dashboard's Work calendar already
# reads. `kind='reminder'` was ALREADY a rendered chip colour and an accepted
# form value — the calendar could always show reminders, but nothing outside the
# dashboard could write one, so the capability existed and was unreachable from a
# conversation. This closes that.
#
# `project_id` is nullable on purpose: a reminder that belongs to no project is a
# first-class thing, not a degraded one.

_DAY_PLAN_DDL = """
CREATE TABLE IF NOT EXISTS day_plan (
    plan_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date  TEXT NOT NULL,
    end_date    TEXT,
    kind        TEXT NOT NULL DEFAULT 'focus',
    project_id  TEXT,
    text        TEXT,
    remind_at   TEXT,
    done        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT
)
"""

# A recurring plan is ONE row plus a rule, expanded when the calendar is drawn —
# the same choice `_plans_between` already makes for multi-day spans, and for the
# same reason: editing "every Monday" should edit one row, not fifty-two.
#
# Everything that can differ BETWEEN occurrences therefore has to live somewhere
# else, and this is that somewhere. Completing one Monday, skipping one Monday,
# moving one Monday, and having been reminded about one Monday are all facts
# about an occurrence, not about the rule. Putting any of them on the row would
# apply them to every occurrence at once.
#
# Single-date plans keep using day_plan.done and are untouched by all of this.
_DAY_PLAN_OCC_DDL = """
CREATE TABLE IF NOT EXISTS day_plan_occurrence (
    plan_id     INTEGER NOT NULL,
    occurred_on TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT '',
    moved_to    TEXT,
    notified_at TEXT,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (plan_id, occurred_on)
)
"""

# 'weekdays' is here because it is the common case for work reminders and is
# clumsy to express otherwise — "every weekday" as five weekly rules is five
# rows to edit. Outlook, Google and iCal all ship it as a first-class option.
_VALID_REPEAT = {"", "daily", "weekdays", "weekly", "monthly", "yearly"}


def _ensure_day_plan(conn) -> None:
    conn.execute(_DAY_PLAN_DDL)
    conn.execute(_DAY_PLAN_OCC_DDL)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(day_plan)")}
    if "recurrence" not in cols:
        conn.execute("ALTER TABLE day_plan ADD COLUMN recurrence TEXT DEFAULT ''")
    if "duration_days" not in cols:
        # How many days ONE occurrence covers. Lets a repeat also be a span —
        # "the first three days of every month" — which the earlier version
        # refused outright.
        conn.execute("ALTER TABLE day_plan ADD COLUMN duration_days INTEGER DEFAULT 1")

    # Carry over the short-lived day_plan_done table this replaced.
    have = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "day_plan_done" in have:
        conn.execute(
            "INSERT OR IGNORE INTO day_plan_occurrence "
            "(plan_id, occurred_on, status, updated_at) "
            "SELECT plan_id, occurred_on, 'done', done_at FROM day_plan_done")


def _resolve_reminder_date(date: str) -> tuple[str, str]:
    """Accept an ISO date or a small set of plain-English offsets.

    Returns (iso_date, error). Natural phrasing is supported because the caller
    is usually relaying something the researcher said out loud — "in a week" —
    and forcing the conversion at the call site is where off-by-one errors get
    introduced silently.
    """
    raw = (date or "").strip().lower()
    if not raw:
        return "", "a date is required"
    today = datetime.date.today()
    offsets = {
        "today": 0, "tomorrow": 1,
        "in a week": 7, "next week": 7, "in one week": 7,
        "in two weeks": 14, "in a fortnight": 14,
        "in a month": 30, "next month": 30,
    }
    if raw in offsets:
        return (today + datetime.timedelta(days=offsets[raw])).isoformat(), ""
    m = re.fullmatch(r"in (\d{1,3}) (day|days|week|weeks|month|months)", raw)
    if m:
        n = int(m.group(1))
        mult = {"day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30}
        return (today + datetime.timedelta(days=n * mult[m.group(2)])).isoformat(), ""
    try:
        return datetime.date.fromisoformat(raw).isoformat(), ""
    except ValueError:
        return "", (f"could not read {date!r} as a date — use YYYY-MM-DD, or a "
                    f"phrase like 'in a week' or 'in 3 days'")


@app.tool()
def add_reminder(
    text: str,
    date: str,
    project_id: str = "",
    remind_at: str = "",
    until: str = "",
    repeat: str = "",
    duration_days: int = 1,
) -> list[TextContent]:
    """Put a reminder on the researcher's dashboard calendar.

    Use this whenever they ask to be reminded of something, or whenever you agree
    to come back to something later. It appears as a chip on the Work calendar on
    the chosen day.

    Args:
        text: What to remind them of. Write it so it still makes sense in a week
            with no other context — "re-run the routing audit", not "check that".
        date: When. Either YYYY-MM-DD, or a phrase: "tomorrow", "in a week",
            "in 3 days", "in two weeks", "in a month".
        project_id: Optional project slug to file it under (e.g. "metis-dashboard").
            Leave empty for a reminder that belongs to no project — that is a
            normal case, not a fallback.
        remind_at: Optional time of day, "HH:MM".
        until: Optional end date, same formats as `date`. Its meaning depends on
            `repeat`, and the two readings are mutually exclusive:
              * without `repeat` — a MULTI-DAY event. `date`..`until` is one
                continuous block (a conference, a field trip, leave).
              * with `repeat` — when the SERIES stops. Leave empty for open-ended.
            A recurring multi-day event is not supported; say so rather than
            silently picking one of the two readings.
        repeat: "" (default), "daily", "weekdays", "weekly", "monthly" or
            "yearly". A repeating plan is stored as one row plus this rule and
            expanded when the calendar is drawn, so changing it changes every
            future occurrence at once.
        duration_days: How many days ONE occurrence covers, default 1. Use it with
            `repeat` for something like "the first three days of every month".
            Without `repeat`, prefer `until` — it says the same thing more clearly.

    Returns:
        Confirmation naming the date, span or schedule it was placed on.
    """
    text = (text or "").strip()
    if not text:
        return [TextContent(type="text", text="Nothing to remind you of — text is required.")]

    iso, err = _resolve_reminder_date(date)
    if err:
        return [TextContent(type="text", text=f"Could not set the reminder: {err}.")]

    repeat = (repeat or "").strip().lower()
    if repeat in ("weekday", "every weekday", "workdays"):
        repeat = "weekdays"
    if repeat not in _VALID_REPEAT:
        return [TextContent(type="text", text=(
            f"Could not set the reminder: {repeat!r} is not a repeat I understand. "
            "Use daily, weekdays, weekly, monthly or yearly."))]
    try:
        duration_days = max(1, int(duration_days))
    except (TypeError, ValueError):
        duration_days = 1

    end_iso = None
    if (until or "").strip():
        end_iso, err = _resolve_reminder_date(until)
        if err:
            return [TextContent(type="text", text=f"Could not set the reminder: {err}.")]
        if end_iso < iso:
            return [TextContent(type="text", text=(
                f"Could not set the reminder: {end_iso} is before the start date {iso}."))]

    if duration_days > 1 and not repeat:
        # Without a rule there is only one occurrence, so a duration and an end
        # date say the same thing. Fold it into end_date rather than storing two
        # descriptions of one span that can disagree later.
        span_end = (datetime.date.fromisoformat(iso)
                    + datetime.timedelta(days=duration_days - 1)).isoformat()
        if end_iso and end_iso != span_end:
            return [TextContent(type="text", text=(
                "Could not set the reminder: `until` and `duration_days` describe "
                "different spans. Give one or the other."))]
        end_iso, duration_days = span_end, 1

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with connect(paths.db) as conn:
            _ensure_day_plan(conn)
            if project_id:
                known = conn.execute(
                    "SELECT 1 FROM projects WHERE project_id = ?", (project_id,)
                ).fetchone()
                if not known:
                    # Better an unfiled reminder that shows up than a filed one
                    # that vanishes behind a project that does not exist.
                    project_id = ""
            cur = conn.execute(
                "INSERT INTO day_plan (start_date, end_date, kind, project_id, text, "
                "remind_at, done, recurrence, duration_days, created_at, updated_at) "
                "VALUES (?, ?, 'reminder', ?, ?, ?, 0, ?, ?, ?, ?)",
                (iso, end_iso, project_id or None, text,
                 (remind_at or "").strip() or None, repeat, duration_days, now, now),
            )
            conn.commit()
            plan_id = cur.lastrowid
    except Exception as exc:
        return [TextContent(type="text", text=f"Could not save the reminder: {exc}")]

    when = datetime.date.fromisoformat(iso)
    days = (when - datetime.date.today()).days
    rel = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
    where = f" under {project_id}" if project_id else ""
    if repeat:
        stop = (f", until {datetime.date.fromisoformat(end_iso).strftime('%d %B %Y')}"
                if end_iso else ", open-ended")
        each = f", {duration_days} days each" if duration_days > 1 else ""
        head = (f"Repeating {repeat} from {when.strftime('%A %d %B %Y')} "
                f"({rel}){each}{stop}")
    elif end_iso:
        end = datetime.date.fromisoformat(end_iso)
        span = (end - when).days + 1
        head = (f"Blocked out {when.strftime('%a %d %B')} to {end.strftime('%a %d %B %Y')} "
                f"({span} days, starting {rel})")
    else:
        head = f"Reminder set for {when.strftime('%A %d %B %Y')} ({rel})"
    return [TextContent(type="text", text=f"{head}{where}: {text} [plan #{plan_id}]")]
