# seed_projects.R
# Run this once to add the three external research projects and their todos
# to the Metis SQLite database.
# Safe to re-run — uses INSERT OR IGNORE so existing records are not overwritten.

library(DBI)
library(RSQLite)

db_path <- file.path(normalizePath(getwd(), winslash = "/"), "data", "metis.sqlite")
con <- DBI::dbConnect(RSQLite::SQLite(), db_path)
on.exit(DBI::dbDisconnect(con), add = TRUE)

# ---- Add new columns if not yet present ----
cols <- DBI::dbGetQuery(con, "PRAGMA table_info(projects)")$name
if (!"external_path" %in% cols) {
  DBI::dbExecute(con, "ALTER TABLE projects ADD COLUMN external_path TEXT")
}
if (!"github_url" %in% cols) {
  DBI::dbExecute(con, "ALTER TABLE projects ADD COLUMN github_url TEXT")
}
if (!"launch_cmd" %in% cols) {
  DBI::dbExecute(con, "ALTER TABLE projects ADD COLUMN launch_cmd TEXT")
}

now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")

# ---- Projects ----
projects <- data.frame(
  project_id    = c("hat-dashboard", "hat-clustering", "multilevel-analysis"),
  title         = c("HAT Dashboard", "HAT Risk Mapping and Clustering", "Multilevel Analysis Course"),
  domain        = c("sleeping-sickness", "sleeping-sickness", "education"),
  status        = c("active", "active", "active"),
  priority      = c("high", "high", "medium"),
  next_step     = c(
    "Review reactive architecture and data processing scripts",
    "Review Risk_Mapping_Script_2025_KC.R for PhD article",
    "Check mlm-app status and connect spatial scan material"
  ),
  external_path = c(
    "C:\\Users\\sverschaeve\\OneDrive - ITG\\Documents\\2. HAT disease\\1. Epi Data\\7. Dashboard",
    "C:\\Users\\sverschaeve\\OneDrive - ITG\\Documents\\2. HAT disease\\1. Epi Data\\4. Clustering",
    "C:\\Users\\sverschaeve\\OneDrive - ITG\\Documents\\9. Education\\1. Multilevel Analysis"
  ),
  github_url    = c(
    "https://github.com/SVerITG/HAT_Dashboard_1.0",
    "pending",   # create on GitHub then update
    "https://github.com/SVerITG/MLM_course"
  ),
  launch_cmd    = c(
    NA_character_,
    NA_character_,
    "cd mlm-app && node server.js"
  ),
  created_at    = rep(now, 3),
  stringsAsFactors = FALSE
)

for (i in seq_len(nrow(projects))) {
  existing <- DBI::dbGetQuery(
    con,
    paste0("SELECT project_id FROM projects WHERE project_id = '", projects$project_id[i], "'")
  )
  if (nrow(existing) == 0) {
    DBI::dbAppendTable(con, "projects", projects[i, ])
    cat("Inserted project:", projects$title[i], "\n")
  } else {
    cat("Skipped (exists):", projects$title[i], "\n")
  }
}

# ---- Tasks ----
tasks <- data.frame(
  task_id    = c(
    "task-hatdash-reactive",
    "task-hatdash-github",
    "task-hatdash-paths",
    "task-hatdash-derived",
    "task-clustering-kc-review",
    "task-clustering-link-phd",
    "task-clustering-hpc-check",
    "task-mlm-app-check",
    "task-mlm-spatial-connect",
    "task-mlm-github"
  ),
  project_id = c(
    "hat-dashboard", "hat-dashboard", "hat-dashboard", "hat-dashboard",
    "hat-clustering", "hat-clustering", "hat-clustering",
    "multilevel-analysis", "multilevel-analysis", "multilevel-analysis"
  ),
  title = c(
    "Review reactive architecture in app.R and modules",
    "Initialize git and push to GitHub",
    "Check for hardcoded paths in all scripts",
    "Review 02d_derived_datasets.R performance",
    "Review Risk_Mapping_Script_2025_KC.R for PhD article",
    "Link clustering outputs to passive screening article",
    "Review HPC folder scripts and document workflow",
    "Check mlm-app Shiny app status",
    "Connect spatial scan statistics material",
    "Consider GitHub for course scripts"
  ),
  status   = rep("open", 10),
  due_date = rep("", 10),
  owner    = c(
    "Software Engineer", "Software Engineer", "Software Engineer", "Software Engineer",
    "Software Engineer", "PhD Architect", "Software Engineer",
    "Software Engineer", "Methods Coach", "Software Engineer"
  ),
  notes = c(
    "Check for business logic in UI layer and missing req()",
    "Github/ folder already exists with GIT_GUIDE.md",
    "Hardcoded paths break on other machines",
    "Likely the heaviest script — check for slow joins",
    "Main KC script for risk mapping — priority for elimination article",
    "Clustering results feed the passive case finding narrative",
    "HPC = high-performance computing scripts for SaTScan at scale",
    "migrate_db.js present — check if app needs database setup",
    "Spatial scan connects education and research",
    "Makes scripts citable and shareable"
  ),
  created_at = rep(now, 10),
  stringsAsFactors = FALSE
)

for (i in seq_len(nrow(tasks))) {
  existing <- DBI::dbGetQuery(
    con,
    paste0("SELECT task_id FROM tasks WHERE task_id = '", tasks$task_id[i], "'")
  )
  if (nrow(existing) == 0) {
    DBI::dbAppendTable(con, "tasks", tasks[i, ])
    cat("Inserted task:", tasks$title[i], "\n")
  } else {
    cat("Skipped (exists):", tasks$title[i], "\n")
  }
}

# ---- Additional tasks: missing agent × project coverage ----
# Added 2026-03-27: fills gaps identified in v4 agent audit

extra_tasks <- data.frame(
  task_id    = c(
    "task-hatdash-ui-audit",
    "task-hatdash-data-privacy",
    "task-clustering-satscan-params",
    "task-clustering-article-draft",
    "task-mlm-slides",
    "task-mlm-references",
    "task-passive-screening-phd-map"
  ),
  project_id = c(
    "hat-dashboard",
    "hat-dashboard",
    "hat-clustering",
    "hat-clustering",
    "multilevel-analysis",
    "multilevel-analysis",
    "passive-screening-drc"
  ),
  title = c(
    "Audit exploration tab layout and filter cascade UX",
    "Review data layer: ensure no individual records exposed in UI",
    "Review SaTScan parameter choices for KC spatial scan",
    "Draft clustering to passive screening narrative for PhD article",
    "Create teaching slide deck for multilevel analysis module",
    "Find key MLM textbook references for course bibliography",
    "Map passive screening article to thesis backbone"
  ),
  status   = rep("open", 7),
  due_date = rep("", 7),
  owner    = c(
    "Dashboard Engineer",
    "Software Engineer",
    "Methods Coach",
    "Writing Partner",
    "Presentation Maker",
    "Librarian",
    "PhD Architect"
  ),
  notes = c(
    "Context doc: 02_agents/dashboard-engineer/hat-dashboard-context.md",
    "Security rule: aggregate display only — no patient-level records. See 08_system/security/",
    "Context doc: 02_agents/methods-coach/hat-clustering-context.md. Check max cluster size, space-time vs space-only, population denominator",
    "Context doc: 02_agents/writing-partner/hat-clustering-context.md. Link KC cluster results to passive case-finding narrative",
    "Context doc: 02_agents/presentation-maker/multilevel-analysis-course-context.md. One slide deck per module",
    "Priority: MLM foundational texts (Snijders & Bosker, Rabe-Hesketh & Skrondal) + SaTScan original paper (Kulldorff 1997)",
    "Context doc: 02_agents/phd-architect/hat-clustering-context.md. Define which research question passive screening article answers"
  ),
  created_at = rep(now, 7),
  stringsAsFactors = FALSE
)

for (i in seq_len(nrow(extra_tasks))) {
  existing <- DBI::dbGetQuery(
    con,
    paste0("SELECT task_id FROM tasks WHERE task_id = '", extra_tasks$task_id[i], "'")
  )
  if (nrow(existing) == 0) {
    DBI::dbAppendTable(con, "tasks", extra_tasks[i, ])
    cat("Inserted task:", extra_tasks$title[i], "\n")
  } else {
    cat("Skipped (exists):", extra_tasks$title[i], "\n")
  }
}

# ---- Builder and News Radar coverage ----
reactive_agent_tasks <- data.frame(
  task_id    = c("task-builder-mcp-server", "task-newsradar-rss-setup"),
  project_id = c("metis-dashboard", "phd-framework"),
  title      = c(
    "Scaffold MCP server for Metis data automation",
    "Configure RSS feeds for HAT elimination and sleeping sickness monitoring"
  ),
  status   = rep("open", 2),
  due_date = rep("", 2),
  owner    = c("Builder", "News Radar"),
  notes = c(
    "Consider: local MCP server exposing metis.sqlite queries to Claude Code. See ruflo-reference for MCP patterns.",
    "Sources: WHO HAT updates, PLoS NTD, Lancet Infectious Diseases, relevant institutional feeds. Store in 07_outputs/news/"
  ),
  created_at = rep(now, 2),
  stringsAsFactors = FALSE
)

for (i in seq_len(nrow(reactive_agent_tasks))) {
  existing <- DBI::dbGetQuery(
    con,
    paste0("SELECT task_id FROM tasks WHERE task_id = '", reactive_agent_tasks$task_id[i], "'")
  )
  if (nrow(existing) == 0) {
    DBI::dbAppendTable(con, "tasks", reactive_agent_tasks[i, ])
    cat("Inserted task:", reactive_agent_tasks$title[i], "\n")
  } else {
    cat("Skipped (exists):", reactive_agent_tasks$title[i], "\n")
  }
}

cat("\nDone. Run the Metis dashboard to see updated projects and tasks.\n")
