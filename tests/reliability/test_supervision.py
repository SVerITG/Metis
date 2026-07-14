"""Regression tests for the supervision layer.

WHY THIS FILE EXISTS
    On 2026-07-14 the dashboard was found to have been un-restartable for months.
    system/app-py/run.sh takes its singleton lock with `exec 9>lock; flock -n 9`,
    then spawned long-lived children (the node course server; a watchdog subshell)
    WITHOUT closing fd 9. Children inherit file descriptors, and an flock is only
    released when EVERY fd on that open file description is closed. So a process
    that served nothing held the launch lock for its entire life, every later
    launch failed `flock -n`, printed "another launch in progress", and exit 1.
    No code path could recover. Reboots masked it; the wedge silently re-formed.

    There were ZERO tests on the reliability layer, which is why it lived so long.
    Each test below maps to a specific way that outage happened.

RUNNING
    Fast, safe checks (no restart, run anywhere):
        pytest tests/reliability -m "not destructive"

    The full suite kills and restarts the real dashboard, so it is opt-in:
        METIS_RELIABILITY_DESTRUCTIVE=1 pytest tests/reliability -v

    Either way the session fixture leaves you with a serving dashboard.
"""

from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
import time

import pytest

from .conftest import (
    APP_DIR,
    BOOT_SH,
    COLD_START_TIMEOUT,
    LOCK,
    REPO,
    RUN_SH,
    WEDGE_RECOVERY_TIMEOUT,
    course_server_pids,
    destructive,
    health_code,
    is_healthy,
    kill_stack,
    lock_holders,
    port_pids,
    run_boot,
    wait_for_down,
    wait_for_health,
)

# ══════════════════════════════════════════════════════════════════════════════
# Source guards — no restart needed. These are the cheapest possible net: they
# assert the load-bearing lines are still THERE. Every one of them was a real
# outage, and every one is a single character away from being "cleaned up".
# ══════════════════════════════════════════════════════════════════════════════


def test_run_sh_closes_the_lock_fd_in_the_course_server():
    """`9>&-` on the node spawn. Without it, node holds the launch lock for life."""
    src = RUN_SH.read_text()
    spawn = re.search(r"nohup .*server\.js.*", src)
    assert spawn, "could not find the course-server spawn in run.sh"
    assert "9>&-" in spawn.group(0), (
        "The course server is spawned WITHOUT `9>&-`, so it inherits run.sh's "
        "launch-lock fd and will hold the lock forever. This is the exact bug "
        "that made the dashboard un-restartable for months.\n"
        f"  found: {spawn.group(0)}"
    )


def test_run_sh_closes_the_lock_fd_in_the_watchdog():
    """`) 9>&- &` on the watchdog subshell — the second, subtler instance."""
    src = RUN_SH.read_text()
    assert ") 9>&- &" in src, (
        "The course-server watchdog subshell is backgrounded without `9>&-`. It "
        "(and its `sleep`) inherit the launch lock and hold it while serving nothing."
    )


def test_run_sh_retries_the_lock_instead_of_giving_up():
    """The loser path must RETRY flock and take over a stale holder — never exit 1.

    Originally it polled only for health and then `exit 1`. That is what made the
    wedge permanent: nothing in the system could ever reclaim the lock.
    """
    src = RUN_SH.read_text()
    assert "flock -n 9" in src, "run.sh no longer takes the launch lock at all"
    assert "got_lock" in src, (
        "run.sh's flock-loser path no longer retries the lock. A transient holder "
        "(a dying supervisor, a `sleep`) will again cost a full timeout, and a "
        "stale holder will again wedge the dashboard permanently."
    )
    assert "taking over" in src, "the stale-lock takeover path is gone"


def test_metis_boot_closes_the_lock_fd_in_its_child():
    """metis-boot.sh must not leak ITS lock fd (8) into the long-lived run.sh."""
    src = (REPO / "tools" / "metis-boot.sh").read_text()
    assert "8>&-" in src, (
        "metis-boot.sh spawns run.sh without `8>&-`, so run.sh inherits the boot "
        "lock and holds it for life — permanently blocking every future heartbeat. "
        "Same fd-inheritance class as the original outage."
    )


def test_health_endpoint_actually_touches_the_database():
    """/health is the SOLE definition of health for the whole supervision chain.

    It used to return {"status": "ok"} unconditionally without reading the DB, so a
    corrupt database served a dashboard of zeros while every supervisor reported
    "nothing to do".
    """
    src = (APP_DIR / "main.py").read_text()
    start = src.index("async def health(")
    # Slice to the NEXT top-level def, not a fixed char count — the body is long
    # (it carries the why-comment) and a fixed window silently truncated it.
    nxt = src.find("\n@app.", start)
    health = src[start : nxt if nxt > start else len(src)]
    assert "sqlite3" in health and "sqlite_master" in health, (
        "/health no longer queries the database — a corrupt DB would again be "
        "invisible to run.sh and to the 5-minute heartbeat."
    )
    assert "503" in health, "/health no longer reports unhealthy on a DB failure"
    # It must NOT use the helpers that swallow OperationalError.
    assert "db_query(" not in health and "db_scalar(" not in health, (
        "/health uses db_query/db_scalar, which catch OperationalError (including "
        "'disk image is malformed') and return a default — reporting a corrupt "
        "database as perfectly healthy."
    )


def test_reinstall_script_fails_loudly_on_a_broken_install():
    """`exit 1` inside a `| while` exits only the subshell.

    reinstall-mcp.sh printed "✗ ModuleNotFoundError" and then "Reinstall complete."
    with status 0, and metis-preflight.sh gated on that exit code.
    """
    src = (REPO / "tools" / "reinstall-mcp.sh").read_text()
    assert "grep -q '^IMPORTFAIL'" in src, (
        "reinstall-mcp.sh no longer checks the import failure OUTSIDE a pipeline — "
        "it will again report success over a broken install."
    )


def test_daily_jobs_have_an_already_ran_today_guard():
    """Without it, every restart re-fires every daily job — including a paid API call."""
    src = (APP_DIR / "scheduler.py").read_text()
    assert "_ran_today" in src, (
        "scheduler.py lost the _ran_today() guard. Every dashboard restart will "
        "again re-run morning_scan, memory_consolidation (duplicate memory rows) "
        "and brief_synthesis (a BILLABLE Claude API call). Observed 7-8× per morning."
    )
    # Assert on CODE, not on prose: the why-comment legitimately contains the
    # string timezone="UTC" while explaining the bug.
    code = "\n".join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert 'AsyncIOScheduler(timezone="UTC")' not in code, (
        "the scheduler is back on UTC while the catch-up logic compares local time — "
        "the 09:00 brief will fire at 11:00 Brussels."
    )
    assert "_LOCAL_TZ" in code, "the scheduler no longer resolves the local timezone"


# ══════════════════════════════════════════════════════════════════════════════
# Live state — needs a running dashboard, but changes nothing.
# ══════════════════════════════════════════════════════════════════════════════


def test_dashboard_is_serving(running_dashboard):
    assert health_code() == 200


def test_the_course_server_does_not_hold_the_launch_lock(running_dashboard):
    """THE regression test for the outage.

    The node course server is long-lived and serves the dashboard nothing. If it
    holds even one fd on the launch lock, the dashboard is one crash away from
    being permanently un-restartable.
    """
    holders = {p.pid for p in lock_holders()}
    node = course_server_pids()
    assert node, "the course server is not running — cannot prove it isn't leaking"
    leaked = holders & node
    assert not leaked, (
        f"THE LOCK IS LEAKED. Course-server PID(s) {sorted(leaked)} hold an fd on "
        f"{LOCK.name}. Once the dashboard dies, nothing will ever be able to "
        "reclaim the lock and it will never restart. Check `9>&-` in run.sh."
    )


def test_every_lock_holder_is_actually_serving(running_dashboard):
    """Generalises the above: nothing that serves nothing may hold the lock.

    A legitimate holder is the supervisor (bash run.sh) or uvicorn. Anything else —
    a stray `sleep`, a watchdog subshell, a node process — is a future outage.
    """
    holders = lock_holders()
    assert holders, "nobody holds the launch lock — the singleton is not working"
    serving = port_pids()
    illegitimate = [
        p for p in holders
        if p.pid not in serving
        and "run.sh" not in p.cmdline
        and p.comm not in ("bash", "python3")
    ]
    assert not illegitimate, (
        "Non-serving processes hold the launch lock:\n"
        + "\n".join(f"  pid={p.pid} comm={p.comm} cmd={p.cmdline[:70]}" for p in illegitimate)
    )


def test_memory_embeddings_are_reconciled():
    """Cross-pollination silently degraded to a keyword LIKE at 1.8% coverage.

    episodic_memory has many writers; only remember() embeds. The nightly
    `embedding_backfill` job reconciles the gap — if coverage collapses again, the
    flagship feature is quietly broken and nothing else will tell us.
    """
    sys.path.insert(0, str(REPO / "system" / "mcp-server" / "src"))
    from metis_mcp.config import paths  # noqa: PLC0415

    con = sqlite3.connect(f"file:{paths.db}?mode=ro", uri=True)
    try:
        total = con.execute("SELECT count(*) FROM episodic_memory").fetchone()[0]
        embedded = con.execute("SELECT count(*) FROM vec_episodic_rowids").fetchone()[0]
    finally:
        con.close()
    if not total:
        pytest.skip("no episodic memory yet")
    coverage = embedded / total
    assert coverage >= 0.95, (
        f"episodic memory is only {coverage:.1%} embedded ({embedded}/{total}). "
        "Semantic recall — the whole point of cross-pollination — is degrading to "
        "keyword search. Run: tools/backfill-embeddings.py"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Destructive — these actually kill the dashboard. Opt in with
# METIS_RELIABILITY_DESTRUCTIVE=1. The fixtures restore a healthy dashboard.
# ══════════════════════════════════════════════════════════════════════════════


@destructive
def test_dashboard_recovers_when_killed(running_dashboard):
    """The heartbeat must resurrect a dead dashboard with no human involved."""
    kill_stack()
    assert wait_for_down(), "the dashboard did not actually go down"

    run_boot()
    assert wait_for_health(COLD_START_TIMEOUT), (
        "the dashboard did NOT come back. This is the outage: something is holding "
        "the launch lock while serving nothing."
    )


@destructive
def test_dashboard_recovers_while_the_course_server_survives(running_dashboard):
    """The EXACT shape of the original bug.

    Kill the dashboard but leave the node course server alive. Before the fix, node
    held the launch lock, so this state was terminal — the dashboard could never
    return.
    """
    node_before = course_server_pids()
    assert node_before, "course server not running — this test proves nothing"

    kill_stack()  # deliberately does not touch node
    assert wait_for_down()
    assert course_server_pids(), "the course server died — test setup is wrong"

    run_boot()
    assert wait_for_health(COLD_START_TIMEOUT), (
        "The dashboard could not restart while the course server was alive. That is "
        "precisely the fd-9 lock leak, and it means the dashboard is permanently "
        "wedged until node is killed."
    )


@destructive
def test_recovery_from_a_wedged_lock(running_dashboard):
    """A stale holder must not be able to wedge the dashboard forever.

    Simulate the worst case: a process holds the launch lock open while nothing
    serves. run.sh must retry, then take the lock over via a fresh inode.
    """
    kill_stack()
    assert wait_for_down()

    # A squatter holding the lock fd open, serving nothing — the wedge.
    squatter = subprocess.Popen(
        ["bash", "-c", f'exec 9>"{LOCK}"; flock -n 9; sleep 400'],
    )
    try:
        time.sleep(2)
        run_boot(timeout=WEDGE_RECOVERY_TIMEOUT + 60)
        assert wait_for_health(WEDGE_RECOVERY_TIMEOUT), (
            "A stale lock holder permanently wedged the dashboard. run.sh's "
            "takeover path is not working — this is the un-restartable state."
        )
    finally:
        squatter.kill()
        squatter.wait(timeout=10)


@destructive
def test_restart_does_not_refire_todays_jobs(running_dashboard):
    """A restart must not re-run daily jobs — one of them is a BILLABLE API call.

    Before the _ran_today() guard, every restart after the scheduled time re-ran
    every daily job: 7-8 runs of brief_synthesis and memory_consolidation in a
    single morning, once a 5-minute heartbeat started restarting the dashboard.
    """
    sys.path.insert(0, str(REPO / "system" / "mcp-server" / "src"))
    from metis_mcp.config import paths  # noqa: PLC0415

    def runs_today() -> int:
        con = sqlite3.connect(f"file:{paths.db}?mode=ro", uri=True)
        try:
            return con.execute(
                "SELECT count(*) FROM jobs_log "
                "WHERE date(created_at) = date('now', 'localtime')"
            ).fetchone()[0]
        finally:
            con.close()

    before = runs_today()

    kill_stack()
    assert wait_for_down()
    run_boot()
    assert wait_for_health(COLD_START_TIMEOUT)

    time.sleep(30)  # give any catch-up thread time to fire
    after = runs_today()

    assert after == before, (
        f"A restart re-fired {after - before} job(s). Daily jobs are running again "
        "on every restart — that means duplicate memory rows and repeated BILLABLE "
        "brief_synthesis calls. The _ran_today() guard is not working."
    )
