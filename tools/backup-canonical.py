#!/usr/bin/env python3
"""
backup-canonical.py — plain snapshot of the canonical live DB to OneDrive.

Closes the data-persistence gap (see system/config/data-persistence-strategy.md):
the live DB sits on the native filesystem (~/.local/share/metis/), deliberately OFF
OneDrive because SQLite's WAL + OneDrive sync corrupts it. That keeps it safe from
corruption but un-synced — not recoverable if the disk dies.

A STATIC snapshot has no WAL, so OneDrive can sync it safely. We keep it UNENCRYPTED
on purpose: OneDrive is considered safe enough, and an encrypted backup whose key is
lost is just unrecoverable data. No key, no key-loss risk — the backup is always
restorable by copying the file back.

  1. consistent snapshot of the canonical DB (sqlite backup API — checkpoints WAL)
  2. write it to the OneDrive-synced backup dir, prune old ones

Run:  "$HOME/.local/share/metis-mcp/.venv/bin/python3" tools/backup-canonical.py
Schedule daily (dashboard scheduler / cron). Restore: copy the file back to paths.db.
"""

import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))
from metis_mcp.config import paths  # noqa: E402

DB = Path(str(paths.db))
ONEDRIVE_BACKUPS = ROOT / "system" / "app" / "data" / "cloud-backups"  # OneDrive-synced, git-ignored
KEEP = 14


def main():
    if not DB.exists():
        print(f"No canonical DB at {DB} — nothing to back up.")
        sys.exit(1)
    ONEDRIVE_BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    snap = Path("/tmp") / f"metis-snap-{stamp}.sqlite"

    # 1 — consistent snapshot to a temp file (checkpoints WAL → a clean static copy).
    src = sqlite3.connect(str(DB))
    dst = sqlite3.connect(str(snap))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    # 2 — move the complete static file onto OneDrive (cloud-recoverable). Moving the
    # FINISHED file (not writing live) means OneDrive never sees a half-written DB.
    target = ONEDRIVE_BACKUPS / f"metis-{stamp}.sqlite"
    shutil.move(str(snap), str(target))  # shutil.move crosses filesystems (/tmp → OneDrive)

    # 3 — prune
    backups = sorted(ONEDRIVE_BACKUPS.glob("metis-*.sqlite"))
    for old in backups[:-KEEP]:
        old.unlink(missing_ok=True)

    size = target.stat().st_size // 1024
    print(f"  ✓ backup → {target.relative_to(ROOT)} ({size}KB) · kept {min(len(backups), KEEP)} of last {KEEP}")
    print("  cloud-recoverable via OneDrive — no key needed; restore by copying the file back to the live DB path.")


if __name__ == "__main__":
    main()
