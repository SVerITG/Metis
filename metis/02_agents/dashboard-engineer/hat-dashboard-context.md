# HAT Dashboard — Dashboard Engineer Context

**Invocation:** `/dashboard-engineer <task title>`
**Project:** HAT Dashboard
**Repo:** `SVerITG/HAT_Dashboard_1.0` · branch `server`
**Local path:** `C:\Users\sverschaeve\OneDrive - ITG\Documents\2. HAT disease\1. Epi Data\7. Dashboard`

---

## What this dashboard does

R Shiny app for HAT (Human African Trypanosomiasis) epidemiological data from the DRC. Primary users: the researcher and potentially institutional collaborators. Displays surveillance data, interactive maps, time series, and epidemiological statistics.

---

## Current architecture

```
00_config.R           — configuration and paths
01_packages.R         — package loading
02a_data_cleaning.R   — raw data cleaning
02b_data_loading.R    — data ingestion
02c_data_processing.R — transformations
02d_derived_datasets.R — computed indicators
03_css_styles.R       — UI styling (custom CSS)
04_helpers.R          — utility functions
app.R                 — main Shiny app entry
server_overview.R     — overview tab server logic
server_agent.R        — AI agent tab (connects to RAG service)
ui_exploration.R      — exploration tab UI (14+ reactive filters)
Data-assistant/       — Python RAG service (separate)
```

---

## UI/UX priorities

- **Exploration tab** (`ui_exploration.R`): Most complex UI — 14+ cascading filters. Needs review for:
  - Filter cascade order (geography → time → indicator)
  - UI feedback when no data matches filter combination
  - Mobile/tablet responsiveness (currently desktop-focused)

- **Overview tab**: Summary statistics and KPIs — keep clean, scannable

- **Agent tab** (`server_agent.R`): AI chat interface — needs clear input/output visual separation

---

## Dashboard Engineer tasks for this project

- **Audit exploration tab layout** — are 14 filters overwhelming? Can some be collapsed or grouped?
- **Review reactive filter cascade** — are dependent filters updating in the right order?
- **CSS consistency** (`03_css_styles.R`) — is the style coherent with the data complexity?
- **No-data state handling** — are empty states clearly communicated to the user?

---

## Key design constraints

- Single researcher, desktop-primary use
- R Shiny (not a web framework): no React, no custom JS beyond Shiny events
- HAT data has geographic (health zones, provinces), temporal, and case-type dimensions
- Patient-level records must NEVER be displayed individually — aggregate only

---

## Coordination

- **Software Engineer**: handles code correctness and performance
- **Methods Coach**: handles indicator definitions and statistical logic
- **Dashboard Engineer**: owns UI architecture and visual decisions
