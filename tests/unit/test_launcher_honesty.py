"""A launcher must reflect a capability, not assert one.

Written 2026-09-03 after the researcher asked "all the launchers of the
workbench fail?" — and they did, two independent ways.

**The row advertised what it could not do.** `launchers` was unset on 17 of 18
projects, so every card fell through to a list that offered Claude Code, Chat
and Cowork *regardless of whether the project had a folder* — while 7 of 16
active projects had none. Claude Code writes a CLAUDE.md into that folder and
opens a terminal in it, so with no folder there is nothing for it to do. The
button was a promise the card could not keep.

**And there was no way to fix it.** `external_path` was never in the editable
fields whitelist, so a folder could only be set at the moment a project was
created. Every project made without one stayed that way, permanently, with no
control anywhere on the page. That is *why* seven projects had no folder.

**Separately, the environment was down.** WSL registers a handler for Windows
binaries under binfmt_misc; when that registration is missing every `.exe`
fails at exec time, and the page surfaced the kernel's own words —
`[Errno 8] Exec format error` — which names a condition the reader cannot act
on. It has a one-line fix and it is nobody's mistake, so it is worth a sentence.

These tests assert the three properties that follow, plus the structural one
that caught a real dead button: a target the card can render must exist on the
server. `github` was offerable from the day the template was written and never
implemented — it fell through to "Unknown target".
"""
import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "system" / "app-py"
WORK_PY = APP / "routers" / "work.py"
CARDS = APP / "templates" / "partials" / "work_projects.html"
APP_JS = APP / "static" / "app.js"


@pytest.fixture(scope="module")
def work_py() -> str:
    return WORK_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cards() -> str:
    return CARDS.read_text(encoding="utf-8")


def _code_only(src: str, comment: str = "#") -> str:
    """Strip comments so a check cannot match the prose explaining the bug.

    Third time this has been needed: a test forbidding `pane.style.display`
    matched the comment quoting it, and the persona linter matched its own
    documentation. A check that a string is absent must read the code.
    """
    pat = r"#.*$" if comment == "#" else r"//.*$"
    return "\n".join(re.sub(pat, "", ln) for ln in src.split("\n"))


def _launch_branch_targets(src: str) -> set[str]:
    """Every `target` value the launch endpoint actually handles."""
    m = re.search(r"async def project_launch\(.*?\n(.*?)(?=\n@router\.)", src, re.S)
    assert m, "could not locate project_launch"
    body = m.group(1)
    found = set()
    for mm in re.finditer(r'target\s*(?:==|in)\s*(\(?[^\n:]+)', body):
        found |= set(re.findall(r'"([a-z_]+)"', mm.group(1)))
    return found


def _template_offerable(cards_src: str) -> set[str]:
    """Every target key the card template can render a button for."""
    m = re.search(r"\{%\s*set\s+_all\s*=\s*\[(.*?)\]\s*%\}", cards_src, re.S)
    assert m, "could not find the template's launcher table"
    return set(re.findall(r"\(\s*'([a-z_]+)'", m.group(1)))


# ── 1. the structural one: a button the server cannot answer ─────────────────

def test_every_offerable_target_has_a_handler(work_py, cards):
    """`github` was renderable and unimplemented — it hit "Unknown target"."""
    offerable = _template_offerable(cards)
    handled = _launch_branch_targets(work_py)
    missing = sorted(offerable - handled - {"claude_desktop"})
    assert not missing, (
        "the card can render buttons the launch endpoint does not handle, so "
        f"pressing one returns 'Unknown target': {missing}"
    )


def test_every_offerable_target_declares_what_it_needs(work_py, cards):
    """A target with no declared requirements is offered unconditionally."""
    offerable = _template_offerable(cards)
    m = re.search(r"_LAUNCH_NEEDS[^=]*=\s*\{(.*?)\n\}", work_py, re.S)
    assert m, "the requirements table is gone"
    declared = set(re.findall(r'"([a-z_]+)"\s*:', m.group(1)))
    missing = sorted(offerable - declared)
    assert not missing, (
        "these targets are renderable but declare no requirements, so nothing "
        f"stops them being offered where they cannot work: {missing}"
    )


# ── 2. offer only what can run ───────────────────────────────────────────────

def test_a_folderless_project_is_not_offered_a_folder_opener(work_py):
    """The specific false promise: Claude Code with no folder to open."""
    m = re.search(r"_LAUNCH_NEEDS[^=]*=\s*\{(.*?)\n\}", work_py, re.S)
    table = m.group(1)
    for target in ("claude_code", "rstudio", "vscode", "explorer"):
        row = re.search(rf'"{target}"\s*:\s*\(([^)]*)\)', table)
        assert row, f"{target} has no requirements row"
        assert '"path"' in row.group(1), (
            f"{target} opens a folder but no longer requires one — it will be "
            "offered on projects that have none, which is what the researcher "
            "was seeing"
        )


def test_targets_that_need_no_folder_still_work_without_one(work_py):
    """Over-correcting is its own defect: Chat and Cowork use no folder.

    The first version of the launch endpoint rejected EVERY target whenever the
    folder was missing, which would have removed two buttons that work fine.
    """
    m = re.search(r"_LAUNCH_NEEDS[^=]*=\s*\{(.*?)\n\}", work_py, re.S)
    table = m.group(1)
    for target in ("claude_chat", "claude_cowork"):
        row = re.search(rf'"{target}"\s*:\s*\(([^)]*)\)', table)
        assert row, f"{target} missing from the table"
        assert '"path"' not in row.group(1), (
            f"{target} now demands a folder it never uses, so it disappears "
            "from every project without one for no reason"
        )


def test_the_explicit_list_is_filtered_too(work_py):
    """A saved preference is not a claim about the present.

    A launcher list stored when a folder existed must stop advertising the
    folder once it is gone.
    """
    m = re.search(r"def _parse_launchers\(.*?\n(.*?)(?=\ndef _capable_only)", work_py, re.S)
    assert m, "could not locate _parse_launchers"
    body = _code_only(m.group(1))
    assert "_capable_only(p, json.loads(raw))" in body, (
        "the stored launcher list is returned unfiltered, so a project can "
        "still offer a launcher it cannot run"
    )


# ── 3. the environment check, stated once and in words ──────────────────────

def test_interop_is_checked_before_anything_is_executed(work_py):
    m = re.search(r"async def project_launch\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
    body = m.group(1)
    check = body.find("_interop_state()")
    first_run = body.find("_run_windows_cmd(")
    assert check != -1, "the launch endpoint no longer checks interop at all"
    assert first_run != -1, "no launcher runs a Windows command any more?"
    assert check < first_run, (
        "interop is checked after the first attempt to run a Windows command, "
        "so the raw exec error reaches the reader first"
    )


def test_the_raw_exec_errno_is_never_what_the_reader_sees(work_py):
    """`[Errno 8] Exec format error` names a kernel condition, not an action."""
    m = re.search(r"async def project_launch\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
    body = _code_only(m.group(1))
    assert "errno == 8" in body, (
        "ENOEXEC is no longer translated; if interop drops between the check "
        "and the attempt, the kernel's wording reaches the page again"
    )
    assert not re.search(r'"Launch failed: \{e\}"', body), (
        "the endpoint is back to pasting the exception into the response"
    )


def test_the_notice_is_rendered_once_for_the_page(cards):
    assert "launch-down" in cards, "no interop notice on the project list"
    assert cards.count("{% if not interop_ok %}") == 1, (
        "the interop notice is conditional in more than one place — it is one "
        "fact about the machine, not a per-card property"
    )


# ── 4. the control that did not exist ───────────────────────────────────────

def test_a_project_folder_can_be_set_from_the_page(work_py, cards):
    """The root cause: `external_path` was only ever settable at creation."""
    assert "/api/project/{project_id}/set-path" in work_py, "no way to set a folder"
    assert "projSetPath" in cards, (
        "the card has no control to point a project at its folder, so a project "
        "created without one can never get one"
    )
    assert "Where does this live?" in cards


def test_setting_a_folder_is_validated_because_launching_writes_into_it(work_py):
    """Claude Code writes a CLAUDE.md there — an unchecked path is a stray write."""
    m = re.search(r"async def project_set_path\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
    assert m, "could not locate project_set_path"
    body = m.group(1)
    assert "os.path.isabs" in body, "a relative path is accepted"
    assert "os.path.exists" in body, "a path that does not exist is accepted"
    assert "os.path.isdir" in body, (
        "a FILE is accepted as a project folder, and launching would then try "
        "to write a file inside a file"
    )


def test_clearing_a_folder_stays_possible(work_py):
    """Blank is a real answer — "this project has no folder" — not an error."""
    m = re.search(r"async def project_set_path\(.*?\n(.*?)(?=\n@router\.)", work_py, re.S)
    body = m.group(1)
    assert "cleared" in body, (
        "a blank path is now rejected, so there is no way to say a project has "
        "no folder once one has been set"
    )


def test_the_windows_form_of_a_path_is_accepted(work_py):
    """Copying a folder address in Explorer gives `C:\\...`, often quoted.

    Asking someone to hand-translate that into /mnt/c is asking them to get it
    wrong.
    """
    m = re.search(r"def _windows_to_wsl\(.*?\n(.*?)(?=\n@router\.|\ndef )", work_py, re.S)
    assert m, "no Windows-path converter"
    body = m.group(1)
    assert "/mnt/" in body, "the converter no longer produces a WSL path"
    assert 'strip(\'"\')' in body or 'strip(\'\\\'\')' in body or "strip('\"')" in body, (
        "quotes are not stripped — Explorer's 'Copy as path' wraps the path in "
        "double quotes, so the pasted value would never resolve"
    )


def test_the_module_still_imports(work_py):
    """A docstring containing `C:\\Users` is a unicode escape, not a path.

    `\\U` begins an 8-digit escape, so a normal docstring holding a Windows
    path is a SyntaxError. It has to be a raw string. This bit once already,
    in the redactor.
    """
    ast.parse(work_py)
    m = re.search(r"def _windows_to_wsl\(path: str\) -> str:\n(\s*)(r?)\"\"\"", work_py)
    assert m, "could not read the converter's docstring"
    if "\\U" in work_py[m.end():m.end() + 200]:
        assert m.group(2) == "r", "docstring holds a Windows path but is not raw"
