---
name: New Project
description: "new project, scaffold project, create project, set up project, build a dashboard, create a shiny app, start a new analysis, create a project for, I want to visualize, set up a project, new shiny, new R script, new tool"
model: claude-sonnet-4-6
effort: normal
complexity: standard
---

## Purpose

Scaffolds a new project in the Metis RC system from any starting point (idea, data file, conversation, task). Works from Claude Code and Claude Desktop.

## What to do when invoked

**Step 1 — Gather information** (ask all at once, not sequentially):
- Project name (will be slugified)
- Type: `shiny` / `script` / `report` / `tool`
- Domain / research link (e.g., "sleeping sickness", "phd-framework", "general")
- Data source path (optional — can be added later)

**Step 2 — Create project card:**
Write `04_projects/active/[slug].md` with this frontmatter:

```yaml
---
title: [Project Name]
slug: [slug]
type: [shiny|script|report|tool]
status: active
domain: [domain]
priority: medium
created: [YYYY-MM-DD]
data_paths: []
launchers: []
github: ""
next_step: "[suggested first action]"
---
```

Followed by a brief `## Context` section (1-2 sentences from the user's description).

**Step 3 — Scaffold files:**

For **Shiny app** (`type: shiny`):
```
07_outputs/apps/[slug]/
  app.R               ← minimal page_navbar skeleton
  R/
    helpers.R         ← metis_paths() copy + theme
  data/               ← empty, gitignored
  www/
    styles.css        ← link to metis styles
  launch.R            ← shinyApp(launch.browser=TRUE, port=3839)
```

For **R script** (`type: script`):
```
05_sources/code/[slug]/
  main.R              ← boilerplate with common.R source
  README.md           ← purpose, inputs, outputs, run instructions
```

For **report** (`type: report`):
```
07_outputs/reports/[slug]/
  [slug].Rmd          ← RMarkdown skeleton with YAML header
  data/               ← empty
```

For **tool** (`type: tool`):
```
05_sources/code/[slug]/
  main.py or main.R   ← based on description
  README.md
```

**Step 4 — Register in Metis DB:**
```r
# Run in R (or suggest user runs):
con <- DBI::dbConnect(RSQLite::SQLite(), "07_outputs/apps/metis-dashboard/data/metis.sqlite")
DBI::dbExecute(con, "INSERT OR IGNORE INTO projects (project_id, title, domain, status, priority, next_step, created_at) VALUES (?,?,?,?,?,?,?)",
  params = list(slug, title, domain, "active", "medium", next_step, format(Sys.time(), "%Y-%m-%d %H:%M:%S")))
DBI::dbDisconnect(con)
```

**Step 5 — Log and return project card:**
Log to `agent_runs` as `new-project`.

Always end with this project card summary:
```
─────────────────────────────────────
Project:   [name]
Type:      [type]
Location:  [path]
Data:      [data path or "none"]
Open with: Rscript [path]/launch.R
Next step: [suggested first action]
─────────────────────────────────────
```

## Edge cases
- User gives a vague name: suggest a slug, confirm before creating files.
- Type is unclear: ask one clarifying question.
- Path already exists: show existing structure, ask to overwrite or use different name.
- No data source: scaffold without data/ population, note it in next_step.
- Shiny app requested with port conflict: suggest port 3840 or 3841 as alternatives.
