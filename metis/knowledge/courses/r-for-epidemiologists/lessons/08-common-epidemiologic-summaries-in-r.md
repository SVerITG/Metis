# Common Epidemiologic Summaries in R

## Learning objectives
- Produce frequencies, proportions, rates, and grouped summaries in R.
- Explain why denominator discipline matters.
- Translate routine epidemiologic questions into codeable summaries.

## Prerequisites
- Exploratory data analysis and visualization.

## Content
Routine epidemiologic analysis often involves counts by time, place, and person; proportions by subgroup; and rates using appropriate denominators. R helps make these summaries reproducible and easy to update. The most important conceptual point is denominator discipline: proportions and rates mean little without clarity about who or what is being counted.

## Key takeaways
- Common epidemiologic summaries map well onto grouped code workflows.
- Denominators must be explicit.
- Reproducible summaries are easier to update and verify.

## Self-check questions
1. Why are denominators essential?
2. What is one common grouped summary in epidemiology?
3. Why is code useful for routine summaries?
4. What is one danger of unclear denominators?
5. Why do grouped summaries matter for surveillance?

## Answer key
1. Because they define what the count is relative to.
2. Case counts by district, age group, or month.
3. Because summaries can be rerun consistently after updates.
4. Misleading proportions or rates.
5. They show variation across time, place, and population.

## Further reading
- [dplyr documentation](https://dplyr.tidyverse.org/)
- [R for Data Science](https://r4ds.hadley.nz/)

## Links to Metis library
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/surveillance-systems.md`
