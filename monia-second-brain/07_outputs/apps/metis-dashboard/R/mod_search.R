# mod_search.R
# Full-text search across SQLite tables + second-brain markdown files.

search_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Search"),
      p("Search across tasks, projects, news, ideas, meetings, and markdown notes.")
    ),

    card(
      card_header("Search"),
      card_body(
        div(class = "action-row",
          div(style = "flex:1;",
              textInput(ns("query"), NULL, placeholder = "Type to search…",
                        width = "100%")),
          actionButton(ns("run_search"), tagList(icon("magnifying-glass"), " Search"),
                       class = "btn-primary")
        ),
        div(style = "display:flex; gap:0.5rem; flex-wrap:wrap; font-size:0.8rem; color:#6d7c74;",
          tags$span(tagList(icon("circle-info"), "  Searches tasks, projects, news briefs, ideas, meetings, and markdown files.")),
          uiOutput(ns("result_count"))
        )
      )
    ),

    uiOutput(ns("results"))
  )
}

search_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    results_data <- reactiveVal(NULL)

    observeEvent(input$run_search, {
      req(nzchar(trimws(input$query)))
      res <- tryCatch(
        search_all_sources(paths, input$query),
        error = function(e) list()
      )
      results_data(res)
    })

    # Also trigger on Enter key via debounced input (optional — button is primary)
    observeEvent(input$query, {
      # Only search if the user has typed enough
      if (nchar(trimws(input$query)) >= 3L) {
        res <- tryCatch(
          search_all_sources(paths, input$query),
          error = function(e) list()
        )
        results_data(res)
      }
    }, ignoreInit = TRUE)

    output$result_count <- renderUI({
      res <- results_data()
      if (is.null(res)) return(NULL)
      total <- sum(vapply(res, nrow_safe, 0L))
      tags$span(style = "color:#174c4f; font-weight:600;",
                sprintf("%d results found", total))
    })

    output$results <- renderUI({
      res <- results_data()
      if (is.null(res)) return(NULL)
      if (!length(res)) {
        return(div(class = "search-no-results",
          tagList(icon("magnifying-glass"), "  No results found. Try a broader search term.")))
      }

      type_labels <- c(
        tasks       = "Tasks",
        projects    = "Projects",
        news_briefs = "News briefs",
        ideas       = "Ideas",
        meetings    = "Meetings",
        markdown    = "Markdown files"
      )

      type_icons <- c(
        tasks       = "list-check",
        projects    = "folder",
        news_briefs = "newspaper",
        ideas       = "lightbulb",
        meetings    = "microphone",
        markdown    = "file-lines"
      )

      sections <- lapply(names(res), function(type) {
        rows  <- res[[type]]
        if (!nrow_safe(rows)) return(NULL)
        label <- type_labels[[type]] %||% type
        ico   <- type_icons[[type]]  %||% "file"

        item_cards <- lapply(seq_len(min(nrow(rows), 10L)), function(i) {
          row     <- rows[i, ]
          title   <- extract_title(row, type)
          snippet <- extract_snippet(row, type)
          div(class = "search-result-item",
            div(class = "search-result-title", title),
            if (nzchar(snippet)) div(class = "search-result-snippet", snippet)
          )
        })

        div(class = "search-result-group",
          div(class = "search-result-type",
              icon(ico), " ", label,
              tags$span(style = "color:#6d7c74; font-weight:400; margin-left:0.3em;",
                        paste0("(", nrow(rows), ")"))),
          item_cards
        )
      })

      tagList(sections)
    })
  })
}

# ── Helpers ─────────────────────────────────────────────────────────────────

nrow_safe <- function(x) {
  if (is.data.frame(x)) nrow(x) else 0L
}

`%||%` <- function(a, b) if (!is.null(a) && !is.na(a) && nzchar(a)) a else b

extract_title <- function(row, type) {
  candidates <- c("title", "text", "path", "basename", names(row)[1L])
  for (col in candidates) {
    if (col %in% names(row) && !is.na(row[[col]]) && nzchar(row[[col]])) {
      return(as.character(row[[col]]))
    }
  }
  "(no title)"
}

extract_snippet <- function(row, type) {
  candidates <- switch(type,
    tasks       = c("notes", "owner"),
    projects    = c("next_step", "domain"),
    news_briefs = c("summary", "domain", "brief_date"),
    ideas       = c("tags", "idea_type"),
    meetings    = c("domain", "meeting_date", "project"),
    markdown    = c("path"),
    character()
  )
  parts <- character()
  for (col in candidates) {
    if (col %in% names(row) && !is.na(row[[col]]) && nzchar(row[[col]])) {
      parts <- c(parts, as.character(row[[col]]))
    }
  }
  paste(parts, collapse = " · ")
}
