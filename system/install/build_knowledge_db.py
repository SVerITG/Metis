#!/usr/bin/env python3
"""build_knowledge_db.py — Layered PDF → knowledge database pipeline (Phase L7).

Standalone script (no MCP needed). Indexes PDFs into named knowledge layers
using local fastembed (nomic-embed-text-v1.5-Q, no API key needed).

Built-in databases (base Metis):
  ph-background   Layer 1: General MPH, global health, health systems
  epi-methods     Layer 2: Epidemiology methods, biostatistics, spatial, multilevel

Domain-specific layers (added by variant installs, e.g. Metis_PH):
  hat-specialist  Metis_PH specialist literature — seeded by seed_ph_database.py

Usage:
    python3 build_knowledge_db.py                              # index all layers
    python3 build_knowledge_db.py --database ph-background    # one layer only
    python3 build_knowledge_db.py --list                      # show layers + status
    python3 build_knowledge_db.py --library-dir /path/to/library --db /path/to/metis.sqlite

WSL stability flags:
    --batch-size 4     Chunks per embedding call (default 4, lower = less RAM)
    --sleep 0.5        Seconds to pause between PDFs (default 0.3)
    --timeout 90       Per-PDF extraction timeout in seconds (default 90)
    --max-pages 300    Skip PDFs with more pages than this (default 400)
"""

from __future__ import annotations

# Set thread limits BEFORE any numpy/onnx import to prevent WSL OOM
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import argparse
import gc
import re
import signal
import sqlite3
import struct
import sys
import time
from pathlib import Path
from typing import Generator, List, Optional, Tuple

# ── Layer definitions ─────────────────────────────────────────────────────────

DATABASES = [
    {
        "slug": "hat-specialist",
        "name": "Specialist Literature (Metis_PH)",
        "description": (
            "Metis_PH specialist layer: domain research corpus — diagnostics, screening & surveillance, "
            "statistics & modelling, methodology, epidemiology, elimination, WHO Atlas, clinical."
        ),
        "layer": 3,
        "color": "#dc3545",
        "folders": [
            "Diagnostics",
            "Screening & Surveillance",
            "Statistics & Mathematical Modelling",
            "Methodology",
            "Epidemiology",
            "WHO Atlas",
            "Elimination",
            "Integration",
            "Clinical & Treatment",
            "History",
            "Overview",
            "Burden",
            "Vector & Vector Control",
            "Determinants and risks",
            "Community",
            "Health Economics",
            "PNLTHA",
            "Multi-NTD",
        ],
    },
    {
        "slug": "ph-background",
        "name": "Public Health Background",
        "description": (
            "Foundation layer: general MPH knowledge — health systems, global health, "
            "governance, social determinants, environmental health, NCDs, nutrition, "
            "mental health, maternal & child health, health economics, DHIS2."
        ),
        "layer": 1,
        "color": "#0d6efd",
        "folders": [
            "open-access-books/Health Systems & Financing",
            "open-access-books/Global Health & Health Systems",
            "open-access-books/Global Health Governance",
            "open-access-books/Social Determinants & Equity",
            "open-access-books/Environmental & Occupational Health",
            "open-access-books/Infectious Disease & Surveillance",
            "open-access-books/Maternal & Child Health",
            "open-access-books/NCDs",
            "open-access-books/Nutrition & Food Security",
            "open-access-books/Mental Health",
            "open-access-books/Health Economics",
            "open-access-books/One Health & AMR",
            "open-access-books/Climate Change & Health",
            "open-access-books/Health Informatics & DHIS2",
            "open-access-books/Course Materials",
        ],
    },
    {
        "slug": "epi-methods",
        "name": "Epidemiology & Methods",
        "description": (
            "Methods layer: epidemiology foundations, biostatistics, spatial epidemiology, "
            "multilevel models, research methods, field epidemiology, scientific writing."
        ),
        "layer": 2,
        "color": "#198754",
        "folders": [
            "open-access-books/Epidemiology & Methods",
            "open-access-books/Biostatistics & Methods",
            "open-access-books/Spatial Epidemiology",
            "open-access-books/Multilevel Models",
            "open-access-books/Research Methods & Writing",
            "open-access-books/Field Epidemiology",
            "methods",
            "concepts",
        ],
    },
]

CHUNK_CHARS   = 3200
OVERLAP_CHARS = 400
EMBEDDING_DIM = 768

_ACRONYMS = {"WHO","CDC","NTD","HAT","HIV","AMR","NCD","UHC","SDH","DHIS2",
             "AFRO","PAHO","ECDC","GBD","DALY","TB","ANC","AI","ML","API"}

# How many PDFs to process before closing and reopening the SQLite connection
# (releases WAL file memory that accumulates over a long run)
_CONN_RECYCLE_EVERY = 20


# ── Helpers ───────────────────────────────────────────────────────────────────

def _encode_vec(v: List[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _clean_text(text: str) -> str:
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = text.split("\n")
    return "\n".join(
        l for l in lines
        if not (l.strip() and len(l.strip()) <= 4
                and (l.strip().isdigit() or l.strip().isupper()))
    ).strip()


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
    return " ".join(
        w.upper() if w.upper() in _ACRONYMS else w.capitalize()
        for w in stem.split()
    )


class _Timeout(Exception):
    pass


def _is_valid_pdf(path: Path) -> bool:
    """Check the file header — rejects HTML/XML files disguised as .pdf."""
    try:
        with open(path, "rb") as f:
            return f.read(8).startswith(b"%PDF")
    except Exception:
        return False


def _try_pymupdf(path: Path, max_pages: int) -> Tuple[List[Tuple[int, str]], int]:
    import fitz  # PyMuPDF
    doc = fitz.open(str(path))
    total = len(doc)
    if total > max_pages:
        doc.close()
        return [], -1
    pages = []
    for i in range(total):
        try:
            text = _clean_text(doc[i].get_text("text") or "")
            if text.strip():
                pages.append((i + 1, text))
        except Exception:
            continue
    doc.close()
    return pages, total


def _try_pdfplumber(path: Path, max_pages: int) -> Tuple[List[Tuple[int, str]], int]:
    import pdfplumber
    with pdfplumber.open(str(path)) as pdf:
        total = len(pdf.pages)
        if total > max_pages:
            return [], -1
        pages = []
        for i, page in enumerate(pdf.pages):
            try:
                text = _clean_text(page.extract_text() or "")
                if text.strip():
                    pages.append((i + 1, text))
            except Exception:
                continue
    return pages, total


def _try_pypdf(path: Path, max_pages: int) -> Tuple[List[Tuple[int, str]], int]:
    from pypdf import PdfReader
    reader = PdfReader(str(path), strict=False)
    total = len(reader.pages)
    if total > max_pages:
        return [], -1
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            text = _clean_text(page.extract_text() or "")
            if text.strip():
                pages.append((i + 1, text))
        except Exception:
            continue
    return pages, total


def _extract_pages_safe(
    pdf_path: Path,
    timeout_secs: int,
    max_pages: int,
) -> Tuple[List[Tuple[int, str]], int]:
    """Multi-strategy extraction: PyMuPDF → pdfplumber → pypdf.

    Returns (pages, total_page_count).
    Special return codes: -1 too large, -2 timeout, -3 OOM, -4 not a PDF.
    """
    # Reject HTML/XML files immediately — no point trying any parser
    if not _is_valid_pdf(pdf_path):
        return [], -4

    def _handler(signum, frame):
        raise _Timeout()

    use_alarm = hasattr(signal, "SIGALRM")
    if use_alarm:
        signal.signal(signal.SIGALRM, _handler)
        signal.alarm(timeout_secs)

    try:
        # Strategy 1: PyMuPDF — fastest, best for WHO/World Bank PDFs
        try:
            pages, total = _try_pymupdf(pdf_path, max_pages)
            if total == -1:
                return [], -1
            if pages:
                return pages, total
        except Exception:
            pass

        # Strategy 2: pdfplumber — better for complex column layouts and tables
        try:
            pages, total = _try_pdfplumber(pdf_path, max_pages)
            if total == -1:
                return [], -1
            if pages:
                return pages, total
        except Exception:
            pass

        # Strategy 3: pypdf — lightweight fallback
        try:
            pages, total = _try_pypdf(pdf_path, max_pages)
            if total == -1:
                return [], -1
            if pages:
                return pages, total
            # All three returned 0 text pages — likely a scanned/image-only PDF
            return [], total
        except Exception:
            return [], 0

    except _Timeout:
        return [], -2
    except MemoryError:
        return [], -3
    finally:
        if use_alarm:
            signal.alarm(0)


def _stream_chunks(
    pages: List[Tuple[int, str]],
) -> Generator[Tuple[int, str], None, None]:
    """Yield (page_num, chunk_text) one at a time — never builds the full list."""
    for page_num, page_text in pages:
        for ct in _chunk_text(page_text):
            yield page_num, ct


# ── Schema ─────────────────────────────────────────────────────────────────────

def _setup_schema(conn: sqlite3.Connection) -> None:
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception as e:
        print(f"  ⚠ sqlite-vec not loaded ({e}) — vector search disabled", flush=True)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS library_cards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT,
            domain      TEXT,
            summary     TEXT,
            source_path TEXT,
            authors     TEXT DEFAULT '',
            year        INTEGER,
            source      TEXT DEFAULT '',
            tags        TEXT DEFAULT '',
            status      TEXT DEFAULT 'unread',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS knowledge_databases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slug        TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            layer       INTEGER DEFAULT 1,
            color       TEXT DEFAULT '#6c757d',
            doc_count   INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0,
            last_built  TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            db_id       INTEGER NOT NULL DEFAULT 0,
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
        CREATE TABLE IF NOT EXISTS pdf_index_state (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            db_id       INTEGER NOT NULL DEFAULT 0,
            source_file TEXT NOT NULL UNIQUE,
            domain      TEXT DEFAULT '',
            title       TEXT DEFAULT '',
            total_pages INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0,
            file_size   INTEGER DEFAULT 0,
            indexed_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    for table, col in [("pdf_chunks", "db_id"), ("pdf_index_state", "db_id")]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_pdf_chunks_source ON pdf_chunks (source_file)",
        "CREATE INDEX IF NOT EXISTS idx_pdf_chunks_db_id  ON pdf_chunks (db_id)",
        "CREATE INDEX IF NOT EXISTS idx_pdf_chunks_domain ON pdf_chunks (domain)",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass

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


def _seed_databases(conn: sqlite3.Connection) -> dict:
    slug_to_id = {}
    for db in DATABASES:
        existing = conn.execute(
            "SELECT id FROM knowledge_databases WHERE slug = ?", (db["slug"],)
        ).fetchone()
        if existing:
            slug_to_id[db["slug"]] = existing[0]
        else:
            cur = conn.execute(
                "INSERT INTO knowledge_databases (slug, name, description, layer, color) "
                "VALUES (?, ?, ?, ?, ?)",
                (db["slug"], db["name"], db["description"], db["layer"], db["color"])
            )
            slug_to_id[db["slug"]] = cur.lastrowid
    conn.commit()
    return slug_to_id


def _open_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")  # 32 MB page cache max
    conn.execute("PRAGMA temp_store=MEMORY")
    _setup_schema(conn)
    return conn


# ── Core index function ────────────────────────────────────────────────────────

def index_database(
    db_def: dict,
    db_id: int,
    library_dir: Path,
    db_path: Path,
    model,
    force: bool = False,
    verbose: bool = True,
    embed_batch: int = 4,
    sleep_between: float = 0.3,
    timeout_secs: int = 90,
    max_pages: int = 400,
) -> dict:
    def log(msg: str) -> None:
        if verbose:
            print(msg, flush=True)

    slug = db_def["slug"]
    name = db_def["name"]

    # Support per-database library_dir override (e.g. HAT corpus at a different path)
    effective_dir = Path(db_def["library_dir_override"]) if db_def.get("library_dir_override") else library_dir

    pdfs: List[Path] = []
    for folder in db_def["folders"]:
        d = effective_dir / folder
        if d.exists():
            pdfs.extend(sorted(d.rglob("*.pdf")))

    if not pdfs:
        log(f"  [{slug}] No PDFs found — skipping")
        return {"total": 0, "indexed": 0, "skipped": 0, "failed": 0}

    log(f"\n  ── {name} [{slug}] ──")
    log(f"     {len(pdfs)} PDFs across {len(db_def['folders'])} folders")
    log(f"     batch={embed_batch}  sleep={sleep_between}s  timeout={timeout_secs}s  max_pages={max_pages}")

    conn = _open_conn(db_path)
    indexed = skipped = 0
    failed: List[str] = []

    for i, pdf_path in enumerate(pdfs, 1):
        source_file = str(pdf_path.relative_to(effective_dir))
        domain      = pdf_path.parent.name
        title       = _infer_title(pdf_path)
        file_size   = pdf_path.stat().st_size

        # Recycle connection every N PDFs to release WAL memory
        if i % _CONN_RECYCLE_EVERY == 0:
            try:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            except Exception:
                pass  # non-fatal
            conn.close()
            conn = _open_conn(db_path)

        # Skip if already indexed for this db_id
        if not force:
            row = conn.execute(
                "SELECT chunk_count FROM pdf_index_state WHERE source_file = ? AND db_id = ?",
                (source_file, db_id),
            ).fetchone()
            if row and row[0] > 0:
                skipped += 1
                continue

        if force:
            chunk_ids = [r[0] for r in conn.execute(
                "SELECT id FROM pdf_chunks WHERE source_file = ? AND db_id = ?",
                (source_file, db_id),
            ).fetchall()]
            for cid in chunk_ids:
                conn.execute("DELETE FROM vec_pdf_chunks WHERE rowid = ?", (cid,))
            conn.execute("DELETE FROM pdf_chunks WHERE source_file = ? AND db_id = ?",
                         (source_file, db_id))
            conn.execute("DELETE FROM pdf_index_state WHERE source_file = ?", (source_file,))
            conn.commit()

        pages, total_pages = _extract_pages_safe(pdf_path, timeout_secs, max_pages)

        if total_pages == -4:
            log(f"  [{i}/{len(pdfs)}] 🚫 not a PDF (HTML/XML header)  {pdf_path.name}")
            skipped += 1
            continue
        if total_pages == -1:
            log(f"  [{i}/{len(pdfs)}] ⏭ skipped (>{max_pages}p)  {pdf_path.name}")
            skipped += 1
            continue
        if total_pages == -2:
            log(f"  [{i}/{len(pdfs)}] ⏱ timeout  {pdf_path.name}")
            failed.append(source_file)
            gc.collect()
            continue
        if total_pages == -3:
            log(f"  [{i}/{len(pdfs)}] 💥 OOM during extraction  {pdf_path.name}")
            failed.append(source_file)
            gc.collect()
            continue
        if not pages:
            log(f"  [{i}/{len(pdfs)}] ✗ no text after 3 strategies (scanned/image PDF?)  {pdf_path.name}")
            failed.append(source_file)
            continue

        # Stream chunks and embed in small batches — never hold entire PDF in RAM
        chunk_idx   = 0
        chunk_count = 0
        first_text  = ""
        batch_pages: List[int]  = []
        batch_texts: List[str]  = []

        def flush_batch() -> None:
            nonlocal chunk_count, first_text
            if not batch_texts:
                return
            try:
                prefixed = ["search_document: " + t for t in batch_texts]
                vecs = list(model.embed(prefixed))
            except MemoryError:
                log(f"  [{i}/{len(pdfs)}] ⚠ OOM during embed — flushing partial batch")
                batch_pages.clear()
                batch_texts.clear()
                gc.collect()
                return
            except Exception as e:
                log(f"  [{i}/{len(pdfs)}] ⚠ embed error: {e}")
                batch_pages.clear()
                batch_texts.clear()
                return

            nonlocal chunk_idx
            for page_num, text, vec in zip(batch_pages, batch_texts, vecs):
                if not first_text:
                    first_text = text[:300]
                cur = conn.execute(
                    """INSERT INTO pdf_chunks
                       (db_id, source_file, domain, title, page_start, page_end,
                        chunk_idx, chunk_text, char_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (db_id, source_file, domain, title,
                     page_num, page_num, chunk_idx, text, len(text)),
                )
                rowid = cur.lastrowid
                try:
                    conn.execute(
                        "INSERT INTO vec_pdf_chunks (rowid, embedding) VALUES (?, ?)",
                        (rowid, _encode_vec(vec.tolist())),
                    )
                except Exception:
                    pass
                chunk_idx   += 1
                chunk_count += 1

            conn.commit()
            batch_pages.clear()
            batch_texts.clear()
            del vecs
            gc.collect()

        try:
            for page_num, chunk_text in _stream_chunks(pages):
                batch_pages.append(page_num)
                batch_texts.append(chunk_text)
                if len(batch_texts) >= embed_batch:
                    flush_batch()
            flush_batch()  # final partial batch
        except MemoryError:
            log(f"  [{i}/{len(pdfs)}] 💥 OOM streaming  {pdf_path.name}")
            failed.append(source_file)
            del pages, batch_pages, batch_texts
            gc.collect()
            continue
        except Exception as e:
            log(f"  [{i}/{len(pdfs)}] ✗ error  {pdf_path.name}: {e}")
            failed.append(source_file)
            continue
        finally:
            del pages
            gc.collect()

        if chunk_count == 0:
            failed.append(source_file)
            continue

        # Add a library card if one doesn't exist
        if first_text:
            if not conn.execute("SELECT id FROM library_cards WHERE title = ?",
                                (title,)).fetchone():
                try:
                    conn.execute(
                        "INSERT INTO library_cards (title, domain, summary, source_path) "
                        "VALUES (?, ?, ?, ?)",
                        (title, domain, first_text.replace("\n", " "), source_file),
                    )
                except Exception:
                    pass

        conn.execute(
            """INSERT INTO pdf_index_state
               (db_id, source_file, domain, title, total_pages, chunk_count, file_size)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source_file) DO UPDATE SET
                 db_id=excluded.db_id, chunk_count=excluded.chunk_count,
                 total_pages=excluded.total_pages, indexed_at=datetime('now')""",
            (db_id, source_file, domain, title, total_pages, chunk_count, file_size),
        )
        conn.commit()

        pct = int(i / len(pdfs) * 100)
        log(f"  [{i}/{len(pdfs)}  {pct}%] ✓ {pdf_path.name}  ({total_pages}p, {chunk_count} chunks)")
        indexed += 1

        if sleep_between > 0:
            time.sleep(sleep_between)

    # Final stats update + WAL checkpoint (checkpoint is best-effort; data is safe either way)
    docs   = conn.execute("SELECT COUNT(*) FROM pdf_index_state WHERE db_id=?", (db_id,)).fetchone()[0]
    chunks = conn.execute("SELECT COUNT(*) FROM pdf_chunks WHERE db_id=?",      (db_id,)).fetchone()[0]
    conn.execute(
        "UPDATE knowledge_databases SET doc_count=?, chunk_count=?, last_built=datetime('now') WHERE id=?",
        (docs, chunks, db_id),
    )
    conn.commit()
    try:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    except Exception:
        pass  # checkpoint is non-fatal; Windows/OneDrive may hold a brief lock
    conn.close()

    return {"total": len(pdfs), "indexed": indexed, "skipped": skipped, "failed": len(failed)}


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Metis layered PDF knowledge databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--database",    type=str,   default="",
                        help="Slug to index (default: all built-in layers)")
    parser.add_argument("--library-dir", type=Path,  default=None)
    parser.add_argument("--db",          type=Path,  default=None)
    parser.add_argument("--force",       action="store_true",
                        help="Re-index already-indexed PDFs")
    parser.add_argument("--quiet",       action="store_true")
    parser.add_argument("--list",        action="store_true",
                        help="Show databases and index status, then exit")
    parser.add_argument("--batch-size",  type=int,   default=4,
                        help="Chunks per embedding call (default 4, lower = less RAM)")
    parser.add_argument("--sleep",       type=float, default=0.3,
                        help="Seconds to pause between PDFs (default 0.3)")
    parser.add_argument("--timeout",     type=int,   default=90,
                        help="Per-PDF extraction timeout in seconds (default 90)")
    parser.add_argument("--max-pages",   type=int,   default=400,
                        help="Skip PDFs with more pages than this (default 400)")
    args = parser.parse_args()

    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        default_lib = Path(rc_root) / "knowledge" / "library"
        default_db  = Path(rc_root) / "system" / "app" / "data" / "metis.sqlite"
    else:
        root = Path(__file__).resolve().parent.parent.parent
        default_lib = root / "knowledge" / "library"
        default_db  = root / "system" / "app" / "data" / "metis.sqlite"

    library_dir = args.library_dir or default_lib
    db_path     = args.db or default_db

    if not library_dir.exists():
        print(f"Error: library directory not found: {library_dir}", file=sys.stderr)
        sys.exit(1)
    if not db_path.exists():
        print(f"Error: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    verbose = not args.quiet

    conn = _open_conn(db_path)
    slug_to_id = _seed_databases(conn)

    if args.list:
        print("\nMetis Knowledge Databases\n")
        layer_labels = {1: "Foundation", 2: "Specialist", 3: "Methods"}
        last_layer = None
        for db in DATABASES:
            if db["layer"] != last_layer:
                print(f"  ── {layer_labels.get(db['layer'], 'Custom')} ──")
                last_layer = db["layer"]
            db_id = slug_to_id.get(db["slug"], 0)
            row = conn.execute(
                "SELECT doc_count, chunk_count, last_built FROM knowledge_databases WHERE id=?",
                (db_id,),
            ).fetchone()
            docs, chunks, built = row if row else (0, 0, None)
            status    = f"{docs} docs, {chunks:,} chunks" if docs else "not indexed"
            built_str = f" — built {built[:10]}" if built else ""
            print(f"  [{db['slug']}]  {db['name']}")
            print(f"    {status}{built_str}")
        conn.close()
        return

    conn.close()

    to_build = [d for d in DATABASES if not args.database or d["slug"] == args.database]
    if not to_build:
        print(f"Unknown slug '{args.database}'. Options: "
              + ", ".join(d["slug"] for d in DATABASES), file=sys.stderr)
        sys.exit(1)

    # For hat-specialist: if --library-dir was not explicitly set, read from user-preferences.json
    for db_def in to_build:
        if db_def["slug"] == "hat-specialist" and args.library_dir is None:
            prefs_path = Path(rc_root) / "system" / "config" / "user-preferences.json" if rc_root else None
            if prefs_path and prefs_path.exists():
                try:
                    import json as _json_prefs
                    prefs = _json_prefs.loads(prefs_path.read_text(encoding="utf-8"))
                    hat_lib = prefs.get("library_path", "")
                    if hat_lib and Path(hat_lib).exists():
                        db_def = dict(db_def)
                        db_def["library_dir_override"] = hat_lib
                        to_build[to_build.index(next(d for d in to_build if d["slug"] == "hat-specialist"))] = db_def
                        if verbose:
                            print(f"  Domain library path: {hat_lib}")
                except Exception as e:
                    print(f"  Warning: could not read user-preferences.json: {e}", file=sys.stderr)

    if verbose:
        print(f"\n══════════════════════════════════════════════════")
        print(f" Metis PDF Knowledge DB — Layered Build")
        print(f" Library: {library_dir}")
        print(f" Database: {db_path}")
        print(f" Building: {', '.join(d['slug'] for d in to_build)}")
        print(f" batch={args.batch_size}  sleep={args.sleep}s  "
              f"timeout={args.timeout}s  max_pages={args.max_pages}")
        print(f"══════════════════════════════════════════════════")

    if verbose:
        print("\n  Loading embedding model (nomic-embed-text-v1.5-Q)…", flush=True)
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(
            model_name="nomic-ai/nomic-embed-text-v1.5-Q",
            max_length=512,
            # Use single thread for WSL stability
            providers=["CPUExecutionProvider"],
        )
        if verbose:
            print("  ✓ Model ready", flush=True)
    except Exception as e:
        print(f"  ✗ fastembed not available: {e}", file=sys.stderr)
        sys.exit(1)

    t0 = time.time()
    totals = {"total": 0, "indexed": 0, "skipped": 0, "failed": 0}

    for db_def in to_build:
        db_id = slug_to_id[db_def["slug"]]
        stats = index_database(
            db_def=db_def,
            db_id=db_id,
            library_dir=library_dir,
            db_path=db_path,
            model=model,
            force=args.force,
            verbose=verbose,
            embed_batch=args.batch_size,
            sleep_between=args.sleep,
            timeout_secs=args.timeout,
            max_pages=args.max_pages,
        )
        for k in totals:
            totals[k] += stats.get(k, 0)

    elapsed = time.time() - t0
    if verbose:
        print(f"\n══════════════════════════════════════════════════")
        print(f"  Done in {elapsed:.1f}s")
        print(f"  Indexed:  {totals['indexed']}")
        print(f"  Skipped:  {totals['skipped']}")
        print(f"  Failed:   {totals['failed']}")
        conn2 = sqlite3.connect(str(db_path))
        total_chunks = conn2.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
        conn2.close()
        print(f"  Chunks:   {total_chunks:,}")
        print(f"══════════════════════════════════════════════════\n")

    sys.exit(0 if totals["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
