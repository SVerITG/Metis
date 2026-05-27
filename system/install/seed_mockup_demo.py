"""
seed_mockup_demo.py — Populate Metis with realistic demo data for screenshots.

Researcher persona: Dr. Amara Diallo
  Role: Senior Epidemiologist — Outbreak Response, WHO Africa Regional Office
  Focus: Ebola Virus Disease surveillance · DHIS2 · genomic epidemiology
  Projects: EVD surveillance DRC, DHIS2 case notification tracker,
            field investigation methods, genomics collaboration

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
DEFAULT_DB = REPO_ROOT / "system" / "app-py" / "data" / "metis.sqlite"
CONFIG_DIR = REPO_ROOT / "system" / "config"

TODAY = datetime.now()
D = lambda d: (TODAY - timedelta(days=d)).strftime("%Y-%m-%d")
DT = lambda d, h=8: (TODAY - timedelta(days=d)).replace(hour=h, minute=0).strftime("%Y-%m-%d %H:%M:%S")
FUTURE = lambda d: (TODAY + timedelta(days=d)).strftime("%Y-%m-%d")


def seed(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row

    # ── User config ────────────────────────────────────────────────────────────
    prefs = {
        "display_name": "Amara",
        "role": "Senior Epidemiologist · Outbreak Response",
        "interests": ["Ebola virus disease", "viral haemorrhagic fevers", "outbreak investigation",
                      "DHIS2", "genomic epidemiology", "contact tracing",
                      "ring vaccination", "health information systems", "DRC"],
        "news_topics": ["WHO outbreak alerts", "Ebola DRC", "DHIS2 updates",
                        "epidemiology methods", "AI in global health",
                        "VHF surveillance", "genomic sequencing outbreak"],
        "pubmed_query": "Ebola virus disease[Title] OR EVD surveillance[Title/Abstract] OR viral haemorrhagic fever[Title]",
        "active_model": "sonnet",
        "theme": "dark",
        "density": "comfortable",
    }

    user_config = {
        "user": {
            "name": "Amara",
            "role": "Senior Epidemiologist",
            "language": "en",
            "general_context": (
                "Senior epidemiologist specialising in outbreak response, "
                "particularly Ebola Virus Disease (EVD) in Central Africa. "
                "Based at WHO Africa Regional Office. Leads field investigations, "
                "DHIS2 case notification systems, and genomic surveillance analysis."
            ),
            "active_contexts": ["general", "EVD surveillance", "DHIS2"],
            "specialist_contexts": [
                {"name": "EVD surveillance", "description": "Ebola outbreak investigation, ring vaccination, case-fatality analysis"},
                {"name": "DHIS2", "description": "DHIS2 case notification tracker, metadata design, NTD/VHF implementation"},
                {"name": "Genomic epidemiology", "description": "Phylogenetics, transmission cluster analysis, sequencing pipelines"},
            ],
        },
        "research": {
            "field": "Public health · Outbreak epidemiology",
            "interests": ["Ebola virus disease", "outbreak response", "DHIS2", "genomic surveillance"],
            "specific_focus": "EVD outbreak analysis in DRC, DHIS2 case notification systems, genomic cluster detection",
        },
        "data_sensitivity": {"patient_data": True, "embargoed_results": True, "compliance": ["GDPR", "WHO data sharing policy"]},
    }

    prefs_path = CONFIG_DIR / "user-preferences.json"
    prefs_path.write_text(json.dumps(prefs, indent=2, ensure_ascii=False))

    try:
        import yaml
        config_path = CONFIG_DIR / "user-config.yaml"
        with config_path.open("w") as f:
            yaml.dump(user_config, f, default_flow_style=False, allow_unicode=True)
    except ImportError:
        pass

    # ── Projects ───────────────────────────────────────────────────────────────
    projects = [
        {
            "project_id": "proj-EVD-001",
            "title": "EVD Outbreak Analysis — Equateur Province 2025",
            "description": "Retrospective analysis of the 2025 Equateur EVD outbreak. 47 confirmed cases, 31 deaths (CFR 66%). Spatial and genomic analysis to characterise transmission chains and identify index case source.",
            "domain": "Outbreak Response",
            "status": "active",
            "priority": "high",
            "next_step": "Finalise transmission tree — 3 unlinked clusters require genomic confirmation",
            "external_path": "C:/Users/Amara/Documents/research/evd-equateur-2025",
            "github_url": "https://github.com/amaradiallo-who/evd-equateur-2025",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amara/Documents/research/evd-equateur-2025/analysis.Rproj"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amara/Documents/research/evd-equateur-2025"},
                {"label": "GitHub", "type": "github", "url": "https://github.com/amaradiallo-who/evd-equateur-2025"},
            ]),
            "created_at": DT(90),
        },
        {
            "project_id": "proj-DHIS2-002",
            "title": "DHIS2 EVD Case Notification Tracker — DRC Scale-up",
            "description": "Implementation of a DHIS2 real-time case notification tracker for EVD across 8 provinces. Replaces paper-based weekly reporting. Integrates with national HMIS.",
            "domain": "Health Information Systems",
            "status": "active",
            "priority": "high",
            "next_step": "Pilot test the mobile data entry form with field teams in Mbandaka health zone",
            "external_path": "C:/Users/Amara/Documents/dhis2-evd-tracker",
            "github_url": "https://github.com/amaradiallo-who/dhis2-evd-tracker",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open in VS Code", "type": "vscode", "path": "C:/Users/Amara/Documents/dhis2-evd-tracker"},
                {"label": "DHIS2 Dev Instance", "type": "url", "url": "http://localhost:8080/dhis-web-app"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amara/Documents/dhis2-evd-tracker"},
            ]),
            "created_at": DT(60),
        },
        {
            "project_id": "proj-GEN-003",
            "title": "Genomic Surveillance — EVD Transmission Clusters",
            "description": "Whole-genome sequencing of 38 EVD isolates from the 2025 Equateur outbreak. Phylogenetic analysis to resolve transmission clusters and date the introduction event. Collaboration with INRB and Africa CDC.",
            "domain": "Genomic Epidemiology",
            "status": "active",
            "priority": "high",
            "next_step": "Run BEAST2 analysis on the 38-genome alignment — check convergence diagnostics",
            "external_path": "C:/Users/Amara/Documents/research/evd-genomics-2025",
            "github_url": "",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "VS Code", "type": "vscode", "path": "C:/Users/Amara/Documents/research/evd-genomics-2025"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amara/Documents/research/evd-genomics-2025"},
            ]),
            "created_at": DT(45),
        },
        {
            "project_id": "proj-METH-004",
            "title": "Ring Vaccination Effectiveness — Pooled Analysis",
            "description": "Multi-outbreak pooled analysis of rVSV-ZEBOV ring vaccination effectiveness across 4 DRC outbreaks (2018–2025). 6,400 vaccinated contacts. Estimating waning immunity and optimal ring radius.",
            "domain": "Vaccine Epidemiology",
            "status": "active",
            "priority": "medium",
            "next_step": "Harmonise vaccine administration dates across outbreak datasets — 3 country formats differ",
            "external_path": "C:/Users/Amara/Documents/research/ring-vaccination-pooled",
            "github_url": "https://github.com/amaradiallo-who/ring-vax-pooled",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amara/Documents/research/ring-vaccination-pooled/analysis.Rproj"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amara/Documents/research/ring-vaccination-pooled"},
            ]),
            "created_at": DT(30),
        },
        {
            "project_id": "proj-TEACH-005",
            "title": "Course: Field Investigation of Viral Haemorrhagic Fevers",
            "description": "New WHO AFRO online course for national rapid response teams. 8 modules: case definitions, contact tracing, safe burial, ring vaccination, lab coordination, genomics basics, DHIS2 reporting, after-action review.",
            "domain": "Teaching",
            "status": "active",
            "priority": "low",
            "next_step": "Draft Module 5 content: coordinating laboratory specimen transport under BSL-3 protocols",
            "external_path": "C:/Users/Amara/Documents/courses/vhf-field-investigation",
            "github_url": "",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open Course Folder", "type": "folder", "path": "C:/Users/Amara/Documents/courses/vhf-field-investigation"},
                {"label": "VS Code", "type": "vscode", "path": "C:/Users/Amara/Documents/courses/vhf-field-investigation"},
            ]),
            "created_at": DT(20),
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
        # EVD analysis
        {"task_id": "task-001", "project_id": "proj-EVD-001", "title": "Finalise transmission tree — resolve 3 unlinked clusters", "status": "open", "due_date": D(0), "category": "analysis", "notes": "Awaiting genomic sequences from INRB for clusters B, C, and D"},
        {"task_id": "task-002", "project_id": "proj-EVD-001", "title": "Calculate attack rate by household size and case generation", "status": "open", "due_date": D(2), "category": "analysis"},
        {"task_id": "task-003", "project_id": "proj-EVD-001", "title": "Draft manuscript — methods section (transmission analysis)", "status": "open", "due_date": FUTURE(7), "category": "writing", "notes": "Target: NEJM or Lancet — check open call for rapid communications"},
        {"task_id": "task-004", "project_id": "proj-EVD-001", "title": "Debrief with MoH DRC — preliminary findings presentation", "status": "done", "due_date": D(4), "category": "meeting"},
        # DHIS2
        {"task_id": "task-005", "project_id": "proj-DHIS2-002", "title": "Pilot mobile form with field teams — Mbandaka health zone", "status": "open", "due_date": FUTURE(5), "category": "testing", "notes": "Coordinate with zonal health officer"},
        {"task_id": "task-006", "project_id": "proj-DHIS2-002", "title": "Configure automated data quality alerts for case notification lag", "status": "open", "due_date": FUTURE(10), "category": "development"},
        {"task_id": "task-007", "project_id": "proj-DHIS2-002", "title": "Write DHIS2 data entry SOP for rapid response teams", "status": "open", "due_date": FUTURE(14), "category": "documentation"},
        {"task_id": "task-008", "project_id": "proj-DHIS2-002", "title": "Train DHIS2 focal points — 3-day workshop", "status": "open", "due_date": FUTURE(21), "category": "training"},
        # Genomics
        {"task_id": "task-009", "project_id": "proj-GEN-003", "title": "Run BEAST2 on 38-genome alignment — check convergence", "status": "open", "due_date": FUTURE(3), "category": "analysis"},
        {"task_id": "task-010", "project_id": "proj-GEN-003", "title": "Annotate phylogenetic tree with epidemiological metadata", "status": "open", "due_date": FUTURE(8), "category": "analysis"},
        {"task_id": "task-011", "project_id": "proj-GEN-003", "title": "Preprint submission — bioRxiv genomic epidemiology", "status": "open", "due_date": FUTURE(21), "category": "dissemination"},
        # Ring vaccination
        {"task_id": "task-012", "project_id": "proj-METH-004", "title": "Harmonise vaccine administration date formats — 4 outbreak datasets", "status": "open", "due_date": FUTURE(4), "category": "data"},
        {"task_id": "task-013", "project_id": "proj-METH-004", "title": "Literature search: rVSV-ZEBOV waning immunity evidence 2020–2025", "status": "open", "due_date": FUTURE(6), "category": "research"},
        # Teaching
        {"task_id": "task-014", "project_id": "proj-TEACH-005", "title": "Draft Module 5: lab specimen transport under BSL-3", "status": "open", "due_date": FUTURE(14), "category": "teaching"},
        {"task_id": "task-015", "project_id": "proj-TEACH-005", "title": "Curate case study bank for Module 2: contact tracing exercises", "status": "done", "due_date": D(5), "category": "teaching"},
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
            "title": "EVD Outbreak Review — Equateur 2025 Transmission Analysis",
            "meeting_date": D(3),
            "domain": "Outbreak Response",
            "project": "proj-EVD-001",
            "meeting_type": "technical",
            "attendees": "Dr. Diallo (WHO AFRO), Dr. Nkemdirim (INRB), Dr. Osei (Africa CDC), Dr. Martins (MSF), WHO HQ VHF team",
            "transcript": """WHO HQ confirmed that 47 confirmed EVD cases have been verified for the Equateur event. Three distinct transmission clusters identified based on contact tracing data — genomic data pending for two of them.

Dr. Nkemdirim (INRB) reported that whole-genome sequencing is complete for 38 samples. Phylogenetic analysis suggests the outbreak originated from a single introduction event approximately 3 weeks before the index case was detected. Closest match is to a 2022 Equateur lineage, raising questions about reservoir persistence vs re-introduction.

Dr. Osei (Africa CDC) presented the ring vaccination coverage data: 94% of tier-1 contacts vaccinated within 72 hours. Two vaccination rings overlapped — possible over-counting. Amara flagged this as a key uncertainty for the effectiveness analysis.

Key discussion: whether to publish a rapid communication before the outbreak is declared over. WHO HQ guidance: only if genomic analysis is complete and findings would inform response.""",
            "decisions": "1. Await BEAST2 results before submission decision\n2. Amara to lead transmission analysis manuscript\n3. Ring overlap correction to be applied before effectiveness calculation\n4. Next review: 10 days",
            "action_items": "- Amara: finalise transmission tree and resolve unlinked clusters using genomic data\n- Dr. Nkemdirim: share BEAST2-ready alignment and metadata\n- Dr. Osei: send corrected ring vaccination denominator\n- Dr. Martins: confirm safe burial protocol adherence rates for each cluster",
            "duration_minutes": 90,
            "status": "filed",
            "created_at": DT(3),
        },
        {
            "meeting_id": "meet-002",
            "title": "DHIS2 EVD Tracker — Field Pilot Readiness",
            "meeting_date": D(6),
            "domain": "Health Information Systems",
            "project": "proj-DHIS2-002",
            "meeting_type": "stakeholder",
            "attendees": "Dr. Diallo (WHO AFRO), Mr. Basoko (MoH DRC DHIS2 focal point), Ms. Kabanga (Zonal Health Officer, Mbandaka), WHO DHIS2 advisor",
            "transcript": """Pilot readiness confirmed for Mbandaka health zone. Three rapid response team members trained on mobile data entry. Mr. Basoko raised compatibility with the national HMIS — confirmed the EVD tracker uses standard WHO data elements compatible with existing aggregation.

Key issue: the paper-based notification form has 22 fields vs the DHIS2 tracker's 18 fields. Four fields (GPS coordinates of exposure site, contact's occupation, healthcare worker status, traditional healer exposure) are missing from the DHIS2 form. Ms. Kabanga argued these are operationally critical for ring vaccination targeting.

Decision: add the 4 missing fields to the DHIS2 tracker. Amara to propose updated metadata by Friday. WHO DHIS2 advisor confirmed this can be done without breaking the existing aggregate reporting.

Data quality alert configuration: set threshold at 48-hour lag for case notification — any health zone exceeding this triggers automated WhatsApp alert to zonal focal point.""",
            "decisions": "1. Add 4 missing fields to DHIS2 tracker metadata\n2. 48-hour notification lag threshold for automated alerts\n3. Pilot proceeds in Mbandaka next week",
            "action_items": "- Amara: propose updated DHIS2 metadata with 4 additional fields by Friday\n- Mr. Basoko: confirm HMIS compatibility after metadata update\n- Ms. Kabanga: identify 3 RRT members for pilot data entry training",
            "duration_minutes": 75,
            "status": "filed",
            "created_at": DT(6),
        },
        {
            "meeting_id": "meet-003",
            "title": "Genomics Consortium — Sequencing Update and BEAST2 Plan",
            "meeting_date": D(1),
            "domain": "Genomic Epidemiology",
            "project": "proj-GEN-003",
            "meeting_type": "consortium",
            "attendees": "Dr. Diallo (WHO AFRO), Dr. Nkemdirim (INRB), Dr. Park (Wellcome Sanger), Dr. Fall (Institut Pasteur Dakar), Africa CDC genomics team",
            "transcript": """38 genomes QC-passed and aligned. Coverage >90% for 35 samples. Three samples flagged: two with <70% genome coverage, one with suspected lab contamination marker. Dr. Nkemdirim recommends excluding the contaminated sample and including the two low-coverage genomes with a note.

Dr. Park proposed using BEAST2 with a strict molecular clock and exponential population growth model as a first pass. Amara suggested also running a relaxed clock given the reservoir uncertainty. Agreed to run both and compare.

Root-to-tip regression: strong temporal signal (R² = 0.87). Date of introduction estimate: 28 ± 9 days before the reported index case. This is consistent with the field investigation timeline.

Dr. Fall proposed submitting a preprint before peer-reviewed submission — Africa CDC genomics has a fast-turnaround review process.""",
            "decisions": "1. Exclude 1 contaminated sample, include 2 low-coverage with caveats\n2. Run both strict and relaxed clock BEAST2 models\n3. Preprint submission target: 3 weeks after BEAST2 convergence",
            "action_items": "- Amara: run BEAST2 models, share preliminary trees within 5 days\n- Dr. Park: review clock model outputs before preprint\n- Dr. Fall: confirm Institut Pasteur co-authorship and data sharing terms",
            "duration_minutes": 60,
            "status": "filed",
            "created_at": DT(1),
        },
        {
            "meeting_id": "meet-004",
            "title": "Ring Vaccination Pooled Analysis — Data Harmonisation",
            "meeting_date": D(8),
            "domain": "Vaccine Epidemiology",
            "project": "proj-METH-004",
            "meeting_type": "consortium",
            "attendees": "Dr. Diallo (WHO AFRO), Dr. Henao-Restrepo (WHO IVB), Dr. Camacho (LSHTM), Dr. Tchatchouang (Africa CDC), Merck global health team",
            "transcript": """Four outbreak datasets shared via secure WHO transfer. Dataset formats differ significantly: Equateur 2018 uses day-of-exposure dates, Kivu 2019–2020 uses registration dates, Equateur 2022 and 2025 use first-contact dates. Amara flagged this as a critical harmonisation problem — the vaccine effectiveness window calculation depends entirely on which date is used.

Dr. Camacho presented a sensitivity analysis plan: run effectiveness estimate under all three date conventions and report the range. Dr. Henao-Restrepo agreed this is the most honest approach given the data quality variation.

Waning immunity: only the Kivu 2019–2020 dataset has >18 months of follow-up. Insufficient for robust waning estimates — Amara to flag this as a major limitation.

Timeline: pooled analysis manuscript target is 6 months. Lancet or NEJM as primary target.""",
            "decisions": "1. Report vaccine effectiveness under all 3 date conventions\n2. Flag waning analysis as exploratory (limited follow-up)\n3. Target: Lancet or NEJM submission in 6 months",
            "action_items": "- Amara: harmonise date variables across 4 datasets and run primary VE estimate\n- Dr. Camacho: build sensitivity analysis R code for date convention comparison\n- Dr. Henao-Restrepo: confirm WHO authorship and data use agreement",
            "duration_minutes": 80,
            "status": "filed",
            "created_at": DT(8),
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
        {"title": "Ebola virus disease — transmission dynamics and outbreak investigation methods", "domain": "Outbreak Response", "tags": "EVD,Ebola,transmission,outbreak,epidemiology", "summary": "Comprehensive review of EVD transmission dynamics across 12 DRC outbreaks 2014–2024. Serial interval: 7–12 days (mean 8.4). Secondary attack rate among household contacts: 11–17%. Healthcare worker exposure consistently accounts for 10–15% of cases when PPE protocols are not enforced. Key finding: early case detection (<5 days from symptom onset to isolation) reduces secondary attack rate by 60%."},
        {"title": "rVSV-ZEBOV ring vaccination — Lancet trial and subsequent effectiveness evidence", "domain": "Vaccine Epidemiology", "tags": "rVSV-ZEBOV,Ebola,ring-vaccination,effectiveness,Ervebo", "summary": "Pooled analysis of ring vaccination across 2018–2023 DRC outbreaks. Overall vaccine effectiveness: 97.5% (95% CI 86–99.5%) in per-protocol analysis. Effectiveness lower in healthcare workers (91%) vs community contacts (99%). Waning: limited evidence beyond 12 months from initial data. R code and dataset on OSF."},
        {"title": "BEAST2: Bayesian evolutionary analysis for genomic epidemiology", "domain": "Genomic Epidemiology", "tags": "BEAST2,phylogenetics,molecular-clock,Bayesian,genomics", "summary": "Tutorial and benchmark for BEAST2 in outbreak genomic analysis. Covers strict vs relaxed molecular clock selection, population growth models, and convergence diagnostics (ESS >200). Applied example: dating introduction events in Ebola outbreaks. BEAST2 2.7+ required for improved relaxed clock implementation. Companion R package EpiEstim integrates phylogenetic dates with Rt estimation."},
        {"title": "DHIS2 for real-time outbreak surveillance — implementation lessons", "domain": "Health Information Systems", "tags": "DHIS2,surveillance,outbreak,real-time,implementation", "summary": "Review of DHIS2 deployments for outbreak surveillance in 8 African countries. Mobile data entry reduces reporting lag from 72 hours (paper) to 8 hours. Key success factors: offline functionality for field teams, automated data quality alerts, weekly refresher training. EVD-specific: tracker program with contact tracing linkage outperforms event-based aggregate reporting for ring vaccination targeting."},
        {"title": "Whole-genome sequencing in outbreak response — operational guide", "domain": "Genomic Epidemiology", "tags": "WGS,sequencing,outbreak,operational,Nanopore,Ebola", "summary": "Field-deployable sequencing protocols for outbreak response using Oxford Nanopore. Target: 24-hour turnaround from sample to phylogenetic tree. Minimum coverage: 90% genome at 20× depth. QC thresholds: exclude samples with <70% coverage for molecular clock analysis, include with caveats for tree topology. Validated in multiple EVD and MPOX deployments."},
        {"title": "Contact tracing performance and ring vaccination coverage in EVD outbreaks", "domain": "Outbreak Response", "tags": "contact-tracing,ring-vaccination,EVD,coverage,performance", "summary": "Analysis of contact tracing completeness across 6 DRC EVD outbreaks. Mean contact listing rate: 73% (range 51–89%). Tier-1 contact vaccination within 72 hours achieved in 87% of events when ring vaccination team was pre-positioned. Key predictor of poor coverage: urban settings (OR 0.34, 95% CI 0.19–0.60 vs rural). Implications for ring radius definitions in peri-urban outbreaks."},
        {"title": "Phylogeography of Zaire ebolavirus — reservoir persistence vs re-introduction", "domain": "Genomic Epidemiology", "tags": "Zaire-ebolavirus,phylogeography,reservoir,introduction,DRC", "summary": "Bayesian phylogeographic analysis of 847 EVD genomes from 1976–2024 DRC outbreaks. Evidence for independent reservoir introductions rather than sustained human-to-human chains between outbreaks. Equateur lineage shows geographic clustering suggesting local reservoir. Implications: surveillance of animal-human interface important even during inter-outbreak periods."},
        {"title": "Measuring case fatality ratio in real-time during EVD outbreaks", "domain": "Outbreak Response", "tags": "CFR,case-fatality,EVD,real-time,bias,estimation", "summary": "Methodological analysis of CFR estimation under different ascertainment assumptions. Naive CFR overestimates early in outbreaks due to unresolved cases. Recommended: use confirmed deaths / (confirmed deaths + confirmed recovered) once >80% of cases are resolved. Adjustment factor for healthcare access varies 2–4× across settings. R package cfr available on CRAN."},
        {"title": "Safe and dignified burial practices — impact on EVD transmission", "domain": "Outbreak Response", "tags": "safe-burial,EVD,transmission,funeral,intervention", "summary": "Systematic review of safe and dignified burial (SDB) impact on EVD transmission. SDB reduces funeral-associated transmission from 27% to <5% of all cases when adherence >85%. Key barrier: community acceptance — SDB acceptability lowest in first 72 hours after death. Trained community volunteers as intermediaries increases acceptance by 40%."},
        {"title": "R package EpiNow2 — real-time Rt estimation with reporting delays", "domain": "Statistics", "tags": "EpiNow2,Rt,reproduction-number,R,real-time,outbreak", "summary": "EpiNow2 provides Bayesian Rt estimation accounting for reporting delays and right-truncation. Validated on EVD, COVID-19, and MPOX data. Key inputs: case timeseries, serial interval distribution, reporting delay distribution. Outputs daily Rt with credible intervals. GitHub: epiforecasts/EpiNow2. Recommended over EpiEstim for real-time use due to delay correction."},
    ]

    for i, card in enumerate(library_cards, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO library_cards (id, title, domain, tags, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (100+i, card["title"], card["domain"], card["tags"], card["summary"], DT(30+i*3)))

    # ── Ideas ──────────────────────────────────────────────────────────────────
    ideas = [
        {"text": "i: Could the phylogeographic clustering in Equateur outbreaks be used to define high-risk zones for pre-positioned ring vaccination teams? Would need to overlay with bat roost distribution data", "project_id": "proj-GEN-003", "idea_type": "research", "tags": "phylogeography,ring-vaccination,pre-positioning,bat-reservoir", "domain": "Genomic Epidemiology"},
        {"text": "i: DHIS2 tracker could flag cases as 'contact of known case' vs 'community case' automatically based on contact tracing linkage — this would enable real-time chain of transmission monitoring without manual re-coding", "project_id": "proj-DHIS2-002", "idea_type": "method", "tags": "DHIS2,contact-tracing,linkage,automation", "domain": "Health Information Systems"},
        {"text": "i: The ring radius for vaccination is currently fixed at 3 generations — but our Equateur data suggests urban settings have fundamentally different contact network structure. Worth modelling optimal radius by setting type", "project_id": "proj-METH-004", "idea_type": "research", "tags": "ring-vaccination,contact-network,urban,optimal-radius", "domain": "Vaccine Epidemiology"},
        {"text": "q: If two vaccination rings overlap, how do we attribute the prevented case to a specific ring? This is the double-counting problem in the pooled VE analysis — need a principled method", "project_id": "proj-METH-004", "idea_type": "question", "tags": "ring-vaccination,overlap,attribution,VE", "domain": "Statistics"},
        {"text": "i: The 4-field gap between paper and DHIS2 form could be an opportunity — add an optional 'extended investigation' module triggered when healthcare worker exposure is suspected", "project_id": "proj-DHIS2-002", "idea_type": "method", "tags": "DHIS2,HCW,extended-form,adaptive", "domain": "Health Information Systems"},
        {"text": "i: Module 3 of the VHF course could use the DHIS2 EVD tracker as a live configuration exercise — students build a simplified tracker from scratch using test instance", "project_id": "proj-TEACH-005", "idea_type": "teaching", "tags": "DHIS2,teaching,case-study,VHF", "domain": "Teaching"},
        {"text": "n: The BEAST2 relaxed clock estimate gives a much wider introduction date CI (±21 days vs ±9 days for strict clock) — this is scientifically more honest but may be harder to communicate to policy audience", "project_id": "proj-GEN-003", "idea_type": "note", "tags": "BEAST2,molecular-clock,communication,policy", "domain": "Genomic Epidemiology"},
        {"text": "i: EpiNow2 Rt estimates could be integrated into the DHIS2 dashboard as an automated indicator — triggers alert when Rt crosses 1.0 for 3 consecutive days", "project_id": "proj-DHIS2-002", "idea_type": "method", "tags": "EpiNow2,Rt,DHIS2,alert,automation", "domain": "Health Information Systems"},
    ]

    for i, idea in enumerate(ideas, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO ideas
            (idea_id, text, project_id, idea_type, tags, created_at, domain,
             phd_relevance, feasibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 3)
        """, (f"idea-{100+i}", idea["text"], idea.get("project_id"), idea["idea_type"],
              idea["tags"], DT(i), idea["domain"], 0))

    # ── News Briefs ─────────────────────────────────────────────────────────────
    news = [
        {"title": "WHO declares end of Equateur EVD outbreak — 47 confirmed cases, 31 deaths", "domain": "Outbreak Response", "signal_strength": "high", "summary": "WHO and DRC Ministry of Health declared the end of the Equateur Province EVD outbreak today after 42 days with no new confirmed cases. 47 total confirmed cases, CFR 66%. Ring vaccination covered 94% of tier-1 contacts. Full after-action review scheduled for next month.", "source_url": "https://www.who.int/news/item/evd-equateur-2025-end", "source_type": "news", "surprise_flag": 1},
        {"title": "BEAST2 v2.7.6 released — improved relaxed clock convergence diagnostics", "domain": "Genomic Epidemiology", "signal_strength": "medium", "summary": "BEAST2 2.7.6 includes improved MCMC convergence diagnostics for relaxed clock models, reduced burn-in requirement, and a new ESS threshold warning for low-coverage genomes. Release notes recommend re-running existing analyses from v2.7.4 due to a fixed bug in the relaxed clock rate estimator.", "source_url": "https://www.beast2.org/2025/05/release-notes-v276", "source_type": "article", "surprise_flag": 1},
        {"title": "DHIS2 Academy: Outbreak Surveillance Tracker certification now available", "domain": "Health Information Systems", "signal_strength": "medium", "summary": "DHIS2 Academy launched a new certification track specifically for outbreak surveillance tracker implementation. Covers contact tracing linkage, ring vaccination modules, and real-time data quality monitoring. Free for public health practitioners. Completion in approximately 10 hours.", "source_url": "https://academy.dhis2.org/outbreak-tracker", "source_type": "news", "surprise_flag": 0},
        {"title": "New Marburg outbreak confirmed in Tanzania — genome sequences released", "domain": "Outbreak Response", "signal_strength": "high", "summary": "WHO confirmed a new Marburg virus disease cluster in Tanzania (8 cases, 5 deaths). INRB and Institut Pasteur have released the first 3 genome sequences. Phylogenetic analysis in progress. WHO is deploying a field team. Amara flagged this for monitoring — response methods overlap with EVD protocols.", "source_url": "https://www.who.int/emergencies/disease-outbreak-news/item/marburg-tanzania-2025", "source_type": "news", "surprise_flag": 1},
        {"title": "EpiNow2 v2.0 released — native DHIS2 data connector and improved delay estimation", "domain": "Statistics", "signal_strength": "medium", "summary": "EpiNow2 v2.0 adds a direct DHIS2 API connector for pulling case timeseries, improved reporting delay estimation using a mixture model, and a Shiny dashboard for real-time Rt monitoring. Now on CRAN. The DHIS2 connector is directly relevant to the EVD tracker automation idea.", "source_url": "https://epiforecasts.io/EpiNow2/news/index.html", "source_type": "article", "surprise_flag": 0},
        {"title": "OpenAlex: 23 new EVD surveillance papers indexed this week", "domain": "Outbreak Response", "signal_strength": "low", "summary": "Weekly OpenAlex scan returned 23 papers tagged with 'Ebola virus disease' + 'surveillance' published in the last 7 days. Top citation: a modelling study estimating the optimal ring vaccination radius in urban vs rural settings — directly relevant to the pooled VE analysis.", "source_url": "https://openalex.org/works?filter=concepts.id:C2909456852", "source_type": "article", "surprise_flag": 0},
        {"title": "Africa CDC: genomic surveillance capacity in Central Africa expanded to 6 new labs", "domain": "Genomic Epidemiology", "signal_strength": "medium", "summary": "Africa CDC announced funding for 6 new genomic surveillance laboratories in Central Africa, including a new node in Equateur Province DRC. Nanopore sequencing capacity being deployed. Target: 48-hour turnaround from sample to phylogenetic tree by 2026. Amara's consortium is a named technical partner.", "source_url": "https://africacdc.org/news-item/genomic-surveillance-expansion-2025", "source_type": "news", "surprise_flag": 0},
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
    brief_text = """**Today's standout:** WHO declared the end of the Equateur EVD outbreak — 47 cases, CFR 66%, ring vaccination coverage 94%. This validates your transmission chain analysis and gives you a clean final case count for the manuscript. Prioritise finalising the transmission tree today so the methods section can be drafted against resolved data.

**This week's signals:** BEAST2 v2.7.6 has a bug fix in the relaxed clock estimator — re-run your analysis before submitting the genomics preprint. The new EpiNow2 DHIS2 connector is worth testing for the automated Rt alert you sketched last week. The Marburg cluster in Tanzania is worth monitoring — response methods overlap and Africa CDC may ask for support.

**Tasks overdue or due today:** Transmission tree finalisation (overdue — awaiting INRB sequences), attack rate calculation (2 days overdue). The DHIS2 pilot in Mbandaka is due in 5 days — confirm field team training is scheduled."""

    conn.execute("""
        INSERT OR REPLACE INTO daily_insights (id, insight_date, content, generated_at)
        VALUES (1, ?, ?, ?)
    """, (D(0), brief_text, DT(0, 7)))

    # ── Agent Runs ─────────────────────────────────────────────────────────────
    agent_runs = [
        {"agent_slug": "librarian", "task_summary": "Literature search: rVSV-ZEBOV ring vaccination effectiveness 2018–2025", "input_path": "inputs/searches/ring-vax-evd-2025.md", "output_path": "outputs/reviews/librarian/2026-05-13_ring-vax-effectiveness.md", "status": "completed", "input_tokens": 1240, "output_tokens": 3890, "model": "claude-sonnet-4-6", "created_at": DT(2)},
        {"agent_slug": "epidemiologist", "task_summary": "Methodology review: transmission tree and secondary attack rate estimation", "input_path": "inputs/code/transmission-tree-v2.R", "output_path": "outputs/reviews/epidemiologist/2026-05-11_transmission-tree-review.md", "status": "completed", "input_tokens": 2100, "output_tokens": 4200, "model": "claude-opus-4-7", "created_at": DT(4)},
        {"agent_slug": "writing-partner", "task_summary": "Methods section draft: outbreak investigation and transmission analysis", "input_path": "inputs/drafts/manuscript-methods-v1.md", "output_path": "outputs/reviews/writing-partner/2026-05-10_manuscript-methods.md", "status": "completed", "input_tokens": 3400, "output_tokens": 5600, "model": "claude-sonnet-4-6", "created_at": DT(5)},
        {"agent_slug": "dhis2-expert", "task_summary": "DHIS2 tracker metadata design: EVD case notification with contact tracing linkage", "input_path": "inputs/dhis2/evd-tracker-metadata-draft.json", "output_path": "outputs/reviews/dhis2-expert/2026-05-09_evd-tracker-review.md", "status": "completed", "input_tokens": 4200, "output_tokens": 6100, "model": "claude-sonnet-4-6", "created_at": DT(6)},
        {"agent_slug": "meeting-memory", "task_summary": "EVD Outbreak Review meeting — structured brief and action items", "input_path": "inputs/meetings/evd-outbreak-review-2026-05-12.txt", "output_path": "outputs/reviews/meeting-memory/2026-05-13_evd-outbreak-review.md", "status": "completed", "input_tokens": 2800, "output_tokens": 3400, "model": "claude-haiku-4-5", "created_at": DT(2)},
        {"agent_slug": "data-analyst", "task_summary": "Profile ring vaccination dataset: harmonise 4 outbreak date conventions", "input_path": "inputs/data/ring-vax-pooled-raw.csv", "output_path": "outputs/reviews/data-analyst/2026-05-12_ring-vax-profile.md", "status": "completed", "input_tokens": 1800, "output_tokens": 2900, "model": "claude-sonnet-4-6", "created_at": DT(3)},
        {"agent_slug": "news-radar", "task_summary": "Morning brief: EVD + VHF + genomic surveillance signals", "input_path": "", "output_path": "outputs/reviews/news-radar/2026-05-15_morning-brief.md", "status": "completed", "input_tokens": 890, "output_tokens": 1200, "model": "claude-haiku-4-5", "created_at": DT(0, 7)},
        {"agent_slug": "course-builder", "task_summary": "VHF field investigation course — module outline 1–4", "input_path": "", "output_path": "outputs/reviews/course-builder/2026-05-08_vhf-course-outline.md", "status": "completed", "input_tokens": 2200, "output_tokens": 4800, "model": "claude-sonnet-4-6", "created_at": DT(7)},
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
        {"title": "Genomic Epidemiology — BEAST2 and Phylogeography", "category": "genomics", "slug": "genomic-epi-beast2", "progress_pct": 55, "total_modules": 8, "completed_modules": 4, "status": "active", "project_id": "proj-GEN-003"},
        {"title": "DHIS2 Tracker Programs — Outbreak Surveillance", "category": "health-informatics", "slug": "dhis2-tracker-outbreak", "progress_pct": 40, "total_modules": 6, "completed_modules": 2, "status": "active", "project_id": "proj-DHIS2-002"},
        {"title": "Applied Survival Analysis and Time-to-Event Methods", "category": "statistics", "slug": "survival-analysis-r", "progress_pct": 100, "total_modules": 7, "completed_modules": 7, "status": "completed"},
        {"title": "Scientific Writing for Rapid Communications in Outbreak Response", "category": "writing", "slug": "rapid-comms-writing", "progress_pct": 20, "total_modules": 4, "completed_modules": 1, "status": "active", "project_id": "proj-EVD-001"},
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
    print(f"  Researcher: Dr. Amara Diallo — Senior Epidemiologist, WHO AFRO")
    print(f"  Projects: {len(projects)} active")
    print(f"  Tasks: {len(tasks)} (including overdue + upcoming)")
    print(f"  Meetings: {len(meetings)} (with full transcripts)")
    print(f"  Library cards: {len(library_cards)}")
    print(f"  Ideas: {len(ideas)}")
    print(f"  News briefs: {len(news)}")
    print(f"  Agent runs: {len(agent_runs)}")
    print(f"  Learning courses: {len(courses)}")
    print(f"\n  User config and preferences written to system/config/")
    print(f"\n  Open http://127.0.0.1:8080 and start the dashboard to take screenshots.")


def generate_linelist(output_path: Path):
    """Generate a synthetic EpiRHandbook-style EVD case linelist (~150 rows)."""
    import csv
    import random

    rng = random.Random(42)  # fixed seed → reproducible output

    HEALTH_ZONES  = ["Mbandaka", "Bikoro", "Wangata", "Itipo"]
    ZONE_WEIGHTS  = [0.35, 0.30, 0.20, 0.15]
    OUTBREAK_START = TODAY - timedelta(days=90)
    SERIAL_MEAN    = 8
    SERIAL_SD      = 2

    cases: list[dict] = []

    # Generation 0 — index case
    index = {
        "case_id": "EVD-EQ-001",
        "generation": 0,
        "date_onset": OUTBREAK_START,
        "source_case_id": "",
        "health_zone": "Bikoro",
        "gender": "male",
        "age": 42,
        "healthcare_worker": "no",
        "contact_of_known_case": "no",
        "ring_vaccinated": "no",
        "outcome": "Died",
    }
    cases.append(index)

    counter        = 2
    current_gen    = [index]

    for gen in range(1, 9):
        if len(cases) >= 150 or not current_gen:
            break
        next_gen = []
        r_eff = max(0.4, 2.0 - gen * 0.28)

        for source in current_gen:
            if len(cases) >= 150:
                break
            n_sec = rng.choices([0, 1, 1, 2, 3], weights=[20, 30, 25, 15, 10])[0]
            if rng.random() > r_eff / 2:
                n_sec = max(0, n_sec - 1)

            for _ in range(n_sec):
                if len(cases) >= 150:
                    break
                interval = max(5, int(rng.gauss(SERIAL_MEAN, SERIAL_SD)))
                onset    = source["date_onset"] + timedelta(days=interval)
                if onset > TODAY:
                    continue

                zone = source["health_zone"] if rng.random() < 0.65 else rng.choices(HEALTH_ZONES, weights=ZONE_WEIGHTS)[0]
                hcw  = "yes" if rng.random() < 0.13 else "no"
                known_contact = "yes" if rng.random() < 0.76 else "no"

                ring_prob     = min(0.92, 0.08 + gen * 0.11)
                ring_vax      = "yes" if (known_contact == "yes" and rng.random() < ring_prob) else "no"

                cfr = 0.66
                if ring_vax == "yes":
                    cfr = 0.22
                if hcw == "yes":
                    cfr = min(0.85, cfr + 0.10)
                outcome = "Died" if rng.random() < cfr else "Recovered"

                c = {
                    "case_id": f"EVD-EQ-{counter:03d}",
                    "generation": gen,
                    "date_onset": onset,
                    "source_case_id": source["case_id"],
                    "health_zone": zone,
                    "gender": rng.choice(["male", "female"]),
                    "age": max(1, int(rng.gauss(35, 14))),
                    "healthcare_worker": hcw,
                    "contact_of_known_case": known_contact,
                    "ring_vaccinated": ring_vax,
                    "outcome": outcome,
                }
                cases.append(c)
                next_gen.append(c)
                counter += 1
        current_gen = next_gen

    rows = []
    for c in cases:
        onset      = c["date_onset"]
        hosp_date  = onset + timedelta(days=rng.randint(2, 5))
        out_date   = hosp_date + timedelta(days=rng.randint(5, 12))
        resolved   = out_date <= TODAY
        rows.append({
            "case_id":              c["case_id"],
            "generation":           c["generation"],
            "date_onset":           onset.strftime("%Y-%m-%d"),
            "date_hospitalisation": hosp_date.strftime("%Y-%m-%d"),
            "date_outcome":         out_date.strftime("%Y-%m-%d") if resolved else "",
            "outcome":              c["outcome"] if resolved else "",
            "gender":               c["gender"],
            "age":                  c["age"],
            "health_zone":          c["health_zone"],
            "province":             "Equateur",
            "healthcare_worker":    c["healthcare_worker"],
            "ring_vaccinated":      c["ring_vaccinated"],
            "contact_of_known_case": c["contact_of_known_case"],
            "source_case_id":       c["source_case_id"],
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id", "generation", "date_onset", "date_hospitalisation",
        "date_outcome", "outcome", "gender", "age", "health_zone",
        "province", "healthcare_worker", "ring_vaccinated",
        "contact_of_known_case", "source_case_id",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Linelist written: {output_path} ({len(rows)} cases)")


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
