# Competency Map — Spatial Epidemiology Upskilling Programme
## NTD Field Epidemiologists | 6-Month Programme

**Audience:** 8 NTD field epidemiologists — basic R, no spatial analysis experience  
**Goal:** Independent spatial analysis for NTD surveillance and control decision-making  
**Framework:** Bloom's taxonomy levels noted per competency (Apply minimum; Analyze/Create preferred)

---

## Domain A — Spatial Data Foundations

| ID | Competency | Bloom Level | Prerequisite |
|----|-----------|-------------|-------------|
| A1 | Distinguish vector vs raster data models and explain when each applies to NTD mapping | Understand | — |
| A2 | Import, inspect, and repair coordinate reference systems (CRS) in R using `sf` | Apply | A1 |
| A3 | Join tabular epidemiological data to spatial geometries (district/health zone polygons) | Apply | A2 |
| A4 | Identify and resolve common data quality issues in field-collected GPS coordinates | Analyze | A3 |
| A5 | Source and evaluate publicly available shapefiles for LMICs (GADM, OCHA, HDX) | Evaluate | A1 |

---

## Domain B — Spatial Visualisation

| ID | Competency | Bloom Level | Prerequisite |
|----|-----------|-------------|-------------|
| B1 | Produce a publication-quality choropleth map of NTD prevalence in `ggplot2` + `sf` | Apply | A3 |
| B2 | Design maps that communicate uncertainty (confidence intervals, data completeness) | Analyze | B1 |
| B3 | Build interactive maps in `leaflet` for field team consumption | Apply | A3 |
| B4 | Apply colour theory principles to avoid misleading prevalence maps | Evaluate | B1 |
| B5 | Adapt map design for low-literacy field audiences and print/offline use | Create | B4 |

---

## Domain C — Spatial Statistics I (Descriptive)

| ID | Competency | Bloom Level | Prerequisite |
|----|-----------|-------------|-------------|
| C1 | Compute and interpret global Moran's I for NTD case clustering | Analyze | A3 |
| C2 | Run Local Indicators of Spatial Association (LISA / Anselin local Moran) and map hot/cold spots | Analyze | C1 |
| C3 | Construct and interpret a variogram; explain range, sill, nugget in disease context | Understand | C1 |
| C4 | Apply kernel density estimation to point-level case data | Apply | A4 |
| C5 | Perform spatial scan statistics (SaTScan / `SpatialEpi`) for cluster detection | Apply | C2 |

---

## Domain D — Spatial Statistics II (Regression & Modelling)

| ID | Competency | Bloom Level | Prerequisite |
|----|-----------|-------------|-------------|
| D1 | Diagnose spatial autocorrelation in regression residuals (Moran test on residuals) | Analyze | C1 |
| D2 | Fit and interpret a spatial lag model vs spatial error model | Analyze | D1 |
| D3 | Specify and run a Poisson spatial regression for NTD counts with offset | Apply | D2 |
| D4 | Apply geographically weighted regression (GWR) to examine non-stationarity | Apply | D3 |
| D5 | Evaluate model fit using DIC, WAIC, or cross-validation in a spatial context | Evaluate | D3 |

---

## Domain E — NTD-Specific Applications

| ID | Competency | Bloom Level | Prerequisite |
|----|-----------|-------------|-------------|
| E1 | Delineate treatment units based on spatial prevalence and programme boundaries | Create | B1, C2 |
| E2 | Produce a risk map for HAT / LF / onchocerciasis integrating environmental covariates | Create | D3, B2 |
| E3 | Design a spatial monitoring framework for MDA coverage tracking | Create | B3, C4 |
| E4 | Conduct a spatial equity analysis of health service accessibility (distance to treatment point) | Analyze | D4, B2 |
| E5 | Present spatial findings to a non-technical programme manager audience | Create | B5, E2 |

---

## Prerequisite DAG (text representation)

```
A1 → A2 → A3 → A4
          A3 → B1 → B2 → B5
          A3 → B3
          B1 → B4 → B5
          A3 → C1 → C2 → C5
                    C2 → E1
          C1 → C3
          A4 → C4 → E3
          C1 → D1 → D2 → D3 → D4 → E4
                         D3 → D5
                         D3 → E2
     A1 → A5
          B1, C2 → E1
          D3, B2 → E2
          B3, C4 → E3
          B5, E2 → E5
```

---

## Bloom's Taxonomy Distribution

| Level | Count | % |
|-------|-------|---|
| Understand | 3 | 12% |
| Apply | 12 | 48% |
| Analyze | 8 | 32% |
| Evaluate | 3 | 12% |
| Create | 6 | 24% |

*Note: Several competencies are counted once at their primary level; total exceeds 25 due to rounding.*  
**No competency sits below Apply — all learning goals are action-oriented.**
