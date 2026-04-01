# Monia Dashboard Implementation Plan

## Goal

Build one local-first command-center application that becomes the daily operating surface for Monia and the specialist agents.

## Architecture choice

Use `R Shiny` as the UI backbone for `v1`, with modular page structure from the start.

Do not force all background work into Shiny itself. Keep longer-running tasks outside the reactive layer and trigger them from the app.

## First build phases

### Phase 1: working shell

- create app navigation
- create shared theme and layout rules
- show live counts from current folders and metadata
- define core pages:
  - Control Room
  - Library
  - PhD
  - Projects
  - Meetings
  - News
  - Ideas

Status:
- implemented

### Phase 2: local metadata layer

- add a small `SQLite` or `DuckDB` database
- mirror literature, meeting, project, and note metadata into indexed tables
- stop reading everything directly from files on each view
- define stable object ids for:
  - source
  - note
  - meeting
  - project
  - article
  - task

Status:
- implemented with `SQLite`

### Phase 3: action wiring

- add `Scan for new material`
- add `Import meeting recording`
- add `Create or import transcript`
- add `Create idea`
- add `Mark as relevant to PhD`
- add `Open acquisition-needed list`

These actions should call local scripts, not embed long jobs directly in reactive code.

Status:
- implemented for library scan, meeting import, transcript workflow, structured extraction, and feed fetch
- not implemented yet for PhD-specific actions and acquisition-needed flows

### Phase 4: agent integration

- Monia reads the dashboard state and open decisions
- Librarian writes scan results and relevance notes
- Meeting Memory writes transcripts, decisions, and briefings
- PhD Architect writes thesis-spine and evidence-map updates
- News Radar writes daily and weekly briefs

### Phase 4a: implemented automation

- transcript import or Whisper-trigger path
- transcript-to-structured-note extraction
- transcript-to-briefing generation
- automated news feed ingestion into stored briefs
- real project and task objects in SQLite

Current blocker:
- local Whisper engine installation is incomplete, so automatic audio transcription is still pending

### Phase 5: visual maturity

Status: **substantially complete as of v2.0 (2026-03-27)**

- ~~replace placeholder tables with designed cards and filtered views~~ — done (news cards, progress bars, network maps)
- add timeline and dependency views where they improve decisions — not yet
- add saved state and bookmarked working views — not yet
- add project-level drilldowns — not yet

## Build order (updated 2026-03-27)

1. finish local Whisper installation and update `transcribe_meeting.R` to use the installed engine
2. verify `fetch_news_feeds.R` against live feeds and improve source selection
3. add PhD evidence-map tables and dashboard views
4. add file-opening and navigation shortcuts from dashboard tables
5. add agent-output pages and Monia recommendation logic
6. ~~refine visual design and app ergonomics~~ — done in v2.0

## Technical structure

### UI

- `app.R`
- `R/data_store.R`
- `R/mod_control_room.R`
- `R/mod_library.R`
- `R/mod_phd.R`
- `R/mod_projects.R`
- `R/mod_meetings.R`
- `R/mod_news.R`
- `R/mod_ideas.R`
- `www/styles.css`

### Worker scripts

- `inst/scripts/scan_library.R`
- `inst/scripts/import_meeting.R`
- `inst/scripts/transcribe_meeting.R`
- `inst/scripts/extract_meeting_structure.R`
- `inst/scripts/fetch_news_feeds.R`

### Current verification state (updated 2026-03-27, v2.0)

- app loads successfully
- metadata database exists and contains projects, tasks, meetings, news briefs, ideas, idea_links
- structured note generation works
- briefing generation works
- feed ingestion script exists but still needs live validation
- automatic transcription still depends on finishing local Whisper installation
- visNetwork mind map (Ideas) and cluster map (Library) implemented with graceful fallbacks
- full CSS redesign complete — scroll issue resolved

## Non-goals for v1

- perfect ontology coverage
- rich editing inside the dashboard
- cloud-first architecture
- premature multi-user support

## Decision rule

If a feature is mainly analytical, routing-focused, or metadata-heavy, keep it in the dashboard.

If a feature is a long-running pipeline, keep it as a local worker and trigger it from the dashboard.
