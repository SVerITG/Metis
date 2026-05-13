---
title: "GIS for Epidemiology"
domain: "methods"
tags:
  - GIS
  - mapping
  - spatial-data
  - QGIS
  - OpenStreetMap
related:
  - "methods/spatial-epidemiology.md"
  - "methods/surveillance-systems.md"
  - "concepts/digital-health-epi.md"
phd_relevance: "high"
status: "current"
updated: "2026-03-30"
---
# GIS for Epidemiology

> Reference card — spatial data fundamentals, mapping health data, and software tools for epidemiological GIS work.

---

## Coordinate Reference Systems

- **WGS84 (EPSG:4326):** Global standard for GPS coordinates; latitude/longitude in degrees; use for data collection and storage
- **UTM (Universal Transverse Mercator):** Projected system; meters as units; better for distance/area calculations within a zone
- **Always check and document the CRS** of every dataset before combining
- Reprojection needed when datasets use different CRS; use `st_transform()` in R or reproject in QGIS

## Vector vs Raster Data

- **Vector:** Points (health facilities, cases), lines (roads, rivers), polygons (admin boundaries, catchment areas)
- **Raster:** Grid of cells with values; used for continuous surfaces (elevation, temperature, population density, remotely sensed imagery)
- **Shapefiles (.shp):** Common vector format; actually 4+ files (.shp, .shx, .dbf, .prj); legacy format with limitations
- **GeoPackage (.gpkg):** Modern alternative to shapefile; single file, no field name length limits; recommended
- **GeoTIFF (.tif):** Standard raster format with embedded georeferencing

## Geocoding Health Facility Data

- Convert facility names/addresses to coordinates
- Master facility lists (MFL) often available from MoH or WHO
- OpenStreetMap as supplementary source
- GPS field collection for unmapped facilities (handheld GPS or smartphone)
- Always validate: check points fall within expected administrative boundaries

## Linking Health Data to Administrative Boundaries

- Join tabular health data (cases, coverage) to boundary shapefiles via shared admin codes
- Standard admin boundary sources: GADM, UN OCHA (HDX), national mapping agencies
- Watch for: mismatched admin codes, boundary changes over time, naming inconsistencies
- P-codes (place codes) from OCHA provide standardized identifiers

## Map Types for Epidemiology

- **Choropleth:** Shaded polygons by rate/count; good for admin-level comparisons; beware visual dominance of large areas
- **Dot maps:** Individual cases or facilities as points; shows spatial pattern without aggregation bias
- **Proportional symbols:** Circles scaled to magnitude at each location
- **Heat maps / kernel density:** Smooth continuous surface from point data; highlights clusters
- **Isopleth / contour maps:** Lines connecting equal values; used for environmental exposures

## Software and R Packages

- **QGIS:** Free, open-source desktop GIS; full-featured; good for exploration and map production
- **ArcGIS:** Commercial; widely used in government; ArcGIS Online for web maps
- **R packages:**
  - `sf` — modern spatial data handling (replaces `sp`); integrates with tidyverse
  - `terra` — raster data (replaces `raster`)
  - `tmap` — thematic maps; publication-quality; grammar-of-graphics style
  - `leaflet` — interactive web maps; great for Shiny dashboards
  - `mapview` — quick interactive map exploration during analysis
  - `spdep` — spatial autocorrelation and spatial regression
  - `gstat` — geostatistics and kriging

## GPS Data Collection in the Field

- Record waypoints at health facilities, case households, intervention sites
- Accuracy: standard smartphones 3-5 m; dedicated GPS units 2-3 m; differential GPS < 1 m
- Record metadata: date, time, collector ID, site description
- Privacy consideration: jitter or aggregate case locations to protect patient confidentiality
- Battery and satellite signal challenges in dense forest or deep valleys

## Current Developments (2025-2026)

- **Modern R-spatial workflows are now the default:** The `rgdal`, `rgeos`, and `maptools` retirements are no longer transitional footnotes; in 2025-2026 the practical standard is `sf` + `terra`, not legacy `sp`-centric code.
- **`sf` and `tmap` are actively maintained:** The `sf` project recorded releases through **12 January 2026 (v1.0-24)** and `tmap` reached **v4.2 on 10 September 2025**, which matters because geometry handling and cartography continue to improve.
- **GIS work is becoming more surveillance-facing:** ECDC published its wastewater-based surveillance framework on **10 December 2025**, showing how geospatial infrastructure is being integrated into routine public-health surveillance rather than used only for retrospective mapping.
- **Practical implication:** For field epidemiology and NTD mapping, use stable open formats such as GeoPackage and GeoTIFF, document CRS decisions explicitly, and avoid building new workflows on retired spatial packages.

## Practical Examples

- **HAT atlas workflows:** Georeferenced HAT case and health-facility data are a clear example of GIS supporting focal surveillance, service accessibility analysis, and elimination planning.
- **Environmental covariates for vector-borne disease:** Satellite-derived rainfall, land cover, and temperature rasters are routinely linked to case data to explain vector distribution or transmission suitability.
- **Facility mapping for service gaps:** Joining facility coordinates to administrative boundaries is a practical way to identify diagnostic deserts, referral bottlenecks, and under-covered districts.
- **Wastewater surveillance siting:** GIS is increasingly used to decide where environmental sampling points best complement clinical surveillance and population coverage.

## Key References

- **Cromley EK, McLafferty SL.** *GIS and Public Health.* 2nd ed. Guilford Press, 2011.
- **Pebesma E.** Simple features for R: standardized support for spatial vector data. *The R Journal.* 2018;10(1):439-446.
- **Tennekes M.** tmap: thematic maps in R. *Journal of Statistical Software.* 2018;84(6):1-39.
- **Hay SI et al.** Global mapping of infectious disease. *Philosophical Transactions of the Royal Society B.* 2013;368(1614):20120250.
- **`sf` project site and changelog:** https://r-spatial.github.io/sf/
- **`tmap` project site and changelog:** https://r-tmap.github.io/tmap/
- **R-spatial transition guidance:** https://r-spatial.org/r/2023/05/15/evolution4.html
- **ECDC wastewater-based surveillance framework news:** https://www.ecdc.europa.eu/en/news-events/ecdc-lead-integration-wastewater-based-surveillance-infectious-disease-surveillance

---

## Learning Path

- Start with `knowledge/library/courses/spatial-epidemiology/` and `knowledge/library/courses/epidemiology-foundations/`.
- Pair with `knowledge/library/methods/data-management.md` for reproducible GIS workflows and `knowledge/library/concepts/digital-health-epi.md` for digital surveillance integration.
- Use alongside `knowledge/library/concepts/health-systems-strengthening.md` for service or workforce mapping insights.
- In the Learning Hub, this card supports **Spatial epidemiology** and **Data management & R**.

---

*Last updated: 2026-03-30 | Enriched with current R-spatial and public-health GIS updates*
