"""A category's KIND must change how it behaves, or it is only a label.

This is the whole reason the model exists. `literature_metadata.collection` was
a single flat column and sat NULL on all 1,144 rows for months — not because
writing to it was hard, but because there was nothing useful to DO with a label
once applied. If every kind sorts the same way and reads the same way, this
rewrite has reproduced that column with more ceremony.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ROUTER = ROOT / "system/app-py/routers/shelves.py"
PAGE = ROOT / "system/app-py/templates/library_shelf.html"
PICKER = ROOT / "system/app-py/templates/partials/library_shelf_picker.html"
SCHEMA = ROOT / "system/installer/schema.sql"


@pytest.fixture(scope="module")
def router() -> str:
    return ROUTER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_the_three_kinds_are_named_once(router):
    """One author for the kind list, so a fourth kind cannot be half-added."""
    assert 'KINDS = ("purpose", "tracking", "attachment")' in router
    for k in ("purpose", "tracking", "attachment"):
        assert f'"{k}"' in router


def test_each_kind_orders_differently(router):
    """A purpose category must NOT be ordered like a timeline.

    A reference shelf has no intrinsic chronology; a tracked subject is
    meaningless without one. Sorting both by the same column is the defect this
    test exists to catch, and it is invisible by eye because both pages render.
    """
    m = re.search(r"_ORDER = \{(.*?)\}", router, re.S)
    assert m, "no _ORDER map — ordering cannot depend on the kind"
    body = m.group(1)
    for k in ("purpose", "tracking", "attachment"):
        assert f'"{k}"' in body, f"{k} has no ordering of its own"
    # The two that are timelines order by the ITEM's date; purpose orders by
    # when it was filed. If those two expressions are identical the kind is
    # decorative.
    orders = dict(re.findall(r'"(\w+)":\s*"([^"]+)"', body))
    assert orders["purpose"] != orders["tracking"], (
        "purpose and tracking sort identically, so the kind changes nothing"
    )


def test_only_a_tracking_category_carries_a_since_marker(router, page):
    """"New since you last looked" is meaningless on a reference shelf.

    Printing an unread count against a methods paper invents an obligation the
    category explicitly does not create — and a number that can never reach
    zero is the thing this dashboard keeps having to remove.
    """
    assert 'if kind == "tracking"' in router, "the marker is not gated on the kind"
    assert "last_seen_at" in router
    assert "last_seen_at" in SCHEMA.read_text(encoding="utf-8"), (
        "last_seen_at is written but not declared in schema.sql, so the other "
        "computer will not have the column"
    )
    assert "kind == 'tracking'" in page, "the page shows the marker regardless of kind"


def test_the_picker_does_not_hardcode_its_host(picker=None):
    """The picker is opened from two surfaces whose rows differ.

    A hardcoded `closest .fw-row` matched nothing on a library row, so the
    click was silently inert — the worst failure an HTMX control has, because
    it looks exactly like a working one.
    """
    src = PICKER.read_text(encoding="utf-8")
    assert 'hx-target="{{ target }}"' in src, "the swap target is not parameterised"
    # STRIP THE COMMENTS FIRST. The note explaining this very fix quotes the
    # old selector, so a naive search finds the string in prose and fails a
    # file that is correct. Six times now a check here has matched the
    # commentary rather than the markup.
    markup = re.sub(r"\{#.*?#\}", "", src, flags=re.S)
    assert "closest .fw-row" not in markup, (
        "the picker still names one host's row class in its markup"
    )


def test_attachment_categories_reach_the_work_they_belong_to(router):
    """Evidence filed against a project that never shows on the project is
    evidence you will not find when you need it."""
    assert "def kept_by_ref" in router, "nothing exposes per-ref counts"
    work = (ROOT / "system/app-py/templates/partials/work_projects.html").read_text(encoding="utf-8")
    learn = (ROOT / "system/app-py/templates/partials/today_learning.html").read_text(encoding="utf-8")
    assert "p.kept" in work, "the project card does not show what is filed against it"
    assert "sl.kept" in learn, "the course slot does not show what is filed against it"


def test_membership_is_a_join_not_a_column(router):
    """One paper belongs on several categories at once.

    Kept for its method, filed against a project, and part of a tracked
    subject — all three are true of the same paper, and a single column would
    force a choice that loses two of them.
    """
    assert "library_shelf_items" in router
    schema = SCHEMA.read_text(encoding="utf-8")
    assert "PRIMARY KEY (shelf, kind, item_id)" in schema, (
        "membership is not keyed on the triple, so one item cannot sit on two "
        "categories"
    )
