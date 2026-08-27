"""An optional target date, and the rule that an undated task is not late.

the researcher, 2026-08-27: *"we can give the option to assign a date to a task … but dont
make it obligatory, because often i dont know when i will work on something."*

THE CONSTRAINT IS THE FEATURE. Not knowing when you will get to something is the
normal case, and the code was already breaking that rule before the control
existed: `due_date IS NOT NULL AND due_date < today` looks correct and is not,
because 69 of 71 open tasks stored '' rather than NULL, and in SQLite an empty
string sorts BEFORE any date. Every undated task counted as overdue — the
dashboard reported 70 overdue out of 71 open.

`created_at` is not this. It has always been written automatically; the question
"completion date or creation date?" answers itself from the schema. What was
missing was a TARGET, and a way to say it loosely.
"""
import datetime as dt
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "system" / "app-py"
sys.path.insert(0, str(APP))


# ── 1. an undated task is undated, never late ────────────────────────────────

def test_no_query_treats_an_empty_string_as_a_date():
    """`IS NOT NULL` passes '' and '' < any-date is TRUE. This is the bug that
    made 69 undated tasks overdue, and it reads as correct at a glance."""
    bad = []
    for f in list((APP / "routers").glob("*.py")) + \
             list((ROOT / "system/mcp-server/src/metis_mcp/tools").glob("*.py")):
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"due_date IS NOT NULL(?!\s+AND\s+\w*\.?due_date\s*!=\s*'')", src):
            line = src[:m.start()].count("\n") + 1
            bad.append(f"{f.name}:{line}")
    assert not bad, (
        f"`due_date IS NOT NULL` without an empty-string guard at {bad} — "
        f"use COALESCE(due_date,'') != ''")


def test_clearing_a_date_writes_null_not_empty_string():
    """The whole empty-string trap starts here. If clearing wrote '', every
    cleared task would silently rejoin the overdue list."""
    src = (APP / "routers" / "work.py").read_text(encoding="utf-8")
    body = src[src.index("async def set_task_due("):]
    assert "due = None" in body, "clearing must store NULL"
    assert 'due = ""' not in body


# ── 2. the relative words mean what they say ─────────────────────────────────

@pytest.fixture
def when():
    """The real table, imported — not a slice of the file exec'd.

    The first version sliced the source between two string markers and exec'd
    it, which broke the moment a blank line moved. A test that reads the code as
    TEXT tests the text, not the behaviour."""
    from routers import work
    return work._WHEN


def test_today_and_tomorrow(when):
    d = dt.date(2026, 8, 27)           # a Thursday
    assert when["today"](d) == d
    assert when["tomorrow"](d) == dt.date(2026, 8, 28)


def test_this_week_means_the_end_of_the_working_week(when):
    """A task you say you will do 'this week' is not due next Wednesday."""
    assert when["this-week"](dt.date(2026, 8, 24)) == dt.date(2026, 8, 28)   # Mon → Fri
    assert when["this-week"](dt.date(2026, 8, 27)) == dt.date(2026, 8, 28)   # Thu → Fri
    assert when["this-week"](dt.date(2026, 8, 28)) == dt.date(2026, 8, 28)   # Fri → today


def test_next_week_is_a_full_week_later(when):
    assert when["next-week"](dt.date(2026, 8, 27)) == dt.date(2026, 9, 4)


def test_this_month_is_the_last_day_of_it(when):
    assert when["this-month"](dt.date(2026, 8, 27)) == dt.date(2026, 8, 31)
    assert when["this-month"](dt.date(2026, 2, 3)) == dt.date(2026, 2, 28)


# ── 3. the filter that decides how a date reads ──────────────────────────────

def test_due_delta_returns_none_for_no_date():
    """None, not 0. A task with no date is not due today — collapsing those two
    is exactly how the overdue count went wrong."""
    import main
    assert main._due_delta("") is None
    assert main._due_delta(None) is None
    assert main._due_delta("not-a-date") is None
    assert main._due_delta(dt.date.today().isoformat()) == 0


def test_due_delta_is_registered_as_a_filter():
    import main
    assert "due_delta" in main._SHARED_FILTERS


# ── 4. the control is optional in how it looks, not only in what it stores ───

def test_an_undated_task_shows_no_prompt_until_hover():
    """A column of empty date prompts is how a field ends up ignored."""
    css = (APP / "static" / "styles.css").read_text(encoding="utf-8")
    block = css[css.index(".due-chip--none"):]
    assert "opacity: 0" in block.split("}")[0]
    assert "hover" in block[:400]


def test_late_styling_needs_an_actual_date():
    tpl = (APP / "templates" / "partials" / "_duedate.html").read_text(encoding="utf-8")
    # `due-late` may only appear inside a branch that already has a delta.
    assert "due_delta" in tpl
    assert tpl.index("d is none") < tpl.index("due-late")


def test_the_control_replaces_itself():
    """Targeting the list container would swap away the element carrying its own
    hx-get loader, and re-render forty rows to change one date."""
    tpl = (APP / "templates" / "partials" / "_duedate.html").read_text(encoding="utf-8")
    assert "target='closest .due'" in tpl or 'target="closest .due"' in tpl
