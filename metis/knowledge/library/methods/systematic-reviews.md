---
title: "Systematic Reviews and Meta-Analysis"
domain: "methods"
tags:
  - systematic-review
  - meta-analysis
  - evidence-synthesis
  - PRISMA
  - Cochrane
related:
  - "methods/study-designs.md"
  - "methods/biostatistics-essentials.md"
  - "methods/data-management.md"
phd_relevance: "medium"
status: "current"
updated: "2026-03-29"
---
# Systematic Reviews and Meta-Analysis

> Reference card — PRISMA, GRADE, meta-analysis methods, risk of bias, protocol registration.

---

## PRISMA 2020 Guidelines

### Overview
- **Full name:** Preferred Reporting Items for Systematic Reviews and Meta-Analyses
- **PRISMA 2020:** Updated from 2009; 27-item checklist + flow diagram
- **Purpose:** Transparent, complete reporting of systematic reviews
- **Extensions:** PRISMA-S (search reporting), PRISMA-ScR (scoping reviews), PRISMA-P (protocols), PRISMA-NMA (network meta-analysis), PRISMA-DTA (diagnostic test accuracy), PRISMA-IPD (individual participant data)

### Key Sections
1. **Title:** Identify as systematic review, meta-analysis, or both
2. **Registration/protocol:** PROSPERO ID, published protocol
3. **Eligibility criteria:** PICO/PECO framework
4. **Information sources:** Databases, registers, other sources
5. **Search strategy:** Full strategy for at least one database (reproducible)
6. **Selection process:** Screening, deduplication, independent reviewers
7. **Data collection:** Extraction process, variables, assumptions
8. **Risk of bias assessment:** Tool used, process, results
9. **Synthesis:** Methods for combining results, heterogeneity assessment
10. **Certainty of evidence:** GRADE or equivalent

### Flow Diagram (2020 update)
- Identification: databases, registers, other sources
- Screening: title/abstract, then full text (with reasons for exclusion)
- Included: studies in qualitative synthesis, studies in quantitative synthesis (meta-analysis)

---

## GRADE Framework

### Purpose
- Assess **certainty of evidence** (not quality of individual studies)
- Rate evidence as High, Moderate, Low, Very Low

### Starting Point
- RCTs start at High
- Observational studies start at Low

### Downgrading Factors (5)

| Factor | Description |
|--------|-------------|
| **Risk of bias** | Limitations in study design/execution |
| **Inconsistency** | Unexplained heterogeneity across studies |
| **Indirectness** | Differences in population, intervention, outcome, or comparator from question |
| **Imprecision** | Wide confidence intervals; small sample size |
| **Publication bias** | Selective reporting; funnel plot asymmetry |

### Upgrading Factors (3, for observational studies)

| Factor | Description |
|--------|-------------|
| **Large effect** | RR >2 or <0.5 with no plausible confounding |
| **Dose-response** | Clear gradient |
| **Confounding** | All plausible confounders would reduce effect |

### Interpretation

| Rating | Meaning |
|--------|---------|
| **High** | Very confident the true effect lies close to estimate |
| **Moderate** | Moderately confident; true effect likely close but may be substantially different |
| **Low** | Limited confidence; true effect may be substantially different |
| **Very Low** | Very little confidence; true effect likely substantially different |

---

## Meta-Analysis Methods

### Fixed-Effect Model
- **Assumption:** Single true effect size underlying all studies
- **Method:** Inverse-variance weighted average (Mantel-Haenszel for binary)
- **When to use:** Studies homogeneous; same population/intervention

### Random-Effects Model
- **Assumption:** True effect sizes vary across studies (heterogeneity)
- **Method:** DerSimonian-Laird (classic); REML (recommended); Hartung-Knapp-Sidik-Jonkman (HKSJ) for CIs
- **When to use:** Expected heterogeneity (most real-world scenarios); gives wider CIs

### Heterogeneity Assessment
- **Cochran's Q test:** Tests whether heterogeneity exists (low power with few studies)
- **I-squared:** Proportion of variability due to heterogeneity (not chance); 25%/50%/75% = low/moderate/high
- **Tau-squared:** Estimate of between-study variance
- **Prediction interval:** Range within which effect of a future study would likely fall

### Subgroup and Meta-Regression
- **Subgroup analysis:** Stratify by pre-specified characteristics; test for interaction
- **Meta-regression:** Model effect size as function of study-level covariates
- **Caution:** Ecological fallacy; low power; should be pre-specified

### Publication Bias Assessment
- **Funnel plot:** Scatter of effect size vs precision; asymmetry suggests bias
- **Egger's test:** Statistical test for funnel plot asymmetry
- **Trim-and-fill:** Imputes "missing" studies; adjusted estimate
- **P-curve / P-uniform:** Assess evidential value of significant results
- **Selection models:** Vevea-Hedges, Copas model

### Network Meta-Analysis (NMA)
- **Purpose:** Compare multiple treatments simultaneously using direct + indirect evidence
- **Assumption:** Transitivity (indirect comparisons valid)
- **Output:** Treatment rankings (SUCRA, P-score), league table
- **Software:** `netmeta`, `gemtc` (R); CINeMA for certainty

---

## Risk of Bias Tools

| Tool | Study Type | Domains |
|------|-----------|---------|
| **Cochrane RoB 2** | Randomized trials | Randomization, deviations, missing data, measurement, selection of results |
| **ROBINS-I** | Non-randomized studies of interventions | Confounding, selection, classification, deviations, missing data, measurement, reporting |
| **Newcastle-Ottawa Scale** | Cohort and case-control | Selection, comparability, outcome/exposure (star system) |
| **QUADAS-2** | Diagnostic accuracy | Patient selection, index test, reference standard, flow and timing |
| **JBI Critical Appraisal** | Various (prevalence, qualitative, etc.) | Design-specific checklists |
| **AXIS** | Cross-sectional | 20-item quality assessment |

### RoB 2 Signal Questions
- Each domain assessed as Low risk / Some concerns / High risk
- Overall: worst domain drives overall judgement (unless compensated)
- Always assess per outcome, per analysis

---

## Protocol Registration

### PROSPERO
- **What:** International database of prospectively registered systematic review protocols
- **Who:** CRD, University of York
- **When to register:** Before screening begins (ideally before search)
- **What to include:** PICO, search strategy, data extraction plan, analysis plan
- **URL:** crd.york.ac.uk/prospero

### Other Registration Options
- **OSF Registries:** Open Science Framework; more flexible
- **Protocol publication:** BMJ Open, Systematic Reviews journal, PLOS ONE
- **Cochrane protocols:** For Cochrane reviews

---

## Software for Systematic Reviews

| Tool | Purpose |
|------|---------|
| **Covidence** | Screening, data extraction, RoB (commercial; Cochrane-recommended) |
| **Rayyan** | Free screening tool (web-based; AI-assisted) |
| **EPPI-Reviewer** | Comprehensive SR management |
| **RevMan** | Cochrane's review management and meta-analysis |
| **R: meta, metafor** | Meta-analysis (metafor is most comprehensive) |
| **R: robvis** | Visualization of risk of bias assessments |
| **R: dmetar** | Companion to Harrer et al. textbook |
| **GRADE profiler (GRADEpro)** | Summary of findings tables, GRADE assessment |
| **ASReview** | Active learning for screening (AI-assisted prioritization) |

---

## Current Developments (2025-2026)

- **Cochrane Handbook current version:** Cochrane lists **version 6.5 (2024)** as the current handbook version in 2025-2026, so this remains the main live methods reference rather than an older static edition.
- **PROSPERO scale keeps growing:** The University of York reported on **6 January 2025** that PROSPERO had passed **300,000 published registrations**, with a new version planned to improve automation and duplication checks.
- **AI-assisted screening is now mainstream enough to require explicit reporting:** Tools such as ASReview are increasingly part of normal workflow discussion, but their effect on prioritization and inclusion should still be reported transparently.

## Practical Examples

- **Protocol registration as waste prevention:** PROSPERO's scale in 2025 is itself evidence that duplication and overlapping reviews are now major practical concerns.
- **Reporting transparency:** PRISMA 2020 remains the backbone for making review methods inspectable, especially when searches, exclusions, and synthesis choices become complex.
- **Certainty assessment:** GRADE remains essential because meta-analysis without certainty assessment often overstates what the evidence can support.

## Key References

- **Page MJ et al.** The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. *BMJ.* 2021;372:n71.
- **Higgins JPT et al. (eds).** *Cochrane Handbook for Systematic Reviews of Interventions.* Version 6.4. Cochrane, 2023.
- **Harrer M et al.** *Doing Meta-Analysis with R: A Hands-On Guide.* CRC Press, 2021. [Free online: bookdown.org/MathiasHarrer/Doing_Meta_Analysis_in_R]
- **Borenstein M et al.** *Introduction to Meta-Analysis.* 2nd ed. Wiley, 2021.
- **Guyatt GH et al.** GRADE: an emerging consensus on rating quality of evidence and strength of recommendations. *BMJ.* 2008;336:924-926.
- **Sterne JAC et al.** RoB 2: a revised tool for assessing risk of bias in randomised trials. *BMJ.* 2019;366:l4898.
- **PRISMA 2020 statement:** https://www.prisma-statement.org/prisma-2020-statement
- **Cochrane Handbook current version:** https://training.cochrane.org/handbook/current
- **Cochrane handbook landing page:** https://www.cochrane.org/authors/handbooks-and-manuals/handbook
- **PROSPERO 2025 update from York:** https://www.york.ac.uk/crd/about/news/2025/prospero2025/
- **PROSPERO register:** https://www.crd.york.ac.uk/prospero/
- **GRADE working group:** https://www.gradeworkinggroup.org/
- **GRADEpro:** https://www.gradepro.org/

## Learning Path

- Start with `06_library/courses/research-writing/`, especially the literature review, protocol, reporting-guideline, and PRISMA lessons.
- Pair this card with `06_library/methods/writing-for-journals.md` for manuscript preparation and with `06_library/methods/diagnostic-test-evaluation.md` when reading diagnostic test reviews.
- Use it alongside `06_library/methods/study-designs.md` when deciding whether review inclusion criteria are clinically and epidemiologically coherent.
- In the Learning Hub, this card aligns primarily with **Scientific communication** and secondarily with **Epidemiological methods**.

---

*Last updated: 2026-03-29 | Enriched with PROSPERO 2025 and current Cochrane guidance*
