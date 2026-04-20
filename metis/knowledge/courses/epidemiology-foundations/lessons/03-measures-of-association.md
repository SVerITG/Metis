# Measures of Association

## Learning objectives
- Calculate and interpret risk ratios, rate ratios, odds ratios, and risk differences.
- Distinguish relative measures from absolute measures and explain why both matter for decisions.
- Recognize which measures fit best with cohort, case-control, and outbreak-study settings.
- Explain when odds ratios are reasonable approximations of risk ratios and when they are misleading.

## Prerequisites
- Measures of disease frequency.
- Basic familiarity with cohort and case-control logic.

## Content

### Section 1: What a measure of association is trying to show
A measure of association compares disease occurrence between groups that differ in exposure or another factor of interest. The central question is simple: does the outcome occur more often in one group than another, and by how much?

If disease occurs equally often in exposed and unexposed groups, the ratio-based measure is close to 1.0 and the risk difference is close to 0. Higher occurrence in the exposed group pushes the ratio above 1 and the difference above 0; lower occurrence suggests a protective association.

Interpretation always depends on study design, bias, confounding, and decision context. A strong association does not automatically mean causation, and a modest association can still matter when exposure is common.

### Section 2: Relative measures
Relative measures ask how many times higher or lower disease occurrence is in one group compared with another.

**Risk ratio (RR)** compares cumulative incidence:

\[
RR = \frac{Risk\ in\ exposed}{Risk\ in\ unexposed}
\]

Suppose 40 of 200 people exposed to contaminated water develop gastroenteritis, compared with 10 of 200 unexposed people. The risk in the exposed group is 0.20 and the risk in the unexposed group is 0.05. The risk ratio is:

\[
RR = \frac{0.20}{0.05} = 4.0
\]

This means the exposed group experienced four times the risk over the study period.

**Rate ratio** is similar, but it compares incidence rates rather than risks. It is useful when person-time differs across groups, such as in dynamic cohorts, occupational follow-up, or surveillance studies where follow-up time is unequal.

\[
Rate\ Ratio = \frac{Incidence\ rate\ in\ exposed}{Incidence\ rate\ in\ unexposed}
\]

Relative measures communicate strength of association clearly, but they can sound dramatic even when the actual number of excess events is small.

### Section 3: Absolute measures
Absolute measures ask how much extra disease is occurring, not just how many times higher it is.

**Risk difference (RD)** is:

\[
RD = Risk\ in\ exposed - Risk\ in\ unexposed
\]

Using the waterborne outbreak example:

\[
RD = 0.20 - 0.05 = 0.15
\]

That means there were 15 additional cases per 100 people attributable to the exposure during the study period.

This is often more useful for public-health planning than the ratio alone.

Attributable fraction among the exposed and population attributable fraction go one step further by translating association into preventable burden, assuming the association is causal.

### Section 4: Odds ratios and why they cause confusion
The **odds ratio (OR)** compares odds rather than risks:

\[
OR = \frac{Odds\ in\ exposed}{Odds\ in\ unexposed}
\]

In a cohort table, odds are:

\[
Odds = \frac{Probability\ of\ event}{Probability\ of\ no\ event}
\]

Odds ratios arise naturally in case-control studies because investigators sample on outcome status rather than observing incidence directly. In that setting, you usually cannot calculate a risk ratio from the study data alone, but you can estimate the odds ratio.

This makes the odds ratio indispensable, but also easy to overstate. When the outcome is rare, the OR and RR are numerically similar. When the outcome is common, the OR moves farther from 1 than the RR and can make effects sound larger than they are.

In practice:
- Use risk ratios when risks can be estimated directly.
- Use rate ratios when person-time is central.
- Use odds ratios when the design requires them, especially in case-control studies and logistic regression.
- Translate results into absolute impact whenever decisions depend on expected burden reduction.

### Section 5: Worked example from a cohort study
Imagine a prospective cohort following 1,000 smokers and 1,000 non-smokers for 10 years to assess coronary heart disease.

- Smokers with incident CHD: 120
- Smokers without incident CHD: 880
- Non-smokers with incident CHD: 60
- Non-smokers without incident CHD: 940

The risk in smokers is:

\[
\frac{120}{1000} = 0.12
\]

The risk in non-smokers is:

\[
\frac{60}{1000} = 0.06
\]

So:

\[
RR = \frac{0.12}{0.06} = 2.0
\]

\[
RD = 0.12 - 0.06 = 0.06
\]

Interpretation:
- Smokers had twice the 10-year risk of CHD compared with non-smokers.
- There were 6 excess CHD cases per 100 smokers over 10 years.

These two statements are both correct, but they answer different questions. The RR conveys strength of association; the RD conveys expected excess burden.

### Section 6: Worked example from an outbreak case-control study
Now consider a foodborne outbreak investigation. Investigators compare 80 cases with 160 controls and assess whether participants ate egg salad.

- Cases exposed: 48
- Cases unexposed: 32
- Controls exposed: 24
- Controls unexposed: 136

The odds ratio is:

\[
OR = \frac{48 \times 136}{32 \times 24} = 8.5
\]

Interpretation:
- The odds of exposure among cases were 8.5 times the odds of exposure among controls.
- This is strong evidence that egg salad is a likely outbreak vehicle, assuming major bias or confounding is unlikely.

Because this is a case-control study, a direct risk ratio is not available from the sampled data. The OR is the standard effect measure here and is often enough to support urgent control actions.

### Section 7: Real-world application and common mistakes
Measures of association are used constantly in epidemiologic practice. Cohort studies often report risk or rate ratios. Vaccine effectiveness studies frequently use odds ratios from case-control or test-negative designs, and outbreak investigations often rely on ORs because case-control sampling is fast and practical.

Common mistakes include:

- **Confusing statistical association with causation.** A ratio above 1 does not by itself prove an exposure caused the outcome.
- **Reporting odds ratios as if they were risk ratios.** This is especially misleading when outcomes are common.
- **Ignoring the baseline risk.** A doubling of risk may still correspond to a very small absolute increase.
- **Choosing the wrong denominator.** If follow-up time differs, incidence rates may be more appropriate than cumulative risks.
- **Forgetting precision.** Measures of association should usually be interpreted with confidence intervals, not point estimates alone.

For Metis users, the practical habit is simple: ask what measure was used, whether it matches the study design, whether the absolute effect is also reported, and what sources of bias might distort the estimate.

## Key takeaways
- Measures of association compare disease occurrence between groups and help quantify how strongly an exposure and outcome are related.
- Risk ratios and rate ratios are relative measures; risk differences add the absolute burden perspective needed for policy and planning.
- Odds ratios are standard in case-control studies and logistic regression, but they are not the same as risk ratios.
- The rarer the outcome, the closer the odds ratio is likely to be to the risk ratio.
- Interpretation always depends on study design, outcome frequency, precision, and potential bias or confounding.

## Self-check questions
1. What is the conceptual difference between a risk ratio and a risk difference?
2. Why might a public-health planner care about a risk difference even when the risk ratio is large?
3. In which study design is the odds ratio usually the default association measure?
4. Why can an odds ratio exaggerate the apparent effect when an outcome is common?
5. In a cohort study, the risk is 18% in the exposed group and 9% in the unexposed group. What are the risk ratio and risk difference?
6. Why should measures of association usually be interpreted alongside confidence intervals and possible sources of bias?

## Answer key
1. The risk ratio compares relative occurrence between groups, while the risk difference shows the absolute excess or deficit of disease attributable to the exposure over the study period.
2. Because planning usually depends on how many excess events may be prevented or caused, not only on the multiplicative strength of the association.
3. Case-control studies, because incidence cannot usually be estimated directly from outcome-based sampling.
4. Because odds diverge more from risks as outcomes become common, pushing the OR farther away from 1 than the corresponding RR.
5. The risk ratio is 0.18 / 0.09 = 2.0. The risk difference is 0.18 - 0.09 = 0.09, or 9 excess cases per 100 people.
6. Because the point estimate alone does not show precision and may be distorted by confounding, selection bias, information bias, or random error.

## Further reading
- [CDC Principles of Epidemiology, Lesson 3](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/lesson3/index.html)
- [CDC overview of vaccine effectiveness study designs](https://www.cdc.gov/flu-vaccines-work/php/effectiveness-studies/)
- [STROBE Statement](https://www.strobe-statement.org/)
- [Framingham Heart Study risk resources](https://www.framinghamheartstudy.org/fhs-risk-functions/coronary-heart-disease-10-year-risk/)

## Links to Metis library
- `06_library/methods/study-designs.md`
- `06_library/methods/causal-inference.md`
- `06_library/methods/biostatistics-essentials.md`
- `06_library/methods/outbreak-investigation.md`
