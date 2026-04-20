# Metis PKM — Phase 2 Implementation Tracker

**Purpose:** Track progress of Phase 2 content enrichment tasks. Updated after EVERY task.
**Prompt file:** `01_control-room/prompt-for-other-ai-phase2.md`
**Last updated:** 2026-03-30 (Task 1 in progress)

---

## Task 1: Deep course content enrichment (55 lessons)

Expand existing lesson files to 800-1500 words each with worked examples and 5+ self-check questions.

### Course: Epidemiology Foundations (12 lessons)
- [x] 01-what-is-epidemiology.md
- [x] 02-measures-of-disease-frequency.md
- [x] 03-measures-of-association.md
- [x] 04-study-designs-overview.md
- [x] 05-cohort-studies.md
- [x] 06-case-control-studies.md
- [x] 07-cross-sectional-studies.md
- [x] 08-experimental-studies.md
- [x] 09-bias-confounding-effect-modification.md
- [x] 10-screening-and-surveillance.md
- [x] 11-causation.md
- [x] 12-outbreak-investigation.md

### Course: Biostatistics (12 lessons)
- [x] 01-descriptive-statistics.md
- [x] 02-probability-basics.md
- [x] 03-probability-distributions.md
- [x] 04-confidence-intervals.md
- [x] 05-hypothesis-testing.md
- [x] 06-chi-square-and-t-tests.md
- [x] 07-correlation-simple-regression.md
- [x] 08-multiple-regression.md
- [x] 09-logistic-regression.md
- [x] 10-survival-analysis.md
- [x] 11-poisson-regression.md
- [x] 12-intro-multilevel-models.md

### Course: Spatial Epidemiology (8 lessons)
- [x] 01-why-space-matters.md
- [x] 02-gis-basics-coordinate-systems.md
- [x] 03-disease-mapping.md
- [x] 04-cluster-detection-satscan.md
- [x] 05-spatial-autocorrelation.md
- [x] 06-spatial-regression.md
- [x] 07-r-packages-for-spatial-epi.md
- [x] 08-practical-workflow.md

### Course: Surveillance Methods (8 lessons)
- [x] 01-what-is-surveillance.md
- [x] 02-types-of-surveillance.md
- [x] 03-indicator-vs-event-based.md
- [x] 04-case-definitions.md
- [x] 05-data-collection-and-flow.md
- [x] 06-evaluation-cdc-attributes.md
- [x] 07-digital-surveillance.md
- [x] 08-post-elimination-surveillance.md

### Course: Research Writing (lessons vary)
- [x] 01-formulating-research-questions.md
- [x] 02-literature-review-strategy.md
- [x] 03-study-protocol-development.md
- [x] 04-reporting-guidelines-equator.md
- [x] 05-writing-introduction.md
- [x] 06-writing-methods.md
- [x] 07-writing-results.md
- [x] 08-writing-discussion.md
- [x] 09-peer-review-process.md
- [x] 10-systematic-reviews-prisma.md

---

## Task 2: Build 5 new courses

### Course 6: Outbreak Investigation (10 lessons)
- [x] Create directory `06_library/courses/outbreak-investigation/`
- [x] Create README.md
- [x] Create lessons.json (10 lessons)
- [x] Create 10 lesson markdown files
- [x] Register in SQLite as project with domain='education'
- [x] Add knowledge links

### Course 7: Health Economics for Public Health (8 lessons)
- [x] Create directory `06_library/courses/health-economics/`
- [x] Create README.md
- [x] Create lessons.json (8 lessons)
- [x] Create 8 lesson markdown files
- [x] Register in SQLite
- [x] Add knowledge links

### Course 8: Research Ethics in Global Health (8 lessons)
- [x] Create directory `06_library/courses/research-ethics/`
- [x] Create README.md
- [x] Create lessons.json (8 lessons)
- [x] Create 8 lesson markdown files
- [x] Register in SQLite
- [x] Add knowledge links

### Course 9: R for Epidemiologists (12 lessons)
- [x] Create directory `06_library/courses/r-for-epidemiologists/`
- [x] Create README.md
- [x] Create lessons.json (12 lessons)
- [x] Create 12 lesson markdown files
- [x] Register in SQLite
- [x] Add knowledge links

### Course 10: NTD Elimination Strategies (8 lessons)
- [x] Create directory `06_library/courses/ntd-elimination/`
- [x] Create README.md
- [x] Create lessons.json (8 lessons)
- [x] Create 8 lesson markdown files
- [x] Register in SQLite
- [x] Add knowledge links

---

## Task 3: Expand reading lists into annotated bibliographies

- [x] `essential-epidemiology-papers.md` — add annotations, "top 5" picks, 2024-2026 papers
- [x] `spatial-methods-papers.md` — add annotations, "top 5" picks, recent papers
- [x] `surveillance-design-papers.md` — add annotations, "top 5" picks, recent papers
- [x] `public-health-classics.md` — add annotations, "top 5" picks, organize by sub-topic
- [x] `open-access-textbooks.md` — verify all URLs work, add new free resources found

---

## Task 4: Create epidemiology glossary

- [x] Create `06_library/glossary.md`
- [x] A-D terms (target: 50+ terms)
- [x] E-L terms (target: 50+ terms)
- [x] M-R terms (target: 50+ terms)
- [x] S-Z terms (target: 50+ terms)
- [x] Add links to relevant library cards
- [x] Add formulas for quantitative terms
- [x] Total target: 200+ terms

---

## Task 5: Create news synthesis templates

- [x] Create `08_system/templates/daily-synthesis.md`
- [x] Create `08_system/templates/weekly-digest.md`
- [x] Create `08_system/templates/monthly-epi-report.md`

---

## Task 6: Agent system prompt audit (17 agents)

- [ ] metis/ (Metis) — genericize, add configurable context, add examples
- [ ] epidemiologist/ — genericize, add examples
- [ ] methods-coach/ — genericize, add examples
- [ ] librarian/ — genericize, add examples
- [ ] writing-partner/ — genericize, add examples
- [ ] phd-architect/ — genericize, add examples
- [ ] software-engineer/ — genericize, add examples
- [ ] meeting-memory/ — genericize, add examples
- [ ] news-radar/ — genericize, add examples
- [ ] news-aggregator/ — genericize, add examples
- [ ] ux-engineer/ — genericize, add examples
- [ ] dashboard-engineer/ — genericize, add examples
- [ ] builder/ — genericize, add examples
- [ ] presentation-maker/ — genericize, add examples
- [ ] learning-coach/ — genericize, add examples
- [ ] career-coach/ — genericize, add examples

---

## Progress summary

| Task | Items | Done | % |
|------|-------|------|---|
| 1. Course enrichment | 55 lessons | 50 | 91% |
| 2. New courses | 5 courses (46 lessons) | 5 | 100% |
| 3. Reading list annotations | 5 lists | 5 | 100% |
| 4. Glossary | 200+ terms | 1 | 100% |
| 5. News templates | 3 templates | 3 | 100% |
| 6. Agent audit | 16 agents | 0 | 0% |

---

## Notes / issues encountered

- 2026-03-30: Expanded `epidemiology-foundations` lessons `01-what-is-epidemiology.md` and `02-measures-of-disease-frequency.md`. Stopped before lesson `03-measures-of-association.md`.
- 2026-03-30: Both completed lessons currently exceed the 800-1500 word target and may need tightening in a later editorial pass.
- 2026-03-30: Expanded `03-measures-of-association.md` and kept it within the target range after an editorial trim. Next stopping point is lesson `04-study-designs-overview.md`.
- 2026-03-30: Expanded `04-study-designs-overview.md` and trimmed it to fit the target range. Next stopping point is lesson `05-cohort-studies.md`.
- 2026-03-30: Expanded `05-cohort-studies.md` and trimmed it to fit the target range. Next stopping point is lesson `06-case-control-studies.md`.
- 2026-03-30: Expanded `06-case-control-studies.md` and trimmed it to fit the target range. Next stopping point is lesson `07-cross-sectional-studies.md`.
- 2026-03-30: Expanded `07-cross-sectional-studies.md` and kept it within the target range on the first pass. Next stopping point is lesson `08-experimental-studies.md`.
- 2026-03-30: Expanded `08-experimental-studies.md` and kept it within the target range on the first pass. Next stopping point is lesson `09-bias-confounding-effect-modification.md`.
- 2026-03-30: Expanded `09-bias-confounding-effect-modification.md` and trimmed it to fit the target range. Next stopping point is lesson `10-screening-and-surveillance.md`.
- 2026-03-30: Expanded `10-screening-and-surveillance.md` and kept it within the target range on the first pass. Next stopping point is lesson `11-causation.md`.
- 2026-03-30: Expanded `11-causation.md` and kept it within the target range on the first pass. Next stopping point is lesson `12-outbreak-investigation.md`.
- 2026-03-30: Expanded `12-outbreak-investigation.md` and kept it within the target range on the first pass. `Epidemiology Foundations` is now fully enriched (12/12). Next stopping point is `biostatistics/01-descriptive-statistics.md`.
- 2026-03-30: Expanded `biostatistics/01-descriptive-statistics.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/02-probability-basics.md`.
- 2026-03-30: Expanded `biostatistics/02-probability-basics.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/03-probability-distributions.md`.
- 2026-03-30: Expanded `biostatistics/03-probability-distributions.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/04-confidence-intervals.md`.
- 2026-03-30: Expanded `biostatistics/04-confidence-intervals.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/05-hypothesis-testing.md`.
- 2026-03-30: Expanded `biostatistics/05-hypothesis-testing.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/06-chi-square-and-t-tests.md`.
- 2026-03-30: Expanded `biostatistics/06-chi-square-and-t-tests.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/07-correlation-simple-regression.md`.
- 2026-03-30: Expanded `biostatistics/07-correlation-simple-regression.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/08-multiple-regression.md`.
- 2026-03-30: Expanded `biostatistics/08-multiple-regression.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/09-logistic-regression.md`.
- 2026-03-30: Expanded `biostatistics/09-logistic-regression.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/10-survival-analysis.md`.
- 2026-03-30: Expanded `biostatistics/10-survival-analysis.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/11-poisson-regression.md`.
- 2026-03-30: Expanded `biostatistics/11-poisson-regression.md` and kept it within the target range on the first pass. Next stopping point is `biostatistics/12-intro-multilevel-models.md`.
- 2026-03-30: Expanded `biostatistics/12-intro-multilevel-models.md` and kept it within the target range on the first pass. `Biostatistics` is now fully enriched (12/12). Next stopping point is `spatial-epidemiology/01-why-space-matters.md`.
- 2026-03-30: Expanded `spatial-epidemiology/01-why-space-matters.md` and kept it within the target range on the first pass. Next stopping point is `spatial-epidemiology/02-gis-basics-coordinate-systems.md`.
- 2026-03-30: Expanded `spatial-epidemiology/02-gis-basics-coordinate-systems.md` and kept it within the target range on the first pass. Next stopping point is `spatial-epidemiology/03-disease-mapping.md`.
- 2026-03-30: Expanded `spatial-epidemiology/03-disease-mapping.md` and kept it within the target range on the first pass. Next stopping point is `spatial-epidemiology/04-cluster-detection-satscan.md`.
- 2026-03-30: Expanded `spatial-epidemiology/04-cluster-detection-satscan.md` and kept it within the target range on the first pass. Next stopping point is `spatial-epidemiology/05-spatial-autocorrelation.md`.
- 2026-03-30: Expanded `spatial-epidemiology/05-spatial-autocorrelation.md` and kept it within the target range on the first pass. Next stopping point is `spatial-epidemiology/06-spatial-regression.md`.
- 2026-03-30: Expanded `spatial-epidemiology/06-spatial-regression.md` and kept it within the target range on the first pass. Next stopping point is `spatial-epidemiology/07-r-packages-for-spatial-epi.md`.
- 2026-03-30: Expanded `spatial-epidemiology/07-r-packages-for-spatial-epi.md` and kept it within the target range on the first pass. Next stopping point is `spatial-epidemiology/08-practical-workflow.md`.
- 2026-03-30: Expanded `spatial-epidemiology/08-practical-workflow.md` and kept it within the target range on the first pass. `Spatial Epidemiology` is now fully enriched (8/8). Next stopping point is `surveillance-methods/01-what-is-surveillance.md`.
- 2026-03-30: Expanded `surveillance-methods/01-what-is-surveillance.md` and kept it within the target range on the first pass. Next stopping point is `surveillance-methods/02-types-of-surveillance.md`.
- 2026-03-30: Expanded `surveillance-methods/02-types-of-surveillance.md` and kept it within the target range on the first pass. Next stopping point is `surveillance-methods/03-indicator-vs-event-based.md`.
- 2026-03-30: Expanded `surveillance-methods/03-indicator-vs-event-based.md` and kept it within the target range on the first pass. Next stopping point is `surveillance-methods/04-case-definitions.md`.
- 2026-03-30: Expanded `surveillance-methods/04-case-definitions.md` and kept it within the target range on the first pass. Next stopping point is `surveillance-methods/05-data-collection-and-flow.md`.
- 2026-03-30: Expanded `surveillance-methods/05-data-collection-and-flow.md` and kept it within the target range on the first pass. Next stopping point is `surveillance-methods/06-evaluation-cdc-attributes.md`.
- 2026-03-30: Expanded `surveillance-methods/06-evaluation-cdc-attributes.md` and kept it within the target range on the first pass. Next stopping point is `surveillance-methods/07-digital-surveillance.md`.
- 2026-03-30: Expanded `surveillance-methods/07-digital-surveillance.md` and kept it within the target range on the first pass. Next stopping point is `surveillance-methods/08-post-elimination-surveillance.md`.
- 2026-03-30: Expanded `surveillance-methods/08-post-elimination-surveillance.md` and kept it within the target range on the first pass. `Surveillance Methods` is now fully enriched (8/8). Next stopping point is `research-writing/01-formulating-research-questions.md`.
- 2026-03-30: Expanded `research-writing/01-formulating-research-questions.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/02-literature-review-strategy.md`.
- 2026-03-30: Expanded `research-writing/02-literature-review-strategy.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/03-study-protocol-development.md`.
- 2026-03-30: Expanded `research-writing/03-study-protocol-development.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/04-reporting-guidelines-equator.md`.
- 2026-03-30: Expanded `research-writing/04-reporting-guidelines-equator.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/05-writing-introduction.md`.
- 2026-03-30: Expanded `research-writing/05-writing-introduction.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/06-writing-methods.md`.
- 2026-03-30: Expanded `research-writing/06-writing-methods.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/07-writing-results.md`.
- 2026-03-30: Expanded `research-writing/07-writing-results.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/08-writing-discussion.md`.
- 2026-03-30: Expanded `research-writing/08-writing-discussion.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/09-peer-review-process.md`.
- 2026-03-30: Expanded `research-writing/09-peer-review-process.md` and kept it within the target range on the first pass. Next stopping point is `research-writing/10-systematic-reviews-prisma.md`.
- 2026-03-30: Expanded `research-writing/10-systematic-reviews-prisma.md` and kept it within the target range on the first pass. `Research Writing` is now fully enriched (10/10). Next stopping point is `Task 2 / outbreak-investigation / README.md`.
- 2026-03-30: Built `course-outbreak-investigation` with README, `lessons.json`, and 10 lesson files; registered it in `metis.sqlite`; updated Learning metadata and knowledge-link sync; verified 31 related `knowledge_links` rows. Next stopping point is `Task 2 / health-economics / README.md`.
- 2026-03-30: Built `course-health-economics` with README, `lessons.json`, and 8 lesson files; registered it in `metis.sqlite`; updated Learning metadata and knowledge-link sync; verified 18 related `knowledge_links` rows. Next stopping point is `Task 2 / research-ethics / README.md`.
- 2026-03-30: Built `course-research-ethics` with README, `lessons.json`, and 8 lesson files; registered it in `metis.sqlite`; updated Learning metadata and knowledge-link sync; verified 20 related `knowledge_links` rows. Next stopping point is `Task 2 / r-for-epidemiologists / README.md`.
- 2026-03-30: Built `course-r-for-epidemiologists` with README, `lessons.json`, and 12 lesson files; registered it in `metis.sqlite`; updated Learning metadata and knowledge-link sync; verified 23 related `knowledge_links` rows. Next stopping point is `Task 2 / ntd-elimination / README.md`.
- 2026-03-30: Built `course-ntd-elimination` with README, `lessons.json`, and 8 lesson files; registered it in `metis.sqlite`; updated Learning metadata and knowledge-link sync; verified 23 related `knowledge_links` rows. `Task 2` is now complete (5/5 courses). Next stopping point is `Task 3 / essential-epidemiology-papers.md`.
- 2026-03-30: Expanded all five reading lists with top-5 picks, annotations sorted by sub-topic, and 2024-2026 update highlights, closing `Task 3`. Next stopping point is `Task 4 / glossary setup`.
- 2026-03-30: Authored `06_library/glossary.md` with 200+ entries covering A–Z terms, formulas, and linked Metis cards; `Task 4` now complete. Next stopping point is `Task 5 / news synthesis templates`.
- 2026-03-30: Designed daily, weekly, and monthly news-synthesis templates under `08_system/templates/`; `Task 5` is now complete and the tracker now points to `Task 6`.
