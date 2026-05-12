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

- [ ] **M — 11 missing slash commands**  
  These agents are registered in routing but have no `/<slug>` skill file — invoking them fails silently.  
  Create stub `.claude/skills/<slug>/skill.md` for each:  
  `course-builder`, `content-harvester`, `design-auditor`, `frontend-designer-builder`,  
  `hr-talent`, `learning-architect`, `news-aggregator`, `rc-builder`,  
  `research-architect`, `visualization-maker`, `data-analyst`  
  Each stub: description, input format, steps, output. Pull from existing system-prompts.

- [ ] **XS — news_briefs source_type column**  
  Add `source_type TEXT DEFAULT 'news'` column to `news_briefs` table (ALTER TABLE + backfill).  
  Distinguish RSS news items from scientific articles. Feeds news rail categorisation and morning brief.

- [ ] **XS — metis-identity.json** `system/config/metis-identity.json`  
  Machine-readable file: version, active agent list, install profile, feature flags, domain.  
  Enables any AI interface to discover what this Metis instance can do without reading CLAUDE.md.

- [ ] **L — Empty states on all 9 tabs**  
  Every tab shows "0" or blank on first use with no guidance.  
  Each tab needs first-run copy and a clear next-step action:  
  - Knowledge: "Import your literature — run `/metis-library-setup` to connect Zotero"  
  - Meetings: "Drop a transcript in `inbox/` or paste one with `/meeting-memory`"  
  - Work: "Add your first project — type `t:` + task name in the capture bar"  
  - (etc. for all 9 tabs)

---

## Phase C — Automation and ambient operation
*What makes Metis run without being asked. The system should work while you sleep.*

- [ ] **L — Morning scan at 07:00**  
  APScheduler job already exists. What's missing: the OS-level process that keeps it alive.  
  Implementation:  
  1. Windows Task Scheduler entry at user logon → runs `run.bat` (wake WSL, start dashboard)  
  2. NSSM wraps the FastAPI process as a Windows service (auto-restart on crash)  
  3. APScheduler `job_morning_scan()` fires at 07:00 inside the running process  
  *The "Schedule morning brief" button on the dateline already writes the Task Scheduler entry — verify it works end-to-end.*

- [ ] **L — Inbox auto-processing**  
  Files dropped in `inbox/` are not automatically picked up.  
  Implementation: `watchdog` library polling at 5-second interval (NTFS-compatible, inotify is not).  
  On new file: call `scan_inbox()` → route to Librarian or appropriate agent.  
  Add `watchdog` to requirements.txt.

- [ ] **M — PLANNING.md auto-update at session end**  
  The stop hook (Phase A) writes the handoff brief. Extend it to also update the active project's PLANNING.md with what was done and what the next step is. Currently manual.

- [ ] **S — PubMed daily literature monitoring** `tools/literature_monitor.py`  
  New MCP tool: `scan_pubmed_alerts(query="trypanosomiasis OR sleeping sickness", reldate=1)`.  
  Uses NCBI E-utilities free API. Inserts to `news_briefs` table with `source_type='article'`.  
  Add to `job_morning_scan()` alongside RSS feeds.  
  *Free API, no key required, 5-10 new papers per day for HAT.*

- [ ] **M — OpenAlex paper monitoring** `tools/literature_monitor.py`  
  `scan_openalex(query, from_publication_date=yesterday)`.  
  OpenAlex covers 474M papers including preprints, no API key required.  
  Same insert pattern as PubMed scan.

---

## Phase D — Intelligence and quality
*Where the system gets meaningfully smarter.*

- [x] **Morning brief AI-generated** — DONE 2026-05-12  
  `_get_or_generate_brief()` in `today.py`: assembles context, calls Claude Haiku, caches result.

- [x] **Semantic theme extraction for self-improvement** — DONE 2026-05-12  
  `_theme_from()` in `improvement.py` now calls Claude Haiku for semantic themes, falls back to word frequency.

- [ ] **L — Morning brief: richer structure**  
  Current brief is a single paragraph. Improve toward the IHP Newsletter pattern:  
  - One leading insight (what to think about today)  
  - 2–3 items grouped by theme (not just listed)  
  - One research thread to pick up  
  - Feedback buttons per item ("useful / not useful") feeding a relevance table  
  *IHP model: narrative prose, editorial commentary, cross-references between stories.*

- [ ] **L — Domain-specific tool loading**  
  Currently all 120 tools are loaded on every agent call.  
  Group tools into 6 domain subsets: literature, writing, methods, data, admin, security.  
  Each agent declares its subset; MCP serves only that subset.  
  Estimated 50–80% input token reduction.  
  *This is the single highest-ROI token efficiency change available.*

- [ ] **S — token-efficient-tools beta header**  
  Add `anthropic-beta: token-efficient-tools-2025-02-19` to all Claude API calls in `pipeline.py`.  
  One line of code. Estimated 14% output token savings.

- [ ] **S — Prompt caching for stable prefixes**  
  Add `cache_control: {"type": "ephemeral"}` to the stable system prompt + tool block prefix.  
  Move any dynamic content (timestamps, session IDs) after the cached block.  
  90% cost reduction on repeated calls within a 5-minute window.

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

- [ ] **S — Session-level injection tracking**  
  Current `pre-tool-use.mjs` fires independently on each call. Extend: maintain a session counter per pattern.  
  If the same injection pattern fires 3+ times in a session: raise severity from warn to block, log to `security_events` table.  
  Repeated probing is a qualitatively different threat than a single match.

- [ ] **S — /security-scan skill**  
  Skill that runs a security audit from Claude Code:  
  - Read last session's tool-use audit log (from PostToolUse hook)  
  - Run `check_data_safety()` on any files read this session  
  - Verify no API keys or patient identifiers appeared in outputs  
  - Print a clean pass/fail summary  

- [ ] **M — Enterprise controls file** `system/config/enterprise-controls.md`  
  Governance document for research institutes deploying Metis to their researchers:  
  data classification policy, access controls, escalation procedures, audit requirements.  
  Not code — documentation that makes Metis credible to IT departments.

- [ ] **M — Output PII scan**  
  Scan Claude's text responses (not just inputs) for accidentally included secrets or patient identifiers.  
  Hook on the PostToolUse event: if the tool result contains high-confidence PII patterns, log and warn.  
  *Gap specific to the patient-data research context.*

---

## Phase F — Developer experience and installation
*Lowering the barrier for new researchers and institutional deployments.*

- [ ] **L — Install profiles in setup-mcp.sh**  
  Add a profile selector at the start of installation:  
  - `light`: MCP server only. Works with Claude Desktop + Claude Code. No dashboard. ~5 min.  
  - `standard`: MCP server + dashboard. Full 9-tab UI. ~15 min.  
  - `full`: Standard + Windows Task Scheduler automation + daily scan. ~25 min.  
  Write chosen profile to `system/config/install-state.json`.

- [ ] **S — install-state.json** `system/config/install-state.json`  
  Records: installed profile, version, install date, optional components.  
  Read by `metis-update` skill to know what needs updating.  
  Read by `metis-doctor` health check to surface profile-specific gaps.

- [ ] **M — /metis_config rewrite for Python dashboard**  
  Current wizard requires R + RStudio + 17 R packages, walks through 10 wrong tabs, writes config keys that no code reads.  
  Rewrite: Python-based, covers the actual 9 tabs, prompts for API key, asks for research domain, writes keys that are wired to real behaviour.  
  *Blocking for public release.*

- [ ] **M — .gemini/GEMINI.md**  
  Gemini 2.0 harness configuration equivalent to CLAUDE.md.  
  `google-genai` is already in requirements.txt — this is documentation + routing config, not new code.  
  Adds multi-AI interface support without changing the underlying MCP tools.

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

- [ ] **L — Meeting Memory cross-references projects and papers**  
  After saving a meeting transcript, auto-link action items to open projects and surface related papers from the library.  
  Currently: transcription + extraction only.

- [ ] **L — Telegram bot for mobile capture**  
  Text, voice note, or image sent to a Telegram bot → arrives in Metis inbox → cross-pollination runs overnight.  
  Implementation: `python-telegram-bot` library + `faster-whisper` for voice (local transcription, no audio leaves machine).  
  Telegram is strictly better than WhatsApp for this: open API, no approval process, free.  
  *The WhatsApp webhook stub in `webhook.py` can be repurposed.*

- [ ] **M — Mobile PWA capture page**  
  FastAPI `/capture` route + `manifest.json` + service worker = home screen shortcut on phone.  
  Accessible via Tailscale from anywhere. No external service dependency.  
  *Simpler than Telegram if Stan already has Tailscale installed.*

- [ ] **L — Course Builder end-to-end pipeline**  
  System-prompt and questionnaire exist. Missing: orchestration code, `/course-builder` slash command, Quarto integration for lesson rendering.

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

- [ ] **M — Agent eval harness**  
  For each agent: a small set of golden input/output pairs.  
  Before promoting a self-improvement proposal: run candidate skill.md against golden inputs, compare output quality to incumbent.  
  Prevents promoting changes that break agent behaviour. Currently promotion is a judgement call with no data.

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
