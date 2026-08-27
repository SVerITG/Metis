#!/usr/bin/env python3
"""Move hand-written empty states onto the component.

The audit found 104 templates writing their own "nothing here yet" prose while
`empty_state.html` sat used exactly once — it is a first-run HERO and what they
needed was a quiet line. Three sizes now exist in `_empty.html`; this puts the
panel-shaped ones onto the middle size.

WHAT IT DOES NOT DO. It does not rewrite the words. Each of these sentences was
written by someone who knew what that panel is for, and a codemod that
paraphrases would flatten exactly the thing worth keeping. It splits the first
sentence off as the title — because a title that is a sentence reads as a
paragraph with a big font — and leaves the rest as the body, verbatim.

    python3 tools/migrate_empty_states.py --check
    python3 tools/migrate_empty_states.py --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "system" / "app-py" / "templates"

PANEL_EMPTY = re.compile(
    r'<div class="panel[^"]*"[^>]*>\s*<(p|div)[^>]*>\s*([^<{]{10,300}?)\s*</\1>\s*</div>',
    re.S)
STARTS_EMPTY = re.compile(r"^(No |None|Nothing|Not yet)", re.I)

IMPORT = '{% from "partials/_empty.html" import panel as empty_panel %}'


def split(text: str) -> tuple[str, str]:
    """First sentence becomes the title; the rest is the body.

    A title that is a whole sentence reads as a paragraph in a bigger font, and
    a body with no title has nothing for the eye to land on. The split is where
    the author already put a full stop.
    """
    text = re.sub(r"\s+", " ", text).strip()
    m = re.match(r"(.+?[.!?])\s+(.+)$", text)
    if m and len(m.group(1)) <= 90:
        return m.group(1).rstrip(" ."), m.group(2)
    return text.rstrip(" ."), ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not (a.apply or a.check):
        ap.error("pass --check or --apply")

    n = 0
    for f in sorted(TPL.rglob("*.html")):
        src = f.read_text(encoding="utf-8")
        out = src
        for m in PANEL_EMPTY.finditer(src):
            body_text = m.group(2)
            if not STARTS_EMPTY.match(body_text.strip()):
                continue
            title, body = split(body_text)
            call = (f'{{{{ empty_panel("{title}", "{body}") }}}}' if body
                    else f'{{{{ empty_panel("{title}") }}}}')
            if '"' in title or '"' in body:
                print(f"   SKIP {f.name}: quotes in the prose — needs a human")
                continue
            out = out.replace(m.group(0), call, 1)
            n += 1
            print(f"   {f.name:32s} {title[:52]}")
        if out != src:
            if IMPORT not in out:
                out = IMPORT + "\n" + out
            if a.apply:
                f.write_text(out, encoding="utf-8")

    print(f"\n{'APPLIED' if a.apply else 'DRY RUN'} — {n} empty states on the component")
    return 0


if __name__ == "__main__":
    sys.exit(main())
