# MLM Course — Methods Coach Context

**Invocation:** `/methods-coach <task title>`
**Project:** Multilevel Analysis and Spatial Scan Statistics Course
**Repo:** `SVerITG/MLM_course`
**Local path:** `C:\Users\sverschaeve\OneDrive - ITG\Documents\9. Education\1. Multilevel Analysis`

---

## Course scope

Teaching course on multilevel modelling (MLM) and spatial scan statistics. Dual audience:
- **Personal learning**: researcher building methodological depth for PhD
- **Teaching**: potential external audience (students, colleagues)

---

## Methods covered

### Multilevel analysis (MLM)
| Example script | Method | Model type |
|---|---|---|
| logistic.R | Binary outcome | 2-level logistic |
| ordinal.R | Ordered outcome | Cumulative link |
| poisson_nb.R | Count outcome | Poisson / Negative Binomial |
| three_level.R | Three-level structure | Random intercepts |
| longitudinal.R | Repeated measures | Random slopes |
| gee.R | Population average | GEE (marginal model) |

### Spatial scan statistics
- SaTScan integration (links to HAT clustering project)
- Space-time cluster detection for epidemiological outcomes
- Interpretation for surveillance decisions

---

## Methods Coach tasks for this project

- **Review logistic MLM example** — is the ICC interpretation correct? Are random effects justified?
- **Connect spatial scan to MLM** — how do cluster membership and multilevel structure interact?
- **Validate teaching assumptions** — are the examples using plausible data-generating mechanisms?
- **HPC workflow** — does the spatial scan material reference HPC correctly?
- **Suggest missing methods** — is there a gap between MLM and spatial stats (e.g., spatially structured random effects, INLA)?

---

## Key methodological principles for teaching

- Always state the **research question** before the model
- Distinguish **random effects** (heterogeneity) from **fixed effects** (average associations)
- ICC and VPC should always be reported and interpreted
- GEE vs MLM choice depends on whether the question is **population-average** or **cluster-specific**
- Spatial scan: clusters are **descriptive**, not causal — be explicit about this

---

## Coordination

- **Methods Coach**: validates the statistical content and teaching assumptions
- **Presentation Maker**: turns validated content into slides
- **Software Engineer**: reviews R scripts for correctness and reproducibility
- **Writing Partner**: improves written explanations in Quarto files
