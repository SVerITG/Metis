#!/usr/bin/env python3
"""Account guard: make every git push go to the account its project belongs to.

The projects and accounts are declared in system/config/accounts.json (no
secrets: names, ids and where each login is kept). This script is called by the
pre-push hook that `install` puts in each repository:

    python3 account_guard.py install <repo>           put the hook in a repository
    python3 account_guard.py which [<path>]           which project/account a folder belongs to
    python3 account_guard.py pre-push <repo> <url>    (called by the hook) allow or refuse

A push to a remote that is not declared for that project is REFUSED. A commit
whose author e-mail belongs to the other account only gives a warning: older
history legitimately carries the address used at the time.
Override for one push, deliberately: git push --no-verify
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REGISTRY = Path(os.environ.get(
    "METIS_ACCOUNTS",
    Path(__file__).resolve().parents[1] / "config" / "accounts.json"))


def load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def norm_path(p: str) -> str:
    return os.path.normcase(os.path.realpath(os.path.expanduser(p))).rstrip("/")


def find_project(reg: dict, path: str) -> dict | None:
    """The project whose folder contains `path` (the longest match wins)."""
    target = norm_path(path)
    best = None
    for proj in reg.get("projects", []):
        root = norm_path(proj["path"])
        if target == root or target.startswith(root + "/"):
            if best is None or len(root) > len(norm_path(best["path"])):
                best = proj
    return best


def remote_key(url: str) -> str:
    """git@github-personal:StannVer/EPSO.git / https://github.com/X/Y -> host:owner/repo"""
    url = url.strip()
    m = re.match(r"^(?:ssh://)?git@([^:/]+)[:/](.+?)(?:\.git)?/?$", url)
    if not m:
        m = re.match(r"^https?://(?:[^@/]+@)?([^/]+)/(.+?)(?:\.git)?/?$", url)
    if not m:
        return url
    return f"{m.group(1).lower()}:{m.group(2)}"


def cmd_which(path: str) -> int:
    reg = load()
    proj = find_project(reg, path)
    if not proj:
        print(f"No project in {REGISTRY} covers {path}.")
        return 1
    acct = reg["accounts"][proj["account"]]
    print(json.dumps({"project": proj, "account": {"key": proj["account"], **acct}}, indent=2, ensure_ascii=False))
    return 0


def cmd_pre_push(repo: str, url: str) -> int:
    if not REGISTRY.exists():
        # A plain Metis installation (someone else's clone) has no registry:
        # nothing is declared, so there is nothing to enforce.
        return 0
    try:
        reg = load()
    except Exception as exc:  # fail closed: an unreadable registry must not wave pushes through
        print(f"account guard: cannot read {REGISTRY} ({exc}). Push refused; fix the file or use --no-verify deliberately.")
        return 1
    proj = find_project(reg, repo)
    if not proj:
        print(f"account guard: {repo} is not declared in {REGISTRY}. Push refused: add the project first, so Metis knows which account it uses.")
        return 1
    key = remote_key(url)
    # Entries are written "host:owner/repo"; a full URL is accepted too.
    allowed = [remote_key(r) if r.startswith(("git@", "ssh://", "http")) else r
               for r in proj.get("git_remotes", [])]
    if key not in allowed:
        acct = reg["accounts"][proj["account"]]["label"]
        print(f"account guard: REFUSED. '{proj['name']}' belongs to the {acct} account and may push only to:")
        for r in proj.get("git_remotes", []):
            print(f"    {r}")
        print(f"  This push goes to {key}.")
        if proj.get("notes"):
            print(f"  ({proj['notes']})")
        return 1
    # Author e-mails of the commits being pushed: warn only.
    mine = set(reg["accounts"][proj["account"]]["github"].get("commit_emails", []))
    other = {e for k, a in reg["accounts"].items() if k != proj["account"] for e in a["github"].get("commit_emails", [])}
    stdin = sys.stdin.read() if not sys.stdin.isatty() else ""
    wrong = set()
    for line in stdin.splitlines():
        parts = line.split()
        if len(parts) != 4 or set(parts[1]) == {"0"}:
            continue
        local_sha, remote_sha = parts[1], parts[3]
        rng = local_sha if set(remote_sha) == {"0"} else f"{remote_sha}..{local_sha}"
        try:
            emails = subprocess.run(["git", "-C", repo, "log", "--format=%ae", rng, "--not", "--remotes"],
                                    capture_output=True, text=True, check=True).stdout.split()
        except subprocess.CalledProcessError:
            continue
        wrong |= {e for e in emails if e in other and e not in mine}
    if wrong:
        print(f"account guard: note: new commits carry the other account's e-mail ({', '.join(sorted(wrong))}). "
              f"Set it for this repository: git config user.email {sorted(mine)[0] if mine else '<e-mail>'}")
    print(f"account guard: OK, {proj['name']} -> {key} ({reg['accounts'][proj['account']]['label']}).")
    return 0


HOOK = """#!/usr/bin/env bash
# Installed by Metis (system/release/account_guard.py install). Refuses a push to
# a remote that accounts.json does not declare for this project.
exec python3 "{guard}" pre-push "$(git rev-parse --show-toplevel)" "$2"
"""


def cmd_install(repo: str) -> int:
    hooks_path = subprocess.run(["git", "-C", repo, "config", "core.hooksPath"],
                                capture_output=True, text=True).stdout.strip()
    if hooks_path:
        hooks = Path(hooks_path) if os.path.isabs(hooks_path) else Path(repo) / hooks_path
    else:
        git_dir = subprocess.run(["git", "-C", repo, "rev-parse", "--git-common-dir"],
                                 capture_output=True, text=True, check=True).stdout.strip()
        hooks = (Path(repo) / git_dir if not os.path.isabs(git_dir) else Path(git_dir)) / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / "pre-push"
    if hook.exists() and "account_guard.py" not in hook.read_text(encoding="utf-8", errors="replace"):
        hook.rename(hooks / "pre-push.before-account-guard")
    hook.write_text(HOOK.format(guard=Path(__file__).resolve()), encoding="utf-8")
    hook.chmod(0o755)
    print(f"installed {hook}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "which":
        return cmd_which(argv[2] if len(argv) > 2 else os.getcwd())
    if len(argv) == 4 and argv[1] == "pre-push":
        return cmd_pre_push(argv[2], argv[3])
    if len(argv) == 3 and argv[1] == "install":
        return cmd_install(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
