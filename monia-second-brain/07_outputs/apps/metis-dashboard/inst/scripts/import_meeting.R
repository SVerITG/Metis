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
    "monia-second-brain/07_outputs/apps/metis-dashboard/inst/scripts"
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

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 5L) {
  log_job(paths, "import_meeting", "error", "Expected args: source_path title date domain project")
  stop("Expected args: source_path title date domain project", call. = FALSE)
}

source_path <- args[[1]]
title <- args[[2]]
meeting_date <- args[[3]]
domain <- args[[4]]
project <- args[[5]]

if (!file.exists(source_path)) {
  log_job(paths, "import_meeting", "error", sprintf("File not found: %s", source_path))
  stop(sprintf("File not found: %s", source_path), call. = FALSE)
}

audio_root <- ensure_dir(file.path(paths$meetings_root, "audio"))
structured_root <- ensure_dir(file.path(paths$meetings_root, "structured"))
template_path <- file.path(paths$meetings_root, "templates", "meeting-note-template.md")

slug <- gsub("[^A-Za-z0-9]+", "-", tolower(title))
slug <- gsub("(^-+|-+$)", "", slug)
if (!nzchar(slug)) {
  slug <- "meeting"
}

timestamp <- format(Sys.time(), "%Y%m%d-%H%M%S")
ext <- tools::file_ext(source_path)
meeting_id <- sprintf("%s-%s", meeting_date, slug)
audio_name <- sprintf("%s-%s.%s", timestamp, slug, ext)
stored_audio_path <- file.path(audio_root, audio_name)

ok <- file.copy(source_path, stored_audio_path, overwrite = FALSE)
if (!isTRUE(ok)) {
  log_job(paths, "import_meeting", "error", sprintf("Copy failed for %s", source_path))
  stop(sprintf("Copy failed for %s", source_path), call. = FALSE)
}

template_lines <- safe_read_lines(template_path, n = 200L)
if (!length(template_lines)) {
  template_lines <- c(
    "# Meeting Template",
    "",
    "## Metadata",
    "- Date:",
    "- Title:",
    "- Participants:",
    "- Domain:",
    "- Project:"
  )
}

replacements <- c(
  "- Date:" = sprintf("- Date: %s", meeting_date),
  "- Title:" = sprintf("- Title: %s", title),
  "- Domain:" = sprintf("- Domain: %s", domain),
  "- Project:" = sprintf("- Project: %s", project)
)

for (pattern in names(replacements)) {
  template_lines[template_lines == pattern] <- replacements[[pattern]]
}

structured_note_path <- file.path(structured_root, sprintf("%s.md", meeting_id))
writeLines(template_lines, structured_note_path, useBytes = TRUE)

con <- connect_db(paths)
on.exit(DBI::dbDisconnect(con), add = TRUE)

invisible(DBI::dbExecute(
  con,
  paste(
    "INSERT OR REPLACE INTO meetings",
    "(meeting_id, title, meeting_date, domain, project, source_filename, stored_audio_path, structured_note_path, created_at)",
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
  ),
  params = list(
    meeting_id,
    title,
    meeting_date,
    domain,
    project,
    basename(source_path),
    stored_audio_path,
    structured_note_path,
    format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  )
))

log_job(paths, "import_meeting", "success", sprintf("Imported %s", basename(source_path)))
cat(sprintf("Meeting imported: %s\n", meeting_id))
