"""The reading stack: one triage store, and the promises it makes.

Built 2026-08-26. The researcher: "The today page is really to see what is new, open them
if I want to see them straight away but often that they get categorized for
future reading so they become a stack of things to read connected to the News
and Library surfaces."

Before this, that one idea had three implementations and one hole — papers had
triage on the Library surface, focus areas had `focus_verdict`, and News had
NOTHING: seven tabs, 337 links, zero actions, which is why clicking around it
felt inert.

The properties under test:
  1. Nothing is ever deleted by a verdict — declining folds, it does not remove.
  2. A paper's verdict is mirrored onto the columns the Library surface reads,
     so the two surfaces cannot disagree.
  3. `added_at` is NOT claimed by a one-click save: on this schema it means
     "acquired, with a PDF", and a save that set it would make the library lie.
  4. States are read for many items in ONE query — the news grid renders 60.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

S = pytest.importorskip("metis_mcp.tools.stack")


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A throwaway database — never the live one, which the dashboard is holding."""
    monkeypatch.setattr(S.paths, "db", tmp_path / "stack_t.db")
    with S.connect(S.paths.db) as con:
        S.ensure_schema(con)
        con.execute("CREATE TABLE IF NOT EXISTS new_publications ("
                    "id INTEGER PRIMARY KEY, title TEXT, added_at TEXT, "
                    "dismissed_at TEXT, read_at TEXT)")
        con.execute("INSERT INTO new_publications (id, title, added_at, "
                    "dismissed_at, read_at) VALUES (7, 'A paper', '', '', '')")
    return S.paths.db


# ── 1. the four verbs ────────────────────────────────────────────────────────

@pytest.mark.parametrize("state", ["saved", "later", "declined", "read"])
def test_every_state_round_trips(db, state):
    S.set_state("news", "nb-1", state, "A headline", "https://x.test")
    got = S.get_state("news", "nb-1")
    assert got["state"] == state
    assert got["title"] == "A headline"


def test_a_verdict_never_deletes_the_row(db):
    S.set_state("news", "nb-1", "declined", "Not for me")
    assert S.stack(state="declined")[0]["title"] == "Not for me"
    assert S.counts()["declined"] == 1


def test_restating_replaces_rather_than_duplicating(db):
    S.set_state("news", "nb-1", "later", "One headline")
    S.set_state("news", "nb-1", "read", "One headline")
    assert S.counts()["total"] == 1
    assert S.get_state("news", "nb-1")["state"] == "read"


def test_a_bare_restate_keeps_what_was_known(db):
    """A button that carries only an id must not blank the title."""
    S.set_state("news", "nb-1", "later", "The full headline", "https://x.test", "BBC")
    S.set_state("news", "nb-1", "read")
    got = S.get_state("news", "nb-1")
    assert got["title"] == "The full headline"
    assert got["url"] == "https://x.test"
    assert got["source"] == "BBC"


def test_an_unknown_state_is_refused(db):
    with pytest.raises(ValueError):
        S.set_state("news", "nb-1", "maybe", "x")
    with pytest.raises(ValueError):
        S.set_state("invention", "nb-1", "later", "x")


def test_clearing_returns_to_undecided(db):
    S.set_state("news", "nb-1", "later", "x")
    S.clear_state("news", "nb-1")
    assert S.get_state("news", "nb-1") == {}


# ── 2. write-through, so two surfaces cannot disagree ────────────────────────

def test_declining_a_paper_dismisses_it_where_the_library_looks(db):
    S.set_state("paper", "7", "declined", "A paper")
    with S.connect(db) as con:
        r = con.execute("SELECT dismissed_at FROM new_publications WHERE id=7").fetchone()
    assert r["dismissed_at"], "the Library surface reads this column directly"


def test_reading_a_paper_marks_it_read_and_undismisses(db):
    S.set_state("paper", "7", "declined", "A paper")
    S.set_state("paper", "7", "read", "A paper")
    with S.connect(db) as con:
        r = con.execute("SELECT read_at, dismissed_at FROM new_publications "
                        "WHERE id=7").fetchone()
    assert r["read_at"] and not r["dismissed_at"]


def test_saving_does_not_claim_the_paper_was_acquired(db):
    """`added_at` means 'in the library, with a PDF'. A one-click save is not that."""
    S.set_state("paper", "7", "saved", "A paper")
    with S.connect(db) as con:
        r = con.execute("SELECT added_at FROM new_publications WHERE id=7").fetchone()
    assert not r["added_at"], "a save must not make the library claim it holds a PDF"


def test_clearing_a_paper_clears_the_owning_columns_too(db):
    S.set_state("paper", "7", "read", "A paper")
    S.clear_state("paper", "7")
    with S.connect(db) as con:
        r = con.execute("SELECT read_at, dismissed_at FROM new_publications "
                        "WHERE id=7").fetchone()
    assert not r["read_at"] and not r["dismissed_at"]


def test_write_through_survives_a_missing_table(db, monkeypatch):
    """An older install has a different column set; the stack must still work."""
    with S.connect(db) as con:
        con.execute("DROP TABLE new_publications")
    S.set_state("paper", "7", "declined", "A paper")
    assert S.get_state("paper", "7")["state"] == "declined"


# ── 3. tags ──────────────────────────────────────────────────────────────────

def test_tags_are_normalised(db):
    S.set_state("news", "nb-1", "later", "x", tags="  Sleeping Sickness , DHIS2,dhis2 , ")
    assert S.get_state("news", "nb-1")["tags"] == "sleeping sickness, dhis2"


def test_tagging_an_untouched_item_puts_it_on_the_stack(db):
    """Tagging something IS a decision to come back to it."""
    S.set_tags("news", "nb-9", "later-reading")
    assert S.get_state("news", "nb-9")["state"] == "later"


def test_tag_filter_matches_whole_tags_only(db):
    S.set_state("news", "a", "later", "A", tags="hat")
    S.set_state("news", "b", "later", "B", tags="hat surveillance")
    assert [i["item_id"] for i in S.stack(tag="hat")] == ["a"]


def test_all_tags_counts_and_orders_by_use(db):
    S.set_state("news", "a", "later", "A", tags="ntd, hat")
    S.set_state("news", "b", "later", "B", tags="ntd")
    assert S.all_tags() == [("ntd", 2), ("hat", 1)]


# ── 4. reading many at once ──────────────────────────────────────────────────

def test_states_for_is_one_query_for_the_whole_grid(db):
    for i in range(60):
        if i % 3 == 0:
            S.set_state("news", f"nb-{i}", "later", f"item {i}")
    got = S.states_for("news", [f"nb-{i}" for i in range(60)])
    assert len(got) == 20
    assert got["nb-0"]["state"] == "later"


def test_states_for_tolerates_an_empty_or_ragged_list(db):
    assert S.states_for("news", []) == {}
    assert S.states_for("news", [None, "", "nb-x"]) == {}


def test_counts_covers_every_state(db):
    """`counts()` must report a key for EVERY state the store recognises.

    Derived from `S.STATES` rather than written out. The literal list that used
    to stand here is the same mistake that produced the defect this suite exists
    to catch: the field digest had the four verbs typed into a query, the store
    gained a fifth, and the queue silently stopped clearing for one of them. A
    check that repeats a constant stops testing the constant and starts testing
    the copy.
    """
    S.set_state("news", "a", "later", "A")
    S.set_state("news", "b", "saved", "B")
    c = S.counts()
    assert c["later"] == 1 and c["saved"] == 1 and c["total"] == 2
    assert set(c) == set(S.STATES) | {"total"}
    assert "dismissed" in c, (
        "the verdict that clears a row without judging its subject is missing"
    )


def test_dismissed_is_not_read_as_a_rejection(db):
    """Only `declined` may count as evidence against a subject.

    If `dismissed` ever joins NEGATIVE, clearing a busy morning's queue teaches
    the ranker that those topics are unwanted — which is the fastest way to make
    a relevance model wrong about someone, and it would happen silently.
    """
    assert S.NEGATIVE == ("declined",), (
        f"NEGATIVE is {S.NEGATIVE}; a verdict that only clears a row must not "
        f"be read as disinterest"
    )
    assert "dismissed" in S.JUDGED, "Dismiss must clear the row"
    assert "dismissed" not in S.NEGATIVE


# ── 5. the surface contract ──────────────────────────────────────────────────

def test_the_news_card_is_not_one_giant_link_any_more():
    """The reason the News surface had zero actions: a button inside an anchor
    navigates away instead of firing."""
    tpl = (ROOT / "system" / "app-py" / "templates" / "partials"
           / "news_tab.html").read_text(encoding="utf-8")
    assert '<a class="nf-card"' not in tpl, "the card-wide anchor is back"
    assert "item(" in tpl, "the list must render through the shared item macro"


def test_one_item_component_serves_every_list():
    """Nine list-item shapes existed before the design audit. The lists that
    carry triage now share one, or 'save' drifts into meaning different things
    on different pages."""
    parts = ROOT / "system" / "app-py" / "templates" / "partials"
    for name in ("news_tab.html", "stack_body.html"):
        tpl = (parts / name).read_text(encoding="utf-8")
        assert 'from "partials/_item.html"' in tpl, f"{name} rolls its own row"


def test_the_action_bar_sends_only_what_the_server_cannot_know():
    """Title, url and source are read from the owning table. Posting them back
    put ~100 KB of already-known strings on a 60-item tab."""
    tpl = (ROOT / "system" / "app-py" / "templates" / "partials"
           / "_item.html").read_text(encoding="utf-8")
    bar = tpl[tpl.index("{% macro actions("):tpl.index("{% macro act(")]
    assert 'name="item_id"' in bar and 'name="kind"' in bar
    for gone in ('name="title"', 'name="url"', 'name="source"'):
        assert gone not in bar, f"{gone} is posted back but already known"


def test_icons_come_from_one_sprite():
    """Six shapes inlined 300 times is 45 KB of the same six words."""
    tpl = (ROOT / "system" / "app-py" / "templates" / "partials"
           / "_item.html").read_text(encoding="utf-8")
    assert "<use href=" in tpl
    base = (ROOT / "system" / "app-py" / "templates"
            / "base.html").read_text(encoding="utf-8")
    for name in ("later", "saved", "read", "declined", "tag", "undo"):
        assert f'id="i-{name}"' in base, f"sprite is missing i-{name}"


def test_every_news_control_carries_tab_period_and_view():
    """Three independent axes on one list. A control that sends only its own
    value silently resets the other two."""
    tpl = (ROOT / "system" / "app-py" / "templates" / "partials"
           / "_news_tabstrip.html").read_text(encoding="utf-8")
    import re
    urls = re.findall(r'hx-get="(/api/partial/news/tab\?[^"]+)"', tpl)
    assert urls, "no tab controls found"
    for u in urls:
        assert "tab=" in u and "period=" in u and "view=" in u, u


def test_section_headings_fold_and_guard_localstorage():
    js = (ROOT / "system" / "app-py" / "static" / "app.js").read_text(encoding="utf-8")
    block = js[js.index("metis.fold.v1"):]
    assert "try {" in block and "catch" in block, "localStorage throws in a private window"
    assert "htmx:afterSwap" in block, "folds must survive an HTMX swap"
    assert "aria-expanded" in block and "tabindex" in block, "a div you can only click is not a control"
    assert "ui-zone-body" in block, "headings already inside a zone must be skipped"
