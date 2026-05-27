# DHIS2 Reference: HAT Stage Confirmation Program Stage
**Created:** 2026-05-26
**Source:** DHIS2 Expert agent output (see `outputs/reviews/dhis2-expert/2026-05-26_hat-stage-confirmation-program-stage.md`)
**Applies to:** HAT Case Management tracker program, Stage Confirmation stage

---

## Summary

The **Stage Confirmation** program stage captures the clinical workup that assigns HAT disease stage (Stage 1 haemo-lymphatic vs. Stage 2 meningo-encephalitic). It sits between Diagnosis and Treatment in the program stage order.

## Key design decisions

1. **Separate stage** (not merged with Diagnosis) — LP and staging workup happen on a different date/visit from initial serodiagnosis.
2. **Lymph node palpation** — gated section; DE `Lymph node palpation performed` (Yes/No) gates all downstream lymph node DEs.
3. **Woo test (mAECT)** — gated section; specimen type optionSet determines which result fields appear. CSF Woo result feeds into auto-staging rule.
4. **LP** — gated section; `CSF WBC count` drives auto-categorisation (PR-5) and auto-staging (PR-6/PR-7).
5. **Auto-staging via Program Rules** — Stage 2 triggers on WBC ≥5, CSF trypanosomes, or Woo CSF positive. Stage 1 triggers on LP normal + no CSF evidence.
6. **Warning if Stage 2 without LP** — PR-8 surfaces a warning without blocking completion.

## Data elements (21 total across 4 sections)

- Section 1: Lymph node assessment (5 DEs)
- Section 2: Woo test / mAECT (5 DEs)
- Section 3: Lumbar puncture (7 DEs)
- Section 4: Stage assignment (4 DEs)

## Program rules (9 total)

PR-1–PR-4: Gate/hide DEs by test performed.
PR-5: Auto-categorise WBC count.
PR-6: Auto-assign Stage 2.
PR-7: Auto-assign Stage 1.
PR-8: Warning — Stage 2 without LP.
PR-9: Warning — LP contraindicated but performed.

## Staging threshold

| Criterion | Stage |
|---|---|
| CSF WBC ≥5 cells/µL | Stage 2 |
| Trypanosomes in CSF (any method) | Stage 2 |
| Woo test on CSF positive | Stage 2 |
| LP normal + no CSF evidence | Stage 1 |

Source: WHO TRS 984 (2019).

## Files

- Full blueprint: `outputs/reviews/dhis2-expert/2026-05-26_hat-stage-confirmation-program-stage.md`
- Related: `outputs/reviews/dhis2-expert/2026-05-26_hat-tracker-design.md`
