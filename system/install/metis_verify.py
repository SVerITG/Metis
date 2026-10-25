#!/usr/bin/env python3
"""metis_verify.py — does Metis work on this computer, and if not, fix it.

The self-check every installation runs on a schedule (set up by the installers),
and that Claude can run on request (`verify_install` tool, `metis-verify` prompt).
Written for someone who will never open a terminal: every problem is stated in
plain words, and --fix repairs what can be repaired without them.

WHAT IT CHECKS — the way Claude actually reaches Metis
  connection   Claude Desktop and/or Claude Code has Metis registered, and the
               command registered there exists
  starts       Metis starts from that exact registration and answers the
               protocol, in time for Claude not to give up
  database     the database exists where the server reads it, is intact, and
               has every table the dashboard expects
  search       the search model is on disk (search works offline)
  profile      Metis knows the person's name and interests
  disk         enough free space beside the database

WHAT --fix REPAIRS
  connection   re-registers Metis with Claude Desktop (merging, never replacing)
  starts       reinstalls the Metis package into its environment
  database     creates it, or adds missing tables (CREATE … IF NOT EXISTS only)
  search       downloads the model (needs internet)
  Profile and disk are reported, never "fixed": they need a person.

OUTPUT
  system/config/readiness.json — the verdict the dashboard shows on Today and
  the Metis tab. Exit 0 ready · 1 ready with warnings · 2 not ready.

    python metis_verify.py              check
    python metis_verify.py --fix        check and repair
    python metis_verify.py --quiet      no output (scheduled runs)
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("METIS_RC_ROOT", str(ROOT))
_SRC = ROOT / "system" / "mcp-server" / "src"
RESULT_JSON = Path(os.environ.get("METIS_VERIFY_RESULT") or ROOT / "system" / "config" / "readiness.json")
SCHEMA = ROOT / "system" / "installer" / "schema.sql"

PASS, WARN, FAIL = "pass", "warn", "fail"
results: list[dict] = []
QUIET = False
# Claude Desktop waits about a minute for a connector to answer before it marks
# it failed; the first start after boot is the slowest, so warn well before that.
SLOW_START_S = 30


def record(area: str, name: str, status: str, detail: str = "", fix: str = "") -> None:
    results.append({"area": area, "name": name, "status": status,
                    "detail": " ".join(str(detail).split())[:300], "fix": fix})
    if not QUIET:
        mark = {"pass": "✓", "warn": "!", "fail": "✗"}[status]
        print(f"  {mark} {name}" + (f" — {detail}" if detail and status != PASS else ""))


# ── where Claude has Metis registered ────────────────────────────────────────

def desktop_config_path() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") \
            / "Claude" / "claude_desktop_config.json"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def registrations() -> list[tuple[str, dict]]:
    """Every place Metis is registered: (label, server entry)."""
    found = []
    try:
        desk = json.loads(desktop_config_path().read_text(encoding="utf-8-sig"))
        entry = (desk.get("mcpServers") or {}).get("metis-rc")
        if isinstance(entry, dict) and entry.get("command"):
            found.append(("Claude Desktop", entry))
    except (OSError, ValueError):
        pass
    # Claude Code: user scope (every folder) at the top of ~/.claude.json, or a
    # per-folder registration under "projects" — older installs made those.
    try:
        code = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        code = {}
    entry = (code.get("mcpServers") or {}).get("metis-rc")
    if not entry:
        for folder in (code.get("projects") or {}).values():
            entry = ((folder or {}).get("mcpServers") or {}).get("metis-rc")
            if entry:
                break
    if isinstance(entry, dict) and entry.get("command"):
        found.append(("Claude Code", entry))
    return found


def _local_command(entry: dict) -> tuple[str, list[str], dict]:
    """The command as this machine can run it. A WSL registration (wsl.exe … bash
    run.sh) is probed by running its bash part directly, from inside Linux."""
    cmd, args = entry["command"], list(entry.get("args") or [])
    env = {**os.environ, **(entry.get("env") or {})}
    if Path(cmd).name.lower() in ("wsl.exe", "wsl") and "bash" in args:
        return "bash", args[args.index("bash") + 1:], env
    return cmd, args, env


async def _probe(cmd: str, args: list[str], env: dict) -> tuple[float, int]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=cmd, args=args, env=env)
    with open(os.devnull, "w") as devnull:
        async with stdio_client(params, errlog=devnull) as (r, w):
            async with ClientSession(r, w) as s:
                t = time.monotonic()
                await s.initialize()
                started = time.monotonic() - t
                return started, len((await s.list_tools()).tools)


def check_connection(fix: bool) -> list[tuple[str, dict]]:
    regs = registrations()
    # Claude Desktop is installed (its settings exist) but has no Metis: judged on
    # its own, because being connected to Claude Code says nothing about Desktop,
    # and Desktop is where most people will talk to Metis.
    desktop_installed = desktop_config_path().exists()
    if fix and (not regs or (desktop_installed and "Claude Desktop" not in dict(regs))):
        _register_desktop()
        regs = registrations()
    if desktop_installed and "Claude Desktop" not in dict(regs):
        record("connection", "Metis is connected to Claude Desktop", FAIL,
               "Claude Desktop is installed but does not have Metis",
               "run with --fix, then quit and reopen Claude Desktop")
    if not regs:
        record("connection", "Metis is connected to Claude", FAIL,
               "neither Claude Desktop nor Claude Code has Metis registered",
               "run setup again, or: python system/install/register_desktop.py")
        return []
    for label, entry in regs:
        cmd = entry["command"]
        ok = Path(cmd).name.lower() in ("wsl.exe", "wsl") or Path(cmd).exists() or shutil.which(cmd)
        if not ok and fix and label == "Claude Desktop":
            _register_desktop()
            entry = dict(registrations()).get(label, entry)
            ok = Path(entry["command"]).exists()
        record("connection", f"Metis is connected to {label}", PASS if ok else FAIL,
               "" if ok else f"it points at {cmd}, which does not exist",
               "" if ok else "python system/install/register_desktop.py")
    return regs


def _venv_python() -> Path | None:
    for p in (ROOT / "system" / "mcp-server" / ".venv-win" / "Scripts" / "python.exe",
              Path.home() / ".local" / "share" / "metis-mcp" / ".venv" / "bin" / "python3"):
        if p.exists():
            return p
    return None


def _register_desktop() -> None:
    py = _venv_python()
    if py is None or not desktop_config_path().parent.exists():
        return
    subprocess.run([str(py), str(ROOT / "system" / "install" / "register_desktop.py"),
                    "--python", str(py), "--root", str(ROOT)],
                   capture_output=True, timeout=60)


def _reinstall() -> bool:
    # Tests point the checker at a stand-in environment that leads to a real one;
    # they set this so a repair can never reinstall into an installation by accident.
    if os.environ.get("METIS_VERIFY_NO_REINSTALL") == "1":
        return False
    py = _venv_python()
    if py is None:
        return False
    src = ROOT / "system" / "mcp-server"
    lock = src / "requirements.txt"
    uv = shutil.which("uv") or str(Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv"))
    constraint = ["-c", str(lock)] if lock.exists() else []
    if Path(uv).exists():
        cmd = [uv, "pip", "install", "--python", str(py), *constraint, f"{src}[embedding,library,ocr]"]
    else:
        cmd = [str(py), "-m", "pip", "install", *constraint, f"{src}[embedding,library,ocr]"]
    return subprocess.run(cmd, capture_output=True, timeout=1800).returncode == 0


def check_starts(regs: list[tuple[str, dict]], fix: bool) -> None:
    if not regs:
        return
    label, entry = regs[0]
    for attempt in (1, 2):
        try:
            started, n = asyncio.run(asyncio.wait_for(_probe(*_local_command(entry)), 180))
        except Exception as exc:
            if attempt == 1 and fix and _reinstall():
                continue
            record("starts", "Metis starts when Claude asks", FAIL,
                   f"it did not answer ({type(exc).__name__})",
                   "run with --fix, or run setup again")
            return
        record("starts", "Metis starts when Claude asks",
               PASS if started < SLOW_START_S else WARN,
               f"answered in {started:.0f}s with {n} tools" if started < SLOW_START_S
               else f"took {started:.0f}s — Claude may give up on a slow start; try again after a restart")
        return


# ── database, search, profile, disk ──────────────────────────────────────────

def _db_path() -> Path:
    sys.path.insert(0, str(_SRC))
    try:
        from metis_mcp.config import resolve_live_db
        return resolve_live_db(ROOT)
    except Exception:
        data = os.environ.get("METIS_DATA_DIR") or str(Path.home() / ".local" / "share" / "metis")
        return Path(os.environ.get("METIS_DB") or Path(data) / "metis.sqlite")


def _schema_tables() -> set[str]:
    import re
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA.read_text(encoding="utf-8")))


def check_database(fix: bool) -> Path:
    db = _db_path()
    if not db.exists() and fix and SCHEMA.exists():
        db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db)
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        con.close()
    if not db.exists():
        record("database", "Your Metis database", FAIL, f"not found at {db}", "run with --fix")
        return db
    try:
        con = sqlite3.connect(db, timeout=15)
        verdict = con.execute("PRAGMA quick_check").fetchone()[0]
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = _schema_tables() - have if SCHEMA.exists() else set()
        if missing and fix:
            # IF NOT EXISTS only: adds what is absent, never touches what is there.
            con.executescript(SCHEMA.read_text(encoding="utf-8"))
            have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            missing = _schema_tables() - have
        con.close()
    except sqlite3.Error as exc:
        record("database", "Your Metis database", FAIL, f"could not be opened: {exc}",
               "restore it from a backup (ask for help)")
        return db
    if verdict != "ok":
        record("database", "Your Metis database", FAIL, f"damaged: {verdict}",
               "restore it from a backup (ask for help)")
    elif missing:
        record("database", "Your Metis database", WARN,
               f"{len(missing)} table(s) missing — some panels will be empty", "run with --fix")
    else:
        record("database", "Your Metis database", PASS)
    return db


def check_search(fix: bool) -> None:
    def cached() -> bool:
        places = [Path.home() / ".cache" / "fastembed", Path.home() / ".cache" / "huggingface" / "hub"]
        try:
            sys.path.insert(0, str(_SRC))
            from metis_mcp.embeddings import _cache_candidates
            places = list(_cache_candidates()) + places
        except Exception:
            pass
        return any(p.exists() and any(p.rglob("*.onnx")) for p in places)

    if not cached() and fix:
        py = _venv_python() or Path(sys.executable)
        env = {**os.environ, "HF_HUB_OFFLINE": "0"}
        subprocess.run([str(py), "-c", "from metis_mcp.embeddings import embed_query; embed_query('warmup')"],
                       capture_output=True, timeout=900, env=env)
    ok = cached()
    record("search", "Search works offline", PASS if ok else WARN,
           "" if ok else "the search model is not downloaded yet", "" if ok else "run with --fix while online")


def check_profile() -> None:
    try:
        prefs = json.loads((ROOT / "system" / "config" / "user-preferences.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prefs = {}
    name = str(prefs.get("display_name") or "").strip()
    interests = prefs.get("library_interests") or prefs.get("interests") or []
    if name and interests:
        record("profile", "Metis knows who you are", PASS)
    else:
        record("profile", "Metis knows who you are", WARN,
               "your name or interests are missing — Claude will ask you for them",
               "say hello to Metis in Claude Desktop")


def check_disk(db: Path) -> None:
    where = db.parent if db.parent.exists() else Path.home()
    free_gb = shutil.disk_usage(where).free / 1e9
    record("disk", "Enough disk space", PASS if free_gb >= 2 else (WARN if free_gb >= 0.5 else FAIL),
           f"{free_gb:.1f} GB free", "" if free_gb >= 2 else "free some space on this drive")


# ── report ───────────────────────────────────────────────────────────────────

def write_report(started: float) -> int:
    fails = [r for r in results if r["status"] == FAIL]
    warns = [r for r in results if r["status"] == WARN]
    overall = "NOT READY" if fails else ("READY WITH WARNINGS" if warns else "READY")
    data = {"overall": overall,
            "run_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "seconds": round(time.monotonic() - started, 1), "source": "metis_verify",
            "counts": {"pass": len(results) - len(fails) - len(warns), "warn": len(warns), "fail": len(fails)},
            "checks": results}
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = RESULT_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, RESULT_JSON)
    if not QUIET:
        print(f"\n  {overall}" + ("" if not (fails or warns) else
              " — " + "; ".join(r["name"] for r in fails + warns)))
    return 2 if fails else (1 if warns else 0)


def main() -> int:
    global QUIET
    ap = argparse.ArgumentParser(description="Check that Metis works on this computer, and fix it.")
    ap.add_argument("--fix", action="store_true", help="repair what can be repaired")
    ap.add_argument("--quiet", action="store_true", help="no output (scheduled runs)")
    args = ap.parse_args()
    QUIET = args.quiet
    # A Windows console is cp1252, which has no ✓: the first print raised, and
    # every check "crashed" before checking anything.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    started = time.monotonic()
    if not QUIET:
        print("Checking Metis on this computer…")
    sys.path.insert(0, str(_SRC))
    steps = [lambda: check_starts(check_connection(args.fix), args.fix)]
    db_box: list[Path] = []
    steps += [lambda: db_box.append(check_database(args.fix)),
              lambda: check_search(args.fix), check_profile,
              lambda: check_disk(db_box[0] if db_box else _db_path())]
    for step in steps:
        try:
            step()
        except Exception as exc:  # one broken check must not hide the others
            # FAIL, not WARN: a check that did not run proved nothing, and as a
            # warning it let the installer report "works" while nothing was checked.
            record("verify", "A check could not run", FAIL, f"{type(exc).__name__}: {exc}")
    return write_report(started)


if __name__ == "__main__":
    raise SystemExit(main())
