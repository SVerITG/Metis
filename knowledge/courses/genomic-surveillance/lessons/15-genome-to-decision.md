# Lesson 15 — From genome to decision: what genomic surveillance is actually for

> **Concept map**
> **Builds on** — the whole course. This is where the chain from Lesson 0 terminates.
> **Connects to** — every deep dive, each of which is assessed against the test in Section 2.
> **Leads to** — the standing question you should ask of every genomic surveillance activity you fund, run or review.

## Why this matters

A genomic surveillance programme can be technically excellent and epidemiologically useless. This is not a rhetorical warning; it is the observed failure mode. Sequences accumulate, trees are built, dashboards update, papers appear — and no decision is different from what it would have been without any of it.

That programme is vulnerable, and correctly so. When budgets contract, "we produced 8,400 genomes" is not a defence. "We identified three importation events that changed vaccination targeting, excluded two suspected nosocomial clusters that would have closed a ward, and established that the outbreak lineage carried no diagnostic-escape mutation" is a defence.

This lesson is about producing the second kind of programme.

## Learning objectives
By the end of this lesson you will be able to:

- **List** the concrete decisions genomic surveillance can change, and name the analysis behind each.
- **Apply** the "so what" test to a proposed genomic surveillance activity before it is funded.
- **Specify** the timeliness requirement implied by a decision, working backwards from it.
- **Write** a genomic finding for an incident management team rather than for a journal.
- **Recognise** when the correct genomic finding is "nothing has changed", and why that is a result.

## Prerequisites
Lessons 0–14.

---

## Section 1 · The decisions genomics actually changes

Not the questions it answers — Lesson 0 covered those. The **operational decisions** that come out differently.

| Decision | Analysis | Question |
|---|---|---|
| **Close or reopen a ward** | Cluster analysis; exclusion of a suspected link | Q1 |
| **Escalate or stand down a suspected outbreak** | Genomic distance versus local background | Q1 |
| **Redirect contact tracing to a new setting** | Compatible genomes with no known contact (Lesson 12's top-right cell) | Q1 |
| **Change border or travel measures** | Introductions versus local transmission | Q2 |
| **Target vaccination geographically** | Where the transmitting lineage is, versus where cases are reported | Q2 |
| **Search for an animal reservoir** | Host-state reconstruction; repeated independent spillovers | Q2 |
| **Extend or end an outbreak response** | Continued diversification versus a closing epidemic | Q3 |
| **Reallocate surveillance effort** | tMRCA-to-detection gap; unobserved transmission fraction | Q3 |
| **Switch first-line treatment** | Resistance-marker frequency crossing a policy threshold | Q4 |
| **Withdraw or keep a diagnostic** | Target-site mutations; *pfhrp2/3* deletions | Q4 |
| **Change the vaccine composition** | Antigenic evolution relative to the current strain | Q4 |
| **Investigate a survivor-associated flare-up rather than a new spillover** | Long branch attaching to an old lineage | Q1/Q2 |
| **Retain confidence in the current response** | **No fitness-altering mutations, no lineage dominance** | Q4 |

That last row is the one people forget, and it was one of the flagship study's main conclusions. **"Nothing has changed" is a result.** It requires the same work as a positive finding, and it justifies continuing the current response, the current diagnostics and the current case definitions rather than churning them on speculation. A response that does not know whether the pathogen has changed will eventually assume it has.

## Section 2 · The "so what" test

Before funding, running or expanding a genomic surveillance activity, answer four questions in order. If you cannot, you are producing data, not surveillance.

**1. What decision could this change?** Name it, and name the person or body who makes it. "Improve understanding" is not a decision.

**2. What result would change it, and in which direction?** State the finding in advance: *"If more than 10% of isolates carry marker X, we change first-line treatment."* Deciding the threshold before seeing the data is the difference between surveillance and interpretation-after-the-fact.

**3. By when must the answer arrive?** Work backwards from the decision point. A result that arrives after the decision was made has zero value, however good it is.

**4. What is the confidence needed, and does the sampling support it?** Lesson 13. A decision requiring a proportion estimate needs a representative frame; a decision requiring detection needs enough sequences to detect at the relevant prevalence.

⚠ **Most genomic surveillance activities fail question 1, and almost all fail question 2.** Failing question 1 means you are doing research, which is legitimate — but it should be funded, staffed and evaluated as research, not as surveillance.

## Section 3 · Timeliness, derived from the decision

Timeliness requirements are not universal; they follow from the decision.

| Decision | Required turnaround | Implication |
|---|---|---|
| Ward closure during an active cluster | 24–72 hours | On-site sequencing, no batching, pre-agreed pathway |
| Outbreak response steering | Days to 1–2 weeks | In-country sequencing; weekly reporting cadence |
| Treatment policy change | Months | Batching fine; representativeness is what matters |
| Vaccine strain selection | Annual/biannual cycle | Global aggregation; comparability dominates |
| Retrospective evaluation | Any | Completeness matters, speed does not |

**Measure the distribution, not the mean.** A median of 6 days with a 90th percentile of 40 days is a system that works for the average case and fails exactly when the sample came from somewhere remote — which is where the epidemiologically interesting cases are.

✱ **The Bundibugyo analysis is a good illustration of matching cadence to purpose.** A 100-day window posted publicly as a work in progress, explicitly preliminary, with the sensitivity analyses that make preliminary results usable. It is not a paper and it does not pretend to be. **Publishing the analysis at response cadence, with the uncertainty visible, is a different and more useful act than publishing a polished version a year later** — and virological.org exists precisely to make that possible.

## Section 4 · Writing for an incident management team

A genomic finding for an incident manager is not a paper abstract. It is four sentences, in this order.

> **1. What we found.** "The 47 sequences from Health Zone A form a single cluster within two substitutions, dating to mid-June."
>
> **2. What it means epidemiologically.** "This is consistent with a single introduction followed by local transmission, rather than repeated importation from Health Zone B."
>
> **3. What it does not mean.** "It does not identify who infected whom, and 12 of the 59 reported cases in this zone were not sequenced."
>
> **4. What we recommend, and with what confidence.** "We suggest concentrating contact tracing within Health Zone A rather than at the boundary. Moderate confidence: the conclusion depends on sequences from Health Zone B, which are sparse."

Rules that make this work:

- **No jargon without a plain-English gloss.** "tMRCA" becomes "the common ancestor of these cases dates to around". "Ne" does not appear at all.
- **State what you did not sequence, every time.** In one clause. It is the single most important limitation and it is the easiest to omit.
- **Give confidence in words, calibrated and consistent.** High / moderate / low, used the same way every week, is more useful than a credible interval nobody reads.
- **Separate finding from recommendation.** The finding is yours. The recommendation is advice to someone whose constraints you do not fully know.
- **Never name individuals** (Lesson 12).

## Section 5 · Evaluating a programme

Lesson 13 gave the technical metrics. Add these, and put them first.

**1. Decisions changed.** A log. Date, decision, genomic finding, what would have happened otherwise. Maintaining this log is a small ongoing task and it is the single best protection a programme has when it is asked to justify itself.

**2. Time from result to recipient.** Not to database, not to publication — **to the person who can act.** Many programmes are timely up to deposition and then lose weeks to reporting.

**3. Questions declined.** A mature programme says "sequencing cannot answer that" regularly. A programme that always finds something is over-interpreting.

**4. Analytical independence.** Can the programme analyse its own data, or does it export sequences and import conclusions? This is the capacity question from Lesson 14, and it is measurable: who produced the last five analyses?

**5. Cost per decision-relevant result.** Cost per genome is the wrong denominator — it rewards volume. Cost per result that changed something rewards the right thing, and it is usually a much larger and much more honest number.

## Section 6 · When genomics is the wrong tool

Saying so is part of professional competence.

- **The pathogen evolves too slowly for the question.** Lesson 1's arithmetic. Sequencing mpox from an animal reservoir to resolve individual transmissions will not work at any sequencing depth.
- **The question is about magnitude, not relatedness.** How many people are infected is a case-ascertainment problem. Ne is not prevalence (Lesson 10).
- **The decision does not depend on the answer.** If the response is identical whether it is one introduction or five, sequencing is expensive curiosity.
- **The sampling cannot support the inference.** A phylogeographic conclusion from a dataset with twentyfold variation in sequences-per-case is not a weak conclusion; it is an unsupported one.
- **The money is better spent elsewhere.** In a programme where 40% of cases have no recorded onset date, fixing the metadata (Lesson 13) buys more epidemiology per euro than sequencing more samples. **The opportunity cost of a sequencer is often a data manager, and the data manager frequently wins.**

## Section 7 · The course, closed

The spine, restated now that it has been earned:

> **A pathogen genome is a clock and a family tree at the same time. Every claim in genomic surveillance answers one of four questions — is this the same outbreak, where did it come from, how fast is it spreading, has the pathogen changed. And what decides whether the answer is trustworthy is almost never the sequencer; it is the sampling and the metadata.**

Both halves have now been argued. The first half made the field learnable: four questions, one chain from molecule to decision, one arithmetic (rate × length × serial interval) that tells you in advance what any dataset can resolve. The second half is why the course does not go out of date. The chemistry will change — it changed twice while this course was being written. The failure modes will not. Unequal sampling will still bias phylogeography. Ct thresholds will still select on severity. Receipt dates will still be substituted for collection dates. Effective population size will still be read as prevalence. A tree will still be read as a transmission chain.

Which leaves the standing question, the one to carry out of this course and into every meeting where a tree is on the screen:

> **What decision would come out differently, and does the sampling support it?**

## Practice — the capstone

Design a genomic surveillance activity for a pathogen and setting you know. One page:

1. **The decision** it will change, and who makes it.
2. **The question**, as one of the four.
3. **The sampling frame**, and the sequences-per-case you expect by stratum.
4. **The arithmetic**: rate × genome length × serial interval, and therefore what it can and cannot resolve.
5. **The platform**, argued from arrival rate, latency and operating environment.
6. **The minimum metadata set**, and how sequences link to case records.
7. **The timeliness requirement**, derived backwards from the decision.
8. **The analysis**, named — and where it will be run, and by whom.
9. **Sharing**: platform, licence, and when.
10. **The result that would change the decision**, stated in advance.
11. **The limitation** you already know you will have to write.

If you can write that page, you can run a programme. Points 10 and 11 are the ones that separate a proposal from a wish.

## In one paragraph

Genomic surveillance exists to change decisions, and a programme that cannot name the decisions it changed is producing data rather than surveillance. The test is four questions asked before funding: what decision, what result would change it and in which direction, by when, and does the sampling support the required confidence — with most activities failing the first and almost all failing the second. Timeliness is derived from the decision rather than asserted, and it should be measured as a distribution because the tail is where the interesting cases are. Findings should reach incident managers as four sentences — what we found, what it means, what it does not mean, what we recommend and with what confidence — always including what was not sequenced. And the professional skill that takes longest to acquire is saying that sequencing is the wrong tool: when the clock is too slow, when the question is about magnitude, when the decision does not depend on the answer, or when the same money spent on metadata would buy more epidemiology.
