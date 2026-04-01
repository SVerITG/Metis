ensure_db_schema <- function(paths) {
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS library_inventory (
      relative_path TEXT PRIMARY KEY,
      basename TEXT,
      top_folder TEXT,
      extension TEXT,
      size_bytes INTEGER,
      modified_date TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS library_duplicates (
      hash TEXT,
      duplicate_count INTEGER,
      file TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS library_seeded (
      relative_path TEXT PRIMARY KEY,
      basename TEXT,
      top_folder TEXT,
      extension TEXT,
      size_bytes INTEGER,
      modified_date TEXT,
      entity_type TEXT,
      disease TEXT,
      geography TEXT,
      method TEXT,
      surveillance_mode TEXT,
      elimination_phase TEXT,
      diagnostic_test TEXT,
      project_link TEXT,
      phd_article_link TEXT,
      relevance_note TEXT,
      status TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS meetings (
      meeting_id TEXT PRIMARY KEY,
      title TEXT,
      meeting_date TEXT,
      domain TEXT,
      project TEXT,
      source_filename TEXT,
      stored_audio_path TEXT,
      structured_note_path TEXT,
      transcript_path TEXT,
      transcript_status TEXT,
      created_at TEXT
    )
    "
  )

  meeting_cols <- DBI::dbGetQuery(con, "PRAGMA table_info(meetings)")
  existing_cols <- meeting_cols$name
  if (!"transcript_path" %in% existing_cols) {
    DBI::dbExecute(con, "ALTER TABLE meetings ADD COLUMN transcript_path TEXT")
  }
  if (!"transcript_status" %in% existing_cols) {
    DBI::dbExecute(con, "ALTER TABLE meetings ADD COLUMN transcript_status TEXT")
  }

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS news_briefs (
      brief_id TEXT PRIMARY KEY,
      brief_date TEXT,
      title TEXT,
      domain TEXT,
      signal_strength TEXT,
      summary TEXT,
      project_link TEXT,
      created_at TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS projects (
      project_id TEXT PRIMARY KEY,
      title TEXT,
      domain TEXT,
      status TEXT,
      priority TEXT,
      next_step TEXT,
      external_path TEXT,
      github_url TEXT,
      created_at TEXT
    )
    "
  )

  project_cols <- DBI::dbGetQuery(con, "PRAGMA table_info(projects)")$name
  if (!"external_path" %in% project_cols) {
    DBI::dbExecute(con, "ALTER TABLE projects ADD COLUMN external_path TEXT")
  }
  if (!"github_url" %in% project_cols) {
    DBI::dbExecute(con, "ALTER TABLE projects ADD COLUMN github_url TEXT")
  }
  if (!"launch_cmd" %in% project_cols) {
    DBI::dbExecute(con, "ALTER TABLE projects ADD COLUMN launch_cmd TEXT")
  }

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS tasks (
      task_id TEXT PRIMARY KEY,
      project_id TEXT,
      title TEXT,
      status TEXT,
      due_date TEXT,
      owner TEXT,
      notes TEXT,
      created_at TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS jobs_log (
      job_id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_type TEXT,
      status TEXT,
      details TEXT,
      created_at TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS ideas (
      idea_id TEXT PRIMARY KEY,
      text TEXT,
      project_id TEXT,
      idea_type TEXT,
      tags TEXT,
      created_at TEXT
    )
    "
  )

  idea_cols <- DBI::dbGetQuery(con, "PRAGMA table_info(ideas)")$name
  if (!"domain" %in% idea_cols) {
    DBI::dbExecute(con, "ALTER TABLE ideas ADD COLUMN domain TEXT")
  }
  if (!"linked_papers" %in% idea_cols) {
    DBI::dbExecute(con, "ALTER TABLE ideas ADD COLUMN linked_papers TEXT")
  }
  if (!"feasibility" %in% idea_cols) {
    DBI::dbExecute(con, "ALTER TABLE ideas ADD COLUMN feasibility TEXT")
  }
  if (!"phd_relevance" %in% idea_cols) {
    DBI::dbExecute(con, "ALTER TABLE ideas ADD COLUMN phd_relevance TEXT")
  }
  if (!"novelty_status" %in% idea_cols) {
    DBI::dbExecute(con, "ALTER TABLE ideas ADD COLUMN novelty_status TEXT")
  }

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS idea_links (
      link_id INTEGER PRIMARY KEY AUTOINCREMENT,
      idea_id_a TEXT,
      idea_id_b TEXT,
      link_label TEXT,
      created_at TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS spaced_repetition (
      sr_id         TEXT PRIMARY KEY,
      source_table  TEXT NOT NULL,
      source_id     TEXT NOT NULL,
      front_text    TEXT,
      back_text     TEXT,
      next_review   TEXT NOT NULL,
      interval_days INTEGER DEFAULT 1,
      ease_factor   REAL DEFAULT 2.5,
      repetitions   INTEGER DEFAULT 0,
      created_at    TEXT NOT NULL
    )
    "
  )

  DBI::dbExecute(
    con,
    "CREATE INDEX IF NOT EXISTS idx_sr_next_review ON spaced_repetition(next_review)"
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS phd_milestones (
      milestone_id  TEXT PRIMARY KEY,
      article_title TEXT NOT NULL,
      target_date   TEXT NOT NULL,
      status        TEXT NOT NULL DEFAULT 'planned',
      notes         TEXT,
      created_at    TEXT NOT NULL
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS course_progress (
      progress_id  TEXT PRIMARY KEY,
      course_id    TEXT NOT NULL,
      lesson_id    TEXT NOT NULL,
      completed_at TEXT,
      notes        TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS knowledge_links (
      link_id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_type TEXT,
      source_id TEXT,
      target_type TEXT,
      target_id TEXT,
      link_label TEXT,
      created_at TEXT
    )
    "
  )

  # ── v5 News synthesis tables ──────────────────────────────────────
  news_cols <- DBI::dbGetQuery(con, "PRAGMA table_info(news_briefs)")$name
  if (!"source_url" %in% news_cols) {
    DBI::dbExecute(con, "ALTER TABLE news_briefs ADD COLUMN source_url TEXT")
  }
  if (!"tags" %in% news_cols) {
    DBI::dbExecute(con, "ALTER TABLE news_briefs ADD COLUMN tags TEXT")
  }
  if (!"surprise_flag" %in% news_cols) {
    DBI::dbExecute(con, "ALTER TABLE news_briefs ADD COLUMN surprise_flag INTEGER DEFAULT 0")
  }

  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS news_topics (
      topic_id        TEXT PRIMARY KEY,
      label           TEXT,
      domain          TEXT,
      first_seen      TEXT,
      last_seen       TEXT,
      mention_count   INTEGER DEFAULT 1,
      trend_direction TEXT DEFAULT 'stable'
    )
  ")

  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS news_brief_topics (
      brief_id TEXT,
      topic_id TEXT,
      PRIMARY KEY (brief_id, topic_id)
    )
  ")

  DBI::dbExecute(con, "CREATE INDEX IF NOT EXISTS idx_briefs_date ON news_briefs(brief_date)")
  DBI::dbExecute(con, "CREATE INDEX IF NOT EXISTS idx_briefs_domain ON news_briefs(domain)")

  # ── v5 Meeting intelligence tables ────────────────────────────────
  mtg_cols <- DBI::dbGetQuery(con, "PRAGMA table_info(meetings)")$name
  for (col in c("attendees", "meeting_type", "decisions", "action_items",
                "follow_ups", "linked_meetings", "pre_briefing_path")) {
    if (!col %in% mtg_cols) {
      DBI::dbExecute(con, sprintf("ALTER TABLE meetings ADD COLUMN %s TEXT", col))
    }
  }

  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS meeting_persons (
      person_id        TEXT PRIMARY KEY,
      name             TEXT,
      role             TEXT,
      last_meeting_date TEXT,
      meeting_count    INTEGER DEFAULT 0
    )
  ")

  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS meeting_attendance (
      meeting_id TEXT,
      person_id  TEXT,
      PRIMARY KEY (meeting_id, person_id)
    )
  ")

  # ── v5 Learning tables ───────────────────────────────────────────
  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS learning_competencies (
      competency_id TEXT PRIMARY KEY,
      domain        TEXT,
      topic         TEXT,
      level         TEXT DEFAULT 'beginner',
      notes         TEXT,
      last_activity TEXT,
      created_at    TEXT
    )
  ")

  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS learning_activities (
      activity_id   TEXT PRIMARY KEY,
      competency_id TEXT,
      activity_type TEXT,
      description   TEXT,
      completed_at  TEXT
    )
  ")

  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS learning_resources (
      resource_id    TEXT PRIMARY KEY,
      competency_id  TEXT,
      title          TEXT,
      resource_type  TEXT,
      url            TEXT,
      recommended_by TEXT,
      created_at     TEXT
    )
  ")

  # ── v5 Finance tables ────────────────────────────────────────────
  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS finance_watchlist (
      item_id    TEXT PRIMARY KEY,
      category   TEXT,
      label      TEXT,
      notes      TEXT,
      created_at TEXT
    )
  ")

  DBI::dbExecute(con, "
    CREATE TABLE IF NOT EXISTS finance_snapshots (
      snapshot_id   TEXT PRIMARY KEY,
      snapshot_date TEXT,
      category      TEXT,
      label         TEXT,
      headline      TEXT,
      detail        TEXT,
      trend         TEXT,
      project_link  TEXT,
      created_at    TEXT
    )
  ")

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS agent_runs (
      run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
      agent_slug TEXT,
      task_summary TEXT,
      input_path TEXT,
      output_path TEXT,
      status     TEXT DEFAULT 'completed',
      created_at TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS crucible_intake (
      intake_id           TEXT PRIMARY KEY,
      filename            TEXT,
      file_type           TEXT,
      analysis_type       TEXT,
      project_link        TEXT,
      phd_article_link    TEXT,
      analysis_depth      TEXT,
      focus               TEXT,
      custom_instructions TEXT,
      stored_path         TEXT,
      output_path         TEXT,
      status              TEXT DEFAULT 'pending',
      ideas_extracted     INTEGER DEFAULT 0,
      tasks_created       INTEGER DEFAULT 0,
      created_at          TEXT
    )
    "
  )

  DBI::dbExecute(
    con,
    "
    CREATE TABLE IF NOT EXISTS talks (
      talk_id              TEXT PRIMARY KEY,
      title                TEXT,
      speaker              TEXT,
      source               TEXT,
      event_name           TEXT,
      talk_date            TEXT,
      url                  TEXT,
      transcript_path      TEXT,
      structured_note_path TEXT,
      domain               TEXT,
      project_link         TEXT,
      key_takeaways        TEXT,
      created_at           TEXT
    )
    "
  )

  invisible(TRUE)
}

update_task_status <- function(paths, task_id, new_status) {
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  DBI::dbExecute(con, "UPDATE tasks SET status = ? WHERE task_id = ?",
                 params = list(new_status, task_id))
  invisible(TRUE)
}

update_task_notes <- function(paths, task_id, notes) {
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  DBI::dbExecute(con, "UPDATE tasks SET notes = ? WHERE task_id = ?",
                 params = list(notes, task_id))
  invisible(TRUE)
}

get_course_progress <- function(paths, course_id) {
  ensure_db_schema(paths)
  db_table(paths, sprintf(
    "SELECT * FROM course_progress WHERE course_id = '%s'",
    course_id
  ))
}

mark_lesson_complete <- function(paths, course_id, lesson_id) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  progress_id <- sprintf("prog-%s-%s", make_slug(course_id), make_slug(lesson_id))
  DBI::dbExecute(
    con,
    "INSERT OR REPLACE INTO course_progress (progress_id, course_id, lesson_id, completed_at) VALUES (?, ?, ?, ?)",
    params = list(progress_id, course_id, lesson_id, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(TRUE)
}

insert_sr_item <- function(paths, source_table, source_id, front_text, back_text) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  sr_id <- sprintf("sr-%s", format(Sys.time(), "%Y%m%d%H%M%S%OS3"))
  DBI::dbExecute(
    con,
    paste(
      "INSERT OR IGNORE INTO spaced_repetition",
      "(sr_id, source_table, source_id, front_text, back_text, next_review, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?)"
    ),
    params = list(
      sr_id, source_table, source_id, front_text, back_text,
      format(Sys.Date()),
      format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    )
  )
  invisible(sr_id)
}

get_due_sr_items <- function(paths, n = 1L) {
  ensure_db_schema(paths)
  db_table(paths, sprintf(
    "SELECT * FROM spaced_repetition WHERE next_review <= '%s' ORDER BY next_review ASC LIMIT %d",
    format(Sys.Date()), as.integer(n)
  ))
}

update_sr_review <- function(paths, sr_id, rating) {
  item <- tryCatch(
    db_table(paths, sprintf("SELECT * FROM spaced_repetition WHERE sr_id = '%s'", sr_id)),
    error = function(...) data.frame()
  )
  if (!nrow(item)) return(invisible(FALSE))

  new_interval <- sm2_next_review(item$interval_days[1L], rating)
  new_review   <- format(Sys.Date() + new_interval)
  new_reps     <- item$repetitions[1L] + 1L

  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  DBI::dbExecute(
    con,
    "UPDATE spaced_repetition SET next_review=?, interval_days=?, repetitions=? WHERE sr_id=?",
    params = list(new_review, new_interval, new_reps, sr_id)
  )
  invisible(TRUE)
}

insert_phd_milestone <- function(paths, article_title, target_date, status, notes) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  milestone_id <- sprintf("ms-%s-%s", make_slug(article_title), format(Sys.time(), "%Y%m%d%H%M%S"))
  DBI::dbExecute(
    con,
    paste(
      "INSERT INTO phd_milestones",
      "(milestone_id, article_title, target_date, status, notes, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?)"
    ),
    params = list(
      milestone_id, article_title, target_date, status,
      if (nzchar(notes)) notes else NA_character_,
      format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    )
  )
  invisible(milestone_id)
}

get_phd_milestones <- function(paths) {
  db_table(paths, "SELECT * FROM phd_milestones ORDER BY target_date ASC")
}

seed_default_data <- function(paths) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  project_count <- DBI::dbGetQuery(con, "SELECT COUNT(*) AS n FROM projects")$n[[1]]
  if (identical(project_count, 0L) || identical(project_count, 0)) {
    now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    projects <- data.frame(
      project_id = c("phd-framework", "passive-screening-drc", "metis-dashboard"),
      title = c("PhD framework", "Passive screening in DRC", "Metis dashboard"),
      domain = c("phd", "sleeping sickness", "software"),
      status = c("active", "active", "active"),
      priority = c("high", "high", "high"),
      next_step = c(
        "Refine the thesis spine across current and future papers",
        "Consolidate evidence and operational notes",
        "Wire more agents into the app"
      ),
      created_at = rep(now, 3),
      stringsAsFactors = FALSE
    )
    DBI::dbWriteTable(con, "projects", projects, append = TRUE)
  }

  task_count <- DBI::dbGetQuery(con, "SELECT COUNT(*) AS n FROM tasks")$n[[1]]
  if (identical(task_count, 0L) || identical(task_count, 0)) {
    now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    tasks <- data.frame(
      task_id = c("task-phd-map", "task-news-page", "task-meeting-transcribe",
                   "task-news-aggregator-config", "task-ux-audit", "task-epi-review"),
      project_id = c("phd-framework", "metis-dashboard", "metis-dashboard",
                      "metis-dashboard", "metis-dashboard", "phd-framework"),
      title = c(
        "Refine PhD evidence map",
        "Review latest brief categories",
        "Install and connect local Whisper workflow",
        "Configure and run initial 18-feed collection",
        "Audit dashboard CSS for WCAG AA compliance",
        "Review passive case detection study design"
      ),
      status = c("open", "open", "open", "open", "open", "open"),
      due_date = c("", "", "", "", "", ""),
      owner = c("Metis", "Metis", "Meeting Memory",
                 "News Aggregator", "UX Engineer", "Epidemiologist"),
      notes = c(
        "Link current articles to future-paper candidates",
        "Decide which domains should appear in the daily briefing",
        "Auto-transcription is pending local Whisper installation",
        "Run fetch_news_feeds.R with expanded 18-feed config and verify all 8 domains populated",
        "Check contrast ratios, cursor states, hover transitions, and responsive breakpoints",
        "Challenge assumptions about denominator, case definition, and selection bias"
      ),
      created_at = rep(now, 6),
      stringsAsFactors = FALSE
    )
    DBI::dbWriteTable(con, "tasks", tasks, append = TRUE)
  }

  # ── Seed learning competencies ──────────────────────────────────────────
  comp_count <- DBI::dbGetQuery(con, "SELECT COUNT(*) AS n FROM learning_competencies")$n[[1]]
  if (identical(comp_count, 0L) || identical(comp_count, 0)) {
    now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    competencies <- data.frame(
      competency_id = c("comp-epi-methods", "comp-biostatistics", "comp-spatial-epi",
                         "comp-surveillance", "comp-outbreak", "comp-sampling",
                         "comp-data-mgmt", "comp-diagnostics", "comp-sci-writing",
                         "comp-research-ethics", "comp-health-economics", "comp-leadership"),
      domain = c("Epidemiological methods", "Biostatistics", "Spatial epidemiology",
                 "Surveillance systems", "Outbreak investigation", "Sampling strategies",
                 "Data management & R", "Diagnostic evaluation", "Scientific communication",
                 "Research ethics", "Health economics", "Leadership & management"),
      topic = c(
        "Study design, bias, measures of association, DAGs",
        "Regression, multilevel models, survival analysis, Bayesian",
        "SaTScan, GIS, disease mapping, spatial regression",
        "System design, evaluation (CDC attributes), IBS/EBS, digital",
        "CDC 10-step, rapid assessment, epidemic curves, field investigation",
        "Probability sampling, LQAS, cluster surveys, sample size",
        "FAIR principles, reproducibility, R workflows, Git, REDCap/DHIS2",
        "Test accuracy, STARD, PPV in low-prevalence, ROC curves",
        "EQUATOR guidelines, IMRaD, journal selection, peer review",
        "Helsinki, IRB, consent in LMICs, community engagement, GDPR",
        "CEA, DALY/QALY, ICER, budget impact, economic evaluation",
        "Project management, stakeholder engagement, team supervision"
      ),
      level = rep("beginner", 12),
      notes = c(
        "Foundation for all epidemiological research. Library card: methods/study-designs.md",
        "Currently taking MLM course. Library card: methods/biostatistics-essentials.md",
        "Active use with SaTScan for HAT clustering. Library card: methods/spatial-epidemiology.md",
        "Core professional domain. Library card: methods/surveillance-systems.md",
        "FETP core skill. Library card: methods/outbreak-investigation.md",
        "Needed for PhD study design. Library card: methods/sampling-strategies.md",
        "Strong in R, building reproducibility practices. Library card: methods/data-management.md",
        "Directly relevant to HAT diagnostics work. Library card: methods/diagnostic-test-evaluation.md",
        "Building through PhD writing. Library card: methods/writing-for-journals.md",
        "Formalizing through PhD process. Library card: concepts/research-ethics.md",
        "Foundation needed for policy arguments. Library card: methods/health-economics-basics.md",
        "Growing through PhD and project coordination"
      ),
      last_activity = rep("", 12),
      created_at = rep(now, 12),
      stringsAsFactors = FALSE
    )
    DBI::dbWriteTable(con, "learning_competencies", competencies, append = TRUE)
  }

  # ── Seed learning resources ─────────────────────────────────────────────
  res_count <- DBI::dbGetQuery(con, "SELECT COUNT(*) AS n FROM learning_resources")$n[[1]]
  if (identical(res_count, 0L) || identical(res_count, 0)) {
    now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    resources <- data.frame(
      resource_id = sprintf("res-%03d", 1:16),
      competency_id = c(
        "comp-epi-methods", "comp-epi-methods",
        "comp-biostatistics", "comp-biostatistics",
        "comp-spatial-epi", "comp-spatial-epi",
        "comp-surveillance", "comp-surveillance",
        "comp-outbreak",
        "comp-sampling",
        "comp-data-mgmt",
        "comp-diagnostics",
        "comp-sci-writing",
        "comp-research-ethics",
        "comp-health-economics",
        "comp-leadership"
      ),
      title = c(
        "Gordis Epidemiology, 7th Ed (2024)",
        "Rothman - Modern Epidemiology, 4th Ed",
        "Kirkwood & Sterne - Essential Medical Statistics",
        "Gelman & Hill - Data Analysis Using Regression and MLM",
        "Lawson - Handbook of Spatial Epidemiology",
        "Bivand et al. - Applied Spatial Data Analysis with R",
        "CDC - Principles of Epi in Public Health Practice",
        "WHO PHI Competency Framework (2025)",
        "CDC Field Epidemiology Manual",
        "Levy & Lemeshow - Sampling of Populations",
        "Wilson et al. - Good Enough Practices in Scientific Computing",
        "Bossuyt et al. - STARD 2015 Guidelines",
        "EQUATOR Network Reporting Guidelines",
        "CIOMS International Ethical Guidelines (2016)",
        "Drummond et al. - Methods for Economic Evaluation",
        "WHO - Global Competency Framework for Essential PH Functions"
      ),
      resource_type = c(
        "textbook", "textbook",
        "textbook", "textbook",
        "textbook", "textbook",
        "online", "guideline",
        "online",
        "textbook",
        "paper",
        "guideline",
        "online",
        "guideline",
        "textbook",
        "guideline"
      ),
      url = c(
        "", "",
        "", "",
        "", "",
        "https://www.cdc.gov/eis/field-epi-manual/index.html",
        "https://www.who.int/docs/default-source/eios/phi-competency-framework.pdf",
        "https://www.cdc.gov/eis/field-epi-manual/index.html",
        "",
        "https://doi.org/10.1371/journal.pcbi.1005510",
        "https://www.equator-network.org/reporting-guidelines/stard/",
        "https://www.equator-network.org/",
        "https://cioms.ch/wp-content/uploads/2017/01/WEB-CIOMS-EthicalGuidelines.pdf",
        "",
        "https://www.who.int/publications/i/item/9789240091214"
      ),
      recommended_by = rep("Metis", 16),
      created_at = rep(now, 16),
      stringsAsFactors = FALSE
    )
    DBI::dbWriteTable(con, "learning_resources", resources, append = TRUE)
  }
}

refresh_db_from_files <- function(paths) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  inventory_path <- file.path(paths$literature_metadata, "library-inventory.tsv")
  duplicates_path <- file.path(paths$literature_metadata, "exact-duplicates.tsv")
  seeded_path <- file.path(paths$literature_metadata, "library-phd-seeded.tsv")

  inventory <- safe_read_tsv(inventory_path)
  duplicates <- safe_read_tsv(duplicates_path)
  seeded <- safe_read_tsv(seeded_path)

  DBI::dbWithTransaction(con, {
    DBI::dbExecute(con, "DELETE FROM library_inventory")
    DBI::dbExecute(con, "DELETE FROM library_duplicates")
    DBI::dbExecute(con, "DELETE FROM library_seeded")

    if (nrow(inventory)) {
      DBI::dbWriteTable(con, "library_inventory", inventory, append = TRUE)
    }
    if (nrow(duplicates)) {
      names(duplicates) <- c("hash", "duplicate_count", "file")
      DBI::dbWriteTable(con, "library_duplicates", duplicates, append = TRUE)
    }
    if (nrow(seeded)) {
      DBI::dbWriteTable(con, "library_seeded", seeded, append = TRUE)
    }
  })

  log_job(paths, "refresh_metadata_db", "success", sprintf(
    "Inventory: %s rows; duplicates: %s rows; seeded: %s rows",
    nrow(inventory), nrow(duplicates), nrow(seeded)
  ))

  invisible(TRUE)
}

log_job <- function(paths, job_type, status, details = "") {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  invisible(DBI::dbExecute(
    con,
    "INSERT INTO jobs_log (job_type, status, details, created_at) VALUES (?, ?, ?, ?)",
    params = list(job_type, status, details, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  ))
}

db_scalar <- function(paths, sql) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  res <- DBI::dbGetQuery(con, sql)
  if (!nrow(res)) {
    return(0L)
  }

  res[[1]][1]
}

db_table <- function(paths, sql) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  DBI::dbGetQuery(con, sql)
}

make_slug <- function(text) {
  slug <- gsub("[^A-Za-z0-9]+", "-", tolower(text))
  slug <- gsub("(^-+|-+$)", "", slug)
  if (!nzchar(slug)) {
    slug <- "item"
  }
  slug
}

insert_project <- function(paths, title, domain, status, priority, next_step) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  project_id <- sprintf("%s-%s", make_slug(title), format(Sys.time(), "%Y%m%d%H%M%S"))
  DBI::dbExecute(
    con,
    paste(
      "INSERT INTO projects",
      "(project_id, title, domain, status, priority, next_step, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?)"
    ),
    params = list(project_id, title, domain, status, priority, next_step, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(project_id)
}

insert_task <- function(paths, project_id, title, status, due_date, owner, notes) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  task_id <- sprintf("%s-%s", make_slug(title), format(Sys.time(), "%Y%m%d%H%M%S"))
  DBI::dbExecute(
    con,
    paste(
      "INSERT INTO tasks",
      "(task_id, project_id, title, status, due_date, owner, notes, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    ),
    params = list(task_id, project_id, title, status, due_date, owner, notes, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(task_id)
}

log_agent_run <- function(paths, agent_slug, task_summary, input_path = "", output_path = "") {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  DBI::dbExecute(
    con,
    paste(
      "INSERT INTO agent_runs",
      "(agent_slug, task_summary, input_path, output_path, status, created_at)",
      "VALUES (?, ?, ?, ?, 'completed', ?)"
    ),
    params = list(agent_slug, task_summary, input_path, output_path,
                  format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
}

insert_news_brief <- function(paths, brief_date, title, domain, signal_strength, summary, project_link) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  brief_id <- sprintf("%s-%s", brief_date, make_slug(title))
  DBI::dbExecute(
    con,
    paste(
      "INSERT OR REPLACE INTO news_briefs",
      "(brief_id, brief_date, title, domain, signal_strength, summary, project_link, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    ),
    params = list(brief_id, brief_date, title, domain, signal_strength, summary, project_link, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(brief_id)
}

project_choices <- function(paths) {
  projects <- db_table(paths, "SELECT project_id, title FROM projects ORDER BY title")
  if (!nrow(projects)) {
    return(setNames(character(), character()))
  }
  stats::setNames(projects$project_id, projects$title)
}

insert_idea <- function(paths, text, project_id, idea_type, tags,
                        domain = "", linked_papers = "", feasibility = "",
                        phd_relevance = "", novelty_status = "") {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  idea_id <- sprintf("idea-%s", format(Sys.time(), "%Y%m%d%H%M%S"))
  DBI::dbExecute(
    con,
    paste(
      "INSERT INTO ideas",
      "(idea_id, text, project_id, idea_type, tags, domain, linked_papers,",
      "feasibility, phd_relevance, novelty_status, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ),
    params = list(
      idea_id, text,
      if (nzchar(project_id)) project_id else NA_character_,
      idea_type, tags,
      if (nzchar(domain)) domain else NA_character_,
      if (nzchar(linked_papers)) linked_papers else NA_character_,
      if (nzchar(feasibility)) feasibility else NA_character_,
      if (nzchar(phd_relevance)) phd_relevance else NA_character_,
      if (nzchar(novelty_status)) novelty_status else NA_character_,
      format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    )
  )
  invisible(idea_id)
}

insert_talk <- function(paths, title, speaker, source, event_name, talk_date,
                        url = "", transcript_path = "", structured_note_path = "",
                        domain = "", project_link = "", key_takeaways = "") {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  talk_id <- sprintf("talk-%s-%s", format(Sys.time(), "%Y%m%d%H%M%S"), make_slug(title))
  DBI::dbExecute(
    con,
    paste(
      "INSERT INTO talks",
      "(talk_id, title, speaker, source, event_name, talk_date, url, transcript_path,",
      " structured_note_path, domain, project_link, key_takeaways, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ),
    params = list(
      talk_id,
      title,
      speaker,
      source,
      event_name,
      talk_date,
      if (nzchar(url)) url else NA_character_,
      if (nzchar(transcript_path)) transcript_path else NA_character_,
      if (nzchar(structured_note_path)) structured_note_path else NA_character_,
      if (nzchar(domain)) domain else NA_character_,
      if (nzchar(project_link)) project_link else NA_character_,
      if (nzchar(key_takeaways)) key_takeaways else NA_character_,
      format(Sys.time(), "%Y-%m-%d %H:%M:%S")
    )
  )

  invisible(talk_id)
}

get_talks <- function(paths, source = NULL) {
  ensure_db_schema(paths)
  sql <- paste(
    "SELECT talk_id, title, speaker, source, event_name, talk_date,",
    "COALESCE(url,'') AS url,",
    "COALESCE(transcript_path,'') AS transcript_path,",
    "COALESCE(structured_note_path,'') AS structured_note_path,",
    "COALESCE(domain,'') AS domain,",
    "COALESCE(project_link,'') AS project_link,",
    "COALESCE(key_takeaways,'') AS key_takeaways,",
    "created_at",
    "FROM talks"
  )
  if (!is.null(source) && nzchar(source)) {
    sql <- paste(sql, sprintf("WHERE source = '%s'", source))
  }
  sql <- paste(sql, "ORDER BY COALESCE(talk_date, created_at) DESC, created_at DESC")
  db_table(paths, sql)
}

talk_choices <- function(paths) {
  talks <- tryCatch(
    get_talks(paths),
    error = function(...) data.frame()
  )
  if (!nrow(talks)) {
    return(setNames(character(), character()))
  }
  labels <- sprintf(
    "%s | %s%s",
    ifelse(nzchar(talks$talk_date), talks$talk_date, "undated"),
    talks$title,
    ifelse(nzchar(talks$speaker), paste0(" (", talks$speaker, ")"), "")
  )
  stats::setNames(talks$talk_id, labels)
}

get_ideas <- function(paths, project_id = NULL) {
  sql <- if (is.null(project_id) || project_id == "all") {
    paste(
      "SELECT i.idea_id, i.text, COALESCE(p.title, 'Cross-project') AS project,",
      "i.project_id, i.idea_type, i.tags, COALESCE(i.domain,'') AS domain,",
      "COALESCE(i.linked_papers,'') AS linked_papers, COALESCE(i.feasibility,'') AS feasibility,",
      "COALESCE(i.phd_relevance,'') AS phd_relevance, COALESCE(i.novelty_status,'') AS novelty_status,",
      "i.created_at",
      "FROM ideas i LEFT JOIN projects p ON p.project_id = i.project_id",
      "ORDER BY i.created_at DESC"
    )
  } else {
    sprintf(
      paste(
        "SELECT i.idea_id, i.text, COALESCE(p.title, 'Cross-project') AS project,",
        "i.project_id, i.idea_type, i.tags, COALESCE(i.domain,'') AS domain,",
        "COALESCE(i.linked_papers,'') AS linked_papers, COALESCE(i.feasibility,'') AS feasibility,",
        "COALESCE(i.phd_relevance,'') AS phd_relevance, COALESCE(i.novelty_status,'') AS novelty_status,",
        "i.created_at",
        "FROM ideas i LEFT JOIN projects p ON p.project_id = i.project_id",
        "WHERE COALESCE(i.project_id, '') = '%s'",
        "ORDER BY i.created_at DESC"
      ),
      project_id
    )
  }
  db_table(paths, sql)
}

replace_knowledge_links <- function(paths, links_df) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)

  DBI::dbWithTransaction(con, {
    DBI::dbExecute(con, "DELETE FROM knowledge_links")
    if (nrow(links_df)) {
      DBI::dbWriteTable(con, "knowledge_links", links_df, append = TRUE)
    }
  })

  invisible(TRUE)
}

build_knowledge_links <- function(paths) {
  ensure_db_schema(paths)

  add_link <- function(source_type, source_id, target_type, target_id, link_label) {
    data.frame(
      source_type = source_type,
      source_id = source_id,
      target_type = target_type,
      target_id = target_id,
      link_label = link_label,
      created_at = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
      stringsAsFactors = FALSE
    )
  }

  library_root <- file.path(paths$second_brain_root, "06_library")
  course_root <- file.path(library_root, "courses")
  local_course_projects <- c(
    "course-biostatistics",
    "course-epi-foundations",
    "course-health-economics",
    "course-ntd-elimination",
    "course-outbreak-investigation",
    "course-r-for-epidemiologists",
    "course-research-ethics",
    "course-research-writing",
    "course-spatial-epi",
    "course-surveillance-design"
  )

  library_competencies <- c(
    "methods/biostatistics-essentials.md" = "comp-biostatistics",
    "methods/causal-inference.md" = "comp-epi-methods",
    "methods/data-management.md" = "comp-data-mgmt",
    "methods/diagnostic-test-evaluation.md" = "comp-diagnostics",
    "methods/gis-for-epidemiology.md" = "comp-spatial-epi",
    "methods/health-economics-basics.md" = "comp-health-economics",
    "methods/mixed-methods-research.md" = "comp-sci-writing",
    "methods/outbreak-investigation.md" = "comp-outbreak",
    "methods/sampling-strategies.md" = "comp-sampling",
    "methods/spatial-epidemiology.md" = "comp-spatial-epi",
    "methods/study-designs.md" = "comp-epi-methods",
    "methods/surveillance-systems.md" = "comp-surveillance",
    "methods/systematic-reviews.md" = "comp-sci-writing",
    "methods/writing-for-journals.md" = "comp-sci-writing",
    "concepts/current-challenges-2026.md" = "comp-leadership",
    "concepts/digital-health-epi.md" = "comp-data-mgmt",
    "concepts/elimination-framework.md" = "comp-surveillance",
    "concepts/global-health-governance.md" = "comp-leadership",
    "concepts/health-equity-sdh.md" = "comp-research-ethics",
    "concepts/health-systems-strengthening.md" = "comp-leadership",
    "concepts/implementation-science.md" = "comp-sci-writing",
    "concepts/one-health.md" = "comp-surveillance",
    "concepts/research-ethics.md" = "comp-research-ethics",
    "disease-areas/hat-sleeping-sickness.md" = "comp-surveillance",
    "disease-areas/ntd-overview.md" = "comp-surveillance",
    "people-organizations/key-institutions.md" = "comp-leadership"
  )

  library_cards <- sort(unlist(lapply(
    c("methods", "concepts", "disease-areas", "people-organizations"),
    function(folder) {
      files <- list.files(
        file.path(library_root, folder),
        pattern = "\\.md$",
        full.names = FALSE
      )
      file.path(folder, files)
    }
  )))

  missing_cards <- setdiff(library_cards, names(library_competencies))
  extra_cards <- setdiff(names(library_competencies), library_cards)
  if (length(missing_cards) || length(extra_cards)) {
    stop(sprintf(
      "Library competency mapping mismatch. Missing: %s | Extra: %s",
      paste(missing_cards, collapse = ", "),
      paste(extra_cards, collapse = ", ")
    ))
  }

  competency_courses <- list(
    "comp-epi-methods" = c("course-epi-foundations", "course-research-writing"),
    "comp-biostatistics" = c("course-biostatistics", "multilevel-analysis"),
    "comp-spatial-epi" = c("course-spatial-epi"),
    "comp-surveillance" = c("course-ntd-elimination", "course-surveillance-design", "course-epi-foundations"),
    "comp-outbreak" = c("course-outbreak-investigation", "course-epi-foundations", "course-surveillance-design"),
    "comp-sampling" = c("course-epi-foundations", "course-surveillance-design"),
    "comp-data-mgmt" = c("course-r-for-epidemiologists", "course-research-writing", "course-spatial-epi"),
    "comp-diagnostics" = c("course-surveillance-design", "course-research-writing"),
    "comp-sci-writing" = c("course-research-writing"),
    "comp-research-ethics" = c("course-research-ethics", "course-research-writing"),
    "comp-health-economics" = c("course-health-economics"),
    "comp-leadership" = c("course-research-writing", "course-surveillance-design", "course-ntd-elimination")
  )

  related_methods <- list(
    "methods/biostatistics-essentials.md" = c(
      "methods/study-designs.md",
      "methods/causal-inference.md",
      "methods/sampling-strategies.md"
    ),
    "methods/causal-inference.md" = c(
      "methods/study-designs.md",
      "methods/biostatistics-essentials.md",
      "methods/systematic-reviews.md"
    ),
    "methods/data-management.md" = c(
      "methods/surveillance-systems.md",
      "methods/gis-for-epidemiology.md",
      "methods/writing-for-journals.md"
    ),
    "methods/diagnostic-test-evaluation.md" = c(
      "methods/surveillance-systems.md",
      "methods/biostatistics-essentials.md",
      "methods/study-designs.md"
    ),
    "methods/gis-for-epidemiology.md" = c(
      "methods/spatial-epidemiology.md",
      "methods/data-management.md",
      "methods/biostatistics-essentials.md"
    ),
    "methods/health-economics-basics.md" = c(
      "methods/study-designs.md",
      "methods/data-management.md",
      "methods/writing-for-journals.md"
    ),
    "methods/mixed-methods-research.md" = c(
      "methods/study-designs.md",
      "methods/writing-for-journals.md",
      "methods/systematic-reviews.md"
    ),
    "methods/outbreak-investigation.md" = c(
      "methods/surveillance-systems.md",
      "methods/diagnostic-test-evaluation.md",
      "methods/sampling-strategies.md"
    ),
    "methods/sampling-strategies.md" = c(
      "methods/biostatistics-essentials.md",
      "methods/study-designs.md",
      "methods/outbreak-investigation.md"
    ),
    "methods/spatial-epidemiology.md" = c(
      "methods/gis-for-epidemiology.md",
      "methods/biostatistics-essentials.md",
      "methods/surveillance-systems.md"
    ),
    "methods/study-designs.md" = c(
      "methods/causal-inference.md",
      "methods/biostatistics-essentials.md",
      "methods/sampling-strategies.md"
    ),
    "methods/surveillance-systems.md" = c(
      "methods/outbreak-investigation.md",
      "methods/diagnostic-test-evaluation.md",
      "methods/data-management.md"
    ),
    "methods/systematic-reviews.md" = c(
      "methods/writing-for-journals.md",
      "methods/causal-inference.md",
      "methods/mixed-methods-research.md"
    ),
    "methods/writing-for-journals.md" = c(
      "methods/systematic-reviews.md",
      "methods/mixed-methods-research.md",
      "methods/data-management.md"
    )
  )

  links <- list()

  for (card in library_cards) {
    links[[length(links) + 1L]] <- add_link(
      "library_card",
      card,
      "competency",
      unname(library_competencies[[card]]),
      "builds_competency"
    )
  }

  for (competency_id in names(competency_courses)) {
    courses <- competency_courses[[competency_id]]
    if (!length(courses)) {
      next
    }
    for (course_id in courses) {
      links[[length(links) + 1L]] <- add_link(
        "competency",
        competency_id,
        "course",
        course_id,
        "taught_by"
      )
    }
  }

  for (method_id in names(related_methods)) {
    for (target_id in related_methods[[method_id]]) {
      links[[length(links) + 1L]] <- add_link(
        "library_card",
        method_id,
        "library_card",
        target_id,
        "related_method"
      )
    }
  }

  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  course_projects <- DBI::dbGetQuery(
    con,
    "SELECT project_id, external_path FROM projects WHERE domain = 'education'"
  )

  extract_library_refs <- function(lesson_path) {
    lines <- readLines(lesson_path, warn = FALSE, encoding = "UTF-8")
    matches <- regmatches(lines, gregexpr("06_library/[^`]+\\.md", lines, perl = TRUE))
    refs <- unique(unlist(matches, use.names = FALSE))
    if (!length(refs)) {
      return(character())
    }
    sub("^06_library/", "", refs)
  }

  for (i in seq_len(nrow(course_projects))) {
    course_id <- course_projects$project_id[[i]]
    course_path <- course_projects$external_path[[i]]
    if (!course_id %in% local_course_projects) {
      next
    }

    lessons_manifest <- file.path(course_path, "lessons.json")
    lessons_dir <- file.path(course_path, "lessons")
    if (!file.exists(lessons_manifest) || !dir.exists(lessons_dir)) {
      next
    }

    lessons_meta <- jsonlite::fromJSON(lessons_manifest)$lessons
    lessons_meta <- lessons_meta[order(lessons_meta$order), , drop = FALSE]
    lesson_files <- sort(list.files(lessons_dir, pattern = "\\.md$", full.names = TRUE))
    if (nrow(lessons_meta) != length(lesson_files)) {
      stop(sprintf("Lesson manifest/file count mismatch for %s", course_id))
    }

    for (j in seq_len(nrow(lessons_meta))) {
      lesson_source_id <- paste(course_id, lessons_meta$id[[j]], sep = "/")
      refs <- extract_library_refs(lesson_files[[j]])
      if (!length(refs)) {
        next
      }
      for (ref in refs) {
        links[[length(links) + 1L]] <- add_link(
          "course_lesson",
          lesson_source_id,
          "library_card",
          ref,
          "references"
        )
      }
    }
  }

  links_df <- do.call(rbind, links)
  unique(links_df)
}

sync_knowledge_links <- function(paths) {
  links_df <- build_knowledge_links(paths)
  replace_knowledge_links(paths, links_df)
  invisible(links_df)
}

get_idea_links <- function(paths) {
  db_table(paths, "SELECT idea_id_a, idea_id_b, link_label FROM idea_links")
}

meeting_choices <- function(paths) {
  meetings <- db_table(
    paths,
    "SELECT meeting_id, title, meeting_date FROM meetings ORDER BY created_at DESC"
  )
  if (!nrow(meetings)) {
    return(setNames(character(), character()))
  }
  stats::setNames(meetings$meeting_id, paste(meetings$meeting_date, meetings$title))
}

# ── v5: News synthesis helpers ─────────────────────────────────────────────

news_domain_summary <- function(paths, date_from = NULL, date_to = NULL) {
  where <- "1=1"
  if (!is.null(date_from)) where <- paste0(where, " AND brief_date >= '", date_from, "'")
  if (!is.null(date_to))   where <- paste0(where, " AND brief_date <= '", date_to, "'")
  db_table(paths, sprintf(
    "SELECT domain, signal_strength, COUNT(*) AS n FROM news_briefs WHERE %s GROUP BY domain, signal_strength ORDER BY domain",
    where
  ))
}

news_by_domain <- function(paths, domain, n = 5L) {
  db_table(paths, sprintf(
    "SELECT brief_id, brief_date, title, signal_strength, COALESCE(summary,'') AS summary, COALESCE(project_link,'') AS project_link, COALESCE(tags,'') AS tags, COALESCE(source_url,'') AS source_url FROM news_briefs WHERE domain = '%s' ORDER BY brief_date DESC, created_at DESC LIMIT %d",
    domain, as.integer(n)
  ))
}

news_surprise_items <- function(paths, n = 3L) {
  db_table(paths, sprintf(
    "SELECT * FROM news_briefs WHERE surprise_flag = 1 ORDER BY brief_date DESC LIMIT %d",
    as.integer(n)
  ))
}

news_top_signals <- function(paths, date = NULL, n = 5L) {
  d <- if (is.null(date)) format(Sys.Date()) else date
  db_table(paths, sprintf(
    "SELECT brief_id, brief_date, title, domain, signal_strength, COALESCE(summary,'') AS summary, COALESCE(project_link,'') AS project_link, COALESCE(tags,'') AS tags FROM news_briefs WHERE signal_strength = 'high' AND brief_date >= date('%s', '-7 days') ORDER BY brief_date DESC LIMIT %d",
    d, as.integer(n)
  ))
}

insert_news_brief_v5 <- function(paths, brief_date, title, domain, signal_strength,
                                  summary, project_link, source_url = "", tags = "",
                                  surprise_flag = 0L) {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  brief_id <- sprintf("%s-%s", brief_date, make_slug(title))
  DBI::dbExecute(
    con,
    paste(
      "INSERT OR REPLACE INTO news_briefs",
      "(brief_id, brief_date, title, domain, signal_strength, summary, project_link,",
      "source_url, tags, surprise_flag, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    ),
    params = list(brief_id, brief_date, title, domain, signal_strength, summary,
                  project_link, source_url, tags, as.integer(surprise_flag),
                  format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(brief_id)
}

# ── v5: Meeting intelligence helpers ───────────────────────────────────────

insert_meeting_person <- function(paths, name, role = "") {
  ensure_db_schema(paths)
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  person_id <- sprintf("person-%s", make_slug(name))
  DBI::dbExecute(
    con,
    "INSERT OR IGNORE INTO meeting_persons (person_id, name, role) VALUES (?, ?, ?)",
    params = list(person_id, name, role)
  )
  invisible(person_id)
}

get_meeting_persons <- function(paths) {
  db_table(paths, "SELECT * FROM meeting_persons ORDER BY name")
}

get_meeting_context <- function(paths, project = NULL, keywords = NULL) {
  sql <- paste(
    "SELECT m.meeting_id, m.title, m.meeting_date, m.domain, m.project,",
    "COALESCE(m.decisions,'') AS decisions, COALESCE(m.action_items,'') AS action_items",
    "FROM meetings m WHERE 1=1"
  )
  if (!is.null(project) && nzchar(project)) {
    sql <- paste0(sql, sprintf(" AND m.project = '%s'", project))
  }
  sql <- paste0(sql, " ORDER BY m.meeting_date DESC LIMIT 10")
  db_table(paths, sql)
}

update_meeting_intelligence <- function(paths, meeting_id, attendees = NULL,
                                         meeting_type = NULL, decisions = NULL,
                                         action_items = NULL, follow_ups = NULL) {
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  sets <- character()
  params <- list()
  if (!is.null(attendees)) { sets <- c(sets, "attendees = ?"); params <- c(params, list(attendees)) }
  if (!is.null(meeting_type)) { sets <- c(sets, "meeting_type = ?"); params <- c(params, list(meeting_type)) }
  if (!is.null(decisions)) { sets <- c(sets, "decisions = ?"); params <- c(params, list(decisions)) }
  if (!is.null(action_items)) { sets <- c(sets, "action_items = ?"); params <- c(params, list(action_items)) }
  if (!is.null(follow_ups)) { sets <- c(sets, "follow_ups = ?"); params <- c(params, list(follow_ups)) }
  if (!length(sets)) return(invisible(FALSE))
  params <- c(params, list(meeting_id))
  DBI::dbExecute(con, sprintf("UPDATE meetings SET %s WHERE meeting_id = ?", paste(sets, collapse = ", ")),
                 params = params)
  invisible(TRUE)
}

# ── v5: Learning helpers ──────────────────────────────────────────────────

seed_default_competencies <- function(paths) {
  # Delegates to seed_default_data() which now handles competencies + resources
  seed_default_data(paths)
  invisible(TRUE)
}

get_competencies <- function(paths, domain = NULL) {
  sql <- "SELECT * FROM learning_competencies"
  if (!is.null(domain)) sql <- paste0(sql, sprintf(" WHERE domain = '%s'", domain))
  sql <- paste0(sql, " ORDER BY topic")
  db_table(paths, sql)
}

insert_learning_activity <- function(paths, competency_id, activity_type, description) {
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  activity_id <- sprintf("act-%s", format(Sys.time(), "%Y%m%d%H%M%S%OS3"))
  now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  DBI::dbExecute(
    con,
    "INSERT INTO learning_activities (activity_id, competency_id, activity_type, description, completed_at) VALUES (?,?,?,?,?)",
    params = list(activity_id, competency_id, activity_type, description, now)
  )
  DBI::dbExecute(con, "UPDATE learning_competencies SET last_activity = ? WHERE competency_id = ?",
                 params = list(now, competency_id))
  # Auto-level based on activity count
  act_count <- DBI::dbGetQuery(con, sprintf(
    "SELECT COUNT(*) AS n FROM learning_activities WHERE competency_id = '%s'", competency_id
  ))$n[[1]]
  new_level <- if (act_count >= 15L) "advanced" else if (act_count >= 5L) "intermediate" else "beginner"
  DBI::dbExecute(con, "UPDATE learning_competencies SET level = ? WHERE competency_id = ?",
                 params = list(new_level, competency_id))
  invisible(activity_id)
}

get_learning_activities <- function(paths, competency_id, n = 10L) {
  db_table(paths, sprintf(
    "SELECT * FROM learning_activities WHERE competency_id = '%s' ORDER BY completed_at DESC LIMIT %d",
    competency_id, as.integer(n)
  ))
}

# ── v5: Finance helpers ───────────────────────────────────────────────────

insert_finance_snapshot <- function(paths, snapshot_date, category, label, headline,
                                     detail = "", trend = "stable", project_link = "") {
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  snapshot_id <- sprintf("fin-%s-%s", snapshot_date, make_slug(label))
  DBI::dbExecute(
    con,
    "INSERT OR REPLACE INTO finance_snapshots (snapshot_id, snapshot_date, category, label, headline, detail, trend, project_link, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
    params = list(snapshot_id, snapshot_date, category, label, headline, detail, trend,
                  project_link, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(snapshot_id)
}

get_finance_today <- function(paths) {
  db_table(paths, sprintf(
    "SELECT * FROM finance_snapshots WHERE snapshot_date = '%s' ORDER BY category, label",
    format(Sys.Date())
  ))
}

get_finance_trends <- function(paths, days = 30L) {
  db_table(paths, sprintf(
    "SELECT category, label, headline, trend, snapshot_date FROM finance_snapshots WHERE snapshot_date >= date('%s', '-%d days') ORDER BY snapshot_date DESC",
    format(Sys.Date()), as.integer(days)
  ))
}

insert_finance_watchlist <- function(paths, category, label, notes = "") {
  con <- connect_db(paths)
  on.exit(DBI::dbDisconnect(con), add = TRUE)
  item_id <- sprintf("watch-%s", make_slug(label))
  DBI::dbExecute(
    con,
    "INSERT OR IGNORE INTO finance_watchlist (item_id, category, label, notes, created_at) VALUES (?,?,?,?,?)",
    params = list(item_id, category, label, notes, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  )
  invisible(item_id)
}

get_finance_watchlist <- function(paths) {
  db_table(paths, "SELECT * FROM finance_watchlist ORDER BY category, label")
}
