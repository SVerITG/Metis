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


def topics_for(slug: str) -> list[str]:
    f = ROOT / "knowledge" / "courses" / slug / "lessons.json"
    if not f.is_file():
        return []
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  ! {slug}: lessons.json unreadable: {exc}", file=sys.stderr)
        return []
    lessons = d if isinstance(d, list) else d.get("lessons", [])
    seen: dict[str, str] = {}
    for L in lessons:
        if not isinstance(L, dict):
            continue
        for t in _as_list(L.get("topics")):
            t = " ".join(t.split())
            if MIN_LEN <= len(t) <= MAX_LEN:
                seen.setdefault(t.lower(), t)   # first spelling wins
    return list(seen.values())[:MAX_PER_COURSE]


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
        print(f"{'course':44s} {'lessons.json':13s} {'topics':>7s}  action")
        print("-" * 88)
        for r in rows:
            if args.slug and r["slug"] != args.slug:
                continue
            have_file = (ROOT / "knowledge" / "courses" / r["slug"] / "lessons.json").is_file()
            topics = topics_for(r["slug"])
            title = (r["title"] or r["slug"])[:44]
            if not topics:
                print(f"{title:44s} {'yes' if have_file else 'no':13s} {0:>7d}  skip"
                      f"{'' if have_file else ' (no lessons.json)'}")
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
            print(f"{title:44s} {'yes':13s} {len(topics):>7d}  {action}")

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
