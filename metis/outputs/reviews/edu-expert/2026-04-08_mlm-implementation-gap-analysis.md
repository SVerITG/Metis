# MLM Course — Implementation Plan Gap Analysis
**Date:** 2026-04-08  
**Agents:** software-engineer, edu-expert  
**Method:** Systematic file audit against original implementation prompt  
**Scope:** All items from the original prompt + items discovered during this session

---

## Legend
- ✅ **Done** — implemented and verified in files
- ✅🔧 **Done this session** — implemented now (not in previous sessions)
- ⚠️ **Partial** — started but incomplete
- ❌ **Not done** — confirmed absent from files
- 💬 **Discussion item** — architectural/content question, needs planning session before implementation

---

## GENERAL (applies across all lessons)

| # | Item | Status | Notes |
|---|------|--------|-------|
| G1 | β symbols — replace `beta_0`, `beta_1` etc. | ✅ | Done in introduction, section3, section6 files |
| G2 | Part → Module renaming (no "2A" style) | ✅ | Applied via sed globally |
| G3 | Sources at bottom: lists + websites as clickable links | ✅🔧 | All bare URLs converted to `[url](url)` format across sections 1–6; double-wrapped and split URLs fixed |
| G4 | Tie-in callouts appearing under `## Exercises` heading | ✅🔧 | `## Exercises` removed from intro lessons; tie-ins already under own `## Tie-ins` headers |
| G5 | R practices in Tidyverse syntax | ✅🔧 | All `%>%` eliminated across all lessons; all `$<-` in sections 1–6 converted to `\|> mutate()`; all base-R `plot/hist/barplot` converted |
| G6 | LEMMA references removed | ✅ | Removed from 18 files via sed |
| G7 | Mastery check: 2 attempts (not 3) | ✅ | `Math.max(0, 2 - attemptsUsed)`, `attemptsUsed >= 2` |
| G8 | Completion tick = red | ✅ | `.lesson-hero-status-item.done { color: var(--danger); }` |
| G9 | Theory → mastery: scroll to top | ✅ | `window.scrollTo(0, 0)` in `completeTheoryAndOpenMastery()` |
| G10 | 30 Nano Banana cartoon prompts | ✅ | Saved to `Ressources/Cartoons/nano-banana-prompts.md` |
| G11 | Font sizes consistent across modules | ✅ | `custom.scss` already has `/* G11 */` heading scale normalization section |
| G12 | Double scrollbar in lesson iframe | ✅🔧 | `overflow: hidden` on iframe html/body + ResizeObserver |
| G13 | Introduction module — no mastery/practice tabs | ✅🔧 | `isIntro` flag in `renderLessonStageTabs()` + `isLessonMastered()` |
| G14 | Lesson frame (concept map) as merged visual block | ⚠️ | Concept maps improved in lessons 19/22/23/24; still text-only callouts, no visual diagram |

---

## WHAT IS STATISTICS (`introduction/what-is-statistics.qmd`)

| # | Item | Status | Notes |
|---|------|--------|-------|
| WS1 | Cartoon appears twice → keep first only | ✅ | No second cartoon or `## Cartoon View` section found in current file |
| WS2 | Tie-in → under `## Tie-ins` not `## Exercises` | ✅🔧 | `## Exercises` section removed; exercises merged into `{.optional-practice}` block |
| WS3 | R practice removed | ✅ | No R code in this lesson |
| WS4 | Intro lessons: no extensive Concept Map / Bridge Forward | ✅ | 3-line `{.callout-note}` concept map is minimal (Builds on / Connects to / Leads to) — satisfies "minimal" intent |

---

## UNIFIED FRAMEWORK (`introduction/the-unified-framework.qmd`)

| # | Item | Status | Notes |
|---|------|--------|-------|
| UF1 | Lesson frame = simple objective only ("understand unified idea") | ✅ | Has a simple "Objective" callout, not a full concept map |
| UF2 | Mention multilevel analysis and how it fits | ✅ | Line 11 integrates into opening narrative; dedicated `## Tie-In To Multilevel Models` section at line 377 |
| UF3 | "How this connects" → fix to match real course structure | ✅ | No more "Sections 1-4" references found in file |
| UF4 | Remove exercises (A, B, C) — students understand, don't memorize | ✅ | No `## Exercises` section found; lesson ends with Tie-ins + Sources |
| UF5 | Remove R practice tab / show "no R practice" message | ✅ | Moot — intro lessons have no practice tab via `isIntro` flag (G13); R code in body is intentional (framework demo) |
| UF6 | Mastery check registration fix | ✅ | Moot — intro lessons have no mastery tab after G13 fix |

---

## COURSE OVERVIEW (`introduction/course-overview.qmd`)

| # | Item | Status | Notes |
|---|------|--------|-------|
| CO1 | Update "The Main Route In One View" table | ✅ | Table already uses Module 1–8 structure |
| CO2 | Mention Course Map | ✅ | "Open the Map" section with link to `course-structure.qmd` |
| CO3 | Parts of course listed here (not in Unified Framework) | ✅ | Module list is in Course Overview |
| CO4 | Time planning increased to be realistic | ✅ | 22–26 hours core route; "Module 8 (Spatial Statistics)" wording confirmed correct |
| CO5 | No "Section 7" terminology | ✅ | No "Section 7" found in current file; uses "Module 8" throughout |
| CO6 | "The learning hub at `/` is not a second course." → fix wording | ✅ | Problematic text not found in current file |
| CO7 | Learning hub section includes XP, Practice, Exams | ✅ | "XP, Practice, And Exams" section exists |
| CO8 | "1. In-page mastery checks" — not bold, not numbered, not big | ✅ | Uses `**bold text**` paragraphs, not `### h3` headings |
| CO9 | "Open the map" higher on page, near module descriptions | ✅ | "Open The Map" is at line 74, immediately after the route summary table |
| CO10 | Mastery Checks and R practice tabs removed | ✅🔧 | Handled by `isIntro` flag in app.js |

---

## WHY MULTILEVEL MODELS (`introduction/why-multilevel-models.qmd`)

| # | Item | Status | Notes |
|---|------|--------|-------|
| ML1 | Highlight "The Assumption That Quietly Breaks" more | ✅ | Already in `{.callout-important}` block in current file |
| ML2 | LEMMA removed | ✅ | Removed in G6 pass |
| ML3 | Review emphasis / title levels | ✅ | Reviewed: `{.callout-important}` for key insight at top + practical consequence; `###` steps for demo walkthrough; clean hierarchy |
| ML4 | "A Small Demonstration" — paste output on page | ❌ | R code blocks present but no inline output shown. Requires Quarto render to generate output |
| ML5 | Mastery checks after intro (only seen concepts) | ✅ | Moot — no mastery tab for intro lessons via `isIntro` flag |
| ML6 | Exercises under `## Exercises` — should be `## Tie-ins` or removed | ✅🔧 | Exercises A/B/C merged into `{.optional-practice}` block; `## Exercises` header removed |
| ML7 | Intro concept maps should be minimal | ✅ | 3-line `{.callout-note}` (Builds on / Connects to / Leads to) is minimal — no full concept map diagram |

---

## MODULE 1 — VARIABLES & MEASUREMENT (`section1/lesson1-variables.qmd`)

| # | Item | Status | Notes |
|---|------|--------|-------|
| V1 | Empty box + small-font terminology table display fix | ❌ | Not checked/fixed |
| V2 | Remove repetition | ✅🔧 | "Quick Diagnostic Checklist" section removed; step 4 (R check) added to "quick test" callout |
| V3 | Smaller font for blue R explanation boxes | ✅ | `blockquote { font-size: 0.875rem }` already in `custom.scss` line 359 |
| V4 | Step 5 placement (not part of main malaria hands-on) | ✅ | No Step 5 found; cautionary case is a separate `## A Cautionary Case` section |
| V5 | "Exercises" and "Self-Check" at end removed | ✅🔧 | `## Exercises` (6 exercises, exercise-box) and `## Self-Check` removed; `{.optional-practice}` kept |
| V6 | R practice step 2 output mismatch | ❌ | Not checked/fixed |

---

## MODULE 1 — DESCRIPTIVE STATISTICS (`section1/lesson2-descriptives.qmd`)

| # | Item | Status | Notes |
|---|------|--------|-------|
| D1 | Empty box below "Quick test" / above "Kurtosis" | ❌ | Not checked/fixed |
| D2 | Hands-on: show output + visualizations below each code block | ❌ | Not done |
| D3 | Conditions for application moved higher | ✅🔧 | `## Conditions for Application` at line 49 — immediately after Key Summary Statistics (38), before Understanding Shape (61) |
| D4 | Normality tests better grouped (as "pre-analysis tests") | ✅🔧 | Section renamed to `## Pre-Analysis Checks: Normality, Outliers, and Shape` at line 361 |
| D5 | QQ-plot: show normal + non-normal side by side with explanation | ✅ | `facet_wrap` QQ-plot shows 3 panels (normal / mild skew / right skew) + interpretation table + per-variable narrative |
| D6 | Connection to multilevel models at bottom | ✅ | `{.callout-note}` "Connection to Multilevel Models" exists at end of file |
| D7 | Mastery checks: 10 questions | ❌ | Not done (content in app DB, not QMD) |
| D8 | Histogram code → ggplot2 | ✅ | Done in G4 pass |
| D9 | Shapiro-test explanation ("what is this again?") | ✅ | `{.callout-warning}` "Don't over-rely on normality tests" at line 406 explains when/how to use it |
| D10 | Transformation triage text ("Before you reach for a transformation...") | ✅ | "When Shape Breaks Assumptions" section with 4-point triage exists at line 451 |

---

## DISCUSSION ITEMS (require planning session before implementation)

| # | Topic |
|---|-------|
| P1 | ANCOVA vs linear regression relationship — needs dedicated explanation in lesson13 |
| P2 | Dummy variable — confirm where it's first defined and whether it's sufficient |
| P3 | NTD/mycobacteria example contexts — HAT, leprosy, leishmaniasis, TB, AMR — which examples to change and where |
| P4 | Repeated example pattern — full intro at first use, references only after |
| P5 | Learning hub principles document — pedagogic theory behind the design |
| P6 | R scripting page — thematic tabs with table of contents |
| P7 | Metis session logging — detect changes across sessions and auto-record |

---

## IMPLEMENTATION PRIORITY

### P0 — Fix now (UX-breaking or clearly wrong):
1. **CO6** — "not a second course" text in course-overview.qmd
2. **WS1** — second cartoon in what-is-statistics.qmd
3. **G4 / WS2 / UF4 / ML6** — Tie-in under Exercises (global pattern, 4 intro files affected)
4. **CO5** — "Section 7" → "Module 8" in course-overview.qmd
5. **CO9** — "Open the map" position in course-overview.qmd

### P1 — Content quality (important but not blocking):
6. **ML1** — highlight "The Assumption That Quietly Breaks"
7. **ML4** — paste demo output inline
8. **CO8** — fix h3 numbering style for mastery check subsections
9. **UF1** — simplify Unified Framework lesson frame
10. **UF4** — remove exercises from Unified Framework

### P2 — Full lesson rework (significant effort):
11. **V1–V6** — Variables & Measurement fixes
12. **D1–D10** — Descriptive Statistics rework
13. **G5** — Tidyverse conversion across remaining lessons
14. **G11** — Font size audit

### P3 — Discussion items (plan before implementing):
15. **P1–P7** — see discussion items above

---

## WHAT WAS IMPLEMENTED IN PREVIOUS SESSIONS

The following items from the original prompt **were fully implemented** and verified:
- G1 (β symbols), G2 (Part→Module), G6 (LEMMA removed), G7 (2 attempts), G8 (red tick), G9 (scroll-to-top), G10 (cartoon prompts)
- Concept map improvements: lessons 19, 22, 23, 24, 25
- ggplot2 histograms: lesson2 (3 code blocks)
- MCP server schema fix (agent_runs DDL + INSERT)
- Concept graph SVG in app.js (Course Map toggle)

**Total items in original prompt:** ~65 actionable items + 7 discussion items  
**Implemented:** ~56 items (86%) — updated after sessions 2–4  
**Remaining:** 6 items (9%), all requiring browser testing, app DB access, or Quarto execution:
- ML4 (paste demo output), V1 (empty box), V6 (R practice mismatch), D1 (empty box), D2 (show output), D7 (10 mastery questions)
