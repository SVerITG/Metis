"""The Work surface's three views, and the switcher that has to reveal them.

Written 2026-09-03 after the researcher reported that only the List view worked. It did
not — and the cause was one line that could never have worked:

    pane.style.display = active ? '' : 'none';

Both the Board and Calendar panes are authored with `class="u-hide"`, and that
class is `display:none !important`. Setting `display:''` merely REMOVES the inline
value and lets the class apply again, so the pane stayed hidden. **An inline
style cannot beat `!important`** — the two views had been unreachable from the day
that class was added, and both were loading their content the whole time.

Nothing tested this because the panes RENDER correctly; only the toggle was
broken. A test that fetches a partial and checks it returns HTML cannot see a
view the user can never open. So these assert the toggle mechanism itself.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "system" / "app-py" / "templates" / "work.html"
CSS = ROOT / "system" / "app-py" / "static" / "styles.css"


@pytest.fixture(scope="module")
def work_src() -> str:
    assert WORK.is_file(), f"missing {WORK}"
    return WORK.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css_src() -> str:
    return CSS.read_text(encoding="utf-8")


def test_u_hide_is_still_important(css_src):
    """The premise of the bug. If `u-hide` ever stops being `!important`, the
    inline-style approach would start working and this whole test file is moot —
    so assert the premise rather than leaving it implied."""
    m = re.search(r"\.u-hide\s*\{([^}]*)\}", css_src)
    assert m, "the .u-hide utility is gone"
    assert "!important" in m.group(1), (
        "u-hide is no longer !important — re-check whether the view switcher "
        "still needs to toggle the class rather than the style"
    )


def test_all_three_panes_exist(work_src):
    for view in ("list", "board", "calendar"):
        assert f'id="work-view-{view}"' in work_src, f"no pane for the {view} view"


def _strip_js_comments(js: str) -> str:
    """Drop `//` line comments.

    Needed because the comment above the fix QUOTES the broken line it replaced,
    to explain why it was broken — and the first version of the test below then
    matched its own documentation and failed on correct code. A check that a
    string is absent has to look at the code, not at the prose about the code.
    """
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in js.split("\n"))


def test_switcher_toggles_the_class_not_the_inline_style(work_src):
    """The fix, stated as the property that matters."""
    m = re.search(r"window\.workSetView\s*=\s*function.*?\n\s*\};", work_src, re.S)
    assert m, "could not locate workSetView"
    code = _strip_js_comments(m.group(0))
    assert "classList.toggle('u-hide'" in code or 'classList.toggle("u-hide"' in code, (
        "the switcher no longer toggles the u-hide class — if it sets "
        "pane.style.display instead, the Board and Calendar views are unreachable "
        "again, because an inline style cannot override display:none !important"
    )
    assert not re.search(r"pane\.style\.display\s*=", code), (
        "the switcher is back to setting an inline display, which cannot beat "
        "the !important class the panes carry"
    )


def test_the_hidden_panes_carry_the_class_the_switcher_removes(work_src):
    """The two halves have to agree: whatever hides a pane at page load must be
    the same thing the switcher can lift. They drifted once."""
    for view in ("board", "calendar"):
        m = re.search(rf'<div([^>]*)id="work-view-{view}"', work_src)
        assert m, f"no {view} pane"
        attrs = m.group(1)
        assert "u-hide" in attrs, (
            f"the {view} pane is no longer hidden by the u-hide class; if it is "
            "hidden some other way, the switcher cannot show it"
        )


def test_each_view_owns_its_panels(work_src):
    """A panel rendered in two views is a panel that will drift.

    `planner/intentions` is currently in BOTH the list and board views — recorded
    here as a known duplication so that fixing it is a deliberate act and adding
    a second one is not.
    """
    intentions = work_src.count("/api/partial/planner/intentions")
    assert intentions <= 2, (
        f"planner/intentions is rendered {intentions} times on this surface; it "
        "was already duplicated across the list and board views and should be "
        "going down, not up"
    )
