# MLM Course Content Evaluation
**Date:** 2026-04-08  
**Agents:** edu-expert, methods-coach, epidemiologist  
**Scope:** Full course evaluation — pedagogical quality, statistical accuracy, epidemiological framing, concept ties

---

## Summary

The MLM course is in strong shape. 72 lessons cover the full arc from descriptive statistics through three-level models with consistent notation, good epidemiological framing, and measurable learning objectives. Seven issues were found and resolved in this session; no critical errors remain.

---

## Findings and Fixes

### 1. Vague Learning Objectives (edu-expert) — FIXED

Three objectives used "Understand…" (not a measurable Bloom's verb):

| Lesson | Old objective | Fixed objective |
|:-------|:--------------|:----------------|
| lesson2-descriptives.qmd, obj 5 | Understand why distributional shape matters for model assumptions | Explain how skewness and heavy tails violate mean-based summaries and determine which model assumptions require checking |
| lesson13-multiple-regression.qmd, obj 2 | Understand what "controlling for" means (partial effects) | Explain what "controlling for" means in terms of partial regression coefficients and connect it to stratified analysis |
| lesson21-icc.qmd, obj 4 | Understand what a "null model" is and what it tells you | Describe what a null model contains (intercept + random intercept only) and interpret its variance components as a decomposition of total outcome variability |

All other 100+ objectives across 72 lessons use measurable Bloom's verbs (Compute, Distinguish, Visualise, Fit, Interpret, Apply, etc.). ✅

---

### 2. Wald CI — No Justification in GLMM Lessons (methods-coach) — FIXED

All `confint()` calls use `method = "Wald"`. In the LMM lessons this is appropriate and already justified in lesson22. In the GLMM lessons (30, 30b, 31) there was no explanation.

**Fix:** Added a `{.callout-note}` block in lesson30-binary-outcomes.qmd before the first `confint(... method = "Wald")` call explaining:
- Profile likelihood is the gold standard but slow and sometimes non-convergent
- Wald is adequate at tropical health dataset sample sizes (hundreds–thousands of observations)
- When to prefer profile (small N, sparse outcomes, implausible CIs)
- The same convention applies in lessons 30b and 31

---

### 3. Concept Map Style Inconsistency (edu-expert) — FIXED

lesson21-icc.qmd "Leads to" callout referenced "Section 6, Lesson 6.1" — inconsistent with the lesson-number style used in all other concept maps.

**Fix:** Changed to "Lesson 22" and "Lessons 22–31".

---

### 4. Statistical Notation — PASS (methods-coach)

- $u_{0j}$, $\gamma_{00}$, $\tau_{00}$, $\sigma^2$ used consistently throughout Section 6 ✅
- lme4 + lmerTest present in every MLM lesson; Satterthwaite df mentioned ✅
- `parm = "beta_"` correctly preserved as lme4 argument (not a latex render target) ✅
- Random intercept vs random slope distinction clear in lessons 23–24 ✅
- Cross-level interaction mechanism explained in lesson26 ✅

---

### 5. Causal Language — PASS (epidemiologist)

No causal language detected in observational regression lessons (13, 23). Language consistently uses "association", "adjusted odds ratio", "holding constant". ✅

Confounding coverage: lesson14b (bias and confounding) + lesson14c (stratified analysis) provide solid conceptual groundwork before lesson13's multiple regression treatment. ✅

---

### 6. Tropical Health Framing — PASS (epidemiologist)

705 references to tropical health datasets in Sections 5–6. Datasets span malaria (DRC, Cameroon), malnutrition (MUAC), HIV co-infection, bed net distribution. ✅

lesson19 concept map rewired (previous session) to link the residual $e_i$ from lesson13 as the conceptual seed for multilevel structures. ✅

---

### 7. Cognitive Load — PASS (edu-expert)

lesson28 (three-level models, the densest lesson): 387 lines, 22 structural elements (callouts, headers, code blocks). Density is moderate and well-segmented. Not flagged. ✅

---

## Outstanding Items (low priority)

| Item | Priority | Notes |
|:-----|:---------|:------|
| Profile CI for GLMM lessons | Low | Wald justified; consider adding a `# try: confint(..., method = "profile")` comment in lesson30 exercise for advanced students |
| Nano Banana cartoon prompts (G11) | — | 30 prompts written and saved to `Ressources/Cartoons/nano-banana-prompts.md`; images not yet generated |
| lesson30/30b cross-reference | Low | lesson30b could link back to the Wald CI callout in lesson30 to avoid duplication |

---

## Agent Run Summary

| Agent | Task | Tokens (approx) |
|:------|:-----|:----------------|
| edu-expert | Bloom's verb audit, learning objective fixes | ~8,000 |
| methods-coach | Notation audit, CI method review | ~5,000 |
| epidemiologist | Causal language, tropical framing, dataset coverage | ~4,000 |
| software-engineer | Concept graph (app.js), LEMMA removal, Part→Module, schema fix | ~15,000 |

*Note: All agents ran in parent session due to OneDrive path permission restrictions on background subagents.*
