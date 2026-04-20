# Health Economics Basics

> Reference card — core methods for economic evaluation in health, outcome measures, and decision thresholds.

---

## Types of Economic Evaluation

### Cost-Effectiveness Analysis (CEA)
- Compares costs to health outcomes in natural units (e.g., cost per case averted, cost per life-year gained)
- Most common type in global health
- Results expressed as an incremental cost-effectiveness ratio (ICER)

### Cost-Benefit Analysis (CBA)
- Monetizes all outcomes (including health) in currency units
- Allows comparison across sectors (health vs education vs infrastructure)
- Controversial: requires assigning monetary value to life and health

### Cost-Utility Analysis (CUA)
- Special case of CEA using quality-adjusted outcomes (QALYs or DALYs)
- Enables comparison across different diseases and interventions
- Preferred by many HTA agencies (NICE, WHO-CHOICE)

## DALYs and QALYs

- **DALY (Disability-Adjusted Life Year):** Years of life lost (YLL) + years lived with disability (YLD); measures burden; lower is better
- **QALY (Quality-Adjusted Life Year):** Life years weighted by health-related quality of life (0 = death, 1 = perfect health); measures benefit; higher is better
- DALYs dominant in global health / LMIC settings; QALYs dominant in HIC / HTA settings
- Disability weights (DALYs) derived from population surveys (GBD study)
- Utility weights (QALYs) derived from patient or general population preferences (EQ-5D, SF-6D, TTO, SG)

## ICER (Incremental Cost-Effectiveness Ratio)

- ICER = (Cost_new - Cost_comparator) / (Effect_new - Effect_comparator)
- Plotted on cost-effectiveness plane (four quadrants)
- Northwest: new intervention dominated (more costly, less effective)
- Southeast: new intervention dominant (less costly, more effective)
- Northeast: trade-off — compare ICER to willingness-to-pay threshold

## Willingness-to-Pay (WTP) Threshold

- If ICER < WTP threshold, intervention considered cost-effective
- WHO-CHOICE (historical): 1x GDP per capita (very cost-effective), 3x GDP per capita (cost-effective) — now considered too simplistic
- Country-specific thresholds increasingly recommended based on opportunity cost
- NICE (UK): GBP 20,000-30,000 per QALY

## Budget Impact Analysis

- Estimates total financial cost of adopting a new intervention at population level
- Complements CEA: an intervention can be cost-effective but unaffordable
- Time horizon typically 1-5 years
- Accounts for eligible population, uptake rates, displacement of current practice

## Discounting

- Future costs and health outcomes are discounted to present value
- Standard rate: 3% per year (WHO-CHOICE, US guidelines); 3.5% (NICE)
- Rationale: time preference — people value present benefits more than future ones
- Sensitivity analysis should test alternative rates (0%, 5%)

## Current Developments (2025-2026)

- **WHO cost-effectiveness update:** In 2025 WHO reiterated that GDP-based thresholds are no longer recommended and encourages country-specific opportunity-cost-informed thresholds, often drawn from marginal productivity analyses of the health budget.
- **Cost-effectiveness in elimination programs:** WHO’s `Choosing Interventions that are Cost-Effective (WHO-CHOICE)` online tool now includes new modeling templates for elimination and post-elimination strategies (updated 2025), combining DALY-based results with budget impact for sustainability.
- **Second Panel report 2024 update:** The Second Panel (US) published supplemental notes in 2024-2025 about incorporating equity weights and distributional cost-effectiveness, which is especially relevant for interventions in inequitable settings.

## Learning Path

- Pair this card with `06_library/courses/surveillance-methods/` for measuring elimination returns and with `06_library/courses/biostatistics/` for statistical modeling in economic evaluations.
- Combine with `06_library/concepts/health-equity-sdh.md` when equity-adjusted cost-effectiveness or distributional considerations are required.
- Link to `06_library/courses/research-writing/` for framing economic arguments within funding proposals or manuscripts.
- In the Learning Hub, this card links to **Health economics** (conceptual domain) and **Epidemiological methods** for modeling.

---

*Last updated: 2026-03-30 | Enriched with WHO-CHOICE updates and opportunity-cost threshold guidance*
