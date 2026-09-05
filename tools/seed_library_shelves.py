#!/usr/bin/env python
"""Create the library shelves and seed a starting set.

Run once. Idempotent: existing shelves keep their name, blurb and order, so a
re-run cannot overwrite a shelf that has been renamed.

THE SEED IS A STARTING POINT, NOT A TAXONOMY. The standing preference is more
narrow categories rather than fewer broad ones — a category broad enough to need
filtering costs time on every visit, while overlap between two narrow ones costs
almost nothing. So these are deliberately specific, and adding more is the
expected way to use this.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path.home() / ".local/share/metis/metis.sqlite"

# kind: purpose | tracking | attachment
SEED = [
    # PURPOSE — kept for HOW it was done. Timeless; raided when designing.
    ("methodology",   "Methodology",        "purpose",
     "Kept for how it was done — a design, an estimator, an analysis worth copying."),
    ("study-design",  "Study design",       "purpose",
     "Sampling, case definitions, comparison groups, the shape of a study."),
    ("writing",       "Writing & framing",  "purpose",
     "Papers kept for how they argue, structure or explain, not for their findings."),
    ("visualisation", "Visualisation",      "purpose",
     "Figures and tables worth stealing the form of."),
    ("data-sources",  "Data & sources",     "purpose",
     "Datasets, registries and routine-data sources, and what is known about their quality."),

    # TRACKING — following a field as it moves. Chronological.
    ("ai",            "AI",                 "tracking",
     "Following how AI in health develops — read in order, not raided."),
    ("genomics",      "Genomics",           "tracking",
     "Sequencing, lineages and what genomic data is being used to decide."),
    ("diagnostics",   "Diagnostics",        "tracking",
     "New tests, accuracy evidence and how case detection is changing."),
    ("elimination",   "Elimination & policy", "tracking",
     "Targets, verification, post-elimination surveillance and the policy around them."),
    ("outbreaks",     "Outbreaks",          "tracking",
     "Event-based reporting and outbreak investigations as they happen."),
]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60]


def main() -> int:
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    now = datetime.now().isoformat(timespec="seconds")

    # LET SQLITE PARSE ITS OWN DDL. Two hand-rolled attempts to pick the shelf
    # statements out of schema.sql — first a regex on the table-name prefix,
    # then a split on the statement terminator — each silently selected some of
    # the statements and not others, and the seeder then failed on a table it
    # believed it had created. The file is 92 CREATE TABLE and 22 CREATE INDEX
    # statements, every one of them IF NOT EXISTS, which is precisely what the
    # installer relies on: running the whole thing is idempotent by
    # construction and needs no parser of mine.
    ddl = (Path(__file__).parent.parent / "system/installer/schema.sql").read_text(encoding="utf-8")
    con.executescript(ddl)
    con.commit()
    for t in ("library_shelves", "library_shelf_items"):
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                           (t,)).fetchone():
            print(f"  ERROR: {t} still missing after running schema.sql")
            return 1

    added = kept = 0
    def put(slug, name, kind, blurb, ref="", order=0):
        nonlocal added, kept
        if con.execute("SELECT 1 FROM library_shelves WHERE slug=?", (slug,)).fetchone():
            kept += 1
            return
        con.execute(
            "INSERT INTO library_shelves (slug,name,kind,blurb,ref,sort_order,created_at) "
            "VALUES (?,?,?,?,?,?,?)", (slug, name, kind, blurb, ref, order, now))
        added += 1

    for i, (slug, name, kind, blurb) in enumerate(SEED):
        put(slug, name, kind, blurb, "", i)

    # ATTACHMENT shelves are DERIVED, never typed. A shelf per active research
    # project and per course he is taking — because "evidence for this piece of
    # work" is a category the dashboard can already name, and asking him to
    # retype names it already holds is how two spellings of one project appear.
    n0 = added
    for r in con.execute(
            "SELECT project_id, title FROM projects "
            "WHERE status IN ('active','incubating') "
            "AND LOWER(COALESCE(domain,'')) NOT IN ('software','tooling','personal') "
            "ORDER BY title"):
        put("proj-" + _slug(r["project_id"] or r["title"]), r["title"], "attachment",
            "Evidence and reading for this project.", r["project_id"] or "", 100)
    n_proj = added - n0

    n0 = added
    for r in con.execute(
            "SELECT slug, title FROM learning_courses "
            "WHERE status IN ('active','in_progress','building','paused') ORDER BY title"):
        put("course-" + _slug(r["slug"]), r["title"], "attachment",
            "Reading that belongs to this course.", r["slug"] or "", 200)
    n_course = added - n0

    con.commit()
    print(f"  shelves: {added} added ({n_proj} project, {n_course} course), {kept} already present")
    for k in ("purpose", "tracking", "attachment"):
        n = con.execute("SELECT COUNT(*) FROM library_shelves WHERE kind=? AND archived=0", (k,)).fetchone()[0]
        print(f"    {k:<11} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
