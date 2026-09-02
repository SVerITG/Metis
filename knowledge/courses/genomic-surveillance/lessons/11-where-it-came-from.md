# Lesson 11 — Where it came from: phylogeography, introductions, and the sampling bias that eats it

> **Concept map**
> **Builds on** — Lesson 9 (a time tree) and Lesson 10 (the same sampling problem, now in space).
> **Connects to** — Lesson 13, which is the systematic treatment of the bias this lesson keeps running into.
> **Leads to** — Deep Dive 3, where phylogeography across *hosts* rather than places establishes a single H5N1 spillover into cattle.

## Why this matters

"Where did it come from?" is the question decision-makers ask first and the question genomics answers least reliably. It is also the one where the gap between what the software outputs and what the data support is widest.

The mechanics are straightforward: treat location as a character that evolves along the tree, reconstruct ancestral states, read off where lineages were and when they moved. The software returns confident, colourful, mappable answers.

The problem is equally straightforward and much less often stated: **ancestral state reconstruction assumes your samples represent the populations they came from.** They do not. Sequences come from where sequencing happens — capital cities, referral hospitals, well-funded countries, health zones with a functioning laboratory. Feed unequal sampling into a phylogeographic model and it will confidently place origins where you sequenced most.

Handle this well and phylogeography is one of the most valuable things genomics offers. Handle it naively and you produce a map that is a picture of your own laboratory network.

## Learning objectives
By the end of this lesson you will be able to:

- **Explain** discrete-trait phylogeography and identify its sampling-bias failure mode.
- **Say** why structured coalescent methods are less biased, and what they cost.
- **Interpret** a count of introductions, and state what it depends on.
- **Apply** the same machinery to hosts rather than places, for One Health questions.
- **Write** a phylogeographic conclusion with its sampling caveat built into the sentence.

## Prerequisites
Lessons 0–10.

---

## Section 1 · Discrete trait analysis — the standard approach

Each tip carries a **location** (country, province, health zone). Treat location as a discrete character evolving along the tree under a continuous-time Markov chain — the same mathematical machinery as a substitution model in Lesson 8, with locations in place of nucleotides.

The model estimates migration rates between locations and reconstructs the location of every internal node. Outputs:

- **Ancestral locations** with posterior support at each node.
- **Markov jump counts** — the estimated number of transitions between each pair of locations.
- **BSSVS** (Bayesian stochastic search variable selection) — identifies which migration routes have support, sparsifying an otherwise dense matrix.

It is available in BEAST X and it is what most published phylogeography uses.

### The failure mode, precisely

Discrete trait analysis (DTA) treats location as a **trait of the lineage**, evolving on a tree whose shape was determined by the coalescent — which knows nothing about location. The consequence: **the model has no concept of how many infections exist in each location, only of how many sequences you gave it.**

So:

- A location with many sequences is inferred as ancestral, because most of the tree is there.
- A location with few sequences appears to receive rather than export.
- Unsampled locations do not exist, and transmission through them is attributed to the sampled locations either side.

⚠ **The worked example everyone should carry.** Country A sequences 5,000 cases. Country B, next door, sequences 50. DTA will very likely infer that the epidemic originated in A and spread to B — regardless of the truth. The pattern is not subtle and it is not rare, and it maps directly onto global inequities in sequencing capacity. **Phylogeography done naively encodes the geography of laboratory funding as the geography of the epidemic**, and then publishes it as a finding about a country.

## Section 2 · Structured coalescent — the better-behaved alternative

The structured coalescent models the epidemic as **subpopulations connected by migration**, each with its own effective population size, and models coalescence *within* demes and migration *between* them.

The crucial difference: it **separates population size from sampling intensity**. A deme can be large and barely sampled, and the model can represent that; DTA cannot.

- Implementations: `MASCOT`, `BASTA`, and the exact structured coalescent (rarely tractable).
- **Substantially less biased by unequal sampling** — the main reason to use it.
- **Costs:** more parameters, much heavier computation, and practical limits on the number of demes. Analyses are typically restricted to a handful of locations.

**Practical guidance:** if sampling is grossly unequal across your locations and the origin-versus-recipient conclusion matters, DTA is not adequate. Use a structured method, or aggregate to fewer, better-sampled units, or subsample to equalise (Section 4), or state the limitation as a limitation rather than a caveat.

**Continuous phylogeography** — relaxed random walk models over latitude/longitude rather than discrete units — is a third option, giving diffusion rates and dispersal velocities. It suits spatially continuous spread (rabies in a wildlife population, an epidemic wave across a landscape) and inherits the same sampling problem in continuous form.

## Section 3 · Counting introductions

A very common and very useful analysis: **how many separate times was this pathogen introduced into this place?** Each introduction is a distinct clade of local sequences descending from a non-local ancestor.

Why it matters operationally: it discriminates between two situations demanding opposite responses.

- **Many introductions, little local spread** → the problem is at the border, in travel, in importation. Control there.
- **Few introductions, extensive local spread** → the problem is domestic transmission. Border measures will not help.

**What the count depends on** — all four of these, and none of them is the truth:

1. **Local sampling fraction.** Sequence more locally and single introductions resolve into several.
2. **External sampling.** Introductions from unsampled places may be misassigned or merged.
3. **The clustering rule.** "A local clade descending from a non-local parent" needs a support threshold, and different thresholds give different counts.
4. **Time window.** Longer windows accumulate more.

✱ **So an introduction count is not a property of the epidemic; it is a property of the epidemic and your surveillance jointly.** Report it as a minimum — "at least N independent introductions" — which is exactly the phrasing used in careful mpox clade Ib work describing multiple introductions into a country.

## Section 4 · Subsampling, and why it is not cheating

If unequal sampling biases phylogeography, the direct fix is to **make it equal**: subsample so each location contributes comparably, or in proportion to case counts rather than to sequencing capacity.

Standard practice in Nextstrain builds, which subsample by region and time to keep a global build both tractable and less lopsided.

**Doing it well:**

- Subsample proportionally to *cases*, not to sequences.
- Also balance across **time**, or a period of intense sequencing dominates the tree.
- **Repeat with several random subsamples** and check the conclusion holds. A phylogeographic result that changes across replicate subsamples is not a result.
- Report the scheme, precisely enough to reproduce.

⚠ **What subsampling cannot fix: locations with zero sequences.** No amount of statistical care recovers a country that never sequenced. This is why sequencing equity (Lesson 14) is a *methodological* issue and not only a fairness issue — the analysis is wrong for everyone when part of the map is empty.

## Section 5 · The same machinery, applied to hosts

Replace "location" with "host species" and phylogeography becomes the core tool of One Health genomics. The tree now reconstructs ancestral *hosts* and counts *cross-species jumps*.

This is how the H5N1 dairy cattle story was established (Deep Dive 3): epidemiological information plus genomic analysis supported **a single spillover** of a reassorted genotype (B3.13) into cattle in late 2023, with cattle sequences forming a single clade — and then, in January 2025, a **separate, independent** introduction of a distinct genotype (D1.1). One clade means one jump; two clades means two. The virus then disseminated through cattle movement and was reintroduced from cattle back into other species, which the tree shows as lineages exiting the cattle clade.

The same approach addresses questions closer to this course's home ground. The animal reservoir question in gambiense HAT — whether pigs, dogs, small ruminants, or the duikers and mangabeys detected in Gabonese foci maintain transmission that human screening cannot reach — is exactly a host-state reconstruction problem. **And it is exactly the problem where sampling bias is worst**, because human sampling is orders of magnitude denser than animal sampling. A tree built from 500 human isolates and 12 animal isolates will place ancestry in humans whatever the truth. The methodological lesson transfers directly: this is a structured-coalescent problem, not a DTA problem, and its honest answer is a bound rather than a point estimate.

## Section 6 · Writing a phylogeographic conclusion

Weak: *"The outbreak originated in Mongbwalu health zone."*

Better, and closer to how the Bundibugyo authors actually wrote it: *"Genomes from Mongbwalu showed substantial diversity and emerged from relatively deep parts of the tree, suggesting Mongbwalu as a possible starting point for the outbreak."*

Look at what the second sentence does:

- States the **observation** (diversity, deep position), not just the conclusion.
- Uses **"suggesting"** and **"possible"** — hedges that are load-bearing, not decorative.
- Leaves room for the alternative that Mongbwalu was simply sampled early and well.

**A three-part template:**

1. The genomic observation.
2. The epidemiological interpretation, hedged in proportion to the sampling.
3. The alternative explanation that sampling could produce, and why you do or do not favour it.

Add one sentence giving sequences-per-case by location. If you cannot, that is the finding.

## Practice

Take a published phylogeographic analysis and:

1. Find the number of sequences per location. Then find the number of *cases* per location. Compute sequences-per-case. How many-fold does it vary?
2. Check whether the inferred origin is also the location with the highest sequences-per-case.
3. Determine whether DTA or a structured method was used, and whether the choice is justified.
4. Look for subsampling; if present, check whether replicates were run.
5. Rewrite the abstract's origin claim using the three-part template.

## In one paragraph

Phylogeography reconstructs ancestral locations by treating place as a character evolving on the tree, and its standard implementation — discrete trait analysis — has no way to know that a location with few sequences may have many infections, so it systematically infers origins where sequencing is dense. Structured coalescent methods separate population size from sampling intensity and are the right tool when that conclusion matters, at the cost of computation and a limited number of demes. Introduction counts are jointly a property of the epidemic and of your surveillance, so report them as minima. The same machinery applied to hosts is how a single H5N1 spillover into cattle was established, and it is the right frame for the animal-reservoir question in gambiense HAT — where the sampling asymmetry between humans and animals is so extreme that only a bound is honest.
