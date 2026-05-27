# Spatial Epidemiology Upskilling Programme
## NTD Field Epidemiologists — 6-Month Programme

**Audience:** 8 NTD field epidemiologists | Basic R | No spatial analysis experience  
**Duration:** 26 weeks | 1 session/week (2–3 h) + practicals  
**Designed:** 2026-05-26 | Learning Architect

---

## What this programme builds

By the end of 6 months, each participant can independently:
- Wrangle spatial epidemiological data in R (`sf`, `spdep`, `spatialreg`)
- Produce publication-quality and field-ready maps
- Apply spatial statistics to identify NTD clusters
- Fit and interpret spatial regression models
- Translate spatial evidence into programme recommendations

---

## File index

| File | Contents |
|------|----------|
| `competency-map.md` | 25 competencies across 5 domains A–E, with Bloom levels and prerequisite DAG |
| `module-sequence.md` | 26 modules across 4 phases; session plans; spaced repetition schedule |
| `assessment-checkpoints.md` | 4 assessed checkpoints + 8 embedded quizzes + certificate criteria |
| `course.json` | Machine-readable course metadata |

---

## Programme structure at a glance

| Phase | Weeks | Domains | Assessment |
|-------|-------|---------|-----------|
| 1 — Spatial Data Foundations | 1–5 | A (data), B (visualisation) | Checkpoint 1 |
| 2 — Descriptive Spatial Statistics | 6–12 | C (Moran, LISA, KDE, scan) | Checkpoint 2 |
| 3 — Spatial Regression | 13–18 | D (lag, error, Poisson, GWR) | Checkpoint 3 |
| 4 — NTD Applications + Capstone | 19–26 | E (risk maps, MDA monitoring, equity) | Capstone |

---

## Key design decisions

**Backward design:** All 25 competencies defined before any content was sequenced. No module was designed without knowing what it contributes to the exit standard.

**NTD-grounded throughout:** Every module uses NTD examples (HAT, LF, onchocerciasis). Participants always apply methods to their own programme data, not toy datasets.

**Spaced repetition enforced structurally:** Each concept is actively reviewed at +1 day, +3 days, +1 week, +2 weeks, and +1 month. The master table in module-sequence.md shows which reviews are active every week.

**No competency below Apply:** All 25 learning outcomes are at Bloom Apply level or higher. Understand-only outcomes appear only as prerequisites for higher-level work.

**Failure is recoverable:** Every checkpoint has a defined remediation pathway. Participants who struggle get targeted support before progressing, not a failing grade.

---

## R packages required

```r
install.packages(c(
  "sf", "ggplot2", "spdep", "spatialreg", "gstat",
  "spatstat", "GWmodel", "leaflet", "tmap", "SpatialEpi"
))
# INLA via:
install.packages("INLA", repos = c(getOption("repos"), INLA = "https://inla.r-inla-download.org/R/stable"))
```

---

## Facilitator notes

- Pre-programme: run a 1-hour R baseline assessment to confirm entry-level skills. Participants who cannot produce a basic `ggplot2` histogram need a 2-week R refresher before Week 1.
- Weeks 1–5 move fast. Invest in data-wrangling foundations — the entire programme depends on A2/A3.
- The capstone should use real programme data wherever possible. Prepare a fallback synthetic dataset matching the endemic disease profile in case data governance issues arise.
- Consider inviting a programme manager to the Week 26 presentations — this raises stakes, improves communication quality, and embeds spatial analysis into the programme's normal workflow.
