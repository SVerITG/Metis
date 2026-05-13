# Cohort Studies

## Learning objectives
- Describe the basic logic of prospective and retrospective cohort studies.
- Explain why cohort studies are strong for temporality, incidence estimation, and studying multiple outcomes.
- Recognize major validity threats in cohorts, including confounding, selection, and loss to follow-up.
- Interpret common cohort effect measures such as risk ratios, rate ratios, and hazard ratios.

## Prerequisites
- Study designs overview.
- Measures of disease frequency and measures of association.

## Content

### Section 1: The core logic of a cohort
A cohort study starts with people grouped by exposure status and then asks whether outcomes occur differently over follow-up. This can happen prospectively, with participants enrolled and followed forward from baseline, or retrospectively, using existing records to reconstruct exposure and outcome histories. In both cases, the core logic is the same: exposure is defined before the outcome is counted.

That temporal ordering is one of the main advantages of cohort studies. If you want to know whether smoking precedes lung cancer, whether occupational pesticide exposure precedes neurologic disease, or whether screening participation predicts later diagnosis patterns, a cohort design is often a natural choice.

Cohorts are especially useful when:

- the exposure is uncommon but identifiable
- incidence matters
- multiple outcomes may follow from one exposure
- the timing of exposure is central to the research question

### Section 2: Prospective versus retrospective cohorts
In a **prospective cohort**, researchers define the cohort near the start of follow-up and observe events as they occur. This often gives stronger control over exposure measurement, outcome definitions, and covariate collection, but it can be expensive and slow.

In a **retrospective cohort**, both exposure and outcome have already occurred by the time the study begins, but existing records make it possible to reconstruct the sequence. Examples include occupational cohorts built from employment records, electronic health record cohorts, or routine-program cohorts using surveillance or treatment databases.

Retrospective does not automatically mean weaker. A well-defined retrospective cohort with clear eligibility, high-quality records, defensible time zero, and complete follow-up can be extremely informative. The real question is not whether the design is prospective or retrospective, but whether the underlying data support valid comparisons.

### Section 3: What cohorts are good at
Cohort studies have several major strengths. They can estimate **incidence** directly, are strong for **temporality**, and allow one exposure to be linked to **multiple outcomes**. They also work well when exposures are time-varying, which matters in environmental epidemiology, pharmacoepidemiology, and public-health program evaluation.

### Section 4: What cohorts are bad at
The classic limitation is inefficiency for **rare outcomes**. If the event of interest is uncommon, a cohort may need to be very large or followed for a long period. That is one reason case-control studies are often preferred for rare diseases.

Cohorts can also become expensive, logistically difficult, and analytically complex. Long follow-up invites changing exposure patterns, migration, missing data, shifts in diagnostic criteria, and attrition. If those processes differ systematically between exposure groups, bias can result.

Another limitation is **confounding**. Because exposure is not randomized, exposed and unexposed people may differ in ways that also affect the outcome. Statistical adjustment can help, but it cannot fully fix badly measured or unmeasured confounders.

### Section 5: Time zero, follow-up, and censoring
Good cohort studies take time seriously. Three concepts are essential.

**Time zero** is the moment follow-up begins. It should be defined in a way that aligns with eligibility, exposure assignment, and outcome risk. If time zero is ambiguous or differs across groups, serious bias can appear immediately.

**Follow-up** is the period during which outcomes are observed. Cohorts need clear rules for when follow-up starts, when it ends, and what counts as continued observation.

**Censoring** occurs when a participant stops contributing outcome information before experiencing the event of interest, for example because of migration, loss to follow-up, administrative study end, or death from another cause. Censoring is not automatically a problem, but it becomes one when it is informative and differs by exposure or prognosis.

This is why cohort analysis often uses person-time methods, survival analysis, and careful documentation of attrition.

### Section 6: Worked example - smoking and coronary heart disease
Imagine a cohort of 4,000 adults without prior coronary heart disease at baseline: 1,500 current smokers and 2,500 non-smokers. They are followed for 8 years.

During follow-up:

- 180 smokers develop incident coronary heart disease
- 120 non-smokers develop incident coronary heart disease

The cumulative incidence in smokers is:

\[
\frac{180}{1500} = 0.12
\]

The cumulative incidence in non-smokers is:

\[
\frac{120}{2500} = 0.048
\]

The risk ratio is:

\[
\frac{0.12}{0.048} = 2.5
\]

Interpretation:
- Smokers had 2.5 times the 8-year risk of coronary heart disease compared with non-smokers.

The risk difference is:

\[
0.12 - 0.048 = 0.072
\]

Interpretation:
- There were 7.2 excess CHD cases per 100 smokers over 8 years.

This simple example shows why cohorts pair naturally with both relative and absolute measures. They help answer etiologic and policy questions at the same time.

### Section 7: Real-world example - the British doctors study
The British doctors study is one of the classic cohort studies in epidemiology. Physicians were classified by smoking status and followed for mortality outcomes over decades. The long-term follow-up showed large differences in lung cancer and all-cause mortality by smoking exposure, and later analyses also demonstrated the benefits of cessation.

This study is often taught because exposure preceded disease, multiple outcomes could be studied, repeated follow-up strengthened inference, and both absolute and relative risks could be communicated clearly.

### Section 8: Common sources of bias in cohort studies
Several recurring problems deserve attention.

- **Confounding:** smokers may differ from non-smokers in income, occupation, alcohol use, or access to care.
- **Selection bias at entry:** if cohort inclusion depends on factors related to both exposure and outcome, estimates may already be distorted at baseline.
- **Loss to follow-up:** if higher-risk exposed participants disappear from follow-up more often than others, associations may be biased.
- **Information bias:** poor exposure classification or inconsistent outcome ascertainment can weaken validity.
- **Immortal time bias:** if exposure groups are defined using future information, part of the follow-up may be misclassified as guaranteed survival time.

Modern cohort reporting increasingly emphasizes explicit eligibility criteria, aligned time zero, and target-trial logic to reduce these design failures.

### Section 9: Practical design questions before launching a cohort
Before building or interpreting a cohort, ask:

1. How is the exposure defined, and when is it measured?
2. When exactly does follow-up begin?
3. How are outcomes ascertained, and are definitions comparable across groups?
4. Which confounders are essential to measure?
5. How much loss to follow-up is likely, and how will it be handled?
6. Is person-time or time-to-event analysis needed?

If those questions are vague, the cohort is probably not yet well designed.

## Key takeaways
- Cohort studies begin with exposure status and follow participants for outcomes.
- They are strong for temporality, incidence estimation, and studying multiple outcomes from one exposure.
- Prospective and retrospective cohorts can both be valid if time zero, eligibility, and follow-up are clearly defined.
- The main threats are confounding, selection bias, information bias, and informative loss to follow-up.
- Cohort studies work best when exposure definition, outcome ascertainment, and censoring rules are explicit from the start.

## Self-check questions
1. What is the defining structural feature of a cohort study?
2. Why can cohort studies estimate incidence directly while case-control studies usually cannot?
3. When might a retrospective cohort be more practical than a prospective cohort?
4. Why is loss to follow-up a threat to validity rather than just an inconvenience?
5. What is time zero, and why does it matter so much in cohort design?
6. Name two common biases that can distort a cohort estimate even when follow-up is long.

## Answer key
1. Participants are grouped by exposure status before outcome occurrence is counted over follow-up.
2. Because the cohort design observes the population at risk over time, making risks, rates, and person-time estimable.
3. When high-quality historical records already exist and waiting years for prospective follow-up would be inefficient.
4. Because attrition may be related to both exposure and prognosis, producing biased comparisons between groups.
5. Time zero is the moment follow-up starts; if it is misaligned with eligibility or exposure definition, bias can be introduced immediately.
6. Examples include confounding, selection bias at entry, information bias, immortal time bias, and informative censoring.

## Further reading
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)
- [STROBE checklists](https://www.strobe-statement.org/checklists/)
- [British doctors study, 50-year follow-up](https://pubmed.ncbi.nlm.nih.gov/15213107/)
- [BMJ TARGET statement on target trial emulation](https://www.bmj.com/content/390/bmj-2025-087179)

## Links to Metis library
- `knowledge/library/methods/study-designs.md`
- `knowledge/library/methods/causal-inference.md`
- `knowledge/library/methods/biostatistics-essentials.md`
