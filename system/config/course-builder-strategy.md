# Course Builder Strategy — Public Health Background Database

**Version:** 1.0 — 2026-05-19
**Purpose:** Defines how Metis builds, verifies, and maintains the public health background knowledge base across all 22 MPH curriculum domains. This document is authoritative for the Content Harvester and Course Builder agents.

---

## 1. The Core Principle

A knowledge database is only useful if it actually covers a topic well. "We have a file about it" is not coverage. Coverage means: the indexed content is sufficient for a competent researcher to retrieve, reason about, and write on the topic without gaps.

This strategy enforces that standard at every step.

---

## 2. The Pipeline

Every domain goes through this pipeline — in order, without skipping steps:

```
DISCOVER → HARVEST → EXTRACT → EVALUATE → GAP-FILL → REPORT
```

### 2.1 Discover
Identify the target resources for the domain (minimum 5, ideally 8–10). Prefer:
1. Open-access textbooks or book chapters (HTML or PDF)
2. WHO / CDC / ECDC official guidelines (PDF or HTML)
3. Landmark review articles (PMC open access)
4. Domain-specific handbooks or field manuals
5. Recent systematic reviews or meta-analyses

For each resource, record: title, URL, format, expected file size, access status (open / browser-only / paywall).

### 2.2 Harvest
Pull each resource using the appropriate method:
- **HTML books/pages** → Content Harvester web fetch → save as Markdown knowledge card
- **Open PDFs** → `curl -L` → verify size > 50KB → index
- **Browser-only PDFs** → flag in `MANUAL-DOWNLOADS-COMPLETE.md`, do NOT block progress
- **Paywalled** → extract abstract/summary only, flag clearly

If a resource is unavailable, immediately search for an equivalent alternative. Never leave a slot empty without a substitute.

### 2.3 Extract
Run the indexer on all downloaded PDFs:
```bash
SEMANTIC=0 MAX_PDF_MB=25 python3 knowledge/library/index-ph-library.py
```

For HTML sources, run Content Harvester to produce knowledge cards in `knowledge/library/ph-background/{domain-slug}/`.

After extraction, spot-check 3 documents per domain:
- Word count > 1,000? If not → image-scanned PDF, mark as `⚠️ image-only`
- Content on-topic? If not → extraction artefact (HTML error page captured), remove

### 2.4 Evaluate
Run the coverage check (see §3). Produce the domain coverage table.

### 2.5 Gap-fill
Any domain rated `❌ Empty` or `⚠️ Weak` after evaluation:
1. Check whether the alternative HTML sources from §4 have been harvested
2. If not → run Content Harvester on those URLs
3. If yes and still weak → search PMC/Google Scholar for open-access alternatives
4. Repeat until coverage reaches at least `⚠️ Moderate`

Do NOT declare a domain complete if it is still `❌ Empty`. This is a hard rule.

### 2.6 Report
After every indexing or harvesting run, produce a coverage report (§3.3). Save to:
`outputs/reviews/metis/YYYY-MM-DD_ph-library-coverage-report.md`

---

## 3. Coverage Standards

### 3.1 Word threshold per domain

| Rating | Criteria | Action |
|---|---|---|
| ✅ **Strong** | ≥50,000 words from ≥2 distinct source types | No action needed |
| ⚠️ **Moderate** | 15,000–50,000 words OR only 1 source type | Add 1–2 more sources |
| ⚠️ **Weak** | 5,000–15,000 words | Gap-fill required |
| ❌ **Empty** | <5,000 words (or only image-PDFs) | Immediate gap-fill required |

### 3.2 Diversity requirement

A domain is never Strong unless it has at least:
- 1 **foundational text** (textbook chapter, authoritative overview)
- 1 **official guideline** (WHO, CDC, ECDC, or equivalent body)
- 1 **evidence-based review** (systematic review, meta-analysis, or landmark paper)

A domain covered by only one type (e.g., three WHO reports but no textbook) is capped at Moderate regardless of word count.

### 3.3 Coverage report template

After every pipeline run, produce this table:

```markdown
## PH Library Coverage Report — [DATE]

| Domain | Words | Docs | Rating | Gaps |
|--------|-------|------|--------|------|
| D1 Epidemiology | X,XXX | N | ✅/⚠️/❌ | [what's missing] |
...

### Summary
- Strong domains: N
- Moderate: N
- Weak: N
- Empty: N
- Total words indexed: X,XXX,XXX
- Image-only (unusable): N docs flagged

### Immediate gap-fill targets
1. ...

### Browser downloads still needed
1. ...
```

---

## 4. Domain Reference — Resources and Targets

For each domain: current status as of 2026-05-19, primary targets (what to harvest next), and at least 5 alternative/additional sources.

---

### D1 — Epidemiology Foundations & Surveillance

**Current (2026-05-19):** WHO IDSR Technical Guidelines (92,669w) ✅
**Rating: ⚠️ Moderate** — strong surveillance coverage, foundational textbooks missing

**Harvest targets (priority order):**
1. **EpiR Handbook** (HTML book, ~300 chapters) — `https://epirhandbook.com/en/` — Content Harvester
2. **CDC Principles of Epidemiology SS1978** (PDF, already in library, index if cloud-synced)
3. **Bonita Basic Epidemiology 2nd ed** — `https://iris.who.int/handle/10665/43541` — browser download
4. **CDC Field Epidemiology Manual** (HTML) — `https://www.cdc.gov/eis/field-epi-manual/index.html`
5. **ECDC Surveillance Handbook** — `https://www.ecdc.europa.eu/en/publications-data/ecdc-handbook-surveillance-indicators`
6. **Porta Dictionary of Epidemiology** (6th ed, Oxford) — paywall; extract abstract only
7. **CDC MMWR Evaluating Public Health Surveillance 2001** — `https://www.cdc.gov/mmwr/preview/mmwrhtml/rr5013a1.htm` (HTML version)

**Minimum coverage target:** 150,000 words (textbook + guidelines + R handbook)

---

### D2 — Biostatistics & Statistical Methods

**Current (2026-05-19):** LibreTexts (161k) + Biostat-R (139k) + lme4 (18k) + Leyland MLM (105k) = 423,000w ✅
**Rating: ✅ Strong** — excellent quantitative base

**Additional sources to add:**
1. **Introduction to Statistical Learning (ISLR2)** (PDF, free) — `https://www.statlearning.com/`
2. **R for Data Science 2nd ed** (HTML) — `https://r4ds.hadley.nz/`
3. **OpenStax Introductory Statistics 2e** (HTML) — `https://openstax.org/books/introductory-statistics-2e/pages/1-introduction`
4. **Gelman BDA3** (PDF, 53MB — index with `MAX_PDF_MB=60`) — already in library
5. **Diggle & Chetwynd Statistical Analysis of Spatial Data** — partial via Google Books

**Minimum coverage target:** Already met. Add ISLR and R4DS for modern ML methods.

---

### D3 — Environmental Health

**Current (2026-05-19):** 0 words ❌
**Rating: ❌ Empty** — nothing indexed

**Harvest targets (priority order):**
1. **WHO Air Quality Guidelines 2021** — `https://iris.who.int/handle/10665/345329` — browser download
2. **WHO Drinking Water Quality Guidelines 4th ed** — `https://iris.who.int/handle/10665/352532` — browser download
3. **WHO Housing and Health Guidelines 2018** — `https://iris.who.int/handle/10665/276001` — browser download
4. **CDC Environmental Public Health Indicators** (HTML) — `https://ephtracking.cdc.gov/DataExplorer/`
5. **UNEP Global Environment Outlook 6 Summary** (PDF) — `https://wedocs.unep.org/bitstream/handle/20.500.11822/27539/GEO6_2019.pdf`
6. **EPA Environmental Justice guidance** (HTML) — `https://www.epa.gov/environmentaljustice`
7. **WHO Environmental Health Indicators framework** (HTML) — `https://www.who.int/tools/environmental-health-indicators`

**Minimum coverage target:** 50,000 words

---

### D4 — Health Systems & Policy

**Current (2026-05-19):** Astana (1.9k) + RHIS (4k) = 5,900w ⚠️
**Rating: ❌ Weak** — all major WHO World Health Reports blocked

**Harvest targets (priority order):**
1. **WHO World Health Report 2000** (HTML) — `https://www.who.int/whr/2000/en/`
2. **WHO World Health Report 2008: PHC** (HTML) — `https://www.who.int/whr/2008/en/`
3. **WHO World Health Report 2010: Health Financing** (HTML) — `https://www.who.int/whr/2010/en/`
4. **European Observatory HiT series** (many open-access PDFs) — `https://eurohealthobservatory.who.int/publications/health-systems-in-transition-hit-series`
5. **Kutzin health financing framework 2013** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC3748748/`
6. **Kruk high-quality health systems 2018** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC6237506/`
7. **WHO Everybody's Business 2007** — `https://iris.who.int/handle/10665/43432` — browser download
8. **WHO Health Systems Performance Assessment 2000** — `https://apps.who.int/iris/handle/10665/42478` — browser download

**Minimum coverage target:** 80,000 words

---

### D5 — Health Economics

**Current (2026-05-19):** WHO GBD/DALY methods (17,489w) ⚠️
**Rating: ⚠️ Weak**

**Harvest targets:**
1. **CHEERS 2022 Reporting Checklist** (HTML) — `https://www.equator-network.org/reporting-guidelines/cheers/`
2. **iDSI Reference Case for Economic Evaluation** (PDF) — `https://www.idsihealth.org/resource-library/the-reference-case-for-economic-evaluation/`
3. **WHO CHOICE Intervention Priority-Setting** (HTML) — `https://www.who.int/teams/health-systems-governance-and-financing/economic-analysis/cost-effectiveness`
4. **World Bank WDR 1993 Investing in Health** (PDF) — `https://openknowledge.worldbank.org/handle/10986/5976`
5. **Jamison DCP3 Overview chapter** (PMC open) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC7199931/`
6. **Wagstaff health equity measurement** (World Bank open) — `https://openknowledge.worldbank.org/handle/10986/13437`
7. **Global Burden of Disease study results** (HTML) — `https://www.healthdata.org/research-analysis/gbd`

**Minimum coverage target:** 60,000 words

---

### D6 — Social Determinants of Health & Equity

**Current (2026-05-19):** Marmot Fair Society (137k) + WHO CSDH (1.3k) = 138,600w ✅
**Rating: ✅ Strong** (one source dominates — add diversity)

**Additional sources to add:**
1. **Dahlgren & Whitehead rainbow model** (WHO Europe, PDF) — `https://iris.who.int/handle/10665/352490`
2. **Solar & Irwin CSDH conceptual framework** (WHO, PDF) — `https://www.who.int/publications/i/item/9789241563703`
3. **WHO CSDH Closing the Gap 2008** — `https://iris.who.int/handle/10665/43943` — browser download
4. **Link & Phelan fundamental cause theory** — paywall; use PMC versions where available
5. **WHO Health Equity Assessment Toolkit** (HTML) — `https://www.who.int/data/inequality-monitor/assessment_toolkit`
6. **PAHO Health in the Americas 2022** (HTML summary) — `https://hia.paho.org/en`

**Minimum coverage target:** Already met on words. Needs diversity (2 more source types).

---

### D7 — Global Health Governance

**Current (2026-05-19):** ECDC Rapid Risk Assessment (20k) + WHO-JEE (image only) = 20,360w ⚠️
**Rating: ⚠️ Weak**

**Harvest targets:**
1. **IHR 2005 full text** (HTML) — `https://www.who.int/publications/i/item/9789241580496`
2. **WHO Constitution + Alma Ata Declaration** (HTML) — `https://www.who.int/about/governance/constitution`
3. **WHO JEE methodology** (HTML) — `https://www.who.int/publications/i/item/9789240051980`
4. **UN SDG progress report 2023** (PDF) — `https://unstats.un.org/sdgs/report/2023/`
5. **Gostin et al Global Health Law** (open chapters) — `https://globalhealth.law/`
6. **Global Fund strategy 2023-2028** (PDF) — `https://www.theglobalfund.org/media/11612/strategy_2023-2028_en.pdf`
7. **WHO Global Action Plan for Healthy Lives and Well-being** (HTML) — `https://www.who.int/initiatives/sdg3-global-action-plan`

**Minimum coverage target:** 60,000 words

---

### D8 — Infectious Disease & Surveillance Systems

**Current (2026-05-19):** Surveillance guidance = image-only PDFs ≈ 3,000 real words ❌
**Rating: ❌ Empty** (indexed docs are image PDFs)

**Harvest targets:**
1. **ECDC Digital Technologies for Infectious Disease Surveillance 2022** (PDF in library, re-index if cloud-synced)
2. **ECDC Wastewater-Based Surveillance Framework** (PDF in library, re-index)
3. **ECDC Epidemiological Methods guidance** (HTML) — `https://www.ecdc.europa.eu/en/publications-data/conducting-infectious-disease-surveillance`
4. **ProMED methodology and practice** (HTML) — `https://promedmail.org/about-promed/`
5. **CDC MMWR Surveillance Summaries** (HTML, selected) — `https://www.cdc.gov/mmwr/mmwr_ss.html`
6. **Tuite et al mathematical modelling review** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC7014988/`
7. **WHO Vaccination Coverage Cluster Survey Manual 2018** — `https://iris.who.int/handle/10665/272820` — browser download

**Minimum coverage target:** 60,000 words

---

### D9 — Neglected Tropical Diseases & HAT

**Current (2026-05-19):** WHO HAT Atlas = image only (847w real) ❌
**Rating: ❌ Empty** — critical gap given research focus

**Harvest targets (HIGH PRIORITY for this user's PhD):**
1. **Simarro et al 2012 HAT global situation** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC3485037/`
2. **Büscher et al 2017 HAT Lancet review** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC5705698/`
3. **WHO NTD Roadmap 2021-2030** (HTML) — `https://www.who.int/publications/i/item/9789240010352`
4. **DNDi HAT disease overview** (HTML) — `https://dndi.org/diseases/human-african-trypanosomiasis/`
5. **Sutherland et al HAT elimination progress** (PMC open access) — search `https://pmc.ncbi.nlm.nih.gov/` for "human african trypanosomiasis elimination 2020"
6. **WHO HAT TRS 984 2013** — `https://iris.who.int/handle/10665/95008` — browser download
7. **MSF HAT access to medicines reports** (HTML) — `https://msfaccess.org/sleeping-sickness`
8. **WHO HAT Atlas interactive** (HTML data) — `https://www.who.int/data/atlas-of-human-african-trypanosomiasis`
9. **Hotez NTDs as poverty-promoting conditions** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC2267196/`
10. **ISGlobal NTD fact sheets** (HTML) — `https://www.isglobal.org/en/our-research-and-training/our-areas-of-research/neglected-tropical-diseases`

**Minimum coverage target:** 80,000 words (10 sources — this domain is core to the user's research)

---

### D10 — Maternal & Child Health

**Current (2026-05-19):** Postnatal Care highlights (4,421w) ⚠️
**Rating: ❌ Weak**

**Harvest targets:**
1. **WHO ANC Recommendations 2016** — `https://iris.who.int/handle/10665/250796` — browser download
2. **Countdown to 2030 MCH tracking** (HTML) — `https://www.countdown2030.org/`
3. **UNICEF State of the World's Children 2023** (HTML summary) — `https://www.unicef.org/reports/state-of-worlds-children`
4. **The Lancet Maternal Survival series 2006** (PMC open) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC2276683/`
5. **WHO Skilled Birth Attendant global mapping** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC8053463/`
6. **GBD 2019 Child Mortality estimates** (Lancet open) — `https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(21)01728-0/fulltext`

**Minimum coverage target:** 60,000 words

---

### D11 — Nutrition & Food Security

**Current (2026-05-19):** 0 words (Global Nutrition Report may be cloud-only) ❌
**Rating: ❌ Empty**

**Harvest targets:**
1. **Global Nutrition Report 2023** (HTML) — `https://globalnutritionreport.org/reports/2023-global-nutrition-report/`
2. **SOFI 2023 State of Food Security** (HTML) — `https://www.fao.org/publications/sofi/en/`
3. **WHO Nutrition action factsheets** (HTML) — `https://www.who.int/news-room/fact-sheets/detail/malnutrition`
4. **UNICEF-WHO-World Bank joint malnutrition estimates** (HTML data portal) — `https://www.who.int/data/nutrition`
5. **Black et al Lancet 2013 maternal & child undernutrition** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC3752254/`
6. **IFPRI Global Food Policy Report 2022** (PDF) — `https://www.ifpri.org/publication/2022-global-food-policy-report`
7. **WHO double burden of malnutrition** (HTML) — `https://www.who.int/news-room/fact-sheets/detail/the-double-burden-of-malnutrition`

**Minimum coverage target:** 50,000 words

---

### D12 — Non-Communicable Diseases

**Current (2026-05-19):** PAHO NCD Roadmap (1.8k) + WHO NCD Best Buys (image) ≈ 1,800w ❌
**Rating: ❌ Weak**

**Harvest targets:**
1. **WHO STEPS surveillance manual** (PDF) — `https://www.who.int/teams/noncommunicable-diseases/surveillance/systems-tools/steps`
2. **WHO Global NCD Action Plan 2013-2020** — `https://iris.who.int/handle/10665/94384` — browser download
3. **WHO Best Buys for NCDs expanded** (PDF) — `https://iris.who.int/handle/10665/259232` — browser download (note: 847w = image version in library)
4. **NCD Alliance resources** (HTML) — `https://ncdalliance.org/resources`
5. **GBD 2019 NCD estimates** (Lancet open) — `https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(20)30925-9/fulltext`
6. **WHO STEPwise country profiles** (HTML per country) — `https://www.who.int/teams/noncommunicable-diseases/surveillance/data/country-profiles`
7. **IHME NCD Collaborators papers** (Lancet, many open) — `https://www.healthdata.org/research-analysis/diseases-and-conditions`

**Minimum coverage target:** 60,000 words

---

### D13 — Mental Health

**Current (2026-05-19):** 0 words ❌
**Rating: ❌ Empty**

**Harvest targets:**
1. **WHO Mental Health factsheets** (HTML) — `https://www.who.int/news-room/fact-sheets/detail/mental-disorders`
2. **Lancet Commission on Global Mental Health 2018** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC6191490/`
3. **Patel et al 2018 mental health science paper** (Lancet, open) — `https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(18)31612-X/fulltext`
4. **WHO mhGAP Intervention Guide v2** — `https://iris.who.int/handle/10665/250796` — browser download (or HTML summary)
5. **WHO Mental Health Atlas 2020** — `https://iris.who.int/handle/10665/345946` — browser download
6. **WHO Thinking Healthy perinatal depression guide** (PDF) — `https://www.who.int/publications/i/item/9789241548564`
7. **Collins et al Grand challenges global mental health** (Nature, open) — `https://www.nature.com/articles/475027a`

**Minimum coverage target:** 50,000 words

---

### D14 — Spatial Epidemiology & GIS

**Current (2026-05-19):** Leyland MLM = 105,142w (multilevel, not spatial) ⚠️
**Rating: ⚠️ Weak** — strong on MLM, weak on spatial methods

**Harvest targets:**
1. **Paula Moraga "Geospatial Health Data"** (HTML book, free) — `https://www.paulamoraga.com/book-geospatial/`
2. **SaTScan User Guide v10** (PDF, free registration) — `https://www.satscan.org/`
3. **Bivand et al Applied Spatial Data Analysis with R** (Springer Open partial) — `https://asdar-book.org/`
4. **INLA tutorials** (HTML) — `https://www.r-inla.org/examples-tutorials`
5. **Elliott & Wartenberg spatial epidemiology challenges** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC1241832/`
6. **Lawson disease mapping resources** (HTML) — `https://www.wiley.com/en-us/Bayesian+Disease+Mapping%2C+3rd+Edition-p-9780367670832`
7. **OpenStreetMap spatial health research guides** (HTML) — `https://wiki.openstreetmap.org/wiki/Health`

**Minimum coverage target:** 80,000 words (spatial must include both methods and applications)

---

### D15 — Research Methods & Scientific Writing

**Current (2026-05-19):** Cochrane Ch1 (5.3k) + Biostat-R (counted in D2) ⚠️
**Rating: ⚠️ Weak** — reporting guidelines missing

**Harvest targets:**
1. **EpiR Handbook** (HTML book) — already in D1, tag for D15 too — `https://epirhandbook.com/en/`
2. **PRISMA 2020 Statement** (HTML) — `https://www.prisma-statement.org/prisma-2020`
3. **STROBE Statement for observational studies** (HTML) — `https://www.strobe-statement.org/`
4. **CONSORT 2010 for RCTs** (HTML) — `https://www.consort-statement.org/`
5. **GATHER guidelines for global health estimates** (HTML) — `https://www.gather-statement.org/`
6. **Cochrane Handbook full version** (HTML) — `https://training.cochrane.org/handbook`
7. **BMJ Statistics Notes series** (BMJ open) — `https://www.bmj.com/specialties/statistics-notes`

**Minimum coverage target:** 60,000 words

---

### D16 — Program Evaluation & Implementation Science

**Current (2026-05-19):** CDC Framework MMWR (in library, not indexed) ≈ 0 searchable ❌
**Rating: ❌ Empty**

**Harvest targets:**
1. **CDC Framework for Program Evaluation MMWR 1999** — index existing file (in library)
2. **W.K. Kellogg Foundation Logic Model Guide** (PDF, free) — `https://www.wkkf.org/resource-directory/resources/2004/01/logic-model-development-guide`
3. **UNDP Evaluation Handbook** (PDF, free) — `https://erc.undp.org/evaluation/documents/download/9117`
4. **BetterEvaluation Rainbow Framework** (HTML) — `https://www.betterevaluation.org/frameworks-guides/rainbow-framework`
5. **WHO Health Programme Evaluation Guide 2013** — `https://iris.who.int/handle/10665/85735` — browser download
6. **Fixsen et al implementation science frameworks** (PDF) — `https://nirn.fpg.unc.edu/resources/implementation-research-synthesis-literature`
7. **USAID CLA Framework** (HTML) — `https://usaidlearninglab.org/cla`

**Minimum coverage target:** 40,000 words

---

### D17 — Health Informatics & DHIS2

**Current (2026-05-19):** DHIS2 guide (24MB, not indexed due to size cap) ❌
**Rating: ❌ Empty** (technically available but bypassed by size cap)

**Harvest targets:**
1. **DHIS2 Implementation Guide** — re-index with `MAX_PDF_MB=30` (already in library)
2. **DHIS2 online documentation** (HTML) — `https://docs.dhis2.org/en/implement/implementing-dhis2/overview.html`
3. **WHO Digital Health Atlas** (HTML) — `https://digitalhealthatlas.org/`
4. **OpenHIE Community Standards** (HTML) — `https://ohie.org/framework/`
5. **Braa et al "Networks of Action" DHIS2 paper** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC1831530/`
6. **WHO Global Digital Health Strategy 2020-2025** (PDF, in library — index if cloud-synced)
7. **HL7 FHIR for public health** (HTML) — `https://www.hl7.org/fhir/overview.html`

**Minimum coverage target:** 80,000 words (DHIS2 alone is 60k+ once indexed)

---

### D18 — Field Epidemiology & Outbreak Response

**Current (2026-05-19):** CIFOR Foodborne (56k) + AFENET (image) + ECDC (image) ≈ 56,000w ⚠️
**Rating: ⚠️ Moderate** (CIFOR is good; AFENET and ECDC are image-only)

**Harvest targets:**
1. **CDC Field Epidemiology Manual** (HTML, full) — `https://www.cdc.gov/eis/field-epi-manual/index.html`
2. **PAHO Field Epidemiology Training** (HTML) — `https://www.paho.org/en/field-epidemiology-training-program-fetp`
3. **WHO Outbreak Communication Guidelines** (HTML/PDF) — `https://www.who.int/publications/i/item/outbreak-communication-guidelines`
4. **GOARN methodology documents** (HTML) — `https://extranet.who.int/goarn/`
5. **ECDC Field Epidemiology Manual full** (HTML, if accessible) — `https://fieldmanuals.mscbs.es/`
6. **Langmuir "The Epidemiologic Basis of Eradication" classic paper** — PMC open access
7. **Reingold outbreak investigations textbook chapter** — extract available portions

**Minimum coverage target:** 80,000 words

---

### D19 — Climate Change & Health

**Current (2026-05-19):** WHO Climate-Resilient (31k) + WHO-UNFCCC (11k) = 42,000w ✅ (plus WHO-COP29 in library, cloud-only)
**Rating: ⚠️ Moderate** — good start, needs IPCC and Lancet Countdown

**Harvest targets:**
1. **IPCC AR6 WG2 Chapter 7 — Human Health** (PDF, free) — `https://www.ipcc.ch/report/ar6/wg2/`
2. **Lancet Countdown 2023 Report** (HTML) — `https://www.lancetcountdown.org/2023-report/`
3. **WHO Climate & Health factsheets** (HTML) — `https://www.who.int/news-room/fact-sheets/detail/climate-change-and-health`
4. **WHO COP29 Special Report** — index from library if cloud-synced
5. **Watts et al Lancet Countdown foundational paper 2018** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC6196257/`
6. **Climate & Clean Air Coalition health resources** (HTML) — `https://www.ccacoalition.org/en/content/health`

**Minimum coverage target:** 80,000 words

---

### D20 — One Health & Antimicrobial Resistance

**Current (2026-05-19):** WHO One Health (image) + WOAH AMR (not indexed, cloud-only) ≈ 0w ❌
**Rating: ❌ Empty**

**Harvest targets:**
1. **O'Neill AMR Review Final Report 2016** (PDF, free) — `https://amr-review.org/sites/default/files/160518_Final%20paper_with%20cover.pdf`
2. **WHO Global Action Plan on AMR** (HTML) — `https://www.who.int/publications/i/item/9789241509763`
3. **Tripartite One Health Joint Plan 2022-2026** (PDF in library, index if cloud-synced)
4. **FAO AMR resources** (HTML) — `https://www.fao.org/antimicrobial-resistance/en/`
5. **WOAH AMR strategy** (HTML) — `https://www.woah.org/en/what-we-do/animal-health-and-welfare/antimicrobial-resistance/`
6. **Chatham House One Health report** (PDF) — `https://www.chathamhouse.org/2021/05/one-health-approach-global-health`
7. **van Boeckel et al global antibiotic use** (Science, open) — `https://www.science.org/doi/10.1126/science.1260752`

**Minimum coverage target:** 50,000 words

---

### D21 — Africa & Sub-Saharan Africa Health Systems

**Current (2026-05-19):** 5 WHO AFRO reports = 193,000w ✅
**Rating: ✅ Strong** (but Africa CDC documents are image-only — fix needed)

**Priority fix:** Africa CDC PDFs (58, 59, Africa-CDC-Public-Health) extract as image. Find text-based versions:
1. **Africa CDC Annual Report 2023** (HTML) — `https://africacdc.org/annual-reports/`
2. **Africa CDC Strategic Plan 2023-2027** (HTML) — `https://africacdc.org/strategic-plan/`

**Additional sources:**
1. **Lancet Africa Commission 2023** (open) — `https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(23)00675-2/fulltext`
2. **IHME Sub-Saharan Africa GBD visualizations** (HTML) — `https://www.healthdata.org/research-analysis/health-by-location/profiles/sub-saharan-africa`
3. **AU Agenda 2063 health dimensions** (HTML) — `https://au.int/agenda2063/`
4. **WHO AFRO Integrated Disease Surveillance** (HTML) — `https://www.afro.who.int/health-topics/disease-surveillance`

**Minimum coverage target:** Already met. Fix Africa CDC image PDFs.

---

### D22 — HAT & Human African Trypanosomiasis (Deep Domain)

**Current (2026-05-19):** WHO HAT Atlas = image only (847w) ❌
**Rating: ❌ Empty** — this is the user's core research domain, highest priority

**This domain requires aggressive harvesting:**
1. **Büscher et al 2017 Lancet review** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC5705698/`
2. **Simarro et al 2012 global situation** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC3485037/`
3. **Simarro et al 2010 Atlas** (PMC) — `https://pmc.ncbi.nlm.nih.gov/articles/PMC2987831/`
4. **Franco et al 2014 HAT epidemiology** (PMC) — search PMC for "human african trypanosomiasis epidemiology franco 2014"
5. **WHO TRS 984 2013** (browser download) — `https://iris.who.int/handle/10665/95008`
6. **DNDi HAT disease page** (HTML) — `https://dndi.org/diseases/human-african-trypanosomiasis/`
7. **MSF sleeping sickness access** (HTML) — `https://msfaccess.org/sleeping-sickness`
8. **Lindner et al HAT elimination case DRC** (PMC) — search for "HAT elimination criteria Lindner"
9. **WHO HAT 2022 progress report** (HTML) — `https://www.who.int/news-room/feature-stories/detail/human-african-trypanosomiasis`
10. **Pépin "The Origin of AIDS" (HAT context)** — extract relevant chapters (paywall, flag)
11. **Mitashi et al HAT DRC mHealth** (PMC) — search PMC "HAT mHealth Democratic Republic Congo"
12. **Barrett & Welburn HAT treatment review** (PMC) — landmark paper on treatment
13. **Atlas of HAT 2019 annual report** — `https://www.who.int/data/atlas-of-human-african-trypanosomiasis`

**Minimum coverage target:** 120,000 words (depth required — this supports PhD research)

---

## 5. Agent Integration Rules

### 5.1 Content Harvester — Coverage Verification Protocol

Before declaring any harvesting task complete, the Content Harvester **must**:

1. Count words indexed for the target domain in `library_fulltext` (query: `SELECT SUM(word_count) WHERE scope='ph_library' AND filename LIKE '%[domain-keyword]%' ...`)
2. Apply the coverage rubric from §3.1
3. If rating is `❌ Empty` or `⚠️ Weak`: search for and harvest 2+ additional sources from §4 before stopping
4. Produce a one-paragraph coverage note at the end of every harvesting session

**The Content Harvester must never stop harvesting a domain rated Empty or Weak without escalating to Metis for a decision.**

### 5.2 Course Builder — Mandatory Coverage Gate

Step 3 (Harvest) in the Course Builder workflow is extended with a mandatory gate:

```
3a. Harvest planned sources
3b. Run coverage check (§3 rubric)
3c. If any module domain is Empty or Weak → Gap-fill before proceeding to Step 4
3d. Produce coverage report (§3.3 template) and attach to course folder as coverage-report.md
```

A course cannot proceed to the Review step (Step 6) with any module rated `❌ Empty`.

### 5.3 Evaluation is mandatory after every run

After every batch download or harvesting session, produce the coverage report. Be honest:
- Do not round up ratings. A domain with 4,800 words is `❌ Weak`, not `⚠️ Moderate`.
- Image-only PDFs (≤1,500 words extracted) count as 0 for coverage purposes.
- Do not count the same document twice across domains.

---

## 6. Quick Reference: Priority Order for Gap-Filling

When time or bandwidth is limited, fill gaps in this order:

| Priority | Domain | Reason |
|---|---|---|
| 🔴 P1 | D22 HAT | Core PhD research domain |
| 🔴 P1 | D9 NTDs | Direct research relevance |
| 🟠 P2 | D4 Health Systems | WHO WHRs blocked; HTML available |
| 🟠 P2 | D8 Infectious Disease | Image PDFs need replacement |
| 🟠 P2 | D13 Mental Health | Empty, PMC open access available |
| 🟡 P3 | D3 Environmental | Empty, requires browser downloads |
| 🟡 P3 | D11 Nutrition | Empty, HTML sources available |
| 🟡 P3 | D16 Program Evaluation | Empty, W.K. Kellogg etc. accessible |
| 🟡 P3 | D20 One Health/AMR | Empty, O'Neill review accessible |
| 🟢 P4 | All others | Moderate or better |

---

*This document is maintained by Metis. Update the Current status line for each domain after every harvesting run. The coverage report generated by the pipeline (§3.3) is the authoritative state of the library.*
