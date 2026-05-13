# Case-Control Studies

## Learning objectives
- Explain how case-control studies sample on outcome status rather than exposure status.
- Describe how valid control selection anchors the design.
- Calculate and interpret the odds ratio in a case-control study.
- Recognize major threats to validity, especially selection bias, recall bias, and misclassification.

## Prerequisites
- Measures of association and study designs overview.
- Basic familiarity with odds ratios.

## Content

### Section 1: The core logic of a case-control study
A case-control study starts with people who have the outcome of interest and compares them with people who do not have that outcome. Investigators then look backward to assess whether prior exposures differed between the two groups. This makes the design efficient when the outcome is rare, when rapid answers are needed, or when following a large cohort would be impractical.

The key point is that the design samples on **outcome status**, not exposure. Because of that, case-control studies usually cannot estimate incidence directly. What they can estimate well is whether exposure was more common among cases than among comparable controls.

This is why case-control studies are common in outbreak investigation, rare-disease epidemiology, and early analytic phases of urgent public-health work.

### Section 2: The source population and why controls matter
The single most important design question is: **from what population did the cases arise?** Controls should represent the exposure distribution in that same source population, had those controls become cases.

If the controls do not come from the same underlying population, the comparison becomes distorted. That is why control selection is the central discipline of case-control work.

Good controls are not necessarily "healthy" people in a vague sense. They are people who were eligible to become cases under the same case definition, during the same period, in the same catchment population, but who did not develop the outcome being studied.

Common control sources include:

- community controls
- hospital or clinic controls
- controls sampled from registries or administrative records
- outbreak-specific controls drawn from attendees at the same event

Each option has trade-offs. Hospital controls may be convenient but can create bias if hospital attendance is related to the exposure. Community controls may be more representative, but harder to recruit quickly. In outbreak investigations, the most defensible controls are often people drawn from the same meal, school, facility, or gathering where exposure opportunities were shared.

### Section 3: Why the odds ratio is central
Because case-control studies sample on outcome rather than following a population at risk, the natural effect measure is the **odds ratio (OR)**.

For a standard two-by-two table:

\[
OR = \frac{a \times d}{b \times c}
\]

where:

- `a` = exposed cases
- `b` = exposed controls
- `c` = unexposed cases
- `d` = unexposed controls

The odds ratio compares the odds of exposure among cases with the odds of exposure among controls. If the OR is greater than 1, exposure was more common among cases. If it is less than 1, exposure was less common among cases, suggesting a protective association.

When the outcome is rare, the OR often approximates the risk ratio. When the outcome is common, that approximation becomes weaker, so interpretation should stay precise.

### Section 4: Worked example from an outbreak investigation
Imagine investigators examine a wedding-associated gastroenteritis outbreak. They identify 60 cases and 120 controls from the guest list and ask whether participants ate chicken salad.

- Cases exposed: 42
- Cases unexposed: 18
- Controls exposed: 30
- Controls unexposed: 90

The odds ratio is:

\[
OR = \frac{42 \times 90}{30 \times 18} = 7.0
\]

Interpretation:
- The odds of having eaten chicken salad were 7 times higher among cases than among controls.

That is a strong signal that chicken salad is the likely outbreak vehicle. The study still needs to be interpreted alongside interview quality, food histories, and laboratory or environmental evidence, but the design gives a fast analytic answer that can support control measures.

This example also shows why case-control studies are operationally valuable. Investigators could move quickly from suspicion to actionable evidence.

### Section 5: Major strengths of case-control studies
Case-control studies are especially useful when:

- the disease is rare
- the latent period is long
- the question involves multiple possible exposures
- time and resources are limited

They can be completed far more quickly than many cohort studies and often require much smaller sample sizes.

Case-control designs are also flexible. Variants such as nested case-control, matched case-control, and case-crossover designs allow investigators to tailor the design to the data structure and scientific question.

### Section 6: Major weaknesses and bias risks
The major weakness is vulnerability to bias.

**Selection bias** is the biggest threat. If controls are chosen in a way that distorts the exposure distribution of the source population, the OR may be biased even before analysis begins.

**Recall bias** is another classic problem. Cases may think harder about past exposures than controls, especially if the exposure has already been mentioned in the media or by clinicians.

**Interviewer bias** can occur when interviewers probe cases more intensively than controls.

**Exposure misclassification** can weaken or distort associations if records are incomplete or recall is poor.

**Temporality** can also be difficult. Because exposure is often assessed after the outcome has occurred, some studies struggle to show that exposure clearly preceded disease.

These problems do not make case-control studies weak by definition, but they do mean that discipline in design and measurement matters enormously.

### Section 7: Matching and when to use it carefully
Some case-control studies match cases and controls on factors such as age, sex, neighborhood, or facility. Matching can improve efficiency and help control strong confounders, but it is not automatically helpful.

Overmatching can be a problem. If you match on a factor that is closely related to the exposure of interest, you may remove the very contrast you hoped to study. Matching also affects the analysis plan, because matched designs require matched analytic methods.

Match only when there is a clear design reason, not because it seems automatically more rigorous.

### Section 8: Real-world design logic
Case-control studies are often the preferred design in early analytic outbreak work. If a group of conference attendees became ill after multiple shared meals, investigators can define cases based on symptoms and timing, select controls from non-ill attendees, and compare food exposures rapidly. The result may be enough to identify a contaminated item, remove it, and prevent more illness.

They are also widely used for rare conditions where cohort follow-up would be unrealistic. In that setting, the design trades direct incidence estimation for efficiency.

### Section 9: Questions to ask before trusting a case-control study
Before accepting the result, ask:

1. Were cases defined consistently and appropriately?
2. Do the controls reflect the exposure distribution of the same source population?
3. Was exposure measured similarly in cases and controls?
4. Could recall, interviewer behavior, or record quality differ across groups?
5. Was matching used, and if so, was it justified?
6. Does the interpretation stay within what an odds ratio can actually tell you?

If those questions are weakly answered, a precise-looking odds ratio may still be misleading.

## Key takeaways
- Case-control studies sample on outcome status and compare prior exposures between cases and controls.
- Their main strength is efficiency, especially for rare diseases and outbreak investigations.
- The odds ratio is the core effect measure because incidence usually cannot be estimated directly.
- Control selection is the design feature most likely to determine whether the study is credible.
- Recall bias, selection bias, interviewer bias, and exposure misclassification are recurring threats.

## Self-check questions
1. What is the defining structural feature of a case-control study?
2. Why can case-control studies usually not estimate incidence directly?
3. What should controls represent in a valid case-control study?
4. Why are case-control studies often preferred during outbreak investigations?
5. What is recall bias, and why is it especially relevant here?
6. Why can matching sometimes make a case-control study worse rather than better?

## Answer key
1. Participants are sampled based on outcome status, and prior exposures are then compared between cases and controls.
2. Because the design does not follow a full population at risk over time; it samples from outcomes rather than observing incidence denominators directly.
3. They should reflect the exposure distribution in the same source population that produced the cases.
4. Because they are fast, efficient, and can evaluate multiple exposures without waiting for new outcomes to occur.
5. Recall bias occurs when cases remember or report past exposures differently from controls, which can distort the odds ratio.
6. Because overmatching can remove meaningful exposure differences and may complicate the analysis without improving validity.

## Further reading
- [CDC Field Epidemiology Manual](https://academic.oup.com/book/34988)
- [STROBE checklists](https://www.strobe-statement.org/checklists/)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `knowledge/library/methods/study-designs.md`
- `knowledge/library/methods/outbreak-investigation.md`
- `knowledge/library/methods/causal-inference.md`
