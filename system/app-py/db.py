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

import logging
import asyncio
import os
import re
import sqlite3
from pathlib import Path


# NOTE: the two helpers below are intentionally duplicated verbatim in the MCP
# server's system/mcp-server/src/metis_mcp/config.py. Both processes must resolve
# the live DB to the SAME location, and the two codebases don't share a module.
# Keep them in sync.

def _is_usable_db(path: Path) -> bool:
    """True only if `path` is a real SQLite DB with actual content.

    Guards the migration source. `path.exists()` is dangerously insufficient: a
    0-byte file opens as a VALID EMPTY SQLite database, so migrating from one
    silently produces an empty Metis — every note, paper and memory apparently
    gone, with no error anywhere. Require: non-empty file, readable header, and at
    least one table.
    """
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
    except OSError:
        return False

    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tables = con.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            return bool(tables)
        finally:
            con.close()
    except sqlite3.DatabaseError:
        return False


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

    # .exists() is NOT enough: SQLite opens a 0-byte file as a valid EMPTY DB, so a
    # fresh install / restore would "migrate" from the OneDrive-orphan 0-byte artifact
    # and come up with all memory silently gone. Require a proven-USABLE source. This
    # mirrors resolve_live_db() in the MCP server's config.py — keep them in sync.
    source = next((p for p in (onedrive, legacy) if _is_usable_db(p)), None)
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
    except (OSError, sqlite3.DatabaseError) as exc:
        # OSError covers FileNotFoundError + a read-only/full data dir (mkdir in
        # get_db_path); sqlite3.DatabaseError covers OperationalError ("database is
        # locked") AND "database disk image is malformed" (corruption). Degrade to
        # the default instead of 500-ing every panel.
        #
        # BUT NEVER SILENTLY. Degrading turns a broken query into a plausible empty
        # state, and an empty state is indistinguishable from "you have nothing".
        # That is exactly how a missing `tasks.priority` column made the Work
        # surface announce "No open tasks across any project" while 79 open tasks
        # sat in the table, for as long as nobody counted the rows by hand
        # (found 2026-08-12). A malformed query is a bug in us; a locked database is
        # a passing condition. Log the first loudly, the second quietly.
        _msg = str(exc)
        logging.getLogger("metis.db").log(
            logging.WARNING if "locked" in _msg.lower() else logging.ERROR,
            "query degraded to its default (%s): %s | SQL: %s",
            type(exc).__name__, _msg, " ".join(sql.split())[:200],
        )
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
    except (OSError, sqlite3.DatabaseError) as exc:
        # OSError covers FileNotFoundError + a read-only/full data dir (mkdir in
        # get_db_path); sqlite3.DatabaseError covers OperationalError ("database is
        # locked") AND "database disk image is malformed" (corruption). Degrade to
        # the default instead of 500-ing every panel.
        #
        # BUT NEVER SILENTLY. Degrading turns a broken query into a plausible empty
        # state, and an empty state is indistinguishable from "you have nothing".
        # That is exactly how a missing `tasks.priority` column made the Work
        # surface announce "No open tasks across any project" while 79 open tasks
        # sat in the table, for as long as nobody counted the rows by hand
        # (found 2026-08-12). A malformed query is a bug in us; a locked database is
        # a passing condition. Log the first loudly, the second quietly.
        _msg = str(exc)
        logging.getLogger("metis.db").log(
            logging.WARNING if "locked" in _msg.lower() else logging.ERROR,
            "query degraded to its default (%s): %s | SQL: %s",
            type(exc).__name__, _msg, " ".join(sql.split())[:200],
        )
        return default


def db_execute(sql: str, params=()) -> None:
    """Execute a write statement (INSERT/UPDATE/DELETE) with auto-commit."""
    conn = _connect()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


# ── WHAT COUNTS AS LIVE WORK ─────────────────────────────────────────────────
# One definition, because three were in use at once and each surface had quietly
# invented its own. Measured 2026-09-03 on a real store of 123 task rows:
#
#   status != 'done'                → 92   counts abandoned work as backlog
#   status = 'open'                 → 56   drops work that is merely held
#   status NOT IN ('done','cancel') → 58   ← what a person means by "open"
#
# The middle two differ by two rows, and those two rows are the point: a task
# nobody can act on yet is still a task, and a board that hides it is how it
# gets forgotten. The first differs by thirty-four, which is how a heading came
# to advertise more work than existed.
#
# Cancelled is not a kind of open. It is a decision already taken.
LIVE_STATUSES: tuple[str, ...] = ("open", "blocked", "in_progress")
DEAD_STATUSES: tuple[str, ...] = ("done", "cancelled")


def live_task_sql(col: str = "status") -> str:
    """A SQL predicate for "this task is still live work".

    Phrased as an exclusion rather than an inclusion on purpose. A status this
    code has never heard of should surface as work to look at, not vanish — an
    inclusion list silently swallows every value added after it was written,
    and a task you cannot see is worse than one filed oddly.
    """
    return f"COALESCE({col},'') NOT IN ('done','cancelled')"


def record_token_usage(agent_slug: str, model: str, input_tokens, output_tokens,
                       task_summary: str = "", session_id: str = "") -> None:
    """Record a REAL API call's token usage into agent_runs (Keystone B6.3) so the
    dashboard token monitor reflects actual spend instead of ~0. Call this right after
    any Anthropic API response with usage. Best-effort; never raises. Pass session_id
    only for session-scoped agent work — leave empty for background calls (briefs,
    news) so they feed the token totals without cluttering per-session 'who did what'."""
    try:
        import datetime as _dt
        db_execute(
            "INSERT INTO agent_runs (agent_slug, task_summary, status, created_at, "
            "input_tokens, output_tokens, model, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_slug or "metis", (task_summary or "")[:200], "completed",
             _dt.datetime.now().isoformat(), int(input_tokens or 0), int(output_tokens or 0),
             model or "", session_id or ""),
        )
    except Exception:
        pass


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

    # Strip `--` comments BEFORE matching table bodies.
    #
    # The block matcher below is non-greedy up to `);`, so it ends a table body at
    # the FIRST `);` in the text — including one inside a comment. A perfectly
    # ordinary explanatory line like
    #     -- entry_kind = what it is (article/review/report); lane = where it goes
    # therefore truncated `new_publications` after its third-from-last column, and
    # every column below the comment silently stopped being migrated. Found while
    # fixing exactly that table on 2026-08-24: the file said the columns existed,
    # the parser never saw them, and nothing reported a problem.
    #
    # Comments carry no schema, so removing them first costs nothing and makes the
    # file safe to document. Done line-wise on `--` only; schema.sql has no string
    # literals containing `--`, and a stray one would merely truncate that line.
    schema_sql = "\n".join(
        line.split("--", 1)[0].rstrip() if "--" in line else line
        for line in schema_sql.splitlines()
    )
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
    except (OSError, sqlite3.DatabaseError):
        # A read-only/full data dir (mkdir in get_db_path), a locked DB, or a
        # corrupt DB must not crash startup — migrations are best-effort and retried
        # next boot. (main.py calls this in the lifespan; an escape here would fail
        # uvicorn startup and trigger the supervisor's give-up-after-8 path.)
        pass

    return changes


# ---------------------------------------------------------------------------
# How close is "close to my work"
# ---------------------------------------------------------------------------
# ONE AUTHOR. This lived as three different numbers — 0.68 in the news card,
# 0.60 in the hero query, and a comment asserting 0.64 — for one idea, so the
# same paper was "close to my work" on one surface and not on another.
#
# CALIBRATED 2026-09-05 against 300 sampled papers scored by the weighted
# profile, with control probes that had to separate before the distribution was
# read at all:
#
#     his own subject   0.713 – 0.767
#     a course subject  0.708
#     an epi method     0.671      <- "occasionally epidemiology" lands here
#     generic public health 0.576
#     unrelated         0.529 – 0.583
#
# 0.66 sits below everything of his own and above generic public-health
# writing, admitting a strong methods paper and rejecting a weak one. It cuts
# the feed to roughly the top sixth; the previous 0.64, on the older unweighted
# profile, admitted 62% of everything — a filter that passes two thirds of what
# it sees is not filtering.
#
# THIS NUMBER IS ONLY MEANINGFUL AGAINST WEIGHTED SCORES. Rows scored by the
# old profile are on a different scale and must be re-scored before it applies
# (tools/rescore_relevance.py).
RELEVANCE_CLOSE: float = 0.66
