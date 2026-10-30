"""The data-mode hook must recognise data requests and stay silent on everything else.

Written 2026-10-30, after the first version missed the researcher's own first
request: it began "Metis, can you…" and "metis" was on the system-work list, and
"endemic", "villages" and "health zones" were on no list at all. The hook now
also uses the researcher's own data words (data-vocab.json, written by every
Data Memory scan). This file is the measurement: labelled prompts, in three
languages, run through the hook's own isDataWork() — never a restatement of it.

The vocabulary here is synthetic and generic on purpose; it stands in for the
words a scan of any researcher's scripts would produce.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "data-mode.mjs"

# words a scan of the researcher's scripts would export
VOCAB = ["endemic", "villages", "village", "health", "healthzone", "zones", "zone", "cases",
         "screening", "coordination", "foci", "positivity", "passive", "structures", "burden",
         "northvale", "northvale", "eastmoor", "surveyx", "rdt", "province", "area", "areas", "population"]

DATA = [
    "Metis, can you make me a script that tells me the endemic areas (villages and health zones) for 2026?",
    "is it specific for northvale region? does it compare the entire country with the northvale region?",
    "no no the cases are in the surveillance dashboard",
    "how many villages had a case in 2025 in Northvale",
    "make a map of the screening coverage per health area",
    "show me the trend of positivity by coordination since 2015",
    "which health zones had no active screening in the last 5 years",
    "compare RDT positivity between Eastmoor and Northvale",
    "I need a table of new villages with cases per year",
    "plot SurveyX results by health zone",
    "what is the population of the villages within the foci",
    "rewrite 05_region_case_burden.R so it uses the last 10 years",
    "maak een kaart van de gevallen per gezondheidszone in 2025",
    "hoeveel dorpen hadden een geval in 2024",
    "fais-moi un tableau des cas par zone de santé pour 2026",
    "combien de villages endémiques en 2025 ?",
    "how many cases did the passive structures detect in 2026?",
    "can you add a figure with the share of passive cases",
    "what is the denominator for screening coverage",
    "the dashboard shows the wrong number of cases per coordination",
    "make a figure for the paper with cases per year",
    "which coordinations still had new cases after 2020",
]

NOT_DATA = [
    "fix the HTMX partial on the Metis dashboard route",
    "add a new MCP tool for the wizard",
    "thanks, that looks great",
    "yes commit to all github pages",
    "write me an email to my colleague about the meeting next week",
    "summarise this paper for me please",
    "Metis, what's on my calendar today",
    "and are you sure that the tool calling is sensitive enough, enough key words and such?",
    "restyle the Data page so the cards look better",
    "remind me in a week to re-run the routing audit",
    "who should I invite to the steering committee",
    "the morning brief failed again this morning",
    "how do I install Metis on my laptop",
    "prepare the release notes for colleagues",
    # subject words without a data request: literature, writing, presenting
    "what does the literature say about RDT sensitivity in community screening",
    "draft the methods paragraph for the community screening article",
    "find papers on elimination of the disease in Eastmoor",
    "prepare slides on elimination progress for the steering committee",
    # false alarms found by replaying 621 real prompts (2026-10-30)
    "i made a new key, what do i fill in in the enviroment variables",
    "now for the exercises, change them so you really need to solve them to gain points",
    "put the brief again at the top of the Today surface, sessions go all the way to the bottom",
    "why does metis in claude desktop give strange answers every conversation",
    "something is wrong with the syncing of feeds on the metis dashboard",
]


@pytest.fixture(scope="module")
def verdicts():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    prompts = DATA + NOT_DATA
    script = (
        f"import {{ isDataWork }} from {json.dumps(HOOK.as_uri())};\n"
        f"const terms = new Set({json.dumps(VOCAB)});\n"
        f"const prompts = {json.dumps(prompts)};\n"
        "console.log(JSON.stringify(prompts.map(p => isDataWork(p, terms))));\n"
    )
    out = subprocess.run([node, "--input-type=module", "-e", script],
                         capture_output=True, text=True, timeout=20)
    assert out.returncode == 0, out.stderr
    return dict(zip(prompts, json.loads(out.stdout)))


@pytest.mark.parametrize("prompt", DATA)
def test_data_request_switches_the_mode_on(verdicts, prompt):
    assert verdicts[prompt], f"missed: {prompt}"


@pytest.mark.parametrize("prompt", NOT_DATA)
def test_other_work_stays_silent(verdicts, prompt):
    assert not verdicts[prompt], f"false alarm: {prompt}"


def test_the_server_judges_exactly_like_the_hook(verdicts):
    """Desktop runs no hooks; the server's copy of the rules must not drift."""
    import sys
    src = str(Path(__file__).resolve().parents[2] / "system" / "mcp-server" / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from metis_mcp import data_memory as dm
    terms = set(VOCAB)
    differ = [p for p, v in verdicts.items() if dm.is_data_request(p, terms) != v]
    assert not differ, differ


def test_without_vocabulary_the_researchers_first_request_still_triggers():
    """No scan yet (a new install): generic words alone must carry the clear cases."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    p = "Metis, can you make me a script that tells me the endemic areas for 2026?"
    script = (f"import {{ isDataWork }} from {json.dumps(HOOK.as_uri())};\n"
              f"console.log(isDataWork({json.dumps(p)}, new Set()));\n")
    out = subprocess.run([node, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=20)
    assert out.stdout.strip() == "true", out.stderr
