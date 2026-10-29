#!/usr/bin/env python3
"""Refuse an edition copy that still carries the owner's own subject matter.

    python3 editions/scan_edition.py <copy-dir> <edition-dir>

Reads <edition-dir>/forbidden.txt (one case-insensitive regex per line, # for
comments) and <edition-dir>/allowed.txt (lines "path-glob<TAB>regex": a hit of
that regex in a matching file is accepted, with the reason in a trailing
comment). Both files live under editions/, which no edition ships, so the list
of what must not be published is not itself published.

Exit 0 clean · 2 hits found · 4 refused to judge (nothing was scanned, or the
term list is empty). A scan over zero files is not a clean scan.
"""
from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

TEXT_EXT = {".py", ".md", ".html", ".js", ".css", ".json", ".toml", ".yml", ".yaml",
            ".txt", ".ps1", ".bat", ".vbs", ".iss", ".sh", ".sql", ".cfg", ".ini",
            ".example", ".j2", ".svg", ".mjs", ".r", ".R"}


def _lines(p: Path) -> list[str]:
    if not p.is_file():
        return []
    return [ln.rstrip("\n") for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    copy, ed = Path(sys.argv[1]), Path(sys.argv[2])
    terms = [re.compile(t, re.I) for t in _lines(ed / "forbidden.txt")]
    allowed = []
    for ln in _lines(ed / "allowed.txt"):
        glob, _, rx = ln.split("#", 1)[0].rstrip().partition("\t")
        if glob and rx:
            allowed.append((glob.strip(), re.compile(rx.strip(), re.I)))
    if not terms:
        print("REFUSED: no forbidden terms to look for.")
        return 4

    scanned, hits = 0, []
    for f in sorted(copy.rglob("*")):
        if ".git" in f.parts or not f.is_file() or f.suffix not in TEXT_EXT:
            continue
        rel = f.relative_to(copy).as_posix()
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        for n, line in enumerate(text.splitlines(), 1):
            for t in terms:
                m = t.search(line)
                if not m:
                    continue
                if any(fnmatch.fnmatch(rel, g) and rx.search(line) for g, rx in allowed):
                    continue
                hits.append(f"{rel}:{n}: [{m.group(0)}] {line.strip()[:110]}")
    # Also the file NAMES: a file called after a disease ships its subject even empty.
    for f in copy.rglob("*"):
        if ".git" in f.parts:
            continue
        for t in terms:
            if t.search(f.name):
                hits.append(f"{f.relative_to(copy).as_posix()}: [file name]")
    if scanned == 0:
        print("REFUSED: no text files were scanned.")
        return 4
    if hits:
        print(f"{len(hits)} hit(s) in {scanned} files scanned:")
        print("\n".join(hits[:400]))
        if len(hits) > 400:
            print(f"... and {len(hits) - 400} more")
        return 2
    print(f"Clean: {scanned} text files scanned, {len(terms)} terms, no hits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
