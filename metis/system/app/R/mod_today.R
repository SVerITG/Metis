# mod_today.R
# Today tab — arrival screen: greeting strip, overnight summary, launcher row,
# today's focus, scan for changes, token footer.
# Phase 2 redesign: stripped from 10-section control room to 5-section dashboard.

# ── UI ───────────────────────────────────────────────────────────────────────

today_ui <- function(id) {
  ns <- NS(id)

  tagList(
    # 1. Greeting strip
    uiOutput(ns("greeting_strip")),

    # 2. What's new overnight
    uiOutput(ns("overnight_ui")),

    # 3. Launcher row — 6 cards
    div(class = "launcher-row",
      launcher_card_btn(ns, "capture",   "lightbulb",     "Capture an idea",        "Press Ctrl+K or click here",            "Dashboard"),
      launcher_card_btn(ns, "brainstorm","comments",       "Brainstorm out loud",    "Free-flowing thinking with Metis",      "Claude Chat"),
      launcher_card_btn(ns, "document",  "file-lines",     "Work on a document",     "Draft, edit, review Word files",        "Claude Cowork"),
      launcher_card_btn(ns, "code",      "terminal",       "Review code or build",   "R scripts, Shiny, debugging",           "Claude Code"),
      launcher_card_btn(ns, "meeting",   "calendar-check", "Prep for a meeting",     "Brief, agenda, context",                "Dashboard"),
      launcher_card_btn(ns, "inbox",     "inbox",          "Process the inbox",      "Run Librarian over new PDFs",           "Dashboard")
    ),

    # 4. Today's focus (conditional — highest-priority active project)
    uiOutput(ns("focus_ui")),

    # 5. Scan for changes
    card(
      card_header(
        div(style = "display:flex; justify-content:space-between; align-items:center;",
          span(tagList(icon("magnifying-glass"), "  Scan for changes")),
          actionButton(ns("run_scan"), tagList(icon("rotate"), " Scan now"),
                       class = "btn btn-sm btn-outline-secondary")
        )
      ),
      card_body(uiOutput(ns("scan_results_ui")))
    ),

    # 6. Token footer
    uiOutput(ns("token_footer"))
  )
}

# ── Launcher card button helper ──────────────────────────────────────────────

launcher_card_btn <- function(ns, card_id, icon_name, title, subtitle, client_label) {
  client_cls <- paste0("launcher-client-", tolower(gsub("[^a-z]", "", client_label)))
  tags$button(
    class = "launcher-card",
    onclick = sprintf(
      "Shiny.setInputValue('%s', '%s', {priority:'event'})",
      ns("launcher_click"), card_id
    ),
    div(class = "launcher-icon", icon(icon_name)),
    div(class = "launcher-content",
      div(class = "launcher-title",    title),
      div(class = "launcher-subtitle", subtitle),
      div(class = paste("launcher-client", client_cls), client_label)
    )
  )
}

# ── Server ──────────────────────────────────────────────────────────────────

today_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # ── 1. Greeting strip ─────────────────────────────────────────────────
    output$greeting_strip <- renderUI({
      greeting  <- morning_greeting()
      today_lbl <- format(Sys.Date(), "%A, %d %B %Y")

      open_n <- tryCatch(
        db_scalar(paths, "SELECT COUNT(*) FROM tasks WHERE status != 'done'"),
        error = function(...) 0L
      )
      inbox_n  <- inbox_item_count(paths)
      overdue_n <- tryCatch({
        r <- db_table(paths, sprintf(
          "SELECT COUNT(*) AS n FROM tasks WHERE status != 'done' AND due_date != '' AND due_date <= '%s'",
          format(Sys.Date())
        ))
        if (nrow(r)) r$n[1L] else 0L
      }, error = function(...) 0L)

      morning_runs <- tryCatch(
        db_table(paths, sprintf(
          "SELECT agent_slug FROM agent_runs WHERE agent_slug IN ('news-radar','librarian') AND DATE(started_at) = '%s'",
          format(Sys.Date())
        )),
        error = function(...) data.frame(agent_slug = character())
      )

      overdue_chip <- div(
        class = if (overdue_n > 0L) "morning-chip morning-chip-alert" else "morning-chip morning-chip-ok",
        if (overdue_n > 0L) tagList(icon("triangle-exclamation"), sprintf(" %d overdue", overdue_n))
        else tagList(icon("check"), " No overdue tasks")
      )
      inbox_chip <- div(
        class = if (inbox_n > 0L) "morning-chip morning-chip-warn" else "morning-chip morning-chip-ok",
        tagList(icon("inbox"), sprintf(" %d in inbox", inbox_n))
      )
      tasks_chip <- div(class = "morning-chip morning-chip-ok",
                        tagList(icon("list-check"), sprintf(" %d open", open_n)))

      ran <- unique(morning_runs$agent_slug)
      agents_chip <- if (length(ran)) {
        parts <- c(
          if ("news-radar" %in% ran) "News Radar \u2713",
          if ("librarian"  %in% ran) "Librarian \u2713"
        )
        div(class = "morning-chip morning-chip-ok",
            tagList(icon("robot"), " ", paste(parts, collapse = " \u00b7 ")))
      }

      div(class = "today-greeting-strip",
        div(class = "today-greeting", greeting),
        div(class = "today-date",     today_lbl),
        div(class = "morning-chips",
          overdue_chip, inbox_chip, tasks_chip,
          if (!is.null(agents_chip)) agents_chip
        )
      )
    })

    # ── 2. What's new overnight ───────────────────────────────────────────
    output$overnight_ui <- renderUI({
      news_n <- tryCatch(
        db_scalar(paths, "SELECT COUNT(*) FROM news_briefs WHERE brief_date >= date('now', '-1 day')"),
        error = function(...) 0L
      )
      papers_n <- tryCatch(
        db_scalar(paths, "SELECT COUNT(*) FROM library_inventory WHERE created_at >= datetime('now', '-1 day')"),
        error = function(...) 0L
      )
      ideas_n <- tryCatch(
        db_scalar(paths, "SELECT COUNT(*) FROM ideas WHERE created_at >= datetime('now', '-1 day')"),
        error = function(...) 0L
      )
      meetings_n <- tryCatch(
        db_scalar(paths, "SELECT COUNT(*) FROM meetings WHERE created_at >= datetime('now', '-1 day')"),
        error = function(...) 0L
      )

      items <- list(
        list(icon = "newspaper",  count = news_n,     label = "news items", tab = "Knowledge"),
        list(icon = "book-open",  count = papers_n,   label = "new papers", tab = "Knowledge"),
        list(icon = "lightbulb",  count = ideas_n,    label = "new ideas",  tab = "Thinking"),
        list(icon = "microphone", count = meetings_n, label = "meetings",   tab = "Meetings")
      )
      active <- Filter(function(x) x$count > 0L, items)

      if (!length(active)) {
        return(div(class = "overnight-card overnight-quiet",
          tagList(icon("moon"), "  Nothing new overnight. A clean slate.")))
      }

      div(class = "overnight-card",
        div(class = "overnight-label", tagList(icon("star"), "  What's new overnight")),
        div(class = "overnight-items",
          lapply(active, function(x) {
            div(class = "overnight-item",
              div(class = "overnight-count", as.character(x$count)),
              div(class = "overnight-desc",
                div(class = "overnight-item-label", x$label),
                div(class = "overnight-item-tab",   paste0("in ", x$tab))
              )
            )
          })
        )
      )
    })

    # ── 3. Launcher clicks ────────────────────────────────────────────────
    observeEvent(input$launcher_click, {
      req(input$launcher_click)
      card_id <- input$launcher_click

      modal_def <- switch(card_id,
        capture = list(
          title = tagList(icon("lightbulb"), " Capture an idea"),
          body  = tagList(
            tags$p("Type your idea — Metis will save it and cross-pollinate it."),
            textAreaInput(ns("quick_idea_text"), NULL,
                          placeholder = "What's on your mind?", rows = 3L),
            tags$p(style = "font-size:0.8rem; color:var(--bs-secondary);",
                   tagList(icon("keyboard"), " Shortcut: Ctrl+K from any tab (coming in Phase 3)"))
          ),
          footer = tagList(
            modalButton("Cancel"),
            actionButton(ns("save_quick_idea"), "Save idea", class = "btn-primary")
          )
        ),
        brainstorm = list(
          title  = tagList(icon("comments"), " Brainstorm out loud"),
          body   = brainstorm_prompt_ui(ns,
            paste0(
              "/metis Brainstorm \u2014 ", format(Sys.Date(), "%d %B %Y"), "\n\n",
              "I want to think out loud about: [topic]\n\n",
              "Context sources: [library / meetings / recent ideas / all]\n",
              "Start with one clarifying question, then help me explore."
            )
          ),
          footer = modalButton("Close")
        ),
        document = list(
          title  = tagList(icon("file-lines"), " Work on a document"),
          body   = cowork_prompt_ui(ns,
            paste0(
              "/writing-partner Review the document I'm about to share.\n\n",
              "Focus on: [prose quality / structure / argument / citations]\n",
              "Context: [brief description]"
            )
          ),
          footer = modalButton("Close")
        ),
        code = list(
          title  = tagList(icon("terminal"), " Review code or build"),
          body   = code_prompt_ui(ns,
            paste0(
              "/software-engineer Review the code I'm about to share.\n\n",
              "# Or, to extend Metis itself:\n",
              "/rc-builder [describe what you want to add or fix]"
            )
          ),
          footer = modalButton("Close")
        ),
        meeting = list(
          title  = tagList(icon("calendar-check"), " Prep for a meeting"),
          body   = tagList(
            tags$p("Go to the ", tags$strong("Meetings"), " tab to record, import, or prep."),
            tags$p(style = "font-size:0.8rem; color:var(--bs-secondary);",
                   "Meetings has three modes: Quick record, Auto-analyze, and Prep briefing.")
          ),
          footer = tagList(
            modalButton("Cancel"),
            tags$button(
              class   = "btn btn-primary",
              onclick = sprintf(
                "Shiny.setInputValue('%s', 'meetings', {priority:'event'})",
                ns("nav_to")
              ),
              "Go to Meetings"
            )
          )
        ),
        inbox = list(
          title  = tagList(icon("inbox"), " Process the inbox"),
          body   = inbox_prompt_ui(ns,
            "/librarian Process inbox \u2014 scan 00_inbox/ for new PDFs, extract metadata, assign tags, create knowledge links."
          ),
          footer = modalButton("Close")
        ),
        NULL  # default — unknown card_id
      )

      if (!is.null(modal_def)) {
        showModal(modalDialog(
          title     = modal_def$title,
          modal_def$body,
          footer    = modal_def$footer,
          easyClose = TRUE
        ))
      }
    }, ignoreNULL = TRUE)

    # Navigate to another tab from a launcher modal
    observeEvent(input$nav_to, {
      req(input$nav_to)
      tab <- switch(input$nav_to,
        meetings = "Meetings",
        today    = "Today",
        input$nav_to
      )
      removeModal()
      nav_select("main_nav", tab)
    }, ignoreNULL = TRUE)

    # Save quick idea (from launcher modal — delegates to insert_idea helper)
    observeEvent(input$save_quick_idea, {
      txt <- trimws(input$quick_idea_text)
      req(nzchar(txt))
      tryCatch({
        insert_idea(paths, text = txt, project_id = "", idea_type = "idea",
                    tags = auto_tags(txt))
        removeModal()
        showNotification("Idea saved.", type = "message", duration = 3L)
      }, error = function(e) {
        showNotification(paste("Save failed:", conditionMessage(e)), type = "error")
      })
    })

    # ── 4. Today's focus ─────────────────────────────────────────────────
    output$focus_ui <- renderUI({
      project <- tryCatch(
        db_table(paths, paste(
          "SELECT title, domain, priority, next_step FROM projects",
          "WHERE status = 'active' ORDER BY priority DESC, created_at DESC LIMIT 1"
        )),
        error = function(...) data.frame()
      )
      if (!nrow(project)) return(NULL)

      p <- project[1L, ]
      priority_col <- switch(p$priority, high = "#c0392b", medium = "#e67e22", "#27ae60")

      card(
        card_header(tagList(icon("crosshairs"), "  Today's focus")),
        card_body(
          div(class = "focus-card",
            style = paste0("border-left: 4px solid ", priority_col, ";"),
            div(class = "focus-project-title", p$title),
            div(class = "focus-project-meta",
              tags$span(
                class = paste0("domain-badge domain-", gsub("[^a-z0-9]", "-", tolower(p$domain))),
                p$domain
              ),
              tags$span(class = paste0("priority-", p$priority), p$priority)
            ),
            if (!is.na(p$next_step) && nzchar(p$next_step))
              div(class = "focus-next-step",
                tags$span(class = "focus-next-label", "Next: "),
                p$next_step
              )
          )
        )
      )
    })

    # ── 5. Scan for changes ──────────────────────────────────────────────
    scan_results <- reactiveVal(NULL)

    observeEvent(input$run_scan, {
      showNotification("Scanning\u2026", id = "scan_notif", duration = NULL, type = "message")

      git_st <- tryCatch(git_all_projects_status(paths), error = function(...) NULL)

      tracked <- tryCatch(
        db_table(paths, "SELECT label, stored_path FROM tracked_files WHERE watch = 1"),
        error = function(...) data.frame(label = character(), stored_path = character())
      )
      changed_files <- Filter(Negate(is.null), lapply(seq_len(nrow(tracked)), function(i) {
        fp <- tracked$stored_path[i]
        if (!file.exists(fp)) return(NULL)
        mt <- file.mtime(fp)
        if (as.Date(mt) >= Sys.Date())
          list(label = tracked$label[i], mtime = format(mt, "%H:%M"))
        else NULL
      }))

      planning_hits <- tryCatch({
        projs <- db_table(paths,
          "SELECT title, external_path FROM projects WHERE status = 'active' AND external_path != ''")
        Filter(Negate(is.null), lapply(seq_len(nrow(projs)), function(i) {
          pm <- file.path(projs$external_path[i], "PLANNING.md")
          if (!file.exists(pm)) return(NULL)
          mt <- file.mtime(pm)
          if (as.Date(mt) >= Sys.Date())
            list(project = projs$title[i], mtime = format(mt, "%H:%M"))
          else NULL
        }))
      }, error = function(...) list())

      git_dirty <- if (!is.null(git_st) && nrow(git_st)) {
        git_st[(!is.na(git_st$uncommitted) & git_st$uncommitted > 0L) |
               (!is.na(git_st$unpushed)    & git_st$unpushed    > 0L), , drop = FALSE]
      } else data.frame()

      scan_results(list(
        git_dirty    = git_dirty,
        files        = changed_files,
        planning     = planning_hits,
        scanned_at   = format(Sys.time(), "%H:%M:%S")
      ))
      removeNotification("scan_notif")
    })

    output$scan_results_ui <- renderUI({
      r <- scan_results()
      if (is.null(r)) {
        return(div(class = "empty-state",
          tagList(icon("magnifying-glass"), " Click 'Scan now' to check for changes.")))
      }

      has_changes <- (nrow(r$git_dirty) > 0L) || length(r$files) || length(r$planning)

      parts <- tagList()

      if (nrow(r$git_dirty) > 0L) {
        parts <- tagList(parts,
          div(class = "scan-section",
            div(class = "scan-section-header", tagList(icon("code-branch"), " Git — uncommitted or unpushed")),
            lapply(seq_len(nrow(r$git_dirty)), function(i) {
              row <- r$git_dirty[i, ]
              div(class = "scan-item",
                tags$strong(row$project),
                tags$span(class = "scan-item-detail", row$advice)
              )
            })
          )
        )
      }

      if (length(r$files)) {
        parts <- tagList(parts,
          div(class = "scan-section",
            div(class = "scan-section-header", tagList(icon("file"), " Tracked files changed today")),
            lapply(r$files, function(f) {
              div(class = "scan-item",
                tags$strong(f$label),
                tags$span(class = "scan-item-detail", paste0("modified at ", f$mtime))
              )
            })
          )
        )
      }

      if (length(r$planning)) {
        parts <- tagList(parts,
          div(class = "scan-section",
            div(class = "scan-section-header", tagList(icon("clipboard-list"), " PLANNING.md updated today")),
            lapply(r$planning, function(p) {
              div(class = "scan-item",
                tags$strong(p$project),
                tags$span(class = "scan-item-detail", paste0("at ", p$mtime))
              )
            })
          )
        )
      }

      if (!has_changes) {
        parts <- div(class = "scan-all-clear",
          tagList(icon("circle-check"), " All clear \u2014 no changes detected."))
      }

      tagList(
        parts,
        div(class = "scan-timestamp",
            paste0("Scanned at ", r$scanned_at))
      )
    })

    # ── 6. Token footer ──────────────────────────────────────────────────
    output$token_footer <- renderUI({
      yesterday <- format(Sys.Date() - 1L, "%Y-%m-%d")
      usage <- tryCatch(
        db_table(paths, sprintf(
          paste(
            "SELECT COUNT(*) AS runs,",
            "SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS total_tokens",
            "FROM agent_runs WHERE DATE(started_at) = '%s'"
          ),
          yesterday
        )),
        error = function(...) data.frame(runs = 0L, total_tokens = 0L)
      )
      runs_n   <- if (nrow(usage) && !is.na(usage$runs[1L]))         as.integer(usage$runs[1L])         else 0L
      tokens_n <- if (nrow(usage) && !is.na(usage$total_tokens[1L])) as.integer(usage$total_tokens[1L]) else 0L

      if (runs_n == 0L) return(NULL)

      cost_est <- round(tokens_n / 1e6 * 3, 3)   # rough €/M estimate at Sonnet pricing

      div(class = "token-footer",
        tagList(
          icon("chart-bar"),
          sprintf(
            "  Yesterday: %s tokens across %d agent run%s (est. \u20ac%.3f)",
            format(tokens_n, big.mark = ","),
            runs_n,
            if (runs_n == 1L) "" else "s",
            cost_est
          )
        )
      )
    })
  })
}

# ── Modal body helpers ───────────────────────────────────────────────────────

copy_prompt_block <- function(ns, prompt_text, btn_id) {
  fn_name <- paste0("copyMetisPrompt_", btn_id)
  tagList(
    tags$pre(class = "launch-prompt-block", prompt_text),
    tags$script(sprintf(
      "function %s() {
        navigator.clipboard.writeText(%s).then(function() {
          var b = document.getElementById('%s');
          b.innerText = 'Copied!';
          setTimeout(function() { b.innerText = 'Copy prompt'; }, 2000);
        });
      }",
      fn_name,
      jsonlite::toJSON(prompt_text, auto_unbox = TRUE),
      ns(btn_id)
    )),
    tags$button(
      id      = ns(btn_id),
      class   = "btn btn-sm btn-primary",
      onclick = paste0(fn_name, "()"),
      tagList(icon("copy"), " Copy prompt")
    )
  )
}

brainstorm_prompt_ui <- function(ns, prompt) {
  tagList(
    tags$p("Copy into ", tags$strong("Claude Chat"), " (with MCP connected):"),
    copy_prompt_block(ns, prompt, "copy_brainstorm"),
    tags$p(class = "launcher-modal-hint",
           tagList(icon("circle-info"),
                   " Chat is for thinking \u2014 free-flowing, exploratory, question-driven."))
  )
}

cowork_prompt_ui <- function(ns, prompt) {
  tagList(
    tags$p("Copy into ", tags$strong("Claude Cowork"), ":"),
    copy_prompt_block(ns, prompt, "copy_cowork"),
    tags$p(class = "launcher-modal-hint",
           tagList(icon("circle-info"),
                   " Cowork is for writing \u2014 drafting, editing papers, reviewing Word documents."))
  )
}

code_prompt_ui <- function(ns, prompt) {
  tagList(
    tags$p("Copy into ", tags$strong("Claude Code"), " in your terminal:"),
    copy_prompt_block(ns, prompt, "copy_code"),
    tags$p(class = "launcher-modal-hint",
           tagList(icon("circle-info"),
                   " Claude Code is for the technical side \u2014 R scripts, debugging, building tools."))
  )
}

inbox_prompt_ui <- function(ns, prompt) {
  tagList(
    tags$p("Copy into ", tags$strong("Claude Code"), ":"),
    copy_prompt_block(ns, prompt, "copy_inbox"),
    tags$p(class = "launcher-modal-hint",
           tagList(icon("circle-info"),
                   " Librarian scans ", tags$code("00_inbox/"), ", extracts metadata, and links to existing knowledge."))
  )
}
