#!/usr/bin/env python3
"""Does each Today board row link to the thing it claims to be?

WHY
    The boards gained a visible date column on 2026-09-02, and with the rows
    finally legible it became obvious that some links do not go where the title
    says. One congress row pointed at an unrelated travel-medicine listing on a
    different society's site; two outbreak rows pointed at generic landing pages
    (a disease fact sheet, an "outbreaks and other emergencies updates" index)
    rather than at the outbreak named in the row.

    That is the same defect class as the retired top-bar search, whose results
    all linked to a tab instead of to the paper: a link that resolves is not the
    same as a link that is right.

WHAT IT CHECKS — WITHOUT THE NETWORK
    Deliberately offline. It compares the row's own words against the URL's
    host and path, and reports three grades:

      ok        the URL's host or path carries the row's distinctive words, or
                the path has the shape of a single item ("/item/2026-DON613")
      generic   the URL names nothing in the row — a section or landing page
      mismatch  the path names something the row does not mention at all

    It cannot tell whether a page has since moved or been rewritten; only a
    fetch can, and fetching every board URL on a schedule is a different tool
    with different permissions. This one is safe to run any time and catches
    the case that actually occurred.

USAGE
    python3 tools/check_board_links.py
    python3 tools/check_board_links.py --board outbreaks
"""
from __future__ import annotations

import argparse
import contextlib
import os
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

DB = Path(os.environ.get("METIS_DB")
          or (Path.home() / ".local/share/metis/metis.sqlite"))

# Structural URL furniture and English filler only. NOTE what is deliberately
# NOT here: "outbreak", "disease", "congress", or any disease name — those are
# the words that make a link identifiable, and stopping them was why the first
# version of this tool flagged six rows of which five were correct.
STOP = set("""the and for with from into onto that this than then when what which your you
are was were not but its his her their them these those how why who whom does did can could
should would may might must have has had been being over under versus per via out off all
any one two three as at by in of on to or an is it be do if so no up
item items detail details page index html htm php aspx www http https
about home default main list view show search""".split())

# A path segment that names a SPECIFIC item, even when the identifier itself is
# opaque. `/disease-outbreak-news/item/2026-DON613` is exactly the right shape
# for an outbreak row; the id is not supposed to be readable.
_ITEM_SHAPE = re.compile(
    r"/(item|items|detail|article|news|entry|record)/[^/]{4,}", re.I)


def words(text: str) -> set[str]:
    """Three characters, not four: a three-letter country or agency acronym is
    identifying, and requiring four dropped them."""
    return {w for w in re.findall(r"[a-z0-9]{3,}", str(text or "").lower())
            if w not in STOP}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="")
    args = ap.parse_args()

    if not DB.is_file():
        print(f"database not found: {DB}", file=sys.stderr)
        return 2

    with contextlib.closing(sqlite3.connect(f"file:{DB}?mode=ro", uri=True)) as c:
        c.row_factory = sqlite3.Row
        sql = ("SELECT id, board, source, title, url FROM today_board_items "
               "WHERE dismissed=0")
        params: tuple = ()
        if args.board:
            sql += " AND board=?"
            params = (args.board,)
        rows = c.execute(sql + " ORDER BY board, id", params).fetchall()

    findings = []
    print(f"{'id':>4}  {'board':10s} {'verdict':9s} row")
    print("-" * 96)
    for r in rows:
        url = str(r["url"] or "").strip()
        title_w = words(r["title"])
        if not url:
            verdict = "no-link"
        else:
            p = urlparse(url)
            # The HOST counts. A congress whose row links to the root of its own
            # site — ectmih2027.eu for "ECTMIH 2027" — is correct, and judging
            # on the path alone called that generic.
            host_w = words(p.netloc.replace(".", " ").replace("-", " "))
            path_w = words(p.path.replace("-", " ").replace("_", " ").replace("/", " "))
            # A host is often ONE token with the name and year run together —
            # "ectmih2027.eu" — so word-for-word matching missed it. Compare by
            # containment against the flattened host as well.
            host_flat = re.sub(r"[^a-z0-9]", "", p.netloc.lower())
            in_host = any(w in host_flat for w in title_w if len(w) >= 4)
            if (title_w & (host_w | path_w)) or in_host:
                verdict = "ok"
            elif _ITEM_SHAPE.search(p.path):
                verdict = "ok"          # points at one item, opaque id and all
            elif not path_w:
                verdict = "generic"     # a bare host that names nothing in the row
            else:
                verdict = "mismatch"    # the path names something else entirely
        if verdict in ("mismatch", "generic", "no-link"):
            findings.append((r["id"], r["board"], verdict, r["title"], url))
        print(f"{r['id']:>4}  {r['board']:10s} {verdict:9s} {str(r['title'])[:56]}")
        if verdict != "ok":
            print(f"{'':>4}  {'':10s} {'':9s} \033[2m{url[:88]}\033[0m"
                  if sys.stdout.isatty() else f"{'':>4}  {'':10s} {'':9s} {url[:88]}")

    print("-" * 96)
    if not findings:
        print("every board row links to something its title identifies.")
        return 0
    print(f"{len(findings)} row(s) worth a look:\n")
    for i, b, v, t, u in findings:
        print(f"  [{i}] {b} · {v}")
        print(f"       {t}")
        print(f"       {u or '(no url)'}")
    print("\nNothing was changed. A 'generic' link resolves but lands on a section;")
    print("a 'mismatch' points at something the title does not name. Re-run the")
    print("board's Update to have those replaced, or edit the row by hand.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
