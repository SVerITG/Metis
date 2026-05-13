---
title: "DHIS2 — District Health Information Software 2"
domain: "concepts"
tags:
  - DHIS2
  - HMIS
  - health-information-systems
  - surveillance
  - data-collection
  - NTD
  - implementation
agent: dhis2-expert
updated: "2026-05-07"
---

# DHIS2 — District Health Information Software 2

> Reference card for the DHIS2 platform. Use `/dhis2-expert` for configuration, development, or implementation questions.

---

## What DHIS2 is

- Open-source health management information system (HMIS) developed by HISP (Health Information Systems Programme), University of Oslo.
- Used in 100+ countries as national HMIS, disease surveillance platform, and logistics system.
- Three data models: **aggregate** (routine facility reports), **tracker** (individual-level longitudinal), **event** (anonymous events).
- Web-based, mobile-capable (Android app), API-first.
- Current stable: 2.41.x (2026). Long-term support: 2.38, 2.39, 2.40.

---

## Architecture

```
Browser / Android App
       ↓
   DHIS2 Web App (Java/Spring, runs in Tomcat)
       ↓
   PostgreSQL (primary data store)
       ↓ (optional)
   Redis (caching) + Elasticsearch (full-text)
```

- Standard deployment: Ubuntu 22.04 + nginx reverse proxy + Tomcat 9 + PostgreSQL 14+
- Docker deployment: dhis2/core image, `dhis2-docker-compose` (official)
- Cloud: supported on AWS, GCP, Azure; managed hosting via Baosystems, HISP partners

---

## Data model

### Aggregate
- **Organisation Unit (OU):** geographic/administrative hierarchy (national → district → facility)
- **Data Element:** what is measured (e.g., "HAT cases confirmed by RDT")
- **Category Combo:** disaggregations (age, sex, stage)
- **Dataset:** collection of data elements + reporting period + OU assignment
- **Indicator:** calculated from data elements (rates, ratios, coverage)

### Tracker
- **Tracked Entity Type (TET):** what is tracked (usually "Person")
- **Tracked Entity Instance (TEI):** individual record
- **Program:** defines the workflow (enrollment attributes + stages)
- **Program Stage:** event within a program (e.g., screening, diagnosis, treatment)
- **Data Element:** collected at each stage

### Event (anonymous tracker)
- Like tracker but no TEI — used for anonymous events (e.g., service counts, commodity distribution)

---

## Key modules

| Module | Purpose |
|---|---|
| Data Entry | Aggregate forms, custom HTML forms |
| Tracker Capture | Individual case tracking (web) |
| Capture (new) | Replacement for Tracker Capture (React) |
| Analytics / Data Visualiser | Charts, pivot tables, maps |
| Dashboard | Composable views of visualisations |
| Maps | GIS layer visualisation (OpenLayers) |
| Event Reports | Tabular/chart views of event/tracker data |
| Maintenance | Metadata management |
| Import/Export | Bulk metadata and data operations |
| User Management | Roles, sharing, access control |
| Android Settings App | Configure Android data collection |

---

## Web API

Base URL: `https://[server]/api/[endpoint]`

Key endpoints:
- `/api/dataElements` — list/create data elements
- `/api/programs` — tracker programs
- `/api/trackedEntityInstances` — individual records (deprecated in v40+, use `/api/tracker`)
- `/api/tracker` — new unified tracker API (v37+, recommended from v40)
- `/api/analytics` — aggregate analytics queries
- `/api/events` — event data
- `/api/dataValueSets` — bulk aggregate data import/export
- `/api/metadata` — full metadata import/export (JSON/XML/CSV)

Authentication: Basic auth (dev only), API tokens (recommended), OAuth2.

---

## NTD / HAT implementations

### WHO NTDS (Global)
- WHO uses DHIS2 for the Global HAT Atlas and NTD reporting
- Data: annual case reports by country, disaggregated by form (gHAT/rHAT), stage, sex, age
- Contact: WHO NTD Data Portal

### DRC — PNLTHA
- National HAT control programme uses DHIS2 for case-based surveillance
- Tracker program: TEI = HAT patient; stages = screening → confirmation → treatment → follow-up
- Integrates with ESPEN for NTD co-endemic data

### ESPEN (Expanded Special Project for Elimination of NTDs)
- WHO AFRO-hosted DHIS2 instance for NTD data across sub-Saharan Africa
- Covers: HAT, lymphatic filariasis, onchocerciasis, schistosomiasis, STH, trachoma, leprosy
- URL: espen.who.int

### ITG / Institute of Tropical Medicine (Antwerp)
- HAT dashboard integrates with DHIS2 API for case data retrieval
- Custom R/Python scripts for data extraction and epidemiological analysis

---

## DHIS2 Academy & Training

| Track | Content | Level |
|---|---|---|
| Fundamentals | Platform overview, navigation | Beginner |
| Aggregate Customisation | Dataset design, indicators, dashboards | Intermediate |
| Tracker Customisation | Program design, program rules | Intermediate |
| Android Customisation | Android Settings App, offline sync | Intermediate |
| Analytics & Dashboards | Visualiser, maps, event analytics | Intermediate |
| App Development | DHIS2 App Framework, React, d2 | Advanced |
| System Administration | Installation, upgrades, performance | Advanced |

All courses free at: academy.dhis2.org

---

## Key documentation locations

| Doc | URL |
|---|---|
| User guide | docs.dhis2.org/en/use/ |
| Implementation guide | docs.dhis2.org/en/implement/ |
| Developer guide | docs.dhis2.org/en/develop/ |
| Android guide | docs.dhis2.org/en/implement/android/ |
| API reference | docs.dhis2.org/en/develop/using-the-api/ |
| Release notes | github.com/dhis2/dhis2-releases |
| Community forum | community.dhis2.org |
| App Hub | apps.dhis2.org |

---

## Integration patterns

| Pattern | Use case |
|---|---|
| DHIS2 → R/Python via API | Data extraction for epidemiological analysis |
| ODK/KoBoToolbox → DHIS2 | Field data collection → national HMIS |
| DHIS2 → HL7 FHIR | Interoperability with clinical systems |
| DHIS2 → ADX | WHO/PEPFAR aggregate data exchange |
| OpenMRS → DHIS2 | Patient records → population-level reporting |
| DHIS2 → LMIS | Health commodity reporting |
