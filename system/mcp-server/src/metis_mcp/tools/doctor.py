"""Health checks: the install doctor's doors, and the server's own self-diagnosis.

What a PERSON runs — metis_doctor (report) and verify_install (repair) — is the
install doctor, system/install/metis_verify.py, driven by the one list of
essentials in system/install/essentials.json. The dashboard and the installers
run the same script, so no two of them can give different answers.

run_doctor() below is something else: the server's own fast, in-process
self-diagnosis at start-up. It must stay cheap and must never start a server
(the install doctor starts one to test it — calling that from start-up would
start servers that start servers).

run_doctor runs a battery of low-cost checks and returns a structured report. Designed
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

import re
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
        # This was a substring test: `'name: ""' in text or 'name: ''' in text`.
        # Python concatenates adjacent literals, so `'name: '''` is just
        # `'name: '` — and the whole condition collapsed to "does the file
        # contain the characters `name: `". It does, always. So the check warned
        # "`name` is empty — run /metis_config" on every run of every install,
        # including this one where the name is plainly `the researcher`. A permanent false
        # warning is worse than no check: it trains you to ignore the report.
        # Read the actual value.
        name = ""
        try:
            import yaml
            data = yaml.safe_load(text) or {}
            name = str((data.get("user") or {}).get("name") or "").strip()
        except Exception:
            m = re.search(r"^\s*name:\s*(.*)$", text, re.MULTILINE)
            name = (m.group(1).strip().strip('"\'') if m else "")
        if not name:
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
            "detail": f"{cfg.relative_to(paths.root)} · name set to {name!r}",
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


def _check_session_memory() -> dict:
    """Is session memory actually being recorded, and recently? A stale or empty
    session_summaries table means Metis isn't capturing what gets done — the exact
    thing a user checking 'is my memory working' wants confirmed."""
    import datetime
    db = paths.db
    if not db.exists():
        return {"name": "Session memory", "ok": False, "severity": "fail",
                "detail": "database missing"}
    try:
        with sqlite3.connect(str(db)) as con:
            n = con.execute("SELECT COUNT(*) FROM session_summaries").fetchone()[0]
            last = con.execute("SELECT MAX(created_at) FROM session_summaries").fetchone()[0]
    except Exception as e:
        return {"name": "Session memory", "ok": False, "severity": "warn",
                "detail": f"could not read session_summaries: {e}"}
    if not n:
        return {"name": "Session memory", "ok": False, "severity": "warn",
                "detail": "no sessions recorded yet — save_session_summary() has never run"}
    age_days = None
    try:
        d = datetime.datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        age_days = (datetime.datetime.now(datetime.timezone.utc) - d).days
    except Exception:
        pass
    if age_days is not None and age_days > 14:
        return {"name": "Session memory", "ok": False, "severity": "warn",
                "detail": f"{n} recorded, but last was {age_days}d ago — recording may have stalled"}
    when = str(last)[:10]
    return {"name": "Session memory", "ok": True, "severity": "info",
            "detail": f"{n} sessions recorded · last {when} — actively recording"}


def _check_projects() -> dict:
    """Are projects registered so the dashboard + routing can see them?"""
    db = paths.db
    if not db.exists():
        return {"name": "Projects", "ok": False, "severity": "fail", "detail": "database missing"}
    try:
        with sqlite3.connect(str(db)) as con:
            has = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
            ).fetchone()
            if not has:
                return {"name": "Projects", "ok": False, "severity": "warn",
                        "detail": "no projects table — none registered yet"}
            total = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
            try:
                active = con.execute(
                    "SELECT COUNT(*) FROM projects WHERE COALESCE(status,'active') != 'archived'"
                ).fetchone()[0]
            except Exception:
                active = total
    except Exception as e:
        return {"name": "Projects", "ok": False, "severity": "warn",
                "detail": f"could not read projects: {e}"}
    if not total:
        return {"name": "Projects", "ok": False, "severity": "warn",
                "detail": "no projects registered — add one so Metis can track your work"}
    return {"name": "Projects", "ok": True, "severity": "info",
            "detail": f"{active} active · {total} total registered"}


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


def _check_installed_matches_source() -> dict:
    """Is the RUNNING MCP package the same code as the source tree?

    The server runs an INSTALLED COPY in the venv, not the source. A `git pull`
    alone leaves it executing old code, silently. On 2026-07-14 the repo was fully
    current while the running server was SIX DAYS stale — 7 files behind, quietly
    missing the memory-gateway / session-memory / user-profile tools. Nothing
    anywhere reported it. This check exists so that can never be invisible again.
    """
    import filecmp

    name = "MCP install is current"
    src_dir = paths.root / "system" / "mcp-server" / "src" / "metis_mcp"
    installed_dir = Path(__file__).resolve().parent.parent  # …/site-packages/metis_mcp

    if not src_dir.is_dir():
        return {"name": name, "ok": True, "severity": "info",
                "detail": "no source tree here (installed-only machine)"}

    try:
        if installed_dir.resolve() == src_dir.resolve():
            return {"name": name, "ok": True, "severity": "info",
                    "detail": "running directly from source (editable install)"}
    except OSError:
        pass

    stale: list[str] = []
    for src_file in src_dir.rglob("*.py"):
        if "__pycache__" in src_file.parts:
            continue
        rel = src_file.relative_to(src_dir)
        inst_file = installed_dir / rel
        if not inst_file.exists() or not filecmp.cmp(src_file, inst_file, shallow=False):
            stale.append(str(rel))

    if not stale:
        return {"name": name, "ok": True, "severity": "info",
                "detail": "installed package matches source"}

    shown = ", ".join(stale[:4]) + (f" (+{len(stale) - 4} more)" if len(stale) > 4 else "")
    return {
        "name": name,
        "ok": False,
        "severity": "fail",
        "detail": (
            f"{len(stale)} file(s) STALE — the server is running OLD code: {shown}. "
            "Tools you think exist may not. Fix: bash tools/reinstall-mcp.sh, "
            "then /mcp → reconnect 'metis-rc' (Claude Desktop: quit and reopen)."
        ),
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
    """Can the RAG / semantic-search engine actually EMBED something?

    This used to check only that `fastembed` and `sqlite_vec` import. On
    2026-08-24 it reported OK while every embedding feature was dead: the
    packages were installed, but the 132 MB model file was on the other
    computer's disk and `HF_HUB_OFFLINE=1` meant it could never be fetched.
    Semantic search 500'd on every call and the health check said "ok".

    An installed library is not a working feature. So embed one short string —
    it costs one model load, and the model is a process-wide singleton the
    server needs warm anyway, so the cost is paid once and not wasted.
    """
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
    try:
        from metis_mcp.embeddings import embed, EMBEDDING_DIM
        vec = embed(["metis health check"])[0]
    except Exception as e:
        return {
            "name": "Embedding / RAG engine", "ok": False, "severity": "fail",
            "detail": f"packages installed but the model will NOT load — semantic "
                      f"search and the knowledge layer are OFF. {str(e)[:220]}",
        }
    if len(vec) != EMBEDDING_DIM:
        return {
            "name": "Embedding / RAG engine", "ok": False, "severity": "fail",
            "detail": f"model returned {len(vec)} dims, index expects {EMBEDDING_DIM} — "
                      "stored vectors and new ones are incompatible.",
        }
    return {"name": "Embedding / RAG engine", "ok": True, "severity": "info",
            "detail": f"model loads and embeds ({EMBEDDING_DIM} dims)"}


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
    """Is the dashboard currently serving? Reads the live port written by run.sh."""
    import socket
    try:
        port = int((paths.root / "system" / "app-py" / ".metis-port").read_text().strip())
    except Exception:
        port = 8080
    label = f"Dashboard (:{port})"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return {"name": label, "ok": True, "severity": "info",
                "detail": f"running — open http://localhost:{port}"}
    except Exception:
        return {"name": label, "ok": False, "severity": "warn",
                "detail": "not running (this is fine — just not started). "
                          "Restart with:  bash system/app-py/run.sh  "
                          "(or the Metis desktop icon)"}
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
        _check_session_memory(),
        _check_projects(),
        _check_agents(),
        _check_skills(),
        _check_dashboard(),
        _check_claude_desktop(),
        _check_legacy_paths(),
        _check_mcp_imports(),
        _check_installed_matches_source(),
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


async def _install_doctor(fix: bool) -> str:
    """Run the install doctor (system/install/metis_verify.py) and return its report.

    The one doctor: the installers, the daily task, the dashboard and these
    tools all run it, so they cannot disagree. It checks every entry in
    system/install/essentials.json — computer, Metis's programs, each AI app,
    dashboard, background tasks, data — and with fix=True repairs what it can.
    """
    import asyncio
    import sys

    script = paths.root / "system" / "install" / "metis_verify.py"
    if not script.exists():
        return "The install doctor is not included in this installation."
    args = [sys.executable, str(script)] + (["--fix"] if fix else [])
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        cwd=str(paths.root))
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=900)
    except asyncio.TimeoutError:
        proc.kill()
        return "The check did not finish within 15 minutes."
    return out.decode("utf-8", "replace").strip()


@app.tool()
async def metis_doctor() -> list[TextContent]:
    """Check everything Metis needs on this computer, without changing anything.

    The install doctor's report: the computer (version, disk, internet), Metis's
    own programs (Python, tools, search engine, search model), each AI app it
    connects to (Claude Desktop, Claude Code, VS Code, Cursor) and whether
    Metis starts from that app's settings, the dashboard and its morning scans,
    the scheduled tasks, and the data (database, specialists, profile, updates).
    To also repair, use verify_install. Tell the person the result in plain words.
    """
    return [TextContent(type="text", text=await _install_doctor(fix=False))]


@app.tool()
async def verify_install(fix: bool = True) -> list[TextContent]:
    """Check everything Metis needs on this computer, and repair what can be repaired.

    The install doctor — the same check the installers run and schedule daily —
    over the list in system/install/essentials.json: computer, Metis's
    programs, every AI app it connects to and whether Metis starts from that
    app's own settings, the dashboard and its scans, the scheduled tasks, and
    the data. With fix=True (default) it reinstalls broken or outdated tools,
    reconnects apps (merging, never replacing their other connectors), adds
    missing database tables, downloads the search model, starts the dashboard
    and re-creates missing scheduled tasks — then checks again.

    Use when the person says something is not working, after an update, or when
    they ask whether everything is set up. Tell them the result in plain words;
    if an app was reconnected, they must quit it completely (Claude Desktop:
    also from the tray) and open it again.
    """
    return [TextContent(type="text", text=await _install_doctor(fix=fix))]


@app.tool()
async def update_metis(confirm: bool = False) -> list[TextContent]:
    """Check for a newer version of Metis and, with confirm=True, install it.

    For installs made by MetisSetup.exe on Windows. Without confirm it only
    reports the installed and the newest published version and what updating
    does — ask the person before calling again with confirm=True. Updating
    keeps their profile, library, projects and settings.

    After confirm=True the installer shows a small progress window and stops
    Metis while it works, so this conversation loses Metis for a few minutes.
    Tell the person: wait until the progress window closes, then quit Claude
    Desktop completely (also from the tray) and open it again.
    """
    import asyncio
    from metis_mcp import updates
    from metis_mcp.config import use_system_certificates

    current = updates.installed_version(paths.root)
    if not current:
        return [TextContent(type="text", text=(
            "This copy of Metis was not installed with the Windows setup program, so it "
            "cannot update itself. It is updated the way it was installed (for example "
            "git pull and setup-mcp.sh)."))]
    use_system_certificates()
    latest = await asyncio.to_thread(updates.latest_release)
    if latest is None:
        return [TextContent(type="text", text=(
            f"Installed: Metis {current}. The list of releases could not be reached "
            "(no connection, or GitHub is blocked here), so it is unknown whether an "
            "update exists. Try again later."))]
    if not updates.is_newer(latest["version"], current):
        return [TextContent(type="text", text=f"Metis {current} is the newest version.")]
    if not confirm:
        return [TextContent(type="text", text=(
            f"Metis {latest['version']} is available; this computer has {current}.\n"
            "Updating downloads the setup program (about 1 minute), then runs it with "
            "a progress window and no questions; profile, library, projects and "
            "settings are kept. Metis is unavailable for 5–10 minutes meanwhile.\n\n"
            f"What is new:\n{latest['notes']}\n\n"
            "Ask the person; if they agree, call update_metis(confirm=True)."))]
    try:
        dest = await asyncio.to_thread(updates.download_and_launch, latest)
    except Exception as exc:
        return [TextContent(type="text", text=(
            f"The update could not be started: {exc}. It can be installed by hand: "
            f"download {latest['name']} from https://github.com/{updates.REPO}/releases/latest "
            "and run it."))]
    return [TextContent(type="text", text=(
        f"The update to Metis {latest['version']} has started ({dest.name}). A small "
        "progress window is open. When it closes, quit Claude Desktop completely "
        "(also from the tray icon) and open it again."))]
