# HAT Dashboard — Software Engineer Context

**Invocation:** `/software-engineer <task title>`
**Repository:** `SVerITG/HAT_Dashboard_1.0`
**Branch:** `server` (active working branch)
**Local path:** `C:\Users\sverschaeve\OneDrive - ITG\Documents\2. HAT disease\1. Epi Data\7. Dashboard`

---

## Current git state (as of 2026-03-27)

**14 modified files — uncommitted:**
- `.Rhistory`, `.claude/settings.local.json`
- `00_config.R` — configuration and paths
- `03_css_styles.R` — UI styling
- `0_Start-up` — startup script
- `CLAUDE.md` — agent context file
- `Data-assistant/chunks.json`, `faiss.index`, `processed_docs.json` — RAG knowledge base
- `app.R` — main Shiny entry point
- `documentation/ShinyServer.docx` — server deployment docs
- `server_agent.R` — AI agent server logic
- `server_overview.R` — overview tab server
- `ui_exploration.R` — exploration tab UI

**Untracked new files:**
- `Data-assistant/add_kb_to_index.py`, `rag_knowledge_base.md`, `rag_service.py`, `start_rag_service.sh`, `system_prompt.md`
- `deploy_to_server.sh`
- `.vscode/` settings

---

## Architecture summary

- **R Shiny** app with multiple tab modules (overview, exploration, agent)
- **RAG Data-assistant**: Python FastAPI service + FAISS index for in-app vector search
- **Key files:**
  - `app.R` — UI + server wiring
  - `00_config.R` — paths, database connections, global settings
  - `server_overview.R` — overview tab reactive logic
  - `server_agent.R` — AI agent tab, connects to RAG service
  - `ui_exploration.R` — exploration tab UI (14+ reactive filters)
  - `03_css_styles.R` — custom CSS

---

## Known issues / priorities

- 14 uncommitted files: review which should be committed vs. gitignored
- Hardcoded paths in scripts — check `00_config.R` for portability
- `server_overview.R` contains performance-sensitive joins (9M record dataset)
- RAG service (`rag_service.py`) needs to be running before agent tab works
- `deploy_to_server.sh` is new — document deployment workflow

---

## Useful commands

```bash
# Check status
git -C "C:/Users/sverschaeve/OneDrive - ITG/Documents/2. HAT disease/1. Epi Data/7. Dashboard" status

# Start RAG service (from dashboard folder)
cd "Data-assistant" && python rag_service.py

# Run app
Rscript -e "shiny::runApp('.')"
```

---

## RAG context

The Data-assistant folder contains a FAISS-indexed knowledge base of processed documents.
Key files: `chunks.json` (text chunks), `faiss.index` (vector index), `processed_docs.json` (source tracking).
`add_kb_to_index.py` can add new documents to the index.
