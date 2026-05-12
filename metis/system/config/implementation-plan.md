# Metis — Implementation Plan
**Last updated:** 2026-05-12  
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

- [ ] **XL — SPECTER2 / nomic-embed cross-pollination**  
  The largest single architectural gap. Current cross-pollination uses SQL LIKE matching.  
  Target: hybrid vector + entity retrieval finding connections keyword search misses.  
  Implementation path:  
  1. Install `nomic-embed-text` via Ollama (local, free) for notes and ideas  
  2. Install `SPECTER2` via sentence-transformers for papers and abstracts  
  3. Add `connections` table in SQLite for storing cross-pollination vectors  
  4. Async background task on every capture: embed → retrieve top 3 (MMR diversity scoring)  
  5. Enforce: exactly 3 connections, at least 1 from a different content type  
  *This changes the emotional experience of using cross-pollination.*

- [ ] **XL — PaperQA2 + ZoteroDB semantic library search**  
  Replace SQL LIKE search on abstracts with PaperQA2 hybrid retrieval (BM25 + vector + reranker).  
  Enables: "What does my library say about treatment outcomes in stage 2 gambiense HAT?" answered with inline citations.  
  *Separate phase — install size and setup time mean this is post-v1.0.*

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
  `.gemini/GEMINI.md` created: full agent routing table, Stan's profile, key paths, standing rules,  
  and a section explaining how Gemini's native features (Grounding, code execution) relate to MCP tools.

- [ ] **XL — Windows .exe installer**  
  No terminal required. Double-click, answer configuration questions, done.  
  Handles: Python, virtual environment, MCP registration, Windows shortcut, dashboard autostart.  
  *Phase 11 item. Blocking for public release.*

- [ ] **XXL — Docker image**  
  `ghcr.io/sveritg/metis:latest`. Self-contained, no WSL required.  
  Low priority for solo Windows use; high priority for Linux users and institutional deployments.  
  *Phase 11 item.*

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

- [ ] **XL — Phase 10: Automated daily tasks (full)**  
  APScheduler 6-job schedule: 06:45 brief synthesis, 07:00 news scan, 07:30 literature scan, 08:00 inbox processing, 20:00 daily reflexion aggregation, Sunday 09:00 weekly summary.  
  Settings UI in Today tab to enable/disable/reschedule each job.

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

---

## What to build next (ordered recommendation)

1. **Stop hook** (S, 2h) — ambient handoff brief without any user action. Immediate daily value.
2. **11 missing slash commands** (M, 3h) — fixes broken invocations, half a day, high friction reduction.
3. **Hook profiles** (XS, 30min) — flexibility for different work contexts, almost free.
4. **Morning scan at 07:00** (L, 1d) — the single change that most makes Metis feel "on" rather than "waiting".
5. **Inbox auto-processing** (L, 1d) — files dropped, Metis picks them up. No manual step.
6. **PubMed + OpenAlex monitoring** (L, 1d) — new papers arrive without asking. Closes the most obvious research workflow gap.
7. **Empty states on all 9 tabs** (L, 1d) — essential before any public release.
8. **/metis_config rewrite** (M, half day) — blocking for public release.
9. **Domain-specific tool loading** (L, 1d) — 50–80% token cost reduction, biggest ROI on infrastructure.
10. **token-efficient-tools + prompt caching** (S, 3h combined) — quick wins on token cost.
