#!/usr/bin/env python3
"""Give Claude Desktop a scheduled task that writes the Metis morning briefing.

The briefing is written by Claude Desktop, on the person's own subscription:
every weekday a scheduled task opens a session in the Metis folder, follows
system/config/scheduled/morning-briefing.md, and saves the brief through the
Metis connector. The dashboard only shows it. An API key stays an option (the
dashboard can then write it itself) but is never needed.

A Desktop scheduled task is two things:
  ~/.claude/scheduled-tasks/<id>/SKILL.md          what the task says to do
  <Claude data>/claude-code-sessions/<account>/<org>/scheduled-tasks.json
                                                   when it runs, and where
The second folder exists only once someone has signed in to Claude Desktop, so
on a fresh computer setup can write the first half and not the second. The
install doctor runs this again every day until it can ("pending" below).

    python register_schedule.py --root C:\\...\\Metis [--time 08:30]
    python register_schedule.py --root … --status    # registered | pending | off
    python register_schedule.py --remove             # uninstall

Only the task's own entry is touched; every other task is kept. A time the
person changed in Claude Desktop is kept too: a reinstall refreshes where the
task points, never when it runs. Exit 0 on success (pending included); 1 when a
settings file is not valid JSON and was therefore left alone.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

TASK_ID = "metis-morning-briefing"
DISPLAY_NAME = "Metis morning briefing"
ROUTINE = Path("system") / "config" / "scheduled" / "morning-briefing.md"
DEFAULT_TIME = "08:30"


def skill_file() -> Path:
    return Path.home() / ".claude" / "scheduled-tasks" / TASK_ID / "SKILL.md"


def _data_dirs() -> list[Path]:
    """Claude Desktop's data folder: the installer edition and the Microsoft
    Store edition keep it in different places."""
    dirs = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        dirs.append(Path(appdata) / "Claude")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs += sorted((Path(local) / "Packages").glob("Claude_*/LocalCache/Roaming/Claude"))
    return [d for d in dirs if d.is_dir()]


def task_files() -> list[Path]:
    """One scheduled-tasks.json per signed-in account and organisation."""
    out = []
    for d in _data_dirs():
        for org in sorted((d / "claude-code-sessions").glob("*/*")):
            if org.is_dir():
                out.append(org / "scheduled-tasks.json")
    return out


def skill_text(root: Path) -> str:
    return (
        "---\n"
        f"name: {TASK_ID}\n"
        "description: Writes the Metis morning briefing each weekday and leaves it on the dashboard\n"
        "---\n\n"
        f"Work in the Metis folder: {root}\n\n"
        f"Read {root / ROUTINE} and follow it exactly, from step 1. It is the one "
        "definition of this routine and is updated with Metis; do not improvise steps "
        "that are not in it.\n\n"
        "Use the Metis connector (the metis-rc tools). Never wait on a step that hangs: "
        "note it and move on. When done, reply with one short summary: what was saved, "
        "and which steps failed.\n"
    )


def _cron(hhmm: str) -> str:
    h, m = (int(x) for x in hhmm.split(":", 1))
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(hhmm)
    return f"{m} {h} * * 1-5"


def _load(path: Path) -> dict | None:
    if not path.exists():
        return {"scheduledTasks": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except (OSError, ValueError):
        return None
    data.setdefault("scheduledTasks", [])
    return data


def _save(path: Path, data: dict) -> None:
    backup = path.with_name(path.name + ".before-metis")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def register(root: Path, hhmm: str = DEFAULT_TIME) -> tuple[str, list[str]]:
    """Write the task. Returns (status, notes); status is 'registered' when at
    least one Claude Desktop account has it, else 'pending'."""
    notes: list[str] = []
    sk = skill_file()
    sk.parent.mkdir(parents=True, exist_ok=True)
    sk.write_text(skill_text(root), encoding="utf-8")

    files = task_files()
    if not files:
        return "pending", ["Claude Desktop has not been signed in to yet; the daily self-check finishes this later"]
    done = 0
    for f in files:
        data = _load(f)
        if data is None:
            notes.append(f"{f} is not valid JSON; left alone")
            continue
        entry = next((t for t in data["scheduledTasks"] if t.get("id") == TASK_ID), None)
        if entry is None:
            data["scheduledTasks"].append({
                "id": TASK_ID,
                "displayName": DISPLAY_NAME,
                "cronExpression": _cron(hhmm),
                "enabled": True,
                "filePath": str(sk),
                "createdAt": int(time.time() * 1000),
                "cwd": str(root),
            })
        else:
            entry.update({"filePath": str(sk), "cwd": str(root)})
        _save(f, data)
        done += 1
    return ("registered" if done else "pending"), notes


def status() -> str:
    for f in task_files():
        data = _load(f) or {}
        if any(t.get("id") == TASK_ID for t in data.get("scheduledTasks", [])):
            return "registered"
    return "pending" if skill_file().exists() else "off"


def remove() -> int:
    bad = 0
    for f in task_files():
        data = _load(f)
        if data is None:
            bad = 1
            continue
        kept = [t for t in data["scheduledTasks"] if t.get("id") != TASK_ID]
        if len(kept) != len(data["scheduledTasks"]):
            data["scheduledTasks"] = kept
            _save(f, data)
    shutil.rmtree(skill_file().parent, ignore_errors=True)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, help="the Metis folder")
    ap.add_argument("--time", default=DEFAULT_TIME, help="HH:MM, weekdays (default %(default)s)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    if a.remove:
        return remove()
    if a.status:
        print(status())
        return 0
    if not a.root:
        ap.error("--root is required")
    try:
        _cron(a.time)
    except ValueError:
        ap.error(f"--time must be HH:MM, not {a.time!r}")
    st, notes = register(a.root.resolve(), a.time)
    print(st)
    for n in notes:
        print("  " + n)
    return 1 if any("not valid JSON" in n for n in notes) else 0


if __name__ == "__main__":
    sys.exit(main())
