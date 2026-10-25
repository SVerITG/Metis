#!/usr/bin/env python3
"""Add Metis to an AI app's settings — or take it out again — touching nothing else.

Metis is an MCP server, so any app that speaks MCP can use it. Each app keeps
the connectors a person has set up in one settings file. This merges one entry,
"metis-rc", and leaves every other key as it was. The installers used to WRITE
Claude Desktop's file, so whatever else a colleague had connected was gone.

    python register_desktop.py --python C:\\...\\python.exe --root C:\\...\\Metis
    python register_desktop.py --client vscode --python … --root …
    python register_desktop.py --all-installed --python … --root …
    python register_desktop.py --remove                 # uninstall: every app

Apps (CLIENTS below is the one list; the install doctor reads it too):
    claude-desktop   Claude Desktop          (default, and created if missing)
    vscode           VS Code (user mcp.json) only when VS Code is installed
    cursor           Cursor (~/.cursor)      only when Cursor is installed
Claude Code is registered with its own command (`claude mcp add`), not a file.

A copy of each file is kept next to it as <name>.before-metis (the first time
only, so a reinstall never overwrites the person's original with a
Metis-modified one).

Exit 0 on success; 1 when an existing file is not valid JSON — then that file is
not written, because a file we cannot read is a file we cannot merge into safely.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path

ENTRY = "metis-rc"


def _appdata() -> Path:
    return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")


def _user_config_dir(app: str) -> Path:
    """Where an Electron app keeps its per-user settings on this system."""
    system = platform.system()
    if system == "Windows":
        return _appdata() / app
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / app
    return Path.home() / ".config" / app


def _wsl_windows_appdata() -> Path | None:
    """Under WSL, Claude Desktop is a Windows program: its settings are on the
    Windows side, in the Windows user's roaming profile."""
    if platform.system() != "Linux" or "microsoft" not in platform.release().lower():
        return None
    import getpass
    users = Path("/mnt/c/Users")
    mine = users / getpass.getuser() / "AppData" / "Roaming"
    if (mine / "Claude").exists():
        return mine
    found = [p.parent for p in users.glob("*/AppData/Roaming/Claude")] if users.exists() else []
    return found[0] if len(found) == 1 else None


def config_path() -> Path:
    # Both the classic and the Microsoft Store editions of Claude Desktop read
    # %APPDATA%\Claude\claude_desktop_config.json.
    # An explicit folder wins (tests, and anyone with an unusual setup).
    if os.environ.get("METIS_CLAUDE_DESKTOP_DIR"):
        return Path(os.environ["METIS_CLAUDE_DESKTOP_DIR"]) / "claude_desktop_config.json"
    wsl = _wsl_windows_appdata()
    if wsl is not None:
        return wsl / "Claude" / "claude_desktop_config.json"
    return _user_config_dir("Claude") / "claude_desktop_config.json"


# name → label, settings file, the key servers live under, whether the app is
# installed, and the shape of one server entry in that app's format.
CLIENTS: dict[str, dict] = {
    "claude-desktop": {
        "label": "Claude Desktop",
        "path": config_path,
        "key": "mcpServers",
        "installed": lambda: config_path().parent.exists(),
        "shape": lambda e: e,
    },
    "vscode": {
        "label": "VS Code",
        "path": lambda: _user_config_dir("Code") / "User" / "mcp.json",
        "key": "servers",
        "installed": lambda: (_user_config_dir("Code") / "User").exists(),
        "shape": lambda e: {"type": "stdio", **e},
    },
    "cursor": {
        "label": "Cursor",
        "path": lambda: Path.home() / ".cursor" / "mcp.json",
        "key": "mcpServers",
        "installed": lambda: (Path.home() / ".cursor").exists(),
        "shape": lambda e: e,
    },
}


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


def standard_entry(python: str, root: str) -> dict:
    # No API key here: the server reads system/.env itself, and a key in this
    # file is one more plain-text copy for nothing.
    return {"command": python, "args": ["-m", "metis_mcp.server"], "env": {"METIS_RC_ROOT": root}}


def read_entry(client: str) -> dict | None:
    """The Metis entry this app has, or None."""
    c = CLIENTS[client]
    data = load(c["path"]())
    servers = (data or {}).get(c["key"])
    entry = servers.get(ENTRY) if isinstance(servers, dict) else None
    return entry if isinstance(entry, dict) and entry.get("command") else None


def write_entry(client: str, entry: dict) -> bool:
    """Merge Metis into this app's settings. False when the file cannot be read."""
    c = CLIENTS[client]
    path = c["path"]()
    data = load(path)
    if data is None:
        return False
    backup = path.with_name(path.name + ".before-metis")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    servers = data.get(c["key"])
    if not isinstance(servers, dict):
        servers = {}
    plain = {k: entry[k] for k in ("command", "args", "env") if k in entry}
    servers[ENTRY] = c["shape"](plain)
    data[c["key"]] = servers
    save(path, data)
    return True


def remove_entry(client: str) -> bool:
    c = CLIENTS[client]
    path = c["path"]()
    data = load(path)
    servers = (data or {}).get(c["key"])
    if isinstance(servers, dict) and ENTRY in servers:
        del servers[ENTRY]
        save(path, data)
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--python", help="interpreter that has metis_mcp installed")
    ap.add_argument("--root", help="the Metis folder (METIS_RC_ROOT)")
    ap.add_argument("--client", action="append", choices=sorted(CLIENTS),
                    help="app to connect (repeatable; default claude-desktop)")
    ap.add_argument("--all-installed", action="store_true",
                    help="Claude Desktop, plus every other app found on this computer")
    ap.add_argument("--remove", action="store_true", help="remove the Metis entry from every app")
    ap.add_argument("--config", type=Path, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.config:  # tests: one Claude Desktop file at a given path
        CLIENTS["claude-desktop"]["path"] = lambda: args.config

    if args.remove:
        for name, c in CLIENTS.items():
            if remove_entry(name):
                print(f"Metis removed from {c['label']}; other connectors kept.")
        return 0

    if not args.python or not args.root:
        ap.error("--python and --root are required unless --remove")

    targets = args.client or ["claude-desktop"]
    if args.all_installed:
        targets = ["claude-desktop"] + [n for n, c in CLIENTS.items()
                                        if n != "claude-desktop" and c["installed"]()]
    entry = standard_entry(args.python, args.root)
    code = 0
    for name in dict.fromkeys(targets):
        c = CLIENTS[name]
        if write_entry(name, entry):
            data = load(c["path"]()) or {}
            others = len(data.get(c["key"]) or {}) - 1
            print(f"Metis added to {c['label']} ({others} other connector(s) kept).")
        else:
            print(f"{c['label']} settings at {c['path']()} are not valid JSON — left untouched. "
                  f"Fix the file and run setup again.")
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
