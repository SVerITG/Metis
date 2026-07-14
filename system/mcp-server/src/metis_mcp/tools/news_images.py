"""news_images.py — find a thumbnail for a news item.

WHY
    The news surface had no images at all, so every story looked identical and
    nothing invited a click. A news page without pictures is a list of links; the
    picture is what makes a front page a front page.

WHERE IMAGES ACTUALLY COME FROM
    Measured against the real feeds (2026-07-14):
      · BBC / Guardian / most news RSS  → carry <media:thumbnail> or
        <media:content>. Free, instant, no extra request.
      · Nature / Lancet / most journal RSS → carry NOTHING. The image only exists
        as an <meta property="og:image"> on the article page, so it costs one
        HTTP fetch.

    So: take it from the feed when it is there (free), and fall back to a single
    cheap og:image scrape when it is not. Cache the result — including the
    failures, so a feed that will never have an image is not re-fetched daily.

DELIBERATE LIMITS
    · Only ever fetches the ARTICLE URL we already stored — no user-supplied URLs,
      so this adds no SSRF surface.
    · Hard 4s timeout, capped read, HEAD-like early exit. A slow news site must
      never stall the scan.
    · Never raises. No thumbnail is a cosmetic problem; a crashed scan is not.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

log = logging.getLogger("metis.news")

# og:image / twitter:image, tolerant of attribute order.
_OG_RE = re.compile(
    rb'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)(?::src)?["\'][^>]*>',
    re.IGNORECASE,
)
_CONTENT_RE = re.compile(rb'content=["\']([^"\']+)["\']', re.IGNORECASE)

_TIMEOUT = 4.0
_MAX_BYTES = 200_000  # og:image lives in <head>; never read a whole article


def image_from_entry(entry: Any) -> str | None:
    """Pull a thumbnail straight out of the parsed feed entry. Free — no request."""
    try:
        for key in ("media_thumbnail", "media_content"):
            media = entry.get(key) if hasattr(entry, "get") else None
            if media:
                url = (media[0] or {}).get("url")
                if url and url.startswith("http"):
                    return url

        # Some feeds attach the image as an enclosure link.
        for link in (entry.get("links") or []):
            if "image" in (link.get("type") or "") and link.get("href", "").startswith("http"):
                return link["href"]

        # Others inline it in the HTML summary.
        html = entry.get("summary") or ""
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if m and m.group(1).startswith("http"):
            return m.group(1)
    except Exception as exc:  # never break a scan over a picture
        log.debug("news image: entry parse failed: %s", exc)
    return None


def image_from_page(url: str) -> str | None:
    """Fetch the article and read its og:image. One request, hard-capped.

    Only called for the article URL already in the feed — never a user-supplied
    one, so this introduces no new SSRF surface.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        import httpx

        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            with client.stream("GET", url, headers={"User-Agent": "Metis/1.0"}) as resp:
                if resp.status_code != 200:
                    return None
                if "html" not in resp.headers.get("content-type", ""):
                    return None
                buf = b""
                for chunk in resp.iter_bytes(16_384):
                    buf += chunk
                    if b"</head>" in buf or len(buf) >= _MAX_BYTES:
                        break

        tag = _OG_RE.search(buf)
        if not tag:
            return None
        content = _CONTENT_RE.search(tag.group(0))
        if not content:
            return None
        img = content.group(1).decode("utf-8", "ignore").strip()
        return img if img.startswith("http") else None
    except Exception as exc:
        log.debug("news image: og:image fetch failed for %s (%s)", url[:60], exc)
        return None


def resolve_image(entry: Any, url: str, conn: sqlite3.Connection | None = None) -> str | None:
    """The one call the scanner makes: feed first, page second, cache always.

    Returns "" (not None) when we looked and there is genuinely no image, so the
    cache can distinguish "never tried" from "tried, nothing there" and stop
    re-fetching a journal feed that will never carry pictures.
    """
    img = image_from_entry(entry)
    if img:
        return img

    if conn is not None:
        try:
            row = conn.execute(
                "SELECT image_url FROM news_image_cache WHERE source_url = ?", (url,)
            ).fetchone()
            if row is not None:
                return row[0] or None  # "" → we already looked; don't fetch again
        except sqlite3.DatabaseError:
            pass  # cache table not created yet — fall through and fetch

    img = image_from_page(url)

    if conn is not None:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO news_image_cache (source_url, image_url) VALUES (?, ?)",
                (url, img or ""),
            )
        except sqlite3.DatabaseError as exc:
            log.debug("news image: could not cache result: %s", exc)

    return img


DDL = """
CREATE TABLE IF NOT EXISTS news_image_cache (
    source_url TEXT PRIMARY KEY,
    image_url  TEXT           -- '' means: looked, none found. Don't re-fetch.
)
"""
