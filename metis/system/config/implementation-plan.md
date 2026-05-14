# Metis — Implementation Plan
**Last updated:** 2026-05-13  
**Sources:** May 10 deep system evaluation · open-source AI tooling research · user sessions

This plan consolidates all open work into a single prioritised roadmap. Items are grouped by phase. Within each phase, order is impact-per-effort. Check items off as they complete and update this file — it is the single source of truth for what to build next.

The feature backlog (`feature-backlog.md`) remains the raw list; this document is the organised plan.

---

## How to read this

**Effort codes:** XS = under 1h · S = 1–3h · M = half day · L = 1 day · XL = 2–5 days · XXL = 1+ week  
**Status:** `[ ]` open · `[~]` in progress · `[x]` done

---

## Phase A — Hooks and session lifecycle
*The infrastructure that makes Metis ambient. Small effort, high daily value.*

- [x] **S — Hook profiles** `pre-tool-use.mjs` — DONE 2026-05-12  
  Add `METIS_HOOK_PROFILE=minimal|standard|full` environment variable.  
  - `minimal`: domain allowlist only (fast, for low-risk sessions)  
  - `standard`: current behaviour (default)  
  - `full`: current + PII keyword detection on file reads  
  No file editing required to switch modes.

- [x] **S — Stop hook** `.claude/hooks/stop.mjs` — DONE 2026-05-12  
  Fires when Claude Code exits or `/exit` is called.  
  Calls `generate_handoff_brief()` automatically. Writes output to `journal/session-{date}-handoff.md`.  
  Closes the gap where session context is lost without a manual handoff step.  
  *The M8.13.5 backlog item — implementing as a hook is cleaner than a pipeline trigger.*

- [x] **S — PostToolUse hook** `.claude/hooks/post-tool-use.mjs` — DONE 2026-05-12  
  Fires after every MCP tool call. Logs: tool name, elapsed time, agent slug.  
  Enables the session pulse widget (how many tools this session, which agents active).  
  Feeds the future `/security-scan` skill with a complete tool-use audit trail.

- [x] **S — Pre-compact hook** `.claude/hooks/pre-compact.mjs` — DONE 2026-05-12  
  Fires before Claude compresses the conversation context.  
  Saves: current working notes, open tasks, last 3 tool results to `journal/pre-compact-{timestamp}.md`.  
  Prevents the common pattern where a mid-session compaction loses the working thread.

---

## Phase B — Missing commands and surface fixes
*These are gaps the researcher hits immediately. Small effort, high friction reduction.*

- [x] **M — 11 missing slash commands** — DONE 2026-05-12  
  All 11 skill.md files were already present with real content:  
  `course-builder`, `content-harvester`, `design-auditor`, `frontend-designer-builder`,  
  `hr-talent`, `learning-architect`, `news-aggregator`, `rc-builder`,  
  `research-architect`, `visualization-maker`, `data-analyst`

- [x] **XS — news_briefs source_type column** — DONE (column already existed)  
  `source_type TEXT DEFAULT 'news'` confirmed present in `news_briefs` schema.

- [x] **XS — metis-identity.json** `system/config/metis-identity.json` — DONE 2026-05-12  
  Machine-readable file created: version, active agent list, install profile, feature flags, domain.

- [x] **L — Empty states on all 9 tabs** — DONE 2026-05-12  
  Verified across all 9 tabs — 7 already had proper empty states.  
  Upgraded `thinking_notes.html` and `thinking_questions.html` from bare `<em>` text to  
  styled panels with keyboard shortcut guidance matching the rest of the system.

---

## Phase C — Automation and ambient operation
*What makes Metis run without being asked. The system should work while you sleep.*

- [~] **L — Morning scan at 07:00**  
  APScheduler job already exists and now includes PubMed + OpenAlex.  
  Remaining: Windows Task Scheduler entry to keep the process alive at user logon + NSSM for auto-restart.  
  *The "Schedule morning brief" button on the dateline already generates the schtasks command — verify it works end-to-end from Windows.*

- [x] **L — Inbox auto-processing** — DONE 2026-05-12  
  `inbox_watcher.py` added to `system/app-py/`: 5-second polling loop (no watchdog dep needed).  
  On new file: classifies by extension (literature/audio/image/data), logs to `inbox_items` table.  
  Wired into `main.py` lifespan — starts automatically with the dashboard.

- [x] **M — PLANNING.md auto-update at session end** — DONE 2026-05-12  
  `stop.mjs` extended: after handoff brief, calls `/api/session/touch-planning` (new FastAPI endpoint in `main.py`).  
  Endpoint queries `projects WHERE status='active'` for `external_path`, finds PLANNING.md there,  
  appends `_Last Metis session: YYYY-MM-DD_` marker (idempotent — no duplicate on same day).  
  Local fallback: if dashboard isn't running, scans `projects/active/` subdirectories directly.

- [x] **S — PubMed daily literature monitoring** — DONE 2026-05-12  
  `tools/literature_monitor.py`: `scan_pubmed_alerts()` using NCBI E-utilities (free, no key).  
  Inserts to `news_briefs` with `source_type='article'`. Added to `job_morning_scan()`.

- [x] **M — OpenAlex paper monitoring** — DONE 2026-05-12  
  `scan_openalex()` in same file. 474M papers, no API key required.  
  Abstract reconstruction from OpenAlex inverted index. Added to `job_morning_scan()`.

---

## Phase D — Intelligence and quality
*Where the system gets meaningfully smarter.*

- [x] **Morning brief AI-generated** — DONE 2026-05-12  
  `_get_or_generate_brief()` in `today.py`: assembles context, calls Claude Haiku, caches result.

- [x] **Semantic theme extraction for self-improvement** — DONE 2026-05-12  
  `_theme_from()` in `improvement.py` now calls Claude Haiku for semantic themes, falls back to word frequency.

- [x] **L — Morning brief: richer structure** — DONE 2026-05-12  
  Brief now follows the IHP Newsletter pattern: three prose paragraphs.  
  1. One leading insight (most important development + why it matters).  
  2. 2–3 items grouped by theme (research / policy / operational), cross-referenced.  
  3. One research thread to pick up today.  
  Prompt caching added (`anthropic-beta: prompt-caching-2024-07-31`) — stable system preamble  
  cached with `cache_control: {"type": "ephemeral"}`, reducing cost on repeated same-day calls.  
  max_tokens increased 300 → 600 to allow the fuller structure.  
  *Feedback buttons deferred — need a relevance_feedback table + routes.*

- [x] **L — Domain-specific tool loading** — DONE 2026-05-12  
  `system/config/tool-subsets.json`: 9 tool groups + 17-agent subset mapping.  
  `metis_mcp/subset_loader.py`: `apply_tool_subset(app, agent_slug)` — reads config, resolves groups  
  to module names, removes non-matching tools from `app._tool_manager._tools` via `tool.fn.__module__`.  
  `server.py`: checks `METIS_TOOL_SUBSETS=1` + `METIS_AGENT_SUBSET=<slug>` at startup and applies filter.  
  `run.sh`: auto-sets `METIS_TOOL_SUBSETS=1` when `METIS_AGENT_SUBSET` is present.  
  Verified: librarian 82/133 tools (38% reduction), data-guardian 47/133 (65% reduction).  
  ALWAYS_ALLOWED set ensures infrastructure tools (pipeline, agents, observability, handoff) are never stripped.

- [x] **S — token-efficient-tools beta header** — N/A 2026-05-12  
  Not applicable: `pipeline.py` routes through Claude Code's tool system, not direct API calls.  
  `today.py` and `improvement.py` make direct httpx calls but define no tools, so the beta header  
  has no effect there. Closed as not applicable rather than deferred.

- [x] **S — Prompt caching for stable prefixes** — DONE 2026-05-12  
  Added to `_get_or_generate_brief()` in today.py: stable system preamble cached with  
  `cache_control: {"type": "ephemeral"}` + `anthropic-beta: prompt-caching-2024-07-31`.  
  Dynamic content (today's context) kept outside the cached block.

- [x] **XL — nomic-embed-text-v1.5-Q cross-pollination** — DONE 2026-05-13  
  Upgraded from BAAI/bge-small-en-v1.5 (384-dim) to nomic-embed-text-v1.5-Q (768-dim) via fastembed.  
  `embeddings.py`: `embed_query()` / `embed_document()` task-prefix API. Model ~130MB, cached in `~/.cache/fastembed/`.  
  `vector_memory.py`: DDL updated float[384]→float[768]. `_migrate_vec_table()` auto-drops and recreates vec0  
  tables on dimension mismatch — safe upgrade path, no data lost (tables were empty).  
  `ideas.py`: `_cross_pollinate_core()` upgraded to hybrid vector (episodic_memory) + keyword SQL with RRF  
  merge and title-dedup (MMR-lite). `capture_idea()` now embeds every idea into `vec_episodic` on save —  
  cross-pollination gets richer with every captured idea. `semantic_search()` updated to use `embed_query`.

- [x] **XL — PaperQA2 semantic library search** — DONE 2026-05-13 (index pending)  
  `tools/paperqa_search.py`: two MCP tools — `index_library_pdfs()` and `ask_library()`.  
  Walks `knowledge/library/`, pre-validates PDFs with pypdf strict=False, indexes with Claude Haiku.  
  Persists index as pickle to `system/app/data/paperqa_index/docs.pkl`.  
  API key loaded from environment or `metis/system/.env` fallback.  
  **To activate:** add `ANTHROPIC_API_KEY=sk-ant-...` to `metis/system/.env`, then call `index_library_pdfs()`.  
  After indexing (~15 min, 221 PDFs): `ask_library("what does my library say about HAT treatment outcomes?")`.

---

## Phase E — Security and governance
*Closing gaps identified in the security evaluation.*

- [x] **S — Session-level injection tracking** — DONE 2026-05-12  
  `pre-tool-use.mjs` now maintains `/tmp/metis-injection-session.json` across tool calls.  
  3+ hits from the same pattern → automatic block with reason. Counts readable by `/security-scan`.

- [x] **S — /security-scan skill** — DONE 2026-05-12  
  `.claude/skills/security-scan/skill.md` created. Reads today's session JSONL, injection counter,  
  sensitive path matches, output PII patterns, and API key exposure. Prints pass/fail summary.

- [x] **M — Enterprise controls file** — DONE 2026-05-12  
  `system/config/enterprise-controls.md`: data classification tiers, access controls, escalation  
  procedures (low/medium/high severity), audit requirements, GDPR/HIPAA compliance notes.

- [x] **M — Output PII scan** — DONE 2026-05-12  
  `post-tool-use.mjs` now scans tool results for email, phone, patient-ID, and API key patterns.  
  Warns to stderr and logs to session injection counter. Skipped on minimal profile.

---

## Phase F — Developer experience and installation
*Lowering the barrier for new researchers and institutional deployments.*

- [x] **L — Install profiles in setup-mcp.sh** — DONE 2026-05-12  
  Interactive profile selector at start of `setup-mcp.sh`: light / standard / full.  
  Dashboard install skipped on `light`. `install-state.json` written at end of every install.  
  Override without prompting: `METIS_PROFILE=light bash setup-mcp.sh`.

- [x] **S — install-state.json** — DONE 2026-05-12  
  `system/config/install-state.json`: profile, version, installed_at, component flags.  
  Created on install by `setup-mcp.sh`. Initial seed written manually for current install.

- [x] **M — /metis_config rewrite for Python dashboard** — DONE (already complete)  
  Verified 2026-05-12: the current `metis-config/skill.md` is already fully Python-based.  
  Covers: Python/venv environment checks, API key setup, Claude Desktop integration, 9-tab dashboard,  
  `user-config.yaml` writes that are wired to real behaviour, 13-section wizard.  
  No R or RStudio references present. No rewrite needed.

- [x] **M — .gemini/GEMINI.md** — DONE 2026-05-12  
  `.gemini/GEMINI.md` created: full agent routing table, the user's profile, key paths, standing rules,  
  and a section explaining how Gemini's native features (Grounding, code execution) relate to MCP tools.

- [~] **XL — Windows .exe installer**  
  Inno Setup script complete (`metis-setup.iss`). Pending: compile on Windows + clean-VM test.  
  *Code written — needs Stan to run `ISCC.exe metis-setup.iss` on a Windows machine with Inno Setup 6.*

- [ ] **XXL — Docker image**  
  `ghcr.io/sveritg/metis:latest`. Self-contained, no WSL required.  
  Low priority for solo Windows use; high priority for Linux users and institutional deployments.  
  *Phase 11 item — deferred.*

---

## Phase G — Domain backgrounds
*Making Metis genuinely useful outside public health. Community contribution target.*

Each domain background lives in `knowledge/domains/<field>/` and contains:
- `feeds.yaml` — curated RSS feeds and free API endpoints for the field
- `vocabulary.md` — key terms, standard classifications, field-specific MeSH equivalents
- `agents/` — 1–2 field-specific agent definitions
- `setup.md` — external tools the domain needs and how to configure them

| Domain | Status | Priority |
|---|---|---|
| Social Sciences | Not started | High — large user base |
| Biomedical Sciences | Not started | High — close to current domain |
| Economics & Development | Not started | High — many global health researchers cross over |
| Environmental Science | Not started | Medium |
| Psychology | Not started | Medium |
| Law & Policy | Not started | Medium |
| Education Research | Not started | Low |
| Nursing & Allied Health | Not started | Low |

*Target: community contributions. See CONTRIBUTING.md for the spec.*

---

## Phase H — Research workflow automation
*The features that change the daily research experience most.*

- [x] **L — Meeting Memory cross-references projects and papers** — DONE 2026-05-12  
  `tools/meetings.py` created: `enrich_meeting_with_crossrefs(meeting_id)` MCP tool.  
  Extracts keywords from transcript + summary + decisions.  
  Matches against: open tasks (by title), active projects (by title/description), library papers (literature_metadata + library_cards fallback).  
  Writes cross-ref brief back to the meeting's notes field in the DB.  
  Registered in `server.py`. Call after `transcribe_recording()` or manual meeting save.

- [ ] **L — Telegram bot for mobile capture**  
  Text, voice note, or image sent to a Telegram bot → arrives in Metis inbox → cross-pollination runs overnight.  
  Implementation: `python-telegram-bot` library + `faster-whisper` for voice (local transcription, no audio leaves machine).  
  Telegram is strictly better than WhatsApp for this: open API, no approval process, free.  
  *The WhatsApp webhook stub in `webhook.py` can be repurposed.*

- [x] **M — Mobile PWA capture page** — DONE 2026-05-12  
  `/capture` route in `main.py` renders `templates/capture.html` — standalone dark-mode mobile form.  
  Type selector buttons (IDEA / NOTE / TASK / QUESTION / JOURNAL) auto-prefix the capture text.  
  Submits to existing `/api/capture` POST handler. Shows cross-pollination connections inline.  
  `/manifest.json` route returns PWA metadata — add to phone home screen for one-tap access.  
  *Service worker deferred — offline caching useful only when Tailscale VPN is active anyway.*

- [x] **L — Course Builder end-to-end pipeline** — DONE 2026-05-12  
  `tools/course_builder.py` created: 4 MCP tools wiring the 7-step pipeline:  
  `start_course_build()` — creates `course_builds` + `learning_courses` rows, returns intake questionnaire.  
  `save_course_outline()` — saves approved module list, advances to step 3, creates `knowledge/courses/{slug}/`.  
  `get_course_status()` — check build progress for one or all active builds.  
  `publish_course()` — finalise build, mark `learning_courses` status='active', appears on Learning tab.  
  `/course-builder` skill already existed with full 7-step pipeline spec.  
  Registered in `server.py`. Quarto integration deferred as a separate enhancement.

- [x] **XL — Phase 10: Automated daily tasks (full)** — DONE 2026-05-12  
  7 scheduled jobs: 06:45 brief synthesis, 07:00 news scan, 07:30 library index, 08:00 inbox process,  
  20:00 evening reflexion, Sunday 09:00 weekly summary, 23:00 nightly backup.  
  Settings persisted to `user-config.yaml` jobs section. `apply_settings_and_reschedule()` applies  
  changes live without restarting. Automation panel on Today tab shows all jobs with:  
  per-job time picker, ON/OFF toggle, RUN now button, last-run status dot and message.  
  Changes saved instantly via `/api/scheduler/settings` POST — no restart needed.

---

## Phase I — Quality and test coverage
*Can't ship without this.*

- [ ] **XXL — Phase 12: Test suite**  
  Unit tests for all MCP tools (mock SQLite).  
  Integration tests for dashboard routes (FastAPI TestClient).  
  End-to-end tests for the 5 most critical flows: capture → cross-pollinate, morning brief, library sync, self-improvement promote, agent run + reflexion.  
  Zero coverage currently.

- [x] **M — Agent eval harness** — DONE 2026-05-12  
  `system/config/agent-eval/golden-tests.json`: 14 golden test cases across 8 agents (librarian, epidemiologist,  
  methods-coach, writing-partner, news-radar, phd-architect, data-guardian, meeting-memory, course-builder, metis).  
  Tags: smoke, regression, edge-case, security. Each test: input, required_keys, forbidden_keys, min_length.  
  `system/config/agent-eval/eval-runner.py`: CLI runner with `--agent`, `--tag`, `--id`, `--compare`, `--json`.  
  `--compare` mode runs incumbent vs candidate skill.md and reports regression/improvement before promoting.  
  Falls back gracefully if `run_agent_call()` is not available (scores against skill.md heuristics).

---

## Completed (this evaluation cycle)

| Date | Item |
|---|---|
| 2026-05-06 | Cross-pollination fires automatically after idea capture |
| 2026-05-06 | Meeting assistant built (import, extraction, live assistant) |
| 2026-05-10 | Self-improvement promote writes to skill.md on disk (`apply_proposal()`) |
| 2026-05-10 | Security hook paths fixed (current folder structure) |
| 2026-05-10 | Injection pattern lists unified (pre-tool-use.mjs ↔ guardrails.py) |
| 2026-05-10 | `get_news_briefs()` MCP tool added |
| 2026-05-10 | `assemble_daily_context()` standalone function added to intelligence.py |
| 2026-05-12 | RSS feeds expanded: 4 → 23 (ProMED, IHP, Eurosurveillance, BMJ, Lancet, arXiv, Reuters, BBC…) |
| 2026-05-12 | `_theme_from()` upgraded from word frequency to Claude Haiku semantic analysis |
| 2026-05-12 | Morning brief connected to AI: assembles context → Claude Haiku → cached in daily_insights |
| 2026-05-12 | README rewritten: dual User/Developer structure, domain backgrounds, full dependency list |
| 2026-05-12 | CONTRIBUTING.md rewritten: domain backgrounds as priority, full contribution spec |
| 2026-05-12 | Comprehensive implementation plan created (`system/config/implementation-plan.md`) |
| 2026-05-12 | **Phase A complete**: hook profiles, stop hook, PostToolUse hook, pre-compact hook — all four registered in `.claude/settings.json` |
| 2026-05-12 | **Phase B complete**: 11 slash commands verified, `source_type` column confirmed, `metis-identity.json` created, empty states completed across all 9 tabs |
| 2026-05-12 | **Phase C (partial)**: PubMed daily alerts, OpenAlex monitoring, inbox watcher — all three new components live. Morning scan job updated. |
| 2026-05-12 | **Phase D (partial)**: Morning brief richer structure (3-para IHP pattern), prompt caching with ephemeral cache_control, max_tokens 300→600. |
| 2026-05-12 | **Phase E complete**: Session injection counter, /security-scan skill, enterprise controls doc, output PII scan in post-tool-use hook. |
| 2026-05-12 | **Phase F (partial)**: install-state.json, install profiles in setup-mcp.sh, .gemini/GEMINI.md. /metis_config rewrite + Docker deferred. |
| 2026-05-12 | **Phase H (partial)**: Mobile PWA capture page — `/capture` route + `manifest.json` + dark-mode mobile form with type selector and cross-pollination display. |
| 2026-05-12 | **Phase C complete**: PLANNING.md auto-update at session end — `stop.mjs` + `/api/session/touch-planning` FastAPI endpoint. |
| 2026-05-12 | **Phase D (tool subsets)**: `system/config/tool-subsets.json` created — 9 groups + 17-agent mapping. Loading code deferred as XL. token-efficient-tools closed N/A. |
| 2026-05-12 | **Phase F complete**: `/metis_config` verified already Python-native — no rewrite needed. |
| 2026-05-12 | **Phase H complete** (Telegram excluded): Meeting Memory cross-refs (`enrich_meeting_with_crossrefs()`), Course Builder 4-tool pipeline (`start_course_build`, `save_course_outline`, `get_course_status`, `publish_course`). |
| 2026-05-12 | **Phase I (eval harness)**: 14 golden tests × 8 agents + `eval-runner.py` with `--compare` mode for pre-promotion regression checks. |
| 2026-05-12 | **Phase D complete**: Domain-specific tool loading live — `subset_loader.py` + `server.py` wiring. Verified: librarian 38% reduction, data-guardian 65% reduction. |
| 2026-05-13 | **Phase 10 complete**: 7 APScheduler jobs, settings UI, automation panel — per-job time/toggle/run controls, live reschedule without restart. |
| 2026-05-13 | **nomic-embed-text-v1.5-Q upgrade**: 384→768 dims, task-prefix API (embed_query/embed_document), vec0 auto-migration, ideas now embed to episodic memory on capture. |
| 2026-05-13 | **PaperQA2 library search**: `index_library_pdfs()` + `ask_library()` MCP tools, pypdf pre-validation, API key .env fallback. Awaiting `ANTHROPIC_API_KEY` in `.env` to run indexer. |
| 2026-05-13 | **README pushed to main**: full researcher/developer overhaul with Metis PNG (380px), Mermaid architecture diagram, dual audience structure, contributing spec. |
| 2026-05-13 | **Phase K complete** (K1–K5): `course-build-lessons-learned.md` written, course-builder skill.md updated with standing rules, `knowledge/course-template/` created, edition variants defined, Inno Setup course selector added. |
| 2026-05-13 | **Phase 11 partial** (M11.1, M11.3, M11.5+M11.6): `vendor_download.py` + `config_merger.py` + `tray_launcher.py` (with port selection) written. Tray launcher wired into installer + install.ps1. Pending: Inno Setup compile + clean-VM test + code signing. |
| 2026-05-14 | **Phase 11 complete (code)** (M11.2, M11.4): `bootstrap_python.ps1` (4-strategy Python cascade: PATH → winget → python.org → bundled embed zip), `download_vendor_python.ps1` (pre-download offline embed), `metis-setup.iss` updated (full/standard/minimal/custom types, courses/biostatistics component, 3-step [Run] bootstrap sequence). All installer code done. M11.7 (clean VM test) + M11.8 (code signing) require Stan. |
| 2026-05-14 | **Library seed script**: `download-library-ph-seed.sh` — 600-line comprehensive script, 176 resources across 19 MPH/GH domains. Fixed `set -e` bug that aborted on failed wget. Running now. |

---

## Phase J — Config Wizard (comprehensive first-run experience)

**Goal:** 13-section guided setup wizard that runs inside Claude Desktop / Claude Code
on first launch. Spec: `system/config/first-run-wizard.md` (already written).

- [x] **J1** (S) — `write_user_config()` MCP tool — DONE 2026-05-13 (`config_tools.py`)
- [x] **J2** (S) — `write_user_preferences()` MCP tool — DONE 2026-05-13
- [x] **J3** (S) — `ingest_ideas_document()` MCP tool — DONE 2026-05-13
- [x] **J4** (S) — `remove_first_run_marker()` MCP tool — DONE 2026-05-13
- [x] **J5** (M) — `.first-run` wizard trigger in CLAUDE.md — DONE 2026-05-13
- [x] **J6** (M) — `system/config/claude-project-wizard.md` for claude.ai Projects — DONE 2026-05-13
- [x] **J7** (L) — Dashboard `/setup` page (`routers/setup.py` + `templates/setup.html`) — DONE 2026-05-13
- [x] **J8** (S) — `/metis-config` skill section-argument routing — DONE 2026-05-13

---

## Phase K — Course Builder: Lessons Learned

**Goal:** Document all lessons from the MLM course build, bake fixes into the Course Builder
agent so every new course starts with those improvements applied.

- [x] **K1** (M) — Write `system/config/course-build-lessons-learned.md` — DONE 2026-05-13
- [x] **K2** (M) — Update `.claude/skills/course-builder/skill.md` with standing rules from K1 — DONE 2026-05-13
- [x] **K3** (S) — Create `knowledge/course-template/` starter with all K1 fixes pre-applied — DONE 2026-05-13
- [x] **K4** (S) — Edition variants defined in `system/config/edition-variants.md` — DONE 2026-05-13
- [x] **K5** (M) — Installer course component selector in `metis-setup.iss` (full/standard/minimal types, courses/biostatistics component, install-state.json write) — DONE 2026-05-13

---

## Phase L — PDF Knowledge Database (Background Semantic Index)

**Goal:** Transform all downloaded PDFs into a queryable background knowledge database.
No API key required — uses local fastembed (nomic-embed-text-v1.5-Q, 768-dim, ONNX).
The result is a distributable SQLite database (~80–150 MB) that ships with Metis_PH.

**Pipeline:** PDF → pypdf text extraction → clean → 800-token chunks (200-char overlap)
→ batch nomic-embed → `pdf_chunks` + `vec_pdf_chunks` in metis.sqlite

**Estimated output:** ~10,000 chunks from 96 PDFs, 768-dim embeddings, ~80 MB DB increment

- [ ] **L1** (S) — Add `pdf_chunks` + `pdf_index_state` tables to `system/installer/schema.sql`
  - `pdf_chunks`: id, source_file, domain, title, page_start, page_end, chunk_idx, chunk_text, char_count
  - `pdf_index_state`: source_file (UNIQUE), domain, title, total_pages, chunk_count, indexed_at
- [ ] **L2** (M) — `vec_pdf_chunks` vec0 virtual table setup in `knowledge_db.py` (sqlite-vec, 768-dim)
- [ ] **L3** (L) — `build_pdf_knowledge_db()` MCP tool
  - Walks `knowledge/library/open-access-books/` + `papers/` recursively
  - Skips already-indexed files (checks `pdf_index_state`)
  - pypdf text extraction with OCR artifact cleanup
  - Chunks: 3200 chars per chunk, 400-char overlap, split on paragraph boundaries
  - Batch embeddings (32 at a time) via fastembed
  - Auto-generates `library_cards` entry for each new document
  - Reports: files indexed, chunks created, time taken, DB size
- [ ] **L4** (M) — `search_pdf_knowledge(query, top_k, domain_filter)` MCP tool
  - Vec0 ANN search → returns top-k chunks with source, page range, similarity score
  - BM25 hybrid re-ranking (combine keyword + semantic scores)
  - Result includes: title, domain, page_start, chunk excerpt, score
- [ ] **L5** (S) — `get_pdf_index_stats()` MCP tool — per-domain stats, total chunks, DB size
- [ ] **L6** (M) — Dashboard: **Knowledge search bar** (Knowledge tab)
  - HTMX input → `/api/knowledge/search?q=...` → chunk results with source citations
  - Filters by domain chip (matches existing domain tabs on Knowledge tab)
- [ ] **L7** (M) — **Standalone build script** `system/install/build_knowledge_db.py`
  - Runs outside MCP (direct Python script for installer post-build step)
  - `--library-dir`, `--db`, `--domain`, `--force` flags
  - Outputs progress bar + final stats
  - Callable from `seed_ph_database.py --index-pdfs` flag
- [ ] **L8** (S) — **Installer integration**: add post-install step in `metis-setup.iss` [Run]
  - `build_knowledge_db.py --library-dir {app}\knowledge\library --db {app}\system\app\data\metis.sqlite`
  - StatusMsg: "Building knowledge database (this takes 5–15 minutes)…"
  - Only runs if any PDFs present (check `knowledge\library\open-access-books\` exists)
- [ ] **L9** (S) — **Distributable DB export**: `export_knowledge_db.py`
  - Exports `pdf_chunks` + `vec_pdf_chunks` to standalone `knowledge_db.sqlite`
  - Can be shipped as optional ~150 MB download for users who skip the PDF indexing step
  - Imported back via `import_knowledge_db.py --merge`

---

## What to build next (ordered recommendation)

1. **Phase L — PDF Knowledge Database** (L, 1–2d) — L1–L7 are the core; L8–L9 are distribution polish. **Start here — the 96 PDFs are ready.**
2. **Activate PaperQA2 index** (XS, 5min) — add `ANTHROPIC_API_KEY` to `metis/system/.env`, call `index_library_pdfs()`. Unlocks Claude-synthesized Q&A over papers (complements Phase L).
3. **Morning scan Windows autostart** (S, 1h) — verify "Schedule morning brief" button end-to-end.
4. **Telegram bot** (L, 1d) — text/voice/image → inbox → cross-pollination.
5. **Windows .exe final build** (XL, 1d) — compile `metis-setup.iss` with Inno Setup. All installer code ✅ done. Steps: (1) on Windows run `download_vendor_python.ps1` to get embed zip, (2) run `ISCC.exe installer/metis-setup.iss`, (3) test `.exe` on a clean VM.
6. **Docker image final build** (M, 4h) — test Dockerfile + docker-compose end-to-end.
7. **Phase 12 test suite** (XXL) — unit + integration + e2e. Zero coverage currently.
8. **Metis GitHub repos** — create `Metis` (empty shell), `Metis_BM`, `Metis_CL` placeholder repos.
