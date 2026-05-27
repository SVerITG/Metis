# Lesson 5 — Data Flow, DHIS2, and the National HAT Atlas

## Learning objectives
By the end of this lesson you will be able to:
- **Trace** the gHAT data pipeline from a village screening register up to DHIS2 and the WHO HAT Atlas.
- **Apply** the core data-quality dimensions (completeness, timeliness, consistency) to a reporting chain.
- **Audit** one health-zone reporting chain and identify where data are lost or delayed.

## Prerequisites
- Lessons 2–3 (where case data are generated: passive facilities and mobile teams).
- Familiarity with the idea of aggregate vs. case-based reporting.

## Content

### Section 1: From a patient to a global database
A confirmed gHAT case generates data at several handoffs, each a chance for loss or delay:

1. **Point of detection** — a passive facility register or a mobile-team screening form records the patient: identifiers, village, test results, stage, treatment.
2. **Health area / health zone aggregation** — facility data are compiled, usually monthly, often still on paper first.
3. **DHIS2 entry** — the DRC uses **DHIS2** as its national health information system. gHAT indicators (cases screened, seropositives, confirmed cases by stage, treatments) are entered against the reporting organisation unit (the health zone or facility) and period.
4. **National programme consolidation** — PNLTHA-RDC reconciles aggregate DHIS2 figures with its own **case-based** line lists, because elimination tracking needs the *location of every case*, not just counts.
5. **WHO HAT Atlas** — national case-based data are submitted to WHO and georeferenced into the HAT Atlas (Franco et al., 2020), the continental database that maps every reported case to its village of probable infection. This is what underpins the "<1 case per 10,000 per year per focus" elimination assessment.

The key tension: **DHIS2 is built for aggregate routine indicators**, but elimination verification needs **case-based, georeferenced** data. A field epidemiologist often works across both — feeding routine DHIS2 dashboards while maintaining the line list that the Atlas and verification require.

> **DRC-grounded example.** In a Kwilu health zone, 4 confirmed cases are treated across three health centres in a quarter. DHIS2 shows "4 confirmed gHAT cases" for the zone. But the verification dossier needs each case geolocated to its village of likely infection — two cases trace to the same riverside hamlet, revealing a micro-focus the aggregate number completely hid.

### Section 2: The three data-quality dimensions that matter most
- **Completeness** — did every facility that should report actually report, and is every detected case in the system? Missing reports look like falling cases — a dangerous illusion near elimination.
- **Timeliness** — did the report arrive in time to act? A case reported four months late cannot trigger a timely reactive screening round.
- **Consistency / accuracy** — do the numbers agree across sources (facility register vs. DHIS2 vs. line list)? Do confirmed cases never exceed seropositives? Do stage counts add up to total cases?

A fourth practical one is **georeferencing quality** — a case with no usable village of origin cannot be placed in the Atlas and weakens the focus-level elimination picture.

### Section 3: Auditing a reporting chain
A reporting-chain audit is a structured walk from the source document to the database, checking each handoff:

1. Pick a period and a health zone.
2. Pull the **source** count (facility registers + mobile-team forms).
3. Pull the **DHIS2** value for the same org unit and period.
4. Pull the **national line list / Atlas** count.
5. Compare. Reconcile every discrepancy: a case in the register but not in DHIS2 (completeness loss), a DHIS2 value entered late (timeliness), a confirmed count exceeding seropositives (impossible — accuracy error), a case with no village (georeferencing gap).

The output is a short reconciliation note: what the true count is, where the leak occurred, and one fix (e.g., a monthly register-to-DHIS2 cross-check by the zone data officer).

### Section 4: Why this is a surveillance issue, not just paperwork
Near elimination, **one missed or mislocated case changes the focus-level rate**. The denominator of the elimination indicator (cases per 10,000 per focus) is small, so a single completeness or georeferencing error can flip a focus from "above threshold" to "below" or vice versa. Data quality *is* surveillance performance in the endgame.

## Summary
- gHAT data flow from village/facility through health-zone aggregation into DHIS2, then into PNLTHA case-based line lists and the WHO HAT Atlas.
- DHIS2 carries aggregate routine indicators; elimination verification needs case-based, georeferenced data — field epidemiologists bridge both.
- Completeness, timeliness, consistency, and georeferencing quality are the data dimensions that decide whether your surveillance numbers can be trusted.
- A reporting-chain audit walks from source document to database, reconciling discrepancies at each handoff.

## Exercises
1. Draw the five-step pipeline from a village screening form to the WHO HAT Atlas and label, at each arrow, one thing that could go wrong.
2. A health zone's facility registers show 7 confirmed cases for Q2, DHIS2 shows 5, and the national line list shows 6. List the checks you would run, in order, to find the true number and the leak point.
3. Explain to a zone data officer why, near elimination, getting the *village of origin* right matters as much as getting the case *count* right.

## Further reading
- Franco JR et al. *Monitoring the elimination of HAT at continental and country level (the HAT Atlas).* PLoS Negl Trop Dis, 2020. doi:10.1371/journal.pntd.0008261.
- WHO TRS 984, 2013 — data management and reporting sections.
- DHIS2 documentation on aggregate vs. tracker (case-based) data models (open access, dhis2.org).
