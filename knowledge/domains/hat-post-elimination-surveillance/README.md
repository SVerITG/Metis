# Layer: hat-post-elimination-surveillance

Permanent searchable knowledge layer on **post-elimination surveillance for human African trypanosomiasis** (gambiense + rhodesiense HAT).

## What this layer covers

The corpus is scoped around the operational and methodological question:
**"Once a country crosses the EPHP threshold, how do you sustain confidence that HAT transmission is not silently re-emerging — and how do you detect resurgence early enough to act?"**

Topic cluster:

1. WHO elimination framework, EPHP criteria, verification dossier process
2. Passive surveillance design and performance after elimination as a public health problem
3. Sentinel-zone hybrid designs (reduced active screening + targeted reactive screening)
4. Diagnostic algorithms in low-prevalence settings (RDT, CATT, trypanolysis, LAMP, mAECT)
5. Healthcare-seeking behaviour and its impact on passive case-detection sensitivity
6. Mathematical modelling of resurgence risk and elimination thresholds
7. Tsetse vector surveillance and Tiny Targets in low-transmission settings
8. Integration of HAT surveillance into DHIS2 and national NTD reporting
9. DRC-specific HAT epidemiology and PNLTHA programmatic evidence
10. Analogue post-elimination NTD surveillance (yaws, onchocerciasis, LF) for cross-pollination

## How to use it

Once indexed, any Metis agent can retrieve from this layer:

```
/background use hat-post-elimination-surveillance
```

Then ask questions like:

- "What sensitivity does passive surveillance achieve once prevalence is below 1/10,000?"
- "Which diagnostic algorithms does WHO recommend for the verification phase?"
- "Are there published sentinel-site designs for HAT post-elimination?"
- "What modelling work exists on healthcare-seeking thresholds for HAT detection?"

The Epidemiologist, Methods Coach, PhD Architect, and Writing Partner will pull chunks from this layer automatically when relevant.

## Folder layout

```
hat-post-elimination-surveillance/
├── layer-meta.yaml      # canonical metadata
├── README.md            # this file
├── manifests/           # source manifests per harvest batch
│   └── 2026-05-26_seed-manifest.md
├── sources/             # raw harvested content (papers, reports, web)
├── scrubbed/            # post-Data-Guardian clean text
├── quarantine/          # Data-Guardian-flagged content, never indexed
├── paywalled.md         # paywalled sources + OA alternatives (created on harvest)
└── failed.md            # fetch failures + reason (created on harvest)
```

## Build status

- **2026-05-26** — Layer scoped. Topic cluster locked. Seed manifest written. Awaiting Content Harvester pass to populate `sources/` and index into the vector store.

## Extend later

```
/background extend hat-post-elimination-surveillance --topic "<new topic>"
```

Suggested extensions once survey is indexed: aat-tsetse-ecology, hat-treatment-fexinidazole-acoziborole, ntd-elimination-verification-process.
