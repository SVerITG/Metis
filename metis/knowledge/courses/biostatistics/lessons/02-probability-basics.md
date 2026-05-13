# Probability Basics

## Learning objectives
- Explain probability as a formal way of expressing uncertainty.
- Use basic probability rules for complements, addition, and multiplication.
- Interpret conditional probability and independence in epidemiologic settings.
- Apply Bayes reasoning to diagnostic testing and low-prevalence surveillance.

## Prerequisites
- Descriptive statistics.

## Content

### Section 1: What probability is for
Probability is a language for uncertainty. It helps quantify how likely an event is under a defined set of assumptions or within a reference population. In epidemiology, probability underlies risk estimates, diagnostic interpretation, confidence intervals, and many model-based decisions.

A probability always refers to an event and a reference set. Saying that the probability of disease is 0.20 means little unless you specify among whom, over what period, and under what conditions. This is why probability is not only arithmetic. It is also a framing exercise.

Probabilities range from 0 to 1:

- `0` means the event is impossible under the stated setup
- `1` means the event is certain under the stated setup
- values in between express varying uncertainty

### Section 2: Events, complements, and simple rules
An **event** is an outcome or set of outcomes of interest. Examples include "a test is positive," "a person develops disease," or "a case is reported within 48 hours."

The **complement** of an event is simply "not that event." If the probability of disease is `P(D)`, then the probability of no disease is:

\[
P(not\ D) = 1 - P(D)
\]

Two basic rules are especially useful.

For **either-or** events that cannot both happen at once:

\[
P(A\ or\ B) = P(A) + P(B)
\]

For **both-and** thinking:

\[
P(A\ and\ B) = P(A) \times P(B|A)
\]

That second rule leads naturally to conditional probability.

### Section 3: Conditional probability
Conditional probability asks how likely an event is **given** that some other information is already known. This is written as:

\[
P(A|B)
\]

which reads as "the probability of A given B."

This is fundamental in public health. Diagnostic interpretation, outbreak triage, and surveillance verification all depend on revising probability once new information becomes available.

For example:

- `P(disease | positive test)` is not the same as `P(positive test | disease)`
- `P(outbreak | unusual signal)` is not the same as `P(unusual signal | outbreak)`

That distinction is one of the most common beginner stumbling points.

### Section 4: Independence
Two events are **independent** if knowing one does not change the probability of the other.

Formally:

\[
P(A|B) = P(A)
\]

In practice, true independence is uncommon in epidemiology because many health-related events share causes or context. Exposure, infection, diagnosis, and care-seeking are often linked.

Still, the idea matters because many statistical calculations start from an independence assumption. If that assumption is badly violated, standard errors and probability calculations can mislead. This is one reason clustered data, repeated measures, and household transmission patterns need special handling.

### Section 5: Bayes intuition
Bayes reasoning tells us how to update probability after observing new evidence. The formal equation can look intimidating, but the intuition is simple: the post-test probability depends on both the quality of the evidence and the baseline probability before the evidence arrived.

In epidemiology, the baseline probability is often the **prevalence** or pre-test probability. The new evidence may be a test result, symptom pattern, or epidemiologic link.

This matters because a highly specific test does not automatically produce a high probability of true disease after a positive result. If the disease is very rare, false positives may still dominate positive results.

That is the core practical lesson of Bayes reasoning for epidemiologists.

### Section 6: Worked example - positive predictive value in low prevalence
Imagine a screening test has:

- sensitivity = 95%
- specificity = 99%
- disease prevalence = 0.1%

Now apply the test to 10,000 people.

Expected numbers:

- true cases: `10`
- non-cases: `9,990`
- true positives: `9.5` or about `10`
- false negatives: about `0.5`
- false positives: `99.9` or about `100`

So after testing, there are roughly `110` positive results, but only about `10` are true positives.

The positive predictive value is therefore about:

\[
\frac{10}{110} \approx 9\%
\]

Interpretation:
- Even with strong test characteristics, most positive results are false positives in this low-prevalence setting.

This is why elimination and post-elimination programmes often rely on confirmatory algorithms rather than one positive screening result alone.

### Section 7: Diagnostic thinking and surveillance
Probability basics become operational very quickly in public-health work.

In diagnostic evaluation:

- sensitivity is `P(test positive | disease)`
- specificity is `P(test negative | no disease)`
- positive predictive value is `P(disease | test positive)`

Those are not interchangeable quantities.

In surveillance:

- the probability that a signal reflects a true event depends on baseline event frequency, reporting quality, and the characteristics of the signal source
- a rumor in a high-risk context may deserve a different response than the same rumor in a low-risk context

Conditional thinking is therefore central to triage, verification, and resource allocation.

### Section 8: Common mistakes in beginner probability
Several mistakes recur often.

- Confusing `P(test positive | disease)` with `P(disease | test positive)`
- Ignoring the baseline prevalence or pre-test probability
- Assuming independence where events are actually correlated
- Treating probability as a property of the person rather than of the defined scenario
- Using formulas without stating what the event and reference set are

The fix is usually conceptual clarity, not more algebra. Write down the event, the conditioning information, and the population you are talking about.

### Section 9: Why probability matters before inference
Probability is not only the foundation of formal hypothesis testing later in the course. It also sharpens plain-language reasoning. Once you think conditionally, you become less likely to overinterpret a positive test, a surveillance alert, or a rare event cluster.

That makes probability one of the most practical parts of biostatistics for epidemiologists. It helps translate uncertainty into better decisions rather than false certainty.

## Key takeaways
- Probability quantifies uncertainty for clearly defined events in a clearly defined reference set.
- Conditional probability is central to diagnosis, surveillance, and risk assessment.
- Independence means one event does not change the probability of another, but this assumption often fails in real epidemiologic data.
- Bayes reasoning updates probability using both prior prevalence and new evidence.
- In low-prevalence settings, positive predictive value can be low even when a test has strong sensitivity and specificity.

## Self-check questions
1. What is the difference between `P(disease | positive test)` and `P(positive test | disease)`?
2. Why does low prevalence reduce positive predictive value?
3. What does it mean for two events to be independent?
4. Why is probability always tied to a reference set or context?
5. In a public-health program, why might one positive screening result not be enough for action?
6. What is one common conceptual error beginners make with conditional probability?

## Answer key
1. The first is the probability that disease is present after a positive result; the second is the probability that the test turns positive among those who truly have disease.
2. Because when disease is rare, the pool of non-diseased people is large enough that even a small false-positive rate can generate many false positives.
3. It means that knowing whether one event occurred does not change the probability of the other.
4. Because a probability statement is only meaningful when you specify among whom and under what conditions the event is being considered.
5. Because the post-test probability may still be too low, especially in low-prevalence settings, so confirmatory testing is needed before major action.
6. Confusing the probability of the evidence given disease with the probability of disease given the evidence.

## Further reading
- [OpenIntro Statistics](https://www.openintro.org/book/os/)
- [Khan Academy probability library](https://www.khanacademy.org/math/statistics-probability/probability-library)
- [CDC Principles of Epidemiology](https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/index.html)

## Links to Metis library
- `knowledge/library/methods/diagnostic-test-evaluation.md`
- `knowledge/library/methods/biostatistics-essentials.md`
- `knowledge/library/methods/surveillance-systems.md`
