# Cross-Sectional Studies

## Learning objectives
- Define the cross-sectional design and identify when it is appropriate.
- Interpret prevalence, prevalence ratios, and prevalence differences in context.
- Explain why temporality is usually unresolved in cross-sectional data.
- Recognize how sampling design, weighting, and non-response affect validity.

## Prerequisites
- Measures of disease frequency.
- Basic familiarity with study designs and measures of association.

## Content

### Section 1: The snapshot logic
A cross-sectional study measures exposure, outcome, or both at a single point in time, or within a narrow time window. The design gives a snapshot of the population rather than a movie of events unfolding over time. That makes it especially useful for burden estimation, service planning, and hypothesis generation.

If you want to know how many adults currently have hypertension, how many households own insecticide-treated nets, or what proportion of health workers have received recent training, a cross-sectional survey is often an efficient design. It can also be used to compare subgroups, such as prevalence by age, sex, district, or occupation.

The main limitation follows directly from the snapshot structure: exposure and outcome are often measured at the same moment, so temporality is unclear.

### Section 2: What cross-sectional studies are good at
Cross-sectional studies are often the best first answer to questions about **current burden** and **current distribution**.

They are useful for:

- estimating prevalence of disease, symptoms, behaviors, or service coverage
- identifying which groups carry the highest current burden
- planning services, staffing, diagnostics, or procurement
- generating hypotheses for later cohort or case-control work
- monitoring some indicators repeatedly through serial surveys

This is why they are common in demographic and health surveys, KAP surveys, serosurveys, screening coverage assessments, and routine health-system evaluations.

When repeated at intervals using comparable methods, cross-sectional surveys can also describe trends. Strictly speaking, each survey is still cross-sectional, but together they can reveal how population patterns are changing.

### Section 3: Measures commonly used
The natural measure in cross-sectional work is **prevalence**:

\[
Prevalence = \frac{Existing\ cases}{Population\ assessed}
\]

If 180 of 1,200 adults in a district survey have hypertension, the prevalence is:

\[
\frac{180}{1200} = 0.15
\]

So the point prevalence is 15%.

When comparing groups, investigators may use:

- **prevalence ratio**
- **prevalence difference**
- sometimes **prevalence odds ratio**

For common outcomes, prevalence ratios are usually easier to interpret than odds ratios. As with other designs, absolute and relative measures answer different questions. A prevalence ratio may highlight inequality between groups, while a prevalence difference may be more useful for service planning.

### Section 4: Why temporality is the core weakness
Cross-sectional studies often struggle with the question: did the exposure come before the outcome, or did the outcome affect the exposure?

Suppose a survey finds that people currently using bed nets have lower malaria prevalence. That pattern may reflect protection from net use, but it might also reflect reverse causation or confounding. People in lower-risk households may be more likely to use nets consistently, or recently ill households may have changed their behavior after an episode of malaria.

This is why cross-sectional studies are usually weak for strong causal claims. Some exposure-outcome pairs are more interpretable than others. Age, sex, or place of residence clearly precede many outcomes. But for many behavioral, clinical, or service variables, the timing is much less clear.

### Section 5: Worked example - district hypertension survey
Imagine a district survey samples 2,000 adults using a two-stage cluster design. Investigators measure blood pressure and collect data on obesity.

Results:

- 300 adults have hypertension
- 700 adults are obese
- among obese adults, 175 have hypertension
- among non-obese adults, 125 have hypertension

Overall hypertension prevalence is:

\[
\frac{300}{2000} = 0.15
\]

So prevalence is 15%.

Hypertension prevalence among obese adults is:

\[
\frac{175}{700} = 0.25
\]

Hypertension prevalence among non-obese adults is:

\[
\frac{125}{1300} \approx 0.096
\]

The prevalence ratio is:

\[
\frac{0.25}{0.096} \approx 2.6
\]

Interpretation:
- Hypertension prevalence is about 2.6 times higher among obese adults than among non-obese adults in this survey.

This is useful for programme targeting, but the survey alone does not establish causality. It tells you the conditions coexist; it does not fully prove the sequence.

### Section 6: Sampling design matters
Cross-sectional studies are only as good as their sampling strategy. A perfectly analyzed non-representative sample still gives a biased picture of population burden.

Important design choices include:

- who is eligible
- whether the sample is random
- whether clustering or stratification is used
- how non-response is handled
- whether weights are needed

Population-based surveys often use complex sampling rather than simple random sampling. That means analysis should account for clustering, unequal selection probabilities, and survey weights where appropriate. Ignoring the survey design can lead to misleading standard errors, confidence intervals, and even biased population estimates.

### Section 7: Common biases in cross-sectional studies
Several biases recur often.

**Non-response bias** occurs when people who decline participation differ systematically from those who participate.

**Prevalence-incidence bias** or **Neyman bias** arises because cross-sectional designs overrepresent long-duration cases and may miss short-duration or rapidly fatal cases. That means the measured prevalence reflects both incidence and duration.

**Recall bias** can affect exposure measurement when participants are asked about past behavior or diagnosis history.

**Selection bias** can arise when surveys are conducted in facilities, schools, or workplaces and then generalized too broadly.

These issues do not make cross-sectional studies unhelpful. They simply define what kinds of claims are credible.

### Section 8: Real-world use in public health
Cross-sectional designs are widely used for operational decisions. A programme may run a survey to estimate vaccination coverage, identify geographic gaps in service uptake, measure community awareness, or assess the current prevalence of anemia or malnutrition.

In elimination settings, cross-sectional serosurveys or screening surveys may help describe whether transmission indicators remain low in specific populations. Even there, interpretation depends on who was sampled, how representative the sample was, and whether the measured marker reflects past or current exposure.

### Section 9: Questions to ask before trusting a cross-sectional study
Before accepting the result, ask:

1. Is the target population clearly defined?
2. Does the sample represent that population well?
3. Were weighting and clustering handled correctly?
4. Is the estimate about prevalence, not incidence?
5. Could the exposure-outcome relationship reflect reverse causation?
6. Are the conclusions staying within what a snapshot design can support?

Those questions keep cross-sectional evidence useful without overselling it.

## Key takeaways
- Cross-sectional studies provide a snapshot of exposure and outcome status in a population.
- They are strong for prevalence estimation, service planning, and hypothesis generation.
- Their main limitation is weak temporality, which restricts causal interpretation.
- Prevalence ratios and prevalence differences are often more useful than odds ratios for common outcomes.
- Representativeness, weighting, non-response, and clustering strongly affect validity.

## Self-check questions
1. What kind of epidemiologic question is a cross-sectional study especially good at answering?
2. Why is temporality usually difficult to establish in cross-sectional data?
3. What is the difference between prevalence and incidence?
4. Why can prevalence-incidence bias distort interpretation?
5. Why should survey weights and clustering be considered in analysis?
6. In what way can repeated cross-sectional surveys still be useful over time?

## Answer key
1. Questions about current burden, current distribution, and current service coverage in a defined population.
2. Because exposure and outcome are often measured at the same time, so the sequence between them is uncertain.
3. Prevalence counts existing cases at a point or period, while incidence counts new cases over time.
4. Because cross-sectional surveys tend to capture people with longer-duration conditions more easily than short-duration or rapidly fatal cases.
5. Because complex sampling affects both population estimates and uncertainty; ignoring it can produce misleading inferences.
6. They can show how population prevalence or coverage changes across repeated time points, even though each individual survey remains a snapshot.

## Further reading
- [STROBE checklists](https://www.strobe-statement.org/checklists/)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
- [OpenIntro Statistics](https://www.openintro.org/book/os/)

## Links to Metis library
- `06_library/methods/study-designs.md`
- `06_library/methods/sampling-strategies.md`
- `06_library/methods/biostatistics-essentials.md`
