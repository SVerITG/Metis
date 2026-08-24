#!/usr/bin/env python3
"""bulk_add_to_library.py — move reviewed candidates from the queue into the library.

WHY A BULK PATH EXISTS AT ALL
    The New Literature surface adds one paper at a time on purpose: entering the
    catalogue is a decision, and a tool that adds things you did not choose is a
    tool that fills your library with noise.

    But 375 harvested HAT papers is not a review queue, it is a wall. Approving
    them one at a time is not a decision process, it is data entry — and the
    predictable outcome is that none of them get reviewed at all. the researcher chose to
    bulk-add the strong matches and prune afterwards, which inverts the cost:
    subtracting a wrong paper takes one click, whereas approving 375 right ones
    takes 375.

    So this exists, and it is deliberately NARROW: it only takes rows that are
    already tagged into a known-good bucket, and it never guesses.

WHAT IT DOES PER PAPER
    1. Attempt the PDF — open access only by default (`--pdf`), because 375
       sequential publisher requests is inconsiderate and most will fail anyway.
    2. Write a catalogue row in `literature_metadata` (dedup on DOI, then title).
    3. Push to Zotero with the PDF attached when we got one.
    4. Mark the queue row added, recording the acquisition outcome so the red dot
       still tells the truth.

    Every step is independently guarded: a Zotero outage must not stop
    cataloguing, and a failed download must not stop either.

USAGE
    python3 tools/bulk_add_to_library.py --topics 'hat-%' --dry-run
    python3 tools/bulk_add_to_library.py --topics 'hat-%' --pdf oa --limit 400
    python3 tools/bulk_add_to_library.py --topics 'hat-%' --pdf none
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "system" / "app-py"))
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))
os.environ.setdefault("METIS_RC_ROOT", str(ROOT))

# ───────────────────────────────────────────────────────────────────────────────
# CONTENT FILTER — why topic_tag is not enough.
#
# `topic_tag` records WHICH QUERY produced a row, not whether the row is about
# that topic. The harvest used OpenAlex's `search`, which is semantically loose:
# the query "human African trypanosomiasis diagnosis" returned, among real
# papers, a stroke-conference abstract, an ambulance-workforce study and a
# consumer-health piece — all filed under `hat-diagnostics`.
#
# Measured on this queue: 375 rows tagged hat-*, of which 139 (37%) never mention
# a trypanosome at all. Bulk-adding on the tag would have put that straight into
# the catalogue, where it is far more expensive to remove than it was to admit.
#
# So membership is decided by CONTENT — title, abstract and journal — and the tag
# is only used to narrow the candidate pool.
# ───────────────────────────────────────────────────────────────────────────────
HAT_TERMS = (
    "trypanosom", "sleeping sickness", "tsetse", "glossina", "gambiense",
    "rhodesiense", "brucei", "nagana",
    # Animal African trypanosomiasis: the same parasite genus and directly
    # relevant to the reservoir question. "Surra" alone names T. evansi disease
    # and would otherwise be missed.
    "surra", "evansi", "congolense",
)


def matches_terms(row, terms) -> bool:
    hay = " ".join(str(row[k] or "") for k in ("title", "abstract", "journal")).lower()
    return any(term in hay for term in terms)


_ZOTERO_TYPE = {
    "article": "journalArticle", "review": "journalArticle",
    "preprint": "preprint", "book": "book",
    "chapter": "bookSection", "report": "report",
}


def db() -> sqlite3.Connection:
    """Connection tuned for running ALONGSIDE the live dashboard.

    The first full run died at 60/257 with `database is locked`. The database is
    already in WAL mode, which lets readers and one writer coexist — but WAL does
    not make a second writer wait indefinitely, and Python's default busy timeout
    is 5 seconds. The dashboard writes on nearly every request, so a long
    cataloguing loop loses that race eventually.

    Two changes: a 60-second busy timeout so a brief overlap is waited out rather
    than fatal, and committing every row instead of every twenty, so each write
    transaction is short enough to interleave. Slower per row, and it finishes.
    """
    c = sqlite3.connect(
        str(Path.home() / ".local/share/metis" / "metis.sqlite"), timeout=60.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout = 60000")
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", default="hat-%",
                    help="SQL LIKE pattern for topic_tag")
    ap.add_argument("--pdf", choices=["oa", "all", "none"], default="oa",
                    help="oa = open access only (default); all = also try the "
                         "institutional route; none = metadata only")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--require-doi", action="store_true", default=True)
    ap.add_argument("--no-zotero", action="store_true")
    ap.add_argument("--must-match", default="hat",
                    choices=["hat", "none"],
                    help="content filter: 'hat' requires a trypanosome term in "
                         "title/abstract/journal (default); 'none' trusts the tag")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = db()
    rows = conn.execute(
        "SELECT * FROM new_publications "
        "WHERE topic_tag LIKE ? AND COALESCE(added_at,'')='' "
        "  AND COALESCE(dismissed_at,'')='' "
        + ("AND doi != '' " if args.require_doi else "")
        + "ORDER BY relevance DESC, pub_iso DESC LIMIT ?",
        (args.topics, args.limit)).fetchall()

    if args.must_match == "hat":
        before = len(rows)
        rows = [r for r in rows if matches_terms(r, HAT_TERMS)]
        print(f"content filter: {before} tagged → {len(rows)} genuinely mention a "
              f"trypanosome ({before - len(rows)} excluded as query noise)")

    print(f"candidates: {len(rows)}  (topic_tag LIKE {args.topics!r})")
    print(f"pdf mode  : {args.pdf}   zotero: {'off' if args.no_zotero else 'on'}")
    if args.dry_run:
        for r in rows[:20]:
            print(f"   {(r['topic_tag'] or '')[:22]:<22} {(r['title'] or '')[:64]}")
        print(f"\n   … and {max(0, len(rows) - 20)} more")
        print("\n  DRY RUN — nothing written.")
        return 0

    from services.acquire import acquire_pdf

    push = None
    if not args.no_zotero:
        try:
            from routers.new_literature import _push_one_to_zotero as push
        except Exception as exc:
            print(f"  ! Zotero push unavailable ({exc}); cataloguing only")

    catalogued = with_pdf = pushed = failed = 0
    now_iso = datetime.now().isoformat(timespec="seconds")

    for i, row in enumerate(rows, 1):
        pub = dict(row)
        title = (pub.get("title") or "").strip()
        doi = (pub.get("doi") or "").strip()
        if not title:
            continue

        # ── 1. PDF ───────────────────────────────────────────────────────────
        acq = {"status": "", "reason": "not attempted", "path": "", "method": ""}
        if args.pdf != "none":
            try:
                # `oa` mode: temporarily hide the proxy so only open-access rungs
                # are tried. 375 sequential publisher hits is not neighbourly, and
                # without a session they would fail anyway.
                saved = os.environ.pop("LIBRARY_PROXY_TEMPLATE", None) \
                    if args.pdf == "oa" else None
                try:
                    acq = acquire_pdf(conn, pub)
                finally:
                    if saved is not None:
                        os.environ["LIBRARY_PROXY_TEMPLATE"] = saved
            except Exception as exc:
                acq = {"status": "failed", "reason": f"{type(exc).__name__}",
                       "path": "", "method": ""}
            if acq["status"] == "ok":
                with_pdf += 1

        # ── 2. Catalogue ─────────────────────────────────────────────────────
        existing = conn.execute(
            "SELECT id FROM literature_metadata WHERE "
            "(doi != '' AND lower(doi)=lower(?)) OR lower(title)=lower(?) LIMIT 1",
            (doi or "\x00", title)).fetchone()
        if existing:
            lit_id = existing["id"]
        else:
            conn.execute(
                "INSERT INTO literature_metadata (title, authors, year, source, "
                "journal, tags, doi, abstract, url, item_type, library_source, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (title[:500], (pub.get("authors") or "")[:300],
                 (pub.get("pub_iso") or "")[:4] or None,
                 pub.get("journal", ""), pub.get("journal", ""),
                 pub.get("topic_tag", ""), doi,
                 (pub.get("abstract") or "")[:4000], pub.get("source_url", ""),
                 _ZOTERO_TYPE.get(pub.get("entry_kind") or "article", "journalArticle"),
                 "bulk-add", now_iso))
            lit_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            catalogued += 1

        # ── 3. Zotero ────────────────────────────────────────────────────────
        zkey = (pub.get("zotero_key") or "").strip()
        if push and not zkey:
            try:
                zkey, zerr = push(pub, acq.get("path", ""))
                if zkey:
                    pushed += 1
                elif zerr and pushed == 0 and i <= 3:
                    # Report the FIRST few failures loudly. A silent Zotero
                    # outage across 375 papers is exactly the sort of thing that
                    # is discovered a week later.
                    print(f"   ! Zotero: {zerr[:90]}")
            except Exception as exc:
                zerr = str(exc)[:90]

        # ── 4. Close the queue row ───────────────────────────────────────────
        conn.execute(
            "UPDATE new_publications SET added_at=?, acq_status=?, acq_reason=?, "
            "pdf_path=?, zotero_key=COALESCE(NULLIF(?,''), zotero_key) WHERE id=?",
            (now_iso, acq["status"] or "", acq["reason"][:400],
             acq["path"], zkey, pub["id"]))

        if acq["status"] == "failed":
            failed += 1
        # Commit EVERY row: short transactions interleave with the dashboard's
        # writes; a 20-row batch does not, and that is what deadlocked.
        conn.commit()
        if i % 20 == 0:
            print(f"   {i}/{len(rows)} · catalogued {catalogued} · "
                  f"pdf {with_pdf} · zotero {pushed}")
        time.sleep(0.05)

    conn.commit()
    print(f"\n{'=' * 66}")
    print(f"  processed   : {len(rows)}")
    print(f"  catalogued  : {catalogued}")
    print(f"  with a PDF  : {with_pdf}")
    print(f"  no PDF      : {failed}  (red dot + resolver link in the surface)")
    print(f"  pushed to Zotero: {pushed}")
    print(f"{'=' * 66}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
