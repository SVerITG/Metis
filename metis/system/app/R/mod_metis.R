# mod_metis.R
# Metis tab — system overview, agents, data protection — makes the Metis agent ecosystem visible and auditable.
# Sections: My Profile | Agent Roster | Data Protection | Token Usage

# ---------------------------------------------------------------------------
# Helpers (module-private)
# ---------------------------------------------------------------------------

# Parse YAML frontmatter between the first pair of --- delimiters in a character vector.
# Returns a named list of scalar values; unknown/complex fields are left as character.
parse_skill_frontmatter <- function(lines) {
  if (!length(lines)) return(list())

  # Find --- delimiters
  dashes <- which(trimws(lines) == "---")
  if (length(dashes) < 2L) return(list())

  yaml_lines <- lines[(dashes[1L] + 1L):(dashes[2L] - 1L)]
  if (!length(yaml_lines)) return(list())

  # Simple key: value parser — no external YAML package needed
  result <- list()
  for (line in yaml_lines) {
    m <- regmatches(line, regexec("^([A-Za-z_][A-Za-z0-9_]*):\\s*(.*)", line))[[1L]]
    if (length(m) == 3L) {
      key <- trimws(m[2L])
      val <- trimws(m[3L])
      # Strip surrounding quotes if present
      val <- gsub('^["\']|["\']$', "", val)
      result[[key]] <- val
    }
  }
  result
}

# Read all agents from agents_root / 02_agents subfolder.
# Returns a data.frame with: slug, name, description, model, effort, skill_path.
read_agent_roster <- function(paths) {
  agents_dir <- file.path(paths$agents_root)
  if (!dir.exists(agents_dir)) {
    return(data.frame(
      slug = character(), name = character(), description = character(),
      model = character(), effort = character(), skill_path = character(),
      stringsAsFactors = FALSE
    ))
  }

  subdirs <- list.dirs(agents_dir, recursive = FALSE, full.names = TRUE)
  if (!length(subdirs)) {
    return(data.frame(
      slug = character(), name = character(), description = character(),
      model = character(), effort = character(), skill_path = character(),
      stringsAsFactors = FALSE
    ))
  }

  rows <- lapply(subdirs, function(d) {
    slug       <- basename(d)
    skill_path <- file.path(d, "skill.md")
    lines      <- safe_read_lines(skill_path, n = 30L)
    fm         <- if (length(lines)) parse_skill_frontmatter(lines) else list()

    data.frame(
      slug        = slug,
      name        = if (!is.null(fm$name))        fm$name        else slug,
      description = if (!is.null(fm$description)) fm$description else "",
      model       = if (!is.null(fm$model))       tolower(fm$model) else "unknown",
      effort      = if (!is.null(fm$effort))      fm$effort      else "",
      skill_path  = skill_path,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

# Colour-code model badge by model family keyword.
model_badge_style <- function(model) {
  model_lc <- tolower(model)
  if (grepl("haiku", model_lc)) {
    list(bg = "#d4edda", fg = "#155724", label = model)
  } else if (grepl("sonnet", model_lc)) {
    list(bg = "#cce5ff", fg = "#004085", label = model)
  } else if (grepl("opus", model_lc)) {
    list(bg = "#e2d9f3", fg = "#4a1d96", label = model)
  } else {
    list(bg = "#e2e3e5", fg = "#383d41", label = model)
  }
}

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

metis_tab_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(
      class = "page-intro",
      h1("Metis"),
      p("Agent ecosystem overview, user profile, data protection policy, and token usage audit.")
    ),

    # ── Section 1: My Profile ───────────────────────────────────────────────
    card(
      card_header(tagList(icon("circle-user"), "  My Profile")),
      card_body(uiOutput(ns("profile_ui")))
    ),

    # ── Section 2: Agent Roster ─────────────────────────────────────────────
    card(
      card_header(tagList(icon("robot"), "  Agent Roster")),
      card_body(uiOutput(ns("agent_roster_ui")))
    ),

    # ── Section 3: Data Protection ──────────────────────────────────────────
    card(
      card_header(tagList(icon("shield-halved"), "  Data Protection")),
      card_body(
        uiOutput(ns("red_lines_ui")),
        tags$hr(style = "margin: 1rem 0;"),
        # Data classification table
        tags$h6(style = "font-weight: 600; margin-bottom: 0.5rem;", "Data Classification Levels"),
        tags$table(
          class = "table table-sm table-bordered",
          style = "font-size: 0.84rem;",
          tags$thead(
            tags$tr(
              tags$th("Level"),
              tags$th("Description")
            )
          ),
          tags$tbody(
            tags$tr(
              tags$td(tags$span(
                style = "font-weight:700; color:#c0392b;",
                "SENSITIVE"
              )),
              tags$td("Personal health data, credentials, private keys — never processed by AI agents.")
            ),
            tags$tr(
              tags$td(tags$span(
                style = "font-weight:700; color:#b36a1d;",
                "CONFIDENTIAL"
              )),
              tags$td("Internal strategies, unpublished research, financial projections — restricted to local agents only.")
            ),
            tags$tr(
              tags$td(tags$span(
                style = "font-weight:700; color:#2d6073;",
                "INTERNAL"
              )),
              tags$td("Meeting notes, project plans, learning resources — accessible to trusted local agents.")
            ),
            tags$tr(
              tags$td(tags$span(
                style = "font-weight:700; color:#2e6b4f;",
                "PUBLIC"
              )),
              tags$td("Published papers, public news, open datasets — freely processable by any agent.")
            )
          )
        ),
        tags$hr(style = "margin: 1rem 0;"),
        # Data Guardian status
        div(
          style = paste0(
            "display:flex; align-items:center; gap:0.6rem; padding:0.6rem 0.9rem;",
            "background:#eaf4ee; border-radius:6px; border:1px solid #b2dfce;"
          ),
          div(
            style = "width:10px; height:10px; border-radius:50%; background:#2e6b4f; flex-shrink:0;"
          ),
          div(
            tags$strong(style = "color:#155724;", "Data Guardian"),
            tags$span(
              style = "color:#2e6b4f; font-size:0.86rem; margin-left:0.4rem;",
              "Active \u2014 PreToolUse hook monitoring file operations"
            )
          )
        )
      )
    ),

    # ── Section 4: How Metis knows you ─────────────────────────────────────
    card(
      card_header(
        div(
          style = "display:flex; justify-content:space-between; align-items:center;",
          span(tagList(icon("brain"), "  How Metis Knows You")),
          actionButton(ns("reset_thinking_profile"), "Reset profile",
                       class = "btn btn-sm btn-outline-danger",
                       icon = icon("rotate-left"))
        )
      ),
      card_body(uiOutput(ns("thinking_profile_ui")))
    ),

    # ── Section 5: Pending Skill Improvement Proposals ─────────────────────
    card(
      card_header(
        div(
          style = "display:flex; justify-content:space-between; align-items:center;",
          span(tagList(icon("lightbulb"), "  Pending Agent Improvement Proposals")),
          actionButton(ns("refresh_proposals"), NULL,
                       class = "btn btn-sm btn-outline-secondary",
                       icon = icon("rotate"), title = "Refresh")
        )
      ),
      card_body(uiOutput(ns("proposals_ui")))
    ),

    # ── Section 6: Token Usage ──────────────────────────────────────────────
    card(
      card_header(
        div(
          style = "display:flex; justify-content:space-between; align-items:center;",
          span(tagList(icon("chart-bar"), "  Token Usage \u2014 Last 7 Days")),
          actionButton(
            ns("refresh_tokens"),
            tagList(icon("rotate"), "  Refresh"),
            class = "btn btn-sm btn-outline-secondary"
          )
        )
      ),
      card_body(uiOutput(ns("token_usage_ui")))
    )
  )
}

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

metis_tab_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns

    # Reactive trigger for token table refresh
    token_refresh <- reactiveVal(0L)
    observeEvent(input$refresh_tokens, token_refresh(token_refresh() + 1L))

    # ── Section 1: My Profile ─────────────────────────────────────────────
    output$profile_ui <- renderUI({
      config_path <- file.path(paths$second_brain_root, "08_system", "user-config.yaml")

      if (!file.exists(config_path)) {
        return(
          div(
            class = "empty-state",
            style = "padding:1rem;",
            icon("circle-info"),
            tags$p(
              style = "margin-top:0.5rem;",
              "No user profile configured yet. Run ",
              tags$code("/metis_config"),
              " to set up."
            )
          )
        )
      }

      lines <- tryCatch(
        readLines(config_path, warn = FALSE),
        error = function(e) character()
      )

      if (!length(lines)) {
        return(
          div(
            class = "empty-state",
            style = "padding:1rem;",
            "user-config.yaml exists but appears to be empty."
          )
        )
      }

      tags$pre(
        style = paste0(
          "background:rgba(255,255,255,0.8); backdrop-filter:blur(4px);",
          "border:1px solid #e0e0e0; border-radius:8px;",
          "padding:1rem 1.2rem; font-size:0.84rem;",
          "white-space:pre-wrap; word-break:break-word; max-height:340px; overflow-y:auto;"
        ),
        paste(lines, collapse = "\n")
      )
    })

    # ── Section 2: Agent Roster ───────────────────────────────────────────
    output$agent_roster_ui <- renderUI({
      roster <- tryCatch(
        read_agent_roster(paths),
        error = function(e) {
          data.frame(
            slug = character(), name = character(), description = character(),
            model = character(), effort = character(), skill_path = character(),
            stringsAsFactors = FALSE
          )
        }
      )

      if (!nrow(roster)) {
        return(
          div(
            class = "empty-state",
            style = "padding:1rem;",
            icon("robot"),
            tags$p(
              style = "margin-top:0.5rem;",
              "No agents found in ",
              tags$code(paths$agents_root),
              ". Ensure each agent has a subfolder with a skill.md file."
            )
          )
        )
      }

      # Fetch last-run timestamps for all agents in one query
      last_runs <- tryCatch(
        db_table(paths, paste(
          "SELECT agent_slug, MAX(created_at) AS last_run",
          "FROM agent_runs",
          "GROUP BY agent_slug"
        )),
        error = function(e) data.frame(agent_slug = character(), last_run = character(), stringsAsFactors = FALSE)
      )

      # Build a lookup: slug -> last_run
      last_run_map <- if (nrow(last_runs)) {
        setNames(as.list(last_runs$last_run), last_runs$agent_slug)
      } else {
        list()
      }

      cards <- lapply(seq_len(nrow(roster)), function(i) {
        agent <- roster[i, ]

        badge_style <- model_badge_style(agent$model)
        model_badge <- tags$span(
          style = paste0(
            "display:inline-block; padding:2px 8px; border-radius:10px;",
            "font-size:0.72rem; font-weight:600;",
            "background:", badge_style$bg, "; color:", badge_style$fg, ";"
          ),
          badge_style$label
        )

        effort_badge <- if (nzchar(agent$effort)) {
          tags$span(
            style = paste0(
              "display:inline-block; padding:2px 8px; border-radius:10px;",
              "font-size:0.72rem; font-weight:500;",
              "background:#f0f0f0; color:#555; margin-left:4px;"
            ),
            agent$effort
          )
        }

        last_run_raw <- last_run_map[[agent$slug]]
        last_run_label <- if (!is.null(last_run_raw) && nzchar(last_run_raw)) {
          # Format timestamp if it looks like a datetime, otherwise show as-is
          formatted <- tryCatch(
            format(as.POSIXct(last_run_raw, tz = "UTC"), "%Y-%m-%d %H:%M"),
            error = function(e) last_run_raw
          )
          tags$span(
            style = "font-size:0.75rem; color:#6d7c74;",
            tagList(icon("clock"), "  Last run: ", formatted)
          )
        } else {
          tags$span(
            style = "font-size:0.75rem; color:#aaa; font-style:italic;",
            "Never run"
          )
        }

        div(
          style = paste0(
            "background:rgba(255,255,255,0.8); backdrop-filter:blur(4px);",
            "border:1px solid #e0e0e0; border-radius:10px;",
            "padding:0.85rem 1rem; display:flex; flex-direction:column; gap:0.4rem;",
            "box-shadow:0 1px 4px rgba(0,0,0,0.06);"
          ),
          div(
            style = "display:flex; align-items:baseline; gap:0.4rem; flex-wrap:wrap;",
            tags$strong(style = "font-size:0.95rem;", agent$name),
            model_badge,
            effort_badge
          ),
          if (nzchar(agent$description)) {
            tags$p(
              style = "font-size:0.82rem; color:#4a5a5e; margin:0; line-height:1.4;",
              agent$description
            )
          },
          last_run_label
        )
      })

      div(
        style = paste0(
          "display:grid;",
          "grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));",
          "gap:0.85rem;"
        ),
        cards
      )
    })

    # ── Section 3: Red Lines (Data Protection) ────────────────────────────
    output$red_lines_ui <- renderUI({
      red_lines_path <- file.path(paths$second_brain_root, "08_system", "red-lines.md")

      if (!file.exists(red_lines_path)) {
        return(
          div(
            class = "empty-state",
            style = "padding:0.75rem 0;",
            icon("triangle-exclamation"),
            tags$p(
              style = "margin-top:0.4rem;",
              "No red-lines.md found at ",
              tags$code(file.path("08_system", "red-lines.md")),
              ". Create this file in your second brain to document data protection rules."
            )
          )
        )
      }

      tryCatch(
        includeMarkdown(red_lines_path),
        error = function(e) {
          div(
            class = "empty-state",
            style = "padding:0.75rem 0;",
            paste("Could not render red-lines.md:", conditionMessage(e))
          )
        }
      )
    })

    # ── Section 4: How Metis knows you ────────────────────────────────────
    output$thinking_profile_ui <- renderUI({
      profile_path <- file.path(paths$second_brain_root, "08_system", "thinking-profile.yaml")

      if (!file.exists(profile_path)) {
        return(div(
          class = "empty-state",
          style = "padding:1rem;",
          icon("brain"),
          p(style = "margin-top:0.5rem;",
            "No thinking profile yet. Metis builds this as you work — capture ideas, brainstorm, and rate agent outputs.")
        ))
      }

      profile <- tryCatch(
        yaml::yaml.load_file(profile_path),
        error = function(e) NULL
      )

      if (is.null(profile)) {
        return(div(class = "empty-state", "Could not parse thinking-profile.yaml."))
      }

      rows <- list()

      # Preferred idea sources
      if (!is.null(profile$preferred_idea_sources) && length(profile$preferred_idea_sources) > 0L) {
        src_data <- do.call(rbind, lapply(names(profile$preferred_idea_sources), function(s) {
          data.frame(source = s, count = profile$preferred_idea_sources[[s]],
                     stringsAsFactors = FALSE)
        }))
        src_data <- src_data[order(-src_data$count), ]
        rows <- c(rows, list(
          tags$h6(style = "font-weight:600; margin-bottom:0.4rem;", "Preferred idea sources"),
          div(style = "display:flex; gap:0.4rem; flex-wrap:wrap; margin-bottom:1rem;",
            lapply(seq_len(min(nrow(src_data), 8L)), function(i) {
              tags$span(
                style = paste0(
                  "padding:3px 10px; border-radius:12px; font-size:0.8rem;",
                  "background:#cce5ff; color:#004085;"
                ),
                paste0(src_data$source[i], " (", src_data$count[i], ")")
              )
            })
          )
        ))
      }

      # Agent feedback rates
      if (!is.null(profile$agent_feedback) && length(profile$agent_feedback) > 0L) {
        fb <- profile$agent_feedback
        fb_names <- names(fb)
        rows <- c(rows, list(
          tags$h6(style = "font-weight:600; margin-bottom:0.4rem;", "Agent interactions"),
          tags$table(
            class = "table table-sm",
            style = "font-size:0.83rem; max-width:500px;",
            tags$thead(tags$tr(tags$th("Agent"), tags$th("Positive"), tags$th("Flagged"))),
            tags$tbody(lapply(fb_names, function(ag) {
              tags$tr(
                tags$td(ag),
                tags$td(fb[[ag]]$positive %||% 0L),
                tags$td(fb[[ag]]$flagged  %||% 0L)
              )
            }))
          )
        ))
      }

      # Connection follow-up rate
      if (!is.null(profile$connection_preferences$followed_up_rate)) {
        rate <- round(profile$connection_preferences$followed_up_rate * 100, 1)
        rows <- c(rows, list(
          tags$h6(style = "font-weight:600; margin-bottom:0.4rem;", "Brainstorm follow-up rate"),
          div(style = "margin-bottom:1rem;",
            tags$span(
              style = paste0(
                "font-size:1.4rem; font-weight:700; color:",
                if (rate > 50) "#2e6b4f" else "#b36a1d", ";"
              ),
              paste0(rate, "%")
            ),
            tags$span(
              style = "font-size:0.8rem; color:#666; margin-left:0.5rem;",
              "of brainstorm connections acted on"
            )
          )
        ))
      }

      if (length(rows) == 0L) {
        return(div(class = "empty-state",
                   p("Thinking profile is empty — start capturing ideas and brainstorming to build it.")))
      }

      tagList(rows)
    })

    observeEvent(input$reset_thinking_profile, {
      showModal(modalDialog(
        title = "Reset thinking profile?",
        "This will clear all learned preferences. Metis will start fresh. This cannot be undone.",
        footer = tagList(
          modalButton("Cancel"),
          actionButton(ns("confirm_reset_profile"), "Reset", class = "btn-danger")
        )
      ))
    })

    observeEvent(input$confirm_reset_profile, {
      profile_path <- file.path(paths$second_brain_root, "08_system", "thinking-profile.yaml")
      empty <- list(
        version = 1L,
        last_updated = format(Sys.Date(), "%Y-%m-%d"),
        connection_preferences = list(),
        preferred_idea_sources = list(),
        agent_feedback = list()
      )
      tryCatch({
        yaml::write_yaml(empty, profile_path)
        showNotification("Thinking profile reset.", type = "message")
      }, error = function(e) {
        showNotification(paste("Error:", conditionMessage(e)), type = "error")
      })
      removeModal()
    })

    # ── Section 5: Pending proposals ─────────────────────────────────────
    proposals_refresh <- reactiveVal(0L)
    observeEvent(input$refresh_proposals, proposals_refresh(proposals_refresh() + 1L))

    output$proposals_ui <- renderUI({
      proposals_refresh()

      proposals <- tryCatch(
        db_table(paths, paste(
          "SELECT id, agent_slug, proposed_at, rationale,",
          "SUBSTR(proposed_content, 1, 150) AS preview",
          "FROM skill_improvement_proposals",
          "WHERE status = 'pending'",
          "ORDER BY proposed_at DESC"
        )),
        error = function(e) NULL
      )

      if (is.null(proposals) || nrow(proposals) == 0L) {
        return(div(
          class = "empty-state",
          icon("check-circle"),
          p("No pending proposals. Agents will queue improvement suggestions here after you rate their outputs.")
        ))
      }

      tagList(lapply(seq_len(nrow(proposals)), function(i) {
        row <- proposals[i, ]
        div(
          style = paste0(
            "border:1px solid #e4e4e4; border-radius:8px; padding:0.85rem;",
            "margin-bottom:0.65rem; background:#fffdf7;"
          ),
          div(
            style = "display:flex; justify-content:space-between; align-items:flex-start;",
            div(
              tags$strong(row$agent_slug),
              tags$span(style = "font-size:0.78rem; color:#888; margin-left:0.5rem;",
                        substr(row$proposed_at, 1L, 16L)),
              if (!is.na(row$rationale) && nzchar(row$rationale))
                tags$p(style = "font-size:0.83rem; color:#444; margin:0.3rem 0 0 0;",
                       row$rationale)
            ),
            div(style = "display:flex; gap:0.4rem;",
              tags$button(
                class = "btn btn-xs btn-success",
                style = "padding:2px 10px; font-size:0.78rem;",
                onclick = sprintf(
                  "Shiny.setInputValue('%s', %d, {priority:'event'})",
                  ns("approve_proposal"), row$id
                ),
                tagList(icon("check"), " Approve")
              ),
              tags$button(
                class = "btn btn-xs btn-outline-danger",
                style = "padding:2px 10px; font-size:0.78rem;",
                onclick = sprintf(
                  "Shiny.setInputValue('%s', %d, {priority:'event'})",
                  ns("reject_proposal"), row$id
                ),
                tagList(icon("x"), " Reject")
              )
            )
          ),
          if (!is.na(row$preview) && nzchar(row$preview))
            div(
              style = paste0(
                "margin-top:0.4rem; padding:0.4rem 0.6rem;",
                "background:#f5f5f5; border-radius:4px;",
                "font-family:monospace; font-size:0.76rem; color:#555;"
              ),
              paste0(row$preview, "\u2026")
            )
        )
      }))
    })

    observeEvent(input$approve_proposal, {
      req(input$approve_proposal)
      pid <- input$approve_proposal
      proposal <- tryCatch(
        db_table(paths, sprintf(
          "SELECT * FROM skill_improvement_proposals WHERE id = %d AND status = 'pending'", pid
        )),
        error = function(e) NULL
      )
      if (is.null(proposal) || nrow(proposal) == 0L) {
        showNotification("Proposal not found or already actioned.", type = "warning")
        return()
      }
      # Write the proposed content to the skill file
      agent_slug <- proposal$agent_slug[1L]
      proposed   <- proposal$proposed_content[1L]
      # Find skill file
      skill_candidates <- c(
        file.path(paths$second_brain_root, ".claude", "skills", agent_slug, "skill.md"),
        file.path(paths$agents_root, agent_slug, "skill.md")
      )
      skill_file <- skill_candidates[file.exists(skill_candidates)][1L]
      if (is.na(skill_file)) {
        skill_file <- skill_candidates[1L]
        dir.create(dirname(skill_file), recursive = TRUE, showWarnings = FALSE)
      }
      # Backup + write
      if (file.exists(skill_file)) {
        backup <- paste0(skill_file, ".backup-", format(Sys.time(), "%Y%m%d%H%M%S"))
        file.copy(skill_file, backup)
      }
      writeLines(proposed, skill_file)
      # Mark approved
      con <- connect_db(paths)
      on.exit(DBI::dbDisconnect(con), add = TRUE)
      DBI::dbExecute(con, "UPDATE skill_improvement_proposals SET status = 'approved' WHERE id = ?",
                     params = list(pid))
      showNotification(paste0("Proposal #", pid, " approved. Skill file updated."), type = "message")
      proposals_refresh(proposals_refresh() + 1L)
    }, ignoreNULL = TRUE)

    observeEvent(input$reject_proposal, {
      req(input$reject_proposal)
      pid <- input$reject_proposal
      con <- connect_db(paths)
      on.exit(DBI::dbDisconnect(con), add = TRUE)
      DBI::dbExecute(con, "UPDATE skill_improvement_proposals SET status = 'rejected' WHERE id = ?",
                     params = list(pid))
      showNotification(paste0("Proposal #", pid, " rejected."), type = "message")
      proposals_refresh(proposals_refresh() + 1L)
    }, ignoreNULL = TRUE)

    # ── Section 6: Token Usage ────────────────────────────────────────────
    output$token_usage_ui <- renderUI({
      token_refresh()  # take dependency on refresh trigger

      usage <- tryCatch(
        db_table(paths, paste(
          "SELECT agent_slug,",
          "  COUNT(*) AS runs,",
          "  SUM(COALESCE(input_tokens, 0))  AS input_tokens,",
          "  SUM(COALESCE(output_tokens, 0)) AS output_tokens",
          "FROM agent_runs",
          "WHERE created_at >= date('now', '-7 days')",
          "GROUP BY agent_slug",
          "ORDER BY runs DESC"
        )),
        error = function(e) data.frame(
          agent_slug     = character(),
          runs           = integer(),
          input_tokens   = integer(),
          output_tokens  = integer(),
          stringsAsFactors = FALSE
        )
      )

      if (!nrow(usage)) {
        return(
          div(
            class = "empty-state",
            style = "padding:1rem;",
            icon("chart-bar"),
            tags$p(
              style = "margin-top:0.5rem;",
              "No agent runs recorded this week."
            )
          )
        )
      }

      # Add a total row
      totals <- data.frame(
        agent_slug    = "TOTAL",
        runs          = sum(usage$runs),
        input_tokens  = sum(usage$input_tokens),
        output_tokens = sum(usage$output_tokens),
        stringsAsFactors = FALSE
      )
      usage_display <- rbind(usage, totals)

      # Rename columns for display
      names(usage_display) <- c("Agent", "Runs", "Input Tokens", "Output Tokens")

      renderTable(
        usage_display,
        bordered = TRUE,
        striped  = TRUE,
        spacing  = "s"
      )
    })
  })
}
