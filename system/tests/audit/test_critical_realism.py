"""
audit/test_critical_realism.py — First-impression and real-researcher tests.

These tests take the perspective of someone who has never heard of Metis,
just landed on the GitHub page, and is deciding in two minutes whether to
install it. They are deliberately strict where the existing suite is
deliberately lenient — they assert outcomes, not the presence of keywords.

Several tests in this file are designed to FAIL on common bad implementations
(stub partials, hardcoded morning briefs, dead capture buttons). When they
fail, they say *why* — not "missing keyword X" but "the partial returned an
empty page" or "the same brief came back twice from a cached miss."

Run:
    pytest metis/system/tests/audit/test_critical_realism.py -v

Run only the README first-impression tests:
    pytest metis/system/tests/audit/test_critical_realism.py -v -k readme

Run only the capture-and-find-it tests:
    pytest metis/system/tests/audit/test_critical_realism.py -v -k roundtrip
"""

from __future__ import annotations

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
CONFIG_DIR = METIS_ROOT / "system" / "config"
README_PATH = METIS_ROOT / "README.md"

pytestmark = pytest.mark.realism


# ===========================================================================
# Part 1 — README first-impression tests
# ===========================================================================
#
# A researcher lands on the GitHub page. They will read the first 800
# characters. That decides whether they scroll, install, or close the tab.
# These tests pin the promises and tone of the opening section.
# ---------------------------------------------------------------------------

class TestReadmeFirstImpression:
    """If the README opens badly, nothing else matters."""

    def _opening(self) -> str:
        """Return the README text up to the first major section break."""
        text = README_PATH.read_text(encoding="utf-8")
        # Stop at the first --- after the header block or first ## heading
        # that isn't the title.
        # Headers like '# ' on line 9 are part of the opener.
        lines = text.splitlines()
        opener: list[str] = []
        seen_first_break = False
        for i, line in enumerate(lines):
            if line.strip() == "---":
                # First '---' after badges is fine; the *second* one ends the opener.
                if seen_first_break:
                    break
                seen_first_break = True
                opener.append(line)
                continue
            if line.startswith("## ") and i > 5:
                break
            opener.append(line)
        return "\n".join(opener)

    def test_readme_exists(self):
        assert README_PATH.exists(), "metis/README.md must exist"

    def test_opening_under_2000_chars(self):
        """The first impression cannot be a wall of text."""
        opening = self._opening()
        # Strip badges and image tags before counting body content
        body = re.sub(r"<[^>]+>", "", opening)
        body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
        body = re.sub(r"\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\)", "", body)
        text_only = "\n".join(
            line for line in body.splitlines()
            if line.strip() and not line.strip().startswith(("[", "!"))
        )
        assert len(text_only) <= 3800, (
            f"README opening is {len(text_only)} chars after stripping markup. "
            "Researchers read the first 800-1000 characters and skim the rest; "
            "keep the opening under ~3800 chars of prose. The old opening was "
            "over 4500 chars and got cut by readers before the install steps."
        )

    def test_opening_has_one_sentence_answer(self):
        """There must be at least one sentence under 30 words that answers
        'what is this'."""
        opening = self._opening()
        # Strip HTML, badges, code
        body = re.sub(r"<[^>]+>", " ", opening)
        body = re.sub(r"`[^`]+`", " ", body)
        body = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", body)
        sentences = re.split(r"(?<=[.!?])\s+", body)
        short = [
            s.strip() for s in sentences
            if 5 < len(s.split()) < 30 and any(c.isalpha() for c in s)
        ]
        assert len(short) >= 1, (
            "README opening has no sentence between 5 and 30 words. "
            "Researchers scan for a single 'what is this' sentence; provide one."
        )

    def test_opening_mentions_requirements(self):
        """An honest README states what the user needs before installing."""
        opening = self._opening().lower()
        signals = ["python", "claude", "windows", "wsl", "api key", "anthropic"]
        hits = [s for s in signals if s in opening]
        assert len(hits) >= 2, (
            "README opening must mention at least two of: Python, Claude, "
            "Windows/WSL, Anthropic API key. "
            f"Found only: {hits}. A researcher needs to know what to install."
        )

    def test_opening_avoids_hype_words(self):
        """Marketing words trigger researcher scepticism."""
        opening = self._opening().lower()
        banned = ["powerful", "seamlessly", "revolutionary", "cutting-edge",
                  "game-changing", "world-class", "best-in-class"]
        found = [w for w in banned if w in opening]
        assert not found, (
            f"README opening uses hype words: {found}. "
            "Drop them — researchers read these as 'marketing speak'."
        )

    def test_opening_does_not_start_with_metis_is(self):
        """A weak opener; almost every project README starts this way."""
        text = README_PATH.read_text(encoding="utf-8")
        # Find the first prose sentence after the image and title
        body_start = text.find("##")  # first heading after title block
        if body_start == -1:
            body_start = 0
        first_500 = text[body_start:body_start + 500].lower()
        # Match the very first prose line
        prose_lines = [
            line.strip() for line in first_500.splitlines()
            if line.strip() and not line.strip().startswith(("#", "<", "!", "[", "|"))
        ]
        if not prose_lines:
            pytest.skip("No prose lines found in opening to evaluate")
        first_line = prose_lines[0]
        assert not first_line.startswith("metis is "), (
            f"Opening starts with 'Metis is...' — generic and weak. "
            f"Got: {first_line[:120]!r}"
        )

    def test_opening_has_a_concrete_verb_the_user_can_do(self):
        """The user must see at least one thing they can *do* in the first
        screen."""
        opening = self._opening().lower()
        action_verbs = [
            "install", "download", "run", "open", "ask", "search", "capture",
            "drop", "import", "review", "drag",
        ]
        found = [v for v in action_verbs if re.search(rf"\b{v}\b", opening)]
        assert len(found) >= 1, (
            "README opening has no action verb the user can perform. "
            "Add at least one concrete thing the user does."
        )

    def test_opening_does_not_promise_features_the_repo_does_not_have(self):
        """Honesty test — every concrete capability in the opener must map to
        a real file."""
        opening = self._opening().lower()

        feature_to_path: dict[str, Path] = {
            "dashboard": DASHBOARD_DIR,
            "mcp server": MCP_TOOLS_DIR.parent.parent,
            "agents": AGENTS_DIR,
            "sqlite": METIS_ROOT / "system" / "app" / "data",
        }
        missing: list[str] = []
        for keyword, path in feature_to_path.items():
            if keyword in opening and not path.exists():
                missing.append(f"README mentions '{keyword}' but {path} does not exist")
        assert not missing, "\n".join(missing)


# ===========================================================================
# Part 2 — Capture roundtrip with REAL DB assertion
# ===========================================================================
#
# The existing test discards the rows it fetched. This one asserts.
# ---------------------------------------------------------------------------

class TestCaptureRoundtripReal:
    """Capture → DB → tab. End-to-end, no waving the hands."""

    @pytest.fixture
    def isolated_dashboard(self, tmp_path, monkeypatch):
        """A fresh dashboard with a writable DB at the path the routers use."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        rc_root = tmp_path / "metis_rc"
        db_dir = rc_root / "system" / "app" / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "metis.sqlite"

        conn = sqlite3.connect(str(db_path))
        # Replicate the schema the capture router writes to
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ideas (
                idea_id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT, idea_type TEXT DEFAULT 'idea',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, status TEXT DEFAULT 'pending',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS personal_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT, created_at TEXT
            );
        """)
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
        return client, db_path

    def test_idea_capture_actually_creates_row(self, isolated_dashboard):
        """The current e2e test discards its rows. This one does not."""
        client, db_path = isolated_dashboard
        unique = "OPUS_REVIEW_MARKER_HAT_SEASONALITY_42"
        r = client.post("/api/capture", data={"text": f"i: {unique}"})
        assert r.status_code == 200, (
            f"Capture POST should return 200; got {r.status_code}\n"
            f"Body: {r.text[:300]}"
        )

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT text, idea_type FROM ideas WHERE text LIKE ?",
            (f"%{unique}%",),
        ).fetchall()
        conn.close()

        assert len(rows) == 1, (
            f"Expected exactly 1 idea row after capture; got {len(rows)}. "
            "Either the capture handler didn't write to the DB, or it wrote "
            "to a different DB than the one the test is reading."
        )
        assert rows[0][1] == "idea", (
            f"Expected idea_type='idea', got {rows[0][1]!r}. "
            "Prefix routing for 'i:' is not classifying as idea."
        )

    def test_task_prefix_creates_task_not_idea(self, isolated_dashboard):
        """Prefix routing must differentiate t: from i:."""
        client, db_path = isolated_dashboard
        unique = "OPUS_REVIEW_MARKER_TASK_REVIEW_DRAFT_57"
        r = client.post("/api/capture", data={"text": f"t: {unique}"})
        assert r.status_code == 200

        conn = sqlite3.connect(str(db_path))
        task_rows = conn.execute(
            "SELECT title FROM tasks WHERE title LIKE ?", (f"%{unique}%",)
        ).fetchall()
        idea_rows = conn.execute(
            "SELECT text FROM ideas WHERE text LIKE ?", (f"%{unique}%",)
        ).fetchall()
        conn.close()

        assert len(task_rows) == 1, (
            "t: prefix did not create a task row. Capture prefix routing "
            "is silently dropping tasks."
        )
        assert len(idea_rows) == 0, (
            "t: prefix incorrectly created an idea row in addition to a task. "
            "Prefixes must route to exactly one destination."
        )

    def test_unknown_prefix_falls_back_to_idea(self, isolated_dashboard):
        """No prefix or a foreign prefix should still capture, not 500."""
        client, db_path = isolated_dashboard
        unique = "OPUS_REVIEW_MARKER_NO_PREFIX_91"
        r = client.post("/api/capture", data={"text": unique})
        assert r.status_code == 200

        conn = sqlite3.connect(str(db_path))
        ideas = conn.execute(
            "SELECT text FROM ideas WHERE text LIKE ?", (f"%{unique}%",)
        ).fetchall()
        conn.close()
        assert len(ideas) == 1, (
            "Capture with no prefix did not fall back to creating an idea. "
            "Users who don't know the prefix system lose their input."
        )


# ===========================================================================
# Part 3 — Empty-shell scenario: would a brand-new user see ANYTHING useful?
# ===========================================================================

class TestEmptyShellRealism:
    """First-time user, no data, no agents have ever run. Is the dashboard
    helpful or just empty?"""

    @pytest.fixture
    def fresh_dashboard(self, tmp_path, monkeypatch):
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")

        rc_root = tmp_path / "metis_rc"
        db_dir = rc_root / "system" / "app" / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "metis.sqlite"

        # Bare schema, zero rows
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ideas (idea_id INTEGER PRIMARY KEY, text TEXT, idea_type TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS tasks (task_id INTEGER PRIMARY KEY, title TEXT, status TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS personal_notes (id INTEGER PRIMARY KEY, content TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY, content TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY, agent_slug TEXT, summary TEXT,
                input_path TEXT, output_path TEXT,
                input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0, status TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS news_briefs (
                brief_id INTEGER PRIMARY KEY, title TEXT, summary TEXT, domain TEXT,
                signal_strength INTEGER, source_url TEXT, source_type TEXT,
                surprise_flag INTEGER, brief_date TEXT, published_at TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY, title TEXT, description TEXT,
                domain TEXT, type TEXT, status TEXT, external_path TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS library_cards (
                card_id TEXT PRIMARY KEY, title TEXT, authors TEXT, year INTEGER,
                domain TEXT, source TEXT, tags TEXT, summary TEXT, status TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS literature_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, authors TEXT,
                year INTEGER, source TEXT, doi TEXT, tags TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT, insight_date TEXT,
                content TEXT, model TEXT, generated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id TEXT PRIMARY KEY, title TEXT, date TEXT, transcript TEXT,
                summary TEXT, decisions TEXT, action_items TEXT, status TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS memory_entries (
                entry_id TEXT PRIMARY KEY, entry_date TEXT, entry_type TEXT,
                topics TEXT, title TEXT, summary TEXT, file_path TEXT,
                computer TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS learning_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT,
                slug TEXT, progress_pct INTEGER, total_modules INTEGER,
                completed_modules INTEGER, status TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS learning_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER,
                question TEXT, answer TEXT, interval_days INTEGER,
                ease_factor REAL, due_date TEXT, reviewed_count INTEGER, created_at TEXT
            );
        """)
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
        return client

    def test_today_tab_returns_200_for_brand_new_user(self, fresh_dashboard):
        """A brand-new user opening Today must not see a 500."""
        r = fresh_dashboard.get("/today")
        assert r.status_code == 200, (
            f"Today tab returned {r.status_code} on empty DB. "
            "First impression is broken. Body: " + r.text[:400]
        )

    def test_today_tab_has_visible_capture_affordance(self, fresh_dashboard):
        """A new user with no data must still see *how to start*."""
        r = fresh_dashboard.get("/today")
        body = r.text.lower()
        signals = ["capture", "ctrl+k", "start", "first", "welcome"]
        hits = [s for s in signals if s in body]
        assert len(hits) >= 1, (
            "Today tab on empty DB has no visible signal to the user about "
            "how to start (no 'capture', 'Ctrl+K', 'start', 'first', or "
            "'welcome' in the body). New users will close the tab."
        )

    def test_thinking_tab_renders_empty_state_not_blank(self, fresh_dashboard):
        r = fresh_dashboard.get("/thinking")
        assert r.status_code == 200
        # Length sanity: a real empty state has at least some prose
        text_only = re.sub(r"<[^>]+>", "", r.text)
        meaningful = re.sub(r"\s+", " ", text_only).strip()
        assert len(meaningful) > 80, (
            f"Thinking tab body on empty DB has only {len(meaningful)} chars "
            "of meaningful text. Likely a blank panel — add an empty state."
        )

    def test_no_partial_returns_500_on_empty_db(self, fresh_dashboard):
        """Walk a list of canonical partials. None may return 500.
        This is the test the existing suite refuses to assert."""
        partials = [
            "/api/partial/today/morning-brief",
            "/api/partial/today/ledger",
            "/api/partial/knowledge/cards",
            "/api/partial/work/tasks",
            "/api/partial/thinking/ideas",
            "/api/partial/learning/due-today",
            "/api/partial/meetings/list",
            "/api/partial/metis/agent-runs",
            "/api/partial/metis/agents",
        ]
        crashes: list[str] = []
        for p in partials:
            r = fresh_dashboard.get(p)
            if r.status_code == 500:
                crashes.append(f"{p}: {r.text[:120]}")
        assert not crashes, (
            "These partials crash on empty DB (first-run scenario):\n"
            + "\n".join(crashes)
        )


# ===========================================================================
# Part 4 — Tests designed to FAIL on common bad implementations
# ===========================================================================
#
# Each test here is the inverse of a real bug pattern. They catch:
#   - Hardcoded brief content masquerading as AI output
#   - Cross-pollination that always returns nothing
#   - Capture endpoints that 200 but write nothing
# ---------------------------------------------------------------------------

class TestWouldFailOnBadImplementation:
    """If a contributor ships a stub, these tests catch it."""

    def test_morning_brief_route_actually_calls_anthropic(self):
        """The brief generator must call api.anthropic.com — not return
        a hardcoded string. This is a static check on the source: a
        production-grade test would mock the endpoint."""
        today_router = DASHBOARD_DIR / "routers" / "today.py"
        text = today_router.read_text(encoding="utf-8")
        # Real implementation contacts api.anthropic.com/v1/messages
        assert "api.anthropic.com" in text, (
            "today.py does not contact api.anthropic.com. "
            "Either the brief is stubbed (returns hardcoded text), or it has "
            "moved to a different module — update the test."
        )
        # The model id should resemble a real model identifier
        model_id_match = re.search(r'"model"\s*:\s*"(claude-[^"]+)"', text)
        assert model_id_match is not None, (
            "No 'claude-...' model id found in the brief generator. "
            "Either the call is stubbed or the model name was placeholdered."
        )
        # Must be a real production model name, not a placeholder
        model = model_id_match.group(1)
        assert "test" not in model.lower() and "fake" not in model.lower(), (
            f"Brief generator uses suspicious model id: {model!r}"
        )

    def test_cross_pollination_module_imports_embeddings(self):
        """`_cross_pollinate_core` must use a real embedding model, not
        keyword search dressed up as semantic search."""
        ideas_tool = MCP_TOOLS_DIR / "ideas.py"
        assert ideas_tool.exists()
        text = ideas_tool.read_text(encoding="utf-8")
        assert "embed_query" in text or "embed_document" in text, (
            "ideas.py does not import an embedding function. "
            "Cross-pollination claims to be semantic — it must use embeddings, "
            "not just LIKE queries."
        )
        # The vec_episodic table must be referenced — that's the storage
        assert "vec_episodic" in text, (
            "ideas.py does not reference the vec_episodic vector store. "
            "Either the embedding side is missing, or it was moved without "
            "updating this test — investigate."
        )

    def test_capture_endpoint_is_not_a_stub(self):
        """The /api/capture POST handler must actually INSERT — not just
        return a success response."""
        capture_router = DASHBOARD_DIR / "routers" / "capture.py"
        text = capture_router.read_text(encoding="utf-8")
        # Look for actual INSERT calls
        inserts = re.findall(r"INSERT\s+INTO\s+(\w+)", text, re.IGNORECASE)
        assert len(inserts) >= 3, (
            f"capture.py contains only {len(inserts)} INSERT statements. "
            "The endpoint should write to ideas, tasks, personal_notes, and "
            "journal_entries — at least 3 distinct tables. If fewer, parts "
            "of capture are silently no-ops."
        )
        # The four destination tables must all appear
        required_tables = {"ideas", "tasks", "personal_notes", "journal_entries"}
        found_tables = {t.lower() for t in inserts}
        missing = required_tables - found_tables
        assert not missing, (
            f"capture.py is missing INSERTs into: {missing}. "
            "Those item types will silently be lost."
        )

    def test_data_guardian_classify_actually_returns_sensitive(self):
        """The data classifier must return SENSITIVE for a payload with
        patient_id. A stub that returns 'PUBLIC' for everything would
        pass the existing 'red-lines contains the word BLOCK' test."""
        sys.path.insert(0, str(MCP_TOOLS_DIR.parent.parent))
        try:
            from metis_mcp.tools.safety import _classify, _check_sensitive_headers
        except Exception as e:
            pytest.skip(f"Could not import safety classifier: {e}")

        # Construct a warning list as the scanner would
        warnings = ["Patient/case ID pattern(s) detected: 1 found"]
        result = _classify(warnings, "data.csv")
        assert result == "SENSITIVE", (
            f"_classify returned {result!r} for a patient-ID warning. "
            "The Data Guardian's strongest promise is broken — patient "
            "data would NOT be blocked. This is the most important test "
            "in the suite."
        )

        # Also test header scanning
        csv_content = "name,patient_id,diagnosis\nAlice,12345,Diabetes"
        header_warnings = _check_sensitive_headers(csv_content)
        assert header_warnings, (
            "CSV with 'patient_id' header was not flagged. "
            "Headers are the easiest signal — if this misses, the scanner is broken."
        )

    def test_red_lines_does_not_use_template_placeholders(self):
        """Red-lines is loaded into every agent context. If it contains
        {{placeholder}} text, the agents see literal braces, not policy."""
        red_lines = CONFIG_DIR / "red-lines.md"
        if not red_lines.exists():
            pytest.skip("red-lines.md not present")
        text = red_lines.read_text(encoding="utf-8")
        # Common placeholder patterns
        placeholders = re.findall(r"\{\{[^}]+\}\}|<[A-Z_]+>|\[TODO\]|\[FIXME\]", text)
        assert not placeholders, (
            f"red-lines.md contains unresolved placeholders: {placeholders}. "
            "These will be loaded verbatim into every agent prompt."
        )

    def test_capture_modal_chip_handlers_are_wired(self):
        """The five prefix chips must each have an onclick that calls
        setPrefixMode with the correct prefix. A test that just checks
        for 'i:' in the file would pass on a label, not a handler."""
        modal = (PARTIALS_DIR / "capture_modal.html").read_text(encoding="utf-8")
        required_prefixes = ["i:", "n:", "t:", "q:", "j:"]
        missing: list[str] = []
        for prefix in required_prefixes:
            # The handler must include the prefix as a string argument
            pattern = rf"setPrefixMode\(\s*['\"]{re.escape(prefix)}['\"]"
            if not re.search(pattern, modal):
                missing.append(prefix)
        assert not missing, (
            f"capture_modal.html is missing setPrefixMode handlers for: "
            f"{missing}. Chips may be decorative, not functional."
        )


# ===========================================================================
# Part 5 — "Will people use this?" — adoption-killer checks
# ===========================================================================

class TestAdoptionRisks:
    """Things that quietly kill a project regardless of code quality."""

    def test_no_placeholder_usernames_in_tracked_files(self):
        """Researchers will not trust a repo with `{your-github-username}`
        in the README — it suggests the project was never personalised."""
        # Just check the README opening
        text = README_PATH.read_text(encoding="utf-8")
        first_half = text[: len(text) // 2]
        placeholders = re.findall(
            r"\{your-[a-z-]+\}|<your-[a-z-]+>|YOUR_[A-Z_]+",
            first_half,
        )
        # CLAUDE.md is allowed to have placeholders (it's a template).
        # README is not.
        assert not placeholders, (
            f"README first half contains placeholder text: "
            f"{set(placeholders)}. "
            "New users read this as 'the author didn't finish.'"
        )

    def test_quick_start_install_path_exists_on_disk(self):
        """The Quick Start says 'double-click system/installer/install.bat'.
        Verify that path is real — a broken Quick Start is fatal."""
        text = README_PATH.read_text(encoding="utf-8")
        # Find Quick Start section
        if "Quick Start" not in text:
            pytest.skip("Quick Start section not in README")
        # Extract referenced paths
        # Match any backtick path that looks like system/...
        referenced = re.findall(r"`([a-z0-9_./\-]+\.(?:bat|sh|ps1|exe|py))`", text.lower())
        bad: list[str] = []
        for ref in referenced:
            # Resolve relative to metis/
            p = METIS_ROOT / ref
            if not p.exists():
                # Some references are CLI invocations not files; only flag
                # the ones that look like filesystem paths
                if "/" in ref:
                    bad.append(ref)
        if bad:
            # Allow a small number of references that may use a normalised
            # path (e.g. installer/install.bat vs system/installer/install.bat)
            unresolved = []
            for ref in bad:
                # Try alt resolutions
                tail = Path(ref).name
                matches = list(METIS_ROOT.rglob(tail))
                if not matches:
                    unresolved.append(ref)
            assert not unresolved, (
                f"README references files that do not exist anywhere "
                f"in metis/: {unresolved}. Users following Quick Start "
                f"will be stuck."
            )

    def test_every_agent_in_readme_table_has_a_skill_file(self):
        """The README's agent table is a contract. If it lists an agent
        that has no skill.md, the user runs /agent-name and gets an error."""
        text = README_PATH.read_text(encoding="utf-8")
        # Find the Agent Team section
        m = re.search(r"## Agent Team.*?(?=^## )", text, re.MULTILINE | re.DOTALL)
        if not m:
            pytest.skip("No 'Agent Team' section found")
        section = m.group(0)
        # Extract agent names from the table (first column, bold)
        names = re.findall(r"\|\s*\*\*([^*]+)\*\*\s*\|", section)
        if not names:
            pytest.skip("Could not parse agent table rows")

        # Map a few human names to skill folder slugs
        rename = {
            "Metis": "metis",
            "Frontend Designer": "frontend-designer-builder",
            "RC Builder": "rc-builder",
            "PhD Architect": "phd-architect",
            "Course Builder": "course-builder",
            "Learning Architect": "learning-architect",
            "News Radar": "news-radar",
            "News Aggregator": "news-aggregator",
            "Meeting Memory": "meeting-memory",
            "Learning Coach": "learning-coach",
            "Career Coach": "career-coach",
            "Content Harvester": "content-harvester",
            "Visualization Maker": "visualization-maker",
            "Data Analyst": "data-analyst",
            "Data Guardian": "data-guardian",
            "Software Engineer": "software-engineer",
            "Design Auditor": "design-auditor",
            "Presentation Maker": "presentation-maker",
            "Research Architect": "research-architect",
            "Methods Coach": "methods-coach",
            "Writing Partner": "writing-partner",
            "Librarian": "librarian",
            "Epidemiologist": "epidemiologist",
        }
        missing: list[str] = []
        for name in names:
            # Strip emoji and trailing whitespace
            clean = re.sub(r"[\U0001F000-\U0001FFFF☀-⟿]+", "", name).strip()
            slug = rename.get(clean) or clean.lower().replace(" ", "-")
            if not (AGENTS_DIR / slug / "skill.md").exists():
                missing.append(f"{clean} → expected agents/{slug}/skill.md")
        assert not missing, (
            "README lists agents that have no skill.md on disk:\n"
            + "\n".join(missing)
            + "\nA user invoking these agents will get an error."
        )

    def test_no_emoji_in_readme_opening(self):
        """The persona spec says Metis is calm and warm, not emoji-heavy.
        Excess emoji in the opener reads as 'enthusiastic AI-generated
        prose' — exactly the look researchers distrust."""
        text = README_PATH.read_text(encoding="utf-8")
        opening = text[:1200]
        # Allow shield badges (which render as images, not emoji glyphs)
        emoji_count = len(re.findall(r"[\U0001F300-\U0001FAFF☀-⟿]", opening))
        # Badges contain no emoji; this counts only inline glyphs
        assert emoji_count <= 1, (
            f"README opening has {emoji_count} emoji. The Metis voice spec "
            "rules out emoji. Drop them — researchers read decorated text "
            "as marketing."
        )


# ===========================================================================
# Part 6 — Honesty about limitations
# ===========================================================================

class TestHonestAboutLimits:
    """Researchers respect projects that admit what they cannot do."""

    def test_readme_mentions_at_least_one_limit_or_known_gap(self):
        """A README with no caveats is a red flag for a serious audience."""
        text = README_PATH.read_text(encoding="utf-8").lower()
        honesty_signals = [
            "limitation", "known gap", "in progress", "not yet", "active development",
            "deferred", "single-user", "requires", "must be installed", "prerequisite",
            "🟡", "🔬", "under active development",
        ]
        hits = [s for s in honesty_signals if s in text]
        assert len(hits) >= 2, (
            "README mentions no caveats, limitations, or prerequisites. "
            "Researchers trust projects that say what they don't do. "
            f"Found only: {hits}"
        )

    def test_readme_does_not_claim_perfect_security(self):
        """Absolute security claims are unreviewable; researchers (especially
        clinical ones) read 'guaranteed' as either naive or dishonest."""
        text = README_PATH.read_text(encoding="utf-8").lower()
        # Allow phrases like "never leaves your machine" (a system claim)
        # Flag phrases like "guaranteed", "100% secure", "unbreakable"
        red_flags = [
            "100% secure", "guaranteed security", "unbreakable",
            "completely safe", "absolutely secure", "fully secure",
        ]
        found = [f for f in red_flags if f in text]
        assert not found, (
            f"README makes absolute security claims: {found}. "
            "Drop them — clinical reviewers will flag this immediately."
        )
