#!/bin/bash
# download-library-ph-seed.sh
# Comprehensive open-access library seed for Metis_PH
# Covers full MPH + Global Health + NTDs + DHIS2 + Research Methods scope
# 176 resources across 19 domains
#
# DIRECT PDFs: downloaded automatically below
# [IRIS — browser download]: listed in MANUAL-DOWNLOADS.md
#
# Usage: bash download-library-ph-seed.sh
# Run from: metis/knowledge/library/

BASE="$(cd "$(dirname "$0")/open-access-books" && pwd)"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
PASS=0; FAIL=0

get() {
    local dest="$1" url="$2"
    if [ -f "$dest" ] && [ "$(stat -c%s "$dest")" -gt 10000 ]; then
        echo "  skip (exists): $(basename "$dest")"
        return
    fi
    [ -f "$dest" ] && rm -f "$dest"
    wget -q --timeout=60 --tries=2 --user-agent="$UA" -O "$dest" "$url" 2>/dev/null || true
    local size
    size=$(stat -c%s "$dest" 2>/dev/null || echo 0)
    if [ "$size" -gt 10000 ]; then
        echo "  ✓ $(( size / 1024 ))KB  $(basename "$dest")"
        PASS=$(( PASS + 1 ))
    else
        rm -f "$dest" 2>/dev/null || true
        echo "  ✗ FAILED ($(basename "$dest")) — add to MANUAL-DOWNLOADS.md"
        FAIL=$(( FAIL + 1 ))
    fi
}

mkdir -p \
  "$BASE/Epidemiology & Methods" \
  "$BASE/Biostatistics & Methods" \
  "$BASE/Health Systems & Financing" \
  "$BASE/Global Health Governance" \
  "$BASE/Social Determinants & Equity" \
  "$BASE/Environmental Health" \
  "$BASE/Infectious Disease & Surveillance" \
  "$BASE/NTDs - Overview" \
  "$BASE/NTDs - HAT" \
  "$BASE/NTDs - Malaria" \
  "$BASE/NTDs - TB" \
  "$BASE/NTDs - HIV" \
  "$BASE/NTDs - Schistosomiasis" \
  "$BASE/NTDs - Other" \
  "$BASE/Maternal & Child Health" \
  "$BASE/NCDs" \
  "$BASE/Nutrition & Food Security" \
  "$BASE/Mental Health" \
  "$BASE/Health Informatics & DHIS2" \
  "$BASE/Health Economics" \
  "$BASE/One Health & AMR" \
  "$BASE/Climate Change & Health" \
  "$BASE/Field Epidemiology" \
  "$BASE/Research Methods & Writing" \
  "$BASE/Spatial Epidemiology & Statistics" \
  "$BASE/Multilevel Models" \
  "$BASE/Africa & Sub-Saharan Africa" \
  "$BASE/Global Health & Health Systems" \
  "$BASE/HAT & NTDs" \
  "$BASE/Course Materials"

echo ""
echo "══════════════════════════════════════════════════════════════"
echo " Metis Library — Comprehensive PH Seed Download"
echo " $(date '+%Y-%m-%d')"
echo "══════════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════════
# 1. EPIDEMIOLOGY FOUNDATIONS
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[1/19] Epidemiology Foundations..."
D="$BASE/Epidemiology & Methods"

get "$D/CDC-SS1978-principles-of-epidemiology-3rd-ed.pdf" \
    "https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/SS1978.pdf"

get "$D/CDC-FETP-standard-core-curriculum.pdf" \
    "https://stacks.cdc.gov/view/cdc/29401/cdc_29401_DS1.pdf"

get "$D/CDC-FETP-programme-development-handbook.pdf" \
    "https://stacks.cdc.gov/view/cdc/29400/cdc_29400_DS1.pdf"

get "$D/CDC-MMWR-evaluating-surveillance-systems-2001.pdf" \
    "https://www.cdc.gov/mmwr/pdf/rr/rr5013a1.pdf"

get "$D/CDC-MMWR-framework-program-evaluation-1999.pdf" \
    "https://www.cdc.gov/mmwr/pdf/rr/rr4811.pdf"

get "$D/R-epicalc-epidemiological-data-analysis.pdf" \
    "https://cran.r-project.org/doc/contrib/Epicalc_Book.pdf"

get "$D/AFENET-field-epidemiology-training-manual.pdf" \
    "https://www.afenet.net/images/stories/pdf_files/FETP-Training-Manual.pdf"

get "$D/EpiRHandbook-offline-full.pdf" \
    "https://github.com/appliedepi/epiRhandbook_eng/releases/download/v1.0.1/epiRhandbook.pdf"

get "$D/IDSR-technical-guidelines-3rd-ed-WHO-AFRO.pdf" \
    "https://stacks.cdc.gov/view/cdc/12082/cdc_12082_DS1.pdf"

get "$D/CDC-intro-program-evaluation-self-study.pdf" \
    "https://stacks.cdc.gov/view/cdc/26235/cdc_26235_DS1.pdf"

# ═══════════════════════════════════════════════════════════════
# 2. BIOSTATISTICS & METHODS
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[2/19] Biostatistics & Methods..."
D="$BASE/Biostatistics & Methods"

get "$D/OpenStax-Introductory-Statistics-2e.pdf" \
    "https://assets.openstax.org/oscms-prodcms/media/documents/Introductory_Statistics_2e_-_WEB.pdf"

get "$D/Leyland-Multilevel-Modelling-Public-Health-SpringerOpen-2020.pdf" \
    "https://library.oapen.org/bitstream/id/013159f2-d58c-4af4-a368-d1c386426fca/2020_Book_MultilevelModellingForPublicHe.pdf"

get "$D/WHO-GBD-2021-DALY-methods.pdf" \
    "https://cdn.who.int/media/docs/default-source/gho-documents/global-health-estimates/ghe2021_daly_methods.pdf"

get "$D/WHO-World-Health-Statistics-2023.pdf" \
    "https://cdn.who.int/media/docs/default-source/gho-documents/world-health-statistic-reports/2023/world-health-statistics-2023_20230519_.pdf"

get "$D/WHO-GBD-2019-DALY-methods.pdf" \
    "https://www.who.int/docs/default-source/gho-documents/global-health-estimates/ghe2019_daly-methods.pdf"

get "$D/IHME-GBD-2017-policy-booklet.pdf" \
    "https://www.healthdata.org/sites/default/files/files/policy_report/2019/GBD_2017_Booklet.pdf"

get "$D/lme4-mixed-models-in-r-vignette-Bates.pdf" \
    "https://cran.r-project.org/web/packages/lme4/vignettes/lmer.pdf"

get "$D/Nakagawa-Schielzeth-R2-mixed-models-2013.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC3799170/pdf/"

get "$D/McNeish-small-samples-multilevel-models-2017.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC5769813/pdf/"

# ═══════════════════════════════════════════════════════════════
# 3. HEALTH SYSTEMS & FINANCING
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[3/19] Health Systems & Financing..."
D="$BASE/Health Systems & Financing"

get "$D/WHO-Monitoring-Building-Blocks-Health-Systems-2010.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/258734/9789241564052-eng.pdf"

get "$D/WorldBank-UHC-Inclusive-Sustainable-Development-2014.pdf" \
    "https://documents1.worldbank.org/curated/en/575211468278746561/pdf/888620PUB0REPL00Box385245B00PUBLIC0.pdf"

get "$D/WorldBank-Health-Systems-Analysis-Strengthening-2009.pdf" \
    "https://documents1.worldbank.org/curated/en/472131468331150352/pdf/659270WP0Healt00Box365730B00PUBLIC0.pdf"

get "$D/WorldBank-DCP3-Vol9-Improving-Health-Reducing-Poverty.pdf" \
    "https://www.ncbi.nlm.nih.gov/books/NBK525289/pdf/Bookshelf_NBK525289.pdf"

get "$D/WHO-Health-Financing-Dos-Donts-2019.pdf" \
    "https://p4h.world/app/uploads/2023/02/WHO19-0120health20financing20complete20low20res200922.x23411.pdf"

get "$D/WorldBank-Health-Systems-Financing-Revisited-2006.pdf" \
    "https://documents1.worldbank.org/curated/en/874011468313782370/pdf/370910Health0f101OFFICIAL0USE0ONLY1.pdf"

# ═══════════════════════════════════════════════════════════════
# 4. GLOBAL HEALTH GOVERNANCE
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[4/19] Global Health Governance..."
D="$BASE/Global Health Governance"

get "$D/WHO-Global-Digital-Health-Strategy-2020-2025.pdf" \
    "https://www.who.int/docs/default-source/documents/gs4dhdaa2a9f352b0445bafbc79ca799dce4d.pdf"

get "$D/WHO-Global-Strategy-Health-Environment-Climate-2020.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/331959/9789240000377-eng.pdf"

get "$D/ECDC-Long-Term-Surveillance-Framework-2021-2027.pdf" \
    "https://www.ecdc.europa.eu/sites/default/files/documents/long-term-surveillance-framework-2021-2027.pdf"

get "$D/ECDC-Rapid-Risk-Assessment-Methodology-Guidance-2011.pdf" \
    "https://www.ecdc.europa.eu/sites/default/files/media/en/publications/Publications/1108_TED_Risk_Assessment_Methodology_Guidance.pdf"

get "$D/CFR-Challenges-Global-Health-Governance-Garrett-2013.pdf" \
    "https://www.college-de-france.fr/media/dominique-kerouedan/UPL5475089948888627355_CFR_Governance_paper_IIGG_WorkingPaper4_GlobalHealth.pdf"

get "$D/WHO-WHO-Role-Global-Health-Governance-EB132.pdf" \
    "https://apps.who.int/gb/ebwha/pdf_files/eb132/b132_5add5-en.pdf"

# ═══════════════════════════════════════════════════════════════
# 5. SOCIAL DETERMINANTS & EQUITY
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[5/19] Social Determinants & Health Equity..."
D="$BASE/Social Determinants & Equity"

get "$D/WHO-CSDH-Closing-the-Gap-in-a-Generation-2008.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/43943/9789241563703_eng.pdf"

get "$D/Marmot-Fair-Society-Healthy-Lives-2010.pdf" \
    "https://www.drugsandalcohol.ie/20844/1/WHO_Marmot_final-report-in-english.pdf"

get "$D/WHO-Health-Environment-Climate-WHA72-2019.pdf" \
    "https://www.who.int/docs/default-source/climate-change/who-global-strategy-on-health-environment-and-climate-change-a72-15.pdf"

get "$D/WHO-Healthy-Environments-Healthier-Populations-2019.pdf" \
    "https://www.who.int/docs/default-source/environment-climate-change-and-health/health-environment-2019-easyprint.pdf"

# ═══════════════════════════════════════════════════════════════
# 6. ENVIRONMENTAL HEALTH
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[6/19] Environmental Health..."
D="$BASE/Environmental Health"

get "$D/WHO-Guidelines-Drinking-Water-Quality-4th-ed-2022.pdf" \
    "https://bdd.pseau.org/outils/ouvrages/who_guidelines_for_drinking_water_quality_4th_edition_2022.pdf"

get "$D/WHO-Guidance-Climate-Resilient-Healthcare-Facilities-2020.pdf" \
    "https://www.who.int/docs/default-source/climate-change/2833-phe-300920-electronic.pdf"

get "$D/WHO-Climate-Change-Human-Health-McMichael-2003.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/42742/924156248X_eng.pdf"

get "$D/WHO-WASH-Information-Sheet-2019.pdf" \
    "https://www.who.int/docs/default-source/documents/publications/information-sheet-wash.pdf"

get "$D/WHO-UNFCCC-Guidance-Protect-Health-Climate-Change-2018.pdf" \
    "https://unfccc.int/sites/default/files/resource/WHO_guidance_to_protect_health_from_climate_change.pdf"

get "$D/WHO-Antenatal-Care-Operational-Guide-2018.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/259947/WHO-RHR-18.02-eng.pdf"

# ═══════════════════════════════════════════════════════════════
# 7. INFECTIOUS DISEASE & SURVEILLANCE
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[7/19] Infectious Disease & Surveillance..."
D="$BASE/Infectious Disease & Surveillance"

get "$D/UNAIDS-Global-AIDS-Update-2024-Urgency-of-Now.pdf" \
    "https://www.unaids.org/sites/default/files/media_asset/2024-unaids-global-aids-update_en.pdf"

get "$D/UNAIDS-Global-AIDS-Update-2023-Path-That-Ends-AIDS.pdf" \
    "https://thepath.unaids.org/wp-content/themes/unaids2023/assets/files/2023_report.pdf"

get "$D/ECDC-Digital-Technologies-Infectious-Disease-Surveillance-2022.pdf" \
    "https://www.ecdc.europa.eu/sites/default/files/documents/Digital-technologies-in-infectious-disease-surveillance-prevention-and-control.pdf"

get "$D/ECDC-Wastewater-Based-Surveillance-Framework-2022.pdf" \
    "https://www.ecdc.europa.eu/sites/default/files/documents/wastewater-based-surveillance-framework.pdf"

get "$D/WHO-IDSR-3rd-Ed-Technical-Guidelines-2010.pdf" \
    "https://www.afro.who.int/sites/default/files/2017-06/IDSR-Technical-Guidelines_Final_2010_0.pdf"

get "$D/CDC-MMWR-Evaluating-Surveillance-Systems-guidelines-2001.pdf" \
    "https://www.cdc.gov/mmwr/pdf/rr/rr5013a1.pdf"

# ═══════════════════════════════════════════════════════════════
# 8. NTDs — OVERVIEW
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[8a/19] NTDs — Overview..."
D="$BASE/NTDs - Overview"

get "$D/WHO-NTD-Roadmap-2021-2030-targets-summary.pdf" \
    "https://cdn.who.int/media/docs/default-source/ntds/ntd-roadmap-targets-2021-2030.pdf"

get "$D/WHO-NTD-Roadmap-2021-2030-full.pdf" \
    "https://www.iapb.org/wp-content/uploads/2021/02/A-roadmapfor-neglected-tropical-diseases-2021-30-eng.pdf"

get "$D/DCP3-Vol6-Ch1-Major-Infectious-Diseases-Overview.pdf" \
    "https://www.dcp-3.org/sites/default/files/chapters/DCP3%20Major%20Infectious%20Diseases_Ch1.pdf"

get "$D/One-Health-Approach-NTDs-2021-2030-Mectizan.pdf" \
    "https://mectizan.org/wp-content/uploads/2022/02/One-health_approach-for-action-against-neglected-tropical-diseases-2021-2030.pdf"

get "$D/GHC-NTDs-Brief-2023.pdf" \
    "https://globalhealth.org/wp-content/uploads/2023/02/GHBB23NeglectedTropicalDiseasesBrief.pdf"

get "$D/WHO-Preventive-Chemotherapy-Human-Helminthiasis-2006.pdf" \
    "https://www.who.int/publications/b/31232"

get "$D/WHO-STH-Schistosomiasis-Prevention-Control-UNICEF-2002.pdf" \
    "https://www.taskforce.org/wp-content/uploads/2024/03/WHO-UNICEF-Prevention-of-STH-and-Schisto.pdf"

# ═══════════════════════════════════════════════════════════════
# 8b. NTDs — HAT
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[8b/19] NTDs — HAT..."
D="$BASE/NTDs - HAT"

get "$D/HAT-Frontiers-Current-Status-Review-2023.pdf" \
    "https://www.frontiersin.org/journals/tropical-diseases/articles/10.3389/fitd.2023.1087003/pdf"

# ═══════════════════════════════════════════════════════════════
# 8c. NTDs — Leishmaniasis
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[8c/19] NTDs — Leishmaniasis..."
D="$BASE/NTDs - Other"

get "$D/PAHO-WHO-Guideline-Leishmaniasis-Americas-2nd-2022.pdf" \
    "https://iris.paho.org/bitstream/handle/10665.2/49653/9789275120439_eng.pdf"

get "$D/WHO-Leishmaniasis-Vector-Control-Operational-Manual-LSHTM.pdf" \
    "https://researchonline.lshtm.ac.uk/id/eprint/4670580/7/WHO-2022-Operational-manual-on-leishmaniasis-vector.pdf"

# ═══════════════════════════════════════════════════════════════
# 8d. NTDs — Malaria
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[8d/19] Malaria..."
D="$BASE/NTDs - Malaria"
# Note: WHO malaria guides are IRIS — see MANUAL-DOWNLOADS.md
# Downloading what's accessible:
get "$D/WorldBank-DCP3-Vol6-Major-Infectious-Diseases-frontmatter.pdf" \
    "https://www.dcp-3.org/sites/default/files/volume_downloads/9781464805240_fm.pdf"

# ═══════════════════════════════════════════════════════════════
# 8e. NTDs — TB & HIV
# ═══════════════════════════════════════════════════════════════
# TB and HIV global reports are IRIS-hosted — listed in MANUAL-DOWNLOADS.md

# ═══════════════════════════════════════════════════════════════
# 9. MATERNAL & CHILD HEALTH
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[9/19] Maternal & Child Health..."
D="$BASE/Maternal & Child Health"

get "$D/WHO-Antenatal-Care-Recommendations-2016.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/250796/9789241549912-eng.pdf"

get "$D/WHO-Antenatal-Care-Operational-Guide-2018.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/259947/WHO-RHR-18.02-eng.pdf"

get "$D/WHO-Postnatal-Care-Highlights-2013-Guidelines.pdf" \
    "https://www.who.int/docs/default-source/mca-documents/nbh/brief-postnatal-care-for-mothers-and-newborns-highlights-from-the-who-2013-guidelines.pdf"

get "$D/Global-Nutrition-Report-2022.pdf" \
    "https://globalnutritionreport.org/documents/922/2022_Global_Nutrition_Report.pdf"

# ═══════════════════════════════════════════════════════════════
# 10. NCDs
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[10/19] NCDs..."
D="$BASE/NCDs"

get "$D/WHO-Global-NCD-Action-Plan-2013-2020.pdf" \
    "https://africahealthforum.afro.who.int/first-edition/IMG/pdf/global_action_plan_for_the_prevention_and_control_of_ncds_2013-2020.pdf"

get "$D/PAHO-NCD-Roadmap-2023-2030.pdf" \
    "https://www.paho.org/sites/default/files/2023-06/2ncd-roadmap.pdf"

get "$D/WHO-NCD-Cost-Effective-Interventions-Appendix3-2023.pdf" \
    "https://cdn.who.int/media/docs/default-source/ncds/mnd/2022-app3-technical-annex-v26jan2023.pdf"

# ═══════════════════════════════════════════════════════════════
# 11. NUTRITION & FOOD SECURITY
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[11/19] Nutrition & Food Security..."
D="$BASE/Nutrition & Food Security"

get "$D/SOFI-2023-State-of-Food-Security-Nutrition.pdf" \
    "https://data.unicef.org/wp-content/uploads/2023/07/SOFI-2023.pdf"

get "$D/Global-Nutrition-Report-2022.pdf" \
    "https://globalnutritionreport.org/documents/922/2022_Global_Nutrition_Report.pdf"

# ═══════════════════════════════════════════════════════════════
# 12. MENTAL HEALTH
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[12/19] Mental Health..."
D="$BASE/Mental Health"

get "$D/WHO-mhGAP-Intervention-Guide-v2-2016.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/250239/9789241549790-eng.pdf"

get "$D/WHO-mhGAP-Humanitarian-Intervention-Guide-2015.pdf" \
    "https://apps.who.int/iris/rest/bitstreams/721425/retrieve"

get "$D/WHO-Mental-Health-Atlas-2020.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/345946/9789240036703-eng.pdf"

get "$D/WHO-Comprehensive-Mental-Health-Action-Plan-2013-2030.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/272735/9789241514019-eng.pdf"

# ═══════════════════════════════════════════════════════════════
# 13. HEALTH INFORMATICS & DHIS2
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[13/19] Health Informatics & DHIS2..."
D="$BASE/Health Informatics & DHIS2"

get "$D/DHIS2-Implementation-Guide-2023.pdf" \
    "https://docs.dhis2.org/en/full/implement/dhis2-implementation-guide.pdf"

get "$D/WHO-RHIS-Toolkit-Analysis-Use-Routine-Health-Data-2021.pdf" \
    "https://cdn.who.int/media/docs/default-source/world-health-data-platform/rhis-modules/hdf-rhis-toolkit_feb2021_dissemination.pdf"

get "$D/DHIS2-Community-Health-Information-Systems-Guidelines-2018.pdf" \
    "https://www.ictworks.org/wp-content/uploads/2018/11/DHIS2_community-health-information-systems_Guidelines.pdf"

get "$D/DHIS2-Immunization-Resource-Guide-2020.pdf" \
    "https://s3-eu-west-1.amazonaws.com/content.dhis2.org/general/DHIS2+and+Immunization+Resource+Guide_June2020_Final.pdf"

get "$D/WHO-Global-Digital-Health-Strategy-2020-2025.pdf" \
    "https://www.who.int/docs/default-source/documents/gs4dhdaa2a9f352b0445bafbc79ca799dce4d.pdf"

get "$D/ECDC-Assessment-EHR-Infectious-Disease-Surveillance-2022.pdf" \
    "https://www.ecdc.europa.eu/sites/default/files/documents/assessment-electronic-health-records-for-infectious-disease-surveillance.pdf"

# ═══════════════════════════════════════════════════════════════
# 14. HEALTH ECONOMICS
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[14/19] Health Economics..."
D="$BASE/Health Economics"

get "$D/WHO-Health-Financing-Country-Diagnostic-2016.pdf" \
    "https://iris.who.int/bitstream/handle/10665/246136/9789241510097-eng.pdf"

get "$D/WorldBank-WDR-1993-Investing-in-Health.pdf" \
    "https://openknowledge.worldbank.org/bitstream/handle/10986/5976/WDR%201993%20-%20English.pdf"

get "$D/Norheim-Priority-Setting-Global-Health-2014.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC4098760/pdf/"

get "$D/Jamison-Global-Health-2035-Lancet.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC7159393/pdf/"

get "$D/CHEERS-2022-Reporting-Checklist.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC8793223/pdf/"

get "$D/Wagstaff-Poverty-and-Health-2002.pdf" \
    "https://openknowledge.worldbank.org/bitstream/handle/10986/15629/multi0page.pdf"

get "$D/WHO-GBD-Methods-DALY-2021.pdf" \
    "https://cdn.who.int/media/docs/default-source/gho-documents/global-health-estimates/ghe2021_daly_methods.pdf"

# ═══════════════════════════════════════════════════════════════
# 15. ONE HEALTH & AMR
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[15/19] One Health & AMR..."
D="$BASE/One Health & AMR"

get "$D/WOAH-Implementing-Global-Action-Plan-AMR-2024.pdf" \
    "https://www.woah.org/app/uploads/2024/01/implementing-the-global-action-plan-on-antimicrobial-resistance.pdf"

get "$D/One-Health-NTDs-2021-2030-Mectizan.pdf" \
    "https://mectizan.org/wp-content/uploads/2022/02/One-health_approach-for-action-against-neglected-tropical-diseases-2021-2030.pdf"

# ═══════════════════════════════════════════════════════════════
# 16. CLIMATE CHANGE & HEALTH
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[16/19] Climate Change & Health..."
D="$BASE/Climate Change & Health"

get "$D/WHO-COP29-Special-Report-Health-Climate-Action-2024.pdf" \
    "https://cdn.who.int/media/docs/default-source/environment-climate-change-and-health/58595-who-cop29-special-report_layout_9web.pdf"

get "$D/WHO-Global-Strategy-Health-Environment-Climate-2020.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/331959/9789240000377-eng.pdf"

get "$D/WHO-Guidance-Climate-Resilient-Sustainable-Healthcare-2020.pdf" \
    "https://www.who.int/docs/default-source/climate-change/2833-phe-300920-electronic.pdf"

get "$D/WHO-UNFCCC-Guidance-Protect-Health-Climate-2018.pdf" \
    "https://unfccc.int/sites/default/files/resource/WHO_guidance_to_protect_health_from_climate_change.pdf"

get "$D/McMichael-Climate-Change-Human-Health-WHO-2003.pdf" \
    "https://apps.who.int/iris/bitstream/handle/10665/42742/924156248X_eng.pdf"

# ═══════════════════════════════════════════════════════════════
# 17. FIELD EPIDEMIOLOGY & OUTBREAK RESPONSE
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[17/19] Field Epidemiology & Outbreak Response..."
D="$BASE/Field Epidemiology"

get "$D/CIFOR-Guidelines-Foodborne-Disease-Outbreak-Response-3ed-2014.pdf" \
    "https://cifor.us/downloads/clearinghouse/CIFOR-Guidelines-Complete-third-Ed.-FINAL.pdf"

get "$D/CDC-MMWR-Evaluating-Public-Health-Surveillance-Systems-2001.pdf" \
    "https://www.cdc.gov/mmwr/pdf/rr/rr5013a1.pdf"

get "$D/WHO-IDSR-Guidelines-3rd-Ed-2010-AFRO.pdf" \
    "https://www.afro.who.int/sites/default/files/2017-06/IDSR-Technical-Guidelines_Final_2010_0.pdf"

get "$D/CDC-FETP-Standard-Core-Curriculum.pdf" \
    "https://stacks.cdc.gov/view/cdc/29401/cdc_29401_DS1.pdf"

get "$D/AFENET-FETP-Training-Manual.pdf" \
    "https://www.afenet.net/images/stories/pdf_files/FETP-Training-Manual.pdf"

get "$D/ECDC-Field-Epidemiology-Manual-Surveillance-Chapter.pdf" \
    "https://www.ecdc.europa.eu/sites/default/files/documents/fem-surveillance-methods-and-interpretation.pdf"

# ═══════════════════════════════════════════════════════════════
# 18. RESEARCH METHODS & SCIENTIFIC WRITING
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[18/19] Research Methods & Scientific Writing..."
D="$BASE/Research Methods & Writing"

get "$D/OpenStax-Introductory-Statistics-2e.pdf" \
    "https://assets.openstax.org/oscms-prodcms/media/documents/Introductory_Statistics_2e_-_WEB.pdf"

get "$D/Leyland-Multilevel-Modelling-Public-Health-SpringerOpen-2020.pdf" \
    "https://library.oapen.org/bitstream/id/013159f2-d58c-4af4-a368-d1c386426fca/2020_Book_MultilevelModellingForPublicHe.pdf"

get "$D/R-Epicalc-Epidemiological-Data-Analysis.pdf" \
    "https://cran.r-project.org/doc/contrib/Epicalc_Book.pdf"

get "$D/NOU-Research-Methods-Public-Health-Graduate-Notes.pdf" \
    "https://nou.edu.ng/coursewarecontent/PHS%20805%20RESEARCH%20METHODSIN%20PUBLIC%20HEALTH.pdf"

get "$D/EpiRHandbook-offline-full.pdf" \
    "https://github.com/appliedepi/epiRhandbook_eng/releases/download/v1.0.1/epiRhandbook.pdf"

get "$D/CDC-Framework-Program-Evaluation-MMWR-1999.pdf" \
    "https://www.cdc.gov/mmwr/pdf/rr/rr4811.pdf"

# ═══════════════════════════════════════════════════════════════
# 19. SPATIAL EPIDEMIOLOGY (keep existing + add new)
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[19/19] Spatial Epidemiology & Statistics..."
D="$BASE/Spatial Epidemiology & Statistics"

get "$D/Lovelace-Geocomputation-with-R.pdf" \
    "https://r.geocompx.org/geocompr.pdf"

get "$D/SaTScan-Users-Guide-v10.pdf" \
    "https://www.satscan.org/cgi-bin/satscan/register.pl/SaTScan_Users_Guide.pdf"

get "$D/Besag-York-Mollie-BYM-1991.pdf" \
    "https://link.springer.com/content/pdf/10.1007/BF00116466.pdf"

get "$D/Kulldorff-Spatial-Scan-Statistic-1997.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC2279481/pdf/"

get "$D/Riebler-BYM2-Disease-Mapping-2016.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC4985630/pdf/"

get "$D/Robertson-Space-Time-Disease-Surveillance-2020.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC7185413/pdf/"

get "$D/Alkhamis-Spatial-Temporal-Clustering-2020.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC7120538/pdf/"

get "$D/Elliott-Wartenberg-Spatial-Epi-Challenges-2004.pdf" \
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC1247193/pdf/"

# ═══════════════════════════════════════════════════════════════
# BONUS: Course Materials
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[Bonus] Course Materials..."
D="$BASE/Course Materials"

get "$D/CDC-SS1978-Principles-of-Epidemiology-3rd-ed.pdf" \
    "https://archive.cdc.gov/www_cdc_gov/csels/dsepd/ss1978/SS1978.pdf"

get "$D/Gelman-BDA3-Bayesian-Data-Analysis-3rd-ed.pdf" \
    "http://www.stat.columbia.edu/~gelman/book/BDA3.pdf"

get "$D/lme4-Bates-Mixed-Models-R-vignette.pdf" \
    "https://cran.r-project.org/web/packages/lme4/vignettes/lmer.pdf"

get "$D/EpiRHandbook-offline-full.pdf" \
    "https://github.com/appliedepi/epiRhandbook_eng/releases/download/v1.0.1/epiRhandbook.pdf"

get "$D/DHIS2-Implementation-Guide-2023.pdf" \
    "https://docs.dhis2.org/en/full/implement/dhis2-implementation-guide.pdf"

get "$D/OpenStax-Introductory-Statistics-2e.pdf" \
    "https://assets.openstax.org/oscms-prodcms/media/documents/Introductory_Statistics_2e_-_WEB.pdf"

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════════════════════════"
echo " Download complete. Counting results..."
echo "══════════════════════════════════════════════════════════════"

TOTAL=0; DOWNLOADED=0
while IFS= read -r -d '' f; do
    TOTAL=$((TOTAL + 1))
    size=$(stat -c%s "$f" 2>/dev/null || echo 0)
    [ "$size" -gt 10000 ] && DOWNLOADED=$((DOWNLOADED + 1))
done < <(find "$BASE" -name "*.pdf" -print0)

TOTAL_MB=$(du -sm "$BASE" 2>/dev/null | cut -f1)
echo ""
echo "  Files found:      $TOTAL"
echo "  Real PDFs:        $DOWNLOADED"
echo "  Library size:     ${TOTAL_MB} MB"
echo ""
echo "  For WHO IRIS files that couldn't be downloaded automatically:"
echo "  → See knowledge/library/MANUAL-DOWNLOADS.md"
echo ""
echo "  Next step: run index_library_pdfs() in MCP to embed all PDFs"
echo "════════════════════════════════════════════════════════════════"
