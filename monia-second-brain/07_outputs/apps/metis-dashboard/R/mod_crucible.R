# mod_crucible.R
# The Crucible: file intake, analysis, and PKM integration.
# Drop any file — Metis analyzes it, links it, and integrates it into the knowledge base.

crucible_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Crucible"),
      p("Drop a file here. Metis will analyze it, link it to your projects and library, and extract ideas and tasks.")
    ),

    layout_columns(
      col_widths = c(5, 7),

      # ── Left: intake form ────────────────────────────────────────
      card(
        card_header("Intake"),
        card_body(
          fileInput(ns("file_upload"), "Upload file",
                    accept = c(".pdf", ".csv", ".txt", ".md", ".docx", ".xlsx", ".R", ".py", ".html"),
                    placeholder = "PDF, CSV, TXT, DOCX, MD, R, ..."),

          selectInput(ns("analysis_type"), "What is this?",
                      choices = c(
                        "Literature / paper"   = "literature",
                        "Data file"            = "data",
                        "Meeting notes"        = "meeting",
                        "Conference talk / TED" = "talk",
                        "Report / grey lit"    = "report",
                        "Code / script"        = "code",
                        "Custom"               = "custom"
                      )),

          uiOutput(ns("project_selector")),

          selectInput(ns("phd_article"), "Link to PhD article",
                      choices = c("None" = "", "Article 1" = "article-1",
                                  "Article 2" = "article-2", "Article 3" = "article-3",
                                  "Future work" = "future")),

          selectInput(ns("analysis_depth"), "Analysis depth",
                      choices = c("Quick scan" = "quick",
                                  "Standard review" = "standard",
                                  "Deep analysis" = "deep")),

          selectInput(ns("focus"), "Focus on",
                      choices = c("Everything" = "all",
                                  "Methods" = "methods",
                                  "Results / findings" = "results",
                                  "Discussion / implications" = "discussion",
                                  "Data quality" = "data_quality",
                                  "Study design" = "study_design")),

          conditionalPanel(
            condition = sprintf("input['%s'] == 'custom'", ns("analysis_type")),
            textAreaInput(ns("custom_instructions"), "Custom analysis instructions",
                          placeholder = "What should Metis look for in this file?",
                          rows = 3L)
          ),

          tags$hr(),
          div(class = "action-row",
            actionButton(ns("submit_intake"), tagList(icon("flask"), " Analyze"),
                         class = "btn-primary"),
            actionButton(ns("clear_form"), tagList(icon("rotate-left"), " Clear"),
                         class = "btn-outline-secondary btn-sm")
          ),
          textOutput(ns("intake_status"))
        )
      ),

      # ── Right: intake history + current analysis ─────────────────
      tagList(
        # Current analysis card
        card(
          card_header("Analysis"),
          card_body(uiOutput(ns("analysis_result")))
        ),

        # History card
        card(
          card_header(
            div(style = "display:flex; justify-content:space-between; align-items:center;",
              span("Intake history"),
              actionButton(ns("refresh_history"), tagList(icon("rotate"), " Refresh"),
                           class = "btn-outline-secondary btn-sm")
            )
          ),
          card_body(class = "card-scroll", uiOutput(ns("intake_history")))
        )
      )
    )
  )
}

crucible_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    intake_status_text <- reactiveVal("")
    current_analysis   <- reactiveVal(NULL)
    refresh_trigger    <- reactiveVal(0L)

    # ── Project dropdown ─────────────────────────────────────────
    output$project_selector <- renderUI({
      choices <- tryCatch(project_choices(paths), error = function(...) character())
      selectInput(ns("project_link"), "Link to project",
                  choices = c("None" = "", choices))
    })

    # ── Clear form ───────────────────────────────────────────────
    observeEvent(input$clear_form, {
      intake_status_text("")
      current_analysis(NULL)
    })

    # ── Submit intake ────────────────────────────────────────────
    observeEvent(input$submit_intake, {
      req(input$file_upload)

      file_info <- input$file_upload
      filename  <- file_info$name
      tmp_path  <- file_info$datapath
      file_ext  <- tolower(tools::file_ext(filename))

      # 1. Copy file to intake storage
      intake_dir <- file.path(paths$second_brain_root, "00_inbox", "crucible")
      if (!dir.exists(intake_dir)) dir.create(intake_dir, recursive = TRUE)
      dest_path <- file.path(intake_dir, filename)
      file.copy(tmp_path, dest_path, overwrite = TRUE)

      # 2. Generate intake ID
      intake_id <- sprintf("intake-%s-%s",
                           format(Sys.time(), "%Y%m%d%H%M%S"),
                           make_slug(tools::file_path_sans_ext(filename)))

      # 3. Record in database
      insert_crucible_intake(
        paths,
        intake_id    = intake_id,
        filename     = filename,
        file_type    = file_ext,
        analysis_type = input$analysis_type,
        project_link  = if (!is.null(input$project_link)) input$project_link else "",
        phd_article   = input$phd_article,
        analysis_depth = input$analysis_depth,
        focus          = input$focus,
        custom_instructions = if (!is.null(input$custom_instructions)) input$custom_instructions else "",
        stored_path   = dest_path
      )

      # 4. Build the analysis prompt for Metis
      agent <- crucible_route_agent(input$analysis_type)
      prompt <- crucible_build_prompt(
        filename    = filename,
        file_type   = file_ext,
        analysis_type = input$analysis_type,
        project     = if (!is.null(input$project_link)) input$project_link else "",
        phd_article = input$phd_article,
        depth       = input$analysis_depth,
        focus       = input$focus,
        custom      = if (!is.null(input$custom_instructions)) input$custom_instructions else ""
      )

      # 5. Display the analysis card with instructions
      current_analysis(list(
        intake_id = intake_id,
        filename  = filename,
        agent     = agent,
        prompt    = prompt,
        dest_path = dest_path,
        status    = "ready"
      ))

      intake_status_text(sprintf("Intake recorded: %s", filename))
      refresh_trigger(refresh_trigger() + 1L)

      log_job(paths, "crucible_intake", "success",
              sprintf("%s [%s] → %s", filename, input$analysis_type, agent$slug))
    })

    output$intake_status <- renderText(intake_status_text())

    # ── Analysis result card ─────────────────────────────────────
    output$analysis_result <- renderUI({
      analysis <- current_analysis()

      if (is.null(analysis)) {
        return(div(class = "empty-state",
          tagList(icon("flask"), "  Upload a file and click Analyze to begin.")
        ))
      }

      # Build the invoke command for Claude Code
      invoke_cmd <- sprintf("/%s Analyze %s — %s",
                            analysis$agent$slug,
                            analysis$filename,
                            substr(analysis$prompt, 1L, 80L))

      copy_js <- sprintf(
        "navigator.clipboard.writeText('%s').then(function(){var b=document.getElementById('%s');b.innerText='Copied!';setTimeout(function(){b.innerText='Copy to Claude Code';},2000);});",
        gsub("'", "\\'", analysis$prompt, fixed = TRUE),
        ns("copy_prompt_btn")
      )

      tagList(
        div(class = "crucible-analysis-card",
          div(class = "crucible-file-header",
            tags$strong(analysis$filename),
            tags$span(class = "crucible-type-badge", analysis$agent$display_name)
          ),

          tags$p(style = "font-size:0.82rem; color:#6d7c74; margin:0.5rem 0;",
                 sprintf("Routed to: %s | Depth: %s | Focus: %s",
                         analysis$agent$display_name,
                         analysis$status,
                         "ready")),

          tags$h6(style = "color:#174c4f; margin-top:0.75rem;", "Analysis prompt"),
          div(style = "max-height:200px; overflow-y:auto; background:#f5f3ee; border-radius:4px; padding:0.5rem 0.75rem; margin-bottom:0.5rem;",
            tags$pre(style = "font-size:0.76rem; white-space:pre-wrap; margin:0; color:#2d3a3e;",
                     analysis$prompt)
          ),

          div(class = "action-row",
            tags$button(
              id = ns("copy_prompt_btn"),
              class = "btn btn-sm btn-primary",
              onclick = copy_js,
              tagList(icon("copy"), "  Copy to Claude Code")
            )
          ),

          tags$p(style = "font-size:0.75rem; color:#6d7c74; margin-top:0.5rem;",
            tagList(
              icon("info-circle"), "  ",
              "Paste this prompt into Claude Code. Metis will analyze the file at: ",
              tags$code(style = "font-size:0.72rem;", analysis$dest_path)
            )
          )
        )
      )
    })

    # ── Intake history ───────────────────────────────────────────
    output$intake_history <- renderUI({
      refresh_trigger()

      intakes <- tryCatch(
        db_table(paths, paste(
          "SELECT intake_id, filename, file_type, analysis_type, project_link,",
          "analysis_depth, status, created_at",
          "FROM crucible_intake ORDER BY created_at DESC LIMIT 20"
        )),
        error = function(...) data.frame()
      )

      if (!nrow(intakes)) {
        return(div(class = "empty-state",
          "No files analyzed yet. Upload your first file above."))
      }

      tagList(lapply(seq_len(nrow(intakes)), function(i) {
        r <- intakes[i, ]
        type_icon <- switch(r$analysis_type,
          literature = "book",
          data       = "database",
          meeting    = "users",
          talk       = "microphone",
          report     = "file-lines",
          code       = "code",
          "file"
        )

        status_class <- switch(r$status,
          complete = "signal-high",
          analyzing = "signal-medium",
          "signal-low"
        )

        div(class = "crucible-history-item",
          div(class = "crucible-history-header",
            icon(type_icon),
            tags$strong(style = "margin-left:0.3em;", r$filename),
            tags$span(class = status_class, style = "margin-left:auto;", r$status)
          ),
          div(class = "crucible-history-meta",
            tags$span(r$analysis_type),
            if (nzchar(r$project_link)) tags$span(class = "news-project-chip", r$project_link),
            tags$span(style = "margin-left:auto; color:#888;", r$created_at)
          )
        )
      }))
    })
  })
}

# ── Route to agent based on analysis type ────────────────────────────────────

crucible_route_agent <- function(analysis_type) {
  routes <- list(
    literature = list(slug = "librarian",         display_name = "Librarian"),
    data       = list(slug = "methods-coach",     display_name = "Methods Coach"),
    meeting    = list(slug = "meeting-memory",    display_name = "Meeting Memory"),
    talk       = list(slug = "librarian",         display_name = "Librarian"),
    report     = list(slug = "librarian",         display_name = "Librarian"),
    code       = list(slug = "software-engineer", display_name = "Software Engineer"),
    custom     = list(slug = "monia",             display_name = "Metis")
  )
  if (analysis_type %in% names(routes)) routes[[analysis_type]] else routes[["custom"]]
}

# ── Build analysis prompt ────────────────────────────────────────────────────

crucible_build_prompt <- function(filename, file_type, analysis_type, project,
                                  phd_article, depth, focus, custom) {
  lines <- character()

  # Header
  lines <- c(lines, sprintf("Analyze this file: %s", filename))
  lines <- c(lines, "")

  # Context
  if (nzchar(project)) lines <- c(lines, sprintf("Project: %s", project))
  if (nzchar(phd_article)) lines <- c(lines, sprintf("PhD article: %s", phd_article))
  lines <- c(lines, sprintf("Analysis depth: %s", depth))
  lines <- c(lines, sprintf("Focus: %s", focus))
  lines <- c(lines, "")

  # Type-specific instructions
  instructions <- switch(analysis_type,
    literature = paste(
      "This is a research paper or article. Please:",
      "1. Extract: authors, year, journal, study design, setting, population",
      "2. Summarize methods and key findings (3-5 bullet points)",
      "3. Assess methodological strengths and limitations",
      "4. Rate relevance to my PhD work (high/medium/low) with justification",
      "5. Identify any research ideas this paper triggers",
      "6. Suggest which library concepts or methods cards this connects to",
      "7. Note any papers cited that I should also read",
      sep = "\n"
    ),
    data = paste(
      "This is a data file. Please:",
      "1. Profile the dataset: rows, columns, data types, completeness",
      "2. Check for quality issues: missing values, outliers, duplicates",
      "3. Describe what this data represents and its temporal/spatial scope",
      "4. Suggest appropriate analysis methods based on the data structure",
      "5. Flag any concerns about the data for epidemiological use",
      sep = "\n"
    ),
    meeting = paste(
      "These are meeting notes. Please:",
      "1. Extract: attendees, date, context",
      "2. List decisions made",
      "3. List action items with owners and deadlines",
      "4. Note unresolved questions",
      "5. Identify follow-up meetings needed",
      "6. Link decisions to active projects",
      sep = "\n"
    ),
    talk = paste(
      "This is a conference talk, TED talk, or presentation transcript. Please:",
      "1. Identify: speaker, event, date, topic",
      "2. Extract the core thesis (1-2 sentences)",
      "3. List the key evidence and methods cited",
      "4. Note implications for public health / epidemiology",
      "5. Identify any research ideas this triggers",
      "6. Rate relevance to my research (high/medium/low)",
      sep = "\n"
    ),
    report = paste(
      "This is a report or grey literature document. Please:",
      "1. Identify: organization, date, scope",
      "2. Summarize key findings and recommendations (5-7 bullet points)",
      "3. Extract any data, statistics, or indicators cited",
      "4. Note policy implications",
      "5. Identify connections to my current projects and research",
      sep = "\n"
    ),
    code = paste(
      "This is a code file or script. Please:",
      "1. Describe what the code does (high-level purpose)",
      "2. Review for correctness and potential bugs",
      "3. Check for performance issues (especially with large datasets)",
      "4. Assess code quality: naming, structure, comments",
      "5. Suggest improvements",
      "6. Flag any security concerns (hardcoded paths, SQL injection, etc.)",
      sep = "\n"
    ),
    # custom
    ""
  )

  if (nzchar(instructions)) lines <- c(lines, instructions)
  if (nzchar(custom)) lines <- c(lines, "", "Additional instructions:", custom)

  # Output instructions
  lines <- c(lines, "", "---",
    "Write output to: 07_outputs/reviews/{agent-slug}/{date}_{filename-slug}.md",
    "Extract any research ideas to the Ideas table.",
    "Create follow-up tasks if action items are found.",
    "Log this analysis with log_agent_run()."
  )

  paste(lines, collapse = "\n")
}

# ── DB insert for crucible intake ────────────────────────────────────────────

insert_crucible_intake <- function(paths, intake_id, filename, file_type,
                                    analysis_type, project_link, phd_article,
                                    analysis_depth, focus, custom_instructions,
                                    stored_path) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  DBI::dbExecute(
    con,
    paste(
      "INSERT INTO crucible_intake",
      "(intake_id, filename, file_type, analysis_type, project_link,",
      "phd_article_link, analysis_depth, focus, custom_instructions,",
      "stored_path, status, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)"
    ),
    params = list(intake_id, filename, file_type, analysis_type, project_link,
                  phd_article, analysis_depth, focus, custom_instructions,
                  stored_path, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(intake_id)
}
