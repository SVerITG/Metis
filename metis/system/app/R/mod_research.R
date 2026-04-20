# mod_research.R
# Research: thesis spine, article evidence map, milestone timeline, and bucket progress.

research_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Research"),
      p("Thesis spine, article alignment, milestone timeline, and evidence coverage.")
    ),

    # ── Active articles + Scan for updates ─────────────────────────
    card(
      card_header(
        div(style = "display:flex; justify-content:space-between; align-items:center;",
          span(tagList(icon("file-word"), "  Active research documents")),
          actionButton(ns("scan_updates"), tagList(icon("rotate"), " Scan for updates"),
                       class = "btn btn-sm btn-primary")
        )
      ),
      card_body(
        uiOutput(ns("scan_results")),
        uiOutput(ns("active_articles"))
      )
    ),

    layout_columns(
      col_widths = c(5, 7),

      # ── Left: thesis spine + focus ──────────────────────────────
      tagList(
        card(
          card_header("Thesis spine — central document"),
          card_body(style = "font-family:'IBM Plex Serif',serif; font-size:0.88rem;",
                    verbatimTextOutput(ns("central_doc"))),
        ),
        card(
          card_header("Current focus areas"),
          card_body(tags$ul(style = "padding-left:1.2em; font-size:0.9rem;",
            tags$li(tags$strong("Backbone: "),
                    "Elimination and post-elimination surveillance logic."),
            tags$li(tags$strong("Methods: "),
                    "Multilevel analysis, SaTScan spatial scan statistics."),
            tags$li(tags$strong("Three in-progress: "),
                    "Align all to the backbone before submitting."),
            tags$li(tags$strong("Future papers: "),
                    "Track via milestones below — connected to the spine.")
          ))
        )
      ),

      # ── Right: evidence map ─────────────────────────────────────
      card(
        card_header("Article evidence map — bucket coverage"),
        card_body(uiOutput(ns("evidence_progress")))
      )
    ),

    # ── Milestone timeline ──────────────────────────────────────────
    card(
      card_header(
        div(style = "display:flex; justify-content:space-between; align-items:center;",
          span(tagList(icon("timeline"), "  Article milestone timeline")),
          actionButton(ns("show_add_milestone"), tagList(icon("plus"), " Add milestone"),
                       class = "btn btn-sm btn-outline-secondary")
        )
      ),
      card_body(
        # Add form (hidden by default, toggled)
        uiOutput(ns("milestone_form")),
        uiOutput(ns("milestone_timeline"))
      )
    ),

    # ── Bucket detail table ─────────────────────────────────────────
    card(
      card_header("Research article bucket — count table"),
      card_body(tableOutput(ns("bucket_summary")))
    )
  )
}

research_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ms_refresh   <- reactiveVal(0L)
    show_form    <- reactiveVal(FALSE)
    save_status  <- reactiveVal("")

    observeEvent(input$show_add_milestone, show_form(!show_form()))

    # ── Milestone form ──────────────────────────────────────────────
    output$milestone_form <- renderUI({
      if (!show_form()) return(NULL)
      ns <- session$ns
      div(style = "background:#f5f3ee; border-radius:5px; padding:0.75rem; margin-bottom:0.75rem;",
        layout_columns(
          col_widths = c(5, 3, 4),
          textInput(ns("ms_title"), "Article title"),
          textInput(ns("ms_date"),  "Target date (YYYY-MM-DD)"),
          selectInput(ns("ms_status"), "Status",
                      choices = c("planned","in_progress","submitted","in_revision","accepted","published"))
        ),
        textInput(ns("ms_notes"), "Notes (optional)"),
        div(class = "action-row",
          actionButton(ns("save_milestone"), tagList(icon("plus"), " Save milestone"), class = "btn-primary"),
          actionButton(ns("cancel_milestone"), "Cancel", class = "btn-outline-secondary")
        ),
        textOutput(ns("save_status"))
      )
    })

    observeEvent(input$cancel_milestone, show_form(FALSE))

    observeEvent(input$save_milestone, {
      req(nzchar(input$ms_title), nzchar(input$ms_date))
      insert_research_milestone(paths, input$ms_title, input$ms_date,
                                input$ms_status, input$ms_notes)
      ms_refresh(ms_refresh() + 1L)
      save_status(sprintf("Saved: %s", input$ms_title))
      show_form(FALSE)
    })

    output$save_status <- renderText(save_status())

    # ── Timeline ────────────────────────────────────────────────────
    output$milestone_timeline <- renderUI({
      ms_refresh()
      ms <- get_research_milestones(paths)

      if (!nrow(ms)) {
        return(div(class = "empty-state",
          tagList(icon("timeline"), "  No milestones yet. Add your first article target above.")
        ))
      }

      today  <- Sys.Date()
      dates  <- as.Date(ms$target_date)
      d_min  <- min(c(today - 30L, dates))
      d_max  <- max(c(today + 365L, dates))
      d_span <- as.numeric(d_max - d_min)

      status_colour <- function(s) {
        switch(s,
          planned     = "#6d7c74",
          in_progress = "#b36a1d",
          submitted   = "#2d6073",
          in_revision = "#7b4f2e",
          accepted    = "#2e6b4f",
          published   = "#174c4f",
          "#888"
        )
      }

      # Today marker
      today_pct <- round((as.numeric(today - d_min) / d_span) * 100L)

      milestone_nodes <- lapply(seq_len(nrow(ms)), function(i) {
        d   <- as.Date(ms$target_date[i])
        pct <- round((as.numeric(d - d_min) / d_span) * 100L)
        col <- status_colour(ms$status[i])

        div(
          class = paste0("research-milestone milestone-", ms$status[i]),
          style = sprintf("left: %d%%; top: calc(50%% - 30px);", pct),
          div(class = "research-milestone-dot",
              style = paste0("background:", col, "; box-shadow: 0 0 0 2px ", col, ";")),
          div(class = "research-milestone-label", ms$article_title[i]),
          div(class = "research-milestone-date", format(d, "%b %Y")),
          if (!is.na(ms$status[i])) {
            tags$span(
              style = paste0("font-size:0.64rem; color:", col, "; font-weight:600;"),
              ms$status[i]
            )
          }
        )
      })

      # Today line
      today_marker <- div(
        style = sprintf(
          paste0("position:absolute; left:%d%%; top:calc(50%% - 20px);",
                 "display:flex; flex-direction:column; align-items:center;"),
          today_pct
        ),
        div(style = paste0(
          "width:2px; height:40px; background:#b36a1d;",
          "margin-bottom:3px;"
        )),
        tags$span(style = "font-size:0.66rem; color:#b36a1d; font-weight:600; white-space:nowrap;",
                  "Today")
      )

      div(
        style = "overflow-x:auto;",
        div(class = "research-timeline-wrap",
          div(class = "research-timeline-axis"),
          today_marker,
          milestone_nodes
        ),
        # Legend
        div(style = "display:flex; flex-wrap:wrap; gap:0.5rem; margin-top:0.5rem; font-size:0.75rem;",
          lapply(
            c("planned","in_progress","submitted","in_revision","accepted","published"),
            function(s) {
              col <- status_colour(s)
              div(style = "display:flex; align-items:center; gap:0.3rem;",
                div(style = sprintf("width:10px;height:10px;border-radius:50%;background:%s;", col)),
                s
              )
            }
          )
        )
      )
    })

    # ── Thesis spine ────────────────────────────────────────────────
    output$central_doc <- renderText({
      doc_path <- file.path(paths$research_root, "00_center", "README.md")
      lines <- safe_read_lines(doc_path, n = 40L)
      if (!length(lines)) {
        return(paste(
          "No central research document found yet.",
          "", "Create: 03_domains/research/00_center/README.md",
          "", "Include: thesis title, backbone statement, links to three in-progress articles.",
          sep = "\n"
        ))
      }
      paste(lines, collapse = "\n")
    })

    # ── Evidence progress ───────────────────────────────────────────
    output$evidence_progress <- renderUI({
      buckets <- article_bucket_summary(paths)
      if (!nrow(buckets)) {
        return(div(class = "empty-state",
          tagList(icon("folder-open"), "  No seeded articles yet. Run a Library scan first.")))
      }

      total   <- sum(buckets$count)
      max_cnt <- max(buckets$count)
      palette <- c("#174c4f","#2d6073","#2e6b4f","#b36a1d","#7b4f2e",
                   "#5c3d8f","#8f3d3d","#3d6e4e","#4e5c8f","#8f7b3d")

      tagList(
        tags$p(style = "font-size:0.82rem; color:#6d7c74; margin-bottom:1rem;",
               sprintf("Total seeded: %d articles across %d buckets", total, nrow(buckets))),
        lapply(seq_len(nrow(buckets)), function(i) {
          col <- palette[((i - 1L) %% length(palette)) + 1L]
          pct <- round(buckets$count[i] / max_cnt * 100L)
          pct_total <- round(buckets$count[i] / total * 100L)
          div(style = "margin-bottom:1em;",
            div(style = "display:flex; justify-content:space-between; align-items:baseline; margin-bottom:3px;",
              tags$strong(style = "font-size:0.87rem;", buckets$bucket[i]),
              div(
                tags$span(style = paste0(
                  "font-size:0.75rem; font-weight:600; color:#fff;",
                  "background:", col, "; padding:1px 7px; border-radius:10px;"),
                  buckets$count[i]),
                tags$span(style = "font-size:0.72rem; color:#888; margin-left:0.4em;",
                          paste0(pct_total, "%"))
              )
            ),
            div(style = "background:#e8e4dc; border-radius:6px; height:10px; overflow:hidden;",
              div(style = sprintf(
                "width:%d%%; height:100%%; background:%s; border-radius:6px;", pct, col))
            )
          )
        })
      )
    })

    output$bucket_summary <- renderTable(
      article_bucket_summary(paths),
      bordered = TRUE, striped = TRUE, spacing = "s"
    )

    # ── Active research documents ───────────────────────────────────
    output$active_articles <- renderUI({
      root <- paths$research_root
      if (!dir.exists(root)) {
        return(div(class = "empty-state",
          tagList(icon("folder-open"), "  Research folder not found: ", tags$code(root))
        ))
      }

      files <- list.files(root, pattern = "\\.(docx|md|txt|Rmd)$",
                          recursive = TRUE, full.names = TRUE)
      if (!length(files)) {
        return(div(class = "empty-state",
          tagList(icon("file"), "  No research documents found in ", tags$code(root))
        ))
      }

      info <- file.info(files)
      info <- info[order(info$mtime, decreasing = TRUE), , drop = FALSE]
      info <- head(info, 15L)

      tagList(
        tags$p(style = "font-size:0.8rem; color:var(--metis-text-muted); margin-bottom:0.5rem;",
               sprintf("%d document%s found", length(files), if (length(files) == 1L) "" else "s")),
        lapply(rownames(info), function(f) {
          fname   <- basename(f)
          relpath <- sub(paste0("^", normalizePath(root, winslash = "/", mustWork = FALSE), "/?"), "", f)
          mtime   <- format(file.info(f)$mtime, "%Y-%m-%d %H:%M")
          ext     <- tolower(tools::file_ext(fname))
          icon_name <- switch(ext, docx = "file-word", md = "file-lines",
                              rmd = "file-code", "file")

          div(class = "scan-result-row",
            div(style = "display:flex; align-items:center; gap:0.4rem;",
              icon(icon_name, style = "color:var(--metis-blue);"),
              tags$span(style = "font-weight:500;", fname),
              tags$span(style = "font-size:0.75rem; color:var(--metis-text-muted);",
                        relpath)
            ),
            div(style = "display:flex; align-items:center; gap:0.5rem;",
              tags$span(class = "scan-unchanged", mtime),
              if (ext == "docx") {
                tags$button(
                  class = "btn btn-xs btn-outline-secondary",
                  onclick = sprintf("Shiny.setInputValue('%s', '%s', {priority:'event'})",
                                    session$ns("open_doc"), f),
                  tagList(icon("up-right-from-square"), " Open")
                )
              }
            )
          )
        })
      )
    })

    # ── Scan for updates ────────────────────────────────────────────
    scan_trigger <- reactiveVal(0L)

    observeEvent(input$scan_updates, scan_trigger(scan_trigger() + 1L))
    observeEvent(input$open_doc, {
      req(input$open_doc)
      tryCatch(browseURL(paste0("file:///", gsub("\\\\", "/", input$open_doc))),
               error = function(...) NULL)
    })

    output$scan_results <- renderUI({
      if (scan_trigger() == 0L) return(NULL)

      root  <- paths$research_root
      files <- list.files(root, pattern = "\\.(docx|md|txt|Rmd)$",
                          recursive = TRUE, full.names = TRUE)
      if (!length(files)) return(NULL)

      tracked <- tryCatch(
        db_table(paths, "SELECT path, last_modified FROM tracked_files"),
        error = function(...) data.frame(path = character(), last_modified = character())
      )

      now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
      changed_files <- character()

      for (f in files) {
        mtime_str <- format(file.info(f)$mtime, "%Y-%m-%d %H:%M:%S")
        match_row  <- if (nrow(tracked)) tracked[tracked$path == f, , drop = FALSE] else data.frame()
        if (!nrow(match_row) || match_row$last_modified[1L] != mtime_str) {
          changed_files <- c(changed_files, f)
        }
      }

      # Update tracked_files table
      tryCatch({
        con <- connect_db(paths)
        on.exit(DBI::dbDisconnect(con), add = TRUE)
        for (f in files) {
          mtime_str <- format(file.info(f)$mtime, "%Y-%m-%d %H:%M:%S")
          DBI::dbExecute(con,
            "INSERT OR REPLACE INTO tracked_files (path, last_modified, last_scanned) VALUES (?, ?, ?)",
            params = list(f, mtime_str, now))
        }
      }, error = function(...) NULL)

      if (!length(changed_files)) {
        return(div(style = "background:var(--metis-gray-light); border-radius:8px; padding:0.6rem 0.875rem; margin-bottom:0.5rem; font-size:0.85rem;",
          tagList(icon("check", style = "color:var(--metis-green);"), " All documents unchanged since last scan.")
        ))
      }

      div(style = "background:#fff8e6; border:1px solid rgba(245,159,0,0.3); border-radius:8px; padding:0.6rem 0.875rem; margin-bottom:0.5rem;",
        tags$p(style = "font-weight:600; font-size:0.85rem; color:var(--metis-amber); margin-bottom:0.4rem;",
               tagList(icon("triangle-exclamation"), sprintf(" %d document%s changed since last scan",
                       length(changed_files), if (length(changed_files) == 1L) "" else "s"))),
        tags$ul(style = "margin:0; padding-left:1.2em; font-size:0.82rem;",
          lapply(changed_files, function(f) tags$li(basename(f)))
        )
      )
    })
  })
}
