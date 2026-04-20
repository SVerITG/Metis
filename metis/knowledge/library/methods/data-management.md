# Data Management

> Reference card — FAIR principles, data capture tools, cleaning workflows, and reproducible research practices.

---

## FAIR Principles

- **Findable:** Persistent identifiers (DOI), rich metadata, registered in searchable resources
- **Accessible:** Retrievable by identifier using open protocols; metadata accessible even if data restricted
- **Interoperable:** Use shared vocabularies and standards; machine-readable formats (CSV, JSON, not PDF tables)
- **Reusable:** Clear license, provenance documentation, community standards for metadata
- Increasingly required by funders (Wellcome, NIH, EU Horizon)

## Data Dictionaries and Codebooks

- Document every variable: name, label, type, coding scheme, allowable values, units, missing codes
- Create before data collection, update during cleaning
- Essential for reproducibility and data sharing
- Include skip logic documentation for survey data

## Electronic Data Capture Tools

- **REDCap:** Secure, web-based; widely used in clinical research; supports branching logic, calculated fields, audit trails; free for consortium members
- **ODK / KoboToolbox:** Open-source mobile data collection; offline-capable; strong for field surveys in LMICs
- **DHIS2:** Health management information system; national-level routine data; aggregate and tracker modules
- **EpiCollect5:** Free mobile data collection; GPS capture; simpler than ODK for small projects
- Selection criteria: offline capability, cost, institutional support, data ownership, regulatory requirements

## Data Cleaning Workflow

- **Validation rules:** Built into data entry forms (range checks, type constraints, required fields)
- **Range checks:** Flag implausible values (e.g., age > 120, negative counts)
- **Consistency checks:** Cross-variable logic (e.g., diagnosis date before birth date, male pregnancies)
- **Duplicate detection:** Identify and resolve duplicate records (exact and fuzzy matching)
- **Outlier review:** Statistical detection (IQR, z-score) with domain-informed judgment
- **Documentation:** Log every cleaning decision; never overwrite raw data; maintain cleaning script

## Reproducible Research Workflow (R-Focused)

- **R projects (.Rproj):** Self-contained working directory; never use `setwd()`
- **renv:** Package version management; lock file ensures same package versions across machines
- **targets:** Pipeline toolkit; tracks dependencies, only re-runs what changed; ideal for complex analyses
- **Quarto / RMarkdown:** Literate programming; code + narrative + output in one document
- **here:** Construct file paths relative to project root; avoids absolute path fragility
- Folder structure convention: `data-raw/`, `data/`, `R/`, `output/`, `reports/`

## Version Control with Git

- Track all code and documentation (not data files > 100 MB)
- Meaningful commit messages: what changed and why
- `.gitignore` for data files, credentials, OS artifacts
- Branching for experiments; merge when validated
- GitHub/GitLab for collaboration, code review, issue tracking

## Data Sharing and Archiving

- **Zenodo:** CERN-hosted; free; DOI assignment; integrates with GitHub
- **Figshare:** Free for individual researchers; multiple file types; DOI
- **Dryad:** Curated; primarily for data underlying publications; fee may apply
- **Institutional repositories:** Check if your university or institute has one
- License your data explicitly: CC-BY 4.0, CC0 for maximum reuse
- Embargo options available for sensitive or pre-publication data

## Current Developments (2025-2026)

- **WHO continues to frame data as a public good:** WHO's data-principles pages still explicitly anchor stewardship in openness, trust, system capacity, responsible management, and gap-filling, while also referencing FAIR and GATHER as relevant standards.
- **Digital-health governance is now current policy:** WHO published the **Global Strategy on Digital Health 2020-2027** on **1 December 2025**, following the World Health Assembly decision in May 2025 to extend the strategy.
- **REDCap remains a major real-world platform:** The REDCap consortium site reports **7,985 active institutional partners in 163 countries**, with more than **2.4 million projects** and **3.9 million users**.
- **Data plans now need more than storage logic:** Interoperability, metadata, auditability, ethical sharing, and code availability increasingly sit inside normal data-management expectations.

## Practical Examples

- **WHO-aligned stewardship:** FAIR principles are strongest when paired with explicit metadata, provenance, and access conditions rather than treated as a slogan.
- **Field data collection:** ODK/Kobo remain practical choices for offline collection in LMIC settings, while REDCap remains strong where institutional hosting and governance support are available.
- **Reproducible pipelines:** `renv`, `targets`, and Quarto are most valuable when used together: locked dependencies, explicit pipeline steps, and human-readable analytic outputs.

## Key References

- Broman, K. W. & Woo, K. H. (2018). Data organization in spreadsheets. *The American Statistician*, 72(1), 2-10.
- Wilson, G. et al. (2017). Good enough practices in scientific computing. *PLoS Computational Biology*, 13(6), e1005510.
- Wilkinson, M. D. et al. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data*, 3, 160018.
- Landau, W. M. (2021). The targets R package: a dynamic Make-like function-oriented pipeline toolkit for reproducibility and high-performance computing. *JOSS*, 6(57), 2959.
- **WHO data principles:** https://data.who.int/about/data/who-data-principles
- **WHO data policy:** https://data.who.int/about/data/data-policy
- **WHO Global Strategy on Digital Health 2020-2027:** https://www.who.int/publications/i/item/9789240116870
- **REDCap consortium:** https://project-redcap.org/
- **ODK:** https://getodk.org/
- **GATHER guidance:** https://data.who.int/about/data/gather

## Learning Path

- Start with `06_library/courses/biostatistics/` and `06_library/courses/surveillance-methods/`.
- Pair this card with `06_library/methods/surveillance-systems.md` for reporting flows and with `06_library/concepts/digital-health-epi.md` for governance and platform questions.
- Use it alongside `06_library/courses/research-writing/` when building protocols, reproducible analysis plans, and sharing strategies.
- In the Learning Hub, this card aligns primarily with **Data management & R** and also supports **Surveillance systems**.

---

*Last updated: 2026-03-29 | Enriched with WHO data-governance and digital-health updates*
