"""Tests for the meeting-series layer.

The case these exist for: several recurring meetings that look alike — same
template title, same agenda, and the researcher plus the same central colleagues
in every one of them — held with DIFFERENT groups. Linking a new meeting to the
wrong series attaches another group's actions to its report, so the matcher must
lean on what actually tells the series apart and must ask when it cannot.

Names and codes below are invented.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"
if str(_MCP_SRC) not in sys.path:
    sys.path.insert(0, str(_MCP_SRC))

from metis_mcp import meeting_series as MS  # noqa: E402

CENTRAL = ["Alex Researcher", "Dr Sam Finance", "Robin Logistics"]


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "m.sqlite"))
    c.row_factory = sqlite3.Row
    MS.ensure_schema(c)
    yield c
    c.close()


@pytest.fixture
def two_series(conn):
    """Two quarterly series with the same template and the same central team."""
    a = MS.create_series(conn, "Quarterly review — North", code="NRTH",
                         cadence_days=91, language="fr")
    b = MS.create_series(conn, "Quarterly review — South", code="STH",
                         cadence_days=91, language="fr")
    MS.save_meeting(conn, "NRTH - Réunion T3", "2026-07-20",
                    attendees=CENTRAL + ["Dr Kim North", "Lee Northdata"],
                    series_id=a, sequence_label="T3 2026",
                    actions=[{"description": "Send the stock inventory",
                              "owner": "Lee Northdata", "due_date": "2026-08-31"},
                             {"description": "Repair the microscope",
                              "owner": "Robin Logistics"}])
    MS.save_meeting(conn, "STH - Réunion T3", "2026-07-22",
                    attendees=CENTRAL + ["Dr Pat South"],
                    series_id=b, sequence_label="T3 2026",
                    actions=["Update the screening register"])
    return a, b


def test_code_in_file_name_is_decisive(conn, two_series):
    a, _ = two_series
    r = MS.match_series(conn, title="Réunion T4", meeting_date="2026-10-20",
                        attendees=CENTRAL, filenames=["2026_T4_NRTH.pptx"])
    assert r["decision"] == "propose"
    assert r["candidates"][0]["series_id"] == a
    assert "Correct?" in r["question"]


def test_shared_central_team_does_not_pick_a_series(conn, two_series):
    # Same template title, only the people who attend EVERY series, no code:
    # nothing distinguishes the two, so the researcher must be asked.
    r = MS.match_series(conn, title="Réunion trimestrielle T4",
                        meeting_date="2026-10-21", attendees=CENTRAL)
    assert r["decision"] != "propose"


def test_series_specific_people_rank_but_do_not_link_alone(conn, two_series):
    _, b = two_series
    r = MS.match_series(conn, title="Réunion trimestrielle T4",
                        meeting_date="2026-10-21",
                        attendees=CENTRAL + ["Docteur Pat South"])
    assert r["candidates"][0]["series_id"] == b
    # Attendance plus timing cannot clear the bar without the code.
    assert r["decision"] == "ambiguous"


def test_unrelated_meeting_is_new(conn, two_series):
    r = MS.match_series(conn, title="Thesis committee", meeting_date="2026-10-01",
                        attendees=["Prof Unknown"])
    assert r["decision"] == "new"


def test_no_series_yet(conn):
    assert MS.match_series(conn, title="anything")["decision"] == "new"


def test_person_key_ignores_titles_accents_and_order():
    assert MS.person_key("Dr Marie-Cécile Ngo") == MS.person_key("Ngo Marie Cecile")
    assert MS.person_key("Mme X Y (finance)") == MS.person_key("Y X")


def test_code_must_be_unique(conn, two_series):
    with pytest.raises(ValueError):
        MS.create_series(conn, "Another", code="nrth")


def test_actions_follow_up_across_meetings(conn, two_series):
    a, _ = two_series
    acts = MS.open_actions(conn, a)
    assert len(acts) == 2
    assert acts[0]["owner"] == "Lee Northdata"
    t4 = MS.save_meeting(conn, "NRTH - Réunion T4", "2026-10-20",
                         attendees=CENTRAL, series_id=a, sequence_label="T4 2026",
                         actions=[{"description": "Train two lab technicians",
                                   "owner": "Dr Kim North"}])
    m = MS.get_meeting(conn, t4)
    assert m["previous_meeting_id"]  # linked to T3
    MS.review_action(conn, acts[0]["id"], "done", meeting_id=t4)
    MS.review_action(conn, acts[1]["id"], "in_progress", meeting_id=t4,
                     note="part ordered")
    still = MS.open_actions(conn, a)
    assert {x["description"] for x in still} == {"Repair the microscope",
                                                 "Train two lab technicians"}
    report = MS.draft_report(conn, t4)
    # French labels, previous actions with their status AT this meeting, new plan.
    assert "Suivi des actions de la réunion précédente" in report
    assert "Réalisé" in report and "En cours — part ordered" in report
    assert "Plan d'actions" in report and "Train two lab technicians" in report
    # The other series' actions never leak in.
    assert "screening register" not in report


def test_review_rejects_unknown_status(conn, two_series):
    a, _ = two_series
    act = MS.open_actions(conn, a)[0]
    with pytest.raises(ValueError):
        MS.review_action(conn, act["id"], "finished")


def test_rules_are_per_series(conn, two_series):
    a, b = two_series
    MS.add_report_rule(conn, a, "No meeting duration in the header")
    MS.add_report_rule(conn, a, "no meeting duration in the header")  # duplicate
    assert MS.get_series(conn, a)["report_rules"] == ["No meeting duration in the header"]
    assert MS.get_series(conn, b)["report_rules"] == []
    assert "No meeting duration" in MS.briefing(conn, a)


def test_briefing_lists_open_actions(conn, two_series):
    a, _ = two_series
    text = MS.briefing(conn, a)
    assert "Open actions (2)" in text
    assert "Send the stock inventory" in text
    assert "Update the screening register" not in text


def test_link_after_confirmation(conn, two_series):
    a, _ = two_series
    mid = MS.save_meeting(conn, "Réunion T4", "2026-10-20", attendees=CENTRAL,
                          actions=["Check the solar kit"])
    assert MS.get_meeting(conn, mid)["series_id"] == ""
    MS.link_meeting_to_series(conn, mid, a, sequence_label="T4 2026")
    m = MS.get_meeting(conn, mid)
    assert m["series_id"] == a and m["previous_meeting_id"]
    assert any(x["description"] == "Check the solar kit" for x in MS.open_actions(conn, a))


def test_report_diff_separates_removed_and_rewritten():
    draft = "Durée : 2 h\nPoint A jugé sérieux par X\nAction 1\nAction 2"
    final = "Point A\nAction 1"
    d = MS.report_diff(draft, final)
    assert "Durée : 2 h" in d["removed"]
    assert "Action 2" in d["removed"]
    assert {"before": "Point A jugé sérieux par X", "after": "Point A"} in d["changed"]


def test_report_diff_ignores_markdown_lost_in_word():
    # The draft is Markdown; the final comes back from Word as plain lines. Only
    # the real edit may surface, not every line whose markup disappeared.
    draft = ("# Compte rendu — X\n\n**Date** : 2026-10-22\n## Plan d'actions\n"
             "| N° | Action |\n|---|---|\n| 1 | Envoyer |\n- Point 1")
    final = ("Compte rendu — X\nDate : 2026-10-22\nPlan d'actions\nN° Action\n"
             "1 Envoyer\nPoint 1 révisé")
    d = MS.report_diff(draft, final)
    assert d["removed"] == [] and d["added"] == []
    assert d["changed"] == [{"before": "Point 1", "after": "Point 1 révisé"}]


def test_docx_export_makes_real_tables(conn, two_series, tmp_path):
    docx = pytest.importorskip("docx")
    a, _ = two_series
    mid = MS.series_meetings(conn, a)[-1]["meeting_id"]
    out = MS.markdown_to_docx(MS.draft_report(conn, mid), str(tmp_path / "r.docx"))
    d = docx.Document(out)
    assert len(d.tables) == 1
    assert d.tables[0].cell(1, 1).text == "Send the stock inventory"


def test_ensure_schema_upgrades_an_old_database(tmp_path):
    c = sqlite3.connect(str(tmp_path / "old.sqlite"))
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE meetings (meeting_id TEXT PRIMARY KEY, title TEXT, "
              "meeting_date TEXT, attendees TEXT, decisions TEXT, created_at TEXT)")
    c.execute("CREATE TABLE meeting_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
              "meeting_id INTEGER NOT NULL, description TEXT NOT NULL, "
              "status TEXT DEFAULT 'open', due_date TEXT, created_at TEXT)")
    MS.ensure_schema(c)
    MS.ensure_schema(c)  # idempotent
    cols = {r[1] for r in c.execute("PRAGMA table_info(meetings)")}
    assert {"series_id", "summary", "notes", "previous_meeting_id"} <= cols
    acols = {r[1] for r in c.execute("PRAGMA table_info(meeting_actions)")}
    assert {"owner", "series_id"} <= acols


def test_word_round_trip_shows_no_edit(conn, two_series, tmp_path):
    """A report exported to Word and read back unchanged must diff to nothing,
    tables included — otherwise every learned rule starts from noise."""
    pytest.importorskip("docx")
    T = pytest.importorskip("metis_mcp.tools.meetings")
    a, _ = two_series
    mid = MS.series_meetings(conn, a)[-1]["meeting_id"]
    draft = MS.draft_report(conn, mid)
    path = MS.markdown_to_docx(draft, str(tmp_path / "r.docx"))
    d = MS.report_diff(draft, T._read_transcript_file(path))
    assert d["removed"] == [] and d["added"] == [] and d["changed"] == []
