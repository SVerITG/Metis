# Deep Dive 1 — Bundibugyo virus in Ituri, DRC, 2026: a 100-day window, line by line

> **The source.** Wawina-Bokalanga T, Mbala-Kingebeni P, et al. *Phylodynamics and evolution of the 2026 Bundibugyo virus circulating in the Democratic Republic of the Congo: insights from a 100-day window of genomic sequencing.* virological.org, post 1046 (2026). INRB Kinshasa with the Universities of Edinburgh, Oxford and Birmingham, the your institution Antwerp, WHO, Africa CDC and US CDC.
>
> **Read it alongside this page.** The aim of this deep dive is that by the end, every sentence in that post is transparent — including the ones the authors did not explain because they assumed their readers already knew.

---

## 1 · The question someone actually asked

On **5 May 2026**, WHO received an alert about an unknown illness with high mortality in Mongbwalu Health Zone, Ituri Province, DRC — including four health workers who died within four days. An index case had been identified in Bunia on **24 April**. On **15 May 2026**, the DRC Ministry of Public Health declared the country's **17th Ebola disease outbreak**.

The pathogen was **Bundibugyo virus (BDBV)** — and that identification is not a detail. BDBV is a **distinct species** within *Orthoebolavirus*, not a variant of Zaire ebolavirus. The licensed vaccine (ERVEBO) and the licensed monoclonal therapeutics target Zaire; **there is no licensed vaccine or specific therapeutic for Bundibugyo virus.** Previous BDBV outbreaks — Uganda 2007, DRC 2012 — were small, with case fatality between roughly 30% and 50%. Candidate BDBV-specific vaccine trials only began in July 2026, during this outbreak.

By **1 August 2026** the outbreak had reached **3,748 cases and 1,657 deaths** across 21 health zones in Ituri and one in Nord-Kivu — an order of magnitude larger than any previous Bundibugyo event, and among the largest filovirus outbreaks ever recorded.

The questions the response needed answering were the four from Lesson 0, in a specific order:

1. **When did this start, and how much did we miss?** (Q3 — the detection lag.)
2. **How fast is it growing?** (Q3 — is the response keeping pace?)
3. **Where did it start?** (Q2 — where does the response concentrate?)
4. **Has the virus changed in a way that matters?** (Q4 — do the diagnostics still work, is a lineage sweeping, is there an escape mutation?)

Question 4 carries extra weight here, because with no licensed countermeasure the response depends entirely on diagnostics, isolation and contact tracing — every one of which is vulnerable to viral change.

## 2 · Why it looked tractable

Three things made this a genomics problem rather than an aspiration.

**The clock is in the right range.** Lesson 1's arithmetic: 8.5 × 10⁻⁴ substitutions per site per year on ~18,900 bases is ~16 substitutions per genome per year, one every ~23 days, about **0.66 substitutions per transmission** at a two-week serial interval. Clusters resolve; growth rates are estimable; individual links are not resolvable. That is the productive zone.

**The sequencing was in-country and at scale.** INRB in Kinshasa, with the Birmingham sequencing team whose ARTIC-lineage tooling was originally built for Ebola virus in West Africa, produced **626 genomes across roughly 100 days**. For context, this is a sequencing density most high-income countries have never achieved in an outbreak.

**The analysis happened during the outbreak, in the open.** Posted on virological.org as a work in progress — the same venue and the same practice that made real-time genomic epidemiology possible for Zika, Ebola and SARS-CoV-2.

## 3 · The data, and what it does not represent

**What was collected.** EDTA whole blood from living patients; **oral fluid from deceased patients**. That second stream is why people who died in the community — the group most likely to sit in undetected chains — appear in the genomic record at all (Lesson 3).

**Diagnosis.** RADIONE point-of-care system and RealStar Filovirus Screen RT-PCR (v1.0 or 2.0).

**Selection for sequencing.** **All PCR-positive samples with Ct < 31.** Lesson 3 in one line: this is correct laboratory practice and it is also a sampling frame. It selects on viral load, which tracks time since onset, severity and speed of presentation. The sequenced set is enriched for people who presented early and sick.

**Geography.** 625 genomes from Ituri across 21 health zones, 1 from Nord-Kivu. Concentrated in **Bunia, Rwampara and Mongbwalu**.

**The cascade** (Lesson 13's figure, with real numbers):

```
   3,748 cases reported to 1 August
        ↓  sample taken, transported, PCR-positive, Ct < 31
     626 genomes generated
        ↓  −32 with ADAR editing signatures
     594
        ↓  −69 phylogenetic outliers (iterative, ±2 SD)
     525 genomes analysed
```

**525 of 3,748 is about 14% of reported cases** — and the reported cases are themselves a fraction of infections. Every conclusion below is conditional on that, and the authors say so.

## 4 · The method, decoded

This is the section this whole course was built to make readable. Each item below is a phrase from the post, followed by what it means and which lesson covers it.

### "amplicon-nf v.2 from ARTIC Network"
A Nextflow pipeline for ARTIC-style tiling amplicon schemes: reads in, consensus genomes out, with QC. Nextflow means containerised, version-pinned, portable across compute. Its ancestor is `artic fieldbioinformatics`, written for Ebola virus sequencing in West Africa a decade ago. **Lesson 5.**

### "MAFFT alignment; trimmed to 18,900 bp"
Multiple sequence alignment — the homology hypothesis underlying everything (Lesson 7). The trim removes end-of-genome sequencing artefacts, present in at least one genome (26FHV054). **The trade: lose a few hundred positions from every sequence to remove noise contaminating all of them.** Correct when artefacts concentrate at the edges, which for amplicon-derived viral genomes they reliably do. **Lessons 5 and 7.**

### "32 genomes with excess T→C mutations in short spans, excluded"
**ADAR editing.** Host adenosine deaminase converts A to I in double-stranded RNA; I reads as G; on the reverse-complement strand conventionally used for filovirus genomes this appears as **T→C**. The tell is not the base change but its **clustering in short consecutive spans** — ADAR is processive.

Why exclude: these are not the virus's evolutionary history. Left in they inflate the clock, create spurious long branches, distort tree shape and therefore the coalescent growth estimates, and appear homoplastically across unrelated tips. **The clock is the parameter this filter protects.** **Lesson 2.**

### "IQ-TREE 3 with ModelFinder (GTR+F+R3)"
Maximum likelihood phylogeny. **GTR** — all six reversible base-change types free. **+F** — base frequencies taken from the alignment rather than estimated (filovirus genomes are AT-rich). **+R3** — FreeRate site-rate heterogeneity with three freely-estimated rate classes, making no assumption about the shape of the rate distribution, unlike the more common `+G` gamma model. `ModelFinder` selected it by information criterion; the model was chosen by procedure, not preference. **Lesson 8.**

### "Small branches collapsed to zero; tree rooted to minimise residuals"
Two decisions, both correct and both worth naming.

**Collapsing near-zero branches into polytomies** is an honest admission: at 0.66 substitutions per transmission, many internal branches rest on no evidence at all. A fully bifurcating tree drawn from zero-length branches is a false claim of precision. **Lesson 7.**

**Residual-minimising rooting** is clock-based rooting: choose the root position that makes the root-to-tip-versus-date regression fit best. Appropriate for a densely sampled, time-stamped outbreak with no suitable outgroup — an earlier BDBV outbreak genome is decades divergent and would distort branch lengths. **Lesson 8.**

### "Root-to-tip outlier removal, iteratively, ±2 SD"
Plot each tip's genetic distance from the root against its sampling date; fit a line; the slope (**7.9 × 10⁻⁴**) estimates the evolutionary rate. Remove tips whose residuals exceed ±2 SD, re-root to minimise residuals, repeat. **Cumulative removal: 69 genomes.**

✱ **The sophistication worth stealing.** The authors note that a bout of ADAR editing on an internal branch affects **multiple tips**, so outliers are not independent of each other. That is exactly why the removal is iterative rather than one-pass. Treating non-independent outliers as independent is a standard mistake and they avoided it. **Lessons 2 and 9.**

### "BEAST X v10.6.0-beta2 … 100 million steps; 10,000 samples; 10% burn-in"
Bayesian phylodynamics. BEAST X is the 2025 generation of BEAST, with new clock and substitution models and gradient-informed integration that makes analyses of this size tractable. 100 million MCMC steps because tree space is enormous; 10,000 recorded samples; the first 10% discarded as burn-in.

⚠ **What the post does not state, and what you should ask for: ESS values and chain convergence.** Without ESS > 200 per reported parameter, the credible intervals are not trustworthy. This is a work-in-progress post rather than a paper, so the omission is understandable — but it is the first thing to look for in the published version. **Lesson 9.**

### "Two coalescent priors: exponential growth and SkyGrid (31 one-week transition points, 32-week cutoff)"
The **tree prior is the epidemiological hypothesis**, not a nuisance parameter.

**Exponential growth** — two parameters, powerful when growth really is exponential, and it yields the doubling time.

**SkyGrid** — non-parametric. Look back 32 weeks from the most recent sample; split that into weekly blocks at 31 transition points; estimate effective population size freely in each, with a smoothing prior linking adjacent blocks. **Weekly resolution against a ~2-week serial interval** is a deliberate match: fine enough to see real change, coarse enough that each interval contains coalescent events. **Lesson 10.**

**Running both is the point.** They make different assumptions and therefore give different tMRCAs. Agreement on the substantive conclusions across both is the evidence.

### "Pathoplexus, BDBV_DRC_20260820 (PP_SS_3400.1), restricted"
The open-source-platform database launched in 2024 as a middle path between fully open INSDC and access-controlled GISAID. Restricted licence, contact required before use in advance of publication, INRB scientists named as contacts. **The analysis is public in real time; the sequences stay under the control of the institution that generated them until they publish.** **Lesson 14.**

### "PearTree"
The interactive tree viewer the post links to ("Show in PearTree", "Open in PearTree"), taking a tree file and a JSON configuration. **Lesson 7.**

## 5 · What they found

### The clock
**8.5 × 10⁻⁴ substitutions per site per year (95% HPDI 7.3–9.8 × 10⁻⁴)**, against a root-to-tip regression slope of 7.9 × 10⁻⁴. The agreement between a quick heuristic and a full Bayesian model is genuine reassurance (Lesson 9).

### The origin date
**tMRCA 22 February 2026 (95% HPDI 16 January – 24 March)** under SkyGrid.

Set against the timeline — index case 24 April, alert 5 May, declaration 15 May — **the common ancestor of sequenced cases predates the first recognised case by roughly two months.**

Read it correctly (Lesson 9): this is a **lower bound** on the age of the outbreak, conditional on the sequences available. Real transmission almost certainly began earlier; earlier lineages that died out or were never sampled leave no trace. And it is **not** the spillover date — the spillover sits somewhere on the branch leading to that node.

**The finding stated properly:** transmission was established at least six to eight weeks before the outbreak was recognised. That gap is a surveillance-system performance metric, and almost nobody reports it.

### The growth
**Doubling time 21.0 days (95% HPDI 15.0–40.7)** under exponential growth. Note the skew: the interval runs to nearly six weeks. Quoting "21 days" alone hides that much slower growth is well within the data.

The SkyGrid curve: **a relatively slow start, increased growth from March to June, then an apparent decline.**

### The geography
Genomes from **Mongbwalu** showed **substantial diversity** and emerged from **relatively deep parts of the tree**, suggesting Mongbwalu as a possible starting point.

✱ **Look at the hedging, because it is doing real work.** "Suggesting", "could have been". The alternative is that Mongbwalu was sampled early and heavily. In a dataset where sequencing density varies across 21 health zones, deep-and-diverse is exactly what dense-and-early sampling also produces (Lesson 11). The authors state the observation and the inference separately, and hedge the inference. That is the model for how to write a phylogeographic claim.

### The virus itself — the negative result
> "Genomic and phylogenetic diversity was maintained and increasing during the sampling period, without any indication of fitness-altering mutations or a particular lineage starting to dominate."

**This is arguably the most operationally useful sentence in the post.** A lineage sweeping to dominance would signal possible fitness change — greater transmissibility, immune escape, or diagnostic escape. In an outbreak with no licensed vaccine or therapeutic, where the response rests entirely on diagnostics, isolation and contact tracing, "the virus has not changed in a way that threatens any of those" is what allows the response to keep doing what it is doing.

**Reporting that nothing changed is a result, and it costs as much work as a positive finding.**

## 6 · How it was evaluated

This is where the analysis earns trust, and it is the part to copy.

The authors noticed **reduced genome sampling after mid-July**, and that the apparent decline in effective population size at the end of the series is exactly what weakened sampling produces (Lesson 10). Rather than caveat it, they tested it.

**The iterative cutoff analysis:**

1. Four datasets with progressively longer windows: through **23 June, 3 July, 16 July, 9 August**.
2. **Identical** curation and filtering applied to each.
3. A separate SkyGrid analysis on each.
4. Compare clock rate and tMRCA across them.

**Result:** clock rates converged at ~8.5 × 10⁻⁴ across the later datasets (the smallest gave 1.10 × 10⁻³ — the expected instability of a short window), and the tMRCA was relatively stable from July onward. Their conclusion that the most recent inferences reflect general epidemiological dynamics is *earned* by an experiment, not asserted.

**Stated limitations, in the authors' own framing:**

- Preliminary, work in progress.
- Reduced sampling after mid-July as a potential bias.
- Possible missing diversity, particularly in the first two months of 2026 — around and preceding the inferred tMRCA. **That is the period with the fewest samples and the most influence on the date**, and naming it is the sign of authors who know where their result is weakest.

⚠ **What the check can and cannot do.** Stability across nested truncations shows the result is not an artefact of where you cut the data. It cannot rescue you from bias that ran in the same direction throughout. The authors do not claim otherwise.

## 7 · What happened next

At the time of writing (late August 2026) the outbreak is ongoing. The first Bundibugyo-specific candidate vaccine trials began in the UK on 24 July and in Canada shortly after — the first ever for this species. The genomic data supported the response by establishing the detection lag, the growth rate, a candidate origin, and — critically — the absence of viral change that would have invalidated the diagnostics in use.

## 8 · What it is actually worth

**Honest accounting.**

**Strong:**

- 626 genomes over 100 days from an active filovirus outbreak in a conflict-affected province is an extraordinary operational achievement, and it was done in-country.
- The curation is mechanistically motivated (ADAR) before it is statistical (outliers), which is the right order.
- The nested-truncation sensitivity analysis is better practice than most published phylodynamics.
- The negative finding on lineage dominance is reported as a finding.
- The analysis was public during the outbreak, when it could be used.

**Weaker, or unstated:**

- No ESS or convergence diagnostics reported (understandable in a work-in-progress post; required in the paper).
- No cascade from cases to analysed genomes, so the compound selection from the Ct gate and quality filters is not quantified.
- No sequences-per-case by health zone, which is what would let a reader judge the Mongbwalu inference.
- Phylogeographic inference is described qualitatively rather than through a formal discrete-trait or structured-coalescent model — appropriate caution for a preliminary post, and the thing to look for in the paper.

**What it demonstrates about the field:** an African national institute leading the genomic analysis of its own outbreak, in real time, with international collaborators as collaborators, publishing the analysis openly while retaining control of the sequences. That is what the Africa PGI's decade of capacity building was for, and this is what it looks like when it works.

## 9 · Transferable lessons

1. **Filter mechanistically before you filter statistically.** ADAR first, outliers second. A mechanistic filter removes sequences for a reason; the blunt statistical filter then has less to do.
2. **Iterate outlier removal**, because artefacts on internal branches affect multiple tips and outliers are therefore not independent.
3. **Run two demographic models**, not one. Where they agree, you have a result. Where they differ, you have learned that the conclusion depends on the assumption.
4. **Test recent-end conclusions with nested truncations**, applying identical curation at each cutoff. One extra figure; it is the difference between a finding and a sampling artefact with a credible interval.
5. **Match grid resolution to generation time.** Weekly blocks for a two-week serial interval.
6. **Hedge phylogeographic claims in proportion to sampling variation**, and state the observation separately from the inference.
7. **Report the negative finding.** "No lineage dominance, no fitness-altering mutations" is what tells a response its assumptions still hold.
8. **The tMRCA-to-detection gap is a metric.** Roughly two months here. Report it; it is one of the few direct measurements of how blind a surveillance system was.
9. **Publish at response cadence.** Preliminary and public during the outbreak beats polished and published a year later — provided the uncertainty is visible, which here it is.

## 10 · Explain it in 60 seconds

> During the 2026 Bundibugyo virus outbreak in Ituri, DRC, Congolese scientists at INRB with international partners sequenced 626 virus genomes over about 100 days and analysed them while the outbreak was still going.
>
> Because the virus picks up roughly one mutation every three weeks, the genomes act like a clock. Winding it back, the common ancestor of all the sequenced cases dates to around **22 February 2026** — about two months before the first case was recognised. The virus was spreading, unseen, for weeks before anyone knew.
>
> The genomes also show how fast it grew: a **doubling time of about 21 days**, with a slow start, acceleration from March to June, then an apparent slowdown — which the team tested carefully, because sequencing had dropped off, and less sequencing looks exactly like a slowing epidemic.
>
> And the most reassuring finding was a negative one: **the virus had not changed in any way that mattered.** No lineage taking over, no mutations suggesting it had become more transmissible or able to evade the tests. With no licensed vaccine or treatment for this species, that is what told the response its diagnostics and its strategy still worked.

## 11 · Read more

- [The post itself](https://virological.org/t/phylodynamics-and-evolution-of-the-2026-bundibugyo-virus-circulating-in-the-democratic-republic-of-the-congo-insights-from-a-100-day-window-of-genomic-sequencing/1046) on virological.org — with the PearTree links.
- WHO Disease Outbreak News **2026-DON602**, and the AFRO outbreak page for case counts.
- *Bundibugyo virus disease outbreak in Ituri, Democratic Republic of the Congo*, The Lancet (2026).
- *Bundibugyo Virus Disease in 2026 — Clinical and Public Health Responses*, NEJM (NEJMra2607216).
- ARTIC Network `amplicon-nf` — [github.com/artic-network/amplicon-nf](https://github.com/artic-network/amplicon-nf) and [artic.network/resources/amplicon-nf](https://artic.network/resources/amplicon-nf)
- BEAST X — Baele, Ji et al., *Nature Methods* (2025).
- IQ-TREE 3 — *Molecular Biology and Evolution* 43(5):msag117 (2026).
- Pathoplexus — [pathoplexus.org](https://pathoplexus.org)

⚠ Every reference above is a lead. The virological post was read in full during authoring; the others were identified from search results and their specific claims have not each been verified against the source. See `sources/source-ledger.md`.
