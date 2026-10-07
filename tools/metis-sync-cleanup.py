#!/usr/bin/env python3
"""metis-sync-cleanup.py — repair what the old append-only merge left behind.

The merger that tools/metis_sync.py replaced did two kinds of damage:

  1. MISSING IDS. Rows whose id is TEXT (ideas, notes, journal entries, memory
     entries, contacts) were copied WITHOUT the id, so they arrived with a NULL
     one — visible in lists, impossible to open, edit or link.
     Repair, in order of preference:
       a. the same row also exists WITH its id  → the NULL copy is a duplicate; drop it
       b. a snapshot from the other computer has the row with its id → restore that id
       c. otherwise → give it a new id shaped like the table's other ids

  2. DUPLICATES. Any edit to a synced row (a run finishing, a paper marked read,
     a memory archived) merged as a second row, and the copies travelled back.
     Each group of copies is collapsed into the OLDEST row, keeping the most
     advanced state of each (read beats unread, finished beats running, the
     latest timestamp, any value over an empty one). References from other tables
     to a removed copy are pointed at the row that was kept.

Dry run by default. With --apply it first writes a full backup next to the live
database, then repairs in one transaction.

USAGE
    python3 tools/metis-sync-cleanup.py              # show what would change
    python3 tools/metis-sync-cleanup.py --apply      # back up, then repair
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import metis_sync as ms  # noqa: E402

# The tables the old merger wrote to — the only place its duplicates can be.
OLD_MERGE_TABLES = [
    "episodic_memory", "semantic_memory", "procedural_memory", "session_summaries",
    "agent_runs", "memory_entries", "reflexion_log", "ideas", "journal_entries",
    "personal_notes", "user_decisions", "skill_improvement_proposals",
    "literature_metadata", "contacts",
]
FLAG_MAX = {"is_read", "starred", "dismissed", "crucial", "archived", "delivered", "hits"}
RUNNING = {"working", "running", "in_progress", "pending", "queued", "started"}


def live_db_path() -> Path:
    sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))
    from metis_mcp.config import paths  # noqa: E402
    return Path(paths.db)


def new_id_like(existing: list[str]) -> str:
    shapes = Counter()
    for v in existing[:500]:
        m = re.match(r"^([A-Za-z]+-)?([0-9a-f]+)$", v or "")
        if m:
            shapes[(m.group(1) or "", len(m.group(2)))] += 1
    if shapes:
        (prefix, n), _ = shapes.most_common(1)[0]
        return prefix + uuid.uuid4().hex[:n] if n <= 32 else uuid.uuid4().hex
    return uuid.uuid4().hex[:12]


class SnapshotIds:
    """Find a row's original id in the other computer's snapshots."""

    def __init__(self, d: Path):
        self.files = sorted(list(d.glob("sync-*.sqlite.gz")) + list(d.glob("metis-*.sqlite")),
                            key=lambda p: p.name, reverse=True) if d.exists() else []
        self.cache: dict[tuple[str, str], dict[str, str]] = {}

    def lookup(self, table: str, pkcol: str, ident: list[str], fp: str) -> str | None:
        for f in self.files:
            key = (str(f), table)
            if key not in self.cache:
                m: dict[str, str] = {}
                try:
                    con = sqlite3.connect(f"file:{ms.local_copy(f)}?mode=ro", uri=True)
                    have = {r[1] for r in con.execute(f"PRAGMA table_info({ms._q(table)})")}
                    if pkcol in have and all(c in have for c in ident):
                        sel = ",".join(ms._q(c) for c in [pkcol] + ident)
                        for row in con.execute(
                                f"SELECT {sel} FROM {ms._q(table)} WHERE {ms._q(pkcol)} IS NOT NULL"):
                            d = dict(zip([pkcol] + ident, row))
                            m.setdefault(ms.fingerprint(d, ident), d[pkcol])
                    con.close()
                except sqlite3.DatabaseError:
                    pass
                self.cache[key] = m
            hit = self.cache[key].get(fp)
            if hit:
                return hit
        return None


def merged_value(col: str, values: list):
    present = [v for v in values if v not in (None, "")]
    if not present:
        return values[0]
    if col in FLAG_MAX:
        try:
            return max(present, key=lambda v: float(v))
        except (TypeError, ValueError):
            return present[0]
    if col.endswith("_at") or col in ("last_seen", "last_synced"):
        return max(present, key=str)
    if col in ("status", "state"):
        final = [v for v in present if str(v).lower() not in RUNNING]
        return final[0] if final else present[0]
    return present[0]


def repair_null_ids(con, snaps: SnapshotIds, report: list[str]) -> int:
    fixed = 0
    for name, sql in ms.synced_tables(con).items():
        t = ms.describe(con, "main", name, sql)
        if t.intkey or len(t.pk) != 1 or not t.has_rowid:
            continue
        pk = t.pk[0]
        nulls = con.execute(f"SELECT rowid, * FROM {ms._q(name)} WHERE {ms._q(pk)} IS NULL").fetchall()
        if not nulls:
            continue
        cols = [d[0] for d in con.execute(f"SELECT * FROM {ms._q(name)} LIMIT 0").description]
        ident = ms.identity_cols(t, cols)
        twins: dict[str, int] = {}
        existing_ids: list[str] = []
        for row in con.execute(f"SELECT rowid, * FROM {ms._q(name)} WHERE {ms._q(pk)} IS NOT NULL"):
            d = dict(zip(["rowid"] + cols, row))
            twins.setdefault(ms.fingerprint(d, ident), d["rowid"])
            existing_ids.append(str(d[pk]))
        taken = set(existing_ids)
        dropped = restored = generated = 0
        for row in nulls:
            d = dict(zip(["rowid"] + cols, row))
            fp = ms.fingerprint(d, ident)
            if fp in twins:
                keep = twins[fp]
                kept = dict(zip(["rowid"] + cols, con.execute(
                    f"SELECT rowid, * FROM {ms._q(name)} WHERE rowid=?", (keep,)).fetchone()))
                fill = {c: d[c] for c in cols if c != pk
                        and ms.is_unset(kept[c], t.defaults.get(c))
                        and not ms.is_unset(d[c], t.defaults.get(c))}
                if fill:
                    con.execute(f"UPDATE {ms._q(name)} SET "
                                + ", ".join(f"{ms._q(c)}=?" for c in fill)
                                + " WHERE rowid=?", list(fill.values()) + [keep])
                con.execute(f"DELETE FROM {ms._q(name)} WHERE rowid=?", (d["rowid"],))
                dropped += 1
                continue
            new = snaps.lookup(name, pk, ident, fp)
            if new and new not in taken:
                restored += 1
            else:
                new = new_id_like(existing_ids)
                while new in taken:
                    new = new_id_like(existing_ids)
                generated += 1
            taken.add(new)
            con.execute(f"UPDATE {ms._q(name)} SET {ms._q(pk)}=? WHERE rowid=?", (new, d["rowid"]))
            twins[fp] = d["rowid"]
        n = dropped + restored + generated
        fixed += n
        report.append(f"  {name:<28} {len(nulls):>5} without an id → "
                      f"{dropped} duplicate(s) dropped, {restored} id(s) restored, "
                      f"{generated} new id(s)")
    return fixed


def collapse_duplicates(con, report: list[str]) -> int:
    removed_total = 0
    tables = ms.synced_tables(con)
    for name in OLD_MERGE_TABLES:
        if name not in tables:
            continue
        t = ms.describe(con, "main", name, tables[name])
        if not t.intkey:
            continue  # TEXT ids cannot repeat; their NULL copies are handled above
        cols = [d[0] for d in con.execute(f"SELECT * FROM {ms._q(name)} LIMIT 0").description]
        ident = ms.identity_cols(t, cols)
        groups: dict[str, list[dict]] = {}
        for row in con.execute(f"SELECT rowid, * FROM {ms._q(name)} ORDER BY rowid"):
            d = dict(zip([ms.RID] + cols, row))
            k = ms.natural_key(name, d) or (ms.fingerprint(d, ident) if len(ident) >= 2 else None)
            if k:
                groups.setdefault(k, []).append(d)
        remap: dict[int, int] = {}
        removed = 0
        for rows in groups.values():
            if len(rows) < 2:
                continue
            keep = rows[0]
            changes = {}
            for c in cols:
                if c in t.pk:
                    continue
                v = merged_value(c, [r[c] for r in rows])
                if v != keep[c]:
                    changes[c] = v
            if changes:
                con.execute(f"UPDATE {ms._q(name)} SET "
                            + ", ".join(f"{ms._q(c)}=?" for c in changes)
                            + " WHERE rowid=?", list(changes.values()) + [keep[ms.RID]])
            for r in rows[1:]:
                con.execute(f"DELETE FROM {ms._q(name)} WHERE rowid=?", (r[ms.RID],))
                remap[r[ms.RID]] = keep[ms.RID]
                removed += 1
        if removed:
            # point references at the row that was kept
            for tbl, col, target, disc in ms.REFS:
                if target != name or tbl not in tables:
                    continue
                for old, new in remap.items():
                    where = f"{ms._q(col)} IN (?, ?)"
                    params = [old, str(old)]
                    if disc:
                        where += f" AND {ms._q(disc[0])}=?"
                        params.append(disc[1])
                    try:
                        con.execute(f"UPDATE OR IGNORE {ms._q(tbl)} SET {ms._q(col)}=? WHERE {where}",
                                    [new] + params)
                    except sqlite3.DatabaseError:
                        pass
            report.append(f"  {name:<28} {removed:>5} duplicate(s) collapsed into their original")
        removed_total += removed
    return removed_total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="back up, then repair")
    ap.add_argument("--db", type=Path, help="database (default: this computer's live DB)")
    ap.add_argument("--sync-dir", type=Path, help="folder holding the other computer's snapshots")
    a = ap.parse_args()

    db = a.db or live_db_path()
    d = a.sync_dir or ms.sync_dir()
    if not db.exists():
        print(f"no database at {db}")
        return 1
    print(f"database : {db}")
    print(f"snapshots: {d}\n")

    if a.apply:
        bdir = db.parent / "backups"
        bdir.mkdir(exist_ok=True)
        backup = bdir / f"pre-cleanup-{time.strftime('%Y%m%d-%H%M%S')}.sqlite"
        src = sqlite3.connect(str(db))
        dst = sqlite3.connect(str(backup))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        print(f"backup   : {backup}\n")

    con = sqlite3.connect(str(db), timeout=60, isolation_level=None)
    con.execute("PRAGMA busy_timeout=60000")
    report: list[str] = []
    con.execute("BEGIN IMMEDIATE")
    try:
        n1 = repair_null_ids(con, SnapshotIds(d), report)
        n2 = collapse_duplicates(con, report)
        if a.apply:
            con.execute("COMMIT")
        else:
            con.execute("ROLLBACK")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()

    print("\n".join(report) if report else "  nothing to repair — no missing ids, no duplicates")
    print()
    if a.apply:
        print(f"repaired {n1} row(s) without an id and removed {n2} duplicate(s).")
    elif n1 or n2:
        print(f"DRY RUN — {n1} row(s) without an id and {n2} duplicate(s) would be repaired.")
        print("Run again with --apply to do it (a backup is written first).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
