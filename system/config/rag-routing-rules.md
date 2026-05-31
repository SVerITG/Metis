# RAG Routing Rules — Metis Knowledge Pre-fetch

This file defines which queries should trigger `search_pdf_knowledge()` and which database(s) to search.
Used by Metis before routing to any specialist agent.

---

## Database inventory

Four layers, separated by **audience** (see project_knowledge_layer_architecture):
foundation + methods + NTD ship in the public-health edition; the deep HAT corpus is personal-only.

| ID | Audience | Content | Typical query signals |
|---|---|---|---|
| `ph-background` | base (PH edition) | Foundation MPH: WHO/CDC guidelines, health systems, health economics, social determinants, environmental, NCDs, nutrition, mental health, MCH, One Health/AMR, climate, health security, DHIS2 | "WHO", "CDC", "guideline", "recommendation", "health system", "health economics", "health policy", "UHC", "social determinants", "AMR", "DHIS2" |
| `epi-methods` | base (PH edition) | Multilevel models, mixed effects, spatial scan statistics, biostatistics, sampling theory, study design, R methodology | "multilevel", "MLM", "lme4", "random effects", "spatial scan", "SaTScan", "sampling", "confidence interval", "regression", "prevalence", "incidence", "study design", "bias", "confounding" |
| `ntd` | base (PH edition) | NTD program knowledge + general HAT awareness: WHO NTD roadmaps & targets, global NTD report, malaria, sleeping-sickness factsheets | "NTD", "neglected tropical", "roadmap 2030", "elimination target", "malaria", "schistosomiasis", "leishmaniasis", "sleeping sickness" (general) |
| `hat-specialist` | **personal (local only)** | Deep HAT corpus: treatment guidelines, fexinidazole, gHAT elimination verification criteria, stakeholder meetings, control & surveillance (TRS-984) | "fexinidazole", "gHAT", "elimination verification", "HAT treatment", "trypanosomiasis surveillance", "TRS-984", "passive screening" |

---

## Routing decision table

| Agent receiving the task | Search trigger | Databases |
|---|---|---|
| Epidemiologist | Any epi-methods signal | `epi-methods` (+ `ntd` if NTD topic) |
| Methods Coach | Any statistical/methods signal | `epi-methods` |
| PhD Architect | If article topic matches epi/specialist domain | `epi-methods` + `hat-specialist` |
| Writing Partner | If writing about methods or specialist domain | `hat-specialist` (HAT) / `ntd` (general) |
| DHIS2 Expert | Health-information-system questions | `ph-background` |
| Librarian | Only if user asks "what does the literature say about X" — not for catalogue tasks | by topic |
| News Radar | Never | — |
| Software Engineer | Never | — |
| All others | By topic keyword matching above | as applicable |

**HAT-vs-NTD rule:** deep/clinical HAT questions (treatment, fexinidazole, elimination verification, surveillance specifics) → `hat-specialist`. General NTD/HAT awareness (roadmaps, targets, "what is sleeping sickness") → `ntd`. When unsure on a HAT query, search both: `["hat-specialist", "ntd"]`.

---

## Retrieval parameters

```python
# Standard retrieval
search_pdf_knowledge(query=topic_phrase, databases=[db_id], k=5)

# Dual coverage (epi + specialist domain)
search_pdf_knowledge(query=topic_phrase, databases=["epi-methods", "hat-specialist"], k=4)

# Broad public health question
search_pdf_knowledge(query=topic_phrase, databases=["epi-methods", "ph-background"], k=4)

# HAT question (deep + general): search personal + base NTD layers together
search_pdf_knowledge(query=topic_phrase, databases=["hat-specialist", "ntd"], k=4)
```

Score threshold: accept any result (filter is applied server-side).
If the call returns 0 results or raises an exception → skip silently and continue routing.

---

## Skip conditions — never retrieve for

- Conversational / meta queries ("how are you", "what's the plan")
- Routing or orchestration questions ("which agent should handle", "status of project")
- News, briefings, scheduling, cron setup
- Code review, debugging, implementation questions
- Idea capture, journal entries, quick factual lookups
- Tasks where the agent is Data Guardian, Release Coordinator, or Memory Curator
