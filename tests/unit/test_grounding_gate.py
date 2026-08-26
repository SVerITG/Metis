"""The corpus-grounding hook must fire on research questions and stay silent on
work about Metis itself.

Written 2026-08-25 after the researcher noticed grounding ran on nearly every
prompt. Three defects were behind it, and each is regression-tested here:

  1. The trigger list from /api/library/corpus-triggers contains raw English
     stopwords — "what", "have" and "hand" are all live terms. With those in
     play ANY question grounds. The hook filters them; this asserts it still does.
  2. Matching was `p.includes(t)`, a raw substring, so "cont" matched "continue".
     It is now word-boundary matched.
  3. "agent" is Metis vocabulary AND field vocabulary (a trypanocidal agent), so
     it is gated on co-occurrence rather than blocked outright. Both readings are
     asserted, because fixing one by breaking the other is not a fix.

The check runs the hook's own function rather than restating its rules, so the
test cannot drift away from the code the way a duplicated rule set would.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "user-prompt-submit.mjs"
TRIGGERS = ROOT / "system" / "config" / ".corpus-triggers.json"

# Work ON Metis — grounding these in NTD literature is the noise being fixed.
SYSTEM_PROMPTS = [
    "I just saved a hand off document from another computer, can you find it?",
    "what are the decisions to take now?",
    "I just reconnected metis now you can continue",
    "why is the dashboard returning a blank panel?",
    "add a new MCP tool for routing counts",
    "the test suite failed, what broke?",
    "should I push the two oldest commits?",
    "what agents do I have registered?",
    "audit the routing rules and tell me which never fired",
]

# Real research questions — these MUST still reach the corpus.
RESEARCH_PROMPTS = [
    "what is the specificity of CATT for sleeping sickness?",
    "what is the evidence for passive screening in gambiense HAT?",
    "how does tsetse control affect transmission in DRC?",
    "which multilevel model should I use for spatial epidemiology of HAT?",
    "what does the literature say about sample size for surveillance in low prevalence foci?",
    "compare active and passive case detection for trypanosomiasis",
    "what agents are effective against gambiense HAT?",
    "which drug agents show resistance in T.b. rhodesiense?",
]

DRIVER = r"""
import { readFileSync } from "node:fs";
const src = readFileSync(process.argv[2], "utf8");
const m = src.match(/function looksLikeDomainQuestion[\s\S]*?\n}\n/);
if (!m) { console.error("gate function not found"); process.exit(2); }
const gate = eval(`(${m[0]})`);
const terms = JSON.parse(readFileSync(process.argv[3], "utf8")).terms;
const prompts = JSON.parse(process.argv[4]);
console.log(JSON.stringify(prompts.map((p) => gate(p, terms))));
"""


def _gate(prompts):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    if not TRIGGERS.exists():
        pytest.skip("corpus-trigger cache not present on this machine")
    driver = ROOT / "tests" / "unit" / "_grounding_gate_driver.mjs"
    driver.write_text(DRIVER, encoding="utf-8")
    try:
        out = subprocess.run(
            [node, str(driver), str(HOOK), str(TRIGGERS), json.dumps(prompts)],
            capture_output=True, text=True, timeout=30, check=True,
        )
    finally:
        driver.unlink(missing_ok=True)
    return json.loads(out.stdout)


def test_metis_work_does_not_ground():
    fired = _gate(SYSTEM_PROMPTS)
    leaks = [p for p, f in zip(SYSTEM_PROMPTS, fired) if f]
    assert not leaks, (
        "corpus grounding fired on work about Metis itself — the researcher asked "
        f"for this to stop on 2026-08-25:\n  " + "\n  ".join(leaks)
    )


def test_research_questions_still_ground():
    fired = _gate(RESEARCH_PROMPTS)
    missed = [p for p, f in zip(RESEARCH_PROMPTS, fired) if not f]
    assert not missed, (
        "corpus grounding stopped firing on real research questions — the filter "
        f"is now too aggressive:\n  " + "\n  ".join(missed)
    )


def test_stopwords_are_filtered_not_merely_absent():
    """The upstream extractor still emits stopwords; the hook must not rely on
    that being fixed. If these ever stop appearing as triggers, the guard can go."""
    terms = set(json.loads(TRIGGERS.read_text(encoding="utf-8"))["terms"])
    assert {"what", "have", "hand"} & terms, (
        "stopwords no longer present in the trigger list — the extractor may be "
        "fixed; re-check whether the GENERIC filter in the hook is still needed"
    )
