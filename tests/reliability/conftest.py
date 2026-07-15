"""Shared helpers for the reliability suite.

These tests run against the REAL system on this machine — the real launch lock,
the real supervisor, the real uvicorn, the real tools/metis-boot.sh. They do not
mock the failure; they cause it.

Why this suite exists
---------------------
The dashboard "crashed" for months. It never crashed — it DEADLOCKED. run.sh takes
a singleton lock with `exec 9>lock; flock -n 9`, then spawned long-lived children
(the node course server, the course watchdog subshell) WITHOUT closing fd 9.
Children inherit fds, and an flock is released only when EVERY fd on the open file
description is closed. So a process that was not serving anything held the launch
lock forever; every later launch failed `flock -n`, printed "another launch in
progress", and exited 1. Nothing could ever recover.

Not one line of that was under test. That is why it lived for months. Everything
here is a regression test for a failure that actually happened.

Destructive tests
-----------------
Two tests kill the dashboard. They are opt-in so a routine `pytest` run never takes
Stan's dashboard down mid-workday:

    METIS_RELIABILITY_DESTRUCTIVE=1 pytest tests/reliability -m reliability

Without the env var they SKIP (loudly). The non-destructive tests — including the
lock-leak regression test, which is the one that catches the original bug — always
run.

Every test leaves a healthy dashboard behind: the `running_dashboard` fixture
restores one via tools/metis-boot.sh (idempotent) before each test, and a
session-scoped finalizer restores one at the end.
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest

# ── Paths and constants ────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parents[2]
APP_DIR = REPO / "system" / "app-py"
LOCK = APP_DIR / ".metis-launch.lock"
BOOT_SH = REPO / "tools" / "metis-boot.sh"
RUN_SH = APP_DIR / "run.sh"

PORT = 8080
HEALTH_URL = f"http://127.0.0.1:{PORT}/health"

# A cold start loads a local embedding model — measured ~50s on this machine.
# Be generous: a slow OneDrive/DrvFs read can double it.
COLD_START_TIMEOUT = 240

# run.sh waits out a stale lock holder for 120s before taking the lock over via a
# fresh inode, and only THEN cold-starts. 120 + cold start + margin.
WEDGE_RECOVERY_TIMEOUT = 360

DESTRUCTIVE_ENABLED = os.environ.get("METIS_RELIABILITY_DESTRUCTIVE") == "1"

destructive = pytest.mark.skipif(
    not DESTRUCTIVE_ENABLED,
    reason=(
        "destructive: kills the running dashboard. "
        "Enable with METIS_RELIABILITY_DESTRUCTIVE=1"
    ),
)


# ── Health ─────────────────────────────────────────────────────────────────────

def health_code(timeout: float = 5) -> int | None:
    """HTTP status of /health, or None if nothing answered."""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code          # 503 is an answer — the server is up, the DB is not
    except Exception:
        return None              # nothing is listening


def is_healthy() -> bool:
    return health_code() == 200


def wait_for_health(timeout: float, poll: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_healthy():
            return True
        time.sleep(poll)
    return is_healthy()


def wait_for_down(timeout: float = 30, poll: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if health_code(timeout=2) is None:
            return True
        time.sleep(poll)
    return health_code(timeout=2) is None


def run_boot(timeout: float = 420) -> subprocess.CompletedProcess:
    """Run the real supervision entry point (Windows Task Scheduler calls this)."""
    return subprocess.run(
        ["bash", str(BOOT_SH)],
        capture_output=True, text=True, timeout=timeout,
    )


# ── Process inspection ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Proc:
    pid: int
    comm: str
    cmdline: str
    ppid: int

    def __str__(self) -> str:  # pragma: no cover — only used in failure messages
        return f"pid={self.pid} comm={self.comm} ppid={self.ppid} cmd={self.cmdline[:90]!r}"


def _read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return default


def proc_info(pid: int) -> Proc | None:
    base = Path("/proc") / str(pid)
    comm = _read(base / "comm").strip()
    if not comm:
        return None
    cmdline = _read(base / "cmdline").replace("\0", " ").strip()
    ppid = 0
    for line in _read(base / "status").splitlines():
        if line.startswith("PPid:"):
            ppid = int(line.split()[1])
            break
    return Proc(pid=pid, comm=comm, cmdline=cmdline, ppid=ppid)


def lock_holders() -> list[Proc]:
    """Every process holding an fd on the launch lock, found via /proc/<pid>/fd.

    Deliberately NOT fuser-only: fuser resolves the lock file's CURRENT inode, so a
    holder of a since-replaced inode (exactly what run.sh's stale-lock takeover
    creates) is invisible to it. Scanning /proc catches those too — they show up as
    "<path> (deleted)".
    """
    target = str(LOCK)
    holders: list[Proc] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fds = list((entry / "fd").iterdir())
        except OSError:
            continue  # process gone, or not ours
        for fd in fds:
            try:
                link = os.readlink(fd)
            except OSError:
                continue
            if link == target or link.startswith(target + " (deleted)"):
                info = proc_info(int(entry.name))
                if info:
                    holders.append(info)
                break
    return holders


def fuser_lock_pids() -> set[int]:
    """Cross-check of lock_holders() using fuser (current inode only)."""
    try:
        res = subprocess.run(
            ["fuser", str(LOCK)], capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {int(tok) for tok in res.stdout.split() if tok.isdigit()}


def port_pids(port: int = PORT) -> set[int]:
    """PIDs holding the dashboard's TCP port — i.e. the processes actually SERVING."""
    try:
        res = subprocess.run(
            ["fuser", f"{port}/tcp"], capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {int(tok) for tok in res.stdout.split() if tok.isdigit()}


def _pgrep(pattern: str) -> set[int]:
    try:
        res = subprocess.run(
            ["pgrep", "-f", pattern], capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {int(line) for line in res.stdout.split() if line.isdigit()}


def course_server_pids() -> set[int]:
    """The node statistics-course server — the process that held the lock for months."""
    return _pgrep(r"node.*server\.js")


def run_sh_pids() -> set[int]:
    """Every bash running run.sh: the supervisor AND its watchdog subshell.

    They are indistinguishable by cmdline — a subshell keeps its parent's argv — so
    they are told apart by parentage in supervisor_pids() below.
    """
    return {p for p in _pgrep(r"bash .*app-py/run\.sh") if proc_info(p)}


def supervisor_pids() -> set[int]:
    """The run.sh SUPERVISORS: a run.sh bash whose parent is not itself a run.sh bash.

    That excludes the course-watchdog subshell, which is a fork of the supervisor and
    therefore carries an identical cmdline.
    """
    all_run_sh = run_sh_pids()
    out = set()
    for pid in all_run_sh:
        info = proc_info(pid)
        if info and info.ppid not in all_run_sh:
            out.add(pid)
    return out


def kill_stack(sig: int = 9) -> None:
    """Kill the whole dashboard stack: supervisors, watchdog subshells, uvicorn.

    Deliberately leaves the node course server alone — it is a separate app, and one
    of the things we assert is that run.sh never had to kill it to recover.
    """
    victims = run_sh_pids() | port_pids()
    for pid in victims:
        try:
            os.kill(pid, sig)
        except OSError:
            pass
    time.sleep(1.5)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _ensure_healthy(what: str) -> None:
    if is_healthy():
        return
    # These live checks assert properties of a RUNNING deployment. In an
    # environment with no dashboard and no way to start one — CI runners, a fresh
    # checkout, any headless box — they are not applicable, so SKIP rather than
    # fail. (CI runs `pytest tests/ -m "not e2e"`; without this the whole
    # reliability module errored there while passing on a real machine.)
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS") or not BOOT_SH.exists():
        pytest.skip("no live dashboard here (CI / headless) — live reliability checks N/A")
    result = run_boot()
    if not wait_for_health(COLD_START_TIMEOUT):
        pytest.skip(
            f"could not bring the dashboard up {what} via {BOOT_SH} — "
            f"skipping live reliability check.\nboot stderr:\n{result.stderr[:500]}"
        )


@pytest.fixture()
def running_dashboard():
    """Guarantee a healthy dashboard before the test — and again after it.

    Restoring BEFORE each test (not only after) means one failed destructive test
    cannot cascade into the rest of the suite.
    """
    _ensure_healthy("before the test")
    yield
    _ensure_healthy("after the test")


@pytest.fixture(scope="session", autouse=True)
def _restore_dashboard_at_end():
    """Whatever these tests do, the machine ends with a serving dashboard."""
    yield
    # Only restore where there's a real deployment to restore — never try to boot
    # a dashboard in CI / a headless checkout.
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS") or not BOOT_SH.exists():
        return
    if not is_healthy():
        run_boot()
        wait_for_health(COLD_START_TIMEOUT)
