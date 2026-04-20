# Metis — Build History

Running log of everything built, changed, or decided in the Metis system. Updated after each implementation session.

For detailed session reports, see: `07_outputs/reviews/implementation/`

---

## 2026-04-03 — Session 9 (Phase 7: Security hooks, Dashboard restructure, Claude Desktop commands, Self-improvement)

**Context:** Large multi-session prompt backlog organized into 11 themes. Full implementation of all themes.

### Built

**Security (Theme A)**
- `.claude/hooks/pre-tool-use.mjs` — pre-tool-use hook: domain allowlist, prompt injection detection, sensitive path warnings, destructive rm block
- `.claude/settings.json` — registers hook on WebFetch, WebSearch, Bash, Write, Edit
- `.claude/hooks/README.md` — hook documentation
- Updated `02_agents/data-guardian/skill.md` and `02_agents/cybersecurity/skill.md` to accurately describe hook-based enforcement

**Dashboard restructure (Themes C + D)**
- `R/mod_notes.R` — NEW: Notes tab with Personal Notes (journalling) + Meeting Notes modes
- `R/mod_ideas.R` — Removed Journal mode; added Mindmap as 4th mode (visNetwork, idea connections, filter by idea/project/tags)
- `R/app.R` — Added Notes tab to navbar
- `R/data_store.R` — Added `personal_notes` table, `skill_improvement_proposals` table, `launcher_type`/`launcher_path` columns to projects

**Project launchers (Theme E)**
- `R/mod_projects.R` — Launcher buttons (RStudio/VS Code/Explorer/Claude) per project row; launcher fields in add-project form
- `R/data_store.R` — `insert_project()` updated to accept launcher fields

**Claude Desktop commands (Theme B)**
- `.claude/skills/metis-brainstorm/skill.md` — cross-pollination session
- `.claude/skills/metis-ideas/skill.md` — quick idea capture
- `.claude/skills/metis-notes/skill.md` — personal notes
- `.claude/skills/metis-weekly/skill.md` — weekly summary
- `.claude/skills/metis-research/skill.md` — research session context
- `.claude/skills/metis-status/skill.md` — quick project/task status
- `CLAUDE.md` — updated with RC workflow commands table

**Self-improvement + System tab (Theme J)**
- `08_system/mcp-server/src/metis_mcp/tools/self_improvement.py` — NEW: `propose_skill_improvement`, `get_pending_proposals`, `approve_proposal`, `reject_proposal`
- `R/mod_system.R` — "How Metis knows you" section (thinking profile display + reset) + Pending Proposals section (approve/reject in UI)

**Software Engineer agent (Theme F)**
- `02_agents/software-engineer/skill.md` — Rewritten: explain-first + 5-layer testing approach (unit, integration, UI, edge cases, test output)

**Whisper transcription (Theme G)**
- `08_system/mcp-server/src/metis_mcp/tools/transcription.py` — NEW: `transcribe_recording` MCP tool (Whisper + optional pyannote diarization)
- `R/mod_meetings.R` — Transcribe button per meeting row; modal with MCP call instructions

**Prompt caching + model review (Theme H)**
- `08_system/mcp-server/src/metis_mcp/cache_helpers.py` — NEW: caching utilities for future API-calling tools
- `08_system/token-guardrails.md` — Added detailed per-agent model assignment table

**Code hygiene (Theme I)**
- Deleted `05_sources/code/ruflo-reference/`
- Confirmed: no brand references in R or Python code files

### MCP server updated
- `server.py`: imports `self_improvement`, `transcription`

---

## 2026-04-03 — Session 1 (Token guardrails + MCP improvements)

**Context:** First structured improvement session. Watched YouTube video on token efficiency, implemented recommendations.

### Built
- `08_system/token-guardrails.md` — policy document: 6 rules, model matrix, 5 agent commandments, audit checklist
- `02_agents/cybersecurity/system-prompt.md` — pruned "Example interactions" section (~10 lines)
- `02_agents/data-guardian/system-prompt.md` — trimmed Anthropic data policy, removed examples
- `08_system/mcp-server/src/metis_mcp/tools/agents.py` — added token tracking fields to `log_agent_run()`: `input_tokens`, `output_tokens`, `model`
- `08_system/mcp-server/src/metis_mcp/tools/phd.py` — added `max_chars` cap to `get_phd_context()`
- `08_system/mcp-server/src/metis_mcp/tools/notes.py` — added `max_chars_per_result` to `search_notes()`

### Decisions
- Token guardrail policy adopted: Haiku for triage/formatting, Sonnet for standard tasks, Opus for deep analysis only
- All agents must log token counts going forward

---

## 2026-04-03 — Session 2 (Phase 1: Foundation & Cleanup)

**Context:** Full Metis → Metis rename + dashboard cleanup + policy documents.

### Built
- Root folder: `metis-second-brain/` → `metis/`
- Domain folder: `03_domains/phd/` → `03_domains/research/`
- Dashboard: removed More menu (Finance, Talks, Agents, Search, Graph tabs)
- Dashboard: PhD tab → Research tab (`mod_phd.R` → `mod_research.R`)
- Dashboard: Crucible tab → Dropzone tab (`mod_crucible.R` → `mod_dropzone.R`)
- MCP: `tools/phd.py` → `tools/research.py` (tool renamed `get_research_context`)
- MCP: `config.py` — `paths.phd` → `paths.research`
- MCP: `server.py` — updated import
- DB: `phd_milestones` → `research_milestones` (with migration)
- DB: `crucible_intake` → `dropzone_intake`
- `helpers.R` — `phd_root` → `research_root`
- `data_store.R` — renamed milestone functions
- `08_system/red-lines.md` — 5 non-negotiable constraints + data classification table
- `08_system/workflows.md` — 11 workflows documented with steps
- Various path references updated in README, scripts, hooks

### Decisions
- "Metis" is the platform name (no qualifier). Not "the Metis dashboard."
- Dashboard tabs: Control Room, Library, Research, Projects, Meetings, News, Learning, Ideas, Dropzone (9 tabs)
- No More menu
- Root folder: `/metis/` (was `metis-second-brain/`)

### Pending manual action
- User must update Claude Desktop config: `METIS_PKM_ROOT` → new path ending in `metis`

---

## 2026-04-03 — Session 3 (Phase 2: Agent Architecture Refactor)

**Context:** All agents converted to skill.md format. New agents created.

### Built
- 17 existing agents: `system-prompt.md` → `skill.md` (kept alongside)
- `02_agents/research-architect/` created (renamed from `phd-architect/`)
- `02_agents/hr-talent/` — new agent: capability gap assessor
- `02_agents/rc-builder/` — new agent: Metis system builder (Opus)
- `02_agents/edu-expert/` — new agent: educational content standards

### skill.md format adopted
```
---
name, description (routing signal), model, effort, complexity
---
## Reasoning
## Output contract
## Edge cases
```

### Model assignments confirmed
- Opus: software-engineer, dashboard-engineer, rc-builder
- Sonnet: metis, epidemiologist, research-architect, writing-partner, librarian, methods-coach, presentation-maker, ux-engineer, builder, edu-expert
- Haiku: news-radar, news-aggregator, meeting-memory, learning-coach, career-coach, data-guardian, cybersecurity, hr-talent

---

## 2026-04-03 — Session 4 (Phase 3: MCP Server Updates)

**Context:** RC Builder (Opus) orchestrated; Sonnet subagents implemented each file.

### Built
- `tools/ideas.py` — 11 tools: capture_idea, get_ideas, add_journal_entry, get_journal, get_contacts, update_contact, get_glossary, add_glossary_term, find_connections, cross_pollinate, assemble_brainstorm_context
- `tools/safety.py` — check_data_safety (PII scanner, 4-level classification)
- `tools/files.py` — scan_tracked_files, add_tracked_file, remove_tracked_file
- `tools/intelligence.py` — generate_daily_insight, get_daily_insight, get_new_publications, mark_publications_read, get_user_topics, add_user_topic
- `tools/library.py` — archive_library_item, remove_library_item, search_literature_extended
- `tools/config_tools.py` — get_user_profile, add_specialist_context, toggle_context, list_contexts
- `tools/images.py` — generate_image (Gemini flash/imagen + HuggingFace FLUX.1), list_generated_images
- `tools/projects.py` — extended with archive_project, unarchive_project, remove_project
- `server.py` — all 7 new modules imported
- `pyproject.toml` — pyyaml, requests, google-genai added as dependencies

### New SQLite tables (8 new tables, created on first call)
ideas, journal_entries, contacts, glossary, tracked_files, daily_insights, new_publications, user_topics

### Deferred
- WhatsApp webhook (Phase 5) — requires separate FastAPI server process
- Thinking profile tools (Phase 4) — depends on dashboard Ideas tab being built first

---

---

## 2026-04-03 — Session 5 (Phase 4: Dashboard Updates)

**Context:** Full Phase 4 dashboard build. macOS theme, System tab, module expansions.

### Built

**CSS & Theme (4.1)**
- `helpers.R`: `metis_theme()` updated — macOS colors: bg `#f5f5f7`, primary `#0071e3` (macOS blue), fonts → Inter + JetBrains Mono
- `www/styles.css`: ~380 lines of macOS-inspired CSS added at top — CSS custom properties (`:root`), glass-effect cards (`backdrop-filter: blur(20px)`), macOS navbar, form controls, badge variants, all new Phase 4 component classes

**data_store.R (infrastructure)**
- New tables: `journal_entries`, `contacts`, `daily_insights`, `new_publications`, `user_topics`, `brainstorm_sessions`, `tracked_files`
- Default seed: 3 user topics (sleeping sickness, public health, AI developments)
- ALTER TABLE `agent_runs`: adds `input_tokens`, `output_tokens`, `model` columns if not present
- New helpers: `insert_daily_insight`, `get_daily_insight`, `insert_publication`, `get_publications`, `mark_publication_read`, `get_user_topics`, `log_agent_run` (with token tracking, replaces old 4-param version)

**System tab (4.9)** — `mod_system.R` (new, 16KB)
- Section 1: My Profile — reads `08_system/user-config.yaml`, displays verbatim
- Section 2: Agent roster — reads all `02_agents/*/skill.md` frontmatter, shows name/model/effort/description in CSS grid cards + last-run timestamp from `agent_runs`
- Section 3: Data protection — renders `08_system/red-lines.md`, data classification table, Data Guardian status
- Section 4: Token usage — weekly burn table from `agent_runs` (runs, input/output tokens per agent)

**Control Room (4.11)** — `mod_control_room.R` extended
- "Today's insight" card — shows `daily_insights` for today; "Generate" button opens prompt modal with copy-to-clipboard
- "New publications" card — shows unread items from `new_publications` table; "Mark read" per item; "Mark all read" button

**Ideas tab (4.2)** — `mod_ideas.R` full rewrite (34KB)
- Three-mode toggle: Ideas | Journal | Brainstorm (macOS-style pill toggle)
- Journal mode: mood + energy + content entry; recent entries as cards with mood emoji
- Brainstorm mode: multi-select context sources; assembles structured prompt for Claude Code; recent sessions list; copy-to-clipboard button
- DB helpers: `insert_journal_entry`, `get_journal_entries`, `insert_brainstorm_session`, `assemble_brainstorm_context`

**Research tab (4.3)** — `mod_research.R` extended
- "Active research documents" card — scans `03_domains/research/` for .docx/.md/.txt/.Rmd, shows last-modified, "Open" button per .docx
- "Scan for updates" button — compares mtimes against `tracked_files` table; shows changed files list; updates table

**Projects tab (4.6)** — `mod_projects.R` extended
- Projects table converted from `renderTable` → `renderUI` with Archive/Remove buttons per row
- Archive: sets `status = 'archived'` in DB (reversible)
- Remove: confirmation modal → deletes project + tasks from DB (files not touched)
- Un-archive button shown for archived projects

**Learning tab (4.7)** — `mod_learning.R` extended
- "Skill Gap Analysis" card at bottom — "Analyse my work" button builds a `/learning-coach` prompt from competency levels + recent activities + recent agent_runs; shows untouched competencies; copy-to-clipboard

**News tab (4.8)** — `mod_news.R` extended
- AI & Tools section at top — dark-themed card showing briefs where `domain = 'AI'`; signal-strength emojis; clickable titles if source_url present

**Launcher & shortcut**
- `launch_metis.bat` — renamed launcher (parallel to old `launch_monia.bat`)
- `create_shortcut.ps1` — PowerShell script to create Windows desktop + Start Menu shortcuts pointing to `launch_metis.bat`; run once with right-click → "Run with PowerShell"

**Meetings tab (4.5)** — `mod_meetings.R` extended (649 lines total)
- Mode bar added at top: `[Quick] [Auto-analyse] [Live] | [Import]` — pill-style toggle
- JavaScript MediaRecorder API: `metisStartRecording(nsPrefix)` / `metisStopRecording(nsPrefix)` — inline JS, no shinyjs
- `uiOutput(ns("recording_panel"))` — mode-aware card showing record/stop buttons + duration counter + live indicator
- `observeEvent(input$audio_data)`: decodes base64 webm, saves to `meetings_root/recordings/recording-YYYYMMDD-HHMMSS.webm`
- Post-recording modal: title/date/type/attendees fields + Claude Code `/meeting-memory` transcription prompt (Whisper not installed)
- `observeEvent(input$save_recording_meta)`: inserts meeting to DB with `transcript_status = 'pending_transcription'`
- Graceful fallback if `base64enc` not installed: shows install instructions + import suggestion

**Library tab (4.10)** — `mod_library.R` extended
- New `library_item_status` table in `data_store.R` — survives TSV refreshes (separate from `library_seeded`)
- New `data_store.R` helpers: `archive_library_item`, `unarchive_library_item`, `remove_library_item`, `get_library_item_statuses`
- "Show archived" `checkboxInput` in Actions card + `archived_count` badge showing "(N archived)"
- `gallery_cards_with_actions(s, ns, statuses, show_archived)` — gallery cards with Archive/Remove/Un-archive buttons; archived items at opacity 0.55
- `lit_table_with_actions(s, ns, statuses, show_archived)` — table rows with Archive/Remove/Un-archive buttons
- Remove: confirmation modal, then `DELETE` from `library_item_status` (item reappears as active on next import)
- Archive is reversible; removed items hidden unless "Show archived" + status is re-checked

### Pending
- WhatsApp webhook (Phase 5) — separate FastAPI server, deferred

---

## 2026-04-03 — Session 6 (Phase 4 complete)

**Context:** Finalized remaining Phase 4 items. Phase 4 is now fully complete.

### All Phase 4 sub-phases delivered

| Sub-phase | Description | Status |
|-----------|-------------|--------|
| 4.1 | CSS & macOS theme | ✅ |
| 4.2 | Ideas tab (Ideas / Journal / Brainstorm) | ✅ |
| 4.3 | Research tab (active docs, scan for updates) | ✅ |
| 4.4 | Dropzone tab | ✅ (pre-existing) |
| 4.5 | Meetings 3 modes (Quick / Auto-analyse / Live / Import) | ✅ |
| 4.6 | Projects archive/remove | ✅ |
| 4.7 | Learning skill gap analysis | ✅ |
| 4.8 | News AI section | ✅ |
| 4.9 | System tab (profile, roster, data protection, token usage) | ✅ |
| 4.10 | Library archive/remove | ✅ |
| 4.11 | Control Room (insight + publications cards) | ✅ |

---

## Plan snapshot (as of 2026-04-03)

---

## 2026-04-04 — Session 7 (Phase 5: Automation & Scheduling)

**Context:** Morning agent automation, 3 new skills, dashboard morning digest.

### Built

**CSS fix**
- Removed conflicting old warm earth-tone CSS from `www/styles.css` (lines 605+) that was overriding the macOS theme: deleted old `h1/h2/h3/.card-header { IBM Plex Serif }`, old `.card`, `.card-header`, `.page-intro`, `.action-row`, `.card-scroll`, `.empty-state` duplicates

**5.1 Morning agent infrastructure**
- `inst/scripts/schedule_agents.R` — updated: `Metis_*` → `Metis_*`, `C:\Metis\` → `C:\Metis\`, times 06:30/07:00 → 07:00/07:30, scripts: `fetch_news_feeds.R` + `morning_librarian.R`
- `inst/scripts/morning_librarian.R` — new script: scans `00_inbox/` for new files, registers in `dropzone_intake` table, generates Claude Code tagging prompt, logs to `agent_runs` as `'librarian'`
- `inst/scripts/fetch_news_feeds.R` — added `log_agent_run(paths, "news-radar", ...)` call alongside existing `log_job`

**5.2–5.3 New skills** — in `metis/.claude/skills/`
- `schedule-morning-agents/skill.md` — guides Claude to register Task Scheduler tasks OR RemoteTriggers; documents 07:00/07:30 setup; covers both Windows and claude.ai paths
- `new-project/skill.md` — scaffolds new Shiny/script/report/tool projects; creates project card in `04_projects/active/[slug].md`; registers in SQLite; returns project card summary
- `add-context/skill.md` — adds specialist context to `08_system/user-config.yaml` without re-running `/metis_config`

**5.4 Morning digest in Control Room**
- `mod_control_room.R` — added `morning_runs` query on `agent_runs` for today's `news-radar` + `librarian` entries; added `agents_chip` showing "News Radar ✓ (12) · Librarian ✓ (3)" in morning brief chips row

**CLAUDE.md**
- Added Phase 5 skills table: `/schedule`, `/new-project`, `/add-context`

### Decisions
- Morning agents use Windows Task Scheduler (via `schtasks.exe`) as primary mechanism, RemoteTrigger as backup
- `morning_librarian.R` does mechanical scanning only; AI tagging is deferred to a Claude Code prompt file
- Skills stored in `metis/.claude/skills/` (project-local), not global `~/.claude/skills/`

---

## Plan snapshot (as of 2026-04-04)

---

## 2026-04-04 — Session 8 (Phase 6: GitHub & Open Source)

**Context:** README and /metis_config wizard. All 6 phases now complete.

### Built

**6.1 README.md** — full GitHub README at metis root (replaces old "Metis Second Brain" placeholder)
- Opening: title, tagline "Your research. Your agents. Your rules.", banner image placeholder, full 3-verse poem + prose sections verbatim from plan
- Red lines section: 5 hard constraints + data classification table
- "What is this?" — cross-pollination engine explanation, MCP server framing
- "Metis becomes yours" — /metis_config + thinking profile
- Workflows: Mermaid flowchart + 11-row workflow table + link to workflows.md
- Data protection: Mermaid classification flow diagram
- "Build your own tools" — Dropzone → scaffold → /new-project flow
- MCP server tools list (25+ tools, categorized)
- Agent team table (21 agents, model assignments)
- Tools & capabilities (data, visualization, documents, images, knowledge)
- Quick start (clone → pip install → /metis_config → launch → connect Claude Desktop)
- Architecture (folder tree + component descriptions)
- Token efficiency table
- Self-improving agents explanation
- "Works with any AI?" (MCP = model-agnostic, agents = Claude-first, dashboard = standalone)
- MIT license note

**6.2 /metis_config wizard** — `.claude/skills/metis-config/skill.md`
- 13 sections: Identity, Projects scan, News Radar interests, Data protection, Cybersecurity, RC structure walkthrough, Meet your team, Librarian config, News Radar interval, Dashboard tour, Launcher, Theme, Active courses
- Opening welcome message; resume-from-section support
- Writes `08_system/user-config.yaml`; seeds SQLite tables (projects, user_topics, course_progress)
- Closing summary + confirm → apply flow
- Edge cases: partial quit, existing config, "I don't know", missing SQLite

**CLAUDE.md** — added `/metis_config` to Phase 5 skills table

### All 6 phases delivered

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation & Cleanup (Metis → Metis rename) | ✅ |
| 2 | Agent Architecture Refactor (skill.md format) | ✅ |
| 3 | MCP Server Updates (25+ tools, 8 new tables) | ✅ |
| 4 | Dashboard Updates (11 sub-phases, 10 tabs) | ✅ |
| 5 | Automation & Scheduling (morning agents, 3 skills) | ✅ |
| 6 | GitHub & Open Source (README, /metis_config) | ✅ |

### Pending (out of scope / deferred)
- WhatsApp webhook — Phase 5 deferred; requires separate FastAPI server + Twilio account
- 6.3 Generic shell cleanup — personal content removal before public release
- Thinking profile tools (Phase 3 deferred item) — depends on user feedback loop being used
- Dashboard shortcut icon — `Metis_github.png` exists at RC root but ICO conversion not done
- Dark theme CSS — stored in user-config.yaml but CSS not yet wired

**Full approved plan:** `/home/sverschaeve/.claude/plans/squishy-dazzling-dragonfly.md`
