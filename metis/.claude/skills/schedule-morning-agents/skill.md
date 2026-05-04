---
name: Schedule Morning Agents
description: "schedule morning agents, set up daily automation, configure news-radar schedule, configure librarian schedule, automate morning briefing, register task scheduler, set up 7am automation"
model: claude-sonnet-4-6
effort: normal
complexity: standard
---

## Purpose

Set up persistent scheduled automation for two Metis morning agents:
1. **News Radar** — 07:00 CET: fetch RSS feeds, populate `news_briefs` table
2. **Librarian** — 07:30 CET: scan `00_inbox/` for new files, queue for tagging

## What to do when invoked

**Step 1 — Check existing schedule:**
Run `schedule_agents.R` check first:
```r
# From the dashboard folder:
source("inst/scripts/schedule_agents.R")
```
If it reports existing Metis tasks, show them and ask whether to re-register or skip.

**Step 2 — Register via Windows Task Scheduler (primary method):**
Open a Windows terminal (not WSL) and run:
```
cd "C:\Users\{username}\[path-to-research-cortex]\metis\07_outputs\apps\metis-dashboard"
Rscript inst\scripts\schedule_agents.R
```
This creates:
- `Metis_NewsRadar` — daily 07:00, runs `fetch_news_feeds.R`
- `Metis_LibrarianScan` — daily 07:30, runs `morning_librarian.R`

**Step 3 — Register via RemoteTrigger (backup / cloud method):**
Use the RemoteTrigger tool to create persistent claude.ai scheduled triggers:

News Radar trigger:
- name: "Metis Morning — News Radar"
- schedule: 07:00 CET daily
- prompt: `/news-radar Run the daily morning briefing for Metis RC. Fetch today's news for: [your research topic], AI tools and developments, global health policy, epidemiology updates. Save each brief item to the news_briefs SQLite table. Save markdown summary to 07_outputs/reviews/news-radar/YYYY-MM-DD_morning.md. Log run to agent_runs table as 'news-radar'.`

Librarian trigger:
- name: "Metis Morning — Librarian"
- schedule: 07:30 CET daily
- prompt: `/librarian Scan 00_inbox/ for new PDF, DOCX, or MD files added since yesterday. For each new file: auto-tag (entity_type, disease, geography, method, phd_article_link), add to library_seeded table, move processed papers to 05_sources/literature/. Log run to agent_runs table as 'librarian'.`

**Step 4 — Confirm:**
Report to user:
- Which method was used (Task Scheduler / RemoteTrigger / both)
- Task names and scheduled times
- How to verify: "Check Task Scheduler > Task Scheduler Library for Metis_* entries"
- How to run manually: "Run `source('inst/scripts/fetch_news_feeds.R')` from the dashboard folder"

## Notes
- CET = UTC+1 (winter) / CEST = UTC+2 (summer). Windows Task Scheduler uses local time automatically.
- Logs appear in `C:\Metis\` after first run.
- Dashboard Control Room shows morning agent status once they've run.
- If Task Scheduler fails on OneDrive paths, the script creates wrapper `.bat` files in `C:\Metis\` to avoid path-with-spaces issues.
