# Master Implementation Roadmap

## Purpose

This is the continuation document for the Metis second-brain build. It should let a future session resume the work without reconstructing the project from memory.

## What already exists

### Strategy and ontology

- initial strategy
- execution roadmap
- ontology v1
- literature migration strategy

### Agent layer

- Metis
- Librarian
- Meeting Memory
- PhD Architect
- Writing Partner
- Methods Coach
- Builder
- Dashboard Engineer
- News Radar
- Presentation Maker
- Software Engineer (added 2026-03-27 — R/Python/Shiny code review, bug fix, feature build; distils ruflo memory + security patterns; can escalate to ruflo swarm for large tasks)

### Reference material

- `02_agents/ruflo-reference/` — full clone of ruflo v3.5 (2026-03-27), shallow
- `02_agents/ruflo-reference/ANALYSIS.md` — what to use, what to ignore, when to call ruflo directly

### Literature work

- inventory of the sleeping-sickness literature folder
- duplicate detection
- seeded PhD subset
- PhD article buckets

### Dashboard work

- first modular Shiny app shell
- local SQLite metadata layer
- library scan action
- meeting import action
- transcript workflow
- structured note extraction
- briefing generation
- news page and feed-ingestion script
- project and task storage

## Current implementation state (updated 2026-03-27, redesign pass)

### Agent management — implemented
- `CLAUDE.md` in second brain root — agent router, all 11 agents callable by name
- `triage_inbox.R` — keyword-based routing for 00_inbox/ files, runs every 2h via scheduler
- `schedule_agents.R` — registers Windows Task Scheduler for News Radar, Library, Inbox triage
- Agent calling pattern: type `/agent-name task` in any Claude Code session

### Dashboard — working, no RStudio required
- `launch_monia.bat` — double-click launcher, opens browser at localhost:3838
- `launch_monia_background.vbs` — silent startup launcher for shell:startup auto-start
- `launch.R` — R script called by both launchers
- `check_setup.R` — first-run diagnostic: checks packages, files, git, R version

### Dashboard — comprehensive redesign (2026-03-27) — **v2.0**
- Full CSS rewrite: warm earth-tone palette (#f4f1ea cream / #174c4f teal / #b36a1d rust), compact value boxes (5.5rem instead of 10rem), scroll issue resolved
- **Ideas tab**: complete rewrite — persistent SQLite storage (`ideas` + `idea_links` tables), visNetwork interactive mind map, project hub nodes, cross-pollination amber edges via shared tags, project filter, idea type classification (Research/Method/Collaboration/Learning/Wildcard), graceful fallback
- **Library tab**: visNetwork topic cluster map — bucket nodes sized by article count, click-to-filter (node click populates article list panel), animated progress bars per bucket, graceful fallback
- **Meetings tab**: fixed broken `showcase` string values (AUD/TXT/PREP → proper `icon()` calls), improved layout
- **PhD tab**: animated progress bars per article bucket, thesis document preview with placeholder text, two-column layout
- **News tab**: signal-strength colour-coded brief cards (green=high / amber=medium / grey=low), summary text display, improved capture form
- **Control Room**: compact KPI strip, CSS-grid project boards, styled git status rows, latest brief preview card
- **New dependency**: `visNetwork` — added to `check_setup.R` auto-install; graceful fallback if missing
- History folder created: `07_outputs/apps/metis-dashboard/History/` with CHANGELOG, VERSION_HISTORY, DECISIONS, KNOWN_ISSUES, session log, and version summary

### Dashboard — new features (2026-03-27, between v2.0 and v3.0)
- GitHub status panel in Control Room (green/red dots, commit/push advice, Refresh button)
- Per-project todo boards in Control Room (colour-coded by priority)
- `external_path` and `github_url` columns added to projects table
- `seed_projects.R` — seeds 3 external projects + 10 tasks with correct GitHub URLs

### Dashboard — v3.0 feature build (2026-03-27) — **8 features**
- **Morning Brief** (Control Room): time-aware greeting, overdue/today tasks, inbox count, open task count, latest high-signal news, daily PhD paper pick
- **Kanban Board** (Projects tab): 4-column Kanban view toggle, task cards with red overdue dates, JS single-observer status transitions via `Shiny.setInputValue`
- **Full-text Search** (new Search tab, under "More"): queries all SQLite tables + filesystem markdown; results grouped by type; auto-fires on 3+ chars
- **Global Knowledge Graph** (new Graph tab, under "More"): visNetwork of projects/ideas/article clusters/meetings; toggle checkboxes; graceful fallback
- **Spaced Repetition** (Library tab): SM-2 daily article review widget; client-side reveal; Hard/Good/Easy ratings write to `spaced_repetition` SQLite table
- **Gallery View** (Library tab): CSS grid article cards with bucket badges; capped at 60 for performance
- **Project Completion %** (Control Room): animated CSS progress bars per project board card
- **PhD Milestone Timeline** (PhD tab): CSS horizontal timeline, status-coloured dots, today marker, toggle-add form, `phd_milestones` SQLite table
- New files: `R/mod_search.R`, `R/mod_graph.R`
- New SQLite tables: `spaced_repetition`, `phd_milestones`
- New helpers: `morning_greeting`, `inbox_item_count`, `random_phd_paper`, `project_completion`, `sm2_next_review`, `search_all_sources`
- New data_store functions: `insert_sr_item`, `get_due_sr_items`, `update_sr_review`, `sm2_next_review`, `insert_phd_milestone`, `get_phd_milestones`, `update_task_status`
- `jsonlite` added to `check_setup.R` required packages

### Working now

- modular Shiny app structure exists
- dashboard pages exist (9 tabs: Control Room, Projects, Library, PhD, Meetings, News, Ideas, Search, Graph)
- metadata database schema exists (10 tables: sources, meetings, projects, tasks, news_briefs, literature, ideas, idea_links, spaced_repetition, phd_milestones)
- library scan can rebuild inventory and refresh the database
- meeting import can copy an audio file into the system and create a structured meeting note
- transcript workflow can import transcript files and create structured notes plus briefing notes
- News page can store briefs manually and has a feed-ingestion script
- project and task objects exist in SQLite and appear in the Control Room as kanban board and table view
- Morning Brief renders on every Control Room load (greeting, tasks, inbox, daily paper)
- Full-text search queries all SQLite tables and markdown files on disk
- Global knowledge graph renders all entity types as interactive visNetwork
- Spaced repetition widget surfaces due article reviews in Library tab
- Gallery view shows PhD article cards in Library tab
- Project completion % bars shown on every project board card
- PhD milestone timeline with today marker in PhD tab
- app loads successfully in the current environment
- bundled `imageio-ffmpeg` is installed in the local dashboard virtual environment

### Not implemented yet

- full local Whisper engine installation and successful automatic audio transcription (KI-001)
- verified live-source news ingestion through the dashboard (KI-002)
- Librarian internet retrieval workflow from the dashboard
- Metis recommendation engine
- PhD evidence-map article table with page-level filters (KI-003 — milestone timeline is partial resolution)
- Agent-output pages (Metis, Librarian, Meeting Memory outputs visible in the app)
- File-level open actions from search results and library gallery
- R code review workflows

## Session stop point

Last session (2026-03-27, v3.0 feature build) stopped after:

- Morning Brief added to Control Room
- Kanban Board added to Projects tab (JS single-observer pattern)
- Full-text Search tab created (new mod_search.R)
- Global Knowledge Graph tab created (new mod_graph.R)
- Spaced Repetition widget added to Library tab
- Gallery View added to Library tab
- Project Completion % bars added to Control Room
- PhD Milestone Timeline added to PhD tab
- History folder and roadmap updated

The next session should start with:

1. inspect `07_outputs/apps/metis-dashboard/.venv`
2. decide whether to continue with `openai-whisper` or switch to a lighter CPU-friendly transcription stack (KI-001)
3. verify `inst/scripts/fetch_news_feeds.R` with approved live internet access if needed (KI-002)
4. add PhD evidence-map article table with filters (KI-003, partially addressed by milestone timeline)
5. add agent-output pages showing Metis, Librarian, Meeting Memory outputs
6. add file-level open actions from search results and library gallery

## Key paths

### Dashboard app

- `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/metis-second-brain/07_outputs/apps/metis-dashboard`

### Metadata database

- `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/metis-second-brain/07_outputs/apps/metis-dashboard/data/metis.sqlite`

### Worker scripts

- `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/metis-second-brain/07_outputs/apps/metis-dashboard/inst/scripts`

### Core content roots

- literature metadata:
  `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/metis-second-brain/05_sources/literature/sleeping-sickness/metadata`
- meetings:
  `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/metis-second-brain/05_sources/meetings`
- PhD:
  `/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/metis-second-brain/03_domains/phd`

## Recommended next build order

1. finish local Whisper installation and point the transcription worker to the installed binary (KI-001)
2. test automatic transcription on a real meeting file
3. verify automated news feed ingestion against live sources (KI-002)
4. add PhD evidence-map article table and page-level filters (KI-003 — partial: milestone timeline is done)
5. add an Agents page showing Metis, Librarian, and Meeting Memory outputs
6. add file-level open actions from search results and library gallery cards
7. add saved-state and bookmarked working views

Note: dashboard visual maturity (Phase 5) and core interactive features (Phase 6) are substantially complete as of v3.0. Items above are Phase 3/4 completion (transcription, news) and further capability work.

## Decision log

### Backbone

- use `R Shiny` as the visible dashboard backbone for v1
- keep long-running work outside Shiny in local scripts

### Storage

- keep source documents in the filesystem
- keep indexed metadata in SQLite
- keep Zotero as citation infrastructure, not the whole knowledge model

### Operating model

- local-first by default
- ask permission for general internet use
- Librarian and News Radar can use the internet within scope

## Resumption checklist

When resuming in a future session:

1. inspect the dashboard app folder
2. inspect the local dashboard virtual environment in `.venv`
2. inspect the metadata database schema and current tables
3. inspect the worker scripts in `inst/scripts`
4. run the Shiny app locally
5. decide whether the next priority is meetings, news, PhD, or tasks

## High-value next files to open

- `07_outputs/apps/metis-dashboard/app.R`
- `07_outputs/apps/metis-dashboard/R/data_store.R`
- `07_outputs/apps/metis-dashboard/R/mod_library.R`
- `07_outputs/apps/metis-dashboard/R/mod_meetings.R`
- `07_outputs/apps/metis-dashboard/R/mod_news.R`
- `07_outputs/apps/metis-dashboard/inst/scripts/transcribe_meeting.R`
- `07_outputs/apps/metis-dashboard/inst/scripts/extract_meeting_structure.R`
- `07_outputs/apps/metis-dashboard/inst/scripts/fetch_news_feeds.R`
- `07_outputs/apps/metis-dashboard/IMPLEMENTATION_PLAN.md`
