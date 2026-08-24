# Lesson 3 — Predict what happens next: forecasting, and why the ensemble wins

> **Concept map**
> **Builds on** — Lesson 1 (shape 2 and its comparator, the seasonal-naive forecast); Lesson 2, which shares the machinery of count time series but asks a different question.
> **Connects to** — Lesson 9, which supplies the scoring vocabulary; and the Google Flu Trends deep dive, which is a shape-2 model sold as shape 1.
> **Leads to** — Lesson 8 (choosing an action), because a forecast that changes no decision is a hobby.

## Why this matters

This is the shape that carries the phrase **epidemic preparedness**. If you are going to
explain AI in public health to anyone, forecasting is where they will want to start, because
it is the one that sounds like prophecy.

It is also the shape with the most mature and most humbling evidence base — and the humbling
part is the interesting part. After a decade of organised, prospective, head-to-head
evaluation, the central empirical finding of infectious-disease forecasting is not that a
particular method wins. It is that **combining many mediocre models beats almost every
individual model, almost always**. Including the sophisticated ones. Including yours.

✱ That result is unusual in that it was *earned prospectively*, in public, under
pre-registered scoring rules, over years. Very little in health AI can say the same. Which
makes this shape the best available demonstration of what an honest evaluation culture
produces — and what it produces is humility.

## Learning objectives
By the end of this lesson you will be able to:
- **Distinguish** forecasting from nowcasting from early warning, and say why the distinction decides the evidence required.
- **Explain** why scoring a point forecast with MAE rewards over-confidence, and compute an interval score instead.
- **State** the ensemble finding and the two mechanisms behind it.
- **Identify** reporting delay as the reason recent data always looks like a decline.

## Prerequisites
Lesson 1. Familiarity with count time series and seasonality — assumed.

---

## Section 1 · Three questions people call forecasting

They need different evidence, and conflating them is the commonest error in this shape.

| | Question | Time | Example |
|---|---|---|---|
| **Nowcasting** | What is happening *right now*, given incomplete reporting? | present | Correcting this week's case count for reports not yet arrived |
| **Forecasting** | What will the number be in *k* weeks? | future | Four-week-ahead hospitalisation forecast |
| **Early warning** | Is something *unusual* starting? | present | Shape 1 — lesson 2 |

⚠ Google Flu Trends was a **nowcast**, evaluated as a nowcast, and marketed as **early
warning**. That mismatch is why its failure surprised people who had only read the marketing.

✱ And note the practical ordering: **you cannot forecast what you cannot nowcast.** If your
estimate of the present is wrong by 30%, a four-week forecast built on it is decoration.

## Section 2 · Reporting delay, and the false decline

Every routine surveillance series shares one property: **the most recent points are
incomplete.** A case occurring today is reported over the following days to weeks — through a
facility, a district, a national system. So the last few points of any real-time series are
partial counts, and they always look like a fall.

The consequence is severe and constant: **an uncorrected series appears to be declining, at
all times, including during exponential growth.** Programmes have relaxed on this artefact
more than once.

The correction is called **nowcasting** and it works by estimating the delay distribution —
how long reports take — from historical data, then inflating recent counts by the fraction not
yet expected to have arrived. `EpiNow2` and `epinowcast` implement this.

⚠ Two hazards. The delay distribution **changes** — during a surge, reporting slows; after a
system upgrade, it jumps. And the correction is largest exactly where you most want certainty:
the present.

## Section 3 · The classical toolkit, which is the comparator

**Seasonal naive.** Forecast this week's value as the value from the same week last year. Or
persistence: forecast next week as this week. **This is the baseline every method must beat**,
and for strongly seasonal diseases it is startlingly hard to beat more than a few weeks out.

**Statistical time series.** ARIMA and relatives, generalised additive models with seasonal
smooths, and for counts a negative-binomial regression with harmonic seasonal terms. Cheap,
interpretable, robust, and competitive.

**Mechanistic / compartmental models.** SIR, SEIR and their elaborations. Not statistical
descriptions but models of *transmission* — with parameters that mean something. Which buys
you the one thing statistical models cannot provide:

✱ **Only a mechanistic model can answer a counterfactual.** "What if we close schools?" is not
a question a time-series model can address, because school closure is not in its feature space.
This is the honest division of labour: statistical models for *what will happen*, mechanistic
models for *what would happen if*.

**Renewal-equation models** sit between: estimate the time-varying reproduction number *R*ₜ
from incidence and a generation-interval distribution, then project. Very widely used in 2020
and after, and they are semi-mechanistic — enough structure to interpret, not so much that
every parameter must be guessed.

## Section 4 · Where machine learning fits — and where it does not

Honest short list, again.

**Where it genuinely helps:**

- **Many predictors, unknown functional form.** Climate-driven arbovirus forecasting is the
  clearest case: rainfall, temperature, ENSO indices, vegetation, mobility, population
  structure, all with lags and interactions nobody can specify in advance. Gradient boosting on
  a lagged feature matrix does real work here.
- **Spatial and spatio-temporal borrowing.** Forecasting 500 districts jointly, letting
  data-poor districts borrow from similar ones. ⚠ Though the strongest tool here remains
  Bayesian hierarchical modelling — INLA — not machine learning. Your own ground.
- **Non-traditional data streams.** Search, mobility, wastewater as *inputs*, recalibrated
  continuously against a ground-truth series. The lesson of Google Flu Trends is not that these
  are useless; it is that they cannot stand alone.

**Where it does not help:**

- **Short series.** Weekly surveillance gives ~52 points a year. Deep learning needs data that
  routine surveillance does not have.
- **Extrapolating beyond the observed range.** A tree-based model cannot predict a value larger
  than any it has seen, which is a fatal property when forecasting an epidemic's peak. ⚠ This
  is not a tuning issue — it is what a tree does.
- **Structural breaks.** New variant, new intervention, new policy. Every model breaks here;
  ML breaks *silently*, while a mechanistic model at least has a parameter you can argue about.

## Section 5 · Scoring — where over-confidence gets rewarded

A forecast is a **distribution**, so it must be scored as one. Score only the central estimate
and you create an incentive to lie about uncertainty.

Here is the demonstration. Two forecasters, **identical median of 100**, differing only in
their 95% interval. The interval score is
`(u − l) + (2/α)(l − y)` if the truth falls below, `+ (2/α)(y − u)` if above:

| Truth | Narrow [98, 102] | Wide [60, 140] | **MAE of both** |
|---|---|---|---|
| 100 | **4.0** | 80.0 | **0** |
| 103 | **44.0** | 80.0 | **3** |
| 110 | 324.0 | **80.0** | **10** |
| 140 | 1524.0 | **80.0** | **40** |
| 180 | 3124.0 | **1680.0** | **80** |

Read the last column. **MAE cannot tell these two forecasters apart. Ever.** They have the same
median, so on any point-forecast metric they are identical — while one is claiming to know the
answer to ±2 and the other to ±40.

The interval score does what you want: it rewards the narrow forecaster when they are right
(4.0 versus 80.0) and punishes them severely when they are not. The crossover is at **104** —
just 4 above the median, and only 2 outside the stated interval.

**The vocabulary:**
- **Proper** scoring rules — log score, CRPS, and **WIS** (weighted interval score, the
  quantile version) — cannot be gamed: the best expected score comes from reporting your honest
  belief.
- **Improper** ones — MAE, RMSE on a point forecast — can be, as above.
- **Coverage** — do your 50% and 95% intervals contain the truth 50% and 95% of the time?
  Report it. Under-coverage is the signature of over-confidence.

## Section 6 · The ensemble finding

The single most important empirical result in this shape.

The **CDC FluSight** and **COVID-19 Forecast Hub** efforts (and the European equivalent)
collected forecasts from dozens of independent teams, weekly, prospectively, and scored them
all with the same proper rule. Methods ranged from mechanistic to purely statistical to
machine-learned to human judgement.

The finding, replicated across diseases and continents: **a simple combination — often the
median of all submitted forecasts — outperformed almost every individual model, almost always,
and was far more reliable across time.** Individual models had good months; the ensemble rarely
had bad ones.

Two mechanisms, worth separating:

1. **Error cancellation.** Independent models err in different directions. Averaging shrinks
   variance without needing to know which model is right.
2. **Robustness to regime change.** Every individual model has conditions under which it fails
   badly. The ensemble is never best, and is never catastrophic — and over a long run, avoiding
   catastrophe beats occasional brilliance.

✱ The organisational implication is larger than the statistical one. **The correct response to
forecasting uncertainty is not a better model, it is more models and an honest scoring rule.**
That is a claim about institutions, and it is why hubs exist.

⚠ It is also a claim with limits: an ensemble of models that share an assumption inherits that
assumption. Diversity is what does the work, so a hub of twenty variants of the same SEIR is
not an ensemble in the useful sense.

---

## Key insight

**In this shape, honesty is measurable — and it is the thing being measured.** Every other
shape lets you hide uncertainty; forecasting scores it directly, which is why proper scoring
rules exist and why they matter. The ensemble finding follows: once you are scored on honesty
rather than on confidence, the humble aggregate wins.

And the corollary for reading claims: **a forecast reported without an interval has not been
evaluated, whatever accuracy figure accompanies it.**

---

## Worked example — the over-confident forecaster, scored two ways

Dataset: a simulated weekly count series with trend and seasonality, and three forecasters —
seasonal-naive, a well-calibrated model, and an over-confident model with the *same* median as
the calibrated one.

The point: on MAE the over-confident model and the calibrated model are **indistinguishable**;
on WIS they are not.

### In R

```r
library(tidyverse)

set.seed(11)
n_weeks <- 156                                  # three years of weekly data
week    <- 1:n_weeks

# ---- A realistic-ish surveillance series ------------------------------------
# Trend + annual seasonality + overdispersed counts (never Poisson in practice).
mu     <- exp(2.6 + 0.004 * week + 0.55 * sin(2*pi*week/52) )
series <- tibble(week, cases = rnbinom(n_weeks, mu = mu, size = 8))

# Hold out the last 26 weeks as the forecast target.
train <- series |> filter(week <= n_weeks - 26)
test  <- series |> filter(week >  n_weeks - 26)

# ---- Forecaster 1: seasonal naive — the comparator that must be beaten ------
# Same week last year. One line, no parameters, and hard to beat.
naive_med <- series$cases[test$week - 52]

# ---- Forecaster 2: a calibrated model --------------------------------------
# Negative-binomial GLM with harmonic seasonal terms. Predictive intervals come
# from the fitted NB distribution, so they widen appropriately.
fit <- MASS::glm.nb(
  cases ~ week + sin(2*pi*week/52) + cos(2*pi*week/52), data = train)
mu_hat  <- predict(fit, newdata = test, type = "response")
theta   <- fit$theta
cal_med <- mu_hat
cal_lo  <- qnbinom(0.025, mu = mu_hat, size = theta)
cal_hi  <- qnbinom(0.975, mu = mu_hat, size = theta)

# ---- Forecaster 3: over-confident — SAME median, interval shrunk 5x --------
# This is the forecaster that a point-forecast metric cannot detect.
half    <- (cal_hi - cal_lo) / 2
over_lo <- round(cal_med - half/5)
over_hi <- round(cal_med + half/5)

# ---- Scoring ---------------------------------------------------------------
# Interval score for a central (1-alpha) prediction interval:
#   width  +  (2/alpha) * (distance outside the interval, if any)
# Sharpness is rewarded by the width term; being wrong is punished by the rest.
interval_score <- function(l, u, y, alpha = 0.05) {
  (u - l) + (2/alpha) * pmax(l - y, 0) + (2/alpha) * pmax(y - u, 0)
}

# Coverage: does the interval contain the truth as often as it claims?
coverage <- function(l, u, y) mean(y >= l & y <= u)

tibble(
  forecaster = c("seasonal naive", "calibrated NB", "over-confident"),
  MAE = c(mean(abs(naive_med - test$cases)),
          mean(abs(cal_med   - test$cases)),
          mean(abs(cal_med   - test$cases))),          # <- identical by construction
  interval_score = c(NA,
          mean(interval_score(cal_lo,  cal_hi,  test$cases)),
          mean(interval_score(over_lo, over_hi, test$cases))),
  coverage_95 = c(NA,
          coverage(cal_lo,  cal_hi,  test$cases),
          coverage(over_lo, over_hi, test$cases))
)
# Expect: MAE identical for rows 2 and 3 — the metric is blind to the defect.
# Expect: the over-confident row to have a much worse interval score and
# coverage far below 0.95. That gap is the whole point of a proper scoring rule.

# ---- And the comparison people skip ---------------------------------------
# Does the model beat the naive forecast at all? Report the ratio, not the raw
# number: a MAE of 12 means nothing without knowing that naive scores 15.
c(skill_vs_naive = 1 - mean(abs(cal_med - test$cases)) /
                       mean(abs(naive_med - test$cases)))
# Positive = better than doing nothing clever. Frequently it is not.
```

⚠ Not executed here (no Rscript in WSL); `MASS::glm.nb` may fail to converge on some seeds. The
interval-score table earlier in this lesson **was** computed and is exact. Read the code for the
construction: the two forecasters share a median by design, so their MAE is identical by
arithmetic, not by luck.

---

## Exercises

**Recall.** Distinguish nowcasting, forecasting and early warning in one sentence each, and say
which one Google Flu Trends was evaluated as and which it was sold as.

**Application.** Take any routine surveillance series you work with. Plot the last twelve weeks
as reported. Then ask: how much of the apparent recent decline is reporting delay? If you cannot
answer, that is the finding.

**Application.** Run the worked example and compute the skill score against seasonal naive. If
it is negative, explain what you would report and to whom.

**Conceptual.** The ensemble beats nearly every individual model. Argue that this means
individual modelling effort is wasted. Then rebut your own argument — what does the ensemble
require in order to work?

**Challenge.** A colleague forecasts HAT cases per health zone for next year using gradient
boosting on climate and population covariates, reporting an excellent RMSE. Name three things
you would ask for before believing it, in the order you would ask.

---

## Connection to the course spine

Shape 2's debt, from Lesson 9, is **a proper scoring rule and a naive baseline** — and this
lesson is where both are earned rather than asserted. The interval-score table is the second
half of the spine in miniature: two forecasters, identical on the reported metric, and only the
evaluation distinguishes them.

The first half holds too. Every method here — ARIMA, SEIR, renewal equations, gradient boosting
— is a way of answering *what will this number be*. Recognising that they are the same shape is
what lets you demand the same evidence from all of them, which is exactly what a forecast hub
does, and why it works.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified. Leads, not citations.

**Start here**
- **Gneiting T, Raftery AE.** *Strictly proper scoring rules, prediction, and estimation.*
  **JASA** 2007. The foundation. Dense but decisive.
- **Bracher J, Ray EL, Gneiting T, Reich NG.** *Evaluating epidemic forecasts in an interval
  format.* **PLOS Computational Biology** 2021;17(2):e1008618;
  doi:10.1371/journal.pcbi.1008618. ✓ **Verified 2026-08-21** (note the correction,
  2022;18(10):e1010592). Where WIS is defined for exactly this use.

**The hubs and the ensemble finding**
- **Reich NG, Ray EL, Cramer EY**, and colleagues on the **COVID-19 Forecast Hub** and
  **FluSight** — the ensemble results, prospectively evaluated. ⚠ Several papers; the
  US and European hub evaluations are the ones to read.
- **Sherratt K, Gruson H, Funk S**, and colleagues on the **European COVID-19 Forecast Hub** —
  the replication.

**Nowcasting and reporting delay**
- **Höhle M, an der Heiden M.** On nowcasting outbreaks with reporting delays.
- The `{EpiNow2}` and `{epinowcast}` documentation — the practical implementations, and unusually
  good at explaining the statistics.
- **Abbott S, Hellewell J, Funk S**, and colleagues on real-time *R*ₜ estimation.

**Mechanistic and semi-mechanistic**
- **Cori A, Ferguson NM, Fraser C, Cauchemez S.** *A new framework and software to estimate
  time-varying reproduction numbers.* **AJE** 2013 (`EpiEstim`).
- **Keeling MJ, Rohani P.** *Modeling Infectious Diseases in Humans and Animals* (2008). The
  textbook, if you want compartmental models properly.

**Books**
- **Hyndman RJ, Athanasopoulos G.** *Forecasting: Principles and Practice* (free online). The
  best general forecasting text there is, and strong on baselines and on scoring.
- **Held L, Höhle M, Hofmann M (eds).** *Handbook of Infectious Disease Data Analysis.*

---

## Retain long-term

- Nowcasting, forecasting and early warning are three questions with three evidence requirements.
- You cannot forecast what you cannot nowcast.
- Uncorrected surveillance series always look like they are declining, because recent points are incomplete.
- Seasonal naive is the baseline; report skill relative to it or the number is uninterpretable.
- MAE on a point forecast cannot distinguish a calibrated forecaster from an over-confident one with the same median.
- Proper scoring rules — log score, CRPS, WIS — cannot be gamed. Report coverage too.
- Only a mechanistic model can answer a counterfactual; statistical models answer what will happen, not what would happen if.
- Trees cannot extrapolate beyond the observed range, which is fatal for peak forecasting.
- The ensemble beats almost every individual model, almost always — via error cancellation and robustness to regime change.
- An ensemble of models sharing an assumption inherits it. Diversity does the work.
