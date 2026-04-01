# mod_agents.R
# Agent output page: list agents, quick-invoke templates, run history, task counts.

agents_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "page-intro",
      h1("Agents"),
      p("Browse agents, copy invoke commands for Claude Code, and track delegation history.")
    ),

    layout_columns(
      col_widths = c(3, 9),

      # ── Agent list sidebar ──────────────────────────────────────────
      card(
        card_header("Agents"),
        card_body(uiOutput(ns("agent_list")))
      ),

      # ── Agent detail panel ─────────────────────────────────────────
      card(
        card_header(uiOutput(ns("agent_detail_header"))),
        card_body(uiOutput(ns("agent_detail")))
      )
    )
  )
}

agents_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    selected_agent <- reactiveVal(NULL)

    # ── List agents from filesystem ─────────────────────────────────
    output$agent_list <- renderUI({
      agent_dirs <- tryCatch(
        list.dirs(paths$agents_root, full.names = FALSE, recursive = FALSE),
        error = function(...) character()
      )
      agent_dirs <- sort(agent_dirs[nzchar(agent_dirs)])

      if (!length(agent_dirs)) {
        return(div(class = "empty-state",
               "No agent directories found in 02_agents/."))
      }

      ns_id <- ns("select_agent")
      tagList(lapply(agent_dirs, function(slug) {
        # Task count for this agent
        display_name <- agent_display_name(slug)
        task_count <- tryCatch(
          db_scalar(paths, sprintf(
            "SELECT COUNT(*) FROM tasks WHERE LOWER(owner) = LOWER('%s') AND status != 'done'",
            display_name
          )),
          error = function(...) 0L
        )

        badge <- if (task_count > 0L) {
          tags$span(class = "agent-task-badge", task_count)
        }

        div(
          class = "agent-list-item",
          onclick = sprintf(
            "Shiny.setInputValue('%s','%s',{priority:'event'})",
            ns_id, slug
          ),
          div(class = "agent-list-name", display_name, badge)
        )
      }))
    })

    observeEvent(input$select_agent, {
      selected_agent(input$select_agent)
    }, ignoreNULL = TRUE)

    # ── Agent detail header ─────────────────────────────────────────
    output$agent_detail_header <- renderUI({
      slug <- selected_agent()
      if (is.null(slug)) return(span("Select an agent"))
      span(agent_display_name(slug))
    })

    # ── Agent detail panel ─────────────────────────────────────────
    output$agent_detail <- renderUI({
      slug <- selected_agent()
      if (is.null(slug)) {
        return(div(class = "empty-state",
               tagList(icon("hand-pointer"), "  Select an agent from the list.")))
      }

      display_name <- agent_display_name(slug)

      # 1. Quick-invoke templates
      templates <- agent_invoke_templates(slug)
      invoke_ui <- if (length(templates)) {
        tagList(
          tags$p(style = "font-size:0.82rem; color:#6d7c74; margin-bottom:0.5rem;",
                 "Copy a command below and paste into Claude Code:"),
          div(class = "invoke-templates",
            lapply(seq_along(templates), function(i) {
              cmd <- templates[[i]]$cmd
              label <- templates[[i]]$label
              btn_id <- sprintf("copy_tpl_%s_%d", slug, i)
              copy_js <- sprintf(
                "navigator.clipboard.writeText('%s').then(function(){var b=document.getElementById('%s');b.innerText='Copied!';setTimeout(function(){b.innerText='Copy';},1500);});",
                gsub("'", "\\'", cmd, fixed = TRUE), btn_id
              )
              div(class = "invoke-template-row",
                div(class = "invoke-template-label", label),
                div(class = "invoke-cmd-row",
                  tags$code(class = "invoke-cmd-text", cmd),
                  tags$button(
                    id = btn_id,
                    class = "btn btn-xs btn-outline-secondary",
                    onclick = copy_js,
                    "Copy"
                  )
                )
              )
            })
          )
        )
      } else {
        tags$p(style = "color:#aaa; font-size:0.84rem;",
               sprintf("No quick-invoke templates defined for %s.", display_name))
      }

      # 2. Task count + list
      open_tasks <- tryCatch(
        db_table(paths, sprintf(
          "SELECT t.title, COALESCE(p.title,'---') AS project, t.status, COALESCE(t.due_date,'') AS due FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id WHERE LOWER(t.owner) = LOWER('%s') AND t.status != 'done' ORDER BY t.created_at DESC LIMIT 10",
          display_name
        )),
        error = function(...) data.frame()
      )

      done_count <- tryCatch(
        db_scalar(paths, sprintf(
          "SELECT COUNT(*) FROM tasks WHERE LOWER(owner) = LOWER('%s') AND status = 'done'",
          display_name
        )),
        error = function(...) 0L
      )

      tasks_ui <- if (!nrow(open_tasks)) {
        tags$p(style = "color:#6d7c74; font-size:0.85rem;",
               sprintf("No open tasks assigned to %s. %d completed.", display_name, done_count))
      } else {
        tagList(
          tags$p(style = "font-size:0.82rem; color:#6d7c74; margin-bottom:0.3rem;",
                 sprintf("%d open task(s) · %d completed", nrow(open_tasks), done_count)),
          tags$ul(style = "padding-left:1.1em; font-size:0.84rem;",
            lapply(seq_len(nrow(open_tasks)), function(i) {
              t <- open_tasks[i, ]
              tags$li(
                tags$strong(t$title),
                tags$span(style = "color:#6d7c74; font-size:0.78em; margin-left:0.3em;",
                          paste0("[", t$project, "]")),
                tags$span(class = paste0("priority-", t$status),
                          style = "margin-left:0.3em;", t$status)
              )
            })
          )
        )
      }

      # 3. Run history
      runs <- tryCatch(
        db_table(paths, sprintf(
          "SELECT task_summary, output_path, created_at FROM agent_runs WHERE agent_slug = '%s' ORDER BY created_at DESC LIMIT 8",
          slug
        )),
        error = function(...) data.frame()
      )

      runs_ui <- if (!nrow(runs)) {
        tags$p(style = "color:#aaa; font-size:0.84rem;",
               "No recorded runs yet. Runs are logged when agents write to 07_outputs/reviews/.")
      } else {
        tags$ul(style = "padding-left:1.1em; font-size:0.84rem;",
          lapply(seq_len(nrow(runs)), function(i) {
            r <- runs[i, ]
            tags$li(
              tags$strong(r$task_summary),
              if (!is.na(r$output_path) && nzchar(r$output_path))
                tags$span(style = "color:#2d6073; font-size:0.78em; margin-left:0.3em;",
                          paste0(" -> ", basename(r$output_path))),
              tags$span(style = "color:#888; font-size:0.72em; margin-left:0.3em;",
                        r$created_at)
            )
          })
        )
      }

      # 4. Latest output files
      outputs_dir <- file.path(paths$second_brain_root, "07_outputs", "reviews", slug)
      output_files_ui <- if (dir.exists(outputs_dir)) {
        files <- list.files(outputs_dir, recursive = FALSE, full.names = FALSE)
        files <- sort(files, decreasing = TRUE)
        if (!length(files)) {
          tags$p(style = "color:#888; font-size:0.84rem;", "No output files yet.")
        } else {
          tags$ul(style = "padding-left:1.1em; font-size:0.84rem;",
            lapply(head(files, 8L), function(f) {
              tags$li(tagList(icon("file-lines"), "  "), f)
            })
          )
        }
      } else {
        tags$p(style = "color:#aaa; font-style:italic; font-size:0.84rem;",
               paste0("No outputs folder yet. Create: 07_outputs/reviews/", slug, "/"))
      }

      # 5. Context docs
      agent_dir   <- file.path(paths$agents_root, slug)
      ctx_files   <- if (dir.exists(agent_dir)) {
        list.files(agent_dir, pattern = "\\.md$", full.names = FALSE)
      } else character()
      context_files_ui <- if (length(ctx_files)) {
        tags$ul(style = "padding-left:1.1em; font-size:0.84rem;",
          lapply(ctx_files, function(f) tags$li(tagList(icon("file-code"), "  "), f))
        )
      } else {
        tags$p(style = "color:#aaa; font-size:0.84rem;", "No agent documents found.")
      }

      # 6. Triage log entries (grep agent name from triage-log.md)
      triage_path <- file.path(paths$second_brain_root, "01_control-room", "triage-log.md")
      triage_ui <- if (file.exists(triage_path)) {
        lines <- tryCatch(readLines(triage_path, warn = FALSE), error = function(...) character())
        hits  <- lines[grepl(display_name, lines, ignore.case = TRUE)]
        if (length(hits)) {
          tagList(
            tags$p(style = "font-size:0.78rem; color:#6d7c74;",
                   sprintf("%d mention(s) in triage log:", length(hits))),
            tags$ul(style = "padding-left:1.1em; font-size:0.82rem;",
              lapply(head(hits, 5L), function(h) tags$li(h))
            )
          )
        } else {
          tags$p(style = "color:#aaa; font-size:0.84rem;",
                 "No mentions in triage-log.md.")
        }
      } else {
        tags$p(style = "color:#aaa; font-style:italic; font-size:0.84rem;",
               "No triage log found at 01_control-room/triage-log.md.")
      }

      tagList(
        tags$h6(style = "color:#174c4f; margin-top:0;", tagList(icon("terminal"), "  Quick invoke")),
        invoke_ui,
        tags$hr(),
        tags$h6(style = "color:#174c4f;", tagList(icon("list-check"), "  Open tasks")),
        tasks_ui,
        tags$hr(),
        tags$h6(style = "color:#174c4f;", tagList(icon("clock-rotate-left"), "  Run history")),
        runs_ui,
        tags$hr(),
        tags$h6(style = "color:#174c4f;", tagList(icon("file-lines"), "  Latest outputs")),
        output_files_ui,
        tags$hr(),
        tags$h6(style = "color:#174c4f;", tagList(icon("file-code"), "  Agent documents")),
        context_files_ui,
        tags$hr(),
        tags$h6(style = "color:#174c4f;", tagList(icon("inbox"), "  Triage log")),
        triage_ui
      )
    })
  })
}

# ── Helper: slug → display name ─────────────────────────────────────────────

agent_display_name <- function(slug) {
  name_map <- c(
    "software-engineer"  = "Software Engineer",
    "librarian"          = "Librarian",
    "phd-architect"      = "PhD Architect",
    "writing-partner"    = "Writing Partner",
    "methods-coach"      = "Methods Coach",
    "meeting-memory"     = "Meeting Memory",
    "news-radar"         = "News Radar",
    "builder"            = "Builder",
    "dashboard-engineer" = "Dashboard Engineer",
    "presentation-maker" = "Presentation Maker",
    "monia"              = "Metis",
    "ruflo-reference"    = "Ruflo Reference",
    "learning-coach"     = "Learning Coach",
    "career-coach"       = "Career Coach",

    "news-aggregator"    = "News Aggregator",
    "ux-engineer"        = "UX Engineer",
    "epidemiologist"     = "Epidemiologist",
    "cybersecurity"      = "Cybersecurity",
    "data-guardian"       = "Data Guardian"
  )
  if (slug %in% names(name_map)) unname(name_map[slug]) else {
    paste(
      sapply(strsplit(slug, "-")[[1L]], function(w) {
        paste0(toupper(substr(w, 1L, 1L)), substr(w, 2L, nchar(w)))
      }),
      collapse = " "
    )
  }
}

# ── Quick-invoke templates per agent ─────────────────────────────────────────

agent_invoke_templates <- function(slug) {
  templates <- list(
    "epidemiologist" = list(
      list(label = "Review study design",
           cmd   = "/epidemiologist Review my study design for passive case detection analysis"),
      list(label = "Challenge SaTScan parameters",
           cmd   = "/epidemiologist Challenge my SaTScan parameter choices for cluster detection"),
      list(label = "Surveillance strategy",
           cmd   = "/epidemiologist What sampling strategy for post-elimination surveillance?"),
      list(label = "Review a draft",
           cmd   = "/epidemiologist Review methodology in 03_domains/phd/01_current-articles/article-1/")
    ),
    "writing-partner" = list(
      list(label = "Grammar and flow check",
           cmd   = "/writing-partner Check grammar and argument flow in [path to draft]"),
      list(label = "Strengthen argument",
           cmd   = "/writing-partner Strengthen the argument structure in my discussion section"),
      list(label = "Review abstract",
           cmd   = "/writing-partner Review and improve my abstract for clarity and impact")
    ),
    "software-engineer" = list(
      list(label = "Review a module",
           cmd   = "/software-engineer Review R/mod_news.R for performance and code quality"),
      list(label = "Debug an issue",
           cmd   = "/software-engineer Debug this error: [paste error message]"),
      list(label = "Review dashboard",
           cmd   = "/software-engineer Review the Metis dashboard code for issues")
    ),
    "methods-coach" = list(
      list(label = "Statistical approach",
           cmd   = "/methods-coach Is my multilevel model specification appropriate for this data?"),
      list(label = "SaTScan guidance",
           cmd   = "/methods-coach Help me choose SaTScan parameters for HAT cluster detection"),
      list(label = "Sample size",
           cmd   = "/methods-coach What sample size do I need for this surveillance study?")
    ),
    "librarian" = list(
      list(label = "Search literature",
           cmd   = "/librarian Search for HAT passive case detection papers from 2020-2025"),
      list(label = "Find methods papers",
           cmd   = "/librarian Find spatial epidemiology methods papers relevant to my PhD"),
      list(label = "Check for new papers",
           cmd   = "/librarian What new HAT papers appeared this month?")
    ),
    "phd-architect" = list(
      list(label = "Review thesis alignment",
           cmd   = "/phd-architect Do my three articles still align with the thesis spine?"),
      list(label = "Gap analysis",
           cmd   = "/phd-architect What evidence gaps remain in my thesis framework?"),
      list(label = "Article scope",
           cmd   = "/phd-architect Is Article 2 scoped correctly or too broad?")
    ),
    "news-radar" = list(
      list(label = "Daily briefing",
           cmd   = "/news-radar What happened today that I should know about?"),
      list(label = "Domain scan",
           cmd   = "/news-radar Any developments in sleeping sickness this week?"),
      list(label = "Surprise signals",
           cmd   = "/news-radar What unexpected cross-domain signals did you detect?")
    ),
    "news-aggregator" = list(
      list(label = "Run feed collection",
           cmd   = "/news-aggregator Fetch all 17 RSS feeds and report what was collected"),
      list(label = "Check feed health",
           cmd   = "/news-aggregator Which feeds are failing or returning empty results?")
    ),
    "ux-engineer" = list(
      list(label = "Audit CSS",
           cmd   = "/ux-engineer Audit www/styles.css for WCAG AA compliance"),
      list(label = "Review a module UI",
           cmd   = "/ux-engineer Review the UI in R/mod_news.R for accessibility and responsiveness"),
      list(label = "Design system check",
           cmd   = "/ux-engineer Is the current design system consistent across all tabs?")
    ),
    "meeting-memory" = list(
      list(label = "Structure meeting notes",
           cmd   = "/meeting-memory Structure my notes from today's meeting"),
      list(label = "Pre-briefing",
           cmd   = "/meeting-memory Create a pre-briefing for my meeting with [person]")
    ),
    "dashboard-engineer" = list(
      list(label = "Visualization advice",
           cmd   = "/dashboard-engineer What's the best way to visualize HAT case trends by health zone?"),
      list(label = "Layout review",
           cmd   = "/dashboard-engineer Review the layout of the Control Room tab")
    ),
    "learning-coach" = list(
      list(label = "Learning path",
           cmd   = "/learning-coach What should I learn next for my PhD methods?"),
      list(label = "Skill assessment",
           cmd   = "/learning-coach Assess my current spatial epidemiology skill level")
    ),
    "career-coach" = list(
      list(label = "CV review",
           cmd   = "/career-coach Review my CV for EU institutional positions"),
      list(label = "Career strategy",
           cmd   = "/career-coach What career options match my epidemiology + AI profile?")
    ),

    "presentation-maker" = list(
      list(label = "Create slide outline",
           cmd   = "/presentation-maker Create a slide outline for a 15-minute talk on [topic]")
    ),
    "builder" = list(
      list(label = "Build a tool",
           cmd   = "/builder Build an MCP server for [purpose]")
    ),
    "monia" = list(
      list(label = "General request (Metis routes)",
           cmd   = "/metis [describe what you need — she picks the agent]"),
      list(label = "Morning briefing",
           cmd   = "/metis What should I focus on today?"),
      list(label = "Review a paper (full chain)",
           cmd   = "/metis Review my Article 1 draft for methodology, grammar, and thesis fit"),
      list(label = "Triage inbox",
           cmd   = "/metis Triage everything in 00_inbox/"),
      list(label = "Weekly review",
           cmd   = "/metis Run my weekly review"),
      list(label = "What am I overlooking?",
           cmd   = "/metis What should I be aware of that I haven't asked about?")
    )
  )

  if (slug %in% names(templates)) templates[[slug]] else list()
}
