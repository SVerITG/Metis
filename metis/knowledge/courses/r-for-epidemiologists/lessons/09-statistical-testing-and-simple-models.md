# Statistical Testing and Simple Models

## Learning objectives
- Run simple tests and models in R with appropriate caution.
- Explain why interpretation matters more than printing p-values.
- Recognize the limits of point-and-click statistical use.

## Prerequisites
- Common epidemiologic summaries in R.

## Content
R makes it easy to run t-tests, chi-square tests, linear regression, and logistic regression. The danger is false confidence: software can always produce an answer, but interpretation still depends on design, assumptions, coding, and context.

Analysts should therefore pair every model with questions about data structure, missingness, confounding, and whether the estimate answers the actual study question.

## Key takeaways
- Running a model is easier than interpreting it correctly.
- Statistical output must be tied back to study design and assumptions.
- Software does not replace methodological reasoning.

## Self-check questions
1. Why is software output not enough by itself?
2. What is one issue to check before trusting a model?
3. Why should p-values not dominate interpretation?
4. What is one benefit of scripting models in R?
5. How does study design affect interpretation?

## Answer key
1. Because validity depends on assumptions, coding, and design.
2. Missingness, confounding, outcome coding, or clustering.
3. Because effect size and uncertainty matter more than significance alone.
4. The analysis becomes transparent and reproducible.
5. Design determines what causal or descriptive claims are defensible.

## Further reading
- [R for Data Science](https://r4ds.hadley.nz/)
- [OpenIntro Statistics](https://www.openintro.org/book/os/)

## Links to Metis library
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/study-designs.md`
