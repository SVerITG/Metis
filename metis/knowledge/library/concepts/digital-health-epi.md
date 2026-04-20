# Digital Health and Epidemiology

> Reference card — AI/ML in epi, digital surveillance, mHealth, ethics.

---

## AI and Machine Learning in Epidemiology

### Applications
- **Outbreak prediction:** ML models for early warning (dengue forecasting, influenza nowcasting)
- **Disease mapping:** Deep learning for satellite imagery classification (habitat mapping, urbanization)
- **Diagnostics:** Computer vision for microscopy (malaria parasites, TB on X-ray, skin NTDs), LLMs for clinical decision support
- **Genomic epidemiology:** Phylogenetics, lineage classification, AMR prediction from sequences
- **Natural language processing:** Automated extraction from clinical notes, event-based surveillance signal triage
- **Causal ML:** Heterogeneous treatment effects, targeted learning (TMLE), causal forests

### Common ML Methods in Epi Context
| Method | Use Case |
|--------|----------|
| Random forests | Risk prediction, variable importance |
| Gradient boosting (XGBoost) | Prediction models, tabular data |
| Neural networks / deep learning | Image classification, NLP, sequence data |
| LASSO/elastic net | Variable selection in high-dimensional data |
| Clustering (k-means, DBSCAN) | Phenotyping, spatial clustering |
| Time series (ARIMA, Prophet, LSTM) | Forecasting disease incidence |

### Cautions
- **Prediction vs explanation:** ML excels at prediction; causal inference requires different tools
- **Black box problem:** Interpretability critical for public health decision-making
- **Overfitting:** Validation on held-out data essential; external validation preferred
- **Data quality:** Garbage in, garbage out — especially with routine health data in LMICs
- **Representativeness:** Training data may not reflect target population

---

## Digital Disease Surveillance

### Event-Based (Digital) Surveillance Tools
| Platform | Description |
|----------|-------------|
| **EIOS** | WHO Epidemic Intelligence from Open Sources; aggregates media, reports |
| **ProMED** | ISID; moderated expert reports on outbreaks since 1994 |
| **HealthMap** | Automated aggregation of online news, alerts (Boston Children's Hospital) |
| **BlueDot** | AI-powered global infectious disease intelligence |
| **GPHIN** | Global Public Health Intelligence Network (Public Health Agency of Canada) |
| **Google Trends** | Search query surveillance (limited reliability post-2013 flu debacle) |
| **Metabiota/Ginkgo** | Biosecurity and pandemic tracking |

### Routine Digital Systems
| System | Description |
|--------|-------------|
| **DHIS2** | Open-source HMIS; 80+ countries; modular (tracker, aggregate, events) |
| **Go.Data** | WHO outbreak investigation tool; contact tracing, transmission chains |
| **SORMAS** | Surveillance and outbreak response (Germany/Nigeria origin); open-source |
| **ODK / KoboToolbox** | Mobile data collection for field surveys |
| **CommCare** | Mobile platform for community health workers |
| **OpenMRS** | Open-source medical records system |

### Wastewater-Based Epidemiology
- COVID-19 demonstrated feasibility at scale
- Applications: poliovirus, AMR, antimicrobial consumption, illicit drugs
- Advantages: population-level, unbiased by healthcare-seeking behaviour
- Challenges: normalization, sampling design, lab capacity

---

## mHealth and Telemedicine in LMICs

### Applications
- **Community health worker (CHW) tools:** Decision support, data collection, reporting (CommCare, ODK)
- **SMS-based systems:** Appointment reminders, treatment adherence (e.g., MomConnect in South Africa)
- **Telemedicine:** Remote consultation, teledermatology for NTDs, tele-radiology
- **Self-diagnosis/triage:** Symptom checkers, AI-powered chatbots
- **Supply chain:** Stock management for medicines, cold chain monitoring

### Evidence Base
- Mixed evidence on effectiveness; context-dependent
- SMS reminders for adherence: moderate evidence of benefit
- CHW decision support: improves data quality and case management
- Telemedicine: promising for specialist access in remote areas
- Sustainability and scale-up remain major challenges

### Key Considerations for LMICs
- Network connectivity and power supply limitations
- Digital literacy variation
- Phone ownership gender gap
- Interoperability with national HMIS
- Data ownership and sovereignty

---

## Ethical Considerations

### AI Bias
- **Training data bias:** Historical health data reflects existing inequities
- **Algorithmic fairness:** Disparate performance across demographic groups
- **Feedback loops:** Biased predictions reinforce biased resource allocation
- **Mitigation:** Diverse training data, fairness metrics, algorithmic audits, human oversight

### Privacy and Data Protection
- **Health data sensitivity:** Requires highest protection standards
- **Consent:** Informed consent for digital data collection; challenges with big data/surveillance
- **De-identification:** Re-identification risk with geospatial and temporal data
- **Regulatory:** GDPR, national data protection laws, WHO guidance on health data governance
- **Sovereignty:** Who owns and controls health data generated in LMICs?

### Equity in Digital Health
- **Digital divide:** Access to technology mirrors existing inequities
- **Exclusion risk:** Digitalization may exclude most vulnerable populations
- **Language:** Majority of AI/digital tools in English; limited local language support
- **Infrastructure:** Internet access, electricity, hardware availability

### Responsible AI Principles for Health
1. Inclusiveness and equity
2. Transparency and explainability
3. Accountability and governance
4. Privacy and security
5. Reliability and safety
6. Human autonomy and oversight

---

## WHO Guideline on Digital Health Interventions (2019)

### Recommendations (selected)
- Birth notification via mobile devices (recommended)
- Death notification via mobile devices (recommended)
- Stock notification and management via mobile (recommended)
- Client-to-provider telemedicine (recommended under certain conditions)
- Digital tracking of health status combined with decision support (recommended)

### Key Message
- Digital tools are a means, not an end — must serve health system goals
- Enabling environment required: governance, infrastructure, legislation, workforce, standards

---

## R and Python Tools for Digital Epi

| Tool | Language | Purpose |
|------|----------|---------|
| `surveillance` | R | Temporal and spatio-temporal outbreak detection |
| `EpiEstim` | R | Real-time estimation of reproduction number |
| `EpiNow2` | R | Real-time Rt estimation with uncertainty |
| `tidymodels` | R | ML framework (R equivalent of scikit-learn) |
| `torch` | R | Deep learning in R |
| `scikit-learn` | Python | ML (classification, regression, clustering) |
| `PyTorch` / `TensorFlow` | Python | Deep learning |
| `Nextstrain` | Web/CLI | Genomic epidemiology visualization |

---

## Current Developments (2025-2026)

- **WHO digital-health strategy formally extended:** WHO announced on **23 May 2025** that the Global Strategy on Digital Health was extended to **2027**, and the full **Global Strategy on Digital Health 2020-2027** publication appeared on **1 December 2025**.
- **AI governance in health is now implementation-focused:** The European Commission's healthcare page states that the **EU AI Act entered into force on 1 August 2024**, with direct implications for high-risk AI systems used for medical purposes.
- **Policy now explicitly links AI, interoperability, and workforce capacity:** WHO's 2025 messaging frames digital health as central to universal health coverage, preparedness, and climate-resilient systems rather than as a standalone innovation agenda.
- **Platform maturity still matters:** REDCap, DHIS2, Go.Data, SORMAS, and ODK remain important because governance and adoption footprint often determine what is actually implementable.

## Practical Examples

- **Digital surveillance:** EIOS, HealthMap, and similar platforms show how NLP and open-source aggregation can support event-based surveillance, but only when verification pathways are strong.
- **Clinical and public-health AI:** AI tools for diagnostics or forecasting need external validation, subgroup performance checks, and governance plans before they are operationally credible.
- **Health-system digitalization:** In LMIC settings, the decisive questions are often offline usability, interoperability, training burden, and local data control rather than algorithmic novelty.

## Key References

- **WHO.** *WHO Guideline: Recommendations on Digital Interventions for Health System Strengthening.* 2019.
- **WHO.** *Ethics and Governance of Artificial Intelligence for Health.* 2021.
- **Brownstein JS et al.** Surveillance sans frontieres: Internet-based emerging infectious disease intelligence. *PLOS Medicine.* 2008;5(7):e151.
- **Wahl B et al.** Artificial intelligence (AI) and global health. *BMJ Global Health.* 2018;3:e000798.
- **Rajpurkar P et al.** AI in health and medicine. *Nature Medicine.* 2022;28:31-38.
- **WHO.** *Global Strategy on Digital Health 2020-2025.* 2021.
- **Labrique AB et al.** mHealth innovations as health system strengthening tools. *Tropical Medicine and International Health.* 2013;18(8):993-1006.
- **WHO digital health update (23 May 2025):** https://www.who.int/news/item/23-05-2025-world-health-assembly-endorses-extension-of-the-global-digital-health-strategy-to-2027
- **WHO digital health topic page:** https://www.who.int/health-topics/digital-health/
- **WHO Global Strategy on Digital Health 2020-2027:** https://www.who.int/publications/i/item/9789240116870
- **European Commission AI in healthcare:** https://health.ec.europa.eu/ehealth-digital-health-and-care/artificial-intelligence-healthcare_en
- **REDCap:** https://project-redcap.org/
- **WHO data principles:** https://data.who.int/about/data/who-data-principles

## Learning Path

- Start with `06_library/courses/surveillance-methods/` and `06_library/courses/research-writing/`.
- Pair this card with `06_library/concepts/current-challenges-2026.md` for the wider policy and governance context.
- Use it alongside `06_library/methods/data-management.md` for interoperability, metadata, stewardship, and reproducibility issues.
- In the Learning Hub, this card supports **Surveillance systems**, **Data management & R**, and **Scientific communication**.

---

*Last updated: 2026-03-29 | Enriched with 2025-2026 digital-health and AI-governance updates*
