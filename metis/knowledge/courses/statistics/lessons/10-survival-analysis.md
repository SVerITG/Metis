# Survival Analysis

## Learning objectives
- Explain why time-to-event outcomes require different methods from ordinary binary analyses.
- Interpret censoring, Kaplan-Meier curves, and hazard ratios.
- Recognize when survival methods preserve important information that simpler approaches waste.
- Understand why hazard ratios should not be casually read as risk ratios.

## Prerequisites
- Confidence intervals and regression basics.

## Content

### Section 1: Why time matters
Many important epidemiologic outcomes are not only about whether an event happened, but also about **when** it happened. Examples include time from exposure to disease, time from diagnosis to relapse, time from treatment to death, or time from symptoms to diagnosis.

If you collapse such data into a simple yes/no outcome at a fixed time point, you lose information. Someone diagnosed after 3 days and someone diagnosed after 300 days both count as "diagnosed," even though their experiences are very different.

Survival analysis is designed to use both event status and event timing.

### Section 2: What censoring is
A major reason survival methods are needed is **censoring**. Censoring occurs when the exact event time is not observed for some individuals during the study period.

Common reasons include:

- the study ends before the event occurs
- the participant is lost to follow-up
- the participant withdraws
- a competing endpoint stops observation

These individuals still contribute information up to the point they were observed. That is why simply excluding them would waste information and may introduce bias.

### Section 3: Kaplan-Meier curves
The **Kaplan-Meier curve** estimates the probability of remaining event-free over time. It is a descriptive tool that shows how survival or event-free experience evolves during follow-up.

Kaplan-Meier curves are useful because they allow you to:

- compare groups visually
- see when events are happening
- inspect separation or crossing of curves
- estimate median survival or event-free time when relevant

In epidemiology, the term "survival" is often retained even when the event is not death. The same methods apply to relapse, diagnosis, failure, dropout, or recovery, as long as the time-to-event structure is central.

### Section 4: The hazard and hazard ratio
The **hazard** is the instantaneous event rate among those still at risk at a given time. It is not the same as risk, though the two are related.

The **hazard ratio (HR)** compares hazards between groups, often through a Cox proportional hazards model.

An HR greater than `1` suggests a higher instantaneous event rate in one group; below `1` suggests a lower rate. But hazard ratios are often overinterpreted. They do not mean the risk is multiplied by that amount at every moment, and they do not directly communicate absolute event probability.

This is why hazard ratios should be interpreted carefully and, where possible, supplemented with Kaplan-Meier summaries or absolute measures.

### Section 5: Worked example - time to diagnosis
Imagine a study compares time from symptom onset to diagnosis in two surveillance strategies.

- strategy A: community-linked referral
- strategy B: standard passive detection

If you analyze only whether diagnosis occurred by 12 months, you lose information about how quickly diagnosis occurred. A survival approach can use the full timing data and account for people who were not diagnosed before the study ended.

Suppose the Cox model gives an HR of `1.6` for strategy A versus strategy B.

Interpretation:
- at a given time during follow-up, the instantaneous rate of diagnosis is estimated to be 1.6 times as high under strategy A, assuming the model assumptions hold

This suggests faster diagnosis, but the exact public-health importance still depends on the time scale, the curve shapes, and the absolute difference in delays.

### Section 6: Proportional hazards and other assumptions
The Cox proportional hazards model is popular because it does not require specifying the baseline hazard fully. But it does assume that the hazard ratio is **proportional over time**.

If the effect changes substantially over time, this assumption may be violated. For example, an intervention may speed diagnosis early but have little effect later.

Other practical issues include:

- informative censoring
- measurement error in event time
- delayed entry or left truncation
- competing risks

As with other models, diagnostics and substantive plausibility matter. A survival model is not automatically correct just because the software runs.

### Section 7: Why survival methods are useful in epidemiology
Survival analysis is especially valuable when:

- follow-up times differ across participants
- event timing matters substantively
- censoring is common
- the event does not occur in everyone during observation

This makes it central to cohort studies, treatment follow-up, outbreak follow-up, relapse research, program retention studies, and many clinical and public-health evaluations.

### Section 8: Common mistakes
Several mistakes recur often.

- treating a hazard ratio as if it were a risk ratio
- ignoring censoring mechanisms
- reducing a time-to-event outcome to a fixed binary endpoint when timing matters
- interpreting the Cox model without checking proportional hazards
- discussing relative effects without showing curves or absolute event patterns

The practical lesson is that survival methods are not only a technical upgrade. They are often the correct design-analysis match for the question being asked.

## Key takeaways
- Survival analysis is used when both whether and when an event occurs matter.
- Censoring means some individuals have incomplete event-time information but should still contribute data up to the time observed.
- Kaplan-Meier curves provide a descriptive summary of event-free probability over time.
- Hazard ratios compare instantaneous event rates, not simple cumulative risks.
- Survival methods are often preferable to binary analyses when follow-up varies or timing itself is scientifically important.

## Self-check questions
1. What is censoring?
2. Why might a binary outcome at 12 months waste information?
3. What does a Kaplan-Meier curve show?
4. How should a hazard ratio be interpreted cautiously?
5. Why is proportional hazards an important assumption?
6. In what kinds of epidemiologic studies are survival methods especially useful?

## Answer key
1. It is incomplete observation of the event time, such as when the study ends or follow-up is lost before the event occurs.
2. Because it ignores when the event happened and treats early and late events as equivalent.
3. The estimated probability of remaining event-free over time.
4. As a comparison of instantaneous event rates among those still at risk, not as a direct risk ratio or absolute probability difference.
5. Because the Cox model assumes the hazard ratio is relatively stable over time; if it is not, the summary may mislead.
6. Cohort follow-up, relapse studies, time to diagnosis, time to treatment failure, retention analyses, and many clinical and public-health evaluations.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Cochrane Handbook](https://training.cochrane.org/handbook/current)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/study-designs.md`
- `knowledge/library/methods/causal-inference.md`
