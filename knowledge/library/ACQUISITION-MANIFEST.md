# Background-Layer Acquisition Manifest

Curated list of authoritative, open-access **books/major reports** to acquire and index so each
background layer is a genuine *reference frame*. Books/handbooks/flagship reports are preferred over
single articles — they cover a topic comprehensively and age more slowly. Re-reviewed periodically.

Status legend: ☐ to acquire · ☑ indexed · ⚠ needs manual download (IRIS/login)

---

## PRIORITY GAPS (thin or empty domains)

### Africa & Sub-Saharan Africa  → `ph-background` / domain "Africa & Sub-Saharan Africa"  (currently EMPTY)
- ☐ Disease Control Priorities, 3rd ed (DCP3) — Vol. 9 "Improving Health and Reducing Poverty" (World Bank, open)
- ☐ WHO AFRO — The State of Health in the WHO African Region (open)
- ☐ World Bank — Africa Human Capital / health financing flagship (open)
- ☐ WHO AFRO — Atlas of African Health Statistics (latest, open)
- ☐ Lancet Commission — The path to universal health coverage in Africa (open)

### NCDs  → `ph-background` / domain "NCDs"  (currently 1 doc)
- ☐ WHO — Global Action Plan for the Prevention and Control of NCDs 2013–2030 (open)
- ☐ WHO — NCD Progress Monitor (latest, open)
- ☐ WHO — Saving lives, spending less: the case for investing in NCDs (open)
- ☐ WHO — Package of Essential NCD Interventions (PEN) for primary care (open)

### Health Economics  → `ph-background` / domain "Health Economics"  (currently 1 doc)
- ☐ Disease Control Priorities 3 — Vol. 9 economics chapters (World Bank, open)
- ☐ WHO — Health systems financing: the path to universal coverage (World Health Report 2010, open)
- ☐ WHO — Making fair choices on the path to UHC (open)
- ☐ WHO — Global spending on health (latest report, open)
- ☐ WHO guide to cost-effectiveness analysis (WHO-CHOICE, open)

---

## DEEPEN EXISTING LAYERS (books > articles)

### Epidemiology & Methods  → `epi-methods`
- ☐ WHO — Basic Epidemiology, 2nd ed (Bonita, Beaglehole, Kjellström) — open, the canonical free epi text
- ☐ CDC — Principles of Epidemiology in Public Health Practice, 3rd ed (open courseware)
- ☐ OpenIntro Statistics, 4th ed (open) — biostatistics foundation
- ☐ Moraga — Geospatial Health Data: Modeling and Visualization (bookdown, open) — spatial epi
- ☐ Lovelace et al. — Geocomputation with R (open) — spatial methods
- ☐ Harrell — Regression Modeling Strategies notes / Bates lme4 vignette (open) — multilevel

### Infectious Disease & Surveillance  → `ph-background`
- ☐ WHO — Public health surveillance: a tool for targeting and monitoring (standards, open)
- ☐ WHO/CDC — Technical Guidelines for Integrated Disease Surveillance and Response (IDSR), 3rd ed (open)
- ☐ WHO — Managing epidemics: key facts about deadly diseases (open handbook)

### Health Systems & Financing  → `ph-background`  (already 5 docs — round out)
- ☐ WHO — Health systems strengthening glossary / building blocks (open)
- ☐ WHO — Primary health care measurement framework and indicators (open)

### One Health & AMR  → `ph-background`
- ☐ WHO/FAO/WOAH — One Health Joint Plan of Action (open)
- ☐ WHO — GLASS report: global AMR surveillance (latest, open)

---

## NTD LAYER  → `ntd`  (base PH edition)
- ☑ WHO NTD Roadmap 2021–2030 (full + targets summary)
- ☑ WHO Global Report on NTDs 2023
- ☑ WHO World Malaria Report 2023
- ☑ DNDi Sleeping Sickness Factsheet
- ☐ WHO — Ending the neglect: NTD roadmap companion / investment case (open)
- ☐ WHO — Lymphatic filariasis / schistosomiasis / soil-transmitted helminth control guidelines (open)
- ☐ ESPEN (Expanded Special Project for Elimination of NTDs, AFRO) portal reports (open)

## HAT SPECIALIST  → `hat-specialist`  (LOCAL ONLY — never shipped)
- ☑ WHO HAT Treatment Guidelines 2024 + Fexinidazole
- ☑ WHO gHAT Elimination Verification Criteria 2023
- ☑ WHO HAT 5th Stakeholders Meeting 2023
- ☑ WHO HAT TRS-984 Control & Surveillance 2013
- ☐ WHO — gHAT / rHAT technical report series updates (open)
- ☐ DNDi — fexinidazole & acoziborole clinical trial summaries (open)
- ☐ Key HAT review articles mined from reference lists (via mine_references on seed DOIs)

---

## How this gets built (repeatable, runs again in future)
1. For each ☐ item, find the current open-access URL (WHO IRIS, World Bank Open Knowledge, bookdown, CDC).
2. `curl -L` download into the mapped folder under `knowledge/library/open-access-books/<Domain>/`.
3. `build_pdf_knowledge_db(database=<layer>)` — incremental, resumes, per-PDF commit.
4. Items behind IRIS automation blocks → flagged ⚠ for manual browser download.
