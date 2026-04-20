# A Practical Spatial Epi Workflow

## Learning objectives
- Move from raw data to a defensible spatial analysis plan.
- Link data cleaning, mapping, diagnostics, and modeling in a coherent sequence.
- Document key spatial decisions for reproducibility and critique.
- Keep the final product tied to a concrete public-health decision.

## Prerequisites
- The previous spatial lessons.

## Content

### Section 1: Start with the public-health question
The first step in spatial epidemiology is not opening GIS software. It is defining the decision problem.

Examples include:

- where should intensified surveillance be prioritized?
- are there unusual clusters that need field verification?
- which areas have poor facility access?
- how does ecological suitability relate to detected incidence?

The workflow should follow the question. A hotspot-screening workflow is not the same as a service-access workflow or a spatial etiologic model.

### Section 2: Assemble and audit the data
Most spatial problems start as data problems. Before mapping anything, assemble:

- case or event data
- denominator data
- administrative boundaries or point coordinates
- relevant environmental or service covariates
- metadata on dates, CRS, source quality, and completeness

Then audit them. Are IDs consistent? Are boundaries current for the time period? Are denominators aligned to the same spatial unit? Are coordinates plausible? Are missing values concentrated in specific areas?

Spatial analysis done on weakly audited data can become very persuasive and very wrong.

### Section 3: Verify geometry and CRS
Before analysis:

- inspect geometry type
- inspect coordinate reference systems
- reproject when needed
- plot layers together to confirm alignment

This is where many silent failures happen. If facility points and district polygons do not align, or if rasters and vector layers are in incompatible systems, later maps and models can be invalid even if no software error is thrown.

### Section 4: Build the first descriptive products
Once data are aligned, start with descriptive exploration.

Useful first products include:

- raw point maps
- choropleths of rates
- denominator maps
- facility-access maps
- simple time-stratified maps if the period matters

The goal at this stage is not to prove a mechanism. It is to understand what patterns exist, where data may be unstable, and where quality or denominator problems are obvious.

### Section 5: Diagnose instability and dependence
After the first descriptive maps, ask two questions.

1. Are the mapped rates unstable because of small populations or sparse counts?
2. Is there evidence of spatial dependence?

If instability is strong, smoothing may be appropriate. If spatial autocorrelation is present, later regression models may need to account for it rather than assume independence.

This stage links cartography to formal analysis.

### Section 6: Choose the analytic next step
The next analytic move depends on the operational question.

- If the goal is stable area comparison, smoothing or Bayesian disease mapping may be useful.
- If the goal is hotspot detection, a formal cluster method such as SaTScan may be appropriate.
- If the goal is understanding association with covariates, spatial regression or geostatistical approaches may be needed.
- If the goal is communication only, careful descriptive mapping may be enough.

This is why spatial epidemiology should be treated as a decision workflow, not a checklist of methods to apply in fixed order.

### Section 7: Worked example - post-elimination vigilance
Imagine a post-elimination surveillance programme wants to identify zones needing intensified vigilance.

A reasonable workflow might be:

1. assemble recent confirmed cases, population denominators, health-facility locations, and referral data
2. verify administrative codes and CRS
3. map crude case counts and crude rates
4. inspect whether small areas have unstable rates
5. smooth rates if needed
6. assess whether unusual clusters are present with a scan statistic
7. combine this with facility-access information and surveillance-performance indicators
8. use the combined evidence to prioritize zones for outreach, supervision, or refresher training

This is a more defensible workflow than jumping straight to a hotspot map from raw counts.

### Section 8: Document everything that affects interpretation
Spatial workflows require explicit documentation of choices such as:

- spatial unit
- denominator source
- CRS and reprojection decisions
- smoothing method
- neighbor definition
- cluster-detection parameters
- privacy protections for mapped points

Without this documentation, spatial outputs become difficult to reproduce and hard to critique.

### Section 9: Common mistakes
Several workflow mistakes recur often.

- starting with the map rather than the decision problem
- skipping data audit and CRS checks
- moving to advanced modeling before basic descriptive mapping
- failing to distinguish raw, standardized, and smoothed quantities
- omitting documentation of spatial parameters and preprocessing steps

The core habit is sequential discipline: define, audit, align, describe, diagnose, model, communicate.

## Key takeaways
- A spatial workflow should begin with a clear public-health question.
- Data audit, denominator checks, and CRS verification are essential early steps.
- Descriptive mapping should come before advanced cluster detection or spatial modeling.
- The right analytic next step depends on whether the goal is mapping, smoothing, cluster detection, explanation, or prediction.
- Reproducibility depends on documenting every important spatial choice.

## Self-check questions
1. What should be decided before opening GIS software?
2. Why are denominator checks essential before disease mapping?
3. Why should descriptive maps come before advanced modeling?
4. What kinds of choices must be documented in a spatial workflow?
5. Why might a hotspot map based on raw counts be misleading?
6. What is the advantage of integrating surveillance performance data into a spatial workflow?

## Answer key
1. The public-health question or decision the spatial analysis is meant to support.
2. Because without valid denominators, mapped differences may reflect population size rather than risk.
3. Because they reveal pattern, instability, and data problems that should shape later modeling choices.
4. Choices such as spatial unit, CRS, smoothing approach, neighborhood definition, cluster settings, and privacy protections.
5. Because raw counts may mainly reflect population size, service access, or reporting intensity rather than unusual underlying risk.
6. Because it helps distinguish true transmission patterns from artifacts of detection, reporting, or service structure.

## Further reading
- [Simple Features for R](https://r-spatial.github.io/sf/)
- [SaTScan home page](https://www.satscan.org/)
- [CRAN tmap package](https://cran.r-project.org/package=tmap)

## Links to Metis library
- `06_library/methods/spatial-epidemiology.md`
- `06_library/methods/gis-for-epidemiology.md`
- `06_library/methods/data-management.md`
