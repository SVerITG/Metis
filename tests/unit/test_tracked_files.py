"""
Regression tests for the MCP file-tracking tools (system/mcp-server/.../tools/files.py).

Guards against BUG-TRACKFILE (found 2026-06-04): `_ensure_tracked_files` used to
call *itself* instead of running the CREATE TABLE DDL, so every file-tracking entry
point (add_tracked_file, connect_project_folder, scan_tracked_files) crashed with
"maximum recursion depth exceeded" on the first line, for any input. The bug had been
present since the file was created (commit 87523ee, 2026-04-13).

Uses the `tmp_db` fixture from conftest.py — never touches production metis.sqlite.
"""

import asyncio
import sqlite3


def _run(coro):
    return asyncio.run(coro)


class TestEnsureTrackedFiles:
    def test_does_not_recurse_and_creates_table(self, tmp_db):
        """The original bug: infinite self-recursion. This must return normally
        and leave a usable tracked_files table with the migrated columns."""
        from metis_mcp.tools.files import _ensure_tracked_files

        conn = sqlite3.connect(str(tmp_db))
        conn.row_factory = sqlite3.Row
        try:
            _ensure_tracked_files(conn)  # would raise RecursionError before the fix
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(tracked_files)")}
        finally:
            conn.close()

        assert {"path", "last_modified", "last_scanned", "label", "watch"} <= cols

    def test_idempotent(self, tmp_db):
        """Calling it twice (e.g. two add_tracked_file calls in a row) is safe."""
        from metis_mcp.tools.files import _ensure_tracked_files

        conn = sqlite3.connect(str(tmp_db))
        conn.row_factory = sqlite3.Row
        try:
            _ensure_tracked_files(conn)
            _ensure_tracked_files(conn)
        finally:
            conn.close()


class TestAddTrackedFile:
    def test_tracks_a_real_file(self, tmp_db, tmp_path, db_conn):
        from metis_mcp.tools.files import add_tracked_file

        target = tmp_path / "analysis.R"
        target.write_text("# fuzzy matching\n", encoding="utf-8")

        result = _run(add_tracked_file(path=str(target), label="my-project"))
        assert "Now tracking" in result[0].text

        row = db_conn.execute(
            "SELECT label, watch FROM tracked_files WHERE path = ?", (str(target),)
        ).fetchone()
        assert row is not None
        assert row["label"] == "my-project"
        assert row["watch"] == 1

    def test_missing_file_reports_cleanly(self, tmp_db, tmp_path):
        from metis_mcp.tools.files import add_tracked_file

        result = _run(add_tracked_file(path=str(tmp_path / "nope.R")))
        assert "File not found" in result[0].text

    def test_retrack_updates_label(self, tmp_db, tmp_path, db_conn):
        """ON CONFLICT path — re-adding keeps one row and updates the label."""
        from metis_mcp.tools.files import add_tracked_file

        target = tmp_path / "data.csv"
        target.write_text("a,b\n1,2\n", encoding="utf-8")

        _run(add_tracked_file(path=str(target), label="first"))
        _run(add_tracked_file(path=str(target), label="second"))

        rows = db_conn.execute(
            "SELECT label FROM tracked_files WHERE path = ?", (str(target),)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["label"] == "second"
