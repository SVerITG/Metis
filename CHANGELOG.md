# Changelog

All notable changes to Metis are documented here.

## [0.2.0] — 2026-05-27

### Added
- **Live meeting voice recognition** — Speaker profiles enrolled via audio sample or browser recording. Cosine similarity matching (resemblyzer GE2E embeddings) auto-identifies enrolled speakers during transcription. Running mean across samples improves accuracy over time.
- **Speaker management UI** — Voice Profiles panel in Meetings tab: enroll, list, delete. Shows enrollment count per speaker.
- **Biostatistician agent** — R package development, simulation studies, sample size/power calculations, Monte Carlo methods, CRAN-ready package scaffolding.
- **Dashboard Engineer agent** — Restored and rewritten. Owns FastAPI + HTMX dashboard architecture, tab design, and partial rendering patterns.
- **7 new dashboard partials** — Knowledge topic coverage, teaching courses, morning brief, agent directory, and more.
- **Memory loop** — Session bootstrap, working memory, model registry, and persona discipline are now fully wired.
- **Comprehensive eval toolkit** — `tests/functional/run_metis_promises.sh` harness, promise registry, self-reflexion skill.
- **Knowledge tab** — HAT corpus browser, unified search, coverage gap analysis, recently-added strip.
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
