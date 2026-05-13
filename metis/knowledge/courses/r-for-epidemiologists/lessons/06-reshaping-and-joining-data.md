# Reshaping and Joining Data

## Learning objectives
- Explain when data should be reshaped between long and wide forms.
- Use joins carefully to combine related datasets.
- Recognize common merge errors in epidemiologic workflows.

## Prerequisites
- Cleaning and transforming data with dplyr.

## Content
Analysts often need to reshape data for plotting, tabulation, or modeling. Long data are often easier for visualization and grouped analysis, while wide data may be useful for some reporting tasks. Joins are used to merge datasets such as case records and laboratory results or facility lists and reporting indicators.

Join mistakes are common and dangerous. Duplicate keys, mismatched identifiers, and silent row inflation can all distort analysis. Every join should therefore be checked.

## Key takeaways
- Long and wide forms serve different analytic needs.
- Joins require deliberate key checking.
- Merge errors can silently distort results.

## Self-check questions
1. Why might long format be useful?
2. What is one common risk in joins?
3. Why should join results be checked?
4. What kind of datasets are often joined in epidemiology?
5. Why can row inflation be dangerous?

## Answer key
1. It often works better for grouped summaries and plotting.
2. Duplicate or mismatched keys.
3. Because merge errors may silently change counts and denominators.
4. Case records, laboratory data, facility lists, or population denominators.
5. It can create false counts and misleading estimates.

## Further reading
- [tidyr documentation](https://tidyr.tidyverse.org/)
- [dplyr documentation](https://dplyr.tidyverse.org/)

## Links to Metis library
- `knowledge/library/methods/data-management.md`
