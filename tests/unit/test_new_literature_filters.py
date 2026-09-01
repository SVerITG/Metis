"""The two filters that decide whether a paper can be reached at all.

Written 2026-09-01, after this was reported: a paper cited in a July morning
brief — plainly close to the work — could not be found anywhere in Library →
New, so there was nowhere to press "add to library" or "not interested".

Nothing was broken in the ordinary sense. Two filters simply had no setting
that included it:

  1. The longest window was 30 days, and `catchup` collapses to nothing the
     moment a catch-up is recorded. The paper was 56 days old.
  2. `show='unread'` required an empty `read_at` as well as an empty
     added/dismissed pair — so a bulk mark-as-read, which is a statement about
     ATTENTION, silently retired 2,286 papers that had never been triaged,
     which is a statement about INTENT.

Together: 17 papers reachable out of 2,299.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "app-py"))

nl = pytest.importorskip("routers.new_literature")


def test_everything_window_has_no_lower_bound():
    """`days or 7` is a falsy-zero trap: a 0-day window means "no bound", but
    `or` reads 0 as absent and hands back seven days. That would make
    "Everything" a silent synonym for "This week" — the exact failure this
    window was added to fix, wearing the label of the fix."""
    cutoff, label = nl._window_cutoff("all")
    assert cutoff == "", f"'Everything' still has a lower bound ({cutoff!r})"
    assert "every" in label.lower()


def test_the_fixed_windows_still_bound():
    """The guard above must not have loosened the ordinary windows."""
    for key in ("day", "week", "month"):
        cutoff, _ = nl._window_cutoff(key)
        assert cutoff, f"window {key!r} lost its lower bound"
    assert nl._window_cutoff("day")[0] > nl._window_cutoff("month")[0]


def test_undecided_ignores_whether_you_have_seen_it():
    """The distinction the surface exists for. 'unread' may consult `read_at`;
    'undecided' must not, or a bulk mark-as-read hides the backlog again and
    there is no filter left that can find it."""
    def where_for(show):
        clauses = []
        # Mirror the branch under test rather than importing a private helper,
        # so this fails when the SQL changes shape and not merely when it moves.
        src = (ROOT / "system" / "app-py" / "routers" / "new_literature.py").read_text(encoding="utf-8")
        marker = f'elif show == "{show}":' if show != "unread" else 'if show == "unread":'
        assert marker in src, f"the {show!r} branch is gone"
        body = src[src.index(marker) + len(marker):]
        body = body[: body.index("elif ") if "elif " in body else 200]
        return body

    assert "read_at" not in where_for("undecided"), (
        "'undecided' consults read_at again — marking papers read will re-hide "
        "the untriaged backlog"
    )
    assert "added_at" in where_for("undecided") and "dismissed_at" in where_for("undecided")


def test_every_show_state_is_offered_in_the_ui():
    """`show` existed for months with no control — it could only be changed by
    editing the URL, which means in practice it was always its default. A filter
    the reader cannot reach is not a filter."""
    tpl = (ROOT / "system" / "app-py" / "templates" / "partials"
           / "library_new_literature.html").read_text(encoding="utf-8")
    for state in ("unread", "undecided", "added"):
        assert f"'{state}'" in tpl, f"no control offers show={state!r}"


def test_every_window_is_offered_in_the_ui():
    """The chips are generated from LIT_WINDOWS, so a new key appears for free —
    this asserts that generation is still what happens."""
    tpl = (ROOT / "system" / "app-py" / "templates" / "partials"
           / "library_new_literature.html").read_text(encoding="utf-8")
    assert "windows.items()" in tpl, "window chips are no longer generated from LIT_WINDOWS"
    assert "all" in nl.LIT_WINDOWS
