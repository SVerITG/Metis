"""
Integration tests for the Metis dashboard FastAPI routes.

Uses httpx AsyncClient (via fastapi.testclient.TestClient) to hit every
tab route and key API endpoint without a running server.

All 9 tabs must return 200 OK with HTML content.
Key API endpoints must return 200 with the expected content-type.
"""

import os
import sys
from pathlib import Path

import pytest

_APP_PY = Path(__file__).parent.parent.parent / "system" / "app-py"
if str(_APP_PY) not in sys.path:
    sys.path.insert(0, str(_APP_PY))

# fastapi TestClient is synchronous
try:
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("fastapi not installed", allow_module_level=True)


@pytest.fixture(scope="function")
def client(tmp_path_factory, monkeypatch):
    """Create a TestClient for the Metis dashboard app."""
    db_path = tmp_path_factory.mktemp("data") / "test.sqlite"

    # Create minimal schema
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_runs (run_id INTEGER PRIMARY KEY AUTOINCREMENT, agent_slug TEXT NOT NULL DEFAULT '', task_summary TEXT NOT NULL DEFAULT '', input_path TEXT DEFAULT '', output_path TEXT DEFAULT '', status TEXT DEFAULT 'completed', created_at TEXT NOT NULL DEFAULT '', input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0, model TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS news_briefs (brief_id INTEGER PRIMARY KEY, title TEXT, summary TEXT, domain TEXT, source_url TEXT, source_type TEXT, created_at TEXT, signal_strength INTEGER, surprise_flag INTEGER, brief_date TEXT);
        CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT, priority TEXT, created_at TEXT, project_id TEXT, due_date TEXT, description TEXT);
        CREATE TABLE IF NOT EXISTS library_cards (id INTEGER PRIMARY KEY, title TEXT, authors TEXT, year INTEGER, domain TEXT, tags TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS ideas (id INTEGER PRIMARY KEY, text TEXT, created_at TEXT, project_id TEXT);
        CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, title TEXT, status TEXT, description TEXT, created_at TEXT, next_step TEXT, external_path TEXT);
        CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, client TEXT, computer TEXT, started_at TEXT, last_active TEXT);
        CREATE TABLE IF NOT EXISTS jobs_log (id INTEGER PRIMARY KEY, job_type TEXT, status TEXT, details TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS memory_entries (entry_id TEXT PRIMARY KEY, entry_date TEXT, entry_type TEXT, topics TEXT, title TEXT, summary TEXT, file_path TEXT, computer TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS personal_notes (id INTEGER PRIMARY KEY, content TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS user_config (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS daily_insights (id INTEGER PRIMARY KEY, insight_date TEXT, content TEXT, model TEXT, generated_at TEXT);
        CREATE TABLE IF NOT EXISTS meetings (id INTEGER PRIMARY KEY, title TEXT, meeting_date TEXT, created_at TEXT, summary TEXT);
        CREATE TABLE IF NOT EXISTS learning_courses (id INTEGER PRIMARY KEY, title TEXT, slug TEXT, category TEXT, progress_pct INTEGER, total_modules INTEGER, completed_modules INTEGER, status TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS competencies (id INTEGER PRIMARY KEY, name TEXT, level INTEGER, domain TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS news_topic_summaries (id INTEGER PRIMARY KEY, period TEXT, domain TEXT, summary TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS literature_metadata (id INTEGER PRIMARY KEY, title TEXT, authors TEXT, year INTEGER, journal TEXT, doi TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS open_questions (id INTEGER PRIMARY KEY, question TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS brainstorm_sessions (id INTEGER PRIMARY KEY, topic TEXT, created_at TEXT);
    """)
    conn.commit()
    conn.close()

    monkeypatch.setenv("METIS_DB", str(db_path))
    monkeypatch.setenv("METIS_RC_ROOT", str(Path(__file__).parent.parent.parent))

    os.chdir(str(_APP_PY))
    from main import app
    return TestClient(app, raise_server_exceptions=False)


_TAB_ROUTES = [
    "/",
    "/today",
    "/knowledge",
    "/meetings",
    "/learning",
    "/work",
    "/thinking",
    "/planner",
    "/teach",
    "/metis",
]

@pytest.mark.parametrize("route", _TAB_ROUTES)
def test_tab_route_returns_200(client, route):
    resp = client.get(route)
    assert resp.status_code == 200, f"{route} returned {resp.status_code}"
    assert "text/html" in resp.headers.get("content-type", "")


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"


def test_unknown_tab_redirects(client):
    resp = client.get("/nonexistent-tab-xyz", follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_static_files_served(client):
    # app.js should be served from /static/
    resp = client.get("/static/app.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers.get("content-type", "")


_PARTIAL_ROUTES = [
    "/api/partial/today/dateline",
    "/api/partial/today/focus-thread",
    "/api/partial/today/activity-feed",
]

@pytest.mark.parametrize("route", _PARTIAL_ROUTES)
def test_partial_returns_html(client, route):
    resp = client.get(route)
    # Partials may return 200 with HTML or gracefully return empty fragment
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
