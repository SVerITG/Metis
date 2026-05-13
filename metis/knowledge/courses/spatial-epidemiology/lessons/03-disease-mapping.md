# Disease Mapping

## Learning objectives
- Create interpretable choropleth and point maps for epidemiologic data.
- Distinguish counts, crude rates, standardized rates, and smoothed estimates.
- Recognize small-number instability and why smoothing is often needed.
- Identify cartographic choices that can mislead interpretation.

## Prerequisites
- GIS basics.

## Content

### Section 1: Maps are analytic tools, not decoration
Disease maps are often the first spatial product a programme sees. They can summarize burden, suggest clustering, reveal data gaps, and support targeting. But they are also easy to misuse. A map can look authoritative while silently reflecting population size, boundary choices, or unstable small-area rates rather than true underlying risk.

That is why disease mapping requires the same discipline as any other epidemiologic analysis. You need to know what quantity is being mapped, what denominator supports it, and how much instability or smoothing is involved.

### Section 2: Counts versus rates
Raw case counts are often a poor basis for comparison across areas because counts naturally rise with population size. A district with more people may show more cases even if risk is lower.

For comparison across places, epidemiologic maps often need:

- crude rates
- age-standardized or otherwise standardized rates
- standardized morbidity or mortality ratios

The choice depends on the question. If you want to show workload for service planning, counts may matter. If you want to compare risk across areas, rates are usually more appropriate.

### Section 3: Small-number instability
One of the most important issues in disease mapping is the **small number problem**. Areas with small populations can have highly unstable crude rates. A tiny numerator change can produce a large apparent jump in the mapped rate.

This can create visually dramatic hotspots that are mostly random noise. Small-area mapping therefore needs careful interpretation, especially when denominators vary widely across space.

That is why smoothing methods are common in spatial epidemiology. They reduce instability by borrowing strength from neighboring areas or from the wider distribution of rates.

### Section 4: Smoothing and shrinkage
Smoothing does not reveal the hidden truth automatically. It is a modeling choice that trades local detail for stability.

Common approaches include:

- empirical Bayes smoothing
- Bayesian hierarchical disease mapping
- BYM or BYM2-type models for areal data

These methods are especially useful when the map is intended for interpretation or prioritization rather than as a raw display of observed counts. In small-area epidemiology, a smoothed map is often more informative than a crude-rate map, provided the smoothing method is documented clearly.

### Section 5: Worked example - HAT mapping
Imagine you map HAT cases by health zone using raw counts. Large zones with bigger populations stand out immediately. But this may mainly reflect more people, not greater underlying risk.

Now suppose you convert the map to incidence rates. Some smaller zones begin to stand out, but a few have highly unstable values because their populations are small and case numbers are low.

Finally, you apply a smoothing approach. The resulting map shows more stable focal patterns that may be more useful for prioritization and surveillance planning.

This sequence illustrates an important spatial-epidemiology habit: move from counts to rates to stability-aware mapping rather than stopping at the first choropleth.

### Section 6: Cartographic choices matter
Disease maps are shaped by design choices, including:

- classification scheme
- color palette
- legend scaling
- whether zero values are distinct
- whether missing data are shown clearly
- whether neighboring boundaries are emphasized or minimized

These choices affect interpretation. For example, quantile class breaks may exaggerate contrast even when absolute differences are small. Large-area polygons can visually dominate the page even when population is sparse. Poor color scaling can hide meaningful moderate-risk zones.

This is why cartography is not only about aesthetics. It is part of inference.

### Section 7: Point maps and confidentiality
Point maps can be powerful because they avoid some aggregation problems and show finer-scale clustering. But they also raise confidentiality concerns, especially for stigmatized or rare conditions.

Protective strategies include:

- aggregation to larger units
- spatial jittering
- masking or binning
- mapping at facility or village level rather than household level

Good spatial epidemiology balances analytic value with ethical data handling.

### Section 8: Common mistakes
Several mapping mistakes recur often.

- mapping counts when rates are the real quantity of interest
- comparing unstable crude rates without acknowledging denominator differences
- smoothing without documenting the method
- hiding missing data by coloring them like zeros
- letting the map imply certainty that the underlying data do not support

The practical lesson is simple: before publishing a map, ask what a reader is likely to infer and whether that inference is justified.

## Key takeaways
- Disease maps should reflect the epidemiologic question, not only the available geometry.
- Rates are usually more informative than counts when comparing risk across areas.
- Small-area crude rates can be unstable, so smoothing is often useful.
- Cartographic design choices influence interpretation and can mislead if made carelessly.
- Point maps can be analytically valuable but may require privacy protection.

## Self-check questions
1. Why can raw counts be misleading in disease mapping?
2. What is the small number problem?
3. Why might smoothing be useful in a choropleth map?
4. What is one risk of poor class-break choice in a disease map?
5. Why should missing data be displayed explicitly?
6. Why can point maps raise ethical concerns?

## Answer key
1. Because counts often reflect population size or reporting volume rather than underlying risk.
2. It is the instability of rates in small populations, where small numerator changes can create large apparent differences.
3. Because smoothing reduces random instability and can make area comparisons more interpretable.
4. It can exaggerate or hide differences and lead readers to overstate risk contrasts.
5. Because otherwise readers may mistake missing information for true zero values.
6. Because precise locations may reveal identifiable or sensitive information about patients or households.

## Further reading
- [CRAN tmap package](https://cran.r-project.org/package=tmap)
- [CRAN spdep package](https://cran.r-project.org/package=spdep)
- [OpenIntro Statistics](https://www.openintro.org/book/os/)

## Links to Metis library
- `knowledge/library/methods/spatial-epidemiology.md`
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/gis-for-epidemiology.md`
