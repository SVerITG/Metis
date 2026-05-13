# Measures of Disease Frequency

## Learning objectives
- Distinguish prevalence, cumulative incidence, incidence rate, and attack rate.
- Match each frequency measure to the study question and data structure.
- Use person-time correctly when follow-up differs across participants.
- Recognize common denominator mistakes that make disease frequency misleading.

## Prerequisites
- Lesson 1: What Is Epidemiology?

## Content

### Section 1: Why frequency measures matter
Before you can compare groups, identify risk factors, or evaluate interventions, you need to describe how often disease or health events occur. Measures of disease frequency are the language epidemiologists use to answer questions such as:

- How common is this problem right now?
- How many new cases are appearing?
- Is transmission increasing or declining?
- Which denominator makes sense for this event?

These measures seem straightforward, but beginners often mix them up. A prevalence estimate may be used when incidence is needed. A denominator may include people who were never at risk. A rate may be described as a "risk" even though it was calculated with person-time. Those errors are not just technical. They can change the public-health conclusion.

### Section 2: Prevalence - how much disease exists
**Prevalence** describes the proportion of a population with a condition at a specified time or during a specified period.

There are two common forms:

- **Point prevalence:** proportion with the condition at one moment
- **Period prevalence:** proportion who had the condition at any point during a defined interval

The basic formula for point prevalence is:

`Prevalence = existing cases / total population`

Prevalence is useful for describing burden. It is commonly used in surveys, service planning, and chronic disease monitoring. If a ministry of health wants to know how much hypertension, diabetes, depression, or disability currently exists in a population, prevalence is often the right measure.

However, prevalence mixes two things:

- how often new cases occur
- how long people remain in the diseased state

That means a disease can have high prevalence because incidence is high, because duration is long, or both. A condition with low incidence but very long survival can still have high prevalence. Conversely, a very rapidly fatal disease may have modest prevalence even if new cases occur frequently.

### Section 3: Incidence - how many new events occur
**Incidence** focuses on new cases or new events over time. This is usually more informative than prevalence for causal questions, prevention, and intervention evaluation because it captures disease occurrence, not just disease burden.

Two major incidence measures are used.

**Cumulative incidence** is the proportion of initially disease-free individuals who develop the outcome during a defined period.

Formula:

`Cumulative incidence (risk) = new cases during follow-up / number at risk at start`

This is also called **risk**. It is easy to interpret: "the probability of developing the outcome over this period."

**Incidence rate** uses person-time instead of persons as the denominator.

Formula:

`Incidence rate = new cases / total person-time at risk`

This is useful when participants enter or leave at different times, are lost to follow-up, die, or are observed for unequal durations. It is common in cohort studies, surveillance systems, and routine program datasets where observation time is uneven.

### Section 4: Risk versus rate
Risk and rate are related but not identical.

Risk is a probability over a defined interval. It must be between 0 and 1, or between 0% and 100%.

Rate is an occurrence measure per unit of person-time, such as per 1,000 person-years. A rate is not a probability. It summarizes how quickly events are arising.

Beginners often say, "The incidence rate was 12%, so the risk was 12%." That is not always correct. When events are rare and time intervals are short, rate and risk may be numerically similar. But conceptually they are different and should not be used interchangeably.

### Section 5: Attack rate and secondary attack rate
During outbreaks, epidemiologists often use **attack rate**. Despite the name, it is really a short-term cumulative incidence measure.

Formula:

`Attack rate = new cases during outbreak period / population at risk during outbreak period`

If 45 people at a wedding ate lunch and 18 developed acute gastroenteritis within 48 hours, the overall attack rate is:

`18 / 45 = 0.40 = 40%`

You can also calculate **food-specific attack rates** by exposure group and compare them to generate hypotheses.

**Secondary attack rate** focuses on spread among contacts of primary cases.

Formula:

`Secondary attack rate = new cases among contacts / susceptible contacts exposed`

This is especially useful in household transmission studies, schools, dormitories, or institutional outbreaks.

### Section 6: Choosing the right denominator
The denominator should represent the population truly at risk of experiencing the event.

This sounds obvious, but it is one of the most common sources of error in beginner epidemiology.

Examples:

- For incidence of cervical cancer, the denominator should not include people without a cervix.
- For maternal mortality ratios, the denominator is usually live births, not the total female population.
- For occupational injury frequency in miners, the denominator should reflect the workforce at risk, not all district residents.
- For facility-based surveillance, the denominator may be the catchment population, but only if catchment assumptions are credible.

If the denominator is poorly defined, the resulting frequency measure can look precise while being conceptually wrong.

### Worked numerical example 1: prevalence versus cumulative incidence
Suppose a district survey on 1 July includes 2,000 adults. Among them, 160 currently have hypertension.

Point prevalence of hypertension:

`160 / 2000 = 0.08 = 8%`

Now imagine that among the 1,840 adults who did not have hypertension at baseline, 92 develop hypertension over the next 12 months.

Cumulative incidence over 12 months:

`92 / 1840 = 0.05 = 5%`

Interpretation:

- On 1 July, 8% of adults were living with hypertension.
- Over the following year, 5% of those initially free of hypertension became new cases.

These measures answer different questions. Prevalence tells you how much hypertension exists now. Incidence tells you how often new hypertension is occurring.

### Worked numerical example 2: incidence rate with person-time
Imagine a cohort of 5 participants followed for tuberculosis recurrence:

| Participant | Follow-up time | Event? |
|-------------|----------------|--------|
| A | 12 months | Yes |
| B | 12 months | No |
| C | 8 months | Yes |
| D | 6 months | Lost to follow-up |
| E | 12 months | No |

Total person-time:

`12 + 12 + 8 + 6 + 12 = 50 person-months`

New events:

`2`

Incidence rate:

`2 / 50 = 0.04 events per person-month`

This could also be written as:

`4 events per 100 person-months`

Why not just use cumulative incidence? Because not everyone was observed for the same amount of time. Person-time gives a more honest denominator.

### Real-world case study: Framingham and risk over time
The Framingham Heart Study became famous partly because it used longitudinal follow-up to estimate risk of developing cardiovascular outcomes. That is classic incidence thinking. Participants free of disease at baseline were followed over time, allowing investigators to estimate who developed new disease and how those new events related to blood pressure, smoking, cholesterol, and other factors.

If Framingham had only reported baseline prevalence of coronary disease, it would have been far less useful for causal thinking. Incidence made temporality visible.

### Real-world public-health example: elimination settings
In elimination or post-elimination surveillance, prevalence and incidence can point in different directions. Suppose an active screening campaign in a low-prevalence disease setting finds very few existing cases. That low prevalence may look reassuring. But if routine passive surveillance still identifies a steady stream of new confirmed cases in certain foci, incidence tells you transmission has not truly stopped.

This is why prevalence alone can be misleading in elimination programs. For planning service need, prevalence may be useful. For judging whether transmission continues, incidence is often more important.

### Common pitfalls and misconceptions
**Pitfall 1: Using prevalence to infer cause.**  
Prevalence is often influenced by disease duration and survival, so it may not reflect current causal pressure well.

**Pitfall 2: Calling everything "incidence."**  
Incidence requires new cases over time. A one-time survey of existing diabetes cases measures prevalence, not incidence.

**Pitfall 3: Using the wrong at-risk population.**  
A denominator should exclude people who cannot experience the event.

**Pitfall 4: Forgetting the time component.**  
If you say "incidence was 3%," the listener should ask, "Over what period?"

**Pitfall 5: Mixing rate and risk language.**  
An incidence rate per person-year is not automatically the same as probability of disease over a year.

### Practical rule of thumb
Ask three questions before choosing a measure:

1. Am I counting **existing** or **new** cases?
2. Is there a defined **time period**?
3. Do all individuals contribute the **same follow-up time**, or do I need person-time?

If you answer those correctly, you will usually choose the right frequency measure.

## Key takeaways
- Prevalence measures existing disease burden; incidence measures new occurrence.
- Cumulative incidence is a risk over time; incidence rate uses person-time.
- Attack rate is a short-term outbreak form of cumulative incidence.
- Denominators must represent the true population at risk.
- Frequency measures answer different questions, so choosing the wrong one can mislead policy and analysis.

## Self-check questions
1. Why can prevalence be high even when incidence is low?
2. What is the difference between cumulative incidence and incidence rate?
3. When is person-time preferable to a simple count of persons?
4. In an outbreak investigation, why is attack rate usually more useful than point prevalence?
5. A cohort begins with 500 disease-free participants. Over one year, 25 develop the outcome. What is the cumulative incidence?
6. In the same cohort, total follow-up equals 450 person-years because of deaths and loss to follow-up. What is the incidence rate?
7. Give one example of a denominator that would be clearly inappropriate for a frequency measure.

## Answer key
1. Because prevalence depends on both incidence and duration. A disease with long survival or chronic duration can accumulate many existing cases even if few new cases occur each year.
2. Cumulative incidence is the proportion at risk who become cases during a defined interval. Incidence rate is the number of new cases divided by person-time at risk.
3. When follow-up time differs across individuals, such as with losses to follow-up, staggered entry, competing events, or open cohorts.
4. Because attack rate measures the proportion becoming ill during the outbreak period among those exposed or at risk, which is directly relevant to transmission and source investigation.
5. `25 / 500 = 0.05`, so cumulative incidence is 5% over one year.
6. `25 / 450 = 0.0556 per person-year`, or about 5.6 cases per 100 person-years.
7. Examples include using the entire population as the denominator for cervical cancer incidence, using all district residents for an occupational injury measure, or including already diseased people in the denominator for cumulative incidence of first occurrence.

## Further reading
- [CDC Principles of Epidemiology, Lesson 3](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/lesson3/index.html)
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [WHO screening resources](https://www.who.int/europe/teams/noncommunicable-diseases/screening)
- [Framingham Heart Study overview](https://framinghamheartstudy.org/)

## Links to Metis library
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/study-designs.md`
- `knowledge/library/methods/surveillance-systems.md`
- `knowledge/library/concepts/elimination-framework.md`
