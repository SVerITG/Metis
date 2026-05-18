args_all <- commandArgs(trailingOnly = FALSE)
script_hits <- args_all[grepl("^--file=", args_all)]

if (length(script_hits) && !is.na(script_hits[1L])) {
  script_path <- sub("^--file=", "", script_hits[1L])
  script_path <- gsub("~\\+~", " ", script_path)
  common_dir  <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))
} else {
  candidates <- c(
    "inst/scripts",
    "07_outputs/apps/metis-dashboard/inst/scripts",
    "07_outputs/apps/metis-dashboard/inst/scripts"
  )
  common_dir <- NULL
  for (cand in candidates) {
    if (file.exists(file.path(cand, "common.R"))) {
      common_dir <- normalizePath(cand, winslash = "/", mustWork = TRUE)
      break
    }
  }
  if (is.null(common_dir)) {
    stop("Cannot locate common.R. Run from the dashboard directory or use Rscript.", call. = FALSE)
  }
}
source(file.path(common_dir, "common.R"))

workflow_script <- file.path(
  paths$second_brain_root,
  "08_system",
  "workflows",
  "literature",
  "build_inventory.sh"
)

if (!file.exists(workflow_script)) {
  log_job(paths, "scan_library", "error", "build_inventory.sh not found")
  stop("build_inventory.sh not found", call. = FALSE)
}

result <- system2("bash", workflow_script, stdout = TRUE, stderr = TRUE)
status <- attr(result, "status")
if (is.null(status)) {
  status <- 0L
}

if (status != 0L) {
  details <- paste(result, collapse = "\n")
  log_job(paths, "scan_library", "error", details)
  stop(details, call. = FALSE)
}

refresh_db_from_files(paths)
log_job(paths, "scan_library", "success", "Library inventory rebuilt and database refreshed.")
cat("Library scan completed.\n")
