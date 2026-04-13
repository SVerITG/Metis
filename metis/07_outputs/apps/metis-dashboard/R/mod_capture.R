# mod_capture.R
# Global quick-capture modal — triggered by Ctrl+K or the "+ Capture" nav button.
# Phase 3 — M3.1 (shortcut handler), M3.2 (modal + auto-classification), M3.3 (DB writes).
#
# Prefix routing:
#   i:  or no prefix → idea    → ideas table        (idea_type = "idea")
#   n:             → note     → personal_notes table
#   t:             → task     → tasks table          (status = "open", owner = "Metis")
#   q:             → question → ideas table          (idea_type = "question")

# ── UI ──────────────────────────────────────────────────────────────────────
# Returns empty tagList — this module has no persistent on-page UI.

quick_capture_ui <- function(id) {
  tagList()
}

# ── Server ──────────────────────────────────────────────────────────────────

quick_capture_server <- function(id, paths, open_trigger) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # Show modal whenever the trigger fires (Ctrl+K or nav button click)
    observeEvent(open_trigger(), {
      showModal(modalDialog(
        title = tagList(icon("bolt"), " Quick capture"),
        size  = "m",
        easyClose = TRUE,
        tagList(
          div(class = "capture-modal-prefix-hint",
            tags$span(class = "capture-prefix-badge capture-prefix-idea",   "i:"),  " idea  ",
            tags$span(class = "capture-prefix-badge capture-prefix-note",   "n:"),  " note  ",
            tags$span(class = "capture-prefix-badge capture-prefix-task",   "t:"),  " task  ",
            tags$span(class = "capture-prefix-badge capture-prefix-question","q:"), " question",
            tags$span(style = "color:var(--metis-text-muted); margin-left:0.5rem;",
                      "— or just type (defaults to idea)")
          ),
          textAreaInput(
            ns("capture_text"), NULL,
            placeholder = "What's on your mind?",
            rows = 3L,
            width = "100%"
          ),
          uiOutput(ns("type_badge_ui"))
        ),
        footer = tagList(
          modalButton("Cancel"),
          actionButton(ns("save_capture"), tagList(icon("bolt"), " Save"),
                       class = "btn-primary")
        )
      ))
      # Auto-focus the textarea after modal opens
      shinyjs_focus_if_available(ns("capture_text"))
    }, ignoreNULL = TRUE)

    # Live type-badge: update as user types
    output$type_badge_ui <- renderUI({
      txt <- input$capture_text
      if (is.null(txt) || !nzchar(trimws(txt))) return(NULL)
      info <- parse_capture_prefix(txt)
      div(class = paste0("capture-type-badge capture-type-", info$type),
        tagList(icon(info$icon), " ", info$label),
        if (nzchar(info$stripped) && info$stripped != txt)
          tags$span(style = "font-size:0.75rem; color:var(--metis-text-muted); margin-left:0.4rem;",
                    paste0("\u2192 \"", substr(info$stripped, 1L, 40L),
                           if (nchar(info$stripped) > 40L) "\u2026" else "", "\""))
      )
    })

    # Save
    observeEvent(input$save_capture, {
      txt <- trimws(input$capture_text)
      req(nzchar(txt))

      info <- parse_capture_prefix(txt)

      result <- tryCatch({
        switch(info$type,
          idea = {
            tags_str <- auto_tags(info$stripped)
            insert_idea(paths, info$stripped, project_id = "", idea_type = "idea",
                        tags = tags_str)
            list(ok = TRUE, msg = paste0("Idea saved. Tags: ", tags_str))
          },
          note = {
            insert_quick_note(paths, info$stripped)
            list(ok = TRUE, msg = "Note saved.")
          },
          task = {
            insert_task(paths, project_id = NA_character_, title = info$stripped,
                        status = "open", due_date = "", owner = "Metis", notes = "")
            list(ok = TRUE, msg = "Task created (unlinked, owner: Metis).")
          },
          question = {
            tags_str <- auto_tags(info$stripped)
            insert_idea(paths, info$stripped, project_id = "", idea_type = "question",
                        tags = tags_str)
            list(ok = TRUE, msg = "Question queued for Metis.")
          },
          list(ok = FALSE, msg = "Unknown type.")
        )
      }, error = function(e) {
        list(ok = FALSE, msg = conditionMessage(e))
      })

      removeModal()
      type <- if (result$ok) "message" else "error"
      showNotification(result$msg, type = type, duration = 4L)
    })
  })
}

# ── Helpers ──────────────────────────────────────────────────────────────────

# Parse prefix from raw text. Returns list(type, label, icon, stripped).
parse_capture_prefix <- function(txt) {
  txt <- trimws(txt)

  prefix_map <- list(
    "i:"  = list(type = "idea",     label = "Idea",     icon = "lightbulb"),
    "n:"  = list(type = "note",     label = "Note",     icon = "file-lines"),
    "t:"  = list(type = "task",     label = "Task",     icon = "list-check"),
    "q:"  = list(type = "question", label = "Question", icon = "circle-question")
  )

  for (pfx in names(prefix_map)) {
    if (startsWith(tolower(txt), pfx)) {
      info    <- prefix_map[[pfx]]
      stripped <- trimws(substr(txt, nchar(pfx) + 1L, nchar(txt)))
      return(c(info, list(stripped = if (nzchar(stripped)) stripped else txt)))
    }
  }

  # No prefix → idea
  list(type = "idea", label = "Idea", icon = "lightbulb", stripped = txt)
}

# Simple auto-tag extraction (mirrors the MCP tool's logic in pure R)
auto_tags <- function(txt) {
  hashtags <- regmatches(txt, gregexpr("#\\w+", txt))[[1L]]
  if (length(hashtags)) {
    return(paste(sub("^#", "", hashtags[seq_len(min(length(hashtags), 10L))]), collapse = ","))
  }
  stopwords <- c("about", "after", "before", "between", "could", "should",
                 "would", "their", "there", "which", "where", "these", "those")
  words <- regmatches(tolower(txt), gregexpr("\\b[a-zA-Z]{5,}\\b", tolower(txt)))[[1L]]
  unique_words <- character()
  for (w in words) {
    if (!w %in% stopwords && !w %in% unique_words) {
      unique_words <- c(unique_words, w)
      if (length(unique_words) >= 5L) break
    }
  }
  paste(unique_words, collapse = ",")
}

# Insert a quick personal note (no insert_note helper exists in data_store.R)
insert_quick_note <- function(paths, content) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  note_id <- sprintf("note-%s", format(Sys.time(), "%Y%m%d%H%M%S"))
  now     <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  DBI::dbExecute(
    con,
    "INSERT INTO personal_notes (note_id, content, title, tags, created_at, updated_at) VALUES (?, ?, '', '', ?, ?)",
    params = list(note_id, content, now, now)
  )
  invisible(note_id)
}

# No-op if shinyjs not loaded — focus is nice-to-have, not required
shinyjs_focus_if_available <- function(input_id) {
  tryCatch(
    shinyjs::runjs(sprintf("document.getElementById('%s').focus();", input_id)),
    error = function(...) NULL
  )
}
