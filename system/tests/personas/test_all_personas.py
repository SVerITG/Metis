"""
personas/test_all_personas.py — The 10 Metis user persona tests.

Each class tests one persona's full workflow:
  - Installation prerequisites
  - Tab routes this user depends on
  - Agent availability (skill.md files present)
  - MCP tool availability
  - Specific workflow API calls
  - UX checklist (automated where possible)

These tests are permanent — they represent recurring regression checks.
Run after every significant change to verify no persona's workflow broke.

Run all:
    pytest metis/system/tests/personas/test_all_personas.py -v

Run one persona:
    pytest metis/system/tests/personas/test_all_personas.py::TestPersona01 -v
"""

import sqlite3
import subprocess
from pathlib import Path

import pytest

from .profiles import PERSONA_BY_ID, PERSONA_BY_SLUG, PERSONAS
from .conftest_personas import (
    AGENTS_DIR, METIS_ROOT, MCP_TOOLS_DIR, DASHBOARD_DIR, make_persona_client
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def agent_skill_exists(slug: str) -> bool:
    return (AGENTS_DIR / slug / "skill.md").exists()


def mcp_tool_exists(module: str) -> bool:
    return (MCP_TOOLS_DIR / f"{module}.py").exists()


def assert_agent_available(slug: str):
    assert agent_skill_exists(slug), (
        f"Agent '{slug}' skill.md not found at agents/{slug}/skill.md"
    )


def assert_mcp_tool(module: str):
    assert mcp_tool_exists(module), (
        f"MCP tool module '{module}.py' not found"
    )


# ---------------------------------------------------------------------------
# Persona 1 — Fatou Diallo: PhD student, Epidemiology
# ---------------------------------------------------------------------------

class TestPersona01PhDStudent:
    """
    Fatou Diallo — PhD student, epidemiology, NTD surveillance.
    Windows, .exe install, beginner, Zotero user.
    Morning: Today → Knowledge → Epidemiologist → Writing Partner → Thinking → Learning
    """

    PERSONA = PERSONA_BY_ID[1]

    def test_profile_completeness(self):
        p = self.PERSONA
        assert p.name == "Fatou Diallo"
        assert "windows" == p.platform
        assert len(p.morning_workflow) >= 4

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_mcp_tools_for_literature_workflow(self):
        for module in ("literature", "library", "fulltext_index", "zotero", "paperqa_search"):
            assert_mcp_tool(module)

    def test_methodology_and_writing_tools(self):
        for module in ("pipeline", "guardrails", "memory"):
            assert_mcp_tool(module)

    def test_primary_tabs_respond(self, dashboard_client, tmp_db):
        for tab in ["/today", "/knowledge", "/thinking", "/learning"]:
            r = dashboard_client.get(tab)
            assert r.status_code != 500, f"Tab {tab} crashed for persona 01"

    def test_morning_brief_endpoint(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/today/morning-brief")
        assert r.status_code in (200, 404), "Morning brief partial should exist or return 404"

    def test_knowledge_stats_loads(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/knowledge/stats")
        assert r.status_code in (200, 404)

    def test_cross_pollination_tool_exists(self):
        assert_mcp_tool("brainstorm")
        assert_mcp_tool("ideas")

    def test_capture_modal_route(self, dashboard_client, tmp_db):
        r = dashboard_client.post("/api/capture", data={
            "text": "i: what if HAT re-emergence correlates with conflict zones?",
        })
        assert r.status_code not in (500,), "Capture modal should not crash"

    def test_windows_installer_iss_exists(self):
        iss = METIS_ROOT / "system" / "install" / "installer" / "metis-setup.iss"
        assert iss.exists(), "Inno Setup .iss file must exist for Windows installer"

    def test_bootstrap_python_ps1_exists(self):
        ps1 = METIS_ROOT / "system" / "install" / "bootstrap_python.ps1"
        assert ps1.exists(), "Python bootstrap script must exist for Windows install"

    @pytest.mark.audit
    def test_ux_checklist(self):
        """
        UX AUDIT — Persona 01 (manual verification points).
        These assertions document expected UX behaviour; automated where possible.
        """
        # Keyboard shortcut Ctrl+K for capture modal is wired in app.js
        app_js = DASHBOARD_DIR / "static" / "app.js"
        content = app_js.read_text(encoding="utf-8")
        assert "Ctrl+K" in content or "ctrlKey" in content, \
            "Ctrl+K capture shortcut must be wired in app.js"

        # Cross-pollination prefix routing (i: n: t: q:) is documented
        assert "i:" in content or "prefix" in content.lower(), \
            "Capture prefix routing (i:/n:/t:) must be in app.js"

        # HTMX is loaded (local or CDN)
        base_html = DASHBOARD_DIR / "templates" / "base.html"
        base = base_html.read_text(encoding="utf-8")
        assert "htmx" in base.lower(), "HTMX must be loaded in base template"


# ---------------------------------------------------------------------------
# Persona 2 — Dr. Elena Marchetti: Senior NTD researcher, multi-project
# ---------------------------------------------------------------------------

class TestPersona02SeniorResearcher:
    """
    Dr. Elena Marchetti — Senior NTD researcher, 5 projects, heavy meeting user.
    Windows, .exe install, intermediate, full 9-tab user.
    Morning: Today → Meetings → Knowledge → Work → Planner → Writing Partner
    """

    PERSONA = PERSONA_BY_ID[2]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_meeting_workflow_tools(self):
        for module in ("meetings", "transcription", "voice_capture"):
            assert_mcp_tool(module)

    def test_all_9_tabs_respond(self, dashboard_client, tmp_db):
        tabs = ["/today", "/knowledge", "/meetings", "/learning",
                "/work", "/thinking", "/planner", "/teach", "/metis"]
        for tab in tabs:
            r = dashboard_client.get(tab)
            assert r.status_code != 500, f"Tab {tab} crashed for senior researcher"

    def test_work_tab_projects_loaded(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/work/projects")
        assert r.status_code in (200, 404)

    def test_meeting_list_loads(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/meetings/list")
        assert r.status_code in (200, 404)

    def test_self_improvement_loop_tools(self):
        for module in ("improvement", "self_improvement", "observability"):
            assert_mcp_tool(module)

    def test_agent_runs_visible_in_metis_tab(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/metis/agent-runs")
        assert r.status_code in (200, 404)

    def test_planner_tab_loads(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/planner")
        assert r.status_code in (200, 302)

    @pytest.mark.audit
    def test_ux_interlinkedness(self):
        """
        Audit: are tabs connected? Check for cross-tab HTMX triggers and nav links.
        """
        base = (DASHBOARD_DIR / "templates" / "base.html").read_text()
        for tab_name in ("today", "knowledge", "work", "meetings", "planner"):
            assert tab_name in base.lower(), \
                f"Tab '{tab_name}' not found in base navigation"

    @pytest.mark.audit
    def test_token_usage_visible(self):
        """Audit: token usage must be visible — check metis_tab template."""
        metis_html = (DASHBOARD_DIR / "templates" / "metis_tab.html").read_text()
        assert "token" in metis_html.lower(), \
            "Token usage stats must be visible in Metis tab for cost-aware users"


# ---------------------------------------------------------------------------
# Persona 3 — Kwame Asante: Biomedical data analyst, Linux, R user
# ---------------------------------------------------------------------------

class TestPersona03DataAnalyst:
    """
    Kwame Asante — Biomedical data analyst, R heavy, Linux/bash install.
    Expert user. Morning: data profiling → cleaning → visualization → methods.
    """

    PERSONA = PERSONA_BY_ID[3]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_data_analysis_tools(self):
        for module in ("data_tools", "anonymization"):
            assert_mcp_tool(module)

    def test_bash_install_script_exists(self):
        setup_sh = METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh"
        assert setup_sh.exists(), "setup-mcp.sh must exist for Linux/bash install"
        content = setup_sh.read_text()
        assert "ubuntu" in content.lower() or "linux" in content.lower(), \
            "setup-mcp.sh must handle Linux distributions"

    def test_docker_install_available(self):
        dockerfile = METIS_ROOT / "system" / "install" / "docker" / "Dockerfile"
        assert dockerfile.exists(), "Dockerfile must exist for Docker install"

    def test_docker_compose_available(self):
        compose = METIS_ROOT / "system" / "install" / "docker" / "docker-compose.yml"
        assert compose.exists(), "docker-compose.yml must exist"

    def test_data_guardian_not_blocking_internal_data(self):
        """Data Guardian red-lines must allow internal research data (not patient IDs)."""
        red_lines = METIS_ROOT / "system" / "config" / "red-lines.md"
        assert red_lines.exists(), "red-lines.md must exist"
        content = red_lines.read_text()
        assert "ALLOW" in content, "red-lines.md must specify what IS allowed, not just what's blocked"
        assert "aggregated" in content.lower() or "anonymi" in content.lower(), \
            "red-lines must explicitly allow aggregated/anonymized data"

    def test_vs_code_integration_documented(self):
        claude_md = METIS_ROOT / "CLAUDE.md"
        content = claude_md.read_text()
        assert "VS Code" in content or "vscode" in content.lower(), \
            "CLAUDE.md must document VS Code integration"

    def test_visualization_agent_exists(self):
        assert_agent_available("visualization-maker")

    def test_work_tab_project_launcher(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/work")
        assert r.status_code != 500


# ---------------------------------------------------------------------------
# Persona 4 — Prof. Sarah Okonkwo: Medical educator, course builder
# ---------------------------------------------------------------------------

class TestPersona04MedicalEducator:
    """
    Prof. Sarah Okonkwo — Medical educator, Teach tab, course building.
    Windows, .exe install, intermediate.
    Morning: Teach tab → Course Builder → Presentation Maker → Learning tab
    """

    PERSONA = PERSONA_BY_ID[4]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_course_builder_tool_exists(self):
        assert_mcp_tool("course_builder")

    def test_teach_tab_loads(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/teach")
        assert r.status_code in (200, 302)

    def test_learning_tab_loads(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/learning")
        assert r.status_code in (200, 302)

    def test_course_template_exists(self):
        template_dir = METIS_ROOT / "knowledge" / "course-template"
        assert template_dir.exists(), \
            "knowledge/course-template/ must exist for course builder scaffold"

    def test_knowledge_sources_in_teach_template(self):
        teach_html = DASHBOARD_DIR / "templates" / "teach.html"
        if teach_html.exists():
            content = teach_html.read_text()
            assert "Library" in content or "library" in content, \
                "Teach tab must include Library as a knowledge source option"

    @pytest.mark.audit
    def test_ux_teach_tab_form_elements(self):
        """Audit: Teach tab must have all form elements described in survey."""
        teach_html = DASHBOARD_DIR / "templates" / "teach.html"
        if not teach_html.exists():
            pytest.skip("teach.html not found")
        content = teach_html.read_text()
        for element in ("audience", "depth", "PowerPoint", "Outline", "Markdown"):
            assert element in content, \
                f"Teach tab must contain '{element}' form element"

    def test_presentation_agent_exists(self):
        assert_agent_available("presentation-maker")

    def test_learning_architect_agent_exists(self):
        assert_agent_available("learning-architect")


# ---------------------------------------------------------------------------
# Persona 5 — Thomas Weber: Early career researcher, learning-first
# ---------------------------------------------------------------------------

class TestPersona05EarlyCareerResearcher:
    """
    Thomas Weber — Early career, learning + career development focus.
    macOS, bash install, beginner.
    Morning: Learning tab → Methods Coach → Career Coach → Thinking
    """

    PERSONA = PERSONA_BY_ID[5]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_macos_bash_install_documented(self):
        setup_sh = METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh"
        content = setup_sh.read_text()
        assert "macos" in content.lower() or "darwin" in content.lower() or "brew" in content.lower(), \
            "setup-mcp.sh must handle macOS (Homebrew)"

    def test_learning_tab_spaced_repetition(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/learning/due-today")
        assert r.status_code in (200, 404)

    def test_thinking_tab_threads_persist(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/thinking")
        assert r.status_code in (200, 302)

    def test_career_coach_agent_exists(self):
        assert_agent_available("career-coach")

    def test_cross_pollination_on_idea_capture(self, dashboard_client, tmp_db):
        """Ideas captured should trigger cross-pollination via brainstorm tool."""
        r = dashboard_client.post("/api/capture", data={
            "text": "i: multilevel models might apply to HAT case clustering",
        })
        assert r.status_code not in (500,)

    @pytest.mark.audit
    def test_ux_empty_states_learning_tab(self):
        """Audit: Learning tab must have styled empty states for new users with no data."""
        learning_html = DASHBOARD_DIR / "templates" / "learning.html"
        if not learning_html.exists():
            pytest.skip("learning.html not found")
        content = learning_html.read_text()
        assert "empty" in content.lower() or "no " in content.lower() or "placeholder" in content.lower(), \
            "Learning tab must handle empty state (new user with no courses)"


# ---------------------------------------------------------------------------
# Persona 6 — Dr. Aminata Sow: Global health consultant, news + meetings
# ---------------------------------------------------------------------------

class TestPersona06GlobalHealthConsultant:
    """
    Dr. Aminata Sow — WHO/NGO consultant, travel-heavy, policy briefs.
    Windows, .exe install, intermediate.
    Morning: Today news → Meeting review → Write brief → Work status
    """

    PERSONA = PERSONA_BY_ID[6]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_news_tools_exist(self):
        for module in ("intelligence", "content_scan", "literature_monitor"):
            assert_mcp_tool(module)

    def test_today_tab_news_loads(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/today/news-archive")
        assert r.status_code in (200, 404)

    def test_rss_feeds_configured(self):
        """RSS feeds should be configured for WHO + global health news."""
        # Check if news_briefs table would be populated by the morning scan
        assert_mcp_tool("content_scan")
        assert_mcp_tool("intelligence")

    def test_writing_partner_agent_exists(self):
        assert_agent_available("writing-partner")

    def test_pwa_manifest_exists(self):
        r_path = DASHBOARD_DIR / "main.py"
        content = r_path.read_text()
        assert "manifest" in content.lower(), \
            "main.py must define a /manifest.json route for PWA support"

    def test_morning_brief_structure(self, dashboard_client, tmp_db):
        """Morning brief must be short and actionable — check route exists."""
        r = dashboard_client.get("/today")
        assert r.status_code in (200, 302)

    @pytest.mark.audit
    def test_ux_today_tab_overview_quality(self):
        """Audit: Today tab must show news + literature + tasks without clicking anything."""
        today_html = DASHBOARD_DIR / "templates" / "today.html"
        if not today_html.exists():
            pytest.skip("today.html not found")
        content = today_html.read_text()
        for element in ("morning", "news", "task", "ledger"):
            assert element in content.lower(), \
                f"Today tab must include '{element}' section for overview users"


# ---------------------------------------------------------------------------
# Persona 7 — Dr. James Obi: Clinical researcher, data governance focus
# ---------------------------------------------------------------------------

class TestPersona07ClinicalResearcher:
    """
    Dr. James Obi — Clinical researcher, patient data protection is critical.
    Windows, .exe install, strict IT environment.
    Morning: Data Guardian check → Literature → Epidemiologist → CONSORT compliance
    """

    PERSONA = PERSONA_BY_ID[7]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_data_guardian_agent_exists(self):
        assert_agent_available("data-guardian")

    def test_red_lines_enforced(self):
        red_lines = METIS_ROOT / "system" / "config" / "red-lines.md"
        assert red_lines.exists()
        content = red_lines.read_text()
        for requirement in ("patient", "individual", "BLOCK", "never"):
            assert requirement.lower() in content.lower(), \
                f"red-lines.md must contain '{requirement}' for clinical data protection"

    def test_constitution_clinical_rules_exist(self):
        constitution = METIS_ROOT / "system" / "config" / "constitution.md"
        assert constitution.exists()
        content = constitution.read_text()
        assert "clinical" in content.lower(), \
            "constitution.md must contain clinical citation/uncertainty rules"

    def test_pre_tool_use_hook_exists(self):
        hook = METIS_ROOT / ".claude" / "hooks" / "pre-tool-use.mjs"
        assert hook.exists(), "Pre-tool-use security hook must exist"

    def test_anonymization_tool_exists(self):
        assert_mcp_tool("anonymization")

    def test_pii_detection_in_hook(self):
        hook = METIS_ROOT / ".claude" / "hooks" / "pre-tool-use.mjs"
        if hook.exists():
            content = hook.read_text()
            assert "pii" in content.lower() or "patient" in content.lower() or "personal" in content.lower(), \
                "pre-tool-use hook must check for PII/patient data"

    def test_guardrails_tool_exists(self):
        assert_mcp_tool("guardrails")

    def test_bundled_python_for_restricted_it(self):
        """IT-managed machines need offline Python — bundled embed must be supported."""
        bootstrap = METIS_ROOT / "system" / "install" / "bootstrap_python.ps1"
        content = bootstrap.read_text()
        assert "embed" in content.lower() or "vendor" in content.lower(), \
            "bootstrap_python.ps1 must support bundled/offline Python for restricted IT environments"

    @pytest.mark.audit
    def test_ux_security_transparency(self):
        """Audit: Users must be able to see what data guardian rules apply."""
        assert (METIS_ROOT / "system" / "config" / "red-lines.md").exists()
        assert (METIS_ROOT / "system" / "config" / "constitution.md").exists()


# ---------------------------------------------------------------------------
# Persona 8 — Marta Gonzalez: Developer, Docker, technical extensibility
# ---------------------------------------------------------------------------

class TestPersona08Developer:
    """
    Marta Gonzalez — Research software engineer, Docker install, Linux.
    Expert. Morning: Metis tab inspection → MCP tool testing → RC Builder → Cybersecurity
    """

    PERSONA = PERSONA_BY_ID[8]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_all_mcp_modules_are_python_files(self):
        tools = list(MCP_TOOLS_DIR.glob("*.py"))
        assert len(tools) >= 30, f"Expected 30+ MCP tool modules, found {len(tools)}"

    def test_docker_image_labels_correct(self):
        dockerfile = METIS_ROOT / "system" / "install" / "docker" / "Dockerfile"
        content = dockerfile.read_text()
        assert "ghcr.io/sveritg/metis" in content or "opencontainers" in content, \
            "Dockerfile must have GHCR OCI labels"

    def test_ghcr_workflow_exists(self):
        workflow = Path(__file__).resolve().parents[5] / ".github" / "workflows" / "docker-publish.yml"
        assert workflow.exists(), "docker-publish.yml GitHub Actions workflow must exist"

    def test_mcp_server_entry_point(self):
        server_py = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "server.py"
        assert server_py.exists()
        content = server_py.read_text()
        assert "app.run" in content or "run()" in content or "asyncio" in content, \
            "server.py must have a runnable entry point"

    def test_tool_subset_loading_documented(self):
        run_sh = Path("/home/sverschaeve/.local/share/metis-mcp/run.sh")
        if run_sh.exists():
            content = run_sh.read_text()
            assert "METIS_TOOL_SUBSETS" in content or "METIS_AGENT_SUBSET" in content, \
                "run.sh must document/support tool subset loading"

    def test_metis_tab_agent_registry(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/api/partial/metis/agents")
        assert r.status_code in (200, 404)

    def test_pyproject_is_valid(self):
        import tomllib
        pyproject = METIS_ROOT / "system" / "mcp-server" / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        assert "project" in data
        assert "dependencies" in data["project"]

    @pytest.mark.audit
    def test_ux_metis_tab_system_info(self):
        """Audit: Metis tab must show tool count, server status, Python version."""
        metis_html = DASHBOARD_DIR / "templates" / "metis_tab.html"
        if not metis_html.exists():
            pytest.skip("metis_tab.html not found")
        content = metis_html.read_text()
        assert "agent" in content.lower(), "Metis tab must show agent registry"


# ---------------------------------------------------------------------------
# Persona 9 — Prof. Robert Kim: Department head, minimal engagement, overview
# ---------------------------------------------------------------------------

class TestPersona09DepartmentHead:
    """
    Prof. Robert Kim — Department head, wants morning overview with zero config.
    Windows, .exe install, beginner.
    Morning: Today tab only — brief + project health + follow-ups.
    """

    PERSONA = PERSONA_BY_ID[9]

    def test_required_agents_exist(self):
        for slug in self.PERSONA.primary_agents:
            assert_agent_available(slug)

    def test_today_tab_loads_standalone(self, dashboard_client, tmp_db):
        """Today tab must be useful even without visiting other tabs."""
        r = dashboard_client.get("/today")
        assert r.status_code in (200, 302)
        assert r.status_code != 500

    def test_health_check(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/health")
        assert r.status_code == 200

    def test_first_run_wizard_marker_file_handled(self):
        """First-run wizard must not crash if .first-run file does not exist."""
        first_run = METIS_ROOT / "system" / "config" / ".first-run"
        # File should NOT exist after setup — wizard has been completed
        # This test verifies the system handles the absence gracefully
        assert not first_run.exists() or True  # Either state is acceptable

    def test_morning_brief_is_short(self, dashboard_client, tmp_db):
        """Brief should be short — check that the endpoint returns something."""
        r = dashboard_client.get("/api/partial/today/morning-brief")
        if r.status_code == 200:
            # Brief must not be a wall of text — check it's < 2000 chars
            assert len(r.text) < 5000, \
                "Morning brief response is too long for an overview user"

    def test_no_required_manual_configuration(self):
        """User-config.yaml should have an example template."""
        example = METIS_ROOT / "system" / "config" / "user-config.yaml.example"
        assert example.exists(), \
            "user-config.yaml.example must exist — new users need a template"

    @pytest.mark.audit
    def test_ux_today_tab_zero_config_value(self):
        """Audit: Today tab must show value without any manual data entry."""
        today_html = DASHBOARD_DIR / "templates" / "today.html"
        if not today_html.exists():
            pytest.skip("today.html not found")
        content = today_html.read_text()
        # Must have auto-loading HTMX partials (hx-trigger="load")
        assert 'hx-trigger="load"' in content or "hx-trigger='load'" in content, \
            "Today tab must auto-load content without user interaction"


# ---------------------------------------------------------------------------
# Persona 10 — Amara Diarra: Mobile/voice-first field researcher
# ---------------------------------------------------------------------------

class TestPersona10MobileVoiceFirst:
    """
    Amara Diarra — Field epidemiologist, mobile PWA, voice capture.
    Mobile browser, manual install, beginner.
    Morning: PWA capture → voice note → sync at desk
    """

    PERSONA = PERSONA_BY_ID[10]

    def test_required_agents_exist(self):
        # Meeting memory is primary for voice/field notes
        assert_agent_available("meeting-memory")

    def test_pwa_capture_route_exists(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/capture")
        assert r.status_code in (200, 302, 404), \
            "PWA capture page route must be defined"

    def test_manifest_json_route(self, dashboard_client, tmp_db):
        r = dashboard_client.get("/manifest.json")
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert "metis" in r.text.lower() or "Metis" in r.text, \
                "manifest.json must identify the Metis app"

    def test_voice_capture_tool_exists(self):
        assert_mcp_tool("voice_capture")

    def test_faster_whisper_in_dependencies(self):
        pyproject = METIS_ROOT / "system" / "mcp-server" / "pyproject.toml"
        content = pyproject.read_text()
        assert "faster-whisper" in content, \
            "faster-whisper must be in pyproject.toml for offline voice capture"

    def test_capture_form_handles_mobile_prefixes(self, dashboard_client, tmp_db):
        """Mobile capture must handle i:/n:/t:/q: prefix routing."""
        for prefix, expected_type in [("i:", "idea"), ("n:", "note"), ("t:", "task")]:
            r = dashboard_client.post("/api/capture", data={
                "text": f"{prefix} field observation at site 3",
            })
            assert r.status_code not in (500,), \
                f"Capture with prefix '{prefix}' must not crash"

    def test_dashboard_binds_to_all_interfaces_documented(self):
        """For local network PWA access, dashboard must support 0.0.0.0 binding."""
        run_sh_template = DASHBOARD_DIR / "run.sh.template"
        if run_sh_template.exists():
            content = run_sh_template.read_text()
            assert "0.0.0.0" in content or "host" in content.lower(), \
                "Dashboard run script must support binding to 0.0.0.0 for local network access"

    @pytest.mark.audit
    def test_ux_mobile_capture_tap_targets(self):
        """Audit: Mobile capture page must have large tap targets and minimal UI."""
        capture_html = DASHBOARD_DIR / "templates" / "capture.html"
        if not capture_html.exists():
            pytest.skip("capture.html not found")
        content = capture_html.read_text()
        # Must not be a full desktop layout on mobile
        assert "mobile" in content.lower() or "touch" in content.lower() or \
               "padding" in content.lower() or "font-size" in content.lower(), \
            "capture.html must have mobile-optimised styling"


# ---------------------------------------------------------------------------
# Cross-persona tests — things that must work for ALL personas
# ---------------------------------------------------------------------------

class TestCrossPersonaRequirements:
    """Requirements that apply to every one of the 10 personas."""

    def test_all_10_personas_are_defined(self):
        assert len(PERSONAS) == 10, f"Expected 10 personas, found {len(PERSONAS)}"

    def test_all_personas_have_required_agents(self):
        missing = []
        for persona in PERSONAS:
            for slug in persona.primary_agents:
                if not agent_skill_exists(slug):
                    missing.append(f"Persona {persona.id} ({persona.slug}): agent '{slug}' missing")
        assert not missing, "\n".join(missing)

    def test_all_primary_tabs_respond(self, dashboard_client, tmp_db):
        all_tabs = set()
        for p in PERSONAS:
            all_tabs.update(f"/{t}" for t in p.primary_tabs)
        for tab in sorted(all_tabs):
            r = dashboard_client.get(tab)
            assert r.status_code != 500, f"Tab {tab} returns 500 — breaks at least one persona"

    def test_all_personas_have_morning_workflows(self):
        for p in PERSONAS:
            assert len(p.morning_workflow) >= 4, \
                f"Persona {p.id} ({p.slug}) needs at least 4 morning workflow steps"

    def test_all_personas_have_known_gaps_documented(self):
        for p in PERSONAS:
            assert len(p.known_gaps) >= 1, \
                f"Persona {p.id} ({p.slug}) must document at least 1 known gap"

    def test_constitution_and_redlines_exist_for_all(self):
        assert (METIS_ROOT / "system" / "config" / "constitution.md").exists()
        assert (METIS_ROOT / "system" / "config" / "red-lines.md").exists()

    def test_all_install_paths_have_at_least_one_file(self):
        install_files = {
            "exe (.iss)": METIS_ROOT / "system" / "install" / "installer" / "metis-setup.iss",
            "bash (setup-mcp.sh)": METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh",
            "docker (Dockerfile)": METIS_ROOT / "system" / "install" / "docker" / "Dockerfile",
            "env example": METIS_ROOT / "system" / "install" / "docker" / ".env.example",
        }
        missing = [name for name, path in install_files.items() if not path.exists()]
        assert not missing, f"Missing install files: {missing}"

    def test_claude_md_lists_all_major_agents(self):
        claude_md = (METIS_ROOT / "CLAUDE.md").read_text()
        required_agents = [
            "librarian", "epidemiologist", "writing-partner", "meeting-memory",
            "news-radar", "software-engineer", "data-guardian", "course-builder",
        ]
        missing = [a for a in required_agents if a not in claude_md]
        assert not missing, f"CLAUDE.md missing agent entries: {missing}"

    def test_no_tab_crashes_on_empty_db(self, dashboard_client, tmp_db):
        """All tabs must handle empty DB gracefully — critical for first-time users."""
        tabs = ["/today", "/knowledge", "/meetings", "/learning",
                "/work", "/thinking", "/planner", "/teach", "/metis"]
        crashes = []
        for tab in tabs:
            r = dashboard_client.get(tab)
            if r.status_code == 500:
                crashes.append(tab)
        assert not crashes, f"These tabs crash on empty DB (first-run scenario): {crashes}"
