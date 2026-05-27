---
title: "Spatial Epidemiology"
domain: "methods"
tags:
  - spatial
  - cluster-detection
  - disease-mapping
  - risk-factors
  - hotspots
related:
  - "methods/gis-for-epidemiology.md"
  - "methods/surveillance-systems.md"
  - "disease-areas/hat-sleeping-sickness.md"
  - "methods/biostatistics-essentials.md"
phd_relevance: "high"
status: "current"
updated: "2026-03-29"
---
# Spatial Epidemiology

> Reference card — spatial analysis methods, disease mapping, cluster detection, software.

---

## Cluster Detection Methods

### Kulldorff Scan Statistic (SaTScan)
- **Principle:** Circular (or elliptical) scanning window moves across study area; compares observed vs expected cases inside vs outside window using likelihood ratio
- **Models:** Poisson (count data), Bernoulli (case/control), space-time permutation
- **Strengths:** Adjusts for multiple testing; identifies most likely cluster + secondary clusters; well-validated
- **Limitations:** Circular window may miss irregular-shaped clusters; sensitive to population heterogeneity
- **Software:** SaTScan (free, standalone), `rsatscan` (R interface)

### FleXScan
- **Principle:** Flexible spatial scan statistic using irregularly shaped windows based on graph connectivity
- **Strengths:** Detects non-circular clusters; better for administrative boundary data
- **Limitations:** Computationally intensive; less widely validated
- **Software:** FleXScan (standalone), R implementation available

### Other Cluster Methods
- **Moran's I:** Global spatial autocorrelation; is there overall clustering?
- **Local Moran's I (LISA):** Identifies local clusters (hot spots) and spatial outliers
- **Getis-Ord Gi*:** Hot spot analysis; identifies statistically significant spatial clusters of high/low values
- **Knox test:** Space-time interaction for point data
- **K-function (Ripley's K):** Point pattern analysis; evaluates clustering at multiple distances

---

## Disease Mapping

### Bayesian Smoothing
- **Problem:** Raw rates from small areas are unstable (small number problem)
- **Solution:** Borrow strength from neighbours using Bayesian hierarchical models
- **Effect:** Shrinks extreme estimates toward local or global mean

### BYM Model (Besag-York-Mollie)
- **Structure:** Poisson likelihood + two random effects:
  - Spatially structured (ICAR — intrinsic conditional autoregressive)
  - Unstructured (exchangeable/iid)
- **Use:** Standard model for disease mapping with areal data
- **Extensions:** BYM2 (reparameterized, easier to set priors; Riebler et al. 2016)
- **Software:** `R-INLA`, `CARBayes`, `brms`, WinBUGS/OpenBUGS

### Other Mapping Approaches
- **Standardized Mortality/Morbidity Ratio (SMR):** Observed/expected; unstable for small populations
- **Empirical Bayes (EB):** Non-fully-Bayesian shrinkage; simpler but less flexible
- **Spatio-temporal models:** Add temporal random effects (Type I-IV interactions; Knorr-Held)

---

## Spatial Regression

### Spatial Autoregressive (SAR) Models
- **Spatial lag model:** Outcome in area i depends on outcomes in neighbours
- **Spatial error model:** Error terms are spatially correlated
- **When to use:** When spatial dependence is in the outcome or residuals

### Conditional Autoregressive (CAR) Models
- **Principle:** Conditional distribution of each area given its neighbours
- **ICAR:** Intrinsic CAR — improper prior, used in BYM
- **Leroux CAR:** Balances spatial and non-spatial variation; single smoothing parameter
- **When to use:** Bayesian disease mapping, areal data with neighbourhood structure

### Geographically Weighted Regression (GWR)
- **Principle:** Allows regression coefficients to vary spatially
- **When to use:** Exploring spatial non-stationarity in relationships
- **Limitations:** Multicollinearity issues; bandwidth selection; interpretation challenges
- **Software:** `GWmodel`, `spgwr` (R)

### Geostatistical Models
- **Principle:** Model continuous spatial surface from point data using variograms/kriging
- **When to use:** Environmental exposures, interpolation of point-referenced data
- **Software:** `geoR`, `gstat`, `PrevMap` (R)

---

## Key R Packages

| Package | Purpose |
|---------|---------|
| `sf` | Simple features; spatial data handling (successor to `sp`) |
| `terra` | Raster data handling (successor to `raster`) |
| `spdep` | Spatial dependence: weights, Moran's I, spatial regression |
| `spatstat` | Point pattern analysis |
| `SpatialEpi` | Cluster detection, disease mapping utilities |
| `rsatscan` | R interface to SaTScan |
| `R-INLA` | Bayesian spatial models (INLA approximation) |
| `CARBayes` | CAR models via MCMC |
| `tmap` | Thematic maps (publication-quality) |
| `leaflet` | Interactive web maps |
| `mapview` | Quick interactive visualization |
| `GWmodel` | Geographically weighted models |
| `gstat` | Geostatistics, variograms, kriging |
| `PrevMap` | Geostatistical prevalence mapping |
| `rgeoda` | R interface to GeoDa (spatial analysis) |

---

## Workflow Template

1. **Data preparation:** Shapefile/GeoJSON + case data; compute rates; define neighbourhood (queen/rook contiguity or k-nearest)
2. **Exploratory:** Map raw rates; test global autocorrelation (Moran's I); LISA maps
3. **Smoothing:** BYM2 model via INLA for stable rate estimates
4. **Cluster detection:** SaTScan for formal cluster identification
5. **Regression:** Spatial regression if covariates available; check residual autocorrelation
6. **Visualization:** tmap for static publication figures; leaflet for interactive

---

## Current Developments (2025-2026)

- **SaTScan remains actively maintained:** The official SaTScan site lists **version 10.3.3** with a **September 2025** release date, which is important for analysts relying on spatial and space-time scan statistics in elimination and outbreak settings.
- **The `sf` ecosystem is still evolving:** The `sf` changelog records releases on **24 March 2025 (v1.0-20)**, **28 November 2025 (v1.0-23)**, and **12 January 2026 (v1.0-24)**. This reinforces that modern spatial epidemiology in R continues to move further away from legacy `sp` workflows.
- **Cartography tools improved in 2025:** The `tmap` project changelog shows **v4.1 on 12 May 2025** and **v4.2 on 10 September 2025**, with ongoing work on legends, inset maps, animation, and dashboard-friendly display options.
- **Spatial regression tooling remains current:** CRAN metadata show `spatialreg` published an update on **6 September 2025**, supporting continued use of lag and error models in maintained R workflows.
- **Practical implication:** The strongest current workflow is usually a modular stack: `sf` + `terra` + `tmap` + `spdep`/`spatialreg` + SaTScan, rather than depending on one older umbrella package.

## Practical Examples

- **Disease atlas and focal persistence:** Simarro et al. showed how georeferenced disease case data can be used to identify persistent foci and support elimination planning.
- **Bayesian disease mapping in practice:** Riebler et al. (2016) formalized BYM2, which is now widely used when analysts need stable small-area estimates with interpretable priors.
- **Formal cluster detection:** Kulldorff's scan statistic remains one of the most practical tools for deciding whether apparent hotspots are unusual relative to background population structure.
- **Reproducible geospatial health workflows:** Moraga's geospatial health text remains one of the clearest applied bridges between Bayesian mapping, R code, and public-health visualization.

## Key References

- **Lawson AB.** *Bayesian Disease Mapping: Hierarchical Modeling in Spatial Epidemiology.* 3rd ed. CRC Press, 2018.
- **Waller LA, Gotway CA.** *Applied Spatial Statistics for Public Health Data.* Wiley, 2004.
- **Bivand RS, Pebesma E, Gomez-Rubio V.** *Applied Spatial Data Analysis with R.* 2nd ed. Springer, 2013.
- **Moraga P.** *Geospatial Health Data: Modeling and Visualization with R-INLA and Shiny.* CRC Press, 2019.
- **Kulldorff M.** A spatial scan statistic. *Communications in Statistics — Theory and Methods.* 1997;26(6):1481-1496.
- **Besag J, York J, Mollie A.** Bayesian image restoration with two applications in spatial statistics. *Annals of the Institute of Statistical Mathematics.* 1991;43:1-20.
- **Riebler A et al.** An intuitive Bayesian spatial model for disease mapping that accounts for scaling. *Statistical Methods in Medical Research.* 2016;25(4):1145-1165.
- **SaTScan official site:** https://www.satscan.org/
- **SaTScan downloads and documentation:** https://www.satscan.org/download_satscan.html
- **`sf` project site:** https://r-spatial.github.io/sf/
- **`sf` changelog:** https://r-spatial.github.io/sf/news/index.html
- **`tmap` project site:** https://r-tmap.github.io/tmap/
- **`tmap` changelog:** https://r-tmap.github.io/tmap/news/index.html
- **CRAN `spatialreg`:** https://cran.r-project.org/package=spatialreg
- **CRAN `SpatialEpi`:** https://cran.r-project.org/package=SpatialEpi

## Learning Path

- Start with `knowledge/library/courses/spatial-epidemiology/`.
- Pair this card with `knowledge/library/methods/gis-for-epidemiology.md` for data structures, CRS, and mapping basics.
- Review `knowledge/library/methods/biostatistics-essentials.md` before fitting spatial regression or Bayesian smoothing models.
- In the Learning Hub, this card aligns primarily with **Spatial epidemiology** and secondarily with **Biostatistics**.

---

*Last updated: 2026-03-29 | Enriched with 2025-2026 software and workflow updates*
