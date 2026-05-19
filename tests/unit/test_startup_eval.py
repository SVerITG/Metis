"""
Unit tests for startup_eval.py — the dashboard health-check module.

Each check function is tested in isolation. No running server needed.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

_APP_PY = Path(__file__).parent.parent.parent / "system" / "app-py"
if str(_APP_PY) not in sys.path:
    sys.path.insert(0, str(_APP_PY))

from startup_eval import _check_database, _check_templates, _check_configs, run_startup_eval


# ── _check_database ────────────────────────────────────────────────────────

class TestCheckDatabase:
    def test_pass_all_tables_present(self, tmp_path):
        db = tmp_path / "ok.sqlite"
        conn = sqlite3.connect(str(db))
        for table in [
            "agent_runs", "news_briefs", "tasks", "library_cards",
            "memory_entries", "ideas", "projects", "sessions", "jobs_log",
        ]:
            conn.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        result = _check_database(str(db))
        assert result["status"] == "PASS"

    def test_fail_db_not_found(self, tmp_path):
        result = _check_database(str(tmp_path / "nonexistent.sqlite"))
        assert result["status"] == "FAIL"
        assert "not found" in result["detail"]

    def test_warn_missing_tables(self, tmp_path):
        db = tmp_path / "partial.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE agent_runs (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        result = _check_database(str(db))
        assert result["status"] == "WARN"
        assert "Missing tables" in result["detail"]

    def test_fail_empty_path(self):
        result = _check_database("")
        assert result["status"] == "FAIL"


# ── _check_templates ───────────────────────────────────────────────────────

class TestCheckTemplates:
    def test_pass_all_templates_present(self, tmp_path):
        for name in [
            "today.html", "knowledge.html", "meetings.html", "learning.html",
            "work.html", "thinking.html", "planner.html", "teach.html", "metis_tab.html",
        ]:
            (tmp_path / name).write_text("")
        result = _check_templates(tmp_path)
        assert result["status"] == "PASS"

    def test_fail_missing_templates(self, tmp_path):
        (tmp_path / "today.html").write_text("")  # only one present
        result = _check_templates(tmp_path)
        assert result["status"] == "FAIL"
        assert "Missing" in result["detail"]

    def test_fail_empty_dir(self, tmp_path):
        result = _check_templates(tmp_path / "nonexistent")
        assert result["status"] == "FAIL"


# ── _check_configs ─────────────────────────────────────────────────────────

class TestCheckConfigs:
    def test_pass_required_configs_present(self, tmp_path, monkeypatch):
        (tmp_path / "system" / "config").mkdir(parents=True)
        (tmp_path / "system" / "config" / "constitution.md").write_text("")
        (tmp_path / "system" / "mcp-server" / "src" / "metis_mcp" / "tools").mkdir(parents=True)
        (tmp_path / "system" / "mcp-server" / "src" / "metis_mcp" / "tools" / "memory_curator.py").write_text("")
        result = _check_configs(str(tmp_path))
        assert result["status"] == "PASS"

    def test_warn_missing_rc_root(self):
        result = _check_configs("")
        assert result["status"] == "WARN"
        assert "METIS_RC_ROOT not set" in result["detail"]

    def test_warn_missing_config_file(self, tmp_path):
        # rc_root exists but none of the required files are there
        result = _check_configs(str(tmp_path))
        assert result["status"] == "WARN"
        assert "Missing" in result["detail"]


# ── run_startup_eval ───────────────────────────────────────────────────────

class TestRunStartupEval:
    def test_returns_dict_with_required_keys(self, tmp_path, monkeypatch):
        monkeypatch.setenv("METIS_DB", str(tmp_path / "nonexistent.sqlite"))
        monkeypatch.setenv("METIS_RC_ROOT", str(tmp_path))
        result = run_startup_eval()
        assert "overall" in result
        assert "checks" in result
        assert "run_at" in result
        assert isinstance(result["checks"], list)
        assert len(result["checks"]) == 4

    def test_overall_fail_when_db_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("METIS_DB", str(tmp_path / "ghost.sqlite"))
        monkeypatch.setenv("METIS_RC_ROOT", str(tmp_path))
        result = run_startup_eval()
        assert result["overall"] in ("FAIL", "WARN")

    def test_writes_json_result_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("METIS_DB", str(tmp_path / "ghost.sqlite"))
        monkeypatch.setenv("METIS_RC_ROOT", str(tmp_path))
        run_startup_eval()
        result_file = tmp_path / "system" / "config" / "eval-results.json"
        assert result_file.exists()
        import json
        data = json.loads(result_file.read_text())
        assert "overall" in data

    def test_check_names_present(self, tmp_path, monkeypatch):
        monkeypatch.setenv("METIS_DB", str(tmp_path / "ghost.sqlite"))
        monkeypatch.setenv("METIS_RC_ROOT", str(tmp_path))
        result = run_startup_eval()
        names = {c["name"] for c in result["checks"]}
        assert names == {"database", "templates", "routers", "configs"}
