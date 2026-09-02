# Lesson 1 — The six shapes

> **Concept map**
> **Builds on** — Lesson 0, the Atlas: the ~95 applications you are about to learn to sort.
> **Connects to** — Lesson 9 (Evaluation), which supplies the second half of the spine; the four-question routine here is the same one every deep-dive page uses.
> **Leads to** — Lessons 2–8, one per shape. Each assumes you can already name the shape and its classical comparator.

## Why this matters

You are going to read about AI in public health for the rest of your career, at a rate of several claims a week, most of them written by people with something to sell. You cannot evaluate each one from first principles. You need a **sorting reflex**.

The claim of this course is that the reflex is small enough to memorise:

> **Every AI application in public health is one of six pattern-recognition problems wearing different clothes — and what decides whether it works is never the model, it is the evaluation.**

Two halves. This lesson installs the first half. Lesson 9 installs the second, and the rest of the course keeps proving both.

## Learning objectives
By the end of this lesson you will be able to:

- **Classify** any AI-in-health claim into one of six problem shapes, in under a minute.
- **Name** the classical method each shape must beat, and why that comparator matters more than the algorithm.
- **Predict** the characteristic failure mode of each shape before reading the methods section.

## Prerequisites
The Atlas (lesson 0).

---

## The six shapes, and what each one is really doing

### 1 · Detect the unusual
**Question:** is this different from what I expected? **You must supply:** a model of "expected". That is the whole difficulty — the algorithm is downstream of your baseline. **Classical ancestor:** control charts, CUSUM, Farrington. **Characteristic failure:** the expected value was wrong (reporting changed, a holiday, a new clinic opened), so the anomaly is administrative, not epidemiological.

### 2 · Predict what happens next
**Question:** what will this number be in three weeks? **You must supply:** an honest statement of uncertainty. A forecast without an interval is not a forecast. **Classical ancestor:** ARIMA, compartmental models. **Characteristic failure:** evaluated on point accuracy, so over-confident models win.

### 3 · Assign a label
**Question:** what is this thing? **You must supply:** labels — and labels come from somewhere, usually a human, usually imperfectly. **Classical ancestor:** logistic regression; diagnostic test evaluation. **Characteristic failure:** the label was a proxy for what you actually cared about (Obermeyer), or the model found a shortcut correlated with the label (the ruler in the melanoma photograph).

### 4 · Find structure without labels
**Question:** what groups are in here? **You must supply:** a reason to believe the groups are real, because the algorithm will return groups from pure noise every single time. **Classical ancestor:** cluster analysis, latent class analysis, scan statistics. **Characteristic failure:** clusters that do not replicate in a second dataset.

### 5 · Turn language into data
**Question:** what does this text say, as fields? **You must supply:** a definition of correct — which for free text is genuinely contested, and negation and hedging are where it breaks. **Classical ancestor:** manual chart abstraction; ICD coding. **Characteristic failure:** fluent, well-formatted, confidently wrong output, which is much harder to notice than a wrong number.

### 6 · Choose an action
**Question:** given all this, what should we do? **You must supply:** the objective function — and it encodes your values whether you write it down or not. **Classical ancestor:** operations research, decision analysis. **Characteristic failure:** evaluated against observational data that only ever recorded the actions people already took.

---

## Proving the spine: classify these

Here are eight real claims, stripped of their branding. Assign each a shape before reading the answers. Aim for under ten seconds each.

1. A system reads chest X-rays at TB screening sites and flags films needing molecular testing.
2. A model estimates influenza-like illness from search-engine query volume.
3. A tool listens to a consultation and drafts the clinical note.
4. Viral load in city wastewater rises three weeks before hospital admissions do.
5. Latent-class analysis of sepsis patients finds four subtypes with different steroid responses.
6. An algorithm identifies which patients should be enrolled in a care-management programme.
7. Reinforcement learning recommends vasopressor doses in intensive care.
8. A multi-team ensemble publishes weekly probabilistic case forecasts.

<details> <summary>Answers</summary>

1 → **3** (label from pixels) · 2 → **2**, and arguably **1** — nowcasting ILI is prediction, and Google Flu Trends was sold as early warning; that ambiguity is itself the lesson · 3 → **5** · 4 → **1** · 5 → **4** · 6 → **3** (tabular label — and the Obermeyer case, so also a label-bias failure) · 7 → **6** · 8 → **2**

</details>

✱ Notice what happened with number 2. When a claim straddles two shapes, that is almost always where the trouble is: it was *evaluated* as shape 2 (does it track ILI?) and *sold* as shape 1 (does it warn you early?). Those need different evidence. Watching for this mismatch will catch more bad claims than any statistical test.

---

## The comparator rule

For each shape there is a boring method that already exists, and the honest question is never "does the AI work?" but **"does it beat that?"**

| Shape | The thing to beat |
|---|---|
| 1 Detect the unusual | Farrington / CUSUM on the same series |
| 2 Predict what happens next | A seasonal naive forecast, or last week's value |
| 3 Assign a label | Logistic regression on the same predictors |
| 4 Find structure | A scan statistic, or a pre-specified stratification |
| 5 Language into data | A rule-based extractor, or a human coder |
| 6 Choose an action | Current practice |

⚠ Roughly speaking: **if a paper does not report the boring comparator, it is because the boring comparator won.** This is not cynicism, it is a base rate. Tabular deep learning versus gradient boosting is the clearest documented example.

---

## Reading a claim in four questions

The routine from the Atlas, which every deep-dive page in this course follows:

1. **Which shape?** If it does not fit, say so — that is a genuine finding.
2. **What is the comparator?** No comparator, no claim.
3. **How was it evaluated?** Internal only, or external? Calibration, or only discrimination? Subgroups reported?
4. **Maturity, honestly?** Research, piloted, at scale, or withdrawn.

---

## Key insight

The shape is not a property of the method — it is a property of **the question**. The same gradient-boosted tree is shape 1 when it scores how surprising today's count is, shape 2 when it predicts next month's, and shape 3 when it labels an X-ray. People argue about algorithms because algorithms have names. The question is what determines what evidence you need.

---

## Worked example — building a claims register

The four-question routine only compounds if you write the answers down. So the artefact this lesson produces is a **claims register**: one row per claim you have read, which becomes the raw material for new Atlas rows later.

Dataset: the eight claims from the classification exercise above.

### In R

```r
library(tidyverse)

# One row per claim you have read. `shape` is 1-6 from this lesson;
# `comparator` is the boring method it must beat; `evaluated` records how it
# was actually assessed — deliberately allowed to be NA, because "the article
# does not say" is the single most informative value this column takes.
claims <- tribble(
  ~claim,                          ~shape, ~comparator,            ~evaluated,        ~maturity,
  "CXR reading for TB screening",       3L, "radiologist + Xpert",  "external, multi-site", "at scale",
  "ILI from search queries",            2L, "sentinel ILI surveillance", "internal only",   "withdrawn",
  "Ambient note drafting",              5L, "clinician typing",     "burnout endpoints",    "at scale",
  "Wastewater viral load rise",         1L, "clinical admissions",  "lead-time vs cases",   "at scale",
  "Sepsis subtypes by latent class",    4L, "pre-specified strata", "internal only",        "research",
  "Care-management enrolment score",    3L, "logistic on need",     "cost as label",        "withdrawn",
  "RL vasopressor policy",              6L, "current practice",     "off-policy only",      "research",
  "Multi-team case forecast ensemble",  2L, "seasonal naive",       "WIS, prospective",     "at scale"
)

# The shape distribution tells you where your own reading is skewed.
claims |> count(shape, sort = TRUE)

# The diagnostic question: which claims never name a comparator, or were only
# ever evaluated internally? Those are the ones to distrust first.
claims |>
  filter(str_detect(evaluated, "internal|off-policy") | is.na(comparator)) |>
  select(claim, shape, evaluated, maturity)
#> # A tibble: 3 x 4
#>   claim                            shape evaluated      maturity
#>   <chr>                            <int> <chr>          <chr>
#> 1 ILI from search queries              2 internal only  withdrawn
#> 2 Sepsis subtypes by latent class      4 internal only  research
#> 3 RL vasopressor policy                6 off-policy only research

# Note what that filter just did: with no knowledge of any algorithm, it
# recovered two of the six cases in the cautionary canon.
```

✱ That last comment is the lesson. Three columns of bookkeeping, no modelling, and the register flags the failures. Keep adding rows as you read.

---

## Exercises

**Application.** Take the three most recent AI-in-health items from your news feed. For each, answer the four questions in two sentences apiece. Note which question you could not answer from the article itself — that absence is usually the most informative thing about it.

**Conceptual.** Number 4 above (wastewater) is shape 1. Argue the case that it is really shape 2. Which framing should determine how it is evaluated, and why?

**Challenge.** Find a claim that genuinely does not fit any of the six shapes. If you find one, it belongs in the Atlas' "still missing" list and the taxonomy needs amending.

---

## Connection to the course spine

The spine says the field is six problems, not hundreds. This lesson is the only place that claim is made testable: if you can sort eight branding-stripped claims correctly, the taxonomy holds, and every later lesson is one shape studied properly. If you find a claim that fits none of the six, the taxonomy is wrong and the Atlas needs amending — which is a result worth having, not a failure.

The second half of the spine — *evaluation decides everything* — is already visible here in the comparator rule and in the register's `evaluated` column. Lesson 9 makes it the subject.

---

## Sources

⚠ Written from model knowledge to mid-2026 and not verified against the literature. Treat each as a lead to confirm before citing.

**Books**

- Topol, *Deep Medicine* (2019) — the clinical framing; read critically, it is optimistic.
- Hastie, Tibshirani & Friedman, *Elements of Statistical Learning* — ch. 2 for the supervised/unsupervised split underlying shapes 3 and 4.

**Online**

- The `surveillance` R package vignettes — shape 1's classical ancestors, in code.
- Epiverse-TRACE and Applied Epi tutorials — outbreak analytics in R.

**Key papers** (the canon this lesson gestures at, each a deep dive later)

- Lazer et al., *The Parable of Google Flu* — Science, 2014.
- Obermeyer et al., *Dissecting racial bias in an algorithm…* — Science, 2019.
- Wong et al., *External validation of a widely implemented proprietary sepsis prediction model* — JAMA Internal Medicine, 2021.
- Wynants et al., *Prediction models for COVID-19: systematic review and critical appraisal* — BMJ, 2020 (living review).
- Beede et al., *A human-centered evaluation of a deep learning system deployed in clinics* — CHI, 2020.

---

## Retain long-term

- The six shapes, and the question each one answers.
- Every shape has a boring classical comparator; absence of the comparator is evidence.
- A claim evaluated as one shape and sold as another is the most common failure mode.
- What decides whether an AI application works is the evaluation, not the model.
- The shape is a property of the question, not of the method.
