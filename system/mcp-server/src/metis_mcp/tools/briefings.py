"""Nature Briefing — the editorial digests, kept apart from the news feed.

WHY THIS IS NOT JUST ANOTHER RSS SOURCE
    The researcher asked for the Nature Daily Briefing and the AI & Robotics Briefing to
    have "special places in the news surface". They are not a wire feed: each one
    is an EDITION, edited as a whole, with a running order that means something.
    Shredding them into `news_briefs` would drop 3,700 more headlines into a feed
    already carrying 3,700, and lose the only thing a briefing has that a feed
    does not — someone decided what mattered today, and in what order.

    So an edition is a row, its stories are rows beneath it, and the surface
    shows editions.

HOW IT IS REACHED
    Nature's Briefing arrives by email, which Metis cannot read. But every
    Mailchimp campaign has a public web archive, and the list exposes an RSS feed
    of them:

        https://us17.campaign-archive.com/feed?u=<user>&id=<list>

    Found 2026-08-27 by reading the page source of one briefing the researcher pasted in.
    Nothing is scraped from behind a login and no account is used: this is the
    same archive URL printed in the footer of every issue.

    ONE FEED CARRIES THEM ALL — Daily, AI & Robotics, Translational Research,
    Anthropocene, Cancer, and the translated editions. They are told apart by the
    masthead image's alt text, which is the only reliable marker: the FOOTER of
    every issue advertises every other briefing, so searching the body for "AI &
    Robotics" matches all of them. That mistake is worth recording because the
    result looks plausible — every edition classified as AI.
"""
from __future__ import annotations

import hashlib
import html as _html
import re
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

FEED = ("https://us17.campaign-archive.com/feed"
        "?u=2c6057c528fdc6f73fa196d9d&id=b27a691814")

# masthead alt text → (slug, display name). Order matters: the longer, more
# specific names must be tested before the bare "Nature Briefing".
KINDS: list[tuple[str, str, str]] = [
    ("Nature Briefing: AI & Robotics",          "nature-ai",     "Nature Briefing · AI & Robotics"),
    ("Nature Briefing: Translational Research", "nature-transl", "Nature Briefing · Translational Research"),
    ("Nature Briefing: Anthropocene",           "nature-anthro", "Nature Briefing · Anthropocene"),
    ("Nature Briefing: Cancer",                 "nature-cancer", "Nature Briefing · Cancer"),
    ("Nature Briefing: Microbiology",           "nature-micro",  "Nature Briefing · Microbiology"),
    ("Nature Briefing",                         "nature-daily",  "Nature Briefing · Daily"),
]

# The two the researcher asked for. The others are ingested and simply not surfaced, so
# turning one on later is a template change rather than a re-scan.
SURFACED = ("nature-daily", "nature-ai")

_DDL_EDITION = """
CREATE TABLE IF NOT EXISTS briefing_edition (
    edition_id   TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    lang         TEXT DEFAULT 'en',
    title        TEXT NOT NULL,
    published_at TEXT NOT NULL,
    url          TEXT DEFAULT '',
    n_items      INTEGER DEFAULT 0,
    fetched_at   TEXT NOT NULL
)
"""
_DDL_ITEM = """
CREATE TABLE IF NOT EXISTS briefing_item (
    item_id     TEXT PRIMARY KEY,
    edition_id  TEXT NOT NULL,
    ord         INTEGER DEFAULT 0,
    headline    TEXT NOT NULL,
    blurb       TEXT DEFAULT '',
    url         TEXT DEFAULT '',
    source      TEXT DEFAULT ''
)
"""


def ensure_schema(con) -> None:
    con.execute(_DDL_EDITION)
    con.execute(_DDL_ITEM)
    con.execute("CREATE INDEX IF NOT EXISTS idx_edition_kind "
                "ON briefing_edition(kind, published_at DESC)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_item_edition "
                "ON briefing_item(edition_id, ord)")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def classify(body: str) -> tuple[str, str]:
    """Which briefing is this? Read the MASTHEAD, never the body.

    Every issue's footer lists every other Nature Briefing as a sign-up link, so
    a body search matches all of them at once and returns whichever was checked
    first. The masthead image's alt text is the one place the edition names
    itself.
    """
    for alt in re.findall(r'alt="([^"]{4,80})"', body)[:6]:
        alt = _html.unescape(alt).strip()
        for needle, slug, name in KINDS:
            if alt.lower().startswith(needle.lower()):
                return slug, name
    return "nature-other", "Nature Briefing"


def _text(fragment: str) -> str:
    """Tags out, entities in, whitespace collapsed.

    CDATA is stripped FIRST. `<[^>]+>` treats `<![CDATA[` as an unterminated tag
    and eats everything up to the next `>` — which is usually deep inside the
    content, so every RSS title came back empty. Silent, and it looks like the
    feed simply has no titles.
    """
    t = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", fragment, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


def _is_latin(text: str) -> bool:
    """Is this edition in a Latin script?

    Nature publishes translated editions on the SAME list — the Arabic Briefing
    arrives beside the English one. It IS the daily briefing, so classifying it
    as such is right; putting it in a panel the researcher reads in English is not. The
    language is recorded and the surface filters, rather than the ingest
    throwing away an edition somebody might want.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    sample = letters[:400]
    return sum(1 for c in sample if c.isascii()) / len(sample) > 0.5


def extract_items(body: str, limit: int = 14) -> list[dict]:
    """The stories in one edition, in the order the editor put them.

    Mailchimp templates are table soup, so this reads STRUCTURE rather than
    classes: a story is an <h1>-<h3> that carries a link out to a real article,
    followed by prose. Anything pointing back at nature.com/briefing (the
    sign-up and manage-preferences furniture) is skipped.
    """
    out: list[dict] = []
    seen: set[str] = set()
    for m in re.finditer(r"<h[1-3][^>]*>(.*?)</h[1-3]>", body, re.S | re.I):
        head_html = m.group(1)
        link = re.search(r'href="([^"]+)"', head_html)
        headline = _text(head_html)
        if not headline or len(headline) < 12:
            continue
        url = _html.unescape(link.group(1)) if link else ""
        if "nature.com/briefing" in url or "list-manage" in url or "campaign-archive" in url:
            continue
        low = headline.lower()
        if low.startswith(("nature briefing", "read the full", "sign up",
                           "get the briefing", "jobs from")):
            continue
        key = headline[:70].lower()
        if key in seen:
            continue
        seen.add(key)
        # The prose immediately after the heading is the blurb.
        tail = body[m.end():m.end() + 2200]
        blurb = ""
        for p in re.finditer(r"<p[^>]*>(.*?)</p>", tail, re.S | re.I):
            t = _text(p.group(1))
            if len(t) > 60 and not t.lower().startswith(("reference", "read more")):
                blurb = t[:420]
                break
        source = ""
        s = re.search(r"\|\s*([A-Z][A-Za-z&'\. ]{2,38})\s*\|", tail[:900])
        if s:
            source = s.group(1).strip()
        out.append({"headline": headline[:240], "blurb": blurb, "url": url,
                    "source": source})
        if len(out) >= limit:
            break
    return out


def _iso(pubdate: str) -> str:
    try:
        d = parsedate_to_datetime(pubdate)
        if d.tzinfo:
            d = d.astimezone(timezone.utc).replace(tzinfo=None)
        return d.isoformat(timespec="seconds")
    except Exception:
        return datetime.now().isoformat(timespec="seconds")


def fetch(timeout: int = 40) -> str:
    req = urllib.request.Request(FEED, headers={"User-Agent": "Metis/1.0 (research dashboard)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def scan(xml: str | None = None) -> dict:
    """Pull the archive feed and store every edition it carries.

    Idempotent: an edition is keyed on its own archive URL, so re-running adds
    nothing. That matters because this is scheduled — a scanner that duplicates
    on every run turns a daily job into a slow-growing mess.
    """
    xml = xml if xml is not None else fetch()
    added = 0
    per_kind: dict[str, int] = {}
    with connect(paths.db) as con:
        ensure_schema(con)
        for raw in re.findall(r"<item>(.*?)</item>", xml, re.S):
            title = _text(re.search(r"<title>(.*?)</title>", raw, re.S).group(1)) \
                if re.search(r"<title>(.*?)</title>", raw, re.S) else ""
            link_m = re.search(r"<link>(.*?)</link>", raw, re.S)
            url = _html.unescape(link_m.group(1)).strip() if link_m else ""
            pub_m = re.search(r"<pubDate>(.*?)</pubDate>", raw, re.S)
            published = _iso(pub_m.group(1).strip()) if pub_m else ""
            body = _html.unescape(raw)

            kind, _name = classify(body)
            eid = "be-" + hashlib.sha1((url or title).encode()).hexdigest()[:12]

            # Two keys, because one is not enough. The archive URL is the
            # natural id, but Mailchimp re-issues a campaign under a NEW url
            # (a resend, a corrected link), and the same edition then arrives
            # twice — observed on 2026-08-21, the melanoma vaccine issue, with
            # identical timestamps and content. Kind + timestamp + title is what
            # actually identifies an edition to a reader.
            if con.execute("SELECT 1 FROM briefing_edition WHERE edition_id=?",
                           (eid,)).fetchone():
                continue
            # The DATE, not the timestamp. Mailchimp sent the 21 August daily
            # briefing twice, six seconds apart, under two archive URLs — a
            # segment split or a resend. Matching on the exact timestamp misses
            # that by design; two editions of the same briefing on the same day
            # with the same headline are the same edition to a reader, which is
            # the only definition that matters here.
            if title and con.execute(
                    "SELECT 1 FROM briefing_edition "
                    "WHERE kind=? AND substr(published_at,1,10)=? AND title=?",
                    (kind, published[:10], title[:240])).fetchone():
                continue

            items = extract_items(body)
            con.execute(
                "INSERT INTO briefing_edition (edition_id, kind, lang, title, "
                "published_at, url, n_items, fetched_at) VALUES (?,?,?,?,?,?,?,?)",
                (eid, kind,
                 "en" if _is_latin(title + " " + " ".join(
                     i["headline"] for i in items[:3])) else "other",
                 title[:240], published, url, len(items),
                 datetime.now().isoformat(timespec="seconds")))
            for i, it in enumerate(items):
                con.execute(
                    "INSERT OR IGNORE INTO briefing_item (item_id, edition_id, ord, "
                    "headline, blurb, url, source) VALUES (?,?,?,?,?,?,?)",
                    (f"{eid}-{i:02d}", eid, i, it["headline"], it["blurb"],
                     it["url"], it["source"]))
            added += 1
            per_kind[kind] = per_kind.get(kind, 0) + 1
    return {"added": added, "by_kind": per_kind}


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def editions(kind: str, limit: int = 5, lang: str = "en") -> list[dict]:
    """Editions of one briefing. English by default — see `_is_latin`."""
    sql = "SELECT * FROM briefing_edition WHERE kind=?"
    params: list = [kind]
    if lang:
        sql += " AND COALESCE(lang,'en') = ?"
        params.append(lang)
    sql += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)
    with connect(paths.db) as con:
        ensure_schema(con)
        return [dict(r) for r in con.execute(sql, tuple(params))]


def items_of(edition_id: str) -> list[dict]:
    with connect(paths.db) as con:
        ensure_schema(con)
        return [dict(r) for r in con.execute(
            "SELECT * FROM briefing_item WHERE edition_id=? ORDER BY ord",
            (edition_id,))]


def counts() -> dict:
    with connect(paths.db) as con:
        ensure_schema(con)
        return {r["kind"]: r["n"] for r in con.execute(
            "SELECT kind, COUNT(*) AS n FROM briefing_edition GROUP BY kind")}


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------
@app.tool()
async def scan_nature_briefings() -> list[TextContent]:
    """Fetch the latest Nature Briefing editions from the public archive feed."""
    try:
        r = scan()
    except Exception as e:
        return [TextContent(type="text", text=f"Could not reach the archive feed: {e}")]
    if not r["added"]:
        return [TextContent(type="text", text="Nothing new — already up to date.")]
    lines = [f"Added {r['added']} edition(s):"]
    names = {slug: name for _, slug, name in KINDS}
    for k, n in sorted(r["by_kind"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  {n}x {names.get(k, k)}")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def nature_briefing(kind: str = "nature-daily") -> list[TextContent]:
    """The latest Nature Briefing edition, as text.

    kind: nature-daily · nature-ai · nature-transl · nature-anthro · nature-cancer
    """
    eds = editions(kind, 1)
    if not eds:
        return [TextContent(type="text", text=f"No {kind} editions stored yet — "
                                              f"run scan_nature_briefings first.")]
    e = eds[0]
    out = [f"# {e['title']}", "", f"{e['published_at'][:16].replace('T', ' ')} · "
           f"<{e['url']}>", ""]
    for it in items_of(e["edition_id"]):
        out.append(f"**{it['headline']}**"
                   + (f"  _{it['source']}_" if it["source"] else ""))
        if it["blurb"]:
            out.append(f"{it['blurb']}")
        if it["url"]:
            out.append(f"<{it['url']}>")
        out.append("")
    return [TextContent(type="text", text="\n".join(out))]
