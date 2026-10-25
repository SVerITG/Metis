"""
The install doctor's list of essentials and its code must describe the same things.

system/install/essentials.json is the one list of what Metis needs on a computer;
metis_verify.py holds one check per entry. A requirement added in one place and
not the other is either never checked or checked without anyone knowing why —
exactly how the dashboard's log-on task and the search engine's runtime came to
exist without a check. These tests make that impossible to miss.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALL = ROOT / "system" / "install"
SPEC = json.loads((INSTALL / "essentials.json").read_text(encoding="utf-8"))


def _doctor():
    spec = importlib.util.spec_from_file_location("metis_verify_under_test", INSTALL / "metis_verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_essential_has_a_check_and_every_check_is_listed():
    doctor = _doctor()
    listed = [e["id"] for e in SPEC["essentials"]]
    assert len(listed) == len(set(listed)), "an essential is listed twice"
    assert set(listed) - set(doctor.CHECKS) == set(), "listed but never checked"
    assert set(doctor.CHECKS) - set(listed) == set(), "checked but not in essentials.json"


def test_repairs_match_what_the_list_promises():
    doctor = _doctor()
    auto = {e["id"] for e in SPEC["essentials"] if e["repair"] == "auto"}
    assert auto - set(doctor.FIXES) == set(), "repair=auto but there is no repair"
    assert set(doctor.FIXES) - auto == set(), "a repair exists that the list does not mention"


def test_entries_are_complete_and_plain():
    for e in SPEC["essentials"]:
        assert e["group"] in SPEC["groups"], e["id"]
        assert e["severity"] in ("fail", "warn"), e["id"]
        assert e["repair"] in ("auto", "person"), e["id"]
        assert set(e.get("platforms", [])) <= {"windows", "linux", "darwin"}, e["id"]
        assert e.get("needs") in (None, "dashboard"), e["id"]
        for field in ("name", "why", "how"):
            assert e.get(field, "").strip(), f"{e['id']} has no {field}"


def test_every_ai_app_metis_can_connect_is_checked():
    sys.path.insert(0, str(INSTALL))
    import register_desktop
    ids = {e["id"] for e in SPEC["essentials"]}
    expected = {"app_" + c.replace("-", "_") for c in register_desktop.CLIENTS} | {"app_claude_code"}
    assert expected <= ids


def test_apps_are_connected_by_merging(tmp_path):
    """VS Code and Cursor get Metis in their own format; whatever was there stays,
    and an uninstall takes Metis out of every app."""
    home = tmp_path / "home"
    (home / ".config" / "Code" / "User").mkdir(parents=True)
    (home / ".cursor").mkdir(parents=True)
    (home / ".config" / "Code" / "User" / "mcp.json").write_text(
        json.dumps({"servers": {"theirs": {"type": "stdio", "command": "x"}}}), encoding="utf-8")
    # The Claude Desktop folder named explicitly: under WSL it would otherwise be
    # the real one on the Windows side.
    env = {**os.environ, "HOME": str(home),
           "METIS_CLAUDE_DESKTOP_DIR": str(home / ".config" / "Claude")}
    reg = [sys.executable, str(INSTALL / "register_desktop.py")]
    subprocess.run(reg + ["--all-installed", "--python", "/opt/py", "--root", "/opt/metis"],
                   env=env, check=True, capture_output=True)
    vs = json.loads((home / ".config" / "Code" / "User" / "mcp.json").read_text())["servers"]
    assert set(vs) == {"theirs", "metis-rc"} and vs["metis-rc"]["type"] == "stdio"
    cur = json.loads((home / ".cursor" / "mcp.json").read_text())["mcpServers"]
    assert cur["metis-rc"]["command"] == "/opt/py"
    desk = json.loads((home / ".config" / "Claude" / "claude_desktop_config.json").read_text())
    assert "metis-rc" in desk["mcpServers"]

    subprocess.run(reg + ["--remove"], env=env, check=True, capture_output=True)
    vs = json.loads((home / ".config" / "Code" / "User" / "mcp.json").read_text())["servers"]
    assert set(vs) == {"theirs"}
    assert "metis-rc" not in json.loads((home / ".cursor" / "mcp.json").read_text())["mcpServers"]
