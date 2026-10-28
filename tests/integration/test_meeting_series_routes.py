"""Dashboard routes for meeting series, against the real schema.

The two things worth pinning here are the ones that were silently broken or
that would be easy to break again:

  · a meeting saved by the dashboard has a TEXT id ('mtg-…'), and the detail
    route used to declare `meeting_id: int` — so it answered 422 for every
    meeting created since ids were fixed;
  · the import form never links a meeting on resemblance: it proposes, and
    only the confirm button links.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
_APP_PY = _REPO / "system" / "app-py"
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"
for _p in (str(_APP_PY), str(_MCP_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("fastapi not installed", allow_module_level=True)

from metis_mcp import meeting_series as MS  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "metis.sqlite"
    c = sqlite3.connect(str(db))
    c.executescript((_REPO / "system" / "installer" / "schema.sql").read_text())
    c.commit()
    c.close()
    monkeypatch.setenv("METIS_DB", str(db))
    monkeypatch.setenv("METIS_RC_ROOT", str(_REPO))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    os.chdir(str(_APP_PY))
    from main import app
    return TestClient(app, raise_server_exceptions=False), db


def _conn(db):
    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    return c


def test_series_panel_and_create(env):
    client, db = env
    r = client.get("/api/partial/meetings/series")
    assert r.status_code == 200 and "No series yet" in r.text
    r = client.post("/api/meeting/series", data={
        "name": "Quarterly review — North", "code": "nrth", "cadence_days": "91",
        "language": "fr"})
    assert r.status_code == 200 and "Quarterly review — North" in r.text
    r = client.post("/api/meeting/series", data={"name": "Dup", "code": "NRTH"})
    assert "already belongs" in r.text


def test_import_proposes_then_confirm_links(env):
    client, db = env
    c = _conn(db)
    sid = MS.create_series(c, "Quarterly review — North", code="NRTH",
                           cadence_days=91, language="fr")
    MS.save_meeting(c, "NRTH - Réunion T3", "2026-07-20", attendees="A Lee, B Kim",
                    series_id=sid, actions=[{"description": "Send inventory",
                                             "owner": "A Lee"}])
    c.close()

    r = client.post("/api/meeting/import", data={
        "title": "NRTH - Réunion T4", "meeting_date": "2026-10-20",
        "attendees": "A Lee, B Kim", "transcript": "Action: repair the microscope",
        "series_id": "auto", "sequence_label": "T4 2026"})
    assert r.status_code == 200, r.text
    assert "follow-up to Quarterly review — North" in r.text

    c = _conn(db)
    mid = c.execute("SELECT meeting_id, series_id FROM meetings "
                    "WHERE title = 'NRTH - Réunion T4'").fetchone()
    assert mid["series_id"] == ""        # proposed, not linked
    c.close()

    r = client.post(f"/api/meeting/{mid['meeting_id']}/link-series",
                    data={"series_id": sid, "sequence_label": "T4 2026"})
    assert "LINKED" in r.text and "follows the previous meeting" in r.text

    r = client.get(f"/api/partial/meetings/detail/{mid['meeting_id']}")
    assert r.status_code == 200, r.text[:300]
    assert "SERIES · QUARTERLY REVIEW — NORTH" in r.text

    r = client.get(f"/api/partial/meetings/series/{sid}")
    assert r.status_code == 200
    assert "Send inventory" in r.text and "repair the microscope" in r.text


def test_status_change_is_recorded_at_latest_meeting(env):
    client, db = env
    c = _conn(db)
    sid = MS.create_series(c, "S", code="SSS")
    MS.save_meeting(c, "T3", "2026-07-20", series_id=sid,
                    actions=["Send inventory"])
    t4 = MS.save_meeting(c, "T4", "2026-10-20", series_id=sid)
    aid = MS.open_actions(c, sid)[0]["id"]
    c.close()
    r = client.post(f"/api/meeting/series-action/{aid}/status",
                    data={"series_id": sid, "status": "done", "at_meeting": t4})
    assert r.status_code == 200
    c = _conn(db)
    rev = c.execute("SELECT meeting_id, status FROM meeting_action_reviews "
                    "WHERE action_id = ?", (aid,)).fetchone()
    assert rev["meeting_id"] == t4 and rev["status"] == "done"
    c.close()


def test_report_docx_download(env):
    pytest.importorskip("docx")
    client, db = env
    c = _conn(db)
    sid = MS.create_series(c, "S", code="SSS", language="fr")
    mid = MS.save_meeting(c, "T3", "2026-07-20", series_id=sid,
                          sequence_label="T3 2026", actions=["Send inventory"])
    c.close()
    r = client.get(f"/api/meeting/{mid}/report.docx")
    assert r.status_code == 200
    assert r.content[:2] == b"PK"   # a zip container, i.e. a real .docx


def test_rule_add_and_remove(env):
    client, db = env
    c = _conn(db)
    sid = MS.create_series(c, "S")
    c.close()
    r = client.post(f"/api/meeting/series/{sid}/rule",
                    data={"rule": "No duration in the header"})
    assert "No duration in the header" in r.text
    r = client.post(f"/api/meeting/series/{sid}/rule", data={"remove_index": "0"})
    assert "No duration in the header" not in r.text
