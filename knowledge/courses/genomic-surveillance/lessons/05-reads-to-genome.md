# Lesson 5 — Reads to genome: the bioinformatics chain, and the four thresholds that decide your dataset

> **Concept map**
> **Builds on** — Lesson 3 (every artefact created at the bench arrives here) and Lesson 4 (the error profile determines the filters).
> **Connects to** — Lesson 2 (this is where within-host diversity is discarded) and Lesson 13 (QC thresholds are sampling decisions).
> **Leads to** — Lesson 6, where the finished genome gets a name.

## Why this matters

The bioinformatics chain looks like a technical pipeline you either run correctly or incorrectly. It is not. It contains **four numerical thresholds**, each of which is set by a human, each of which changes which cases end up in your final dataset, and none of which is usually reported in enough detail to reproduce:

1. The minimum read depth to call a base.
2. The frequency at which a minority base becomes the consensus.
3. The maximum fraction of Ns a genome may contain and still be included.
4. The distance beyond which a sequence is called an outlier and dropped.

Every one of these has the same structural bias: **they preferentially remove samples with low pathogen load, which are the same samples that came from late presenters, milder cases, degraded specimens and remote health zones.** The Ct threshold at the bench (Lesson 3) selects once; these thresholds select again, in the same direction. By the time you have a final alignment, you have applied a compound filter that nobody has quantified.

This lesson is the chain, and then those four thresholds treated as what they are: epidemiological decisions.

## Learning objectives
By the end of this lesson you will be able to:

- **Name** the file formats in the chain and say what information each one holds and loses.
- **Distinguish** reference mapping from de novo assembly and choose between them.
- **Explain** primer trimming and predict what happens when it is omitted.
- **Interpret** depth and breadth of coverage, and justify a minimum-depth threshold.
- **State**, for a given QC threshold, which cases it removes and in which direction that biases inference.

## Prerequisites
Lessons 0–4. No command-line experience needed; tool names are given so you recognise them in methods sections, not so you run them today.

---

## Section 1 · The formats, and what each one throws away

Data loses information at every step. Knowing what each format still contains tells you which questions are still answerable.

**FASTQ** — the sequencer's output. Four lines per read: an identifier, the bases, a separator, and a per-base quality string.

```
@read_00417
ACGTTGCAAGCTTACGGATCAGGTTACAG
+
IIIIIIIIIHHHHGGGFFFEEDDCCBA@?      ← ASCII-encoded Phred scores
```

Contains: every read, every base, every quality. Loses: the raw signal. (For nanopore, the raw signal is kept separately as POD5 if you want to re-basecall later — and Lesson 4 says you might.)

**BAM / SAM** — reads after alignment to a reference, with their positions, mapping quality and mismatches. Contains: everything in FASTQ plus where each read went. **This is the file that still holds within-host diversity.** If you keep only consensus FASTAs, minority variants are gone forever.

**VCF** — the differences from the reference: positions, alleles, frequencies, depths. Compact and precise. Loses everything about positions that match.

**FASTA (consensus)** — one sequence per sample. The object everything downstream uses. Has thrown away depth, quality, read support and all minority variation. **N** marks positions that could not be called.

**BED** — coordinate intervals. Used for primer schemes and masking.

⚠ **Practical consequence:** a surveillance programme that archives only consensus FASTAs can never retrospectively answer a within-host question — mixed infection, minority resistance, transmission bottleneck. Archiving BAMs or FASTQs costs storage and preserves optionality. This is a policy decision made once, usually by default, and regretted later.

## Section 2 · Quality control on reads

Before anything else:

- **Adapter trimming.** Short fragments get read into the adapter; those bases are synthetic and must go. (`fastp`, `trimmomatic`, `cutadapt`.)
- **Quality trimming.** Illumina reads degrade at the 3′ end; trim where quality falls.
- **Length filtering.** Reads far shorter or longer than the expected amplicon are usually chimeras or junk.
- **Host read removal.** Map against the human genome and discard what sticks. Essential for metagenomics, and an ethical requirement as much as a technical one — human reads in a pathogen dataset are identifiable human genetic data, and uploading them is a data-protection incident. (See Lesson 14.)
- **Overall read QC.** `FastQC` / `MultiQC` to see the run at a glance.

## Section 3 · Reference mapping versus de novo assembly

Two ways to get from reads to a genome.

### Reference mapping
Align every read to a known reference genome, then read off the consensus.

- **Fast, robust at low coverage, works with fragmented data.** The standard for viral surveillance.
- Tools: `minimap2` (the default for long reads and increasingly for everything), `bwa-mem`, `bowtie2`.
- **The bias:** you can only see what maps. Large insertions absent from the reference, or highly divergent regions, are invisible or misassembled. Choosing a reference that is distant from your samples degrades everything quietly.

### De novo assembly
Reconstruct the genome from overlaps between reads, with no reference.

- **Necessary for bacteria** (accessory genome, plasmids, insertion sequences all vary between isolates and are not in any single reference) and **for anything genuinely novel**.
- Tools: `SPAdes`/`shovill`/`unicycler` (short read), `Flye` (long read), hybrid approaches for both.
- Then: `QUAST` for assembly metrics, `CheckM` for completeness/contamination, `kraken2` for species identity, `prokka`/`bakta` for annotation.
- **The bias:** repeats break assemblies. Short reads cannot span them, so you get contigs, not a chromosome. This is the single strongest argument for long reads in bacterial work.

**Rule of thumb:** virus with a good reference and amplicon data → map. Bacterium, or novel agent, or you care about plasmids and structural variation → assemble.

## Section 4 · Primer trimming — the step that is skipped

If your data came from a tiling amplicon scheme (Lesson 3), each read begins and ends in **primer sequence**, not patient sequence. Primers were synthesised from the *reference*. So if the patient's virus has a mutation under a primer, the primer's reference base is physically present in the read.

Leave it in and the consensus reports the reference base. **You have manufactured a reversion to reference at exactly the variable position you cared about.**

Trimming uses the scheme's BED file to remove primer regions from aligned reads — `align_trim` in the ARTIC toolchain, `ivar trim`, `samtools ampliconclip`. It is not optional, it is not automatic in every pipeline, and its omission has put spurious reversions into public databases.

✱ Two related amplicon pathologies to recognise:

- **Amplicon dropout:** a mutation under a primer kills amplification, producing a coverage hole and a run of Ns. Note the direction of the loss: **you lose data precisely where the virus changed.**
- **Amplicon imbalance:** amplicons amplify unequally, so coverage is spiky. Some regions have 5,000× and some have 12×. A single depth threshold applied across a spiky profile masks entire amplicons.

## Section 5 · Depth, breadth, and the consensus

Two different words, constantly confused:

- **Depth** = how many reads cover a given position. "500× at position 4,412."
- **Breadth (coverage / completeness)** = what fraction of the genome is covered at or above your depth threshold. "97.4% of the genome at ≥20×."

**Consensus calling**, position by position:

1. Is depth ≥ the minimum threshold? If not → **N**.
2. If yes, what fraction of reads support each base?
3. If one base exceeds the consensus frequency threshold → call it.
4. If no base does (a genuine mixture) → call an **ambiguity code** (R = A/G, Y = C/T, etc.) or N, depending on the pipeline.

### The four thresholds, and what they do to your epidemiology

**(1) Minimum depth — commonly 10× or 20×.** Too low and single-read errors become consensus bases: you invent mutations, inflate the apparent evolutionary rate, and create phantom diversity. Too high and low-load samples fill with Ns and get dropped. The threshold trades *false mutations* against *lost cases*, and the lost cases are systematically the high-Ct ones.

**(2) Consensus frequency threshold — commonly 0.5 to 0.75.** Where does a minority base take over? At 0.5, a 51/49 split flips the consensus and serial samples from one patient appear to "mutate" between visits. At 0.75 you get more ambiguity codes and fewer phantom changes. Neither is right; the choice should follow the question.

**(3) Maximum N fraction for inclusion — commonly 5–10%.** Genomes below the completeness bar are excluded. This is the biggest single filter in most datasets, and it is a straight function of viral load. **It removes the same people the Ct threshold removed, again.**

**(4) Outlier distance.** Lesson 2, Section 5 — and, in the Bundibugyo analysis, ±2 SD from the root-to-tip regression, applied iteratively.

⚠ **Compound selection is the thing to internalise.** Take a hypothetical but entirely ordinary cascade: 100 cases → 78 with a sample → 60 PCR-positive at Ct < 31 → 52 producing ≥90% genome coverage → 49 surviving outlier filtering. **You are now analysing half your cases, and the missing half is not missing at random.** Every phylogeographic and phylodynamic statement in Lessons 10–12 is conditional on that cascade, and the cascade is almost never drawn.

✱ **This is the most useful figure you can add to a genomic surveillance paper, and almost nobody includes it: a flow diagram from cases to analysed genomes, with the reason for each loss.** It costs one panel and it converts unstated bias into stated bias.

## Section 6 · Pipelines, and why they are named in methods

Nobody assembles these steps by hand any more. Standard pipelines:

- **`amplicon-nf`** (ARTIC Network) — Nextflow pipeline for ARTIC-style amplicon schemes: reads in, consensus out, with QC. **Used at v2 for the 2026 Bundibugyo genomes.**
- **`artic fieldbioinformatics`** — the Python ancestor of the above, originally written for Ebola virus sequencing in West Africa, designed to run on a laptop in a field lab.
- **`nf-core/viralrecon`** — a broader community pipeline for viral amplicon and metagenomic data, Illumina and nanopore.
- Bacterial equivalents: `nf-core/bactmap`, `bactopia`, national systems like IRIDA.

Two reasons pipelines matter beyond convenience:

**Reproducibility.** A pipeline pins tool versions in containers, so "we ran amplicon-nf v2" is a far more reproducible statement than a list of six tools with no versions. Since the basecaller version alone can change your genomes (Lesson 4), version pinning is not bureaucracy.

**Consistency across sites.** In a multi-country outbreak, genomes from different laboratories processed with different thresholds are not comparable — the differences you see between countries may be differences between pipelines. Shared pipelines are how networks like Africa PGI make their data poolable.

## Section 7 · Contamination, and how to catch it

Contamination is the great destroyer of Q1 (linkage) claims, because it makes unrelated samples look identical — which is exactly the signal an outbreak investigation is looking for.

Detection, in rough order of usefulness:

1. **Negative controls with reads in them.** The single strongest signal. Any pipeline should report reads-in-negatives prominently rather than burying it.
2. **Unexpected heterozygosity.** A haploid pathogen showing many positions at ~50% is a mixture — of two infections, or of two samples.
3. **Impossible identity.** Two samples from distant health zones with zero differences, when the local background diversity says that should be rare.
4. **Batch structure in the tree.** If the tree clusters by sequencing run rather than by geography or date, you are looking at a laboratory artefact. **Always colour a tree by sequencing batch at least once.** It takes a minute and it has saved entire studies.

## Practice

Open the methods of a viral genomic surveillance paper and find, or fail to find:

1. The pipeline and version.
2. The minimum depth for a base call.
3. The genome completeness threshold for inclusion.
4. Whether primer trimming was performed.
5. The number of samples entering and leaving each stage.

Then draw the cascade from cases to analysed genomes. In most papers you will not be able to complete it. That incompleteness is the review comment, and it is a more substantive one than anything about the choice of substitution model.

## In one paragraph

The chain from reads to genome is FASTQ → QC → mapping or assembly → primer trimming → depth-thresholded consensus → FASTA, and each format discards information the next step can never recover — most importantly, the consensus discards within-host diversity, so archiving only FASTAs forecloses a class of questions permanently. Primer trimming prevents manufactured reversions to reference, and amplicon dropout removes data exactly where the pathogen changed. The four thresholds — minimum depth, consensus frequency, maximum N fraction, outlier distance — are set by humans and all push the same way, removing low-load samples that came disproportionately from late presenters and remote areas. Draw the cascade from cases to analysed genomes with a reason for each loss, and you have converted an unstated bias into a stated one, which is the whole job.
