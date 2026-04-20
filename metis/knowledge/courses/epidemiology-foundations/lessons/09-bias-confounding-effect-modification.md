# Bias, Confounding, and Effect Modification

## Learning objectives
- Distinguish systematic error from random error.
- Explain the difference between bias, confounding, and effect modification.
- Identify design and analysis strategies that reduce avoidable error.
- Recognize when subgroup differences are a nuisance and when they are the real finding.

## Prerequisites
- Lessons 1 to 8.
- Basic familiarity with measures of association and study design.

## Content

### Section 1: Why this lesson matters
Epidemiology is not only about calculating ratios and fitting models. It is also about asking whether the estimate you produced is believable. Three concepts dominate that judgment: **bias**, **confounding**, and **effect modification**.

They are often mentioned together because all three can make associations look different across analyses or subgroups.

- **Bias** is systematic error.
- **Confounding** is a mixing of effects that distorts a comparison.
- **Effect modification** is a real difference in the size of an effect across strata.

Getting these distinctions right is central to good epidemiology.

### Section 2: Random error versus systematic error
Before focusing on bias, it helps to separate **random error** from **systematic error**.

Random error is the play of chance. With small samples, estimates bounce around more. Confidence intervals widen. Repeating the study could give somewhat different results.

Systematic error is different. It pushes the estimate in a particular direction because of how participants were selected, how information was measured, or how the comparison was structured. Collecting more data does not fix systematic error. A very precise estimate can still be wrong.

This is why a narrow confidence interval is not the same as validity.

### Section 3: Bias
Bias is any systematic deviation of an estimate from the truth. In introductory epidemiology, the two big families are **selection bias** and **information bias**.

**Selection bias** happens when the relation between exposure and outcome differs for those who enter or remain in the study compared with those who do not. Examples include:

- differential loss to follow-up in cohorts
- poor control selection in case-control studies
- conditioning on a collider through sampling or analysis

**Information bias** happens when exposure, outcome, or covariates are measured inaccurately in ways that distort the comparison. Examples include:

- recall bias
- interviewer bias
- diagnostic misclassification
- socially desirable responses in self-reported behaviors

Bias can move estimates toward or away from the null, and sometimes the direction is not obvious in advance.

### Section 4: Confounding
Confounding occurs when the observed association between exposure and outcome is mixed with the effect of another variable that is associated with both. A confounder is not on the causal pathway, but it creates a backdoor route that distorts the comparison.

A classic example is the relationship between coffee drinking and lung cancer if smoking is ignored. Coffee may appear associated with lung cancer partly because smokers are more likely to drink coffee and more likely to develop lung cancer. In that case, smoking is a confounder.

For a variable to behave like a confounder in the usual epidemiologic sense, it generally must:

- be associated with the exposure
- be associated with the outcome
- not lie on the causal pathway between exposure and outcome

Confounding is different from bias in one useful way: it is a structural problem in the comparison, not simply sloppy measurement. But like bias, it threatens causal interpretation.

### Section 5: Effect modification
Effect modification, sometimes called interaction in epidemiologic teaching, means that the size of the association truly differs across levels of another variable.

For example, a malaria-prevention intervention might have a larger effect in young children than in adults. That is not necessarily a problem to eliminate. It may be exactly the finding that matters for policy, targeting, and equity.

This is the key conceptual difference:

- **Confounding** is distortion that should usually be controlled.
- **Effect modification** is heterogeneity that should usually be described and interpreted.

Many beginners confuse the two because both can appear when results differ across strata. The deciding question is whether the third variable is distorting the exposure-outcome comparison or genuinely changing the magnitude of effect.

### Section 6: Worked example - confounding by age
Imagine a cohort study examines whether influenza vaccination is associated with winter mortality. Crude results suggest vaccinated adults have higher mortality than unvaccinated adults.

At first glance, that could be misread as vaccination being harmful. But suppose older adults are much more likely to be vaccinated and also much more likely to die during winter regardless of vaccination status. Age is then confounding the crude association.

After stratifying by age group, the association weakens or reverses within strata. The crude association was misleading because it mixed the effect of vaccination with baseline age differences.

Without confounding control, even sensible programs can appear ineffective or harmful.

### Section 7: Worked example - effect modification by sex
Now imagine a prevention program for occupational heat stress. Overall, the intervention reduces dehydration-related clinic visits by 20%. But when results are stratified, the reduction is 10% in men and 35% in women.

If the sex difference reflects a genuine difference in how the intervention works or is experienced, this is effect modification. It is not something to hide by reporting only one pooled estimate. The subgroup difference may have direct implications for programme design and implementation.

Confounding asks, "What should be adjusted for?" Effect modification asks, "For whom is the effect different?"

### Section 8: Common strategies to reduce bias and confounding
Good epidemiology uses both design-stage and analysis-stage strategies.

At the **design stage**:

- randomization can reduce confounding
- restriction can limit variability in a key confounder
- matching can improve comparability in some designs
- better protocols can reduce information bias
- clear follow-up procedures can reduce attrition bias

At the **analysis stage**:

- stratification can reveal confounding or effect modification
- standardization can adjust for differences in population structure
- multivariable regression can control measured confounders
- weighting or matching approaches can improve balance in observational studies
- sensitivity analysis can assess how robust results are to unmeasured confounding

None of these fully rescues a poorly designed study. But they can substantially improve interpretation when applied with a clear causal question in mind.

### Section 9: DAG thinking and modern causal practice
Modern epidemiology increasingly uses directed acyclic graphs, or DAGs, to make assumptions explicit. DAGs help analysts decide what to adjust for, what not to adjust for, and where selection bias or collider bias may arise.

This matters because adjustment is not automatically beneficial. Controlling for a mediator can block part of the effect you want to estimate, and conditioning on a collider can create a spurious association.

### Section 10: Common beginner mistakes
Several mistakes recur often.

- Treating all subgroup differences as confounding.
- Assuming statistical significance proves absence of bias.
- Believing larger samples solve systematic error.
- Adjusting for every available variable without a causal rationale.
- Reporting one overall estimate when the important policy question is actually subgroup-specific.

The practical skill is learning to ask whether a third variable is distorting the comparison, changing the effect, or merely being overcontrolled.

## Key takeaways
- Random error affects precision; bias affects validity.
- Selection bias and information bias are major sources of systematic error in epidemiology.
- Confounding distorts an exposure-outcome comparison because of a third variable linked to both.
- Effect modification means the association truly differs across strata and may be substantively important.
- Design-stage prevention is usually stronger than post hoc statistical repair.

## Self-check questions
1. Why can a study be very precise but still invalid?
2. What is the difference between selection bias and information bias?
3. What three general features make a variable a potential confounder?
4. How does effect modification differ conceptually from confounding?
5. Why is it not always correct to adjust for every available variable?
6. Give one example in which a subgroup difference would be important to report rather than hide.

## Answer key
1. Because a large study can reduce random error while still suffering from systematic error in selection, measurement, or causal structure.
2. Selection bias comes from who enters or remains in the study, while information bias comes from how variables are measured or reported.
3. It is associated with the exposure, associated with the outcome, and not on the causal pathway between them.
4. Confounding is distortion that should usually be controlled, while effect modification is a real difference in effect size across strata that should usually be described.
5. Because some variables are mediators or colliders, and adjusting for them can bias the estimate rather than improve it.
6. Examples include sex-specific vaccine effectiveness, age-specific intervention benefit, or stronger effects in underserved populations that matter for targeting and equity.

## Further reading
- [Hernan and Robins, Causal Inference: What If](https://miguelhernan.org/whatifbook)
- [STROBE resources](https://www.strobe-statement.org/)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
- [DAGitty](https://dagitty.net/)

## Links to Metis library
- `06_library/methods/causal-inference.md`
- `06_library/methods/study-designs.md`
- `06_library/methods/biostatistics-essentials.md`
