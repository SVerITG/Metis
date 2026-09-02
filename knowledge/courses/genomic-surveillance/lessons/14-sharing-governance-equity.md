# Lesson 14 — Sharing, governance and equity: where the sequence goes, and who decides

> **Concept map**
> **Builds on** — Lesson 11 (unequal sequencing biases the science) and Lesson 13 (metadata is the constraint).
> **Connects to** — Lesson 15: a sequence nobody can see changes no decisions.
> **Leads to** — Deep Dive 1, whose data sit on Pathoplexus under a restricted licence with named contacts.

## Why this matters

Sharing looks like an administrative step at the end of the pipeline. It is not. It is the step that determines:

- **Whether the science is right.** Lesson 11 established that missing regions bias phylogeography for everyone. Unshared data is missing data.
- **Whether anyone acts on it.** A sequence in a laboratory freezer, or in a database nobody can query, changes nothing.
- **Whether the people who generated it are treated fairly.** This has been a live grievance for two decades and it is the reason the platform landscape looks the way it does.

The tension is genuine and it does not resolve into a slogan. Immediate open sharing maximises global scientific value and minimises the ability of the originating country to lead the analysis of its own outbreak. Restricted sharing protects that ability and slows everyone down. Every platform in this lesson is a different position on that trade-off, and knowing where each one sits is part of the job.

## Learning objectives
By the end of this lesson you will be able to:

- **Compare** INSDC, GISAID and Pathoplexus on access model, credit and restrictions.
- **Explain** why the Bundibugyo data are under a restricted licence, and defend that choice.
- **Describe** how Nagoya/DSI and the WHO PABS negotiations affect pathogen sequence sharing.
- **Identify** the data-protection risks in pathogen sequencing, including human read contamination.
- **Argue** that sequencing equity is a methodological requirement, not only an ethical one.

## Prerequisites
Lessons 0–13.

---

## Section 1 · The three sharing models

### INSDC — GenBank / ENA / DDBJ
The oldest and most open. Submit a sequence and it becomes fully public, downloadable, and usable by anyone for any purpose. No terms of use, no access control, no obligation to credit beyond ordinary academic citation.

- **Best for science:** maximum reuse, permanent accessions, unrestricted redistribution.
- **The grievance it produced:** originating laboratories in low- and middle-income countries have repeatedly seen their sequences analysed and published by better-resourced groups before they could publish themselves. "Helicopter research" is the shorthand, and it is not hypothetical.

### GISAID
Built for influenza (EpiFlu, from 2008), scaled dramatically for SARS-CoV-2 (EpiCoV). Access requires registration and agreement to terms: **you must acknowledge the originating and submitting laboratories, and you may not redistribute the data.**

- **What it achieved:** it is widely credited with getting sequences shared at all, at speed, from countries that would not have submitted to a fully open database. That is a real and large achievement.
- **What it costs:** data cannot be redistributed, so reproducible analyses are harder to build and pipelines must handle access control. It has been the subject of sustained public conflict about governance and access decisions.
- Long-standing partner of WHO's Global Influenza Surveillance and Response System.

### Pathoplexus
Launched in 2024, built on the open-source **Loculus** platform, and designed explicitly as a middle path: **open data with structural protections for the originating scientists.**

- Initially covering Ebola, West Nile and Crimean-Congo haemorrhagic fever viruses, since expanded — it collected 2,765 mpox sequences in 2025.
- Supports **restricted-access periods** with named contacts, then transition to open.
- Sequences carry explicit provenance and terms.

**This is where the flagship data live.** The 2026 Bundibugyo dataset is deposited as `BDBV_DRC_20260820` (`PP_SS_3400.1`) under a **restricted** licence, with contact required before use in advance of publication, and Dr Tony Wawina-Bokalanga and Prof. Placide Mbala-Kingebeni at INRB named as the contacts.

✱ **Look at what that arrangement achieves simultaneously.** The analysis was posted publicly on virological.org within the outbreak, so the world could see the methods, the trees and the numbers in near-real time. The *sequences* remain under the control of the institution that generated them until they publish. This is not a compromise between openness and equity; it is a design that delivers most of both, and it is worth studying as a model rather than treated as an obstacle.

### The comparison

| | INSDC | GISAID | Pathoplexus |
|---|---|---|---|
| Access | Fully open | Registered users, terms | Open, with optional restricted period |
| Redistribution | Unrestricted | **Prohibited** | Permitted (after any restriction) |
| Credit | Citation norms | **Contractually required** | Structured provenance |
| Protects originators | No | Via terms of use | Via licence + restricted period |
| Reproducibility | Best | Hardest | Good |
| Governance | Public consortium | Private foundation | Open-source, community |

## Section 2 · Why "just share everything immediately" is not the answer

Four reasons, and none of them is bad faith.

**1. Publication and career.** A researcher in Kinshasa who deposits sequences openly on day three can be scooped by a group with more analysts and no fieldwork. Under any existing academic incentive system this is a serious professional cost, and the consequence is predictable: less sharing, later.

**2. Capacity building requires doing the analysis.** If sequences are immediately analysed elsewhere, the local analytical capacity never develops — and capacity is precisely what the Africa PGI's investments (70 sequencing platforms distributed, more than 1,000 people trained, 7 countries with sequencing capacity in 2019 rising to 46 by late 2025) exist to build. Open data flow can undercut the capacity it is meant to complement.

**3. Sovereignty and legal obligation.** Sequences derive from human samples collected under national law and ethical approval, with specific consent terms. A researcher cannot unilaterally place them beyond national control.

**4. Nagoya and DSI.** The Nagoya Protocol governs access to genetic resources and benefit sharing. Whether **digital sequence information (DSI)** falls within its scope was contested for a decade and has now moved: CBD COP16 (November 2024) agreed a multilateral mechanism, and the **Cali Fund** was launched in February 2025 for benefit sharing from commercial use of DSI, with details and contribution rates to be settled at COP17 in October 2026. Public databases, public research and academic institutions are not expected to make monetary contributions — but the direction of travel is unmistakable: **sequence data is a genetic resource with benefit-sharing obligations attached.**

## Section 3 · PABS and the WHO Pandemic Agreement

The health-specific version of the same argument. The **Pathogen Access and Benefit-Sharing (PABS)** system is intended to secure both halves at once: rapid sharing of pathogens and sequences with pandemic potential, and equitable sharing of the benefits derived from them — vaccines, diagnostics, therapeutics.

Status as of 2026: the PABS annex to the WHO Pandemic Agreement is **still being negotiated.** Member States extended negotiations through 2026, and in May 2026 decided that a final negotiated outcome would be presented to the World Health Assembly for adoption in **May 2027**. The unresolved core is the same one: a bloc of roughly 100 low- and middle-income countries seeks mandatory benefit sharing — guaranteed access to vaccines, therapeutics and diagnostics — as the condition for rapid sharing of information on novel pathogens.

⚠ **Why this belongs in a methods course rather than a policy seminar.** The outcome determines how fast sequences move during the next emergency, and therefore how good the phylogeography is, and therefore how good the response is. During the 2026 Bundibugyo outbreak, the practical answer was worked out case by case, institution by institution: post the analysis openly, restrict the sequences, name the contacts. That is what operating in an unsettled legal environment looks like, and it is what you should expect to negotiate in your own work.

## Section 4 · Data protection — the part that is nobody's job

**Human reads in pathogen datasets.** Any clinical sample contains host nucleic acid. Metagenomic data is mostly human. Even amplicon data contains off-target host reads. **Human genomic data is identifiable and is regulated as personal data** in the EU and many other jurisdictions.

The requirement: **deplete host reads before deposition**, and verify. This is a technical step (Lesson 5) with a legal consequence, and it falls between the bioinformatician who thinks it is a data-protection matter and the data-protection officer who does not know it exists.

**Re-identification through metadata.** In a small health zone, "female, 34, village X, onset 12 June" is identifying. Genomic databases carry rich metadata by design, and the same fields that make a sequence scientifically useful (Lesson 13) make it potentially identifying. Aggregate location to an appropriate administrative level, blur dates where precision is not needed, and consider what a linked database would reveal.

**Consent.** Consent for diagnosis is not consent for sequencing, and consent for sequencing is not consent for open publication. Public health legislation often provides a legal basis independent of individual consent for outbreak surveillance, and that basis needs to be established explicitly rather than assumed.

## Section 5 · Equity as a methodological requirement

The argument this course keeps making, stated in full.

**Empty regions of the map bias inference for everyone.** Lesson 11: discrete trait phylogeography infers origins where sequencing is dense. If a region does not sequence, the global analysis does not merely lack detail there — it produces **actively wrong** conclusions about where lineages arose and how they moved, and those conclusions are published, cited, and used to justify travel restrictions on the countries that could not sequence.

So sequencing equity is not a moral supplement to good methods. **It is a precondition for them.** A phylogeography of Africa built without African sequences is not incomplete; it is incorrect. The same holds within a country: a phylogeography of the Ituri outbreak built only from Bunia would misplace its origin.

**What is being built.** The Africa CDC Africa Pathogen Genomics Initiative expanded next-generation sequencing capacity from 7 African Union Member States in 2019 to 46 by late 2025, distributing 70 sequencing platforms with ancillary equipment, training more than 1,000 people in genomics and bioinformatics, and installing high-performance computing in selected public health laboratories — the last of which matters as much as the sequencers, for the reason given in Lesson 4. **AGARI**, launched with the African Society for Laboratory Medicine in late 2025, adds a continent-wide hub for uploading, archiving, analysing and sharing genomic data — a regional platform that is a third answer to the sovereignty question, alongside GISAID and Pathoplexus.

The WHO **Global genomic surveillance strategy for pathogens with pandemic and epidemic potential 2022–2032** is the framing document, and its central ambition is the right one: moving genomics out of academic research and into routine public health practice, integrated with existing surveillance rather than parallel to it.

✱ **The gap that remains, and it is the one to watch.** Sequencing capacity has expanded far faster than bioinformatics capacity, and bioinformatics capacity far faster than the institutional ability to link sequences to case data (Lesson 13). Instruments are purchasable; analysts are trainable but slowly; data linkage requires organisational change that no grant buys. **Expect the binding constraint to be, in order: metadata linkage, then analysts, then compute, then sequencers.** Most funding is allocated in exactly the reverse order.

## Section 6 · Practical guidance for a submission

1. **Deposit somewhere.** A sequence in a laboratory folder has no value beyond that laboratory.
2. **Choose the platform for the situation.** Routine surveillance and retrospective work → INSDC. Influenza and contexts where the network expects it → GISAID. Outbreak sequences you need to control while your team analyses them → Pathoplexus with a restricted period.
3. **Deposit metadata, not just sequence.** Collection date at real precision, location at a defined administrative level, host, specimen type. Lesson 13's minimum set.
4. **Deplete human reads and verify.**
5. **State the terms.** If restricted, say so, say until when, and name a contact — as the Bundibugyo dataset does.
6. **Cite generators.** Sequences have authors. Acknowledge originating and submitting laboratories in every analysis, whether or not the licence compels it.
7. **Publish the analysis even when the sequences are restricted.** virological.org, medRxiv/bioRxiv, a Nextstrain build, a national bulletin. The Bundibugyo team's approach: the analysis is public in real time, the sequences follow.

## Practice

Take a genomic dataset you or your institution holds:

1. Where is it deposited? If nowhere, why not, and what would it take?
2. What licence or terms apply, and who decided?
3. Are human reads depleted, and has anyone verified it?
4. Could an individual be re-identified from the metadata plus a local case list?
5. If a group in another country analysed it tomorrow and published, what would your institution's position be? **Answer that before it happens, not after.**

## In one paragraph

Where a sequence goes determines whether the science is right, whether anyone acts on it, and whether the people who produced it are treated fairly — and no platform gets all three. INSDC maximises reuse and produced the helicopter-research grievance; GISAID traded redistribution for credit and got data shared that otherwise would not have been; Pathoplexus offers a restricted period with named contacts, which is why the 2026 Bundibugyo genomes sit there while the analysis itself was posted publicly during the outbreak. Above the platforms sit two unfinished legal frameworks: the CBD's DSI mechanism with the Cali Fund, and the WHO PABS annex now scheduled for adoption in May 2027. And the equity argument is not an addendum to the methods — unsequenced regions do not merely leave gaps, they cause phylogeographic models to place origins where sequencing is dense, which makes sequencing capacity a precondition for correct inference rather than a fairness consideration layered on top of it.
