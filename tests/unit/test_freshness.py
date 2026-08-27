"""New on top, and one line per running story.

the researcher, 2026-08-27: highlight new content and put it on top; and "in the lists
there is the same item though (outbreak I have seen Ebola multiple times for
example)".

THE EBOLA ROWS WERE NOT DUPLICATES, and that changed the fix. WHO publishes a
weekly situation report, so what looked like the same item four times was
Report 13, Report 14, Report 15 — each genuinely new — plus one true duplicate
of Report 15. Deleting instalments would delete information.

So: duplicates collapse, series GROUP under the newest with the rest reachable,
and the two are never confused.

The tests that matter most are the negative ones. A similarity fingerprint
merges "WFP Bangladesh Country Brief" with "WFP Togo Country Brief" and
"Venezuela: Earthquakes" with "Colombia - Earthquake" — which would silently
hide a second outbreak, the most expensive failure this surface can have.
"""
import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "app-py"))

F = pytest.importorskip("freshness")


# ── 1. what must GROUP ───────────────────────────────────────────────────────

@pytest.mark.parametrize("a,b", [
    ("EBOLA … Uganda Weekly External Situation Report 13, Data as of 09 August 2026",
     "EBOLA … Uganda Weekly External Situation Report 15, Data as of 23 August 2026"),
    ("Electronic Surveillance Monthly Bulletin (May 2026)",
     "Electronic surveillance monthly bulletin (June 2026)"),
    ("Communicable disease threats report, 15 - 21 August 2026, week 34",
     "Communicable disease threats report, 8 - 14 August 2026, week 33"),
    ("Call to Action – Third International Conference for PEN-Plus in Africa (ICPPA 2026)",
     "The 3rd International Conference on PEN-Plus in Africa (ICPPA 2026)"),
])
def test_instalments_of_one_story_share_a_key(a, b):
    assert F.series_key(a) == F.series_key(b)


# ── 2. what must NOT group — the expensive failures ──────────────────────────

@pytest.mark.parametrize("a,b,why", [
    ("WFP Bangladesh Country Brief, August 2026",
     "WFP Togo Country Brief, August 2026", "different country"),
    ("Venezuela: Earthquakes - LTC Situation Report (Telecoms) #06",
     "Colombia - Earthquake: LTC Telecoms Situation Report #01", "different country"),
    ("Create detection area polygons in QGIS — passive screening",
     "Create detection area polygons in QGIS — active screening", "different task"),
    ("Ebola outbreak declared in Uganda", "Ebola outbreak declared in Guinea",
     "different country — the second outbreak this must never hide"),
])
def test_different_subjects_stay_apart(a, b, why):
    assert F.series_key(a) != F.series_key(b), why


def test_a_place_name_is_never_treated_as_a_variable_part():
    """Only what varies BETWEEN instalments is stripped — numbers, dates, month
    names, 'report 4'. A country is subject, not serial."""
    for place in ("uganda", "bangladesh", "venezuela", "congo"):
        assert place in F.series_key(f"Situation Report 12 — {place.title()} 2026")


# ── 3. freshness ─────────────────────────────────────────────────────────────

def test_bands():
    now = dt.datetime(2026, 8, 27, 12, 0)
    assert F.band(dt.datetime(2026, 8, 27, 9).isoformat(), now) == "today"
    assert F.band(dt.datetime(2026, 8, 24).isoformat(), now) == "week"
    assert F.band(dt.datetime(2026, 8, 1).isoformat(), now) == ""
    assert F.band("", now) == ""
    assert F.band("not-a-date", now) == ""


def test_new_goes_on_top_and_newest_first_within_a_band():
    now = dt.datetime.now()
    rows = [
        {"title": "old one", "created_at": (now - dt.timedelta(days=40)).isoformat()},
        {"title": "this week", "created_at": (now - dt.timedelta(days=3)).isoformat()},
        {"title": "today early", "created_at": now.replace(hour=1).isoformat()},
        {"title": "today late", "created_at": now.replace(hour=9).isoformat()},
    ]
    out = [r["title"] for r in F.collapse(rows)]
    assert out[:2] == ["today late", "today early"], out
    assert out[-1] == "old one"


# ── 4. nothing is discarded ──────────────────────────────────────────────────

def test_every_row_is_still_reachable():
    """A list that quietly drops rows cannot be checked against its source —
    the same rule the focus safe and the reading stack follow."""
    now = dt.datetime.now().isoformat()
    rows = [{"title": "Report 1 of the thing", "created_at": now},
            {"title": "Report 2 of the thing", "created_at": now},
            {"title": "Report 2 of the thing", "created_at": now},
            {"title": "Something else entirely", "created_at": now}]
    out = F.collapse(rows)
    total = len(out) + sum(len(r.get("_earlier", [])) for r in out) \
                     + sum(len(r.get("_dupes", [])) for r in out) \
                     + sum(len(e.get("_dupes", [])) for r in out
                           for e in r.get("_earlier", []))
    assert total == len(rows), f"{total} accounted for, {len(rows)} given"


def test_the_newest_instalment_is_the_one_shown():
    now = dt.datetime.now()
    rows = [{"title": "Weekly Report 3 — Uganda",
             "created_at": (now - dt.timedelta(days=14)).isoformat()},
            {"title": "Weekly Report 5 — Uganda", "created_at": now.isoformat()}]
    out = F.collapse(rows)
    assert len(out) == 1
    assert "5" in out[0]["title"], "the older instalment became the head"
    assert out[0]["_n_earlier"] == 1


def test_an_exact_duplicate_is_folded_not_grouped():
    """Two arrivals of the SAME instalment is a duplicate; two instalments is a
    series. Confusing them is how information gets deleted."""
    now = dt.datetime.now().isoformat()
    out = F.collapse([{"title": "Identical headline", "created_at": now},
                      {"title": "Identical  headline", "created_at": now}])
    assert len(out) == 1
    assert out[0]["_n_dupes"] == 1
    assert out[0]["_n_earlier"] == 0
