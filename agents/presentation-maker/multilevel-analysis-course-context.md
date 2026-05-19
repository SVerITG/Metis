# MLM Course — Presentation Maker Context

**Invocation:** `/presentation-maker <task title>`
**Project:** Multilevel Analysis and Spatial Scan Statistics Course
**Repo:** `SVerITG/MLM_course`
**Local path:** `C:\Users\sverschaeve\OneDrive - ITG\Documents\9. Education\1. Multilevel Analysis`

---

## What needs to be presented

Teaching material for multilevel analysis (MLM) and spatial scan statistics. Two possible audiences:

| Audience | Tone | Assumed knowledge |
|---|---|---|
| Students / trainees | Pedagogical, step-by-step | Basic statistics, some R |
| Colleagues / seminars | Technical, efficient | Graduate-level statistics |

---

## Course modules to turn into slides

| Module | Key slide content |
|---|---|
| Introduction to MLM | When clustering matters, ICC, why OLS fails |
| Binary outcomes | Logistic multilevel model, random intercepts, ICC interpretation |
| Ordinal outcomes | Cumulative link models, proportional odds assumption |
| Count outcomes | Poisson / Negative Binomial, overdispersion |
| Three-level structures | Adding a third level (health zone → province → country) |
| Longitudinal | Random slopes, growth curves |
| GEE vs MLM | Population-average vs cluster-specific interpretation |
| Spatial scan statistics | SaTScan logic, cluster output, interpretation for surveillance |

---

## Slide design principles

- **1 concept per slide** — do not compress; use reveal/animation for sequences
- **Show R code** on method slides — learners should see the actual syntax
- **Show output** next to code — coefficient tables, ICC, model comparison
- **Use real data** where possible — [your surveillance domain] data is available if appropriate
- **No decorative elements** — clean, academic, high information density

---

## Key messages per module

- **MLM intro**: "Ignoring clustering inflates type I error"
- **ICC**: "This number tells you how much the group matters"
- **GEE vs MLM**: "The question determines the model, not the other way around"
- **Spatial scan**: "Clusters are descriptive, not causal"

---

## Coordination

- **Methods Coach**: validates technical content before slides are made
- **Presentation Maker**: structures and visualises validated content
- **Software Engineer**: ensures R code examples run correctly
