# Seed manifest — 2026-05-26

Initial source-discovery plan for the `hat-post-elimination-surveillance` layer. This is the **scope and seed-query manifest** the Content Harvester + Librarian will execute. It is not yet a fetched corpus.

**Depth:** survey (target 50–100 indexed docs)

## Seed queries by topic

### 1. WHO elimination framework & verification
- PubMed: `("African trypanosomiasis" OR "sleeping sickness") AND ("elimination" OR "EPHP" OR "verification") AND ("WHO" OR "World Health Organization")`
- WHO site: `site:who.int "human African trypanosomiasis" elimination verification`
- WER (Weekly Epidemiological Record): HAT progress reports 2018–2026
- Expected: ~10 docs (WHO road-map, technical reports, validation criteria)

### 2. Passive surveillance design & performance post-elimination
- PubMed: `("passive surveillance" OR "case detection") AND ("African trypanosomiasis" OR "sleeping sickness") AND (sensitivity OR performance OR coverage)`
- Authors to seed-track: Lutumba P, Mitashi P, Boelaert M, Büscher P, Bessell PR, Snijders R, Hasker E, Mpanya A
- Expected: ~15 docs

### 3. Sentinel & hybrid surveillance designs
- PubMed: `("sentinel" OR "reactive screening" OR "targeted screening") AND ("African trypanosomiasis" OR "sleeping sickness")`
- Cross-disease analogue: `("sentinel surveillance" AND "post-elimination") AND (yaws OR onchocerciasis OR "lymphatic filariasis")`
- Expected: ~8 docs

### 4. Diagnostic algorithms (RDT, CATT, trypanolysis, LAMP, mAECT)
- PubMed: `("rapid diagnostic test" OR CATT OR trypanolysis OR LAMP OR mAECT) AND ("African trypanosomiasis" OR "sleeping sickness")`
- FIND technical reports, DNDi diagnostic pipeline notes
- Expected: ~12 docs

### 5. Healthcare-seeking behaviour & detection sensitivity
- PubMed: `("health seeking" OR "care seeking" OR "treatment seeking") AND ("African trypanosomiasis" OR "sleeping sickness" OR "neglected tropical")`
- Expected: ~5 docs

### 6. Mathematical modelling of resurgence
- PubMed: `("mathematical model" OR "transmission model" OR "compartmental") AND ("African trypanosomiasis" OR "sleeping sickness")`
- HAT-MEPP consortium outputs; Rock KS, Castaño S, Crump RE, Aliee M
- Expected: ~10 docs

### 7. Tsetse vector surveillance & Tiny Targets
- PubMed: `("Glossina" OR "tsetse") AND ("surveillance" OR "Tiny Targets" OR "vector control")`
- Authors: Tirados I, Esterhuizen J, Lehane MJ, Solano P
- Expected: ~8 docs

### 8. DHIS2 / national NTD reporting integration
- Google Scholar: `"DHIS2" AND ("neglected tropical" OR "HAT" OR "African trypanosomiasis")`
- DHIS2 community docs and University of Oslo HISP materials
- Expected: ~5 docs

### 9. DRC-specific HAT epidemiology & PNLTHA
- PubMed: `("Democratic Republic of Congo" OR DRC OR "DR Congo") AND ("African trypanosomiasis" OR "sleeping sickness")` filtered 2018–2026
- PNLTHA-DRC programme reports (FR + EN)
- Expected: ~15 docs

### 10. Cross-pollination — other NTD post-elimination surveillance
- PubMed: `("post-elimination" OR "post-validation") AND (surveillance) AND (NTD OR "neglected tropical")`
- Yaws verification (Asiedu, Mitja), onchocerciasis verification (Lakwo, Sauerbrey), LF (Ottesen)
- Expected: ~8 docs (analogue methods, not core)

**Total expected pre-dedup:** ~96 sources → ~70–85 after dedup and paywall filtering.

## Source-type targets

| Type | Target count |
|---|---|
| Peer-reviewed papers | 55–70 |
| WHO / agency reports | 10–15 |
| Programmatic / PNLTHA reports | 5–8 |
| Web pages / guidelines | 5–10 |
| **Total indexed (post-scrub)** | **~75–90** |

## Safety preconditions

- Data Guardian `check_patient_data_exposure` runs on every fetched doc before indexing.
- Any PNLTHA programmatic data containing line-lists, GPS coordinates of patients, or named villages with case counts → quarantined to `quarantine/`, never indexed.
- Cybersecurity `injection_probe` runs on every web-sourced doc to flag adversarial content.

## Next step

Hand this manifest to the Content Harvester:

```
/content-harvester run-manifest knowledge/domains/hat-post-elimination-surveillance/manifests/2026-05-26_seed-manifest.md
```

Harvester returns to Background Maker with `sources/`, `scrubbed/`, `quarantine/` populated and a fetch report. Background Maker then calls the MCP index tools and updates `layer-meta.yaml` with `doc_count` and `chunk_count`.
