#!/usr/bin/env python3
"""Merge corpus records that hold byte-identical text under different names.

WHY MERGE AND NOT DELETE
    69 groups were found on 2026-08-31 where the TEXT hashes identically and
    only the naming convention differs — a descriptive title beside a journal
    id, a WHO document code, an author tag, or a bare filename. 3,671 chunks,
    about 8% of the index, so roughly one retrieval slot in twelve was being
    spent handing back a passage already returned.

    Deleting the extra copies would fix retrieval and lose something. In six
    groups the right name is genuinely unclear, and in one of them a THESIS and
    a PAPER BY DIFFERENT AUTHORS share a fingerprint — meaning one file is
    mislabelled, and deleting the "copy" would destroy the correct name for a
    document still held.

    So the text is kept once under the most informative title, and every other
    name is recorded in pdf_title_aliases. Retrieval is fixed, no name is lost,
    and the ambiguous cases stay answerable.

CHOOSING THE CANONICAL NAME
    The one carrying the most REAL WORDS. A journal id, a WHO code and a bare
    filename all score zero on that measure, which is exactly right: they
    identify the file, they do not describe the work. Ties go to the longer.

SAFETY
    · --check is the default and writes nothing.
    · --apply copies the database first.
    · Only groups whose full text hashes IDENTICALLY are touched. Similar is
      not the same, and near-duplicate detection is not attempted here.
    · Vectors are deleted before rows. Deleting the row alone would leave an
      embedding that search still returns and then cannot resolve — a partial
      merge indistinguishable from a clean one.
    · The orphan count is verified afterwards and reported.

USAGE
    python3 tools/merge_corpus_aliases.py
    python3 tools/merge_corpus_aliases.py --apply
    python3 tools/merge_corpus_aliases.py --undo        # list what was merged
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DB = Path.home() / ".local/share/metis/metis.sqlite"

# Groups where the two names are not obviously the same work. Recorded on the
# alias row so the question stays visible instead of being quietly settled.
REVIEW_MARKERS = ("phdthesis alainmpanya", "kayembe passivescreening",
                  "masterthesis danel", "fexinidazole", "carina praisler",
                  "christine clayton")

STOP = set("the a an of and or in on for to with by from at is are as its this that "
           "et al eng fr full final version draft copy pdf".split())
IDLIKE = re.compile(r"^(journal|s\d|10\.\d|nbk\d|pone|pntd|pcbi|who|htm|ntd|idm|\d)", re.I)


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.enable_load_extension(True)
    try:
        import sqlite_vec
        sqlite_vec.load(con)
    except Exception as exc:                                    # pragma: no cover
        print(f"sqlite-vec unavailable ({exc}). Refusing to run: without it the "
              f"embeddings cannot be removed and the merge would be silently "
              f"partial.", file=sys.stderr)
        raise SystemExit(2)
    con.enable_load_extension(False)
    return con


def informativeness(title: str) -> tuple[int, int]:
    """How much the name tells you. Real words first, length as the tiebreak."""
    words = [w for w in re.sub(r"[^a-z0-9]+", " ", title.lower()).split()
             if w not in STOP and len(w) > 2 and not IDLIKE.match(w)]
    return (len(words), len(title))


def fingerprint(con: sqlite3.Connection, title: str) -> tuple[str, int]:
    rows = con.execute(
        "SELECT chunk_text FROM pdf_chunks WHERE title=? ORDER BY chunk_idx",
        (title,)).fetchall()
    blob = "".join(r[0] or "" for r in rows).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), len(rows)


def ensure_table(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS pdf_title_aliases (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_title TEXT NOT NULL,
            alias_title     TEXT NOT NULL,
            alias_file      TEXT DEFAULT '',
            chunks_removed  INTEGER DEFAULT 0,
            needs_review    INTEGER DEFAULT 0,
            merged_at       TEXT NOT NULL,
            UNIQUE(alias_title)
        )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_alias_canonical "
                "ON pdf_title_aliases(canonical_title)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", action="store_true", help="list what was merged")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"no database at {db_path}", file=sys.stderr)
        return 2
    con = connect(db_path)
    ensure_table(con)

    if args.undo:
        rows = con.execute(
            "SELECT canonical_title, alias_title, chunks_removed, needs_review, merged_at "
            "FROM pdf_title_aliases ORDER BY merged_at DESC, chunks_removed DESC").fetchall()
        if not rows:
            print("nothing has been merged")
            return 0
        print(f"{len(rows)} aliases recorded\n")
        for canon, alias, n, review, when in rows:
            flag = " ⚠ review" if review else ""
            print(f"  {n:5d}  {alias[:52]:54s} → {canon[:44]}{flag}")
        print("\nThe text was kept under the canonical name. To restore a copy, "
              "re-index the original file — its name is in alias_file.")
        return 0

    titles = [r[0] for r in con.execute(
        "SELECT DISTINCT title FROM pdf_chunks WHERE title != ''")]
    groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for t in titles:
        groups[fingerprint(con, t)].append(t)

    plan = []
    for (digest, n_chunks), names in groups.items():
        if len(names) < 2:
            continue
        names = sorted(names, key=informativeness, reverse=True)
        keep, drop = names[0], names[1:]
        review = any(m in t.lower() for t in names for m in REVIEW_MARKERS)
        plan.append((n_chunks, keep, drop, review))
    plan.sort(key=lambda x: -x[0])

    freed = sum(n * len(d) for n, _, d, _ in plan)
    print(f"{len(plan)} groups · {sum(len(d) for _, _, d, _ in plan)} aliases · "
          f"{freed} chunks freed")
    for n, keep, drop, review in plan[:12]:
        print(f"  {n:5d}  keep {keep[:50]}{'   ⚠' if review else ''}")
        for d in drop:
            print(f"         alias {d[:50]}")

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply.")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup = db_path.with_suffix(db_path.suffix + f".bak-{stamp}")
    shutil.copy2(db_path, backup)
    print(f"\nbacked up to {backup.name}")

    now = datetime.datetime.now().isoformat(timespec="seconds")
    removed = 0
    for n_chunks, keep, drop, review in plan:
        for alias in drop:
            row = con.execute(
                "SELECT source_file FROM pdf_chunks WHERE title=? LIMIT 1", (alias,)).fetchone()
            alias_file = Path(row[0]).name if row and row[0] else ""
            ids = [r[0] for r in con.execute(
                "SELECT id FROM pdf_chunks WHERE title=?", (alias,))]
            # Vectors first: if this fails nothing has been orphaned yet.
            con.executemany("DELETE FROM vec_pdf_chunks WHERE rowid = ?", [(i,) for i in ids])
            con.executemany("DELETE FROM pdf_chunks   WHERE id    = ?", [(i,) for i in ids])
            con.execute("DELETE FROM pdf_index_state WHERE title = ?", (alias,))
            con.execute(
                "INSERT OR REPLACE INTO pdf_title_aliases "
                "(canonical_title, alias_title, alias_file, chunks_removed, needs_review, merged_at) "
                "VALUES (?,?,?,?,?,?)",
                (keep, alias, alias_file, len(ids), 1 if review else 0, now))
            removed += len(ids)
    con.commit()

    # ── Phase 2: the same text twice under ONE title ──────────────────────
    # Grouping by title is structurally blind to this. A document indexed twice
    # from two different source files carries ONE title, so it never looks like
    # a duplicate group — it just has twice as many chunks. Found because a
    # search returned the same page of the same thesis twice AFTER the merge:
    # 130 chunks where 65 were unique.
    #
    # No alias is recorded here and none is needed: the title and the text are
    # both identical, so there is no name to preserve and no judgement to make.
    # The lowest id survives.
    dupe_rows = con.execute("""
        SELECT title, chunk_text, MIN(id) AS keep_id, COUNT(*) AS n
        FROM pdf_chunks GROUP BY title, chunk_text HAVING n > 1""").fetchall()
    chunk_dupes = 0
    for title, text, keep_id, _n in dupe_rows:
        ids = [r[0] for r in con.execute(
            "SELECT id FROM pdf_chunks WHERE title=? AND chunk_text=? AND id != ?",
            (title, text, keep_id))]
        if not ids:
            continue
        con.executemany("DELETE FROM vec_pdf_chunks WHERE rowid = ?", [(i,) for i in ids])
        con.executemany("DELETE FROM pdf_chunks   WHERE id    = ?", [(i,) for i in ids])
        chunk_dupes += len(ids)
    con.commit()
    print(f"{chunk_dupes} chunks were the same text twice under one title")

    left = con.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
    docs = con.execute("SELECT COUNT(DISTINCT title) FROM pdf_chunks").fetchone()[0]
    orphans = con.execute(
        "SELECT COUNT(*) FROM vec_pdf_chunks v WHERE NOT EXISTS "
        "(SELECT 1 FROM pdf_chunks p WHERE p.id = v.rowid)").fetchone()[0]
    aliases = con.execute("SELECT COUNT(*) FROM pdf_title_aliases").fetchone()[0]
    flagged = con.execute(
        "SELECT COUNT(*) FROM pdf_title_aliases WHERE needs_review=1").fetchone()[0]
    print(f"{removed} chunks merged away · {left} remain across {docs} documents")
    print(f"{aliases} names preserved as aliases ({flagged} flagged for review)")
    print(f"{orphans} orphaned vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
