"""ambient.py — memory write-backs on the always-hit path (Keystone M1).

THE PROBLEM (memory evaluation, 2026-08-12 — Keystone Appendix C.2)
    A live census of every memory layer found two memory systems: one alive, one
    dormant. Alive: everything written by DIRECT tool calls — `save_session_summary`
    (687 rows, today), `log_agent_run → _auto_extract_memory` (2,018 episodic rows),
    `write_reflexion` (36 rows, today). Dormant: everything written by the PIPELINE —
    `session_events` = 0 rows, ever, and the `sessions` registry frozen since May.

    The reason is not a bug in the pipeline. The pipeline is fine. It simply is not
    called: `run_metis`/`session_bootstrap` only run if the model *chooses* to call
    them, and in ordinary use it does not. Everything gated behind them is therefore
    empty — including the two features built the day before this module (live
    "who's working" and the Desktop learning loop), which were correct code sitting
    on a road with no traffic.

        The lifecycle was convention, not construction.

THE FIX — the same one the security guard already made
    `middleware.py` solved this exact shape of problem in July, for security:
    guards wired at individual call sites are "a front-door mat in a building with
    212 side doors," so it wrapped `FastMCP.call_tool`, the one function every tool
    call passes through. Its own conclusion applies verbatim here:

        "A control that depends on being remembered is not a control —
         it is a convention."

    Memory continuity is such a control. So it moves to the same chokepoint. This
    module holds that logic; the middleware calls it. Four things become structural:

    1. SESSION REGISTRY — the first tool call of a connection resumes or opens a
       session row, tagged with the client it came from. No bootstrap call needed.
    2. SESSION EVENTS — every tool call leaves a compact event. The lifecycle trace
       exists because calls happened, not because anyone logged them.
    3. SESSION-ID INJECTION — `log_agent_run`, `write_reflexion` and friends take a
       `session_id` the model almost never passes. We fill it in. This is what makes
       the direct-tool path (the one that WORKS) and the session registry (the one
       that DIDN'T) finally refer to the same session.
    4. AGENT LIVENESS — adopting a specialist means calling `get_agent_context`.
       That call now opens the 'running' row that live monitoring reads, so
       "who's working" is true without `run_metis` in the picture.

WHAT THIS DELIBERATELY DOES NOT DO
    It never authors content. A session summary and a reflexion are the model's
    words about what happened; middleware cannot invent them and must not fake
    them. It makes the *scaffolding* structural — identity, timing, liveness — so
    that when the model does write, the writing lands somewhere coherent.

NEVER BREAKS A TOOL CALL
    Every entry point is wrapped and swallows its own errors. Memory bookkeeping
    failing is an annoyance; a tool call failing because bookkeeping broke is an
    outage. Writes are best-effort by design.

Disable in an emergency: METIS_NO_AMBIENT_MEMORY=1
"""

from __future__ import annotations

import datetime
import logging
import os
import queue
import socket
import threading
import time
from typing import Any
from uuid import uuid4

log = logging.getLogger("metis.ambient")

# How long a session may be idle before the next tool call counts as a new one.
# Matches session_bootstrap's rule exactly — two writers of the same table must
# not disagree about what "the current session" means.
_IDLE_HOURS = 2

# Tools that accept a `session_id` the model realistically never supplies. Filling
# it in is what stitches the working direct-tool path onto the session registry.
_WANTS_SESSION_ID = {
    "log_agent_run",
    "write_reflexion",
    "save_session_summary",
    "save_session_event",
    "evaluate_against_layers",
}

# Tools that accept a `client` field for the Code-vs-Desktop split.
_WANTS_CLIENT = {"save_session_summary", "session_bootstrap"}

# Bookkeeping/plumbing calls. They are real calls, but recording them would bury
# the actual narrative of a session under tool-discovery chatter.
_NOT_WORTH_AN_EVENT = {
    "find_tools",
    "load_tool_group",
    "list_tool_groups",
    "get_user_profile",
    "discovery_status",
    "next_discovery_tip",
    "session_bootstrap",   # writes its own richer events
    "save_session_event",  # would double-record
}

# ── in-process state ─────────────────────────────────────────────────────────
_lock = threading.Lock()
_session_id: str | None = None
_session_touched: datetime.datetime | None = None
_learning_loop_started = False


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def enabled() -> bool:
    return os.environ.get("METIS_NO_AMBIENT_MEMORY") != "1"


def detect_client() -> str:
    """Which Claude client launched this server process.

    Determined by process environment, which is reliable because the two clients
    start the server in genuinely different ways (verified on this machine,
    2026-08-12):

      Claude Code    → launches the server as a direct child of `claude`, which
                       exports CLAUDECODE=1 and CLAUDE_CODE_SESSION_ID.
      Claude Desktop → launches it through the WSL Relay/SessionLeader chain,
                       where none of those variables exist.

    This is what finally gives the dashboard a truthful Code-vs-Desktop split;
    the `sessions` table has 5 rows and every one says 'code' because 'code' was
    the default argument nobody overrode.
    """
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_SESSION_ID"):
        return "code"
    if os.environ.get("METIS_CLIENT"):
        return os.environ["METIS_CLIENT"]
    return "chat"


def _external_session_id() -> str | None:
    """Claude Code's own session id, when we can see it.

    Reusing the harness's id instead of minting a UUID means a Metis session and
    the conversation it belongs to share one identifier — so a transcript and its
    memory rows can actually be lined up later. Appendix C.4 lists "session
    identity is messy: a mix of dates, empty strings and UUIDs" as an open gap;
    this is the half of it we can fix for free.
    """
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    return sid or None


def ensure_session() -> str:
    """Resume or open the current session; return its id. Cheap after the first call.

    Cached in-process so the common path costs no database work at all: only the
    first call of a connection, and any call after the idle window, touches SQLite.
    """
    global _session_id, _session_touched

    now = datetime.datetime.now(datetime.timezone.utc)
    with _lock:
        if (
            _session_id
            and _session_touched
            and (now - _session_touched) < datetime.timedelta(hours=_IDLE_HOURS)
        ):
            _session_touched = now
            return _session_id

    session_id = ""
    try:
        from metis_mcp.config import paths
        from metis_mcp.db import connect
        from metis_mcp.tools.pipeline import _ensure_pipeline_tables

        _ensure_pipeline_tables()
        client = detect_client()
        computer = socket.gethostname()
        cutoff = (now - datetime.timedelta(hours=_IDLE_HOURS)).isoformat()

        with connect(paths.db) as con:
            row = con.execute(
                """SELECT session_id FROM sessions
                   WHERE computer = ? AND last_active > ?
                   ORDER BY last_active DESC LIMIT 1""",
                (computer, cutoff),
            ).fetchone()
            if row:
                session_id = row["session_id"]
                con.execute(
                    "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                    (_now(), session_id),
                )
            else:
                session_id = _external_session_id() or str(uuid4())
                con.execute(
                    """INSERT OR IGNORE INTO sessions
                       (session_id, client, computer, started_at, last_active)
                       VALUES (?, ?, ?, ?, ?)""",
                    (session_id, client, computer, _now(), _now()),
                )
            con.commit()
    except Exception as exc:
        log.warning("ambient: could not open a session (%s) — continuing", exc)
        # A session id we cannot persist is still better than none: downstream
        # writes stay correlated with each other for the life of the process.
        session_id = session_id or _external_session_id() or str(uuid4())

    with _lock:
        _session_id = session_id
        _session_touched = now
    return session_id


# ── the event writer ─────────────────────────────────────────────────────────
# Breadcrumbs are written by a background thread, not by the tool call itself.
#
# Measured before this existed: +15.9 ms on EVERY tool call, because each call
# opened two SQLite connections (insert the event, then bump last_active) and
# each commit costs a WAL fsync. On a cheap tool that is a 10x slowdown, and the
# very cheapest tools are the ones called most. Nothing about a breadcrumb needs
# to be synchronous — no tool reads these rows to decide what to do — so the call
# now just drops the event on a queue and returns.
#
# A bounded queue and a daemon thread: if the writer ever falls behind, we drop
# breadcrumbs rather than grow memory without limit or stall the assistant.
# Losing a trace row is a cosmetic loss; stalling is not.
_events: "queue.Queue[tuple[str, str, str]]" = queue.Queue(maxsize=2000)
_writer_started = False


def _drain_events() -> None:
    """Write queued events in batches, one transaction per batch."""
    from metis_mcp.config import paths
    from metis_mcp.db import connect
    from metis_mcp.tools.pipeline import _SESSION_EVENTS_DDL

    while True:
        batch = [_events.get()]              # block until there is work
        while len(batch) < 50:               # opportunistically take more
            try:
                batch.append(_events.get_nowait())
            except queue.Empty:
                break
        try:
            with connect(paths.db) as con:
                con.execute(_SESSION_EVENTS_DDL)
                con.executemany(
                    """INSERT INTO session_events (session_id, event_type, content, created_at)
                       VALUES (?, ?, ?, ?)""",
                    [(sid, etype, content[:2000], _now()) for sid, etype, content in batch],
                )
                for sid in {b[0] for b in batch}:
                    con.execute(
                        "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                        (_now(), sid),
                    )
                con.commit()
        except Exception as exc:
            log.debug("ambient: dropped %d event(s) (%s)", len(batch), exc)
        finally:
            for _ in batch:
                _events.task_done()


def _start_writer_once() -> None:
    global _writer_started
    with _lock:
        if _writer_started:
            return
        _writer_started = True
    try:
        threading.Thread(target=_drain_events, name="metis-ambient-writer", daemon=True).start()
    except Exception:
        _writer_started = False


def _start_learning_loop_once() -> None:
    """Kick the throttled reflexion→improvement loop, off the request path.

    It used to hang off `session_bootstrap`, which (see the module docstring) is
    barely called — so the Desktop learning loop shipped and then never ran. It
    now hangs off the first tool call of the process instead.

    In a DAEMON THREAD deliberately: the loop aggregates reflexions, consolidates
    them and may call the Claude API to draft proposals. Inline, that is seconds
    of latency bolted onto whichever innocent tool call happened to be first.
    """
    global _learning_loop_started
    with _lock:
        if _learning_loop_started:
            return
        _learning_loop_started = True

    def _run() -> None:
        try:
            from metis_mcp.tools.pipeline import _maybe_run_learning_loop

            _maybe_run_learning_loop()  # self-throttling: at most once per ~20h
        except Exception as exc:
            log.debug("ambient: learning loop skipped (%s)", exc)

    try:
        threading.Thread(target=_run, name="metis-learning-loop", daemon=True).start()
    except Exception:
        pass


def inject_arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Fill in the session context the model cannot be expected to know.

    This is the hinge of M1. `log_agent_run(session_id=...)` already knows how to
    close out a 'running' agent row and write a result event — it just receives an
    empty string, every time, because nothing in a normal conversation tells the
    model what the session id is. So the parameter existed, the code behind it
    worked, and the feature was dead. Supplying the argument here revives it for
    every caller at once, including callers written next year.

    Only ever fills a MISSING or EMPTY value: an explicit argument always wins.
    """
    if not arguments:
        arguments = {}
    try:
        if name in _WANTS_SESSION_ID and not (arguments.get("session_id") or "").strip():
            arguments["session_id"] = ensure_session()
        if name in _WANTS_CLIENT and not (arguments.get("client") or "").strip():
            arguments["client"] = detect_client()
    except Exception as exc:
        log.debug("ambient: argument injection skipped for %s (%s)", name, exc)
    return arguments


def _summarise_args(arguments: dict[str, Any]) -> str:
    """A short, readable trace of what a call was about — never the whole payload.

    Values are truncated hard. An event row is a breadcrumb; the egress PII rail
    in middleware.py inspects tool OUTPUT, and this writes tool INPUT to disk, so
    keeping it small is a privacy measure as much as a storage one.
    """
    parts = []
    for key, value in list((arguments or {}).items())[:4]:
        if key in ("session_id", "client"):
            continue
        text = str(value)
        if len(text) > 80:
            text = text[:77] + "…"
        parts.append(f"{key}={text}")
    return ", ".join(parts)[:300]


def note_call(name: str, arguments: dict[str, Any], failed: bool = False) -> None:
    """Record that a tool ran. The lifecycle trace, written by construction.

    Returns as fast as a queue put — the actual write happens on the writer
    thread. See the note above _drain_events for why that matters.
    """
    if name in _NOT_WORTH_AN_EVENT:
        return
    try:
        session_id = ensure_session()
        _start_writer_once()
        _events.put_nowait((
            session_id,
            "tool_error" if failed else "tool",
            f"{name}({_summarise_args(arguments)})",
        ))
    except queue.Full:
        log.debug("ambient: event queue full — dropped a breadcrumb for %s", name)
    except Exception as exc:
        log.debug("ambient: could not record %s (%s)", name, exc)


def flush(timeout: float = 5.0) -> None:
    """Wait for queued events to reach the database. For tests and shutdown."""
    try:
        deadline = time.monotonic() + timeout
        while not _events.empty() and time.monotonic() < deadline:
            time.sleep(0.02)
        time.sleep(0.05)
    except Exception:
        pass


def mark_agent_running(agent_slug: str) -> None:
    """Open a 'running' agent row when a specialist is actually adopted.

    Live monitoring (Phase S.2) reads `agent_runs.status='running'`, and the only
    writer was `run_metis`'s dispatch — so the panel could only ever light up for
    the pipeline path nobody takes. `get_agent_context(agent_slug=...)` is the
    call that means "I am becoming this specialist now", on every path, so that is
    where liveness belongs.

    Idempotent: re-reading a specialist's context mid-task must not stack up
    duplicate running rows for the same agent in the same session.
    """
    slug = (agent_slug or "").strip()
    if not slug:
        return
    try:
        session_id = ensure_session()
        from metis_mcp.config import paths
        from metis_mcp.db import connect

        with connect(paths.db) as con:
            existing = con.execute(
                """SELECT 1 FROM agent_runs
                   WHERE session_id = ? AND agent_slug = ? AND status = 'running'
                   LIMIT 1""",
                (session_id, slug),
            ).fetchone()
            if existing:
                return
            con.execute(
                """INSERT INTO agent_runs
                   (agent_slug, task_summary, input_path, output_path, status,
                    created_at, input_tokens, output_tokens, model, session_id)
                   VALUES (?, ?, '', '', 'running', ?, 0, 0, ?, ?)""",
                (slug, "working…", _now(), "", session_id),
            )
            con.commit()
    except Exception as exc:
        log.debug("ambient: could not mark %s running (%s)", slug, exc)


def before_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Everything that must happen before a tool runs."""
    if not enabled():
        return arguments
    _start_learning_loop_once()
    arguments = inject_arguments(name, arguments)
    if name == "get_agent_context":
        mark_agent_running(str((arguments or {}).get("agent_slug") or ""))
    return arguments


def after_call(name: str, arguments: dict[str, Any], failed: bool = False) -> None:
    """Everything that must happen once a tool has run."""
    if not enabled():
        return
    note_call(name, arguments, failed=failed)
