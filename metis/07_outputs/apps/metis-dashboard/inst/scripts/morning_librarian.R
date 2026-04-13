# morning_librarian.R
# Metis morning Librarian agent — runs daily at 07:30 via Task Scheduler.
#
# What it does:
#   1. Scans 00_inbox/ for new PDF, DOCX, MD, TXT files
#   2. Registers each new file in dropzone_intake table (status = 'pending')
#   3. Logs a summary to agent_runs (slug: 'librarian')
#   4. Writes a Claude Code prompt file for manual AI tagging
#
# Auto-tagging by AI requires running the resulting prompt file in Claude Code.

args_all <- commandArgs(trailingOnly = FALSE)
script_hits <- args_all[grepl("^--file=", args_all)]

if (length(script_hits) && !is.na(script_hits[1L])) {
  script_path <- sub("^--file=", "", script_hits[1L])
  script_path <- gsub("~\\+~", " ", script_path)
  common_dir  <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))
} else {
  candidates <- c(
    "inst/scripts",
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
    stop("Cannot locate common.R. Run from the dashboard directory.", call. = FALSE)
  }
}
source(file.path(common_dir, "common.R"))

# ── Scan inbox ──────────────────────────────────────────────────────────────
inbox_path <- file.path(paths$second_brain_root, "00_inbox")

if (!dir.exists(inbox_path)) {
  log_job(paths, "morning_librarian", "skip", "00_inbox/ not found")
  log_agent_run(paths, "librarian", "Morning scan: inbox not found", model = "automation")
  cat("00_inbox/ not found — skipping.\n")
  quit(save = "no", status = 0L)
}

# File types to process
inbox_files <- list.files(
  inbox_path,
  pattern    = "\\.(pdf|docx|md|txt|csv|xlsx|pptx|Rmd)$",
  recursive  = FALSE,
  full.names = TRUE,
  ignore.case = TRUE
)

if (!length(inbox_files)) {
  log_job(paths, "morning_librarian", "success", "Inbox empty — nothing to process")
  log_agent_run(paths, "librarian", "Morning scan: inbox empty", model = "automation")
  cat("Inbox is empty — nothing to process.\n")
  quit(save = "no", status = 0L)
}

# ── Check which files are already tracked ───────────────────────────────────
already_tracked <- tryCatch(
  db_table(paths, "SELECT stored_path FROM dropzone_intake")$stored_path,
  error = function(...) character()
)

new_files <- inbox_files[!normalizePath(inbox_files, winslash = "/") %in%
                           normalizePath(already_tracked, winslash = "/")]

if (!length(new_files)) {
  log_job(paths, "morning_librarian", "success", "All inbox files already tracked")
  log_agent_run(paths, "librarian", "Morning scan: all files already tracked", model = "automation")
  cat("All inbox files are already tracked.\n")
  quit(save = "no", status = 0L)
}

# ── Register new files in dropzone_intake ───────────────────────────────────
con <- connect_db(paths)
on.exit(DBI::dbDisconnect(con), add = TRUE)

now <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
registered <- 0L

for (fp in new_files) {
  intake_id <- sprintf("intake-%s-%04d", format(Sys.time(), "%Y%m%d%H%M%S"), registered + 1L)
  fname     <- basename(fp)
  ext       <- tolower(tools::file_ext(fname))
  ftype     <- switch(ext,
    pdf   = "paper",
    docx  = "document",
    md    = "note",
    txt   = "note",
    csv   = "data",
    xlsx  = "data",
    pptx  = "presentation",
    Rmd   = "script",
    "other"
  )

  tryCatch({
    DBI::dbExecute(con, paste(
      "INSERT OR IGNORE INTO dropzone_intake",
      "(intake_id, filename, stored_path, file_type, status, created_at)",
      "VALUES (?,?,?,?,?,?)"
    ), params = list(
      intake_id, fname, normalizePath(fp, winslash = "/"),
      ftype, "pending", now
    ))
    registered <- registered + 1L
    cat(sprintf("  Queued: %s (%s)\n", fname, ftype))
  }, error = function(e) {
    cat(sprintf("  Error queuing %s: %s\n", fname, conditionMessage(e)))
  })
}

# ── Generate Claude Code tagging prompt ─────────────────────────────────────
if (registered > 0L) {
  prompt_dir  <- file.path(paths$second_brain_root, "07_outputs", "reviews", "librarian")
  if (!dir.exists(prompt_dir)) dir.create(prompt_dir, recursive = TRUE, showWarnings = FALSE)

  prompt_file <- file.path(prompt_dir, sprintf("%s_inbox-tagging-prompt.md", format(Sys.Date())))
  file_list   <- paste(
    sprintf("- `%s`", basename(new_files)),
    collapse = "\n"
  )

  prompt_lines <- c(
    sprintf("# Librarian inbox tagging — %s", format(Sys.Date())),
    "",
    "Run `/librarian` with this prompt in Claude Code:",
    "",
    "```",
    sprintf("/librarian Tag these %d new files from 00_inbox/:", registered),
    file_list,
    "",
    "For each file:",
    "1. Identify entity_type (paper/report/protocol/dataset/note)",
    "2. Tag disease relevance (sleeping sickness, HAT, general NTD, other)",
    "3. Tag geography if relevant",
    "4. Tag method if relevant",
    "5. Suggest phd_article_link bucket (chapter-1, chapter-2, chapter-3, methods, background, to_triage)",
    "6. Update dropzone_intake status to 'tagged' once done",
    "7. Move papers to 05_sources/literature/ and notes to 05_sources/notes/",
    "```"
  )
  writeLines(prompt_lines, prompt_file)
  cat(sprintf("  Prompt written: %s\n", prompt_file))
}

# ── Log ─────────────────────────────────────────────────────────────────────
summary_msg <- sprintf("Queued %d new inbox files for tagging", registered)
log_job(paths, "morning_librarian", "success", summary_msg)
log_agent_run(paths, "librarian", summary_msg, model = "automation")

cat(sprintf("\nDone. %s.\n", summary_msg))
if (registered > 0L) {
  cat(sprintf("Open Claude Code and run the tagging prompt at:\n  07_outputs/reviews/librarian/%s_inbox-tagging-prompt.md\n",
              format(Sys.Date())))
}
