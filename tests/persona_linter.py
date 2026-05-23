#!/usr/bin/env python3
"""
persona_linter.py — flag voice-violation strings before commit.

The Metis persona is a warm, plain-English research companion. Generic
developer phrasing ("Could not", "Failed to", "Error:", "alert(") signals
that a script-flavoured message slipped past review.

USAGE
  python3 tests/persona_linter.py                # scan whole repo
  python3 tests/persona_linter.py path/to/file   # scan one file
  python3 tests/persona_linter.py --staged       # scan only git-staged files

EXIT CODES
  0  no violations
  1  one or more violations found

Add to .git/hooks/pre-commit (or via pre-commit framework) to enforce.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# (regex, severity, suggestion)
PATTERNS: list[tuple[str, str, str]] = [
    # JS / Python — hard violations
    (r"\balert\s*\(", "error", "use showToast() instead of alert() — keep the dialog inside Metis"),
    (r"Could not [a-z]", "warn", "rewrite in first person: 'I couldn't…' or 'Something went wrong…'"),
    (r"Failed to [a-z]", "warn", "rewrite in first person: 'I couldn't…' / 'I wasn't able to…'"),
    (r"\bError:\s", "warn", "drop 'Error:' label; say what went wrong in plain English"),
    (r"\bError occurred", "warn", "be specific: 'Something went wrong with X — try Y.'"),
    (r"\bNothing here yet\b", "warn", "make empty states warm + actionable, not generic"),
    (r"\bNo data\b", "warn", "tab-specific: 'No meetings yet — paste a transcript above to start.'"),
    (r"\bInternal Server Error\b", "warn", "translate to: 'Something on my end broke — give me a moment.'"),
    (r"\bTry again later\b", "warn", "be specific: 'Try again in a moment' or give a real next step"),
    # Implementation jargon leaking to user
    (r"\b(MCP|API|JSONL|JSON|SQL|venv)\b", "info", "consider replacing with plain English if user-facing"),
    (r"\bdef \w+\(", "info", "function names in copy is dev-speak — describe behaviour instead"),
]

# File extensions to scan (only user-visible templates / scripts)
SCAN_EXTS = {".html", ".js", ".py"}

# Paths that are NOT user-facing — skip them to avoid noise
SKIP_PARTS = {
    "/.venv/", "/node_modules/", "/htmx.min.js", "/bootstrap",
    "/tests/", "/scripts/", "/.git/", "/__pycache__/", "/dist/",
    "/persona_linter.py", "/run_metis_promises.sh",
    "/.claude/worktrees/",
}

# Lines containing these are typically not user-facing copy
LINE_SKIP_HINTS = (
    "logger.", "log.", "print(", "raise ", "except ", "assert ",
    "# noqa", "# type:", "TODO:", "console.log", "console.warn", "console.error",
    "import ", "from ",
)


def should_scan(p: Path) -> bool:
    s = str(p).replace("\\", "/")
    if any(skip in s for skip in SKIP_PARTS):
        return False
    return p.suffix in SCAN_EXTS


def scan_file(p: Path) -> list[tuple[int, str, str, str, str]]:
    """Return list of (line_no, severity, pattern_summary, matched_text, line_excerpt)."""
    out = []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are obviously not user-facing copy
        if any(h in stripped for h in LINE_SKIP_HINTS):
            continue
        for pat, sev, _ in PATTERNS:
            m = re.search(pat, line)
            if m:
                out.append((i, sev, pat, m.group(0), stripped[:140]))
                break  # one violation per line is enough signal
    return out


def staged_files() -> list[Path]:
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, check=True,
        )
        return [Path(p) for p in res.stdout.splitlines() if p]
    except Exception:
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="files or dirs (default: whole repo)")
    ap.add_argument("--staged", action="store_true", help="scan git-staged files only")
    ap.add_argument("--errors-only", action="store_true", help="fail only on errors, not warns")
    args = ap.parse_args()

    if args.staged:
        candidates = [p for p in staged_files() if should_scan(p) and p.exists()]
    elif args.paths:
        candidates = []
        for raw in args.paths:
            p = Path(raw)
            if p.is_file() and should_scan(p):
                candidates.append(p)
            elif p.is_dir():
                candidates.extend(q for q in p.rglob("*") if q.is_file() and should_scan(q))
    else:
        # Default: scan the user-facing dirs
        roots = [Path("system/app-py/templates"), Path("system/app-py/static"),
                 Path("system/app-py/routers")]
        candidates = []
        for r in roots:
            if r.exists():
                candidates.extend(q for q in r.rglob("*") if q.is_file() and should_scan(q))

    errors = 0
    warns = 0
    by_file: dict[Path, list] = {}
    for f in candidates:
        viol = scan_file(f)
        if viol:
            by_file[f] = viol
            for _, sev, *_ in viol:
                if sev == "error":
                    errors += 1
                elif sev == "warn":
                    warns += 1

    if not by_file:
        print(f"✓ persona linter clean ({len(candidates)} files scanned)")
        return 0

    for f, viol in sorted(by_file.items()):
        rel = f.as_posix()
        print(f"\n{rel}")
        for line_no, sev, pat, match, excerpt in viol:
            marker = "🔴" if sev == "error" else ("🟡" if sev == "warn" else "·")
            print(f"  {marker} L{line_no}  [{sev}]  matched {match!r}")
            print(f"      {excerpt}")

    print(f"\n— {errors} errors · {warns} warnings · {len(by_file)} files —")
    if errors > 0:
        return 1
    if warns > 0 and not args.errors_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
