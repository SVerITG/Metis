# mod_control_room.R
# Morning command center: brief, KPIs, GitHub status, project boards with completion %.

control_room_ui <- function(id) {
  ns <- NS(id)

  tagList(
    # ── Project quick-launch panel ───────────────────────────────────
    uiOutput(ns("project_launch_panel")),

    # ── Morning brief ────────────────────────────────────────────────
    uiOutput(ns("morning_brief")),

    div(
      class = "page-intro",
      h1("Control Room"),
      p("Knowledge counts, project health, git status, and open tasks.")
    ),

    # ── KPI strip ────────────────────────────────────────────────────
    layout_columns(
      col_widths = c(3, 3, 3, 3),
      value_box(title = "Library items",    value = textOutput(ns("library_items")),
                showcase = icon("book-open"),      theme = "primary"),
      value_box(title = "PhD-seeded",       value = textOutput(ns("phd_seeded")),
                showcase = icon("graduation-cap"), theme = "success"),
      value_box(title = "Meeting artifacts",value = textOutput(ns("meeting_artifacts")),
                showcase = icon("microphone"),     theme = "info"),
      value_box(title = "Open tasks",       value = textOutput(ns("open_tasks")),
                showcase = icon("list-check"),     theme = "warning")
    ),

    # ── GitHub + snapshot ────────────────────────────────────────────
    layout_columns(
      col_widths = c(5, 7),
      card(
        card_header(
          div(style = "display:flex; justify-content:space-between; align-items:center;",
            span(tagList(icon("code-branch"), "  GitHub — repository status")),
            actionButton(ns("refresh_git"), tagList(icon("rotate")),
                         class = "btn btn-sm btn-outline-secondary", title = "Refresh"))
        ),
        card_body(uiOutput(ns("git_status_panel")))
      ),
      card(
        card_header("System snapshot"),
        card_body(tableOutput(ns("snapshot")))
      )
    ),

    # ── Latest brief ─────────────────────────────────────────────────
    card(
      card_header(tagList(icon("newspaper"), "  Latest news brief")),
      card_body(uiOutput(ns("latest_brief_ui")))
    ),

    # ── Project boards with completion bars ──────────────────────────
    card(
      card_header("Projects — health and open todos"),
      card_body(uiOutput(ns("project_boards")))
    ),

    # ── Recent files + tasks ─────────────────────────────────────────
    layout_columns(
      col_widths = c(6, 6),
      card(card_header("Recent files"),
           card_body(class = "card-scroll", tableOutput(ns("recent_files")))),
      card(card_header("All open tasks"),
           card_body(class = "card-scroll", tableOutput(ns("task_table"))))
    )
  )
}

control_room_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    metrics <- reactivePoll(
      10000L, session,
      checkFunc  = function() file.info(paths$second_brain_root)$mtime,
      valueFunc  = function() control_room_metrics(paths)
    )

    output$library_items     <- renderText(metrics()$library_items)
    output$phd_seeded        <- renderText(metrics()$phd_seeded)
    output$meeting_artifacts <- renderText(metrics()$meeting_artifacts)
    output$open_tasks        <- renderText(
      db_scalar(paths, "SELECT COUNT(*) FROM tasks WHERE status != 'done'")
    )

    # ── Morning brief ───────────────────────────────────────────────
    output$morning_brief <- renderUI({
      greeting  <- morning_greeting()
      today_lbl <- format(Sys.Date(), "%A, %d %B %Y")

      # Overdue / today tasks
      overdue <- tryCatch(
        db_table(paths, sprintf(
          paste(
            "SELECT t.title, p.title AS project, t.due_date",
            "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id",
            "WHERE t.status != 'done' AND t.due_date != '' AND t.due_date <= '%s'",
            "ORDER BY t.due_date ASC LIMIT 3"
          ),
          format(Sys.Date())
        )),
        error = function(...) data.frame()
      )

      open_n    <- tryCatch(db_scalar(paths, "SELECT COUNT(*) FROM tasks WHERE status != 'done'"), error = function(...) 0L)
      inbox_n   <- inbox_item_count(paths)
      paper     <- random_phd_paper(paths)

      # Latest high-signal news
      news_item <- tryCatch(
        db_table(paths,
          "SELECT title, domain FROM news_briefs WHERE signal_strength='high' ORDER BY brief_date DESC LIMIT 1"),
        error = function(...) data.frame()
      )

      # Overdue chip
      overdue_chip <- if (nrow(overdue) > 0L) {
        div(class = "morning-chip morning-chip-alert",
            icon("triangle-exclamation"),
            sprintf("%d overdue", nrow(overdue)))
      } else {
        div(class = "morning-chip morning-chip-ok", tagList(icon("check"), " No overdue tasks"))
      }

      # Inbox chip
      inbox_chip <- div(
        class = if (inbox_n > 0L) "morning-chip morning-chip-warn" else "morning-chip morning-chip-ok",
        icon("inbox"),
        sprintf("%d in inbox", inbox_n)
      )

      # Open tasks chip
      tasks_chip <- div(class = "morning-chip morning-chip-ok", icon("list-check"),
                        sprintf("%d open tasks", open_n))

      # News chip
      news_chip <- if (nrow(news_item)) {
        div(class = "morning-chip morning-chip-ok", icon("newspaper"), news_item$title[1L])
      }

      # Today's paper
      paper_block <- if (!is.null(paper) && nrow(paper)) {
        bucket <- if ("phd_article_link" %in% names(paper)) paper$phd_article_link[1L] else "—"
        fname  <- if ("basename" %in% names(paper)) paper$basename[1L] else "Unknown"
        div(class = "todays-paper",
          div(class = "todays-paper-label", tagList(icon("book-open"), "  Today's paper")),
          tags$strong(fname),
          tags$br(),
          tags$span(style = "font-size:0.78rem; color:#6d7c74;", paste0("Bucket: ", bucket))
        )
      }

      # Overdue list
      overdue_list <- if (nrow(overdue)) {
        div(style = "margin-top:0.6rem;",
          tags$p(style = "font-size:0.78rem; font-weight:600; color:#c0392b; margin-bottom:0.25rem;",
                 "Overdue tasks:"),
          tags$ul(style = "padding-left:1.1em; margin:0; font-size:0.82rem;",
            lapply(seq_len(nrow(overdue)), function(i) {
              tags$li(overdue$title[i],
                      tags$span(style = "color:#aaa; font-size:0.72em; margin-left:0.3em;",
                                paste0("[", overdue$due_date[i], "]")))
            })
          )
        )
      }

      div(class = "morning-brief",
        div(class = "morning-greeting", greeting),
        div(class = "morning-date", today_lbl),
        div(class = "morning-chips",
          overdue_chip, inbox_chip, tasks_chip,
          if (!is.null(news_chip)) news_chip
        ),
        paper_block,
        overdue_list
      )
    })

    # ── Snapshot ────────────────────────────────────────────────────
    output$snapshot <- renderTable({
      tryCatch(
        data.frame(
          Metric = c("DB inventory rows", "DB meetings", "Logged jobs"),
          Value  = c(
            db_scalar(paths, "SELECT COUNT(*) FROM library_inventory"),
            db_scalar(paths, "SELECT COUNT(*) FROM meetings"),
            db_scalar(paths, "SELECT COUNT(*) FROM jobs_log")
          ),
          stringsAsFactors = FALSE
        ),
        error = function(...) {
          data.frame(
            Metric = c("Library items", "Duplicate groups", "Agent specs"),
            Value  = c(metrics()$library_items, metrics()$duplicate_groups, metrics()$agent_specs),
            stringsAsFactors = FALSE
          )
        }
      )
    }, bordered = TRUE, striped = TRUE, spacing = "s")

    output$recent_files <- renderTable(
      recent_files_df(paths$second_brain_root, n = 6L),
      bordered = TRUE, striped = TRUE, spacing = "s"
    )

    # ── Latest brief ────────────────────────────────────────────────
    output$latest_brief_ui <- renderUI({
      brief <- db_table(paths,
        paste("SELECT brief_date, title, domain, signal_strength, COALESCE(summary,'') AS summary",
              "FROM news_briefs ORDER BY brief_date DESC, created_at DESC LIMIT 1"))
      if (!nrow(brief)) return(p(class = "status-info", "No briefs stored yet."))
      b   <- brief[1L, ]
      col <- switch(b$signal_strength, high = "#2e6b4f", medium = "#b36a1d", "#6d7c74")
      div(style = paste0("border-left:4px solid ", col, "; padding:0.5em 0.8em; background:#faf9f6; border-radius:3px;"),
        div(style = "display:flex; justify-content:space-between;",
            tags$strong(b$title),
            tags$span(style = "font-size:0.78rem; color:#888;", paste(b$brief_date, "|", b$domain))),
        if (nzchar(b$summary)) tags$p(style = "font-size:0.84rem; color:#4a5a5e; margin:0.2em 0 0;", b$summary),
        tags$span(class = paste0("signal-", b$signal_strength), b$signal_strength)
      )
    })

    # ── Git status ──────────────────────────────────────────────────
    git_trigger <- reactiveVal(0L)
    observeEvent(input$refresh_git, git_trigger(git_trigger() + 1L))

    git_data <- reactive({
      git_trigger()
      tryCatch(git_all_projects_status(paths), error = function(e) NULL)
    })

    # ── Project quick-launch panel ───────────────────────────────────
    output$project_launch_panel <- renderUI({
      git_trigger()
      projects <- tryCatch(
        db_table(paths, paste(
          "SELECT project_id, title, domain, external_path,",
          "COALESCE(github_url,'') AS github_url,",
          "COALESCE(launch_cmd,'') AS launch_cmd",
          "FROM projects WHERE status = 'active' ORDER BY priority DESC, title"
        )),
        error = function(...) data.frame()
      )
      if (!nrow(projects)) return(NULL)

      statuses <- git_data()
      ns_id <- ns("launch_action")

      rows <- lapply(seq_len(nrow(projects)), function(i) {
        p <- projects[i, ]

        # Git chip
        st <- if (!is.null(statuses) && nrow(statuses)) {
          statuses[statuses$project == p$title, , drop = FALSE]
        } else data.frame()

        git_chip <- if (!nrow(st)) {
          div(class = "launch-git-chip launch-git-na", "—")
        } else if (!is.na(st$uncommitted[1L]) && st$uncommitted[1L] > 0L) {
          div(class = "launch-git-chip launch-git-warn",
              sprintf("\u26a0 %d uncommitted", st$uncommitted[1L]))
        } else if (!is.na(st$unpushed[1L]) && st$unpushed[1L] > 0L) {
          div(class = "launch-git-chip launch-git-push",
              sprintf("\u2191 %d unpushed", st$unpushed[1L]))
        } else {
          div(class = "launch-git-chip launch-git-ok", "\u25cf clean")
        }

        # Action buttons
        open_btn <- if (!is.na(p$external_path) && nzchar(p$external_path)) {
          tags$button(
            class = "btn btn-xs btn-outline-secondary",
            onclick = sprintf(
              "Shiny.setInputValue('%s',{action:'open',pid:'%s'},{priority:'event'})",
              ns_id, p$project_id
            ),
            tagList(icon("folder-open"), "  Open folder")
          )
        }

        gh_btn <- if (nzchar(p$github_url) && p$github_url != "pending") {
          tags$a(class = "btn btn-xs btn-outline-secondary",
                 href = p$github_url, target = "_blank", tagList(icon("code-branch"), "  GitHub"))
        }

        launch_btn <- if (nzchar(p$launch_cmd)) {
          tags$button(
            class = "btn btn-xs btn-outline-primary",
            onclick = sprintf(
              "Shiny.setInputValue('%s',{action:'launch',pid:'%s'},{priority:'event'})",
              ns_id, p$project_id
            ),
            tagList(icon("rocket"), "  Launch")
          )
        }

        div(class = "launch-row",
          div(class = "launch-row-title",
            tags$strong(p$title),
            tags$span(class = paste0("domain-badge domain-", gsub("[^a-z0-9]", "-", tolower(p$domain))),
                      p$domain)
          ),
          git_chip,
          div(class = "launch-row-btns", open_btn, gh_btn, launch_btn)
        )
      })

      card(
        card_header(tagList(icon("briefcase"), "  Projects — quick launch")),
        card_body(div(class = "launch-panel", rows))
      )
    })

    observeEvent(input$launch_action, {
      act <- input$launch_action
      req(is.list(act), !is.null(act$action), !is.null(act$pid))

      proj <- tryCatch(
        db_table(paths, sprintf(
          "SELECT * FROM projects WHERE project_id = '%s'", act$pid
        )),
        error = function(...) data.frame()
      )
      if (!nrow(proj)) return()

      if (act$action == "open") {
        local_path <- proj$external_path[1L]
        if (!is.na(local_path) && nzchar(local_path)) {
          url <- paste0("file:///", gsub("\\\\", "/", local_path))
          browseURL(url)
        }
      } else if (act$action == "launch") {
        cmd <- if ("launch_cmd" %in% names(proj)) proj$launch_cmd[1L] else NA_character_
        if (!is.na(cmd) && nzchar(cmd)) {
          showModal(modalDialog(
            title = paste("Launch:", proj$title[1L]),
            tags$p("Run this command in your terminal:"),
            div(class = "launch-cmd-block",
                tags$code(cmd)),
            tags$p(style = "font-size:0.8rem; color:#6d7c74; margin-top:0.5rem;",
                   paste0("From: ", proj$external_path[1L])),
            easyClose = TRUE,
            footer = modalButton("Close")
          ))
        }
      }
    }, ignoreNULL = TRUE)

    output$git_status_panel <- renderUI({
      statuses <- git_data()
      if (is.null(statuses) || !nrow(statuses)) {
        return(p(class = "status-info", "No git projects found. Run seed_projects.R first."))
      }
      tagList(
        lapply(seq_len(nrow(statuses)), function(i) {
          row <- statuses[i, ]
          ok  <- (!is.na(row$uncommitted) && row$uncommitted == 0L) &&
                 (is.na(row$unpushed) || row$unpushed == 0L)
          col <- if (ok) "#27ae60" else "#c0392b"
          div(class = "git-row",
            div(class = "git-dot", style = paste0("background:", col, ";")),
            div(style = "flex:1;",
              tags$strong(row$project),
              tags$span(style = "font-size:0.78em; color:#888; margin-left:0.4em;",
                        paste0("(", row$branch, ")")),
              tags$br(),
              tags$span(style = paste0("font-size:0.82em; color:", col, ";"), row$advice)
            )
          )
        }),
        tags$p(style = "font-size:0.75em; color:#aaa; margin-top:0.5em;",
               tagList(icon("circle-info"), "  Green = clean. Red = commit or push needed."))
      )
    })

    # ── Task table ──────────────────────────────────────────────────
    output$task_table <- renderTable({
      tasks <- db_table(paths, paste(
        "SELECT t.title, p.title AS project, t.status, COALESCE(t.due_date,'') AS due_date",
        "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id",
        "WHERE t.status != 'done' ORDER BY t.created_at DESC LIMIT 12"
      ))
      if (!nrow(tasks)) return(data.frame(message = "No open tasks.", stringsAsFactors = FALSE))
      tasks
    }, bordered = TRUE, striped = TRUE, spacing = "s")

    # ── Project boards with completion bars ─────────────────────────
    output$project_boards <- renderUI({
      projects <- db_table(paths,
        "SELECT project_id, title, domain, priority, next_step FROM projects WHERE status = 'active' ORDER BY priority DESC, title")
      if (!nrow(projects)) {
        return(p(class = "status-info",
                 "No active projects. Run inst/scripts/seed_projects.R to populate."))
      }
      completion <- project_completion(paths)

      all_tasks <- db_table(paths,
        "SELECT project_id, title, status, owner FROM tasks WHERE status != 'done' ORDER BY created_at")

      priority_col <- function(p) switch(p, high="#c0392b", medium="#e67e22", low="#27ae60", "#7f8c8d")

      boards <- lapply(seq_len(nrow(projects)), function(i) {
        pid    <- projects$project_id[i]
        ppri   <- projects$priority[i]
        pnext  <- projects$next_step[i]
        ptasks <- all_tasks[all_tasks$project_id == pid, , drop = FALSE]

        # Completion %
        comp_row <- if (nrow(completion)) completion[completion$project_id == pid, , drop = FALSE] else data.frame()
        comp_ui <- if (nrow(comp_row)) {
          pct <- comp_row$pct[1L]
          div(
            div(class = "completion-bar-wrap",
                div(class = "completion-bar-fill", style = sprintf("width:%d%%;", pct))),
            div(class = "completion-label",
                sprintf("%d / %d tasks done (%d%%)", comp_row$done[1L], comp_row$total[1L], pct))
          )
        }

        task_items <- if (!nrow(ptasks)) {
          tags$p(style = "color:#aaa; font-style:italic; font-size:0.82rem;", "No open tasks")
        } else {
          tags$ul(style = "padding-left:1.1em; margin:0;",
            lapply(seq_len(nrow(ptasks)), function(j) {
              owner_b <- if (!is.na(ptasks$owner[j]) && nchar(ptasks$owner[j]) > 0L) {
                tags$span(style = "font-size:0.72em; color:#888; margin-left:0.3em;",
                          paste0("[", ptasks$owner[j], "]"))
              }
              tags$li(style = "margin-bottom:0.25em; font-size:0.85em;", ptasks$title[j], owner_b)
            })
          )
        }

        div(class = "project-board-card",
            style = paste0("border-left: 4px solid ", priority_col(ppri), ";"),
          div(style = "display:flex; align-items:baseline; gap:0.4em; margin-bottom:0.2em;",
              tags$strong(projects$title[i]),
              tags$span(class = paste0("priority-", ppri), ppri)),
          comp_ui,
          tags$p(style = "font-size:0.82em; color:#555; margin:0.3em 0 0.4em;",
                 tags$em("Next: "), pnext),
          task_items
        )
      })

      div(class = "project-board-grid", boards)
    })
  })
}
