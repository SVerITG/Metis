---
title: "Diagnostic Test Evaluation"
domain: "methods"
tags:
  - diagnostics
  - sensitivity
  - specificity
  - ROC
  - predictive-value
  - LR
related:
  - "methods/study-designs.md"
  - "disease-areas/hat-sleeping-sickness.md"
  - "methods/surveillance-systems.md"
phd_relevance: "high"
status: "current"
updated: "2026-03-29"
---
# Diagnostic Test Evaluation

> Reference card — measures of test accuracy, study designs, and reporting standards for diagnostic evaluations.

---

## Core Measures

- **Sensitivity (Se):** Proportion of true positives correctly identified; Pr(T+ | D+)
- **Specificity (Sp):** Proportion of true negatives correctly identified; Pr(T- | D-)
- **Positive Predictive Value (PPV):** Pr(D+ | T+); depends heavily on prevalence
- **Negative Predictive Value (NPV):** Pr(D- | T-); also prevalence-dependent

## PPV Collapse in Low-Prevalence Settings

- As prevalence drops, PPV plummets even with highly specific tests
- Critical implication for elimination-phase diseases: most positives may be false positives
- Example: Se=95%, Sp=99%, prevalence=0.1% -> PPV ~ 8.7%
- Mitigation: confirmatory testing algorithms, sequential testing, raising specificity

## ROC Curves and AUC

- Receiver Operating Characteristic curve plots Se (y-axis) vs 1-Sp (x-axis) across thresholds
- AUC summarizes overall discriminative ability (0.5 = coin flip, 1.0 = perfect)
- Useful for comparing tests or selecting optimal cut-off points
- Partial AUC can focus on clinically relevant specificity range

## Likelihood Ratios

- **LR+ = Se / (1 - Sp):** How much a positive result increases the odds of disease
- **LR- = (1 - Se) / Sp:** How much a negative result decreases the odds of disease
- Advantage: independent of prevalence; can be applied across settings using pre-test probability
- LR+ > 10 or LR- < 0.1 are considered strong evidence

## Agreement Measures

- **Cohen's kappa:** Agreement beyond chance between two raters or tests
- Interpretation: < 0.20 poor, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, > 0.80 almost perfect
- **Prevalence-adjusted bias-adjusted kappa (PABAK):** Corrects for prevalence and bias effects on kappa
- Useful when comparing two imperfect tests without a gold standard (latent class analysis is an alternative)

## Study Designs for Test Accuracy

- **Cross-sectional (single-gate):** Consecutive patients from target population receive both index test and reference standard; preferred design
- **Case-control (two-gate):** Separate recruitment of known diseased and non-diseased; inflates Se/Sp estimates; avoid if possible
- **Paired design:** All subjects receive all tests; allows direct comparison
- **Randomized design:** Subjects randomized to different tests; useful for comparing diagnostic strategies

## STARD Reporting Guidelines

- **STARD (Standards for Reporting of Diagnostic Accuracy Studies):** Checklist of 30 essential items
- Requires flow diagram showing participant enrollment, index test, reference standard, and final diagnoses
- Mandates reporting of indeterminate/missing results
- Updated in 2015 (STARD 2015)

## Current Developments (2025-2026)

- **AI-specific reporting now exists:** The **STARD-AI guideline was published on 15 September 2025** in *Nature Medicine*, extending diagnostic-accuracy reporting to studies using artificial intelligence.
- **Regulatory reporting expectations remain explicit:** FDA's guidance on reporting diagnostic test studies remains useful because it requires target-population clarity, subgroup reporting, confidence intervals, and transparent accounting for exclusions and indeterminate results.
- **Low-prevalence interpretation is becoming more important:** As elimination and post-elimination programmes expand, the practical challenge is often preserving acceptable PPV in real-world use rather than quoting sensitivity and specificity in isolation.

## Practical Examples

- **HAT screening algorithms:** In very low-prevalence HAT settings, PPV collapse makes confirmatory pathways essential even when rapid tests have high nominal specificity.
- **Diagnostic accuracy reviews:** QUADAS-2 and STARD remain the standard combination for critically reading diagnostic studies and then synthesizing them in reviews.
- **AI-based diagnostics:** STARD-AI signals that diagnostic evaluation now increasingly needs to report model development, validation, deployment context, and human-AI interaction, not just 2x2 table performance.

## Key References

- Bossuyt, P. M. et al. (2015). STARD 2015: An updated list of essential items for reporting diagnostic accuracy studies. *BMJ*, 351, h5527.
- Peeling, R. W. & Mabey, D. (2010). Point-of-care tests for diagnosing infections in the developing world. *Clin Microbiol Infect*, 16(8), 1062-1069.
- Deeks, J. J. & Altman, D. G. (2004). Diagnostic tests 4: likelihood ratios. *BMJ*, 329(7458), 168-169.
- Defined by the Cochrane Collaboration: *Handbook for Diagnostic Test Accuracy Reviews*. Available at methods.cochrane.org.
- Banoo, S. et al. (2010). Evaluation of diagnostic tests for infectious diseases: general principles. *Nature Reviews Microbiology*, 8, S17-S29.
- **STARD 2015 statement (open access):** https://pmc.ncbi.nlm.nih.gov/articles/PMC4623764/
- **STARD-AI guideline (15 September 2025):** https://www.nature.com/articles/s41591-025-03953-8
- **FDA guidance on reporting diagnostic test studies:** https://www.fda.gov/regulatory-information/search-fda-guidance-documents/statistical-guidance-reporting-results-studies-evaluating-diagnostic-tests-guidance-industry-and-fda
- **Cochrane DTA methods:** https://methods.cochrane.org/sdt/
- **EQUATOR STARD page:** https://www.equator-network.org/reporting-guidelines/stard/

## Learning Path

- Start with `06_library/courses/surveillance-methods/` and `06_library/courses/biostatistics/`.
- Pair this card with `06_library/methods/surveillance-systems.md` for case definitions, signal quality, and low-prevalence surveillance design.
- Pair it with `06_library/disease-areas/hat-sleeping-sickness.md` for a concrete elimination-phase use case.
- In the Learning Hub, this card aligns primarily with **Diagnostic evaluation** and also supports **Surveillance systems**.

---

*Last updated: 2026-03-29 | Enriched with STARD-AI and low-prevalence diagnostic evaluation context*
