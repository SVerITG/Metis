args <- commandArgs(trailingOnly = FALSE)
script_flag <- "--file="
script_hits <- args[grepl(script_flag, args)]

if (length(script_hits) && !is.na(script_hits[1L])) {
  script_path <- sub(script_flag, "", script_hits[1L])
  script_path <- gsub("~\\+~", " ", script_path)
  script_dir  <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))
  app_root    <- dirname(dirname(script_dir))
} else {
  # Interactive use: look for app root relative to working directory
  candidates <- c(
    ".",
    "07_outputs/apps/metis-dashboard",
    "07_outputs/apps/metis-dashboard"
  )
  app_root <- NULL
  for (cand in candidates) {
    if (file.exists(file.path(cand, "app.R"))) {
      app_root <- normalizePath(cand, winslash = "/", mustWork = TRUE)
      break
    }
  }
  if (is.null(app_root)) {
    stop("Cannot locate app root (app.R). Run from the dashboard directory or use Rscript.", call. = FALSE)
  }
}

r_files <- list.files(file.path(app_root, "R"), pattern = "\\.[Rr]$", full.names = TRUE)
invisible(lapply(r_files, source, local = FALSE))

paths <- metis_paths(app_root)
ensure_db_schema(paths)
