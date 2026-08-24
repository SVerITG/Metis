# Lesson 9 — Evaluation: the lesson that decides all the others

> **Concept map**
> **Builds on** — Lesson 1 (the six shapes) for the comparator rule; Lessons 2–8 for the methods being judged.
> **Connects to** — Lesson 10 (deployment and governance), which asks what happens after a model passes this lesson; and every deep-dive page, which ends with these questions.
> **Leads to** — nothing. This is the lesson the others depend on, which is why it is written before most of them.

## Why this matters

Almost every failure in the Atlas is an evaluation failure, not a modelling failure.

That is a strong claim, so test it against the cautionary canon. Google Flu Trends used a
reasonable method on unstable predictors and was never evaluated prospectively against a
drifting search engine. The Epic Sepsis Model was a competent gradient-boosted classifier
that nobody validated outside its development data. Obermeyer's algorithm predicted its
label superbly; the label was wrong. The COVID prognostic literature produced hundreds of
models, almost all at high risk of bias by their own reporting standards. The AI Clinician
was evaluated on data that only ever recorded the actions clinicians already took.

Six famous disasters. **Not one of them is a story about the algorithm.**

So this is the load-bearing lesson. Learn it and you can read any claim in the Atlas —
including claims about methods invented after this course was written.

✱ There is also good news for you specifically: you already know most of this. Sensitivity,
specificity, PPV, confounding, selection bias, external validity — this is diagnostic-test
epidemiology and study design, applied to a model instead of a test. The vocabulary is new;
the reasoning is yours.

## Learning objectives
By the end of this lesson you will be able to:
- **Distinguish** discrimination from calibration, and explain why only the second supports a decision.
- **Compute** PPV and alert burden at a realistic prevalence, and show why AUC conceals both.
- **Identify** leakage, dataset shift and label bias in a described study, before reading its results.
- **Appraise** a prediction-model paper against TRIPOD+AI and PROBAST+AI in about twenty minutes.

## Prerequisites
Lesson 1. Working knowledge of sensitivity, specificity and predictive values — assumed, not taught.

---

## Section 1 · Discrimination is not calibration

Two entirely different questions get collapsed into "is the model good?".

**Discrimination** asks: does the model rank people correctly? Given one person who has
the outcome and one who does not, how often does the model score the first higher? That
number is the **AUC** — and it is exactly the Mann–Whitney U statistic, which is worth
knowing because it tells you what AUC ignores. It depends only on *ordering*. Multiply
every predicted probability by three and the AUC does not move.

**Calibration** asks: when the model says 0.7, does the outcome happen 70% of the time?

Only calibration supports a decision. A perfectly discriminating, badly calibrated model
tells you who is at higher risk but not whether anyone is at *enough* risk to act. Yet the
majority of published models report AUC alone.

The two standard summaries:
- **Calibration slope** — regress the outcome on the model's linear predictor. Slope 1 is
  ideal; below 1 means predictions are too extreme (the usual overfitting signature).
- **Calibration-in-the-large (intercept)** — is the average predicted risk equal to the
  observed rate? Wrong on transfer to a new setting almost by default, because prevalence
  differs.

⚠ A calibration *plot* is not optional decoration. It is the primary result.

## Section 2 · Prevalence eats your model

This is the single most consequential piece of arithmetic in applied health AI, and the
one your background makes trivial.

A model at **80% sensitivity and 90% specificity** — respectable, publishable — behaves
like this:

| True prevalence | PPV | Alert rate | Patients flagged per true case |
|---|---|---|---|
| 10% | **47.1%** | 17.0% | 2.1 |
| 1% | **7.5%** | 10.7% | 13.4 |
| 0.1% | **0.79%** | 10.1% | 125.9 |
| 0.01% | **0.08%** | 10.0% | 1251 |

The sensitivity and specificity never changed. The model never changed. **Only the setting
changed**, and the tool went from useful to actively harmful.

Read the third column too. As prevalence falls, the alert rate barely budges — it converges
on the false-positive rate. The model keeps firing at roughly the same volume while
becoming almost entirely wrong. That is the mechanism behind alert fatigue, and it is why
clinicians learn to ignore sepsis alerts.

**And the specificity required to fix it is brutal.** To reach a merely tolerable PPV of
30% at 0.1% prevalence with 80% sensitivity, you need specificity of **99.81%** — a
false-positive rate of 1 in 535. Almost nothing in medicine achieves that.

✱ This is why WHO's endorsement of chest-X-ray CAD for TB is worded as *screening and
triage with a configurable threshold*, not diagnosis. The threshold is the deployment
decision, and it is set per setting, from the local prevalence. A single "recommended
threshold" is a red flag on any product.

## Section 3 · Internal validation measures the dataset

Cross-validation, bootstrap, a held-out split from the same hospital in the same year —
these estimate how the model performs **on data like the data it was built from**. Nothing
more.

The escalating ladder of evidence:

1. **Apparent performance** — evaluated on training data. Meaningless.
2. **Internal validation** — cross-validation or bootstrap. Corrects optimism, not generalisability.
3. **Temporal validation** — a later time period. Catches drift.
4. **External / geographical validation** — a different site or system. Catches everything about local practice.
5. **Prospective evaluation** — deployed, outcomes measured forward.
6. **Impact evaluation** — a trial. Does using it change patient outcomes?

The Epic Sepsis Model reached step 2 and was sold as though it had reached step 6. When
someone finally did step 4 across a large health system, discrimination came out around
0.63 against vendor claims in the high 0.70s–low 0.80s, with poor calibration, low
sensitivity at the deployed threshold, and alerts on a large share of all admissions.
⚠ Verify those figures before quoting them; the *shape* of the finding is the point.

✱ Steps 5 and 6 are where the **AI chasm** sits. The number of health AI systems with a
published impact evaluation is small enough to list.

## Section 4 · Leakage — the most common cause of fake performance

Leakage is when information about the outcome reaches the model in a way it never could in
deployment. It produces spectacular, entirely fake results, and it is very hard to see from
a methods section.

The recurring forms:
- **Post-outcome predictors.** A "prediction" model for sepsis using antibiotic orders. The
  order happened because someone already suspected sepsis.
- **Patient overlap across folds.** The same patient in train and test — trivial with
  repeat admissions or multiple images per person.
- **Temporal leakage.** Random splits on time-series data let the model see the future.
- **Preprocessing before splitting.** Imputation, scaling or feature selection fitted on
  the whole dataset.
- **Confounded acquisition.** Portable X-rays are taken of sicker patients; the model learns
  the scanner. Surgical rulers appear in melanoma photographs because someone already
  suspected melanoma.

⚠ Heuristic: if performance is much better than a clinician's, suspect leakage before
believing genius. That prior is well earned.

## Section 5 · Dataset shift, and who the model fails

The model has no way of knowing anything changed. The forms that matter:

- **Covariate shift** — the population differs. Age, comorbidity, skin tone, scanner.
- **Label shift** — prevalence differs. See section 2.
- **Concept shift** — the relationship itself changes. New variant, new treatment, new
  coding practice, a new triage protocol.
- **Feedback loops** — the model changes the behaviour that generates its own training
  data. Uniquely nasty, because performance can look stable while meaning drifts.

And always: **aggregate accuracy is a weighted average that hides who the model fails.**
Report performance by subgroup, or you have not reported performance. Dermatology models
trained overwhelmingly on Fitzpatrick I–III skin are the standing example — and the deeper
problem is that performance on darker skin is frequently not measured at all, so the
failure is invisible rather than merely known.

## Section 6 · Forecasts need proper scoring rules

For shape 2 the rules differ. A forecast is a distribution, so it must be scored as one.

- **Proper** scoring rules (log score, CRPS, **WIS** for quantile forecasts) cannot be
  gamed: the best expected score comes from reporting your honest belief.
- **Improper** ones can. Evaluating a point forecast with MAE or RMSE rewards
  over-confidence, because there is no penalty for a too-narrow interval.
- **Coverage** — do the 50% and 95% intervals contain the truth 50% and 95% of the time?
- **Baselines matter more here than anywhere.** A seasonal-naive forecast is startlingly
  hard to beat, and the FluSight/Forecast Hub experience is that a simple *ensemble* beats
  nearly every individual model. Humility is empirically optimal.

## Section 7 · Accuracy is not utility

The last step everyone skips. A model can be well calibrated and still useless.

- **Net benefit / decision curves** put sensitivity and specificity on one axis by asking
  what threshold probability a decision-maker would accept. It answers "would using this
  beat treating everyone, or nobody?" — often the honest answer is no.
- **What action changes?** If the flagged patients would have been managed identically
  anyway, the model's accuracy is irrelevant.
- **Number needed to screen / alert burden** — the deployment currency.
- **Cost-effectiveness** — nearly absent from the health-AI literature, which is itself a
  finding.

## Section 8 · The frameworks, and how to use them

You do not need to memorise these. You need to know they exist and to open the checklist
when reading something important.

| Framework | For | Use it to ask |
|---|---|---|
| **TRIPOD+AI** (2024) | Reporting prediction models | Is enough reported to reproduce or appraise this? |
| **PROBAST+AI** | Risk of bias in prediction models | Where could this be systematically wrong? |
| **STARD-AI** | Diagnostic accuracy studies | Was the reference standard applied blind and to everyone? |
| **CONSORT-AI / SPIRIT-AI** | Randomised trials of AI interventions | Was the comparator the real alternative? |
| **DECIDE-AI** | Early live clinical evaluation | What happened when humans used it? |

✱ Twenty minutes with PROBAST settles most arguments about a paper, and it settles them in
a way you can show someone else. Learn the four domains (participants, predictors, outcome,
analysis) and the rest follows.

---

## Key insight

**Discrimination is a property of the model. Everything that matters is a property of the
model *in a setting*.** PPV, alert burden, calibration, net benefit, subgroup performance —
all of them move when you move the model, and none of them appear in an AUC.

Which is why "AUC 0.92" is not a result. It is the beginning of a question: *at what
prevalence, with what threshold, in whose population, costing what?*

---

## Worked example — one model, two verdicts

Dataset: a simulated cohort of 100,000 patients, 1% outcome prevalence, with a model that
discriminates respectably but whose predicted probabilities are inflated threefold — the
single most common real-world defect, produced by developing at high prevalence and
deploying at low.

The point of the example: **the AUC is unaffected by the defect, and every quantity that
matters is destroyed by it.**

### In R

```r
library(tidyverse)

set.seed(42)
n    <- 100000          # cohort size
prev <- 0.01            # 1% outcome prevalence — a realistic screening setting

# ---- Simulate a cohort with a genuinely informative marker -----------------
# The marker is shifted upward in cases, so it carries real signal.
dat <- tibble(
  y      = rbinom(n, 1, prev),                 # true outcome
  marker = rnorm(n, mean = 1.2 * y, sd = 1)    # informative but overlapping
)

# A well-specified model: logistic regression on the marker.
fit <- glm(y ~ marker, family = binomial, data = dat)
dat$p_good <- predict(fit, type = "response")   # calibrated predictions

# ---- The defect: the same model, probabilities inflated 3x ------------------
# Ordering is untouched, so discrimination is untouched. Only the numbers lie.
dat$p_bad <- pmin(dat$p_good * 3, 0.999)

# ---- AUC, computed from first principles -----------------------------------
# AUC IS the Mann-Whitney U statistic: the rank-sum of cases, normalised.
# No package needed, and writing it this way makes clear that AUC sees
# only the ORDER of predictions — never their values.
auc <- function(p, y) {
  n1 <- sum(y == 1); n0 <- sum(y == 0)
  (sum(rank(p)[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

auc(dat$p_good, dat$y)   # calibrated model
auc(dat$p_bad,  dat$y)   # inflated model — IDENTICAL, because ranks are identical

# ---- Calibration: where the two models separate ----------------------------
# Calibration slope: regress the outcome on the model's linear predictor.
# Slope 1 = ideal. Well below 1 = predictions too extreme.
cal_slope <- function(p, y) {
  lp <- log(p / (1 - p))                        # back to the logit scale
  unname(coef(glm(y ~ lp, family = binomial))[2])
}

cal_slope(dat$p_good, dat$y)   # near 1
cal_slope(dat$p_bad,  dat$y)   # pulled away from 1

# Calibration-in-the-large: does mean predicted risk match observed risk?
c(observed      = mean(dat$y),
  predicted_good = mean(dat$p_good),
  predicted_bad  = mean(dat$p_bad))   # the inflated model triples its own risk estimate

# ---- What a decision-maker actually feels ----------------------------------
# Pick the threshold each model's own scale suggests, then ask the only
# questions that matter operationally: who gets flagged, and is it worth it.
operating <- function(p, y, threshold) {
  flag <- p >= threshold
  tibble(
    threshold   = threshold,
    alert_rate  = mean(flag),                        # share of ALL patients flagged
    sensitivity = sum(flag & y == 1) / sum(y == 1),
    specificity = sum(!flag & y == 0) / sum(y == 0),
    ppv         = sum(flag & y == 1) / max(sum(flag), 1),
    flagged_per_case = max(sum(flag), 1) / max(sum(flag & y == 1), 1)
  )
}

bind_rows(
  operating(dat$p_good, dat$y, 0.10) |> mutate(model = "calibrated"),
  operating(dat$p_bad,  dat$y, 0.10) |> mutate(model = "inflated 3x")
)
# Same AUC. Same ranking. Wildly different alert burden at the same nominal
# threshold — because the threshold means something different on each scale.

# ---- The prevalence table from Section 2, derived rather than quoted -------
ppv_at <- function(prevalence, sens = 0.80, spec = 0.90) {
  tp <- prevalence * sens
  fp <- (1 - prevalence) * (1 - spec)
  tibble(prevalence, ppv = tp / (tp + fp), alert_rate = tp + fp,
         flagged_per_case = (tp + fp) / tp)
}
map_dfr(c(0.10, 0.01, 0.001, 0.0001), ppv_at)
#> # A tibble: 4 x 4
#>   prevalence      ppv alert_rate flagged_per_case
#>        <dbl>    <dbl>      <dbl>            <dbl>
#> 1     0.1    0.471         0.17              2.12
#> 2     0.01   0.0748        0.107            13.4
#> 3     0.001  0.00794       0.101           126.
#> 4     0.0001 0.000799      0.100          1251.
```

⚠ The `ppv_at` table is exact arithmetic and has been checked. The simulation results above
it depend on `set.seed(42)` and your R version, so read them for the *pattern* — identical
AUC, divergent calibration and alert burden — not for specific digits. The code has not
been executed in this environment.

---

## Exercises

**Recall.** State, in one sentence each, what discrimination and calibration measure, and
which one a threshold decision requires.

**Application.** Take the most recent AI-in-health paper you read. Find its reported AUC.
Then find (a) the prevalence in the validation set, (b) whether calibration is reported at
all, (c) whether validation was external. Note how long each took to find — the ones that
take longest are usually the ones being downplayed.

**Application.** Your HAT screening work sits at roughly 1 per 10,000. Using the `ppv_at`
function, work out what specificity a screening model would need for a PPV of 20% at 80%
sensitivity. Then decide whether you believe any imaging or tabular model achieves it.

**Conceptual.** A vendor reports that their model, deployed live, has 92% accuracy. The
outcome occurs in 3% of patients. What is the highest-accuracy model you can build in one
line of code, and what does that tell you about the claim?

**Challenge.** Pick any entry in the Atlas marked ⚰️ and write two paragraphs identifying
which section of this lesson it violated. Then find an entry marked 🚀 and check whether it
avoided the same trap or merely has not been caught yet.

---

## Connection to the course spine

The spine has two halves, and this lesson is the second: *what decides whether it works is
never the model, it is the evaluation.*

Lesson 1 made the field finite by sorting it into six shapes. This lesson is what makes the
sorting useful — because once you know which shape a claim is, you know which evaluation it
owes you. Shape 1 owes you a false-alarm rate and a timeliness measure. Shape 2 owes you a
proper scoring rule and a naive baseline. Shape 3 owes you calibration and PPV at the
deployment prevalence. Shape 4 owes you replication in a second dataset. Shape 5 owes you a
definition of correct. Shape 6 owes you an account of how it was evaluated without being
deployed.

Six shapes, six debts. That is the whole course in two sentences.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified against the literature. Leads to
confirm, not citations to reuse.

**Books**
- Steyerberg, *Clinical Prediction Models* (2nd ed.) — the standard reference; chapters on
  validation and on calibration are the two to read.
- Riley et al., *Prognosis Research in Health Care* — open access, and strong on external
  validation.

**Online**
- The TRIPOD+AI and PROBAST+AI checklists themselves — short, and designed to be used
  rather than read.
- `{rms}`, `{dcurves}` and `{scoringutils}` in R — validation, decision curves, and forecast
  scoring respectively.

**Key papers**
- Collins et al., *TRIPOD+AI statement* — BMJ, 2024.
- Wong et al., *External validation of a widely implemented proprietary sepsis prediction
  model in hospitalized patients* — JAMA Internal Medicine, 2021.
- Obermeyer et al., *Dissecting racial bias in an algorithm used to manage the health of
  populations* — Science, 2019.
- Wynants et al., *Prediction models for diagnosis and prognosis of covid-19* — BMJ, 2020.
- Vickers & Elkin, *Decision curve analysis* — Medical Decision Making, 2006.
- Gneiting & Raftery, *Strictly proper scoring rules, prediction, and estimation* — JASA, 2007.

---

## Retain long-term

- Discrimination is ordering; calibration is meaning. Only calibration supports a decision.
- AUC is the Mann–Whitney statistic — it sees only ranks, so it is blind to inflated probabilities.
- At 80% sensitivity and 90% specificity, PPV is 47% at 10% prevalence and 0.8% at 0.1%.
- As prevalence falls, the alert rate converges on the false-positive rate: the model keeps firing and stops being right.
- Internal validation measures the dataset. External validation measures the model.
- If performance beats a clinician's, suspect leakage before genius.
- Aggregate accuracy is a weighted average that hides who the model fails.
- Point forecasts scored by MAE reward over-confidence; use WIS, CRPS or the log score.
- Six shapes, six evaluation debts.
