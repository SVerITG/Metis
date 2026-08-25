#!/usr/bin/env python3
"""mine_decisions.py — promote standing decisions out of session summaries.

WHAT THIS CORRECTS
    On 2026-08-24 I reported "7,578 decisions sit in session summaries, 2 are in
    the decisions table". The second half was right; the first was not.

        7,619 raw entries
        1,199 unique strings
           68 actually decision-SHAPED

    The gap is the echo. The most repeated entries are project next-steps restated
    every session — "HAT Dashboard — _next: Review reactive architecture" appears
    **607 times** — plus session findings ("Library health score 58/100"), which are
    facts for semantic memory, not preferences an agent should apply.

    So the reader was missing, but the backlog was 68, not 7,578. Reusing
    `decisions_ledger._is_decision` rather than counting array elements is what
    tells the difference: a restated task is not an unmade decision.

WHY ATTRIBUTION IS KEYWORD-BASED AND CONSERVATIVE
    A decision is only useful if it reaches the specialist that acts on it, and a
    wrong attribution is worse than none: it hides the rule from the agent that
    needed it AND clutters one that does not. So the mapping below is deliberately
    narrow, and anything it cannot place confidently becomes project-wide — where
    every agent sees it. Over-attributing is the failure mode to avoid.

USAGE
    python3 tools/mine_decisions.py --dry-run
    python3 tools/mine_decisions.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "system" / "mcp-server" / "src"))
os.environ.setdefault("METIS_RC_ROOT", str(_ROOT))

from metis_mcp.tools.decisions_ledger import _fingerprint, _is_decision  # noqa: E402

# (regex, agent_slug, category). First match wins, so order is precedence.
ROUTE = [
    (r"palette|css|chart|colour|color|layout|macro|navbar|surface|tab\b|ui\b|"
     r"dashboard look|typograph|token", "frontend-designer-builder", "design"),
    (r"\bDB\b|database|sqlite|wal\b|onedrive|flock|lock|port |supervisor|"
     r"install|venv|schema|migration|hook|crash|restart", "software-engineer", "architecture"),
    (r"raster|cost-distance|vector|kriging|spatial|multilevel|model\b|"
     r"estimat|sample size|power|statistic", "methods-coach", "method"),
    (r"corpus|library|zotero|literature|paper|citation|doi|index", "librarian", "library"),
    (r"study design|case definition|surveillance|bias|epidemi", "epidemiologist", "method"),
    (r"village|dataset|clean|column|one-row|record linkage|merge", "data-analyst", "method"),
    (r"repo|push|remote|base shell|release|changelog|version", "release-coordinator", "process"),
    (r"prompt|persona|voice|tone|marker|reply|writing|prose", "writing-partner", "writing"),
    (r"\bMCP\b|tool|agent|routing|subset|token", "rc-builder", "architecture"),
    (r"course|lesson|quiz|curriculum|teach", "course-builder", "process"),
]


def route(text: str) -> tuple[str, str]:
    low = text.lower()
    for pat, slug, cat in ROUTE:
        if re.search(pat, low, re.I):
            return slug, cat
    return "", "process"          # project-wide — every agent sees it


def db_path() -> Path:
    env = os.environ.get("METIS_DB_PATH", "")
    if env and Path(env).exists():
        return Path(env)
    return Path.home() / ".local/share/metis" / "metis.sqlite"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row

    raw: list[str] = []
    for (d,) in con.execute(
            "SELECT decisions FROM session_summaries "
            "WHERE COALESCE(decisions,'') NOT IN ('','[]')"):
        try:
            v = json.loads(d)
            raw += v if isinstance(v, list) else [str(v)]
        except Exception:
            raw.append(d)
    raw = [str(x).strip() for x in raw if str(x).strip()]

    # Already-stored decisions, so a re-run is a no-op rather than a duplicator.
    try:
        existing = {_fingerprint(r[0]) for r in con.execute(
            "SELECT decision FROM user_decisions")}
    except Exception:
        existing = set()

    picked: dict[str, str] = {}
    for s in dict.fromkeys(raw):
        if not _is_decision(s):
            continue
        fp = _fingerprint(s)
        if fp in existing or fp in picked:
            continue
        # Near-duplicates differing only in trailing words ("… per keep-both-repos
        # rule" vs "… using keep-both-repos rule") survive a full fingerprint, so
        # collapse on the first eight meaningful tokens too.
        short = " ".join(_fingerprint(s).split()[:8])
        if any(" ".join(_fingerprint(v).split()[:8]) == short for v in picked.values()):
            continue
        picked[fp] = s

    by_agent: dict[str, int] = {}
    written = 0
    for s in picked.values():
        slug, cat = route(s)
        by_agent[slug or "(project-wide)"] = by_agent.get(slug or "(project-wide)", 0) + 1
        if not args.dry_run:
            con.execute(
                "INSERT INTO user_decisions (category, decision, context, scope, "
                "source, hits, created_at, agent_slug) "
                "VALUES (?,?,?,'always','mined',0,datetime('now'),?)",
                (cat, s[:900], "Promoted from a session summary by "
                               "tools/mine_decisions.py", slug))
            written += 1
    if not args.dry_run:
        con.commit()

    print(f"  raw entries            : {len(raw):,}")
    print(f"  unique strings         : {len(dict.fromkeys(raw)):,}")
    print(f"  decision-shaped, new   : {len(picked)}")
    print(f"  {'would write' if args.dry_run else 'WROTE'}            : {len(picked) if args.dry_run else written}")
    print()
    for a, n in sorted(by_agent.items(), key=lambda kv: -kv[1]):
        print(f"    {n:4d}  {a}")
    total = con.execute("SELECT COUNT(*) FROM user_decisions").fetchone()[0]
    con.close()
    print(f"\n  user_decisions now holds {total} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
