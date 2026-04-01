# mod_graph.R
# Global knowledge graph: projects, ideas, article buckets, meetings as a unified visNetwork.
# Requires visNetwork: install.packages("visNetwork")

graph_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Knowledge Graph"),
      p("All entities — projects, ideas, article clusters, and meetings — in one connected view.")
    ),

    layout_columns(
      col_widths = c(3, 9),

      # ── Controls ────────────────────────────────────────────────
      card(
        card_header("Filter"),
        card_body(
          checkboxInput(ns("show_buckets"),  "Article topic clusters", value = TRUE),
          checkboxInput(ns("show_meetings"), "Meetings (last 10)",     value = FALSE),
          checkboxInput(ns("show_tags"),     "Cross-tag idea links",   value = TRUE),
          tags$hr(),
          actionButton(ns("refresh_graph"), tagList(icon("rotate"), " Refresh"),
                       class = "btn-outline-secondary btn-sm"),
          tags$hr(),
          # Legend
          div(class = "graph-legend",
            graph_legend_item("#174c4f", "Project"),
            graph_legend_item("#b36a1d", "Idea"),
            graph_legend_item("#2e6b4f", "Article cluster"),
            graph_legend_item("#2d6073", "Meeting"),
            graph_legend_item("#cccccc", "— edge (link)"),
            graph_legend_item("#b36a1d", "— edge (shared tag)", dashed = TRUE)
          ),
          tags$hr(),
          tags$p(style = "font-size:0.78rem; color:#6d7c74;",
            "Tip: click a node to highlight its connections. Scroll to zoom.")
        )
      ),

      # ── Graph ───────────────────────────────────────────────────
      card(
        card_header("Graph"),
        card_body(style = "padding:0;",
                  uiOutput(ns("graph_or_fallback")))
      )
    )
  )
}

graph_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns             <- session$ns
    has_visnetwork <- requireNamespace("visNetwork", quietly = TRUE)

    output$graph_or_fallback <- renderUI({
      if (!has_visnetwork) {
        return(div(class = "empty-state", style = "padding:3rem;",
          tags$p(tagList(icon("circle-exclamation"), "  visNetwork is not installed.")),
          tags$p(tags$code("install.packages(\"visNetwork\")"),
                 " then restart the dashboard.")))
      }
      visNetwork::visNetworkOutput(ns("graph"), height = "600px")
    })

    output$graph <- visNetwork::renderVisNetwork({
      req(has_visnetwork)
      input$refresh_graph
      input$show_buckets
      input$show_meetings
      input$show_tags

      # ── Load data ──────────────────────────────────────────────
      projects <- tryCatch(
        db_table(paths, "SELECT project_id, title, domain FROM projects WHERE status='active'"),
        error = function(...) data.frame()
      )
      ideas <- tryCatch(
        get_ideas(paths),
        error = function(...) data.frame()
      )
      buckets <- if (isTRUE(input$show_buckets)) {
        tryCatch(article_bucket_summary(paths), error = function(...) data.frame())
      } else data.frame()
      meetings <- if (isTRUE(input$show_meetings)) {
        tryCatch(
          db_table(paths,
            "SELECT meeting_id, title, project FROM meetings ORDER BY created_at DESC LIMIT 10"),
          error = function(...) data.frame()
        )
      } else data.frame()

      # Node ID namespace — prefix-based to avoid collisions
      nodes <- build_graph_nodes(projects, ideas, buckets, meetings)
      edges <- build_graph_edges(projects, ideas, buckets, meetings,
                                 show_tags = isTRUE(input$show_tags))

      if (!nrow(nodes)) {
        placeholder <- data.frame(id=1L, label="No data yet\nAdd projects and ideas to populate",
                                  shape="ellipse", color="#ddd", font.size=14L,
                                  stringsAsFactors=FALSE)
        return(
          visNetwork::visNetwork(placeholder, data.frame(from=integer(),to=integer())) |>
          visNetwork::visPhysics(enabled=FALSE)
        )
      }

      visNetwork::visNetwork(nodes, edges) |>
        visNetwork::visOptions(
          highlightNearest = list(enabled=TRUE, degree=2L, hover=TRUE),
          nodesIdSelection = FALSE
        ) |>
        visNetwork::visPhysics(
          solver = "forceAtlas2Based",
          forceAtlas2Based = list(
            gravitationalConstant = -60L,
            springLength = 150L
          ),
          stabilization = list(iterations = 150L)
        ) |>
        visNetwork::visEdges(
          smooth = list(type = "continuous"),
          color  = list(opacity = 0.6)
        ) |>
        visNetwork::visInteraction(
          navigationButtons = TRUE,
          tooltipDelay = 80L
        )
    })
  })
}

# ── Node builder ─────────────────────────────────────────────────────────────

build_graph_nodes <- function(projects, ideas, buckets, meetings) {
  node_list <- list()

  # Projects
  if (nrow(projects)) {
    node_list[["projects"]] <- data.frame(
      id       = paste0("p_", projects$project_id),
      label    = projects$title,
      title    = paste0("<b>Project:</b> ", projects$title, "<br>Domain: ", projects$domain),
      shape    = "box",
      color    = "#174c4f",
      font.color = "#ffffff",
      font.size  = 15L,
      group    = "project",
      stringsAsFactors = FALSE
    )
  }

  # Ideas
  if (nrow(ideas)) {
    n_ideas <- min(nrow(ideas), 80L)  # cap for readability
    s       <- ideas[seq_len(n_ideas), , drop = FALSE]
    tags_safe <- ifelse(is.na(s$tags) | !nzchar(s$tags), "", paste0("<br>Tags: ", s$tags))
    node_list[["ideas"]] <- data.frame(
      id       = paste0("i_", s$idea_id),
      label    = substr(s$text, 1L, 30L),
      title    = paste0("<b>", s$text, "</b>", tags_safe,
                        "<br>Type: ", s$idea_type,
                        "<br>Project: ", s$project),
      shape    = "ellipse",
      color    = "#b36a1d",
      font.size  = 11L,
      group    = "idea",
      stringsAsFactors = FALSE
    )
  }

  # Article buckets
  if (nrow(buckets)) {
    node_list[["buckets"]] <- data.frame(
      id       = paste0("b_", seq_len(nrow(buckets))),
      label    = buckets$bucket,
      title    = paste0("<b>", buckets$bucket, "</b><br>", buckets$count, " articles"),
      shape    = "dot",
      value    = buckets$count,
      color    = "#2e6b4f",
      font.size  = 12L,
      group    = "bucket",
      stringsAsFactors = FALSE
    )
  }

  # Meetings
  if (nrow(meetings)) {
    node_list[["meetings"]] <- data.frame(
      id       = paste0("m_", meetings$meeting_id),
      label    = substr(meetings$title, 1L, 25L),
      title    = paste0("<b>", meetings$title, "</b><br>Project: ",
                        ifelse(is.na(meetings$project), "—", meetings$project)),
      shape    = "diamond",
      color    = "#2d6073",
      font.size  = 11L,
      group    = "meeting",
      stringsAsFactors = FALSE
    )
  }

  if (!length(node_list)) return(data.frame())

  # Standardise columns
  all_cols <- c("id","label","title","shape","color","font.size","group")
  combined <- lapply(node_list, function(df) {
    for (col in setdiff(all_cols, names(df))) df[[col]] <- NA_character_
    df[, all_cols, drop = FALSE]
  })
  do.call(rbind, combined)
}

# ── Edge builder ─────────────────────────────────────────────────────────────

build_graph_edges <- function(projects, ideas, buckets, meetings, show_tags = TRUE) {
  edge_list <- list()

  # Project → Idea edges
  if (nrow(projects) && nrow(ideas)) {
    proj_ids <- paste0("p_", projects$project_id)
    idea_ids <- paste0("i_", ideas$idea_id)

    # ideas$project_id is NA for cross-project ideas
    linked <- !is.na(ideas$project_id) & nzchar(ideas$project_id)
    from_p <- paste0("p_", ideas$project_id[linked])
    to_i   <- paste0("i_", ideas$idea_id[linked])
    # only keep from_p that exist in projects
    valid  <- from_p %in% proj_ids
    if (any(valid)) {
      edge_list[["proj_idea"]] <- data.frame(
        from  = from_p[valid],
        to    = to_i[valid],
        color = "#cccccc",
        dashes = FALSE,
        stringsAsFactors = FALSE
      )
    }
  }

  # Project → Bucket edges (via seeded articles project_link column)
  if (nrow(projects) && nrow(buckets)) {
    # We don't have a direct FK; skip or add a simple hub connection
    # Just connect each project to all buckets for now (light grey, thin)
    # Only if there's 1 project and many buckets (informative)
    if (nrow(projects) == 1L) {
      edge_list[["proj_bucket"]] <- data.frame(
        from  = paste0("p_", projects$project_id[1L]),
        to    = paste0("b_", seq_len(nrow(buckets))),
        color = "#dddddd",
        dashes = FALSE,
        stringsAsFactors = FALSE
      )
    }
  }

  # Project → Meeting edges (meeting.project text matches project title)
  if (nrow(projects) && nrow(meetings)) {
    proj_title_map <- stats::setNames(paste0("p_", projects$project_id), tolower(projects$title))
    for (i in seq_len(nrow(meetings))) {
      mp <- if (!is.na(meetings$project[i])) tolower(trimws(meetings$project[i])) else ""
      if (nzchar(mp) && mp %in% names(proj_title_map)) {
        edge_list[[paste0("meet_", i)]] <- data.frame(
          from  = proj_title_map[[mp]],
          to    = paste0("m_", meetings$meeting_id[i]),
          color = "#cccccc",
          dashes = FALSE,
          stringsAsFactors = FALSE
        )
      }
    }
  }

  # Idea → Idea cross-project tag edges
  if (show_tags && nrow(ideas) > 1L) {
    from_v <- character()
    to_v   <- character()
    for (i in seq_len(nrow(ideas) - 1L)) {
      ti <- parse_tags_graph(ideas$tags[i])
      if (!length(ti)) next
      for (j in (i + 1L):nrow(ideas)) {
        if (identical(ideas$project_id[i], ideas$project_id[j])) next
        tj <- parse_tags_graph(ideas$tags[j])
        if (length(intersect(ti, tj)) > 0L) {
          from_v <- c(from_v, paste0("i_", ideas$idea_id[i]))
          to_v   <- c(to_v,   paste0("i_", ideas$idea_id[j]))
        }
      }
    }
    if (length(from_v)) {
      edge_list[["tag_links"]] <- data.frame(
        from  = from_v,
        to    = to_v,
        color = "#b36a1d",
        dashes = TRUE,
        stringsAsFactors = FALSE
      )
    }
  }

  if (!length(edge_list)) {
    return(data.frame(from=character(), to=character(), color=character(),
                      dashes=logical(), stringsAsFactors=FALSE))
  }
  do.call(rbind, edge_list)
}

# ── Helpers ──────────────────────────────────────────────────────────────────

parse_tags_graph <- function(tag_str) {
  if (is.na(tag_str) || !nzchar(tag_str)) return(character())
  trimws(strsplit(tag_str, ",")[[1L]])
}

graph_legend_item <- function(colour, label, dashed = FALSE) {
  div(class = "graph-legend-item",
    if (dashed) {
      div(style = sprintf(
        "width:18px; height:2px; border-top:2px dashed %s; margin-top:4px;", colour))
    } else {
      div(class = "graph-legend-dot", style = paste0("background:", colour, ";"))
    },
    label
  )
}
