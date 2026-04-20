# MLM Course Implementation Plan — Change Log

**Date**: 2026-04-07  
**Source document**: mlm_course_implementation_plan.md  
**Logged by**: Course Architect  

---

## Global Changes (§0) — Owner: Software Engineer

| ID | Change | Status |
|----|--------|--------|
| G01 | Rename all "Part X / Part 2A" → "Module N" across all lessons | Pending |
| G02 | Replace all beta_0, beta_1 underscore notation with β₀, β₁ symbols | Pending |
| G03 | Format all source lists as bullet lists; make website sources clickable links | Pending |
| G04 | Remove LEMMA as cited source everywhere | Pending |
| G05 | Change Mastery Check max attempts from 3 → 2 globally | Pending |
| G06 | Change completion tick colour to red in all title blocks | Pending |
| G07 | Audit and standardise font sizes across all modules (H1/H2/H3/body) | Pending |
| G08 | Convert all R code to Tidyverse syntax throughout the course | Pending |
| G09 | Fix page scroll: Theory → Mastery Check must open at top | Pending |

---

## 30 Cartoon Prompts — Owner: Metis (to use with Nano Banana)

Prompts 1–30 documented in implementation plan §0.9. Cartoons to be created externally and inserted at specified lesson locations.

| ID | Location | Concept | Status |
|----|----------|---------|--------|
| C01 | Theory / What is Statistics | Researcher + chaotic data | Pending |
| C02 | Theory / What is Statistics | Coin flip / estimation | Pending |
| C03 | Theory / Variables & Measurement | Ruler measuring a cloud | Pending |
| C04 | Theory / Variables & Measurement | Variable wearing hats | Pending |
| C05 | Exercise / Variables & Measurement | Dog in cat category | Pending |
| C06 | Theory / Distributions | Bell curve sunbathing | Pending |
| C07 | Exercise / Distributions | Histogram mirror | Pending |
| C08 | Theory / Regression | Line of best fit | Pending |
| C09 | Theory / Regression | β₀ vs β₁ argument | Pending |
| C10 | Exercise / Regression | Residual bouncing off line | Pending |
| C11 | Theory / Multilevel | Nested student/class/school | Pending |
| C12 | Theory / Multilevel | Students sharing classroom | Pending |
| C13 | Exercise / Multilevel | Regression cracking | Pending |
| C14 | Theory / ICC | Pie chart within/between | Pending |
| C15 | Theory / Random Effects | Slope on roller skates | Pending |
| C16 | Exercise / Random Effects | Fixed vs random at party | Pending |
| C17 | Theory / Model Fit | AIC and BIC on a scale | Pending |
| C18 | Exercise / Model Fit | Overfitting pancakes | Pending |
| C19 | Theory / Hypothesis Testing | p=0.051 outside velvet rope | Pending |
| C20 | Exercise / Hypothesis Testing | Type I and II in waiting room | Pending |
| C21 | Theory / Confidence Intervals | Lasso around parameter | Pending |
| C22 | Exercise / Confidence Intervals | CI including/excluding zero | Pending |
| C23 | Theory / Centering | Grand-mean centering | Pending |
| C24 | Exercise / Centering | Group-mean centering | Pending |
| C25 | Theory / GLM | GLM family portrait | Pending |
| C26 | Exercise / GLM | Binary outcome forced linear | Pending |
| C27 | Theory / Assumptions | Model sneaking past diagnostics | Pending |
| C28 | Exercise / Assumptions | Fan-shaped residual ignored | Pending |
| C29 | Theory / Cross-level Interaction | Slope changing per group | Pending |
| C30 | Exercise / Cross-level Interaction | Effect only in some schools | Pending |

---

## Introduction Module — Owner: Course Architect + Software Engineer

| ID | Change | Owner | Status |
|----|--------|-------|--------|
| I01 | Remove Concept Map, Bridge Forward boxes from all Intro lessons | Course Architect | Pending |
| I02 | Add explanation in Course Overview that these features start in Module 1 | Course Architect | Pending |
| I03 | Remove Mastery Check and R Practice tabs from all Intro lessons | Software Engineer | Pending |
| I04 | What is Statistics: remove duplicate cartoon | Course Architect | Pending |
| I05 | What is Statistics: move Tie-in to "Tie-ins" heading (not under Exercises) | Course Architect | Pending |
| I06 | What is Statistics: remove R Practice section | Software Engineer | Pending |
| I07 | Unified Framework: simplify Lesson Frame to single objective sentence | Course Architect | Pending |
| I08 | Unified Framework: add mention of Multilevel Analysis | Course Architect | Pending |
| I09 | Unified Framework: fix "How this connects" to match actual course structure | Course Architect | Pending |
| I10 | Unified Framework: remove GLM question from Mastery Check | Course Architect | Pending |
| I11 | Unified Framework: remove memorisation-style Mastery Check questions | Course Architect | Pending |
| I12 | Unified Framework: R Practice tab — show "no practice required yet" message | Software Engineer | Pending |
| I13 | Unified Framework: fix Mastery Check completion state blocking R Practice | Software Engineer | Pending |
| I14 | Course Overview: update "Main Route in One View" to current structure | Course Architect | Pending |
| I15 | Course Overview: add Course Map reference + move "Open the map" button up | Software Engineer | Pending |
| I16 | Course Overview: move full module list here; remove from Unified Framework | Course Architect | Pending |
| I17 | Course Overview: update time estimates; replace "Section 7" with "Module 7" | Course Architect | Pending |
| I18 | Course Overview: update Learning Hub description text | Course Architect | Pending |
| I19 | Course Overview: restructure Learning Hub section to include XP/Practice/Exams | Course Architect | Pending |
| I20 | Course Overview: fix "In-page mastery checks" label formatting | Software Engineer | Pending |
| I21 | Course Overview: remove Mastery Check and R Practice tabs | Software Engineer | Pending |
| I22 | Course Overview: add prose explanation of why/how Mastery Checks and R Practice work | Course Architect | Pending |
| I23 | Why MLM: visually emphasise "The Assumption That Quietly Breaks" | Course Architect | Pending |
| I24 | Why MLM: remove all LEMMA citations | Course Architect | Pending |
| I25 | Why MLM: fix heading hierarchy H1/H2/H3 | Course Architect | Pending |
| I26 | Why MLM: paste R output on page + annotate key numbers | Software Engineer | Pending |
| I27 | Why MLM: add short post-intro Mastery Check (concepts already covered, no GLM/ICC) | Course Architect | Pending |
| I28 | Reorder: move "What is Statistics" → first lesson of Module 1 | Course Architect | Pending |
| I29 | Reorder: add 2–3 sentences on statistics to Unified Framework (since What is Stats moves) | Course Architect | Pending |

---

## Module 1 — Owner: Course Architect + Software Engineer

| ID | Change | Owner | Status |
|----|--------|-------|--------|
| M101 | Variables & Measurement: fix empty box / terminology layout bug | Software Engineer | Pending |
| M102 | Variables & Measurement: remove repeated content | Course Architect | Pending |
| M103 | Variables & Measurement: reduce font size of blue Hands-On explanations | Software Engineer | Pending |
| M104 | Variables & Measurement: move/retitle Step 5 (cautionary case); check for duplicates | Course Architect | Pending |
| M105 | Variables & Measurement: remove Exercises and Self-Check at end | Course Architect | Pending |
| M106 | Variables & Measurement: fix R Practice Step 2 output to match code | Software Engineer | Pending |
| M107 | Descriptive Statistics: remove empty box between mean/median and Kurtosis | Software Engineer | Pending |
| M108 | Descriptive Statistics: add actual output + annotations below all Hands-On code blocks | Software Engineer | Pending |
| M109 | Descriptive Statistics: add skewness visualisation examples | Course Architect | Pending |
| M110 | Descriptive Statistics: add links to R scripting page for visualisations/formulas | Software Engineer | Pending |
| M111 | Descriptive Statistics: move Conditions for Application higher on page | Course Architect | Pending |
| M112 | Descriptive Statistics: group normality tests under "Tests before analysis" frame | Course Architect | Pending |
| M113 | Descriptive Statistics: implement QQ-plot side-by-side (normal vs non-normal) with ggplot2 | Software Engineer | Pending |
| M114 | Descriptive Statistics: add plain-language Shapiro-Wilk explanation | Course Architect | Pending |
| M115 | Descriptive Statistics: fix/remove transformation triage sentence | Course Architect | Pending |
| M116 | Descriptive Statistics: add MLM connection section at bottom | Course Architect | Pending |
| M117 | Descriptive Statistics: expand Mastery Check to 10 questions covering normality | Course Architect | Pending |

---

## Cross-Course Standards

| ID | Change | Owner | Status |
|----|--------|-------|--------|
| X01 | Standardise example introduction: full intro on first use, reference on reuse | Course Architect | Pending |
| X02 | Fix malaria example: introduce properly in Variables & Measurement, reference thereafter | Course Architect | Pending |
| X03 | Compile full list of all examples per lesson for context/disease adaptation review | Course Architect | Pending |
| X04 | Reorganise R Scripting page into thematic tabs with Table of Contents | Software Engineer | Pending |
| X05 | Fix broken R script functionality | Software Engineer | Pending |

---

## Separate Deliverable — Owner: Course Architect

| ID | Change | Owner | Status |
|----|--------|-------|--------|
| P01 | Create Pedagogic Principles Document (standalone, reusable for future courses) | Course Architect | Pending |

---

## Deferred (Plan Mode Required)

| ID | Topic | Status |
|----|-------|--------|
| D01 | ANCOVA vs multivariate linear regression — clarify relationship in course | Awaiting discussion |
| D02 | Dummy variables — review adequacy of explanation in course | Awaiting discussion |
| D03 | Disease/context example adaptation — review example list before implementing | Awaiting discussion |
