#!/usr/bin/env python3
"""repair_filename_titles.py — recover author, year and title from filename stems.

WHAT WAS WRONG
    211 of 726 `literature_metadata` rows were created by `scan_literature_folder()`,
    which inserts a PDF's filename stem as the title and literally the string
    'unknown' as the authors, with a NULL year:

        title   = '2004_Fèvre_Reanalyzing-the-19001920-Sleeping-Sickness'
        authors = 'unknown'
        year    = NULL

    Every one of those is a real paper, and in 179 of them the author and year are
    sitting RIGHT THERE in the title string, unparsed. The result:

      · unsearchable by author — the field says 'unknown'
      · unsortable by year — the field is NULL
      · and invisible in the browser, because both library routes filtered out
        any title starting with '19' or '20' to hide exactly these rows

    So the surface's answer to badly-parsed metadata was to hide the papers.
    That is the worst option available: a reference you own, cannot find, and are
    never told about. Fèvre 2004 on the 1900–1920 Ugandan epidemic is not a
    stray file — it is core material for this researcher.

WHAT THIS DOES
    Parses `YYYY_Author_Title-with-dashes` into real fields, then clears the
    filter's reason to exist. Conservative throughout:

      · only touches rows whose title matches the pattern
      · only fills authors when the current value is empty or 'unknown'
      · only fills year when it is NULL
      · keeps the original stem in `tags` so nothing is unrecoverable

    Hyphen-to-space is the one lossy step: a genuinely hyphenated term
    ('Spatio-temporal') becomes two words. Accepted deliberately — a slightly
    imperfect readable title beats a perfect unreadable one, and search tokenises
    on both anyway.

USAGE
    python3 tools/repair_filename_titles.py --dry-run
    python3 tools/repair_filename_titles.py
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

# YYYY_Author_Some-Title-With-Dashes
_STEM_RE = re.compile(r"^(\d{4})_([^_]{2,40})_(.+)$")

# Words that are not a surname, seen in this corpus's filenames.
_NOT_AUTHORS = {"who", "unknown", "anon", "various", "et", "al", "report"}


def clean_title(raw: str) -> str:
    """Turn 'Reanalyzing-the-19001920-Sleeping-Sickness' into readable prose."""
    t = raw.replace("-", " ").replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip()
    # A run of 8 digits is a mangled year range: 19001920 → 1900-1920.
    t = re.sub(r"\b(\d{4})(\d{4})\b", r"\1-\2", t)
    return t[:1].upper() + t[1:] if t else t


def parse_stem(stem: str) -> tuple[str, str, int] | None:
    """(title, author, year) from a filename stem, or None if it does not match."""
    m = _STEM_RE.match(stem.strip())
    if not m:
        return None
    year_s, author, rest = m.groups()
    year = int(year_s)
    if not (1800 <= year <= 2100):
        return None
    author = author.strip()
    if author.lower() in _NOT_AUTHORS or author.isdigit():
        author = ""
    title = clean_title(rest)
    if len(title) < 8:
        return None
    return title, author, year


def db_path() -> Path:
    env = os.environ.get("METIS_DB_PATH", "")
    if env and Path(env).exists():
        return Path(env)
    return Path.home() / ".local/share/metis" / "metis.sqlite"


def main() -> int:
    dry = "--dry-run" in sys.argv
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row

    rows = con.execute(
        "SELECT id, title, authors, year, tags FROM literature_metadata "
        "WHERE title LIKE '%\\_%' ESCAPE '\\'"
    ).fetchall()

    repaired = skipped = 0
    shown = 0
    for r in rows:
        parsed = parse_stem(r["title"])
        if not parsed:
            skipped += 1
            continue
        title, author, year = parsed

        new_authors = r["authors"]
        if not (r["authors"] or "").strip() or (r["authors"] or "").lower() == "unknown":
            new_authors = author or ""
        new_year = r["year"] if r["year"] else year

        # Preserve the original stem so the repair is reversible and the file on
        # disk can still be found by its real name.
        tags = (r["tags"] or "").strip()
        stem_tag = f"filestem:{r['title']}"
        new_tags = tags if stem_tag in tags else (f"{tags},{stem_tag}" if tags else stem_tag)

        if shown < 10:
            print(f"  {r['title'][:58]}")
            print(f"    → {title[:66]}")
            print(f"      author={new_authors or '(none)'}  year={new_year}")
            shown += 1

        if not dry:
            con.execute(
                "UPDATE literature_metadata SET title=?, authors=?, year=?, tags=? "
                "WHERE id=?",
                (title[:500], (new_authors or "")[:300], new_year,
                 new_tags[:600], r["id"]),
            )
        repaired += 1

    if not dry:
        con.commit()
    total = con.execute("SELECT COUNT(*) FROM literature_metadata").fetchone()[0]
    still_unknown = con.execute(
        "SELECT COUNT(*) FROM literature_metadata "
        "WHERE COALESCE(authors,'')='' OR lower(authors)='unknown'"
    ).fetchone()[0]
    con.close()

    print(f"\n  repaired {repaired}, left alone {skipped}")
    print(f"  {total} catalogue rows; {still_unknown} still without an author")
    print(f"  {'DRY RUN — nothing written' if dry else '✓ applied'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
