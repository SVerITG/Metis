# seed_projects.R
# Example seeder — run once to add sample research projects and tasks to the
# Metis SQLite database.  Edit the data frames below to match your own projects.
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
# Replace these with your own projects.
projects <- data.frame(
  project_id    = c("research-project-1", "research-project-2", "learning-course-1"),
  title         = c("Research Project A", "Research Project B", "Statistics Course"),
  domain        = c("research", "research", "education"),
  status        = c("active", "active", "active"),
  priority      = c("high", "high", "medium"),
  next_step     = c(
    "Review data processing pipeline",
    "Complete analysis and draft findings",
    "Finish module 3 and move to module 4"
  ),
  external_path = c(
    "C:\\Users\\YourName\\Documents\\research-project-a",
    "C:\\Users\\YourName\\Documents\\research-project-b",
    "C:\\Users\\YourName\\Documents\\statistics-course"
  ),
  github_url    = c(
    "https://github.com/yourusername/research-project-a",
    "pending",
    "https://github.com/yourusername/statistics-course"
  ),
  launch_cmd    = c(
    NA_character_,
    NA_character_,
    NA_character_
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
    "task-proj1-data-review",
    "task-proj1-github",
    "task-proj1-paths",
    "task-proj2-analysis",
    "task-proj2-draft",
    "task-course-module3",
    "task-course-references"
  ),
  project_id = c(
    "research-project-1", "research-project-1", "research-project-1",
    "research-project-2", "research-project-2",
    "learning-course-1", "learning-course-1"
  ),
  title = c(
    "Review data processing scripts",
    "Initialize git and push to GitHub",
    "Check for hardcoded paths in scripts",
    "Complete main analysis",
    "Draft findings section",
    "Complete module 3",
    "Compile course bibliography"
  ),
  status   = rep("open", 7),
  due_date = rep("", 7),
  owner    = c(
    "Software Engineer", "Software Engineer", "Software Engineer",
    "Software Engineer", "Writing Partner",
    "Software Engineer", "Librarian"
  ),
  notes = c(
    "Check for business logic mixed into UI layer",
    "Set up remote and push main branch",
    "Hardcoded paths break on other machines — use relative paths",
    "Run full analysis pipeline and review outputs",
    "Structure around key findings from the analysis",
    "Write exercises and further reading for module 3",
    "Gather foundational textbook references"
  ),
  created_at = rep(now, 7),
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

# ---- Builder and News Radar coverage ----
reactive_agent_tasks <- data.frame(
  task_id    = c("task-builder-mcp-server", "task-newsradar-rss-setup"),
  project_id = c("metis-dashboard", "research-project-1"),
  title      = c(
    "Scaffold MCP server for Metis data automation",
    "Configure RSS feeds for your research domain"
  ),
  status   = rep("open", 2),
  due_date = rep("", 2),
  owner    = c("Builder", "News Radar"),
  notes = c(
    "Local MCP server exposing metis.sqlite queries to Claude Code.",
    "Add relevant journal and institution feeds. Store output in outputs/news/"
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
