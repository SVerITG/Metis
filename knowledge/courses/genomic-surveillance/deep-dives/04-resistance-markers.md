# Deep Dive 4 — Resistance as genomic surveillance: malaria and TB, or genomics without trees

> **The case.** Two of the largest and most consequential genomic surveillance programmes in the world barely build phylogenies. They are **marker** surveillance, not **tree** surveillance — a different discipline with a different failure mode — and it is the version most likely to be running in a country near you.

---

## 1 · Why this is a different discipline

Every other deep dive in this course reads epidemiology off the *relationships between* genomes. This one reads it off the *contents of* genomes: does a specific position carry a specific change, and in what proportion of the parasite or bacterial population.

The distinction follows from biology, and it is Lesson 1's argument arriving at its consequence.

**Malaria.** *Plasmodium falciparum* has a ~23 Mb genome and **recombines sexually in the mosquito** every transmission cycle. Recombination shreds linkage: different parts of the genome have different histories, so a single tree describes none of it (Lesson 8). Add frequent multi-clone infections within one host, and consensus-based tree reasoning is compromised at the root.

**Tuberculosis.** *M. tuberculosis* does not recombine meaningfully, so trees do work — and they are used for transmission analysis. But it accumulates only **~0.3–0.5 SNPs per genome per year**, which makes tree-based inference slow and coarse, while the clinically urgent question is answerable from a handful of positions **today**.

So both fields converged on: **find the markers, count them, act.** No tree required.

## 2 · Malaria — three markers, three different decisions

### Artemisinin partial resistance: *kelch13*
Mutations in the propeller domain of the *kelch13* gene cause delayed parasite clearance — artemisinin partial resistance. A WHO-curated list distinguishes **validated** markers from **candidate/associated** ones, and that distinction is the operational content: only validated markers trigger policy.

Established position: *kelch13* propeller mutations are **entrenched in several countries of East, Central and the Horn of Africa** — the emergence of African artemisinin partial resistance, independent of the original South-East Asian focus. Contrast with settings where surveillance finds it essentially absent: in South African malaria-eliminating districts (2022–2024), validated markers were rare, with P574L in two samples and P553L in one.

**The decision it feeds:** whether to change first-line treatment, whether to deploy multiple first-line therapies or triple ACTs, and where to concentrate therapeutic efficacy studies.

### Diagnostic escape: *pfhrp2/pfhrp3* deletions
Most malaria rapid diagnostic tests detect the HRP2 protein. Parasites that have **deleted the *pfhrp2* and *pfhrp3* genes** are invisible to those RDTs. Double deletions have been confirmed in the Horn of Africa; the South African survey found none.

**The decision it feeds:** whether to switch a national programme from HRP2-based RDTs to pLDH-based ones — a procurement decision affecting millions of tests, triggered when deletion prevalence crosses a WHO-recommended threshold.

✱ **This is the cleanest "so what" in the whole course** (Lesson 15). The decision is named, the threshold is pre-specified, the result direction is defined in advance, and the action is concrete. Most genomic surveillance cannot describe itself this cleanly.

### The rest of the panel and the data resource
*pfcrt*, *pfmdr1* (chloroquine, lumefantrine, amodiaquine), *pfdhfr*/*pfdhps* (sulfadoxine– pyrimethamine, which matters directly for intermittent preventive treatment in pregnancy).

**MalariaGEN Pf8**, released June 2025, is an open dataset of *P. falciparum* genome variation from **33,325 samples worldwide** — the reference background against which any national survey is interpreted. Large-scale analyses across more than 100,000 samples have been used to characterise the global rise of artemisinin resistance.

## 3 · Tuberculosis — the catalogue, and where sequencing sits in the algorithm

TB is where marker surveillance is most formalised, and the formalisation is the achievement.

**The WHO *Catalogue of mutations in Mycobacterium tuberculosis complex and their association with drug resistance* (2nd edition, 2023)** analysed over **52,000 isolates with matched whole genome sequencing and phenotypic drug susceptibility testing**, and grades mutations for **13 anti-TB medicines**.

⚠ **Understand what that catalogue is, because it is the model the rest of the field should copy.** It is not a list of mutations someone noticed in resistant isolates. It is a **genotype–phenotype association study at scale**, with graded confidence, which converts a sequence into a susceptibility prediction with a stated evidence level. This is the bridge Lesson 0 said was usually missing — **a mutation is a hypothesis about a phenotype** — built explicitly, once, for everyone.

**Where sequencing sits in the diagnostic algorithm.** WHO's 2025 consolidated guidelines and operational handbook place **targeted next-generation sequencing (tNGS)** *after* initial automated nucleic acid amplification tests, delivering catalogue-linked molecular drug susceptibility testing across a broad drug panel — and reserve **whole genome sequencing** for discordance resolution, confirmation and surveillance.

**tNGS** amplifies a defined panel of resistance-associated regions **directly from sputum** and sequences them deeply. Compared with WGS from culture: no culture wait, works on paucibacillary specimens, far cheaper, and deep enough to detect **minority resistant subpopulations** — the heteroresistance that a consensus genome hides (Lesson 2). Compared with a line probe assay: many more drugs, and actual mutation identity rather than probe-hybridisation failure.

## 4 · The failure modes of marker surveillance

Different from tree surveillance, and worth learning separately.

**1. The marker–phenotype link is the whole edifice.** If the association is wrong, incomplete, or lineage-dependent, everything built on it is wrong. Hence the WHO catalogue's graded confidence levels, and hence the distinction between validated and candidate *kelch13* mutations. **Never treat an unvalidated marker as a resistance call.**

**2. Absence of a known marker is not absence of resistance.** Resistance mechanisms not yet in the catalogue — efflux, unknown loci, epistatic combinations — produce phenotypically resistant organisms with a "susceptible" genotype. **Genotypic susceptibility prediction has a sensitivity below 1, and phenotypic testing is not obsolete.**

**3. Frequency estimates need a sampling frame.** "8% of isolates carry marker X" is a proportion, and Lesson 13 applies in full. Isolates from a referral hospital treating treatment failures are not a random sample of infections; using them to estimate national prevalence inflates it, potentially triggering an unnecessary and expensive policy change.

**4. Threshold effects are policy, not biology.** "Switch when deletions exceed 5%" is a decision rule. Its consequences either side of the line are asymmetric — switching too early wastes money, too late means missed diagnoses — and the threshold should be set by whoever bears both costs.

**5. Within-host mixtures matter and consensus hides them.** A patient with 15% resistant parasites or bacilli is a treatment-failure risk that a consensus genome reports as fully susceptible. This is the practical reason deep targeted sequencing exists (Lesson 2).

## 5 · What it is actually worth

**Very high, and it is the most decision-linked genomics in routine global health.** Every marker above maps to a named decision with a threshold. Compare with much viral genomic surveillance, where the link to action is real but harder to state.

**And it is the most deployable.** tNGS panels and targeted malaria genotyping need far less sequencing capacity, far less bioinformatics and far less compute than whole-genome phylodynamics. A national programme that cannot run BEAST can run a resistance panel and act on it — which is why, for many countries, **this is what genomic surveillance actually means**.

⚠ **The gap to watch is the catalogue for everything else.** TB has one. Malaria has curated marker lists. Most other pathogens have neither — resistance markers scattered across the literature, of varying evidence quality, without graded confidence. **Building the catalogue is the rate-limiting step for extending marker surveillance to a new pathogen**, and it is unglamorous, expensive, and worth more than another sequencer.

## 6 · Transferable lessons

1. **Not all genomic surveillance is phylogenetics.** Ask whether the question needs relationships or contents. Recombining organisms often make trees inapplicable and markers essential.
2. **A curated, graded genotype–phenotype catalogue is the highest-value artefact in a marker programme** — higher than any single study.
3. **Distinguish validated from candidate markers, always, in every report.**
4. **Genotypic prediction has imperfect sensitivity.** Phenotypic testing remains necessary for discordance and for discovering what the catalogue lacks.
5. **A marker frequency is a proportion and needs a representative sampling frame.**
6. **Deep targeted sequencing beats WGS for minority variants**, which is often the clinically relevant question.
7. **Sequence directly from specimen where possible.** Culture adds weeks and selects for what grows.

## 7 · Explain it in 60 seconds

> Most genomic surveillance is about how samples are *related* — family trees of viruses. For malaria and TB, it is mostly about what is *in* the genome: does this parasite or bacterium carry a specific change that makes a specific drug or test fail?
>
> For malaria, three things are watched. Mutations in a gene called *kelch13* mean artemisinin works more slowly — now entrenched across parts of East, Central and the Horn of Africa. Deletions in *pfhrp2* and *pfhrp3* make the parasite invisible to most rapid tests — which, above a threshold, forces a country to switch to a different kind of test entirely. And a panel of older markers tracks the drugs used in prevention.
>
> For TB, WHO built a catalogue from over 52,000 bacteria with both their genome and their laboratory drug-resistance results, so a sequence can now be read as a resistance profile for 13 drugs, with a stated confidence level for each mutation. Sequencing panels can be run straight from a patient's sputum, no culture, in a couple of days.
>
> The catch is the same in both: the genome only tells you about resistance mechanisms someone has already identified. **A "susceptible" genome is not a guarantee.**

## 8 · Read more

- WHO. *Catalogue of mutations in Mycobacterium tuberculosis complex and their association with drug resistance*, 2nd ed. (2023). ISBN 9789240082410
- *Targeted Next-Generation Sequencing in Drug-Resistant Tuberculosis: WHO Guidance and Practical Implementation Priorities*, **Biomedicines** 14(1):93 (2026)
- *Targeted next-generation sequencing to diagnose drug-resistant tuberculosis: a systematic review and meta-analysis*, **Lancet Infectious Diseases** (2024)
- *Understanding the global rise of artemisinin resistance: insights from over 100,000 Plasmodium falciparum samples*, **eLife** 105544
- MalariaGEN **Pf8** open dataset (June 2025; 33,325 samples) — malariagen.net
- *Very low prevalence of validated kelch13 mutations and absence of hrp2/3 double gene deletions in South African malaria-eliminating districts (2022–2024)*

⚠ Leads, not verified citations. See `sources/source-ledger.md`.
