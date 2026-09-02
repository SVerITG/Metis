#!/usr/bin/env python3
"""Collapse duplicate rows in `literature_metadata`, merging what they know.

THE PROBLEM
    3,084 rows carried 1,099 distinct titles. One paper was stored 26 times.
    The copies usually differ only in journal capitalisation ("PLOS Neglected
    Tropical Diseases" against "PLoS neglected tropical diseases") — the same
    record re-imported under a slightly different rendering of its metadata.

    Last year's dedupe work covered the RAG corpus (48,624 chunks to 40,747) and
    never touched this table, so every figure drawn from it was inflated: the
    Library head said "3,084 papers", the undecided-papers backlog said 2,282,
    and a search for "reservoir hosts" returned the same paper six times.

MERGE, DO NOT JUST PICK
    Copies are not identical. One may carry the DOI, another the abstract,
    another a Zotero key, another the fact that you have read it. Keeping the
    "best" row and dropping the rest would throw away real metadata. So the
    survivor INHERITS every field the others have and it lacks, and inherits
    read state if ANY copy was read — read is a fact about the paper, not about
    the row that happened to record it.

SAFETY
    - Nothing references `literature_metadata.id`. Verified before writing this:
      the six tables carrying an `item_id`/`source_id` all scope theirs to other
      entities (news, competencies, course slugs) and not one holds a numeric id
      matching a literature row. `pdf_index_state.id` and `pdf_title_aliases.id`
      are those tables' OWN primary keys, not links.
    - Dry run by default. `--apply` writes, inside one transaction.
    - Every deleted row is written to an audit file first, so the decision is
      reviewable and reversible from a backup.

USAGE
    python3 tools/dedupe_literature.py                  # report only
    python3 tools/dedupe_literature.py --apply
    python3 tools/dedupe_literature.py --apply --audit /path/to/log.tsv
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import os
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("METIS_DB")
          or (Path.home() / ".local/share/metis/metis.sqlite"))

# Fields worth inheriting from a copy that is about to be deleted, in no
# particular order — each is filled on the survivor only if the survivor's own
# value is empty.
INHERIT = ("authors", "year", "source", "tags", "doi", "abstract", "journal",
           "item_type", "url", "zotero_key", "collection", "library_source")

_TAG = re.compile(r"<[^>]+>")
_NONWORD = re.compile(r"[^a-z0-9]+")


def norm(title: str) -> str:
    """The identity of a paper for this purpose: its title, stripped of markup,
    case and punctuation. Deliberately NOT the DOI — 63% of these rows have no
    DOI recorded, so a DOI key would leave most of the duplication in place."""
    return _NONWORD.sub("", _TAG.sub("", str(title or "")).lower())


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--audit", default="")
    args = ap.parse_args()

    if not DB.is_file():
        print(f"database not found: {DB}", file=sys.stderr)
        return 2

    audit = Path(args.audit) if args.audit else (
        ROOT / "system" / "config" / "local"
        / f"dedupe-literature-{datetime.date.today().isoformat()}.tsv")

    with contextlib.closing(sqlite3.connect(str(DB), timeout=30)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM literature_metadata ORDER BY id").fetchall()
        groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for r in rows:
            k = norm(r["title"])
            if k:
                groups[k].append(r)

        dupes = {k: v for k, v in groups.items() if len(v) > 1}

        def score(r: sqlite3.Row) -> tuple:
            """Most complete first, then the earliest imported."""
            return (
                0 if _blank(r["doi"]) else 1,
                0 if _blank(r["year"]) else 1,
                0 if _blank(r["abstract"]) else 1,
                0 if _blank(r["zotero_key"]) else 1,
                sum(0 if _blank(r[f]) else 1 for f in INHERIT),
                -int(r["id"]),          # tie-break: keep the oldest row
            )

        plan = []           # (survivor, [doomed...], inherited{}, read_at)
        for k, group in dupes.items():
            survivor = max(group, key=score)
            doomed = [r for r in group if r["id"] != survivor["id"]]
            inherited = {}
            for f in INHERIT:
                if _blank(survivor[f]):
                    for d in doomed:
                        if not _blank(d[f]):
                            inherited[f] = d[f]
                            break
            reads = [r["read_at"] for r in group if not _blank(r["read_at"])]
            any_read = any(int(r["is_read"] or 0) for r in group)
            read_at = min(reads) if reads else None
            plan.append((survivor, doomed, inherited, read_at, any_read))

        n_del = sum(len(d) for _, d, _, _, _ in plan)
        n_inh = sum(len(i) for _, _, i, _, _ in plan)
        n_read = sum(1 for s, _, _, ra, ar in plan
                     if (ar or ra) and not int(s["is_read"] or 0))

        print(f"rows now                     {len(rows):>6}")
        print(f"distinct titles              {len(groups):>6}")
        print(f"titles with more than one    {len(dupes):>6}")
        print(f"rows to delete               {n_del:>6}   ({100*n_del//max(len(rows),1)}%)")
        print(f"rows remaining after         {len(rows)-n_del:>6}")
        print(f"fields recovered onto survivors {n_inh:>3}")
        print(f"survivors gaining read state {n_read:>6}")
        print()
        worst = sorted(plan, key=lambda p: -len(p[1]))[:5]
        print("largest groups:")
        for s, d, _, _, _ in worst:
            print(f"  x{len(d)+1:<3} keep id={s['id']:<6} {_TAG.sub('', str(s['title']))[:64]}")

        if not args.apply:
            print("\nDry run. Nothing written — re-run with --apply.")
            return 0

        # ── audit first, so the record exists even if the write fails ────────
        audit.parent.mkdir(parents=True, exist_ok=True)
        with audit.open("w", encoding="utf-8") as fh:
            fh.write("deleted_id\tkept_id\tyear\tdoi\ttitle\n")
            for s, doomed, _, _, _ in plan:
                for d in doomed:
                    t = _TAG.sub("", str(d["title"] or "")).replace("\t", " ")
                    fh.write(f"{d['id']}\t{s['id']}\t{d['year'] or ''}\t"
                             f"{d['doi'] or ''}\t{t}\n")
        print(f"\naudit written: {audit}  ({n_del} rows listed)")

        # ── one transaction ────────────────────────────────────────────────
        try:
            conn.execute("BEGIN")
            for s, doomed, inherited, read_at, any_read in plan:
                sets, params = [], []
                for f, v in inherited.items():
                    sets.append(f"{f} = ?")
                    params.append(v)
                if (any_read or read_at) and not int(s["is_read"] or 0):
                    sets.append("is_read = 1")
                    if read_at:
                        sets.append("read_at = ?")
                        params.append(read_at)
                if sets:
                    params.append(s["id"])
                    conn.execute(
                        f"UPDATE literature_metadata SET {', '.join(sets)} WHERE id = ?",
                        params)
                conn.executemany("DELETE FROM literature_metadata WHERE id = ?",
                                 [(d["id"],) for d in doomed])
            conn.execute("COMMIT")
        except Exception as exc:
            conn.execute("ROLLBACK")
            print(f"\nFAILED, rolled back: {exc}", file=sys.stderr)
            return 1

        left = conn.execute("SELECT COUNT(*) FROM literature_metadata").fetchone()[0]
        distinct = len({norm(r[0]) for r in
                        conn.execute("SELECT title FROM literature_metadata")})
        print(f"done. rows now {left}, distinct titles {distinct}")
        if left != len(rows) - n_del:
            print("  ! unexpected row count — check the audit file", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
