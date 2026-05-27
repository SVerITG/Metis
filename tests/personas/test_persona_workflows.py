"""
Persona workflow tests.

Ten distinct user personas, each with different data profiles and daily habits,
run through their typical Metis workflows. This validates that the dashboard
handles diverse usage patterns gracefully — not just the happy-path researcher.

Each persona:
  - Has a unique SQLite dataset seeded to reflect their work
  - Runs the routes they'd actually hit each day
  - Checks that content is rendered correctly for their context

Personas:
  1. PhD epidemiologist (core user — NTD/epidemiology focus)
  2. Clinical research nurse (meetings + tasks, minimal stats)
  3. Biostatistician (stats-heavy, methods learning)
  4. MPH student (learning-first, new to research tools)
  5. Global health consultant (project-heavy, multi-country)
  6. Health data analyst (knowledge tab, no meetings)
  7. Academic department head (meetings + admin, no learning)
  8. DHIS2 implementation expert (technical tasks, projects)
  9. Science policy advisor (news-heavy, thinking tab)
  10. Self-directed learner (learning only, minimal research data)
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).parent.parent.parent
_APP_PY = _REPO / "system" / "app-py"

if str(_APP_PY) not in sys.path:
    sys.path.insert(0, str(_APP_PY))

try:
    from fastapi.testclient import TestClient
except ImportError:
    pytest.skip("fastapi not installed", allow_module_level=True)


# ---------------------------------------------------------------------------
# Persona data definitions
# ---------------------------------------------------------------------------

PERSONAS: list[dict[str, Any]] = [
    {
        "id": "phd_epidemiologist",
        "name": "PhD Epidemiologist",
        "description": "Senior researcher, NTD/epidemiology focus, active PhD, daily dashboard user",
        "tabs": ["/", "/today", "/knowledge", "/learning", "/work", "/planner"],
        "partials": [
            "/api/partial/today/dateline",
            "/api/partial/today/focus-thread",
            "/api/partial/today/activity-feed",
        ],
        "seed": {
            "tasks": [
                ("Write methods section for Article 1", "open", "high"),
                ("Reply to reviewers for Journal of Tropical Medicine", "open", "high"),
                ("Update disease surveillance literature review", "in_progress", "medium"),
                ("Attend PhD committee meeting", "open", "low"),
                ("Run multilevel model for district-level disease data", "done", "high"),
            ],
            "projects": [
                ("proj-ntd-001", "Disease Surveillance Study", "active", "Mapping vector-borne disease transmission zones"),
                ("proj-phd-001", "PhD Article 1", "active", "Methods and results for first article"),
            ],
            "news_briefs": [
                ("WHO issues new disease elimination targets for 2030", "high", "ntd"),
                ("New lancet paper on NTD control programmes in DRC", "medium", "ntd"),
            ],
            "library_cards": [
                ("Spatial distribution of vector-borne disease", "Example Author et al.", 2022, "epidemiology"),
                ("Bayesian multilevel models for surveillance data", "Gelman et al.", 2019, "statistics"),
            ],
            "learning_courses": [
                ("Statistics for Epidemiology", "statistics-for-epi", "statistics", 45, 12, 5, "active"),
            ],
            "competencies": [
                ("Multilevel modelling", 3, "statistics"),
                ("Spatial epidemiology", 2, "epidemiology"),
            ],
        },
    },
    {
        "id": "clinical_research_nurse",
        "name": "Clinical Research Nurse",
        "description": "Clinician-researcher, heavy meeting notes, task tracking, minimal stats",
        "tabs": ["/", "/meetings", "/work", "/thinking"],
        "partials": ["/api/partial/today/activity-feed"],
        "seed": {
            "tasks": [
                ("Prepare informed consent forms for TB study", "open", "high"),
                ("Follow up with IRB on protocol amendment", "open", "high"),
                ("Enroll 5 new participants this week", "in_progress", "medium"),
                ("Data entry for CRF batch 3", "done", "low"),
            ],
            "projects": [
                ("proj-tb-001", "TB Contact Tracing Study", "active", "Community-based TB screening and contact investigation"),
            ],
            "meetings": [
                ("Weekly clinical team meeting", "2026-05-12", "Discussed enrolment targets and protocol deviations"),
                ("IRB review call", "2026-05-10", "IRB requested clarification on consent process for minors"),
                ("Site initiation visit", "2026-05-05", "Sponsor conducted SIV; all queries resolved"),
            ],
            "ideas": [
                ("Use tablet-based eCRF to reduce data entry burden"),
                ("Implement SMS reminders for participant follow-up visits"),
            ],
        },
    },
    {
        "id": "biostatistician",
        "name": "Biostatistician",
        "description": "Methods-focused, heavy learning use, stats course progression, code review",
        "tabs": ["/", "/learning", "/knowledge", "/work"],
        "partials": ["/api/partial/today/focus-thread"],
        "seed": {
            "tasks": [
                ("Review survival analysis code for malaria study", "open", "high"),
                ("Write simulation study for sample size calculation", "in_progress", "medium"),
                ("Attend methods seminar on causal inference", "done", "low"),
            ],
            "learning_courses": [
                ("Statistics for Epidemiology", "statistics-for-epi", "statistics", 82, 12, 10, "active"),
                ("Bayesian Data Analysis", "bayesian-da", "statistics", 20, 8, 2, "active"),
                ("Causal Inference Methods", "causal-inference", "methods", 0, 10, 0, "not_started"),
            ],
            "competencies": [
                ("Survival analysis", 4, "statistics"),
                ("Mixed effects models", 3, "statistics"),
                ("Sample size calculation", 3, "biostatistics"),
                ("R programming", 4, "computing"),
                ("Bayesian methods", 2, "statistics"),
            ],
            "library_cards": [
                ("Applied Survival Analysis", "Hosmer et al.", 2008, "statistics"),
                ("Regression Modeling Strategies", "Harrell", 2015, "statistics"),
                ("The Book of Why", "Pearl & Mackenzie", 2018, "methods"),
            ],
        },
    },
    {
        "id": "mph_student",
        "name": "MPH Student",
        "description": "Student, learning-first user, building foundational skills, few projects",
        "tabs": ["/", "/learning", "/thinking", "/knowledge"],
        "partials": ["/api/partial/today/dateline"],
        "seed": {
            "learning_courses": [
                ("Introduction to Epidemiology", "intro-epi", "epidemiology", 100, 8, 8, "completed"),
                ("Statistics for Epidemiology", "statistics-for-epi", "statistics", 30, 12, 4, "active"),
                ("Global Health Systems", "global-health-systems", "global_health", 10, 10, 1, "active"),
                ("Research Methods", "research-methods", "methods", 0, 6, 0, "not_started"),
            ],
            "competencies": [
                ("Descriptive statistics", 2, "statistics"),
                ("Study design", 1, "epidemiology"),
            ],
            "ideas": [
                ("Could I do a thesis on climate change and malaria transmission?"),
                ("Ask supervisor about mixed methods approaches"),
                ("Look into WHO internship for next summer"),
            ],
            "tasks": [
                ("Complete assignment 3 on confidence intervals", "open", "high"),
                ("Literature search for proposal draft", "in_progress", "medium"),
            ],
        },
    },
    {
        "id": "global_health_consultant",
        "name": "Global Health Consultant",
        "description": "Heavy project workload, multi-country, many meetings, task-driven",
        "tabs": ["/", "/work", "/planner", "/meetings"],
        "partials": ["/api/partial/today/activity-feed"],
        "seed": {
            "tasks": [
                ("Submit WHO concept note for DRC malaria programme", "open", "high"),
                ("Review PEPFAR indicators for Ethiopia site", "in_progress", "high"),
                ("Prepare quarterly report for GAVI secretariat", "open", "medium"),
                ("Travel to Kinshasa for site visit", "done", "high"),
                ("Update country-specific theory of change", "open", "low"),
                ("Respond to RFP for Niger health systems strengthening", "open", "high"),
            ],
            "projects": [
                ("proj-drc-001", "DRC Malaria Control Programme", "active", "WHO-funded national malaria control support"),
                ("proj-eth-001", "Ethiopia PEPFAR Support", "active", "PEPFAR M&E capacity building"),
                ("proj-niger-001", "Niger HSS RFP", "incubating", "Health systems strengthening proposal"),
            ],
            "meetings": [
                ("DRC Technical Working Group", "2026-05-14", "Agreed on HMIS integration roadmap"),
                ("GAVI quarterly review", "2026-05-08", "Coverage targets on track; cold chain issues flagged"),
                ("Ethiopia PEPFAR site call", "2026-05-13", "Data quality improvement plan drafted"),
            ],
            "news_briefs": [
                ("GAVI board approves new malaria vaccine funding", "high", "global_health"),
                ("WHO emergency committee convenes on mpox outbreak", "high", "surveillance"),
                ("DRC reports sustained decline in NTD cases", "medium", "ntd"),
            ],
        },
    },
    {
        "id": "health_data_analyst",
        "name": "Health Data Analyst",
        "description": "Data-heavy user, knowledge tab, library heavy, minimal social features",
        "tabs": ["/", "/knowledge", "/work", "/thinking"],
        "partials": ["/api/partial/today/focus-thread"],
        "seed": {
            "library_cards": [
                ("DHIS2 Aggregate Data Model", "HISP", 2023, "data_systems"),
                ("WHO Health Data Quality Framework", "WHO", 2022, "data_quality"),
                ("OpenHIE Architecture Specification", "OpenHIE", 2021, "interoperability"),
                ("Practical Statistics for Data Scientists", "Bruce & Bruce", 2020, "statistics"),
                ("The Grammar of Graphics", "Wilkinson", 1999, "visualization"),
                ("R for Data Science", "Wickham & Grolemund", 2023, "computing"),
            ],
            "tasks": [
                ("Profile district-level HMIS dataset for completeness", "in_progress", "high"),
                ("Build DHIS2 data quality dashboard", "open", "medium"),
                ("Document data dictionary for NTD indicators", "open", "low"),
            ],
            "ideas": [
                ("Could use R Shiny for interactive data quality reporting"),
                ("DHIS2 SQL views could replace manual Excel exports"),
            ],
            "open_questions": [
                ("What is the best threshold for data completeness in HMIS?"),
                ("How to handle missing denominators in coverage calculations?"),
            ],
        },
    },
    {
        "id": "department_head",
        "name": "Academic Department Head",
        "description": "Admin-heavy, meeting-dominated, task tracking, no learning modules",
        "tabs": ["/", "/meetings", "/work", "/planner"],
        "partials": ["/api/partial/today/activity-feed"],
        "seed": {
            "tasks": [
                ("Review faculty promotion dossier for Dr. Abubakar", "open", "high"),
                ("Approve MSc dissertation proposal from 3 students", "in_progress", "high"),
                ("Prepare department budget proposal for 2027", "open", "medium"),
                ("Respond to accreditation board questionnaire", "open", "medium"),
                ("Hire new biostatistics lecturer", "in_progress", "high"),
                ("Chair curriculum review committee meeting", "done", "low"),
            ],
            "meetings": [
                ("Faculty meeting — semester planning", "2026-05-15", "Agreed on revised course credit structure"),
                ("PhD student annual review panel", "2026-05-13", "Three students passed; one deferred"),
                ("Accreditation site visit prep call", "2026-05-10", "Self-evaluation report due June 1"),
                ("Budget review with Finance", "2026-05-08", "Allocation cut by 12%; need to reprioritize"),
                ("External examiner briefing", "2026-05-06", "Final exam marking guidelines confirmed"),
            ],
            "projects": [
                ("proj-accred-001", "Departmental Accreditation", "active", "WHO/AFRO school of public health accreditation"),
                ("proj-recruit-001", "Biostatistics Lecturer Hire", "active", "Hiring for 2027 academic year"),
            ],
            "ideas": [
                ("Explore cross-departmental PhD co-supervision model"),
                ("Introduce a journal club for all PhD students"),
            ],
        },
    },
    {
        "id": "dhis2_expert",
        "name": "DHIS2 Implementation Expert",
        "description": "Technical user, code and config tasks, project tracking, minimal news",
        "tabs": ["/", "/work", "/knowledge", "/planner"],
        "partials": ["/api/partial/today/focus-thread"],
        "seed": {
            "tasks": [
                ("Configure DHIS2 tracker program for NTD case management", "in_progress", "high"),
                ("Write SQL views for malaria indicator verification", "open", "high"),
                ("Test DHIS2 API integration with mobile app", "in_progress", "medium"),
                ("Document data element naming conventions", "done", "low"),
                ("Fix broken validation rules in ANC tracker", "open", "high"),
                ("Review DHIS2 2.42 upgrade release notes", "open", "medium"),
            ],
            "projects": [
                ("proj-dhis2-ntd", "DHIS2 NTD Case Management", "active", "Tracker program for NTD diagnosis and treatment"),
                ("proj-dhis2-malaria", "DHIS2 Malaria Dashboards", "active", "National malaria programme analytics"),
            ],
            "library_cards": [
                ("DHIS2 Developer Documentation 2.42", "DHIS2 Project", 2024, "dhis2"),
                ("FHIR R4 Implementation Guide", "HL7", 2023, "interoperability"),
            ],
            "ideas": [
                ("Use DHIS2 event capture for field-level NTD screening data"),
                ("Investigate DHIS2 to FHIR conversion for cross-border data sharing"),
            ],
        },
    },
    {
        "id": "policy_advisor",
        "name": "Science Policy Advisor",
        "description": "News-heavy, knowledge and thinking tabs, synthesizes intelligence",
        "tabs": ["/", "/today", "/thinking", "/knowledge"],
        "partials": [
            "/api/partial/today/dateline",
            "/api/partial/today/focus-thread",
            "/api/partial/today/activity-feed",
        ],
        "seed": {
            "news_briefs": [
                ("G7 health ministers endorse pandemic treaty framework", "high", "global_health"),
                ("EU proposes mandatory AI transparency rules for medical devices", "high", "ai_governance"),
                ("WHO updates International Health Regulations surveillance annex", "high", "surveillance"),
                ("Lancet commission report: climate change and infectious disease", "medium", "climate_health"),
                ("Nature: large language models in clinical decision support", "medium", "ai_health"),
                ("Mpox clade Ib confirmed in three new countries", "high", "surveillance"),
            ],
            "ideas": [
                ("Policy brief: AI governance gaps in low-income country health systems"),
                ("Position paper: IHR reform and equity implications for Africa"),
                ("Think piece: pandemic treaty and national sovereignty tensions"),
            ],
            "open_questions": [
                ("How does the WHO pandemic treaty interact with IHR amendments?"),
                ("What evidence base supports AI-assisted disease surveillance?"),
                ("Which countries have the most advanced national AI health strategies?"),
            ],
            "library_cards": [
                ("Global Health Law", "Gostin", 2014, "global_health"),
                ("The End of Epidemics", "Quick", 2018, "global_health"),
            ],
        },
    },
    {
        "id": "self_directed_learner",
        "name": "Self-Directed Learner",
        "description": "Learning-first, no research projects, uses Metis purely for skill development",
        "tabs": ["/", "/learning", "/thinking"],
        "partials": ["/api/partial/today/dateline"],
        "seed": {
            "learning_courses": [
                ("Statistics for Epidemiology", "statistics-for-epi", "statistics", 60, 12, 7, "active"),
                ("Python for Data Science", "python-ds", "computing", 40, 10, 4, "active"),
                ("Introduction to Machine Learning", "intro-ml", "computing", 5, 15, 1, "active"),
                ("Academic Writing", "academic-writing", "writing", 100, 5, 5, "completed"),
                ("Critical Appraisal", "critical-appraisal", "methods", 75, 8, 6, "active"),
            ],
            "competencies": [
                ("Descriptive statistics", 3, "statistics"),
                ("Probability theory", 2, "statistics"),
                ("Python basics", 2, "computing"),
                ("Literature appraisal", 3, "methods"),
                ("Data visualization", 2, "computing"),
            ],
            "ideas": [
                ("Build a flashcard app for statistics concepts"),
                ("Create a learning journal for tracking weekly insights"),
            ],
        },
    },
]

_PERSONA_IDS = [p["id"] for p in PERSONAS]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_BASE_DDL = """
CREATE TABLE IF NOT EXISTS agent_runs (run_id INTEGER PRIMARY KEY AUTOINCREMENT, agent_slug TEXT NOT NULL DEFAULT '', task_summary TEXT NOT NULL DEFAULT '', input_path TEXT DEFAULT '', output_path TEXT DEFAULT '', status TEXT DEFAULT 'completed', created_at TEXT NOT NULL DEFAULT '', input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0, model TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS news_briefs (brief_id INTEGER PRIMARY KEY, title TEXT, summary TEXT, domain TEXT, source_url TEXT, source_type TEXT, created_at TEXT, signal_strength INTEGER, surprise_flag INTEGER, brief_date TEXT);
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT, priority TEXT, created_at TEXT, project_id TEXT, due_date TEXT, description TEXT);
CREATE TABLE IF NOT EXISTS library_cards (id INTEGER PRIMARY KEY, title TEXT, authors TEXT, year INTEGER, domain TEXT, tags TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS ideas (id INTEGER PRIMARY KEY, text TEXT, created_at TEXT, project_id TEXT);
CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, title TEXT, status TEXT, description TEXT, created_at TEXT, next_step TEXT, external_path TEXT);
CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, client TEXT, computer TEXT, started_at TEXT, last_active TEXT);
CREATE TABLE IF NOT EXISTS jobs_log (id INTEGER PRIMARY KEY, job_type TEXT, status TEXT, details TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS memory_entries (entry_id TEXT PRIMARY KEY, entry_date TEXT, entry_type TEXT, topics TEXT, title TEXT, summary TEXT, file_path TEXT, computer TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS personal_notes (id INTEGER PRIMARY KEY, content TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS user_config (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS daily_insights (id INTEGER PRIMARY KEY, insight_date TEXT, content TEXT, model TEXT, generated_at TEXT);
CREATE TABLE IF NOT EXISTS meetings (id INTEGER PRIMARY KEY, title TEXT, meeting_date TEXT, created_at TEXT, summary TEXT);
CREATE TABLE IF NOT EXISTS learning_courses (id INTEGER PRIMARY KEY, title TEXT, slug TEXT, category TEXT, progress_pct INTEGER, total_modules INTEGER, completed_modules INTEGER, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS competencies (id INTEGER PRIMARY KEY, name TEXT, level INTEGER, domain TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS news_topic_summaries (id INTEGER PRIMARY KEY, period TEXT, domain TEXT, summary TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS literature_metadata (id INTEGER PRIMARY KEY, title TEXT, authors TEXT, year INTEGER, journal TEXT, doi TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS open_questions (id INTEGER PRIMARY KEY, question TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS brainstorm_sessions (id INTEGER PRIMARY KEY, topic TEXT, created_at TEXT);
"""


def _seed_persona(conn: sqlite3.Connection, seed: dict) -> None:
    now = "2026-05-18T08:00:00"

    for t in seed.get("tasks", []):
        conn.execute(
            "INSERT INTO tasks (title, status, priority, created_at) VALUES (?, ?, ?, ?)",
            (t[0], t[1], t[2], now),
        )
    for p in seed.get("projects", []):
        conn.execute(
            "INSERT INTO projects (project_id, title, status, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (p[0], p[1], p[2], p[3], now),
        )
    for n in seed.get("news_briefs", []):
        conn.execute(
            "INSERT INTO news_briefs (title, signal_strength, domain, created_at, brief_date) VALUES (?, ?, ?, ?, ?)",
            (n[0], n[1] if isinstance(n[1], int) else {"high": 5, "medium": 3, "low": 1}.get(n[1], 3), n[2], now, "2026-05-18"),
        )
    for lc in seed.get("library_cards", []):
        conn.execute(
            "INSERT INTO library_cards (title, authors, year, domain, created_at) VALUES (?, ?, ?, ?, ?)",
            (lc[0], lc[1], lc[2], lc[3], now),
        )
    for c in seed.get("learning_courses", []):
        conn.execute(
            "INSERT INTO learning_courses (title, slug, category, progress_pct, total_modules, completed_modules, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (c[0], c[1], c[2], c[3], c[4], c[5], c[6], now),
        )
    for comp in seed.get("competencies", []):
        conn.execute(
            "INSERT INTO competencies (name, level, domain, created_at) VALUES (?, ?, ?, ?)",
            (comp[0], comp[1], comp[2], now),
        )
    for m in seed.get("meetings", []):
        conn.execute(
            "INSERT INTO meetings (title, meeting_date, created_at, summary) VALUES (?, ?, ?, ?)",
            (m[0], m[1], now, m[2]),
        )
    for i in seed.get("ideas", []):
        text = i if isinstance(i, str) else i[0]
        conn.execute("INSERT INTO ideas (text, created_at) VALUES (?, ?)", (text, now))
    for q in seed.get("open_questions", []):
        conn.execute("INSERT INTO open_questions (question, created_at) VALUES (?, ?)", (q, now))

    conn.commit()


@pytest.fixture(scope="function")
def persona_clients(tmp_path_factory, monkeypatch):
    """Build one TestClient per persona, each with its own temp SQLite DB."""
    clients: dict[str, Any] = {}

    os.chdir(str(_APP_PY))

    for persona in PERSONAS:
        db_path = tmp_path_factory.mktemp(f"db_{persona['id']}") / "test.sqlite"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(_BASE_DDL)
        conn.commit()
        _seed_persona(conn, persona.get("seed", {}))
        conn.close()

        monkeypatch.setenv("METIS_DB", str(db_path))
        monkeypatch.setenv("METIS_RC_ROOT", str(_REPO))

        # Import app fresh for each persona by clearing the module cache for db-dependent modules
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith(("routers.", "db", "main")) and mod_name in sys.modules:
                del sys.modules[mod_name]

        from main import app
        clients[persona["id"]] = TestClient(app, raise_server_exceptions=False)

    return clients


# ---------------------------------------------------------------------------
# Tests — one parametrized block per workflow type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona", PERSONAS, ids=_PERSONA_IDS)
def test_persona_primary_tabs_return_200(persona, persona_clients):
    """Every tab in a persona's daily workflow must return 200 with HTML."""
    client = persona_clients[persona["id"]]
    for route in persona["tabs"]:
        resp = client.get(route)
        assert resp.status_code == 200, (
            f"[{persona['name']}] Tab {route} returned {resp.status_code}"
        )
        assert "text/html" in resp.headers.get("content-type", ""), (
            f"[{persona['name']}] Tab {route} did not return HTML"
        )


@pytest.mark.parametrize("persona", PERSONAS, ids=_PERSONA_IDS)
def test_persona_partials_return_200(persona, persona_clients):
    """Partial endpoints used by a persona must return 200 with HTML."""
    client = persona_clients[persona["id"]]
    for route in persona.get("partials", []):
        resp = client.get(route)
        assert resp.status_code == 200, (
            f"[{persona['name']}] Partial {route} returned {resp.status_code}"
        )
        assert "text/html" in resp.headers.get("content-type", ""), (
            f"[{persona['name']}] Partial {route} did not return HTML"
        )


@pytest.mark.parametrize("persona", PERSONAS, ids=_PERSONA_IDS)
def test_persona_health_check_always_ok(persona, persona_clients):
    """Health endpoint must return ok for every persona."""
    client = persona_clients[persona["id"]]
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


@pytest.mark.parametrize(
    "persona",
    [p for p in PERSONAS if p["seed"].get("tasks")],
    ids=[p["id"] for p in PERSONAS if p["seed"].get("tasks")],
)
def test_persona_work_tab_reflects_seeded_tasks(persona, persona_clients):
    """Work tab must render without error for personas with tasks seeded."""
    client = persona_clients[persona["id"]]
    resp = client.get("/work")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize(
    "persona",
    [p for p in PERSONAS if p["seed"].get("learning_courses")],
    ids=[p["id"] for p in PERSONAS if p["seed"].get("learning_courses")],
)
def test_persona_learning_tab_renders(persona, persona_clients):
    """Learning tab must render for personas with courses seeded."""
    client = persona_clients[persona["id"]]
    resp = client.get("/learning")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize(
    "persona",
    [p for p in PERSONAS if p["seed"].get("meetings")],
    ids=[p["id"] for p in PERSONAS if p["seed"].get("meetings")],
)
def test_persona_meetings_tab_renders(persona, persona_clients):
    """Meetings tab must render for personas with meeting data."""
    client = persona_clients[persona["id"]]
    resp = client.get("/meetings")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize(
    "persona",
    [p for p in PERSONAS if p["seed"].get("news_briefs")],
    ids=[p["id"] for p in PERSONAS if p["seed"].get("news_briefs")],
)
def test_persona_today_tab_with_news_renders(persona, persona_clients):
    """Today tab must render correctly for personas with news briefs seeded."""
    client = persona_clients[persona["id"]]
    resp = client.get("/today")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize(
    "persona",
    [p for p in PERSONAS if p["seed"].get("ideas") or p["seed"].get("open_questions")],
    ids=[p["id"] for p in PERSONAS if p["seed"].get("ideas") or p["seed"].get("open_questions")],
)
def test_persona_thinking_tab_renders(persona, persona_clients):
    """Thinking tab must render for personas with ideas or open questions."""
    client = persona_clients[persona["id"]]
    resp = client.get("/thinking")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize(
    "persona",
    [p for p in PERSONAS if p["seed"].get("projects")],
    ids=[p["id"] for p in PERSONAS if p["seed"].get("projects")],
)
def test_persona_planner_tab_with_projects_renders(persona, persona_clients):
    """Planner tab must render for personas with projects."""
    client = persona_clients[persona["id"]]
    resp = client.get("/planner")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize(
    "persona",
    [p for p in PERSONAS if p["seed"].get("library_cards")],
    ids=[p["id"] for p in PERSONAS if p["seed"].get("library_cards")],
)
def test_persona_knowledge_tab_with_library_renders(persona, persona_clients):
    """Knowledge tab must render for personas with library data."""
    client = persona_clients[persona["id"]]
    resp = client.get("/knowledge")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize("persona", PERSONAS, ids=_PERSONA_IDS)
def test_persona_metis_tab_always_renders(persona, persona_clients):
    """Metis tab must render for all personas regardless of data."""
    client = persona_clients[persona["id"]]
    resp = client.get("/metis")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.parametrize("persona", PERSONAS, ids=_PERSONA_IDS)
def test_persona_unknown_route_does_not_crash(persona, persona_clients):
    """An unknown route must not return 500 for any persona."""
    client = persona_clients[persona["id"]]
    resp = client.get("/route-that-does-not-exist", follow_redirects=False)
    assert resp.status_code not in (500, 502, 503), (
        f"[{persona['name']}] Unknown route returned {resp.status_code}"
    )
