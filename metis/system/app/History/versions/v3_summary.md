# Version 3.0 — 2026-03-27

## Overview

**Theme: Interactive Daily Work Surface**

v3.0 is a feature-density release. Eight independent features were added across five modules in a single session. The dashboard moves from a polished read-only tool to a system that actively supports the user's daily workflow: surfacing what needs attention (morning brief), managing work in progress (kanban), reviewing knowledge (spaced repetition), finding things (search), and seeing how everything connects (knowledge graph).

## New Features

### 1. Morning Brief (Control Room)
Auto-generated panel at the top of the Control Room rendered on every app load. Shows a time-aware greeting, count of overdue and today's tasks, inbox item count, total open task count, the latest high-signal news snippet, and a consistent "today's paper" — a daily random PhD article pick that stays the same throughout the day.
Files affected: R/mod_control_room.R, R/helpers.R (morning_greeting, inbox_item_count, random_phd_paper)

### 2. Kanban Board (Projects tab)
Toggle between Kanban view (new) and Table view (existing). Four columns: Open, In Progress, Blocked, Done. Task cards show project name, owner, and due date with overdue dates highlighted in red. Status transitions are handled by a single shared observeEvent — the JS pattern `Shiny.setInputValue("kanban_move", {task_id, new_status})` is called from each card button, avoiding the duplicate observer problem that arises when per-card observers are registered inside renderUI loops.
Files affected: R/mod_projects.R (rewrite), R/data_store.R (update_task_status), www/styles.css

### 3. Full-text Search (new Search tab under "More")
Queries all SQLite tables (tasks, projects, news_briefs, ideas, meetings) and performs filesystem search across PhD and meetings markdown files. Results are grouped by type with icons and text snippets. Auto-fires after 3+ characters or on button click.
Files affected: R/mod_search.R (NEW), R/helpers.R (search_all_sources), app.R

### 4. Global Knowledge Graph (new Graph tab under "More")
visNetwork graph showing all entity types in the second brain as a unified network: projects (box/teal), ideas (ellipse/amber), article clusters (dot/green), meetings (diamond/blue). Toggle checkboxes control which entity types and edge types are visible. Edges represent: project->idea (FK), project->meeting (title match), idea<->idea (shared tags, dashed amber). Graceful fallback if visNetwork is absent.
Files affected: R/mod_graph.R (NEW), app.R

### 5. Spaced Repetition (Library tab)
SM-2 simplified daily article review widget. A due-review card is surfaced at the top of the Library tab. Interaction is two-step: prompt shown first, then client-side CSS reveal of the answer (no server round-trip), then Hard/Good/Easy rating buttons that write back to SQLite and advance the next_review date. Interval rules: Hard=max(1,cur), Good=max(2,cur*1.5), Easy=max(4,cur*2). A seed button populates the deck from the PhD-seeded article list.
Files affected: R/mod_library.R (rewrite), R/data_store.R (spaced_repetition table + 4 functions), www/styles.css

### 6. Gallery View (Library tab)
Toggle between Gallery (new) and Table views for PhD-seeded articles. Gallery renders a CSS grid of article cards showing: colour-coded bucket badge, filename, surveillance mode, and relevance note. Capped at 60 cards with a count shown if more exist.
Files affected: R/mod_library.R (rewrite), www/styles.css

### 7. Project Completion % (Control Room)
Each project board card now shows a done/total task count and an animated CSS progress bar (transition: width 0.4s ease). Completion percentage is computed by project_completion() in helpers.R.
Files affected: R/mod_control_room.R (rewrite), R/helpers.R (project_completion), www/styles.css

### 8. PhD Milestone Timeline (PhD tab)
New horizontal CSS timeline rendered in renderUI with absolute positioning. Shows all PhD article milestones as status-coloured dots (planned/in_progress/submitted/in_revision/accepted/published) with an amber vertical line marking today. A toggle-form allows adding new milestones: article title, target date, status, notes. Milestone data persists in the new phd_milestones SQLite table.
Files affected: R/mod_phd.R (rewrite), R/data_store.R (phd_milestones table + 2 functions), www/styles.css

## Breaking Changes

None. All existing data in metis.sqlite is preserved. Two new tables (spaced_repetition, phd_milestones) are created on app load via the existing ensure_tables() pattern.

## New Dependencies

- `jsonlite` — added to check_setup.R required packages list (used by search and graph modules for structured data handling)

## Known Limitations

- KI-001: Local Whisper transcription still pending
- KI-002: News feed ingestion not validated against live sources
- KI-003: PhD evidence-map article table with filters not yet implemented (milestone timeline is partial resolution)
- Gallery and SR seed both rely on the PhD-seeded article list being populated — if the Library scan has not been run, these surfaces will be empty

## Upgrade Notes

No manual migration needed. Start the app normally — ensure_tables() will create the two new SQLite tables automatically on first load after the upgrade.
