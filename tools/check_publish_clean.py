#!/usr/bin/env python3
"""Refuse to publish a repository that still carries what must never ship.

Run this against the repository that is about to become public — ideally a
fresh mirror clone of the remote, not the working tree, because the working
tree is the one place where a clean answer proves nothing about what is
already published.

    python3 tools/check_publish_clean.py --repo /path/to/mirror.git
    python3 tools/check_publish_clean.py --self-test

Exit codes
----------
0   clean
1   usage error
2   BLOCK   — something that must never ship is present
3   WARN    — something suspicious, a human decides
4   REFUSED TO JUDGE

Four is the whole point. Every defect in this repository's publishing history
shares one shape: a step that did nothing returned the same answer as a step
that found nothing. `grep` exits 1 for "no match", "empty input", "wrong
path" and "broken pipe" alike. So every check here reports the size of the
population it searched, and **a check whose denominator is zero fails** — it
did not look at anything, and that is not the same as finding nothing.

Run --self-test first, every time. It builds a throwaway repository carrying
one instance of every rule plus the negative controls, and exits 4 if the
checker fails to flag them. A checker that cannot catch a planted defect
cannot certify the absence of a real one.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = ROOT / "tools" / "base-shell" / "publish-rules.toml"

BLOCK, WARN, REFUSE = "BLOCK", "WARN", "REFUSE"


# ---------------------------------------------------------------- rules ----

DEFAULT_RULES: dict = {
    # Paths that must not appear anywhere in history. Prefix match.
    "forbidden_path_prefixes": [
        "inputs/literature/",
        "inputs/meetings/",
        "inputs/code/",
        "journal/",
        "outputs/",
        "projects/active/",
        "archive/",
        "01_control-room/",
        "system/app/data/",
        # Courses are the owner's own learning material. The shell ships the
        # machinery to build one (knowledge/course-template/) and no content.
        "knowledge/courses/",
        "metis/outputs/",
        "metis/archive/",
        "metis/inputs/",
        "metis/journal/",
        "metis/projects/",
        "metis/01_journal/",
        "metis/09_archive/",
        "metis/07_outputs/",
    ],
    # Blob suffixes that must not appear anywhere in history.
    "forbidden_suffixes": [
        ".pdf", ".docx", ".sqlite", ".sqlite-shm", ".sqlite-wal",
        ".onnx", ".onnx.data", ".zip",
    ],
    "forbidden_exact_paths": ["HANDOFF.md"],
    # Words that must not appear in commit messages. Matched with word
    # boundaries — substring matching inflates every one of these by an order
    # of magnitude (a short name matches inside longer innocent words).
    # Identity and third-party literals live ONLY in the private rules file.
    # A published tool that names what it removes republishes it.
    "forbidden_message_words": [],
    # Trailers that disclose what performed the work.
    "forbidden_message_patterns": [r"co-authored-by:\s*claude"],
    # Strings that must not appear in tracked file contents at the tip.
    "forbidden_content_words": [],
    # Words that LOOK like a hit but are legitimate. If a rule fires on one of
    # these, the rule is broken, not the repository.
    "negative_controls": ["pneumonia", "ammonia", "standalone", "understand", "constant"],
}


def load_rules() -> tuple[dict, list[str]]:
    """Merge the shipped defaults with the private, gitignored rules file.

    The private file holds the maintainer's own identity strings, which is
    exactly the material that must not be published — so the file that names
    them cannot itself be committed. Same reasoning as the existing
    tools/base-shell/scrub-names.txt.
    """
    notes: list[str] = []
    rules = {k: list(v) for k, v in DEFAULT_RULES.items()}
    if not RULES_FILE.exists():
        notes.append(
            f"private rules file absent ({RULES_FILE.name}); identity words are "
            "NOT being checked — defaults only"
        )
        return rules, notes
    if tomllib is None:
        notes.append("tomllib unavailable; private rules file ignored")
        return rules, notes
    try:
        extra = tomllib.loads(RULES_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        notes.append(f"private rules file unreadable: {exc}")
        return rules, notes
    for key, val in extra.items():
        if isinstance(val, list):
            rules.setdefault(key, [])
            rules[key] = list(dict.fromkeys(rules[key] + val))
    notes.append(f"private rules loaded: {RULES_FILE.name}")
    return rules, notes


# --------------------------------------------------------------- finding ---

@dataclass
class Finding:
    level: str
    check: str
    message: str
    denominator: int = 0
    samples: list[str] = field(default_factory=list)


def git(repo: Path, *args: str, check: bool = True) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, errors="replace",
    )
    if check and out.returncode != 0 and not out.stdout:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()[:300]}")
    return out.stdout


def word_re(word: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![0-9A-Za-z]){re.escape(word)}(?![0-9A-Za-z])", re.I)


# ---------------------------------------------------------------- checks ---

def collect_blob_paths(repo: Path) -> list[str]:
    """Every path that has ever existed on any ref.

    NOT `rev-list --objects` alone. Git stores content once, so two files with
    identical bytes are ONE object, and `rev-list --objects` prints that object
    once under whichever path it happened to reach first. A forbidden path
    whose content is byte-identical to an innocent file therefore never
    appears, and a path-based scan silently passes.

    This is not hypothetical: the self-test caught it here, because a planted
    a file under a forbidden directory and a planted `HANDOFF.md` both contained
    "planted\\n", collapsed to one blob, and only `HANDOFF.md` was reported.

    So the path population is the union of two enumerations:
      · `log --name-only`   — every path any commit touched
      · `rev-list --objects` — catches paths in trees no commit diff names
    """
    paths: set[str] = set()

    out = git(repo, "log", "--all", "--format=", "--name-only", check=False)
    for line in out.splitlines():
        line = line.strip()
        if line:
            paths.add(line)

    out = git(repo, "rev-list", "--objects", "--all")
    for line in out.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1].strip():
            paths.add(parts[1])

    return sorted(paths)


def check_paths(repo: Path, rules: dict) -> list[Finding]:
    paths = collect_blob_paths(repo)
    n = len(paths)
    if n == 0:
        return [Finding(REFUSE, "paths",
                        "no object paths found — empty repo, wrong path, or a "
                        "failed rev-list. Cannot certify anything.", 0)]
    findings: list[Finding] = []
    prefixes = tuple(rules["forbidden_path_prefixes"])
    suffixes = tuple(rules["forbidden_suffixes"])
    exact = set(rules["forbidden_exact_paths"])

    hits = [p for p in paths if p.startswith(prefixes)]
    if hits:
        findings.append(Finding(BLOCK, "forbidden-path",
                                f"{len(hits)} object(s) under a forbidden path",
                                n, sorted(set(hits))[:6]))
    hits = [p for p in paths if p.endswith(suffixes)]
    if hits:
        findings.append(Finding(BLOCK, "forbidden-suffix",
                                f"{len(hits)} object(s) with a forbidden extension",
                                n, sorted(set(hits))[:6]))
    hits = [p for p in paths if p in exact]
    if hits:
        findings.append(Finding(BLOCK, "forbidden-file",
                                f"{len(hits)} forbidden file(s)", n,
                                sorted(set(hits))[:6]))
    if not findings:
        findings.append(Finding("OK", "paths", "no forbidden paths", n))
    return findings


def check_messages(repo: Path, rules: dict) -> list[Finding]:
    out = git(repo, "log", "--all", "--format=%H%x00%B%x00%x00")
    # git puts a newline between records, so each entry after the first opens
    # with one. Left in place it ends up inside the reported SHA.
    entries = [e.lstrip("\n") for e in out.split("\x00\x00") if e.strip()]
    n = len(entries)
    if n == 0:
        return [Finding(REFUSE, "messages",
                        "no commit messages read — cannot certify.", 0)]
    findings: list[Finding] = []
    for word in rules["forbidden_message_words"]:
        rx = word_re(word)
        hits = [e.split("\x00")[0][:9] for e in entries if rx.search(e)]
        if hits:
            findings.append(Finding(BLOCK, f"message-word:{word}",
                                    f"{len(hits)} commit(s) name '{word}'",
                                    n, hits[:6]))
    for pat in rules["forbidden_message_patterns"]:
        rx = re.compile(pat, re.I)
        hits = [e.split("\x00")[0][:9] for e in entries if rx.search(e)]
        if hits:
            findings.append(Finding(BLOCK, "message-trailer",
                                    f"{len(hits)} commit(s) match /{pat}/",
                                    n, hits[:6]))
    if not findings:
        findings.append(Finding("OK", "messages", "no forbidden words or trailers", n))
    return findings


def check_identity(repo: Path, rules: dict) -> list[Finding]:
    out = git(repo, "log", "--all", "--format=%an|%ae|%cn|%ce")
    lines = [l for l in out.splitlines() if l.strip()]
    n = len(lines)
    if n == 0:
        return [Finding(REFUSE, "identity", "no authorship read — cannot certify.", 0)]
    people = sorted({l for l in lines})
    findings: list[Finding] = []
    words = rules.get("forbidden_identity_words", [])
    for word in words:
        rx = word_re(word)
        hits = [p for p in people if rx.search(p)]
        if hits:
            findings.append(Finding(BLOCK, f"identity:{word}",
                                    f"{len(hits)} distinct identity string(s) name '{word}'",
                                    n, hits[:4]))
    if len(people) > 0 and not findings:
        findings.append(Finding("OK", "identity",
                                f"{len(people)} distinct author/committer string(s), none forbidden", n))
    return findings


def check_tags(repo: Path) -> list[Finding]:
    out = git(repo, "tag", check=False)
    tags = [t for t in out.splitlines() if t.strip()]
    if tags:
        return [Finding(WARN, "tags",
                        f"{len(tags)} tag(s) present — a tag keeps its whole ancestry "
                        "REACHABLE, so rewriting a branch alone removes nothing",
                        len(tags), tags[:8])]
    return [Finding("OK", "tags", "no tags anchoring old history", 1)]


def check_tip_content(repo: Path, rules: dict) -> list[Finding]:
    words = rules["forbidden_content_words"] + rules.get("forbidden_identity_words", [])
    if not words:
        return [Finding("OK", "tip-content", "no content words configured", 1)]
    out = git(repo, "ls-tree", "-r", "--name-only", "HEAD", check=False)
    files = [f for f in out.splitlines() if f.strip()]
    n = len(files)
    if n == 0:
        return [Finding(REFUSE, "tip-content",
                        "no files at HEAD — bare mirror without a checkout, or wrong ref. "
                        "Use --repo on a mirror plus --tip-ref, or skip this check.", 0)]
    findings: list[Finding] = []
    for word in words:
        res = subprocess.run(
            ["git", "-C", str(repo), "grep", "-I", "-l", "-i", "-w", "-e", word, "HEAD"],
            capture_output=True, text=True, errors="replace",
        )
        hits = [l for l in res.stdout.splitlines() if l.strip()]
        if hits:
            findings.append(Finding(BLOCK, f"tip-content:{word}",
                                    f"{len(hits)} tracked file(s) contain '{word}'",
                                    n, hits[:6]))
    if not findings:
        findings.append(Finding("OK", "tip-content", "no forbidden strings at tip", n))
    return findings


def check_history_content(repo: Path, rules: dict) -> list[Finding]:
    """Scan the content of EVERY blob on every ref, not just the tip.

    The tip-content check answers "is the current source clean?", which is a
    different question from "is anything still published?" — the whole reason
    this job exists. A file scrubbed at HEAD keeps its old text in every commit
    that touched it.

    Binary blobs are skipped and counted separately. Compressed data contains
    arbitrary byte sequences, so a short acronym turns up inside an image by
    chance — one here matched sixteen times. Reporting those as disclosures
    trains the reader to ignore the check, which is worse than not running it.
    """
    words = (rules["forbidden_content_words"]
             + rules.get("forbidden_identity_words", [])
             + rules["forbidden_message_words"])
    if not words:
        return [Finding("OK", "history-content", "no content words configured", 1)]

    out = git(repo, "rev-list", "--objects", "--all")
    names: dict[str, str] = {}
    for line in out.splitlines():
        parts = line.split(" ", 1)
        if parts[0]:
            names[parts[0]] = parts[1] if len(parts) == 2 else "(no path)"
    if not names:
        return [Finding(REFUSE, "history-content", "no objects found", 0)]

    listing = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="\n".join(names).encode(), capture_output=True)
    blobs = [l.split()[0].decode() for l in listing.stdout.splitlines() if b" blob" in l]
    if not blobs:
        return [Finding(REFUSE, "history-content", "no blobs found", 0)]

    patterns = {w: re.compile(
        rf"(^|[^0-9A-Za-z]){re.escape(w)}([^0-9A-Za-z]|$)".encode(), re.I) for w in words}
    found: dict[str, set[str]] = {}
    binary = 0
    for b in blobs:
        data = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", b],
                              capture_output=True).stdout
        if b"\0" in data[:8000]:
            binary += 1
            continue
        for w, rx in patterns.items():
            if rx.search(data):
                found.setdefault(w, set()).add(names.get(b, "?"))

    if found:
        return [Finding(BLOCK, f"history-content:{w}",
                        f"{len(ps)} blob(s) contain '{w}' somewhere in history",
                        len(blobs), sorted(ps)[:5]) for w, ps in found.items()]
    return [Finding("OK", "history-content",
                    f"no forbidden strings in any text blob "
                    f"({binary} binary blob(s) skipped)", len(blobs))]


def check_negative_controls(rules: dict) -> list[Finding]:
    """The rules must not fire on words that merely contain a forbidden one.

    This runs against strings, not the repository, so it always has a
    denominator and can always be evaluated.
    """
    controls = rules["negative_controls"]
    n = len(controls)
    if n == 0:
        return [Finding(REFUSE, "negative-controls", "no controls configured", 0)]
    watched = (rules["forbidden_message_words"]
               + rules["forbidden_content_words"]
               + rules.get("forbidden_identity_words", []))
    bad: list[str] = []
    for control in controls:
        for word in watched:
            if word_re(word).search(control):
                bad.append(f"{word!r} fires on {control!r}")
    if bad:
        return [Finding(REFUSE, "negative-controls",
                        "a rule matches a known-innocent word — the rule is broken, "
                        "so its clean verdicts mean nothing", n, bad[:6])]
    return [Finding("OK", "negative-controls",
                    f"{n} innocent words correctly not matched", n)]


CHECKS = [
    ("negative-controls", lambda r, ru: check_negative_controls(ru)),
    ("paths", check_paths),
    ("messages", check_messages),
    ("identity", check_identity),
    ("tags", lambda r, ru: check_tags(r)),
    ("tip-content", check_tip_content),
    ("history-content", check_history_content),
]


def run_checks(repo: Path, rules: dict) -> list[Finding]:
    findings: list[Finding] = []
    for name, fn in CHECKS:
        try:
            findings.extend(fn(repo, rules))
        except Exception as exc:  # noqa: BLE001
            findings.append(Finding(REFUSE, name,
                                    f"check raised, so it certified nothing: {exc}"))
    return findings


def report(findings: list[Finding], notes: list[str]) -> int:
    for note in notes:
        print(f"  note: {note}")
    print()
    worst = 0
    for f in findings:
        mark = {"OK": "ok  ", BLOCK: "BLOCK", WARN: "warn ", REFUSE: "REFUSE"}[f.level]
        den = f" [searched {f.denominator}]" if f.denominator else " [searched 0]"
        print(f"  {mark} {f.check:<26} {f.message}{den}")
        for s in f.samples:
            print(f"          · {s}")
        # Rank, not exit code. Exit codes are not ordered by severity (2=BLOCK
        # is more severe than 3=WARN), so max() over them silently DOWNGRADED a
        # BLOCK that followed a WARN — the checker reported "WARNINGS" while
        # naming five blocking findings directly above.
        rank = {"OK": 0, WARN: 1, BLOCK: 2, REFUSE: 3}[f.level]
        worst = max(worst, rank)
    print()
    verdict = {0: "CLEAN", 1: "WARNINGS", 2: "BLOCKED", 3: "REFUSED TO JUDGE"}[worst]
    exit_code = {0: 0, 1: 3, 2: 2, 3: 4}[worst]
    print(f"  verdict: {verdict}")
    return exit_code


# ------------------------------------------------------------- self test ---

def self_test() -> int:
    """Plant one instance of every rule and confirm each is caught.

    A checker is only evidence if it can fail. This builds a repository that
    should trip every rule, and treats a clean verdict on it as a failure of
    the checker itself.
    """
    rules_preview, _notes = load_rules()
    message_word = (rules_preview.get("forbidden_message_words") or [None])[0]
    content_word = (rules_preview.get("forbidden_content_words") or [None])[0]
    prefixes = rules_preview.get("forbidden_path_prefixes") or []
    if not message_word or not content_word or not prefixes:
        print("  no message/content/path rules are configured, so there is "
              "nothing to plant and nothing this checker could catch.")
        print(f"  supply them in {RULES_FILE}")
        print("\n  verdict: REFUSED TO JUDGE")
        return 4
    forbidden_dir = prefixes[0].rstrip("/")

    tmp = Path(tempfile.mkdtemp(prefix="publish-selftest-"))
    try:
        repo = tmp / "dirty"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Tester"], check=True)

        (repo / forbidden_dir).mkdir(parents=True)
        (repo / forbidden_dir / "x.txt").write_text("planted\n")
        (repo / "paper.pdf").write_bytes(b"%PDF-1.4 planted\n")
        (repo / "HANDOFF.md").write_text("planted\n")
        content_word = (rules_preview.get("forbidden_content_words") or ["__none__"])[0]
        (repo / "src.py").write_text(f"# references {content_word} here\n")
        # The negative control lives in the repo too: it must NOT be flagged.
        (repo / "clinical.md").write_text("pneumonia and ammonia are innocent\n")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m",
             f"planted commit about {message_word}\n\n"
             "Co-Authored-By: Claude <noreply@anthropic.com>"],
            check=True)
        subprocess.run(["git", "-C", str(repo), "tag", "v0.0.1-planted"], check=True)

        findings = run_checks(repo, rules_preview)

        must_catch = {
            "forbidden-path": False,
            "forbidden-suffix": False,
            "forbidden-file": False,
            f"message-word:{message_word}": False,
            "message-trailer": False,
            "tags": False,
            f"tip-content:{content_word}": False,
            f"history-content:{content_word}": False,
        }
        for f in findings:
            if f.check in must_catch and f.level in (BLOCK, WARN):
                must_catch[f.check] = True

        control_broke = any(
            f.check == "negative-controls" and f.level == REFUSE for f in findings
        )

        print("  self-test — planted defects and whether each was caught:\n")
        for k, v in must_catch.items():
            print(f"    {'caught' if v else 'MISSED'}  {k}")
        print(f"    {'BROKEN' if control_broke else 'ok    '}  negative-controls "
              f"(must not fire on pneumonia/ammonia)")
        print()

        missed = [k for k, v in must_catch.items() if not v]
        if missed or control_broke:
            print(f"  verdict: SELF-TEST FAILED — {len(missed)} rule(s) missed"
                  f"{', negative control broken' if control_broke else ''}")
            print("  This checker cannot certify anything until it catches its own "
                  "planted defects.")
            return 4
        print("  verdict: SELF-TEST PASSED — every planted defect was caught, "
              "and no innocent word was.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Refuse to publish a repository that still carries "
                    "what must never ship.")
    ap.add_argument("--repo", help="repository to check "
                                   "(ideally a fresh mirror clone of the remote)")
    ap.add_argument("--self-test", action="store_true",
                    help="plant every defect and confirm the checker catches it")
    args = ap.parse_args()

    if args.self_test:
        print("\ncheck_publish_clean — self test\n")
        return self_test()

    if not args.repo:
        ap.error("--repo is required (or use --self-test)")
    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print(f"  REFUSE: {repo} does not exist")
        return 4

    rules, notes = load_rules()
    print(f"\ncheck_publish_clean — {repo}\n")
    findings = run_checks(repo, rules)
    return report(findings, notes)


if __name__ == "__main__":
    sys.exit(main())
