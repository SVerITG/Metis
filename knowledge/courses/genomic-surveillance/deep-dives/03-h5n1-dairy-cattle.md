# Deep Dive 3 — H5N1 in dairy cattle: one spillover, then two, and what a genotype name carries

> **The case.** A single cross-species jump, established by phylogenetics, that reorganised the entire response to an animal-health emergency — and then a second, independent jump fourteen months later that showed the first conclusion had been a description of the past, not a guarantee about the future.

---

## 1 · The question someone actually asked

In March 2024, US dairy herds began reporting an illness in lactating cows: reduced milk production, thickened milk, lethargy. Highly pathogenic avian influenza A(H5N1) was confirmed — in cattle, a host in which HPAI was not an established problem.

The immediate operational question was not "is this H5N1". It was:

> **Is this one introduction spreading between cattle, or many independent introductions from wild birds?**

These demand opposite responses. **Many introductions from birds** → the exposure is environmental, control means biosecurity against wild birds at every farm, and the number of affected herds tracks bird migration. **One introduction spreading cow-to-cow** → the virus has adapted to a new mammalian host, control means movement restrictions and herd-level quarantine, and the number of affected herds tracks the cattle trade.

Only genomics could distinguish them, and quickly.

## 2 · The method: phylogeography with hosts instead of places

Lesson 11, with "host species" substituted for "location". Reconstruct ancestral host states on the tree and count cross-species transitions.

The logic is clean:

- **Repeated independent spillovers** → cattle sequences scattered across the bird phylogeny, each nested among bird sequences, each with its own recent bird ancestor.
- **A single spillover with onward transmission** → cattle sequences forming **one monophyletic clade** descending from a single bird-derived ancestor.

The published finding, from combined epidemiological information and genomic analysis: **a single spillover of the reassorted HPAI H5N1 genotype B3.13 virus into dairy cattle**, with cattle sequences clustering within a single group, supporting a single introduction in **late 2023** — months before the March 2024 detection. The tMRCA-to-detection gap again (Lesson 9), in an animal-health system this time.

### Why a genotype name and not a subtype name

Influenza has **eight separate genome segments** that reassort (Lesson 1). So the virus does not have one phylogeny; it has eight, and they can disagree.

- **H5N1** names two surface proteins. Thousands of distinct viruses share it.
- **Clade 2.3.4.4b** names a clade of the haemagglutinin gene tree only.
- **Genotype B3.13** names a **specific combination of lineages across all eight segments** — a particular reassortant.

The finding is only expressible at genotype resolution. "H5N1 spilled into cattle" is compatible with a hundred separate events. "**Genotype B3.13** spilled into cattle, once" is a claim about a specific reassortant and its descendants. **Lesson 6's point about naming systems, with an epidemiological conclusion resting entirely on it.**

## 3 · What followed: adaptation, spread, and spillback

**Adaptation.** Cattle B3.13 viruses rapidly accumulated changes in the polymerase genes that improved replication in bovine cells and in cells of other mammals including humans. **PB2 M631L is found in all cattle sequences; PA K497R in the majority.** Polymerase adaptation is one of the classic mammalian-adaptation routes for avian influenza, and finding it fixed across the cattle clade is a Q4 finding of the first importance.

⚠ **And it is a Q4 finding of the specific kind Lesson 0 warned about: a mutation is a hypothesis about a phenotype.** The inference that these substitutions matter rests on experimental work in cells and animals, not on their presence in a tree. The genomic surveillance identified them; separate science established what they do. Both were needed.

**Spread.** The virus disseminated across the US through movement of asymptomatic or presymptomatic animals — a mechanism the phylogeny reveals directly, because sequences from distant states sit adjacent on the tree in a pattern that migration of birds cannot produce and the cattle trade can. By June 2025, over **1,000 infected herds across 17 states**.

**Spillback.** Sequences show lineages exiting the cattle clade into other species — poultry, peridomestic mammals, cats — and into humans. Cattle became a source rather than only a sink, which is a change in the risk assessment, not a detail.

**And then the second introduction.** In **January 2025** a distinct genotype, **D1.1**, caused a second and independent spillover into dairy cattle — an unprecedented situation of two distinct viruses entering the same new host within a limited period.

✱ **This is the methodological punchline of the deep dive.** The single-spillover finding was correct and it was a statement about the past. It did not, and could not, mean that further spillovers would not occur. **Phylogenetic reconstructions describe what happened; they do not bound what will happen.** A response that read "one spillover" as "spillover is rare" read it wrong. Continued genomic surveillance is what detected the second event — and a programme that had stood down after establishing the first would have missed it entirely.

## 4 · What it is actually worth

**High and demonstrable.** The single-spillover finding redirected the response from environmental biosecurity to cattle movement control, within weeks, on evidence that no other method could have produced at that speed. That is a Lesson 15 "decision changed", cleanly attributable.

**With a caveat that generalises.** The finding depends on the completeness of bird sequencing. Under-sampling of the wild bird reservoir would make multiple similar introductions look like one clade — the Lesson 11 sampling problem, in host space. Wild bird surveillance is substantially less dense than the cattle response sequencing became, so the single-introduction conclusion is better read as "**one dominant introduction that established, plus any that did not establish or were not sampled**".

**A One Health lesson about institutions, not biology.** The animal-health, food-safety and human-health surveillance systems that had to combine here sit in different agencies with different reporting obligations, different data systems and different legal bases for sharing. The genomics was, comparatively, the easy part. Deep Dive 1's data-sharing questions (Lesson 14) recur here in a form nobody has solved.

## 5 · Transferable lessons

1. **Host-state reconstruction is phylogeography.** One clade = one jump; several scattered = several jumps. The logic transfers to any reservoir question, including *T. b. gambiense* in animals.
2. **The name must be at the resolution of the finding.** Subtype could not express this; genotype could. Check that a claim's naming system can carry its claim.
3. **A phylogenetic reconstruction describes the past.** "One spillover" was true and was not a forecast.
4. **Sampling of the *source* population bounds the conclusion.** Sparse bird sequencing makes multiple introductions collapse into one apparent clade.
5. **Adaptation markers are hypotheses.** PB2 M631L became meaningful because experimental work said what it does.
6. **Follow the spillback.** Lineages leaving the new host are a change in the risk assessment, and only genomics sees them.

## 6 · Explain it in 60 seconds

> In March 2024, American dairy cows started getting bird flu. The critical question was whether birds were infecting cows over and over on many farms, or whether it had happened once and the virus was now spreading cow to cow — because those need completely different responses.
>
> The genomes answered it. All the cattle viruses formed a single family group descending from one bird virus, meaning **one jump**, in late 2023, months before anyone noticed. After that, the virus was moving with the cattle trade, not with birds — so the response shifted to animal movement controls.
>
> The virus then picked up changes in its copying machinery that help it replicate in mammals, and it spilled back out into other species and into people.
>
> And in January 2025 a **second, unrelated** bird flu virus jumped into dairy cattle independently. The first finding had been correct — and it had described the past, not promised the future. Ongoing sequencing is what caught the second one.

## 7 · Read more

- *Emergence and interstate spread of highly pathogenic avian influenza A(H5N1) in dairy cattle in the United States*, **Science**, doi:10.1126/science.adq0900
- *Spillover of highly pathogenic avian influenza H5N1 virus to dairy cattle*, **Nature** (2024), s41586-024-07849-4
- *Polymerase mutations underlie early adaptation of H5N1 influenza virus to dairy cattle and other mammals*
- *H5N1 clade 2.3.4.4b dynamics in experimentally infected calves and cows*, **Nature** (2024)
- *The emergence and molecular evolution of H5N1 influenza viruses in United States dairy cattle*, bioRxiv 2026.03.30.713641

⚠ Leads, not verified citations. See `sources/source-ledger.md`.
