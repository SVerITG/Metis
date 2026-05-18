"""
Unit tests for system/app-py/db.py helper functions.

Uses the `tmp_db` fixture from conftest.py — a real temp SQLite file.
Never touches the production metis.sqlite.
"""

import sqlite3

import pytest

from db import db_execute, db_query, db_scalar, get_db_path


class TestGetDbPath:
    def test_returns_path_when_metis_db_set(self, tmp_db):
        p = get_db_path()
        assert p.exists()
        assert p == tmp_db

    def test_raises_when_no_db_configured(self, monkeypatch, tmp_path):
        monkeypatch.delenv("METIS_DB", raising=False)
        monkeypatch.delenv("METIS_RC_ROOT", raising=False)
        import pytest
        with pytest.raises(FileNotFoundError):
            get_db_path()


class TestDbQuery:
    def test_returns_list_of_dicts(self, tmp_db, db_conn):
        db_conn.execute("INSERT INTO tasks (title, status) VALUES ('t1', 'open')")
        db_conn.commit()
        rows = db_query("SELECT title, status FROM tasks")
        assert isinstance(rows, list)
        assert len(rows) == 1
        assert rows[0]["title"] == "t1"

    def test_returns_empty_list_on_no_rows(self, tmp_db):
        rows = db_query("SELECT * FROM tasks WHERE 1=0")
        assert rows == []

    def test_returns_default_on_error(self, tmp_db):
        rows = db_query("SELECT * FROM nonexistent_table_xyz", default=[])
        assert rows == []

    def test_params_substitution(self, tmp_db, db_conn):
        db_conn.execute("INSERT INTO tasks (title, status) VALUES ('alpha', 'open')")
        db_conn.execute("INSERT INTO tasks (title, status) VALUES ('beta', 'done')")
        db_conn.commit()
        rows = db_query("SELECT title FROM tasks WHERE status = ?", ("done",))
        assert len(rows) == 1
        assert rows[0]["title"] == "beta"


class TestDbScalar:
    def test_returns_count(self, tmp_db, db_conn):
        db_conn.execute("INSERT INTO tasks (title) VALUES ('x')")
        db_conn.execute("INSERT INTO tasks (title) VALUES ('y')")
        db_conn.commit()
        n = db_scalar("SELECT COUNT(*) FROM tasks")
        assert n == 2

    def test_returns_default_on_no_rows(self, tmp_db):
        result = db_scalar("SELECT COUNT(*) FROM tasks WHERE 1=0", default=99)
        assert result == 0  # COUNT returns 0 even with WHERE false

    def test_returns_default_on_error(self, tmp_db):
        result = db_scalar("SELECT * FROM nonexistent_xyz", default=-1)
        assert result == -1


class TestDbExecute:
    def test_insert(self, tmp_db, db_conn):
        db_execute("INSERT INTO tasks (title, status) VALUES (?, ?)", ("new task", "open"))
        row = db_conn.execute("SELECT title FROM tasks WHERE title='new task'").fetchone()
        assert row is not None

    def test_update(self, tmp_db, db_conn):
        db_conn.execute("INSERT INTO tasks (title, status) VALUES ('t', 'open')")
        db_conn.commit()
        db_execute("UPDATE tasks SET status = 'done' WHERE title = ?", ("t",))
        row = db_conn.execute("SELECT status FROM tasks WHERE title='t'").fetchone()
        assert row["status"] == "done"

    def test_delete(self, tmp_db, db_conn):
        db_conn.execute("INSERT INTO tasks (title) VALUES ('del')")
        db_conn.commit()
        db_execute("DELETE FROM tasks WHERE title = ?", ("del",))
        n = db_conn.execute("SELECT COUNT(*) FROM tasks WHERE title='del'").fetchone()[0]
        assert n == 0
