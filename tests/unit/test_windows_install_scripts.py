"""
The Windows installer, checked from any computer.

None of these defects can be seen on Linux, and the development machine could not
run Windows programs when they were found — so each became a rule here instead:

  * install.ps1 used PowerShell 7 syntax (`?.`) and powershell.exe is 5.1: the
    whole script failed to parse, and nothing in it ran.
  * Windows PowerShell 5.1 reads a script without a byte-order mark in the ANSI
    code page. The last byte of an em dash is then a curly closing quote, which
    ends the string it sits in. Every .ps1 with a non-ASCII character had this.
  * The installer wrote claude_desktop_config.json and ~/.claude/CLAUDE.md whole,
    deleting a colleague's other connectors and their own Claude instructions.
  * The setup program referenced files it never shipped, and pointed install
    steps at the retired database location system\\app\\data.

The full 5.1 compatibility analysis (PSScriptAnalyzer) needs PowerShell; this
is the part that runs everywhere, in the normal suite.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WIN = ROOT / "system" / "install" / "windows"
INSTALL_PS1 = WIN / "install.ps1"
ISS = ROOT / "system" / "install" / "installer" / "metis-setup.iss"


def _tracked(pattern: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files", pattern], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [ROOT / p for p in out]


PS1 = _tracked("*.ps1")


def test_there_are_scripts_to_check():
    # A rule over an empty list passes for the wrong reason.
    assert len(PS1) >= 5, f"only {len(PS1)} .ps1 files found — is git available?"


@pytest.mark.parametrize("path", PS1, ids=lambda p: p.name)
def test_non_ascii_powershell_has_a_bom(path):
    data = path.read_bytes()
    if any(b > 127 for b in data):
        assert data.startswith(b"\xef\xbb\xbf"), (
            f"{path.name} has non-ASCII characters but no UTF-8 byte-order mark: "
            "Windows PowerShell 5.1 will misread it, and an em dash can end a string")


# Operators that exist only in PowerShell 7: ?. ?[ ?? ??= and the ternary.
PS7_ONLY = re.compile(r"(\$\{?\w+\}?|\))\?\.|\?\?=?|\)\s*\?\s*\S+\s*:\s")


@pytest.mark.parametrize("path", PS1, ids=lambda p: p.name)
def test_no_powershell_7_only_operators(path):
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        code = line.split("#", 1)[0]
        code = re.sub(r"'[^']*'|\"[^\"]*\"", "''", code)  # ignore string contents
        assert not PS7_ONLY.search(code), (
            f"{path.name}:{n} uses PowerShell 7 syntax; powershell.exe is 5.1:\n  {line.strip()}")


def test_install_ps1_merges_claude_desktop_settings():
    src = INSTALL_PS1.read_text(encoding="utf-8-sig")
    assert "register_desktop.py" in src, "Claude Desktop must be registered by merging"
    assert not re.search(r"(Set-Content|Out-File|WriteAllText)[^\n]*claude_desktop_config", src), (
        "install.ps1 writes claude_desktop_config.json directly — that deletes the "
        "person's other connectors")


def test_install_ps1_keeps_the_persons_own_claude_md():
    src = INSTALL_PS1.read_text(encoding="utf-8-sig")
    assert "<!-- metis:start" in src and "<!-- metis:end -->" in src, (
        "CLAUDE.md must be changed only inside a marked Metis section")


def test_install_ps1_never_prompts_when_run_by_setup():
    src = INSTALL_PS1.read_text(encoding="utf-8-sig")
    for n, line in enumerate(src.splitlines(), 1):
        if "Read-Host" in line and "function Write-Fail" not in line:
            # Every prompt must sit behind $interactive, which -FromInstaller clears.
            window = "\n".join(src.splitlines()[max(0, n - 12):n])
            assert "$interactive" in window, (
                f"install.ps1:{n} prompts without checking $interactive — setup waits "
                "on it and hangs")


def test_setup_program_ships_every_file_it_names():
    text = ISS.read_text(encoding="utf-8-sig")
    base = ISS.parent
    missing = []
    for src, flags in re.findall(r'^Source:\s*"([^"]+)"([^\n]*)', text, re.M):
        if "skipifsourcedoesntexist" in flags or "*" in src:
            continue
        path = (base / src.replace("{#RepoRoot}", "../../..").replace("\\", "/")).resolve()
        if not path.exists():
            missing.append(src)
    assert not missing, "metis-setup.iss names files that do not exist:\n  " + "\n  ".join(missing)


def test_setup_program_ships_what_install_ps1_needs():
    text = ISS.read_text(encoding="utf-8-sig")
    for needed in ("requirements.txt", "schema.sql", "init_db.py", "register_desktop.py"):
        assert needed in text, f"install.ps1 needs {needed}, and setup does not ship it"


def test_no_install_step_targets_the_retired_database():
    for path in (ISS, INSTALL_PS1):
        text = path.read_text(encoding="utf-8-sig")
        assert not re.search(r"system[\\/]+app[\\/]+data[\\/]+metis\.sqlite", text), (
            f"{path.name} points at system\\app\\data\\metis.sqlite, retired in June; "
            "nothing reads a database there")


def test_batch_files_get_windows_line_endings():
    attrs = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for ext in ("bat", "ps1", "vbs"):
        assert re.search(rf"^\*\.{ext}\s+text\s+eol=crlf", attrs, re.M), (
            f"*.{ext} must be checked out with CRLF — cmd.exe misreads labels otherwise")
