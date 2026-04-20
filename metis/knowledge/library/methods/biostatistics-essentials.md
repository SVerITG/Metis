# Biostatistics Essentials

> Reference card — measures of association, regression models, confounding, power, corrections.

---

## Measures of Association

| Measure | Definition | Study Design | Interpretation |
|---------|-----------|--------------|----------------|
| **Risk Ratio (RR)** | Incidence in exposed / incidence in unexposed | Cohort, RCT | RR=2: exposed have 2x the risk |
| **Odds Ratio (OR)** | Odds of exposure in cases / odds in controls | Case-control (any) | Approximates RR when outcome rare (<10%) |
| **Hazard Ratio (HR)** | Instantaneous rate ratio from survival model | Cohort, RCT with time-to-event | HR=1.5: 50% higher instantaneous rate |
| **Rate Ratio (IRR)** | Incidence rate in exposed / rate in unexposed | Cohort, Poisson regression | Accounts for person-time |
| **Risk Difference (RD)** | Incidence_exposed - Incidence_unexposed | Cohort, RCT | Absolute measure; used for NNT = 1/RD |
| **Prevalence Ratio** | Prevalence_exposed / Prevalence_unexposed | Cross-sectional | Not the same as RR (mixes incidence + duration) |

### Attributable Measures
- **Attributable Risk (AR):** RD = risk_exposed - risk_unexposed
- **Attributable Fraction (AF):** (RR - 1) / RR among exposed
- **Population Attributable Fraction (PAF):** Proportion of disease in population attributable to exposure
- **NNT (Number Needed to Treat):** 1 / absolute risk reduction

---

## Regression Models

### Logistic Regression
- **Outcome:** Binary (0/1)
- **Link:** Logit: log(odds) = B0 + B1*X
- **Output:** Odds ratios (exponentiated coefficients)
- **Assumptions:** Linearity in log-odds; no multicollinearity; independence of observations
- **Variants:** Conditional (matched data), ordinal (ordered outcome), multinomial (>2 categories)

### Poisson Regression
- **Outcome:** Count data (with offset for person-time or population)
- **Link:** Log: log(rate) = B0 + B1*X + offset(log(person-time))
- **Output:** Incidence rate ratios (IRR)
- **Assumption:** Mean = variance (equidispersion)
- **Problem:** Overdispersion is common in practice

### Negative Binomial Regression
- **Outcome:** Count data with overdispersion (variance > mean)
- **Use:** When Poisson assumption of equidispersion is violated
- **Extra parameter:** Dispersion parameter allows variance to exceed mean

### Cox Proportional Hazards
- **Outcome:** Time-to-event (survival data)
- **Model:** h(t) = h0(t) * exp(B1*X)
- **Output:** Hazard ratios
- **Assumption:** Proportional hazards (constant HR over time); check with Schoenfeld residuals
- **Strengths:** Semi-parametric (no assumption about baseline hazard shape)

### Multilevel / Mixed Models
- **Use:** Hierarchical/clustered data (patients in hospitals, repeated measures, spatial nesting)
- **Components:** Fixed effects + random effects (intercepts and/or slopes)
- **Types:** Random intercept, random slope, cross-classified, crossed random effects
- **Software:** `lme4`, `nlme`, `glmmTMB` (R); `xtmixed` (Stata)

### Zero-Inflated Models
- **Use:** Excess zeros beyond what Poisson/NB predicts
- **Types:** Zero-inflated Poisson (ZIP), zero-inflated negative binomial (ZINB)
- **Software:** `pscl`, `glmmTMB` (R)

---

## Confounding and Effect Modification

### Confounding
- **Definition:** A third variable that is associated with both exposure and outcome, is not on the causal pathway
- **Control methods:**
  - Design: Randomization, restriction, matching
  - Analysis: Stratification, multivariable regression, propensity scores, IPTW
- **Assessment:** >10% change-in-estimate criterion (traditional); DAG-based (modern)

### Effect Modification (Interaction)
- **Definition:** The effect of exposure on outcome differs across levels of a third variable
- **Assessment:** Stratified analysis (different stratum-specific estimates); interaction terms in regression
- **Additive vs multiplicative:** Additive interaction (RERI, AP, SI) more relevant for public health; multiplicative is default in logistic regression

### Directed Acyclic Graphs (DAGs)
- **Purpose:** Encode causal assumptions; identify confounders, mediators, colliders
- **Rules:** Condition on confounders; do NOT condition on colliders or mediators
- **Backdoor criterion:** Block all backdoor paths from exposure to outcome
- **Software:** DAGitty (web + R package `dagitty`), `ggdag` (R)

---

## Sample Size and Power

### Key Parameters
- **Alpha (type I error):** Usually 0.05
- **Power (1 - beta):** Usually 0.80 or 0.90
- **Effect size:** Clinically meaningful difference to detect
- **Variability:** Standard deviation or baseline rate

### Common Formulas
- **Two proportions:** n = (Z_alpha/2 + Z_beta)^2 * [p1(1-p1) + p2(1-p2)] / (p1 - p2)^2
- **Two means:** n = (Z_alpha/2 + Z_beta)^2 * 2*sigma^2 / delta^2
- **Cluster trials:** n_cluster = n_individual * [1 + (m-1)*ICC] (design effect)

### Software
- R: `pwr`, `samplesize`, `clusterPower`
- Standalone: G*Power, PASS, OpenEpi

---

## Multiple Testing Corrections

| Method | Approach | When to Use |
|--------|----------|-------------|
| **Bonferroni** | alpha / number of tests | Conservative; few independent tests |
| **Holm (step-down)** | Sequential Bonferroni; less conservative | Default improved Bonferroni |
| **Benjamini-Hochberg (FDR)** | Controls false discovery rate | Genomics, multiple outcomes, exploratory |
| **Simes** | Global test for any significant result | Testing family of hypotheses jointly |
| **No correction** | Pre-specified primary outcome | Single primary analysis in RCT |

---

## Model Selection and Diagnostics

- **AIC/BIC:** Compare non-nested models; lower is better
- **Likelihood ratio test:** Compare nested models
- **Hosmer-Lemeshow test:** Goodness of fit for logistic regression
- **Residual diagnostics:** Deviance residuals, Pearson residuals, Cook's distance
- **VIF:** Variance inflation factor for multicollinearity (VIF > 5-10 = concern)
- **Overdispersion:** Deviance/df >> 1 in Poisson model suggests negative binomial

---

## Current Developments (2025-2026)

- **Biostatistical guidance is shifting toward method maturity, not just novelty:** The STRATOS initiative's 2025 ISCB mini-symposium focused on how methods mature through development, evaluation, and guidance phases, which is a useful corrective to "latest method wins" thinking.
- **Reporting quality remains a live concern:** STROBE continues to be the baseline reporting framework for observational epidemiology, and common weaknesses still concern model choice, missing data handling, non-linearity, and overinterpretation.
- **Open learning resources remain strong:** OpenIntro Statistics and similar free resources continue to lower access barriers for learners building core statistical fluency from beginner level.
- **Practical implication:** In 2026, the strongest default is still careful descriptive work, explicit estimands, transparent diagnostics, and conservative interpretation rather than premature complexity.

---

## Practical Examples

- **Framingham-style time-to-event modeling:** Cox proportional hazards models remain a standard example for studying cardiovascular risk factors over time and interpreting hazard ratios.
- **NTD incidence modeling:** Poisson or negative binomial regression is routinely used when comparing incidence rates across districts or intervention periods with person-time denominators.
- **Matched outbreak analyses:** Logistic regression and stratified odds ratios remain standard when analytic studies are nested inside outbreak investigations or case-control surveillance studies.
- **Hierarchical health-systems data:** Multilevel models are increasingly necessary when observations are nested within facilities, districts, or repeated follow-up visits and independence assumptions fail.

---

## Key References

- **Hosmer DW, Lemeshow S, Sturdivant RX.** *Applied Logistic Regression.* 3rd ed. Wiley, 2013.
- **Gelman A, Hill J.** *Data Analysis Using Regression and Multilevel/Hierarchical Models.* Cambridge, 2007.
- **Kirkwood BR, Sterne JAC.** *Essential Medical Statistics.* 2nd ed. Blackwell, 2003.
- **Vittinghoff E et al.** *Regression Methods in Biostatistics.* 2nd ed. Springer, 2012.
- **Collett D.** *Modelling Survival Data in Medical Research.* 3rd ed. CRC Press, 2015.
- **Greenland S, Rothman KJ.** Introduction to stratified analysis. In: *Modern Epidemiology.* 3rd ed. 2008.
- **STROBE statement and checklists:** https://www.strobe-statement.org/
- **STRATOS initiative:** https://www.stratos-initiative.org/
- **STRATOS ISCB 2025 mini-symposium:** https://stratos-initiative.org/sites/default/files/2025-06/ISCB2025-prog-off.pdf
- **OpenIntro Statistics:** https://www.openintro.org/book/os/

---

## Learning Path

- Start with `06_library/courses/biostatistics/`.
- Pair this card with `06_library/methods/study-designs.md` because measures of association and regression choices only make sense in relation to study design.
- Use `06_library/methods/causal-inference.md` when deciding what to adjust for and how to interpret model coefficients causally.
- In the Learning Hub, this card aligns primarily with **Biostatistics** and secondarily with **Epidemiological methods** and **Data management & R**.

---

*Last updated: 2026-03-30 | Enriched with current statistical guidance and learning links*
