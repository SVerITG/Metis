"""Project categories as a thing you can own, not a SELECT DISTINCT.

Built 2026-09-03. Categories existed only as whatever strings sat in
`projects.category`, discovered by DISTINCT. That is enough to filter by and not
enough to own: you could not rename one, merge two, reorder them, or create an
empty one to move a project into — and a category that vanishes when its last
project leaves cannot be a place you put things.

The consequence was visible in the data: five of nine categories held exactly
ONE project and two projects held none, with no way to fix either from the page.
`/api/project/update` had accepted `category` all along; nothing exposed it.

The invariants these protect, each learned from getting it wrong first:

  1. An empty category must be creatable AND VISIBLE. The first version rendered
     only categories that held projects, so pressing "New category" appeared to
     do nothing and the feature was unreachable.
  2. A rename moves the projects too. Renaming the row alone would orphan them
     under a heading that no longer exists.
  3. Deleting a category never deletes a project — they become uncategorised.
  4. Uncategorised is NAMED and shown last. A bucket you cannot see is a bucket
     you never empty.
  5. A count reported by an endpoint has to be counted. `db_execute` returns
     None, so the first version reported `"moved": null`.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORK_PY = ROOT / "system" / "app-py" / "routers" / "work.py"
CARDS = ROOT / "system" / "app-py" / "templates" / "partials" / "work_projects.html"
APP_JS = ROOT / "system" / "app-py" / "static" / "app.js"
CSS = ROOT / "system" / "app-py" / "static" / "styles.css"


@pytest.fixture(scope="module")
def work_py() -> str:
    return WORK_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cards() -> str:
    return CARDS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


# ── 1. categories are a table, seeded from what already existed ──────────────

def test_categories_have_their_own_table(work_py):
    assert "CREATE TABLE IF NOT EXISTS project_categories" in work_py
    assert "display_order" in work_py, "no ordering column — reorder cannot persist"


def test_seeding_is_additive(work_py):
    """Adopting existing categories must never remove one the researcher created."""
    m = re.search(r"def _ensure_categories\(.*?\n(.*?)(?=\ndef )", work_py, re.S)
    assert m, "could not locate _ensure_categories"
    body = m.group(1)
    assert "INSERT OR IGNORE" in body, "seeding should not overwrite"
    assert "DELETE" not in body.upper(), (
        "seeding deletes something — it must only adopt, or a category the "
        "researcher created disappears on the next render"
    )


# ── 2. every operation exists, and keeps both halves in step ─────────────────

@pytest.mark.parametrize("route", [
    "/api/project-category/list",
    "/api/project-category/create",
    "/api/project-category/rename",
    "/api/project-category/merge",
    "/api/project-category/delete",
    "/api/project-category/reorder",
    "/api/project/{project_id}/move-category",
])
def test_route_exists(work_py, route):
    assert route in work_py, f"missing {route}"


def test_rename_moves_the_projects_too(work_py):
    m = re.search(r"async def project_category_rename\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
    assert m, "could not locate the rename handler"
    body = m.group(1)
    assert "UPDATE projects SET category=?" in body, (
        "a rename that does not move the projects orphans them under a heading "
        "that no longer exists"
    )
    assert "project_categories" in body, "the category row itself is not renamed"


def test_delete_frees_projects_rather_than_removing_them(work_py):
    m = re.search(r"async def project_category_delete\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
    assert m, "could not locate the delete handler"
    body = m.group(1)
    assert "UPDATE projects SET category=''" in body, (
        "deleting a category must uncategorise its projects, never delete them"
    )
    assert "DELETE FROM projects" not in body, "this must never delete a project"


def test_reported_counts_are_counted_not_assumed(work_py):
    """`db_execute` returns None, so assigning it to a count reported null."""
    assert "_count_in_category" in work_py, (
        "counts are being taken from db_execute's return value again, which is "
        "always None — the endpoint then reports \"moved\": null"
    )
    for handler in ("project_category_rename", "project_category_merge",
                    "project_category_delete"):
        m = re.search(rf"async def {handler}\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
        assert m, handler
        assert not re.search(r"=\s*db_execute\(", m.group(1)), (
            f"{handler} assigns db_execute's return value, which is None"
        )


def test_moving_a_project_can_invent_its_destination(work_py):
    """Re-filing and creating a home for something are one gesture in practice."""
    m = re.search(r"async def project_move_category\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
    assert m, "could not locate move-category"
    body = m.group(1)
    assert "INSERT OR IGNORE INTO project_categories" in body, (
        "an unknown target category is rejected rather than created, so typing a "
        "new name in the move dialog fails"
    )


# ── 3. the surface shows them, including the empty ones ──────────────────────

def test_cards_are_grouped_into_collapsible_sections(cards):
    assert "cat-sec" in cards and "<details" in cards, "sections are not collapsible"
    assert "cat-body" in cards
    assert 'class="grid grid-2 grid--top cat-body"' in cards, (
        "the cards were replaced rather than wrapped — the project card carries "
        "the next step, the task list and the launchers, which is most of why it "
        "exists"
    )


def test_an_empty_category_still_gets_a_heading(work_py, cards):
    """The bug that made 'New category' look like it did nothing."""
    # Assert the flag is CONSULTED, not merely present. The first version
    # checked `"show_empty" in work_py`, which stayed true when the usage was
    # removed and the assignment left behind — so the test passed while the
    # feature was broken. A presence check is not a behaviour check.
    assert re.search(r"if c in buckets or show_empty", work_py), (
        "the group list no longer consults show_empty, so empty categories are "
        "filtered out again — a newly created one is invisible and there is "
        "nowhere to move the first project to"
    )
    assert "Nothing filed here yet" in cards, "an empty section says nothing"


def test_empty_sections_are_hidden_under_a_filter(work_py):
    """Asked to see one category, you should not get the nine that do not match."""
    assert re.search(r'show_empty\s*=\s*f in \("", "active", "all"\)', work_py), (
        "empty sections are shown regardless of the filter"
    )


def test_uncategorised_is_named_and_last(work_py):
    assert 'UNCAT = "Uncategorised"' in work_py
    m = re.search(r"if UNCAT in buckets:\s*\n\s*ordered\.append\(UNCAT\)", work_py)
    assert m, "uncategorised is not forced to the end"


def test_three_activity_states_not_two(work_py):
    """"Active and not so active" needs a third state: four projects have never
    been opened, which is not the same as one that went quiet in June."""
    # Anchored on the next top-level def/decorator, NOT on a blank line: the
    # first version stopped at the blank line inside the docstring and then
    # asserted against three lines of prose.
    m = re.search(r"def _activity_band\(.*?\n(.*?)(?=\n@router\.|\ndef )", work_py, re.S)
    assert m, "could not locate _activity_band"
    body = m.group(1)
    for state in ("never", "hot", "cold"):
        assert f'"{state}"' in body, f"no {state!r} state"


def test_the_category_label_is_the_control_that_changes_it(cards):
    assert "projMoveCategory" in cards, "no way to move a project from its card"
    assert "tag--edit" in cards
    assert "tag--needs" in cards, (
        "an uncategorised project has no visible control — it needs one more "
        "than a filed project, not less"
    )


def test_section_tools_do_not_toggle_the_disclosure(cards):
    """A button inside a <summary> also activates the disclosure unless stopped."""
    for m in re.finditer(r'class="cat-tool"[^>]*onclick="([^"]*)"', cards):
        js = m.group(1)
        assert "preventDefault" in js and "stopPropagation" in js, (
            "a section tool will toggle the section as well as firing: "
            f"{js[:60]}"
        )


def test_collapse_state_is_remembered(app_js):
    """Reserved for the persistence hook, which lives in work.html."""
    work = (ROOT / "system" / "app-py" / "templates" / "work.html").read_text(encoding="utf-8")
    assert "metis.work.cats" in work, "collapse state is not persisted"
    assert "htmx:afterSwap" in work, (
        "state is applied once at load, but the projects zone is re-rendered by "
        "every filter, rename, merge and re-file — so it must be re-applied "
        "after a swap"
    )


def test_the_management_controls_are_wired(app_js):
    for fn in ("catCreate", "catManage", "catReorder", "projMoveCategory"):
        assert f"function {fn}" in app_js or f"async function {fn}" in app_js, f"no {fn}"
    assert "_catReload" in app_js, (
        "no reload after a category change — a rename changes headings and a "
        "merge removes a whole section, so the group has to be re-rendered"
    )
