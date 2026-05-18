"""
seed_mockup_demo.py — Populate Metis with realistic demo data for screenshots.

Researcher persona: Dr. Amélie Fontaine
  Role: Senior Epidemiologist, Institut de Médecine Tropicale (IMT Lyon)
  Focus: HAT surveillance · DHIS2 · multilevel spatial models
  Projects: HAT surveillance DRC, DHIS2 facility mapping, PhD thesis, malaria resistance

Usage:
    python seed_mockup_demo.py                          # seed live DB
    python seed_mockup_demo.py --db /path/to/other.db  # seed a copy
    python seed_mockup_demo.py --reset                 # wipe and reseed

This script is safe to re-run — all inserts use INSERT OR REPLACE.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "metis" / "system" / "app" / "data" / "metis.sqlite"
CONFIG_DIR = REPO_ROOT / "metis" / "system" / "config"

TODAY = datetime.now()
D = lambda d: (TODAY - timedelta(days=d)).strftime("%Y-%m-%d")
DT = lambda d, h=8: (TODAY - timedelta(days=d)).replace(hour=h, minute=0).strftime("%Y-%m-%d %H:%M:%S")
FUTURE = lambda d: (TODAY + timedelta(days=d)).strftime("%Y-%m-%d")


def seed(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row

    # ── User config ────────────────────────────────────────────────────────────
    prefs = {
        "display_name": "Amélie",
        "role": "Senior Epidemiologist · Neglected Tropical Diseases",
        "interests": ["sleeping sickness", "HAT", "neglected tropical diseases",
                      "DHIS2", "multilevel models", "spatial epidemiology",
                      "disease burden", "health information systems", "West Africa"],
        "news_topics": ["WHO NTD roadmap", "sleeping sickness elimination",
                        "DHIS2 updates", "epidemiology methods", "AI in global health",
                        "DRC health system", "malaria drug resistance"],
        "pubmed_query": "human African trypanosomiasis[Title] OR sleeping sickness[Title] OR NTD[Title/Abstract]",
        "active_model": "sonnet",
        "theme": "light",
        "density": "comfortable",
    }

    user_config = {
        "user": {
            "name": "Amélie Fontaine",
            "role": "Senior Epidemiologist",
            "language": "en",
            "general_context": (
                "Senior epidemiologist specialising in neglected tropical diseases, "
                "particularly human African trypanosomiasis (HAT). Based at IMT Lyon. "
                "Three-article PhD in progress: surveillance (article 1 submitted), "
                "methods (article 2 in preparation), policy (article 3 planned)."
            ),
            "active_contexts": ["general", "NTD surveillance", "DHIS2"],
            "specialist_contexts": [
                {"name": "NTD surveillance", "description": "HAT, sleeping sickness, DRC disease burden analysis"},
                {"name": "DHIS2", "description": "DHIS2 metadata design, tracker programs, NTD implementation"},
                {"name": "Spatial epidemiology", "description": "Multilevel models, kriging, health facility mapping"},
            ],
        },
        "research": {
            "field": "Public health · Epidemiology",
            "interests": ["neglected tropical diseases", "HAT", "DHIS2", "multilevel models", "spatial epidemiology"],
            "specific_focus": "HAT surveillance in DRC, DHIS2 NTD module implementation, spatial disease burden",
        },
        "data_sensitivity": {"patient_data": True, "embargoed_results": True, "compliance": ["GDPR", "DRC MoH ethics"]},
    }

    prefs_path = CONFIG_DIR / "user-preferences.json"
    prefs_path.write_text(json.dumps(prefs, indent=2, ensure_ascii=False))

    try:
        import yaml
        config_path = CONFIG_DIR / "user-config.yaml"
        with config_path.open("w") as f:
            yaml.dump(user_config, f, default_flow_style=False, allow_unicode=True)
    except ImportError:
        pass  # yaml not installed — skip

    # ── Projects ───────────────────────────────────────────────────────────────
    projects = [
        {
            "project_id": "proj-HAT-001",
            "title": "Article 1 — HAT Surveillance DRC 2015–2023",
            "description": "Retrospective analysis of HAT incidence trends in DRC. 8 health zones, 3,400 cases. R/INLA spatial model. Submitted to Lancet ID.",
            "domain": "Neglected Tropical Diseases",
            "status": "active",
            "priority": "high",
            "next_step": "Revise Figure 3 — reviewer asked for district-level breakdown by year",
            "external_path": "C:/Users/Amelie/Documents/research/article1-HAT-DRC",
            "github_url": "https://github.com/amefontaine/hat-drc-surveillance",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amelie/Documents/research/article1-HAT-DRC/analysis.Rproj"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/research/article1-HAT-DRC"},
                {"label": "GitHub", "type": "github", "url": "https://github.com/amefontaine/hat-drc-surveillance"},
            ]),
            "created_at": DT(180),
        },
        {
            "project_id": "proj-DHIS2-002",
            "title": "DHIS2 NTD Module — DRC Ministry of Health",
            "description": "Implementation of DHIS2 tracker program for HAT passive surveillance across 5 provinces. Aggregate reporting + case-level tracker.",
            "domain": "Health Information Systems",
            "status": "active",
            "priority": "high",
            "next_step": "Finalize metadata mapping for health facility coordinates — 247 facilities pending GPS entry",
            "external_path": "C:/Users/Amelie/Documents/dhis2-ntd-drc",
            "github_url": "https://github.com/amefontaine/dhis2-ntd-tracker",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open in VS Code", "type": "vscode", "path": "C:/Users/Amelie/Documents/dhis2-ntd-drc"},
                {"label": "DHIS2 Dev Instance", "type": "url", "url": "http://localhost:8080/dhis-web-app"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/dhis2-ntd-drc"},
            ]),
            "created_at": DT(90),
        },
        {
            "project_id": "proj-PHD-003",
            "title": "PhD Thesis — NTD Burden & Surveillance Systems",
            "description": "Three-article PhD. Article 1 submitted (Lancet ID). Article 2 in preparation: multilevel model of HAT risk factors. Article 3 planned: policy implications of elimination.",
            "domain": "Research",
            "status": "active",
            "priority": "high",
            "next_step": "Write Article 2 methods section — INLA model specification for spatial random effects",
            "external_path": "C:/Users/Amelie/Documents/phd-thesis",
            "github_url": "",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open Thesis Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/phd-thesis"},
                {"label": "Article 2 Draft", "type": "vscode", "path": "C:/Users/Amelie/Documents/phd-thesis/article2"},
                {"label": "Overleaf", "type": "url", "url": "https://www.overleaf.com/project/hat-article2"},
            ]),
            "created_at": DT(730),
        },
        {
            "project_id": "proj-MAL-004",
            "title": "Malaria Drug Resistance — West Africa Sentinel Sites",
            "description": "Multi-country analysis of P. falciparum artemisinin partial resistance markers. 14 sentinel sites, 6 countries. Collaboration with NMCP partners.",
            "domain": "Malaria",
            "status": "active",
            "priority": "medium",
            "next_step": "Data cleaning script: harmonise site codes across 6 country datasets",
            "external_path": "C:/Users/Amelie/Documents/malaria-resistance-wa",
            "github_url": "https://github.com/amefontaine/malaria-resistance-wa",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amelie/Documents/malaria-resistance-wa/analysis.Rproj"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/malaria-resistance-wa"},
            ]),
            "created_at": DT(60),
        },
        {
            "project_id": "proj-TEACH-005",
            "title": "Course: Epidemiology for Digital Health",
            "description": "New graduate course for MPH students. 9 modules: disease burden, surveillance design, DHIS2, spatial methods, policy translation. First delivery: March 2027.",
            "domain": "Teaching",
            "status": "active",
            "priority": "low",
            "next_step": "Draft Module 4 outline: spatial epidemiology methods with QGIS exercises",
            "external_path": "C:/Users/Amelie/Documents/courses/epi-digital-health",
            "github_url": "",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open Course Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/courses/epi-digital-health"},
                {"label": "VS Code", "type": "vscode", "path": "C:/Users/Amelie/Documents/courses/epi-digital-health"},
            ]),
            "created_at": DT(30),
        },
    ]

    for p in projects:
        conn.execute("""
            INSERT OR REPLACE INTO projects
            (project_id, title, description, domain, status, priority, next_step,
             external_path, github_url, launcher_type, launchers, created_at)
            VALUES (:project_id, :title, :description, :domain, :status, :priority,
                    :next_step, :external_path, :github_url, :launcher_type, :launchers, :created_at)
        """, p)

    # ── Tasks ─────────────────────────────────────────────────────────────────
    tasks = [
        # Article 1
        {"task_id": "task-001", "project_id": "proj-HAT-001", "title": "Revise Figure 3 — district breakdown by year", "status": "open", "due_date": D(0), "category": "writing", "notes": "Reviewer 2 asked for year-stratified map. Use ggplot2 facet_wrap."},
        {"task_id": "task-002", "project_id": "proj-HAT-001", "title": "Update supplement table S3 with 2023 data", "status": "open", "due_date": D(2), "category": "analysis", "notes": ""},
        {"task_id": "task-003", "project_id": "proj-HAT-001", "title": "Respond to Reviewer 1 comments on case definition", "status": "open", "due_date": FUTURE(3), "category": "writing", "notes": "Reviewer wants CATT sensitivity noted in limitations"},
        {"task_id": "task-004", "project_id": "proj-HAT-001", "title": "Re-run INLA model with updated 2022–2023 data", "status": "done", "due_date": D(5), "category": "analysis"},
        # DHIS2
        {"task_id": "task-005", "project_id": "proj-DHIS2-002", "title": "GPS entry for 247 remaining health facilities", "status": "open", "due_date": FUTURE(7), "category": "data", "notes": "Coordinate with Ministry GIS unit"},
        {"task_id": "task-006", "project_id": "proj-DHIS2-002", "title": "Test case notification form with health zone supervisors", "status": "open", "due_date": FUTURE(14), "category": "testing"},
        {"task_id": "task-007", "project_id": "proj-DHIS2-002", "title": "Write DHIS2 metadata maintenance SOP", "status": "open", "due_date": FUTURE(21), "category": "documentation"},
        {"task_id": "task-008", "project_id": "proj-DHIS2-002", "title": "Train district data managers — Kinshasa workshop", "status": "open", "due_date": FUTURE(30), "category": "training"},
        # PhD
        {"task_id": "task-009", "project_id": "proj-PHD-003", "title": "Write Article 2 methods section — INLA specification", "status": "open", "due_date": FUTURE(10), "category": "writing", "notes": "Focus on spatial random effect justification"},
        {"task_id": "task-010", "project_id": "proj-PHD-003", "title": "Meet with supervisor — Article 2 outline review", "status": "open", "due_date": FUTURE(5), "category": "meeting"},
        {"task_id": "task-011", "project_id": "proj-PHD-003", "title": "Register Article 1 preprint on medRxiv", "status": "done", "due_date": D(3), "category": "dissemination"},
        # Malaria
        {"task_id": "task-012", "project_id": "proj-MAL-004", "title": "Harmonise site codes across 6 country datasets", "status": "open", "due_date": FUTURE(4), "category": "data"},
        {"task_id": "task-013", "project_id": "proj-MAL-004", "title": "Literature search: artemisinin resistance markers 2022–2025", "status": "open", "due_date": FUTURE(7), "category": "research"},
        # Teaching
        {"task_id": "task-014", "project_id": "proj-TEACH-005", "title": "Draft Module 4 outline: spatial epidemiology + QGIS", "status": "open", "due_date": FUTURE(14), "category": "teaching"},
        {"task_id": "task-015", "project_id": "proj-TEACH-005", "title": "Curate reading list for Module 1: disease burden", "status": "done", "due_date": D(7), "category": "teaching"},
    ]

    for t in tasks:
        conn.execute("""
            INSERT OR REPLACE INTO tasks
            (task_id, project_id, title, status, due_date, category, notes, created_at)
            VALUES (:task_id, :project_id, :title, :status, :due_date, :category,
                    :notes, datetime('now'))
        """, {**{"notes": "", "category": "general"}, **t})

    # ── Meetings ───────────────────────────────────────────────────────────────
    meetings = [
        {
            "meeting_id": "meet-001",
            "title": "HAT Consortium Call — Q2 Progress Review",
            "meeting_date": D(2),
            "domain": "NTD",
            "project": "proj-HAT-001",
            "meeting_type": "consortium",
            "attendees": "Dr. Fontaine, Dr. Büscher (ITM Antwerp), Prof. Lutumba (INRB Kinshasa), Dr. Priotto (DNDi), Dr. Simarro (WHO)",
            "transcript": """WHO confirmed that DRC HAT notifications dropped below 1,000 for the first time in 2024. The consortium reviewed the spatial clustering analysis from Article 1. Prof. Lutumba raised concerns about underreporting in Bandundu province — health zones with no cases since 2020 may reflect surveillance gaps, not true elimination.

Key discussion: should the 2030 elimination target apply uniformly or be zone-stratified? Dr. Priotto suggested a risk-stratification framework (high/medium/low) that would prioritise active surveillance resources. Dr. Simarro presented the WHO updated roadmap draft.

Amélie presented the INLA model preliminary results. Reviewer questions focused on denominator data quality.""",
            "decisions": "1. Adopt risk-stratification framework for 2026–2030 surveillance plan\n2. Amélie to lead methods section for consortium surveillance protocol update\n3. Next call: 3 months, full review of Article 2 draft",
            "action_items": "- Amélie: update Article 1 revision based on consortium feedback by June 5\n- Dr. Büscher: share ITM prevalence data for supplementary table\n- Dr. Priotto: circulate DNDi risk-stratification framework draft\n- Dr. Simarro: send WHO roadmap chapter on surveillance targets",
            "duration_minutes": 90,
            "status": "filed",
            "created_at": DT(2),
        },
        {
            "meeting_id": "meet-002",
            "title": "PhD Supervision — Article 2 Scope",
            "meeting_date": D(5),
            "domain": "Research",
            "project": "proj-PHD-003",
            "meeting_type": "supervision",
            "attendees": "Dr. Fontaine, Prof. Boelaert (IMT/UA promoter), Dr. Van Damme (co-promoter)",
            "transcript": """Prof. Boelaert reviewed the Article 2 outline. Strong interest in the methodological contribution — comparing INLA Besag model to standard GLM for HAT risk factors.

Discussion on whether to include household survey data (DHS) as a covariate or keep analysis to passive surveillance. Van Damme argued for passive surveillance only to avoid ecological fallacy. Boelaert suggested a sensitivity analysis including DHS.

Timeline: aim for methods section draft by July, results by October, submission December.""",
            "decisions": "1. Article 2 scope: passive surveillance data + DHS sensitivity analysis\n2. Methods section draft target: July 15\n3. Consider special issue submission: PLoS NTD 'Surveillance Methods' collection",
            "action_items": "- Amélie: draft INLA model specification and DAG by June 10\n- Prof. Boelaert: share 2018 DRC DHS data extract\n- Check PLoS NTD special issue deadline",
            "duration_minutes": 60,
            "status": "filed",
            "created_at": DT(5),
        },
        {
            "meeting_id": "meet-003",
            "title": "DHIS2 Implementation Review — DRC Ministry of Health",
            "meeting_date": D(8),
            "domain": "Health Information Systems",
            "project": "proj-DHIS2-002",
            "meeting_type": "stakeholder",
            "attendees": "Dr. Fontaine, Mr. Kabila (MoH NTD Programme Director), Ms. Nsimba (Data Manager), WHO-AFRO DHIS2 advisor",
            "transcript": """Ministry confirmed budget allocation for DHIS2 training: $45,000 for Q3 workshops in Kinshasa, Lubumbashi, and Kisangani.

GPS entry for health facilities behind schedule — 247 of 890 facilities still missing coordinates. Mr. Kabila requested a 3-week extension. Agreed, new deadline June 28.

WHO advisor raised compatibility with national HMIS — confirmed DHIS2 NTD module will use standard data elements, compatible with existing HMIS aggregation. The tracker program was demonstrated. Ms. Nsimba flagged that the paper form has more fields than the DHIS2 form — discrepancy needs resolution.""",
            "decisions": "1. GPS deadline extended to June 28\n2. Training schedule confirmed: Kinshasa Aug 5–7, Lubumbashi Aug 19–21, Kisangani Sep 2–4\n3. Paper vs digital form discrepancy: Amélie to propose harmonised form by June 15",
            "action_items": "- Amélie: resolve paper/digital form discrepancy, propose harmonised version by June 15\n- Mr. Kabila: assign GPS entry officers to remaining 247 facilities\n- MS Nsimba: send list of all current data elements in paper form",
            "duration_minutes": 120,
            "status": "filed",
            "created_at": DT(8),
        },
        {
            "meeting_id": "meet-004",
            "title": "Malaria Resistance Consortium — Data Sharing Protocol",
            "meeting_date": D(1),
            "domain": "Malaria",
            "project": "proj-MAL-004",
            "meeting_type": "consortium",
            "attendees": "Dr. Fontaine, Dr. Ouédraogo (IRSS Burkina), Dr. Asamoah (KCCR Ghana), Dr. Fall (PNLP Senegal), Dr. Coulibaly (INRSP Mali), Prof. Barnes (LSHTM)",
            "transcript": """Consortium agreed on a common data dictionary after 3 months of discussion. Key issue resolved: site code standardisation — will use WHO SPAR codes + country prefix. This unblocks Amélie's analysis.

Pfkelch13 validation status: 4 of 6 country datasets have WHO-validated results. Ghana and Mali pending lab confirmation for 2024 samples.

Prof. Barnes proposed a pooled analysis for WHO pre-qualification of the K13 445 mutation as a partial resistance marker. Timeline: 6 months. Amélie invited to lead statistical analysis plan.""",
            "decisions": "1. Site codes: WHO SPAR + country prefix (immediate)\n2. Pooled K13 analysis: Amélie leads statistical analysis plan\n3. Data sharing portal: OSF project created, all datasets uploaded by July 31",
            "action_items": "- Amélie: clean and upload DRC dataset to OSF by June 20\n- Dr. Ouédraogo: send updated Burkina metadata\n- Prof. Barnes: circulate pooled analysis protocol draft",
            "duration_minutes": 75,
            "status": "filed",
            "created_at": DT(1),
        },
    ]

    for m in meetings:
        conn.execute("""
            INSERT OR REPLACE INTO meetings
            (meeting_id, title, meeting_date, domain, project, meeting_type, attendees,
             transcript, decisions, action_items, duration_minutes, status, created_at)
            VALUES (:meeting_id, :title, :meeting_date, :domain, :project, :meeting_type,
                    :attendees, :transcript, :decisions, :action_items, :duration_minutes,
                    :status, :created_at)
        """, m)

    # ── Library Cards ──────────────────────────────────────────────────────────
    library_cards = [
        {"title": "Systematic review of HAT treatment outcomes 2010–2024", "domain": "NTD", "tags": "HAT,treatment,eflornithine,NIFURTIMOX,systematic-review", "summary": "Meta-analysis of 23 RCTs. NECT (nifurtimox-eflornithine combination) superior to monotherapy. Stage 2 cure rates: 94.2% (NECT) vs 88.1% (eflornithine alone). Fexinidazole oral treatment shows comparable efficacy in recent trials."},
        {"title": "Mapping HAT transmission risk in DRC using spatial random effects", "domain": "NTD", "tags": "HAT,spatial,INLA,DRC,risk-mapping", "summary": "Bayesian geostatistical model (INLA-SPDE) identified 12 high-transmission clusters along major river systems. Population at risk: 4.2M. Underreporting adjustment doubled estimated incidence in remote zones."},
        {"title": "WHO Roadmap for NTD control 2021–2030 — surveillance targets", "domain": "NTD", "tags": "WHO,NTD,roadmap,targets,elimination,surveillance", "summary": "Updated milestones for HAT elimination: <1 case/10,000 population in all endemic health zones by 2030. Requires shift from passive to active surveillance in 340 remaining endemic zones."},
        {"title": "DHIS2 for national disease surveillance: lessons from 12 LMIC deployments", "domain": "Health Information Systems", "tags": "DHIS2,surveillance,LMIC,implementation,data-quality", "summary": "Comparative study of DHIS2 NTD modules across 12 countries. Key success factors: dedicated national data manager, mobile data entry for field teams, automated data quality alerts. Timeliness improved by 67% vs paper systems."},
        {"title": "Bayesian hierarchical models for disease burden estimation", "domain": "Statistics", "tags": "INLA,bayesian,multilevel,disease-burden,R-INLA", "summary": "Comprehensive guide to R-INLA for spatial epidemiology. Covers BYM2 model for areal data, SPDE for point-referenced data, temporal extensions. Benchmark against MCMC shows 40× speedup with comparable accuracy."},
        {"title": "Artemisinin partial resistance in P. falciparum: global surveillance 2022–2024", "domain": "Malaria", "tags": "malaria,artemisinin,resistance,Pfkelch13,surveillance", "summary": "K13 mutations validated as partial resistance markers now detected in 8 African countries. WHO urgent review triggered. C580Y dominant in Southeast Asia; multiple mutations in Africa. ACT treatment failures: 12–26% in affected sites."},
        {"title": "Multilevel modelling in population health — applied examples", "domain": "Statistics", "tags": "multilevel,MLM,epidemiology,methods,textbook", "summary": "Applied textbook covering 2-level and 3-level models. HAT chapters co-authored by IMT team. Stata and R examples throughout. Strong on contextual effects and cross-level interactions."},
        {"title": "OpenStreetMap for health facility mapping in sub-Saharan Africa", "domain": "GIS", "tags": "OSM,mapping,health-facilities,GIS,DHIS2", "summary": "Systematic comparison of OSM vs official facility lists in 6 countries. OSM coverage: 68–94% of verified facilities. Completeness higher in urban areas. Recommended as first-pass data source for DHIS2 facility imports."},
        {"title": "Measuring disease burden in low-income settings: methodological challenges", "domain": "Epidemiology", "tags": "disease-burden,DALYs,methods,surveillance,underreporting", "summary": "Reviews four approaches to burden estimation under surveillance gaps: capture-recapture, multiplier methods, Bayesian modelling, expert elicitation. Recommends triangulation. Specific guidance for NTDs with passive-only surveillance."},
        {"title": "Field evaluation of RDTs for HAT stage 1 screening", "domain": "NTD", "tags": "HAT,rapid-diagnostic-test,RDT,screening,sensitivity", "summary": "Head-to-head evaluation of three HAT RDTs (HAT Sero-K-SeT, SD-Bioline HAT 2.0, rHAT Sero-Strip) in DRC active surveillance campaign. HAT Sero-K-SeT: sensitivity 95.3%, specificity 99.1%. Best performer in field conditions."},
    ]

    for i, card in enumerate(library_cards, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO library_cards (id, title, domain, tags, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (100+i, card["title"], card["domain"], card["tags"], card["summary"], DT(30+i*3)))

    # ── Ideas ──────────────────────────────────────────────────────────────────
    ideas = [
        {"text": "i: Use capture-recapture with health zone treatment data as second list — more rigorous than current multiplier method for underreporting estimate", "project_id": "proj-HAT-001", "idea_type": "research", "tags": "HAT,methodology,capture-recapture,underreporting", "domain": "NTD", "phd_relevance": 4},
        {"text": "i: Could the DHIS2 facility location data feed directly into the INLA spatial model for Article 2? Would save manual coordinate extraction step", "project_id": "proj-DHIS2-002", "idea_type": "method", "tags": "DHIS2,spatial,integration,INLA", "domain": "Health Information Systems", "phd_relevance": 3},
        {"text": "i: Risk stratification from Article 1 results could directly inform DRC Ministry targeting of active surveillance resources — policy article opportunity", "project_id": "proj-PHD-003", "idea_type": "research", "tags": "policy,risk-stratification,surveillance,HAT", "domain": "NTD", "phd_relevance": 5},
        {"text": "q: What happens to spatial autocorrelation estimates in INLA when health zone boundaries changed mid-period (2018 administrative reform)?", "project_id": "proj-PHD-003", "idea_type": "question", "tags": "INLA,spatial,administrative-boundaries,methods", "domain": "Statistics", "phd_relevance": 4},
        {"text": "i: The K13 mutation diversity across West Africa sites might map onto treatment pathway differences — ask Dr. Fall if Senegal has disaggregated by treatment line", "project_id": "proj-MAL-004", "idea_type": "research", "tags": "malaria,K13,West-Africa,treatment", "domain": "Malaria", "phd_relevance": 1},
        {"text": "i: Module 3 of the digital health course could use the DRC DHIS2 implementation as a live case study — students configure a test instance", "project_id": "proj-TEACH-005", "idea_type": "teaching", "tags": "DHIS2,teaching,case-study,digital-health", "domain": "Teaching", "phd_relevance": 0},
        {"text": "n: Reviewer 2 on Article 1 is likely Boillot (LMU Munich) — the specific question about CATT threshold matches his 2022 paper exactly", "project_id": "proj-HAT-001", "idea_type": "note", "tags": "peer-review,CATT,HAT", "domain": "NTD", "phd_relevance": 2},
        {"text": "i: Fasciola hepatica prevalence data released last week from West Africa — potentially useful as comparator burden calculation in the introductory framing", "project_id": "proj-PHD-003", "idea_type": "literature", "tags": "fasciola,NTD,burden,West-Africa", "domain": "NTD", "phd_relevance": 2},
    ]

    for i, idea in enumerate(ideas, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO ideas
            (idea_id, text, project_id, idea_type, tags, created_at, domain,
             phd_relevance, feasibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 3)
        """, (f"idea-{100+i}", idea["text"], idea.get("project_id"), idea["idea_type"],
              idea["tags"], DT(i), idea["domain"], idea.get("phd_relevance", 2)))

    # ── News Briefs ─────────────────────────────────────────────────────────────
    news = [
        {"title": "WHO confirms HAT notifications below 1,000 globally for first time in 2024", "domain": "NTD", "signal_strength": "high", "summary": "WHO NTD department confirmed global HAT notifications dropped to 848 in 2024 — a historic milestone and the first time below 1,000. DRC accounts for 73% of remaining cases. WHO states the 2030 elimination target remains achievable but requires sustained surveillance investment.", "source_url": "https://www.who.int/news/item/hat-milestone-2024", "source_type": "news", "surprise_flag": 1},
        {"title": "New INLA spatial model for malaria risk — comparison with geostatistical benchmark", "domain": "Statistics", "signal_strength": "medium", "summary": "Open-access paper in Spatial and Spatio-temporal Epidemiology compares R-INLA SPDE approach to geostatistical Gaussian process models for malaria risk mapping. INLA 15× faster with 2% lower WAIC. Code on GitHub. Directly applicable to Article 2 methods.", "source_url": "https://doi.org/10.1016/j.sste.2025.100651", "source_type": "article", "surprise_flag": 0},
        {"title": "DHIS2 Academy: NTD Module certification now available online", "domain": "Health Information Systems", "signal_strength": "medium", "summary": "DHIS2 Academy launched a new online certification track for NTD surveillance module implementation. 12-hour course, covers aggregate + tracker programs. Free for public health professionals.", "source_url": "https://academy.dhis2.org/ntd", "source_type": "news", "surprise_flag": 0},
        {"title": "P. falciparum K13 C469Y mutation validated as partial resistance marker — WHO urgent review", "domain": "Malaria", "signal_strength": "high", "summary": "WHO malaria threat response team published urgent review confirming C469Y as a validated partial resistance marker. Detected in Uganda, Rwanda, and DRC in 2024 samples. Updates previous classification from 'not validated' to 'validated'.", "source_url": "https://www.who.int/publications/i/item/k13-c469y-review", "source_type": "news", "surprise_flag": 1},
        {"title": "Lancet Infectious Diseases: open call for HAT elimination supplement", "domain": "NTD", "signal_strength": "high", "summary": "Lancet ID announced a special supplement on HAT elimination, open call for contributions. Deadline: September 30. Topics include: surveillance systems, treatment access, operational research, policy. Directly relevant to Article 1 revised submission and PhD Article 3.", "source_url": "https://www.thelancet.com/journals/laninf/article/hat-elimination-supplement", "source_type": "news", "surprise_flag": 1},
        {"title": "OpenAlex: 47 new HAT surveillance papers indexed this week", "domain": "NTD", "signal_strength": "low", "summary": "Weekly OpenAlex scan returned 47 papers tagged with 'human African trypanosomiasis' + 'surveillance' published in the last 7 days. Top citation: Büscher et al. on passive surveillance performance in DRC focus area.", "source_url": "https://openalex.org/works?filter=concepts.id:C2778793908", "source_type": "article", "surprise_flag": 0},
        {"title": "PubMed alert: R-INLA 24.9.0 released — new features for spatial models", "domain": "Statistics", "signal_strength": "medium", "summary": "R-INLA version 24.9.0 adds improved support for non-stationary spatial models and new PC priors for spatial range parameter. Release notes include worked example for disease surveillance. Run update.packages() to upgrade.", "source_url": "https://www.r-inla.org/news", "source_type": "article", "surprise_flag": 0},
    ]

    for i, n in enumerate(news, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO news_briefs
            (brief_id, brief_date, title, domain, signal_strength, summary,
             source_url, source_type, surprise_flag, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f"demo-news-{200+i}", D(i//3), n["title"], n["domain"], n["signal_strength"],
              n["summary"], n["source_url"], n["source_type"], n["surprise_flag"], DT(i//3)))

    # ── Daily Insight (Morning Brief) ──────────────────────────────────────────
    brief_text = """**Today's standout:** WHO confirmed global HAT notifications fell below 1,000 for the first time in 2024. This directly validates the surveillance trend you described in Article 1 and strengthens your elimination timeline argument. Worth adding a sentence to your revision cover letter.

**This week's signals:** The Lancet ID call for HAT elimination supplement is open (deadline September 30) — Article 1 revised submission could fit this perfectly. A new R-INLA 24.9.0 release includes non-stationary spatial model support, worth testing for Article 2. The K13 C469Y validation news is urgent for the malaria project — update your resistance classification table.

**Research thread to pick up:** You have three items overdue or due today: the Figure 3 revision, the supplement table S3 update, and the harmonised DHIS2 form draft (due June 15). The DHIS2 item unblocks training preparation, so prioritise it over the manuscript revision this morning."""

    # daily_insights schema uses insight_date + content + generated_at
    conn.execute("""
        INSERT OR REPLACE INTO daily_insights (id, insight_date, content, generated_at)
        VALUES (1, ?, ?, ?)
    """, (D(0), brief_text, DT(0, 7)))

    # ── Agent Runs ─────────────────────────────────────────────────────────────
    agent_runs = [
        {"agent_slug": "librarian", "task_summary": "Literature search: HAT surveillance DRC 2020–2025", "input_path": "inputs/searches/hat-drc-2025.md", "output_path": "outputs/reviews/librarian/2026-05-13_hat-surveillance-drc.md", "status": "completed", "input_tokens": 1240, "output_tokens": 3890, "model": "claude-sonnet-4-6", "created_at": DT(2)},
        {"agent_slug": "epidemiologist", "task_summary": "Methodology review: INLA model for Article 2 spatial analysis", "input_path": "inputs/code/article2-inla-draft.R", "output_path": "outputs/reviews/epidemiologist/2026-05-11_article2-inla-review.md", "status": "completed", "input_tokens": 2100, "output_tokens": 4200, "model": "claude-opus-4-7", "created_at": DT(4)},
        {"agent_slug": "writing-partner", "task_summary": "Methods section revision: Article 1 response to reviewers", "input_path": "inputs/drafts/article1-methods-v3.md", "output_path": "outputs/reviews/writing-partner/2026-05-10_article1-methods-revision.md", "status": "completed", "input_tokens": 3400, "output_tokens": 5600, "model": "claude-sonnet-4-6", "created_at": DT(5)},
        {"agent_slug": "dhis2-expert", "task_summary": "DHIS2 tracker metadata review: NTD passive surveillance program", "input_path": "inputs/dhis2/ntd-tracker-metadata.json", "output_path": "outputs/reviews/dhis2-expert/2026-05-09_ntd-tracker-review.md", "status": "completed", "input_tokens": 4200, "output_tokens": 6100, "model": "claude-sonnet-4-6", "created_at": DT(6)},
        {"agent_slug": "meeting-memory", "task_summary": "HAT Consortium Call Q2 — structured brief + action items", "input_path": "inputs/meetings/hat-consortium-q2-2026.txt", "output_path": "outputs/reviews/meeting-memory/2026-05-13_hat-consortium-q2.md", "status": "completed", "input_tokens": 2800, "output_tokens": 3400, "model": "claude-haiku-4-5", "created_at": DT(2)},
        {"agent_slug": "data-analyst", "task_summary": "Profile and harmonise malaria resistance dataset: 6 country merge", "input_path": "inputs/code/malaria-merge-v2.csv", "output_path": "outputs/reviews/data-analyst/2026-05-12_malaria-profile.md", "status": "completed", "input_tokens": 1800, "output_tokens": 2900, "model": "claude-sonnet-4-6", "created_at": DT(3)},
        {"agent_slug": "news-radar", "task_summary": "Morning brief: NTD + malaria + DHIS2 signals", "input_path": "", "output_path": "outputs/reviews/news-radar/2026-05-15_morning-brief.md", "status": "completed", "input_tokens": 890, "output_tokens": 1200, "model": "claude-haiku-4-5", "created_at": DT(0, 7)},
        {"agent_slug": "course-builder", "task_summary": "Course outline: Epidemiology for Digital Health — Module 1–4 draft", "input_path": "", "output_path": "outputs/reviews/course-builder/2026-05-08_epi-digital-health-outline.md", "status": "completed", "input_tokens": 2200, "output_tokens": 4800, "model": "claude-sonnet-4-6", "created_at": DT(7)},
    ]

    for i, run in enumerate(agent_runs, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO agent_runs
            (agent_slug, task_summary, input_path, output_path, status,
             input_tokens, output_tokens, model, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (run["agent_slug"], run["task_summary"],
              run["input_path"], run["output_path"], run["status"],
              run["input_tokens"], run["output_tokens"], run["model"], run["created_at"]))

    # ── Learning Courses ────────────────────────────────────────────────────────
    courses = [
        {"title": "Bayesian Spatial Epidemiology with R-INLA", "category": "statistics", "slug": "bayesian-spatial-inla", "progress_pct": 67, "total_modules": 9, "completed_modules": 6, "status": "active", "project_id": "proj-PHD-003"},
        {"title": "DHIS2 Tracker Programs — Advanced Configuration", "category": "health-informatics", "slug": "dhis2-tracker-advanced", "progress_pct": 33, "total_modules": 6, "completed_modules": 2, "status": "active", "project_id": "proj-DHIS2-002"},
        {"title": "Applied Multilevel Models in Epidemiology", "category": "statistics", "slug": "multilevel-models-epi", "progress_pct": 100, "total_modules": 8, "completed_modules": 8, "status": "completed"},
        {"title": "Scientific Writing for Public Health — Revision Strategies", "category": "writing", "slug": "scientific-writing-ph", "progress_pct": 0, "total_modules": 5, "completed_modules": 0, "status": "active", "project_id": "proj-PHD-003"},
    ]

    for i, c in enumerate(courses, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO learning_courses
            (id, title, category, slug, progress_pct, total_modules, completed_modules,
             status, project_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (300+i, c["title"], c["category"], c["slug"], c["progress_pct"],
              c["total_modules"], c["completed_modules"], c["status"],
              c.get("project_id"), DT(60+i*10)))

    conn.commit()
    print(f"✓ Demo data seeded successfully.")
    print(f"  Researcher: Dr. Amélie Fontaine — Senior Epidemiologist, IMT Lyon")
    print(f"  Projects: {len(projects)} active")
    print(f"  Tasks: {len(tasks)} (including overdue + upcoming)")
    print(f"  Meetings: {len(meetings)} (with full transcripts)")
    print(f"  Library cards: {len(library_cards)}")
    print(f"  Ideas: {len(ideas)}")
    print(f"  News briefs: {len(news)}")
    print(f"  Agent runs: {len(agent_runs)}")
    print(f"  Learning courses: {len(courses)}")
    print(f"\n  User config and preferences written to system/config/")
    print(f"\n  Open http://127.0.0.1:8000 and start the dashboard to take screenshots.")


def main():
    parser = argparse.ArgumentParser(description="Seed Metis with demo data for screenshots.")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB), help="Path to SQLite database")
    parser.add_argument("--reset", action="store_true", help="Wipe demo rows before seeding")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Start the dashboard first to create the database, then run this script.")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))

    if args.reset:
        print("Resetting demo rows...")
        for table, id_col, prefix in [
            ("projects", "project_id", "proj-"),
            ("tasks", "task_id", "task-"),
            ("meetings", "meeting_id", "meet-"),
            # agent_runs.run_id is INTEGER — skip prefix delete for it
            ("ideas", "idea_id", "idea-"),
        ]:
            try:
                conn.execute(f"DELETE FROM {table} WHERE {id_col} LIKE ?", (f"{prefix}%",))
            except Exception:
                pass
        try:
            conn.execute("DELETE FROM library_cards WHERE id >= 100 AND id < 200")
            conn.execute("DELETE FROM news_briefs WHERE brief_id LIKE 'demo-news-%'")
            conn.execute("DELETE FROM learning_courses WHERE id >= 300 AND id < 400")
            conn.execute("DELETE FROM daily_insights WHERE id = 1")
        except Exception:
            pass
        conn.commit()
        print("Reset done.")

    seed(conn)
    conn.close()


if __name__ == "__main__":
    main()
