---
project_id: hat-dashboard
title: HAT Dashboard
domain: sleeping-sickness
status: active
priority: high
external_path: C:\Users\sverschaeve\OneDrive - ITG\Documents\2. HAT disease\1. Epi Data\7. Dashboard
github_url: https://github.com/SVerITG/HAT_Dashboard_1.0
branch_active: server
---

# HAT Dashboard

R Shiny dashboard for HAT (Human African Trypanosomiasis) epidemiological data analysis and visualization. Built via vibecoding with Claude/Gemini. Actively developed.

## What it does
- Loads and cleans HAT surveillance data from the DRC
- Provides interactive visualizations: maps, time series, tables
- Statistics and epidemiological analysis tools
- Multi-module structure (data cleaning, loading, processing, derived datasets)

## Current structure
```
00_config.R         — configuration and paths
01_packages.R       — package loading
02a_data_cleaning.R — raw data cleaning
02b_data_loading.R  — data ingestion
02c_data_processing.R — transformations
02d_derived_datasets.R — computed indicators
03_css_styles.R     — UI styling
04_helpers.R        — utility functions
app.R               — main Shiny app
```

## Open todos
- [ ] Review `02c_data_processing.R` for performance (large dataset handling)
- [ ] Add GitHub version control (Github/ folder exists but may not be initialized)
- [ ] Review reactive architecture for correctness
- [ ] Add unit tests for key indicator calculations
- [ ] Standardize path handling (check for hardcoded paths)
- [ ] Review 02d_derived_datasets.R — likely most complex script

## Notes
- Already has CLAUDE.md, AGENTS.md, GEMINI.md — actively AI-assisted
- Has a `Github/` folder with `GIT_GUIDE.md` — needs git init + push
- `Dashboard_main_clean_2026-03-06` and `Dashboard_main_reset_2026-03-06` are snapshot backups
- Has a `Data-assistant` subfolder (separate project?)
