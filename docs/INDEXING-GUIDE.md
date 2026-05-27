# Metis RAG Indexing Guide

A step-by-step guide to indexing PDFs into the Metis knowledge base. By the end of this guide you will have working semantic search over your own documents.

---

## Prerequisites

Before indexing, confirm the following:

1. **The MCP server is running.** The indexing tools are exposed as MCP tools via the Metis server. The server must be active for Claude Code to call them. Start it with `bash system/mcp-server/run.sh` if it is not already running.

2. **fastembed is installed.** The embedding model runs via the `fastembed` package. It is included in the MCP server dependencies. Verify: `pip show fastembed` inside the MCP server venv. If missing: `pip install fastembed`.

3. **sqlite-vec is installed.** Vector search requires the `sqlite-vec` extension. Verify: `pip show sqlite-vec`. If missing: `pip install sqlite-vec`.

4. **PDFs are available.** The system indexes PDFs from `knowledge/library/`. You need at least one PDF in one of the mapped folders before you can build a database.

The embedding model (`nomic-ai/nomic-embed-text-v1.5-Q`, approximately 130 MB) downloads automatically on first use and is cached at `~/.cache/fastembed/`. The first build will include a brief download pause; subsequent builds are fully offline.

---

## Step 1: Organise Your PDFs

PDFs live under `knowledge/library/`. The folder structure maps directly to the three built-in knowledge databases. Place PDFs in the correct subfolder before indexing.

**Folder-to-database mapping:**

| Database slug | Layer | Folders scanned |
|---|---|---|
| `ph-background` | Foundation | `open-access-books/Health Systems & Financing`, `open-access-books/Global Health Governance`, `open-access-books/Social Determinants & Equity`, `open-access-books/Environmental & Occupational Health`, `open-access-books/Infectious Disease & Surveillance`, `open-access-books/Maternal & Child Health`, `open-access-books/NCDs`, `open-access-books/Nutrition & Food Security`, `open-access-books/Mental Health`, `open-access-books/Health Economics`, `open-access-books/One Health & AMR`, `open-access-books/Climate Change & Health`, `open-access-books/Africa & Sub-Saharan Africa`, `open-access-books/Health Informatics & DHIS2`, `open-access-books/Health Security` |
| `hat-specialist` | Specialist | `papers/`, `open-access-books/HAT & NTDs`, `open-access-books/NTDs - HAT`, `open-access-books/NTDs - Overview`, `open-access-books/NTDs - Other`, `open-access-books/NTDs - Leishmaniasis`, `open-access-books/NTDs - Malaria`, `open-access-books/NTDs - TB`, `open-access-books/NTDs - HIV`, `open-access-books/NTDs - Schistosomiasis`, `disease-areas/` |
| `epi-methods` | Methods | `open-access-books/Epidemiology & Methods`, `open-access-books/Biostatistics & Methods`, `open-access-books/Spatial Epidemiology`, `open-access-books/Research Methods & Writing`, `open-access-books/Field Epidemiology`, `methods/`, `concepts/` |

The scan is recursive — any PDF anywhere inside a mapped folder (including nested subfolders) will be picked up. Folder names are used as the `domain` tag for attribution in search results.

**Practical naming tip:** File names become inferred titles. The system strips leading numbers and hyphens and capitalises words, while preserving known acronyms (WHO, CDC, HAT, DHIS2, etc.). A file named `WHO-HAT-Treatment-Guidelines-2024.pdf` becomes the title "WHO HAT Treatment Guidelines 2024". Clean, descriptive filenames make search results easier to read.

---

## Step 2: Build a Knowledge Database

Call `build_pdf_knowledge_db()` with the slug of the database you want to index:

```
build_pdf_knowledge_db(database='ph-background')
```

What happens:

1. The tool opens a WAL-mode connection to `metis.sqlite`.
2. It seeds the three built-in database registry entries if they do not exist.
3. It scans all mapped folders for `.pdf` files recursively.
4. For each PDF not yet indexed, it extracts text using `pdfminer.six`, cleans it, and splits it into chunks of 3,200 characters with 400-character overlap.
5. Chunks are embedded in batches of 32 using `nomic-embed-text-v1.5-Q` with the `"search_document: "` task prefix.
6. Each chunk is written to `pdf_chunks` and its vector to `vec_pdf_chunks`.
7. An index state record is written to `pdf_index_state` so the file is not re-processed on subsequent builds.
8. Counts are updated in `knowledge_databases`.

**Expected output:**

```
══════════════════════════════════════════════════════
 Built: Public Health Background  [ph-background]
══════════════════════════════════════════════════════

  PDFs found:  42
  Indexed:     42
  Skipped:     0  (already indexed)
  Failed:      0
  Time:        187.3s

  [1/42] ✓ WHO-Monitoring-Building-Blocks-Health-Systems-2010.pdf  (1p, 18 chunks)
  [2/42] ✓ WHO-Astana-Declaration-PHC-2018.pdf  (1p, 4 chunks)
  ...
```

**Timing:** Expect roughly 3–6 seconds per PDF on a standard laptop, primarily dominated by embedding inference. A 42-PDF foundation library takes around 3–5 minutes. Subsequent incremental builds are much faster because already-indexed files are skipped.

**Force rebuild:** If you replace or update PDFs, use `force_rebuild=True` to re-index them:

```
build_pdf_knowledge_db(database='ph-background', force_rebuild=True)
```

This deletes all existing chunks and vectors for the database and re-indexes from scratch.

**Indexing all three layers:**

```
build_pdf_knowledge_db(database='ph-background')
build_pdf_knowledge_db(database='hat-specialist')
build_pdf_knowledge_db(database='epi-methods')
```

Run these in sequence. Each is independent and can be run at different times.

---

## Step 3: Verify Indexing

Call `get_pdf_index_stats()` to see what was indexed and what is still pending:

```
get_pdf_index_stats(database='ph-background')
```

**Example output:**

```
══════════════════════════════════════════════════════
 PDF Knowledge Database — Index Status
══════════════════════════════════════════════════════

  ── Foundation ──
  [ph-background]  Public Health Background
    42 docs · 1,847 chunks · last built 2026-05-27

    Health Systems & Financing                          8 docs     312 chunks
    Global Health Governance                            5 docs     214 chunks
    Infectious Disease & Surveillance                   6 docs     278 chunks
    Health Informatics & DHIS2                          3 docs     156 chunks
    ...
```

**Reading the stats:**

- `docs` is the number of PDFs successfully indexed in that domain folder.
- `chunks` is the total number of text segments extracted and embedded from those PDFs.
- The domain breakdown tells you which topic areas have the most coverage.
- A line like `⚠ 3 PDFs not yet indexed` means PDFs are present in the mapped folders but have not been embedded — run `build_pdf_knowledge_db()` to pick them up.

To see all databases at once, call with no arguments:

```
get_pdf_index_stats()
```

---

## Step 4: Test a Query

Run a semantic search to confirm the knowledge base returns useful results:

```
search_pdf_knowledge(
    query="multilevel models for disease prevalence estimation",
    databases=["epi-methods"],
    top_k=5
)
```

**Example output:**

```
**Knowledge search: 'multilevel models for disease prevalence estimation'**
Scope: epi-methods | Top 5 of 2,341 chunks

**1. Leyland Multilevel Modelling Public Health 2020** (score: 0.872)
   Layer: Epidemiology & Methods | Domain: Biostatistics & Methods | p.1 | Leyland-Multilevel-Modelling-Public-Health-2020.pdf
   > Multilevel models (also called hierarchical models or mixed models) are used when data have a nested structure — for example, patients within clinics, or clinics within districts. They partition variance between levels and allow…

**2. Bates lme4 Mixed Models In R Vignette** (score: 0.841)
   Layer: Epidemiology & Methods | Domain: Biostatistics & Methods | p.1 | Bates-lme4-mixed-models-in-r-vignette.pdf
   > The lme4 package provides facilities to fit and analyse linear mixed-effects models. The basic formula interface extends the standard R lm() formula to include random-effects terms specified in parentheses…
```

**Reading scores:**

- Scores run from 0.0 to 1.0. Values above 0.8 indicate a strong semantic match.
- Values between 0.6 and 0.8 are relevant but less precise — they may be from a related section rather than the exact topic.
- Values below 0.5 suggest the query did not match well; try rephrasing or check that the relevant database is indexed.

**Searching multiple databases:**

```
search_pdf_knowledge(
    query="sample size active screening HAT low prevalence",
    databases=["hat-specialist", "epi-methods"],
    top_k=5
)
```

Results from both layers are merged and ranked by score. This is the recommended pattern for any query that sits at the intersection of domain expertise and methodology.

**Searching all databases:**

Omit the `databases` parameter to search everything currently indexed:

```
search_pdf_knowledge(query="WHO health system building blocks", top_k=8)
```

---

## Step 5: Create a Custom Domain Layer

If your research falls outside the three built-in domains, register a custom database:

```
create_knowledge_database(
    slug='dhis2-specialist',
    name='DHIS2 Technical Knowledge',
    description='DHIS2 implementation guides, tracker documentation, API references, NTD program configurations',
    layer=4
)
```

**Slug rules:** lowercase letters, numbers, and hyphens only. Examples: `dhis2-specialist`, `malaria-research`, `climate-health`.

After registering:

1. Create the folder: `knowledge/library/dhis2-specialist/` (or any subfolder structure you prefer).
2. Drop your PDFs into that folder.
3. Build: `build_pdf_knowledge_db(database='dhis2-specialist')`.

**Note on folder mapping for custom databases:** The three built-in databases have hardcoded folder lists in `BUILTIN_DATABASES`. Custom databases created via `create_knowledge_database()` currently need their PDFs placed in a folder that matches the slug (e.g., `knowledge/library/dhis2-specialist/`). The tool scans that folder automatically. A future update (planned as "Layer L9") will allow explicitly specifying multiple folders at registration time.

**Verify your custom database:**

```
list_knowledge_databases()
```

This shows all registered databases including your custom ones, with their current doc and chunk counts.

---

## Troubleshooting

**pdfminer extraction fails / file skipped as "no extractable text"**

Some PDFs are image-based scans — they contain no machine-readable text, only images of pages. `pdfminer.six` cannot extract text from these. The build log will show them as skipped with reason `"no extractable text"`. The solution is to OCR the PDF first using a tool like `ocrmypdf` (free, open source) and replace the original with the OCR-processed version.

**Empty chunks / very low chunk count for a large PDF**

If a PDF indexes but produces far fewer chunks than expected, the text extraction likely encountered encoding issues or unusual formatting. Open the PDF in a reader and check that text can be selected and copied. If it cannot, the PDF needs OCR. If text can be copied but chunk counts are still unexpectedly low, the cleaning step may have stripped too much — this can happen with PDFs that use heavy header/footer formatting on every page.

**Embedding model not loading ("Could not load fastembed")**

The `fastembed` package is not installed, or the MCP server venv is not the active environment. Run `pip install fastembed` in the correct venv (the one the MCP server uses, typically at `system/mcp-server/.venv/`). On first successful load, the model downloads approximately 130 MB to `~/.cache/fastembed/`.

**"sqlite-vec not available"**

The `sqlite-vec` extension is not installed. Run `pip install sqlite-vec` in the MCP server venv. The extension must be importable from the same Python environment the server uses.

**Low-score results for queries you know are covered**

First confirm the relevant database is indexed by running `get_pdf_index_stats()`. If it is indexed, try rephrasing the query using terminology closer to the document text — academic papers use formal phrasing. A query like "sleeping sickness elimination targets" will score better than "how close are we to getting rid of HAT". You can also increase `top_k` to see more candidates and find where the relevant material is ranking.

**"Unknown database" error**

The slug you passed does not match any registered database. Run `list_knowledge_databases()` to see the exact slugs. The three built-in slugs are `ph-background`, `hat-specialist`, and `epi-methods`.
