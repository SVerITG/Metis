#!/usr/bin/env python3
"""Check that every DOI in a course resolves, and points at the paper claimed.

Two different failures, and the second is the dangerous one:

  1. The DOI does not exist. A fabricated citation.
  2. The DOI exists but resolves to a DIFFERENT paper than the surrounding text
     claims. A citation that looks checkable, passes a glance, and is wrong.

Only the second needs Crossref metadata, so that is what this does: fetch the
record, compare first author and year against what the lesson line asserts.

It runs a control pair FIRST — a DOI that certainly exists and one that certainly
does not — and refuses to judge any real DOI unless those two come back different.
A checker that returns the same answer for pass and fail is decoration, and this
one has already been caught doing exactly that: an earlier version requested CSL
JSON via content negotiation, which failed silently for every DOI and reported all
ten citations in `ai-in-public-health` as unresolvable. They were all fine.

Usage:
    python3 tools/check_course_dois.py --all
    python3 tools/check_course_dois.py ai-in-public-health genomic-surveillance
"""
import os
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COURSES = ROOT / "knowledge" / "courses"
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
# Crossref asks callers for a contact address so it can reach you about a
# misbehaving script, and rewards giving one with the faster "polite" pool. It
# was hard-coded to a real address in a repository that is PUBLIC on GitHub —
# checked 2026-09-02, both Metis and Metis_PH return 200 unauthenticated. An
# address in source is a published address. Set METIS_CROSSREF_MAILTO to opt
# back into the polite pool; without it the script still works, just slower.
MAILTO = os.environ.get("METIS_CROSSREF_MAILTO", "")


def _user_agent() -> str:
    """The User-Agent header, with a contact address only if one is configured.

    `(mailto:)` with nothing after it is worse than omitting it: Crossref reads
    a malformed contact as an unidentified caller anyway, and it reads to a
    human as a bug.
    """
    if MAILTO:
        return f"User-Agent: metis-course-check (mailto:{MAILTO})"
    return "User-Agent: metis-course-check"


def crossref(doi: str):
    r = subprocess.run(
        ["curl", "-sL", "--max-time", "20",
         "-H", _user_agent(),
         f"https://api.crossref.org/works/{doi}"],
        capture_output=True, text=True)
    try:
        m = json.loads(r.stdout)["message"]
    except Exception:
        return None
    title = (m.get("title") or [""])
    authors = m.get("author") or []
    return {
        "title": (title[0] if title else "").strip(),
        "first_author": authors[0].get("family", "") if authors else "",
        "year": ((m.get("issued", {}).get("date-parts") or [[None]])[0] or [None])[0],
        "journal": (m.get("container-title") or [""])[0],
    }


def control_ok() -> bool:
    good = crossref("10.1038/s41586-020-2649-2")   # the NumPy paper
    bad = crossref("10.9999/definitely.not.a.real.doi")
    if good and good.get("first_author") and bad is None:
        print("  control: known-good resolves, known-bad does not. Check discriminates.\n")
        return True
    print(f"  control FAILED (good={bool(good)}, bad={bad is not None}) — "
          "the check cannot tell pass from fail. Aborting rather than reporting.\n")
    return False


def claimed(line: str):
    """What the lesson line asserts, as (first author, year). '?' when not stated."""
    # bolded surname, skipping bolded journal names that follow the title
    cands = re.findall(r"\*\*([A-Z][A-Za-z\-']+)[ ,.]", line)
    cands += re.findall(r"\b([A-Z][a-z]{3,})\s+(?:et al\.|[A-Z]{1,3}[,.])", line)
    years = re.findall(r"\b((?:19|20)\d{2})\b", line)
    return (cands[0] if cands else "?", years[0] if years else "?")


def scan(slug: str):
    base = pathlib.Path(slug) if pathlib.Path(slug).is_dir() else COURSES / slug
    if not base.is_dir():
        raise SystemExit(f"no such course: {slug}")
    found = {}
    for f in sorted(base.rglob("*.md")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            for doi in DOI_RE.findall(line):
                found.setdefault(doi.rstrip(".,;)"), (f.name, line.strip()))
    return base, found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("courses", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    targets = list(args.courses)
    if args.all:
        targets = sorted(d.name for d in COURSES.iterdir() if d.is_dir())
    if not targets:
        ap.error("name a course, or pass --all")

    print("DOI check")
    if not control_ok():
        return 2

    bad, suspect, total = [], [], 0
    for slug in targets:
        base, found = scan(slug)
        if not found:
            continue
        print(f"{base.name}  ({len(found)} DOIs)")
        for doi, (fname, line) in sorted(found.items()):
            total += 1
            cr = crossref(doi)
            if cr is None:
                print(f"  ✗ NOT FOUND       {doi}   [{fname}]")
                bad.append((slug, doi, fname)); continue
            ca, cy = claimed(line)
            a_ok = ca == "?" or ca.lower() == cr["first_author"].lower()
            y_ok = cy == "?" or (cr["year"] and abs(int(cy) - int(cr["year"])) <= 1)
            if a_ok and y_ok:
                print(f"  ✓ {cr['first_author']} {cr['year']}".ljust(22)
                      + f"{doi}   {cr['title'][:52]}")
            else:
                print(f"  ⚠ claims {ca} {cy}, record says "
                      f"{cr['first_author']} {cr['year']}   {doi}   [{fname}]")
                suspect.append((slug, doi, fname, ca, cy, cr))
        print()

    print("-" * 100)
    summary = f"{total} DOIs · {len(bad)} unresolvable · {len(suspect)} needing a human look"
    if suspect:
        print("\nAuthor extraction is heuristic — a bolded journal name before the author "
              "trips it. Read each of these lines before concluding anything:")
        for slug, doi, fname, ca, cy, cr in suspect:
            print(f"  {slug}/{fname}: {doi} — claims '{ca} {cy}', "
                  f"record is {cr['first_author']} {cr['year']}, {cr['title'][:60]}")
    # Summary last, so `| tail -1` is a valid check. It was not, and a verification
    # script grepping the last three lines reported this tool as failing when it
    # had passed — the check on the check being wrong rather than the check.
    print()
    print("RESULT: " + summary)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
