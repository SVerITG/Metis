#!/usr/bin/env python
"""Re-score stored relevance with the weighted interest profile.

WHY THIS HAS TO RUN. `relevance` is a STORED column, written once when an item
is collected. Changing how the profile is built therefore changes nothing that
is already in the database — the surfaces keep filtering thousands of old rows
by a number computed from the old, unweighted profile, on a different scale from
the threshold now applied to it. Half the feed would be judged by one rule and
half by another, and nothing on screen would say so.

Idempotent: re-running re-computes the same numbers. Resumable: it commits per
batch, so an interrupted run leaves consistent rows behind it rather than a
half-written column.

    python tools/rescore_relevance.py            # report only, writes nothing
    python tools/rescore_relevance.py --apply    # write the new scores
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".local/share/metis/metis.sqlite"
BATCH = 250

# (table, id column, the text that describes the item)
TARGETS = [
    ("new_publications", "id",
     "COALESCE(title,'') || ' ' || COALESCE(journal,'')"),
    ("news_briefs", "brief_id",
     "COALESCE(title,'') || ' ' || COALESCE(summary,'')"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the scores")
    ap.add_argument("--limit", type=int, default=0, help="stop after N rows (testing)")
    args = ap.parse_args()

    from metis_mcp.tools.relevance import build_profile, score_batch_profile

    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row

    profile = build_profile(con, force=True)
    if not profile or not profile.get("weights"):
        print("ERROR: no weighted profile — refusing to write scores on the old scale.",
              file=sys.stderr)
        return 1
    print(f"profile: {len(profile['anchors'])} anchors, bands {profile.get('bands')}")

    # A CONTROL BEFORE ANY WRITE. If the profile cannot tell the researcher's
    # own subject from an unrelated clinical paper, it must not be allowed to
    # overwrite thousands of stored scores. A check that cannot fail is
    # decoration; this one is given a case built to fail.
    near, far = score_batch_profile([
        "Spatial risk mapping of sleeping sickness transmission",
        "Cerebrovascular injury following manual strangulation",
    ], profile)
    print(f"control: near={near:.3f}  far={far:.3f}  separation={near - far:.3f}")
    if near - far < 0.08:
        print("ERROR: the profile does not separate. Nothing written.", file=sys.stderr)
        return 1

    total_changed = 0
    for table, idcol, textexpr in TARGETS:
        rows = con.execute(
            f"SELECT {idcol} AS id, {textexpr} AS txt, COALESCE(relevance,0) AS old "
            f"FROM {table} WHERE COALESCE({textexpr},'') != ''"
        ).fetchall()
        if args.limit:
            rows = rows[:args.limit]
        print(f"\n{table}: {len(rows)} rows")

        moved, done = [], 0
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            scores = score_batch_profile([r["txt"][:500] for r in chunk], profile)
            if args.apply:
                con.executemany(
                    f"UPDATE {table} SET relevance=? WHERE {idcol}=?",
                    [(round(float(s), 4), r["id"]) for r, s in zip(chunk, scores)])
                con.commit()
            moved += [abs(float(s) - float(r["old"])) for r, s in zip(chunk, scores)]
            done += len(chunk)
            print(f"  {done}/{len(rows)}", end="\r", flush=True)

        avg = sum(moved) / max(len(moved), 1)
        print(f"  {done} scored · mean change {avg:+.3f}"
              f"{'' if args.apply else '  (dry run — nothing written)'}")
        total_changed += done

    if not args.apply:
        print("\nDry run. Re-run with --apply to write.")
    else:
        print(f"\nWrote {total_changed} scores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
