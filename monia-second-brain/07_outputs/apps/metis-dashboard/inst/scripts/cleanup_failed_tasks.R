# cleanup_failed_tasks.R
# Removes the broken Monia tasks registered by the previous schedule_agents.R run.
# Run once, then re-run schedule_agents.R.

broken <- c(
  "Monia_NewsRadar",
  "Monia_LibraryScan",
  "Monia_InboxTriage_0800",
  "Monia_InboxTriage_1000",
  "Monia_InboxTriage_1200",
  "Monia_InboxTriage_1400",
  "Monia_InboxTriage_1600",
  "Monia_InboxTriage_1800"
)

for (task in broken) {
  result <- system2("schtasks", c("/Delete", "/TN", task, "/F"),
                    stdout = TRUE, stderr = TRUE)
  status <- attr(result, "status")
  if (is.null(status) || status == 0L) {
    cat("Deleted:", task, "\n")
  } else {
    cat("Not found (OK):", task, "\n")
  }
}

cat("\nDone. Now re-run: source('inst/scripts/schedule_agents.R')\n")
