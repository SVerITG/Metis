#!/usr/bin/env python3
"""metis-sync-db.py — converge Metis's memory across two computers, safely.

THE PROBLEM
    Stan works from two machines. The CODE syncs (git + the OneDrive folder), but
    the DATABASE does not: this machine's memory stopped at 8 July while the other
    had 8-13 July. Sessions, agent runs, ideas and reflexions diverged silently.

WHY THE LIVE DB IS NOT SIMPLY PUT ON ONEDRIVE
    It was, and OneDrive destroyed it (2026-06-19). A live SQLite database is
    THREE files — .sqlite, -wal, -shm — that must stay mutually consistent.
    OneDrive copied them at different instants, mid-write, and the result was a
    corrupt database. That is why the live DB was moved to the native filesystem.

    But the lesson is narrower than "SQLite and OneDrive don't mix". It is:

        ** OneDrive must never touch a file that is being WRITTEN. **

    A finished, static snapshot has no WAL and no writer. It is just bytes. That
    is provably safe on OneDrive — tools/backup-canonical.py has been doing it
    correctly all along (snapshot to /tmp via the SQLite backup API, then MOVE the
    completed file across, so OneDrive never sees a half-written database).

THE DESIGN
    live DB (local, native FS)  ──export──▶  immutable snapshot on OneDrive
                                                     │
    live DB (other machine)     ◀──merge───────────── ┘

    * The live database NEVER goes on OneDrive. That rule is unchanged.
    * OneDrive carries only finished, hostname-stamped snapshots.
    * Each machine merges the snapshots the OTHER machines left behind.
    * Convergence is eventual, and that is fine: this is memory, not a ledger.

WHY THE MERGE IS SAFE
    The tables we merge are append-only event logs. Union is the correct operation
    — there is no conflict to resolve, only rows one machine has not seen yet.

    The one real trap: every table has an autoincrement `id`, and those COLLIDE
    across machines (both have an episodic_memory id=5, meaning different things).
    So rows are identified by a CONTENT FINGERPRINT — a hash of every column
    except the local id. Merging is therefore idempotent: re-importing the same
    snapshot inserts nothing.

    Mutable, stateful tables (tasks, projects) are deliberately NOT merged. They
    would need real conflict resolution, and getting that subtly wrong is worse
    than not doing it. See SKIPPED below.

    Newly merged memory has no embedding — the nightly `embedding_backfill` job
    reconciles that automatically, so semantic recall picks the rows up on its own.

USAGE
    python3 tools/metis-sync-db.py            # export ours, merge theirs
    python3 tools/metis-sync-db.py --status   # what's out there, what's merged
    python3 tools/metis-sync-db.py --dry-run  # show what WOULD be merged
    python3 tools/metis-sync-db.py --import-only / --export-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

from metis_mcp.config import paths  # noqa: E402

SNAPSHOTS = ROOT / "system" / "app" / "data" / "cloud-backups"  # OneDrive-synced
HOST = "".join(c if c.isalnum() else "-" for c in platform.node()) or "unknown"
KEEP_PER_HOST = 7

# ── What we merge ────────────────────────────────────────────────────────────
# Append-only logs, each self-contained (nothing else joins to their `id`).
MERGE_TABLES = [
    "episodic_memory",
    "semantic_memory",
    "procedural_memory",
    "session_summaries",
    "agent_runs",
    "memory_entries",
    "reflexion_log",
    "ideas",
    "journal_entries",
    "personal_notes",
    "user_decisions",
    "skill_improvement_proposals",
    "literature_metadata",
    "contacts",
]

# ── What we deliberately DON'T merge, and why ────────────────────────────────
SKIPPED = {
    "tasks / projects":     "mutable state — needs real conflict resolution, not a union",
    "note_links / idea_links": "foreign keys to ids that differ per machine — a union would mis-link",
    "tracked_files":        "machine-local filesystem paths",
    "jobs_log":             "machine-local scheduler noise",
    "pdf_chunks / library_*": "large and regenerable — the PDFs themselves already sync via OneDrive",
    "vec_* (embeddings)":   "rebuilt locally by the nightly embedding_backfill job",
}

_SYNC_STATE_DDL = """
CREATE TABLE IF NOT EXISTS db_sync_state (
    snapshot   TEXT PRIMARY KEY,   -- filename of the snapshot we merged
    host       TEXT NOT NULL,      -- which machine produced it
    merged_at  TEXT NOT NULL,
    rows_added INTEGER NOT NULL DEFAULT 0
)
"""


def _connect(path: Path, readonly: bool = False) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro" if readonly else f"file:{path}"
    con = sqlite3.connect(uri, uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    if not readonly:
        con.execute("PRAGMA busy_timeout=30000")
    return con


def _pk_of(con: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in con.execute(f"PRAGMA table_info({table})") if r["pk"]}


def _columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]


def _fingerprint(row: sqlite3.Row, cols: list[str]) -> str:
    """Machine-independent identity: hash the CONTENT, never the local id.

    Autoincrement ids collide across machines — both computers have an
    episodic_memory id=5 meaning entirely different things. Hashing the content is
    what makes the merge idempotent and safe to re-run.
    """
    payload = json.dumps(
        [("" if row[c] is None else str(row[c])) for c in cols],
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Export ───────────────────────────────────────────────────────────────────

def export_snapshot(verbose: bool = True) -> Path | None:
    """Write a consistent, static snapshot of the live DB to OneDrive.

    Snapshot to /tmp with the SQLite backup API (which checkpoints the WAL), then
    MOVE the finished file. OneDrive therefore only ever sees a complete database —
    never a half-written one. This is the property whose absence corrupted the DB.
    """
    if not paths.db.exists():
        print("  no live DB — nothing to export")
        return None

    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    tmp = Path("/tmp") / f"metis-snap-{stamp}.sqlite"

    src = sqlite3.connect(str(paths.db))
    dst = sqlite3.connect(str(tmp))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    target = SNAPSHOTS / f"metis-{HOST}-{stamp}.sqlite"
    shutil.move(str(tmp), str(target))  # crosses filesystems (/tmp → OneDrive)

    # Prune only OUR OWN history — never another machine's snapshots.
    mine = sorted(SNAPSHOTS.glob(f"metis-{HOST}-*.sqlite"))
    for old in mine[:-KEEP_PER_HOST]:
        old.unlink(missing_ok=True)

    if verbose:
        mb = target.stat().st_size / 1_048_576
        print(f"  exported {target.name} ({mb:.0f} MB) · keeping last {KEEP_PER_HOST}")
    return target


# ── Import / merge ───────────────────────────────────────────────────────────

def _foreign_snapshots() -> list[Path]:
    """Snapshots produced by OTHER machines, newest first."""
    out = [
        p for p in SNAPSHOTS.glob("metis-*.sqlite")
        if not p.name.startswith(f"metis-{HOST}-")
    ]
    return sorted(out, key=lambda p: p.stat().st_mtime, reverse=True)


def _host_of(snapshot: Path) -> str:
    """Machine name from `metis-<host>-<YYYYmmdd>-<HHMMSS>.sqlite`.

    Snapshots taken before hostname-stamping are named `metis-<date>-<time>` with
    no host at all. Detect that (the field is all digits) and call it what it is,
    rather than inventing a machine called "20260622".
    """
    parts = snapshot.stem.split("-")
    if len(parts) >= 3 and not parts[1].isdigit():
        return parts[1]
    return "legacy"


def merge_snapshot(live: sqlite3.Connection, snapshot: Path, dry_run: bool) -> dict[str, int]:
    """Union the append-only tables from `snapshot` into the live DB."""
    added: dict[str, int] = {}
    other = _connect(snapshot, readonly=True)
    try:
        their_tables = {
            r["name"] for r in other.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in MERGE_TABLES:
            if table not in their_tables:
                continue
            try:
                live_cols = _columns(live, table)
            except sqlite3.DatabaseError:
                continue
            if not live_cols:
                continue

            pk = _pk_of(live, table)
            their_cols = _columns(other, table)
            # Only columns BOTH schemas have — the two machines may sit on
            # different migrations, and a merge must never fail on a schema drift.
            shared = [c for c in live_cols if c in their_cols]
            content = [c for c in shared if c not in pk]
            if not content:
                continue

            have = {
                _fingerprint(r, content)
                for r in live.execute(f"SELECT * FROM {table}")
            }

            insert_cols = content
            placeholders = ",".join("?" for _ in insert_cols)
            sql = (
                f"INSERT INTO {table} ({','.join(insert_cols)}) VALUES ({placeholders})"
            )

            n = 0
            for row in other.execute(f"SELECT * FROM {table}"):
                if _fingerprint(row, content) in have:
                    continue
                if not dry_run:
                    live.execute(sql, [row[c] for c in insert_cols])
                n += 1
            if n:
                added[table] = n
        if not dry_run:
            live.commit()
    finally:
        other.close()
    return added


def import_snapshots(dry_run: bool = False) -> int:
    live = _connect(paths.db)
    live.execute(_SYNC_STATE_DDL)
    live.commit()

    merged_already = {
        r["snapshot"] for r in live.execute("SELECT snapshot FROM db_sync_state")
    }

    total = 0
    foreign = _foreign_snapshots()
    if not foreign:
        print("  no snapshots from other machines yet.")
        print("  → run this script on the OTHER computer to publish its memory.")
        live.close()
        return 0

    # Only the newest snapshot per host: an older one is a strict subset of it.
    newest: dict[str, Path] = {}
    for snap in foreign:
        newest.setdefault(_host_of(snap), snap)

    for host, snap in newest.items():
        if snap.name in merged_already:
            print(f"  {snap.name} — already merged")
            continue
        age_d = (time.time() - snap.stat().st_mtime) / 86400
        print(f"  merging {snap.name}  (host {host}, {age_d:.0f}d old)")
        added = merge_snapshot(live, snap, dry_run)
        n = sum(added.values())
        total += n
        if added:
            for t, c in sorted(added.items(), key=lambda kv: -kv[1]):
                print(f"      +{c:<5} {t}")
        else:
            print("      nothing new — already converged")
        if not dry_run:
            live.execute(
                "INSERT OR REPLACE INTO db_sync_state "
                "(snapshot, host, merged_at, rows_added) VALUES (?,?,?,?)",
                (snap.name, host, time.strftime("%Y-%m-%dT%H:%M:%S"), n),
            )
            live.commit()

    live.close()
    if total and not dry_run:
        print(f"\n  merged {total} row(s). The nightly embedding_backfill job will")
        print("  embed the new memory so semantic recall picks it up automatically.")
    return total


def status() -> None:
    print(f"  this machine : {HOST}")
    print(f"  live DB      : {paths.db}  ({paths.db.stat().st_size / 1_048_576:.0f} MB)")
    print(f"  snapshots in : {SNAPSHOTS.relative_to(ROOT)}\n")
    snaps = sorted(SNAPSHOTS.glob("metis-*.sqlite"), key=lambda p: p.stat().st_mtime)
    if not snaps:
        print("  (no snapshots yet)")
        return
    for p in snaps:
        age = (time.time() - p.stat().st_mtime) / 86400
        who = "ours" if p.name.startswith(f"metis-{HOST}-") else f"host {_host_of(p)}"
        print(f"    {p.name:<44} {p.stat().st_size / 1_048_576:>5.0f} MB  {age:>4.1f}d  {who}")

    print("\n  NOT merged (by design):")
    for what, why in SKIPPED.items():
        print(f"    {what:<24} {why}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--import-only", action="store_true")
    ap.add_argument("--export-only", action="store_true")
    a = ap.parse_args()

    if a.status:
        status()
        return 0

    if not a.import_only:
        print("── export ──")
        export_snapshot()
    if not a.export_only:
        print("── merge ──")
        import_snapshots(dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
