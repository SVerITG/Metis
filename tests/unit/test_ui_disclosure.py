"""The progressive-disclosure primitives, and the invariants they exist to hold.

Built 2026-08-25 after an audit of the Today surface. The audit's headline number
was WRONG on the first pass — it counted hidden DOM, reporting 4,894 "visible"
words when the truth was 2,447, because the news rail is 98% collapsed already.
That correction is the reason the first test here exists: a measurement that
cannot tell hidden content from shown content will mis-rank every panel.

The invariants:
  1. A panel with nothing to say occupies no space.
  2. A peek never produces an inner scrollbar and never silently drops items.
  3. A count on the surface is a delta you can act on; the total is demoted.
  4. Disclosure state is remembered, so the shape of the page belongs to the reader.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "app-py"))

ui = pytest.importorskip("ui")


# ── 1. empty means empty ─────────────────────────────────────────────────────

def test_nothing_renders_no_visible_box():
    out = ui.nothing()
    assert "<div" not in out and "panel" not in out
    assert re.sub(r"<!--.*?-->", "", out).strip() == ""


def test_a_zone_with_no_body_is_nothing():
    """A fold whose contents are empty must not render a clickable header that
    opens onto nothing."""
    assert ui.zone("Title", "", key="k") == ui.nothing()


# ── 2. peek keeps everything, hides some ─────────────────────────────────────

def test_peek_shows_the_limit_and_keeps_the_rest():
    items = [f"<p>item {i}</p>" for i in range(12)]
    out = ui.peek(items, key="t", limit=5)
    for i in range(12):
        assert f"item {i}" in out, f"peek dropped item {i}"
    assert 'class="ui-peek-rest"' in out
    assert "hidden" in out
    assert "7 more" in out


def test_peek_under_the_limit_has_no_toggle():
    out = ui.peek(["<p>a</p>", "<p>b</p>"], key="t", limit=5)
    assert "ui-peek-toggle" not in out


def test_peek_never_creates_an_inner_scroll_region():
    """A scroll region inside a page that also scrolls is the defect this was
    built to remove."""
    out = ui.peek([f"<p>{i}</p>" for i in range(30)], key="t", limit=3)
    assert "overflow" not in out
    assert "max-height" not in out


def test_peek_of_nothing_is_nothing():
    assert ui.peek([], key="t") == ""


def test_peek_toggle_is_a_real_button_with_aria():
    out = ui.peek([f"<p>{i}</p>" for i in range(9)], key="t", limit=4)
    assert "<button" in out
    assert 'aria-expanded="false"' in out
    m = re.search(r'aria-controls="([^"]+)"', out)
    assert m, "toggle must name what it controls"
    assert f'id="{m.group(1)}"' in out, "aria-controls must point at a real element"


# ── 3. the counter rule ──────────────────────────────────────────────────────

def test_a_delta_leads_and_the_total_is_demoted():
    out = ui.delta_count("test.key.unused", total=1433, newer=12)
    assert "12" in out
    assert "ui-delta" in out
    assert "1,433" in out and "ui-total" in out
    # the growing total must not be the loud element
    assert out.index("ui-delta") < out.index("ui-total")


def test_no_total_shown_when_it_adds_nothing():
    out = ui.delta_count("test.key.unused", total=3, newer=3)
    assert "ui-total" not in out


def test_zero_new_says_so_quietly():
    out = ui.delta_count("test.key.unused", total=900, newer=0)
    assert "nothing new" in out
    assert "ui-delta--quiet" in out


def test_since_label_is_words_not_a_timestamp():
    """A delta is only useful if the reader knows what it is a delta from, and a
    raw timestamp makes them do arithmetic."""
    import datetime as dt
    now = dt.datetime.now()
    assert ui.since_label((now - dt.timedelta(minutes=10)).isoformat()) == "in the last hour"
    assert ui.since_label((now - dt.timedelta(days=1)).isoformat()) == "since yesterday"
    assert "so far" == ui.since_label("")
    assert "so far" == ui.since_label("not-a-date")
    for probe in ("", "not-a-date", (now - dt.timedelta(days=3)).isoformat()):
        assert not re.search(r"\d{4}-\d{2}-\d{2}", ui.since_label(probe))


# ── 4. state is remembered, and styled from existing tokens ──────────────────

def test_disclosure_state_is_keyed_for_persistence():
    assert 'data-peek-key="lit"' in ui.peek(["<p>x</p>"] * 9, key="lit", limit=3)
    assert 'data-zone-key="mem"' in ui.zone("T", "<p>body</p>", key="mem")


def test_the_javascript_guards_localstorage():
    """localStorage throws outright in a private window or with site data
    blocked; the page must still work with none."""
    js = (ROOT / "system" / "app-py" / "static" / "app.js").read_text(encoding="utf-8")
    block = js[js.index("metis.disclosure."):]
    assert "try {" in block and "catch" in block
    assert "htmx:afterSwap" in block, "state must survive an HTMX swap"


def test_styles_use_existing_tokens_not_new_colours():
    """The audit's conclusion was that the visual system is not the problem. A
    disclosure primitive that introduces its own palette contradicts that."""
    css = (ROOT / "system" / "app-py" / "static" / "styles.css").read_text(encoding="utf-8")
    block = css[css.index("PROGRESSIVE DISCLOSURE"):]
    literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", block)
    assert not literals, f"hard-coded colours in the disclosure CSS: {literals}"


# ── 5. the closing items: search, and a real document outline ────────────────

def test_today_has_a_search_that_reuses_the_existing_one():
    """A second search that could answer the same question differently is worse
    than none, so Today points at knowledge.py's unified-search."""
    t = (ROOT / "system" / "app-py" / "templates" / "today.html").read_text(encoding="utf-8")
    assert 'id="today-find-input"' in t
    assert "/api/partial/knowledge/unified-search" in t
    assert 'id="today-find-results"' in t


def test_the_search_input_is_labelled():
    t = (ROOT / "system" / "app-py" / "templates" / "today.html").read_text(encoding="utf-8")
    assert 'for="today-find-input"' in t, "an input with no label is unusable by screen reader"
    css = (ROOT / "system" / "app-py" / "static" / "styles.css").read_text(encoding="utf-8")
    assert ".sr-only" in css, "the visually-hidden label needs the class to exist"


def _has_class(html: str, tag: str, token: str) -> bool:
    """Does any `tag` carry `token` among its classes?

    Matching the literal attribute string broke the moment a second class was
    added — which is exactly what a class attribute is for. A class is a SET;
    test it as one.
    """
    for m in re.finditer(rf"<{tag}\b[^>]*class=\"([^\"]*)\"", html):
        if token in m.group(1).split():
            return True
    return False


def test_panels_that_had_no_heading_now_have_one():
    """Both carried a visual label with no place in the document outline."""
    parts = ROOT / "system" / "app-py" / "templates" / "partials"
    resume = (parts / "today_resume_card.html").read_text(encoding="utf-8")
    bridges = (parts / "today_brief_bridges.html").read_text(encoding="utf-8")
    assert _has_class(resume, "h2", "sec-label") and "Where you left off" in resume
    assert _has_class(bridges, "h[23]", "sec-label") and "Connections to your research" in bridges


def test_search_pluralises_correctly():
    """Rendered '2 ENTRYIES' — ENTRY and IES concatenated instead of ENTR + Y/IES."""
    tpl = (ROOT / "system" / "app-py" / "templates" / "partials"
           / "knowledge_unified_search.html").read_text(encoding="utf-8")
    assert "ENTRYIES" not in tpl
    assert "ENTRY{%" not in tpl, "the concatenation bug is back"
