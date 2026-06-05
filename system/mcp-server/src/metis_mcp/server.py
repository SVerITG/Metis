"""MCP server bootstrap, tool registration, and main entry point.

WhatsApp webhook runs as a separate FastAPI process (see webhook.py).
Start with: uvicorn metis_mcp.webhook:app --port 8000
"""

# Use the shared app instance to avoid split registrations across tool modules.
# All tool modules should import `app` from either server.py or app_instance.py —
# both now point to the same object.
from metis_mcp.app_instance import app  # noqa: F401

# ── Resilient tool loading ───────────────────────────────────────────────────
# Each tool module registers handlers via @app.tool() on import. Historically
# these were imported atomically (`from metis_mcp.tools import a, b, c, ...`),
# which meant ONE module with a bad import (missing optional dep, syntax error)
# took down the ENTIRE server — no tools at all. Now each module loads in
# isolation: a failure is logged and skipped, the rest of the server still works.
import importlib as _importlib
import logging as _logging

_log = _logging.getLogger("metis")

# Order matters only for readability — registration is independent per module.
TOOL_MODULES = [
    "agents", "literature", "notes", "projects", "reviews", "tasks", "ideas",
    "safety", "files", "intelligence", "library", "config_tools", "images",
    "thinking_profile", "self_improvement", "transcription", "memory", "pipeline",
    "vector_memory", "guardrails", "knowledge_graph", "observability",
    "anonymization", "backup", "brainstorm", "data_tools", "handoff", "improvement",
    "observation", "content_scan", "zotero", "doctor", "ref_miner", "fulltext_index",
    "user_profile", "literature_monitor", "meetings", "course_builder",
    "paperqa_search", "voice_capture", "knowledge_db", "session_memory",
    "memory_curator", "research", "research_timeline", "project_tracker", "dhis2",
    "discovery", "prompts",
]

LOADED_MODULES: list[str] = []
FAILED_MODULES: dict[str, str] = {}

for _name in TOOL_MODULES:
    try:
        _importlib.import_module(f"metis_mcp.tools.{_name}")
        LOADED_MODULES.append(_name)
    except Exception as _exc:  # noqa: BLE001 — never let one module crash startup
        FAILED_MODULES[_name] = f"{type(_exc).__name__}: {_exc}"
        _log.error("Tool module '%s' failed to load (skipped): %s", _name, _exc)

if FAILED_MODULES:
    _log.warning(
        "%d/%d tool modules loaded; %d skipped: %s",
        len(LOADED_MODULES), len(TOOL_MODULES), len(FAILED_MODULES),
        ", ".join(FAILED_MODULES),
    )


# ── Domain-specific tool loading ─────────────────────────────────────────────
# When METIS_TOOL_SUBSETS=1 and METIS_AGENT_SUBSET=<slug> are set, strip tools
# not in the agent's declared subset. This reduces the tools/list token cost
# by 50–80% for targeted agent sessions.
#
# Example (from run.sh or a per-agent launcher):
#   METIS_TOOL_SUBSETS=1 METIS_AGENT_SUBSET=librarian python -m metis_mcp.server
import os as _os

# Tool subset loading — active by default when METIS_TOOL_SUBSETS=1 (set in run.sh).
# Pass METIS_TOOL_SUBSETS=0 to load all tools (developer / debug mode).
# When METIS_AGENT_SUBSET is not set, the "_default" subset from tool-subsets.json is used.
if _os.environ.get("METIS_TOOL_SUBSETS", "0") == "1":
    _agent = _os.environ.get("METIS_AGENT_SUBSET", "_default").strip() or "_default"
    from metis_mcp.subset_loader import apply_tool_subset
    _removed = apply_tool_subset(app, _agent)
    import logging as _logging
    _logging.getLogger("metis").info(
        "Tool subset active: agent=%s, %d tools removed, %d exposed",
        _agent, _removed, len(app._tool_manager._tools),
    )


def _startup_selfcheck() -> None:
    """Run a fast health self-check at server start and log a clear summary.

    Never raises — diagnostics must not block the server. Writes a machine-readable
    health snapshot to system/config/mcp-health.json so the dashboard / installer
    can show whether the last server start was healthy.
    """
    log = _logging.getLogger("metis")
    # 1) Tool-load summary (from the resilient loader above)
    try:
        tool_count = len(getattr(app, "_tool_manager")._tools) if hasattr(app, "_tool_manager") else 0
    except Exception:
        tool_count = 0
    log.info("Metis MCP: %d/%d tool modules loaded, %d tools registered.",
             len(LOADED_MODULES), len(TOOL_MODULES), tool_count)

    # 2) Environment health via the doctor checks
    report = {"status": "unknown", "checks": []}
    try:
        from metis_mcp.tools.doctor import run_doctor
        report = run_doctor()
        fails = [c["name"] for c in report.get("checks", []) if not c.get("ok") and c.get("severity") == "fail"]
        warns = [c["name"] for c in report.get("checks", []) if not c.get("ok") and c.get("severity") == "warn"]
        if fails:
            log.error("Metis MCP startup health: FAIL — %s", ", ".join(fails))
        elif warns:
            log.warning("Metis MCP startup health: WARN — %s", ", ".join(warns))
        else:
            log.info("Metis MCP startup health: OK — all checks passed.")
    except Exception as exc:
        log.warning("Metis MCP self-check could not run: %s", exc)

    # 3) Stale-install detection — the failure mode from 2026-06-01: the server runs
    #    an installed COPY of the package, so source edits don't take effect until
    #    reinstall. Warn loudly if the installed code looks older than the repo source.
    try:
        import metis_mcp, os, datetime
        installed_file = getattr(metis_mcp, "__file__", "") or ""
        from metis_mcp.config import paths as _paths
        src_server = _paths.root / "system" / "mcp-server" / "src" / "metis_mcp" / "server.py"
        if installed_file and "site-packages" in installed_file and src_server.exists():
            inst_server = os.path.join(os.path.dirname(installed_file), "server.py")
            if os.path.exists(inst_server):
                src_m = src_server.stat().st_mtime
                inst_m = os.path.getmtime(inst_server)
                if src_m > inst_m + 5:  # source newer than installed by >5s
                    log.warning(
                        "Metis MCP may be running STALE installed code "
                        "(source is newer than the installed package). "
                        "Run: bash tools/reinstall-mcp.sh  then reconnect the server."
                    )
                    report["stale_install"] = True
    except Exception:
        pass

    # 4) Persist a health snapshot (best-effort)
    try:
        import json
        from metis_mcp.config import paths as _paths
        hp = _paths.root / "system" / "config" / "mcp-health.json"
        hp.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "checked_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "status": report.get("status", "unknown"),
            "tools_registered": tool_count,
            "modules_loaded": len(LOADED_MODULES),
            "modules_failed": FAILED_MODULES,
            "stale_install": report.get("stale_install", False),
        }
        hp.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    except Exception:
        pass


def run():
    # Apply any pending schema migrations BEFORE serving tools.
    # See metis_mcp/migrations.py — this is what prevented us from ever
    # repeating the brainstorm_sessions title-vs-topic drift from R8 (2026-05-25).
    try:
        from metis_mcp.migrations import run_on_default_db
        result = run_on_default_db()
        log = _logging.getLogger("metis")
        if result["applied"]:
            log.info("Schema migrations applied: %s", ", ".join(result["applied"]))
        if result["errors"]:
            log.warning("Schema migrations skipped with errors: %s", result["errors"])
    except Exception as _exc:
        # Don't block server start if migrations module fails to import.
        _logging.getLogger("metis").warning("Schema migration check failed: %s", _exc)

    # Self-diagnose and log a health summary (never blocks startup).
    try:
        _startup_selfcheck()
    except Exception as _exc:
        _logging.getLogger("metis").warning("Startup self-check failed: %s", _exc)

    app.run()


if __name__ == "__main__":
    run()
