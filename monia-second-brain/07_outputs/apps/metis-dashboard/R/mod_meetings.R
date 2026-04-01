# mod_meetings.R
# v5: Meeting intelligence — import, transcribe, structure, brief, recommend.

meetings_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Meetings"),
      p("Import recordings, extract intelligence, track people, and get pre-meeting briefings.")
    ),

    # ── KPIs ───────────────────────────────────────────────────────
    layout_columns(
      col_widths = c(3, 3, 3, 3),
      value_box(title = "Meetings",    value = textOutput(ns("meeting_count")),
                showcase = icon("calendar"),   theme = "primary"),
      value_box(title = "Transcripts", value = textOutput(ns("transcript_count")),
                showcase = icon("file"),       theme = "info"),
      value_box(title = "People",      value = textOutput(ns("person_count")),
                showcase = icon("users"),      theme = "success"),
      value_box(title = "Briefings",   value = textOutput(ns("briefing_count")),
                showcase = icon("book-open"),  theme = "warning")
    ),

    layout_columns(
      col_widths = c(5, 7),

      # ── Left: Import + Pre-briefing ─────────────────────────────
      tagList(
        card(
          card_header("Import meeting"),
          card_body(
            fileInput(ns("meeting_file"), "Audio / transcript file", multiple = FALSE),
            textInput(ns("meeting_title"), "Title"),
            layout_columns(
              col_widths = c(6, 6),
              textInput(ns("meeting_date"), "Date", value = format(Sys.Date())),
              selectInput(ns("meeting_type"), "Type",
                          choices = c("general", "project_review", "phd_supervision",
                                      "strategy", "seminar", "one_on_one"))
            ),
            layout_columns(
              col_widths = c(6, 6),
              textInput(ns("meeting_domain"), "Domain", value = "sleeping sickness"),
              textInput(ns("meeting_project"), "Project", value = "general")
            ),
            textInput(ns("meeting_attendees"), "Attendees (comma-separated)"),
            div(class = "action-row",
              actionButton(ns("import_meeting"), tagList(icon("upload"), " Import"), class = "btn-primary")
            ),
            textOutput(ns("import_status"))
          )
        ),

        card(
          card_header(tagList(icon("wand-magic-sparkles"), "  Pre-meeting briefing generator")),
          card_body(
            tags$p(style = "font-size:0.82rem; color:#6d7c74;",
                   "Generate context from past meetings + library for your next meeting."),
            layout_columns(
              col_widths = c(6, 6),
              textInput(ns("prebriefing_topic"), "Topic / project"),
              textInput(ns("prebriefing_people"), "Key people")
            ),
            div(class = "action-row",
              actionButton(ns("generate_prebriefing"), tagList(icon("bolt"), " Generate briefing"),
                           class = "btn-outline-secondary")
            ),
            uiOutput(ns("prebriefing_output"))
          )
        )
      ),

      # ── Right: Transcript workflow + Intelligence ────────────────
      tagList(
        card(
          card_header("Transcript workflow"),
          card_body(
            uiOutput(ns("meeting_choice_ui")),
            fileInput(ns("transcript_file"), "Attach transcript (.txt / .md)",
                      multiple = FALSE, accept = c(".txt", ".md")),
            div(class = "action-row",
              actionButton(ns("transcribe_meeting"), tagList(icon("microphone-lines"), " Import transcript"), class = "btn-outline-secondary"),
              actionButton(ns("extract_structure"), tagList(icon("list-check"), " Extract structure"), class = "btn-outline-secondary")
            ),
            textOutput(ns("transcript_status")),
            textOutput(ns("structure_status"))
          )
        ),

        card(
          card_header(tagList(icon("brain"), "  Meeting intelligence")),
          card_body(
            uiOutput(ns("meeting_intel_ui"))
          )
        )
      )
    ),

    # ── Meeting timeline ───────────────────────────────────────────
    card(
      card_header("Meeting timeline"),
      card_body(class = "card-scroll", uiOutput(ns("meeting_timeline")))
    ),

    # ── Person directory ───────────────────────────────────────────
    card(
      card_header(tagList(icon("users"), "  Person directory")),
      card_body(
        div(class = "action-row",
          textInput(ns("new_person_name"), NULL, placeholder = "Add person name..."),
          textInput(ns("new_person_role"), NULL, placeholder = "Role..."),
          actionButton(ns("add_person"), tagList(icon("plus"), " Add"), class = "btn-sm btn-outline-secondary")
        ),
        tableOutput(ns("person_table"))
      )
    )
  )
}

meetings_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh_trigger     <- reactiveVal(0L)
    import_status       <- reactiveVal("")
    transcript_status   <- reactiveVal("")
    structure_status    <- reactiveVal("")

    output$meeting_choice_ui <- renderUI({
      refresh_trigger()
      selectInput(ns("meeting_choice"), "Select meeting", choices = meeting_choices(paths))
    })

    # ── KPIs ───────────────────────────────────────────────────────
    output$meeting_count    <- renderText({
      refresh_trigger()
      db_scalar(paths, "SELECT COUNT(*) FROM meetings")
    })
    output$transcript_count <- renderText({
      refresh_trigger()
      safe_count_files(file.path(paths$meetings_root, "transcripts"))
    })
    output$person_count     <- renderText({
      refresh_trigger()
      db_scalar(paths, "SELECT COUNT(*) FROM meeting_persons")
    })
    output$briefing_count   <- renderText({
      refresh_trigger()
      safe_count_files(file.path(paths$meetings_root, "briefings"))
    })

    # ── Import meeting ─────────────────────────────────────────────
    observeEvent(input$import_meeting, {
      req(input$meeting_file)
      result <- tryCatch(
        run_script(
          "import_meeting.R",
          args = c(
            normalizePath(input$meeting_file$datapath, winslash = "/", mustWork = TRUE),
            if (nzchar(input$meeting_title)) input$meeting_title else "Meeting",
            if (nzchar(input$meeting_date)) input$meeting_date else format(Sys.Date()),
            if (nzchar(input$meeting_domain)) input$meeting_domain else "general",
            if (nzchar(input$meeting_project)) input$meeting_project else "general"
          ),
          paths = paths
        ),
        error = function(e) list(status = 1L, output = conditionMessage(e))
      )
      import_status(result$output)

      # Store meeting intelligence metadata
      if (nzchar(input$meeting_attendees)) {
        # Get the last inserted meeting
        last_mtg <- tryCatch(
          db_table(paths, "SELECT meeting_id FROM meetings ORDER BY created_at DESC LIMIT 1"),
          error = function(...) data.frame()
        )
        if (nrow(last_mtg)) {
          update_meeting_intelligence(paths, last_mtg$meeting_id[1L],
                                       attendees = input$meeting_attendees,
                                       meeting_type = input$meeting_type)
          # Track persons
          persons <- trimws(strsplit(input$meeting_attendees, ",")[[1L]])
          for (p in persons) {
            if (nzchar(p)) insert_meeting_person(paths, p)
          }
        }
      }
      refresh_trigger(refresh_trigger() + 1L)
    })

    # ── Transcript + structure ─────────────────────────────────────
    observeEvent(input$transcribe_meeting, {
      req(input$meeting_choice)
      tp <- ""
      if (!is.null(input$transcript_file)) {
        tp <- normalizePath(input$transcript_file$datapath, winslash = "/", mustWork = TRUE)
      }
      result <- tryCatch(
        run_script("transcribe_meeting.R", args = c(input$meeting_choice, tp), paths = paths),
        error = function(e) list(status = 1L, output = conditionMessage(e))
      )
      transcript_status(result$output)
      refresh_trigger(refresh_trigger() + 1L)
    })

    observeEvent(input$extract_structure, {
      req(input$meeting_choice)
      result <- tryCatch(
        run_script("extract_meeting_structure.R", args = c(input$meeting_choice), paths = paths),
        error = function(e) list(status = 1L, output = conditionMessage(e))
      )
      structure_status(result$output)
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$import_status     <- renderText(import_status())
    output$transcript_status <- renderText(transcript_status())
    output$structure_status  <- renderText(structure_status())

    # ── Pre-meeting briefing generator ─────────────────────────────
    observeEvent(input$generate_prebriefing, {
      req(nzchar(input$prebriefing_topic) || nzchar(input$prebriefing_people))
    })

    output$prebriefing_output <- renderUI({
      input$generate_prebriefing
      topic  <- isolate(input$prebriefing_topic)
      people <- isolate(input$prebriefing_people)
      if (is.null(topic) && is.null(people)) return(NULL)
      if (!nzchar(topic) && !nzchar(people)) return(NULL)

      # Gather context from past meetings
      context <- get_meeting_context(paths, project = topic)

      # Search library for relevant articles
      library_hits <- tryCatch({
        if (nzchar(topic)) {
          db_table(paths, sprintf(
            "SELECT basename, phd_article_link FROM library_seeded WHERE LOWER(basename) LIKE '%%%s%%' OR LOWER(COALESCE(relevance_note,'')) LIKE '%%%s%%' LIMIT 5",
            tolower(topic), tolower(topic)
          ))
        } else data.frame()
      }, error = function(...) data.frame())

      # Build briefing
      tagList(
        tags$hr(),
        tags$h6(style = "color:#174c4f;", tagList(icon("file-lines"), "  Pre-meeting context")),

        if (nrow(context)) {
          tagList(
            tags$p(style = "font-size:0.78rem; color:#6d7c74;",
                   sprintf("%d related past meeting(s):", nrow(context))),
            tags$ul(style = "font-size:0.84rem; padding-left:1.1em;",
              lapply(seq_len(min(nrow(context), 5L)), function(i) {
                m <- context[i, ]
                tags$li(
                  tags$strong(m$title),
                  tags$span(style = "color:#888; font-size:0.78rem;",
                            paste0(" (", m$meeting_date, ")")),
                  if (nzchar(m$decisions))
                    tags$span(style = "color:#2e6b4f; font-size:0.78rem;", " [has decisions]"),
                  if (nzchar(m$action_items))
                    tags$span(style = "color:#b36a1d; font-size:0.78rem;", " [has action items]")
                )
              })
            )
          )
        } else {
          tags$p(style = "color:#888; font-size:0.84rem;", "No past meetings found for this topic.")
        },

        if (nrow(library_hits)) {
          tagList(
            tags$p(style = "font-size:0.78rem; color:#6d7c74; margin-top:0.5rem;",
                   sprintf("%d relevant library article(s):", nrow(library_hits))),
            tags$ul(style = "font-size:0.84rem; padding-left:1.1em;",
              lapply(seq_len(nrow(library_hits)), function(i) {
                tags$li(library_hits$basename[i],
                        if ("phd_article_link" %in% names(library_hits) && !is.na(library_hits$phd_article_link[i]))
                          tags$span(class = "gallery-card-bucket", library_hits$phd_article_link[i]))
              })
            )
          )
        }
      )
    })

    # ── Meeting intelligence panel ─────────────────────────────────
    output$meeting_intel_ui <- renderUI({
      refresh_trigger()
      req(input$meeting_choice)
      mtg <- tryCatch(
        db_table(paths, sprintf(
          "SELECT * FROM meetings WHERE meeting_id = '%s'", input$meeting_choice
        )),
        error = function(...) data.frame()
      )
      if (!nrow(mtg)) return(div(class = "empty-state", "Select a meeting to see intelligence."))
      m <- mtg[1L, ]

      tagList(
        tags$h6(style = "color:#174c4f;", m$title),
        tags$p(style = "font-size:0.82rem; color:#6d7c74;",
               paste(m$meeting_date, "|", m$domain,
                     if (!is.na(m$meeting_type) && nzchar(m$meeting_type))
                       paste0(" | ", m$meeting_type) else "")),

        if (!is.na(m$attendees) && nzchar(m$attendees)) {
          div(style = "margin-bottom:0.4rem;",
            tags$span(style = "font-size:0.78rem; font-weight:600; color:#174c4f;", "Attendees: "),
            lapply(trimws(strsplit(m$attendees, ",")[[1L]]), function(p) {
              tags$span(class = "meeting-person-chip", p)
            })
          )
        },

        if (!is.na(m$decisions) && nzchar(m$decisions)) {
          div(style = "margin-top:0.4rem;",
            tags$span(style = "font-size:0.78rem; font-weight:600; color:#2e6b4f;", "Decisions: "),
            tags$pre(style = "font-size:0.78rem; white-space:pre-wrap; margin:0.2rem 0;", m$decisions)
          )
        },

        if (!is.na(m$action_items) && nzchar(m$action_items)) {
          div(style = "margin-top:0.4rem;",
            tags$span(style = "font-size:0.78rem; font-weight:600; color:#b36a1d;", "Action items: "),
            tags$pre(style = "font-size:0.78rem; white-space:pre-wrap; margin:0.2rem 0;", m$action_items)
          )
        },

        if (!is.na(m$follow_ups) && nzchar(m$follow_ups)) {
          div(style = "margin-top:0.4rem;",
            tags$span(style = "font-size:0.78rem; font-weight:600; color:#2d6073;", "Follow-ups: "),
            tags$pre(style = "font-size:0.78rem; white-space:pre-wrap; margin:0.2rem 0;", m$follow_ups)
          )
        },

        tags$hr(),
        tags$p(style = "font-size:0.75rem; color:#888;",
               "Tip: Use 'Extract structure' to auto-populate decisions, action items, and follow-ups from the transcript.")
      )
    })

    # ── Meeting timeline ───────────────────────────────────────────
    output$meeting_timeline <- renderUI({
      refresh_trigger()
      meetings <- tryCatch(
        db_table(paths, paste(
          "SELECT meeting_id, title, meeting_date, domain, project,",
          "COALESCE(meeting_type,'') AS meeting_type,",
          "COALESCE(attendees,'') AS attendees,",
          "COALESCE(decisions,'') AS decisions,",
          "COALESCE(action_items,'') AS action_items",
          "FROM meetings ORDER BY meeting_date DESC, created_at DESC LIMIT 20"
        )),
        error = function(...) data.frame()
      )
      if (!nrow(meetings)) return(div(class = "empty-state", "No meetings recorded yet."))

      lapply(seq_len(nrow(meetings)), function(i) {
        m <- meetings[i, ]
        has_decisions <- nzchar(m$decisions)
        has_actions   <- nzchar(m$action_items)

        div(class = "meeting-timeline-item",
          div(class = "meeting-timeline-header",
            tags$strong(m$title),
            tags$span(class = "meeting-timeline-date", m$meeting_date),
            if (nzchar(m$meeting_type))
              tags$span(class = "meeting-type-badge", m$meeting_type)
          ),
          div(class = "meeting-timeline-meta",
            tags$span(style = "font-size:0.78rem; color:#888;", paste0(m$domain, " | ", m$project)),
            if (nzchar(m$attendees))
              tags$span(style = "font-size:0.75rem; color:#6d7c74;",
                        paste0(" | ", m$attendees))
          ),
          div(class = "meeting-timeline-badges",
            if (has_decisions) tags$span(class = "meeting-badge-decisions", tagList(icon("gavel"), "  decisions")),
            if (has_actions)   tags$span(class = "meeting-badge-actions", tagList(icon("list-check"), "  actions"))
          )
        )
      })
    })

    # ── Person directory ───────────────────────────────────────────
    observeEvent(input$add_person, {
      req(nzchar(input$new_person_name))
      insert_meeting_person(paths, input$new_person_name, input$new_person_role)
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$person_table <- renderTable({
      refresh_trigger()
      persons <- get_meeting_persons(paths)
      if (!nrow(persons)) return(data.frame(message = "No people tracked yet.", stringsAsFactors = FALSE))
      persons[, c("name", "role", "last_meeting_date", "meeting_count"), drop = FALSE]
    }, bordered = TRUE, striped = TRUE, spacing = "s")
  })
}
