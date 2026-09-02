# Lesson 6 — Naming things: clades, lineages, variants, sequence types, and the SNP threshold

> **Concept map**
> **Builds on** — Lesson 5: you have a consensus genome; now it needs a name a human can act on.
> **Connects to** — Lesson 7 (every name is a claim about a tree) and Lesson 12 (the SNP threshold is a cluster definition, i.e. a case definition).
> **Leads to** — Deep Dive 2 (mpox clade Ib) and Deep Dive 3 (H5N1 genotypes B3.13 and D1.1), where the names carry the whole argument.

## Why this matters

Naming is the interface between genomics and everybody else. A Minister does not act on a tree; they act on "clade Ib is circulating in this province". Every consequential communication in this field passes through a name.

And naming is where the field is at its messiest. Four different systems — clades, lineages, WHO labels, sequence types — overlap, use the same English words for different things, and change under you. Two failures follow, both common:

- **Over-reading a name.** "A new variant" is heard as "more dangerous". A lineage designation is a statement about *phylogenetic position*, and nothing else. Nothing about transmissibility, severity or immune escape is implied by the act of naming.
- **Under-reading a threshold.** "These isolates are within 5 SNPs, so they are one outbreak" sounds like a measurement. It is a **definition**, chosen for a pathogen and a context, with a sensitivity and specificity that someone should have estimated.

## Learning objectives
By the end of this lesson you will be able to:

- **Distinguish** clade, lineage, variant, genotype, serotype and sequence type, and say which are phylogenetic and which are phenotypic.
- **Read** a Pango lineage name, including aliasing, and say what it asserts.
- **Explain** MLST, cgMLST and SNP-distance typing, and when each is appropriate.
- **Critique** a SNP-threshold cluster definition by asking what its sensitivity and specificity are.

## Prerequisites
Lessons 0–5. Lesson 7 formalises what a tree is; this lesson survives without it.

---

## Section 1 · The vocabulary, sorted by what it actually claims

| Term | What it claims | Basis |
|---|---|---|
| **Clade** | A group on a tree consisting of an ancestor and *all* its descendants (monophyletic) | Phylogenetic |
| **Lineage** | A line of descent; in practice, a named clade meeting designation criteria | Phylogenetic |
| **Genotype** | A defined genetic constitution — sometimes a clade, sometimes a *combination* (e.g. influenza segment sets) | Genetic, not always phylogenetic |
| **Serotype / serovar** | An antigenic type detected by antibodies | **Phenotypic** — inferable from sequence, but originally a lab test |
| **Sequence type (ST)** | An allelic profile at a defined set of loci | Genetic, index-based |
| **Variant** | Anything from a single mutation to a WHO-labelled entity | **Ambiguous — always ask which** |
| **Strain** | Colloquial; an isolate, a lineage, or a lab stock | Avoid in technical writing |
| **Species** | A taxonomic rank. *Bundibugyo virus* is a distinct **species** within *Orthoebolavirus*, not a variant of Ebola virus | Taxonomic |

⚠ **"Variant" is the word that causes the most damage.** In a virology methods section it may mean a single nucleotide difference. In a press release it means a WHO-designated entity with epidemiological consequences. The same word, four orders of magnitude apart in importance. When you write, say "mutation", "lineage" or "WHO variant of concern", and never "variant" alone.

✱ And note the row that resolves a common confusion in the flagship study: **Bundibugyo virus is a different species from Ebola virus**, not a variant of it. That is why there is no licensed vaccine or specific therapeutic for it while there are for Zaire ebolavirus — the ERVEBO vaccine and the licensed monoclonals target Zaire, and Bundibugyo is far enough away that cross-protection cannot be assumed. A taxonomic distinction with a body count.

## Section 2 · Viral nomenclature

### Nextstrain clades
Broad, coarse groupings named for practical communication ("clade 2.3.4.4b" for H5N1, "clade Ib" for mpox). Deliberately few, deliberately stable. Designed so that a public health audience can hold the set in their head.

### Pango lineages (SARS-CoV-2, and the model others copy)
Fine-grained, dynamic, rule-based. A lineage is designated when a group is monophyletic, shows evidence of onward transmission, and is epidemiologically distinct.

- Names are hierarchical and dot-separated: `B.1.1.7`, `BA.2.86`.
- When a name exceeds three levels it is **aliased**: `B.1.1.529.2` became `BA.2`, and `BA.2.75.3.4.1.1.1.1.1.1` became `XBB`'s parent lineage `BJ.1`-style shorthand. **The alias is the same lineage with a shorter label**, and alias tables are how software resolves them.
- Recombinants get an `X` prefix — `XBB` is a recombinant of two BA.2 sublineages.

**What a Pango name asserts:** that this sequence sits inside a defined clade. Nothing else.

### WHO labels
Variant of Interest / Variant of Concern, plus Greek letters. **These are risk-assessment labels, not phylogenetic ones.** They are assigned by a committee weighing transmissibility, severity, immune escape and diagnostic impact. Alpha and Delta were WHO labels wrapped around Pango lineages; the two systems answer different questions and it is legitimate for a lineage to grow fast without ever earning a WHO label.

### Mpox
Clade I and clade II, subdivided into Ia, Ib, IIa, IIb, with lineages beneath (e.g. the 2025 Sierra Leone outbreak lineage **G.1** within clade IIb). **Clade Ib is the entity that drove the 2024 PHEIC**, and its designation was a genomic finding: a distinct clade I lineage showing sustained human-to-human transmission in eastern DRC, marked by APOBEC3 signature mutations and a large deletion. Deep Dive 2.

### Influenza — where naming gets genuinely hard
Because influenza reassorts, you need several names at once:

- **Subtype:** H5N1 — the two surface proteins.
- **HA clade:** 2.3.4.4b — a clade of the haemagglutinin gene tree specifically.
- **Genotype:** B3.13, D1.1 — a *combination* of lineages across all eight segments.

The H5N1 cattle story turns on that last distinction: a single spillover of **genotype B3.13** into US dairy cattle in late 2023, and then in January 2025 a separate introduction of **genotype D1.1**. Both are H5N1 clade 2.3.4.4b. The subtype name cannot express the difference; the genotype name is the whole finding. Deep Dive 3.

### Nextclade — the practical tool
A browser or command-line tool that takes your consensus sequences and returns: placement on a reference tree, clade/lineage assignment, the mutation list relative to reference, and a set of QC flags (too many Ns, too many private mutations, clustered differences, stop codons).

✱ **Its QC flags are worth as much as its clade calls.** "Excess private mutations" and "clustered differences" are exactly the signatures of contamination, co-infection and the editing artefacts from Lesson 2. Running Nextclade as a quality gate before phylogenetics is cheap and catches a lot.

## Section 3 · Bacterial nomenclature — a different logic

Bacterial genomes are large, and a substantial fraction is **accessory**: present in some isolates, absent in others, moving on plasmids. So bacterial typing is built on **defined loci** rather than whole-genome alignment.

### MLST — 7 genes
Sequence seven housekeeping genes. Each distinct allele at each locus gets an integer. The seven integers are an **allelic profile**, and each unique profile is a **sequence type (ST)**.

- Portable, database-backed, comparable across decades and laboratories — this is its enduring virtue.
- Far too coarse for outbreak investigation: thousands of unrelated isolates share an ST.

### cgMLST — hundreds to thousands of genes
The same idea applied to the **core genome** — the loci present in essentially all members of the species. Pathogenwatch provides MLST for 37+ bacterial species and cgMLST schemes for 20+ priority organisms, contextualised against a large curated public collection.

- **Allele-based, so a single SNP and a whole recombined block both count as "one allele difference".** That is a feature: it stops recombination from inflating distances.
- Scheme-dependent and therefore only comparable within a scheme.
- Underpins routine foodborne surveillance (PulseNet and equivalents).

### SNP-distance typing
Map isolates to a reference, count differing positions, cluster on distance.

- Higher resolution than cgMLST for closely related isolates.
- **Requires masking** of recombinant regions, repeats and resistance loci, or a single recombination event contributes dozens of SNPs and shatters a real cluster.
- Reference-dependent: change the reference, change the distances.

## Section 4 · The SNP threshold is a case definition

Here is the sentence to take from this lesson.

> **"Isolates within N SNPs belong to the same cluster" is not a measurement. It is a case definition, and it has a sensitivity and a specificity, and someone should have estimated them.**

Thresholds vary by pathogen because evolutionary rates vary (Lesson 1). Commonly used values — TB at ~5 SNPs for recent transmission and ~12 for a broader cluster, *Listeria* and *Salmonella* at very small allele differences — are conventions derived from studies of known epidemiological links, not constants of nature.

**How to interrogate any threshold, in four questions:**

1. **What is the background diversity?** If unlinked isolates in this setting routinely sit 3 SNPs apart, a 5-SNP threshold has terrible specificity. The threshold is meaningless without the background distribution, and the background distribution is local.
2. **Over what time window?** At 0.5 SNPs/genome/year, 5 SNPs is a decade of TB evolution. A threshold tuned for a two-year study is wrong for a twenty-year one.
3. **What was it validated against?** Ideally against epidemiologically confirmed links, with sensitivity and specificity reported. Usually against nothing.
4. **What happens either side of it?** A pair at N+1 SNPs is not qualitatively different from a pair at N. Thresholds create hard edges in a continuous quantity, and near the edge the classification is arbitrary. Report distances, not just cluster membership.

⚠ **The threshold has direct operational consequences.** Too tight: real clusters fragment, outbreaks are missed, transmission is called "sporadic". Too loose: unrelated cases are merged, investigators chase links that do not exist, and the public receives a larger outbreak than exists. This is a classic sensitivity–specificity trade-off and it should be made explicitly, by the people who bear the consequences of each error, and written down.

## Section 5 · When names go wrong

**Naming ahead of evidence.** A lineage designated on three sequences from one laboratory is a hypothesis. Under media attention it becomes a fact.

**Name inflation.** A growing lineage gets a name; a name implies importance; importance implies a phenotype nobody measured. Break the chain at the third step, every time, out loud.

**Nomenclature drift.** Schemes are revised, lineages are merged or split, aliases change. **Record the version of the nomenclature and the tool alongside the call.** "Pango lineage BA.2.86 (pangolin v4.3, pangoLEARN 2023-11-30)" is reproducible; "BA.2.86" is not.

**Sampling-driven "emergence".** A lineage appears to rise because a country started sequencing, or changed its sampling frame. Lesson 13.

**Cross-system confusion.** "Clade Ib" (Nextstrain-style clade, mpox) and "B.1.1.7" (Pango lineage, SARS-CoV-2) and "ST131" (MLST, *E. coli*) are three different kinds of object. People say "strain" for all three and lose the distinction.

## Practice

Take three recent news items about a "new variant". For each:

1. Identify which naming system the name comes from.
2. State exactly what the name asserts phylogenetically.
3. State what phenotypic claim is being made, and what evidence supports it.
4. Note whether steps 2 and 3 are the same claim. They usually are not, and the gap between them is the story.

## In one paragraph

Naming is where genomics meets everyone else, and four overlapping systems make it treacherous. Clades and lineages are phylogenetic claims — a position on a tree and nothing more; WHO labels are risk assessments made by a committee; serotypes are phenotypes; sequence types and cgMLST profiles are allelic indices designed to survive recombination. Influenza needs three names at once because it reassorts, which is why the H5N1 cattle story is told in genotypes rather than subtypes. And the SNP threshold that defines an outbreak cluster is not a measurement but a case definition with a sensitivity, a specificity and a local background distribution that someone should have estimated — because setting it too tight fragments real outbreaks and setting it too loose invents them.
