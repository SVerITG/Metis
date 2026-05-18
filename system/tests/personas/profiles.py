"""
personas/profiles.py — The 10 canonical Metis user profiles.

Each profile is a dataclass used by all persona tests and the audit report.
Profiles are permanent — they represent recurring test identities, not
one-time scenarios. Add new profiles here; never hardcode them in tests.

Run the full persona suite:
    pytest metis/system/tests/personas/ -v

Run a single persona:
    pytest metis/system/tests/personas/test_persona_01_phd_student.py -v
"""

from dataclasses import dataclass, field


@dataclass
class Persona:
    id: int
    slug: str
    name: str
    role: str
    institution: str
    platform: str                   # windows | mac | linux | docker | mobile
    install_method: str             # exe | bash | docker | manual
    experience: str                 # beginner | intermediate | expert
    primary_tabs: list[str]         # which dashboard tabs this user hits daily
    primary_agents: list[str]       # which agents this user invokes most
    morning_workflow: list[str]     # ordered list of morning tasks
    critical_features: list[str]    # features that must work for this user
    known_gaps: list[str]           # known gaps or risks for this profile
    description: str


PERSONAS: list[Persona] = [

    Persona(
        id=1,
        slug="phd-epidemiology",
        name="Fatou Diallo",
        role="PhD student — Epidemiology",
        institution="Institute of Tropical Medicine (external collaborator)",
        platform="windows",
        install_method="exe",
        experience="beginner",
        primary_tabs=["today", "knowledge", "thinking", "learning"],
        primary_agents=["librarian", "epidemiologist", "writing-partner", "methods-coach"],
        morning_workflow=[
            "Open Today tab — check morning brief for HAT surveillance news",
            "Review 2–3 suggested papers in Knowledge tab",
            "Ask Epidemiologist to review study design for Article 1",
            "Use Writing Partner to improve methods section draft",
            "Capture a methodology question in Thinking tab",
            "Check Learning tab for spaced repetition due today",
        ],
        critical_features=[
            "Morning brief includes relevant surveillance news",
            "Literature search returns PubMed results",
            "Epidemiologist agent challenges methodology",
            "Writing Partner preserves STROBE guideline language",
            "Capture modal works with Ctrl+K",
            "Cross-pollination connects new idea to existing papers",
        ],
        known_gaps=[
            "First-time install: Python bootstrap may fail on university-managed machine",
            "Zotero sync requires API key setup (not covered in basic install)",
            "PaperQA2 requires index to be built before semantic search works",
        ],
        description=(
            "Second-year PhD student working on NTD surveillance in West Africa. "
            "Uses Metis primarily for literature management, methodology feedback, "
            "and article writing. Not technical — needs installer to just work. "
            "Key pain point: connecting her reading to her writing."
        ),
    ),

    Persona(
        id=2,
        slug="senior-ntd-researcher",
        name="Dr. Elena Marchetti",
        role="Senior Research Scientist — NTD",
        institution="University research group, multiple projects",
        platform="windows",
        install_method="exe",
        experience="intermediate",
        primary_tabs=["today", "work", "meetings", "knowledge", "planner"],
        primary_agents=["metis", "meeting-memory", "librarian", "writing-partner", "news-radar"],
        morning_workflow=[
            "Check Today tab — overnight brief + action items from yesterday",
            "Review meeting notes from yesterday's consortium call",
            "Scan literature alerts for sleeping sickness + drug trials",
            "Check Work tab — which project needs attention today",
            "Open Planner — review weekly intentions vs actuals",
            "Open active article in Writing Partner for revision",
        ],
        critical_features=[
            "Meeting Memory captures action items accurately",
            "Work tab shows all active projects with status",
            "Morning brief includes NTD-specific literature alerts",
            "Planner shows realistic weekly horizon",
            "Agent runs are logged with token cost visible",
            "Self-improvement loop shows what agents have learned",
        ],
        known_gaps=[
            "Live meeting assistant (browser-based) — backend may be partial",
            "Cross-project task linkage not fully implemented",
            "Token cost visibility requires agent_runs data to be populated",
        ],
        description=(
            "10-year research career, leads a small team, juggles 4–5 projects. "
            "Uses Metis as command-and-control: morning overview, meeting follow-up, "
            "literature monitoring. Needs everything to interconnect. "
            "Pain point: switching between projects without losing context."
        ),
    ),

    Persona(
        id=3,
        slug="biomedical-data-analyst",
        name="Kwame Asante",
        role="Biomedical Data Analyst",
        institution="Research institute, R-heavy workflow",
        platform="linux",
        install_method="bash",
        experience="expert",
        primary_tabs=["work", "knowledge", "thinking"],
        primary_agents=["data-analyst", "software-engineer", "visualization-maker", "methods-coach"],
        morning_workflow=[
            "Pull latest data export to inputs/code/",
            "Ask Data Analyst to profile the CSV: missing values, outliers, duplicates",
            "Run cleaning script via Software Engineer review",
            "Ask Visualization Maker for ggplot2 figure code",
            "Check Methods Coach on appropriate regression model choice",
            "Commit clean dataset + analysis script to project repo",
        ],
        critical_features=[
            "Data Analyst reads CSV/Excel/SPSS/Stata files",
            "Data Guardian does NOT block internal research data",
            "Software Engineer produces working R/Python code",
            "Visualization Maker outputs valid ggplot2/Plotly code",
            "bash install works on Ubuntu 22.04 without sudo for most steps",
            "VS Code integration opens project folder directly",
        ],
        known_gaps=[
            "No Git MCP tool — must use CLI for commits",
            "DHIS2 expert has skill but no dedicated MCP tool module",
            "R/RStudio launcher depends on Windows PATH (not relevant on Linux)",
        ],
        description=(
            "Expert R/Python analyst. Installs via bash script on Ubuntu. "
            "Uses Metis as a thinking partner for analysis decisions and code review. "
            "Pain point: the gap between 'what analysis should I do' and 'how do I code it'."
        ),
    ),

    Persona(
        id=4,
        slug="medical-educator",
        name="Prof. Sarah Okonkwo",
        role="Associate Professor — Public Health Education",
        institution="Medical school, teaches epidemiology + biostatistics",
        platform="windows",
        install_method="exe",
        experience="intermediate",
        primary_tabs=["teach", "knowledge", "learning", "today"],
        primary_agents=["course-builder", "presentation-maker", "learning-architect", "writing-partner"],
        morning_workflow=[
            "Open Teach tab — check course build status",
            "Use Course Builder to generate lecture outline for next week",
            "Ask Presentation Maker to structure 45-min lecture as slides",
            "Pull in library papers as course references",
            "Check Learning Architect for spaced repetition card suggestions",
            "Review student question from last session in Thinking tab",
        ],
        critical_features=[
            "Teach tab loads course builder form without errors",
            "Course Builder integrates library sources into curriculum",
            "Presentation Maker produces PowerPoint-compatible outline",
            "Knowledge sources chip toggles (Library/Literature/Web) work",
            "Output format toggles (PowerPoint/Outline/Markdown) work",
            "Courses appear in Learning tab after publishing",
        ],
        known_gaps=[
            "PowerPoint export requires python-pptx or Quarto — check if installed",
            "Course Builder output is Markdown/outline; actual PPTX generation may be manual step",
            "Teach tab right-side output panel not fully surveyed",
        ],
        description=(
            "Teaches 3 courses, builds one new course per semester. "
            "Uses Metis to turn her literature collection into teaching materials. "
            "Pain point: the gap between knowing the research and making it teachable."
        ),
    ),

    Persona(
        id=5,
        slug="early-career-researcher",
        name="Thomas Weber",
        role="Junior Researcher / Postdoc",
        institution="First job post-MSc, building skills",
        platform="mac",
        install_method="bash",
        experience="beginner",
        primary_tabs=["learning", "today", "thinking", "knowledge"],
        primary_agents=["learning-coach", "methods-coach", "career-coach", "librarian"],
        morning_workflow=[
            "Check spaced repetition due cards in Learning tab",
            "Ask Learning Coach for today's statistics exercise",
            "Search 2 papers in Knowledge tab on multilevel models",
            "Capture a question from reading in Thinking tab",
            "Ask Career Coach for feedback on LinkedIn summary",
            "Review Methods Coach answer to yesterday's regression question",
        ],
        critical_features=[
            "Learning tab shows spaced repetition cards due today",
            "Streak tracker updates after completing cards",
            "Learning Coach provides progressive exercises, not just answers",
            "Career Coach gives EU job-market specific advice",
            "Thinking tab threads persist between sessions",
            "Cross-pollination connects questions to relevant papers",
        ],
        known_gaps=[
            "macOS install: Homebrew Python detection in setup-mcp.sh",
            "Spaced repetition requires seeded learning_items rows to show cards",
            "Career Coach was listed but skill.md content not surveyed",
        ],
        description=(
            "Just started first research position. Overwhelmed by what to learn. "
            "Uses Metis primarily for structured learning and career development. "
            "Pain point: not knowing what he doesn't know."
        ),
    ),

    Persona(
        id=6,
        slug="global-health-consultant",
        name="Dr. Aminata Sow",
        role="Global Health Consultant — WHO / NGO",
        institution="Freelance, works across organizations",
        platform="windows",
        install_method="exe",
        experience="intermediate",
        primary_tabs=["today", "meetings", "work", "thinking"],
        primary_agents=["news-radar", "meeting-memory", "writing-partner", "presentation-maker"],
        morning_workflow=[
            "Read Today tab — overnight news brief (WHO + policy signals)",
            "Review yesterday's meeting transcript for action items",
            "Write policy brief using Writing Partner",
            "Check Work tab — which report is due this week",
            "Use Presentation Maker for WHO meeting deck",
            "Capture 3 news signals worth tracking in Thinking tab",
        ],
        critical_features=[
            "Morning brief covers WHO + global health policy news",
            "Meeting Memory outputs action items as tasks",
            "Writing Partner respects UN/WHO publication style",
            "Work tab projects include external consulting engagements",
            "News Radar distinguishes signal from noise",
            "Today tab ledger shows pending follow-ups",
        ],
        known_gaps=[
            "No Telegram integration — field capture requires PWA",
            "Meeting audio transcription (browser microphone) — requires HTTPS or localhost",
            "WHO website access requires internet permission (allowlist)",
        ],
        description=(
            "Travels frequently, attends 2–3 meetings per day, writes policy briefs. "
            "Needs Metis to be a rapid intelligence-to-output system. "
            "Pain point: staying on top of WHO/policy signals while producing outputs."
        ),
    ),

    Persona(
        id=7,
        slug="clinical-researcher",
        name="Dr. James Obi",
        role="Clinical Researcher — RCT + Systematic Reviews",
        institution="Teaching hospital, strict IT policy",
        platform="windows",
        install_method="exe",
        experience="intermediate",
        primary_tabs=["knowledge", "work", "meetings", "today"],
        primary_agents=["data-guardian", "librarian", "epidemiologist", "writing-partner"],
        morning_workflow=[
            "Check Data Guardian rules apply before opening patient data",
            "Literature search in Knowledge tab — Cochrane + PubMed Clinical Queries",
            "Ask Epidemiologist to review randomisation strategy",
            "Import meeting notes from IRB committee meeting",
            "Writing Partner review of CONSORT checklist compliance",
            "Export anonymised dataset for analysis (Data Guardian approval)",
        ],
        critical_features=[
            "Data Guardian BLOCKS any file containing patient IDs",
            "Red-lines are enforced (no individual case records externally)",
            "Librarian searches Cochrane + systematic review sources",
            "Epidemiologist knows RCT methodology and CONSORT",
            "Meeting Memory handles IRB/ethics committee meeting format",
            "Constitution clinical-citation rule fires on clinical claims",
        ],
        known_gaps=[
            "IT-managed machine: Python install may need admin rights → use bundled embed",
            "Hospital proxy may block outbound HTTPS for API calls",
            "CONSORT/PRISMA compliance is in agent system prompts but not automated",
        ],
        description=(
            "Works in a teaching hospital with strict data governance. "
            "Uses Metis for systematic review methodology and trial design. "
            "Critical requirement: patient data must NEVER leave local machine. "
            "Pain point: confidence that the tool is safe to use with clinical data."
        ),
    ),

    Persona(
        id=8,
        slug="developer-technical",
        name="Marta Gonzalez",
        role="Research Software Engineer",
        institution="Builds tools for research teams",
        platform="linux",
        install_method="docker",
        experience="expert",
        primary_tabs=["work", "metis"],
        primary_agents=["software-engineer", "builder", "rc-builder", "cybersecurity"],
        morning_workflow=[
            "Check Metis tab — agent registry, tool count, recent runs",
            "Review MCP server logs for errors",
            "Use RC Builder to add a new MCP tool module",
            "Test new tool via Software Engineer review",
            "Use Builder to scaffold a new FastAPI microservice",
            "Check Cybersecurity agent for URL/injection threat scan",
        ],
        critical_features=[
            "Docker image starts without errors (`docker compose up -d`)",
            "MCP server exposes all 43 tool modules",
            "RC Builder can modify agent skill.md files",
            "Software Engineer produces idiomatic Python/FastAPI code",
            "Metis tab shows full agent registry",
            "Tool subsets work correctly via METIS_AGENT_SUBSET env var",
        ],
        known_gaps=[
            "No Git MCP tool — must use CLI for version control",
            "Docker image push to GHCR requires workflow trigger (no auto-push on code change)",
            "RC Builder modifies local files; no git commit automation",
        ],
        description=(
            "Builds and extends Metis itself. Runs on Docker, uses Linux. "
            "Needs the system to be inspectable, extensible, and well-documented. "
            "Pain point: understanding what's already built vs what needs to be added."
        ),
    ),

    Persona(
        id=9,
        slug="department-head",
        name="Prof. Robert Kim",
        role="Department Head — 5-person research group",
        institution="University department, research + teaching mix",
        platform="windows",
        install_method="exe",
        experience="beginner",
        primary_tabs=["today", "work", "planner", "meetings"],
        primary_agents=["metis", "news-radar", "meeting-memory"],
        morning_workflow=[
            "30-second Today tab check — what needs attention",
            "Work tab — project health across all 5 active projects",
            "Planner — weekly intentions vs actual progress",
            "Scan meeting follow-ups from this week",
            "Check if any high-priority news needs forwarding to team",
            "No deep agent work — just overview and dispatch",
        ],
        critical_features=[
            "Today tab gives useful overview without requiring any input",
            "Work tab projects are grouped and sortable",
            "Planner shows realistic weekly + quarterly view",
            "Morning brief is short and actionable (< 3 paragraphs)",
            "Meeting follow-ups appear in Today tab automatically",
            "No technical setup required to get value from day one",
        ],
        known_gaps=[
            "First-run wizard must be smooth (this user won't debug)",
            "Today tab value depends on data being populated from other sources",
            "Team collaboration features not present — Metis is single-user",
        ],
        description=(
            "Manages a team, handles grant oversight, attends many meetings. "
            "Wants a 5-minute morning briefing, no configuration, no technical work. "
            "Pain point: spending time on admin instead of research leadership."
        ),
    ),

    Persona(
        id=10,
        slug="mobile-voice-first",
        name="Amara Diarra",
        role="Field Epidemiologist — data collection + surveillance",
        institution="National program, field-based work",
        platform="mobile",
        install_method="manual",
        experience="beginner",
        primary_tabs=["today"],
        primary_agents=["meeting-memory", "metis"],
        morning_workflow=[
            "Open Metis PWA on phone (http://[local-IP]:8080)",
            "Record 2-minute voice note from last night's field visit",
            "Voice auto-transcribed → routed as journal entry",
            "Capture 3 observations as ideas via mobile form",
            "Check Today tab for any overnight literature alerts",
            "When back at desk: review structured notes from field",
        ],
        critical_features=[
            "PWA loads on mobile browser without install",
            "Mobile capture page has large tap targets",
            "Voice capture works offline (faster-whisper local)",
            "Capture modal prefix routing (i:/n:/t:/q:) works on mobile",
            "Dashboard accessible on local network (not just localhost)",
            "Captured items appear in appropriate tab on desktop later",
        ],
        known_gaps=[
            "faster-whisper requires Python environment — not available standalone on phone",
            "PWA offline caching not implemented (service worker deferred)",
            "Dashboard binds to 0.0.0.0 needed for local network access (default is localhost only)",
            "Voice capture likely requires desktop Metis open to process audio",
        ],
        description=(
            "Works in the field, often with poor connectivity. "
            "Needs to capture observations quickly and sync when back at base. "
            "Pain point: friction between field observation and structured research record."
        ),
    ),
]

PERSONA_BY_SLUG: dict[str, Persona] = {p.slug: p for p in PERSONAS}
PERSONA_BY_ID: dict[int, Persona] = {p.id: p for p in PERSONAS}
