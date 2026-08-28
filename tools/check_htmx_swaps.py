#!/usr/bin/env python3
"""Check that every HTMX swap puts back what it took away.

WHY THIS EXISTS
    Two bugs found on 2026-08-27/28, both invisible to the 456-test suite, a
    byte-count audit and a rendered-text snapshot, because in every one of them
    the TEXT was correct and only its wrapper was wrong:

      · /meetings — the template had
            <h2 class="sec-label" hx-get="…/next-label" hx-swap="outerHTML">
        and the route returned only `<span>Next meeting</span><span…>`. outerHTML
        replaces the ELEMENT, so the <h2> and its class vanished on load and the
        section rendered as unstyled body text: "Next meetingNONE SCHEDULED".

      · /knowledge — the read/unread control was authored twice, once in
        knowledge_library_table.html and once in routers/knowledge.py. They
        drifted. The page looked right until you clicked, at which point the
        button was replaced by the router's older styling.

    Both are the same mistake: an element that exists in two places, where only
    one of them is exercised by a first-paint test.

WHAT IT CHECKS
    outerHTML swaps  the root element the route returns must have the same tag
                     and the same classes as the element it replaces.
    innerHTML swaps  no heading may sit inside the swap target, because HTMX
                     empties it — the heading renders for one frame and is then
                     gone for good, which looks like a panel that was never
                     given a title.
    self-retrigger   an outerHTML response must not carry hx-trigger="load",
                     or it requests itself forever.

USAGE
    python3 tools/check_htmx_swaps.py            # needs the dashboard running
    python3 tools/check_htmx_swaps.py --port 8080
Exit 0 = clean.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "system" / "app-py" / "templates"

OPEN_TAG = re.compile(r'<(?P<tag>[a-zA-Z][\w-]*)\b(?P<attrs>[^>]*)>')
DIV_TAG = re.compile(r'<(/?)div\b[^>]*>', re.I)


def attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{name}="([^"]*)"', attrs)
    return m.group(1) if m else None


def classes(attrs: str) -> set[str]:
    """Static class tokens only — a {{ jinja }} expression is not comparable."""
    c = attr(attrs, "class") or ""
    return {t for t in c.split() if "{" not in t and "}" not in t}


def inner_of(src: str, open_end: int) -> str:
    """Body of a <div> whose opening tag ends at open_end."""
    depth = 1
    for m in DIV_TAG.finditer(src, open_end):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return src[open_end:m.start()]
    return src[open_end:]


def fetch(base: str, path: str) -> str | None:
    """Fetch as HTMX would. Without the HX-Request header several routes return
    a whole page (correctly — that is the no-JS fallback), and comparing a full
    document against a fragment reports a bug that does not exist."""
    req = urllib.request.Request(base + path, headers={
        "HX-Request": "true", "HX-Boosted": "false",
        "Accept": "text/html,*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


# Leading <style>, <script>, <datalist>, <template> and comments are preamble,
# not the element being swapped in. Skip them to find the real root.
PREAMBLE = ("style", "script", "datalist", "template", "link", "meta")


def root_element(html: str):
    pos = 0
    while True:
        html_l = html[pos:].lstrip()
        pos = len(html) - len(html_l)
        if html_l.startswith("<!--"):
            end = html.find("-->", pos)
            if end == -1:
                return None
            pos = end + 3
            continue
        m = OPEN_TAG.match(html, pos)
        if m is None:
            return None
        tag = m.group("tag").lower()
        if tag not in PREAMBLE:
            return m
        close = re.search(rf'</{tag}\s*>', html[m.end():], re.I)
        if close is None:
            return None
        pos = m.end() + close.end()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="8080")
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}"

    if fetch(base, "/health") is None:
        print(f"dashboard not answering on {base} — start it first", file=sys.stderr)
        return 2

    problems: list[str] = []
    checked = 0

    for f in sorted(TPL.rglob("*.html")):
        src = f.read_text(encoding="utf-8", errors="replace")
        rel = str(f.relative_to(TPL))
        for m in OPEN_TAG.finditer(src):
            attrs = m.group("attrs")
            url = attr(attrs, "hx-get")
            if not url or "{" in url:
                continue                      # computed URL: cannot fetch it
            swap = attr(attrs, "hx-swap") or "innerHTML"
            tag = m.group("tag").lower()

            # hx-target redirects the swap at another element entirely, so this
            # element is NOT the thing being replaced and nothing about it can
            # be lost. Ignoring this was the single biggest source of false
            # positives on the first run: every <button> that loads a panel
            # elsewhere was reported as losing its own classes.
            if attr(attrs, "hx-target"):
                continue

            # ── innerHTML: a heading inside the target is destroyed on load ──
            if swap == "innerHTML":
                if tag != "div":
                    continue
                body = inner_of(src, m.end())
                if re.search(r'<h[1-6]\b', body) or "sec_label(" in body:
                    served = fetch(base, url) or ""
                    # only a problem if the partial does NOT supply its own
                    if not (re.search(r'<h[1-6]\b', served) or 'class="sec-label' in served):
                        problems.append(
                            f"{rel}: heading sits inside the innerHTML swap target "
                            f"{url} and is destroyed on load (partial supplies none)")
                        checked += 1
                continue

            if swap != "outerHTML":
                continue

            served = fetch(base, url)
            checked += 1
            if served is None:
                problems.append(f"{rel}: {url} did not respond")
                continue
            if not served.strip():
                # An EMPTY body is a legitimate outerHTML response: it deletes
                # the element. That is how the demo / welcome / api-key banners
                # remove themselves when there is nothing to announce.
                continue
            root = root_element(served)
            if root is None:
                problems.append(
                    f"{rel}: {url} returned no element, but hx-swap=outerHTML "
                    f"replaces a <{tag}> — its wrapper and classes are lost")
                continue

            want, got = classes(attrs), classes(root.group("attrs"))
            lost = want - got - {"skeleton"}
            if root.group("tag").lower() != tag:
                problems.append(
                    f"{rel}: {url} returns <{root.group('tag').lower()}> but replaces "
                    f"<{tag}>")
            elif lost:
                problems.append(
                    f"{rel}: {url} drops class(es) {' '.join(sorted(lost))} from the "
                    f"<{tag}> it replaces")
            if 'hx-trigger="load"' in root.group("attrs") and attr(attrs, "hx-trigger") == "load":
                problems.append(
                    f"{rel}: {url} returns an element that re-triggers itself on load")

    print(f"checked {checked} HTMX swap sites")
    for p in problems:
        print(f"  ✗ {p}")
    if not problems:
        print("  ✓ every swap returns what it replaced")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
