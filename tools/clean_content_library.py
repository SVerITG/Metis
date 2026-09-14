#!/usr/bin/env python3
"""clean_content_library.py — leave only what can go on a slide.

The content library is what a deck is built from, so it should hold slide
material and nothing else. In practice it also accumulates the manifests and
extracted tables that produced the images — someone's work, and worth keeping,
but not worth scrolling past every time you look for a figure.

THREE VERDICTS, AND THE THIRD IS THE POINT.

  keep     images, vector art and video — things that can appear on a slide
  archive  manifests, notes, extracted data — moved, never deleted
  ask      documents that might be either (PDF, DOCX, a stray deck)

NOTHING IS DELETED, EVER. `--apply` MOVES archive-class files into an `_archive/`
folder inside the library, keeping their relative path, so the whole operation is
reversible with a file manager and nothing is lost if a verdict was wrong.

The `ask` class exists because guessing is how you lose something. A folder of
open-access articles is a real reference collection that happens to live here;
whether it belongs is the owner's call, and the tool reports it rather than
deciding.

Usage:
    python3 tools/clean_content_library.py <folder>            # show the verdicts
    python3 tools/clean_content_library.py <folder> --apply    # move the archive class
"""
from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

# Anything that can be placed on a slide.
KEEP = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".tif", ".tiff",
        ".bmp", ".svg", ".emf", ".wmf", ".mp4", ".mov", ".webm", ".m4v",
        ".mp3", ".wav"}
# Working material: it produced the images, it is not itself slide material.
ARCHIVE = {".csv", ".tsv", ".md", ".txt", ".json", ".yml", ".yaml", ".xml",
           ".log", ".xlsx", ".xls", ".ods"}
# Could be either. Reported, never moved.
ASK = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".odp", ".odt", ".zip"}

ARCHIVE_DIR = "_archive"


def verdict(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in KEEP:
        return "keep"
    if ext in ARCHIVE:
        return "archive"
    if ext in ASK:
        return "ask"
    return "ask"                      # unknown is a question, not a decision


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="the content library")
    ap.add_argument("--apply", action="store_true",
                    help="move the archive class into _archive/ (never deletes)")
    args = ap.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        print(f"no such folder: {root}", file=sys.stderr)
        return 2
    dest_root = root / ARCHIVE_DIR

    buckets: dict[str, list[Path]] = {"keep": [], "archive": [], "ask": []}
    exts: dict[str, Counter] = {k: Counter() for k in buckets}
    for p in root.rglob("*"):
        if not p.is_file() or ARCHIVE_DIR in p.parts or p.name.startswith("~$"):
            continue
        v = verdict(p)
        buckets[v].append(p)
        exts[v][p.suffix.lower() or "(none)"] += 1

    for name, label in (("keep", "KEEP — can go on a slide"),
                        ("archive", "ARCHIVE — working material, will be moved"),
                        ("ask", "ASK — your call, nothing will be touched")):
        rows = exts[name].most_common()
        print(f"\n{label}: {len(buckets[name])} file(s)")
        for ext, n in rows:
            print(f"    {ext:<8} {n:>5}")

    if buckets["ask"]:
        print("\n  the 'ask' files, by folder:")
        folders = Counter(str(p.parent.relative_to(root)) for p in buckets["ask"])
        for f, n in folders.most_common(12):
            print(f"    {n:>4}  {f or '.'}")

    if not args.apply:
        print(f"\nDRY RUN — nothing moved. Re-run with --apply to move the "
              f"{len(buckets['archive'])} archive-class file(s) into {ARCHIVE_DIR}/")
        return 0

    moved = failed = 0
    for p in buckets["archive"]:
        target = dest_root / p.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            # Never overwrite — a same-named file already archived is a
            # different file until proven otherwise.
            stem, suf, i = target.stem, target.suffix, 2
            while target.exists():
                target = target.with_name(f"{stem}~{i}{suf}")
                i += 1
        try:
            shutil.move(str(p), str(target))
            moved += 1
        except OSError as exc:
            print(f"  ! could not move {p.name}: {exc}", file=sys.stderr)
            failed += 1
    print(f"\nmoved {moved} file(s) into {ARCHIVE_DIR}/"
          + (f" · {failed} could not be moved" if failed else ""))
    print("Nothing was deleted. Reverse it by moving the folder's contents back.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
