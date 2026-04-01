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
if (length(args) < 1L) {
  log_job(paths, "extract_meeting_structure", "error", "Expected args: meeting_id")
  stop("Expected args: meeting_id", call. = FALSE)
}

meeting_id <- args[[1]]
con <- connect_db(paths)
on.exit(DBI::dbDisconnect(con), add = TRUE)

meeting <- DBI::dbGetQuery(
  con,
  paste(
    "SELECT meeting_id, title, meeting_date, domain, project, structured_note_path, transcript_path",
    "FROM meetings WHERE meeting_id = ?"
  ),
  params = list(meeting_id)
)

if (!nrow(meeting)) {
  log_job(paths, "extract_meeting_structure", "error", sprintf("Meeting not found: %s", meeting_id))
  stop(sprintf("Meeting not found: %s", meeting_id), call. = FALSE)
}

if (!nzchar(meeting$transcript_path[[1]]) || !file.exists(meeting$transcript_path[[1]])) {
  log_job(paths, "extract_meeting_structure", "error", sprintf("Transcript missing for %s", meeting_id))
  stop(sprintf("Transcript missing for %s", meeting_id), call. = FALSE)
}

lines <- safe_read_lines(meeting$transcript_path[[1]], n = 5000L)
lines <- trimws(lines)
lines <- lines[nzchar(lines)]

if (!length(lines)) {
  lines <- c("Transcript file exists but contains no readable text.")
}

pick_lines <- function(pattern, fallback = character(), max_n = 5L, ignore_case = TRUE) {
  hits <- grep(pattern, lines, value = TRUE, ignore.case = ignore_case)
  hits <- unique(hits)
  if (!length(hits)) {
    hits <- fallback
  }
  head(hits, max_n)
}

summary_lines <- head(lines, 5L)
decision_lines <- pick_lines("\\b(decid|agree|approved|concluded|resolved)\\b", fallback = "No explicit decision sentence detected.")
action_lines <- pick_lines("\\b(action|todo|follow up|next step|need to|will|should)\\b", fallback = "No explicit action sentence detected.")
question_lines <- pick_lines("\\?|\\b(unclear|question|uncertainty|unknown)\\b", fallback = "No unresolved question detected.")
risk_lines <- pick_lines("\\b(risk|concern|problem|issue|constraint|delay)\\b", fallback = "No explicit risk statement detected.")

all_words <- unlist(strsplit(tolower(paste(lines, collapse = " ")), "[^a-z0-9]+"))
all_words <- all_words[nchar(all_words) >= 5]
stop_words <- c("about", "after", "again", "there", "their", "these", "those", "which", "would", "could", "should", "meeting", "title", "project", "audio", "transcript", "because", "where", "while", "needs", "using")
all_words <- all_words[!all_words %in% stop_words]
topics <- sort(table(all_words), decreasing = TRUE)
topic_lines <- if (length(topics)) {
  sprintf("- %s", names(head(topics, 8L)))
} else {
  "- topic extraction unavailable"
}

structured_lines <- c(
  "# Meeting Record",
  "",
  "## Metadata",
  sprintf("- Date: %s", meeting$meeting_date[[1]]),
  sprintf("- Title: %s", meeting$title[[1]]),
  "- Participants:",
  sprintf("- Domain: %s", meeting$domain[[1]]),
  sprintf("- Project: %s", meeting$project[[1]]),
  "- Related article:",
  "- Source quality: transcript-derived",
  "- Confidence: low",
  "",
  "## Summary",
  sprintf("- %s", summary_lines),
  "",
  "## Decisions",
  sprintf("- %s", decision_lines),
  "",
  "## Action Items",
  sprintf("- %s", action_lines),
  "",
  "## Owners and Deadlines",
  "- Owners and deadlines need review.",
  "",
  "## Unresolved Questions",
  sprintf("- %s", question_lines),
  "",
  "## Risks / Concerns",
  sprintf("- %s", risk_lines),
  "",
  "## Topics Mentioned",
  topic_lines,
  "",
  "## Next Meeting Preparation",
  "- Review extracted actions and unresolved questions before the next meeting."
)

writeLines(structured_lines, meeting$structured_note_path[[1]], useBytes = TRUE)

briefings_root <- ensure_dir(file.path(paths$meetings_root, "briefings"))
briefing_path <- file.path(briefings_root, sprintf("%s-briefing.md", meeting_id))
briefing_lines <- c(
  sprintf("# Briefing for %s", meeting$title[[1]]),
  "",
  "## Last meeting summary",
  sprintf("- %s", summary_lines),
  "",
  "## Outstanding actions",
  sprintf("- %s", action_lines),
  "",
  "## Unresolved issues",
  sprintf("- %s", question_lines),
  "",
  "## What to discuss next",
  "- Confirm actions, assign owners, and validate the extracted decisions."
)
writeLines(briefing_lines, briefing_path, useBytes = TRUE)

log_job(paths, "extract_meeting_structure", "success", sprintf("Structured note updated for %s", meeting_id))
cat(sprintf("Structured meeting outputs updated for %s\n", meeting_id))
