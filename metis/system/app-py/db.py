"""
db.py — SQLite helper for the Metis dashboard.
"""

import os
import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    """Find metis.sqlite.

    Search order:
    1. METIS_RC_ROOT env var → {root}/system/app/data/metis.sqlite
    2. Path relative to this file: ./data/metis.sqlite
    Raises FileNotFoundError if neither exists.
    """
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        candidate = Path(rc_root) / "system" / "app" / "data" / "metis.sqlite"
        if candidate.exists():
            return candidate

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


def db_query(sql: str, params=()) -> list[dict]:
    """Execute a SELECT query and return a list of dicts."""
    try:
        conn = _connect()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    except FileNotFoundError:
        return []


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
