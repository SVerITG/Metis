# mod_thinking.R
# Thinking tab — wrapper combining Notes and Ideas as nested sub-modules.

thinking_ui <- function(id) {
  ns <- NS(id)

  tagList(
    div(
      class = "page-intro",
      h1("Thinking"),
      p("Notes, ideas, and brainstorm sessions.")
    ),
    navset_card_tab(
      id = ns("thinking_tabs"),
      nav_panel("Notes", notes_ui(ns("notes"))),
      nav_panel("Ideas", ideas_ui(ns("ideas")))
    )
  )
}

thinking_server <- function(id, paths, parent_session = NULL) {
  moduleServer(id, function(input, output, session) {
    notes_server("notes", paths, parent_session = parent_session)
    ideas_server("ideas", paths)
  })
}
