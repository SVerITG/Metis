#!/usr/bin/env python3
"""test_routing_regression.py — the labelled request set the router must satisfy.

WHY THIS FILE EXISTS
    The 2026-09-14 audit found the routing table had been tuned by argument
    rather than by measurement: priorities were assigned on an intuition about
    which agent was "more specialist", and nobody could tell afterwards whether
    a change had helped. Re-pricing 200+ rules by hand is exactly the kind of
    bulk edit that produces a table nobody can reason about later, so the
    re-pricing ships with the cases it was meant to fix.

    Each case is a request the audit actually sent, with the agent that should
    own it. Run this before and after any routing change.

USAGE
    python3 tools/test_routing_regression.py          # pass/fail summary
    python3 tools/test_routing_regression.py -v       # show every case
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "system" / "mcp-server" / "src"))
os.environ.setdefault("METIS_RC_ROOT", str(_ROOT))

# (request, expected_agent). The expectation is that the agent APPEARS in the
# routed set — not that it leads — because a real request often warrants two
# perspectives and the audit's complaint was absence, not ordering.
CASES: list[tuple[str, str]] = [
    # — collisions the old priority scheme got backwards —
    ("Which spatial scan model should I use, space-time permutation or discrete Poisson?",
     "epidemiologist"),
    ("Help me interpret the ICC and the BLUPs from my multilevel model",
     "methods-coach"),
    ("Is there one consistent learning progression across my four courses?",
     "course-builder"),
    ("Build a new filter-panel UI component for the dashboard",
     "frontend-designer-builder"),
    ("Audit the endemic-rate colour coding for accessibility",
     "design-auditor"),
    ("Fix the course launcher bug so a partial re-render can't roll back progress",
     "software-engineer"),
    ("Is Article 1 tracked yet, and what should its PLANNING.md say?",
     "research-architect"),
    # — agents that had no reachable phrasing at all —
    ("Verify that Article 4's numbers are internally consistent and flag unsupported claims",
     "critic"),
    ("Please act as a critic and review whether this claim is supported by the evidence",
     "critic"),
    ("Is 3.6% loss to follow-up concerning by surveillance standards?",
     "epidemiologist"),
    ("Add a context overlay file for the research architect agent",
     "rc-builder"),
    ("I need a title-slide background graphic for the diagnostics course",
     "presentation-maker"),
    ("Draft a job description for a data-manager hire",
     "hr-talent"),
    ("Consolidate today's session notes into a memory entry",
     "memory-curator"),
    ("Untrack .venv_kb and r_libs from git safely before merging",
     "software-engineer"),
    ("Map the spatial scan foci against the cross-border zones",
     "visualization-maker"),
    # — requests the old table sent to the wrong domain —
    ("Find the agency situation reports I should cite in the Discussion",
     "librarian"),
    ("Fetch the full text of that paper and pull out a clean methods section",
     "content-harvester"),
    ("Scan for breaking agency and programme announcements this week",
     "news-radar"),
    # — requests that were already right and must STAY right —
    ("Tighten the prose in Article 4's Discussion",
     "writing-partner"),
    ("What did we agree with the programme about the rollout timeline?",
     "meeting-memory"),
    ("Should the risk-mapping article and the clustering article stay separate?",
     "phd-architect"),
    ("How is the DHIS2 tracker API structured for the passive-screening data?",
     "dhis2-expert"),
    ("Do a commit scan and a rollback plan before I merge the dashboard",
     "release-coordinator"),
    ("Scaffold a new grant-writer agent folder",
     "builder"),
    ("Give me a 12-month plan from finishing the thesis to a postdoc",
     "career-coach"),
    ("Make me a 10-slide quarterly-review deck for the programme",
     "presentation-maker"),
    ("Review Module 5's learning objectives and assessment alignment",
     "course-builder"),
    ("Profile this CSV export and tell me about missing values and duplicates",
     "data-analyst"),

    # — the two statistics agents must stay apart —
    #
    # The audit recommended MERGING biostatistician into methods-coach: their
    # capability lists both claimed multilevel models and power, and which one a
    # request reached was decided by the priority numbers rather than by the
    # question. The merge was made conditional on re-pricing failing to separate
    # them, and re-pricing separated them cleanly — moving "sample size" and
    # "power calculation" to methods-coach removed the only genuine overlap, and
    # what biostatistician keeps is computational-statistics vocabulary that
    # means nothing else.
    #
    # So the merge was NOT done, and these twelve cases are the evidence for that
    # decision. If a future re-pricing re-breaks the separation, this is where it
    # shows up — otherwise the argument for merging would quietly become true
    # again with nobody watching.
    ("Write a simulation study to check the estimator's coverage", "biostatistician"),
    ("Run a Monte Carlo to see how the bootstrap behaves at n=40", "biostatistician"),
    ("Package these functions as an R package for CRAN", "biostatistician"),
    ("Compute a parametric bootstrap confidence interval", "biostatistician"),
    ("What tolerance interval should I report for the assay?", "biostatistician"),
    ("Fit a dose-response curve and report the ED50", "biostatistician"),
    ("Which regression should I use for count data with overdispersion?", "methods-coach"),
    ("Help me interpret the ICC and random effects in my multilevel model", "methods-coach"),
    ("Is a Bayesian or frequentist approach better for this spatial model?", "methods-coach"),
    ("What sample size do I need to detect a 20% difference?", "methods-coach"),
    ("Should I use propensity score matching or adjustment here?", "methods-coach"),
    ("How do I choose between logistic regression and survival analysis?", "methods-coach"),
]

# Agents that must NEVER appear in a routing result: they are retired, and two of
# them cannot be dispatched by the Agent tool at all. A rule pointing at one of
# these fails at the point of use, far from its cause.
MUST_NOT_ROUTE = {
    "ux-engineer", "edu-expert", "learning-architect",
    "news-aggregator", "learning-coach", "metis-self-reflexion", "metis-update",
    "metis-audit-features", "metis-audit-install", "metis-audit-memory",
    "metis-audit-security", "metis-audit-ui", "metis-audit-vision",
    "metis-audit-workflow",
}



# ── The original 35-agent evaluation, one request per agent ──────────────────
#
# These are the requests that started the whole audit: one per specialist, each
# phrased as the researcher would actually type it. The first run of this set
# found 14 agents that were never reached at all. Kept here so that number can
# never quietly grow again — a specialist that becomes unreachable fails a test
# instead of just going quiet.
CASES += [
    ("What's new in NTD policy this week?", "news-radar"),
    ("Generate STROBE flashcards for Article 4", "course-builder"),
    ("What's needed before merging the cache format change to the server?", "release-coordinator"),
    ("Is dashboard navigation intuitive, any friction before the demo?", "frontend-designer-builder"),
    ("Is this link safe, it looks like a phishing attempt", "cybersecurity"),
    ("Does this Excel file contain patient data I should not share?", "data-guardian"),
    ("Fix a launcher bug so a partial re-render can't roll back a learner's progress", "software-engineer"),
]


# ── The two dashboard agents must stay apart ─────────────────────────────────
#
# `dashboard-engineer` was retired on 2026-09-14 and RESTORED on 2026-09-15 at the
# researcher's instruction. The retirement had rested on the other agent's prompt
# claiming to replace it; its own prompt opens "You are not a generic frontend
# builder", and it carries a HAT-dashboard context file nothing else has.
#
# They share a stack, so the stack cannot separate them. The question does: "does
# this look right" is design, "is this the right indicator over the right
# denominator" is epidemiology. These cases hold that line — if a future tidy-up
# merges the vocabularies again, this is where it shows.
CASES += [
    ("Is the positivity rate panel using the right denominator?", "dashboard-engineer"),
    ("Add a coverage gap indicator to the surveillance dashboard", "dashboard-engineer"),
    ("Build a data quality panel for the passive screening data", "dashboard-engineer"),
    ("This dashboard tab renders a blank panel, the spinner never resolves", "dashboard-engineer"),
    ("The spacing and typography on this panel feel wrong", "frontend-designer-builder"),
    ("Pick a palette for the new design system", "frontend-designer-builder"),
    ("This looks ugly, the formatting is inconsistent", "frontend-designer-builder"),
]

# ── Follow-ups that name no domain at all ────────────────────────────────────
#
# Measured 2026-09-15: the researcher's real UI requests reached the design
# specialist ZERO times out of nine, because a follow-up carries its subject in
# the CONVERSATION, not in the sentence — "still ugly", "less loss of space".
# These run against a session that has already been routed once, and check that
# the subject holds. They are the reason `_sticky_agent` exists.
STICKY_CASES: list[tuple[str, str]] = [
    ('Redo "What needs you today" its not well organized and not inspiring', "frontend-designer-builder"),
    ("yes its collapsed but still ugly", "frontend-designer-builder"),
    ("the formatting between the three boxes needs to be the same, less loss of space", "frontend-designer-builder"),
    ("put the sources to the right side of the text as there is a lot of space", "frontend-designer-builder"),
    ("every item should start with its name and behind it are icons", "frontend-designer-builder"),
    ("apply same formatting also to where you left off as there is a lot of empty space", "frontend-designer-builder"),
]
STICKY_SEED = "Build a new filter-panel UI component for the dashboard frontend"

# A subject the researcher genuinely changed to must BREAK the stickiness rather
# than inherit it — otherwise one routed turn captures the rest of the session.
STICKY_BREAKS: list[tuple[str, str]] = [
    ("Find the agency situation reports I should cite in the Discussion", "librarian"),
    ("Run a Monte Carlo to check the estimator's coverage", "biostatistician"),
    ("What did we agree with the programme about the rollout timeline?", "meeting-memory"),
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    from metis_mcp.tools.pipeline import _parse_intent_stage

    passed, failed = 0, []
    for request, expected in CASES:
        intent = _parse_intent_stage(request, "")
        agents = intent["agents"]
        ok = expected in agents
        if ok:
            passed += 1
        else:
            failed.append((request, expected, agents, intent["task_type"]))
        if args.verbose:
            print(f"  {'ok ' if ok else 'FAIL'}  want={expected:26} got={','.join(agents)}")

    # Sticky routing: seed a session with one request that names the domain, then
    # send follow-ups that name nothing, and check the subject holds.
    import uuid as _uuid
    sid = "regression-" + _uuid.uuid4().hex[:8]
    _parse_intent_stage(STICKY_SEED, sid)
    sticky_fail = []
    for request, expected in STICKY_CASES + STICKY_BREAKS:
        got = _parse_intent_stage(request, sid)["agents"]
        if expected not in got:
            sticky_fail.append((request, expected, got))

    # A retired agent appearing in ANY result is a failure regardless of which
    # case produced it, so this is checked across the whole set rather than
    # per-case.
    leaked: set[str] = set()
    for request, _expected in CASES:
        leaked |= set(_parse_intent_stage(request, "")["agents"]) & MUST_NOT_ROUTE

    total = len(CASES)
    print(f"\nrouting regression: {passed}/{total} passed")
    if leaked:
        print(f"RETIRED AGENTS LEAKED INTO ROUTING: {sorted(leaked)}")
    else:
        print(f"retired agents: none reachable ({len(MUST_NOT_ROUTE)} checked)")
    n_sticky = len(STICKY_CASES) + len(STICKY_BREAKS)
    print(f"session-sticky follow-ups: {n_sticky - len(sticky_fail)}/{n_sticky} passed")
    for request, expected, got in sticky_fail:
        print(f"  want {expected:26} got {','.join(got):30}")
        print(f"       {request[:74]}")
    if failed:
        print("\nfailures:")
        for request, expected, agents, tt in failed:
            print(f"  want {expected:26} got {','.join(agents):34} [{tt}]")
            print(f"       {request[:88]}")
    return 0 if (not failed and not leaked and not sticky_fail) else 1


if __name__ == "__main__":
    raise SystemExit(main())
