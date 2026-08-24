# Lesson 5 — Labels from pixels: images, video, and what the model is really looking at

> **Concept map**
> **Builds on** — Lesson 1 (shape 3 and its comparator); Lesson 4 (labels from tables — same shape, different failure modes); Lesson 9 for the evaluation vocabulary used throughout.
> **Connects to** — the *Two imaging stories* deep dive, which is this lesson applied to TB chest X-ray and dermatology; and Lesson 10, because imaging AI is where regulation bites hardest.
> **Leads to** — nothing depends on this lesson, so it can be read on its own.

## Why this matters

Imaging is where health AI has done the most good and made the most noise, and the two are
not the same applications. It is also the shape where **you cannot audit the model by reading
its inputs**. A tabular model's predictors have names; you can look at a column called
`antibiotic_ordered` and know you have a problem. A convolutional network's inputs are
pixels, and the thing it has latched onto has no name at all.

That single asymmetry generates most of this lesson.

✱ And imaging is the shape where the classical comparator is not a statistical model but **a
person** — a radiologist, a dermatologist, a microscopist. Which changes the question from
"is it accurate?" to "accurate compared with whom, available where, at what cost?" Often the
honest comparator is *nobody*, and that is when imaging AI is at its most valuable.

## Learning objectives
By the end of this lesson you will be able to:
- **Explain** what a convolutional network is actually computing, without hand-waving.
- **Identify** confounded acquisition — the mechanism behind the ruler, the skin marking and the portable X-ray.
- **Predict** which imaging applications will generalise across sites and which will not, from the data description alone.
- **Judge** what a subgroup performance table must contain before you believe an accuracy figure.

## Prerequisites
Lesson 1. Lesson 9 recommended. No computer-vision background assumed.

---

## Section 1 · What the model is computing

Strip away the vocabulary and a convolutional network does one thing repeatedly: it slides a
small filter across the image, multiplies and sums, and keeps the result. A filter is just a
little grid of weights, and what it computes is a measure of *how much this patch resembles
this pattern*.

Stack those operations and something useful emerges from nothing clever:

- **First layers** learn edges and gradients — light-to-dark transitions at various angles.
- **Middle layers** combine edges into textures and motifs — a speckle, a ring, a striation.
- **Late layers** combine motifs into configurations — something with the shape of a nodule,
  something with the shape of a network of vessels.
- A final layer maps that configuration to a score.

Nothing in this tells the model what it *should* look at. It finds whatever reduces the
training error, and the training error is defined by the labels.

**Vision transformers**, which have largely displaced convolutional networks at the frontier,
change the mechanism — they compare patches with each other rather than sliding filters — but
they do not change the epidemiology. Every problem in the rest of this lesson applies equally.

⚠ So resist the pull of architecture. In this shape the architecture is rarely the story: the
data, the label and the acquisition are.

## Section 2 · Confounded acquisition, and why it is the signature failure

Here is the mechanism, stated once, because everything famous in this area is an instance of it.

> **A medical image is not a neutral record of a patient. It is a record of a clinical
> encounter — and the encounter carries information about the diagnosis.**

Whoever took the image had already formed a suspicion. That suspicion shaped what equipment
was used, how the patient was positioned, what was placed in the frame, and where the image
came from. If any of that correlates with the label, the model will find it, because it is
easier to learn than the pathology.

The documented instances:

- **Surgical skin markings.** A clinician marks a lesion they intend to excise. Marked
  lesions are enriched for malignancy. A model shown marked and unmarked images learns to
  detect the pen.
- **Rulers.** Dermoscopy images of concerning lesions are more likely to include a scale.
- **Portable versus fixed X-ray.** Portable machines go to patients too sick to move.
  "Portable-ness" is visible in the image and predicts severity.
- **Chest drains.** A model predicting pneumothorax learns to spot the drain — which is only
  present *because someone already diagnosed and treated* the pneumothorax.
- **Site as a proxy.** Pool data from a specialist referral centre and a screening clinic, and
  scanner artefacts identify the site, which predicts prevalence.

✱ Note the shape of all five: **the model is right, for a reason that will not hold in
deployment.** This is not overfitting in the usual sense — the signal is real and reproducible
within the dataset. It is a *validity* problem, and it is invisible in any internal validation.

⚠ The practical test: ask what a **radiologist shown only the non-anatomical parts of the
image** could guess about the diagnosis. If the answer is "quite a lot", you have a confound.

## Section 3 · Who is in the training data

The second structural problem, and the one with the sharpest equity consequences.

A model's performance is a weighted average over the population it was tested on. Change the
population and the number changes, silently.

**The dermatology case is the standing example**, and its lesson is subtler than usually told.
Training and evaluation sets were dominated by lighter skin — Fitzpatrick types I–III. The
problem is not merely that performance is worse on darker skin. It is that for years
**skin type was not recorded in the evaluation sets at all**, so the failure was
*unmeasurable*. Purpose-built diverse test sets had to be constructed before anyone could
state the gap, and when they were, performance dropped.

✱ Unmeasured is worse than known-poor. A known limitation can be designed around: you set a
different threshold, you refer differently, you tell the user. An unmeasured one is simply
distributed as harm.

The same question generalises: which scanners, which age bands, which disease stages, which
countries, which comorbidities? A subgroup table is not a courtesy — it is the result.

## Section 4 · What generalises, and how to predict it in advance

You can often tell from the data description alone. The features that predict generalisation:

| Predicts generalising | Predicts failing |
|---|---|
| **Standardised acquisition** — fixed projection, calibrated device, trained operator | Uncontrolled capture — any phone, any light, any distance |
| **Label from an independent reference** — culture, PCR, histopathology | Label from the clinician being replaced |
| **Multi-site training and multi-site external validation** | Single archive, internal split |
| **Training population resembles deployment population** | Specialist-clinic data deployed in screening |
| **Continuous score with a locally tunable threshold** | One fixed vendor threshold |
| **A confirmatory step downstream** | The model is the decision |

⚠ Read that table against the TB chest X-ray and dermatology stories in the deep dive. TB CAD
has the left column almost throughout; dermatology apps have the right. **Both matched
specialists on a benchmark.** The table, not the benchmark, predicted which reached practice.

## Section 5 · Video, and what the extra dimension buys

Video adds time, which adds genuinely new capability and genuinely new problems.

**What it buys:** motion is diagnostic. Gait, tremor, infant spontaneous movement, cardiac
wall motion, swallowing, seizure semiology — none of these exist in a still frame. And video
allows *guidance*: a model can tell an operator to move the probe, which turns an unskilled
capture into a usable one.

✱ **The most important design idea in this whole lesson.** AI-guided obstetric ultrasound lets
someone with no sonography training sweep a probe and obtain a reliable gestational-age
estimate. The AI is not replacing a specialist's judgement; it is **moving a skill down the
cadre ladder**. Trialled in Zambia and the US. In a system with no sonographers, the
counterfactual is not a worse estimate — it is no estimate.

**What it costs:** frames within a video are massively correlated, so a random train/test split
across frames leaks catastrophically — the same patient, nearly the same image, on both sides.
Splits must be at the **patient** level, always. And video is identifiable in a way a chest
X-ray is not: faces, rooms, voices, gait.

⚠ And the ethically corrosive branch: video-based behavioural surveillance — mask compliance,
crowd density — deployed during COVID and largely abandoned. Worth studying as a governance
failure rather than a technical one.

## Section 6 · What imaging AI is actually worth

Where the value is real and demonstrated:

- **Task-shifting where the specialist does not exist.** TB CXR reading, retinal screening,
  AI-guided ultrasound, automated microscopy. The counterfactual is no service.
- **Triage of a queue.** Ranking studies so the urgent ones are read first. Modest, safe,
  genuinely useful, unglamorous.
- **Reading things humans cannot.** Systemic disease from retinal photographs, reduced
  ejection fraction from an ECG. Not faster human performance — a different capability.
- **Denominators from satellite imagery.** ✱ Quietly one of the highest-value uses in global
  health: building footprints and population estimates where no census exists. Nobody calls
  it medical AI and it underpins a great deal of coverage estimation.

Where it is oversold: autonomous diagnosis on consumer devices, anything where "matched
specialists on a curated benchmark" is presented as clinical readiness, and any product whose
threshold is fixed by the vendor.

---

## Key insight

**In this shape you cannot audit the input, so you must audit the acquisition.** You will
never inspect the feature the model used. What you can inspect is *how the images came to
exist* — who took them, with what, on what suspicion, and what else was in the frame. That
history is where the failure lives, and it is available in the methods section of any paper
willing to describe it.

---

## Worked example — a model with an AUC of 0.9 that has learned nothing

Dataset: a simulated cohort of 4,000 dermoscopy images. There is no image data — that is the
point. We only need the *structure*: a weak true signal, and a confound (a ruler in the frame)
that clinicians introduced because they were already suspicious.

This is the ruler, the skin marking and the chest drain, in twelve lines.

### In R

```r
library(tidyverse)

set.seed(7)
n <- 4000

# ---- The generative story ---------------------------------------------------
# `malignant` is truth. `lesion_signal` is the genuine but weak visual signal a
# model would have to learn from the pathology itself.
# `ruler` is the confound: a clinician who suspected malignancy photographed the
# lesion with a scale. It is not caused by the disease — it is caused by the
# SUSPICION of disease, which is why it will not exist in a screening setting.
dat <- tibble(
  malignant     = rbinom(n, 1, 0.20),
  lesion_signal = rnorm(n, mean = 0.45 * malignant, sd = 1),
  ruler         = rbinom(n, 1, ifelse(malignant == 1, 0.80, 0.10))
)

# ---- Two models, same data -------------------------------------------------
# Model A sees only the genuine signal. Model B sees only the confound.
# Neither is "wrong" arithmetically; they differ in what they will do next year.
auc <- function(p, y) {                     # Mann-Whitney U, no package needed
  n1 <- sum(y == 1); n0 <- sum(y == 0)
  (sum(rank(p)[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

pA <- predict(glm(malignant ~ lesion_signal, binomial, dat), type = "response")
pB <- predict(glm(malignant ~ ruler,         binomial, dat), type = "response")

c(signal_only   = auc(pA, dat$malignant),
  confound_only = auc(pB, dat$malignant))
# The confound alone should score far higher than the pathology. A model free to
# use both will lean almost entirely on the ruler, because it is easier to learn.

# ---- Deployment: the confound disappears ------------------------------------
# In a screening programme nobody has pre-selected the lesion, so rulers appear
# at the background rate and carry no information about the label.
deploy <- dat |>
  mutate(ruler = rbinom(n, 1, 0.15))        # same camera habits, no suspicion

fitB <- glm(malignant ~ ruler, binomial, dat)          # trained on the archive
auc(predict(fitB, newdata = deploy, type = "response"), deploy$malignant)
# Expect ~0.5. The model has not degraded — it never knew anything about skin.

# ---- What internal validation would have told you --------------------------
# Cross-validate the confounded model WITHIN the archive and it looks excellent,
# because the confound is present and predictive in every fold. This is why
# internal validation cannot detect this class of error: the problem is not
# variance, it is validity.
folds <- sample(rep(1:5, length.out = n))
cv <- map_dbl(1:5, function(k) {
  tr <- dat[folds != k, ]; te <- dat[folds == k, ]
  auc(predict(glm(malignant ~ ruler, binomial, tr), newdata = te,
              type = "response"), te$malignant)
})
c(cv_mean = mean(cv), deployment = auc(
  predict(fitB, newdata = deploy, type = "response"), deploy$malignant))
# Two numbers from the same model. Only one of them describes the future.
```

⚠ Not executed here (no Rscript in WSL). The construction is elementary and the direction of
each result is forced by how the data are generated, but the exact figures depend on the seed
and your R version. Read it for the mechanism.

✱ The final comparison is the lesson of the whole course in two numbers: a cross-validated
AUC and a deployment AUC, from one model, disagreeing completely — and no amount of
statistical care inside the archive can tell you which one you are looking at.

---

## Exercises

**Recall.** Name five documented confounds in medical imaging and, for each, say what clinical
decision put it in the frame.

**Application.** Take the table in Section 4 and score a medical imaging product you have read
about. Count the left-column features. Does the count, or its reported accuracy, better predict
whether it is in use?

**Application.** Run the worked example. Then change `ruler` so it is only mildly associated
with malignancy (say 0.4 versus 0.2). At what association strength does the confound stop
dominating the genuine signal? What does that tell you about how strong a confound needs to be
to matter?

**Conceptual.** A model detects reduced cardiac ejection fraction from an ECG better than
cardiologists can. Is this a confound, or a genuinely new capability? What evidence would
distinguish them?

**Challenge.** Design the subgroup table you would require before deploying a skin-lesion
classifier in a Belgian primary-care setting. Then design it for rural DRC. Explain every row
that differs — and note which rows you cannot fill from any published dataset.

---

## Connection to the course spine

Shape 3's debt is **calibration and PPV at the deployment prevalence** — and this lesson adds
the imaging-specific rider: *and a subgroup table, and an account of how the images were
acquired.* Without the acquisition story you cannot know whether the calibration will hold,
because you do not know what the model is calibrated *on*.

The second half of the spine is unusually stark here. Two models in the worked example have
the same shape, the same data and nearly the same code. One will work and one will not, and
**nothing in the modelling distinguishes them.** Only the evaluation — external, in the
deployment population — can.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified. Leads, not citations.

**Books**
- Goodfellow, Bengio & Courville, *Deep Learning* (free online) — ch. 9 for convolution, if
  you want the mechanism formally.

**Online**
- Oakden-Rayner L — blog and papers on hidden stratification and medical imaging dataset
  flaws. The most clear-eyed writing in this area, and readable.
- The ISIC archive and the Fitzpatrick-annotated dermatology datasets — worth browsing to see
  what a training set actually looks like.

**Key papers**
- Esteva A et al. *Dermatologist-level classification of skin cancer with deep neural
  networks.* **Nature** 2017.
- Winkler JK et al. *Association between surgical skin markings in dermoscopic images and
  diagnostic performance of a deep learning CNN for melanoma recognition.* **JAMA
  Dermatology** 2019. The confound, demonstrated.
- Daneshjou R et al. *Disparities in dermatology AI performance on a diverse, curated clinical
  image set.* **Science Advances** 2022;8:eabq6147. ✓ Verified — ROC-AUC of state-of-the-art
  models dropped **27–36%** on the 656-image DDI set.
- Zech JR et al. *Variable generalization performance of a deep learning model to detect
  pneumonia in chest radiographs: a cross-sectional study.* **PLOS Medicine** 2018. Site as a
  confound, cleanly shown.
- Roberts M et al. *Common pitfalls and recommendations for using machine learning to detect
  and prognosticate for COVID-19 using chest radiographs and CT scans.* **Nature Machine
  Intelligence** 2021.
- **Pokaprakarn T, et al.** *AI estimation of gestational age from blind ultrasound sweeps in
  low-resource settings.* **NEJM Evidence** 2022; doi:10.1056/EVIDoa2100058.
  ✓ **Verified 2026-08-21** — 4,695 pregnant volunteers in North Carolina and Zambia,
  Sept 2018–June 2021, novice operators and low-cost devices. A 2024 JAMA diagnostic-accuracy
  study follows it.
- WHO consolidated guidelines on tuberculosis, Module 2: Screening (2021) — CAD for CXR.

---

## Retain long-term

- A convolutional network learns edges → textures → configurations; nothing tells it what to look at.
- Architecture is rarely the story in this shape. The data, the label and the acquisition are.
- A medical image records a clinical encounter, not just a patient — and the encounter carries the diagnosis.
- Five confounds: skin markings, rulers, portable X-ray, chest drains, site artefacts.
- Confounded acquisition is a validity problem, invisible to internal validation.
- Unmeasured subgroup performance is worse than known-poor performance: it cannot be designed around.
- What predicts generalising: standardised acquisition, independent label, multi-site validation, matched population, tunable threshold, confirmatory step downstream.
- Video splits must be at patient level; frames within a video leak catastrophically.
- AI-guided ultrasound moves a skill down the cadre ladder — the strongest design pattern in imaging AI.
