#!/usr/bin/env python3
"""evaluate_course_against_library.py — check a course against the corpus that
should support it.

WHY
    A course written from model knowledge is a set of claims with no provenance.
    That was acceptable while the library was not indexed — there was nothing to
    check against. Now that the HAT corpus is 220+ documents and semantically
    searchable, every lesson can be asked two questions it could not be asked
    before:

      1. ARE ITS CITATIONS REAL AND HELD? The lessons cite loosely — "Buscher P
         et al., Diagnostic accuracy of tests for gambiense HAT (open-access
         review)" — with no DOI and no link. Either that paper is in the library
         and the reference can be made precise, or it is not and the claim rests
         on nothing the researcher can open.

      2. WHAT DOES THE LIBRARY NOW KNOW THAT THE LESSON DOES NOT? A lesson
         written before the library was completed cannot cite the 144 papers
         reference mining has since surfaced, nor anything the parasitology feeds
         brought in. Newer, better-supported evidence may be sitting unused.

    Both are gaps a reader cannot see. A confident lesson and a well-sourced one
    look identical on the page.

WHAT IT DOES NOT DO
    It does not judge whether a lesson is CORRECT. It reports what is citable and
    what is available. Deciding whether a claim survives contact with the
    evidence is the researcher's job, and a tool that pretended otherwise would
    be the "LLM-judge" failure mode already documented in this backlog.

USAGE
    python3 tools/evaluate_course_against_library.py <course-slug>
    python3 tools/evaluate_course_against_library.py <course-slug> --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = os.environ.get("METIS_PORT", "8080")
BASE = f"http://127.0.0.1:{PORT}"


def db() -> sqlite3.Connection:
    c = sqlite3.connect(str(Path.home() / ".local/share/metis" / "metis.sqlite"))
    c.row_factory = sqlite3.Row
    return c


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def corpus_search(q: str, top_k: int = 5, min_score: float = 0.60) -> list[dict]:
    """Ask the running dashboard. Returns [] if it is not up."""
    url = (f"{BASE}/api/library/corpus-search?q={urllib.parse.quote(q)}"
           f"&top_k={top_k}&min_score={min_score}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read()).get("results", [])
    except Exception:
        return []


def extract_references(text: str) -> list[str]:
    """Pull the reference lines out of a lesson.

    The lessons use a trailing bullet list under a References / Further reading
    heading rather than inline citations, so that is what is parsed. Anything
    else would silently find nothing.
    """
    m = re.search(r"##+\s*(?:References|Sources|Further reading|Reading)\b(.*?)"
                  r"(?=\n##\s|\Z)", text, re.S | re.I)
    if not m:
        return []
    refs = []
    for line in m.group(1).splitlines():
        line = line.strip().lstrip("-*• ").strip()
        if len(line) > 15:
            refs.append(line)
    return refs


def reference_title(ref: str) -> str:
    """Best guess at the paper title inside a loose reference line."""
    # Prefer *italicised* text — the lessons put titles there.
    m = re.search(r"\*([^*]{12,})\*", ref)
    if m:
        return m.group(1).strip()
    # Otherwise take the part before the first em-dash or parenthesis.
    return re.split(r"\s+—\s+|\s+\(", ref)[0].strip()


def held_in_library(conn: sqlite3.Connection, title: str) -> dict | None:
    key = norm(title)
    if len(key) < 12:
        return None
    words = [w for w in key.split() if len(w) > 4][:6]
    if not words:
        return None
    clause = " AND ".join("lower(title) LIKE ?" for _ in words)
    row = conn.execute(
        f"SELECT id, title, year, doi FROM literature_metadata WHERE {clause} LIMIT 1",
        tuple(f"%{w}%" for w in words)).fetchone()
    if row:
        return dict(row)
    # Relax: any three of the distinctive words.
    for drop in range(1, min(4, len(words))):
        sub = words[:-drop]
        if len(sub) < 2:
            break
        clause = " AND ".join("lower(title) LIKE ?" for _ in sub)
        row = conn.execute(
            f"SELECT id, title, year, doi FROM literature_metadata "
            f"WHERE {clause} LIMIT 1", tuple(f"%{w}%" for w in sub)).fetchone()
        if row:
            return dict(row)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    course_dir = ROOT / "knowledge" / "courses" / args.slug
    if not course_dir.is_dir():
        print(f"✗ no course at {course_dir}")
        return 1

    meta = {}
    cj = course_dir / "course.json"
    if cj.exists():
        meta = json.loads(cj.read_text(encoding="utf-8"))

    conn = db()
    lessons = sorted((course_dir / "lessons").glob("*.md"))
    report = {"course": meta.get("title", args.slug), "lessons": []}

    print(f"\n{'=' * 74}")
    print(f"  {meta.get('title', args.slug)}")
    print(f"  {len(lessons)} lesson(s) · evaluated against the indexed corpus")
    print(f"{'=' * 74}")

    total_refs = held = missing = 0
    for path in lessons:
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = next((l.lstrip("# ").strip() for l in text.splitlines()
                      if l.startswith("#")), path.stem)
        refs = extract_references(text)

        entry = {"file": path.name, "title": title,
                 "references": [], "available_now": []}

        print(f"\n── {title[:66]}")
        if not refs:
            print("     references: none listed")
        for ref in refs:
            total_refs += 1
            rt = reference_title(ref)
            hit = held_in_library(conn, rt)
            if hit:
                held += 1
                mark = "✓ held"
                detail = f"#{hit['id']} {(hit.get('doi') or 'no DOI')}"
            else:
                missing += 1
                mark = "✗ NOT in library"
                detail = ""
            print(f"     {mark:<18} {rt[:52]} {detail}")
            entry["references"].append(
                {"raw": ref, "title": rt, "held": bool(hit),
                 "library_id": hit["id"] if hit else None,
                 "doi": (hit or {}).get("doi", "")})

        # What the corpus can now contribute to this lesson's topic.
        hits = corpus_search(title, top_k=4, min_score=0.66)
        if hits:
            print(f"     ── corpus offers {len(hits)} passage(s) for this topic:")
            for h in hits[:4]:
                print(f"        · [{h['score']}] {h['title'][:58]} p.{h['page']}")
            entry["available_now"] = hits
        conn_used = True
        report["lessons"].append(entry)

    print(f"\n{'=' * 74}")
    print(f"  references listed   : {total_refs}")
    print(f"  verifiably held     : {held}")
    print(f"  NOT in the library  : {missing}")
    print(f"{'=' * 74}")
    if missing:
        print("  A reference the researcher cannot open is a claim with no")
        print("  provenance. Either acquire it, or soften the claim.")

    out = ROOT / "outputs" / "reviews" / "learning-architect"
    out.mkdir(parents=True, exist_ok=True)
    import datetime
    p = out / f"{datetime.date.today().isoformat()}_{args.slug}_library-check.json"
    p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n  report: {p.relative_to(ROOT)}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
