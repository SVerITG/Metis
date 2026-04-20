# mod_knowledge.R
# Knowledge tab — wrapper combining Library, Research, and News as nested sub-modules.

knowledge_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(
      class = "page-intro",
      h1("Knowledge"),
      p("Literature library, research articles, and news — all in one place.")
    ),
    navset_card_tab(
      id = ns("knowledge_tabs"),
      nav_panel("Library",  library_ui(ns("library"))),
      nav_panel("Research", research_ui(ns("research"))),
      nav_panel("News",     news_ui(ns("news")))
    )
  )
}

knowledge_server <- function(id, paths) {
  moduleServer(id, function(input, output, session) {
    library_server("library",   paths)
    research_server("research", paths)
    news_server("news",         paths)
  })
}
