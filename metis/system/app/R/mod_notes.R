# mod_notes.R
# Notes tab — Personal Notes (journalling) and Meeting Notes.
# Personal Notes: free-form markdown notes with mood + energy tracking.
# Meeting Notes: read-only list from meetings table with link to Meetings tab.

mood_emoji_notes <- c(
  "Very good" = "\U0001f60a",
  "Good"      = "\U0001f642",
  "Neutral"   = "\U0001f610",
  "Tired"     = "\U0001f634",
  "Stressed"  = "\U0001f630",
  "Excited"   = "\U0001f680"
)

# ── UI ────────────────────────────────────────────────────────────────────────

notes_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(
      class = "page-intro",
      h1("Notes"),
      p("Your personal reflections and meeting records — all in one place."),
      div(
        style = "display:flex; gap:0.5rem; margin-top:0.75rem;",
        actionButton(
          ns("mode_personal"), "Personal Notes",
          class = "btn-primary",
          icon  = icon("pen-to-square")
        ),
        actionButton(
          ns("mode_meeting"), "Meeting Notes",
          class = "btn-outline-secondary",
          icon  = icon("users")
        )
      )
    ),

    # ── Personal Notes panel ─────────────────────────────────────────────────
    conditionalPanel(
      condition = "output.notes_mode === 'personal'",
      ns = ns,

      layout_columns(
        col_widths = c(5, 7),

        # Left: note entry form
        card(
          card_header("New note"),
          card_body(
            textInput(ns("note_title"), "Title (optional)",
                      placeholder = "Untitled note"),
            textAreaInput(ns("note_content"), NULL,
                          placeholder = "What\u2019s on your mind today?",
                          rows = 8,
                          width = "100%"),
            selectInput(
              ns("note_mood"), "Mood",
              choices = c("Very good", "Good", "Neutral", "Tired", "Stressed", "Excited")
            ),
            sliderInput(ns("note_energy"), "Energy level",
                        min = 1, max = 5, value = 3, step = 1, ticks = TRUE),
            textInput(ns("note_tags"), "Tags",
                      placeholder = "comma-separated, e.g. phd, ideas, stress"),
            div(
              class = "action-row",
              actionButton(ns("save_note"), "Save note",
                           class = "btn-primary", icon = icon("floppy-disk")),
              actionButton(ns("clear_note"), "Clear",
                           class = "btn-outline-secondary")
            ),
            textOutput(ns("note_status"))
          )
        ),

        # Right: recent notes
        card(
          card_header(
            div(
              style = "display:flex; justify-content:space-between; align-items:center; width:100%;",
              span("Recent notes"),
              actionButton(ns("refresh_notes"), NULL,
                           icon  = icon("rotate"),
                           class = "btn-sm btn-outline-secondary",
                           title = "Refresh")
            )
          ),
          card_body(
            class = "card-scroll",
            uiOutput(ns("notes_list_ui"))
          )
        )
      )
    ),

    # ── Meeting Notes panel ──────────────────────────────────────────────────
    conditionalPanel(
      condition = "output.notes_mode === 'meeting'",
      ns = ns,

      layout_columns(
        col_widths = c(12),

        card(
          card_header(
            div(
              style = "display:flex; justify-content:space-between; align-items:center; width:100%;",
              span("Meeting notes"),
              div(
                style = "display:flex; gap:0.5rem;",
                actionButton(ns("refresh_meetings_notes"), NULL,
                             icon  = icon("rotate"),
                             class = "btn-sm btn-outline-secondary",
                             title = "Refresh"),
                actionButton(ns("go_to_meetings"), "Open Meetings tab",
                             class = "btn-sm btn-outline-secondary",
                             icon  = icon("arrow-right"))
              )
            )
          ),
          card_body(
            class = "card-scroll",
            uiOutput(ns("meeting_notes_ui"))
          )
        )
      )
    )
  )
}

# ── Server ────────────────────────────────────────────────────────────────────

notes_server <- function(id, paths, parent_session = NULL) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    ensure_db_schema(paths)

    # ── Mode tracking ────────────────────────────────────────────────────────
    notes_mode <- reactiveVal("personal")

    observeEvent(input$mode_personal, { notes_mode("personal") })
    observeEvent(input$mode_meeting,  { notes_mode("meeting") })

    output$notes_mode <- renderText({ notes_mode() })
    outputOptions(output, "notes_mode", suspendWhenHidden = FALSE)

    observe({
      m <- notes_mode()
      try(updateActionButton(session, "mode_personal",
                         class = if (m == "personal") "btn-primary" else "btn-outline-secondary"), silent = TRUE)
      try(updateActionButton(session, "mode_meeting",
                         class = if (m == "meeting") "btn-primary" else "btn-outline-secondary"), silent = TRUE)
    })

    # Navigate to Meetings tab when button clicked
    observeEvent(input$go_to_meetings, {
      s <- if (!is.null(parent_session)) parent_session else session
      updateNavbarPage(s, inputId = "main_nav", selected = "Meetings")
    })

    # ── Personal Notes ───────────────────────────────────────────────────────
    notes_refresh <- reactiveVal(0L)
    note_status   <- reactiveVal("")

    observeEvent(input$save_note, {
      content <- trimws(input$note_content)
      req(nzchar(content))
      tryCatch({
        insert_journal_entry(
          paths        = paths,
          content      = content,
          mood         = input$note_mood,
          energy_score = as.integer(input$note_energy),
          tags         = trimws(input$note_tags)
        )
        note_status("Note saved.")
        notes_refresh(notes_refresh() + 1L)
      }, error = function(e) {
        note_status(paste("Error saving note:", conditionMessage(e)))
      })
    })

    observeEvent(input$clear_note, {
      updateTextInput(session, "note_title", value = "")
      updateTextAreaInput(session, "note_content", value = "")
      updateTextInput(session, "note_tags", value = "")
      updateSliderInput(session, "note_energy", value = 3)
      note_status("")
    })

    observeEvent(input$refresh_notes, {
      notes_refresh(notes_refresh() + 1L)
    })

    output$note_status <- renderText(note_status())

    output$notes_list_ui <- renderUI({
      notes_refresh()

      entries <- tryCatch(
        get_journal_entries(paths, n = 15L),
        error = function(e) NULL
      )

      if (is.null(entries) || nrow(entries) == 0L) {
        return(div(
          class = "empty-state",
          icon("pen-to-square"),
          p("No notes yet. Write your first one.")
        ))
      }

      entry_cards <- lapply(seq_len(nrow(entries)), function(i) {
        row      <- entries[i, ]
        emoji    <- mood_emoji_notes[row$mood]
        if (is.na(emoji)) emoji <- ""
        date_str <- substr(row$created_at, 1L, 10L)
        preview  <- if (nchar(row$content) > 220L)
          paste0(substr(row$content, 1L, 220L), "\u2026")
        else
          row$content

        tag_chips <- if (nzchar(trimws(row$tags))) {
          tgs <- trimws(strsplit(row$tags, ",")[[1L]])
          tagList(lapply(tgs, function(t)
            tags$span(t,
              style = paste0(
                "display:inline-block; margin:2px 3px 0 0; padding:1px 7px;",
                "background:#e8f0f0; border-radius:10px;",
                "font-size:0.75rem; color:#2e6b4f;"
              )
            )
          ))
        } else NULL

        div(
          style = paste0(
            "border:1px solid #e4e4e4; border-radius:8px; padding:0.85rem;",
            "margin-bottom:0.75rem; background:#fff;"
          ),
          div(
            style = "display:flex; justify-content:space-between; align-items:baseline;",
            tags$strong(date_str),
            tags$span(style = "font-size:1.2rem;", emoji)
          ),
          p(
            style = "margin:0.4rem 0 0.5rem 0; color:#444; font-size:0.88rem; line-height:1.45;",
            preview
          ),
          tag_chips
        )
      })

      tagList(entry_cards)
    })

    # ── Meeting Notes ────────────────────────────────────────────────────────
    mtg_notes_refresh <- reactiveVal(0L)

    observeEvent(input$refresh_meetings_notes, {
      mtg_notes_refresh(mtg_notes_refresh() + 1L)
    })

    output$meeting_notes_ui <- renderUI({
      mtg_notes_refresh()

      meetings <- tryCatch({
        sql <- "SELECT meeting_id, title, meeting_date, domain, project,
                       transcript_status, structured_note_path
                  FROM meetings
                 ORDER BY meeting_date DESC
                 LIMIT 30"
        db_table(paths, sql)
      }, error = function(e) NULL)

      if (is.null(meetings) || nrow(meetings) == 0L) {
        return(div(
          class = "empty-state",
          icon("users"),
          p("No meeting notes yet."),
          p("Record or import a meeting in the ", tags$strong("Meetings tab"), ".")
        ))
      }

      meeting_cards <- lapply(seq_len(nrow(meetings)), function(i) {
        row        <- meetings[i, ]
        date_str   <- if (nzchar(trimws(row$meeting_date))) row$meeting_date else "—"
        domain_str <- if (!is.na(row$domain) && nzchar(row$domain)) row$domain else ""
        project_str <- if (!is.na(row$project) && nzchar(row$project)) row$project else ""

        status_badge <- switch(
          row$transcript_status %||% "",
          "complete"               = tags$span("Transcribed", class = "badge bg-success"),
          "pending_transcription"  = tags$span("Pending transcription", class = "badge bg-warning text-dark"),
          tags$span("No transcript", class = "badge bg-secondary")
        )

        note_link <- if (!is.na(row$structured_note_path) && nzchar(row$structured_note_path)) {
          tags$span(
            style = "font-size:0.78rem; color:#2d6073;",
            icon("file-lines"), " Structured note available"
          )
        } else NULL

        div(
          style = paste0(
            "border:1px solid #e4e4e4; border-radius:8px; padding:0.85rem;",
            "margin-bottom:0.65rem; background:#fff;"
          ),
          div(
            style = "display:flex; justify-content:space-between; align-items:flex-start;",
            div(
              tags$strong(row$title),
              tags$br(),
              tags$span(style = "font-size:0.8rem; color:#666;",
                        date_str,
                        if (nzchar(domain_str)) paste0(" · ", domain_str),
                        if (nzchar(project_str)) paste0(" · ", project_str))
            ),
            status_badge
          ),
          if (!is.null(note_link)) div(style = "margin-top:0.4rem;", note_link)
        )
      })

      tagList(meeting_cards)
    })
  })
}

# ── DB helpers (shared with brainstorm context assembly in mod_ideas.R) ───────

insert_journal_entry <- function(paths, content, mood, energy_score, tags) {
  entry_id   <- sprintf("jrnl-%s", format(Sys.time(), "%Y%m%d%H%M%S"))
  created_at <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")

  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  DBI::dbExecute(
    con,
    paste0(
      "INSERT INTO journal_entries ",
      "(entry_id, content, mood, energy_score, tags, created_at) ",
      "VALUES (?, ?, ?, ?, ?, ?)"
    ),
    list(entry_id, content, mood, as.integer(energy_score), tags, created_at)
  )

  invisible(entry_id)
}

get_journal_entries <- function(paths, n = 15L) {
  sql <- sprintf(
    "SELECT entry_id, content, mood, energy_score, tags, created_at
       FROM journal_entries
      ORDER BY created_at DESC
      LIMIT %d",
    as.integer(n)
  )
  db_table(paths, sql)
}

# Null-coalescing helper used in meeting notes UI
`%||%` <- function(a, b) if (!is.null(a) && !is.na(a)) a else b
