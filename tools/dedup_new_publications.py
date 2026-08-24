#!/usr/bin/env python3
"""dedup_new_publications.py — collapse the same paper arriving by several routes.

WHY THIS EXISTS
    A paper reaches `new_publications` by up to four independent routes: a journal
    ToC feed, a preprint server, a PubMed topic query, and an OpenAlex topic query.
    Dedup was keyed on `source_url` and `doi` — and PubMed's esummary frequently
    omits the DOI (a limitation noted in the scheduler's own code). So the same
    paper lands three times under three URLs with no shared key:

        2026-07-17  Glycerol metabolism triggers trypanosome differentiation…
        2026 Jul 1  Glycerol metabolism triggers trypanosome differentiation…
        2025-05-26  Glycerol metabolism triggers trypanosome differentiation…

    Observed immediately after the first retrospective HAT sweep. Triplicates are
    not a cosmetic problem on a review surface: a reviewer who has to decide
    "have I already seen this?" three times per paper stops trusting the list, and
    a list you do not trust is one you stop opening.

THE KEY
    A normalised title: lowercased, HTML/entities stripped, punctuation and
    whitespace collapsed, a leading article-type prefix ("[Comment]") removed.
    Titles are the only field ALL four routes reliably populate.

    Deliberately NOT fuzzy. An edit-distance match would eventually merge two
    genuinely different papers from the same group with near-identical titles,
    and a wrongly merged paper is invisible — the worst outcome. Exact match on a
    normalised key errs toward keeping both, which is recoverable.

WHICH ROW SURVIVES
    The most informative one: DOI first, then abstract, then authors, then
    earliest discovery. A survivor inherits any field the losers had and it
    lacked, so collapsing never loses metadata — only rows.

USAGE
    python3 tools/dedup_new_publications.py --dry-run
    python3 tools/dedup_new_publications.py
"""
from __future__ import annotations

import html
import os
import re
import sqlite3
import sys
from pathlib import Path

_TAG_RE      = re.compile(r"<[^>]+>")
_PREFIX_RE   = re.compile(r"^\s*\[[^\]]{1,40}\]\s*")     # "[Comment] ", "[Correspondence] "
_NONWORD_RE  = re.compile(r"[^a-z0-9]+")


def title_key(title: str) -> str:
    """Normalise a title into a dedup key. Empty string if unusable."""
    t = html.unescape(title or "")
    t = _TAG_RE.sub(" ", t)          # journals ship <i>Trypanosoma</i> in titles
    t = _PREFIX_RE.sub("", t)
    t = _NONWORD_RE.sub(" ", t.lower()).strip()
    # Very short titles are not distinctive enough to merge on safely.
    return t if len(t) >= 18 else ""


def db_path() -> Path:
    env = os.environ.get("METIS_DB_PATH", "")
    if env and Path(env).exists():
        return Path(env)
    return Path.home() / ".local/share/metis" / "metis.sqlite"


def score(row: sqlite3.Row) -> tuple:
    """Higher is better — decides which duplicate survives."""
    return (
        1 if (row["doi"] or "") else 0,
        len(row["abstract"] or ""),
        len(row["authors"] or ""),
        1 if (row["pub_date"] or "") else 0,
        -(row["id"] or 0),          # tie-break: the earliest row discovered
    )


def main() -> int:
    dry = "--dry-run" in sys.argv
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row

    # Add the key column so future inserts can check it cheaply. Additive only.
    #
    # The column may already exist without any keys in it — that is the normal
    # case now that `system/installer/schema.sql` declares it and the dashboard
    # adds it on startup. The backfill below therefore keys off whether a ROW
    # lacks its key, never off whether the COLUMN was just created: those are
    # different facts, and conflating them meant that on a database where the
    # column pre-existed, every key stayed empty and the index was never built
    # (found 2026-08-24 — `download_pickup`'s `WHERE title_key = ?` matched
    # nothing at all, silently, on 1302 rows).
    cols = {r[1] for r in con.execute("PRAGMA table_info(new_publications)")}
    if "title_key" not in cols:
        print("  + adding column title_key")
        if not dry:
            con.execute("ALTER TABLE new_publications ADD COLUMN title_key TEXT DEFAULT ''")
            cols.add("title_key")
    if not dry and "title_key" in cols:
        # Unconditional and idempotent — an existing index is left alone.
        con.execute("CREATE INDEX IF NOT EXISTS idx_newpub_titlekey "
                    "ON new_publications(title_key)")

    rows = con.execute(
        "SELECT id, title, doi, abstract, authors, pub_date, source_url, "
        "       read_at, added_at, journal, topic_tag, "
        "       COALESCE(title_key, '') AS title_key "
        "FROM new_publications ORDER BY id"
    ).fetchall()
    print(f"  scanning {len(rows)} rows")

    groups: dict[str, list[sqlite3.Row]] = {}
    backfilled = 0
    for r in rows:
        k = title_key(r["title"])
        if k:
            groups.setdefault(k, []).append(r)
        # Write the key whenever the stored one is missing or has drifted from
        # what the current normaliser produces. Cheap, and it means a change to
        # title_key() propagates on the next run instead of leaving a mix of two
        # key generations in one column — which would silently stop matching.
        if not dry and r["title_key"] != k:
            con.execute("UPDATE new_publications SET title_key=? WHERE id=?", (k, r["id"]))
            backfilled += 1

    if backfilled:
        print(f"  backfilled title_key on {backfilled} row(s)")

    dupe_groups = {k: v for k, v in groups.items() if len(v) > 1}
    removable = sum(len(v) - 1 for v in dupe_groups.values())
    print(f"  {len(dupe_groups)} duplicated title(s), {removable} row(s) removable")

    shown = 0
    for k, members in sorted(dupe_groups.items(), key=lambda kv: -len(kv[1])):
        keep = max(members, key=score)
        losers = [m for m in members if m["id"] != keep["id"]]
        if shown < 12:
            print(f"    ×{len(members)}  {keep['title'][:66]}")
            shown += 1
        if dry:
            continue

        # Merge missing metadata upward before dropping the losers, so a row that
        # only PubMed had a date for, or only OpenAlex had an abstract for, keeps
        # both. Dedup must never cost information.
        patch: dict[str, str] = {}
        for field in ("doi", "abstract", "authors", "pub_date", "journal"):
            if not (keep[field] or ""):
                for m in losers:
                    if m[field]:
                        patch[field] = m[field]
                        break
        # If any copy was already handled, the survivor inherits that too —
        # otherwise a paper you dismissed reappears as brand new.
        for field in ("read_at", "added_at"):
            if not (keep[field] or ""):
                for m in losers:
                    if m[field]:
                        patch[field] = m[field]
                        break
        if patch:
            sets = ", ".join(f"{f}=?" for f in patch)
            con.execute(f"UPDATE new_publications SET {sets} WHERE id=?",
                        (*patch.values(), keep["id"]))
        con.executemany("DELETE FROM new_publications WHERE id=?",
                        [(m["id"],) for m in losers])

    if not dry:
        con.commit()
    total = con.execute("SELECT COUNT(*) FROM new_publications").fetchone()[0]
    con.close()
    print(f"\n  {'DRY RUN — nothing written' if dry else '✓ deduplicated'} · "
          f"{total} row(s) remain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
