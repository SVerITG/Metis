#!/usr/bin/env python3
"""verify_library_feeds.py — prove a literature feed is alive before trusting it.

WHY THIS EXISTS
    feedparser does not raise on a 404. It returns an object with zero entries,
    which is indistinguishable from a journal that published nothing this week.
    A dead feed therefore looks like a quiet one, forever. 24 of 52 feeds in an
    earlier version of the allowlist were dead, several for years.

    So a feed is only acceptable if it PARSES, returns entries, AND carries a
    recent publication date. The third condition is the one that catches the
    worst case: a feed that still serves valid XML from 2021.

USAGE
    python3 tools/verify_library_feeds.py                 # check the live allowlist
    python3 tools/verify_library_feeds.py --candidates    # check proposed additions
    python3 tools/verify_library_feeds.py --all
"""
from __future__ import annotations

import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor

import feedparser

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)
STALE_DAYS = 120   # a journal that has not published in four months is suspect

# ---------------------------------------------------------------------------
# Candidate GENERAL SCIENCE feeds — the big-journal tier.
#
# These are NOT in LIBRARY_FEEDS today, which is why a "General Science" tab had
# nothing to fill it. The point of the tier is results important enough to matter
# outside their own field: Nature, Science, NEJM, Lancet, PNAS, BMJ, Cell.
#
# Deliberately the JOURNAL feeds, not the news desks — Nature's news feed already
# sits in NEWS_FEEDS, where journalism belongs. This tier is primary literature
# that happens to be broad, which is a different thing.
# ---------------------------------------------------------------------------
CANDIDATES = [
    ("Nature",                 "https://www.nature.com/nature/current_issue/rss"),
    ("Nature research",        "https://www.nature.com/nature.rss"),
    ("Science",                "https://www.science.org/rss/news_current.xml"),
    ("Science research",       "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science"),
    ("NEJM",                   "https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss"),
    ("The Lancet",             "https://www.thelancet.com/rssFeed/lancet_current.xml"),
    ("BMJ",                    "https://www.bmj.com/pages/rss"),
    ("BMJ current",            "https://www.bmj.com/rss/current.xml"),
    ("PNAS",                   "https://www.pnas.org/action/showFeed?type=etoc&feed=rss&jc=pnas"),
    ("Cell",                   "https://www.cell.com/cell/current.rss"),
    ("Nature Comms",           "https://www.nature.com/ncomms.rss"),
    ("eLife",                  "https://elifesciences.org/rss/recent.xml"),
    ("PLOS Biology",           "https://journals.plos.org/plosbiology/feed/atom"),
    ("Nature Human Behaviour", "https://www.nature.com/nathumbehav.rss"),
    ("Lancet Public Health",   "https://www.thelancet.com/rssFeed/lanpub_current.xml"),
    ("JAMA",                   "https://jamanetwork.com/rss/site_3/67.xml"),
    ("Nature Rev Dis Primers", "https://www.nature.com/nrdp.rss"),
    ("Science Advances",       "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv"),
]

# ---------------------------------------------------------------------------
# Candidate PARASITOLOGY / TRYPANOSOME-BIOLOGY feeds.
#
# Added after the researcher noticed new VSG-differentiation evidence had never reached his
# library. The cause is structural, not a ranking failure: LIBRARY_FEEDS covers
# epidemiology, surveillance, spatial methods and global health — and NOT ONE
# molecular parasitology journal. So HAT *biology* had no route into the library
# at all. Antigenic variation, VSG expression, stumpy-form differentiation and
# host–parasite work are published in exactly these titles.
#
# This matters beyond convenience: an elimination argument that ignores parasite
# biology is a weaker argument, and diagnostics (CATT, TL, rapid tests) depend
# directly on VSG variability.
# ---------------------------------------------------------------------------
PARASITOLOGY_CANDIDATES = [
    ("PLOS Pathogens",         "https://journals.plos.org/plospathogens/feed/atom"),
    ("Nature Microbiology",    "https://www.nature.com/nmicrobiol.rss"),
    ("Nature Rev Microbiol",   "https://www.nature.com/nrmicro.rss"),
    ("Trends in Parasitology", "https://www.cell.com/trends/parasitology/current.rss"),
    ("Cell Host & Microbe",    "https://www.cell.com/cell-host-microbe/current.rss"),
    ("mBio",                   "https://journals.asm.org/action/showFeed?type=etoc&feed=rss&jc=mbio"),
    ("PLOS Biology",           "https://journals.plos.org/plosbiology/feed/atom"),
    ("Mol Microbiology",       "https://onlinelibrary.wiley.com/feed/13652958/most-recent"),
    ("Parasitology (CUP)",     "https://www.cambridge.org/core/rss/product/id/D9F3E1D4F0F0E4C9A3F5"),
    ("Int J Parasitology",     "https://rss.sciencedirect.com/publication/science/00207519"),
    ("Acta Tropica",           "https://rss.sciencedirect.com/publication/science/0001706X"),
    ("Exp Parasitology",       "https://rss.sciencedirect.com/publication/science/00144894"),
    ("PLOS ONE parasitology",  "https://journals.plos.org/plosone/feed/atom"),
    ("Emerg Microbes & Inf",   "https://www.tandfonline.com/feed/rss/temi20"),
    ("Nucleic Acids Research", "https://academic.oup.com/rss/site_5127/OpenAccess.xml"),
    ("bioRxiv microbiology",   "https://connect.biorxiv.org/biorxiv_xml.php?subject=microbiology"),
    ("bioRxiv all",            "https://connect.biorxiv.org/biorxiv_xml.php?subject=all"),
    ("Wellcome Open Research", "https://wellcomeopenresearch.org/rss/site_articles"),
    ("Open Research Africa",   "https://openresearchafrica.org/rss/site_articles"),
]


def fetch(url: str):
    """Parse, retrying once with a browser UA — many publishers 403 the default."""
    first = feedparser.parse(url)
    if first.entries:
        return first
    status = getattr(first, "status", None) or 0
    if status in (401, 403, 406, 429) or status == 0 or status >= 500:
        second = feedparser.parse(url, agent=BROWSER_UA)
        if second.entries:
            return second
    return first


def newest_date(parsed) -> dt.date | None:
    best = None
    for e in parsed.entries[:25]:
        for key in ("published_parsed", "updated_parsed"):
            tm = e.get(key)
            if tm:
                try:
                    d = dt.date(tm[0], tm[1], tm[2])
                except (TypeError, ValueError):
                    continue
                if best is None or d > best:
                    best = d
    return best


def check(pair: tuple[str, str]) -> dict:
    name, url = pair
    try:
        parsed = fetch(url)
    except Exception as exc:
        return {"name": name, "url": url, "verdict": "ERROR",
                "detail": f"{type(exc).__name__}: {str(exc)[:70]}"}

    status = getattr(parsed, "status", None) or 0
    n = len(parsed.entries)
    if status >= 400:
        return {"name": name, "url": url, "verdict": "DEAD",
                "detail": f"HTTP {status}"}
    if n == 0:
        bozo = str(getattr(parsed, "bozo_exception", "") or "")[:60]
        return {"name": name, "url": url, "verdict": "EMPTY",
                "detail": f"0 entries{f' ({bozo})' if bozo else ''}"}

    newest = newest_date(parsed)
    if newest is None:
        # Some feeds (Spatial & Spatio-temporal Epi is one) carry no dates at all.
        # Usable, but the surface must fall back to scan time for ordering.
        return {"name": name, "url": url, "verdict": "OK-NODATE",
                "detail": f"{n} entries, no publication dates"}

    age = (dt.date.today() - newest).days
    verdict = "OK" if age <= STALE_DAYS else "STALE"
    return {"name": name, "url": url, "verdict": verdict,
            "detail": f"{n} entries, newest {newest.isoformat()} ({age}d)"}


def run(pairs: list[tuple[str, str]], label: str) -> list[dict]:
    print(f"\n{'=' * 78}\n{label}  ({len(pairs)} feeds)\n{'=' * 78}")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, pairs))
    order = {"OK": 0, "OK-NODATE": 1, "STALE": 2, "EMPTY": 3, "DEAD": 4, "ERROR": 5}
    for r in sorted(results, key=lambda x: (order.get(x["verdict"], 9), x["name"])):
        mark = {"OK": "✓", "OK-NODATE": "~", "STALE": "!",
                "EMPTY": "✗", "DEAD": "✗", "ERROR": "✗"}[r["verdict"]]
        print(f" {mark} {r['verdict']:<10} {r['name']:<26} {r['detail']}")
    good = sum(1 for r in results if r["verdict"].startswith("OK"))
    print(f"\n  usable: {good}/{len(results)}")
    return results


def main() -> int:
    args = set(sys.argv[1:])
    do_all = "--all" in args or not args
    if do_all or "--live" in args:
        sys.path.insert(0, "system/mcp-server/src")
        try:
            from metis_mcp.tools.content_scan import LIBRARY_FEEDS
            run([(n, u) for n, u, _ in LIBRARY_FEEDS], "LIVE LIBRARY_FEEDS")
        except Exception as exc:
            print(f"could not import LIBRARY_FEEDS: {exc}")
    if do_all or "--candidates" in args:
        run(CANDIDATES, "CANDIDATE GENERAL-SCIENCE FEEDS")
    if do_all or "--parasitology" in args:
        run(PARASITOLOGY_CANDIDATES, "CANDIDATE PARASITOLOGY / TRYPANOSOME FEEDS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
