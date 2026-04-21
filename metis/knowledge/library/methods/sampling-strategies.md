---
title: "Sampling Strategies"
domain: "methods"
tags:
  - sampling
  - surveys
  - design
  - cluster-sampling
  - probability-sampling
related:
  - "methods/study-designs.md"
  - "methods/surveillance-systems.md"
  - "disease-areas/hat-sleeping-sickness.md"
  - "methods/biostatistics-essentials.md"
phd_relevance: "high"
status: "current"
updated: "2026-03-30"
---
# Sampling Strategies

> Reference card — probability and non-probability sampling methods, sample size, and decision guidance.

---

## Probability Sampling

- **Simple random sampling (SRS):** Every unit has equal selection probability; gold standard but requires complete sampling frame
- **Systematic sampling:** Select every k-th unit from ordered list; simpler than SRS but beware periodicity in the list
- **Stratified sampling:** Divide population into homogeneous strata, sample within each; improves precision for subgroup estimates
- **Cluster sampling:** Randomly select clusters (villages, health facilities), then sample all or some units within; practical when no individual-level frame exists
- **Multistage sampling:** Combine approaches hierarchically (e.g., districts -> health areas -> villages -> households); standard for large national surveys (DHS, MICS)

## Non-Probability Sampling

- **Convenience:** Recruit whoever is accessible; fast but high risk of selection bias
- **Purposive:** Deliberately select information-rich cases; common in qualitative research
- **Snowball:** Existing participants recruit others; useful for hidden/hard-to-reach populations (e.g., people who inject drugs)
- **Quota:** Fill predefined quotas by key characteristics; structured but still non-random

## LQAS (Lot Quality Assurance Sampling)

- Classifies small areas (lots) as meeting or not meeting a coverage threshold
- Small sample per lot (typically 19); decision rule based on binomial probability
- Used in immunization and NTD program monitoring
- Strength: low cost, rapid, decentralized decision-making
- Limitation: classifies lots, does not precisely estimate coverage

## Cluster Surveys

- **WHO 30x7 design:** 30 clusters, 7 individuals per cluster; historically used for immunization coverage
- **Updated EPI survey methodology:** Now recommends probability-proportional-to-size (PPS) cluster selection with flexible cluster sizes
- Design effect (DEFF) accounts for within-cluster correlation (ICC); typical DEFF 1.5-3.0 for health outcomes
- Weight calculation: product of inverse selection probabilities at each stage

## Sample Size

- **Prevalence estimation:** n = Z^2 * p(1-p) / d^2; inflate by DEFF for cluster designs
- **Comparison of two proportions:** Requires specification of alpha, power, expected proportions in each group
- **Finite population correction:** Apply when sampling > 5-10% of the population
- **Non-response adjustment:** Inflate calculated sample by expected non-response rate (e.g., multiply by 1/0.90 for 10% non-response)

## Decision Tree: When to Use What

- Need precise population estimate + sampling frame exists -> SRS or stratified
- No individual sampling frame + geographically dispersed -> cluster or multistage
- Want subgroup comparisons with good precision -> stratified
- Rapid program classification (above/below threshold) -> LQAS
- Hard-to-reach or hidden population -> snowball or respondent-driven sampling
- Exploratory qualitative work -> purposive or theoretical sampling

## Current Developments (2025-2026)

- **Bias reduction remains the main sampling priority:** WHO's vaccination coverage cluster-survey manual, revised in **2021**, still represents the clearest operational standard for avoiding convenience-style shortcuts in field surveys.
- **Program monitoring is moving beyond simple 30x7 habits:** Contemporary survey guidance favors probability-proportional-to-size selection, explicit weights, and better documentation of segmentation and non-response handling.
- **LQAS is still evolving for elimination settings:** Recent NTD work has shown that LQAS decision rules can misclassify districts when diagnostics are imperfect or infection is spatially heterogeneous, especially near low-prevalence thresholds.
- **Practical implication:** In 2026, the right question is not "what sample size formula do I know?" but "what decision is this sample meant to support, under what operational constraints, and with what diagnostic performance?"

## Practical Examples

- **Immunization coverage surveys:** Multistage cluster designs remain standard when no household-level national frame exists and programme managers need district-level coverage estimates.
- **NTD monitoring:** Kazienga et al. (2022) showed that two-stage LQAS frameworks may need more clusters and highly specific diagnostics in low-endemic settings.
- **Coverage evaluation after MDA:** Multicountry comparisons of NTD coverage surveys showed that stratified LQAS-style designs can be faster and cheaper, but design choice depends on whether classification or estimation is the primary goal.
- **Vaccine roll-out monitoring:** Recent pilot work on LQAS for new-vaccine evaluation illustrates how sampling can support quick operational decisions when full prevalence estimation is not necessary.

## Key References

- Levy, P. S. & Lemeshow, S. (2008). *Sampling of Populations: Methods and Applications*. 4th ed. Wiley.
- WHO (2018). *Vaccination Coverage Cluster Surveys: Reference Manual*. WHO/IVB/18.09.
- Turner, A. G. et al. (1996). Sampling strategies for the WHO EPI cluster survey. *Int J Epidemiol*, 25(1), 38-48.
- Valadez, J. J. (1991). *Assessing Child Survival Programs in Developing Countries: Testing Lot Quality Assurance Sampling*. Harvard University Press.
- Bennett, S. et al. (1991). A simplified general method for cluster-sample surveys of health in developing countries. *World Health Statistics Quarterly*, 44(3), 98-106.
- **WHO vaccination coverage cluster surveys manual:** https://www.who.int/publications/i/item/WHO-IVB-18.09
- **WHO IRIS record for the manual:** https://iris.who.int/handle/10665/272820
- **Kazienga A et al.** Two-stage lot quality assurance sampling framework for monitoring and evaluation of neglected tropical diseases. *PLOS Neglected Tropical Diseases.* 2022. https://pubmed.ncbi.nlm.nih.gov/35394996/
- **Mwingira U et al.** A multicountry comparison of three coverage evaluation survey sampling methodologies for neglected tropical diseases. *American Journal of Tropical Medicine and Hygiene.* 2020. https://pubmed.ncbi.nlm.nih.gov/32840202/
- **Hora R et al.** Lot quality assurance sampling for coverage evaluation of a new vaccine: a pilot study. *Vaccine X.* 2024. https://pubmed.ncbi.nlm.nih.gov/39559738/

## Learning Path

- Start with `06_library/courses/epidemiology-foundations/` and `06_library/courses/surveillance-methods/`.
- Pair this card with `06_library/methods/biostatistics-essentials.md` because weighting, design effects, precision, and inference depend on the sampling design.
- Use `06_library/methods/outbreak-investigation.md` when rapid field sampling is being planned during acute events.
- In the Learning Hub, this card aligns primarily with **Sampling strategies** and also supports **Surveillance systems** and **Epidemiological methods**.

---

*Last updated: 2026-03-30 | Enriched with current survey and LQAS guidance*
