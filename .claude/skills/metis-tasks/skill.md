---
name: Metis Tasks
description: "tasks, my tasks, show tasks, task list, what tasks do I have, open tasks, what needs doing, overdue tasks, blocked tasks, in progress, filter tasks, task status, todo list, work tasks"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

A filtered task list from the CLI — equivalent to the Work tab's task panel. Shows open, blocked, in-progress, and overdue items. Accepts an optional filter to narrow by project or status.

## What to do when invoked

**Usage:** `/metis_tasks` or `/metis_tasks [filter]`

Filters accepted:
- `/metis_tasks blocked` — only blocked tasks
- `/metis_tasks overdue` — tasks past their due date
- `/metis_tasks [project-slug]` — tasks for a specific project (e.g. `my-research-project`)
- `/metis_tasks all` — everything including completed (last 7 days)

**Step 1 — Pull tasks**
- `get_tasks(status="open")` — open tasks ordered by priority
- `get_tasks(status="in_progress")` — active work
- `get_tasks(status="blocked")` — anything blocked (always surface these first)
- If filter matches a project slug: filter results to that project only

**Step 2 — Check for overdue**
Compare each task's `due_date` (if set) to today's date. Flag anything past due with `[OVERDUE]`.

**Step 3 — Compose output**

Group by status: BLOCKED → IN PROGRESS → OPEN (by priority: high → medium → low).

For each task, show:
- Priority indicator: `!!` high / `·` medium / ` ` low
- Task title (truncated to 60 chars if needed)
- Project slug in brackets
- Due date if set, and overdue flag

**Step 4 — Do not log** unless filter is "all" (lightweight read-only command).

## Output format

```
─── Tasks — [YYYY-MM-DD] ──────────────────────────────────

BLOCKED  (n)
  !! [my-research-project] Fix reactive trigger in map module  ← due 2026-04-20 [OVERDUE]
  ·  [my-thesis] Resolve thesis spine alignment

IN PROGRESS  (n)
  !! [analysis-project] Fix inline output for model 4

OPEN — HIGH  (n)
  !! [my-research-project] Review clustering script output
  !! [my-thesis] Write Article 1 intro section

OPEN — MEDIUM / LOW  (n)
  ·  [metis-system] Seed my-thesis external_path
  ·  [field-study] Consolidate screening notes

─────────────────────────────────────────────────────────
n total open tasks · n blocked · Last updated: HH:MM
```

Do not hallucinate task data. If no tasks match the filter, say so plainly: _"No blocked tasks."_
