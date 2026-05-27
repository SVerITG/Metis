"""Standalone script to index missing PDFs and clean stale entries.

Run with:
  cd system/mcp-server
  .venv/bin/python index_missing.py
"""

import os
import re
import struct
import sqlite3
from pathlib import Path
from typing import List

os.environ.setdefault("FASTEMBED_CACHE_PATH", str(Path.home() / ".cache" / "fastembed"))

RC_ROOT = Path(__file__).parent.parent.parent
DB_PATH = RC_ROOT / "system" / "app" / "data" / "metis.sqlite"
LIB_ROOT = RC_ROOT / "knowledge" / "library"

CHUNK_CHARS = 3200
OVERLAP_CHARS = 400
EMBED_BATCH = 32
EMBEDDING_DIM = 768

STALE_ENTRIES = [
    "open-access-books/Course Materials/DHIS2-Implementation-Guide-2023-DL29GY3.pdf",
    "open-access-books/Health Informatics & DHIS2/WHO-Classification-Digital-Health-Interventions-v1-2018.pdf",
]

MISSING = {
    "ph-background": [
        "open-access-books/Health Security/WHO-International-Health-Regulations-2022.pdf",
        "open-access-books/Health Security/GHSA-2028-Framework.pdf",
        "open-access-books/Infectious Disease & Surveillance/WHO-IDSR-Technical-Guidelines-2010.pdf",
        "open-access-books/Infectious Disease & Surveillance/WHO-Global-TB-Report-2024-Technical.pdf",
        "open-access-books/Infectious Disease & Surveillance/WHO-Global-TB-Report-2024.pdf",
    ],
    "epi-methods": [
        "open-access-books/Epidemiology & Methods/CDC-Principles-Epidemiology-SS1978-ArchiveMirror.pdf",
        "open-access-books/Epidemiology & Methods/Hernan-Robins-Causal-Inference-What-If-2024.pdf",
        "open-access-books/Epidemiology & Methods/WHO-integrated-disease-surveillance-response-guide.pdf",
        "open-access-books/Biostatistics & Methods/Biostatistics-for-Epi-PH-using-R.pdf",
        "open-access-books/Biostatistics & Methods/Gelman-BDA3-bayesian-data-analysis-3rd-ed.pdf",
        "open-access-books/Biostatistics & Methods/LibreTexts-Biostatistics-Open-Learning-Textbook.pdf",
    ],
}

_ACRONYMS = {"WHO","CDC","NTD","HAT","HIV","AMR","NCD","UHC","SDH","DHIS2",
             "AFRO","PAHO","ECDC","GBD","DALY","TB","ANC","AI","ML","API","IDSR","GHSA","IHR"}

def _connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    return conn

def _ensure_vec(conn):
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception as e:
        print(f"  WARNING: sqlite_vec not loaded: {e}")

def _encode_vec(v):
    return struct.pack(f"{len(v)}f", *v)

def _clean_text(text):
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = text.split("\n")
    cleaned = [l for l in lines if not (
        l.strip() and len(l.strip()) <= 4 and (l.strip().isdigit() or l.strip().isupper())
    )]
    return "\n".join(cleaned).strip()

def _chunk_text(text):
    if len(text) <= CHUNK_CHARS:
        return [text] if text.strip() else []
    chunks = []
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

def _infer_title(path):
    stem = re.sub(r"^\d+_", "", path.stem)
    stem = stem.replace("-", " ").replace("_", " ")
    words = stem.split()
    return " ".join(w.upper() if w.upper() in _ACRONYMS else w.capitalize() for w in words)

def _extract_text(pdf_path):
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(str(pdf_path))
        if not text or not text.strip():
            return ""
        return _clean_text(text)
    except Exception as e:
        print(f"  pdfminer error on {pdf_path.name}: {e}")
        return ""

def clean_stale(conn):
    print("\n--- Cleaning stale entries ---")
    for sf in STALE_ENTRIES:
        row = conn.execute("SELECT id FROM pdf_index_state WHERE source_file = ?", (sf,)).fetchone()
        if not row:
            print(f"  (not in DB) {sf}")
            continue
        # Delete chunks and vectors
        chunk_ids = [r[0] for r in conn.execute(
            "SELECT id FROM pdf_chunks WHERE source_file = ?", (sf,)
        ).fetchall()]
        for cid in chunk_ids:
            conn.execute("DELETE FROM vec_pdf_chunks WHERE rowid = ?", (cid,))
        conn.execute("DELETE FROM pdf_chunks WHERE source_file = ?", (sf,))
        conn.execute("DELETE FROM pdf_index_state WHERE source_file = ?", (sf,))
        conn.commit()
        print(f"  ✓ Removed {len(chunk_ids)} chunks + index entry: {sf.split('/')[-1]}")

def index_file(conn, db_slug, rel_path, embed_fn):
    db_id = conn.execute("SELECT id FROM knowledge_databases WHERE slug = ?", (db_slug,)).fetchone()
    if not db_id:
        print(f"  ERROR: db '{db_slug}' not found")
        return

    db_id = db_id[0]
    pdf_path = LIB_ROOT / rel_path

    if not pdf_path.exists():
        print(f"  SKIP (not on disk): {pdf_path.name}")
        return

    # Check if already indexed for this db
    existing = conn.execute(
        "SELECT chunk_count FROM pdf_index_state WHERE source_file = ? AND db_id = ?",
        (rel_path, db_id)
    ).fetchone()
    if existing and existing[0] > 0:
        print(f"  SKIP (already indexed, {existing[0]} chunks): {pdf_path.name}")
        return

    title = _infer_title(pdf_path)
    domain = pdf_path.parent.name
    file_size = pdf_path.stat().st_size

    print(f"  Extracting: {pdf_path.name} ({file_size // 1024}KB) ...", end="", flush=True)
    text = _extract_text(pdf_path)
    if not text:
        print(" NO TEXT")
        return

    chunks = _chunk_text(text)
    if not chunks:
        print(" NO CHUNKS")
        return

    print(f" {len(chunks)} chunks ... embedding ...", end="", flush=True)
    embeddings = []
    for i in range(0, len(chunks), EMBED_BATCH):
        batch = ["search_document: " + t for t in chunks[i:i+EMBED_BATCH]]
        embeddings.extend(embed_fn(batch))

    print(f" inserting ...", end="", flush=True)
    for idx, (chunk_text, vec) in enumerate(zip(chunks, embeddings)):
        cur = conn.execute(
            """INSERT INTO pdf_chunks
               (db_id, source_file, domain, title, page_start, page_end,
                chunk_idx, chunk_text, char_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (db_id, rel_path, domain, title, 1, 1, idx, chunk_text, len(chunk_text))
        )
        rowid = cur.lastrowid
        try:
            conn.execute(
                "INSERT INTO vec_pdf_chunks (rowid, embedding) VALUES (?, ?)",
                (rowid, _encode_vec(vec))
            )
        except Exception:
            pass

    # Auto library card
    snippet = chunks[0][:300].replace("\n", " ")
    if not conn.execute("SELECT id FROM library_cards WHERE title = ?", (title,)).fetchone():
        try:
            conn.execute(
                "INSERT INTO library_cards (title, domain, summary, source_path) VALUES (?, ?, ?, ?)",
                (title, domain, snippet, rel_path)
            )
        except Exception:
            pass

    conn.execute(
        """INSERT INTO pdf_index_state
           (db_id, source_file, domain, title, total_pages, chunk_count, file_size)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(source_file) DO UPDATE SET
             db_id=excluded.db_id, chunk_count=excluded.chunk_count,
             total_pages=excluded.total_pages, file_size=excluded.file_size,
             indexed_at=datetime('now')""",
        (db_id, rel_path, domain, title, 1, len(chunks), file_size)
    )
    conn.commit()
    print(f" DONE ✓")

def update_counts(conn):
    for row in conn.execute("SELECT id, slug FROM knowledge_databases").fetchall():
        docs = conn.execute("SELECT COUNT(*) FROM pdf_index_state WHERE db_id = ?", (row[0],)).fetchone()[0]
        chunks = conn.execute("SELECT COUNT(*) FROM pdf_chunks WHERE db_id = ?", (row[0],)).fetchone()[0]
        conn.execute(
            "UPDATE knowledge_databases SET doc_count=?, chunk_count=?, last_built=datetime('now') WHERE id=?",
            (docs, chunks, row[0])
        )
    conn.commit()

def main():
    print("Loading fastembed model...")
    from fastembed import TextEmbedding
    model = TextEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5-Q")
    def embed_fn(texts):
        return [e.tolist() for e in model.embed(texts)]
    print("Model loaded.")

    conn = _connect()
    _ensure_vec(conn)

    clean_stale(conn)

    for db_slug, files in MISSING.items():
        print(f"\n--- Indexing {db_slug} ({len(files)} files) ---")
        for rel_path in files:
            index_file(conn, db_slug, rel_path, embed_fn)

    print("\n--- Updating counts ---")
    update_counts(conn)
    conn.close()

    print("\nDone! Final state:")
    conn2 = _connect()
    for row in conn2.execute("SELECT slug, doc_count, chunk_count FROM knowledge_databases ORDER BY layer").fetchall():
        print(f"  {row[0]}: {row[1]} docs, {row[2]:,} chunks")
    conn2.close()

if __name__ == "__main__":
    main()
