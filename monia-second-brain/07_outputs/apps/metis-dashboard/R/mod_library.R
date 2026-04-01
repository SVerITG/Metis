# mod_library.R
# Literature: cluster map, gallery view, spaced repetition, PhD bucket bars.

library_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Library"),
      p("Literature inventory, PhD coverage, topic cluster map, and daily article review.")
    ),

    # ── Actions ─────────────────────────────────────────────────────
    card(
      card_header("Actions"),
      card_body(
        div(class = "action-row",
          actionButton(ns("scan_library"), tagList(icon("folder-open"), " Scan for new material"),
                       class = "btn-primary"),
          actionButton(ns("refresh_db"), tagList(icon("database"), " Refresh metadata database"),
                       class = "btn-outline-secondary")
        ),
        textOutput(ns("action_status"))
      )
    ),

    # ── KPIs ────────────────────────────────────────────────────────
    layout_columns(
      col_widths = c(4, 4, 4),
      value_box(title = "Inventory rows",   value = textOutput(ns("inventory_rows")),
                showcase = icon("database"), theme = "primary"),
      value_box(title = "Duplicate groups", value = textOutput(ns("duplicate_groups")),
                showcase = icon("copy"),     theme = "warning"),
      value_box(title = "PhD-seeded",       value = textOutput(ns("seeded_rows")),
                showcase = icon("flask"),    theme = "success")
    ),

    # ── Today's review (spaced repetition) ──────────────────────────
    uiOutput(ns("sr_section")),

    # ── Cluster map + article panel ──────────────────────────────────
    layout_columns(
      col_widths = c(7, 5),
      card(
        card_header(
          div(style = "display:flex; justify-content:space-between; align-items:center;",
            span("PhD article cluster map"),
            tags$small(style = "color:#6d7c74;", "Click a topic to filter"))
        ),
        card_body(style = "padding:0.4rem;",
                  uiOutput(ns("cluster_map_or_fallback")))
      ),
      card(
        card_header("Articles in selected topic"),
        card_body(class = "card-scroll",
                  uiOutput(ns("selected_bucket_articles")))
      )
    ),

    # ── Literature browser — gallery / table toggle ──────────────────
    card(
      card_header(
        div(style = "display:flex; justify-content:space-between; align-items:center;",
          span("PhD-seeded literature"),
          div(class = "view-toggle",
            actionButton(ns("view_gallery"), tagList(icon("grip"), " Gallery"),
                         class = "btn btn-sm btn-outline-secondary"),
            actionButton(ns("view_tbl"),    tagList(icon("table"), " Table"),
                         class = "btn btn-sm btn-outline-secondary")
          )
        )
      ),
      card_body(uiOutput(ns("literature_view")))
    ),

    # ── Bucket bars ──────────────────────────────────────────────────
    card(
      card_header("PhD article buckets — full summary"),
      card_body(uiOutput(ns("bucket_bars")))
    ),

    # ── Courses ──────────────────────────────────────────────────────
    uiOutput(ns("courses_section"))
  )
}

library_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns              <- session$ns
    action_status   <- reactiveVal("No action run yet.")
    refresh_trigger <- reactiveVal(0L)
    selected_bucket <- reactiveVal(NULL)
    lit_view        <- reactiveVal("gallery")   # "gallery" | "table"

    has_visnetwork  <- requireNamespace("visNetwork", quietly = TRUE)

    observeEvent(input$view_gallery, lit_view("gallery"))
    observeEvent(input$view_tbl,     lit_view("table"))

    # ── Scan / refresh ───────────────────────────────────────────────
    observeEvent(input$scan_library, {
      result <- tryCatch(run_script("scan_library.R", paths = paths),
                         error = function(e) list(status = 1L, output = conditionMessage(e)))
      action_status(result$output)
      refresh_trigger(refresh_trigger() + 1L)
    })

    observeEvent(input$refresh_db, {
      result <- tryCatch(run_script("refresh_metadata_db.R", paths = paths),
                         error = function(e) list(status = 1L, output = conditionMessage(e)))
      action_status(result$output)
      refresh_trigger(refresh_trigger() + 1L)
    })

    inventory  <- reactive({ refresh_trigger(); safe_read_tsv(file.path(paths$literature_metadata, "library-inventory.tsv")) })
    duplicates <- reactive({ refresh_trigger(); safe_read_tsv(file.path(paths$literature_metadata, "exact-duplicates.tsv")) })
    seeded     <- reactive({ refresh_trigger(); safe_read_tsv(file.path(paths$literature_metadata, "library-phd-seeded.tsv")) })

    output$inventory_rows   <- renderText(nrow(inventory()))
    output$duplicate_groups <- renderText(nrow(duplicates()))
    output$seeded_rows      <- renderText(nrow(seeded()))
    output$action_status    <- renderText(action_status())

    # ── Spaced repetition ────────────────────────────────────────────
    sr_refresh <- reactiveVal(0L)

    observeEvent(input$sr_rating, {
      req(input$sr_rating, is.list(input$sr_rating))
      update_sr_review(paths, input$sr_rating$sr_id, input$sr_rating$rating)
      sr_refresh(sr_refresh() + 1L)
    }, ignoreNULL = TRUE)

    observeEvent(input$sr_seed, {
      s <- seeded()
      if (!nrow(s) || !"basename" %in% names(s)) return()
      valid <- s[!is.na(s$phd_article_link) & nzchar(s$phd_article_link) &
                   s$phd_article_link != "to_triage", , drop = FALSE]
      if (!nrow(valid)) return()
      for (i in seq_len(min(nrow(valid), 20L))) {
        row    <- valid[i, ]
        front  <- row$basename
        back   <- paste0(
          "Bucket: ", row$phd_article_link, "\n",
          if ("surveillance_mode" %in% names(row) && !is.na(row$surveillance_mode)) paste0("Mode: ", row$surveillance_mode, "\n") else "",
          if ("relevance_note" %in% names(row) && !is.na(row$relevance_note)) row$relevance_note else ""
        )
        insert_sr_item(paths, "library_seeded", row$relative_path, front, back)
      }
      sr_refresh(sr_refresh() + 1L)
    })

    output$sr_section <- renderUI({
      sr_refresh()
      due <- get_due_sr_items(paths, n = 1L)

      if (!nrow(due)) {
        # Nothing due — offer to seed
        return(card(
          card_header(tagList(icon("brain"), "  Daily article review")),
          card_body(
            div(class = "sr-widget",
              div(class = "sr-deck-label", "No cards due today"),
              tags$p(style = "color:#6d7c74; font-size:0.85rem;",
                     "All caught up! You can seed new review cards from your seeded articles."),
              actionButton(ns("sr_seed"), tagList(icon("plus"), " Seed review deck"),
                           class = "btn-outline-secondary btn-sm")
            )
          )
        ))
      }

      item    <- due[1L, ]
      ns_id   <- ns("sr_rating")
      hard_js <- sprintf("Shiny.setInputValue('%s',{sr_id:'%s',rating:'hard'},{priority:'event'})",
                         ns_id, item$sr_id)
      good_js <- sprintf("Shiny.setInputValue('%s',{sr_id:'%s',rating:'good'},{priority:'event'})",
                         ns_id, item$sr_id)
      easy_js <- sprintf("Shiny.setInputValue('%s',{sr_id:'%s',rating:'easy'},{priority:'event'})",
                         ns_id, item$sr_id)

      back_text <- if (!is.na(item$back_text) && nzchar(item$back_text)) {
        item$back_text
      } else "No additional details stored."

      card(
        card_header(tagList(icon("brain"), "  Daily article review")),
        card_body(
          div(class = "sr-widget",
            div(class = "sr-deck-label",
                sprintf("Review %d · interval %d days", item$repetitions + 1L, item$interval_days)),
            div(class = "sr-prompt",
                tags$em("What do you remember about:"),
                tags$br(),
                tags$strong(item$front_text)
            ),
            # Reveal button (client-side only) + answer block
            tags$button(
              id = ns("sr_reveal_btn"),
              class = "btn btn-outline-secondary btn-sm",
              onclick = sprintf(
                "this.style.display='none'; document.getElementById('%s').style.display='block';",
                ns("sr_answer_block")
              ),
              tagList(icon("eye"), "  Reveal")
            ),
            div(id = ns("sr_answer_block"), style = "display:none;",
              div(class = "sr-answer",
                  tags$pre(style = "white-space:pre-wrap; font-size:0.84rem; margin:0;", back_text)),
              div(class = "sr-rating-row",
                tags$button(class = "btn btn-sm", style = "background:#c0392b; color:#fff;",
                            onclick = hard_js, "Hard"),
                tags$button(class = "btn btn-sm", style = "background:#2d6073; color:#fff;",
                            onclick = good_js, "Good"),
                tags$button(class = "btn btn-sm", style = "background:#2e6b4f; color:#fff;",
                            onclick = easy_js, "Easy")
              )
            ),
            div(class = "sr-progress",
                sprintf("Next review after rating: Hard=+1d · Good=+%dd · Easy=+%dd",
                        max(2L, round(item$interval_days * 1.5)),
                        max(4L, item$interval_days * 2L)))
          )
        )
      )
    })

    # ── Cluster map ──────────────────────────────────────────────────
    output$cluster_map_or_fallback <- renderUI({
      if (!has_visnetwork) {
        return(div(class = "empty-state",
          tags$p(tagList(icon("circle-exclamation"), "  visNetwork not installed.")),
          tags$p(tags$code("install.packages(\"visNetwork\")"), " to enable the map.")))
      }
      visNetwork::visNetworkOutput(ns("cluster_map"), height = "380px")
    })

    output$cluster_map <- visNetwork::renderVisNetwork({
      req(has_visnetwork)
      refresh_trigger()
      buckets <- article_bucket_summary(paths)
      if (!nrow(buckets)) {
        nodes <- data.frame(id=1L, label="No seeded articles yet", shape="ellipse",
                            color="#ddd", font.size=14L, stringsAsFactors=FALSE)
        return(visNetwork::visNetwork(nodes, data.frame(from=integer(),to=integer())) |>
               visNetwork::visPhysics(enabled=FALSE))
      }
      hub <- data.frame(id=0L, label="PhD\nLiterature", title="PhD Literature",
                        shape="box", color="#174c4f", font.size=16L,
                        value=max(buckets$count)*2L, stringsAsFactors=FALSE)
      palette <- colorRamp_palette(nrow(buckets))
      bnodes  <- data.frame(
        id=seq_len(nrow(buckets)), label=buckets$bucket,
        title=paste0("<b>",buckets$bucket,"</b><br>",buckets$count," articles"),
        shape="ellipse", value=buckets$count, color=palette, font.size=13L,
        stringsAsFactors=FALSE)
      nodes <- rbind(hub[,c("id","label","title","shape","color","font.size","value")],
                     bnodes[,c("id","label","title","shape","color","font.size","value")])
      edges <- data.frame(from=0L, to=seq_len(nrow(buckets)), color="#cccccc",
                          stringsAsFactors=FALSE)
      visNetwork::visNetwork(nodes, edges) |>
        visNetwork::visLayout(randomSeed=42L) |>
        visNetwork::visOptions(highlightNearest=list(enabled=TRUE,degree=1L,hover=TRUE)) |>
        visNetwork::visEvents(
          selectNode = sprintf(
            "function(n){Shiny.setInputValue('%s',n.nodes[0],{priority:'event'});}",
            ns("selected_node")
          ),
          deselectNode = sprintf(
            "function(n){Shiny.setInputValue('%s',null,{priority:'event'});}",
            ns("selected_node")
          )
        ) |>
        visNetwork::visPhysics(solver="forceAtlas2Based",
                               forceAtlas2Based=list(gravitationalConstant=-80L)) |>
        visNetwork::visEdges(smooth=list(type="continuous"))
    })

    observeEvent(input$selected_node, {
      nid <- input$selected_node
      if (is.null(nid) || nid == 0L) { selected_bucket(NULL); return() }
      b <- article_bucket_summary(paths)
      if (nrow(b) >= nid) selected_bucket(b$bucket[as.integer(nid)])
    })

    output$selected_bucket_articles <- renderUI({
      bucket <- selected_bucket()
      if (is.null(bucket)) {
        return(div(class="empty-state", tagList(icon("hand-pointer"), "  Click a topic node to see its articles.")))
      }
      s <- seeded()
      if (!nrow(s) || !"phd_article_link" %in% names(s)) return(p("No seeded data available."))
      arts <- s[!is.na(s$phd_article_link) & s$phd_article_link == bucket, , drop=FALSE]
      if (!nrow(arts)) return(p(style="color:#888;", paste("No articles in bucket:", bucket)))
      col_name <- if ("basename" %in% names(arts)) "basename" else names(arts)[1L]
      tags$div(
        tags$h6(style="color:#174c4f; margin-bottom:0.5rem;",
                tagList(icon("book-open"), "  "), bucket,
                tags$small(style="color:#888; margin-left:0.5em;",
                           paste0("(", nrow(arts), " articles)"))),
        tags$ul(style="padding-left:1.2em; margin:0;",
          lapply(seq_len(min(nrow(arts), 20L)), function(i) {
            tags$li(style="margin-bottom:0.35em; font-size:0.85em;", arts[[col_name]][i])
          })
        ),
        if (nrow(arts)>20L) tags$p(style="color:#888;font-size:0.8em;margin-top:0.4em;",
                                    sprintf("… and %d more.", nrow(arts)-20L))
      )
    })

    # ── Literature view — gallery / table ───────────────────────────
    output$literature_view <- renderUI({
      refresh_trigger()
      s <- seeded()
      if (!nrow(s)) {
        return(div(class="empty-state",
                   "No seeded articles yet. Run a library scan first."))
      }
      if (lit_view() == "gallery") {
        gallery_cards(s)
      } else {
        cols <- intersect(c("basename","phd_article_link","surveillance_mode","relevance_note","status"), names(s))
        tableOutput(ns("lit_table"))
      }
    })

    output$lit_table <- renderTable({
      s    <- seeded()
      cols <- intersect(c("basename","phd_article_link","surveillance_mode","relevance_note"), names(s))
      head(s[, cols, drop=FALSE], 50L)
    }, bordered=TRUE, striped=TRUE, spacing="s")

    # ── Courses ──────────────────────────────────────────────────────
    courses_refresh <- reactiveVal(0L)

    observeEvent(input$lesson_complete, {
      act <- input$lesson_complete
      req(is.list(act), !is.null(act$course_id), !is.null(act$lesson_id))
      mark_lesson_complete(paths, act$course_id, act$lesson_id)
      courses_refresh(courses_refresh() + 1L)
    }, ignoreNULL = TRUE)

    observeEvent(input$lesson_sr, {
      act <- input$lesson_sr
      req(is.list(act), !is.null(act$course_id), !is.null(act$lesson_id))
      front <- act$lesson_id
      back  <- paste0("Course: ", act$course_id, "\nLesson: ", act$lesson_id)
      insert_sr_item(paths, "course_progress", paste0(act$course_id, "::", act$lesson_id), front, back)
      showNotification("Added to spaced repetition deck.", type = "message", duration = 2L)
    }, ignoreNULL = TRUE)

    output$courses_section <- renderUI({
      courses_refresh()
      course_projects <- tryCatch(
        db_table(paths, paste(
          "SELECT project_id, title, COALESCE(external_path,'') AS external_path",
          "FROM projects WHERE domain = 'education' AND status = 'active'"
        )),
        error = function(...) data.frame()
      )
      if (!nrow(course_projects)) return(NULL)

      has_jsonlite <- requireNamespace("jsonlite", quietly = TRUE)
      ns_id_complete <- ns("lesson_complete")
      ns_id_sr       <- ns("lesson_sr")

      course_cards <- lapply(seq_len(nrow(course_projects)), function(i) {
        cp  <- course_projects[i, ]
        cid <- cp$project_id

        # Try to load lessons.json
        lessons_path <- file.path(cp$external_path, "mlm-app", "lessons.json")
        if (!file.exists(lessons_path)) {
          lessons_path <- file.path(cp$external_path, "lessons.json")
        }

        lessons <- if (has_jsonlite && file.exists(lessons_path)) {
          tryCatch({
            raw <- jsonlite::fromJSON(lessons_path, simplifyDataFrame = FALSE)
            if (is.data.frame(raw)) raw else if (is.list(raw) && !is.null(raw$lessons)) raw$lessons else raw
          }, error = function(...) NULL)
        } else NULL

        # Get completion progress
        progress <- tryCatch(get_course_progress(paths, cid), error = function(...) data.frame())
        completed_ids <- if (nrow(progress)) progress$lesson_id else character()

        if (is.null(lessons)) {
          lesson_ui <- div(class = "empty-state",
            if (!has_jsonlite) {
              tags$p(tagList(icon("circle-exclamation"), "  Install jsonlite to load lessons: "),
                     tags$code("install.packages('jsonlite')"))
            } else {
              tags$p(style = "color:#888; font-size:0.85rem;",
                     "No lessons.json found. Expected at: mlm-app/lessons.json")
            }
          )
        } else {
          lesson_list <- if (is.data.frame(lessons)) {
            id_col    <- intersect(c("id", "lesson_id", "lessonId"), names(lessons))[1L]
            title_col <- intersect(c("title", "name", "label"), names(lessons))[1L]
            lapply(seq_len(nrow(lessons)), function(j) {
              lid   <- if (!is.na(id_col)) as.character(lessons[[id_col]][j]) else as.character(j)
              ltitle <- if (!is.na(title_col)) lessons[[title_col]][j] else paste0("Lesson ", j)
              done  <- lid %in% completed_ids
              div(class = paste("course-lesson-row", if (done) "lesson-done" else ""),
                div(class = "course-lesson-title",
                    if (done) icon("check-circle") else tagList(icon("circle"), "  "), ltitle),
                if (!done) {
                  div(class = "course-lesson-actions",
                    tags$button(
                      class = "btn btn-xs btn-outline-success",
                      onclick = sprintf(
                        "Shiny.setInputValue('%s',{course_id:'%s',lesson_id:'%s'},{priority:'event'})",
                        ns_id_complete, cid, lid
                      ),
                      "Mark complete"
                    ),
                    tags$button(
                      class = "btn btn-xs btn-outline-secondary",
                      onclick = sprintf(
                        "Shiny.setInputValue('%s',{course_id:'%s',lesson_id:'%s'},{priority:'event'})",
                        ns_id_sr, cid, lid
                      ),
                      tagList(icon("brain"), "  Add to SR deck")
                    )
                  )
                }
              )
            })
          } else {
            # lessons is a plain list
            lapply(seq_along(lessons), function(j) {
              item  <- lessons[[j]]
              lid   <- if (is.list(item)) {
                v <- item[["id"]]
                if (is.null(v)) v <- item[["lesson_id"]]
                if (is.null(v)) v <- j
                as.character(v)
              } else as.character(j)
              ltitle <- if (is.list(item)) {
                v <- item[["title"]]
                if (is.null(v)) v <- item[["name"]]
                if (is.null(v)) v <- paste0("Lesson ", j)
                as.character(v)
              } else as.character(item)
              done <- lid %in% completed_ids
              div(class = paste("course-lesson-row", if (done) "lesson-done" else ""),
                div(class = "course-lesson-title",
                    if (done) icon("check-circle") else tagList(icon("circle"), "  "), ltitle),
                if (!done) {
                  div(class = "course-lesson-actions",
                    tags$button(
                      class = "btn btn-xs btn-outline-success",
                      onclick = sprintf(
                        "Shiny.setInputValue('%s',{course_id:'%s',lesson_id:'%s'},{priority:'event'})",
                        ns_id_complete, cid, lid
                      ),
                      "Mark complete"
                    ),
                    tags$button(
                      class = "btn btn-xs btn-outline-secondary",
                      onclick = sprintf(
                        "Shiny.setInputValue('%s',{course_id:'%s',lesson_id:'%s'},{priority:'event'})",
                        ns_id_sr, cid, lid
                      ),
                      tagList(icon("brain"), "  Add to SR deck")
                    )
                  )
                }
              )
            })
          }

          n_total <- length(lesson_list)
          n_done  <- length(completed_ids)
          pct     <- if (n_total > 0L) round(n_done / n_total * 100L) else 0L

          lesson_ui <- tagList(
            div(class = "course-progress-bar-wrap",
              div(class = "course-progress-label",
                  sprintf("%d / %d lessons complete (%d%%)", n_done, n_total, pct)),
              div(style = "background:#e8e4dc; height:6px; border-radius:3px; overflow:hidden; margin-top:4px;",
                div(style = sprintf("width:%d%%; height:100%%; background:#2e6b4f; border-radius:3px;", pct)))
            ),
            div(class = "course-lesson-list", lesson_ui)
          )
        }

        div(class = "course-card",
          div(class = "course-card-title", tagList(icon("graduation-cap"), "  "), cp$title),
          lesson_ui
        )
      })

      card(
        card_header("Courses"),
        card_body(div(class = "courses-grid", course_cards))
      )
    })

    # ── Bucket bars ──────────────────────────────────────────────────
    output$bucket_bars <- renderUI({
      refresh_trigger()
      buckets <- article_bucket_summary(paths)
      if (!nrow(buckets)) {
        return(div(class="empty-state",
                   "No seeded articles found. Run a library scan first."))
      }
      max_count <- max(buckets$count)
      palette   <- colorRamp_palette(nrow(buckets))
      lapply(seq_len(nrow(buckets)), function(i) {
        pct <- round(buckets$count[i] / max_count * 100L)
        div(style="margin-bottom:0.6em;",
          div(style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:2px;",
              span(buckets$bucket[i]),
              span(style="color:#6d7c74;", buckets$count[i])),
          div(style="background:#eee;border-radius:4px;height:8px;",
            div(class="bucket-bar",
                style=sprintf("width:%d%%;background:%s;", pct, palette[i])))
        )
      })
    })
  })
}

# ── Gallery card builder ────────────────────────────────────────────────────

gallery_cards <- function(s) {
  n       <- min(nrow(s), 60L)  # cap at 60 for performance
  rows    <- s[seq_len(n), , drop = FALSE]
  palette <- c("#174c4f","#2d6073","#2e6b4f","#b36a1d","#7b4f2e",
               "#5c3d8f","#8f3d3d","#3d6e4e","#4e5c8f","#8f7b3d")

  cards <- lapply(seq_len(nrow(rows)), function(i) {
    row    <- rows[i, ]
    fname  <- if ("basename" %in% names(row)) row$basename else "—"
    bucket <- if ("phd_article_link" %in% names(row) && !is.na(row$phd_article_link))
                row$phd_article_link else "—"
    mode   <- if ("surveillance_mode" %in% names(row) && !is.na(row$surveillance_mode))
                row$surveillance_mode else ""
    note   <- if ("relevance_note" %in% names(row) && !is.na(row$relevance_note))
                row$relevance_note else ""
    col    <- palette[((i - 1L) %% length(palette)) + 1L]

    div(class = "gallery-card",
      div(class = "gallery-card-bucket", style = paste0("background:", col, ";"), bucket),
      div(class = "gallery-card-title", fname),
      if (nzchar(mode)) div(class = "gallery-card-mode", mode),
      if (nzchar(note)) div(class = "gallery-card-note", note)
    )
  })

  tagList(
    if (nrow(s) > 60L) {
      tags$p(style = "font-size:0.78rem; color:#888; margin-bottom:0.5rem;",
             sprintf("Showing 60 of %d seeded articles.", nrow(s)))
    },
    div(class = "gallery-grid", cards)
  )
}

# ── Palette helper ──────────────────────────────────────────────────────────

colorRamp_palette <- function(n) {
  if (n == 0L) return(character())
  colours <- c("#174c4f","#2d6073","#2e6b4f","#b36a1d","#7b4f2e",
               "#5c3d8f","#8f3d3d","#3d6e4e","#4e5c8f","#8f7b3d")
  colours[((seq_len(n) - 1L) %% length(colours)) + 1L]
}
