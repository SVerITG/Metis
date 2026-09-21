#!/usr/bin/env python3
"""apply_specialist_mining.py — attribute standing decisions to the specialist that acts on them.

WHY THIS EXISTS
    A standing decision with no `agent_slug` is project-wide: it reaches every
    specialist through a shared block that the per-agent memory generator caps at a
    small number of entries. Project-wide rows outnumber any one specialist's own by
    roughly ten to one, so an unattributed preference competes for a slot it will
    usually lose, and the specialist that actually needed it never sees it.

    Two separate causes produced the backlog this script clears:

      1. Rows promoted out of session history were attributed by a keyword router
         whose rule table can only ever emit about fifteen slugs. Every other
         specialist is unreachable by it BY CONSTRUCTION, not because nothing was
         ever decided for them — so they hold nothing and return a persona.
      2. Preferences stated in prose that was never mined at all: session prose,
         event log, reflexions. Those were read by hand for this pass.

WHAT IT DOES
      job1  — set `agent_slug` on existing unattributed rows.
      job1b — correct a small number of rows attributed to a specialist that cannot
              act on them.
      job2  — insert preferences found in history that are not yet standing
              decisions, each carrying a verbatim quote and its source row.

    Every proposal was reviewed by a person before it reached the data file. The file
    is the reviewed artefact; this script only executes it.

SAFETY
    Default is a DRY RUN. `--apply` writes, and takes a database snapshot first.
    Before changing any attribution it records the previous value to a revert journal
    beside the data file, so `--revert` restores exactly what was there. job2 inserts
    are NOT reverted automatically — deleting rows is a different risk from restoring
    a field, so it prints the ids for a deliberate decision.

    Inserts go through the package's own record_decision() rather than raw SQL, so the
    table shape has one author.

Run:
    PY=$HOME/.local/share/metis-mcp/.venv/bin/python3
    METIS_RC_ROOT="$PWD" PYTHONPATH="...:$PWD/system/mcp-server/src" \
        $PY tools/apply_specialist_mining.py            # dry run
        $PY tools/apply_specialist_mining.py --apply
        $PY tools/apply_specialist_mining.py --revert
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("METIS_RC_ROOT", Path(__file__).resolve().parents[1]))
DEFAULT_DATA = ROOT / "outputs/reviews/memory-curator/2026-09-21_specialist-mining.json"

_STOP = {"the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "with", "that",
         "this", "it", "is", "be", "we", "i", "should", "will", "would", "can", "do"}


def _db_path() -> Path:
    """Resolve the live database the same way the package does, with a fallback."""
    try:
        from metis_mcp.config import paths           # type: ignore
        return Path(paths.db)
    except Exception:
        return Path.home() / ".local/share/metis/metis.sqlite"


def _fingerprint(s: str) -> str:
    words = [w for w in re.sub(r"[^\w\s]", " ", (s or "").lower()).split()
             if w not in _STOP]
    return " ".join(sorted(words))


def _known_slugs() -> set[str]:
    """Slugs that can actually be dispatched — a decision filed under a slug with no
    agent definition is delivered to nobody, which is the failure being fixed."""
    d = ROOT / ".claude/agents"
    return {p.stem for p in d.glob("*.md")} if d.is_dir() else set()


def _snapshot() -> None:
    tool = ROOT / "tools/backup-canonical.py"
    if not tool.exists():
        print("  ! backup-canonical.py not found — refusing to write without a snapshot")
        sys.exit(2)
    print("  · taking a database snapshot first")
    subprocess.run([sys.executable, str(tool)], check=True)


# ── the three operations ────────────────────────────────────────────────────

def plan(data: dict, con: sqlite3.Connection) -> dict:
    """Compare the reviewed proposal against the live table. Returns a work plan
    plus everything that no longer matches, which is reported rather than forced."""
    slugs = _known_slugs()
    todo, skip = [], []

    for item in data.get("job1_reattribute", []) + data.get("job1b_reattribute_nonorphan", []):
        row = con.execute("SELECT decision, COALESCE(agent_slug,'') FROM user_decisions "
                          "WHERE decision_id=?", (item["decision_id"],)).fetchone()
        if row is None:
            skip.append((item["decision_id"], "row no longer exists"))
            continue
        current = row[1]
        if current == item["to"]:
            skip.append((item["decision_id"], "already attributed as proposed"))
            continue
        expected = item.get("expect_from")
        if expected is not None and current != expected:
            skip.append((item["decision_id"],
                         f"attribution changed since review (now '{current}')"))
            continue
        if slugs and item["to"] not in slugs:
            skip.append((item["decision_id"], f"no agent definition for '{item['to']}'"))
            continue
        todo.append({"decision_id": item["decision_id"], "from": current,
                     "to": item["to"], "text": row[0]})

    existing = {}
    for did, d in con.execute("SELECT decision_id, decision FROM user_decisions"):
        existing[_fingerprint(d)] = did
    short: dict[str, int] = {}
    for k, v in existing.items():
        short.setdefault(" ".join(k.split()[:8]), v)

    inserts, dupes = [], []
    for item in data.get("job2_insert", []):
        f = _fingerprint(item["decision"])
        hit = existing.get(f) or short.get(" ".join(f.split()[:8]))
        if hit:
            dupes.append((item["slug"], hit))
        elif slugs and item["slug"] not in slugs:
            skip.append((item["slug"], "no agent definition for this slug"))
        else:
            inserts.append(item)

    return {"reattribute": todo, "insert": inserts,
            "skipped": skip, "already_present": dupes}


def do_apply(data: dict, data_path: Path, dry: bool) -> int:
    con = sqlite3.connect(_db_path())
    work = plan(data, con)

    print(f"\n  re-attribute : {len(work['reattribute']):>4}")
    print(f"  insert new   : {len(work['insert']):>4}")
    print(f"  already ok   : {len(work['already_present']):>4}  (identical text already stored)")
    print(f"  skipped      : {len(work['skipped']):>4}")

    by_slug: dict[str, int] = {}
    for w in work["reattribute"]:
        by_slug[w["to"]] = by_slug.get(w["to"], 0) + 1
    for w in work["insert"]:
        by_slug[w["slug"]] = by_slug.get(w["slug"], 0) + 1
    if by_slug:
        print("\n  per specialist:")
        for slug, n in sorted(by_slug.items(), key=lambda kv: -kv[1]):
            print(f"      {n:>4}  {slug}")

    for what, why in work["skipped"]:
        print(f"  · skipped {what}: {why}")

    if dry:
        print("\n  DRY RUN — nothing written. Re-run with --apply to write.")
        con.close()
        return 0

    _snapshot()

    journal = {"applied_at": datetime.now().isoformat(timespec="seconds"),
               "previous": {str(w["decision_id"]): w["from"] for w in work["reattribute"]}}
    jpath = data_path.with_name(data_path.stem + "_revert.json")
    jpath.write_text(json.dumps(journal, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  · previous attributions written to {jpath.name} — needed for --revert")

    for w in work["reattribute"]:
        con.execute("UPDATE user_decisions SET agent_slug=? WHERE decision_id=?",
                    (w["to"], w["decision_id"]))
    con.commit()
    con.close()

    # Inserts go through the package so there is one author for the table shape.
    from metis_mcp.tools.pipeline import record_decision      # type: ignore
    made = []
    for item in work["insert"]:
        ctx = (f"Mined from {item['table']} row {item['row']} ({item['date']}). "
               f"Verbatim source: \"{item['quote']}\"")
        record_decision(decision=item["decision"], category=item.get("category", "preference"),
                        context=ctx, scope="always", agent_slug=item["slug"])
        made.append(item["slug"])

    print(f"\n  applied: {len(work['reattribute'])} re-attributed, {len(made)} inserted")
    print("  regenerate the per-agent memory files:  python3 tools/generate_agent_memory.py")
    return 0


def _unescape(s: str) -> str:
    """One history column stores JSON text, so its em dashes are literal \\uXXXX
    escapes. Fold both forms before comparing, or a true quote reports as missing."""
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    return re.sub(r"\s+", " ", s)


_SOURCE_SQL = {
    "session_summaries": "SELECT COALESCE(summary,'')||' '||COALESCE(decisions,'') "
                         "FROM session_summaries WHERE id=?",
    "episodic_memory": "SELECT content FROM episodic_memory WHERE id=?",
    "reflexion_log": "SELECT COALESCE(went_well,'')||' '||COALESCE(could_improve,'')||' '"
                     "||COALESCE(missing_context,'')||' '||COALESCE(tool_wishes,'') "
                     "FROM reflexion_log WHERE reflexion_id=?",
    "memory_entries": "SELECT COALESCE(title,'')||' '||COALESCE(summary,'') "
                      "FROM memory_entries WHERE entry_id=?",
}


def do_verify(data: dict) -> int:
    """Re-check every proposed insert's quote against the row it claims to come from.

    A proposal whose quote cannot be found is a fabrication, whatever else it looks
    like — so this must be able to FAIL, and it is the check that makes the review's
    provenance claim reproducible rather than asserted.
    """
    con = sqlite3.connect(_db_path())
    bad = 0
    for item in data.get("job2_insert", []):
        sql = _SOURCE_SQL.get(item["table"])
        row = con.execute(sql, (item["row"],)).fetchone() if sql else None
        found = bool(row) and _unescape(item["quote"]) in _unescape(row[0])
        if not found:
            bad += 1
        print(f"  {'ok  ' if found else 'MISS'} {item['slug']:20s} "
              f"{item['table']}#{item['row']} · {item['quote'][:60]}")
    con.close()
    total = len(data.get("job2_insert", []))
    print(f"\n  {total} quote(s) checked, {bad} not found in the claimed source row")
    return 1 if bad else 0


def do_revert(data_path: Path, dry: bool) -> int:
    jpath = data_path.with_name(data_path.stem + "_revert.json")
    if not jpath.exists():
        print(f"  no revert journal at {jpath} — nothing was applied from this file")
        return 1
    journal = json.loads(jpath.read_text(encoding="utf-8"))
    prev = journal.get("previous", {})
    print(f"  revert journal from {journal.get('applied_at')}: {len(prev)} attribution(s)")

    con = sqlite3.connect(_db_path())
    changed = 0
    for did, old in prev.items():
        row = con.execute("SELECT COALESCE(agent_slug,'') FROM user_decisions "
                          "WHERE decision_id=?", (int(did),)).fetchone()
        if row is None or row[0] == old:
            continue
        changed += 1
        if not dry:
            con.execute("UPDATE user_decisions SET agent_slug=? WHERE decision_id=?",
                        (old, int(did)))
    if dry:
        print(f"  DRY RUN — would restore {changed} attribution(s). Re-run with --apply.")
    else:
        _snapshot()
        con.commit()
        print(f"  restored {changed} attribution(s)")
        print("  note: inserted rows are NOT deleted by --revert; remove them deliberately "
              "if that is what you want.")
    con.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(DEFAULT_DATA),
                    help="reviewed proposal file (JSON)")
    ap.add_argument("--apply", action="store_true", help="write the changes")
    ap.add_argument("--revert", action="store_true",
                    help="restore the attributions recorded in the revert journal")
    ap.add_argument("--verify", action="store_true",
                    help="check every proposed insert's quote against its source row, "
                         "and exit non-zero if any is not found")
    args = ap.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"  proposal file not found: {data_path}")
        return 1

    print(f"  data : {data_path}")
    print(f"  db   : {_db_path()}")

    if args.revert:
        return do_revert(data_path, dry=not args.apply)

    data = json.loads(data_path.read_text(encoding="utf-8"))
    if args.verify:
        return do_verify(data)
    kept = len(data.get("job1_keep_shared", []))
    print(f"  proposal generated {data.get('generated')} · "
          f"{kept} row(s) deliberately left project-wide and not touched here")
    return do_apply(data, data_path, dry=not args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
