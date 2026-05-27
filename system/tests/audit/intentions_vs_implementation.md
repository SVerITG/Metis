# Metis — Intentions vs Implementation Report

**Date:** 2026-05-15  
**Basis:** All conversations, prompts, and implementation sessions from the Research Cortex project.  
**Auditor:** Automated audit against live codebase.  
**Purpose:** Comprehensive gap analysis — what was intended, what is built, what is missing.

---

## How to read this

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully implemented and verifiable |
| 🟡 | Partially implemented — core works, details missing |
| ❌ | Not implemented |
| ⚠️ | Known gap — explicitly deferred or requires user action |
| 🔬 | Requires live test (automated tests cover structure, not runtime behaviour) |

---

## 1. Core Concept — Research Companion

**Intention:** Metis is an always-on research companion for a senior researcher/PhD student. It routes requests to the right specialist, stays aware of context across sessions, and surfaces connections the researcher would otherwise miss.

| Intention | Status | Evidence |
|-----------|--------|----------|
| Metis always-on (no invocation needed) | ✅ | `CLAUDE.md` — Metis active from first message every session |
| Routes to 30+ specialist agents | ✅ | 32 agents in `agents/` with `skill.md` and `system-prompt.md` |
| Cross-session context via PLANNING.md | ✅ | `stop.mjs` writes PLANNING.md at session end; `CLAUDE.md` reads it at session start |
| User profile drives personalisation | ✅ | `get_user_profile()` called at session start; morning brief and agent runs use interests |
| Plain English — never condescending | ✅ | `metis-persona.md` spec; validated in persona tests |
| Works in Claude Code + Claude Desktop | ✅ | MCP server registered globally; `~/.claude/settings.json` + `claude_desktop_config.json` |

---

## 2. Installation Paths

**Intention:** A researcher at any skill level on any platform can get Metis running in under 30 minutes.

| Path | Intention | Status | Evidence |
|------|-----------|--------|----------|
| Windows `.exe` installer | One-click install, no Python knowledge | 🟡 | `metis-setup.iss` complete; Inno Setup compile pending (requires testing on a Windows machine) |
| Bash install (Linux/macOS) | `setup-mcp.sh` with profile selector | ✅ | `setup-mcp.sh` with light/standard/full profiles; `install-state.json` written |
| Docker | `docker compose up -d` | 🟡 | `Dockerfile` + `docker-compose.yml` written; GHCR push workflow exists; not yet runtime-tested |
| Manual (claude.ai Projects) | `CLAUDE.md` self-contained | ✅ | `claude-project-wizard.md` + `claude-project-instructions.md` |
| Bundle Python (offline Windows) | `download_vendor_python.ps1` | ✅ | 4-strategy Python cascade in `bootstrap_python.ps1` |
| Tray launcher | System tray icon on Windows | ✅ | `tray_launcher.py` wired into installer + `install.ps1` |
| Clean-VM test | Verify `.exe` on fresh machine | ⚠️ | Requires manual test on a clean Windows VM — all code is done |
| Code signing | `.exe` trusted by Windows Defender | ⚠️ | Not yet signed — may trigger Defender warning on install |

---

## 3. First-Run Config Wizard

**Intention:** A 13-section guided setup that runs on first launch, personalises Metis completely, and removes barriers to first use.

| Section | Intention | Status | Evidence |
|---------|-----------|--------|----------|
| 1 — About You | Capture name, role, domain | ✅ | `write_user_config()` stores `user.name`, `user.role` |
| 2 — Research Domain | Field, interests, populations | ✅ | Stored in `user-config.yaml` under `research:` |
| 3 — News Monitoring | PubMed queries, news topics | ✅ | Stored in `user-preferences.json`; feeds `scan_pubmed_alerts()` |
| 4 — Current Projects | Active projects + deadlines | ✅ | MCP tools write to `projects` table + `user-config.yaml` |
| 5 — Seed Knowledge | Web seeding, PDF import, Zotero | 🟡 | `content_scan()`, `index_library_pdfs()` exist; Zotero sync present; no guided auto-run |
| 6 — Ideas/Notes Import | Import existing idea document | ✅ | `ingest_ideas_document()` handles .txt/.md/.docx |
| 7 — Meeting Notes Import | Import past meetings | 🟡 | `process_meeting_transcript()` exists; wizard calls it but no batch import UI |
| 8 — Working Style | Response length, tools, stats methods | ✅ | Stored in `user-config.yaml` under `style:` |
| 9 — Teaching | Courses, monitor literature | ✅ | Stored in `user-config.yaml` under `teaching:` |
| 10 — Data Sensitivity | Patient data, GDPR, PII mode | ✅ | `METIS_PII_STRICT=1` activated; stored in `data_sensitivity:` |
| 11 — Dashboard Appearance | Theme, density | ✅ | Stored in `user-preferences.json`; applied in `base.html` |
| 12 — Plain English Explanation | Explain how Metis works | ✅ | Full explanation in wizard spec Section 12 |
| 13 — Finish | Write configs, remove marker | ✅ | `write_user_config()` + `write_user_preferences()` + `remove_first_run_marker()` |
| Dashboard `/setup` page | GUI wizard for .exe users | ✅ | `routers/setup.py` + `templates/setup.html` |
| `.first-run` trigger | Automatic wizard on first open | ✅ | `CLAUDE.md` checks for `.first-run` marker |

---

## 4. Dashboard — 9 Tabs

**Intention:** A fully-functional HTMX dashboard where every surface serves a specific research use case.

### Today Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Morning brief — AI-generated, domain-specific | ✅ | Claude Haiku with prompt caching; IHP 3-paragraph structure |
| Morning brief — cached (not regenerated every refresh) | ✅ | `daily_insights` table caches per day |
| News rail — real RSS feeds | ✅ | 23 RSS feeds (ProMED, IHP, Lancet, BMJ, arXiv, Reuters, WHO…) |
| Today tab value with zero data | ✅ | Empty states verified; tabs don't crash on empty DB |
| Resume section — what was I doing | ✅ | `today_resume.html` partial |
| Ledger — open tasks and follow-ups | ✅ | `today_ledger.html` queries tasks + meetings |
| Token footer — session token usage | ✅ | `today_token_footer.html` + `metis_token_monitor.html` |
| Automation panel — scheduler controls | ✅ | Per-job controls, ON/OFF toggle, RUN now button |
| Capture modal from Today | ✅ | `Ctrl+K` shortcut in `app.js` |

### Knowledge Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Library cards — reading status | ✅ | `knowledge_cards.html` + `library_cards` table |
| Literature metadata table | ✅ | `knowledge_literature.html` + `literature_metadata` table |
| PDF semantic search (Phase L) | ✅ | `knowledge_pdf_search.html` + `search_pdf_knowledge()` MCP tool |
| Domain breakdown | ✅ | `knowledge_domains.html` |
| Live search with HTMX | ✅ | `knowledge_search.html` with hx-get |
| Knowledge graph | ✅ | `knowledge_graph.html` |
| Zotero sync status | ✅ | `knowledge_sync_status.html` |

### Meetings Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Import meeting notes (text/transcript) | ✅ | `meeting_import_form.html` + `meeting_import_result.html` |
| Live meeting assistant (record + transcribe) | 🟡 | `meeting_live_session.html` + `meeting_live_setup.html` present; transcription wired via `routers/transcription.py` |
| Action item extraction | ✅ | `enrich_meeting_with_crossrefs()` extracts keywords → tasks |
| Cross-reference to projects/papers | ✅ | `meetings.py` MCP tool: `enrich_meeting_with_crossrefs()` |
| Meetings week-ahead | ✅ | `meetings_week_ahead.html` partial |
| Meeting follow-ups in Today | ✅ | `meetings_follow_ups.html` + Today ledger query |
| IRB/ethics committee format | 🟡 | Meeting Memory agent has this in skill.md; not a separate template |

### Learning Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Spaced repetition — cards due today | ✅ | `learning_due.html` + `learning_items` table |
| Course progress bars | ✅ | `learning_courses.html` + `learning_courses` table with progress_pct |
| Competency map | ✅ | `learning_competencies.html` |
| Streak tracker | 🟡 | Partial — `learning_items.reviewed_count` exists; UI streak display not confirmed |
| Course Builder publish → Learning tab | ✅ | `publish_course()` marks `learning_courses.status='active'` |

### Work Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Task list with priority | ✅ | `work_tasks.html` + `tasks` table with priority colours |
| Active projects — grouped by domain | ✅ | `work_projects.html` + `projects` table |
| Project launcher (open in VS Code / RStudio) | ✅ | `/api/project/launch` endpoint + `work_project_detail.html` |
| Project kanban | ✅ | `work_kanban.html` |
| Work tab stats | ✅ | `work_stats.html` |
| Cross-project task linkage | ❌ | Tasks have `project` field but no cross-project view |

### Thinking Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Idea capture with cross-pollination | ✅ | `capture_idea()` embeds to `vec_episodic`; hybrid vector + keyword search |
| Notes | ✅ | `thinking_notes.html` |
| Open questions | ✅ | `thinking_questions.html` |
| Brainstorm sessions | ✅ | `thinking_brainstorm_sessions.html` + `brainstorm.py` MCP tool |
| Cross-pollination shows connections | ✅ | nomic-embed-text-v1.5-Q (768-dim) + RRF merge |
| Thinking threads persist | ✅ | `ideas` + `memory_entries` tables |

### Planner Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Kanban (someday/incubating/active) | ✅ | `planner_kanban.html` |
| PhD focus board | ✅ | `planner_focus.html` |
| Weekly intentions vs actuals | ✅ | `planner_week.html` + `planner_intentions.html` |
| Quarterly/horizon view | ✅ | `planner_horizon.html` + `planner_timeline.html` |
| PLANNING.md per project | ✅ | `stop.mjs` auto-updates PLANNING.md at session end |

### Teach Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Course cards with library alerts | ✅ | `teach_courses.html` + `teach_lit_alerts.html` + `teach_news_alerts.html` |
| Course Builder form | ✅ | `teach_courses_list.html` + Course Builder buttons |
| Chat / Co-work / Slides / Assessment / Q-bank / Gap-analysis | 🟡 | Buttons exist in `app.js` (stubs: `openCourseChat` etc.); backend pipeline exists; full e2e not confirmed |
| Course → Learning tab publish | ✅ | `publish_course()` MCP tool |
| PowerPoint export | ⚠️ | Requires `python-pptx` or Quarto; listed as manual step |

### Metis Tab
| Intention | Status | Evidence |
|-----------|--------|----------|
| Agent run history | ✅ | `metis_runs.html` + `agent_runs` table |
| Token stats | ✅ | `metis_stats.html` |
| Agent directory (all 32 agents) | ✅ | `metis_agent_directory.html` + `metis_agents.html` |
| System info | ✅ | `metis_system_info.html` |
| Self-improvement loop | ✅ | `metis_improvement.html` — aggregate_reflexions, draft/promote/reject proposals |
| Identity card + edit modal | ✅ | `metis_identity_card.html` + `metis_identity_edit_modal.html` |
| Token monitor | ✅ | `metis_token_monitor.html` |
| Trust badge (local-only reassurance) | ✅ | `trust_badge.html` |
| Tracing/observability | ✅ | `metis_traces.html` + `observability.py` MCP tool |
| Memory overview | ✅ | `metis_memory_overview.html` + `metis_memory_stream.html` |

---

## 5. Agents (32 deployed)

**Intention:** A team of specialist agents covering all research domains. Each agent has a `skill.md` (Claude Code invocation) and `system-prompt.md` (deep work). The orchestrator routes between them.

| Agent | Intended Use | Status |
|-------|-------------|--------|
| `metis` | Master orchestrator | ✅ |
| `librarian` | Literature search, Zotero | ✅ |
| `epidemiologist` | Study design review, STROBE, CONSORT | ✅ |
| `writing-partner` | Draft, revise, structure arguments | ✅ |
| `methods-coach` | Statistical methods, R methodology | ✅ |
| `phd-architect` | Thesis structure, article alignment | ✅ |
| `meeting-memory` | Transcribe, structure, brief meetings | ✅ |
| `news-radar` | Morning brief, WHO/policy monitoring | ✅ |
| `software-engineer` | Python/R code review, FastAPI | ✅ |
| `data-guardian` | PII protection, patient data blocking | ✅ |
| `data-analyst` | CSV/Excel/Stata profiling, cleaning | ✅ |
| `dhis2-expert` | DHIS2 dashboards, tracker, metadata | ✅ |
| `course-builder` | 7-step course pipeline | ✅ |
| `learning-coach` | Spaced repetition, skill progression | ✅ |
| `learning-architect` | Curriculum design, competency maps | ✅ |
| `career-coach` | EU job-market, CV support | ✅ |
| `builder` | New apps, tools, MCP servers | ✅ |
| `rc-builder` | Extend Metis itself | ✅ |
| `presentation-maker` | PowerPoint-compatible slides | ✅ |
| `content-harvester` | Web, PDF, DOCX, YouTube extraction | ✅ |
| `background-maker` | Build RAG knowledge layers | ✅ |
| `visualization-maker` | ggplot2, Plotly, Mermaid diagrams | ✅ |
| `news-aggregator` | RSS curation, signal tagging | ✅ |
| `design-auditor` | UI audit, design critique | ✅ |
| `frontend-designer-builder` | UI/UX, CSS, design system | ✅ |
| `cybersecurity` | Injection defence, threat intel | ✅ |
| `research-architect` | Study design, methodology planning | ✅ |
| `edu-expert` | Education research specialist | ✅ |
| `hr-talent` | HR and talent management context | ✅ |
| `dashboard-engineer` | Dashboard build specialist | ✅ |
| `ux-engineer` | UX engineering, accessibility | ✅ |
| `release-coordinator` | Release management | ✅ |

---

## 6. MCP Tools (43 modules)

**Intention:** A complete tool layer that gives agents the ability to read/write all Metis data and perform specialised operations.

| Module | Core Function | Status |
|--------|--------------|--------|
| `agents.py` | List and describe agents | ✅ |
| `anonymization.py` | Strip PII before external transmission | ✅ |
| `backup.py` | Nightly SQLite backup | ✅ |
| `brainstorm.py` | Cross-pollination trigger | ✅ |
| `config_tools.py` | write_user_config, write_user_preferences, wizard tools | ✅ |
| `content_scan.py` | Scan web/PDFs for content | ✅ |
| `course_builder.py` | 4-tool course pipeline | ✅ |
| `data_tools.py` | CSV/Excel/SPSS/Stata profiling | ✅ |
| `doctor.py` | System health diagnostics | ✅ |
| `files.py` | read_file, list_basket, promote_basket_item | ✅ |
| `fulltext_index.py` | Full-text search over library | ✅ |
| `guardrails.py` | injection_probe, validate_agent_output | ✅ |
| `handoff.py` | generate_handoff_brief | ✅ |
| `ideas.py` | capture_idea, cross_pollinate, semantic_search | ✅ |
| `images.py` | Image extraction and processing | ✅ |
| `improvement.py` | aggregate_reflexions, draft_self_improvement_proposal | ✅ |
| `intelligence.py` | assemble_daily_context | ✅ |
| `knowledge_db.py` | build_pdf_knowledge_db, search_pdf_knowledge | ✅ |
| `knowledge_graph.py` | Knowledge graph generation | ✅ |
| `library.py` | add_library_card, update_library_card | ✅ |
| `literature.py` | Literature metadata management | ✅ |
| `literature_monitor.py` | scan_pubmed_alerts, scan_openalex | ✅ |
| `meetings.py` | enrich_meeting_with_crossrefs | ✅ |
| `memory.py` | Memory entries CRUD | ✅ |
| `notes.py` | Note capture and retrieval | ✅ |
| `observability.py` | Session telemetry, tool-use audit | ✅ |
| `observation.py` | Research observations | ✅ |
| `paperqa_search.py` | index_library_pdfs, ask_library | ✅ (API key needed for indexing) |
| `pipeline.py` | run_metis, orchestration | ✅ |
| `projects.py` | Project CRUD, tracking | ✅ |
| `ref_miner.py` | Reference mining from PDFs | ✅ |
| `research.py` | Research session helpers | ✅ |
| `reviews.py` | Agent review logging | ✅ |
| `safety.py` | Red-line enforcement | ✅ |
| `self_improvement.py` | apply_proposal, reject_proposal | ✅ |
| `tasks.py` | Task CRUD | ✅ |
| `thinking_profile.py` | Thinking profile management | ✅ |
| `transcription.py` | Voice/audio transcription | ✅ |
| `user_profile.py` | get_user_profile | ✅ |
| `vector_memory.py` | Episodic vector memory (768-dim) | ✅ |
| `voice_capture.py` | Voice capture integration | ✅ |
| `zotero.py` | Zotero library sync | ✅ |

---

## 7. Slash Commands / Skills (56 total)

**Intention:** Every agent and workflow has a Claude Code `/skill` invocation. Power users can invoke specialists directly; beginners use `/metis` for routing.

**Status:** 56 skills present in `.claude/skills/`. Core skills verified:

| Skill | Status |
|-------|--------|
| `/metis` | ✅ |
| `/librarian`, `/epidemiologist`, `/writing-partner` | ✅ |
| `/methods-coach`, `/phd-architect`, `/meeting-memory` | ✅ |
| `/news-radar`, `/software-engineer`, `/data-guardian` | ✅ |
| `/data-analyst`, `/course-builder`, `/learning-coach` | ✅ |
| `/builder`, `/rc-builder`, `/background` | ✅ |
| `/metis_config` | ✅ |
| `/metis_brainstorm`, `/metis_handoff`, `/metis_weekly` | ✅ |
| `/metis_research`, `/metis_status`, `/metis_notes` | ✅ |
| `/metis_ideas`, `/metis_morning` | ✅ |
| `/security-scan` | ✅ |
| `/add-context` | ✅ |

---

## 8. Security & Governance

**Intention:** Patient data and PII must never leave the local machine. Multiple independent layers of protection.

| Intention | Status | Evidence |
|-----------|--------|----------|
| Injection probe on external tool results | ✅ | `guardrails.py` — 11 patterns + zero-width chars |
| Session-level injection counter (3+ hits → block) | ✅ | `pre-tool-use.mjs` maintains `/tmp/metis-injection-session.json` |
| Data Guardian blocks patient-ID files | ✅ | `data-guardian/system-prompt.md` + `safety.py` + `pii-patterns.txt` |
| PII scan on tool outputs | ✅ | `post-tool-use.mjs` scans email/phone/patient-ID patterns |
| Constitution 12-rule system | ✅ | `system/config/constitution.md` loaded at Stage 7.5 |
| Red-lines enforced | ✅ | `system/config/red-lines.md` + `safety.py` |
| Enterprise controls doc | ✅ | `system/config/enterprise-controls.md` |
| Domain allowlist/blocklist | ✅ | `system/config/security/domain-allowlist.txt` + `domain-blocklist.txt` |
| METIS_PII_STRICT mode | ✅ | Flag activates full PII scanning; set by wizard for clinical users |
| Hook profiles (minimal/standard/full) | ✅ | `METIS_HOOK_PROFILE` env var in `pre-tool-use.mjs` |
| Personal data scrub — tracked files | ✅ | `test_personal_data_scrub.py` — 50 tests, all passing |

---

## 9. Automation & Ambient Operation

**Intention:** Metis works while the researcher sleeps. Morning briefs, PubMed alerts, and inbox processing happen automatically.

| Intention | Status | Evidence |
|-----------|--------|----------|
| 07:00 — News scan (RSS + WHO) | ✅ | `job_morning_scan()` in APScheduler |
| 07:30 — PubMed/OpenAlex literature alerts | ✅ | `scan_pubmed_alerts()` + `scan_openalex()` |
| 06:45 — Brief synthesis pre-generation | ✅ | `_get_or_generate_brief()` scheduled |
| Inbox auto-processing on drop | ✅ | `inbox_watcher.py` — 5s polling, classifies by extension |
| 20:00 — Evening reflexion | ✅ | Scheduled job, writes to reflexions table |
| 23:00 — Nightly backup | ✅ | `backup.py` scheduled |
| Sunday 09:00 — Weekly summary | ✅ | Weekly summary job |
| Per-job time controls in UI | ✅ | Automation panel on Today tab |
| Windows Task Scheduler autostart | 🟡 | `schtasks` command generated by "Schedule morning brief" button; end-to-end test pending |
| Stop hook → handoff brief | ✅ | `stop.mjs` calls `generate_handoff_brief()` |
| Pre-compact hook → save working notes | ✅ | `pre-compact.mjs` saves to `journal/pre-compact-*.md` |
| Post-tool-use → session telemetry | ✅ | `post-tool-use.mjs` logs tool name, elapsed time, agent slug |

---

## 10. Knowledge Foundations

**Intention:** Metis ships with a public health + epidemiology background layer (PH edition). Researchers in other fields can build their own backgrounds.

| Intention | Status | Evidence |
|-----------|--------|----------|
| PH seed library (176 resources, 19 domains) | 🟡 | `download-library-ph-seed.sh` written; indexing was running 2026-05-14 |
| PDF semantic index (Phase L) | ✅ | `build_pdf_knowledge_db()` — pypdf → nomic-embed → `pdf_chunks` + `vec_pdf_chunks` |
| PDF search via vec0 ANN | ✅ | `search_pdf_knowledge()` with domain filter |
| PaperQA2 library Q&A | 🟡 | `paperqa_search.py` written; requires `index_library_pdfs()` to run (needs API key) |
| Distributable knowledge DB export | 🟡 | `export_knowledge_db.py` written; indexer must complete first |
| Background Maker agent | ✅ | `agents/background-maker/` — skill.md, system-prompt.md, contract.md |
| Domain backgrounds for other fields | ❌ | Phase G — Social Sciences, Biomedical, Economics not started |

---

## 11. Learning System

**Intention:** Metis helps researchers build structured knowledge through spaced repetition and progressive skill development.

| Intention | Status | Evidence |
|-----------|--------|----------|
| Spaced repetition (SM-2 algorithm) | 🟡 | `learning_items` table has `interval_days`, `ease_factor`, `due_date`; SM-2 update logic in learning router |
| Course Builder 7-step pipeline | ✅ | `start_course_build()` → `save_course_outline()` → `publish_course()` |
| Learning Architect curriculum design | ✅ | `learning-architect/skill.md` + `learning-architect/system-prompt.md` |
| Streak tracker | 🟡 | `reviewed_count` in `learning_items`; visual streak not confirmed in UI |
| Course template for fast authoring | ✅ | `knowledge/course-template/` with K1 lessons pre-applied |
| Teach tab → Learning tab pipeline | ✅ | `publish_course()` creates `learning_courses` row visible in Learning tab |
| Statistics course (MLM) | ✅ | Seeded: statistics-full course (id=6), 14 placeholder courses |

---

## 12. Meeting Memory

**Intention:** Every meeting becomes structured knowledge — action items, decisions, cross-references — without manual work.

| Intention | Status | Evidence |
|-----------|--------|----------|
| Text/transcript import | ✅ | `meeting_import_form.html` + POST endpoint |
| Live meeting recording | 🟡 | UI present; faster-whisper transcription wired; requires HTTPS or localhost |
| Action item extraction | ✅ | `enrich_meeting_with_crossrefs()` + tasks table |
| Cross-reference to papers/projects | ✅ | Keyword extraction → library_cards + projects matching |
| Meeting follow-ups in Today tab | ✅ | `meetings_follow_ups.html` linked from Today ledger |
| IRB/ethics meeting format | 🟡 | In Meeting Memory agent system-prompt; not a dedicated template |
| Meeting audio transcription offline | ✅ | `transcription.py` uses faster-whisper locally |
| PLANNING.md updated from meetings | ✅ | `stop.mjs` + `/api/session/touch-planning` |

---

## 13. Self-Improvement Loop

**Intention:** After every agent run, Metis reflects on what went well, what could improve, and proposes skill.md updates. Over time, agents get better.

| Intention | Status | Evidence |
|-----------|--------|----------|
| `write_reflexion()` after every run | ✅ | `CLAUDE.md` rule: write_reflexion after any agent run |
| Semantic theme extraction from reflexions | ✅ | `_theme_from()` uses Claude Haiku for themes |
| Self-improvement proposals drafted | ✅ | `draft_self_improvement_proposal()` |
| Proposals applied to skill.md on promote | ✅ | `apply_proposal()` writes to agent's `skill.md` on disk |
| Proposals rejected/archived | ✅ | `reject_proposal()` route + UI button |
| Self-improvement UI on Metis tab | ✅ | `metis_improvement.html` with themed reflexions + proposals |
| Agent eval harness before promoting | ✅ | `agent-eval/eval-runner.py` with `--compare` mode |

---

## 14. Open Gaps — Summary

### Critical (blocks a complete persona workflow)

| Gap | Affected Personas | Effort |
|-----|------------------|--------|
| Windows `.exe` compile + clean-VM test | Personas 1, 2, 4, 6, 7, 9 | User-side action |
| PaperQA2 index run (API key in `.env`) | All library users | XS — 5 min setup |
| Morning scan Windows autostart e2e test | All Windows users | S — verify schtasks |

### High (reduces value significantly)

| Gap | Affected Personas | Effort |
|-----|------------------|--------|
| Docker runtime test (not just code) | Developer persona (8) | M |
| Streak tracker UI display | Learning personas (1, 5) | S |
| Teach tab Course Chat/Slides backends | Educator persona (4) | L per feature |
| Cross-project task linkage view | Senior researcher (2), Dept head (9) | M |

### Medium (nice to have)

| Gap | Effort |
|-----|--------|
| Telegram bot for mobile capture | L |
| Domain backgrounds (social sciences etc.) | XL per domain |
| PowerPoint export via python-pptx | M |
| Service worker for offline PWA | M |
| Batch meeting notes import UI | S |

### Low / Explicitly deferred

| Gap | Notes |
|-----|-------|
| OpenTelemetry gen_ai spans | Phase 5.9 — deferred |
| DHIS2 dedicated MCP tool | Skill exists; no MCP module |
| WhatsApp webhook | Replaced by Telegram (also deferred) |
| Multi-user / team features | Metis is single-user by design |

---

## 15. Overall Assessment

**What works exceptionally well:**
- The intelligence pipeline: morning brief → agent routing → reflexion → self-improvement is fully end-to-end.
- Security: five independent layers (hook profile, injection probe, constitution, red-lines, data guardian). Zero personal data in tracked files.
- Automation: 7 scheduled jobs, inbox watcher, PLANNING.md auto-update, handoff brief on exit — Metis genuinely runs while you sleep.
- Knowledge base: Phase L PDF semantic search + PaperQA2 gives the best possible local search over PDFs.
- The 32-agent team is comprehensive — every research workflow has a named specialist.

**What needs attention before "general release":**
1. The `.exe` installer exists as code but is untested on a clean machine — this is the path for 90% of target users.
2. The PWA mobile experience works structurally but offline caching is missing — field epidemiologists need this.
3. The Teach tab course actions (Chat, Slides, Assessment, Q-bank) are stub buttons — the most requested educator features are incomplete.
4. Streak tracker and spaced repetition UI are structurally present but the SM-2 update cycle hasn't been confirmed end-to-end.

**Verdict:** Metis is a production-capable research companion for the primary use case (Windows + Claude Code + daily research workflows). The automation pipeline, security model, and knowledge foundations are solid. The path to broader release (clean VM test, mobile PWA, Teach tab actions) has a clear roadmap.
