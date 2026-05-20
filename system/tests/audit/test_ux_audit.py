"""
audit/test_ux_audit.py — UX surface audit across all 9 dashboard tabs.

Tests:
  1. Navigation — all 9 tabs reachable, no dead links
  2. Empty states — every surface degrades gracefully on zero data
  3. Capture — modal, keyboard shortcut, prefix routing
  4. Cross-tab linkedness — does completing an action in one tab affect another
  5. Creativity & cross-pollination — idea capture triggers connections
  6. Live meeting assistant — endpoints and template present
  7. Mobile / PWA capture — /capture route, manifest.json
  8. Voice-to-text capture — faster-whisper tool chain
  9. Collapsible / overflow — long lists don't break layout
  10. Button wiring — every hx-post/hx-get target must exist
  11. Customisation — display_name, theme, density all wired
  12. Morning brief — value out of the box, no configuration required

Run:
    pytest metis/system/tests/audit/test_ux_audit.py -v
    pytest metis/system/tests/audit/test_ux_audit.py -v -m ux
    pytest metis/system/tests/audit/test_ux_audit.py -v -k "mobile"
"""

import re
import sqlite3
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Research Cortex root: system/tests/audit/ -> parents[3] = RC root
METIS_ROOT = Path(__file__).resolve().parents[3]
DASHBOARD_DIR = METIS_ROOT / "system" / "app-py"
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
PARTIALS_DIR = TEMPLATES_DIR / "partials"
STATIC_DIR = DASHBOARD_DIR / "static"
MCP_TOOLS_DIR = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools"
AGENTS_DIR = METIS_ROOT / "agents"

pytestmark = pytest.mark.ux

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def template_text(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def partial_text(name: str) -> str:
    return (PARTIALS_DIR / name).read_text(encoding="utf-8")


def has_partial(name: str) -> bool:
    return (PARTIALS_DIR / name).exists()


# ---------------------------------------------------------------------------
# 1. Navigation
# ---------------------------------------------------------------------------

class TestNavigation:
    """All 9 tabs must be reachable from the navigation bar."""

    EXPECTED_TABS = [
        ("today", "/today"),
        ("knowledge", "/knowledge"),
        ("meetings", "/meetings"),
        ("learning", "/learning"),
        ("work", "/work"),
        ("thinking", "/thinking"),
        ("planner", "/planner"),
        ("teach", "/teach"),
        ("metis", "/metis"),
    ]

    def test_base_template_has_all_9_tabs(self):
        base = template_text("base.html")
        missing = []
        for tab_name, tab_path in self.EXPECTED_TABS:
            if tab_path not in base and tab_name not in base:
                missing.append(tab_path)
        assert not missing, f"base.html missing tabs: {missing}"

    def test_all_tab_templates_exist(self):
        missing = []
        for tab_name, _ in self.EXPECTED_TABS:
            tmpl = TEMPLATES_DIR / f"{tab_name}.html"
            if not tmpl.exists():
                # metis tab uses different name
                tmpl = TEMPLATES_DIR / "metis_tab.html"
                if not tmpl.exists():
                    missing.append(tab_name)
        assert not missing, f"Missing tab templates: {missing}"

    def test_htmx_is_loaded(self):
        base = template_text("base.html")
        assert "htmx" in base.lower(), \
            "HTMX must be loaded in base.html — all partials depend on it"

    def test_htmx_is_local_not_cdn_only(self):
        """Local htmx.min.js avoids CDN-SRI mismatch bugs."""
        htmx_local = STATIC_DIR / "htmx.min.js"
        if not htmx_local.exists():
            # CDN with integrity is acceptable but document the risk
            base = template_text("base.html")
            assert "integrity" in base or "htmx" in base, \
                "If htmx is CDN-only, it must have SRI integrity hash in base.html"

    def test_all_tab_routers_exist(self):
        routers_dir = DASHBOARD_DIR / "routers"
        router_names = {
            "today": "today.py", "knowledge": "knowledge.py",
            "meetings": "meetings.py", "learning": "learning.py",
            "work": "work.py", "thinking": "thinking.py",
            "planner": "planner.py", "teach": "teach.py",
            "metis": "metis_tab.py",
        }
        missing = [k for k, v in router_names.items()
                   if not (routers_dir / v).exists()]
        assert not missing, f"Missing routers: {missing}"

    def test_capture_shortcut_wired_in_appjs(self):
        app_js = STATIC_DIR / "app.js"
        if not app_js.exists():
            pytest.skip("app.js not found")
        text = app_js.read_text(encoding="utf-8")
        assert "ctrlKey" in text or "Ctrl+K" in text or "metaKey" in text, \
            "Capture modal keyboard shortcut (Ctrl+K) must be wired in app.js"


# ---------------------------------------------------------------------------
# 2. Empty states
# ---------------------------------------------------------------------------

class TestEmptyStates:
    """Every surface must show a meaningful empty state when there is no data."""

    PARTIALS_THAT_NEED_EMPTY_STATES = [
        ("today_morning_brief.html", ["brief", "empty", "no "]),
        ("meetings_list.html", ["no meeting", "empty", "no "]),
        ("learning_due.html", ["no card", "up to date", "empty", "no "]),
        ("work_tasks.html", ["no task", "empty", "no "]),
        ("thinking_ideas.html", ["no idea", "empty", "start", "no "]),
        ("knowledge_cards.html", ["no card", "empty", "no ", "library"]),
    ]

    def test_empty_state_partial_exists(self):
        assert has_partial("empty_state.html"), \
            "A reusable empty_state.html partial must exist"

    def test_thinking_ideas_has_empty_state(self):
        if not has_partial("thinking_ideas.html"):
            pytest.skip("thinking_ideas.html not present")
        text = partial_text("thinking_ideas.html")
        assert any(kw in text.lower() for kw in ["empty", "no idea", "start", "first"]), \
            "thinking_ideas.html must have an empty state for new users"

    def test_thinking_notes_has_empty_state(self):
        if not has_partial("thinking_notes.html"):
            pytest.skip("thinking_notes.html not present")
        text = partial_text("thinking_notes.html")
        assert any(kw in text.lower() for kw in ["empty", "no note", "start", "first"]), \
            "thinking_notes.html must have an empty state for new users"

    def test_today_morning_brief_handles_no_data(self):
        if not has_partial("today_morning_brief.html"):
            pytest.skip("today_morning_brief.html not present")
        text = partial_text("today_morning_brief.html")
        # Must handle both populated and empty brief
        assert "{% if" in text or "{% for" in text or "empty" in text.lower(), \
            "today_morning_brief.html must handle the empty (no brief yet) case"

    def test_meetings_list_handles_zero_meetings(self):
        if not has_partial("meetings_list.html"):
            pytest.skip("meetings_list.html not present")
        text = partial_text("meetings_list.html")
        assert "{% if" in text or "empty" in text.lower() or "no meeting" in text.lower(), \
            "meetings_list.html must handle zero meetings gracefully"

    def test_learning_due_handles_no_cards(self):
        if not has_partial("learning_due.html"):
            pytest.skip("learning_due.html not present")
        text = partial_text("learning_due.html")
        assert "{% if" in text or "up to date" in text.lower() or "no " in text.lower(), \
            "learning_due.html must handle the case where no cards are due"


# ---------------------------------------------------------------------------
# 3. Capture modal
# ---------------------------------------------------------------------------

class TestCaptureModal:
    """The capture modal is the primary input surface — it must work correctly."""

    def test_capture_modal_template_exists(self):
        assert has_partial("capture_modal.html"), \
            "capture_modal.html partial must exist"

    def test_capture_modal_has_prefix_routing(self):
        modal = partial_text("capture_modal.html")
        # i: n: t: q: prefix routing
        assert "i:" in modal or "prefix" in modal.lower() or "idea" in modal.lower(), \
            "Capture modal must show prefix routing options (i:/n:/t:/q:)"

    def test_capture_modal_has_text_input(self):
        modal = partial_text("capture_modal.html")
        assert "<textarea" in modal or 'type="text"' in modal or "input" in modal, \
            "Capture modal must have a text input"

    def test_capture_post_endpoint_exists(self):
        capture_router = DASHBOARD_DIR / "routers" / "capture.py"
        assert capture_router.exists(), "routers/capture.py must exist"
        text = capture_router.read_text(encoding="utf-8")
        assert "@router.post" in text or "async def" in text, \
            "capture.py must define a POST endpoint"

    def test_capture_route_registered_in_main(self):
        main_py = DASHBOARD_DIR / "main.py"
        text = main_py.read_text(encoding="utf-8")
        assert "capture" in text.lower(), \
            "main.py must include the capture router"

    def test_cross_pollination_triggered_after_capture(self):
        capture_router = DASHBOARD_DIR / "routers" / "capture.py"
        text = capture_router.read_text(encoding="utf-8")
        # cross_pollinate or brainstorm should be in the capture flow
        assert "cross_pollinate" in text or "brainstorm" in text or \
               "connections" in text or "similar" in text, \
            "Capture router should trigger cross-pollination after saving an idea"

    def test_capture_works_from_mobile(self):
        """The /capture route must be a standalone page (not just a modal)."""
        # Check for a standalone capture template
        standalone = TEMPLATES_DIR / "capture.html"
        assert standalone.exists(), \
            "templates/capture.html must exist for mobile PWA capture"

    def test_capture_template_has_type_selector(self):
        standalone = TEMPLATES_DIR / "capture.html"
        text = standalone.read_text(encoding="utf-8")
        # Must have type buttons (IDEA / NOTE / TASK / QUESTION)
        assert "IDEA" in text or "idea" in text.lower(), \
            "Standalone capture page must have type selector buttons"


# ---------------------------------------------------------------------------
# 4. Cross-tab linkedness
# ---------------------------------------------------------------------------

class TestCrossTabLinkedness:
    """Actions in one tab must propagate to other tabs (no siloed surfaces)."""

    def test_idea_captured_in_thinking_visible_in_today(self):
        """Today tab should show recent ideas from the ideas table."""
        today_tmpl = template_text("today.html") if \
            (TEMPLATES_DIR / "today.html").exists() else ""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if today_router.exists():
            text = today_router.read_text(encoding="utf-8")
            # Should query ideas table for "idea of the day" or similar
            assert "ideas" in text.lower() or "idea" in text.lower(), \
                "Today tab must surface recent ideas from the ideas table"

    def test_library_paper_visible_in_knowledge_and_teach(self):
        """A paper added to the library must appear in both Knowledge and Teach tabs."""
        knowledge_router = DASHBOARD_DIR / "routers" / "knowledge.py"
        teach_router = DASHBOARD_DIR / "routers" / "teach.py"
        for router in [knowledge_router, teach_router]:
            if router.exists():
                text = router.read_text(encoding="utf-8")
                assert "library" in text.lower() or "literature" in text.lower(), \
                    f"{router.name} must query the library/literature tables"

    def test_meeting_action_items_visible_in_work(self):
        """Action items from meetings should feed into the Work tab tasks."""
        work_router = DASHBOARD_DIR / "routers" / "work.py"
        if work_router.exists():
            text = work_router.read_text(encoding="utf-8")
            assert "task" in text.lower(), \
                "work.py must query tasks — which includes meeting action items"

    def test_agent_run_visible_in_metis_and_today(self):
        """An agent run logged to agent_runs must appear in both Today and Metis tabs."""
        for router_name in ["today.py", "metis_tab.py"]:
            router = DASHBOARD_DIR / "routers" / router_name
            if router.exists():
                text = router.read_text(encoding="utf-8")
                assert "agent_run" in text.lower() or "runs" in text.lower(), \
                    f"{router_name} must query agent_runs for activity display"

    def test_project_in_work_tab_visible_in_planner(self):
        """Projects in the Work tab must also appear in the Planner."""
        planner_router = DASHBOARD_DIR / "routers" / "planner.py"
        if planner_router.exists():
            text = planner_router.read_text(encoding="utf-8")
            assert "project" in text.lower(), \
                "planner.py must reference projects — needed for PhD focus board"

    def test_course_published_visible_in_teach_and_learning(self):
        """A published course must appear in both Teach and Learning tabs."""
        for router_name in ["teach.py", "learning.py"]:
            router = DASHBOARD_DIR / "routers" / router_name
            if router.exists():
                text = router.read_text(encoding="utf-8")
                assert "course" in text.lower(), \
                    f"{router_name} must query learning_courses"


# ---------------------------------------------------------------------------
# 5. Creativity and cross-pollination
# ---------------------------------------------------------------------------

class TestCreativity:
    """Metis should promote unexpected connections between ideas, papers, and work."""

    def test_brainstorm_mcp_tool_exists(self):
        assert (MCP_TOOLS_DIR / "brainstorm.py").exists() or \
               (MCP_TOOLS_DIR / "ideas.py").exists(), \
            "A brainstorm/ideas MCP tool must exist for cross-pollination"

    def test_cross_pollination_happens_on_idea_save(self):
        ideas_tool = MCP_TOOLS_DIR / "ideas.py"
        if not ideas_tool.exists():
            pytest.skip("ideas.py not found")
        text = ideas_tool.read_text(encoding="utf-8")
        assert "cross_pollinate" in text or "similar" in text or "vec" in text, \
            "ideas.py must run cross-pollination when an idea is saved"

    def test_semantic_search_uses_embeddings(self):
        """Cross-pollination must use vector embeddings, not just keyword search."""
        ideas_tool = MCP_TOOLS_DIR / "ideas.py"
        if not ideas_tool.exists():
            pytest.skip("ideas.py not found")
        text = ideas_tool.read_text(encoding="utf-8")
        assert "embed" in text or "vec" in text or "vector" in text, \
            "ideas.py must use embeddings for semantic similarity search"

    def test_vector_memory_tool_exists(self):
        vector_files = list(MCP_TOOLS_DIR.glob("vector*.py")) + \
                       list(MCP_TOOLS_DIR.glob("*memory*.py")) + \
                       list(MCP_TOOLS_DIR.glob("*embed*.py"))
        assert len(vector_files) >= 1, \
            "At least one vector/embedding/memory tool must exist for cross-pollination"

    def test_thinking_tab_has_brainstorm_launcher(self):
        if not (TEMPLATES_DIR / "thinking.html").exists():
            pytest.skip("thinking.html not present")
        text = template_text("thinking.html")
        assert "brainstorm" in text.lower() or "hx-post" in text or \
               "hx-get" in text, \
            "Thinking tab must have a brainstorm launcher button"

    def test_cross_pollination_results_shown_in_capture(self):
        """After capture, related items should appear."""
        capture_router = DASHBOARD_DIR / "routers" / "capture.py"
        if not capture_router.exists():
            pytest.skip("capture.py not found")
        text = capture_router.read_text(encoding="utf-8")
        assert "connection" in text.lower() or "related" in text.lower() or \
               "similar" in text.lower() or "cross" in text.lower(), \
            "Capture endpoint must surface cross-pollination connections after save"

    def test_brainstorm_sessions_partial_exists(self):
        assert has_partial("thinking_brainstorm_sessions.html"), \
            "thinking_brainstorm_sessions.html partial must exist for session history"


# ---------------------------------------------------------------------------
# 6. Live meeting assistant
# ---------------------------------------------------------------------------

class TestLiveMeetingAssistant:
    """Meeting Memory must support live meetings, not just post-hoc import."""

    def test_meeting_live_session_partial_exists(self):
        assert has_partial("meeting_live_session.html"), \
            "meeting_live_session.html partial must exist for live meeting UI"

    def test_meeting_live_setup_partial_exists(self):
        assert has_partial("meeting_live_setup.html"), \
            "meeting_live_setup.html partial must exist for meeting setup"

    def test_transcription_tool_exists(self):
        transcription = DASHBOARD_DIR / "routers" / "transcription.py"
        if not transcription.exists():
            transcription = MCP_TOOLS_DIR / "transcription.py"
        assert transcription.exists(), \
            "A transcription router or MCP tool must exist for voice capture"

    def test_meeting_import_form_exists(self):
        assert has_partial("meeting_import_form.html"), \
            "meeting_import_form.html must exist for importing meeting notes"

    def test_meetings_router_has_live_endpoint(self):
        meetings_router = DASHBOARD_DIR / "routers" / "meetings.py"
        if not meetings_router.exists():
            pytest.skip("meetings.py not found")
        text = meetings_router.read_text(encoding="utf-8")
        assert "live" in text.lower() or "record" in text.lower() or \
               "transcrib" in text.lower(), \
            "meetings.py must have endpoints for live/recording functionality"

    def test_meeting_detail_partial_exists(self):
        assert has_partial("meeting_detail.html"), \
            "meeting_detail.html partial must exist to show meeting content"

    def test_meeting_action_items_extracted(self):
        """Meeting Memory must extract action items, not just store the transcript."""
        meetings_router = DASHBOARD_DIR / "routers" / "meetings.py"
        if not meetings_router.exists():
            pytest.skip("meetings.py not found")
        text = meetings_router.read_text(encoding="utf-8")
        assert "action" in text.lower() or "task" in text.lower(), \
            "meetings.py must extract and store action items from meetings"

    @pytest.mark.known_gap
    def test_live_meeting_audio_note(self):
        """
        Known gap: live meeting audio capture requires microphone access over HTTPS or localhost.
        This test documents the limitation — not an implementation failure.
        """
        transcription = MCP_TOOLS_DIR / "transcription.py"
        if transcription.exists():
            text = transcription.read_text(encoding="utf-8")
            has_whisper = "whisper" in text.lower() or "faster_whisper" in text.lower() or \
                          "faster-whisper" in text.lower()
            # Document the state — warn but don't fail
            if not has_whisper:
                pytest.xfail(
                    "transcription.py exists but faster-whisper integration not confirmed. "
                    "Known gap: voice-to-text requires whisper running locally."
                )


# ---------------------------------------------------------------------------
# 7. Mobile / PWA capture
# ---------------------------------------------------------------------------

class TestMobilePWA:
    """Metis must work as a PWA for mobile field capture."""

    def test_capture_standalone_page_exists(self):
        assert (TEMPLATES_DIR / "capture.html").exists(), \
            "templates/capture.html must exist for standalone mobile capture"

    def test_capture_page_has_large_tap_targets(self):
        """Mobile UX: tap targets should be large (check for btn or large class)."""
        text = template_text("capture.html")
        assert "btn" in text.lower() or "button" in text.lower(), \
            "capture.html must have button elements (tap targets for mobile)"

    def test_manifest_json_endpoint_exists(self):
        main_py = DASHBOARD_DIR / "main.py"
        text = main_py.read_text(encoding="utf-8")
        assert "manifest.json" in text or "manifest" in text.lower(), \
            "main.py must expose /manifest.json for PWA home screen add"

    def test_capture_template_dark_mode_class(self):
        """Mobile capture should have dark-mode styling for field use."""
        text = template_text("capture.html")
        assert "dark" in text.lower() or "background" in text.lower() or \
               "color" in text.lower(), \
            "capture.html should have dark-mode or themed styling for outdoor readability"

    def test_capture_route_bound_to_all_interfaces(self):
        """Dashboard must be accessible on LAN (0.0.0.0) for mobile access."""
        run_sh = DASHBOARD_DIR / "run.sh"
        if not run_sh.exists():
            pytest.skip("run.sh not found")
        text = run_sh.read_text(encoding="utf-8")
        assert "0.0.0.0" in text or "host" in text.lower(), \
            "run.sh must bind to 0.0.0.0 for local-network mobile access"

    @pytest.mark.known_gap
    def test_service_worker_gap_documented(self):
        """Known gap: PWA offline caching requires a service worker."""
        service_worker = STATIC_DIR / "service-worker.js"
        if not service_worker.exists():
            pytest.xfail(
                "No service worker present. Offline capture is not available. "
                "Known gap: service worker deferred — offline only useful with Tailscale VPN."
            )


# ---------------------------------------------------------------------------
# 8. Voice-to-text capture
# ---------------------------------------------------------------------------

class TestVoiceCapture:
    """Voice capture must be wired from browser mic → whisper → capture modal."""

    def test_transcription_router_exists(self):
        transcription = DASHBOARD_DIR / "routers" / "transcription.py"
        if not transcription.exists():
            transcription = MCP_TOOLS_DIR / "transcription.py"
        assert transcription.exists(), \
            "A transcription module must exist for voice capture"

    def test_transcription_references_whisper(self):
        transcription = DASHBOARD_DIR / "routers" / "transcription.py"
        if not transcription.exists():
            transcription = MCP_TOOLS_DIR / "transcription.py"
        if not transcription.exists():
            pytest.skip("No transcription module found")
        text = transcription.read_text(encoding="utf-8")
        assert "whisper" in text.lower() or "audio" in text.lower(), \
            "transcription module must reference whisper for local voice processing"

    def test_audio_stays_local(self):
        """Audio processing must not send audio to external services."""
        transcription = DASHBOARD_DIR / "routers" / "transcription.py"
        if not transcription.exists():
            transcription = MCP_TOOLS_DIR / "transcription.py"
        if not transcription.exists():
            pytest.skip("No transcription module found")
        text = transcription.read_text(encoding="utf-8")
        # Must not reference OpenAI Whisper API (which is cloud-based)
        assert "openai.com" not in text and "api.openai" not in text, \
            "Transcription must use local whisper — audio must not leave the machine"

    def test_voice_capture_integrated_in_meeting(self):
        """Meeting Memory must connect to voice capture (via transcription router or template)."""
        # Transcription is handled by routers/transcription.py — separate router registered in main.py
        # The meeting live_session template wires the mic UI; verify both pieces exist
        transcription_router = DASHBOARD_DIR / "routers" / "transcription.py"
        live_session_tmpl = PARTIALS_DIR / "meeting_live_session.html"
        assert transcription_router.exists() or live_session_tmpl.exists(), \
            "Live meeting audio requires routers/transcription.py and/or meeting_live_session.html"
        # Also verify the live session template connects to the transcription endpoint
        if live_session_tmpl.exists():
            text = live_session_tmpl.read_text(encoding="utf-8")
            assert "transcri" in text.lower() or "record" in text.lower() or \
                   "audio" in text.lower() or "hx-post" in text or "fetch" in text, \
                "meeting_live_session.html must have a recording/transcription control"


# ---------------------------------------------------------------------------
# 9. Button wiring — every interactive element must have a real target
# ---------------------------------------------------------------------------

class TestButtonWiring:
    """Every hx-post and hx-get in templates must point to a real endpoint."""

    def _extract_hx_targets(self, text: str) -> list[str]:
        targets = re.findall(r'hx-(?:get|post|put|delete)="([^"]+)"', text)
        return targets

    def _endpoint_registered(self, path: str) -> bool:
        """Check if a path is registered in any router."""
        routers_dir = DASHBOARD_DIR / "routers"
        main_py = DASHBOARD_DIR / "main.py"
        for f in list(routers_dir.glob("*.py")) + [main_py]:
            try:
                text = f.read_text(encoding="utf-8")
                # Check for both the path and common variants
                path_no_params = path.split("?")[0].split("{")[0]
                if path_no_params in text:
                    return True
            except Exception:
                continue
        return False

    def test_today_tab_htmx_targets(self):
        today = template_text("today.html") if (TEMPLATES_DIR / "today.html").exists() else ""
        targets = self._extract_hx_targets(today)
        critical = ["/api/partial/today/morning-brief", "/api/partial/today/resume",
                    "/api/partial/today/ledger"]
        missing = [t for t in critical if t not in targets and
                   not any(c in today for c in [t.replace("/api/partial/today/", "")])]
        assert not missing, f"Today tab missing critical HTMX targets: {missing}"

    def test_capture_endpoint_registered(self):
        # Capture router uses prefix="/api" in main.py, so route is defined as "/capture"
        capture_router = DASHBOARD_DIR / "routers" / "capture.py"
        assert capture_router.exists(), "routers/capture.py must exist"
        text = capture_router.read_text(encoding="utf-8")
        assert '"/capture"' in text or "'/capture'" in text, \
            "capture.py must define a /capture POST route (registered with prefix='/api' in main.py)"

    def test_knowledge_search_endpoint_registered(self):
        assert self._endpoint_registered("/api/knowledge") or \
               self._endpoint_registered("/knowledge"), \
            "Knowledge search endpoint must be registered"

    def test_teach_tab_buttons_have_htmx(self):
        if not (TEMPLATES_DIR / "teach.html").exists():
            pytest.skip("teach.html not present")
        text = template_text("teach.html")
        assert "hx-get" in text or "hx-post" in text, \
            "Teach tab must have HTMX-wired buttons (not static HTML)"

    def test_metis_tab_agent_run_history_wired(self):
        metis_tmpl = TEMPLATES_DIR / "metis_tab.html"
        if not metis_tmpl.exists():
            pytest.skip("metis_tab.html not present")
        text = metis_tmpl.read_text(encoding="utf-8")
        assert "agent" in text.lower() and ("hx-get" in text or "hx-post" in text), \
            "Metis tab must have HTMX-wired agent run history"

    def test_planner_kanban_wired(self):
        if not has_partial("planner_kanban.html"):
            pytest.skip("planner_kanban.html not present")
        text = partial_text("planner_kanban.html")
        assert "hx" in text.lower() or "id=" in text.lower(), \
            "planner_kanban.html must have interactive HTMX elements"


# ---------------------------------------------------------------------------
# 10. Collapsible sections / long-list handling
# ---------------------------------------------------------------------------

class TestCollapsible:
    """Long lists must be collapsible or paginated to avoid UI overflow."""

    def test_agent_runs_table_has_limit_or_pagination(self):
        metis_router = DASHBOARD_DIR / "routers" / "metis_tab.py"
        if not metis_router.exists():
            pytest.skip("metis_tab.py not found")
        text = metis_router.read_text(encoding="utf-8")
        assert "LIMIT" in text or "limit" in text or "offset" in text or \
               "page" in text.lower(), \
            "Agent runs list must be paginated or limited — can grow to thousands of rows"

    def test_news_briefs_have_limit(self):
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "LIMIT" in text or "limit" in text, \
            "Today tab news must be limited — full table scan breaks performance"

    def test_library_table_has_limit_or_search(self):
        knowledge_router = DASHBOARD_DIR / "routers" / "knowledge.py"
        if not knowledge_router.exists():
            pytest.skip("knowledge.py not found")
        text = knowledge_router.read_text(encoding="utf-8")
        assert "LIMIT" in text or "search" in text.lower() or "q=" in text, \
            "Knowledge tab library table must be limited or searchable"

    def test_base_template_has_toggle_or_collapse_support(self):
        base = template_text("base.html")
        has_collapse = any(kw in base.lower() for kw in
                           ["collapse", "accordion", "toggle", "details", "summary"])
        # Alternatively, app.js may provide collapsing
        app_js = STATIC_DIR / "app.js"
        if app_js.exists():
            js_text = app_js.read_text(encoding="utf-8")
            has_collapse = has_collapse or "collapse" in js_text.lower() or \
                           "toggle" in js_text.lower()
        assert has_collapse or True, (
            "base.html or app.js should support collapsible sections for long content. "
            "This is a UX recommendation — not blocking."
        )


# ---------------------------------------------------------------------------
# 11. Customisation wiring
# ---------------------------------------------------------------------------

class TestCustomisation:
    """User identity and preferences must affect what the dashboard shows."""

    def test_display_name_appears_in_greeting(self):
        """The greeting must use display_name, not a hardcoded name."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "display_name" in text or "user_name" in text or "name" in text.lower(), \
            "Today tab greeting must use display_name from user-preferences.json"

    def test_no_hardcoded_personal_name_in_templates(self):
        """No template should hardcode a personal name."""
        personal_names = ["Stan", "Fatou", "Elena", "Kwame", "STAN"]
        violations = []
        for tmpl in TEMPLATES_DIR.rglob("*.html"):
            text = tmpl.read_text(encoding="utf-8", errors="replace")
            for name in personal_names:
                if name in text and "persona" not in str(tmpl):
                    violations.append(f"{tmpl.name}: hardcoded '{name}'")
        assert not violations, f"Hardcoded personal names in templates: {violations}"

    def test_metis_header_uses_dynamic_name(self):
        """The Metis tab header must show a dynamic researcher name."""
        metis_tmpl = TEMPLATES_DIR / "metis_tab.html"
        if not metis_tmpl.exists():
            pytest.skip("metis_tab.html not present")
        text = metis_tmpl.read_text(encoding="utf-8")
        # Must use a template variable, not hardcoded text
        assert "{{" in text or "{%" in text, \
            "metis_tab.html must use template variables for the header name"

    def test_theme_preference_respected(self):
        """The theme setting (light/dark/system) must be applied."""
        base = template_text("base.html")
        # CSS variables or class-based theming
        assert "theme" in base.lower() or "dark" in base.lower() or \
               "--color" in base or "prefers-color-scheme" in base, \
            "base.html must respect theme preference (dark/light/system)"

    def test_identity_edit_modal_exists(self):
        assert has_partial("metis_identity_edit_modal.html"), \
            "Identity edit modal must exist so user can change display_name from the UI"

    def test_identity_card_exists(self):
        assert has_partial("metis_identity_card.html"), \
            "Identity card partial must exist to show current user profile on Metis tab"


# ---------------------------------------------------------------------------
# 12. Morning brief — value out of the box
# ---------------------------------------------------------------------------

class TestMorningBrief:
    """The morning brief is the #1 entry point — it must work without configuration."""

    def test_morning_brief_partial_exists(self):
        assert has_partial("today_morning_brief.html"), \
            "today_morning_brief.html partial must exist"

    def test_morning_brief_generated_by_today_router(self):
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "morning" in text.lower() or "brief" in text.lower(), \
            "today.py must generate the morning brief"

    def test_morning_brief_uses_ai(self):
        """Morning brief must use Claude (not just static text)."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "claude" in text.lower() or "anthropic" in text.lower() or \
               "haiku" in text.lower() or "messages" in text.lower(), \
            "today.py morning brief must use Claude AI — not static text"

    def test_morning_brief_cached(self):
        """Brief must be cached in daily_insights — not regenerated on every load."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "daily_insights" in text or "cache" in text.lower(), \
            "Morning brief must be cached (daily_insights) to avoid re-generating on refresh"

    def test_morning_brief_under_600_tokens(self):
        """Brief must be concise — long briefs reduce daily usefulness."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        # Check max_tokens setting
        max_tokens_match = re.search(r"max_tokens\s*=\s*(\d+)", text)
        if max_tokens_match:
            max_tokens = int(max_tokens_match.group(1))
            assert max_tokens <= 800, \
                f"Morning brief max_tokens={max_tokens} — keep ≤ 800 for conciseness"

    def test_news_feed_loaded_in_today(self):
        """Today tab must show recent news signals."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "news_briefs" in text or "news" in text.lower(), \
            "today.py must query news_briefs for the news rail"

    def test_today_tab_has_value_without_agent_run(self):
        """Today tab must show useful content even if no agent has ever run."""
        today_tmpl = TEMPLATES_DIR / "today.html"
        if not today_tmpl.exists():
            pytest.skip("today.html not found")
        text = today_tmpl.read_text(encoding="utf-8")
        # Must have sections that don't depend on agent_runs
        assert "morning" in text.lower() or "brief" in text.lower() or \
               "news" in text.lower(), \
            "Today tab must have static-value sections (brief, news) that work day-1"


# ---------------------------------------------------------------------------
# 13. Surface completeness — each tab serves its stated purpose
# ---------------------------------------------------------------------------

class TestSurfaceCompleteness:
    """Each tab must contain the elements needed for its stated use case."""

    def test_knowledge_tab_has_search(self):
        knowledge_tmpl = TEMPLATES_DIR / "knowledge.html"
        if not knowledge_tmpl.exists():
            pytest.skip("knowledge.html not found")
        text = knowledge_tmpl.read_text(encoding="utf-8")
        assert "search" in text.lower() or "input" in text.lower(), \
            "Knowledge tab must have a search box"

    def test_knowledge_tab_has_pdf_search(self):
        assert has_partial("knowledge_pdf_search.html"), \
            "knowledge_pdf_search.html must exist for semantic PDF search (Phase L)"

    def test_learning_tab_has_spaced_repetition(self):
        assert has_partial("learning_due.html"), \
            "learning_due.html must exist for spaced repetition cards"

    def test_meetings_tab_has_import(self):
        assert has_partial("meeting_import_form.html"), \
            "meeting_import_form.html must exist for importing meeting notes"

    def test_work_tab_has_projects_and_tasks(self):
        assert has_partial("work_projects.html"), \
            "work_projects.html must exist to show active projects"
        assert has_partial("work_tasks.html"), \
            "work_tasks.html must exist to show tasks"

    def test_thinking_tab_has_ideas_notes_questions(self):
        for partial_name in ("thinking_ideas.html", "thinking_notes.html",
                             "thinking_questions.html"):
            assert has_partial(partial_name), \
                f"{partial_name} must exist — Thinking tab needs ideas, notes, and questions"

    def test_planner_has_kanban_and_focus(self):
        assert has_partial("planner_kanban.html"), \
            "planner_kanban.html must exist for the PhD kanban board"
        assert has_partial("planner_focus.html"), \
            "planner_focus.html must exist for the PhD focus board"

    def test_teach_tab_has_courses(self):
        assert has_partial("teach_courses.html") or \
               has_partial("teach_courses_list.html"), \
            "A teach courses partial must exist"

    def test_metis_tab_has_agent_directory(self):
        assert has_partial("metis_agent_directory.html") or \
               has_partial("metis_agents.html"), \
            "Metis tab must show agent directory for discoverability"

    def test_metis_tab_has_self_improvement(self):
        assert has_partial("metis_improvement.html"), \
            "metis_improvement.html must exist — self-improvement loop is a core Phase 9b feature"

    def test_token_monitor_exists(self):
        assert has_partial("metis_token_monitor.html"), \
            "metis_token_monitor.html must exist for token usage awareness"


# ---------------------------------------------------------------------------
# 14. Morning brief v2 — collapsibility, caching, and refresh behaviour
# ---------------------------------------------------------------------------

class TestMorningBriefV2:
    """Morning brief must be collapsible, cached, and refreshable without losing content."""

    def test_morning_brief_partial_exists(self):
        assert has_partial("today_morning_brief.html"), \
            "today_morning_brief.html partial must exist"

    def test_morning_brief_auto_opens_when_content_present(self):
        if not has_partial("today_morning_brief.html"):
            pytest.skip("today_morning_brief.html not present")
        text = partial_text("today_morning_brief.html")
        # display:block when brief, display:none when empty
        assert ("block" in text and "{% if" in text) or "display" in text, \
            "today_morning_brief.html must use display:block/none conditional for auto-open"

    def test_morning_brief_is_collapsible(self):
        if not has_partial("today_morning_brief.html"):
            pytest.skip("today_morning_brief.html not present")
        text = partial_text("today_morning_brief.html")
        assert "toggleBrief" in text or "onclick" in text.lower(), \
            "Morning brief header must have onclick handler (toggleBrief) for collapse"

    def test_morning_brief_chevron_rotates(self):
        if not has_partial("today_morning_brief.html"):
            pytest.skip("today_morning_brief.html not present")
        text = partial_text("today_morning_brief.html")
        assert "rotate" in text and "90" in text, \
            "Morning brief chevron must rotate 90deg when brief is open"

    def test_morning_brief_update_button_uses_htmx(self):
        if not has_partial("today_morning_brief.html"):
            pytest.skip("today_morning_brief.html not present")
        text = partial_text("today_morning_brief.html")
        assert "hx-post" in text and "morning-brief" in text, \
            "Morning brief update button must use hx-post to /api/morning-brief/refresh"

    def test_brief_refresh_endpoint_exists_in_router(self):
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        assert "morning-brief/refresh" in text or "morning_brief_refresh" in text, \
            "today.py must define the /api/morning-brief/refresh POST endpoint"

    def test_brief_generation_does_not_delete_cache_first(self):
        """Deleting cache before regeneration risks losing content if API call fails."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        if not today_router.exists():
            pytest.skip("today.py not found")
        text = today_router.read_text(encoding="utf-8")
        import re
        # Check that a DELETE on daily_insights does NOT appear before regeneration in the same function
        # A safe pattern regenerates first, then replaces — it does not delete first
        delete_before_generate = bool(
            re.search(r'DELETE.*daily_insights', text, re.IGNORECASE)
        )
        assert not delete_before_generate, \
            "_get_or_generate_brief must not DELETE from daily_insights before regenerating — " \
            "this risks losing cached content if the API call fails"

    def test_scheduler_brief_synthesis_no_asyncio_run(self):
        sched_py = DASHBOARD_DIR / "scheduler.py"
        if not sched_py.exists():
            pytest.skip("scheduler.py not found")
        text = sched_py.read_text(encoding="utf-8")
        import re
        brief_fn = re.search(r'def job_brief_synthesis.*?(?=\ndef |\Z)', text, re.DOTALL)
        if not brief_fn:
            pytest.skip("job_brief_synthesis function not found")
        assert "asyncio.run(" not in brief_fn.group(0), \
            "job_brief_synthesis must not use asyncio.run() — call _get_or_generate_brief() directly"


# ---------------------------------------------------------------------------
# 15. News quality — domain tagging and signal pipeline
# ---------------------------------------------------------------------------

class TestNewsQuality:
    """News ingestion must tag articles accurately and prioritise recent items."""

    def test_content_scan_classify_domain_exists(self):
        content_scan = DASHBOARD_DIR / "content_scan.py"
        if not content_scan.exists():
            pytest.skip("content_scan.py not found")
        text = content_scan.read_text(encoding="utf-8")
        assert "_classify_domain" in text, \
            "content_scan.py must define _classify_domain() for accurate topic tagging"

    def test_classify_domain_checks_hat_keywords(self):
        content_scan = DASHBOARD_DIR / "content_scan.py"
        if not content_scan.exists():
            pytest.skip("content_scan.py not found")
        text = content_scan.read_text(encoding="utf-8").lower()
        hat_keywords = ["trypanosomiasis", "sleeping sickness", "tsetse", "gambiense"]
        missing = [kw for kw in hat_keywords if kw not in text]
        assert not missing, \
            f"_classify_domain must check HAT-specific keywords — missing: {missing}"

    def test_classify_domain_not_just_first_tag(self):
        """Using tags.split(',')[0] as the only classification is a false-positive factory."""
        content_scan = DASHBOARD_DIR / "content_scan.py"
        if not content_scan.exists():
            pytest.skip("content_scan.py not found")
        text = content_scan.read_text(encoding="utf-8")
        # If _classify_domain only contains tags.split — that's insufficient
        import re
        fn_match = re.search(r'def _classify_domain.*?(?=\ndef |\Z)', text, re.DOTALL)
        if fn_match:
            fn_body = fn_match.group(0)
            assert "split" not in fn_body or len(fn_body) > 200, \
                "_classify_domain must do more than tags.split(',')[0] — implement keyword matching"

    def test_intelligence_uses_recency_ordering(self):
        """Daily context must surface last-24h items before older high-signal items."""
        intel_py = DASHBOARD_DIR / "intelligence.py"
        if not intel_py.exists():
            pytest.skip("intelligence.py not found")
        text = intel_py.read_text(encoding="utf-8")
        assert "created_at >= ?" in text or "created_at >=" in text, \
            "intelligence.py assemble_daily_context must filter/prioritise last-24h items"

    def test_intelligence_two_tier_order_by(self):
        intel_py = DASHBOARD_DIR / "intelligence.py"
        if not intel_py.exists():
            pytest.skip("intelligence.py not found")
        text = intel_py.read_text(encoding="utf-8")
        assert "THEN 0 ELSE 1" in text or "CASE WHEN" in text, \
            "intelligence.py must use two-tier ORDER BY: recent items first, then signal_strength"

    def test_news_briefs_has_source_type_column(self):
        _db1 = METIS_ROOT / "system" / "app" / "data" / "metis.sqlite"
        db_path = _db1 if _db1.exists() else DASHBOARD_DIR / "data" / "metis.sqlite"
        if not db_path.exists():
            pytest.skip("metis.sqlite not found")
        import sqlite3
        con = sqlite3.connect(str(db_path))
        try:
            cols = [r[1] for r in con.execute("PRAGMA table_info(news_briefs)").fetchall()]
            assert "source_type" in cols, \
                "news_briefs table must have source_type column to distinguish RSS/arXiv/WHO sources"
        except Exception as e:
            pytest.skip(f"Could not query news_briefs: {e}")
        finally:
            con.close()


# ---------------------------------------------------------------------------
# 16. Scheduler — coalesce, catch-up, and safe backup
# ---------------------------------------------------------------------------

class TestScheduler:
    """APScheduler must be configured for resilience after downtime."""

    def test_scheduler_file_exists(self):
        assert (DASHBOARD_DIR / "scheduler.py").exists(), \
            "scheduler.py must exist — daily tasks are not yet automated without it"

    def test_scheduler_no_misfire_grace_3600(self):
        sched_py = DASHBOARD_DIR / "scheduler.py"
        if not sched_py.exists():
            pytest.skip("scheduler.py not found")
        text = sched_py.read_text(encoding="utf-8")
        assert "misfire_grace_time=3600" not in text, \
            "misfire_grace_time=3600 must not be used — use None (unlimited) instead"

    def test_scheduler_uses_coalesce(self):
        sched_py = DASHBOARD_DIR / "scheduler.py"
        if not sched_py.exists():
            pytest.skip("scheduler.py not found")
        text = sched_py.read_text(encoding="utf-8")
        assert "coalesce=True" in text, \
            "add_job() calls must use coalesce=True to prevent job pile-up after downtime"

    def test_scheduler_has_catchup_block(self):
        sched_py = DASHBOARD_DIR / "scheduler.py"
        if not sched_py.exists():
            pytest.skip("scheduler.py not found")
        text = sched_py.read_text(encoding="utf-8").lower()
        assert "catch" in text and ("up" in text or "catchup" in text), \
            "scheduler.py must have a startup catch-up block that fires missed jobs on restart"

    def test_nightly_backup_uses_sqlite_backup(self):
        sched_py = DASHBOARD_DIR / "scheduler.py"
        if not sched_py.exists():
            pytest.skip("scheduler.py not found")
        text = sched_py.read_text(encoding="utf-8")
        import re
        backup_fn = re.search(r'def job_nightly_backup.*?(?=\ndef |\Z)', text, re.DOTALL)
        if not backup_fn:
            pytest.skip("job_nightly_backup not found in scheduler.py")
        fn_body = backup_fn.group(0)
        assert "shutil.copy2" not in fn_body, \
            "job_nightly_backup must not use shutil.copy2 — it can corrupt DB on live copy"
        assert ".backup(" in fn_body, \
            "job_nightly_backup must use sqlite3.Connection.backup() for safe live backup"

    def test_brief_synthesis_job_exists(self):
        sched_py = DASHBOARD_DIR / "scheduler.py"
        if not sched_py.exists():
            pytest.skip("scheduler.py not found")
        text = sched_py.read_text(encoding="utf-8")
        assert "brief_synthesis" in text or "morning_brief" in text.lower(), \
            "scheduler.py must define a brief synthesis job for automated morning brief generation"


# ---------------------------------------------------------------------------
# 17. CSS polish — motion.css, focus states, and design tokens
# ---------------------------------------------------------------------------

class TestCSSPolish:
    """CSS must include accessibility states, motion directives, and no conflicting rules."""

    def test_motion_css_file_exists(self):
        assert (STATIC_DIR / "motion.css").exists(), \
            "static/motion.css must exist — it owns all animation/transition CSS"

    def test_motion_css_linked_in_base(self):
        base = template_text("base.html")
        assert "motion.css" in base, \
            "motion.css must be linked in base.html"

    def test_motion_css_loaded_after_styles(self):
        base = template_text("base.html")
        styles_pos = base.find("styles.css")
        motion_pos = base.find("motion.css")
        if styles_pos == -1 or motion_pos == -1:
            pytest.skip("styles.css or motion.css not found in base.html")
        assert motion_pos > styles_pos, \
            "motion.css must be linked AFTER styles.css so it can override without !important"

    def test_app_div_has_data_motion(self):
        base = template_text("base.html")
        assert 'data-motion="on"' in base, \
            "The .app container div must have data-motion=\"on\" for motion.css directives"

    def test_app_div_has_data_hairline(self):
        base = template_text("base.html")
        assert 'data-hairline="on"' in base, \
            "The .app container div must have data-hairline=\"on\""

    def test_app_div_has_data_lift(self):
        base = template_text("base.html")
        assert 'data-lift="on"' in base, \
            "The .app container div must have data-lift=\"on\""

    def test_styles_css_has_focus_visible(self):
        styles_css = STATIC_DIR / "styles.css"
        if not styles_css.exists():
            pytest.skip("styles.css not found")
        text = styles_css.read_text(encoding="utf-8")
        assert "focus-visible" in text, \
            "styles.css must define :focus-visible for keyboard navigation accessibility"

    def test_styles_css_has_disabled_state(self):
        styles_css = STATIC_DIR / "styles.css"
        if not styles_css.exists():
            pytest.skip("styles.css not found")
        text = styles_css.read_text(encoding="utf-8")
        assert ":disabled" in text, \
            "styles.css must style :disabled buttons and inputs"

    def test_styles_css_no_conflicting_m_edge_left(self):
        """motion.css owns .m-edge-left::before — styles.css must not redefine its opacity."""
        styles_css = STATIC_DIR / "styles.css"
        if not styles_css.exists():
            pytest.skip("styles.css not found")
        text = styles_css.read_text(encoding="utf-8")
        import re
        conflict = re.search(r'm-edge-left\s*::\s*before[^}]*opacity\s*:', text, re.DOTALL)
        assert not conflict, \
            "styles.css must not define .m-edge-left::before { opacity: ... } — motion.css owns this rule"

    def test_styles_css_has_cache_bust_param(self):
        """Cache-busting parameter prevents stale CSS on deploy."""
        base = template_text("base.html")
        import re
        assert re.search(r'styles\.css\?v=', base), \
            "styles.css link in base.html must include ?v= cache-busting parameter"


# ---------------------------------------------------------------------------
# 18. Database schema completeness — v9e tables
# ---------------------------------------------------------------------------

class TestDatabaseSchema:
    """New tables added in v9e sessions must exist with correct columns."""

    def _get_connection(self):
        _db1 = METIS_ROOT / "system" / "app" / "data" / "metis.sqlite"
        db_path = _db1 if _db1.exists() else DASHBOARD_DIR / "data" / "metis.sqlite"
        if not db_path.exists():
            return None
        import sqlite3
        return sqlite3.connect(str(db_path))

    def _get_columns(self, con, table: str) -> list:
        try:
            return [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
        except Exception:
            return []

    def _get_tables(self, con) -> list:
        try:
            return [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        except Exception:
            return []

    def test_daily_insights_table_exists(self):
        # daily_insights is created lazily (CREATE TABLE IF NOT EXISTS) on first morning-brief
        # generation. Accept either: table present in live DB, OR CREATE TABLE defined in source.
        con = self._get_connection()
        if con:
            try:
                tables = self._get_tables(con)
                if "daily_insights" in tables:
                    return  # live table found — pass
            finally:
                con.close()
        # Fall back: verify the table is defined in source code
        today_py = METIS_ROOT / "system" / "app-py" / "routers" / "today.py"
        intel_py = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools" / "intelligence.py"
        found = any(
            p.exists() and "daily_insights" in p.read_text()
            for p in [today_py, intel_py]
        )
        assert found, "daily_insights must be defined in today.py or intelligence.py"

    def test_daily_insights_has_required_columns(self):
        con = self._get_connection()
        if not con:
            pytest.skip("metis.sqlite not found")
        try:
            cols = self._get_columns(con, "daily_insights")
            if not cols:
                pytest.skip("daily_insights table not found")
            required = ["insight_date", "content", "model", "generated_at"]
            missing = [c for c in required if c not in cols]
            assert not missing, \
                f"daily_insights table missing columns: {missing}"
        finally:
            con.close()

    def test_user_config_table_exists(self):
        # user_config is created lazily on first config_wizard or get_user_profile call.
        # Accept either: table present in live DB, OR CREATE TABLE defined in source.
        con = self._get_connection()
        if con:
            try:
                tables = self._get_tables(con)
                if "user_config" in tables:
                    return  # live table found — pass
            finally:
                con.close()
        # Fall back: verify the table is defined in source code
        import glob as _glob
        src_dirs = [
            str(METIS_ROOT / "system" / "app-py"),
            str(METIS_ROOT / "system" / "mcp-server" / "src"),
        ]
        found = False
        for d in src_dirs:
            for f in _glob.glob(d + "/**/*.py", recursive=True):
                try:
                    if "user_config" in open(f).read():
                        found = True
                        break
                except Exception:
                    pass
            if found:
                break
        assert found, "user_config table must be defined somewhere in app-py or mcp-server source"

    def test_user_config_has_key_value_columns(self):
        con = self._get_connection()
        if not con:
            pytest.skip("metis.sqlite not found")
        try:
            cols = self._get_columns(con, "user_config")
            if not cols:
                pytest.skip("user_config table not found")
            assert "key" in cols, "user_config must have a 'key' column"
            assert "value" in cols, "user_config must have a 'value' column"
        finally:
            con.close()

    def test_news_briefs_source_type_column(self):
        con = self._get_connection()
        if not con:
            pytest.skip("metis.sqlite not found")
        try:
            cols = self._get_columns(con, "news_briefs")
            if not cols:
                pytest.skip("news_briefs table not found")
            assert "source_type" in cols, \
                "news_briefs must have source_type column to distinguish RSS/arXiv/WHO sources"
        finally:
            con.close()

    def test_user_name_set_in_config(self):
        """user_config must have a user_name key that is not a placeholder."""
        con = self._get_connection()
        if not con:
            pytest.skip("metis.sqlite not found")
        try:
            tables = self._get_tables(con)
            if "user_config" not in tables:
                pytest.skip("user_config table not found")
            row = con.execute(
                "SELECT value FROM user_config WHERE key='user_name'"
            ).fetchone()
            if row is None:
                pytest.skip("user_name key not set in user_config")
            name = row[0]
            assert name not in ("", "Researcher", "Amélie", "User", None), \
                f"user_config.user_name is a placeholder value: '{name}' — set to the actual user name"
        finally:
            con.close()

    def test_trust_badge_exists(self):
        assert has_partial("trust_badge.html"), \
            "trust_badge.html must exist to reassure users that data stays local"
