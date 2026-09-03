"""One definition of "an open task", because three were live at once.

Found 2026-09-03 while validating the status board. The board's "No date"
column said 54 while another figure on the same surface said 90, and the reason
was that nothing in the app agreed on which rows are work:

    status != 'done'                    → 92   project-category headings
    status = 'open'                     → 56   the status board's columns
    status NOT IN ('done','cancelled')  → 58   the header, and the all-tasks list

The store holds 34 **cancelled** tasks. So the headings advertised 34 tasks that
had already been decided against, and the board hid the 2 **blocked** ones —
which is the more dangerous of the two, because held work that appears nowhere
is how it stops being work at all.

These tests are about drift, not arithmetic. Any single site is easy to write
correctly; what went wrong is that four sites were written correctly at four
different times against four different intentions. So the property asserted is
that the predicate has ONE author.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "system" / "app-py"
DB = APP / "db.py"

# Routers that reason about a researcher's own task backlog. `meetings.py` is
# deliberately absent: it queries `meeting_actions`, a different table with its
# own lifecycle, and folding it in here would assert a shared vocabulary that
# does not exist.
TASK_ROUTERS = ("work.py", "calendar_plan.py")


@pytest.fixture(scope="module")
def db_src() -> str:
    return DB.read_text(encoding="utf-8")


def test_the_definition_exists_and_is_an_exclusion(db_src):
    """Phrased as NOT IN, so an unrecognised status shows up rather than vanishing.

    An inclusion list is the tempting shape and the wrong one: add a status
    later — 'waiting', 'someday' — and every task carrying it silently leaves
    every view, with nothing failing anywhere.
    """
    assert "def live_task_sql" in db_src, "the shared predicate is gone"
    m = re.search(r"def live_task_sql\(.*?\n(.*?)(?=\n\ndef |\n\n[A-Z_])", db_src, re.S)
    assert m, "could not read live_task_sql"
    body = m.group(1)
    assert "NOT IN" in body, (
        "live_task_sql is no longer an exclusion; if it lists the live statuses "
        "instead, any status added later disappears from every surface at once"
    )
    assert "'cancelled'" in body, "cancelled is being counted as live work again"
    assert "'done'" in body


def test_no_router_writes_its_own_open_task_predicate():
    """The actual defect: four sites, four authors, four answers."""
    offenders = []
    for name in TASK_ROUTERS:
        src = (APP / "routers" / name).read_text(encoding="utf-8")
        # Strip comments so the prose explaining the old predicate — which
        # quotes it verbatim — cannot fail the check on correct code. Same
        # family as the `pane.style.display` test that matched its own
        # rationale.
        code = "\n".join(re.sub(r"#.*$", "", ln) for ln in src.split("\n"))
        for pat, why in (
            (r"status\s*!=\s*'done'", "hand-written 'not done' counts cancelled work as backlog"),
            (r"status\s*<>\s*'done'", "same, with the other inequality spelling"),
            (r"status\s+IN\s*\(\s*'open'\s*\)", "'open' alone drops blocked work"),
            (r"status\s*=\s*'open'\s+AND\s+COALESCE\(\s*t?\.?due_date",
             "a date bucket filtered on status='open' hides held work"),
        ):
            for m in re.finditer(pat, code):
                line = code[:m.start()].count("\n") + 1
                offenders.append(f"{name}:{line} — {why}")
    assert not offenders, (
        "a task-status predicate was written by hand instead of coming from "
        "db.live_task_sql(); each one is a new answer to 'how much work is "
        "there':\n  " + "\n  ".join(offenders)
    )


def test_the_routers_actually_import_it():
    """Guards against the predicate being defined, praised in a comment, and unused."""
    for name in TASK_ROUTERS:
        src = (APP / "routers" / name).read_text(encoding="utf-8")
        assert re.search(r"^from db import .*live_task_sql", src, re.M), (
            f"{name} does not import live_task_sql"
        )
        code = "\n".join(re.sub(r"#.*$", "", ln) for ln in src.split("\n"))
        assert code.count("live_task_sql(") >= 2, (
            f"{name} imports live_task_sql but barely calls it — check whether "
            "a query went back to spelling the statuses out"
        )


def test_the_status_board_columns_partition():
    """Three date buckets and one status column cannot overlap.

    'In progress' is its own column, so if the date columns admitted
    in-progress work a task due today would be drawn twice and counted twice in
    two different totals on the same screen.
    """
    src = (APP / "routers" / "work.py").read_text(encoding="utf-8")
    m = re.search(r"DATED\s*=\s*(.+)", src)
    assert m, "the status board no longer names its date-column predicate"
    assert "live_task_sql" in m.group(1), (
        "the date columns spell out statuses again rather than deriving from "
        "the one definition"
    )
    assert "in_progress" in m.group(1), (
        "the date columns no longer exclude in-progress work, so a dated task "
        "in progress appears in two columns at once"
    )


def test_a_move_between_columns_changes_only_what_the_column_means():
    """Dropping a card onto a date must not silently rewrite its status.

    The first version wrote `due_date=?, status='open'` together, so dragging a
    BLOCKED task onto Today quietly unblocked it — two edits from one gesture,
    and the one nobody asked for invisible.
    """
    src = (APP / "routers" / "work.py").read_text(encoding="utf-8")
    m = re.search(r"async def work_kanban_move\(.*?\n(.*?)(?=\n@router\.)", src, re.S)
    assert m, "could not locate work_kanban_move"
    body = "\n".join(re.sub(r"#.*$", "", ln) for ln in m.group(1).split("\n"))
    for bad in re.finditer(r"SET\s+due_date=[^\"']*status\s*=", body):
        pytest.fail(
            "a date-setting column also writes a status: " + bad.group(0)[:60]
        )
    # The in-progress column is the one that legitimately sets a status — and it
    # must equally leave the DATE alone.
    prog = re.search(r'elif col == "progress":(.*?)(?=\n    elif|\n    else|\Z)', body, re.S)
    assert prog, "no in-progress branch"
    assert "due_date" not in prog.group(1), (
        "moving a card into In progress also edits its due date, discarding a "
        "deadline the researcher set"
    )

def test_the_exclusion_list_is_not_re_spelled_per_query():
    """The variant the first version of this test missed.

    An audit of the app found SEVEN different exclusion lists in use:

        ('done','cancelled')                              the intended one
        ('done','cancelled','deleted')
        ('done','completed','cancelled','deleted')
        ('done','deleted')                                ← counts cancelled
        ('done','cancelled','paused')
        ('done','completed','cancelled','deleted','blocked')  ← hides held work

    Only four statuses have ever existed in the store — open, blocked,
    cancelled, done — so 'deleted', 'completed' and 'paused' name nothing and
    most of the variants were equivalent BY ACCIDENT. Two were not: the fourth
    drew 34 abandoned tasks as live work across nine project cards, and the
    last would hide held work the moment anything were starred.

    A list that is right by coincidence is the thing to catch, because the
    coincidence ends the day a status is added.
    """
    offenders = []
    for name in TASK_ROUTERS:
        src = (APP / "routers" / name).read_text(encoding="utf-8")
        code = "\n".join(re.sub(r"#.*$", "", ln) for ln in src.split("\n"))
        for m in re.finditer(r"status\s+NOT\s+IN\s*\(([^)]*)\)", code, re.I):
            listed = {x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()}
            line = code[:m.start()].count("\n") + 1
            if "cancelled" not in listed:
                offenders.append(f"{name}:{line} — omits 'cancelled', so abandoned "
                                 f"work counts as backlog: {sorted(listed)}")
            elif "blocked" in listed:
                offenders.append(f"{name}:{line} — excludes 'blocked', so held work "
                                 f"disappears instead of being marked: {sorted(listed)}")
            else:
                offenders.append(f"{name}:{line} — a hand-written exclusion list; use "
                                 f"live_task_sql() so there is one: {sorted(listed)}")
    assert not offenders, (
        "task-status exclusion lists are being spelled out per query again:\n  "
        + "\n  ".join(offenders)
    )
