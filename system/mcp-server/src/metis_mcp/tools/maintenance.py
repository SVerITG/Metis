"""maintenance.py — the operations a Desktop user cannot reach without a shell.

WHY THIS EXISTS
    A researcher working entirely in Claude Desktop has no terminal. When the
    dashboard stops, when a scan needs running now rather than at 09:03, when the
    index has fallen behind — there is nothing they can do about it from inside
    the conversation, and the only advice available is "open WSL and type this",
    which is precisely the advice Metis exists to make unnecessary.

    Claude Code hides this because it has Bash. Desktop, Cursor and every other
    MCP client do not.

WHY A WHITELIST AND NOT A SHELL
    The obvious implementation is `run_command(cmd)`. That would be a remote code
    execution tool driven by a language model, on a machine holding patient-adjacent
    research data. No amount of prompt-level care makes that safe, and the
    project's own rules forbid it.

    So this exposes NAMED OPERATIONS. Each maps to one known function or script
    with no user-supplied arguments reaching a shell. The set is deliberately
    small and every member is idempotent and reversible: nothing here deletes
    data, and re-running any of them is harmless.

    The test applied to each candidate was: "if a model invoked this at the worst
    possible moment, what is the damage?" Anything whose answer was not "some
    wasted time" did not get added.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

log = logging.getLogger("metis")

_DASH = "http://127.0.0.1:8080"
_TIMEOUT = 600


def _dashboard_up(timeout: int = 3) -> bool:
    try:
        with urllib.request.urlopen(f"{_DASH}/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


# ── The whitelist ───────────────────────────────────────────────────────────
# name -> (human description, what it actually does)
OPERATIONS: dict[str, str] = {
    "status":           "Is the dashboard running, when did each job last run, how big is the corpus",
    "restart-dashboard": "Stop and restart the Metis dashboard (safe: it holds no unsaved state)",
    "scan-library":     "Search every literature source now — journals, Zotero, PubMed, OpenAlex",
    "scan-news":        "Refresh the news feeds and sync Zotero now",
    "pickup-downloads": "File any papers you downloaded through the browser",
    "rebuild-index":    "Index any PDFs added to a knowledge layer since its last build",
    "health-check":     "Run the Metis self-test and report what is broken",
}


def _run(script: list[str], timeout: int = _TIMEOUT) -> tuple[int, str]:
    """Run a KNOWN script. No user input reaches this."""
    try:
        p = subprocess.run(script, capture_output=True, text=True,
                           timeout=timeout, cwd=str(paths.root),
                           env={**os.environ, "METIS_RC_ROOT": str(paths.root)})
        out = (p.stdout or "") + (("\n" + p.stderr) if p.returncode else "")
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except Exception as exc:
        return 1, f"{type(exc).__name__}: {exc}"


@app.tool()
async def run_maintenance(operation: str = "status") -> list[TextContent]:
    """Run a safe Metis maintenance operation without needing a terminal.

    For researchers working in a chat client, where there is no shell. Every
    operation is idempotent, reversible and destroys nothing; there is no way to
    pass an arbitrary command.

    Args:
        operation: One of —
            status             what is running, what ran last, how big the corpus is
            restart-dashboard  restart the Metis dashboard
            scan-library       search every literature source now
            scan-news          refresh the news feeds now
            pickup-downloads   file papers downloaded through the browser
            rebuild-index      index PDFs added to a knowledge layer
            health-check       run the self-test

    Returns:
        What happened, in plain language.
    """
    op = (operation or "status").strip().lower()
    if op not in OPERATIONS:
        listing = "\n".join(f"  {k:<18} {v}" for k, v in OPERATIONS.items())
        return [TextContent(type="text", text=(
            f"'{operation}' is not an available operation.\n\n{listing}"
        ))]

    venv_py = str(Path.home() / ".local/share/metis-mcp/.venv/bin/python3")

    # ── status ──────────────────────────────────────────────────────────────
    if op == "status":
        import sqlite3
        up = _dashboard_up()
        lines = [f"Dashboard: {'running' if up else 'NOT running'} ({_DASH})"]
        try:
            c = sqlite3.connect(str(paths.db), timeout=5)
            c.row_factory = sqlite3.Row
            d = c.execute("SELECT COALESCE(SUM(doc_count),0) d, COALESCE(SUM(chunk_count),0) k "
                          "FROM knowledge_databases WHERE COALESCE(enabled,1)=1").fetchone()
            lines.append(f"Corpus: {d['d']} documents, {d['k']} passages indexed")
            lines.append(f"Catalogue: "
                         f"{c.execute('SELECT COUNT(*) FROM literature_metadata').fetchone()[0]} references")
            lines.append("")
            lines.append("Recent background jobs:")
            for r in c.execute(
                "SELECT job_type, status, substr(details,1,58) d, created_at "
                "FROM jobs_log ORDER BY rowid DESC LIMIT 8"
            ):
                lines.append(f"  {(r['created_at'] or '')[:16]}  {r['status']:<6} "
                             f"{r['job_type']:<18} {r['d']}")
            c.close()
        except Exception as exc:
            lines.append(f"(database unreadable: {type(exc).__name__})")
        if not up:
            lines += ["", "The dashboard is down. Semantic search and the Library "
                          "surface need it. Run: run_maintenance('restart-dashboard')"]
        return [TextContent(type="text", text="\n".join(lines))]

    # ── restart ─────────────────────────────────────────────────────────────
    if op == "restart-dashboard":
        # Stop by reading /proc rather than pkill: a pattern broad enough to catch
        # uvicorn is broad enough to catch the shell that ran it.
        killed = []
        try:
            import signal
            for d in Path("/proc").iterdir():
                if not d.name.isdigit():
                    continue
                try:
                    cmd = (d / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                        errors="ignore")
                except Exception:
                    continue
                if "uvicorn" in cmd and "main:app" in cmd:
                    try:
                        os.kill(int(d.name), signal.SIGTERM)
                        killed.append(d.name)
                    except ProcessLookupError:
                        pass
        except Exception:
            pass
        await asyncio.sleep(4)

        runner = paths.root / "system" / "app-py" / "run.sh"
        if not runner.exists():
            return [TextContent(type="text", text="run.sh not found; cannot restart.")]
        subprocess.Popen(["bash", str(runner)], cwd=str(paths.root),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True,
                         env={**os.environ, "METIS_RC_ROOT": str(paths.root)})
        for _ in range(45):
            await asyncio.sleep(1)
            if _dashboard_up():
                return [TextContent(type="text", text=(
                    f"Dashboard restarted and answering on {_DASH}"
                    + (f" (stopped {len(killed)} old process)" if killed else "")
                ))]
        return [TextContent(type="text", text=(
            "Restart issued but the dashboard did not answer within 45s. "
            "It may still be starting — check again with run_maintenance('status')."
        ))]

    # ── the scans ───────────────────────────────────────────────────────────
    if op in ("scan-library", "scan-news", "pickup-downloads"):
        if not _dashboard_up():
            return [TextContent(type="text", text=(
                "The dashboard is not running, and these operations run inside it.\n"
                "Start it first: run_maintenance('restart-dashboard')"
            ))]
        # VERIFIED against the running app, not assumed. `/api/news/scan` does
        # not exist — writing a tool against a guessed endpoint is how a
        # maintenance action becomes a 404 the user cannot diagnose. The real
        # news trigger is /api/scan/content, which also syncs Zotero.
        endpoint = {"scan-library": "/api/library/scan",
                    "scan-news": "/api/scan/content",
                    "pickup-downloads": "/api/library/pickup-downloads"}[op]
        try:
            req = urllib.request.Request(f"{_DASH}{endpoint}", method="POST")
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                import json as _j
                d = _j.loads(r.read())
            msg = d.get("message") or d.get("error")
            if not msg and d.get("steps"):
                msg = "\n".join(str(s) for s in d["steps"])
            return [TextContent(type="text", text=msg or "Done.")]
        except Exception as exc:
            return [TextContent(type="text",
                                text=f"{op} failed: {type(exc).__name__}: {exc}")]

    # ── index ───────────────────────────────────────────────────────────────
    if op == "rebuild-index":
        from metis_mcp.tools.knowledge_db import (
            build_pdf_knowledge_db, pending_pdf_count,
        )
        import sqlite3
        done, total = [], 0
        try:
            c = sqlite3.connect(str(paths.db), timeout=10)
            slugs = [r[0] for r in c.execute(
                "SELECT slug FROM knowledge_databases WHERE COALESCE(enabled,1)=1")]
            c.close()
        except Exception:
            slugs = []
        for slug in slugs:
            n = pending_pdf_count(slug)
            if not n:
                continue
            await build_pdf_knowledge_db(database=slug)
            done.append(f"{slug} (+{n})")
            total += n
        return [TextContent(type="text", text=(
            f"Indexed {total} new PDF(s): {', '.join(done)}" if done
            else "Every knowledge layer is already up to date."
        ))]

    # ── health ──────────────────────────────────────────────────────────────
    if op == "health-check":
        script = paths.root / "tools" / "test-mcp.sh"
        if script.exists():
            code, out = _run(["bash", str(script)], timeout=180)
            tail = "\n".join(out.splitlines()[-25:])
            return [TextContent(type="text", text=(
                f"{'Healthy' if code == 0 else 'PROBLEMS FOUND'} (exit {code})\n\n{tail}"))]
        return [TextContent(type="text", text="Self-test script not found.")]

    return [TextContent(type="text", text="Nothing to do.")]
