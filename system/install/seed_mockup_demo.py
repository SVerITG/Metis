"""
seed_mockup_demo.py — the sample workspace a new user can explore before setting up.

Researcher persona (fictional): Dr. Amélie Fontaine
  Role: Senior Health Economist · Global Health Policy
  Focus: economic evaluation · health financing / UHC · global health policy
  Activities: builds R Shiny dashboards, writes policy briefs, teaches health economics
  Topics span public health broadly — malaria, NCDs, immunization, pandemic
  preparedness, universal health coverage — so any researcher recognises their
  own work in the demo.

Everything here is invented. The news items are labelled as samples, attributed
to no real organisation, and link to example.org.

    python seed_mockup_demo.py --load       # add the demo to this computer's Metis
    python seed_mockup_demo.py --unload     # remove exactly what --load added
    python seed_mockup_demo.py --db X.db    # seed another database (screenshots)

--load records every row it adds (system/config/.demo-rows.json) and refuses to
run in a workspace that already holds the person's own projects, tasks, ideas,
meetings or notes. --unload deletes exactly those rows and restores the settings
the demo replaced: "Exit demo" used to remove the banner and leave the sample
data mixed into the person's real workspace.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

METIS_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = METIS_ROOT / "system" / "config"
MANIFEST = CONFIG_DIR / ".demo-rows.json"

# Tables the demo writes to, and the ones that mean "this workspace is in use".
DEMO_TABLES = ("projects", "tasks", "meetings", "ideas", "idea_links", "personal_notes",
               "journal_entries", "contacts", "library_cards", "literature_metadata",
               "news_briefs", "daily_insights", "agent_runs", "reflexion_log",
               "learning_courses", "user_config")
OWN_CONTENT = ("projects", "tasks", "ideas", "meetings", "personal_notes", "journal_entries")


def live_db_path() -> Path:
    """The database the dashboard and server read (never the retired system/app/data)."""
    import os
    try:
        from metis_mcp.config import resolve_live_db
        return resolve_live_db(METIS_ROOT)
    except ImportError:
        if os.environ.get("METIS_DB"):
            return Path(os.environ["METIS_DB"])
        data_dir = os.environ.get("METIS_DATA_DIR") or os.path.join(
            os.path.expanduser("~"), ".local", "share", "metis")
        return Path(data_dir) / "metis.sqlite"

TODAY = datetime.now()
D = lambda d: (TODAY - timedelta(days=d)).strftime("%Y-%m-%d")
DT = lambda d, h=8: (TODAY - timedelta(days=d)).replace(hour=h, minute=0).strftime("%Y-%m-%d %H:%M:%S")
FUTURE = lambda d: (TODAY + timedelta(days=d)).strftime("%Y-%m-%d")


def seed(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row

    # ── User config ────────────────────────────────────────────────────────────
    prefs = {
        "display_name": "Amélie",
        "role": "Senior Health Economist · Global Health Policy",
        "interests": ["health economics", "cost-effectiveness analysis",
                      "universal health coverage", "health financing",
                      "malaria control", "non-communicable diseases",
                      "immunization", "global health policy", "health systems",
                      "data dashboards"],
        "news_topics": ["WHO", "Global Fund", "Gavi", "universal health coverage",
                        "health financing", "pandemic preparedness", "NCDs",
                        "malaria", "global health policy"],
        "pubmed_query": "health economics[Title/Abstract] OR cost-effectiveness[Title] OR universal health coverage[Title/Abstract]",
        "active_model": "sonnet",
        "theme": "light",
        "density": "comfortable",
    }

    user_config = {
        "user": {
            "name": "Amélie Fontaine",
            "role": "Senior Health Economist",
            "language": "en",
            "general_context": (
                "Health economist and global-health policy researcher. Works across "
                "cost-effectiveness analysis, health financing and universal health "
                "coverage. Builds interactive R Shiny data dashboards, writes policy "
                "briefs for ministries and WHO, and teaches health economics to MPH "
                "students. Topics span malaria, NCDs, immunization and pandemic preparedness."
            ),
            "active_contexts": ["general", "health economics", "global health policy"],
            "specialist_contexts": [
                {"name": "Health economics", "description": "Economic evaluation, cost-effectiveness analysis, decision modelling, ICER thresholds"},
                {"name": "Global health policy", "description": "Universal health coverage, health financing, donor transition, priority-setting"},
                {"name": "Data dashboards", "description": "R Shiny dashboards for health-system and financing indicators"},
            ],
        },
        "research": {
            "field": "Public health · Health economics · Global health policy",
            "interests": ["health economics", "cost-effectiveness analysis", "universal health coverage", "global health policy", "health financing"],
            "specific_focus": "Economic evaluation of global-health interventions, UHC financing in LMICs, NCD and malaria burden",
        },
        "data_sensitivity": {"patient_data": True, "embargoed_results": True, "compliance": ["GDPR"]},
    }

    # Demo identity goes into the DEMO DB only — the dashboard reads the user
    # name from the user_config table (routers.today._user_name), so this keeps
    # the demo fully isolated and NEVER touches the real system/config files.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_config "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '', updated_at TEXT)"
    )
    for _k, _v in [
        ("user_name", "Amélie Fontaine"),
        ("user_role", "Senior Health Economist · Global Health Policy"),
        ("user_field", "Public health · Health economics · Global health policy"),
        ("onboarded", "true"),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO user_config (key, value, updated_at) "
            "VALUES (?, ?, datetime('now'))",
            (_k, _v),
        )

    # ── Projects ───────────────────────────────────────────────────────────────
    projects = [
        {
            "project_id": "proj-CEA-001",
            "title": "Cost-Effectiveness of Seasonal Malaria Mass Drug Administration",
            "description": "Economic evaluation of seasonal mass drug administration for malaria across three countries. Markov model, DALYs averted, ICERs benchmarked against WHO-CHOICE and opportunity-cost thresholds. Manuscript under review at Value in Health.",
            "domain": "Health Economics",
            "status": "active",
            "priority": "high",
            "next_step": "Respond to reviewer comments on the discount-rate sensitivity analysis",
            "external_path": "C:/Users/Amelie/Documents/research/malaria-mda-cea",
            "github_url": "https://example.org/metis-demo/code/malaria-mda-cea",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amelie/Documents/research/malaria-mda-cea/analysis.Rproj"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/research/malaria-mda-cea"},
                {"label": "GitHub", "type": "github", "url": "https://example.org/metis-demo/code/malaria-mda-cea"},
            ]),
            "created_at": DT(150),
        },
        {
            "project_id": "proj-DASH-002",
            "title": "Global Health Financing Dashboard (R Shiny)",
            "description": "Interactive R Shiny dashboard tracking health expenditure, donor financing and UHC service-coverage indicators across 40 countries. Built as a reusable template — modular golem architecture, bslib theme, leaflet maps, reactive WHO GHED / World Bank data feeds. Used by the financing working group.",
            "domain": "Software",
            "status": "active",
            "priority": "medium",
            "next_step": "Add the 2024 GHED data release and a domestic-vs-external financing split view",
            "external_path": "C:/Users/Amelie/Documents/health-financing-dashboard",
            "github_url": "https://example.org/metis-demo/code/health-financing-dashboard",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amelie/Documents/health-financing-dashboard/app.Rproj"},
                {"label": "Live Dashboard", "type": "url", "url": "http://financing-wg.local/dashboard"},
                {"label": "GitHub", "type": "github", "url": "https://example.org/metis-demo/code/health-financing-dashboard"},
            ]),
            "created_at": DT(95),
        },
        {
            "project_id": "proj-POL-003",
            "title": "Policy Brief — UHC Financing in West Africa",
            "description": "Eight-page policy brief for a regional health-ministers forum on closing the universal-health-coverage financing gap: domestic resource mobilisation, efficiency gains, and managing donor transition. Commissioned by WHO AFRO.",
            "domain": "Health Policy",
            "status": "active",
            "priority": "high",
            "next_step": "Finalise the financing-gap figure and the three-policy-options box",
            "external_path": "C:/Users/Amelie/Documents/policy/uhc-financing-brief",
            "github_url": "",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open Brief Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/policy/uhc-financing-brief"},
                {"label": "Overleaf", "type": "url", "url": "https://example.org/metis-demo/docs/uhc-financing-brief"},
            ]),
            "created_at": DT(40),
        },
        {
            "project_id": "proj-TEACH-004",
            "title": "Course: Health Economics for Global Health (MPH)",
            "description": "Graduate course, 10 modules: demand for health, economic evaluation, health financing, UHC, equity, behavioural economics, priority-setting. First delivery spring 2027.",
            "domain": "Teaching",
            "status": "active",
            "priority": "low",
            "next_step": "Draft Module 5 (health financing) around a live policy-brief case study",
            "external_path": "C:/Users/Amelie/Documents/courses/health-economics-mph",
            "github_url": "",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open Course Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/courses/health-economics-mph"},
                {"label": "VS Code", "type": "vscode", "path": "C:/Users/Amelie/Documents/courses/health-economics-mph"},
            ]),
            "created_at": DT(30),
        },
        {
            "project_id": "proj-NCD-005",
            "title": "Economic Burden of NCDs in Low-Income Settings",
            "description": "Multi-country estimation of the macroeconomic and household burden of diabetes and hypertension. Cost-of-illness plus catastrophic-health-expenditure analysis using national household surveys from six countries.",
            "domain": "Non-Communicable Diseases",
            "status": "active",
            "priority": "medium",
            "next_step": "Harmonise catastrophic-expenditure definitions across the six survey datasets",
            "external_path": "C:/Users/Amelie/Documents/research/ncd-burden",
            "github_url": "https://example.org/metis-demo/code/ncd-economic-burden",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amelie/Documents/research/ncd-burden/analysis.Rproj"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/research/ncd-burden"},
            ]),
            "created_at": DT(60),
        },
        {
            "project_id": "proj-GRANT-006",
            "title": "Grant — Pandemic Preparedness Financing (Wellcome)",
            "description": "Proposal for a 3-year grant on sustainable financing mechanisms for pandemic preparedness in LMICs. Budget €1.4M. Value-for-money framework, country case studies. Concept note accepted; full proposal in preparation.",
            "domain": "Grant",
            "status": "active",
            "priority": "high",
            "next_step": "Draft the value-for-money framework and the budget justification",
            "external_path": "C:/Users/Amelie/Documents/grants/pandemic-financing",
            "github_url": "",
            "launcher_type": "vscode",
            "launchers": json.dumps([
                {"label": "Open Proposal Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/grants/pandemic-financing"},
                {"label": "Overleaf", "type": "url", "url": "https://example.org/metis-demo/docs/pandemic-financing-proposal"},
            ]),
            "created_at": DT(45),
        },
        {
            "project_id": "proj-IMM-007",
            "title": "Immunization Investment Case — Gavi Transition",
            "description": "Investment case for a country transitioning out of Gavi support: return on investment of sustaining routine immunization, co-financing scenarios, and the economic cost of coverage backsliding.",
            "domain": "Health Policy",
            "status": "active",
            "priority": "medium",
            "next_step": "Run the ROI scenarios for three co-financing trajectories",
            "external_path": "C:/Users/Amelie/Documents/research/gavi-investment-case",
            "github_url": "",
            "launcher_type": "rstudio",
            "launchers": json.dumps([
                {"label": "Open in RStudio", "type": "rstudio", "path": "C:/Users/Amelie/Documents/research/gavi-investment-case/analysis.Rproj"},
                {"label": "Open Folder", "type": "folder", "path": "C:/Users/Amelie/Documents/research/gavi-investment-case"},
            ]),
            "created_at": DT(70),
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
        # Malaria MDA cost-effectiveness
        {"task_id": "task-001", "project_id": "proj-CEA-001", "title": "Respond to reviewer comments on discount-rate sensitivity", "status": "open", "due_date": D(0), "category": "writing", "notes": "Reviewer 2 wants 0% and 5% discount-rate scenarios alongside the 3% base case."},
        {"task_id": "task-002", "project_id": "proj-CEA-001", "title": "Re-run ICER analysis with 2024 unit costs", "status": "open", "due_date": D(2), "category": "analysis", "notes": ""},
        {"task_id": "task-003", "project_id": "proj-CEA-001", "title": "Update probabilistic sensitivity analysis (10,000 draws)", "status": "done", "due_date": D(6), "category": "analysis"},
        # NCD burden
        {"task_id": "task-004", "project_id": "proj-NCD-005", "title": "Harmonise catastrophic-expenditure definitions across 6 surveys", "status": "open", "due_date": FUTURE(4), "category": "data", "notes": "10% and 25% of household consumption thresholds; WHO vs World Bank definitions."},
        {"task_id": "task-005", "project_id": "proj-NCD-005", "title": "Estimate household cost-of-illness for diabetes", "status": "open", "due_date": FUTURE(9), "category": "analysis"},
        # UHC policy brief
        {"task_id": "task-006", "project_id": "proj-POL-003", "title": "Finalise the financing-gap figure", "status": "open", "due_date": D(0), "category": "writing", "notes": "Pair the US$370bn gap with the efficiency-gains evidence — that's the brief's headline."},
        {"task_id": "task-007", "project_id": "proj-POL-003", "title": "Draft the three policy-options box", "status": "open", "due_date": FUTURE(3), "category": "writing"},
        {"task_id": "task-008", "project_id": "proj-POL-003", "title": "Circulate brief to WHO AFRO focal point for comment", "status": "open", "due_date": FUTURE(7), "category": "dissemination"},
        # Financing dashboard
        {"task_id": "task-009", "project_id": "proj-DASH-002", "title": "Add the 2024 GHED data release", "status": "open", "due_date": FUTURE(9), "category": "software"},
        {"task_id": "task-010", "project_id": "proj-DASH-002", "title": "Build the domestic-vs-external financing split view", "status": "open", "due_date": FUTURE(16), "category": "software"},
        {"task_id": "task-011", "project_id": "proj-DASH-002", "title": "Refactor the indicator module so it can be reused for other dashboards", "status": "open", "due_date": FUTURE(18), "category": "software", "notes": "Generalise the data-feed + map module — could template an immunization-coverage or NCD-burden dashboard."},
        # Teaching
        {"task_id": "task-012", "project_id": "proj-TEACH-004", "title": "Draft Module 5 (health financing) around a policy-brief case study", "status": "open", "due_date": FUTURE(14), "category": "teaching"},
        {"task_id": "task-013", "project_id": "proj-TEACH-004", "title": "Curate reading list for Module 2 (economic evaluation)", "status": "done", "due_date": D(7), "category": "teaching"},
        # Pandemic financing grant
        {"task_id": "task-014", "project_id": "proj-GRANT-006", "title": "Draft the value-for-money framework", "status": "open", "due_date": FUTURE(6), "category": "grant"},
        {"task_id": "task-015", "project_id": "proj-GRANT-006", "title": "Budget justification + full costing", "status": "open", "due_date": FUTURE(10), "category": "grant"},
        {"task_id": "task-016", "project_id": "proj-GRANT-006", "title": "Collect letters of support from partner institutions", "status": "open", "due_date": FUTURE(20), "category": "grant"},
        {"task_id": "task-017", "project_id": "proj-GRANT-006", "title": "Submit concept note", "status": "done", "due_date": D(12), "category": "grant"},
        # Gavi immunization investment case
        {"task_id": "task-018", "project_id": "proj-IMM-007", "title": "Run ROI scenarios for three co-financing trajectories", "status": "open", "due_date": FUTURE(5), "category": "analysis"},
        {"task_id": "task-019", "project_id": "proj-IMM-007", "title": "Meet Gavi country team on the transition timeline", "status": "open", "due_date": FUTURE(8), "category": "meeting"},
        {"task_id": "task-020", "project_id": "proj-IMM-007", "title": "Draft the coverage-backsliding cost estimate", "status": "open", "due_date": FUTURE(12), "category": "analysis"},
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
            "title": "Global Health Financing Working Group — UHC Gap Review",
            "meeting_date": D(2),
            "domain": "Health Policy",
            "project": "proj-POL-003",
            "meeting_type": "working-group",
            "attendees": "Dr. Fontaine, Dr. Okonkwo (WHO AFRO, health financing), Prof. Ross (LSHTM), Mr. Mensah (World Bank), Ministry of Health representative",
            "transcript": """The new global monitoring report (a sample news item) puts the LMIC universal-health-coverage financing gap at roughly US$370 billion per year — wider than the pre-pandemic estimate. The group debated how the policy brief should frame this.

Prof. Ross argued strongly against a 'just spend more' message: a commonly cited estimate puts 20–40% of health spending lost to inefficiency, so the brief should pair the financing gap with concrete efficiency-gains evidence and domestic resource mobilisation. Mr. Mensah offered the latest World Bank health-expenditure data as the comparator.

Discussion on donor transition: several countries are losing Global Fund and Gavi eligibility simultaneously. Amélie noted this is exactly the immunization investment-case problem and could be a shared analysis.""",
            "decisions": "1. Brief frames the gap alongside efficiency gains + domestic resource mobilisation (not 'spend more')\n2. Amélie leads the financing-gap figure and the three-policy-options box\n3. Reuse the financing dashboard's expenditure data for the brief's comparator",
            "action_items": "- Amélie: finalise the financing-gap figure by end of week\n- Mr. Mensah: share the 2024 GHED extract\n- Dr. Okonkwo: route the draft to the WHO AFRO focal point\n- Prof. Ross: send the efficiency-gains references",
            "duration_minutes": 90,
            "status": "filed",
            "created_at": DT(2),
        },
        {
            "meeting_id": "meet-002",
            "title": "Co-author Call — Malaria MDA Cost-Effectiveness Revision",
            "meeting_date": D(5),
            "domain": "Health Economics",
            "project": "proj-CEA-001",
            "meeting_type": "research",
            "attendees": "Dr. Fontaine, Prof. Ross (LSHTM, senior author), Dr. Herrera (modelling co-author)",
            "transcript": """Reviewer comments on the Value in Health submission reviewed. The main ask is a fuller discount-rate sensitivity analysis (0%, 3%, 5%) and an explicit statement of the cost-effectiveness threshold used.

Prof. Ross suggested framing the threshold debate around the iDSI reference case rather than a single WHO-CHOICE multiple of GDP — reviewers in this space expect it. Dr. Herrera will re-run the Markov model with 2024 unit costs.

Agreed to add an extended cost-effectiveness analysis (ECEA) appendix showing financial-risk-protection gains — strengthens the equity argument.""",
            "decisions": "1. Add 0/3/5% discount-rate scenarios\n2. Frame thresholds via the iDSI reference case\n3. Add an ECEA appendix on financial-risk protection",
            "action_items": "- Amélie: draft the discount-rate sensitivity + threshold paragraph\n- Dr. Herrera: re-run Markov model with 2024 unit costs\n- Prof. Ross: review the ECEA appendix outline",
            "duration_minutes": 60,
            "status": "filed",
            "created_at": DT(5),
        },
        {
            "meeting_id": "meet-003",
            "title": "WHO AFRO — UHC Policy Brief Scope",
            "meeting_date": D(8),
            "domain": "Health Policy",
            "project": "proj-POL-003",
            "meeting_type": "stakeholder",
            "attendees": "Dr. Fontaine, Dr. Okonkwo (WHO AFRO), Regional health-financing adviser",
            "transcript": """WHO AFRO confirmed the brief is for the regional health-ministers forum in September. Audience is policy, not technical — keep it to eight pages, lead with the headline number and three actionable options.

Agreed structure: (1) the financing gap, (2) why 'spend more' alone won't work, (3) three options — domestic revenue, efficiency gains, smart donor transition. Each option needs an illustrative country example.

Dr. Okonkwo asked for a one-page executive summary that a minister could read in five minutes.""",
            "decisions": "1. Eight pages + a one-page executive summary\n2. Three policy options, each with a country example\n3. Deadline: first full draft in two weeks",
            "action_items": "- Amélie: produce the full draft + executive summary\n- Dr. Okonkwo: supply two country examples for donor transition",
            "duration_minutes": 45,
            "status": "filed",
            "created_at": DT(8),
        },
        {
            "meeting_id": "meet-004",
            "title": "NCD Economic Burden Consortium — Data Sharing",
            "meeting_date": D(1),
            "domain": "Non-Communicable Diseases",
            "project": "proj-NCD-005",
            "meeting_type": "consortium",
            "attendees": "Dr. Fontaine, Dr. Herrera, country-survey leads (6 countries), Prof. Ross",
            "transcript": """The consortium agreed a common analysis plan for the household cost-of-illness work. Key issue resolved: the catastrophic-expenditure threshold — both 10% and 25% of household consumption will be reported, using the WHO definition as primary.

Open question: productivity-loss method. Dr. Herrera favours the human-capital approach; Prof. Ross wants a friction-cost sensitivity analysis. Both will be reported.

Two countries' 2023 survey microdata are still under data-use review; expected within three weeks.""",
            "decisions": "1. Catastrophic expenditure reported at 10% and 25% thresholds (WHO primary)\n2. Productivity loss: human-capital base case + friction-cost sensitivity\n3. Pooled dataset on the shared OSF project by month-end",
            "action_items": "- Amélie: harmonise catastrophic-expenditure code across the six surveys\n- Dr. Herrera: implement both productivity-loss methods\n- Country leads: clear the two pending data-use agreements",
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
        {"title": "Reference case for economic evaluation in global health (iDSI)", "domain": "Health Economics", "tags": "economic-evaluation,reference-case,iDSI,methods", "summary": "Defines an 11-principle reference case for cost-effectiveness analysis of global-health interventions — perspective, discount rate, threshold, equity. Now the de-facto standard reviewers expect. Directly relevant to the malaria MDA paper's threshold framing."},
        {"title": "Disease Control Priorities, 3rd Edition — cost-effective interventions", "domain": "Global Health", "tags": "DCP3,cost-effectiveness,priority-setting", "summary": "Synthesis of cost-effectiveness evidence across 21 volumes. Defines an essential UHC package of 218 interventions. Key reference for priority-setting in low-income settings."},
        {"title": "WHO guide to cost-effectiveness analysis (WHO-CHOICE)", "domain": "Health Economics", "tags": "WHO-CHOICE,thresholds,CEA,methods", "summary": "Generalised CEA methodology and the original GDP-multiple threshold guidance. Useful but increasingly superseded by opportunity-cost thresholds — note the critique when citing."},
        {"title": "The Lancet Commission on Investing in Health — Global Health 2035", "domain": "Health Policy", "tags": "investing,convergence,Lancet-Commission,financing", "summary": "Argues a 'grand convergence' in health is achievable within a generation with the right investment. The economic case for health spending as investment, not cost. Foundational for the pandemic-financing grant framing."},
        {"title": "Global Burden of Disease 2021 — the rising NCD share", "domain": "Public Health", "tags": "GBD,DALYs,NCD,burden", "summary": "Latest GBD estimates: NCDs now account for ~74% of global deaths, with the fastest rises in low-income settings. DALY methodology and the epidemiological transition. Core comparator for the NCD burden project."},
        {"title": "Health financing for universal coverage — WHO World Health Report", "domain": "Health Financing", "tags": "UHC,financing,domestic-revenue,efficiency", "summary": "The three financing challenges for UHC: raising funds, reducing reliance on out-of-pocket payments, and improving efficiency. a commonly cited estimate puts 20–40% of health spending lost to waste. Headline evidence for the UHC brief."},
        {"title": "Cost-effectiveness of mass drug administration for malaria", "domain": "Health Economics", "tags": "malaria,MDA,cost-effectiveness,DALYs", "summary": "Review of economic evaluations of malaria mass drug administration. Cost per person treated low at scale; cost per DALY averted depends strongly on transmission intensity and coverage. Direct benchmark for the CEA paper."},
        {"title": "The global economic burden of non-communicable diseases", "domain": "Non-Communicable Diseases", "tags": "NCD,economic-burden,macroeconomic", "summary": "Projects the cumulative macroeconomic loss from NCDs at tens of trillions of dollars over 2011–2030. Human-capital and value-of-lost-output approaches compared. Framing reference for the NCD burden project."},
        {"title": "Return on investment from childhood immunization in LMICs", "domain": "Immunization", "tags": "immunization,ROI,investment-case,Gavi", "summary": "Estimates a 16:1 return on immunization investment using a cost-of-illness approach, rising to 44:1 including broader economic and social value. Methodological backbone for the Gavi transition investment case."},
        {"title": "Financing pandemic preparedness — G20 High-Level Panel", "domain": "Health Policy", "tags": "pandemic,financing,preparedness,global-public-good", "summary": "Estimates an annual financing need of ~US$15bn for pandemic preparedness as a global public good, and proposes financing mechanisms. Core source for the Wellcome grant value-for-money framework."},
    ]

    for i, card in enumerate(library_cards, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO library_cards (id, title, domain, tags, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (100+i, card["title"], card["domain"], card["tags"], card["summary"], DT(30+i*3)))

    # ── Ideas ──────────────────────────────────────────────────────────────────
    ideas = [
        {"text": "i: An extended cost-effectiveness analysis (ECEA) would strengthen the malaria MDA paper — it shows financial-risk-protection gains, not just DALYs averted. Reviewers in this space respond to the equity framing.", "project_id": "proj-CEA-001", "idea_type": "research", "tags": "ECEA,equity,CEA,malaria", "domain": "Health Economics", "phd_relevance": 4},
        {"text": "i: The financing dashboard's data-feed module is indicator-agnostic — I could drive an immunization-coverage dashboard with the same golem skeleton, just a new data contract.", "project_id": "proj-DASH-002", "idea_type": "method", "tags": "dashboard,reuse,immunization,golem", "domain": "Software", "phd_relevance": 2},
        {"text": "i: The UHC financing brief could become a teaching case study for Module 5 — students rebuild the financing-gap calculation themselves, then argue for one of the three options.", "project_id": "proj-POL-003", "idea_type": "teaching", "tags": "teaching,UHC,case-study,financing", "domain": "Health Policy", "phd_relevance": 2},
        {"text": "q: How sensitive is the NCD burden estimate to the discount rate and the productivity-loss method (human-capital vs friction-cost)? Could be a methods box on its own.", "project_id": "proj-NCD-005", "idea_type": "question", "tags": "discount-rate,cost-of-illness,methods", "domain": "Health Economics", "phd_relevance": 3},
        {"text": "i: Pandemic-preparedness financing needs a value-for-money framework — I can borrow the ICER logic from the malaria MDA model, just with a different time horizon and a global-public-good lens.", "project_id": "proj-GRANT-006", "idea_type": "research", "tags": "pandemic,value-for-money,financing", "domain": "Health Policy", "phd_relevance": 2},
        {"text": "n: Reviewer 2 on the MDA paper is almost certainly from the iDSI network — the threshold question matches their reference-case language exactly. Address it head-on with the reference case.", "project_id": "proj-CEA-001", "idea_type": "note", "tags": "peer-review,reference-case,thresholds", "domain": "Health Economics", "phd_relevance": 1},
        {"text": "i: The new World Bank health-expenditure data is out — useful comparator for the UHC brief's domestic-financing argument, and it plugs straight into the dashboard.", "project_id": "proj-POL-003", "idea_type": "literature", "tags": "World-Bank,financing,UHC,GHED", "domain": "Health Policy", "phd_relevance": 1},
        {"text": "i: An NCD-vs-infectious-disease burden comparison could frame the NCD paper's introduction — the 'double burden' narrative resonates with funders and ministries alike.", "project_id": "proj-NCD-005", "idea_type": "research", "tags": "NCD,infectious-disease,double-burden,framing", "domain": "Public Health", "phd_relevance": 2},
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
    # Sample news. Every item is invented for the demo, so none is attributed to a
    # real organisation and every link goes to example.org: a published demo must
    # not put a made-up figure in a real institution's mouth, or send someone to
    # a real page that does not say what the card claims.
    news = [
        {"title": "Sample report: financing gap for universal health coverage widens", "domain": "Health Policy", "signal_strength": "high", "summary": "(Sample item.) A global monitoring report finds the annual gap to reach universal health coverage in low- and middle-income countries has widened, driven by debt distress and stalled domestic revenue, and stresses efficiency gains alongside more spending.", "source_url": "https://example.org/metis-demo/news-1", "source_type": "news", "surprise_flag": 1},
        {"title": "Sample: a major health fund sets its next replenishment target", "domain": "Global Health", "signal_strength": "high", "summary": "(Sample item.) A multilateral health fund sets a higher target for its next three-year cycle, warning that flat donor funding threatens recent gains; co-financing rules for transitioning countries tighten.", "source_url": "https://example.org/metis-demo/news-2", "source_type": "news", "surprise_flag": 0},
        {"title": "Sample: vaccine-alliance strategy focuses on zero-dose children", "domain": "Immunization", "signal_strength": "medium", "summary": "(Sample item.) A new strategic period prioritises reaching children who have had no vaccines at all, and strengthens country co-financing as more countries approach transition. Relevant to the transition project.", "source_url": "https://example.org/metis-demo/news-3", "source_type": "news", "surprise_flag": 0},
        {"title": "Sample modelling study: economic burden of non-communicable diseases keeps rising", "domain": "Non-Communicable Diseases", "signal_strength": "high", "summary": "(Sample item.) A modelling study projects a large and growing macroeconomic loss from non-communicable diseases, steepest in low-income settings. Strengthens the case for early prevention in the NCD paper.", "source_url": "https://example.org/metis-demo/news-4", "source_type": "news", "surprise_flag": 0},
        {"title": "Sample guidance: cost-effectiveness thresholds based on opportunity cost", "domain": "Health Economics", "signal_strength": "medium", "summary": "(Sample item.) New guidance moves away from GDP-multiple thresholds toward opportunity-cost-based thresholds for country priority-setting. Relevant to the threshold paragraph in the MDA paper.", "source_url": "https://example.org/metis-demo/news-5", "source_type": "news", "surprise_flag": 0},
        {"title": "Sample: preparedness fund opens a new call for proposals", "domain": "Health Policy", "signal_strength": "medium", "summary": "(Sample item.) A pandemic-preparedness fund opens a funding round prioritising surveillance, laboratory systems and workforce, with value-for-money criteria — useful framing for the grant proposal.", "source_url": "https://example.org/metis-demo/news-6", "source_type": "news", "surprise_flag": 0},
        {"title": "Sample: health-expenditure database adds new country data", "domain": "Health Financing", "signal_strength": "medium", "summary": "(Sample item.) The latest release adds country health-expenditure data, including domestic versus external financing. Plugs straight into the financing dashboard and the brief's comparator figure.", "source_url": "https://example.org/metis-demo/news-7", "source_type": "news", "surprise_flag": 0},
    ]

    for i, n in enumerate(news, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO news_briefs
            (brief_id, brief_date, title, domain, signal_strength, summary,
             source_url, source_type, surprise_flag, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f"demo-news-{200+i}", D(i//3), n["title"], n["domain"], n["signal_strength"],
              n["summary"], n["source_url"], n["source_type"], n["surprise_flag"], DT(i//3)))

    # ── Personal Notes ──────────────────────────────────────────────────────────
    # note-001 is referenced by the morning brief (cross-pollination demo).
    personal_notes = [
        {"note_id": "note-001", "title": "Framing the UHC brief — gap + efficiency, not 'spend more'",
         "content": "The new global monitoring report (a sample news item) puts the LMIC UHC financing gap at ~US$370bn/year. The brief's strongest move is to pair that number with the efficiency-gains evidence — a commonly cited estimate puts 20–40% of health spending lost to waste. Don't just say 'spend more'; say 'mobilise domestic revenue AND capture efficiency gains AND manage donor transition.' The financing working group agreed this framing two days ago. This is also a clean teaching case for Module 5 — see idea-103.",
         "tags": "UHC,financing-gap,efficiency,policy-brief", "project_id": "proj-POL-003"},
        {"note_id": "note-002", "title": "Discount rate + productivity-loss method (NCD burden)",
         "content": "Decision for the NCD paper: report a 3% discount-rate base case with 0% and 5% sensitivity. Productivity loss — human-capital approach as base case, friction-cost as sensitivity (Ross wants this). Be explicit that the human-capital method gives the larger, more headline-friendly number; the friction-cost method is the conservative one funders will trust. Ties to idea-104.",
         "tags": "discount-rate,cost-of-illness,productivity,methods", "project_id": "proj-NCD-005"},
        {"note_id": "note-003", "title": "Reusing the financing dashboard for other indicators",
         "content": "The Shiny financing dashboard's data-feed + map module is basically indicator-agnostic — reactive data contract, leaflet layer, bslib theme, modular golem. If anyone asks for an immunization-coverage or NCD-burden dashboard, do NOT rebuild from scratch: fork the golem skeleton and swap the data contract. Worth 30 minutes documenting the data-contract assumptions first.",
         "tags": "dashboard,Shiny,reuse,golem", "project_id": "proj-DASH-002"},
        {"note_id": "note-004", "title": "Reference case / ICER threshold reading",
         "content": "For the MDA paper revision: lead the threshold discussion with the iDSI reference case rather than a single WHO-CHOICE GDP multiple. Reviewers expect it now. The opportunity-cost threshold literature (Woods et al.) gives defensible country-specific values. This is idea-101's companion point.",
         "tags": "reference-case,ICER,thresholds,CEA", "project_id": "proj-CEA-001"},
    ]
    for n in personal_notes:
        conn.execute("""
            INSERT OR REPLACE INTO personal_notes
            (note_id, content, title, tags, created_at, updated_at, project_id)
            VALUES (:note_id, :content, :title, :tags, :created_at, :updated_at, :project_id)
        """, {**n, "created_at": DT(3), "updated_at": DT(1)})

    # ── Journal Entries ───────────────────────────────────────────────────────────
    journal = [
        {"entry_id": "jrnl-001", "mood": "focused", "energy_score": 4,
         "summary": "CEA revision momentum",
         "content": "Good day. Re-ran the probabilistic sensitivity analysis for the MDA paper and the conclusions held — seasonal MDA stays cost-effective across the threshold range. Reviewer 2 will push on the discount rate but the new scenarios cover it. The ECEA appendix is going to make the equity story much stronger.",
         "tags": "CEA,MDA,progress"},
        {"entry_id": "jrnl-002", "mood": "scattered", "energy_score": 2,
         "summary": "Too many threads — brief + grant + teaching",
         "content": "Three things pulling at once: the UHC brief's financing-gap figure is due, the Wellcome value-for-money framework is half-drafted, and Module 5 is overdue. Need Metis to help me sequence this — the financing-gap figure is the unblocker (the whole brief hangs off it and the working group is waiting), so it should go first even though the grant feels more strategic.",
         "tags": "overwhelm,prioritisation,UHC"},
    ]
    for j in journal:
        conn.execute("""
            INSERT OR REPLACE INTO journal_entries
            (entry_id, content, mood, energy_score, summary, image_path, tags, created_at)
            VALUES (:entry_id, :content, :mood, :energy_score, :summary, '', :tags, :created_at)
        """, {**j, "created_at": DT(2, 21)})

    # ── Idea Links (cross-pollination graph) ──────────────────────────────────────
    idea_links = [
        ("idea-101", "idea-106", "ECEA framing answers the iDSI reference-case reviewer point"),
        ("idea-103", "idea-102", "the UHC teaching case study could be built on the financing dashboard"),
        ("idea-104", "idea-108", "discount-rate / method choices shape how the NCD burden is framed"),
        ("idea-105", "idea-101", "the pandemic value-for-money framework reuses the CEA model logic"),
    ]
    for a, b, label in idea_links:
        conn.execute("""
            INSERT INTO idea_links (idea_id_a, idea_id_b, link_label, created_at)
            VALUES (?, ?, ?, ?)
        """, (a, b, label, DT(2)))

    # ── Contacts (collaborators who appear in the meetings) ───────────────────────
    contacts = [
        {"contact_id": "c-001", "name": "Dr. Naledi Okonkwo", "role": "Health Financing Lead", "affiliation": "WHO AFRO", "notes": "Commissioned the UHC financing brief; co-chairs the financing working group.", "last_seen": D(2)},
        {"contact_id": "c-002", "name": "Prof. Helena Ross", "role": "Professor of Health Economics", "affiliation": "LSHTM", "notes": "Senior author on the malaria MDA paper; advises on ICER thresholds and the ECEA appendix.", "last_seen": D(5)},
        {"contact_id": "c-003", "name": "Mr. David Mensah", "role": "Senior Health Economist", "affiliation": "World Bank", "notes": "Shares GHED / health-expenditure data for the dashboard and the brief.", "last_seen": D(2)},
        {"contact_id": "c-004", "name": "Dr. Priya Nair", "role": "Immunization Financing Specialist", "affiliation": "Gavi", "notes": "Gavi transition investment-case contact; co-financing scenarios.", "last_seen": D(1)},
        {"contact_id": "c-005", "name": "Dr. Tomás Herrera", "role": "Modelling co-author", "affiliation": "Institute of Global Health", "notes": "NCD burden + decision modelling; suggested the friction-cost sensitivity analysis.", "last_seen": D(1)},
    ]
    for c in contacts:
        conn.execute("""
            INSERT OR REPLACE INTO contacts
            (contact_id, name, role, affiliation, notes, last_seen, updated_at)
            VALUES (:contact_id, :name, :role, :affiliation, :notes, :last_seen, :updated_at)
        """, {**c, "updated_at": DT(1)})

    # ── Literature Metadata (the indexed library — coherent with her field) ───────
    # Seeded explicitly because demo mode disables the live literature scan.
    lit = [
        ("Global health 2035: a world converging within a generation", "Jamison DT, Summers LH, Alleyne G, et al.", "2013", "The Lancet", "global-health,investing,Lancet-Commission", "10.1016/S0140-6736(13)62105-4"),
        ("Disease Control Priorities, third edition: improving health and reducing poverty", "Jamison DT, Gelband H, Horton S, et al.", "2018", "The Lancet", "DCP3,cost-effectiveness,priority-setting", "10.1016/S0140-6736(17)32906-9"),
        ("Methods for the Economic Evaluation of Health Care Programmes", "Drummond MF, Sculpher MJ, Claxton K, et al.", "2015", "Oxford University Press", "economic-evaluation,methods,textbook", ""),
        ("Country-level cost-effectiveness thresholds: initial estimates", "Woods B, Revill P, Sculpher M, Claxton K", "2016", "Value in Health", "threshold,ICER,opportunity-cost,methods", "10.1016/j.jval.2016.02.017"),
        ("Extended cost-effectiveness analysis for health policy assessment", "Verguet S, Kim JJ, Jamison DT", "2016", "PharmacoEconomics", "ECEA,equity,financial-risk-protection", "10.1007/s40273-016-0414-z"),
        ("Financing transformative health systems towards achievement of the SDGs", "Stenberg K, Hanssen O, Edejer TT, et al.", "2017", "The Lancet Global Health", "UHC,financing,SDG", "10.1016/S2214-109X(17)30263-2"),
        ("Return on investment from childhood immunization in low- and middle-income countries", "Ozawa S, Clark S, Portnoy A, et al.", "2016", "Health Affairs", "immunization,ROI,investment-case", "10.1377/hlthaff.2015.1086"),
        ("The global economic burden of non-communicable diseases", "Bloom DE, Cafiero ET, Jané-Llopis E, et al.", "2011", "World Economic Forum", "NCD,economic-burden,macroeconomic", ""),
        ("Consolidated Health Economic Evaluation Reporting Standards 2022 (CHEERS 2022) statement", "Husereau D, Drummond M, Augustovski F, et al.", "2022", "BMJ", "CHEERS,reporting,cost-effectiveness", "10.1136/bmj-2021-067975"),
        ("Decision Modelling for Health Economic Evaluation", "Briggs A, Claxton K, Sculpher M", "2006", "Oxford University Press", "decision-modelling,Markov,methods", ""),
        ("Progress on catastrophic health spending in 133 countries", "Wagstaff A, Flores G, Hsu J, et al.", "2018", "The Lancet Global Health", "catastrophic-expenditure,UHC,equity", "10.1016/S2214-109X(17)30429-1"),
        ("Financing Global Health: development assistance and the pandemic", "Institute for Health Metrics and Evaluation", "2023", "IHME", "health-financing,DAH,global", ""),
        ("Cost-Effectiveness in Health and Medicine (Second Panel)", "Neumann PJ, Sanders GD, Russell LB, et al.", "2016", "Oxford University Press", "cost-effectiveness,reference-case,methods", ""),
        ("Reference case for global health cost-effectiveness analysis", "Wilkinson T, Sculpher MJ, Claxton K, et al.", "2016", "Value in Health", "reference-case,iDSI,methods", "10.1016/j.jval.2016.04.015"),
        ("Measuring universal health coverage based on an index of effective coverage", "Lozano R, Fullman N, Mumford JE, et al.", "2020", "The Lancet", "UHC,effective-coverage,GBD", "10.1016/S0140-6736(20)30750-9"),
        ("Financing pandemic preparedness and response", "Yamey G, Jamison D, Hanssen O, Soucat A", "2017", "The Lancet", "pandemic,financing,preparedness", "10.1016/S0140-6736(17)32132-3"),
    ]
    for i, (title, authors, year, journal, tags, doi) in enumerate(lit, start=1):
        conn.execute("""
            INSERT OR REPLACE INTO literature_metadata
            (id, title, authors, year, source, tags, doi, journal, item_type, created_at)
            VALUES (?, ?, ?, ?, 'library', ?, ?, ?, 'journalArticle', ?)
        """, (500+i, title.strip(), authors, year, tags, doi, journal, DT(40 + i)))

    # ── Daily Insight (Morning Brief) ──────────────────────────────────────────
    brief_text = """**Today's standout — the pieces just connected.** The new global monitoring report (a sample news item) puts the LMIC universal-health-coverage financing gap at about **US$370 billion a year** — wider than before the pandemic. That single figure lands on top of three things already in your workspace:

• **The UHC financing brief** (WHO AFRO) — this number *is* the brief's headline. Drop it into the financing-gap figure that's due today.
• **The idea you captured** about turning the brief into a Module 5 teaching case study: the same financing-gap calculation works for students.
• **Your note + the working-group decision** — you wrote that the brief should pair the gap with efficiency-gains evidence ("mobilise revenue AND capture efficiency, not just spend more"), and the financing working group agreed exactly that framing two days ago. Your note, that meeting, and this report are one coherent argument now.

**This week's signals:** The Global Fund's US$18bn 8th-Replenishment target tightens co-financing for transitioning countries — relevant to the Gavi investment case. WHO's updated cost-effectiveness-threshold guidance (opportunity-cost, not GDP multiples) is directly useful for the malaria MDA paper's threshold paragraph. The 2024 GHED data is out — it plugs straight into the financing dashboard.

**Where to start this morning:** Two items are due today — the financing-gap figure (brief) and the reviewer response on the MDA paper. The figure unblocks the whole brief and the working group is waiting on it, so do it first. Your highest-leverage 20 minutes: build the figure around the US$370bn number while it's fresh — it anchors the brief *and* you can lift it straight into the Module 5 case study."""

    # daily_insights schema uses insight_date + content + generated_at + model.
    # model MUST be 'claude-haiku-brief' or the dashboard treats the row as stale
    # and tries to regenerate via the API (which the demo has no key for).
    conn.execute("""
        INSERT OR REPLACE INTO daily_insights (id, insight_date, content, generated_at, model)
        VALUES (1, ?, ?, ?, 'claude-haiku-brief')
    """, (D(0), brief_text, DT(0, 7)))

    # Weekly brief (week-in-review) — served when the Today brief is toggled to
    # "Weekly". Stored under a distinct insight_date so it coexists with the daily.
    weekly_text = """**This week in review — the throughline was financing.** The new global monitoring report (a sample news item) putting the LMIC universal-health-coverage gap at ~US$370bn/year set the agenda, and it converged with three of your own threads: the UHC policy brief (where it's now the headline figure), the Global Fund's US$18bn replenishment target, and the Gavi co-financing work — all circling the same uncomfortable question of how countries sustain coverage as donor money tightens.

**Your work moved.** The malaria MDA cost-effectiveness paper took shape: the discount-rate sensitivity and the iDSI reference-case framing for the threshold debate are now the plan, and the consortium agreed an ECEA appendix on financial-risk protection. On the NCD burden study, the consortium settled the catastrophic-expenditure thresholds (10% and 25%, WHO primary) and the productivity-loss methods (human-capital base case, friction-cost sensitivity). The financing working group asked you to lead the financing-gap figure for the brief.

**The thread for next week.** The strongest cross-cutting move is the one your own note already flagged: pair the US$370bn gap with the efficiency-gains evidence in the brief, then reuse that exact calculation as the Module 5 teaching case. Three of your projects — the brief, the course, and the dashboard — are converging on the same financing story. Worth consolidating before it scatters."""
    conn.execute("""
        INSERT OR REPLACE INTO daily_insights (id, insight_date, content, generated_at, model)
        VALUES (2, ?, ?, ?, 'claude-haiku-weekly')
    """, (f"{D(0)}-weekly", weekly_text, DT(0, 7)))

    # ── Agent Runs ─────────────────────────────────────────────────────────────
    agent_runs = [
        {"agent_slug": "librarian", "task_summary": "Literature search: cost-effectiveness thresholds in global health 2016–2025", "input_path": "inputs/searches/ce-thresholds-2025.md", "output_path": "outputs/reviews/librarian/2026-05-13_ce-thresholds.md", "status": "completed", "input_tokens": 1240, "output_tokens": 3890, "model": "claude-sonnet-4-6", "created_at": DT(2)},
        {"agent_slug": "methods-coach", "task_summary": "Methods review: Markov model structure for the malaria MDA cost-effectiveness paper", "input_path": "inputs/code/mda-markov-model.R", "output_path": "outputs/reviews/methods-coach/2026-05-11_mda-markov-review.md", "status": "completed", "input_tokens": 2100, "output_tokens": 4200, "model": "claude-opus-4-7", "created_at": DT(4)},
        {"agent_slug": "writing-partner", "task_summary": "Policy-brief revision: UHC financing options section", "input_path": "inputs/drafts/uhc-brief-v2.md", "output_path": "outputs/reviews/writing-partner/2026-05-10_uhc-brief-revision.md", "status": "completed", "input_tokens": 3400, "output_tokens": 5600, "model": "claude-sonnet-4-6", "created_at": DT(5)},
        {"agent_slug": "data-analyst", "task_summary": "Profile and harmonise catastrophic-expenditure across six household surveys", "input_path": "inputs/code/ncd-surveys-merge.csv", "output_path": "outputs/reviews/data-analyst/2026-05-12_ncd-survey-profile.md", "status": "completed", "input_tokens": 1800, "output_tokens": 2900, "model": "claude-sonnet-4-6", "created_at": DT(3)},
        {"agent_slug": "meeting-memory", "task_summary": "Global Health Financing Working Group — structured brief + action items", "input_path": "inputs/meetings/financing-wg-2026.txt", "output_path": "outputs/reviews/meeting-memory/2026-05-13_financing-wg.md", "status": "completed", "input_tokens": 2800, "output_tokens": 3400, "model": "claude-haiku-4-5", "created_at": DT(2)},
        {"agent_slug": "presentation-maker", "task_summary": "Financing-gap figure + executive-summary slide for the UHC brief", "input_path": "inputs/data/ghed-2024-extract.csv", "output_path": "outputs/reviews/presentation-maker/2026-05-12_financing-gap-figure.md", "status": "completed", "input_tokens": 1500, "output_tokens": 2400, "model": "claude-sonnet-4-6", "created_at": DT(3)},
        {"agent_slug": "news-radar", "task_summary": "Morning brief: UHC financing + NCD + immunization signals", "input_path": "", "output_path": "outputs/reviews/news-radar/2026-05-15_morning-brief.md", "status": "completed", "input_tokens": 890, "output_tokens": 1200, "model": "claude-haiku-4-5", "created_at": DT(0, 7)},
        {"agent_slug": "course-builder", "task_summary": "Course outline: Health Economics for Global Health — Modules 1–5 draft", "input_path": "", "output_path": "outputs/reviews/course-builder/2026-05-08_health-econ-outline.md", "status": "completed", "input_tokens": 2200, "output_tokens": 4800, "model": "claude-sonnet-4-6", "created_at": DT(7)},
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

    # ── Reflexions (self-improvement signal for the Metis tab) ────────────────────
    reflexions = [
        ("demo-sess-001", "methods-coach", "Clear walkthrough of the discount-rate sensitivity setup for the MDA paper.", "Could have flagged the human-capital vs friction-cost choice earlier.", "", "A built-in ICER / cost-effectiveness-threshold table generator."),
        ("demo-sess-002", "writing-partner", "Tightened the UHC brief's three-policy-options box.", "Drifted long — the brief has to stay under eight pages.", "Didn't have WHO AFRO's house style guide.", ""),
        ("demo-sess-003", "librarian", "Found the iDSI reference-case paper and the threshold literature fast.", "Returned a few off-scope health-tech papers.", "", "Filter library search by study type (economic evaluation)."),
        ("demo-sess-004", "data-analyst", "Harmonised catastrophic-expenditure definitions across the six surveys.", "Slow on the large Stata files.", "", "Native .dta streaming for big survey datasets."),
        ("demo-sess-005", "meeting-memory", "Action items from the financing working group were spot on.", "Missed one decision about the GHED comparator.", "", ""),
    ]
    for i, (sid, slug, ww, ci, mc, tw) in enumerate(reflexions):
        conn.execute(
            "INSERT INTO reflexion_log (session_id, agent_slug, went_well, could_improve, missing_context, tool_wishes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, slug, ww, ci, mc, tw, DT(i + 1)),
        )

    # ── Learning Courses ────────────────────────────────────────────────────────
    courses = [
        {"title": "Economic Evaluation in Global Health (iDSI reference case)", "category": "health-economics", "slug": "econ-eval-global-health", "progress_pct": 67, "total_modules": 9, "completed_modules": 6, "status": "active", "project_id": "proj-CEA-001"},
        {"title": "Decision Modelling with R for Health Economics", "category": "health-economics", "slug": "decision-modelling-r", "progress_pct": 33, "total_modules": 6, "completed_modules": 2, "status": "active", "project_id": "proj-NCD-005"},
        {"title": "Health Financing Policy for Universal Health Coverage", "category": "health-policy", "slug": "health-financing-uhc", "progress_pct": 100, "total_modules": 8, "completed_modules": 8, "status": "completed"},
        {"title": "Data Visualization & Shiny Dashboards", "category": "data-science", "slug": "shiny-dashboards", "progress_pct": 0, "total_modules": 5, "completed_modules": 0, "status": "active", "project_id": "proj-DASH-002"},
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



def _existing(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                        (table,)).fetchone() is not None


def load(db_path: Path, manifest: Path = MANIFEST) -> dict:
    """Add the demo, recording every row added. Refuses a workspace in use."""
    if manifest.exists():
        return {"ok": True, "already": True}
    conn = sqlite3.connect(str(db_path))
    try:
        in_use = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in OWN_CONTENT if _existing(conn, t)}
        if any(in_use.values()):
            return {"ok": False, "error": (
                "This workspace already has your own content ("
                + ", ".join(f"{t.replace('_', ' ')}: {n}" for t, n in in_use.items() if n)
                + "). The demo is for an empty workspace, so nothing was added.")}
        tables = [t for t in DEMO_TABLES if _existing(conn, t)]
        before = {t: conn.execute(f"SELECT COALESCE(MAX(rowid), 0) FROM {t}").fetchone()[0]
                  for t in tables}
        saved_config = []
        if "user_config" in tables:
            saved_config = [list(r) for r in conn.execute("SELECT * FROM user_config")]
        seed(conn)
        added = {t: [r[0] for r in conn.execute(
                     f"SELECT rowid FROM {t} WHERE rowid > ?", (before[t],))]
                 for t in tables if t != "user_config"}
    finally:
        conn.close()
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"db": str(db_path), "added": added,
                                    "user_config": saved_config}), encoding="utf-8")
    return {"ok": True, "rows": sum(len(v) for v in added.values())}


def unload(manifest: Path = MANIFEST) -> dict:
    """Remove exactly the rows load() added, and put user_config back."""
    if not manifest.exists():
        return {"ok": True, "removed": 0}
    rec = json.loads(manifest.read_text(encoding="utf-8"))
    conn = sqlite3.connect(rec["db"])
    removed = 0
    try:
        for table, rowids in rec.get("added", {}).items():
            for i in range(0, len(rowids), 500):
                chunk = rowids[i:i + 500]
                cur = conn.execute(f"DELETE FROM {table} WHERE rowid IN "
                                   f"({','.join('?' * len(chunk))})", chunk)
                removed += cur.rowcount
        if _existing(conn, "user_config"):
            conn.execute("DELETE FROM user_config")
            for row in rec.get("user_config", []):
                conn.execute(f"INSERT INTO user_config VALUES ({','.join('?' * len(row))})", row)
        conn.commit()
    finally:
        conn.close()
    manifest.unlink()
    return {"ok": True, "removed": removed}

def main():
    parser = argparse.ArgumentParser(description="The Metis sample workspace.")
    parser.add_argument("--load", action="store_true", help="add the demo to this computer's Metis")
    parser.add_argument("--unload", action="store_true", help="remove what --load added")
    parser.add_argument("--db", type=str, default="", help="seed this database instead (no tracking)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.unload:
        res = unload()
        print(f"Demo removed ({res.get('removed', 0)} rows).")
        return
    if args.db:
        conn = sqlite3.connect(args.db)
        seed(conn)
        conn.close()
        return
    db_path = live_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path} — install Metis first.")
        sys.exit(1)
    res = load(db_path)
    if not res["ok"]:
        print(res["error"])
        sys.exit(1)
    if not args.quiet:
        print("Demo loaded." if not res.get("already") else "Demo already loaded.")
    if res.get("ok") and not res.get("already"):
        (CONFIG_DIR / ".demo-mode").touch()


if __name__ == "__main__":
    main()
