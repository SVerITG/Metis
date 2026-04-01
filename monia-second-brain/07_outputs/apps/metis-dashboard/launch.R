# launch.R — Start the Metis dashboard without opening RStudio
# Usage: Rscript launch.R
# Or double-click launch_monia.bat

# Detect the folder this script lives in
args_all   <- commandArgs(trailingOnly = FALSE)
flag       <- args_all[grepl("^--file=", args_all)]
if (length(flag)) {
  app_dir <- dirname(normalizePath(sub("^--file=", "", flag[1]), winslash = "/"))
} else {
  app_dir <- normalizePath(getwd(), winslash = "/")
}

# Sanity check
if (!file.exists(file.path(app_dir, "app.R"))) {
  stop("app.R not found in: ", app_dir, "\nPlease run from the metis-dashboard folder.")
}

setwd(app_dir)

cat("===========================================\n")
cat("  Metis Dashboard\n")
cat("===========================================\n")
cat("  Folder:", app_dir, "\n")
cat("  URL:    http://localhost:3838\n")
cat("  Close this window to stop the dashboard.\n")
cat("===========================================\n\n")

shiny::runApp(".", port = 3838, launch.browser = TRUE)
