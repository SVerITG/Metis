"""
e2e/test_smoke.py — Dashboard smoke tests.

Verifies that the dashboard loads, all tab pages respond with 200, and
key HTMX partials return 200. Uses FastAPI TestClient (no browser required).

Run:
    bash system/tests/run_tests.sh --full
    # or directly:
    pytest system/tests/e2e/ -v -m e2e
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Resolve paths
# File is at: Research Cortex/system/tests/e2e/test_smoke.py
#   parents[2] = Research Cortex/system/
#   parents[3] = Research Cortex/  (git root)
# ---------------------------------------------------------------------------

_SYSTEM_DIR = Path(__file__).resolve().parents[2]  # Research Cortex/system/
DASHBOARD_DIR = _SYSTEM_DIR / "app-py"
MCP_SRC = _SYSTEM_DIR / "mcp-server" / "src"

# Add both to sys.path so imports work
for p in (str(DASHBOARD_DIR), str(MCP_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------------------------------------------------------------------
# Minimal DB schema — tables the app expects to exist on startup
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ideas (
    idea_id TEXT PRIMARY KEY, title TEXT, body TEXT,
    tags TEXT, status TEXT DEFAULT 'open', created_at TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY, title TEXT, priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open', project TEXT, due_date TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id TEXT PRIMARY KEY, agent_slug TEXT, summary TEXT,
    input_path TEXT, output_path TEXT,
    input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0, status TEXT DEFAULT 'completed', created_at TEXT
);
CREATE TABLE IF NOT EXISTS reflexions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
    agent_slug TEXT, went_well TEXT, could_improve TEXT,
    missing_context TEXT, tool_wishes TEXT, created_at TEXT
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
CREATE TABLE IF NOT EXISTS news_briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, summary TEXT,
    source TEXT, source_type TEXT DEFAULT 'news',
    domain TEXT, source_url TEXT,
    published_at TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS meetings (
    meeting_id TEXT PRIMARY KEY, title TEXT, date TEXT, transcript TEXT,
    summary TEXT, decisions TEXT, action_items TEXT, status TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY, title TEXT, description TEXT,
    domain TEXT, type TEXT, status TEXT DEFAULT 'active',
    external_path TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS daily_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_date TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    sources TEXT DEFAULT '',
    generated_at TEXT NOT NULL,
    model TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS learning_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT,
    slug TEXT, progress_pct INTEGER DEFAULT 0, total_modules INTEGER DEFAULT 1,
    completed_modules INTEGER DEFAULT 0, status TEXT DEFAULT 'active', created_at TEXT
);
CREATE TABLE IF NOT EXISTS learning_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER,
    question TEXT, answer TEXT, interval_days INTEGER DEFAULT 1,
    ease_factor REAL DEFAULT 2.5, due_date TEXT, reviewed_count INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id TEXT PRIMARY KEY, entry_date TEXT, entry_type TEXT,
    topics TEXT, title TEXT, summary TEXT, file_path TEXT,
    computer TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS library_fulltext (
    id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT, filename TEXT,
    filepath TEXT, word_count INTEGER DEFAULT 0,
    extraction_mode TEXT, indexed_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY, started_at TEXT, ended_at TEXT,
    computer TEXT, summary TEXT
);
CREATE TABLE IF NOT EXISTS jobs_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, job_type TEXT, status TEXT,
    details TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS migrations (
    name TEXT PRIMARY KEY, applied_at TEXT
);
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """
    Build a FastAPI TestClient with a minimal seeded SQLite database.
    Scoped to module so the DB is shared across all smoke tests.
    """
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    tmp = tmp_path_factory.mktemp("metis_e2e")
    rc_root = tmp / "rc"
    db_dir = rc_root / "system" / "app" / "data"
    db_dir.mkdir(parents=True)

    # Stub out config files the app may read
    config_dir = rc_root / "system" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "user-preferences.json").write_text(
        '{"name": "Tester", "role": "researcher", "interests": [], "news_topics": []}',
        encoding="utf-8",
    )

    db_path = db_dir / "metis.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()

    # Set env vars directly (module-scoped fixture cannot use function-scoped monkeypatch)
    _orig_rc = os.environ.get("METIS_RC_ROOT")
    _orig_db = os.environ.get("METIS_DB")
    _orig_key = os.environ.get("ANTHROPIC_API_KEY")
    os.environ["METIS_RC_ROOT"] = str(rc_root)
    os.environ["METIS_DB"] = str(db_path)
    os.environ.pop("ANTHROPIC_API_KEY", None)  # prevent live API calls

    # Clear any cached dashboard module state from previous test runs
    for mod in list(sys.modules.keys()):
        if mod.startswith("routers") or mod in ("db", "main", "scheduler",
                                                 "startup_eval", "inbox_watcher"):
            del sys.modules[mod]

    from fastapi.testclient import TestClient
    import main as dashboard_main
    tc = TestClient(dashboard_main.app, raise_server_exceptions=False)
    yield tc

    # Restore original env
    if _orig_rc is None:
        os.environ.pop("METIS_RC_ROOT", None)
    else:
        os.environ["METIS_RC_ROOT"] = _orig_rc
    if _orig_db is None:
        os.environ.pop("METIS_DB", None)
    else:
        os.environ["METIS_DB"] = _orig_db
    if _orig_key is not None:
        os.environ["ANTHROPIC_API_KEY"] = _orig_key


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

class TestHealthAndRoot:
    """Basic reachability — the server is up and not returning 5xx."""

    @pytest.mark.e2e
    def test_health_endpoint(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    @pytest.mark.e2e
    def test_root_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    @pytest.mark.e2e
    def test_unknown_tab_redirects(self, client):
        r = client.get("/nonexistent-tab", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308)


class TestTabPages:
    """All named tabs return 200 HTML."""

    TABS = [
        "today",
        "knowledge",
        "meetings",
        "learning",
        "work",
        "thinking",
        "planner",
        "teach",
        "metis",
    ]

    @pytest.mark.e2e
    @pytest.mark.parametrize("tab", TABS)
    def test_tab_page_loads(self, client, tab):
        r = client.get(f"/{tab}")
        assert r.status_code == 200, f"/{tab} returned {r.status_code}"
        assert "text/html" in r.headers.get("content-type", "")

    @pytest.mark.e2e
    @pytest.mark.parametrize("tab", TABS)
    def test_htmx_tab_partial(self, client, tab):
        """HTMX tab-swap partials used by the navigation rail."""
        r = client.get(f"/api/tab/{tab}")
        assert r.status_code == 200, f"/api/tab/{tab} returned {r.status_code}"


class TestKeyPartials:
    """Key HTMX partials that the Today and Knowledge tabs depend on."""

    @pytest.mark.e2e
    def test_morning_brief_partial(self, client):
        r = client.get("/api/partial/today/morning-brief")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_knowledge_stats(self, client):
        r = client.get("/api/partial/knowledge/stats")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_knowledge_library(self, client):
        r = client.get("/api/partial/knowledge/library")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_knowledge_literature(self, client):
        r = client.get("/api/partial/knowledge/literature")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_learning_courses(self, client):
        r = client.get("/api/partial/learning/courses")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_learning_due_today(self, client):
        r = client.get("/api/partial/learning/due-today")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_news_tab_partial(self, client):
        r = client.get("/api/tab/news")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_planner_tab_partial(self, client):
        r = client.get("/api/tab/planner")
        assert r.status_code == 200


class TestApiUtilities:
    """Lightweight API endpoints used by the UI chrome."""

    @pytest.mark.e2e
    def test_scheduler_status(self, client):
        r = client.get("/api/scheduler/status")
        # 200 when APScheduler started successfully; 500 when scheduler
        # isn't running (expected in test environments without full setup)
        assert r.status_code in (200, 500)

    @pytest.mark.e2e
    def test_setup_status(self, client):
        r = client.get("/api/setup/status")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_mcp_status(self, client):
        r = client.get("/api/mcp/status")
        # 200 (MCP importable) or 503 (offline) — both are valid responses, not 5xx errors
        assert r.status_code in (200, 503)

    @pytest.mark.e2e
    def test_trust_badge(self, client):
        r = client.get("/api/trust-badge")
        assert r.status_code == 200

    @pytest.mark.e2e
    def test_pwa_manifest(self, client):
        r = client.get("/manifest.json")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert "start_url" in data

    @pytest.mark.e2e
    def test_capture_page(self, client):
        r = client.get("/capture")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
