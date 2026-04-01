# mod_ideas.R
# Mind-map idea capture with project grouping and cross-pollination.
# Requires the visNetwork package: install.packages("visNetwork")

# Palette for projects in the mind map
project_palette <- c(
  "#174c4f", "#b36a1d", "#2e6b4f", "#2d6073", "#7b4f2e",
  "#5c3d8f", "#8f3d3d", "#3d6e4e", "#4e5c8f", "#8f7b3d"
)

idea_type_colours <- c(
  "Research question" = "#174c4f",
  "Method idea" = "#2d6073",
  "Analysis approach" = "#2e6b4f",
  Collaboration = "#b36a1d",
  "Paper concept" = "#7b4f2e",
  "Policy implication" = "#8f3d3d"
)

ideas_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(
      class = "page-intro",
      h1("Ideas"),
      p("Capture fleeting thoughts, connect them to projects, and surface cross-project patterns.")
    ),

    layout_columns(
      col_widths = c(4, 8),

      # ── Left: capture + filter ──────────────────────────────────────────
      tagList(
        card(
          card_header("Capture an idea"),
          card_body(
            textAreaInput(ns("idea_text"), NULL, placeholder = "Describe the idea...", rows = 3),
            selectInput(
              ns("idea_project"), "Project",
              choices = c("Cross-project (no link)" = "")
            ),
            selectInput(
              ns("idea_type"), "Type",
              choices = c(
                "Research question",
                "Method idea",
                "Analysis approach",
                "Collaboration",
                "Paper concept",
                "Policy implication"
              )
            ),
            selectInput(
              ns("idea_domain"), "Domain",
              choices = c("Epidemiology", "Biostatistics", "Surveillance",
                          "Spatial", "NTDs", "PH systems")
            ),
            selectInput(
              ns("idea_phd_relevance"), "PhD relevance",
              choices = c("None", "Article 1", "Article 2", "Article 3", "Future")
            ),
            selectInput(
              ns("idea_feasibility"), "Feasibility",
              choices = c("high", "medium", "low")
            ),
            selectInput(
              ns("idea_novelty_status"), "Novelty status",
              choices = c("novel", "partial", "exists")
            ),
            textInput(ns("idea_linked_papers"), "Linked papers", placeholder = "comma-separated citations or keys"),
            textInput(ns("idea_tags"), "Tags", placeholder = "comma-separated, e.g. spatial, PhD, AI"),
            div(
              class = "action-row",
              actionButton(ns("save_idea"), "Capture", class = "btn-primary", icon = icon("lightbulb")),
              actionButton(ns("clear_idea"), "Clear", class = "btn-outline-secondary")
            ),
            textOutput(ns("save_status"))
          )
        ),

        card(
          card_header("Map filter"),
          card_body(
            selectInput(
              ns("map_filter"), "Show ideas for",
              choices = c("All projects" = "all")
            ),
            checkboxInput(ns("show_cross_links"), "Show tag-based cross-connections", value = TRUE),
            actionButton(ns("refresh_map"), "Refresh map", class = "btn-sm btn-outline-secondary", icon = icon("rotate"))
          )
        )
      ),

      # ── Right: mind map ─────────────────────────────────────────────────
      card(
        card_header("Mind map"),
        card_body(
          style = "padding: 0.4rem;",
          uiOutput(ns("map_or_fallback"))
        )
      )
    ),

    # ── All ideas table ─────────────────────────────────────────────────
    card(
      card_header("All captured ideas"),
      card_body(
        class = "card-scroll",
        tableOutput(ns("idea_table"))
      )
    )
  )
}

ideas_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh_trigger <- reactiveVal(0L)
    save_status <- reactiveVal("")

    has_visnetwork <- requireNamespace("visNetwork", quietly = TRUE)

    # ── Populate project choices ──────────────────────────────────────────
    observe({
      refresh_trigger()
      choices <- c("Cross-project (no link)" = "", project_choices(paths))
      updateSelectInput(session, "idea_project", choices = choices)
      filter_choices <- c("All projects" = "all", "", project_choices(paths))
      updateSelectInput(session, "map_filter", choices = filter_choices)
    })

    # ── Capture ──────────────────────────────────────────────────────────
    observeEvent(input$save_idea, {
      req(nzchar(trimws(input$idea_text)))
      insert_idea(
        paths,
        text       = trimws(input$idea_text),
        project_id = input$idea_project,
        idea_type  = input$idea_type,
        tags       = input$idea_tags,
        domain = input$idea_domain,
        linked_papers = input$idea_linked_papers,
        feasibility = input$idea_feasibility,
        phd_relevance = input$idea_phd_relevance,
        novelty_status = input$idea_novelty_status
      )
      save_status(sprintf("Saved: \"%s\"", substr(trimws(input$idea_text), 1L, 50L)))
      refresh_trigger(refresh_trigger() + 1L)
    })

    observeEvent(input$clear_idea, {
      updateTextAreaInput(session, "idea_text", value = "")
      updateTextInput(session, "idea_linked_papers", value = "")
      updateTextInput(session, "idea_tags", value = "")
      save_status("")
    })

    observeEvent(input$refresh_map, {
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$save_status <- renderText(save_status())

    # ── Ideas data ───────────────────────────────────────────────────────
    ideas_data <- reactive({
      refresh_trigger()
      filter_val <- if (is.null(input$map_filter)) "all" else input$map_filter
      get_ideas(paths, project_id = if (filter_val == "all") NULL else filter_val)
    })

    # ── Mind map ─────────────────────────────────────────────────────────
    output$map_or_fallback <- renderUI({
      if (!has_visnetwork) {
        return(div(
          class = "empty-state",
          tags$p(tagList(icon("circle-exclamation"), "  visNetwork is not installed.")),
          tags$p(
            tags$code("install.packages(\"visNetwork\")"),
            " then restart the dashboard."
          )
        ))
      }
      visNetwork::visNetworkOutput(ns("idea_map"), height = "460px")
    })

    output$idea_map <- visNetwork::renderVisNetwork({
      req(has_visnetwork)
      refresh_trigger()
      input$refresh_map

      ideas <- ideas_data()

      if (!nrow(ideas)) {
        # Show a placeholder
        nodes <- data.frame(
          id = 1L, label = "No ideas yet\nCapture your first idea →",
          shape = "ellipse", color = "#ddd", font.size = 14L,
          stringsAsFactors = FALSE
        )
        return(
          visNetwork::visNetwork(nodes, data.frame(from = integer(), to = integer())) |>
          visNetwork::visOptions(highlightNearest = FALSE) |>
          visNetwork::visPhysics(enabled = FALSE)
        )
      }

      # ── Build project hub nodes ──────────────────────────────────────
      projects_in_map <- unique(ideas$project)
      n_proj <- length(projects_in_map)

      hub_ids <- seq_len(n_proj)
      hub_colours <- project_palette[((seq_len(n_proj) - 1L) %% length(project_palette)) + 1L]
      hub_nodes <- data.frame(
        id        = hub_ids,
        label     = projects_in_map,
        title     = projects_in_map,
        shape     = "box",
        color     = hub_colours,
        font.size = 15L,
        level     = 1L,
        stringsAsFactors = FALSE
      )

      # ── Build idea nodes ─────────────────────────────────────────────
      idea_node_ids <- seq_len(nrow(ideas)) + n_proj
      proj_idx <- match(ideas$project, projects_in_map)
      node_colours <- project_palette[((proj_idx - 1L) %% length(project_palette)) + 1L]

      tags_safe <- ifelse(is.na(ideas$tags) | !nzchar(ideas$tags), "—", ideas$tags)
      idea_nodes <- data.frame(
        id        = idea_node_ids,
        label     = mapply(function(txt, typ) paste0(strwrap_label(txt, 22L), "\n[", typ, "]"),
                           ideas$text, ideas$idea_type, USE.NAMES = FALSE),
        title     = paste0(
          ideas$text, "\nType: ", ideas$idea_type,
          "\nDomain: ", ideas$domain,
          "\nPhD: ", ideas$phd_relevance,
          "\nFeasibility: ", ideas$feasibility,
          "\nNovelty: ", ideas$novelty_status,
          "\nPapers: ", ifelse(nzchar(ideas$linked_papers), ideas$linked_papers, "—"),
          "\nProject: ", ideas$project,
          "\nTags: ", tags_safe,
          "\nCaptured: ", substr(ideas$created_at, 1L, 10L)
        ),
        shape     = "ellipse",
        color     = node_colours,
        font.size = 12L,
        level     = 2L,
        stringsAsFactors = FALSE
      )

      nodes <- rbind(
        hub_nodes[, c("id","label","title","shape","color","font.size","level")],
        idea_nodes[, c("id","label","title","shape","color","font.size","level")]
      )

      # ── Hub → idea edges ────────────────────────────────────────────
      hub_edges <- data.frame(
        from  = hub_ids[proj_idx],
        to    = idea_node_ids,
        color = "#cccccc",
        stringsAsFactors = FALSE
      )

      # ── Cross-pollination edges (shared tags) ────────────────────────
      cross_from  <- integer()
      cross_to    <- integer()
      cross_color <- character()

      if (isTRUE(input$show_cross_links) && nrow(ideas) > 1L) {
        for (i in seq_len(nrow(ideas) - 1L)) {
          tags_i <- parse_tags(ideas$tags[i])
          if (!length(tags_i)) next
          for (j in (i + 1L):nrow(ideas)) {
            if (ideas$project[i] == ideas$project[j]) next
            tags_j <- parse_tags(ideas$tags[j])
            if (length(intersect(tags_i, tags_j)) > 0L) {
              cross_from  <- c(cross_from,  idea_node_ids[i])
              cross_to    <- c(cross_to,    idea_node_ids[j])
              cross_color <- c(cross_color, "#b36a1d")
            }
          }
        }
      }

      cross_edges <- data.frame(from = cross_from, to = cross_to,
                                color = cross_color, stringsAsFactors = FALSE)

      edges <- rbind(
        hub_edges[, c("from","to","color")],
        if (nrow(cross_edges)) cross_edges[, c("from","to","color")] else data.frame(from=integer(),to=integer(),color=character())
      )

      visNetwork::visNetwork(nodes, edges) |>
        visNetwork::visHierarchicalLayout(direction = "LR", levelSeparation = 200L) |>
        visNetwork::visOptions(
          highlightNearest = list(enabled = TRUE, degree = 1L, hover = TRUE),
          nodesIdSelection = FALSE
        ) |>
        visNetwork::visInteraction(
          navigationButtons = FALSE,
          tooltipDelay      = 100L
        ) |>
        visNetwork::visPhysics(enabled = FALSE) |>
        visNetwork::visEdges(smooth = list(type = "cubicBezier"))
    })

    # ── Ideas table ──────────────────────────────────────────────────────
    output$idea_table <- renderTable({
      refresh_trigger()
      ideas <- get_ideas(paths)
      if (!nrow(ideas)) {
        return(data.frame(message = "No ideas captured yet.", stringsAsFactors = FALSE))
      }
      ideas[, c("created_at", "project", "idea_type", "domain", "phd_relevance",
                "feasibility", "novelty_status", "linked_papers", "tags", "text")]
    }, bordered = TRUE, striped = TRUE, spacing = "s")
  })
}

# ── Helpers ────────────────────────────────────────────────────────────────

parse_tags <- function(tag_str) {
  if (is.na(tag_str) || !nzchar(tag_str)) return(character())
  trimws(strsplit(tag_str, ",")[[1L]])
}

strwrap_label <- function(text, width = 22L) {
  wrapped <- strwrap(text, width = width)
  paste(head(wrapped, 3L), collapse = "\n")
}
