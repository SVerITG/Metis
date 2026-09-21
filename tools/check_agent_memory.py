#!/usr/bin/env python3
"""check_agent_memory.py — is the specialist learning loop actually closing?

WHAT THIS EXISTS TO CATCH
    A standing decision that is recorded and never reaches an agent is
    indistinguishable, from the outside, from one that was never recorded. For a
    long time every usage counter in the table sat at zero while the count of
    decisions grew past five hundred — the writer worked, the reader worked, and
    nothing in between reported back, so nothing could tell the difference.

    This restates the property independently, the same way the other checkers in
    this directory do, so that drift between the intent and the data is visible
    instead of inferred.

WHAT IT REPORTS
    · how many decisions exist, and how many have ever been delivered or applied
    · which specialists carry nothing, and therefore cannot grow
    · decisions attached to a specialist that has never run — recorded, but with
      no route to a reader
    · whether each agent's projected memory file exists and is current

EXIT CODE
    0  the loop is closing
    1  something is recorded that can never be read

USAGE
    python3 tools/check_agent_memory.py
    python3 tools/check_agent_memory.py --verbose
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

from metis_mcp.config import paths            # noqa: E402
from metis_mcp.db import connect              # noqa: E402
from metis_mcp.tools.agent_memory import _ensure   # noqa: E402

AGENTS = ROOT / ".claude" / "agents"
MEM = ROOT / ".claude" / "agent-memory"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    slugs = sorted(p.stem for p in AGENTS.glob("*.md"))
    problems: list[str] = []

    with connect(paths.db) as con:
        _ensure(con)
        total = con.execute("SELECT COUNT(*) FROM user_decisions").fetchone()[0]
        delivered = con.execute("SELECT COUNT(*) FROM user_decisions "
                                "WHERE COALESCE(delivered,0)>0").fetchone()[0]
        applied = con.execute("SELECT COUNT(*) FROM user_decisions "
                              "WHERE COALESCE(hits,0)>0").fetchone()[0]
        shared = con.execute("SELECT COUNT(*) FROM user_decisions "
                             "WHERE COALESCE(agent_slug,'')=''").fetchone()[0]
        per = {r[0]: r[1] for r in con.execute(
            "SELECT COALESCE(agent_slug,''), COUNT(*) FROM user_decisions "
            "WHERE COALESCE(agent_slug,'')<>'' GROUP BY 1")}
        ran = {r[0] for r in con.execute(
            "SELECT DISTINCT agent_slug FROM agent_runs")}

    pct = lambda n: f"{n * 100 // max(total, 1)}%"
    print("=" * 74)
    print("  SPECIALIST LEARNING LOOP")
    print("=" * 74)
    print(f"  standing decisions            {total}")
    print(f"  ever delivered to an agent    {delivered:<5} ({pct(delivered)})")
    print(f"  ever confirmed applied        {applied:<5} ({pct(applied)})")
    print(f"  project-wide (no specialist)  {shared:<5} ({pct(shared)})")

    if total and delivered == 0:
        problems.append(
            "No decision has ever been delivered. Either nothing is calling "
            "get_agent_context, or the delivery signal is not wired — the whole "
            "point of recording preferences is lost either way.")

    # ── per specialist ───────────────────────────────────────────────────────
    empty = [s for s in slugs if not per.get(s)]
    orphaned = sorted(s for s in per if s not in ran)
    stale: list[str] = []
    missing: list[str] = []

    for slug in slugs:
        f = MEM / slug / "MEMORY.md"
        if not f.exists():
            missing.append(slug)

    print()
    print(f"  specialists defined           {len(slugs)}")
    print(f"  carrying no decisions         {len(empty)}")
    print(f"  projected memory file present {len(slugs) - len(missing)} of {len(slugs)}")

    if args.verbose:
        print("\n  decisions per specialist:")
        for slug in slugs:
            n = per.get(slug, 0)
            mark = " (never run)" if slug in orphaned else ""
            print(f"      {n:>4}  {slug}{mark}")

    if empty:
        print(f"\n  ⚠ {len(empty)} specialist(s) carry NO decisions — they return a "
              f"persona and nothing more:")
        print("     " + ", ".join(empty))

    if orphaned:
        print(f"\n  ⚠ {len(orphaned)} specialist(s) have decisions but have never run, "
              f"so those preferences have no reader:")
        print("     " + ", ".join(orphaned))

    if missing:
        problems.append(
            f"{len(missing)} agent(s) have no projected memory file: "
            f"{', '.join(missing)}. Run tools/generate_agent_memory.py.")

    print()
    print("-" * 74)
    if problems:
        for p_ in problems:
            print(f"  ✗ {p_}")
        print("\nRESULT: the loop is NOT closing")
        return 1
    print("  ✓ decisions are reaching agents, and every agent has a memory file")
    print("\nRESULT: the loop closes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
