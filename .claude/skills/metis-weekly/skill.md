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
- `get_briefing_coverage(days=7)` — the week's story threads, each labelled with
  whether the researcher has already seen it in a daily
- `get_missed_news(days=7)` — stories that never reached him in a briefing he read

**Step 2b — The weekly is COMPLETE; this overrides the daily cooldown**

The daily briefings deliberately hold back long-running stories so they don't
repeat every morning. **The weekly must not inherit that suppression.** the researcher reads
the weekly as an overview, not as a diff — if the Ebola epidemic mattered this
week it belongs here even if every daily held it back. Do not omit a thread
because it is on cooldown.

What changes is the **treatment**, not the coverage:

- **Already seen in a daily** → give the week's **trajectory**: where it started,
  what moved, where it stands now. Never restate the daily paragraph he read.
- **Never delivered** (from `get_missed_news`) → report it **properly and in full**.
  He has never been told, so this is new information however old the story is.
  Mark these plainly, e.g. "you haven't seen this yet".
- Prefer a never-delivered story for the standout/what-to-read-next slot when it
  is of comparable importance.

**Step 3 — Compose the summary**

Structure:
1. **Week at a glance** — 3-bullet headline summary
2. **The field this week** — story threads, split into what he already saw
   (trajectory across the week) and what he missed entirely (reported in full)
3. **Ideas** — how many captured, standout 1–2
4. **Literature** — papers indexed, key topic
5. **Meetings** — how many, key decisions or action items
6. **Projects** — any status changes, completed tasks
7. **Notes & mood** — mood trend over the week (if available)
8. **PhD progress** — mention active articles and any movement
9. **Coming up** — tasks due in the next 7 days

**Step 4 — Save output**

Write to: `outputs/reviews/metis/YYYY-MM-DD_weekly-summary.md`
Log: `log_agent_run(paths, "metis", "Weekly summary", ...)`
Mark read: `mark_brief_read(date=<today>, period="weekly")` — a weekly the researcher has read
blocks a story from leading the next day's daily, but does not advance the daily
cooldown ladder. The weekly informs the dailies; it does not silence them for a week. 

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
