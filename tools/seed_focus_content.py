#!/usr/bin/env python3
"""Apply authored focus-surface content from `system/config/focus/*.md` to the DB.

WHY THIS EXISTS
    A focus surface renders four things out of its `focus_areas` row: the
    `overview` markdown, the `links` it offers as reference cards, the
    `sections` it shows, and the `keyword_groups` that define its lens. All four
    were previously authored by writing straight into the database.

    That database is `~/.local/share/metis/metis.sqlite` — machine-local, and
    deliberately not synced, because OneDrive corrupts SQLite's WAL sidecars.
    So content written only into the DB exists on ONE of the two computers and
    silently does not exist on the other. The same class of failure as the venv
    and the model cache.

    So the markdown file is the AUTHOR and the row is DERIVED. The file syncs
    with the repo; this tool replays it. Re-running after editing the file is
    the intended workflow, and it is safe.

WHAT IT WILL NOT DO
    Create a focus. A focus is created on the dashboard or through the MCP tool,
    which is where the slug, title and shelf slot are decided. This tool only
    fills in the content of one that exists — naming a slug that does not is an
    error, not an invitation.

PROSE IS UNWRAPPED ON PURPOSE
    The overview renders through `nl2br`, so every hard wrap in the source
    becomes a forced `<br>` and the paragraph never reflows. This tool reports
    any hard-wrapped prose it is asked to install rather than fixing it
    silently — the same defect `tools/unwrap_course_prose.py` fixes for lessons.

USAGE
    python3 tools/seed_focus_content.py                  # dry run: report only
    python3 tools/seed_focus_content.py --apply          # write
    python3 tools/seed_focus_content.py --slug ai-in-health-epidemiology --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# TWO DIRECTORIES, AND THE SECOND ONE IS THE POINT.
#
# A focus overview is written FOR one reader: it addresses them directly and
# draws connections to their own work. Both repositories here are public, so
# that content must never be committed — but it still has to reach the other
# computer, and the database does not sync.
#
# `system/config/local/` is gitignored while living inside the repo folder,
# which OneDrive replicates. So a file there syncs between machines and never
# reaches GitHub: exactly the right home for authored personal content.
#
# `system/config/focus/` stays available for content that is genuinely generic
# and meant to ship. A local file WINS over a shipped one with the same slug.
CFG_DIRS = [REPO / "system" / "config" / "focus",
            REPO / "system" / "config" / "local" / "focus"]

# The section keys focus.html actually has a branch for. A key outside this set
# renders NOTHING, silently — so it is rejected here rather than shipped.
KNOWN_SECTIONS = {"pulse", "overview", "tools", "whatsnew", "safe", "brief",
                  "thinking", "feed", "reading"}

# A line that STARTS a new block: heading, list item, table row, quote, rule.
# NOTE the required space after a bullet character. Without it, a paragraph that
# merely BEGINS with emphasis — *"every citation is an unverified lead"* — reads
# as a bullet, the joiner leaves the wrap alone, and one forced <br> survives in
# the middle of a sentence. That was the last of the original 19.
_STARTS = re.compile(r"^\s*([-*+]\s|[>#|]|\d+\.\s|---\s*$)")
# A line that must never absorb following text: a heading has to stay on its own
# line, and a table row must not swallow the paragraph after it. Everything else
# — including a list item — may absorb its own wrapped continuation, which is
# where 8 of the first 19 forced breaks were hiding.
_NO_ABSORB = re.compile(r"^\s*([#|]|---\s*$)")


def db_path() -> Path:
    env = os.environ.get("METIS_DB")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "metis" / "metis.sqlite"


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Raises on a malformed file."""
    if not text.startswith("---"):
        raise ValueError("file does not begin with a --- frontmatter block")
    try:
        import yaml
    except ImportError:  # pragma: no cover
        raise SystemExit("PyYAML is required: pip install pyyaml")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter is not a mapping")
    # Strip an HTML comment header — it is a note to the author, not content.
    body = re.sub(r"^\s*<!--.*?-->\s*", "", body, flags=re.S)
    return meta, body.strip() + "\n"


def hard_wraps(body: str) -> int:
    """Count prose line breaks that nl2br will turn into a forced <br>."""
    lines = body.split("\n")
    n = 0
    for i, ln in enumerate(lines[:-1]):
        nxt = lines[i + 1]
        if (ln.strip() and nxt.strip()
                and not _STARTS.match(nxt) and not _NO_ABSORB.match(ln)):
            n += 1
    return n


def validate(meta: dict, body: str, path: Path) -> list[str]:
    """Every reason this file must not be installed. Empty list = good."""
    errs: list[str] = []
    if not meta.get("slug"):
        errs.append("no `slug` in frontmatter")
    if not body.strip():
        errs.append("body (the overview) is empty")

    secs = meta.get("sections") or []
    if secs:
        unknown = [s for s in secs if s not in KNOWN_SECTIONS]
        if unknown:
            errs.append(f"unknown section keys {unknown} — the template has no "
                        f"branch for these and they would render nothing")
        if "tools" in secs and not meta.get("links"):
            errs.append("sections declares `tools` but there are no links, so "
                        "the section would render as an empty box")

    for i, l in enumerate(meta.get("links") or []):
        if not isinstance(l, dict):
            errs.append(f"link {i} is not a mapping")
            continue
        if not l.get("title") or not l.get("href"):
            errs.append(f"link {i} needs both `title` and `href`")
            continue
        href = str(l["href"])
        if not (href.startswith("http") or href.startswith("/")):
            errs.append(f"link {i} href {href!r} is neither a URL nor a site path")

    groups = meta.get("keyword_groups")
    if groups is not None:
        if not isinstance(groups, list) or not all(isinstance(g, list) for g in groups):
            errs.append("`keyword_groups` must be a list of lists")
        elif not groups or not all(groups):
            errs.append("`keyword_groups` has an empty group — an empty lens "
                        "matches nothing at all")
    return errs


def apply_file(con: sqlite3.Connection, path: Path, write: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    try:
        meta, body = split_frontmatter(text)
    except Exception as exc:
        print(f"  ✗ {path.name}: {exc}")
        return False

    errs = validate(meta, body, path)
    if errs:
        print(f"  ✗ {path.name}: refusing to install")
        for e in errs:
            print(f"      - {e}")
        return False

    slug = meta["slug"]
    row = con.execute("SELECT overview, sections, links, keyword_groups "
                      "FROM focus_areas WHERE slug=?", (slug,)).fetchone()
    if row is None:
        print(f"  ✗ {path.name}: no focus with slug {slug!r}. Create the focus "
              f"first — this tool fills content, it does not invent surfaces.")
        return False

    new = {
        "overview": body,
        "sections": json.dumps(meta.get("sections") or []),
        "links": json.dumps(meta.get("links") or []),
        "keyword_groups": json.dumps(meta.get("keyword_groups")
                                     if meta.get("keyword_groups") is not None
                                     else json.loads(row["keyword_groups"] or "[]")),
    }

    print(f"  {path.name}  ->  focus {slug!r}")
    changed = []
    for col, val in new.items():
        old = row[col] or ""
        if str(old) == str(val):
            print(f"      {col:15s} unchanged")
            continue
        changed.append(col)
        if col == "overview":
            print(f"      {col:15s} {len(str(old).split()):5d} -> "
                  f"{len(val.split()):5d} words")
        elif col == "keyword_groups":
            o = json.loads(old or "[]")
            n = json.loads(val)
            for gi, (og, ng) in enumerate(zip(o or [[]] * len(n), n), 1):
                added = [k for k in ng if k not in og]
                gone = [k for k in og if k not in ng]
                if added:
                    print(f"      {'':15s} group {gi} + {added}")
                if gone:
                    print(f"      {'':15s} group {gi} - {gone}  (REMOVED)")
        else:
            o = json.loads(old or "[]")
            n = json.loads(val)
            print(f"      {col:15s} {len(o) if isinstance(o, list) else '?'} -> "
                  f"{len(n)} entries")

    hw = hard_wraps(body)
    if hw:
        print(f"      ⚠ {hw} hard-wrapped prose line(s) — each becomes a forced "
              f"<br> because the overview renders through nl2br. Write one line "
              f"per paragraph.")

    if not changed:
        print("      nothing to do")
        return True

    if not write:
        print(f"      DRY RUN — would update: {', '.join(changed)}")
        return True

    con.execute("UPDATE focus_areas SET overview=?, sections=?, links=?, "
                "keyword_groups=? WHERE slug=?",
                (new["overview"], new["sections"], new["links"],
                 new["keyword_groups"], slug))
    con.commit()
    print(f"      WROTE: {', '.join(changed)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    ap.add_argument("--slug", default="", help="only this focus")
    args = ap.parse_args()

    # Later directories win, so a local file overrides a shipped one.
    by_slug: dict[str, Path] = {}
    for d in CFG_DIRS:
        if d.is_dir():
            for f in sorted(d.glob("*.md")):
                by_slug[f.stem] = f
    if not by_slug:
        print("no focus content files found in:")
        for d in CFG_DIRS:
            print(f"  {d}")
        return 1
    files = [by_slug[k] for k in sorted(by_slug)]
    if args.slug:
        files = [f for f in files if f.stem == args.slug]
    if not files:
        print(f"no focus content file for slug {args.slug!r}")
        return 1

    db = db_path()
    if not db.exists():
        print(f"database not found: {db}")
        return 1

    print(f"{'APPLYING' if args.apply else 'DRY RUN'} — {len(files)} file(s), db={db}")
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    ok = all(apply_file(con, f, args.apply) for f in files)
    con.close()
    if not args.apply:
        print("\nre-run with --apply to write")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
