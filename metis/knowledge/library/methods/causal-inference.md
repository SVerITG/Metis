---
title: "Causal Inference"
domain: "methods"
tags:
  - causal-inference
  - DAGs
  - counterfactual
  - confounding
  - IV
  - RDD
related:
  - "methods/study-designs.md"
  - "methods/biostatistics-essentials.md"
phd_relevance: "high"
status: "current"
updated: "2026-03-29"
---
# Causal Inference

> Reference card — causal frameworks, DAGs, quasi-experimental methods, key tools.

---

## Philosophical Foundations

### Counterfactual (Potential Outcomes) Framework
- **Origin:** Neyman (1923), Rubin (1974)
- **Core idea:** Causal effect = Y(1) - Y(0) for individual i; we only observe one potential outcome
- **Fundamental problem:** Cannot observe both potential outcomes for the same unit
- **Solution:** Average causal effects estimated from groups under assumptions (exchangeability, positivity, consistency, SUTVA)

### Structural Causal Models (Pearl)
- **Approach:** Graphical models (DAGs) + do-calculus to formalize interventions
- **do-operator:** P(Y | do(X)) differs from P(Y | X) — intervention vs observation
- **Advantage:** Makes assumptions explicit and testable via graph structure

---

## Bradford Hill Criteria (1965)

Criteria for assessing causation from observational evidence (not a checklist — a framework for judgement):

| Criterion | Description |
|-----------|-------------|
| **Strength** | Large magnitude of association |
| **Consistency** | Replicated across studies, populations, settings |
| **Specificity** | Specific exposure leads to specific outcome |
| **Temporality** | Exposure precedes outcome (the only necessary criterion) |
| **Biological gradient** | Dose-response relationship |
| **Plausibility** | Biologically plausible mechanism |
| **Coherence** | Consistent with existing knowledge |
| **Experiment** | Experimental evidence supports causation |
| **Analogy** | Similar exposures cause similar outcomes |

---

## Directed Acyclic Graphs (DAGs)

### Key Concepts
- **Node:** Variable (exposure, outcome, confounder, mediator, collider)
- **Arrow:** Direct causal effect (direction matters)
- **Path:** Sequence of edges connecting two nodes (causal or non-causal)
- **Confounder:** Common cause of exposure and outcome — condition on it to block backdoor path
- **Mediator:** On the causal pathway — do NOT condition on it (unless mediation analysis)
- **Collider:** Common effect of two variables — do NOT condition on it (opens spurious path)

### Rules for Variable Selection
1. Identify all backdoor paths from exposure to outcome
2. Find a minimal sufficient adjustment set that blocks all backdoor paths
3. Never condition on descendants of the outcome
4. Never condition on colliders (or their descendants) unless necessary and accounted for
5. Use DAGitty or `dagitty` R package to identify valid adjustment sets algorithmically

### Common Pitfalls
- **Collider bias (selection bias):** Conditioning on a collider creates spurious association
- **M-bias:** Complex collider structures that look like confounders but aren't
- **Over-adjustment:** Conditioning on mediators or descendants of exposure

### Software
- **DAGitty:** Web tool (dagitty.net) + R package `dagitty`
- **ggdag:** R package for plotting and analyzing DAGs

---

## Quasi-Experimental Methods

### Propensity Score Methods
- **Propensity score:** P(treatment | covariates) — probability of receiving treatment given observed covariates
- **Methods:**
  - Matching (1:1, 1:k, caliper)
  - Stratification/subclassification
  - Inverse probability of treatment weighting (IPTW)
  - Covariate adjustment (regression with PS)
- **Assumption:** No unmeasured confounding (strong and untestable)
- **Diagnostics:** Balance tables, standardized mean differences (SMD < 0.1)
- **R packages:** `MatchIt`, `twang`, `WeightIt`, `cobalt` (balance)

### Instrumental Variables (IV)
- **Concept:** Find a variable (instrument) that affects outcome ONLY through exposure
- **Requirements:** (1) Relevance — instrument predicts exposure; (2) Exclusion restriction — instrument affects outcome only via exposure; (3) Independence — instrument independent of confounders
- **Examples:** Mendelian randomization (genetic variants), distance to facility, policy changes
- **Methods:** Two-stage least squares (2SLS), LIML
- **Limitation:** Estimates Local Average Treatment Effect (LATE) for compliers only
- **R packages:** `ivreg`, `AER`

### Difference-in-Differences (DiD)
- **Design:** Compare change over time in treatment group vs control group
- **Key assumption:** Parallel trends — in absence of treatment, both groups would have followed same trajectory
- **Assessment:** Plot pre-treatment trends; test for divergence before treatment
- **Extensions:** Staggered treatment timing (Callaway-Sant'Anna, Sun-Abraham); event studies
- **R packages:** `did`, `fixest`, `bacondecomp`

### Regression Discontinuity (RD)
- **Design:** Treatment assigned by threshold on a continuous running variable (e.g., age cutoff, score cutoff)
- **Types:** Sharp (deterministic at cutoff) vs fuzzy (probability changes at cutoff)
- **Key assumption:** No manipulation of running variable around cutoff
- **Diagnostics:** McCrary density test, balance of covariates at cutoff
- **R packages:** `rdrobust`, `rdd`

### Interrupted Time Series (ITS)
- **Design:** Multiple observations before and after intervention; assess change in level and trend
- **Requirements:** Sufficient pre-intervention time points (usually 8+); clear intervention date
- **Model:** Segmented regression with level change and slope change parameters
- **Threats:** History (concurrent events), autocorrelation
- **R packages:** `its.analysis`, basic `lm` with appropriate terms

### Synthetic Control Method
- **Design:** Construct a weighted combination of control units to create a "synthetic" version of the treated unit
- **When to use:** Single treated unit (country, region) with multiple control units
- **R packages:** `Synth`, `gsynth`

---

## Mediation Analysis

- **Total effect = Direct effect + Indirect effect (through mediator)**
- **Traditional:** Baron & Kenny steps (outdated but widely known)
- **Modern:** Counterfactual-based mediation (VanderWeele); natural direct and indirect effects
- **Sensitivity:** E-value for unmeasured confounding of mediator-outcome
- **R packages:** `mediation`, `medflex`, `CMAverse`

---

## Sensitivity Analysis for Unmeasured Confounding

- **E-value:** Minimum strength of association that an unmeasured confounder would need (with both exposure and outcome) to explain away the observed result (VanderWeele & Ding, 2017)
- **Rosenbaum bounds:** For matched studies; how much hidden bias would alter conclusions
- **Quantitative bias analysis:** Probabilistic bias analysis, Monte Carlo sensitivity analysis
- **R packages:** `EValue`, `sensemakr`, `episensr`

---

## Current Developments (2025-2026)

- **Target trial emulation is being formalized:** The **TARGET statement was published on 3 September 2025 in BMJ**, giving a dedicated reporting guideline for observational studies explicitly emulating a target trial.
- **Journal uptake is increasing:** **PLOS Medicine announced on 31 October 2025** that target-trial emulation submissions should follow the TARGET statement.
- **The field is still accelerating:** JAMA Network Open published a new overview on **19 February 2026** describing target trial emulation as a unifying approach for causal inference from observational data.
- **Estimands are spreading beyond classic trials:** The BMJ primer on the **ICH E9(R1) estimands framework** remains important because it pushes analysts to define the exact causal question before selecting a model.

## Practical Examples

- **Target trial emulation for intervention questions:** Explicitly specifying eligibility, time zero, treatment strategies, follow-up, and estimand helps avoid immortal-time and selection biases.
- **DAG-guided adjustment:** DAGs remain one of the most practical tools for deciding what to adjust for and what to leave alone in complex epidemiologic settings.
- **Sensitivity analysis as interpretation support:** E-values and related approaches are most useful when presented as complements to design quality rather than as substitutes for it.

## Key References

- **Hernan MA, Robins JM.** *Causal Inference: What If.* Chapman & Hall/CRC, 2020. [Free online]
- **Pearl J.** *Causality: Models, Reasoning, and Inference.* 2nd ed. Cambridge, 2009.
- **Pearl J, Glymour M, Jewell NP.** *Causal Inference in Statistics: A Primer.* Wiley, 2016.
- **Angrist JD, Pischke JS.** *Mostly Harmless Econometrics.* Princeton, 2009.
- **VanderWeele TJ.** *Explanation in Causal Inference.* Oxford, 2015.
- **Hill AB.** The environment and disease: association or causation? *Proceedings of the Royal Society of Medicine.* 1965;58:295-300.
- **VanderWeele TJ, Ding P.** Sensitivity analysis in observational research: introducing the E-value. *Annals of Internal Medicine.* 2017;167(4):268-274.
- **What If book (free online):** https://miguelhernan.org/whatifbook
- **TARGET statement (BMJ, 3 September 2025):** https://www.bmj.com/content/390/bmj-2025-087179
- **PLOS Medicine endorsement of TARGET (31 October 2025):** https://journals.plos.org/plosmedicine/article?id=10.1371%2Fjournal.pmed.1004796
- **JAMA Network Open target trial overview (19 February 2026):** https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2845271
- **BMJ estimands primer (23 January 2024):** https://www.bmj.com/content/384/bmj-2023-076316
- **DAGitty:** https://dagitty.net/

## Learning Path

- Start with `knowledge/library/courses/epidemiology-foundations/`, then `knowledge/library/courses/biostatistics/`.
- Pair this card with `knowledge/library/methods/study-designs.md` for design logic and `knowledge/library/methods/biostatistics-essentials.md` for estimation tools.
- Use it alongside `knowledge/library/courses/research-writing/` when drafting study protocols and analytic plans.
- In the Learning Hub, this card aligns primarily with **Epidemiological methods** and secondarily with **Biostatistics**.

---

*Last updated: 2026-03-29 | Enriched with TARGET and target-trial developments*
