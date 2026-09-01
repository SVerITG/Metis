"""Content scan tools — RSS feed ingestion, literature discovery, inbox scan.
No LLM calls. Pure data fetching and dedup.
"""
import html as _html
import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.local_overrides import load_overrides
from metis_mcp.tools.guardrails import sanitize_external

log = logging.getLogger("metis.content_scan")


def _dashboard_port(default: int = 8080) -> int:
    """Live dashboard port written by run.sh, so printed links never drift."""
    try:
        port_file = paths.root / "system" / "app-py" / ".metis-port"
        return int(port_file.read_text().strip())
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════════════════════════
# TWO SEPARATE FEED LISTS, because News and Library are different jobs.
#
# NEWS_FEEDS   → news_briefs      → the News surface
# LIBRARY_FEEDS → new_publications → the Library surface
#
# The distinction is not "health vs science", it is **journalism vs primary
# literature**:
#
#   News is reporting that PICKED UP a result — Guardian Science on a Lancet
#   paper, ScienceDaily on a new model, STAT on a trial readout. It is what
#   happened, and what the world is saying about it.
#
#   Library is the primary literature itself — journal tables-of-contents and
#   preprint servers. It exists to build a scientific background, not to tell you
#   the news, and it is scanned on the Library's schedule, not the News one.
#
# Mixing them was a recurring bug: journal ToCs landed in news_briefs and the
# relevance ranking PROMOTED them to the lead, because a paper is by definition
# closer to a researcher's corpus than a headline. Separate lists make that
# structurally impossible rather than a filter someone has to remember.
#
# EVERY URL BELOW WAS VERIFIED LIVE ON 2026-08-19: parsed, non-empty, and recent.
# Never add one unverified — feedparser returns an EMPTY RESULT rather than
# raising on a 404, so a bad URL fails silently and looks like a quiet news day
# forever. 24 of the 52 feeds in the version before this were dead, some for
# years. `check_news_feeds` exists to catch exactly that.
# ═══════════════════════════════════════════════════════════════════════════════

NEWS_FEEDS = [
    # ── Outbreak & disease surveillance ───────────────────────────────────────
    # ECDC publishes per-topic feeds at taxonomy/term/<id>/feed (listed on
    # ecdc.europa.eu/en/rss-feeds). The weekly Communicable Disease Threats
    # Report is the working substitute for WHO's retired DON feed.
    ("ECDC threats report",    "https://www.ecdc.europa.eu/en/taxonomy/term/1505/feed",                 "surveillance,outbreaks,public-health"),
    ("ECDC epi updates",       "https://www.ecdc.europa.eu/en/taxonomy/term/1310/feed",                 "surveillance,epidemiology"),
    ("ECDC news",              "https://www.ecdc.europa.eu/en/taxonomy/term/1307/feed",                 "surveillance,public-health"),
    ("WHO AFRO",               "https://www.afro.who.int/rss.xml",                                       "surveillance,public-health,africa"),
    ("WHO AFRO press",         "https://afro.who.int/rss/featured-news.xml",                            "surveillance,public-health,africa"),
    ("PAHO news",              "https://www.paho.org/en/rss.xml",                                        "surveillance,public-health,americas"),
    ("Outbreak News Today",    "https://outbreaknewstoday.com/feed/",                                   "surveillance,outbreaks,infectious-disease"),
    ("Avian Flu Diary",        "https://afludiary.blogspot.com/feeds/posts/default?alt=rss",            "surveillance,outbreaks,infectious-disease"),

    # ── Science journalism — reporting ON research ────────────────────────────
    # This is the block that makes News a news surface. Aggregators first:
    # ScienceDaily and Phys.org syndicate university and journal press releases,
    # so one feed covers hundreds of institutions.
    ("ScienceDaily",           "https://www.sciencedaily.com/rss/all.xml",                              "science"),
    ("ScienceDaily health",    "https://www.sciencedaily.com/rss/health_medicine.xml",                  "science,public-health"),
    ("Phys.org",               "https://phys.org/rss-feed/",                                             "science"),
    ("MedicalXpress",          "https://medicalxpress.com/rss-feed/",                                    "science,public-health"),
    ("Guardian Science",       "https://www.theguardian.com/science/rss",                               "science"),
    ("Guardian Environment",   "https://www.theguardian.com/environment/rss",                           "science,climate-health"),
    ("BBC Sci & Environment",  "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",         "science"),
    ("BBC Health",             "https://feeds.bbci.co.uk/news/health/rss.xml",                          "science,public-health"),
    ("Science News",           "https://www.sciencenews.org/feed",                                       "science"),
    ("New Scientist",          "https://www.newscientist.com/feed/home/",                               "science"),
    ("Ars Technica Science",   "https://arstechnica.com/science/feed/",                                 "science"),
    ("Quanta",                 "https://www.quantamagazine.org/feed/",                                  "science"),
    ("Nature news",            "https://www.nature.com/nature.rss",                                     "science"),
    ("Nature health sci",      "https://www.nature.com/subjects/health-sciences.rss",                   "science,public-health"),
    ("Science news",           "https://www.science.org/rss/news_current.xml",                          "science"),
    # ("Lancet", ".../rssFeed/lancet_current.xml") — REMOVED 2026-08-21. That URL
    # is the Lancet's journal TABLE OF CONTENTS, and a ToC in News is the precise
    # failure the NEWS/LIBRARY split was built to make impossible; it had survived
    # the 2026-08-19 split unnoticed. Now in LIBRARY_FEEDS as general-science.
    # Lancet journalism still reaches News via STAT, Guardian Science and
    # ScienceDaily, which report ON Lancet papers rather than listing them.
    # Research-integrity reporting. Directly useful when assessing a literature
    # base: a retracted paper you have cited is news you want early.
    ("Retraction Watch",       "https://retractionwatch.com/feed/",                                     "science,methods"),
    ("Undark",                 "https://undark.org/feed/",                                              "science"),
    # The Conversation is academics writing for a general audience — the closest
    # thing to "a researcher explaining what this result means". The Africa desk
    # is the most relevant edition for this field.
    ("The Conversation Africa","https://theconversation.com/africa/articles.atom",                      "science,africa,public-health"),
    ("The Conversation health","https://theconversation.com/africa/health/articles.atom",               "science,public-health,africa"),

    # ── Global-health journalism ──────────────────────────────────────────────
    ("STAT News",              "https://www.statnews.com/feed/",                                        "public-health,science"),
    ("KFF Health News",        "https://kffhealthnews.org/feed/",                                       "public-health,policy"),
    ("Health Policy Watch",    "https://healthpolicy-watch.news/feed/",                                 "policy,public-health"),
    ("IHP Newsletter",         "https://www.internationalhealthpolicies.org/feed/",                     "policy,public-health"),
    ("Geneva Health Files",    "https://genevahealthfiles.substack.com/feed",                           "policy,health-financing"),
    ("Lancet Global Health",   "https://www.thelancet.com/rssFeed/langlo_current.xml",                  "public-health,policy"),

    # ── Policy & financing ────────────────────────────────────────────────────
    ("Global Fund",            "https://www.theglobalfund.org/data/rss-feeds/latest/",                  "policy,health-financing"),
    ("Unitaid",                "https://unitaid.org/feed/",                                             "policy,health-financing"),
    ("DNDi",                   "https://dndi.org/feed/?post_type=news",                                 "ntd,tropical-medicine,policy"),
    ("MSF",                    "https://www.msf.org/rss/all",                                           "field-research,public-health,tropical-medicine"),
    ("UN News health",         "https://news.un.org/feed/subscribe/en/news/topic/health/feed/rss.xml",  "policy,public-health"),

    # ── Humanitarian & disaster ───────────────────────────────────────────────
    # Outbreaks happen inside emergencies, so disaster feeds are epidemiological
    # context, not a separate interest. GDACS is the EU/UN automated alert system.
    ("GDACS alerts",           "https://www.gdacs.org/xml/rss.xml",                                     "policy,disasters"),
    ("ReliefWeb disasters",    "https://reliefweb.int/disasters/rss.xml",                               "policy,disasters"),
    ("Reliefweb",              "https://reliefweb.int/updates/rss.xml",                                 "policy,public-health"),
    ("ReliefWeb DRC",          "https://reliefweb.int/updates/rss.xml?advanced-search=%28C61%29",        "policy,africa,drc"),
    ("OCHA",                   "https://www.unocha.org/rss.xml",                                        "policy,disasters"),
    ("IFRC",                   "https://www.ifrc.org/rss.xml",                                          "policy,disasters"),
    ("The New Humanitarian",   "https://www.thenewhumanitarian.org/rss.xml",                            "policy,public-health,africa"),
    ("Guardian Global dev",    "https://www.theguardian.com/global-development/rss",                    "policy,public-health,africa"),

    # ── Africa desks ──────────────────────────────────────────────────────────
    ("AllAfrica health",       "https://allafrica.com/tools/headlines/rdf/health/headlines.rdf",        "africa,public-health"),
    ("AllAfrica",              "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",        "africa,world-news"),
    ("RFI Afrique",            "https://www.rfi.fr/fr/afrique/rss",                                     "africa,world-news"),
    ("Le Monde Afrique",       "https://www.lemonde.fr/afrique/rss_full.xml",                           "africa,world-news"),
    ("France24 Afrique",       "https://www.france24.com/fr/afrique/rss",                               "africa,world-news"),

    # ── World ─────────────────────────────────────────────────────────────────
    ("BBC World",              "https://feeds.bbci.co.uk/news/world/rss.xml",                           "world-news"),
    ("Al Jazeera",             "https://www.aljazeera.com/xml/rss/all.xml",                             "world-news,africa"),

    # ── AI ────────────────────────────────────────────────────────────────────
    # Anthropic publishes NO official feed (verified: every candidate 404s; only
    # third-party scraper mirrors exist, not a dependency worth taking).
    ("MIT Tech Review AI",     "https://www.technologyreview.com/topic/artificial-intelligence/feed",   "AI"),
    ("Google AI blog",         "https://blog.google/technology/ai/rss/",                                "AI"),
    ("Ars Technica AI",        "https://arstechnica.com/ai/feed/",                                      "AI"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# LIBRARY FEEDS — primary literature. Scanned by scan_library_feeds(), NOT by the
# news scan, and written to `new_publications` for the Library surface.
#
# Springer/BMC expose every journal at
#   link.springer.com/search.rss?facet-journal-id=<id>
# which is how the whole BMC family below is reachable — the older
# <journal>.biomedcentral.com/articles/most-recent/rss.xml form now 301s to a
# non-feed.
#
# NOT INCLUDED — PubMed. Its feeds require an `rss_guid` generated by clicking
# "Create RSS" on a saved search, so the URL cannot be constructed. Rather than
# block on that, this list covers the same ground through publishers and
# preprint servers directly. If a PubMed saved search is ever wanted, paste its
# erss.cgi URL here.
# ═══════════════════════════════════════════════════════════════════════════════

LIBRARY_FEEDS = [
    # ── NTDs & tropical medicine ──────────────────────────────────────────────
    ("PLOS NTDs",              "https://journals.plos.org/plosntds/feed/atom",                                    "ntd,tropical-medicine,public-health"),
    ("Parasites & Vectors",    "https://link.springer.com/search.rss?facet-journal-id=13071",                     "ntd,tropical-medicine,vectors"),
    ("Infect Dis Poverty",     "https://link.springer.com/search.rss?facet-journal-id=40249",                     "ntd,tropical-medicine,public-health"),
    ("Trop Med & Health",      "https://link.springer.com/search.rss?facet-journal-id=41182",                     "tropical-medicine,public-health"),
    ("Tropical Med & IH",      "https://onlinelibrary.wiley.com/feed/13653156/most-recent",                       "tropical-medicine,methods,public-health"),
    ("Malaria Journal",        "https://link.springer.com/search.rss?facet-journal-id=12936",                     "malaria,tropical-medicine"),

    # ── Infectious disease & surveillance ─────────────────────────────────────
    ("Lancet Inf. Diseases",   "https://www.thelancet.com/rssFeed/laninf_current.xml",                            "infectious-disease,public-health,methods"),
    ("CDC EID journal",        "https://wwwnc.cdc.gov/eid/rss/ahead-of-print.xml",                                "methods,surveillance"),
    ("BMC Infect Dis",         "https://link.springer.com/search.rss?facet-journal-id=12879",                     "infectious-disease,epidemiology"),

    # ── Global & public health ────────────────────────────────────────────────
    ("PLOS Medicine",          "https://journals.plos.org/plosmedicine/feed/atom",                                "public-health,methods"),
    ("PLOS Global Pub Health", "https://journals.plos.org/globalpublichealth/feed/atom",                           "public-health,policy"),
    ("BMJ Global Health",      "https://gh.bmj.com/rss/current.xml",                                              "public-health,methods"),
    ("Conflict and Health",    "https://link.springer.com/search.rss?facet-journal-id=13031",                     "conflict-health,public-health"),

    # ── Methods, spatial epidemiology, modelling ───────────────────────────────
    ("Int J Health Geogr",     "https://link.springer.com/search.rss?facet-journal-id=12942",                     "spatial-epi,methods"),
    # No publication dates in this feed; date filters fall back to scan time.
    ("Spat Spatio-temp Epi",   "https://rss.sciencedirect.com/publication/science/18775845",                      "spatial-epi,methods"),
    ("Int J Epidemiology",     "https://academic.oup.com/rss/site_5339/OpenAccess.xml",                           "methods,epidemiology"),

    # ── Preprints ─────────────────────────────────────────────────────────────
    ("medRxiv",                "https://connect.medrxiv.org/medrxiv_xml.php?subject=all",                          "preprint,epidemiology,public-health"),
    ("arXiv q-bio (epi)",      "https://rss.arxiv.org/rss/q-bio.PE",                                               "epidemiology,methods,preprint"),

    # ── Biomedical & AI-in-science ────────────────────────────────────────────
    ("Nature Medicine",        "https://www.nature.com/nm.rss",                                                    "methods,biomedical"),
    ("Nature Mach Intell",     "https://www.nature.com/natmachintell.rss",                                         "AI,methods"),
    ("arXiv cs.AI",            "https://rss.arxiv.org/rss/cs.AI",                                                   "AI,methods"),

    # ── PARASITE BIOLOGY ──────────────────────────────────────────────────────
    # Added 2026-08-21 after the researcher found that new VSG-differentiation evidence had
    # never reached his library. The cause was structural, not a ranking failure:
    # every feed above is epidemiology, surveillance, methods or global health,
    # and NOT ONE was a molecular parasitology journal. HAT *biology* therefore
    # had no route into the library at all — antigenic variation, VSG expression
    # and switching, stumpy-form differentiation, host–parasite interaction.
    #
    # This is not adjacent curiosity. Serodiagnosis (CATT, trypanolysis, RDTs)
    # rests directly on VSG variability, and an elimination argument that ignores
    # parasite biology is a weaker argument.
    #
    # ALL VERIFIED LIVE 2026-08-21 by tools/verify_library_feeds.py.
    ("PLOS Pathogens",         "https://journals.plos.org/plospathogens/feed/atom",                                "parasitology,trypanosome,molecular,infectious-disease"),
    ("Nature Microbiology",    "https://www.nature.com/nmicrobiol.rss",                                            "parasitology,molecular,infectious-disease"),
    ("Nature Rev Microbiol",   "https://www.nature.com/nrmicro.rss",                                               "parasitology,molecular,infectious-disease"),
    ("Trends in Parasitology", "https://www.cell.com/trends/parasitology/current.rss",                             "parasitology,trypanosome,tropical-medicine"),
    ("Cell Host & Microbe",    "https://www.cell.com/cell-host-microbe/current.rss",                               "parasitology,molecular,immunology"),
    ("Mol Microbiology",       "https://onlinelibrary.wiley.com/feed/13652958/most-recent",                        "parasitology,molecular,trypanosome"),
    ("mBio",                   "https://journals.asm.org/action/showFeed?type=etoc&feed=rss&jc=mbio",              "parasitology,molecular,infectious-disease"),
    ("Emerg Microbes & Inf",   "https://www.tandfonline.com/feed/rss/temi20",                                      "parasitology,infectious-disease"),
    # No publication dates in these three; date filters fall back to scan time.
    ("Acta Tropica",           "https://rss.sciencedirect.com/publication/science/0001706X",                       "parasitology,tropical-medicine,ntd"),
    ("Int J Parasitology",     "https://rss.sciencedirect.com/publication/science/00207519",                       "parasitology,trypanosome"),
    ("Exp Parasitology",       "https://rss.sciencedirect.com/publication/science/00144894",                       "parasitology,trypanosome"),
    # Preprints are where trypanosome molecular biology appears first, often by a
    # year. bioRxiv 'all' is broad but the relevance centroid does the filtering.
    ("bioRxiv microbiology",   "https://connect.biorxiv.org/biorxiv_xml.php?subject=microbiology",                 "preprint,parasitology,molecular"),
    ("Wellcome Open Research", "https://wellcomeopenresearch.org/rss/site_articles",                               "parasitology,tropical-medicine,ntd"),

    # ── GENERAL SCIENCE ───────────────────────────────────────────────────────
    # The `general-science` tag is load-bearing, not decorative: it is what routes
    # an item to the General Science lane instead of a topic tab. The tier exists
    # for results important enough to matter outside their own field — which is a
    # different job from tracking one's own literature, and mixing the two buries
    # the NTD work under a much larger flow of high-profile biology.
    #
    # Deliberately the JOURNAL feeds, not the news desks: Nature's and Science's
    # news feeds live in NEWS_FEEDS, where journalism belongs.
    #
    # ALL VERIFIED LIVE 2026-08-21. BMJ is absent because both its feed patterns
    # return HTTP 403 to any automated client.
    ("Nature",                 "https://www.nature.com/nature/current_issue/rss",                                  "general-science"),
    ("Science",                "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science",            "general-science"),
    ("NEJM",                   "https://www.nejm.org/action/showFeed?jc=nejm&type=etoc&feed=rss",                  "general-science,public-health"),
    # Moved here from NEWS_FEEDS 2026-08-21: lancet_current.xml is a journal
    # table of contents, and a ToC in News is the exact failure the two-list
    # split was created to make impossible. It had survived the split unnoticed.
    ("The Lancet",             "https://www.thelancet.com/rssFeed/lancet_current.xml",                             "general-science,public-health"),
    ("Lancet Public Health",   "https://www.thelancet.com/rssFeed/lanpub_current.xml",                             "general-science,public-health,policy"),
    ("JAMA",                   "https://jamanetwork.com/rss/site_3/67.xml",                                        "general-science,public-health"),
    ("PNAS",                   "https://www.pnas.org/action/showFeed?type=etoc&feed=rss&jc=pnas",                  "general-science"),
    ("Science Advances",       "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=sciadv",             "general-science"),
    ("Nature Comms",           "https://www.nature.com/ncomms.rss",                                                "general-science"),
    ("eLife",                  "https://elifesciences.org/rss/recent.xml",                                         "general-science"),
    ("Cell",                   "https://www.cell.com/cell/current.rss",                                            "general-science"),
    ("Nature Rev Dis Primers", "https://www.nature.com/nrdp.rss",                                                  "general-science,methods"),
]

# Combined view, kept because existing callers and `check_news_feeds` iterate one
# list. The 4th element is the KIND, derived rather than hand-maintained so the
# two lists cannot disagree with it.
FEED_ALLOWLIST = (
    [(n, u, t, "news") for n, u, t in NEWS_FEEDS]
    + [(n, u, t, "paper") for n, u, t in LIBRARY_FEEDS]
)

# ═══════════════════════════════════════════════════════════════════════════════
# REMOVED — verified permanently unavailable 2026-08-19. Recorded so nobody
# re-adds them; all were in the list returning nothing, silently, for months.
#
#  WHO outbreak news / DON / WER — WHO RETIRED RSS FOR DISEASE OUTBREAK NEWS.
#      The DON page now offers an email subscription only. No feed exists.
#      ECDC threats report + WHO AFRO above are the substitutes.
#  ProMED-mail   — ISID closed its feed permanently in 2023 to stop scraping.
#  CIDRAP        — only parseable feed last published 2022-11-22 (1,365d stale).
#  Africa CDC    — /feed/ 200 but unparseable; outbreak feed 750d stale.
#  Anthropic     — no official feed; only third-party scraper mirrors.
#  Reuters       — feeds.reuters.com NXDOMAIN, public RSS retired.
#  EurekAlert, Scientific American, Think Global Health, Global Health NOW,
#  BMJ news (403), Nature Medicine news (303), Devex (403, paywalled),
#  ACAPS, Mail & Guardian, Nation Africa, WHO EURO, WHO SEARO, CDC newsroom,
#  Europe PMC — all 403/404/unparseable on every pattern tried.
#  Eurosurveillance — five URL patterns all dead.
#  MDPI ×3       — 403; MDPI blocks automated feed access.
#  GOARN, Gavi, Wellcome, ITM Antwerp — 404/302/Cloudflare challenge.
#  bioRxiv epidemiology — parses but last published 2021-07-10 (1,866d).
#      medRxiv (above) covers the same ground and is current.
# ═══════════════════════════════════════════════════════════════════════════════

# Many publishers reject feedparser's default User-Agent outright. Measured
# 2026-08-19: Africa CDC returned 403 Forbidden with the default UA and a clean
# 200 with a browser-style one; WHO, Anthropic and Wellcome also 403 on default.
# Because feedparser swallows the HTTP error and returns an object with zero
# entries, this failed SILENTLY — `scan_news_feeds` recorded "0 new items" and
# looked like a quiet news day rather than a blocked request. That is why the
# feed looked thin: not too few sources, but sources that never answered.
# There is no single UA that works everywhere, so try both. Measured 2026-08-19,
# sequential single requests (the parallel test was confounded by rate limiting):
#   default UA  → Al Jazeera and France24 return 200; Africa CDC returns 403
#   browser UA  → Africa CDC returns 200; Al Jazeera and France24 return 403
# Committing to either loses feeds. Fetch tries the default first and retries with
# the browser UA only on an auth-ish rejection, so no publisher is hit twice
# unnecessarily.
FEED_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)
_RETRY_STATUSES = (401, 403, 406, 429)


def _fetch_feed(url: str):
    """Parse a feed, retrying once with a browser User-Agent on rejection.

    Returns the feedparser result whose entry list is non-empty where possible,
    so the caller sees the best of the two attempts rather than the last one.
    """
    first = feedparser.parse(url)
    if first.entries:
        return first
    status = getattr(first, "status", None) or 0
    if status in _RETRY_STATUSES or status == 0 or status >= 500:
        second = feedparser.parse(url, agent=FEED_USER_AGENT)
        if second.entries:
            return second
        # Report whichever attempt got further than a bare rejection.
        if (getattr(second, "status", None) or 0) and status in _RETRY_STATUSES:
            return second
    return first

_DDL_NEWS = """
CREATE TABLE IF NOT EXISTS news_briefs (
    brief_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT,
    domain         TEXT,
    signal_strength TEXT,
    summary        TEXT,
    source_url     TEXT,
    created_at     TEXT,
    tags           TEXT,
    brief_date     TEXT,
    -- when the story was PUBLISHED (from the feed). created_at is the scan time.
    published_at   TEXT DEFAULT ''
)
"""

_DDL_LIT = """
CREATE TABLE IF NOT EXISTS literature_metadata (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT,
    authors    TEXT,
    year       INTEGER,
    source     TEXT,
    tags       TEXT,
    doi        TEXT,
    created_at TEXT
)
"""


def _connect():
    conn = sqlite3.connect(str(paths.db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# Domain classification keyword sets. "AI" ships as a generic, universally
# relevant default; any field-specific domains (diseases, health systems, …) are
# loaded from the gitignored local override file, so the public source stays
# domain-agnostic. Override domains are checked first (more specific), AI last.
_AI_KEYWORDS = {
    "llm", "large language model", "machine learning", "neural network",
    "artificial intelligence", "deep learning", "transformer", "gpt", "claude",
    "gemini", "generative ai", "agentic", "agent framework",
}
_DOMAIN_OVERRIDE: list[tuple[set[str], str]] = []
for _domain, _kws in (load_overrides().get("domain_keywords") or {}).items():
    if isinstance(_kws, list) and _kws:
        _DOMAIN_OVERRIDE.append((set(str(k).lower() for k in _kws), str(_domain)))
_DOMAIN_OVERRIDE.append((_AI_KEYWORDS, "AI"))


import uuid as _uuid


def _entry_authors(entry) -> str:
    """Author list from a feed entry, '' if the feed omits it.

    Feeds disagree wildly here: Atom gives `authors` as a list of dicts, RSS gives
    a single `author` string, Springer and Wiley put a semicolon-joined list in
    `dc_creator`, and preprint servers often give nothing at all. A catalogue row
    without authors is close to unusable — you cannot recognise a paper you have
    already read — so it is worth trying all four shapes.
    """
    names: list[str] = []
    for a in (entry.get("authors") or []):
        n = (a.get("name") or "").strip() if isinstance(a, dict) else str(a).strip()
        if n and n not in names:
            names.append(n)
    if not names:
        for key in ("author", "dc_creator", "creator"):
            raw = entry.get(key)
            if isinstance(raw, str) and raw.strip():
                names = [p.strip() for p in raw.split(";") if p.strip()] or [raw.strip()]
                break
    return "; ".join(names[:10])[:400]


_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def _entry_doi(entry, link: str = "") -> str:
    """Best-effort DOI for a feed entry.

    Worth the effort because the DOI is the key to EVERYTHING downstream: the
    open-access lookup, the institutional resolver, the Zotero item, and dedup
    against a library that already holds the paper under a different title
    spelling. A row without a DOI cannot be acquired automatically at all.

    Publishers expose it in at least five places, none of them standard.
    """
    for key in ("prism_doi", "dc_identifier", "doi", "id", "guid"):
        raw = entry.get(key)
        if isinstance(raw, str):
            m = _DOI_RE.search(raw)
            if m:
                return m.group(0).rstrip(".,;)").lower()
    for field in (link, entry.get("link", "") or ""):
        m = _DOI_RE.search(field or "")
        if m:
            return m.group(0).rstrip(".,;)").lower()
    return ""


def _entry_published(entry) -> str:
    """ISO publication timestamp from a feed entry, or '' if the feed omits it.

    Why this matters: `created_at` records when the SCAN ran, so it answers "when
    did Metis notice this?" — not "when did it happen?". Between 13 Jul and 18 Aug
    2026 no scan ran at all, and every story from that window was then stamped
    18 August. Any daily/weekly/monthly filter built on created_at therefore
    reports the scanner's uptime rather than the news, which is worse than having
    no filter because it looks authoritative.

    feedparser normalises the several date formats RSS and Atom permit into
    `published_parsed` / `updated_parsed` struct_times, already UTC.
    """
    import calendar as _calendar

    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        st = entry.get(field)
        if not st:
            continue
        try:
            ts = _calendar.timegm(st)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            # A feed that reports a date far in the future is broken, not prescient.
            if dt > datetime.now(timezone.utc) + timedelta(days=2):
                continue
            return dt.replace(tzinfo=None).isoformat()
        except (TypeError, ValueError, OverflowError):
            continue
    return ""


def _strip_html(text: str) -> str:
    """RSS summaries arrive as HTML fragments; the dashboard renders them as text.

    Feeds routinely put markup in <description> — ReliefWeb ships
    `<div class="tag country">Country: Chad</div>` — and Jinja correctly escapes it,
    so the card shows the tags as literal characters instead of a summary. Measured
    2026-08-12: 474 of 874 stored briefs, 54%, displayed markup rather than prose.

    Tags are removed, entities decoded, whitespace collapsed. Done at ingestion
    rather than in the template because the value is also embedded for relevance
    scoring, and scoring "div class tag country" as content is its own small harm.
    """
    import html as _html
    import re as _re

    if not text:
        return ""
    # UNESCAPE FIRST, then strip — and repeat, because feeds double-encode.
    # Stripping first leaves `&lt;div&gt;` untouched (it is not yet a tag) and the
    # unescape then TURNS IT INTO one, so the cleaner manufactures the markup it
    # was meant to remove. Measured: a first pass in the wrong order cleaned 475
    # rows and left 456 still showing tags.
    for _ in range(3):
        prev = text
        text = _html.unescape(text)
        text = _re.sub(r"<br\s*/?>|</p>|</div>|</li>", " ", text, flags=_re.I)
        text = _re.sub(r"<[^>]+>", "", text)
        if text == prev:
            break
    return _re.sub(r"\s+", " ", text).strip()


def _classify_domain(title: str, summary: str, feed_tags: str) -> str:
    """Return the most specific domain for an article.

    Checks title + summary text against keyword sets first. If a keyword matches,
    that domain wins over the feed-level tag. Falls back to the first feed tag so
    we never return an empty string.
    """
    haystack = (title + " " + summary).lower()
    for keywords, domain in _DOMAIN_OVERRIDE:
        if any(kw in haystack for kw in keywords):
            return _norm_domain(domain)
    # No keyword match — fall back to first feed tag
    return _norm_domain(feed_tags.split(",")[0])


def _norm_domain(domain: str) -> str:
    """Lowercase, hyphenated domain tag.

    The stored values had drifted into mixed case because the override keys in
    `domain-overrides.local.json` are written naturally ('NTD', 'HAT',
    'SPATIAL-EPI', 'MALARIA') while feed tags are lowercase. The result was
    'NTD' (52 rows) and 'ntd' (48 rows) as two different domains, and
    'SURVEILLANCE' separate from 'surveillance' — so a category filter grouping
    by domain silently showed half of each. Normalising once at ingestion is the
    fix; the News tabs also case-fold at match time so existing rows still group.
    """
    return re.sub(r"[\s_]+", "-", (domain or "").strip().lower())


# High-authority sources — a hit here lifts the signal one level.
_AUTHORITY_SOURCES = {
    "who outbreak news", "lancet inf. diseases", "nature medicine",
    "plos medicine", "plos ntds", "eurosurveillance", "cdc eid journal",
    "africa cdc", "ecdc threat reports", "bmj global health",
    "int j epidemiology", "who afro", "ijh geographics",
}
# Words that mark a genuinely high-signal development (not routine coverage).
_URGENCY_WORDS = {
    "outbreak", "emergency", "alert", "elimination", "eliminated", "breakthrough",
    "first case", "resurgence", "epidemic", "pandemic", "recall", "withdrawn",
    "approval", "approved", "vaccine", "resistance", "novel", "emerging",
}

# Board auto-classification — routes scanned items into the Outbreaks / Events /
# Funding boxes on the Today surface. Outbreaks are SOURCE-GATED (only actual
# surveillance feeds), not keyword-gated, to avoid false positives from research
# articles that merely mention "outbreak". Events and Funding use keywords but
# require specific multi-word phrases to stay selective.
_OUTBREAK_SOURCES = {
    "who outbreak news", "who don (full)", "promed-mail", "goarn",
    "africa cdc", "ecdc threat reports", "who afro", "who wer",
}
_EVENT_KEYWORDS = {
    "call for abstracts", "registration open", "annual meeting",
    "congress 2026", "congress 2027", "symposium 2026", "symposium 2027",
    "conference 2026", "conference 2027", "workshop 2026", "workshop 2027",
}
_FUNDING_KEYWORDS = {
    "call for proposals", "call for applications", "request for applications",
    "request for proposals", "funding opportunity", "grant opportunity",
    "fellowship opportunity", "scholarship deadline",
}

_DDL_BOARD = """
CREATE TABLE IF NOT EXISTS today_board_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    board       TEXT NOT NULL,
    title       TEXT NOT NULL,
    url         TEXT DEFAULT '',
    description TEXT DEFAULT '',
    source      TEXT DEFAULT '',
    starred     INTEGER DEFAULT 0,
    dismissed   INTEGER DEFAULT 0,
    auto_added  INTEGER DEFAULT 1,
    start_date  TEXT DEFAULT '',
    end_date    TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def _maybe_add_to_board(conn, title: str, url: str, summary: str, source_name: str):
    """Route a scanned article to a Today board if it qualifies.

    Outbreaks: source-gated — only items from actual surveillance feeds (WHO DON,
    ProMED, GOARN, etc.). A journal article mentioning "outbreak" is NOT an outbreak.
    Events/Funding: keyword-gated with selective multi-word phrases.
    """
    board = None
    # Outbreaks: only from surveillance sources
    if source_name.lower() in _OUTBREAK_SOURCES:
        board = "outbreaks"
    else:
        haystack = (title + " " + summary).lower()
        if any(w in haystack for w in _EVENT_KEYWORDS):
            board = "events"
        elif any(w in haystack for w in _FUNDING_KEYWORDS):
            board = "funding"
    if not board:
        return
    if conn.execute("SELECT 1 FROM today_board_items WHERE url=? LIMIT 1", (url,)).fetchone():
        return
    conn.execute(
        "INSERT INTO today_board_items (board, title, url, source, auto_added) "
        "VALUES (?, ?, ?, ?, 1)",
        (board, title[:300], url, source_name),
    )


@app.tool()
def update_today_board(board: str, items: list[dict]) -> dict:
    """Fill a Today-surface board (Outbreaks, Events or Funding) with items you found on the web.

    Use this after web-searching for the researcher's field. The Outbreaks board holds
    current active disease outbreaks / public-health emergencies; the Events board holds
    upcoming scientific congresses/conferences/symposia; the Funding board holds open
    or upcoming research funding calls, grants and fellowships. These boards have no
    RSS source, so this tool is how Claude Desktop (on the user's subscription, no API
    rate limit) keeps them current — the dashboard's "Update" buttons open
    a chat that calls this tool.

    Replaces the previously tool-filled rows on that board; items the user curated or
    added by hand are preserved.

    Args:
        board: "outbreaks", "events" or "funding".
        items: list of objects, each {"title": str, "url": str, "date": str (optional,
            event date or application deadline), "description": str (optional, one short
            sentence)}. Only include real items with a working http(s) URL.

    Returns:
        dict: {ok, board, saved} on success, or {ok: False, error} on failure.
    """
    import sqlite3 as _sqlite3
    import datetime as _dt

    board = (board or "").strip().lower()
    if board not in ("outbreaks", "events", "funding"):
        return {"ok": False, "error": "board must be 'outbreaks', 'events' or 'funding'"}

    clean: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        title = str(it.get("title", "")).strip()
        url = str(it.get("url", "")).strip()
        if not title or not url.lower().startswith("http") or url in seen:
            continue
        seen.add(url)
        date = str(it.get("date", "")).strip()
        desc = str(it.get("description", "")).strip()
        if date:
            desc = (desc + f" · {date}").strip(" ·")
        clean.append((title[:300], url[:500], desc[:400]))

    if not clean:
        return {"ok": False, "error": "no valid items — each needs a title and an http(s) url"}

    try:
        conn = _sqlite3.connect(str(paths.db))
        conn.execute(_DDL_BOARD)
        now = _dt.datetime.now().isoformat()
        # Refresh = replace previous auto/tool-added rows; keep curated & manual.
        conn.execute(
            "DELETE FROM today_board_items WHERE board=? AND source IN ('web-search','claude')",
            (board,),
        )
        added = 0
        for title, url, desc in clean:
            if conn.execute(
                "SELECT 1 FROM today_board_items WHERE board=? AND url=? LIMIT 1", (board, url)
            ).fetchone():
                continue  # don't shadow a curated/manual item with the same URL
            conn.execute(
                "INSERT INTO today_board_items (board, title, url, description, source, auto_added, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'claude', 1, ?, ?)",
                (board, title, url, desc, now, now),
            )
            added += 1
        conn.commit()
        conn.close()
        return {"ok": True, "board": board, "saved": added}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _user_topics(channel: str = "news") -> set[str]:
    """Lower-cased topic terms for relevance scoring, for one channel.

    `channel="news"` scores news items against what the person wants to HEAR
    about; `channel="library"` scores papers against what they want a scientific
    BACKGROUND on. These are separate lists on purpose — someone may follow a
    conflict in the news daily and never collect literature on it, and want deep
    literature on a method that never makes the news. Scoring both channels off a
    single list made each one wrong in a different direction.

    Falls back to user-config.yaml's research block, which is background-shaped,
    so a person who has only been through the install wizard still gets sensible
    library scoring.
    """
    out: set[str] = set()
    try:
        from metis_mcp.tools.user_profile import read_interest_lists
        lists = read_interest_lists()
        key = "library" if channel == "library" else "news"
        out = {t.strip().lower() for t in lists.get(key, []) if t.strip()}
    except Exception:
        pass

    # Always fold in the declared field/topics from the install wizard: they are
    # the baseline for both channels when nothing more specific has been set.
    try:
        import yaml
        cfg_path = paths.config / "user-config.yaml"
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            research = cfg.get("research", {}) if isinstance(cfg.get("research"), dict) else {}
            topics = research.get("topics") or cfg.get("topics") or []
            if isinstance(topics, str):
                topics = [t.strip() for t in topics.split(",")]
            out |= {str(t).strip().lower() for t in topics if str(t).strip()}
            field = research.get("field") or cfg.get("field") or ""
            if field:
                out.add(str(field).strip().lower())
    except Exception:
        pass
    return out


def _score_signal(title: str, summary: str, feed_name: str,
                  user_topics: set[str], sem: float = 0.0) -> str:
    """Heuristic signal strength: 'high' | 'medium' | 'low'.

    Combines source authority, urgency vocabulary, keyword overlap with the user's
    configured topics, AND semantic closeness to the user's ACTUAL corpus (``sem``
    = cosine similarity to the interest-profile centroid, see relevance.py). The
    semantic term is what makes results "close to my work" rather than mere keyword
    hits. Thresholds calibrated on the real corpus: relevant items cluster ~0.65+,
    unrelated ~0.57-.
    """
    haystack = (title + " " + summary).lower()
    score = 0
    if feed_name.lower() in _AUTHORITY_SOURCES:
        score += 1
    if any(w in haystack for w in _URGENCY_WORDS):
        score += 2  # an outbreak / approval / elimination is a strong signal on its own
    if user_topics and any(t in haystack for t in user_topics):
        score += 2  # keyword overlap with configured topics
    if sem >= 0.64:
        score += 3
    elif sem >= 0.60:
        score += 2
    elif sem >= 0.575:
        score += 1

    # ── "HIGH" NOW REQUIRES SEMANTIC EVIDENCE ─────────────────────────────
    # the researcher, 2026-08-31: "When it says 'related to your work' it is not so close
    # actually."
    #
    # He was right, and the arithmetic shows why: an urgency word scored +2 and
    # one topic keyword another +2, so ANY item mentioning an outbreak and any
    # configured term reached the threshold of 3 and was labelled high — with a
    # semantic similarity of zero. A story could be called close to his work
    # without ever being compared to his work.
    #
    # Urgency and keywords are still worth points; they can no longer buy the
    # top label on their own. The floor is 0.60, where relevant items cluster
    # on this corpus (unrelated ones sit at 0.57 and below).
    #
    # WHEN THE SIMILARITY IS MISSING (sem == 0.0 exactly — embeddings
    # unavailable, not "measured as unrelated") the old heuristic still decides,
    # so a scan without the model is degraded rather than flattened to low.
    scored_semantically = sem > 0.0
    if scored_semantically:
        if score >= 3 and sem >= 0.60:
            return "high"
        if score >= 1 or sem >= 0.575:
            return "medium"
        return "low"

    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def _scan_feeds(feeds, max_per_feed: int = 10) -> dict:
    """Scan a given feed list. `feeds` is [(name, url, tags, kind), ...].

    One engine, two callers: `scan_news_feeds()` passes NEWS_FEEDS and
    `scan_library_feeds()` passes LIBRARY_FEEDS. Previously a single function
    walked the combined list and branched on kind, which meant a News scan always
    also pulled 21 journal tables-of-contents, and the Library could not be
    refreshed without re-scanning every newspaper. News and Library are different
    jobs on different schedules; they now have different entry points.
    """
    from metis_mcp.tools.news_images import DDL as _IMG_DDL, image_from_entry, resolve_image
    papers_added = 0

    added = 0
    errors = []
    # Score against the channel this scan actually serves: news items against
    # what the person wants to hear about, papers against what they want a
    # background on. `feeds` is homogeneous per call (scan_news_feeds /
    # scan_library_feeds each pass one kind), so one lookup is correct.
    _kind = feeds[0][3] if feeds else "news"
    user_topics = _user_topics("library" if _kind == "paper" else "news")
    with _connect() as conn:
        conn.execute(_DDL_NEWS)
        conn.execute(_IMG_DDL)
        try:
            conn.execute("ALTER TABLE news_briefs ADD COLUMN image_url TEXT DEFAULT ''")
        except Exception:
            pass  # already there

        conn.execute(_DDL_BOARD)
        # Numeric semantic relevance (closeness to the user's corpus) for ranking.
        try:
            conn.execute("ALTER TABLE news_briefs ADD COLUMN relevance REAL DEFAULT 0")
        except Exception:
            pass
        conn.commit()

        # Build the interest-profile centroid once (cached daily; local, no API).
        # MAX-ANCHOR, not centroid. A centroid of 5 topics + ~100 work items +
        # ~390 library titles means "public health in general", and on that
        # measure a foodborne-bacteria paper outscored a paper on passive HAT
        # screening. Scoring against the CLOSEST SINGLE project / idea / note
        # separates his work from the middle ground; see relevance.py.
        centroid = None
        _score_batch = None
        try:
            from metis_mcp.tools.relevance import (build_profile,
                                                   score_batch_profile as _score_batch)
            centroid = build_profile(conn)
        except Exception:
            _score_batch = None

        for name, url, tags, kind in feeds:
            try:
                parsed = _fetch_feed(url)
                # feedparser never raises on HTTP errors — it returns an object
                # with no entries — so a 403/404 was indistinguishable from a
                # quiet feed. Record it as an error so a dead source is visible
                # in the scan report instead of masquerading as no news.
                _status = getattr(parsed, "status", None)
                if _status and _status >= 400:
                    errors.append(f"{name}: HTTP {_status}")
                    continue
                if not parsed.entries:
                    _bozo = str(getattr(parsed, "bozo_exception", "") or "")[:80]
                    errors.append(f"{name}: no entries" + (f" ({_bozo})" if _bozo else ""))
                    continue
                pending = []
                for entry in parsed.entries[:max_per_feed]:
                    link = entry.get("link", "")
                    title = entry.get("title", "").strip()
                    if not link or not title:
                        continue
                    # Dedup against the table this feed actually WRITES to.
                    _dedup_table = "new_publications" if kind == "paper" else "news_briefs"
                    if conn.execute(
                        f"SELECT 1 FROM {_dedup_table} WHERE source_url=? LIMIT 1", (link,)
                    ).fetchone():
                        continue
                    # Thumbnail: free from the feed if present (BBC/Guardian do),
                    # else resolved from the article's og:image below (journals).
                    pending.append((title, entry.get("summary", "")[:800], link,
                                    image_from_entry(entry), _entry_published(entry)))
                if not pending:
                    continue
                # One batched embedding call per feed (efficient).
                sims = (_score_batch([f"{t}. {s}" for t, s, _, _, _ in pending], centroid)
                        if _score_batch else [0.0] * len(pending))
                for (title, summary_raw, link, feed_img, published_at), sim in zip(pending, sims):
                    # Classify/score on the RAW text (an injection banner must not
                    # skew relevance), then sanitise before it touches the DB.
                    primary_domain = _classify_domain(title, summary_raw, tags)
                    signal = _score_signal(title, summary_raw, name, user_topics, sim)

                    # ── INGESTION CHOKEPOINT — RSS is fully attacker-controlled text.
                    src = f"RSS:{name}"
                    title = sanitize_external(title, f"{src}:title", compact=True)
                    summary_raw = _strip_html(summary_raw)
                    summary_raw = sanitize_external(summary_raw, src)

                    # ── ROUTE ON KIND ────────────────────────────────────────
                    # A journal table-of-contents feed emits PAPERS. They belong in
                    # the library, not on the news surface. Sending them to
                    # news_briefs is what filled News with articles and preprints —
                    # and the relevance ranking then promoted them to the lead,
                    # because a paper is by definition closer to a researcher's
                    # corpus than a BBC headline.
                    if kind == "paper":
                        # The ABSTRACT. For a journal ToC feed, entry.summary IS
                        # the abstract — and this branch used to discard it while
                        # the news branch below kept the same field. That single
                        # omission is why "let me read the abstract" was
                        # impossible for exactly the items that had one.
                        abstract = summary_raw[:4000]
                        authors = _entry_authors(entry)
                        doi = _entry_doi(entry, link)
                        entry_kind, lane = classify_publication(
                            title, abstract, name, tags, link, float(sim),
                        )
                        raw_date = (published_at[:10] if published_at
                                    else datetime.now().date().isoformat())
                        pub_iso, pub_prec = normalise_pub_date(raw_date)
                        tkey = publication_title_key(title)
                        # Title-key dedup, in ADDITION to the source_url check
                        # above: the same paper arrives from a journal feed and a
                        # preprint server under two different URLs and, when
                        # PubMed omits the DOI, with no shared key at all.
                        if tkey and conn.execute(
                            "SELECT 1 FROM new_publications WHERE title_key=? LIMIT 1",
                            (tkey,),
                        ).fetchone():
                            continue
                        conn.execute(
                            """INSERT INTO new_publications
                               (title, journal, pub_date, doi, topic_tag, source_url,
                                discovered_at, authors, abstract, feed_name,
                                entry_kind, lane, relevance, pub_iso, pub_precision,
                                title_key)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            # pub_date is the paper's real date when the feed gives
                            # one; falling back to today made every backlog paper
                            # look published on the day it was scanned.
                            (title, name, raw_date,
                             doi, tags, link, datetime.now().isoformat(),
                             authors, abstract, name, entry_kind, lane,
                             round(float(sim), 4), pub_iso, pub_prec, tkey),
                        )
                        papers_added += 1
                        continue

                    # A news page without pictures is a list of links. Never let a
                    # slow image lookup break a scan — resolve_image never raises.
                    image_url = feed_img or (resolve_image(None, link, conn) or "")

                    # published_at = when it HAPPENED (from the feed, '' if absent).
                    # created_at   = when this scan ran. Both are kept: readers use
                    # COALESCE(published_at, created_at) so pre-2026-08-19 rows,
                    # which have no publication date recoverable, still sort.
                    conn.execute(
                        """INSERT INTO news_briefs
                           (brief_id, title, domain, signal_strength, summary, source_url, created_at, tags, brief_date, relevance, image_url, published_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            f"nb-{_uuid.uuid4().hex[:12]}", title, primary_domain, signal, summary_raw, link,
                         datetime.now().isoformat(), tags,
                         (published_at[:10] if published_at else datetime.now().date().isoformat()),
                         round(float(sim), 4), image_url, published_at),
                    )
                    _maybe_add_to_board(conn, title, link, summary_raw, name)
                    added += 1
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {str(e)[:120]}")
            # COMMIT PER FEED, not once at the end. Found 2026-09-01: this scan
            # ran inside ONE write transaction spanning every feed — and the
            # network fetch for feed N+1 happens inside it. In WAL mode a write
            # transaction holds an exclusive lock, so for the whole run — over
            # five minutes, measured — no other writer anywhere in Metis could
            # commit: not the dashboard, not the MCP servers. Marking a task
            # done returned 500; the boot scan starts 25s after the dashboard
            # does, so this was the state of the system for minutes after every
            # single restart.
            #
            # One commit per feed bounds the lock to one feed's inserts. It also
            # means a scan that dies halfway keeps what it already found, which
            # the all-or-nothing version did not.
            try:
                conn.commit()
            except Exception as _commit_exc:
                errors.append(f"{name}: commit failed: {str(_commit_exc)[:80]}")
        conn.commit()
    # Reported separately on purpose: "12 news, 30 papers" is the honest picture.
    # They are different things and they went to different places.
    return {
        "news_added": added,
        "papers_added": papers_added,
        "errors": errors,
        "semantic": centroid is not None,
        "feeds_checked": len(feeds),
    }


def scan_news_feeds(max_per_feed: int = 10) -> dict:
    """Scan the NEWS feeds only — journalism, into `news_briefs`.

    Journal tables-of-contents are deliberately NOT scanned here. News is
    reporting that picked up a result; the primary literature is the Library's
    job (`scan_library_feeds`).
    """
    return _scan_feeds([(n, u, t, "news") for n, u, t in NEWS_FEEDS], max_per_feed)


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSIFYING A DISCOVERED PUBLICATION
#
# Two independent axes, and keeping them independent is the whole point:
#
#   entry_kind — WHAT the thing is (article, review, preprint, book, report).
#       the researcher asked for articles and books to be listed separately, which is
#       impossible if nothing records which is which.
#
#   lane       — WHERE it belongs on the surface (his field, or general science).
#       A Nature paper about trypanosome antigenic variation is NOT general
#       science to him; it is the middle of his field that happens to have been
#       published somewhere prestigious. So the lane cannot be read off the
#       journal alone — it needs corpus closeness too.
# ═══════════════════════════════════════════════════════════════════════════════

GENERAL_SCIENCE_TAG = "general-science"

_PUB_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def normalise_pub_date(raw: str) -> tuple[str, str]:
    """Normalise a publication date to (iso, precision).

    Sources disagree completely: feeds and OpenAlex give '2026-08-18', PubMed
    gives '2026 Jul 1', '2026 Aug', or bare '2026'. A time window built on the
    raw string compares LEXICALLY, so '2026 Jul 1' sorts after '2026-08-20' and a
    July paper shows up under Today while an August one does not — wrong, and
    silently so.

    Month precision resolves to the 1st and year precision to 1 January, with the
    precision returned alongside so a surface can render "Aug 2026" instead of
    implying a day it does not know.

    Mirrored in tools/normalise_pub_dates.py, which backfills existing rows.
    """
    s = (raw or "").strip()
    if not s:
        return "", ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "day"
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}", "day"
    m = re.match(r"^(\d{4})\s+([A-Za-z]{3,9})\s+(\d{1,2})", s)
    if m:
        mi = _PUB_MONTHS.get(m.group(2)[:3].lower())
        if mi:
            day = min(max(int(m.group(3)), 1), 28 if mi == 2 else 30)
            return f"{m.group(1)}-{mi:02d}-{day:02d}", "day"
    m = re.match(r"^(\d{4})\s+([A-Za-z]{3,9})", s)
    if m:
        mi = _PUB_MONTHS.get(m.group(2)[:3].lower())
        if mi:
            return f"{m.group(1)}-{mi:02d}-01", "month"
    m = re.match(r"^(\d{4})", s)
    if m and 1800 <= int(m.group(1)) <= 2100:
        return f"{m.group(1)}-01-01", "year"
    return "", ""


def publication_title_key(title: str) -> str:
    """Normalised title used to dedup one paper arriving by several routes.

    A paper reaches new_publications from a journal feed, a preprint server, a
    PubMed query and an OpenAlex query. PubMed's esummary often omits the DOI, so
    URL-and-DOI dedup let the same paper in three times — observed as triplicates
    immediately after the first retrospective sweep.

    Exact match on a normalised key, deliberately not fuzzy: a wrongly MERGED
    paper is invisible and unrecoverable, while a missed duplicate is merely
    untidy. Mirrored in tools/dedup_new_publications.py.
    """
    t = _html.unescape(title or "")
    t = re.sub(r"<[^>]+>", " ", t)               # journals ship <i>…</i> in titles
    t = re.sub(r"^\s*\[[^\]]{1,40}\]\s*", "", t)  # "[Comment] ", "[Correspondence] "
    t = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    return t if len(t) >= 18 else ""

# Above this centroid similarity an item counts as "close to my work" and stays
# in a topic tab even when it came from a general-science feed. Calibrated
# against the measurements recorded when relevance.py landed: NTD/HAT/malaria
# scored 0.65–0.73, an AI paper 0.545, off-topic material ~0.52.
FIELD_RELEVANCE_FLOOR = 0.62

_KIND_PATTERNS = (
    # Order matters — first match wins, most specific first.
    ("preprint", ("biorxiv", "medrxiv", "arxiv", "preprint", "research square")),
    ("review",   ("a review", "systematic review", "meta-analysis", "scoping review",
                  "narrative review", "trends in", "nature rev", "annual review")),
    ("book",     ("handbook", "textbook", "monograph", "second edition",
                  "third edition", "(ed.)", "(eds.)")),
    ("report",   ("world health report", "situation report", "technical report",
                  "guideline", "guidelines", "position paper", "roadmap")),
)


def classify_publication(
    title: str,
    summary: str,
    feed_name: str,
    tags: str,
    link: str,
    relevance: float,
) -> tuple[str, str]:
    """Return (entry_kind, lane) for one discovered publication.

    Deliberately conservative: anything unrecognised is an 'article' in the
    'field' lane, because a misfiled item the researcher can still see beats one
    quietly routed to a tab he never opens. The failure mode to avoid is silent
    disappearance, not imprecise labelling.
    """
    haystack = f"{title} {feed_name} {link}".lower()

    kind = "article"
    for candidate, needles in _KIND_PATTERNS:
        if any(n in haystack for n in needles):
            kind = candidate
            break

    tag_set = {t.strip().lower() for t in (tags or "").split(",") if t.strip()}
    from_general_feed = GENERAL_SCIENCE_TAG in tag_set

    # A general-science feed only produces a general-science item when the paper
    # is NOT close to his corpus. This is the rule that keeps a Nature paper on
    # trypanosomes out of the "interesting but not mine" pile.
    lane = "general" if (from_general_feed and relevance < FIELD_RELEVANCE_FLOOR) else "field"
    return kind, lane


def scan_library_feeds(max_per_feed: int = 10) -> dict:
    """Scan the LIBRARY feeds only — journal ToCs and preprints, into
    `new_publications`.

    This is the literature-alert side: it exists to build a scientific background,
    not to report the news, so it runs on the Library's schedule and its output
    never reaches the News surface.
    """
    return _scan_feeds([(n, u, t, "paper") for n, u, t in LIBRARY_FEEDS], max_per_feed)


def scan_literature_folder() -> dict:
    """Scan inputs/literature/ for new PDFs not yet in literature_metadata."""
    lit_path = paths.root / "inputs" / "literature"
    if not lit_path.exists():
        return {"papers_added": 0, "note": "no literature folder"}
    added = 0
    with _connect() as conn:
        conn.execute(_DDL_LIT)
        conn.commit()
        for pdf in lit_path.rglob("*.pdf"):
            stem = pdf.stem
            if conn.execute(
                "SELECT 1 FROM literature_metadata WHERE title=? LIMIT 1", (stem,)
            ).fetchone():
                continue
            domain_hint = pdf.parent.name
            conn.execute(
                """INSERT INTO literature_metadata
                   (title, authors, year, source, tags, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (stem, "unknown", None, "local-pdf", domain_hint, datetime.now().isoformat()),
            )
            added += 1
        conn.commit()
    return {"papers_added": added}


AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".aac", ".opus", ".webm"}
DOC_EXTS   = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx"}


def _scan_inbox() -> dict:
    """Count and categorise files in inbox/ that haven't been processed."""
    inbox = paths.root / "inbox"
    if not inbox.exists():
        return {"inbox_items": 0, "audio": [], "docs": [], "other": []}
    items = [f for f in inbox.iterdir() if f.is_file() and not f.name.startswith(".")]
    audio = [f for f in items if f.suffix.lower() in AUDIO_EXTS]
    docs  = [f for f in items if f.suffix.lower() in DOC_EXTS]
    other = [f for f in items if f not in audio and f not in docs]
    return {
        "inbox_items": len(items),
        "audio": [str(f) for f in audio],
        "docs":  [f.name for f in docs],
        "other": [f.name for f in other],
        "files": [f.name for f in items[:10]],
    }


def _transcribe_inbox_audio(audio_path: str, model_size: str = "base") -> str | None:
    """Transcribe a single audio file with faster-whisper. Returns text or None."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, beam_size=3)
        text = " ".join(seg.text.strip() for seg in segments).strip() or None
    except Exception as e:
        log.warning("Inbox transcription failed for %s: %s: %s",
                    audio_path, type(e).__name__, e)
        return None

    # ── INGESTION CHOKEPOINT — a transcript is external content. The audio may be
    #    a recorded meeting, a downloaded talk, or anything else a third party
    #    said. It goes straight into `ideas` and then into cross-pollination.
    if text:
        text = sanitize_external(text, f"audio-transcript:{Path(audio_path).name}")
    return text


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@app.tool()
async def scan_news() -> list[TextContent]:
    """Fetch the news feeds and add new items to the News surface.

    Scans journalism only — outbreak surveillance (ECDC threats report, WHO AFRO,
    PAHO), science reporting (ScienceDaily, Guardian Science, STAT, Nature news,
    The Conversation Africa), humanitarian and disaster feeds (GDACS, ReliefWeb,
    OCHA), Africa desks and policy sources. Journal tables-of-contents are NOT
    scanned here: the primary literature is the Library's job, via
    `scan_library`. Deduplicates by URL, so running it repeatedly is safe.
    """
    result = scan_news_feeds()
    errors = result.get("errors", [])
    msg = (f"News scan complete. {result['news_added']} new items added "
           f"from {result.get('feeds_checked', 0)} feeds.")
    if errors:
        msg += (f"\n{len(errors)} feed(s) failed and contributed nothing: "
                + "; ".join(errors[:5]))
        if len(errors) > 5:
            msg += f" (+{len(errors) - 5} more)"
        msg += "\nRun a feed check to see the full list."
    return [TextContent(type="text", text=msg)]


@app.tool()
async def scan_library() -> list[TextContent]:
    """Fetch the literature feeds and add new papers to the Library.

    This is the Library's own scan: journal tables-of-contents and preprint
    servers (PLOS NTDs, Parasites & Vectors, Malaria Journal, Lancet ID, CDC EID,
    BMC Infectious Diseases, Int J Health Geographics, medRxiv, arXiv q-bio …),
    written to `new_publications` for the literature-alert surface.

    Separate from `scan_news` on purpose: this builds a scientific background
    rather than reporting what happened, so it runs on its own schedule and its
    output never appears on the News surface. Deduplicates by URL.
    """
    result = scan_library_feeds()
    errors = result.get("errors", [])
    msg = (f"Library scan complete. {result['papers_added']} new paper(s) added "
           f"from {result.get('feeds_checked', 0)} journal/preprint feeds.")
    if errors:
        msg += (f"\n{len(errors)} feed(s) failed: " + "; ".join(errors[:5]))
    return [TextContent(type="text", text=msg)]


@app.tool()
async def scan_literature() -> list[TextContent]:
    """Scan inputs/literature/ for new PDFs and register them in literature_metadata.

    Walks all subdirectories. Uses the parent folder name as a domain tag.
    Deduplicates by title so running multiple times is safe.
    """
    result = scan_literature_folder()
    note = result.get("note", "")
    msg = f"Literature scan complete. {result['papers_added']} new papers registered."
    if note:
        msg += f" ({note})"
    return [TextContent(type="text", text=msg)]


@app.tool()
async def scan_inbox(auto_transcribe_audio: bool = True) -> list[TextContent]:
    """Scan the inbox/ folder and auto-transcribe any audio files to ideas.

    Detects audio files (.m4a, .mp3, .wav, .ogg, .flac, .aac) and, when
    auto_transcribe_audio=True (default), transcribes each one with faster-whisper
    and captures the transcript as an idea. The audio file is moved to
    inbox/processed/ after successful transcription.

    Non-audio files are listed but left for manual review.

    Args:
        auto_transcribe_audio: When True (default), automatically transcribe
            audio files found in the inbox. Set to False to just list them.
    """
    import os
    import shutil
    result = _scan_inbox()
    n = result["inbox_items"]
    if n == 0:
        return [TextContent(type="text", text="Inbox is clear.")]

    lines: list[str] = [f"Inbox: {n} item(s) found."]
    audio_paths = result.get("audio", [])
    docs  = result.get("docs", [])
    other = result.get("other", [])

    # ── Audio files: auto-transcribe ─────────────────────────────────────────
    transcribed, failed = 0, 0
    if audio_paths and auto_transcribe_audio:
        lines.append(f"\n🎙 Audio files ({len(audio_paths)}) — transcribing with Whisper:")
        processed_dir = paths.root / "inbox" / "processed"
        processed_dir.mkdir(exist_ok=True)

        for audio_path_str in audio_paths:
            audio_path = Path(audio_path_str)
            fname = audio_path.name
            text = _transcribe_inbox_audio(str(audio_path))
            if text:
                # Capture as idea via cross-pollination
                try:
                    from metis_mcp.tools.ideas import _cross_pollinate_core
                    from metis_mcp.db import connect
                    now = datetime.now().isoformat()
                    with connect(paths.db) as conn:
                        conn.execute(
                            "INSERT INTO ideas (content, tags, created_at) VALUES (?, ?, ?)",
                            (text, f"voice-note,inbox,auto-transcribed", now),
                        )
                    connections = _cross_pollinate_core(text[:400], max_results=3) or []
                except Exception:
                    connections = []

                conn_summary = ""
                if connections:
                    conn_summary = " → " + ", ".join(c.get("title", "")[:40] for c in connections[:2])

                lines.append(f"  ✓ {fname}: \"{text[:80]}…\"{conn_summary}")
                transcribed += 1

                # Move to processed/
                try:
                    shutil.move(str(audio_path), str(processed_dir / fname))
                except Exception:
                    pass
            else:
                lines.append(f"  ✗ {fname}: transcription failed (faster-whisper not installed or empty audio)")
                failed += 1

    elif audio_paths:
        lines.append(f"\n🎙 Audio files ({len(audio_paths)}) — set auto_transcribe_audio=True to process:")
        for p in audio_paths:
            lines.append(f"  · {Path(p).name}")

    # ── Documents ─────────────────────────────────────────────────────────────
    if docs:
        lines.append(f"\n📄 Documents ({len(docs)}) — route manually:")
        for f in docs[:5]:
            lines.append(f"  · {f}")
        if len(docs) > 5:
            lines.append(f"  · … and {len(docs) - 5} more")

    # ── Other ─────────────────────────────────────────────────────────────────
    if other:
        lines.append(f"\n📦 Other ({len(other)}):")
        for f in other[:5]:
            lines.append(f"  · {f}")

    if transcribed:
        lines.append(f"\n✓ {transcribed} voice note(s) captured as ideas. Audio moved to inbox/processed/.")
    if failed:
        lines.append(f"⚠ {failed} audio file(s) could not be transcribed — install faster-whisper if missing.")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def get_news_briefs(
    limit: int = 10,
    source_type: str = "",
    domain: str = "",
    since: str = "",
) -> list[TextContent]:
    """Retrieve recent news briefs from the database.

    Args:
        limit: Maximum number of briefs to return (default 10).
        source_type: Filter by type — "news" for RSS items, "article" for scientific papers. Empty = all.
        domain: Filter by domain tag (e.g. "HAT", "AI", "public-health"). Empty = all.
        since: ISO date string — only return briefs created after this date. Empty = all.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="Database not found.")]

    conditions: list[str] = []
    params: list = []
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)
    if domain:
        conditions.append("domain = ?")
        params.append(domain)
    if since:
        conditions.append("created_at >= ?")
        params.append(since)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    with _connect() as conn:
        conn.execute(_DDL_NEWS)
        rows = conn.execute(
            f"SELECT brief_id, title, domain, signal_strength, summary, source_url, "
            f"source_type, created_at, tags "
            f"FROM news_briefs {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()

    if not rows:
        return [TextContent(type="text", text="No news briefs found.")]

    lines = [f"{len(rows)} brief(s):\n"]
    for r in rows:
        tag = f"[{(r['domain'] or '').upper()}]" if r["domain"] else "[—]"
        src = f"\n  {r['source_url']}" if r["source_url"] else ""
        summary = (r["summary"] or "")[:200]
        lines.append(f"{tag} {r['title']}\n  {summary}{src}")
    return [TextContent(type="text", text="\n\n".join(lines))]


@app.tool()
async def check_news_feeds(kind: str = "news") -> list[TextContent]:
    """Check every news feed and report which ones are actually working.

    Why this exists: feedparser never raises on an HTTP error — it returns an
    object with zero entries. So a feed returning 404 or 403 was indistinguishable
    from a quiet news day, and `scan_news_feeds` reported "0 new items" either way.
    Measured 2026-08-19: 14 of 33 news feeds were HTTP-dead and had been
    contributing nothing, silently. That is the real reason the News surface looked
    thin — not too few sources, but sources that never answered.

    Requests are sequential and spaced, because hammering publishers in parallel
    produces 403s that are rate limiting rather than real rejections.

    Args:
        kind: "news" (journalism, the News surface), "paper" (journal ToCs and
            preprints, the Library), or "all". Default "news".

    Returns:
        Per feed: working (with entry count and newest publication date) or the
        HTTP status that needs fixing.
    """
    import time as _time

    feeds = [f for f in FEED_ALLOWLIST if kind == "all" or f[3] == kind]
    if not feeds:
        return [TextContent(type="text", text=f"No feeds of kind '{kind}'.")]

    working: list[str] = []
    broken: list[str] = []
    undated: list[str] = []

    for i, (name, url, tags, fkind) in enumerate(feeds):
        try:
            parsed = _fetch_feed(url)
            status = getattr(parsed, "status", None)
            n = len(parsed.entries)
            if n:
                dated = sum(1 for e in parsed.entries[:10] if _entry_published(e))
                newest = (_entry_published(parsed.entries[0]) or "")[:10] or "no date"
                working.append(f"{name} — {n} entries, newest {newest}")
                if dated == 0:
                    undated.append(name)
            else:
                bz = str(getattr(parsed, "bozo_exception", "") or "")[:60]
                broken.append(f"{name} — HTTP {status}" + (f" · {bz}" if bz else ""))
        except Exception as e:
            broken.append(f"{name} — {type(e).__name__}: {str(e)[:60]}")
        if i < len(feeds) - 1:
            _time.sleep(1.5)

    lines = [f"**Feed health — {len(feeds)} '{kind}' feed(s) checked**", ""]
    lines.append(f"WORKING ({len(working)}):")
    for w in working:
        lines.append(f"  · {w}")
    if broken:
        lines.append("")
        lines.append(f"NOT WORKING ({len(broken)}) — these contribute nothing and need a new URL:")
        for b in broken:
            lines.append(f"  · {b}")
    if undated:
        lines.append("")
        lines.append(
            "No publication dates (period filters fall back to scan time): "
            + ", ".join(undated)
        )
    if broken:
        lines.append("")
        lines.append(
            f"{len(broken)} of {len(feeds)} sources are dead. Until they are replaced, "
            "the news you see is drawn from the remainder — so a quiet briefing may "
            "mean a broken feed rather than a quiet week."
        )
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def full_scan() -> list[TextContent]:
    """Run all Metis update scans in sequence and return a combined report.

    Runs:
    1. News feeds (RSS) — new items added to news_briefs
    2. Literature folder — new PDFs registered in literature_metadata
    3. Inbox — unprocessed items flagged
    4. Tracked files — changed files reported

    No LLM calls. Safe to run at any time.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"── Metis Full Scan ── {now} ──\n"]

    # 1. News (journalism)
    try:
        news = scan_news_feeds()
        err_note = f" ({len(news['errors'])} feed errors)" if news["errors"] else ""
        lines.append(f"NEWS       {news['news_added']:>4} new items "
                     f"from {news.get('feeds_checked', 0)} feeds{err_note}")
    except Exception as e:
        lines.append(f"NEWS       ERROR: {e}")

    # 1b. Library feeds (journal ToCs + preprints). Reported on its own line
    # because it goes somewhere else and answers a different question.
    try:
        lib = scan_library_feeds()
        err_note = f" ({len(lib['errors'])} feed errors)" if lib["errors"] else ""
        lines.append(f"PAPERS     {lib['papers_added']:>4} new papers "
                     f"from {lib.get('feeds_checked', 0)} journal feeds{err_note}")
    except Exception as e:
        lines.append(f"PAPERS     ERROR: {e}")

    # 2. Literature
    try:
        lit = scan_literature_folder()
        note = f" ({lit.get('note', '')})" if lit.get("note") else ""
        lines.append(f"LITERATURE {lit['papers_added']:>4} new papers{note}")
    except Exception as e:
        lines.append(f"LITERATURE ERROR: {e}")

    # 3. Inbox
    try:
        inbox = _scan_inbox()
        n = inbox["inbox_items"]
        lines.append(f"INBOX      {n:>4} unprocessed item(s)")
        if n and inbox.get("files"):
            for f in inbox["files"][:5]:
                lines.append(f"             · {f}")
    except Exception as e:
        lines.append(f"INBOX      ERROR: {e}")

    # 4. Tracked files
    try:
        from metis_mcp.db import connect
        import datetime as _dt
        utcnow = _dt.datetime.now(_dt.timezone.utc).isoformat()
        changed = []
        with connect(paths.db) as conn:
            rows = conn.execute(
                "SELECT path, last_modified FROM tracked_files WHERE watch = 1"
            ).fetchall()
            for row in rows:
                fp = Path(row["path"])
                if fp.exists():
                    mtime = _dt.datetime.fromtimestamp(
                        fp.stat().st_mtime, tz=_dt.timezone.utc
                    ).isoformat()
                    if mtime > (row["last_modified"] or ""):
                        changed.append(fp.name)
                        conn.execute(
                            "UPDATE tracked_files SET last_modified=? WHERE path=?",
                            (mtime, row["path"]),
                        )
            conn.commit()
        lines.append(f"FILES      {len(changed):>4} changed since last scan")
        for f in changed[:5]:
            lines.append(f"             · {f}")
    except Exception as e:
        lines.append(f"FILES      ERROR: {e}")

    lines.append(f"\nDashboard: http://127.0.0.1:{_dashboard_port()}")
    return [TextContent(type="text", text="\n".join(lines))]
