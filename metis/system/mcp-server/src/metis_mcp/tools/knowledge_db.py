"""knowledge_db.py — PDF Knowledge Database pipeline (Phase L).

Extracts text from all PDFs in knowledge/library/, chunks, embeds with local
nomic-embed-text-v1.5-Q (no API key required), and stores in SQLite.

Tools:
  build_pdf_knowledge_db(domain_filter, force_rebuild)
  search_pdf_knowledge(query, top_k, domain_filter)
  get_pdf_index_stats()
"""

from __future__ import annotations

import re
import struct
import time
from pathlib import Path
from typing import List, Optional

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app
from metis_mcp.db import connect

# ── Config ────────────────────────────────────────────────────────────────────

CHUNK_CHARS = 3200        # ~800 tokens
OVERLAP_CHARS = 400       # ~100 tokens
EMBED_BATCH = 32          # chunks per embedding batch
EMBEDDING_DIM = 768

_LIBRARY_SUBDIRS = [
    "open-access-books",
    "papers",
    "disease-areas",
    "methods",
    "concepts",
]

# ── Schema setup ──────────────────────────────────────────────────────────────

_VEC_DDL = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS vec_pdf_chunks USING vec0(
    rowid INTEGER PRIMARY KEY,
    embedding float[{EMBEDDING_DIM}]
);
"""

_CHUNK_DDL = """
CREATE TABLE IF NOT EXISTS pdf_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    domain      TEXT DEFAULT '',
    title       TEXT DEFAULT '',
    page_start  INTEGER DEFAULT 0,
    page_end    INTEGER DEFAULT 0,
    chunk_idx   INTEGER NOT NULL,
    chunk_text  TEXT NOT NULL,
    char_count  INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_pdf_chunks_source ON pdf_chunks (source_file);
CREATE INDEX IF NOT EXISTS idx_pdf_chunks_domain  ON pdf_chunks (domain);
"""

_STATE_DDL = """
CREATE TABLE IF NOT EXISTS pdf_index_state (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL UNIQUE,
    domain      TEXT DEFAULT '',
    title       TEXT DEFAULT '',
    total_pages INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    file_size   INTEGER DEFAULT 0,
    indexed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _ensure_schema(conn) -> None:
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        pass
    for ddl in (_CHUNK_DDL, _STATE_DDL, _VEC_DDL):
        for stmt in ddl.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except Exception:
                    pass
    conn.commit()


# ── Text helpers ──────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Normalize PDF-extracted text: fix line breaks, remove junk."""
    # Rejoin hyphenated line-breaks
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Collapse excessive whitespace but preserve paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove page headers/footers (short isolated lines)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that look like page numbers or headers (very short, all caps, or just digits)
        if stripped and not (len(stripped) <= 4 and (stripped.isdigit() or stripped.isupper())):
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def _chunk_text(text: str, chunk_size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> List[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break
        # Walk back to nearest paragraph or sentence boundary
        boundary = text.rfind("\n\n", start, end)
        if boundary == -1 or boundary <= start + chunk_size // 2:
            boundary = text.rfind(". ", start, end)
        if boundary == -1 or boundary <= start + chunk_size // 2:
            boundary = end
        else:
            boundary += 2  # include the delimiter

        chunk = text[start:boundary].strip()
        if chunk:
            chunks.append(chunk)
        start = boundary - overlap
        if start < 0:
            start = 0

    return chunks


def _infer_title(path: Path) -> str:
    """Derive a human-readable title from the filename."""
    stem = path.stem
    # Remove leading numbers like "01_" or "CDC-SS1978-"
    stem = re.sub(r"^\d+_", "", stem)
    # Convert separators to spaces
    stem = stem.replace("-", " ").replace("_", " ")
    # Titlecase but preserve known acronyms
    words = stem.split()
    titled = []
    acronyms = {"WHO", "CDC", "NTD", "HAT", "HIV", "AMR", "NCD", "UHC", "SDH",
                "DHIS2", "AFRO", "PAHO", "ECDC", "GBD", "DALY", "BMI", "TB",
                "ANC", "PHC", "MHC", "AI", "ML", "API", "PDF", "R2"}
    for w in words:
        if w.upper() in acronyms:
            titled.append(w.upper())
        else:
            titled.append(w.capitalize())
    return " ".join(titled)


def _encode_vec(vector: List[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


# ── PDF extraction ─────────────────────────────────────────────────────────────

def _extract_pdf_pages(pdf_path: Path) -> tuple[List[tuple[int, str]], int]:
    """Extract (page_num, text) pairs and total page count from a PDF.

    Returns (pages, total_pages). Pages is a list of (1-indexed page_num, text).
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path), strict=False)
        total = len(reader.pages)
        pages = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
                text = _clean_text(text)
                if text.strip():
                    pages.append((i + 1, text))
            except Exception:
                continue
        return pages, total
    except Exception:
        return [], 0


# ── Core build function ───────────────────────────────────────────────────────

def _library_root() -> Path:
    return paths.root / "knowledge" / "library"


def _collect_pdfs(domain_filter: str = "") -> List[Path]:
    lib = _library_root()
    pdfs: List[Path] = []
    for subdir in _LIBRARY_SUBDIRS:
        d = lib / subdir
        if d.exists():
            for p in d.rglob("*.pdf"):
                if domain_filter and domain_filter.lower() not in p.parent.name.lower():
                    continue
                pdfs.append(p)
    return sorted(pdfs)


def _already_indexed(conn, source_file: str) -> bool:
    row = conn.execute(
        "SELECT chunk_count FROM pdf_index_state WHERE source_file = ?",
        (source_file,)
    ).fetchone()
    return row is not None and row[0] > 0


def _delete_existing(conn, source_file: str) -> None:
    rows = conn.execute(
        "SELECT id FROM pdf_chunks WHERE source_file = ?", (source_file,)
    ).fetchall()
    for row in rows:
        conn.execute("DELETE FROM vec_pdf_chunks WHERE rowid = ?", (row[0],))
    conn.execute("DELETE FROM pdf_chunks WHERE source_file = ?", (source_file,))
    conn.execute("DELETE FROM pdf_index_state WHERE source_file = ?", (source_file,))
    conn.commit()


def _upsert_library_card(conn, title: str, domain: str, source_path: str, summary: str) -> None:
    existing = conn.execute(
        "SELECT id FROM library_cards WHERE title = ?", (title,)
    ).fetchone()
    if existing:
        return
    conn.execute(
        "INSERT INTO library_cards (title, domain, summary, source_path) VALUES (?, ?, ?, ?)",
        (title, domain, summary[:500], source_path)
    )


def _index_one_pdf(conn, pdf_path: Path, lib_root: Path) -> dict:
    """Index a single PDF. Returns stats dict."""
    from metis_mcp.embeddings import embed

    source_file = str(pdf_path.relative_to(lib_root))
    domain = pdf_path.parent.name
    title = _infer_title(pdf_path)
    file_size = pdf_path.stat().st_size

    pages, total_pages = _extract_pdf_pages(pdf_path)
    if not pages:
        return {"status": "skip", "reason": "no extractable text", "source_file": source_file}

    # Build per-page chunks, tracking which pages each chunk spans
    all_chunks: List[dict] = []
    for page_num, page_text in pages:
        for chunk_text in _chunk_text(page_text):
            all_chunks.append({
                "page_start": page_num,
                "page_end": page_num,
                "text": chunk_text,
            })

    if not all_chunks:
        return {"status": "skip", "reason": "no chunks produced", "source_file": source_file}

    # Batch embed
    texts = [c["text"] for c in all_chunks]
    embeddings: List[List[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        batch_embeddings = embed(batch, prefix="search_document: ")
        embeddings.extend(batch_embeddings)

    # Insert chunks + vectors
    for idx, (chunk, vec) in enumerate(zip(all_chunks, embeddings)):
        cur = conn.execute(
            """INSERT INTO pdf_chunks
               (source_file, domain, title, page_start, page_end, chunk_idx, chunk_text, char_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (source_file, domain, title,
             chunk["page_start"], chunk["page_end"],
             idx, chunk["text"], len(chunk["text"]))
        )
        rowid = cur.lastrowid
        conn.execute(
            "INSERT INTO vec_pdf_chunks (rowid, embedding) VALUES (?, ?)",
            (rowid, _encode_vec(vec))
        )

    # Auto library card — first chunk as summary snippet
    summary_text = all_chunks[0]["text"][:300].replace("\n", " ")
    _upsert_library_card(conn, title, domain, source_file, summary_text)

    # Record state
    conn.execute(
        """INSERT INTO pdf_index_state
           (source_file, domain, title, total_pages, chunk_count, file_size)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(source_file) DO UPDATE SET
             chunk_count=excluded.chunk_count,
             total_pages=excluded.total_pages,
             indexed_at=datetime('now')""",
        (source_file, domain, title, total_pages, len(all_chunks), file_size)
    )
    conn.commit()

    return {
        "status": "ok",
        "source_file": source_file,
        "domain": domain,
        "pages": total_pages,
        "chunks": len(all_chunks),
    }


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@app.tool()
async def build_pdf_knowledge_db(
    domain_filter: str = "",
    force_rebuild: bool = False,
) -> list[TextContent]:
    """Index all PDFs in the Metis library into a local semantic knowledge database.

    Uses local nomic-embed-text-v1.5-Q (fastembed, ONNX) — no API key required.
    Stores chunks + 768-dim embeddings in pdf_chunks + vec_pdf_chunks tables.
    Skips already-indexed files unless force_rebuild=True.

    Args:
        domain_filter: Only index PDFs whose parent folder contains this string
                       (e.g. "Epidemiology", "NTD", "DHIS2"). Empty = index all.
        force_rebuild: Re-index even files already in the database.
    """
    t0 = time.time()

    lib_root = _library_root()
    if not lib_root.exists():
        return [TextContent(type="text", text=f"Library root not found: {lib_root}")]

    pdfs = _collect_pdfs(domain_filter)
    if not pdfs:
        filter_msg = f" matching '{domain_filter}'" if domain_filter else ""
        return [TextContent(type="text", text=f"No PDFs found in library{filter_msg}.")]

    conn = connect()
    _ensure_schema(conn)

    total = len(pdfs)
    indexed = 0
    skipped = 0
    failed: List[str] = []
    results: List[str] = []

    for i, pdf_path in enumerate(pdfs, 1):
        source_file = str(pdf_path.relative_to(lib_root))

        if not force_rebuild and _already_indexed(conn, source_file):
            skipped += 1
            continue

        if force_rebuild:
            _delete_existing(conn, source_file)

        try:
            result = _index_one_pdf(conn, pdf_path, lib_root)
            if result["status"] == "ok":
                indexed += 1
                results.append(
                    f"  [{i}/{total}] ✓ {source_file} — "
                    f"{result['pages']}p, {result['chunks']} chunks"
                )
            else:
                skipped += 1
                results.append(f"  [{i}/{total}] skip {source_file}: {result['reason']}")
        except Exception as exc:
            failed.append(f"{source_file}: {exc}")
            results.append(f"  [{i}/{total}] ✗ {source_file}: {exc}")

    conn.close()
    elapsed = time.time() - t0

    summary_lines = [
        "══════════════════════════════════════",
        " Metis PDF Knowledge Database — Build",
        "══════════════════════════════════════",
        "",
        f"  PDFs found:    {total}",
        f"  Indexed:       {indexed}",
        f"  Skipped:       {skipped}",
        f"  Failed:        {len(failed)}",
        f"  Time:          {elapsed:.1f}s",
        "",
        "  Per-file results:",
    ]
    summary_lines.extend(results[:60])
    if len(results) > 60:
        summary_lines.append(f"  … and {len(results) - 60} more")
    if failed:
        summary_lines.append("")
        summary_lines.append(f"  Errors ({len(failed)}):")
        summary_lines.extend(f"    {e}" for e in failed[:10])

    summary_lines.extend([
        "",
        "  Next: call search_pdf_knowledge(query) to search the index.",
    ])

    return [TextContent(type="text", text="\n".join(summary_lines))]


@app.tool()
async def search_pdf_knowledge(
    query: str,
    top_k: int = 8,
    domain_filter: str = "",
) -> list[TextContent]:
    """Semantic search over all indexed PDFs in the knowledge library.

    Uses 768-dim nomic-embed ANN search (vec0) against pdf_chunks.
    Returns excerpts with source document, page, domain, and similarity score.

    Args:
        query:         Natural language question or keyword phrase.
        top_k:         Number of results to return (default 8).
        domain_filter: Restrict to a specific domain folder name (optional).
    """
    from metis_mcp.embeddings import embed_query

    if not query.strip():
        return [TextContent(type="text", text="query cannot be empty")]

    conn = connect()
    _ensure_schema(conn)

    # Check index exists
    count = conn.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
    if count == 0:
        conn.close()
        return [TextContent(type="text", text=(
            "No PDFs indexed yet. Run build_pdf_knowledge_db() first."
        ))]

    q_vec = _encode_vec(embed_query(query))

    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        conn.close()
        return [TextContent(type="text", text="sqlite-vec not available — cannot do vector search")]

    # ANN search
    rows = conn.execute(
        f"""SELECT v.rowid, v.distance
            FROM vec_pdf_chunks v
            WHERE v.embedding MATCH ?
              AND k = ?""",
        (q_vec, min(top_k * 3, 50))
    ).fetchall()

    if not rows:
        conn.close()
        return [TextContent(type="text", text="No results found.")]

    rowids = [r[0] for r in rows]
    distances = {r[0]: r[1] for r in rows}

    placeholders = ",".join("?" * len(rowids))
    chunks = conn.execute(
        f"""SELECT id, source_file, domain, title, page_start, page_end, chunk_text
            FROM pdf_chunks WHERE id IN ({placeholders})""",
        rowids
    ).fetchall()
    conn.close()

    # Apply domain filter
    if domain_filter:
        df = domain_filter.lower()
        chunks = [c for c in chunks if df in c[2].lower()]

    # Sort by distance ascending
    chunks.sort(key=lambda c: distances.get(c[0], 9999))
    chunks = chunks[:top_k]

    if not chunks:
        return [TextContent(type="text", text=f"No results in domain '{domain_filter}'.")]

    lines = [
        f"**Knowledge search: '{query}'**",
        f"Top {len(chunks)} results from {count:,} indexed chunks",
        "",
    ]
    for rank, c in enumerate(chunks, 1):
        chunk_id, source_file, domain, title, page_start, page_end, chunk_text = c
        dist = distances.get(chunk_id, 0)
        score = max(0.0, 1.0 - dist)
        excerpt = chunk_text[:400].replace("\n", " ")
        if len(chunk_text) > 400:
            excerpt += "…"
        lines.extend([
            f"**{rank}. {title}** (score: {score:.2f})",
            f"   Domain: {domain} | Pages: {page_start}–{page_end} | File: {source_file}",
            f"   > {excerpt}",
            "",
        ])

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def get_pdf_index_stats() -> list[TextContent]:
    """Report statistics on the PDF knowledge database index.

    Returns per-domain breakdown of indexed files and chunk counts,
    total chunks, estimated DB size, and list of un-indexed PDFs.
    """
    conn = connect()
    _ensure_schema(conn)

    total_chunks = conn.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
    total_docs = conn.execute("SELECT COUNT(*) FROM pdf_index_state").fetchone()[0]

    domain_rows = conn.execute(
        """SELECT domain, COUNT(*) as docs, SUM(chunk_count) as chunks, SUM(file_size) as bytes
           FROM pdf_index_state
           GROUP BY domain
           ORDER BY chunks DESC"""
    ).fetchall()

    conn.close()

    # PDFs on disk
    all_pdfs = _collect_pdfs()
    lib_root = _library_root()

    conn2 = connect()
    indexed_files = {
        r[0] for r in conn2.execute("SELECT source_file FROM pdf_index_state").fetchall()
    }
    conn2.close()

    pending = [
        str(p.relative_to(lib_root))
        for p in all_pdfs
        if str(p.relative_to(lib_root)) not in indexed_files
    ]

    lines = [
        "══════════════════════════════════════",
        " PDF Knowledge Database — Index Stats",
        "══════════════════════════════════════",
        "",
        f"  Documents indexed: {total_docs}",
        f"  Total chunks:      {total_chunks:,}",
        f"  Estimated DB size: ~{(total_chunks * 3800) // (1024*1024)} MB "
          f"(text + embeddings)",
        "",
        "  By domain:",
    ]

    for row in domain_rows:
        domain, docs, chunks, size_bytes = row
        size_mb = (size_bytes or 0) / (1024 * 1024)
        lines.append(f"    {domain:<40} {docs:>3} docs  {chunks or 0:>6} chunks  ({size_mb:.1f} MB)")

    if pending:
        lines.extend([
            "",
            f"  Not yet indexed ({len(pending)} PDFs):",
        ])
        for p in pending[:20]:
            lines.append(f"    - {p}")
        if len(pending) > 20:
            lines.append(f"    … and {len(pending) - 20} more")
        lines.extend([
            "",
            "  Run build_pdf_knowledge_db() to index these.",
        ])

    return [TextContent(type="text", text="\n".join(lines))]
