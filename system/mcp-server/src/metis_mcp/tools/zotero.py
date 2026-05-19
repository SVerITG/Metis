"""Zotero library connector — sync, search, and AI-powered organisation.

Supports Zotero via pyzotero. Mendeley users are guided to export BibTeX
and import via import_bibtex_library().

Config is read from environment variables (set in metis/system/.env):
  ZOTERO_API_KEY  — Zotero Web API key
  ZOTERO_USER_ID  — numeric Zotero user ID
  ZOTERO_GROUP_ID — optional, for group libraries
"""

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

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
        return pyz.Zotero(group_id, "group", api_key)
    return pyz.Zotero(user_id, "user", api_key)


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

            existing = conn.execute(
                "SELECT id FROM literature_metadata WHERE zotero_key = ?",
                (row["zotero_key"],),
            ).fetchone()

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
                updated += 1
            else:
                conn.execute(
                    """INSERT INTO literature_metadata
                       (title, authors, year, source, journal, tags, doi, abstract,
                        url, item_type, zotero_key, zotero_version, library_source, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (row["title"], row["authors"], row["year"], row["source"], row["journal"],
                     row["tags"], row["doi"], row["abstract"], row["url"], row["item_type"],
                     row["zotero_key"], row["zotero_version"], row["library_source"], row["created_at"]),
                )
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


@app.tool()
async def search_library(query: str, limit: int = 10) -> list[TextContent]:
    """Search the local literature library (Zotero-synced + manually added papers).

    Searches title, authors, abstract, tags, and journal fields.

    Args:
        query: Search terms.
        limit: Maximum results (default 10).
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
            abstract = (entry.get("abstract") or "")[:2000]
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
    """Return a summary of the current literature library."""
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
