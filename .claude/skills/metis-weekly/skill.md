---
name: Metis Weekly
description: "weekly summary, week review, what happened this week, weekly briefing, weekly digest, week in review, metis weekly, what did I do this week, weekly overview"
model: claude-sonnet-4-6
effort: thorough
complexity: deep
---

## Purpose

Generate a structured weekly summary across all knowledge domains: ideas captured, papers read, meetings held, projects moved, news highlights, and PhD progress.

## What to do when invoked

**Usage:** `/metis_weekly` or `/metis_weekly [week of YYYY-MM-DD]`

**Step 1 — Determine the week**
Default: the current calendar week (Mon–Sun). If a date is given, use the week containing that date.

**Step 2 — Pull data from RC**

Use the following MCP tools, each filtered to the target week:
- `get_ideas(since=week_start)` — ideas captured
- `search_literature(since=week_start)` — papers indexed
- `get_journal(since=week_start)` — personal notes + mood trend
- `get_daily_insight(date=today)` — latest synthesis
- `get_tasks(status="done", since=week_start)` — completed tasks
- `get_project_status()` — project status changes
- `search_notes(query="meeting", since=week_start)` — meetings

**Step 3 — Compose the summary**

Structure:
1. **Week at a glance** — 3-bullet headline summary
2. **Ideas** — how many captured, standout 1–2
3. **Literature** — papers indexed, key topic
4. **Meetings** — how many, key decisions or action items
5. **Projects** — any status changes, completed tasks
6. **Notes & mood** — mood trend over the week (if available)
7. **PhD progress** — mention active articles and any movement
8. **Coming up** — tasks due in the next 7 days

**Step 4 — Save output**

Write to: `outputs/reviews/metis/YYYY-MM-DD_weekly-summary.md`
Log: `log_agent_run(paths, "metis", "Weekly summary", ...)` 

## Output format

```
─── Weekly Summary: [Mon DD MMM – Sun DD MMM YYYY] ──────
Generated: YYYY-MM-DD HH:MM

WEEK AT A GLANCE
• [Bullet 1]
• [Bullet 2]
• [Bullet 3]

IDEAS (N captured)
──────────────────
[List or "None this week"]

LITERATURE (N papers)
─────────────────────
[List or "None this week"]

MEETINGS (N)
────────────
[List with 1-line summary per meeting]

PROJECTS
────────
[Status changes + completed tasks]

NOTES & MOOD
────────────
[Mood trend + standout entry]

PhD PROGRESS
────────────
[Article status + any movement]

COMING UP (next 7 days)
───────────────────────
[Due tasks]
─────────────────────────────────────────────────────────
```

## Voice

- Terse. Section prose should be one sentence per item; no paragraph-length commentary.
- No openers or closers. No "What a productive week!" or "See you next week."
- WEEK AT A GLANCE bullets state facts: "3 ideas captured, 5 papers indexed, Article 1 draft started." Not: "It was a solid week for literature."
- End on the COMING UP section. Nothing after the template.

## Edge cases
- No data for the week: produce the skeleton with "Nothing recorded" per section — still useful as a checkpoint
- Week spans month boundary: use the calendar week, not month
- User asks for last week: auto-detect and use the previous Mon–Sun range
