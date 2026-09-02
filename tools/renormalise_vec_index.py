#!/usr/bin/env python3
"""Keep every vector in the semantic index unit length, and prove the index ranks.

WHAT THIS IS ACTUALLY FOR — and what it is NOT
    I found it while chasing a symptom that turned out to have a different
    cause, so the honest version of both is worth recording.

    THE SYMPTOM: every semantic query from the DASHBOARD returned the same
    document. A subject the corpus genuinely covers, an off-topic physics query
    and the nonsense string "zxqv wobble frobnicator" all came back with the
    same top hit, and the nonsense scored BETTER than the real subject.

    THE CAUSE was the dashboard's QUERY, not the index: it called `embed_one()`,
    whose default prefix is "search_document: " and whose default is
    `normalize=False`. That produced a query vector of norm ~20 against a store
    of unit vectors, and under L2 the only things near it were the handful of
    chunks that were also unnormalised. The MCP side has always called
    `embed_query(..., normalize=True)` and has always worked.

    WHAT THIS TOOL FIXES is the smaller, real defect underneath: **139 of 42,468
    vectors were stored unnormalised** — one document, indexed before the
    indexer gained `normalize=True` and never rebuilt. Against a correct
    normalised query those 139 sit at a distance no meaningful text can reach,
    so that document was effectively unsearchable. Direction is preserved
    exactly; only length changes, and no re-embedding is needed — it is
    arithmetic on bytes already in the database.

    Run it after any index build that might predate the normalising indexer.

THE CONTROL
    A known-relevant query and a known-nonsense query, before and after. The
    pass condition is that their separation is HEALTHY, not that it improved —
    written the other way round first, and it then reported failure on a corpus
    that was already 99% correct, because a fix to 139 stragglers cannot move a
    number that was not broken. A control has to state the property it wants.

USAGE
    python3 tools/renormalise_vec_index.py             # measure only
    python3 tools/renormalise_vec_index.py --apply
"""
from __future__ import annotations

import argparse
import contextlib
import math
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("METIS_DB")
          or (Path.home() / ".local/share/metis/metis.sqlite"))
DIM = 768
BATCH = 2000

RELEVANT = "drinking water quality guidelines and monitoring"
NONSENSE = "zxqv wobble frobnicator plibble"


def _open():
    import sqlite3
    import sqlite_vec
    con = sqlite3.connect(str(DB), timeout=60)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


def _probe(con, embed_query) -> tuple[float, float]:
    """Best distance for a relevant query and for a nonsense one."""
    out = []
    for text in (RELEVANT, NONSENSE):
        v = embed_query(text, normalize=True)
        blob = struct.pack(f"{len(v)}f", *v)
        row = con.execute(
            "SELECT v.distance FROM vec_pdf_chunks v "
            "WHERE v.embedding MATCH ? AND k = 1 ORDER BY v.distance", (blob,)
        ).fetchone()
        out.append(float(row["distance"]) if row else float("nan"))
    return out[0], out[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not DB.is_file():
        print(f"database not found: {DB}", file=sys.stderr)
        return 2
    sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))
    try:
        from metis_mcp.embeddings import embed_query
    except Exception as exc:
        print(f"embeddings unavailable: {exc}", file=sys.stderr)
        return 2

    with contextlib.closing(_open()) as con:
        total = con.execute("SELECT COUNT(*) FROM vec_pdf_chunks").fetchone()[0]
        print(f"vectors in the index      {total:>8,}")

        # ── norm distribution ───────────────────────────────────────────────
        norms, unit = [], 0
        for r in con.execute("SELECT rowid, embedding FROM vec_pdf_chunks"):
            v = struct.unpack(f"{DIM}f", r["embedding"])
            n = math.sqrt(sum(x * x for x in v))
            norms.append(n)
            if abs(n - 1.0) < 1e-3:
                unit += 1
        norms.sort()
        print(f"already unit length       {unit:>8,}  ({100*unit//max(total,1)}%)")
        print(f"norm  min / median / max  {norms[0]:.3f} / {norms[len(norms)//2]:.3f} / {norms[-1]:.3f}")

        before = _probe(con, embed_query)
        gap_before = before[1] - before[0]
        print(f"\nCONTROL, before")
        print(f"  relevant query best distance   {before[0]:.3f}")
        print(f"  nonsense query best distance   {before[1]:.3f}")
        print(f"  separation (nonsense - relevant) {gap_before:+.3f}"
              f"   {'← nonsense ranks BETTER' if gap_before <= 0 else ''}")

        if unit == total:
            print("\nAlready normalised. Nothing to do.")
            return 0
        if not args.apply:
            print(f"\nWould normalise {total - unit:,} vectors. Re-run with --apply.")
            return 0

        # ── rewrite ────────────────────────────────────────────────────────
        print(f"\nnormalising {total - unit:,} vectors…")
        done = 0
        rows = con.execute("SELECT rowid, embedding FROM vec_pdf_chunks").fetchall()
        con.execute("BEGIN")
        try:
            for i in range(0, len(rows), BATCH):
                payload = []
                for r in rows[i:i + BATCH]:
                    v = struct.unpack(f"{DIM}f", r["embedding"])
                    n = math.sqrt(sum(x * x for x in v))
                    if n == 0 or abs(n - 1.0) < 1e-6:
                        continue
                    payload.append((struct.pack(f"{DIM}f", *[x / n for x in v]),
                                    r["rowid"]))
                con.executemany(
                    "UPDATE vec_pdf_chunks SET embedding = ? WHERE rowid = ?", payload)
                done += len(payload)
                if len(rows) > BATCH:
                    print(f"  {done:>8,} / {total:,}", end="\r", flush=True)
            con.execute("COMMIT")
        except Exception as exc:
            con.execute("ROLLBACK")
            print(f"\nFAILED, rolled back: {exc}", file=sys.stderr)
            return 1
        print(f"  {done:>8,} / {total:,}  written")

        # ── control again — this decides whether it worked ─────────────────
        after = _probe(con, embed_query)
        gap_after = after[1] - after[0]
        print(f"\nCONTROL, after")
        print(f"  relevant query best distance   {after[0]:.3f}")
        print(f"  nonsense query best distance   {after[1]:.3f}")
        print(f"  separation (nonsense - relevant) {gap_after:+.3f}")

        # The pass condition is that separation is HEALTHY, not that it improved.
        # Written the other way round first, and it then reported failure on a
        # corpus where 99% of vectors were already unit length and the ranking
        # was already fine — the fix touched 139 stragglers and could not move a
        # number that was not broken. A control has to state the property it
        # wants, not assume every run is a rescue.
        MIN_GAP = 0.10
        if gap_after < MIN_GAP:
            print(f"\n! Separation is {gap_after:+.3f}, under {MIN_GAP}. Nonsense ranks "
                  f"at or near a real subject, so something beyond normalisation is "
                  f"wrong — do not trust semantic search yet.", file=sys.stderr)
            return 1
        if gap_after > gap_before + 0.01:
            print(f"\nSeparation improved {gap_before:+.3f} → {gap_after:+.3f}.")
        else:
            print(f"\nSeparation was already healthy ({gap_after:+.3f}) and is unchanged "
                  f"— the vectors fixed here were a minority that could not be "
                  f"retrieved properly, not the cause of a ranking problem.")
        print(f"A relevant query ranks ahead of nonsense by {gap_after:.3f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
