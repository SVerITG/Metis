# Module Sequence with Spaced Repetition
## Spatial Epidemiology Upskilling Programme — NTD Field Epidemiologists

**Duration:** 6 months (26 weeks)  
**Cadence:** 1 core session/week (2–3 hours) + spaced review tasks  
**Format:** Team workshop + individual R practicals (apply immediately to own NTD data)  
**Spaced repetition schedule per concept:** +1 day → +3 days → +1 week → +2 weeks → +1 month

---

## Phase 1 — Spatial Data Foundations (Weeks 1–5)

### Module 1 | Week 1 — Spatial Thinking for Epidemiologists
**Competencies:** A1, A5  
**Bloom level:** Understand → Evaluate  

**Session (3 h):**
- Conceptual lecture: vector vs raster; CRS basics; projection distortion
- Demo: load a GADM shapefile for your endemic country in R
- Group task: evaluate 3 candidate shapefiles from OCHA/HDX — which is fit for purpose?

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Reproduce the demo shapefile load; annotate each line |
| Day 4 (+3) | Find and document the official health-zone boundary file for your programme country |
| Week 2 start (+1 wk) | Mini-quiz: 5 CRS/projection questions embedded in Module 2 warm-up |

---

### Module 2 | Week 2 — Wrangling Spatial Data in R
**Competencies:** A2, A3  
**Bloom level:** Apply  
**Prerequisites met:** A1  

**Session (2.5 h):**
- `sf` package: read, transform CRS, `st_transform()`
- Joining prevalence data to district polygons: `left_join()` + `st_as_sf()`
- Debugging mismatched district names (the NTD reality)

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Join programme prevalence table to shapefile; troubleshoot 3 unmatched districts |
| Day 4 (+3) | Write a reusable R function that checks CRS before joining |
| Week 3 (+1 wk) | Review: embedded A1 quiz + demonstrate joined file to a partner |

---

### Module 3 | Week 3 — GPS Data Quality & Field Realities
**Competencies:** A4  
**Bloom level:** Analyze  
**Prerequisites met:** A2, A3  

**Session (2 h):**
- Common GPS errors: swapped lat/lon, impossible coordinates, datum mismatch
- Detection and flagging workflow in R
- Case study: HAT active screening GPS from DRC field data (anonymised)

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Run provided "dirty" GPS dataset through detection pipeline |
| Day 4 (+3) | Write a validation report for your own programme's GPS data |
| Week 4 (+1 wk) | A2+A3 flashcard review embedded in Module 4 opening |

---

### Module 4 | Week 4 — Making Maps That Communicate
**Competencies:** B1, B4  
**Bloom level:** Apply → Evaluate  
**Prerequisites met:** A3  

**Session (3 h):**
- `ggplot2` + `sf`: `geom_sf()`, `scale_fill_viridis_c()`, themes
- Colour theory for maps: sequential vs diverging palettes, colour-blind safety
- Critique session: peer-review 3 published NTD maps — what misleads?

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Reproduce a choropleth of LF prevalence with proper legend + scale bar |
| Day 4 (+3) | Redesign a poor map from the critique using improved palette + annotation |
| Week 5 (+1 wk) | A2/A3/B1 integration exercise: full map from raw shapefile to final figure |

---

### Module 5 | Week 5 — Uncertainty and Audience-Adapted Maps
**Competencies:** B2, B5  
**Bloom level:** Analyze → Create  
**Prerequisites met:** B1, B4  

**Session (2.5 h):**
- Mapping confidence intervals: bivariate maps, hatching for data-sparse areas
- Offline/print maps for field use: `tmap`, PDF export, font sizing
- Adaptation for low-literacy audiences: legend design, icon-based maps

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Add a data-completeness layer to your Week 4 map |
| Day 4 (+3) | Produce a print-ready A4 map for a district health officer |
| Week 6 (+1 wk) | B1–B5 synthesis: deliver a 5-minute map briefing to the team (assessed) |

**Phase 1 Assessment (end of Week 5 / beginning of Week 6) — see assessments file**

---

## Phase 2 — Spatial Statistics: Describing Patterns (Weeks 6–12)

### Module 6 | Week 6 — Interactive Maps & Phase 1 Review
**Competencies:** B3 + Phase 1 spaced review  
**Bloom level:** Apply  

**Session (2 h):**
- `leaflet` in R: markers, popups, basemaps, choropleth overlays
- Embedding interactive maps in R Markdown / Quarto reports
- Phase 1 integrated review quiz (A1–A5, B1–B5 spot checks)

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Build a leaflet map of active screening sites with hover-pop case counts |
| Day 4 (+3) | Export map to HTML; share with a colleague for usability feedback |

---

### Module 7 | Week 7 — Is Disease Clustering? Global Spatial Autocorrelation
**Competencies:** C1  
**Bloom level:** Analyze  
**Prerequisites met:** A3  

**Session (2.5 h):**
- Spatial weights matrices: queen/rook contiguity, k-nearest neighbours
- Global Moran's I: formula, permutation test, interpretation
- R: `spdep` package — `poly2nb()`, `nb2listw()`, `moran.test()`

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Compute Moran's I on your programme's district prevalence; interpret result |
| Day 4 (+3) | Test sensitivity to weights matrix choice (queen vs k=5) |
| Week 8 (+1 wk) | Pair with a colleague: each explains Moran's I to the other without notes |

---

### Module 8 | Week 8 — Where Is Disease Clustering? Local Statistics & Hot Spots
**Competencies:** C2  
**Bloom level:** Analyze  
**Prerequisites met:** C1  

**Session (2.5 h):**
- Local Moran's I (LISA): HH, LL, HL, LH quadrants
- False discovery rate correction for multiple testing
- Mapping LISA clusters with significance overlay in R

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Produce a LISA cluster map for your NTD district data |
| Day 4 (+3) | Identify 3 high-high clusters; hypothesize explanatory factors |
| Week 9 (+1 wk) | C1 flashcard review + Moran's I / LISA distinction quiz |

---

### Module 9 | Week 9 — Variograms and Spatial Continuity
**Competencies:** C3  
**Bloom level:** Understand → Analyze  
**Prerequisites met:** C1  

**Session (2 h):**
- Semivariance: concept, experimental variogram, model fitting
- Range, sill, nugget: ecological meaning for NTD transmission zones
- R: `gstat` package — variogram fitting

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Fit and plot an experimental variogram on programme point data |
| Day 4 (+3) | Fit spherical vs exponential model; compare and justify choice |

---

### Module 10 | Week 10 — Kernel Density & Point Pattern Analysis
**Competencies:** C4  
**Bloom level:** Apply  
**Prerequisites met:** A4  

**Session (2 h):**
- KDE: bandwidth selection, edge correction
- Point pattern analysis: intensity, nearest-neighbour distance
- R: `spatstat`, `MASS::kde2d()`

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | KDE map of HAT cases from active screening; test two bandwidths |
| Day 4 (+3) | Compare KDE output to LISA hot-spot map from Module 8 — where do they agree/disagree? |
| Week 11 (+1 wk) | C1–C4 synthesis quiz embedded in Module 11 |

---

### Module 11 | Week 11 — Spatial Scan Statistics for Cluster Detection
**Competencies:** C5  
**Bloom level:** Apply  
**Prerequisites met:** C2  

**Session (2 h):**
- SaTScan logic: purely spatial, space-time, Poisson model
- `SpatialEpi` in R as an alternative
- Interpreting LLR, RR, p-value; reporting for programme use

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Run spatial scan on district case counts; identify top 3 clusters |
| Day 4 (+3) | Draft a one-page cluster alert memo using scan output |

---

### Module 12 | Week 12 — Phase 2 Integration & Mid-Point Review
**Competencies:** C1–C5 integration  
**Bloom level:** Analyze  

**Session (2 h):**
- Comparative exercise: apply Moran's I, LISA, KDE, and scan statistics to the same dataset
- Discussion: which method answers which question?
- Phase 2 assessment (see assessments file)

---

## Phase 3 — Spatial Regression & Modelling (Weeks 13–19)

### Module 13 | Week 13 — Why Spatial Regression?
**Competencies:** D1  
**Bloom level:** Analyze  
**Prerequisites met:** C1  

**Session (2.5 h):**
- OLS residual diagnostics: Moran test on residuals (`lm.morantest()`)
- Consequences of ignoring spatial autocorrelation in NTD models
- Choosing between spatial lag, spatial error, spatially filtered models

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Fit an OLS model on district NTD rates; test residuals for autocorrelation |
| Day 4 (+3) | Interpret the Lagrange multiplier tests from `spatialreg::lm.LMtests()` |
| Week 14 (+1 wk) | C1 + D1 quiz: autocorrelation concept and diagnostic recap |

---

### Module 14 | Week 14 — Spatial Lag and Spatial Error Models
**Competencies:** D2  
**Bloom level:** Analyze  
**Prerequisites met:** D1  

**Session (2.5 h):**
- Spatial lag model: `lagsarlm()` — interpretation of spatial lag coefficient rho
- Spatial error model: `errorsarlm()` — interpretation of lambda
- Model selection: Robust LM tests; AIC comparison

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Fit both models to your NTD dataset; compare coefficients and AIC |
| Day 4 (+3) | Write a methods paragraph justifying your model choice |

---

### Module 15 | Week 15 — Poisson Spatial Regression for Count Data
**Competencies:** D3  
**Bloom level:** Apply  
**Prerequisites met:** D2  

**Session (2.5 h):**
- Count data in NTD surveillance: why Poisson, offset for population/effort
- Spatial Poisson models: `spatialreg` + `INLA` intro
- Overdispersion checks; negative binomial alternative

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Fit a Poisson spatial regression for your district case counts with population offset |
| Day 4 (+3) | Check for overdispersion; refit with NB if needed; compare results |
| Week 16 (+1 wk) | D1–D3 combined quiz |

---

### Module 16 | Week 16 — Geographically Weighted Regression
**Competencies:** D4  
**Bloom level:** Apply  
**Prerequisites met:** D3  

**Session (2 h):**
- Non-stationarity: when associations vary across space
- GWR: kernel functions, bandwidth selection (CV, AIC)
- R: `GWmodel` package; mapping local coefficients

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Fit GWR to poverty → NTD prevalence; map local beta coefficients |
| Day 4 (+3) | Identify districts where the poverty effect is strongest; generate hypotheses |

---

### Module 17 | Week 17 — Model Evaluation and Selection
**Competencies:** D5  
**Bloom level:** Evaluate  
**Prerequisites met:** D3  

**Session (2 h):**
- DIC, WAIC in Bayesian spatial models (INLA)
- Leave-one-out cross-validation for spatial models
- Reporting model uncertainty for programme decision-makers

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Compare DIC across three models fit to your dataset |
| Day 4 (+3) | Draft a model comparison table for a technical report |

---

### Module 18 | Week 18 — Phase 3 Review + Peer Teaching
**Competencies:** D1–D5 integration  
**Bloom level:** Analyze/Evaluate  

**Session (2 h):**
- Peer teaching: each participant explains one regression concept to a partner
- Group debug: 2 intentionally flawed spatial regression scripts — find the errors
- Phase 3 assessment (see assessments file)

---

## Phase 4 — NTD Applications & Capstone (Weeks 19–26)

### Module 19 | Week 19 — Environmental Covariates for NTD Risk Mapping
**Competencies:** E2 (part 1)  
**Bloom level:** Create (building)  
**Prerequisites met:** D3, B2  

**Session (2.5 h):**
- Environmental covariate sources: NDVI, rainfall, land use, temperature (Google Earth Engine export / pre-processed rasters)
- Extracting raster values to polygon centroids; handling missing covariates
- Building an NTD risk model integrating ecology + epidemiology

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Extract NDVI values to your district polygons; check correlation with NTD rates |
| Day 4 (+3) | Add 2 environmental covariates to your spatial regression; compare AIC |

---

### Module 20 | Week 20 — Delineating Treatment Units from Spatial Data
**Competencies:** E1  
**Bloom level:** Create  
**Prerequisites met:** B1, C2  

**Session (2 h):**
- Spatial definition of treatment units: LISA cluster + programmatic feasibility overlay
- Combining spatial analysis output with operational boundaries
- Producing a MDA target-area map with clear decision logic

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Delineate treatment priority zones using LISA output + programme coverage data |
| Day 4 (+3) | Present decision logic in a one-page map brief to a non-spatial colleague |

---

### Module 21 | Week 21 — Spatial MDA Coverage Monitoring
**Competencies:** E3  
**Bloom level:** Create  
**Prerequisites met:** B3, C4  

**Session (2 h):**
- Designing a spatial monitoring system: what data, what frequency, what trigger
- Coverage gap mapping: KDE of treatment points vs eligible population
- Leaflet dashboard for field supervisors

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Build a leaflet coverage dashboard for a simulated MDA round |
| Day 4 (+3) | Identify 3 under-covered clusters; write a field follow-up protocol |

---

### Module 22 | Week 22 — Accessibility and Health Equity Analysis
**Competencies:** E4  
**Bloom level:** Analyze  
**Prerequisites met:** D4, B2  

**Session (2 h):**
- Distance-to-facility analysis: `sf::st_distance()`, travel time surfaces (if available)
- Spatial equity: who is far from treatment and are they also high-risk?
- Equity maps: overlaying distance, prevalence, and population density

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Compute distance from village centroids to nearest treatment point |
| Day 4 (+3) | Produce an equity map: accessibility vs NTD risk quartiles |

---

### Module 23 | Week 23 — Communicating Spatial Evidence
**Competencies:** E5  
**Bloom level:** Create  
**Prerequisites met:** B5, E2  

**Session (2 h):**
- Structuring a spatial analysis brief for programme managers
- Verbal narrative around maps: what to say, what to avoid
- Handling stakeholder questions about model uncertainty

**Practicals:**
| Day | Task |
|-----|------|
| Day 2 (+1) | Draft a 2-page spatial evidence brief for a programme review meeting |
| Day 4 (+3) | Present brief to partner — partner role-plays as a sceptical programme manager |

---

### Modules 24–25 | Weeks 24–25 — Capstone Projects

**Format:** Individual or pairs. Each participant applies the full pipeline to a real dataset from their programme (or a supplied comparable dataset).

**Capstone deliverables:**
1. Cleaned and joined spatial dataset with CRS documentation
2. Descriptive spatial analysis (Moran's I, LISA map, KDE)
3. Spatial regression model with justification
4. Risk or coverage map (publication-quality)
5. One-page programme brief with decision recommendation
6. 10-minute presentation to the team + external reviewer

**Week 24:** Work session with facilitator support (code review, troubleshooting)  
**Week 25:** Presentation rehearsal + peer feedback

---

### Module 26 | Week 26 — Final Presentations & Retrospective
**Competencies:** E1–E5 demonstrated  
**Bloom level:** Create + Evaluate  

**Session (4 h):**
- Capstone presentations (each ~12 min + Q&A)
- External reviewer panel (programme manager + methods expert)
- Group retrospective: what worked, what needs reinforcement
- Individual competency self-assessment (map against baseline)
- Programme close-out: resources, community of practice, continuing review schedule

---

## Spaced Repetition Master Schedule

Each concept receives review at: **+1 day, +3 days, +1 week, +2 weeks, +1 month post-introduction**. The table below shows which competency domains receive active review in each week:

| Week | New Content | Active Spaced Reviews |
|------|------------|----------------------|
| 1 | A1, A5 | — |
| 2 | A2, A3 | A1 (+1 wk) |
| 3 | A4 | A1 (+2 wk), A2/A3 (+1 wk) |
| 4 | B1, B4 | A2/A3 (+2 wk), A4 (+1 wk) |
| 5 | B2, B5 | A1 (+1 mo), B1/B4 (+1 wk), A4 (+2 wk) |
| 6 | B3 | B1/B4 (+2 wk), B2/B5 (+1 wk), A2/A3 (+1 mo) |
| 7 | C1 | B3 (+1 wk), B2/B5 (+2 wk), A4 (+1 mo) |
| 8 | C2 | C1 (+1 wk), B1/B4 (+1 mo) |
| 9 | C3 | C2 (+1 wk), C1 (+2 wk), B3 (+1 mo) |
| 10 | C4 | C3 (+1 wk), C2 (+2 wk), B2/B5 (+1 mo) |
| 11 | C5 | C4 (+1 wk), C3 (+2 wk), C1 (+1 mo) |
| 12 | Integration | C5 (+1 wk), C4 (+2 wk), C2 (+1 mo) |
| 13 | D1 | C5 (+2 wk), C3 (+1 mo) |
| 14 | D2 | D1 (+1 wk), C4 (+1 mo) |
| 15 | D3 | D2 (+1 wk), D1 (+2 wk), C5 (+1 mo) |
| 16 | D4 | D3 (+1 wk), D2 (+2 wk), D1 (+1 mo) |
| 17 | D5 | D4 (+1 wk), D3 (+2 wk), D2 (+1 mo) |
| 18 | Integration | D5 (+1 wk), D4 (+2 wk), D3 (+1 mo) |
| 19 | E2 (part) | D5 (+2 wk), D4 (+1 mo) |
| 20 | E1 | E2 (+1 wk), D5 (+1 mo) |
| 21 | E3 | E1 (+1 wk), E2 (+2 wk) |
| 22 | E4 | E3 (+1 wk), E1 (+2 wk), E2 (+1 mo) |
| 23 | E5 | E4 (+1 wk), E3 (+2 wk), E1 (+1 mo) |
| 24 | Capstone | E5 (+1 wk), E4 (+2 wk) |
| 25 | Rehearsal | E5 (+2 wk), E3 (+1 mo) |
| 26 | Final | All domains — retrospective self-assessment |
