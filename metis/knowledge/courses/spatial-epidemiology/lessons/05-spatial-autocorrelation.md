# Spatial Autocorrelation

## Learning objectives
- Explain why nearby observations may be more similar than distant observations.
- Interpret Moran's I and local indicators of spatial association at an introductory level.
- Recognize what residual spatial autocorrelation implies after regression.
- Understand why independence assumptions often fail in spatial epidemiology.

## Prerequisites
- Disease mapping.

## Content

### Section 1: What spatial autocorrelation means
Spatial autocorrelation means that observations close together in space tend to be more similar, or less similar, than would be expected under independence.

Positive spatial autocorrelation means neighboring areas resemble each other. Negative spatial autocorrelation means neighbors tend to be dissimilar. In epidemiology, positive autocorrelation is much more common because ecology, services, environment, and human movement are spatially structured.

This matters because many standard statistical methods assume independent observations. When strong spatial dependence is present, those assumptions can break down.

### Section 2: Why it happens
Spatial autocorrelation can arise for many reasons:

- environmental conditions vary smoothly across space
- vectors or reservoirs spread across neighboring areas
- nearby facilities share programme practices
- reporting quality clusters geographically
- social and transport networks connect nearby places

These processes mean that one area is often not statistically isolated from its neighbors. That is not an inconvenience to be ignored; it is often part of the epidemiologic process itself.

### Section 3: Global Moran's I
One widely used global measure is **Moran's I**. It summarizes whether similar values tend to occur near each other across the whole study area.

At a practical level:

- positive Moran's I suggests clustering of similar values
- values near zero suggest little overall spatial structure
- negative values suggest neighboring dissimilarity

Global Moran's I is useful as a first diagnostic, but it does not tell you where clustering occurs. It answers a whole-map question, not a local one.

### Section 4: Local indicators of spatial association
Local measures, often grouped under **LISA** or local Moran's I, identify where unusual spatial patterning is concentrated.

They can help detect:

- high-high areas, where high values cluster with high-value neighbors
- low-low areas, where low values cluster with low-value neighbors
- spatial outliers, such as high values surrounded by low values

This is useful for hotspot exploration, but local outputs should still be interpreted cautiously because many local tests are being evaluated at once.

### Section 5: Spatial weights matter
Measures of spatial autocorrelation depend on a **spatial weights matrix**, which defines which places are treated as neighbors.

Common choices include:

- shared boundaries such as queen or rook contiguity
- distance-based neighbors
- k-nearest neighbors

This matters because the answer can change depending on how "neighbor" is defined. A district-based areal dataset and a point-based village dataset may need different neighbor structures. As in other parts of spatial epidemiology, the analytic choice should reflect the substantive process.

### Section 6: Worked example - residual clustering after regression
Imagine you fit a district-level incidence model using rainfall, access to care, and vector habitat. The fitted coefficients look sensible, but residuals still show positive Moran's I.

What does that imply?

- the model may be missing spatially structured drivers
- the dependence structure has not been captured fully
- standard errors may be too optimistic if independence is still assumed

This is one of the main reasons spatial autocorrelation diagnostics matter after regression, not only before it.

### Section 7: Why residual spatial structure matters
Residual spatial autocorrelation often means that the model has not fully explained the spatial pattern. Possible reasons include:

- omitted environmental variables
- poorly specified nonlinear relationships
- neighborhood spillover effects
- measurement or reporting heterogeneity

The presence of residual spatial structure does not automatically tell you which spatial model to use next, but it does tell you the current model is incomplete in spatial terms.

### Section 8: Common mistakes
Several mistakes recur often.

- assuming independence because the data are aggregated
- using only a map and never checking formal dependence
- treating Moran's I as a causal measure
- ignoring the role of the spatial weights matrix
- stopping at a global test when the local pattern is the real operational question

The practical lesson is that spatial autocorrelation is both a descriptive finding and a modeling diagnostic.

## Key takeaways
- Spatial autocorrelation means nearby places are statistically related rather than independent.
- Positive spatial autocorrelation is common in epidemiology because risks, environments, and systems are spatially structured.
- Global Moran's I summarizes overall dependence, while local measures identify where clustering or spatial outliers occur.
- Results depend partly on how neighborhood structure is defined.
- Residual spatial autocorrelation after regression suggests that important spatial structure remains unmodeled.

## Self-check questions
1. What does positive spatial autocorrelation mean?
2. What is the difference between global Moran's I and local Moran's I?
3. Why does the spatial weights matrix matter?
4. Why might neighboring districts show similar incidence?
5. What does residual spatial autocorrelation suggest after a regression model?
6. Why is Moran's I not a causal explanation?

## Answer key
1. It means nearby areas tend to have similar values more often than expected under independence.
2. Global Moran's I summarizes overall spatial dependence across the whole study area, while local Moran's I identifies where local clustering or outliers occur.
3. Because it defines which areas count as neighbors, and different definitions can produce different dependence results.
4. Because they may share ecology, vectors, services, reporting systems, or connected human movement.
5. It suggests that important spatial pattern remains unaccounted for, such as omitted variables or spatial spillover.
6. Because it only describes spatial patterning, not the mechanism producing that pattern.

## Further reading
- [CRAN spdep package](https://cran.r-project.org/package=spdep)
- [CRAN spatialreg package](https://cran.r-project.org/package=spatialreg)
- [OpenIntro Statistics](https://www.openintro.org/book/os/)

## Links to Metis library
- `06_library/methods/spatial-epidemiology.md`
- `06_library/methods/biostatistics-essentials.md`
- `06_library/methods/gis-for-epidemiology.md`
