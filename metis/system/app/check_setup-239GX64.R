# check_setup.R
# Run this FIRST before launching the dashboard.
# It checks all required packages and configuration.
# Run from RStudio: source("check_setup.R")

cat("=== Metis Dashboard Setup Check ===\n\n")

ok <- TRUE

# ---- 1. Required packages ----
required <- c(
  "shiny", "bslib", "plotly", "shinyBS",
  "DBI", "RSQLite", "visNetwork",
  "xml2", "jsonlite", "httr", "rvest", "lubridate"
)

cat("1. Package check:\n")
for (pkg in required) {
  installed <- requireNamespace(pkg, quietly = TRUE)
  status    <- if (installed) "OK" else "MISSING"
  cat(sprintf("   %-20s %s\n", pkg, status))
  if (!installed) ok <- FALSE
}

if (!ok) {
  cat("\n   Installing missing packages...\n")
  missing_pkgs <- required[!vapply(required, requireNamespace, logical(1L), quietly = TRUE)]
  install.packages(missing_pkgs, repos = "https://cloud.r-project.org")
  cat("   Done. Re-run check_setup.R to verify.\n\n")
  ok <- TRUE  # reset to continue checks
}

# ---- 2. app.R exists ----
cat("\n2. App files:\n")
# Uses getwd() — make sure your working directory is the metis-dashboard folder.
# In RStudio: Session > Set Working Directory > To Source File Location
app_root <- normalizePath(getwd(), winslash = "/")

key_files <- c("app.R", "R/data_store.R", "R/helpers.R",
               "R/mod_control_room.R", "inst/scripts/common.R",
               "data/metis.sqlite", "www/styles.css")

for (f in key_files) {
  full <- file.path(app_root, f)
  status <- if (file.exists(full)) "OK" else "MISSING"
  cat(sprintf("   %-35s %s\n", f, status))
  if (status == "MISSING" && f != "data/metis.sqlite") ok <- FALSE
}

if (!file.exists(file.path(app_root, "data", "metis.sqlite"))) {
  cat("   (metis.sqlite will be created on first launch — OK)\n")
}

# ---- 3. Second brain root ----
cat("\n3. Second brain folder:\n")
second_brain <- normalizePath(
  file.path(app_root, "..", "..", ".."),  # app is at 07_outputs/apps/metis-dashboard
  winslash = "/", mustWork = FALSE
)
# Verify we landed in the right place (should contain the metis folder structure)
if (!dir.exists(file.path(second_brain, "02_agents"))) {
  cat(sprintf("   WARNING: 02_agents not found under: %s\n", second_brain))
  cat("   Make sure getwd() is set to the metis-dashboard folder.\n")
}
cat(sprintf("   Root: %s\n", second_brain))
expected_dirs <- c("00_inbox", "01_control-room", "02_agents",
                   "03_domains", "04_projects", "05_sources")
for (d in expected_dirs) {
  full <- file.path(second_brain, d)
  status <- if (dir.exists(full)) "OK" else "MISSING"
  cat(sprintf("   %-25s %s\n", d, status))
  if (status == "MISSING") ok <- FALSE
}

# ---- 4. Git availability ----
cat("\n4. Git:\n")
git_version <- tryCatch(
  system2("git", "--version", stdout = TRUE, stderr = FALSE),
  error = function(...) NULL
)
if (!is.null(git_version) && length(git_version)) {
  cat(sprintf("   %s\n", git_version[[1L]]))
} else {
  cat("   WARNING: git not found in PATH. GitHub status panel will show blanks.\n")
  cat("   Install Git for Windows from https://git-scm.com/\n")
}

# ---- 5. R version ----
cat("\n5. R version:\n")
cat(sprintf("   %s\n", R.version.string))
if (getRversion() < "4.1.0") {
  cat("   WARNING: R < 4.1.0 detected. Please update R.\n")
  ok <- FALSE
}

# ---- 6. R file syntax check ----
cat("\n6. R file syntax check:\n")
r_files <- list.files(file.path(app_root, "R"), pattern = "\\.[Rr]$", full.names = TRUE)
for (f in r_files) {
  result <- tryCatch({ parse(f); NULL }, error = function(e) e$message)
  if (!is.null(result)) {
    cat(sprintf("   [SYNTAX ERROR] %s:\n     %s\n", basename(f), result))
    ok <- FALSE
  } else {
    cat(sprintf("   [OK] %s\n", basename(f)))
  }
}

# ---- Summary ----
cat("\n===================================\n")
if (ok) {
  cat("All checks passed. You can launch the dashboard:\n\n")
  cat("  Option A (RStudio):  shiny::runApp()\n")
  cat("  Option B (browser):  double-click launch_metis.bat\n")
  cat("  Dashboard URL: http://localhost:3939\n\n")
} else {
  cat("Some checks failed. Fix the issues above and re-run check_setup.R.\n")
}
cat("===================================\n")
