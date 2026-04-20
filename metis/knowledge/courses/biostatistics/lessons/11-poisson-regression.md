# Poisson Regression

## Learning objectives
- Explain when Poisson regression is appropriate for counts and rates.
- Use offsets correctly to compare rates across units with different exposure time or population size.
- Interpret incidence rate ratios from Poisson models.
- Recognize overdispersion and when alternatives such as negative binomial models may be needed.

## Prerequisites
- Probability distributions and multiple regression.

## Content

### Section 1: Why count models matter
Many epidemiologic outcomes are counts rather than continuous measurements or simple yes/no variables. Examples include:

- number of incident cases in a district
- number of hospital admissions per month
- number of relapses during follow-up
- number of deaths in a surveillance period

These outcomes often depend on how much population, person-time, or observation time is available. A district with twice the population might naturally have more cases even if the underlying rate is the same. Poisson regression helps model this kind of count data, especially when the scientific interest is in **rates**.

### Section 2: The basic Poisson model
Poisson regression models the logarithm of the expected count as a linear function of predictors:

\[
log(E[Y]) = \beta_0 + \beta_1X_1 + \cdots + \beta_kX_k
\]

If an offset is included to represent exposure time or population size, the model becomes a rate model rather than a raw count model.

Exponentiated coefficients are interpreted as **incidence rate ratios (IRRs)** when the offset is specified appropriately.

This makes Poisson regression especially useful when comparing event rates across groups, districts, or time periods.

### Section 3: What an offset does
An **offset** is a term included with its coefficient fixed at 1. It adjusts the model for different amounts of exposure, such as:

- person-time at risk
- population size
- observation period

For example, if district A has 100,000 people and district B has 20,000 people, comparing raw case counts alone is misleading. An offset allows the model to compare rates rather than unadjusted totals.

In practice, offsets are often written as the logarithm of person-time or population.

### Section 4: Worked example - district incidence rates
Imagine a programme models confirmed HAT case counts across districts. Predictors include:

- screening intensity
- distance to referral center
- district type

Each district has a different population size, so the model includes `log(population)` as an offset.

Suppose the incidence rate ratio for high screening intensity is `1.4`.

Interpretation:
- holding the other modeled variables constant, districts with higher screening intensity are estimated to have 1.4 times the rate of detected cases, relative to the comparison level

This is a rate interpretation, not a probability interpretation. That distinction matters for communication.

### Section 5: When Poisson regression works well
Poisson regression is most natural when:

- the outcome is a count
- events are relatively uncommon
- the observation window is well defined
- interest lies in event rates
- exposure time or population size differs across observations

It is widely used in infectious-disease epidemiology, surveillance, injury epidemiology, and health-services research.

The model also connects naturally to the Poisson distribution introduced earlier in the course.

### Section 6: Overdispersion
One of the most important practical problems is **overdispersion**, meaning the observed variance exceeds what the Poisson model expects.

This is common in real public-health data because counts may be influenced by:

- clustering
- unmeasured heterogeneity
- repeated outbreaks
- extra zeros
- inconsistent reporting systems

If overdispersion is ignored, standard errors may be too small and p-values too optimistic. Practical responses include:

- robust standard errors
- negative binomial regression
- better model specification

Checking overdispersion is therefore not optional.

### Section 7: Poisson versus logistic regression
Poisson regression and logistic regression answer different kinds of questions.

- logistic regression is usually for binary outcomes
- Poisson regression is for counts or rates

In some settings, modified Poisson approaches are also used to estimate relative risks for binary outcomes, but that is a special applied use, not the core logic of ordinary Poisson count modeling.

The model should follow the structure of the data and the target estimand, not analyst preference.

### Section 8: Common mistakes
Several mistakes recur often.

- modeling counts without accounting for different exposure times or population sizes
- forgetting the offset when comparing rates
- interpreting rate ratios as if they were odds ratios or risks
- ignoring overdispersion
- fitting a Poisson model when the data are dominated by excess zeros or strong clustering

The main habit to build is simple: ask whether you are modeling counts, rates, or probabilities, and choose the model accordingly.

## Key takeaways
- Poisson regression is designed for count outcomes and is especially useful for modeling rates.
- Offsets convert raw count models into rate comparisons by accounting for exposure time or population size.
- Exponentiated coefficients are usually interpreted as incidence rate ratios.
- Overdispersion is common in real epidemiologic data and must be checked.
- The correct model depends on the structure of the outcome and the scientific question.

## Self-check questions
1. What kind of outcome is Poisson regression primarily designed for?
2. What does an offset do in a Poisson model?
3. How should an incidence rate ratio be interpreted?
4. What is overdispersion?
5. Why can ignoring overdispersion be misleading?
6. Why is Poisson regression often preferable to a linear model for case counts?

## Answer key
1. Count outcomes, especially when the analysis is focused on event rates.
2. It adjusts for different amounts of exposure, such as person-time or population size, so the model compares rates rather than raw counts.
3. As the ratio of modeled event rates associated with a one-unit or category difference in a predictor, holding other variables constant.
4. It is the situation where the observed variance in the counts is greater than the Poisson model expects.
5. Because it can make standard errors too small and lead to overconfident inference.
6. Because counts are non-negative integers and often depend on exposure time or population size, which linear models handle poorly.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [CRAN MASS package](https://cran.r-project.org/package=MASS)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `06_library/methods/biostatistics-essentials.md`
- `06_library/methods/surveillance-systems.md`
- `06_library/methods/study-designs.md`
