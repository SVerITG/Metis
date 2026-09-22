#!/usr/bin/env python3
"""Emit publish rules for the git hooks, so they never restate them.

The hooks are shell, are themselves published, and must not spell out the
names they exist to remove — the same reason tools/base-shell/publish-rules.toml
is gitignored. So the rules have ONE author (check_publish_clean.load_rules)
and the hooks ask for them.

    _rules.py paths   -> one ERE matching any forbidden path
    _rules.py words   -> one word per line, identity/third-party literals only

Exit 1 with no output if the rules cannot be built. A hook that cannot load its
rules must refuse, not pass: "no rules" is not "no problems".
"""

from __future__ import annotations

import importlib.util
import re
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load() -> dict:
    src = ROOT / "tools" / "check_publish_clean.py"
    loader = SourceFileLoader("_publish_rules_src", str(src))
    spec = importlib.util.spec_from_loader("_publish_rules_src", loader)
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE executing: @dataclass resolves its own module through
    # sys.modules, and gets None -> AttributeError if the module is absent.
    sys.modules["_publish_rules_src"] = mod
    loader.exec_module(mod)
    rules, _notes = mod.load_rules()
    return rules


def main() -> int:
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        rules = load()
    except Exception as exc:  # noqa: BLE001
        print(f"could not load publish rules: {exc}", file=sys.stderr)
        return 1

    if what == "paths":
        alts = [f"^{re.escape(p)}" for p in rules.get("forbidden_path_prefixes", [])]
        alts += [f"{re.escape(s)}$" for s in rules.get("forbidden_suffixes", [])]
        alts += [f"^{re.escape(e)}$" for e in rules.get("forbidden_exact_paths", [])]
        if not alts:
            return 1
        print("|".join(alts))
        return 0

    if what == "words":
        controls = {c.lower() for c in rules.get("negative_controls", [])}
        words = (rules.get("forbidden_identity_words", [])
                 + rules.get("forbidden_message_words", [])
                 + rules.get("forbidden_content_words", []))
        out = [w for w in dict.fromkeys(words) if w.lower() not in controls]
        if not out:
            return 1
        print("\n".join(out))
        return 0

    print("usage: _rules.py paths|words", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
