# Lesson 2 — Detect the unusual: anomaly detection and early warning

> **Concept map**
> **Builds on** — Lesson 1: this is shape 1, and its classical comparator is Farrington/CUSUM.
> **Connects to** — Lesson 3 (forecasting) shares the machinery but answers a different question; Lesson 9 (evaluation) supplies the false-alarm and timeliness measures this lesson depends on.
> **Leads to** — Lesson 6 (clustering), where scan statistics do detection and grouping at once; and the wastewater and EIOS deep dives.

## Why this matters

This is the shape the NUST syllabus called an *Early Epidemic and Pandemic Detection
System*, and it is the oldest computational task in public health — Farr was doing a
version of it in the 1840s. It is also the shape where the gap between the marketing and
the mathematics is widest, because "AI detects outbreaks before humans do" is an
irresistible headline and an almost unfalsifiable claim.

The honest version is a trade-off you cannot escape:

> **You can have early, or you can have specific. Buying more of one always costs you the
> other, and where you set that exchange rate is a policy decision, not a technical one.**

Every algorithm in this lesson is a different way of expressing that exchange rate. None
of them abolishes it.

## Learning objectives
By the end of this lesson you will be able to:
- **Explain** why an anomaly detector is mostly a model of *expected*, and why that is where the work is.
- **Apply** the Farrington/Noufaily family to a count time series and interpret its threshold.
- **Distinguish** the three cases where machine learning genuinely adds something from the many where it does not.
- **Evaluate** a detection system on timeliness, false-alarm rate and probability of detection rather than accuracy.

## Prerequisites
Lesson 1. Comfort with count data, seasonality and overdispersion — assumed.

---

## Section 1 · An anomaly detector is a model of "expected"

Strip any aberration-detection method down and it has two parts:

1. A model of what you **expected** to see.
2. A rule for how far above expectation counts as an alarm.

Part 2 is a threshold. Part 1 is the entire scientific content. This matters because
almost all published effort goes into part 2 — the clever detector — while almost all
real-world failure comes from part 1.

What has to be inside "expected" for routine surveillance counts:

- **Secular trend.** Reporting improves; populations grow.
- **Seasonality.** Usually the dominant signal, and usually the thing a naive detector
  discovers and reports as an outbreak every winter.
- **Day-of-week and holiday effects.** Clinics close. Counts crash on Sundays and around
  public holidays, then rebound.
- **Overdispersion.** Case counts are almost never Poisson. Assuming they are makes the
  threshold too tight and the false-alarm rate explode.
- **Past outbreaks in the baseline.** If last year's epidemic is in your reference window,
  it raises "expected" and hides this year's. Every serious method downweights or removes
  historical outliers.
- **Reporting delay.** The most recent points are incomplete. Fail to correct and every
  series looks like it is declining right now.

⚠ **The failure this produces is diagnostic, not statistical.** An alarm tells you the
count exceeded expectation. It cannot tell you *why*. A new clinic opened, a case
definition changed, a lab switched assay, a data clerk caught up on a backlog, a
neighbouring district started referring — all of these produce beautiful, highly
significant, entirely administrative anomalies. In routine practice these outnumber real
outbreaks.

✱ So the first question on any alarm is never "is this statistically significant?" — the
algorithm already answered that. It is **"did the denominator or the data pipeline
change?"**

## Section 2 · The classical family — and why it is still the benchmark

### Control charts and CUSUM
Shewhart charts flag single points beyond a limit. **CUSUM** accumulates deviations, so it
detects small sustained shifts a point-wise rule misses. That distinction — sudden spike
versus slow drift — is a real design choice: CUSUM is more sensitive to gradual change and
slower on sharp jumps.

**EARS (C1/C2/C3)**, from CDC, are CUSUM-style methods built for a specific hard case: you
have almost no history. Designed for mass gatherings and post-disaster surveillance, they
use a 7-day baseline and accept crudeness as the price of working immediately. C3 adds a
short accumulation window. Useful, honest, and not to be judged as though they were trying
to be Farrington.

### Farrington, and Noufaily's improvement
The **Farrington** algorithm is the workhorse of European routine surveillance. The idea:

1. Take counts from the same **seasonal window** in previous years — the weeks around the
   current week, going back several years.
2. Fit an **overdispersed Poisson (quasi-Poisson) GLM** with a linear trend.
3. Compute a one-sided **prediction interval** for the current week.
4. Downweight historical outliers so past outbreaks do not inflate expectation.
5. Alarm if the observation exceeds the upper threshold.

**Noufaily et al.**'s revision (implemented as `farringtonFlexible`) improved several known
weak points: a better reference window, a negative-binomial-style handling of
overdispersion, improved reweighting, and better behaviour on low counts — which is exactly
the regime that matters near elimination.

✱ Notice what this family is: a **regression model with a prediction interval.** That is
all. It works because the hard part was never the detector, it was the baseline, and
Farrington puts the science in the baseline where it belongs.

**This is the comparator.** Any anomaly-detection method claiming to improve on routine
surveillance is claiming to beat this, on the same series, at a matched false-alarm rate.
If a paper does not report that comparison, apply the base rate from Lesson 1.

## Section 3 · What machine learning actually adds

Three places where it genuinely wins, and it is worth being precise, because the honest
list is short.

**1 · Many signals at once (the real one).** Farrington is univariate. Run it on 400 syndrome-by-district
series and you have 400 independent multiple-comparison problems and an unusable alarm
volume. Multivariate methods — isolation forests, autoencoders, one-class SVMs, PCA-residual
monitoring — score a whole *vector* of signals at once and can flag a pattern that is
unremarkable in every individual series. That is a real capability the classical stack
lacks.

**2 · Signals with no natural baseline.** Text, images, sequence data, mobility traces. You
cannot write a quasi-Poisson GLM for "unusual phrasing in outbreak reports". Here
representation learning is doing something classical methods cannot express at all.

**3 · Learned normality in high dimensions.** An autoencoder trained on normal data
reconstructs normal data well and abnormal data badly, and reconstruction error becomes an
anomaly score. This is elegant and genuinely useful for wearables, waveform and image data.

And where it does **not** win: a single count series with good history. On one weekly time
series with five years of data, Farrington/Noufaily is very hard to beat, and the literature
claiming otherwise usually compares at unmatched false-alarm rates or on simulated outbreaks
injected with the very shape the new method detects best.

⚠ **Unsupervised anomaly detection cannot be validated the way you want.** You have no
labels. "Anomalous" is defined by the model, so the model is definitionally right. The only
honest evaluations are: inject simulated outbreaks of known size and shape and measure
detection probability, or reconstruct historically confirmed outbreaks and measure how
early each method fired at a matched false-alarm rate.

## Section 4 · Event-based surveillance — anomaly detection on text

A separate tradition, and where the shape has moved most recently.

**EIOS** (WHO's Epidemic Intelligence from Open Sources) is the reference implementation:
continuous machine-assisted scanning of media and web sources, deduplicated, categorised
and triaged, with **human epidemiologists making the judgement**. That last clause is the
design, not a limitation — the machine manages volume, the human manages meaning.

**ProMED-mail** is the human-curated ancestor and still valuable, with real funding
fragility. **HealthMap** is the automated cousin. **BlueDot** and similar commercial services
flagged unusual pneumonia reporting from Wuhan in late December 2019.

⚠ On that last point, be precise, because it is the most over-claimed story in the field:
they surfaced a signal from open sources a few days before official international
notification. They did not predict a pandemic, and the signal was one among many that
week. The achievement is real and much smaller than the retelling.

**Where this is going:** LLM-based extraction turning free text into structured event
records — location, pathogen, case count, confidence — at a volume no human team can read.
The bottleneck moves from finding candidate signals to *verifying* them, which is exactly
the bottleneck EIOS already has.

## Section 5 · Evaluating a detection system

Accuracy is meaningless here — outbreaks are rare, so "no alarm, ever" scores extremely
well. The real measures:

| Measure | Question |
|---|---|
| **Probability of detection (POD)** | Of known outbreaks, what fraction were flagged at all? |
| **Timeliness** | How many days/weeks before the reference detection? Report the distribution, not the best case |
| **False-alarm rate** | Alarms per unit time when nothing is happening. **The currency of trust** |
| **Positive predictive value of an alarm** | Of alarms raised, how many were real? Lesson 9's arithmetic applies unchanged |
| **Alarm burden** | Alarms per week per person who must investigate them |

Two rules that follow:

1. **Never compare methods at different false-alarm rates.** Any detector looks earlier if
   allowed to alarm more often. Fix the false-alarm rate, then compare timeliness.
2. **Earlier is only better if something can be done earlier.** A signal three weeks ahead
   of confirmation is worth nothing if response requires laboratory confirmation anyway.
   This is the syndromic surveillance finding: it genuinely is earlier, and it mostly did
   not change what anyone did.

✱ Alarm fatigue is a measurable failure mode, not a soft concern. Once the PPV of an alarm
drops low enough, investigators stop investigating, and system sensitivity goes to zero
regardless of what the algorithm reports.

---

## Key insight

**The detector is the easy half.** The baseline is the science, the threshold is the policy,
and the alarm's meaning is epidemiological rather than statistical. Machine learning helps
most where the classical stack cannot express the problem at all — many signals at once, or
signals with no natural baseline — and helps least on the single well-behaved count series
that most papers use to demonstrate it.

---

## Worked example — aberration detection on a real surveillance series

Dataset: **`salmonella.agona`** from the R `surveillance` package — the canonical Farrington
demonstration series, weekly counts of *Salmonella* Agona reports. The `surveillance` package
is the reference implementation of this entire lesson's classical half.

⚠ Object and function names differ across versions of `surveillance`. Check
`data(package = "surveillance")` and the `farringtonFlexible` help page against your
installed version before assuming the code below runs verbatim. It has not been executed here.

### In R

```r
library(surveillance)
library(tidyverse)

# ---- The data ---------------------------------------------------------------
# Weekly counts of Salmonella Agona reports. Shipped as a legacy `disProg`
# object; `disProg2sts()` converts it to the modern `sts` class that the
# current algorithms expect.
data("salmonella.agona")
sts <- disProg2sts(salmonella.agona)

plot(sts, main = "Salmonella Agona, weekly reports")

# ---- Step 1: look at the baseline BEFORE choosing a detector ----------------
# This is the actual work of the lesson. Seasonality and trend are what the
# detector must be told to expect; anything you fail to model becomes an alarm.
obs <- tibble(
  week  = seq_len(nrow(sts@observed)),
  count = as.numeric(sts@observed[, 1])
)

# Overdispersion check: is a Poisson assumption defensible?
# variance/mean >> 1 means Poisson thresholds will be far too tight and the
# false-alarm rate will be much higher than nominal.
obs |> summarise(mean = mean(count), var = var(count), ratio = var(count) / mean(count))

# ---- Step 2: Farrington (Noufaily revision) --------------------------------
# b = number of past years used for the baseline
# w = half-width, in weeks, of the seasonal window around the current week
#     (so w = 3 uses a 7-week window centred on the same week in past years)
# alpha = one-sided level for the upper prediction threshold
# The reweighting step downweights past outbreaks so they do not inflate
# "expected" and mask a current one.
n_weeks <- nrow(sts@observed)
ctrl <- list(
  range         = (n_weeks - 103):n_weeks,   # score the last two years
  b             = 4,
  w             = 3,
  alpha         = 0.01,
  pastWeeksNotIncluded = 26,                 # guard against reporting delay
  weightsThreshold     = 2.58                # outlier reweighting
)

res <- farringtonFlexible(sts, control = ctrl)
plot(res, main = "Farrington/Noufaily threshold and alarms")

# ---- Step 3: what actually came out ----------------------------------------
# `upperbound` is the expected-plus-threshold; `alarm` is the flag.
out <- tibble(
  week      = ctrl$range,
  observed  = as.numeric(res@observed),
  threshold = as.numeric(res@upperbound),
  alarm     = as.logical(res@alarm)
)

# The two numbers that matter operationally: how often does this fire, and
# how much headroom does the threshold leave? An alarm rate of 10% of weeks
# means someone investigates every other week — see alarm fatigue.
out |> summarise(
  weeks       = n(),
  alarms      = sum(alarm),
  alarm_rate  = mean(alarm),
  median_headroom = median(threshold - observed)
)

# ---- Step 4: the comparison the papers skip --------------------------------
# Before believing any ML method beats this, you must fix the false-alarm rate.
# Tune alpha until the classical method fires as often as the challenger, THEN
# compare timeliness. Anything else compares a loose detector to a tight one.
sweep <- map_dfr(c(0.05, 0.01, 0.005, 0.001), function(a) {
  r <- farringtonFlexible(sts, control = modifyList(ctrl, list(alpha = a)))
  tibble(alpha = a, alarm_rate = mean(as.logical(r@alarm)))
})
sweep
# Read this as the exchange rate between early and specific. Choosing a row
# is a policy decision about who investigates how many false alarms.
```

✱ Step 4 is the lesson. That `sweep` table *is* the early-versus-specific trade-off, made
explicit and priced. Every claim of the form "our method detects outbreaks earlier" should
be accompanied by one, and almost none are.

---

## Exercises

**Recall.** Name the six components that must be in a model of "expected" for routine
weekly surveillance counts, and say which one causes a false decline in the most recent
data points.

**Application.** Run the `sweep` above. At which `alpha` does the alarm rate become
operationally tolerable for a team that can investigate one signal a week? What have you
given up in timeliness to get there?

**Application.** A district reports a statistically significant excess of malaria cases.
List the five administrative explanations you would rule out before treating it as an
epidemiological signal, in the order you would check them.

**Conceptual.** Multivariate anomaly detection is the strongest genuine case for ML in this
shape. Explain why it cannot be evaluated the same way as a univariate detector, and propose
an evaluation design that would convince you.

**Challenge.** Wastewater surveillance is listed in the Atlas under shape 1. Argue that it
is really shape 2 (forecasting). Whichever you conclude, state which evaluation measures
follow from your choice — that dependency is the point of the exercise.

---

## Connection to the course spine

Shape 1's debt, from Lesson 9, is a **false-alarm rate and a timeliness measure at a matched
threshold**. This lesson shows why: the detector is nearly interchangeable, the baseline is
the science, and the threshold is a policy choice about how many false alarms someone will
tolerate. A claim in this shape that reports neither a matched comparison nor a false-alarm
rate has not been evaluated, whatever its accuracy figure says.

And the spine's first half holds here too: Farrington is a regression model with a prediction
interval. Recognising that is what stops a new detector from looking like a new idea.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified. Leads, not citations.

**Books**
- Held, Höhle & Hofmann, *Handbook of Infectious Disease Data Analysis* — the aberration-detection chapters.
- Lawson & Kleinman, *Spatial and Syndromic Surveillance for Public Health*.

**Online**
- The `surveillance` R package vignettes — `vignette("surveillance")` and the
  `farringtonFlexible` documentation. The reference implementation of this lesson.
- WHO EIOS — the event-based surveillance reference system.
- `{EpiNow2}` / `{epinowcast}` for the reporting-delay correction this lesson only gestures at.

**Key papers**
- Farrington et al., *A statistical algorithm for the early detection of outbreaks of
  infectious disease* — JRSS-A, 1996.
- Noufaily et al., *An improved algorithm for outbreak detection in multiple surveillance
  systems* — Statistics in Medicine, 2013.
- Salmon, Schumacher & Höhle, *Monitoring count time series in R: aberration detection in
  public health surveillance.* **Journal of Statistical Software** 2016;70(10):1–35.
  ✓ **Verified 2026-08-21.**
- Lazer et al., *The parable of Google Flu: traps in big data analysis* — Science, 2014.

---

## Retain long-term

- An anomaly detector is a model of "expected" plus a threshold; the baseline is the science.
- Six things must be in the baseline: trend, seasonality, day-of-week/holiday, overdispersion, past outbreaks, reporting delay.
- An alarm is statistical; its explanation is epidemiological. Check the denominator and the pipeline first.
- Farrington/Noufaily is a quasi-Poisson GLM with a one-sided prediction interval — and it is the benchmark.
- ML genuinely adds: many signals at once; signals with no natural baseline; learned normality in high dimensions.
- Never compare detectors at different false-alarm rates.
- Earlier is only better if something can be done earlier.
- Once alarm PPV falls far enough, investigators stop investigating and system sensitivity goes to zero.
