"""
personas/conftest_personas.py — Shared fixtures for persona tests.

Provides:
  - persona_client(slug)  FastAPI TestClient with seeded DB for a given persona
  - persona_db(slug)      Path to the persona's temp SQLite
  - mcp_tools()           List of registered MCP tool names
  - agent_slugs()         List of agent folder names on disk
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

# Research Cortex root: system/tests/personas/ → parents[3] = RC root
METIS_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = METIS_ROOT / "agents"
MCP_TOOLS_DIR = METIS_ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools"
DASHBOARD_DIR = METIS_ROOT / "system" / "app-py"

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
    source TEXT, source_type TEXT DEFAULT 'news', published_at TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS meetings (
    meeting_id TEXT PRIMARY KEY, title TEXT, date TEXT, transcript TEXT,
    summary TEXT, decisions TEXT, action_items TEXT, status TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY, title TEXT, domain TEXT,
    status TEXT DEFAULT 'active', priority TEXT, next_step TEXT,
    created_at TEXT, external_path TEXT, github_url TEXT,
    launch_cmd TEXT, launcher_type TEXT, launcher_path TEXT
);
CREATE TABLE IF NOT EXISTS daily_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT UNIQUE,
    brief TEXT, created_at TEXT
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
CREATE TABLE IF NOT EXISTS pdf_chunks (
    chunk_id TEXT PRIMARY KEY, doc_path TEXT, domain TEXT,
    chunk_text TEXT, chunk_index INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS pdf_index_state (
    doc_path TEXT PRIMARY KEY, indexed_at TEXT, chunk_count INTEGER
);
"""


def _seed_persona_db(conn: sqlite3.Connection, persona_slug: str) -> None:
    """Insert minimal realistic rows for a persona's typical data state."""
    today = "2026-05-15"

    conn.executescript(f"""
    INSERT OR IGNORE INTO agent_runs VALUES
      ('run-001','{persona_slug}-librarian','Literature search: NTD surveillance 2024',
       '','outputs/reviews/librarian/2026-05-15_ntd.md',120,240,360,'completed','{today} 07:30:00'),
      ('run-002','{persona_slug}-news-radar','Morning brief generated',
       '','outputs/reviews/news-radar/2026-05-15_brief.md',80,160,240,'completed','{today} 07:00:00');

    INSERT OR IGNORE INTO library_cards VALUES
      ('card-001','Systematic review of HAT treatment outcomes',
       'Lutumba P et al.',2023,'neglected-tropical-diseases',
       'Lancet Infect Dis','NTD,HAT,treatment',
       'Review of 12 trials; eflornithine-NIFURTIMOX combination most effective.',
       'reading','{today}'),
      ('card-002','Multilevel modelling in public health',
       'Rabe-Hesketh S, Skrondal A',2022,'statistics',
       'Stata Press','statistics,MLM,multilevel',
       'Comprehensive guide to multilevel models with Stata examples.',
       'unread','{today}');

    INSERT OR IGNORE INTO literature_metadata VALUES
      (1,'Sleeping sickness transmission dynamics','Büscher P et al.',
       2021,'PLoS Negl Trop Dis','10.1371/journal.pntd.0009353',
       'NTD,HAT,transmission','{today}'),
      (2,'OpenStreetMap for health facility mapping','Friesen J et al.',
       2020,'IJHG','10.1186/s12942-020-00218-9',
       'GIS,mapping,health facilities','{today}');

    INSERT OR IGNORE INTO news_briefs VALUES
      (1,'WHO updates HAT elimination targets for 2030',
       'New milestones published in revised roadmap.',
       'WHO','news','{today}','{today}'),
      (2,'New fasciola hepatica prevalence data from West Africa',
       'Cross-sectional survey across 8 countries.',
       'PubMed','article','{today}','{today}');

    INSERT OR IGNORE INTO projects (project_id, title, domain, status, external_path, created_at, launcher_type)
    VALUES
      ('proj-001','Article 1 — HAT Surveillance Senegal','NTD','active',
       'C:/Users/YourName/Documents/research/article1','{today}','rstudio'),
      ('proj-002','PhD Thesis — Backbone','Research','active',
       'C:/Users/YourName/Documents/phd','{today}','vscode');

    INSERT OR IGNORE INTO learning_courses VALUES
      (1,'Statistics for Epidemiology','statistics','statistics-epidemiology',
       33,9,3,'active','{today}'),
      (2,'Applied Multilevel Models','statistics','multilevel-models',
       0,6,0,'active','{today}');

    INSERT OR IGNORE INTO daily_insights VALUES
      (1,'{today}',
       'Three surveillance papers published this week on HAT in central Africa. The WHO roadmap revision sets stricter 2030 targets. Your Article 1 methods section needs the case-definition paragraph reviewed.',
       '{today}');
    """)


@pytest.fixture(scope="session")
def agent_slugs() -> list[str]:
    return sorted([d.name for d in AGENTS_DIR.iterdir() if d.is_dir()])


@pytest.fixture(scope="session")
def mcp_tool_modules() -> list[str]:
    return sorted([
        f.stem for f in MCP_TOOLS_DIR.glob("*.py")
        if f.stem not in ("__init__",)
    ])


def make_persona_client(persona_slug: str, tmp_path: Path, monkeypatch):
    """Build a FastAPI TestClient seeded for a given persona."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    rc_root = tmp_path / "metis_rc"
    db_dir = rc_root / "system" / "app" / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "metis.sqlite"

    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    _seed_persona_db(conn, persona_slug)
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
    return TestClient(dashboard_main.app, raise_server_exceptions=False), db_path
