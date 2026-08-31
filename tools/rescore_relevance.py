#!/usr/bin/env python3
"""Re-score every stored item against the interest profile.

WHY
    `new_publications.relevance` was hardcoded to 0.9 by the PubMed and OpenAlex
    ingest paths — "a topic hit is by definition his field". It is not: 56 rows
    reached 0.9 that way, among them papers on spiritual-care teaching and
    manual strangulation, presented to an NTD researcher under "close to my
    work". A score identical on every row cannot rank rows.

    The profile itself was also wrong in two ways, both silent:
      · its STATED-FOCUS band was empty, because it read a yaml path that
        resolves inside the venv and does not exist there;
      · 400 library titles outweighed ~16 projects, so the profile drifted
        toward general public health rather than what he is working on.

    Both are fixed in tools/relevance.py. This applies the corrected profile to
    everything already stored, so the backlog ranks the same way new arrivals
    will.

USAGE
    python3 tools/rescore_relevance.py            # dry run, shows the shift
    python3 tools/rescore_relevance.py --apply
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import sqlite3
import sys
from pathlib import Path

BATCH = 256


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="score only N rows (for a quick look)")
    args = ap.parse_args()

    from metis_mcp.config import paths
    from metis_mcp.tools.relevance import build_profile, score_batch_profile

    db = Path(str(paths.db))
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    centroid = build_profile(con, force=True)
    if not centroid:
        print("no interest profile could be built — nothing scored", file=sys.stderr)
        return 2

    targets = [
        ("new_publications", "id", "title", "abstract"),
        # news_briefs has no `id`: its key is brief_id, and rowid is what the
        # rest of the app joins on. Named explicitly rather than assumed.
        ("news_briefs", "rowid", "title", "summary"),
    ]

    if args.apply:
        stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        shutil.copy2(db, db.with_suffix(db.suffix + f".bak-{stamp}"))
        print(f"backed up to {db.name}.bak-{stamp}\n")

    for table, idcol, titlecol, bodycol in targets:
        try:
            rows = con.execute(
                f"SELECT {idcol} AS id, COALESCE({titlecol},'') AS t, "
                f"COALESCE({bodycol},'') AS b, COALESCE(relevance,0) AS old FROM {table}"
                + (f" LIMIT {args.limit}" if args.limit else "")
            ).fetchall()
        except sqlite3.OperationalError as exc:
            print(f"{table}: skipped ({exc})")
            continue
        if not rows:
            continue

        moved_up = moved_down = 0
        updates = []
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            texts = [(r["t"] + " " + r["b"])[:500] for r in chunk]
            scores = score_batch_profile(texts, centroid)
            for r, sc in zip(chunk, scores):
                new = round(float(sc), 4)
                updates.append((new, r["id"]))
                if new > r["old"] + 0.02:
                    moved_up += 1
                elif new < r["old"] - 0.02:
                    moved_down += 1
            print(f"  {table}: {min(i + BATCH, len(rows))}/{len(rows)}", end="\r", flush=True)

        print(f"  {table}: {len(rows)} scored · {moved_up} rose · {moved_down} fell        ")
        if args.apply:
            con.executemany(f"UPDATE {table} SET relevance = ? WHERE {idcol} = ?", updates)
            con.commit()

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply.")
        return 0

    print("\ntop of the Library after re-scoring:")
    for r in con.execute(
        "SELECT ROUND(relevance,3) s, title FROM new_publications "
        "ORDER BY relevance DESC LIMIT 8"
    ):
        print(f"  {r[0]:.3f}  {str(r[1])[:72]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
