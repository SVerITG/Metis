# Monia Dashboard

This is the first working dashboard shell for the local-first second-brain system.

## Current scope

- modular `R Shiny` application
- current navigation for:
  - Control Room
  - Library
  - PhD
  - Projects
  - Meetings
  - News
  - Ideas
- live counts pulled from the current second-brain folders and metadata files
- local `SQLite` metadata database
- project and task tracking
- library scan action
- meeting import action
- transcript import / transcript placeholder action
- structured note and briefing generation from transcripts
- manual and feed-based news brief storage
- lightweight styling with `bslib`

## Launching the dashboard

**Step 0 — first-time setup (run once in RStudio):**
```r
source("check_setup.R")                    # checks + installs packages (incl. visNetwork)
source("inst/scripts/seed_projects.R")     # populates projects and tasks
source("inst/scripts/schedule_agents.R")   # registers Windows scheduled jobs
```

**Option A — from RStudio:** `shiny::runApp()`

**Option B — without RStudio:** double-click `launch_monia.bat`
- Dashboard opens at `http://localhost:3838`
- Keep the console window open

**Option C — auto-start at Windows login:**
1. Press `Win+R` → type `shell:startup` → Enter
2. Drop a shortcut to `launch_monia_background.vbs` into that folder

## Main files

- `app.R`
- `R/data_store.R`
- `R/mod_control_room.R`
- `R/mod_library.R`
- `R/mod_projects.R`
- `R/mod_meetings.R`
- `R/mod_news.R`
- `inst/scripts/`

## Current limitations

- automatic Whisper transcription is not working yet because the local engine install is incomplete
- news feed ingestion exists but still needs live-source verification and curation
- PhD editing and evidence-map workflows are not yet in the app
- no authentication or role-based permissions yet

## Next implementation priority

Finish local Whisper setup, validate automated news ingestion on live feeds, and add richer PhD/task workflows.
