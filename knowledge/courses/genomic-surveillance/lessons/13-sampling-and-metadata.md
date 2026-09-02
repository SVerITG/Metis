# Lesson 13 — Sampling and metadata: the two things that decide whether any of it is true

> **Concept map**
> **Builds on** — every previous lesson, each of which ran into this problem and deferred it.
> **Connects to** — Lesson 14 (what you can share) and Lesson 15 (what you can decide).
> **Leads to** — the limitations paragraph of every deep dive.

## Why this matters

This is the lesson the course has been building towards, and it is placed here deliberately. Taught on day one it sounds like a caveat. Taught after you have seen a Ct threshold select cases, a coverage filter select them again, a phylogeographic model infer origins from sequencing density, and a SkyGrid curve bend because sampling weakened, it reads as what it is: **the dominant determinant of whether a genomic surveillance system produces knowledge or artefacts.**

The second half of this course's spine says it plainly: *what decides whether the answer is trustworthy is almost never the sequencer; it is the sampling and the metadata.* A programme with a modest sequencer, a defensible sampling frame and complete metadata beats a programme with a NovaSeq, convenience sampling and a spreadsheet of receipt dates. This is not a consolation for under-resourced programmes. It is the actual ordering of importance.

## Learning objectives
By the end of this lesson you will be able to:

- **Choose** a sampling strategy for a stated surveillance objective and justify it.
- **Calculate** the number of sequences needed to detect a variant at a given prevalence, and explain why the real number is larger.
- **Specify** a minimum metadata set and say what each field enables.
- **Evaluate** a genomic surveillance system on representativeness, timeliness, coverage and completeness.
- **Draw** the sampling cascade for a study and state the direction of every loss.

## Prerequisites
Lessons 0–12.

---

## Section 1 · Four sampling strategies, four different questions

There is no general-purpose sampling frame. The frame follows the objective, and a programme that has not named its objective is sampling by convenience whether it admits it or not.

### 1. Representative / random sampling
A defined random fraction of all diagnosed cases.

- **Answers:** what lineages are circulating and in what proportions; population-level trends; phylodynamics.
- **Requires:** a case register to sample from, and discipline to sequence what is selected rather than what is convenient.
- **The only frame that supports proportion estimates.** "Lineage X is 40% of infections" is a claim that requires this and is routinely made without it.

### 2. Sentinel sampling
Everything (or a fixed fraction) from a fixed set of sites.

- **Answers:** trends over time, consistently. Cheaper and more sustainable.
- **Trade-off:** representative of the sentinel sites' catchments, not the country. Good for change detection, poor for national proportions.

### 3. Targeted / risk-based sampling
Deliberately enriched: vaccine breakthroughs, severe or fatal cases, travellers, treatment failures, unusual clinical presentations, diagnostic anomalies (S-gene target failure, *pfhrp2* discordance).

- **Answers:** is something unusual happening in this specific high-information group.
- **Efficient for detection**, and **completely unusable for proportions.** Mixing targeted and representative sequences into one dataset and reporting lineage proportions is a routine and serious error.

### 4. Universal / census sequencing
Everything that tests positive, subject to a quality gate.

- What INRB did in Ituri: **all PCR-positive samples with Ct < 31.**
- The best available frame for an outbreak of moderate size, and still not random — the Ct gate selects, as Lesson 3 established, and detection itself selects.

⚠ **The failure this taxonomy exists to prevent: analysing a mixture of frames as though it were one.** National datasets are commonly a blend of routine sentinel, outbreak investigation, traveller screening and research studies. Each has a different selection process. Pooled and analysed as one, the resulting "national picture" is a composite of four different populations, and the apparent trends can be produced entirely by shifts in the mix. **Record the sampling frame as a field on every sequence.** It is the single highest-value metadata item almost nobody collects.

## Section 2 · How many sequences do you need?

### The baseline calculation
To detect at least one case of a variant circulating at prevalence *p*, with probability 1 − α, assuming simple random sampling:

> **n = ln(α) / ln(1 − p)**

For α = 0.05, this is very nearly **n ≈ 3/p**:

| Variant prevalence | Sequences needed (95% confidence of ≥1) |
|---|---|
| 10% | ~29 |
| 5% | ~59 |
| 1% | ~299 |
| 0.5% | ~598 |
| 0.1% | ~2,995 |

To *estimate* a proportion rather than merely detect it, you need considerably more — the usual proportion-precision formula — and to detect **change** in a proportion, more again.

### Why the real number is larger

The formula assumes simple random sampling from the population of infections. Nothing in Lesson 3 or Lesson 5 was simple random sampling. Published work on sample size for pathogen variant surveillance in the presence of biological and systematic biases makes the same point formally: the required sample size inflates once you account for the layered selection — detection, care-seeking, testing, Ct threshold, sequencing success, metadata completeness.

Three inflators to reason about explicitly:

1. **Case ascertainment.** You sample from *detected* cases, not infections. If detection is 20%, and the variant is associated with milder disease, it is under-represented before sequencing begins.
2. **Geographic clustering.** A new variant emerges somewhere, not everywhere. National random sampling detects a locally concentrated variant later than targeted local sampling would.
3. **The sequencing cascade.** The Ct gate and coverage filter remove low-load samples, and load is not independent of lineage, timing or severity.

✱ **The practical consequence.** "We sequence 300 samples a month, so we can detect a variant at 1%" is wrong in a knowable direction. A defensible version states the assumed ascertainment fraction and the sequencing success rate, and reports the detectable prevalence as a range.

## Section 3 · Metadata is the bottleneck

**A sequence without metadata is close to worthless, and this is the most consistently underestimated fact in genomic surveillance.**

Consider what is lost:

- **No collection date** → no time tree, no tMRCA, no phylodynamics. Half this course becomes inapplicable.
- **No location** → no phylogeography, no cluster mapping, no importation-versus-local determination.
- **No host or specimen type** → no One Health inference, and confounded comparisons.
- **No link to the case record** → no severity, no outcome, no vaccination status, no exposure. **No ability to answer any question about whether the pathogen's change matters.**

### The minimum metadata set

| Field | Why it is needed | Common failure |
|---|---|---|
| **Collection date** | Everything time-based | **Receipt or sequencing date substituted.** Shifts every node date, silently |
| Date precision | Honest uncertainty | "2026-05" recorded as "2026-05-01" |
| Location (defined admin level) | Phylogeography, clusters | Residence, facility and reporting unit conflated |
| Host species | One Health | Assumed human |
| Specimen type | Comparability | Not recorded |
| Sampling frame | **Which population this represents** | Almost never recorded |
| Case ID linking to surveillance | Everything clinical and epidemiological | The hard one; often absent |
| Sequencing platform, pipeline, basecaller version | Comparability, reproducibility (Lessons 4–5) | Rarely recorded |
| Ct value | Interpreting coverage and quality | Discarded after the run |

Then, from the case record: onset date, age, sex, outcome, vaccination status, treatment, travel, exposure, facility.

⚠ **The collection-date substitution deserves its own warning.** Using the date the laboratory received or sequenced a sample, instead of the date it was collected, shifts every tip later by the transport and batching delay — and that delay is longer for remote areas. The result is a tree in which remote health zones systematically appear *later*, which then feeds phylogeographic inference and produces a spurious centre-to-periphery spread pattern. **A metadata error becomes an epidemiological conclusion.**

### The linkage problem
Linking a sequence to its case record is technically trivial and organisationally the hardest part of running a genomic surveillance system. Laboratory and surveillance systems are usually separate, with separate identifiers, separate custodians and separate legal bases. Programmes that solve this produce far more value per genome than programmes that sequence more.

✱ **The rule that follows: adding a metadata field is often worth more than adding a sequencer.** A programme sequencing 100 genomes a month with complete case linkage can answer severity, vaccine-effectiveness and outcome questions. A programme sequencing 1,000 with laboratory data alone can answer none of them.

## Section 4 · The sampling cascade — draw it

The figure this course keeps asking for:

```
   Infections in the population                     ??? (unknown)
        ↓  care-seeking, access, severity
   Cases presenting to health services            e.g. 5,200
        ↓  testing policy, test availability
   Cases tested                                        4,100
        ↓  test sensitivity, timing
   Cases PCR-positive                                  3,748
        ↓  sample retained, transported, Ct < 31
   Samples selected for sequencing                       712
        ↓  library, run, coverage threshold
   Genomes produced                                      626
        ↓  editing-signature and outlier filtering
   Genomes analysed                                      525
        ↓  metadata complete enough for the analysis
   Genomes in the phylogeographic analysis                ???
```

*(The 3,748 / 626 / 525 figures are the real reported Bundibugyo numbers; the intermediate steps are illustrative, because they are exactly the steps almost never reported.)*

**Every arrow is a selection with a direction.** Write the direction next to each one and you have your limitations paragraph, quantified rather than gestured at. This costs one figure and it is the most honest thing a genomic surveillance paper can contain.

## Section 5 · Evaluating a genomic surveillance system

Judge a system on these, not on genome counts.

**1. Representativeness.** Sequences per case, by location, by time, by severity, by age. **The ratio, not the count.** Report the range across strata; if it varies twenty-fold, every spatial inference is suspect.

**2. Timeliness.** The distribution — not the mean — of collection-to-result, and collection-to-public-availability. Report medians and 90th percentiles. A system with a 14-day median and a 60-day tail has a tail problem that a mean conceals.

**3. Coverage.** What proportion of cases are sequenced, and does it vary by the strata that matter?

**4. Completeness.** Percentage of sequences with each minimum metadata field. Publish the table. It improves quickly once it is visible.

**5. Data quality.** Genome completeness distribution, contamination rate, negative-control failure rate, replicate concordance.

**6. Utility — the one that is never measured.** How many decisions did this system change in the last year? Lesson 15 argues this is the metric that should sit at the top, and that its absence is why genomic surveillance programmes are vulnerable when budgets contract.

## Section 6 · Sampling for different objectives — a summary

| Objective | Frame | Volume driver | Key metadata |
|---|---|---|---|
| Lineage proportions nationally | Representative random | Precision on the proportion | Date, location, frame |
| Detect a new variant early | Targeted + sentinel | Detectable prevalence (≈3/p) | Date, location, clinical anomaly |
| Outbreak reconstruction | Universal within outbreak | All available cases | Date, health zone, case ID, onset |
| Importation vs local | Representative + traveller | Enough of each | Travel history, date, location |
| Severity of a lineage | Representative + case linkage | Outcome numbers | **Outcome, vaccination, age** |
| AMR trends | Representative among isolates | Precision on resistance prevalence | Specimen, treatment, phenotype |
| Reservoir / One Health | Targeted across hosts | Coverage of each host | **Host species, geography** |

## Practice

Take a genomic surveillance system you know:

1. Name its objective in one sentence. If it has more than one, name the frame for each.
2. Compute sequences-per-case for the three largest and three smallest units. Report the ratio.
3. Compute the metadata completeness percentage for the ten fields in Section 3.
4. Compute the median and 90th percentile collection-to-result time.
5. List the decisions the system changed in the past twelve months.

Item 5 is the hardest to answer and the most important. If the list is empty, the problem is not the sequencing.

## In one paragraph

Sampling frame and metadata determine whether genomic surveillance produces knowledge or artefacts, and both are decided by people rather than by instruments. Four frames answer four different questions, and mixing them into one dataset produces trends that are artefacts of the mix — so the sampling frame belongs as a field on every sequence. Detecting a variant at prevalence *p* needs roughly 3/p sequences under random sampling, and more once ascertainment, geographic clustering and the sequencing cascade are accounted for. Metadata is the binding constraint: a sequence without a collection date cannot be dated, without a location cannot be mapped, and without a link to the case record cannot answer whether any of it matters — and substituting the receipt date for the collection date converts a clerical shortcut into a false conclusion about spread. Draw the cascade from infections to analysed genomes, label the direction of every loss, and judge the system on representativeness, timeliness and decisions changed rather than on genomes produced.
