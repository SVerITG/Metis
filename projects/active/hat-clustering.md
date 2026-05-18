---
project_id: hat-clustering
title: HAT Risk Mapping and Clustering
domain: sleeping-sickness
status: active
priority: high
external_path: C:\Users\sverschaeve\OneDrive - ITG\Documents\2. HAT disease\1. Epi Data\4. Clustering
github_url: pending
---

# HAT Risk Mapping and Clustering

Spatial clustering and risk mapping analysis for HAT using SaTScan. Multiple sub-projects covering different geographic areas and time periods in the DRC.

## What it does
- Prepares case and population data for SaTScan (space-time cluster detection)
- Runs spatial scan statistics for HAT hotspot identification
- Produces risk maps for Kwilu-Congo (KC) and broader DRC areas
- Feeds into the passive case finding / post-elimination surveillance narrative

## Sub-projects
- **Basic** — baseline SaTScan setup and test
- **DRC_24-25** — DRC-wide 2024-2025 analysis
- **DRC_24-25_5%POP_90%SP** — sensitivity analysis variant
- **KC (Kwilu-Congo)** — risk mapping analysis with full data pipeline (analysis_data, case_counts, population_long)

## Key R scripts
- `1. Data/Script/Database_script.R` — data preparation
- `2. Projects/Basic/Basic.R` — basic SaTScan run
- `2. Projects/KC/Risk_Mapping_Script_2025_KC.R` — main KC analysis

## Open todos
- [ ] Review `Risk_Mapping_Script_2025_KC.R` — priority for PhD article
- [ ] Document the data preparation pipeline in Database_script.R
- [ ] Add 3. SaTScan and 4. HPC output review
- [ ] Link clustering outputs to passive screening article
- [ ] Consider version control for scripts

## Notes
- SaTScan `.prm` files define scan parameters (max cluster size, time periods)
- KC project has the richest pipeline (rds data files, tables, graphs, maps, satscan results)
- HPC folder likely contains high-performance computing scripts — check
- Directly relevant to PhD backbone (post-elimination surveillance)
