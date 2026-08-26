#!/usr/bin/env python3
"""Close the accessibility defects the design audit turned up.

Found 2026-08-26, after the inline-style count reached its honest floor. The
remaining attributes were mostly single declarations already written in the
design language — which is the system being used, not entropy. So the question
became what is actually WRONG, and the answer was not cosmetic:

    52  outline:none with no replacement   keyboard focus made invisible
    96  <input> with no label              a placeholder is not a label
    44  clickable <div> with no keyboard   mouse-only controls
     5  a coloured dot with no text        colour as the only signal
     2  target=_blank with no rel          window.opener handed to the target

WHAT THIS TOOL DOES NOT DO. It does not invent labels. Where an input has a
placeholder, that text is the author's own description and becomes the
aria-label; where it has none, the input is REPORTED and left alone, because a
made-up label is worse than a missing one — it lies confidently.

    python3 tools/fix_accessibility.py --check
    python3 tools/fix_accessibility.py --apply
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "system" / "app-py" / "templates"

JINJA = re.compile(r"\{\{|\{%")


def fix_outline(s: str, stats: Counter) -> str:
    """Remove inline `outline:none`.

    Inline `outline:none` applies ALWAYS, not only on focus, so it removes the
    ring permanently — and almost none of these had a replacement, because a
    style attribute cannot express `:focus-visible`. The stylesheet now carries
    a proper focus ring for inputs and controls; deleting the inline override is
    what lets it through.
    """
    def sub(m):
        stats["outline:none removed"] += 1
        return ""
    s = re.sub(r"outline:\s*none\s*;?", sub, s)
    # Tidy a style attribute left empty by the removal.
    return re.sub(r'\s*style="\s*"', "", s)


def fix_input_labels(s: str, stats: Counter, report: list, name: str) -> str:
    """Give an unlabelled input the aria-label its placeholder already implies."""
    def sub(m):
        tag = m.group(0)
        if re.search(r'type="(hidden|submit|button|checkbox|radio)"', tag):
            return tag
        if "aria-label" in tag or "aria-labelledby" in tag:
            return tag
        idm = re.search(r'id="([^"]+)"', tag)
        if idm and f'for="{idm.group(1)}"' in s:
            return tag
        ph = re.search(r'placeholder="([^"]+)"', tag)
        if not ph:
            report.append(f"{name}: input with no placeholder to borrow — {tag[:60]}")
            return tag
        label = ph.group(1)
        if JINJA.search(label):
            # A computed placeholder cannot become a static label; the value is
            # only known at render. Point the label at the same expression.
            stats["aria-label from computed placeholder"] += 1
        else:
            label = html.unescape(label).rstrip("… .")
            stats["aria-label from placeholder"] += 1
        return tag[:-1].rstrip() + f' aria-label="{label}">'
    return re.sub(r"<input\b[^>]*>", sub, s)


def fix_clickable(s: str, stats: Counter) -> str:
    """Give a clickable div a keyboard path.

    `role="button"` and `tabindex="0"` make it focusable and announce it
    correctly; the Enter/Space handling is delegated once in app.js rather than
    written onto forty-four elements.
    """
    def sub(m):
        tag = m.group(0)
        if "tabindex" in tag or 'role="' in tag:
            return tag
        stats["clickable div made reachable"] += 1
        return tag[:-1].rstrip() + ' role="button" tabindex="0">'
    return re.sub(r"<(?:div|span)\b[^>]*\bonclick=[^>]*>", sub, s)


def fix_blank_rel(s: str, stats: Counter) -> str:
    def sub(m):
        stats['rel="noopener" added'] += 1
        return m.group(0)[:-1].rstrip() + ' rel="noopener">'
    return re.sub(r'<a\b[^>]*target="_blank"(?![^>]*rel=)[^>]*>', sub, s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not (a.apply or a.check):
        ap.error("pass --check or --apply")

    stats: Counter = Counter()
    report: list[str] = []
    touched = 0
    for f in sorted(TPL.rglob("*.html")):
        src = f.read_text(encoding="utf-8")
        out = fix_outline(src, stats)
        out = fix_input_labels(out, stats, report, f.name)
        out = fix_clickable(out, stats)
        out = fix_blank_rel(out, stats)
        if out != src:
            touched += 1
            if a.apply:
                f.write_text(out, encoding="utf-8")

    print(f"{'APPLIED' if a.apply else 'DRY RUN'} — {touched} files\n")
    for k, n in stats.most_common():
        print(f"   {n:4d}  {k}")
    if report:
        print(f"\n   {len(report)} left for a human — no honest label available:")
        for r in report[:10]:
            print(f"      {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
