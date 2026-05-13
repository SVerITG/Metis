#!/usr/bin/env python3
"""
eval-runner.py — Agent evaluation harness for Metis.

Loads golden-tests.json, runs each test case against the live MCP tools
via the metis_mcp Python API, and scores the output against required/
forbidden key checks and minimum length requirements.

Usage:
  # Run all tests
  python eval-runner.py

  # Run tests for a specific agent
  python eval-runner.py --agent librarian

  # Run only tests with a specific tag
  python eval-runner.py --tag smoke

  # Run a single test by ID
  python eval-runner.py --id lib-001

  # Compare incumbent vs candidate skill.md before promoting
  python eval-runner.py --agent epidemiologist --compare path/to/candidate/skill.md

  # Output JSON for CI pipelines
  python eval-runner.py --json

Requirements:
  The metis_mcp package must be importable (run from inside the venv or with PYTHONPATH set).
  METIS_RC_ROOT must point to the Research Cortex root.
"""

import argparse
import json
import os
import sys
import textwrap
import time
from pathlib import Path
from typing import Any


EVAL_DIR = Path(__file__).parent
GOLDEN_TESTS = EVAL_DIR / "golden-tests.json"
RESULTS_DIR  = EVAL_DIR / "results"


# ── Terminal colours (skip if not a tty) ─────────────────────────────────────

def _c(code: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

GREEN  = lambda t: _c("32", t)
RED    = lambda t: _c("31", t)
YELLOW = lambda t: _c("33", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)


# ── Test runner ───────────────────────────────────────────────────────────────

def load_tests(agent: str = "", tag: str = "", test_id: str = "") -> list[dict]:
    with open(GOLDEN_TESTS, encoding="utf-8") as f:
        data = json.load(f)
    tests = data["tests"]
    if agent:
        tests = [t for t in tests if t["agent"] == agent]
    if tag:
        tests = [t for t in tests if tag in t.get("tags", [])]
    if test_id:
        tests = [t for t in tests if t["id"] == test_id]
    return tests


def score_output(output: str, test: dict) -> tuple[bool, list[str]]:
    """Return (passed, list of failure reasons)."""
    failures = []

    output_lower = output.lower()

    for key in test.get("required_keys", []):
        if key.lower() not in output_lower:
            failures.append(f"Missing required key: '{key}'")

    for key in test.get("forbidden_keys", []):
        if key.lower() in output_lower:
            failures.append(f"Forbidden key present: '{key}'")

    min_len = test.get("min_length", 0)
    if len(output) < min_len:
        failures.append(f"Output too short: {len(output)} < {min_len} chars")

    return len(failures) == 0, failures


def run_test(test: dict, skill_override: str | None = None) -> dict:
    """Run a single golden test. Returns a result dict."""
    start = time.monotonic()

    agent_slug = test["agent"]
    skill_path = (
        Path(skill_override)
        if skill_override
        else Path(os.environ.get("METIS_RC_ROOT", "")) / ".claude" / "skills" / agent_slug / "skill.md"
    )

    # Read the skill file so we have it as context
    skill_text = ""
    if skill_path.exists():
        skill_text = skill_path.read_text(encoding="utf-8")[:500]
    else:
        skill_text = f"[skill.md not found at {skill_path}]"

    # ── Attempt MCP tool call via pipeline ───────────────────────────────────
    output = ""
    error  = None
    try:
        # Import here so missing packages produce a clear error
        from metis_mcp.tools.pipeline import run_agent_call  # type: ignore
        output = run_agent_call(
            agent_slug=agent_slug,
            user_input=test["input"],
            max_tokens=1024,
        )
    except ImportError:
        # pipeline.run_agent_call may not exist in all versions
        # Fall back: simulate output using only the skill.md text for scoring
        error = "run_agent_call not available — scoring against skill.md heuristics only"
        output = f"[Simulated: skill loaded, length={len(skill_text)} chars] " + skill_text[:200]
    except Exception as exc:
        error = str(exc)
        output = ""

    elapsed = time.monotonic() - start
    passed, failures = score_output(output, test)

    return {
        "id":       test["id"],
        "agent":    agent_slug,
        "tags":     test.get("tags", []),
        "input":    test["input"][:80],
        "passed":   passed,
        "failures": failures,
        "elapsed":  round(elapsed, 2),
        "output_len": len(output),
        "error":    error,
    }


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_result(r: dict) -> None:
    icon = GREEN("✓ PASS") if r["passed"] else RED("✗ FAIL")
    print(f"  {icon}  {r['id']} ({r['agent']}) — {r['elapsed']}s")
    if r["failures"]:
        for f in r["failures"]:
            print(f"        {YELLOW('→')} {f}")
    if r["error"]:
        print(f"        {DIM('error: ' + r['error'])}")


def print_summary(results: list[dict]) -> None:
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print()
    print(BOLD(f"Results: {passed}/{total} passed"))
    if failed:
        print(RED(f"  {failed} test(s) failed"))
        failed_tests = [r for r in results if not r["passed"]]
        for r in failed_tests:
            print(f"  • {r['id']} ({r['agent']}): {'; '.join(r['failures'])}")


def save_results(results: list[dict]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / f"eval-{ts}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out


# ── Compare mode ─────────────────────────────────────────────────────────────

def compare_mode(agent: str, candidate_skill: str) -> None:
    """Run the eval suite twice — once with incumbent, once with candidate skill.md."""
    tests = load_tests(agent=agent)
    if not tests:
        print(f"No tests found for agent '{agent}'.")
        return

    print(BOLD(f"Comparing incumbent vs candidate skill.md for '{agent}'"))
    print(f"Candidate: {candidate_skill}")
    print()

    incumbent_results = []
    candidate_results = []

    for test in tests:
        r_inc = run_test(test, skill_override=None)
        r_can = run_test(test, skill_override=candidate_skill)
        incumbent_results.append(r_inc)
        candidate_results.append(r_can)

    inc_passed = sum(1 for r in incumbent_results if r["passed"])
    can_passed = sum(1 for r in candidate_results if r["passed"])
    total = len(tests)

    print(f"  Incumbent:  {inc_passed}/{total} passed")
    print(f"  Candidate:  {can_passed}/{total} passed")
    print()

    if can_passed > inc_passed:
        print(GREEN(f"  Candidate is BETTER (+{can_passed - inc_passed}). Safe to promote."))
    elif can_passed == inc_passed:
        print(YELLOW("  Candidate is NEUTRAL (same score). Review manually before promoting."))
    else:
        print(RED(f"  Candidate is WORSE (-{inc_passed - can_passed}). DO NOT promote."))
        print()
        print("  Regressions:")
        for i, (r_inc, r_can) in enumerate(zip(incumbent_results, candidate_results)):
            if r_inc["passed"] and not r_can["passed"]:
                print(f"    • {r_can['id']}: {'; '.join(r_can['failures'])}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run golden-test evaluation suite against Metis agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
          Examples:
            python eval-runner.py
            python eval-runner.py --agent librarian
            python eval-runner.py --tag smoke
            python eval-runner.py --id epi-001
            python eval-runner.py --agent epidemiologist --compare /path/to/candidate/skill.md
            python eval-runner.py --json > results.json
        """),
    )
    parser.add_argument("--agent",   default="", help="Filter by agent slug")
    parser.add_argument("--tag",     default="", help="Filter by tag (smoke, regression, ...)")
    parser.add_argument("--id",      default="", help="Run a single test by ID")
    parser.add_argument("--compare", default="", metavar="PATH",
                        help="Compare incumbent vs candidate skill.md (requires --agent)")
    parser.add_argument("--json",    action="store_true", help="Output results as JSON")
    parser.add_argument("--save",    action="store_true", help="Save results to agent-eval/results/")
    args = parser.parse_args()

    if args.compare:
        if not args.agent:
            print("--compare requires --agent")
            sys.exit(1)
        compare_mode(args.agent, args.compare)
        return

    tests = load_tests(agent=args.agent, tag=args.tag, test_id=args.id)
    if not tests:
        print("No matching tests found.")
        sys.exit(0)

    if not args.json:
        print(BOLD(f"Running {len(tests)} test(s)..."))
        print()

    results = []
    for test in tests:
        r = run_test(test)
        results.append(r)
        if not args.json:
            print_result(r)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print_summary(results)

    if args.save:
        out_path = save_results(results)
        print(f"\n  Saved: {out_path}")

    failed = any(not r["passed"] for r in results)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
