"""Two computers, one Metis: the sync must leave both databases identical.

Every scenario here was a real failure of the append-only merger it replaced:
TEXT ids arriving as NULL, edits arriving as duplicates, deletions and Today
verdicts never arriving, and whole tables (tasks, preferences) never syncing.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import metis_sync as ms  # noqa: E402


@pytest.fixture(scope="module")
def schema_db(tmp_path_factory) -> Path:
    """A database with the real schema, built once."""
    path = tmp_path_factory.mktemp("schema") / "schema.sqlite"
    os.environ.setdefault("METIS_RC_ROOT", str(ROOT))
    sys.path.insert(0, str(ROOT / "system" / "app-py"))
    sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))
    db = importlib.import_module("db")
    orig = db.get_db_path
    db.get_db_path = lambda: path
    try:
        db.run_migrations()
    finally:
        db.get_db_path = orig
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.close()
    return path


@pytest.fixture
def world(tmp_path, schema_db):
    d = tmp_path / "onedrive"
    d.mkdir()
    p, s = tmp_path / "P.sqlite", tmp_path / "S.sqlite"
    shutil.copy(schema_db, p)
    shutil.copy(schema_db, s)
    return d, p, s


def run(con_path: Path, sql: str, params=()):
    con = sqlite3.connect(con_path)
    con.execute(sql, params)
    con.commit()
    con.close()


def one(con_path: Path, sql: str, params=()):
    con = sqlite3.connect(con_path)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def dump(path: Path) -> dict:
    con = sqlite3.connect(path)
    out = {}
    for name, sql in ms.synced_tables(con).items():
        t = ms.describe(con, "main", name, sql)
        cols = ",".join(ms._q(c) for c in sorted(t.cols))
        rid = "rowid," if t.has_rowid else ""
        out[name] = sorted(map(repr, con.execute(f"SELECT {rid}{cols} FROM {ms._q(name)}")))
    con.close()
    return out


def cycle(d, p, s):
    """S publishes, P merges and publishes, S rebases."""
    reports = [ms.sync(s, d, "S", files_root=None), ms.sync(p, d, "P", files_root=None), ms.sync(s, d, "S", files_root=None)]
    for r in reports:
        assert not [x for x in r.problems if "stopped" in x], r.problems
    return reports


def seed_divergent(p, s):
    # Shared history: both computers once had task t1 and run 1.
    for db in (p, s):
        run(db, "INSERT INTO tasks (task_id, title, status, project_id) VALUES ('t1','write','open','x')")
        run(db, "INSERT INTO news_briefs (brief_id, title, created_at) VALUES ('b1','Story','2026-10-01')")
    # P's own
    run(p, "INSERT INTO ideas (idea_id, text, created_at) VALUES ('i1','idea on P','2026-10-01')")
    run(p, "INSERT INTO agent_runs (agent_slug, task_summary, status, created_at) "
           "VALUES ('librarian','P run','done','2026-10-01T10:00')")
    # S's own — including a verdict on the shared story, and a run that collides
    run(s, "UPDATE news_briefs SET seen_at='2026-10-02' WHERE brief_id='b1'")
    run(s, "INSERT INTO tasks (task_id, title, status, project_id) VALUES ('t2','only on S','open','x')")
    run(s, "INSERT INTO ideas (idea_id, text, created_at) VALUES ('i2','idea on S','2026-10-01')")
    run(s, "INSERT INTO agent_runs (agent_slug, task_summary, status, created_at) "
           "VALUES ('critic','S run','done','2026-10-01T11:00')")
    run(s, "INSERT INTO focus_verdict (slug, kind, item_id, verdict, created_at) "
           "VALUES ('f','news','b1','keep','2026-10-02')")


def test_first_sync_converges_with_primary_winning(world):
    d, p, s = world
    seed_divergent(p, s)
    run(p, "UPDATE tasks SET status='open' WHERE task_id='t1'")
    run(s, "UPDATE tasks SET status='done' WHERE task_id='t1'")
    ms.make_primary(d, "P")
    ms.sync(p, d, "P", files_root=None)
    cycle(d, p, s)

    assert dump(p) == dump(s), "the two computers differ after a full cycle"
    assert one(p, "SELECT status FROM tasks WHERE task_id='t1'") == [("open",)]  # primary wins
    assert one(p, "SELECT title FROM tasks WHERE task_id='t2'") == [("only on S",)]
    assert {r[0] for r in one(p, "SELECT idea_id FROM ideas")} == {"i1", "i2"}
    assert one(p, "SELECT seen_at FROM news_briefs WHERE brief_id='b1'") == [("2026-10-02",)]
    assert one(p, "SELECT verdict FROM focus_verdict WHERE item_id='b1'") == [("keep",)]
    runs = {r[0] for r in one(p, "SELECT task_summary FROM agent_runs")}
    assert runs == {"P run", "S run"}, "a colliding id must be renumbered, not overwritten"
    assert one(p, "SELECT COUNT(*) FROM ideas WHERE idea_id IS NULL") == [(0,)]


def test_edits_deletes_and_collisions_travel_both_ways(world):
    d, p, s = world
    seed_divergent(p, s)
    ms.make_primary(d, "P")
    ms.sync(p, d, "P", files_root=None)
    cycle(d, p, s)
    ms.sync(p, d, "P", files_root=None)
    assert dump(p) == dump(s)

    # Both computers work between syncs.
    run(p, "UPDATE ideas SET text='edited on P' WHERE idea_id='i1'")
    run(p, "INSERT INTO agent_runs (agent_slug, task_summary, status, created_at) "
           "VALUES ('librarian','P second','done','2026-10-03T09:00')")
    run(s, "UPDATE tasks SET status='done' WHERE task_id='t2'")
    run(s, "DELETE FROM ideas WHERE idea_id='i2'")
    run(s, "UPDATE news_briefs SET seen_at='2026-10-03' WHERE brief_id='b1'")
    con = sqlite3.connect(s)
    rid = con.execute("INSERT INTO agent_runs (agent_slug, task_summary, status, created_at) "
                      "VALUES ('critic','S second','done','2026-10-03T09:05')").lastrowid
    con.execute("INSERT INTO agent_spans (span_id, run_id, name, start_ms) VALUES ('sp1', ?, 'step', 0)", (rid,))
    con.commit()
    con.close()

    cycle(d, p, s)
    ms.sync(p, d, "P", files_root=None)
    assert dump(p) == dump(s), "the two computers differ after concurrent work"

    assert one(s, "SELECT text FROM ideas WHERE idea_id='i1'") == [("edited on P",)]
    assert one(p, "SELECT status FROM tasks WHERE task_id='t2'") == [("done",)]
    assert one(p, "SELECT COUNT(*) FROM ideas WHERE idea_id='i2'") == [(0,)], "deletion did not travel"
    assert one(p, "SELECT seen_at FROM news_briefs WHERE brief_id='b1'") == [("2026-10-03",)]
    # The span still points at S's run, wherever that run ended up.
    assert one(p, "SELECT r.task_summary FROM agent_spans s JOIN agent_runs r "
                  "ON r.run_id = s.run_id WHERE s.span_id='sp1'") == [("S second",)]

    # Nothing left to do: a second pass changes nothing anywhere.
    again = [ms.sync(s, d, "S", files_root=None), ms.sync(p, d, "P", files_root=None), ms.sync(s, d, "S", files_root=None)]
    assert sum(r.changed for r in again) == 0
    assert dump(p) == dump(s)


def test_an_edit_made_before_rebasing_is_not_lost(world):
    """S edits a row the primary already merged, before S has seen the primary's
    newer snapshot. Read against the old base that edit looks like a new row."""
    d, p, s = world
    ms.make_primary(d, "P")
    ms.sync(p, d, "P", files_root=None)
    cycle(d, p, s)
    run(s, "INSERT INTO personal_notes (note_id, title, content, created_at, updated_at) "
           "VALUES ('n1','note','first','2026-10-04','2026-10-04')")
    ms.sync(s, d, "S", files_root=None)
    ms.sync(p, d, "P", files_root=None)                       # P merges the note, publishes
    held = d.parent / "held"
    held.mkdir()
    newest_p = [x for x in ms.list_snaps(d) if x.host == "P"][-1]
    shutil.move(str(newest_p.path), held / newest_p.name)   # OneDrive has not delivered it yet
    run(s, "UPDATE personal_notes SET content='second' WHERE note_id='n1'")
    ms.sync(s, d, "S", files_root=None)                       # publishes again on the old base
    shutil.move(str(held / newest_p.name), newest_p.path)
    ms.sync(p, d, "P", files_root=None)
    assert one(p, "SELECT content FROM personal_notes WHERE note_id='n1'") == [("second",)]
    ms.sync(s, d, "S", files_root=None)
    assert dump(p) == dump(s)


def test_silence_is_reported(world):
    d, p, s = world
    r = ms.sync(p, d, "P", files_root=None)
    assert any("main computer" in x for x in r.problems), "an unassigned primary must be loud"
    ms.make_primary(d, "P")
    r = ms.sync(p, d, "P", files_root=None)
    assert any("nothing from another computer" in x for x in r.problems)


def _cleanup_module():
    spec = importlib.util.spec_from_file_location(
        "metis_sync_cleanup", ROOT / "tools" / "metis-sync-cleanup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cleanup_repairs_what_the_old_merger_left(tmp_path, schema_db):
    import importlib.util  # noqa: F401
    db = tmp_path / "live.sqlite"
    shutil.copy(schema_db, db)
    snapdir = tmp_path / "onedrive"
    snapdir.mkdir()
    other = snapdir / "metis-OTHER-20261001-120000.sqlite"
    shutil.copy(schema_db, other)
    run(other, "INSERT INTO ideas (idea_id, text, created_at) VALUES ('idea-abcdef123456','from other','2026-10-01')")

    run(db, "INSERT INTO ideas (idea_id, text, created_at) VALUES ('idea-111111111111','twin','2026-10-01')")
    run(db, "INSERT INTO ideas (idea_id, text, created_at) VALUES (NULL,'twin','2026-10-01')")
    run(db, "INSERT INTO ideas (idea_id, text, created_at) VALUES (NULL,'from other','2026-10-01')")
    run(db, "INSERT INTO ideas (idea_id, text, created_at) VALUES (NULL,'orphan','2026-10-01')")
    run(db, "INSERT INTO literature_metadata (title, doi, is_read) VALUES ('Paper','10.1/x',0)")
    run(db, "INSERT INTO literature_metadata (title, doi, is_read, read_at) VALUES ('Paper','10.1/x',1,'2026-10-02')")
    run(db, "INSERT INTO agent_runs (agent_slug, task_summary, status, created_at) VALUES ('a','job','working','t')")
    run(db, "INSERT INTO agent_runs (agent_slug, task_summary, status, created_at) VALUES ('a','job','done','t')")
    run(db, "INSERT INTO agent_spans (span_id, run_id, name, start_ms) VALUES ('sp', 2, 'x', 0)")

    mod = _cleanup_module()
    con = sqlite3.connect(db, isolation_level=None)
    con.execute("BEGIN")
    report: list[str] = []
    mod.repair_null_ids(con, mod.SnapshotIds(snapdir), report)
    mod.collapse_duplicates(con, report)
    con.execute("COMMIT")
    con.close()

    ideas = dict(one(db, "SELECT text, idea_id FROM ideas"))
    assert len(one(db, "SELECT * FROM ideas")) == 3, "the NULL twin should be dropped"
    assert ideas["from other"] == "idea-abcdef123456", "the original id should be restored"
    assert re.match(r"^idea-[0-9a-f]{12}$", ideas["orphan"]), ideas["orphan"]
    assert one(db, "SELECT is_read, read_at FROM literature_metadata") == [(1, "2026-10-02")]
    assert one(db, "SELECT run_id, status FROM agent_runs") == [(1, "done")]
    assert one(db, "SELECT run_id FROM agent_spans") == [(1,)]


def test_preference_files_and_missing_content_are_handled(world, tmp_path):
    d, p, s = world
    rp, rs = tmp_path / "repoP", tmp_path / "repoS"
    for r in (rp, rs):
        (r / "system" / "config").mkdir(parents=True)
    cfg = "system/config/user-preferences.json"
    (rp / cfg).write_text('{"tone": "brief"}')
    (rs / cfg).write_text('{"tone": "brief"}')
    (rp / "knowledge" / "courses" / "c1").mkdir(parents=True)
    (rp / "knowledge" / "courses" / "c1" / "lesson1.md").write_text("x")

    ms.make_primary(d, "P")
    ms.sync(p, d, "P", files_root=rp)
    ms.sync(s, d, "S", files_root=rs)
    r = ms.sync(p, d, "P", files_root=rp)
    r2 = ms.sync(s, d, "S", files_root=rs)
    assert any("knowledge/courses" in x for x in r2.problems), \
        "a course on the main computer that never arrived must be reported"

    # A preference changed on the secondary reaches the primary …
    (rs / cfg).write_text('{"tone": "detailed"}')
    ms.sync(s, d, "S", files_root=rs)
    ms.sync(p, d, "P", files_root=rp)
    assert (rp / cfg).read_text() == '{"tone": "detailed"}'
    ms.sync(s, d, "S", files_root=rs)

    # … and when both change it, the primary wins and nothing is lost.
    (rs / cfg).write_text('{"tone": "from S"}')
    (rp / cfg).write_text('{"tone": "from P"}')
    ms.sync(s, d, "S", files_root=rs)
    ms.sync(p, d, "P", files_root=rp)
    ms.sync(s, d, "S", files_root=rs)
    assert (rp / cfg).read_text() == '{"tone": "from P"}'
    assert (rs / cfg).read_text() == '{"tone": "from P"}'
    kept = list((rp / "system" / "config").glob("*conflict*")) + \
        list((rs / "system" / "config").glob("*conflict*"))
    assert any(k.read_text() == '{"tone": "from S"}' for k in kept)


def test_a_column_only_this_computer_has_keeps_its_data(world):
    """Newer code on the secondary added a column; adopting the primary's rows
    must not reset it."""
    d, p, s = world
    run(p, "INSERT INTO tasks (task_id, title, status, project_id) VALUES ('t1','a','open','x')")
    run(s, "INSERT INTO tasks (task_id, title, status, project_id) VALUES ('t1','a','open','x')")
    run(s, "ALTER TABLE tasks ADD COLUMN energy TEXT")
    run(s, "UPDATE tasks SET energy='high' WHERE task_id='t1'")
    ms.make_primary(d, "P")
    ms.sync(p, d, "P", files_root=None)
    run(p, "UPDATE tasks SET title='b' WHERE task_id='t1'")
    ms.sync(p, d, "P", files_root=None)
    ms.sync(s, d, "S", files_root=None)
    assert one(s, "SELECT title, energy FROM tasks WHERE task_id='t1'") == [("b", "high")]
