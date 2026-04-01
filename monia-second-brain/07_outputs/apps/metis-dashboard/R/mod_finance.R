# mod_finance.R
# v5: Financial awareness — short-term headlines + long-term trends.

finance_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Finance"),
      p("Market awareness and trend tracking. Short-term headlines and long-term investment themes.")
    ),

    layout_columns(
      col_widths = c(6, 6),

      # ── Short-term: today's headlines ────────────────────────────
      card(
        card_header(tagList(icon("bolt"), "  Short-term — today's headlines")),
        card_body(uiOutput(ns("short_term_ui")))
      ),

      # ── Long-term: trends ────────────────────────────────────────
      card(
        card_header(tagList(icon("chart-line"), "  Long-term — trends & themes")),
        card_body(uiOutput(ns("long_term_ui")))
      )
    ),

    # ── Add snapshot ───────────────────────────────────────────────
    card(
      card_header("Add finance snapshot"),
      card_body(
        layout_columns(
          col_widths = c(3, 3, 3, 3),
          textInput(ns("snap_date"), "Date", value = format(Sys.Date())),
          selectInput(ns("snap_category"), "Category",
                      choices = c("market_index", "sector", "theme", "currency", "crypto")),
          textInput(ns("snap_label"), "Label (e.g., 'AI Investments')"),
          selectInput(ns("snap_trend"), "Trend", choices = c("up", "down", "stable"))
        ),
        layout_columns(
          col_widths = c(6, 6),
          textInput(ns("snap_headline"), "Headline"),
          textInput(ns("snap_detail"), "Detail / context")
        ),
        layout_columns(
          col_widths = c(6, 6),
          uiOutput(ns("snap_project_ui")),
          div(class = "action-row", style = "margin-top:1.6rem;",
            actionButton(ns("save_snapshot"), tagList(icon("bookmark"), " Save snapshot"),
                         class = "btn-primary"))
        ),
        textOutput(ns("snap_status"))
      )
    ),

    # ── Watchlist ──────────────────────────────────────────────────
    card(
      card_header(tagList(icon("eye"), "  Watchlist")),
      card_body(
        div(class = "action-row",
          textInput(ns("watch_label"), NULL, placeholder = "Add theme to watch..."),
          selectInput(ns("watch_category"), NULL,
                      choices = c("theme", "sector", "market_index", "currency"),
                      width = "140px"),
          actionButton(ns("add_watch"), tagList(icon("plus"), " Watch"), class = "btn-sm btn-outline-secondary")
        ),
        tableOutput(ns("watchlist_table"))
      )
    ),

    # ── Project connections ────────────────────────────────────────
    card(
      card_header(tagList(icon("link"), "  Project connections")),
      card_body(uiOutput(ns("project_connections_ui")))
    )
  )
}

finance_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh_trigger <- reactiveVal(0L)
    snap_status     <- reactiveVal("")

    output$snap_project_ui <- renderUI({
      selectInput(ns("snap_project"), "Link to project",
                  choices = c("—" = "", project_choices(paths)))
    })

    # ── Short-term view ────────────────────────────────────────────
    output$short_term_ui <- renderUI({
      refresh_trigger()
      today <- get_finance_today(paths)
      market_news <- tryCatch(
        news_by_domain(paths, "markets", n = 5L),
        error = function(...) data.frame()
      )

      items <- list()

      if (nrow(today)) {
        items <- c(items, lapply(seq_len(nrow(today)), function(i) {
          s <- today[i, ]
          arrow <- switch(s$trend, up = "\u2191", down = "\u2193", "\u2194")
          col   <- switch(s$trend, up = "#2e6b4f", down = "#c0392b", "#6d7c74")
          div(class = "finance-card",
            div(class = "finance-card-header",
              tags$span(style = paste0("color:", col, "; font-weight:700; font-size:1.1rem;"), arrow),
              tags$strong(s$label),
              tags$span(class = "finance-category-badge", s$category)
            ),
            tags$p(class = "finance-card-headline", s$headline),
            if (!is.na(s$detail) && nzchar(s$detail))
              tags$p(class = "finance-card-detail", s$detail)
          )
        }))
      }

      if (nrow(market_news)) {
        items <- c(items, lapply(seq_len(nrow(market_news)), function(i) {
          b <- market_news[i, ]
          div(class = "finance-card finance-card-news",
            tags$span(class = paste0("signal-", b$signal_strength), b$signal_strength),
            tags$strong(style = "margin-left:0.4em;", b$title),
            if (nzchar(b$summary)) tags$p(class = "finance-card-detail", b$summary)
          )
        }))
      }

      if (!length(items)) {
        return(div(class = "empty-state", "No market data today. Add a snapshot or news brief."))
      }
      div(class = "finance-list-stack", items)
    })

    # ── Long-term view ─────────────────────────────────────────────
    output$long_term_ui <- renderUI({
      refresh_trigger()
      trends <- get_finance_trends(paths, days = 90L)
      if (!nrow(trends)) {
        return(div(class = "empty-state",
               "No trend data yet. Add finance snapshots over time."))
      }

      # Group by label
      labels <- unique(trends$label)
      lapply(labels[seq_len(min(length(labels), 8L))], function(lbl) {
        t <- trends[trends$label == lbl, , drop = FALSE]
        latest <- t[1L, ]
        arrow <- switch(latest$trend, up = "\u2191", down = "\u2193", "\u2194")
        col   <- switch(latest$trend, up = "#2e6b4f", down = "#c0392b", "#6d7c74")
        count <- nrow(t)

        div(class = "finance-trend-item",
          div(class = "finance-trend-header",
            tags$span(style = paste0("color:", col, "; font-weight:700;"), arrow),
            tags$strong(lbl),
            tags$span(class = "finance-category-badge", latest$category),
            tags$span(style = "font-size:0.72rem; color:#888;",
                      paste0(count, " snapshot(s)"))
          ),
          tags$p(class = "finance-card-headline", latest$headline)
        )
      })
    })

    # ── Save snapshot ──────────────────────────────────────────────
    observeEvent(input$save_snapshot, {
      req(nzchar(input$snap_label), nzchar(input$snap_headline))
      insert_finance_snapshot(
        paths, input$snap_date, input$snap_category, input$snap_label,
        input$snap_headline, input$snap_detail, input$snap_trend,
        input$snap_project
      )
      snap_status(sprintf("Saved: %s", input$snap_label))
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$snap_status <- renderText(snap_status())

    # ── Watchlist ──────────────────────────────────────────────────
    observeEvent(input$add_watch, {
      req(nzchar(input$watch_label))
      insert_finance_watchlist(paths, input$watch_category, input$watch_label)
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$watchlist_table <- renderTable({
      refresh_trigger()
      wl <- get_finance_watchlist(paths)
      if (!nrow(wl)) return(data.frame(message = "No items on watchlist.", stringsAsFactors = FALSE))
      wl[, c("category", "label", "notes"), drop = FALSE]
    }, bordered = TRUE, striped = TRUE, spacing = "s")

    # ── Project connections ────────────────────────────────────────
    output$project_connections_ui <- renderUI({
      refresh_trigger()
      linked <- tryCatch(
        db_table(paths, paste(
          "SELECT label, headline, trend, project_link FROM finance_snapshots",
          "WHERE project_link IS NOT NULL AND project_link != '' AND project_link != '—'",
          "ORDER BY snapshot_date DESC LIMIT 10"
        )),
        error = function(...) data.frame()
      )
      if (!nrow(linked)) {
        return(div(class = "empty-state",
               "No finance items linked to projects yet. Add a project link when saving snapshots."))
      }

      tags$ul(style = "padding-left:1.1em;",
        lapply(seq_len(nrow(linked)), function(i) {
          l <- linked[i, ]
          arrow <- switch(l$trend, up = "\u2191", down = "\u2193", "\u2194")
          tags$li(style = "margin-bottom:0.3rem; font-size:0.85rem;",
            tags$strong(l$label), " ", arrow, " ",
            tags$span(l$headline),
            tags$span(class = "news-project-chip", paste0("-> ", l$project_link))
          )
        })
      )
    })
  })
}
