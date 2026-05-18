# Version 4.0 — 2026-03-27

## Overview

**Theme: Workflow Integration and Agent Bridge**

v4.0 closes the loop between the dashboard and the Claude agent ecosystem. Previously the dashboard was a read surface and a task tracker. Now it is an active launchpad: projects can be opened on disk, linked to GitHub, or launched from within the app. Tasks can be delegated to agents by clicking [Invoke] — which pulls up the correct agent context document and a ready-to-copy command. A dedicated Agents tab gives visibility into what each agent is working on and what outputs they have produced. A Strategy view gives a workflow-level read of all active projects with bottleneck detection. The Library gains a Courses section for tracking structured learning.

## New Features

### 1. Project Quick-Launch Panel (Control Room)
A new card at the very top of the Control Room tab lists every tracked project with three inline actions per row:
- [Open folder]: calls `browseURL()` to open the local project directory
- [GitHub]: opens the project's GitHub URL in the browser
- [Launch app]: opens a modal with the stored `launch_cmd` (copy-to-clipboard)

Each row also shows a domain badge and a git status chip (clean / uncommitted / unpushed).

Files affected: R/mod_control_room.R, R/data_store.R (new `launch_cmd` column), www/styles.css

### 2. Agent Invocation from Task Cards (Projects)
Kanban task cards that have an assigned agent owner now show a small [Invoke] button. Clicking it opens a modal showing:
- The agent's project-specific context document (from `agents/<agent-slug>/<project>-context.md`, falling back to the agent README)
- A pre-formatted agent invocation command (copy-to-clipboard)
- A delegation notes textarea persisted via `update_task_notes()`

Files affected: R/mod_projects.R, R/data_store.R (new `update_task_notes()` helper)

### 3. Agent Output Page (new Agents tab under "More")
A new `mod_agents.R` module with a two-panel layout:
- Left sidebar: all agents discovered by scanning the `agents/` filesystem directory
- Main panel: on agent selection — open tasks assigned to that agent, latest output files from `outputs/reviews/<agent>/`, mentions in triage logs, and the agent's own documents

Files affected: R/mod_agents.R (NEW), app.R

### 4. Strategy View (Projects)
A third toggle mode alongside Kanban and Table for the Projects tab. Each project renders as a horizontal pipeline card: Defined → Open tasks → Agent assigned → In progress → Done. Stage counts are shown in each node. Projects with more than 3 tasks `in_progress` display an amber bottleneck chip.

Files affected: R/mod_projects.R (`strategy_view_ui()` function added), www/styles.css

### 5. Courses Section (Library)
The Library tab gains a Courses section below the existing article content. It reads projects with `domain = 'education'` from the database, then for each project attempts to load `lessons.json` from the project's local path. Each lesson renders as a row with a progress bar, "Mark complete" button, and "Add to SR deck" button. Completion state is persisted in the new `course_progress` SQLite table.

Files affected: R/mod_library.R, R/data_store.R (`course_progress` table, `get_course_progress()`, `mark_lesson_complete()`), www/styles.css

### 6. Agent Context Documents
Two new project-specific context files written for the Software Engineer agent:
- `hat-dashboard-context.md`: HAT Dashboard project (branch `server`, 14 modified files, pipeline architecture)
- `mlm-course-context.md`: MLM Course project (Node.js app, Quarto files, spatial scan module)

These files are picked up automatically by the [Invoke] modal in the Projects tab.

## Bug Fixes

None in this version.

## Breaking Changes

- The `projects` table now expects a `launch_cmd TEXT` column. If upgrading from v3.0, run `ALTER TABLE projects ADD COLUMN launch_cmd TEXT;` against `data/metis.sqlite`, or delete and re-seed.

## Known Limitations

- KI-004: `lessons.json` schema not yet documented — course maintainers have no reference format
- KI-005: Orphaned `course_progress` records if lesson IDs change in `lessons.json`
- Agent Output page depends on the existence of `outputs/reviews/<agent>/` directories — if absent, the panel renders empty without error (graceful, but potentially confusing)

## Upgrade Notes

When upgrading from v3.0 to v4.0:
1. Run the SQLite migration: `ALTER TABLE projects ADD COLUMN launch_cmd TEXT;`
2. Optionally seed `launch_cmd` values for existing projects via `inst/scripts/seed_projects.R`
3. Create `outputs/reviews/<agent-slug>/` directories for agents that will produce file outputs
4. Ensure `agents/<agent-slug>/` directories exist for all agents listed in `app.R`
5. No package changes — all dependencies from v3.0 remain sufficient
