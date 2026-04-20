# Cleaning and Transforming Data with dplyr

## Learning objectives
- Use core dplyr verbs for routine epidemiologic data work.
- Explain why transformation steps should remain readable.
- Recognize how grouped summaries support analytic thinking.

## Prerequisites
- Importing data.

## Content
The `dplyr` workflow centers on verbs such as `filter()`, `select()`, `mutate()`, `arrange()`, `group_by()`, and `summarise()`. These functions allow analysts to clean and reshape data in a readable sequence. The main advantage is clarity: each step should express one transformation.

For epidemiologists, this is especially useful for constructing age bands, collapsing categories, calculating grouped counts, or creating analysis-ready indicators from surveillance data.

## Key takeaways
- `dplyr` makes transformation steps readable and explicit.
- Grouped summaries are central to epidemiologic description.
- Clear stepwise code is easier to audit than dense one-line transformations.

## Self-check questions
1. What does `filter()` do?
2. What is one use of `mutate()`?
3. Why is readable transformation code valuable?
4. What does `group_by()` enable?
5. Why should transformations be explicit?

## Answer key
1. It keeps rows that meet specified conditions.
2. Creating or recoding variables.
3. Because it makes logic easier to inspect, debug, and share.
4. Grouped summaries across categories such as district or sex.
5. So analytical decisions remain transparent and reproducible.

## Further reading
- [dplyr documentation](https://dplyr.tidyverse.org/)
- [R for Data Science](https://r4ds.hadley.nz/)

## Links to Metis library
- `06_library/methods/data-management.md`
- `06_library/methods/biostatistics-essentials.md`
