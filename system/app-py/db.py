"""
db.py — SQLite helper for the Metis dashboard.
"""

import os
import re
import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    """Find metis.sqlite.

    Search order:
    1. METIS_DB env var — explicit override (used by run-demo.sh for demo mode)
    2. METIS_RC_ROOT env var → {root}/system/app/data/metis.sqlite
    3. Path relative to this file: ./data/metis.sqlite
    Raises FileNotFoundError if neither exists.
    """
    explicit = os.environ.get("METIS_DB", "")
    if explicit:
        p = Path(explicit)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        # When METIS_RC_ROOT is set (e.g. Docker containers), always use it.
        # CANONICAL path is system/app/data/metis.sqlite — the same file the MCP
        # server uses (metis_mcp.config.paths.db) and the installer initialises.
        # (Previously this pointed at system/app-py/data, which split the dashboard
        # onto a separate empty DB while all real data lived in app/data.)
        canonical = Path(rc_root) / "system" / "app" / "data" / "metis.sqlite"
        if canonical.exists():
            return canonical
        # Legacy fallback: a pre-fix install that wrote real data to app-py/data.
        legacy = Path(rc_root) / "system" / "app-py" / "data" / "metis.sqlite"
        if legacy.exists():
            return legacy
        # Neither exists yet → initialise at the canonical location.
        canonical.parent.mkdir(parents=True, exist_ok=True)
        return canonical

    local_candidate = Path(__file__).parent / "data" / "metis.sqlite"
    if local_candidate.exists():
        return local_candidate

    raise FileNotFoundError(
        "metis.sqlite not found. Set METIS_RC_ROOT or place the DB at "
        f"{local_candidate}"
    )


def _connect() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def db_query(sql: str, params=(), default=None) -> list[dict]:
    """Execute a SELECT query and return a list of dicts."""
    if default is None:
        default = []
    try:
        conn = _connect()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    except (FileNotFoundError, sqlite3.OperationalError):
        return default


def db_scalar(sql: str, params=(), default=0):
    """Execute a query that returns a single scalar value.

    Returns *default* if no rows are found or an error occurs.
    """
    try:
        conn = _connect()
        try:
            cursor = conn.execute(sql, params)
            row = cursor.fetchone()
            if row is None:
                return default
            return row[0] if row[0] is not None else default
        finally:
            conn.close()
    except (FileNotFoundError, sqlite3.OperationalError):
        return default


def db_execute(sql: str, params=()) -> None:
    """Execute a write statement (INSERT/UPDATE/DELETE) with auto-commit."""
    conn = _connect()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema migrations — safe to call on every startup
# ---------------------------------------------------------------------------

_CONSTRAINT_PREFIXES = frozenset(
    ("primary", "unique", "foreign", "check", "constraint")
)


def run_migrations() -> list[str]:
    """Apply any missing tables or columns from schema.sql to the live database.

    Reads the canonical schema.sql, creates any tables that don't exist yet,
    and adds any columns missing from existing tables. Never drops or renames
    anything, so it is safe to run on every startup after a git pull.

    Returns a list of changes applied (empty if nothing was needed).
    """
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        schema_path = Path(rc_root) / "system" / "installer" / "schema.sql"
    else:
        schema_path = Path(__file__).parent.parent / "installer" / "schema.sql"

    if not schema_path.exists():
        return []

    schema_sql = schema_path.read_text(encoding="utf-8")
    changes: list[str] = []

    try:
        db_path = get_db_path()
        conn = sqlite3.connect(str(db_path))

        for block in re.finditer(
            r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((.+?)\);",
            schema_sql,
            re.IGNORECASE | re.DOTALL,
        ):
            table = block.group(1)
            body = block.group(2)

            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({body})")

            cur = conn.execute(f"PRAGMA table_info({table})")
            live_cols = {row[1].lower() for row in cur.fetchall()}

            for raw_line in body.splitlines():
                line = raw_line.strip().rstrip(",")
                if not line or line.startswith("--"):
                    continue
                tokens = line.split()
                if not tokens:
                    continue
                first = tokens[0].lower()
                if first in _CONSTRAINT_PREFIXES:
                    continue
                if not re.match(r"^[a-z_]\w*$", first):
                    continue
                if first not in live_cols:
                    try:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {line}")
                        changes.append(f"{table}.{first}")
                    except sqlite3.OperationalError:
                        pass

        conn.commit()
        conn.close()
    except (FileNotFoundError, sqlite3.OperationalError):
        pass

    return changes
