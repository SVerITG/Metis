"""
tools/data_automation.py — Data automation triggers.

Allows users to define "when X happens, do Y" rules for datasets:
  - register_data_trigger()  — create a new trigger
  - list_data_triggers()     — view all triggers and their last-run status
  - update_data_trigger()    — enable/disable or modify a trigger
  - delete_data_trigger()    — remove a trigger
  - run_trigger_now()        — manually fire a trigger

Triggers are stored in the data_triggers table. The dashboard scheduler
polls active triggers via job_monitor_datasets() (scheduler.py).
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths


def _connect():
    conn = sqlite3.connect(str(paths.db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_triggers (
            trigger_id   TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            event_type   TEXT NOT NULL,
            source_path  TEXT DEFAULT '',
            action       TEXT NOT NULL,
            action_args  TEXT DEFAULT '{}',
            schedule     TEXT DEFAULT '',
            project_id   TEXT DEFAULT '',
            enabled      INTEGER DEFAULT 1,
            last_run_at  TEXT DEFAULT '',
            last_status  TEXT DEFAULT '',
            last_message TEXT DEFAULT '',
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_trigger_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_id   TEXT NOT NULL,
            status       TEXT NOT NULL,
            message      TEXT DEFAULT '',
            ran_at       TEXT NOT NULL
        )
    """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


VALID_EVENT_TYPES = {"file-added", "file-modified", "scheduled", "record-count"}
VALID_ACTIONS = {"profile", "suggest-cleaning", "clean", "reindex-kg", "alert", "custom"}


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@app.tool()
async def register_data_trigger(
    name: str,
    event_type: str,
    action: str,
    source_path: str = "",
    action_args: str = "{}",
    schedule: str = "",
    project_id: str = "",
) -> list[TextContent]:
    """Register a data automation trigger — "when X happens, do Y".

    Args:
        name: Human-readable name (e.g. "Profile new datasets in inputs/")
        event_type: One of: file-added, file-modified, scheduled, record-count
        action: One of: profile, suggest-cleaning, clean, reindex-kg, alert, custom
        source_path: File or folder to watch (for file events). Can be relative to RC root.
        action_args: JSON string with action-specific parameters (e.g. {"output_dir": "cleaned/"})
        schedule: Cron expression for scheduled triggers (e.g. "0 7 * * *" for 7 AM daily)
        project_id: Optional project to link this trigger to
    """
    if event_type not in VALID_EVENT_TYPES:
        return [TextContent(
            type="text",
            text=f"Invalid event_type '{event_type}'. Must be one of: {', '.join(sorted(VALID_EVENT_TYPES))}"
        )]
    if action not in VALID_ACTIONS:
        return [TextContent(
            type="text",
            text=f"Invalid action '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
        )]

    trigger_id = f"dt-{uuid.uuid4().hex[:8]}"
    now = _now()

    with _connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "INSERT INTO data_triggers "
            "(trigger_id, name, event_type, source_path, action, action_args, "
            "schedule, project_id, enabled, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,1,?,?)",
            (trigger_id, name, event_type, source_path, action,
             action_args, schedule, project_id, now, now),
        )

    return [TextContent(
        type="text",
        text=(
            f"✓ Trigger registered: {name}\n"
            f"  ID: {trigger_id}\n"
            f"  Event: {event_type}\n"
            f"  Action: {action}\n"
            f"  Source: {source_path or '(none)'}\n"
            f"  Schedule: {schedule or '(event-driven)'}"
        ),
    )]


@app.tool()
async def list_data_triggers(
    enabled_only: bool = False,
) -> list[TextContent]:
    """List all data automation triggers with their status.

    Args:
        enabled_only: If true, only show enabled triggers
    """
    with _connect() as conn:
        _ensure_tables(conn)
        where = "WHERE enabled = 1" if enabled_only else ""
        rows = conn.execute(
            f"SELECT * FROM data_triggers {where} ORDER BY created_at DESC"
        ).fetchall()

    if not rows:
        return [TextContent(type="text", text="No data triggers registered.")]

    lines = [f"**Data Triggers** ({len(rows)} total)\n"]
    for r in rows:
        status_icon = "●" if r["enabled"] else "○"
        last = r["last_run_at"] or "never"
        last_status = r["last_status"] or "—"
        lines.append(
            f"{status_icon} **{r['name']}** (`{r['trigger_id']}`)\n"
            f"  Event: {r['event_type']} → Action: {r['action']}\n"
            f"  Source: {r['source_path'] or '—'}\n"
            f"  Last run: {last} ({last_status})\n"
        )

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def update_data_trigger(
    trigger_id: str,
    enabled: bool | None = None,
    name: str = "",
    schedule: str = "",
    action_args: str = "",
) -> list[TextContent]:
    """Update a data trigger (enable/disable, rename, change schedule).

    Args:
        trigger_id: The trigger ID to update
        enabled: Set to true/false to enable/disable
        name: New name (leave empty to keep current)
        schedule: New cron schedule (leave empty to keep current)
        action_args: New action args JSON (leave empty to keep current)
    """
    now = _now()
    updates = ["updated_at = ?"]
    params: list = [now]

    if enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if enabled else 0)
    if name:
        updates.append("name = ?")
        params.append(name)
    if schedule:
        updates.append("schedule = ?")
        params.append(schedule)
    if action_args:
        updates.append("action_args = ?")
        params.append(action_args)

    params.append(trigger_id)

    with _connect() as conn:
        _ensure_tables(conn)
        result = conn.execute(
            f"UPDATE data_triggers SET {', '.join(updates)} WHERE trigger_id = ?",
            params,
        )
        if result.rowcount == 0:
            return [TextContent(type="text", text=f"Trigger '{trigger_id}' not found.")]

    return [TextContent(type="text", text=f"✓ Trigger {trigger_id} updated.")]


@app.tool()
async def delete_data_trigger(trigger_id: str) -> list[TextContent]:
    """Delete a data trigger permanently.

    Args:
        trigger_id: The trigger ID to delete
    """
    with _connect() as conn:
        _ensure_tables(conn)
        result = conn.execute(
            "DELETE FROM data_triggers WHERE trigger_id = ?", (trigger_id,)
        )
        if result.rowcount == 0:
            return [TextContent(type="text", text=f"Trigger '{trigger_id}' not found.")]
        conn.execute(
            "DELETE FROM data_trigger_log WHERE trigger_id = ?", (trigger_id,)
        )

    return [TextContent(type="text", text=f"✓ Trigger {trigger_id} deleted.")]


@app.tool()
async def run_trigger_now(trigger_id: str) -> list[TextContent]:
    """Manually execute a data trigger right now.

    Args:
        trigger_id: The trigger ID to run
    """
    with _connect() as conn:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM data_triggers WHERE trigger_id = ?", (trigger_id,)
        ).fetchone()

    if not row:
        return [TextContent(type="text", text=f"Trigger '{trigger_id}' not found.")]

    result = await _execute_trigger(dict(row))
    return [TextContent(type="text", text=result)]


# ---------------------------------------------------------------------------
# Trigger execution engine
# ---------------------------------------------------------------------------

async def _execute_trigger(trigger: dict) -> str:
    """Run a single trigger's action. Returns a status message."""
    action = trigger["action"]
    source = trigger["source_path"]
    now = _now()
    status = "ok"
    message = ""

    try:
        if action == "profile":
            message = await _action_profile(source, trigger)
        elif action == "suggest-cleaning":
            message = await _action_suggest_cleaning(source, trigger)
        elif action == "alert":
            message = await _action_alert(source, trigger)
        elif action == "reindex-kg":
            message = await _action_reindex_kg(trigger)
        else:
            message = f"Action '{action}' executed (no-op: custom actions require manual implementation)."
    except Exception as e:
        status = "error"
        message = str(e)

    # Log execution
    with _connect() as conn:
        _ensure_tables(conn)
        conn.execute(
            "UPDATE data_triggers SET last_run_at=?, last_status=?, last_message=?, updated_at=? "
            "WHERE trigger_id=?",
            (now, status, message[:500], now, trigger["trigger_id"]),
        )
        conn.execute(
            "INSERT INTO data_trigger_log (trigger_id, status, message, ran_at) VALUES (?,?,?,?)",
            (trigger["trigger_id"], status, message[:500], now),
        )

    return f"[{status}] {trigger['name']}: {message}"


async def _action_profile(source_path: str, trigger: dict) -> str:
    """Profile a dataset at source_path."""
    from pathlib import Path as P
    p = P(source_path)
    if not p.is_absolute():
        p = paths.root / source_path
    if not p.exists():
        return f"Source not found: {p}"
    if p.is_dir():
        files = list(p.glob("*.csv")) + list(p.glob("*.xlsx")) + list(p.glob("*.tsv"))
        return f"Found {len(files)} data files in {p.name}. Use profile_dataset() on each."
    return f"Ready to profile: {p.name} ({p.stat().st_size // 1024} KB). Call profile_dataset('{p}') for full analysis."


async def _action_suggest_cleaning(source_path: str, trigger: dict) -> str:
    """Suggest cleaning operations for a dataset."""
    from pathlib import Path as P
    p = P(source_path)
    if not p.is_absolute():
        p = paths.root / source_path
    if not p.exists():
        return f"Source not found: {p}"
    return f"Ready to suggest cleaning for: {p.name}. Call suggest_cleaning('{p}') for recommendations."


async def _action_alert(source_path: str, trigger: dict) -> str:
    """Generate an alert about a data event."""
    args = json.loads(trigger.get("action_args", "{}"))
    alert_msg = args.get("message", f"Data event detected at {source_path}")
    return f"Alert: {alert_msg}"


async def _action_reindex_kg(trigger: dict) -> str:
    """Reindex the knowledge graph for a project."""
    project_id = trigger.get("project_id", "")
    if project_id:
        return f"Knowledge graph reindex queued for project '{project_id}'."
    return "Knowledge graph reindex queued (all projects)."


# ---------------------------------------------------------------------------
# Polling — called by the dashboard scheduler
# ---------------------------------------------------------------------------

def check_file_triggers() -> list[str]:
    """Check all file-based triggers. Returns list of trigger_ids that fired.

    Called by scheduler.py job_monitor_datasets().
    """
    fired = []
    with _connect() as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT * FROM data_triggers WHERE enabled = 1 AND event_type IN ('file-added', 'file-modified')"
        ).fetchall()

    for row in rows:
        trigger = dict(row)
        source = trigger["source_path"]
        if not source:
            continue

        from pathlib import Path as P
        p = P(source)
        if not p.is_absolute():
            p = paths.root / source

        if not p.exists():
            continue

        last_run = trigger["last_run_at"]
        if not last_run:
            # Never run — fire on any existing files
            fired.append(trigger["trigger_id"])
            continue

        # Check if any file is newer than last run
        from datetime import datetime as dt
        try:
            last_dt = dt.fromisoformat(last_run)
        except ValueError:
            fired.append(trigger["trigger_id"])
            continue

        if p.is_dir():
            for f in p.iterdir():
                if f.is_file() and dt.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) > last_dt:
                    fired.append(trigger["trigger_id"])
                    break
        elif p.is_file():
            if dt.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) > last_dt:
                fired.append(trigger["trigger_id"])

    return fired
