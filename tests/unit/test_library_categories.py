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


# ── the interest profile must not name anyone's field ────────────────────────

RELEVANCE = ROOT / "system/mcp-server/src/metis_mcp/tools/relevance.py"


def test_the_scorer_names_no_ones_speciality():
    """Subject names belong in the reader's data, not in a shared module.

    `relevance.py` ships in BOTH repositories, including the domain-agnostic
    base shell. Two lists of phrases naming one researcher's speciality used to
    live here, which compiled that person's field into a general-purpose tool
    and handed anyone else who installed it an interest profile tilted towards a
    subject they may not work on. The mechanism is code; which subjects get
    which weight is `user_topics.band`.
    """
    src = RELEVANCE.read_text(encoding="utf-8")
    # A sample across several specialities, so this test is not itself a list of
    # one person's interests.
    leaks = [w for w in (
        "sleeping sickness", "trypanosom", "tsetse", "schistosom", "leishman",
        "gambiense", "malaria", "tuberculosis", "oncology", "cardiology",
    ) if w in src.lower()]
    assert not leaks, (
        f"the shared scorer names a speciality: {leaks} — put it in "
        f"user_topics.band instead"
    )


def test_topic_bands_come_from_the_database():
    src = RELEVANCE.read_text(encoding="utf-8")
    assert "user_topics" in src and "band" in src, "bands are not read from data"
    assert '_TOPIC_BANDS = ("field", "method")' in src, (
        "the band names are not declared in one place"
    )
    # The weights must still separate: a standing subject above a broad topic,
    # a broad topic above an occasional method.
    m = re.search(r"BAND_WEIGHTS = \{(.*?)\}", src, re.S)
    assert m, "no weight map"
    w = {k: float(v) for k, v in re.findall(r'"(\w+)":\s*([0-9.]+)', m.group(1))}
    assert w["project"] == w["course"] == 1.00, "own work is not full weight"
    assert w["field"] > w["topic"] > w["method"] > w["task"], (
        f"the bands do not order as intended: {w}"
    )


def test_a_category_can_be_scoped_to_a_stream():
    """The interests differ by stream, so the picker must not offer all of them.

    Matched on the delimited list rather than a bare LIKE: `LIKE '%news%'` would
    also match a stream called "newsletters", and that bug would not surface
    until such a stream existed.
    """
    src = ROUTER.read_text(encoding="utf-8")
    assert "applies_to" in src, "categories cannot be scoped to a stream"
    assert "stream" in src
    assert "','" in src or "', '" in src or "|| ','" in src, (
        "the stream match does not appear to be delimited"
    )
    assert "applies_to" in SCHEMA.read_text(encoding="utf-8"), (
        "applies_to is used but not declared in schema.sql"
    )
