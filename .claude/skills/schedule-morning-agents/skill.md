---
name: Schedule Morning Agents
description: "schedule morning agents, set up daily automation, configure news-radar schedule, configure librarian schedule, automate morning briefing, register task scheduler, set up 7am automation"
model: claude-sonnet-4-6
effort: normal
complexity: standard
---

## Purpose

Set up persistent daily automation for Metis's morning jobs:
1. **morning_scan** — 07:00: news feeds + PubMed + OpenAlex → `news_briefs` / literature tables
2. **library_index** — 07:30: inventory new files in the library

These jobs are **built into the dashboard** via APScheduler (`system/app-py/scheduler.py`).
The dashboard starts the scheduler automatically on launch (`main.py` lifespan →
`scheduler.start()`), so there are **no R scripts and nothing extra to install**.
Automation runs whenever the dashboard is running. (On startup it also runs a
catch-up news scan if the last one was > 4 h ago.)

## What to do when invoked

**Step 1 — Confirm the scheduler is running and show current jobs:**
With the dashboard running (`system/app-py/run.sh`), check:
```
GET http://localhost:8080/api/scheduler/status   → { running: true, ... }
GET http://localhost:8080/api/scheduler/jobs      → next run times per job
```
Report the jobs and their next scheduled times.

**Step 2 — Adjust times (optional):**
Times come from the user config (`jobs` section, or `schedule.morning_brief_time`).
Update them via `save_job_settings(...)` in `scheduler.py`, or the Metis tab settings.
Default: morning_scan 07:00, library_index 07:30.

**Step 3 — Make it persistent across reboots (the dashboard must be running):**
The scheduler only fires while the dashboard process is up. To keep it always on,
auto-start the dashboard at login via **Windows Task Scheduler** (this launches the
dashboard, which then runs the jobs — it does NOT run any standalone script):
- Action: `wscript.exe "<RC>\system\launch-metis-silent.vbs"`  (silent launcher → `run.sh`)
  or `<RC>\system\install\windows\run-dashboard.bat`
- Trigger: At log on
Verify in Task Scheduler Library that the entry exists and points at the launcher.

**Step 4 — Cloud / machine-off backup (RemoteTrigger):**
If the machine is often off at 07:00, register claude.ai scheduled triggers that call
the agents directly (these run in the cloud, independent of the local dashboard):

News Radar trigger:
- name: "Metis Morning — News Radar"
- schedule: 07:00 local daily
- prompt: `/news-radar Run the daily morning briefing for Metis RC. Fetch today's news for: [your research topics], AI tools and developments, global health policy, epidemiology updates. Save each item to the news_briefs table and a markdown summary to outputs/reviews/news-radar/YYYY-MM-DD_morning.md. Log the run as 'news-radar'.`

Librarian trigger:
- name: "Metis Morning — Librarian"
- schedule: 07:30 local daily
- prompt: `/librarian Scan inbox/ for new PDF, DOCX, or MD files since yesterday. Auto-tag each (entity_type, disease, geography, method), add to the library, and move processed papers to knowledge/library/. Log the run as 'librarian'.`

**Step 5 — Confirm to the user:**
- Which mechanism is active: built-in scheduler (and whether the dashboard auto-starts at login) and/or RemoteTrigger
- The job names and times
- Manual trigger: `POST http://localhost:8080/api/scheduler/jobs/{job_id}/run` (job_id = `morning_scan` or `library_index`)
- Where to see results: the dashboard **Today** tab shows the last scan; pause/resume via `/api/scheduler/jobs/{job_id}/pause`

## Notes
- The built-in scheduler uses the machine's local time automatically (no UTC math needed).
- Times are local; CET = UTC+1 (winter) / CEST = UTC+2 (summer).
- If the dashboard isn't running, the built-in jobs don't fire — that's what the
  login auto-start (Step 3) or the RemoteTrigger backup (Step 4) are for.
