"""Routing must be able to name more than one specialist, and say who in plain
English.

Built 2026-08-25 on the researcher's instruction that routing be used in BOTH
Claude Code and Claude Desktop, and that a non-technical user should be able to
SEE which specialists are working on a request — possibly several at once.

Three properties are asserted, because each was broken or absent before:

  1. MULTI-AGENT. `_parse_intent_stage` used to `break` on the first keyword
     match, so "review my methods AND the grammar" silently dropped the second
     specialist. It now collects up to _MAX_ROUTED_AGENTS.
  2. AUDITABILITY. `hits` counted only the rule that won. A rule that matched
     but lost was indistinguishable from one whose requests never arrive — the
     exact ambiguity the 2026-08-25 routing audit could not resolve. `matches`
     now counts presence separately.
  3. PLAIN LANGUAGE. The announcement names agents in words a non-technical
     reader recognises and gives an honest, checkable reason. It must never leak
     a raw slug, and must not claim a specialist when none was found.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

pipeline = pytest.importorskip("metis_mcp.tools.pipeline")


@pytest.fixture(scope="module", autouse=True)
def _seeded():
    try:
        pipeline._ensure_routing_table()
    except sqlite3.Error as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"routing table unavailable: {exc}")


def _route(req):
    return pipeline._parse_intent_stage(req, "test-routing")


# ── 1. multi-agent ───────────────────────────────────────────────────────────

def test_two_domains_reach_two_specialists():
    agents = _route("clean this csv and make a chart of the results")["agents"]
    assert len(agents) >= 2, f"only one specialist routed: {agents}"
    assert "data-analyst" in agents
    assert "visualization-maker" in agents


def test_agents_are_capped_and_unique():
    d = _route("clean this csv, make a chart, review the study design, "
               "fix the grammar, debug the r script and find the paper")
    agents = d["agents"]
    assert len(agents) <= pipeline._MAX_ROUTED_AGENTS, agents
    assert len(agents) == len(set(agents)), f"duplicate agents: {agents}"


def test_single_domain_still_routes_to_one():
    assert _route("what is the right study design here?")["agents"] == ["epidemiologist"]


# ── 2. auditability ──────────────────────────────────────────────────────────

def test_matches_column_exists():
    """`matches` is what separates a shadowed rule from one nobody asks for."""
    with pipeline.connect(pipeline.paths.db) as con:
        cols = {r[1] for r in con.execute("PRAGMA table_info(agent_routing_rules)")}
    assert "matches" in cols


def test_claude_own_agents_are_routable():
    """The researcher asked for Claude's built-in agents to be routable too."""
    assert "Explore" in _route("find where the routing table is defined")["agents"]


def test_coverage_reaches_far_more_agents_than_the_original_seed():
    """The original seed named 21 agents against a registry of 33."""
    with pipeline.connect(pipeline.paths.db) as con:
        n = con.execute(
            "SELECT COUNT(DISTINCT agent_slug) FROM agent_routing_rules").fetchone()[0]
    assert n >= 40, f"only {n} agents reachable by keyword"


# ── 3. plain language ────────────────────────────────────────────────────────

def test_announcement_never_leaks_a_raw_slug():
    d = _route("extend metis with a new mcp tool and a dashboard tab")
    said = pipeline._who_is_on_it(d["routed_because"])
    for slug in d["agents"]:
        assert slug not in said, f"raw slug {slug!r} leaked into: {said!r}"


def test_announcement_gives_a_checkable_reason():
    d = _route("clean this csv and make a chart of the results")
    said = pipeline._who_is_on_it(d["routed_because"])
    assert "you said" in said
    assert "csv" in said or "clean" in said
    assert "chart" in said


def test_no_specialist_is_not_dressed_up_as_one():
    """Telling a user "I've put Metis on it" when Metis IS the assistant is
    confusing rather than informative."""
    d = _route("tell me a joke about badgers")
    said = pipeline._who_is_on_it(d["routed_because"])
    assert "specialist" not in said or said.startswith("No specialist")
    assert "metis" not in said.lower()


def test_friendly_names_are_readable():
    assert pipeline._friendly_agent_name("writing-partner") == "writing partner"
    assert pipeline._friendly_agent_name("Explore") == "code explorer"
    assert pipeline._friendly_agent_name("metis-audit-security") == "security auditor"
    assert pipeline._friendly_agent_name("dhis2-expert") == "DHIS2 expert"
