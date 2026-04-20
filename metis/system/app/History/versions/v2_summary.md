# Version 2.0 — 2026-03-27

## Overview

Comprehensive UI redesign pass. Every page was rebuilt from functional placeholder or stub state to a polished, visually consistent view. The Ideas module was built from scratch as a complete end-to-end feature. visNetwork was introduced as a dependency for interactive network graphs. Two bugs were resolved. The dashboard is now visually mature and fully scrollable.

## New Features

### Ideas module — full implementation
Previous state: 3 placeholder buttons (stub only).
New state: complete feature.
- Persistent idea capture stored in SQLite (`ideas` table, `idea_links` table)
- visNetwork interactive mind map: project hub nodes (coloured by project), idea child nodes, labelled edges
- Cross-pollination edges: amber connections automatically drawn between ideas from different projects when they share a tag — surfaces unexpected connections between research threads
- Project filter dropdown to focus the mind map on one project
- Idea type classification: Research / Method / Collaboration / Learning / Wildcard
- Graceful fallback message if visNetwork is not installed
Files affected: R/mod_ideas.R, R/data_store.R, check_setup.R

### Library cluster map
- visNetwork topic cluster map: PhD article bucket nodes sized proportionally by article count
- Click-to-filter: clicking a bucket node populates the article list panel below with that bucket's articles
- Animated progress bars show percentage coverage per bucket alongside counts
- Graceful fallback if visNetwork absent
Files affected: R/mod_library.R

### CSS design system
- New warm earth-tone palette: #f4f1ea cream (background), #174c4f teal (headers/nav), #b36a1d rust (accents/interactive)
- Signal-strength badge classes (.badge-high, .badge-medium, .badge-low)
- Priority badge classes (.priority-high, .priority-medium, .priority-low)
- CSS Grid project board layout (.project-board-grid)
- Network container sizing (.network-container)
- Semantic status classes (.status-done, .status-pending, .status-blocked)
Files affected: www/styles.css

## Bug Fixes

### KI-R01: Persistent vertical scroll on all pages
- Root cause: default shinydashboard .small-box height (~10rem) caused every page to overflow even with a small number of value boxes per row
- Fix: constrained .small-box to 5.5rem height with proportional padding reduction in CSS
- Impact: all pages now fit within the viewport without scrolling

### KI-R02: Meeting tab raw string icons ("AUD", "TXT", "PREP")
- Root cause: shinydashboard::valueBox() icon parameter received bare strings instead of icon() function calls
- Fix: replaced three string literals with icon("microphone"), icon("file-text"), icon("tasks")
- Impact: meeting showcase values now display correctly

## Visual Changes

| Page | Previous state | New state |
|---|---|---|
| Control Room | Wide value boxes, no project grid | Compact KPI strip, grid project boards, brief preview card |
| Library | Plain table | Table + visNetwork cluster map + progress bars |
| PhD | Plain article table | Animated progress bars per bucket + thesis document preview |
| Meetings | Broken icons, minimal layout | Fixed icons, clear action rows, Whisper status note |
| News | Plain table | Colour-coded signal cards with summary text |
| Ideas | 3 placeholder buttons | Full visNetwork mind map + SQLite storage + cross-pollination |

## New Dependencies

| Package | Purpose | Added to |
|---|---|---|
| visNetwork | Interactive network graphs (mind map, cluster map) | check_setup.R |

## Breaking Changes

None. The SQLite schema additions (ideas, idea_links tables) are additive. Existing data is unaffected.

## Known Limitations (carried forward)

- KI-001: Local Whisper transcription still pending installation
- KI-002: News feed ingestion not validated against live sources
- KI-003: PhD evidence-map editing not yet implemented in app

## Upgrade Notes

- Run `check_setup.R` after upgrading — it will auto-install visNetwork if absent
- No cache rebuild required (SQLite schema is additive)
- No changes to launcher files
