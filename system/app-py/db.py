"""
db.py — SQLite helper for the Metis dashboard.

Stability notes (June 2026):
  - WAL mode is enabled on every connection so the MCP server and dashboard
    can read/write concurrently without "database is locked" errors.
  - busy_timeout is set to 10 s so SQLite retries instead of failing
    immediately when another process holds a write lock.
  - Async wrappers (adb_query, adb_scalar, adb_execute) run the blocking
    SQLite calls in a thread pool so FastAPI's event loop is never blocked.
"""

import asyncio
import os
import re
import sqlite3
from pathlib import Path


# NOTE: the two helpers below are intentionally duplicated verbatim in the MCP
# server's system/mcp-server/src/metis_mcp/config.py. Both processes must resolve
# the live DB to the SAME location, and the two codebases don't share a module.
# Keep them in sync.

def _migrate_db_to_local(source: Path, dest: Path) -> bool:
    """One-time copy of the live DB to local disk via SQLite's backup API.

    The backup API yields a transactionally consistent copy even while the source
    is open/in WAL mode, and ignores the -wal/-shm sidecars (so OneDrive corruption
    can't ride along). Atomic via temp file + os.replace; idempotent. Returns True
    if dest exists afterwards.
    """
    import tempfile

    if dest.exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=str(dest.parent), suffix=".migrating")
        os.close(fd)
        src_conn = sqlite3.connect(str(source), timeout=30)
        try:
            dst_conn = sqlite3.connect(tmp)
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
        finally:
            src_conn.close()
        os.replace(tmp, dest)
        return True
    except Exception:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return False


def get_db_path() -> Path:
    """Resolve the live metis.sqlite path.

    Stability fix (2026-06-19): the live DB must NOT sit on a OneDrive/DrvFs path —
    OneDrive sync deletes/corrupts SQLite's WAL sidecar files mid-write, which takes
    the whole app down (see outputs/reviews/software-engineer/2026-06-19_metis-
    stability-evaluation.md). So the canonical live DB lives on fast local disk
    (~/.local/share/metis/), and an existing OneDrive DB is auto-migrated there on
    first run. OneDrive keeps only the nightly backups.

    Honored as-is: METIS_DB (tests/demo) and Docker volumes (METIS_DOCKER=1).
    """
    explicit = os.environ.get("METIS_DB", "")
    if explicit:
        p = Path(explicit)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # Root: METIS_RC_ROOT, else inferred relative to this file (system/app-py/db.py
    # → repo root is two levels up).
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    root = Path(rc_root) if rc_root else Path(__file__).resolve().parent.parent.parent

    onedrive = root / "system" / "app" / "data" / "metis.sqlite"
    legacy = root / "system" / "app-py" / "data" / "metis.sqlite"

    # Docker: the mounted volume IS the durable store — never relocate.
    if os.environ.get("METIS_DOCKER") == "1":
        return onedrive

    data_dir = Path(
        os.environ.get("METIS_DATA_DIR")
        or (Path.home() / ".local" / "share" / "metis")
    )
    local = data_dir / "metis.sqlite"
    if local.exists():
        return local

    source = onedrive if onedrive.exists() else (legacy if legacy.exists() else None)
    if source is not None and _migrate_db_to_local(source, local):
        return local
    # Fresh install (no existing DB) → create on local disk.
    data_dir.mkdir(parents=True, exist_ok=True)
    return local


def _connect() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    # WAL mode allows concurrent reads during writes (dashboard + MCP server).
    # busy_timeout tells SQLite to retry for up to 10 s before raising
    # "database is locked" — critical when the MCP server is writing.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
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
# Async wrappers — use these from FastAPI async route handlers so the event
# loop is never blocked by SQLite I/O. Under the hood they call the sync
# functions above via asyncio.to_thread() (Python 3.9+ thread pool).
# ---------------------------------------------------------------------------


async def adb_query(sql: str, params=(), default=None) -> list[dict]:
    return await asyncio.to_thread(db_query, sql, params, default)


async def adb_scalar(sql: str, params=(), default=0):
    return await asyncio.to_thread(db_scalar, sql, params, default)


async def adb_execute(sql: str, params=()) -> None:
    return await asyncio.to_thread(db_execute, sql, params)


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
