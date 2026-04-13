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

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  log_job(paths, "transcribe_meeting", "error", "Expected args: meeting_id [transcript_path]")
  stop("Expected args: meeting_id [transcript_path]", call. = FALSE)
}

meeting_id <- args[[1]]
transcript_source <- if (length(args) >= 2L) args[[2]] else ""

con <- connect_db(paths)
on.exit(DBI::dbDisconnect(con), add = TRUE)
meeting <- DBI::dbGetQuery(
  con,
  "SELECT meeting_id, title, stored_audio_path FROM meetings WHERE meeting_id = ?",
  params = list(meeting_id)
)

if (!nrow(meeting)) {
  log_job(paths, "transcribe_meeting", "error", sprintf("Meeting not found: %s", meeting_id))
  stop(sprintf("Meeting not found: %s", meeting_id), call. = FALSE)
}

transcripts_root <- ensure_dir(file.path(paths$meetings_root, "transcripts"))
transcript_path <- file.path(transcripts_root, sprintf("%s.txt", meeting_id))

if (nzchar(transcript_source) && file.exists(transcript_source)) {
  ok <- file.copy(transcript_source, transcript_path, overwrite = TRUE)
  if (!isTRUE(ok)) {
    log_job(paths, "transcribe_meeting", "error", sprintf("Transcript copy failed for %s", meeting_id))
    stop("Transcript copy failed", call. = FALSE)
  }
  status <- "imported"
  details <- sprintf("Transcript file imported for %s", meeting_id)
} else {
  venv_python <- file.path(paths$app_root, ".venv", "bin", "python")
  whisper_cli <- file.path(paths$app_root, ".venv", "bin", "whisper")

  if (file.exists(whisper_cli) && file.exists(venv_python)) {
    whisper_out_dir <- ensure_dir(transcripts_root)
    out <- system2(
      whisper_cli,
      c(
        meeting$stored_audio_path[[1]],
        "--model", "base",
        "--task", "transcribe",
        "--output_dir", whisper_out_dir,
        "--output_format", "txt"
      ),
      stdout = TRUE,
      stderr = TRUE
    )
    command_status <- attr(out, "status")
    if (is.null(command_status)) {
      command_status <- 0L
    }

    generated_txt <- file.path(whisper_out_dir, sprintf("%s.txt", tools::file_path_sans_ext(basename(meeting$stored_audio_path[[1]]))))
    if (command_status == 0L && file.exists(generated_txt)) {
      file.copy(generated_txt, transcript_path, overwrite = TRUE)
      status <- "transcribed_raw"
      details <- sprintf("Whisper transcription completed for %s", meeting_id)
    } else {
      writeLines(
        c(
          sprintf("Meeting: %s", meeting$title[[1]]),
          "",
          "Automatic transcription was attempted but failed.",
          paste(out, collapse = "\n")
        ),
        transcript_path,
        useBytes = TRUE
      )
      status <- "transcription_failed"
      details <- sprintf("Whisper failed for %s", meeting_id)
    }
  } else {
    details <- "No local Whisper installation detected. Install whisper or import a transcript file."
    writeLines(
      c(
        sprintf("Meeting: %s", meeting$title[[1]]),
        "",
        "Automatic transcription requested but no local engine is installed.",
        "Install a local Whisper setup or upload a transcript text file from the dashboard."
      ),
      transcript_path,
      useBytes = TRUE
    )
    status <- "pending_whisper_install"
  }
}

invisible(DBI::dbExecute(
  con,
  "UPDATE meetings SET transcript_path = ?, transcript_status = ? WHERE meeting_id = ?",
  params = list(transcript_path, status, meeting_id)
))

log_job(paths, "transcribe_meeting", "success", details)
if (status %in% c("imported", "transcribed_raw")) {
  invisible(system2("Rscript", c(file.path(paths$scripts_root, "extract_meeting_structure.R"), meeting_id), stdout = TRUE, stderr = TRUE))
}
cat(sprintf("Transcript workflow completed for %s (%s)\n", meeting_id, status))
