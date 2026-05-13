# R Packages for Spatial Epidemiology

## Learning objectives
- Identify the main R packages used in modern spatial epidemiology workflows.
- Understand where `sf`, `terra`, `tmap`, `spdep`, `spatialreg`, and related tools fit.
- Build a minimal but coherent spatial analysis stack.
- Appreciate why reproducible preprocessing matters as much as the final map or model.

## Prerequisites
- GIS basics.

## Content

### Section 1: Why package choice matters
Modern spatial epidemiology in R is modular. No single package does everything well, and that is usually a strength rather than a weakness. A good workflow combines packages for geometry handling, raster processing, visualization, diagnostics, and modeling.

The practical goal is not to memorize package names. It is to know which tool belongs to which task and how to keep the handoffs between tasks explicit and reproducible.

### Section 2: Core vector and raster tools
For vector data, the current standard is **`sf`**. It handles points, lines, polygons, joins, transformations, and geometry validation in a way that integrates well with the broader R ecosystem.

For raster data, **`terra`** is the current workhorse. It supports gridded covariates such as rainfall, elevation, or temperature surfaces and is now preferred over older workflows built on the retired `raster` package.

Together, `sf` and `terra` form the core spatial data stack for most applied epidemiology projects.

### Section 3: Mapping packages
Several packages are useful for visualization.

- **`tmap`** is strong for thematic and publication-quality maps.
- **`leaflet`** is useful for interactive maps and dashboards.
- **`mapview`** is useful for quick exploratory visualization during data cleaning and analysis.

The key distinction is often whether you need a polished static figure, an interactive map for exploration, or a quick look at whether the data even align properly.

### Section 4: Dependence and modeling packages
For spatial dependence diagnostics and classical spatial modeling, packages such as **`spdep`** and **`spatialreg`** are central.

- `spdep` helps define neighbors and compute diagnostics such as Moran's I
- `spatialreg` supports lag and error models

For Bayesian disease mapping and smoothing, analysts often move beyond these packages into frameworks such as `R-INLA`, `CARBayes`, or related modeling tools, depending on the workflow.

For point pattern analysis, `spatstat` may become important. For cluster detection with SaTScan, `rsatscan` can serve as an R interface to the external software.

### Section 5: Worked example - a minimal spatial stack
Suppose you want to analyze village-level HAT data with environmental covariates and health-zone boundaries.

A simple modern stack might look like this:

- `sf` to read and clean village points and polygons
- `terra` to handle environmental raster layers
- `tmap` to produce choropleths and point maps
- `spdep` to define neighborhood structures and test Moran's I
- `spatialreg` or a Bayesian alternative if regression needs explicit spatial structure

This is more robust than trying to force one package to handle every stage.

### Section 6: Why reproducibility matters
In spatial epidemiology, preprocessing choices can materially change the result. CRS transformations, geometry repairs, joins, raster extraction rules, neighborhood definitions, and smoothing settings all affect downstream outputs.

That is why explicit scripts matter. A map that cannot be reproduced from raw inputs is hard to audit and hard to trust. The same is true for a hotspot analysis whose neighbor definition or denominator calculation is hidden in manual GIS clicks.

Good practice means keeping the workflow explicit, scripted, and documented.

### Section 7: Common mistakes
Several package-level mistakes recur often.

- mixing legacy and modern spatial classes carelessly
- keeping preprocessing steps manual and undocumented
- using a mapping package before confirming CRS and geometry validity
- assuming the package default is the right scientific choice
- treating package familiarity as a substitute for understanding the spatial problem

The lesson is pragmatic: the best package is the one that fits the task and preserves clarity, not necessarily the one with the most features.

## Key takeaways
- Modern R spatial epidemiology is modular rather than centered on one umbrella package.
- `sf` and `terra` are the current core tools for vector and raster handling.
- `tmap`, `leaflet`, and `mapview` serve different mapping purposes.
- `spdep` and `spatialreg` are central for dependence diagnostics and classical spatial modeling.
- Reproducible preprocessing is essential because spatial data-handling decisions shape the analytic result.

## Self-check questions
1. What is the main role of `sf` in a spatial workflow?
2. Why is `terra` important?
3. What is one difference between `tmap` and `leaflet`?
4. Which package family helps with spatial autocorrelation diagnostics?
5. Why should preprocessing scripts be explicit in spatial epidemiology?
6. Why is it risky to rely only on package defaults?

## Answer key
1. Handling vector spatial data such as points, lines, polygons, joins, and coordinate transformations.
2. Because it is the main modern package for raster data such as environmental surfaces and gridded covariates.
3. `tmap` is often used for thematic and publication-quality maps, while `leaflet` is commonly used for interactive maps.
4. `spdep` and related packages such as `spatialreg`.
5. Because CRS handling, joins, neighbor definitions, and extraction choices can change the result and need to be auditable and reproducible.
6. Because defaults may not match the epidemiologic question, data structure, or spatial scale of interest.

## Further reading
- [CRAN sf package](https://cran.r-project.org/package=sf)
- [CRAN terra package](https://cran.r-project.org/package=terra)
- [CRAN tmap package](https://cran.r-project.org/package=tmap)
- [CRAN spdep package](https://cran.r-project.org/package=spdep)

## Links to Metis library
- `knowledge/library/methods/gis-for-epidemiology.md`
- `knowledge/library/methods/data-management.md`
- `knowledge/library/methods/spatial-epidemiology.md`
