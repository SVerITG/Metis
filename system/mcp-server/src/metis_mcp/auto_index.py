"""Index a knowledge layer as soon as documents land in it (Keystone M6, automatic half).

WHY THIS EXISTS
    The blocking half of M6 shipped earlier: a layer can now point at a folder outside
    knowledge/library, which is what made 211 sleeping-sickness papers searchable. But a
    document added after that still waited for someone to press Rebuild, or for the
    nightly job. "I added the paper and Metis cannot find it" is indistinguishable from
    "Metis is broken", and the researcher has no way to tell which.

    So every path that PUTS a PDF into a layer's folder ends by calling schedule_index().

SINGLE FLIGHT
    Indexing is minutes of embedding work. Two runs over the same layer race: measured
    on 2026-08-14, a second pass started while the first was live and both wrote to the
    same rows. A lock file per layer means the second call is a no-op that says so,
    rather than a duplicate that corrupts a count.

    The lock records the PID. A stale lock (process gone) is cleared rather than
    honoured, because a lock that outlives its holder turns a transient crash into a
    permanent refusal to index — the failure mode this whole audit keeps finding.

DETACHED
    Fire-and-forget subprocess, start_new_session=True. The caller is an MCP tool
    answering a researcher; it must not block for twenty minutes, and the indexer must
    not die when that call returns.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def _lock_path(slug: str) -> Path:
    d = Path(os.path.expanduser("~/.local/share/metis/locks"))
    d.mkdir(parents=True, exist_ok=True)
    return d / f"index-{slug}.pid"


def _live(pid: int) -> bool:
    try:
        os.kill(pid, 0)          # signal 0 = existence check, no signal delivered
        return True
    except (OSError, ProcessLookupError):
        return False


def index_running(slug: str) -> bool:
    """True if an indexer for this layer is alive. Clears a stale lock as a side effect."""
    lock = _lock_path(slug)
    try:
        pid = int(lock.read_text().strip())
    except Exception:
        return False
    if _live(pid):
        return True
    lock.unlink(missing_ok=True)
    return False


def schedule_index(slug: str, reason: str = "") -> str:
    """Start a detached index of `slug` unless one is already running.

    Returns a short human-readable status — callers append it to their own reply, so
    the researcher learns that indexing started without having to ask.
    """
    if index_running(slug):
        return f"indexing of '{slug}' is already running — the new files join that run"

    root = os.environ.get("METIS_RC_ROOT")
    if not root or not Path(root).is_dir():
        # Guessing a root here would index the wrong tree, or nothing, silently.
        log.warning("auto-index skipped for %s: METIS_RC_ROOT unset or missing", slug)
        return f"could not start indexing of '{slug}' — METIS_RC_ROOT is not set"

    try:
        proc = subprocess.Popen(
            [sys.executable, "-c",
             "import asyncio,os;"
             "from metis_mcp.tools.knowledge_db import build_pdf_knowledge_db as b;"
             "f=getattr(b,'fn',b);"
             f"asyncio.run(f(database={slug!r}))"],
            cwd=root,
            env={**os.environ, "METIS_RC_ROOT": root},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _lock_path(slug).write_text(str(proc.pid))
        log.info("auto-index started for %s (pid %s) %s", slug, proc.pid, reason)
        return f"indexing of '{slug}' started in the background"
    except Exception as exc:
        log.warning("auto-index failed to start for %s: %s", slug, exc)
        return f"could not start indexing of '{slug}': {exc}"
