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

// The gate function is lifted out of the hook and run on its own, so anything
// it references at MODULE scope has to come with it. IS_SYSTEM_WORK moved out
// of the function on 2026-08-29 (the session-stickiness marker needs it too),
// and this driver silently stopped working — a ReferenceError inside the eval,
// surfacing only as "exit status 1". Hoist the constants the gate depends on
// rather than duplicating their values here, which would let the test drift
// away from the code it is checking.
const consts = [...src.matchAll(/^const ([A-Z_]+) = (\/[\s\S]*?\/[gimsuy]*);$/gm)]
  .map((c) => c[0]).join("\n");

const m = src.match(/function looksLikeDomainQuestion[\s\S]*?\n}\n/);
if (!m) { console.error("gate function not found"); process.exit(2); }
const gate = eval(`(() => { ${consts}\nreturn ${m[0]} })()`);
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
        "corpus grounding fired on work about Metis itself — The researcher asked "
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

# ── Session stickiness ──────────────────────────────────────────────────────
# Added 2026-08-29. The researcher: "When we are working on metis you do not have to route
# through the library if not indicated specifically."
#
# The gate-function tests above cannot cover this, because the rule is not a
# property of one prompt. "Where can I find the seven approved patterns?" and
# "build me mockups for all the proposals" are both plainly about this repo and
# contain NO system vocabulary at all — there is nothing for a word filter to
# match. The session has to remember. So these run the whole hook, in order,
# through its real stdin/stdout contract.

import os
import tempfile
import uuid


def _run_hook(prompt, session_id):
    """Invoke the hook exactly as Claude Code does. True = grounding fired."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(ROOT))
    out = subprocess.run(
        [node, str(HOOK)],
        input=json.dumps({"prompt": prompt, "session_id": session_id}),
        capture_output=True, text=True, timeout=40, env=env,
    )
    return "metis-corpus-grounding" in (out.stdout or "")


@pytest.fixture()
def fresh_session():
    """A session id nothing has marked yet, cleaned up afterwards."""
    sid = "test" + uuid.uuid4().hex[:12]
    yield sid
    marker = Path(tempfile.gettempdir()) / "metis-corpus-hook" / f"{sid}.system"
    marker.unlink(missing_ok=True)


def test_plural_system_words_are_caught(fresh_session):
    """`\bdashboard\b` does not match "dashboards" — the trailing s is a word
    character, so the closing boundary never lands. That one missing plural sent
    a question about dashboard design to a DHIS2 manual on 2026-08-28."""
    assert not _run_hook(
        "which are the dashboards that you are comparing yourself with when "
        "reflecting on design changes UI UX wise?", fresh_session)


def test_followups_in_a_metis_session_stay_quiet(fresh_session):
    """Neither of these carries a single system word. They must still be quiet,
    because the SESSION is about Metis."""
    assert not _run_hook("add a peek panel to the Work dashboard", fresh_session)
    assert not _run_hook("where can i find the seven approved patterns?", fresh_session)
    assert not _run_hook(
        "Build me many mockups for all the proposals, so every time you do a "
        "proposal i can compare the orginal with what you propose", fresh_session)


LIBRARY_ASK = ("what does the literature say about tsetse control "
               "effectiveness in Kwilu?")


def test_asking_for_the_library_still_works_mid_session(fresh_session, request):
    """The 'unless indicated specifically' half. A sticky session must not lock
    the researcher out of their own corpus.

    This one needs a CONTROL, and the reason is worth stating: a hook that
    decides to ground still emits nothing if the corpus search behind it times
    out, and the search is a real embedding query over ~48,000 chunks. Asserting
    "grounding fired" therefore fails for two completely different reasons —
    the gate refused, or the dashboard was slow. It failed exactly that way on
    2026-08-29 when five hook invocations ran back to back.

    So: run the same prompt in a clean session first. If THAT does not ground,
    the environment is at fault and there is nothing here to test; skip rather
    than report a defect in code that is fine. Only if the control grounds does
    the mid-session assertion mean anything."""
    control = "control" + fresh_session
    if not _run_hook(LIBRARY_ASK, control):
        Path(tempfile.gettempdir(), "metis-corpus-hook", f"{control}.system").unlink(missing_ok=True)
        pytest.skip("corpus search did not answer in time — environment, not the gate")

    assert not _run_hook("fix the dashboards stylesheet", fresh_session)
    assert _run_hook(LIBRARY_ASK, fresh_session), (
        "a sticky Metis session swallowed an explicit request for the library — "
        "the 'unless indicated specifically' escape hatch is not working"
    )


RESEARCH_Q = ("what is the specificity of CATT in a low prevalence setting "
              "for gambiense HAT screening?")


def test_a_research_session_is_never_marked(fresh_session):
    """A session that never touches Metis keeps grounding on every question.

    Carries the same CONTROL as the test above, and for the same reason — which
    I failed to apply here when I wrote it, so this test flaked on 2026-08-31
    exactly as its sibling had. A hook that decides to ground still emits
    nothing when the corpus search behind it times out, so "did not ground" has
    two completely different causes and only one of them is a defect. Establish
    that the search is answering at all before asserting anything about the gate.
    """
    probe = "probe" + fresh_session
    if not _run_hook(RESEARCH_Q, probe):
        Path(tempfile.gettempdir(), "metis-corpus-hook", f"{probe}.system").unlink(missing_ok=True)
        pytest.skip("corpus search did not answer in time — environment, not the gate")

    assert _run_hook(RESEARCH_Q, fresh_session)
    assert _run_hook(
        "is there evidence for livestock density predicting tsetse abundance?",
        fresh_session)
