args_all <- commandArgs(trailingOnly = FALSE)
script_hits <- args_all[grepl("^--file=", args_all)]

if (length(script_hits) && !is.na(script_hits[1L])) {
  script_path <- sub("^--file=", "", script_hits[1L])
  script_path <- gsub("~\\+~", " ", script_path)
  common_dir  <- dirname(normalizePath(script_path, winslash = "/", mustWork = TRUE))
} else {
  # Interactive use: try known relative paths to inst/scripts/
  candidates <- c(
    "inst/scripts",
    "07_outputs/apps/metis-dashboard/inst/scripts",
    "metis/07_outputs/apps/metis-dashboard/inst/scripts"
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

# ── Feed structure ────────────────────────────────────────────────────────────
# Tier 1 — World context:      General awareness of global events (domain: "world")
# Tier 2 — Research & science:  Professional landscape — journals, science, AI (domains vary)
# Tier 3 — Epi intelligence:    Outbreak alerts, surveillance, field epi (domain: "epi-intel")
# Plus:    Markets feeds kept for the Finance tab (domain: "markets")
# ──────────────────────────────────────────────────────────────────────────────

feeds <- list(

  # Tier 1 — World context ─────────────────────────────────────────────────────
  list(
    domain = "world",
    project_link = "",
    url = "https://feeds.bbci.co.uk/news/world/rss.xml"
  ),
  list(
    domain = "world",
    project_link = "",
    url = "https://www.theguardian.com/world/rss"
  ),
  list(
    domain = "world",
    project_link = "",
    url = "https://www.aljazeera.com/xml/rss/all.xml"
  ),
  list(
    domain = "world",
    project_link = "",
    url = "https://www.standaard.be/rss/section/1f2838d4-99ea-49f0-9102-138784c7ea7c"
  ),
  list(
    domain = "world",
    project_link = "",
    url = "https://feeds.npr.org/1001/rss.xml"
  ),
  list(
    domain = "world",
    project_link = "",
    url = "https://rss.dw.com/xml/rss-en-all"
  ),

  # Tier 2 — Research & science ────────────────────────────────────────────────
  list(
    domain = "science",
    project_link = "phd-framework",
    url = "https://www.nature.com/nature.rss"
  ),
  list(
    domain = "science",
    project_link = "phd-framework",
    url = "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=science"
  ),
  list(
    domain = "medical",
    project_link = "phd-framework",
    url = "https://www.thelancet.com/rssfeed/lancet_current.xml"
  ),
  list(
    domain = "medical",
    project_link = "phd-framework",
    url = "https://www.bmj.com/rss/recent"
  ),
  list(
    domain = "ntds",
    project_link = "phd-framework",
    url = "https://journals.plos.org/plosntds/feed/atom"
  ),
  list(
    domain = "epi",
    project_link = "phd-framework",
    url = "https://www.eurosurveillance.org/content/feed"
  ),
  list(
    domain = "ai",
    project_link = "metis-dashboard",
    url = "https://www.technologyreview.com/feed/"
  ),
  # Add your own PubMed RSS search here.
  # Generate a search URL at: https://pubmed.ncbi.nlm.nih.gov/ → search → Create RSS
  # list(
  #   domain = "your-research-topic",
  #   project_link = "phd-framework",
  #   url = "https://pubmed.ncbi.nlm.nih.gov/rss/search/YOUR_SEARCH_ID/?limit=10"
  # ),
  list(
    domain = "ai",
    project_link = "metis-dashboard",
    url = "https://www.anthropic.com/rss.xml"
  ),

  # Tier 3 — Epi intelligence ─────────────────────────────────────────────────
  list(
    domain = "epi-intel",
    project_link = "phd-framework",
    url = "https://www.who.int/feeds/entity/don/en/rss.xml"
  ),
  list(
    domain = "epi-intel",
    project_link = "phd-framework",
    url = "https://www.who.int/feeds/entity/trypanosomiasis_african/en/rss.xml"
  ),
  list(
    domain = "epi-intel",
    project_link = "",
    url = "https://tools.cdc.gov/api/v2/resources/media/403372.rss"
  ),
  list(
    domain = "epi-intel",
    project_link = "",
    url = "https://reliefweb.int/updates/rss.xml"
  ),
  list(
    domain = "epi-intel",
    project_link = "phd-framework",
    url = "https://dndi.org/feed/"
  ),
  list(
    domain = "epi-intel",
    project_link = "",
    url = "https://www.msf.org/rss/all"
  ),

  # Markets (kept for Finance tab) ────────────────────────────────────────────
  list(
    domain = "markets",
    project_link = "",
    url = "https://www.cnbc.com/id/100003114/device/rss/rss.html"
  ),
  list(
    domain = "markets",
    project_link = "",
    url = "https://feeds.bloomberg.com/markets/news.rss"
  )
)

fetch_feed <- function(url) {
  out <- system2("curl", c("-L", "-A", "MetisNewsRadar/1.0", url), stdout = TRUE, stderr = TRUE)
  status <- attr(out, "status")
  if (!is.null(status) && status != 0L) {
    stop(paste(out, collapse = "\n"), call. = FALSE)
  }
  paste(out, collapse = "\n")
}

extract_entries <- function(doc, domain, project_link) {
  items <- xml2::xml_find_all(doc, ".//item")
  if (!length(items)) {
    items <- xml2::xml_find_all(doc, ".//entry")
  }

  if (!length(items)) {
    return(data.frame())
  }

  take_text <- function(node, xpath) {
    hit <- xml2::xml_find_first(node, xpath)
    if (inherits(hit, "xml_missing")) {
      return("")
    }
    trimws(xml2::xml_text(hit))
  }

  rows <- lapply(items, function(node) {
    title <- take_text(node, ".//title")
    summary <- take_text(node, ".//description|.//summary")
    date <- take_text(node, ".//pubDate|.//updated|.//published")
    if (!nzchar(date)) {
      date <- format(Sys.Date())
    }
    data.frame(
      brief_date = substr(date, 1, 10),
      title = title,
      domain = domain,
      signal_strength = "medium",
      summary = substr(summary, 1, 400),
      project_link = project_link,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}

stored <- 0L
for (feed in feeds) {
  xml_text <- tryCatch(fetch_feed(feed$url), error = function(e) "")
  if (!nzchar(xml_text)) {
    next
  }

  doc <- tryCatch(xml2::read_xml(xml_text), error = function(e) NULL)
  if (is.null(doc)) {
    next
  }

  entries <- extract_entries(doc, feed$domain, feed$project_link)
  if (!nrow(entries)) {
    next
  }

  for (i in seq_len(min(nrow(entries), 5L))) {
    insert_news_brief(
      paths,
      entries$brief_date[[i]],
      entries$title[[i]],
      entries$domain[[i]],
      entries$signal_strength[[i]],
      entries$summary[[i]],
      entries$project_link[[i]]
    )
    stored <- stored + 1L
  }
}

log_job(paths, "fetch_news_feeds", "success", sprintf("Stored %s brief items", stored))
log_agent_run(paths, "news-radar", sprintf("Morning fetch: stored %d news items", stored), model = "automation")
cat(sprintf("Fetched and stored %s news items\n", stored))
