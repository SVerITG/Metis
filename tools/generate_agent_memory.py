#!/usr/bin/env python3
"""generate_agent_memory.py — project standing decisions into native agent memory.

WHY THIS EXISTS
    A specialist only grows if it carries what it has learned into its next run.
    Two mechanisms can do that and each fails alone:

      the decisions table   queryable, rendered on the dashboard, merged between
                            computers, and reachable from the other client — but
                            only if the agent remembers to ask for it.

      native agent memory   injected into the agent's system prompt with no tool
                            call at all — but it is machine-local markdown, it
                            does not sync, and neither the dashboard nor the
                            other client can see it.

    So: the table is canonical, and this writes the projection. One writer, one
    truth, and the agent gets its context whether or not it thinks to look.

WHAT IT WRITES
    .claude/agent-memory/<slug>/MEMORY.md  for every agent in .claude/agents/

    The client reads roughly the first 200 lines / 25 KB of that file, so the
    budget is real. Decisions are ordered by what has most recently proved
    useful — applied first, then delivered, then newest — and anything that does
    not fit is not silently dropped: the file says how many were left and where
    to get them.

WHY THE FILE SAYS "DO NOT EDIT"
    Declaring `memory:` on an agent also gives it write access to this directory.
    An agent editing MEMORY.md would have its work overwritten on the next run of
    this script, which is a worse failure than not being able to write at all,
    because it looks like it worked. The header tells the agent where a
    preference actually belongs.

USAGE
    python3 tools/generate_agent_memory.py           # write all
    python3 tools/generate_agent_memory.py --check   # report, write nothing
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

from metis_mcp.config import paths          # noqa: E402
from metis_mcp.db import connect            # noqa: E402
from metis_mcp.tools.agent_memory import _ensure  # noqa: E402

AGENTS = ROOT / ".claude" / "agents"
OUT = ROOT / ".claude" / "agent-memory"

MAX_LINES = 190          # client reads ~200; leave headroom for the header
MAX_BYTES = 24_000       # client reads ~25 KB

# A HARD CAP ON THE SHARED BLOCK, and it is the most important number here.
#
# Project-wide decisions outnumber any single specialist's own by roughly ten to
# one. Letting them in unbounded fills the budget with rules the specialist did
# not need and pushes out the ones it did — which is the precise failure this
# whole attribution scheme exists to prevent: a flat list of preferences given to
# every agent is noise, and noise gets skipped.
#
# So the specialist's OWN decisions are written first and always fit; the shared
# block is a short tail of the ones that have most demonstrably done work. The
# rest stay one call away and the file says so.
MAX_SHARED = 18

HEADER = """# {title} — what this specialist has learned

<!-- GENERATED — do not edit. Regenerate: python3 tools/generate_agent_memory.py

     Editing this file does nothing: it is rebuilt from the standing-decisions
     table, which is the copy the dashboard renders and the copy that travels
     between computers. To record a preference so it survives, call
     record_decision(decision=..., category=..., agent_slug="{slug}", context=...)
     and it will appear here next time. -->

These are settled preferences. Apply them without being asked, and do not
re-litigate one without a new reason — if you do, say so explicitly.
"""


def rows_for(con, slug: str) -> tuple[list, list]:
    """(this specialist's decisions, project-wide decisions), best first.

    Ordering is by demonstrated usefulness rather than recency alone: something
    that has actually been applied outranks something merely delivered, which in
    turn outranks something that has only ever been written down.
    """
    superseded = {r[0] for r in con.execute(
        "SELECT supersedes FROM user_decisions WHERE supersedes IS NOT NULL")}
    order = ("ORDER BY COALESCE(hits,0) DESC, COALESCE(delivered,0) DESC, "
             "created_at DESC")
    mine = [dict(r) for r in con.execute(
        f"SELECT decision_id, category, decision, context, created_at, "
        f"COALESCE(hits,0) hits, COALESCE(delivered,0) delivered "
        f"FROM user_decisions WHERE COALESCE(agent_slug,'')=? {order}", (slug,))
        if r["decision_id"] not in superseded]
    shared = [dict(r) for r in con.execute(
        f"SELECT decision_id, category, decision, context, created_at, "
        f"COALESCE(hits,0) hits, COALESCE(delivered,0) delivered "
        f"FROM user_decisions WHERE COALESCE(agent_slug,'')='' {order}")
        if r["decision_id"] not in superseded]
    return mine, shared


def render(slug: str, title: str, mine: list, shared: list) -> tuple[str, int]:
    """Build the file, and report how many decisions had to be left out."""
    out = [HEADER.format(title=title, slug=slug)]
    written = 0
    dropped = 0

    def fits(block: str) -> bool:
        text = "\n".join(out + [block])
        return len(text.splitlines()) <= MAX_LINES and len(text.encode()) <= MAX_BYTES

    shared_over = max(0, len(shared) - MAX_SHARED)
    for heading, rows in ((f"## Decided for {slug}", mine),
                          ("## Project-wide", shared[:MAX_SHARED])):
        if not rows:
            continue
        if not fits(heading):
            dropped += len(rows)
            continue
        out.append("")
        out.append(heading)
        for r in rows:
            line = f"- **[{r['category'] or 'general'}]** {r['decision']}"
            if r["context"]:
                line += f"\n  <sub>{r['context']}</sub>"
            if fits(line):
                out.append(line)
                written += 1
            else:
                dropped += 1

    dropped += shared_over
    if dropped:
        out += ["", f"<sub>{dropped} further decision(s) did not fit this file's "
                    f"budget. They are not lost — ask for the full set with "
                    f"`get_agent_context(\"{slug}\")`.</sub>"]
    return "\n".join(out) + "\n", dropped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report what would be written, change nothing")
    args = ap.parse_args()

    slugs = sorted(p.stem for p in AGENTS.glob("*.md"))
    if not slugs:
        print("no agents found — nothing to project", file=sys.stderr)
        return 1

    with connect(paths.db) as con:
        _ensure(con)
        written = skipped = total_dropped = 0
        empty: list[str] = []
        print(f"{'specialist':<30} {'own':>4} {'shared':>7} {'elsewhere':>10}  file")
        print("-" * 78)
        for slug in slugs:
            mine, shared = rows_for(con, slug)
            title = slug.replace("-", " ").title()
            body, dropped = render(slug, title, mine, shared)
            total_dropped += dropped
            if not mine and not shared:
                empty.append(slug)
            target = OUT / slug / "MEMORY.md"
            if args.check:
                state = "would write" if not target.exists() or \
                    target.read_text(encoding="utf-8") != body else "current"
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_text(encoding="utf-8") == body:
                    state = "unchanged"
                    skipped += 1
                else:
                    target.write_text(body, encoding="utf-8")
                    state = "written"
                    written += 1
            print(f"{slug:<30} {len(mine):>4} "
                  f"{min(len(shared), MAX_SHARED):>7} {dropped:>10}  {state}")

    print("-" * 78)
    print(f"{len(slugs)} specialist(s) · {written} written · {skipped} unchanged")
    print("'elsewhere' is by design, not loss: the shared block is capped at "
          f"{MAX_SHARED} so a specialist's own preferences own the budget. The "
          "rest stay one get_agent_context call away.")
    if empty:
        print(f"\n{len(empty)} specialist(s) carry NO decisions at all — they cannot "
              f"grow until something is recorded against them:")
        print("   " + ", ".join(empty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
