"""The safe, the taste model, and the promise that nothing is ever removed.

Built 2026-08-26. the researcher asked for a focus where you can "keep or save a new item
or article in a safe, that will be used for further reflection", and decline
others so "similar things are less (not entirely not) suggested in the future".

THE PARENTHESIS IS THE SPECIFICATION, and it is what most of these tests defend.
A declined item may be demoted and folded; it may never disappear. In a research
tool an absence you were never told about is the expensive kind of mistake —
you cannot audit a literature you were silently stopped from being shown.

The second thing under test is the lens-exclusion rule. Every item on an "AI in
health" focus contains "ai" and "health" — they are why it is there. If taste
learned from those, the first decline would down-weight the subject itself and
mute the whole focus in one click. That failure is silent, total, and would look
exactly like "the feature works".
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

F = pytest.importorskip("metis_mcp.tools.focus")


# The four tables a focus READS but does not own. They are created here with the
# columns the queries actually name, because a focus is a lens over other
# people's rows — stub them too thinly and the test fails for a reason that has
# nothing to do with what it is testing.
_BORROWED = {
    "news_briefs": "brief_id TEXT, brief_date TEXT, title TEXT, summary TEXT, "
                   "source_url TEXT, domain TEXT, signal_strength TEXT, created_at TEXT",
    "new_publications": "id INTEGER, title TEXT, journal TEXT, abstract TEXT, "
                        "pub_date TEXT, pub_iso TEXT, discovered_at TEXT, doi TEXT, "
                        "source_url TEXT, entry_kind TEXT, added_at TEXT, read_at TEXT",
    "personal_notes": "note_id TEXT, title TEXT, content TEXT, tags TEXT, created_at TEXT",
    "ideas": "idea_id TEXT, text TEXT, idea_type TEXT, tags TEXT, created_at TEXT, "
             "domain TEXT",
    "pdf_chunks": "id INTEGER, db_id INTEGER, source_file TEXT, title TEXT, "
                  "page_start INTEGER, chunk_text TEXT",
    "knowledge_databases": "id INTEGER, slug TEXT",
}


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A throwaway database.

    Pointing at the live one would compete with the running dashboard for the
    write lock AND pollute the researcher's real focus — both of which happened once
    already on the calendar tests, which is why this fixture exists.
    """
    monkeypatch.setattr(F.paths, "db", tmp_path / "focus_t.db")
    with F.connect(F.paths.db) as con:
        F.ensure_schema(con)
        for name, cols in _BORROWED.items():
            con.execute(f"CREATE TABLE IF NOT EXISTS {name} ({cols})")
    return F.paths.db


@pytest.fixture
def lens(db):
    """A focus whose lens is 'ai' x 'health' — the shape that can eat itself."""
    import json
    with F.connect(db) as con:
        con.execute(
            "INSERT INTO focus_areas (slug, title, keyword_groups, created_at) "
            "VALUES (?,?,?,?)",
            ("t", "AI in health",
             json.dumps([["ai", "machine learning"], ["health", "clinical"]]),
             F._now()))
    return "t"


# ── 1. nothing is ever removed ───────────────────────────────────────────────

def test_sift_returns_every_item_it_was_given(lens):
    """The invariant the whole feature rests on."""
    items = [{"brief_id": f"b{i}", "title": f"item {i} about widgets"}
             for i in range(20)]
    F.judge(lens, "news", "b0", "kept", items[0]["title"])
    F.judge(lens, "news", "b1", "declined", items[1]["title"])
    s = F.sift(lens, items, "news", "title", "brief_id")
    assert s["n_live"] + s["n_muted"] + len(s["decided"]) == len(items)


def test_a_declined_item_is_folded_not_deleted(lens):
    F.judge(lens, "news", "b1", "declined", "Cricket scores from Melbourne")
    items = [{"brief_id": "b1", "title": "Cricket scores from Melbourne"}]
    s = F.sift(lens, items, "news", "title", "brief_id")
    assert len(s["decided"]) == 1
    assert s["decided"][0]["_verdict"] == "declined"


def test_muting_demotes_it_does_not_drop(lens):
    """Two declines sharing a word mute a third item — into `muted`, not oblivion."""
    F.judge(lens, "news", "b1", "declined", "Cricket highlights from Melbourne")
    F.judge(lens, "news", "b2", "declined", "Cricket selectors name the squad")
    items = [{"brief_id": "b3", "title": "Cricket board announces new season"}]
    s = F.sift(lens, items, "news", "title", "brief_id")
    assert s["n_muted"] == 1, "should be demoted"
    assert s["n_live"] == 0
    assert s["muted"][0]["title"] in [i["title"] for i in items], "still present"


def test_one_decline_is_an_opinion_not_a_pattern(lens):
    """A single decline must not reshape the feed."""
    F.judge(lens, "news", "b1", "declined", "Cricket highlights from Melbourne")
    items = [{"brief_id": "b3", "title": "Cricket board announces new season"}]
    s = F.sift(lens, items, "news", "title", "brief_id")
    assert s["n_muted"] == 0
    assert s["n_live"] == 1


# ── 2. the lens must not eat itself ──────────────────────────────────────────

def test_taste_never_learns_the_lens_words(lens):
    """The failure that would mute an entire focus with one click."""
    F.judge(lens, "news", "b1", "declined",
            "AI and machine learning transform clinical health research")
    taste = F.focus_taste(lens)
    for word in ("health", "clinical", "machine", "learning"):
        assert word not in taste, f"taste learned lens word {word!r}"


def test_declining_one_item_does_not_mute_the_subject(lens):
    """The end-to-end version of the above: the focus must survive a decline."""
    F.judge(lens, "news", "b1", "declined",
            "AI and machine learning in clinical health")
    items = [{"brief_id": f"b{i}", "title": f"AI and machine learning in clinical health {i}"}
             for i in range(2, 10)]
    s = F.sift(lens, items, "news", "title", "brief_id")
    assert s["n_muted"] == 0, "one decline muted the whole subject"
    assert s["n_live"] == len(items)


# ── 3. a judgement you can read, and revise ──────────────────────────────────

def test_a_mute_can_always_say_why(lens):
    F.judge(lens, "news", "b1", "declined", "Cricket highlights from Melbourne")
    F.judge(lens, "news", "b2", "declined", "Cricket selectors name the squad")
    s = F.sift(lens, [{"brief_id": "b3", "title": "Cricket board names a season"}],
               "news", "title", "brief_id")
    assert s["muted"][0]["_why"], "a demotion with no reason is indistinguishable from a bug"
    assert "cricket" in s["muted"][0]["_why"]


def test_a_verdict_can_be_changed_and_undone(lens):
    F.judge(lens, "news", "b1", "declined", "A paper about widgets")
    F.judge(lens, "news", "b1", "kept", "A paper about widgets")
    assert [v["verdict"] for v in F.focus_verdicts(lens)] == ["kept"]
    assert len(F.focus_verdicts(lens)) == 1, "re-judging must replace, not duplicate"
    F.unjudge(lens, "news", "b1")
    assert F.focus_verdicts(lens) == []


def test_the_safe_survives_the_feed_moving_on(lens):
    """Titles live on the verdict, so tidying `news_briefs` cannot empty the safe."""
    F.judge(lens, "news", "gone-from-upstream", "kept", "A headline worth keeping",
            "https://example.org/x")
    kept = F.focus_verdicts(lens, "kept")
    assert kept[0]["title"] == "A headline worth keeping"
    assert kept[0]["url"] == "https://example.org/x"


def test_verdict_rejects_anything_that_is_not_a_verdict(lens):
    with pytest.raises(ValueError):
        F.judge(lens, "news", "b1", "maybe", "x")


# ── 4. the counts on the surface ─────────────────────────────────────────────

def test_counts_separate_what_you_made_from_what_only_grows(lens):
    F.judge(lens, "news", "b1", "kept", "Kept one")
    F.judge(lens, "news", "b2", "declined", "Declined one")
    c = F.focus_counts(lens)
    assert c["saved"] == 1
    assert c["declined"] == 1
    assert "briefs" in c and "papers" in c


def test_questions_are_ideas_not_a_fourth_table(lens, db):
    """A question stays findable in idea search whatever happens to this surface."""
    with F.connect(db) as con:
        con.execute("INSERT INTO ideas VALUES (?,?,?,?,?,?)",
                    ("q1", "Does X cause Y?", "question", f"focus:{lens}",
                     F._now(), lens))
        con.execute("INSERT INTO ideas VALUES (?,?,?,?,?,?)",
                    ("i1", "Try Z", "focus", f"focus:{lens}", F._now(), lens))
    qs = F.focus_questions(lens)
    assert len(qs) == 1 and qs[0]["text"] == "Does X cause Y?"


# ── 5. the brief ─────────────────────────────────────────────────────────────

def test_a_brief_is_kept_not_recomputed(lens):
    F.save_brief(lens, "# First brief\n", 1, 2)
    F.save_brief(lens, "# Second brief\n", 3, 4)
    latest = F.latest_brief(lens)
    assert latest["body"] == "# Second brief\n"
    with F.connect(F.paths.db) as con:
        n = con.execute("SELECT COUNT(*) FROM focus_brief_log WHERE slug=?",
                        (lens,)).fetchone()[0]
    assert n == 2, "history must accumulate — a focus is built over weeks"


def test_the_brief_says_what_is_in_the_safe(lens, db):
    F.judge(lens, "news", "b1", "kept", "The one I kept")
    body = F.build_brief(lens)
    assert "In the safe" in body
    assert "The one I kept" in body


# ── 6. which knowledge layers a focus searches ───────────────────────────────
# Found on the researcher's real focus 2026-08-26: `layers = "all"` meant "a layer called
# all", matched nothing, and the surface reported 0 indexed documents while
# sitting on 27,428 chunks. Empty meaning "everything" and "all" meaning
# "nothing" is backwards, and the failure is silent — an over-restrictive filter
# and an empty library look identical from the outside.

@pytest.mark.parametrize("field", ["", "all", "ALL", " any ", "*", "everything",
                                   "all, any"])
def test_the_words_for_everything_mean_everything(lens, db, field):
    with F.connect(db) as con:
        con.execute("INSERT INTO knowledge_databases VALUES (1, 'ph-background')")
    r = F.layer_filter({"layers": field})
    assert r["slugs"] == [], f"{field!r} should not filter"
    assert r["all"] is True


def test_a_real_layer_still_filters(lens, db):
    with F.connect(db) as con:
        con.execute("INSERT INTO knowledge_databases VALUES (1, 'ph-background')")
        con.execute("INSERT INTO knowledge_databases VALUES (2, 'ntd')")
    r = F.layer_filter({"layers": "ntd"})
    assert r["slugs"] == ["ntd"] and r["unknown"] == []


def test_an_unknown_layer_is_reported_not_silently_applied(lens, db):
    with F.connect(db) as con:
        con.execute("INSERT INTO knowledge_databases VALUES (1, 'ph-background')")
    r = F.layer_filter({"layers": "ph-background, typo-here"})
    assert r["slugs"] == ["ph-background"]
    assert r["unknown"] == ["typo-here"], "a typo must be visible, not swallowed"


def test_all_layers_unknown_falls_back_to_everything(lens, db):
    """The important one: never return an empty corpus because of a typo."""
    with F.connect(db) as con:
        con.execute("INSERT INTO knowledge_databases VALUES (1, 'ph-background')")
    r = F.layer_filter({"layers": "nope, alsonope"})
    assert r["slugs"] == [], "must not filter down to nothing"
    assert r["all"] is True
    assert set(r["unknown"]) == {"nope", "alsonope"}


def test_focus_corpus_reports_unknown_layers(lens, db):
    with F.connect(db) as con:
        con.execute("UPDATE focus_areas SET layers = 'not-a-layer' WHERE slug = ?",
                    (lens,))
    assert F.focus_corpus(lens)["unknown_layers"] == ["not-a-layer"]


# ── 7. how a keyword matches ─────────────────────────────────────────────────
# Changed 2026-08-26 with the researcher's go-ahead, on measured evidence: 70 of 388 briefs
# on his AI-in-health lens (18%) matched only INSIDE longer words — 'ai' in
# "avait", 'gis' in "enregistre". A keyword now has to start at a word boundary.

def test_a_short_keyword_stops_matching_inside_words(lens):
    g = [["ai"], ["health"]]
    assert not F.matches_lens(g, "il avait dit que la health publique")
    assert F.matches_lens(g, "AI in health research")


def test_a_deliberate_stem_still_works(lens):
    """'epidemi' must catch epidemiology AND epidemic — the boundary is at the
    START only, so a keyword may still run into a longer word."""
    g = [["epidemi"]]
    assert F.matches_lens(g, "a paper on epidemiology")
    assert F.matches_lens(g, "the epidemic curve")
    assert not F.matches_lens(g, "a pandemic")


def test_a_hyphen_is_a_word_boundary(lens):
    assert F.matches_lens([["learning"]], "machine-learning methods")


def test_the_conjunction_still_holds_across_groups(lens):
    g = [["ai", "machine learning"], ["health", "clinical"]]
    assert F.matches_lens(g, "machine learning in clinical trials")
    assert not F.matches_lens(g, "machine learning in finance")
    assert not F.matches_lens(g, "clinical trials of a new drug")


def test_an_empty_lens_matches_nothing(lens):
    """A focus with no definition showing the whole library would look like a
    working surface and be pure noise."""
    assert not F.matches_lens([], "anything at all")


def test_confirm_only_removes_never_adds(lens):
    rows = [{"title": "AI in health"}, {"title": "il avait la health"},
            {"title": "clinical health and ai"}]
    kept = F.confirm([["ai"], ["health"]], rows, ["title"])
    assert len(kept) == 2
    assert all(r in rows for r in kept), "confirm must not invent rows"
