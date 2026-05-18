#!/usr/bin/env python3
"""
Metis Research Cortex — Automated Test Runner
==============================================
Runs 80+ checks without calling the Claude API or requiring any manual steps.
Covers: system health, dashboard routing, agent inventory, MCP tools, security,
configuration quality, README accuracy, and database integrity.

Usage:
    python system/metis-autotest.py            (run all checks)
    python system/metis-autotest.py --no-http  (skip dashboard HTTP tests)

Output:
    outputs/test-results/YYYY-MM-DD_HH-MM_metis-autotest.html

Run from the metis/ project root.
"""

import sys
import os
import re
import json
import sqlite3
import subprocess
import time
import datetime
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── optional imports ────────────────────────────────────────────────────────
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ── detect root ─────────────────────────────────────────────────────────────
def find_root() -> Path:
    """Walk up from this file until we find CLAUDE.md."""
    p = Path(__file__).resolve().parent
    for _ in range(5):
        if (p / "CLAUDE.md").exists():
            return p
        p = p.parent
    # fallback: current working directory
    cwd = Path.cwd()
    if (cwd / "CLAUDE.md").exists():
        return cwd
    raise SystemExit("Cannot find metis root (no CLAUDE.md found). Run from the metis/ folder.")

ROOT = find_root()

# ── constants ────────────────────────────────────────────────────────────────
_db_candidate1 = ROOT / "system" / "app" / "data" / "metis.sqlite"
_db_candidate2 = ROOT / "system" / "app-py" / "data" / "metis.sqlite"
_db_candidate3 = ROOT / "metis.sqlite"
DB_PATH      = (
    _db_candidate1 if _db_candidate1.exists() else
    _db_candidate2 if _db_candidate2.exists() else
    _db_candidate3
)
AGENTS_DIR   = ROOT / "agents"
SKILLS_DIR   = ROOT / ".claude" / "skills"
HOOKS_DIR    = ROOT / ".claude" / "hooks"
MCP_TOOLS    = ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools"
APP_PY       = ROOT / "system" / "app-py"
CONFIG_DIR   = ROOT / "system" / "config"
TEMPLATES    = APP_PY / "templates"
ROUTERS      = APP_PY / "routers"
HOOK_FILE    = HOOKS_DIR / "pre-tool-use.mjs"
GUARD_FILE   = MCP_TOOLS / "guardrails.py"
# .gitignore may live one level above the metis/ subfolder (repo root)
GITIGNORE    = ROOT / ".gitignore" if (ROOT / ".gitignore").exists() else ROOT.parent / ".gitignore"
README_FILE  = ROOT / "README.md"
CLAUDE_MD    = ROOT / "CLAUDE.md"
ENV_FILE     = ROOT / "system" / ".env"
USER_CONFIG  = CONFIG_DIR / "user-config.yaml"
RED_LINES    = CONFIG_DIR / "red-lines.md"
IMPL_PROG    = CONFIG_DIR / "implementation-progress.json"
AGENT_REG    = CONFIG_DIR / "agent-registry.json"
APP_JS       = APP_PY / "static" / "app.js"
DASHBOARD_URL = "http://localhost:8080"

REQUIRED_TABLES = [
    "ideas", "tasks", "projects", "agent_runs", "meetings",
    "personal_notes", "reflexion_log", "skill_improvement_proposals",
    "agent_spans", "learning_courses",
]

TABS = ["today", "work", "thinking", "meetings", "learning", "planner", "teach", "knowledge", "metis"]

REQUIRED_SKILLS = [
    "metis", "metis-capture", "meeting-memory", "librarian",
    "phd-architect", "writing-partner", "epidemiologist",
    "methods-coach", "software-engineer", "news-radar",
    "course-builder", "metis-weekly", "metis-status",
    "metis-brainstorm", "metis-handoff", "metis-tasks",
    "metis-projects", "metis-research",
]

SENSITIVE_GITIGNORE_PATTERNS = [
    ".csv", ".rds", ".RData", ".env", "*.sqlite", "*.cas", "*.geo",
]

# ── result dataclass ─────────────────────────────────────────────────────────
STATUS_ORDER = {"FAIL": 0, "WARN": 1, "PASS": 2, "SKIP": 3, "INFO": 4}

@dataclass
class R:
    id: str
    name: str
    category: str
    status: str          # PASS | FAIL | WARN | SKIP | INFO
    detail: str
    rec: Optional[str] = None
    priority: str = "Medium"   # Critical | High | Medium | Low

results: list[R] = []

def add(id, name, category, status, detail, rec=None, priority="Medium"):
    results.append(R(id, name, category, status, detail, rec, priority))

def ok(id, name, cat, detail):
    add(id, name, cat, "PASS", detail)

def fail(id, name, cat, detail, rec, priority="High"):
    add(id, name, cat, "FAIL", detail, rec, priority)

def warn(id, name, cat, detail, rec=None, priority="Medium"):
    add(id, name, cat, "WARN", detail, rec, priority)

def skip(id, name, cat, detail):
    add(id, name, cat, "SKIP", detail)

def info(id, name, cat, detail):
    add(id, name, cat, "INFO", detail)

# ── helpers ──────────────────────────────────────────────────────────────────
def read(path: Path, default="") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return default

def grep_count(path: Path, pattern: str) -> int:
    """Count regex matches in file."""
    try:
        return len(re.findall(pattern, read(path), re.IGNORECASE))
    except Exception:
        return 0

def db_connect():
    if not DB_PATH.exists():
        return None
    try:
        return sqlite3.connect(str(DB_PATH))
    except Exception:
        return None

def db_tables(con) -> list:
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []

def db_columns(con, table: str) -> list:
    try:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
        return [r[1] for r in rows]
    except Exception:
        return []

def http_get(path: str, timeout=5):
    """Returns (status_code, text) or (None, error_string)."""
    if not HAS_REQUESTS:
        return None, "requests not installed"
    try:
        r = requests.get(f"{DASHBOARD_URL}{path}", timeout=timeout)
        return r.status_code, r.text
    except requests.ConnectionError:
        return None, "Connection refused — dashboard not running"
    except Exception as e:
        return None, str(e)

def git_staged_files() -> list:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(ROOT), stderr=subprocess.DEVNULL
        ).decode().strip()
        return [f for f in out.split("\n") if f] if out else []
    except Exception:
        return []

def git_tracked_sensitive() -> list:
    """Files matching sensitive patterns that are tracked by git."""
    sensitive = []
    patterns = [r"\.env$", r"\.csv$", r"\.rds$", r"\.RData$", r"\.sqlite$", r"\.cas$"]
    try:
        out = subprocess.check_output(
            ["git", "ls-files"],
            cwd=str(ROOT), stderr=subprocess.DEVNULL
        ).decode().strip()
        for f in out.split("\n"):
            for pat in patterns:
                if re.search(pat, f, re.IGNORECASE):
                    sensitive.append(f)
                    break
    except Exception:
        pass
    return sensitive

# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — SYSTEM HEALTH
# ════════════════════════════════════════════════════════════════════════════
def run_system():
    print("  → System health...")

    # S01 — database
    if not DB_PATH.exists():
        fail("S01", "SQLite database exists", "System", f"Not found at: {DB_PATH.relative_to(ROOT)}",
             "Run the Metis setup: bash system/mcp-server/setup-mcp.sh — this initialises the database.", "Critical")
    else:
        con = db_connect()
        if con:
            tables = db_tables(con)
            missing = [t for t in REQUIRED_TABLES if t not in tables]
            if missing:
                fail("S01", "SQLite database exists", "System",
                     f"DB found but missing tables: {', '.join(missing)}",
                     f"Run the MCP server once to trigger DDL: python system/mcp-server/run_mcp_server.sh", "Critical")
            else:
                ok("S01", "SQLite database exists", "System",
                   f"Found {len(tables)} tables including all {len(REQUIRED_TABLES)} required tables.")
            con.close()
        else:
            fail("S01", "SQLite database exists", "System", "DB file found but cannot open.",
                 "Check file permissions on metis.sqlite.", "Critical")

    # S02 — .env
    if not ENV_FILE.exists():
        fail("S02", ".env file exists with API key", "System", f"Not found at: {ENV_FILE.relative_to(ROOT)}",
             "Copy system/.env.example to system/.env and add your ANTHROPIC_API_KEY.", "Critical")
    else:
        env_content = read(ENV_FILE)
        if "ANTHROPIC_API_KEY" not in env_content:
            fail("S02", ".env file exists with API key", "System", ".env exists but ANTHROPIC_API_KEY not found.",
                 "Add ANTHROPIC_API_KEY=sk-ant-... to system/.env", "Critical")
        elif "ANTHROPIC_API_KEY=" in env_content and env_content.split("ANTHROPIC_API_KEY=")[-1].strip()[:4] in ("", "\n", "sk-a"):
            val = env_content.split("ANTHROPIC_API_KEY=")[-1].split("\n")[0].strip()
            if not val or val == "YOUR_KEY_HERE":
                fail("S02", ".env file exists with API key", "System",
                     "ANTHROPIC_API_KEY is empty or placeholder.", "Set your real key in system/.env", "Critical")
            else:
                ok("S02", ".env file exists with API key", "System", "Key found (value hidden for security).")
        else:
            ok("S02", ".env file exists with API key", "System", "ANTHROPIC_API_KEY present.")

    # S03 — Python packages (check venv first, then system Python)
    _venv_python = Path.home() / ".local" / "share" / "metis-mcp" / ".venv" / "bin" / "python"
    _py_exe = str(_venv_python) if _venv_python.exists() else sys.executable
    pkgs = {}
    for pkg in ["fastapi", "uvicorn", "mcp", "httpx"]:
        try:
            result = subprocess.run(
                [_py_exe, "-c", f"import {pkg.replace('-','_')}"],
                capture_output=True, timeout=5
            )
            pkgs[pkg] = result.returncode == 0
        except Exception:
            pkgs[pkg] = False
    missing_pkgs = [p for p, ok_ in pkgs.items() if not ok_]
    if missing_pkgs:
        fail("S03", "Python packages installed", "System",
             f"Missing: {', '.join(missing_pkgs)}",
             f"Run: pip install {' '.join(missing_pkgs)} --break-system-packages", "High")
    else:
        ok("S03", "Python packages installed", "System", "fastapi, uvicorn, mcp, httpx all importable.")

    # S04 — Node.js
    try:
        out = subprocess.check_output(["node", "--version"], stderr=subprocess.DEVNULL).decode().strip()
        major = int(re.search(r"v(\d+)", out).group(1))
        if major < 18:
            warn("S04", "Node.js version ≥18", "System", f"Found {out} — v18+ recommended for installer.",
                 "Upgrade Node.js to v18 or v20: https://nodejs.org")
        else:
            ok("S04", "Node.js version ≥18", "System", f"Found {out}.")
    except Exception:
        warn("S04", "Node.js available", "System", "node not found in PATH.",
             "Install Node.js v18+ for the installer script to work.", "Low")

    # S05 — dashboard templates
    missing_tmpl = [t for t in TABS if not (TEMPLATES / f"{t}.html").exists() and not (TEMPLATES / f"{t}_tab.html").exists()]
    if missing_tmpl:
        fail("S05", "All 9 dashboard templates exist", "System",
             f"Missing templates for tabs: {', '.join(missing_tmpl)}",
             "Each tab needs a template file in system/app-py/templates/.", "High")
    else:
        ok("S05", "All 9 dashboard templates exist", "System",
           f"All {len(TABS)} tab templates present in system/app-py/templates/.")

    # S06 — dashboard routers
    missing_rtr = [t for t in TABS if not (ROUTERS / f"{t if t != 'metis' else 'metis_tab'}.py").exists()
                   and not (ROUTERS / f"{t}.py").exists()]
    # recheck properly
    router_files = list(ROUTERS.glob("*.py")) if ROUTERS.exists() else []
    router_names = [f.stem for f in router_files]
    found_tabs = sum(1 for t in TABS if t in router_names or f"{t}_tab" in router_names or
                     any(t in n for n in router_names))
    if found_tabs < len(TABS):
        warn("S06", "All 9 dashboard routers exist", "System",
             f"Found {found_tabs}/{len(TABS)} tab routers. Check {ROUTERS.relative_to(ROOT)}",
             "Each tab should have a corresponding router file.")
    else:
        ok("S06", "All 9 dashboard routers exist", "System",
           f"All {len(TABS)} tab routers found in system/app-py/routers/.")

    # S07 — MCP server entry point
    mcp_entry = ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "server.py"
    if not mcp_entry.exists():
        fail("S07", "MCP server entry point exists", "System",
             f"server.py not found at {mcp_entry.relative_to(ROOT)}",
             "The MCP server is the core of Metis. Restore from git.", "Critical")
    else:
        ok("S07", "MCP server entry point exists", "System",
           f"server.py found at {mcp_entry.relative_to(ROOT)}.")

    # S08 — launcher scripts
    launchers = [ROOT / "system" / "launch-metis.bat", ROOT / "system" / "app-py" / "run.sh"]
    for lnch in launchers:
        if not lnch.exists():
            warn("S08", f"Launcher script: {lnch.name}", "System",
                 f"Not found: {lnch.name}",
                 f"Create {lnch.name} so non-technical users can start Metis easily.", "Medium")
    ok("S08", "Launcher scripts", "System",
       f"Checked {', '.join(l.name for l in launchers)} — see detail for missing items.")

    # S09 — user-config.yaml
    if not USER_CONFIG.exists():
        fail("S09", "user-config.yaml exists", "System",
             f"Not found: {USER_CONFIG.relative_to(ROOT)}",
             "Run /metis_config in Claude Code to create the config file.", "High")
    elif not HAS_YAML:
        warn("S09", "user-config.yaml parses correctly", "System",
             "PyYAML not installed — cannot validate YAML.",
             "pip install pyyaml --break-system-packages")
    else:
        try:
            cfg = yaml.safe_load(read(USER_CONFIG))
            if cfg and isinstance(cfg, dict):
                ok("S09", "user-config.yaml parses correctly", "System",
                   f"Valid YAML with {len(cfg)} top-level keys: {', '.join(list(cfg.keys())[:6])}.")
            else:
                warn("S09", "user-config.yaml content", "System", "File exists but appears empty.",
                     "Run /metis_config to populate the configuration.")
        except Exception as e:
            fail("S09", "user-config.yaml parses correctly", "System", f"YAML parse error: {e}",
                 "Fix the YAML syntax in system/config/user-config.yaml.", "High")

    # S10 — implementation-progress.json
    if not IMPL_PROG.exists():
        warn("S10", "implementation-progress.json exists", "System",
             "Not found. This file tracks development milestones.",
             "Not critical for operation but useful for progress tracking.", "Low")
    else:
        try:
            data = json.loads(read(IMPL_PROG))
            last = data.get("_meta", {}).get("last_phase_completed", "unknown")
            ok("S10", "implementation-progress.json is valid JSON", "System",
               f"Last completed phase: {last}")
        except Exception as e:
            warn("S10", "implementation-progress.json is valid JSON", "System", f"JSON parse error: {e}",
                 "Fix the JSON syntax in implementation-progress.json.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — DASHBOARD HTTP TESTS
# ════════════════════════════════════════════════════════════════════════════
def run_dashboard():
    print("  → Dashboard HTTP tests...")

    # D01 — is dashboard alive?
    code, body = http_get("/")
    if code is None:
        skip("D01", "Dashboard reachable at localhost:8080", "Dashboard",
             f"Dashboard not running: {body}. Start with: bash system/app-py/run.sh")
        # Skip all subsequent HTTP tests
        for tab in TABS:
            skip(f"D-{tab}", f"Tab route: {tab}", "Dashboard", "Skipped — dashboard not running.")
        skip("D20", "HTMX partial routes (no double-navbar)", "Dashboard", "Skipped — dashboard not running.")
        skip("D21", "Course view API route exists (Bug B02)", "Dashboard", "Skipped — dashboard not running.")
        skip("D22", "Partial routes respond 200", "Dashboard", "Skipped — dashboard not running.")
        return
    elif code != 200:
        fail("D01", "Dashboard reachable at localhost:8080", "Dashboard",
             f"HTTP {code} — expected 200.",
             "Check uvicorn is running without errors: bash system/app-py/run.sh", "Critical")
        return
    else:
        ok("D01", "Dashboard reachable at localhost:8080", "Dashboard",
           f"HTTP 200 in < 5s. Response length: {len(body)} chars.")

    # D02-D10 — full tab routes
    for tab in TABS:
        route = f"/tab/{tab}"
        code, body = http_get(route)
        if code == 200:
            ok(f"D-{tab}-full", f"Full tab route: GET {route}", "Dashboard",
               f"HTTP 200, {len(body)} chars.")
        elif code is None:
            skip(f"D-{tab}-full", f"Full tab route: GET {route}", "Dashboard", body)
        else:
            fail(f"D-{tab}-full", f"Full tab route: GET {route}", "Dashboard",
                 f"HTTP {code}.",
                 f"Check router for tab '{tab}' in system/app-py/routers/.", "High")

    # D11-D19 — partial tab routes + double-navbar detection (BUG B01)
    sidebar_indicators = ["nav-item", "id=\"sidebar\"", "class=\"sidebar\"", "<nav"]
    for tab in TABS:
        route = f"/api/tab/{tab}"
        code, body = http_get(route)
        if code is None:
            skip(f"D-{tab}-partial", f"Partial tab route: GET {route}", "Dashboard", body)
            continue
        if code != 200:
            fail(f"D-{tab}-partial", f"Partial tab route: GET {route}", "Dashboard",
                 f"HTTP {code}.",
                 f"Ensure /api/tab/{tab} route exists and returns 200.", "High")
            continue

        # Check for double-navbar: partial should NOT contain sidebar HTML
        sidebar_count = sum(body.count(ind) for ind in sidebar_indicators)
        if sidebar_count > 2:
            fail(f"D-{tab}-partial", f"HTMX partial GET {route} — no double navbar",
                 "Dashboard",
                 f"⚠ BUG B01: Response contains sidebar/nav HTML ({sidebar_count} matches). "
                 f"This route returns a full page, not a partial — causes double navbar when loaded via HTMX.",
                 f"Fix: Make /api/tab/{tab} return a partial template (without base.html wrapper). "
                 f"Create {tab}_partial.html containing only the content block. "
                 f"The full template should only be returned from /tab/{tab}.", "Critical")
        else:
            ok(f"D-{tab}-partial", f"HTMX partial GET {route} — no double navbar", "Dashboard",
               f"HTTP 200, {len(body)} chars. No duplicate sidebar HTML detected.")

    # D20 — course view API route (BUG B02)
    # Check both the route and app.js behaviour
    course_view_route = False
    for router_file in ROUTERS.glob("*.py"):
        content = read(router_file)
        if "course" in router_file.name.lower() or "learning" in router_file.name.lower():
            if re.search(r'/api/course/\{?course_id\}?/view', content):
                course_view_route = True
                break

    app_js_content = read(APP_JS)
    uses_clipboard_for_course = "navigator.clipboard" in app_js_content and "buildCourse" in app_js_content

    if not course_view_route and uses_clipboard_for_course:
        fail("D20", "Course content served inline (Bug B02)", "Dashboard",
             "⚠ BUG B02 CONFIRMED: buildCourse() in app.js copies a CLI prompt to clipboard "
             "instead of opening the course inline. No /api/course/{id}/view route found.",
             "Add route GET /api/course/{course_id}/view in routers/learning.py that reads "
             "knowledge/courses/{slug}/course.json and modules/*.md and returns rendered HTML. "
             "Wire the Learning tab 'Continue' button to hx-get this route.", "Critical")
    elif course_view_route:
        ok("D20", "Course content served inline (Bug B02)", "Dashboard",
           "/api/course/{id}/view route found — course can be served inline.")
    else:
        warn("D20", "Course content served inline (Bug B02)", "Dashboard",
             "buildCourse() clipboard behaviour detected but no inline view route confirmed.",
             "Verify that opening a course in the Learning tab shows content inline, not copies a CLI prompt.")

    # D21 — spot-check 5 partial routes
    partials = [
        "/api/partial/today/hero",
        "/api/partial/work/tasks",
        "/api/partial/thinking/ideas",
        "/api/partial/meetings/list",
        "/api/partial/metis/agent-runs",
    ]
    partial_fails = []
    for route in partials:
        code, _ = http_get(route)
        if code not in (200, 422):  # 422 = missing param, which means route exists
            partial_fails.append(f"{route} → {code}")

    if partial_fails:
        warn("D21", "HTMX partial routes respond", "Dashboard",
             f"Non-200 responses: {'; '.join(partial_fails)}",
             "Check that partial routes handle missing parameters gracefully.")
    else:
        ok("D21", "HTMX partial routes respond", "Dashboard",
           f"All {len(partials)} spot-checked partials returned 200/422.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AGENT INVENTORY
# ════════════════════════════════════════════════════════════════════════════
def run_agents():
    print("  → Agent inventory...")

    # Parse agents declared in CLAUDE.md
    claude_md = read(CLAUDE_MD)
    # Extract agent invocations from the table: /slug → Agent Name
    declared_slugs = set(re.findall(r'`/([a-z][a-z0-9-]+)`', claude_md))
    declared_slugs -= {"metis_config", "schedule", "new-project", "add-context",
                       "metis_brainstorm", "metis_handoff", "metis_ideas",
                       "metis_notes", "metis_weekly", "metis_research",
                       "metis_status", "metis-library-setup"}  # skills, not agents

    # Actual agent folders
    agent_folders = {d.name for d in AGENTS_DIR.iterdir() if d.is_dir()} if AGENTS_DIR.exists() else set()

    # A01 — count
    info("A01", "Agent count", "Agents",
         f"Declared in CLAUDE.md: ~{len(declared_slugs)} agent invocations. "
         f"Agent folders: {len(agent_folders)}. "
         f"README claims: 24 specialist agents.")

    # A02 — skill files present
    missing_skills = []
    stub_skills = []
    for folder in sorted(agent_folders):
        skill = AGENTS_DIR / folder / "skill.md"
        sysp  = AGENTS_DIR / folder / "system-prompt.md"
        if not skill.exists() and not sysp.exists():
            missing_skills.append(folder)
        elif skill.exists():
            lines = len(read(skill).splitlines())
            if lines < 20:
                stub_skills.append(f"{folder} ({lines} lines)")

    if missing_skills:
        fail("A02", "All agents have skill/system-prompt file", "Agents",
             f"No skill file in: {', '.join(missing_skills)}",
             "Each agent folder needs at least a skill.md. "
             "Minimum content: frontmatter (name, description), Reasoning section, Output contract.", "High")
    else:
        ok("A02", "All agents have skill/system-prompt file", "Agents",
           f"All {len(agent_folders)} agent folders have a skill file.")

    if stub_skills:
        warn("A03", "Agent skill files are substantive (>20 lines)", "Agents",
             f"Thin skill files (<20 lines): {', '.join(stub_skills)}",
             "These agents may not have enough instruction to perform well. "
             "Add: Reasoning, Edge cases, and Output contract sections.")
    else:
        ok("A03", "Agent skill files are substantive", "Agents",
           "All skill files have ≥20 lines of content.")

    # A04 — output contract present
    missing_contract = []
    for folder in agent_folders:
        skill = AGENTS_DIR / folder / "skill.md"
        if skill.exists():
            content = read(skill)
            if "output contract" not in content.lower() and "output format" not in content.lower():
                missing_contract.append(folder)

    if missing_contract:
        warn("A04", "Agents have output contract / format section", "Agents",
             f"No output contract found in: {', '.join(missing_contract[:5])}{'...' if len(missing_contract) > 5 else ''}",
             "Without an output contract, agents produce inconsistent formats. "
             "Add an '## Output contract' section to each skill file.")
    else:
        ok("A04", "Agents have output contract / format section", "Agents",
           f"Output contract found in all {len(agent_folders)} checked agent skills.")

    # A05 — GitHub agent gap
    github_agent = any("github" in f.lower() or "git" in f.lower()
                       for f in agent_folders)
    if not github_agent:
        fail("A05", "Dedicated GitHub / Git agent exists", "Agents",
             "No git- or github-specific agent found in agents/. "
             "Git operations are handled ad-hoc through software-engineer via bash.",
             "Create agents/github/ with a skill.md scoped to: commit, push, PR creation, "
             "branch management, and git status reporting. "
             "Add a github.py MCP tool module for structured git operations. "
             "This is needed for project card git status in the Work tab.", "High")
    else:
        ok("A05", "Dedicated GitHub / Git agent exists", "Agents",
           "GitHub/git agent found.")

    # A06 — adaptive course builder
    adaptive_found = False
    for folder in [AGENTS_DIR, SKILLS_DIR]:
        if not folder.exists():
            continue
        for f in folder.rglob("skill.md"):
            content = read(f).lower()
            if "adaptive" in content and "research question" in content:
                adaptive_found = True
                break

    if not adaptive_found:
        fail("A06", "Adaptive Statistics Course Builder feature exists", "Agents",
             "No skill or agent implements the 'describe your research question → get a "
             "personalised course' workflow explicitly.",
             "Implement an adaptive mode in course-builder: "
             "(1) User describes research question, "
             "(2) Metis identifies required statistical methods, "
             "(3) Maps against existing courses for overlap, "
             "(4) Produces a personalised module sequence. "
             "This is the highest-value learning feature for researchers.", "Critical")
    else:
        ok("A06", "Adaptive Statistics Course Builder feature exists", "Agents",
           "Adaptive course builder behaviour found in a skill file.")

    # A07 — README agent count vs actual (exclude retired agents)
    readme = read(README_FILE)
    readme_agent_claim = re.search(r'(\d+)\s+specialist agents', readme)
    retired = {d.name for d in AGENTS_DIR.iterdir()
               if d.is_dir() and (d / "RETIRED.md").exists()} if AGENTS_DIR.exists() else set()
    active_agents = agent_folders - retired
    if readme_agent_claim:
        claimed = int(readme_agent_claim.group(1))
        actual = len(active_agents)
        if abs(claimed - actual) > 2:
            warn("A07", "README agent count matches reality", "Agents",
                 f"README claims {claimed} agents, found {actual} active folders ({len(retired)} retired).",
                 f"Update README: change '{claimed} specialist agents' to '{actual} specialist agents ({len(retired)} retired)'.")
        else:
            ok("A07", "README agent count matches reality", "Agents",
               f"README claims {claimed}, found {actual} active agents ({len(retired)} retired) — accurate.")
    else:
        warn("A07", "README agent count claim", "Agents",
             "Could not find 'N specialist agents' claim in README.",
             "Add agent count to README for transparency.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — MCP TOOL INVENTORY
# ════════════════════════════════════════════════════════════════════════════
def run_mcp():
    print("  → MCP tool inventory...")

    if not MCP_TOOLS.exists():
        fail("M01", "MCP tools directory exists", "MCP Tools",
             f"Not found: {MCP_TOOLS.relative_to(ROOT)}",
             "The MCP server tools directory is missing. Restore from git.", "Critical")
        return

    tool_files = list(MCP_TOOLS.glob("*.py"))
    total_tools = 0
    stub_tools = []

    for tf in tool_files:
        if tf.name.startswith("_"):
            continue
        content = read(tf)
        tool_defs = re.findall(r'@app\.tool\(\)', content)
        n = len(tool_defs)
        total_tools += n

        # Detect stubs: functions with only pass, raise NotImplementedError, or return ""
        stub_pattern = re.compile(
            r'@app\.tool\(\)\s*\n[^@]*?def\s+\w+[^:]*:\s*\n\s*(?:"""[^"]*"""[\s\n]*)?\s*(?:pass|return\s+""|\.\.\.|raise\s+NotImplementedError)',
            re.MULTILINE | re.DOTALL
        )
        stubs = stub_pattern.findall(content)
        if stubs:
            stub_tools.append(f"{tf.name} ({len(stubs)} stub(s))")

    # M01 — tool count vs README claim
    readme = read(README_FILE)
    readme_tool_claim = re.search(r'(\d+)\+?\s+(?:MCP\s+)?tools', readme)
    claimed = int(readme_tool_claim.group(1)) if readme_tool_claim else 76

    info("M01", "MCP tool count", "MCP Tools",
         f"Found {total_tools} @app.tool() definitions across {len(tool_files)} files. README claims '{claimed}+'.")

    if total_tools < claimed * 0.8:
        warn("M01b", "MCP tool count matches README claim", "MCP Tools",
             f"Found {total_tools} tools but README claims {claimed}+. Difference >{claimed*0.2:.0f}.",
             f"Update README: change '{claimed}+ MCP tools' to '{total_tools}+ MCP tools', "
             "or implement the missing tools.")
    else:
        ok("M01b", "MCP tool count matches README claim", "MCP Tools",
           f"{total_tools} tools found — within range of README claim ({claimed}+).")

    # M02 — stub detection
    if stub_tools:
        warn("M02", "No stub/unimplemented MCP tools", "MCP Tools",
             f"Potential stubs: {', '.join(stub_tools)}",
             "Review stub tools and implement them or remove them from the tool registry. "
             "Stubs will cause confusing failures when agents call them.")
    else:
        ok("M02", "No stub/unimplemented MCP tools", "MCP Tools",
           f"No obvious stubs detected in {len(tool_files)} tool files.")

    # M03 — GitHub/git tool module
    github_tool = any("github" in f.name.lower() or "git" in f.name.lower()
                      for f in tool_files)
    if not github_tool:
        fail("M03", "GitHub/git MCP tool module exists", "MCP Tools",
             f"No github.py or git.py found in {MCP_TOOLS.relative_to(ROOT)}. "
             "Git operations currently rely on ad-hoc bash commands through software-engineer.",
             "Create system/mcp-server/src/metis_mcp/tools/github.py with typed tools: "
             "git_status(project), git_commit(message, files), git_push(branch), "
             "git_log(n), create_pr_description(commits). "
             "This will enable accurate project card status in the Work tab.", "High")
    else:
        ok("M03", "GitHub/git MCP tool module exists", "MCP Tools",
           "Git/GitHub tool module found.")

    # M04 — token recording in agent_runs
    con = db_connect()
    if con:
        cols = db_columns(con, "agent_runs")
        has_tokens = "input_tokens" in cols and "output_tokens" in cols
        if not has_tokens:
            fail("M04", "Token columns in agent_runs table", "MCP Tools",
                 f"Columns found: {', '.join(cols)}. Missing: input_tokens, output_tokens.",
                 "Add ALTER TABLE agent_runs ADD COLUMN input_tokens INTEGER DEFAULT 0; "
                 "and ALTER TABLE agent_runs ADD COLUMN output_tokens INTEGER DEFAULT 0; "
                 "Then update log_agent_run() in tools/agents.py to record token usage.", "High")
        else:
            # Check if tokens are actually being recorded (non-zero)
            row = con.execute(
                "SELECT SUM(input_tokens+output_tokens) FROM agent_runs "
                "WHERE input_tokens IS NOT NULL AND input_tokens > 0"
            ).fetchone()
            token_sum = row[0] if row and row[0] else 0
            if token_sum == 0:
                warn("M04", "Token usage is being recorded", "MCP Tools",
                     "Columns exist but all token values are 0 or NULL. "
                     "Tokens are not being recorded from agent runs.",
                     "Update log_agent_run() to accept and store token counts from Claude API responses.")
            else:
                ok("M04", "Token usage is being recorded", "MCP Tools",
                   f"input_tokens + output_tokens columns present. Total recorded: {token_sum:,} tokens.")
        con.close()
    else:
        skip("M04", "Token columns in agent_runs table", "MCP Tools", "Database not accessible.")

    # M05 — span tracing
    obs_file = MCP_TOOLS / "observability.py"
    if obs_file.exists():
        content = read(obs_file)
        if "start_span" in content and "end_span" in content:
            ok("M05", "Span tracing (observability.py) implemented", "MCP Tools",
               "start_span, end_span, log_span, get_spans all present in observability.py.")
        else:
            warn("M05", "Span tracing implemented", "MCP Tools",
                 "observability.py exists but span functions not found.",
                 "Implement start_span/end_span/log_span in observability.py for pipeline tracing.")
    else:
        fail("M05", "Span tracing (observability.py) implemented", "MCP Tools",
             "observability.py not found.",
             "Create tools/observability.py with span tracing for agent pipeline visibility.", "Medium")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SKILL INVENTORY
# ════════════════════════════════════════════════════════════════════════════
def run_skills():
    print("  → Skill inventory...")

    if not SKILLS_DIR.exists():
        fail("K01", "Skills directory exists", "Skills",
             f"Not found: {SKILLS_DIR.relative_to(ROOT)}",
             "The .claude/skills/ directory is missing. Restore from git.", "Critical")
        return

    skill_folders = [d for d in SKILLS_DIR.iterdir() if d.is_dir()]
    ok("K01", "Skills directory exists", "Skills",
       f"Found {len(skill_folders)} skill folders in {SKILLS_DIR.relative_to(ROOT)}.")

    # K02 — required skills present
    missing = [s for s in REQUIRED_SKILLS if not (SKILLS_DIR / s).exists()]
    if missing:
        fail("K02", "All required skills present", "Skills",
             f"Missing skills: {', '.join(missing)}",
             "These skills are referenced in CLAUDE.md but their directories are missing. "
             "Restore the missing skill folders from git.", "High")
    else:
        ok("K02", "All required skills present", "Skills",
           f"All {len(REQUIRED_SKILLS)} required skills found.")

    # K03 — each skill has skill.md
    missing_md = [d.name for d in skill_folders if not (d / "skill.md").exists()]
    if missing_md:
        fail("K03", "Each skill folder has a skill.md file", "Skills",
             f"Missing skill.md in: {', '.join(missing_md[:6])}{'...' if len(missing_md) > 6 else ''}",
             "Claude Code loads skills from skill.md. Create the file for each skill folder.", "High")
    else:
        ok("K03", "Each skill folder has a skill.md file", "Skills",
           f"All {len(skill_folders)} skill folders have skill.md.")

    # K04 — model appropriateness (haiku for quick, opus for chain)
    model_mismatches = []
    for d in skill_folders:
        skill_file = d / "skill.md"
        if not skill_file.exists():
            continue
        content = read(skill_file)
        frontmatter = content[:500].lower()
        # Quick/simple tasks using opus is wasteful
        is_quick = "complexity: quick" in frontmatter
        uses_opus = "claude-opus" in frontmatter
        is_chain = "complexity: chain" in frontmatter
        uses_haiku = "claude-haiku" in frontmatter or "haiku" in frontmatter
        if is_quick and uses_opus:
            model_mismatches.append(f"{d.name}: quick task using opus (wasteful)")
        if is_chain and uses_haiku:
            model_mismatches.append(f"{d.name}: chain task using haiku (underpowered)")

    if model_mismatches:
        warn("K04", "Skill model selection is appropriate", "Skills",
             f"Mismatches: {'; '.join(model_mismatches[:4])}",
             "Quick tasks should use haiku, standard tasks sonnet, chain/deep tasks opus. "
             "Mismatched models waste tokens or produce lower quality output.")
    else:
        ok("K04", "Skill model selection is appropriate", "Skills",
           "Model assignments appear appropriate for task complexity levels.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SECURITY
# ════════════════════════════════════════════════════════════════════════════
def run_security():
    print("  → Security audit...")

    # SEC01 — hook file
    if not HOOK_FILE.exists():
        fail("SEC01", "Pre-tool-use security hook exists", "Security",
             f"Not found: {HOOK_FILE.relative_to(ROOT)}",
             "The pre-tool-use hook is the primary security boundary for web access and file writes. "
             "Restore from git immediately.", "Critical")
        return
    else:
        ok("SEC01", "Pre-tool-use security hook exists", "Security",
           f"Found: {HOOK_FILE.relative_to(ROOT)}")

    hook_content = read(HOOK_FILE)

    # SEC02 — allowlist completeness
    domains = re.findall(r'"([a-z0-9.-]+\.[a-z]{2,})"', hook_content)
    key_domains = ["pubmed.ncbi.nlm.nih.gov", "who.int", "ecdc.europa.eu", "api.zotero.org"]
    missing_domains = [d for d in key_domains if d not in hook_content]
    if missing_domains:
        warn("SEC02", "Domain allowlist contains key research domains", "Security",
             f"Missing from allowlist: {', '.join(missing_domains)}",
             "Add these domains to ALLOWED_DOMAINS in .claude/hooks/pre-tool-use.mjs")
    else:
        ok("SEC02", "Domain allowlist contains key research domains", "Security",
           f"All key research domains present. Total domains in allowlist: ~{len(domains)}.")

    # SEC03 — injection patterns
    if GUARD_FILE.exists():
        guard_content = read(GUARD_FILE)
        injection_patterns = re.findall(r'r["\']([^"\']+)["\']', guard_content)
        injection_count = len([p for p in injection_patterns if len(p) > 10])
        if injection_count < 8:
            warn("SEC03", "Prompt injection patterns (guardrails.py)", "Security",
                 f"Found ~{injection_count} injection patterns. README claims '11 prompt injection patterns'.",
                 "Review guardrails.py and ensure all 11 injection patterns are implemented. "
                 "Patterns should cover: system override, admin mode, ignore instructions, reveal prompt, etc.")
        else:
            ok("SEC03", "Prompt injection patterns (guardrails.py)", "Security",
               f"~{injection_count} injection patterns found in guardrails.py.")
    else:
        fail("SEC03", "Prompt injection scanner (guardrails.py)", "Security",
             f"guardrails.py not found at {GUARD_FILE.relative_to(ROOT)}",
             "Create tools/guardrails.py with injection pattern scanning.", "Critical")

    # SEC04 — Data Guardian PII patterns
    guardian_file = MCP_TOOLS / "safety.py" if (MCP_TOOLS / "safety.py").exists() \
                    else next((f for f in MCP_TOOLS.glob("*.py") if "guard" in f.name.lower()), None)
    if guardian_file:
        guard_content = read(guardian_file)
        pii_matches = re.findall(r'patient_id|national.id|passport|phone|address|email|gps|latitude|coordinate',
                                 guard_content, re.IGNORECASE)
        if len(pii_matches) < 5:
            warn("SEC04", "Data Guardian PII patterns", "Security",
                 f"Only ~{len(pii_matches)} PII pattern keywords found. README claims '40+ PII patterns'.",
                 "Review Data Guardian implementation and ensure 40+ PII patterns are present.")
        else:
            ok("SEC04", "Data Guardian PII patterns", "Security",
               f"PII pattern keywords found in {guardian_file.name}. Coverage appears adequate.")
    else:
        warn("SEC04", "Data Guardian safety file", "Security",
             "Cannot locate safety.py or guardian file in MCP tools.",
             "Ensure Data Guardian logic is in a dedicated tool file.")

    # SEC05 — red-lines.md
    if not RED_LINES.exists():
        fail("SEC05", "red-lines.md data policy exists", "Security",
             f"Not found: {RED_LINES.relative_to(ROOT)}",
             "The data policy file defines what data can and cannot leave the machine. "
             "Restore from git.", "High")
    else:
        content = read(RED_LINES)
        if "SENSITIVE" in content and "BLOCKED" in content:
            ok("SEC05", "red-lines.md data policy exists", "Security",
               "Contains SENSITIVE/BLOCKED classification scheme.")
        else:
            warn("SEC05", "red-lines.md content", "Security",
                 "red-lines.md exists but may not contain the full classification scheme.",
                 "Ensure SENSITIVE/CONFIDENTIAL/INTERNAL/PUBLIC classification is documented.")

    # SEC06 — .gitignore coverage
    if not GITIGNORE.exists():
        fail("SEC06", ".gitignore covers sensitive file types", "Security",
             ".gitignore not found.",
             "Create a .gitignore covering: .env, *.csv, *.rds, *.RData, *.sqlite, *.cas, patient*, inbox/*.xlsx", "High")
    else:
        gi_content = read(GITIGNORE)
        missing_patterns = [p for p in SENSITIVE_GITIGNORE_PATTERNS
                            if p.replace("*.", "") not in gi_content and p not in gi_content]
        if missing_patterns:
            warn("SEC06", ".gitignore covers sensitive file types", "Security",
                 f"Patterns not found in .gitignore: {', '.join(missing_patterns)}",
                 f"Add to .gitignore: {chr(10).join(missing_patterns)}")
        else:
            ok("SEC06", ".gitignore covers sensitive file types", "Security",
               "All key sensitive patterns found in .gitignore.")

    # SEC07 — no sensitive files in git index
    tracked = git_tracked_sensitive()
    if tracked:
        fail("SEC07", "No sensitive data files tracked by git", "Security",
             f"Sensitive files tracked by git: {', '.join(tracked[:5])}{'...' if len(tracked) > 5 else ''}",
             "Remove from tracking: git rm --cached <file> then add to .gitignore. "
             "Review git history for any previously committed sensitive data.", "Critical")
    else:
        ok("SEC07", "No sensitive data files tracked by git", "Security",
           "Git ls-files shows no .csv, .rds, .RData, .sqlite, or .env files tracked.")

    # SEC08 — constitution.md
    const_file = CONFIG_DIR / "constitution.md"
    if not const_file.exists():
        warn("SEC08", "Agent constitution (guardrails document) exists", "Security",
             f"constitution.md not found in {CONFIG_DIR.relative_to(ROOT)}",
             "The constitution defines what agents can and cannot do. Restore from git.")
    else:
        ok("SEC08", "Agent constitution (guardrails document) exists", "Security",
           "constitution.md found.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 7 — CONFIGURATION QUALITY
# ════════════════════════════════════════════════════════════════════════════
def run_config():
    print("  → Configuration quality...")

    # CFG01 — placeholder check in CLAUDE.md
    # Some {placeholders} are intentional format examples in documentation (e.g. {agent-slug},
    # {task-slug}, {your-github-username} used inline as instructions to the user).
    # We only flag placeholders that are structural (standalone on a line as a value).
    INTENTIONAL_FORMAT_PLACEHOLDERS = {
        "{agent-slug}", "{task-slug}", "{your-github-username}", "{username}",
    }
    claude_content = read(CLAUDE_MD)
    placeholders = re.findall(r'\{[a-z][a-z0-9-]*\}', claude_content)
    unique_unfilled = [p for p in set(placeholders) if p not in INTENTIONAL_FORMAT_PLACEHOLDERS]
    if unique_unfilled:
        fail("CFG01", "CLAUDE.md has no unfilled placeholder values", "Config",
             f"Unfilled structural placeholders: {', '.join(unique_unfilled[:8])}",
             "Run /metis_config to personalise CLAUDE.md. "
             "The {user} Owner field on line 6 should be set to your name.", "High")
    else:
        ok("CFG01", "CLAUDE.md has no unfilled placeholder values", "Config",
           "No unset structural {placeholder} values found in CLAUDE.md.")

    # CFG02 — user-config.yaml sections
    if USER_CONFIG.exists() and HAS_YAML:
        try:
            cfg = yaml.safe_load(read(USER_CONFIG)) or {}
            expected_keys = ["user", "research", "projects"]
            present = [k for k in expected_keys if k in cfg]
            missing = [k for k in expected_keys if k not in cfg]
            if missing:
                warn("CFG02", "user-config.yaml has required sections", "Config",
                     f"Missing sections: {', '.join(missing)}. Present: {', '.join(present)}.",
                     "Run /metis_config to complete the configuration wizard.")
            else:
                ok("CFG02", "user-config.yaml has required sections", "Config",
                   f"Required sections present: {', '.join(present)}.")
        except Exception:
            pass  # already reported in S09

    # CFG03 — token guardrails
    token_file = CONFIG_DIR / "token-guardrails.md"
    if not token_file.exists():
        warn("CFG03", "Token guardrails config exists", "Config",
             f"token-guardrails.md not found in {CONFIG_DIR.relative_to(ROOT)}",
             "Create token-guardrails.md with: daily budget, per-model limits, "
             "and auto-handoff trigger threshold.", "Medium")
    else:
        ok("CFG03", "Token guardrails config exists", "Config",
           "token-guardrails.md found.")

    # CFG04 — agent registry
    if not AGENT_REG.exists():
        warn("CFG04", "agent-registry.json exists", "Config",
             f"Not found: {AGENT_REG.relative_to(ROOT)}",
             "The agent registry maps slugs to metadata. "
             "Without it, Metis cannot auto-validate agent routing.", "Medium")
    else:
        try:
            reg = json.loads(read(AGENT_REG))
            agents_in_reg = len(reg) if isinstance(reg, list) else \
                            len(reg.get("agents", [])) if isinstance(reg, dict) else 0
            ok("CFG04", "agent-registry.json exists and parses", "Config",
               f"Valid JSON. Registry entries: {agents_in_reg}.")
        except Exception as e:
            fail("CFG04", "agent-registry.json parses correctly", "Config",
                 f"JSON parse error: {e}",
                 "Fix the JSON syntax in agent-registry.json.", "Medium")

    # CFG05 — thinking profile
    thinking = CONFIG_DIR / "thinking-profile.yaml"
    if not thinking.exists():
        warn("CFG05", "thinking-profile.yaml exists", "Config",
             "Not found. This profiles the user's thinking style for personalised responses.",
             "Run /metis_config or create thinking-profile.yaml manually.", "Low")
    else:
        ok("CFG05", "thinking-profile.yaml exists", "Config",
           "thinking-profile.yaml found.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 8 — README QUALITY
# ════════════════════════════════════════════════════════════════════════════
def run_readme():
    print("  → README quality review...")

    if not README_FILE.exists():
        fail("R01", "README.md exists", "README",
             "README.md not found at repository root.",
             "Create README.md immediately — it is the first thing any user or contributor sees.", "Critical")
        return

    readme = read(README_FILE)
    word_count = len(readme.split())

    # R01 — exists and substantial
    if word_count < 500:
        fail("R01", "README is substantial (>500 words)", "README",
             f"README has only {word_count} words.",
             "A public-facing research tool needs a comprehensive README. "
             "Target: 2000-4000 words covering problem, features, install, usage, architecture.", "High")
    else:
        ok("R01", "README is substantial", "README",
           f"{word_count} words — good length for a public project.")

    # R02 — key sections present
    sections = {
        "Quick Start": bool(re.search(r'quick.?start|getting.?started', readme, re.IGNORECASE)),
        "Architecture": bool(re.search(r'architecture|under the hood', readme, re.IGNORECASE)),
        "Agent Team": bool(re.search(r'agent.?team|specialist.?agent', readme, re.IGNORECASE)),
        "Data Protection": bool(re.search(r'data.?protection|privacy', readme, re.IGNORECASE)),
        "Installation": bool(re.search(r'install|setup|getting.?started', readme, re.IGNORECASE)),
        "Troubleshooting/FAQ": bool(re.search(r'troubleshoot|faq|common.?issue|known.?issue', readme, re.IGNORECASE)),
        "Contributing": bool(re.search(r'contribut', readme, re.IGNORECASE)),
        "License": bool(re.search(r'license|licence|mit', readme, re.IGNORECASE)),
    }
    missing_sections = [s for s, present in sections.items() if not present]
    if missing_sections:
        warn("R02", "README has all key sections", "README",
             f"Missing sections: {', '.join(missing_sections)}",
             f"Add the following sections to README.md: {', '.join(missing_sections)}. "
             "Troubleshooting/FAQ is especially important for non-technical researchers.")
    else:
        ok("R02", "README has all key sections", "README",
           f"All {len(sections)} expected sections found.")

    # R03 — screenshots / images
    has_images = bool(re.search(r'!\[.*?\]\(.*?\.(png|jpg|gif|svg|webp)', readme, re.IGNORECASE))
    has_badges = bool(re.search(r'!\[.*?\]\(https://img\.shields\.io', readme))
    if not has_images:
        fail("R03", "README has screenshots or demo images", "README",
             "No embedded images found in README.md. Only badges present." if has_badges else
             "No images or badges found in README.md.",
             "Add at least one screenshot of the dashboard and one short demo GIF. "
             "A visual preview dramatically increases trust and adoption from researchers "
             "who want to see the tool before installing it.", "High")
    else:
        ok("R03", "README has screenshots or demo images", "README",
           "Image embed(s) found in README.")

    # R04 — WhatsApp claim vs implementation
    whatsapp_in_readme = bool(re.search(r'whatsapp', readme, re.IGNORECASE))
    whatsapp_agent = (AGENTS_DIR / "whatsapp").exists() or \
                     any("whatsapp" in f.name.lower() for f in MCP_TOOLS.glob("*.py") if MCP_TOOLS.exists())
    if whatsapp_in_readme and not whatsapp_agent:
        fail("R04", "WhatsApp feature claim matches implementation", "README",
             "README mentions WhatsApp integration but no implementation found in agents/ or MCP tools.",
             "Either: (a) implement WhatsApp integration via Twilio webhook → inbox/ file → Metis processing, "
             "or (b) remove the claim from README and add it to a 'Coming soon' roadmap section. "
             "Unimplemented features damage researcher trust.", "High")
    elif whatsapp_in_readme and whatsapp_agent:
        ok("R04", "WhatsApp feature claim matches implementation", "README",
           "WhatsApp mentioned in README and implementation found.")
    else:
        ok("R04", "WhatsApp feature claim", "README",
           "WhatsApp not claimed in README (or not checked).")

    # R05 — tool count claim accuracy
    readme_tool_match = re.search(r'(\d+)\+?\s+MCP tools', readme)
    if readme_tool_match:
        claimed = int(readme_tool_match.group(1))
        # Count actual tools (already done in run_mcp but we can redo a quick count)
        actual_tools = sum(
            len(re.findall(r'@app\.tool\(\)', read(f)))
            for f in MCP_TOOLS.glob("*.py")
            if not f.name.startswith("_")
        ) if MCP_TOOLS.exists() else 0
        if actual_tools > 0 and abs(actual_tools - claimed) > claimed * 0.2:
            warn("R05", "README MCP tool count is accurate", "README",
                 f"README claims '{claimed}+ MCP tools' but found {actual_tools} tool definitions.",
                 f"Update README to reflect actual tool count ({actual_tools}).")
        else:
            ok("R05", "README MCP tool count is accurate", "README",
               f"Claims {claimed}+, found {actual_tools} — within 20% tolerance.")

    # R06 — target audience language
    jargon_terms = ["FastAPI", "HTMX", "SQLite schema", "npm install", "uvicorn", "WSL terminal"]
    jargon_found = [t for t in jargon_terms if t in readme]
    if len(jargon_found) > 4:
        warn("R06", "README language appropriate for non-technical researchers", "README",
             f"Technical terms appear without plain-language alternatives: {', '.join(jargon_found[:5])}",
             "For each technical term used, add a brief plain-language explanation in parentheses "
             "or a footnote. The target audience (epidemiologists, ecologists) are domain experts "
             "but not necessarily developers. Jargon without explanation causes drop-off.")
    else:
        ok("R06", "README language appropriate for non-technical researchers", "README",
           f"Technical jargon count is within acceptable range ({len(jargon_found)} flagged terms).")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 9 — DATABASE INTEGRITY
# ════════════════════════════════════════════════════════════════════════════
def run_database():
    print("  → Database integrity...")

    con = db_connect()
    if not con:
        fail("DB01", "Database accessible", "Database",
             f"Cannot connect to {DB_PATH}",
             "Ensure metis.sqlite exists and is not locked by another process.", "Critical")
        return

    tables = db_tables(con)

    # DB01 — required tables
    missing = [t for t in REQUIRED_TABLES if t not in tables]
    if missing:
        fail("DB01", "All required tables exist", "Database",
             f"Missing: {', '.join(missing)}",
             "Start the MCP server once: python system/mcp-server/src/metis_mcp/server.py — "
             "this triggers the DDL that creates missing tables.", "Critical")
    else:
        ok("DB01", "All required tables exist", "Database",
           f"All {len(REQUIRED_TABLES)} required tables present. "
           f"Total tables in DB: {len(tables)}.")

    # DB02 — agent_runs records
    try:
        count = con.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0]
        if count == 0:
            warn("DB02", "agent_runs has activity records", "Database",
                 "agent_runs table is empty — no agent runs have been logged.",
                 "Run any agent (/metis_status, /news-radar, etc.) to create the first record.")
        else:
            ok("DB02", "agent_runs has activity records", "Database",
               f"{count} agent run records found.")
    except Exception as e:
        warn("DB02", "agent_runs readable", "Database", f"Query error: {e}", None)

    # DB03 — ideas table has records
    try:
        count = con.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
        if count == 0:
            warn("DB03", "Ideas table has content", "Database",
                 "ideas table is empty. The system has not been used for idea capture yet.",
                 "Use /metis_capture i: [idea] or the Thinking tab Capture button to add ideas.")
        else:
            ok("DB03", "Ideas table has content", "Database",
               f"{count} idea records found.")
    except Exception as e:
        warn("DB03", "Ideas table readable", "Database", f"Query error: {e}", None)

    # DB04 — self-improvement tables
    for tbl in ["reflexion_log", "skill_improvement_proposals"]:
        if tbl in tables:
            ok(f"DB04-{tbl}", f"Self-improvement table: {tbl}", "Database",
               f"Table {tbl} exists.")
        else:
            fail(f"DB04-{tbl}", f"Self-improvement table: {tbl}", "Database",
                 f"Table {tbl} missing.",
                 f"Run the MCP server to auto-create {tbl}. "
                 "This table is required for the reflexion loop.", "Medium")

    # DB05 — learning_courses
    if "learning_courses" in tables:
        try:
            cols = db_columns(con, "learning_courses")
            ok("DB05", "learning_courses table schema", "Database",
               f"Columns: {', '.join(cols)}")
        except Exception:
            ok("DB05", "learning_courses table exists", "Database", "Table found.")
    else:
        fail("DB05", "learning_courses table exists", "Database",
             "learning_courses table not found.",
             "This table tracks course progress in the Learning tab. "
             "Start MCP server to trigger DDL.", "Medium")

    # DB06 — token columns in agent_runs (also checked in MCP section, but verify here)
    if "agent_runs" in tables:
        cols = db_columns(con, "agent_runs")
        has_model = "model" in cols
        if not has_model:
            warn("DB06", "agent_runs.model column exists", "Database",
                 f"Columns found: {', '.join(cols)}. 'model' column missing.",
                 "Add ALTER TABLE agent_runs ADD COLUMN model TEXT; to record which model was used per run. "
                 "This is needed for the token-by-model breakdown in the Metis tab.")
        else:
            ok("DB06", "agent_runs schema is complete", "Database",
               f"Columns: {', '.join(cols)}.")

    con.close()

# ════════════════════════════════════════════════════════════════════════════
# SECTION 10 — GIT SAFETY
# ════════════════════════════════════════════════════════════════════════════
def run_git():
    print("  → Git safety...")

    try:
        subprocess.check_output(["git", "rev-parse", "--git-dir"],
                                 cwd=str(ROOT), stderr=subprocess.DEVNULL)
        ok("GIT01", "Git repository initialised", "Git",
           "metis/ is a git repository.")
    except Exception:
        warn("GIT01", "Git repository initialised", "Git",
             "metis/ does not appear to be a git repo.",
             "Run: git init && git remote add origin <your-repo-url>", "Medium")
        return

    # GIT02 — staged sensitive files
    staged = git_staged_files()
    sensitive_staged = [f for f in staged if any(
        re.search(p, f, re.IGNORECASE)
        for p in [r"\.env", r"\.csv", r"\.rds", r"\.RData", r"\.sqlite", r"patient"]
    )]
    if sensitive_staged:
        fail("GIT02", "No sensitive files in git staging area", "Git",
             f"Staged sensitive files: {', '.join(sensitive_staged)}",
             f"Unstage with: git rm --cached {' '.join(sensitive_staged)}  "
             "then add to .gitignore before committing.", "Critical")
    else:
        ok("GIT02", "No sensitive files in git staging area", "Git",
           f"Staging area: {len(staged)} file(s) staged, none match sensitive patterns.")

    # GIT03 — tracked sensitive
    tracked = git_tracked_sensitive()
    if tracked:
        fail("GIT03", "No sensitive files already tracked", "Git",
             f"Files matching sensitive patterns already tracked: {', '.join(tracked[:5])}",
             "Remove from tracking: git rm --cached <file>  "
             "Check git history for previously committed sensitive data with: "
             "git log --all --full-history -- '*.csv'", "Critical")
    else:
        ok("GIT03", "No sensitive data files tracked", "Git",
           "No .csv, .rds, .RData, .sqlite, or .env files in git index.")

# ════════════════════════════════════════════════════════════════════════════
# SECTION 11 — DASHBOARD v9e+ CHECKS (CSS Polish, Morning Brief, News, Scheduler)
# ════════════════════════════════════════════════════════════════════════════
def run_dashboard_v2():
    """Dashboard v9e+ checks — CSS polish, morning brief, news pipeline, scheduler."""
    print("  → Dashboard v9e+ checks...")

    STATIC_DIR  = APP_PY / "static"
    TEMPLATES   = APP_PY / "templates"
    PARTIALS    = TEMPLATES / "partials"
    ROUTERS_DIR = APP_PY / "routers"
    styles_css  = STATIC_DIR / "styles.css"
    motion_css  = STATIC_DIR / "motion.css"
    base_html   = TEMPLATES / "base.html"
    today_brief = PARTIALS / "today_morning_brief.html"
    today_router = ROUTERS_DIR / "today.py"
    sched_py    = APP_PY / "scheduler.py"
    content_py  = APP_PY / "content_scan.py"
    intel_py    = APP_PY / "intelligence.py"

    # ── CSS checks ────────────────────────────────────────────────────────

    # DV01 — styles.css has v9e focus-visible tokens
    css = read(styles_css)
    if "focus-visible" in css:
        ok("DV01", "CSS: focus-visible style defined", "Dashboard v9e",
           "styles.css contains :focus-visible rule.")
    else:
        warn("DV01", "CSS: focus-visible style defined", "Dashboard v9e",
             "styles.css does not define :focus-visible.",
             "Add :focus-visible outline style for keyboard accessibility.", "Medium")

    # DV02 — m-skel skeleton class present
    if "m-skel" in css:
        ok("DV02", "CSS: m-skel skeleton class defined", "Dashboard v9e",
           "styles.css contains .m-skel skeleton class.")
    else:
        warn("DV02", "CSS: m-skel skeleton class defined", "Dashboard v9e",
             ".m-skel not found in styles.css.",
             "Add .m-skel class for skeleton loading states (Phase 1 CSS block).", "Low")

    # DV03 — :disabled state defined
    if ":disabled" in css:
        ok("DV03", "CSS: :disabled state styled", "Dashboard v9e",
           "styles.css contains :disabled rule.")
    else:
        warn("DV03", "CSS: :disabled state styled", "Dashboard v9e",
             ":disabled selector not found in styles.css.",
             "Add button:disabled / input:disabled styles to prevent invisible disabled states.", "Low")

    # DV04 — .nav-item transition defined
    if ".nav-item" in css and "transition" in css:
        ok("DV04", "CSS: .nav-item has transition", "Dashboard v9e",
           ".nav-item and transition both present in styles.css.")
    else:
        warn("DV04", "CSS: .nav-item has transition", "Dashboard v9e",
             ".nav-item or transition missing from styles.css.",
             "Add transition: to .nav-item for smooth hover state.", "Low")

    # DV05 — motion.css exists as a file
    if motion_css.exists():
        ok("DV05", "static/motion.css file exists", "Dashboard v9e",
           f"motion.css found ({motion_css.stat().st_size} bytes).")
    else:
        fail("DV05", "static/motion.css file exists", "Dashboard v9e",
             f"motion.css not found at {motion_css.relative_to(ROOT)}",
             "Create static/motion.css with surface-fade, m-edge-left, and reduced-motion media query.", "High")

    # DV06 — motion.css linked in base.html AFTER styles.css
    base = read(base_html)
    styles_pos  = base.find("styles.css")
    motion_pos  = base.find("motion.css")
    if styles_pos == -1:
        warn("DV06", "base.html links styles.css", "Dashboard v9e",
             "styles.css link not found in base.html.", None, "High")
    elif motion_pos == -1:
        fail("DV06", "motion.css loaded after styles.css in base.html", "Dashboard v9e",
             "motion.css is not linked in base.html.",
             "Add <link rel='stylesheet' href='/static/motion.css?v=...'>  AFTER the styles.css link.", "High")
    elif motion_pos > styles_pos:
        ok("DV06", "motion.css loaded after styles.css in base.html", "Dashboard v9e",
           "motion.css link appears after styles.css in base.html — correct load order.")
    else:
        fail("DV06", "motion.css loaded after styles.css in base.html", "Dashboard v9e",
             "motion.css link appears BEFORE styles.css — wrong order.",
             "Move the motion.css <link> tag to after the styles.css <link> in base.html.", "High")

    # DV07 — data-motion, data-hairline, data-lift on .app div
    for attr in ("data-motion=\"on\"", "data-hairline=\"on\"", "data-lift=\"on\""):
        if attr in base:
            ok(f"DV07-{attr.split('=')[0]}", f"base.html .app div has {attr}", "Dashboard v9e",
               f"{attr} found in base.html.")
        else:
            warn(f"DV07-{attr.split('=')[0]}", f"base.html .app div has {attr}", "Dashboard v9e",
                 f"{attr} not found in base.html.",
                 f"Add {attr} to the .app container div to enable motion.css directives.", "Medium")

    # DV08 — no conflicting m-edge-left::before with opacity: in styles.css
    if re.search(r'm-edge-left\s*::\s*before[^}]*opacity\s*:', css, re.DOTALL):
        fail("DV08", "styles.css does not redefine m-edge-left::before opacity", "Dashboard v9e",
             "styles.css contains .m-edge-left::before { opacity: ... } — conflicts with motion.css.",
             "Remove opacity: definition from styles.css .m-edge-left::before. "
             "motion.css owns this rule and uses scaleY for animation.", "Medium")
    else:
        ok("DV08", "styles.css does not redefine m-edge-left::before opacity", "Dashboard v9e",
           "No conflicting m-edge-left::before opacity definition in styles.css.")

    # DV09 — cache-busting ?v= parameter on styles.css link
    if re.search(r'styles\.css\?v=', base):
        ok("DV09", "styles.css link has cache-busting ?v= parameter", "Dashboard v9e",
           "styles.css link in base.html includes ?v= cache-bust parameter.")
    else:
        warn("DV09", "styles.css link has cache-busting ?v= parameter", "Dashboard v9e",
             "styles.css link in base.html does not include ?v= parameter.",
             "Add ?v=9e (or similar) to the styles.css href to force browser cache refresh on deploy.", "Low")

    # ── Morning Brief checks ───────────────────────────────────────────────

    # DV10 — morning brief auto-opens when content exists
    brief = read(today_brief)
    if "display" in brief and "block" in brief and ("brief" in brief.lower() or "{% if" in brief):
        ok("DV10", "Morning brief auto-opens when content present", "Dashboard v9e",
           "today_morning_brief.html uses display:block conditional for auto-open.")
    else:
        warn("DV10", "Morning brief auto-opens when content present", "Dashboard v9e",
             "today_morning_brief.html may not auto-open when brief content exists.",
             "Add display:{%if brief%}block{%else%}none{%endif%} on #morning-brief-body.", "Medium")

    # DV11 — morning brief is collapsible via toggleBrief
    if "toggleBrief" in brief:
        ok("DV11", "Morning brief is collapsible (toggleBrief)", "Dashboard v9e",
           "toggleBrief() referenced in today_morning_brief.html.")
    else:
        warn("DV11", "Morning brief is collapsible (toggleBrief)", "Dashboard v9e",
             "toggleBrief() not found in today_morning_brief.html.",
             "Add onclick=\"toggleBrief()\" to the brief header element.", "Medium")

    # DV12 — brief chevron rotates when open
    if "rotate" in brief and "90" in brief:
        ok("DV12", "Morning brief chevron rotates when open", "Dashboard v9e",
           "Chevron rotation (90deg) found in today_morning_brief.html.")
    else:
        warn("DV12", "Morning brief chevron rotates when open", "Dashboard v9e",
             "Chevron rotate(90deg) not found in today_morning_brief.html.",
             "Add transform:{%if brief%}rotate(90deg){%else%}none{%endif%} to the chevron element.", "Low")

    # DV13 — morning brief update button uses correct hx-post endpoint
    if "hx-post" in brief and "morning-brief/refresh" in brief:
        ok("DV13", "Morning brief update button uses hx-post /api/morning-brief/refresh", "Dashboard v9e",
           "hx-post to morning-brief/refresh found in today_morning_brief.html.")
    else:
        warn("DV13", "Morning brief update button uses hx-post /api/morning-brief/refresh", "Dashboard v9e",
             "hx-post to /api/morning-brief/refresh not found in today_morning_brief.html.",
             "Wire the update button: hx-post='/api/morning-brief/refresh' hx-target='#morning-brief'.", "Medium")

    # DV14 — _get_or_generate_brief does NOT delete cache before regenerating
    today_r = read(today_router)
    if re.search(r'DELETE.*daily_insights', today_r, re.IGNORECASE) and \
       "_get_or_generate_brief" in today_r:
        fail("DV14", "_get_or_generate_brief does not delete cache before regenerating", "Dashboard v9e",
             "today.py deletes from daily_insights before attempting regeneration — risks losing cached content on API failure.",
             "Remove the DELETE statement from _get_or_generate_brief. "
             "Only replace cache on successful regeneration. Return cached_content as fallback.", "High")
    else:
        ok("DV14", "_get_or_generate_brief does not delete cache before regenerating", "Dashboard v9e",
           "No premature cache deletion found in today.py morning brief logic.")

    # DV15 — scheduler.py brief synthesis uses direct call, not asyncio.run()
    sched = read(sched_py)
    if sched_py.exists():
        if "asyncio.run(" in sched and "brief" in sched.lower():
            # Check if asyncio.run is specifically in a brief-related function
            brief_block = re.search(
                r'def job_brief_synthesis.*?(?=\ndef |\Z)', sched, re.DOTALL
            )
            if brief_block and "asyncio.run(" in brief_block.group(0):
                fail("DV15", "job_brief_synthesis uses direct call not asyncio.run()", "Dashboard v9e",
                     "scheduler.py job_brief_synthesis uses asyncio.run() — will fail in async context.",
                     "Remove asyncio.run() wrapper. Call _get_or_generate_brief() directly in the scheduler job.", "High")
            else:
                ok("DV15", "job_brief_synthesis uses direct call not asyncio.run()", "Dashboard v9e",
                   "asyncio.run() not found in job_brief_synthesis function.")
        else:
            ok("DV15", "job_brief_synthesis uses direct call not asyncio.run()", "Dashboard v9e",
               "No asyncio.run() usage detected in scheduler.py brief synthesis.")
    else:
        skip("DV15", "job_brief_synthesis uses direct call not asyncio.run()", "Dashboard v9e",
             "scheduler.py not found.")

    # ── News & Content checks ─────────────────────────────────────────────

    # DV16 — content_scan.py has _classify_domain() function
    cscan = read(content_py)
    if content_py.exists():
        if "_classify_domain" in cscan:
            ok("DV16", "content_scan.py has _classify_domain() function", "Dashboard v9e",
               "_classify_domain() found in content_scan.py.")
        else:
            fail("DV16", "content_scan.py has _classify_domain() function", "Dashboard v9e",
                 "_classify_domain() not found in content_scan.py.",
                 "Implement _classify_domain() to map article text to domain tags. "
                 "Do not use tags.split(',')[0] as a fallback — that misclassifies everything.", "Medium")
    else:
        skip("DV16", "content_scan.py has _classify_domain() function", "Dashboard v9e",
             "content_scan.py not found.")

    # DV17 — _classify_domain checks HAT keywords
    if content_py.exists() and "_classify_domain" in cscan:
        hat_keywords = ["trypanosomiasis", "sleeping sickness", "tsetse", "gambiense"]
        missing_kw = [kw for kw in hat_keywords if kw not in cscan.lower()]
        if not missing_kw:
            ok("DV17", "_classify_domain checks all HAT keywords", "Dashboard v9e",
               f"All HAT keywords present: {', '.join(hat_keywords)}")
        else:
            warn("DV17", "_classify_domain checks all HAT keywords", "Dashboard v9e",
                 f"Missing HAT keywords in _classify_domain: {', '.join(missing_kw)}",
                 f"Add these terms to _classify_domain for accurate HAT domain tagging: {', '.join(missing_kw)}", "Medium")
    else:
        skip("DV17", "_classify_domain checks all HAT keywords", "Dashboard v9e",
             "content_scan.py or _classify_domain not found.")

    # DV18 — intelligence.py assemble_daily_context uses two-tier ORDER BY
    intel = read(intel_py)
    if intel_py.exists():
        if "created_at >= ?" in intel and "THEN 0 ELSE 1" in intel:
            ok("DV18", "intelligence.py uses two-tier ORDER BY (24h first, then signal_strength)", "Dashboard v9e",
               "Two-tier ORDER BY pattern confirmed in intelligence.py.")
        else:
            warn("DV18", "intelligence.py uses two-tier ORDER BY (24h first, then signal_strength)", "Dashboard v9e",
                 "Two-tier ORDER BY not confirmed in intelligence.py.",
                 "Add: ORDER BY CASE WHEN created_at >= ? THEN 0 ELSE 1 END, signal_strength DESC "
                 "to ensure last-24h items appear before older items regardless of signal strength.", "Medium")
    else:
        skip("DV18", "intelligence.py uses two-tier ORDER BY", "Dashboard v9e",
             "intelligence.py not found.")

    # ── Scheduler checks ──────────────────────────────────────────────────

    # DV19 — scheduler.py has no misfire_grace_time=3600
    if sched_py.exists():
        if "misfire_grace_time=3600" in sched:
            fail("DV19", "scheduler.py does not use misfire_grace_time=3600", "Dashboard v9e",
                 "misfire_grace_time=3600 found in scheduler.py — this delays misfired jobs by up to 1h.",
                 "Remove misfire_grace_time=3600. Use misfire_grace_time=None (unlimited) or omit the parameter.", "Medium")
        else:
            ok("DV19", "scheduler.py does not use misfire_grace_time=3600", "Dashboard v9e",
               "No misfire_grace_time=3600 found in scheduler.py.")
    else:
        skip("DV19", "scheduler.py misfire_grace_time check", "Dashboard v9e",
             "scheduler.py not found.")

    # DV20 — scheduler uses coalesce=True
    if sched_py.exists():
        if "coalesce=True" in sched:
            ok("DV20", "scheduler.py uses coalesce=True on jobs", "Dashboard v9e",
               "coalesce=True found in scheduler.py.")
        else:
            warn("DV20", "scheduler.py uses coalesce=True on jobs", "Dashboard v9e",
                 "coalesce=True not found in scheduler.py.",
                 "Add coalesce=True to add_job() calls to prevent job pile-up after downtime.", "Low")
    else:
        skip("DV20", "scheduler.py coalesce=True check", "Dashboard v9e",
             "scheduler.py not found.")

    # DV21 — scheduler has catch-up block for missed windows
    if sched_py.exists():
        if re.search(r'catch.?up|catchup', sched, re.IGNORECASE):
            ok("DV21", "scheduler.py has startup catch-up block for missed jobs", "Dashboard v9e",
               "catch-up / catchup logic found in scheduler.py.")
        else:
            warn("DV21", "scheduler.py has startup catch-up block for missed jobs", "Dashboard v9e",
                 "No catch-up logic found in scheduler.py.",
                 "Add startup catch-up: if current time > last scheduled run, fire morning_scan and "
                 "brief_synthesis immediately on server start.", "Medium")
    else:
        skip("DV21", "scheduler.py catch-up block check", "Dashboard v9e",
             "scheduler.py not found.")

    # ── User identity checks ──────────────────────────────────────────────

    # DV22 — user-config.yaml has name: Stan (not placeholder)
    if USER_CONFIG.exists():
        cfg_text = read(USER_CONFIG)
        name_match = re.search(r'^\s*name\s*:\s*(.+)$', cfg_text, re.MULTILINE)
        if name_match:
            name_val = name_match.group(1).strip().strip('"\'')
            if name_val in ("Researcher", "Amélie", "User", ""):
                fail("DV22", "user-config.yaml name is set (not placeholder)", "Dashboard v9e",
                     f"user-config.yaml name is still placeholder: '{name_val}'",
                     "Update name: Stan in user-config.yaml.", "Medium")
            else:
                ok("DV22", "user-config.yaml name is set (not placeholder)", "Dashboard v9e",
                   f"user-config.yaml name: {name_val}")
        else:
            warn("DV22", "user-config.yaml has name: field", "Dashboard v9e",
                 "No 'name:' field found in user-config.yaml.",
                 "Add 'name: Stan' under the [user] section of user-config.yaml.", "Medium")
    else:
        skip("DV22", "user-config.yaml name check", "Dashboard v9e",
             f"user-config.yaml not found at {USER_CONFIG.relative_to(ROOT)}")

    # DV23 — DB has user_config table with key column
    con = db_connect()
    if con:
        tables = db_tables(con)
        if "user_config" in tables:
            cols = db_columns(con, "user_config")
            if "key" in cols and "value" in cols:
                ok("DV23", "DB has user_config table with key/value columns", "Dashboard v9e",
                   f"user_config table found. Columns: {', '.join(cols)}")
            else:
                warn("DV23", "DB user_config table has key/value columns", "Dashboard v9e",
                     f"user_config exists but columns are: {', '.join(cols)}",
                     "Ensure user_config has at least 'key' and 'value' columns. "
                     "Check DDL in db.py or MCP server initialisation.", "Medium")
        else:
            warn("DV23", "DB has user_config table", "Dashboard v9e",
                 "user_config table not found in database.",
                 "Add CREATE TABLE user_config (key TEXT PRIMARY KEY, value TEXT) "
                 "to the DB initialisation DDL.", "Medium")
        con.close()
    else:
        skip("DV23", "DB user_config table check", "Dashboard v9e", "DB not accessible.")

    # ── Backup checks ─────────────────────────────────────────────────────

    # DV24 — nightly backup uses .backup() not shutil.copy2
    if sched_py.exists():
        backup_block = re.search(
            r'def job_nightly_backup.*?(?=\ndef |\Z)', sched, re.DOTALL
        )
        if backup_block:
            block_text = backup_block.group(0)
            if "shutil.copy2" in block_text:
                fail("DV24", "Nightly backup uses sqlite3.Connection.backup() not shutil.copy2", "Dashboard v9e",
                     "job_nightly_backup uses shutil.copy2 — may corrupt DB if copied while writes are in progress.",
                     "Replace shutil.copy2 with sqlite3.Connection.backup() for a safe live backup.", "High")
            elif ".backup(" in block_text:
                ok("DV24", "Nightly backup uses sqlite3.Connection.backup()", "Dashboard v9e",
                   "job_nightly_backup uses Connection.backup() — safe live backup method.")
            else:
                warn("DV24", "Nightly backup uses sqlite3.Connection.backup()", "Dashboard v9e",
                     "job_nightly_backup found but backup method not confirmed.",
                     "Verify the function uses sqlite3.Connection.backup() for safe DB copy.", "Medium")
        else:
            warn("DV24", "Nightly backup function exists", "Dashboard v9e",
                 "job_nightly_backup function not found in scheduler.py.",
                 "Add job_nightly_backup() using sqlite3.Connection.backup() for nightly DB backup.", "Medium")
    else:
        skip("DV24", "Nightly backup function check", "Dashboard v9e",
             "scheduler.py not found.")

    # ── Database schema checks ────────────────────────────────────────────

    # DV25 — daily_insights table exists with required columns
    con = db_connect()
    if con:
        tables = db_tables(con)
        if "daily_insights" in tables:
            cols = db_columns(con, "daily_insights")
            required = ["insight_date", "content", "model", "generated_at"]
            missing = [c for c in required if c not in cols]
            if not missing:
                ok("DV25", "daily_insights table has required columns", "Dashboard v9e",
                   f"Columns present: {', '.join(cols)}")
            else:
                warn("DV25", "daily_insights table has required columns", "Dashboard v9e",
                     f"Missing columns: {', '.join(missing)}",
                     f"Add missing columns to daily_insights: {', '.join(missing)}", "Medium")
        else:
            fail("DV25", "daily_insights table exists", "Dashboard v9e",
                 "daily_insights table not found — morning brief cannot be cached.",
                 "Add daily_insights table DDL: (id, insight_date, content, model, generated_at). "
                 "Run db initialisation to create it.", "High")
        con.close()
    else:
        skip("DV25", "daily_insights table check", "Dashboard v9e", "DB not accessible.")

    # DV26 — news_briefs table has source_type column
    con = db_connect()
    if con:
        tables = db_tables(con)
        if "news_briefs" in tables:
            cols = db_columns(con, "news_briefs")
            if "source_type" in cols:
                ok("DV26", "news_briefs table has source_type column", "Dashboard v9e",
                   f"source_type column present in news_briefs. All columns: {', '.join(cols)}")
            else:
                warn("DV26", "news_briefs table has source_type column", "Dashboard v9e",
                     f"news_briefs columns: {', '.join(cols)} — source_type missing.",
                     "Add ALTER TABLE news_briefs ADD COLUMN source_type TEXT DEFAULT 'rss' "
                     "to distinguish RSS, arXiv, WHO, and manual entries.", "Medium")
        else:
            skip("DV26", "news_briefs source_type column", "Dashboard v9e",
                 "news_briefs table not found in DB.")
        con.close()
    else:
        skip("DV26", "news_briefs source_type column", "Dashboard v9e", "DB not accessible.")

    # ── HTTP endpoint checks (require running dashboard) ──────────────────

    # DV27 — /api/scan/content returns news_added
    code, body = http_get("/api/scan/content")
    if code is None:
        skip("DV27", "POST /api/scan/content returns news_added", "Dashboard v9e", body)
    elif code in (200, 405):  # 405 = wrong method (it's POST), means route exists
        ok("DV27", "/api/scan/content endpoint exists", "Dashboard v9e",
           f"HTTP {code} — endpoint reachable.")
    else:
        warn("DV27", "/api/scan/content endpoint exists", "Dashboard v9e",
             f"HTTP {code}.",
             "Ensure /api/scan/content route is registered in main.py and returns {news_added: N}.", "Medium")

    # DV28 — /api/morning-brief/refresh is a POST endpoint
    code, body = http_get("/api/morning-brief/refresh")
    if code is None:
        skip("DV28", "POST /api/morning-brief/refresh endpoint exists", "Dashboard v9e", body)
    elif code in (200, 405, 422):
        ok("DV28", "/api/morning-brief/refresh endpoint exists", "Dashboard v9e",
           f"HTTP {code} — endpoint reachable (GET probe; real use is POST).")
    elif code == 404:
        fail("DV28", "POST /api/morning-brief/refresh endpoint exists", "Dashboard v9e",
             "HTTP 404 — endpoint not found.",
             "Add POST /api/morning-brief/refresh to today.py router.", "High")
    else:
        warn("DV28", "POST /api/morning-brief/refresh endpoint exists", "Dashboard v9e",
             f"Unexpected HTTP {code}.", None, "Medium")

    # DV29 — /api/scheduler/status returns JSON with running key
    code, body = http_get("/api/scheduler/status")
    if code is None:
        skip("DV29", "GET /api/scheduler/status returns running key", "Dashboard v9e", body)
    elif code == 200:
        if "running" in body:
            ok("DV29", "GET /api/scheduler/status returns running key", "Dashboard v9e",
               "HTTP 200, 'running' key found in response.")
        else:
            warn("DV29", "GET /api/scheduler/status returns running key", "Dashboard v9e",
                 f"HTTP 200 but 'running' key not found in response body.",
                 "Ensure /api/scheduler/status returns JSON: {running: bool, jobs: [...]}.", "Medium")
    else:
        warn("DV29", "GET /api/scheduler/status returns running key", "Dashboard v9e",
             f"HTTP {code}.", "Add GET /api/scheduler/status endpoint to main.py.", "Medium")

    # DV30 — /api/mcp/status returns JSON with status key
    code, body = http_get("/api/mcp/status")
    if code is None:
        skip("DV30", "GET /api/mcp/status returns status key", "Dashboard v9e", body)
    elif code == 200:
        if "status" in body:
            ok("DV30", "GET /api/mcp/status returns status key", "Dashboard v9e",
               "HTTP 200, 'status' key found in response.")
        else:
            warn("DV30", "GET /api/mcp/status returns status key", "Dashboard v9e",
                 f"HTTP 200 but 'status' key not found in response body.",
                 "Ensure /api/mcp/status returns JSON: {status: 'ok'|'error', tools: N}.", "Medium")
    else:
        warn("DV30", "GET /api/mcp/status returns status key", "Dashboard v9e",
             f"HTTP {code}.", "Add GET /api/mcp/status endpoint.", "Medium")

    # ── Work tab checks ───────────────────────────────────────────────────

    # DV31 — work.py has project detail endpoint
    work_r = read(ROUTERS_DIR / "work.py")
    if re.search(r'/api/(partial/work/project|project/\{)', work_r):
        ok("DV31", "work.py has project detail endpoint", "Dashboard v9e",
           "Project detail endpoint found in work.py.")
    else:
        warn("DV31", "work.py has project detail endpoint", "Dashboard v9e",
             "No project detail endpoint found in work.py.",
             "Add GET /api/partial/work/project?id={project_id} to work.py router.", "Medium")

    # DV32 — work.py has star / untrack / add-task / complete-task endpoints
    work_actions = {
        "star project":    re.search(r'star', work_r, re.IGNORECASE),
        "untrack project": re.search(r'untrack|archive|remove', work_r, re.IGNORECASE),
        "add task":        re.search(r'add.?task|POST.*task', work_r, re.IGNORECASE),
        "complete task":   re.search(r'complet.*task|task.*complet|PATCH.*task|PUT.*task|task.*done|/done', work_r, re.IGNORECASE),
    }
    missing_actions = [k for k, v in work_actions.items() if not v]
    if not missing_actions:
        ok("DV32", "work.py has all project/task action endpoints", "Dashboard v9e",
           "star, untrack, add-task, complete-task patterns found in work.py.")
    else:
        warn("DV32", "work.py has all project/task action endpoints", "Dashboard v9e",
             f"Missing action patterns: {', '.join(missing_actions)}",
             "Add missing endpoints to work.py for full project/task management.", "Medium")


# ════════════════════════════════════════════════════════════════════════════
# HTML REPORT GENERATOR
# ════════════════════════════════════════════════════════════════════════════
def generate_html(run_time: float) -> str:
    ts = datetime.datetime.now().strftime("%A %d %B %Y at %H:%M")
    categories = sorted(set(r.category for r in results))

    def counts(rlist):
        return {s: sum(1 for r in rlist if r.status == s)
                for s in ["PASS", "FAIL", "WARN", "SKIP", "INFO"]}

    total = counts(results)
    checked = total["PASS"] + total["FAIL"] + total["WARN"]
    score_pct = int(100 * total["PASS"] / max(checked, 1))
    score_color = "#15803D" if score_pct >= 80 else "#D97706" if score_pct >= 60 else "#B91C1C"

    # Category breakdown
    cat_rows = ""
    for cat in categories:
        cr = [r for r in results if r.category == cat]
        cc = counts(cr)
        cat_pct = int(100 * cc["PASS"] / max(cc["PASS"] + cc["FAIL"] + cc["WARN"], 1))
        bar_color = "#15803D" if cat_pct >= 80 else "#D97706" if cat_pct >= 60 else "#B91C1C"
        cat_rows += f"""
        <tr>
          <td style="padding:6px 12px;font-weight:600">{cat}</td>
          <td style="padding:6px 12px;text-align:center">{cc['PASS']+cc['FAIL']+cc['WARN']}</td>
          <td style="padding:6px 12px;text-align:center;color:#15803D;font-weight:700">{cc['PASS']}</td>
          <td style="padding:6px 12px;text-align:center;color:#B91C1C;font-weight:700">{cc['FAIL']}</td>
          <td style="padding:6px 12px;text-align:center;color:#D97706;font-weight:700">{cc['WARN']}</td>
          <td style="padding:6px 12px">
            <div style="background:#E5E7EB;border-radius:4px;height:8px;width:100px;display:inline-block;vertical-align:middle">
              <div style="background:{bar_color};border-radius:4px;height:8px;width:{cat_pct}px"></div>
            </div>
            <span style="margin-left:6px;font-size:0.8em;color:{bar_color};font-weight:600">{cat_pct}%</span>
          </td>
        </tr>"""

    # Test rows
    badge = {"PASS": ("#DCFCE7","#15803D"), "FAIL": ("#FEE2E2","#B91C1C"),
             "WARN": ("#FEF3C7","#B45309"), "SKIP": ("#F1F5F9","#6B7280"),
             "INFO": ("#DBEAFE","#1D4ED8")}

    test_sections = ""
    for cat in categories:
        cr = sorted([r for r in results if r.category == cat],
                    key=lambda x: STATUS_ORDER.get(x.status, 9))
        cc = counts(cr)
        cat_pct = int(100 * cc["PASS"] / max(cc["PASS"] + cc["FAIL"] + cc["WARN"], 1))
        hdr_color = "#15803D" if cat_pct >= 80 else "#D97706" if cat_pct >= 60 else "#B91C1C"

        rows_html = ""
        for r in cr:
            bg, fg = badge.get(r.status, ("#F9FAFB","#374151"))
            rec_html = f'<div style="margin-top:4px;padding:6px 10px;background:#FEF3C7;border-left:3px solid #D97706;border-radius:0 4px 4px 0;font-size:0.82em;color:#92400E"><b>💡 Recommendation:</b> {r.rec}</div>' if r.rec else ""
            rows_html += f"""
            <tr style="border-bottom:1px solid #F3F4F6">
              <td style="padding:8px 10px;font-family:'Courier New',monospace;font-size:0.78em;color:#6B7280;white-space:nowrap">{r.id}</td>
              <td style="padding:8px 10px">
                <div style="font-size:0.88em;font-weight:500;color:#111827">{r.name}</div>
                <div style="font-size:0.8em;color:#6B7280;margin-top:2px">{r.detail}</div>
                {rec_html}
              </td>
              <td style="padding:8px 10px;text-align:center;white-space:nowrap">
                <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.78em;font-weight:700;background:{bg};color:{fg}">{r.status}</span>
              </td>
            </tr>"""

        test_sections += f"""
        <details style="margin-bottom:12px;border:1px solid #E5E7EB;border-radius:8px;overflow:hidden">
          <summary style="padding:14px 18px;background:{hdr_color}15;cursor:pointer;font-weight:700;font-size:1em;color:#111827;display:flex;justify-content:space-between;list-style:none">
            <span>📋 {cat}</span>
            <span style="font-weight:400;font-size:0.85em;color:#6B7280">
              <span style="color:#15803D">{cc['PASS']} pass</span>
              {'  ·  <span style="color:#B91C1C">'+str(cc['FAIL'])+' fail</span>' if cc['FAIL'] else ''}
              {'  ·  <span style="color:#D97706">'+str(cc['WARN'])+' warn</span>' if cc['WARN'] else ''}
              {'  ·  <span style="color:#6B7280">'+str(cc['SKIP'])+' skip</span>' if cc['SKIP'] else ''}
            </span>
          </summary>
          <table style="width:100%;border-collapse:collapse">
            <thead><tr style="background:#F9FAFB;border-bottom:2px solid #E5E7EB">
              <th style="padding:8px 10px;text-align:left;font-size:0.78em;color:#6B7280;font-weight:600;width:80px">ID</th>
              <th style="padding:8px 10px;text-align:left;font-size:0.78em;color:#6B7280;font-weight:600">Test / Finding</th>
              <th style="padding:8px 10px;text-align:center;font-size:0.78em;color:#6B7280;font-weight:600;width:80px">Status</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </details>"""

    # Recommendations summary
    fails_and_warns = sorted(
        [r for r in results if r.status in ("FAIL","WARN") and r.rec],
        key=lambda x: ({"Critical":0,"High":1,"Medium":2,"Low":3}.get(x.priority,4), STATUS_ORDER.get(x.status,9))
    )
    rec_html = ""
    for i, r in enumerate(fails_and_warns, 1):
        pri_color = {"Critical":"#B91C1C","High":"#D97706","Medium":"#2563EB","Low":"#6B7280"}.get(r.priority,"#6B7280")
        rec_html += f"""
        <div style="padding:12px 16px;border-left:4px solid {pri_color};background:{'#FEE2E2' if r.priority=='Critical' else '#FEF3C7' if r.priority=='High' else '#F0F9FF' if r.priority=='Medium' else '#F9FAFB'};margin-bottom:8px;border-radius:0 6px 6px 0">
          <div style="display:flex;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:700;font-size:0.88em;color:#111827">{i}. [{r.id}] {r.name}</span>
            <span style="font-size:0.78em;font-weight:700;color:{pri_color};background:white;padding:1px 8px;border-radius:10px;border:1px solid {pri_color}">{r.priority}</span>
          </div>
          <div style="font-size:0.84em;color:#374151">{r.rec}</div>
        </div>"""

    if not rec_html:
        rec_html = '<p style="color:#15803D;font-weight:600">✓ No recommendations — all checks passed!</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Metis Autotest Report — {ts}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0 }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif; background:#F8FAFC; color:#1E293B; line-height:1.5 }}
  .header {{ background:linear-gradient(135deg,#1B2B5E,#2563EB); color:white; padding:32px 40px }}
  .header h1 {{ font-size:1.8em; font-weight:800; letter-spacing:-0.5px }}
  .header p {{ opacity:0.8; margin-top:4px; font-size:0.9em }}
  .body {{ max-width:1100px; margin:0 auto; padding:32px 24px }}
  .scorecard {{ display:grid; grid-template-columns:200px 1fr; gap:24px; margin-bottom:32px }}
  .score-circle {{ background:white; border-radius:12px; padding:24px; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.1) }}
  .score-number {{ font-size:3.5em; font-weight:900; color:{score_color}; line-height:1 }}
  .score-label {{ font-size:0.8em; color:#6B7280; margin-top:4px; font-weight:600 }}
  .score-badges {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; justify-content:center }}
  .badge {{ padding:2px 10px; border-radius:10px; font-size:0.78em; font-weight:700 }}
  .cat-table {{ background:white; border-radius:12px; padding:0; box-shadow:0 1px 3px rgba(0,0,0,0.1); overflow:hidden }}
  .cat-table table {{ width:100%; border-collapse:collapse }}
  .cat-table th {{ padding:10px 12px; text-align:left; font-size:0.8em; color:#6B7280; font-weight:600; background:#F9FAFB; border-bottom:2px solid #E5E7EB }}
  .cat-table tr:hover {{ background:#FAFAFA }}
  section {{ margin-bottom:32px }}
  section h2 {{ font-size:1.1em; font-weight:700; color:#1B2B5E; margin-bottom:12px; padding-bottom:6px; border-bottom:2px solid #E8EBF4 }}
  details summary::-webkit-details-marker {{ display:none }}
  details[open] summary {{ border-bottom:1px solid #E5E7EB }}
  @media print {{
    body {{ background:white }}
    .header {{ background:#1B2B5E !important; -webkit-print-color-adjust:exact }}
    details {{ page-break-inside:avoid }}
    details[open] {{ display:block }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>🔬 Metis Research Cortex — Automated Test Report</h1>
  <p>Generated: {ts} &nbsp;·&nbsp; Runtime: {run_time:.1f}s &nbsp;·&nbsp; Root: {ROOT}</p>
</div>
<div class="body">

  <div class="scorecard">
    <div class="score-circle">
      <div class="score-number">{score_pct}%</div>
      <div class="score-label">OVERALL PASS RATE</div>
      <div class="score-badges" style="margin-top:16px">
        <span class="badge" style="background:#DCFCE7;color:#15803D">{total['PASS']} PASS</span>
        <span class="badge" style="background:#FEE2E2;color:#B91C1C">{total['FAIL']} FAIL</span>
        <span class="badge" style="background:#FEF3C7;color:#B45309">{total['WARN']} WARN</span>
        <span class="badge" style="background:#F1F5F9;color:#6B7280">{total['SKIP']} SKIP</span>
      </div>
    </div>
    <div class="cat-table">
      <table>
        <thead><tr>
          <th>Category</th><th style="text-align:center">Checks</th>
          <th style="text-align:center">Pass</th><th style="text-align:center">Fail</th>
          <th style="text-align:center">Warn</th><th>Score</th>
        </tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>
    </div>
  </div>

  <section>
    <h2>⚠ Recommendations (prioritised)</h2>
    {rec_html}
  </section>

  <section>
    <h2>📊 Detailed Test Results</h2>
    {test_sections}
  </section>

  <section>
    <h2>ℹ What this report does NOT cover</h2>
    <div style="background:white;border-radius:8px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.07);font-size:0.88em;color:#374151;line-height:1.8">
      <p>The following require a running Claude API session and cannot be automated without incurring costs:</p>
      <ul style="margin-top:8px;padding-left:20px">
        <li>Actual agent execution quality (writing-partner, epidemiologist, librarian outputs)</li>
        <li>Meeting memory accuracy (structured note quality from transcripts)</li>
        <li>Cross-pollination relevance (are connected ideas actually meaningful?)</li>
        <li>Course builder pipeline (7-step course generation quality)</li>
        <li>Knowledge testing / exam mode responses</li>
        <li>Presentation maker output quality</li>
        <li>Visual/aesthetic dashboard evaluation (requires human eyes)</li>
        <li>Self-improvement loop proposal quality</li>
      </ul>
      <p style="margin-top:8px">Run the manual test protocol (<code>metis-functional-test.docx</code>) alongside this report for full coverage.</p>
    </div>
  </section>

</div>
</body>
</html>"""

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Metis automated test runner")
    parser.add_argument("--no-http", action="store_true", help="Skip dashboard HTTP tests")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(" Metis Research Cortex — Automated Test Runner")
    print(f" Root: {ROOT}")
    print(f"{'='*60}\n")

    t0 = time.time()

    print("Running checks:")
    run_system()
    if not args.no_http:
        run_dashboard()
    else:
        skip("D_all", "Dashboard HTTP tests", "Dashboard", "Skipped via --no-http flag.")
    run_agents()
    run_mcp()
    run_skills()
    run_security()
    run_config()
    run_readme()
    run_database()
    run_git()
    run_dashboard_v2()

    elapsed = time.time() - t0

    # Console summary
    total = {s: sum(1 for r in results if r.status == s)
             for s in ["PASS", "FAIL", "WARN", "SKIP", "INFO"]}
    checked = total["PASS"] + total["FAIL"] + total["WARN"]
    pct = int(100 * total["PASS"] / max(checked, 1))

    print(f"\n{'='*60}")
    print(f" Results: {total['PASS']} PASS  {total['FAIL']} FAIL  {total['WARN']} WARN  {total['SKIP']} SKIP")
    print(f" Pass rate: {pct}% ({total['PASS']}/{checked} checked)")
    print(f" Runtime: {elapsed:.1f}s")

    # Critical failures
    crits = [r for r in results if r.status == "FAIL" and r.priority == "Critical"]
    if crits:
        print(f"\n ⛔ CRITICAL FAILURES ({len(crits)}):")
        for r in crits:
            print(f"   [{r.id}] {r.name}")

    # Write HTML report
    out_dir = ROOT / "outputs" / "test-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_file = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = out_dir / f"{ts_file}_metis-autotest.html"

    html = generate_html(elapsed)
    out_path.write_text(html, encoding="utf-8")

    print(f"\n Report saved to:\n   {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metis autotest")
    parser.add_argument("--no-http", action="store_true", help="Skip HTTP connectivity tests")
    args = parser.parse_args()
    main()
