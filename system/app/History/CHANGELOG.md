# Metis Dashboard Changelog

Follows [Keep a Changelog](https://keepachangelog.com) conventions.
Versions track the dashboard app itself, independent of the second-brain system version.

---

## [Unreleased]

---

## [v7.0] — 2026-03-28

Metis promoted to universal router and single default entry point. Routing Protocol, complexity model, and Recording Protocol encoded in her system prompt and contract. Agent run tracking added to the data layer. Seventeen output directories created. CLAUDE.md rewritten around the `/metis` default.

### Added
- **Metis Routing Protocol** (agents/metis/system-prompt.md): 5-step protocol — analyze request, select agent(s), assess complexity, announce plan, execute and record; Metis now announces routing decision before executing
- **Routing table** (agents/metis/system-prompt.md): full input-type to primary/secondary agent mapping; covers all 18 agents with chaining rules
- **Complexity model** (agents/metis/system-prompt.md, CLAUDE.md): four levels — quick (haiku), standard (sonnet), deep (opus), chain (opus + subagents); complexity assessed by Metis, not specified by user
- **Recording Protocol** (agents/metis/system-prompt.md): output file template (`outputs/reviews/{agent-slug}/{YYYY-MM-DD}_{task-slug}.md`), DB logging rules, mandate to never skip recording for reviews/analyses/searches
- **`agent_runs` SQLite table** (R/data_store.R): schema — agent_slug, task_summary, input_path, output_path, status, created_at; one row per agent invocation
- **`log_agent_run()` function** (R/data_store.R): CRUD helper; called by Metis after every substantive run to create the DB record
- **17 output directories** (outputs/reviews/): one subdirectory per agent slug, pre-created and ready to receive output files
- **Metis quick-invoke templates expanded** (R/mod_agents.R): six templates — general request, morning briefing, full paper review chain, triage, weekly review, "what am I overlooking?"

### Changed
- **Metis contract** (agents/metis/contract.md): rewrite — Metis now explicitly owns routing decisions, complexity assessment, and PKM recording; complexity table added; recording mandate ("Never skip recording for reviews, analyses, or searches")
- **CLAUDE.md**: `/metis` documented as default entry point; multi-agent routing example added; complete workflow diagram (Dashboard → Claude Code → Agent → Output → Dashboard); Option A (Metis routes) / Option B (direct call) replaces old invocation section; complexity levels table added

---

## [v6.0] — 2026-03-28

Three new agents created, news feed coverage expanded from 3 to 17 feeds, viewport scrolling bug fixed, CSS hardened for accessibility and mobile, and all integration wiring updated throughout. Agent count advances from 15 to 18.

### Added
- **Agent: news-aggregator** (agents/news-aggregator/): automated RSS feed collection and curation; files: system-prompt.md, contract.md, README.md; security tier: internet access granted (unique among agents)
- **Agent: ux-engineer** (agents/ux-engineer/): design system and UI/UX specialist; hard rules encoded in system prompt: no emoji icons, WCAG AA compliance, responsive breakpoints; files: system-prompt.md, contract.md, README.md
- **Agent: epidemiologist** (agents/epidemiologist/): senior specialist reviewer with Socratic questioning persona; HAT/NTD expertise; files: system-prompt.md, contract.md, README.md
- **News feeds expanded** (inst/scripts/fetch_news_feeds.R): feeds added for all 8 domains — sleeping sickness (WHO NTD, DNDi), AI (Anthropic, MIT Tech Review), science (Nature), geopolitics (Reuters, BBC), academia (The Conversation), humanitarian (ReliefWeb, MSF), markets (CNBC, Bloomberg), general (NPR, The Guardian); total feeds: 3 -> 17
- **Seed tasks for new agents** (R/data_store.R): 3 new seed tasks added to `seed_default_data()` — one per new agent; all 18 agents now have at least 1 active task in the Kanban view
- **CSS: accessibility and mobile** (www/styles.css): `min-height: 100vh` on body, button hover transitions (150ms), `cursor: pointer` on all clickables, `@media (prefers-reduced-motion)` support, mobile breakpoints at 768px (stacked grids, column kanban, 2-col KPI strip)
- **CLAUDE.md invocations**: 3 new invocation rows (`/news-aggregator`, `/ux-engineer`, `/epidemiologist`) and 3 new routing guide rows added

### Changed
- **R/mod_agents.R**: `agent_display_name()` extended with display names for news-aggregator, ux-engineer, epidemiologist
- **R/mod_projects.R**: `agent_slug_map()` extended with slug mappings for the 3 new agents
- **agents/metis/security-policy.md**: 3 new rows added to per-agent security table — News Aggregator (internet access granted), UX Engineer (no internet), Epidemiologist (no internet)

### Fixed
- ⚠️ **Viewport-constrained scrolling on content-heavy tabs** (app.R): `fillable = FALSE` added to `page_navbar()` — News and Library tabs now scroll correctly instead of being clipped to viewport height
  Root cause: `page_navbar()` defaults to `fillable = TRUE`, which constrains all panels to the viewport and suppresses natural document scroll
  Impact: any tab with content taller than the viewport was silently truncating its lower content

---

## [v5.0] — 2026-03-28

Four modules added or substantially rewritten in a single session. The dashboard gains an intelligence layer: multi-domain news synthesis, competency-based learning tracking, financial awareness, and meeting intelligence with context-aware pre-briefing generation. Database grows from 13 to 23 tables. Three new agents join the ecosystem (learning-coach, career-coach, personal-finance). 14 R modules, 0 parse errors.

### Added
- **mod_news.R** (R/mod_news.R): COMPLETE REWRITE — multi-domain daily intelligence briefing
  - Top signals section: high-priority items across all domains in a scannable card grid
  - Domain synthesis grid: 7 domains (geopolitics, science, academia, sleeping sickness, humanitarian, markets, AI) each rendered as a summary card
  - "Surprise me" section: items flagged outside the user's usual domains
  - Finance sub-section: short-term market headlines and long-term trends embedded in News tab
  - Full timeline with domain color coding
  - Collapsible add-brief form with source URL, tags, and surprise flag fields
  - Domain filter chips for single-domain focus mode
- **mod_learning.R** (R/mod_learning.R): NEW — statistics and epidemiology competency tracker
  - 8 seeded competencies: sampling, MLM, spatial stats, outbreak investigation, diagnostic test evaluation, survival analysis, Bayesian analysis, GEE
  - Auto-leveling: activity count drives level (0-4 = beginner, 5-14 = intermediate, 15+ = advanced)
  - Activity logger: type, competency, notes per event (course_lesson, paper_read, exercise, sr_review, tutorial, practice)
  - SR integration: learning-specific items surfaced within the Learning tab
  - Learning path view with linked resources per competency
  - MLM Course project integration
- **mod_finance.R** (R/mod_finance.R): NEW — financial awareness tab
  - Short-term headlines from domain='markets' news briefs
  - Long-term trends grouped by label with directional arrows (up/down/sideways)
  - Snapshot capture form: category, label, headline, trend, project link
  - Watchlist management
  - Project connections panel
- **mod_meetings.R** (R/mod_meetings.R): MAJOR EXPANSION
  - Pre-meeting briefing generator: context from past meetings and linked library articles; path stored in meetings.pre_briefing_path
  - Meeting intelligence panel: structured decisions, action items, follow-ups per meeting
  - Person directory: name, role, affiliation; auto-tracks meeting count and last-meeting date
  - Meeting timeline with type badges (general, project_review, phd_supervision, strategy, seminar, one_on_one)
  - Attendee tracking: comma-separated entry parses into meeting_attendance join records
  - Decision/action badge counts on timeline cards
- **New SQLite tables** (R/data_store.R): news_topics, news_brief_topics, meeting_persons, meeting_attendance, learning_competencies, learning_activities, learning_resources, finance_watchlist, finance_snapshots — total tables: 13 -> 23
- **New CRUD functions** (R/data_store.R, 20+): news_domain_summary, news_by_domain, news_surprise_items, news_top_signals, insert_news_brief_v5, insert_meeting_person, get_meeting_persons, get_meeting_context, update_meeting_intelligence, seed_default_competencies, get_competencies, insert_learning_activity, get_learning_activities, insert_finance_snapshot, get_finance_today, get_finance_trends, insert_finance_watchlist, get_finance_watchlist
- **New indexes** (R/data_store.R): idx_briefs_date, idx_briefs_domain on news_briefs
- **Agent: learning-coach** (agents/learning-coach/): skill progression, learning paths, statistics focus; files: system-prompt.md, contract.md, README.md
- **Agent: career-coach** (agents/career-coach/): EU job prep, CV support, career strategy; files: system-prompt.md, contract.md, README.md
- **Agent: personal-finance** (agents/personal-finance/): market awareness, financial trends; files: system-prompt.md, contract.md, README.md
- **CSS additions** (www/styles.css, ~300 lines): News (.news-header-row, .news-domain-chip, .news-top-signals-grid, .news-signal-card, .news-domain-grid, .news-domain-card, .news-surprise-*, .news-timeline-*, .signal-dot-*, .finance-list), Meetings (.meeting-person-chip, .meeting-timeline-*, .meeting-type-badge, .meeting-badge-*), Learning (.competency-grid, .competency-card, .competency-level-badge, .competency-bar-*, .learning-activity-*, .learning-path-*), Finance (.finance-card, .finance-category-badge, .finance-trend-*, .finance-list-stack)

### Changed
- **R/data_store.R**: ALTER TABLE news_briefs — added source_url TEXT, tags TEXT, surprise_flag INTEGER; ALTER TABLE meetings — added attendees TEXT, meeting_type TEXT, decisions TEXT, action_items TEXT, follow_ups TEXT, linked_meetings TEXT, pre_briefing_path TEXT
- **app.R**: added nav_panel("Learning") to main navigation; added nav_panel("Finance") under "More" dropdown; added learning_server and finance_server calls
- **agents/CLAUDE.md**: three new agent invocations added — /learning-coach, /career-coach, /personal-finance; agent count: 11 -> 14

---

## [v4.1-agent-audit] — 2026-03-27

No R code changed. Agent ecosystem completeness and security foundation work conducted after v4.0 release.

### Added
- **Agent coverage audit** (agents/): all 11 agents audited against all 6 active projects; 7 coverage gaps identified and filled
- **6 new agent context documents** (agents/): hat-dashboard-context.md (dashboard-engineer), hat-clustering-context.md (phd-architect), hat-clustering-context.md (methods-coach), multilevel-analysis-course-context.md (methods-coach), hat-clustering-context.md (writing-partner), multilevel-analysis-course-context.md (presentation-maker) — see ADR-012
- **9 new tasks** in metis.sqlite: task-hatdash-ui-audit, task-hatdash-data-privacy, task-clustering-satscan-params, task-clustering-article-draft, task-mlm-slides, task-mlm-references, task-passive-screening-phd-map, task-builder-mcp-server, task-newsradar-rss-setup; all 11 agents now have ≥1 task
- **Security policy** (agents/metis/security-policy.md): system-wide data protection policy with data classification table (SENSITIVE/CONFIDENTIAL/INTERNAL/PUBLIC), local-first principle, code security rules (SQL, filesystem, external commands, secrets, Shiny UI), privacy rules for research data (HAT case records = SENSITIVE), per-agent security table, and escalation rules; derived from Ruflo v3.5 security module

### Changed
- **agents/dashboard-engineer/system-prompt.md**: Shiny UI security section added
- **agents/meeting-memory/system-prompt.md**: local-first privacy rules added
- **agents/librarian/system-prompt.md**: data sourcing protection rules added
- **agents/news-radar/system-prompt.md**: data hygiene and scope rules added
- Note: agents/software-engineer/system-prompt.md was NOT modified — already has a comprehensive security checklist

---

## [v4.0] — 2026-03-27

Six deliverables implemented in one session. The dashboard gains a two-way bridge to the agent ecosystem: projects can be opened, launched, or handed to an agent directly from within the app. A new Agents tab surfaces all agent context, open tasks, and outputs in one place. A Strategy view gives a workflow-level overview across all projects. The Library tab gains a Courses section for structured learning. All R modules pass syntax check.

### Added
- **Project Quick-Launch Panel** (R/mod_control_room.R): new card at top of Control Room
  - Each project row shows: title, domain badge, git status chip (clean / uncommitted / unpushed)
  - [Open folder] button calls `browseURL()` to the local project path
  - [GitHub] link opens the project's GitHub URL in the browser
  - [Launch app] button opens a modal with the project's launch command (copy-to-clipboard)
  - DB: `launch_cmd TEXT` column added to the `projects` table (R/data_store.R)
- **Agent Invocation from Task Cards** (R/mod_projects.R): kanban cards with an agent owner show an [Invoke] button
  - Click opens a modal with: the agent's project-specific context document, a copy-to-clipboard agent command, and a delegation notes textarea
  - Agent context lookup: `agents/<slug>/<project-context>.md` with fallback to `README.md`
  - New helper `update_task_notes(paths, task_id, notes)` added to R/data_store.R
- **Agent Output Page** (R/mod_agents.R): NEW module, registered as "Agents" tab under `nav_menu("More")`
  - Left sidebar: lists all agents discovered from the `agents/` filesystem
  - Main panel: open tasks assigned to that agent, latest output files from `outputs/reviews/<agent>/`, triage log mentions, agent documents
- **Strategy View** (R/mod_projects.R): third toggle mode alongside Kanban and Table
  - Per-project horizontal workflow diagram: Defined → Open tasks → Agent assigned → In progress → Done
  - Bottleneck detection: projects with >3 tasks `in_progress` surface an amber warning chip
  - Implemented as `strategy_view_ui()` standalone function in mod_projects.R
- **Courses Section** (R/mod_library.R): education projects surfaced inside the Library tab
  - Reads projects with `domain = 'education'` from the database
  - Loads `lessons.json` from the project path (graceful fallback if absent)
  - Per-lesson: progress bar, "Mark complete" button, "Add to SR deck" button
  - New SQLite table: `course_progress`
  - New helpers: `get_course_progress()`, `mark_lesson_complete()` in R/data_store.R
- **Agent Context Documents** (agents/): two new project-specific context files
  - `agents/software-engineer/hat-dashboard-context.md` — HAT Dashboard RAG context (branch `server`, 14 modified files)
  - `agents/software-engineer/mlm-course-context.md` — MLM Course Node.js app, Quarto files, spatial scan module

### Changed
- **R/mod_control_room.R**: extended — quick-launch panel added at top of existing Control Room layout
- **R/mod_projects.R**: extended — Strategy view toggle and [Invoke] button added to Kanban cards
- **R/mod_library.R**: extended — Courses section added alongside existing Library content
- **R/data_store.R**: extended — `launch_cmd` column, `course_progress` table, `update_task_notes()`, `get_course_progress()`, `mark_lesson_complete()` helpers
- **app.R**: `mod_agents` registered and Agents tab added under `nav_menu("More")`
- **www/styles.css**: CSS additions for all six deliverables
  - Quick-launch panel: `.launch-panel`, `.launch-row`, `.launch-git-chip` variants, `.domain-badge`, `.launch-cmd-block`
  - Agent invocation: `.invoke-cmd-row`, `.invoke-cmd-text`, `.task-invoke-btn`
  - Strategy view: `.strategy-board`, `.strategy-row`, `.strategy-flow`, `.strategy-stage` (+ `.active`, `.warn`), `.strategy-bottleneck-chip`, `.strategy-arrow`
  - Agent output page: `.agent-list-item`, `.agent-task-badge`
  - Courses: `.courses-grid`, `.course-card`, `.course-lesson-row`
  - Utility: `.btn-xs` (Bootstrap 5 missing class backfill)

---

## [v3.0] — 2026-03-27

Eight new features added across five modules. Dashboard moves from a polished read-only tool to an interactive daily work surface with intelligence (morning brief, spaced repetition, search), planning (kanban, milestones), and exploration (knowledge graph, gallery) layers.

### Added
- **Morning Brief** (R/mod_control_room.R): auto-generated section at top of Control Room on every load
  - Time-aware greeting (`morning_greeting()` in helpers.R)
  - Shows: overdue tasks, today's tasks, inbox item count, open task count
  - Latest high-signal news snippet
  - "Today's paper": consistent daily random PhD article pick (`random_phd_paper()` in helpers.R)
  - Inbox item counter (`inbox_item_count()` in helpers.R)
- **Kanban Board** (R/mod_projects.R): toggle between Kanban and Table views
  - 4 columns: Open, In Progress, Blocked, Done
  - Task cards show project, owner, due date (overdue dates in red)
  - Status transitions via `Shiny.setInputValue` JS pattern
  - Single `observeEvent` handles all card moves — avoids duplicate observer problem
  - `update_task_status()` helper in data_store.R
  - `kanban_ui_output()` standalone function for clean separation
- **Full-text Search** (R/mod_search.R): NEW file — new Search tab under "More" nav menu
  - Queries all SQLite tables: tasks, projects, news_briefs, ideas, meetings
  - Filesystem search across phd_root and meetings_root markdown files
  - Results grouped by type with icons and snippets
  - Triggered by button or auto-fires after 3+ characters typed
  - `search_all_sources()` in helpers.R
- **Global Knowledge Graph** (R/mod_graph.R): NEW file — new Graph tab under "More" nav menu
  - visNetwork showing: projects (box/teal), ideas (ellipse/amber), article clusters (dot/green), meetings (diamond/blue)
  - Toggle checkboxes: article clusters, meetings, cross-tag idea links
  - Edges: project->idea (project_id FK), project->meeting (title match), idea<->idea (shared tags, dashed amber)
  - Graceful fallback if visNetwork not installed
- **Spaced Repetition** (R/mod_library.R): SM-2 simplified daily article review widget
  - New `spaced_repetition` SQLite table (data_store.R)
  - "Daily article review" card surfaced at top of Library tab
  - Two-step interaction: prompt shown -> client-side Reveal (no server round-trip) -> Hard/Good/Easy rating buttons
  - Rating updates `next_review` and `interval_days`: Hard=max(1,cur), Good=max(2,cur*1.5), Easy=max(4,cur*2)
  - Seed button to populate deck from seeded articles
  - Functions: `insert_sr_item()`, `get_due_sr_items()`, `update_sr_review()`, `sm2_next_review()` in data_store.R
- **Gallery View** (R/mod_library.R): toggle between Gallery (new) and Table views for PhD-seeded articles
  - CSS grid cards showing: bucket badge (colour-coded), filename, surveillance mode, relevance note
  - Capped at 60 cards for performance; shows count if more exist
- **Project Completion %** (R/mod_control_room.R): each project board card now shows progress
  - Done/total task count and animated % progress bar (CSS transition: width 0.4s)
  - `project_completion(paths)` helper in helpers.R
- **PhD Milestone Timeline** (R/mod_phd.R): new milestone tracking feature
  - New `phd_milestones` SQLite table (data_store.R)
  - Toggle-form to add milestones: article title, target date, status, notes
  - CSS horizontal timeline rendered in `renderUI` with absolute positioning
  - Today marker (amber vertical line)
  - Status-coloured dots: planned / in_progress / submitted / in_revision / accepted / published
  - Functions: `insert_phd_milestone()`, `get_phd_milestones()` in data_store.R
- **app.R**: Search and Graph tabs added under `nav_menu("More")` dropdown
- **check_setup.R**: `jsonlite` added to required packages list

### Changed
- **mod_control_room.R**: complete rewrite to integrate morning brief and project completion bars
- **mod_projects.R**: complete rewrite to add kanban board alongside existing table view
- **mod_library.R**: complete rewrite to add gallery view and spaced repetition widget
- **mod_phd.R**: complete rewrite to add milestone timeline
- **www/styles.css**: added CSS classes for morning brief panel, kanban columns and cards, gallery grid, SR widget, milestone timeline, search result groups, graph legend

### Architectural decisions
- Search and Graph placed under `nav_menu("More")` dropdown — avoids navbar overflow at 9 tabs (see ADR-006)
- Kanban status transitions use single shared `observeEvent` on `input$kanban_move` via `Shiny.setInputValue` — avoids duplicate observer registration that occurs when per-card observers are created inside `renderUI` loops (see ADR-007)
- SR reveal step is client-side only — no server round-trip required before showing the answer

---

## [v2.0] — 2026-03-27

Comprehensive UI redesign pass. All six pages rebuilt from placeholder/stub state to fully featured views. New Ideas feature implemented end-to-end. visNetwork dependency added.

### Added
- **Ideas module** (R/mod_ideas.R): full rewrite from 3-button stub to complete feature
  - Persistent idea capture stored in SQLite (`ideas` table, `idea_links` table)
  - visNetwork interactive mind map: project hub nodes + idea child nodes
  - Cross-pollination edges: amber connections between ideas from different projects that share tags
  - Project filter dropdown and idea type classification (Research / Method / Collaboration / Learning / Wildcard)
  - Graceful fallback message if visNetwork is not installed
- **Library module** (R/mod_library.R): visNetwork topic cluster map
  - PhD article bucket nodes sized by article count
  - Click-to-filter: selecting a bucket node filters the article list in the side panel
  - Animated progress bars showing bucket coverage percentage
  - Graceful fallback for missing visNetwork
- **data_store.R**: `ideas` and `idea_links` tables added to schema
  - `insert_idea()` helper
  - `get_ideas()` helper
  - `get_idea_links()` helper
- **check_setup.R**: `visNetwork` added to required packages list with auto-install on first run
- CSS: signal-strength badges, priority badges, project board grid layout, network container, status classes

### Changed
- **CSS** (www/styles.css): full redesign — warm earth-tone palette (#f4f1ea cream / #174c4f teal / #b36a1d rust); compact value boxes reduced from ~10rem to 5.5rem height, fixing the main page-scroll issue
- **Meetings module** (R/mod_meetings.R): fixed broken `showcase` string literals — "AUD", "TXT", "PREP" replaced with proper `icon()` calls; improved layout with clear action rows and informational Whisper note
- **PhD module** (R/mod_phd.R): replaced plain article table with animated progress bars per bucket; added thesis document preview with placeholder guidance text; improved two-column layout
- **News module** (R/mod_news.R): replaced plain table with colour-coded brief cards (green = high signal, amber = medium, grey = low); shows summary text inline; improved capture form layout
- **Control Room** (R/mod_control_room.R): compact KPI strip, CSS-grid project boards, styled git status rows, latest brief preview card

### Fixed
- 🐛 Value boxes too tall — caused persistent vertical scroll on every page — Root cause: default shinydashboard box height — Fixed by constraining `.small-box` to 5.5rem in CSS
- 🐛 Meeting tab `showcase` values showing raw strings "AUD"/"TXT"/"PREP" instead of icons — Root cause: incorrect string literals passed where `icon()` calls were expected — Fixed in mod_meetings.R

---

## [v1.0] — 2026-03-26 (baseline)

First working shell of the Metis Dashboard. All pages scaffolded, SQLite backend established, library scan and meeting import wired, news briefs stored, projects and tasks in database.

### Added
- Modular Shiny app structure (app.R + R/mod_*.R pattern)
- SQLite metadata layer (data/metis.sqlite) with tables: sources, meetings, projects, tasks, news_briefs, literature
- Control Room page: live counts, project board, git status panel
- Library page: article inventory from filesystem scan
- PhD page: article buckets, focus list
- Meetings page: audio import, transcript workflow, structured note extraction, briefing generation
- News page: manual brief storage, feed-ingestion script (inst/scripts/fetch_news_feeds.R)
- Ideas page: stub with 3 action buttons (later rewritten in v2.0)
- Worker scripts: scan_library.R, import_meeting.R, transcribe_meeting.R, extract_meeting_structure.R, fetch_news_feeds.R
- Launcher: launch_metis.bat (double-click) and launch_metis_background.vbs (silent startup)
- check_setup.R: first-run diagnostic for packages, files, git, R version
- External project tracking: `external_path` and `github_url` columns in projects table
- seed_projects.R: seeds 3 external projects + 10 tasks with GitHub URLs
- GitHub status panel in Control Room (green/red indicators, commit/push advice, Refresh button)

### Known limitations at v1.0
- Local Whisper installation incomplete — automatic audio transcription pending
- News feed ingestion script not yet validated against live sources
- Ideas tab was a stub only
- visNetwork not yet a dependency
