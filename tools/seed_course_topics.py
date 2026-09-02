#!/usr/bin/env python3
"""Seed `course_topics` from each course's own lessons.json.

WHY THIS EXISTS
    Teach's gap analysis compares a course's topics against the library. The
    table it reads, `course_topics`, was EMPTY for every course — the structural
    audit lists it among seventeen tables that have a writer and no rows — so the
    panel fell back to "words in the course title longer than three characters"
    and asked whether any abstract contained them. Every course came out at
    "100% in library, 0% gap": three identical full bars under a heading that
    says gap analysis. A check that returns the same answer whatever the input
    is decoration.

    The topics were never missing. Each course's `lessons.json` already declares
    a `topics` list per lesson — 99 distinct for one course, 105 for another,
    and they are real subject topics ("Class imbalance and calibration",
    "Adaptive sampling", "Coalescent intuition"). This tool copies them in.

WHAT IT DELIBERATELY DOES NOT USE
    `key_terms`. Those are the vocabulary a reader is meant to learn, and many
    are two- or three-letter acronyms — BAM, ESS, DTA, MDR, AUC. Matched with
    LIKE against 3,000 abstracts every one of them hits something, so seeding
    them would rebuild the always-covered panel out of different parts.

IDEMPOTENT
    Replaces a course's own rows and leaves other courses alone, so re-running
    after editing a lessons.json is safe.

USAGE
    python3 tools/seed_course_topics.py            # dry run: report only
    python3 tools/seed_course_topics.py --apply    # write
    python3 tools/seed_course_topics.py --apply --slug genomic-surveillance
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("METIS_DB")
          or (Path.home() / ".local/share/metis/metis.sqlite"))

# A topic has to be worth asking the library about. One word is usually a
# category rather than a topic ("Surveillance"), and anything very long is a
# sentence someone wrote in a hurry.
MIN_LEN, MAX_LEN = 4, 80
MAX_PER_COURSE = 60


def _as_list(v) -> list[str]:
    """lessons.json stores these as JSON lists, but some rows arrive as the
    str() of a Python list. Accept both rather than losing a course to a quoting
    difference."""
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str) and v.strip().startswith("["):
        try:
            out = ast.literal_eval(v)
            return [str(x) for x in out] if isinstance(out, list) else []
        except Exception:
            return []
    return []


def topics_for(slug: str) -> tuple[list[str], str]:
    """(topics, where they came from).

    THREE SOURCES, in order of how much they were authored as topics:

      declared   a `topics` list per lesson. Two courses have full manifests
                 like this and their topics are real subject topics.
      titles     the five older manifests carry only
                 `id/order/section/title/description`. A lesson TITLE is a
                 topic someone chose deliberately ("Formulating Research
                 Questions"), so it is a fair second source. `description` is
                 NOT used: it is prose, and a sentence is not a topic.
      none       an idea-stage course has an empty manifest. Nothing to
                 extract, and inventing topics for a course that does not exist
                 yet would be putting words in the author's mouth — the surface
                 reports these separately instead.
    """
    f = ROOT / "knowledge" / "courses" / slug / "lessons.json"
    if not f.is_file():
        return [], "no manifest"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  ! {slug}: lessons.json unreadable: {exc}", file=sys.stderr)
        return [], "unreadable"
    lessons = d if isinstance(d, list) else d.get("lessons", [])
    if not lessons:
        return [], "no lessons yet"

    def collect(pick) -> dict[str, str]:
        out: dict[str, str] = {}
        for L in lessons:
            if not isinstance(L, dict):
                continue
            for t in pick(L):
                t = " ".join(str(t).split())
                # Strip a leading "Lesson 3 — " / "Ch 0 — " label: the number is
                # position, not subject.
                t = re.sub(r"^(lesson|ch|chapter|module|part)\s*\d+\s*[—:\-]\s*",
                           "", t, flags=re.I)
                if MIN_LEN <= len(t) <= MAX_LEN:
                    out.setdefault(t.lower(), t)
        return out

    declared = collect(lambda L: _as_list(L.get("topics")))
    if declared:
        return list(declared.values())[:MAX_PER_COURSE], "declared"

    titled = collect(lambda L: [x for x in (L.get("title"), L.get("section")) if x])
    if titled:
        return list(titled.values())[:MAX_PER_COURSE], "lesson titles"
    return [], "nothing usable"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write to the database")
    ap.add_argument("--slug", default="", help="only this course")
    args = ap.parse_args()

    if not DB.is_file():
        print(f"database not found: {DB}", file=sys.stderr)
        return 2

    with contextlib.closing(sqlite3.connect(str(DB), timeout=15)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS course_topics (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            keyword   TEXT NOT NULL)""")
        rows = conn.execute(
            "SELECT id, slug, title, status FROM learning_courses "
            "WHERE COALESCE(slug,'') != '' ORDER BY title").fetchall()

        total_written = 0
        print(f"{'course':40s} {'status':7s} {'source':14s} {'topics':>6s}  action")
        print("-" * 88)
        for r in rows:
            if args.slug and r["slug"] != args.slug:
                continue
            topics, origin = topics_for(r["slug"])
            title = (r["title"] or r["slug"])[:40]
            if not topics:
                print(f"{title:40s} {r['status'] or '?':7s} {origin:14s} {0:>6d}  skip")
                continue
            if args.apply:
                conn.execute("DELETE FROM course_topics WHERE course_id=?", (r["id"],))
                conn.executemany(
                    "INSERT INTO course_topics (course_id, keyword) VALUES (?, ?)",
                    [(r["id"], t) for t in topics])
                total_written += len(topics)
                action = "written"
            else:
                action = "would write"
            print(f"{title:40s} {r['status'] or '?':7s} {origin:14s} {len(topics):>6d}  {action}")

        if args.apply:
            conn.commit()
            print("-" * 88)
            print(f"{total_written} topic rows written across the courses above.")
        else:
            print("-" * 88)
            print("Dry run. Nothing written — re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
