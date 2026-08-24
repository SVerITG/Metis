# Lesson 6 — Finding structure: clustering, embeddings, and clusters that are not there

> **Concept map**
> **Builds on** — Lesson 1 (shape 4 and its comparators: scan statistics, latent class analysis); Lesson 2, because a scan statistic does detection and grouping at once.
> **Connects to** — Lesson 9, though its usual tools do not apply here: with no labels there is nothing to calibrate against.
> **Leads to** — Lesson 8, since a discovered cluster usually exists in order to send someone somewhere.

> ⚠ **A note to the researcher specifically.** This is your ground — SaTScan, spatial scan statistics and
> multilevel structure are things you use professionally, and I am not going to explain them to
> you. What this lesson is *for* is the part that transfers: why unsupervised methods are
> structurally harder to evaluate than anything else in this course, stated in a way you can
> hand to someone who does not already know it. Correct me where I am wrong; the spatial
> sections are the ones most likely to need it.

## Why this matters

Every other shape has a right answer somewhere. There is a diagnosis, a future value, a case
count, a text field, a decision that was taken. You can be wrong, and someone can show you.

This shape has none of that. You ask "what groups are in here?", the algorithm returns groups,
and there is **nothing to compare them against.** Which produces the field's defining property:

> **The algorithm is definitionally right. It returned the clusters it was asked for, and
> "anomalous" or "grouped" is defined by the model, so the model cannot be contradicted by its
> own output.**

Everything difficult about shape 4 follows from that sentence.

## Learning objectives
By the end of this lesson you will be able to:
- **Demonstrate** that standard clustering diagnostics report structure in pure noise.
- **Explain** why replication in an independent dataset is the only honest validation available.
- **Read** a UMAP or t-SNE plot correctly, which mostly means knowing what not to read from it.
- **State** the ethical difference between clustering viruses and clustering people.

## Prerequisites
Lesson 1. Spatial statistics assumed, not taught.

---

## Section 1 · The algorithm always answers

Ask k-means for three clusters and you get three clusters. Ask for six and you get six. It has
no way of telling you there were none, because "none" is not in its output space.

That would be a footnote if the diagnostics caught it. They do not. Below, 300 points drawn
**uniformly at random on the unit square** — a dataset containing, by construction, no clusters
at all:

| k | Within-cluster sum of squares | Mean silhouette | Cluster sizes |
|---|---|---|---|
| 2 | 30.35 | 0.360 | 150, 150 |
| 3 | 18.55 | 0.394 | 94, 99, 107 |
| 4 | 12.18 | **0.407** | 60, 70, 79, 91 |
| 5 | 10.35 | 0.371 | 55, 58, 58, 60, 69 |
| 6 | 8.31 | 0.377 | 38, 39, 53, 54, 57, 59 |

Three things to notice, and each is a trap:

1. **The silhouette is around 0.4 throughout.** In isolation that reads as "moderate but real
   structure". It is noise.
2. **The WSS curve falls smoothly**, 30 → 18 → 12 → 10 → 8. Read it for an elbow and you will
   find one, around k = 3 or 4. There is no elbow to find.
3. **The clusters are balanced and plausible** — roughly equal sizes, contiguous regions. They
   look exactly like a real finding looks.

For comparison, the same diagnostics on three genuinely separated Gaussians: WSS drops from
20.1 to **1.45** at k=3 and then flattens, and the silhouette reaches **0.860**.

✱ So the diagnostics are not useless — they are **only interpretable comparatively.** 0.39 versus
0.86 is informative; 0.39 alone is not. And virtually nobody reports the noise baseline. The fix
is cheap and almost never done: **permute or simulate your data under a no-structure null and run
the identical pipeline.** If the null gives you a silhouette of 0.39 and your data give 0.42, you
have found nothing.

## Section 2 · Why your own field solved this first

Spatial epidemiology confronted this earlier and more honestly than machine learning has, and
the solution is worth naming because it is the template.

The **spatial scan statistic** does not just find the most unusual window. It compares the
observed maximum likelihood ratio against **the distribution of that maximum under a null model**,
obtained by Monte Carlo. So the question it answers is not "where is the most extreme cluster?" —
which always has an answer — but *"is the most extreme cluster more extreme than chance would
produce, given that I looked in thousands of places?"*

✱ That is exactly the discipline the clustering literature usually lacks. The scan statistic is
shape 4 **with the multiple-comparisons problem taken seriously**, and it is the comparator any
ML clustering claim on spatial data should be held to.

⚠ It has its own well-known limits — the shape of the scanning window constrains what can be
found, and a maximum-likelihood window is not a boundary you should draw on an operational map
without judgement. But the inferential structure is right, and it is the thing to transfer.

## Section 3 · Replication is the only honest validation

With no labels, internal metrics cannot establish that a structure is real. What can:

1. **Replication in an independent dataset.** Do the same subgroups appear in a different
   cohort, a different country, a different year? This is the strongest available evidence and
   the one most often skipped.
2. **A null comparison.** Section 1. Cheap, and it should be mandatory.
3. **External validity of the groups.** Do the clusters differ on something you did *not* cluster
   on — outcome, treatment response, an independent biomarker? A cluster that predicts nothing
   external is a description of your distance metric.
4. **Stability under perturbation.** Resample, drop features, change the algorithm. Structure
   that vanishes when you switch from k-means to hierarchical clustering was an artefact of
   k-means.

**The standing case:** latent-class analysis of sepsis patients (Seymour et al.) identified four
clinical phenotypes with apparently different treatment responses. It is the best example of
clustering that meant something — and the subsequent literature on whether those phenotypes
replicate across cohorts is genuinely mixed. ⚠ Both halves of that sentence are the lesson: the
finding was important *and* replication is hard, and a field that reports only the first half is
not doing shape 4 properly.

## Section 4 · Embeddings — the same problem, better hidden

An **embedding** turns any object — a patient, a document, an image, a sequence — into a vector,
positioned so that similar things sit near each other. It is the engine under retrieval, RAG,
deduplication, record linkage and image search, and it is genuinely powerful.

But "similar" is defined by whatever the embedding was trained on. A clinical-note embedding
trained on US discharge summaries encodes US documentation habits as similarity. So the geometry
you then cluster is not a neutral space; it is a model of someone else's data.

⚠ And now the visualisation problem, because this is where errors are most common in published
figures. **In a UMAP or t-SNE plot:**

- **Distances between clusters are not meaningful.** Two blobs far apart are not more different
  than two blobs close together.
- **Cluster sizes are not meaningful.** The algorithms deliberately expand sparse regions and
  compress dense ones.
- **The number of visible blobs depends on the hyperparameters** — perplexity, `n_neighbors`,
  `min_dist` — and can be tuned into or out of existence.
- Only **local neighbourhood** structure is approximately preserved, and that is all.

✱ Which makes the standard figure — a UMAP with coloured groups and a caption asserting three
populations — close to uninterpretable as evidence. It is a picture of a hyperparameter choice.
Use it to look, never to conclude.

## Section 5 · Clustering people is not clustering viruses

Shape 4 has a distinctive ethical edge, because a cluster is often a set of *people*.

**Genomic transmission clustering** in TB and HIV groups sequences by relatedness to infer likely
transmission. Epidemiologically valuable. But an HIV molecular cluster identifies **people whose
viruses are closely related**, which is information about who may have infected whom — in a
setting where transmission can be criminalised, and where the people concerned did not consent to
that inference. This is a live controversy, not a hypothetical, and the disagreement is between
people who all want the epidemic to end.

**Phenotyping and stratification** for programme targeting has the milder version of the same
problem: a discovered subgroup becomes an administrative category, then a resource-allocation
category, and eventually a fact about people rather than a feature of a dataset.

⚠ The question to ask before clustering people: **what happens to someone because of the group
they were placed in, and can they contest it?** A cluster that only informs analysis is one
thing. A cluster that triggers an action — see Lesson 8 — is another.

## Section 6 · What this shape is actually worth

**Genuinely valuable:**
- **Spatial cluster detection with a proper null.** Your ground, and the methodologically
  strongest use in the shape.
- **Embeddings as infrastructure** — retrieval, linkage, deduplication. Here the clusters are a
  means, and the system is evaluated on the end task, which sidesteps the whole problem.
- **Hypothesis generation.** A cluster that prompts a study is a success even if the cluster
  itself turns out not to replicate. ✱ This is the honest framing for most of the shape, and it
  is much less often claimed than it should be.

**Overstated:** discovered subtypes presented as discovered *entities*; UMAP figures as evidence;
any clustering result without a null comparison or a replication attempt.

---

## Key insight

**This is the only shape where the model defines the answer, so it cannot be contradicted by its
own output.** Which means the evidence has to come from outside: a null model, a second dataset,
or an external variable the clusters were not built from.

And the practical corollary, which is the whole lesson in one line: **run your pipeline on
data you know has no structure, and report what it finds.**

---

## Worked example — clusters from nothing at all

Dataset: 300 points drawn uniformly at random. There is no structure. Watch every standard
diagnostic report some anyway.

### In R

```r
library(tidyverse)
library(cluster)          # silhouette()

set.seed(23)

# ---- A dataset with, by construction, NO clusters -------------------------
noise <- tibble(x = runif(300), y = runif(300))

# ---- The standard workflow, applied to nothing ---------------------------
# WSS for an elbow plot, and mean silhouette for "cluster quality".
# Both are computed exactly as they would be on real data.
diag_for_k <- function(dat, k) {
  km <- kmeans(dat, centers = k, nstart = 25)
  sil <- silhouette(km$cluster, dist(dat))
  tibble(k = k,
         wss = km$tot.withinss,
         mean_silhouette = mean(sil[, "sil_width"]),
         sizes = paste(sort(km$size), collapse = ","))
}

map_dfr(2:6, ~ diag_for_k(noise, .x))
#>     k   wss  mean_silhouette  sizes
#>     2 30.35            0.360  150,150
#>     3 18.55            0.394  94,99,107
#>     4 12.18            0.407  60,70,79,91
#>     5 10.35            0.371  55,58,58,60,69
#>     6  8.31            0.377  38,39,53,54,57,59
#
# Silhouette ~0.4 throughout, a smooth WSS decline that reads as an elbow at
# k=3 or 4, and balanced plausible-looking clusters. All of it from noise.

# ---- The comparison that makes the numbers interpretable -----------------
real <- bind_rows(
  tibble(x = rnorm(100, 0.20, 0.05), y = rnorm(100, 0.20, 0.05)),
  tibble(x = rnorm(100, 0.80, 0.05), y = rnorm(100, 0.25, 0.05)),
  tibble(x = rnorm(100, 0.50, 0.05), y = rnorm(100, 0.85, 0.05)))

map_dfr(2:6, ~ diag_for_k(real, .x))
# WSS collapses to ~1.45 at k=3 then flattens; silhouette reaches ~0.86.
# 0.39 vs 0.86 is informative. 0.39 on its own is not.

# ---- The step that should be mandatory and almost never is ---------------
# Permute your real data to destroy structure while preserving the marginal
# distributions, run the IDENTICAL pipeline, and compare. If the null gives
# 0.39 and your data give 0.42, you have found nothing.
null_silhouette <- function(dat, k, reps = 20) {
  map_dbl(seq_len(reps), function(i) {
    permuted <- dat |> mutate(across(everything(), sample))
    diag_for_k(permuted, k)$mean_silhouette
  })
}

tibble(
  observed = diag_for_k(real, 3)$mean_silhouette,
  null_mean = mean(null_silhouette(real, 3)),
  null_max  = max(null_silhouette(real, 3))
)
# Report this table, not the silhouette alone.
```

⚠ The noise and clustered tables above **were computed** (with a hand-rolled k-means and
silhouette in Python, so R's `nstart = 25` may shift the third decimal). The R has not been
executed here.

---

## Exercises

**Recall.** State why internal clustering metrics cannot establish that a structure is real, and
name the four things that can.

**Application.** Run the worked example, then take any clustering you have done or read about and
compute the permutation null. Report the observed value beside the null distribution.

**Application.** Find a published UMAP figure with coloured groups. List what the figure does and
does not license you to conclude.

**Conceptual.** Explain the spatial scan statistic's Monte Carlo null to someone who clusters
gene-expression data, and say what they should borrow from it.

**Challenge.** You are asked to identify high-risk villages by clustering surveillance data.
Write the design: what null, what replication, what external variable, and what happens to a
village placed in the high-risk group. Then say which of the four you could actually deliver.

---

## Connection to the course spine

Shape 4's debt is **replication in an independent dataset** — and this lesson is why that is the
specific debt rather than calibration or a scoring rule. Without labels there is nothing to
calibrate, so the only evidence available comes from outside the analysis: a null, a second
cohort, an external variable.

The spine's second half takes its purest form here. The model cannot be wrong about its own
output. So *everything* that determines whether the finding is real is evaluation, and none of it
is modelling.

---

## Sources

⚠ Written from model knowledge to mid-2026, not verified. Leads, not citations. The spatial
references are the ones you will know better than I do.

**Your ground, for completeness**
- **Kulldorff M.** *A spatial scan statistic.* **Communications in Statistics** 1997 — and the
  SaTScan documentation, which is unusually good on the Monte Carlo null.
- **Getis A, Ord JK** on local spatial association statistics.
- **Diggle PJ.** *Statistical Analysis of Spatial and Spatio-Temporal Point Patterns.*

**The clusters-that-are-not-there problem**
- **Tibshirani R, Walther G, Hastie T.** *Estimating the number of clusters in a data set via the
  gap statistic.* **JRSS-B** 2001. The gap statistic *is* the null comparison, formalised — and
  it is much less used than the elbow it should have replaced.
- **von Luxburg U, Williamson RC, Guyon I.** *Clustering: science or art?* 2012. Short and
  clarifying on why this shape resists evaluation.
- **Hennig C** on cluster validation and stability.

**Phenotyping**
- **Seymour CW, Kennedy JN, Wang S, et al.** *Derivation, validation, and potential treatment
  implications of novel clinical phenotypes for sepsis.* **JAMA** 2019;321:2003–2017;
  doi:10.1001/jama.2019.5791. ✓ **Verified 2026-08-21.** Then read the replication literature
  that followed it.

**Embeddings and their visualisation**
- **Wattenberg M, Viégas F, Johnson I.** *How to use t-SNE effectively.* **Distill** 2016. The
  clearest demonstration that these plots mislead, with interactive examples.
- **Chari T, Pachter L.** *The specious art of single-cell genomics.* ~2023. Blunt, and the
  argument generalises well beyond genomics.

**Ethics of clustering people**
- The literature on **HIV molecular surveillance** and community objections to it — a genuine
  disagreement between people who all want the epidemic to end.

---

## Retain long-term

- The algorithm always returns clusters; "none" is not in its output space.
- 300 uniform random points gave mean silhouette 0.36–0.41 and a smooth WSS curve that reads as an elbow. Real clusters gave 0.86.
- Internal metrics are only interpretable **comparatively**. Run the pipeline on a null and report both.
- Four honest validations: replication in an independent dataset, a null comparison, external validity of the groups, stability under perturbation.
- The spatial scan statistic is shape 4 with the multiple-comparisons problem taken seriously — the template the ML literature usually lacks.
- In UMAP and t-SNE: between-cluster distances, cluster sizes and the number of visible blobs are all uninterpretable. Only local neighbourhoods are approximately preserved.
- An embedding's notion of "similar" is inherited from its training data.
- Clustering people is not clustering viruses: ask what happens to someone because of their assigned group, and whether they can contest it.
- Hypothesis generation is an honest and sufficient claim for most of this shape.
- This is the only shape where the model defines the answer, so all the evidence must come from outside it.
