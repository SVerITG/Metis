# Lesson 12 — Clusters, transmission and the language of genomic evidence

> **Concept map**
> **Builds on** — Lesson 7 (the transmission tree is not the phylogenetic tree) and Lesson 6 (the SNP threshold is a case definition).
> **Connects to** — Lesson 15, where these statements become decisions.
> **Leads to** — the sentence you will actually write in an outbreak report.

## Why this matters

Everything so far has been about producing evidence. This lesson is about **what you are entitled to say**, which is a different skill and the one that most often fails in practice.

The failure has a signature. An investigator asks "are these two cases linked?". The bioinformatician answers "they're identical". Somebody writes "genomic analysis confirmed transmission between case 14 and case 17". A month later a contact investigation finds no plausible contact, and the genomic evidence is quietly discredited — when in fact the genomic evidence was fine and the *sentence* was wrong.

This lesson gives you the sentences: what genomic data can support, what it can only be consistent with, and how to say the difference in a way that survives contact with an incident management team.

## Learning objectives
By the end of this lesson you will be able to:

- **Formulate** genomic conclusions in the three permitted strengths: excludes, is consistent with, cannot distinguish.
- **Combine** genomic and epidemiological evidence so each covers the other's blind spot.
- **Explain** what transmission-tree inference software does and what its output is.
- **Distinguish** relapse from reinfection, and importation from residual transmission, using genomic evidence.
- **Recognise** when a genomic cluster is a laboratory artefact.

## Prerequisites
Lessons 0–11.

---

## Section 1 · The three strengths of genomic statement

Genomic evidence about linkage comes in exactly three strengths. Learn to place every claim into one of them, and to refuse claims that fit none.

### Strength 1 — **Exclusion.** The strong one.
> *"These isolates differ by 27 SNPs. Given a rate of ~16 substitutions per genome per year, that is inconsistent with direct transmission within the outbreak period. These cases are not directly linked."*

This is the most robust thing genomics does. It requires a large distance and a known evolutionary rate, and it is robust to incomplete sampling — unsampled intermediates would make the distance larger, not smaller. **A negative genomic result is a real result and it is routinely the most useful.** It closes lines of investigation, which is how investigations finish.

### Strength 2 — **Consistency.** The honest middle.
> *"These isolates are identical. This is consistent with direct transmission, and equally consistent with a short chain through unsampled cases or with two infections from a common source."*

Almost every "positive" genomic linkage finding lives here. With under one substitution per transmission (Lesson 1), identity carries little discriminating power. Consistency becomes useful when combined with epidemiology (Section 2) — and only then.

### Strength 3 — **Indeterminacy.** The one people skip.
> *"Coverage in this sample was 71%, and the differentiating positions fall in a dropout region. These sequences cannot be compared at the resolution required."*

Say it. A genomic analysis that cannot answer the question should report that it cannot, rather than producing a low-confidence answer that will be quoted at full confidence.

⚠ **The word "confirmed" should almost never appear in a genomic linkage statement.** Genomics confirms exclusions. It supports, is consistent with, or fails to exclude everything else.

## Section 2 · Genomics plus epidemiology: why the pair is stronger than either

The two evidence types have complementary blind spots, and used together they do something neither can do alone.

|  | Epidemiological link | No epidemiological link |
|---|---|---|
| **Genomically compatible** (small distance) | **Strong support for transmission.** Two independent lines agree. | **A hypothesis to chase.** Either an unrecognised contact, an unsampled intermediate, or a shared source nobody has identified. Often the most productive cell in the table. |
| **Genomically excluded** (large distance) | **Reject the epidemiological link.** The contact was real; the transmission was not. Look for the other source. | **Consistent absence.** Both agree these are unrelated. |

✱ **The top-right cell is where genomic surveillance earns its budget.** Cases with no known contact that are genomically compatible point at a missing piece of the transmission network — an unrecognised setting, an asymptomatic chain, a shared exposure. In hospital outbreak investigation this is the routine finding: sequencing reveals transmission between patients who were never on the ward at the same time, and the investigation then finds the shared equipment, the shared staff member, or the environmental reservoir.

**The bottom-left cell prevents harm.** A plausible epidemiological link that genomics excludes stops an investigation from closing on the wrong answer — and in a nosocomial context, stops a clinician being wrongly identified as a source.

## Section 3 · Genomic clusters, and how to define one defensibly

A **genomic cluster** is a set of isolates within some genetic distance of each other. Three components, each a decision:

1. **The distance metric.** SNP distance from a mapped alignment, cgMLST allele differences, or patristic distance on the tree. Not interchangeable, and not comparable across studies that chose differently.
2. **The threshold.** Lesson 6. A case definition, with sensitivity and specificity that should be estimated against known links.
3. **The linkage rule.** Single-linkage (any isolate within N of any cluster member joins) chains clusters together and grows them without limit. Complete-linkage (all pairs within N) is conservative and fragments. Almost nobody states which they used, and the choice materially changes cluster sizes.

**Add a time window.** Genetic distance ignores time, so a 2018 isolate and a 2026 isolate within 4 SNPs will cluster — which is informative about a persistent lineage and not informative about current transmission. Most operational definitions therefore pair a distance threshold with a recency window.

### The artefact check, before anything else
Before treating a cluster as epidemiological:

- Were these samples **sequenced in the same run**? (Lesson 5 — colour the tree by batch.)
- Do the **negative controls** from those runs have reads?
- Is the cluster defined by variants in a **low-coverage or dropout region**?
- Are the isolates **implausibly identical** given the local background diversity?

A laboratory cluster and a transmission cluster look identical in the data and completely different in what you do about them.

## Section 4 · Transmission tree inference, honestly

Software exists to infer who infected whom — `TransPhylo`, `outbreaker2`, `phybreak`, and relatives. They combine the phylogeny with epidemiological priors: generation time distribution, sampling proportion, within-host coalescent dynamics.

**What they do:** produce a **posterior distribution over transmission trees**, accommodating unsampled intermediates by inferring how many there probably were.

**What they are good for:**

- Estimating the **fraction of transmission that is unobserved**, which is a system-performance measure.
- Estimating the **offspring distribution** and hence overdispersion — how much of transmission is superspreading. This has direct policy consequences: highly overdispersed transmission means targeting settings is more efficient than population-wide measures.
- Bounding **how many links are missing** from a contact-tracing dataset.

**What they are not good for:** naming individuals. The posterior probability that person A infected person B is usually low even in the best-supported cases, because the data genuinely do not determine it.

⚠ **Presenting the single highest-posterior transmission tree as "the" transmission tree is a misuse of the method.** The method's whole output is the spread of the posterior. If you must show one tree, show the uncertainty on it — and never attach names in a public document. Individual-level transmission attribution is also an ethical problem, not only a statistical one: in HIV, TB and outbreak settings it can expose people to blame, stigma, and in some jurisdictions prosecution. Several national programmes have explicit policies forbidding individual-level attribution from cluster analysis for exactly this reason.

## Section 5 · Four questions genomics answers well

### 1. Relapse or reinfection?
Two episodes in one patient. Are they the same infection returning, or a new one?

- **Same or near-identical genome** → relapse: the original infection persisted and regrew.
- **Genetically distant genome** → reinfection with a different strain.

This has been settled with whole-genome sequencing in **gambiense HAT**, where sequencing of parasites from relapsed patients showed that relapse was due to **regrowth of the original parasite population, not reinfection** — which is a statement about drug efficacy and follow-up duration, not about ongoing transmission, and it changes what you do. The same design applies to TB (relapse versus reinfection, with direct implications for regimen versus exposure) and to malaria (recrudescence versus new infection, the standard genotyping endpoint in every antimalarial efficacy trial).

✱ Note the elegance of this design: it needs only two samples from one person, and the comparison is internal. It sidesteps every sampling-fraction problem in this course.

### 2. Importation or residual transmission?
A case appears in an area declared free of the disease.

- **Genome falls within the local historical lineage** → residual, undetected local transmission.
- **Genome clusters with sequences from elsewhere** → importation.

This is the standard measles, polio and cholera analysis, and it is the question that will matter most for HAT as districts approach and pass elimination thresholds: a case in a "cleared" focus is either a failure of elimination or an import, and those demand entirely different responses. **The prerequisite is a historical sequence archive**, which is why archiving isolates now, before elimination, is a decision that pays off years later. A programme that reaches elimination without a genomic baseline cannot answer this question at the moment it becomes the only question.

### 3. Persistence and flare-ups
Ebola survivors can harbour virus in immune-privileged sites for months, and sexual transmission from survivors has restarted chains after the end of an outbreak. The genomic signature is distinctive: **a new case whose genome attaches to an old part of the tree on a long branch**, sometimes with an unusually low apparent evolutionary rate (virus replicating slowly in a persistent site). Recognising this pattern changes the response from "new introduction, find the animal source" to "survivor-associated transmission, engage survivor care programmes" — two entirely different operations.

### 4. Contamination and pseudo-outbreaks
A hospital "outbreak" of identical isolates that turns out to be a contaminated reagent, a colonised piece of equipment, or laboratory cross-contamination. Genomics finds these routinely, and finding them is a public health service — a pseudo-outbreak consumes response capacity and can lead to ward closures with real costs.

## Section 6 · The sentences

Take these into your next outbreak report.

**Exclusion**
> "Isolates from cases 14 and 17 differ by 27 nucleotide substitutions. Given the estimated evolutionary rate of 16 substitutions per genome per year, this is inconsistent with direct transmission during the outbreak period. A direct link between these cases is excluded."

**Consistency, with epidemiology**
> "Isolates from cases 22 and 23 are identical. In isolation this is consistent with direct transmission and with transmission through unsampled intermediates. Together with the documented shared exposure on 12 June, the combined evidence supports a transmission link, though the direction cannot be determined from sequence data."

**Consistency, without epidemiology**
> "Five isolates from three health zones are within one substitution of each other, with no identified epidemiological connection. This is consistent with a transmission chain passing through unsampled cases and warrants targeted investigation in the intervening area. It does not establish direct links between the sampled cases."

**Indeterminacy**
> "Genome coverage for case 31 was 71%, with dropout across the region containing the differentiating positions. This sample cannot be placed relative to the cluster at the required resolution."

**Cluster with its definition attached**
> "Cluster A comprises 14 isolates within 5 SNPs of one another (single linkage, masked alignment, sampled within a 90-day window). Background pairwise distance among contemporaneous unlinked isolates in this setting is 18 SNPs (IQR 12–26), so the cluster is unlikely to have arisen by chance."

That last one is the model. **It states the threshold, the linkage rule, the time window, and the background distribution against which the threshold means anything.** Most published cluster definitions state one of the four.

## Practice

Take a real or imagined outbreak investigation with sequences and, for each pair of cases, place the genomic evidence into one of the three strengths and write the sentence. Then check each sentence for: the word "confirmed" (delete it unless it is an exclusion), an implied direction of transmission (sequence data rarely gives direction), and whether the sampling fraction is stated.

## In one paragraph

Genomic evidence about transmission comes in three strengths — exclusion, consistency and indeterminacy — and only the first is strong, which is why negative genomic findings are routinely the most useful thing sequencing produces. Combined with epidemiology it becomes far more powerful, and the most productive combination is the one people find awkward: cases with no known contact whose genomes are compatible, pointing at the part of the network nobody has seen. Cluster definitions need a metric, a threshold, a linkage rule, a time window and a local background distribution, and almost none state all five. Transmission-tree software returns a posterior over trees and is legitimate for measuring unobserved transmission and overdispersion, not for naming who infected whom. And the highest-value routine applications — relapse versus reinfection, importation versus residual transmission, survivor-associated flare-ups — are the ones where the genomic comparison is internal and the sampling-fraction problems that dominate the rest of this course simply do not arise.
