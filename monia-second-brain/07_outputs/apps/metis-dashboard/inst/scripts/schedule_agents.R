# schedule_agents.R
# Registers Windows Task Scheduler jobs for Monia background agents.
# Run ONCE from RStudio. After this, tasks run automatically.
#
# Problem: taskscheduleR breaks on paths with spaces (OneDrive path).
# Solution: creates small wrapper .bat files in C:\Monia\ (no spaces)
#           and schedules those instead.
#
# Run from the metis-dashboard folder: source("inst/scripts/schedule_agents.R")

app_root    <- normalizePath(getwd(), winslash = "\\")
scripts_dir <- file.path(app_root, "inst", "scripts")
rscript     <- normalizePath(file.path(R.home("bin"), "Rscript.exe"), winslash = "\\")

# Short launcher folder — no spaces, easy for Task Scheduler
launcher_dir <- "C:\\Monia"
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
bat_news    <- write_launcher("monia_news.bat",    "fetch_news_feeds.R", "news_radar")
bat_library <- write_launcher("monia_library.bat", "scan_library.R",     "library_scan")
bat_triage  <- write_launcher("monia_triage.bat",  "triage_inbox.R",     "inbox_triage")

# ---- Register tasks via schtasks.exe directly ----
# This avoids taskscheduleR's path-with-spaces bug.
register_schtask <- function(task_name, bat_path, schedule_args) {
  # Remove existing task silently
  system2("schtasks", c("/Delete", "/TN", task_name, "/F"), stdout = FALSE, stderr = FALSE)

  args <- c(
    "/Create",
    "/TN", task_name,
    "/TR", sprintf('"%s"', bat_path),
    "/F",   # force overwrite
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

# News Radar — daily at 06:30
register_schtask(
  "Monia_NewsRadar",
  bat_news,
  c("/SC", "DAILY", "/ST", "06:30", "/SD", today)
)

# Library scan — weekly on Monday at 07:00
register_schtask(
  "Monia_LibraryScan",
  bat_library,
  c("/SC", "WEEKLY", "/D", "MON", "/ST", "07:00", "/SD", today)
)

# Inbox triage — every 2 hours (multiple daily tasks)
for (t in c("08:00", "10:00", "12:00", "14:00", "16:00", "18:00")) {
  task_name <- paste0("Monia_InboxTriage_", gsub(":", "", t))
  register_schtask(
    task_name,
    bat_triage,
    c("/SC", "DAILY", "/ST", t, "/SD", today)
  )
}

# ---- Verify ----
cat("\nVerifying registered tasks:\n")
all_raw <- system2("schtasks", c("/Query", "/FO", "CSV", "/NH"), stdout = TRUE, stderr = FALSE)
monia_tasks <- all_raw[grepl("Monia_", all_raw)]
if (length(monia_tasks)) {
  for (t in monia_tasks) cat(" ", t, "\n")
} else {
  cat("  No Monia tasks found — check errors above.\n")
}

cat("\n--- Done ---\n")
cat("Launcher .bat files: ", launcher_dir, "\n")
cat("Log files will appear in that folder after first run.\n")
cat("To view in Task Scheduler: Start menu > Task Scheduler > Task Scheduler Library\n")
cat("To test manually: run a .bat file from", launcher_dir, "directly\n")
