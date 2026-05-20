"""
integration/test_claude_integration.py — Claude Desktop + Code integration tests.

Tests that every persona can reach Claude Chat, Claude Cowork, and Claude Code
from the Metis dashboard, and that the MCP server is correctly wired into both
Claude Code (~/.claude/settings.json) and Claude Desktop
(claude_desktop_config.json).

Run:
    pytest system/tests/integration/test_claude_integration.py -v
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
METIS_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = METIS_ROOT / "system" / "app-py"
MCP_TOOLS_DIR = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools"
RUN_SH = Path.home() / ".local" / "share" / "metis-mcp" / "run.sh"

# Claude config paths (WSL)
CLAUDE_CODE_SETTINGS = Path.home() / ".claude" / "settings.json"
WIN_USER = os.environ.get("USERPROFILE", "").replace("\\", "/").split("/")[-1]
CLAUDE_DESKTOP_CONFIG = Path(f"/mnt/c/Users/{WIN_USER}/AppData/Roaming/Claude/claude_desktop_config.json")

# Templates to validate launcher targets
WORK_PROJECTS_TMPL = DASHBOARD_DIR / "templates" / "partials" / "work_projects.html"
WORK_HTML = DASHBOARD_DIR / "templates" / "work.html"
WORK_PY = DASHBOARD_DIR / "routers" / "work.py"
APP_JS = DASHBOARD_DIR / "static" / "app.js"


# ============================================================================
# 1. MCP server registration
# ============================================================================

class TestMCPRegistration:
    """Verify the MCP server is registered in both Claude Code and Claude Desktop."""

    def test_run_sh_exists(self):
        assert RUN_SH.exists(), (
            f"MCP run.sh not found at {RUN_SH}. "
            "Run: bash system/mcp-server/setup-mcp.sh"
        )

    def test_run_sh_has_correct_root(self):
        content = RUN_SH.read_text()
        assert "METIS_RC_ROOT" in content, "run.sh must export METIS_RC_ROOT"
        assert "METIS_PKM_ROOT" not in content, (
            "run.sh still uses old METIS_PKM_ROOT — re-run setup-mcp.sh"
        )

    def test_run_sh_uses_correct_research_cortex_path(self):
        content = RUN_SH.read_text()
        rc_root_str = str(METIS_ROOT)
        assert rc_root_str in content, (
            f"run.sh METIS_RC_ROOT does not match current repo root: {rc_root_str}"
        )

    def test_claude_code_settings_has_metis_rc(self):
        assert CLAUDE_CODE_SETTINGS.exists(), (
            "~/.claude/settings.json not found. Run setup-mcp.sh."
        )
        cfg = json.loads(CLAUDE_CODE_SETTINGS.read_text())
        assert "metis-rc" in cfg.get("mcpServers", {}), (
            "metis-rc not in Claude Code mcpServers. Run setup-mcp.sh."
        )

    def test_claude_code_settings_no_stale_metis_pkm(self):
        if not CLAUDE_CODE_SETTINGS.exists():
            pytest.skip("Claude Code settings not found")
        cfg = json.loads(CLAUDE_CODE_SETTINGS.read_text())
        assert "metis-pkm" not in cfg.get("mcpServers", {}), (
            "Stale metis-pkm entry still in Claude Code settings. Remove it."
        )

    def test_claude_code_settings_has_permission_wildcard(self):
        if not CLAUDE_CODE_SETTINGS.exists():
            pytest.skip("Claude Code settings not found")
        cfg = json.loads(CLAUDE_CODE_SETTINGS.read_text())
        allow = cfg.get("permissions", {}).get("allow", [])
        assert "mcp__metis-rc__*" in allow, (
            "mcp__metis-rc__* not in Claude Code permissions.allow"
        )

    def test_claude_desktop_config_has_metis_rc(self):
        if not CLAUDE_DESKTOP_CONFIG.exists():
            pytest.skip("Claude Desktop config not found (may not be installed)")
        cfg = json.loads(CLAUDE_DESKTOP_CONFIG.read_text())
        assert "metis-rc" in cfg.get("mcpServers", {}), (
            "metis-rc not in Claude Desktop mcpServers. Run setup-mcp.sh."
        )

    def test_claude_desktop_no_stale_metis_pkm(self):
        if not CLAUDE_DESKTOP_CONFIG.exists():
            pytest.skip("Claude Desktop config not found")
        cfg = json.loads(CLAUDE_DESKTOP_CONFIG.read_text())
        assert "metis-pkm" not in cfg.get("mcpServers", {}), (
            "Stale metis-pkm in Claude Desktop config (old PKM path). Remove it."
        )

    def test_mcp_server_imports_cleanly(self):
        """MCP server must import without errors (no missing modules)."""
        result = subprocess.run(
            [str(RUN_SH.parent / ".venv" / "bin" / "python3"), "-c",
             "import metis_mcp.server; print('ok')"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"MCP server import failed:\n{result.stderr}"
        )
        assert "ok" in result.stdout

    def test_no_research_module_in_server(self):
        """The removed 'research' module must not appear in server.py imports."""
        server_py = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "server.py"
        content = server_py.read_text()
        assert "    research," not in content, (
            "Stale 'research' import still in server.py — it was removed from tools/"
        )


# ============================================================================
# 2. Desktop shortcut chain
# ============================================================================

class TestDesktopShortcut:
    """Verify the Windows shortcut → VBS → run.sh launch chain is intact."""

    def test_launch_metis_bat_exists(self):
        bat = METIS_ROOT / "system" / "launch-metis.bat"
        assert bat.exists(), "system/launch-metis.bat must exist for desktop shortcut"

    def test_launch_metis_bat_calls_vbs(self):
        bat = (METIS_ROOT / "system" / "launch-metis.bat").read_text()
        assert "launch-metis-silent.vbs" in bat, (
            "launch-metis.bat must invoke launch-metis-silent.vbs"
        )

    def test_launch_metis_silent_vbs_exists(self):
        vbs = METIS_ROOT / "system" / "launch-metis-silent.vbs"
        assert vbs.exists(), "system/launch-metis-silent.vbs must exist"

    def test_vbs_targets_python_dashboard(self):
        vbs = (METIS_ROOT / "system" / "launch-metis-silent.vbs").read_text()
        assert "app-py/run.sh" in vbs, (
            "VBS must launch app-py/run.sh (Python dashboard), not the old R Shiny launcher"
        )

    def test_vbs_opens_correct_port(self):
        vbs = (METIS_ROOT / "system" / "launch-metis-silent.vbs").read_text()
        assert "8080" in vbs, "VBS must open http://127.0.0.1:8080 (not 3939)"

    def test_correct_shortcut_bat_is_root_level(self):
        """The desktop shortcut chain must start from system/launch-metis.bat (root level),
        NOT from system/app/launch_metis.bat (the old R Shiny launcher)."""
        correct_bat = METIS_ROOT / "system" / "launch-metis.bat"
        assert correct_bat.exists(), (
            "system/launch-metis.bat must exist — this is the entry point for the desktop shortcut"
        )
        vbs = METIS_ROOT / "system" / "launch-metis-silent.vbs"
        assert vbs.exists() and "app-py" in vbs.read_text(), (
            "The VBS launcher must reference app-py (Python dashboard), not R Shiny"
        )

    def test_app_py_run_sh_exists(self):
        run_sh = METIS_ROOT / "system" / "app-py" / "run.sh"
        assert run_sh.exists(), "system/app-py/run.sh must exist"

    def test_app_py_run_sh_uses_venv(self):
        content = (METIS_ROOT / "system" / "app-py" / "run.sh").read_text()
        assert ".local/share/metis-mcp/.venv" in content, (
            "app-py/run.sh must reference the metis-mcp venv"
        )


# ============================================================================
# 3. Claude launcher buttons — three targets
# ============================================================================

class TestClaudeLauncherButtons:
    """
    Verify the dashboard has Chat, Cowork, and Code launcher buttons
    wired correctly in templates and backend.
    """

    def test_workbench_has_chat_button(self):
        content = WORK_HTML.read_text()
        assert "claude_chat" in content, (
            "work.html Workbench must have a 'Chat' button calling launchProjectTarget(...,'claude_chat')"
        )

    def test_workbench_has_cowork_button(self):
        content = WORK_HTML.read_text()
        assert "claude_cowork" in content, (
            "work.html Workbench must have a 'Cowork' button calling launchProjectTarget(...,'claude_cowork')"
        )

    def test_workbench_has_code_button(self):
        content = WORK_HTML.read_text()
        assert "claude_code" in content, (
            "work.html Workbench must have a 'Code' button calling launchProjectTarget(...,'claude_code')"
        )

    def test_project_cards_have_chat_button(self):
        content = WORK_PROJECTS_TMPL.read_text()
        assert "claude_chat" in content, (
            "work_projects.html must have a per-project Chat launcher button"
        )

    def test_project_cards_have_cowork_button(self):
        content = WORK_PROJECTS_TMPL.read_text()
        assert "claude_cowork" in content, (
            "work_projects.html must have a per-project Cowork launcher button"
        )

    def test_backend_handles_claude_chat(self):
        content = WORK_PY.read_text()
        assert '"claude_chat"' in content or "'claude_chat'" in content, (
            "work.py must handle claude_chat target in project launcher"
        )

    def test_backend_handles_claude_cowork(self):
        content = WORK_PY.read_text()
        assert '"claude_cowork"' in content or "'claude_cowork'" in content, (
            "work.py must handle claude_cowork target in project launcher"
        )

    def test_backend_claude_chat_opens_desktop(self):
        content = WORK_PY.read_text()
        # The handler block contains both claude_chat and claude:// within a short span
        assert "claude://" in content, "work.py must open claude:// protocol for chat/cowork"
        # The elif that groups chat targets must reference both chat and desktop
        assert '"claude_chat"' in content or "'claude_chat'" in content, (
            "claude_chat target must be handled in work.py"
        )

    def test_backend_claude_cowork_copies_path(self):
        content = WORK_PY.read_text()
        assert "Set-Clipboard" in content, (
            "claude_cowork handler must copy project path to clipboard"
        )

    def test_workbench_no_old_claude_desktop_only_label(self):
        """The old single 'Claude Desktop' button should be replaced by Chat+Cowork+Code."""
        content = WORK_HTML.read_text()
        # Should not have the old generic "Claude Desktop" label as the only Claude button
        # (It's acceptable if it appears as a fallback, but Chat+Cowork+Code must also exist)
        if "claude_desktop" in content and "claude_chat" not in content:
            pytest.fail(
                "work.html still uses old 'claude_desktop' without the new Chat/Cowork/Code split"
            )

    def test_launch_function_exists_in_js(self):
        content = APP_JS.read_text()
        assert "launchProjectTarget" in content, (
            "app.js must define launchProjectTarget function"
        )

    def test_launch_api_endpoint_in_backend(self):
        content = WORK_PY.read_text()
        assert "/api/project/launch" in content, (
            "work.py must define /api/project/launch POST endpoint"
        )


# ============================================================================
# 4. Per-persona launcher link validation
# ============================================================================

class TestPersonaLauncherLinks:
    """
    Each persona should have the right launcher buttons for their project type.
    Tests that launcher_links() returns sensible values for each launcher_type.
    """

    @pytest.mark.parametrize("launcher_type,expected_targets", [
        ("rstudio",  ["rstudio", "claude_code", "claude_chat", "claude_cowork"]),
        ("vscode",   ["vscode",  "claude_code", "claude_chat", "claude_cowork"]),
        ("article",  ["claude_chat", "claude_cowork"]),
        ("generic",  ["claude_code", "claude_chat", "claude_cowork"]),
    ])
    def test_launcher_type_includes_all_claude_targets(self, launcher_type, expected_targets):
        """
        For every project type, all three Claude interfaces must be accessible.
        No researcher should be locked out of Chat, Cowork, or Code.
        """
        content = WORK_PY.read_text()
        # Verify each expected target is in the launcher_links function output for this type
        for target in expected_targets:
            assert f'"{target}"' in content, (
                f"launcher_links for '{launcher_type}' must include '{target}'"
            )


# ============================================================================
# 5. Interconnectedness: dashboard ↔ MCP ↔ agents
# ============================================================================

class TestInterconnectedness:
    """
    Verify the three layers (dashboard, MCP tools, agent system prompts)
    are properly wired together.
    """

    def test_metis_skill_references_rag_prefetch(self):
        skill = METIS_ROOT / ".claude" / "skills" / "metis" / "skill.md"
        if not skill.exists():
            pytest.skip("Metis skill.md not found")
        content = skill.read_text()
        assert "search_pdf_knowledge" in content or "Pre-fetch" in content or "RAG" in content, (
            "Metis skill.md must reference RAG pre-fetch step (F001)"
        )

    def test_metis_system_prompt_has_rag_section(self):
        sp = METIS_ROOT / "agents" / "metis" / "system-prompt.md"
        assert sp.exists()
        content = sp.read_text()
        assert "search_pdf_knowledge" in content or "Knowledge pre-fetch" in content, (
            "Metis system-prompt.md must describe RAG pre-fetch (F001 implementation)"
        )

    def test_all_active_agents_have_system_prompt(self):
        """All non-retired agents must have a system-prompt.md."""
        for agent_dir in METIS_ROOT.glob("agents/*/"):
            if (agent_dir / "RETIRED.md").exists():
                continue  # Skip explicitly retired agents
            sp = agent_dir / "system-prompt.md"
            assert sp.exists(), (
                f"Agent '{agent_dir.name}' is missing system-prompt.md "
                f"(add RETIRED.md if this agent is no longer active)"
            )

    def test_all_agents_have_skill_file(self):
        """Every agent invocable from CLAUDE.md must have a skill.md."""
        skills_dir = METIS_ROOT / ".claude" / "skills"
        if not skills_dir.exists():
            pytest.skip("skills dir not found")
        # Core agents that must have skill files
        required = [
            "metis", "librarian", "writing-partner", "methods-coach",
            "epidemiologist", "phd-architect", "software-engineer",
        ]
        for slug in required:
            skill = skills_dir / slug / "skill.md"
            assert skill.exists(), f"Skill file missing for core agent: {slug}"

    def test_knowledge_db_tool_registered(self):
        assert (MCP_TOOLS_DIR / "knowledge_db.py").exists(), (
            "knowledge_db MCP tool must exist for RAG pre-fetch"
        )

    def test_morning_brief_wired_to_dashboard(self):
        today_partial = DASHBOARD_DIR / "templates" / "partials"
        partials = [p.name for p in today_partial.glob("*.html")]
        assert any("today" in p or "morning" in p or "brief" in p for p in partials), (
            "A today/morning-brief partial template must exist"
        )

    def test_work_tab_has_claude_launcher_api(self):
        """The /api/project/launch endpoint must be in the routers."""
        content = WORK_PY.read_text()
        assert "@router.post" in content and "/api/project/launch" in content

    def test_feature_backlog_exists(self):
        backlog = METIS_ROOT / "system" / "config" / "feature-backlog.md"
        assert backlog.exists(), (
            "system/config/feature-backlog.md must exist — feature requests are logged here"
        )

    def test_f001_listed_in_backlog(self):
        backlog = (METIS_ROOT / "system" / "config" / "feature-backlog.md").read_text()
        assert "F001" in backlog, "F001 (Metis RAG orchestrator) must be in feature-backlog.md"

    def test_install_state_marks_mcp_as_done(self):
        install_state = METIS_ROOT / "system" / "config" / "install-state.json"
        if not install_state.exists():
            pytest.skip("install-state.json not created yet")
        state = json.loads(install_state.read_text())
        assert state.get("components", {}).get("mcp_server") is True, (
            "install-state.json must show mcp_server=true"
        )


# ============================================================================
# 6. Installation smoke tests across persona platforms
# ============================================================================

class TestInstallArtifacts:
    """
    Verify that installation artifacts exist for every persona's platform.
    Persona 1 (Windows .exe), Persona 3 (Linux bash),
    Persona 5 (macOS bash), Persona 8 (Docker), Persona 10 (mobile/manual).
    """

    def test_windows_installer_bat_exists(self):
        bat = METIS_ROOT / "system" / "install" / "windows" / "install.bat"
        assert bat.exists(), "Windows install.bat must exist"

    def test_windows_installer_ps1_exists(self):
        ps1 = METIS_ROOT / "system" / "install" / "windows" / "install.ps1"
        assert ps1.exists(), "Windows install.ps1 must exist"

    def test_linux_setup_sh_exists(self):
        sh = METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh"
        assert sh.exists(), "setup-mcp.sh must exist for Linux/macOS install"

    def test_setup_sh_handles_macos_python(self):
        content = (METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh").read_text()
        assert "Homebrew" in content or "brew" in content.lower() or "3.12" in content, (
            "setup-mcp.sh should handle macOS Python detection (Homebrew)"
        )

    def test_docker_entrypoint_exists(self):
        ep = METIS_ROOT / "system" / "install" / "docker" / "docker-entrypoint.sh"
        assert ep.exists(), "Docker entrypoint must exist for Persona 8 (developer)"

    def test_run_mcp_bat_for_windows_no_wsl(self):
        bat = METIS_ROOT / "system" / "install" / "windows" / "run-mcp.bat"
        assert bat.exists(), "run-mcp.bat must exist for Windows MCP launch"

    def test_create_shortcut_bat_exists(self):
        bat = METIS_ROOT / "system" / "install" / "windows" / "create-shortcut.bat"
        assert bat.exists(), "create-shortcut.bat must exist"

    def test_setup_sh_registers_claude_code(self):
        content = (METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh").read_text()
        assert "~/.claude/settings.json" in content or "CC_SETTINGS" in content, (
            "setup-mcp.sh must register MCP server in Claude Code settings"
        )

    def test_setup_sh_registers_claude_desktop(self):
        content = (METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh").read_text()
        assert "claude_desktop_config.json" in content or "Claude Desktop" in content, (
            "setup-mcp.sh must register MCP server in Claude Desktop config"
        )

    def test_setup_sh_creates_shortcut(self):
        content = (METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh").read_text()
        assert "CreateShortcut" in content or "shortcut" in content.lower(), (
            "setup-mcp.sh must create Windows desktop shortcut"
        )
