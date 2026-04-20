# Architecture Decision Records — Metis Dashboard

---

## ADR-001: R Shiny as UI backbone — 2026-03-26
**Status**: Accepted

**Context**: Needed a local-first command-center UI. Considered pure HTML/JS, Python Dash, and R Shiny.

**Decision**: Use R Shiny for v1.

**Rationale**: Owner is an R user with no JS background. Shiny gives modular UI, reactive state, and direct access to the R analysis stack without requiring a separate language context switch. Deployment is local only — no server cost or authentication overhead.

**Consequences**: Long-running background jobs must live outside the reactive layer (in worker scripts) and be triggered from the app, not run inside it. Shiny's reactive model is not suited to multi-minute jobs.

**Alternatives considered**: Python Dash (would require Python-only stack), plain HTML+JS (no R integration without a separate API layer).

---

## ADR-002: SQLite for metadata storage — 2026-03-26
**Status**: Accepted

**Context**: Source documents stay in the filesystem. Needed an indexed metadata layer for search, filtering, and counts without reading entire folder trees on every page load.

**Decision**: Use SQLite via the `DBI` + `RSQLite` R packages. Single file at `data/metis.sqlite`.

**Rationale**: Zero-install, file-portable, works offline, queryable from R with standard SQL. Sufficient for one-user local load. DuckDB was considered but adds complexity for no gain at this scale.

**Consequences**: Database schema must be maintained in `data_store.R`. Schema migrations are manual (add columns, add tables). No concurrent write safety — acceptable for a single-user local app.

**Alternatives considered**: DuckDB (more powerful analytics, but heavier), flat CSV/RDS files (no query capability), PostgreSQL (requires a running server).

---

## ADR-003: visNetwork for mind maps and cluster maps — 2026-03-27
**Status**: Accepted

**Context**: Phase 5 visual maturity required interactive network views. The Ideas tab needed a mind map. The Library tab needed a cluster map for PhD buckets. Plain tables were insufficient.

**Decision**: Use `visNetwork` as the R binding for vis.js network graphs.

**Rationale**: `visNetwork` integrates natively with Shiny via `visNetworkOutput` / `renderVisNetwork`. It supports click events (used for click-to-filter in Library), node sizing, edge styling, and physics layout. All rendering runs in the browser — no server-side graph computation needed.

**Consequences**: `visNetwork` added as a required package in `check_setup.R`. All visNetwork UI must include a graceful fallback in case the package is absent (implemented as an `if (requireNamespace(...))` guard in both mod_ideas.R and mod_library.R).

**Alternatives considered**: `networkD3` (less Shiny integration), `igraph` (server-side only, no browser interactivity), `ggraph` (static plots).

---

## ADR-004: Warm earth-tone colour palette — 2026-03-27
**Status**: Accepted

**Context**: Default shinydashboard styling (dark blue/green) felt clinical and high-contrast for a personal daily-use tool. Long reading sessions on dark sidebars caused visual fatigue.

**Decision**: Adopt a warm earth-tone palette: cream (#f4f1ea background), teal (#174c4f header/accent), rust (#b36a1d highlights).

**Rationale**: Warm neutrals reduce contrast fatigue for long daily sessions. Cream background is easier on the eyes than white. Teal provides enough contrast for headers without being harsh. Rust provides a warm accent for interactive elements and badges without competing with semantic colours (green/amber/red used for signal strength and status).

**Consequences**: All semantic status colours (green = high signal, amber = medium, red = low/alert) must be used consistently and never overridden by the base palette.

**Alternatives considered**: Dark mode (rejected — owner prefers light for reading), standard shinydashboard blue (rejected — too clinical).

---

## ADR-006: Search and Graph placed under nav_menu("More") dropdown — 2026-03-27
**Status**: Accepted

**Context**: v3.0 added two new top-level tabs (Search, Graph). The primary navbar already had seven tabs (Control Room, Projects, Library, PhD, Meetings, News, Ideas). Adding two more would cause the navbar to overflow or wrap on standard laptop screen widths.

**Decision**: Group Search and Graph inside a `nav_menu("More")` dropdown as the eighth navbar item.

**Rationale**: These two features are accessed on-demand rather than as part of the daily loop. Hiding them under "More" keeps the primary navigation clean without removing the features. bslib/shinydashboard nav menus render as standard Bootstrap dropdowns — no additional dependencies.

**Consequences**: Users must discover Search and Graph via the "More" menu. This is acceptable since both are exploratory/utility features, not primary daily-use tabs.

**Alternatives considered**: Adding both tabs directly (rejected — navbar overflow at 9 tabs), combining Search and Graph into a single tab (rejected — different purposes, confusing to combine).

---

## ADR-007: Single shared observeEvent for kanban status transitions — 2026-03-27
**Status**: Accepted

**Context**: The kanban board renders task cards dynamically inside `renderUI`. Each card has a status-change button. The naive approach (one `observeEvent` per card button, registered inside `renderUI`) creates duplicate observers every time the UI re-renders, causing each click to fire multiple times.

**Decision**: All card move buttons call `Shiny.setInputValue("kanban_move", {task_id, new_status}, {priority: "event"})` from JavaScript. A single `observeEvent(input$kanban_move, ...)` on the server handles all transitions.

**Rationale**: `Shiny.setInputValue` with `priority: "event"` fires even if the value does not change, which is necessary when the same task is moved again. A single server-side observer registered once at startup is never duplicated regardless of how many times the UI re-renders.

**Consequences**: All kanban interaction logic must go through the single `kanban_move` input. Additional per-card actions (e.g., edit, delete) would need their own shared input following the same pattern.

**Alternatives considered**: Per-card observers inside renderUI (rejected — duplicate firing), `shinyjs::onclick` (adds dependency, same duplication problem), full drag-and-drop library (overkill for current scope).

---

## ADR-008: Spaced repetition reveal is client-side only — 2026-03-27
**Status**: Accepted

**Context**: The SR widget shows a prompt (article question), then reveals the answer when the user clicks "Reveal". A server round-trip to toggle visibility would introduce noticeable latency on every reveal action.

**Decision**: The reveal step toggles a CSS class (`sr-hidden` -> visible) via a small inline JavaScript call. No server communication occurs until the user clicks a rating button (Hard/Good/Easy).

**Rationale**: The answer text is already present in the rendered HTML — hiding it is a presentation concern, not a data concern. Client-side toggle is instant and requires no additional server load. The rating buttons are the only action that needs to write back to SQLite.

**Consequences**: The full answer HTML is technically present in the page source even before reveal. This is acceptable for a single-user local app — there is no privacy concern.

**Alternatives considered**: Server-side `shinyjs::toggle` (adds dependency, one round-trip), `conditionalPanel` on a reactive value (requires server state update on reveal, slower).

---

## ADR-009: Agent context lookup via filesystem slug convention — 2026-03-27
**Status**: Accepted

**Context**: The [Invoke] button on kanban task cards needs to surface the correct agent context document for the project being delegated. Each agent may manage multiple projects, each with its own context file. A lookup mechanism was needed that did not require any database schema for agent-to-project mapping.

**Decision**: Resolve context documents via the path `02_agents/<agent-slug>/<project-slug>-context.md`, with a fallback to `02_agents/<agent-slug>/README.md` if no project-specific file exists.

**Rationale**: The `02_agents/` directory is already the canonical location for all agent files. Keeping context documents there (rather than in the project folder or in the database) means agents own their own context. The slug-based naming convention requires no registry — any file matching the pattern is automatically discoverable. The fallback to README.md ensures the Invoke modal always shows something useful even when a project-specific context file has not yet been written.

**Consequences**: When a new project is added and assigned to an agent, a corresponding context file should be created in `02_agents/<agent-slug>/`. The Invoke modal will silently fall back to README.md if it is missing — no error, but possibly less useful context.

**Alternatives considered**: Database table mapping agents to project context file paths (more explicit, but adds schema churn for every new project), flat agent README with all projects concatenated (unmanageable as project count grows).

---

## ADR-010: Strategy view uses renderUI HTML, not visNetwork — 2026-03-27
**Status**: Accepted

**Context**: The Strategy view shows a per-project horizontal workflow diagram (Defined → Open tasks → Agent assigned → In progress → Done). The question was whether to use visNetwork (already a dependency) or a CSS/HTML layout.

**Decision**: Implement the Strategy view as a pure `renderUI` output generating styled HTML `<div>` elements. No graph library used.

**Rationale**: The workflow diagram is a linear sequence of stages, not a general graph. visNetwork is designed for arbitrary node-edge graphs and adds physics layout overhead that would make a simple left-to-right pipeline feel disproportionately heavy. HTML/CSS renders instantly, is fully controllable for layout, and needs no additional JS event wiring. The bottleneck detection logic (count tasks `in_progress` > 3) is a simple server-side check — it does not benefit from graph computation.

**Consequences**: The Strategy view is static — no drag-and-drop or interactive node manipulation. This is intentional: the view is read-only (overview), while Kanban is the interactive task management surface.

**Alternatives considered**: visNetwork (overkill for a linear pipeline), `DiagrammeR` / Mermaid (external dependency, more complex integration for a simple use case).

---

## ADR-011: Courses section reads lessons.json at render time — 2026-03-27
**Status**: Accepted

**Context**: The Courses section in the Library tab needed to load lesson structure (title, description, order) for each education project. Options were to store lesson metadata in SQLite or to read it from a JSON file in the project directory.

**Decision**: Read `lessons.json` from the project's local path at the time the Library tab renders. Store only completion state and SR membership in the `course_progress` SQLite table.

**Rationale**: Lesson structure (the course syllabus) belongs to the course, not to the dashboard. Keeping it in a `lessons.json` file alongside the course materials means the course can be updated without a database migration. The dashboard's job is to track progress, not to duplicate the course definition. Graceful fallback (showing the course card without lesson detail) ensures the app does not crash if `lessons.json` is absent.

**Consequences**: The `lessons.json` format must be documented and followed by any course added to the system. Changes to course structure (adding/removing lessons) are reflected immediately on next render without any dashboard changes. Completion records in `course_progress` reference lessons by a stable lesson ID from the JSON — if lesson IDs change, progress records become orphaned.

**Alternatives considered**: Store lesson metadata in SQLite via an import script (adds an import step, duplicates the course definition), hard-code lesson lists per project in the module (unmaintainable).

---

## ADR-012: Security policy as a standalone document, not duplicated per agent — 2026-03-27
**Status**: Accepted

**Context**: The agent ecosystem handles data of varying sensitivity, including HAT case records (which are patient-level research data). As the number of agents grew to 11, there was a risk that security rules would either be absent from agent system prompts or defined inconsistently across them. A decision was needed about where to locate the authoritative security policy.

**Decision**: Maintain one master security policy at `02_agents/metis/security-policy.md`. Individual agent system prompts receive only the section of the policy that is relevant to their specific surface (e.g., Shiny UI rules for Dashboard Engineer, local-first privacy rules for Meeting Memory). All system prompts reference the master document for the full policy.

**Rationale**: A single source of truth prevents divergence as agents are updated. Targeted excerpts keep each agent's system prompt focused and readable. The Software Engineer agent already had a comprehensive security checklist and was not modified, confirming the excerpt model works in practice. HAT case records are classified as SENSITIVE (highest tier) in the data classification table, which requires an explicit, documented policy rather than informal per-agent rules.

**Consequences**: When the master policy is updated, relevant agent system prompts must be reviewed and their excerpts updated manually. This is a maintenance trade-off accepted in favour of coherence. Any new agent must be assigned a security tier in the per-agent security table at the time of creation.

**Alternatives considered**: Embed the full policy in every agent system prompt (rejected — maintenance burden, high divergence risk over time); no formal policy document (rejected — HAT case records require explicit classification and escalation rules); per-agent policy files with no shared master (rejected — no single point for cross-agent consistency checks).

---

## ADR-013: Auto-leveling competencies by activity count — 2026-03-28
**Status**: Accepted

**Context**: The Learning module needs a mechanism for advancing a user through beginner / intermediate / advanced competency levels. Options were manual level assignment (user explicitly promotes themselves), external assessment, or automatic threshold-based leveling.

**Decision**: Level is derived automatically from the cumulative activity count stored in `learning_competencies`. Thresholds: 0-4 activities = beginner, 5-14 = intermediate, 15+ = advanced. No manual override at launch.

**Rationale**: Manual level assignment requires a conscious judgment at every session, which adds friction and is likely to be neglected. Threshold-based auto-leveling rewards activity logging and gives the user a visible progression signal without any extra action. Thresholds are stored in the CRUD layer (`seed_default_competencies`) and can be tuned per competency in a future pass.

**Consequences**: The level displayed is a function of quantity of logged activities, not quality. A user who logs many low-effort activities will advance faster than intended. Acceptable at this stage — quality signals (SR ratings, exercise outcomes) can be incorporated in a later version.

**Alternatives considered**: Manual level selector (rejected — high friction, likely to be neglected); external quiz/assessment integration (overkill for current scope); activity-type weighting (exercise counts double, paper_read counts once — more precise but adds complexity before the feature has been used in practice).

---

## ADR-014: Normalized person directory alongside legacy free-text attendees — 2026-03-28
**Status**: Accepted

**Context**: The meetings table had a free-text `attendees` column (legacy). v5.0 adds a person directory (meeting_persons) with a join table (meeting_attendance) to enable per-person analytics (meeting count, last-meeting date). The question was whether to migrate the legacy column or run both in parallel.

**Decision**: Retain the legacy `attendees TEXT` column for backward compatibility and quick-entry. Add the normalized `meeting_persons` and `meeting_attendance` tables alongside it. New attendee entries parse the comma-separated string into individual person records in the join table. Existing meeting rows are unaffected — they retain free-text attendees with no corresponding join records.

**Rationale**: A migration of historical free-text attendees to normalized records would require name disambiguation logic that is error-prone (spelling variants, partial names). The analytical value of the person directory starts from new meetings going forward. The free-text column remains useful as a quick-entry field and as a human-readable summary alongside the normalized records.

**Consequences**: The person directory is not retroactively populated. Meeting count and last-meeting date are accurate only from the point when normalized attendance records begin. Any reporting that joins meeting_attendance must acknowledge this limitation.

**Alternatives considered**: Migrate all historical free-text attendees (rejected — name disambiguation risk), drop the free-text column entirely (rejected — backward compatibility break with no corresponding gain for old records), full replacement with JSON in a single column (rejected — harder to aggregate in SQL).

---

## ADR-015: Finance tab placed under "More" nav menu — 2026-03-28
**Status**: Accepted

**Context**: v5.0 adds a Finance tab as a new top-level feature. The primary navigation already holds 7 tabs (Control Room, Projects, Library, PhD, Meetings, News, Ideas). Adding Finance as an 8th primary tab would push the navbar past the safe width on standard laptop screens. The "More" dropdown already holds Search, Graph, and Agents (added in v3.0 and v4.0).

**Decision**: Register Finance as a `nav_panel` under `nav_menu("More")` alongside Search, Graph, and Agents.

**Rationale**: Finance is an on-demand reference view, not part of the daily loop (unlike Control Room, News, or Projects). Hiding it under "More" keeps the primary navigation clean. This follows the established principle from ADR-006 (Search and Graph) — features accessed periodically belong in the overflow menu, not the primary bar.

**Consequences**: Finance is one click deeper than primary tabs. Users must discover it via the "More" menu, which is acceptable given its episodic use pattern. If Finance becomes a daily touchpoint in practice, it should be promoted to the primary nav at a future version.

**Alternatives considered**: Primary nav tab (rejected — navbar overflow at 8 primary items), combining Finance content into the News tab (rejected — different interaction model; News is time-driven briefings, Finance is trend snapshots that persist across days).

---

## ADR-016: page_navbar fillable = FALSE for scrollable content tabs — 2026-03-28
**Status**: Accepted

**Context**: The News and Library tabs contain content grids that substantially exceed the viewport height. After v5.0, users reported that lower content on these tabs was not reachable — the page did not scroll. The root cause was that `bslib::page_navbar()` defaults to `fillable = TRUE`, which constrains each panel to fill the viewport without overflow.

**Decision**: Set `fillable = FALSE` on the top-level `page_navbar()` call in `app.R`.

**Rationale**: `fillable = TRUE` is designed for dashboards where every panel should fit on screen without scrolling (e.g., control rooms with fixed-height cards). The Metis dashboard has a mix of panel types — some short (Control Room KPI strip), some long (News timeline, Library article grid). `fillable = FALSE` lets each panel determine its own height and scroll naturally. This is the correct default for a content-heavy personal dashboard.

**Consequences**: All panels now scroll as standard document pages. Any panel that previously relied on fillable behaviour for a specific layout purpose (e.g., a full-height side-by-side split) must add its own height constraints explicitly. The visNetwork graph in mod_graph.R already had an explicit `height = "600px"` on `visNetworkOutput()` — this continues to work correctly.

**Alternatives considered**: Per-panel `fillable = FALSE` overrides (fragile — every new tab must remember to set it), keeping `fillable = TRUE` and adding `overflow-y: auto` in CSS per tab (workaround, not a fix — some content was still inaccessible).

---

## ADR-017: News Aggregator granted unique internet access permission — 2026-03-28
**Status**: Accepted

**Context**: The default security policy (ADR-012) assigns all agents a local-first permission model with no external internet access by default. The news-aggregator agent is purpose-built for RSS feed collection — its core function requires internet access. This created a policy exception that needed to be explicitly documented.

**Decision**: Grant the news-aggregator agent internet access in the per-agent security table of `02_agents/metis/security-policy.md`. All other v6.0 agents (ux-engineer, epidemiologist) retain the default no-internet permission.

**Rationale**: The news-aggregator's value is entirely derived from external sources. Requiring manual content handoff would undermine its purpose. The agent's scope is bounded: it reads public RSS feeds and returns structured summaries — it does not write to external systems, handle patient data, or access credentials. This is a narrow, audited exception consistent with the News Radar agent's existing scope.

**Consequences**: The news-aggregator must be treated as an internet-connected surface. Any expansion of its capabilities (e.g., API calls, authenticated feeds) must be re-reviewed against the security policy. The per-agent table is the single record of this exception — any future security audit starts there.

**Alternatives considered**: Manual feed download and paste to the agent (defeats automation purpose), local RSS caching script with no agent internet access (separates the concerns but adds a new worker script with no agent intelligence), granting all agents internet access (rejected — unnecessary risk for agents handling sensitive HAT/NTD data).

---

## ADR-018: Metis as single default entry point for all agent requests — 2026-03-28
**Status**: Accepted

**Context**: The agent ecosystem grew to 18 agents across diverse domains (epidemiology, software, library, finance, meetings, news, learning, career). Using any agent required the user to know the correct invocation slug. This was a cognitive barrier that slowed delegation and meant agents were only invoked when the user already had a formed mental model of the work — reducing opportunistic use.

**Decision**: Designate `/metis` as the documented default entry point for all requests. Metis analyzes any input, selects the appropriate agent(s), assesses complexity, announces the routing decision, executes the work, and records the output. Direct agent calls remain valid for users who know what they want.

**Rationale**: Reducing the entry barrier to delegation increases the frequency of agent use. A single entry point is easier to form a habit around than 18 separate invocations. Metis's routing table encodes the agent taxonomy once, so the user does not need to maintain it mentally. The routing announcement ("Routing to [Agent]. Complexity: [level].") provides transparency and lets the user correct routing before work is done.

**Consequences**: Metis bears the full weight of routing quality — if her routing table is wrong or incomplete, users will be mis-routed without knowing it. The routing table in her system prompt must be kept up to date as new agents are added. Direct calls are still supported as an escape hatch for expert users.

**Alternatives considered**: Keeping direct calls as the only interface (rejected — required maintaining a mental model of 18 agents); a routing UI inside the dashboard (rejected — adds a click layer before any real work begins); auto-routing based on NLP classification without announcement (rejected — no transparency, no user correction opportunity).

---

## ADR-019: Filesystem + database dual recording for all substantive agent outputs — 2026-03-28
**Status**: Accepted

**Context**: Agent work was ephemeral — it lived in a conversation window and was lost when the session ended. There was no way to search past agent outputs, no audit trail, and no connection between agent work and the dashboard's Agents tab.

**Decision**: Every substantive agent output is written to two places: (1) a markdown file in `07_outputs/reviews/{agent-slug}/{YYYY-MM-DD}_{task-slug}.md`, and (2) a row in the `agent_runs` SQLite table via `log_agent_run()`. Quick factual questions and status checks are exempt from recording (DB log only for those).

**Rationale**: The file provides the full content — searchable, readable, and diffable. The database record provides structured metadata (agent, task summary, input path, output path, status, timestamp) that the dashboard can query and display. The dual approach means outputs are surfaceable both from the filesystem and from the Agents tab without any schema gymnastics. Pre-creating all 17 output directories removes a potential runtime error and signals the expected structure.

**Consequences**: Metis must remember to call `log_agent_run()` after every substantive run — there is no automatic hook enforcing this. The recording mandate in her system prompt and contract is the enforcement mechanism. Any agent output file that exists in `07_outputs/reviews/` without a corresponding `agent_runs` row represents a recording gap.

**Alternatives considered**: Database-only recording (rejected — loses full output content; Agents tab would need to reconstruct content from DB text columns, which is fragile); filesystem-only recording (rejected — no structured query path, no dashboard integration without a scan step); recording only on explicit user request (rejected — users will not remember to request recording consistently).

---

## ADR-005: Worker scripts outside Shiny reactive layer — 2026-03-26
**Status**: Accepted

**Context**: Long-running operations (library scan, Whisper transcription, news feed fetch, structured note extraction) cannot run inside Shiny's synchronous reactive layer without blocking the UI.

**Decision**: All long-running operations live as standalone R scripts in `inst/scripts/`. The dashboard triggers them via `system2()` calls or file-drop workflows. Results are written back to SQLite or the filesystem and the dashboard reads them reactively.

**Rationale**: Keeps Shiny reactive graph fast and predictable. Scripts can be run manually, scheduled via Task Scheduler, or called from Claude Code agents — all independent of whether the dashboard is running.

**Consequences**: There is a write-then-read latency between a script completing and the dashboard reflecting its output. Users must manually refresh or use a reactive file-watcher. This is acceptable for a once-or-twice-daily workflow.

**Alternatives considered**: `future` / `promises` async in Shiny (adds complexity, still blocks on heavy I/O), `callr` background processes (viable but adds dependency and complicates error surfacing).
