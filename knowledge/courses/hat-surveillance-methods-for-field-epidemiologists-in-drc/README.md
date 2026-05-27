# HAT Surveillance Methods for Field Epidemiologists in DRC

An 8-module practical course on gambiense human African trypanosomiasis (gHAT, sleeping sickness) surveillance, written for field epidemiologists working in the Democratic Republic of the Congo as the country drives toward elimination as a public health problem (EPHP).

## Audience and prerequisites
- Field epidemiologists and programme staff working on gHAT in the DRC.
- Assumed: working knowledge of basic epidemiology (incidence, prevalence, case definition, test 2x2 table) and some R exposure.
- No prior trypanosomiasis knowledge required — Lesson 1 builds it.

## What you will be able to do
After the course you can apply the gHAT case definition and diagnostic algorithm, plan and evaluate passive and active detection, audit a reporting chain into DHIS2 and the HAT Atlas, design tsetse vector surveillance, analyse and map surveillance data in R, and evaluate a health zone's evidence package against WHO EPHP criteria.

## Structure (about 8 hours)
1. gHAT and the DRC Surveillance Landscape (Understand)
2. Passive Surveillance and Health-Facility Detection (Apply)
3. Active Case Finding with Mobile Teams (Apply)
4. Case Definitions, Diagnostic Algorithms, and Test Performance (Analyze)
5. Data Flow, DHIS2, and the National HAT Atlas (Apply)
6. Vector Surveillance and Integrated Tsetse Control (Apply)
7. Analysing and Mapping Surveillance Data in R (Analyze)
8. Surveillance in the Elimination Endgame: Verification and Reintroduction Risk (Evaluate)

## How to work through it
- Take the lessons in order — Lesson 8 (the capstone) integrates all the earlier ones, and Lesson 4's test-performance arithmetic is reused throughout.
- Each lesson has Learning objectives, Prerequisites, Content (with worked DRC examples), a Summary, Exercises, and Further reading.
- Run the R blocks in Lesson 7 yourself; they use only standard tidyverse and the `sf` example shapefile, so they work on a clean install.

## How assessments are graded
- Each lesson's Exercises are formative (self-check) — compare your answers to the lesson Summary and worked examples.
- `assessment.md` holds the graded items per module plus a final capstone (evaluate a zone dossier). Assessment difficulty never exceeds each lesson's Bloom ceiling.
- Acceptance threshold for this course: "I could apply this in the field."

## Sources
Built open-access-first from WHO TRS 984 (2013), WHO gHAT treatment guidelines (2019), the WHO NTD roadmap 2021-2030, the HAT Atlas paper (Franco et al. 2020), tiny-target vector evaluations (Tirados/Courtin 2015), and DRC elimination-timeline modelling (Crump et al. 2024). Full source metadata is in `sources/`.

## Honesty notes
- The animal reservoir / cryptic transmission question for gHAT is genuinely **contested**; Lesson 8 frames it as uncertain rather than settled.
- Library background coverage for several modules (vector control, gHAT-specific operations) was Weak or Empty — see `modules/00_coverage-report.md`. Those modules are drawn from the harvested sources above, with proposed library additions listed in the coverage report.

## Glossary pointers
gHAT, PNLTHA-RDC, EPHP, EOT, CATT, RDT, mAECT, fexinidazole, tiny target, flies/trap/day (FTD), HAT Atlas, DHIS2 — all defined at first use in the lessons. See related Metis cards in `knowledge/library/methods/` and `knowledge/library/concepts/`.
