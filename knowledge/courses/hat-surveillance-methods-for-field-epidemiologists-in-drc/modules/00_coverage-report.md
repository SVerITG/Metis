# Coverage Report — HAT Surveillance Methods for Field Epidemiologists in DRC
Generated: 2026-05-26

## Library Coverage by Module

| Module | PH Domain(s) | Library Words | Status | Notes |
|--------|--------------|---------------|--------|-------|
| 01 gHAT & DRC landscape | NTD / disease epidemiology | ~low | Weak | Only WHO-AFRO regional reports mention HAT in passing; no gHAT-specific monograph in `ph_library`. |
| 02 Passive surveillance | Surveillance systems | adequate | Adequate | Generic surveillance theory present (CDC attributes, IDSR-style framing); gHAT diagnostic specifics absent. |
| 03 Active case finding | Field epi / screening | ~low | Weak | No mobile-team / CATT-RDT screening operational literature indexed. |
| 04 Case definitions & test performance | Diagnostics / biostatistics | adequate | Adequate | Sens/spec/PPV theory well covered (Biostatistics-for-Epi-PH-using-R); gHAT-specific test data must come from harvested sources. |
| 05 Data flow / DHIS2 / HAT Atlas | HIS / surveillance data | ~low | Weak | No HAT Atlas or DHIS2-HAT documentation indexed. |
| 06 Vector surveillance & tsetse control | Entomology / vector control | 0 | Empty | No tsetse / Glossina / tiny-target literature in library. |
| 07 Analysis & mapping in R | Statistics / spatial epi | strong | Strong | tidyverse, Leyland MLM, spatial epi resources present; methods transferable. |
| 08 Elimination endgame & verification | NTD elimination | adequate | Adequate | `ntd-elimination` course + WHO road-map framing available; gHAT verification criteria from harvested WHO docs. |

## Strongly covered areas (>=50k words in library)
- Statistical analysis and R (tidyverse, regression, multilevel models) — Module 7 fully supportable from existing library.

## Weakly covered or empty areas
- **gHAT disease-specific surveillance** (Modules 1, 3, 5) — Weak. The `ph_library` holds WHO-AFRO regional statistics but no dedicated gambiense-HAT operational guidance.
- **Tsetse / vector surveillance** (Module 6) — Empty. No entomology content indexed.

These modules will be drafted from harvested open-access sources (below), not from the existing library. All gHAT operational and test-performance figures are cited to the harvested WHO / peer-reviewed sources.

## Recommended additions before next course build
- [ ] WHO (2013) *Control and surveillance of human African trypanosomiasis* — TRS 984 (open access, WHO IRIS)
- [ ] WHO interim guidelines for the treatment of gHAT (latest edition, WHO IRIS) — open access
- [ ] Franco et al. *Monitoring the elimination of HAT at continental and country level* (PLoS NTD, open access) — for the HAT Atlas data pipeline
- [ ] Crump et al. 2024, *Parasites & Vectors* — gHAT elimination timeline modelling for DRC accounting for cryptic transmission (already surfaced by Librarian 2026-05-26; OA)
- [ ] Tirados / Courtin tiny-target tsetse control field papers (PLoS NTD, OA) — to fill the empty Module 6 vector domain
