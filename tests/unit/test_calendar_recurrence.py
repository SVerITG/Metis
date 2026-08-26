"""Multi-day events and repeating reminders on the Work calendar.

Built 2026-08-25 after the researcher asked how he would add events spanning several days
and recurring reminders.

Two different answers, and the tests reflect that:

  * MULTI-DAY needed almost nothing. `day_plan` already had `end_date` and
    `_plans_between` already expanded a span across the days it covers — the
    reminder tool simply hardcoded end_date to NULL.
  * REPEATS needed a decision. A repeating plan is stored as ONE row plus a rule
    and expanded at draw time, matching the choice already made for spans, so
    editing "every Monday" edits one row rather than fifty-two. That forces
    completion to be per occurrence, because `done` on the row would strike
    through every Monday at once.

`end_date` therefore means two different things depending on `repeat` — a span
end without it, a series end with it. The pair is mutually exclusive by design,
and that is asserted here so nobody later "fixes" it into ambiguity.
"""
import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "app-py"))
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

cal = pytest.importorskip("routers.calendar_plan")
D = dt.date


# ── month arithmetic ─────────────────────────────────────────────────────────

def test_month_step_clamps_to_a_short_month():
    """31 January + 1 month is 28 February — not an error, and not 3 March."""
    assert cal._add_months(D(2026, 1, 31), 1) == D(2026, 2, 28)
    assert cal._add_months(D(2024, 1, 31), 1) == D(2024, 2, 29)  # leap year


def test_month_step_does_not_drift():
    """Clamping must not be sticky: a run through February returns to the 31st."""
    start = D(2026, 1, 31)
    assert cal._add_months(start, 1) == D(2026, 2, 28)
    assert cal._add_months(start, 2) == D(2026, 3, 31)


# ── occurrence expansion ─────────────────────────────────────────────────────

def test_weekly_lands_on_the_same_weekday():
    occ = cal._occurrences(D(2026, 9, 7), "weekly", None, D(2026, 9, 1), D(2026, 9, 30))
    assert occ == [D(2026, 9, 7), D(2026, 9, 14), D(2026, 9, 21), D(2026, 9, 28)]
    assert {d.weekday() for d in occ} == {0}


def test_series_end_is_honoured():
    occ = cal._occurrences(D(2026, 9, 7), "weekly", D(2026, 9, 20), D(2026, 9, 1), D(2026, 9, 30))
    assert occ == [D(2026, 9, 7), D(2026, 9, 14)]


def test_window_before_the_series_starts_is_empty():
    assert cal._occurrences(D(2026, 9, 7), "weekly", None, D(2026, 8, 1), D(2026, 8, 31)) == []


def test_an_old_rule_does_not_cost_more_than_a_new_one():
    """The first occurrence in the window is computed, not stepped to. A weekly
    reminder from 2019 must not make drawing one month slower."""
    occ = cal._occurrences(D(2019, 1, 7), "weekly", None, D(2026, 9, 1), D(2026, 9, 30))
    assert len(occ) == 4
    assert all(d.weekday() == 0 for d in occ)


def test_monthly_from_the_31st_appears_in_short_months():
    occ = cal._occurrences(D(2026, 8, 31), "monthly", None, D(2026, 9, 1), D(2026, 11, 30))
    assert D(2026, 9, 30) in occ   # clamped
    assert D(2026, 10, 31) in occ  # and back to the 31st


def test_unknown_rule_expands_to_nothing():
    assert cal._occurrences(D(2026, 9, 1), "fortnightly", None, D(2026, 9, 1), D(2026, 9, 30)) == []


# ── the tool's input contract ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def add():
    tasks = pytest.importorskip("metis_mcp.tools.tasks")
    return getattr(tasks.add_reminder, "fn", tasks.add_reminder)


def _say(out):
    return " ".join(c.text for c in out)


def test_rejects_a_repeat_it_cannot_honour(add):
    said = _say(add(text="x", date="2026-09-01", repeat="fortnightly"))
    assert "not a repeat I understand" in said
    assert "plan #" not in said, "a rejected reminder must not be written"


def test_rejects_an_end_before_the_start(add):
    said = _say(add(text="x", date="2026-09-10", until="2026-09-01"))
    assert "before the start date" in said
    assert "plan #" not in said


def test_span_and_series_are_described_differently(add, tmp_path, monkeypatch):
    """`until` means a span without `repeat` and a series end with it. If the two
    ever render the same way, the ambiguity has leaked to the user.

    Writes to a throwaway database: a test that writes to the live one competes
    with the running dashboard for the lock AND leaves rows on the researcher's
    real calendar."""
    tasks = pytest.importorskip("metis_mcp.tools.tasks")
    monkeypatch.setattr(tasks.paths, "db", tmp_path / "t.sqlite", raising=False)

    span = _say(add(text="tc span", date="2026-12-01", until="2026-12-04"))
    series = _say(add(text="tc series", date="2026-12-01", until="2026-12-29", repeat="weekly"))
    assert "Blocked out" in span and "4 days" in span, span
    assert "Repeating weekly" in series and "until" in series, series
    assert "Blocked out" not in series


# ── the five gaps closed 2026-08-25 ──────────────────────────────────────────
# Each was listed as an honest limitation when repeats first shipped, so each
# gets a test rather than a note claiming it was fixed.

def test_weekdays_skips_the_weekend():
    """"Every weekday" is the common case for work reminders. Expressed as five
    weekly rules it is five rows that can drift apart."""
    occ = cal._occurrences(D(2026, 9, 1), "weekdays", None, D(2026, 9, 1), D(2026, 9, 13))
    assert len(occ) == 9
    assert not any(d.weekday() >= 5 for d in occ)


def test_weekdays_respects_the_series_end():
    occ = cal._occurrences(D(2026, 9, 1), "weekdays", D(2026, 9, 4), D(2026, 9, 1), D(2026, 9, 30))
    assert occ == [D(2026, 9, 1), D(2026, 9, 2), D(2026, 9, 3), D(2026, 9, 4)]


def test_a_recurring_span_is_now_possible(add, tmp_path, monkeypatch):
    """"The first three days of every month" was refused outright before."""
    tasks = pytest.importorskip("metis_mcp.tools.tasks")
    monkeypatch.setattr(tasks.paths, "db", tmp_path / "cal_t.db", raising=False)
    said = _say(add(text="tc span repeat", date="2026-10-01", repeat="monthly",
                    duration_days=3))
    assert "Repeating monthly" in said and "3 days each" in said


def test_duration_and_until_may_not_disagree(add, tmp_path, monkeypatch):
    """Both describe a span. Two descriptions of one thing drift apart; refuse
    rather than silently picking whichever the code happens to read last."""
    tasks = pytest.importorskip("metis_mcp.tools.tasks")
    monkeypatch.setattr(tasks.paths, "db", tmp_path / "cal_t.db", raising=False)
    said = _say(add(text="tc clash", date="2026-10-01", until="2026-10-09", duration_days=3))
    assert "different spans" in said
    assert "plan #" not in said


def test_a_skipped_occurrence_does_not_take_the_series_with_it():
    """The whole point of skip: one occurrence gone, the rule intact."""
    import inspect
    src = inspect.getsource(cal.plan_skip)
    assert "'skipped'" in src or '"skipped"' in src
    assert "DELETE FROM day_plan" not in src, "skip must never delete the plan row"


def test_deleting_a_series_cleans_up_its_occurrences():
    """Occurrence rows outliving their plan would silently re-apply if a future
    plan reused the id."""
    import inspect
    src = inspect.getsource(cal.plan_delete)
    assert "DELETE FROM day_plan_occurrence" in src


def test_the_two_removals_are_not_the_same_control():
    """"Delete" is ambiguous on a repeat, and silently picking one reading is how
    people lose a year of reminders."""
    import inspect
    src = inspect.getsource(cal._chip)
    assert "/skip" in src and "/delete" in src
    assert "WHOLE repeating series" in src


def test_toast_escapes_apostrophes():
    """`_notify_windows` interpolates into a single-quoted PowerShell string.
    Unescaped, "the researcher's meeting" produced no toast at all — and made arbitrary
    reminder text executable."""
    sched = pytest.importorskip("scheduler")
    import inspect
    src = inspect.getsource(sched._notify_windows)
    assert 'replace("\'", "\'\'")' in src


def test_the_notifier_reuses_the_calendars_own_recurrence_maths():
    """A notifier with its own copy of the rules will eventually disagree with
    the calendar about which days a repeat falls on."""
    sched = pytest.importorskip("scheduler")
    import inspect
    src = inspect.getsource(sched.job_reminder_due)
    assert "_plans_between" in src
    assert "notified_at" in src, "must not re-notify the same occurrence"
