"""Path resolution and environment variable handling for the Metis Research Cortex (RC)."""

import os
from pathlib import Path


def _infer_root() -> Path:
    """Infer RC root from server location: repo root (5 levels up from src/metis_mcp/config.py)."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def get_root() -> Path:
    """Return the RC root directory, from METIS_RC_ROOT env var or inferred."""
    env = os.environ.get("METIS_RC_ROOT") or os.environ.get("METIS_PKM_ROOT")
    if env:
        return Path(env).resolve()
    return _infer_root()


def load_env_file() -> list[str]:
    """Load `system/.env` into os.environ. Returns the names of keys it set.

    The dashboard's run.sh sources system/.env; the MCP server's run.sh never did.
    So inside the MCP process ANTHROPIC_API_KEY was simply NOT SET — and every
    feature that needs the Claude API silently took its degraded path instead of
    failing. The most visible casualty was the weekly self-improvement loop: its
    semantic theme extraction (Claude Haiku) could never run, so it *always* fell
    through to word-frequency counting and produced proposals like
    "Recurring themes: test (4), library (2)". The capability existed; the key
    never reached it. (Found 2026-07-14.)

    Existing environment variables always win — this only fills gaps.
    """
    loaded: list[str] = []
    env_path = get_root() / "system" / ".env"
    try:
        if not env_path.is_file():
            return loaded
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if not key or not value:
                continue
            if os.environ.get(key):
                continue  # never override a real environment variable
            os.environ[key] = value
            loaded.append(key)
    except OSError:
        pass
    return loaded


# NOTE: the two helpers below are intentionally duplicated verbatim in the
# dashboard's system/app-py/db.py. Both processes must resolve the live DB to the
# SAME location, and the two codebases don't share a module. Keep them in sync.

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

    import sqlite3

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
    import sqlite3
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


def resolve_live_db(root: Path) -> Path:
    """Resolve the live metis.sqlite path.

    Stability fix (2026-06-19): the live DB must NOT sit on a OneDrive/DrvFs path —
    OneDrive sync deletes/corrupts SQLite's WAL sidecar files mid-write, which takes
    the whole app down (see outputs/reviews/software-engineer/2026-06-19_metis-
    stability-evaluation.md). So the canonical live DB lives on fast local disk
    (~/.local/share/metis/), and an existing OneDrive DB is auto-migrated there on
    first run. OneDrive keeps only the nightly backups.

    Honored as-is: METIS_DB (tests/demo) and Docker volumes (METIS_DOCKER=1).
    """
    env = os.environ.get("METIS_DB")
    if env:
        p = Path(env)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

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

    # .exists() is NOT enough. SQLite opens a 0-BYTE file as a perfectly valid,
    # perfectly EMPTY database — no error, and .backup() succeeds. There is such a
    # file at system/app/data/metis.sqlite (an artifact of the OneDrive orphan
    # cleanup), so a fresh install / restore / new machine would have "migrated"
    # from it and come up with all memory silently gone. A migration source must be
    # proven USABLE, not merely present.
    source = next(
        (p for p in (onedrive, legacy) if _is_usable_db(p)),
        None,
    )
    if source is not None and _migrate_db_to_local(source, local):
        return local
    # Fresh install (no existing DB) → create on local disk.
    data_dir.mkdir(parents=True, exist_ok=True)
    return local


class Paths:
    """Central path registry for the Metis Research Context."""

    def __init__(self, root: Path | None = None):
        self.root = root or get_root()
        self.agents = self.root / "agents"
        self.research = self.root / "knowledge" / "domains" / "research"
        self.domains = self.root / "knowledge" / "domains"
        self.projects_active = self.root / "projects" / "active"
        self.literature_metadata = (
            self.root
            / "inputs"
            / "literature"
            / "metadata"
        )
        self.library = self.root / "knowledge" / "library"
        self.reviews = self.root / "outputs" / "reviews"
        self.config = self.root / "system" / "config"
        # Live DB resolves to local disk (off OneDrive); see resolve_live_db.
        # Honors METIS_DB (tests/demo) and Docker volumes. Auto-migrates an
        # existing OneDrive DB to local disk on first run.
        self.db = resolve_live_db(self.root)


# Singleton instance
paths = Paths()
