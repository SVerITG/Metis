#!/usr/bin/env python3
"""Draw a line under everything currently stored: from tomorrow, only new items.

WHY
    the researcher, 2026-08-31: "see that all news and library items that we currently
    have are set to 'read' or at least that for those i am not asked to tag them
    as read so we can start from today over, tomorrow mentioning the new items."

    The backlog was demanding triage on every row — 2,082 publications each
    offering "add to library / not interested", and thousands of news briefs
    each offering five actions. A queue that large is not a queue, it is a wall,
    and it hides the twenty things that arrived this morning.

    Nothing is deleted. Every baseline is a TIMESTAMP, so the items remain and
    remain searchable; they simply stop presenting themselves as undecided.

FOUR BASELINES, because four different mechanisms answer "what is new" and
they are not interchangeable:

    library_review_state   the Library's catch-up window — what the New tab hides
    ui_seen                per-surface "since you last looked" deltas
    literature_metadata    per-item read flag + read_at date
    new_publications       per-item read_at date

USAGE
    python3 tools/start_fresh.py            # show what would change
    python3 tools/start_fresh.py --apply
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / ".local/share/metis/metis.sqlite"

# Every key the surfaces pass to ui.whats_new(). Named explicitly rather than
# discovered, so a surface that stops being reset shows up as a missing line
# here instead of silently keeping a stale baseline.
SEEN_KEYS = ("news", "library", "work", "stack", "today.literature")
LIBRARY_SURFACE = "new_literature"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    db = Path(args.db)
    con = sqlite3.connect(db)
    c = con.cursor()
    now = datetime.datetime.now().isoformat(timespec="seconds")

    def n(sql, params=()):
        try:
            return int(c.execute(sql, params).fetchone()[0] or 0)
        except sqlite3.OperationalError:
            return -1

    pubs_untriaged = n("SELECT COUNT(*) FROM new_publications WHERE "
                       "COALESCE(added_at,'')='' AND COALESCE(dismissed_at,'')=''")
    pubs_unread = n("SELECT COUNT(*) FROM new_publications WHERE COALESCE(read_at,'')=''")
    lit_unread = n("SELECT COUNT(*) FROM literature_metadata WHERE COALESCE(is_read,0)=0")
    briefs = n("SELECT COUNT(*) FROM news_briefs")
    seen_now = {k: v for k, v in c.execute("SELECT key, seen_at FROM ui_seen")} \
        if n("SELECT COUNT(*) FROM ui_seen") >= 0 else {}

    print(f"library catch-up window   : {pubs_untriaged} publications still asking to be triaged")
    print(f"new_publications.read_at  : {pubs_unread} without a read date")
    print(f"literature_metadata       : {lit_unread} unread")
    print(f"news_briefs               : {briefs} stored")
    print(f"\nui_seen baselines:")
    for k in SEEN_KEYS:
        print(f"  {k:22s} {seen_now.get(k) or '— never marked —'}")

    if not args.apply:
        print(f"\ndry run — nothing written. --apply would set every baseline to {now}.")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    shutil.copy2(db, db.with_suffix(db.suffix + f".bak-{stamp}"))
    print(f"\nbacked up to {db.name}.bak-{stamp}")

    # 1 · the Library's catch-up window
    c.execute("""CREATE TABLE IF NOT EXISTS library_review_state (
                   surface TEXT PRIMARY KEY, last_reviewed_at TEXT,
                   items_seen INTEGER DEFAULT 0, updated_at TEXT)""")
    c.execute("INSERT INTO library_review_state (surface, last_reviewed_at, items_seen, updated_at) "
              "VALUES (?,?,?,?) ON CONFLICT(surface) DO UPDATE SET "
              "last_reviewed_at=excluded.last_reviewed_at, items_seen=excluded.items_seen, "
              "updated_at=excluded.updated_at",
              (LIBRARY_SURFACE, now, pubs_untriaged, now))

    # 2 · per-surface "since you last looked"
    c.execute("CREATE TABLE IF NOT EXISTS ui_seen (key TEXT PRIMARY KEY, seen_at TEXT)")
    for k in SEEN_KEYS:
        c.execute("INSERT INTO ui_seen (key, seen_at) VALUES (?,?) "
                  "ON CONFLICT(key) DO UPDATE SET seen_at=excluded.seen_at", (k, now))

    # 3 · per-item read dates. One shared timestamp, so a bulk reset stays
    #     distinguishable from thousands of individual acts of reading.
    lit = c.execute("UPDATE literature_metadata SET is_read=1, read_at=? "
                    "WHERE COALESCE(is_read,0)=0", (now,)).rowcount
    pub = c.execute("UPDATE new_publications SET read_at=? "
                    "WHERE COALESCE(read_at,'')=''", (now,)).rowcount
    con.commit()

    print(f"  library catch-up set    · {pubs_untriaged} publications no longer asking")
    print(f"  {len(SEEN_KEYS)} surface baselines set")
    print(f"  {lit} literature records marked read")
    print(f"  {pub} publications given a read date")
    print(f"\nAll of it keyed to {now}. From here, 'new' means arrived after that.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
