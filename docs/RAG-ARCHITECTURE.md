# Metis RAG Architecture

## Overview

Metis RAG is a local, offline-first retrieval-augmented generation system built into the Metis second-brain platform. It allows any Metis agent to query a curated library of PDFs — textbooks, guidelines, research papers, and methods references — using natural language, and receive relevant excerpts with full source attribution.

The design philosophy is deliberately local-first. There is no cloud API, no subscription, and no data leaving your machine. PDF text is extracted, chunked, and embedded entirely on your hardware using an ONNX-based model that runs without a GPU. The resulting vectors are stored in the same SQLite database that holds the rest of the Metis metadata, which means the knowledge base is a single portable file.

This makes the system suitable for researchers working with sensitive data, working offline (fieldwork, travel), or simply preferring not to route document contents through external APIs. It is also considerably cheaper at scale than cloud embedding APIs — a library of several hundred PDFs costs nothing to index beyond the time it takes.

The core implementation lives in `system/mcp-server/src/metis_mcp/tools/knowledge_db.py` (790 lines) and `system/mcp-server/src/metis_mcp/embeddings.py`. Five MCP tools expose the full lifecycle: list, build, search, inspect, and create.

---

## Three-Layer Knowledge System

The knowledge base is organised into named layers. Each layer is a logical grouping of PDFs that covers a coherent domain. Layers are designed to compose: you can search one layer in isolation, or query multiple layers together to blend general and specialist knowledge.

The three built-in layers reflect the knowledge architecture of a public health researcher:

**Layer 1 — Foundation (`ph-background`)**
General public health knowledge. This layer covers health systems and financing, global health governance, social determinants of health, environmental and occupational health, infectious disease and surveillance, maternal and child health, NCDs, nutrition, mental health, health economics, Africa-specific context, health informatics and DHIS2, and health security. It is the baseline that every public health question draws on — the knowledge equivalent of an MPH curriculum. Every researcher who installs Metis starts here.

**Layer 2 — Specialist (`hat-specialist`)**
Domain-specific research literature. The default specialist layer covers Human African Trypanosomiasis (HAT), neglected tropical diseases (NTDs), and related disease areas including Leishmaniasis, Malaria, TB, HIV, and Schistosomiasis. This layer contains primary research papers, WHO guidelines specific to HAT and NTDs, disease roadmaps, and clinical guidance. Researchers in other domains replace or extend this layer with their own specialist corpus.

**Layer 3 — Methods (`epi-methods`)**
Cross-cutting methodological knowledge. This layer covers epidemiology foundations, biostatistics, spatial epidemiology, multilevel models, research methods, field epidemiology, and scientific writing. It is designed to be relevant regardless of disease area — any researcher doing quantitative work needs it. Content includes both standard references (STROBE, PRISMA, CDC Principles of Epidemiology) and specialist texts (Gelman BDA3, lme4 vignette, Hernan-Robins causal inference).

**Layer 4+ — Custom**
User-defined layers. You can register any number of additional databases for domains not covered by the built-ins. A DHIS2 technical corpus, a malaria surveillance layer, a health economics library — anything can become a searchable knowledge layer. Custom layers are Layer 4 by convention.

Layers compose cleanly. A query like "what are the sample size requirements for a prevalence survey in a low-endemic setting?" can usefully draw from both `epi-methods` (sampling theory) and `hat-specialist` (HAT-specific prevalence context). The search tool accepts a list of database slugs and merges results by relevance score.

---

## Embedding

The embedding model is `nomic-ai/nomic-embed-text-v1.5-Q` — a quantised ONNX version of the Nomic Embed 1.5 model, delivering 768-dimensional vectors. It runs via the `fastembed` library, which provides a Python interface to ONNX Runtime without requiring PyTorch or a GPU.

Key characteristics:

- **Dimensions:** 768 floats per vector
- **Model file size:** approximately 130 MB, cached at `~/.cache/fastembed/` on first use
- **Inference:** CPU, ONNX Runtime — no CUDA or MPS required
- **Task prefixes:** the model is trained with Matryoshka-style task awareness. Documents are prefixed with `"search_document: "` at index time; queries are prefixed with `"search_query: "` at retrieval time. This asymmetric prefixing improves retrieval precision and is mandatory for this model family.
- **Fallback:** if `nomic-embed-text-v1.5-Q` fails to load, the system falls back to `BAAI/bge-base-en-v1.5` (768 dims, ~210 MB), which does not use task prefixes.

The choice of this model reflects the constraints of the system: it must be free, local, capable of good semantic retrieval on scientific text, and small enough to be practical. The quantised Nomic model meets all four criteria. Benchmark evaluations of the full-precision Nomic Embed 1.5 place it competitive with OpenAI `text-embedding-ada-002` on MTEB retrieval tasks, while the quantised variant sacrifices minimal quality for a significant reduction in model size.

Embeddings are produced in batches of 32 (`EMBED_BATCH = 32`) to balance memory use and throughput. A library of 100 PDFs typically produces several thousand chunks; the full indexing pass completes in a few minutes on a standard laptop.

---

## Storage

All vectors and metadata are stored in the central Metis SQLite database (`system/app/data/metis.sqlite`). SQLite was chosen for portability, zero external dependencies, and the ability to back up the entire knowledge base by copying a single file.

Vector search is powered by `sqlite-vec`, a SQLite extension that provides approximate nearest-neighbour (ANN) search as a virtual table. The extension is loaded dynamically at query time. If it is not available, the search tool returns a clear error rather than silently falling back to a slower path.

Connections use WAL (Write-Ahead Logging) mode (`PRAGMA journal_mode=WAL`) to allow read operations to proceed concurrently with the long-running indexing writes. This is important when the dashboard is reading agent run data at the same time that a `build_pdf_knowledge_db()` call is indexing hundreds of PDFs.

---

## Chunking

Text is extracted from PDFs using `pdfminer.six`, which produces a single string of full document text. The text is then cleaned to remove hyphenated line breaks (`-\n`), collapse whitespace, strip page numbers and running headers (short all-caps or numeric-only lines), and normalise paragraph breaks.

The cleaned text is chunked using these parameters:

- **Chunk size:** 3,200 characters (`CHUNK_CHARS = 3200`)
- **Overlap:** 400 characters (`OVERLAP_CHARS = 400`)
- **Boundary strategy:** the chunker prefers paragraph boundaries (`\n\n`) as split points. If no paragraph boundary exists in the target window, it falls back to sentence boundaries (`. `). If neither is found, it splits at the hard character limit.

The overlap ensures that sentences at the boundary of two chunks appear in both, preserving context for queries that land near a chunk edge. At 3,200 characters per chunk, a typical academic paragraph or two fits comfortably with room for context. The chunk size was chosen to balance retrieval precision (smaller chunks are more specific) against coverage (larger chunks provide more context per hit).

The character count — rather than token count — was used deliberately to remain model-agnostic. The 3,200-character target corresponds roughly to 600–800 tokens with typical academic English, well within the 2,048-token context window of the Nomic model.

---

## Schema Reference

Three tables form the RAG storage layer. They extend the broader Metis schema defined in `system/installer/schema.sql`.

**`knowledge_databases`** — the registry of all knowledge layers.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Primary key, auto-increment |
| `slug` | TEXT UNIQUE | URL-safe identifier used in all tool calls (`ph-background`, `hat-specialist`, `epi-methods`) |
| `name` | TEXT | Human-readable name displayed in the UI and tool output |
| `description` | TEXT | What this database covers; used by routing rules to match queries |
| `layer` | INTEGER | Layer number: 1=Foundation, 2=Specialist, 3=Methods, 4+=Custom |
| `color` | TEXT | Hex badge colour for the dashboard UI |
| `doc_count` | INTEGER | Number of PDFs indexed; updated after each build |
| `chunk_count` | INTEGER | Total chunks across all PDFs in this database |
| `last_built` | TEXT | ISO datetime of last successful build |
| `created_at` | TEXT | Row creation timestamp |

**`pdf_chunks`** — one row per text chunk extracted from a PDF.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Primary key; also used as `rowid` in the vec table |
| `db_id` | INTEGER | Foreign key to `knowledge_databases.id` |
| `source_file` | TEXT | Relative path from `knowledge/library/` root (e.g. `open-access-books/Epidemiology & Methods/WHO-Basic-Epidemiology-2nd-ed-Bonita-2006.pdf`) |
| `domain` | TEXT | Inferred from the immediate parent folder name |
| `title` | TEXT | Inferred from the filename (hyphens replaced, acronyms preserved) |
| `page_start` | INTEGER | Page number where the chunk begins |
| `page_end` | INTEGER | Page number where the chunk ends (same as `page_start` with pdfminer full-text extraction) |
| `chunk_idx` | INTEGER | Zero-based index of this chunk within its source file |
| `chunk_text` | TEXT | The raw text of the chunk |
| `char_count` | INTEGER | Character length of `chunk_text` |
| `created_at` | TEXT | Row creation timestamp |

Indexes: `idx_pdf_chunks_source` (source_file), `idx_pdf_chunks_domain` (domain), `idx_pdf_chunks_db_id` (db_id).

**`vec_pdf_chunks`** — the virtual vector table for ANN search.

| Column | Type | Description |
|---|---|---|
| `rowid` | INTEGER | Matches `pdf_chunks.id` — the join key |
| `embedding` | float[768] | 768-dimensional float32 embedding, stored as packed binary (`struct.pack`) |

**`pdf_index_state`** — tracking which PDFs have been indexed, used for incremental builds.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Primary key |
| `db_id` | INTEGER | Foreign key to `knowledge_databases.id` |
| `source_file` | TEXT UNIQUE | Relative path — used as the deduplication key |
| `domain` | TEXT | Folder-level domain label |
| `title` | TEXT | Inferred title |
| `total_pages` | INTEGER | Total pages in the source PDF |
| `chunk_count` | INTEGER | Number of chunks produced |
| `file_size` | INTEGER | File size in bytes at index time |
| `indexed_at` | TEXT | Timestamp of last indexing |

---

## Query Pipeline

When `search_pdf_knowledge()` is called:

1. **Embed the query.** The query string is passed to `embed_query()`, which prepends `"search_query: "` and runs it through the fastembed model. The result is a 768-dimensional float vector.

2. **Encode for SQLite.** The float list is packed to binary using `struct.pack(f"{n}f", *vec)` — the format expected by `sqlite-vec`.

3. **ANN search.** The vector is matched against `vec_pdf_chunks` using the `MATCH` operator with `k = min(top_k * 4, 80)` candidates. Over-fetching by 4x compensates for the database filter applied in the next step.

4. **Database filter.** If specific `databases` were requested, results are filtered to chunks whose `db_id` matches one of the requested slugs. This allows multi-layer searches while keeping layer isolation when needed.

5. **Re-rank by distance.** Candidates are sorted by the raw L2 distance returned by `sqlite-vec`. The score reported to the caller is `max(0.0, round(1.0 - distance, 3))` — a normalised similarity where 1.0 is a perfect match and lower values indicate less relevant results.

6. **Return with attribution.** The final `top_k` results are returned with: rank, title, score, layer name, domain, page number, source filename, and a 400-character excerpt of the chunk text.

---

## Integration with Agents

Agents access the knowledge base through the `search_pdf_knowledge()` MCP tool. The routing rules in `system/config/rag-routing-rules.md` define which agents trigger a pre-fetch and which databases they query.

The standard pattern before any substantive response:

```python
# Single-database retrieval
search_pdf_knowledge(query="multilevel models for prevalence estimation", databases=["epi-methods"], top_k=5)

# Multi-database retrieval (HAT context + methods)
search_pdf_knowledge(query="sample size HAT active screening DRC", databases=["hat-specialist", "epi-methods"], top_k=4)

# Broad public health question
search_pdf_knowledge(query="health systems building blocks WHO framework", databases=["ph-background"], top_k=5)
```

The routing rules specify that the Epidemiologist and Methods Coach agents always pre-fetch from `epi-methods`; the PhD Architect pre-fetches from both `epi-methods` and `hat-specialist`; the Writing Partner pre-fetches from `hat-specialist` when writing about HAT. News Radar, DHIS2 Expert, and Software Engineer never trigger a retrieval.

If `search_pdf_knowledge()` returns zero results or raises an exception, agents are instructed to skip silently and continue — a missing or empty knowledge base should never block a useful response.

---

## Building Your Own Domain Layer

To add a new specialist domain to the knowledge base:

1. Register the database with `create_knowledge_database(slug='my-domain', name='My Domain', description='...')`.
2. Add PDFs to a folder under `knowledge/library/`.
3. Index with `build_pdf_knowledge_db(database='my-domain')`.

See [INDEXING-GUIDE.md](INDEXING-GUIDE.md) for the complete step-by-step process, including folder conventions, verification steps, and troubleshooting.
