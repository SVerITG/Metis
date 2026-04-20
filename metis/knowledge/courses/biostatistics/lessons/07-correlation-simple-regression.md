# Correlation and Simple Regression

## Learning objectives
- Distinguish correlation, prediction, and causation.
- Interpret slope, intercept, fitted values, and residuals in simple linear regression.
- Recognize how outliers, nonlinearity, and confounding can distort simple associations.
- Use plots to support interpretation rather than relying on one summary number.

## Prerequisites
- Descriptive statistics and hypothesis testing.

## Content

### Section 1: Why this topic matters
Researchers often start by asking whether two quantitative variables move together. Does screening intensity rise with case detection? Does rainfall track vector density? Does diagnostic delay rise with distance to facility?

Correlation and simple regression are common first tools for these questions. They are useful because they summarize relationships compactly. They are also dangerous when readers jump from association to explanation without checking structure, scale, and causality.

### Section 2: Correlation
Correlation measures the strength and direction of linear association between two variables. The most familiar version is the Pearson correlation coefficient, which ranges from `-1` to `1`.

- values near `1` indicate strong positive linear association
- values near `-1` indicate strong negative linear association
- values near `0` indicate weak or no linear association

Correlation is attractive because it is easy to compute and easy to report. But it has major limitations:

- it does not show causality
- it is sensitive to outliers
- it only summarizes linear association
- it does not adjust for confounding

That is why a scatterplot should usually come before the correlation coefficient, not after it.

### Section 3: Simple linear regression
Simple linear regression models the expected value of an outcome `Y` as a function of one predictor `X`.

The basic form is:

\[
Y = \beta_0 + \beta_1X + \epsilon
\]

where:

- `\beta_0` is the intercept
- `\beta_1` is the slope
- `\epsilon` represents unexplained variation

The **slope** tells you the expected change in the outcome for a one-unit increase in the predictor, according to the fitted model. The **intercept** is the expected outcome when the predictor equals zero, though that may or may not be substantively meaningful.

Regression gives more than a correlation coefficient because it provides a directional model, predicted values, and residuals.

### Section 4: Association is not causation
Simple regression is often mistaken for a causal model. It is not. A regression line describes an association conditional on the form of the model. It does not by itself establish that changing `X` would change `Y`.

Several alternative explanations may exist:

- confounding by a third variable
- reverse causation
- selection bias
- shared time trends
- ecological structure

For example, a positive association between screening intensity and case detection may reflect better programme infrastructure, higher underlying risk, or the fact that areas with more known cases are targeted for more screening. The fitted slope alone does not resolve those possibilities.

### Section 5: Worked example - district screening and case detection
Imagine ten districts report:

- screening intensity per 1,000 population
- confirmed cases detected per 100,000 population

A scatterplot shows that districts with higher screening intensity also tend to have higher detected case rates. A simple regression estimates that every additional 10 people screened per 1,000 population is associated with 1.5 more confirmed cases per 100,000.

This may be useful descriptively, but the interpretation requires care. Districts with more screening may already be districts with higher baseline transmission, better access to laboratories, or stronger surveillance. The model describes an observed association. It does not yet identify the causal effect of screening intensity.

### Section 6: Residuals and model checking
Residuals are the differences between observed outcomes and model-predicted outcomes. They matter because they show what the line is failing to capture.

Residual checks can reveal:

- nonlinearity
- unequal variance across the range of `X`
- outliers
- influential observations

If one district has unusually high case detection because of a focal outbreak or referral bias, that single point may strongly shape the fitted slope. Looking only at the coefficient without inspecting the plot can be misleading.

### Section 7: When simple regression is useful
Simple regression is still valuable when used appropriately. It works well for:

- initial exploration of relationships
- describing a linear trend
- generating hypotheses
- building intuition before moving to multivariable models

It is also a good teaching bridge to more complex regression methods. Many ideas introduced here, such as coefficients, residuals, fitted values, and model diagnostics, carry forward into multiple regression, logistic regression, and other generalized models.

### Section 8: Common mistakes
Several mistakes recur often.

- reporting a strong correlation as if it proves causality
- ignoring outliers that drive the association
- fitting a straight line to a clearly curved relationship
- interpreting the intercept even when zero is not meaningful
- assuming the slope is stable across all subgroups

A disciplined workflow is simple:

1. inspect the scatterplot
2. summarize the association
3. inspect residuals and influential points
4. ask whether a linear model is reasonable
5. separate description from causal interpretation

## Key takeaways
- Correlation summarizes linear association, but it does not prove causality.
- Simple linear regression models the expected outcome as a function of one predictor and provides interpretable coefficients.
- The slope represents the expected change in outcome per one-unit increase in the predictor under the fitted model.
- Scatterplots and residual checks are essential because outliers and nonlinearity can distort interpretation.
- Simple regression is often a useful starting point, but epidemiologic interpretation still requires attention to confounding and study design.

## Self-check questions
1. What does a Pearson correlation coefficient summarize?
2. Why can a strong correlation still be non-causal?
3. What does the slope in simple linear regression represent?
4. Why should you inspect a scatterplot before reporting a correlation?
5. What do residuals tell you?
6. Why might a regression between screening intensity and case detection be hard to interpret causally?

## Answer key
1. The strength and direction of linear association between two variables.
2. Because shared causes, reverse causation, bias, or common time trends can produce an association without a direct causal effect.
3. The expected change in the outcome for a one-unit increase in the predictor according to the fitted linear model.
4. Because the same correlation can arise from very different patterns, and outliers or curvature may make the summary misleading.
5. They show the gap between observed and predicted values and help diagnose nonlinearity, unequal variance, and influential observations.
6. Because higher screening may occur in districts with higher baseline risk, stronger systems, or targeted programme activity, so confounding and reverse causation are plausible.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Khan Academy linear regression](https://www.khanacademy.org/math/statistics-probability/describing-relationships-quantitative-data)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `06_library/methods/biostatistics-essentials.md`
- `06_library/methods/causal-inference.md`
- `06_library/methods/study-designs.md`
