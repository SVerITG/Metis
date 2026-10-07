#!/usr/bin/env python3
"""metis-sync-db.py — keep Metis's database the same on every computer.

The design, and why it replaced the append-only merge, is in tools/metis_sync.py.
In one line: one computer is the MAIN one; every other computer rebases onto it;
the main computer merges their changes three-way; the main computer wins conflicts.

FIRST TIME (once):
    on the MAIN computer      python3 tools/metis-sync-cleanup.py --apply
                              python3 tools/metis-sync-db.py --make-primary
    on the OTHER computer     python3 tools/metis-sync-cleanup.py --apply
                              python3 tools/metis-sync-db.py
    on the MAIN computer      python3 tools/metis-sync-db.py
    After that the dashboard runs the sync every 15 minutes, at start-up and when a
    Claude Code session ends. Nothing else to do.

USAGE
    python3 tools/metis-sync-db.py                 # sync now
    python3 tools/metis-sync-db.py --status        # who is main, what has arrived, any problem
    python3 tools/metis-sync-db.py --make-primary  # this computer becomes the main one

Lines beginning `SYNC-PROBLEM:` are read by the dashboard's scheduler and shown red
on the Automation panel. The last line, `SYNC-SUMMARY:`, is its status message.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

import metis_sync as ms  # noqa: E402


def live_db() -> Path:
    from metis_mcp.config import paths  # noqa: E402
    return Path(paths.db)


class _Lock:
    """One sync at a time on this computer (scheduler, session end, by hand)."""

    def __init__(self, path: Path):
        self.path = path
        self.fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(self.path, "w")
        try:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            pass
        except OSError:
            print("SYNC-SUMMARY: another sync is already running on this computer")
            sys.exit(0)
        return self

    def __exit__(self, *exc):
        self.fh.close()


def status(live: Path, d: Path, host: str) -> int:
    primary = ms.read_primary(d)
    role = "main" if primary == host else ("not set" if primary is None else "secondary")
    print(f"  this computer : {host}  ({role})")
    print(f"  main computer : {primary or '— not set: run --make-primary on it'}")
    print(f"  live database : {live}")
    print(f"  shared folder : {d}")
    if live.exists():
        import sqlite3
        con = sqlite3.connect(str(live))
        try:
            st = ms._state(con)
        finally:
            con.close()
        for k in sorted(st):
            if k != "last_export_digest":
                print(f"    {k:<20} {st[k]}")
    snaps = ms.list_snaps(d)
    print()
    if not snaps:
        print("  (no snapshots in the shared folder yet)")
    for h, s in ms._newest_by_host(snaps).items():
        age_h = (time.time() - time.mktime(time.strptime(s.stamp[:15], "%Y%m%d-%H%M%S"))) / 3600
        who = "this computer" if h == host else h
        print(f"    newest from {who:<18} {s.name}   {age_h:5.1f} h ago")
    rep = ms.Report()
    ms.check_freshness(d, host, primary, rep)
    if primary is None:
        rep.problem("no main computer is set")
    print()
    for p in rep.problems:
        print(f"SYNC-PROBLEM: {p}")
    if not rep.problems:
        print("  ✓ in sync")
    print("\n  Not synced, by design (each computer rebuilds them from synced files):")
    print("    " + ", ".join(sorted(ms.LOCAL_TABLES)) + ", vec_* indexes")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--make-primary", action="store_true",
                    help="make THIS computer the main one (its version wins conflicts)")
    ap.add_argument("--db", type=Path, help="live database (default: this computer's)")
    a = ap.parse_args()

    live = a.db or live_db()
    d = ms.sync_dir()
    host = ms.host_name()

    if a.status:
        return status(live, d, host)

    with _Lock(Path.home() / ".local" / "share" / "metis-mcp" / ".sync.lock"):
        if a.make_primary:
            old = ms.read_primary(d)
            ms.make_primary(d, host)
            print(f"  {host} is now the main computer" + (f" (was {old})" if old and old != host else ""))
        rep = ms.sync(live, d, host)

    print(f"── sync · {host} · {rep.role} ──")
    for ln in rep.lines:
        print("  " + ln)
    for p in rep.problems:
        print(f"SYNC-PROBLEM: {p}")
    if rep.problems:
        summary = rep.problems[0]
    elif rep.changed:
        summary = f"{rep.changed} change(s) synced ({rep.role})"
    else:
        summary = f"in sync ({rep.role})"
    print(f"SYNC-SUMMARY: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
