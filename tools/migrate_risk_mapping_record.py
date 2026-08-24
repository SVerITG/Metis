#!/usr/bin/env python3
"""migrate_risk_mapping_record.py — apply the 2026-08-17 risk-mapping record fixes.

WHY THIS EXISTS
    Metis is worked on from two computers. The repo syncs (OneDrive + git) and
    `metis-preflight.sh` reinstalls the venv at the run.sh chokepoint — but the
    DATABASE syncs by neither. Everything this session corrected lives in the DB:

      * procedural memory #8, the risk-mapping runbook
      * procedure #20, which named 4__pop_density.R / 3__area_at_risk.R / 0__setup.R
        — none of which exist
      * procedure #21, filed as "Angola" but naming only DRC Workflow Article scripts,
        and citing gadm41_AGO_*.shp, which a May-2025 decision explicitly forbids
      * six duplicate Angola project rows

    Without this, the second computer keeps the WRONG procedures and, being freshly
    written, they read as authoritative. A correction that only lands on one machine
    is not a correction.

IDEMPOTENT. Safe to re-run: every step checks whether it has already been applied.

USAGE
    python3 tools/migrate_risk_mapping_record.py           # apply
    python3 tools/migrate_risk_mapping_record.py --check   # report only, change nothing
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sqlite3
import sys

import os

# METIS_DB lets this be rehearsed against a copy before it touches the live DB —
# the only honest way to test a migration whose whole job is to run somewhere else.
DB = pathlib.Path(os.environ.get("METIS_DB")
                  or pathlib.Path.home() / ".local/share/metis/metis.sqlite")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNBOOK = ROOT / "agents/methods-coach/risk-mapping-runbook-context.md"
CORRECTIONS = ROOT / "agents/methods-coach/_procedure-corrections-2026-08-17.json"

CANON = "angola-hat-analysis"
DUPES = ["hat-clustering", "angola-hat-metric", "ago-hat-risk-mapping",
         "cross-border-angola-drc-hat-risk-mapping", "angola-hat-risk-mapping"]

MARK = "CORRECTED 2026-08-17"          # presence = already applied
CHECK = "--check" in sys.argv
done: list[str] = []
skip: list[str] = []


def main() -> int:
    if not DB.exists():
        print(f"✗ No database at {DB}")
        return 1
    if not RUNBOOK.exists():
        print(f"✗ Runbook missing: {RUNBOOK}\n"
              f"  It is gitignored and travels by OneDrive — let the folder finish syncing.")
        return 1

    con = sqlite3.connect(DB, timeout=120.0)
    con.execute("PRAGMA busy_timeout=120000")
    con.row_factory = sqlite3.Row
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ── 1. procedural memory #8 ← the runbook file (single source) ────────────
    body = RUNBOOK.read_text(encoding="utf-8")
    steps = (f"*Generated from `agents/methods-coach/risk-mapping-runbook-context.md` "
             f"on {now[:10]}. Edit that file, then re-run tools/sync_runbook.py — "
             f"do not hand-edit this record, or the two will disagree.*\n\n" + body)
    row = con.execute("SELECT steps FROM procedural_memory WHERE id=8").fetchone()
    if row is None:
        skip.append("#8 absent — this DB has never held the risk-mapping procedure")
    elif (row["steps"] or "").endswith(body):
        skip.append("#8 already matches the runbook")
    else:
        if not CHECK:
            con.execute("UPDATE procedural_memory SET steps=? WHERE id=8", (steps,))
        done.append("#8 re-synced from the runbook file")

    # ── 2 & 3. the two procedures corrected on 2026-08-17 ─────────────────────
    # Their corrected text is carried in a JSON payload beside the runbook, because
    # the DB does not sync between computers but the folder does. Without it this
    # step could only warn, and a warning leaves the wrong procedure in place —
    # which, being the newest record, is the one that gets trusted.
    payload = {}
    if CORRECTIONS.exists():
        try:
            payload = {int(r["id"]): r
                       for r in json.loads(CORRECTIONS.read_text(encoding="utf-8"))["rows"]}
        except Exception as exc:
            skip.append(f"⚠ could not read {CORRECTIONS.name}: {exc}")

    for pid in (20, 21):
        r = con.execute("SELECT steps FROM procedural_memory WHERE id=?", (pid,)).fetchone()
        if r is None:
            skip.append(f"#{pid} not present on this machine")
        elif MARK in (r["steps"] or ""):
            skip.append(f"#{pid} already corrected")
        elif pid not in payload:
            skip.append(f"⚠ #{pid} is UNCORRECTED and {CORRECTIONS.name} is missing — "
                        f"it names files that do not exist; delete it or re-sync the folder")
        else:
            p = payload[pid]
            if not CHECK:
                con.execute(
                    "UPDATE procedural_memory SET procedure_name=?, trigger_context=?, "
                    "steps=?, project_id=?, scope=? WHERE id=?",
                    (p["procedure_name"], p["trigger_context"], p["steps"],
                     p["project_id"], p["scope"], pid))
            done.append(f"#{pid} corrected — {p['procedure_name'][:58]}")

    # ── 4. merge the duplicate Angola project rows ────────────────────────────
    present = [d for d in DUPES if con.execute(
        "SELECT 1 FROM projects WHERE project_id=?", (d,)).fetchone()]
    if not present:
        skip.append("project rows already merged")
    elif con.execute("SELECT 1 FROM projects WHERE project_id=?", (CANON,)).fetchone() is None:
        skip.append(f"⚠ canonical row {CANON} missing — not merging into nothing")
    else:
        if not CHECK:
            desktop = con.execute(
                "SELECT prompt_memory FROM projects WHERE project_id='hat-clustering'"
            ).fetchone()
            if desktop and desktop[0]:
                cur = con.execute("SELECT history_log FROM projects WHERE project_id=?",
                                  (CANON,)).fetchone()[0]
                hist = json.loads(cur) if cur and cur.strip() not in ("", "[]") else []
                if "Claude Desktop" not in json.dumps(hist):
                    hist.insert(0, {"date": "2025-05", "ts": now, "summary":
                        "[Recovered from the retired 'hat-clustering' row — Claude Desktop, "
                        "May 2025.]\n\n" + desktop[0]})
                    con.execute("UPDATE projects SET history_log=? WHERE project_id=?",
                                (json.dumps(hist), CANON))
            for tbl in ("tasks", "episodic_memory", "procedural_memory", "code_artifacts",
                        "data_dictionary", "dataset_treatments"):
                try:
                    con.execute(
                        f"UPDATE {tbl} SET project_id=? WHERE project_id IN "
                        f"({','.join('?' * len(present))})", [CANON] + present)
                except sqlite3.OperationalError:
                    pass  # table absent on this machine — not fatal
            con.execute(f"DELETE FROM projects WHERE project_id IN "
                        f"({','.join('?' * len(present))})", present)
        done.append(f"merged {len(present)} duplicate project row(s) into {CANON}")

    if not CHECK:
        con.commit()
    con.close()

    verb = "WOULD DO" if CHECK else "DID"
    print(f"\n── {verb} ──")
    for d in done or ["(nothing — already up to date)"]:
        print(f"  ✓ {d}")
    print("── skipped ──")
    for s in skip:
        print(f"  · {s}")
    if CHECK and done:
        print("\nRe-run without --check to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
