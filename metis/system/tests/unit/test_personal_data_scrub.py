"""
unit/test_personal_data_scrub.py — Personal data scrub audit for public release.

This test takes the perspective of someone who has just cloned the base Metis
repo from GitHub and is trying to find out anything about its original author —
who they are, what they research, which articles they write, which projects they
work on, what institution they are at.

The test scans every tracked file in the repo (as it would appear on GitHub)
and fails if any personal data pattern is found. It is intended to run against
the `base-release` branch before pushing to `origin`.

Patterns mirror the release-coordinator personal data scanner — keep in sync.

Run:
    pytest metis/system/tests/unit/test_personal_data_scrub.py -v
    pytest metis/system/tests/unit/test_personal_data_scrub.py -v --tb=short
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Personal data patterns
# ---------------------------------------------------------------------------

@dataclass
class Pattern:
    name: str
    regex: re.Pattern
    description: str


# Build pattern list (mirrors release-coordinator/skill.md § Personal data scanner)
_PATTERNS: list[Pattern] = [
    # Names
    Pattern("first_name",       re.compile(r"\bStan\b", re.IGNORECASE),
            "First name (Stan)"),
    Pattern("family_name",      re.compile(r"Verschaeve", re.IGNORECASE),
            "Family name"),
    Pattern("username",         re.compile(r"sverschaeve", re.IGNORECASE),
            "Username (sverschaeve)"),
    Pattern("initials",         re.compile(r"S\.V\."),
            "Initials S.V."),
    Pattern("partial_name",     re.compile(r"Stan V\b"),
            "Partial name (Stan V)"),
    # Email
    Pattern("email_domain",     re.compile(r"@itg\.be"),
            "Institutional email domain @itg.be"),
    Pattern("email_prefix",     re.compile(r"sverschaeve@"),
            "Email prefix sverschaeve@"),
    # Institution
    Pattern("institute_full",   re.compile(r"Institute of Tropical Medicine"),
            "Full institution name"),
    Pattern("institute_abbrev", re.compile(r"\bITG\b"),
            "Institution abbreviation ITG (standalone)"),
    # Local paths
    Pattern("wsl_path",         re.compile(r"/mnt/c/Users/sverschaeve"),
            "WSL personal path"),
    Pattern("win_path_bs",      re.compile(r"C:\\\\Users\\\\sverschaeve"),
            "Windows backslash path"),
    Pattern("win_path_fs",      re.compile(r"C:/Users/sverschaeve"),
            "Windows forward-slash path"),
    Pattern("onedrive_folder",  re.compile(r"OneDrive\s*-\s*ITG"),
            "OneDrive personal folder"),
    # API keys
    Pattern("api_key_prefix",   re.compile(r"sk-ant-[a-zA-Z0-9]"),
            "Anthropic API key prefix"),
    Pattern("api_key_assign",   re.compile(r"ANTHROPIC_API_KEY\s*=\s*sk-"),
            "Hardcoded API key assignment"),
    # Personal data references
    Pattern("sqlite_personal",  re.compile(r"metis\.sqlite.*sverschaeve|sverschaeve.*metis\.sqlite"),
            "Personal SQLite path"),
]

# Allowed exceptions — these patterns are explicitly permitted and must NOT fail the test
_ALLOWED_PATTERNS = {
    "SVerITG",      # public GitHub username
    "sverschaeve@itg.be",  # email only in .env.example placeholder — filtered by file type
}

# File extensions to skip (binary / generated / not human-readable)
_SKIP_EXTENSIONS = {
    ".exe", ".dll", ".so", ".pyc", ".pyo", ".pyd", ".png", ".jpg", ".jpeg",
    ".gif", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".pdf",
    ".sqlite", ".db", ".zip", ".tar", ".gz", ".bz2", ".7z",
}

# Files/directories that are explicitly excluded from the public release
# (gitignored or private by design — scanning them is not meaningful here)
_SKIP_PATHS_CONTAINING = [
    "release-coordinator",   # private agent — gitignored
    ".env",                  # gitignored secrets file
    "/.venv/",               # virtual environments
    "/node_modules/",
    "__pycache__",
    ".git/",
    "/tests/",               # test files contain the patterns as strings — not personal data
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_tracked_files(repo_root: Path) -> list[Path]:
    """Return list of files tracked by git (as they would appear on GitHub)."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    files = []
    for line in result.stdout.splitlines():
        p = repo_root / line.strip()
        if p.is_file():
            files.append(p)
    return files


def should_skip_file(path: Path) -> bool:
    path_str = path.as_posix()
    if path.suffix.lower() in _SKIP_EXTENSIONS:
        return True
    for fragment in _SKIP_PATHS_CONTAINING:
        if fragment in path_str:
            return True
    return False


_PLACEHOLDER_SUFFIXES_RE = re.compile(r"\.\.\.|your-key|your_key|<your|example|placeholder", re.IGNORECASE)


def is_allowlisted(line: str, match: re.Match) -> bool:
    """Return True if the matched content is explicitly permitted."""
    matched_text = match.group(0)
    surrounding = line[max(0, match.start() - 10): match.end() + 50]

    # SVerITG (public GitHub username) is always OK
    if "SVerITG" in surrounding and "sverschaeve" not in surrounding.lower():
        return True

    # API key pattern — allow if it's clearly a placeholder (followed by ... or description words)
    if matched_text.startswith("sk-ant-") or "ANTHROPIC_API_KEY" in surrounding:
        rest = line[match.end():]
        if _PLACEHOLDER_SUFFIXES_RE.search(rest[:30]) or "..." in rest[:10]:
            return True

    # anonymization.py lists ITG as a known institution abbreviation in a regex — code context
    if "anonymization" in str(match.re.pattern) or (
        matched_text == "ITG" and "MSF" in line and "WHO" in line
    ):
        return True

    return False


@dataclass
class Finding:
    file: Path
    line_no: int
    pattern_name: str
    line_content: str
    match_text: str


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings

    for line_no, line in enumerate(text.splitlines(), start=1):
        for pat in _PATTERNS:
            m = pat.regex.search(line)
            if m and not is_allowlisted(line, m):
                findings.append(Finding(
                    file=path,
                    line_no=line_no,
                    pattern_name=pat.name,
                    line_content=line.strip()[:120],
                    match_text=m.group(0),
                ))
    return findings


# ---------------------------------------------------------------------------
# The scrub test
# ---------------------------------------------------------------------------

def test_no_personal_data_in_tracked_files(repo_root: Path):
    """
    Impersonate an external researcher who just cloned the repo.
    Scan every tracked file for personal data. Fail with a full report if any
    personal information is found.

    This is a pre-release gate: the base Metis repo must contain zero
    information that identifies its original author.
    """
    tracked = get_tracked_files(repo_root)
    assert tracked, "No tracked files found — git ls-files returned nothing"

    all_findings: list[Finding] = []
    scanned = 0

    for path in tracked:
        if should_skip_file(path):
            continue
        findings = scan_file(path)
        all_findings.extend(findings)
        scanned += 1

    if not all_findings:
        # Clean — nothing to report
        return

    # Build a readable failure report
    by_file: dict[Path, list[Finding]] = {}
    for f in all_findings:
        by_file.setdefault(f.file, []).append(f)

    lines = [
        f"\n{'='*70}",
        f"PERSONAL DATA SCAN FAILED — {len(all_findings)} finding(s) in {len(by_file)} file(s)",
        f"Scanned {scanned} tracked files.",
        f"{'='*70}",
    ]
    for file_path, file_findings in sorted(by_file.items()):
        rel = file_path.relative_to(repo_root)
        lines.append(f"\n{rel}")
        for f in file_findings:
            lines.append(f"  L{f.line_no:4d}  [{f.pattern_name}]  {f.line_content!r}")
    lines.append(f"\n{'='*70}")
    lines.append("Fix: remove or gitignore all listed files/lines before pushing to origin.")

    pytest.fail("\n".join(lines))


# ---------------------------------------------------------------------------
# Targeted sub-tests — fast, file-specific checks
# ---------------------------------------------------------------------------

def test_claude_md_no_real_name(metis_root: Path):
    """CLAUDE.md ships as a template — must not contain the owner's real name."""
    claude_md = metis_root / "CLAUDE.md"
    if not claude_md.exists():
        pytest.skip("CLAUDE.md not found")
    text = claude_md.read_text()
    for pat in [re.compile(r"\bStan\b"), re.compile(r"Verschaeve"), re.compile(r"sverschaeve")]:
        m = pat.search(text)
        assert not m, f"CLAUDE.md contains personal name at: {m.group(0)!r}"


def test_no_context_files_tracked(repo_root: Path):
    """No *-context.md personal overlay files should be tracked by git."""
    result = subprocess.run(
        ["git", "ls-files", "--", "*-context.md"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    tracked_contexts = [l for l in result.stdout.splitlines() if l.strip()]
    assert not tracked_contexts, (
        f"Personal context files tracked by git: {tracked_contexts}\n"
        "These must be gitignored."
    )


def test_no_session_logs_tracked(repo_root: Path):
    """session-log.md and similar personal session state files must not be tracked."""
    # Exact filename checks — match the file name component only, not substrings
    personal_filenames = {
        "session-log.md", "implementation-progress.json",
        "user-config.yaml", "user-preferences.json",
        "thinking-profile.yaml",
    }
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    tracked = result.stdout.splitlines()
    violations = [
        f for f in tracked
        if Path(f).name in personal_filenames
    ]
    assert not violations, (
        f"Personal config/state files tracked by git:\n" +
        "\n".join(f"  {v}" for v in violations)
    )


def test_no_sqlite_files_tracked(repo_root: Path):
    """Database files (.sqlite, .db) must never be committed."""
    result = subprocess.run(
        ["git", "ls-files", "--", "*.sqlite", "*.db"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    committed_dbs = [l for l in result.stdout.splitlines() if l.strip()]
    assert not committed_dbs, (
        f"Database files committed to git: {committed_dbs}\n"
        "These may contain personal research data."
    )


def test_git_log_no_personal_data(repo_root: Path):
    """Commit messages must not contain personal names or institutional details."""
    result = subprocess.run(
        ["git", "log", "--oneline", "-100", "--format=%s"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    messages = result.stdout.splitlines()
    personal_pats = [
        re.compile(r"\bStan\b", re.IGNORECASE),
        re.compile(r"Verschaeve", re.IGNORECASE),
        re.compile(r"sverschaeve", re.IGNORECASE),
        re.compile(r"@itg\.be"),
        re.compile(r"Institute of Tropical Medicine"),
    ]
    violations = []
    for msg in messages:
        for pat in personal_pats:
            if pat.search(msg):
                violations.append(f"  [{pat.pattern}] in: {msg!r}")
    assert not violations, (
        "Personal data found in commit messages (last 100):\n" +
        "\n".join(violations) + "\n"
        "Consider squashing or rewriting history before publishing."
    )


def test_pyproject_no_personal_author(repo_root: Path):
    """pyproject.toml must not list the author's real name or personal email."""
    pyproject = repo_root / "metis" / "system" / "mcp-server" / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("pyproject.toml not found")
    text = pyproject.read_text()
    assert "sverschaeve" not in text, "pyproject.toml contains personal username"
    assert "@itg.be" not in text, "pyproject.toml contains institutional email"
    assert "Verschaeve" not in text.lower(), "pyproject.toml contains family name"
