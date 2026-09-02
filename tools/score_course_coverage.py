#!/usr/bin/env python3
"""Score each course topic against the library — semantically, and cached.

WHY NOT KEYWORDS
    The coverage panel used to ask whether a topic's words appeared in a title
    or abstract. That fails in both directions at once, which is why its
    percentage was withdrawn: a one-word topic like "Coverage" matched 71 papers
    about something else, while "The molecule-to-decision chain" matched nothing
    however well the subject was covered. Neither number said anything about the
    library.

    The right instrument was already here: 42,468 embedded chunks across 517
    documents. It had never been usable from the dashboard because queries were
    embedded with the document prefix and unnormalised — fixed the same day as
    this tool.

WHY CACHED
    Embedding 187 topics takes seconds, not milliseconds, and a page must not
    wait on a model. This computes once into `course_topic_coverage`; the panel
    reads that table. Re-run after seeding topics or rebuilding the index.

THE BANDS, AND WHERE THEY COME FROM
    Measured on this corpus with normalised cosine:

      a real subject in the corpus      0.806 - 0.851
      an off-topic query                0.609 - 0.629
      literal nonsense                  0.559

    So: >= 0.75 "covered", 0.66 - 0.75 "thin", < 0.66 "absent" — placed either
    side of a +0.189 gap. `--calibrate` re-measures the controls and FAILS if an
    in-corpus query misses "covered" or an off-topic one reaches "thin", so the
    bands can be checked rather than trusted. It rejected my first guess.

WHAT IT ALSO RECORDS
    The best-matching document per topic. "Covered" is far more useful when it
    names the paper, and it makes a wrong band easy to spot — which is the point
    of not hiding behind a percentage.

USAGE
    python3 tools/score_course_coverage.py --calibrate   # check the bands hold
    python3 tools/score_course_coverage.py               # dry run
    python3 tools/score_course_coverage.py --apply
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

# CALIBRATED, not chosen (2026-09-02). My first guess was 0.72/0.62 and
# `--calibrate` rejected it: "quantum chromodynamics" scored 0.629 and so came
# out as "thin", i.e. the library was credited with partially covering particle
# physics. Measured on this corpus the two populations sit at
#   in-corpus 0.818 - 0.825      off-topic 0.609 - 0.629      nonsense 0.559
# a margin of +0.189, so the bands go either side of the gap with room to spare
# rather than on top of one edge of it.
COVERED, THIN = 0.75, 0.66

# Controls chosen to be IN this corpus without naming the research programme —
# this file is published, and a control query is a comment about what the
# library holds. Both score 0.79-0.85 here; if a future corpus does not hold
# them, --calibrate says so rather than silently mis-banding everything.
CONTROLS = [
    ("in corpus",  "drinking water quality guidelines and monitoring"),
    ("in corpus",  "cost-effectiveness analysis of health interventions"),
    ("off-topic",  "quantum chromodynamics lattice gauge theory"),
    ("off-topic",  "medieval Byzantine coinage and mint marks"),
    ("nonsense",   "zxqv wobble frobnicator plibble"),
]

DDL = """
CREATE TABLE IF NOT EXISTS course_topic_coverage (
    course_id  INTEGER NOT NULL,
    keyword    TEXT    NOT NULL,
    score      REAL,               -- best cosine against the indexed corpus
    band       TEXT,               -- covered | thin | absent
    best_doc   TEXT,               -- the document that matched
    scored_at  TEXT NOT NULL,
    PRIMARY KEY (course_id, keyword)
)
"""


def _open():
    import sqlite3
    import sqlite_vec
    con = sqlite3.connect(str(DB), timeout=60)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)
    return con


def _best(con, embed_query, text: str) -> tuple[float, str]:
    """(best cosine, document title) for one topic."""
    v = embed_query(text, normalize=True)
    blob = struct.pack(f"{len(v)}f", *v)
    row = con.execute(
        "SELECT c.title, c.source_file, v.distance "
        "FROM vec_pdf_chunks v JOIN pdf_chunks c ON c.id = v.rowid "
        "WHERE v.embedding MATCH ? AND k = 1 ORDER BY v.distance", (blob,)
    ).fetchone()
    if not row:
        return 0.0, ""
    d = float(row["distance"])
    # Unit vectors: cos = 1 - d²/2.
    cos = max(0.0, min(1.0, 1.0 - (d * d) / 2.0))
    doc = str(row["title"] or Path(str(row["source_file"] or "")).name or "")
    return cos, doc


def band_of(score: float) -> str:
    return "covered" if score >= COVERED else ("thin" if score >= THIN else "absent")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--calibrate", action="store_true",
                    help="re-measure the control queries and stop")
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
        # ── calibration: do the bands still separate? ──────────────────────
        if args.calibrate:
            print(f"bands: covered >= {COVERED}   thin >= {THIN}   else absent\n")
            print(f"{'expected':11s} {'cos':>6s} {'band':8s} query")
            worst_in, best_off = 1.0, 0.0
            for cls, q in CONTROLS:
                cos, _ = _best(con, embed_query, q)
                print(f"{cls:11s} {cos:6.3f} {band_of(cos):8s} {q[:52]}")
                if cls == "in corpus":
                    worst_in = min(worst_in, cos)
                else:
                    best_off = max(best_off, cos)
            print(f"\nworst in-corpus {worst_in:.3f}   best off-topic {best_off:.3f}"
                  f"   margin {worst_in - best_off:+.3f}")
            sys.stdout.flush()
            if worst_in < COVERED:
                print("! an in-corpus control does NOT reach 'covered' — the bands are "
                      "too strict for this corpus", file=sys.stderr)
                return 1
            if best_off >= THIN:
                print("! an off-topic control reaches 'thin' — the bands are too loose",
                      file=sys.stderr)
                return 1
            print("Bands hold: every in-corpus control is covered and no off-topic "
                  "control is even thin.")
            return 0

        con.execute(DDL)
        rows = con.execute(
            "SELECT ct.course_id, ct.keyword, lc.title AS course, lc.status "
            "FROM course_topics ct JOIN learning_courses lc ON lc.id = ct.course_id "
            "ORDER BY lc.title, ct.id").fetchall()
        if not rows:
            print("no course topics recorded — run tools/seed_course_topics.py first")
            return 0

        print(f"scoring {len(rows)} topics across "
              f"{len({r['course_id'] for r in rows})} courses…\n")
        import datetime
        now = datetime.datetime.now().isoformat()
        per_course: dict[str, list[str]] = {}
        payload = []
        for i, r in enumerate(rows, 1):
            cos, doc = _best(con, embed_query, r["keyword"])
            b = band_of(cos)
            per_course.setdefault(r["course"], []).append(b)
            payload.append((r["course_id"], r["keyword"], cos, b, doc, now))
            if i % 25 == 0:
                print(f"  {i}/{len(rows)}", end="\r", flush=True)

        print(f"{'course':42s} {'covered':>8s} {'thin':>5s} {'absent':>7s}")
        print("-" * 66)
        for course, bands in per_course.items():
            print(f"{course[:42]:42s} {bands.count('covered'):>8d} "
                  f"{bands.count('thin'):>5d} {bands.count('absent'):>7d}")

        if not args.apply:
            print("\nDry run. Nothing written — re-run with --apply.")
            return 0

        con.execute("BEGIN")
        try:
            con.executemany(
                "INSERT INTO course_topic_coverage "
                "(course_id, keyword, score, band, best_doc, scored_at) "
                "VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(course_id, keyword) DO UPDATE SET "
                "score=excluded.score, band=excluded.band, "
                "best_doc=excluded.best_doc, scored_at=excluded.scored_at",
                payload)
            con.execute("COMMIT")
        except Exception as exc:
            con.execute("ROLLBACK")
            print(f"\nFAILED, rolled back: {exc}", file=sys.stderr)
            return 1
        print(f"\n{len(payload)} topic scores written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
