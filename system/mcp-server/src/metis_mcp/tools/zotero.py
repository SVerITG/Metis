"""Zotero library connector — sync, search, and AI-powered organisation.

Supports Zotero via pyzotero. Mendeley users are guided to export BibTeX
and import via import_bibtex_library().

Config is read from environment variables (set in metis/system/.env):
  ZOTERO_API_KEY  — Zotero Web API key
  ZOTERO_USER_ID  — numeric Zotero user ID
  ZOTERO_GROUP_ID — optional, for group libraries
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime

log = logging.getLogger("metis.zotero")
from pathlib import Path
from typing import Optional

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.tools.guardrails import sanitize_external

# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------

_LIT_EXTRA_COLS = {
    "abstract":        "TEXT DEFAULT ''",
    "journal":         "TEXT DEFAULT ''",
    "item_type":       "TEXT DEFAULT ''",
    "url":             "TEXT DEFAULT ''",
    "zotero_key":      "TEXT DEFAULT ''",
    "zotero_version":  "INTEGER DEFAULT 0",
    "collection":      "TEXT DEFAULT ''",
    "library_source":  "TEXT DEFAULT 'manual'",
}


def _ensure_lit_schema(conn) -> None:
    existing = {r[1] for r in conn.execute("PRAGMA table_info(literature_metadata)")}
    for col, dtype in _LIT_EXTRA_COLS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE literature_metadata ADD COLUMN {col} {dtype}")


_SYNC_DDL = """
CREATE TABLE IF NOT EXISTS zotero_sync_state (
    id           INTEGER PRIMARY KEY,
    last_version INTEGER DEFAULT 0,
    last_synced  TEXT,
    item_count   INTEGER DEFAULT 0
)
"""


def _get_last_version(conn) -> int:
    conn.execute(_SYNC_DDL)
    row = conn.execute("SELECT last_version FROM zotero_sync_state LIMIT 1").fetchone()
    return row["last_version"] if row else 0


def _set_last_version(conn, version: int, item_count: int) -> None:
    conn.execute(_SYNC_DDL)
    conn.execute("DELETE FROM zotero_sync_state")
    conn.execute(
        "INSERT INTO zotero_sync_state (last_version, last_synced, item_count) VALUES (?,?,?)",
        (version, datetime.now().isoformat(), item_count),
    )


# ---------------------------------------------------------------------------
# Zotero helpers
# ---------------------------------------------------------------------------

def _get_zotero_client():
    """Return a pyzotero Zotero client. Raises if not configured."""
    try:
        from pyzotero import zotero as pyz
    except ImportError:
        raise RuntimeError("pyzotero not installed — run: pip install pyzotero")

    # Load .env if present
    env_path = paths.root / "system" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    api_key = os.environ.get("ZOTERO_API_KEY", "")
    user_id = os.environ.get("ZOTERO_USER_ID", "")
    group_id = os.environ.get("ZOTERO_GROUP_ID", "")

    if not api_key:
        raise RuntimeError(
            "ZOTERO_API_KEY not set. Add it to metis/system/.env:\n"
            "  ZOTERO_API_KEY=your_key\n"
            "  ZOTERO_USER_ID=your_numeric_id\n"
            "Get your key at: https://www.zotero.org/settings/keys"
        )
    if not user_id and not group_id:
        raise RuntimeError(
            "ZOTERO_USER_ID not set. Add it to metis/system/.env:\n"
            "  ZOTERO_USER_ID=your_numeric_id\n"
            "Find it at: https://www.zotero.org/settings/keys"
        )

    if group_id:
        zot = pyz.Zotero(group_id, "group", api_key)
    else:
        zot = pyz.Zotero(user_id, "user", api_key)

    # Corporate TLS-inspecting proxy.
    #
    # ITG's network terminates TLS with its own CA, so httpx — which verifies
    # against certifi's bundle, not the system store — fails with
    # "self-signed certificate in certificate chain" while urllib succeeds
    # (verified 2026-08-21: urllib reached api.zotero.org fine, httpx did not).
    #
    # This used to be handled with verify=False, which disables verification
    # ENTIRELY and sends the API key over a connection nothing has authenticated.
    # The system CA bundle already contains the corporate root — that is why
    # urllib works — so pointing httpx at it fixes the problem while KEEPING
    # verification. verify=False remains only as a last resort, and now says so
    # in the log rather than being silent about it.
    try:
        import httpx

        client = None
        for ca in ("/etc/ssl/certs/ca-certificates.crt",
                   "/usr/lib/ssl/cert.pem",
                   "/etc/pki/tls/certs/ca-bundle.crt"):
            if os.path.exists(ca):
                try:
                    client = httpx.Client(verify=ca, headers=zot.default_headers())
                    break
                except Exception:
                    client = None
        if client is None:
            log.warning(
                "Zotero: no usable system CA bundle found; falling back to "
                "UNVERIFIED TLS. The API key will be sent over a connection "
                "that has not been authenticated.")
            client = httpx.Client(verify=False, headers=zot.default_headers())
        zot.client = client
    except Exception:
        pass

    return zot


def _item_to_row(item: dict) -> dict:
    """Extract a flat dict from a Zotero item for insertion into literature_metadata."""
    data = item.get("data", {})
    meta = item.get("meta", {})

    # Authors: "Lastname, F.; Lastname2, F2."
    creators = data.get("creators", [])
    author_parts = []
    for c in creators:
        if c.get("lastName"):
            name = c["lastName"]
            if c.get("firstName"):
                name += f", {c['firstName'][0]}."
            author_parts.append(name)
        elif c.get("name"):
            author_parts.append(c["name"])
    authors = "; ".join(author_parts[:8])

    # Year from date field
    raw_date = data.get("date", "") or ""
    year_match = re.search(r"\b(19|20)\d{2}\b", raw_date)
    year = int(year_match.group()) if year_match else None

    # Tags: comma-joined
    tags = ",".join(t.get("tag", "") for t in data.get("tags", [])[:12])

    # Collection names from meta (pyzotero includes them)
    collections = data.get("collections", [])

    return {
        "title": (data.get("title") or "")[:500],
        "authors": authors[:300],
        "year": year,
        "source": data.get("publicationTitle") or data.get("bookTitle") or data.get("publisher") or "",
        "journal": data.get("publicationTitle") or "",
        "tags": tags,
        "doi": data.get("DOI") or "",
        "abstract": (data.get("abstractNote") or "")[:2000],
        "url": data.get("url") or data.get("DOI") and f"https://doi.org/{data['DOI']}" or "",
        "item_type": data.get("itemType") or "",
        "zotero_key": data.get("key") or "",
        "zotero_version": item.get("version") or 0,
        "library_source": "zotero",
        "created_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

def _upsert_lit_row(conn, row: dict) -> str:
    """Insert or update one literature_metadata row keyed by zotero_key.

    Returns 'added' or 'updated'. Shared by the Web-API sync and the local
    zotero.sqlite reader so both behave identically.

    INGESTION CHOKEPOINT: an abstract is third-party text fetched from a
    reference manager — the classic poisoned-paper vector. Both Zotero paths
    funnel through here, so probing here covers both.
    """
    row = dict(row)
    if row.get("abstract"):
        row["abstract"] = sanitize_external(
            row["abstract"], f"zotero-abstract:{row.get('title', '')[:60]}"
        )

    existing = conn.execute(
        "SELECT id FROM literature_metadata WHERE zotero_key = ?",
        (row["zotero_key"],),
    ).fetchone() if row.get("zotero_key") else None

    if existing:
        conn.execute(
            """UPDATE literature_metadata SET
               title=?, authors=?, year=?, source=?, journal=?, tags=?, doi=?,
               abstract=?, url=?, item_type=?, zotero_version=?, library_source=?
               WHERE zotero_key=?""",
            (row["title"], row["authors"], row["year"], row["source"], row["journal"],
             row["tags"], row["doi"], row["abstract"], row["url"], row["item_type"],
             row["zotero_version"], row["library_source"], row["zotero_key"]),
        )
        return "updated"

    conn.execute(
        """INSERT INTO literature_metadata
           (title, authors, year, source, journal, tags, doi, abstract,
            url, item_type, zotero_key, zotero_version, library_source, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (row["title"], row["authors"], row["year"], row["source"], row["journal"],
         row["tags"], row["doi"], row["abstract"], row["url"], row["item_type"],
         row["zotero_key"], row["zotero_version"], row["library_source"], row["created_at"]),
    )
    return "added"


def _check_write_access(zot) -> tuple[bool, str]:
    """Does this key allow writing to the target library? Returns (ok, message).

    The whole Zotero integration was READ-ONLY until now, and the configured key
    returns 403 on a permissions check — so we verify write access explicitly and
    fail with a clear, actionable message rather than a cryptic API error.
    """
    try:
        import httpx

        key = os.environ.get("ZOTERO_API_KEY", "")
        r = httpx.get(
            "https://api.zotero.org/keys/current",
            headers={"Zotero-API-Key": key, "Zotero-API-Version": "3"},
            timeout=15, verify=False,
        )
        if r.status_code != 200:
            return False, (
                f"Zotero key check failed (HTTP {r.status_code}). The key is likely "
                "read-only, expired, or invalid. Generate a WRITE-enabled key at "
                "zotero.org → Settings → Security → Applications → New Private Key "
                "(tick 'Allow write access'), then put it in system/.env as "
                "ZOTERO_API_KEY."
            )
        access = r.json().get("access", {})
        can_write = bool(access.get("user", {}).get("write") or access.get("groups"))
        if not can_write:
            return False, (
                "This Zotero key is READ-ONLY. Regenerate it with 'Allow write "
                "access' ticked and update ZOTERO_API_KEY in system/.env."
            )
        return True, "write access confirmed"
    except Exception as exc:
        return False, f"could not verify Zotero write access: {type(exc).__name__}: {exc}"


@app.tool()
async def push_to_zotero(dry_run: bool = True, limit: int = 50) -> list[TextContent]:
    """Push local library papers that aren't in Zotero yet UP to your Zotero library.

    The complement to sync_zotero_library (which only pulls DOWN). Finds
    literature_metadata rows that did not come from Zotero (no zotero_key) and
    creates them as items in your Zotero library, so papers Metis ingested — e.g.
    open-access reports added to a knowledge layer — end up in Zotero too.

    Args:
        dry_run: When True (default), report exactly what WOULD be created without
            writing anything. Always review the dry run before a real push.
        limit: Max items to push in one call.

    Returns:
        A summary: how many candidates, and either the dry-run preview or the
        create result. Requires a WRITE-enabled ZOTERO_API_KEY.
    """
    from metis_mcp.config import paths as _paths

    with connect(_paths.db) as conn:
        _ensure_lit_schema(conn)
        rows = conn.execute(
            "SELECT id, title, authors, year, doi, url, item_type, abstract, tags "
            "FROM literature_metadata "
            "WHERE COALESCE(zotero_key,'') = '' AND COALESCE(title,'') != '' "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    candidates = [dict(r) for r in rows]
    if not candidates:
        return [TextContent(type="text", text="Nothing to push — every local paper is already in Zotero.")]

    def _to_zotero_item(r: dict) -> dict:
        itype = (r.get("item_type") or "").strip() or "report"
        # Map free-text item types to valid Zotero types; default to 'report'
        # (most of the ph-background layer is WHO/agency reports).
        valid = {"journalArticle", "report", "book", "bookSection", "document",
                 "webpage", "preprint", "conferencePaper", "thesis"}
        if itype not in valid:
            itype = "report"
        creators = []
        authors = (r.get("authors") or "").strip()
        if authors and authors.lower() != "unknown":
            for name in re.split(r";|,| and ", authors)[:20]:
                name = name.strip()
                if name:
                    creators.append({"creatorType": "author", "name": name})
        item = {
            "itemType": itype,
            "title": r.get("title") or "",
            "creators": creators,
            "date": str(r.get("year") or ""),
            "url": r.get("url") or "",
            "abstractNote": r.get("abstract") or "",
            "tags": [{"tag": t.strip()} for t in (r.get("tags") or "").split(",") if t.strip()],
        }
        if r.get("doi"):
            item["DOI"] = r["doi"]
        return item

    items = [_to_zotero_item(r) for r in candidates]

    if dry_run:
        preview = "\n".join(f"  • [{it['itemType']}] {it['title'][:80]}" for it in items[:limit])
        return [TextContent(type="text", text=(
            f"DRY RUN — {len(items)} paper(s) would be pushed to Zotero:\n{preview}\n\n"
            "Nothing was written. Re-run with dry_run=False to create these in Zotero "
            "(requires a write-enabled key)."
        ))]

    # Real push — verify write access first.
    try:
        zot = _get_zotero_client()
    except RuntimeError as exc:
        return [TextContent(type="text", text=str(exc))]
    ok, msg = _check_write_access(zot)
    if not ok:
        return [TextContent(type="text", text=f"Cannot push to Zotero: {msg}")]

    created, failed = 0, 0
    key_by_title: dict[str, str] = {}
    # Zotero create_items takes up to 50 at a time.
    for i in range(0, len(items), 50):
        batch = items[i:i + 50]
        try:
            resp = zot.create_items(batch)
            for idx, info in (resp.get("successful") or {}).items():
                created += 1
                key_by_title[info["data"]["title"]] = info["key"]
            failed += len(resp.get("failed") or {})
        except Exception as exc:
            failed += len(batch)
            log.warning("push_to_zotero: batch failed: %s", exc)

    # Record the new Zotero keys locally so we don't push duplicates next time.
    if key_by_title:
        with connect(_paths.db) as conn:
            for title, zkey in key_by_title.items():
                conn.execute(
                    "UPDATE literature_metadata SET zotero_key=? WHERE title=? AND COALESCE(zotero_key,'')=''",
                    (zkey, title),
                )
            conn.commit()

    return [TextContent(type="text", text=(
        f"Pushed to Zotero: {created} created, {failed} failed. "
        "Local rows tagged with their new Zotero keys so they won't be pushed again."
    ))]


# Placeholder values shipped in system/.env.example. A key that is literally
# "your-zotero-api-key-here" is NOT a configured key, but every code path treated
# a non-empty string as configured — so the web API returned 403 on every call and
# the failure was swallowed. Measured 2026-08-21: both Zotero variables in this
# install were still the placeholders, which is why the web sync had "not run"
# since May. It had never run.
_PLACEHOLDER_MARKERS = ("your-", "-here", "changeme", "xxx", "todo")


def zotero_credential_state() -> dict:
    """What Zotero access is actually available? Never raises.

    Returns {web: bool, local: str, reason: str} so a surface can say which of the
    two sync routes will work, instead of showing a Sync button that 403s.

    The distinction matters because the two routes have different capabilities:
      · LOCAL  (zotero.sqlite) — read only, no credentials, works offline. This is
        what actually imported the existing items.
      · WEB    (API key) — required for WRITING back to Zotero. Nothing can push
        an item without it, because the local database belongs to Zotero and must
        not be written by anything else.
    """
    import os as _os
    from pathlib import Path as _P

    rc = _os.environ.get("METIS_RC_ROOT", "")
    if rc:
        envp = _P(rc) / "system" / ".env"
        if envp.exists():
            for line in envp.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    _os.environ.setdefault(k.strip(), v.strip())

    key = (_os.environ.get("ZOTERO_API_KEY") or "").strip()
    uid = (_os.environ.get("ZOTERO_USER_ID") or "").strip()
    gid = (_os.environ.get("ZOTERO_GROUP_ID") or "").strip()

    def placeholder(v: str) -> bool:
        low = v.lower()
        return not v or any(m in low for m in _PLACEHOLDER_MARKERS)

    local = _find_local_zotero_db() or ""

    if placeholder(key):
        return {"web": False, "local": local,
                "reason": "ZOTERO_API_KEY in system/.env is still the placeholder"}
    if placeholder(uid) and placeholder(gid):
        return {"web": False, "local": local,
                "reason": "ZOTERO_USER_ID in system/.env is still the placeholder"}
    return {"web": True, "local": local, "reason": ""}


def sync_zotero_into_db(conn, full: bool = False) -> int:
    """Pull Zotero into literature_metadata on an existing connection.

    A PLAIN function, deliberately: `sync_zotero_library` is an async MCP tool
    that returns TextContent, so the dashboard's scheduler could not call it and
    a THIRD copy of this logic had been written inline in
    `routers/knowledge.py::trigger_zotero_sync`. Three implementations of one
    sync is three chances for them to disagree about what a "collection" is.

    This is now the single implementation. It exists because the sync needed a
    scheduled caller: the library had gone unsynced from 2026-05-21 to 2026-08-21
    — three months — precisely because a manual button is only pressed by someone
    who already suspects it is stale.

    Returns the number of items added + updated. Raises on API failure so the
    caller can log it; returning 0 on an error would be indistinguishable from a
    genuinely quiet library.
    """
    state = zotero_credential_state()
    if not state["web"]:
        # Explicit, not a 403 swallowed three frames up. Callers log this.
        raise RuntimeError(
            f"Zotero web API not configured — {state['reason']}. "
            "Reading still works via the local zotero.sqlite; WRITING to Zotero "
            "needs a real key from https://www.zotero.org/settings/keys")
    zot = _get_zotero_client()          # raises RuntimeError if unconfigured

    # This function reads rows BY NAME (`row["last_version"]`), so a caller that
    # hands over a plain sqlite3 connection gets
    #     TypeError: tuple indices must be integers or slices, not str
    # The MCP callers happen to set row_factory; the scheduler did not, so the
    # web sync raised, the caller caught it, logged a warning nobody was
    # watching, and silently fell back to the local route — reporting
    # "Zotero: 512 (local)" as though the web API were unconfigured. Being the
    # single shared implementation means not depending on how each caller
    # happened to build its connection.
    conn.row_factory = sqlite3.Row

    _ensure_lit_schema(conn)
    last_version = 0 if full else _get_last_version(conn)

    items = (zot.everything(zot.items()) if (full or last_version == 0)
             else zot.everything(zot.items(since=last_version)))
    if not items:
        return 0

    touched = 0
    for item in items:
        data = item.get("data", {})
        if data.get("itemType") in ("attachment", "note"):
            continue
        row = _item_to_row(item)
        if not row["title"]:
            continue
        _upsert_lit_row(conn, row)
        touched += 1

    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM literature_metadata WHERE library_source='zotero'"
        ).fetchone()[0]
        _set_last_version(conn, zot.last_modified_version(), total)
    except Exception:
        # A failed version stamp means the next sync re-reads more than it needed
        # to. Wasteful, not wrong — and far better than losing the items just
        # written because the bookkeeping call failed.
        pass
    conn.commit()
    return touched


@app.tool()
async def sync_zotero_library(full: bool = False) -> list[TextContent]:
    """Sync the Zotero library into Metis literature_metadata.

    Performs an incremental sync by default — only fetches items changed since
    the last sync. Pass full=True to re-sync everything.

    Requires ZOTERO_API_KEY and ZOTERO_USER_ID in metis/system/.env.

    Args:
        full: If True, re-sync all items regardless of last sync state.
    """
    try:
        zot = _get_zotero_client()
    except RuntimeError as e:
        return [TextContent(type="text", text=f"Zotero not configured:\n{e}")]

    with connect(paths.db) as conn:
        _ensure_lit_schema(conn)
        last_version = 0 if full else _get_last_version(conn)

    try:
        if full or last_version == 0:
            items = zot.everything(zot.items())
        else:
            items = zot.everything(zot.items(since=last_version))
    except Exception as e:
        return [TextContent(type="text", text=f"Zotero API error: {e}")]

    if not items:
        return [TextContent(type="text", text="Zotero sync: no new items since last sync.")]

    added = 0
    updated = 0
    skipped = 0

    with connect(paths.db) as conn:
        _ensure_lit_schema(conn)

        for item in items:
            data = item.get("data", {})
            item_type = data.get("itemType", "")
            if item_type in ("attachment", "note"):
                skipped += 1
                continue

            row = _item_to_row(item)
            if not row["title"]:
                skipped += 1
                continue

            if _upsert_lit_row(conn, row) == "updated":
                updated += 1
            else:
                added += 1

        # Store new sync version
        try:
            new_version = zot.last_modified_version()
            total = conn.execute(
                "SELECT COUNT(*) FROM literature_metadata WHERE library_source='zotero'"
            ).fetchone()[0]
            _set_last_version(conn, new_version, total)
        except Exception:
            pass

    lines = [
        f"Zotero sync complete.",
        f"  {added} new items added",
        f"  {updated} items updated",
        f"  {skipped} items skipped (attachments/notes/no title)",
        f"  {added + updated} total changes processed",
    ]
    if full:
        lines.append("  (full sync — all items re-processed)")
    return [TextContent(type="text", text="\n".join(lines))]


def _find_local_zotero_db() -> "str | None":
    """Best-effort search for a local zotero.sqlite in common install locations."""
    import glob
    candidates = [
        os.path.expanduser("~/Zotero/zotero.sqlite"),
        os.path.expanduser("~/.zotero/zotero/*/zotero.sqlite"),
    ]
    # Windows-under-WSL: scan mounted user dirs.
    candidates += glob.glob("/mnt/c/Users/*/Zotero/zotero.sqlite")
    for pat in candidates:
        for hit in glob.glob(pat):
            if os.path.exists(hit):
                return hit
    return None


def _read_local_zotero(db_path: str) -> list[dict]:
    """Read items from a local zotero.sqlite and return rows shaped for upsert.

    Zotero locks its DB while running, so we copy it to a temp file and read the
    copy read-only. No Zotero API key needed — this is the offline path.
    """
    import shutil
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    try:
        shutil.copy2(db_path, tmp.name)
        zc = sqlite3.connect(f"file:{tmp.name}?mode=ro", uri=True)
        zc.row_factory = sqlite3.Row

        # Field values per item (skip deleted, attachments, notes).
        field_rows = zc.execute(
            """
            SELECT i.itemID, i.key AS item_key, i.version AS item_version,
                   it.typeName AS item_type, f.fieldName AS field, idv.value AS value
            FROM items i
            JOIN itemTypes it       ON it.itemTypeID = i.itemTypeID
            JOIN itemData idata     ON idata.itemID = i.itemID
            JOIN fields f           ON f.fieldID = idata.fieldID
            JOIN itemDataValues idv ON idv.valueID = idata.valueID
            WHERE i.itemID NOT IN (SELECT itemID FROM deletedItems)
              AND it.typeName NOT IN ('attachment', 'note')
            """
        ).fetchall()

        items: dict = {}
        for r in field_rows:
            it = items.setdefault(r["itemID"], {
                "key": r["item_key"], "version": r["item_version"],
                "item_type": r["item_type"], "fields": {},
            })
            it["fields"][r["field"]] = r["value"]

        # Creators per item, ordered.
        creator_rows = zc.execute(
            """
            SELECT ic.itemID, c.lastName, c.firstName, c.fieldMode, ic.orderIndex
            FROM itemCreators ic
            JOIN creators c ON c.creatorID = ic.creatorID
            ORDER BY ic.itemID, ic.orderIndex
            """
        ).fetchall()
        creators: dict = {}
        for r in creator_rows:
            if r["fieldMode"] == 1 and r["lastName"]:
                name = r["lastName"]                       # institutional/single-field
            else:
                name = r["lastName"] or ""
                if r["firstName"]:
                    name += f", {r['firstName'][0]}."
            if name:
                creators.setdefault(r["itemID"], []).append(name)

        # Tags per item.
        tag_rows = zc.execute(
            """
            SELECT it.itemID, t.name
            FROM itemTags it JOIN tags t ON t.tagID = it.tagID
            """
        ).fetchall()
        tags_map: dict = {}
        for r in tag_rows:
            tags_map.setdefault(r["itemID"], []).append(r["name"])

        zc.close()

        rows = []
        for item_id, it in items.items():
            fld = it["fields"]
            title = (fld.get("title") or "")[:500]
            if not title:
                continue
            raw_date = fld.get("date", "") or ""
            ym = re.search(r"\b(19|20)\d{2}\b", raw_date)
            year = int(ym.group()) if ym else None
            doi = fld.get("DOI") or ""
            url = fld.get("url") or (f"https://doi.org/{doi}" if doi else "")
            rows.append({
                "title": title,
                "authors": "; ".join(creators.get(item_id, [])[:8])[:300],
                "year": year,
                "source": fld.get("publicationTitle") or fld.get("bookTitle") or fld.get("publisher") or "",
                "journal": fld.get("publicationTitle") or "",
                "tags": ",".join(tags_map.get(item_id, [])[:12]),
                "doi": doi,
                "abstract": (fld.get("abstractNote") or "")[:2000],
                "url": url,
                "item_type": it["item_type"] or "",
                "zotero_key": it["key"] or "",
                "zotero_version": it["version"] or 0,
                "library_source": "zotero-local",
                "created_at": datetime.now().isoformat(),
            })
        return rows
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@app.tool()
async def sync_zotero_local(db_path: str = "") -> list[TextContent]:
    """Import a local Zotero library by reading zotero.sqlite directly (no API key).

    The offline alternative to sync_zotero_library: reads your local Zotero
    database file, so it works with no ZOTERO_API_KEY and no network. Items are
    imported into literature_metadata (library_source='zotero-local'), the same
    table the Librarian and search_library use.

    Args:
        db_path: Path to zotero.sqlite. If empty, Metis searches common locations
                 (~/Zotero/zotero.sqlite, and /mnt/c/Users/*/Zotero on WSL).
    """
    path = db_path or _find_local_zotero_db()
    if not path or not os.path.exists(path):
        return [TextContent(type="text", text=(
            "Local Zotero database not found. Pass db_path explicitly, e.g. "
            "/mnt/c/Users/<you>/Zotero/zotero.sqlite. (Tip: in Zotero, "
            "Settings → Advanced → Data Directory Location shows the folder.)"
        ))]

    try:
        rows = _read_local_zotero(path)
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading local Zotero DB: {e}")]

    if not rows:
        return [TextContent(type="text", text=f"No importable items found in {path}.")]

    added = updated = 0
    with connect(paths.db) as conn:
        _ensure_lit_schema(conn)
        for row in rows:
            if _upsert_lit_row(conn, row) == "updated":
                updated += 1
            else:
                added += 1

    return [TextContent(type="text", text="\n".join([
        f"Local Zotero import complete (from {path}):",
        f"  {added} new items added",
        f"  {updated} items updated",
        f"  {added + updated} total processed",
    ]))]


@app.tool()
async def search_library(query: str, limit: int = 10) -> list[TextContent]:
    """Search the local literature library for matching papers.

    Searches your saved reference METADATA (title/authors/abstract/tags of papers
    in your Zotero-synced + manual library). For meaning-based search inside PDF
    body text use search_pdf_knowledge; for exact keyword search of PDF text use
    search_fulltext; for an online/external literature lookup use search_literature.

    Runs a substring search across the user's indexed references (Zotero-synced
    plus manually added) so you can find what they already have before going to
    the internet. Matches the query against title, authors, abstract, and tags,
    returning the newest papers first. For richer literature workflows see
    ask_library, search_literature, and export_citations.

    Args:
        query: Search terms matched as a substring against title, authors,
            abstract, and tags.
        limit: Maximum number of papers to return, ordered newest year first
            (default 10).

    Returns:
        A formatted text list of matching papers (title, authors, year, journal,
        DOI, abstract snippet), or a "no papers found" message.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="Database not found.")]

    like = f"%{query}%"
    with connect(paths.db) as conn:
        rows = conn.execute(
            """SELECT title, authors, year, journal, doi, tags, abstract, item_type
               FROM literature_metadata
               WHERE title LIKE ? OR authors LIKE ? OR abstract LIKE ? OR tags LIKE ?
               ORDER BY year DESC LIMIT ?""",
            (like, like, like, like, limit),
        ).fetchall()

    if not rows:
        return [TextContent(type="text", text=f"No papers found for: {query}")]

    lines = [f"**{len(rows)} results for '{query}':**\n"]
    for r in rows:
        year = r["year"] or "?"
        journal = r["journal"] or r["item_type"] or "?"
        doi_link = f" · doi:{r['doi']}" if r["doi"] else ""
        abstract = (r["abstract"] or "")[:150]
        lines.append(
            f"**{r['title'][:80]}**\n"
            f"  {r['authors'][:60] or '—'} · {year} · {journal[:40]}{doi_link}"
        )
        if abstract:
            lines.append(f"  _{abstract}…_")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def propose_library_organization(
    n_clusters: int = 0,
    min_papers: int = 3,
) -> list[TextContent]:
    """Cluster papers by topic and propose an AI-generated collection structure.

    Uses abstracts and titles to embed papers, then clusters them with k-means.
    Returns a proposed collection structure with suggested names and paper counts.

    Args:
        n_clusters: Number of topic clusters. 0 = auto-detect (sqrt of library size).
        min_papers: Minimum papers per cluster to report (default 3).
    """
    with connect(paths.db) as conn:
        rows = conn.execute(
            """SELECT id, title, abstract, tags, authors, year
               FROM literature_metadata
               WHERE title != '' AND library_source IN ('zotero','manual')
               ORDER BY year DESC"""
        ).fetchall()

    if len(rows) < 6:
        return [TextContent(type="text", text=
            f"Need at least 6 papers for clustering. Library has {len(rows)}. "
            "Run sync_zotero_library() first."
        )]

    # Build text for each paper
    texts = []
    for r in rows:
        parts = [r["title"] or ""]
        if r["abstract"]:
            parts.append(r["abstract"][:300])
        if r["tags"]:
            parts.append(r["tags"].replace(",", " "))
        texts.append(" ".join(parts))

    # Embed
    try:
        from fastembed import TextEmbedding
        embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        embeddings = list(embedder.embed(texts))
    except Exception as e:
        return [TextContent(type="text", text=f"Embedding error: {e}")]

    import numpy as np
    X = np.array(embeddings)

    # Cluster
    k = n_clusters if n_clusters > 0 else max(4, int(len(rows) ** 0.5))
    k = min(k, len(rows) // 2)

    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import normalize
        X_norm = normalize(X)
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_norm)
    except Exception as e:
        return [TextContent(type="text", text=f"Clustering error: {e}")]

    # Group papers by cluster
    clusters: dict[int, list[dict]] = {}
    for i, row in enumerate(rows):
        c = int(labels[i])
        clusters.setdefault(c, []).append(dict(row))

    # Generate cluster labels from top terms in titles + tags
    def _cluster_label(papers: list[dict]) -> str:
        from collections import Counter
        stopwords = {"the","a","an","of","in","for","on","with","and","or","to",
                     "is","are","was","were","this","that","from","by","at","as",
                     "study","analysis","using","based","case","among","between"}
        words = []
        for p in papers:
            words += re.findall(r"\b[a-zA-Z]{4,}\b", (p.get("title") or "").lower())
            words += (p.get("tags") or "").replace(",", " ").lower().split()
        top = [w for w, _ in Counter(words).most_common(40) if w not in stopwords][:4]
        return " / ".join(top) if top else "Uncategorized"

    lines = [
        f"── Proposed Library Organization ──",
        f"{len(rows)} papers · {k} topic clusters\n",
    ]

    sorted_clusters = sorted(clusters.items(), key=lambda x: -len(x[1]))
    for cluster_id, papers in sorted_clusters:
        if len(papers) < min_papers:
            continue
        label = _cluster_label(papers)
        lines.append(f"**{label.title()}** ({len(papers)} papers)")
        for p in papers[:4]:
            year = p.get("year") or "?"
            lines.append(f"  · {(p.get('title') or '')[:65]} ({year})")
        if len(papers) > 4:
            lines.append(f"  · … and {len(papers) - 4} more")
        lines.append("")

    lines.append(
        "To apply this structure in Zotero: create these as Collections and drag papers in.\n"
        "Or ask the Librarian agent to do a deeper thematic analysis."
    )
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def import_bibtex_library(bibtex_path: str) -> list[TextContent]:
    """Import papers from a BibTeX file into literature_metadata.

    Use this for Mendeley users: export your library from Mendeley as BibTeX,
    then point this tool at the file.

    Args:
        bibtex_path: Full path to the .bib file (e.g. from Mendeley export).
    """
    bib_file = Path(bibtex_path)
    if not bib_file.exists():
        return [TextContent(type="text", text=f"File not found: {bibtex_path}")]

    try:
        import bibtexparser
        with open(bib_file, encoding="utf-8", errors="replace") as f:
            library = bibtexparser.load(f)
        entries = library.entries
    except ImportError:
        # Fallback: crude regex parser
        entries = _parse_bibtex_simple(bib_file.read_text(encoding="utf-8", errors="replace"))

    if not entries:
        return [TextContent(type="text", text="No entries found in BibTeX file.")]

    added = 0
    skipped = 0
    with connect(paths.db) as conn:
        _ensure_lit_schema(conn)
        for entry in entries:
            title = (entry.get("title") or "").strip("{}")
            if not title:
                skipped += 1
                continue
            exists = conn.execute(
                "SELECT 1 FROM literature_metadata WHERE title=? LIMIT 1", (title,)
            ).fetchone()
            if exists:
                skipped += 1
                continue

            authors_raw = entry.get("author") or entry.get("editor") or ""
            authors = authors_raw.replace(" and ", "; ")[:300]
            year_raw = entry.get("year") or ""
            year = int(year_raw) if year_raw.isdigit() else None
            journal = entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or ""
            doi = entry.get("doi") or ""
            # INGESTION CHOKEPOINT — BibTeX/Mendeley import is external content.
            abstract = sanitize_external(
                (entry.get("abstract") or "")[:2000], f"bibtex-abstract:{title[:60]}"
            )
            tags = entry.get("keywords") or ""

            conn.execute(
                """INSERT INTO literature_metadata
                   (title, authors, year, source, journal, tags, doi, abstract,
                    item_type, library_source, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (title, authors, year, journal, journal, tags, doi, abstract,
                 entry.get("ENTRYTYPE") or "article", "mendeley-bibtex",
                 datetime.now().isoformat()),
            )
            added += 1

    return [TextContent(type="text", text=
        f"BibTeX import complete: {added} papers added, {skipped} skipped (duplicates/no title)."
    )]


def _parse_bibtex_simple(text: str) -> list[dict]:
    """Minimal BibTeX parser when bibtexparser is not installed."""
    entries = []
    for block in re.split(r"@(\w+)\s*\{", text)[1:]:
        parts = block.split("\n", 1)
        entry_type = parts[0].strip().lower() if parts else ""
        body = parts[1] if len(parts) > 1 else ""
        entry: dict = {"ENTRYTYPE": entry_type}
        for m in re.finditer(r"(\w+)\s*=\s*[{\"](.+?)[}\"]", body, re.DOTALL):
            entry[m.group(1).lower()] = m.group(2).strip()
        entries.append(entry)
    return entries


@app.tool()
async def get_library_stats() -> list[TextContent]:
    """Summarise your literature library at a glance.

    Use this to see how big and how current your reference collection is before
    searching or citing: it reports the total number of papers, a breakdown by
    source (e.g. Zotero, Mendeley, manual) and by item type, the most recently
    added references, and — if you sync Zotero — when the library was last
    synced. A quick "what's in my library right now?" overview. Takes no
    arguments. Pairs with search_library and sync_zotero_library.

    Returns:
        A formatted summary: total papers, counts by source and item type, the
        five most recent references, and Zotero sync state if available.
    """
    with connect(paths.db) as conn:
        _ensure_lit_schema(conn)
        total = conn.execute("SELECT COUNT(*) FROM literature_metadata").fetchone()[0]
        by_source = conn.execute(
            "SELECT library_source, COUNT(*) as cnt FROM literature_metadata GROUP BY library_source"
        ).fetchall()
        by_type = conn.execute(
            "SELECT item_type, COUNT(*) as cnt FROM literature_metadata GROUP BY item_type ORDER BY cnt DESC LIMIT 6"
        ).fetchall()
        recent = conn.execute(
            "SELECT title, authors, year FROM literature_metadata ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        sync_state = conn.execute(
            "SELECT last_version, last_synced, item_count FROM zotero_sync_state LIMIT 1"
        ).fetchone() if conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='zotero_sync_state'"
        ).fetchone() else None

    lines = [f"── Library Stats ──\n", f"Total papers: {total}\n"]
    lines.append("By source:")
    for r in by_source:
        lines.append(f"  · {r['library_source'] or 'manual'}: {r['cnt']}")
    lines.append("\nBy type:")
    for r in by_type:
        if r["item_type"]:
            lines.append(f"  · {r['item_type']}: {r['cnt']}")
    if sync_state:
        lines.append(f"\nLast Zotero sync: {(sync_state['last_synced'] or '')[:16]}")
        lines.append(f"Zotero library version: {sync_state['last_version']}")
    lines.append("\nMost recently added:")
    for r in recent:
        lines.append(f"  · {(r['title'] or '')[:60]} ({r['year'] or '?'})")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def configure_library_provider(
    provider: str,
    api_key: str = "",
    user_id: str = "",
    bibtex_path: str = "",
) -> list[TextContent]:
    """Configure the library provider for this Metis installation.

    Call this during setup or when switching reference managers.

    Args:
        provider: "zotero" or "mendeley". Mendeley uses BibTeX export.
        api_key: Zotero API key (from https://www.zotero.org/settings/keys).
        user_id: Zotero numeric user ID (shown on the same settings page).
        bibtex_path: For Mendeley: full path to exported .bib file.
    """
    env_path = paths.root / "system" / ".env"
    lines_out = []

    if provider.lower() == "zotero":
        if not api_key or not user_id:
            return [TextContent(type="text", text=
                "To configure Zotero:\n"
                "1. Go to https://www.zotero.org/settings/keys\n"
                "2. Click 'Create new private key'\n"
                "3. Give it library read access\n"
                "4. Copy the key and your numeric user ID (shown at top of that page)\n"
                "5. Call this tool again with api_key='...' and user_id='...'"
            )]

        # Write to .env
        existing = env_path.read_text() if env_path.exists() else ""
        new_lines = []
        seen = set()
        for line in existing.splitlines():
            if line.startswith("ZOTERO_API_KEY=") or line.startswith("ZOTERO_USER_ID="):
                continue
            new_lines.append(line)
        new_lines.append(f"ZOTERO_API_KEY={api_key}")
        new_lines.append(f"ZOTERO_USER_ID={user_id}")
        env_path.write_text("\n".join(new_lines) + "\n")

        # Set in current process too
        os.environ["ZOTERO_API_KEY"] = api_key
        os.environ["ZOTERO_USER_ID"] = user_id

        lines_out = [
            "Zotero configured successfully.",
            f"  API key: {api_key[:6]}…",
            f"  User ID: {user_id}",
            "",
            "Run sync_zotero_library() to import your full library.",
        ]

    elif provider.lower() in ("mendeley", "bibtex"):
        if not bibtex_path:
            return [TextContent(type="text", text=
                "To configure Mendeley:\n"
                "1. Open Mendeley Desktop\n"
                "2. File → Export → BibTeX (all documents)\n"
                "3. Save the .bib file somewhere accessible\n"
                "4. Call this tool again with bibtex_path='/path/to/library.bib'\n"
                "\nNote: After the initial import you can re-export and re-import anytime "
                "to pick up new papers."
            )]
        result = await import_bibtex_library(bibtex_path)
        lines_out = ["Mendeley BibTeX import complete."] + [r.text for r in result]

    else:
        return [TextContent(type="text", text=
            f"Unknown provider '{provider}'. Use 'zotero' or 'mendeley'."
        )]

    return [TextContent(type="text", text="\n".join(lines_out))]


# ---------------------------------------------------------------------------
# Citation export — BibTeX (universal: imports into Word, LaTeX, Zotero, etc.)
# ---------------------------------------------------------------------------

def _bibtex_key(authors: str, year, title: str, used: set) -> str:
    """Generate a unique BibTeX cite key like Garcia2002."""
    first_author = (authors or "").split(",")[0].split(" and ")[0].strip()
    last = first_author.split()[-1] if first_author else "anon"
    last = re.sub(r"[^A-Za-z]", "", last) or "anon"
    yr = str(year or "").strip()[:4] or "n.d."
    base = f"{last}{yr}"
    key, suffix = base, ord("a")
    while key in used:
        key = base + chr(suffix)
        suffix += 1
    used.add(key)
    return key


def _bibtex_escape(s: str) -> str:
    return (s or "").replace("{", "").replace("}", "").replace("\\", "").strip()


@app.tool()
async def export_citations(
    query: str = "",
    tag: str = "",
    collection: str = "",
    fmt: str = "bibtex",
    limit: int = 500,
) -> list[TextContent]:
    """Export library references as a citation file (BibTeX).

    Closes the "no citation-style export" gap: produces a .bib you can import
    into Word (via Zotero/Mendeley), LaTeX/Overleaf, or any reference manager,
    and use for cite-while-you-write.

    Args:
        query: Optional keyword filter over title/authors/journal. Empty = all.
        tag: Optional tag filter (substring match on the tags field).
        collection: Optional collection-name filter.
        fmt: Output format — currently "bibtex" (RIS available via mine_references).
        limit: Max records to export (default 500).

    Writes the file to outputs/exports/ and returns its path + a preview.
    """
    if fmt.lower() not in ("bibtex", "bib"):
        return [TextContent(type="text", text="Only 'bibtex' is supported here. For RIS, use the reference-mining export.")]
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    clauses, params = [], []
    if query:
        clauses.append("(title LIKE ? OR authors LIKE ? OR journal LIKE ?)")
        params += [f"%{query}%", f"%{query}%", f"%{query}%"]
    if tag:
        clauses.append("tags LIKE ?"); params.append(f"%{tag}%")
    if collection:
        clauses.append("collection LIKE ?"); params.append(f"%{collection}%")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    with connect(paths.db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT title, authors, year, doi, journal, item_type, url, abstract "
            f"FROM literature_metadata{where} ORDER BY year DESC, title LIMIT ?",
            (*params, limit),
        ).fetchall()

    if not rows:
        return [TextContent(type="text", text="No matching references to export.")]

    used_keys: set = set()
    entries = []
    for r in rows:
        d = dict(r)
        key = _bibtex_key(d.get("authors", ""), d.get("year"), d.get("title", ""), used_keys)
        etype = {"journalArticle": "article", "book": "book", "report": "techreport",
                 "conferencePaper": "inproceedings"}.get(d.get("item_type") or "", "article")
        fields = [f'  title = {{{_bibtex_escape(d.get("title"))}}}']
        if d.get("authors") and d["authors"] != "unknown":
            authors = d["authors"].replace(";", " and ")
            fields.append(f'  author = {{{_bibtex_escape(authors)}}}')
        if d.get("year"):
            fields.append(f'  year = {{{str(d["year"])[:4]}}}')
        if d.get("journal"):
            fields.append(f'  journal = {{{_bibtex_escape(d["journal"])}}}')
        if d.get("doi"):
            fields.append(f'  doi = {{{d["doi"].strip()}}}')
        if d.get("url"):
            fields.append(f'  url = {{{d["url"].strip()}}}')
        entries.append(f"@{etype}{{{key},\n" + ",\n".join(fields) + "\n}")

    bib = "\n\n".join(entries) + "\n"
    out_dir = paths.root / "outputs" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"library-export-{stamp}.bib"
    out_path.write_text(bib, encoding="utf-8")

    preview = "\n\n".join(entries[:2])
    return [TextContent(type="text", text=(
        f"Exported {len(entries)} reference(s) to BibTeX.\n"
        f"File: {out_path}\n\n"
        f"Import into Word (via Zotero/Mendeley), Overleaf, or any reference manager.\n\n"
        f"Preview:\n{preview}"
    ))]


# ── Zotero → knowledge layer ──────────────────────────────────────────────────
#
# WHY THIS EXISTS
#   A background pack can only ship URLs that any machine can fetch. Every field
#   has canonical texts that fails that test — behind a publisher's browser check
#   or an institutional subscription. Those are declared `access: "manual"` in the
#   manifest and listed in _TO-OBTAIN.md, which leaves the researcher copying PDFs
#   by hand into the right folder.
#
#   Zotero already solves the hard half. Saving with the browser connector while
#   logged in through an institution puts BOTH the citation and the PDF on disk.
#   This bridges the last step: it copies a collection's attachment PDFs into a
#   knowledge layer's folder, where the existing folder-based indexer finds them.
#
#   No API key. It reads zotero.sqlite directly, like sync_zotero_local — the
#   Zotero web API key on this install is read-only (403 on write) and an
#   institutional PDF is not on the web API anyway; it is local to the machine
#   that downloaded it.


def _layer_folder(database: str) -> "tuple[Path | None, str]":
    """Resolve a knowledge layer's on-disk folder, or (None, reason)."""
    try:
        with connect(paths.db) as con:
            row = con.execute(
                "SELECT name, folders FROM knowledge_databases WHERE slug = ?", (database,)
            ).fetchone()
    except Exception as exc:
        return None, f"could not read the knowledge layers: {exc}"
    if not row:
        return None, f"no knowledge layer called '{database}'"
    folders = [f.strip("/") for f in str(row[1] or "").splitlines() if f.strip()]
    if not folders:
        # The built-in layers (ph-background, epi-methods, hat-specialist, ntd)
        # carry an EMPTY folders column — the indexer resolves them from a
        # hardcoded table instead. Reading only the column made this tool refuse
        # every layer that shipped with Metis, which is most of them. Ask the same
        # source of truth the indexer uses, so a file copied here is a file indexed.
        try:
            from metis_mcp.tools.knowledge_db import BUILTIN_DATABASES
            d = next((b for b in BUILTIN_DATABASES if b["slug"] == database), None)
            folders = [f.strip("/") for f in (d or {}).get("folders", []) if str(f).strip()]
        except Exception:
            folders = []
    if not folders:
        # Guessing a folder here is how a previous bug wrote into a directory the
        # layer does not index — silently, and looking like it worked.
        return None, (f"the layer '{database}' has no folder recorded, so there is "
                      f"nowhere safe to put the files")
    first = Path(folders[0]).expanduser()
    return (first if first.is_absolute() else paths.library / folders[0]), row[0]


def _zotero_collection_pdfs(zdb: str, collection: str) -> "tuple[list[tuple[str, Path]], list[str]]":
    """Return [(display_title, source_path)] for PDFs in a collection, plus all collection names."""
    import shutil
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    storage = Path(zdb).parent / "storage"
    try:
        shutil.copy2(zdb, tmp.name)  # Zotero holds a lock while running
        zc = sqlite3.connect(f"file:{tmp.name}?mode=ro", uri=True)
        zc.row_factory = sqlite3.Row
        names = [r[0] for r in zc.execute("SELECT collectionName FROM collections ORDER BY 1")]

        # An attachment is usually a CHILD of the item that sits in the collection,
        # but it can also be filed directly. Both are matched, hence the OR.
        rows = zc.execute(
            """
            SELECT ai.key AS akey, ia.path AS path,
                   COALESCE(idv.value, ia.path) AS title
            FROM collections co
            JOIN collectionItems ci ON ci.collectionID = co.collectionID
            JOIN itemAttachments ia ON ia.parentItemID = ci.itemID OR ia.itemID = ci.itemID
            JOIN items ai           ON ai.itemID = ia.itemID
            LEFT JOIN itemData idata ON idata.itemID = ci.itemID
            LEFT JOIN fields f       ON f.fieldID = idata.fieldID AND f.fieldName = 'title'
            LEFT JOIN itemDataValues idv ON idv.valueID = idata.valueID AND f.fieldID IS NOT NULL
            WHERE co.collectionName = ?
              AND ia.contentType = 'application/pdf'
              AND ia.path LIKE 'storage:%'
            """,
            (collection,),
        ).fetchall()
        zc.close()
    finally:
        os.unlink(tmp.name)

    out, seen = [], set()
    for r in rows:
        fname = r["path"].split("storage:", 1)[1]
        src = storage / r["akey"] / fname
        if src in seen or not src.exists():
            continue
        seen.add(src)
        out.append((str(r["title"] or fname), src))
    return out, names


@app.tool()
async def import_zotero_pdfs(
    collection: str,
    database: str,
    confirm: bool = False,
) -> list[TextContent]:
    """Copy the PDFs from a Zotero collection into a knowledge layer, so they get indexed.

    For texts a background pack cannot download — anything behind a publisher's
    browser check or your institution's subscription. Save them in Zotero with the
    browser connector (logged in through your library), then point this at the
    collection. No Zotero API key needed; it reads your local Zotero database.

    The files are COPIED, so your Zotero library is left untouched. Indexing is not
    run here — press Rebuild on the Library surface, or wait for the nightly index.

    Args:
        collection: Zotero collection name, exactly as it appears in Zotero.
        database:   Slug of the knowledge layer to add them to (e.g. 'ph-foundations').
        confirm:    True to actually copy. Without it you get the list only.
    """
    zdb = _find_local_zotero_db()
    if not zdb:
        return [TextContent(type="text", text=(
            "Could not find your Zotero database. In Zotero, look under "
            "Settings → Advanced → Data Directory Location, then pass that folder's "
            "zotero.sqlite to sync_zotero_local() once so I know where it lives."
        ))]

    target, layer_name = _layer_folder(database)
    if target is None:
        return [TextContent(type="text", text=f"Cannot import: {layer_name}.")]

    try:
        pdfs, names = _zotero_collection_pdfs(zdb, collection)
    except Exception as exc:
        return [TextContent(type="text", text=f"Could not read Zotero: {exc}")]

    if not pdfs:
        hint = ""
        if collection not in names:
            close = [n for n in names if collection.lower() in n.lower()][:5]
            hint = (f" There is no collection called '{collection}'."
                    + (f" Did you mean: {', '.join(close)}?" if close else
                       f" Collections found: {', '.join(names[:12])}"))
        return [TextContent(type="text", text=(
            f"No PDF attachments found in '{collection}'.{hint}"))]

    if not confirm:
        lines = [f"**{len(pdfs)} PDF(s)** in Zotero collection *{collection}* would be copied into "
                 f"**{layer_name}** (`{target}`):", ""]
        lines += [f"- {t[:90]}" for t, _ in pdfs[:20]]
        if len(pdfs) > 20:
            lines.append(f"- …and {len(pdfs)-20} more")
        lines += ["", f"To go ahead: import_zotero_pdfs('{collection}', '{database}', confirm=True)"]
        return [TextContent(type="text", text="\n".join(lines))]

    import shutil
    target.mkdir(parents=True, exist_ok=True)
    copied, skipped, failed = 0, 0, []
    for title, src in pdfs:
        dest = target / re.sub(r"[^\w.\- ]", "_", src.name)
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        try:
            # Same rule as the pack installer: verify it IS a PDF. A Zotero
            # attachment can be a stub saved when a download failed, and an
            # HTML error page indexed as a book is worse than a missing book.
            with open(src, "rb") as fh:
                if fh.read(5) != b"%PDF-":
                    raise OSError("not a PDF (Zotero may have saved a failed download)")
            shutil.copy2(src, dest)
            copied += 1
        except Exception as exc:
            failed.append(f"{title[:60]}: {exc}")

    # M6: a copied paper that is not indexed is a paper the researcher cannot find,
    # and "I added it and Metis cannot see it" reads as breakage rather than a queue.
    from metis_mcp.auto_index import schedule_index
    started = schedule_index(database, reason="zotero import") if copied else ""

    msg = [f"Copied **{copied}** PDF(s) from *{collection}* into **{layer_name}**"
           + (f", {skipped} already there" if skipped else "")
           + (f", {len(failed)} failed" if failed else "") + ".",
           f"Folder: `{target}`"]
    msg.append(started.capitalize() + "." if started else "Nothing new to index.")
    if failed:
        msg += ["", "Could not copy:"] + [f"- {f}" for f in failed[:10]]
    return [TextContent(type="text", text="\n".join(msg))]
