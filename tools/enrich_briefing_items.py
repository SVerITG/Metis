#!/usr/bin/env python3
"""Fetch each briefing article's own picture and short description.

WHY THIS EXISTS. The Nature Briefing e-mail carries neither. Its `blurb` is
Nature's summary cut at a hard 420 characters — every stored one ends mid-word —
and there is no image field at all: those rows were the only ones of 4,170 in
the news table with no picture. Asked for both on 2026-09-04, so this reads the
article's own `og:image` and `og:description`, which is what a publisher puts
there for exactly this purpose: a clean one-sentence description and a
representative image.

WHAT IT WILL NOT DO. It does not store article text. A briefing is a digest of
other people's writing; the full article belongs to the publisher and the
headline links to it. `og:description` is the publisher's own summary, offered
for reuse.

HOW IT BEHAVES, and each of these is deliberate:

  * IDEMPOTENT. An item with `enriched_at` set is skipped unless --force. Run it
    after every scan; it only ever fetches what it has not tried.
  * IT RECORDS FAILURES. `enrich_note` says why — several publishers answer a
    scripted request with 403, and a silent blank is indistinguishable from an
    article that genuinely has no picture.
  * POLITE. One request at a time, a real timeout, a delay between hosts, and it
    reads at most 400 KB of any page. Nothing is retried in a loop.
  * IT VERIFIES THE IMAGE. An `og:image` URL that does not resolve is worse than
    none: it renders as a broken tile. Each candidate is HEAD-checked and kept
    only if it answers and claims an image content-type.

Usage:
    python3 tools/enrich_briefing_items.py            # what it would do
    python3 tools/enrich_briefing_items.py --apply
    python3 tools/enrich_briefing_items.py --apply --limit 10
    python3 tools/enrich_briefing_items.py --apply --force   # re-fetch everything
"""
from __future__ import annotations

import argparse
import gzip
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from html import unescape
from urllib.parse import urlparse

DB = os.path.expanduser("~/.local/share/metis/metis.sqlite")
UA = ("Mozilla/5.0 (compatible; MetisResearchCortex/1.0; "
      "personal research dashboard; +local)")
PAGE_CAP = 400_000          # bytes of HTML to read; og tags live in the <head>
TIMEOUT = 20
PER_HOST_DELAY = 1.5        # seconds between requests to the same host


def _get(url: str, method: str = "GET"):
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Encoding": "gzip",
        "Accept-Language": "en",
    })
    return urllib.request.urlopen(req, timeout=TIMEOUT)


def _meta(html: str, *names: str) -> str:
    """A meta tag's content, with the attributes in either order.

    Both orders occur in the wild and matching only one silently misses half of
    them, which reads as "this publisher provides no description".
    """
    for n in names:
        e = re.escape(n)
        for pat in (rf'<meta[^>]+(?:property|name)=["\']{e}["\'][^>]*?content=["\']([^"\']*)',
                    rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*?(?:property|name)=["\']{e}["\']'):
            m = re.search(pat, html, re.I)
            if m and m.group(1).strip():
                return unescape(m.group(1)).strip()
    return ""


def _image_resolves(url: str) -> bool:
    """A broken picture is worse than no picture, so check before storing."""
    if not url.startswith("http"):
        return False
    try:
        r = _get(url, "HEAD")
        ct = (r.headers.get("Content-Type") or "").lower()
        return r.getcode() == 200 and ("image" in ct or ct == "")
    except Exception:
        # Some CDNs refuse HEAD. Fall back to a ranged GET of a few bytes.
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-256"})
            r = urllib.request.urlopen(req, timeout=TIMEOUT)
            return r.getcode() in (200, 206) and "image" in (r.headers.get("Content-Type") or "").lower()
        except Exception:
            return False


def enrich_one(url: str) -> tuple[str, str, str]:
    """(image_url, description, note). A note means it did not fully work."""
    try:
        r = _get(url)
        raw = r.read(PAGE_CAP)
        if (r.headers.get("Content-Encoding") or "") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass                      # a truncated gzip stream; use what decoded
    except urllib.error.HTTPError as e:
        return "", "", f"HTTP {e.code}"
    except Exception as e:
        return "", "", type(e).__name__

    html = raw.decode("utf-8", "replace")
    img = _meta(html, "og:image", "og:image:secure_url", "twitter:image", "twitter:image:src")
    desc = _meta(html, "og:description", "twitter:description", "description")
    note = ""
    if img and not _image_resolves(img):
        note = "image did not resolve"
        img = ""
    if not img and not desc:
        note = note or "no og tags"
    return img, desc, note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write to the database")
    ap.add_argument("--force", action="store_true", help="re-fetch already-tried items")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    where = "COALESCE(url,'') LIKE 'http%'"
    if not a.force:
        where += " AND COALESCE(enriched_at,'') = ''"
    rows = list(con.execute(
        f"SELECT item_id, headline, url FROM briefing_item WHERE {where} ORDER BY ord"))
    if a.limit:
        rows = rows[:a.limit]

    total_with_url = con.execute(
        "SELECT COUNT(*) FROM briefing_item WHERE COALESCE(url,'') LIKE 'http%'").fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM briefing_item").fetchone()[0]
    print(f"{len(rows)} to fetch · {total_with_url} of {total} items have a link "
          f"({total - total_with_url} carry none, and cannot be enriched)")
    if not a.apply:
        print("DRY RUN — nothing written. Re-run with --apply.\n")

    last_host: dict[str, float] = {}
    got_img = got_desc = failed = 0
    for i, r in enumerate(rows, 1):
        host = urlparse(r["url"]).netloc
        wait = PER_HOST_DELAY - (time.monotonic() - last_host.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        last_host[host] = time.monotonic()

        img, desc, note = enrich_one(r["url"])
        got_img += bool(img)
        got_desc += bool(desc)
        failed += bool(note)
        flag = "img+desc" if (img and desc) else "desc" if desc else "img" if img else "—"
        print(f"  [{i:>2}/{len(rows)}] {flag:<8} {note[:22]:<24} {r['headline'][:44]}")

        if a.apply:
            con.execute(
                "UPDATE briefing_item SET image_url=?, description=?, "
                "enriched_at=datetime('now'), enrich_note=? WHERE item_id=?",
                (img, desc, note, r["item_id"]))
            con.commit()

    print(f"\n{got_img} pictures · {got_desc} descriptions · {failed} with a note")
    if a.apply:
        n = con.execute("SELECT COUNT(*) FROM briefing_item "
                        "WHERE COALESCE(image_url,'') != ''").fetchone()[0]
        d = con.execute("SELECT COUNT(*) FROM briefing_item "
                        "WHERE COALESCE(description,'') != ''").fetchone()[0]
        print(f"stored: {n} items now carry a picture, {d} a description")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
