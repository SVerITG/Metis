"""What the Today boards may CONTAIN, and the seen state that lets you clear them.

Written 2026-09-02 after an inspection found the Events board was 81% cardiology
news — 17 of 21 live rows were MedicalXpress articles about studies presented at
congresses, because the classifier matched the phrase "annual meeting". Outbreaks
was 41 of 47 rows straight from one press feed.

A curation decision had been recorded months earlier: these boards have no RSS
source and are filled by hand. It regressed anyway, and **nothing noticed for
months, because every existing test checked that the boards RENDERED, and none
checked what was in them.** A test that only asserts a panel returns HTML cannot
tell a congress from a cardiology headline.

So these tests assert content and behaviour rather than shape:

  1. The news scan cannot route anything to Events or Funding.
  2. A board refresh clears every auto-added row, not a named subset — the bug
     that let scanner rows accumulate permanently while refreshes removed the
     curated ones.
  3. The date a board collects is stored where the row can render it.
  4. "Seen" and "dismissed" are different columns, and the highlight tracks the
     first, not the clock.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "app-py"))

SCAN = ROOT / "system" / "mcp-server" / "src" / "metis_mcp" / "tools" / "content_scan.py"
TODAY = ROOT / "system" / "app-py" / "routers" / "today.py"
BOX = ROOT / "system" / "app-py" / "templates" / "partials" / "today_board_box.html"
SCHEMA = ROOT / "system" / "installer" / "schema.sql"


@pytest.fixture(scope="module")
def scan_src() -> str:
    assert SCAN.is_file(), f"missing {SCAN}"
    return SCAN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def today_src() -> str:
    return TODAY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def box_src() -> str:
    return BOX.read_text(encoding="utf-8")


# ── 1. the news scan may not fill Events or Funding ──────────────────────────

def test_scan_routes_to_no_board_at_all(scan_src):
    """_maybe_add_to_board must not assign ANY board.

    Events and Funding went first (the phrase "annual meeting" matched every
    study reported from a congress). Outbreaks followed on 2026-09-02: source
    gating looked more careful than keyword gating and was not, because half its
    sources no longer exist, so in practice it resolved to one regional press
    feed and mirrored the lot — 41 of 47 rows, including a cancer services
    blueprint. All three boards are a SELECTION, which is what WHO's Disease
    Outbreak News is and what a feed can never be.

    Asserted on the function body rather than the source sets, because those are
    deliberately KEPT (renamed `_RETIRED_*`) as a record of what was tried.
    """
    m = re.search(r"def _maybe_add_to_board\(.*?\n(.*?)(?=\n@app\.tool|\ndef )",
                  scan_src, re.S)
    assert m, "could not locate _maybe_add_to_board"
    body = m.group(1)
    for forbidden in ('board = "events"', "board = 'events'",
                      'board = "funding"', "board = 'funding'",
                      'board = "outbreaks"', "board = 'outbreaks'"):
        assert forbidden not in body, (
            f"the news scan assigns {forbidden!r} again. All three boards are "
            "curated; a feed mirrors a publisher, which is how Events became 81% "
            "cardiology news and Outbreaks 87% one press feed."
        )
    assert "INSERT INTO today_board_items" not in body, (
        "the scan writes to a board again"
    )


def test_retired_keyword_lists_are_not_consulted(scan_src):
    """The retired lists are a record, not live logic."""
    assert "_RETIRED_EVENT_KEYWORDS" in scan_src, (
        "the retired list was deleted — keep it, it documents an approach that "
        "failed three times so nobody re-derives it"
    )
    # A negative lookbehind, not a strip-then-substring check: `_OUTBREAK_SOURCES`
    # is a SUBSTRING of `_RETIRED_OUTBREAK_SOURCES`, so the naive version failed
    # on the very comment that documents the retirement.
    for name in ("_EVENT_KEYWORDS", "_FUNDING_KEYWORDS", "_OUTBREAK_SOURCES"):
        assert not re.search(rf"(?<!_RETIRED){name}", scan_src), (
            f"a live {name} gate came back"
        )


# ── 2. a refresh must clear what it claims to ────────────────────────────────

def test_board_refresh_clears_every_auto_added_row(scan_src):
    """The delete must key off auto_added, not a named source list.

    With `source IN ('web-search','claude')` a refresh removed the rows Claude had
    just curated and left the scanner's behind, so the noise ratio got worse every
    time the button was pressed. auto_added=0 marks exactly the human-owned rows.
    """
    assert re.search(r"DELETE FROM today_board_items WHERE board=\? AND auto_added=1",
                     scan_src), "board refresh no longer clears all auto-added rows"
    assert "source IN ('web-search','claude')" not in scan_src, (
        "the named-source delete is back — it leaves scanner rows in place forever"
    )


def test_manual_adds_are_marked_human_owned(today_src):
    """A refresh must not be able to take away something typed by hand."""
    assert re.search(r"'manual', 0,", today_src), (
        "the manual add form no longer writes auto_added=0, so a board refresh "
        "would delete hand-typed rows"
    )


# ── 3. the date is stored where it can be rendered ───────────────────────────

def test_collected_date_goes_to_start_date(scan_src):
    """update_today_board must write start_date, not append to description."""
    assert "start_date, source, auto_added" in scan_src, (
        "update_today_board no longer inserts start_date"
    )
    assert 'desc = (desc + f" · {date}")' not in scan_src, (
        "the date is being folded into `description` again — a field the board "
        "row does not render, so every date collected is discarded on the way "
        "to the screen"
    )


def test_board_row_renders_the_event_date(box_src):
    """The row must print the date, or storing it changes nothing."""
    assert "item._when" in box_src, "the board row no longer renders the event date"
    assert "board-item-date" in box_src


def test_board_context_prefers_start_date_over_created_at(today_src):
    assert re.search(r'_when.*start_date', today_src), (
        "_when must come from start_date — showing the scrape date on a deadline "
        "board reads as the deadline"
    )


# ── 4. seen is a state; dismissed is a decision ──────────────────────────────

def test_seen_at_is_declared_in_the_schema(today_src):
    """New columns go in schema.sql AND in the idempotent ensure path."""
    assert "seen_at" in SCHEMA.read_text(encoding="utf-8"), (
        "seen_at missing from schema.sql — a column added only by migration is "
        "absent on a fresh install, which is the two-computer failure class"
    )
    assert "ADD COLUMN seen_at" in today_src, (
        "no migration for databases created before seen_at"
    )


def test_seen_and_dismiss_are_separate_routes(today_src):
    """Acknowledging must not require deleting."""
    assert "/item/{item_id}/seen" in today_src, "no per-item seen route"
    assert "/seen-all" in today_src, (
        "no panel-level mark-all-seen — the news rail has had one for weeks and "
        "clearing a board otherwise costs one confirm dialog per row"
    )


def test_seen_toggle_does_not_dismiss(today_src):
    """The seen route must never touch `dismissed`."""
    m = re.search(r"async def board_seen_item\(.*?\n(.*?)(?=\n@router\.)", today_src, re.S)
    assert m, "could not locate board_seen_item"
    assert "dismissed=1" not in m.group(1), (
        "marking something seen must not delete it"
    )


def test_mark_all_seen_only_touches_live_unseen_rows(today_src):
    m = re.search(r"async def board_seen_all\(.*?\n(.*?)(?=\n@router\.)", today_src, re.S)
    assert m, "could not locate board_seen_all"
    body = m.group(1)
    assert "dismissed=0" in body, "mark-all-seen would resurrect dismissed rows"
    assert "COALESCE(seen_at,'') = ''" in body, (
        "mark-all-seen overwrites existing timestamps, so 'seen on' stops meaning "
        "when it was first acknowledged"
    )


def test_highlight_tracks_attention_not_the_clock(today_src):
    """The band must be gated on _unseen, not left on the age band alone.

    This is the finding that started the whole pass: `_fresh` came from
    created_at, so the tint cleared after seven days whether the row had been
    read or not — and since the default view is the five newest rows, all five
    were always tinted. A mark on 100% of rows carries no information.
    """
    assert '_unseen' in today_src, "no unseen flag on board items"
    assert re.search(r'if not it\["_unseen"\]:\s*\n\s*it\["_fresh"\] = ""', today_src), (
        "a seen item can still carry the new-item band"
    )


def test_row_offers_seen_before_ignore(box_src):
    """The state slot is the seen control; ignore stays available but is not first.

    `board-dismiss` became `board-act--ignore` on 2026-09-05, when the row was
    compressed to one line and the actions were split into three named verbs.
    The invariant is unchanged and is the reason this test exists: the control
    that removes something must not be the first one a reader reaches.
    """
    assert "board-seen" in box_src, "no seen control in the board row"
    assert "board-act--ignore" in box_src, "no ignore control in the board row"
    assert box_src.index("board-seen") < box_src.index("board-act--ignore"), (
        "ignore appears before the seen control — the destructive action should "
        "not be the first thing reachable"
    )


def test_row_carries_three_named_verbs(box_src):
    """Follow, pin and ignore are separate controls, not one star doing three jobs.

    Pin is POSITION and follow is CONTENT: pinning holds a row at the top in an
    order you chose, following asks the news stream for its newest report. They
    were the same `starred` column, so you could not keep a congress date in
    view without also asking for a lookup that will never match it.
    """
    for verb in ("board-act--follow", "board-act--pin", "board-act--ignore"):
        assert verb in box_src, f"the board row has no {verb} control"
    assert "/pin" in box_src and "/star" in box_src, (
        "pin and follow must post to different endpoints, or they are still one verb"
    )


def test_header_counts_unseen(box_src):
    assert "n_unseen" in box_src, (
        "the board header shows only a total, which is the same number every "
        "morning and so answers a question nobody is asking"
    )


# ── 5. the Outbreaks board is a selection, not a mirror ──────────────────────

def test_outbreaks_refresh_points_at_who_don(box_src):
    """The researcher asked for "the main outbreaks in the world", naming WHO's
    Disease Outbreak News as the model. WHO retired the DON RSS feed, so the
    board cannot subscribe to it — the refresh prompt names the page instead."""
    assert "disease-outbreak-news" in box_src, (
        "the Outbreaks refresh no longer points at WHO DON, so a refresh has "
        "nothing telling it to select rather than mirror"
    )
    assert "start_date" in box_src, (
        "the refresh must ask for a date, or the board goes back to showing when "
        "a row was scraped"
    )
