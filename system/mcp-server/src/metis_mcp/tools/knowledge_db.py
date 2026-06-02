"""knowledge_db.py — Layered PDF Knowledge Database (Phase L).

Users build knowledge layer by layer:
  Layer 1 (foundation): ph-background   — general MPH / global health / health systems
  Layer 2 (methods):    epi-methods     — epidemiology methods, stats, spatial, multilevel
  Layer 3+ (custom):    user-defined    — any specialist domain added via create_knowledge_database()

Each layer is a named "knowledge database" registered in knowledge_databases.
pdf_chunks.db_id links every chunk to its database.
Semantic search can query one database, several, or all layers together.

Tools:
  list_knowledge_databases()
  build_pdf_knowledge_db(database, force_rebuild)
  search_pdf_knowledge(query, databases, top_k)
  get_pdf_index_stats(database)
  create_knowledge_database(slug, name, description, layer, folders)
"""

from __future__ import annotations

import re
import struct
import time
from pathlib import Path
from typing import List, Optional

import sqlite3

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app


def _connect():
    """Open a plain SQLite connection with WAL mode for long-running indexing operations."""
    conn = sqlite3.connect(str(paths.db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ── Constants ─────────────────────────────────────────────────────────────────

CHUNK_CHARS   = 3200
OVERLAP_CHARS = 400
# Embedding attention cost is O(batch * seq^2), and fastembed pads every batch to
# the LONGEST sequence in it — so one long chunk blows up the whole batch's matrix
# (batch=8 measured 13.5 GB; batch=32 hit 31 GB and OOM-crashed WSL). batch=1
# processes one sequence at a time, capping peak attention to ~1-3 GB regardless of
# content. Slower, but memory-bounded and crash-proof — the right tradeoff for a
# one-time background index.
EMBED_BATCH   = 1
EMBEDDING_DIM = 768

# ── Memory-safety caps (added 2026-06-01 after an OOM that killed indexing) ──
# A pathological PDF extraction can produce millions of chars / chunks; holding
# all chunks + all embeddings in memory ballooned the process to 31 GB and the
# kernel OOM-killed it. These bound memory to O(EMBED_BATCH) regardless of doc.
MAX_PAGE_CHARS      = 400_000   # truncate any single page beyond this (likely garbage)
MAX_CHUNKS_PER_DOC  = 8_000     # ~25 MB of text — more than any real book chapter set
COMMIT_EVERY_BATCHES = 8        # flush WAL periodically during long docs
# Hard cap on the text handed to the embedding model. nomic-embed's context is
# 8192 tokens (~32k chars); attention cost is O(seq^2), so a single giant chunk
# would balloon onnxruntime's resident memory. 8000 chars (~2000 tokens) is well
# within context and keeps every embed cheap. Chunks are already <=CHUNK_CHARS,
# so this is a no-op for normal docs and a hard guarantee against a bad one.
EMBED_MAX_CHARS     = 4_000   # ~1000 tokens; with EMBED_BATCH=8 keeps attention tiny

# ── Built-in database definitions ─────────────────────────────────────────────
# Each entry: slug, name, description, layer (1=foundation,2=specialist,3=methods),
# color, and the library subdirectory paths that belong to it.

BUILTIN_DATABASES = [
    {
        "slug": "ph-background",
        "name": "Public Health Background",
        "description": (
            "Foundation layer: general MPH knowledge. Health systems, global health, "
            "governance, social determinants, environmental health, NCDs, nutrition, "
            "mental health, maternal & child health, health economics, Africa, DHIS2. "
            "The baseline every public health researcher needs."
        ),
        "layer": 1,
        "color": "#0d6efd",
        "folders": [
            "open-access-books/Health Systems & Financing",
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
            "open-access-books/Africa & Sub-Saharan Africa",
            "open-access-books/Health Informatics & DHIS2",
            "open-access-books/Health Security",
        ],
    },
    {
        "slug": "epi-methods",
        "name": "Epidemiology & Methods",
        "description": (
            "Methods layer: epidemiology foundations, biostatistics, spatial epidemiology, "
            "multilevel models, research methods, field epidemiology, scientific writing. "
            "Cross-cutting — relevant to any research domain built on top."
        ),
        "layer": 2,
        "color": "#198754",
        "folders": [
            "open-access-books/Epidemiology & Methods",
            "open-access-books/Biostatistics & Methods",
            "open-access-books/Spatial Epidemiology",
            "open-access-books/Research Methods & Writing",
            "open-access-books/Field Epidemiology",
            "methods",
            "concepts",
        ],
    },
    {
        # Public-Health-edition layer (Metis_PH). NTD program knowledge + general
        # HAT awareness — roadmaps, global reports, malaria, disease factsheets.
        # The DEEP, personal HAT corpus lives in the separate local 'hat-specialist'
        # custom database (never shipped). See project_knowledge_layer_architecture.
        "slug": "ntd",
        "name": "Neglected Tropical Diseases",
        "description": (
            "Specialist PH layer: neglected tropical disease program knowledge — WHO NTD "
            "roadmaps and targets, the global NTD report, malaria, and general HAT/sleeping-"
            "sickness awareness. The baseline NTD reference frame for the public-health edition."
        ),
        "layer": 3,
        "color": "#dc3545",
        "folders": [
            "open-access-books/NTDs",
        ],
    },
]

# ── Schema ─────────────────────────────────────────────────────────────────────

_VEC_DDL = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS vec_pdf_chunks USING vec0(
    rowid INTEGER PRIMARY KEY,
    embedding float[{EMBEDDING_DIM}]
);
"""

def _ensure_schema(conn) -> None:
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        pass
    try:
        conn.execute(_VEC_DDL)
    except Exception:
        pass
    # Add db_id column to existing tables if missing (migration)
    for table, col in [("pdf_chunks", "db_id"), ("pdf_index_state", "db_id")]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER DEFAULT 0")
        except Exception:
            pass
    # Folder mapping for custom databases (newline-separated library subfolders)
    try:
        conn.execute("ALTER TABLE knowledge_databases ADD COLUMN folders TEXT DEFAULT ''")
    except Exception:
        pass
    conn.commit()


def _seed_builtin_databases(conn) -> None:
    """Insert built-in database definitions if they don't exist yet."""
    for db in BUILTIN_DATABASES:
        existing = conn.execute(
            "SELECT id FROM knowledge_databases WHERE slug = ?", (db["slug"],)
        ).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO knowledge_databases
                   (slug, name, description, layer, color)
                   VALUES (?, ?, ?, ?, ?)""",
                (db["slug"], db["name"], db["description"], db["layer"], db["color"])
            )
    conn.commit()


def _get_db_id(conn, slug: str) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM knowledge_databases WHERE slug = ?", (slug,)
    ).fetchone()
    return row[0] if row else None


def _update_db_counts(conn, db_id: int) -> None:
    docs  = conn.execute(
        "SELECT COUNT(*) FROM pdf_index_state WHERE db_id = ?", (db_id,)
    ).fetchone()[0]
    chunks = conn.execute(
        "SELECT COUNT(*) FROM pdf_chunks WHERE db_id = ?", (db_id,)
    ).fetchone()[0]
    conn.execute(
        "UPDATE knowledge_databases SET doc_count=?, chunk_count=?, last_built=datetime('now') WHERE id=?",
        (docs, chunks, db_id)
    )
    conn.commit()


# ── Text helpers ──────────────────────────────────────────────────────────────

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


_ACRONYMS = {"WHO","CDC","NTD","HAT","HIV","AMR","NCD","UHC","SDH","DHIS2",
             "AFRO","PAHO","ECDC","GBD","DALY","TB","ANC","AI","ML","API"}

def _infer_title(path: Path) -> str:
    stem = re.sub(r"^\d+_", "", path.stem)
    stem = stem.replace("-", " ").replace("_", " ")
    words = stem.split()
    return " ".join(w.upper() if w.upper() in _ACRONYMS else w.capitalize() for w in words)


def _encode_vec(v: List[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _extract_pages(pdf_path: Path) -> tuple[List[tuple[int, str]], int]:
    """Extract text per page. Tries PyMuPDF (fast, robust, per-page) first, then
    falls back to pdfminer. Many WHO PDFs return empty from pdfminer's single-shot
    extract_text() — PyMuPDF handles those, so this is what rescues the documents
    that were silently skipped before (e.g. the gHAT elimination criteria)."""
    # ── Primary: PyMuPDF, page by page (keeps real page numbers for provenance) ──
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        pages: List[tuple[int, str]] = []
        for i, page in enumerate(doc, 1):
            txt = page.get_text("text") or ""
            if txt.strip():
                pages.append((i, _clean_text(txt)))
        total = doc.page_count
        doc.close()
        if pages:
            return pages, total
    except Exception:
        pass
    # ── Fallback: pdfminer single-shot ──
    try:
        from pdfminer.high_level import extract_text
        full_text = extract_text(str(pdf_path))
        if full_text and full_text.strip():
            return [(1, _clean_text(full_text))], 1
    except Exception:
        pass
    return [], 0


def _library_root() -> Path:
    return paths.root / "knowledge" / "library"


def _collect_pdfs_for_db(db_slug: str) -> List[Path]:
    """Return all PDFs that belong to the given database slug.

    Builtin databases use their hardcoded folder list; custom databases read
    their folder mapping from the knowledge_databases.folders column (set by
    create_knowledge_database).
    """
    lib = _library_root()
    db_def = next((d for d in BUILTIN_DATABASES if d["slug"] == db_slug), None)
    folders: List[str] = []
    if db_def:
        folders = db_def["folders"]
    else:
        # Custom database — read folders persisted in the DB row.
        try:
            conn = _connect()
            row = conn.execute(
                "SELECT folders FROM knowledge_databases WHERE slug = ?", (db_slug,)
            ).fetchone()
            conn.close()
            if row and row[0]:
                folders = [f.strip() for f in str(row[0]).splitlines() if f.strip()]
        except Exception:
            folders = []
    pdfs: List[Path] = []
    for folder in folders:
        d = lib / folder
        if d.exists():
            pdfs.extend(sorted(d.rglob("*.pdf")))
    return pdfs


# ── Core indexing ─────────────────────────────────────────────────────────────

def _index_one_pdf(conn, pdf_path: Path, lib_root: Path, db_id: int,
                   embed_fn) -> dict:
    source_file = str(pdf_path.relative_to(lib_root))
    domain      = pdf_path.parent.name
    title       = _infer_title(pdf_path)
    file_size   = pdf_path.stat().st_size

    pages, total_pages = _extract_pages(pdf_path)
    if not pages:
        return {"status": "skip", "reason": "no extractable text", "source_file": source_file}

    # ── Build the chunk list with HARD CAPS so a pathological PDF can't OOM us ──
    all_chunks: List[dict] = []
    truncated = False
    for page_num, page_text in pages:
        if len(page_text) > MAX_PAGE_CHARS:
            page_text = page_text[:MAX_PAGE_CHARS]  # a single huge "page" = bad extraction
        for ct in _chunk_text(page_text):
            all_chunks.append({"page": page_num, "text": ct})
            if len(all_chunks) >= MAX_CHUNKS_PER_DOC:
                truncated = True
                break
        if truncated:
            break

    if not all_chunks:
        return {"status": "skip", "reason": "no chunks", "source_file": source_file}

    snippet = all_chunks[0]["text"][:300].replace("\n", " ")
    n_chunks = len(all_chunks)

    # ── STREAM: embed one batch, insert it, then DISCARD it. Peak memory is
    #    O(EMBED_BATCH), not O(whole document) — this is the OOM fix. ──────────
    batches = 0
    for i in range(0, n_chunks, EMBED_BATCH):
        batch = all_chunks[i:i + EMBED_BATCH]
        # Truncate each chunk to a model-safe length before embedding (guards
        # against a pathological giant chunk OOM-ing onnxruntime's attention).
        vecs = embed_fn([c["text"][:EMBED_MAX_CHARS] for c in batch])
        for j, (chunk, vec) in enumerate(zip(batch, vecs)):
            cur = conn.execute(
                """INSERT INTO pdf_chunks
                   (db_id, source_file, domain, title, page_start, page_end,
                    chunk_idx, chunk_text, char_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (db_id, source_file, domain, title,
                 chunk["page"], chunk["page"],
                 i + j, chunk["text"], len(chunk["text"]))
            )
            try:
                conn.execute(
                    "INSERT INTO vec_pdf_chunks (rowid, embedding) VALUES (?, ?)",
                    (cur.lastrowid, _encode_vec(vec))
                )
            except Exception:
                pass
        batches += 1
        if batches % COMMIT_EVERY_BATCHES == 0:
            conn.commit()  # flush WAL so memory/disk stay bounded on long docs
        del batch, vecs  # free promptly

    # Auto library card
    if not conn.execute("SELECT id FROM library_cards WHERE title = ?", (title,)).fetchone():
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
           (db_id, source_file, domain, title, total_pages, chunk_count, file_size)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(source_file) DO UPDATE SET
             db_id=excluded.db_id, chunk_count=excluded.chunk_count,
             total_pages=excluded.total_pages, file_size=excluded.file_size,
             indexed_at=datetime('now')""",
        (db_id, source_file, domain, title, total_pages, n_chunks, file_size)
    )
    conn.commit()

    return {
        "status": "ok",
        "source_file": source_file,
        "domain": domain,
        "pages": total_pages,
        "chunks": n_chunks,
        "truncated": truncated,
    }


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@app.tool()
async def list_knowledge_databases() -> list[TextContent]:
    """List all knowledge databases (layers) registered in Metis.

    Shows built-in databases (PH background, HAT specialist, Epi methods) and any
    custom databases the user has created. Reports layer, document count, chunk count,
    and last build date.
    """
    conn = _connect()
    _ensure_schema(conn)
    _seed_builtin_databases(conn)

    rows = conn.execute(
        """SELECT slug, name, layer, color, doc_count, chunk_count, last_built, description
           FROM knowledge_databases ORDER BY layer, id"""
    ).fetchall()
    conn.close()

    if not rows:
        return [TextContent(type="text", text="No knowledge databases found.")]

    layer_labels = {1: "Foundation", 2: "Specialist", 3: "Methods", 4: "Custom"}
    lines = [
        "══════════════════════════════════════════════════════",
        " Metis Knowledge Databases",
        "══════════════════════════════════════════════════════",
        "",
    ]
    last_layer = None
    for slug, name, layer, color, doc_count, chunk_count, last_built, description in rows:
        if layer != last_layer:
            label = layer_labels.get(layer, f"Layer {layer}")
            lines.append(f"  ── {label} ──────────────────────────────────────")
            last_layer = layer
        status = f"{doc_count} docs, {chunk_count:,} chunks" if doc_count else "not yet indexed"
        built_str = f" (built {last_built[:10]})" if last_built else ""
        lines.append(f"  [{slug}]  {name}")
        lines.append(f"    {description[:100]}…" if len(description) > 100 else f"    {description}")
        lines.append(f"    Status: {status}{built_str}")
        lines.append("")

    lines.append("  To index a layer: build_pdf_knowledge_db(database='<slug>')")
    lines.append("  To search layers: search_pdf_knowledge(query, databases=['ph-background','hat-specialist'])")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def build_pdf_knowledge_db(
    database: str = "ph-background",
    force_rebuild: bool = False,
) -> list[TextContent]:
    """Index a knowledge database layer from PDFs into the semantic knowledge base.

    Uses local nomic-embed-text-v1.5-Q (fastembed, ONNX) — no API key required.
    Each database is a named layer: 'ph-background', 'hat-specialist', 'epi-methods',
    or any custom database slug created via create_knowledge_database().

    Args:
        database:      Slug of the knowledge database to build (default: 'ph-background').
        force_rebuild: Re-index even files already indexed in this database.
    """
    t0 = time.time()

    conn = _connect()
    _ensure_schema(conn)
    _seed_builtin_databases(conn)

    db_id = _get_db_id(conn, database)
    if db_id is None:
        conn.close()
        return [TextContent(type="text", text=(
            f"Unknown database '{database}'. "
            f"Run list_knowledge_databases() to see available options."
        ))]

    db_row = conn.execute(
        "SELECT name, description FROM knowledge_databases WHERE id = ?", (db_id,)
    ).fetchone()
    db_name = db_row[0]

    pdfs = _collect_pdfs_for_db(database)
    if not pdfs:
        conn.close()
        return [TextContent(type="text", text=
            f"No PDFs found for database '{database}'. "
            f"Check that the library folders exist under knowledge/library/."
        )]

    # Load embedding model
    # Unit-normalized embeddings (same path as the query side) so L2 distance maps
    # to cosine similarity and the displayed relevance score is meaningful.
    try:
        from metis_mcp.embeddings import embed as _embed
        def embed_fn(texts: List[str]) -> List[List[float]]:
            return _embed(texts, prefix="search_document: ", normalize=True)
        embed_fn(["warmup"])  # surface a model-load failure here, before indexing
    except Exception as e:
        conn.close()
        return [TextContent(type="text", text=f"Could not load fastembed: {e}\nInstall: pip install fastembed")]

    lib_root = _library_root()
    total = len(pdfs)
    indexed = skipped = 0
    failed: List[str] = []
    results: List[str] = []

    for i, pdf_path in enumerate(pdfs, 1):
        source_file = str(pdf_path.relative_to(lib_root))

        if not force_rebuild:
            row = conn.execute(
                "SELECT chunk_count FROM pdf_index_state WHERE source_file = ? AND db_id = ?",
                (source_file, db_id)
            ).fetchone()
            if row and row[0] > 0:
                skipped += 1
                continue

        if force_rebuild:
            chunk_ids = [r[0] for r in conn.execute(
                "SELECT id FROM pdf_chunks WHERE source_file = ? AND db_id = ?",
                (source_file, db_id)
            ).fetchall()]
            for cid in chunk_ids:
                conn.execute("DELETE FROM vec_pdf_chunks WHERE rowid = ?", (cid,))
            conn.execute("DELETE FROM pdf_chunks WHERE source_file = ? AND db_id = ?",
                         (source_file, db_id))
            conn.execute("DELETE FROM pdf_index_state WHERE source_file = ?", (source_file,))
            conn.commit()

        try:
            result = _index_one_pdf(conn, pdf_path, lib_root, db_id, embed_fn)
            if result["status"] == "ok":
                indexed += 1
                results.append(
                    f"  [{i}/{total}] ✓ {pdf_path.name}  "
                    f"({result['pages']}p, {result['chunks']} chunks)"
                )
            else:
                skipped += 1
                results.append(f"  [{i}/{total}] – {pdf_path.name}: {result['reason']}")
        except Exception as exc:
            failed.append(pdf_path.name)
            results.append(f"  [{i}/{total}] ✗ {pdf_path.name}: {exc}")

    _update_db_counts(conn, db_id)
    conn.close()
    elapsed = time.time() - t0

    lines = [
        f"══════════════════════════════════════════════════════",
        f" Built: {db_name}  [{database}]",
        f"══════════════════════════════════════════════════════",
        "",
        f"  PDFs found:  {total}",
        f"  Indexed:     {indexed}",
        f"  Skipped:     {skipped}  (already indexed)",
        f"  Failed:      {len(failed)}",
        f"  Time:        {elapsed:.1f}s",
        "",
    ]
    lines.extend(results[:50])
    if len(results) > 50:
        lines.append(f"  … and {len(results)-50} more")
    if failed:
        lines += ["", f"  Failed ({len(failed)}):", *[f"    - {f}" for f in failed[:10]]]
    lines += [
        "",
        f"  Next: build_pdf_knowledge_db(database='hat-specialist') or",
        f"        search_pdf_knowledge('your query', databases=['{database}'])",
    ]
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def search_pdf_knowledge(
    query: str,
    databases: Optional[List[str]] = None,
    top_k: int = 8,
) -> list[TextContent]:
    """Semantic search across one or more knowledge database layers.

    Searches indexed PDF chunks using 768-dim nomic-embed vector similarity.
    You can search a single layer or combine layers (e.g. PH background + HAT specialist).

    Args:
        query:     Natural language question or keyword phrase.
        databases: List of database slugs to search. Default: all indexed databases.
                   Examples: ['ph-background'], ['hat-specialist', 'epi-methods'],
                   or None to search everything.
        top_k:     Number of results to return (default 8).
    """
    from metis_mcp.embeddings import embed_query

    if not query.strip():
        return [TextContent(type="text", text="query cannot be empty")]

    conn = _connect()
    _ensure_schema(conn)

    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        conn.close()
        return [TextContent(type="text", text="sqlite-vec not available")]

    # Resolve db_ids to filter by
    db_filter_ids: Optional[List[int]] = None
    db_names: dict = {}
    if databases:
        db_filter_ids = []
        for slug in databases:
            row = conn.execute(
                "SELECT id, name FROM knowledge_databases WHERE slug = ?", (slug,)
            ).fetchone()
            if row:
                db_filter_ids.append(row[0])
                db_names[row[0]] = row[1]
    else:
        for row in conn.execute("SELECT id, name FROM knowledge_databases").fetchall():
            db_names[row[0]] = row[1]

    total_chunks = conn.execute("SELECT COUNT(*) FROM pdf_chunks").fetchone()[0]
    if total_chunks == 0:
        conn.close()
        return [TextContent(type="text", text=(
            "No PDFs indexed yet. Run build_pdf_knowledge_db() first.\n"
            "Start with: build_pdf_knowledge_db(database='ph-background')"
        ))]

    q_vec = _encode_vec(embed_query(query, normalize=True))

    # ANN search — get more candidates, filter after
    candidates = conn.execute(
        f"""SELECT v.rowid, v.distance
            FROM vec_pdf_chunks v
            WHERE v.embedding MATCH ?
              AND k = ?""",
        (q_vec, min(top_k * 4, 80))
    ).fetchall()

    if not candidates:
        conn.close()
        return [TextContent(type="text", text="No results found.")]

    rowids = [r[0] for r in candidates]
    distances = {r[0]: r[1] for r in candidates}

    ph = ",".join("?" * len(rowids))
    chunks = conn.execute(
        f"""SELECT id, db_id, source_file, domain, title, page_start, chunk_text
            FROM pdf_chunks WHERE id IN ({ph})""",
        rowids
    ).fetchall()
    conn.close()

    # Filter by database if specified
    if db_filter_ids is not None:
        chunks = [c for c in chunks if c[1] in db_filter_ids]

    # Sort by distance
    chunks.sort(key=lambda c: distances.get(c[0], 9999))
    chunks = chunks[:top_k]

    if not chunks:
        db_label = ", ".join(databases) if databases else "any"
        return [TextContent(type="text", text=f"No results in databases: {db_label}")]

    scope = ", ".join(databases) if databases else "all databases"
    lines = [
        f"**Knowledge search: '{query}'**",
        f"Scope: {scope} | Top {len(chunks)} of {total_chunks:,} chunks",
        "",
    ]
    for rank, c in enumerate(chunks, 1):
        chunk_id, db_id, source_file, domain, title, page_start, chunk_text = c
        dist  = distances.get(chunk_id, 0)
        # Vectors are unit-normalized, so sqlite-vec's L2 distance d relates to
        # cosine similarity by cos = 1 - d^2/2. (The old `1 - d` was wrong for L2
        # and collapsed to 0 for every result.)
        score = round(max(0.0, min(1.0, 1.0 - (dist * dist) / 2.0)), 3)
        layer_name = db_names.get(db_id, f"db:{db_id}")
        excerpt = chunk_text[:400].replace("\n", " ")
        if len(chunk_text) > 400:
            excerpt += "…"
        lines += [
            f"**{rank}. {title}** (score: {score})",
            f"   Layer: {layer_name} | Domain: {domain} | p.{page_start} | {source_file.split('/')[-1]}",
            f"   > {excerpt}",
            "",
        ]
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def get_pdf_index_stats(
    database: str = "",
) -> list[TextContent]:
    """Report indexing statistics for the PDF knowledge base.

    Shows per-database status, domain breakdown, and list of un-indexed PDFs.

    Args:
        database: Slug to report on. Empty = report all databases.
    """
    conn = _connect()
    _ensure_schema(conn)
    _seed_builtin_databases(conn)

    db_rows = conn.execute(
        """SELECT slug, name, layer, doc_count, chunk_count, last_built
           FROM knowledge_databases ORDER BY layer, id"""
    ).fetchall()

    lines = [
        "══════════════════════════════════════════════════════",
        " PDF Knowledge Database — Index Status",
        "══════════════════════════════════════════════════════",
        "",
    ]

    layer_labels = {1: "Foundation", 2: "Specialist", 3: "Methods", 4: "Custom"}
    last_layer = None
    for slug, name, layer, doc_count, chunk_count, last_built in db_rows:
        if database and slug != database:
            continue
        if layer != last_layer:
            lines.append(f"  ── {layer_labels.get(layer, f'Layer {layer}')} ──")
            last_layer = layer

        built = f"last built {last_built[:10]}" if last_built else "NOT YET INDEXED"
        lines.append(f"  [{slug}]  {name}")
        lines.append(f"    {doc_count} docs · {chunk_count:,} chunks · {built}")

        if doc_count:
            domain_rows = conn.execute(
                """SELECT c.domain, COUNT(DISTINCT c.source_file) as docs,
                          COUNT(*) as chunks
                   FROM pdf_chunks c
                   JOIN knowledge_databases kd ON kd.id = c.db_id
                   WHERE kd.slug = ?
                   GROUP BY c.domain ORDER BY chunks DESC LIMIT 10""",
                (slug,)
            ).fetchall()
            for domain, docs, chunks in domain_rows:
                lines.append(f"      {domain:<40} {docs:>3} docs  {chunks:>6} chunks")

        # Count pending PDFs
        all_pdfs = _collect_pdfs_for_db(slug)
        lib_root = _library_root()
        indexed = {r[0] for r in conn.execute(
            """SELECT s.source_file FROM pdf_index_state s
               JOIN knowledge_databases kd ON kd.id = s.db_id
               WHERE kd.slug = ?""", (slug,)
        ).fetchall()}
        pending = [p for p in all_pdfs if str(p.relative_to(lib_root)) not in indexed]
        if pending:
            lines.append(f"    ⚠ {len(pending)} PDFs not yet indexed")
        lines.append("")

    conn.close()
    lines.append("  Run build_pdf_knowledge_db(database='<slug>') to index a layer.")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def create_knowledge_database(
    slug: str,
    name: str,
    description: str = "",
    layer: int = 4,
    folders: Optional[List[str]] = None,
) -> list[TextContent]:
    """Register a new custom knowledge database layer.

    After creating, add PDFs to knowledge/library/<your-folder>/ and call
    build_pdf_knowledge_db(database='<slug>') to index them.

    Args:
        slug:        URL-safe identifier (e.g. 'dhis2-specialist', 'malaria-research').
        name:        Human-readable name (e.g. 'DHIS2 Specialist Knowledge').
        description: What this database covers.
        layer:       Layer number (4+ for custom; built-ins use 1–3).
        folders:     List of library subfolder paths to include
                     (e.g. ['open-access-books/Health Informatics & DHIS2']).
    """
    if not re.match(r'^[a-z0-9][a-z0-9-]*$', slug):
        return [TextContent(type="text", text=(
            f"Invalid slug '{slug}'. Use lowercase letters, numbers, and hyphens only. "
            f"Example: 'dhis2-specialist'"
        ))]

    conn = _connect()
    _ensure_schema(conn)
    _seed_builtin_databases(conn)

    existing = conn.execute(
        "SELECT id FROM knowledge_databases WHERE slug = ?", (slug,)
    ).fetchone()
    if existing:
        conn.close()
        return [TextContent(type="text", text=
            f"Database '{slug}' already exists. Use build_pdf_knowledge_db(database='{slug}') to index it."
        )]

    folders_str = "\n".join(folders or [])
    conn.execute(
        """INSERT INTO knowledge_databases (slug, name, description, layer, color, folders)
           VALUES (?, ?, ?, ?, '#6c757d', ?)""",
        (slug, name, description or f"Custom knowledge database: {name}", layer, folders_str)
    )
    conn.commit()
    conn.close()

    folder_note = ""
    if folders:
        folder_note = "\nFolders mapped:\n" + "\n".join(f"  - knowledge/library/{f}" for f in folders)

    return [TextContent(type="text", text=(
        f"✓ Created knowledge database '{slug}' (Layer {layer})\n"
        f"  Name: {name}\n"
        f"{folder_note}\n"
        f"  Next: add PDFs to knowledge/library/ and run:\n"
        f"  build_pdf_knowledge_db(database='{slug}')"
    ))]
