# schedule_agents.R
# Registers Windows Task Scheduler jobs for Metis background agents.
# Run ONCE from RStudio or the dashboard folder.
#
# Problem: taskscheduleR breaks on paths with spaces (OneDrive path).
# Solution: creates small wrapper .bat files in C:\Metis\ (no spaces)
#           and schedules those instead.
#
# Run from the metis-dashboard folder: source("inst/scripts/schedule_agents.R")

app_root    <- normalizePath(getwd(), winslash = "\\")
scripts_dir <- file.path(app_root, "inst", "scripts")
rscript     <- normalizePath(file.path(R.home("bin"), "Rscript.exe"), winslash = "\\")

# Short launcher folder — no spaces, easy for Task Scheduler
launcher_dir <- "C:\\Metis"
if (!dir.exists(launcher_dir)) {
  dir.create(launcher_dir, recursive = TRUE)
  cat("Created launcher folder:", launcher_dir, "\n")
}

# ---- Write a wrapper .bat for each script ----
write_launcher <- function(bat_name, script_name, log_suffix) {
  script_full <- file.path(scripts_dir, script_name)
  log_file    <- file.path(launcher_dir, paste0(log_suffix, ".log"))
  bat_path    <- file.path(launcher_dir, bat_name)

  bat_lines <- c(
    "@echo off",
    sprintf("cd /d \"%s\"", app_root),
    sprintf("\"%s\" \"%s\" >> \"%s\" 2>&1", rscript, script_full, log_file)
  )
  writeLines(bat_lines, bat_path)
  cat(sprintf("  Wrote: %s\n", bat_path))
  bat_path
}

cat("Writing launcher .bat files to", launcher_dir, "...\n")
bat_news      <- write_launcher("metis_news.bat",      "fetch_news_feeds.R",   "news_radar")
bat_librarian <- write_launcher("metis_librarian.bat", "morning_librarian.R",  "librarian")

# ---- Register tasks via schtasks.exe directly ----
register_schtask <- function(task_name, bat_path, schedule_args) {
  # Remove existing task silently
  system2("schtasks", c("/Delete", "/TN", task_name, "/F"), stdout = FALSE, stderr = FALSE)

  args <- c(
    "/Create",
    "/TN", task_name,
    "/TR", sprintf('"%s"', bat_path),
    "/F",
    schedule_args
  )

  result <- system2("schtasks", args, stdout = TRUE, stderr = TRUE)
  status <- attr(result, "status")

  if (is.null(status) || status == 0L) {
    cat(sprintf("  OK: %s\n", task_name))
  } else {
    cat(sprintf("  FAILED: %s\n", task_name))
    cat(paste(result, collapse = "\n"), "\n")
  }
}

today <- format(Sys.Date(), "%d/%m/%Y")

cat("\nRegistering scheduled tasks...\n")

# News Radar — daily at 07:00
register_schtask(
  "Metis_NewsRadar",
  bat_news,
  c("/SC", "DAILY", "/ST", "07:00", "/SD", today)
)

# Librarian inbox scan — daily at 07:30
register_schtask(
  "Metis_LibrarianScan",
  bat_librarian,
  c("/SC", "DAILY", "/ST", "07:30", "/SD", today)
)

# ---- Verify ----
cat("\nVerifying registered tasks:\n")
all_raw <- system2("schtasks", c("/Query", "/FO", "CSV", "/NH"), stdout = TRUE, stderr = FALSE)
metis_tasks <- all_raw[grepl("Metis_", all_raw)]
if (length(metis_tasks)) {
  for (t in metis_tasks) cat(" ", t, "\n")
} else {
  cat("  No Metis tasks found — check errors above.\n")
}

cat("\n--- Done ---\n")
cat("Launcher .bat files: ", launcher_dir, "\n")
cat("Log files will appear in that folder after first run.\n")
cat("To view in Task Scheduler: Start menu > Task Scheduler > Task Scheduler Library\n")
cat("To test manually: run a .bat file from", launcher_dir, "directly\n")
