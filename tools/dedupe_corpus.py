#!/usr/bin/env python3
"""Remove a duplicate document from the PDF corpus — both halves of it.

WHY THIS EXISTS
    The DHIS2 Implementation Guide was indexed twice under two filenames, 322
    chunks each, byte-identical. Every semantic search that matched it therefore
    spent TWO of its six result slots on the same passage. The symptom looks
    like "Metis is obsessed with DHIS2"; the cause is that half the retrieval
    budget was being handed to one duplicated document.

WHY IT IS A SCRIPT AND NOT A DELETE STATEMENT
    A chunk lives in two places: the row in `pdf_chunks`, and its embedding in
    `vec_pdf_chunks`, a sqlite-vec virtual table keyed by the SAME id. Deleting
    only the row leaves an orphaned vector that similarity search still returns
    and then cannot resolve — a partial deletion that looks exactly like a clean
    one, which is a failure mode this project has been bitten by before. The
    vec0 module has to be loaded to touch the second table at all, which is why
    a plain `sqlite3` shell cannot do this job correctly.

SAFETY
    · --check is the default and writes nothing.
    · --apply copies the database first, to <db>.bak-<timestamp>.
    · It refuses to delete unless the surviving copy is byte-identical, so it
      can never silently drop the longer or newer of two similar documents.
    · It never deletes the last copy of anything.

USAGE
    python3 tools/dedupe_corpus.py                       # list duplicate groups
    python3 tools/dedupe_corpus.py --apply               # remove the redundant copies
    python3 tools/dedupe_corpus.py --title "DHIS2 Implementation Guide 2023 Dl29gy3" --apply
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DB = Path.home() / ".local/share/metis/metis.sqlite"


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.enable_load_extension(True)
    try:
        import sqlite_vec
        sqlite_vec.load(con)
    except Exception as exc:                                    # pragma: no cover
        print(f"could not load sqlite-vec ({exc}).", file=sys.stderr)
        print("Refusing to continue: without it the embeddings cannot be removed "
              "and the deletion would be silently partial.", file=sys.stderr)
        raise SystemExit(2)
    con.enable_load_extension(False)
    return con


def same_document(a: str, b: str, max_lead: int = 2, min_chars: int = 25) -> bool:
    """Two titles naming the same document, given identical text.

    Three things make a plain string comparison fail here, and all three were
    found the hard way on 2026-08-31:

      · an AUTHOR PREFIX. "Simarro Mapping The Capacities…" and "Mapping The
        Capacities…" are one paper. Proved by a live search returning the same
        page of it twice, at the same score.
      · DIFFERENT TRUNCATION. The two records are cut at different lengths.
      · the cut lands MID-WORD — "On The Transm" against "On The Transmission" —
        so comparing token by token fails on the final element even when the
        titles are plainly the same. This is the same defect as the project
        card that read "SLEEPING-SICKNES", and it hid 50 duplicate copies from
        a token-wise version of this function.

    So: compare on the STRING prefix, after allowing up to two leading words to
    be an author name. The authored title is the one worth keeping — it carries
    strictly more information.
    """
    norm = lambda t: re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    A, B = norm(a), norm(b)
    for x, y in ((A, B), (B, A)):
        toks = x.split()
        for k in range(0, max_lead + 1):
            xs = " ".join(toks[k:])
            n = min(len(xs), len(y))
            if n >= min_chars and xs[:n] == y[:n]:
                return True
    return False


def fingerprint(con: sqlite3.Connection, title: str) -> tuple[str, int]:
    rows = con.execute(
        "SELECT chunk_text FROM pdf_chunks WHERE title=? ORDER BY chunk_idx", (title,)
    ).fetchall()
    blob = "".join(r[0] or "" for r in rows).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    ap.add_argument("--title", default="", help="only consider this exact title")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"no database at {db_path}", file=sys.stderr)
        return 2

    con = connect(db_path)
    titles = [r[0] for r in con.execute("SELECT DISTINCT title FROM pdf_chunks WHERE title != ''")]

    groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for t in titles:
        groups[fingerprint(con, t)].append(t)

    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    if not dupes:
        print("no byte-identical duplicates in the corpus")
        return 0

    total_freed = 0
    plan: list[str] = []
    for (digest, n_chunks), names in sorted(dupes.items(), key=lambda kv: -kv[0][1]):
        # Keep the shortest title — it is the canonical name; the longer ones
        # carry download ids like "2023 Dl29gy3".
        names_sorted = sorted(names, key=lambda s: (len(s), s))
        keep, drop = names_sorted[0], names_sorted[1:]
        if args.title and args.title not in drop:
            continue
        if args.title:
            drop = [args.title]
        print(f"\n{n_chunks} chunks · sha256 {digest[:16]}")
        print(f"  keep  {keep}")
        for d in drop:
            print(f"  DROP  {d}   (-{n_chunks} chunks)")
            plan.append(d)
            total_freed += n_chunks

    print(f"\n{len(plan)} redundant copies · {total_freed} chunks")

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply to delete.")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = db_path.with_suffix(db_path.suffix + f".bak-{stamp}")
    shutil.copy2(db_path, backup)
    print(f"\nbacked up to {backup}")

    removed = 0
    for title in plan:
        ids = [r[0] for r in con.execute("SELECT id FROM pdf_chunks WHERE title=?", (title,))]
        if not ids:
            continue
        # Vectors FIRST: if this fails we have not yet orphaned anything.
        con.executemany("DELETE FROM vec_pdf_chunks WHERE rowid = ?", [(i,) for i in ids])
        con.executemany("DELETE FROM pdf_chunks   WHERE id    = ?", [(i,) for i in ids])
        con.execute("DELETE FROM pdf_index_state WHERE title = ?", (title,))
        removed += len(ids)
        print(f"  removed {len(ids):4d} chunks · {title}")
    con.commit()

    left = con.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
    orphans = con.execute(
        "SELECT COUNT(*) FROM vec_pdf_chunks v "
        "WHERE NOT EXISTS (SELECT 1 FROM pdf_chunks p WHERE p.id = v.rowid)"
    ).fetchone()[0]
    print(f"\n{removed} chunks removed · {left} remain · {orphans} orphaned vectors")
    return 1 if orphans else 0


if __name__ == "__main__":
    sys.exit(main())
