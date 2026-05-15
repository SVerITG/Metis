"""
Shared fixtures for the Metis test suite.

Three fixture scopes:
  - tmp_db          in-memory SQLite seeded with minimal schema (unit tests)
  - dashboard_app   FastAPI TestClient with a temp DB (integration tests)
  - repo_root       Path to the git repo root (used by privacy/scrub tests)
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the git repository root."""
    here = Path(__file__).resolve()
    # Walk up until we find .git
    for parent in [here, *here.parents]:
        if (parent / ".git").exists():
            return parent
    pytest.skip("Not inside a git repository")


@pytest.fixture(scope="session")
def metis_root(repo_root: Path) -> Path:
    return repo_root / "metis"


# ---------------------------------------------------------------------------
# In-memory SQLite (unit tests)
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ideas (
    idea_id TEXT PRIMARY KEY,
    title TEXT,
    body TEXT,
    tags TEXT,
    status TEXT DEFAULT 'open',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    title TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    project TEXT,
    due_date TEXT,
    created_at TEXT
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
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id TEXT PRIMARY KEY,
    agent_slug TEXT,
    summary TEXT,
    input_path TEXT,
    output_path TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS reflexions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    agent_slug TEXT,
    went_well TEXT,
    could_improve TEXT,
    missing_context TEXT,
    tool_wishes TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS library_cards (
    card_id TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,
    year INTEGER,
    source TEXT,
    status TEXT DEFAULT 'unread',
    created_at TEXT
);
"""


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """SQLite database with minimal Metis schema, in a temp directory."""
    db_path = tmp_path / "metis.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA_SQL)
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def dashboard_client(tmp_db: Path, monkeypatch):
    """FastAPI TestClient with METIS_RC_ROOT wired to a temp dir."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    # Set env so db.py finds the temp SQLite
    tmp_root = tmp_db.parent.parent  # tmp_path
    rc_root = tmp_root / "metis_rc"
    db_dir = rc_root / "system" / "app" / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy(str(tmp_db), str(db_dir / "metis.sqlite"))

    monkeypatch.setenv("METIS_RC_ROOT", str(rc_root))

    # Import app only after env is set
    import importlib
    import sys
    # Ensure routers are re-imported with the patched env
    for mod in list(sys.modules.keys()):
        if mod.startswith("routers") or mod == "db":
            del sys.modules[mod]

    from fastapi.testclient import TestClient
    # Add dashboard dir to path so 'main' is importable
    dashboard_dir = Path(__file__).parent.parent / "app-py"
    if str(dashboard_dir) not in sys.path:
        sys.path.insert(0, str(dashboard_dir))

    import main as dashboard_main
    client = TestClient(dashboard_main.app, raise_server_exceptions=False)
    yield client
