#!/usr/bin/env python3
"""Re-cluster every news item under the CURRENT threading rules.

WHY THIS EXISTS. `assign_threads()` only ever touches items that have no thread
yet — which is right for the hourly path and wrong after the rules change. On
2026-08-27 three fixes landed in `news_threads.classify()`:

  · aliases now need a word boundary on BOTH sides, so `mali` stopped matching
    "MALIgnant" and a pancreatic-cancer story stopped being filed under Mali;
  · verbs can no longer name a thread, so one FDA drug approval stopped
    appearing as three separate running stories called "Approves treatment",
    "Agency approves" and "Approves · Mali";
  · fallback tokens rank by length rather than by position, so the noun wins
    over the filler in front of it.

None of that is visible until the existing rows are re-clustered, because they
carry thread ids assigned under the old rules.

THE PART THAT NEEDS CARE. Thread ids are not opaque keys — they are derived
from the text, so re-clustering CHANGES them. `news_thread_mentions` records
which threads have appeared in a brief, keyed by thread id, and that is what
drives the "briefed" state on the overview. A naive DELETE-and-rebuild orphans
every one of those rows, and the surface would come back claiming nothing has
ever been briefed.

So mentions are CARRIED FORWARD: for each old thread, whichever new thread now
holds the most of its items inherits its mention history. That is a majority
vote, not a proof — an old thread whose items scatter evenly across three new
ones hands its history to one of them. The alternative is losing it entirely.

Reversible. Both tables are copied to `<name>_bak_<stamp>` first, and --undo
puts them back.

    python3 tools/rethread_news.py            # dry run: counts only
    python3 tools/rethread_news.py --apply
    python3 tools/rethread_news.py --undo 20260827T1812
"""
from __future__ import annotations

import argparse
import collections
import datetime
import os
import sqlite3
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "system" / "mcp-server" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from metis_mcp.tools import news_threads as nt  # noqa: E402

DB = Path(os.path.expanduser("~/.local/share/metis/metis.sqlite"))
TABLES = ("news_threads", "news_thread_items")


def _stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%dT%H%M")


def _rows(conn: sqlite3.Connection):
    """Every threaded brief, as (rowid, title, summary, domain)."""
    return conn.execute(
        "SELECT b.rowid, b.title, COALESCE(b.summary,''), COALESCE(b.domain,'') "
        "FROM news_briefs b"
    ).fetchall()


def plan(conn: sqlite3.Connection) -> dict:
    """Work out the new clustering without writing anything."""
    old = {r[0]: r[1] for r in conn.execute(
        "SELECT brief_ref, thread_id FROM news_thread_items")}

    new: dict[int, dict] = {}
    for ref, title, summary, domain in _rows(conn):
        new[ref] = nt.classify(title or "", summary or "", domain or "")

    # old thread -> Counter of the new threads its items landed in
    migration: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    for ref, old_id in old.items():
        if ref in new:
            migration[old_id][new[ref]["thread_id"]] += 1

    remap = {o: c.most_common(1)[0][0] for o, c in migration.items() if c}

    sizes = collections.Counter(v["thread_id"] for v in new.values())
    return {
        "items": len(new),
        "old_threads": len(set(old.values())),
        "new_threads": len(sizes),
        "singletons_before": sum(
            1 for _, n in collections.Counter(old.values()).items() if n == 1),
        "singletons_after": sum(1 for n in sizes.values() if n == 1),
        "remap": remap,
        "new": new,
        "sizes": sizes,
    }


def apply(conn: sqlite3.Connection, p: dict, stamp: str) -> None:
    for t in TABLES:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t}_bak_{stamp} AS SELECT * FROM {t}")
    conn.execute("DELETE FROM news_thread_items")
    conn.execute("DELETE FROM news_threads")

    now = datetime.datetime.now().isoformat()
    seen: dict[str, dict] = {}
    for ref, c in p["new"].items():
        tid = c["thread_id"]
        agg = seen.setdefault(tid, {"c": c, "n": 0})
        agg["n"] += 1
        conn.execute(
            "INSERT OR IGNORE INTO news_thread_items (thread_id, brief_ref, assigned_at) "
            "VALUES (?,?,?)", (tid, ref, now))
    conn.commit()
    for tid, agg in seen.items():
        c = agg["c"]
        conn.execute(
            "INSERT INTO news_threads (thread_id, label, subject, place, keywords, "
            " domain, first_seen, last_seen, item_count, peak_signal, max_number, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, c["label"], c["subject"], c["place"], ",".join(c["keywords"]),
             c.get("domain", ""), now, now, agg["n"], "low", c["max_number"], "active"))

    # Carry the "has been briefed" history across the id change.
    moved = 0
    for old_id, new_id in p["remap"].items():
        if old_id != new_id:
            cur = conn.execute(
                "UPDATE news_thread_mentions SET thread_id=? WHERE thread_id=?",
                (new_id, old_id))
            moved += cur.rowcount
    conn.commit()
    print(f"  mention rows re-pointed: {moved}")


def undo(conn: sqlite3.Connection, stamp: str) -> None:
    for t in TABLES:
        bak = f"{t}_bak_{stamp}"
        n = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (bak,)).fetchone()[0]
        if not n:
            sys.exit(f"no backup table {bak}")
        conn.execute(f"DELETE FROM {t}")
        conn.execute(f"INSERT INTO {t} SELECT * FROM {bak}")
    conn.commit()
    print(f"restored from _bak_{stamp}  (mention re-pointing is NOT reversed)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", metavar="STAMP")
    a = ap.parse_args()

    conn = sqlite3.connect(DB)
    nt.ensure_tables(conn)

    if a.undo:
        undo(conn, a.undo)
        return

    p = plan(conn)
    # Counts only. The corpus itself is not this tool's output.
    print(f"  items                {p['items']:>6}")
    print(f"  threads   before     {p['old_threads']:>6}")
    print(f"            after      {p['new_threads']:>6}")
    print(f"  one-item  before     {p['singletons_before']:>6}"
          f"   ({p['singletons_before'] / max(1, p['old_threads']):.0%})")
    print(f"            after      {p['singletons_after']:>6}"
          f"   ({p['singletons_after'] / max(1, p['new_threads']):.0%})")

    if not a.apply:
        print("\n  dry run — nothing written. Re-run with --apply.")
        return
    stamp = _stamp()
    apply(conn, p, stamp)
    print(f"  applied. undo with:  python3 tools/rethread_news.py --undo {stamp}")


if __name__ == "__main__":
    main()
