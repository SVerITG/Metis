#!/usr/bin/env python3
"""mine_decisions.py — promote standing decisions out of session summaries.

THE LOGIC NO LONGER LIVES HERE. It moved into
`metis_mcp.tools.decisions_ledger.promote_standing_decisions()` on 2026-09-14,
because this file being a manual CLI was itself the bug: the promotion step ran
only when someone remembered to type the command, so the pipeline from "real
work happened" to "an agent knows it" was complete in every part except the one
that had to be triggered by hand. It is now called by the dashboard's evening
job and by the MCP server's opportunistic learning loop as well as from here.

This script stays as the way to run it deliberately and see what it did.

USAGE
    python3 tools/mine_decisions.py --dry-run
    python3 tools/mine_decisions.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "system" / "mcp-server" / "src"))
os.environ.setdefault("METIS_RC_ROOT", str(_ROOT))

from metis_mcp.tools.decisions_ledger import promote_standing_decisions  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    r = promote_standing_decisions(dry_run=args.dry_run)

    print(f"  raw entries            : {r['raw']:,}")
    print(f"  unique strings         : {r['unique']:,}")
    print(f"  decision-shaped, new   : {r['promoted']}")
    print(f"  {'would write' if args.dry_run else 'WROTE'}            : "
          f"{r['promoted'] if args.dry_run else r['written']}")
    print()
    for a, n in sorted(r["by_agent"].items(), key=lambda kv: -kv[1]):
        print(f"    {n:4d}  {a}")
    print()
    print(f"  user_decisions now holds {r['total_rows']:,} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
