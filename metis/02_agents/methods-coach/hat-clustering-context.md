# HAT Clustering — Methods Coach Context

**Invocation:** `/methods-coach <task title>`
**Project:** HAT Risk Mapping and Clustering
**Local path:** `C:\Users\sverschaeve\OneDrive - ITG\Documents\2. HAT disease\1. Epi Data\4. Clustering`

---

## Methods in use

### SaTScan (primary tool)
- Space-time scan statistics for HAT cluster detection
- Sub-projects: Basic, DRC_24-25, DRC_24-25_5%POP_90%SP, KC (Kwilu-Congo)
- `.prm` parameter files define: max cluster size, time periods, scan window, test type
- Output: cluster locations, p-values, relative risk estimates

### R pipeline (KC sub-project)
- `Database_script.R` — case/population data preparation
- `Risk_Mapping_Script_2025_KC.R` — main KC analysis
- Population denominator: `population_long` format (long-form by health zone × year)
- Case data: case counts by health zone × year

### Sensitivity analysis
- `DRC_24-25_5%POP_90%SP` — varying max cluster size (5% population) and spatial probability threshold (90%)
- Tests robustness of cluster detection to parameter assumptions

---

## Key methodological decisions to review

1. **Max cluster size choice** — what % of population is theoretically motivated for HAT?
2. **Space vs. space-time scan** — are we detecting persistent foci or emerging clusters?
3. **Population denominator** — is at-risk population or total population the right denominator?
4. **Time window** — what aggregation level (annual, multi-year) best captures HAT dynamics?
5. **Multiple testing** — with multiple sub-projects, is correction applied?

---

## Connections to other methods

- **Multilevel analysis**: can cluster membership be a level-2 unit in MLM for HAT risk factors?
- **Passive case-finding**: SaTScan clusters define priority zones for passive screening evaluation
- **Surveillance evaluation**: cluster persistence over time = surveillance sensitivity indicator

---

## Methods Coach tasks for this project

- **Review SaTScan parameter choices** — are the `.prm` files methodologically justified?
- **Assess sensitivity analysis** — does the 5%/90% variant change conclusions?
- **Connect clustering to passive screening** — what is the causal pathway from cluster → surveillance decision?
- **HPC feasibility** — is HPC needed for full DRC analysis or is it already running locally?

---

## Key references

- Kulldorff M (1997) — original SaTScan paper
- WHO HAT atlas — population and case denominators
- Spatial epidemiology textbooks (Elliott & Wartenberg; Lawson)
