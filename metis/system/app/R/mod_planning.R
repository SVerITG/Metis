# mod_planning.R
# Planner tab: weekly focus board, kanban, and Gantt timeline.

planning_ui <- function(id) {
  ns <- NS(id)
  tagList(
    div(class = "page-intro",
      h1("Planner"),
      p("Weekly focus, task board, and project timeline across all your work.")
    ),

    # ── filter row ──────────────────────────────────────────────────
    div(class = "action-row mb-3",
      actionButton(ns("btn_new_task"), "+ New Task", class = "btn-primary btn-sm"),
      uiOutput(ns("flt_project_ui")),
      selectInput(ns("flt_domain"), NULL,
                  choices = c("All domains" = ""), width = "160px")
    ),

    # ── focus board ─────────────────────────────────────────────────
    div(class = "planner-section",
      div(class = "planner-section-header",
        span("This Week's Focus"),
        actionButton(ns("btn_pin"), "+ Pin", class = "btn-sm btn-outline-secondary")
      ),
      uiOutput(ns("focus_board"))
    ),

    tags$hr(),

    # ── kanban ──────────────────────────────────────────────────────
    div(class = "planner-section",
      div(class = "planner-section-header", span("Tasks")),
      uiOutput(ns("kanban_board"))
    ),

    tags$hr(),

    # ── gantt ───────────────────────────────────────────────────────
    div(class = "planner-section",
      div(class = "planner-section-header", span("Project Timeline")),
      plotly::plotlyOutput(ns("gantt"), height = "280px")
    ),

  )
}

planning_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh      <- reactiveVal(0L)
    current_week <- reactive(format(Sys.Date(), "%Y-%W"))

    # ── filter dropdowns ────────────────────────────────────────────
    output$flt_project_ui <- renderUI({
      refresh()
      proj <- tryCatch(
        db_table(paths, "SELECT project_id, title FROM projects ORDER BY title"),
        error = function(...) data.frame(project_id = character(), title = character())
      )
      choices <- c("All projects" = "", stats::setNames(proj$project_id, proj$title))
      selectInput(ns("flt_project"), NULL, choices = choices, width = "200px")
    })

    # populate domain filter from project domains
    observe({
      refresh()
      domains <- tryCatch(
        db_table(paths, "SELECT DISTINCT domain FROM projects WHERE domain IS NOT NULL ORDER BY domain"),
        error = function(...) data.frame(domain = character())
      )
      choices <- c("All domains" = "", stats::setNames(domains$domain, domains$domain))
      updateSelectInput(session, "flt_domain", choices = choices)
    })

    # ── data reactives ───────────────────────────────────────────────
    tasks_data <- reactive({
      refresh()
      flt_proj   <- input$flt_project %||% ""
      flt_domain <- input$flt_domain  %||% ""

      sql <- paste(
        "SELECT t.task_id, t.project_id, t.title, t.status,",
        "COALESCE(t.due_date,'') AS due_date,",
        "COALESCE(t.owner,'') AS owner,",
        "COALESCE(t.notes,'') AS notes,",
        "COALESCE(t.created_at,'') AS created_at,",
        "COALESCE(p.title,'—') AS project_title,",
        "COALESCE(p.domain,'') AS domain",
        "FROM tasks t",
        "LEFT JOIN projects p ON t.project_id = p.project_id",
        "WHERE 1=1"
      )
      if (nzchar(flt_proj))   sql <- paste0(sql, sprintf(" AND t.project_id = '%s'", flt_proj))
      if (nzchar(flt_domain)) sql <- paste0(sql, sprintf(" AND p.domain = '%s'", flt_domain))
      sql <- paste0(sql, " ORDER BY t.created_at DESC")
      tryCatch(db_table(paths, sql), error = function(...) data.frame())
    })

    focus_data <- reactive({
      refresh()
      get_focus_items(paths, current_week())
    })

    # ── Focus board ─────────────────────────────────────────────────
    output$focus_board <- renderUI({
      items <- focus_data()
      if (!nrow(items)) {
        return(div(class = "empty-state",
          "Nothing pinned yet \u2014 click + Pin to add this week\u2019s priorities"))
      }
      div(class = "focus-board",
        lapply(seq_len(nrow(items)), function(i) {
          item <- items[i, ]
          type_icon <- if (item$item_type == "task") "\u2756" else "\u2b21"
          div(class = "focus-chip",
            span(class = paste0("focus-type-", item$item_type), type_icon),
            span(item$label),
            tags$button("\u00d7", class = "focus-unpin",
              onclick = sprintf(
                "Shiny.setInputValue('%s', {item_id:'%s',week:'%s'}, {priority:'event'})",
                ns("unpin_click"), item$item_id, item$week
              )
            )
          )
        })
      )
    })

    observeEvent(input$unpin_click, {
      req(input$unpin_click)
      unpin_focus_item(paths, input$unpin_click$item_id, input$unpin_click$week)
      refresh(refresh() + 1L)
    })

    # ── Modal triggers ───────────────────────────────────────────────
    observeEvent(input$btn_new_task, {
      showModal(modalDialog(
        title = "New Task",
        uiOutput(ns("new_task_project_ui")),
        textInput(ns("new_task_title"), "Title"),
        layout_columns(
          col_widths = c(4, 4, 4),
          selectInput(ns("new_task_status"), "Status",
                      choices = c("open", "in_progress", "blocked", "done")),
          textInput(ns("new_task_due"), "Due date (YYYY-MM-DD)"),
          textInput(ns("new_task_owner"), "Owner", value = "Metis")
        ),
        textInput(ns("new_task_notes"), "Notes"),
        footer = tagList(
          actionButton(ns("save_new_task"), "Save task", class = "btn-primary"),
          modalButton("Cancel")
        ),
        easyClose = TRUE
      ))
    })

    observeEvent(input$btn_pin, {
      showModal(modalDialog(
        title = "Pin to This Week",
        uiOutput(ns("pin_select_ui")),
        footer = tagList(
          actionButton(ns("save_pin"), "Pin item", class = "btn-primary"),
          modalButton("Cancel")
        ),
        easyClose = TRUE
      ))
    })

    # ── Pin modal content ────────────────────────────────────────────
    output$pin_select_ui <- renderUI({
      plannable <- get_all_plannable(paths)
      if (!nrow(plannable)) {
        return(p("No tasks or projects available to pin."))
      }
      choices <- stats::setNames(
        paste0(plannable$item_type, "|||", plannable$item_id),
        sprintf("[%s] %s", plannable$item_type, plannable$label)
      )
      tagList(
        selectInput(ns("pin_selection"), "Choose item to pin", choices = choices, width = "100%"),
        p(class = "text-muted", style = "font-size:0.82rem;",
          sprintf("Week: %s", current_week()))
      )
    })

    observeEvent(input$save_pin, {
      req(input$pin_selection)
      parts     <- strsplit(input$pin_selection, "\\|\\|\\|")[[1]]
      item_type <- parts[[1]]
      item_id   <- parts[[2]]
      plannable <- get_all_plannable(paths)
      row       <- plannable[
        plannable$item_id == item_id & plannable$item_type == item_type, ,
        drop = FALSE
      ]
      label <- if (nrow(row)) row$label[[1]] else item_id
      pin_focus_item(paths, item_id, item_type, label, current_week())
      refresh(refresh() + 1L)
      removeModal()
    })

    # ── Kanban board ─────────────────────────────────────────────────
    output$kanban_board <- renderUI({
      tasks <- tasks_data()
      if (!nrow(tasks)) {
        return(div(class = "empty-state", "No tasks yet \u2014 click + New Task to get started."))
      }

      statuses <- c("open", "in_progress", "blocked", "done")
      labels   <- c("Open", "In Progress", "Blocked", "Done")

      div(class = "kanban-wrapper",
        lapply(seq_along(statuses), function(i) {
          st     <- statuses[[i]]
          subset <- tasks[tasks$status == st, , drop = FALSE]
          div(class = "kanban-col",
            div(class = "kanban-col-header",
              span(labels[[i]]),
              span(class = "kanban-count", nrow(subset))
            ),
            div(class = "kanban-col-body",
              if (!nrow(subset)) {
                div(class = "kanban-empty", "\u2014")
              } else {
                lapply(seq_len(nrow(subset)), function(j) {
                  task <- subset[j, ]
                  div(class = "kanban-card",
                    div(class = "kanban-card-title", task$title),
                    div(class = "kanban-card-meta",
                      span(class = "badge-project", task$project_title),
                      if (nzchar(task$due_date))
                        span(class = "kanban-due", task$due_date)
                    ),
                    div(class = "kanban-card-actions",
                      if (st != "in_progress")
                        tags$button("Start",
                          class = "btn btn-xs btn-outline-secondary",
                          onclick = sprintf(
                            "Shiny.setInputValue('%s',{task_id:'%s',status:'in_progress'},{priority:'event'})",
                            ns("kanban_action"), task$task_id
                          )
                        ),
                      if (st != "done")
                        tags$button("Done",
                          class = "btn btn-xs btn-outline-secondary",
                          onclick = sprintf(
                            "Shiny.setInputValue('%s',{task_id:'%s',status:'done'},{priority:'event'})",
                            ns("kanban_action"), task$task_id
                          )
                        )
                    )
                  )
                })
              }
            )
          )
        })
      )
    })

    observeEvent(input$kanban_action, {
      req(input$kanban_action)
      update_task_status(paths, input$kanban_action$task_id, input$kanban_action$status)
      refresh(refresh() + 1L)
    })

    # ── New task modal content ────────────────────────────────────────
    output$new_task_project_ui <- renderUI({
      selectInput(ns("new_task_project"), "Project",
                  choices = project_choices(paths), width = "100%")
    })

    observeEvent(input$save_new_task, {
      req(nzchar(input$new_task_title))
      insert_task(paths,
        project_id = input$new_task_project %||% "",
        title      = input$new_task_title,
        status     = input$new_task_status %||% "open",
        due_date   = input$new_task_due    %||% "",
        owner      = input$new_task_owner  %||% "Metis",
        notes      = input$new_task_notes  %||% ""
      )
      refresh(refresh() + 1L)
      removeModal()
      updateTextInput(session, "new_task_title", value = "")
      updateTextInput(session, "new_task_notes", value = "")
    })

    # ── Gantt ────────────────────────────────────────────────────────
    output$gantt <- plotly::renderPlotly({
      refresh()
      gantt_data <- tryCatch(
        db_table(paths,
          "SELECT t.project_id,
                  COALESCE(p.title, t.project_id) AS project_title,
                  COALESCE(p.status, 'active')     AS proj_status,
                  MIN(t.created_at)                AS start_date,
                  MAX(COALESCE(NULLIF(t.due_date,''), DATE('now','+30 days'))) AS end_date,
                  COUNT(*)                          AS task_count,
                  SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END) AS done_count
           FROM tasks t
           LEFT JOIN projects p ON t.project_id = p.project_id
           WHERE t.project_id IS NOT NULL AND t.project_id != ''
           GROUP BY t.project_id
           ORDER BY start_date ASC"
        ),
        error = function(...) data.frame()
      )

      if (!nrow(gantt_data)) {
        return(plotly::plot_ly() |>
          plotly::layout(
            title = list(text = "No project data yet", font = list(size = 13)),
            xaxis = list(visible = FALSE),
            yaxis = list(visible = FALSE),
            plot_bgcolor  = "rgba(0,0,0,0)",
            paper_bgcolor = "rgba(0,0,0,0)"
          ))
      }

      gantt_data$start_date <- as.Date(substr(gantt_data$start_date, 1, 10))
      gantt_data$end_date   <- as.Date(substr(gantt_data$end_date,   1, 10))
      gantt_data$pct_done   <- ifelse(
        gantt_data$task_count > 0,
        round(gantt_data$done_count / gantt_data$task_count * 100),
        0L
      )

      today     <- Sys.Date()
      x_min     <- today - 90
      x_max     <- today + 120

      status_colors <- c(
        "active"  = "#0071e3",
        "done"    = "#30a46c",
        "blocked" = "#e03131",
        "planned" = "#f59f00"
      )

      fig <- plotly::plot_ly()
      for (i in seq_len(nrow(gantt_data))) {
        row   <- gantt_data[i, ]
        color <- status_colors[[row$proj_status]] %||% "#0071e3"
        fig   <- plotly::add_segments(
          fig,
          x    = ~row$start_date,
          xend = ~row$end_date,
          y    = ~row$project_title,
          yend = ~row$project_title,
          line = list(color = color, width = 18),
          hovertemplate = paste0(
            "<b>", row$project_title, "</b><br>",
            "Start: ", row$start_date, "<br>",
            "End: ",   row$end_date,   "<br>",
            "Done: ",  row$pct_done,   "%<br>",
            "Tasks: ", row$task_count,
            "<extra></extra>"
          ),
          showlegend = FALSE
        )
      }

      fig |>
        plotly::add_segments(
          x = ~today, xend = ~today,
          y = 0, yend = nrow(gantt_data) + 1,
          line = list(color = "rgba(224,49,49,0.6)", width = 1.5, dash = "dot"),
          hoverinfo = "none", showlegend = FALSE
        ) |>
        plotly::layout(
          xaxis = list(
            range     = c(x_min, x_max),
            title     = "",
            type      = "date",
            tickformat = "%b %Y",
            showgrid  = TRUE,
            gridcolor = "rgba(0,0,0,0.07)"
          ),
          yaxis = list(
            title     = "",
            showgrid  = FALSE,
            autorange = "reversed"
          ),
          margin       = list(l = 0, r = 20, t = 10, b = 30),
          plot_bgcolor  = "rgba(0,0,0,0)",
          paper_bgcolor = "rgba(0,0,0,0)",
          font          = list(family = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', system-ui, sans-serif",
                               size = 11, color = "#1d1d1f")
        ) |>
        plotly::config(displayModeBar = FALSE)
    })
  })
}
