# Passive Screening DRC — Project Planning

**Project ID:** passive-screening-drc  
**Full name:** Intégration du dépistage passif de la THA dans le système de santé des provinces endémiques de la RDC  
**Short name:** Dépistage Passif (DP) / Passive HAT Screening  
**Status:** Active — Phase 2 (2024–2026)  
**Role:** Technical and financial support (IMT/ITG), follow-up of operational activities, data analysis, strategic revision, donor reporting, workshop organisation  
**Funded by:** DGD (Belgian government), FABAC  
**Lead partner:** PNLTHA (Programme National de Lutte contre la THA)  
**Other partners:** INRB (national reference lab + KPS production), DPS Kasaï Oriental/Lomami/Sankuru, DNDi, FIND, OMS/WHO  
**Basket documents:** `metis/basket/` — Ateliers 2023/2025/2026, Presentations (DGD/FABAC/partners), Strategy documents 2024–2026

---

## What this project is

A programme to integrate passive HAT (Human African Trypanosomiasis / sleeping sickness) screening into existing health structures in endemic provinces of DRC. Instead of relying only on active mass-screening campaigns, the project trains health workers in fixed structures to recognise, test, and treat HAT patients who present spontaneously.

This is a major strategic shift in the fight against HAT as the disease moves towards elimination: active campaigns become less efficient as disease prevalence falls, and passive detection becomes the primary remaining mechanism for finding cases.

---

## Project phases

| Phase | Period | Coverage | Structures |
|---|---|---|---|
| Phase initiale | 2019–2022 | All endemic ZS in endemic provinces | Limited results → reconsidered |
| Phase pilote | Aug 2022 – Mar 2023 | 3 provinces (Kasaï Oriental, Lomami, Sankuru) | 23 structures designed |
| Phase 1 | Mar 2023 – 2024 | KOR (Kasaï Oriental + Lomami) + Sankuru | 23 functional: 11A + 2B+ + 10B |
| **Phase 2** | **2024–2026** | **3 coordinations, 5 provinces** | **Rationalised — fewer A, more B** |
| Phase 3 (planned) | Post-2026 | 4 coordinations, 7 provinces (+ Manïema/Tanganyika) | Security concerns in new zone |

---

## Health structure types

| Type | Endémicité threshold | Diagnostic package |
|---|---|---|
| **Structure A** | ≥ 20 HAT cases / last 5 years | Serology + KPS + microscopy (mAECT) + PCR/TL confirmation + staging (CSF) + treatment. Lab equipment + electrification + digitalisation + QA. |
| **Structure B+** | Intermediate | Serology + KPS + parasitology (no full lab equipment investment) |
| **Structure B** | < 20 cases / last 5 years | Serology + KPS + transfer to A for urgent confirmation + treatment. Digitalisation + QA. |

**Key technology — KPS (Kit Prélèvement de Sang):** DBS-like blood collection kit. Produced by INRB in DRC. No cold chain required. Sent to INRB for Trypanolyse (TL) and qPCR. Circuit: supply chain → collection at structure → shipping to INRB → lab analysis → results back to structure.

---

## Diagnostic algorithm

1. Patient presents with signs/symptoms compatible with HAT + history of stay in endemic zone
2. Serology: CATT or TDR (rapid diagnostic test)
3. If seropositive: KPS blood sample collected and sent to INRB
4. INRB performs: Trypanolyse (TL) + qPCR ± TL
5. If TL/PCR positive → Structure A: microscopy (mAECT), staging (CSF), treatment
6. Structure B: refer urgent cases to nearest Structure A

**Reactive screening:** Additional component — when a case is found, active follow-up in the patient's origin village.

---

## Geographic coverage (coordinations)

| Code | Provinces | Notes |
|---|---|---|
| KOR | Kasaï Oriental + Lomami | Combined coordination; most cases (36 in Phase 1) |
| SNK | Sankuru | 3 cases in Phase 1; separate coordination |
| KOCC | Kongo Central + ? | Phase 2 expansion |
| TG | Tanganyika (+ Manïema) | Phase 3 planned; security concerns |

---

## Key operational challenges

1. **Delay of results** — KPS shipped to INRB → long turnaround → patients lost to follow-up before results return. Health system delay being tracked in 2026 review.
2. **Test discordance** — iELISA ≠ confirmed (42 positives → 20 discordant); Trypanolyse (21 positives → 9 discordant); qPCR (4 → 1 discordant); parasitology 0 discordant → most reliable but requires expertise and equipment.
3. **Lost to follow-up and deaths** — patients seropositive but not returning for confirmation result; some die before treatment.
4. **Staff permutation** — trained staff rotate to other positions; continuous retraining needed.
5. **Sustainability of technical expertise** — microscopy expertise concentrated in few A structures.
6. **Structure A vs B value-added** — 86% of confirmed cases identified by post-hoc KPS rather than ad hoc microscopy → limited added value of A structures; Phase 2 rationalising.
7. **Costs** — ~USD 20,000 per structure for start-up; ~USD 100,000/year operational for 10 structures.
8. **Quality assurance** — systematic QA introduced via photos, videos, field supervisors.

---

## Financial structure

- **Start-up cost:** USD 75,000–150,000 per coordination
- **Operational cost:** ~USD 100,000/year for ~10 structures
- **Structure A investment:** ~USD 20,000/structure (lab equipment, electrification)
- **Primes/forfaits:** Payments to health workers for passive screening activities — key sustainability mechanism; mobile money used in some areas
- **Funding period:** Phase 2 funded 2024–2026 by DGD (Belgian development agency) + FABAC

---

## Partners and their roles

| Partner | Role |
|---|---|
| **ITG/IMT** | Technical + financial support, data analysis, strategic revision, donor reporting |
| **PNLTHA** | National strategy, field implementation, supervision |
| **INRB** | National reference lab — KPS production, TL/PCR analysis, WHO collaborating centre |
| **DPS** (×3 provinces) | Provincial health coordination |
| **DGD** | Primary funder (Belgian government) |
| **FABAC** | Secondary funder |
| **DNDi** | Partner on diagnostics and treatment |
| **FIND** | Diagnostics partner |
| **OMS/WHO** | Guidelines, integrated passive surveillance procedures |
| **PDSS/World Bank** | Health structure rehabilitation |

---

## Annual review cycle

Annual atelier (workshop) held in Kinshasa, bringing together all partners:
- **Atelier 2023 (Nov 15–17, 2023):** Strategic evaluation; preliminary results; working groups on lab/finances/project management/data circuit; formulation of Phase 2 strategy.
- **Revue 2025 (May 13, 2025):** Annual review at St Pierre Claver; evaluation per coordination; costs 2024; quality assurance; future discussion.
- **Revue 2026 (May 7–8, 2026):** Reactive screening, delays, LFU/deaths, health system delay, staff permutation, QA.

---

## Data and outputs

- **PS_Cases_All_CSV:** Master dataset of all passive screening cases (in basket — handle as potentially identifiable data if contains patient identifiers)
- **Monthly reports by FOSA:** Per health structure monthly reporting (RAPPORT MENSUEL FOSA)
- **Results databases per coordination:** Excel files per coordination (KOR, SNK, KOCC)
- **KPS results:** RESULTATS_KPS files — serological tracking
- **Annual review presentations:** PPTX per coordination + thematic topics

---

## Open questions and next steps

- **Phase 3 timeline and security:** Manïema/Tanganyika expansion contingent on security situation
- **Simplification scenario:** Can Structure B be the only type? Use mobile diagnostic team for urgent confirmation?
- **Data system transition:** Moving from Trypelim (IASO) to a DHIS2-based system — see `projects/active/dhis2app/`
- **Scale-up to national level:** Integration with SNIS reporting; coordination with other vertical programs
- **KPS result delay reduction:** Options to speed up the circuit (satellite lab in coordination vs central INRB)
- **Staff training sustainability:** Distance training options for staff turnover

---

## Cross-project connections

- **DHIS2app** — the new mobile data collection system being designed to replace Trypelim for passive screening data entry
- **HAT Dashboard** — epidemiological data visualisation includes passive screening data
- **PhD framework** — passive screening data and operational research are part of the PhD scope
- **HAT Clustering** — spatial analysis of HAT cases, including passive screening catchment areas
