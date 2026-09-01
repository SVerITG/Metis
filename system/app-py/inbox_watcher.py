"""
inbox_watcher.py — Watchdog-based file watcher for the Metis inbox.

Polls <RC_ROOT>/inbox/ every 5 seconds using watchdog's polling observer
(NTFS/OneDrive compatible — inotify is not). On any new file:
  1. Logs the file to the inbox_items table in SQLite.
  2. Attempts to route by file extension:
       .pdf, .docx, .txt → literature or note (logged for Librarian pickup)
       .mp3, .wav, .m4a  → meeting transcript (logged for Meeting Memory pickup)
       *                 → generic inbox item

New files appear as items in the dashboard Inbox section. They are not
auto-deleted — the researcher or an agent decides what to do with them.
"""

import datetime
import logging
import os
import sqlite3
from pathlib import Path
from threading import Thread

log = logging.getLogger("metis.inbox_watcher")

# The ONE definition of inbox_items. It lives here because this module is the
# table's owner, and `ensure_inbox_table()` below is exported so every other
# writer uses the same shape instead of inventing one.
#
# It had to become shared (2026-08-24). The nightly `inbox_process` job wrote to
# this table with a completely different set of column names — source_path / type
# / logged_at against filepath / file_type / created_at — and never created the
# table at all. Two consequences, both silent:
#   · the table did not exist on this machine, so every INSERT raised inside a
#     bare `except Exception: pass` and the job reported "0 new items — ok";
#   · had the watcher created it first, the job's INSERT would have failed
#     forever against the real columns, still reporting success.
# Nothing surfaced either one. A second spelling of a schema is a second schema.
_DDL = """
CREATE TABLE IF NOT EXISTS inbox_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    filepath    TEXT NOT NULL,
    file_type   TEXT DEFAULT 'unknown',
    status      TEXT DEFAULT 'new',
    created_at  TEXT NOT NULL
)
"""

# Idempotency belongs in the schema, not in each caller's SELECT-then-INSERT.
# With this, `INSERT OR IGNORE` is genuinely a no-op on a file already seen —
# including when the watcher and the nightly job race on the same file.
_DDL_INDEX = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_inbox_items_filepath "
    "ON inbox_items(filepath)"
)


def ensure_inbox_table(con: sqlite3.Connection) -> None:
    """Create inbox_items and its uniqueness guarantee. Safe to call repeatedly."""
    con.execute(_DDL)
    try:
        con.execute(_DDL_INDEX)
    except sqlite3.IntegrityError:
        # A pre-existing table already holds duplicate filepaths (older installs
        # deduped in Python). Leave the rows alone — dropping or merging them is
        # the user's data, not ours to decide. The table still works.
        log.warning("[inbox_watcher] duplicate filepaths present — "
                    "unique index not applied")

_LITERATURE_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".bib", ".ris"}
_AUDIO_EXTS      = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
_IMAGE_EXTS      = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff"}


def _classify(suffix: str) -> str:
    s = suffix.lower()
    if s in _LITERATURE_EXTS:
        return "literature"
    if s in _AUDIO_EXTS:
        return "audio"
    if s in _IMAGE_EXTS:
        return "image"
    if s in {".pptx", ".ppt"}:
        return "presentation"
    if s in {".json", ".csv", ".xlsx", ".xls"}:
        return "data"
    return "file"


def _log_to_db(db_path: str, filepath: Path) -> None:
    con = None
    try:
        # No timeout and no close-on-error, until 2026-09-01: any exception
        # between here and the `con.close()` below abandoned an open connection
        # mid-DDL, and `ensure_inbox_table` is DDL — which takes the write lock.
        con = sqlite3.connect(db_path, timeout=30)
        con.execute("PRAGMA busy_timeout=30000")
        ensure_inbox_table(con)
        now = datetime.datetime.now().isoformat()
        file_type = _classify(filepath.suffix)
        cur = con.execute(
            "INSERT OR IGNORE INTO inbox_items "
            "(filename, filepath, file_type, status, created_at) "
            "VALUES (?, ?, ?, 'new', ?)",
            (filepath.name, str(filepath), file_type, now),
        )
        con.commit()
        if cur.rowcount:
            log.info("[inbox_watcher] logged %s (%s)", filepath.name, file_type)
    except Exception as e:
        log.warning("[inbox_watcher] DB write failed: %s", e)
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass


def _poll_inbox(inbox_dir: Path, db_path: str, interval: int = 5) -> None:
    """Simple polling loop — avoids watchdog import issues on some NTFS mounts."""
    seen: set[Path] = set()
    # Seed with already-present files so they don't trigger on first run
    try:
        for p in inbox_dir.iterdir():
            if p.is_file() and not p.name.startswith("."):
                seen.add(p)
    except Exception:
        pass

    import time
    while True:
        try:
            current = {
                p for p in inbox_dir.iterdir()
                if p.is_file() and not p.name.startswith(".")
            }
            new_files = current - seen
            for f in sorted(new_files):
                _log_to_db(db_path, f)
            seen = current
        except Exception as e:
            log.warning("[inbox_watcher] scan error: %s", e)
        time.sleep(interval)


def start_inbox_watcher() -> bool:
    """Start the inbox watcher background thread.

    Returns True if started, False if RC_ROOT or DB path is missing.
    Called from main.py lifespan on dashboard startup.
    """
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if not rc_root:
        log.warning("[inbox_watcher] METIS_RC_ROOT not set — watcher disabled")
        return False

    inbox_dir = Path(rc_root) / "inbox"
    try:
        inbox_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.warning("[inbox_watcher] could not create inbox dir: %s", e)
        return False

    db_path = os.environ.get("METIS_DB", "")
    if not db_path:
        try:
            from db import get_db_path
            db_path = str(get_db_path())
        except Exception:
            db_path = str(Path(rc_root) / "system" / "app" / "data" / "metis.sqlite")

    t = Thread(
        target=_poll_inbox,
        args=(inbox_dir, db_path, 5),
        daemon=True,
        name="inbox-watcher",
    )
    t.start()
    log.info("[inbox_watcher] started — watching %s", inbox_dir)
    return True
