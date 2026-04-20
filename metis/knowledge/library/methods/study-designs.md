# Study Designs in Epidemiology

> Reference card — core study designs, when to use, strengths, limitations, key biases.

---

## Observational Studies

### Cohort Study
- **Design:** Follow exposed and unexposed groups over time; measure incidence of outcome
- **When to use:** Etiology of disease, natural history, multiple outcomes from single exposure
- **Measure:** Incidence rate, risk ratio (RR), hazard ratio (HR)
- **Strengths:** Temporal sequence established; can estimate incidence; multiple outcomes
- **Limitations:** Expensive, time-consuming (prospective); loss to follow-up; rare outcomes impractical
- **Key biases:** Selection bias, loss to follow-up (attrition), information bias, healthy worker effect
- **Variants:** Prospective, retrospective (historical), ambidirectional, birth cohort

### Case-Control Study
- **Design:** Select cases (diseased) and controls (non-diseased); compare past exposures
- **When to use:** Rare diseases, outbreak investigations, multiple exposures for one outcome
- **Measure:** Odds ratio (OR) — approximates RR when disease is rare
- **Strengths:** Efficient for rare diseases; relatively quick and inexpensive; good for outbreaks
- **Limitations:** Cannot estimate incidence; temporal sequence may be unclear; control selection critical
- **Key biases:** Recall bias, selection bias (Berkson's bias), interviewer bias
- **Variants:** Nested case-control, case-cohort, case-crossover, matched case-control

### Cross-Sectional Study
- **Design:** Measure exposure and outcome simultaneously in a defined population at one time point
- **When to use:** Prevalence estimation, health surveys, hypothesis generation, programme planning
- **Measure:** Prevalence, prevalence ratio, prevalence odds ratio
- **Strengths:** Quick, inexpensive; snapshot of population burden; useful for planning
- **Limitations:** No temporal sequence (chicken-or-egg); prevalence bias (overrepresents long-duration disease)
- **Key biases:** Prevalence-incidence bias (Neyman bias), non-response bias, recall bias

### Ecological Study
- **Design:** Analyze data at group/population level (not individual)
- **When to use:** Hypothesis generation, policy evaluation, when individual data unavailable
- **Measure:** Correlation between group-level exposure and outcome rates
- **Strengths:** Uses routinely available data; inexpensive; can examine population-level exposures
- **Limitations:** Ecological fallacy (cannot infer individual-level associations); confounding hard to control
- **Key biases:** Ecological fallacy, aggregation bias, migration across groups

---

## Experimental Studies

### Randomized Controlled Trial (RCT)
- **Design:** Random allocation of participants to intervention vs control; follow for outcome
- **When to use:** Evaluating treatment efficacy, preventive interventions
- **Measure:** RR, risk difference, NNT, HR
- **Strengths:** Gold standard for causation; randomization controls confounding; blinding reduces bias
- **Limitations:** Expensive; ethical constraints; may lack generalizability (efficacy vs effectiveness)
- **Key biases:** Non-compliance, contamination, Hawthorne effect, attrition
- **Variants:** Parallel, crossover, factorial, non-inferiority, equivalence

### Cluster-Randomized Trial
- **Design:** Randomize groups (villages, clinics, schools) rather than individuals
- **When to use:** Interventions delivered at group level; when individual randomization impractical or risks contamination
- **Strengths:** Reduces contamination; pragmatic; suits public health interventions
- **Limitations:** Requires more participants (design effect/ICC); complex analysis; fewer clusters = less power
- **Key considerations:** Intraclass correlation coefficient (ICC), design effect, restricted randomization

### Stepped-Wedge Trial
- **Design:** All clusters receive intervention eventually; clusters cross from control to intervention at random timepoints
- **When to use:** When withholding intervention is unethical; phased rollout; limited resources
- **Strengths:** All clusters get intervention; logistically feasible for rollouts; within-cluster comparisons
- **Limitations:** Requires strong secular trend assumptions; longer duration; complex analysis; time confounding
- **Key considerations:** Period effects, transition periods, incomplete designs

---

## Surveillance Designs

### Passive Surveillance
- **Design:** Health facilities report cases through routine notification systems
- **When to use:** Routine disease monitoring; notifiable diseases
- **Strengths:** Low cost; sustainable; broad geographic coverage
- **Limitations:** Underreporting; delayed detection; variable data quality

### Active Surveillance
- **Design:** Regular outreach to identify cases (house-to-house, facility visits, mobile teams)
- **When to use:** Elimination programmes (HAT, polio); outbreak response; high-priority diseases
- **Strengths:** More complete case finding; higher sensitivity
- **Limitations:** Expensive; resource-intensive; not sustainable long-term at scale

### Sentinel Surveillance
- **Design:** Selected sites report systematically on defined conditions
- **When to use:** Monitoring trends; antimicrobial resistance; influenza-like illness
- **Strengths:** Higher data quality; standardized protocols; cost-effective for trend monitoring
- **Limitations:** Not representative of full population; site selection bias

### Event-Based Surveillance (EBS)
- **Design:** Systematic collection and rapid assessment of unstructured reports (media, rumours, community alerts)
- **When to use:** Early warning; emerging threats; complement to indicator-based surveillance
- **Strengths:** Early signal detection; captures events outside routine system
- **Limitations:** High noise/signal ratio; needs verification (triage); resource for follow-up

### Syndromic Surveillance
- **Design:** Monitor pre-diagnostic data (symptom patterns, chief complaints) for early signal detection
- **When to use:** Bioterrorism preparedness; mass gatherings; early outbreak detection
- **Strengths:** Timeliness; uses existing data (ED visits, pharmacy sales)
- **Limitations:** Low specificity; high false-positive rate; limited for rare diseases

---

## Quick Selection Guide

| Question | Preferred Design |
|----------|-----------------|
| Does this treatment work? | RCT |
| What causes this rare disease? | Case-control |
| What is the disease burden? | Cross-sectional survey |
| Does exposure X lead to outcome Y over time? | Cohort |
| Is this intervention working in the real world? | Stepped-wedge or cluster-randomized |
| Are cases increasing? | Surveillance (passive + sentinel) |
| Is something unusual happening? | Event-based surveillance |

---

## Current Developments (2025-2026)

- **Target trial emulation is now part of design reporting:** The **TARGET statement was published on 3 September 2025 in BMJ**, which matters for observational studies trying to approximate causal trial logic.
- **Estimands are shaping design language:** The BMJ primer on the **ICH E9(R1) estimands framework** continues to push researchers to define the exact effect question before analysis choices are locked in.
- **Design quality is increasingly judged structurally:** Eligibility, time zero, intervention strategies, follow-up, outcome definitions, and missing-data handling are now more explicitly expected parts of design reporting.

## Practical Examples

- **Cohort versus target-trial framing:** A routine-data cohort evaluating an intervention can become much stronger when re-specified as an emulated trial with explicit eligibility and time zero.
- **Cluster and stepped-wedge trials in public health:** These remain practical designs for screening models, facility workflows, and district-level service changes.
- **Event-based surveillance as a design problem:** Surveillance systems are not only operational tools; they are designs with clear trade-offs in sensitivity, timeliness, and verification burden.

## Key References

- **Rothman KJ, Greenland S, Lash TL.** *Modern Epidemiology.* 4th ed. Wolters Kluwer, 2021.
- **Gordis L.** *Epidemiology.* 6th ed. Elsevier, 2019.
- **Szklo M, Nieto FJ.** *Epidemiology: Beyond the Basics.* 4th ed. Jones & Bartlett, 2019.
- **Porta M (ed).** *A Dictionary of Epidemiology.* 6th ed. Oxford, 2014.
- **WHO.** *Communicable Disease Surveillance and Response Systems: Guide to Monitoring and Evaluating.* WHO/CDS, 2006.
- **Hemming K et al.** The stepped wedge cluster randomised trial: rationale, design, analysis, and reporting. *BMJ.* 2015;350:h391.
- **TARGET statement:** https://www.bmj.com/content/390/bmj-2025-087179
- **BMJ estimands primer:** https://www.bmj.com/content/384/bmj-2023-076316
- **STROBE statement:** https://www.strobe-statement.org/
- **CONSORT statement:** https://www.consort-statement.org/

## Learning Path

- Start with `06_library/courses/epidemiology-foundations/`.
- Pair this card with `06_library/methods/causal-inference.md` for design assumptions and with `06_library/methods/biostatistics-essentials.md` for effect measures and models.
- Use `06_library/courses/research-writing/` when turning design choices into protocols and manuscripts.
- In the Learning Hub, this card aligns primarily with **Epidemiological methods** and also supports **Scientific communication**.

---

*Last updated: 2026-03-29 | Enriched with target-trial and estimand-era design updates*
