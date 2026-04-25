---
name: Metis Morning
description: "morning briefing, good morning, start my day, morning brief, what's on today, today's briefing, daily briefing, start of day, what should I focus on today, morning summary, daily summary, what's happening today"
model: claude-sonnet-4-6
effort: normal
complexity: standard
---

## Purpose

A single, actionable morning briefing that orients you for the work day. Combines news signals, task priorities, PhD status, and overnight agent activity. Mirrors the Today tab but in a compact CLI format you can read in under 2 minutes.

## What to do when invoked

**Usage:** `/metis_morning` or `/metis-morning`

**Step 1 — Pull today's data (run in parallel)**
- `get_tasks(status="in_progress")` — what is actively being worked on
- `get_tasks(status="open", due_soon=true)` — tasks due today or this week
- `get_tasks(status="blocked")` — anything blocked
- `get_project_status()` — project health
- `get_agent_runs(limit=5, since="yesterday")` — what Metis did overnight
- `get_news_briefs(limit=3)` — top news signals
- `get_daily_insight(date=today)` — any AI-generated insight for today

**Step 2 — Check PhD PLANNING.md**
Read the PhD / HAT Dashboard PLANNING.md to surface the most time-pressured active item:
- `C:/Users/sverschaeve/OneDrive - ITG/Documents/2. HAT disease/1. Epi Data/7. Dashboard/PLANNING.md`
- `C:/Users/sverschaeve/OneDrive - ITG/Documents/9. Education/1. Multilevel Analysis/PLANNING.md`

**Step 3 — Compose the briefing**

Structure (keep it tight — no section longer than 5 lines):
1. **Date + weather of the day** — greeting with current date
2. **Focus block** — 1-2 sentence recommendation for where to put your best 2 hours
3. **Top tasks** — max 3, prioritised: blocked > overdue > due today > in progress
4. **PhD pulse** — one line per active article or PhD priority
5. **Overnight** — what agents ran, any outputs ready for review
6. **News signals** — top 2-3 items, one line each with a domain tag [HAT / AI / PUBLIC HEALTH / METHODS]
7. **Capture reminder** — one prompt to surface what's on your mind

**Step 4 — Save and log**
Write to: `outputs/reviews/metis/YYYY-MM-DD_morning-brief.md`
Log: `log_agent_run(paths, "metis", "Morning briefing", "", "outputs/reviews/metis/...")`

## Output format

```
╔══════════════════════════════════════════════════════════════╗
║  Good morning, Stef — [Weekday, DD MMM YYYY]                 ║
╚══════════════════════════════════════════════════════════════╝

FOCUS TODAY
──────────
[1-2 sentence recommendation for deep work block]

TOP TASKS  (blocked → overdue → due today)
──────────
  🔴 [Task] — [Project]   [BLOCKED / OVERDUE / DUE TODAY]
  · [Task] — [Project]
  · [Task] — [Project]

PhD PULSE
─────────
  · Article 1: [one-line status]
  · Article 2: [one-line status]
  · MLM Course: [next priority]

OVERNIGHT
─────────
  [Agent]: [what it did] → [output file if relevant]
  (or "No agent activity since yesterday")

NEWS SIGNALS
────────────
  [HAT] [headline] — [1 line why it matters]
  [AI]  [headline] — [1 line why it matters]
  [PUBLIC HEALTH] [headline] — [1 line why it matters]

─────────────────────────────────────────────────────────────
What's on your mind? → /metis_ideas  or just type /metis [request]
```

## Edge cases
- No tasks at all: "No open tasks — add some via the dashboard or /metis"
- No overnight activity: skip the section with a single "Quiet night."
- No news briefs in DB: skip or note "No recent signals — run /news-radar to update"
- User runs at weekend: acknowledge it, still produce the brief but mark it as weekend orientation
