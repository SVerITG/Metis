# Deep Dive 6 — *T. b. gambiense*: the course's counter-example, and what a genomic baseline would have to contain

> **The case.** Every other deep dive in this course shows genomic surveillance working. This one is about a disease where most of the machinery in Lessons 7 to 12 **does not apply**, where the single most consequential sampling decision is which tissue you take, and where the highest-value genomic act available today is not an analysis at all — it is archiving.

---

## 1 · The question someone actually asked

The WHO NTD road map 2021–2030 targets **elimination of transmission** of gambiense human African trypanosomiasis — reported cases to zero. Elimination *as a public health problem* was already met globally in 2018, and validated country by country since: Togo, Côte d'Ivoire, Benin, Uganda, Equatorial Guinea, Ghana and others.

The trajectory is genuinely remarkable. Global reported cases are in the high hundreds — 802 in 2021, 837 in 2022. In DRC, which still carries most of the remaining burden, reported cases fell from **26,318 in 1998 to 394 in 2023**. Acoziborole, a single-dose oral cure, makes interruption of transmission thinkable in a way it was not a decade ago.

The verification criterion for interruption is: **zero reported human cases for at least five consecutive years.**

And there the question arrives, which is an epidemiological question with a genomic shape:

> **Are there ways for transmission to persist while that criterion is being met?**

There are at least three candidates, and all three are live:

1. **An animal reservoir.** *T. b. gambiense* has been molecularly identified in naturally infected pigs, dogs and small ruminants in Chad, and in **duikers and mangabeys** in Gabonese historical and active foci. Experimental animal–*Glossina*–animal cycles have retained infectivity for periods of around three years.
2. **Latent and asymptomatic human infection.** Seropositive, aparasitaemic individuals who are never confirmed and therefore never treated. Plus the well-documented cases diagnosed outside Africa years or decades after leaving a tsetse area.
3. **The dermal reservoir.** Trypanosomes persist in the basal layer of the dermis, transmissible to tsetse in experimental conditions, **in the absence of detectable parasitaemia**.

That third one deserves its numbers stated plainly, because it reframes the sampling problem for the whole discipline. In studies of suspected and confirmed gHAT, trypanosome DNA was detected in the **blood of 67% of confirmed cases and 9% of unconfirmed seropositive individuals** — but in the **skin of up to 71% of confirmed cases and 41% of unconfirmed seropositives**. After treatment, skin positivity fell to 17% of confirmed cases, while **up to 25% of unconfirmed, untreated seropositives remained skin-positive**.

⚠ **Read that as a Lesson 3 statement and it is startling.** The standard specimen — blood — systematically misses a substantial fraction of the infections that matter most for elimination: the unconfirmed seropositives, who are exactly the people the surveillance system does not treat. **The sampling frame and the reservoir are in different tissues.**

## 2 · Why most of this course does not apply here

Run Lesson 1's arithmetic before anything else, because it rules out most of the toolkit in one line.

***T. b. gambiense* group 1 (Tbg1) is clonal, monophyletic and genetically homogeneous.** Phylogenetic analysis of genome-wide SNPs, and of SNPs in the maxicircle coding region, places all analysed Tbg1 parasites in a single monophyletic group. This is not a sampling artefact; it is the defining population-genetic fact about the organism, and it is why Tbg1 is a distinct thing from Tbg2 and from *T. b. brucei* and *T. b. rhodesiense*, both of which are genetically and phenotypically diverse.

Now put that against the transmission timescale. gHAT is a chronic infection: the interval between infections in a chain is measured in months to years, not days. But the parasite is a diploid eukaryote with high-fidelity replication and — for Tbg1 — essentially no detectable population structure to move against.

**The two clocks have come apart in the direction that kills genomic epidemiology.** Not because the parasite spreads too fast for evolution to keep up, but because the population is so homogeneous that there is almost nothing to distinguish one isolate from another.

The consequences, stated as bluntly as the course's other deep dives state their successes:

| Question (Lesson 0) | Applies to gHAT? |
|---|---|
| **Q1** — is this the same outbreak / who is linked to whom | **No.** Insufficient diversity to resolve chains, clusters or links between cases. |
| **Q2** — where did it come from | **Partly, and only with a baseline.** Import vs residual transmission is answerable *if* historical sequences from that focus exist. Host-state reconstruction is limited by animal sampling (§4). |
| **Q3** — how fast is it spreading | **No.** Phylodynamics needs coalescent signal in a time-scaled tree. There is not enough diversity to build one that means anything. |
| **Q4** — has the pathogen changed | **Yes, and this is where the value is.** Subspecies identification, drug-resistance markers, diagnostic-target integrity. |

✱ **This is the honest version of Lesson 15's hardest skill.** Saying "sequencing is the wrong tool for that question" is not a failure of ambition, it is the professional judgement the lesson argues for — and here it applies to three of the four questions. A proposal to reconstruct gHAT transmission chains by sequencing is a proposal that Lesson 1's arithmetic rules out before any money is spent.

## 3 · The obstacle the methods lessons understate: there is barely any parasite

Lessons 3 and 4 are built around a filovirus at Ct 18 — abundant template, a 19 kb genome, amplicons that work. gHAT is the opposite case on every axis.

- **Parasitaemia is very low**, and often below the detection limit of microscopy. This is why the diagnostic pathway is serological screening (CATT, then RDTs) followed by parasitological confirmation (mAECT, capillary tube centrifugation, lymph node aspirate) rather than a direct molecular test on blood.
- **The genome is ~26 Mb of nuclear DNA** in a sample that is overwhelmingly human. Lesson 3's enrichment problem at its most severe: without selective enrichment you are paying to sequence the patient at great depth to find almost nothing.
- **Culture is not routine** for field isolates, so the bacterial escape route — grow it, then sequence clean abundant DNA — is not available.

So the field solved the detection problem the way Lesson 3 predicts it should be solved when the target is scarce: **by going after a high-copy target.** The kinetoplast — the trypanosome's mitochondrial genome — contains thousands of **minicircles** per cell. Deep sequencing of kinetoplast genomes across 38 animal- and human-infective strains identified **241 minicircle sequence classes as Tbg1-specific**, which became the basis of a molecular assay for detecting *T. b. gambiense* specifically.

✱ **Note what that is, in this course's terms.** It is a genomics-derived *diagnostic*, not a genomic surveillance analysis. Sequencing was used once, to design a target; the field application is a PCR. This is the same shape as the malaria and TB marker work in Deep Dive 4, and it is by some distance the most deployable form of pathogen genomics — a point worth holding onto when a strategy document proposes WGS capacity as the goal.

## 4 · The animal reservoir question, stated as a genomics problem

This is where a genomic surveillance course has something specific and uncomfortable to contribute.

The question — *do animals maintain transmission that human screening cannot reach?* — is formally a **host-state reconstruction**, exactly the machinery Deep Dive 3 used to establish a single H5N1 spillover into cattle. Reconstruct ancestral hosts on the tree; count cross-species transitions; a monophyletic animal clade means a maintained animal cycle, animal sequences scattered among human ones mean repeated spillback from humans.

Three things stand between that idea and an answer, and they are worth being explicit about because the first two are usually left implicit.

**(a) The sampling asymmetry is extreme, and it points the wrong way.** Decades of active screening have produced human isolates and human samples in numbers that animal surveys cannot approach. Lesson 11 is unambiguous about what a discrete trait analysis does with that: **it places ancestry where sampling is dense.** A DTA on 500 human and 12 animal isolates will infer a human origin and human-to-animal spillover regardless of the truth. This is not a subtle bias to caveat; it is a result determined by the sample sizes before the data are examined.

The correct framing is a **structured coalescent** (Lesson 11) — human and animal demes with their own effective sizes connected by migration, so a deme can be large and barely sampled and the model can represent that. And even then, with Tbg1's homogeneity (§2), the honest output is a **bound**, not a point estimate: *the data are consistent with an animal-maintained cycle contributing up to X, and cannot exclude it below Y.*

**(b) There is very little signal to reconstruct with.** Host-state reconstruction rides on the tree. A clonal, monophyletic population gives a tree with almost no resolved internal structure, so there is little for the ancestral-state model to work on. Deep Dive 3 worked because H5N1 accumulates change fast and the cattle clade was unmistakable. Nothing here will be unmistakable.

**(c) Detection in an animal is not maintenance by animals.** Molecular identification of *T. b. gambiense* in pigs, dogs, small ruminants, duikers and mangabeys establishes that animals can be **infected**. Whether they sustain a transmission cycle independent of humans is a different claim requiring different evidence — infectivity to tsetse, duration of infection, vector contact rates, and ideally a demonstration of transmission in the absence of human cases. The experimental animal–*Glossina*–animal work showing retained infectivity over roughly three years is a piece of that argument, not the whole of it.

⚠ **The most likely failure mode here is a strong claim from a weak design**: a handful of animal sequences, a discrete trait analysis, and a headline about the reservoir threatening elimination. The design that would actually inform policy is deliberately sampled across hosts in the same foci at comparable intensity, analysed under a structured model, and reported as a bound.

## 5 · What genomics *can* deliver for gHAT, honestly

The short, real list. Every item maps to a decision.

**1 · Relapse versus reinfection — already delivered.** Whole genome sequencing of parasites from relapsed patients showed relapse is **regrowth of the original parasite population, not reinfection**. This is Lesson 12's internal-comparison design at its best: two samples from one person, a comparison that sidesteps every sampling-fraction problem in this course, and an answer that speaks to drug efficacy and follow-up duration rather than to transmission.

**2 · Species and subspecies identification.** Is this Tbg1? The minicircle assay (§3) exists because sequencing answered that question once, generally.

**3 · Drug-resistance monitoring, and this is the one to build now.** Acoziborole is being deployed as a single-dose oral cure. The history of this disease includes documented resistance mechanisms — the melarsoprol/pentamidine story and the *TbAT1*/P2 transporter. **A single-dose oral drug given widely in a low-transmission setting is exactly the selective environment in which a resistance marker would matter and in which its emergence would be hard to detect from treatment outcomes alone**, because outcomes are counted in a handful of cases per focus per year. A marker programme, built on the Deep Dive 4 model with a curated, graded genotype–phenotype catalogue, is the highest-value genomic investment available here. ⚠ Whether such a catalogue exists for acoziborole was not verified while writing; if it does not, building it is the gap.

**4 · Diagnostic-target integrity.** The malaria *pfhrp2/3* lesson (Deep Dive 4) transfers directly: a diagnostic that detects one target can be evaded by loss or variation of that target. The minicircle assay's 241 Tbg1-specific classes are a molecular target like any other, and periodic re-sequencing to confirm the target still holds across foci is cheap insurance.

**5 · Import versus residual transmission — the one that needs a decision today.**

## 6 · The archive, and why it is the point of this deep dive

Here is the argument, and it is the reason this deep dive exists in a course about outbreak genomics.

When a focus reaches zero and stays there, and then — in year three of the five-year clock — a case appears, exactly one question matters:

> **Is this an importation, or is it residual local transmission that was never interrupted?**

Those demand opposite responses. Importation means the focus held and the case came from elsewhere; the five-year clock survives. Residual transmission means the focus never cleared, the clock resets, and active screening must resume.

Genomics answers this question well (Lesson 12): does the new isolate fall within the local historical lineage, or does it cluster with sequences from elsewhere? Even in a homogeneous population, focus-level structure is the most likely place for what little differentiation exists to sit.

**But it is answerable only against a baseline that must have been collected before elimination.** You cannot go back and sequence the transmission you have just successfully stopped.

✱ **So the highest-value genomic act available for gHAT today is not an analysis. It is archiving** — systematically banking isolates, dried blood spots, skin snips and extracts from every remaining focus, with the Lesson 13 minimum metadata attached (collection date at real precision, focus and health zone, host species, specimen type, and the link to the case record), while there are still cases to bank. Every year of delay permanently removes a year of baseline.

And the specimen point from §1 returns here with force: **a blood-only archive is an archive of the wrong compartment.** If the dermal reservoir carries a meaningful share of the parasites that matter for transmission, and blood misses 30% of confirmed cases and most unconfirmed seropositives, then a bank built on blood alone will not answer the import-versus-residual question for precisely the infections that sustained transmission. Skin snips are cheap. The decision to take them is being made, by default, right now.

## 7 · Transferable lessons

1. **Run the arithmetic first, and be willing to rule out three of the four questions.** A clonal, monophyletic population cannot support linkage, chain or phylodynamic inference at any sequencing depth.
2. **When the target is scarce, go after a high-copy one.** The kinetoplast minicircle assay is genomics used once to design a field PCR — the most deployable form of the discipline.
3. **Sampling asymmetry between hosts is not a caveat, it is a determinant.** Human-dense, animal-sparse data will produce a human origin under discrete trait analysis whatever the truth. Structured coalescent, or a bound, or nothing.
4. **Detection in a host is not maintenance by that host.** Different claim, different evidence.
5. **The specimen decision can put the reservoir outside the sampling frame entirely.** Blood misses the skin.
6. **Archive before elimination.** The import-versus-residual question becomes the only question at exactly the moment it becomes unanswerable without a baseline.
7. **A single-dose drug deployed widely at low transmission is a resistance-surveillance problem** that treatment outcomes alone will not detect at these case numbers.

## 8 · Explain it in 60 seconds

> Sleeping sickness is close to gone — from over 26,000 cases a year in DRC in 1998 to a few hundred across Africa now — and the goal is zero transmission by 2030, verified by five consecutive years of no reported human cases.
>
> The worry is that transmission could carry on quietly while that criterion is met: in animals, in people who test positive but are never confirmed or treated, and in the **skin**, where the parasite persists and can still infect tsetse flies even when there is nothing detectable in the blood. In one set of studies the parasite was found in the skin of 41% of seropositive people whose blood tests were negative.
>
> Genomics is less use here than in any other case in this course. The parasite is essentially clonal — every isolate looks like every other — so you cannot build transmission chains or growth rates from it. What it can do is tell relapse from reinfection, identify the subspecies, and watch for drug resistance as the new single-dose treatment rolls out.
>
> And one thing more, which is urgent and unglamorous. Once a focus is declared clear, the only question that will matter is whether a new case was imported or was never actually eliminated. Genomes can answer that — **but only by comparison with samples banked beforehand.** Every year we do not archive is a year of baseline we can never get back.

## 9 · Read more

- Franco JR et al. *The elimination of human African trypanosomiasis: monitoring progress towards the 2021–2030 WHO road map targets.* PLOS NTD (2024) — PMC11073784
- *Do cryptic reservoirs threaten gambiense-sleeping sickness elimination?* **Trends in Parasitology** (2018) — the framing paper for §1
- *The elimination of Trypanosoma brucei gambiense? Challenges of reservoir hosts and transmission cycles: expect the unexpected.* One Health (2019)
- Capewell P et al. *The skin is a significant but overlooked anatomical reservoir for vector-borne African trypanosomes.* **eLife** (2016) — elifesciences.org/articles/17716
- *Extravascular dermal trypanosomes in suspected and confirmed cases of gambiense HAT.* **Clinical Infectious Diseases** (2021)
- *Dermal trypanosomes in seropositive suspects of gambiense HAT in Côte d'Ivoire.* **PLOS NTD** (2025) — journals.plos.org/plosntds, PMC12404639; and the Guinea prevalence study, PLOS NTD (2024), PMC11361743
- *Deep kinetoplast genome analyses result in a novel molecular assay for detecting T. b. gambiense-specific minicircles.* **NAR Genomics and Bioinformatics** 2022;4(4):lqac081
- Weir W, Capewell P et al. *Population genomics reveals the origin and asexual evolution of human infective trypanosomes* — and the Tbg1 monophyly and homogeneity literature generally
- *Whole genome sequencing shows sleeping sickness relapse is due to parasite regrowth and not reinfection* — PMC4721075
- *Molecular identification of T. b. gambiense in naturally infected pigs, dogs and small ruminants ... in Chad* — PMC7673351
- *Wildlife surveys detect T. b. gambiense in duikers and mangabeys in Gabonese historical and active foci* (2026)
- *The road to interruption of transmission of gambiense HAT in the DRC: an analysis of 25 years of routine data.* medRxiv 2025.10.21.25338447

⚠ **Grading.** Every reference above is a **SEARCH**-grade lead: identified from search results during authoring, not read in full, and the specific numbers attributed to each were not individually confirmed against the source. The dermal-reservoir percentages (67/9 blood, 71/41 skin, 17/25 post-treatment) and the DRC case trajectory (26,318 → 394) come from search extracts and should be checked before they enter a manuscript or a slide. See `sources/source-ledger.md`.
