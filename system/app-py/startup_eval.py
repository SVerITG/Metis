"""
startup_eval.py — Lightweight health check that runs on every dashboard start.

Checks four things without making any HTTP calls:
  1. Database is reachable and required tables exist
  2. Required template files exist (one per tab)
  3. Required router modules are importable
  4. Critical config files are present

Results are written to system/config/eval-results.json and logged at INFO level.
A FAIL in any check does not crash the server — it surfaces in the log and the JSON.
"""

import datetime
import importlib
import json
import logging
import os
import sqlite3
from pathlib import Path

log = logging.getLogger("metis.eval")

_REQUIRED_TABLES = [
    "agent_runs",
    "news_briefs",
    "tasks",
    "library_cards",
    "memory_entries",
    "ideas",
    "projects",
    "sessions",
    "jobs_log",
]

_REQUIRED_TEMPLATES = [
    "today.html",
    "knowledge.html",
    "meetings.html",
    "learning.html",
    "work.html",
    "thinking.html",
    "planner.html",
    "teach.html",
    "metis_tab.html",
]

_REQUIRED_ROUTERS = [
    "routers.today",
    "routers.knowledge",
    "routers.learning",
    "routers.work",
    "routers.meetings",
    "routers.metis_tab",
    "routers.planner",
    "routers.teach",
    "routers.thinking",
]

_REQUIRED_CONFIGS = [
    "system/config/constitution.md",
    "system/mcp-server/src/metis_mcp/tools/memory_curator.py",
]


def _check_database(db_path: str) -> dict:
    result = {"name": "database", "status": "PASS", "detail": ""}
    if not db_path or not Path(db_path).exists():
        result["status"] = "FAIL"
        result["detail"] = f"DB not found at: {db_path}"
        return result

    missing = []
    try:
        conn = sqlite3.connect(db_path, timeout=3)
        for table in _REQUIRED_TABLES:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not row:
                missing.append(table)
        conn.close()
    except Exception as e:
        result["status"] = "FAIL"
        result["detail"] = f"DB connection error: {e}"
        return result

    if missing:
        result["status"] = "WARN"
        result["detail"] = f"Missing tables: {', '.join(missing)}"
    else:
        result["detail"] = f"{len(_REQUIRED_TABLES)} tables present"
    return result


def _check_templates(templates_dir: Path) -> dict:
    result = {"name": "templates", "status": "PASS", "detail": ""}
    missing = [t for t in _REQUIRED_TEMPLATES if not (templates_dir / t).exists()]
    if missing:
        result["status"] = "FAIL"
        result["detail"] = f"Missing: {', '.join(missing)}"
    else:
        result["detail"] = f"{len(_REQUIRED_TEMPLATES)} tab templates present"
    return result


def _check_routers() -> dict:
    result = {"name": "routers", "status": "PASS", "detail": ""}
    failed = []
    for mod in _REQUIRED_ROUTERS:
        try:
            importlib.import_module(mod)
        except Exception as e:
            failed.append(f"{mod} ({e})")
    if failed:
        result["status"] = "FAIL"
        result["detail"] = f"Import errors: {'; '.join(failed)}"
    else:
        result["detail"] = f"{len(_REQUIRED_ROUTERS)} router modules importable"
    return result


def _check_configs(rc_root: str) -> dict:
    result = {"name": "configs", "status": "PASS", "detail": ""}
    if not rc_root:
        result["status"] = "WARN"
        result["detail"] = "METIS_RC_ROOT not set — skipped config checks"
        return result
    root = Path(rc_root)
    missing = [c for c in _REQUIRED_CONFIGS if not (root / c).exists()]
    if missing:
        result["status"] = "WARN"
        result["detail"] = f"Missing: {', '.join(missing)}"
    else:
        result["detail"] = f"{len(_REQUIRED_CONFIGS)} config files present"
    return result


def run_startup_eval() -> dict:
    """Run all checks and return the results dict. Always succeeds (never raises)."""
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    db_path = os.environ.get("METIS_DB", "")
    if not db_path and rc_root:
        db_path = str(Path(rc_root) / "system" / "app" / "data" / "metis.sqlite")

    app_dir = Path(__file__).parent
    templates_dir = app_dir / "templates"

    checks = []
    try:
        checks.append(_check_database(db_path))
    except Exception as e:
        checks.append({"name": "database", "status": "ERROR", "detail": str(e)})

    try:
        checks.append(_check_templates(templates_dir))
    except Exception as e:
        checks.append({"name": "templates", "status": "ERROR", "detail": str(e)})

    try:
        checks.append(_check_routers())
    except Exception as e:
        checks.append({"name": "routers", "status": "ERROR", "detail": str(e)})

    try:
        checks.append(_check_configs(rc_root))
    except Exception as e:
        checks.append({"name": "configs", "status": "ERROR", "detail": str(e)})

    overall = "PASS"
    for c in checks:
        if c["status"] == "FAIL":
            overall = "FAIL"
            break
        if c["status"] in ("WARN", "ERROR") and overall == "PASS":
            overall = "WARN"

    results = {
        "run_at": datetime.datetime.now().isoformat(),
        "overall": overall,
        "checks": checks,
    }

    # Save to eval-results.json (gitignored local config dir)
    if rc_root:
        out_path = Path(rc_root) / "system" / "config" / "eval-results.json"
    else:
        out_path = app_dir / "eval-results.json"

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    except Exception:
        pass

    # Log summary
    icons = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "ERROR": "✗"}
    for c in checks:
        icon = icons.get(c["status"], "?")
        fn = log.info if c["status"] == "PASS" else log.warning
        fn("[eval] %s %s — %s", icon, c["name"], c["detail"])

    if overall == "PASS":
        log.info("[eval] All checks passed")
    elif overall == "WARN":
        log.warning("[eval] Health check completed with warnings")
    else:
        log.error("[eval] Health check FAILED — check eval-results.json")

    return results
