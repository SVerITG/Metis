#!/usr/bin/env python3
"""audit_routing.py — is the agent routing table doing anything?

WHY THIS EXISTS
    The 2026-08-25 hand-off flagged "127 rules exist, only 18 have ever matched"
    and read it as ~85% of the table being decoration. That reading invites
    deleting rules. Before deleting anything the question has to be split,
    because the two causes call for OPPOSITE fixes:

      never-arrived  the requests a rule describes are simply not being made
      shadowed       the requests DO arrive, but an earlier rule matches first
                     and `_parse_intent_stage` breaks on the first match, so the
                     later rule can never be credited even when it applies

    And a third possibility the hand-off did not consider, which turns out to
    dominate: the routing pipeline itself has barely run. `hits` increments only
    inside _parse_intent_stage — i.e. only when a request goes through
    run_metis. Direct agent calls and ordinary Claude Code conversation never
    touch it.

WHAT IT CHECKS
    1. COVERAGE      rules, how many ever matched, and total hits across all of
                     them. Total hits is the denominator everything else needs:
                     with break-on-first-match, N routings can credit at most N
                     rules, so "17 of 126 matched" means nothing until you know
                     whether N was 34 or 34,000.
    2. EXERCISE      total hits against recorded sessions and agent runs, which
                     says whether the table is wrong or merely unused.
    3. SHADOWING     structural, not statistical. Precedence is
                     (priority ASC, user-before-seed, length DESC). If keyword A
                     is reachable only through text that also contains keyword B,
                     and B outranks A, then A is UNREACHABLE by construction —
                     no amount of traffic will ever credit it.
    4. AGENT REACH   which specialists the table can route to at all. A rule set
                     that cannot name an agent is a gap no traffic will reveal.

Usage:  python3 tools/audit_routing.py [--json]
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter

DB = os.path.expanduser("~/.local/share/metis/metis.sqlite")


def _rows(con):
    return con.execute(
        "SELECT rule_id, keyword, agent_slug, task_type, priority, match_mode, "
        "source, scope, hits FROM agent_routing_rules"
    ).fetchall()


def _precedence(r):
    """Mirror _load_routing_rules' ORDER BY, independently — so drift between the
    router and this audit is detectable rather than silently shared."""
    _id, kw, _ag, _tt, prio, _mm, src, _sc, _h = r
    return (prio if prio is not None else 100, 0 if src == "user" else 1, -len(kw))


def _implies(a_kw, b_kw):
    """Does matching keyword `a_kw` guarantee also matching `b_kw`?

    _kw_match is a LEADING word-boundary search: re.search(r"\\b" + kw). So b is
    implied by a when b occurs in a at a word start."""
    return re.search(r"\b" + re.escape(b_kw), a_kw) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(DB):
        print(f"database not found: {DB}", file=sys.stderr)
        return 2
    con = sqlite3.connect(DB)
    rows = _rows(con)
    if not rows:
        print("agent_routing_rules is empty — routing has never been seeded.")
        return 1

    active = [r for r in rows if (r[7] or "always") == "always"]
    order = sorted(active, key=_precedence)
    total_hits = sum(r[8] or 0 for r in rows)
    matched = [r for r in rows if (r[8] or 0) > 0]

    # 3. structural shadowing
    shadowed = []
    for i, r in enumerate(order):
        kw = r[1]
        for earlier in order[:i]:
            if earlier[2] == r[2]:
                continue  # same agent — being shadowed changes no outcome
            if _implies(kw, earlier[1]):
                shadowed.append((r, earlier))
                break

    # A uniform hit distribution is the signature of a HARNESS, not of use.
    # Organic traffic is Zipfian — a few keywords dominate and most trail off.
    # Every matched rule sharing one identical count means each was exercised the
    # same number of times, which is what tests/functional/routing_eval.py does
    # and what a person never does.
    hit_values = sorted({r[8] for r in matched})
    synthetic = len(matched) > 3 and len(hit_values) == 1

    def _count(sql):
        try:
            return con.execute(sql).fetchone()[0]
        except sqlite3.Error:
            return None

    sessions = _count("SELECT COUNT(*) FROM session_summaries")
    runs = _count("SELECT COUNT(*) FROM agent_runs")

    reachable = {r[2] for r in active}
    try:
        known = {a[0] for a in con.execute(
            "SELECT DISTINCT agent_slug FROM agent_runs WHERE agent_slug IS NOT NULL")}
    except sqlite3.Error:
        known = set()

    report = {
        "rules_total": len(rows),
        "rules_active": len(active),
        "rules_ever_matched": len(matched),
        "total_hits": total_hits,
        "sessions": sessions,
        "agent_runs": runs,
        "shadowed": [{"rule": r[1], "agent": r[2], "blocked_by": e[1],
                      "blocked_by_agent": e[2]} for r, e in shadowed],
        "agents_reachable": sorted(reachable),
        "agents_seen_but_unreachable": sorted(known - reachable),
        "hits_by_agent": dict(Counter({a: h for a, h in (
            (r[2], sum(x[8] for x in matched if x[2] == r[2])) for r in matched)
        }).most_common()),
        "by_source": dict(Counter(r[6] or "seed" for r in rows)),
        "traffic_looks_synthetic": synthetic,
        "distinct_hit_values": hit_values,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    W = 74
    print("=" * W)
    print("  Agent routing audit")
    print("=" * W)
    print("\n1. COVERAGE")
    print(f"   rules            : {len(rows)} ({len(active)} active)")
    print(f"   ever matched     : {len(matched)}")
    print(f"   TOTAL HITS       : {total_hits}")
    if total_hits:
        print(f"\n   Break-on-first-match means {total_hits} routings can credit at most")
        print(f"   {total_hits} distinct rules. {len(matched)} were credited, so the ceiling —")
        print(f"   not rule quality — explains most of the {len(rows) - len(matched)} that were not.")

    if synthetic:
        print(f"\n   !! Every matched rule has exactly {hit_values[0]} hits. A uniform")
        print("      distribution is the signature of a test harness, not of use —")
        print("      organic traffic is Zipfian. Treat these hits as SYNTHETIC:")
        print("      real routing traffic is effectively zero.")

    print("\n2. EXERCISE")
    print(f"   recorded sessions: {sessions}")
    print(f"   agent runs       : {runs}")
    if sessions:
        print(f"   routing ran on   : {total_hits}/{sessions} sessions "
              f"({100.0 * total_hits / sessions:.1f}%)")
        print("   -> `hits` only increments inside the run_metis pipeline. Direct agent")
        print("      calls and ordinary conversation never touch it, so a low number here")
        print("      measures PIPELINE USE, not rule quality.")

    print(f"\n3. STRUCTURAL SHADOWING  ({len(shadowed)} unreachable by construction)")
    if not shadowed:
        print("   none — every rule is reachable by some request that reaches it first.")
    for r, e in shadowed:
        print(f"   {r[1]!r} -> {r[2]}")
        print(f"       always caught first by {e[1]!r} -> {e[2]}")

    print("\n4. AGENT REACH")
    print(f"   agents reachable by keyword : {len(reachable)}")
    if report["agents_seen_but_unreachable"]:
        print(f"   ran but NOT reachable       : {len(report['agents_seen_but_unreachable'])}")
        for s in report["agents_seen_but_unreachable"]:
            print(f"       {s}")
        print("   -> these are reached only by the semantic backstop or a direct call.")

    print(f"\n   hits by agent  : {report['hits_by_agent']}")
    print(f"   rules by source: {report['by_source']}")
    print("\n" + "=" * W)
    print("  VERDICT")
    print("=" * W)
    if synthetic:
        print("  Do NOT delete rules on this evidence, and do not read the hit counts")
        print("  as usage. They are uniform, so they came from the eval harness. The")
        print("  finding is not that rules are wrong — it is that the routing PIPELINE")
        print("  is not on the path real requests take. Fix that before judging rules.")
        if report["agents_seen_but_unreachable"]:
            print(f"\n  The one substantive gap: {len(report['agents_seen_but_unreachable'])} agents that have actually run")
            print("  cannot be reached by any keyword. Those depend entirely on the")
            print("  semantic backstop, which is a real coverage hole worth closing.")
    elif total_hits < len(rows):
        print(f"  Do NOT delete rules on this evidence. With only {total_hits} routings ever,")
        print("  most rules have never had the CHANCE to match. The table is untested,")
        print(f"  not disproven. The actionable finding is the {len(shadowed)} structurally")
        print("  shadowed rule(s) above — those are unreachable regardless of traffic.")
    else:
        print("  Traffic is sufficient to judge rule quality; unmatched rules are")
        print("  candidates for review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
