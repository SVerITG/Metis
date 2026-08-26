"""The navbar's htmx contract must not leak into its children.

Found 2026-08-26: the dashboard "always launches to the Learning surface, even
when you click on Today". The cause was not routing — `/`, `/today` and
`/api/tab/today` all served Today correctly. It was htmx attribute inheritance.

htmx resolves hx-target, hx-select and hx-push-url with `getClosestAttributeValue`,
which walks UP the DOM. The Learning nav item contains a child that makes its own
request — the `n-meta` badge polling `/api/partial/learning/nav-meta` on load and
every 300s. That child inherited the item's whole navigation contract, so a
fragment reading "4 courses" ran with hx-push-url="/learning" and rewrote the
address bar seconds after every page load.

These tests pin the two properties that stop it happening again.
"""
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "system" / "app-py" / "templates" / "base.html"

NAV_ATTRS = ("hx-target", "hx-select", "hx-push-url", "hx-swap")


@pytest.fixture(scope="module")
def nav_items():
    # Strip Jinja tags so BeautifulSoup sees plain HTML attributes.
    html = re.sub(r"\{%.*?%\}", "", BASE.read_text(encoding="utf-8"), flags=re.S)
    html = re.sub(r"\{\{.*?\}\}", "", html, flags=re.S)
    soup = BeautifulSoup(html, "html.parser")
    items = [d for d in soup.find_all("div", class_="nav-item") if d.get("hx-get")]
    assert items, "no navigating nav items found — did base.html change shape?"
    return items


def test_every_navigating_item_blocks_inheritance(nav_items):
    """A child that fetches must not inherit where the parent navigates to."""
    leaky = [i.get("data-tab") for i in nav_items if i.get("hx-disinherit") != "*"]
    assert not leaky, f"nav items without hx-disinherit=\"*\": {leaky}"


def test_the_learning_badge_is_the_case_that_broke(nav_items):
    """Regression: the one nav item with a self-fetching child."""
    learning = next(i for i in nav_items if i.get("data-tab") == "learning")
    badge = learning.find(attrs={"hx-get": "/api/partial/learning/nav-meta"})
    assert badge is not None, "the learning nav badge moved — re-check inheritance"
    assert learning.get("hx-disinherit") == "*", (
        "the badge would inherit hx-push-url=/learning and rewrite the URL"
    )


def test_children_that_fetch_are_covered_everywhere(nav_items):
    """Any future badge gets the same protection, not just Learning's."""
    for item in nav_items:
        for child in item.find_all(attrs={"hx-get": True}):
            if child is item:
                continue
            assert item.get("hx-disinherit") == "*", (
                f"{item.get('data-tab')} has a fetching child with no disinherit"
            )


def test_select_of_an_id_pairs_with_outer_html(nav_items):
    """hx-select hands htmx the matched ELEMENT. Swapping it as innerHTML nests a
    second #tab-content inside the first on every click — duplicate IDs."""
    for item in nav_items:
        if item.get("hx-select") == "#tab-content":
            assert item.get("hx-swap") == "outerHTML", (
                f"{item.get('data-tab')}: innerHTML + hx-select=#tab-content nests"
            )
