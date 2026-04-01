# Chi-Square and t-Tests

## Learning objectives
- Use chi-square tests for simple comparisons of categorical variables.
- Use t-tests for comparisons of means while checking core assumptions.
- Interpret test results alongside effect size and confidence intervals.
- Recognize when simple tests are insufficient because of clustering, confounding, or non-standard data structure.

## Prerequisites
- Hypothesis testing.

## Content

### Section 1: Why these tests matter
Chi-square tests and t-tests are among the most common introductory statistical tools because they answer simple and frequent questions.

- Are proportions different between groups?
- Are means different between groups?

These tests are useful because they give a clear first pass at a comparison. They are also limited because real epidemiologic data often involve clustering, confounding, repeated measures, unequal variances, or non-normality. So these tests are important to understand, but they should not be treated as universal solutions.

### Section 2: The chi-square test
The **chi-square test** is commonly used to assess whether categorical variables are associated. A classic example is a two-by-two table comparing exposure status and outcome status.

The test compares the observed counts in each cell with the counts that would be expected if the variables were independent. If the observed and expected counts differ more than would be likely under the null model, the chi-square statistic becomes larger and the p-value becomes smaller.

This is especially useful for:

- comparing proportions across exposure groups
- initial analyses of contingency tables
- outbreak tables with exposed/unexposed by ill/well status

But the chi-square test does not give effect size by itself. A p-value alone does not tell you whether the difference is large, small, or practically important. That is why proportions, risk ratios, odds ratios, or risk differences should usually accompany the test.

### Section 3: When Fisher's exact test is better
The chi-square approximation works best when expected cell counts are not too small. With sparse data, especially in small outbreak studies or rare outcomes, the approximation can become unreliable.

In those settings, **Fisher's exact test** is often preferred because it does not rely on the same large-sample approximation. The lesson is practical: a simple two-by-two table may still be analyzable, but the appropriate test depends on the data structure.

### Section 4: The t-test
The **t-test** is used to compare means. The most familiar version compares the mean of a continuous outcome between two groups.

Common variants include:

- **one-sample t-test:** compares one sample mean with a reference value
- **two-sample t-test:** compares means from two independent groups
- **paired t-test:** compares two measurements taken on the same individuals or matched units

For example, a paired t-test may be appropriate for blood pressure measured in the same participants before and after an intervention, while a two-sample t-test may be appropriate for comparing mean age between cases and controls.

### Section 5: Assumptions behind the t-test
The t-test is not assumption-free. The main assumptions are:

- the observations are appropriately independent
- the variable is approximately normally distributed within groups, especially in smaller samples
- for the classic two-sample version, group variances are reasonably similar

In practice, mild departures from normality are often acceptable in moderate or large samples, but strong skewness, heavy tails, or extreme outliers can make the test misleading. When variances differ substantially, a Welch t-test is often better than the equal-variance version.

This is why exploratory plots still matter even for "simple" tests.

### Section 6: Worked example - chi-square test in a field survey
Imagine an evaluation compares seropositivity in two sets of villages.

- intervention villages: 18 positive out of 120
- comparison villages: 33 positive out of 120

The proportions are:

- intervention: `15%`
- comparison: `27.5%`

A chi-square test can assess whether the observed difference is larger than expected under a null model of no association. But interpretation should not stop there. The comparison should also report the absolute difference and, if appropriate, a risk ratio or prevalence ratio.

This is important because a statistically detectable difference still needs to be interpreted in epidemiologic terms.

### Section 7: Worked example - t-test for mean difference
Imagine a programme compares mean delay to diagnosis between two districts.

- district A mean delay: 24 days
- district B mean delay: 31 days

A two-sample t-test can ask whether that difference is compatible with chance under the null model. But the better interpretation includes:

- the estimated mean difference
- a confidence interval
- whether delay data are skewed
- whether observations are independent

If the distribution is highly skewed or the observations are clustered by facility, a simple t-test may not be the most appropriate final analysis.

### Section 8: Why simple tests often give way to regression
Chi-square tests and t-tests are closely related to regression models.

- chi-square logic connects to logistic and log-linear models
- t-test logic connects to linear regression

Regression generalizes the same comparison ideas while allowing adjustment for covariates, interaction terms, clustering, repeated measurements, and more flexible outcome structures.

That is why simple tests are often the beginning of the analysis, not the end. They help you understand the data and communicate basic comparisons before more complex modeling is used.

### Section 9: Common mistakes
Several mistakes recur often.

- Reporting only the p-value without effect size
- Using the chi-square test with sparse tables when Fisher's exact test would be better
- Applying a t-test to clearly skewed or highly clustered data without checking assumptions
- Treating non-significant results as proof of no difference
- Ignoring the design structure of field data, such as clustering by village or facility

Simple tools are valuable, but they work best when the user stays aware of their assumptions and limits.

## Key takeaways
- Chi-square tests are useful for simple comparisons of categorical variables, while t-tests are useful for mean comparisons.
- Both tests answer narrow questions and should usually be interpreted alongside effect sizes and confidence intervals.
- Assumptions about independence, variance, cell counts, and distribution shape matter.
- Fisher's exact test is often preferable to chi-square in sparse tables.
- Regression models often extend the same logic more flexibly when data structures become more complex.

## Self-check questions
1. What question does a chi-square test address?
2. Why is a p-value from a chi-square test not enough on its own?
3. When might Fisher's exact test be preferable?
4. What is the difference between an independent two-sample t-test and a paired t-test?
5. Why can clustered field data make a simple t-test misleading?
6. How are t-tests and chi-square tests related to later regression models?

## Answer key
1. Whether the observed categorical counts differ from what would be expected under a null model of independence or no association.
2. Because it does not describe the magnitude or practical importance of the difference.
3. When expected cell counts are small and the chi-square approximation may be unreliable.
4. The two-sample t-test compares means between independent groups, while the paired t-test compares linked or repeated measurements on the same units.
5. Because observations within villages or facilities may not be independent, which can distort standard errors and p-values.
6. They represent simpler forms of comparison that linear, logistic, and related regression models generalize with more flexibility.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Khan Academy hypothesis tests](https://www.khanacademy.org/math/statistics-probability)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `06_library/methods/biostatistics-essentials.md`
- `06_library/methods/study-designs.md`
- `06_library/methods/causal-inference.md`
