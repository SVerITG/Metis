#!/usr/bin/env python3
"""
Agent contract test — static analysis of all Metis agents.

Checks that every agent in the registry is structurally complete and wired
for logging. Run before any release or after adding/removing agents.

Usage:
    python3 tests/functional/test_agent_contracts.py
    python3 tests/functional/test_agent_contracts.py --json   # machine-readable

Exit codes:
    0 — all agents pass
    1 — one or more FAIL-level issues found
    2 — no agents found (registry missing or empty)
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RC_ROOT = Path(os.environ.get("METIS_RC_ROOT", Path(__file__).parents[2]))
REGISTRY = RC_ROOT / "system" / "config" / "agent-registry.json"
AGENTS_DIR = RC_ROOT / "agents"
SKILLS_DIR = RC_ROOT / ".claude" / "skills"
DB_PATH = RC_ROOT / "system" / "app" / "data" / "metis.sqlite"

# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return data.get("agents", [])


def load_run_map() -> dict[str, dict]:
    """Return {agent_slug: {runs: int, last_run: str}} from the DB."""
    if not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT agent_slug, COUNT(*) as runs, MAX(created_at) as last_run "
            "FROM agent_runs GROUP BY agent_slug"
        ).fetchall()
        conn.close()
        return {r[0]: {"runs": r[1], "last_run": (r[2] or "")[:10]} for r in rows}
    except Exception:
        return {}


def check_agent(slug: str, run_map: dict) -> dict:
    """Run all contract checks for one agent. Returns a result dict."""
    issues: list[tuple[str, str]] = []  # (level, message)

    agent_dir = AGENTS_DIR / slug
    skill_path = SKILLS_DIR / slug / "skill.md"
    retired_path = agent_dir / "RETIRED.md"

    # 1 — skill.md must exist (FAIL: Metis can't dispatch without it)
    if not skill_path.exists():
        issues.append(("FAIL", "skill.md missing — Metis cannot dispatch this agent"))

    # 2 — skill.md must contain log_agent_run (FAIL: run will never be recorded)
    elif "log_agent_run" not in skill_path.read_text(encoding="utf-8"):
        issues.append(("FAIL", "skill.md has no log_agent_run call — runs will never be recorded"))

    # 3 — skill.md must have a model line (WARN: falls back to default, may be expensive)
    else:
        content = skill_path.read_text(encoding="utf-8")
        if "model:" not in content:
            issues.append(("WARN", "skill.md has no model: line — will use default model (cost risk)"))

    # 4 — system-prompt.md must exist unless agent is retired (FAIL: no persona)
    if not retired_path.exists():
        if not (agent_dir / "system-prompt.md").exists():
            issues.append(("FAIL", "system-prompt.md missing — agent has no persona"))

    # 5 — contract.md should exist (WARN: no authority constraints)
    if not (agent_dir / "contract.md").exists() and not retired_path.exists():
        issues.append(("WARN", "contract.md missing — agent has no authority constraints"))

    # 6 — run coverage (WARN: never been invoked)
    stats = run_map.get(slug)
    run_count = stats["runs"] if stats else 0
    last_run = stats["last_run"] if stats else ""

    if not retired_path.exists():
        if run_count == 0:
            issues.append(("WARN", "never run — zero entries in agent_runs"))
        else:
            # Check if stale (no run in last 90 days)
            if last_run:
                try:
                    last_dt = datetime.fromisoformat(last_run)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    age = datetime.now(timezone.utc) - last_dt
                    if age > timedelta(days=90):
                        issues.append(("WARN", f"last run {last_run} is more than 90 days ago"))
                except ValueError:
                    pass

    # Determine overall status
    levels = [i[0] for i in issues]
    if "FAIL" in levels:
        status = "FAIL"
    elif "WARN" in levels:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "slug": slug,
        "status": status,
        "retired": retired_path.exists(),
        "run_count": run_count,
        "last_run": last_run,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

STATUS_ICON = {"PASS": "✅", "WARN": "🟡", "FAIL": "🔴", "RETIRED": "⚫"}


def render_text(results: list[dict], run_map: dict) -> int:
    """Print human-readable report, return exit code."""
    total = len(results)
    retired = sum(1 for r in results if r["retired"])
    active = total - retired
    fail = sum(1 for r in results if r["status"] == "FAIL")
    warn = sum(1 for r in results if r["status"] == "WARN" and not r["retired"])
    passed = sum(1 for r in results if r["status"] == "PASS" and not r["retired"])
    never_run = sum(1 for r in results if not r["retired"] and r["run_count"] == 0)

    print(f"\n{'='*68}")
    print(f"  METIS AGENT CONTRACT TEST — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*68}")
    print(f"  {total} agents total · {retired} retired · {active} active")
    print(f"  ✅ {passed} pass · 🟡 {warn} warn · 🔴 {fail} fail")
    print(f"  {active - never_run}/{active} active agents have been invoked at least once")
    print(f"{'='*68}\n")

    # Group by status for readability
    for status_filter in ("FAIL", "WARN", "PASS"):
        group = [r for r in results if r["status"] == status_filter and not r["retired"]]
        if not group:
            continue
        icon = STATUS_ICON[status_filter]
        print(f"{icon}  {status_filter} ({len(group)} agents)")
        print("-" * 50)
        for r in group:
            run_info = f"{r['run_count']} run{'s' if r['run_count'] != 1 else ''}"
            if r["last_run"]:
                run_info += f" · last {r['last_run']}"
            print(f"  /{r['slug']:28s}  {run_info}")
            for level, msg in r["issues"]:
                marker = "  🔴" if level == "FAIL" else "  🟡"
                print(f"    {marker} {msg}")
        print()

    # Retired
    retired_agents = [r for r in results if r["retired"]]
    if retired_agents:
        print(f"⚫  RETIRED ({len(retired_agents)} agents — excluded from checks)")
        print("-" * 50)
        for r in retired_agents:
            print(f"  /{r['slug']}")
        print()

    print(f"{'='*68}")
    if fail > 0:
        print(f"  ❌ {fail} agent(s) FAILED contract check — runs will not be recorded")
        print(f"     Fix these before the next release.")
    elif warn > 0:
        print(f"  ⚠️  All agents structurally complete. {warn} warning(s) — review above.")
    else:
        print(f"  ✅ All {active} active agents pass contract checks.")

    coverage_pct = round((active - never_run) / active * 100) if active else 0
    if never_run > 0:
        print(f"  ⚠️  {never_run} agent(s) have never been invoked — use /metis to warm them up.")
    else:
        print(f"  ✅ Agent coverage: {coverage_pct}% — all active agents have at least one run.")
    print(f"{'='*68}\n")

    return 1 if fail > 0 else 0


def render_json(results: list[dict]) -> int:
    fail = sum(1 for r in results if r["status"] == "FAIL")
    print(json.dumps(results, indent=2))
    return 1 if fail > 0 else 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Metis agent contract test")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    agents = load_registry()
    if not agents:
        print("ERROR: No agents found. Is agent-registry.json present?", file=sys.stderr)
        sys.exit(2)

    # Also check for agents in agents/ dir that aren't in the registry
    registry_slugs = {a["slug"] for a in agents}
    dir_slugs = {d.name for d in AGENTS_DIR.iterdir() if d.is_dir()} if AGENTS_DIR.exists() else set()
    unregistered = dir_slugs - registry_slugs
    for slug in sorted(unregistered):
        # Only flag if not retired
        if not (AGENTS_DIR / slug / "RETIRED.md").exists():
            agents.append({"slug": slug, "_unregistered": True})

    run_map = load_run_map()
    results = [check_agent(a["slug"], run_map) for a in agents]

    # Flag unregistered agents
    unregistered_set = {a["slug"] for a in agents if a.get("_unregistered")}
    for r in results:
        if r["slug"] in unregistered_set:
            r["issues"].insert(0, ("FAIL", "agent exists in agents/ dir but is missing from agent-registry.json — invisible in dashboard"))
            r["status"] = "FAIL"
    # Sort: FAIL first, then WARN, then PASS, then RETIRED
    order = {"FAIL": 0, "WARN": 1, "PASS": 2}
    results.sort(key=lambda r: (order.get(r["status"], 3), r["retired"], r["slug"]))

    if args.json:
        sys.exit(render_json(results))
    else:
        sys.exit(render_text(results, run_map))


if __name__ == "__main__":
    main()
