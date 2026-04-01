# mod_news.R
# v5: Multi-domain daily intelligence briefing — news synthesis engine.

news_domains <- function() {
  c("geopolitics", "science", "academia", "sleeping sickness",
    "humanitarian", "markets", "AI", "general")
}

news_domain_color <- function(d) {
  switch(tolower(d),
    geopolitics         = "#5c3d8f",
    science             = "#2d6073",
    academia            = "#174c4f",
    "sleeping sickness" = "#2e6b4f",
    humanitarian        = "#c0392b",
    markets             = "#b36a1d",
    ai                  = "#3d6e4e",
    "#6d7c74"
  )
}

signal_col <- function(s) switch(s, high = "#2e6b4f", medium = "#b36a1d", "#6d7c74")
signal_bg  <- function(s) switch(s, high = "#eaf4ee", medium = "#fdf3e7", "#f5f5f5")

news_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("News Intelligence"),
      p("Multi-domain daily briefing. High-signal intelligence across all your domains.")
    ),

    # ── Header: date + domain filters ──────────────────────────────
    card(
      card_body(
        div(class = "news-header-row",
          div(class = "news-date-nav",
            actionButton(ns("date_today"), "Today", class = "btn btn-sm btn-outline-primary"),
            actionButton(ns("date_week"),  "This week", class = "btn btn-sm btn-outline-secondary"),
            textInput(ns("date_from"), NULL, value = format(Sys.Date()), width = "120px")
          ),
          div(class = "news-domain-filters",
            lapply(news_domains(), function(d) {
              tags$button(
                class = "btn btn-xs news-domain-chip",
                style = paste0("border-color:", news_domain_color(d), ";"),
                onclick = sprintf(
                  "Shiny.setInputValue('%s','%s',{priority:'event'})",
                  ns("toggle_domain"), d
                ),
                d
              )
            })
          ),
          div(class = "news-actions",
            actionButton(ns("fetch_feeds"), tagList(icon("rss"), " Fetch"), class = "btn btn-sm btn-outline-secondary"),
            actionButton(ns("add_brief_toggle"), tagList(icon("plus"), " Add"), class = "btn btn-sm btn-outline-secondary")
          )
        )
      )
    ),

    # ── Section 1: Top Signals ─────────────────────────────────────
    card(
      card_header(tagList(icon("bolt"), "  Top signals — high priority")),
      card_body(uiOutput(ns("top_signals_ui")))
    ),

    # ── Section 2: Domain Synthesis Grid ───────────────────────────
    card(
      card_header(tagList(icon("layer-group"), "  Domain synthesis")),
      card_body(uiOutput(ns("domain_grid_ui")))
    ),

    # ── Section 3: Surprise Me ─────────────────────────────────────
    uiOutput(ns("surprise_section")),

    # ── Section 4: Finance section ─────────────────────────────────
    card(
      card_header(tagList(icon("chart-line"), "  Markets & Finance")),
      card_body(
        layout_columns(
          col_widths = c(6, 6),
          div(
            tags$h6(style = "color:#b36a1d; margin-bottom:0.4rem;", "Short-term — today"),
            uiOutput(ns("finance_short_ui"))
          ),
          div(
            tags$h6(style = "color:#174c4f; margin-bottom:0.4rem;", "Long-term — trends"),
            uiOutput(ns("finance_long_ui"))
          )
        )
      )
    ),

    # ── Section 5: Full timeline ───────────────────────────────────
    card(
      card_header(
        div(style = "display:flex; justify-content:space-between; align-items:center;",
          span(tagList(icon("timeline"), "  Full timeline")),
          span(style = "font-size:0.75rem; color:#888;", textOutput(ns("brief_count"), inline = TRUE), " briefs")
        )
      ),
      card_body(class = "card-scroll", uiOutput(ns("brief_timeline")))
    ),

    # ── Collapsible: Add Brief Form ────────────────────────────────
    uiOutput(ns("add_brief_form"))
  )
}

news_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh_trigger <- reactiveVal(0L)
    save_status     <- reactiveVal("")
    show_form       <- reactiveVal(FALSE)
    active_domain   <- reactiveVal(NULL)

    # ── Date navigation ────────────────────────────────────────────
    observeEvent(input$date_today, updateTextInput(session, "date_from", value = format(Sys.Date())))
    observeEvent(input$date_week,  updateTextInput(session, "date_from", value = format(Sys.Date() - 7L)))
    observeEvent(input$toggle_domain, {
      d <- input$toggle_domain
      if (identical(active_domain(), d)) active_domain(NULL) else active_domain(d)
    })
    observeEvent(input$add_brief_toggle, show_form(!show_form()))

    observeEvent(input$fetch_feeds, {
      result <- tryCatch(
        run_script("fetch_news_feeds.R", paths = paths),
        error = function(e) list(status = 1L, output = conditionMessage(e))
      )
      refresh_trigger(refresh_trigger() + 1L)
      showNotification(result$output, type = if (result$status == 0L) "message" else "warning", duration = 3L)
    })

    # ── Top signals ────────────────────────────────────────────────
    output$top_signals_ui <- renderUI({
      refresh_trigger()
      signals <- news_top_signals(paths, input$date_from, n = 5L)
      if (!nrow(signals)) {
        return(div(class = "empty-state", "No high-signal items this period."))
      }
      div(class = "news-top-signals-grid",
        lapply(seq_len(nrow(signals)), function(i) {
          b <- signals[i, ]
          div(class = "news-signal-card",
            style = paste0("border-left: 4px solid ", news_domain_color(b$domain), ";"),
            div(class = "news-signal-domain",
                style = paste0("color:", news_domain_color(b$domain), ";"), b$domain),
            div(class = "news-signal-title", b$title),
            if (nzchar(b$summary)) div(class = "news-signal-summary", b$summary),
            div(class = "news-signal-meta",
              tags$span(b$brief_date),
              if (nzchar(b$project_link)) tags$span(class = "news-project-chip",
                                                     paste0("-> ", b$project_link)),
              if (nzchar(b$tags)) tags$span(class = "news-tags", b$tags)
            )
          )
        })
      )
    })

    # ── Domain synthesis grid ──────────────────────────────────────
    output$domain_grid_ui <- renderUI({
      refresh_trigger()
      date_from <- if (nzchar(input$date_from)) input$date_from else format(Sys.Date() - 7L)
      domains <- news_domains()
      ad <- active_domain()

      if (!is.null(ad)) domains <- ad

      cards <- lapply(domains, function(d) {
        briefs <- news_by_domain(paths, d, n = 4L)
        if (!nrow(briefs)) return(NULL)

        high_n <- sum(briefs$signal_strength == "high")
        col    <- news_domain_color(d)

        div(class = "news-domain-card",
          style = paste0("border-top: 3px solid ", col, ";"),
          div(class = "news-domain-card-header",
            tags$strong(d),
            tags$span(class = "news-domain-count", nrow(briefs)),
            if (high_n > 0L) tags$span(class = "news-domain-high", paste0(high_n, " high"))
          ),
          tags$ul(class = "news-domain-list",
            lapply(seq_len(nrow(briefs)), function(j) {
              b <- briefs[j, ]
              tags$li(
                tags$span(class = paste0("signal-dot signal-dot-", b$signal_strength)),
                tags$span(class = "news-domain-item-title", b$title),
                if (nzchar(b$tags)) tags$span(class = "news-tags-inline", b$tags)
              )
            })
          )
        )
      })
      cards <- Filter(Negate(is.null), cards)

      if (!length(cards)) return(div(class = "empty-state", "No briefs in selected domains."))
      div(class = "news-domain-grid", cards)
    })

    # ── Surprise Me section ────────────────────────────────────────
    output$surprise_section <- renderUI({
      refresh_trigger()
      surprises <- news_surprise_items(paths, n = 3L)
      if (!nrow(surprises)) return(NULL)

      card(
        card_header(
          div(style = "color:#b36a1d;", tagList(icon("lightbulb"), "  Surprise me — things you didn't ask about"))
        ),
        card_body(
          div(class = "news-surprise-grid",
            lapply(seq_len(nrow(surprises)), function(i) {
              b <- surprises[i, ]
              div(class = "news-surprise-card",
                tags$strong(b$title),
                tags$span(class = "news-surprise-domain", b$domain),
                if (!is.na(b$summary) && nzchar(b$summary))
                  tags$p(style = "font-size:0.82rem; color:#4a5a5e; margin:0.2rem 0 0;", b$summary)
              )
            })
          )
        )
      )
    })

    # ── Finance section ────────────────────────────────────────────
    output$finance_short_ui <- renderUI({
      refresh_trigger()
      today_briefs <- news_by_domain(paths, "markets", n = 5L)
      if (!nrow(today_briefs)) return(tags$p(class = "status-info", "No market news today."))
      tags$ul(class = "finance-list",
        lapply(seq_len(nrow(today_briefs)), function(i) {
          b <- today_briefs[i, ]
          tags$li(class = "finance-item",
            tags$strong(b$title),
            tags$span(class = "finance-date", b$brief_date),
            if (nzchar(b$project_link)) tags$span(class = "news-project-chip", paste0("-> ", b$project_link))
          )
        })
      )
    })

    output$finance_long_ui <- renderUI({
      refresh_trigger()
      trends <- get_finance_trends(paths, days = 30L)
      if (!nrow(trends)) return(tags$p(class = "status-info", "No trend data yet. Add finance snapshots."))
      tags$ul(class = "finance-list",
        lapply(seq_len(min(nrow(trends), 6L)), function(i) {
          t <- trends[i, ]
          arrow <- switch(t$trend, up = "\u2191", down = "\u2193", "\u2194")
          col   <- switch(t$trend, up = "#2e6b4f", down = "#c0392b", "#6d7c74")
          tags$li(class = "finance-item",
            tags$span(style = paste0("color:", col, "; font-weight:700;"), arrow),
            tags$strong(t$label),
            tags$span(style = "font-size:0.78rem; color:#888;", t$headline),
            tags$span(class = "finance-date", t$snapshot_date)
          )
        })
      )
    })

    # ── Brief count ────────────────────────────────────────────────
    output$brief_count <- renderText({
      refresh_trigger()
      db_scalar(paths, "SELECT COUNT(*) FROM news_briefs")
    })

    # ── Full timeline ──────────────────────────────────────────────
    output$brief_timeline <- renderUI({
      refresh_trigger()
      date_from <- if (nzchar(input$date_from)) input$date_from else format(Sys.Date() - 30L)
      ad <- active_domain()

      sql <- paste(
        "SELECT brief_id, brief_date, title, domain, signal_strength,",
        "COALESCE(summary,'') AS summary, COALESCE(project_link,'') AS project_link,",
        "COALESCE(tags,'') AS tags, COALESCE(source_url,'') AS source_url,",
        "COALESCE(surprise_flag,0) AS surprise_flag",
        "FROM news_briefs WHERE brief_date >=", sprintf("'%s'", date_from)
      )
      if (!is.null(ad)) sql <- paste0(sql, sprintf(" AND domain = '%s'", ad))
      sql <- paste0(sql, " ORDER BY brief_date DESC, created_at DESC LIMIT 30")

      briefs <- tryCatch(db_table(paths, sql), error = function(...) data.frame())
      if (!nrow(briefs)) return(div(class = "empty-state", "No briefs in this range."))

      lapply(seq_len(nrow(briefs)), function(i) {
        b <- briefs[i, ]
        col <- news_domain_color(b$domain)
        div(class = "news-timeline-item",
          style = paste0("border-left: 3px solid ", col, ";"),
          div(class = "news-timeline-header",
            tags$span(class = "news-timeline-domain", style = paste0("color:", col, ";"), b$domain),
            tags$strong(b$title),
            tags$span(class = "news-timeline-date", b$brief_date)
          ),
          if (nzchar(b$summary)) tags$p(class = "news-timeline-summary", b$summary),
          div(class = "news-timeline-meta",
            tags$span(class = paste0("signal-", b$signal_strength), b$signal_strength),
            if (nzchar(b$project_link)) tags$span(class = "news-project-chip", paste0("-> ", b$project_link)),
            if (nzchar(b$tags)) tags$span(class = "news-tags-inline", b$tags),
            if (nzchar(b$source_url)) tags$a(href = b$source_url, target = "_blank",
                                              class = "news-source-link", tagList(icon("link"), "  source")),
            if (b$surprise_flag == 1L) tags$span(class = "news-surprise-badge", tagList(icon("lightbulb"), "  surprise"))
          )
        )
      })
    })

    # ── Collapsible add brief form ─────────────────────────────────
    output$add_brief_form <- renderUI({
      if (!show_form()) return(NULL)
      card(
        card_header("Add brief"),
        card_body(
          layout_columns(
            col_widths = c(3, 3, 3, 3),
            textInput(ns("brief_date"), "Date", value = format(Sys.Date())),
            selectInput(ns("brief_domain"), "Domain", choices = news_domains()),
            selectInput(ns("signal_strength"), "Signal", choices = c("high", "medium", "low")),
            uiOutput(ns("project_link_ui"))
          ),
          textInput(ns("brief_title"), "Headline"),
          layout_columns(
            col_widths = c(6, 3, 3),
            textAreaInput(ns("brief_summary"), "Summary", rows = 2L),
            textInput(ns("brief_tags"), "Tags (comma-separated)"),
            textInput(ns("brief_source_url"), "Source URL")
          ),
          layout_columns(
            col_widths = c(6, 6),
            checkboxInput(ns("surprise_flag"), "Surprise item (outside usual domains)", FALSE),
            div(class = "action-row",
              actionButton(ns("save_brief"), tagList(icon("bookmark"), " Save brief"), class = "btn-primary"))
          ),
          textOutput(ns("save_status"))
        )
      )
    })

    output$project_link_ui <- renderUI({
      selectInput(ns("project_link"), "Project",
                  choices = c("—" = "", project_choices(paths)))
    })

    observeEvent(input$save_brief, {
      req(nzchar(input$brief_title))
      insert_news_brief_v5(
        paths, input$brief_date, input$brief_title, input$brief_domain,
        input$signal_strength, input$brief_summary, input$project_link,
        source_url = input$brief_source_url, tags = input$brief_tags,
        surprise_flag = if (isTRUE(input$surprise_flag)) 1L else 0L
      )
      log_job(paths, "save_news_brief", "success", input$brief_title)
      save_status(sprintf("Saved: \"%s\"", input$brief_title))
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$save_status <- renderText(save_status())
  })
}
