"""A focus surface that is the same shape for every focus is one focus's surface.

Written 2026-09-03 after the researcher opened the second focus he had ever made
and reported understanding nothing on it: no use for the safe, the brief, "what
changed" or the thinking pane, and "many things/sections/functionalities that are
only for the [first] shelf. Every shelf is different."

He was right. `focus.html` hard-coded nine sections because the first focus was a
subject to *stay current on*, and the template grew around it. A reference focus
— one you open to look something up — inherited a safe it never fills, a brief it
never asks for, and a thinking pane it never uses, while having nowhere to put
the lookup tool that is the entire reason it exists. A lookup tool had just been built for that
focus and was unreachable from it.

So the shape is data. These protect the four properties that makes it work.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "system" / "app-py"
FOCUS_PY = APP / "routers" / "focus.py"
FOCUS_HTML = APP / "templates" / "focus.html"
COUNTS = APP / "templates" / "partials" / "focus_counts.html"
MAIN = APP / "main.py"
BASE = APP / "templates" / "base.html"


@pytest.fixture(scope="module")
def focus_py() -> str:
    return FOCUS_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def focus_html() -> str:
    return FOCUS_HTML.read_text(encoding="utf-8")


def _known(src: str) -> list[str]:
    m = re.search(r"KNOWN_SECTIONS\s*=\s*\[(.*?)\]", src, re.S)
    assert m, "KNOWN_SECTIONS is gone"
    return re.findall(r'"([a-z]+)"', m.group(1))


# ── 1 · the registry and the template must agree ────────────────────────────

def test_every_known_section_has_a_template_branch(focus_py, focus_html):
    """A key the router accepts and the template ignores renders NOTHING, with
    no error anywhere — the exact failure mode that is impossible to diagnose
    from the page."""
    missing = [k for k in _known(focus_py)
               if f'"{k}" in sections' not in focus_html]
    assert not missing, (
        "these section keys are accepted by the router but the template has no "
        f"branch for them, so declaring one renders an empty page: {missing}"
    )


def test_every_template_branch_is_a_known_section(focus_py, focus_html):
    """The other direction: a branch keyed on a name the router will never pass
    is dead markup that looks live."""
    used = set(re.findall(r'"([a-z]+)" in sections', focus_html))
    unknown = sorted(used - set(_known(focus_py)))
    assert not unknown, (
        f"the template guards on keys the router cannot produce: {unknown}"
    )


# ── 2 · nothing that predates the change may move ───────────────────────────

def test_an_empty_sections_list_means_the_historical_default(focus_py):
    """The first focus has no `sections` value and must render exactly as before."""
    m = re.search(r"def _sections_for\(.*?\n(.*?)(?=\n@router\.|\ndef )", focus_py, re.S)
    assert m, "could not locate _sections_for"
    body = m.group(1)
    assert "DEFAULT_SECTIONS" in body, "no default — an old focus would render blank"
    d = re.search(r"DEFAULT_SECTIONS\s*=\s*\[(.*?)\]", focus_py, re.S)
    assert d, "DEFAULT_SECTIONS is gone"
    default = re.findall(r'"([a-z]+)"', d.group(1))
    # The nine-section surface as it stood on 2026-09-02, minus the two added
    # for reference focuses. If this list shrinks, an existing focus lost a
    # section without anyone asking for that.
    for expected in ("pulse", "overview", "safe", "brief", "thinking", "feed", "reading"):
        assert expected in default, (
            f"'{expected}' left the default, so every pre-existing focus just "
            "lost that section"
        )


def test_a_broken_sections_value_falls_back_rather_than_blanking(focus_py):
    m = re.search(r"def _sections_for\(.*?\n(.*?)(?=\n@router\.|\ndef )", focus_py, re.S)
    body = m.group(1)
    assert "except Exception" in body, "bad JSON in the column would 500 the page"
    assert "or list(DEFAULT_SECTIONS)" in body, (
        "a sections list that filters down to nothing renders a blank surface; "
        "it must fall back"
    )


# ── 3 · both render sites of the counts strip must supply what it reads ─────

def test_the_counts_strip_reads_sections_and_both_sites_pass_it(focus_py):
    """`focus_counts.html` is rendered by the page AND out-of-band after a
    verdict. A partial reading a variable only one site passes falls back to
    showing everything — which would put the safe and thinking counts back onto
    a focus that has neither. Same defect class as the date control that was
    missing on one of two project-task render paths."""
    counts = COUNTS.read_text(encoding="utf-8")
    assert "sections" in counts, "the counts strip no longer varies by focus"
    # _ctx is the shared context builder both sites use.
    m = re.search(r"def _ctx\(.*?\n(.*?)(?=\n@router\.|\ndef )", focus_py, re.S)
    assert m, "could not locate _ctx"
    assert '"sections": _sections_for(area)' in m.group(1), (
        "_ctx does not carry `sections`, so the out-of-band counts swap renders "
        "without it and silently shows every cell again"
    )


# ── 4 · the navbar must not pay for the lens ────────────────────────────────

def test_the_navbar_reads_a_stored_count_not_a_live_lens_query():
    """The measurement that decided this design.

    The focus lens is `LIKE %term%` across ~17 terms over ~4,000 briefs: 19-29 ms
    per focus, measured 2026-09-03. `_focus_shelf` runs on EVERY page render in
    the app, so computing "how many new items" there would have added ~48 ms to
    every page. Same family as the `CREATE TABLE IF NOT EXISTS` that went on a
    render path earlier in this same session.
    """
    src = MAIN.read_text(encoding="utf-8")
    m = re.search(r"def _focus_shelf\(.*?\n(.*?)(?=\ndef |\ntemplates\.env)", src, re.S)
    assert m, "could not locate _focus_shelf"
    # Strip `#` comments before looking for banned constructs. The comment in
    # that function explains why a LIKE query must not be there, and quotes the
    # word — so the first version of this test failed on correct code by
    # matching its own rationale. Fourth instance of that in one session; the
    # rule is that a check for an absent string reads the CODE, never the prose
    # about the code.
    body = "\n".join(re.sub(r"#.*$", "", ln) for ln in m.group(1).split("\n"))
    assert "n_new" in body, "the navbar cannot show a new-item marker at all"
    for banned, why in (
        ("LIKE", "a LIKE lens query on the navbar path costs ~20 ms per focus"),
        ("focus_news", "calling the lens helper on every page render"),
        ("focus_reading", "calling the lens helper on every page render"),
        ("focus_pulse", "focus_pulse runs the full lens twice"),
    ):
        assert banned not in body, f"_focus_shelf now does {banned}: {why}"


def test_the_marker_falls_back_to_the_slot_number():
    """A focus with nothing new must still show its slot, not an empty gap."""
    base = BASE.read_text(encoding="utf-8")
    m = re.search(r"\{% if f\.n_new %\}(.*?)\{% endif %\}", base, re.S)
    assert m, "the navbar no longer distinguishes new items from the slot number"
    assert "n-meta--new" in m.group(1), "the new-item count is not visually marked"
    assert "f.shelf_slot" in base, "the slot number fallback is gone"


# ── 5 · the tools section is what makes a reference focus usable ────────────

def test_a_focus_can_carry_links_and_they_are_validated(focus_py):
    m = re.search(r"def _links_for\(.*?\n(.*?)(?=\n@router\.|\ndef )", focus_py, re.S)
    assert m, "focuses can no longer carry tools"
    body = m.group(1)
    assert "except Exception" in body, "bad JSON in `links` would 500 the page"
    assert 'l.get("title")' in body and 'l.get("href")' in body, (
        "a link without a title or href renders an empty card that goes nowhere"
    )


def test_the_tools_section_only_appears_when_there_is_something_in_it(focus_html):
    assert '{% if "tools" in sections and links %}' in focus_html, (
        "the tools section renders its heading even with no links, which is an "
        "empty panel advertising a feature the focus does not have"
    )
