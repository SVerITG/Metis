# Lesson 4 — Case Definitions, Diagnostic Algorithms, and Test Performance

## Learning objectives
By the end of this lesson you will be able to:
- **Analyse** the sensitivity and specificity of the gHAT diagnostic pathway and explain why screening and confirmation play different roles.
- **Calculate** positive predictive value (PPV) and demonstrate how it collapses as prevalence falls.
- **Justify** why a multi-step algorithm is necessary in an elimination setting rather than a single test.

## Prerequisites
- Lessons 2 and 3 (the screen-confirm staircase in passive and active settings).
- The 2×2 table idea (test result vs. true disease status).

## Content

### Section 1: The four cells and two test properties
Every diagnostic test sorts people into a 2×2 table against their true status:

|                | Disease +        | Disease −        |
|----------------|------------------|------------------|
| **Test +**     | True positive (TP) | False positive (FP) |
| **Test −**     | False negative (FN) | True negative (TN) |

- **Sensitivity** = TP / (TP + FN) — of those truly infected, the fraction the test catches.
- **Specificity** = TN / (TN + FP) — of those truly uninfected, the fraction the test correctly clears.

Sensitivity and specificity are (approximately) **properties of the test**, stable across settings. They do **not** by themselves tell you what a positive result means for a given patient — that is what predictive values do.

### Section 2: Why gHAT needs a staircase, not one test
gHAT screening tests (CATT, individual RDTs) are deliberately tuned to be **highly sensitive** so few infections are missed — but their specificity is imperfect, so they produce false positives. If you treated everyone who screened positive, you would treat uninfected people. So the algorithm follows the sensitive screen with a **highly specific** confirmatory step (seeing the parasite), which has near-100% specificity but lower sensitivity (parasites can be scarce and missed). 

Chaining a sensitive test then a specific test is the classic way to get acceptable overall performance from two imperfect tests: the screen catches nearly everyone infected; the confirmation removes the false positives before anyone is treated. The price is that a few true infections with very low parasitaemia slip through confirmation — which is one reason serological suspects are sometimes followed rather than discharged.

### Section 3: Predictive value and the prevalence trap
**Positive predictive value (PPV)** = TP / (TP + FP) — of those who test positive, the fraction truly infected. Unlike sensitivity/specificity, PPV **depends heavily on prevalence**. As gHAT prevalence falls toward elimination, even a very good test produces mostly false positives on screening.

> **Worked example — DRC elimination setting.**
> Suppose a screening test has sensitivity 95% and specificity 95%. Screen 10,000 people.
>
> **Scenario A — historical high prevalence, 2% (200 infected):**
> - TP = 0.95 × 200 = 190; FN = 10
> - FP = 0.05 × 9,800 = 490; TN = 9,310
> - PPV = 190 / (190 + 490) = **28%**
>
> **Scenario B — near elimination, 0.05% (5 infected per 10,000):**
> - TP = 0.95 × 5 ≈ 4.75; FN ≈ 0.25
> - FP = 0.05 × 9,995 ≈ 499.75; TN ≈ 9,495
> - PPV = 4.75 / (4.75 + 499.75) ≈ **0.9%**
>
> Same test, same sensitivity and specificity — but at elimination-level prevalence, **fewer than 1 in 100 screen-positives is truly infected.** This is the single most important quantitative idea in elimination-phase surveillance: it is precisely why you must confirm parasitologically and never treat on a screen alone, and why over-screening a near-clean population floods the system with false positives.

### Section 4: Quick R check (tidyverse)
```r
library(tidyverse)

ppv <- function(sens, spec, prev) {
  tp <- sens * prev
  fp <- (1 - spec) * (1 - prev)
  tp / (tp + fp)
}

scenarios <- tibble(
  setting = c("historical 2%", "near elimination 0.05%"),
  prev    = c(0.02, 0.0005)
) |>
  mutate(ppv = ppv(sens = 0.95, spec = 0.95, prev = prev))

scenarios
#> # A tibble: 2 x 3
#>   setting                   prev    ppv
#>   <chr>                    <dbl>  <dbl>
#> 1 historical 2%            0.02  0.279
#> 2 near elimination 0.05%   0.0005 0.00942
```

The PPV column makes the prevalence trap unmissable: 28% versus under 1%.

### Section 5: What this means for treatment decisions
The treatment landscape is changing. **Fexinidazole**, an oral drug, simplifies management for eligible confirmed patients and reduces the need for systematic lumbar-puncture staging. But it does **not** change the logic above: eligibility still rests on a *confirmed* diagnosis. A more convenient drug raises, not lowers, the cost of acting on false positives at scale.

## Summary
- Sensitivity and specificity are test properties; predictive values depend on the population's prevalence.
- gHAT uses a sensitive screen followed by a specific confirmation because no single field test is both.
- PPV collapses as prevalence falls — at elimination levels, most screen-positives are false positives, so parasitological confirmation is mandatory.
- Better drugs (fexinidazole) simplify management but do not remove the need to confirm before treating.

## Exercises
1. Using the `ppv()` logic, compute PPV by hand for a test with sensitivity 90% and specificity 99% at a prevalence of 0.1% in a screened population of 10,000. Show the 2×2 cells.
2. Explain, in two sentences for a programme manager, why "the test is 95% accurate" is a misleading way to describe what a positive screen means in a near-elimination focus.
3. Argue for or against this proposal: "To save time, let's treat all RDT-positives in remote villages without confirmation." Ground your answer in the prevalence-trap arithmetic.

## Further reading
- Buscher P et al. *Diagnostic accuracy of tests for gambiense HAT* (open-access review) — for real-world sensitivity/specificity ranges.
- WHO interim guidelines for the treatment of gambiense HAT, 2019 (WHO IRIS) — fexinidazole eligibility and staging.
- WHO TRS 984, 2013 — the reference algorithm.
