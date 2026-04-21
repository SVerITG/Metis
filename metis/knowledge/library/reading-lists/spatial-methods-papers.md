---
title: "Spatial Methods Papers"
domain: "reading-lists"
tags:
  - reading-list
  - spatial
  - methods
  - GIS
  - disease-mapping
related:
  - "methods/spatial-epidemiology.md"
  - "methods/gis-for-epidemiology.md"
phd_relevance: "high"
status: "current"
updated: "2026-04-21"
---
# Spatial Methods Papers

> Core papers for cluster detection, spatial autocorrelation, disease mapping, and practical workflows that keep geography central to public health analysis.

---

## Top 5 Picks

1. **Moran (1950)** – The origin of Moran's I and the first formal global spatial autocorrelation statistic; still the diagnostic for “is there structure?” in spatial epidemiology.
2. **Anselin (1995)** – Introduced Local Indicators of Spatial Association (LISA), giving analysts a consistent way to find hot spots and spatial outliers.
3. **Kulldorff (1997)** – The spatial scan statistic defined the likelihood-based workflow behind SaTScan and cluster-alert systems worldwide.
4. **Besag, York & Mollié (1991)** – BYM laid the foundation for Bayesian disease-map smoothing and still anchors most areal health mapping workflows.
5. **Lawson (2001)** – The Wiley handbook that compiles spatial epidemiology methods, modeling, and applied case studies; still the go-to reference for newcomers.

---

## Annotated bibliography

### Foundational theory

1. **Moran (1950).** *Notes on continuous stochastic phenomena.* *Biometrika.* https://doi.org/10.1093/biomet/37.1-2.17  
   Why it matters: Defines Moran's I, the simplest global test for clustering and a benchmark for more complex indicators.

2. **Getis & Ord (1992).** *Distance statistics for spatial association.* *Geographical Analysis.* https://doi.org/10.1111/j.1538-4632.1992.tb00261.x  
   Why it matters: The Getis-Ord Gi* statistic is still widely used to detect local hot spots.

3. **Anselin (1995).** *Local Indicators of Spatial Association (LISA).* *Geographical Analysis.* https://doi.org/10.1111/j.1538-4632.1995.tb00338.x  
   Why it matters: Introduces a suite of local diagnostics for identifying clusters and spatial outliers.

### Disease mapping and hierarchical models

4. **Besag, York & Mollié (1991).** *Bayesian image restoration.* *Ann Inst Stat Math.* https://doi.org/10.1007/BF00116466  
   Why it matters: The BYM model is the default smoothing framework for areal disease rates.

5. **Marshall (1991).** *Review of spatial methods in disease.* *JRSS A.* https://doi.org/10.2307/2983154  
   Why it matters: Broad review showing how different methods answer public health mapping questions.

6. **Waller et al. (1997).** *Hierarchical spatio-temporal mapping.* *JASA.* https://doi.org/10.1080/01621459.1997.10474012  
   Why it matters: Early demonstration of combining spatial and temporal random effects.

7. **Riebler et al. (2016).** *BYM2 spatial model with scaling.* *Stat Methods Med Res.* https://doi.org/10.1177/0962280216660421  
   Why it matters: Provides interpretable priors for BYM models, improving modern disease mapping.

### Scan statistics and cluster detection

8. **Kulldorff & Nagarwalla (1995).** *Spatial disease clusters.* *Statistics in Medicine.* https://doi.org/10.1002/sim.4780140809  
   Why it matters: Precursor to SaTScan and the foundational likelihood-based cluster detection approach.

9. **Kulldorff (1997).** *A spatial scan statistic.* *Communications in Statistics.* https://doi.org/10.1080/03610929708831995  
   Why it matters: The canonical scan statistic powering SaTScan.

10. **Kulldorff et al. (2006).** *Elliptic spatial scan statistic.* *Statistics in Medicine.* https://doi.org/10.1002/sim.2490  
    Why it matters: Allows elongated clusters beyond circular windows.

11. **Tango & Takahashi (2005).** *Fexible spatial scan statistic.* *IJHG.* https://doi.org/10.1186/1476-072X-4-11  
    Why it matters: Detects irregular shapes without inflating false positives.

12. **Takahashi et al. (2008).** *Flexible space-time scan.* *IJHG.* https://doi.org/10.1186/1476-072X-7-14  
    Why it matters: Space-time extension critical for outbreak detection.

13. **Tango & Takahashi (2012).** *Restricted likelihood for flexible clusters.* *Statistics in Medicine.* https://doi.org/10.1002/sim.5478  
    Why it matters: Practical refinement for complex cluster detection.

### Point-pattern and practical applications

14. **Ripley (1977).** *Modelling spatial patterns.* *JRSS B.* https://doi.org/10.1111/j.2517-6161.1977.tb01615.x  
    Why it matters: Groundwork for point-pattern models beyond aggregated maps.

15. **Lawson (2001).** *Statistical Methods in Spatial Epidemiology.* Wiley. https://doi.org/10.1002/9780470013649  
    Why it matters: Comprehensive handbook uniting theory and public health practice.

16. **Moraga (2020).** *Geospatial Health Data: Modeling with R-INLA and Shiny.* CRC Press. https://doi.org/10.1201/9780429341823  
    Why it matters: Practical guide to combining INLA models with interactive apps.

17. **Baddeley, Rubak & Turner (2015).** *Spatial Point Patterns with R.* CRC Press. https://doi.org/10.1201/b19708  
    Why it matters: Essential for point-pattern modeling and intensity estimation.

---

## 2024-2026 highlights

1. **Malaria Atlas Project (MAP) 2024 release.** Updated high-resolution malaria risk surfaces that underpin district-level intervention planning. https://malariaatlas.org  
2. **WHO Spatial Planning for Health Guidance (2025).** Emphasizes geospatial equity, integrated GIS layers, and standard metadata for disease elimination portfolios. https://www.who.int/geospatial  
3. **WHO PHI Framework (2025).** The Public Health Intelligence framework now mandates explicit geospatial dashboards for early detection. https://www.who.int/teams/emergency-intelligence/public-health-intelligence  
4. **SaTScan 10 streaming scan adaptation (2024).** Introduces faster computation for near-real-time cluster detection, critical for increasingly rapid outbreak surveillance. https://www.satscan.org  
5. **Lancet Digital Health (2024) review on GIS-powered pandemic preparedness.** Highlights modular spatial data stacks and geospatial AI for emerging disease detection. https://www.thelancet.com/journals/landig/issue/current  

---

## Suggested reading order

1. Moran → Getis/Ord → Anselin.  
2. BYM → Riebler.  
3. Kulldorff → Tango/Takahashi.  
4. Lawson/Moraga → Baddeley et al.  

---

## Related Metis links

- `06_library/methods/spatial-epidemiology.md`  
- `06_library/methods/gis-for-epidemiology.md`  
- `06_library/courses/spatial-epidemiology/`

---

*Curated: 2026-03-30*
