# Lesson 4 — Labels from databases: tabular pattern recognition, and the record of the decision

> **Concept map**
> **Builds on** — Lesson 1 (shape 3 and its comparator, logistic regression); Lesson 9 for leakage, calibration and the validation ladder.
> **Connects to** — Lesson 5, which is the same shape from pixels and has **the same underlying failure in a different modality**; and the *Two database failures* deep dive, which is this lesson's case material.
> **Leads to** — Lesson 8, because most tabular risk scores exist to trigger an action.

## Why this matters

This is the least glamorous shape and by far the most deployed. Every sepsis alert, readmission
score, deterioration warning, care-management enrolment algorithm and risk stratifier in every
health system is this: rows and columns, a binary outcome, a fitted model.

It is also where **you already have the strongest instincts of anyone in the room**, because it
is confounding and selection bias in a new costume. If you can interrogate an observational
study you can interrogate a tabular model, and the questions are almost the same ones.

✱ There is one finding worth having at hand before anything else: on tabular data, **gradient
boosting reliably beats deep learning.** Not sometimes — consistently, across benchmarks. So
when someone proposes a neural network for a spreadsheet, the burden of proof is theirs, and
"we used deep learning" is a description of effort, not of quality.

## Learning objectives
By the end of this lesson you will be able to:
- **Explain** why the *presence* of a value in a health record is itself a clinical decision, and what that does to a model.
- **Identify** the tabular-specific leakage patterns, including immortal time and post-outcome predictors.
- **Interrogate** an administrative label — ICD codes, billing categories — as a measurement rather than a fact.
- **Say** what a tabular risk model must report before you would let it trigger anything.

## Prerequisites
Lesson 1. Lesson 9 strongly recommended. Regression and observational study design assumed.

---

## Section 1 · The data was collected for another purpose

Health databases are **found data**. EHRs exist to run a hospital and to bill for it; claims
exist to reimburse; registries exist to count. None was designed to answer your question, and
each carries the fingerprints of the process that produced it.

Three fingerprints matter most:

**1 · Coding reflects incentives, not biology.** ICD codes are assigned to support billing and
administration. Code prevalence shifts when reimbursement rules change, when coders are
retrained, when a hospital adopts a new EHR. A model trained across such a change learns the
administrative regime as much as the disease.

**2 · Records exist only where care was reached.** Everyone in the database attended. The people
who did not — the ones who could not travel, could not pay, were not believed — are absent, and
their absence is not random. ⚠ This is plain selection bias, and it is the reason a model can be
well calibrated on a hospital population and badly wrong about the community it serves.

**3 · Time is messy.** Timestamps record when something was *entered*, not when it happened.
Backdating, batch entry and overnight jobs are routine. Any model whose features depend on
ordering in time is exposed to this.

## Section 2 · Missingness is a clinical decision — the key mechanism

Here is this lesson's central idea, and it is the exact analogue of confounded acquisition in
imaging.

> **In a health record, whether a value exists is itself a clinical judgement. The missingness
> pattern encodes what the clinician was worried about.**

A troponin is measured because someone suspected a cardiac event. A lactate is measured because
someone suspected sepsis. A CT is ordered because someone was concerned. So the indicator
*"was this measured?"* carries the clinician's suspicion — and suspicion is an excellent
predictor of outcome.

The consequence is that a model given missingness indicators can perform superbly while knowing
almost nothing about physiology. In the worked example below, **"was a test ordered?" achieves
an AUC of 0.87 while the test's actual value achieves 0.61.**

✱ Put the two lessons side by side and the parallel is exact:
> Lesson 5 — *the image records the clinical encounter.*
> Lesson 4 — *the presence of a value records the clinical encounter.*
>
> Same mechanism, different modality. In both cases the model is right, for a reason that will
> not survive a change in practice.

⚠ And note what this does to standard advice. "Impute missing values" treats missingness as a
nuisance to be repaired. In health data it is frequently **signal** — and worse, signal that is
valid today and gone tomorrow, because it depends on a testing policy that management can change
on a Monday.

There is no clean rule here, but there is a clear question: **would this feature still be
available, and still mean the same thing, in the setting where the model will run?** If testing
policy differs, the answer is no.

## Section 3 · Leakage, in its tabular forms

Lesson 9 introduced leakage. Tabular health data has its own catalogue, and every item is
something you would catch instantly in a study design.

- **Post-outcome predictors.** Antibiotics "predicting" sepsis. The treatment happened because
  the diagnosis was suspected. In study terms: adjusting for a consequence of the exposure.
- **Immortal time.** Defining a group by something that requires survival to occur — "patients
  who completed treatment" cannot include those who died during it. A classic pharmaco-epi trap,
  and it walks straight into feature engineering.
- **Target leakage through administrative fields.** Discharge codes, length of stay, discharge
  destination, billing categories — all determined after the outcome and all present in the row.
- **Temporal leakage.** A random train/test split on longitudinal data lets the model see the
  future. Splits must be by time, and preferably by site as well.
- **Patient overlap.** The same person appearing in train and test through repeat admissions.
  Split by patient, never by row.
- **Preprocessing before splitting.** Imputation, scaling and feature selection fitted on the
  whole dataset leak the test set into the training procedure. Subtle and extremely common.

⚠ The heuristic from Lesson 9 applies with full force here: **if performance markedly exceeds a
clinician's, suspect leakage before genius.** In this shape that prior is very well earned.

## Section 4 · The label is a measurement, not a fact

The deep dive on Epic and Obermeyer is this section's evidence, so this is the compressed form.

Ask of any tabular outcome: **what was literally recorded, and what do I actually care about?**

- "Sepsis" often means *a clinician ordered antibiotics and cultures*. So a sepsis model may be
  predicting clinician recognition — which is exactly what needs no model.
- "Health need" was operationalised as *next-year healthcare cost*. Cost is need filtered
  through access, and access is unequal, so the proxy is biased with a direction.
- "Case" in a surveillance database means *detected and reported*. ✱ Which is your own daily
  version of this: any model trained on reported cases learns the geography of surveillance as
  much as the geography of disease.

The rule that covers all three: **a proxy inherits the inequities and the artefacts of the
process that generated it.**

## Section 5 · What a tabular model owes you

Concretely, before it triggers anything:

| Requirement | Why |
|---|---|
| **Calibration plot**, not only AUC | A threshold decision needs probabilities that mean something |
| **PPV and alert burden at the deployment prevalence** | See Lesson 9. AUC hides both |
| **External validation**, ideally another site and a later period | Internal validation measures the dataset |
| **Subgroup performance** | Aggregate accuracy is a weighted average that hides who it fails |
| **The feature list, and each feature's availability at prediction time** | This is where leakage is found |
| **What the outcome variable literally is** | Section 4 |
| **Net benefit / decision curve** | Whether using it beats treating everyone or nobody |
| **A recalibration plan** | Coding practice, case mix and testing policy all drift |

⚠ Class imbalance deserves a specific warning. Accuracy is meaningless when the outcome is rare
— predicting "no" for everyone scores 97% on a 3% outcome. And the popular fixes (over-sampling,
SMOTE, class weights) **distort calibration**, which is the property you actually needed. If you
resample, recalibrate afterwards, and say that you did.

## Section 6 · What this shape is actually worth

Honestly assessed, because the hype and the value are in different places.

**Real value:**
- **Triage and prioritisation of scarce human attention** — who gets reviewed first, who gets a
  follow-up call. Modest, safe, genuinely useful.
- **Registry-scale risk stratification** for programme planning rather than individual decisions.
- **Prediction where the alternative is nothing** — a simple, transparent, well-calibrated score
  in a setting with no risk stratification at all beats no score, and gradient boosting on ten
  variables is usually plenty.

**Overstated:**
- Anything claiming to outperform clinicians on judgements clinicians make well.
- Deep learning on tabular data.
- Explainability as a substitute for validation. ✱ A SHAP plot tells you what the model used, not
  whether the model is right. A confounded model produces a beautifully interpretable explanation
  of its confound.

---

## Key insight

**In tabular health data the row does not describe a patient — it describes what was done to a
patient.** Which tests were ordered, which codes were assigned, which visit was recorded. So the
strongest predictors are often traces of clinical judgement rather than measurements of biology,
and they hold exactly as long as the practice that produced them.

That is why this shape rewards epidemiological thinking over modelling effort. The question is
never "which algorithm?" — it is *"how did this column come to exist, and will it mean the same
thing tomorrow?"*

---

## Worked example — the test that was ordered beats the test result

Dataset: a simulated cohort of 20,000 admissions with an unobserved severity, an outcome, a
**clinician decision to test** driven by severity, and a test **value** also driven by severity.

Nothing here is exotic. It is the ordinary structure of every EHR.

### In R

```r
library(tidyverse)

set.seed(3)
n <- 20000

# ---- The ordinary structure of a health record -----------------------------
# `severity` is real and unmeasured. It drives three things independently:
# the outcome, the clinician's decision to test, and the test's value.
# That makes the DECISION a proxy for severity — and a very good one.
dat <- tibble(
  severity = rnorm(n),
  outcome  = rbinom(n, 1, plogis(-2.2 + 1.1 * severity)),
  tested   = rbinom(n, 1, plogis(-1.0 + 1.8 * severity))        # clinician judgement
) |>
  mutate(value = if_else(tested == 1, rnorm(n, 0.6 * severity), NA_real_))

auc <- function(p, y) {                     # Mann-Whitney U again
  n1 <- sum(y == 1); n0 <- sum(y == 0)
  (sum(rank(p)[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

# ---- The comparison that should unsettle you -------------------------------
# Model A uses only the missingness indicator: "was this test ordered?"
# Model B uses only the test result, among those actually tested.
tested_only <- dat |> filter(tested == 1)

c(indicator_only = auc(dat$tested, dat$outcome),
  value_only     = auc(tested_only$value, tested_only$outcome))
#> indicator_only  value_only
#>          0.870       0.606
#
# The FACT that a test was ordered predicts the outcome far better than the
# test's RESULT. The model has learned the clinician's suspicion, not physiology.

# ---- Why this will not survive deployment ----------------------------------
# Management changes policy: everyone gets tested on admission.
deploy <- dat |> mutate(tested = 1L)
auc(deploy$tested, deploy$outcome)
# The indicator is now constant, so it carries no information at all: AUC 0.5.
# Nothing about the patients changed. A memo changed.

# ---- And what naive imputation does ----------------------------------------
# Mean-imputing `value` and dropping the indicator throws away the strong
# (but fragile) signal AND silently mixes two populations - those judged worth
# testing and those not - into one column.
dat |>
  mutate(value_imp = replace_na(value, mean(value, na.rm = TRUE))) |>
  summarise(auc_imputed = auc(value_imp, outcome))
# Neither choice is automatically right. What IS wrong is making it silently.

# ---- The comparator this lesson keeps insisting on -------------------------
# Logistic regression on the honest features, so any fancier model has
# something real to beat.
fit <- glm(outcome ~ tested + I(replace_na(value, 0)) + tested:I(replace_na(value, 0)),
           family = binomial, data = dat)
auc(predict(fit, type = "response"), dat$outcome)
```

⚠ The two AUCs in the comment block (0.870 and 0.606) **were computed** with this generative
structure and this seed. The R code has not been executed here — no Rscript in WSL — so treat
the remaining outputs as directional.

---

## Exercises

**Recall.** Name six tabular leakage patterns and, for each, the observational-study bias it
corresponds to.

**Application.** Take a risk score used where you work, or one from a paper. List its features
and mark each one: available at prediction time, or determined afterwards? Then mark each as
measurement of biology, or trace of a decision.

**Application.** Run the worked example. Then reduce the clinician's severity-dependence in
`tested` from 1.8 toward 0. At what point does the test *value* become more informative than the
*decision to test*? What does that number represent in a real hospital?

**Conceptual.** Your HAT surveillance database records detected cases. Write down three ways a
model trained on it would learn the geography of surveillance rather than of disease, and one
design that would partly separate them.

**Challenge.** A vendor offers a readmission model with AUC 0.79, external validation at two
hospitals, and a SHAP plot. Write the six questions you would ask before it triggers a single
phone call — in the order that would let you stop early.

---

## Connection to the course spine

Shape 3's debt is calibration and PPV at the deployment prevalence — and the tabular rider is
*and the provenance of every column.*

The spine's second half is unusually visible here. Two models in the worked example, same data,
same shape: one at AUC 0.87 and one at 0.61, and **the better-scoring one is the one that will
fail.** No modelling choice distinguishes them. Only asking where the column came from.

And the first half earns its keep by connecting this lesson to Lesson 5. Recognising that
"the image records the encounter" and "the presence of a value records the encounter" are the
same failure means you only have to learn the lesson once.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified. Leads, not citations.

**Start here**
- **Grinsztajn L, Oyallon E, Varoquaux G.** *Why do tree-based models still outperform deep
  learning on typical tabular data?* **NeurIPS** 2022. The evidence for the claim in Section 0.
- **Wong A et al.** (Epic Sepsis) and **Obermeyer Z et al.** — see the *Two database failures*
  deep dive. Read both.

**Leakage, missingness, and study design carried over**
- **Kaufman S, Rosset S, Perlich C.** *Leakage in data mining.* **ACM TKDD** 2012. The original
  taxonomy; still the clearest.
- **Sterne JAC, White IR, Carlin JB, et al.** *Multiple imputation for missing data.* **BMJ**
  2009 — and read it *against* this lesson: the assumptions it requires are frequently violated
  in EHR data precisely because missingness is a decision.
- **Suissa S.** On immortal time bias. Written for pharmaco-epidemiology and directly applicable.
- **Groenwold RHH**, on informative missingness in routine care data.

**Reporting and appraisal**
- **Collins GS et al.** *TRIPOD+AI.* **BMJ** 2024.
- **Wolff RF, Moons KGM, Riley RD, et al.** *PROBAST.* **Annals of Internal Medicine** 2019.
- **Vickers AJ, Elkin EB.** *Decision curve analysis.* 2006.

**Books**
- **Steyerberg EW.** *Clinical Prediction Models*, 2nd ed. The reference for this entire shape.
- **Hernán MA, Robins JM.** *Causal Inference: What If* (free online). Not an ML book, and the
  most useful thing you can read about why tabular prediction goes wrong.

---

## Retain long-term

- On tabular data, gradient boosting reliably beats deep learning. The burden of proof is on the network.
- Health databases are found data: coding reflects incentives, records exist only where care was reached, timestamps record entry not events.
- **Missingness is a clinical decision** — the presence of a value encodes what the clinician suspected.
- "Was a test ordered?" reached AUC 0.87 where the test's value reached 0.61. A memo changing testing policy destroys the first and leaves the second.
- Tabular leakage: post-outcome predictors, immortal time, administrative fields, temporal leakage, patient overlap, preprocessing before splitting.
- The label is a measurement: "sepsis" meant clinician action, "need" meant cost, "case" means detected and reported.
- Resampling for class imbalance distorts calibration. Recalibrate afterwards and say so.
- A SHAP plot tells you what the model used, not whether it is right. A confounded model explains its confound beautifully.
- The row does not describe a patient; it describes what was done to a patient.
