# Phase 3 — Quick Capture (Ctrl+K)
**Date:** 2026-04-13  
**Agent:** RC Builder  
**Scope:** Global Ctrl+K shortcut, capture modal with auto-classification, DB wiring

---

## Completed

| Milestone | Action |
|-----------|--------|
| M3.1 | Ctrl+K / Cmd+K keydown listener in `app.R` header; `+ Capture` button in navbar |
| M3.2 | `mod_capture.R` — `quick_capture_server` module with prefix routing and live type badge |
| M3.3 | Four capture routes: idea → `insert_idea()`, note → `insert_quick_note()`, task → `insert_task()`, question → `insert_idea(type='question')` |

**New file:**
- `R/mod_capture.R` — `quick_capture_ui` (empty) + `quick_capture_server`

**Modified files:**
- `app.R` — Ctrl+K JS, `+ Capture` nav button, `quick_capture_ui("capture")`, `quick_capture_server("capture", paths, reactive(input$global_capture))`
- `R/mod_today.R` — fixed schema bug: replaced raw `INSERT INTO ideas (text, source, ...)` with `insert_idea()` + `auto_tags()`
- `www/styles.css` — Phase 3 CSS block (~60 lines)
- `08_system/implementation-progress.json` — M3.1–M3.3 marked completed

---

## Architecture notes

**Trigger chain:**
```
User presses Ctrl+K         User clicks "+ Capture" button
       ↓                              ↓
JS keydown listener            onclick handler
       ↓                              ↓
Shiny.setInputValue('global_capture', Date.now())
                     ↓
  app.R server: reactive(input$global_capture)
                     ↓
  quick_capture_server observeEvent → showModal()
```

**Prefix routing in `parse_capture_prefix(txt)`:**
```
"i: some idea"    → type=idea,     stripped="some idea"
"n: some note"    → type=note,     stripped="some note"
"t: some task"    → type=task,     stripped="some task"
"q: a question"   → type=question, stripped="a question"
"just text"       → type=idea,     stripped="just text"  (default)
```

**Why `reactive(input$global_capture)` instead of passing `input` directly:**
The `quick_capture_server` module needs a reactive trigger from the parent session. Passing `reactive(input$global_capture)` lets the module observe parent-scope inputs without namespace collision — the module's own `input$` is namespaced to `"capture-*"`.

**Schema fix in `mod_today.R`:**
The original code used `INSERT INTO ideas (text, source, tags, created_at)` — `source` does not exist in the R dashboard's ideas table schema. Fixed to use `insert_idea(paths, text, project_id, idea_type, tags)` which is the canonical helper in `data_store.R`.

**`shinyjs` dependency:**
`shinyjs_focus_if_available()` wraps `shinyjs::runjs()` in a `tryCatch` — auto-focus works if `shinyjs` is loaded, degrades gracefully if not (modal still opens, just without cursor focus).

---

## How to verify

1. `shiny::runApp()` in RStudio
2. Press **Ctrl+K** from any tab → quick-capture modal opens
3. Type `i: HAT surveillance idea` → type badge shows blue "Idea"
4. Type `n: note about methods` → type badge shows green "Note"
5. Type `t: review article draft` → type badge shows orange "Task"
6. Type `q: what is the best clustering method?` → type badge shows purple "Question"
7. Click **Save** → notification confirms; check Thinking tab for the saved entry
8. **"+ Capture" button** visible in navbar, right of "Metis" tab — clicking also opens the modal

---

## Next steps

- **Phase 4** (M4.1–M4.12): Master `/metis` interaction pipeline — session bootstrap, data guardian intercept, intent parsing, token budget, surgical context assembly, session_events table
- **M1.12**: Visual audit (deferred until RStudio session)
