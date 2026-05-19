# Multiple Regression

## Learning objectives
- Interpret adjusted coefficients in multivariable models.
- Explain why multiple predictors are used for confounder control and joint description.
- Recognize common problems such as collinearity, overfitting, and poor model specification.
- Use model building as a way to answer a clear question rather than as an automatic variable-filtering exercise.

## Prerequisites
- Simple regression.

## Content

### Section 1: Why move beyond one predictor
Simple regression is useful, but real epidemiologic questions rarely involve only one predictor. Age, sex, district, season, diagnostic access, and socioeconomic conditions may all matter at once. Multiple regression allows analysts to model an outcome as a function of several predictors simultaneously.

This can be useful for at least three reasons:

- to control measured confounding
- to estimate associations while holding other variables constant
- to improve prediction by incorporating several relevant predictors

These goals overlap, but they are not identical. A model built for causal interpretation may differ from one built for prediction. Good practice starts by deciding which goal matters most.

### Section 2: What an adjusted coefficient means
In a multiple regression model, a coefficient usually represents the expected change in the outcome associated with a one-unit change in a predictor, **holding the other modeled variables constant**.

That phrase matters. It means the coefficient is conditional on the other terms in the model. If the adjustment set changes, the coefficient may change too. This is why "the effect of X" is not a fixed number independent of modeling choices.

Adjusted coefficients are often useful because they compare groups more fairly than crude comparisons. But they are only as meaningful as the variables included, the assumptions made, and the quality of measurement.

### Section 3: Confounder control is not magic
Multiple regression is frequently used to control for confounding, but it does not eliminate all bias.

It can only control variables that are:

- measured
- modeled appropriately
- conceptually relevant

If key confounders are unmeasured, poorly measured, or modeled in the wrong functional form, residual confounding remains possible. Regression is therefore a tool for adjustment, not a guarantee of causal truth.

This is why substantive reasoning, DAG thinking, and study design still matter.

### Section 4: Model specification
Model specification refers to how the relationship is written into the model. Important choices include:

- which predictors to include
- whether continuous variables are modeled linearly
- whether interaction terms are needed
- whether transformations or nonlinear terms are appropriate

Bad specification can distort interpretation. For example, forcing age into a straight-line relationship may be inappropriate if risk rises sharply only after a certain threshold. Similarly, omitting an interaction can hide important subgroup differences.

The key lesson is that regression is not just computation. It is a set of assumptions written into an equation.

### Section 5: Collinearity
Collinearity occurs when predictors are strongly correlated with each other. This can make coefficient estimates unstable and difficult to interpret.

Examples in epidemiology include:

- poverty and remoteness
- altitude and temperature
- age and years since diagnosis in certain datasets

Collinearity does not always make prediction impossible, but it can inflate uncertainty and make it hard to separate the individual role of related predictors. This is one reason coefficients sometimes change direction or become imprecise when multiple related variables are entered together.

### Section 6: Worked example - hemoglobin and infection status
Imagine an analyst studies hemoglobin level as the outcome and infection status as the main predictor of interest. A crude comparison shows lower hemoglobin among infected participants.

A multiple regression model then adjusts for:

- age
- sex
- district
- pregnancy status

After adjustment, the coefficient for infection becomes smaller but remains negative. That suggests part of the crude association was explained by differences in participant composition, but an adjusted association still remains.

This is a more informative result than the crude mean difference alone. But it still does not prove causality. The interpretation depends on whether the adjustment set was appropriate and whether important confounders were omitted.

### Section 7: Overfitting and sample size
Models with too many predictors relative to the amount of information in the data can overfit. Overfitting means the model captures random noise or idiosyncrasies of the sample rather than stable patterns that generalize.

This is especially risky when:

- the sample is small
- the outcome is rare
- many candidate predictors are tested
- variable selection is driven by repeated searching

An overfit model may look excellent in the original dataset and perform poorly elsewhere. That is why restraint and pre-specification matter.

### Section 8: Why automatic stepwise selection is risky
Automatic stepwise procedures are tempting because they promise an easy route to a "final model." But they can produce unstable, hard-to-interpret results and encourage p-value chasing rather than question-driven analysis.

Variables should usually be included because they are:

- part of a confounding structure
- substantively important predictors
- necessary design variables
- planned interaction terms

Model building is stronger when it follows a scientific rationale rather than an algorithm that happens to keep or drop variables.

### Section 9: Diagnostics and interpretation
Useful checks in multiple regression include:

- residual plots
- leverage and influence checks
- collinearity diagnostics such as VIF
- comparison of crude and adjusted estimates
- inspection of whether coefficients are plausible and stable

The analyst should also ask whether the model answers the intended question. A technically correct model can still be unhelpful if it is answering the wrong question or using an incoherent adjustment set.

## Key takeaways
- Multiple regression extends simple regression by modeling several predictors at once.
- Adjusted coefficients describe conditional associations given the other variables in the model.
- Regression can help control measured confounding, but it does not solve unmeasured bias or poor design.
- Model specification, collinearity, and overfitting are central interpretation issues.
- Good model building follows a substantive question and causal or predictive logic, not automatic selection alone.

## Self-check questions
1. What does an adjusted coefficient mean in a multiple regression model?
2. Why can multiple regression reduce confounding but not eliminate it completely?
3. What is collinearity, and why can it be a problem?
4. What is overfitting?
5. Why is automatic stepwise selection often criticized?
6. Why should crude and adjusted estimates be compared during interpretation?

## Answer key
1. It represents the association between a predictor and the outcome conditional on the other variables included in the model.
2. Because it can only adjust for measured and appropriately modeled variables, not for omitted or badly measured confounders.
3. It is strong correlation among predictors, which can make coefficients unstable and hard to interpret separately.
4. It is fitting a model so closely to sample-specific noise that performance or interpretation does not generalize well.
5. Because it can produce unstable models, overemphasize p-values, and disconnect model structure from the substantive question.
6. Because the comparison can show how much adjustment changes the estimate and whether confounding or model dependence may be important.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Causal Inference: What If](https://miguelhernan.org/whatifbook)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
