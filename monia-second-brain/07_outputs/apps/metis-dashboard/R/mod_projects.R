# mod_projects.R
# Project and task management with kanban board + table views.

projects_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Projects"),
      p("Track projects and move tasks through the workflow.")
    ),

    layout_columns(
      col_widths = c(6, 6),
      card(
        card_header("Add project"),
        card_body(
          textInput(ns("project_title"), "Title"),
          layout_columns(
            col_widths = c(4, 4, 4),
            textInput(ns("project_domain"), "Domain", value = "general"),
            selectInput(ns("project_status_sel"), "Status",
                        choices = c("active","planned","blocked","done")),
            selectInput(ns("project_priority"), "Priority",
                        choices = c("high","medium","low"))
          ),
          textInput(ns("project_next_step"), "Next step"),
          div(class = "action-row",
              actionButton(ns("save_project"), tagList(icon("plus"), " Save project"), class = "btn-primary")),
          textOutput(ns("project_status_text"))
        )
      ),
      card(
        card_header("Add task"),
        card_body(
          uiOutput(ns("task_project_ui")),
          textInput(ns("task_title"), "Task"),
          layout_columns(
            col_widths = c(4, 4, 4),
            selectInput(ns("task_status_sel"), "Status",
                        choices = c("open","in_progress","blocked","done")),
            textInput(ns("task_due_date"), "Due date (YYYY-MM-DD)"),
            textInput(ns("task_owner"), "Owner", value = "Metis")
          ),
          textInput(ns("task_notes"), "Notes"),
          div(class = "action-row",
              actionButton(ns("save_task"), tagList(icon("plus"), " Save task"), class = "btn-outline-secondary")),
          textOutput(ns("task_status_text"))
        )
      )
    ),

    # ── Tasks view — toggle kanban / table / strategy ───────────────
    card(
      card_header(
        div(style = "display:flex; justify-content:space-between; align-items:center;",
          span("Tasks"),
          div(class = "view-toggle",
            actionButton(ns("view_kanban"),   tagList(icon("columns"), " Kanban"),
                         class = "btn btn-sm btn-outline-secondary"),
            actionButton(ns("view_table"),    tagList(icon("table"), " Table"),
                         class = "btn btn-sm btn-outline-secondary"),
            actionButton(ns("view_strategy"), tagList(icon("sitemap"), " Strategy"),
                         class = "btn btn-sm btn-outline-secondary")
          )
        )
      ),
      card_body(uiOutput(ns("tasks_view")))
    ),

    # ── Projects table ──────────────────────────────────────────────
    card(
      card_header("All projects"),
      card_body(class = "card-scroll", tableOutput(ns("projects_table")))
    )
  )
}

projects_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh_trigger     <- reactiveVal(0L)
    project_status_text <- reactiveVal("")
    task_status_text    <- reactiveVal("")
    view_mode           <- reactiveVal("kanban")   # "kanban" | "table" | "strategy"
    invoke_task_id      <- reactiveVal(NULL)

    observeEvent(input$view_kanban,   view_mode("kanban"))
    observeEvent(input$view_table,    view_mode("table"))
    observeEvent(input$view_strategy, view_mode("strategy"))

    output$task_project_ui <- renderUI({
      selectInput(ns("task_project"), "Project", choices = project_choices(paths))
    })

    # ── Save project ────────────────────────────────────────────────
    observeEvent(input$save_project, {
      req(nzchar(input$project_title))
      insert_project(paths, input$project_title, input$project_domain,
                     input$project_status_sel, input$project_priority,
                     input$project_next_step)
      log_job(paths, "save_project", "success", input$project_title)
      project_status_text(sprintf("Saved: %s", input$project_title))
      refresh_trigger(refresh_trigger() + 1L)
    })

    # ── Save task ───────────────────────────────────────────────────
    observeEvent(input$save_task, {
      req(input$task_project, nzchar(input$task_title))
      insert_task(paths, input$task_project, input$task_title,
                  input$task_status_sel, input$task_due_date,
                  input$task_owner, input$task_notes)
      log_job(paths, "save_task", "success", input$task_title)
      task_status_text(sprintf("Saved: %s", input$task_title))
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$project_status_text <- renderText(project_status_text())
    output$task_status_text    <- renderText(task_status_text())

    # ── Single kanban action observer (JS → Shiny.setInputValue) ───
    observeEvent(input$kanban_action, {
      req(input$kanban_action)
      act <- input$kanban_action
      req(is.list(act), !is.null(act$task_id), !is.null(act$status))
      update_task_status(paths, act$task_id, act$status)
      refresh_trigger(refresh_trigger() + 1L)
    }, ignoreNULL = TRUE)

    # ── Agent invoke modal ──────────────────────────────────────────
    observeEvent(input$kanban_invoke, {
      act <- input$kanban_invoke
      req(is.list(act), !is.null(act$task_id))
      invoke_task_id(act$task_id)

      task <- tryCatch(
        db_table(paths, sprintf(
          "SELECT t.*, COALESCE(p.title,'') AS project_name FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id WHERE t.task_id = '%s'",
          act$task_id
        )),
        error = function(...) data.frame()
      )
      if (!nrow(task)) return()

      owner      <- task$owner[1L]
      title      <- task$title[1L]
      proj_name  <- task$project_name[1L]
      slug       <- agent_slug(owner)

      # Load context document: project-specific first, then generic README
      proj_slug_name  <- make_slug(proj_name)
      ctx_specific    <- file.path(paths$agents_root, slug, paste0(proj_slug_name, "-context.md"))
      ctx_readme      <- file.path(paths$agents_root, slug, "README.md")

      ctx_content <- if (file.exists(ctx_specific)) {
        paste(readLines(ctx_specific, warn = FALSE), collapse = "\n")
      } else if (file.exists(ctx_readme)) {
        paste(head(readLines(ctx_readme, warn = FALSE), 60L), collapse = "\n")
      } else {
        paste0("No context document found.\nAgent: ", owner, "\nLook in: 02_agents/", slug, "/")
      }

      invoke_cmd <- paste0("/", slug, " ", title)
      copy_js    <- sprintf(
        "navigator.clipboard.writeText('%s').then(function(){var b=document.getElementById('%s');b.innerText='Copied!';setTimeout(function(){b.innerText='Copy command';},2000);});",
        gsub("'", "\\'", invoke_cmd), ns("copy_invoke_btn")
      )

      current_notes <- if (!is.na(task$notes[1L]) && nzchar(task$notes[1L])) task$notes[1L] else ""

      showModal(modalDialog(
        title = paste0("Invoke \u2014 ", owner),
        size  = "l",
        tagList(
          tags$p(tags$strong("Task: "), title,
                 tags$span(style = "font-size:0.8rem; color:#6d7c74; margin-left:0.5em;",
                           paste0("[", proj_name, "]"))),
          div(class = "invoke-cmd-row",
            tags$code(class = "invoke-cmd-text", invoke_cmd),
            tags$button(
              id    = ns("copy_invoke_btn"),
              class = "btn btn-sm btn-outline-secondary",
              onclick = copy_js,
              tagList(icon("copy"), "  Copy command")
            )
          ),
          tags$hr(),
          div(style = "max-height:280px; overflow-y:auto; background:#f8f6f1; border-radius:4px; padding:0.5rem 0.75rem;",
            tags$pre(style = "font-size:0.76rem; white-space:pre-wrap; margin:0; color:#2d3a3e;",
                     ctx_content)
          ),
          tags$hr(),
          textAreaInput(ns("invoke_notes_text"), "Delegation notes (saved to task):",
                        value = current_notes,
                        placeholder = "What should the agent focus on? Record outcome here after running.",
                        rows = 3L),
          div(class = "action-row",
            actionButton(ns("save_invoke_notes"), tagList(icon("save"), " Save notes"),
                         class = "btn-sm btn-outline-secondary"))
        ),
        footer = modalButton("Close")
      ))
    }, ignoreNULL = TRUE)

    observeEvent(input$save_invoke_notes, {
      req(invoke_task_id())
      notes_val <- if (!is.null(input$invoke_notes_text)) input$invoke_notes_text else ""
      update_task_notes(paths, invoke_task_id(), notes_val)
      showNotification("Notes saved to task.", type = "message", duration = 2L)
    })

    # ── Tasks view ──────────────────────────────────────────────────
    output$tasks_view <- renderUI({
      refresh_trigger()
      if (view_mode() == "table") {
        tableOutput(ns("tasks_table"))
      } else if (view_mode() == "strategy") {
        strategy_view_ui(paths, ns)
      } else {
        kanban_ui_output(paths, ns)
      }
    })

    output$tasks_table <- renderTable({
      refresh_trigger()
      db_table(paths, paste(
        "SELECT t.title, p.title AS project, t.status,",
        "COALESCE(t.due_date,'') AS due, t.owner",
        "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id",
        "ORDER BY t.created_at DESC"
      ))
    }, bordered = TRUE, striped = TRUE, spacing = "s")

    output$projects_table <- renderTable({
      refresh_trigger()
      db_table(paths,
        "SELECT title, domain, status, priority, next_step FROM projects ORDER BY created_at DESC")
    }, bordered = TRUE, striped = TRUE, spacing = "s")
  })
}

# ── Kanban board builder ────────────────────────────────────────────────────

kanban_ui_output <- function(paths, ns) {
  tasks <- tryCatch(
    db_table(paths, paste(
      "SELECT t.task_id, t.title, t.status, t.owner, t.due_date,",
      "p.title AS project_name",
      "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id",
      "ORDER BY t.created_at DESC"
    )),
    error = function(...) data.frame()
  )

  statuses <- c("open", "in_progress", "blocked", "done")
  labels   <- c("Open", "In Progress", "Blocked", "Done")
  colors   <- c("#174c4f", "#2d6073", "#c0392b", "#27ae60")

  # JS action helper — uses namespaced input id
  ns_id  <- ns("kanban_action")
  js_act <- function(task_id, new_status) {
    sprintf(
      "Shiny.setInputValue('%s', {task_id: '%s', status: '%s'}, {priority: 'event'})",
      ns_id, task_id, new_status
    )
  }

  cols <- lapply(seq_along(statuses), function(si) {
    s      <- statuses[si]
    s_lbl  <- labels[si]
    s_col  <- colors[si]
    s_tasks <- if (nrow(tasks)) tasks[tasks$status == s, , drop = FALSE] else data.frame()

    cards <- if (!nrow(s_tasks)) {
      div(class = "kanban-empty", "No tasks")
    } else {
      lapply(seq_len(nrow(s_tasks)), function(i) {
        tid   <- s_tasks$task_id[i]
        title <- s_tasks$title[i]
        proj  <- if (!is.na(s_tasks$project_name[i])) s_tasks$project_name[i] else ""
        owner <- if (!is.na(s_tasks$owner[i]) && nzchar(s_tasks$owner[i])) s_tasks$owner[i] else ""
        due   <- if (!is.na(s_tasks$due_date[i]) && nzchar(s_tasks$due_date[i])) s_tasks$due_date[i] else ""

        # [Invoke] button for agent-owned tasks
        invoke_btn <- if (owner %in% names(agent_slug_map())) {
          ns_inv <- ns("kanban_invoke")
          tags$button(
            class = "btn btn-xs task-invoke-btn",
            onclick = sprintf(
              "Shiny.setInputValue('%s',{task_id:'%s',owner:'%s'},{priority:'event'})",
              ns_inv, tid, owner
            ),
            tagList(icon("robot"), "  Invoke")
          )
        }

        # Status-appropriate action buttons
        btns <- switch(s,
          open = tagList(
            tags$button(class = "btn btn-sm task-status-btn btn-outline-secondary",
                        onclick = js_act(tid, "in_progress"), "→ In Progress"),
            tags$button(class = "btn btn-sm task-status-btn btn-outline-success",
                        onclick = js_act(tid, "done"), "✓ Done")
          ),
          in_progress = tagList(
            tags$button(class = "btn btn-sm task-status-btn btn-outline-success",
                        onclick = js_act(tid, "done"), "✓ Done"),
            tags$button(class = "btn btn-sm task-status-btn btn-outline-danger",
                        onclick = js_act(tid, "blocked"), "⊘ Block")
          ),
          blocked = tagList(
            tags$button(class = "btn btn-sm task-status-btn btn-outline-secondary",
                        onclick = js_act(tid, "in_progress"), "→ In Progress"),
            tags$button(class = "btn btn-sm task-status-btn btn-outline-success",
                        onclick = js_act(tid, "done"), "✓ Done")
          ),
          done = tagList(
            tags$button(class = "btn btn-sm task-status-btn btn-outline-secondary",
                        onclick = js_act(tid, "open"), "↩ Reopen")
          )
        )

        div(
          class = paste0("kanban-card", if (s == "blocked") " kanban-card-blocked" else ""),
          div(class = "kanban-card-title", title),
          if (nzchar(proj))  div(class = "kanban-card-meta", tagList(icon("folder"), "  "), proj),
          if (nzchar(owner)) div(class = "kanban-card-meta", tagList(icon("user"), "  "), owner),
          if (nzchar(due))   div(class = "kanban-card-meta",
                                 style = if (due < format(Sys.Date())) "color:#c0392b;" else "",
                                 tagList(icon("calendar"), "  "), due),
          div(class = "kanban-card-actions", btns,
              if (!is.null(invoke_btn)) invoke_btn)
        )
      })
    }

    div(class = "kanban-col",
      div(class = "kanban-col-header",
          style = paste0("border-top: 3px solid ", s_col, ";"),
          span(s_lbl),
          span(class = "kanban-count", nrow(s_tasks))
      ),
      cards
    )
  })

  div(class = "kanban-board", cols)
}

# ── Agent name → slug mapping ───────────────────────────────────────────────

agent_slug_map <- function() {
  c(
    "Software Engineer"   = "software-engineer",
    "Librarian"           = "librarian",
    "Library Curator"     = "librarian",
    "PhD Architect"       = "phd-architect",
    "Writing Partner"     = "writing-partner",
    "Methods Coach"       = "methods-coach",
    "Meeting Memory"      = "meeting-memory",
    "News Radar"          = "news-radar",
    "Builder"             = "builder",
    "Dashboard Engineer"  = "dashboard-engineer",
    "Presentation Maker"  = "presentation-maker",
    "Learning Coach"      = "learning-coach",
    "Career Coach"        = "career-coach",

    "News Aggregator"     = "news-aggregator",
    "UX Engineer"         = "ux-engineer",
    "Epidemiologist"      = "epidemiologist",
    "Cybersecurity"       = "cybersecurity",
    "Data Guardian"       = "data-guardian"
  )
}

agent_slug <- function(owner_name) {
  m <- agent_slug_map()
  if (owner_name %in% names(m)) unname(m[owner_name]) else make_slug(owner_name)
}

# ── Strategy view builder ───────────────────────────────────────────────────

strategy_view_ui <- function(paths, ns) {
  projects <- tryCatch(
    db_table(paths, "SELECT project_id, title, domain FROM projects WHERE status = 'active' ORDER BY priority DESC, title"),
    error = function(...) data.frame()
  )

  if (!nrow(projects)) return(div(class = "empty-state", "No active projects."))

  all_tasks <- tryCatch(
    db_table(paths, "SELECT project_id, status, owner FROM tasks"),
    error = function(...) data.frame()
  )

  known_agents <- names(agent_slug_map())

  rows <- lapply(seq_len(nrow(projects)), function(i) {
    pid    <- projects$project_id[i]
    ptasks <- if (nrow(all_tasks)) all_tasks[all_tasks$project_id == pid, , drop = FALSE] else
               data.frame(status = character(), owner = character())

    open_n    <- sum(ptasks$status == "open")
    in_prog_n <- sum(ptasks$status == "in_progress")
    blocked_n <- sum(ptasks$status == "blocked")
    done_n    <- sum(ptasks$status == "done")
    agent_n   <- if (nrow(ptasks) && "owner" %in% names(ptasks)) {
      sum(!is.na(ptasks$owner) & ptasks$owner %in% known_agents)
    } else 0L
    bottleneck <- in_prog_n > 3L

    mk_stage <- function(label, count, active = FALSE, warn = FALSE, check = FALSE) {
      cls <- paste("strategy-stage",
                   if (active || check) "active" else "",
                   if (warn) "warn" else "")
      div(class = trimws(cls),
        div(class = "strategy-stage-count",
            if (check) "\u2713" else as.character(count)),
        div(class = "strategy-stage-label", label)
      )
    }

    div(class = "strategy-row",
      div(class = "strategy-project-header",
        tags$strong(projects$title[i]),
        tags$span(class = paste0("domain-badge domain-", make_slug(projects$domain[i])),
                  projects$domain[i]),
        if (bottleneck) tags$span(class = "strategy-bottleneck-chip",
                                  tagList(icon("triangle-exclamation"), "  Bottleneck"))
      ),
      div(class = "strategy-flow",
        mk_stage("Defined", 1L, check = TRUE),
        div(class = "strategy-arrow", "\u2192"),
        mk_stage("Open tasks", open_n, active = open_n > 0L),
        div(class = "strategy-arrow", "\u2192"),
        mk_stage("Agent assigned", agent_n, active = agent_n > 0L),
        div(class = "strategy-arrow", "\u2192"),
        mk_stage("In progress", in_prog_n, active = in_prog_n > 0L, warn = bottleneck),
        div(class = "strategy-arrow", "\u2192"),
        mk_stage("Done", done_n, active = done_n > 0L)
      )
    )
  })

  div(class = "strategy-board", rows)
}
