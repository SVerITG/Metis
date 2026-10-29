#!/usr/bin/env python3
"""Make an edition copy's lists agree with what the copy actually carries.

    python3 editions/prune_edition.py <copy-dir>

An edition leaves specialists and tool modules out (editions/<id>/exclude.
gitignore, edition.json "modules_off"). Three files LIST them all the same, and
a list that names what is not there is a promise the copy cannot keep: routing
would pick a specialist with no prompt to load, Desktop's introduction would
offer it, and a tool group would name a module that never loads.

    system/config/agent-registry.json   entries whose agents/<slug>/ is absent
    system/config/tool-subsets.json     those agents' subsets; modules switched off
    system/config/agent-intros.md       the bullet introducing a removed specialist

Run on the COPY by editions/export-edition.sh, after the overlay, before the
scan. The development tree is never touched.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def main() -> int:
    copy = Path(sys.argv[1])
    cfg = copy / "system" / "config"
    present = {d.name for d in (copy / "agents").iterdir() if d.is_dir()}
    edition = json.loads((cfg / "edition.json").read_text(encoding="utf-8"))
    off = set(edition.get("modules_off") or [])

    reg_p = cfg / "agent-registry.json"
    reg = json.loads(reg_p.read_text(encoding="utf-8"))
    removed = [a for a in reg["agents"] if a.get("slug") not in present]
    reg["agents"] = [a for a in reg["agents"] if a.get("slug") in present]
    for a in reg["agents"]:  # a kept specialist must not hand over to a removed one
        if isinstance(a.get("chains_with"), list):
            a["chains_with"] = [s for s in a["chains_with"] if s in present]
    reg_p.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ts_p = cfg / "tool-subsets.json"
    ts = json.loads(ts_p.read_text(encoding="utf-8"))
    ts["core"] = [m for m in ts["core"] if m not in off]
    ts["groups"] = {g: [m for m in mods if m not in off] for g, mods in ts["groups"].items()}
    ts["agents"] = {k: v for k, v in ts["agents"].items() if k.startswith("_") or k in present}
    for k, v in ts["agents"].items():
        if isinstance(v, list):
            ts["agents"][k] = [g for g in v if g not in off]
    ts_p.write_text(json.dumps(ts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    intro_p = cfg / "agent-intros.md"
    n_intro = 0
    if intro_p.exists():
        names = {a.get("name", "") for a in removed if a.get("name")}
        keep = []
        for line in intro_p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*-\s+\*\*(.+?)\*\*", line)
            if m and m.group(1) in names:
                n_intro += 1
                continue
            keep.append(line)
        intro_p.write_text("\n".join(keep) + "\n", encoding="utf-8")

    print(f"Pruned: {len(removed)} specialists from the registry "
          f"({', '.join(a['slug'] for a in removed)}), {n_intro} introductions, "
          f"modules off: {', '.join(sorted(off)) or 'none'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
