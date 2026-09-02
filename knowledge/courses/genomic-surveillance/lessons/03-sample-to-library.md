# Lesson 3 — Sample to library: the wet-lab chain, and the decisions inside it that are epidemiological

> **Concept map**
> **Builds on** — Lesson 1 (genome length sets the strategy) and Lesson 2 (artefacts start here, not in the software).
> **Connects to** — Lesson 4 (the sequencer itself), Lesson 5 (every artefact created here has to be dealt with there), Lesson 13 (the Ct threshold is a sampling decision in disguise).
> **Leads to** — Deep Dive 1, whose selection rule was "all PCR-positive samples with Ct < 31".

## Why this matters

Epidemiologists are usually told the wet lab is somebody else's problem. It is not, for one reason: **several of the decisions made at the bench are epidemiological decisions wearing laboratory clothes**, and if you do not recognise them as such, nobody in the room will.

The clearest example is the one at the heart of this course's flagship study. INRB sequenced "all PCR-positive samples with Ct values < 31". That is presented as a laboratory quality criterion — below Ct 31 there is enough material to get a genome. But look at what it actually does: it **selects cases by viral load**, and viral load correlates with days since onset, with severity, with sample type, and with how quickly a patient reached care. The sequenced set is therefore not a random sample of cases. It is enriched for people who presented early and sick.

That is a sampling frame. It belongs in the limitations paragraph, and it is invisible to anyone who thinks of Ct 31 as a lab detail.

## Learning objectives
By the end of this lesson you will be able to:

- **Trace** a clinical sample from collection through to a sequencing-ready library, naming each step and what can go wrong in it.
- **Explain** what a Ct value is, why it gates sequencing, and what selection it introduces.
- **Choose** between amplicon, capture and metagenomic enrichment for a given pathogen, sample type and budget — and defend the choice.
- **Describe** how a tiling amplicon scheme works, and predict the two ways it fails when the target evolves.
- **Identify** the controls that must be on every run, and what each one rules out.

## Prerequisites
Lessons 0–2. No bench experience required. If you have never pipetted anything, you can still understand every decision in this lesson — that is the point of it.

---

## Section 1 · The specimen

Sequencing begins with a decision about what to collect, and that decision constrains everything downstream.

| Specimen | Typical use | Note for the epidemiologist |
|---|---|---|
| **Whole blood (EDTA)** | Viraemic infections: filoviruses, arboviruses, malaria | The Bundibugyo study's specimen for living patients |
| **Oral fluid / oral swab** | Post-mortem sampling; measles; polio | The Bundibugyo study's specimen for **deceased** patients — safer, faster, needs no phlebotomy on a corpse, and is the reason the dataset includes people who died before reaching care |
| **Nasopharyngeal swab** | Respiratory viruses | Quality varies enormously with who took it |
| **Sputum / culture isolate** | TB, most bacteria | Culture gives abundant clean DNA — and takes weeks, and selects for what grows |
| **Dried blood spot / FTA card** | Field settings, no cold chain | Lower yield; excellent for logistics; degraded nucleic acid |
| **Wastewater** | Population-level, no clinical contact | A mixture of many infections at once — Deep Dive 5 |
| **Vector / animal** | One Health questions | The Gabon *T. b. gambiense* wildlife work; H5N1 in cattle milk |

✱ **Specimen choice is not neutral with respect to who ends up in your dataset.** The Bundibugyo team's use of oral fluid from the deceased is a small methodological note with a large epidemiological effect: without it, everyone who died in the community — the group most likely to be part of undetected chains — would be missing from the genomic record. Look for this pattern. It recurs.

**Biosafety is upstream of everything.** Bundibugyo virus is a risk group 4 pathogen. Samples are collected into inactivation buffer (guanidinium-based) which destroys the virus while preserving RNA, so that the material leaving the isolation unit is no longer infectious. Every choice about buffer and transport affects nucleic acid quality — degraded RNA gives patchy coverage, which gives Ns in the consensus, which propagates all the way to the tree.

## Section 2 · Extraction, and the Ct value

**Extraction** separates nucleic acid from everything else — proteins, membranes, buffer, blood. Column-based, magnetic-bead or automated. The output is a small volume of RNA or DNA in water.

**RNA is fragile.** RNases are everywhere, including on skin. This is why RNA-virus programmes obsess about cold chain and inactivation buffers in ways that DNA programmes do not, and why field sequencing of RNA viruses is genuinely harder than of bacteria.

**Reverse transcription** converts RNA into complementary DNA (cDNA), because essentially all downstream chemistry works on DNA.

### The Ct value, properly understood

In quantitative PCR, the target is amplified in cycles, roughly doubling each cycle, and fluorescence is measured. The **cycle threshold (Ct)** is the cycle number at which the signal crosses a detection threshold.

- **Low Ct = lots of starting material.** Ct 18 is a very high load.
- **High Ct = little starting material.** Ct 35 is near the limit of detection.
- Because amplification is exponential, **each ~3.3 cycles is a ten-fold difference in input.** Ct 21 versus Ct 31 is roughly a thousand-fold difference in template.

Ct is therefore a rough proxy for pathogen load, and it predicts sequencing success better than almost anything else. Below some threshold there simply is not enough template: you get partial genomes, dropout, and consensus sequences full of Ns.

⚠ **Ct is not comparable across assays, platforms, or laboratories.** It depends on the assay, the extraction volume, the machine and the threshold setting. Ct 31 on the RealStar Filovirus Screen RT-PCR is not Ct 31 on something else. Treat it as an internally consistent ordering within one lab's workflow, never as an absolute quantity — and be suspicious of any analysis that pools Ct across sites without normalisation.

**The consequences of the Ct gate, spelled out:**

1. **Selection on time since onset.** Load rises then falls; sample too late and Ct is high. Late presenters drop out of the genomic dataset.
2. **Selection on severity.** In many infections, higher load tracks worse disease. Milder cases are under-represented.
3. **Selection on care-seeking and access.** Whoever reaches a facility quickly is more likely to be sequenced. In an outbreak spread across 21 health zones, this varies geographically — and geography is exactly what phylogeography (Lesson 11) is trying to estimate.

This is not a criticism of the Bundibugyo team — the threshold is correct laboratory practice and they stated it plainly. It is a demonstration that **the sequenced set is never a random sample of the case set**, and that the deviation is structured, not random.

## Section 3 · Enrichment: the central strategic choice

A clinical sample is overwhelmingly host material. In blood from an Ebola patient, viral RNA may be a tiny fraction of total nucleic acid. Sequence it blind and you pay to sequence the patient. So you enrich. There are four approaches and they trade off along the same axis: **how much you need to know about the target in advance.**

### 3.1 Tiling amplicon PCR — the workhorse (ARTIC style)

Design a set of PCR primers that produce short, **overlapping** products spanning the entire genome, like planks on a fence. Split them into two (or more) **pools** so that neighbouring, overlapping amplicons are never in the same reaction — otherwise they would amplify each other's products as short junk.

```
genome  ─────────────────────────────────────────────────────────
pool 1  ▔▔▔▔▔▔▔      ▔▔▔▔▔▔▔      ▔▔▔▔▔▔▔      ▔▔▔▔▔▔▔
pool 2       ▔▔▔▔▔▔▔      ▔▔▔▔▔▔▔      ▔▔▔▔▔▔▔      ▔▔▔▔▔▔▔
              ↑ overlap ensures no gaps between amplicons
```

- **Amplicon length** is a real design decision: ~400 bp schemes tolerate degraded RNA and high Ct; ~1,200–2,000 bp schemes need better-quality input but give far fewer amplicons to handle and play to nanopore's strengths.
- **Schemes are versioned**, and the version matters. The ARTIC SARS-CoV-2 scheme went through many revisions, each fixing amplicons that had started failing.
- Schemes are generated with tools like **PrimalScheme** from a set of reference genomes.

**The two ways amplicon schemes fail — both epidemiologically consequential:**

**(a) Primer dropout / amplicon dropout.** The target evolves a mutation under a primer binding site. That primer binds poorly, its amplicon is under-amplified, and you get a **coverage hole**. In the consensus that becomes a run of Ns — and crucially, **the region that dropped out is the region that changed**, so you systematically lose exactly the mutations you most wanted to see. This is why scheme versions are chased so hard during an evolving epidemic.

**(b) Primer sequence in the consensus.** If primer sequence is not trimmed off the reads, the *primer's* bases — which match the original reference, not the patient's virus — get called as consensus. You get a **fake reversion to reference** at exactly the variable site. Primer trimming (Lesson 5) exists solely to prevent this, and forgetting it has put spurious "reversions" into published datasets.

✱ The Bundibugyo work used the ARTIC Network's **`amplicon-nf` v2** pipeline — a Nextflow implementation of the ARTIC amplicon assembly approach whose intellectual ancestor is the field bioinformatics written for Ebola virus in West Africa a decade ago. The lineage of that software is the lineage of this field.

### 3.2 Bait capture / target enrichment

Synthesise many short biotinylated probes complementary to the target genome, hybridise them to the library, pull them out with magnetic beads.

- **More tolerant of divergence** than PCR: a probe with a few mismatches still hybridises, where a primer with a mismatch at its 3′ end simply fails. So capture is better for pathogens you cannot predict, and for panels covering whole viral families.
- **Less sensitive at very high Ct** than amplicon PCR, and considerably more expensive per sample.
- Used for broad respiratory or viral-family panels, and where new lineages are expected.

### 3.3 Metagenomics (shotgun, pathogen-agnostic)

Sequence everything in the sample; identify pathogens computationally afterwards.

- **The only approach that can find something you did not think of.** For an undiagnosed outbreak — "unknown illness with high mortality", which is exactly how the 2026 DRC event was first reported to WHO — this is the tool.
- **Costly and insensitive** relative to targeted methods. Reported consumables costs range widely, roughly $130 to $600+ per sample depending on depth and prep, and clinical mNGS services have been costed far higher. Most of your reads are host.
- **Host depletion** (saponin lysis, DNase, or nanopore adaptive sampling) improves the ratio but adds handling.
- Deep Dive 5 covers where this is genuinely operational and where it is still a promise.

### 3.4 Direct WGS from culture or high-biomass sample

For bacteria: grow the isolate, extract abundant pure DNA, sequence the whole genome without enrichment. Clean and cheap and the basis of routine bacterial surveillance (Lesson 6, Deep Dive 4) — at the cost of culture time and culture bias.

### Choosing, in one table

| | Amplicon | Capture | Metagenomics | Culture WGS |
|---|---|---|---|---|
| Need to know target in advance | Exactly | Approximately | Not at all | Yes (to culture it) |
| Tolerates high Ct / low load | **Best** | Moderate | Poor | n/a |
| Tolerates a divergent target | **Poor** | Good | Best | Good |
| Cost per sample | Low | High | Highest | Low |
| Finds co-infections / the unexpected | No | Within panel | **Yes** | No |
| Typical use | Known epidemic virus | Viral family panels | Undiagnosed syndrome | Bacterial surveillance |

## Section 4 · Library preparation and multiplexing

The **library** is the amplified, adapter-ligated, barcoded DNA that the sequencer can actually read. Whatever the enrichment, this stage does the same things:

1. **Fragment** (if needed) to the platform's preferred size.
2. **Repair ends and attach adapters** — the platform-specific sequences that let a molecule bind the flow cell and be primed.
3. **Attach a barcode (index)** — a short unique tag identifying which sample a read came from.
4. **Pool and normalise** — combine many barcoded samples into one run, ideally at equal concentration.

**Multiplexing is what makes surveillance affordable.** A flow cell that costs the same whether it carries 1 or 96 samples means the marginal cost of the 96th genome is small. It is the single biggest reason genomic surveillance became a routine activity rather than a research project.

⚠ **And multiplexing creates the field's most under-reported failure mode: index hopping and barcode cross-talk.** Reads get assigned to the wrong sample. A few reads from a high-load sample landing in a low-load sample's bin can, at low coverage, change a consensus base — and you have just invented a mutation, or worse, made two unrelated patients look identical. This is precisely a Q1 (linkage) error, arriving from the bench.

Mitigations: unique dual indices; not running a very high-load sample next to a very low-load one; a minimum depth threshold before calling a base; and controls.

## Section 5 · Controls, and what each one rules out

Non-negotiable on every run. If a genomic surveillance report does not mention controls, that is a finding.

| Control | What it is | What it rules out |
|---|---|---|
| **Negative / no-template control** | Water through the entire workflow | Reagent and environmental contamination; index hopping into an empty bin |
| **Extraction blank** | Buffer only, extracted alongside samples | Contamination introduced during extraction specifically |
| **Positive control** | Known material, ideally a synthetic or distinguishable strain | The run worked; and, if distinguishable, whether it leaked into your samples |
| **Replicate** | The same sample twice, ideally in different positions | Reproducibility of the consensus; barcode-position effects |

✱ A positive control that is **the same strain as your outbreak** is a trap: if it contaminates a sample you cannot tell. Good labs use a distinguishable control for exactly this reason.

## Section 6 · Turnaround, and why it decides everything

For outbreak response, the metric that matters is not accuracy — it is **sample-to-answer time**, and it is dominated by logistics, not chemistry.

```
onset → care-seeking → specimen taken → transport → PCR → sequencing batch →
  run (hours–days) → bioinformatics → interpretation → the person who can act
```

The sequencing run is rarely the bottleneck. The bottleneck is usually **transport** (a sample moving from Mongbwalu to Kinshasa) and **batching** (waiting to fill a flow cell). Both are fixable with money and decentralisation, and both are the argument for in-country and in-outbreak sequencing capacity — the argument the Africa PGI has been making since 2019, taking sequencing capacity from 7 African countries to 46 by late 2025.

⚠ **A genome that arrives after the decision was made has zero epidemiological value and non-zero cost.** Judge a surveillance system on the distribution of sample-to-answer times, not on the number of genomes.

## Practice

Find the methods section of any genomic surveillance paper and extract five things:

1. Specimen type(s), and whether different groups of cases contributed different specimen types.
2. The selection rule for which PCR-positive samples got sequenced (Ct threshold? all? a quota?).
3. The enrichment strategy, and the primer scheme *version* if amplicon-based.
4. Whether primer trimming is mentioned.
5. Controls.

Then write one sentence describing the sampling frame in epidemiological terms. If the paper does not let you write that sentence, you have found its main weakness.

## In one paragraph

The wet-lab chain runs specimen → extraction → reverse transcription → enrichment → library → sequencer, and at least two of those steps are epidemiological decisions in disguise. Specimen choice determines who can be represented at all — oral fluid from the deceased is why community deaths appear in the Bundibugyo dataset. The Ct threshold determines which cases are sequenced, and because Ct tracks time since onset, severity and access to care, that threshold structures the genomic sample in ways that matter for every downstream inference. Enrichment is a trade between how much you must know in advance and how much divergence and cost you can tolerate; tiling amplicons are cheapest and most sensitive but fail exactly where the pathogen changed. Multiplexing makes the whole enterprise affordable and simultaneously creates the cross-contamination risk that most threatens linkage claims, which is why controls are not optional.
