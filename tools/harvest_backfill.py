#!/usr/bin/env python3
"""harvest_backfill.py — retrospective literature sweep for a topic set.

WHY THIS EXISTS
    Fixing the feeds fixes the FUTURE. It recovers nothing.

    the researcher noticed that new VSG-differentiation evidence had never reached his
    library. The cause was that LIBRARY_FEEDS carried no molecular parasitology
    journal at all, so trypanosome biology had no route in. Adding those feeds
    (2026-08-21) means tomorrow's papers arrive — but the most recent VSG work in
    his library was from 2022, and a forward-only watcher will never close a
    four-year hole.

    So: a bounded, explicit, retrospective sweep. Queries PubMed and OpenAlex over
    a date range and writes hits into `new_publications` for review. It does NOT
    write to `literature_metadata` — nothing enters the catalogue without the researcher
    saying so, which is the whole point of an "add to library" action.

DESIGN NOTES
    · PubMed's esearch takes `reldate` (days back), not a date range, so the
      window is expressed in days and converted.
    · Dedup is on source_url AND doi, because the same paper arrives from both
      APIs under different URLs — PubMed gives a pubmed.ncbi URL, OpenAlex gives
      a doi.org one, and without the DOI check every backfill double-counts.
    · Relevance is set to 0.9 rather than computed. These rows exist because they
      matched an explicit topic query, so corpus-centroid closeness would be
      measuring the wrong thing — it would demote a molecular paper for being
      unlike an epidemiology-heavy corpus, which is precisely the gap being fixed.

USAGE
    python3 tools/harvest_backfill.py --topics hat            # curated HAT set
    python3 tools/harvest_backfill.py --topics profile        # topics from profile
    python3 tools/harvest_backfill.py --topics hat --years 4
    python3 tools/harvest_backfill.py --topics hat --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

# ---------------------------------------------------------------------------
# The curated HAT query set.
#
# NOT just "sleeping sickness". A library that already holds 700 epidemiology
# items does not need more epidemiology — it needs the axes that were structurally
# absent. These queries are chosen to span the disease as a whole:
#
#   parasite biology     — the gap the researcher actually hit (VSG, differentiation)
#   diagnostics          — depends directly on VSG variability
#   vector               — tsetse, the other half of transmission
#   elimination & policy — where his own work sits
#   animal reservoir     — the part that decides whether elimination holds
# ---------------------------------------------------------------------------
HAT_QUERIES: list[tuple[str, str]] = [
    # (query, topic_tag)
    ("Trypanosoma brucei variant surface glycoprotein",       "hat-parasite-biology"),
    ("trypanosome antigenic variation VSG switching",         "hat-parasite-biology"),
    ("Trypanosoma brucei differentiation stumpy slender",     "hat-parasite-biology"),
    ("Trypanosoma brucei gambiense genomics",                 "hat-parasite-biology"),
    ("trypanosome quorum sensing development",                "hat-parasite-biology"),
    ("human African trypanosomiasis diagnosis",               "hat-diagnostics"),
    ("trypanolysis test Trypanosoma brucei gambiense",        "hat-diagnostics"),
    ("sleeping sickness rapid diagnostic test",               "hat-diagnostics"),
    ("human African trypanosomiasis treatment fexinidazole",  "hat-treatment"),
    ("acoziborole sleeping sickness",                         "hat-treatment"),
    ("human African trypanosomiasis elimination",             "hat-elimination"),
    ("sleeping sickness surveillance passive screening",      "hat-surveillance"),
    ("Glossina tsetse distribution modelling",                "hat-vector"),
    ("tsetse control vector Trypanosoma",                     "hat-vector"),
    ("Trypanosoma brucei gambiense animal reservoir",          "hat-reservoir"),
    ("human African trypanosomiasis Democratic Republic Congo", "hat-drc"),
    ("gambiense sleeping sickness asymptomatic carrier",      "hat-epidemiology"),
    ("sleeping sickness spatial epidemiology risk map",       "hat-spatial"),
]


def db_path() -> Path:
    env = os.environ.get("METIS_DB_PATH", "")
    if env and Path(env).exists():
        return Path(env)
    return Path.home() / ".local/share/metis" / "metis.sqlite"


def profile_topics() -> list[tuple[str, str]]:
    """Active topics from the researcher's own profile."""
    con = sqlite3.connect(str(db_path()))
    try:
        rows = con.execute(
            "SELECT topic FROM user_topics WHERE active = 1 ORDER BY topic"
        ).fetchall()
        return [(r[0], r[0][:60]) for r in rows if r[0]]
    finally:
        con.close()


def harvest(queries: list[tuple[str, str]], years: int, per_query: int,
            dry: bool) -> dict:
    from metis_mcp.tools.content_scan import classify_publication
    from metis_mcp.tools.literature_monitor import (
        _openalex_search, _pubmed_esearch, _pubmed_esummary,
        _reconstruct_abstract,
    )

    days = int(years * 365.25)
    from_date = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    now = dt.datetime.now().isoformat(timespec="seconds")

    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row
    stats = {"queried": 0, "seen": 0, "added": 0, "dupes": 0, "errors": []}

    def already(url: str, doi: str) -> bool:
        # Two-key dedup: the same paper arrives as a pubmed.ncbi URL from one API
        # and a doi.org URL from the other. URL alone double-counts everything.
        if con.execute("SELECT 1 FROM new_publications WHERE source_url=? LIMIT 1",
                       (url,)).fetchone():
            return True
        if doi and con.execute(
            "SELECT 1 FROM new_publications WHERE doi=? AND doi!='' LIMIT 1",
            (doi,)
        ).fetchone():
            return True
        # Also skip anything already IN the catalogue — re-offering a paper he
        # filed years ago is noise that makes the whole surface less trustworthy.
        if doi and con.execute(
            "SELECT 1 FROM literature_metadata WHERE lower(doi)=? AND doi!='' LIMIT 1",
            (doi.lower(),)
        ).fetchone():
            return True
        return False

    def insert(title, journal, pub_date, doi, tag, url, authors, abstract, src):
        kind, lane = classify_publication(title, abstract, journal, tag, url, 1.0)
        con.execute(
            "INSERT INTO new_publications (title, journal, pub_date, doi, topic_tag, "
            "source_url, discovered_at, authors, abstract, feed_name, entry_kind, "
            "lane, relevance) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (title[:500], journal[:200], pub_date, doi, tag[:60], url, now,
             authors[:400], abstract[:4000], src, kind, lane, 0.9),
        )

    try:
        for query, tag in queries:
            stats["queried"] += 1
            print(f"\n  [{stats['queried']}/{len(queries)}] {query}")

            # ── PubMed ──────────────────────────────────────────────────────
            try:
                pmids = _pubmed_esearch(query, reldate=days, max_results=per_query)
                summaries = _pubmed_esummary(pmids) if pmids else []
                got = 0
                for item in summaries:
                    stats["seen"] += 1
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{item['pmid']}/"
                    doi = (item.get("doi") or "").lower()
                    if already(url, doi):
                        stats["dupes"] += 1
                        continue
                    if not dry:
                        insert(item.get("title", ""), item.get("source", ""),
                               item.get("pubdate", ""), doi, tag, url,
                               item.get("authors", ""), "", "PubMed")
                    stats["added"] += 1
                    got += 1
                print(f"       PubMed  : {len(summaries):>3} hits, {got} new")
            except Exception as exc:
                stats["errors"].append(f"PubMed/{query}: {type(exc).__name__}")
                print(f"       PubMed  : ERROR {exc}")

            # NCBI asks for <= 3 requests/second without a key; two calls per
            # query plus this pause keeps us comfortably inside that.
            time.sleep(0.4)

            # ── OpenAlex ────────────────────────────────────────────────────
            try:
                works = _openalex_search(query, from_date=from_date,
                                         max_results=per_query) or []
                got = 0
                for w in works:
                    stats["seen"] += 1
                    doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
                    url = w.get("doi") or w.get("id") or ""
                    if not url or already(url, doi):
                        stats["dupes"] += 1
                        continue
                    journal = ((w.get("primary_location") or {}).get("source")
                               or {}).get("display_name", "") or ""
                    authors = "; ".join(
                        (a.get("author") or {}).get("display_name", "")
                        for a in (w.get("authorships") or [])[:8]
                    )
                    abstract = _reconstruct_abstract(
                        w.get("abstract_inverted_index")) or ""
                    if not dry:
                        insert(w.get("title") or "Untitled", journal,
                               w.get("publication_date", ""), doi, tag, url,
                               authors, abstract, "OpenAlex")
                    stats["added"] += 1
                    got += 1
                print(f"       OpenAlex: {len(works):>3} hits, {got} new")
            except Exception as exc:
                stats["errors"].append(f"OpenAlex/{query}: {type(exc).__name__}")
                print(f"       OpenAlex: ERROR {exc}")

            time.sleep(0.3)

        if not dry:
            con.commit()
    finally:
        con.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", default="hat", choices=["hat", "profile", "both"])
    ap.add_argument("--years", type=float, default=4.0,
                    help="how far back to sweep (default 4)")
    ap.add_argument("--per-query", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    queries: list[tuple[str, str]] = []
    if args.topics in ("hat", "both"):
        queries += HAT_QUERIES
    if args.topics in ("profile", "both"):
        queries += profile_topics()

    print(f"Retrospective sweep — {len(queries)} queries, "
          f"{args.years:g} years back, {args.per_query}/query/source"
          f"{'  [DRY RUN]' if args.dry_run else ''}")

    stats = harvest(queries, args.years, args.per_query, args.dry_run)

    print(f"\n{'=' * 70}")
    print(f"  queries run : {stats['queried']}")
    print(f"  hits seen   : {stats['seen']}")
    print(f"  NEW         : {stats['added']}")
    print(f"  already had : {stats['dupes']}")
    if stats["errors"]:
        print(f"  errors      : {len(stats['errors'])}")
        for e in stats["errors"][:10]:
            print(f"      - {e}")
    print(f"{'=' * 70}")
    if args.dry_run:
        print("  DRY RUN — nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
