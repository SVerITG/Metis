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

# The two tests below asserted a search FIELD on the Today page. That field was
# removed on 2026-09-02 and replaced by one button in the top bar opening a
# dialog — there had been two always-open inputs 150px apart calling DIFFERENT
# endpoints, so the same question got two answers. The requirements they were
# protecting are unchanged and still checked, just at the new location: ONE
# search, pointed at unified-search, with a labelled input.

def test_there_is_exactly_one_search_in_the_chrome():
    """One search control, not two. This is the defect that prompted the change:
    a box in the bar and a box on Today, calling different endpoints."""
    base = (ROOT / "system" / "app-py" / "templates" / "base.html").read_text(encoding="utf-8")
    today = (ROOT / "system" / "app-py" / "templates" / "today.html").read_text(encoding="utf-8")
    assert 'id="search-modal-input"' in base, "no search field in the dialog"
    assert base.count('type="search"') == 1, (
        "base.html has more than one search input again — the whole point of the "
        "dialog is that there is one"
    )
    assert 'type="search"' not in today, (
        "Today has its own search box again; it is the second one, and the two "
        "answered the same question differently"
    )
    assert 'class="t-searchbtn"' in base, "no button to open the dialog"


def test_search_reuses_unified_search():
    """A second search that could answer the same question differently is worse
    than none, so the dialog points at knowledge.py's unified-search."""
    base = (ROOT / "system" / "app-py" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "/api/partial/knowledge/unified-search" in base
    assert 'id="search-modal-results"' in base


def test_the_search_input_is_labelled():
    base = (ROOT / "system" / "app-py" / "templates" / "base.html").read_text(encoding="utf-8")
    assert 'aria-label="Search papers, notes, meetings and memory"' in base, (
        "an input with no label is unusable by screen reader"
    )
    assert 'role="dialog"' in base and 'aria-modal="true"' in base, (
        "a modal that does not announce itself traps a screen reader in the page behind"
    )
    css = (ROOT / "system" / "app-py" / "static" / "styles.css").read_text(encoding="utf-8")
    assert ".sr-only" in css, "the visually-hidden label needs the class to exist"


def test_search_dialog_can_be_dismissed_without_a_mouse():
    """Escape must close it, and the slash shortcut must not fire while typing."""
    js = (ROOT / "system" / "app-py" / "static" / "app.js").read_text(encoding="utf-8")
    assert "closeSearch()" in js
    esc = js[js.index("if (e.key === 'Escape')"):]
    assert "closeSearch" in esc[:220], "Escape does not reach the search dialog"
    assert "_isTyping" in js, (
        "a bare '/' shortcut with no typing guard steals the slash from every "
        "text field on the page, including the dialog's own input"
    )


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


# ── 5. a fold must SAY which way it is folded ────────────────────────────────
#
# Written 2026-09-01, after "why does the morning briefing not collapse". It
# always collapsed — `#morning-brief-body` went to `display:none` on every
# click. What was missing was any evidence on screen that it had: the button
# was rendered only when the server said `collapsed`, and its label came from
# that same server-side flag, so it still read "read the rest" while the rest
# was open. A control that keeps its opening label while open is indis-
# tinguishable from a control that does nothing.
#
# These are static assertions on purpose. The behaviour is driven from a browser
# in scratch checks, but the two properties that regressed are visible in the
# source and cheap to hold here.

BRIEF_TPL = ROOT / "system" / "app-py" / "templates" / "partials" / "today_morning_brief.html"


def test_the_brief_toggle_is_rendered_in_both_states():
    """It used to live inside `{% if collapsed %}`, so the only obvious way to
    re-close an opened brief was a chevron most readers never find."""
    # Jinja COMMENTS first. The template explains this very defect in prose,
    # quoting `{% if collapsed %}` — and an earlier draft of this test read that
    # sentence as markup and failed on the fix it was written to protect. A
    # scanner that cannot tell a template from a description of one will keep
    # finding things that are not there.
    src = re.sub(r"{#.*?#}", "", BRIEF_TPL.read_text(encoding="utf-8"), flags=re.S)
    m = re.search(r'<button[^>]*class="brief-more"', src)
    assert m, "the brief's disclosure button is gone"
    # Walk back to the nearest enclosing Jinja conditional and make sure it is
    # not keyed on `collapsed`.
    before = src[:m.start()]
    opens = re.findall(r"{%-?\s*(if|endif)([^%]*)%}", before)
    depth, guards = 0, []
    for kind, expr in reversed(opens):
        if kind == "endif":
            depth += 1
        else:
            if depth == 0:
                guards.append(expr)
            else:
                depth -= 1
    assert not any("collapsed" in g for g in guards), (
        f"the button is still gated on `collapsed` ({guards}) — it will be "
        "missing exactly when the reader wants to close the brief again"
    )


def test_toggling_the_brief_rewrites_its_own_label():
    """The label, the aria state and the lede clamp must all move with the fold.
    Any one of them left behind is a fold that looks stuck."""
    src = re.sub(r"{#.*?#}", "", BRIEF_TPL.read_text(encoding="utf-8"), flags=re.S)
    fn = src[src.index("function toggleBrief()"):]
    fn = fn[: fn.index("\n}") + 2]
    for needle, why in [
        ("aria-expanded", "screen readers are told the old state"),
        ("show less", "the button keeps its opening label while open"),
        ("is-folded", "the lede stays on screen, so closing leaves prose behind"),
    ]:
        assert needle in fn, f"toggleBrief() does not touch {needle!r} — {why}"


def test_a_folded_brief_leaves_no_prose_behind():
    """A collapsed brief must collapse — the whole way.

    This test used to assert the opposite, and it was right to at the time: the
    lede was clamped to three lines so that folding visibly changed something
    while still saying enough to decide whether to open the rest. The researcher
    asked for the other trade on 2026-09-04 — "see that the morning briefing
    collapses completely when asked so, not the three lines that are left like
    now" — so the class hides the lede outright.

    Nothing is actually lost: the header keeps the date and the control keeps the
    word count, so a closed brief still says what it is and how long it is.
    Measured after the change: the panel goes from 1170px to 118px.
    """
    css = (ROOT / "system" / "app-py" / "static" / "styles.css").read_text(encoding="utf-8")
    m = re.search(r"\.brief-lede\.is-folded\s*\{([^}]*)\}", css)
    assert m, ".brief-lede.is-folded is not defined, so folding leaves the lede on screen"
    body = m.group(1)
    assert "display" in body and "none" in body, (
        "the folded lede is no longer hidden. If this went back to "
        "`-webkit-line-clamp`, three lines of the brief stay on screen after "
        "collapsing, which is what was reported as not collapsing at all"
    )
    assert "line-clamp" not in body, (
        "the clamp is back — a clamped lede is a partly-open brief"
    )
