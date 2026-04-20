# mod_meetings.R
# v5: Meeting intelligence — import, transcribe, structure, brief, recommend.

meetings_ui <- function(id) {
  ns <- NS(id)

  tagList(
    tags$head(tags$script(HTML("
var metisMediaRecorder = null;
var metisAudioChunks = [];
var metisRecordTimer = null;
var metisRecordSecs = 0;

function metisStartRecording(nsPrefix) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('Your browser does not support audio recording. Please import a transcript file instead.');
    return;
  }
  navigator.mediaDevices.getUserMedia({audio: true}).then(function(stream) {
    metisAudioChunks = [];
    metisRecordSecs = 0;
    metisMediaRecorder = new MediaRecorder(stream);
    metisMediaRecorder.ondataavailable = function(e) {
      if (e.data.size > 0) metisAudioChunks.push(e.data);
    };
    metisMediaRecorder.onstop = function() {
      stream.getTracks().forEach(function(t) { t.stop(); });
      clearInterval(metisRecordTimer);
      var blob = new Blob(metisAudioChunks, {type: 'audio/webm'});
      var reader = new FileReader();
      reader.onloadend = function() {
        Shiny.setInputValue(nsPrefix + 'audio_data', reader.result, {priority: 'event'});
      };
      reader.readAsDataURL(blob);
      document.getElementById(nsPrefix + 'rec_indicator').style.display = 'none';
      document.getElementById(nsPrefix + 'rec_stopped').style.display = 'block';
    };
    metisMediaRecorder.start(1000);
    metisRecordTimer = setInterval(function() {
      metisRecordSecs++;
      var m = Math.floor(metisRecordSecs / 60);
      var s = metisRecordSecs % 60;
      var el = document.getElementById(nsPrefix + 'rec_duration');
      if (el) el.innerText = m + ':' + (s < 10 ? '0' : '') + s;
    }, 1000);
    Shiny.setInputValue(nsPrefix + 'recording_active', true, {priority: 'event'});
    document.getElementById(nsPrefix + 'rec_indicator').style.display = 'flex';
    document.getElementById(nsPrefix + 'rec_stopped').style.display = 'none';
    document.getElementById(nsPrefix + 'btn_start').style.display = 'none';
    document.getElementById(nsPrefix + 'btn_stop').style.display = 'inline-block';
  }).catch(function(err) {
    alert('Microphone access denied: ' + err.message);
  });
}

function metisStopRecording(nsPrefix) {
  if (metisMediaRecorder && metisMediaRecorder.state !== 'inactive') {
    metisMediaRecorder.stop();
  }
  document.getElementById(nsPrefix + 'btn_start').style.display = 'inline-block';
  document.getElementById(nsPrefix + 'btn_stop').style.display = 'none';
  Shiny.setInputValue(nsPrefix + 'recording_active', false, {priority: 'event'});
}
    "))),

    div(class = "page-intro",
      h1("Meetings"),
      p("Import recordings, extract intelligence, track people, and get pre-meeting briefings.")
    ),

    # ── Mode toggle bar ────────────────────────────────────────────
    div(class = "mode-toggle-bar", style = "margin-bottom:1rem;",
      actionButton(ns("mode_quick"),  tagList(icon("bolt"),                " Quick"),        class = "btn btn-sm"),
      actionButton(ns("mode_auto"),   tagList(icon("wand-magic-sparkles"), " Auto-analyse"), class = "btn btn-sm"),
      actionButton(ns("mode_live"),   tagList(icon("broadcast-tower"),     " Live"),         class = "btn btn-sm"),
      tags$span(style = "margin: 0 0.3rem; color:var(--metis-border);", "|"),
      actionButton(ns("mode_import"), tagList(icon("upload"),              " Import"),       class = "btn btn-sm")
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

    # ── Recording panel (shown when mode != "import") ──────────────
    uiOutput(ns("recording_panel")),

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
          "COALESCE(action_items,'') AS action_items,",
          "COALESCE(transcript_status,'') AS transcript_status",
          "FROM meetings ORDER BY meeting_date DESC, created_at DESC LIMIT 20"
        )),
        error = function(...) data.frame()
      )
      if (!nrow(meetings)) return(div(class = "empty-state", "No meetings recorded yet."))

      lapply(seq_len(nrow(meetings)), function(i) {
        m <- meetings[i, ]
        has_decisions <- nzchar(m$decisions)
        has_actions   <- nzchar(m$action_items)
        ts_status     <- if ("transcript_status" %in% names(m))
          (m$transcript_status %||% "") else ""

        transcribe_btn <- if (ts_status == "pending_transcription" || nzchar(ts_status) == FALSE) {
          # Show transcribe button for pending or un-transcribed recordings
          tags$button(
            class = "btn btn-xs btn-outline-secondary",
            style = "font-size:0.73rem; padding:1px 7px; margin-left:0.25rem;",
            onclick = sprintf(
              "Shiny.setInputValue('%s', '%s', {priority:'event'})",
              ns("transcribe_meeting"), m$meeting_id
            ),
            tagList(icon("waveform-lines"), " Transcribe")
          )
        } else if (ts_status == "complete") {
          tags$span(
            style = "font-size:0.73rem; color:#2e6b4f; margin-left:0.25rem;",
            tagList(icon("check"), " Transcribed")
          )
        } else NULL

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
            if (has_actions)   tags$span(class = "meeting-badge-actions", tagList(icon("list-check"), "  actions")),
            if (!is.null(transcribe_btn)) transcribe_btn
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

    # ── Recording mode tracking ────────────────────────────────────
    meeting_mode <- reactiveVal("import")  # default = existing import view

    observeEvent(input$mode_quick,  meeting_mode("quick"))
    observeEvent(input$mode_auto,   meeting_mode("auto"))
    observeEvent(input$mode_live,   meeting_mode("live"))
    observeEvent(input$mode_import, meeting_mode("import"))

    # ── Recording panel renderer ───────────────────────────────────
    output$recording_panel <- renderUI({
      mode <- meeting_mode()
      if (mode == "import") return(NULL)

      ns_prefix <- session$ns("")

      mode_labels <- list(
        quick = list(label = "Quick",        desc = "Record a quick meeting note — no auto-analysis.",        color = "#0071e3"),
        auto  = list(label = "Auto-analyse", desc = "Record + automatically extract decisions and actions.",  color = "#2e6b4f"),
        live  = list(label = "Live",         desc = "Live meeting mode — transcript streamed in real time.",  color = "#b36a1d")
      )
      info <- mode_labels[[mode]]

      card(
        card_header(tagList(icon("microphone"), sprintf("  %s recording", info$label))),
        card_body(
          div(class = "action-row", style = "align-items:center; flex-wrap:wrap; gap:0.5rem;",
            tags$span(
              style = sprintf(
                "background:%s22; color:%s; border-radius:12px; padding:0.2rem 0.65rem; font-size:0.78rem; font-weight:600;",
                info$color, info$color
              ),
              info$label
            ),
            tags$span(style = "font-size:0.82rem; color:#6d7c74;", info$desc),
            tags$span(style = "margin-left:auto; font-size:0.82rem; color:#6d7c74;",
              "Duration: ",
              tags$span(id = ns("rec_duration"), "0:00")
            ),
            tags$button(
              id = ns("btn_start"),
              class = "btn btn-sm btn-primary",
              onclick = sprintf("metisStartRecording('%s')", ns_prefix),
              tagList(icon("circle"), " Start Recording")
            ),
            tags$button(
              id = ns("btn_stop"),
              class = "btn btn-sm btn-danger",
              style = "display:none;",
              onclick = sprintf("metisStopRecording('%s')", ns_prefix),
              tagList(icon("square"), " Stop Recording")
            )
          ),
          div(
            id = ns("rec_indicator"),
            style = "display:none; align-items:center; gap:0.5rem; margin-top:0.5rem; color:#c0392b; font-size:0.84rem;",
            tags$span(style = "width:10px; height:10px; background:#c0392b; border-radius:50%; display:inline-block;"),
            "Recording in progress..."
          ),
          div(
            id = ns("rec_stopped"),
            style = "display:none; margin-top:0.5rem; color:#2e6b4f; font-size:0.84rem;",
            tagList(icon("check-circle"), " Recording complete. Sending to Shiny...")
          )
        )
      )
    })

    # ── Audio data handler ─────────────────────────────────────────
    observeEvent(input$audio_data, {
      req(input$audio_data)
      mode <- meeting_mode()

      tryCatch({
        raw_data    <- sub("^data:audio/webm;base64,", "", input$audio_data)
        audio_bytes <- base64enc::base64decode(raw_data)

        audio_dir      <- ensure_dir(file.path(paths$meetings_root, "recordings"))
        audio_filename <- sprintf("recording-%s.webm", format(Sys.time(), "%Y%m%d-%H%M%S"))
        audio_path     <- file.path(audio_dir, audio_filename)
        writeBin(audio_bytes, audio_path)

        showModal(modalDialog(
          title = tagList(icon("microphone"), sprintf(" %s recording complete", tools::toTitleCase(mode))),
          size  = "l",
          tagList(
            div(style = "background:var(--metis-gray-light); border-radius:8px; padding:0.75rem; margin-bottom:1rem;",
              tags$p(style = "font-size:0.85rem; margin:0;",
                tagList(icon("file-audio"), " Saved: "),
                tags$code(style = "font-size:0.78rem;", audio_path)
              )
            ),
            layout_columns(
              col_widths = c(6, 6),
              textInput(ns("rec_title"), "Meeting title", value = paste("Meeting", format(Sys.Date()))),
              textInput(ns("rec_date"),  "Date",          value = format(Sys.Date()))
            ),
            layout_columns(
              col_widths = c(6, 6),
              selectInput(ns("rec_type"), "Type",
                choices = c("general", "project_review", "phd_supervision", "strategy", "seminar", "one_on_one")),
              textInput(ns("rec_project"), "Project", value = "general")
            ),
            textInput(ns("rec_attendees"), "Attendees (comma-separated)"),
            tags$hr(),
            div(style = "background:var(--metis-blue-light); border-radius:8px; padding:0.875rem;",
              tags$p(style = "font-weight:600; font-size:0.85rem; color:var(--metis-blue); margin-bottom:0.4rem;",
                tagList(icon("terminal"), " Transcribe with Claude Code")),
              tags$p(style = "font-size:0.82rem; margin-bottom:0.5rem;",
                "Local Whisper is not yet configured. Copy this command to transcribe:"),
              tags$pre(
                style = "font-size:0.78rem; background:white; border-radius:6px; padding:0.6rem;",
                sprintf(
                  "/meeting-memory Transcribe and analyse this meeting recording.\nFile: %s\nMode: %s\nSave transcript to: %s\nExtract: decisions, action items, attendees, key topics.",
                  audio_path,
                  mode,
                  file.path(paths$meetings_root, "transcripts", sub("\\.webm$", ".txt", audio_filename))
                )
              )
            ),
            div(class = "action-row", style = "margin-top:0.75rem;",
              actionButton(ns("save_recording_meta"), tagList(icon("save"), " Save meeting record"),
                           class = "btn-primary"),
              modalButton("Cancel")
            )
          ),
          easyClose = FALSE,
          footer    = NULL
        ))
      }, error = function(e) {
        showModal(modalDialog(
          title = "Recording received",
          tagList(
            tags$p("Recording captured but could not be saved automatically."),
            tags$p(style = "font-size:0.84rem; color:var(--metis-text-muted);",
              "Install base64enc: "),
            tags$code("install.packages('base64enc')"),
            tags$p("Then use the Import tab to upload the recording file instead.")
          ),
          easyClose = TRUE,
          footer    = modalButton("Close")
        ))
      })
    }, ignoreNULL = TRUE)

    # ── Save recording metadata ────────────────────────────────────
    observeEvent(input$save_recording_meta, {
      removeModal()
      tryCatch({
        meeting_id <- sprintf("mtg-%s", format(Sys.time(), "%Y%m%d%H%M%S"))
        con <- connect_db(paths)
        on.exit(DBI::dbDisconnect(con), add = TRUE)
        DBI::dbExecute(con, paste(
          "INSERT OR IGNORE INTO meetings",
          "(meeting_id, title, meeting_date, domain, project,",
          " meeting_type, attendees, transcript_status, created_at)",
          "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ), params = list(
          meeting_id,
          if (!is.null(input$rec_title)    && nzchar(input$rec_title))    input$rec_title    else paste("Meeting", format(Sys.Date())),
          if (!is.null(input$rec_date)     && nzchar(input$rec_date))     input$rec_date     else format(Sys.Date()),
          "general",
          if (!is.null(input$rec_project)) input$rec_project else "general",
          if (!is.null(input$rec_type))    input$rec_type    else "general",
          if (!is.null(input$rec_attendees)) input$rec_attendees else "",
          "pending_transcription",
          format(Sys.time(), "%Y-%m-%d %H:%M:%S")
        ))
        title_val <- if (!is.null(input$rec_title) && nzchar(input$rec_title)) input$rec_title else "untitled"
        log_job(paths, "record_meeting", "success", title_val)
        refresh_trigger(refresh_trigger() + 1L)
        showNotification("Meeting record saved. Use Claude Code to transcribe.", type = "message", duration = 4L)
      }, error = function(e) {
        showNotification(paste("Error saving:", conditionMessage(e)), type = "error")
      })
    })

    # ── Transcribe button handler ─────────────────────────────────
    observeEvent(input$transcribe_meeting, {
      req(input$transcribe_meeting)
      meeting_id <- input$transcribe_meeting
      meeting <- tryCatch(
        db_table(paths, sprintf(
          "SELECT title, stored_audio_path FROM meetings WHERE meeting_id = '%s'", meeting_id
        )),
        error = function(...) data.frame()
      )
      title_str  <- if (nrow(meeting)) meeting$title[1L] else meeting_id
      audio_path <- if (nrow(meeting) && !is.na(meeting$stored_audio_path[1L]))
        meeting$stored_audio_path[1L] else ""

      cmd <- sprintf(
        "Call MCP tool:\n  transcribe_recording(\"%s\")\n\nOr run from Claude Code:\n  /metis transcribe meeting \"%s\"",
        meeting_id, title_str
      )

      showModal(modalDialog(
        title = tagList(icon("waveform-lines"), " Transcribe: ", title_str),
        tagList(
          if (nzchar(audio_path)) {
            tags$p(style = "font-size:0.84rem;",
                   tagList(icon("file-audio"), "  Audio: "),
                   tags$code(audio_path))
          } else {
            div(
              class = "empty-state",
              icon("triangle-exclamation"),
              tags$p("No audio file linked to this meeting record."),
              tags$p(style = "font-size:0.82rem; color:#888;",
                     "Audio is saved when you record via the Live/Auto/Quick modes.")
            )
          },
          tags$hr(),
          tags$p(style = "font-size:0.84rem; font-weight:600;",
                 "Run transcription from Claude Code or Claude Desktop:"),
          tags$pre(
            style = "background:#f5f5f5; border-radius:4px; padding:0.6rem; font-size:0.78rem;",
            cmd
          ),
          tags$p(style = "font-size:0.8rem; color:#888;",
                 "Requires: openai-whisper (pip install openai-whisper). ",
                 "Optional: pyannote.audio + HF_TOKEN for speaker labels.")
        ),
        footer = modalButton("Close")
      ))
    }, ignoreNULL = TRUE)
  })
}
