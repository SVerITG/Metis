"""
fulltext_index.py — PDF full-text extraction and indexing.

Extracts text from PDFs in inputs/literature/ and Zotero storage,
stores first 4000 characters in literature_metadata.abstract (if empty)
and a new library_fulltext table for keyword search.

MCP tools:
  - index_pdf_library  : index all unindexed PDFs (incremental)
  - search_fulltext    : keyword search across indexed full text
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from mcp.types import TextContent

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS library_fulltext (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL UNIQUE,
    filepath    TEXT NOT NULL,
    title       TEXT,
    text_chunk  TEXT,
    word_count  INTEGER,
    indexed_at  TEXT
);
"""


def _ensure_table():
    if not paths.db.exists():
        return
    with sqlite3.connect(str(paths.db)) as conn:
        conn.execute(_DDL)
        # Also add abstract column to literature_metadata if missing
        try:
            conn.execute("ALTER TABLE literature_metadata ADD COLUMN abstract TEXT")
        except Exception:
            pass
        conn.commit()


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def _extract_text(pdf_path: Path, max_chars: int = 4000) -> str | None:
    """Extract text from PDF using PyMuPDF (fitz). Returns None if unavailable."""
    try:
        try:
            import pymupdf as fitz  # PyMuPDF >= 1.24
        except ImportError:
            import fitz  # PyMuPDF legacy
        doc = fitz.open(str(pdf_path))
        parts = []
        for page in doc:
            parts.append(page.get_text())
            if sum(len(p) for p in parts) >= max_chars * 2:
                break
        doc.close()
        text = " ".join(parts)
        # Clean up excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except ImportError:
        return None
    except Exception:
        return None


def _already_indexed(conn: sqlite3.Connection, filepath: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM library_fulltext WHERE filepath = ? LIMIT 1", (filepath,)
    )
    return cur.fetchone() is not None


def _match_to_metadata(conn: sqlite3.Connection, filename: str, text: str) -> str | None:
    """Try to match a PDF filename to a literature_metadata title and update abstract."""
    # Extract year + first author from filename like "2023_Makabuza_Passive-surveillance..."
    m = re.match(r"^(\d{4})_([A-Za-z]+)_(.+)\.pdf$", filename)
    if not m:
        return None
    year, author, _ = m.groups()
    cur = conn.execute(
        "SELECT id FROM literature_metadata WHERE year = ? AND authors LIKE ? LIMIT 1",
        (year, f"%{author}%"),
    )
    row = cur.fetchone()
    if row:
        # Update abstract if empty
        conn.execute(
            "UPDATE literature_metadata SET abstract = ? WHERE id = ? AND (abstract IS NULL OR abstract = '')",
            (text[:1500], row[0]),
        )
        return str(row[0])
    return None


# ---------------------------------------------------------------------------
# Core indexer
# ---------------------------------------------------------------------------

def _index_directory(directory: Path, conn: sqlite3.Connection, stats: dict):
    """Index all PDFs in a directory tree."""
    for pdf in sorted(directory.rglob("*.pdf")):
        filepath = str(pdf)
        if _already_indexed(conn, filepath):
            stats["skipped"] += 1
            continue

        text = _extract_text(pdf)
        if text is None:
            stats["no_pymupdf"] += 1
            # Insert placeholder so we don't retry every run
            conn.execute(
                "INSERT OR IGNORE INTO library_fulltext "
                "(filename, filepath, title, text_chunk, word_count, indexed_at) "
                "VALUES (?, ?, ?, '', 0, datetime('now'))",
                (pdf.name, filepath, pdf.stem),
            )
            continue

        word_count = len(text.split())
        conn.execute(
            "INSERT OR IGNORE INTO library_fulltext "
            "(filename, filepath, title, text_chunk, word_count, indexed_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (pdf.name, filepath, pdf.stem, text, word_count),
        )
        _match_to_metadata(conn, pdf.name, text)
        stats["indexed"] += 1

    conn.commit()


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@app.tool()
async def index_pdf_library(scope: str = "all") -> list[TextContent]:
    """Extract and index full text from all PDFs in the Metis library.

    Reads PDFs from inputs/literature/ and Zotero storage.
    Stores first 4000 characters per paper in library_fulltext table.
    Also updates literature_metadata.abstract for any matched papers.
    Incremental — only processes files not yet indexed.

    Args:
        scope: "literature" = inputs/literature/ only | "zotero" = Zotero storage only | "all" = both
    """
    rc_root = Path(os.environ.get("METIS_RC_ROOT", ""))
    zotero_root = Path("/mnt/c/Users/sverschaeve/Zotero/storage")
    lit_root = rc_root / "inputs" / "literature"

    _ensure_table()

    stats = {"indexed": 0, "skipped": 0, "no_pymupdf": 0}

    try:
        import pymupdf  # noqa
        has_pymupdf = True
    except ImportError:
        try:
            import fitz  # noqa
            has_pymupdf = True
        except ImportError:
            has_pymupdf = False

    if not has_pymupdf:
        return [TextContent(type="text", text=
            "PyMuPDF (fitz) not installed. Run:\n"
            "  /home/sverschaeve/.local/share/metis-mcp/.venv/bin/pip install pymupdf\n"
            "then call index_pdf_library again."
        )]

    with sqlite3.connect(str(paths.db)) as conn:
        conn.execute(_DDL)
        if scope in ("all", "literature") and lit_root.exists():
            _index_directory(lit_root, conn, stats)
        if scope in ("all", "zotero") and zotero_root.exists():
            _index_directory(zotero_root, conn, stats)

    return [TextContent(type="text", text=
        f"Full-text indexing complete.\n"
        f"  Newly indexed: {stats['indexed']}\n"
        f"  Already done:  {stats['skipped']}\n"
        f"  No text extracted: {stats['no_pymupdf']}\n"
        f"\nSearch with: search_fulltext(query='your keywords')"
    )]


@app.tool()
async def search_fulltext(query: str, max_results: int = 10) -> list[TextContent]:
    """Full-text keyword search across all indexed PDFs.

    Searches the library_fulltext table for papers containing your keywords.
    More powerful than title/abstract search — finds methodological details
    in the body of papers.

    Args:
        query:       Keywords to search for (space-separated).
        max_results: Maximum results to return (default 10).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text="Database not found.")]

    words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", query.lower())
             if w not in {"the", "and", "for", "with", "this", "that", "are", "from"}]
    if not words:
        return [TextContent(type="text", text="No usable keywords in query.")]

    clauses = " OR ".join(["text_chunk LIKE ? OR title LIKE ?"] * len(words))
    params = []
    for w in words:
        params += [f"%{w}%", f"%{w}%"]

    with sqlite3.connect(str(paths.db)) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_table()
        cur = conn.execute(
            f"SELECT filename, title, text_chunk, word_count FROM library_fulltext "
            f"WHERE {clauses} AND word_count > 0 LIMIT ?",
            params + [max_results],
        )
        rows = cur.fetchall()

    if not rows:
        return [TextContent(type="text", text=f"No results for: {query}")]

    lines = [f"**{len(rows)} results for '{query}':**\n"]
    for r in rows:
        # Find the matching snippet
        chunk = r["text_chunk"] or ""
        snippet = ""
        for w in words:
            idx = chunk.lower().find(w)
            if idx >= 0:
                start = max(0, idx - 60)
                snippet = "…" + chunk[start:idx + 120].strip() + "…"
                break
        lines.append(f"**{r['title'] or r['filename']}**")
        if snippet:
            lines.append(f"  _{snippet}_")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]
