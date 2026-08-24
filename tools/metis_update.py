#!/usr/bin/env python3
"""metis_update.py — update Metis safely, from a button, with a way back.

WHY THIS EXISTS (Keystone P2.4)
    `tools/metis-update.sh` could update Metis, but only from a terminal — which
    fails the whole "non-technical by default" promise: the person Metis is built
    for cannot open a shell and run a script. It also backed up only the database,
    ran no rollback, and if the update broke something it left the researcher with
    a half-updated system and no way back.

    An update the user is afraid to run is an update that never happens, and a
    Metis that never updates is one that quietly rots.

THE CONTRACT
    1. RECORD what "before" looked like — the commit, and row counts for every
       table that holds the researcher's work.
    2. BACK UP the canonical database to a static snapshot (no live WAL).
    3. PULL, reinstall, migrate — additively, never dropping anything.
    4. VERIFY by re-counting. Any table that SHRANK means data was lost.
    5. ROLL BACK automatically if verification fails: restore the commit, restore
       the database, reinstall. The researcher ends where they started.

    Every step writes to a status file, so a dashboard can show progress and, more
    importantly, so a failure leaves a readable account of itself rather than a
    silent half-state.

USAGE
    python3 tools/metis_update.py            # run the update
    python3 tools/metis_update.py --dry-run  # check only; changes nothing
    python3 tools/metis_update.py --status   # print the last run's status JSON
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = Path.home() / ".local/share/metis-mcp"
STATUS_FILE = STATE_DIR / "update-status.json"

# Tables holding the researcher's own work. A row count that DROPS across an
# update is the definition of a failed update, whatever else succeeded.
GUARDED_TABLES = [
    "ideas", "projects", "tasks", "memory_entries", "episodic_memory",
    "semantic_memory", "procedural_memory", "session_summaries", "reflexion_log",
    "agent_runs", "user_decisions", "agent_routing_rules", "personal_notes",
    "literature_metadata", "pdf_chunks", "knowledge_databases",

    # ── Library tables, added 2026-08-21 ───────────────────────────────────
    # `literature_metadata` was guarded and everything else about the library
    # was not, so an update could have emptied the reading list, the book shelf,
    # the full-text index or the PDF-path index and still reported success. The
    # verification step compares row counts, so an unlisted table is simply not
    # checked — silence, not a warning.
    #
    # These hold work that cannot be recreated by re-scanning:
    #   new_publications        — every reviewed/dismissed decision, and the
    #                             acquisition state behind each red dot
    #   library_review_state    — the catch-up marker; losing it silently widens
    #                             the catch-up window to "everything"
    #   library_acquisition_log — why a PDF could not be obtained
    #   library_cards           — the book shelf, with read status
    #   library_fulltext(+_chunks) — extracted PDF text and its embeddings, which
    #                             cost real time to rebuild
    #   library_inventory / library_seeded / library_item_status / zotero_sync_state
    "new_publications", "library_review_state", "library_acquisition_log",
    "library_cards", "library_fulltext", "library_fulltext_chunks",
    "library_inventory", "library_seeded", "library_item_status",
    "zotero_sync_state",
]

# The PDFs themselves live OUTSIDE the repository — under the researcher's own
# library_path (an OneDrive folder here) — so no git operation during an update
# can touch them, which is the right arrangement and worth stating rather than
# leaving as an accident. Metis therefore never backs them up either: that is
# OneDrive's job, and duplicating gigabytes of PDFs into the repo would be worse
# than the risk it removes. What Metis DOES own is the mapping from a catalogue
# row to a path, and those tables are now guarded above.


def _venv_python() -> str:
    p = Path.home() / ".local/share/metis-mcp/.venv/bin/python3"
    return str(p) if p.exists() else sys.executable


def _db_path() -> Path:
    try:
        out = subprocess.run(
            [_venv_python(), "-c",
             "from metis_mcp.config import paths; print(paths.db)"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "METIS_RC_ROOT": str(ROOT)},
        ).stdout.strip().splitlines()
        for line in reversed(out):
            if line.endswith(".sqlite"):
                return Path(line)
    except Exception:
        pass
    return Path.home() / ".local/share/metis/metis.sqlite"


def _status(step: str, state: str, detail: str = "", **extra) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}
    except Exception:
        current = {}
    current.update({
        "step": step, "state": state, "detail": detail,
        "updated_at": datetime.now().isoformat(timespec="seconds"), **extra,
    })
    log = current.setdefault("log", [])
    log.append({"step": step, "state": state, "detail": detail[:300],
                "at": current["updated_at"]})
    current["log"] = log[-40:]
    try:
        STATUS_FILE.write_text(json.dumps(current, indent=2))
    except Exception:
        pass
    print(f"[{state:8}] {step}{(' — ' + detail) if detail else ''}", flush=True)
    return current


def _counts(db: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    if not db.is_file():
        return out
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=120)
        for t in GUARDED_TABLES:
            try:
                out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                pass          # a table that does not exist yet is not a loss
        con.close()
    except Exception:
        pass
    return out


def _git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, timeout=180, check=check)


def _run(cmd: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          cwd=str(ROOT),
                          env={**os.environ, "METIS_RC_ROOT": str(ROOT)})


def main() -> int:
    dry = "--dry-run" in sys.argv
    if "--status" in sys.argv:
        print(STATUS_FILE.read_text() if STATUS_FILE.exists() else "{}")
        return 0

    db = _db_path()
    STATUS_FILE.unlink(missing_ok=True)
    _status("start", "running", f"{'DRY RUN — nothing will change' if dry else 'updating Metis'}",
            dry_run=dry, db=str(db))

    # ── 1. Record "before" ───────────────────────────────────────────────────
    dirty = bool(_git("status", "--porcelain").stdout.strip())
    before_sha = _git("rev-parse", "HEAD").stdout.strip()
    before = _counts(db)
    _status("record", "ok",
            f"{len(before)} data tables, {sum(before.values()):,} rows, at {before_sha[:8]}"
            + (" — WORKING TREE DIRTY" if dirty else ""),
            before_sha=before_sha, before_counts=before, dirty=dirty)

    if dirty and not dry:
        # Uncommitted work would be destroyed by a rollback's `git reset --hard`.
        # Refusing is the only safe answer: the whole point of this tool is that it
        # can always undo itself, and it cannot promise that here.
        _status("finish", "blocked",
                "You have uncommitted changes. Commit or stash them first — "
                "otherwise a rollback would discard them.")
        return 2

    # ── 2. Is there anything to update? ──────────────────────────────────────
    fetched = _git("fetch", "metis-ph", "--quiet")
    behind = _git("rev-list", "--count", "HEAD..metis-ph/main").stdout.strip() or "0"
    if fetched.returncode != 0:
        _status("check", "warn", "could not reach the update server — check your connection")
    if behind == "0":
        _status("finish", "ok", "Metis is already up to date.", behind=0)
        return 0
    _status("check", "ok", f"{behind} update(s) available", behind=int(behind))

    if dry:
        _status("finish", "ok", f"Dry run complete — {behind} update(s) would be applied.")
        return 0

    # ── 3. Back up the database (static snapshot, no live WAL) ───────────────
    backup = STATE_DIR / f"pre-update-{time.strftime('%Y%m%d-%H%M%S')}.sqlite"
    try:
        src = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=120)
        dst = sqlite3.connect(str(backup))
        with dst:
            src.backup(dst)          # the SQLite backup API — WAL-safe, unlike cp
        src.close(); dst.close()
        _status("backup", "ok", f"database saved to {backup.name} "
                                f"({backup.stat().st_size // 1_000_000} MB)", backup=str(backup))
    except Exception as exc:
        _status("finish", "failed", f"could not back up the database — stopping: {exc}")
        return 1

    def rollback(why: str) -> int:
        _status("rollback", "running", why)
        _git("reset", "--hard", before_sha)
        try:
            if backup.is_file():
                shutil.copy2(backup, db)
                for sidecar in (db.with_suffix(".sqlite-wal"), db.with_suffix(".sqlite-shm")):
                    sidecar.unlink(missing_ok=True)
        except Exception as exc:
            _status("rollback", "failed",
                    f"code restored but the database could not be: {exc}. "
                    f"Your backup is at {backup}")
            return 1
        _run(["bash", str(ROOT / "tools/reinstall-mcp.sh")])
        _status("finish", "rolled_back",
                f"Update undone — you are back on {before_sha[:8]} with your data intact.")
        return 1

    # ── 4. Pull ──────────────────────────────────────────────────────────────
    pull = _git("merge", "--ff-only", "metis-ph/main")
    if pull.returncode != 0:
        _status("finish", "failed",
                "could not apply the update cleanly (local changes diverge) — nothing was changed")
        return 1
    _status("pull", "ok", f"updated to {_git('rev-parse','HEAD').stdout.strip()[:8]}")

    # ── 5. Reinstall + additive migrations ───────────────────────────────────
    r = _run(["bash", str(ROOT / "tools/reinstall-mcp.sh")])
    if r.returncode != 0:
        return rollback("the new version could not be installed")
    _status("install", "ok", "server reinstalled and migrations applied")

    # ── 6. Verify nothing was lost ───────────────────────────────────────────
    after = _counts(db)
    lost = {t: (before[t], after.get(t, 0))
            for t in before if after.get(t, 0) < before[t]}
    if lost:
        return rollback("data would have been lost: "
                        + ", ".join(f"{t} {b}→{a}" for t, (b, a) in lost.items()))

    health = _run(["bash", str(ROOT / "tools/test-mcp.sh")])
    if "RESULT: HEALTHY" not in (health.stdout or ""):
        return rollback("the updated system did not pass its health check")

    _status("finish", "ok",
            f"Metis updated. {sum(after.values()):,} rows intact across {len(after)} tables; "
            f"health check passed.",
            after_counts=after, backup=str(backup))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
