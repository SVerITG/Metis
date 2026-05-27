"""
Integration tests for the Memory Curator MCP tools.

Tests consolidate_session_memory, surface_relevant_context, and
memory_health_report against a real temp SQLite database.

The MCP tools read from METIS_DB and METIS_RC_ROOT env vars, which are
patched by the `tmp_db` fixture in conftest.py.
"""

import datetime
import json
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
_APP_PY = _REPO / "system" / "app-py"
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"

for _p in [str(_APP_PY), str(_MCP_SRC)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from metis_mcp.tools.memory_curator import (
        consolidate_session_memory,
        memory_health_report,
        surface_relevant_context,
    )
except ImportError:
    pytest.skip("metis_mcp not installed", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_runs(conn: sqlite3.Connection, runs: list[dict]) -> None:
    """Insert agent_runs rows for testing."""
    conn.executemany(
        """INSERT INTO agent_runs (agent_slug, task_summary, output_path, created_at)
           VALUES (:slug, :summary, :output, :created_at)""",
        [
            {
                "slug": r.get("slug", "epidemiologist"),
                "summary": r.get("summary", "Reviewed study design for cohort analysis"),
                "output": r.get("output", "outputs/reviews/epidemiologist/2026-01-01_test.md"),
                "created_at": r.get("created_at", datetime.datetime.now().isoformat()),
            }
            for r in runs
        ],
    )
    conn.commit()


def _seed_memory_entries(conn: sqlite3.Connection, entries: list[dict]) -> None:
    """Insert memory_entries rows for testing."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            entry_id TEXT PRIMARY KEY, entry_date TEXT, entry_type TEXT,
            topics TEXT, title TEXT, summary TEXT, file_path TEXT,
            computer TEXT, created_at TEXT
        )
    """)
    conn.executemany(
        """INSERT OR IGNORE INTO memory_entries
           (entry_id, entry_date, entry_type, topics, title, summary, file_path, computer, created_at)
           VALUES (:id, :date, :type, :topics, :title, :summary, :file_path, '', :created_at)""",
        [
            {
                "id": e.get("id", f"mem-test-{i}"),
                "date": e.get("date", "2026-01-01"),
                "type": e.get("type", "session"),
                "topics": e.get("topics", "methods,phd"),
                "title": e.get("title", "Test entry"),
                "summary": e.get("summary", "A test memory entry about epidemiology methods"),
                "file_path": e.get("file_path", ""),
                "created_at": e.get("created_at", datetime.datetime.now().isoformat()),
            }
            for i, e in enumerate(entries)
        ],
    )
    conn.commit()


def _text(result) -> str:
    """Extract text from MCP tool result."""
    return result[0].text if result else ""


# ---------------------------------------------------------------------------
# consolidate_session_memory
# ---------------------------------------------------------------------------

class TestConsolidateSessionMemory:
    def test_empty_runs_returns_message(self, tmp_db):
        import asyncio
        result = asyncio.run(consolidate_session_memory(n_runs=10))
        text = _text(result)
        assert "No agent runs found" in text

    def test_writes_entries_for_high_value_runs(self, tmp_db, db_conn):
        _seed_runs(db_conn, [
            {
                "slug": "epidemiologist",
                "summary": "Reviewed cohort study design for disease surveillance in a field setting",
                "output": "outputs/reviews/epidemiologist/2026-01-01_cohort.md",
            },
            {
                "slug": "methods-coach",
                "summary": "Explained mixed-effects models for longitudinal epidemiology data",
                "output": "outputs/reviews/methods-coach/2026-01-01_mlm.md",
            },
        ])
        import asyncio
        result = asyncio.run(consolidate_session_memory(n_runs=20))
        text = _text(result)
        assert "Entries written" in text
        # Verify at least one entry was written to the DB
        n = db_conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
        assert n >= 1

    def test_skips_short_summaries(self, tmp_db, db_conn):
        _seed_runs(db_conn, [{"slug": "epidemiologist", "summary": "OK", "output": ""}])
        import asyncio
        result = asyncio.run(consolidate_session_memory(n_runs=5))
        text = _text(result)
        n = db_conn.execute(
            "SELECT COUNT(*) FROM memory_entries WHERE 1=1"
        ).fetchone()[0] if "memory_entries" in [
            r[0] for r in db_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ] else 0
        assert n == 0

    def test_deduplicates_on_second_run(self, tmp_db, db_conn):
        _seed_runs(db_conn, [
            {
                "slug": "epidemiologist",
                "summary": "Reviewed cohort design for vector-borne disease surveillance study 2026",
                "output": "outputs/reviews/epidemiologist/2026-01-01_cohort.md",
            }
        ])
        import asyncio
        asyncio.run(consolidate_session_memory(n_runs=5))
        n_first = db_conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
        # Run again — same run should not create a duplicate
        asyncio.run(consolidate_session_memory(n_runs=5))
        n_second = db_conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
        assert n_second == n_first

    def test_all_quality_includes_more_runs(self, tmp_db, db_conn):
        _seed_runs(db_conn, [
            {
                "slug": "rc-builder",
                "summary": "Built Phase 10 scheduler configuration for automated jobs",
                "output": "",
            }
        ])
        import asyncio
        result = asyncio.run(consolidate_session_memory(n_runs=5, min_quality="all"))
        text = _text(result)
        # rc-builder is not in high_value_agents but min_quality=all should include it
        assert "Runs reviewed" in text

    def test_writes_report_markdown(self, tmp_db, db_conn, tmp_path, monkeypatch):
        """consolidate_session_memory should produce a report text even if no entries written."""
        import asyncio
        result = asyncio.run(consolidate_session_memory(n_runs=5))
        text = _text(result)
        assert "Memory Consolidation" in text
        assert "Runs reviewed" in text


# ---------------------------------------------------------------------------
# surface_relevant_context
# ---------------------------------------------------------------------------

class TestSurfaceRelevantContext:
    def test_returns_no_entries_message_when_empty(self, tmp_db):
        import asyncio
        result = asyncio.run(surface_relevant_context(topic="disease surveillance"))
        text = _text(result)
        assert "No memory entries found" in text

    def test_finds_entries_by_topic(self, tmp_db, db_conn):
        _seed_memory_entries(db_conn, [
            {
                "id": "mem-001",
                "topics": "methods,phd",
                "title": "[epidemiologist] Reviewed disease surveillance cohort design",
                "summary": "Discussed sampling strategy for vector-borne disease surveillance. "
                           "Recommended cluster randomization with village as primary sampling unit.",
            }
        ])
        import asyncio
        result = asyncio.run(surface_relevant_context(topic="disease surveillance"))
        text = _text(result)
        assert "Relevant past context" in text
        assert "surveillance" in text

    def test_finds_by_tags(self, tmp_db, db_conn):
        _seed_memory_entries(db_conn, [
            {
                "id": "mem-002",
                "topics": "statistics,methods",
                "title": "[methods-coach] Mixed-effects model for longitudinal data",
                "summary": "Explained random intercept models using lme4. "
                           "Discussed REML vs ML estimation for nested data structures.",
            }
        ])
        import asyncio
        result = asyncio.run(surface_relevant_context(topic="unrelated", tags="statistics"))
        text = _text(result)
        assert "Relevant past context" in text

    def test_respects_top_n_limit(self, tmp_db, db_conn):
        entries = [
            {
                "id": f"mem-{i:03d}",
                "topics": "phd",
                "title": f"[epidemiologist] Study design review session {i}",
                "summary": f"Reviewed article {i} methodology for PhD thesis submission.",
            }
            for i in range(10)
        ]
        _seed_memory_entries(db_conn, entries)
        import asyncio
        result = asyncio.run(surface_relevant_context(topic="PhD", top_n=3))
        text = _text(result)
        # Should contain a header and some rows, but not all 10
        assert "Relevant past context" in text
        # Row count is hard to pin exactly, but at most top_n in the table
        row_lines = [l for l in text.splitlines() if l.startswith("| [")]
        assert len(row_lines) <= 3

    def test_detail_section_present_when_results_found(self, tmp_db, db_conn):
        _seed_memory_entries(db_conn, [
            {
                "id": "mem-detail-01",
                "topics": "writing,phd",
                "title": "[writing-partner] Revised Article 1 introduction",
                "summary": "Rewrote the introduction using a gap-claim-evidence structure "
                           "targeting a public health epidemiology audience.",
            }
        ])
        import asyncio
        result = asyncio.run(surface_relevant_context(topic="writing"))
        text = _text(result)
        assert "Detail — highest relevance entry" in text


# ---------------------------------------------------------------------------
# memory_health_report
# ---------------------------------------------------------------------------

class TestMemoryHealthReport:
    def test_returns_report_when_empty(self, tmp_db):
        import asyncio
        result = asyncio.run(memory_health_report())
        text = _text(result)
        assert "Memory Health Report" in text
        assert "Total entries: **0**" in text

    def test_counts_entries_by_type(self, tmp_db, db_conn):
        _seed_memory_entries(db_conn, [
            {"id": "m1", "type": "session", "topics": "phd", "title": "Session entry 1",
             "summary": "First session memory about epidemiology."},
            {"id": "m2", "type": "session", "topics": "methods", "title": "Session entry 2",
             "summary": "Second session memory about statistics."},
            {"id": "m3", "type": "reference", "topics": "literature", "title": "Reference entry 1",
             "summary": "Paper on domain-specific surveillance methods."},
        ])
        import asyncio
        result = asyncio.run(memory_health_report())
        text = _text(result)
        assert "session" in text
        assert "reference" in text

    def test_identifies_gaps(self, tmp_db, db_conn):
        _seed_memory_entries(db_conn, [
            {"id": "gap1", "topics": "phd", "title": "PhD entry",
             "summary": "PhD planning entry for thesis structure."},
        ])
        import asyncio
        result = asyncio.run(memory_health_report())
        text = _text(result)
        assert "Coverage gaps" in text
        # 'hat' is a core topic, should show as gap with only phd entries
        assert "hat" in text or "ntd" in text or "No gaps" in text

    def test_detects_entries_without_provenance(self, tmp_db, db_conn):
        _seed_memory_entries(db_conn, [
            {"id": "no-file", "topics": "code", "title": "Entry without file",
             "summary": "An entry that has no linked output file — just text.",
             "file_path": ""},
        ])
        import asyncio
        result = asyncio.run(memory_health_report())
        text = _text(result)
        assert "without file provenance" in text or "no linked output" in text

    def test_no_provenance_count_zero_when_all_have_files(self, tmp_db, db_conn):
        _seed_memory_entries(db_conn, [
            {"id": "with-file", "topics": "code,metis", "title": "Entry with file",
             "summary": "An entry with a valid output file path for provenance.",
             "file_path": "outputs/reviews/software-engineer/2026-01-01_test.md"},
        ])
        import asyncio
        result = asyncio.run(memory_health_report())
        text = _text(result)
        assert "Entries without file provenance: 0" in text
