"""record_decision must work on a database the installer built.

schema.sql declares user_decisions.created_at NOT NULL with no default; the
insert relied on a default, so every recorded decision failed there.
"""
import sqlite3


def test_record_decision_on_installer_schema(tmp_path, monkeypatch):
    from metis_mcp.config import paths
    from metis_mcp.tools import pipeline

    db = tmp_path / "t.sqlite"
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE user_decisions (
        decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT DEFAULT '', decision TEXT NOT NULL, context TEXT DEFAULT '',
        scope TEXT DEFAULT 'always', source TEXT DEFAULT 'user',
        hits INTEGER DEFAULT 0, created_at TEXT NOT NULL,
        agent_slug TEXT DEFAULT '', supersedes INTEGER,
        last_applied_at TEXT DEFAULT '')""")
    con.commit()
    con.close()
    monkeypatch.setattr(paths, "db", db)

    out = pipeline.record_decision("Report rates, never raw counts.", category="methods")
    assert out.startswith("Recorded")
    con = sqlite3.connect(db)
    row = con.execute("SELECT decision, created_at FROM user_decisions").fetchone()
    con.close()
    assert row[0] == "Report rates, never raw counts." and row[1]
