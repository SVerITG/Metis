---
title: "Outbreak Investigation"
domain: "methods"
tags:
  - outbreak
  - investigation
  - response
  - case-finding
  - contact-tracing
related:
  - "methods/surveillance-systems.md"
  - "methods/study-designs.md"
  - "disease-areas/hat-sleeping-sickness.md"
phd_relevance: "medium"
status: "current"
updated: "2026-03-30"
---
# Outbreak Investigation

> Reference card — systematic framework for investigating disease outbreaks in the field and from the desk.

---

## CDC 10-Step Framework

1. **Prepare for fieldwork** — assemble team, supplies, communications plan
2. **Verify the diagnosis** — confirm cases with lab/clinical criteria
3. **Establish the existence of an outbreak** — compare observed vs expected cases (baseline data)
4. **Define and identify cases** — develop a case definition (suspected, probable, confirmed)
5. **Describe the outbreak** — time (epidemic curve), place (spot map), person (demographics)
6. **Develop hypotheses** — based on descriptive epi, clinical features, known pathogen ecology
7. **Evaluate hypotheses** — analytic epidemiology (cohort or case-control study)
8. **Refine hypotheses and conduct further studies** — if initial analysis inconclusive
9. **Implement control and prevention measures** — may begin at any step
10. **Communicate findings** — report to authorities, publish, debrief

## Epidemic Curves

- **Point source:** Rapid rise and fall; cases cluster within one incubation period
- **Continuous (common) source:** Prolonged exposure; plateau shape
- **Propagated (person-to-person):** Successive waves separated by incubation period intervals
- **Mixed:** Combination of patterns (e.g., common source triggering secondary transmission)
- Epi curve shape helps infer source type and estimate exposure period (back-calculate from incubation)

## Attack Rates and Case Fatality

- **Attack rate (AR):** Number of cases / population at risk during the outbreak period
- **Food-specific attack rate:** AR among those exposed vs unexposed to each food item
- **Secondary attack rate:** Cases among contacts / total contacts (excludes primary cases)
- **Case fatality rate (CFR):** Deaths / total cases; measure of severity, not risk

## 2x2 Tables and Relative Risk

- Exposed: a (ill), b (well); Unexposed: c (ill), d (well)
- **Relative risk (RR):** [a/(a+b)] / [c/(c+d)] — used in cohort/outbreak studies
- **Odds ratio (OR):** (a*d) / (b*c) — used in case-control studies
- **Attributable risk:** AR_exposed - AR_unexposed
- Chi-square or Fisher's exact test for significance

## Line Listing

- Spreadsheet with one row per case: ID, demographics, onset date, symptoms, exposures, lab results, outcome
- Essential for real-time case tracking and descriptive analysis
- Should be started immediately and updated continuously
- Include geographic coordinates when possible for mapping

## Rapid Risk Assessment

- **WHO approach:** Hazard assessment, exposure assessment, context assessment -> risk characterization
- **ECDC framework:** Similar structure with explicit likelihood and impact scoring
- Used for early decision-making before full investigation is complete
- Output: risk level (low/moderate/high/very high) with recommended actions

## Field vs Desk-Based Investigation

- **Field investigation:** Direct data collection, specimen collection, environmental assessment; resource-intensive but essential for novel outbreaks
- **Desk-based analysis:** Uses routine surveillance data, lab records, existing databases; faster, suitable for recognized pathogens with good existing data
- Most real investigations combine both approaches

## Current Developments (2025-2026)

- **CDC's field guidance has been refreshed:** CDC's online **Field Epidemiology Manual** was updated in **2024-2025**, including current chapters on conducting field investigations and communicating during investigations.
- **Outbreak work is increasingly digital and multidisciplinary:** Current manuals put more weight on rapid data flows, cross-border coordination, risk communication, and the use of newer data sources alongside classic line lists and interviews.
- **Collaborative surveillance is expanding institutionally:** ECDC and Africa CDC both highlighted integrated surveillance and preparedness initiatives in 2025, which means outbreak investigation is more tightly linked to ongoing surveillance infrastructure than before.
- **Practical implication:** The classic 10-step framework still holds, but the strongest current practice treats communication, data management, and control measures as parallel activities rather than end-stage add-ons.

## Practical Examples

- **Food-borne outbreak investigations:** Cohort or case-control studies using 2x2 tables remain the clearest examples of how analytic epidemiology can identify a specific vehicle quickly.
- **Mpox and other cross-border events:** Recent multinational responses have shown the importance of combining field teams, rapid risk assessment, and coordinated data management across jurisdictions.
- **Disease cluster follow-up in elimination settings:** In elimination programmes, a suspected cluster may require desk-based surveillance review, facility verification, and targeted field assessment rather than a large classical outbreak deployment.
- **Healthcare-associated outbreaks:** Modern field investigations often rely on patient movement data, laboratory confirmation, and repeated communication with facilities while control measures are already being implemented.

## Key References

- CDC (2018). *Principles of Epidemiology in Public Health Practice*. 3rd ed. (Self-study course SS1978).
- Gregg, M. B. (2008). *Field Epidemiology*. 3rd ed. Oxford University Press.
- Goodman, R. A. et al. (2014). *A Practical Guide to Field Epidemiology*. Oxford University Press.
- WHO (2017). *Rapid Risk Assessment of Acute Public Health Events*. WHO/HSE/GCR/LYO/2012.4.
- Reingold, A. L. (1998). Outbreak investigations: a perspective. *Emerg Infect Dis*, 4(1), 21-27.
- **CDC Field Epidemiology Manual overview:** https://www.cdc.gov/field-epi-manual/php/about/index.html
- **CDC manual chapter, Conducting a Field Investigation (6 January 2025):** https://www.cdc.gov/field-epi-manual/php/chapters/field-investigation.html
- **CDC manual chapter, Communicating During an Outbreak or Public Health Investigation:** https://www.cdc.gov/field-epi-manual/php/chapters/communicating-investigation.html
- **WHO rapid risk assessment guidance:** https://www.who.int/publications/i/item/9789241510141

## Learning Path

- Start with `knowledge/library/courses/epidemiology-foundations/lessons/12-outbreak-investigation.md`.
- Pair this card with `knowledge/library/methods/surveillance-systems.md` because outbreak investigations almost always depend on existing indicator-based and event-based detection systems.
- Review `knowledge/library/methods/diagnostic-test-evaluation.md` when confirmation testing and case classification are uncertain.
- In the Learning Hub, this card aligns primarily with **Outbreak investigation** and also supports **Surveillance systems** and **Scientific communication**.

---

*Last updated: 2026-03-30 | Enriched with current CDC field-manual and integrated-surveillance context*
