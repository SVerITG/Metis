#!/usr/bin/env python3
"""Add Metis to Claude Desktop's settings — or take it out again — touching nothing else.

Claude Desktop keeps every connector a person has set up in one file,
claude_desktop_config.json. The Windows installer used to WRITE that file, so
whatever else a colleague had connected was gone after installing Metis. This
merges one entry, `mcpServers["metis-rc"]`, and leaves every other key as it was.

    python register_desktop.py --python C:\\...\\python.exe --root C:\\...\\Metis
    python register_desktop.py --remove          # uninstall: drop only metis-rc

A copy of the previous file is kept next to it as
claude_desktop_config.json.before-metis (the first time only, so a reinstall
never overwrites the person's original with a Metis-modified one).

Exit 0 on success; 1 when the existing file is not valid JSON — then nothing is
written, because a file we cannot read is a file we cannot merge into safely.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ENTRY = "metis-rc"


def config_path() -> Path:
    # Both the classic and the Microsoft Store editions of Claude Desktop read
    # %APPDATA%\Claude\claude_desktop_config.json.
    import platform
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.system() != "Windows":
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Claude" / "claude_desktop_config.json"


def load(path: Path) -> dict | None:
    if not path.exists() or not path.read_text(encoding="utf-8-sig").strip():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--python", help="interpreter that has metis_mcp installed")
    ap.add_argument("--root", help="the Metis folder (METIS_RC_ROOT)")
    ap.add_argument("--remove", action="store_true", help="remove the Metis entry only")
    ap.add_argument("--config", type=Path, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    path = args.config or config_path()
    data = load(path)
    if data is None:
        print(f"Claude Desktop settings at {path} are not valid JSON — left untouched. "
              f"Add Metis by hand, or fix the file and run setup again.")
        return 1

    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}

    if args.remove:
        if ENTRY in servers:
            del servers[ENTRY]
            data["mcpServers"] = servers
            save(path, data)
            print("Metis removed from Claude Desktop; other connectors kept.")
        return 0

    if not args.python or not args.root:
        ap.error("--python and --root are required unless --remove")

    backup = path.with_name(path.name + ".before-metis")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)

    # No API key here: the server reads system/.env itself, and a key in this
    # file is one more plain-text copy for nothing.
    servers[ENTRY] = {
        "command": args.python,
        "args": ["-m", "metis_mcp.server"],
        "env": {"METIS_RC_ROOT": args.root},
    }
    data["mcpServers"] = servers
    save(path, data)
    others = len(servers) - 1
    print(f"Metis added to Claude Desktop ({others} other connector(s) kept).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
