# mod_learning.R
# Learning hub with a course-led top section, competencies, activity log, and resources.

learning_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(class = "learning-shell",
      div(class = "learning-hero",
        div(class = "page-intro learning-hero-copy",
          h1("Learning"),
          p("Build methodological depth through structured courses, competency tracking, and spaced review.")
        ),
        div(class = "learning-hero-stats",
          uiOutput(ns("learning_summary_ui"))
        )
      ),

      card(
        class = "learning-section-card learning-courses-section",
        card_header(
          div(class = "learning-section-header",
            div(
              tags$span(class = "learning-section-kicker", "Top Section"),
              tags$h2("Course Browser")
            ),
            tags$p("Structured courses lead the Learning Hub. Open a course to see lesson progress and spaced-review actions.")
          )
        ),
        card_body(uiOutput(ns("course_browser_ui")))
      ),

      card(
        class = "learning-section-card",
        card_header(
          div(class = "learning-section-header",
            div(
              tags$span(class = "learning-section-kicker", "Middle Section"),
              tags$h2("Competency Dashboard")
            ),
            tags$p("Track the skill domains that your courses and daily work are strengthening.")
          )
        ),
        card_body(uiOutput(ns("competency_grid")))
      ),

      uiOutput(ns("learning_sr_section")),

      div(class = "learning-bottom-stack",
        layout_columns(
          col_widths = c(5, 7),
          card(
            class = "learning-section-card",
            card_header(
              div(class = "learning-section-header",
                div(
                  tags$span(class = "learning-section-kicker", "Bottom Section"),
                  tags$h2("Activity Logger")
                ),
                tags$p("Record study sessions, paper reading, practice, and course work against competencies.")
              )
            ),
            card_body(
              uiOutput(ns("competency_select_ui")),
              selectInput(ns("activity_type"), "Activity type",
                choices = c("course_lesson", "paper_read", "exercise",
                  "sr_review", "tutorial", "practice")
              ),
              textInput(ns("activity_desc"), "What did you learn?"),
              div(class = "action-row",
                actionButton(ns("log_activity"), tagList(icon("plus"), " Log activity"),
                  class = "btn-primary"
                )
              ),
              textOutput(ns("log_status"))
            )
          ),
          card(
            class = "learning-section-card",
            card_header(
              div(class = "learning-section-header",
                div(tags$h2("Recent Activity")),
                tags$p("Latest logged learning events across competencies.")
              )
            ),
            card_body(class = "card-scroll", uiOutput(ns("recent_activities_ui")))
          )
        ),
        card(
          class = "learning-section-card",
          card_header(
            div(class = "learning-section-header",
              div(tags$h2("Resources")),
              tags$p("Open references, textbooks, and guides organized by competency domain.")
            )
          ),
          card_body(uiOutput(ns("resources_ui")))
        )
      ),

      # ── Skill gap analysis ─────────────────────────────────────────
      card(
        class = "learning-section-card",
        card_header(
          div(class = "learning-section-header",
            div(tags$h2("Skill Gap Analysis")),
            tags$p("Analyse your recent work and find gaps in your learning path.")
          )
        ),
        card_body(
          div(class = "action-row",
            actionButton(ns("analyse_skill_gaps"), tagList(icon("magnifying-glass-chart"),
                           " Analyse my work — find skill gaps"),
                         class = "btn-primary")
          ),
          uiOutput(ns("skill_gap_result"))
        )
      )
    )
  )
}

learning_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    ns <- session$ns
    refresh_trigger <- reactiveVal(0L)
    sr_refresh <- reactiveVal(0L)
    log_status_text <- reactiveVal("")
    selected_course <- reactiveVal(NULL)

    seed_default_competencies(paths)

    course_meta <- list(
      "course-epi-foundations" = list(
        competency = "Epidemiological methods",
        accent = "#174c4f",
        summary = "Study design, disease measures, bias, causation, and outbreak foundations."
      ),
      "course-biostatistics" = list(
        competency = "Biostatistics",
        accent = "#2d6073",
        summary = "Inference, regression, survival analysis, count models, and multilevel basics."
      ),
      "course-spatial-epi" = list(
        competency = "Spatial epidemiology",
        accent = "#2e6b4f",
        summary = "GIS, disease mapping, SaTScan, spatial dependence, and workflow design."
      ),
      "course-surveillance-design" = list(
        competency = "Surveillance systems",
        accent = "#b36a1d",
        summary = "System design, PHI, data flow, evaluation, and post-elimination surveillance."
      ),
      "course-outbreak-investigation" = list(
        competency = "Outbreak investigation",
        accent = "#8b3f2f",
        summary = "Detection, line listing, field analytics, control measures, and after-action learning."
      ),
      "course-health-economics" = list(
        competency = "Health economics",
        accent = "#5d5a24",
        summary = "Costs, consequences, affordability, uncertainty, and applied priority setting."
      ),
      "course-research-ethics" = list(
        competency = "Research ethics",
        accent = "#6b4a63",
        summary = "Consent, data governance, justice, partnerships, emergencies, and publication integrity."
      ),
      "course-r-for-epidemiologists" = list(
        competency = "Data workflow",
        accent = "#3b5f7a",
        summary = "Importing, cleaning, visualizing, modeling, and reporting epidemiologic data reproducibly in R."
      ),
      "course-ntd-elimination" = list(
        competency = "NTD elimination",
        accent = "#6a5b21",
        summary = "Elimination targets, endgame surveillance, verification, last-mile equity, and post-elimination vigilance."
      ),
      "course-research-writing" = list(
        competency = "Scientific communication",
        accent = "#7a4d3b",
        summary = "Research questions, protocols, reporting guidelines, and IMRaD writing."
      ),
      "multilevel-analysis" = list(
        competency = "Biostatistics",
        accent = "#6d7c74",
        summary = "External multilevel modeling course already linked into the Learning Hub."
      )
    )

    read_course_lessons <- function(course_path) {
      if (!requireNamespace("jsonlite", quietly = TRUE)) {
        return(NULL)
      }
      lessons_path <- file.path(course_path, "lessons.json")
      if (!file.exists(lessons_path)) {
        return(NULL)
      }

      raw <- tryCatch(
        jsonlite::fromJSON(lessons_path, simplifyDataFrame = FALSE),
        error = function(...) NULL
      )
      if (is.null(raw)) {
        return(NULL)
      }
      if (is.list(raw) && !is.null(raw$lessons)) {
        raw$lessons
      } else {
        raw
      }
    }

    course_progress_snapshot <- function(cp) {
      lessons <- read_course_lessons(cp$external_path)
      progress <- tryCatch(get_course_progress(paths, cp$project_id), error = function(...) data.frame())
      completed_ids <- if (nrow(progress)) unique(progress$lesson_id) else character()
      n_total <- if (is.null(lessons)) 0L else length(lessons)
      n_done <- length(completed_ids)
      pct <- if (n_total > 0L) round(100 * n_done / n_total) else 0L
      meta <- course_meta[[cp$project_id]]
      if (is.null(meta)) {
        meta <- list(
          competency = "Learning pathway",
          accent = "#174c4f",
          summary = "Structured course available in the Learning Hub."
        )
      }

      list(
        lessons = lessons,
        completed_ids = completed_ids,
        n_total = n_total,
        n_done = n_done,
        pct = pct,
        meta = meta
      )
    }

    course_projects <- reactive({
      refresh_trigger()
      tryCatch(
        db_table(paths, paste(
          "SELECT project_id, title, COALESCE(external_path,'') AS external_path",
          "FROM projects WHERE domain = 'education' AND status = 'active'",
          "ORDER BY title"
        )),
        error = function(...) data.frame()
      )
    })

    output$learning_summary_ui <- renderUI({
      projects <- course_projects()
      if (!nrow(projects)) {
        return(div(class = "learning-summary-grid",
          div(class = "learning-summary-card",
            div(class = "learning-summary-value", "0"),
            div(class = "learning-summary-label", "Courses")
          )
        ))
      }

      snapshots <- lapply(seq_len(nrow(projects)), function(i) course_progress_snapshot(projects[i, ]))
      total_lessons <- sum(vapply(snapshots, function(x) x$n_total, integer(1)))
      completed_lessons <- sum(vapply(snapshots, function(x) x$n_done, integer(1)))
      avg_progress <- if (total_lessons > 0L) round(100 * completed_lessons / total_lessons) else 0L

      div(class = "learning-summary-grid",
        div(class = "learning-summary-card",
          div(class = "learning-summary-value", nrow(projects)),
          div(class = "learning-summary-label", "Active courses")
        ),
        div(class = "learning-summary-card",
          div(class = "learning-summary-value", total_lessons),
          div(class = "learning-summary-label", "Lessons available")
        ),
        div(class = "learning-summary-card",
          div(class = "learning-summary-value", completed_lessons),
          div(class = "learning-summary-label", "Lessons completed")
        ),
        div(class = "learning-summary-card",
          div(class = "learning-summary-value", paste0(avg_progress, "%")),
          div(class = "learning-summary-label", "Overall progress")
        )
      )
    })

    render_course_card <- function(cp) {
      snapshot <- course_progress_snapshot(cp)
      selected <- identical(selected_course(), cp$project_id)

      div(
        class = paste("learning-course-card", if (selected) "learning-course-card-active" else ""),
        style = sprintf("--course-accent:%s;", snapshot$meta$accent),
        div(class = "learning-course-card-top",
          div(class = "learning-course-icon", icon("graduation-cap")),
          tags$span(class = "learning-course-competency", snapshot$meta$competency)
        ),
        div(class = "learning-course-title", cp$title),
        tags$p(class = "learning-course-summary", snapshot$meta$summary),
        div(class = "learning-course-metrics",
          div(class = "learning-course-metric",
            tags$span(class = "learning-course-metric-value", paste0(snapshot$pct, "%")),
            tags$span(class = "learning-course-metric-label", "progress")
          ),
          div(class = "learning-course-metric",
            tags$span(class = "learning-course-metric-value", snapshot$n_total),
            tags$span(class = "learning-course-metric-label", "lessons")
          ),
          div(class = "learning-course-metric",
            tags$span(class = "learning-course-metric-value", snapshot$n_done),
            tags$span(class = "learning-course-metric-label", "done")
          )
        ),
        div(class = "learning-course-progress",
          div(class = "learning-course-progress-fill",
            style = sprintf("width:%d%%;", snapshot$pct)
          )
        ),
        div(class = "learning-course-footer",
          tags$span(class = "learning-course-footer-note",
            sprintf("%d of %d lessons complete", snapshot$n_done, snapshot$n_total)
          ),
          tags$button(
            class = "btn btn-sm btn-outline-secondary",
            onclick = sprintf("Shiny.setInputValue('%s','%s',{priority:'event'})", ns("open_course"), cp$project_id),
            if (selected) "Viewing" else "Open course"
          )
        )
      )
    }

    render_course_detail <- function(cp) {
      snapshot <- course_progress_snapshot(cp)
      lessons <- snapshot$lessons
      completed_ids <- snapshot$completed_ids

      if (is.null(lessons)) {
        return(div(class = "empty-state", "Could not load lessons.json for this course."))
      }

      lesson_rows <- lapply(seq_along(lessons), function(i) {
        lesson <- lessons[[i]]
        lid <- as.character(lesson$id %||% paste0("lesson-", i))
        title <- as.character(lesson$title %||% paste("Lesson", i))
        desc <- as.character(lesson$description %||% "")
        done <- lid %in% completed_ids

        div(class = paste("course-lesson-row", if (done) "lesson-done" else ""),
          div(class = "course-lesson-title",
            if (done) icon("check-circle") else tagList(icon("circle"), "  "),
            div(
              tags$strong(title),
              if (nzchar(desc)) {
                tags$div(style = "font-size:0.8rem; color:#6d7c74;", desc)
              }
            )
          ),
          if (!done) {
            div(class = "course-lesson-actions",
              tags$button(
                class = "btn btn-xs btn-outline-success",
                onclick = sprintf(
                  "Shiny.setInputValue('%s',{course_id:'%s',lesson_id:'%s'},{priority:'event'})",
                  ns("lesson_complete"), cp$project_id, lid
                ),
                "Mark complete"
              ),
              tags$button(
                class = "btn btn-xs btn-outline-secondary",
                onclick = sprintf(
                  "Shiny.setInputValue('%s',{course_id:'%s',lesson_id:'%s'},{priority:'event'})",
                  ns("lesson_sr"), cp$project_id, lid
                ),
                tagList(icon("brain"), "  Add to SR")
              )
            )
          }
        )
      })

      div(class = "learning-course-detail",
        style = sprintf("--course-accent:%s;", snapshot$meta$accent),
        div(class = "learning-course-detail-header",
          div(
            div(class = "learning-course-detail-kicker", snapshot$meta$competency),
            div(class = "learning-course-detail-title", cp$title),
            tags$p(class = "learning-course-detail-summary", snapshot$meta$summary)
          ),
          actionButton(ns("close_course"), tagList(icon("arrow-left"), " Back to courses"),
            class = "btn btn-outline-secondary btn-sm"
          )
        ),
        div(class = "learning-course-detail-progress",
          div(class = "learning-course-detail-progress-meta",
            sprintf("%d / %d lessons complete", snapshot$n_done, snapshot$n_total)
          ),
          div(class = "learning-course-progress",
            div(class = "learning-course-progress-fill",
              style = sprintf("width:%d%%;", snapshot$pct)
            )
          ),
          div(class = "learning-course-detail-progress-note",
            sprintf("%d%% complete", snapshot$pct)
          )
        ),
        div(class = "course-lesson-list", lesson_rows)
      )
    }

    observeEvent(input$open_course, {
      selected_course(input$open_course)
    }, ignoreNULL = TRUE)

    observeEvent(input$close_course, {
      selected_course(NULL)
    })

    observeEvent(input$lesson_complete, {
      act <- input$lesson_complete
      req(is.list(act), !is.null(act$course_id), !is.null(act$lesson_id))
      mark_lesson_complete(paths, act$course_id, act$lesson_id)
      refresh_trigger(refresh_trigger() + 1L)
    }, ignoreNULL = TRUE)

    observeEvent(input$lesson_sr, {
      act <- input$lesson_sr
      req(is.list(act), !is.null(act$course_id), !is.null(act$lesson_id))
      front <- act$lesson_id
      back <- paste0("Course: ", act$course_id, "\nLesson: ", act$lesson_id)
      insert_sr_item(paths, "course_progress", paste0(act$course_id, "::", act$lesson_id), front, back)
      showNotification("Added to spaced repetition deck.", type = "message", duration = 2L)
    }, ignoreNULL = TRUE)

    output$course_browser_ui <- renderUI({
      projects <- course_projects()
      if (!nrow(projects)) {
        return(div(class = "empty-state", "No courses registered yet."))
      }

      sel <- selected_course()

      tagList(
        if (!is.null(sel) && sel %in% projects$project_id) {
          cp <- projects[projects$project_id == sel, , drop = FALSE][1L, ]
          render_course_detail(cp)
        },
        div(class = "learning-course-browser-grid",
          lapply(seq_len(nrow(projects)), function(i) render_course_card(projects[i, ]))
        )
      )
    })

    output$competency_grid <- renderUI({
      refresh_trigger()
      comps <- get_competencies(paths)
      if (!nrow(comps)) {
        return(div(class = "empty-state", "No competencies defined yet."))
      }

      level_col <- function(l) switch(l,
        beginner = "#c0392b",
        intermediate = "#b36a1d",
        advanced = "#2e6b4f",
        "#6d7c74"
      )
      level_pct <- function(l) switch(l, beginner = 15L, intermediate = 55L, advanced = 90L, 5L)
      course_map <- c(
        "comp-epi-methods" = "Epidemiology Foundations",
        "comp-biostatistics" = "Biostatistics for Epidemiologists",
        "comp-spatial-epi" = "Spatial Epidemiology",
        "comp-surveillance" = "Surveillance System Design",
        "comp-outbreak" = "Epidemiology Foundations",
        "comp-sampling" = "Epidemiology Foundations",
        "comp-data-mgmt" = "Research Methods and Scientific Writing",
        "comp-diagnostics" = "Surveillance System Design",
        "comp-sci-writing" = "Research Methods and Scientific Writing",
        "comp-research-ethics" = "Research Methods and Scientific Writing",
        "comp-leadership" = "Surveillance System Design"
      )

      div(class = "competency-grid",
        lapply(seq_len(nrow(comps)), function(i) {
          c <- comps[i, ]
          col <- level_col(c$level)
          pct <- level_pct(c$level)
          act_n <- tryCatch(
            db_scalar(paths, sprintf(
              "SELECT COUNT(*) FROM learning_activities WHERE competency_id = '%s'",
              c$competency_id
            )),
            error = function(...) 0L
          )
          last_act <- if (!is.na(c$last_activity) && nzchar(c$last_activity)) {
            substr(c$last_activity, 1L, 10L)
          } else {
            "never"
          }

          div(class = "competency-card",
            div(class = "competency-card-header",
              tags$strong(c$topic),
              tags$span(class = "competency-level-badge", style = paste0("background:", col, ";"), c$level)
            ),
            div(class = "competency-bar-wrap",
              div(class = "competency-bar-fill", style = sprintf("width:%d%%; background:%s;", pct, col))
            ),
            div(class = "competency-card-meta",
              tags$span(paste0(act_n, " activities")),
              tags$span(paste0("Last: ", last_act))
            ),
            if (!is.na(course_map[[c$competency_id]])) {
              tags$p(style = "font-size:0.78rem; color:#6d7c74; margin-top:0.45rem;",
                paste0("Suggested course: ", course_map[[c$competency_id]])
              )
            }
          )
        })
      )
    })

    output$competency_select_ui <- renderUI({
      comps <- get_competencies(paths)
      if (!nrow(comps)) {
        return(NULL)
      }
      choices <- stats::setNames(comps$competency_id, comps$topic)
      selectInput(ns("activity_competency"), "Competency", choices = choices)
    })

    observeEvent(input$log_activity, {
      req(input$activity_competency, nzchar(input$activity_desc))
      insert_learning_activity(paths, input$activity_competency, input$activity_type, input$activity_desc)
      log_status_text(sprintf("Logged: %s", input$activity_desc))
      refresh_trigger(refresh_trigger() + 1L)
    })

    output$log_status <- renderText(log_status_text())

    output$recent_activities_ui <- renderUI({
      refresh_trigger()
      acts <- tryCatch(
        db_table(paths, paste(
          "SELECT a.activity_type, a.description, a.completed_at, c.topic",
          "FROM learning_activities a",
          "LEFT JOIN learning_competencies c ON c.competency_id = a.competency_id",
          "ORDER BY a.completed_at DESC LIMIT 15"
        )),
        error = function(...) data.frame()
      )
      if (!nrow(acts)) {
        return(div(class = "empty-state", "No activities logged yet."))
      }

      type_icon <- function(t) switch(t,
        course_lesson = "graduation-cap",
        paper_read = "book-open",
        exercise = "pen-ruler",
        sr_review = "brain",
        tutorial = "video",
        practice = "code",
        "circle"
      )

      tags$ul(style = "padding-left:0; list-style:none;",
        lapply(seq_len(nrow(acts)), function(i) {
          a <- acts[i, ]
          tags$li(class = "learning-activity-row",
            icon(type_icon(a$activity_type)),
            tags$span(class = "learning-activity-desc", a$description),
            tags$span(class = "learning-activity-topic", a$topic),
            tags$span(class = "learning-activity-date", substr(a$completed_at, 1L, 10L))
          )
        })
      )
    })

    observeEvent(input$learning_sr_rating, {
      req(input$learning_sr_rating, is.list(input$learning_sr_rating))
      update_sr_review(paths, input$learning_sr_rating$sr_id, input$learning_sr_rating$rating)
      sr_refresh(sr_refresh() + 1L)
    }, ignoreNULL = TRUE)

    output$learning_sr_section <- renderUI({
      sr_refresh()
      refresh_trigger()
      due <- tryCatch(
        db_table(paths, sprintf(
          "SELECT * FROM spaced_repetition WHERE source_table IN ('learning_competencies','course_progress') AND next_review <= '%s' ORDER BY next_review ASC LIMIT 1",
          format(Sys.Date())
        )),
        error = function(...) data.frame()
      )
      if (!nrow(due)) {
        return(NULL)
      }

      item <- due[1L, ]
      hard_js <- sprintf("Shiny.setInputValue('%s',{sr_id:'%s',rating:'hard'},{priority:'event'})", ns("learning_sr_rating"), item$sr_id)
      good_js <- sprintf("Shiny.setInputValue('%s',{sr_id:'%s',rating:'good'},{priority:'event'})", ns("learning_sr_rating"), item$sr_id)
      easy_js <- sprintf("Shiny.setInputValue('%s',{sr_id:'%s',rating:'easy'},{priority:'event'})", ns("learning_sr_rating"), item$sr_id)

      card(
        class = "learning-section-card",
        card_header(tagList(icon("brain"), "  Learning review")),
        card_body(
          div(class = "sr-widget",
            div(class = "sr-deck-label",
              sprintf("Review %d | interval %d days", item$repetitions + 1L, item$interval_days)
            ),
            div(class = "sr-prompt",
              tags$em("What do you remember about:"), tags$br(), tags$strong(item$front_text)
            ),
            tags$button(
              id = ns("sr_reveal"), class = "btn btn-outline-secondary btn-sm",
              onclick = sprintf("this.style.display='none'; document.getElementById('%s').style.display='block';", ns("sr_answer")),
              tagList(icon("eye"), "  Reveal")
            ),
            div(id = ns("sr_answer"), style = "display:none;",
              div(class = "sr-answer",
                tags$pre(style = "white-space:pre-wrap; font-size:0.84rem; margin:0;",
                  if (!is.na(item$back_text)) item$back_text else "No details stored."
                )
              ),
              div(class = "sr-rating-row",
                tags$button(class = "btn btn-sm", style = "background:#c0392b;color:#fff;", onclick = hard_js, "Hard"),
                tags$button(class = "btn btn-sm", style = "background:#2d6073;color:#fff;", onclick = good_js, "Good"),
                tags$button(class = "btn btn-sm", style = "background:#2e6b4f;color:#fff;", onclick = easy_js, "Easy")
              )
            )
          )
        )
      )
    })

    output$resources_ui <- renderUI({
      refresh_trigger()
      comps <- get_competencies(paths)
      if (!nrow(comps)) {
        return(div(class = "empty-state", "No competencies to show."))
      }

      resources <- tryCatch(
        db_table(paths, "SELECT * FROM learning_resources ORDER BY competency_id, title"),
        error = function(...) data.frame()
      )

      div(class = "learning-path-grid",
        lapply(seq_len(nrow(comps)), function(i) {
          c <- comps[i, ]
          c_res <- if (nrow(resources)) {
            resources[resources$competency_id == c$competency_id, , drop = FALSE]
          } else {
            data.frame()
          }

          div(class = "learning-path-card",
            tags$strong(c$topic), " ",
            tags$span(class = "competency-level-badge",
              style = paste0("background:", switch(c$level,
                beginner = "#c0392b",
                intermediate = "#b36a1d",
                advanced = "#2e6b4f",
                "#6d7c74"
              ), ";"),
              c$level
            ),
            if (nrow(c_res)) {
              tags$ul(style = "font-size:0.82rem; padding-left:1.1em; margin:0.3rem 0 0;",
                lapply(seq_len(nrow(c_res)), function(j) {
                  r <- c_res[j, ]
                  tags$li(
                    if (!is.na(r$url) && nzchar(r$url)) {
                      tags$a(href = r$url, target = "_blank", r$title)
                    } else {
                      tags$span(r$title)
                    },
                    tags$span(style = "font-size:0.72rem; color:#888;", paste0(" [", r$resource_type, "]"))
                  )
                })
              )
            } else {
              tags$p(style = "font-size:0.78rem; color:#aaa; margin:0.2rem 0 0;", "No resources yet.")
            }
          )
        })
      )
    })

    # ── Skill gap analysis ───────────────────────────────────────────
    observeEvent(input$analyse_skill_gaps, {
      # Build a prompt showing recent activity vs competency coverage
      comps <- tryCatch(
        db_table(paths, "SELECT domain, topic, level, last_activity FROM learning_competencies ORDER BY domain"),
        error = function(...) data.frame()
      )
      recent_runs <- tryCatch(
        db_table(paths, paste(
          "SELECT agent_slug, task_summary, created_at FROM agent_runs",
          "ORDER BY created_at DESC LIMIT 20"
        )),
        error = function(...) data.frame()
      )
      recent_acts <- tryCatch(
        db_table(paths, paste(
          "SELECT a.activity_type, a.description, c.domain",
          "FROM learning_activities a",
          "LEFT JOIN learning_competencies c ON c.competency_id = a.competency_id",
          "ORDER BY a.completed_at DESC LIMIT 15"
        )),
        error = function(...) data.frame()
      )

      # Identify untouched competencies
      untouched <- if (nrow(comps)) {
        comps[is.na(comps$last_activity) | comps$last_activity == "", , drop = FALSE]
      } else data.frame()

      prompt <- paste(
        "/learning-coach Analyse my current skill gaps.",
        "",
        "Competency levels:",
        if (nrow(comps)) paste(sprintf("  - %s (%s): %s", comps$domain, comps$level, comps$topic), collapse = "\n") else "  None recorded.",
        "",
        if (nrow(untouched)) paste("Untouched competencies:", paste(untouched$domain, collapse = ", ")) else "",
        "",
        "Recent activities:",
        if (nrow(recent_acts)) paste(sprintf("  - [%s] %s", recent_acts$activity_type, recent_acts$description), collapse = "\n") else "  None logged.",
        "",
        "Recent agent runs (last 20):",
        if (nrow(recent_runs)) paste(sprintf("  - %s: %s", recent_runs$agent_slug, recent_runs$task_summary), collapse = "\n") else "  None.",
        "",
        "Find: where are the gaps between what I work on and what I study? What should I prioritize?",
        sep = "\n"
      )

      output$skill_gap_result <- renderUI({
        div(
          tags$p(style = "font-size:0.84rem; font-weight:600; margin-bottom:0.5rem;",
                 "Copy this prompt into Claude Code:"),
          div(class = "skill-gap-prompt", prompt),
          div(class = "action-row",
            tags$script(sprintf(
              "function copySkillGap() {
                navigator.clipboard.writeText(%s).then(function() {
                  var b=document.getElementById('skill-gap-copy');
                  b.innerText='Copied!';
                  setTimeout(function(){b.innerText='Copy prompt';}, 2000);
                });
              }",
              jsonlite::toJSON(prompt, auto_unbox = TRUE)
            )),
            tags$button(id = "skill-gap-copy", class = "btn btn-sm btn-primary",
                        onclick = "copySkillGap()", "Copy prompt")
          ),
          if (nrow(untouched)) {
            div(class = "skill-gap-result",
              tags$strong("Quick scan — untouched competencies:"),
              tags$ul(lapply(seq_len(nrow(untouched)), function(i)
                tags$li(untouched$domain[i])
              ))
            )
          }
        )
      })
    })
  })
}

`%||%` <- function(x, y) {
  if (is.null(x) || !length(x) || is.na(x)) y else x
}
