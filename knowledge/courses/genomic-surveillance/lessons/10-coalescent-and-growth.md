# Lesson 10 — Phylodynamics: reading epidemic dynamics off the shape of a tree

> **Concept map**
> **Builds on** — Lesson 9 (you need a time tree before any of this means anything).
> **Connects to** — Lesson 13, because every quantity here is conditional on the sampling process.
> **Leads to** — Deep Dive 1's second headline: a doubling time of 21.0 days, and a SkyGrid curve that rises and then flattens.

## Why this matters

Here is the idea that gives the field its name, and it is genuinely surprising the first time you meet it:

> **The *shape* of a time-scaled phylogeny contains information about the epidemic that produced it — how fast it grew, roughly how many infections were sustaining it, and whether it is still growing — even without a single case report.**

Not the topology's fine detail; the **distribution of node times**. When an epidemic is small, lineages find common ancestors quickly, so nodes bunch up. When it is large, lineages take longer to coalesce, so nodes spread out. Read the node-time distribution and you can invert it for population dynamics.

This is powerful and it is dangerous, in a specific way: **changes in sampling look exactly like changes in dynamics.** Most of this lesson is the machinery; the last third is how not to be fooled by it, which is where the Bundibugyo analysis does its most careful work.

## Learning objectives
By the end of this lesson you will be able to:

- **Explain** coalescent intuition: why small populations produce bunched coalescences.
- **Distinguish** effective population size from prevalence, and state the three reasons they differ.
- **Choose** between constant, exponential, skyline/SkyGrid and birth–death tree priors.
- **Interpret** a SkyGrid plot, including what a flattening curve does and does not imply.
- **Design** the sensitivity analysis that separates a real change in dynamics from a change in sampling.

## Prerequisites
Lessons 0–9.

---

## Section 1 · Coalescent intuition

Run time backwards. Two lineages sampled today had a common ancestor at some point in the past. **How far back depends on how many infections there were to choose from.**

- **Small infected population:** few possible parents, so two lineages find a common ancestor quickly. Coalescences cluster near the present. The tree looks *bushy near the tips*.
- **Large infected population:** many possible parents, so lineages wander a long time before meeting. Coalescences are spread out and pushed deeper. Long internal branches.

Formally, the rate of coalescence between any two lineages is inversely proportional to the **effective population size Ne**. That inverse relationship is the engine: node times are data about Ne, and a time tree is a noisy measurement of Ne through time.

```
   SMALL Ne (or early epidemic)          LARGE Ne (established epidemic)

        ╱╲╱╲╱╲                              ╱      ╲
       ╱  ╲ ╲ ╲                            ╱   ╱╲   ╲
      coalescences bunched               ╱   ╱   ╲    ╲
      close to the present              long internal branches,
                                        coalescences spread out
```

## Section 2 · Effective population size is not prevalence

The number that comes out is **Ne**, and in phylodynamics you will often see **Ne·τ** — the effective population size multiplied by generation time. Three reasons it is not the number of infected people:

**1. Variance in transmission.** Ne is the size of an *idealised* population that would produce the observed genetic variability. Real epidemics are overdispersed: a minority of cases cause most transmission. Superspreading reduces the effective size far below the census size — sometimes by an order of magnitude. **Ne is not smaller than prevalence because of a counting error; it is smaller because transmission is unequal.**

**2. Generation time.** The coalescent estimates Ne·τ. To convert to a number of infections you must divide by generation time, which you must supply from elsewhere, with its own uncertainty.

**3. Population structure.** Geographic and contact structure make lineages coalesce more slowly than a well-mixed model predicts, inflating apparent Ne. An epidemic spread across 21 health zones is not a well-mixed population.

⚠ **So Ne is a good indicator of the *shape and trend* of an epidemic and a poor estimator of its *size*.** Read the curve; do not read the axis as a case count. This is the most common misreading of a skyline plot.

## Section 3 · The four tree priors you will meet

In Bayesian phylodynamics the demographic model is the **tree prior** — the model of how the population produced the tree. It is not a nuisance parameter; it is the epidemiological hypothesis.

### Constant size
Ne fixed. Rarely appropriate for an outbreak, useful as a null.

### Exponential growth
Ne grows exponentially at rate *r*. Two parameters, so it is powerful when growth really is exponential — which, for an epidemic in its early phase, it approximately is. It gives you the number everybody wants:

> **Doubling time = ln(2) / r**

The Bundibugyo exponential-growth analysis returned a **doubling time of 21.0 days (95% HPDI 15.0–40.7)**. Note the interval: the point estimate is 21 days, but doubling times up to about six weeks are entirely consistent with the data. **Quote the interval.**

### Skyline / SkyGrid — non-parametric
Do not assume a shape. Divide time into intervals and estimate Ne separately in each, with a smoothing prior linking adjacent intervals so the curve does not thrash.

The Bundibugyo specification, decoded: **"SkyGrid non-parametric model with 31 transition points at one-week intervals and a cutoff of 32 weeks."**

- **32-week cutoff** — the model looks back 32 weeks from the most recent sample. Beyond that, one constant value.
- **31 transition points at one-week intervals** — those 32 weeks are split into weekly blocks, with Ne free to change at each boundary.
- **Weekly resolution** is a deliberate match to the epidemiological question: for a filovirus with a serial interval of about two weeks, weekly is fine enough to see real change and coarse enough to be estimable.

✱ **Grid resolution is a choice with consequences.** Too coarse and you smooth away the feature you were looking for. Too fine and each interval has almost no coalescent events, so the smoothing prior — not the data — determines the curve. Weekly over 32 weeks, with 525 genomes, is a sensible balance, and it is a balance worth interrogating in any skyline you read.

### Birth–death models
A different framework: model birth (transmission), death (recovery/removal) and sampling as explicit processes. Advantages:

- **Estimates Re directly**, which is the quantity public health actually uses, rather than Ne which needs conversion.
- **Models sampling explicitly** as a parameter, rather than conditioning on it.
- **Birth–death skyline** allows Re to change in intervals, which is how you detect the effect of an intervention.

Trade-off: you must specify or estimate the sampling proportion and the removal rate, and Re estimates are sensitive to both.

**Rough guide:** coalescent when sampling is a small, poorly-characterised fraction and you want trends; birth–death when you can characterise sampling and want Re on the same scale as the case-based estimate.

## Section 4 · What the Bundibugyo curve showed

The reported pattern: **"a relatively slow start and then an increased rate of growth from March until June, after which the rate appears to decline."** Plus: **"genomic and phylogenetic diversity was maintained and increasing during the sampling period, without any indication of fitness-altering mutations or a particular lineage starting to dominate."**

Take those apart, because both sentences are doing careful work.

**"Slow start, then acceleration from March to June."** Consistent with the tMRCA of late February: a period of low-level transmission before amplification. The amplification phase begins roughly when transmission moved into settings that sustain it, and it precedes the outbreak declaration on 15 May.

**"After which the rate appears to decline."** The word is *appears*, and the authors immediately treat it as suspect — because a decline in inferred Ne at the end of a dataset is exactly what reduced sampling produces. Section 5.

**"Diversity maintained and increasing, no lineage dominating."** This is a *negative* finding and it is arguably the most operationally useful sentence in the post. A lineage sweeping to dominance would be a signal of possible fitness change — greater transmissibility, immune escape, diagnostic escape. Its absence means the epidemiological picture is not being driven by viral evolution, and that the diagnostics and the response logic remain sound. **Reporting "nothing has changed" is a result, and one that requires just as much work as a positive finding.**

## Section 5 · Sampling change versus dynamic change — the central problem

> **A phylodynamic curve is estimated from the tree, and the tree is estimated from the samples you took. Anything that changes your sampling changes the curve.**

Ways this bites:

- **Sampling declines at the end** (funding, fatigue, insecurity, a policy change). Fewer recent samples → fewer recent coalescences → **Ne appears to fall**. The epidemic looks controlled because surveillance weakened.
- **Sampling intensifies somewhere.** Extra coalescences in that subpopulation → **apparent growth**, driven by a decision in an office.
- **Sampling changes composition.** Switch from severe hospitalised cases to community screening and you are sampling a different part of the transmission network.

### How the Bundibugyo team handled it — the part worth copying

They noticed reduced genome sampling after mid-July and did not simply caveat it. They ran an **iterative cutoff analysis**:

1. Build four datasets with progressively longer windows, ending **23 June, 3 July, 16 July** and **9 August**.
2. Apply **identical** curation and filtering to each.
3. Run a separate SkyGrid analysis on each.
4. Compare the key parameters across datasets.

**Result:** the clock rate converged to about 8.5 × 10⁻⁴ across the later datasets (the smallest gave 1.10 × 10⁻³), and the tMRCA was relatively stable from July onward. Their conclusion — that the most recent inferences reflect general epidemiological dynamics rather than an artefact of curation — is *earned* by that experiment rather than asserted.

✱ **This is the template. Steal it.** When a phylodynamic conclusion depends on the recent end of a dataset, re-run the analysis on nested truncations of your own data and show that the answer is stable. It is one extra figure, it costs compute rather than thought, and it is the difference between a robust finding and a sampling artefact with a credible interval.

⚠ **And note what the check can and cannot do.** Stability across nested windows shows the result is not an artefact of *where you cut the data*. It cannot rescue you if sampling was biased throughout in the same direction. The authors say so, flagging possible missing diversity in the first two months of 2026, around and preceding the inferred tMRCA — the period with the fewest samples and the most influence on the date.

## Section 6 · Genomic dynamics versus the epidemic curve

You will usually have both a case-based epidemic curve and a phylodynamic estimate. They measure related but different things and **they should be shown together.**

| | Case-based Rt | Phylodynamic Re / growth rate |
|---|---|---|
| Input | Reported cases by date | Time-scaled tree |
| Sees | Detected infections | Infections that left sampled descendants |
| Blind to | Undetected transmission | Lineages that died out unsampled |
| Biased by | Reporting delay, testing changes | Sequencing coverage changes |
| Timeliness | Fast | Slower (sequence + analyse) |

**When they agree**, that is real corroboration — two measurements with largely independent biases pointing the same way.

**When they disagree, that is the finding, not an error to be reconciled away.** The classic pattern: case counts flat while genomic diversity keeps rising, which usually means transmission continuing outside the surveillance system's field of view. That is precisely the situation in which the genomic result should change what the response does.

## Practice

Find a published skyline or SkyGrid plot and answer:

1. What are the axis units — Ne, Ne·τ, or something converted to infections? If converted, with what generation time?
2. What is the grid resolution, and is it justified against the pathogen's generation time?
3. What did sequencing effort do over the same period? Overlay sequences-per-week on the curve mentally. Does the trend track the effort?
4. Is there a nested-truncation or equivalent sensitivity analysis?
5. Does the case-based epidemic curve appear on the same figure? If not, why not?

## In one paragraph

Phylodynamics inverts the shape of a time-scaled tree for the population dynamics that produced it: coalescences bunch when the infected population is small and spread out when it is large, so node times measure effective population size through time. Ne is not prevalence — overdispersed transmission, generation time and population structure all separate them — so read the trend, not the axis. The tree prior is the epidemiological hypothesis: exponential growth gives a doubling time (21.0 days, 15.0–40.7, for Bundibugyo in Ituri), SkyGrid estimates Ne freely in weekly blocks, and birth–death models give Re directly at the price of specifying sampling. And the whole enterprise's central hazard is that a change in sampling is indistinguishable from a change in dynamics unless you test it — which is why nested-truncation sensitivity analysis, run identically at each cutoff, is the thing to copy from this study.
