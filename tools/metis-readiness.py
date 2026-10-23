#!/usr/bin/env python3
"""metis-readiness.py — is this computer ready to start work with Metis?

WHY THIS EXISTS
    Metis can fail in ways nothing announces: the MCP server runs an installed
    copy that a `git pull` leaves behind, the dashboard keeps serving code from
    before the last change, the embedding model goes missing and semantic search
    quietly returns nothing, a scheduler job starts failing every night. Each has
    its own check somewhere (metis_doctor, test-mcp.sh, the preflight report, the
    HTMX checker); this runs them together, the way Claude actually reaches Metis,
    and writes one verdict.

    It checks THIS machine, so it has to run on it — a cloud task sees the code,
    never the running dashboard, the installed venv or the model cache.

WHAT IT CHECKS
    code       the repo is current with the other computer; the installed MCP
               copy matches the source
    mcp        the server starts through the real launcher (run.sh) and answers
               the protocol; the load-bearing tools are registered
    doctor     every metis_doctor row (DB, embedding model, knowledge layer, …)
    database   SQLite integrity; free disk space beside it
    dashboard  serving; not running code older than the source; no route
               returns a server error; HTMX swap sites intact; no scheduler job
               whose last run failed

OUTPUT
    system/config/readiness.json          the verdict, read by the dashboard
                                          and the SessionStart hook
    outputs/readiness/<date>.md           the same, for a person

    Exit 0 = READY, 1 = READY WITH WARNINGS, 2 = NOT READY.

USAGE
    bash tools/metis-readiness.sh               # check and report
    bash tools/metis-readiness.sh --fix         # also start the dashboard if it
                                                # is down and reinstall a stale MCP
    bash tools/metis-readiness.sh --summary     # one line from the last run
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("METIS_RC_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

STATE_DIR = Path.home() / ".local" / "share" / "metis-mcp"
RUN_SH = STATE_DIR / "run.sh"
RESULT_JSON = ROOT / "system" / "config" / "readiness.json"
REPORT_DIR = ROOT / "outputs" / "readiness"

# The tools a session cannot work without. Same list as tools/test-mcp.sh.
LOAD_BEARING = ["session_bootstrap", "run_metis", "save_session_event",
                "get_agent_context", "log_agent_run", "write_reflexion",
                "save_session_summary", "recall", "remember"]

PASS, WARN, FAIL = "pass", "warn", "fail"
results: list[dict] = []

# Importing the server and loading the embedder log freely to stdout/stderr
# (fastembed through its own logger). The checks run with both pointed at
# /dev/null and the report goes to a saved copy of the real stdout.
_OUT = sys.stdout


def say(text: str) -> None:
    print(text, file=_OUT, flush=True)


def record(area: str, name: str, status: str, detail: str = "", fix: str = "") -> None:
    detail = " ".join(detail.split())
    results.append({"area": area, "name": name, "status": status,
                    "detail": detail, "fix": fix.strip()})
    mark = {"pass": "✓", "warn": "⚠", "fail": "✗"}[status]
    say(f"  {mark} [{area}] {name}" + (f" — {detail.strip()}" if detail else ""))


# ── code ──────────────────────────────────────────────────────────────────────

def check_code(fix: bool) -> None:
    # Fetch first so "behind" means behind the other computer today, not at the
    # last fetch. Read-only on the working tree; a dead network is only a warning.
    remote = "metis-ph"
    remotes = subprocess.run(["git", "-C", str(ROOT), "remote"],
                             capture_output=True, text=True).stdout.split()
    if remote in remotes:
        try:
            # No prompts: a scheduled run has nobody to type a passphrase.
            subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", remote],
                           capture_output=True, timeout=60,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                                "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"})
        except subprocess.TimeoutExpired:
            record("code", "fetch", WARN, f"git fetch {remote} timed out — 'behind' may be out of date")

    preflight = ROOT / "tools" / "metis-preflight.sh"
    if not preflight.exists():
        record("code", "sync report", WARN, "tools/metis-preflight.sh missing")
        return
    out = subprocess.run(["bash", str(preflight), "--report"], capture_output=True,
                         text=True, timeout=60).stdout
    lines = [ln.removeprefix("METIS SYNC: ") for ln in out.splitlines() if ln.startswith("METIS SYNC:")]
    stale = [ln for ln in lines if "STALE" in ln]
    if stale and fix:
        r = subprocess.run(["bash", str(ROOT / "tools" / "reinstall-mcp.sh")],
                           capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            record("code", "installed MCP copy", WARN,
                   "was stale — reinstalled from source",
                   "Reconnect in any open Claude session: /mcp → reconnect 'metis-rc'")
        else:
            record("code", "installed MCP copy", FAIL, "stale, and the reinstall failed: "
                   + (r.stderr or r.stdout)[-200:], "bash tools/reinstall-mcp.sh")
        lines = [ln for ln in lines if ln not in stale]
    elif stale:
        record("code", "installed MCP copy", WARN, "older than the source — new code is not loaded",
               "bash tools/reinstall-mcp.sh, then /mcp → reconnect 'metis-rc'")
        lines = [ln for ln in lines if ln not in stale]
    else:
        record("code", "installed MCP copy", PASS, "matches the source")
    for ln in lines:
        record("code", "sync", WARN, ln)
    if not lines:
        record("code", "sync", PASS, "in step with the other computer, nothing unpushed")


# ── mcp ───────────────────────────────────────────────────────────────────────

async def _probe_mcp() -> tuple[float, list[str], str]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    if RUN_SH.exists():
        params = StdioServerParameters(command="bash", args=[str(RUN_SH)], env=dict(os.environ))
    else:
        params = StdioServerParameters(command=sys.executable, args=["-m", "metis_mcp.server"],
                                       env=dict(os.environ))
    with open(os.devnull, "w") as devnull:
        async with stdio_client(params, errlog=devnull) as (r, w):
            async with ClientSession(r, w) as s:
                t = time.monotonic()
                await s.initialize()
                started = time.monotonic() - t
                names = [x.name for x in (await s.list_tools()).tools]
                reply = ""
                if "find_tools" in names:
                    res = await s.call_tool("find_tools", {"query": "doctor"})
                    reply = "error" if res.isError else "ok"
                return started, names, reply


def check_mcp() -> None:
    launcher = "run.sh" if RUN_SH.exists() else "python -m metis_mcp.server (no run.sh found)"
    try:
        started, names, reply = asyncio.run(asyncio.wait_for(_probe_mcp(), 180))
    except Exception as exc:
        record("mcp", "server starts", FAIL, f"via {launcher}: {type(exc).__name__}: {exc}"[:300],
               "bash tools/test-mcp.sh for detail; reinstall with bash tools/reinstall-mcp.sh")
        return
    record("mcp", "server starts", PASS if started < 30 else WARN,
           f"via {launcher}, handshake in {started:.1f}s, {len(names)} tools exposed")
    if reply == "error":
        record("mcp", "tool call", FAIL, "find_tools returned an error over the protocol")
    elif reply == "ok":
        record("mcp", "tool call", PASS, "a read-only call round-trips")

    # With tool search on, only core modules are exposed; a parked tool is still
    # reachable, so check registration in-process rather than in the listing.
    try:
        from metis_mcp.app_instance import app
        import metis_mcp.server as server  # noqa: F401 — registers every tool module
        from metis_mcp.tools import tool_search
        registered = set(app._tool_manager._tools) | set(tool_search._PARKED)
        missing = [t for t in LOAD_BEARING if t not in registered]
        failed = getattr(server, "FAILED_MODULES", {}) or {}
        if missing:
            record("mcp", "load-bearing tools", FAIL, "not registered: " + ", ".join(missing))
        else:
            record("mcp", "load-bearing tools", PASS, f"all {len(LOAD_BEARING)} registered")
        if failed:
            record("mcp", "tool modules", WARN, "degraded: " + ", ".join(failed))
    except Exception as exc:
        record("mcp", "load-bearing tools", WARN, f"could not import the server: {exc}"[:200])


# ── doctor ────────────────────────────────────────────────────────────────────

# Rows the other areas already cover better, or that are not about readiness.
_DOCTOR_SKIP = {"MCP install is current", "Claude Desktop link",
                # Claude Code and Desktop bring their own key; only direct API
                # scripts need this, so it would warn every single day.
                "Anthropic API key"}


def check_doctor() -> None:
    try:
        from metis_mcp.tools.doctor import run_doctor
        report = run_doctor()
    except Exception as exc:
        record("doctor", "metis_doctor", FAIL, f"could not run: {exc}"[:200])
        return
    for c in report.get("checks", []):
        if c.get("name") in _DOCTOR_SKIP or c.get("name", "").startswith("Dashboard"):
            continue
        status = PASS if c.get("ok") else (FAIL if c.get("severity") == "fail" else WARN)
        record("doctor", c.get("name", "?"), status,
               "" if status == PASS else str(c.get("detail", ""))[:240])


# ── database ──────────────────────────────────────────────────────────────────

def check_database() -> None:
    try:
        from metis_mcp.config import paths
        db = Path(paths.db)
    except Exception as exc:
        record("database", "location", FAIL, f"cannot resolve the database path: {exc}")
        return
    if not db.exists():
        record("database", "integrity", FAIL, f"no database at {db}",
               "python3 system/installer/init_db.py")
        return
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=15)
        verdict = con.execute("PRAGMA quick_check").fetchone()[0]
        con.close()
        record("database", "integrity", PASS if verdict == "ok" else FAIL,
               "quick_check ok" if verdict == "ok" else f"quick_check: {verdict}"[:240],
               "" if verdict == "ok" else "restore from the latest snapshot (tools/backup-canonical.py)")
    except Exception as exc:
        record("database", "integrity", WARN, f"could not open read-only: {exc}"[:200])
    free_gb = shutil.disk_usage(db.parent).free / 1e9
    record("database", "disk space", PASS if free_gb >= 2 else (WARN if free_gb >= 0.5 else FAIL),
           f"{free_gb:.1f} GB free beside the database")


# ── dashboard ─────────────────────────────────────────────────────────────────

def _healthy(base: str) -> bool:
    import httpx
    try:
        return httpx.get(f"{base}/health", timeout=5).status_code == 200
    except Exception:
        return False


def check_dashboard(port: str, fix: bool) -> None:
    import httpx
    base = f"http://127.0.0.1:{port}"
    if not _healthy(base) and fix:
        launcher = ROOT / "system" / "app-py" / "run-dashboard.sh"
        subprocess.Popen(["bash", str(launcher)], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                         start_new_session=True, env={**os.environ, "METIS_PORT": port})
        for _ in range(45):
            time.sleep(2)
            if _healthy(base):
                record("dashboard", "serving", WARN, f"was down — started it on :{port}")
                break
    if not _healthy(base):
        record("dashboard", "serving", FAIL, f"nothing answering on :{port}",
               "bash system/app-py/run-dashboard.sh (or the Metis desktop icon)")
        return
    if not any(r["area"] == "dashboard" and r["name"] == "serving" for r in results):
        record("dashboard", "serving", PASS, f"healthy on :{port}")

    # Dashboard code changes need a restart. startup_eval rewrites eval-results.json
    # on every boot, so its run_at is the boot time to compare the source with.
    try:
        boot = json.loads((ROOT / "system" / "config" / "eval-results.json").read_text())["run_at"]
        boot_ts = datetime.datetime.fromisoformat(boot.replace("Z", "+00:00")).timestamp()
        app_dir = ROOT / "system" / "app-py"
        newest = max((p for p in app_dir.rglob("*.py") if "__pycache__" not in p.parts),
                     key=lambda p: p.stat().st_mtime)
        if newest.stat().st_mtime > boot_ts + 5:
            record("dashboard", "running current code", WARN,
                   f"{newest.relative_to(ROOT)} changed after the dashboard started",
                   "bash tools/restart-dashboard.sh")
        else:
            record("dashboard", "running current code", PASS, f"started {boot[:16].replace('T', ' ')}")
    except Exception:
        record("dashboard", "running current code", WARN, "boot time unknown (no eval-results.json)")

    # Every parameter-free GET: a 5xx is a broken panel somebody will open.
    try:
        spec = httpx.get(f"{base}/openapi.json", timeout=20).json()
        gets = [p for p, v in spec.get("paths", {}).items() if "get" in v and "{" not in p
                and not any(s in p for s in ("stream", "sse", "events", "/ws", "download",
                                              "export", "backup", "shutdown", "restart", "/live"))]
        broken, slow = [], []
        with httpx.Client(base_url=base, timeout=30) as c:
            for p in gets:
                t = time.monotonic()
                try:
                    code = c.get(p).status_code
                except Exception as exc:
                    code = type(exc).__name__
                if not isinstance(code, int) or code >= 500:
                    broken.append(f"{p} ({code})")
                if time.monotonic() - t > 5:
                    slow.append(p)
        if broken:
            record("dashboard", "routes", FAIL, f"{len(broken)}/{len(gets)} fail: " + ", ".join(broken[:6]))
        else:
            record("dashboard", "routes", PASS if not slow else WARN,
                   f"{len(gets)} routes answer" + (f"; slow (>5s): {', '.join(slow[:4])}" if slow else ""))
    except Exception as exc:
        record("dashboard", "routes", WARN, f"could not crawl: {exc}"[:200])

    htmx = ROOT / "tools" / "check_htmx_swaps.py"
    if htmx.exists():
        r = subprocess.run([sys.executable, str(htmx), "--port", port],
                           capture_output=True, text=True, timeout=300)
        problems = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().startswith("✗")]
        record("dashboard", "HTMX swaps", PASS if r.returncode == 0 else WARN,
               "intact" if r.returncode == 0 else "; ".join(problems[:3])[:300])

    try:
        jobs = httpx.get(f"{base}/api/scheduler/status", timeout=15).json()
        failing = [j for j in jobs.get("jobs", [])
                   if str(j.get("last_status") or "").lower() in ("error", "failed", "fail")]
        if not jobs.get("running"):
            record("dashboard", "scheduler", FAIL, "the job scheduler is not running",
                   "restart the dashboard: bash tools/restart-dashboard.sh")
        elif failing:
            record("dashboard", "scheduler", WARN, "last run failed: " + ", ".join(
                f"{j.get('name') or j.get('id')} ({str(j.get('last_message') or '')[:60]})" for j in failing[:4]))
        else:
            record("dashboard", "scheduler", PASS, f"{len(jobs.get('jobs', []))} jobs, none failing")
    except Exception as exc:
        record("dashboard", "scheduler", WARN, f"status unavailable: {exc}"[:200])


# ── report ────────────────────────────────────────────────────────────────────

def write_report(started: float) -> int:
    fails = [r for r in results if r["status"] == FAIL]
    warns = [r for r in results if r["status"] == WARN]
    overall = "NOT READY" if fails else ("READY WITH WARNINGS" if warns else "READY")
    now = datetime.datetime.now().astimezone()
    data = {"overall": overall, "run_at": now.isoformat(timespec="seconds"),
            "seconds": round(time.monotonic() - started, 1),
            "counts": {"pass": len(results) - len(fails) - len(warns),
                       "warn": len(warns), "fail": len(fails)},
            "checks": results}
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    md = [f"# Metis readiness — {overall}", "",
          f"{now:%Y-%m-%d %H:%M} · {data['counts']['pass']} pass · "
          f"{len(warns)} warn · {len(fails)} fail · {data['seconds']}s", ""]
    for title, rows in (("Not ready", fails), ("Worth fixing", warns)):
        if rows:
            md += [f"## {title}", ""]
            md += [f"- **{r['area']} · {r['name']}** — {r['detail']}"
                   + (f"  \n  Fix: `{r['fix']}`" if r["fix"] else "") for r in rows]
            md.append("")
    md += ["## All checks", "", "| Area | Check | Result | Detail |", "|---|---|---|---|"]
    md += [f"| {r['area']} | {r['name']} | {r['status']} | {r['detail'].replace('|', '/')[:160]} |"
           for r in results]
    (REPORT_DIR / f"{now:%Y-%m-%d}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    say(f"\n  RESULT: {overall} — report: outputs/readiness/{now:%Y-%m-%d}.md")
    return 2 if fails else (1 if warns else 0)


def summary() -> int:
    """One line from the last run, for the SessionStart hook. Silent when all is well.

    If the last run is old (the computer was off at the scheduled time) and this
    machine has a Metis install, a fresh check starts in the background so the
    next session has a current verdict.
    """
    try:
        d = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
        age_h = (datetime.datetime.now().astimezone()
                 - datetime.datetime.fromisoformat(d["run_at"])).total_seconds() / 3600
    except Exception:
        d, age_h = None, float("inf")
    venv_py = STATE_DIR / ".venv" / "bin" / "python3"
    if age_h > 20 and venv_py.exists():
        with open(STATE_DIR / "readiness.log", "a") as log:
            subprocess.Popen([str(venv_py), str(Path(__file__).resolve()), "--fix"],
                             stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                             start_new_session=True)
        print("METIS READINESS: no check in the last 20h — running one in the background now.")
    if d is None:
        return 0
    if age_h > 36:
        print(f"METIS READINESS: last check was {age_h:.0f}h ago — the scheduled check may not be running.")
    if d.get("overall") != "READY":
        problems = [r for r in d.get("checks", []) if r["status"] == FAIL] or \
                   [r for r in d.get("checks", []) if r["status"] == WARN]
        print(f"METIS READINESS: {d['overall']} ({d['run_at'][:16].replace('T', ' ')}) — "
              + "; ".join(f"{r['area']}/{r['name']}: {r['detail'][:80]}" for r in problems[:3])
              + " — full report in outputs/readiness/.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fix", action="store_true",
                    help="start the dashboard if it is down; reinstall a stale MCP copy")
    ap.add_argument("--port", default=os.environ.get("METIS_PORT", "8080"))
    ap.add_argument("--summary", action="store_true", help="print one line from the last run")
    args = ap.parse_args()
    if args.summary:
        return summary()

    global _OUT
    started = time.monotonic()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # what the dashboard runs with
    say("Metis readiness check — " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    sys.stdout.flush()
    sys.stderr.flush()
    _OUT = os.fdopen(os.dup(1), "w")
    saved_err = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    try:
        for step in (lambda: check_code(args.fix), check_mcp, check_doctor, check_database,
                     lambda: check_dashboard(args.port, args.fix)):
            try:
                step()
            except Exception as exc:  # one broken check must not hide the others
                record("readiness", "internal", WARN,
                       f"a check crashed: {type(exc).__name__}: {exc}"[:200])
        return write_report(started)
    finally:
        sys.stdout.flush()
        os.dup2(_OUT.fileno(), 1)
        os.dup2(saved_err, 2)


if __name__ == "__main__":
    raise SystemExit(main())
