metis_paths <- function(app_root) {
  second_brain_root <- dirname(dirname(dirname(app_root)))

  list(
    app_root = app_root,
    second_brain_root = second_brain_root,
    data_root = file.path(app_root, "data"),
    scripts_root = file.path(app_root, "inst", "scripts"),
    literature_metadata = file.path(
      second_brain_root,
      "05_sources",
      "literature",
      "sleeping-sickness",
      "metadata"
    ),
    meetings_root = file.path(second_brain_root, "05_sources", "meetings"),
    phd_root = file.path(second_brain_root, "03_domains", "phd"),
    agents_root = file.path(second_brain_root, "02_agents")
  )
}

metis_theme <- function() {
  bs_theme(
    version = 5,
    bg = "#f4f1ea",
    fg = "#1f2a2e",
    primary = "#174c4f",
    secondary = "#6d7c74",
    success = "#2e6b4f",
    info = "#2d6073",
    warning = "#b36a1d",
    base_font = font_google("Source Sans 3"),
    heading_font = font_google("IBM Plex Serif"),
    code_font = font_google("JetBrains Mono")
  )
}

safe_count_files <- function(path, pattern = NULL) {
  if (!dir.exists(path)) {
    return(0L)
  }

  length(list.files(path, recursive = TRUE, full.names = TRUE, pattern = pattern))
}

safe_read_tsv <- function(path) {
  if (!file.exists(path)) {
    return(data.frame())
  }

  tryCatch(
    read.delim(path, sep = "\t", quote = "", stringsAsFactors = FALSE),
    error = function(...) data.frame()
  )
}

safe_read_lines <- function(path, n = 20L) {
  if (!file.exists(path)) {
    return(character())
  }

  tryCatch(readLines(path, n = n, warn = FALSE), error = function(...) character())
}

recent_files_df <- function(path, n = 5L) {
  if (!dir.exists(path)) {
    return(data.frame(name = character(), modified = character(), stringsAsFactors = FALSE))
  }

  files <- list.files(path, recursive = TRUE, full.names = TRUE)
  if (!length(files)) {
    return(data.frame(name = character(), modified = character(), stringsAsFactors = FALSE))
  }

  info <- file.info(files)
  info$path <- rownames(info)
  info <- info[order(info$mtime, decreasing = TRUE), , drop = FALSE]
  info <- head(info, n)

  data.frame(
    name = sub(paste0("^", normalizePath(path, winslash = "/", mustWork = FALSE), "/?"), "", info$path),
    modified = format(info$mtime, "%Y-%m-%d %H:%M"),
    stringsAsFactors = FALSE
  )
}

control_room_metrics <- function(paths) {
  inventory <- safe_read_tsv(file.path(paths$literature_metadata, "library-inventory.tsv"))
  seeded <- safe_read_tsv(file.path(paths$literature_metadata, "library-phd-seeded.tsv"))
  duplicates <- safe_read_tsv(file.path(paths$literature_metadata, "exact-duplicates.tsv"))

  list(
    library_items = nrow(inventory),
    phd_seeded = nrow(seeded),
    duplicate_groups = nrow(duplicates),
    meeting_artifacts = safe_count_files(paths$meetings_root),
    agent_specs = safe_count_files(paths$agents_root, pattern = "\\.md$"),
    phd_documents = safe_count_files(paths$phd_root)
  )
}

article_bucket_summary <- function(paths) {
  seeded <- safe_read_tsv(file.path(paths$literature_metadata, "library-phd-seeded.tsv"))
  if (!nrow(seeded) || !"phd_article_link" %in% names(seeded)) {
    return(data.frame(bucket = character(), count = integer(), stringsAsFactors = FALSE))
  }

  seeded <- seeded[seeded$phd_article_link != "" & seeded$phd_article_link != "to_triage", , drop = FALSE]
  if (!nrow(seeded)) {
    return(data.frame(bucket = character(), count = integer(), stringsAsFactors = FALSE))
  }

  counts <- sort(table(seeded$phd_article_link), decreasing = TRUE)
  data.frame(
    bucket = names(counts),
    count = as.integer(counts),
    stringsAsFactors = FALSE
  )
}

# ---------------------------------------------------------------------------
# Git status helpers
# ---------------------------------------------------------------------------

# Check git status for a single local project path.
# Returns a list: is_repo, uncommitted (int), unpushed (int), branch (chr), advice (chr)
git_project_status <- function(local_path) {
  empty <- list(
    is_repo = FALSE, uncommitted = 0L, unpushed = 0L,
    branch = NA_character_, advice = "Not a git repository"
  )

  if (is.na(local_path) || !nzchar(local_path) || local_path == "pending") {
    return(empty)
  }

  # Normalise Windows-style path for system calls
  path <- normalizePath(local_path, winslash = "/", mustWork = FALSE)

  git_ok <- function(...) {
    tryCatch(
      system2("git", c("-C", path, ...), stdout = TRUE, stderr = FALSE),
      error = function(...) NULL
    )
  }

  # Check it is actually a git repo
  top <- git_ok("rev-parse", "--show-toplevel")
  if (is.null(top) || !length(top)) return(empty)

  branch <- git_ok("rev-parse", "--abbrev-ref", "HEAD")
  branch <- if (length(branch)) branch[[1L]] else "unknown"

  # Uncommitted changes (porcelain = one line per changed file)
  porcelain <- git_ok("status", "--porcelain")
  uncommitted <- if (is.null(porcelain)) 0L else length(porcelain)

  # Unpushed commits (commits on HEAD not on remote tracking branch)
  ahead_raw <- git_ok("rev-list", "--count", paste0("@{u}..HEAD"))
  unpushed <- if (!is.null(ahead_raw) && length(ahead_raw) && !is.na(suppressWarnings(as.integer(ahead_raw[[1L]])))) {
    as.integer(ahead_raw[[1L]])
  } else {
    NA_integer_
  }

  # Build advice string
  advice <- character(0)
  if (uncommitted > 0L) {
    advice <- c(advice, sprintf("Commit %d changed file%s", uncommitted, if (uncommitted == 1L) "" else "s"))
  }
  if (!is.na(unpushed) && unpushed > 0L) {
    advice <- c(advice, sprintf("Push %d commit%s to GitHub", unpushed, if (unpushed == 1L) "" else "s"))
  }
  if (!length(advice)) {
    advice <- "Up to date"
  }

  list(
    is_repo    = TRUE,
    uncommitted = uncommitted,
    unpushed   = unpushed,
    branch     = branch,
    advice     = paste(advice, collapse = " · ")
  )
}

# Run git_project_status for all active projects stored in the DB.
# Returns a data.frame with one row per project.
git_all_projects_status <- function(paths) {
  projects <- tryCatch(
    db_table(
      paths,
      "SELECT project_id, title, external_path, github_url FROM projects WHERE status = 'active'"
    ),
    error = function(...) data.frame()
  )

  if (!nrow(projects)) {
    return(data.frame(
      project    = character(),
      branch     = character(),
      uncommitted = integer(),
      unpushed   = integer(),
      advice     = character(),
      stringsAsFactors = FALSE
    ))
  }

  rows <- lapply(seq_len(nrow(projects)), function(i) {
    s <- git_project_status(projects$external_path[[i]])
    data.frame(
      project     = projects$title[[i]],
      branch      = if (s$is_repo) s$branch else "—",
      uncommitted = if (s$is_repo) s$uncommitted else NA_integer_,
      unpushed    = if (s$is_repo && !is.na(s$unpushed)) s$unpushed else NA_integer_,
      advice      = s$advice,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

# ---------------------------------------------------------------------------
# Morning brief helpers
# ---------------------------------------------------------------------------

morning_greeting <- function() {
  h <- as.integer(format(Sys.time(), "%H"))
  if (h < 12L) "Good morning" else if (h < 17L) "Good afternoon" else "Good evening"
}

inbox_item_count <- function(paths) {
  inbox <- file.path(paths$second_brain_root, "00_inbox")
  if (!dir.exists(inbox)) return(0L)
  length(list.files(inbox, pattern = "\\.(md|txt|R)$", recursive = FALSE))
}

random_phd_paper <- function(paths) {
  seeded <- safe_read_tsv(file.path(paths$literature_metadata, "library-phd-seeded.tsv"))
  if (!nrow(seeded)) return(NULL)
  if (!all(c("basename", "phd_article_link") %in% names(seeded))) return(NULL)
  valid <- seeded[
    !is.na(seeded$phd_article_link) &
    nzchar(seeded$phd_article_link) &
    seeded$phd_article_link != "to_triage",
    , drop = FALSE
  ]
  if (!nrow(valid)) return(NULL)
  set.seed(as.integer(format(Sys.Date(), "%j")) + as.integer(format(Sys.Date(), "%Y")) * 365L)
  valid[sample(nrow(valid), 1L), , drop = FALSE]
}

# ---------------------------------------------------------------------------
# Project completion
# ---------------------------------------------------------------------------

project_completion <- function(paths) {
  projects <- tryCatch(
    db_table(paths, "SELECT project_id, title FROM projects WHERE status = 'active'"),
    error = function(...) data.frame()
  )
  if (!nrow(projects)) return(data.frame())

  all_tasks <- tryCatch(
    db_table(paths, "SELECT project_id, status FROM tasks"),
    error = function(...) data.frame()
  )

  rows <- lapply(seq_len(nrow(projects)), function(i) {
    pid    <- projects$project_id[i]
    ptasks <- if (nrow(all_tasks)) {
      all_tasks[all_tasks$project_id == pid, , drop = FALSE]
    } else {
      data.frame(status = character())
    }
    total <- nrow(ptasks)
    done  <- sum(ptasks$status == "done")
    pct   <- if (total > 0L) round(done / total * 100L) else 0L
    data.frame(
      project_id = pid, title = projects$title[i],
      total = total, done = done, pct = pct,
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, rows)
}

# ---------------------------------------------------------------------------
# Spaced repetition — SM-2 simplified
# ---------------------------------------------------------------------------

sm2_next_review <- function(current_interval, rating) {
  current_interval <- max(1L, as.integer(current_interval))
  switch(rating,
    hard  = max(1L, current_interval),
    good  = max(2L, round(current_interval * 1.5)),
    easy  = max(4L, current_interval * 2L),
    1L
  )
}

# ---------------------------------------------------------------------------
# Full-text search across SQLite + filesystem
# ---------------------------------------------------------------------------

search_all_sources <- function(paths, query, max_per = 10L) {
  q <- tolower(trimws(query))
  if (!nzchar(q)) return(list())

  results <- list()

  tables_cols <- list(
    tasks       = c("title", "notes"),
    projects    = c("title", "next_step"),
    news_briefs = c("title", "summary"),
    ideas       = c("text", "tags"),
    meetings    = c("title")
  )

  for (tbl in names(tables_cols)) {
    cols  <- tables_cols[[tbl]]
    where <- paste0(
      "LOWER(COALESCE(", cols, ",'')) LIKE '%", q, "%'",
      collapse = " OR "
    )
    sql  <- sprintf("SELECT * FROM %s WHERE %s LIMIT %d", tbl, where, as.integer(max_per))
    rows <- tryCatch(db_table(paths, sql), error = function(...) data.frame())
    if (nrow(rows)) results[[tbl]] <- rows
  }

  # Filesystem: phd + meetings markdown
  search_dirs <- c(paths$phd_root, paths$meetings_root)
  md_hits     <- character()

  for (d in search_dirs) {
    if (!dir.exists(d)) next
    files <- list.files(d, pattern = "\\.md$", recursive = TRUE, full.names = TRUE)
    for (f in head(files, 150L)) {
      lines <- tryCatch(readLines(f, warn = FALSE, n = 200L), error = function(...) character())
      if (length(lines) && any(grepl(q, tolower(lines), fixed = TRUE))) {
        md_hits <- c(md_hits, f)
        if (length(md_hits) >= max_per) break
      }
    }
    if (length(md_hits) >= max_per) break
  }

  if (length(md_hits)) {
    brain_root <- normalizePath(paths$second_brain_root, winslash = "/", mustWork = FALSE)
    results[["markdown"]] <- data.frame(
      path = sub(
        paste0("^", brain_root, "/?"), "",
        normalizePath(md_hits, winslash = "/", mustWork = FALSE)
      ),
      stringsAsFactors = FALSE
    )
  }

  results
}

ensure_dir <- function(path) {
  if (!dir.exists(path)) {
    dir.create(path, recursive = TRUE, showWarnings = FALSE)
  }

  path
}

db_path <- function(paths) {
  ensure_dir(paths$data_root)
  file.path(paths$data_root, "metis.sqlite")
}

connect_db <- function(paths) {
  DBI::dbConnect(RSQLite::SQLite(), dbname = db_path(paths))
}

run_script <- function(script, args = character(), paths) {
  script_path <- file.path(paths$scripts_root, script)
  if (!file.exists(script_path)) {
    stop(sprintf("Script not found: %s", script_path))
  }

  command_args <- c(script_path, args)
  result <- system2("Rscript", command_args, stdout = TRUE, stderr = TRUE)
  status <- attr(result, "status")
  if (is.null(status)) {
    status <- 0L
  }

  list(
    status = as.integer(status),
    output = paste(result, collapse = "\n")
  )
}
