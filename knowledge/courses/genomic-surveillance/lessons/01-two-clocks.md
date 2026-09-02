# Lesson 1 — Two clocks: why a pathogen genome carries epidemiological information at all

> **Concept map**
> **Builds on** — Lesson 0, question 1 and question 3.
> **Connects to** — Lesson 9 (the molecular clock made quantitative) and Lesson 12 (why the two clocks being *similar* is exactly what makes transmission inference hard).
> **Leads to** — Lesson 2, where the vocabulary for describing genetic change gets nailed down.

## Why this matters

There is one fact that makes this entire discipline possible, and it is not "sequencing got cheap". Cheap sequencing made genomic surveillance *practical*. What makes it *informative* is a coincidence of timescales:

> **A pathogen's genome changes at roughly the same speed that the pathogen spreads between people.**

If pathogens evolved a thousand times slower, every isolate in an outbreak would be identical and a sequence would tell you nothing you didn't already know from the case report. If they evolved a thousand times faster, every isolate would be unrelated noise and the tree would be meaningless. Neither of those is a hypothetical: **both are real pathogens**, and one of the practical skills in this lesson is recognising which regime you are in *before* you plan a study.

This is the concept Black and Dudas put at the centre of *The Applied Genomic Epidemiology Handbook*, and it deserves that position. Get this lesson and the rest of the course is mechanism. Miss it and you will run pipelines without knowing what they can possibly find.

## Learning objectives
By the end of this lesson you will be able to:

- **Explain** the overlapping-timescales principle and why it is the precondition for all genomic epidemiology.
- **Calculate** the expected number of substitutions per transmission event for a pathogen, given its evolutionary rate, genome length and serial interval.
- **Predict**, from that number alone, whether genomic data can resolve individual transmission events, only clusters, or only long-range lineages.
- **Distinguish** a measurably evolving population from one that is not, and say what changes about your study design.

## Prerequisites
Lesson 0. No molecular biology assumed. If "genome" means "the pathogen's full set of genetic instructions, written in DNA or RNA" you have enough.

---

## Section 1 · What a pathogen genome is, in the amount of detail you need

A genome is a string. For most purposes in this course, that is genuinely all you need.

- **The alphabet is four letters** — A, C, G, T (in DNA) or A, C, G, U (in RNA). Bioinformatics writes RNA genomes as DNA, so you will see T everywhere regardless.
- **The length varies over four orders of magnitude**, and this matters more than people expect:

| Pathogen | Genome | Length |
|---|---|---|
| Hepatitis B | DNA | ~3,200 bases |
| SARS-CoV-2 | RNA (+ssRNA) | ~29,900 bases |
| Ebola / Bundibugyo virus | RNA (−ssRNA) | ~19,000 bases |
| Influenza A | RNA, **8 separate segments** | ~13,500 total |
| Mpox virus | DNA (double-stranded) | ~197,000 bases |
| *Mycobacterium tuberculosis* | DNA (bacterial chromosome) | ~4.4 million bases |
| *Plasmodium falciparum* | DNA (eukaryote, 14 chromosomes) | ~23 million bases |
| *Trypanosoma brucei* | DNA (eukaryote + kinetoplast) | ~26 million bases + minicircles |

Two consequences you will use constantly:

**Genome length sets your sequencing strategy.** A 19 kb virus can be covered by ~100 overlapping PCR amplicons on a laptop-sized sequencer in a field lab. A 4.4 Mb bacterial chromosome cannot — you sequence the whole thing from extracted DNA and assemble it. A 23 Mb parasite genome inside a human blood sample is >99% host DNA, so you need selective enrichment or you are paying to sequence the patient. This is Lesson 3.

**Genome length also sets how much signal a single case gives you.** Evolutionary rates are quoted *per site per year*. A rate of 10⁻³ on a 30 kb virus is 30 changes a year. The same rate on a 3 kb virus is 3. Same rate, ten times less resolution.

⚠ **Influenza's eight segments are not a footnote.** Segments can be swapped wholesale between co-infecting viruses — **reassortment** — which means influenza does not have *a* phylogeny, it has eight, and they disagree. The H5N1 genotype names you will meet in Deep Dive 3 (B3.13, D1.1) are precisely names for *combinations of segment lineages*. Any pathogen that reassorts or recombines breaks the single-tree assumption underlying most of Lessons 7–11, and you must know whether yours does.

## Section 2 · Why genomes change: mutation

Every time a pathogen replicates, it copies its genome, and copying is imperfect. The error rate depends overwhelmingly on one thing: **whether the copying enzyme proofreads.**

- **RNA viruses** mostly use an RNA-dependent RNA polymerase with **no proofreading**. Error rates around 10⁻⁴ to 10⁻⁶ per site per copy. This is why RNA viruses are the workhorses of genomic epidemiology.
- **Coronaviruses are the exception among RNA viruses** — they carry a proofreading exonuclease (nsp14), which is why a 30 kb RNA genome is even possible and why SARS-CoV-2 evolves an order of magnitude slower per site than influenza.
- **DNA viruses** use higher-fidelity polymerases. Orthopoxviruses like mpox have a baseline substitution rate around 10⁻⁶ per site per year — far too slow for outbreak resolution. *Except* that in sustained human transmission, host **APOBEC3** enzymes edit the viral genome and drive an apparent rate two orders of magnitude higher. Deep Dive 2 is entirely about this, because it converts mpox from "unusable for outbreak epidemiology" to "usable, with a large asterisk".
- **Bacteria** have proofreading plus mismatch repair. *M. tuberculosis* accumulates roughly **0.3–0.5 SNPs per genome per year**. That is the slow regime, and it is why TB cluster definitions are stated in whole SNPs (5, 12) rather than as tree distances.
- **Eukaryotic parasites** are slower still per site, and additionally recombine sexually — *P. falciparum* recombines in the mosquito, which shreds long-range linkage and makes tree-based reasoning much weaker. Malaria genomic surveillance is therefore mostly a **marker** discipline (Q4), not a **tree** discipline (Q1–Q3). Deep Dive 4.

✱ Notice what just happened. In one section, the biology of a polymerase determined which of the four questions from Lesson 0 you are allowed to ask. That is the general pattern: **the pathogen's molecular biology decides which epidemiological questions its genome can answer.** Never choose a method before you have checked the rate.

## Section 3 · The central calculation

Here is the calculation to do at the start of every genomic epidemiology study. It takes thirty seconds and it will save you months.

> **Substitutions per transmission event =**
> **(evolutionary rate per site per year) × (genome length) × (serial interval in years)**

Work it for the flagship study of this course, the 2026 Bundibugyo virus outbreak in Ituri. The authors estimated a rate of **8.5 × 10⁻⁴ substitutions per site per year** on an alignment trimmed to **18,900 bases**:

```
8.5e-4  ×  18,900  =  16.1 substitutions per genome per year
365 / 16.1         =  one substitution every ~23 days
```

Ebola-family serial intervals run around two weeks. So:

```
16.1 subs/year × (15/365) years  ≈  0.66 substitutions per transmission event
```

**Roughly two thirds of a mutation per transmission.** That is close to the ideal. It means that over a chain of a few transmissions you accumulate detectable change, so clusters separate — but individual links often share identical genomes, so you cannot resolve who-infected-whom. Which is exactly what the Bundibugyo analysis reports and exactly what it does not claim.

Run the same arithmetic across the field and a table falls out that predicts, in advance, what any study can hope to find:

| Pathogen | ≈ subs / genome / year | Serial interval | ≈ subs per transmission | What genomes can resolve |
|---|---|---|---|---|
| Influenza A (HA) | ~5–10 | ~3 days | ~0.05 | Lineages and antigenic evolution; **not** individual links |
| SARS-CoV-2 | ~24 (≈2/month) | ~5 days | ~0.3 | Clusters and introductions; links only with extra evidence |
| Bundibugyo / Ebola | ~16 | ~15 days | ~0.7 | Clusters, chains-of-a-few, introductions, growth rate |
| Measles | ~10 | ~14 days | ~0.4 | Importation vs endemic transmission; genotype tracking |
| HIV | high, but chronic | years | many | Clusters and long-term transmission networks |
| *M. tuberculosis* | ~0.3–0.5 | ~1.5 years | ~0.5–0.75 | Clusters over years; recent vs remote transmission |
| Mpox (human chains, APOBEC3-driven) | ~10 | ~2 weeks | ~0.4 | Chains and introductions — *only because of APOBEC3* |
| Mpox (zoonotic, no APOBEC3) | ~0.2 | — | ~0 | Essentially nothing at outbreak scale |

⚠ **These are teaching figures, order-of-magnitude, for building intuition.** Real rates vary by gene, by lineage, by whether you are looking within or between hosts, and by how they were estimated. Do not put this table in a manuscript. Do use it to decide, in a meeting, whether the study someone is proposing can possibly work.

### Reading the table

- **≈0.05 subs/transmission (influenza):** the genome is nearly static across an outbreak. Genomics answers Q2 and Q4 well and Q1 barely at all.
- **≈0.3–0.7 (most epidemic viruses):** the productive zone. Clusters resolve, chains partially resolve, growth rates are estimable. Nearly everything in this course lives here.
- **≫1:** you can start distinguishing individual transmissions — but you are usually now in a chronic infection where within-host diversity (Lesson 2) becomes the dominant complication rather than a nuisance.

## Section 4 · "Measurably evolving populations", and how to check

A population is **measurably evolving** if genomes sampled later are, on average, detectably further from the root than genomes sampled earlier. That sounds like a definition; it is actually an empirical test you must run, and it is the gate on every time-based analysis in Lessons 9–11.

The test is the **root-to-tip regression**: build a tree, measure each tip's genetic distance from the root, plot it against that tip's sampling date, fit a line. If the slope is positive and the fit is decent, you have temporal signal and the slope estimates the evolutionary rate. If the cloud is flat or shapeless, **you do not get to date anything**, and any tMRCA you compute is your prior talking back to you.

The Bundibugyo authors did exactly this and reported a regression slope of **7.9 × 10⁻⁴** — close to the 8.5 × 10⁻⁴ their full Bayesian model later produced. That agreement is the point of doing both: the quick regression is a sanity check on the expensive model.

✱ Notice this is a **falsifiable precondition**, not a formality. Over a 100-day window on a virus that changes once every 23 days, having temporal signal at all is not guaranteed. The authors had to show it, and they showed it before doing anything else.

## Section 5 · The second clock, and the trouble it causes

So far, one clock: evolution. The second clock is **transmission** — the rate at which the pathogen moves between hosts.

Genomic epidemiology works because the two clocks tick at comparable speeds. But that comparability is also the source of the field's hardest limitation, and it is worth stating now so that Lesson 12 is not a surprise:

> **Because roughly one mutation happens per transmission — sometimes zero, sometimes two — the genetic distance between two isolates is a noisy, low-resolution measurement of the number of transmissions between them.**

Zero differences does not mean "direct transmission". It means "few enough transmissions that no mutation happened to land", and with 0.66 expected substitutions per link, **a chain of three people has a substantial chance of showing no genetic change at all.** Conversely, two differences does not mean "three links" — mutation is a stochastic process and occasionally fires twice in one host.

This is the deep reason for the asymmetry stated in Lesson 0: **genomics rules links out much better than it rules them in.** Large distance is strong evidence against a direct link, because that would require an improbable burst of mutation. Small distance is weak evidence for one, because it is consistent with many histories.

## Section 6 · Where the two clocks come apart

Three situations break the tidy picture, and all three appear in this course's deep dives:

1. **Chronic or persistent infection.** Ebola survivors can harbour virus for months; the virus keeps evolving inside them, so a flare-up months later looks like a *long branch* rather than a recent link. Diagnosing this correctly changed the response in several West African outbreak tails.
2. **Host-driven editing.** APOBEC3 (mpox) and ADAR (filoviruses, among others) impose mutations that are **not** the pathogen's own replication error. They can inflate the apparent clock — useful in mpox, an artefact to be removed in the Bundibugyo analysis. Lesson 2 and Deep Dive 1.
3. **Animal reservoirs.** Time spent in a non-human host may evolve at a different rate and is entirely unsampled. A long branch back to an animal reservoir is uninformative about *when* in that interval the spillover happened. This is exactly the situation for H5N1 in cattle (Deep Dive 3) and for *T. b. gambiense* in the animal-reservoir question that hangs over HAT elimination.

## Practice

Do this before Lesson 2. It takes fifteen minutes and it is the single most transferable skill in the course.

For a pathogen you actually work on:

1. Find a published evolutionary rate (subs/site/year) and note how it was estimated.
2. Multiply by genome length → substitutions per genome per year.
3. Multiply by the serial interval in years → substitutions per transmission.
4. Write one sentence: *"With ≈ X substitutions per transmission, sequencing this pathogen can distinguish ______ but cannot distinguish ______."*

Keep that sentence. It is the abstract of every genomic study you will ever design on that pathogen.

## In one paragraph

Genomic epidemiology exists because pathogen genomes change at roughly the speed pathogens spread. One multiplication — rate × genome length × serial interval — tells you how many substitutions separate two people in a transmission chain, and that single number predicts whether genomes can resolve individual links, clusters, or only broad lineages. The same number explains the field's central asymmetry: with under one mutation per transmission, identical genomes are consistent with many histories, so sequencing dismisses links far better than it confirms them. Before any of it applies, the population must be *measurably evolving*, and that is a testable claim you check with a root-to-tip regression, not an assumption you make.
