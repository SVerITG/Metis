# Lesson 4 — The machines: how DNA becomes data, and why the platform choice is a surveillance-design choice

> **Concept map**
> **Builds on** — Lesson 3: you have a library; this is what happens to it.
> **Connects to** — Lesson 5 (the error profile you inherit here determines the filters you need there) and Lesson 13 (throughput and latency are surveillance-system parameters).
> **Leads to** — Deep Dive 1's field-sequencing setup, and Deep Dive 5's wastewater work, which lives or dies on platform economics.

## Why this matters

This is the literal "DNA to machines" step: the point at which a molecule stops being chemistry and becomes a string of letters in a file. Two things make it worth a full lesson rather than a paragraph.

**First, the error profile you inherit here propagates all the way to the tree.** Illumina and nanopore fail in different ways — one makes substitution errors, the other historically made length errors in repeats — and every quality filter in Lesson 5 exists to clean up a specific platform's specific weakness. You cannot judge a filter without knowing what it is filtering.

**Second, platform choice is not a procurement decision, it is a surveillance-design decision.** Throughput, latency, capital cost, power, cold chain and who can fix the machine determine whether your programme produces 500 genomes in one batch six weeks late, or 40 genomes a week in real time. Those two programmes answer different questions. Choosing the instrument before deciding the question is the most common and most expensive mistake in national genomic surveillance planning.

## Learning objectives
By the end of this lesson you will be able to:

- **Explain**, at mechanism level, how Illumina sequencing-by-synthesis and nanopore sequencing produce a read.
- **Interpret** a Phred quality score and explain why depth compensates for per-read error.
- **Describe** what basecalling is and why re-basecalling old data changes the genomes you get.
- **Match** a platform to a surveillance scenario, arguing from latency, throughput, accuracy and operating environment rather than brand.
- **State** what adaptive sampling is and the two problems it solves.

## Prerequisites
Lessons 0–3.

---

## Section 1 · What every sequencer is trying to do

Strip away the chemistry and every platform solves the same problem:

> Take an unreadable physical molecule and produce a **read** — a string of letters with a per-letter confidence score.

The platforms differ on how they observe the molecule, and that single difference cascades into everything else: read length, error type, throughput, latency, cost, size and whether the machine survives a hot room with unreliable power.

## Section 2 · Illumina — sequencing by synthesis

The dominant platform for volume, and the one behind most of the world's bacterial and much of its viral surveillance.

**How it works:**

1. **Bind.** Library molecules attach to a glass flow cell coated with oligos matching the adapters.
2. **Amplify in place.** Each single molecule is copied into a tight cluster of ~1,000 identical copies — **bridge amplification**. This matters: the machine cannot see one molecule, so it makes a spot bright enough to photograph.
3. **Sequence by synthesis.** Add all four bases at once, each carrying a different fluorescent dye and a **reversible terminator** that stops the chain after exactly one base. Wash, photograph the whole flow cell, chemically remove dye and terminator, repeat. Each cycle adds one base to every cluster.
4. **Read out.** The sequence of colours at each cluster location, across cycles, is the read.
5. **Paired ends.** The fragment is then sequenced from the other end too, giving a read pair with a known approximate insert size — useful for mapping and for detecting structural weirdness.

**Consequences of this design, which are the things you actually need:**

- **Short reads.** Typically 2 × 150 bp, up to 2 × 300 bp on some instruments. Cycles are slow and signal degrades as clusters lose synchrony (**phasing**), so length is capped.
- **Very high per-base accuracy**, typically Q30+ (1 error in 1,000). Errors are almost all **substitutions**, not indels.
- **Enormous throughput**, and correspondingly **high latency**: you fill a flow cell, run it for hours to days, then get everything at once. Nothing is available until the run ends.
- **Quality degrades along the read** — the 3′ end is worse. Hence read trimming in Lesson 5.
- **A specific weakness: low-complexity and repetitive regions.** Short reads cannot span a long repeat, so assemblies fragment there. For a 19 kb virus, irrelevant. For a bacterial genome with repeated insertion sequences or a plasmid, this is why short-read-only assemblies are usually draft-quality and in many pieces.

**Instrument range**, roughly: benchtop MiSeq-class instruments (low six figures, small runs, 2 × 300 bp) through NextSeq-class mid-throughput up to NovaSeq-class population-scale machines costing close to a million. **The capital cost is rarely the binding constraint — the reagent cold chain, the service contract and the run-size economics are.** A NovaSeq in a laboratory that can fill it twice a year is a worse instrument than a MiSeq that runs weekly.

## Section 3 · Oxford Nanopore — reading the molecule directly

The platform that made field and in-country outbreak sequencing normal, and the one used across the ARTIC-lineage filovirus work.

**How it works:**

1. **A membrane with protein pores.** An electrical potential across the membrane drives ions through each pore, producing a steady current.
2. **A motor protein** ratchets a single DNA strand through the pore, one short stretch at a time.
3. **The bases in the pore obstruct the current** in a way that depends on which ~5–10 bases are sitting in the constriction. The measured current over time — the **"squiggle"** — is the raw data.
4. **A neural network converts squiggle to sequence.** This is basecalling, and it is Section 5.

**Consequences:**

- **Read length is limited by the molecule, not the chemistry.** If you can deliver a 100 kb fragment intact, you can read it. For amplicon work this means 1–2 kb amplicons are trivial; for bacteria it means a single read can span a repeat and give you a closed, single-contig genome.
- **Real-time output.** Reads appear as they are sequenced. You can watch coverage accumulate and **stop the run when you have enough**, which is a latency advantage nothing else matches.
- **Small and portable.** A MinION is roughly the size of a stapler and costs on the order of $1,000, running off a laptop's USB. GridION and PromethION scale the same chemistry up.
- **Historically the accuracy problem, now largely a solved one.** Current R10.4.1 / Kit 14 chemistry with the super-accurate basecaller reaches roughly **Q23 in simplex** (≈0.5% error) and, with **duplex** basecalling — reading both strands of the same molecule and combining them — approximately **Q30**, i.e. Illumina-comparable.
- **The characteristic residual weakness is homopolymers** — runs of the same base, where the current does not change as the strand ratchets through, so the length must be inferred. Much improved, still the first place to look for a spurious indel.
- **Flow cells are reusable** (washed between runs) and can be loaded with a few samples at a time, which changes the economics of small, frequent batches — exactly what outbreak response needs.

### Adaptive sampling — the feature worth understanding

Because nanopore reads a molecule progressively and the pore can be electrically reversed, the software can look at the first few hundred bases, decide the read is uninteresting, and **eject it** to free the pore for another molecule. This is **adaptive sampling** (ReadUntil).

It solves two problems that matter here:

- **Host depletion without wet-lab work** — reject human reads, enrich for pathogen, in software.
- **Targeted enrichment without primers** — sequence only reads matching a reference panel, e.g. AMR genes or a plasmid.

Once a niche demo, it is now in routine use across host depletion, metagenomics, targeted loci and AMR workflows. For metagenomic surveillance in a low-biomass, high-host sample it is one of the more consequential recent developments.

## Section 4 · The rest of the field, briefly

- **PacBio HiFi.** Circularises a molecule and reads it many times, producing a highly accurate long read (Q30+, 10–25 kb). Excellent for reference-quality assemblies. Capital and per-sample cost keep it out of routine surveillance.
- **Ion Torrent.** Detects the pH change from proton release during base incorporation — semiconductor, no optics. Fast, cheaper instruments, weaker on homopolymers. Still deployed in places, notably in some national systems.
- **Sanger sequencing.** Not dead and not obsolete. For a single short target — a polio VP1 region, a resistance locus, a confirmation — Sanger is cheap, ubiquitous, and available in laboratories that have no NGS at all. Much of global poliovirus surveillance ran on it for decades.

## Section 5 · Basecalling: where DNA actually becomes data

This is the hinge of the whole course, and it is worth being explicit about.

**Basecalling is the interpretation of a physical measurement as a sequence of letters.**

- On Illumina, it maps fluorescence intensities per cycle per cluster to bases.
- On nanopore, it maps a continuous ionic-current trace to bases, using a **neural network** — currently Dorado, which supersedes earlier basecallers and uses newer network architectures for speed and accuracy.

Three practical consequences:

**1. The basecaller is a model, and models have versions.** Re-basecalling the same raw signal with a newer model produces *different sequence*. Better sequence, usually — but different. If you compare genomes basecalled with different model versions, some of the differences you see are software, not biology. **Record the basecaller version alongside the sequence.** It belongs in the metadata as much as the sampling date does.

**2. Basecalling has a compute cost, and it is often the real bottleneck.** Super-accurate nanopore models need a GPU. A field laboratory with a laptop can run fast models in real time and must queue the accurate ones. This is a genuine constraint on decentralised sequencing, and it is why "high-performance computing systems in selected public health laboratories" appears in Africa CDC's Africa PGI investment list next to the sequencers themselves. Buying an instrument without buying the compute produces a laboratory that can generate signal and not genomes.

**3. Quality scores come from here.** The **Phred score** Q is defined as `Q = −10 × log₁₀(P_error)`:

| Q | Error probability | Meaning |
|---|---|---|
| Q10 | 1 in 10 | Poor |
| Q20 | 1 in 100 | Usable |
| Q23 | ~1 in 200 | Nanopore simplex, current chemistry |
| Q30 | 1 in 1,000 | Illumina standard; nanopore duplex |
| Q40 | 1 in 10,000 | Very high confidence |

✱ **Why per-read error matters much less than newcomers expect.** Errors are largely independent between reads. If a base is covered 100 times at Q20 (1% error each), the chance that a majority of reads agree on the *same wrong base* is negligible. **Depth converts mediocre reads into an excellent consensus.** This is why nanopore was usable for outbreak consensus genomes years before its per-read accuracy became competitive, and it is why minimum-depth thresholds (Lesson 5) are the load-bearing quality control, not read quality.

⚠ **The exception is systematic error.** If a platform makes the *same* mistake every time — homopolymer length, a specific context — depth does not save you, because all 100 reads are wrong identically. Systematic error is the reason platform-specific filters exist, and the reason a variant seen only on one platform deserves suspicion.

## Section 6 · Choosing a platform, honestly

| | Illumina (benchtop) | Nanopore (MinION/GridION) | PacBio | Sanger |
|---|---|---|---|---|
| Read length | 150–300 bp | Molecule-limited (kb–Mb) | 10–25 kb | ~800 bp |
| Per-read accuracy | Q30+ | Q23 simplex / ~Q30 duplex | Q30+ | Very high |
| Dominant error | Substitution | Indel in homopolymers | Low | Low |
| Latency | Run must finish | **Real-time** | Run must finish | Hours |
| Capital cost | ~$100k–$350k | ~$1k–$50k | High | Low, ubiquitous |
| Portability | No | **Yes** | No | No |
| Cold chain / power | Demanding | Tolerant | Demanding | Modest |
| Best at | Volume, bacterial WGS, deep amplicons | Outbreak response, field, long reads, closing genomes | Reference assemblies | Single targets |

### Four scenarios, four answers

- **Filovirus outbreak, provincial laboratory, 30 samples a day, answers needed this week.** Nanopore, amplicon, on site. Real-time output and small batches beat accuracy, and depth handles accuracy anyway. This is the Bundibugyo setup, and the ARTIC-lineage software stack exists for exactly it.
- **National *Salmonella*/*Listeria* surveillance, 3,000 isolates a year, cluster detection at 0–5 SNP resolution.** Illumina. You need per-base accuracy at scale and you can tolerate weekly batching. Add long reads selectively to close plasmids.
- **Undiagnosed severe illness, no hypothesis.** Metagenomics; nanopore if speed and adaptive sampling matter, Illumina if depth and sensitivity do. Expect to pay.
- **A national programme with unreliable power, no service engineer within 2,000 km, and a $60k budget.** Nanopore, and spend the difference on cold chain, connectivity and — above all — on people. An instrument nobody can service is a cupboard.

⚠ **The most common failure in national genomic surveillance procurement is buying throughput.** A high-throughput instrument is efficient only when saturated. Under-filled, it forces batching, which adds latency, which destroys the outbreak-response use case that justified the purchase. Match the instrument to the *arrival rate of samples*, not to the annual total.

## Practice

For a surveillance programme you know or can imagine, write the four numbers that actually determine platform choice, then pick:

1. Samples arriving per week (and how bursty).
2. Acceptable sample-to-answer time.
3. Genome size and whether repeats matter.
4. Available power, cold chain, compute and maintenance.

Then ask the question that decides it: *what happens on the day the machine breaks?*

## In one paragraph

Every sequencer converts a molecule into reads with confidence scores, and how it observes the molecule determines everything downstream. Illumina amplifies clusters and photographs one base at a time: short reads, superb per-base accuracy, huge throughput, and all of it arriving at the end of a run. Nanopore threads a single strand through a pore and reads the current with a neural network: molecule-length reads, real-time output, portability, and an accuracy that has closed most of the gap. Basecalling is where DNA literally becomes data, which means the basecaller version is part of your metadata and the compute to run it is part of your instrument. Per-read error matters far less than depth as long as the error is random; systematic error is the exception and the reason platform-specific filters exist. And the platform decision should be made from arrival rate, latency requirement and operating environment — never from throughput headline figures.
