"""
The self-check colleagues' computers run every day: it must notice what breaks
and repair what it says it repairs.

Run against a throwaway home directory and database. It starts the real server
from the registration it finds, exactly as Claude Desktop would.
"""

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "system" / "install" / "metis_verify.py"
SCHEMA = ROOT / "system" / "installer" / "schema.sql"


@pytest.fixture()
def world(tmp_path):
    pytest.importorskip("mcp")
    home = tmp_path / "home"
    desk = home / ".config" / "Claude"
    desk.mkdir(parents=True)
    db = tmp_path / "metis.sqlite"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.execute("DROP TABLE glossary")
    con.close()
    # Claude Desktop is installed, with another connector and no Metis.
    (desk / "claude_desktop_config.json").write_text(
        json.dumps({"mcpServers": {"other": {"command": "other"}}}), encoding="utf-8")
    # PATH without uv, and no pip in the test's environment: a --fix that decides
    # to reinstall must not be able to reach a real installation from a test.
    env = {**os.environ, "HOME": str(home), "METIS_DB": str(db), "HF_HUB_OFFLINE": "1",
           "PATH": "/usr/bin:/bin",
           "METIS_VERIFY_NO_REINSTALL": "1",
           # A Windows console: cp1252 has no ✓, and every check once crashed on it.
           "PYTHONIOENCODING": "cp1252",
           "METIS_VERIFY_RESULT": str(tmp_path / "readiness.json"),
           "PYTHONPATH": str(ROOT / "system" / "mcp-server" / "src")}
    return tmp_path, home, db, env


def _run(env, *args):
    proc = subprocess.run([sys.executable, str(VERIFY), *args], env=env, cwd=ROOT,
                          capture_output=True, text=True, timeout=600)
    return proc.returncode, proc.stdout


def _by_name(tmp):
    return {c["name"]: c for c in json.loads((tmp / "readiness.json").read_text())["checks"]}


def test_notices_then_repairs(world):
    tmp, home, db, env = world
    code, out = _run(env)
    checks = _by_name(tmp)
    assert code == 2, out
    assert checks["Metis is connected to Claude Desktop"]["status"] == "fail"
    assert checks["Your Metis database"]["status"] == "warn"

    # --fix needs a Metis environment to register; point it at this interpreter.
    venv = home / ".local" / "share" / "metis-mcp" / ".venv" / "bin"
    venv.mkdir(parents=True)
    # A wrapper, not a symlink: a venv's python reached through a link outside
    # its own folder does not find its packages.
    (venv / "python3").write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    (venv / "python3").chmod(0o755)
    code, out = _run(env, "--fix")
    checks = _by_name(tmp)
    assert checks["Metis is connected to Claude Desktop"]["status"] == "pass", out
    assert checks["Metis starts when Claude asks"]["status"] in ("pass", "warn"), out
    assert checks["Your Metis database"]["status"] == "pass", out

    servers = json.loads((home / ".config" / "Claude" / "claude_desktop_config.json").read_text())["mcpServers"]
    assert set(servers) == {"other", "metis-rc"}, "the other connector must survive the repair"
    assert sqlite3.connect(db).execute(
        "SELECT 1 FROM sqlite_master WHERE name='glossary'").fetchone()
