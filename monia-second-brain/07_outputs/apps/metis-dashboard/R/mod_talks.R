# mod_talks.R
# Talks and conferences: log talks, store transcripts, and prepare analysis handoffs.

talks_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Talks"),
      p("Track conference sessions, TED talks, webinars, and podcasts. Store transcripts, capture takeaways, and route talks into Metis workflows.")
    ),

    layout_columns(
      col_widths = c(3, 3, 3, 3),
      value_box(title = "Talks", value = textOutput(ns("talk_count")),
                showcase = icon("microphone-lines"), theme = "primary"),
      value_box(title = "Transcripts", value = textOutput(ns("transcript_count")),
                showcase = icon("file-lines"), theme = "info"),
      value_box(title = "Structured notes", value = textOutput(ns("note_count")),
                showcase = icon("book-open"), theme = "success"),
      value_box(title = "Sources", value = textOutput(ns("source_count")),
                showcase = icon("tower-broadcast"), theme = "warning")
    ),

    layout_columns(
      col_widths = c(5, 7),
      tagList(
        card(
          card_header("Log talk or webinar"),
          card_body(
            textInput(ns("talk_title"), "Title"),
            layout_columns(
              col_widths = c(6, 6),
              textInput(ns("talk_speaker"), "Speaker"),
              selectInput(ns("talk_source"), "Source",
                          choices = c("conference", "TED", "webinar", "podcast", "seminar", "other"))
            ),
            layout_columns(
              col_widths = c(6, 6),
              textInput(ns("talk_event"), "Event / series", placeholder = "ASTMH 2025, TED Global Health, WHO webinar"),
              textInput(ns("talk_date"), "Date", value = format(Sys.Date()))
            ),
            textInput(ns("talk_url"), "URL", placeholder = "https://..."),
            layout_columns(
              col_widths = c(6, 6),
              selectInput(ns("talk_domain"), "Domain",
                          choices = c("Epidemiology", "Biostatistics", "Surveillance",
                                      "Spatial", "NTDs", "PH systems")),
              uiOutput(ns("talk_project_ui"))
            ),
            fileInput(ns("talk_transcript"), "Transcript or notes file",
                      multiple = FALSE, accept = c(".txt", ".md", ".pdf", ".docx")),
            textAreaInput(ns("talk_takeaways"), "Key takeaways",
                          placeholder = "Short notes or why this matters for your work...", rows = 4),
            div(class = "action-row",
              actionButton(ns("save_talk"), tagList(icon("plus"), " Save talk"), class = "btn-primary"),
              actionButton(ns("clear_talk"), tagList(icon("rotate-left"), " Clear"), class = "btn-outline-secondary btn-sm")
            ),
            textOutput(ns("talk_status"))
          )
        ),
        card(
          card_header(tagList(icon("flask"), "  Analysis handoff")),
          card_body(
            uiOutput(ns("talk_choice_ui")),
            div(class = "action-row",
              actionButton(ns("prepare_talk_prompt"), tagList(icon("wand-magic-sparkles"), " Prepare prompt"),
                           class = "btn-outline-secondary")
            ),
            uiOutput(ns("talk_prompt_ui"))
          )
        )
      ),
      tagList(
        card(
          card_header("Recent talks"),
          card_body(class = "card-scroll", uiOutput(ns("talk_timeline_ui")))
        ),
        card(
          card_header("Source guide"),
          card_body(
            tags$ul(style = "margin-bottom:0;",
              tags$li(tags$strong("Conference"), ": sessions from ASTMH, ECTMIH, ESCAIDE, ITM seminars, or similar events."),
              tags$li(tags$strong("TED / webinar"), ": talks with transcripts or detailed notes that can be routed through Crucible."),
              tags$li(tags$strong("Podcast"), ": episodes with research relevance, ideally logged with summary notes or transcript files.")
            ),
            tags$p(style = "font-size:0.8rem; color:#6d7c74; margin-top:0.7rem;",
                   "Use this module for metadata capture and workflow routing. Use Crucible when you want deeper transcript analysis and idea extraction.")
          )
        )
      )
    ),

    card(
      card_header("Talk catalog"),
      card_body(class = "card-scroll", tableOutput(ns("talk_table")))
    )
  )
}

talks_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh_trigger <- reactiveVal(0L)
    talk_status <- reactiveVal("")
    current_prompt <- reactiveVal(NULL)

    talks_root <- file.path(paths$second_brain_root, "05_sources", "talks")
    transcript_root <- file.path(talks_root, "transcripts")

    output$talk_project_ui <- renderUI({
      selectInput(ns("talk_project"), "Project",
                  choices = c("None" = "", project_choices(paths)))
    })

    output$talk_choice_ui <- renderUI({
      refresh_trigger()
      selectInput(ns("talk_choice"), "Select talk", choices = talk_choices(paths))
    })

    talks_data <- reactive({
      refresh_trigger()
      tryCatch(get_talks(paths), error = function(...) data.frame())
    })

    output$talk_count <- renderText({
      nrow(talks_data())
    })

    output$transcript_count <- renderText({
      sum(nzchar(talks_data()$transcript_path))
    })

    output$note_count <- renderText({
      sum(nzchar(talks_data()$structured_note_path))
    })

    output$source_count <- renderText({
      talks <- talks_data()
      if (!nrow(talks)) return(0L)
      length(unique(talks$source))
    })

    observeEvent(input$clear_talk, {
      updateTextInput(session, "talk_title", value = "")
      updateTextInput(session, "talk_speaker", value = "")
      updateTextInput(session, "talk_event", value = "")
      updateTextInput(session, "talk_url", value = "")
      updateTextAreaInput(session, "talk_takeaways", value = "")
      talk_status("")
      current_prompt(NULL)
    })

    observeEvent(input$save_talk, {
      req(nzchar(trimws(input$talk_title)))

      ensure_dir(talks_root)
      ensure_dir(transcript_root)

      transcript_path <- ""
      if (!is.null(input$talk_transcript)) {
        uploaded <- input$talk_transcript
        filename <- paste0(format(Sys.time(), "%Y%m%d%H%M%S"), "-", make_slug(uploaded$name))
        dest_path <- file.path(transcript_root, filename)
        file.copy(uploaded$datapath, dest_path, overwrite = TRUE)
        transcript_path <- dest_path
      }

      talk_id <- insert_talk(
        paths,
        title = trimws(input$talk_title),
        speaker = trimws(input$talk_speaker),
        source = input$talk_source,
        event_name = trimws(input$talk_event),
        talk_date = trimws(input$talk_date),
        url = trimws(input$talk_url),
        transcript_path = transcript_path,
        domain = input$talk_domain,
        project_link = input$talk_project,
        key_takeaways = trimws(input$talk_takeaways)
      )

      talk_status(sprintf("Saved talk: %s", talk_id))
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$talk_status <- renderText(talk_status())

    observeEvent(input$prepare_talk_prompt, {
      req(input$talk_choice)
      talks <- talks_data()
      talk <- talks[talks$talk_id == input$talk_choice, , drop = FALSE]
      req(nrow(talk) == 1L)

      prompt_lines <- c(
        sprintf("Analyze this talk: %s", talk$title[[1L]]),
        "",
        sprintf("Speaker: %s", ifelse(nzchar(talk$speaker[[1L]]), talk$speaker[[1L]], "Unknown")),
        sprintf("Source: %s", talk$source[[1L]]),
        sprintf("Event: %s", ifelse(nzchar(talk$event_name[[1L]]), talk$event_name[[1L]], "Unspecified")),
        sprintf("Date: %s", ifelse(nzchar(talk$talk_date[[1L]]), talk$talk_date[[1L]], "Unspecified")),
        if (nzchar(talk$domain[[1L]])) sprintf("Domain: %s", talk$domain[[1L]]) else NULL,
        if (nzchar(talk$project_link[[1L]])) sprintf("Project link: %s", talk$project_link[[1L]]) else NULL,
        if (nzchar(talk$url[[1L]])) sprintf("URL: %s", talk$url[[1L]]) else NULL,
        if (nzchar(talk$transcript_path[[1L]])) sprintf("Transcript path: %s", talk$transcript_path[[1L]]) else NULL,
        "",
        "Please:",
        "1. Identify the core thesis in 1-2 sentences.",
        "2. Extract the key evidence, examples, and methods cited.",
        "3. Summarize practical implications for epidemiology or public health.",
        "4. Note links to Metis library cards or current projects.",
        "5. Capture research ideas, methodological questions, and follow-up reading.",
        "6. Flag whether this belongs in Crucible for deeper transcript analysis.",
        "",
        "Write output to: 07_outputs/reviews/{agent-slug}/{date}_{talk-slug}.md",
        "Log the run with log_agent_run()."
      )

      current_prompt(paste(prompt_lines, collapse = "\n"))
    })

    output$talk_prompt_ui <- renderUI({
      prompt <- current_prompt()
      if (is.null(prompt) || !nzchar(prompt)) {
        return(NULL)
      }

      copy_js <- sprintf(
        "navigator.clipboard.writeText('%s').then(function(){var b=document.getElementById('%s');b.innerText='Copied!';setTimeout(function(){b.innerText='Copy to Claude Code';},2000);});",
        gsub("'", "\\\\'", prompt),
        ns("copy_talk_prompt_btn")
      )

      div(class = "crucible-analysis-card",
        tags$h6(style = "color:#174c4f; margin-top:0;", "Talk analysis prompt"),
        div(style = "max-height:220px; overflow-y:auto; background:#f5f3ee; border-radius:4px; padding:0.5rem 0.75rem; margin-bottom:0.5rem;",
          tags$pre(style = "font-size:0.76rem; white-space:pre-wrap; margin:0; color:#2d3a3e;", prompt)
        ),
        div(class = "action-row",
          tags$button(
            id = ns("copy_talk_prompt_btn"),
            class = "btn btn-sm btn-primary",
            onclick = copy_js,
            tagList(icon("copy"), "  Copy to Claude Code")
          )
        )
      )
    })

    output$talk_timeline_ui <- renderUI({
      talks <- talks_data()
      if (!nrow(talks)) {
        return(div(class = "empty-state", "No talks logged yet."))
      }

      tagList(lapply(seq_len(min(nrow(talks), 20L)), function(i) {
        talk <- talks[i, ]
        transcript_flag <- if (nzchar(talk$transcript_path)) "Transcript" else "No transcript"
        note_flag <- if (nzchar(talk$structured_note_path)) "Structured note" else NULL
        chips <- c(transcript_flag, note_flag)
        chips <- chips[!is.null(chips) & nzchar(chips)]

        div(class = "meeting-timeline-item",
          div(class = "meeting-timeline-date",
              if (nzchar(talk$talk_date)) talk$talk_date else substr(talk$created_at, 1L, 10L)),
          div(class = "meeting-timeline-content",
            div(class = "meeting-timeline-title",
              talk$title,
              if (nzchar(talk$speaker)) tags$span(style = "font-weight:400; color:#6d7c74;", paste0(" | ", talk$speaker))
            ),
            div(class = "meeting-timeline-detail",
              paste(
                c(
                  if (nzchar(talk$source)) tools::toTitleCase(talk$source) else NULL,
                  if (nzchar(talk$event_name)) talk$event_name else NULL,
                  if (nzchar(talk$domain)) talk$domain else NULL
                ),
                collapse = " | "
              )
            ),
            if (length(chips)) {
              div(class = "meeting-timeline-badges",
                lapply(chips, function(chip) {
                  tags$span(class = "meeting-badge-decisions", chip)
                })
              )
            },
            if (nzchar(talk$key_takeaways)) {
              tags$p(style = "margin:0.35rem 0 0; font-size:0.82rem; color:#1f2a2e;", talk$key_takeaways)
            }
          )
        )
      }))
    })

    output$talk_table <- renderTable({
      talks <- talks_data()
      if (!nrow(talks)) {
        return(data.frame(message = "No talks logged yet.", stringsAsFactors = FALSE))
      }
      talks[, c("talk_date", "title", "speaker", "source", "event_name", "domain", "project_link", "url")]
    }, bordered = TRUE, striped = TRUE, spacing = "s")
  })
}
