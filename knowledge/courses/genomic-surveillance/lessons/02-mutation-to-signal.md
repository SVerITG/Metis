# Lesson 2 — Mutation, substitution, signal, artefact: the vocabulary that stops you being fooled

> **Concept map**
> **Builds on** — Lesson 1: you know the clock ticks; this is what a tick actually looks like in data.
> **Connects to** — Lesson 5 (where consensus calling throws most of this away) and Lesson 9 (where the substitution model formalises it).
> **Leads to** — Deep Dive 1, whose most consequential decision is the exclusion of 32 genomes for a specific mutational signature.

## Why this matters

Almost every serious misreading of genomic data traces back to a word being used loosely. "Mutation" for "substitution". "The virus mutated" for "we observed a difference". "New variant" for "a lineage we hadn't named yet". These are not pedantic distinctions — each one hides a different quantity, and confusing them is how a routine sequencing artefact becomes a press release about a dangerous new strain.

This lesson is the vocabulary, and then the part that matters more: how to tell **signal** (the pathogen genuinely changed) from **artefact** (something in the host, the lab, or the software made it look that way). The flagship study of this course threw away 32 of 626 genomes on exactly this judgement, and if it had not, the headline evolutionary rate would have been wrong.

## Learning objectives
By the end of this lesson you will be able to:

- **Use** mutation, substitution, polymorphism, SNP, indel and variant precisely, and correct their misuse.
- **Explain** why a consensus genome is a summary that discards within-host diversity, and when that matters.
- **Recognise** the three mutational signatures that are not the pathogen's own evolution — APOBEC3, ADAR, and oxidative damage — from their base-change patterns alone.
- **Justify** the exclusion of sequences from a phylodynamic analysis, and state what excluding them costs.

## Prerequisites
Lessons 0–1.

---

## Section 1 · The words, in the right order

**Mutation** — an *event*. A copying error occurs in one replication, in one host, at one moment. Mutations happen constantly and almost all of them go nowhere: the virion carrying them is never transmitted, never sampled, or is out-competed.

**Substitution** — a mutation that has *become fixed* in a lineage you can observe. When epidemiologists say "the evolutionary rate", they mean the substitution rate: the rate at which changes accumulate along a lineage *and survive to be sampled*.

⚠ **The mutation rate and the substitution rate are different numbers, sometimes by orders of magnitude.** The mutation rate is a property of the polymerase. The substitution rate is a property of the polymerase *filtered through* natural selection, population bottlenecks and your sampling. Purifying selection removes most mutations, so substitution rate < mutation rate — usually far less. A paper that quotes one while meaning the other is a paper to read carefully.

**Polymorphism** — a position where more than one base is present in the population under study. Neutral word, no claim about history.

**SNP / SNV** — single nucleotide polymorphism / variant. One position, one base swapped. The workhorse unit of bacterial genomic epidemiology ("these isolates differ by 4 SNPs").

**Indel** — insertion or deletion. Harder to call reliably, often excluded from analyses for that reason, and occasionally the most informative thing in the dataset: the mpox clade Ib work identifies a large ~1,142 bp deletion and terminal deletions as lineage markers.

**Transition / transversion** — a transition swaps a purine for a purine (A↔G) or a pyrimidine for a pyrimidine (C↔T). A transversion crosses the classes. Transitions are chemically easier and happen several times more often; every substitution model in Lesson 8 has a parameter for this ratio, and **an unusual transition pattern is your first clue that something non-evolutionary is going on** (Section 4).

**Synonymous / non-synonymous** — a synonymous change leaves the protein unchanged (the genetic code is redundant); a non-synonymous one changes an amino acid. The ratio dN/dS is the classical test for selection: <1 means purifying selection (most of the genome, most of the time), >1 means positive selection.

**Homoplasy** — the same change arising independently in two lineages. It is the enemy of tree-building, because it makes unrelated things look related. Recurrent, convergent mutations at drug-resistance loci are homoplasy by definition — which is why resistance sites are often *masked* before tree building. Lesson 8.

**Lineage / clade / variant / strain** — deferred to Lesson 6, which is entirely about naming, because naming is where this field is messiest.

## Section 2 · The consensus genome: a summary, not a specimen

Here is the single most under-taught fact in applied genomic surveillance.

When you sequence a clinical sample, you are not sequencing *a* genome. You are sequencing a **population** of genomes — millions of viral particles or bacterial cells inside one person, which are not identical, because the pathogen has been replicating and mutating inside that host since infection.

What comes out of the standard pipeline is a **consensus genome**: at each position, the base that the majority of reads support. It is a summary statistic of a population, in the same way that a mean is a summary of a distribution.

```
     Reads at position 4,412
     ────────────────────────
     ...ACGT A GCTA...        68 reads     A  ← consensus reports A
     ...ACGT G GCTA...        32 reads     G  ← the 32% is discarded
```

That discarded 32% is **within-host diversity**, and the individual variants are **iSNVs** (intra-host single nucleotide variants). Consensus calling throws them away by design, and usually that is correct — they are noisy, sequencing-depth dependent, and easily confused with error. But it means:

- **A consensus genome cannot show you a mixed infection.** Two lineages in one host average into one impossible-looking sequence, or the minor one vanishes.
- **A consensus genome cannot show you a minority resistant subpopulation.** For TB and HIV this is clinically consequential; it is why targeted deep sequencing exists.
- **A consensus genome cannot measure the transmission bottleneck.** How much diversity passes from one host to the next is a real question with real answers, and it needs reads, not consensus.
- **The consensus can change without the population changing**, if a minor variant crosses 50% because of a shift in sampling depth. This produces phantom "mutations" between serial samples of the same patient.

✱ Practical rule: **the consensus genome is the right object for between-host questions (Q1–Q4 at population scale) and the wrong object for within-host questions.** If your question involves mixed infection, minority resistance, bottlenecks, or persistence in a survivor, you must plan to keep the reads. Storage and analysis costs are the reason most programmes cannot answer those questions retrospectively.

## Section 3 · Which changes carry epidemiological signal

Not every difference between two genomes is useful, and knowing which to trust is the whole craft.

**Signal — trust these**

- Substitutions in well-covered, non-repetitive regions with high read depth on both strands.
- Changes shared by a set of sequences in a way consistent with a tree (i.e. they define clades rather than appearing scattered).
- Indels that are cleanly supported and reproducible across samples and runs.

**Noise — treat with suspicion**

- Changes at the ends of the genome. Coverage falls off, amplicon primers sit there, and assembly gets ragged. **The Bundibugyo authors trimmed their alignment to 18,900 bp precisely to remove end-of-genome artefacts**, after one genome (26FHV054) showed them.
- Changes in homopolymer runs (AAAAAA). Nanopore historically miscounts these; it is much better now but they remain the first place to look.
- Changes at primer-binding sites in amplicon schemes. If a primer sits over a real mutation, you get **amplicon dropout** — and if primer sequence leaks into the consensus, you get a *fake reversion to reference*. Lesson 5.
- Changes appearing only in low-coverage regions, or supported by reads from one strand only.
- Changes at known recurrent/homoplastic sites — resistance loci, hypervariable repeats.

**Artefact from the host — the interesting case, Section 4.**

## Section 4 · Three mutational signatures that are not the pathogen's evolution

This is the section that makes Deep Dive 1 comprehensible, and it is the section most courses skip.

Your immune system attacks pathogen genomes chemically. It edits them. The edits look exactly like mutations to a sequencing pipeline, but they are **host-imposed damage**, not the pathogen's replication error — and they have distinctive, recognisable base-change patterns.

### APOBEC3 — the mpox clock
APOBEC3 enzymes deaminate cytosine to uracil in single-stranded DNA. In the genome this reads out as **C→T** changes (and G→A on the other strand), strongly enriched in a specific sequence context (TC dinucleotides).

For mpox this turned out to be enormously useful. Orthopoxviruses evolve far too slowly for outbreak epidemiology; but during **sustained human-to-human transmission**, APOBEC3-driven C→T changes accumulate fast enough to give a usable clock. So in mpox, the APOBEC3 signature is:

1. **A clock** — it provides the temporal signal for dating.
2. **A diagnostic of human transmission** — a genome loaded with APOBEC3-type changes has been passing through humans, not sitting in an animal reservoir. This is how the clade Ib work, and the Canadian and US clade Ib detections, argued for sustained human transmission from sequence alone.

⚠ **But it is not neutral evolution, and treating it as such biases everything.** The changes are not randomly distributed, they are not independent, and a standard substitution model assumes they are. This is an active methodological problem, not a solved one.

### ADAR — and why 32 Bundibugyo genomes were deleted
ADAR (Adenosine Deaminase Acting on RNA) deaminates adenosine to inosine in double-stranded RNA. Inosine is read as G, so on the genome strand you see **A→G**, and on the reverse-complement — which is how filovirus genomes are conventionally written — you see **T→C**.

The tell is not the base change alone but its **clustering**: ADAR is processive, so it edits *short spans* of consecutive sites rather than isolated positions. The Bundibugyo authors screened for exactly this — genomes with an "excess of T→C mutations" in short spans — and **excluded 32 of 626 genomes** on that basis.

Why exclude rather than keep? Because those changes are not the virus's evolutionary history. Left in, they:

- inflate the apparent substitution rate, which biases the clock, which biases the tMRCA;
- create long spurious branches, distorting tree shape, which biases the coalescent estimates of growth rate;
- are homoplastic across unrelated tips, corrupting topology.

✱ And note the second-order sophistication in that paper, which is the part worth stealing: the authors observed that **"a bout of ADAR editing on an internal branch may affect multiple tips"** — the affected genomes are not independent of each other. That is why their outlier removal was **iterative** (Section 5): remove, re-root, re-fit, remove again. Treating non-independent outliers as independent is a standard mistake, and they avoided it.

### Oxidative damage — the lab's own signature
Sample handling, particularly shearing during library prep, oxidises guanine, producing characteristic **G→T** artefacts. Low-frequency, often strand-biased. Mostly a problem for low-frequency variant calling rather than consensus, but it is the third member of the family and it comes from your own laboratory rather than the patient.

### The summary table worth memorising

| Signature | Base change | Source | Pattern | What to do |
|---|---|---|---|---|
| **APOBEC3** | C→T (G→A) | Host, ssDNA | TC context, genome-wide | Mpox: use it as the clock, but model it honestly |
| **ADAR** | A→G (T→C) | Host, dsRNA | **Short consecutive spans** | Filoviruses: screen and exclude |
| **Oxidative** | G→T | Lab, sample prep | Low frequency, strand-biased | Fix the protocol; filter by strand balance |

## Section 5 · Excluding sequences: how to do it defensibly

Excluding data is a decision with a cost, and it is the decision most likely to be challenged. The Bundibugyo analysis is a good template because it makes every step explicit.

Their sequence of exclusions, from 626 genomes:

1. **32 excluded for ADAR editing signatures** — a *mechanistic* criterion, decided by a known biological process, not by "this one looks odd".
2. **69 excluded as phylogenetic outliers** — a *statistical* criterion. Build the ML tree, run root-to-tip regression, remove tips more than ±2 SD from the regression residuals, re-root the tree to minimise residuals, and repeat. Cumulative removal across iterations: 69.
3. **525 genomes retained** for the phylodynamic analysis.

Four things make this defensible, and you should demand all four of any exclusion you read or write:

- **The criterion is stated before the result.** ADAR editing is a known process with a known signature; the filter is not "remove until the tree looks nice".
- **The counts are reported at every stage.** 626 → 594 → 525. You can reconstruct what happened.
- **The procedure handles non-independence.** Iterating, rather than one pass, because outliers cluster.
- **The consequence is checked.** They ran the whole analysis on four nested time windows to confirm the conclusions were not an artefact of curation or of sparse late sampling (Deep Dive 1).

⚠ **What does exclusion cost?** Real diversity, if you get it wrong. A genuinely divergent introduction from an unsampled chain looks exactly like a root-to-tip outlier. That is why the mechanistic filter (ADAR) should always come first: it removes sequences for a *reason*, leaving the blunt statistical filter to handle less. And why the residual outliers are worth a look before they are discarded — occasionally the outlier is the finding.

## Practice

Take any phylodynamic paper on an RNA virus and answer four questions:

1. How many sequences were generated, and how many were analysed? If those numbers differ, is the difference explained?
2. Was any mutational-signature screening done? (For filoviruses: ADAR. For mpox: APOBEC3. For anything: end-of-genome trimming.)
3. Was outlier removal one-pass or iterative?
4. Was the alignment trimmed, and is the trimming justified with a reason rather than a convention?

If you cannot answer these from the paper, that is the review comment.

## In one paragraph

A mutation is an event, a substitution is a mutation that survived to be seen, and the difference between those two rates is selection. What arrives in your pipeline is a consensus genome — a majority summary of a diverse within-host population — so any question about mixture, minority resistance or transmission bottlenecks needs the reads instead. Among the differences you do see, some are the pathogen's evolution and some are host enzymes editing it: APOBEC3 writes C→T and gives mpox its usable clock, ADAR writes T→C in short runs and cost the Bundibugyo dataset 32 genomes. Distinguishing signal from artefact before building a tree is not a preliminary; it is the step that determines whether the clock, the date of origin and the growth rate mean anything at all.
