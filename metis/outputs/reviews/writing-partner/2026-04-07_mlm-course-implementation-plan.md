# MLM Course Implementation Plan — Summary

**Date:** 2026-04-07
**Status:** Plan created, pending implementation

## Scope
Full implementation plan created from Stan's prompt covering:
- **Section A:** 5 global changes (terminology, sources, fonts, UX fixes, Tidyverse conversion) + 30 cartoon prompts
- **Section B:** Introduction module restructure (5 lessons)
- **Section C:** Module 1 — Variables & Measurement + Descriptive Statistics
- **Section D:** 5 discussion items needing Stan's input (ANCOVA, dummy variables, disease examples, pedagogic doc, R script fix)

## Key structural change
"What is Statistics" moves from Introduction → Module 1 Lesson 1. Introduction becomes: Unified Framework, Course Overview, Why MLM.

## Blocked
- `create_task` tool has a DB schema error (`updated_at` column missing) — new tasks could not be added to Metis
- Previous implementation history was on another Claude subscription — what's already done is unknown

## File
Implementation plan saved as `MLM_Course_Implementation_Plan.md`

## Next steps
1. Stan to confirm what was already done on other subscription
2. Fix Metis DB schema for task creation
3. Hand plan to implementing AI
