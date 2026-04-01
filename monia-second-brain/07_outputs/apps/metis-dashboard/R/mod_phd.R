# mod_phd.R
# PhD thesis spine, article evidence map, milestone timeline, and bucket progress.

phd_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("PhD"),
      p("Thesis spine, article alignment, milestone timeline, and evidence coverage.")
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
      card_header("PhD article bucket — count table"),
      card_body(tableOutput(ns("bucket_summary")))
    )
  )
}

phd_server <- function(id, paths) {
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
      insert_phd_milestone(paths, input$ms_title, input$ms_date,
                           input$ms_status, input$ms_notes)
      ms_refresh(ms_refresh() + 1L)
      save_status(sprintf("Saved: %s", input$ms_title))
      show_form(FALSE)
    })

    output$save_status <- renderText(save_status())

    # ── Timeline ────────────────────────────────────────────────────
    output$milestone_timeline <- renderUI({
      ms_refresh()
      ms <- get_phd_milestones(paths)

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
          class = paste0("phd-milestone milestone-", ms$status[i]),
          style = sprintf("left: %d%%; top: calc(50%% - 30px);", pct),
          div(class = "phd-milestone-dot",
              style = paste0("background:", col, "; box-shadow: 0 0 0 2px ", col, ";")),
          div(class = "phd-milestone-label", ms$article_title[i]),
          div(class = "phd-milestone-date", format(d, "%b %Y")),
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
        div(class = "phd-timeline-wrap",
          div(class = "phd-timeline-axis"),
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
      doc_path <- file.path(paths$phd_root, "00_center", "README.md")
      lines <- safe_read_lines(doc_path, n = 40L)
      if (!length(lines)) {
        return(paste(
          "No central thesis document found yet.",
          "", "Create: 03_domains/phd/00_center/README.md",
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
  })
}
