library(shiny)
library(bslib)
library(plotly)
library(shinyBS)

r_files <- list.files("R", pattern = "\\.[Rr]$", full.names = TRUE)
invisible(lapply(r_files, source, local = FALSE))

app_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
paths    <- metis_paths(app_root)

# ── Global Ctrl+K / Cmd+K quick-capture listener ────────────────────────────
ctrlk_js <- tags$script(HTML(
  "document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      Shiny.setInputValue('global_capture', Date.now(), {priority: 'event'});
    }
  });"
))

ui <- page_navbar(
  title    = div(class = "metis-brand", "Metis"),
  id       = "main_nav",
  fillable = FALSE,
  theme    = metis_theme(),
  header   = tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css"),
    ctrlk_js
  ),
  nav_panel("Today",     today_ui("today")),
  nav_panel("Knowledge", knowledge_ui("knowledge")),
  nav_panel("Thinking",  thinking_ui("thinking")),
  nav_panel("Planner",   planning_ui("planning")),
  nav_panel("Work",      work_ui("work")),
  nav_panel("Meetings",  meetings_ui("meetings")),
  nav_panel("Learning",  learning_ui("learning")),
  nav_panel("Metis",     metis_tab_ui("metis")),
  # ── Always-visible quick-capture button ──
  nav_item(
    tags$button(
      class   = "btn btn-capture-nav",
      title   = "Quick capture (Ctrl+K)",
      onclick = "Shiny.setInputValue('global_capture', Date.now(), {priority:'event'})",
      tagList(icon("plus"), tags$span(class = "capture-nav-label", " Capture"))
    )
  ),
  nav_spacer(),
  nav_item(
    div(class = "trust-badge",
      icon("shield-halved"),
      tags$span(class = "trust-badge-text", "Local-first")
    )
  ),
  # Quick-capture module (no persistent UI — modal only)
  nav_item(quick_capture_ui("capture"))
)

server <- function(input, output, session) {
  ensure_db_schema(paths)
  seed_default_data(paths)
  sync_knowledge_links(paths)

  # ── Live-reload when DB is updated externally (e.g. by Metis via MCP) ──────
  db_watcher <- reactivePoll(
    intervalMillis = 20000,
    session        = session,
    checkFunc      = function() {
      if (file.exists(paths$db)) as.numeric(file.mtime(paths$db)) else 0
    },
    valueFunc      = function() Sys.time()
  )
  observeEvent(db_watcher(), {
    showNotification(
      ui       = tagList("Metis updated the database. ",
                         actionLink("reload_link", "Reload now")),
      type     = "message",
      duration = NULL,
      id       = "db_updated_notif"
    )
  })
  observeEvent(input$reload_link, session$reload())
  # ─────────────────────────────────────────────────────────────────────────

  # ── Tab servers ───────────────────────────────────────────────────────────
  today_server("today", paths)
  knowledge_server("knowledge", paths)
  thinking_server("thinking", paths, parent_session = session)
  planning_server("planning", paths)
  work_server("work", paths)
  meetings_server("meetings", paths)
  learning_server("learning", paths)
  metis_tab_server("metis", paths)

  # ── Global quick-capture (Ctrl+K + nav button) ────────────────────────────
  quick_capture_server("capture", paths, open_trigger = reactive(input$global_capture))
}

shinyApp(ui, server)
