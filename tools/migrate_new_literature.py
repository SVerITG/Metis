#!/usr/bin/env python3
"""migrate_new_literature.py — give `new_publications` the columns the New
Literature surface needs, additively and idempotently.

WHY THIS EXISTS
    `new_publications` was designed as a small alert list for the Today surface:
    title, journal, date, doi, one topic tag, a URL. That is enough for a nudge
    and nowhere near enough for a literature-review surface.

    Three things were missing and each broke a specific promise:

    1. NO ABSTRACT. `_scan_feeds()` reads `entry.summary` from every feed — which
       for a journal ToC feed IS the abstract — and then throws it away on the
       paper branch while keeping it on the news branch. So "I can read an
       abstract" was impossible for exactly the items that had one.

    2. NO ARTICLE/BOOK DISTINCTION. Everything was a row. Books, reports and
       preprints cannot be listed separately from journal articles if nothing
       records which is which.

    3. NO ACQUISITION STATE. "Add to library" wrote a metadata row and marked the
       paper read. Whether a PDF was actually obtained was not recorded anywhere,
       so a failure was indistinguishable from a success — the red dot had nothing
       to read.

    Also added: `lane` (field vs general science), so the General Science tab is a
    stored decision rather than a query someone has to re-derive per request, and
    `relevance`, which the scan already COMPUTES against the corpus centroid and
    then discards on the paper branch.

SAFETY
    Only ever ADDs columns and tables. Never drops, never rewrites a value that is
    already set. Safe to run repeatedly, and safe to run mid-update — which is the
    point: `tools/metis_update.py` verifies by row count, so a migration that
    could lose a row would trigger a rollback.

USAGE
    python3 tools/migrate_new_literature.py            # apply
    python3 tools/migrate_new_literature.py --dry-run  # report only
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Columns added to new_publications. Every one has a DEFAULT, so existing rows
# stay valid without a backfill pass and no reader can hit a NULL it did not
# expect.
# ---------------------------------------------------------------------------
NEW_PUB_COLUMNS: dict[str, str] = {
    # Bibliographic — what a catalogue entry needs to be readable on its own.
    "authors":      "TEXT DEFAULT ''",
    "abstract":     "TEXT DEFAULT ''",
    "feed_name":    "TEXT DEFAULT ''",

    # Classification. `entry_kind` separates articles from books/reports/
    # preprints; `lane` separates "close to my work" from "general science".
    # Both are stored rather than derived per request so the tabs are stable and
    # a misclassification can be corrected in one place.
    "entry_kind":   "TEXT DEFAULT 'article'",
    "lane":         "TEXT DEFAULT 'field'",

    # Corpus closeness, already computed by the scan's interest centroid and
    # previously discarded for papers. Drives ordering inside every tab.
    "relevance":    "REAL DEFAULT 0",

    # Acquisition state — the red dot reads these three and nothing else.
    #   acq_status: '' (never attempted) | 'ok' | 'failed' | 'pending'
    #   acq_reason: human-readable why, shown on hover. Never a stack trace.
    #   pdf_path:   path relative to the configured library root, '' if none.
    "acq_status":   "TEXT DEFAULT ''",
    "acq_reason":   "TEXT DEFAULT ''",
    "pdf_path":     "TEXT DEFAULT ''",

    # Lifecycle. `read_at` already existed but conflated three different things:
    # seen, added, and dismissed. Splitting them is what makes the catch-up
    # window honest — an item you added is not an item you skipped.
    "added_at":     "TEXT DEFAULT ''",
    "dismissed_at": "TEXT DEFAULT ''",
    "zotero_key":   "TEXT DEFAULT ''",
}

# ---------------------------------------------------------------------------
# Review state. "Since I last caught up" needs a stored marker; without one the
# only available windows are fixed spans (today, 7 days), which is precisely the
# complaint — coming back after ten days away and being shown "this week".
#
# One row per surface so News and Library can be caught up independently.
# ---------------------------------------------------------------------------
REVIEW_STATE_DDL = """
CREATE TABLE IF NOT EXISTS library_review_state (
    surface          TEXT PRIMARY KEY,
    last_reviewed_at TEXT NOT NULL,
    items_seen       INTEGER DEFAULT 0,
    updated_at       TEXT NOT NULL
)
"""

# Acquisition attempt log. Kept separate from the item row so a retry does not
# overwrite the record of why the previous attempt failed — the difference
# between "paywalled" and "the proxy was not configured yet" matters, and one
# column cannot hold both.
ACQ_LOG_DDL = """
CREATE TABLE IF NOT EXISTS library_acquisition_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pub_id      INTEGER,
    doi         TEXT DEFAULT '',
    method      TEXT DEFAULT '',
    outcome     TEXT DEFAULT '',
    detail      TEXT DEFAULT '',
    bytes       INTEGER DEFAULT 0,
    attempted_at TEXT NOT NULL
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_newpub_discovered ON new_publications(discovered_at)",
    "CREATE INDEX IF NOT EXISTS idx_newpub_lane       ON new_publications(lane)",
    "CREATE INDEX IF NOT EXISTS idx_newpub_kind       ON new_publications(entry_kind)",
    "CREATE INDEX IF NOT EXISTS idx_newpub_doi        ON new_publications(doi)",
    "CREATE INDEX IF NOT EXISTS idx_acqlog_pub        ON library_acquisition_log(pub_id)",
]


def db_path() -> Path:
    env = os.environ.get("METIS_DB_PATH", "")
    if env and Path(env).exists():
        return Path(env)
    return Path.home() / ".local/share/metis" / "metis.sqlite"


def main() -> int:
    dry = "--dry-run" in sys.argv
    path = db_path()
    if not path.exists():
        print(f"✗ database not found at {path}")
        return 1

    con = sqlite3.connect(str(path))
    try:
        existing = {r[1] for r in con.execute("PRAGMA table_info(new_publications)")}
        if not existing:
            print("✗ new_publications does not exist — run a literature scan first")
            return 1

        to_add = {c: t for c, t in NEW_PUB_COLUMNS.items() if c not in existing}
        print(f"new_publications: {len(existing)} existing columns, "
              f"{len(to_add)} to add")
        for col, decl in to_add.items():
            print(f"  + {col} {decl}")
            if not dry:
                con.execute(f"ALTER TABLE new_publications ADD COLUMN {col} {decl}")

        for name, ddl in (("library_review_state", REVIEW_STATE_DDL),
                          ("library_acquisition_log", ACQ_LOG_DDL)):
            present = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
            ).fetchone()
            print(f"  {'·' if present else '+'} table {name}"
                  f"{' (exists)' if present else ''}")
            if not dry:
                con.execute(ddl)

        if not dry:
            for stmt in INDEXES:
                con.execute(stmt)
            con.commit()

        rows = con.execute("SELECT COUNT(*) FROM new_publications").fetchone()[0]
        print(f"\n{'DRY RUN — nothing written' if dry else '✓ migration applied'} "
              f"· {rows} publication row(s) intact")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
