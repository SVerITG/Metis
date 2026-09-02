# Lesson 9 — Putting time on the tree: molecular clocks, tMRCA, and what a date of origin actually is

> **Concept map**
> **Builds on** — Lesson 1 (the clock exists), Lesson 8 (the tree exists and is rooted).
> **Connects to** — Lesson 10, which reads population dynamics off a time-scaled tree; nothing in Lesson 10 works without this lesson.
> **Leads to** — Deep Dive 1's headline result: a tMRCA of 22 February 2026 for an outbreak declared on 15 May.

## Why this matters

A divergence tree tells you *how much* change separates sequences. A **time tree** tells you *when* — branch lengths in days and years, internal nodes with dates and credible intervals. Almost every epidemiologically useful statement needs the time tree:

- When did this outbreak start? (Before you noticed. Always before you noticed.)
- Is this cluster ongoing transmission or an old lineage resurfacing?
- Did this introduction precede or follow the border closure?
- How long was the cryptic period between spillover and detection?

The conversion is done by a **molecular clock** calibrated on sampling dates. This lesson is how that works, and — more important — what a **tMRCA** does and does not mean, because it is the single most over-interpreted number in the field.

## Learning objectives
By the end of this lesson you will be able to:

- **Test** whether a dataset has temporal signal, and refuse to date one that does not.
- **Choose** between strict and relaxed clock models with a reason.
- **State** precisely what a tMRCA is, and list the three things it is not.
- **Read** a Bayesian phylodynamic result: HPD intervals, ESS, burn-in, convergence.
- **Explain** what happens when temporal signal is weak and the prior takes over.

## Prerequisites
Lessons 0–8. Bayesian inference is described conceptually; no derivations.

---

## Section 1 · Temporal signal: the gate

You cannot date a tree unless later samples are, on average, further from the root than earlier ones. That is the empirical claim, and it is testable.

**Root-to-tip regression** (Lesson 1, revisited with the tree now in hand):

1. Take the rooted ML tree.
2. For each tip, measure genetic distance from the root (substitutions per site).
3. Plot against sampling date.
4. Fit a line. **Slope = evolutionary rate. Intercept on the x-axis ≈ the date of the root.**

The Bundibugyo analysis reports a slope of **7.9 × 10⁻⁴ substitutions per site per year** and describes good temporal signal. `TempEst` is the standard interactive tool; root-to-tip plots appear in the supplement of most well-done phylodynamic papers, and their absence is a warning.

**What a failed test looks like:** a flat or shapeless cloud, a near-zero or negative slope, a very low R². Causes include too short a sampling window relative to the clock rate, a slowly-evolving pathogen, wrong or missing dates, and contamination.

⚠ **If there is no temporal signal, you do not get to date anything.** You may still build a tree; you may not put years on it. Software will happily return a tMRCA anyway — it will be your prior, restated with a credible interval that looks like evidence. This is the most common way a confident wrong date enters the literature.

✱ Two structural cautions about the regression itself. **Tips are not independent** — they share ancestry, so ordinary least squares understates uncertainty. And **root-to-tip is a diagnostic, not an estimator**; use it to check that dating is possible and to sanity-check the model, then take the rate from the full Bayesian analysis. The Bundibugyo authors do exactly this: 7.9 × 10⁻⁴ from the regression, 8.5 × 10⁻⁴ from BEAST, and the agreement is the reassurance.

## Section 2 · Clock models

A clock model describes how the substitution rate varies across branches.

**Strict clock.** One rate everywhere. Simple, few parameters, most powerful *when true*. Reasonable for a single outbreak of one pathogen over a short window with one host — which is precisely the Bundibugyo situation, and a defensible default there.

**Relaxed clock — uncorrelated lognormal (UCLN).** Each branch draws its own rate from a shared lognormal distribution. Handles genuine rate variation between lineages: different hosts, chronic versus acute infections, adaptive bursts. The standard workhorse for multi-year, multi-host datasets. Costs statistical power.

**Random local clock.** Allows discrete rate shifts at a few points, inferring where they happen. Useful when you suspect a specific lineage changed rate.

**Which to use:** if lineages plausibly evolve at different rates — long timescales, host jumps, mixed acute and chronic infection — relax. If not, strict is more powerful and more honest. You can test: fit both and compare with marginal likelihoods, or check whether the relaxed clock's coefficient of variation excludes zero.

⚠ **A specific trap this course has already set up.** Host editing (Lesson 2) inflates the apparent rate. If ADAR-edited genomes are left in a filovirus dataset, or if APOBEC3 editing in mpox is modelled as ordinary substitution, the clock is estimating a mixture of two processes. This is exactly why the Bundibugyo team removed the 32 edited genomes *before* running the clock — not as tidying, but because the clock is the parameter that filter protects.

## Section 3 · tMRCA — the most over-interpreted number in genomic epidemiology

**tMRCA = time to the Most Recent Common Ancestor**: the date of the node from which all sampled sequences descend.

The Bundibugyo estimate, under the SkyGrid model: **22 February 2026, 95% HPDI 16 January to 24 March 2026.**

### What that means

The common ancestor of *the 525 genomes analysed* existed around late February 2026. Set against the outbreak timeline — index case identified in Bunia on 24 April, WHO alerted to an unknown severe illness in Mongbwalu on 5 May, outbreak declared 15 May — the genomic estimate places the common ancestor **roughly two months before the first recognised case**.

That is a substantive epidemiological finding, and it is the kind of thing only genomes provide. It says the virus was circulating, undetected, for weeks before surveillance saw it. It bounds how much unobserved transmission there was. And it is the standard finding in filovirus outbreaks, which is itself the point: **detection systematically lags transmission, and the genomic tMRCA is how you measure the lag.**

### The three things tMRCA is not

**1. It is not the date of the index case.** It is the ancestor of *your sample*. Real transmission almost always precedes it — earlier lineages that died out or were never sequenced leave no trace. **tMRCA is a lower bound on the age of the outbreak, not an estimate of it.**

**2. It is not the date of spillover.** For a zoonosis, the spillover is somewhere on the branch *leading to* the tMRCA node, which may be long. With one spillover you cannot date it from human sequences alone; with several independent spillovers, each seeds a separate lineage and the human tMRCA of each is a separate, later, lower bound.

**3. It is not a fixed point.** It moves as you add sequences. Sequence one more case from an early, divergent chain and the tMRCA moves earlier — sometimes a lot. **Any tMRCA is conditional on the sequences available when it was computed**, which is why the Bundibugyo authors ran their analysis on four nested time windows and reported that the tMRCA was "relatively stable" from July onward. That stability check is the difference between a number and a claim.

✱ **The right sentence in a report:** "The common ancestor of sequenced cases dates to late February 2026 (95% HPDI: mid-January to late March), indicating that transmission was established at least six to eight weeks before the outbreak was recognised." Note what it does: gives the interval, says *at least*, and says *sequenced cases*.

## Section 4 · The Bayesian machinery, in the amount of detail you need

Time trees at this level are estimated in a Bayesian framework — **`BEAST X` v10.6.0-beta2** in the flagship study. BEAST X is the 2025 generation of BEAST, with new clock and substitution models, discrete/continuous/mixed trait handling, and gradient-informed integration techniques that make large phylodynamic analyses tractable.

**What the software does:** samples from the joint posterior over trees, clock rates, demographic parameters and everything else, given the alignment, the sampling dates, the models and the priors. It does this with **MCMC** — a random walk through parameter space that spends time in each region in proportion to its posterior probability.

**The four numbers to check in any BEAST analysis:**

**Chain length.** The Bundibugyo runs: **100 million steps**. Long chains are needed because tree space is enormous.

**Sampling and burn-in.** **10,000 samples with 10% burn-in.** Burn-in discards the start of the chain, before it reached the region of high posterior probability. Ten percent is conventional; the right amount is however much it took, judged from the trace.

**ESS — effective sample size.** Consecutive MCMC samples are correlated, so 10,000 samples are not 10,000 independent draws. ESS estimates how many independent draws they are worth. **Convention: ESS > 200 for every parameter you report.** Below that, your credible intervals are not trustworthy. Checked in `Tracer`.

**Convergence.** Run at least two independent chains from different starting points and confirm they agree. A single converged-looking chain can be stuck in a local optimum.

⚠ **The reporting standard is low and you should raise it.** Many papers report a tMRCA with an HPD and never mention ESS or whether chains converged. Those are the numbers that say whether the interval means anything. Ask for them.

**HPD / HPDI — highest posterior density interval.** The narrowest interval containing 95% of the posterior. Not a confidence interval: it is a direct probability statement about the parameter *given the model and priors*. Which is the caveat — if the prior dominates, the HPD describes the prior.

## Section 5 · Priors, and when they take over

Every Bayesian analysis has priors. When data are informative, they barely matter. When data are weak, they are the answer.

Priors that matter most in practice:

- **The clock rate prior.** With weak temporal signal this drives the tMRCA directly. Often set from previous studies of the same pathogen — reasonable, and a route by which one paper's assumption becomes another paper's finding.
- **The tree prior / demographic model.** This is Lesson 10, and it is not a nuisance parameter: constant-size, exponential-growth and SkyGrid priors imply different tree shapes and therefore different node dates. **The Bundibugyo tMRCA differs between their exponential and SkyGrid analyses**, which is why the model is stated alongside the number.

**The test that settles it: run the analysis sampling from the prior only** (no data). If the tMRCA is much the same, the data are not informing it. This takes one extra run and it is the single most useful robustness check in phylodynamics.

## Section 6 · Reading a phylodynamic result properly

The Bundibugyo headline numbers, annotated:

| Quantity | Estimate | 95% HPDI | What to notice |
|---|---|---|---|
| Evolutionary rate | 8.5 × 10⁻⁴ subs/site/year | 7.3 – 9.8 × 10⁻⁴ | Tight; matches the 7.9 × 10⁻⁴ regression slope |
| tMRCA (SkyGrid) | 22 February 2026 | 16 Jan – 24 Mar 2026 | Over two months wide; **quote the interval, not the point** |
| Doubling time (exponential) | 21.0 days | 15.0 – 40.7 days | Strongly right-skewed — the upper tail is much longer |

Three habits to build:

1. **Quote intervals.** "tMRCA 22 February" is a five-week under-statement of the uncertainty.
2. **Notice asymmetry.** The doubling-time interval runs 15–40.7 days around a point of 21. Reporting "21 days" alone hides that slow growth is well within the data.
3. **Name the model with the number.** tMRCA under SkyGrid and tMRCA under exponential growth are different quantities from different assumptions.

## Practice

For a time-scaled tree in your field:

1. Find the root-to-tip regression. If absent, note it.
2. Find the clock model and ask whether the dataset justifies strict or relaxed.
3. Find the tMRCA and its HPD. Convert it into a sentence including "at least" and "of sequenced cases".
4. Find ESS and convergence. If absent, note it.
5. Compare the tMRCA with the date of first detection. **That gap is the surveillance system's blind period, and it is a system performance metric nobody routinely reports.**

## In one paragraph

Putting time on a tree requires temporal signal, which is a testable claim — check the root-to-tip regression, and refuse to date a dataset that fails it, because the software will hand you your prior dressed as a result. A clock model then converts substitutions into years, strict when one rate is plausible and relaxed when lineages differ. The output everyone quotes is the tMRCA, and it is three things it is often taken for: not the index case, not the spillover, and not fixed — it is a lower bound on the age of the outbreak, conditional on the sequences you happen to have, which is why the Bundibugyo team checked its stability across four nested datasets. Read the result as an interval with a model attached, and check ESS and convergence before believing the interval at all.
