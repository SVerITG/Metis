# triage_inbox.R
# Scans 00_inbox/ for new files and prepends a Metis routing suggestion.
# Safe to re-run — already-routed files are skipped.
#
# Run: Rscript inst/scripts/triage_inbox.R

args_all   <- commandArgs(trailingOnly = FALSE)
flag       <- "--file="
script_arg <- args_all[grepl(flag, args_all)][1]
script_arg <- sub(flag, "", script_arg)
script_arg <- gsub("~\\+~", " ", script_arg)

source(file.path(
  dirname(normalizePath(script_arg, winslash = "/", mustWork = TRUE)),
  "common.R"
))

inbox_path <- file.path(paths$second_brain_root, "00_inbox")
log_path   <- file.path(paths$second_brain_root, "01_control-room", "triage-log.md")

# ---- Routing rules ------------------------------------------------
routing_rules <- list(
  list(
    keywords = c("paper", "article", "pubmed", "doi", "journal", "abstract",
                 "systematic review", "meta-analysis", "citation"),
    agent    = "Librarian",
    reason   = "Looks like a literature item — needs cataloguing and metadata."
  ),
  list(
    keywords = c("meeting", "transcript", "discussion", "call", "conference",
                 "agenda", "minutes"),
    agent    = "Meeting Memory",
    reason   = "Looks like a meeting artifact — needs structuring and briefing."
  ),
  list(
    keywords = c("phd", "thesis", "chapter", "elimination", "surveillance",
                 "post-elimination", "backbone"),
    agent    = "PhD Architect",
    reason   = "Relates to PhD structure or article alignment."
  ),
  list(
    keywords = c("script", "shiny", "code", "function", "error", "bug",
                 "debug", "library(", "ggplot", "dplyr", ".r"),
    agent    = "Software Engineer",
    reason   = "Contains code or a code-related question."
  ),
  list(
    keywords = c("write", "draft", "paragraph", "introduction", "discussion",
                 "abstract", "conclusion", "manuscript"),
    agent    = "Writing Partner",
    reason   = "Writing or drafting task."
  ),
  list(
    keywords = c("method", "sample", "statistic", "model", "regression",
                 "multilevel", "spatial", "satscan", "cluster", "bayesian"),
    agent    = "Methods Coach",
    reason   = "Methodological or statistical question."
  ),
  list(
    keywords = c("news", "geopolit", "financial", "market", "outbreak",
                 "pandemic", "brief", "what happened"),
    agent    = "News Radar",
    reason   = "External intelligence or news item."
  ),
  list(
    keywords = c("idea", "brainstorm", "think", "concept", "what if",
                 "could we", "explore", "curious"),
    agent    = "Metis",
    reason   = "Open idea — Metis will capture and route after reviewing."
  )
)

route_content <- function(content_lower) {
  best_agent  <- "Metis"
  best_reason <- "No clear match — Metis will triage manually."
  best_score  <- 0L

  for (rule in routing_rules) {
    score <- sum(vapply(
      rule$keywords,
      function(kw) grepl(kw, content_lower, fixed = TRUE),
      logical(1L)
    ))
    if (score > best_score) {
      best_score  <- score
      best_agent  <- rule$agent
      best_reason <- rule$reason
    }
  }
  list(agent = best_agent, reason = best_reason)
}

# ---- Scan inbox ---------------------------------------------------
if (!dir.exists(inbox_path)) {
  cat("Inbox not found:", inbox_path, "\n")
  quit(save = "no")
}

files <- list.files(inbox_path, pattern = "\\.(md|txt|R|r)$",
                    full.names = TRUE, recursive = FALSE)

if (!length(files)) {
  cat("Inbox is empty.\n")
  quit(save = "no")
}

routed  <- 0L
skipped <- 0L
log_entries <- character(0)

for (f in files) {
  lines <- tryCatch(readLines(f, warn = FALSE), error = function(...) character(0))
  if (!length(lines)) next

  if (grepl("<!-- MONIA ROUTED", lines[[1L]], fixed = TRUE)) {
    skipped <- skipped + 1L
    next
  }

  content       <- paste(lines, collapse = "\n")
  content_lower <- tolower(content)
  result        <- route_content(content_lower)
  timestamp     <- format(Sys.time(), "%Y-%m-%d %H:%M")

  routing_block <- c(
    sprintf("<!-- MONIA ROUTED: %s | Agent: %s | %s -->",
            timestamp, result$agent, result$reason),
    "",
    sprintf("**Routed to:** %s", result$agent),
    sprintf("**Reason:** %s", result$reason),
    sprintf("**Date:** %s", timestamp),
    "",
    "---",
    "",
    content
  )

  writeLines(routing_block, f)
  routed      <- routed + 1L
  log_entries <- c(
    log_entries,
    sprintf("- `%s` → **%s** — %s", basename(f), result$agent, result$reason)
  )
  cat(sprintf("Routed: %s → %s\n", basename(f), result$agent))
}

# ---- Append to triage log -----------------------------------------
if (length(log_entries)) {
  log_entry <- c(
    "",
    sprintf("## %s", format(Sys.time(), "%Y-%m-%d %H:%M")),
    log_entries
  )
  if (file.exists(log_path)) {
    existing <- readLines(log_path, warn = FALSE)
    writeLines(c(existing, log_entry), log_path)
  } else {
    writeLines(c("# Metis Triage Log", log_entry), log_path)
  }
}

cat(sprintf("\nDone. Routed: %d | Skipped (already routed): %d\n", routed, skipped))
