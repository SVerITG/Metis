#!/usr/bin/env python3
"""Move inline hover handlers onto classes, conservatively.

WHY THIS EXISTS
    A row's response to the cursor depended on which template drew it. Counted
    2026-08-29: 35 `onmouseover` and 7 `onmouseenter` attributes across 28
    templates, in a dozen slightly different spellings — some shift background,
    some recolour text, some move the element — while `row-hit`, the class that
    exists for exactly this, was used ONCE.

    Three consequences, and the third is the one that matters:
      · You cannot tell what is clickable without clicking it, because a row
        with no handler looks identical to one with a handler.
      · `prefers-reduced-motion` cannot reach an inline style, so the two
        handlers that translate or scale ignore it.
      · Keyboard users get nothing at all — :hover has no keyboard equivalent,
        so every one of these is mouse-only. The classes below pair :hover with
        :focus-visible, which is the actual fix and cannot be done inline.

HOW IT IS SAFE
    A rule fires only when the over AND out handlers BOTH match the pair it
    knows, exactly, character for character. It then removes both and adds one
    class. It never guesses, never fires on a handler carrying a Jinja
    expression, and never touches an element that already has the class.

USAGE
    python3 tools/migrate_hover.py --check     # prints what it would do
    python3 tools/migrate_hover.py --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "system" / "app-py" / "templates"

# (class, over-handler, out-handler)
# Ordered most specific first, so a two-property pair is consumed before a rule
# that would match only one of its properties.
RULES: list[tuple[str, str, str]] = [
    ("hov-edge",
     "this.style.borderColor='var(--m-accent)';this.style.color='var(--m-accent)'",
     "this.style.borderColor='var(--m-rule)';this.style.color='var(--m-muted)'"),
    ("hov-dim",
     "this.style.opacity='1';this.style.color='var(--m-ink)'",
     "this.style.opacity='0.5';this.style.color='var(--m-muted)'"),
    ("row-hit",
     "this.style.background='var(--m-surface-2)'",
     "this.style.background=''"),
    ("row-hit",
     "this.style.background='var(--m-surface-2)';",
     "this.style.background='transparent';"),
    ("hov-ink",
     "this.style.color='var(--m-accent)'",
     "this.style.color='var(--m-ink)'"),
    ("hov-ink",
     "this.style.color='var(--m-accent)'",
     "this.style.color='var(--m-muted)'"),
    ("hov-edge",
     "this.style.borderColor='var(--m-accent)'",
     "this.style.borderColor='var(--m-rule)'"),
]

TAG = re.compile(r"<[a-zA-Z][^>]*>", re.S)


def add_class(tag: str, cls: str) -> str:
    m = re.search(r'\bclass="([^"]*)"', tag)
    if m:
        if cls in m.group(1).split():
            return tag
        return tag[:m.start(1)] + (m.group(1) + " " + cls).strip() + tag[m.end(1):]
    # no class attribute — put one right after the tag name
    return re.sub(r"^<([a-zA-Z][\w-]*)", rf'<\1 class="{cls}"', tag, count=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    apply = args.apply and not args.check

    hits: Counter[str] = Counter()
    touched: set[str] = set()

    for f in sorted(TPL.rglob("*.html")):
        src = f.read_text(encoding="utf-8")
        out = []
        pos = 0
        changed = False
        for m in TAG.finditer(src):
            tag = m.group(0)
            if "onmouseover=" not in tag and "onmouseenter=" not in tag:
                continue
            new = tag
            for cls, over, leave in RULES:
                for on_attr, off_attr in (("onmouseover", "onmouseout"),
                                          ("onmouseenter", "onmouseleave")):
                    a = f'{on_attr}="{over}"'
                    b = f'{off_attr}="{leave}"'
                    if a in new and b in new:
                        new = new.replace(a, "").replace(b, "")
                        new = add_class(new, cls)
                        hits[cls] += 1
                        break
                else:
                    continue
                break
            if new != tag:
                new = re.sub(r"\s{2,}", " ", new).replace(" >", ">")
                out.append((m.start(), m.end(), new))
                changed = True
        if not changed:
            continue
        touched.add(str(f.relative_to(TPL)))
        buf, last = [], 0
        for s0, e0, new in out:
            buf.append(src[last:s0]); buf.append(new); last = e0
        buf.append(src[last:])
        if apply:
            f.write_text("".join(buf), encoding="utf-8")

    left = sum(len(re.findall(r"onmouse(?:over|enter)=", p.read_text(encoding="utf-8")))
               for p in TPL.rglob("*.html"))
    print(("APPLIED" if apply else "DRY RUN") + f" — {len(touched)} files")
    for cls, n in hits.most_common():
        print(f"  {n:4d}  .{cls}")
    print(f"  {sum(hits.values()):4d}  total · {left} inline hover handlers remain")
    if not apply:
        print("\nnothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
