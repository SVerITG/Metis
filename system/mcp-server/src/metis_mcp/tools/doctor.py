"""metis_doctor — one-screen health check for the Metis system.

Runs a battery of low-cost checks and returns a structured report. Designed
so a non-technical user can copy/paste the output into a support thread or
read the verdict in plain English from the dashboard.

Each check returns:
    {
        "name":     short label,
        "ok":       bool,
        "severity": "info" | "warn" | "fail",
        "detail":   one-line explanation,
    }

Top-level status:
    "ok"   — every check passed
    "warn" — at least one check is in warn state, none failed
    "fail" — at least one check failed
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_python() -> dict:
    import sys
    v = sys.version_info
    ok = v >= (3, 10)
    return {
        "name": "Python 3.10+",
        "ok": ok,
        "severity": "info" if ok else "fail",
        "detail": f"running {v.major}.{v.minor}.{v.micro}",
    }


def _check_metis_root() -> dict:
    root = paths.root
    ok = root.exists() and root.is_dir()
    return {
        "name": "METIS_RC_ROOT",
        "ok": ok,
        "severity": "info" if ok else "fail",
        "detail": str(root) if ok else f"missing or not a directory: {root}",
    }


def _check_db() -> dict:
    db = paths.db
    if not db.exists():
        return {
            "name": "SQLite database",
            "ok": False,
            "severity": "fail",
            "detail": f"not found at {db} — run setup-mcp.sh",
        }
    try:
        with sqlite3.connect(str(db)) as con:
            n_tables = con.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
        return {
            "name": "SQLite database",
            "ok": True,
            "severity": "info",
            "detail": f"{db.name} · {n_tables} tables · {round(db.stat().st_size / 1024)} KB",
        }
    except Exception as e:
        return {
            "name": "SQLite database",
            "ok": False,
            "severity": "fail",
            "detail": f"could not open: {e}",
        }


def _check_api_key() -> dict:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {
            "name": "Anthropic API key",
            "ok": True,
            "severity": "info",
            "detail": "set in environment",
        }
    env_file = paths.root / "system" / ".env"
    if env_file.exists():
        try:
            text = env_file.read_text(encoding="utf-8")
            if "ANTHROPIC_API_KEY" in text and "=" in text:
                return {
                    "name": "Anthropic API key",
                    "ok": True,
                    "severity": "info",
                    "detail": f"found in {env_file.relative_to(paths.root)}",
                }
        except Exception:
            pass
    return {
        "name": "Anthropic API key",
        "ok": False,
        "severity": "warn",
        "detail": (
            "not found — Claude Desktop and Claude Code provide their own; "
            "set ANTHROPIC_API_KEY for direct API calls"
        ),
    }


def _check_user_config() -> dict:
    cfg = paths.root / "system" / "config" / "user-config.yaml"
    if not cfg.exists():
        return {
            "name": "user-config.yaml",
            "ok": False,
            "severity": "warn",
            "detail": "not present — run /metis_config to create it",
        }
    try:
        text = cfg.read_text(encoding="utf-8")
        if 'name: ""' in text or 'name: ''' in text:
            return {
                "name": "user-config.yaml",
                "ok": False,
                "severity": "warn",
                "detail": "exists but `name` is empty — run /metis_config to personalise",
            }
        return {
            "name": "user-config.yaml",
            "ok": True,
            "severity": "info",
            "detail": f"{cfg.relative_to(paths.root)} · {len(text)} bytes",
        }
    except Exception as e:
        return {
            "name": "user-config.yaml",
            "ok": False,
            "severity": "warn",
            "detail": f"unreadable: {e}",
        }


def _check_agents() -> dict:
    agents_dir = paths.root / "agents"
    if not agents_dir.exists():
        return {
            "name": "Agent folder",
            "ok": False,
            "severity": "fail",
            "detail": f"not found at {agents_dir}",
        }
    folders = [p for p in agents_dir.iterdir() if p.is_dir()]
    retired = [p for p in folders if (p / "RETIRED.md").exists()]
    return {
        "name": "Agents",
        "ok": True,
        "severity": "info",
        "detail": f"{len(folders) - len(retired)} active, {len(retired)} retired",
    }


def _check_skills() -> dict:
    skills_dir = paths.root / ".claude" / "skills"
    if not skills_dir.exists():
        return {
            "name": ".claude/skills folder",
            "ok": False,
            "severity": "fail",
            "detail": f"not found at {skills_dir}",
        }
    n = sum(1 for p in skills_dir.iterdir() if p.is_dir())
    return {
        "name": ".claude/skills",
        "ok": True,
        "severity": "info",
        "detail": f"{n} slash commands available",
    }


def _check_legacy_paths() -> dict:
    """Look for legacy folder names (02_agents/, 07_outputs/, etc.) that
    survived the Phase 5.4 rename. Anything found is a documentation drift
    bug, not an immediate failure."""
    needles = [
        "02_agents/", "05_sources/", "06_library/",
        "07_outputs/", "08_system/", "00_inbox/",
    ]
    hits: list[str] = []
    for sub in ("agents", ".claude/skills", "system/config"):
        d = paths.root / sub
        if not d.exists():
            continue
        for path in d.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for n in needles:
                if n in text:
                    hits.append(str(path.relative_to(paths.root)))
                    break
        if len(hits) > 8:
            break
    if not hits:
        return {
            "name": "Folder-rename hygiene",
            "ok": True,
            "severity": "info",
            "detail": "no legacy paths detected",
        }
    return {
        "name": "Folder-rename hygiene",
        "ok": False,
        "severity": "warn",
        "detail": f"{len(hits)} file(s) still reference legacy paths (e.g. {hits[0]})",
    }


def _check_mcp_imports() -> dict:
    """Import a representative tool module to verify the package is healthy."""
    try:
        import metis_mcp.tools.literature  # noqa: F401
        import metis_mcp.tools.ideas  # noqa: F401
        import metis_mcp.tools.guardrails  # noqa: F401
        return {
            "name": "MCP tool imports",
            "ok": True,
            "severity": "info",
            "detail": "core tool modules import cleanly",
        }
    except Exception as e:
        return {
            "name": "MCP tool imports",
            "ok": False,
            "severity": "fail",
            "detail": f"import error: {e}",
        }


def _check_env_files_safe() -> dict:
    """Verify .env is not tracked by git (best-effort: check gitignore)."""
    gi = paths.root.parent / ".gitignore"
    if not gi.exists():
        gi = paths.root / ".gitignore"
    if not gi.exists():
        return {
            "name": "Secrets gitignore",
            "ok": False,
            "severity": "warn",
            "detail": "no .gitignore found — verify .env is excluded before pushing",
        }
    try:
        text = gi.read_text(encoding="utf-8")
        if ".env" in text:
            return {
                "name": "Secrets gitignore",
                "ok": True,
                "severity": "info",
                "detail": ".env is excluded from git",
            }
        return {
            "name": "Secrets gitignore",
            "ok": False,
            "severity": "warn",
            "detail": ".env is NOT in .gitignore — risk of leaking the API key",
        }
    except Exception as e:
        return {
            "name": "Secrets gitignore",
            "ok": False,
            "severity": "warn",
            "detail": f"could not read .gitignore: {e}",
        }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def _check_embedding() -> dict:
    """The RAG / semantic-search engine: fastembed + sqlite-vec must be installed."""
    missing = []
    for mod, label in [("fastembed", "fastembed"), ("sqlite_vec", "sqlite-vec")]:
        try:
            __import__(mod)
        except Exception:
            missing.append(label)
    if missing:
        return {
            "name": "Embedding / RAG engine", "ok": False, "severity": "warn",
            "detail": f"missing {', '.join(missing)} — semantic search + knowledge layer are OFF. "
                      "Fix: reinstall with the [embedding] extra.",
        }
    return {"name": "Embedding / RAG engine", "ok": True, "severity": "info",
            "detail": "fastembed + sqlite-vec installed"}


def _check_knowledge_layer() -> dict:
    """Is there any indexed knowledge to ground answers in?"""
    try:
        con = sqlite3.connect(str(paths.db))
        n = con.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
        con.close()
    except Exception:
        return {"name": "Knowledge layer", "ok": True, "severity": "info",
                "detail": "not initialised yet — index docs with build_pdf_knowledge_db()"}
    if n == 0:
        return {"name": "Knowledge layer", "ok": False, "severity": "warn",
                "detail": "no documents indexed — the RAG layer has nothing to search yet"}
    return {"name": "Knowledge layer", "ok": True, "severity": "info",
            "detail": f"{n:,} chunks indexed and searchable"}


def _check_dashboard() -> dict:
    """Is the dashboard currently serving on :8080? (Not running is fine.)"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", 8080))
        s.close()
        return {"name": "Dashboard (:8080)", "ok": True, "severity": "info",
                "detail": "running — open http://localhost:8080"}
    except Exception:
        return {"name": "Dashboard (:8080)", "ok": True, "severity": "info",
                "detail": "not running — start it from the Metis desktop icon or run.sh"}
    finally:
        try:
            s.close()
        except Exception:
            pass


def _check_claude_desktop() -> dict:
    """Is the metis-rc MCP server registered with Claude Desktop? (Windows/WSL.)"""
    import glob
    import json
    candidates = glob.glob("/mnt/c/Users/*/AppData/Roaming/Claude/claude_desktop_config.json")
    if not candidates:
        return {"name": "Claude Desktop link", "ok": True, "severity": "info",
                "detail": "Claude Desktop config not found (Desktop may not be installed here)"}
    try:
        cfg = json.loads(Path(candidates[0]).read_text(encoding="utf-8"))
        if "metis-rc" in (cfg.get("mcpServers") or {}):
            return {"name": "Claude Desktop link", "ok": True, "severity": "info",
                    "detail": "metis-rc is registered — Metis is reachable in Claude Desktop"}
        return {"name": "Claude Desktop link", "ok": False, "severity": "warn",
                "detail": "Claude Desktop found but metis-rc not registered — re-run setup-mcp.sh"}
    except Exception as e:
        return {"name": "Claude Desktop link", "ok": False, "severity": "warn",
                "detail": f"could not read Claude Desktop config ({type(e).__name__})"}


def run_doctor() -> dict:
    """Run all checks. Returns the structured report (Python dict)."""
    checks = [
        _check_python(),
        _check_metis_root(),
        _check_db(),
        _check_api_key(),
        _check_embedding(),
        _check_knowledge_layer(),
        _check_user_config(),
        _check_agents(),
        _check_skills(),
        _check_dashboard(),
        _check_claude_desktop(),
        _check_legacy_paths(),
        _check_mcp_imports(),
        _check_env_files_safe(),
    ]

    has_fail = any(not c["ok"] and c["severity"] == "fail" for c in checks)
    has_warn = any(not c["ok"] and c["severity"] == "warn" for c in checks)
    if has_fail:
        status = "fail"
        summary = "One or more checks failed. Fix the FAIL rows before relying on Metis."
    elif has_warn:
        status = "warn"
        summary = "Metis works but has rough edges. The WARN rows are worth fixing soon."
    else:
        status = "ok"
        summary = "All checks passed. Metis is healthy."

    return {"status": status, "summary": summary, "checks": checks}


@app.tool()
async def metis_doctor() -> list[TextContent]:
    """Run a one-screen health check on Metis.

    Verifies Python version, the SQLite database, the Anthropic API key, your
    user-config.yaml, agent and skill folders, folder-rename hygiene, MCP
    imports, and that `.env` is gitignored. Returns a structured report so the
    dashboard or a CLI session can render it cleanly.

    Use when:
      - Something feels broken and you want a single command to triage.
      - Just before publishing the repo, to catch hygiene issues.
      - After a `git pull`, to confirm nothing regressed.
    """
    report = run_doctor()
    _glyph = {"ok": "✓", "warn": "⚠", "fail": "✗"}
    _verdict = {"ok": "✓ HEALTHY", "warn": "⚠ NEEDS ATTENTION", "fail": "✗ PROBLEMS FOUND"}
    bar = "═" * 52
    lines = [
        bar,
        "  Metis · Research Cortex — Health Check",
        bar,
        f"  Status: {_verdict.get(report['status'], report['status'].upper())}",
        f"  {report['summary']}",
        "",
    ]
    for c in report["checks"]:
        g = _glyph["ok"] if c["ok"] else _glyph.get(c["severity"], "•")
        lines.append(f"  {g}  {c['name']:<26} {c['detail']}")
    lines.append("─" * 52)

    # Plain-language next step for the most severe open item
    fail = next((c for c in report["checks"] if not c["ok"] and c["severity"] == "fail"), None)
    warn = next((c for c in report["checks"] if not c["ok"] and c["severity"] == "warn"), None)
    focus = fail or warn
    if focus:
        lines.append(f"  Next step → {focus['name']}: {focus['detail']}")
    else:
        lines.append("  All clear — Metis is healthy.")
    return [TextContent(type="text", text="\n".join(lines))]
