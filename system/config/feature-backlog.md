# Metis Feature Backlog

Items are added here whenever a feature is requested or identified during a session.
Check this file at the start of every session before starting new work.

---

## Open

### F001 — Metis as RAG orchestrator
**Priority:** High
**Requested:** 2026-05-19

Metis should decide when to call `search_pdf_knowledge()` before routing to a specialist agent — not individual agents. This is the correct architectural pattern for a shared knowledge layer.

**What to build:**
- In the Metis routing step, detect queries that benefit from grounding (methods questions, guideline references, statistical procedures, WHO/CDC recommendations)
- Call `search_pdf_knowledge(query, databases=[...])` based on detected topic domain
- Inject the top-k retrieved chunks as `[KNOWLEDGE CONTEXT]` block into the agent's prompt
- Define a topic → database mapping (health economics/systems/epi → ph-background; MLM/biostat/spatial → epi-methods; HAT/NTDs → hat-specialist)
- Skip retrieval for: conversational, routing, news, scheduling, status queries

**Why not in individual agents:**
- Repetitive and inconsistent across 20+ agents
- Adding a new knowledge database would require editing every agent prompt
- Retrieval tuning (top_k, score threshold) should be centralized

**Files to change:**
- `.claude/skills/metis.md` — add RAG pre-step to routing logic
- Possibly a new `system/config/rag-routing-rules.md` for the topic → database mapping

---

### F002 — Raise max-pages limit for large biostat books
**Priority:** Medium
**Requested:** 2026-05-19

BDA3 (Gelman), LibreTexts Biostatistics, and Biostatistics-for-Epi-PH-using-R are all skipped by the semantic indexer because they exceed the 400-page default limit. These are high-value references.

**What to do:**
- Re-run epi-methods indexer with `--max-pages 600` for these three books
- Or index them separately as a batch with higher limit

**Command:**
```bash
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
  ~/.local/share/metis-mcp/.venv/bin/python3 \
  system/install/build_knowledge_db.py \
  --database epi-methods --max-pages 600 --batch-size 2 --sleep 0.5
```

---

### F003 — MLM course materials in epi-methods layer
**Priority:** Medium
**Requested:** 2026-05-19

If specific MLM course materials exist (slides, practicals, worked examples from a university module or MOOC), they should be added to `knowledge/library/open-access-books/Biostatistics & Methods/` and re-indexed.

Currently only Leyland (343 chunks) and Bates lme4 vignette (59 chunks) cover MLM. Large books (BDA3, LibreTexts) were skipped due to page limit.

---

### F004 — D14 Spatial Epidemiology gap
**Priority:** Low-Medium
**Requested:** 2026-05-19

Spatial Epi semantic layer has only SaTScan Tutorial (35 chunks). Web-only books (Moraga, Geocompr) cannot be auto-downloaded.

**Options:**
- Register at satscan.org and download SaTScan User Guide v10 PDF
- Check if Paula Moraga's book has a print/PDF edition available

---

### F005 — D4 Health Systems gap
**Priority:** Low
**Requested:** 2026-05-19

Health Systems semantic layer is weak. WHO World Health Reports (2000, 2008, 2010) are HTML-only.

**Options:**
- Use Content Harvester on the HTML versions
- Find PDF mirrors via WHO IRIS DSpace API

---
