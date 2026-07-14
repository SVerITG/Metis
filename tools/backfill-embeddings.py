#!/usr/bin/env python3
"""backfill-embeddings.py — make cross-pollination actually work.

THE PROBLEM (found 2026-07-14)
    episodic_memory held 1,858 rows. vec_episodic held 33. **1.8% embedded.**
    Cross-pollination — the feature described as the whole point of Metis — was
    silently degrading to a SQL LIKE over a handful of keywords, because the
    semantic index it searches was essentially empty.

WHY
    `remember()` embeds on write. But episodic_memory has MANY other writers
    (session events, agent runs, auto-capture, meeting import) that INSERT
    directly and never touch the vector table. Chasing every writer is fragile —
    the next new writer reintroduces the gap.

THE FIX
    Reconcile instead. Anything in a source table with no row in its vec0 index
    gets embedded. Idempotent, resumable, batched — safe to run on a schedule,
    which is what keeps the index honest no matter who writes.

Run:      "$HOME/.local/share/metis-mcp/.venv/bin/python3" tools/backfill-embeddings.py
Options:  --dry-run     report the gap, change nothing
          --limit N     only process N rows (for a quick check)
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

from metis_mcp.config import paths  # noqa: E402
from metis_mcp.embeddings import embed_document  # noqa: E402
from metis_mcp.tools.vector_memory import _encode_vec, _setup_tables  # noqa: E402

# (source table, vec table, the column holding the text to embed)
TARGETS = [
    ("episodic_memory", "vec_episodic", "content"),
    ("semantic_memory", "vec_semantic", "definition"),
]
BATCH = 64


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(paths.db), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    _setup_tables(conn)  # loads sqlite-vec and ensures the vec0 tables exist
    return conn


def _missing(conn, src: str, vec: str, col: str, limit: int | None):
    """Rows in the source table with no vector. The vec0 shadow table
    `<vec>_rowids` is the reliable way to ask what is already indexed."""
    sql = (
        f"SELECT s.rowid AS rid, s.{col} AS txt FROM {src} s "
        f"WHERE s.{col} IS NOT NULL AND trim(s.{col}) != '' "
        f"AND s.rowid NOT IN (SELECT rowid FROM {vec}_rowids) "
        f"ORDER BY s.rowid"
    )
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    conn = _connect()
    total_done = total_fail = 0

    for src, vec, col in TARGETS:
        n_src = conn.execute(f"SELECT count(*) FROM {src}").fetchone()[0]
        n_vec = conn.execute(f"SELECT count(*) FROM {vec}_rowids").fetchone()[0]
        rows = _missing(conn, src, vec, col, args.limit)
        pct = (n_vec / n_src * 100) if n_src else 100.0
        print(f"\n{src}: {n_src} rows, {n_vec} embedded ({pct:.1f}%) — {len(rows)} to backfill")

        if args.dry_run or not rows:
            continue

        done = fail = 0
        t0 = time.time()
        for i in range(0, len(rows), BATCH):
            chunk = rows[i : i + BATCH]
            for r in chunk:
                try:
                    v = embed_document((r["txt"] or "")[:2000])
                    conn.execute(
                        f"INSERT INTO {vec} (rowid, embedding) VALUES (?, ?)",
                        (r["rid"], _encode_vec(v)),
                    )
                    done += 1
                except Exception as e:
                    # Report, never swallow. A `try/except: pass` here is exactly
                    # what let the index rot to 1.8% without anyone noticing.
                    fail += 1
                    if fail <= 3:
                        print(f"  ! rowid {r['rid']}: {type(e).__name__}: {e}")
            conn.commit()
            pct_done = (i + len(chunk)) / len(rows) * 100
            print(f"  {i + len(chunk):>5}/{len(rows)}  ({pct_done:5.1f}%)", end="\r", flush=True)

        n_vec2 = conn.execute(f"SELECT count(*) FROM {vec}_rowids").fetchone()[0]
        cov = (n_vec2 / n_src * 100) if n_src else 100.0
        print(f"  embedded {done}, failed {fail}, {time.time() - t0:.0f}s → coverage now {cov:.1f}%")
        total_done += done
        total_fail += fail

    conn.close()
    print(f"\n✓ backfill complete — {total_done} embedded, {total_fail} failed")
    return 1 if total_fail and not total_done else 0


if __name__ == "__main__":
    sys.exit(main())
