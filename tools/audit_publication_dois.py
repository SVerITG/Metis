#!/usr/bin/env python3
"""Find library rows whose DOI points at a DIFFERENT paper than the row claims.

WHY THIS EXISTS
    Found 2026-09-04 while promoting one feed row to a cited reference. The row
    carried DOI 10.1038/d41586-026-02716-w. The real DOI — sitting in that same
    row's own abstract, and in its source_url — is 10.1038/d41586-026-02684-1.
    The `authors` field named a different person than the article's byline. Both
    values had been taken from a neighbouring item in the same feed batch.

    TWO FAILURE MODES, AND THE SECOND IS THE DANGEROUS ONE:
      - a DOI that does not resolve at all — obvious the moment you click it;
      - a DOI that resolves to a real but DIFFERENT paper — checkable-looking
        and wrong, and it will be copied into a manuscript unexamined.

    Every row found so far is the second kind.

    Measured across 1,111 rows carrying a DOI: 119 DOIs are attached to more
    than one distinct title, covering 957 titles; 158 rows name a DOI in their
    own abstract that contradicts their doi column. Every one is a Nature-family
    feed (Nature 50, Nature Comms 42, Nature Medicine 23, Nature Microbiology
    15, Nature Mach Intell 13, Nature Rev Microbiol 8, Nature Rev Dis Primers 7).

WHAT IT IS NOT
    A network check. `tools/check_course_dois.py` already resolves DOIs against
    Crossref; this one needs no network, because these rows CONTRADICT
    THEMSELVES. The truth is already in the row: Nature's feed puts the article's
    own DOI in its description ("...; doi:10.1038/...") and its slug in the URL.
    An internal-consistency check is cheaper, offline, and cannot be confounded
    by a rate limit or a failed content negotiation.

IS THE INGEST STILL DOING THIS?
    No — checked 2026-09-04. `_entry_doi` in content_scan.py reads `prism_doi`
    per entry, and feedparser returns the correct per-item value for Nature's
    RSS today. These rows are legacy. That is why this tool repairs data and
    changes no parser.

THE CONTROL
    Runs two synthetic rows first — one consistent, one deliberately
    contradictory — and refuses to judge the library unless it calls them
    differently. A checker that returns the same verdict for a good row and a
    bad one is decoration.

USAGE
    python3 tools/audit_publication_dois.py              # report only
    python3 tools/audit_publication_dois.py --apply      # repair the doi column
    python3 tools/audit_publication_dois.py --limit 40   # show more examples
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# "...; doi:10.1038/d41586-026-02684-1" — how Nature states it in a description.
_DOI_IN_TEXT = re.compile(r"doi:\s*(10\.\d{4,9}/[^\s;<)\]]+)", re.I)
# A Nature article URL ends in the article's own slug, which IS its DOI suffix.
_NATURE_SLUG = re.compile(r"nature\.com/articles/([a-z0-9.\-]+)", re.I)

# ── THE SECOND SOURCE OF TRUTH: THE ROW'S OWN URL ────────────────────────────
# Most publishers put the article's identifier straight in its link, so a row
# whose DOI was batch-stamped still carries the right one in `source_url`:
#
#   medRxiv   /content/10.64898/2026.09.01.26361950v1
#   Springer  link.springer.com/10.1186/s12879-026-14170-0
#   eLife     dx.doi.org/10.7554/eLife.107818
#   Elsevier  /article/PIIS1473-3099(26)00430-5/fulltext   (a PII, not a DOI)
#
# An Elsevier PII maps to a DOI by prefixing the Elsevier registrant: PII
# S1473-3099(26)00430-5 is DOI 10.1016/S1473-3099(26)00430-5. Verified against
# Crossref on 2026-09-04 across 16 rows spanning 12 feeds: 16 correct, 0 wrong.
_DOI_IN_URL = re.compile(r"(10\.\d{4,9}/[^\s?&#]+)")
_ELSEVIER_PII = re.compile(r"/PII([SB]\d{4}-\d{4}\(\d{2}\)\d{5}-[\dXx])", re.I)
# Trailing decoration a link adds and a DOI does not carry.
_URL_TAIL = re.compile(r"(v\d+)?(\.full(-text)?|\.pdf|/fulltext|/abstract)?/?$")


def db_path() -> Path:
    return Path(os.environ.get("METIS_DB")
                or Path.home() / ".local" / "share" / "metis" / "metis.sqlite")


def norm(doi: str) -> str:
    d = (doi or "").strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d.rstrip(".,;)")


def doi_from_url(url: str) -> str:
    """The DOI an article link carries, or ''. See the patterns above."""
    u = url or ""
    m = _ELSEVIER_PII.search(u)
    if m:
        return norm(f"10.1016/{m.group(1)}")
    m = _NATURE_SLUG.search(u)
    if m:
        slug = m.group(1).rstrip("/.")
        # Only a slug shaped like a Nature DOI suffix, never a section path.
        if re.match(r"^[sd]4\d{4}-\d{3}-\d{4,6}-[a-z0-9]$", slug):
            return norm(f"10.1038/{slug}")
    m = _DOI_IN_URL.search(u)
    if m:
        return norm(_URL_TAIL.sub("", m.group(1)))
    return ""


def truth_for(row: dict) -> tuple[str, str] | None:
    """The DOI this row itself asserts, and where it said so. None if silent.

    The abstract wins over the URL: it is the publisher's own statement of the
    DOI, whereas a URL has to be parsed, and a parse can be wrong.
    """
    m = _DOI_IN_TEXT.search(row.get("abstract") or "")
    if m:
        return norm(m.group(1)), "abstract"
    d = doi_from_url(row.get("source_url") or "")
    if d:
        return d, "source_url"
    return None


def verdict(row: dict) -> tuple[str, str, str]:
    """(status, truth, where). status in {ok, mismatch, no_claim, no_doi}."""
    col = norm(row.get("doi") or "")
    if not col:
        return "no_doi", "", ""
    t = truth_for(row)
    if not t:
        return "no_claim", "", ""
    truth, where = t
    return ("ok" if truth == col else "mismatch"), truth, where


def run_control() -> bool:
    good = {"doi": "10.1038/d41586-026-02684-1", "source_url":
            "https://www.nature.com/articles/d41586-026-02684-1",
            "abstract": "Nature, Published online: 30 August 2026; "
                        "doi:10.1038/d41586-026-02684-1 Spread of diseases."}
    bad = dict(good, doi="10.1038/d41586-026-02716-w")
    vg, vb = verdict(good)[0], verdict(bad)[0]
    print(f"  control: consistent row -> {vg} | contradictory row -> {vb}")
    return vg == "ok" and vb == "mismatch"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="rewrite the doi column of mismatching rows")
    ap.add_argument("--limit", type=int, default=15, help="examples to print")
    args = ap.parse_args()

    print("── DOI misattribution audit ──")
    if not run_control():
        print("  CONTROLS DID NOT DIFFER — refusing to judge the library.")
        return 2
    print("  controls differ; proceeding\n")

    db = db_path()
    if not db.exists():
        print(f"database not found: {db}")
        return 1
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT id, title, doi, abstract, source_url, authors, feed_name "
        "FROM new_publications")]

    # A DOI worn by several DIFFERENT titles is the damage signature: a DOI is
    # unique to a paper, so this cannot be anything but wrong.
    shared_doi: dict[str, set] = defaultdict(set)
    for r in rows:
        d = norm(r.get("doi") or "")
        if d:
            shared_doi[d].add((r.get("title") or "").strip().lower())

    buckets: dict[str, list[dict]] = defaultdict(list)
    fixes: list[tuple[int, str, str, str]] = []
    held_back = 0
    for r in rows:
        st, truth, where = verdict(r)
        buckets[st].append(r)
        if st != "mismatch":
            continue
        # THE GUARD. An abstract that states a DOI is the publisher speaking, so
        # it is repaired on its own authority. A URL is only PARSED, so it is
        # trusted solely where the stored DOI is already provably wrong — worn
        # by more than one title. Without this, a healthy row whose link points
        # at a related object would be "corrected" into being wrong.
        if where == "source_url" and len(shared_doi[norm(r["doi"])]) < 2:
            held_back += 1
            continue
        fixes.append((r["id"], norm(r["doi"]), truth, where))

    print(f"rows examined:            {len(rows)}")
    print(f"  carry no DOI:           {len(buckets['no_doi'])}")
    print(f"  DOI, row says nothing:  {len(buckets['no_claim'])}  (not checkable offline)")
    print(f"  DOI agrees with the row: {len(buckets['ok'])}")
    print(f"  DOI CONTRADICTS the row: {len(buckets['mismatch'])}   <- misattributed")
    print(f"  repairable now:          {len(fixes)}")
    if held_back:
        print(f"  held back by the guard:  {held_back}  (URL disagrees, but the "
              f"stored DOI is unique — not provably the batch-stamping fault)")
    by_src: dict[str, int] = defaultdict(int)
    for _i, _c, _t, w in fixes:
        by_src[w] += 1
    if by_src:
        print("  truth taken from: " +
              ", ".join(f"{k} {v}" for k, v in sorted(by_src.items())))

    # A DOI worn by several different titles is the same fault seen from the
    # other side, and it catches rows whose abstract is empty.
    byd: dict[str, set] = defaultdict(set)
    for r in rows:
        d = norm(r.get("doi") or "")
        if d:
            byd[d].add((r.get("title") or "").strip().lower())
    shared = {d: t for d, t in byd.items() if len(t) > 1}
    print(f"\nDOIs attached to >1 distinct title: {len(shared)}, "
          f"covering {sum(len(t) for t in shared.values())} titles")

    by_feed: dict[str, int] = defaultdict(int)
    for r in buckets["mismatch"]:
        by_feed[r.get("feed_name") or "?"] += 1
    if by_feed:
        print("misattributed by feed: " +
              ", ".join(f"{k} {v}" for k, v in sorted(by_feed.items(),
                                                      key=lambda kv: -kv[1])))

    if fixes:
        print(f"\nexamples (showing {min(args.limit, len(fixes))} of {len(fixes)}):")
        for rid, col, truth, where in fixes[:args.limit]:
            title = next(r["title"] for r in rows if r["id"] == rid)
            print(f"  id={rid}")
            print(f"     stored: {col}")
            print(f"     actual: {truth}   (from the row's own {where})")
            print(f"     {title[:88]}")

    print("\nNOTE: `authors` is wrong on many of the same rows and CANNOT be "
          "repaired from the row itself — it needs Crossref. Not attempted here.")

    if not fixes:
        print("\nnothing to repair.")
        return 0
    if not args.apply:
        print(f"\nDRY RUN — re-run with --apply to repair {len(fixes)} doi value(s).")
        return 0

    for rid, _col, truth, _where in fixes:
        con.execute("UPDATE new_publications SET doi=? WHERE id=?", (truth, rid))
    con.commit()
    print(f"\nREPAIRED {len(fixes)} row(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
