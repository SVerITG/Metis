# RAG Routing Rules — Metis Knowledge Pre-fetch

This file defines which queries should trigger `search_pdf_knowledge()` and which database(s) to search.
Used by Metis before routing to any specialist agent.

---

## Database inventory

| ID | Content | Typical query signals |
|---|---|---|
| `epi-methods` | Multilevel models, mixed effects, spatial scan statistics, biostatistics, sampling theory, study design, R methodology | "multilevel", "MLM", "lme4", "random effects", "spatial scan", "SaTScan", "sampling", "confidence interval", "regression", "prevalence", "incidence", "study design", "bias", "confounding" |
| `ph-background` | WHO guidelines, CDC recommendations, health systems, health economics, NTD program management, public health policy | "WHO", "CDC", "guideline", "recommendation", "health system", "health economics", "NTD", "neglected tropical", "program", "policy" |
| `hat-specialist` | Human African Trypanosomiasis — diagnosis, mAECT, OBI, trypanolysis, surveillance DRC, RDT sensitivity/specificity, passive/active screening | "HAT", "sleeping sickness", "trypanosomiasis", "mAECT", "OBI", "trypanolysis", "gambiense", "rhodesiense", "DRC surveillance", "passive screening", "active screening" |

---

## Routing decision table

| Agent receiving the task | Search trigger | Databases |
|---|---|---|
| Epidemiologist | Any epi-methods signal | `epi-methods` |
| Methods Coach | Any statistical/methods signal | `epi-methods` |
| PhD Architect | If article topic matches epi/HAT | `epi-methods` + `hat-specialist` |
| Writing Partner | If writing about methods or HAT | `hat-specialist` (for HAT text) |
| Librarian | Only if user asks "what does the literature say about X" — not for catalogue tasks | by topic |
| News Radar | Never | — |
| DHIS2 Expert | Never | — |
| Software Engineer | Never | — |
| All others | By topic keyword matching above | as applicable |

---

## Retrieval parameters

```python
# Standard retrieval
search_pdf_knowledge(query=topic_phrase, databases=[db_id], k=5)

# Dual coverage (epi + HAT)
search_pdf_knowledge(query=topic_phrase, databases=["epi-methods", "hat-specialist"], k=4)

# Broad public health question
search_pdf_knowledge(query=topic_phrase, databases=["epi-methods", "ph-background"], k=4)
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
