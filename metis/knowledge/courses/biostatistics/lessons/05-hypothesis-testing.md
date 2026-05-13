# Hypothesis Testing

## Learning objectives
- Explain null hypotheses, alternative hypotheses, test statistics, and p-values.
- Distinguish type I error, type II error, alpha, beta, and power.
- Interpret statistically non-significant results without equating them to "no effect."
- Avoid common misreadings of p-values in epidemiology and public-health research.

## Prerequisites
- Confidence intervals.

## Content

### Section 1: What hypothesis testing is trying to do
Hypothesis testing asks how compatible the observed data are with a specified null model. The logic is not "prove the null true or false." It is "if the null model were true, how surprising would these data be?"

The usual pieces are:

- a **null hypothesis**, often representing no association or no difference
- an **alternative hypothesis**, representing some departure from the null
- a **test statistic**, which summarizes the observed evidence
- a **p-value**, which quantifies how extreme the observed test statistic would be under the null model

This framework is widely used, but it is easy to misuse when the p-value is treated as a shortcut for importance, truth, or causal validity.

### Section 2: What a p-value actually means
A p-value is the probability, under the null hypothesis and model assumptions, of observing data at least as extreme as those seen.

It is **not**:

- the probability that the null hypothesis is true
- the probability that the results occurred "by chance alone"
- the probability that the alternative hypothesis is true
- a direct measure of effect size

These distinctions matter because p-values are often overinterpreted. A small p-value means the data would be unusual if the null model were true. It does not automatically mean the effect is large, important, causal, or well estimated.

### Section 3: Type I and type II error
Hypothesis testing involves decision risk.

A **type I error** occurs when we reject the null hypothesis even though it is true. The probability of this error is commonly denoted by **alpha**, often set at `0.05`.

A **type II error** occurs when we fail to reject the null hypothesis even though a real effect exists. The probability of this error is commonly denoted by **beta**.

**Power** is:

\[
1 - \beta
\]

It is the probability of detecting an effect of a specified size if that effect is truly present.

These concepts are important because "non-significant" results may simply reflect low power, not absence of an important association.

### Section 4: Statistical significance versus practical importance
An estimate can be statistically significant and still be trivial in practice. Conversely, an estimate can fail to reach a conventional threshold and still be clinically or programmatically important.

This is why effect size and confidence intervals matter. Hypothesis testing without magnitude and precision is incomplete. In epidemiology, the relevant question is rarely just "did it cross 0.05?" More often it is "how large is the effect, how uncertain is it, and is it credible enough to matter?"

### Section 5: Worked example - small outbreak study
Imagine a foodborne outbreak investigation compares exposure to a suspect food among 20 cases and 20 controls. The odds ratio is elevated, but the p-value is `0.08`.

How should this be interpreted?

- The result does not meet the conventional `0.05` threshold.
- The estimate may still be compatible with a meaningful association.
- The study is small, so low power is a plausible reason for the non-significant result.
- The exposure may still deserve attention if descriptive, environmental, and biologic evidence point in the same direction.

This example shows why "not significant" should not be translated automatically into "nothing is happening."

### Section 6: Worked example - large sample, tiny effect
Now imagine a national dataset with 200,000 observations finds a risk ratio of `1.03` with a p-value `< 0.001`.

Interpretation:

- The estimate is highly statistically significant.
- The effect is very small in magnitude.
- Whether it matters depends on context, bias risk, and potential population impact.

This example shows the opposite problem: very large samples can make tiny differences look compelling if readers focus only on the p-value.

### Section 7: Multiple testing and false positives
When many hypotheses are tested, false-positive findings become more likely. If you test enough unrelated questions, some p-values will appear small just by chance.

This matters in subgroup analyses, exploratory biomarker screens, multi-outcome studies, and flexible analytic workflows. The problem is not only mathematical. It is also procedural. Repeated model tinkering, selective reporting, and post hoc subgroup hunting can produce apparently persuasive p-values that do not replicate.

That is why pre-specification, transparent reporting, and corrections for multiple testing are important when many hypotheses are in play.

### Section 8: Power and study design
Power depends on several factors:

- sample size
- outcome frequency
- variability
- effect size
- significance threshold

Low-powered studies are not useless, but they are more likely to miss real effects and produce unstable estimates. In epidemiology, small studies of rare outcomes often face this problem. Interpretation should then emphasize uncertainty rather than sharp negative conclusions.

Power is a design issue, not something to worry about only after results are disappointing.

### Section 9: Better habits for reading test results
A disciplined way to read a hypothesis test is:

1. identify the null and alternative questions
2. inspect the effect estimate
3. inspect the confidence interval
4. interpret the p-value as one compatibility measure, not the whole story
5. consider bias, confounding, multiple testing, and study design

This approach prevents the p-value from dominating interpretation.

## Key takeaways
- Hypothesis testing evaluates how compatible the observed data are with a specified null model.
- A p-value is not the probability that the null hypothesis is true.
- Type I error, type II error, and power describe the risks of incorrect decisions under uncertainty.
- Statistical significance is not the same as practical importance.
- P-values should be interpreted alongside effect size, confidence intervals, study design, and bias risk.

## Self-check questions
1. What does a p-value quantify?
2. What is a type I error? What is a type II error?
3. Why can a non-significant result still matter in a small study?
4. Why can a highly significant result in a huge dataset still be unimportant?
5. How does multiple testing increase false-positive risk?
6. Why is power primarily a design issue?

## Answer key
1. The probability, under the null hypothesis and model assumptions, of observing data at least as extreme as those observed.
2. A type I error is rejecting a true null hypothesis; a type II error is failing to reject a false null hypothesis.
3. Because the study may have low power, so a real and meaningful effect might not reach a conventional significance threshold.
4. Because the effect size may be extremely small even though the sample is large enough to make it statistically detectable.
5. Because testing many hypotheses creates more chances for apparently small p-values to appear just by random variation.
6. Because sample size, expected effect size, and design features that determine power must usually be planned before data collection or primary analysis.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Khan Academy significance tests](https://www.khanacademy.org/math/statistics-probability/significance-tests-one-sample)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/study-designs.md`
- `knowledge/library/methods/causal-inference.md`
