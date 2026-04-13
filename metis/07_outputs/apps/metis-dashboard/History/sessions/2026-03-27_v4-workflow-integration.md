# Session Log — 2026-03-27 (v4.0 — Workflow Integration and Agent Bridge)

## Summary

Six deliverables were designed and implemented in a single session, advancing the Metis Dashboard from a self-contained interactive daily tool (v3.0) to a two-way bridge between the user's projects and the Claude agent ecosystem. The dashboard can now open, link to, and launch any tracked project directly from the Control Room. Kanban task cards with an assigned agent expose an [Invoke] button that surfaces the agent's project-specific context document and copies a ready-to-run command. A new Agents tab lists all agents from the filesystem and shows their open tasks and latest outputs. A third project view mode (Strategy) provides a workflow-level overview with bottleneck detection. The Library tab gains a Courses section for structured learning. Two agent context documents were written for the Software Engineer agent. All R modules pass Rscript parse syntax check.

## Changes Made

| File | Type | Description |
|------|------|-------------|
| R/mod_control_room.R | MODIFIED | Quick-launch panel added at top of Control Room; each project row shows title, domain badge, git status chip, [Open folder], [GitHub], [Launch app] buttons |
| R/mod_projects.R | MODIFIED | Strategy view toggle added as third mode alongside Kanban and Table; [Invoke] button added to kanban cards that have an agent owner; `strategy_view_ui()` added as standalone function |
| R/mod_library.R | MODIFIED | Courses section added; reads education projects from DB, loads lessons.json from project path, renders per-lesson progress bars with "Mark complete" and "Add to SR deck" buttons |
| R/mod_agents.R | NEW | Agent Output page module — left sidebar lists all agents from 02_agents/ filesystem; main panel shows open tasks, latest output files from 07_outputs/reviews/<agent>/, triage log mentions, agent documents |
| R/data_store.R | MODIFIED | Added `launch_cmd TEXT` column to projects table; added `course_progress` table; added `update_task_notes()`, `get_course_progress()`, `mark_lesson_complete()` helpers |
| app.R | MODIFIED | mod_agents registered; Agents tab added under nav_menu("More") dropdown |
| www/styles.css | MODIFIED | ~20 new CSS classes: .launch-panel, .launch-row, .launch-git-chip variants, .domain-badge, .launch-cmd-block, .invoke-cmd-row, .invoke-cmd-text, .task-invoke-btn, .strategy-board, .strategy-row, .strategy-flow, .strategy-stage (+.active/.warn), .strategy-bottleneck-chip, .strategy-arrow, .agent-list-item, .agent-task-badge, .courses-grid, .course-card, .course-lesson-row, .btn-xs |
| 02_agents/software-engineer/hat-dashboard-context.md | NEW | HAT Dashboard RAG context document for Software Engineer agent — branch server, 14 modified files listed |
| 02_agents/software-engineer/mlm-course-context.md | NEW | MLM Course context document for Software Engineer agent — Node.js app, Quarto files, spatial scan module |

## Decisions Made

- Decision: Agent context lookup via filesystem slug convention (`02_agents/<slug>/<project-context>.md`)
  Rationale: No database registry needed; agents own their own context; fallback to README.md ensures the modal always shows something useful.
  Alternatives considered: Database mapping table (schema churn), concatenated README per agent (unmanageable at scale).
  ADR: ADR-009

- Decision: Strategy view implemented as pure renderUI HTML/CSS, not visNetwork
  Rationale: A linear pipeline diagram does not benefit from a graph physics engine. HTML/CSS renders instantly and gives full layout control. Bottleneck detection is a simple count check.
  Alternatives considered: visNetwork (overkill), DiagrammeR/Mermaid (unnecessary dependency).
  ADR: ADR-010

- Decision: Courses section reads lessons.json from project path at render time; only progress stored in SQLite
  Rationale: Lesson structure belongs to the course, not the dashboard. Avoids a pre-import step and keeps the course definition in one place (the course directory).
  Alternatives considered: SQLite import of lesson metadata (schema churn per course), hard-coded lesson lists in the module (unmaintainable).
  ADR: ADR-011

- Decision: .btn-xs added to www/styles.css as a Bootstrap 5 backfill
  Rationale: Bootstrap 5 removed this utility class. It is used in multiple places (course lesson rows, agent task badges, kanban card buttons). Backfilling in CSS is the least-invasive fix.
  Alternatives considered: Replace all .btn-xs usages with .btn-sm (would require HTML changes across multiple modules), upgrade to a Bootstrap 5 compatible button library (overkill).

## Issues Encountered

- Issue: Bootstrap 5 does not include .btn-xs, causing very small inline buttons to appear at full .btn-sm size
  Resolution: Added .btn-xs to www/styles.css as a backfill class (smaller padding and font-size than .btn-sm).

## Next Steps

- [ ] KI-001: Decide on Whisper vs lighter CPU transcription stack — inspect .venv
- [ ] KI-002: Validate news feed ingestion against live sources
- [ ] KI-003: Add PhD evidence-map table view and article-level filters
- [ ] KI-004: Document the lessons.json schema for course maintainers
- [ ] KI-005: Add stable lesson ID convention to prevent orphaned course_progress records
- [ ] Add file-level open actions from search results and library gallery (carried from v3.0)
- [ ] Consider saved working views / bookmarks (carried from v3.0)
- [ ] Test agent invocation flow end-to-end with a real task delegated to Software Engineer

## Data Rules Validated

N/A — this session concerns the dashboard app, not HAT epidemiological data processing.
