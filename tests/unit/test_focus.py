"""Tests for focus areas.

Two properties carry this feature, and both are easy to break silently:

  1. **The lens is a conjunction.** OR within a keyword group, AND across groups.
     A flat list for "AI in health" returns "Can AI ever be conscious?" — real AI
     news, wrong surface. If this regresses the feed fills with noise and the
     surface stops being opened.

  2. **A focus owns nothing.** Archiving it must leave every note, idea, paper and
     brief exactly where it was. This is the answer to "what happens when I remove
     it", so it is asserted rather than trusted.

The shelf cap is tested too: it must REFUSE a fourth activation rather than
silently evicting something, because which focus loses its slot is a judgement
about attention.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"
if str(_MCP_SRC) not in sys.path:
    sys.path.insert(0, str(_MCP_SRC))

from metis_mcp.tools import focus as F  # noqa: E402

AI = ["artificial intelligence", "machine learning", "llm"]
HEALTH = ["health", "clinical", "epidemi"]
GROUPS = json.dumps([AI, HEALTH])


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """A database with the tables a focus reads, and content that discriminates."""
    p = tmp_path / "focus.sqlite"
    con = sqlite3.connect(str(p))
    con.execute("""CREATE TABLE news_briefs (brief_id TEXT PRIMARY KEY,
        brief_date TEXT, title TEXT, summary TEXT, source_url TEXT, domain TEXT,
        signal_strength TEXT, created_at TEXT)""")
    con.execute("""CREATE TABLE new_publications (id INTEGER PRIMARY KEY
        AUTOINCREMENT, title TEXT, journal TEXT, pub_date TEXT, pub_iso TEXT,
        doi TEXT, abstract TEXT, source_url TEXT, entry_kind TEXT,
        discovered_at TEXT, added_at TEXT, read_at TEXT)""")
    con.execute("""CREATE TABLE ideas (idea_id TEXT PRIMARY KEY, text TEXT,
        idea_type TEXT, tags TEXT, created_at TEXT, domain TEXT)""")
    con.execute("""CREATE TABLE personal_notes (note_id TEXT PRIMARY KEY,
        content TEXT, title TEXT, tags TEXT, created_at TEXT, updated_at TEXT)""")
    con.execute("CREATE TABLE knowledge_databases (id INTEGER PRIMARY KEY, slug TEXT, name TEXT)")
    con.execute("INSERT INTO knowledge_databases VALUES (1,'fixture','F')")
    con.execute("""CREATE TABLE pdf_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT,
        db_id INTEGER, source_file TEXT, domain TEXT, title TEXT,
        page_start INTEGER, page_end INTEGER, chunk_idx INTEGER,
        chunk_text TEXT, char_count INTEGER, created_at TEXT)""")

    news = [
        # ON subject — both axes present.
        ("n1", "2026-08-20", "AI model helps clinicians detect heart disease",
         "A machine learning tool used in a clinical setting."),
        # OFF subject — AI only. The case a flat keyword list gets wrong.
        ("n2", "2026-08-21", "Can AI ever be conscious?",
         "A philosophical argument about artificial intelligence."),
        # OFF subject — health only.
        ("n3", "2026-08-22", "New clinical guideline for hypertension",
         "An update to health policy with no computation involved."),
    ]
    for bid, d, t, s in news:
        con.execute("INSERT INTO news_briefs (brief_id, brief_date, title, summary, "
                    "created_at) VALUES (?,?,?,?,?)", (bid, d, t, s, d))
    con.execute("INSERT INTO new_publications (title, abstract, pub_date, pub_iso, "
                "discovered_at, entry_kind) VALUES (?,?,?,?,?,?)",
                ("Machine learning for clinical triage", "", "2026-08-01",
                 "2026-08-01", "2026-08-01", "article"))
    con.execute("INSERT INTO new_publications (title, abstract, pub_date, pub_iso, "
                "discovered_at, entry_kind) VALUES (?,?,?,?,?,?)",
                ("A large language model with an impossible date", "clinical",
                 "2030-01-01", "2030-01-01", "2026-02-02", "preprint"))
    con.commit()
    con.close()
    monkeypatch.setattr(F.paths, "db", p, raising=False)
    return p


def _make(title="AI in Health", groups=GROUPS, activate=False):
    return asyncio.run(F.create_focus_area(title=title, keyword_groups=groups,
                                           activate=activate))[0].text


# ── The lens is a conjunction ────────────────────────────────────────────────
def test_lens_requires_all_groups(db):
    _make()
    titles = [n["title"] for n in F.focus_news("ai-in-health")]
    assert any("heart disease" in t for t in titles)          # both axes
    assert not any("conscious" in t for t in titles)          # AI only
    assert not any("hypertension" in t for t in titles)       # health only


def test_a_flat_keyword_list_would_be_wrong(db):
    """Documents WHY groups exist: one group behaves like a flat list."""
    _make(title="Flat", groups=json.dumps([AI]))
    titles = [n["title"] for n in F.focus_news("flat")]
    assert any("conscious" in t for t in titles), \
        "a single group is a flat list and should pull in off-subject AI news"


def test_an_empty_lens_matches_nothing_not_everything(db):
    """A focus with no definition must not render the whole library as a feed."""
    frag, params = F.lens_sql([], "title")
    assert frag == "0" and params == []


# ── A focus owns nothing — the removal question ──────────────────────────────
def test_archiving_keeps_notes_and_ideas(db):
    _make(activate=True)
    con = sqlite3.connect(str(db))
    con.execute("INSERT INTO ideas (idea_id, text, idea_type, tags, created_at) "
                "VALUES ('i1','an idea','focus','focus:ai-in-health','2026-08-24')")
    con.execute("INSERT INTO personal_notes (note_id, content, title, tags, "
                "created_at, updated_at) VALUES ('n1','a note','T',"
                "'focus:ai-in-health','2026-08-24','2026-08-24')")
    con.commit()
    con.close()

    before = F.focus_thinking("ai-in-health")
    assert len(before["ideas"]) == 1 and len(before["notes"]) == 1

    asyncio.run(F.set_focus_state("ai-in-health", "archived"))

    con = sqlite3.connect(str(db))
    assert con.execute("SELECT COUNT(*) FROM ideas WHERE tags LIKE "
                       "'%focus:ai-in-health%'").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM personal_notes WHERE tags LIKE "
                       "'%focus:ai-in-health%'").fetchone()[0] == 1
    con.close()
    # And the focus itself is filed, not deleted.
    area = F.get_focus("ai-in-health")
    assert area["state"] == "archived" and area["archived_at"]


def test_archiving_keeps_the_feed_readable(db):
    """The lens still resolves after archiving — the page stays openable."""
    _make(activate=True)
    asyncio.run(F.set_focus_state("ai-in-health", "archived"))
    assert F.focus_news("ai-in-health"), "an archived focus must still read"


# ── The shelf ────────────────────────────────────────────────────────────────
def test_activation_assigns_a_slot(db):
    _make(activate=True)
    assert F.get_focus("ai-in-health")["shelf_slot"] == 1


def test_shelf_is_capped_and_refuses_rather_than_evicting(db):
    for i in range(F.MAX_SHELF):
        _make(title=f"Area {i}", activate=True)
    _make(title="Fourth")
    msg = asyncio.run(F.set_focus_state("fourth", "active"))[0].text
    assert "shelf is full" in msg.lower()
    assert F.get_focus("fourth")["state"] != "active"
    # Nothing was evicted to make room.
    assert len(F.list_focus("active")) == F.MAX_SHELF


def test_following_frees_the_slot(db):
    _make(activate=True)
    asyncio.run(F.set_focus_state("ai-in-health", "following"))
    a = F.get_focus("ai-in-health")
    assert a["state"] == "following" and a["shelf_slot"] is None
    assert F.list_focus("active") == []


def test_only_active_areas_reach_the_navbar(db):
    _make(title="On shelf", activate=True)
    _make(title="Just following")
    assert [a["title"] for a in F.list_focus("active")] == ["On shelf"]


# ── Reading order: an impossible date must not lead the list ────────────────
def test_future_dated_item_does_not_top_the_reading_list(db):
    """The corpus really does hold papers stamped 2027 and 2030."""
    _make()
    rows = F.focus_reading("ai-in-health")
    assert rows, "the fixture has two matching publications"
    assert "impossible date" not in rows[0]["title"], \
        "a 2030-stamped paper must not sit permanently at the top of a feed"


# ── Slug handling ───────────────────────────────────────────────────────────
def test_slugify_is_stable_and_url_safe():
    assert F.slugify("AI in Health & Epidemiology") == "ai-in-health-epidemiology"
    assert F.slugify("  Multiple   spaces  ") == "multiple-spaces"


def test_duplicate_titles_are_refused(db):
    _make()
    assert "already exists" in _make()


def test_bad_keyword_groups_are_rejected_with_an_explanation(db):
    msg = asyncio.run(F.create_focus_area(
        title="Bad", keyword_groups='["not","a","list","of","lists"]'))[0].text
    assert "list of lists" in msg
    assert F.get_focus("bad") is None
