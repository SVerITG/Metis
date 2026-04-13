# Phase 2 — Today Tab Redesign + M1.11 Cleanup
**Date:** 2026-04-13  
**Agent:** RC Builder  
**Scope:** Today tab stripped to locked layout; M1.11 old module deletion

---

## Completed

| Milestone | Action |
|-----------|--------|
| M1.11 | Deleted `mod_control_room.R`, `mod_projects.R`, `mod_system.R`, `mod_dropzone.R` (user confirmed) |
| M2.1 | `mod_today.R` fully rewritten — stripped from 10-section control room to 6-section arrival screen |
| M2.2 | Launcher row: 6 cards (Capture, Brainstorm, Document, Code, Meeting, Inbox) with copy-prompt modals |
| M2.3 | "What's new overnight" card — counts from last 24h: news items, new papers, ideas, meetings |
| M2.4 | "Today's focus" card — highest-priority active project with next step (conditional) |
| M2.5 | "Scan for changes" — checks git dirty/unpushed, tracked_files changed today, PLANNING.md updated today |
| M2.6 | Trust badge in navbar: `nav_spacer()` + `nav_item(div.trust-badge)` — green shield + "Local-first" |

**Modified files:**
- `R/mod_today.R` — complete rewrite (Phase 2 layout)
- `app.R` — added `nav_spacer()` + trust badge `nav_item()`
- `www/styles.css` — Phase 2 CSS block appended (~180 lines)
- `08_system/implementation-progress.json` — M1.11 + M2.1–M2.6 marked completed

---

## Architecture notes

**Today tab new structure (6 sections):**
1. `greeting_strip` — date, chips (overdue/inbox/tasks/morning-agents ran)
2. `overnight_ui` — counts from last 24h across 4 tables, "clean slate" fallback
3. Launcher row — 6 `launcher-card` buttons, 3-col grid (responsive to 2-col / 1-col)
4. `focus_ui` — top active project by priority; `NULL` when no active projects
5. Scan for changes — `run_scan` button + `scan_results_ui` reactive
6. `token_footer` — yesterday's token usage from `agent_runs`; `NULL` when no runs

**Launcher modal pattern:**
Each card opens a `showModal()` with either:
- **Copy-prompt**: `copy_prompt_block(ns, text, btn_id)` → `tags$pre` + clipboard JS + copy button
- **Navigate**: button sets `input$nav_to` → `observeEvent` calls `removeModal()` + `nav_select("main_nav", tab)`

**Launcher clients:**
| Card | Target | Client label |
|------|--------|-------------|
| Capture | quick-capture modal | Dashboard |
| Brainstorm | Claude Chat with /metis prompt | Claude Chat |
| Document | Claude Cowork with /writing-partner prompt | Claude Cowork |
| Code | Claude Code with /software-engineer or /rc-builder prompt | Claude Code |
| Meeting | Navigate to Meetings tab | Dashboard |
| Inbox | Claude Code with /librarian prompt | Dashboard |

**Trust badge:**
Static `nav_item` in navbar. Shows green shield + "Local-first". Full session call tracking (showing "2 calls sent to Claude — review") is deferred to Phase 4 (pipeline logging, Stage 10).

**Scan for changes scope:**
- Git: `git_all_projects_status(paths)` — all active projects with `external_path`
- Tracked files: `SELECT label, stored_path FROM tracked_files WHERE watch = 1` — files with mtime today
- PLANNING.md: iterates active projects, checks `external_path/PLANNING.md` for today's mtime

---

## Skipped / Deferred

| Item | Reason |
|------|--------|
| M1.12 — Visual audit | Deferred to next RStudio session |
| Ctrl+K capture shortcut | Phase 3 (M3.1–M3.3) |
| Trust badge session call count | Phase 4 pipeline (Stage 10 logging) |
| Quick-capture modal wired to `capture_idea` MCP tool | Phase 3 |

---

## How to verify

1. `shiny::runApp()` in RStudio
2. **Today tab**: should show greeting strip, overnight card, 6 launcher buttons (3-wide grid)
3. Click **"Capture an idea"** → modal with text input
4. Click **"Brainstorm out loud"** → modal with copy-prompt block
5. Click **"Prep for a meeting"** → modal with "Go to Meetings" button → tab switches
6. Click **"Scan now"** → shows results or "All clear"
7. Trust badge visible top-right in navbar: green shield "Local-first"

---

## Next steps

- **Phase 3** (M3.1–M3.3): Ctrl+K quick-capture shortcut, global across all 8 tabs, wired to `capture_idea` MCP tool
- **M1.12**: Visual audit once app is running
