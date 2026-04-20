# mod_ideas.R
# Ideas tab — idea capture, brainstorm context assembly, and mindmap.
# Journal/personal notes have moved to the Notes tab (mod_notes.R).
# Requires the visNetwork package: install.packages("visNetwork")

# ── Colour palettes ────────────────────────────────────────────────────────────

project_palette <- c(
  "#174c4f", "#b36a1d", "#2e6b4f", "#2d6073", "#7b4f2e",
  "#5c3d8f", "#8f3d3d", "#3d6e4e", "#4e5c8f", "#8f7b3d"
)

idea_type_colours <- c(
  "Research question"  = "#174c4f",
  "Method idea"        = "#2d6073",
  "Analysis approach"  = "#2e6b4f",
  "Collaboration"      = "#b36a1d",
  "Paper concept"      = "#7b4f2e",
  "Policy implication" = "#8f3d3d"
)

# ── UI ─────────────────────────────────────────────────────────────────────────

ideas_ui <- function(id) {
  ns <- NS(id)

  tagList(
    # ── Mode toggle bar ──────────────────────────────────────────────────────
    div(
      class = "page-intro",
      h1("Ideas"),
      p("Capture thoughts, explore connections, and assemble brainstorm context."),
      div(
        style = "display:flex; gap:0.5rem; margin-top:0.75rem;",
        actionButton(
          ns("mode_ideas"), "Ideas",
          class = "btn-primary",
          icon  = icon("lightbulb")
        ),
        actionButton(
          ns("mode_brainstorm"), "Brainstorm",
          class = "btn-outline-secondary",
          icon  = icon("brain")
        ),
        actionButton(
          ns("mode_mindmap"), "Mindmap",
          class = "btn-outline-secondary",
          icon  = icon("diagram-project")
        )
      )
    ),

    # ── Ideas panel ──────────────────────────────────────────────────────────
    conditionalPanel(
      condition = "output.current_mode === 'ideas'",
      ns = ns,

      layout_columns(
        col_widths = c(4, 8),

        # Left: capture form
        tagList(
          card(
            card_header("Capture an idea"),
            card_body(
              textAreaInput(ns("idea_text"), NULL,
                            placeholder = "Describe the idea...", rows = 3),
              selectInput(
                ns("idea_project"), "Project",
                choices = c("Cross-project (no link)" = "")
              ),
              selectInput(
                ns("idea_type"), "Type",
                choices = c(
                  "Research question", "Method idea", "Analysis approach",
                  "Collaboration", "Paper concept", "Policy implication"
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
              textInput(ns("idea_linked_papers"), "Linked papers",
                        placeholder = "comma-separated citations or keys"),
              textInput(ns("idea_tags"), "Tags",
                        placeholder = "comma-separated, e.g. spatial, PhD, AI"),
              div(
                class = "action-row",
                actionButton(ns("save_idea"), "Capture",
                             class = "btn-primary", icon = icon("lightbulb")),
                actionButton(ns("clear_idea"), "Clear",
                             class = "btn-outline-secondary")
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
              checkboxInput(ns("show_cross_links"),
                            "Show tag-based cross-connections", value = TRUE),
              actionButton(ns("refresh_map"), "Refresh map",
                           class = "btn-sm btn-outline-secondary",
                           icon  = icon("rotate"))
            )
          )
        ),

        # Right: mind map + table
        tagList(
          card(
            card_header("Mind map"),
            card_body(
              style = "padding: 0.4rem;",
              uiOutput(ns("map_or_fallback"))
            )
          ),
          card(
            card_header("All captured ideas"),
            card_body(
              class = "card-scroll",
              tableOutput(ns("idea_table"))
            )
          )
        )
      )
    ),

    # ── Mindmap panel ─────────────────────────────────────────────────────────
    conditionalPanel(
      condition = "output.current_mode === 'mindmap'",
      ns = ns,

      layout_columns(
        col_widths = c(3, 9),

        card(
          card_header("Filter"),
          card_body(
            selectInput(
              ns("mindmap_idea_select"),
              "Centre on idea",
              choices = c("All ideas (project hubs)" = "all")
            ),
            checkboxInput(ns("mindmap_cross_links"),
                          "Show tag-based cross-connections", value = TRUE),
            checkboxInput(ns("mindmap_show_papers"),
                          "Include linked papers", value = FALSE),
            actionButton(ns("refresh_mindmap"), "Refresh",
                         class = "btn-sm btn-outline-secondary",
                         icon  = icon("rotate"))
          )
        ),

        card(
          card_header("Idea connections"),
          card_body(
            style = "padding:0;",
            uiOutput(ns("mindmap_or_fallback"))
          )
        )
      )
    ),

    # ── Brainstorm panel ──────────────────────────────────────────────────────
    conditionalPanel(
      condition = "output.current_mode === 'brainstorm'",
      ns = ns,

      layout_columns(
        col_widths = c(4, 8),

        # Left: context selector
        card(
          card_header("Select context sources"),
          card_body(
            p(class = "text-muted",
              style = "font-size:0.85rem; margin-bottom:1rem;",
              "Choose the knowledge sources to include in your brainstorm prompt."),
            checkboxGroupInput(
              ns("brainstorm_sources"),
              label = NULL,
              choices = c(
                "Scientific library (all indexed papers)"  = "library",
                "Recent meetings (last 30 days)"           = "meetings",
                "Journal entries (this month)"             = "journal",
                "My active research articles"              = "articles",
                "My active projects"                       = "projects",
                "Past ideas (this month)"                  = "ideas",
                "Recent news (high-signal)"                = "news"
              )
            ),
            tags$hr(),
            textAreaInput(ns("brainstorm_topic"),
                          "What do you want to brainstorm about?",
                          placeholder = "Describe your topic or question...",
                          rows = 4,
                          width = "100%"),
            div(
              class = "action-row",
              actionButton(ns("assemble_context"), "Assemble context",
                           class = "btn-primary", icon = icon("wand-magic-sparkles"))
            )
          )
        ),

        # Right: assembled prompt + recent sessions
        tagList(
          card(
            card_header("Assembled prompt"),
            card_body(
              uiOutput(ns("brainstorm_prompt_ui"))
            )
          ),
          card(
            card_header("Recent brainstorm sessions"),
            card_body(
              class = "card-scroll",
              uiOutput(ns("brainstorm_sessions_ui"))
            )
          )
        )
      )
    )
  )
}

# ── Server ─────────────────────────────────────────────────────────────────────

ideas_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    ensure_db_schema(paths)

    has_visnetwork <- requireNamespace("visNetwork", quietly = TRUE)

    # ── Mode tracking ────────────────────────────────────────────────────────
    current_mode <- reactiveVal("ideas")

    observeEvent(input$mode_ideas,     { current_mode("ideas") })
    observeEvent(input$mode_brainstorm,{ current_mode("brainstorm") })
    observeEvent(input$mode_mindmap,   { current_mode("mindmap") })

    # Expose mode to conditionalPanel (client-side)
    output$current_mode <- renderText({ current_mode() })
    outputOptions(output, "current_mode", suspendWhenHidden = FALSE)

    # Update button styles to reflect active mode
    observe({
      m <- current_mode()
      try(updateActionButton(session, "mode_ideas",
                         class = if (m == "ideas") "btn-primary" else "btn-outline-secondary"), silent = TRUE)
      try(updateActionButton(session, "mode_brainstorm",
                         class = if (m == "brainstorm") "btn-primary" else "btn-outline-secondary"), silent = TRUE)
      try(updateActionButton(session, "mode_mindmap",
                         class = if (m == "mindmap") "btn-primary" else "btn-outline-secondary"), silent = TRUE)
    })

    # ── Shared refresh trigger ───────────────────────────────────────────────
    refresh_trigger <- reactiveVal(0L)

    # ── ================================================================= ──
    # ── IDEAS mode ────────────────────────────────────────────────────────
    # ── ================================================================= ──

    save_status <- reactiveVal("")

    # Populate project choices
    observe({
      refresh_trigger()
      choices <- c("Cross-project (no link)" = "", project_choices(paths))
      updateSelectInput(session, "idea_project", choices = choices)
      filter_choices <- c("All projects" = "all", "", project_choices(paths))
      updateSelectInput(session, "map_filter", choices = filter_choices)
    })

    observeEvent(input$save_idea, {
      req(nzchar(trimws(input$idea_text)))
      tryCatch({
        insert_idea(
          paths,
          text           = trimws(input$idea_text),
          project_id     = input$idea_project,
          idea_type      = input$idea_type,
          tags           = input$idea_tags,
          domain         = input$idea_domain,
          linked_papers  = input$idea_linked_papers,
          feasibility    = input$idea_feasibility,
          phd_relevance  = input$idea_phd_relevance,
          novelty_status = input$idea_novelty_status
        )
        save_status(sprintf("Saved: \"%s\"", substr(trimws(input$idea_text), 1L, 50L)))
        refresh_trigger(refresh_trigger() + 1L)
      }, error = function(e) {
        save_status(paste("Error saving idea:", conditionMessage(e)))
      })
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

    ideas_data <- reactive({
      refresh_trigger()
      filter_val <- if (is.null(input$map_filter)) "all" else input$map_filter
      get_ideas(paths, project_id = if (filter_val == "all") NULL else filter_val)
    })

    # Mind map
    output$map_or_fallback <- renderUI({
      if (!has_visnetwork) {
        return(div(
          class = "empty-state",
          tags$p(tagList(icon("circle-exclamation"), "  visNetwork is not installed.")),
          tags$p(tags$code("install.packages(\"visNetwork\")"), " then restart the dashboard.")
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
        nodes <- data.frame(
          id = 1L, label = "No ideas yet\nCapture your first idea \u2192",
          shape = "ellipse", color = "#ddd", font.size = 14L,
          stringsAsFactors = FALSE
        )
        return(
          visNetwork::visNetwork(nodes, data.frame(from = integer(), to = integer())) |>
            visNetwork::visOptions(highlightNearest = FALSE) |>
            visNetwork::visPhysics(enabled = FALSE)
        )
      }

      projects_in_map <- unique(ideas$project)
      n_proj          <- length(projects_in_map)
      hub_ids         <- seq_len(n_proj)
      hub_colours     <- project_palette[((seq_len(n_proj) - 1L) %% length(project_palette)) + 1L]

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

      idea_node_ids <- seq_len(nrow(ideas)) + n_proj
      proj_idx      <- match(ideas$project, projects_in_map)
      node_colours  <- project_palette[((proj_idx - 1L) %% length(project_palette)) + 1L]
      tags_safe     <- ifelse(is.na(ideas$tags) | !nzchar(ideas$tags), "\u2014", ideas$tags)

      idea_nodes <- data.frame(
        id    = idea_node_ids,
        label = mapply(function(txt, typ)
          paste0(strwrap_label(txt, 22L), "\n[", typ, "]"),
          ideas$text, ideas$idea_type, USE.NAMES = FALSE),
        title = paste0(
          ideas$text, "\nType: ", ideas$idea_type,
          "\nDomain: ", ideas$domain,
          "\nPhD: ", ideas$phd_relevance,
          "\nFeasibility: ", ideas$feasibility,
          "\nNovelty: ", ideas$novelty_status,
          "\nPapers: ", ifelse(nzchar(ideas$linked_papers), ideas$linked_papers, "\u2014"),
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

      hub_edges <- data.frame(
        from  = hub_ids[proj_idx],
        to    = idea_node_ids,
        color = "#cccccc",
        stringsAsFactors = FALSE
      )

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
        if (nrow(cross_edges))
          cross_edges[, c("from","to","color")]
        else
          data.frame(from = integer(), to = integer(), color = character())
      )

      visNetwork::visNetwork(nodes, edges) |>
        visNetwork::visHierarchicalLayout(direction = "LR", levelSeparation = 200L) |>
        visNetwork::visOptions(
          highlightNearest = list(enabled = TRUE, degree = 1L, hover = TRUE),
          nodesIdSelection = FALSE
        ) |>
        visNetwork::visInteraction(navigationButtons = FALSE, tooltipDelay = 100L) |>
        visNetwork::visPhysics(enabled = FALSE) |>
        visNetwork::visEdges(smooth = list(type = "cubicBezier"))
    })

    output$idea_table <- renderTable({
      refresh_trigger()
      ideas <- get_ideas(paths)
      if (!nrow(ideas)) {
        return(data.frame(message = "No ideas captured yet.", stringsAsFactors = FALSE))
      }
      ideas[, c("created_at", "project", "idea_type", "domain", "phd_relevance",
                "feasibility", "novelty_status", "linked_papers", "tags", "text")]
    }, bordered = TRUE, striped = TRUE, spacing = "s")

    # ── ================================================================= ──
    # ── MINDMAP mode ──────────────────────────────────────────────────────
    # ── ================================================================= ──

    mindmap_refresh <- reactiveVal(0L)

    observeEvent(input$refresh_mindmap, {
      mindmap_refresh(mindmap_refresh() + 1L)
    })

    # Populate idea selector
    observe({
      mindmap_refresh()
      ideas <- tryCatch(get_ideas(paths), error = function(e) NULL)
      if (!is.null(ideas) && nrow(ideas) > 0L) {
        idea_choices <- c(
          "All ideas (project hubs)" = "all",
          setNames(ideas$idea_id, substr(ideas$text, 1L, 60L))
        )
      } else {
        idea_choices <- c("All ideas (project hubs)" = "all")
      }
      updateSelectInput(session, "mindmap_idea_select", choices = idea_choices)
    })

    output$mindmap_or_fallback <- renderUI({
      if (!has_visnetwork) {
        return(div(
          class = "empty-state",
          style = "padding:2rem;",
          tags$p(tagList(icon("circle-exclamation"), "  visNetwork is not installed.")),
          tags$p(tags$code("install.packages(\"visNetwork\")"), " then restart.")
        ))
      }
      visNetwork::visNetworkOutput(ns("idea_mindmap"), height = "520px")
    })

    output$idea_mindmap <- visNetwork::renderVisNetwork({
      req(has_visnetwork)
      mindmap_refresh()
      input$refresh_mindmap

      ideas    <- tryCatch(get_ideas(paths), error = function(e) NULL)
      selected <- input$mindmap_idea_select %||% "all"

      if (is.null(ideas) || nrow(ideas) == 0L) {
        nodes <- data.frame(
          id = 1L, label = "No ideas yet",
          shape = "ellipse", color = "#ddd", font.size = 14L,
          stringsAsFactors = FALSE
        )
        return(
          visNetwork::visNetwork(nodes, data.frame(from = integer(), to = integer())) |>
            visNetwork::visOptions(highlightNearest = FALSE) |>
            visNetwork::visPhysics(enabled = FALSE)
        )
      }

      # Filter to selected idea + its neighbours if a single idea is chosen
      if (selected != "all") {
        focal    <- ideas[ideas$idea_id == selected, , drop = FALSE]
        focal_tags <- parse_tags(focal$tags[1L])
        if (length(focal_tags)) {
          connected <- ideas[sapply(ideas$tags, function(t)
            length(intersect(parse_tags(t), focal_tags)) > 0L), ]
        } else {
          connected <- ideas[ideas$project == focal$project[1L], ]
        }
        ideas <- unique(rbind(focal, connected))
      }

      projects_in_map <- unique(ideas$project)
      n_proj          <- length(projects_in_map)
      hub_ids         <- seq_len(n_proj)
      hub_colours     <- project_palette[((seq_len(n_proj) - 1L) %% length(project_palette)) + 1L]

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

      idea_node_ids <- seq_len(nrow(ideas)) + n_proj
      proj_idx      <- match(ideas$project, projects_in_map)
      node_colours  <- project_palette[((proj_idx - 1L) %% length(project_palette)) + 1L]

      # Highlight the focal idea
      if (selected != "all") {
        focal_idx <- which(ideas$idea_id == selected)
        if (length(focal_idx)) node_colours[focal_idx] <- "#FFD700"
      }

      tags_safe <- ifelse(is.na(ideas$tags) | !nzchar(ideas$tags), "\u2014", ideas$tags)

      idea_nodes <- data.frame(
        id    = idea_node_ids,
        label = mapply(function(txt, typ)
          paste0(strwrap_label(txt, 22L), "\n[", typ, "]"),
          ideas$text, ideas$idea_type, USE.NAMES = FALSE),
        title = paste0(
          ideas$text,
          "\nType: ", ideas$idea_type,
          "\nDomain: ", ideas$domain,
          "\nPhD: ", ideas$phd_relevance,
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

      hub_edges <- data.frame(
        from  = hub_ids[proj_idx],
        to    = idea_node_ids,
        color = "#cccccc",
        stringsAsFactors = FALSE
      )

      cross_from  <- integer()
      cross_to    <- integer()
      cross_color <- character()

      if (isTRUE(input$mindmap_cross_links) && nrow(ideas) > 1L) {
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
        if (nrow(cross_edges))
          cross_edges[, c("from","to","color")]
        else
          data.frame(from = integer(), to = integer(), color = character())
      )

      visNetwork::visNetwork(nodes, edges) |>
        visNetwork::visHierarchicalLayout(direction = "LR", levelSeparation = 220L) |>
        visNetwork::visOptions(
          highlightNearest = list(enabled = TRUE, degree = 1L, hover = TRUE),
          nodesIdSelection = FALSE
        ) |>
        visNetwork::visInteraction(navigationButtons = FALSE, tooltipDelay = 100L) |>
        visNetwork::visPhysics(enabled = FALSE) |>
        visNetwork::visEdges(smooth = list(type = "cubicBezier"))
    })

    # ── ================================================================= ──
    # ── BRAINSTORM mode ───────────────────────────────────────────────────
    # ── ================================================================= ──

    brainstorm_prompt_text <- reactiveVal(NULL)
    brainstorm_refresh     <- reactiveVal(0L)

    observeEvent(input$assemble_context, {
      topic   <- trimws(input$brainstorm_topic)
      sources <- input$brainstorm_sources

      if (!nzchar(topic)) {
        brainstorm_prompt_text(NULL)
        showNotification("Please enter a topic first.", type = "warning")
        return()
      }
      if (is.null(sources) || length(sources) == 0L) {
        brainstorm_prompt_text(NULL)
        showNotification("Select at least one knowledge source.", type = "warning")
        return()
      }

      prompt <- tryCatch(
        assemble_brainstorm_context(paths, sources, topic),
        error = function(e) {
          paste("Error assembling context:", conditionMessage(e))
        }
      )

      # Persist session to DB
      tryCatch({
        insert_brainstorm_session(
          paths        = paths,
          topic        = topic,
          sources_used = paste(sources, collapse = ", "),
          summary      = substr(prompt, 1L, 500L)
        )
        brainstorm_refresh(brainstorm_refresh() + 1L)
      }, error = function(e) NULL)

      brainstorm_prompt_text(prompt)
    })

    output$brainstorm_prompt_ui <- renderUI({
      prompt <- brainstorm_prompt_text()

      if (is.null(prompt)) {
        return(div(
          class = "empty-state",
          icon("wand-magic-sparkles"),
          p("Select sources and a topic, then click Assemble context.")
        ))
      }

      tagList(
        div(
          style = paste0(
            "background:#f5f7f7; border:1px solid #dde4e4; border-radius:8px;",
            "padding:1rem; font-family:monospace; font-size:0.8rem;",
            "white-space:pre-wrap; max-height:400px; overflow-y:auto;"
          ),
          prompt
        ),
        tags$br(),
        div(
          class = "action-row",
          actionButton(
            ns("copy_prompt"), "Copy to clipboard",
            class = "btn-sm btn-outline-secondary",
            icon  = icon("copy"),
            onclick = sprintf(
              "navigator.clipboard.writeText(%s).then(function(){Shiny.notification.show('Copied!', {type:'message', duration:2000})});",
              jsonlite::toJSON(prompt, auto_unbox = TRUE)
            )
          )
        )
      )
    })

    output$brainstorm_sessions_ui <- renderUI({
      brainstorm_refresh()

      sessions <- tryCatch(
        get_brainstorm_sessions(paths, n = 5L),
        error = function(e) NULL
      )

      if (is.null(sessions) || nrow(sessions) == 0L) {
        return(div(
          class = "empty-state",
          icon("brain"),
          p("No brainstorm sessions yet.")
        ))
      }

      session_cards <- lapply(seq_len(nrow(sessions)), function(i) {
        row      <- sessions[i, ]
        date_str <- substr(row$created_at, 1L, 16L)

        source_chips <- if (nzchar(trimws(row$sources_used))) {
          srcs <- trimws(strsplit(row$sources_used, ",")[[1L]])
          tagList(lapply(srcs, function(s)
            tags$span(
              s,
              style = paste0(
                "display:inline-block; margin:2px 3px 0 0; padding:1px 7px;",
                "background:#eef0f8; border-radius:10px;",
                "font-size:0.73rem; color:#3d4e8f;"
              )
            )
          ))
        } else NULL

        div(
          style = paste0(
            "border:1px solid #e4e4e4; border-radius:8px; padding:0.75rem;",
            "margin-bottom:0.6rem; background:#fff;"
          ),
          div(
            style = "display:flex; justify-content:space-between; align-items:baseline;",
            tags$strong(row$topic),
            tags$span(style = "font-size:0.78rem; color:#888;", date_str)
          ),
          div(style = "margin-top:0.35rem;", source_chips)
        )
      })

      tagList(session_cards)
    })
  })
}

# ── Shared helpers (ideas) ─────────────────────────────────────────────────────

parse_tags <- function(tag_str) {
  if (is.na(tag_str) || !nzchar(tag_str)) return(character())
  trimws(strsplit(tag_str, ",")[[1L]])
}

strwrap_label <- function(text, width = 22L) {
  wrapped <- strwrap(text, width = width)
  paste(head(wrapped, 3L), collapse = "\n")
}

# ── Brainstorm DB helpers ──────────────────────────────────────────────────────

insert_brainstorm_session <- function(paths, topic, sources_used, summary = "") {
  session_id <- sprintf("bsrm-%s", format(Sys.time(), "%Y%m%d%H%M%S"))
  created_at <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")

  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  DBI::dbExecute(
    con,
    paste0(
      "INSERT INTO brainstorm_sessions ",
      "(session_id, topic, sources_used, summary, created_at) ",
      "VALUES (?, ?, ?, ?, ?)"
    ),
    list(session_id, topic, sources_used, summary, created_at)
  )

  invisible(session_id)
}

get_brainstorm_sessions <- function(paths, n = 5L) {
  sql <- sprintf(
    "SELECT session_id, topic, sources_used, summary, created_at
       FROM brainstorm_sessions
      ORDER BY created_at DESC
      LIMIT %d",
    as.integer(n)
  )
  db_table(paths, sql)
}

assemble_brainstorm_context <- function(paths, sources, topic) {
  lines <- character()

  lines <- c(lines,
    "BRAINSTORM CONTEXT",
    "==================",
    sprintf("Topic: %s", topic),
    "",
    "Selected knowledge sources:",
    ""
  )

  if ("library" %in% sources) {
    lines <- c(lines, "=== SCIENTIFIC LIBRARY ===")
    papers <- tryCatch({
      sql <- "SELECT title FROM papers ORDER BY indexed_at DESC LIMIT 20"
      df  <- db_table(paths, sql)
      if (nrow(df)) df$title else character()
    }, error = function(e) character())
    if (length(papers)) {
      lines <- c(lines, paste0("  - ", papers))
    } else {
      lines <- c(lines, "  (no papers indexed yet)")
    }
    lines <- c(lines, "")
  }

  if ("meetings" %in% sources) {
    lines <- c(lines, "=== RECENT MEETINGS (last 30 days) ===")
    meetings <- tryCatch({
      cutoff <- format(Sys.Date() - 30, "%Y-%m-%d")
      sql    <- sprintf(
        "SELECT title FROM meetings WHERE date >= '%s' ORDER BY date DESC LIMIT 15",
        cutoff
      )
      df <- db_table(paths, sql)
      if (nrow(df)) df$title else character()
    }, error = function(e) character())
    if (length(meetings)) {
      lines <- c(lines, paste0("  - ", meetings))
    } else {
      lines <- c(lines, "  (no recent meetings found)")
    }
    lines <- c(lines, "")
  }

  if ("journal" %in% sources) {
    lines <- c(lines, "=== JOURNAL ENTRIES (this month) ===")
    entries <- tryCatch({
      month_start <- format(as.Date(format(Sys.Date(), "%Y-%m-01")), "%Y-%m-%d")
      sql <- sprintf(
        "SELECT content, mood, created_at FROM journal_entries
          WHERE created_at >= '%s'
          ORDER BY created_at DESC LIMIT 10",
        month_start
      )
      df <- db_table(paths, sql)
      df
    }, error = function(e) NULL)
    if (!is.null(entries) && nrow(entries) > 0L) {
      for (i in seq_len(nrow(entries))) {
        date_str <- substr(entries$created_at[i], 1L, 10L)
        preview  <- substr(entries$content[i], 1L, 100L)
        lines    <- c(lines, sprintf("  [%s | %s] %s\u2026", date_str, entries$mood[i], preview))
      }
    } else {
      lines <- c(lines, "  (no journal entries this month)")
    }
    lines <- c(lines, "")
  }

  if ("articles" %in% sources) {
    lines <- c(lines, "=== MY ACTIVE RESEARCH ARTICLES ===")
    articles <- tryCatch({
      sql <- "SELECT title, status FROM articles WHERE status NOT IN ('published', 'archived') ORDER BY updated_at DESC LIMIT 10"
      df  <- db_table(paths, sql)
      if (nrow(df)) paste0(df$title, " [", df$status, "]") else character()
    }, error = function(e) character())
    if (length(articles)) {
      lines <- c(lines, paste0("  - ", articles))
    } else {
      lines <- c(lines, "  (no active articles found)")
    }
    lines <- c(lines, "")
  }

  if ("projects" %in% sources) {
    lines <- c(lines, "=== MY ACTIVE PROJECTS ===")
    projects <- tryCatch({
      sql <- "SELECT name, status FROM projects WHERE status = 'active' ORDER BY name LIMIT 10"
      df  <- db_table(paths, sql)
      if (nrow(df)) df$name else character()
    }, error = function(e) character())
    if (length(projects)) {
      lines <- c(lines, paste0("  - ", projects))
    } else {
      lines <- c(lines, "  (no active projects found)")
    }
    lines <- c(lines, "")
  }

  if ("ideas" %in% sources) {
    lines <- c(lines, "=== PAST IDEAS (this month) ===")
    ideas <- tryCatch({
      month_start <- format(as.Date(format(Sys.Date(), "%Y-%m-01")), "%Y-%m-%d")
      sql <- sprintf(
        "SELECT text, idea_type, tags FROM ideas
          WHERE created_at >= '%s'
          ORDER BY created_at DESC LIMIT 15",
        month_start
      )
      db_table(paths, sql)
    }, error = function(e) NULL)
    if (!is.null(ideas) && nrow(ideas) > 0L) {
      for (i in seq_len(nrow(ideas))) {
        lines <- c(lines, sprintf("  [%s] %s", ideas$idea_type[i], ideas$text[i]))
      }
    } else {
      lines <- c(lines, "  (no ideas captured this month)")
    }
    lines <- c(lines, "")
  }

  if ("news" %in% sources) {
    lines <- c(lines, "=== RECENT NEWS (high-signal) ===")
    news <- tryCatch({
      sql <- "SELECT title, source FROM news WHERE signal = 'high' ORDER BY published_at DESC LIMIT 10"
      df  <- db_table(paths, sql)
      if (nrow(df)) paste0(df$title, " (", df$source, ")") else character()
    }, error = function(e) character())
    if (length(news)) {
      lines <- c(lines, paste0("  - ", news))
    } else {
      lines <- c(lines, "  (no high-signal news available)")
    }
    lines <- c(lines, "")
  }

  lines <- c(
    lines,
    "==================",
    "",
    "Instructions: Cross-pollinate the selected sources. Surface non-obvious connections.",
    "Think out loud with me. Start by identifying 3-5 tensions or opportunities that emerge",
    "from the combination of these knowledge sources and my topic."
  )

  paste(lines, collapse = "\n")
}
