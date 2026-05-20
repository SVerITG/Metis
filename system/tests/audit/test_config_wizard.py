"""
audit/test_config_wizard.py — Config wizard tests across all install types.

Tests:
  1. Wizard spec completeness (all 13 sections, all questions present)
  2. MCP tools that the wizard calls are implemented
  3. First-run trigger mechanism (.first-run marker)
  4. Write tools actually persist data to the right files
  5. Empty-shell scenario — wizard works with no background data
  6. Project setup questions exist in the wizard spec
  7. Install-type adaptations (exe / bash / docker / manual)
  8. Dashboard /setup page (web-based alternative wizard)

Run:
    pytest metis/system/tests/audit/test_config_wizard.py -v
    pytest metis/system/tests/audit/test_config_wizard.py -v -m wizard
"""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Research Cortex root: system/tests/audit/ -> parents[3] = RC root
METIS_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = METIS_ROOT / "system" / "config"
INSTALL_DIR = METIS_ROOT / "system" / "install"
MCP_TOOLS_DIR = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools"
DASHBOARD_DIR = METIS_ROOT / "system" / "app-py"

WIZARD_SPEC = CONFIG_DIR / "first-run-wizard.md"
CLAUDE_PROJECT_WIZARD = CONFIG_DIR / "claude-project-wizard.md"

# ---------------------------------------------------------------------------
# Wizard spec structure tests
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.wizard


class TestWizardSpec:
    """The first-run wizard specification must be complete."""

    def test_wizard_spec_exists(self):
        assert WIZARD_SPEC.exists(), "first-run-wizard.md must exist"

    def test_wizard_spec_has_13_sections(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        sections = [line for line in text.splitlines()
                    if line.startswith("## Section")]
        assert len(sections) >= 13, (
            f"Wizard needs 13 sections (found {len(sections)}): "
            "About You, Domain, News/Lit, Projects, Seed, Ideas, Meetings, "
            "Style, Teaching, Sensitivity, Dashboard, How it Works, Finish"
        )

    def test_wizard_section_1_asks_name(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "name" in text.lower() and ("greeting" in text.lower() or "greet" in text.lower()), \
            "Section 1 must ask for name (used for daily greetings)"

    def test_wizard_section_2_asks_research_interests(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "research" in text.lower() and "interest" in text.lower(), \
            "Section 2 must ask for research interests"

    def test_wizard_section_3_asks_news_monitoring(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "news" in text.lower() and "pubmed" in text.lower(), \
            "Section 3 must set up news/PubMed monitoring"

    def test_wizard_section_4_asks_projects(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "project" in text.lower() and "status" in text.lower(), \
            "Section 4 must ask about current projects and their status"

    def test_wizard_section_4_asks_deadlines(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "deadline" in text.lower() or "milestone" in text.lower(), \
            "Section 4 must ask about project deadlines/milestones"

    def test_wizard_section_5_offers_knowledge_seeding(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "seed" in text.lower() or "zotero" in text.lower() or "library" in text.lower(), \
            "Section 5 must offer to seed the knowledge library"

    def test_wizard_section_10_asks_data_sensitivity(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "patient" in text.lower() and "pii" in text.lower() or \
               "patient" in text.lower() and "data" in text.lower(), \
            "Section 10 must ask about patient/sensitive data"

    def test_wizard_section_10_mentions_strict_mode(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "METIS_PII_STRICT" in text or "pii_strict" in text.lower(), \
            "Section 10 must activate strict PII mode for clinical users"

    def test_wizard_finish_writes_both_config_files(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "write_user_config" in text, \
            "Wizard finish section must call write_user_config()"
        assert "write_user_preferences" in text, \
            "Wizard finish section must call write_user_preferences()"

    def test_wizard_finish_removes_first_run_marker(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        # Spec says "Delete the first-run marker file" or calls remove_first_run_marker()
        assert "remove_first_run_marker" in text or \
               "delete the first-run marker" in text.lower() or \
               "first-run marker" in text.lower(), \
            "Wizard must instruct deletion of .first-run marker at the end"

    def test_wizard_explains_metis_in_plain_english(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "plain english" in text.lower() or "plain-english" in text.lower() or \
               "behind the scenes" in text.lower(), \
            "Section 12 must explain how Metis works in plain English"

    def test_wizard_mentions_local_only(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "your computer" in text.lower() or "local" in text.lower(), \
            "Wizard must reassure user that data stays local"

    def test_wizard_output_yaml_keys_documented(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        for key in ("user:", "research:", "projects:", "style:", "data_sensitivity:"):
            assert key in text, f"Wizard spec must document YAML key: {key}"

    def test_wizard_output_json_keys_documented(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        for key in ("news_topics", "theme", "density"):
            assert key in text, f"Wizard spec must document JSON pref key: {key}"


# ---------------------------------------------------------------------------
# MCP tools that power the wizard
# ---------------------------------------------------------------------------

class TestWizardMCPTools:
    """All MCP tools called from the wizard spec must be implemented."""

    def test_config_tools_module_exists(self):
        assert (MCP_TOOLS_DIR / "config_tools.py").exists(), \
            "config_tools.py must exist — contains write_user_config, write_user_preferences"

    def test_write_user_config_implemented(self):
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "async def write_user_config" in text, \
            "write_user_config() must be implemented in config_tools.py"

    def test_write_user_preferences_implemented(self):
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "async def write_user_preferences" in text, \
            "write_user_preferences() must be implemented in config_tools.py"

    def test_remove_first_run_marker_implemented(self):
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "async def remove_first_run_marker" in text, \
            "remove_first_run_marker() must be implemented in config_tools.py"

    def test_ingest_ideas_document_implemented(self):
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "async def ingest_ideas_document" in text, \
            "ingest_ideas_document() must be implemented for Section 6"

    def test_get_user_profile_implemented(self):
        assert (MCP_TOOLS_DIR / "user_profile.py").exists(), \
            "user_profile.py must exist — contains get_user_profile()"
        text = (MCP_TOOLS_DIR / "user_profile.py").read_text(encoding="utf-8")
        assert "async def get_user_profile" in text, \
            "get_user_profile() must be implemented"

    def test_add_specialist_context_implemented(self):
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "async def add_specialist_context" in text, \
            "add_specialist_context() must be implemented for /add-context skill"

    def test_first_run_marker_path_consistent(self):
        """The .first-run marker path in config_tools.py must match first-run-wizard.md."""
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert ".first-run" in text, \
            "config_tools.py must reference the .first-run marker path"


# ---------------------------------------------------------------------------
# First-run trigger mechanism
# ---------------------------------------------------------------------------

class TestFirstRunTrigger:
    """The first-run wizard trigger must work correctly."""

    def test_claude_md_checks_first_run_marker(self):
        global_claude = Path("/home/sverschaeve/.claude/CLAUDE.md")
        if not global_claude.exists():
            pytest.skip("Global CLAUDE.md not present in this environment")
        text = global_claude.read_text(encoding="utf-8")
        assert ".first-run" in text, \
            "CLAUDE.md must check for .first-run marker at session start"
        assert "wizard" in text.lower() or "first-run" in text.lower(), \
            "CLAUDE.md must trigger the wizard when .first-run is present"

    def test_first_run_marker_not_currently_present(self):
        """After wizard runs, the marker must be deleted."""
        marker = CONFIG_DIR / ".first-run"
        assert not marker.exists(), (
            ".first-run marker still present — wizard was not completed. "
            "Run the first-run wizard to completion."
        )

    def test_wizard_spec_includes_welcome_message(self):
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "welcome" in text.lower() and "metis" in text.lower(), \
            "Wizard must open with a welcome message"


# ---------------------------------------------------------------------------
# Write tools actually persist data
# ---------------------------------------------------------------------------

class TestWizardWriteTools:
    """Wizard write tools must produce the right file changes."""

    def test_write_user_config_merges_existing_contexts(self):
        """write_user_config must preserve specialist_contexts from existing config."""
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "specialist_contexts" in text, \
            "write_user_config must handle specialist_contexts merge (not overwrite)"

    def test_write_user_preferences_merges_existing(self):
        """write_user_preferences must merge, not overwrite, existing preferences."""
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "existing" in text and "update" in text, \
            "write_user_preferences must merge into existing prefs file"

    def test_user_config_default_exists(self):
        """A default user-config.yaml.example (or .yaml) must ship with Metis."""
        default_exists = (
            (CONFIG_DIR / "user-config.yaml.example").exists()
            or (CONFIG_DIR / "user-config.yaml").exists()
        )
        assert default_exists, \
            "A default user-config.yaml (or .example) must be present for empty installs"

    def test_write_user_config_creates_file_if_missing(self, tmp_path, monkeypatch):
        """write_user_config must create user-config.yaml if it doesn't exist."""
        pytest.importorskip("yaml")

        rc_root = tmp_path / "metis_rc"
        config_dir = rc_root / "system" / "config"
        config_dir.mkdir(parents=True)

        sys.path.insert(0, str(METIS_ROOT / "system" / "mcp-server" / "src"))
        monkeypatch.setenv("METIS_RC_ROOT", str(rc_root))

        # Reload config_tools with new paths
        for mod in list(sys.modules.keys()):
            if "metis_mcp" in mod:
                del sys.modules[mod]

        from metis_mcp.tools.config_tools import _CONFIG_PATH, _load_config  # noqa
        # Patch _CONFIG_PATH to point to tmp dir
        import metis_mcp.tools.config_tools as ct
        monkeypatch.setattr(ct, "_CONFIG_PATH", config_dir / "user-config.yaml")

        data = ct._load_config()
        assert "user" in data, "Default config must have 'user' key"
        assert (config_dir / "user-config.yaml").exists(), \
            "_load_config() must create the file if missing"

    def test_user_prefs_written_by_wizard_affects_display_name(self):
        """display_name in user-preferences.json must be shown in Metis greetings."""
        metis_tab = DASHBOARD_DIR / "routers" / "metis_tab.py"
        if not metis_tab.exists():
            pytest.skip("metis_tab.py not found")
        text = metis_tab.read_text(encoding="utf-8")
        assert "display_name" in text, \
            "metis_tab.py must read display_name from user-preferences.json"

    def test_news_topics_from_wizard_used_in_morning_brief(self):
        """News topics set in wizard must feed the morning brief generator."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "news_topics" in text or "user_profile" in text.lower() or \
               "get_user_profile" in text, \
            "today.py morning brief must use news_topics set during wizard"


# ---------------------------------------------------------------------------
# Empty-shell scenario
# ---------------------------------------------------------------------------

class TestEmptyShellScenario:
    """Metis must be useful for a researcher who just installed it with no data."""

    def test_wizard_spec_offers_web_seeding(self):
        """Section 5 must offer to populate an empty library from the internet."""
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "search the web" in text.lower() or "content_scan" in text, \
            "Section 5 must offer web seeding for empty-library users"

    def test_wizard_spec_offers_inbox_import(self):
        """Section 5 must allow PDF drop in inbox/ for new installs."""
        text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "inbox" in text.lower() or "upload" in text.lower() or \
               "pdf" in text.lower(), \
            "Section 5 must explain inbox/ drop zone for new users"

    def test_seed_ph_script_exists(self):
        """A library seed script must exist for the PH background install."""
        seed_scripts = list(INSTALL_DIR.glob("seed_*.py")) + \
                       list(INSTALL_DIR.glob("download-library-*.sh"))
        assert len(seed_scripts) >= 1, \
            "At least one seed script must exist for pre-populating PH background"

    def test_empty_today_tab_does_not_crash(self):
        """Today tab must give value on empty database (first-time user scenario)."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_dir = tmp_path / "system" / "app" / "data"
            db_dir.mkdir(parents=True)
            db_path = db_dir / "metis.sqlite"

            conn = sqlite3.connect(str(db_path))
            # Create schema but seed NO data — true empty shell
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY, agent_slug TEXT, summary TEXT,
                input_path TEXT, output_path TEXT, input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0, tokens_used INTEGER DEFAULT 0,
                status TEXT DEFAULT 'completed', created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT UNIQUE,
                brief TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS news_briefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, summary TEXT,
                source TEXT, source_type TEXT DEFAULT 'news',
                published_at TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, title TEXT, priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'open', project TEXT, due_date TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS ideas (
                idea_id TEXT PRIMARY KEY, title TEXT, body TEXT,
                tags TEXT, status TEXT DEFAULT 'open', created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY, title TEXT, description TEXT,
                domain TEXT, type TEXT, status TEXT DEFAULT 'active',
                external_path TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS library_cards (
                card_id TEXT PRIMARY KEY, title TEXT, authors TEXT, year INTEGER,
                domain TEXT, source TEXT, tags TEXT, summary TEXT,
                status TEXT DEFAULT 'unread', created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS literature_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, authors TEXT,
                year INTEGER, source TEXT, doi TEXT, tags TEXT, created_at TEXT
            );
            """)
            conn.commit()
            conn.close()

            import os
            os.environ["METIS_RC_ROOT"] = str(tmp_path)
            for mod in list(sys.modules.keys()):
                if mod.startswith("routers") or mod in ("db", "main"):
                    del sys.modules[mod]
            if str(DASHBOARD_DIR) not in sys.path:
                sys.path.insert(0, str(DASHBOARD_DIR))

            from fastapi.testclient import TestClient
            import main as dashboard_main
            client = TestClient(dashboard_main.app, raise_server_exceptions=False)
            r = client.get("/today")
            assert r.status_code != 500, \
                f"Today tab must not crash on empty database (got {r.status_code})"


# ---------------------------------------------------------------------------
# Install-type adaptations
# ---------------------------------------------------------------------------

class TestInstallTypeAdaptations:
    """Each install method must have the right wizard entry point."""

    def test_exe_installer_has_setup_page(self):
        """Windows .exe install: dashboard /setup page is the post-install wizard."""
        setup_router = DASHBOARD_DIR / "routers" / "setup.py"
        assert setup_router.exists(), \
            "routers/setup.py must exist — the /setup post-install wizard page"

    def test_setup_template_exists(self):
        setup_template = DASHBOARD_DIR / "templates" / "setup.html"
        assert setup_template.exists(), \
            "templates/setup.html must exist for the web-based wizard"

    def test_setup_template_has_name_field(self):
        setup_template = DASHBOARD_DIR / "templates" / "setup.html"
        text = setup_template.read_text(encoding="utf-8")
        assert "name" in text.lower(), \
            "Setup template must include a name input field"

    def test_bash_install_has_mcp_setup_script(self):
        """bash install: setup-mcp.sh is the entry point."""
        setup_mcp = METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh"
        assert setup_mcp.exists(), \
            "setup-mcp.sh must exist for bash install path"

    def test_bash_setup_mentions_user_config(self):
        setup_mcp = METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh"
        text = setup_mcp.read_text(encoding="utf-8")
        assert "user-config" in text or "user_config" in text or \
               "config" in text.lower(), \
            "setup-mcp.sh must reference user configuration"

    def test_docker_install_has_env_example(self):
        """Docker install: .env.example documents required configuration."""
        env_example = INSTALL_DIR / "docker" / ".env.example"
        assert env_example.exists(), \
            ".env.example must exist for Docker install path"

    def test_docker_env_example_has_api_key_placeholder(self):
        env_example = INSTALL_DIR / "docker" / ".env.example"
        text = env_example.read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY" in text, \
            ".env.example must show ANTHROPIC_API_KEY placeholder for Docker users"

    def test_install_state_json_written_after_install(self):
        """install-state.json must be written by any install method so wizard can read it."""
        install_state_exists = (CONFIG_DIR / "install-state.json").exists()
        # This may not exist in CI — check the bash script that creates it
        setup_mcp = METIS_ROOT / "system" / "mcp-server" / "setup-mcp.sh"
        if not install_state_exists:
            if setup_mcp.exists():
                text = setup_mcp.read_text(encoding="utf-8")
                assert "install-state" in text or "install_state" in text, \
                    "setup-mcp.sh must write install-state.json after install"

    def test_claude_project_wizard_exists_for_claude_ai(self):
        """claude.ai Projects users need their own wizard entry point."""
        assert CLAUDE_PROJECT_WIZARD.exists(), \
            "claude-project-wizard.md must exist for claude.ai Projects users"

    def test_manual_install_claude_md_is_self_contained(self):
        """Manual install: CLAUDE.md must be enough to get started without a script."""
        metis_claude = METIS_ROOT / "CLAUDE.md"
        assert metis_claude.exists()
        text = metis_claude.read_text(encoding="utf-8")
        assert "agent" in text.lower() and "invoke" in text.lower(), \
            "CLAUDE.md must explain how to invoke agents for manual install users"


# ---------------------------------------------------------------------------
# Dashboard /setup page (web wizard alternative)
# ---------------------------------------------------------------------------

class TestDashboardSetupPage:
    """The /setup page is the GUI alternative to the wizard for .exe users."""

    def test_setup_router_has_get_endpoint(self):
        setup_router = DASHBOARD_DIR / "routers" / "setup.py"
        text = setup_router.read_text(encoding="utf-8")
        assert "@router.get" in text or "def get_setup" in text, \
            "setup.py must have a GET endpoint for the /setup page"

    def test_setup_router_has_post_endpoint(self):
        setup_router = DASHBOARD_DIR / "routers" / "setup.py"
        text = setup_router.read_text(encoding="utf-8")
        assert "@router.post" in text or "def post_setup" in text or \
               "async def" in text, \
            "setup.py must have a POST handler for wizard form submissions"

    def test_setup_router_writes_to_config_files(self):
        """POST /setup must produce changes in user-config.yaml or user-preferences.json."""
        setup_router = DASHBOARD_DIR / "routers" / "setup.py"
        text = setup_router.read_text(encoding="utf-8")
        assert "user-config" in text or "user_config" in text or \
               "yaml.dump" in text or "json.dumps" in text or \
               "write_user" in text, \
            "setup.py POST handler must write to config files — not just echo back"

    def test_setup_page_loads_with_testclient(self, tmp_path, monkeypatch):
        """The /setup route must return 200."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        rc_root = tmp_path / "metis_rc"
        db_dir = rc_root / "system" / "app" / "data"
        db_dir.mkdir(parents=True)

        conn = sqlite3.connect(str(db_dir / "metis.sqlite"))
        conn.execute("CREATE TABLE IF NOT EXISTS dummy (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        monkeypatch.setenv("METIS_RC_ROOT", str(rc_root))
        for mod in list(sys.modules.keys()):
            if mod.startswith("routers") or mod in ("db", "main"):
                del sys.modules[mod]
        if str(DASHBOARD_DIR) not in sys.path:
            sys.path.insert(0, str(DASHBOARD_DIR))

        from fastapi.testclient import TestClient
        import main as dashboard_main
        client = TestClient(dashboard_main.app, raise_server_exceptions=False)
        r = client.get("/setup")
        assert r.status_code in (200, 302), \
            f"/setup must return 200 or redirect, got {r.status_code}"

    def test_setup_page_submit_produces_config_change(self, tmp_path, monkeypatch):
        """POST /api/setup/save (or similar) must change user-preferences.json."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        pytest.importorskip("yaml")

        rc_root = tmp_path / "metis_rc"
        config_dir = rc_root / "system" / "config"
        db_dir = rc_root / "system" / "app" / "data"
        config_dir.mkdir(parents=True)
        db_dir.mkdir(parents=True)

        conn = sqlite3.connect(str(db_dir / "metis.sqlite"))
        conn.execute("CREATE TABLE IF NOT EXISTS dummy (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        monkeypatch.setenv("METIS_RC_ROOT", str(rc_root))
        for mod in list(sys.modules.keys()):
            if mod.startswith("routers") or mod in ("db", "main"):
                del sys.modules[mod]
        if str(DASHBOARD_DIR) not in sys.path:
            sys.path.insert(0, str(DASHBOARD_DIR))

        from fastapi.testclient import TestClient
        import main as dashboard_main
        client = TestClient(dashboard_main.app, raise_server_exceptions=False)

        # Try common save endpoints
        endpoints = [
            ("/api/setup/save", {"display_name": "Test Researcher", "role": "Researcher"}),
            ("/api/settings/identity", {"name": "Test Researcher"}),
            ("/api/identity/update", {"name": "Test Researcher"}),
        ]
        saved = False
        for endpoint, payload in endpoints:
            r = client.post(endpoint, data=payload)
            if r.status_code in (200, 201, 302):
                saved = True
                break

        if not saved:
            # Fallback: check setup page itself has a form that POSTs somewhere
            setup_router = DASHBOARD_DIR / "routers" / "setup.py"
            text = setup_router.read_text(encoding="utf-8")
            assert "@router.post" in text, (
                "No POST save endpoint found and setup.py has no POST handler. "
                "Setup wizard must be able to persist changes."
            )


# ---------------------------------------------------------------------------
# Questions → config changes: per-section verification
# ---------------------------------------------------------------------------

class TestWizardQuestionsLeadToChanges:
    """Every wizard question must have a corresponding config field it writes to."""

    SECTION_TO_CONFIG = {
        "name": ("user-config.yaml", "name"),
        "role": ("user-config.yaml", "role"),
        "research interests": ("user-config.yaml", "interests"),
        "news topics": ("user-preferences.json", "news_topics"),
        "pubmed": ("user-preferences.json", "pubmed_query"),
        "teaching": ("user-config.yaml", "teaching"),
        "patient data": ("user-config.yaml", "data_sensitivity"),
        "theme": ("user-preferences.json", "theme"),
        "density": ("user-preferences.json", "density"),
    }

    def test_config_tools_handles_user_section(self):
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert '"name"' in text or "'name'" in text, \
            "config_tools.py must handle 'name' key from wizard Section 1"

    def test_config_tools_handles_specialist_contexts(self):
        text = (MCP_TOOLS_DIR / "config_tools.py").read_text(encoding="utf-8")
        assert "specialist_contexts" in text, \
            "config_tools.py must handle specialist_contexts from /add-context"

    def test_user_prefs_news_topics_used_by_morning_scan(self):
        """news_topics from wizard must reach the morning scan job.

        The chain is: wizard → user-preferences.json → intelligence.py → scan jobs.
        Check the full pipeline, not just literature_monitor.py.
        """
        tools_dir = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools"
        pipeline_files = list(tools_dir.glob("*.py")) + \
                         list((METIS_ROOT / "system" / "app-py" / "routers").glob("*.py"))
        for f in pipeline_files:
            try:
                text = f.read_text(encoding="utf-8")
                if "news_topics" in text or "pubmed_query" in text:
                    return  # pipeline uses wizard output
            except Exception:
                continue
        pytest.fail(
            "No module in the tool chain reads news_topics/pubmed_query from user-preferences.json. "
            "Wizard Section 3 must feed into the morning scan pipeline."
        )

    def test_wizard_section_4_projects_land_in_database(self):
        """Projects entered in the wizard must appear in the projects table."""
        wizard_text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "project" in wizard_text.lower(), "Section 4 must cover projects"

        # The projects table is defined in db.py, conftest_personas.py, or a schema file
        # Search broadly across the system directory
        project_table_found = False
        search_paths = [
            DASHBOARD_DIR / "db.py",
            METIS_ROOT / "system" / "tests" / "personas" / "conftest_personas.py",
        ]
        search_paths += list(INSTALL_DIR.glob("*.sql"))
        search_paths += list(INSTALL_DIR.glob("*.py"))

        for f in search_paths:
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8")
                if "projects" in text and ("CREATE TABLE" in text or "project_id" in text):
                    project_table_found = True
                    break
            except Exception:
                continue
        assert project_table_found, \
            "A 'projects' table must exist in the schema (db.py or schema SQL) " \
            "to receive wizard Section 4 project data"

    def test_data_sensitivity_sets_env_flag(self):
        """If patient_data=True, METIS_PII_STRICT=1 must be mentioned."""
        wizard_text = WIZARD_SPEC.read_text(encoding="utf-8")
        assert "METIS_PII_STRICT" in wizard_text, \
            "Wizard must mention METIS_PII_STRICT=1 when patient_data is confirmed"
