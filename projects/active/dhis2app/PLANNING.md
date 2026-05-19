---
project_id: dhis2app
title: DHIS2app — NTD Screening App
domain: software
status: active
priority: high
external_path: C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\DHIS2app
---

# DHIS2app — NTD Screening App

A custom DHIS2-native Android app to replace the current Trypelim/IASO app used for HAT (sleeping sickness) field screening. Designed from the ground up to be multi-NTD, modular, and extensible to post-elimination surveillance.

---

## Origin

- **Current tool**: Trypelim v2.6.2 (25-10-2025), built on Bluesquare's **IASO** platform (Python/Django)
- **APK location**: `C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\TRYPELIM`
- **IASO repo**: github.com/BLSQ/iaso
- **What IASO does well**: séries (session management), CATT/TDR screening forms, NFC smart cards for patient identity, P2P Bluetooth/WiFi Direct sync between devices, ODK forms
- **Gaps in IASO/Trypelim**: no confirmation/treatment on mobile, no post-elimination surveillance mode, no multi-NTD architecture, disease logic compiled into APK (not configurable), result data stored as single `result TEXT` column (no structure per test type)

---

## Architecture decisions (updated 2026-05-07)

### Backend: DHIS2 Tracker — confirmed
- Individual patient records (TEI) + aggregate reporting — both needed
- Core use case: find the same person when the team returns to the same village next year
- TEI search by: last name + mother's name + birth year (+ village as filter)
- No NFC

### Two app versions — decided

**Version 1 — Full team (active screening campaigns)**
- Two tablets, two-person workflow (encoder on Tablet A, tester/verifier on Tablet B)
- P2P sync: Tablet B pushes records to Tablet A (simple one-way push over local WiFi hotspot — NOT CouchDB bidirectional replication)
- USB microscope camera (same hardware as Trypelim)
- Records ALL screened people (needed for longitudinal follow-up)
- Requires a **custom Kotlin app** on DHIS2 Android SDK (DHIS2 Android Capture has no P2P sync or USB camera)
- Latest Android versions

**Version 2 — Lightweight (facility / reduced-team / near-elimination)**
- One tablet
- Records seropositives only
- USB microscope camera (same hardware)
- Potentially DHIS2 Android Capture + companion USB camera app (custom intent)
- Simpler build and deployment

### What is dropped vs. Trypelim (simplifications)
- ~~NFC~~ — dropped; name+mother+birth year is the identifier
- **Village population enumeration** — dropped; no pre-loaded census; enroll on arrival
- **Per-patient GPS** — dropped; village org unit handles mapping
- **Session metadata** — reduced to date + village + logged-in user (no weather, GPS route, device IDs, timestamps per stage, CouchDB revision history)
- **Absence codes** — simplified to one optional field with ≤3 values (not screened / reason)
- **Three-tablet P2P replication** — simplified to two tablets, one-way push from B to A over local hotspot

### Session management: Screening Finished button
- No IASO-style "série" concept (complex, all-or-nothing)
- Each village visit = a screening session with `status = IN_PROGRESS | CLOSED`
- Field team taps **Screening Finished** → session closes → all records become read-only → sync triggered
- Simpler, more reliable, compatible with partial village coverage

### No ODK
- Remove ODK form rendering entirely
- Test inputs use **native Compose UI widgets** mapped by test type (defined in DiseaseProtocol JSON)
- E.g., CATT → titre selector widget; TDR → brand picker + positive/negative; microscopy → parasite density numeric entry

### DiseaseProtocol JSON (core enabler of multi-NTD)
- Server downloads a `DiseaseProtocol` JSON to each device on sync
- Protocol defines: disease name, test types, decision rules (thresholds), widget mappings, referral logic, program stage mapping
- New test types or diseases = update the server config, not the app
- HAT, leprosy, visceral leishmaniasis, lymphatic filariasis, schistosomiasis, yaws all run on the same engine with different protocol files

### Intelligence layer (post-elimination surveillance)
- Separate **FastAPI Python service** (runs server-side or locally)
- Algorithms:
  - Surveillance debt scoring (how long since a zone was screened × population density)
  - Rogan-Gladen seroprevalence estimation with sensitivity/specificity correction
  - SaTScan-style spatial clustering (R integration)
  - Confidence accumulation (Bayesian posterior on absence)
  - Sample size calculation for elimination verification
- Outputs: field team plans, sentinel site priorities, WHO reporting summaries
- Not on mobile — web dashboard only

### Two surfaces
1. **Android app** (Kotlin/Compose + DHIS2 Android SDK) — field and facility data collection
2. **Web surveillance dashboard** (React + DHIS2 App Framework OR standalone FastAPI/React) — intelligence layer, analytics, post-elimination monitoring

---

## Data model

### DHIS2 Tracker setup
- **Tracked Entity Type**: Person
- **TEI attributes**: last name, first name, mother's name, birth year, sex, GPS (home), village, zone, national ID (optional), NFC UID (optional)
- **Program**: NTD Screening (configurable per disease set)
- **Program stages**:
  - Stage 1: Screening (field or facility)
  - Stage 2: Confirmation (RDT, microscopy, LAMP, staging)
  - Stage 3: Treatment
  - Stage 4: Follow-up (3, 6, 12, 24 months)
  - Stage 5: Post-elimination surveillance visit

### Key data model fix vs Trypelim
- Trypelim: `SerieInput.result TEXT` — single text column for all test results
- New: `ScreeningResult.tests JSON` — typed array: `[{type: "CATT", result: "positive", titre: "1/8"}, {type: "TDR", brand: "Abbott", result: "negative"}]`
- This is the foundational change that makes multi-NTD possible

---

## Build order

| Phase | Content | Duration | Priority |
|---|---|---|---|
| 0 | DHIS2 Tracker configuration + metadata import | 2 months | Critical first |
| 1 | Data migration (Trypelim patients → DHIS2 TEIs) | 1 month (parallel) | Critical |
| 2 | Android app — core: session mgmt, patient search, basic screening | 3 months | Critical path |
| 3 | Android app — advanced: multi-disease protocols, camera, offline | 2 months | High |
| 4 | Web dashboard + intelligence service | 2 months (parallel with Phase 3) | High |
| 5 | Field testing DRC | 2 months | Critical |
| 6 | Multi-NTD extension (leprosy, VL, etc.) | 2 months | Medium |

**Total: 9–12 months for full rebuild**
**Alternative: 4–6 months to extend Trypelim** (faster but loses DHIS2 ecosystem)

---

## Team requirements

- **Senior Android developer**: Kotlin/Compose, DHIS2 Android SDK experience
- **Backend developer**: DHIS2 configuration + Python (FastAPI) + React (DHIS2 App Framework)
- **Epidemiologist/domain expert**: HAT workflow, DRC context, NTD protocols

---

## Competitive / strategic context

- Bluesquare (Trypelim/IASO) is a Belgian social enterprise — potential partner rather than competition
- Option: fork IASO and extend (faster) vs. rebuild on DHIS2 (better ecosystem fit)
- WHO uses DHIS2 for the Global HAT Atlas — DHIS2 native integration is free
- ESPEN (WHO AFRO) runs all NTD data on DHIS2 — same ecosystem

---

## What to do before writing code

1. **Talk to Bluesquare** — fork vs. rebuild decision; they may already be planning multi-NTD
2. **Check WHO HAT metadata package** — may cover significant portion of tracker setup
3. **Map current Trypelim data schema** — APK analysis done (see `outputs/reviews/builder/2026-05-07_trypelim-project-intake.md`)
4. **DHIS2 Tracker config prototype** — set up in a test instance first (DHIS2 play.dhis2.org)
5. **DRC PNLTHA stakeholder alignment** — they own the national data; any new system needs their buy-in

---

## Strategy decision (2026-05-07)

Full research + strategy completed. See:
- `outputs/reviews/dhis2-expert/2026-05-07_mobile-data-collection-vertical-programs.md` — 60+ source landscape review
- `outputs/reviews/builder/2026-05-07_dhis2app-strategy.md` — 4-option strategy with data model + implementation plan

**Recommended path: Option B — Hybrid (IASO active screening + DHIS2 passive + ETL bridge)**

Key finding: IASO was built from Trypelim. Its USB microscope, NFC, and P2P sync have no DHIS2 equivalent. Microscopy QC is non-negotiable for HAT confirmation. Full migration to DHIS2 Android Capture only makes sense at elimination when passive detection dominates.

## Open questions (must resolve before build)

- [ ] **HAT Tracker decision**: Does the program need individual-level DHIS2 Tracker (TEI per patient, longitudinal follow-up), or is aggregate reporting in SNIS sufficient? Determines whether a HAT Tracker needs to be added to DRC SNIS.
- [ ] **DRC SNIS access**: Does PNLTHA have access to DRC SNIS, or is a dedicated DHIS2 server needed?
- [ ] **P2P sync mechanism**: How does Version 1 implement tablet-to-tablet sync without a server? Options: local WiFi hotspot, WiFi Direct, or Bluetooth. Needs prototyping.
- [ ] **USB camera integration**: The same USB microscope hardware as Trypelim. For Version 2 this can use Android Capture's custom intent (external app → return image). For Version 1 it needs native USB OTG in the custom SDK app.

## Next steps

- [ ] Answer HAT Tracker question — drives the entire backend data model
- [ ] Set up DHIS2 test instance (Docker) and test Android Capture on an existing tablet
- [ ] Prototype P2P sync approach for Version 1 (local hotspot or WiFi Direct)
- [ ] Survey DRC SNIS / PNLTHA on server access and NTD module status

---

## Key references

- **APK**: `C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\TRYPELIM\iaso-2.6.2-8bffb5069-trypelim-release 25102025.apk`
- **IASO platform**: github.com/BLSQ/iaso
- **DHIS2 Android SDK**: github.com/dhis2/dhis2-android-sdk
- **DHIS2 HAT context**: `knowledge/library/concepts/dhis2/dhis2-overview.md` (NTD/HAT section)
- **Design conversation**: `outputs/reviews/builder/2026-05-07_trypelim-project-intake.md`
