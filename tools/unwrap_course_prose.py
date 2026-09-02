#!/usr/bin/env python3
"""Make course lesson markdown render the way it was written.

`routers/learning.py` renders lessons with:

    markdown.Markdown(extensions=["fenced_code", "tables", "nl2br"])

Two consequences that nobody notices by reading the source, because the source
looks fine:

  1. `nl2br` turns EVERY newline into a <br>. Hard-wrapped body prose therefore
     renders with a forced break at each wrap point: the paragraph is pinned to
     whatever measure the author typed to, and double-wraps raggedly in a narrow
     window. `nl2br` is there deliberately — the concept-map blockquote at the top
     of each lesson relies on it — so the fix is on the source side, not the
     renderer's.

  2. Python-Markdown needs a blank line before a list. Written without one:

         By the end of this lesson you will be able to:
         - **Name** the file formats in the chain ...

     the whole block renders as ONE paragraph of flat text with the "-" and "1."
     left as literal characters. Every "By the end of this lesson" block in every
     course was rendering this way.

Three stages, in order:

  1. unwrap            — join hard-wrapped prose into one line per paragraph
  2. blank_before_lists — insert the blank line a list needs
  3. reflow_blockquotes — reflow prose blockquotes, leaving label blocks alone

Left exactly as written: fenced code, tables, headings, horizontal rules, list
item boundaries, and any blockquote whose every line opens with "> **" (the
concept maps and structured pull-quotes, which want their line breaks).

Idempotent. Refuses to write a file if the word count changes.

Usage:
    python3 tools/unwrap_course_prose.py --check --all
    python3 tools/unwrap_course_prose.py --check ai-in-public-health
    python3 tools/unwrap_course_prose.py ai-in-public-health
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COURSES = ROOT / "knowledge" / "courses"

LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s")
KEEP_RE = re.compile(r"^\s*(\||>|#{1,6}\s|---\s*$|\*\*\*\s*$|___\s*$)")
QUOTE_ENDS = (".", ":", "?", "!", "**", "—")


def words(text: str) -> int:
    """Count real words, ignoring markdown structure.

    A bare ">" or "-" is a token to str.split(), so joining a quoted line onto the
    one above drops "words" while losing no content. Counting only tokens that
    contain a letter or digit makes the guard mean what it is meant to mean.
    """
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


def unwrap(text: str) -> str:
    """Stage 1 — one line per paragraph, so nl2br has nothing spurious to break on."""
    out, buf, in_fence = [], [], False

    def flush():
        if buf:
            out.append(" ".join(s.strip() for s in buf))
            buf.clear()

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            flush(); in_fence = not in_fence; out.append(line); continue
        if in_fence:
            out.append(line); continue
        if not line.strip():
            flush(); out.append(""); continue
        if KEEP_RE.match(line):
            flush(); out.append(line); continue
        if LIST_RE.match(line):
            flush()                      # a new bullet starts a new logical line
        buf.append(line)
    flush()
    return "\n".join(out)


def blank_before_lists(text: str) -> str:
    """Stage 2 — a list needs a blank line above it or it is not a list."""
    out, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence; out.append(line); continue
        if (not in_fence and LIST_RE.match(line)
                and out and out[-1].strip()
                and not LIST_RE.match(out[-1])
                and not KEEP_RE.match(out[-1])):
            out.append("")
        out.append(line)
    return "\n".join(out)


def reflow_blockquotes(text: str) -> str:
    """Stage 3 — reflow prose blockquotes; leave label blocks untouched.

    A per-line rule ("a line opening '> **' starts a new line") misfires on prose
    whose wrap point lands on bold text. Two rules instead:

      1. If EVERY non-blank line of a blockquote opens with "> **", it is a label
         block — a concept map, a structured template — and is left alone.
      2. Otherwise reflow, breaking at a "> **" only when the line above ended a
         sentence or a lead-in. A wrap point never lands there, so prose joins and
         genuine labels still break.
    """
    lines = text.split("\n")
    out, in_fence, i = [], False, 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence; out.append(line); i += 1; continue
        if in_fence or not line.lstrip().startswith(">"):
            out.append(line); i += 1; continue

        block, j = [], i
        while j < len(lines) and lines[j].lstrip().startswith(">"):
            block.append(lines[j]); j += 1

        content = [b for b in block if b.strip() != ">"]
        if content and all(b.lstrip().startswith("> **") for b in content):
            out.extend(block)
        else:
            acc = []
            for b in block:
                st = b.lstrip()
                if st.strip() == ">":
                    acc.append(b); continue
                prev = acc[-1].rstrip() if acc else ""
                prev_open = bool(prev) and prev.strip() != ">"
                if prev_open and not (st.startswith("> **") and prev.endswith(QUOTE_ENDS)):
                    acc[-1] = prev + " " + st[1:].strip()
                else:
                    acc.append(b)
            out.extend(acc)
        i = j
    return "\n".join(out)


def transform(text: str) -> str:
    return reflow_blockquotes(blank_before_lists(unwrap(text)))


def diagnose(text: str) -> dict:
    """Source-level symptoms, so --check needs no running server."""
    wrapped = 0        # prose lines that will render with a forced break
    orphan_lists = 0   # list blocks with no blank line above them
    in_fence = False
    lines = text.split("\n")
    for k, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence; continue
        if in_fence or not line.strip():
            continue
        prev = lines[k - 1] if k else ""
        if LIST_RE.match(line):
            if prev.strip() and not LIST_RE.match(prev) and not KEEP_RE.match(prev):
                orphan_lists += 1
            continue
        if KEEP_RE.match(line):
            continue
        if prev.strip() and not KEEP_RE.match(prev) and not LIST_RE.match(prev):
            wrapped += 1
    return {"forced_breaks": wrapped, "orphan_lists": orphan_lists}


def course_files(slug_or_path: str):
    p = pathlib.Path(slug_or_path)
    base = p if p.is_dir() else COURSES / slug_or_path
    if not base.is_dir():
        raise SystemExit(f"no such course: {slug_or_path}")
    return base, sorted(base.glob("lessons/*.md")) + sorted(base.glob("deep-dives/*.md"))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("courses", nargs="*", help="course slug(s) or path(s)")
    ap.add_argument("--all", action="store_true", help="every course under knowledge/courses")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    targets = list(args.courses)
    if args.all:
        targets = sorted(d.name for d in COURSES.iterdir()
                         if d.is_dir() and (d / "lessons").is_dir())
    if not targets:
        ap.error("name at least one course, or pass --all")

    grand = {"files": 0, "changed": 0, "breaks": 0, "lists": 0}
    for slug in targets:
        base, files = course_files(slug)
        if not files:
            continue
        breaks = lists = changed = 0
        for f in files:
            src = f.read_text(encoding="utf-8")
            d = diagnose(src)
            breaks += d["forced_breaks"]; lists += d["orphan_lists"]
            new = transform(src)
            if words(src) != words(new):
                print(f"  !! WORD LOSS in {f} — {words(src)} -> {words(new)}; nothing written")
                return 1
            if new != src:
                changed += 1
                if not args.check:
                    f.write_text(new, encoding="utf-8")
        verb = "would fix" if args.check else "fixed"
        flag = "" if (breaks or lists) else "  clean"
        print(f"{base.name:<56} {len(files):>3} files · "
              f"{breaks:>5} forced breaks · {lists:>4} orphan lists · {verb} {changed}{flag}")
        grand["files"] += len(files); grand["changed"] += changed
        grand["breaks"] += breaks; grand["lists"] += lists

    print("-" * 100)
    print(f"{'TOTAL':<56} {grand['files']:>3} files · "
          f"{grand['breaks']:>5} forced breaks · {grand['lists']:>4} orphan lists · "
          f"{'would change' if args.check else 'changed'} {grand['changed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
