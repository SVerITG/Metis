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
    if s in {".json", ".csv", ".xlsx", ".xls"}:
        return "data"
    return "file"


def _log_to_db(db_path: str, filepath: Path) -> None:
    try:
        con = sqlite3.connect(db_path)
        con.execute(_DDL)
        now = datetime.datetime.now().isoformat()
        file_type = _classify(filepath.suffix)
        # Only insert if not already tracked (idempotent on re-watch)
        existing = con.execute(
            "SELECT id FROM inbox_items WHERE filepath = ? LIMIT 1",
            (str(filepath),),
        ).fetchone()
        if not existing:
            con.execute(
                "INSERT INTO inbox_items (filename, filepath, file_type, status, created_at) "
                "VALUES (?, ?, ?, 'new', ?)",
                (filepath.name, str(filepath), file_type, now),
            )
            con.commit()
            log.info("[inbox_watcher] logged %s (%s)", filepath.name, file_type)
        con.close()
    except Exception as e:
        log.warning("[inbox_watcher] DB write failed: %s", e)


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
