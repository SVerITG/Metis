# knowledge/library/

This folder is the physical source of all PDF knowledge in Metis. Every PDF you place here can be indexed into a searchable knowledge layer and retrieved by any Metis agent during a research session.

---

## Purpose

The library holds the documents that back the Metis RAG system. When you run `build_pdf_knowledge_db()`, the indexer scans specific subfolders here, extracts text from PDFs, chunks it, embeds it with a local language model, and stores the vectors in the Metis SQLite database. Once indexed, agents can search these documents semantically — asking questions in natural language and getting back relevant excerpts with source attribution.

The library is intentionally structured by topic, not by document type. A WHO guideline, a textbook chapter, and a research paper all live together in the folder that best matches their subject matter, because that is how the indexer assigns domain labels and how search results are presented.

---

## Folder Structure

```
knowledge/library/
│
├── open-access-books/          # Freely available PDFs, organised by topic
│   ├── Biostatistics & Methods/
│   ├── Climate Change & Health/
│   ├── Environmental & Occupational Health/
│   ├── Epidemiology & Methods/
│   ├── Field Epidemiology/
│   ├── Global Health Governance/
│   ├── HAT & NTDs/
│   ├── Health Economics/
│   ├── Health Informatics & DHIS2/
│   ├── Health Security/
│   ├── Health Systems & Financing/
│   ├── Infectious Disease & Surveillance/
│   ├── Maternal & Child Health/
│   ├── Mental Health/
│   ├── NCDs/
│   ├── Nutrition & Food Security/
│   ├── One Health & AMR/
│   ├── Research Methods & Writing/
│   ├── Social Determinants & Equity/
│   └── Spatial Epidemiology/
│
├── papers/                     # Primary research papers (specialist layer)
├── disease-areas/              # Disease-specific reference documents
├── methods/                    # Standalone methodology reference files (Markdown)
├── concepts/                   # Concept notes and reference sheets (Markdown)
└── hat/                        # Structured HAT knowledge notes (Markdown + YAML)
```

The `methods/` and `concepts/` folders contain Markdown files rather than PDFs. These are indexed alongside PDFs and treated identically during retrieval. The `hat/` folder contains structured notes organised by source document.

---

## How Folders Map to Databases

The three built-in knowledge databases each scan a defined set of subfolders:

**`ph-background` — Public Health Background (Foundation layer)**
Scans all subfolders under `open-access-books/` except for disease-specific NTD subfolders. This is the general public health curriculum: health systems, governance, social determinants, environmental health, infectious disease surveillance, maternal and child health, NCDs, nutrition, mental health, health economics, health informatics, and health security.

**`hat-specialist` — HAT & NTD Specialist (Specialist layer)**
Scans `papers/`, `disease-areas/`, and the `open-access-books/HAT & NTDs/` family of subfolders (including NTDs - HAT, NTDs - Overview, NTDs - Other, NTDs - Leishmaniasis, NTDs - Malaria, NTDs - TB, NTDs - HIV, NTDs - Schistosomiasis). This is the deep research layer for NTD researchers.

**`epi-methods` — Epidemiology & Methods (Methods layer)**
Scans `open-access-books/Epidemiology & Methods/`, `open-access-books/Biostatistics & Methods/`, `open-access-books/Spatial Epidemiology/`, `open-access-books/Research Methods & Writing/`, `open-access-books/Field Epidemiology/`, `methods/`, and `concepts/`. This is the cross-cutting methods layer relevant to any quantitative researcher.

The full folder lists are defined in `BUILTIN_DATABASES` inside `system/mcp-server/src/metis_mcp/tools/knowledge_db.py`.

---

## Adding PDFs

Drop your PDFs into the relevant subfolder, then run the build command.

```
# Example: add a new WHO guidelines document to the foundation layer
# 1. Copy the PDF
cp ~/Downloads/WHO-New-Guideline-2025.pdf knowledge/library/open-access-books/Health Systems\ \&\ Financing/

# 2. Index the updated database
# (In a Claude Code session, call the MCP tool:)
build_pdf_knowledge_db(database='ph-background')
```

The indexer is incremental. Already-indexed files are skipped, so only the new PDF will be processed. The build completes in seconds when only one or two files have been added.

For a new domain not covered by the three built-in databases, see the custom layer workflow in [docs/INDEXING-GUIDE.md](../../docs/INDEXING-GUIDE.md).

---

## Gitignore Note

PDFs and personal library content are intentionally excluded from version control. The `.gitignore` excludes:

- `knowledge/library/papers/`
- `knowledge/library/open-access-books/`
- `knowledge/library/disease-areas/`
- `knowledge/library/ph-background/`

This is by design. PDFs are large binary files, many are under copyright, and your personal research library is specific to you. Only the folder structure, Markdown reference files, and structured notes are tracked in git.

When you clone Metis for the first time, the library folders exist but are empty. You build your own library by downloading open-access documents and placing them in the appropriate subfolders, then running the indexer. This is documented in detail in [docs/INDEXING-GUIDE.md](../../docs/INDEXING-GUIDE.md).

---

## Example: Adding a Custom Domain

If you work in climate science and want a searchable knowledge layer for it:

1. Create the folder: `knowledge/library/open-access-books/Climate Change & Health/` (this one already exists for the foundation layer) or a new custom folder such as `knowledge/library/climate-specialist/`.

2. Register a custom database in a Claude Code session:
   ```
   create_knowledge_database(
       slug='climate-specialist',
       name='Climate & Health Specialist',
       description='Research literature on climate change, health impacts, adaptation, and One Health'
   )
   ```

3. Add your PDFs to `knowledge/library/climate-specialist/`.

4. Build:
   ```
   build_pdf_knowledge_db(database='climate-specialist')
   ```

5. Search:
   ```
   search_pdf_knowledge(
       query="health adaptation strategies for extreme heat events",
       databases=["climate-specialist", "ph-background"],
       top_k=5
   )
   ```

Your new layer is now available to all Metis agents. Update `system/config/rag-routing-rules.md` to tell Metis which agents should pre-fetch from it automatically.
