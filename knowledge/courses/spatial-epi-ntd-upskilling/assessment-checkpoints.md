# Assessment Checkpoints
## Spatial Epidemiology Upskilling Programme — NTD Field Epidemiologists

**Philosophy:** Assessments are formative first, summative second. Every checkpoint produces actionable feedback before the next phase begins. No participant fails — struggling participants receive targeted coaching before progressing.

---

## Checkpoint 1 — Phase 1 Exit Assessment (End of Week 5 / Start of Week 6)
**Domains covered:** A1–A5, B1–B5  
**Format:** 90-minute individual R practical + peer map critique  
**Mode:** Take-home (submit by end of Week 5)

### Task 1A — Spatial Data Wrangling (45 min)
Provided: a prevalence CSV + a shapefile with intentional issues (CRS mismatch, 5 unmatched district names, 3 invalid GPS points)

Participants must:
1. Identify and document all data quality issues
2. Resolve CRS, join data correctly, flag GPS outliers
3. Produce a cleaned `sf` object with documentation of decisions made

**Pass criteria:** All 3 issue types identified; join produces ≥ 90% match rate; R script is reproducible (runs clean from top).

### Task 1B — Map Production (45 min)
Using the cleaned dataset from 1A, produce:
1. A choropleth map suitable for a technical report (colour-blind safe, proper projection, scale bar, north arrow, legend)
2. A simplified print map for a district health officer (no statistical jargon, clear action message)

**Pass criteria:** Both maps render; Reviewer checklist (10 items) scores ≥ 7/10 on each.

### Peer Review Component
Each participant reviews one colleague's maps using a structured rubric (communication clarity, colour choice, audience-appropriateness). Written feedback (< 300 words) submitted.

### Remediation trigger
Score < 6/10 on Task 1A or 1B → 1-hour targeted coaching session before Week 7 begins. Concepts reinforced: whichever of {CRS, joining, colour/map design} scored lowest.

---

## Checkpoint 2 — Phase 2 Mid-Point Assessment (End of Week 12)
**Domains covered:** C1–C5 (spatial statistics, descriptive)  
**Format:** Group analysis challenge (pairs) + individual interpretation memo  
**Mode:** 2-hour in-session practical

### Task 2A — Method Selection Challenge (group, 30 min)
Three NTD surveillance scenarios presented (district counts, household GPS cases, time-series by month). Pairs must:
1. Select the most appropriate spatial statistics method for each
2. Justify their choice in 2–3 sentences per scenario

**Pass criteria:** ≥ 2/3 method selections appropriate; justifications reference assumptions (not just naming methods).

### Task 2B — Applied Analysis (individual, 75 min)
Provided: a new district-level dataset (not used in practicals)

Participants must:
1. Compute Global Moran's I and state whether significant clustering exists
2. Run LISA and produce a labelled cluster map
3. Run a spatial scan and identify the top cluster (LLR, RR, p-value)
4. Write a 200-word interpretation connecting all three methods

**Pass criteria:** All three methods run without error; interpretation correctly distinguishes what each method tells you; no contradictory statements between methods.

### Reflection prompt (individual, 15 min)
"What is one thing these methods cannot tell you about NTD transmission that field data could?" Written submission, not graded — used for facilitator feedback on conceptual depth.

### Remediation trigger
Task 2B score < 60% → supplementary worked example session (2 h) before Phase 3 begins. Peer support pairing assigned.

---

## Checkpoint 3 — Phase 3 Exit Assessment (End of Week 18)
**Domains covered:** D1–D5 (spatial regression)  
**Format:** Individual analysis report  
**Mode:** Take-home over 1 week (submitted end of Week 18)

### Task 3 — Full Regression Pipeline
Provided: a district NTD dataset with 6 candidate covariates (poverty index, rainfall, forest cover, health worker density, distance to water, urbanisation score)

Participants must produce a structured analysis report (~1,500 words + code appendix) including:

1. **Covariate selection:** Correlation matrix + VIF check; state which covariates retained and why
2. **Baseline model:** OLS regression; Moran test on residuals; state whether spatial model is needed
3. **Model choice:** Fit spatial lag and spatial error model; compare AIC + LM tests; justify final model selection
4. **Interpretation:** For each retained covariate, write 1 sentence interpreting the coefficient in programme terms (not just statistics)
5. **Uncertainty:** State 95% CI for the strongest predictor; explain what this means for programme decision-making
6. **Map output:** Map model residuals; identify any remaining spatial pattern

**Marking rubric:**

| Criterion | Weight | Indicators |
|-----------|--------|-----------|
| Technical correctness | 40% | Correct syntax, no logical errors, valid model diagnostics |
| Interpretation quality | 30% | Programme-relevant language; correct directionality; no over-claiming |
| Model justification | 20% | Selection criteria stated; alternatives compared |
| Communication | 10% | Report is readable by a technical (non-spatial) colleague |

**Pass criteria:** ≥ 60% total; ≥ 50% on Technical correctness specifically.

### Remediation trigger
< 60% overall or < 50% technical → 1:1 session reviewing the specific failed component; resubmission of that section only within 1 week.

---

## Checkpoint 4 — Capstone Final Assessment (Week 26)
**Domains covered:** All (A–E)  
**Format:** Individual or pair project + 12-minute presentation  
**Reviewers:** Facilitator + one external reviewer (programme manager or NTD methods expert)

### Deliverable package (submitted end of Week 25):
1. Cleaned, documented spatial dataset (`.rds` + data dictionary)
2. Descriptive spatial analysis script (Moran's I, LISA, KDE or scan)
3. Spatial regression model script with residual diagnostics
4. Two final maps: one technical, one programme-facing
5. One-page programme brief with a spatial evidence-based recommendation
6. R Markdown / Quarto report knitting all components

### Presentation structure (12 min + 5 min Q&A):
- 2 min: Programme context and research question
- 4 min: Spatial analysis findings (walk through maps)
- 3 min: Regression model and key drivers
- 3 min: Recommendation and operational implication

### Capstone rubric:

| Criterion | Weight | Indicators |
|-----------|--------|-----------|
| Spatial analysis rigour | 25% | Correct methods for the data type; assumptions checked |
| Map quality | 20% | Technical and programme maps both meet Phase 1 standards |
| Interpretation & inference | 25% | Conclusions supported by analysis; uncertainty acknowledged |
| Programme relevance | 20% | Recommendation is operational; audience-appropriate brief |
| Code quality | 10% | Reproducible; commented; runs clean |

**Distinction:** ≥ 80% overall  
**Pass:** ≥ 60% overall  
**Support plan:** < 60% → 2-week extension with facilitator support; revised submission accepted

---

## Continuous Assessment — Spaced Review Quizzes

Embedded in each module opening (see module-sequence.md), these are **not graded** but are **tracked** to flag participants falling behind:

- 5–10 multiple choice / short answer questions per session
- Automatic trigger: < 60% on any domain quiz → facilitator notified within 48 hours
- Peer support pair contacted to schedule a review session

**Quiz bank domains and timing:**
| Quiz | Domain | Triggered in |
|------|--------|-------------|
| Q1 | A1 (CRS, vector/raster) | Week 2 |
| Q2 | A2–A3 (joining, sf) | Week 3 |
| Q3 | B1–B4 (maps, colour) | Week 6 |
| Q4 | C1–C2 (Moran, LISA) | Week 9 |
| Q5 | C3–C5 (variogram, KDE, scan) | Week 12 |
| Q6 | D1–D2 (lag/error models) | Week 15 |
| Q7 | D3–D5 (Poisson, GWR, model eval) | Week 18 |
| Q8 | E1–E5 (NTD applications) | Week 25 |

---

## Programme Completion Certificate Criteria

To receive a programme completion certificate, participants must:
- [ ] Pass Checkpoints 1, 2, 3 (≥ 60% each, remediation pathway counts)
- [ ] Pass Capstone (≥ 60%)
- [ ] Complete ≥ 80% of weekly practicals (submission of R script counts)
- [ ] Submit all peer review tasks
- [ ] Attend ≥ 20 of 26 sessions (or catch-up equivalents)
