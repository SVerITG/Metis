"""metis_sync — one Metis database, the same on every computer.

WHY THIS REPLACED THE APPEND-ONLY MERGE
    The first sync unioned fourteen "append-only" tables and nothing else. Tasks,
    projects, Today verdicts, library state, preferences and every table added
    later never travelled, edits arrived as duplicates, deletions never arrived at
    all, and rows with a TEXT id came across with a NULL id. Each computer slowly
    became its own Metis.

THE MODEL — a primary, and secondaries that rebase onto it (like git)
    * One computer is the PRIMARY (`--make-primary`, recorded in the shared
      folder). On a conflict the primary wins; everything else is merged.
    * Each computer publishes a finished snapshot of every synced table to the
      shared (OneDrive) folder. The live database never goes there — OneDrive
      corrupted it once by copying the .sqlite/-wal/-shm trio mid-write.
    * The PRIMARY merges each secondary's newest snapshot THREE-WAY: against the
      primary snapshot that secondary was based on, it can tell what the
      secondary inserted, changed and deleted, field by field.
    * A SECONDARY rebases: it takes the primary's newest snapshot, replays its
      own changes made since the snapshot the primary last merged, and makes its
      live database equal to the result, in place, in one transaction.
    After one round trip both databases hold the same rows under the SAME ids,
    so every implicit reference (a verdict on paper 412, a plan occurrence of
    plan 9) points at the same thing on both machines.

IDS
    Integer ids are kept. Only when both computers inserted into the same table
    between two syncs can an id collide; then the secondary's row is renumbered,
    the renumbering is recorded (_sync_remap) and shipped with the primary's
    snapshot, and the known references to it (REFS) are rewritten.

WHAT DOES NOT SYNC
    Derived indexes that each machine rebuilds from synced sources (PDF chunks,
    embeddings, the file inventory) and genuinely machine-local state (job log,
    tracked filesystem paths, applied-migration ledger). See LOCAL_TABLES.

NO BASE?
    The first time two diverged databases meet there is no common snapshot. The
    merge then runs as a UNION: rows are matched by id, by a UNIQUE key, or by
    content; the primary's values win; a field the primary never set (NULL, '' or
    the column default) is filled from the secondary. Deletions cannot travel in
    this mode — there is nothing to say a missing row was deleted.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import tempfile
import time
import uuid
import zlib
from dataclasses import dataclass, field
from pathlib import Path

FORMAT = 2
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYNC_DIR = ROOT / "system" / "app" / "data" / "cloud-backups"  # OneDrive-synced
PRIMARY_FILE = "sync-primary.txt"
SNAP_PREFIX = "sync-"
KEEP_OWN = 8          # own snapshots kept (plus any the other side still needs)
STALE_HOURS = 72      # the other computer is "not reaching us" after this
PRIMARY_ACTIVE_HOURS = 6

# ── What never syncs ─────────────────────────────────────────────────────────
LOCAL_TABLES = {
    "jobs_log",            # this machine's scheduler log
    "tracked_files",       # absolute filesystem paths
    "_schema_migrations",  # which migrations ran HERE
    "tool_guard_log",      # local audit log
    "news_image_cache",    # cache
    "db_sync_state",       # the old merger's ledger
    # Derived from files that already sync through OneDrive; each machine's
    # library_index / embedding_backfill jobs rebuild them.
    "pdf_chunks", "pdf_index_state", "pdf_title_aliases",
    "library_inventory", "library_fulltext", "library_duplicates",
    "office_documents",
}
LOCAL_PREFIXES = ("sqlite_", "_sync_", "vec_")

# ── Preference FILES that travel inside the snapshot ─────────────────────────
# Gitignored personal settings: git never carries them, and OneDrive only does if
# the whole repo folder happens to sync on both machines. Small, so they ride
# along. system/.env is deliberately absent — it holds API keys.
SYNC_FILES = [
    "system/config/user-config.yaml",
    "system/config/user-preferences.json",
    "system/config/thinking-profile.yaml",
    "system/config/metis-learned.md",
    "system/config/metis-persona.md",
    "system/config/feature-backlog.md",
    "system/config/domain-overrides.local.json",
    "system/config/session-log.md",
    "system/config/local/*",
]
MAX_FILE_BYTES = 2_000_000

# ── Content folders: too large to carry, so they are CHECKED, not carried ────
# Each snapshot lists what these folders hold; the other computer reports what
# it is missing — the difference between "OneDrive syncs it" and knowing it did.
MANIFEST_ROOTS = [
    "knowledge/courses", "knowledge/library", "inputs/literature", "projects",
    "journal", "outputs", "backgrounds", "agents",
]
MANIFEST_MAX = 60_000

# ── Columns that change after a row is written (not part of its identity) ────
MUTABLE_GENERIC = {
    "status", "state", "updated_at", "modified_at", "seen_at", "read_at",
    "state_at", "reviewed_at", "last_seen", "last_seen_at", "last_applied_at",
    "last_delivered_at", "last_synced", "archived", "starred", "dismissed",
    "is_read", "hits", "delivered", "pin_order", "crucial", "note", "notes",
    "tags", "output_path", "input_tokens", "output_tokens", "model",
    "reviewer_note", "completed_at", "done_at", "next_review", "interval_days",
    "ease_factor", "repetitions", "relevance", "score", "abstract",
    "zotero_version", "zotero_key", "collection",
}
# A paper is the same paper by DOI, else Zotero key, else title.
NATURAL_KEY = {
    "literature_metadata": ("doi", "zotero_key", "title"),
    "new_publications": ("doi", "url", "title"),
}

# ── Implicit integer references (no table declares a FOREIGN KEY) ────────────
# (table, column, target table, (discriminator column, value) or None).
# The target id is its rowid. Used to rewrite references when a row is renumbered.
REFS = [
    ("agent_spans", "run_id", "agent_runs", None),
    ("course_topics", "course_id", "courses", None),
    ("day_plan_occurrence", "plan_id", "day_plan", None),
    ("news_thread_items", "brief_ref", "news_briefs", None),
    ("reading_stack", "item_id", "literature_metadata", ("kind", "paper")),
    ("library_shelf_items", "item_id", "new_publications", ("kind", "paper")),
]

FINAL_STATUSES = {"done", "completed", "complete", "ok", "error", "failed",
                  "cancelled", "closed", "archived", "dismissed"}


def host_name() -> str:
    # METIS_SYNC_HOST: for tests, or two computers that share a hostname.
    raw = os.environ.get("METIS_SYNC_HOST") or platform.node()
    return "".join(c if c.isalnum() else "-" for c in raw) or "unknown"


def sync_dir() -> Path:
    return Path(os.environ.get("METIS_SYNC_DIR") or DEFAULT_SYNC_DIR)


# ═════════════════════════════════════════════════════════════════════════════
# Table description
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Table:
    name: str
    sql: str
    cols: list[str]
    types: dict[str, str]
    defaults: dict[str, str | None]
    pk: list[str]
    has_rowid: bool
    intkey: bool                      # the row's key IS its rowid
    uniques: list[tuple[str, ...]] = field(default_factory=list)

    @property
    def rowid_alias(self) -> str | None:
        """The INTEGER PRIMARY KEY column that aliases rowid, if any."""
        if self.intkey and self.pk:
            return self.pk[0]
        return None


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def synced_tables(con: sqlite3.Connection, schema: str = "main") -> dict[str, str]:
    rows = con.execute(
        f"SELECT name, sql FROM {schema}.sqlite_master WHERE type='table'").fetchall()
    virtual = [n for n, s in rows if (s or "").upper().startswith("CREATE VIRTUAL")]
    out = {}
    for n, s in rows:
        if n in LOCAL_TABLES or n.startswith(LOCAL_PREFIXES):
            continue
        if n in virtual or any(n.startswith(v + "_") for v in virtual):
            continue
        if not s:
            continue
        out[n] = s
    return out


def describe(con: sqlite3.Connection, schema: str, name: str, sql: str) -> Table:
    info = con.execute(f"PRAGMA {schema}.table_info({_q(name)})").fetchall()
    cols = [r[1] for r in info]
    types = {r[1]: (r[2] or "").upper() for r in info}
    defaults = {r[1]: r[4] for r in info}
    pk = [r[1] for r in sorted((r for r in info if r[5]), key=lambda r: r[5])]
    has_rowid = "WITHOUT ROWID" not in (sql or "").upper()
    intkey = has_rowid and (not pk or (len(pk) == 1 and types[pk[0]] == "INTEGER"))
    uniques = []
    for idx in con.execute(f"PRAGMA {schema}.index_list({_q(name)})").fetchall():
        # (seq, name, unique, origin, partial)
        if idx[2] and idx[3] != "pk" and not idx[4]:
            icols = [r[2] for r in con.execute(
                f"PRAGMA {schema}.index_info({_q(idx[1])})").fetchall()]
            if icols and all(c in cols for c in icols):
                uniques.append(tuple(icols))
    return Table(name, sql, cols, types, defaults, pk, has_rowid, intkey, uniques)


def _default_literal(d: str | None):
    if d is None:
        return None
    d = d.strip()
    if d.startswith("("):
        return None
    if len(d) >= 2 and d[0] == d[-1] == "'":
        return d[1:-1]
    return d


def is_unset(value, default) -> bool:
    if value is None or value == "":
        return True
    lit = _default_literal(default)
    return lit is not None and str(value) == lit


def identity_cols(t: Table, cols: list[str]) -> list[str]:
    return [c for c in cols
            if c not in t.pk and c not in MUTABLE_GENERIC]


def fingerprint(row: dict, cols: list[str]) -> str:
    payload = json.dumps([("" if row.get(c) is None else str(row.get(c))) for c in cols],
                         ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def natural_key(table: str, row: dict) -> str | None:
    for c in NATURAL_KEY.get(table, ()):
        v = row.get(c)
        if v is not None and str(v).strip():
            return f"{c}:{str(v).strip().lower()}"
    return None


# ═════════════════════════════════════════════════════════════════════════════
# Row loading
# ═════════════════════════════════════════════════════════════════════════════

RID = "__rid"


def load_rows(con: sqlite3.Connection, schema: str, t: Table, cols: list[str]) -> list[dict]:
    sel = ",".join(_q(c) for c in cols)
    if t.has_rowid:
        sql = f"SELECT rowid AS {RID}, {sel} FROM {schema}.{_q(t.name)}"
    else:
        sql = f"SELECT {sel} FROM {schema}.{_q(t.name)}"
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def row_key(t: Table, row: dict):
    if t.intkey:
        return row[RID]
    return tuple(row.get(c) for c in t.pk)


def _ref_rules_for(table: str):
    return [r for r in REFS if r[0] == table]


def translate_refs(table: str, row: dict, remap: dict[str, dict]) -> dict:
    """Rewrite implicit integer references through `remap` (target → {old: new})."""
    for _tbl, col, target, disc in _ref_rules_for(table):
        if col not in row or target not in remap or not remap[target]:
            continue
        if disc and str(row.get(disc[0])) != disc[1]:
            continue
        v = row[col]
        try:
            old = int(v)
        except (TypeError, ValueError):
            continue
        new = remap[target].get(old)
        if new is not None and new != old:
            row = dict(row)
            row[col] = str(new) if isinstance(v, str) else new
    return row


def table_order(names) -> list[str]:
    """Reference targets before the tables that point at them."""
    names = list(names)
    targets = {r[2] for r in REFS}
    return sorted(names, key=lambda n: (0 if n in targets else 1, n))


# ═════════════════════════════════════════════════════════════════════════════
# The merge
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class MergeStats:
    inserted: dict = field(default_factory=dict)
    updated: dict = field(default_factory=dict)
    deleted: dict = field(default_factory=dict)
    renumbered: dict = field(default_factory=dict)
    matched: dict = field(default_factory=dict)

    def bump(self, kind: str, table: str, n: int = 1):
        d = getattr(self, kind)
        d[table] = d.get(table, 0) + n

    def total(self) -> int:
        return sum(sum(d.values()) for d in
                   (self.inserted, self.updated, self.deleted))

    def lines(self) -> list[str]:
        out = []
        for kind in ("inserted", "updated", "deleted", "renumbered", "matched"):
            d = getattr(self, kind)
            if d:
                parts = ", ".join(f"{t} {n}" for t, n in sorted(d.items(), key=lambda kv: -kv[1])[:8])
                out.append(f"{kind:<10} {sum(d.values()):>6}  ({parts})")
        return out


def _ensure_table(con, schema: str, name: str, sql: str):
    exists = con.execute(
        f"SELECT 1 FROM {schema}.sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    if exists:
        return
    m = re.match(r"\s*CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?", sql, re.I)
    body = sql[m.end():] if m else sql
    # body starts with the (possibly quoted) table name
    nm = re.match(r'\s*("(?:[^"]|"")+"|\[[^\]]+\]|`[^`]+`|\w+)', body)
    rest = body[nm.end():] if nm else body
    con.execute(f"CREATE TABLE {schema}.{_q(name)}{rest}")


def _ensure_columns(con, schema: str, dst: Table, src: Table) -> Table:
    added = False
    for c in src.cols:
        if c not in dst.cols:
            typ = src.types.get(c, "")
            con.execute(f"ALTER TABLE {schema}.{_q(dst.name)} ADD COLUMN {_q(c)} {typ}")
            added = True
    return describe(con, schema, dst.name, dst.sql) if added else dst


class Merger:
    """Merge THEIRS into LIVE, optionally three-way against BASE.

    All three are schemas attached to one connection; the caller owns the
    transaction. `incoming_remap` translates THEIRS/BASE integer keys first (the
    primary's record of how it renumbered this secondary's rows last time).
    """

    def __init__(self, con: sqlite3.Connection, live: str, theirs: str,
                 base: str | None, incoming_remap: dict[str, dict] | None = None):
        self.con, self.live, self.theirs, self.base = con, live, theirs, base
        self.incoming = incoming_remap or {}
        self.remap: dict[str, dict] = {}          # created by THIS merge
        self.stats = MergeStats()

    # combined view used to translate references
    def _all_remap(self) -> dict[str, dict]:
        out = {t: dict(m) for t, m in self.incoming.items()}
        for t, m in self.remap.items():
            out.setdefault(t, {}).update(m)
        return out

    def run(self) -> MergeStats:
        their_tables = synced_tables(self.con, self.theirs)
        base_tables = synced_tables(self.con, self.base) if self.base else {}
        for name in table_order(their_tables):
            self._merge_table(name, their_tables[name], name in base_tables)
        return self.stats

    def _prep(self, t: Table, rows: list[dict]) -> dict:
        """Translate incoming keys/references; index by key."""
        inc = self.incoming.get(t.name, {})
        allmap = self._all_remap()
        out = {}
        for r in rows:
            if t.intkey and inc and r[RID] in inc:
                r = dict(r)
                r[RID] = inc[r[RID]]
                if t.rowid_alias:
                    r[t.rowid_alias] = r[RID]
            r = translate_refs(t.name, r, allmap)
            out[row_key(t, r)] = r
        return out

    def _merge_table(self, name: str, sql: str, in_base: bool):
        con = self.con
        _ensure_table(con, self.live, name, sql)
        lt = describe(con, self.live, name, sql)
        tt = describe(con, self.theirs, name, sql)
        lt = _ensure_columns(con, self.live, lt, tt)
        cols = [c for c in lt.cols if c in tt.cols]
        bt = describe(con, self.base, name, sql) if (self.base and in_base) else None
        bcols = [c for c in cols if bt and c in bt.cols]

        # Fast path: nothing changed on their side since the base.
        if bt is not None and bcols == cols and self._identical(name, cols, lt):
            return

        theirs = self._prep(tt, load_rows(con, self.theirs, tt, cols))
        base = self._prep(bt, load_rows(con, self.base, bt, bcols)) if bt is not None else None
        live_rows = load_rows(con, self.live, lt, cols)
        live = {row_key(lt, r): r for r in live_rows}
        idx = _IdentityIndex(lt, cols, live_rows)   # built lazily on first lookup

        for k, tr in theirs.items():
            br = base.get(k) if base is not None else None
            if base is not None and br is not None:
                if _same(tr, br, bcols):
                    continue
                self._apply_update(lt, cols, live.get(k), tr, br)
            else:
                if base is not None and k in live and _same(tr, live[k], cols):
                    continue
                self._apply_insert(lt, cols, k, tr, live, idx)

        if base is not None:
            for k, br in base.items():
                if k in theirs:
                    continue
                lr = live.get(k)
                if lr is not None and _same(lr, br, bcols):
                    self._delete(lt, k)
                    self.stats.bump("deleted", name)

    def _identical(self, name: str, cols: list[str], lt: Table) -> bool:
        sel = ",".join(_q(c) for c in cols)
        rid = "rowid, " if lt.has_rowid else ""
        q = (f"SELECT COUNT(*) FROM (SELECT {rid}{sel} FROM {self.theirs}.{_q(name)} "
             f"EXCEPT SELECT {rid}{sel} FROM {self.base}.{_q(name)})")
        q2 = (f"SELECT COUNT(*) FROM (SELECT {rid}{sel} FROM {self.base}.{_q(name)} "
              f"EXCEPT SELECT {rid}{sel} FROM {self.theirs}.{_q(name)})")
        try:
            if self.incoming.get(name):
                return False
            return (self.con.execute(q).fetchone()[0] == 0
                    and self.con.execute(q2).fetchone()[0] == 0)
        except sqlite3.DatabaseError:
            return False

    # ── writes ──────────────────────────────────────────────────────────────
    def _where(self, t: Table, k):
        if t.intkey:
            return "rowid=?", [k]
        return " AND ".join(f"{_q(c)} IS ?" for c in t.pk), list(k)

    def _delete(self, t: Table, k):
        w, p = self._where(t, k)
        self.con.execute(f"DELETE FROM {self.live}.{_q(t.name)} WHERE {w}", p)

    def _set(self, t: Table, k, changes: dict):
        if not changes:
            return
        sets = ", ".join(f"{_q(c)}=?" for c in changes)
        w, p = self._where(t, k)
        self.con.execute(f"UPDATE {self.live}.{_q(t.name)} SET {sets} WHERE {w}",
                         list(changes.values()) + p)

    def _apply_update(self, t: Table, cols, lr, tr, br):
        """Field-level three-way: take their change where we did not change it."""
        if lr is None:
            return  # deleted here — the primary/live side wins
        changes = {}
        for c in cols:
            if c in t.pk:
                continue
            if tr.get(c) != br.get(c) and lr.get(c) == br.get(c):
                changes[c] = tr.get(c)
        if changes:
            self._set(t, row_key(t, lr), changes)
            self.stats.bump("updated", t.name)

    def _fill(self, t: Table, cols, lr, tr):
        """Union rule: live wins; fill only what live never set."""
        changes = {}
        for c in cols:
            if c in t.pk:
                continue
            lv, tv = lr.get(c), tr.get(c)
            if is_unset(lv, t.defaults.get(c)) and not is_unset(tv, t.defaults.get(c)):
                changes[c] = tv
        if changes:
            self._set(t, row_key(t, lr), changes)
            self.stats.bump("updated", t.name)

    def _apply_insert(self, t: Table, cols, k, tr, live: dict, idx: "_IdentityIndex"):
        # Same row already here? (same text id, same UNIQUE key, same content)
        match_key = None
        if not t.intkey and None not in k and k in live:
            match_key = k
        else:
            match_key = idx.find(tr)
        if match_key is None and t.intkey and k in live and _same(tr, live[k], cols):
            match_key = k
        if match_key is not None:
            lr = live[match_key]
            self._fill(t, cols, lr, tr)
            self.stats.bump("matched", t.name)
            if t.intkey and match_key != k:
                self.remap.setdefault(t.name, {})[k] = match_key
            elif t.has_rowid and not t.intkey and lr.get(RID) != tr.get(RID):
                self.remap.setdefault(t.name, {})[tr[RID]] = lr[RID]
            return

        row = dict(tr)
        if not t.intkey and t.pk and any(row.get(c) is None for c in t.pk) and len(t.pk) == 1:
            row[t.pk[0]] = uuid.uuid4().hex[:12]   # a NULL text id from the old merger
        keep_rid = t.has_rowid and row.get(RID) is not None
        if keep_rid:
            taken = self.con.execute(
                f"SELECT 1 FROM {self.live}.{_q(t.name)} WHERE rowid=?", (row[RID],)
            ).fetchone()
            keep_rid = taken is None
        ins_cols = [c for c in cols if not (t.rowid_alias == c)]
        names = ([("rowid")] if keep_rid else []) + [_q(c) for c in ins_cols]
        vals = ([row[RID]] if keep_rid else []) + [row.get(c) for c in ins_cols]
        try:
            cur = self.con.execute(
                f"INSERT INTO {self.live}.{_q(t.name)} ({','.join(names)}) "
                f"VALUES ({','.join('?' for _ in vals)})", vals)
        except sqlite3.IntegrityError:
            # A constraint we could not see (e.g. a partial UNIQUE index).
            # The live row wins; record nothing.
            self.stats.bump("matched", t.name)
            return
        new_rid = cur.lastrowid
        self.stats.bump("inserted", t.name)
        if t.has_rowid and row.get(RID) is not None and new_rid != row[RID]:
            self.remap.setdefault(t.name, {})[row[RID]] = new_rid
            self.stats.bump("renumbered", t.name)
        nk = new_rid if t.intkey else tuple(row.get(c) for c in t.pk)
        stored = dict(row)
        stored[RID] = new_rid
        if t.rowid_alias:
            stored[t.rowid_alias] = new_rid
        live[nk] = stored
        idx.add(stored, nk)


def _same(a: dict, b: dict, cols) -> bool:
    return all(a.get(c) == b.get(c) for c in cols)


class _IdentityIndex:
    """Find a live row that IS the incoming row, though its key differs."""

    def __init__(self, t: Table, cols: list[str], rows: list[dict]):
        self.t = t
        self.uniques = [u for u in t.uniques if all(c in cols for c in u)]
        self.ident = identity_cols(t, cols)
        self.by_unique = [dict() for _ in self.uniques]
        self.by_natural: dict = {}
        self.by_fp: dict = {}
        self._pending = rows
        self._built = False

    def _build(self):
        if not self._built:
            self._built = True
            for r in self._pending:
                self.add(r, row_key(self.t, r))
            self._pending = []

    def _keys(self, r):
        for i, u in enumerate(self.uniques):
            vals = tuple(r.get(c) for c in u)
            if None not in vals:
                yield ("u", i, vals)
        nk = natural_key(self.t.name, r)
        if nk:
            yield ("n", 0, nk)
        elif len(self.ident) >= 2:
            yield ("f", 0, fingerprint(r, self.ident))

    def add(self, r, key):
        if not self._built:
            return  # folded in when the index is first built
        for kind, i, v in self._keys(r):
            if kind == "u":
                self.by_unique[i].setdefault(v, key)
            elif kind == "n":
                self.by_natural.setdefault(v, key)
            else:
                self.by_fp.setdefault(v, key)

    def find(self, r):
        self._build()
        for kind, i, v in self._keys(r):
            hit = (self.by_unique[i] if kind == "u" else
                   self.by_natural if kind == "n" else self.by_fp).get(v)
            if hit is not None:
                return hit
        return None


# ═════════════════════════════════════════════════════════════════════════════
# Mirror: make LIVE equal to a merged target, in place
# ═════════════════════════════════════════════════════════════════════════════

def mirror(con: sqlite3.Connection, src: str, dst: str) -> int:
    """Make every synced table in `dst` equal to `src`, preserving rowids."""
    changed = 0
    for name, sql in synced_tables(con, src).items():
        _ensure_table(con, dst, name, sql)
        st = describe(con, src, name, sql)
        dt = describe(con, dst, name, sql)
        dt = _ensure_columns(con, dst, dt, st)
        cols = [c for c in dt.cols if c in st.cols]
        sel = ",".join(_q(c) for c in cols)
        S, D = f"{src}.{_q(name)}", f"{dst}.{_q(name)}"
        if st.has_rowid and dt.has_rowid:
            n0 = con.total_changes
            con.execute(f"DELETE FROM {D} WHERE rowid NOT IN (SELECT rowid FROM {S})")
            differ = (f"SELECT rowid FROM (SELECT rowid,{sel} FROM {S} "
                      f"EXCEPT SELECT rowid,{sel} FROM {D})")
            # Rows present on both sides are UPDATED, not replaced: a column only
            # this computer has (newer code than the main one) must keep its data.
            con.execute(f"CREATE TEMP TABLE IF NOT EXISTS _sync_differ (rid INTEGER PRIMARY KEY)")
            con.execute("DELETE FROM temp._sync_differ")
            con.execute(f"INSERT INTO temp._sync_differ {differ}")
            try:
                con.execute(
                    f"UPDATE {D} SET ({sel}) = (SELECT {sel} FROM {S} AS s WHERE s.rowid = {D}.rowid) "
                    f"WHERE rowid IN (SELECT rid FROM temp._sync_differ)")
            except sqlite3.IntegrityError:
                # e.g. two rows swapped their text ids — replace instead
                con.execute(
                    f"INSERT OR REPLACE INTO {D} (rowid,{sel}) SELECT rowid,{sel} FROM {S} "
                    f"WHERE rowid IN (SELECT rid FROM temp._sync_differ)")
            con.execute(
                f"INSERT OR REPLACE INTO {D} (rowid,{sel}) SELECT rowid,{sel} FROM {S} "
                f"WHERE rowid IN (SELECT rid FROM temp._sync_differ) "
                f"AND rowid NOT IN (SELECT rowid FROM {D})")
            changed += con.total_changes - n0
        else:
            pk = ",".join(_q(c) for c in dt.pk)
            n0 = con.total_changes
            con.execute(f"DELETE FROM {D} WHERE ({pk}) NOT IN (SELECT {pk} FROM {S})")
            con.execute(f"INSERT OR REPLACE INTO {D} ({sel}) "
                        f"SELECT {sel} FROM {S} EXCEPT SELECT {sel} FROM {D}")
            changed += con.total_changes - n0
    return changed


# ═════════════════════════════════════════════════════════════════════════════
# Local sync state (lives in the live DB, never synced: _sync_ prefix)
# ═════════════════════════════════════════════════════════════════════════════

_STATE_DDL = [
    "CREATE TABLE IF NOT EXISTS _sync_state (key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE IF NOT EXISTS _sync_remap (source TEXT, tbl TEXT, old INTEGER, new INTEGER)",
]


def _state(con, schema="main") -> dict:
    for ddl in _STATE_DDL:
        con.execute(ddl.replace("IF NOT EXISTS ", f"IF NOT EXISTS {schema}."))
    return dict(con.execute(f"SELECT key, value FROM {schema}._sync_state").fetchall())


def _set_state(con, key, value, schema="main"):
    con.execute(f"INSERT OR REPLACE INTO {schema}._sync_state (key, value) VALUES (?,?)",
                (key, value))


# ═════════════════════════════════════════════════════════════════════════════
# Snapshots
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Snap:
    path: Path
    host: str
    stamp: str

    @property
    def name(self) -> str:
        return self.path.name


SNAP_SUFFIX = ".sqlite.gz"


def parse_snap(p: Path) -> Snap | None:
    m = re.match(rf"^{SNAP_PREFIX}(.+)-(\d{{8}}-\d{{6}}-\d{{3}})\.sqlite\.gz$", p.name)
    if not m:
        return None
    return Snap(p, m.group(1), m.group(2))


def list_snaps(d: Path) -> list[Snap]:
    if not d.exists():
        return []
    out = [s for s in (parse_snap(p) for p in d.glob(f"{SNAP_PREFIX}*{SNAP_SUFFIX}")) if s]
    return sorted(out, key=lambda s: s.stamp)


def _cache_dir() -> Path:
    d = Path(os.environ.get("METIS_SYNC_CACHE") or (Path.home() / ".cache" / "metis-sync"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def local_copy(path: Path) -> Path:
    """A decompressed copy of a snapshot on local disk (cached).

    Snapshots travel gzip-compressed — a SQLite file shrinks several-fold, and
    OneDrive uploads every one. They are never opened in the shared folder.
    """
    if not str(path).endswith(".gz"):
        return path
    st = path.stat()
    key = hashlib.sha1(f"{path.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:20]
    out = _cache_dir() / f"{key}.sqlite"
    if not out.exists():
        part = out.with_suffix(".part")
        with gzip.open(path, "rb") as src, open(part, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        os.replace(part, out)
    return out


def prune_cache(max_age_h: float = 48):
    try:
        for f in _cache_dir().glob("*.sqlite"):
            if time.time() - f.stat().st_mtime > max_age_h * 3600:
                f.unlink(missing_ok=True)
    except OSError:
        pass


def read_meta(path: Path) -> dict:
    path = local_copy(path)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return dict(con.execute("SELECT key, value FROM _sync_meta").fetchall())
    except sqlite3.DatabaseError:
        return {}
    finally:
        con.close()


def read_remap(path: Path, source: str | None) -> dict[str, dict]:
    if not source:
        return {}
    path = local_copy(path)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        out: dict[str, dict] = {}
        for tbl, old, new in con.execute(
                "SELECT tbl, old, new FROM _sync_remap WHERE source=?", (source,)):
            out.setdefault(tbl, {})[old] = new
        return out
    except sqlite3.DatabaseError:
        return {}
    finally:
        con.close()


def _stamp() -> str:
    t = time.time()
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(t)) + f"-{int(t * 1000) % 1000:03d}"


def _iter_sync_files(root: Path):
    for pat in SYNC_FILES:
        for f in sorted(root.glob(pat)):
            if f.is_file() and f.stat().st_size <= MAX_FILE_BYTES \
                    and not f.name.endswith((".part", ".tmp")) and "-conflict" not in f.name:
                yield f.relative_to(root).as_posix(), f


def _manifest(root: Path) -> list[tuple[str, int]]:
    out = []
    for r in MANIFEST_ROOTS:
        base = root / r
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if not x.startswith((".", "__pycache__", "node_modules"))]
            for fn in filenames:
                if fn.startswith((".", "~$")):
                    continue
                f = Path(dirpath) / fn
                try:
                    out.append((f.relative_to(root).as_posix(), f.stat().st_size))
                except OSError:
                    continue
                if len(out) >= MANIFEST_MAX:
                    return sorted(out)
    return sorted(out)


def export_snapshot(live: Path, d: Path, host: str, meta: dict,
                    remap_rows: list[tuple] = (), files_root: Path | None = None) -> Path | None:
    """Copy every synced table into a finished file, then publish it atomically.

    Returns None when the content is byte-identical to our last snapshot.
    """
    d.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="metis-sync-") as td:
        tmp = Path(td) / "snap.sqlite"
        con = sqlite3.connect(str(tmp))
        con.execute("ATTACH DATABASE ? AS live", (str(live),))
        con.execute("BEGIN")
        for name, sql in synced_tables(con, "live").items():
            _ensure_table(con, "main", name, sql)
            t = describe(con, "live", name, sql)
            sel = ",".join(_q(c) for c in t.cols)
            if t.has_rowid:
                con.execute(f"INSERT INTO main.{_q(name)} (rowid,{sel}) "
                            f"SELECT rowid,{sel} FROM live.{_q(name)}")
            else:
                con.execute(f"INSERT INTO main.{_q(name)} ({sel}) SELECT {sel} FROM live.{_q(name)}")
        con.execute("CREATE TABLE _sync_remap (source TEXT, tbl TEXT, old INTEGER, new INTEGER)")
        con.executemany("INSERT INTO _sync_remap VALUES (?,?,?,?)",
                        sorted((str(a), str(b), c, e) for a, b, c, e in remap_rows))
        con.execute("CREATE TABLE _sync_files (path TEXT PRIMARY KEY, sha TEXT, content BLOB)")
        con.execute("CREATE TABLE _sync_manifest (path TEXT PRIMARY KEY, size INTEGER)")
        if files_root is not None:
            for rel, f in _iter_sync_files(files_root):
                data = f.read_bytes()
                con.execute("INSERT INTO _sync_files VALUES (?,?,?)",
                            (rel, hashlib.sha256(data).hexdigest(), data))
            con.executemany("INSERT INTO _sync_manifest VALUES (?,?)", _manifest(files_root))
        con.commit()
        con.execute("DETACH DATABASE live")
        # The DATA decides whether to publish, not the metadata. Hashing the
        # metadata too made every merge republish (merged_from changed) and every
        # rebase republish (base changed): a 15-minute ping-pong of uploads with
        # nothing in them.
        digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
        con.execute("CREATE TABLE _sync_meta (key TEXT PRIMARY KEY, value TEXT)")
        con.executemany("INSERT INTO _sync_meta VALUES (?,?)",
                        [(k, "" if v is None else str(v)) for k, v in meta.items()])
        con.commit()
        con.close()

        lcon = sqlite3.connect(str(live), timeout=30)
        try:
            st = _state(lcon)
            if st.get("last_export_digest") == digest and st.get("last_export_name") \
                    and (d / st["last_export_name"]).exists():
                return None
            name = f"{SNAP_PREFIX}{host}-{_stamp()}{SNAP_SUFFIX}"
            part = d / f".{name}.part"
            with open(tmp, "rb") as src, gzip.open(part, "wb", compresslevel=4) as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            os.replace(part, d / name)        # appears complete, never half-written
            _set_state(lcon, "last_export_digest", digest)
            _set_state(lcon, "last_export_name", name)
            _set_state(lcon, "last_export_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
            lcon.commit()
        finally:
            lcon.close()
    return d / name


def prune(d: Path, host: str, keep_names: set[str]):
    mine = [s for s in list_snaps(d) if s.host == host]
    for s in mine[:-KEEP_OWN]:
        if s.name not in keep_names:
            s.path.unlink(missing_ok=True)


# ═════════════════════════════════════════════════════════════════════════════
# Roles
# ═════════════════════════════════════════════════════════════════════════════

def read_primary(d: Path) -> str | None:
    env = os.environ.get("METIS_SYNC_PRIMARY")
    if env:
        return env.strip()
    f = d / PRIMARY_FILE
    if f.exists():
        v = f.read_text(encoding="utf-8").strip()
        return v or None
    return None


def make_primary(d: Path, host: str):
    d.mkdir(parents=True, exist_ok=True)
    (d / PRIMARY_FILE).write_text(host + "\n", encoding="utf-8")


def _connect_live(live: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(live), timeout=60, isolation_level=None)
    con.execute("PRAGMA busy_timeout=60000")
    return con


def _newest_by_host(snaps: list[Snap]) -> dict[str, Snap]:
    out: dict[str, Snap] = {}
    for s in snaps:
        out[s.host] = s  # sorted ascending → last wins
    return out


def is_ready(s: Snap) -> bool:
    """False while OneDrive is still bringing the file in (truncated gzip)."""
    try:
        local_copy(s.path)
        return True
    except (OSError, EOFError, gzip.BadGzipFile, zlib.error):
        return False


def _newest_ready_by_host(snaps: list[Snap]) -> dict[str, Snap]:
    out: dict[str, Snap] = {}
    for s in reversed(snaps):
        if s.host not in out and is_ready(s):
            out[s.host] = s
    return out


@dataclass
class Report:
    role: str = ""
    host: str = ""
    primary: str | None = None
    lines: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    changed: int = 0

    def say(self, s: str):
        self.lines.append(s)

    def problem(self, s: str):
        self.problems.append(s)


def primary_merge(live: Path, d: Path, host: str, rep: Report, files_root: Path | None = None):
    snaps = list_snaps(d)
    newest = _newest_ready_by_host(snaps)
    con = _connect_live(live)
    try:
        st = _state(con)
        for other, snap in newest.items():
            if other == host:
                continue
            key = f"merged:{other}"
            if st.get(key) == snap.name:
                rep.say(f"{other}: newest snapshot already merged ({snap.name})")
                continue
            meta = read_meta(snap.path)
            base_name = meta.get("base") or ""
            incoming: dict[str, dict] = {}
            # If the secondary has not rebased since the last snapshot we merged
            # from it, THAT snapshot is the exact base: the difference is what it
            # did since. Using the older primary snapshot instead would read an
            # edit to a row we merged last time as a brand-new row, and drop it.
            prev = st.get(key)
            if prev and (d / prev).exists() and \
                    (read_meta(d / prev).get("base") or "") == base_name:
                base_name = prev
                incoming = {}
                for t, o, n in con.execute(
                        "SELECT tbl, old, new FROM _sync_remap WHERE source=?", (prev,)):
                    incoming.setdefault(t, {})[o] = n
            base_path = d / base_name if base_name else None
            if base_path is not None and not base_path.exists():
                rep.problem(f"{other}'s snapshot is based on {base_name}, which is gone — "
                            f"merging without a base (deletions on {other} cannot travel)")
                base_path = None
                incoming = {}
            con.execute("ATTACH DATABASE ? AS theirs", (str(local_copy(snap.path)),))
            if base_path:
                con.execute("ATTACH DATABASE ? AS base", (str(local_copy(base_path)),))
            try:
                con.execute("BEGIN IMMEDIATE")
                m = Merger(con, "main", "theirs", "base" if base_path else None, incoming)
                stats = m.run()
                # Cumulative since the secondary last rebased: it still numbers the
                # rows we renumbered last time its own way.
                cum = {t: dict(mp) for t, mp in incoming.items()}
                for t, mp in m.remap.items():
                    cum.setdefault(t, {}).update(mp)
                con.execute("DELETE FROM _sync_remap WHERE source=?", (snap.name,))
                con.executemany(
                    "INSERT INTO _sync_remap (source, tbl, old, new) VALUES (?,?,?,?)",
                    [(snap.name, t, o, n) for t, mp in cum.items() for o, n in mp.items()])
                _set_state(con, key, snap.name)
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
            finally:
                con.execute("DETACH DATABASE theirs")
                if base_path:
                    con.execute("DETACH DATABASE base")
            if files_root is not None:
                merge_files(files_root, snap.path, base_path, True, other, rep)
                check_manifest(files_root, snap.path, other, rep)
            mode = "three-way" if base_path else "union (no common base)"
            rep.say(f"merged {snap.name} from {other} — {mode}")
            for ln in stats.lines():
                rep.say("    " + ln)
            rep.changed += stats.total()
        merged = {k.split(":", 1)[1]: v for k, v in _state(con).items() if k.startswith("merged:")}
        remap_rows = con.execute(
            "SELECT source, tbl, old, new FROM _sync_remap WHERE source IN (%s)"
            % ",".join("?" for _ in merged), list(merged.values())).fetchall() if merged else []
    finally:
        con.close()
    return merged, remap_rows


def secondary_rebase(live: Path, d: Path, host: str, primary: str, rep: Report,
                     files_root: Path | None = None):
    snaps = [s for s in list_snaps(d) if s.host == primary]
    if not snaps:
        rep.problem(f"no snapshot from the main computer ({primary}) has arrived in {d} — "
                    "check that this folder syncs on both machines")
        return
    ready = _newest_ready_by_host(snaps)
    if primary not in ready:
        rep.say("the main computer's snapshot is still arriving — next run")
        return
    newest = ready[primary]
    con = _connect_live(live)
    try:
        st = _state(con)
        if st.get("base") == newest.name:
            rep.say(f"already up to date with the main computer ({newest.name})")
            return
        meta = read_meta(newest.path)
        merged = json.loads(meta.get("merged_from") or "{}")
        ref_name = merged.get(host)
        ref_path = d / ref_name if ref_name else None
        if ref_path is not None and not ref_path.exists():
            rep.problem(f"the main computer merged {ref_name}, which is no longer here — "
                        "rebasing without a base (deletions made here since cannot travel)")
            ref_path = None
        incoming = read_remap(newest.path, ref_name) if ref_path else {}

        with tempfile.TemporaryDirectory(prefix="metis-rebase-") as td:
            tgt = Path(td) / "target.sqlite"
            shutil.copyfile(local_copy(newest.path), tgt)
            con.execute("ATTACH DATABASE ? AS tgt", (str(tgt),))
            if ref_path:
                con.execute("ATTACH DATABASE ? AS base", (str(local_copy(ref_path)),))
            try:
                con.execute("BEGIN IMMEDIATE")
                # Our changes since the snapshot the primary merged → onto the primary.
                m = Merger(con, "tgt", "main", "base" if ref_path else None, incoming)
                stats = m.run()
                changed = mirror(con, "tgt", "main")
                _set_state(con, "base", newest.name)
                _set_state(con, "rebased_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
                con.execute("COMMIT")
            except Exception:
                con.execute("ROLLBACK")
                raise
            finally:
                con.execute("DETACH DATABASE tgt")
                if ref_path:
                    con.execute("DETACH DATABASE base")
        if files_root is not None:
            # Base for files: the snapshot we published that the primary merged.
            merge_files(files_root, newest.path, ref_path, False, primary, rep)
        mode = "three-way" if ref_path else "union (first sync — the main computer wins)"
        rep.say(f"rebased onto {newest.name} — {mode}")
        for ln in stats.lines():
            rep.say("    kept from here: " + ln)
        rep.say(f"    {changed} row change(s) applied to this computer")
        rep.changed += changed
    finally:
        con.close()


def check_freshness(d: Path, host: str, primary: str | None, rep: Report):
    newest = _newest_by_host(list_snaps(d))
    others = {h: s for h, s in newest.items() if h != host}
    if not others:
        rep.problem(f"nothing from another computer has arrived in {d} — "
                    "check that this folder syncs on both machines")
        return
    for h, s in others.items():
        age_h = (time.time() - time.mktime(time.strptime(s.stamp[:15], "%Y%m%d-%H%M%S"))) / 3600
        if age_h > STALE_HOURS:
            rep.problem(f"the newest snapshot from {h} is {age_h / 24:.0f} days old — "
                        "that computer has stopped syncing, or the folder stopped syncing")


def _snap_files(path: Path | None) -> dict[str, tuple[str, bytes]]:
    if path is None:
        return {}
    con = sqlite3.connect(f"file:{local_copy(path)}?mode=ro", uri=True)
    try:
        return {p: (sha, data) for p, sha, data in
                con.execute("SELECT path, sha, content FROM _sync_files")}
    except sqlite3.DatabaseError:
        return {}
    finally:
        con.close()


def _write_atomic(target: Path, data: bytes):
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.sync-tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)


def merge_files(root: Path, theirs: Path, base: Path | None, live_wins: bool,
                their_host: str, rep: Report) -> int:
    """Three-way merge of the preference files, by content hash.

    Their change is taken where ours did not change. When both changed, the
    primary's version stays in place and the other one is kept beside it as
    `<name>.<host>-conflict<ext>` — a preference is never silently thrown away.
    """
    tf, bf = _snap_files(theirs), _snap_files(base)
    n = 0
    for rel, (tsha, tdata) in tf.items():
        target = root / rel
        lsha = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        bsha = bf.get(rel, (None, b""))[0] if base is not None else None
        if lsha == tsha:
            continue
        if base is not None and tsha == bsha:
            continue                                   # only we changed it
        if lsha is None or (base is not None and lsha == bsha):
            _write_atomic(target, tdata)               # only they changed it
            rep.say(f"file updated from {their_host}: {rel}")
            n += 1
            continue
        if live_wins:
            side = target.with_name(f"{target.stem}.{their_host}-conflict{target.suffix}")
            _write_atomic(side, tdata)
            rep.say(f"file changed on both computers: kept this one, saved theirs as {side.name}")
        else:
            side = target.with_name(f"{target.stem}.{host_name()}-conflict{target.suffix}")
            _write_atomic(side, target.read_bytes())
            _write_atomic(target, tdata)
            rep.say(f"file changed on both computers: the main computer's {rel} wins; "
                    f"this computer's version saved as {side.name}")
        n += 1
    return n


def check_manifest(root: Path, theirs: Path, their_host: str, rep: Report):
    """Report content files the other computer has and this one lacks."""
    con = sqlite3.connect(f"file:{local_copy(theirs)}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT path, size FROM _sync_manifest").fetchall()
    except sqlite3.DatabaseError:
        return
    finally:
        con.close()
    missing = [p for p, _ in rows if not (root / p).exists()]
    if missing:
        by_root: dict[str, int] = {}
        for p in missing:
            top = "/".join(p.split("/")[:2])
            by_root[top] = by_root.get(top, 0) + 1
        where = ", ".join(f"{k} {v}" for k, v in sorted(by_root.items(), key=lambda kv: -kv[1])[:4])
        rep.problem(f"{len(missing)} file(s) on {their_host} are not on this computer "
                    f"({where}; e.g. {missing[0]}) — OneDrive is not syncing them here")


def sync(live: Path, d: Path | None = None, host: str | None = None,
         files_root: Path | None = ROOT) -> Report:
    d = d or sync_dir()
    host = host or host_name()
    primary = read_primary(d)
    rep = Report(host=host, primary=primary)
    if not live.exists():
        rep.problem(f"no live database at {live}")
        return rep
    if primary is None:
        rep.role = "unassigned"
        rep.problem("no main computer is set — run `python3 tools/metis-sync-db.py "
                    "--make-primary` on the main computer")
        export_snapshot(live, d, host, {"format": FORMAT, "host": host, "role": "unassigned"},
                        (), files_root)
        return rep

    if host == primary:
        rep.role = "primary"
        merged, remap_rows = primary_merge(live, d, host, rep, files_root)
        p = export_snapshot(live, d, host, {
            "format": FORMAT, "host": host, "role": "primary",
            "merged_from": json.dumps(merged)}, remap_rows, files_root)
        rep.say(f"published {p.name}" if p else "nothing changed since the last snapshot")
        # keep what secondaries still build on
        keep = set()
        for h, s in _newest_by_host(list_snaps(d)).items():
            if h != host:
                b = read_meta(s.path).get("base")
                if b:
                    keep.add(b)
        prune(d, host, keep)
    else:
        rep.role = "secondary"
        secondary_rebase(live, d, host, primary, rep, files_root)
        con = _connect_live(live)
        try:
            base = _state(con).get("base", "")
        finally:
            con.close()
        p = export_snapshot(live, d, host, {
            "format": FORMAT, "host": host, "role": "secondary", "base": base}, (), files_root)
        rep.say(f"published {p.name}" if p else "nothing changed since the last snapshot")
        keep = set()
        prim = [s for s in list_snaps(d) if s.host == primary]
        if prim and files_root is not None:
            check_manifest(files_root, prim[-1].path, primary, rep)
        if prim:
            mf = json.loads(read_meta(prim[-1].path).get("merged_from") or "{}")
            if mf.get(host):
                keep.add(mf[host])
        prune(d, host, keep)
    check_freshness(d, host, primary, rep)
    prune_cache()
    return rep


def primary_recently_active(d: Path | None = None, host: str | None = None,
                            hours: float = PRIMARY_ACTIVE_HOURS) -> bool:
    """True when THIS computer is a secondary and the main one published recently.

    Scheduled content jobs (news scans, library scans, briefs) then run on the
    main computer only, and their results arrive here by sync — instead of both
    machines fetching the same items and colliding.
    """
    d = d or sync_dir()
    host = host or host_name()
    primary = read_primary(d)
    if not primary or primary == host:
        return False
    snaps = [s for s in list_snaps(d) if s.host == primary]
    if not snaps:
        return False
    age_h = (time.time() - time.mktime(time.strptime(snaps[-1].stamp[:15], "%Y%m%d-%H%M%S"))) / 3600
    return age_h < hours
