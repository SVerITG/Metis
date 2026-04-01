# Monia Dashboard — Version History

---

## v7.0 — 2026-03-28

**Theme: Monia as Universal Router**

Monia becomes the single explicit entry point for the entire agent ecosystem. A formal five-step Routing Protocol, a routing table covering all 18 agents, a four-level complexity model, and a Recording Protocol are encoded in her system prompt and contract. CLAUDE.md is rewritten around the `/monia` default — users no longer need to know the agent taxonomy. An `agent_runs` SQLite table and `log_agent_run()` CRUD function make every agent output traceable and surfaceable in the dashboard. Seventeen output directories under `07_outputs/reviews/` organize the agent filesystem. Agent count and module count unchanged.

### Headline changes
- Monia Routing Protocol: analyze → select → assess complexity → announce → execute and record
- Complexity model: quick (haiku) / standard (sonnet) / deep (opus) / chain (opus + subagents)
- Recording mandate: every review, analysis, or search is written to filesystem + DB
- `agent_runs` table + `log_agent_run()` function added to data layer
- 17 output directories pre-created under `07_outputs/reviews/`
- CLAUDE.md: Option A (Monia routes) / Option B (direct call); full workflow diagram
- Monia quick-invoke templates: 6 templates covering the primary daily use cases

### New files
| File | Purpose |
|------|---------|
| 07_outputs/reviews/{17 agent dirs} | Output directories for all agent work products |

### Files changed
| File | Change |
|------|--------|
| 02_agents/metis/system-prompt.md | Full rewrite — Routing Protocol, routing table, complexity model, Recording Protocol |
| 02_agents/metis/contract.md | Rewrite — routing ownership, complexity table, recording mandate |
| CLAUDE.md | Default entry point, Option A/B, workflow diagram, complexity levels table |
| R/mod_agents.R | 6 Monia quick-invoke templates |
| R/data_store.R | `agent_runs` table + `log_agent_run()` |

### Verification
- 14 R modules, unchanged from v6.0
- 18 active agents, unchanged from v6.0
- 23 SQLite tables + 1 new (`agent_runs`) = 24 total

---

## v6.0 — 2026-03-28

**Theme: Agents, News Data, UX Fix, Epidemiologist**

Three new agents expand the ecosystem from 15 to 18. News feed coverage jumps from 3 sources to 17, covering all 8 domains end-to-end. A scrolling bug that silently clipped content on News and Library tabs is fixed. CSS is hardened for accessibility (WCAG AA, reduced-motion, cursor hints) and gains proper mobile breakpoints for the first time.

### Headline changes
- Viewport scroll fix: `fillable = FALSE` in `page_navbar()` — News and Library no longer clip to viewport height
- CSS: accessibility pass + 768px mobile breakpoints (stacked grids, column kanban, 2-col KPI strip)
- Agent: news-aggregator — automated RSS collection; unique internet permission in the security policy
- Agent: ux-engineer — design system specialist; enforces no-emoji-icons and WCAG AA rules
- Agent: epidemiologist — Socratic reviewer with HAT/NTD expertise
- News feeds: 3 -> 17 (all 8 domains covered: sleeping sickness, AI, science, geopolitics, academia, humanitarian, markets, general)
- All integration wiring updated: agent_display_name, agent_slug_map, seed tasks, security policy, CLAUDE.md

### New files
| File | Purpose |
|------|---------|
| 02_agents/news-aggregator/system-prompt.md | RSS aggregator agent — internet-enabled |
| 02_agents/news-aggregator/contract.md | Agent contract |
| 02_agents/news-aggregator/README.md | Agent README |
| 02_agents/ux-engineer/system-prompt.md | UX/design system agent |
| 02_agents/ux-engineer/contract.md | Agent contract |
| 02_agents/ux-engineer/README.md | Agent README |
| 02_agents/epidemiologist/system-prompt.md | Senior epi reviewer agent with Socratic persona |
| 02_agents/epidemiologist/contract.md | Agent contract |
| 02_agents/epidemiologist/README.md | Agent README |

### Files changed
| File | Change |
|------|--------|
| app.R | `fillable = FALSE` added to `page_navbar()` — scrolling fix |
| www/styles.css | `min-height: 100vh`, hover transitions, cursor hints, `prefers-reduced-motion`, mobile breakpoints at 768px |
| R/mod_agents.R | 3 display names added to `agent_display_name()` |
| R/mod_projects.R | 3 slug mappings added to `agent_slug_map()` |
| R/data_store.R | 3 seed tasks added in `seed_default_data()` |
| inst/scripts/fetch_news_feeds.R | 14 new feed URLs added (3 -> 17 total) |
| CLAUDE.md | 3 invocation rows + 3 routing rows added |
| 02_agents/metis/security-policy.md | 3 rows added to per-agent security table |

### Verification
- 14 R modules, no new modules added (scrolling fix was in app.R)
- 18 active agents (was 15 at end of v5.0)
- 17 news feed sources (was 3 at v5.0)

---

## v5.0 — 2026-03-28

**Theme: Intelligence Layer — News Synthesis, Meeting Intelligence, Learning, Finance**

The largest single-session expansion to date. Four modules added or substantially rewritten. The dashboard now actively synthesizes information across seven news domains, tracks competency growth over time, surfaces financial awareness, and generates context-aware meeting briefings. The database grows from 13 to 23 tables. Three new agents (learning-coach, career-coach, personal-finance) expand the ecosystem from 11 to 14 active agents. All 14 R modules pass syntax check with 0 parse errors.

### Headline changes
- News tab: complete rewrite — top signals grid, domain synthesis cards, surprise items, finance sub-section, domain filter chips, full timeline with color coding
- Learning tab: new — 8 seeded competencies, auto-leveling by activity count, activity logger, SR integration, learning paths
- Finance tab: new — short-term headlines, long-term trend arrows, snapshot capture, watchlist, project connections
- Meetings tab: major expansion — pre-meeting briefing generator, meeting intelligence panel (decisions/actions/follow-ups), person directory, attendee tracking, type badges
- 10 new SQLite tables; ALTER TABLE on news_briefs and meetings; 20+ new CRUD functions; 2 new indexes
- ~300 new CSS lines across all four domains

### New files
| File | Purpose |
|------|---------|
| R/mod_learning.R | Learning competency tracker — new tab |
| R/mod_finance.R | Financial awareness — new tab under "More" |
| 02_agents/learning-coach/system-prompt.md | Learning coach agent — skill progression and statistics |
| 02_agents/career-coach/system-prompt.md | Career coach agent — EU job prep and CV support |
| 02_agents/personal-finance/system-prompt.md | Personal finance agent — market awareness |

### Verification
- 14 R modules, 0 parse errors
- 23 SQLite tables
- 14 active agents

---

## v4.1-agent-audit — 2026-03-27

**Theme: Agent Ecosystem Completeness and Security Foundation**

Not a dashboard version release — no R code was changed. This work addressed two system-level gaps that existed after v4.0: (1) uneven agent coverage across the six active projects, and (2) the absence of a formal data security policy.

**Theme: Agent Ecosystem Completeness and Security Foundation**

Not a dashboard version release — no R code was changed. This work addressed two system-level gaps that existed after v4.0: (1) uneven agent coverage across the six active projects, and (2) the absence of a formal data security policy.

### What changed
- **Agent coverage audit**: all 11 agents reviewed against all 6 projects; 7 agent/project gaps identified
- **6 new context documents** written and placed in the correct `02_agents/<slug>/` locations — ensures the [Invoke] modal (introduced in v4.0 via ADR-009) always surfaces useful context for each agent/project pair
- **9 new tasks** added to metis.sqlite — all 11 agents now have at least 1 active task visible in the Kanban view
- **Security policy created** at `02_agents/metis/security-policy.md` — HAT case records formally classified as SENSITIVE; local-first principle and per-agent internet permissions documented; code security rules for SQL, filesystem, external commands, and Shiny UI captured
- **4 agent system prompts updated** (dashboard-engineer, meeting-memory, librarian, news-radar) with targeted security excerpts from the master policy

### What was NOT changed
- No R source files modified
- No SQLite schema changes (only data rows added)
- Software Engineer system prompt left intact (already had comprehensive security checklist)

### Architectural decision recorded
- ADR-012: security policy as a standalone document, not duplicated per agent

### New known issue recorded
- KI-006: security policy excerpts in agent system prompts require manual sync when master policy changes (accepted risk)

---

## v4.0 — 2026-03-27

**Theme: Workflow Integration and Agent Bridge**

Six deliverables completed in one session. The dashboard evolves from a self-contained daily tool into a two-way bridge between the user's projects and the agent ecosystem. Projects can be opened, launched, and handed to agents without leaving the dashboard. Agents have their own dedicated output page. A Strategy view gives a workflow-state overview across all active projects. The Library gains a Courses section for structured learning tracking.

### Headline changes
- Quick-Launch Panel: open, GitHub-link, and launch any project from the Control Room
- Agent Invocation: [Invoke] button on kanban task cards — copies agent command and context document
- Agent Output Page: new Agents tab listing agents, their open tasks, and their latest outputs
- Strategy View: third project view mode — per-project horizontal workflow diagram with bottleneck detection
- Courses Section: education projects with lessons.json, progress bars, SR deck integration
- Agent Context Documents: hat-dashboard-context.md and mlm-course-context.md added to 02_agents/software-engineer/

### New files
| File | Purpose |
|---|---|
| R/mod_agents.R | Agent Output page module — new tab under "More" |
| 02_agents/software-engineer/hat-dashboard-context.md | HAT Dashboard RAG context for Software Engineer agent |
| 02_agents/software-engineer/mlm-course-context.md | MLM Course context for Software Engineer agent |

### Files extended
| File | What was added |
|---|---|
| R/mod_control_room.R | Quick-launch panel card with open/GitHub/launch actions per project |
| R/mod_projects.R | Strategy view toggle; [Invoke] button on kanban cards with agent modal |
| R/mod_library.R | Courses section reading education projects + lessons.json |
| R/data_store.R | `launch_cmd` column; `course_progress` table; `update_task_notes()`, `get_course_progress()`, `mark_lesson_complete()` helpers |
| app.R | mod_agents registered; Agents tab under nav_menu("More") |
| www/styles.css | 20+ new CSS classes across all six deliverables + .btn-xs backfill |

### New SQLite objects
| Object | Type | Purpose |
|---|---|---|
| `projects.launch_cmd` | Column (TEXT) | Stores the shell command to launch each project |
| `course_progress` | Table | Tracks per-lesson completion status and SR deck inclusion |

### Key architectural choices
- Agent context lookup uses a slug-to-filesystem convention: `02_agents/<slug>/<project-context>.md` — see ADR-009
- Strategy view uses a pure `renderUI` HTML approach (no visNetwork) — bottleneck detection is a server-side count check, not a graph algorithm
- Courses section reads `lessons.json` from the project's local path at render time — no pre-import step required
- `.btn-xs` added to `www/styles.css` because Bootstrap 5 removed this utility class that was present in Bootstrap 4 / shinydashboard defaults

### Syntax validation
All R modules confirmed parse-clean via `Rscript --vanilla -e "parse(file='<module>')"` before session close.

---

## v3.0 — 2026-03-27

**Theme: Interactive Daily Work Surface**

Eight features added in a single session. The dashboard advances from a polished read-only tool to an interactive daily work surface. Intelligence layer: morning brief, spaced repetition, full-text search. Planning layer: kanban board, PhD milestone timeline. Exploration layer: global knowledge graph, article gallery. Each feature is independently toggleable and degrades gracefully if optional packages are absent.

### Headline changes
- Morning Brief: time-aware greeting + overdue tasks + inbox count + daily PhD paper pick
- Kanban Board: 4-column drag-style task management with JS status transitions
- Full-text Search: new tab querying all SQLite tables + markdown files on disk
- Global Knowledge Graph: new tab showing projects, ideas, article clusters, meetings as a unified network
- Spaced Repetition: SM-2 daily article review widget in Library tab
- Gallery View: CSS grid article cards with bucket badges in Library tab
- Project Completion %: animated progress bars on every project board card
- PhD Milestone Timeline: CSS horizontal timeline with today marker and status dots

### New dependencies
- `jsonlite` — added to check_setup.R (used by search and graph modules)

### New files
| File | Purpose |
|---|---|
| R/mod_search.R | Full-text search module |
| R/mod_graph.R | Global knowledge graph module |

### Files rewritten
| File | What changed |
|---|---|
| R/mod_control_room.R | Complete rewrite — morning brief + completion bars |
| R/mod_projects.R | Complete rewrite — kanban board |
| R/mod_library.R | Complete rewrite — gallery + SR widget |
| R/mod_phd.R | Complete rewrite — milestone timeline |

### Files extended
| File | What was added |
|---|---|
| R/data_store.R | `spaced_repetition` + `phd_milestones` tables; 6 new helper functions |
| R/helpers.R | 6 new helper functions (morning_greeting, inbox_item_count, random_phd_paper, project_completion, sm2_next_review, search_all_sources) |
| www/styles.css | Morning brief, kanban, gallery, SR widget, timeline, search result, graph legend CSS |
| app.R | Search and Graph tabs under nav_menu("More") |
| check_setup.R | jsonlite added to required packages |

### Key architectural choices
- Nav overflow solved via `nav_menu("More")` dropdown — keeps primary nav readable at 9 total tabs
- Kanban observer pattern: single `observeEvent(input$kanban_move)` with `Shiny.setInputValue` from JS — prevents duplicate observers inside `renderUI` loops
- SR reveal is pure client-side — no server round-trip before showing the answer card

---

## v2.0 — 2026-03-27

**Theme: UI Redesign and Ideas Feature**

Full redesign pass across all six dashboard pages. The dashboard moved from functional placeholder state to a polished, visually consistent tool. The Ideas module was built from scratch as a full feature with persistent storage and an interactive network visualisation.

### Headline changes
- Complete CSS rewrite: warm earth-tone palette, compact value boxes (scrolling fixed)
- Ideas tab: SQLite persistence, visNetwork mind map, cross-pollination edges
- Library tab: visNetwork bucket cluster map, click-to-filter, progress bars
- Meetings tab: icon fix (AUD/TXT/PREP string literals corrected)
- PhD tab: animated bucket progress bars, thesis preview
- News tab: signal-strength colour-coded cards
- Control Room: compact KPI strip, grid project boards, brief preview

### New dependency
- `visNetwork` — interactive network graphs (mind maps, cluster maps)

### Files changed
| File | Change type |
|---|---|
| www/styles.css | Full rewrite |
| R/mod_ideas.R | Full rewrite (stub -> feature) |
| R/mod_library.R | Added cluster map + progress bars |
| R/mod_meetings.R | Bug fix (icons) + layout |
| R/mod_phd.R | Progress bars + thesis preview |
| R/mod_news.R | Signal cards + layout |
| R/mod_control_room.R | Compact KPI + grid boards |
| R/data_store.R | Added ideas/idea_links schema + helpers |
| check_setup.R | Added visNetwork to package list |

---

## v1.0 — 2026-03-26 (baseline)

**Theme: Working Shell**

First deployable version of the Monia Dashboard. All pages existed in scaffold or stub form. The SQLite backend was established and the primary data actions (library scan, meeting import, transcript workflow, news storage) were wired. The app loads from a double-click launcher with no RStudio required.

### Headline changes
- Modular Shiny app (app.R + mod_*.R pattern)
- SQLite metadata layer (metis.sqlite)
- Library scan, meeting import, transcript extraction, briefing generation
- News brief storage and feed-ingestion script
- Project + task objects in database with GitHub URL tracking
- GitHub status panel in Control Room
- Double-click launcher (launch_monia.bat)
- check_setup.R diagnostic

### Known limitations
- Whisper audio transcription pending installation
- News feed ingestion not validated against live sources
- Ideas tab was a 3-button stub
- No visual network maps
