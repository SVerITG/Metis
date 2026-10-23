#!/usr/bin/env python3
"""metis-sync-db.py — converge Metis's memory across two computers, safely.

THE PROBLEM
    The user works from two machines. The CODE syncs (git + the OneDrive folder), but
    the DATABASE does not: this machine's memory stopped at 8 July while the other
    had 8-13 July. Sessions, agent runs, ideas and reflexions diverged silently.

WHY THE LIVE DB IS NOT SIMPLY PUT ON ONEDRIVE
    It was, and OneDrive destroyed it (2026-06-19). A live SQLite database is
    THREE files — .sqlite, -wal, -shm — that must stay mutually consistent.
    OneDrive copied them at different instants, mid-write, and the result was a
    corrupt database. That is why the live DB was moved to the native filesystem.

    But the lesson is narrower than "SQLite and OneDrive don't mix". It is:

        ** OneDrive must never touch a file that is being WRITTEN. **

    A finished, static snapshot has no WAL and no writer. It is just bytes. That
    is provably safe on OneDrive — tools/backup-canonical.py has been doing it
    correctly all along (snapshot to /tmp via the SQLite backup API, then MOVE the
    completed file across, so OneDrive never sees a half-written database).

THE DESIGN
    live DB (local, native FS)  ──export──▶  immutable snapshot on OneDrive
                                                     │
    live DB (other machine)     ◀──merge───────────── ┘

    * The live database NEVER goes on OneDrive. That rule is unchanged.
    * OneDrive carries only finished, hostname-stamped snapshots.
    * Each machine merges the snapshots the OTHER machines left behind.
    * Convergence is eventual, and that is fine: this is memory, not a ledger.

WHY THE MERGE IS SAFE
    The tables we merge are append-only event logs. Union is the correct operation
    — there is no conflict to resolve, only rows one machine has not seen yet.

    The one real trap: every table has an autoincrement `id`, and those COLLIDE
    across machines (both have an episodic_memory id=5, meaning different things).
    So rows are identified by a CONTENT FINGERPRINT — a hash of every column
    except the local id. Merging is therefore idempotent: re-importing the same
    snapshot inserts nothing.

    Mutable tables — briefs, Today boards, news, tasks, projects — need more than a
    union: a row edited on one machine must REPLACE the old version on the other,
    and a row deleted on one must not be resurrected by the other. Every table is
    synced unless EXCLUDED (see plan_tables / KEYED_OVERRIDES): each keyed table
    has a natural key that means the same thing on both machines, triggers
    record when each row last changed (sync_meta) and when it was deleted
    (sync_tombstones), and the newer edit wins. Without that, the two dashboards
    showed different briefs, boards and tasks however often the memory synced.

    Newly merged memory has no embedding — the nightly `embedding_backfill` job
    reconciles that automatically, so semantic recall picks the rows up on its own.

USAGE
    python3 tools/metis-sync-db.py            # export ours, merge theirs
    python3 tools/metis-sync-db.py --status   # what's out there, what's merged
    python3 tools/metis-sync-db.py --dry-run  # show what WOULD be merged
    python3 tools/metis-sync-db.py --import-only / --export-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))

from metis_mcp.config import paths  # noqa: E402

SNAPSHOTS = ROOT / "system" / "app" / "data" / "cloud-backups"  # OneDrive-synced
HOST = "".join(c if c.isalnum() else "-" for c in platform.node()) or "unknown"
KEEP_PER_HOST = 7

# ── What we merge ────────────────────────────────────────────────────────────
# Append-only logs, each self-contained (nothing else joins to their `id`).
MERGE_TABLES = [
    "episodic_memory",
    "semantic_memory",
    "procedural_memory",
    "session_summaries",
    "agent_runs",
    "reflexion_log",
    "user_decisions",
    "skill_improvement_proposals",
    "focus_brief_log",
    "session_events",
    "brainstorm_turns",
    "research_timeline",
    "library_acquisition_log",
    "data_dictionary",
    "dataset_treatments",
    "knowledge_links",
]

# ── Every other table: matched by natural key, newest edit wins ──────────────
# The rule is "the same on every computer": any table not excluded below is
# synced. Its key comes from KEYED_OVERRIDES, else its primary key when that is
# not a local autoincrement integer, else its first UNIQUE index. A table with
# none of those falls back to the append-only union — and the status listing
# says so, so a new mutable table cannot silently get union semantics.
#
# key      columns that identify the row on EVERY machine (never a local autoincrement id)
# version  timestamp columns; the newest of them dates a row changed before the
#          triggers existed. sync_meta takes precedence once a row has an entry
# local    columns describing this machine, carried on insert but never overwritten
# dedupe   a second identity checked before inserting: news ids are random uuids,
#          so the same article scanned on both machines arrives under two ids
# refs     columns holding ANOTHER table's local id: translated through that
#          table's own key, optionally only when a discriminator column matches.
#          A declined paper is stored as its local new_publications id — the
#          same number names a different paper on the other machine.
KEYED_OVERRIDES: dict[str, dict] = {
    "daily_insights":       {"key": ("insight_date",), "version": ("generated_at", "read_at")},
    "today_board_items":    {"key": ("board", "title", "url"), "version": ("updated_at", "created_at", "seen_at")},
    "tasks":                {"key": ("task_id",), "version": ("updated_at", "created_at")},
    "projects":             {"key": ("project_id",), "version": ("last_session_at", "created_at"),
                             "local": ("external_path", "launch_cmd", "launcher_type", "launcher_path",
                                       "launchers", "claude_desktop_linked", "last_scanned",
                                       "scan_summary")},
    "news_briefs":          {"key": ("brief_id",), "version": ("created_at", "seen_at"), "dedupe": "source_url"},
    "new_publications":     {"key": ("source_url",),
                             "version": ("discovered_at", "read_at", "added_at", "dismissed_at")},
    "literature_metadata":  {"key": ("title", "year"), "version": ("created_at", "read_at")},
    "learning_courses":     {"key": ("slug",), "version": ("updated_at", "created_at", "completed_at")},
    "code_artifacts":       {"key": ("project_id", "title"), "version": ("updated_at", "created_at")},
    "library_cards":        {"key": ("source_path",), "version": ("created_at",)},
    "focus_dismissed":      {"key": ("item_type", "item_id"), "version": ("dismissed_at",)},
    "day_plan":             {"key": ("created_at", "kind"), "version": ("updated_at", "created_at")},
    "day_plan_occurrence":  {"key": ("plan_id", "occurred_on"), "version": ("updated_at", "notified_at"),
                             "refs": {"plan_id": ("day_plan", "plan_id", None)}},
    "reading_stack":        {"key": ("kind", "item_id"), "version": ("state_at", "added_at"),
                             "refs": {"item_id": [("new_publications", "id", ("kind", "paper")),
                                                  ("news_briefs", "brief_id", ("kind", "news"))]}},
}

# Never synced: each machine regenerates these from synced data or its own files,
# or they describe the machine itself. Copying them would be wrong or wasteful.
EXCLUDED_PREFIXES = ("vec_", "sqlite_", "sync_", "news_thread", "library_fulltext")
EXCLUDED = {
    "db_sync_state", "_schema_migrations", "metis_meta",       # sync / schema bookkeeping
    "jobs_log", "tool_guard_log",                               # this machine's own logs
    "tracked_files", "zotero_sync_state", "learning_loop_state",  # this machine's paths and cursors
    "pdf_chunks", "pdf_index_state",                            # search index, rebuilt from the PDFs
    "library_inventory", "library_seeded", "library_duplicates",  # scans of the OneDrive library
}

# Merging any of these changes what relevance scoring learns from, so the
# cached interest profile must be rebuilt rather than served for another day.
PREFERENCE_TABLES = {"reading_stack", "new_publications", "news_briefs", "user_topics",
                     "projects", "tasks", "ideas", "personal_notes", "meetings",
                     "learning_courses", "literature_metadata", "focus_dismissed"}


def _excluded(table: str) -> bool:
    return table in EXCLUDED or table.startswith(EXCLUDED_PREFIXES) or "_bak_" in table


def plan_tables(con: sqlite3.Connection) -> dict[str, dict]:
    """Every table in `con` that is synced by key, with its spec."""
    plan: dict[str, dict] = {}
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        if _excluded(table) or table in MERGE_TABLES:
            continue
        if table in KEYED_OVERRIDES:
            plan[table] = KEYED_OVERRIDES[table]
            continue
        info = con.execute(f"PRAGMA table_info({_q(table)})").fetchall()
        types = {r["name"]: (r["type"] or "").upper() for r in info}
        pk = [r["name"] for r in sorted(info, key=lambda r: r["pk"]) if r["pk"]]
        stamps = tuple(r["name"] for r in info
                       if r["name"].endswith(("_at", "updated", "modified")))
        if pk and not (len(pk) == 1 and types[pk[0]] == "INTEGER"):
            plan[table] = {"key": tuple(pk), "version": stamps}
            continue
        for idx in con.execute(f"PRAGMA index_list({_q(table)})"):
            if idx["unique"] and idx["origin"] != "pk":
                cols = tuple(r["name"] for r in con.execute(f"PRAGMA index_info({_q(idx['name'])})"))
                if cols and all(cols):
                    plan[table] = {"key": cols, "version": stamps}
                    break
    return plan


def union_tables(con: sqlite3.Connection) -> list[str]:
    """MERGE_TABLES plus any non-excluded table with no usable key."""
    keyed = plan_tables(con)
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    extra = [t for t in names if t not in keyed and t not in MERGE_TABLES and not _excluded(t)]
    return list(MERGE_TABLES) + extra

# A tombstone older than this has reached every machine that syncs at all.
TOMBSTONE_TTL_DAYS = 90

# ── What we deliberately DON'T merge, and why ────────────────────────────────
SKIPPED = {
    "news_threads / items": "derived — each machine threads merged briefs itself (brief_ref is a local rowid)",
    "tracked_files":        "machine-local filesystem paths",
    "jobs_log / tool_guard_log": "this machine's own logs",
    "pdf_chunks / library_inventory / library_fulltext": "rebuilt from the PDFs, which sync via OneDrive",
    "vec_* (embeddings)":   "rebuilt locally by the nightly embedding_backfill job",
    "zotero / learning-loop cursors": "where THIS machine's own sync loops left off",
}

_SYNC_STATE_DDL = """
CREATE TABLE IF NOT EXISTS db_sync_state (
    snapshot   TEXT PRIMARY KEY,   -- filename of the snapshot we merged
    host       TEXT NOT NULL,      -- which machine produced it
    merged_at  TEXT NOT NULL,
    rows_added INTEGER NOT NULL DEFAULT 0
)
"""

# Change tracking lives in side tables, not in new columns on the app's tables:
# an extra column would break any positional INSERT or SELECT * unpacking.
_TRACKING_DDL = (
    "CREATE TABLE IF NOT EXISTS sync_meta ("
    " tbl TEXT NOT NULL, k TEXT NOT NULL, mtime TEXT NOT NULL,"
    " PRIMARY KEY (tbl, k)) WITHOUT ROWID",
    "CREATE TABLE IF NOT EXISTS sync_tombstones ("
    " tbl TEXT NOT NULL, k TEXT NOT NULL, deleted_at TEXT NOT NULL,"
    " PRIMARY KEY (tbl, k)) WITHOUT ROWID",
)
_NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


def _connect(path: Path, readonly: bool = False) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro" if readonly else f"file:{path}"
    con = sqlite3.connect(uri, uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    if not readonly:
        con.execute("PRAGMA busy_timeout=30000")
    return con


def _pk_of(con: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in con.execute(f"PRAGMA table_info({table})") if r["pk"]}


def _columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]


# ── Columns that are LOCAL STATE, not identity ───────────────────────────────
# A usage counter says what this machine did with a row; it does not say which
# row it is. Including one in the content hash means the same decision, seen on
# two computers with different counts, hashes differently — so the merge reads it
# as new and inserts a duplicate on every single run, for ever.
#
# The counters were harmless while every value was 0. A delivery count that
# actually increments makes them divergent, which is exactly when this breaks.
# Identity is the content; usage is local and starts fresh on each machine.
LOCAL_STATE = {
    "user_decisions": {"hits", "last_applied_at", "delivered", "last_delivered_at"},
}


def _fingerprint(row: sqlite3.Row, cols: list[str]) -> str:
    """Machine-independent identity: hash the CONTENT, never the local id.

    Autoincrement ids collide across machines — both computers have an
    episodic_memory id=5 meaning entirely different things. Hashing the content is
    what makes the merge idempotent and safe to re-run.
    """
    payload = json.dumps(
        [("" if row[c] is None else str(row[c])) for c in cols],
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Export ───────────────────────────────────────────────────────────────────

def export_snapshot(verbose: bool = True) -> Path | None:
    """Write a consistent, static snapshot of the live DB to OneDrive.

    Snapshot to /tmp with the SQLite backup API (which checkpoints the WAL), then
    MOVE the finished file. OneDrive therefore only ever sees a complete database —
    never a half-written one. This is the property whose absence corrupted the DB.
    """
    if not paths.db.exists():
        print("  no live DB — nothing to export")
        return None

    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    tmp = Path("/tmp") / f"metis-snap-{stamp}.sqlite"

    src = sqlite3.connect(str(paths.db))
    dst = sqlite3.connect(str(tmp))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    target = SNAPSHOTS / f"metis-{HOST}-{stamp}.sqlite"
    shutil.move(str(tmp), str(target))  # crosses filesystems (/tmp → OneDrive)

    # Prune only OUR OWN history — never another machine's snapshots.
    mine = sorted(SNAPSHOTS.glob(f"metis-{HOST}-*.sqlite"))
    for old in mine[:-KEEP_PER_HOST]:
        old.unlink(missing_ok=True)

    if verbose:
        mb = target.stat().st_size / 1_048_576
        print(f"  exported {target.name} ({mb:.0f} MB) · keeping last {KEEP_PER_HOST}")
    return target


# ── Import / merge ───────────────────────────────────────────────────────────

def _foreign_snapshots() -> list[Path]:
    """Snapshots produced by OTHER machines, newest first."""
    out = [
        p for p in SNAPSHOTS.glob("metis-*.sqlite")
        if not p.name.startswith(f"metis-{HOST}-")
    ]
    return sorted(out, key=lambda p: p.stat().st_mtime, reverse=True)


def _host_of(snapshot: Path) -> str:
    """Machine name from `metis-<host>-<YYYYmmdd>-<HHMMSS>.sqlite`.

    Snapshots taken before hostname-stamping are named `metis-<date>-<time>` with
    no host at all. Detect that (the field is all digits) and call it what it is,
    rather than inventing a machine called "20260622".
    """
    parts = snapshot.stem.split("-")
    if len(parts) >= 3 and not parts[1].isdigit():
        return parts[1]
    return "legacy"


def merge_snapshot(live: sqlite3.Connection, snapshot: Path, dry_run: bool,
                   keyed: bool = True) -> dict[str, int]:
    """Union the append-only tables from `snapshot`, then converge the keyed ones."""
    added: dict[str, int] = {}
    other = _connect(snapshot, readonly=True)
    try:
        their_tables = {
            r["name"] for r in other.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in union_tables(live):
            if table not in their_tables:
                continue
            try:
                live_cols = _columns(live, table)
            except sqlite3.DatabaseError:
                continue
            if not live_cols:
                continue

            pk = _pk_of(live, table)
            their_cols = _columns(other, table)
            # Only columns BOTH schemas have — the two machines may sit on
            # different migrations, and a merge must never fail on a schema drift.
            shared = [c for c in live_cols if c in their_cols]
            content = [c for c in shared
                       if c not in pk and c not in LOCAL_STATE.get(table, ())]
            if not content:
                continue

            have = {
                _fingerprint(r, content)
                for r in live.execute(f"SELECT * FROM {table}")
            }

            insert_cols = content
            placeholders = ",".join("?" for _ in insert_cols)
            sql = (
                f"INSERT INTO {table} ({','.join(insert_cols)}) VALUES ({placeholders})"
            )

            n = 0
            for row in other.execute(f"SELECT * FROM {table}"):
                if _fingerprint(row, content) in have:
                    continue
                if not dry_run:
                    live.execute(sql, [row[c] for c in insert_cols])
                n += 1
            if n:
                added[table] = n
        if not dry_run:
            live.commit()
        if keyed:
            added.update(merge_keyed(live, other, their_tables, dry_run))
    finally:
        other.close()
    return added


# ── Keyed merge: mutable tables, newest edit wins ────────────────────────────

def _q(col: str) -> str:
    return '"' + col.replace('"', '""') + '"'


def _key_sql(key: tuple[str, ...], prefix: str = "") -> str:
    """json_array(...) over the key columns — the cross-machine identity of a row.

    Built by SQLite on both sides (triggers and merge alike), so the same row
    always yields byte-identical text.
    """
    return "json_array(" + ", ".join(prefix + _q(c) for c in key) + ")"


def _norm(ts) -> str:
    """Comparable timestamp: '2026-10-05 09:00:00' and '2026-10-05T09:00:00.000Z' align."""
    s = str(ts or "").strip().replace(" ", "T")
    return s[:-1][:23] if s.endswith("Z") else s[:23]


def install_change_tracking(live: sqlite3.Connection) -> None:
    """Create sync_meta / sync_tombstones and (re)create the triggers that fill them.

    Recreated on every run rather than created once: a migration that adds a
    column must be picked up by the update trigger's change test. An update that
    only touches `local` columns does not count as an edit — a local folder scan
    must never make a row look newer than a real edit made on the other machine.
    """
    for ddl in _TRACKING_DDL:
        live.execute(ddl)
    for table, spec in plan_tables(live).items():
        cols = _columns(live, table)
        if not cols or any(k not in cols for k in spec["key"]):
            continue
        pk = _pk_of(live, table)
        tracked = [c for c in cols
                   if (c not in pk or c in spec["key"]) and c not in spec.get("local", ())]
        new_k, old_k = _key_sql(spec["key"], "NEW."), _key_sql(spec["key"], "OLD.")
        changed = " OR ".join(f"NEW.{_q(c)} IS NOT OLD.{_q(c)}" for c in tracked)
        t = table
        # DELETE-then-INSERT, never INSERT OR REPLACE: inside a trigger, the
        # outer statement's conflict policy overrides the trigger's own. An app
        # upsert (INSERT … ON CONFLICT DO UPDATE) therefore turned the trigger's
        # REPLACE into a hard failure on the second save of the same row, and an
        # outer OR IGNORE silently dropped the change record.
        live.executescript(f"""
            DROP TRIGGER IF EXISTS sync_ins_{t};
            DROP TRIGGER IF EXISTS sync_upd_{t};
            DROP TRIGGER IF EXISTS sync_del_{t};
            CREATE TRIGGER sync_ins_{t} AFTER INSERT ON {_q(t)} BEGIN
                DELETE FROM sync_meta WHERE tbl = '{t}' AND k = {new_k};
                INSERT INTO sync_meta VALUES ('{t}', {new_k}, {_NOW_SQL});
            END;
            CREATE TRIGGER sync_upd_{t} AFTER UPDATE ON {_q(t)} WHEN {changed} BEGIN
                DELETE FROM sync_meta WHERE tbl = '{t}' AND k = {new_k};
                INSERT INTO sync_meta VALUES ('{t}', {new_k}, {_NOW_SQL});
                DELETE FROM sync_tombstones
                    WHERE tbl = '{t}' AND k = {old_k} AND {old_k} IS NOT {new_k};
                INSERT INTO sync_tombstones
                    SELECT '{t}', {old_k}, {_NOW_SQL} WHERE {old_k} IS NOT {new_k};
            END;
            CREATE TRIGGER sync_del_{t} AFTER DELETE ON {_q(t)} BEGIN
                DELETE FROM sync_tombstones WHERE tbl = '{t}' AND k = {old_k};
                INSERT INTO sync_tombstones VALUES ('{t}', {old_k}, {_NOW_SQL});
                DELETE FROM sync_meta WHERE tbl = '{t}' AND k = {old_k};
            END;
        """)
    live.execute(
        "DELETE FROM sync_tombstones WHERE deleted_at < "
        f"strftime('%Y-%m-%dT%H:%M:%fZ','now','-{TOMBSTONE_TTL_DAYS} days')"
    )
    live.commit()


def _side_table(con: sqlite3.Connection, name: str, table: str) -> dict[str, str]:
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone():
        return {}
    col = "mtime" if name == "sync_meta" else "deleted_at"
    return {r["k"]: r[col] for r in
            con.execute(f"SELECT k, {col} FROM {name} WHERE tbl=?", (table,))}


def _version(row, k: str, meta: dict, spec: dict, cols: list[str]) -> str:
    """When a row last changed: its sync_meta entry, else the newest of its timestamps."""
    if k in meta:
        return _norm(meta[k])
    stamps = [_norm(row[c]) for c in spec.get("version", ()) if c in cols and row[c]]
    return max(stamps) if stamps else ""


# ── Rows that lost their id ──────────────────────────────────────────────────
# The append-only union used to insert every column except the primary key. For
# an autoincrement integer that is right; for a TEXT id it left NULL — ideas,
# journal entries, notes and memory entries that arrived from the other machine
# could not be opened, edited or deleted by id. The repair derives the id from
# the row's CONTENT, so both machines independently arrive at the same id for
# the same row, and the keyed merge then matches them.
REPAIR_PREFIX = {"ideas": "idea-", "journal_entries": "je-", "memory_entries": "mem-",
                 "personal_notes": "note-", "contacts": "contact-", "news_briefs": "nb-",
                 "meetings": "meeting-", "brainstorm_sessions": "bs-"}


def _text_pk(con: sqlite3.Connection, table: str) -> str | None:
    info = con.execute(f"PRAGMA table_info({_q(table)})").fetchall()
    pk = [r for r in info if r["pk"]]
    if len(pk) == 1 and (pk[0]["type"] or "").upper() != "INTEGER":
        return pk[0]["name"]
    return None


def _repaired_id(table: str, row, cols: list[str], pk: str) -> str:
    content = sorted(c for c in cols if c != pk)
    return REPAIR_PREFIX.get(table, f"{table}-") + _fingerprint(row, content)[:12]


def repair_null_ids(live: sqlite3.Connection) -> int:
    fixed = 0
    for table in plan_tables(live):
        pk = _text_pk(live, table)
        if not pk:
            continue
        cols = _columns(live, table)
        for r in live.execute(f"SELECT rowid AS _rid, * FROM {_q(table)} WHERE {_q(pk)} IS NULL").fetchall():
            nid = _repaired_id(table, r, cols, pk)
            if live.execute(f"SELECT 1 FROM {_q(table)} WHERE {_q(pk)} = ?", (nid,)).fetchone():
                live.execute(f"DELETE FROM {_q(table)} WHERE rowid = ?", (r["_rid"],))  # identical twin
            else:
                live.execute(f"UPDATE {_q(table)} SET {_q(pk)} = ? WHERE rowid = ?", (nid, r["_rid"]))
            fixed += 1
    live.commit()
    return fixed


# ── References to another table's local id ───────────────────────────────────

class _RefMap:
    """Translate a value of their `ref_table.ref_col` into ours, via the row's key."""

    def __init__(self, live, other, ref_table: str, ref_col: str, spec: dict):
        self.ok = ref_table in plan_tables(live)
        if not self.ok:
            return
        key, dedupe = spec["key"], spec.get("dedupe")
        sel = f"SELECT {_key_sql(key)} AS _k, {_q(ref_col)} AS _v" + (f", {_q(dedupe)} AS _d" if dedupe else "")
        theirs = other.execute(f"{sel} FROM {_q(ref_table)}").fetchall()
        ours = live.execute(f"{sel} FROM {_q(ref_table)}").fetchall()
        self.their = {str(r["_v"]): (r["_k"], r["_d"] if dedupe else None) for r in theirs}
        self.by_key = {r["_k"]: r["_v"] for r in ours}
        self.by_dedupe = {r["_d"]: r["_v"] for r in ours if dedupe and r["_d"]}

    def __call__(self, value):
        if not self.ok or value is None or str(value) not in self.their:
            return value
        k, d = self.their[str(value)]
        mine = self.by_key.get(k)
        if mine is None and d:
            mine = self.by_dedupe.get(d)
        if mine is None:
            return value
        return str(mine) if isinstance(value, str) else mine


def _translator(live, other, spec: dict, plan: dict):
    """Return f(dict_row) -> dict_row with every `refs` column translated, or None."""
    refs = spec.get("refs")
    if not refs:
        return None
    rules = []
    for col, targets in refs.items():
        for ref_table, ref_col, cond in (targets if isinstance(targets, list) else [targets]):
            if ref_table in plan:
                rules.append((col, cond, _RefMap(live, other, ref_table, ref_col, plan[ref_table])))

    def translate(row: dict) -> dict:
        for col, cond, refmap in rules:
            if col in row and (cond is None or row.get(cond[0]) == cond[1]):
                row[col] = refmap(row[col])
        return row
    return translate


# ── Today boards: the latest refresh decides the auto-added items ────────────
# A scan replaces a board's auto-added items wholesale. Before tombstones existed
# those replacements left no trace, so a union kept both machines' stale items
# and the boards grew to several times the size of either. Items the researcher
# starred, pinned, dismissed or added by hand are never touched by this rule.

def _board_refreshes(con) -> dict[str, str]:
    return {r[0]: _norm(r[1]) for r in con.execute(
        "SELECT board, MAX(created_at) FROM today_board_items WHERE auto_added = 1 GROUP BY board")}


def _board_disposable(row) -> bool:
    return (row["auto_added"] == 1 and not row["starred"] and not row["dismissed"]
            and not (row["pin_order"] or 0))


def merge_keyed(live: sqlite3.Connection, other: sqlite3.Connection,
                their_tables: set[str], dry_run: bool) -> dict[str, int]:
    """Converge every keyed table: deletions first, then inserts and newer edits.

    Tables whose rows point at another table's local id are merged last, after
    the rows they point at are in place.
    """
    added: dict[str, int] = {}
    plan = plan_tables(live)
    order = sorted(plan, key=lambda t: bool(plan[t].get("refs")))
    for table in order:
        spec = plan[table]
        if table not in their_tables:
            continue
        key = spec["key"]
        live_cols, their_cols = _columns(live, table), _columns(other, table)
        if not live_cols or any(k not in live_cols or k not in their_cols for k in key):
            continue
        shared = [c for c in live_cols if c in their_cols]
        pk = _pk_of(live, table)
        ins_cols = [c for c in shared if c not in pk or c in key]
        upd_cols = [c for c in ins_cols if c not in key and c not in spec.get("local", ())]
        translate = _translator(live, other, spec, plan)
        text_pk = _text_pk(live, table)

        def key_of(values: dict) -> str:
            return live.execute(f"SELECT json_array({', '.join('?' for _ in key)})",
                                [values[c] for c in key]).fetchone()[0]

        ours = {r["_k"]: r for r in
                live.execute(f"SELECT {_key_sql(key)} AS _k, * FROM {_q(table)}")}
        # Their rows, made comparable: lost ids repaired, local-id references
        # translated, and re-keyed in OUR terms. `orig` keeps their own key for
        # looking up their sync_meta.
        theirs: dict[str, tuple[str, dict]] = {}
        for r in other.execute(f"SELECT {_key_sql(key)} AS _k, * FROM {_q(table)}"):
            row = {c: r[c] for c in their_cols}
            if text_pk and text_pk in key and row.get(text_pk) is None:
                row[text_pk] = _repaired_id(table, row, their_cols, text_pk)
            if translate:
                row = translate(row)
            theirs[key_of(row)] = (r["_k"], row)

        our_meta, their_meta = _side_table(live, "sync_meta", table), _side_table(other, "sync_meta", table)
        our_tomb = _side_table(live, "sync_tombstones", table)
        their_tomb = {}
        for k, ts in _side_table(other, "sync_tombstones", table).items():
            vals = dict(zip(key, json.loads(k)))
            their_tomb[key_of(translate(vals) if translate else vals)] = ts
        where = " AND ".join(f"{_q(c)} IS ?" for c in key)

        def set_side(name: str, k: str, ts: str | None) -> None:
            if dry_run:
                return
            if ts:
                live.execute(f"INSERT OR REPLACE INTO {name} VALUES (?,?,?)", (table, k, ts))
            else:
                live.execute(f"DELETE FROM {name} WHERE tbl=? AND k=?", (table, k))

        def delete(k: str) -> None:
            if not dry_run:
                live.execute(f"DELETE FROM {_q(table)} WHERE {where}", json.loads(k))
            ours.pop(k, None)

        n_ins = n_upd = n_del = 0
        for k, deleted_at in their_tomb.items():
            if k in ours and _version(ours[k], k, our_meta, spec, live_cols) <= _norm(deleted_at):
                delete(k)
                n_del += 1
            if _norm(our_tomb.get(k)) < _norm(deleted_at):
                our_tomb[k] = deleted_at
                set_side("sync_tombstones", k, deleted_at)

        boards = table == "today_board_items" and {"auto_added", "starred", "dismissed",
                                                    "pin_order", "board"} <= set(shared)
        if boards:
            their_refresh = _board_refreshes(other)
            our_refresh = _board_refreshes(live)
            for k, r in list(ours.items()):
                latest = _norm(their_refresh.get(r["board"]))
                # >= not >: once their refresh has been copied here, both sides
                # share its timestamp, and our older leftovers are still stale.
                if (latest and latest >= _norm(our_refresh.get(r["board"]))
                        and _norm(r["created_at"]) < latest
                        and k not in theirs and _board_disposable(r)):
                    delete(k)  # superseded by their refresh; the trigger records it
                    n_del += 1

        dedupe = spec.get("dedupe") if spec.get("dedupe") in shared else None
        seen = {r[dedupe] for r in ours.values() if r[dedupe]} if dedupe else set()
        for k, (orig_k, row) in theirs.items():
            tv = _version(row, orig_k, their_meta, spec, their_cols)
            if k in ours:
                if (tv > _version(ours[k], k, our_meta, spec, live_cols)
                        and any(row[c] != ours[k][c] for c in upd_cols)):
                    if not dry_run:
                        sets = ", ".join(f"{_q(c)} = ?" for c in upd_cols)
                        live.execute(f"UPDATE {_q(table)} SET {sets} WHERE {where}",
                                     [row[c] for c in upd_cols] + json.loads(k))
                    set_side("sync_meta", k, tv)
                    n_upd += 1
                continue
            if k in our_tomb and _norm(our_tomb[k]) >= tv:
                continue  # deleted here after their last edit
            if dedupe and row[dedupe] and row[dedupe] in seen:
                continue  # same article, different random id
            if (boards and _board_disposable(row)
                    and _norm(row["created_at"]) < _norm(our_refresh.get(row["board"]))):
                continue  # from a refresh older than ours
            if not dry_run:
                live.execute(
                    f"INSERT INTO {_q(table)} ({', '.join(_q(c) for c in ins_cols)}) "
                    f"VALUES ({', '.join('?' for _ in ins_cols)})",
                    [row[c] for c in ins_cols],
                )
            # Keep their timestamp, not the moment of merging — otherwise every
            # merged row would look freshly edited and bounce back next time.
            set_side("sync_meta", k, tv or None)
            if dedupe and row[dedupe]:
                seen.add(row[dedupe])
            n_ins += 1

        if n_ins or n_upd or n_del:
            added[f"{table} (+{n_ins} ~{n_upd} -{n_del})"] = n_ins + n_upd + n_del
    if not dry_run:
        live.commit()
    return added


def invalidate_interest_cache(changed_tables: set[str]) -> bool:
    """Relevance caches its interest profile for a day; merged feedback must count now."""
    if not changed_tables & PREFERENCE_TABLES:
        return False
    for name in ("interest_profile.json", "interest_centroid.json"):
        (paths.db.parent / name).unlink(missing_ok=True)
    return True


# Bump when the merge starts covering data an earlier version skipped, so a
# snapshot already merged under the old rules is merged once more under the new.
MERGE_VERSION = 3


def import_snapshots(dry_run: bool = False) -> int:
    live = _connect(paths.db)
    live.execute(_SYNC_STATE_DDL)
    if "merge_version" not in _columns(live, "db_sync_state"):
        live.execute("ALTER TABLE db_sync_state ADD COLUMN merge_version INTEGER DEFAULT 1")
    live.commit()

    merged_already = {
        r["snapshot"] for r in live.execute(
            "SELECT snapshot FROM db_sync_state WHERE merge_version >= ?", (MERGE_VERSION,))
    }

    total = 0
    changed: set[str] = set()
    foreign = _foreign_snapshots()
    if not foreign:
        print("  no snapshots from other machines yet.")
        print("  → run this script on the OTHER computer to publish its memory.")
        live.close()
        return 0

    # Only the newest snapshot per host: an older one is a strict subset of it.
    newest: dict[str, Path] = {}
    for snap in foreign:
        newest.setdefault(_host_of(snap), snap)

    for host, snap in newest.items():
        if snap.name in merged_already:
            print(f"  {snap.name} — already merged")
            continue
        age_d = (time.time() - snap.stat().st_mtime) / 86400
        print(f"  merging {snap.name}  (host {host}, {age_d:.0f}d old)")
        # A pre-hostname snapshot predates change tracking by months: its rows
        # have no tombstones, so a keyed merge would resurrect everything deleted
        # since. Its append-only memory is still worth the union.
        added = merge_snapshot(live, snap, dry_run, keyed=(host != "legacy"))
        n = sum(added.values())
        total += n
        changed |= {label.split(" ")[0] for label in added}
        if added:
            for t, c in sorted(added.items(), key=lambda kv: -kv[1]):
                print(f"      +{c:<5} {t}")
        else:
            print("      nothing new — already converged")
        if not dry_run:
            live.execute(
                "INSERT OR REPLACE INTO db_sync_state "
                "(snapshot, host, merged_at, rows_added, merge_version) VALUES (?,?,?,?,?)",
                (snap.name, host, time.strftime("%Y-%m-%dT%H:%M:%S"), n, MERGE_VERSION),
            )
            live.commit()

    live.close()
    if total and not dry_run:
        print(f"\n  merged {total} row(s). The nightly embedding_backfill job will")
        print("  embed the new memory so semantic recall picks it up automatically.")
        if invalidate_interest_cache(changed):
            print("  your keep/decline history changed — relevance rebuilds its profile on next use.")
    return total


def status() -> None:
    print(f"  this machine : {HOST}")
    print(f"  live DB      : {paths.db}  ({paths.db.stat().st_size / 1_048_576:.0f} MB)")
    print(f"  snapshots in : {SNAPSHOTS.relative_to(ROOT)}\n")
    snaps = sorted(SNAPSHOTS.glob("metis-*.sqlite"), key=lambda p: p.stat().st_mtime)
    if not snaps:
        print("  (no snapshots yet)")
        return
    for p in snaps:
        age = (time.time() - p.stat().st_mtime) / 86400
        who = "ours" if p.name.startswith(f"metis-{HOST}-") else f"host {_host_of(p)}"
        print(f"    {p.name:<44} {p.stat().st_size / 1_048_576:>5.0f} MB  {age:>4.1f}d  {who}")

    con = _connect(paths.db, readonly=True)
    keyed, union = plan_tables(con), union_tables(con)
    con.close()
    print(f"\n  synced by key ({len(keyed)}): {', '.join(sorted(keyed))}")
    print(f"\n  synced as append-only union ({len(union)}): {', '.join(union)}")
    print("\n  NOT merged (by design):")
    for what, why in SKIPPED.items():
        print(f"    {what:<24} {why}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--import-only", action="store_true")
    ap.add_argument("--export-only", action="store_true")
    a = ap.parse_args()

    if a.status:
        status()
        return 0

    if not a.dry_run and paths.db.exists():
        # Before the export, so the snapshot carries sync_meta / sync_tombstones.
        con = _connect(paths.db)
        fixed = repair_null_ids(con)
        if fixed:
            print(f"── repaired {fixed} row(s) that had lost their id ──")
        install_change_tracking(con)
        con.close()

    if not a.import_only:
        print("── export ──")
        export_snapshot()
    if not a.export_only:
        print("── merge ──")
        import_snapshots(dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
