# Deep Dive 5 — Wastewater and pathogen-agnostic surveillance: sequencing a population, and sequencing without a hypothesis

> **The case.** Two frontiers that break assumptions this course has relied on throughout. Wastewater gives you a **mixture** rather than an individual, so the consensus genome — the object every earlier lesson was built around — no longer exists. Metagenomics removes the requirement to know what you are looking for, which removes the sampling frame along with it.

---

## 1 · Wastewater: what changes when the sample is a population

Every technique in Lessons 5–12 assumed one sample equals one infection. Wastewater from a treatment plant catchment contains virus shed by everyone infected in that catchment, at unknown and unequal rates.

**What you gain:**

- **Population coverage without clinical contact.** No care-seeking, no testing decision, no consent-by-individual, no Ct gate. The Lesson 13 cascade largely disappears — which is a substantial epistemic gain, not a convenience.
- **Independence from health-seeking behaviour.** It sees infections that never reach a clinic, which for mild, asymptomatic or stigmatised infections is most of them.
- **Cost per person monitored is extraordinarily low.** One sample can represent hundreds of thousands.

**What you lose:**

- **The individual.** No case, no clinical data, no outcome, no demographics.
- **The denominator.** Signal depends on shedding rates, dilution, rainfall, industrial discharge, temperature, transit time and sewer design. **Converting signal to prevalence is unreliable**, which is why wastewater surveillance is a trend instrument, not a counting instrument.
- **The consensus genome.** This is the deep one.

## 2 · The consensus genome does not exist here

In a clinical sample, consensus calling reports the majority base and discards minority variation (Lesson 2). Applied to wastewater it produces a **chimera**: a sequence that is the position-by-position majority across several co-circulating lineages, and which corresponds to no real virus. It is not noisy. It is meaningless.

So the analytical object changes. Instead of *"what is the genome"*, the question is **"what mixture of known lineages best explains the observed allele frequencies at every position?"** — a **deconvolution** problem.

This is what **Freyja** does. Its central step, `freyja demix`, uses the mutations present in sequencing reads, with their frequencies, to infer the relative abundance of individual lineages in the sample, against a reference set of lineage-defining mutation profiles.

**Freyja 2** (2025) extends this into a real-time multi-pathogen framework:

- New methods for estimating lineage prevalence **and growth rates**.
- Demonstrated **robustness across sequencing platforms and to low genomic coverage** — which matters, because wastewater RNA is degraded and coverage is patchy by nature.
- Incorporates global pathogen data streams for multi-pathogen surveillance.
- Applied across **SARS-CoV-2, mpox and H5N1**, revealing unreported diversity and lineage co-circulation — including **H5N1 during the initial dairy cattle outbreaks** (Deep Dive 3), plus West Nile virus, measles and hundreds of viral taxa.

⚠ **The critical dependency: deconvolution is against a reference set of known lineages.** A truly novel lineage with no profile cannot be assigned; it appears as unexplained variation, as a poor fit, or gets misassigned to the nearest known relative. **Wastewater lineage surveillance detects the arrival of known things well and the emergence of unknown things poorly**, which is close to the inverse of what people assume it does.

✱ A second, subtler dependency: the reference lineage set is built from *clinical* sequencing. So wastewater surveillance is not independent of clinical surveillance — it inherits the clinical system's blind spots in its reference database, even while escaping the clinical system's sampling cascade in its sample.

## 3 · Where wastewater has genuinely delivered

**Polio.** Environmental surveillance is a core pillar of global polio eradication and predates the current enthusiasm by decades. It detects circulating vaccine-derived polioviruses in populations reporting no paralytic cases — which is precisely the situation eradication has to manage, and precisely what clinical surveillance cannot do, because most poliovirus infections are asymptomatic. **This is the proof of concept for the entire modality**, and it is the case where the operational pathway from detection to action is fully built.

**SARS-CoV-2.** Lineage tracking at population scale, often leading clinical detection of a new lineage's arrival, and continuing to function after clinical testing collapsed.

**Emerging multi-pathogen use.** Measles, H5N1, mpox, West Nile — the Freyja 2 work demonstrates the technical feasibility. **Feasibility is not yet an operational pathway.** For most of these there is no agreed action threshold and no named decision-maker, which by Lesson 15's test means it is still research.

## 4 · Pathogen-agnostic metagenomics: sequencing without a hypothesis

The other frontier. Sequence everything in a sample; work out afterwards what is there.

**Why it matters.** It is the only method that can find something nobody asked about. The 2026 DRC event began as "an unknown illness with high mortality" (Deep Dive 1) — the exact scenario metagenomics exists for. It has produced genuine first diagnoses in encephalitis and sepsis of unknown cause.

**Where it stands.** Reviews describe metagenomics as increasingly used for viral diagnosis and surveillance, with new rapid sequencing approaches and selective enrichment expanding the range of scenarios — while stating plainly that **validation and accreditation of protocols, plus further methodological development, are needed before routine clinical and public health service use.** That is a fair summary: real, growing, not yet routine.

**The obstacles, in order of severity:**

**1. Cost.** Consumables for a metagenomic workflow range roughly **$130 to $600+ per sample** depending on depth and preparation, and clinical mNGS services have been costed far higher — the UCSF meningitis/encephalitis test at around **$3,000 per sample** (2024). Against a targeted PCR panel at a few dollars, this restricts mNGS to cases where the panel failed.

**2. Sensitivity.** Most reads are host. Even with depletion or adaptive sampling (Lesson 4), low-abundance pathogens are missed. Diagnostic accuracy meta-analyses have consistently found mNGS sensitivity below that of targeted methods **for targets those methods cover** — its advantage is entirely in what they do not cover.

**3. Interpretation.** Every sample contains commensals, environmental organisms, reagent contaminants and index-hopped reads. **Distinguishing pathogen from passenger is the hard part**, it requires curated background databases and negative controls at every run, and it is where the false positives come from.

**4. Data protection.** The output is mostly human sequence. Lesson 14: identifiable personal genetic data, requiring depletion before deposition — and this is the modality where the requirement is largest and most often neglected.

**5. No sampling frame.** If you are sequencing whatever arrives from whoever was sick enough to be investigated, you have a case series. Pathogen-agnostic *surveillance* — as opposed to pathogen-agnostic *diagnosis* — needs a defined sampling frame, and prospective sentinel designs such as the national viral metagenomic sentinel surveillance pilots in primary care are the form that attempt to supply one.

## 5 · What both are actually worth

**Wastewater:** proven and operational for polio and SARS-CoV-2; technically demonstrated and operationally immature for the multi-pathogen case. It is the cheapest population-level surveillance that exists and it will expand. **Judge any new application on whether an action threshold and a decision-maker exist**, because the technology is now ahead of the governance.

**Metagenomics:** genuinely transformative for the individual undiagnosed severe case, and still too expensive and too unstandardised for routine population surveillance. Falling costs and adaptive sampling are moving it; the interpretation problem is not primarily a cost problem and will not be solved by cheaper sequencing.

**The honest position on both:** these are the two modalities most often oversold in strategy documents, and both are real. The overselling is not about whether they work — it is about skipping the question of who acts on the result.

## 6 · Transferable lessons

1. **When the sample is a mixture, the consensus genome is a chimera.** Move to deconvolution, and know the reference-set dependency.
2. **Deconvolution finds what is already in the reference set.** Good for arrival of the known, poor for emergence of the unknown.
3. **Wastewater signal is a trend, not a count.** Shedding, dilution and sewer dynamics are not calibratable in practice.
4. **The polio programme is the template.** Not because of the technology, but because the pathway from detection to action was built and is used.
5. **Pathogen-agnostic diagnosis and pathogen-agnostic surveillance are different activities.** The first is a clinical service; the second needs a sampling frame.
6. **In metagenomics, interpretation dominates.** Curated backgrounds and controls, not read counts.
7. **Human read depletion is a legal requirement**, and metagenomics is where it matters most.

## 7 · Explain it in 60 seconds

> Two newer ways of doing genomic surveillance break the usual rules.
>
> The first is sewage. Everyone infected in a city sheds virus into the same pipes, so one sample represents a whole population — no clinic visit, no test, no consent from each person. But it is a **mixture**, so you cannot read off "the" genome. Instead software like Freyja works out which known variants, in what proportions, best explain the mutations it sees. That works beautifully for tracking variants you already know about — and poorly for spotting something genuinely new, because it can only match against a list. Polio has used sewage surveillance for decades and it is the reason we know about silent transmission.
>
> The second is sequencing everything in a sample without deciding in advance what you are looking for. It is the only method that can find an unknown pathogen — which is exactly how the 2026 DRC outbreak first presented, as an unknown illness with high mortality. But it costs hundreds to thousands of dollars per sample, most of what it reads is the patient's own DNA, and telling a real pathogen from a harmless passenger is genuinely difficult. It is a last-resort diagnostic that is slowly becoming a surveillance tool.

## 8 · Read more

- *Real-time, multi-pathogen wastewater genomic surveillance with Freyja 2*, medRxiv 2025.07.26.25332245 / PMC12330420
- *Clinical metagenomics for diagnosis and surveillance of viral pathogens*, **Nature Reviews Microbiology** (2025), s41579-025-01223-5
- *Metagenomic Sequencing as a Pathogen-Agnostic Clinical Diagnostic Tool: a Systematic Review and Meta-analysis*, **Journal of Clinical Microbiology**
- *Viral metagenomic sentinel surveillance of acute respiratory infections in primary care*, medRxiv 2025.12.18.25342553
- *Surveillance for emerging and reemerging pathogens using pathogen agnostic metagenomic sequencing in the United States*, PMC11044857
- Freyja documentation, and the Cambridge Bioinformatics SARS-CoV-2 wastewater abundance materials

⚠ Leads, not verified citations. See `sources/source-ledger.md`.
