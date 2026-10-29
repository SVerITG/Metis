#!/usr/bin/env python3
"""metis_verify.py — the install doctor: does Metis work on this computer, and if not, fix it.

Every requirement Metis has is listed ONCE, in system/install/essentials.json:
the computer, Metis's own programs, every AI app it connects to (Claude
Desktop, Claude Code, VS Code, Cursor), the dashboard, the background tasks and
the data. This script checks each entry in that order, and with --fix repairs
the ones marked repair=auto, then checks them again. Written for someone who
will never open a terminal: every problem is stated in plain words, with what
to do about it.

It is the one doctor. The installers run it at the end of setup and schedule it
daily; Claude runs it on request (verify_install / metis_doctor tools,
metis-verify prompt); the dashboard runs it from the Metis tab. (The server's
own start-up self-diagnosis, run_doctor in tools/doctor.py, is internal and
deliberately does not start servers — this one does.)

OUTPUT
  system/config/readiness.json — the verdict the dashboard shows on Today and
  the Metis tab. Exit 0 ready · 1 ready with warnings · 2 not ready.
  Rows that do not apply (an app that is not installed) are "skip" and do not
  count either way.

    python metis_verify.py              check
    python metis_verify.py --fix        check and repair
    python metis_verify.py --quiet      no output (scheduled runs)

METIS_VERIFY_SANDBOX=1 (tests): repairs never reach outside the test's own
files — no reinstall, no dashboard start, no scheduled tasks, no network.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import filecmp
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("METIS_RC_ROOT", str(ROOT))
HERE = Path(__file__).resolve().parent
_SRC = ROOT / "system" / "mcp-server" / "src"
RESULT_JSON = Path(os.environ.get("METIS_VERIFY_RESULT") or ROOT / "system" / "config" / "readiness.json")
SCHEMA = ROOT / "system" / "installer" / "schema.sql"
ESSENTIALS = HERE / "essentials.json"

sys.path.insert(0, str(HERE))      # register_desktop: the one list of AI apps
import register_desktop as apps    # noqa: E402

PASS, WARN, FAIL, SKIP, PROBLEM = "pass", "warn", "fail", "skip", "problem"
SYSTEM = {"Windows": "windows", "Darwin": "darwin"}.get(platform.system(), "linux")
IS_WSL = SYSTEM == "linux" and "microsoft" in platform.release().lower()
SANDBOX = os.environ.get("METIS_VERIFY_SANDBOX") == "1" or os.environ.get("METIS_VERIFY_NO_REINSTALL") == "1"
# An AI app waits about a minute for a connector to answer before it marks it
# failed; the first start after boot is the slowest, so warn well before that.
SLOW_START_S = 30
QUIET = False

CHECKS: dict[str, Callable[[], tuple[str, str]]] = {}
FIXES: dict[str, Callable[[], str]] = {}


def check(eid: str):
    def deco(fn):
        CHECKS[eid] = fn
        return fn
    return deco


def repair(eid: str):
    def deco(fn):
        FIXES[eid] = fn
        return fn
    return deco


def _run(cmd: list[str], timeout: float = 180, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace", **kw)


# ── shared facts, worked out once and forgotten after a repair ──────────────

_cache: dict = {}


def forget() -> None:
    _cache.clear()


def venv_python() -> Path | None:
    for p in (Path(os.environ.get("LOCALAPPDATA", "")) / "Metis" / "venv" / "Scripts" / "python.exe",
              ROOT / "system" / "mcp-server" / ".venv-win" / "Scripts" / "python.exe",
              Path.home() / ".local" / "share" / "metis-mcp" / ".venv" / "bin" / "python3"):
        if p.is_absolute() and p.exists():
            return p
    return None


def has_dashboard() -> bool:
    return (ROOT / "system" / "app-py" / "main.py").exists()


def claude_code_entry() -> dict | None:
    """Claude Code: user scope (every folder) at the top of ~/.claude.json, or a
    per-folder registration under "projects" — older installs made those."""
    try:
        code = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = (code.get("mcpServers") or {}).get("metis-rc")
    if not entry:
        for folder in (code.get("projects") or {}).values():
            entry = ((folder or {}).get("mcpServers") or {}).get("metis-rc")
            if entry:
                break
    return entry if isinstance(entry, dict) and entry.get("command") else None


def claude_code_installed() -> bool:
    return bool(shutil.which("claude")) or (Path.home() / ".claude.json").exists()


# app id → (label, installed?, current entry)
APPS: dict[str, tuple[str, Callable[[], bool], Callable[[], dict | None]]] = {
    "app_claude_desktop": ("Claude Desktop", apps.CLIENTS["claude-desktop"]["installed"],
                           lambda: apps.read_entry("claude-desktop")),
    "app_claude_code": ("Claude Code", claude_code_installed, claude_code_entry),
    "app_vscode": ("VS Code", apps.CLIENTS["vscode"]["installed"], lambda: apps.read_entry("vscode")),
    "app_cursor": ("Cursor", apps.CLIENTS["cursor"]["installed"], lambda: apps.read_entry("cursor")),
}


def _is_wsl_entry(entry: dict) -> bool:
    return Path(entry["command"]).name.lower() in ("wsl.exe", "wsl")


def _runnable(entry: dict) -> bool:
    cmd = entry["command"]
    return _is_wsl_entry(entry) or Path(cmd).exists() or bool(shutil.which(cmd))


def registered() -> list[tuple[str, dict]]:
    """(label, entry) for every installed app that has Metis."""
    out = []
    for label, installed, entry_of in APPS.values():
        e = entry_of()
        if e:
            out.append((label, e))
    return out


def canonical_entry() -> dict | None:
    """What a newly connected app should start: a registration that already
    works here, else Metis's own Python with the standard arguments."""
    for label, e in registered():
        if not _is_wsl_entry(e) and _runnable(e):
            return {k: e[k] for k in ("command", "args", "env") if k in e}
    py = venv_python()
    return apps.standard_entry(str(py), str(ROOT)) if py else None


def _local_command(entry: dict) -> tuple[str, list[str], dict]:
    """The command as this machine can run it. A WSL registration (wsl.exe … bash
    run.sh) is probed by running its bash part directly, from inside Linux."""
    cmd, args = entry["command"], list(entry.get("args") or [])
    env = {**os.environ, **(entry.get("env") or {})}
    if _is_wsl_entry(entry) and "bash" in args:
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


def probe(entry: dict) -> tuple[float, int] | Exception:
    """Start Metis exactly as an app would, once per distinct command."""
    key = ("probe", entry["command"], tuple(entry.get("args") or []))
    if key not in _cache:
        try:
            _cache[key] = asyncio.run(asyncio.wait_for(_probe(*_local_command(entry)), 180))
        except Exception as exc:  # noqa: BLE001 — any failure means "did not start"
            _cache[key] = exc
    return _cache[key]


def in_venv(code: str, timeout: float = 180) -> subprocess.CompletedProcess | None:
    py = venv_python()
    if py is None:
        return None
    env = {**os.environ, "METIS_RC_ROOT": str(ROOT)}
    return _run([str(py), "-c", code], timeout=timeout, env=env)


def db_path() -> Path:
    try:
        sys.path.insert(0, str(_SRC))
        from metis_mcp.config import resolve_live_db
        return resolve_live_db(ROOT)
    except Exception:
        data = os.environ.get("METIS_DATA_DIR") or str(Path.home() / ".local" / "share" / "metis")
        return Path(os.environ.get("METIS_DB") or Path(data) / "metis.sqlite")


def dashboard_url() -> str:
    if os.environ.get("METIS_VERIFY_DASHBOARD_URL"):
        return os.environ["METIS_VERIFY_DASHBOARD_URL"].rstrip("/")
    port = os.environ.get("METIS_PORT", "")
    pf = ROOT / "system" / "app-py" / ".metis-port"
    if not port and pf.exists():
        port = pf.read_text(encoding="utf-8").strip()
    return f"http://127.0.0.1:{port or 8080}"


def http_status(url: str, timeout: float = 5) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


# ── reinstall: the repair for a broken or outdated program ──────────────────

def reinstall() -> str:
    if SANDBOX:
        return "not attempted (test run)"
    py = venv_python()
    if py is None:
        return "no Metis Python to install into"
    src = ROOT / "system" / "mcp-server"
    lock = src / "requirements.txt"
    constraint = ["-c", str(lock)] if lock.exists() else []
    pkgs = [f"{src}[embedding,library,ocr,office]"]
    app_req = ROOT / "system" / "app-py" / "requirements.txt"
    if has_dashboard() and app_req.exists():
        pkgs += ["-r", str(app_req)]
    uv = next((u for u in (shutil.which("uv"),
                           str(Path(os.environ.get("LOCALAPPDATA", "")) / "Metis" / "bin" / "uv.exe"),
                           str(Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")))
               if u and Path(u).is_absolute() and Path(u).exists()), None)
    env = {**os.environ, "UV_NATIVE_TLS": "1"}
    cmd = ([uv, "pip", "install", "--python", str(py), *constraint, *pkgs] if uv
           else [str(py), "-m", "pip", "install", *constraint, *pkgs])
    forget()
    try:
        r = _run(cmd, timeout=1800, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"the reinstall did not succeed ({type(e).__name__})"
    if r.returncode == 0:
        return "reinstalled"
    # Keep the reason: a failed repair nobody can explain is no help to IT.
    last = next((ln.strip() for ln in reversed((r.stderr or r.stdout).splitlines())
                 if ln.strip()), "")
    return "the reinstall did not succeed" + (f": {last[:200]}" if last else "")


# ═════════════════════════════ the checks ═══════════════════════════════════
# One function per essentials.json id. Each returns (status, detail): pass,
# warn, fail, skip (does not apply here), or problem (counts as the severity
# the list gives it).

# ── computer ────────────────────────────────────────────────────────────────

@check("os_supported")
def _os():
    if SYSTEM == "windows":
        build = sys.getwindowsversion().build  # type: ignore[attr-defined]
        return (PASS, f"Windows build {build}") if build >= 17763 else \
               (PROBLEM, f"Windows build {build}; build 17763 (Windows 10 version 1809) or newer is needed")
    return PASS, f"{platform.system()} {platform.release()}"


@check("disk_space")
def _disk():
    d = db_path()
    where = d.parent if d.parent.exists() else Path.home()
    free_gb = shutil.disk_usage(where).free / 1e9
    if free_gb >= 2:
        return PASS, f"{free_gb:.1f} GB free"
    return (WARN if free_gb >= 0.5 else FAIL), f"only {free_gb:.1f} GB free"


@check("internet")
def _internet():
    if SANDBOX:
        return SKIP, "not checked in a test run"
    try:
        from metis_mcp.config import use_system_certificates
        use_system_certificates()
    except Exception:
        pass
    hosts = ["https://pypi.org/simple/pip/", "https://github.com", "https://huggingface.co"]
    bad, cert = [], False
    for url in hosts:
        try:
            urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=8)
        except urllib.error.HTTPError:
            pass  # the host answered
        except Exception as exc:  # noqa: BLE001
            bad.append(url.split("/")[2])
            cert = cert or "CERTIFICATE" in str(exc).upper()
    if not bad:
        return PASS, "pypi.org, github.com and huggingface.co answer"
    if len(bad) == len(hosts):
        return PROBLEM, "no connection — everything on this computer works; news, new papers and updates wait"
    why = " (the network replaces their security certificate)" if cert else ""
    return PROBLEM, "cannot reach " + ", ".join(bad) + why


# ── Metis's own programs ────────────────────────────────────────────────────

@check("python_env")
def _python_env():
    r = in_venv("import sys; print('%d.%d' % sys.version_info[:2])", timeout=60)
    if r is None:
        return PROBLEM, "not found"
    if r.returncode != 0:
        return PROBLEM, "it is there but does not run"
    v = r.stdout.strip()
    major, minor = (int(x) for x in v.split("."))
    if (major, minor) < (3, 10) or (major, minor) >= (3, 14):
        return PROBLEM, f"Python {v}; Metis needs 3.10 to 3.13"
    return PASS, f"Python {v} at {venv_python()}"


@check("tools_import")
def _tools_import():
    r = in_venv("import metis_mcp.server")
    if r is None:
        return SKIP, "needs Metis's own Python"
    if r.returncode == 0:
        return PASS, ""
    last = (r.stderr.strip().splitlines() or ["no detail"])[-1]
    return PROBLEM, f"they do not load: {last[:200]}"


@repair("tools_import")
def _fix_tools():
    return reinstall()


@check("tools_current")
def _tools_current():
    src = _SRC / "metis_mcp"
    if not src.is_dir():
        return SKIP, "no source copy to compare with"
    r = in_venv("import os, metis_mcp; print(os.path.dirname(metis_mcp.__file__))", timeout=60)
    if r is None or r.returncode != 0:
        return SKIP, "the tools do not load (reported above)"
    inst = Path(r.stdout.strip().splitlines()[-1])
    try:
        if inst.resolve() == src.resolve():
            return PASS, "runs directly from this copy"
    except OSError:
        pass
    stale = [str(f.relative_to(src)) for f in src.rglob("*.py")
             if "__pycache__" not in f.parts
             and not ((inst / f.relative_to(src)).exists()
                      and filecmp.cmp(f, inst / f.relative_to(src), shallow=False))]
    if not stale:
        return PASS, "installed copy matches"
    return PROBLEM, f"{len(stale)} file(s) are older than this version of Metis"


repair("tools_current")(_fix_tools)


@check("office_documents")
def _office_documents():
    r = in_venv("import docx, pptx", timeout=60)
    if r is None:
        return SKIP, "needs Metis's own Python"
    if r.returncode == 0:
        return PASS, ""
    return PROBLEM, "the Word and PowerPoint libraries are missing; templates cannot be filled"


@repair("office_documents")
def _fix_office_documents():
    return reinstall()


@check("search_engine")
def _search_engine():
    r = in_venv("import onnxruntime", timeout=120)
    if r is None:
        return SKIP, "needs Metis's own Python"
    if r.returncode == 0:
        return PASS, ""
    dll = "DLL" in r.stderr or "msvcp" in r.stderr.lower()
    return PROBLEM, ("Microsoft's Visual C++ runtime is missing" if dll
                     else "it does not load; document search is off")


@repair("search_engine")
def _fix_search_engine():
    if SANDBOX:
        return "not attempted (test run)"
    if SYSTEM == "windows" and shutil.which("winget"):
        arm = os.environ.get("PROCESSOR_ARCHITECTURE") == "ARM64"
        _run(["winget", "install", "--id", f"Microsoft.VCRedist.2015+.{'arm64' if arm else 'x64'}",
              "--silent", "--accept-package-agreements", "--accept-source-agreements"], timeout=600)
        forget()
        return "asked Windows to install the Visual C++ runtime"
    return reinstall()


def _model_cached() -> bool:
    places = [Path.home() / ".cache" / "fastembed", Path.home() / ".cache" / "huggingface" / "hub"]
    try:
        sys.path.insert(0, str(_SRC))
        from metis_mcp.embeddings import _cache_candidates
        places = list(_cache_candidates()) + places
    except Exception:
        pass
    return any(p.exists() and any(p.rglob("*.onnx")) for p in places)


@check("search_model")
def _search_model():
    return (PASS, "") if _model_cached() else (PROBLEM, "the search model is not downloaded yet")


@repair("search_model")
def _fix_search_model():
    if SANDBOX:
        return "not attempted (test run)"
    py = venv_python() or Path(sys.executable)
    env = {**os.environ, "HF_HUB_OFFLINE": "0", "METIS_RC_ROOT": str(ROOT)}
    _run([str(py), "-c", "from metis_mcp.embeddings import embed_query; embed_query('warmup')"],
         timeout=900, env=env)
    return "downloaded"


# ── your AI apps ────────────────────────────────────────────────────────────

def _app_check(eid: str):
    label, installed, entry_of = APPS[eid]

    def run():
        if not installed():
            return SKIP, f"{label} is not installed"
        e = entry_of()
        if not e:
            return PROBLEM, f"{label} is installed but does not have Metis"
        if not _runnable(e):
            return PROBLEM, f"it points at {e['command']}, which does not exist"
        return PASS, ""
    return run


def _app_fix(eid: str):
    def run():
        entry = canonical_entry()
        if entry is None:
            return "no working Metis to connect it to"
        if eid == "app_claude_code":
            claude = shutil.which("claude")
            if not claude:
                return "the claude command is not on this computer's path"
            _run([claude, "mcp", "remove", "--scope", "user", "metis-rc"], timeout=60)
            envs = [x for k, v in (entry.get("env") or {}).items() for x in ("-e", f"{k}={v}")]
            ok = _run([claude, "mcp", "add", "--scope", "user", *envs, "metis-rc", "--",
                       entry["command"], *(entry.get("args") or [])], timeout=60).returncode == 0
            return "connected" if ok else "Claude Code did not accept the connection"
        if eid == "app_claude_desktop" and IS_WSL and not os.environ.get("METIS_CLAUDE_DESKTOP_DIR"):
            # Desktop is on the Windows side and must start Metis through wsl.exe;
            # setup-mcp.sh writes that form, a Linux command here would break it.
            return "on this computer it is connected by system/mcp-server/setup-mcp.sh"
        client = {"app_claude_desktop": "claude-desktop", "app_vscode": "vscode", "app_cursor": "cursor"}[eid]
        if not apps.write_entry(client, entry):
            return "its settings file is not valid JSON, so it was left untouched"
        return f"connected — restart {APPS[eid][0]} to see Metis"
    return run


for _eid in APPS:
    CHECKS[_eid] = _app_check(_eid)
    FIXES[_eid] = _app_fix(_eid)


@check("any_app")
def _any_app():
    regs = [label for label, e in registered() if _runnable(e)]
    if regs:
        return PASS, ", ".join(regs)
    return PROBLEM, "no AI app on this computer has Metis"


@check("server_starts")
def _server_starts():
    regs = [(label, e) for label, e in registered() if _runnable(e)]
    if not regs:
        return SKIP, "no app has Metis to start"
    groups: dict[tuple, list[str]] = {}
    entries: dict[tuple, dict] = {}
    for label, e in regs:
        key = (e["command"], tuple(e.get("args") or []))
        groups.setdefault(key, []).append(label)
        entries[key] = e
    slow, failed, details = [], [], []
    for key, labels in groups.items():
        res = probe(entries[key])
        if isinstance(res, Exception):
            failed.append(f"{' and '.join(labels)} ({type(res).__name__})")
            continue
        started, n = res
        details.append(f"{started:.0f}s, {n} tools ({', '.join(labels)})")
        if started >= SLOW_START_S:
            slow.append(f"{' and '.join(labels)} took {started:.0f}s")
    if failed:
        return PROBLEM, "it did not answer for " + "; ".join(failed)
    if slow:
        return WARN, "; ".join(slow) + " — an app may give up on a slow start; try again after a restart"
    return PASS, "answered in " + "; ".join(details)


repair("server_starts")(_fix_tools)


# ── the dashboard ───────────────────────────────────────────────────────────

@check("dashboard_running")
def _dashboard_running():
    return (PASS, dashboard_url()) if http_status(dashboard_url() + "/health", 3) == 200 \
        else (PROBLEM, "it is not running")


@repair("dashboard_running")
def _fix_dashboard_running():
    if SANDBOX:
        return "not attempted (test run)"
    if SYSTEM == "windows":
        vbs = ROOT / "system" / "install" / "windows" / "launch-dashboard-silent.vbs"
        subprocess.Popen(["wscript.exe", str(vbs), "/background"], close_fds=True)
    else:
        with open(os.devnull, "wb") as dn:
            subprocess.Popen(["bash", str(ROOT / "system" / "app-py" / "run.sh")], cwd=ROOT / "system" / "app-py",
                             stdin=dn, stdout=dn, stderr=dn, start_new_session=True)
    for _ in range(45):
        if http_status(dashboard_url() + "/health", 3) == 200:
            return "started"
        time.sleep(2)
    return "started, but it did not answer within 90 seconds"


@check("dashboard_pages")
def _dashboard_pages():
    base = dashboard_url()
    if http_status(base + "/health", 3) != 200:
        return SKIP, "the dashboard is not running"
    broken = [p for p in ("/", "/api/scheduler/status") if http_status(base + p, 60) != 200]
    return (PROBLEM, "these do not open: " + ", ".join(broken)) if broken else (PASS, "")


@check("background_scans")
def _background_scans():
    try:
        con = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True, timeout=10)
        row = con.execute("SELECT created_at, status, details FROM jobs_log WHERE job_type='morning_scan' "
                          "ORDER BY created_at DESC LIMIT 1").fetchone()
        con.close()
    except sqlite3.Error:
        row = None
    if not row:
        return SKIP, "no scan has run yet — normal on a new install; the first runs soon after the dashboard starts"
    when, status, details = row
    try:
        age_h = (datetime.datetime.now() - datetime.datetime.fromisoformat(str(when)[:19])).total_seconds() / 3600
    except ValueError:
        return SKIP, f"the last scan's time could not be read ({when})"
    if status == "error":
        return PROBLEM, f"the last scan failed: {str(details)[:160]}"
    if age_h > 36:
        return PROBLEM, f"the last scan was {age_h / 24:.0f} day(s) ago"
    return PASS, f"last scan {age_h:.0f} hour(s) ago"


@repair("background_scans")
def _fix_scans():
    # Started, the dashboard catches up on a scan more than four hours old.
    if http_status(dashboard_url() + "/health", 3) == 200:
        return "the dashboard is running; the next scan is on its schedule"
    return _fix_dashboard_running() + " — it catches up on the scan within minutes"


# ── background tasks ────────────────────────────────────────────────────────

def _windows_task(name: str) -> tuple[str, str]:
    r = _run(["schtasks", "/Query", "/TN", name, "/XML"], timeout=30)
    if r.returncode != 0:
        return PROBLEM, "it is not scheduled"
    if re.search(r"<DisallowStartIfOnBatteries>\s*true", r.stdout, re.I):
        return PROBLEM, "it is scheduled but would never run on battery"
    return PASS, ""


def _register_tasks(only: str) -> str:
    if SANDBOX:
        return "not attempted (test run)"
    ps1 = ROOT / "system" / "install" / "windows" / "register-tasks.ps1"
    r = _run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
              "-InstallDir", str(ROOT), "-Only", only], timeout=120)
    return "scheduled" if r.returncode == 0 else "could not be scheduled: " + r.stdout.strip()[-160:]


@check("task_selfcheck")
def _task_selfcheck():
    if SYSTEM == "windows":
        return _windows_task("Metis self-check")
    if IS_WSL or Path("/.dockerenv").exists():
        return SKIP, "scheduled from Windows on this computer"
    if not shutil.which("crontab"):
        return PROBLEM, "this system has no cron to schedule it with"
    r = _run(["crontab", "-l"], timeout=30)
    return (PASS, "") if "metis_verify.py" in r.stdout else (PROBLEM, "it is not scheduled")


@repair("task_selfcheck")
def _fix_task_selfcheck():
    if SYSTEM == "windows":
        return _register_tasks("selfcheck")
    if SANDBOX:
        return "not attempted (test run)"
    py = venv_python() or Path(sys.executable)
    line = f"35 9 * * * METIS_RC_ROOT='{ROOT}' '{py}' '{Path(__file__).resolve()}' --fix --quiet"
    cur = [ln for ln in _run(["crontab", "-l"], timeout=30).stdout.splitlines() if "metis_verify.py" not in ln]
    p = subprocess.run(["crontab", "-"], input="\n".join(cur + [line]) + "\n", text=True, capture_output=True)
    return "scheduled" if p.returncode == 0 else "could not be scheduled"


@check("morning_briefing")
def _morning_briefing():
    import register_schedule as sched
    if SYSTEM != "windows":
        return SKIP, "Claude Desktop's scheduled tasks are set up from Windows"
    st = sched.status()
    if st == "off":
        return SKIP, "switched off in setup"
    if st == "registered":
        return PASS, ""
    return PROBLEM, "Claude Desktop has not got the task yet (it needs to be signed in once)"


@repair("morning_briefing")
def _fix_morning_briefing():
    import register_schedule as sched
    if SANDBOX:
        return "not attempted (test run)"
    st, _ = sched.register(ROOT)
    return "scheduled in Claude Desktop" if st == "registered" else "Claude Desktop is not signed in yet"


@check("task_dashboard")
def _task_dashboard():
    return _windows_task("Metis dashboard")


@repair("task_dashboard")
def _fix_task_dashboard():
    return _register_tasks("dashboard")


# ── your data ───────────────────────────────────────────────────────────────

def _schema_tables() -> set[str]:
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA.read_text(encoding="utf-8")))


@check("database")
def _database():
    db = db_path()
    if not db.exists():
        return PROBLEM, f"not found at {db}"
    try:
        con = sqlite3.connect(db, timeout=15)
        verdict = con.execute("PRAGMA quick_check").fetchone()[0]
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        con.close()
    except sqlite3.Error as exc:
        return FAIL, f"could not be opened: {exc}"
    if verdict != "ok":
        return FAIL, f"damaged: {verdict}"
    missing = _schema_tables() - have if SCHEMA.exists() else set()
    if missing:
        return WARN, f"{len(missing)} table(s) missing — some panels will be empty"
    return PASS, ""


@repair("database")
def _fix_database():
    # CREATE … IF NOT EXISTS only: adds what is absent, never touches what is there.
    if not SCHEMA.exists():
        return "the database definition is missing"
    db = db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db, timeout=15)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.close()
    return "missing parts created"


@check("specialists")
def _specialists():
    n = len(list((ROOT / "agents").glob("*/system-prompt.md")))
    return (PASS, f"{n} specialists") if n >= 10 else (PROBLEM, f"only {n} found in {ROOT / 'agents'}")


@check("profile")
def _profile():
    try:
        prefs = json.loads((ROOT / "system" / "config" / "user-preferences.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prefs = {}
    name = str(prefs.get("display_name") or "").strip()
    interests = prefs.get("library_interests") or prefs.get("interests") or []
    if name and interests:
        return PASS, name
    return PROBLEM, "your name or interests are missing — Metis will ask you for them"


@check("updates")
def _updates():
    try:
        sys.path.insert(0, str(_SRC))
        from metis_mcp import updates
        from metis_mcp.config import use_system_certificates
    except Exception:
        return SKIP, "the update check is not part of this copy"
    current = updates.installed_version(ROOT)
    if not current:
        return SKIP, "not installed by the setup program; updated the way it was installed"
    if SANDBOX or os.environ.get("METIS_VERIFY_NO_UPDATE_CHECK") == "1":
        return SKIP, "not checked in a test run"
    use_system_certificates()
    latest = updates.latest_release()
    if latest is None:
        return SKIP, "GitHub could not be reached"
    if updates.is_newer(latest["version"], current):
        return PROBLEM, f"Metis {latest['version']} is available (this is {current})"
    return PASS, f"version {current}"


# ═════════════════════════════ running the list ═════════════════════════════

def load_essentials() -> dict:
    return json.loads(ESSENTIALS.read_text(encoding="utf-8"))


def run(fix: bool) -> list[dict]:
    spec = load_essentials()
    groups = spec["groups"]
    results: list[dict] = []
    shown_group = None
    for ess in spec["essentials"]:
        if SYSTEM not in ess.get("platforms", ["windows", "linux", "darwin"]):
            continue  # does not exist on this system — not a row at all
        eid, severity = ess["id"], ess["severity"]

        def judge() -> tuple[str, str]:
            if ess.get("needs") == "dashboard" and not has_dashboard():
                return SKIP, "the dashboard is not installed (AI-only setup)"
            try:
                status, detail = CHECKS[eid]()
            except Exception as exc:  # noqa: BLE001 — one broken check must not hide the others
                # FAIL, not WARN: a check that did not run proved nothing, and as a
                # warning it let the installer report "works" while nothing was checked.
                return FAIL, f"the check itself could not run: {type(exc).__name__}: {exc}"
            return (severity if status == PROBLEM else status), detail

        status, detail = judge()
        note = ""
        if fix and status in (WARN, FAIL) and ess["repair"] == "auto" and eid in FIXES:
            try:
                note = FIXES[eid]()
            except Exception as exc:  # noqa: BLE001
                note = f"the repair failed: {type(exc).__name__}: {exc}"
            forget()
            status, detail = judge()
        row = {"id": eid, "group": ess["group"], "area": groups[ess["group"]], "name": ess["name"],
               "status": status, "detail": " ".join(str(detail).split())[:300],
               "fix": ess["how"] if status in (WARN, FAIL) else "",
               "repair": ess["repair"], "repaired": bool(note) and status == PASS,
               "repair_note": note}
        results.append(row)
        if not QUIET:
            if ess["group"] != shown_group:
                shown_group = ess["group"]
                print(f"\n  {groups[shown_group]}")
            mark = {PASS: "✓", WARN: "!", FAIL: "✗", SKIP: "–"}[status]
            extra = detail if status != PASS else ""
            if note:
                extra = (extra + " · " if extra else "") + f"repair: {note}"
            print(f"    {mark} {ess['name']}" + (f" — {extra}" if extra else ""))
            if status in (WARN, FAIL):
                print(f"        what to do: {ess['how']}")
    return results


def write_report(results: list[dict], started: float) -> int:
    fails = [r for r in results if r["status"] == FAIL]
    warns = [r for r in results if r["status"] == WARN]
    checked = [r for r in results if r["status"] != SKIP]
    overall = "NOT READY" if fails else ("READY WITH WARNINGS" if warns else "READY")
    data = {"overall": overall,
            "run_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "seconds": round(time.monotonic() - started, 1), "source": "metis_verify",
            "counts": {"pass": len(checked) - len(fails) - len(warns), "warn": len(warns),
                       "fail": len(fails), "skip": len(results) - len(checked),
                       "repaired": sum(1 for r in results if r["repaired"])},
            "checks": results}
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = RESULT_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, RESULT_JSON)
    if not QUIET:
        c = data["counts"]
        print(f"\n  {overall} — {c['pass']} of {len(checked)} checks pass"
              + (f", {c['repaired']} repaired" if c["repaired"] else "")
              + (f" ({c['skip']} do not apply here)" if c["skip"] else ""))
        for r in fails + warns:
            print(f"    • {r['name']}: {r['fix']}")
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
        print("Checking Metis on this computer" + (" and repairing what it can" if args.fix else "") + "…")
    sys.path.insert(0, str(_SRC))
    return write_report(run(args.fix), started)


if __name__ == "__main__":
    raise SystemExit(main())
