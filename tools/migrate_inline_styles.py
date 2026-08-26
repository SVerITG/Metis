#!/usr/bin/env python3
"""Move inline styling onto the idiom classes, conservatively.

WHAT THIS IS FOR
    A design audit on 2026-08-26 counted 3,171 inline `style=` attributes across
    191 templates, carrying 12,041 hand-written declarations — 53 font sizes,
    222 paddings, 78 colours. The declarations repeat heavily (the top 50 cover
    59% of the volume) but the whole attributes do not (the top 100 cover 31%),
    so there is no find-and-replace shortcut. The repetition lives at the level
    of IDIOMS: "an uppercase label", "a row of things", "the growing column".

HOW IT IS SAFE
    Each rule names an exact set of declarations and the class that reproduces
    them. A rule fires only when EVERY declaration in its set is present in the
    attribute; it then removes exactly those and adds the class, leaving any
    other declarations inline. It never guesses, never reorders, and never
    touches an attribute it does not fully understand.

    Three things it will not do:
      · fire inside a Jinja expression, where `style="{{ ... }}"` is computed
      · fire on an element that already carries the class
      · remove a declaration whose value differs by so much as a space

    Run with --check first. It prints what it would do and changes nothing.

USAGE
    python3 tools/migrate_inline_styles.py --check
    python3 tools/migrate_inline_styles.py --apply [--only today_]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "system" / "app-py" / "templates"

# ── The rules ──────────────────────────────────────────────────────────────
# (class, {declarations it reproduces exactly})
#
# Ordered most-specific first: a rule that consumes four declarations must get
# the chance before one that consumes a subset of them, or the specific match
# is destroyed by the general one.
RULES: list[tuple[str, set[str]]] = [
    # ── the uppercase label, in its common spellings ──
    ("u-label u-label--wide", {
        "font-family:var(--m-mono)", "font-size:11px",
        "letter-spacing:0.14em", "text-transform:uppercase",
        "color:var(--m-muted)"}),
    ("u-label u-label--wide", {
        "font-family:var(--m-mono)", "font-size:11px",
        "letter-spacing:0.12em", "text-transform:uppercase",
        "color:var(--m-muted)"}),
    ("u-label u-label--wide", {
        "font-family:var(--m-mono)", "font-size:11px",
        "letter-spacing:0.1em", "text-transform:uppercase",
        "color:var(--m-muted)"}),
    ("u-label", {"font-family:var(--m-mono)", "font-size:11px",
                 "letter-spacing:0.12em", "color:var(--m-muted)"}),
    ("u-label", {"font-family:var(--m-mono)", "font-size:11px",
                 "letter-spacing:0.1em", "color:var(--m-muted)"}),
    ("u-label", {"font-family:var(--m-mono)", "font-size:11px",
                 "letter-spacing:0.14em", "color:var(--m-muted)"}),
    ("u-label", {"font-family:var(--m-mono)", "font-size:11px",
                 "color:var(--m-muted)"}),
    ("u-label u-label--accent", {"font-family:var(--m-mono)", "font-size:11px",
                                 "color:var(--m-accent)"}),

    # ── rows ──
    ("u-row u-row--wrap", {"display:flex", "align-items:center",
                           "flex-wrap:wrap", "gap:8px"}),
    ("u-row u-row--between", {"display:flex", "align-items:center",
                              "justify-content:space-between"}),
    ("u-row u-row--top", {"display:flex", "align-items:flex-start", "gap:8px"}),
    ("u-row u-row--base", {"display:flex", "align-items:baseline", "gap:8px"}),
    ("u-row", {"display:flex", "align-items:center", "gap:8px"}),
    ("u-row", {"display:flex", "align-items:center", "gap:6px"}),
    ("u-row u-row--wrap", {"display:flex", "align-items:center", "flex-wrap:wrap"}),
    ("u-row", {"display:flex", "align-items:center"}),
    ("u-col", {"display:flex", "flex-direction:column", "gap:8px"}),
    ("u-col", {"display:flex", "flex-direction:column"}),

    # ── the growing column ──
    ("u-grow", {"flex:1", "min-width:0"}),
    ("u-grow", {"flex:1"}),
    ("u-fixed", {"flex-shrink:0"}),

    # ── stack spacing, snapped to the scale ──
    ("u-mb-1", {"margin-bottom:4px"}),
    ("u-mb-2", {"margin-bottom:6px"}),
    ("u-mb-2", {"margin-bottom:8px"}),
    ("u-mb-3", {"margin-bottom:10px"}),
    ("u-mb-3", {"margin-bottom:12px"}),
    ("u-mb-4", {"margin-bottom:14px"}),
    ("u-mb-4", {"margin-bottom:16px"}),
    ("u-mb-4", {"margin-bottom:18px"}),
    ("u-mb-5", {"margin-bottom:20px"}),
    ("u-mb-5", {"margin-bottom:22px"}),
    ("u-mb-5", {"margin-bottom:24px"}),
    ("u-mb-6", {"margin-bottom:28px"}),
    ("u-mb-6", {"margin-bottom:30px"}),
    ("u-mb-6", {"margin-bottom:32px"}),

    # ── separators ──
    ("u-rule", {"border-bottom:1px solid var(--m-rule-soft)"}),
    ("u-rule-t", {"border-top:1px solid var(--m-rule-soft)"}),

    # ── editorial voice ──
    ("u-ed", {"font-family:var(--m-display)", "font-style:italic",
              "color:var(--m-muted)"}),

    # ── truncation ──
    ("u-truncate", {"overflow:hidden", "text-overflow:ellipsis",
                    "white-space:nowrap"}),

    # ── hidden ──
    ("u-hide", {"display:none"}),
]

# An attribute containing a Jinja tag is computed, not literal. Never touch it.
JINJA = re.compile(r"\{\{|\{%")


def norm(decl: str) -> str:
    """Whitespace-insensitive form, so `padding: 4px` matches `padding:4px`."""
    k, _, v = decl.partition(":")
    return f"{k.strip()}:{re.sub(r'\s+', ' ', v.strip())}"


def migrate_tag(tag: str, stats: Counter) -> str:
    m = re.search(r'style="([^"]*)"', tag)
    if not m or JINJA.search(m.group(1)):
        return tag
    decls = [norm(d) for d in m.group(1).split(";") if ":" in d]
    if not decls:
        return tag
    remaining = list(decls)
    add: list[str] = []

    for cls, want in RULES:
        if want <= set(remaining):
            # Only add a class the element does not already carry.
            existing = re.search(r'class="([^"]*)"', tag)
            have = set((existing.group(1) if existing else "").split())
            if not set(cls.split()) <= have:
                add.append(cls)
                # Count only what actually CHANGES. Counting matches instead
                # made --check report 92 substitutions on a file it would not
                # touch — an element that already carries the class and still
                # has the declarations inline matches forever and moves nothing.
                # A tool whose dry run never reaches zero cannot be trusted to
                # say when it is done.
                stats[cls] += 1
            remaining = [d for d in remaining if d not in want]

    if not add:
        return tag

    # Rebuild the style attribute with whatever no rule claimed.
    if remaining:
        tag = re.sub(r'style="[^"]*"', 'style="' + ";".join(remaining) + ';"', tag)
    else:
        tag = re.sub(r'\s*style="[^"]*"', "", tag)

    new_classes = " ".join(add)
    if re.search(r'class="[^"]*"', tag):
        tag = re.sub(r'class="([^"]*)"',
                     lambda mm: f'class="{mm.group(1)} {new_classes}"'.replace("  ", " "),
                     tag, count=1)
    else:
        tag = re.sub(r"^<(\w+)", rf'<\1 class="{new_classes}"', tag, count=1)
    return tag


# ── Pass 2: snap literal values onto the scales ────────────────────────────
# A different kind of fix from the rules above. Those REMOVE a declaration by
# naming the idiom it belongs to; these keep the declaration and put its VALUE
# on the scale. That is what turns "53 distinct font sizes" into eight, and it
# reaches the 2,700 attributes too bespoke for any class.
#
# The existing scale maps almost exactly onto the most-used literals — 11/12/13
# /15px are --t-micro/meta/small/body to the pixel — which says it was derived
# from real usage and then abandoned. Snapping is restoring it, not imposing it.
#
# Values off the scale move by at most 1px, except 10px→11px and 10.5px→11px.
# That IS a visible change, and it is the intended one: a rhythm you can see
# beats a value nobody chose.
FONT_SIZE = {
    "9px": "var(--t-micro)", "9.5px": "var(--t-micro)", "10px": "var(--t-micro)",
    "10.5px": "var(--t-micro)", "11px": "var(--t-micro)", "11.5px": "var(--t-meta)",
    "12px": "var(--t-meta)", "12.5px": "var(--t-meta)",
    "13px": "var(--t-small)", "13.5px": "var(--t-small)",
    "14px": "var(--t-body)", "14.5px": "var(--t-body)", "15px": "var(--t-body)",
    "16px": "var(--t-h4)", "17px": "var(--t-h4)", "18px": "var(--t-h4)",
    "20px": "var(--t-h3)", "21px": "var(--t-h3)", "22px": "var(--t-h3)",
    "24px": "var(--t-h2)", "26px": "var(--t-h2)",
    "28px": "var(--t-h1)", "30px": "var(--t-h1)", "32px": "var(--t-h1)",
}
# Every value the templates actually use, mapped to the nearest step. The first
# version stopped at 32px and skipped the odd numbers, so `padding:18px 22px`
# never snapped — 22px was simply absent — and 76 panels kept writing raw
# pixels. A partial map is worse than none: it leaves a residue that looks like
# a deliberate exception.
SPACE = {"2px": "var(--m-space-1)", "3px": "var(--m-space-1)",
         "4px": "var(--m-space-1)", "5px": "var(--m-space-1)",
         "6px": "var(--m-space-2)", "7px": "var(--m-space-2)",
         "8px": "var(--m-space-2)", "9px": "var(--m-space-2)",
         "10px": "var(--m-space-3)", "11px": "var(--m-space-3)",
         "12px": "var(--m-space-3)", "13px": "var(--m-space-3)",
         "14px": "var(--m-space-4)", "15px": "var(--m-space-4)",
         "16px": "var(--m-space-4)", "17px": "var(--m-space-4)",
         "18px": "var(--m-space-4)", "19px": "var(--m-space-5)",
         "20px": "var(--m-space-5)", "21px": "var(--m-space-5)",
         "22px": "var(--m-space-5)", "23px": "var(--m-space-5)",
         "24px": "var(--m-space-5)", "26px": "var(--m-space-6)",
         "28px": "var(--m-space-6)", "30px": "var(--m-space-6)",
         "32px": "var(--m-space-6)", "36px": "var(--m-space-7)",
         "40px": "var(--m-space-7)", "44px": "var(--m-space-7)",
         "48px": "var(--m-space-7)", "56px": "var(--m-space-8)",
         "64px": "var(--m-space-8)"}
RADIUS = {"2px": "var(--m-radius-sm)", "3px": "var(--m-radius)",
          "4px": "var(--m-radius)", "100px": "var(--m-radius-pill)",
          "999px": "var(--m-radius-pill)", "50%": "50%"}


def _snap(decl: str, stats: Counter) -> str:
    k, _, v = decl.partition(":")
    k, v = k.strip(), v.strip()
    if k == "font-size" and v in FONT_SIZE:
        return f"{k}:{FONT_SIZE[v]}"
    if k in ("gap", "margin-bottom", "margin-top") and v in SPACE:
        return f"{k}:{SPACE[v]}"
    if k == "border-radius" and v in RADIUS and v != "50%":
        return f"{k}:{RADIUS[v]}"
    # Padding is the last and largest holdout — 222 distinct values across 863
    # uses — because it is multi-valued: "16px 20px" is two decisions in one
    # declaration. Snap each side independently and the pair lands on the grid
    # without needing a rule per combination.
    if k in ("padding", "margin") and v and "var(" not in v and "%" not in v:
        parts = v.split()
        if 1 <= len(parts) <= 4 and all(x in SPACE or x == "0" for x in parts):
            return f"{k}:" + " ".join("0" if x == "0" else SPACE[x] for x in parts)
    return decl


def snap(decl: str, stats: Counter) -> str:
    """Snap one declaration onto the scales, counting only real changes.

    Wraps `_snap`. The first version counted every declaration it RECOGNISED,
    so `margin:0` — which snaps to `margin:0` — was reported as a substitution
    92 times over. A dry run that never reaches zero cannot tell you when the
    migration is finished, which is the one question it exists to answer.
    """
    out = _snap(decl, stats)
    if out == decl:
        return decl
    stats[decl.partition(":")[0].strip() + " → scale"] += 1
    return out


def snap_tag(tag: str, stats: Counter) -> str:
    m = re.search(r'style="([^"]*)"', tag)
    if not m or JINJA.search(m.group(1)):
        return tag
    parts = [d for d in m.group(1).split(";") if d.strip()]
    out = [snap(norm(d), stats) if ":" in d else d for d in parts]
    return tag.replace(m.group(0), 'style="' + ";".join(out) + ';"')


# ── Buttons ────────────────────────────────────────────────────────────────
# Element-aware, unlike the idiom rules above: these fire only on a <button>,
# because `cursor:pointer` on a div means something different from
# `cursor:pointer` on a button, and a rule that cannot tell them apart would
# turn every clickable row into a button.
#
# The audit's revealing number was not the 62 buttons with no class — it was the
# 108 that HAVE a class and carry an inline style overriding it. That is what a
# system covering four cases looks like when the templates need seven: people
# take the nearest class and patch the difference. The variants added alongside
# this (soft, danger, sm, lg, icon) are those patches, named.
#
# `.btn` already supplies these, so an inline copy is redundant whatever the
# variant: they are stripped from any element that ends up carrying `.btn`.
BTN_BASE = {
    "display:inline-flex", "align-items:center", "cursor:pointer",
    "text-decoration:none", "font-weight:500",
    "border:1px solid transparent", "background:transparent",
    "border-radius:var(--m-radius)", "border-radius:var(--m-radius-sm)",
    "transition:background 120ms, border-color 120ms, color 120ms",
}

# (variant classes, declarations that identify AND are reproduced by it)
BTN_LOOKS = [
    ("btn btn--primary", {"background:var(--m-accent)", "color:var(--m-on-accent)"}),
    ("btn btn--primary", {"background:var(--m-accent)"}),
    ("btn btn--soft", {"background:var(--m-accent-wash)",
                       "border:1px solid var(--m-accent)"}),
    ("btn btn--sec", {"background:transparent", "border:1px solid var(--m-line)"}),
    ("btn btn--sec", {"background:transparent", "border:1px solid var(--m-rule)"}),
    ("btn btn--sec", {"background:transparent",
                      "border:1px solid var(--m-rule-soft)"}),
    ("btn btn--sec", {"background:transparent",
                      "border:1px solid var(--m-rule-strong)"}),
    ("btn btn--ghost", {"background:transparent", "border:none"}),
    ("btn btn--ghost", {"background:transparent", "border:0"}),
    ("btn btn--ghost", {"background:none", "border:none"}),
    ("btn btn--ghost", {"background:none", "border:0"}),
]

BTN_SIZE = {
    "padding:4px 10px": "btn--sm", "padding:3px 10px": "btn--sm",
    "padding:4px 12px": "btn--sm", "padding:5px 11px": "btn--sm",
    "padding:10px 20px": "btn--lg", "padding:12px 24px": "btn--lg",
}

# Bootstrap classes leaking into a hand-built system. They are not "another
# variant" — they are a second design language, and five buttons wearing it look
# like a different application.
BOOTSTRAP = {"btn-outline-secondary": "btn--sec", "btn-sm": "btn--sm",
             "btn-primary": "btn--primary", "btn-secondary": "btn--sec",
             "btn-outline-primary": "btn--soft", "btn-lg": "btn--lg",
             "btn-danger": "btn--danger", "btn-light": "btn--ghost"}


def migrate_button(tag: str, stats: Counter) -> str:
    if not tag.lstrip("<").lower().startswith("button"):
        return tag
    cls_m = re.search(r'class="([^"]*)"', tag)
    have = set((cls_m.group(1) if cls_m else "").split())

    # Bootstrap first: translate the foreign language before reading the look.
    if have & set(BOOTSTRAP):
        new = {BOOTSTRAP.get(c, c) for c in have}
        new.add("btn")
        stats["bootstrap → btn"] += 1
        tag = re.sub(r'class="[^"]*"', f'class="{" ".join(sorted(new))}"', tag, 1)
        have = new

    st_m = re.search(r'style="([^"]*)"', tag)
    if not st_m or JINJA.search(st_m.group(1)):
        return tag
    decls = [norm(d) for d in st_m.group(1).split(";") if ":" in d]
    remaining = list(decls)
    add = []

    if "btn" not in have:
        for cls, want in BTN_LOOKS:
            if want <= set(remaining):
                add += [c for c in cls.split() if c not in have]
                remaining = [d for d in remaining if d not in want]
                stats[cls] += 1
                break

    if "btn" in have or "btn" in add:
        for d in list(remaining):
            if d in BTN_BASE:
                remaining.remove(d)
                stats["redundant with .btn"] += 1
            elif d in BTN_SIZE and BTN_SIZE[d] not in have:
                add.append(BTN_SIZE[d])
                remaining.remove(d)
                stats[BTN_SIZE[d]] += 1

    if not add and len(remaining) == len(decls):
        return tag

    if remaining:
        tag = re.sub(r'style="[^"]*"', 'style="' + ";".join(remaining) + ';"', tag, 1)
    else:
        tag = re.sub(r'\s*style="[^"]*"', "", tag, 1)
    if add:
        if re.search(r'class="[^"]*"', tag):
            tag = re.sub(r'class="([^"]*)"',
                         lambda m: f'class="{m.group(1)} {" ".join(add)}"'.strip(),
                         tag, 1)
        else:
            tag = re.sub(r"^<(\w+)", lambda m: f'<{m.group(1)} class="{" ".join(add)}"',
                         tag, 1)
    return tag


def process(text: str, stats: Counter) -> str:
    text = re.sub(r"<\w[^>]*style=\"[^\"]*\"[^>]*>",
                  lambda m: migrate_tag(m.group(0), stats), text)
    text = re.sub(r"<\w[^>]*style=\"[^\"]*\"[^>]*>",
                  lambda m: snap_tag(m.group(0), stats), text)
    # Buttons last: the passes above may have moved declarations onto classes,
    # and this reads what is left on the element as it finally stands.
    return re.sub(r"<button\b[^>]*>",
                  lambda m: migrate_button(m.group(0), stats), text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", default="", help="only files whose name contains this")
    a = ap.parse_args()
    if not (a.apply or a.check):
        ap.error("pass --check or --apply")

    stats: Counter = Counter()
    before = after = 0
    touched = 0
    for f in sorted(TPL.rglob("*.html")):
        if a.only and a.only not in f.name:
            continue
        src = f.read_text(encoding="utf-8")
        before += src.count('style="')
        out = process(src, stats)
        after += out.count('style="')
        if out != src:
            touched += 1
            if a.apply:
                f.write_text(out, encoding="utf-8")

    print(f"{'APPLIED' if a.apply else 'DRY RUN'} — {touched} files")
    print(f"style attributes: {before:,} → {after:,}   ({before - after:,} removed)")
    print("\nby idiom:")
    for cls, n in stats.most_common():
        print(f"   {n:5d}  .{cls}")
    print(f"\n   {sum(stats.values()):5d}  total substitutions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
