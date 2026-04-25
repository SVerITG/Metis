---
name: Metis Projects
description: "projects overview, show me my projects, project status, active projects, project list, what projects do I have, project health, project summary, where are my projects, projects dashboard, work overview, what am I working on"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

A clean overview of all active projects: their status, open task counts, recent activity, and the next concrete step. Replaces needing to open the Work or Planner tab for a quick orientation.

## What to do when invoked

**Usage:** `/metis_projects` or `/metis-projects`
**Optional:** `/metis_projects [project-name]` — deep-dive on one project

**Step 1 — Pull project data**
- `get_project_status()` — all projects with status, last_activity
- `get_tasks(status="open")` — count open tasks per project
- `get_tasks(status="blocked")` — flag blocked items
- `get_tasks(status="in_progress")` — flag in-progress items

**Step 2 — Read PLANNING.md files for context on active projects**

Active projects with PLANNING.md files:
- HAT Dashboard: `C:/Users/sverschaeve/OneDrive - ITG/Documents/2. HAT disease/1. Epi Data/7. Dashboard/PLANNING.md`
- HAT Clustering: `C:/Users/sverschaeve/OneDrive - ITG/Documents/2. HAT disease/1. Epi Data/4. Clustering/PLANNING.md`
- MLM Course: `C:/Users/sverschaeve/OneDrive - ITG/Documents/9. Education/1. Multilevel Analysis/PLANNING.md`

For single-project deep-dive: read the matching PLANNING.md fully and surface the last-session summary + next step.

**Step 3 — Compose the output**

For each project:
- Status indicator: 🟢 active / 🟡 stalled / 🔴 blocked / ⚪ someday
- Open tasks count + any overdue
- One-line "next step" extracted from PLANNING.md or tasks
- Git status note if relevant (uncommitted, branch name)

**Step 4 — Log** (skip for quick single-project lookups)
`log_agent_run([], "metis", "Projects overview", "", "")`

## Output format

```
─── Projects Overview — [YYYY-MM-DD] ───────────────────────

🟢 HAT DASHBOARD  [hat-dashboard]
   Branch: server | Repo: SVerITG/HAT_Dashboard_1.0
   Open: N tasks  · Blocked: N  · In progress: N
   Next: [extracted from PLANNING.md or top task]

🟢 HAT CLUSTERING  [hat-clustering]
   Branch: main  · Open: N tasks
   Next: [next step]

🟢 MLM COURSE  [multilevel-analysis]
   Teaching / Development  · 33% complete (2/6 modules)
   Next: [next step from PLANNING.md]

🟡 PASSIVE SCREENING DRC  [passive-screening-drc]
   Open: N tasks
   Next: [next step]

🔵 PhD FRAMEWORK  [phd-framework]
   Three articles in progress
   Next: [most time-pressured item]

──────────────────────────────────────────────────────────
Total active: N  · Open tasks: N  · Blocked: N

To dive into one project: /metis_projects [name]
To see all tasks:         /metis_status
To work on a project:     /metis [describe what you want to do]
```

## Edge cases
- Project has no PLANNING.md: show tasks only, note "No PLANNING.md — consider adding one"
- Project is stalled (no activity in 14+ days): flag as 🟡 stalled with last-activity date
- Single project mode: read PLANNING.md fully and produce a 10-line summary of last session + next 3 steps
