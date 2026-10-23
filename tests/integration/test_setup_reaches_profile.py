"""
What a colleague types into setup must be what Claude sees afterwards.

Setup wrote the persona, user-config.yaml and user_topics, while
get_user_profile() — the call Claude makes at the start of a conversation —
reads user-preferences.json, which setup never wrote. Tested on a clean install:
after a completed wizard, Claude got display_name "Researcher", no role and no
news interests, and the setup checks still said everything was fine.

So this test does not inspect the file setup writes. It runs setup's processing
on an empty Metis folder and then asks get_user_profile(), in a fresh process
with that folder as its root, exactly as Claude Desktop's server would.
"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "system" / "installer" / "schema.sql"

ANSWERS = {
    "name": "Ada Example",
    "institution": "Example Institute",
    "role": "Senior epidemiologist",
    "field": "vector-borne disease epidemiology",
    "methods": "Bayesian hierarchical models, spatial statistics",
    "news_terms": "WHO guidance; AI in health",
    "tools": "R",
    "feedback_style": "direct",
    "projects": [],
}

PROBE = r"""
import asyncio, json, sys
sys.path.insert(0, sys.argv[1])
import process_wizard_answers as p
from pathlib import Path
res = p.process(json.loads(sys.argv[3]), Path(sys.argv[2]))
from metis_mcp.tools.user_profile import get_user_profile
out = asyncio.run(get_user_profile())
print("PROFILE=" + out[0].text.replace("\n", " "))
print("RESULT=" + json.dumps(res.get("profile_written")))
"""


@pytest.fixture(scope="module")
def profile(tmp_path_factory):
    pytest.importorskip("mcp")
    root = tmp_path_factory.mktemp("metis-root")
    (root / "system" / "config").mkdir(parents=True)
    db = tmp_path_factory.mktemp("data") / "metis.sqlite"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.close()
    env = {**os.environ, "METIS_RC_ROOT": str(root), "METIS_DB": str(db),
           "ANTHROPIC_API_KEY": "",
           "PYTHONPATH": str(ROOT / "system" / "mcp-server" / "src")}
    proc = subprocess.run(
        [sys.executable, "-c", PROBE, str(ROOT / "system" / "install"), str(root),
         json.dumps(ANSWERS)],
        env=env, capture_output=True, text=True, timeout=300)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("PROFILE=")), None)
    assert line, f"probe failed:\n{proc.stdout[-1500:]}\n{proc.stderr[-3000:]}"
    return json.loads(line[len("PROFILE="):]), root


def test_claude_knows_the_name_and_role(profile):
    p, _ = profile
    assert p["display_name"] == "Ada Example", "Claude would greet them as " + p["display_name"]
    assert p["role"] == "Senior epidemiologist"


def test_news_and_library_stay_separate(profile):
    p, _ = profile
    assert p["news_interests"] == ["WHO guidance", "AI in health"]
    lib = [t.lower() for t in p["library_interests"]]
    assert "vector-borne disease epidemiology" in lib
    assert "bayesian hierarchical models" in lib
    # A field you work in is not automatically news you want.
    assert not any("epidemiology" in t.lower() for t in p["news_interests"])


def test_the_interests_count_as_chosen(profile):
    p, _ = profile
    assert p["has_declared_news_interests"] and p["has_declared_library_interests"], (
        "setup answers are the person's own choice; Metis should not offer the "
        "interest interview again as if nothing had been said")


def test_a_rerun_with_blanks_keeps_what_was_there(profile):
    _, root = profile
    sys.path.insert(0, str(ROOT / "system" / "install"))
    try:
        import process_wizard_answers as pwa
    finally:
        sys.path.pop(0)
    pwa.write_user_preferences(root, {"name": "", "role": "", "news_terms": ""})
    prefs = json.loads((root / "system" / "config" / "user-preferences.json").read_text())
    assert prefs["display_name"] == "Ada Example"
    assert prefs["news_interests"] == ["WHO guidance", "AI in health"]
