# Study Designs Overview

## Learning objectives
- Compare descriptive, observational analytic, and experimental study designs.
- Match common epidemiologic questions to suitable study designs.
- Recognize the main trade-offs between speed, validity, feasibility, ethics, and cost.
- Explain why design choice should be driven by the question, not by habit or convenience.

## Prerequisites
- Lessons 1 to 3.
- Basic familiarity with disease frequency and measures of association.

## Content

### Section 1: Why study design matters
Study design is the structural plan for answering a research or public-health question. It determines who is included, when measurements are taken, how groups are compared, and what kinds of inferences are plausible. A strong analysis cannot fully rescue a weak design.

A useful starting point is to ask four questions:

1. What is the exact question: description, causation, prediction, or evaluation?
2. Is the outcome rare or common?
3. Can exposure or intervention be assigned ethically?
4. How quickly is an answer needed?

Those questions narrow the design options quickly. If you want to describe current burden, a cross-sectional survey may be enough. If you want to estimate whether an exposure preceded an outcome, a cohort study is stronger.

### Section 2: Descriptive designs
Descriptive designs summarize health events by person, place, and time. They often come first in epidemiology because they help define the problem before formal hypothesis testing.

Common descriptive designs include:

- **Case reports and case series:** useful for unusual presentations, early outbreak signals, or adverse events.
- **Routine surveillance summaries:** useful for trend monitoring and early detection.
- **Ecological comparisons:** useful when data are available only at group level.
- **Cross-sectional prevalence surveys:** useful for estimating current burden in a defined population.

These designs are often fast and operationally useful, but limited for causal inference. A case series can identify a pattern; it cannot establish whether an exposure caused that pattern. An ecological comparison may suggest a policy effect, but group-level associations can mislead if individual-level confounding is substantial.

The practical strength of descriptive work is hypothesis generation.

### Section 3: Observational analytic designs
Observational analytic studies compare groups without assigning exposure. They are central to epidemiology because many important exposures cannot be randomized, including smoking, poverty, pollution, occupation, or vector exposure.

The three core designs are:

- **Cohort studies:** begin with exposure status and follow participants for outcomes. These are strong for temporality and incidence estimation.
- **Case-control studies:** begin with outcome status and compare previous exposures. These are efficient for rare diseases and outbreak investigations.
- **Cross-sectional analytic studies:** measure exposure and outcome at the same time. These are useful for prevalence and exploratory analysis, but weak for temporality.

Each design makes a different trade-off. Cohort studies are often more intuitive and stronger for time ordering, but they may be expensive or inefficient for rare outcomes. Case-control studies are efficient and fast, but control selection and recall bias become critical. Cross-sectional studies are practical for service planning and hypothesis generation, but often cannot tell whether exposure preceded disease.

### Section 4: Experimental and quasi-experimental designs
Experimental designs actively introduce or allocate an intervention. The most familiar example is the randomized controlled trial.

**Randomized controlled trials (RCTs)** assign participants or clusters to intervention and comparison groups using randomization. That feature helps balance measured and unmeasured confounding, making trials especially strong for causal inference.

In public health, however, individual randomization is not always realistic. Interventions are often delivered to clinics, schools, villages, or districts. That is why epidemiologists also use:

- **Cluster-randomized trials**
- **Stepped-wedge trials**
- **Pragmatic trials**
- **Quasi-experimental designs**, such as interrupted time series or controlled before-after studies

Quasi-experimental approaches are valuable when a policy or service change is rolled out and randomization is impossible.

### Section 5: Choosing the right design for the question
The same topic can require different designs depending on what you need to know.

If a ministry asks, "How common is hypertension in adults this year?" a cross-sectional survey is a reasonable design. If the question becomes, "Does long-term air pollution increase the risk of incident hypertension?" a cohort design is more appropriate. If the question shifts again to, "Did a new salt-reduction policy reduce mean blood pressure at population level?" then an interrupted time-series or controlled policy evaluation may be the right choice.

The design should follow the question, not the dataset already available. In practice, researchers sometimes force causal questions into descriptive datasets because the data are convenient. That usually produces weak inference dressed up as confidence.

### Section 6: Worked example - choosing a design for a screening intervention
Imagine a district wants to test whether a community-based screening strategy for human African trypanosomiasis improves case detection compared with standard passive detection.

Several designs are possible:

- A **before-after comparison** would be fast, but weak, because temporal changes in case numbers could reflect seasonal variation, mobility, diagnostics, or broader health-system shifts.
- A **cross-sectional survey** could estimate coverage at a point in time, but would not evaluate the intervention effect well.
- A **cluster-randomized trial** could randomize health areas to screening strategies and compare case detection, referral completion, or time to treatment.
- A **stepped-wedge design** could be attractive if all areas are expected to receive the intervention eventually and rollout must occur in phases.

The "best" design depends on ethics, logistics, sample size, timing, and whether the intervention is already politically committed.

### Section 7: Real-world design logic in outbreak work
Outbreak investigation often illustrates design pragmatism well. Early in an outbreak, descriptive analysis usually comes first: epidemic curves, maps, and basic summaries. Once a likely source is suspected, investigators may choose a retrospective cohort study if the exposed population is well defined, such as attendees at one wedding. If the affected population is less clearly bounded, a case-control study is often more efficient.

This is a useful reminder that study designs are tools, not status markers. An outbreak case-control study may be more appropriate and more actionable than a slow cohort design, even if a cohort would look more elegant on paper.

### Section 8: Common mistakes when discussing design
Beginners often make four recurring mistakes.

- **Mistaking labels for quality.** Calling a study a cohort or trial does not guarantee credibility; implementation details still matter.
- **Ignoring time zero.** If follow-up does not begin at a defensible starting point, bias can be introduced immediately.
- **Overlooking selection mechanisms.** Who enters the study, and who does not, can strongly shape the final estimate.
- **Choosing the design that is easiest to analyze rather than the one that best answers the question.**

Another common mistake is to discuss design without discussing reporting. For observational studies, STROBE helps authors report what they actually did. For randomized trials, CONSORT plays a similar role. Newer target-trial framing also pushes researchers to define eligibility, time zero, intervention strategies, and outcomes more explicitly.

## Key takeaways
- Study design is the structural plan for answering an epidemiologic question.
- Descriptive designs are useful for burden estimation and hypothesis generation, but limited for causal inference.
- Cohort, case-control, and cross-sectional studies make different trade-offs in temporality, efficiency, and bias.
- Randomized and quasi-experimental designs are especially useful for intervention evaluation.
- The research or policy question should determine the design, not the convenience of the available data.

## Self-check questions
1. What is the main difference between descriptive and analytic designs?
2. Why are cohort studies generally stronger than cross-sectional studies for establishing temporality?
3. Why are case-control studies often preferred for rare outcomes or outbreak investigations?
4. What makes randomized trials especially valuable for causal inference?
5. In what situation might a stepped-wedge design be preferable to an individually randomized trial?
6. Why can a before-after comparison give a misleading answer about intervention effectiveness?

## Answer key
1. Descriptive designs summarize patterns and burden, while analytic designs explicitly compare groups to test hypotheses about associations or effects.
2. Because cohort studies begin with exposure status and observe outcomes over time, making the exposure-outcome sequence clearer.
3. Because they are efficient when the outcome is uncommon or when rapid field investigation is needed, and they do not require following a large population over time.
4. Randomization helps balance confounding factors across groups, strengthening internal validity.
5. When an intervention must be rolled out in phases, contamination is likely, or withholding the intervention permanently is not acceptable.
6. Because changes over time may be caused by secular trends, seasonality, diagnostic shifts, or unrelated system changes rather than the intervention itself.

## Further reading
- [CDC Principles of Epidemiology, Lesson 1](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/lesson1/index.html)
- [STROBE Statement](https://www.strobe-statement.org/)
- [CONSORT Statement](https://www.consort-statement.org/)
- [BMJ TARGET statement on target trial emulation](https://www.bmj.com/content/390/bmj-2025-087179)

## Links to Metis library
- `knowledge/library/methods/study-designs.md`
- `knowledge/library/methods/causal-inference.md`
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/surveillance-systems.md`
