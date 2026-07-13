# Changelog

All notable changes to Metis are documented here.

## [Unreleased]

### Added
- **Today Surface sprint** — resume card, literature discovery, learning nudge, system health monitor, deadline nudges, brief bridges, memory pulse, focus memory, session thread, and trust badge redesign (Jul 13).
- **Meeting assistant upgrade** — Whisper GPU activation with 3.5s chunks, Meetily transcript import, Voxtral cloud transcription backend (requires MISTRAL_API_KEY), speaker diarization improvements (Jul 13).
- **Memory Cortex** — unified memory gateway with `recall()` (searches all 6 memory layers with RRF fusion) and `remember()` (auto-classifies into episodic/semantic/procedural/note); multi-scope identity (agent_id, project_id, scope columns); richer session bootstrap with semantically relevant memories; Memory Health dashboard tab (Jun 18).
- **Progressive tool disclosure** — `find_tools()` / `load_tool_group()` / `list_tool_groups()` park non-core tools at startup and expose them on demand via `send_tool_list_changed()`; 196→~80 exposed, ~130 parked, nothing unreachable (Jun 17).
- **Agent-aware tool titles** — every MCP tool now shows which specialist agent owns it (e.g. "Metis · Librarian — Search Literature"); 96 tools carry agent labels (Jun 18).
- **Script Analyzer** — 4 new MCP tools (`analyze_script`, `scan_project_scripts`, `generate_profiling_script`, `ingest_profiling_output`) for the "send code, not data" pipeline; `/code-intake` skill (Jun 18).
- **Data protection hardening** — `/safe-analysis` workflow ("send code, not data"), Data Guardian with all 11 PII patterns wired through one shared `scan_content()`, pre-tool file-content guard that peeks at data file headers before Read, write-side data-authorization gate on Write/Edit for data-file extensions (Jun 4–16).
- **Cybersecurity deny-rules** — hard-deny reads/writes of `.env`/`~/.ssh`/`~/.aws`/`*.pem`/credentials at the hook; outbound network scoped to domain allowlist (Jun 16).
- **Learnable agent routing** — routing database (not hardcoded list), reaches 21 specialists (was 10), word-boundary matching, learns from user preferences via `record_routing_preference` (late Jun).
- **Personalization layer** — standing preferences and decisions (coding style, citation format, methodology defaults) applied on every request; `record_decision` / `recall_decisions` / `evaluate_against_layers` tools (late Jun).
- **Semantic relevance scoring** — content_scan ranks scanned items by closeness to user's actual corpus via local interest-profile centroid; numeric `relevance` column (Jun 5).
- **Two-button no-API brief** — "Update with Claude" opens Claude Desktop via `claude://` deep link (subscription, no API key); "Update (API)" uses existing path; saves back via shared DB (Jun 5).
- **Brainstorm upgrades** — creativity dial (Grounded/Balanced/Bold), scoped menu (This work · A topic · Mindmap · Cluster), "✦ BRAINSTORM THIS" button on Today brief, Claude Desktop deep-link hand-off (Jun 5).
- **Daily ↔ Weekly brief toggle** in brief header (Jun 5).
- **Working-loop reflexion** — three-tier generate→verify: post-tool-use.mjs syntax-checks code on the spot; `/verify-work` skill with deterministic signals + independent skeptic sub-agent; periodic `/metis-self-reflexion` (Jun 5).
- **Evaluation suite upgrades** — dashboard-up PREFLIGHT + SKIP status, deterministic floors (py_compile sweep + UI/a11y sanity), drift time-series, mandatory independent verifier on high/critical findings (Jun 5).
- **Zotero local connector** — `sync_zotero_local(db_path)` reads a local `zotero.sqlite` without API key (Jun 16).
- **Semantic Scholar source** — `search_semantic_scholar(query)` via free Graph API (Jun 16).
- **PII redaction tool** — `redact_data_file(path)` returns a masked preview with sensitive columns pseudonymised (Jun 16).
- **Output rail** — `scan_outgoing(text)` pass/block verdict + masked version before sending (Jun 16).
- **Knowledge graph markdown export** — `export_knowledge_markdown(out_dir)` generates Obsidian-style vault with `[[wikilinks]]` (Jun 16).
- **Project customization** — rename, category, colour (accent_color), multi-tag, category/tag filtering in Work tab; backend `/api/project/update/{id}` (Jun 16).
- **Desktop project-tracking** — `metis` router prompt now scaffolds tracked projects; `create_project_full()` + `create_task()` from Claude Desktop (Jun 4).
- **Dashboard autostart toggle** — Metis tab → "Startup & persistence" card; registers/removes Windows autostart task over WSL interop, no admin (Jun 22).
- **MCP prompts for Claude Desktop** — 42 prompts (1 `metis` router + one per agent + workflow prompts) in the prompt picker (Jun 2).

### Changed
- **Production stability overhaul** — live DB relocated off OneDrive to `~/.local/share/metis/metis.sqlite` (WAL-safe ext4); removed import-time DB calls (now run in lifespan); supervisor restart loop with backoff in `run.sh`; adopt-don't-kill singleton with `flock` launch-lock; `run.sh` binds `127.0.0.1` (was `0.0.0.0`); persistent rotating logs at `system/config/logs/dashboard.log` (Jun 19–22).
- **MCP server tool count** — 165→210+ registered tools (post progressive disclosure + new tool files).
- **Constitution v1.1** — added no-data-rebuild, no-credential-access, network-allowlist, prefer-safe-analysis rules (Jun 16).
- **Project listing reads registry** — `get_project_status()` now reads `projects` table (14 projects) instead of `projects/active/` folders (2); priority-sorted with task counts (Jun 6).
- **Cross-pollination expanded** — `assemble_brainstorm_context` gained `projects` + `notes` sources; keyword search also searches project titles/descriptions/next_steps (Jun 6).
- **Installer requirements** — `requires-python` capped at `<3.14` (onnxruntime/pyreadstat/pymupdf lack 3.14 wheels); installer pre-flight checks Python 3.10–3.13 + ensurepip (Jun 4).
- **requirements.txt and pyproject.toml** — corrected voice dependencies (resemblyzer, faster-whisper); added `[diarization]` extras group; regenerated pinned freeze from working venv (Jul 13).
- **README** — tool count corrected to 210+ (was 187); agent count "30+" kept; tool subset loading description updated for progressive disclosure.

### Fixed
- **Split-brain DB** — ~12 code paths hardcoded the OneDrive DB path; all routed through `get_db_path()` (Jun 19).
- **Reflected-XSS** in search; broadened PII detection (international phone formats, household-precision GPS) and prompt-injection detection (Jun).
- **File tracking recursion** — `_ensure_tracked_files()` called itself instead of running CREATE TABLE DDL; all file-tracking tools were broken since Apr 13 (Jun 4).
- **Dark mode default** and tab 500 error on `_metis_user_name` missing.
- **Orphaned tracked_files** — relabelled 3,451 orphaned entries to correct project slugs (Jun 5).
- **Prompt registration** — `register_prompts()` false failure when `_AGENTS_DIR` absent in verify subprocess; now handles missing dir gracefully (Jun 4).
- **API-key banner save** — was missing the confirm header (403) (Jul).
- **Dashboard reliability** — offline model load, brief import/log, session dedup (Jul).

## [0.2.0] — 2026-05-27

### Added
- **Live meeting voice recognition** — Speaker profiles enrolled via audio sample or browser recording. Cosine similarity matching (resemblyzer GE2E embeddings) auto-identifies enrolled speakers during transcription. Running mean across samples improves accuracy over time.
- **Speaker management UI** — Voice Profiles panel in Meetings tab: enroll, list, delete. Shows enrollment count per speaker.
- **Biostatistician agent** — R package development, simulation studies, sample size/power calculations, Monte Carlo methods, CRAN-ready package scaffolding.
- **Dashboard Engineer agent** — Restored and rewritten. Owns FastAPI + HTMX dashboard architecture, tab design, and partial rendering patterns.
- **7 new dashboard partials** — Knowledge topic coverage, teaching courses, morning brief, agent directory, and more.
- **Memory loop** — Session bootstrap, working memory, model registry, and persona discipline are now fully wired.
- **Comprehensive eval toolkit** — `tests/functional/run_metis_promises.sh` harness, promise registry, self-reflexion skill.
- **Knowledge tab** — knowledge layer browser, unified search, coverage gap analysis, recently-added strip.
- **Research timeline** — `record_research_finding()`, `query_research_timeline()`, `list_research_entities()` for tracking evolving beliefs over time.
- **Session consolidation** — `consolidate_session_memory()` distils session history into persistent episodic memory.

### Fixed
- Live meeting button non-functional when navigating to Meetings tab via HTMX (script now loaded globally in base.html).
- Dark mode default and tab 500 error on `_metis_user_name` missing.
- `prefers-color-scheme` media query removed — Metis is dark-only.
- Zotero sync, DB commit bug, `.env` cleanup.
- Setup hooks: removed hardcoded username path in stop hook.

### Changed
- MCP server bumped to **0.2.0**.
- README: MCP tool count corrected to 165+ (was 76+).
- README: Outbound services table expanded — CrossRef, HuggingFace, Google Drive, Gemini now documented.
- `requirements.txt`: `resemblyzer`, `webrtcvad-wheels`, `soundfile` added for voice recognition.
- `schema.sql`: `speakers` table added.

## [1.0.0] — 2026-05 (initial public release baseline)

### Added
- 34-agent research system with full MCP tool access.
- 9-tab dashboard (Today, Knowledge, Meetings, Learning, Work, Thinking, Planner, Teach, Metis).
- FastAPI + HTMX + SQLite stack, running fully locally.
- MCP server with 165 registered tools via FastMCP.
- Live meeting assistant with Whisper transcription and diarization.
- PDF knowledge bases (epi-methods, ph-background, hat-specialist) with vector search.
- Self-improvement loop: reflexion → proposal → approval → application.
- Data protection: PII detection, injection probes, AES-256 encryption, machine-readable constitution.
- Morning intelligence brief: papers, news, surveillance alerts, focus recommendation.
- Voice capture and transcription (faster-whisper, fully local).
- Course builder: intake → harvest → curriculum → draft → review → publish.
- Knowledge graph, brainstorm engine, research timeline.
- WSL2 + Windows installer (Inno Setup + PowerShell), macOS bash installer.
