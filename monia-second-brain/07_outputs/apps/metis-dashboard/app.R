library(shiny)
library(bslib)

r_files <- list.files("R", pattern = "\\.[Rr]$", full.names = TRUE)
invisible(lapply(r_files, source, local = FALSE))

app_root <- normalizePath(".", winslash = "/", mustWork = TRUE)
paths    <- metis_paths(app_root)

ui <- page_navbar(
  title    = div(class = "metis-brand", "Metis"),
  id       = "main_nav",
  fillable = FALSE,
  theme    = metis_theme(),
  header   = tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "styles.css")
  ),
  nav_panel("Control Room", control_room_ui("control_room")),
  nav_panel("Library",      library_ui("library")),
  nav_panel("PhD",          phd_ui("phd")),
  nav_panel("Projects",     projects_ui("projects")),
  nav_panel("Meetings",     meetings_ui("meetings")),
  nav_panel("News",         news_ui("news")),
  nav_panel("Learning",     learning_ui("learning")),
  nav_panel("Ideas",        ideas_ui("ideas")),
  nav_panel("Crucible",     crucible_ui("crucible")),
  nav_menu(
    "More",
    nav_panel("Finance",    finance_ui("finance")),
    nav_panel("Talks",      talks_ui("talks")),
    nav_panel("Agents",     agents_ui("agents")),
    nav_panel("Search",     search_ui("search")),
    nav_panel("Graph",      graph_ui("graph"))
  )
)

server <- function(input, output, session) {
  ensure_db_schema(paths)
  seed_default_data(paths)
  sync_knowledge_links(paths)
  control_room_server("control_room", paths)
  library_server("library", paths)
  phd_server("phd", paths)
  projects_server("projects", paths)
  meetings_server("meetings", paths)
  news_server("news", paths)
  learning_server("learning", paths)
  ideas_server("ideas", paths)
  crucible_server("crucible", paths)
  finance_server("finance", paths)
  talks_server("talks", paths)
  search_server("search", paths)
  graph_server("graph", paths)
  agents_server("agents", paths)
}

shinyApp(ui, server)
