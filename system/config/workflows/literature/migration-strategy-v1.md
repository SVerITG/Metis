# Literature Migration Strategy V1

## What I found

Your current HAT literature library already has strong topical structure.

Top-level folders include:

- Burden
- Clinical and Treatment
- Community
- Determinants and risks
- Diagnostics
- Elimination
- Epidemiology
- Health Economics
- History
- Integration
- Methodology
- Multi-NTD
- Overview
- PNLTHA
- Screening and Surveillance
- Statistics and Mathematical Modelling
- Vector and Vector Control
- WHO Atlas

There are currently 221 files.

The largest sections are:

- Diagnostics: 49
- Screening and Surveillance: 32
- Statistics and Mathematical Modelling: 26
- Epidemiology: 17
- Methodology: 17
- Clinical and Treatment: 15
- WHO Atlas: 15

## Recommendation

Do not throw away the current topical structure.

Instead:

1. Keep it as the `topic shelf`.
2. Add a metadata layer on top of it.
3. Add a project and article linking layer above that.

## Proposed future model

### Storage layer

Keep local copies of all source files.

### Browsing layer

Preserve familiar topic folders because they are already meaningful to you.

### Knowledge layer

Add metadata records for each paper, with links to:

- topic
- disease
- geography
- method
- surveillance mode
- elimination phase
- projects
- PhD article relevance

### Action layer

Let the Librarian identify:

- what is new
- what is missing
- what is duplicated
- what is outdated
- what is highly relevant to the current papers

## Migration steps

1. Inventory the current library.
2. Detect duplicates, broken names, and non-paper files.
3. Map each file to ontology fields.
4. Link papers to your current PhD articles.
5. Add a `new since last scan` mechanism.
6. Only then decide whether physical folder renaming is worth it.

## Likely recent additions to check

These appear likely to matter and may not yet be in your folder:

- 2025 Lancet review on human African trypanosomiasis
- 2025 STROGHAT protocol paper
- 2025 passive surveillance paper in DRC on clinical presentation and diagnostic/reference test accuracy
- 2025 prospective evaluation of second-generation rapid diagnostic tests
- 2025 community participation paper for screen-and-treat with acoziborole
- 2024 modelling paper on elimination timelines in DRC with cryptic human and animal transmission

These should be validated during the first real library scan.
