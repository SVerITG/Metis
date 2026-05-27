# Domain-expert review notes — HAT Surveillance Methods (DRC)
Reviewer: Epidemiologist (subject-matter review, delegated by Course Builder)
Date: 2026-05-26
Scope reviewed in depth: Lesson 4 (test performance) and Lesson 8 (elimination endgame); spot-checked Lessons 1-3, 5-7.

## Verdict
**Pass, with two framing caveats addressed in the drafts.** The methodology is sound for a field-epidemiologist audience. The course correctly centres the two ideas that matter most in the gHAT endgame: the prevalence-dependence of predictive value, and the distinction between "low cases from genuine decline" versus "low cases from detection failure."

## Lesson 4 — test performance (Analyze)
- Sensitivity/specificity vs. predictive value distinction is correct and clearly separated.
- The PPV worked example is arithmetically correct: at sens 95% / spec 95%, PPV ≈ 28% at 2% prevalence and ≈ 0.9% at 0.05% prevalence. I re-derived both; they hold. This is the load-bearing quantitative point of the course and it is right.
- The screen-then-confirm (sensitive → specific) rationale is correctly stated. Good that it explicitly warns low-parasitaemia true positives can slip through confirmation.
- Caveat addressed: the illustrative 95/95 figures are labelled as illustrative, not quoted as the real CATT/RDT operating characteristics. Real-world values should be read from Buscher et al. — the lesson points the learner there. Acceptable.

## Lesson 8 — elimination endgame (Evaluate)
- EPHP vs. EOT framing is consistent with WHO definitions and appropriately hedged ("broadly", "around 2030"). Good that exact ceiling numbers are not over-stated.
- Cryptic transmission / animal reservoir is correctly flagged as **contested**, not settled — this is the right scientific posture and satisfies the controversial-topic guardrail.
- The dossier-evaluation example correctly distinguishes credible from non-credible low-incidence claims on the basis of maintained coverage and data quality. This is exactly the judgement a field epidemiologist must make.

## Cross-cutting checks
- Coverage/yield (L3) and incidence-per-10k (L7) are defined consistently and reused coherently into L8. Denominators are handled correctly.
- DRC-grounded examples are concrete (named provinces, plausible health-zone scenarios) and not misleading; no real patient data used.
- R code (L7) is tidyverse-only, uses the `sf` package's bundled `nc.shp` so it runs on a clean install, and labels its geometry as illustrative. Compliant with the R style rule.

## Minor suggestions (non-blocking, for a future revision)
- L4 could add one real published sensitivity/specificity range inline (from Buscher) to anchor the illustrative numbers.
- L6 FTD reduction percentages are described as "often 80-90%" — keep this as a range, not a point estimate, which the draft does.
- Consider a short glossary file if the Learning tab does not auto-extract first-use definitions.
