"""
migrations.py — idempotent schema upkeep for metis.sqlite.

Runs on every MCP server startup. Each migration is a `(name, sql)` tuple,
applied via SQLite's "ADD COLUMN" / "CREATE TABLE IF NOT EXISTS" semantics
so re-runs are safe.

Why this exists: in R8 of the 2026-05-23 audit marathon, the
`brainstorm_sessions` table had drifted — the DDL in `brainstorm.py` expected
columns (title, status, synthesis, action_items) that the existing DB didn't
have, because the table had been created earlier with the legacy shape
(topic, sources_used, summary, linked_idea_ids). `CREATE TABLE IF NOT EXISTS`
silently skipped re-creation, so the new tool's INSERTs failed with
"no column named title". This module makes that whole class of bug impossible
on existing installs upgrading to a new Metis version.

When you add a new column to any table:
  1. Add an `ALTER TABLE ... ADD COLUMN ...` entry to `MIGRATIONS` below
  2. Give it a unique `name` (used to track which migrations have run)
  3. Re-deploy — the runner will apply it once, log it, and skip on next start

When you add a new table, the table's own module should still own its
`CREATE TABLE IF NOT EXISTS` definition. Use this file ONLY for columns
added to existing tables.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


# Migration list. Order matters — each runs once, in sequence.
# Format: (name, sql, table_name)
# - name: unique identifier, never reused (logged to migration history)
# - sql: a single ALTER TABLE or CREATE TABLE IF NOT EXISTS statement
# - table_name: which table this migration touches (for the duplicate-column check)
MIGRATIONS: list[tuple[str, str, str]] = [
    # ── R8 (2026-05-25): brainstorm_sessions drift ──
    (
        "20260525_brainstorm_sessions_add_title",
        "ALTER TABLE brainstorm_sessions ADD COLUMN title TEXT NOT NULL DEFAULT ''",
        "brainstorm_sessions",
    ),
    (
        "20260525_brainstorm_sessions_add_status",
        "ALTER TABLE brainstorm_sessions ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
        "brainstorm_sessions",
    ),
    (
        "20260525_brainstorm_sessions_add_synthesis",
        "ALTER TABLE brainstorm_sessions ADD COLUMN synthesis TEXT DEFAULT NULL",
        "brainstorm_sessions",
    ),
    (
        "20260525_brainstorm_sessions_add_action_items",
        "ALTER TABLE brainstorm_sessions ADD COLUMN action_items TEXT DEFAULT NULL",
        "brainstorm_sessions",
    ),
    # ── 2026-05-30: recurring tasks + subtasks ──
    (
        "20260530_tasks_add_recurrence",
        "ALTER TABLE tasks ADD COLUMN recurrence TEXT DEFAULT ''",
        "tasks",
    ),
    (
        "20260530_tasks_add_parent_task_id",
        "ALTER TABLE tasks ADD COLUMN parent_task_id TEXT DEFAULT ''",
        "tasks",
    ),
    # Future migrations append here. Never modify or delete an existing entry —
    # only add new ones. To revert, write a forward-only "down" migration.
]


def _ensure_history_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _schema_migrations (
            name        TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
            sql         TEXT NOT NULL DEFAULT ''
        )
        """
    )


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def _column_for(sql: str) -> str | None:
    """Extract column name from 'ALTER TABLE ... ADD COLUMN <name> ...'."""
    upper = sql.upper()
    idx = upper.find("ADD COLUMN")
    if idx < 0:
        return None
    rest = sql[idx + len("ADD COLUMN") :].strip().split()
    return rest[0] if rest else None


def run_migrations(db_path: Path | str) -> dict:
    """
    Apply any pending schema migrations. Idempotent.

    Returns:
        {"applied": [names...], "skipped": [names...], "errors": [(name, msg)...]}
    """
    db_path = Path(db_path)
    if not db_path.exists():
        # No DB yet — nothing to migrate. The first tool to use it will create it.
        return {"applied": [], "skipped": [], "errors": []}

    applied: list[str] = []
    skipped: list[str] = []
    errors: list[tuple[str, str]] = []

    with sqlite3.connect(str(db_path)) as conn:
        _ensure_history_table(conn)
        already = {row[0] for row in conn.execute("SELECT name FROM _schema_migrations")}

        for name, sql, table in MIGRATIONS:
            if name in already:
                skipped.append(name)
                continue

            col = _column_for(sql)
            if col and col in _table_columns(conn, table):
                # Column already exists (e.g. created manually before this runner shipped).
                # Mark as applied without re-running, so it's not retried forever.
                conn.execute(
                    "INSERT OR IGNORE INTO _schema_migrations (name, sql) VALUES (?, ?)",
                    (name, sql + "  -- skipped (column already present)"),
                )
                conn.commit()
                skipped.append(name)
                continue

            try:
                conn.execute(sql)
                conn.execute(
                    "INSERT OR IGNORE INTO _schema_migrations (name, sql) VALUES (?, ?)",
                    (name, sql),
                )
                conn.commit()
                applied.append(name)
            except sqlite3.OperationalError as e:
                # Soft-fail: log the error but don't crash the server.
                # Most likely cause: the table itself doesn't exist yet
                # (it gets created lazily by another tool). Migration will retry on next start.
                errors.append((name, str(e)))

    return {"applied": applied, "skipped": skipped, "errors": errors}


def run_on_default_db() -> dict:
    """Convenience: locate the default db via `metis_mcp.config.paths` and migrate."""
    try:
        from metis_mcp.config import paths
        return run_migrations(paths.db)
    except Exception:
        return {"applied": [], "skipped": [], "errors": [("loader", "could not locate paths.db")]}


if __name__ == "__main__":
    # Run standalone — useful for installer scripts and manual upgrades.
    import json
    result = run_on_default_db()
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)
