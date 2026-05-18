# Confidence Intervals

## Learning objectives
- Interpret confidence intervals as summaries of sampling uncertainty under a model.
- Distinguish precision from validity and from substantive importance.
- Read intervals in relation to null values and meaningful effect sizes.
- Explain why confidence intervals usually provide more information than p-values alone.

## Prerequisites
- Probability distributions.

## Content

### Section 1: Why interval estimation matters
Point estimates are useful, but they are incomplete. A sample mean, odds ratio, or risk difference gives one best estimate from the observed data, yet a different sample from the same population would usually give a somewhat different result. Confidence intervals try to summarize that sampling uncertainty.

This matters because epidemiology rarely cares only about the most likely estimate. We also care about how precise the estimate is and which values remain compatible with the data under the model being used.

In practice, intervals help answer questions such as:

- Is the estimate precise or unstable?
- Is the effect plausibly trivial, moderate, or large?
- Are the data compatible with no association?
- How much uncertainty remains for decision-making?

### Section 2: What a confidence interval is
A confidence interval is a range of values computed from the data by a procedure that, over repeated sampling, would contain the true parameter a specified proportion of the time if the model assumptions hold.

For a 95% confidence interval, the long-run procedure succeeds 95% of the time under repeated sampling. That is not the same as saying there is a 95% probability that the true value lies inside the interval for this one observed dataset. The interval either contains the true value or it does not. The 95% refers to the method, not a posterior probability.

This distinction feels technical, but it matters because confidence intervals are often casually misread as direct probability statements about the parameter.

### Section 3: Width and precision
The width of an interval is a practical signal of precision.

Narrow intervals usually mean:

- larger samples
- less variability
- more statistical information

Wide intervals usually mean:

- smaller samples
- more variability
- rarer outcomes
- less stable estimates

A wide interval does not mean the study is useless. It means uncertainty remains substantial. Sometimes that is exactly the correct conclusion.

### Section 4: Null values and meaningful values
Every interval should be read in relation to a reference value.

For ratio measures such as risk ratios, odds ratios, and hazard ratios, the usual null value is:

\[
1
\]

For difference measures such as risk differences or mean differences, the usual null value is:

\[
0
\]

But interpretation should not stop at the null. An interval may exclude the null yet still be too small to matter clinically or programmatically. Conversely, an interval may include the null but still contain effects large enough to matter, especially if the study is underpowered.

That is why confidence intervals support more nuanced interpretation than a simple significant/non-significant dichotomy.

### Section 5: Worked example - odds ratio with a wide interval
Imagine a case-control study of an outbreak reports an odds ratio of `1.8` with a 95% confidence interval from `0.9` to `3.7`.

How should this be read?

- The point estimate suggests a possible positive association.
- The interval is fairly wide, so precision is limited.
- The interval includes `1`, so the data remain compatible with no association under the standard frequentist test relationship.
- The interval also includes moderately large harmful associations, so the study does not rule out an important effect.

This is a more informative interpretation than simply saying "not significant." The result may still matter, especially if the exposure is plausible and the study is small.

### Section 6: Worked example - risk difference and practical importance
Now imagine a programme evaluation reports that an intervention reduced loss to follow-up by `6 percentage points`, with a 95% confidence interval from `2` to `10` percentage points.

Interpretation:

- the estimate is compatible with a modest but real reduction
- the interval does not include `0`
- the likely effect is not only statistically compatible with benefit, but also potentially meaningful for programme operations

This example shows why absolute measures with intervals can be especially helpful in public-health decision making. They connect uncertainty to expected practical impact.

### Section 7: Confidence intervals versus p-values
Confidence intervals and p-values are closely related in standard settings, but they emphasize different things.

A p-value summarizes how unusual the data would be if the null model were true. A confidence interval shows a range of parameter values compatible with the data under the model.

Intervals are often more informative because they show:

- direction of effect
- magnitude of effect
- precision of the estimate
- compatibility with both null and non-null values

This is why many journals and reporting guidelines encourage presenting intervals rather than relying on p-values alone.

### Section 8: Precision is not validity
One of the most important lessons in epidemiology is that precision and validity are not the same thing.

An estimate can have a very narrow confidence interval and still be wrong because of:

- selection bias
- information bias
- confounding
- model misspecification
- systematic measurement problems

Confidence intervals usually reflect random error under a model. They do not automatically account for bias. That is why a "precise" result is not automatically trustworthy.

### Section 9: Common mistakes in reading intervals
Several mistakes recur often.

- Treating the interval as a direct probability statement about the parameter
- Equating interval width only with sample size while ignoring variability
- Interpreting intervals only by whether they include the null
- Forgetting that the interval depends on model assumptions
- Assuming a narrow interval proves causal validity

A better habit is to read intervals in three steps: location, width, and practical relevance.

## Key takeaways
- Confidence intervals summarize sampling uncertainty around an estimate under stated model assumptions.
- Interval width reflects precision, not truth.
- Intervals should be interpreted in relation to both the null value and practically meaningful effect sizes.
- Confidence intervals usually communicate more than p-values because they show magnitude and precision together.
- Narrow intervals do not protect against bias, confounding, or poor study design.

## Self-check questions
1. What does a 95% confidence interval mean in repeated-sampling terms?
2. Why is a wide interval often informative rather than simply disappointing?
3. What is the usual null value for an odds ratio? What about a risk difference?
4. Why can an interval that includes the null still matter substantively?
5. Why is a precise estimate not necessarily valid?
6. What extra information does a confidence interval give beyond a p-value?

## Answer key
1. It means the interval-generating procedure would contain the true parameter 95% of the time over repeated samples if the assumptions hold.
2. Because it tells you that the estimate is imprecise and that the data remain compatible with a wider range of values, which is important for honest interpretation.
3. The null value is `1` for an odds ratio and `0` for a risk difference.
4. Because the interval may still include effects large enough to matter clinically or programmatically, even if it also includes no effect.
5. Because confidence intervals mainly reflect sampling variability and do not automatically correct for bias, confounding, or systematic error.
6. It shows a range of compatible effect sizes and therefore communicates both magnitude and precision, not only compatibility with a null hypothesis.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Khan Academy confidence intervals](https://www.khanacademy.org/math/statistics-probability/confidence-intervals-one-sample)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/causal-inference.md`
- `knowledge/library/methods/study-designs.md`
