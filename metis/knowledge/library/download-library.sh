#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  Metis Knowledge Library — PDF Batch Downloader
#  Generated: 2026-05-13
#
#  Run from the Research Cortex root:
#    cd "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex"
#    bash metis/knowledge/library/download-library.sh
#
#  Items already downloaded are skipped (wget -c / -nc flags).
#  Items marked [MANUAL] need a browser — URL goes to a page, not a direct PDF.
#  Items marked [BORROW] require a free archive.org account.
#  Items marked [PAYWALLED] require institutional access — not included.
# ═══════════════════════════════════════════════════════════════════════════

BASE="metis/knowledge/library/open-access-books"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DL="wget -c -nc --timeout=60 --tries=3 --user-agent=\"$UA\""

mkdir -p "$BASE/HAT & NTDs"
mkdir -p "$BASE/Epidemiology & Methods"
mkdir -p "$BASE/Global Health & Health Systems"
mkdir -p "$BASE/Africa"
mkdir -p "$BASE/Health Economics"
mkdir -p "$BASE/Spatial Epidemiology & Statistics"
mkdir -p "$BASE/Multilevel Models"
mkdir -p "$BASE/Course Materials"

echo "══════════════════════════════════════════"
echo " Metis Library Downloader — 2026-05-13"
echo "══════════════════════════════════════════"
echo ""


# ── HAT & NTDs ──────────────────────────────────────────────────────────────
echo "[1/8] HAT & NTDs..."
cd "$BASE/HAT & NTDs"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "02_WHO-HAT-TRS-984-2013.pdf" \
  "https://apps.who.int/iris/bitstream/handle/10665/95732/9789241209847_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "03_WHO-HAT-fexinidazole-guidelines-2019.pdf" \
  "https://iris.who.int/bitstream/handle/10665/326178/9789241550567-eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "08_HAT-epidemiology-diagnosis-treatment-PMC2024.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC11210952/pdf/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "11_WHO-NTD-roadmap-2021-2030.pdf" \
  "https://iris.who.int/bitstream/handle/10665/338565/9789240010352-eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "15_NTDs-neglected-infections-poverty-Hotez-2011.pdf" \
  "https://www.ncbi.nlm.nih.gov/books/NBK62521/pdf/Bookshelf_NBK62521.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "17_DCP3-investment-case-ending-NTDs.pdf" \
  "https://www.dcp-3.org/sites/default/files/chapters/DCP3%20Major%20Infectious%20Diseases_Ch1.pdf"

# [MANUAL] Item 09 — WHO/FAO Vector Control HAT 2021
#   https://www.who.int/publications/i/item/9789240051867
# [MANUAL] Item 13 — WHO Global Report NTDs 2024
#   https://www.who.int/teams/control-of-neglected-tropical-diseases/global-report-on-neglected-tropical-diseases-2024
# [MANUAL] Item 14 — WHO Global Report NTDs 2023
#   https://www.who.int/teams/control-of-neglected-tropical-diseases/global-report-on-neglected-tropical-diseases-2023
# [BORROW] Item 07 — Progress in HAT, Sleeping Sickness (Dumas et al.)
#   https://archive.org/details/progressinhumana0000unse
# [BORROW] Item 16 — Forgotten People, Forgotten Diseases (Hotez)
#   https://archive.org/details/forgottenpeoplef0000hote

cd - > /dev/null


# ── Epidemiology & Methods ───────────────────────────────────────────────────
echo "[2/8] Epidemiology & Methods..."
cd "$BASE/Epidemiology & Methods"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "19_Dowdle-principles-disease-elimination-1998.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC2305684/pdf/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "36_WHO-basic-epidemiology-2nd-ed-2006.pdf" \
  "https://iris.who.int/bitstream/handle/10665/43541/9241547073_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "37_Foundations-of-Epidemiology-OregonState-2020.pdf" \
  "https://open.oregonstate.education/epidemiology/wp-content/uploads/sites/7/2020/01/Foundations-of-Epidemiology_Bovbjerg.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "48_WHO-communicable-disease-surveillance-guide-2006.pdf" \
  "https://iris.who.int/bitstream/handle/10665/69331/WHO_CDS_EPR_LYO_2006_2_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "50_IHR-2005-international-health-regulations-3rd-ed.pdf" \
  "https://iris.who.int/bitstream/handle/10665/246107/9789241580496-eng.pdf"

# [BORROW] Item 39 — Modern Epidemiology (Rothman, 1st/2nd ed)
#   https://archive.org/details/modernepidemiolo0000roth
# [BORROW] Item 40 — Epidemiology: An Introduction (Rothman, 2002)
#   https://archive.org/details/epidemiology00kenn
# [PAYWALLED] Item 41 — Epidemiology: Beyond the Basics (Szklo & Nieto)

cd - > /dev/null


# ── Global Health & Health Systems ──────────────────────────────────────────
echo "[3/8] Global Health & Health Systems..."
cd "$BASE/Global Health & Health Systems"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "26_DCP3-vol9-improving-health-reducing-poverty.pdf" \
  "https://www.ncbi.nlm.nih.gov/books/NBK525289/pdf/Bookshelf_NBK525289.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "27_DCP3-vol6-major-infectious-diseases.pdf" \
  "https://www.ncbi.nlm.nih.gov/books/NBK525192/pdf/Bookshelf_NBK525192.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "30_WHO-world-health-statistics-2024.pdf" \
  "https://iris.who.int/bitstream/handle/10665/376869/9789240094703-eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "62_WHO-world-health-report-2000-health-systems.pdf" \
  "https://iris.who.int/bitstream/handle/10665/42281/WHR00_en.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "63_WHO-world-health-report-2010-health-financing.pdf" \
  "https://iris.who.int/bitstream/handle/10665/44371/9789241564021_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "64_WHO-everybodys-business-health-systems-2007.pdf" \
  "https://iris.who.int/bitstream/handle/10665/43432/9789241596077_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "65_WHO-making-fair-choices-UHC-2014.pdf" \
  "https://iris.who.int/bitstream/handle/10665/112671/9789241507509_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "66_CSDH-Marmot-closing-gap-health-equity-2008.pdf" \
  "https://iris.who.int/bitstream/handle/10665/43943/9789241563703_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "67_WHO-world-health-report-2008-primary-health-care.pdf" \
  "https://iris.who.int/bitstream/handle/10665/44093/9789241563734_eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "69_Kruk-high-quality-health-systems-SDGs-2018.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC6237506/pdf/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "71_Kutzin-health-financing-UHC-2013.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC3748748/pdf/"

# [BORROW] Item 68 — Getting Health Reform Right (Roberts et al.)
#   https://archive.org/details/gettinghealthref0000robe

cd - > /dev/null


# ── Africa ───────────────────────────────────────────────────────────────────
echo "[4/8] Africa..."
cd "$BASE/Africa"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "58_Africa-CDC-annual-report-2023.pdf" \
  "https://africacdc.org/download/annual-report-2023-realizing-africa-cdcs-autonomy-making-measurable-impact-in-africas-health-security/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "59_Africa-CDC-strategic-plan-2023-2027.pdf" \
  "https://africacdc.org/download/africa-cdc-strategic-plan-2023-2027/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "60_WHO-AFRO-resilient-health-systems-framework-2023-2030.pdf" \
  "https://www.afro.who.int/sites/default/files/2023-07/AFR-RC73-5-Framework%20for%20sustaining%20resilient%20health%20systems%20to%20achieve%20universal%20health%20coverage%20and%20security%202023%E2%80%932030.pdf"

cd - > /dev/null


# ── Health Economics ─────────────────────────────────────────────────────────
echo "[5/8] Health Economics..."
cd "$BASE/Health Economics"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "31_WHO-guide-cost-effectiveness-analysis-2003.pdf" \
  "https://iris.who.int/bitstream/handle/10665/42699/9241546018.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "35_CHEERS-2022-reporting-checklist.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC8793223/pdf/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "70_WHO-health-financing-country-diagnostic-2016.pdf" \
  "https://iris.who.int/bitstream/handle/10665/246136/9789241510097-eng.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "72_World-Bank-WDR-1993-investing-in-health.pdf" \
  "https://openknowledge.worldbank.org/bitstream/handle/10986/5976/WDR%201993%20-%20English.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "73_Jamison-global-health-2035-lancet.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC7159393/pdf/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "74_Wagstaff-poverty-and-health-2002.pdf" \
  "https://openknowledge.worldbank.org/bitstream/handle/10986/15629/multi0page.pdf"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "75_Norheim-priority-setting-global-health-2014.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC4098760/pdf/"

# [BORROW] Item 33 — Methods for Economic Evaluation (Drummond, 3rd ed)
#   https://archive.org/details/methodsforeconom0000unse

cd - > /dev/null


# ── Spatial Epidemiology & Statistics (NEW) ──────────────────────────────────
echo "[6/8] Spatial Epidemiology & Statistics (new)..."
cd "$BASE/Spatial Epidemiology & Statistics"

# Spatial articles already in master list (PMC open access)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "44_Robertson-space-time-disease-surveillance-review-2020.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC7185413/pdf/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "45_Alkhamis-spatial-temporal-clustering-2020.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC7120538/pdf/"

wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "46_Elliott-Wartenberg-spatial-epidemiology-challenges-2004.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC1247193/pdf/"

# NEW: Geocomputation with R — Lovelace, Nowosad, Muenchow (free online book)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "NEW_Lovelace-geocomputation-with-r.pdf" \
  "https://r.geocompx.org/geocompr.pdf"

# NEW: WHO Health Mapping and GIS in Epidemiology (2002, foundational WHO guide)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "NEW_WHO-health-mapping-GIS-epidemiology-2002.pdf" \
  "https://iris.who.int/bitstream/handle/10665/42483/9241545577.pdf"

# NEW: SaTScan User Guide v10 (Kulldorff — always keep the official manual)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "NEW_SaTScan-user-guide-v10.pdf" \
  "https://www.satscan.org/cgi-bin/satscan/register.pl/SaTScan_Users_Guide.pdf"

# NEW: Disease Mapping with WinBUGS and MLwiN — Lawson et al. chapter excerpts
# [PAYWALLED] Lawson "Bayesian Disease Mapping" 3rd ed (CRC Press, 2018)
# [PAYWALLED] Waller & Gotway "Applied Spatial Statistics for Public Health Data" (Wiley, 2004)
# [PAYWALLED] Pfeiffer "Spatial Analysis in Epidemiology" (OUP, 2008) — see item 43

# NEW: Kulldorff 1997 foundational spatial scan statistic paper (PMC)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "NEW_Kulldorff-spatial-scan-statistic-1997.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC2279481/pdf/"

# NEW: Riebler BYM2 paper — disease mapping (PMC)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "NEW_Riebler-BYM2-disease-mapping-2016.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC4985630/pdf/"

# NEW: Besag York Mollie 1991 — the original BYM paper (Springer link, open)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "NEW_Besag-York-Mollie-BYM-1991.pdf" \
  "https://link.springer.com/content/pdf/10.1007/BF00116466.pdf"

# NEW: Moraga 2019 — Small Area Disease Risk with R-INLA (Chapter 1 preprint)
# Full book at https://www.paulamoraga.com/book-geospatial/ (HTML — read online)
# Full book at https://www.paulamoraga.com/book-spatial/ (HTML — read online)

cd - > /dev/null


# ── Multilevel Models (NEW) ───────────────────────────────────────────────────
echo "[7/8] Multilevel Models (new)..."
cd "$BASE/Multilevel Models"

# NEW: Gelman "Bayesian Data Analysis" 3rd ed — free PDF from Gelman's site
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "Gelman-BDA3-bayesian-data-analysis-3rd-ed.pdf" \
  "http://www.stat.columbia.edu/~gelman/book/BDA3.pdf"

# NEW: McNeish 2017 — thanks for the memories: the need for random effects in MLM (PMC)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "McNeish-small-samples-multilevel-models-2017.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC5769813/pdf/"

# NEW: Maas & Hox 2005 — sufficient sample sizes for MLM (open access)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "Maas-Hox-sample-sizes-multilevel-models-2005.pdf" \
  "https://www.metodologiadelainvestigacion.nl/files/Maas%20Hox%202005%20Sufficient%20sample%20sizes%20for%20multilevel.pdf"

# NEW: Hox JJ "Multilevel Analysis" 3rd ed (2018) — Routledge OPEN ACCESS
# Cannot be wget'd directly; download manually at:
#   https://www.routledge.com/Multilevel-Analysis-Techniques-and-Applications-Third-Edition/Hox-Moerbeek-van-de-Schoot/p/book/9781138121362
# Then click "Preview / Open Access PDF" or go to:
#   https://www.taylorfrancis.com/books/oa/10.4324/9781315650982
echo "[MANUAL] Hox Multilevel Analysis 3rd ed — visit:"
echo "  https://www.taylorfrancis.com/books/oa/10.4324/9781315650982"

# NEW: Snijders & Bosker "Multilevel Analysis" 2nd ed (2012) — Sage, paywalled
# [PAYWALLED] Buy or borrow via institutional library

# NEW: Raudenbush & Bryk "Hierarchical Linear Models" 2nd ed — Sage, paywalled
# [PAYWALLED]

# NEW: Verbeke & Molenberghs "Linear Mixed Models for Longitudinal Data" — Springer
# [PAYWALLED]

# NEW: Introduction to mixed models — free R tutorial (Bates et al. lme4 vignette)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "Bates-lme4-mixed-models-in-r-vignette.pdf" \
  "https://cran.r-project.org/web/packages/lme4/vignettes/lmer.pdf"

# NEW: Nakagawa & Schielzeth 2013 — R² for mixed models (influential paper, PMC)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "Nakagawa-Schielzeth-R2-mixed-models-2013.pdf" \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC3799170/pdf/"

cd - > /dev/null


# ── Course Materials (NEW) ────────────────────────────────────────────────────
echo "[8/8] Course Materials (new)..."
cd "$BASE/Course Materials"

# CDC Principles of Epidemiology in Public Health Practice (SS1978)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "CDC-SS1978-principles-of-epidemiology-self-study.pdf" \
  "https://stacks.cdc.gov/view/cdc/13178/cdc_13178_DS1.pdf"

# WHO Public Health Intelligence Competency Framework 2024
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "WHO-public-health-intelligence-competency-framework.pdf" \
  "https://iris.who.int/bitstream/handle/10665/374574/9789240083295-eng.pdf"

# WHO PHI Curriculum
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "WHO-public-health-intelligence-curriculum.pdf" \
  "https://iris.who.int/bitstream/handle/10665/365842/9789240072633-eng.pdf"

# WHO Vaccination Coverage Cluster Survey manual
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "WHO-vaccination-coverage-cluster-surveys-manual.pdf" \
  "https://iris.who.int/bitstream/handle/10665/272512/WHO-IVB-18.09-eng.pdf"

# ECDC Field Epidemiology Manual (open access chapters via ECDC)
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "ECDC-field-epidemiology-manual-surveillance-chapter.pdf" \
  "https://www.ecdc.europa.eu/sites/default/files/documents/fem-surveillance-methods-and-interpretation.pdf"

# OpenWHO Outbreak Investigation course materials
# [MANUAL] https://openwho.org/courses/outbreak-investigation — enrol free
# [MANUAL] https://openwho.org/courses/introduction-to-go-data — enrol free

# WHO Field Guide to Epidemic Investigation
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "WHO-field-guide-epidemic-investigation.pdf" \
  "https://iris.who.int/bitstream/handle/10665/37255/9241544899.pdf"

# AFENET Field Epidemiology Training Manual
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "AFENET-field-epidemiology-training-manual.pdf" \
  "https://www.afenet.net/images/stories/pdf_files/FETP-Training-Manual.pdf"

# Epi R Handbook — condensed PDF snapshot
wget -c -nc --timeout=60 --tries=3 --user-agent="$UA" \
  -O "EpiRHandbook-offline-full.pdf" \
  "https://github.com/appliedepi/epiRhandbook_eng/releases/download/v1.0.1/epiRhandbook.pdf"

cd - > /dev/null


echo ""
echo "══════════════════════════════════════════"
echo " Download complete."
echo ""
echo " Manual downloads needed (browser required):"
echo "   • Hox MLM 3rd ed:  https://www.taylorfrancis.com/books/oa/10.4324/9781315650982"
echo "   • WHO NTD Report 2024: https://www.who.int/teams/control-of-neglected-tropical-diseases/global-report-on-neglected-tropical-diseases-2024"
echo "   • WHO NTD Report 2023: https://www.who.int/teams/control-of-neglected-tropical-diseases/global-report-on-neglected-tropical-diseases-2023"
echo "   • WHO/FAO HAT Vector Control: https://www.who.int/publications/i/item/9789240051867"
echo "   • OpenWHO courses: https://openwho.org"
echo "   • Moraga Geospatial Health Data: https://www.paulamoraga.com/book-geospatial/"
echo "   • Moraga Spatial Stats for DS:  https://www.paulamoraga.com/book-spatial/"
echo ""
echo " Borrow on archive.org (free account):"
echo "   • Rothman Modern Epidemiology: https://archive.org/details/modernepidemiolo0000roth"
echo "   • Rothman Epidemiology Intro:  https://archive.org/details/epidemiology00kenn"
echo "   • Drummond Health Economics:   https://archive.org/details/methodsforeconom0000unse"
echo "   • Lawson Spatial Epidemiology: https://archive.org/details/statisticalmetho0000laws_h4z8"
echo "   • Hotez Forgotten Diseases:    https://archive.org/details/forgottenpeoplef0000hote"
echo ""
echo " Paywalled (institutional library):"
echo "   • Szklo & Nieto — Epidemiology: Beyond the Basics"
echo "   • Pfeiffer — Spatial Analysis in Epidemiology"
echo "   • Lawson — Bayesian Disease Mapping 3rd ed (CRC)"
echo "   • Waller & Gotway — Applied Spatial Stats for Public Health (Wiley)"
echo "   • Snijders & Bosker — Multilevel Analysis 2nd ed (Sage)"
echo "   • Raudenbush & Bryk — Hierarchical Linear Models (Sage)"
echo "══════════════════════════════════════════"
