# A Practical R Workflow for an Epidemiology Project

## Learning objectives
- Summarize an end-to-end R workflow for a typical epidemiology project.
- Connect importing, cleaning, analysis, and reporting into one pipeline.
- Identify where quality checks should occur.

## Prerequisites
- All previous R for Epidemiologists lessons.

## Content
A practical epidemiology workflow in R usually follows the same broad sequence: define a project folder, import raw data, inspect and document types, clean and recode variables, join supporting files, generate descriptive summaries, fit simple models if needed, and output figures or tables through scripted reporting.

Quality checks should appear throughout: after import, after joins, before modeling, and before final output. The main lesson is that R is most useful when it supports a stable workflow rather than disconnected commands.

## Key takeaways
- End-to-end workflow thinking matters more than isolated commands.
- Quality checks belong throughout the pipeline.
- Reproducible reporting is the natural endpoint of a good analysis workflow.

## Self-check questions
1. What is the first step in a practical R workflow?
2. Why should joins be checked before modeling?
3. Where should quality checks occur?
4. What is the endpoint of a strong R workflow?
5. Why is workflow thinking more important than memorizing commands?

## Answer key
1. Set up a stable project and import data carefully.
2. Because merge errors can distort the analysis dataset.
3. At import, cleaning, joining, analysis, and reporting stages.
4. Reproducible outputs such as reports, tables, and figures.
5. Because reliable analysis depends on process, not isolated syntax tricks.

## Further reading
- [R for Data Science](https://r4ds.hadley.nz/)
- [Quarto documentation](https://quarto.org/)

## Links to Metis library
- `06_library/methods/data-management.md`
- `06_library/methods/biostatistics-essentials.md`
- `06_library/methods/writing-for-journals.md`
