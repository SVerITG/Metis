#!/usr/bin/env python3
"""build_knowledge_db.py — Standalone PDF → knowledge database pipeline (Phase L7).

Runs outside the MCP server (no MCP needed). Reads all PDFs from the Metis
library, extracts text, chunks, embeds with local fastembed (nomic-embed,
no API key needed), and writes pdf_chunks + vec_pdf_chunks into metis.sqlite.

Usage:
    python build_knowledge_db.py
    python build_knowledge_db.py --domain "Epidemiology"
    python build_knowledge_db.py --force
    python build_knowledge_db.py --library-dir /path/to/library --db /path/to/metis.sqlite

Called by installer post-build step and seed_ph_database.py --index-pdfs.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import struct
import sys
import time
from pathlib import Path
from typing import List, Optional

# ── Config ─────────────────────────────────────────────────────────────────────

CHUNK_CHARS   = 3200
OVERLAP_CHARS = 400
EMBED_BATCH   = 32
EMBEDDING_DIM = 768

_LIBRARY_SUBDIRS = [
    "open-access-books",
    "papers",
    "disease-areas",
    "methods",
    "concepts",
]

_ACRONYMS = {
    "WHO", "CDC", "NTD", "HAT", "HIV", "AMR", "NCD", "UHC", "SDH",
    "DHIS2", "AFRO", "PAHO", "ECDC", "GBD", "DALY", "BMI", "TB",
    "ANC", "PHC", "AI", "ML", "API", "PDF",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _encode_vec(v: List[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _clean_text(text: str) -> str:
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = text.split("\n")
    cleaned = [l for l in lines if not (
        l.strip() and len(l.strip()) <= 4 and (l.strip().isdigit() or l.strip().isupper())
    )]
    return "\n".join(cleaned).strip()


def _chunk_text(text: str) -> List[str]:
    if len(text) <= CHUNK_CHARS:
        return [text] if text.strip() else []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_CHARS
        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break
        boundary = text.rfind("\n\n", start, end)
        if boundary == -1 or boundary <= start + CHUNK_CHARS // 2:
            boundary = text.rfind(". ", start, end)
        if boundary == -1 or boundary <= start + CHUNK_CHARS // 2:
            boundary = end
        else:
            boundary += 2
        chunk = text[start:boundary].strip()
        if chunk:
            chunks.append(chunk)
        start = boundary - OVERLAP_CHARS
        if start < 0:
            start = 0
    return chunks


def _infer_title(path: Path) -> str:
    stem = re.sub(r"^\d+_", "", path.stem)
    stem = stem.replace("-", " ").replace("_", " ")
    words = stem.split()
    titled = [w.upper() if w.upper() in _ACRONYMS else w.capitalize() for w in words]
    return " ".join(titled)


def _extract_pages(pdf_path: Path) -> tuple[List[tuple[int, str]], int]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path), strict=False)
        total = len(reader.pages)
        pages = []
        for i, page in enumerate(reader.pages):
            try:
                text = _clean_text(page.extract_text() or "")
                if text.strip():
                    pages.append((i + 1, text))
            except Exception:
                continue
        return pages, total
    except Exception:
        return [], 0


def _setup_schema(conn: sqlite3.Connection) -> None:
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception as e:
        print(f"  ⚠ sqlite-vec not loaded ({e}) — vector search won't work")

    conn.executescript(f"""
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
    """)
    try:
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_pdf_chunks USING vec0(
                rowid INTEGER PRIMARY KEY,
                embedding float[{EMBEDDING_DIM}]
            )
        """)
    except Exception:
        pass
    conn.commit()


# ── Main pipeline ──────────────────────────────────────────────────────────────

def index_pdfs(
    library_dir: Path,
    db_path: Path,
    domain_filter: str = "",
    force: bool = False,
    verbose: bool = True,
) -> dict:
    """Run the full PDF → chunks → embeddings → SQLite pipeline.

    Returns stats dict: {total, indexed, skipped, failed, elapsed}.
    """
    def log(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    log(f"\n══════════════════════════════════════════════════")
    log(f" Metis PDF Knowledge DB — Build")
    log(f" Library: {library_dir}")
    log(f" Database: {db_path}")
    if domain_filter:
        log(f" Domain filter: {domain_filter}")
    log(f"══════════════════════════════════════════════════\n")

    # Collect PDFs
    pdfs: List[Path] = []
    for subdir in _LIBRARY_SUBDIRS:
        d = library_dir / subdir
        if d.exists():
            for p in d.rglob("*.pdf"):
                if domain_filter and domain_filter.lower() not in p.parent.name.lower():
                    continue
                pdfs.append(p)
    pdfs.sort()

    if not pdfs:
        log("  No PDFs found.")
        return {"total": 0, "indexed": 0, "skipped": 0, "failed": 0, "elapsed": 0}

    log(f"  Found {len(pdfs)} PDFs\n")

    # Load embedding model once
    log("  Loading embedding model (nomic-embed-text-v1.5-Q)…")
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5-Q")
        log("  ✓ Model ready\n")
    except Exception as e:
        log(f"  ✗ Could not load fastembed: {e}")
        log("    Install with: pip install fastembed")
        return {"total": len(pdfs), "indexed": 0, "skipped": 0, "failed": len(pdfs), "elapsed": 0}

    def batch_embed(texts: List[str]) -> List[List[float]]:
        prefixed = ["search_document: " + t for t in texts]
        results = []
        for i in range(0, len(prefixed), EMBED_BATCH):
            batch = prefixed[i:i + EMBED_BATCH]
            results.extend(e.tolist() for e in model.embed(batch))
        return results

    conn = sqlite3.connect(str(db_path))
    _setup_schema(conn)

    t0 = time.time()
    indexed = skipped = 0
    failed: List[str] = []

    for i, pdf_path in enumerate(pdfs, 1):
        source_file = str(pdf_path.relative_to(library_dir))
        domain = pdf_path.parent.name
        title = _infer_title(pdf_path)
        file_size = pdf_path.stat().st_size

        # Skip if already indexed
        if not force:
            row = conn.execute(
                "SELECT chunk_count FROM pdf_index_state WHERE source_file = ?",
                (source_file,)
            ).fetchone()
            if row and row[0] > 0:
                skipped += 1
                log(f"  [{i}/{len(pdfs)}] skip (indexed)  {source_file}")
                continue

        # Force rebuild: delete existing
        if force:
            existing = conn.execute(
                "SELECT id FROM pdf_chunks WHERE source_file = ?", (source_file,)
            ).fetchall()
            for row in existing:
                conn.execute("DELETE FROM vec_pdf_chunks WHERE rowid = ?", (row[0],))
            conn.execute("DELETE FROM pdf_chunks WHERE source_file = ?", (source_file,))
            conn.execute("DELETE FROM pdf_index_state WHERE source_file = ?", (source_file,))
            conn.commit()

        # Extract text
        pages, total_pages = _extract_pages(pdf_path)
        if not pages:
            log(f"  [{i}/{len(pdfs)}] ✗ no text  {source_file}")
            failed.append(source_file)
            continue

        # Chunk
        all_chunks: List[dict] = []
        for page_num, page_text in pages:
            for ct in _chunk_text(page_text):
                all_chunks.append({"page": page_num, "text": ct})

        if not all_chunks:
            log(f"  [{i}/{len(pdfs)}] ✗ no chunks  {source_file}")
            failed.append(source_file)
            continue

        # Embed
        try:
            texts = [c["text"] for c in all_chunks]
            embeddings = batch_embed(texts)
        except Exception as e:
            log(f"  [{i}/{len(pdfs)}] ✗ embed error  {source_file}: {e}")
            failed.append(source_file)
            continue

        # Store
        for idx, (chunk, vec) in enumerate(zip(all_chunks, embeddings)):
            cur = conn.execute(
                """INSERT INTO pdf_chunks
                   (source_file, domain, title, page_start, page_end,
                    chunk_idx, chunk_text, char_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (source_file, domain, title,
                 chunk["page"], chunk["page"],
                 idx, chunk["text"], len(chunk["text"]))
            )
            rowid = cur.lastrowid
            try:
                conn.execute(
                    "INSERT INTO vec_pdf_chunks (rowid, embedding) VALUES (?, ?)",
                    (rowid, _encode_vec(vec))
                )
            except Exception:
                pass

        # Library card
        if all_chunks:
            snippet = all_chunks[0]["text"][:300].replace("\n", " ")
            existing_card = conn.execute(
                "SELECT id FROM library_cards WHERE title = ?", (title,)
            ).fetchone()
            if not existing_card:
                try:
                    conn.execute(
                        "INSERT INTO library_cards (title, domain, summary, source_path) "
                        "VALUES (?, ?, ?, ?)",
                        (title, domain, snippet, source_file)
                    )
                except Exception:
                    pass

        conn.execute(
            """INSERT INTO pdf_index_state
               (source_file, domain, title, total_pages, chunk_count, file_size)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(source_file) DO UPDATE SET
                 chunk_count=excluded.chunk_count,
                 total_pages=excluded.total_pages,
                 file_size=excluded.file_size,
                 indexed_at=datetime('now')""",
            (source_file, domain, title, total_pages, len(all_chunks), file_size)
        )
        conn.commit()

        size_kb = file_size // 1024
        log(f"  [{i}/{len(pdfs)}] ✓ {pdf_path.name}  "
            f"({total_pages}p, {len(all_chunks)} chunks, {size_kb}KB)")
        indexed += 1

    elapsed = time.time() - t0
    conn.close()

    total_chunks = sum(
        sqlite3.connect(str(db_path)).execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()
    )

    log(f"\n══════════════════════════════════════════════════")
    log(f"  Done in {elapsed:.1f}s")
    log(f"  Indexed:        {indexed}")
    log(f"  Skipped:        {skipped}")
    log(f"  Failed:         {len(failed)}")
    log(f"  Total chunks:   {total_chunks:,}")
    log(f"  DB:             {db_path}")
    if failed:
        log(f"\n  Failed files:")
        for f in failed:
            log(f"    - {f}")
    log(f"══════════════════════════════════════════════════\n")

    return {
        "total": len(pdfs),
        "indexed": indexed,
        "skipped": skipped,
        "failed": len(failed),
        "elapsed": elapsed,
        "total_chunks": total_chunks,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Metis PDF knowledge database (Phase L)"
    )
    parser.add_argument(
        "--library-dir", type=Path, default=None,
        help="Path to knowledge/library/ (default: auto-detect from METIS_RC_ROOT)"
    )
    parser.add_argument(
        "--db", type=Path, default=None,
        help="Path to metis.sqlite (default: auto-detect from METIS_RC_ROOT)"
    )
    parser.add_argument(
        "--domain", type=str, default="",
        help="Only index PDFs in folders containing this string"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-index files even if already in the database"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-file output"
    )
    args = parser.parse_args()

    import os

    # Resolve paths
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        default_lib = Path(rc_root) / "knowledge" / "library"
        default_db  = Path(rc_root) / "system" / "app" / "data" / "metis.sqlite"
    else:
        # Guess from script location: install/ → system/ → metis/
        script_root = Path(__file__).resolve().parent.parent.parent
        default_lib = script_root / "knowledge" / "library"
        default_db  = script_root / "system" / "app" / "data" / "metis.sqlite"

    library_dir = args.library_dir or default_lib
    db_path     = args.db or default_db

    if not library_dir.exists():
        print(f"Error: library directory not found: {library_dir}", file=sys.stderr)
        sys.exit(1)
    if not db_path.exists():
        print(f"Error: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    stats = index_pdfs(
        library_dir=library_dir,
        db_path=db_path,
        domain_filter=args.domain,
        force=args.force,
        verbose=not args.quiet,
    )

    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
