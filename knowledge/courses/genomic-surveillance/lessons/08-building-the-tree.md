# Lesson 8 — Building the tree: substitution models, likelihood, support, and rooting

> **Concept map**
> **Builds on** — Lesson 7 (what the object is) and Lesson 2 (what the changes are).
> **Connects to** — Lesson 9, which adds time, and Lesson 10, which reads epidemiology off the shape.
> **Leads to** — Deep Dive 1, which specifies `IQ-TREE 3` with `ModelFinder` selecting `GTR+F+R3`. By the end of this lesson that string will be transparent.

## Why this matters

Tree building is where genomic surveillance stops being descriptive and starts being statistical inference, and it is the step most people take on trust. That is usually defensible — modern software has good defaults — but three of the choices inside it change conclusions rather than aesthetics:

- **The substitution model**, which determines how genetic distance is converted into evolutionary distance, and therefore every branch length.
- **The support values**, which determine which parts of the tree you are allowed to argue from.
- **The rooting**, which determines the *direction of time* and therefore every statement about origin, ancestry and spread.

Get rooting wrong and you can invert an outbreak's story entirely: the source becomes the destination.

## Learning objectives
By the end of this lesson you will be able to:

- **Decode** a model string such as `GTR+F+R3` component by component.
- **Explain** why maximum likelihood is preferred over parsimony and distance methods for surveillance-scale data.
- **Interpret** bootstrap and ultrafast bootstrap support, and say what a support value does *not* mean.
- **Compare** the three rooting strategies and choose one with a reason.
- **Identify** the three ways a tree can be confidently wrong: recombination, homoplasy and batch effects.

## Prerequisites
Lessons 0–7. No linear algebra. Likelihood is described conceptually.

---

## Section 1 · Why you need a model at all

Count the differences between two sequences and you get an **observed** distance. But observed distance systematically **underestimates** true evolutionary distance, for one reason: **multiple hits**. A site that changed A→G→A reads as no change. A site that changed A→G in one lineage and A→G independently in the other reads as no difference.

The more time has passed, the worse the underestimate, until distance saturates entirely. A substitution model is the correction: a probabilistic description of how bases change, used to infer how much change *actually* occurred given how much you *see*.

For very closely related outbreak sequences — a 100-day window on one virus — multiple hits are rare and the correction is small. **The model matters much less in outbreak analysis than in deep phylogenetics.** But it is not nothing, especially when rate variation across sites is strong, and it costs nothing to do properly.

## Section 2 · Decoding `GTR+F+R3`

The model chosen by ModelFinder for the 2026 Bundibugyo alignment. Four components.

### `GTR` — General Time Reversible
The most general standard nucleotide substitution model. It allows a **separate rate for each of the six reversible base-change types** (A↔C, A↔G, A↔T, C↔G, C↔T, G↔T). "Time reversible" means the process looks the same forwards and backwards in time — a mathematical convenience that makes likelihood computable and that is why unrooted trees are what likelihood naturally produces.

Simpler models are special cases, and it is useful to see the ladder:

- **JC69** — all substitutions equally likely, all base frequencies equal. One parameter.
- **K80** — transitions and transversions differ (Lesson 2's ratio). Two.
- **HKY85** — K80 plus unequal base frequencies.
- **GTR** — all six rates free plus unequal base frequencies. Six rate parameters.

### `+F` — empirical base frequencies
Base frequencies are taken **from your alignment** rather than estimated as free parameters. Genomes are not 25% each base; filovirus genomes are AT-rich. `+F` uses the observed composition, which is both more accurate and cheaper than fitting it.

### `+R3` — FreeRate heterogeneity with 3 categories
The important one, and the one worth understanding.

**Sites do not evolve at the same rate.** Third codon positions are largely free to change; first and second positions are constrained; non-coding regulatory regions are constrained; some sites are essentially invariant. Ignoring this rate heterogeneity biases branch lengths downwards, because the fast sites saturate while the slow ones contribute nothing.

Two ways to model it:

- **`+G` (gamma)** — assume rates follow a gamma distribution, discretised into (usually 4) categories governed by one shape parameter α. Standard for thirty years, and constrained by the assumed distributional shape.
- **`+R` (FreeRate)** — do not assume a distribution. Estimate *k* rate categories and their proportions freely from the data. `+R3` means three categories, each with its own rate and its own weight.

So `GTR+F+R3` reads as: **all six substitution types free, base composition taken from the data, and three freely-estimated site-rate classes.** For an alignment of 525 near-identical 19 kb filovirus genomes, that is a sensible, unconstrained description of a mostly-constrained genome with a minority of fast-evolving sites.

### `ModelFinder`
You do not choose the model by taste. **ModelFinder** (built into IQ-TREE) fits many candidate models and ranks them by an information criterion (BIC by default), trading fit against parameter count. Reporting "ModelFinder selected GTR+F+R3" is reporting a *procedure*, which is why it is the right thing to write in a methods section.

✱ **IQ-TREE 3** — the version used here — extends this further: `MixtureFinder` selects mixture models and automatically determines the number of classes, gene and site concordance factors quantify discordance across genomic regions, and a Python interface (`piqtree`) exposes the inference engine for scripted workflows. For outbreak-scale single-locus data you will mostly use the classical path, but the mixture machinery is where the field is heading for multi-gene and multi-segment problems.

## Section 3 · How the tree is actually estimated

### Distance methods (Neighbour-Joining)
Compute pairwise distances, build a tree by successive joining. Instant, deterministic, and **discards the site-by-site information** by summarising each pair as one number. Fine for a quick look; not for an inference you will defend.

### Maximum parsimony
Choose the tree requiring the fewest changes. Intuitive, no explicit model, and biased when rates vary — its characteristic failure is **long branch attraction**, where two rapidly evolving lineages are pulled together because they share changes by chance.

### Maximum likelihood — the standard
For a given tree (topology + branch lengths) and a substitution model, compute the probability of observing your alignment. Search tree space for the tree maximising that probability.

- Uses all the information in every site.
- Model-explicit, so the assumptions are visible and testable.
- Computationally heavy, but solved in practice: `IQ-TREE`, `RAxML-NG`, `FastTree` (approximate, very fast).

### Bayesian inference
Estimate a **posterior distribution over trees** by MCMC, given priors. Slower still, but the output is an honest quantification of uncertainty, and it is the natural home for adding time, clocks and population models — which is exactly why Lesson 9 moves to `BEAST X`.

### At scale
Standard ML handles thousands of tips. It does not handle millions, which SARS-CoV-2 required, prompting a different family of methods (`UShER` and relatives) that *place* new sequences onto an existing mutation-annotated tree rather than rebuilding from scratch. For outbreak work at hundreds of genomes — 525 in the flagship — classical ML is the right tool.

## Section 4 · Support: how much of the tree can you argue from?

A tree is a point estimate. Support values say which parts of it survive resampling.

**Bootstrap.** Resample alignment columns with replacement, rebuild the tree, repeat 100–1,000 times. The bootstrap value on a branch is the percentage of replicates containing that split. Conventional reading: ≥70% is reasonable support, ≥95% strong.

**Ultrafast bootstrap (UFBoot, IQ-TREE).** An approximation that is orders of magnitude faster — essential at surveillance scale. **Its values are less biased and should be read on a different scale: ≥95% is the threshold for "well supported", not 70%.** Reading UFBoot on the classical bootstrap scale over-states confidence, and this is a common error.

**SH-aLRT.** A fast branch test, often reported alongside UFBoot. Many workflows require both (e.g. SH-aLRT ≥ 80% *and* UFBoot ≥ 95%).

**Posterior probability** (Bayesian). The probability of the clade given data, model and priors. Directly interpretable and generally higher than bootstrap for the same data.

⚠ **What support does not mean.** A support value tells you how consistently *your data under your model* recover a split. It says nothing about whether the model is right, whether the alignment is right, or whether the sampling is representative. **A tree can be strongly supported and thoroughly misleading** — batch-effect clusters (Lesson 5) get excellent bootstrap support, because the contaminating reads really are shared.

✱ And the specific outbreak problem: **at outbreak timescales there is very little signal per branch.** With 0.66 substitutions per transmission, many internal branches rest on a single mutation and will have poor support by construction. That is not a failure of the analysis; it is the honest resolution limit. The correct response is to collapse those branches into polytomies — as the Bundibugyo authors did with near-zero-length branches — not to present a fully bifurcating tree and argue from its fine structure.

## Section 5 · Rooting — the choice that sets the direction of time

Likelihood under a time-reversible model produces an **unrooted** tree: relationships without direction. Rooting is a separate decision, and it determines what is ancestral to what — and therefore every claim about origin and spread.

### Outgroup rooting
Include a sequence known to be outside the group of interest; the root is where it attaches. The gold standard when a good outgroup exists. In a single-outbreak analysis, often there is no suitable outgroup — an earlier BDBV outbreak genome is decades divergent and can distort branch lengths.

### Midpoint rooting
Place the root at the midpoint of the longest tip-to-tip path. Assumes a roughly constant rate across lineages. Convenient, and quietly wrong whenever rates vary.

### Clock-based / residual-minimising rooting — the right one for outbreaks
Choose the root that makes the data look most like a molecular clock: the root position that produces the best root-to-tip-versus-date regression, i.e. **minimises the residuals**.

This is what the Bundibugyo analysis did — "tree rooted to minimize residuals" — and it is the appropriate choice for a densely sampled, time-stamped outbreak with no natural outgroup. `TempEst` does this interactively; several pipelines do it automatically; and in a full Bayesian analysis (Lesson 9) the root is inferred jointly with everything else rather than fixed in advance.

⚠ **The circularity to keep in view:** clock-based rooting uses temporal signal to place the root, and then the same rooted tree is used to demonstrate temporal signal. This is why the Bundibugyo workflow is iterative and why the root-to-tip regression slope (7.9 × 10⁻⁴) is reported as a *cross-check* against the independent Bayesian estimate (8.5 × 10⁻⁴) rather than as the primary result. Agreement between a quick heuristic and a full model is real reassurance; a heuristic validating itself is not.

## Section 6 · Three ways to be confidently wrong

**Recombination and reassortment.** The entire framework assumes one tree describes the whole alignment. Recombination breaks that: different regions have different histories, and forcing one tree onto them produces a tree that is wrong everywhere and well-supported. Detect and handle it — `Gubbins` and `ClonalFrameML` remove recombinant regions in bacteria; for influenza you build a tree **per segment**; for HIV and coronaviruses recombination is routine and must be screened for.

**Homoplasy.** The same change arising independently (Lesson 2) makes unrelated lineages look related. Convergent drug-resistance mutations are the classic case, which is why those sites are masked before tree building in bacterial surveillance.

**Batch effects.** Contamination and index hopping produce shared spurious variants, which produce a well-supported clade of samples that share nothing but a flow cell. **Colour the tree by sequencing run.** Every time.

## Practice

Take a published ML tree in your field and answer:

1. What model, and was it selected by a procedure or asserted?
2. What support metric, on what scale, and what threshold was used to call a clade supported?
3. How was the tree rooted, and was the reason given?
4. Were near-zero branches collapsed, or does the figure show full bifurcation it cannot support?
5. Was recombination screened for, and does this pathogen need it?

Papers that answer all five are a minority, and their trees are the ones worth arguing from.

## In one paragraph

Tree building corrects observed differences into evolutionary distances using a substitution model — `GTR+F+R3` means all six change types free, base composition taken from the data, and three freely-estimated site-rate classes, chosen by ModelFinder rather than by taste. Maximum likelihood uses every site and makes its assumptions explicit, which is why it is the standard; support values then tell you which splits survive resampling, with ultrafast bootstrap read at ≥95% rather than the classical ≥70%, and with the honest expectation that at outbreak timescales many branches rest on a single mutation and should be collapsed rather than drawn. Rooting is a separate decision that sets the direction of time, and for a densely sampled outbreak with no outgroup the defensible method is the clock-based one — the root that minimises root-to-tip regression residuals. Recombination, homoplasy and sequencing batch effects can all produce trees that are strongly supported and entirely wrong.
