# Logistic Regression

## Learning objectives
- Explain why logistic regression is used for binary outcomes.
- Interpret coefficients, odds, and adjusted odds ratios carefully.
- Recognize when odds ratios are useful and when they are hard to communicate.
- Understand common pitfalls such as non-collapsibility, common outcomes, and overadjustment.

## Prerequisites
- Multiple regression.

## Content

### Section 1: Why logistic regression exists
Many epidemiologic outcomes are binary: disease versus no disease, treatment uptake versus non-uptake, positive versus negative test, dead versus alive. Standard linear regression is usually not ideal for such outcomes because fitted values can fall below 0 or above 1 and because the relationship between predictors and probability is often not linear.

Logistic regression solves this by modeling the **log-odds** of the outcome rather than the probability directly.

This makes it one of the most widely used models in epidemiology, clinical research, and public-health analysis.

### Section 2: Odds and the logit link
Before interpreting logistic regression, you need to be clear on odds.

If the probability of an event is `p`, then the odds are:

\[
\frac{p}{1-p}
\]

The logistic model uses the **logit link**:

\[
log\left(\frac{p}{1-p}\right) = \beta_0 + \beta_1X_1 + \cdots + \beta_kX_k
\]

Each coefficient represents a change in the log-odds associated with a one-unit change in the predictor, holding other variables constant. Exponentiating a coefficient gives an **odds ratio**.

### Section 3: Interpreting odds ratios
An odds ratio above `1` indicates higher odds of the outcome; below `1` indicates lower odds. In case-control studies, logistic regression fits naturally because the odds ratio is the core association measure. In many cross-sectional and cohort-type analyses, logistic regression is also used because it is flexible and widely available.

But odds ratios are frequently misread as risk ratios. When the outcome is rare, the odds ratio may approximate the risk ratio reasonably well. When the outcome is common, the odds ratio can exaggerate the perceived strength of association.

That is why logistic regression is statistically convenient but sometimes communicatively awkward.

### Section 4: Worked example - passive case detection
Imagine a programme analyzes predictors of passive case detection among people identified through multiple channels. The binary outcome is whether the case was passively detected (`yes/no`). Predictors include age, sex, district, and previous screening exposure.

Suppose the adjusted odds ratio for prior screening exposure is `1.8`.

Interpretation:
- Holding the other variables constant, the odds of passive case detection are estimated to be 1.8 times as high among those with prior screening exposure.

That is the correct odds-ratio interpretation. It does **not** necessarily mean the probability is 1.8 times higher. If the outcome is common, that shortcut can be seriously misleading.

### Section 5: Predicted probabilities and marginal effects
One way to improve communication is to translate model results into predicted probabilities or risk differences for meaningful profiles of interest.

For example, instead of saying "the adjusted odds ratio is 1.8," you might report:

- predicted probability of the outcome is `22%` in one group and `34%` in another, holding other modeled variables fixed

This is often easier for clinicians, programme managers, and policymakers to understand than odds ratios alone.

The deeper point is that the regression coefficient is not always the best communication tool, even when it is the right estimation tool.

### Section 6: Common assumptions and checks
Important practical issues in logistic regression include:

- correct specification of the model
- independence of observations
- enough outcome events for stable estimation
- sensible treatment of continuous predictors
- absence of extreme multicollinearity

The model also assumes that predictors act linearly on the **log-odds** scale unless additional terms are added. A variable may appear to have a poor fit simply because its relationship is nonlinear and the model has been specified too rigidly.

As with other models, diagnostics, model stability, and substantive plausibility still matter.

### Section 7: When logistic regression is not ideal
Logistic regression is common, but not always the easiest model to interpret.

If the outcome is common and the goal is to communicate relative risk clearly, alternatives such as log-binomial or modified Poisson approaches may be preferable. If time to event matters, survival methods may be better. If clustering is strong, mixed-effects or marginal models may be needed.

The choice of logistic regression should be justified by the question and the outcome structure, not by habit alone.

### Section 8: Common mistakes
Several mistakes recur often.

- interpreting an odds ratio as if it were a risk ratio
- ignoring that outcome prevalence affects the gap between odds and risk
- treating a statistically significant adjusted odds ratio as automatically causal
- including variables without a clear confounding or prediction rationale
- reporting only odds ratios when predicted probabilities would be more intelligible

Another subtle issue is **non-collapsibility**: even without confounding, adjusted odds ratios may differ from crude odds ratios mathematically. This means a change after adjustment does not automatically prove confounding. Interpretation has to be careful.

## Key takeaways
- Logistic regression is designed for binary outcomes and models the log-odds of the event.
- Exponentiated coefficients are odds ratios, not risk ratios.
- Odds ratios can be convenient statistically but hard to communicate when outcomes are common.
- Predicted probabilities often improve interpretation for applied audiences.
- Model choice, specification, confounding structure, and outcome prevalence all shape interpretation.

## Self-check questions
1. Why is logistic regression commonly used for binary outcomes?
2. What does an adjusted odds ratio represent?
3. Why can odds ratios be misleading when outcomes are common?
4. Why might predicted probabilities be easier to communicate than odds ratios?
5. What does the logit link model?
6. Why does a change from crude to adjusted odds ratio not automatically prove confounding?

## Answer key
1. Because it models binary outcomes in a way that keeps fitted probabilities within a sensible range and provides a flexible regression framework.
2. The ratio of modeled odds associated with a one-unit difference in a predictor, conditional on the other variables in the model.
3. Because the odds ratio moves farther from 1 than the corresponding risk ratio as the outcome becomes more common.
4. Because probabilities and percentage-point differences are more intuitive for most applied readers than odds.
5. The logarithm of the odds of the outcome as a linear function of predictors.
6. Because odds ratios are non-collapsible, so adjustment can change them for mathematical reasons as well as because of confounding.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [STROBE statement](https://www.strobe-statement.org/)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
