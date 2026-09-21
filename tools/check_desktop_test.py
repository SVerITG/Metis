#!/usr/bin/env python3
"""check_desktop_test.py — did the other client's test run actually leave traces?

WHY THIS EXISTS
    A conversational assistant can say it recorded something and be wrong, and
    the person reading the reply has no way to tell. That is the failure this
    whole project keeps finding: a write path with no reader looks identical to a
    working one from the outside.

    So the test is run in one client and verified here, against the database,
    where a claim either left a row or did not.

HOW TO USE IT
    1.  python3 tools/check_desktop_test.py --snapshot
        Take a baseline BEFORE running the test prompts.

    2.  Run the test prompts in the other client.

    3.  python3 tools/check_desktop_test.py
        Compare against the baseline and report what actually landed.

    --snapshot writes a small JSON file; nothing else is modified. This tool
    never writes to the database.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

from metis_mcp.config import paths          # noqa: E402
from metis_mcp.db import connect            # noqa: E402

SNAP = ROOT / "system" / "config" / "local" / ".desktop-test-baseline.json"

# What a complete pass should touch. Each row is (label, table, what it proves).
PROBES = [
    ("routing recorded",      "agent_runs",
     "run_metis wrote a live row per specialist, so the dashboard can show work"),
    ("a preference learned",  "user_decisions",
     "a specialist recorded a standing decision — the thing that makes it grow"),
    ("the session kept",      "session_summaries",
     "the conversation itself was written down, not just its side effects"),
    ("self-critique",         "reflexion_log",
     "the improvement loop has something to consolidate"),
    ("episodic trace",        "episodic_memory",
     "what happened is recallable later, not only summarised"),
    ("improvement proposed",  "skill_improvement_proposals",
     "the system suggested a change to itself"),
]


def counts(con) -> dict:
    out = {}
    for _, table, _ in PROBES:
        try:
            out[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            out[table] = None
    # The delivery counter is the one that proves a specialist was actually
    # handed what it had previously learned, rather than merely invoked.
    try:
        out["_delivered"] = con.execute(
            "SELECT COALESCE(SUM(delivered),0) FROM user_decisions").fetchone()[0]
    except Exception:
        out["_delivered"] = None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true",
                    help="record a baseline before running the test")
    args = ap.parse_args()

    with connect(paths.db) as con:
        now = counts(con)

    if args.snapshot:
        SNAP.parent.mkdir(parents=True, exist_ok=True)
        SNAP.write_text(json.dumps(
            {"at": datetime.now().isoformat(timespec="seconds"), "counts": now},
            indent=2), encoding="utf-8")
        print(f"baseline written: {SNAP}")
        print(f"taken at {datetime.now():%Y-%m-%d %H:%M}")
        print("\nNow run the test prompts in the other client, then re-run this "
              "without --snapshot.")
        return 0

    if not SNAP.exists():
        print("No baseline found. Run with --snapshot BEFORE the test, otherwise "
              "there is nothing to compare against and a pass cannot be "
              "distinguished from a no-op.", file=sys.stderr)
        return 2

    base = json.loads(SNAP.read_text(encoding="utf-8"))
    before = base["counts"]

    print("=" * 72)
    print("  CROSS-CLIENT TEST — what actually landed")
    print("=" * 72)
    print(f"  baseline taken {base['at']}")
    print()
    print(f"  {'what it proves':<26}{'before':>9}{'after':>8}{'new':>7}   verdict")
    print("  " + "-" * 68)

    passed = failed = 0
    for label, table, _why in PROBES:
        b, a = before.get(table), now.get(table)
        if b is None or a is None:
            print(f"  {label:<26}{'—':>9}{'—':>8}{'—':>7}   table missing")
            failed += 1
            continue
        d = a - b
        ok = d > 0
        passed += ok
        failed += not ok
        print(f"  {label:<26}{b:>9}{a:>8}{d:>7}   {'✓' if ok else '✗ nothing new'}")

    bd, ad = before.get("_delivered"), now.get("_delivered")
    if bd is not None and ad is not None:
        dd = ad - bd
        print(f"  {'decisions delivered':<26}{bd:>9}{ad:>8}{dd:>7}   "
              f"{'✓' if dd > 0 else '✗ no specialist was handed its memory'}")
        passed += dd > 0
        failed += dd <= 0

    print("  " + "-" * 68)
    print(f"\n  {passed} probe(s) passed · {failed} found nothing new")
    if failed:
        print("\n  A probe that found nothing does not mean the assistant misbehaved —")
        print("  it means that step of the test did not reach the database. Check the")
        print("  matching prompt in the test sheet before concluding anything.")
        return 1
    print("\n  Every probe left a trace: routing, learning, recall and self-critique")
    print("  all reached storage from the other client.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
