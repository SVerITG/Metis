"""
Shared pytest fixtures for the Metis test suite.

All tests that need a database use the `tmp_db` fixture, which creates a
fresh in-memory or temp-file SQLite database and sets METIS_DB so that
db.py helpers and MCP tools pick it up automatically.

No test should connect to the production metis.sqlite.
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# ── Make app-py and mcp-server importable ──────────────────────────────────
_REPO = Path(__file__).parent.parent
_APP_PY = _REPO / "system" / "app-py"
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"

for _p in [str(_APP_PY), str(_MCP_SRC)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── Minimal DDL — tables needed by most tests ──────────────────────────────

_CORE_DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_slug TEXT NOT NULL DEFAULT '',
    task_summary TEXT NOT NULL DEFAULT '',
    input_path TEXT DEFAULT '',
    output_path TEXT DEFAULT '',
    status TEXT DEFAULT 'completed',
    created_at TEXT NOT NULL DEFAULT '',
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    model TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS memory_entries (
    entry_id TEXT PRIMARY KEY,
    entry_date TEXT,
    entry_type TEXT,
    topics TEXT,
    title TEXT,
    summary TEXT,
    file_path TEXT,
    computer TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS news_briefs (
    brief_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    summary TEXT,
    domain TEXT,
    signal_strength INTEGER,
    source_url TEXT,
    source_type TEXT,
    created_at TEXT,
    brief_date TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    status TEXT,
    priority TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS library_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    title TEXT,
    status TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    client TEXT,
    computer TEXT,
    started_at TEXT,
    last_active TEXT
);
CREATE TABLE IF NOT EXISTS jobs_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT,
    status TEXT,
    details TEXT,
    created_at TEXT
);
"""


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Create a temp SQLite DB with core schema and point METIS_DB at it.

    Yields the Path to the database file so tests can connect directly if
    needed. The METIS_DB env var is restored after each test.
    """
    db_path = tmp_path / "test_metis.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_CORE_DDL)
    conn.commit()
    conn.close()

    monkeypatch.setenv("METIS_DB", str(db_path))
    monkeypatch.setenv("METIS_RC_ROOT", str(_REPO))
    # The config `paths` singleton computed its db path at import time (before this
    # fixture set METIS_DB), so MCP tools that read `paths.db` would still hit the
    # real DB. Point the singleton at the temp DB too, so every tool isolates.
    try:
        from metis_mcp.config import paths as _paths
        monkeypatch.setattr(_paths, "db", db_path)
    except Exception:
        pass
    yield db_path


@pytest.fixture()
def db_conn(tmp_db):
    """Open a direct sqlite3 connection to the temp DB for setup/assertions."""
    conn = sqlite3.connect(str(tmp_db))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
