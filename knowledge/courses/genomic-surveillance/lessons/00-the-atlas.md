# Lesson 0 — The atlas: what genomic surveillance is, and the four questions it answers

> **Concept map**
> **Builds on** — nothing. This is the map you will point at for the rest of the course.
> **Connects to** — every later lesson is one box on this map, opened up.
> **Leads to** — Lesson 1, where the map's central claim (a genome is a clock and a family tree at once) gets its justification.

## Why this matters

Genomic surveillance is taught badly almost everywhere, and it is taught badly in a specific way: as a **pipeline**. Sample, extract, amplify, sequence, assemble, align, tree, publish. Learn the steps, run the steps, you have done genomic surveillance.

That is the wrong shape. The pipeline is real and you need it — Lessons 3 to 9 are that pipeline in detail — but it is the plumbing, not the discipline. The discipline is the part where a tree with 525 tips gets turned into a sentence that changes what an outbreak response does on Monday. That sentence is what a Minister, an incident manager, or a reviewer actually receives. Everything upstream exists to make it defensible.

So this course is built the other way round. This lesson gives you the whole landscape on day one — every major application, every method family, every place where it fails — so that when you meet `farringtonFlexible`, or a SkyGrid prior, or an ADAR editing filter, you already know what job it is doing and what would be lost if it were done badly.

> **The spine of this course, in one sentence:**
> **A pathogen genome is a clock and a family tree at the same time. Every claim in genomic surveillance is an answer to one of four questions — is this the same outbreak, where did it come from, how fast is it spreading, and has the pathogen changed. And what decides whether the answer is trustworthy is almost never the sequencer. It is the sampling and the metadata.**

Hold onto the second half. It is the part that does not go out of date. Sequencing chemistry will turn over twice in your career; the failure modes will not.

## Learning objectives
By the end of this lesson you will be able to:

- **Classify** any genomic surveillance claim into one of the four questions, in under a minute.
- **Name** the epidemiological method each genomic answer is competing with — and why the comparator matters.
- **Locate** any of the ~60 applications in the atlas below on the molecule → machine → data → tree → decision chain.
- **State** the three things a consensus genome cannot tell you, no matter how good the sequencing was.

## Prerequisites
None beyond epidemiological literacy. No molecular biology is assumed; Lessons 1–2 build it from the ground up. If you have never seen a phylogenetic tree, that is fine — Lesson 7 assumes you haven't.

---

## Section 1 · The four questions

Everything in this field is one of these. Learn to sort claims into them, because **each one owes you different evidence**, and mixing them up is the most common error in the literature and in press releases.

### Question 1 — "Is this the same outbreak?"
*Also: is this case linked to that case; is this cluster real; did this patient relapse or get reinfected; is this a new introduction or ongoing transmission.*

- **What genomes give you:** genetic distance between isolates, and the shape of the tree connecting them.
- **The comparator:** classical contact tracing and epidemiological linkage.
- **The evidence it owes you:** the *background* genetic diversity. Two isolates 3 SNPs apart mean nothing until you know how far apart two randomly chosen unlinked isolates usually are.
- **The asymmetry you must internalise:** genomics is far better at **ruling links out** than ruling them in. Two genomes 40 SNPs apart in a slow-evolving pathogen were almost certainly not directly linked. Two identical genomes are *consistent with* direct transmission and also with a chain of six people, or two independent infections from the same source.

### Question 2 — "Where did it come from?"
*Also: which country seeded this wave; is this a spillover or human-to-human; is the reservoir animal or human; which ward did the nosocomial cluster start in.*

- **What genomes give you:** phylogeography — a reconstruction of ancestral locations or hosts on the tree.
- **The comparator:** travel histories, exposure questionnaires, animal surveillance.
- **The evidence it owes you:** sampling proportions per location. An ancestral state reconstruction is a statement about *your sample*, and it will confidently place origins wherever you sequenced most.

### Question 3 — "How fast is it spreading?"
*Also: what is R; is the epidemic growing or shrinking; what is the doubling time; how much transmission is unobserved.*

- **What genomes give you:** phylodynamics — growth rates and effective population size inferred from the *shape* of a time-scaled tree.
- **The comparator:** the case-based epidemic curve and Rt from incidence.
- **The evidence it owes you:** agreement or disagreement with the case data, explained. Genomic Re and case-based Rt measure related but different things; when they disagree, that disagreement is the finding.

### Question 4 — "Has the pathogen changed?"
*Also: is this a new variant; is it more transmissible; is it resistant; will the diagnostic still detect it; will the vaccine still work.*

- **What genomes give you:** mutations, lineage assignment, resistance-marker calling.
- **The comparator:** phenotype — an MIC, a neutralisation assay, a clinical outcome, a treatment failure rate.
- **The evidence it owes you:** the phenotypic link. **A mutation is a hypothesis about a phenotype, not a phenotype.** This is where the field produces its worst headlines.

⚠ **The most common failure in the whole field is answering one question with evidence that belongs to another.** "The variant is more transmissible" (Q4) supported only by "it grew faster in our sequence dataset" (Q3, and confounded by sampling) is the canonical version. You will see it several times a year for the rest of your career.

## Section 2 · The chain: from DNA to a decision

Every one of the four questions runs down the same physical and computational chain. This course is organised as that chain, and the atlas below hangs off it.

```
   THE MOLECULE          THE MACHINE            THE DATA             THE TREE           THE DECISION
   ───────────           ───────────            ────────            ──────────          ────────────
   pathogen genome  →    extraction        →    reads (FASTQ)   →   alignment      →    is it one outbreak?
   mutation             library prep           QC + trimming        ML phylogeny        where from?
   substitution rate    amplicon / mNGS        mapping              rooting             how fast?
   within-host          Illumina / ONT         consensus            molecular clock     has it changed?
     diversity          basecalling            lineage call         time-tree           ────────────
                                               ─────────────        phylodynamics       who acts, and when
   Lessons 1–2          Lessons 3–4            Lessons 5–6          Lessons 7–12        Lessons 13–15
```

Two remarks about this diagram, both of which take the rest of the course to earn.

**First: information is only ever lost as you move right.** The molecule contains everything. Every subsequent step is a lossy compression — the consensus genome throws away within-host diversity, the alignment throws away regions you couldn't sequence, the tree throws away everything except topology and branch lengths, the phylodynamic summary throws away the tree. Good practice is knowing *what* each step discarded and whether your question needed it.

**Second: the two boxes with the least glamour — sampling and metadata — sit outside the diagram and determine all of it.** They are Lesson 13, deliberately placed after you know enough to see why they dominate.

## Section 3 · The atlas

What genomic surveillance is actually used for, sorted by question, with a maturity label. **Routine** = done as standard practice in well-resourced systems. **Established** = a mature research application, deployed in places. **Emerging** = real, but the evidence base or the operational model is still being built.

### Q1 · Linkage, clusters and outbreaks

| Application | Pathogens | Maturity |
|---|---|---|
| Hospital / nosocomial outbreak confirmation | MRSA, *K. pneumoniae*, *C. difficile*, SARS-CoV-2 | Routine |
| Foodborne outbreak detection and source attribution | *Salmonella*, *Listeria*, STEC | Routine (PulseNet, cgMLST) |
| Ruling out a suspected transmission link | TB, HIV, all | Routine |
| Relapse vs reinfection | TB, HAT, malaria, Ebola survivors | Established |
| Laboratory cross-contamination detection | any | Routine |
| Distinguishing importation from local transmission | measles, polio, cholera, mpox | Routine |
| Persistence / flare-ups from survivors | Ebola (sexual transmission, months–years later) | Established |
| Cluster detection in near-real-time surveillance | HIV (US CDC), TB | Established |

### Q2 · Origins, geography and hosts

| Application | Pathogens | Maturity |
|---|---|---|
| Reconstructing epidemic seeding between countries | SARS-CoV-2, influenza, cholera | Routine |
| Zoonotic spillover identification and counting | H5N1, mpox, Ebola, Lassa | Established |
| Identifying the reservoir or intermediate host | Lassa (rodents), MERS (camels) | Established |
| Within-country spatial spread of an epidemic | Ebola, cholera, measles | Established |
| Wildlife/livestock–human interface | *T. b. gambiense* in animals, rabies, brucellosis | Emerging |
| Attributing a resurgent focus to import vs residual transmission | polio, HAT, measles | Established |
| Vector genomics: insecticide resistance and species ID | *Anopheles*, *Aedes*, tsetse | Established |

### Q3 · Dynamics

| Application | Pathogens | Maturity |
|---|---|---|
| Growth rate / doubling time from genomes | Ebola, SARS-CoV-2, mpox | Established |
| Re / Rt estimation from phylodynamics | most epidemic viruses | Established |
| Estimating unobserved transmission (how much are we missing) | HIV, TB, SARS-CoV-2 | Established |
| Dating the origin of an outbreak (tMRCA) before its first case | every filovirus outbreak | Routine |
| Detecting hidden/cryptic transmission before case data does | SARS-CoV-2 2020, mpox 2022 | Established |
| Measuring the impact of an intervention on transmission | HIV treatment scale-up | Emerging |

### Q4 · The pathogen has changed

| Application | Pathogens | Maturity |
|---|---|---|
| Variant / lineage designation and tracking | SARS-CoV-2, mpox, influenza | Routine |
| Drug resistance prediction from sequence | TB, HIV, malaria, gonorrhoea | Routine (TB, HIV) |
| Vaccine strain selection | influenza (twice yearly), polio | Routine |
| Diagnostic escape detection | *pfhrp2/3* deletions; SARS-CoV-2 S-gene target failure | Routine |
| AMR gene and plasmid surveillance | Enterobacterales, *N. gonorrhoeae* | Routine |
| Serotype replacement after vaccination | pneumococcus, HPV | Established |
| Immune escape / antigenic evolution | influenza, SARS-CoV-2, RSV | Established |
| Virulence-marker monitoring | H5N1 PB2 mutations, mpox deletions | Emerging |
| Fitness prediction from sequence alone (ML) | influenza, SARS-CoV-2 | Emerging, contested |

### Cross-cutting platforms and modalities

| Modality | What it changes | Maturity |
|---|---|---|
| Wastewater genomic surveillance | population-level, no clinical sampling, lineage mixtures | Established (SARS-CoV-2, polio); Emerging (multi-pathogen) |
| Pathogen-agnostic metagenomics | finds what you didn't ask for | Emerging, expensive |
| Targeted NGS panels (tNGS) | resistance profiling direct from specimen | Routine for TB (WHO 2025 guidance) |
| Portable / in-country sequencing | turnaround, sovereignty, capacity | Routine in an expanding set of countries |
| Real-time public builds (Nextstrain) | a shared, always-current picture | Routine |
| Genomic data platforms (GISAID, Pathoplexus, ENA/GenBank, AGARI) | who can see what, and under what terms | Contested |

## Section 4 · The three things a consensus genome cannot tell you

Worth learning now, because they explain most over-claiming.

1. **Who infected whom.** A phylogeny is a tree of *sequences*, not of *people*. Even a perfect tree from perfect sampling does not give you a transmission tree — Lesson 12 has the full argument, and it is not a small technicality.
2. **Whether a mutation does anything.** Sequence gives you a change in a genome. Phenotype gives you a change in the world. The bridge between them is experimental, and it is often not built.
3. **What is happening where you did not sequence.** The single most important sentence in every genomic surveillance report is the one describing the sampling frame — and it is the sentence most often missing.

✱ There is a fourth, subtler one: **a consensus genome throws away within-host diversity by construction.** It reports the majority base at each position. For questions about transmission bottlenecks, mixed infection, or minority resistant subpopulations, the consensus is the wrong object and you need the reads. Lesson 5.

## Section 5 · Where this course is going

- **Day 1 — the molecule and the machine.** What a genome is, why it carries epidemiological signal, and the physical chain that gets it into a computer. Lessons 1–4.
- **Day 2 — reads to genomes to trees.** Bioinformatics, naming, alignment, tree building. Lessons 5–8.
- **Day 3 — time and dynamics.** Molecular clocks, tMRCA, coalescent models, growth rates, phylogeography, clusters. Lessons 9–12.
- **Day 4 — the system.** Sampling, metadata, data sharing, equity, and turning a genome into a decision. Lessons 13–15, plus the flagship deep dive.
- **Day 5 — recent applications (optional but the point).** Five deep dives on work published in the last two years, each read closely enough that you could explain it to a room.

The flagship is the **2026 Bundibugyo virus outbreak in Ituri, DRC** — 626 genomes over a 100-day window, analysed in the open on virological.org by INRB Kinshasa with Edinburgh, Oxford, Birmingham and ITM Antwerp. By the end of Deep Dive 1 you will understand every methodological choice in that post, including the ones the authors did not explain because they assumed their audience already knew.

## In one paragraph

Genomic surveillance turns a pathogen's genome into epidemiological evidence, and it answers exactly four questions: is this the same outbreak, where did it come from, how fast is it spreading, and has it changed. Each question has a classical comparator it must beat and a distinct kind of evidence it owes you. The chain from molecule to decision is lossy at every step, and the two steps that determine whether any of it is trustworthy — sampling and metadata — are the two that get the least attention. The rest of this course is that chain, one link at a time, and then five recent outbreaks where the links held.
