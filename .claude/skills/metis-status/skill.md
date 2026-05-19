---
name: Metis Status
description: "status, what's my status, project status, task status, what am I working on, what's pending, show me my tasks, current status, overview, what's open, what's blocked, metis status"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

Quick status overview: open tasks, blocked projects, PhD progress, and any urgent items. Designed to give a 30-second orientation at the start of a session.

## What to do when invoked

**Usage:** `/metis_status`

**Step 1 — Pull status data**
- `get_tasks(status="open")` — open tasks
- `get_tasks(status="in_progress")` — in-progress tasks
- `get_tasks(status="blocked")` — blocked items
- `get_project_status()` — project statuses
- `get_research_context()` — PhD articles and their statuses

**Step 2 — Compose the status snapshot**

Prioritise:
1. Blocked items (need attention NOW)
2. In-progress tasks (what's actively being worked on)
3. Overdue tasks (due_date < today)
4. PhD article status
5. Open tasks count per project

**Step 3 — Surface urgent items**

If there are blocked items or overdue tasks, highlight them at the top with a clear call to action.

## Output format

```
─── Metis Status Snapshot ─── [YYYY-MM-DD HH:MM] ────
⚠️  BLOCKED (N)
  · [Task] — [Project] — blocked since [date]

🔴 OVERDUE (N)  
  · [Task] — due [date] — [Project]

⚙️  IN PROGRESS (N)
  · [Task] — [Project] — [owner]

PhD ARTICLES
  · Article 1: [status]
  · Article 2: [status]
  · Article 3: [status]

PROJECTS — open tasks
  · [Project]: N open, N done

─────────────────────────────────────────────────────
Total open: N  · In progress: N  · Blocked: N
```

## Voice

- Terse. Labels and counts only in the template sections; no filler prose around them.
- No openers, no closers, no "Looking good!" — end on the totals line.
- If adding a comment outside the template (e.g. a blocker callout), one sentence maximum.

## Edge cases
- No tasks at all: "No tasks recorded — add tasks via the Projects tab or /metis"
- Everything is clean (no blocked/overdue): show a positive summary — "All clear. N tasks open across M projects."
- Very large task list (>50 open): summarise by project, don't list every task
