# Importing Data

## Learning objectives
- Import common file types into R safely.
- Explain why import checks are part of data quality.
- Recognize common encoding, date, and type problems.

## Prerequisites
- Objects, vectors, data frames, and tibbles.

## Content
Import is not a trivial first step. Analysts should always check row counts, variable names, types, date parsing, and missing-value handling after loading data. CSV and Excel imports often contain silent problems such as numeric IDs converted to numbers, dates guessed incorrectly, or category labels with inconsistent spelling.

A good habit is to import, inspect, and document immediately rather than assuming the file is analysis-ready.

## Key takeaways
- Import is part of quality control.
- Type guessing and date parsing often need checking.
- Early inspection prevents downstream analytic errors.

## Self-check questions
1. Why should import be checked immediately?
2. What is one common date problem during import?
3. Why can IDs be mishandled?
4. What should be checked after loading a file?
5. Why is import documentation useful?

## Answer key
1. Because silent import errors can affect every later step.
2. Dates may be parsed incorrectly or as text.
3. Leading zeros may be dropped or numeric conversion may mislead.
4. Row count, column names, types, missingness, and sample values.
5. It makes data provenance and troubleshooting clearer.

## Further reading
- [readr documentation](https://readr.tidyverse.org/)
- [R for Data Science](https://r4ds.hadley.nz/)

## Links to Metis library
- `knowledge/library/methods/data-management.md`
