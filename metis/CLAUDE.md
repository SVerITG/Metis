# Metis Second Brain — Claude Code Configuration

This is the Metis second-brain system for a Senior Researcher / Epidemiologist / Public Health Methodologist
working on sleeping sickness (HAT), PhD planning, AI development, and personal learning.

**Owner:** sverschaeve
**Root:** This folder
**App:** `system/app/`
**Agents:** `agents/`

---

## Core operating rules

- Work locally first. Do not access the internet unless the task explicitly requires it.
- Ask permission before general internet use. Librarian and News Radar are exempt within their scope.
- Prefer editing existing files over creating new ones.
- Never commit data files (.csv, .rds, .cas, .geo, .pop, shapefiles) to git.
- Never store secrets or API keys in source files.
- When uncertain which agent applies, default to Metis routing.

---

## How to invoke agents

**Default: just call `/metis`** with any request. Metis will analyze it, pick the right agent(s), choose the complexity level, execute the work, and record everything to the RC. You don't need to know which agent to use.

```
/metis Review my Article 1 draft for methodology and grammar
→ Metis routes to: Epidemiologist (methodology) + Writing Partner (grammar)
→ Complexity: chain (opus + subagents)
→ Output: 07_outputs/reviews/epidemiologist/... + 07_outputs/reviews/writing-partner/...
```

**Direct call:** If you already know which agent you want, call them directly:

| Invocation | Agent | When to use |
|---|---|---|
| `/metis` | Metis | **Default entry point.** Any request — she routes, executes, and records |
| `/librarian` | Librarian | Find papers, update literature metadata, search sources |
| `/phd-architect` | PhD Architect | Thesis structure, article alignment, chapter planning |
| `/writing-partner` | Writing Partner | Draft text, improve writing, structure arguments |
| `/methods-coach` | Methods Coach | Epidemiological methods, statistics, sampling, R methodology |
| `/software-engineer` | Software Engineer | Code review, debugging, Python/R scripts, FastAPI |
| `/frontend-designer` | Frontend Designer Builder | UI/UX decisions, design system, visualization design, web interfaces |
| `/meeting-memory` | Meeting Memory | Transcribe, structure, and brief meeting notes |
| `/news-radar` | News Radar | What happened in the world, brief generation |
| `/builder` | Builder | Build new apps, tools, MCP servers |
| `/rc-builder` | RC Builder | Modify/extend Metis itself — new agents, dashboard phases, MCP tools |
| `/presentation-maker` | Presentation Maker | PowerPoint slides, visual summaries |
| `/learning-coach` | Learning Coach | Skill progression, learning paths, statistics competencies |
| `/career-coach` | Career Coach | EU job prep, CV support, career strategy |

| `/news-aggregator` | News Aggregator | Automated RSS collection, feed curation, signal tagging |
| `/design-auditor` | Design Auditor | Audit existing UIs, reverse-engineer design decisions, prioritized improvements |
| `/visualization-maker` | Visualization Maker | Diagrams, charts, system maps, ggplot2 figures, Plotly |
| `/content-harvester` | Content Harvester | Extract and structure content from web, PDFs, DOCX, YouTube, GitHub |
| `/learning-architect` | Learning Architect | Curriculum design, learning paths, spaced repetition, competency maps |
| `/epidemiologist` | Epidemiologist | Study design review, methodology challenge, Socratic questioning |
| `/cybersecurity` | Cybersecurity | URL validation, prompt injection defense, threat intel, agent audit |
| `/data-guardian` | Data Guardian | PII protection, patient data blocking, file transmission approval |
| `/data-analyst` | Data Analyst | Profile, clean, and compare tabular datasets (CSV/Excel/SPSS/Stata) — local only |

**Phase 5 skills (automation & scaffolding):**

| Invocation | Skill | When to use |
|---|---|---|
| `/schedule` | Schedule Morning Agents | Set up 07:00 News Radar + 07:30 Librarian via Task Scheduler or RemoteTrigger |
| `/new-project` | New Project | Scaffold a new Shiny app, R script, report, or tool in Metis |
| `/add-context` | Add Context | Add a specialist context to your profile without re-running /metis_config |
| `/metis_config` | Metis Config Wizard | First-time setup, reconfigure, or add context — 13-section guided wizard |

**RC workflow commands:**

| Invocation | Skill | When to use |
|---|---|---|
| `/metis_brainstorm` | Metis Brainstorm | Activate cross-pollination for an idea; loads RC context and surfaces connections |
| `/metis_handoff` | Metis Handoff | Generate portable context brief for switching AI, hitting token limits, or continuing on another device |
| `/metis_ideas` | Metis Ideas | Quick idea capture with automatic connection detection |
| `/metis_notes` | Metis Notes | Add or view personal notes and journal entries |
| `/metis_weekly` | Metis Weekly | Generate weekly summary: ideas, papers, meetings, projects, PhD progress |
| `/metis_research` | Metis Research | Research session: load article context, check tracked files, suggest next steps |
| `/metis_status` | Metis Status | Quick project + task status overview — blocked, overdue, in progress |

Skills are defined in: `.claude/skills/`

### How invocation works

**Option A — Let Metis route (recommended):**
```
/metis Review my Article 1 draft
```
Metis will:
1. Analyze the request
2. Announce: "Routing to Epidemiologist (methodology) + Writing Partner (grammar). Complexity: chain."
3. Load each agent's system prompt, execute sequentially
4. Write output files to `07_outputs/reviews/{agent-slug}/`
5. Log each run to the `agent_runs` database table
6. Return a summary of what was done and where outputs are

**Option B — Call an agent directly:**
```
/librarian search HAT passive case detection 2024
```
I will load `agents/librarian/system-prompt.md`, act as the Librarian, do the work, record the output, then return to general coordination.

You can switch agents mid-conversation by invoking a new one.

### The complete workflow: dashboard + Claude Code

```
Dashboard (browser)          Claude Code (terminal)
─────────────────            ──────────────────────
See tasks & priorities  →    /metis [any request]
                             Metis routes → agent(s)
                             Agent does the work
                             Writes to outputs/reviews/
                             Logs to agent_runs table
See results in Agents tab ←  Done. Summary returned.
```

**Output convention:** Every substantive agent output goes to:
```
outputs/reviews/{agent-slug}/{YYYY-MM-DD}_{task-slug}.md
```

**Recording convention:** After writing the file, log the run so the dashboard tracks it:
```r
log_agent_run(paths, "agent-slug", "task summary", "input/path", "output/path")
```

**Complexity levels Metis uses:**

| Level | When | Approach |
|---|---|---|
| Quick | Factual question, status check | Direct answer, DB log only |
| Standard | Single-agent review or search | One agent, output file + DB log |
| Deep | Multi-file analysis, methodology challenge | Thorough analysis, detailed output |
| Chain | Needs 2+ agent perspectives | Multiple agents, one output each |

---

## Agent routing guide (for Metis)

When a request arrives, route as follows:

| Input type | Primary agent | Secondary |
|---|---|---|
| Paper, article, source | Librarian | PhD Architect |
| Meeting note, audio, transcript | Meeting Memory | Metis |
| R script, code, bug, FastAPI | Software Engineer | Frontend Designer Builder |
| PhD structure, article fit | PhD Architect | Writing Partner |
| Statistical method question | Methods Coach | PhD Architect |
| News, world events, briefing | News Radar | Metis |
| New app, tool, MCP server | Builder | RC Builder |
| Modify/extend Metis system itself | RC Builder | Software Engineer |
| Slide deck, figure | Presentation Maker | Frontend Designer Builder |
| Idea, brainstorm | Metis (capture → route) | — |
| RSS/feed automation, news curation | News Aggregator | News Radar |
| UI/UX build, design system, CSS, web interface | Frontend Designer Builder | Software Engineer |
| Existing UI audit, design critique | Design Auditor | Frontend Designer Builder |
| Diagrams, charts, visualizations | Visualization Maker | Frontend Designer Builder |
| Content extraction, web scraping, PDFs | Content Harvester | Librarian |
| Learning paths, curriculum, competency maps | Learning Architect | Methods Coach |
| Study design, epi methods, surveillance | Epidemiologist | Methods Coach |
| CSV, Excel, dataset, cleaning, missing values, duplicates, outliers, data quality | Data Analyst | Data Guardian |
| Unclear | Metis | Ask one clarifying question |

---

## Project context

### Active projects (with git repos)
- **HAT Dashboard** — `SVerITG/HAT_Dashboard_1.0`, branch `server`
- **HAT Clustering / Risk Mapping** — local git initialized, push to `SVerITG/HAT_Clustering` pending
- **MLM Course** — `SVerITG/MLM_course`

### PhD
- Topic: elimination / post-elimination surveillance (being defined)
- Three articles in progress — need to be aligned to the thesis backbone
- Most time-pressured priority

### Key paths
- Literature: `inputs/literature/sleeping-sickness/`
- Code staging: `inputs/code/` (copy scripts here for review)
- Project cards: `projects/active/`
- Inbox: `inbox/` (drop anything here for Metis to route)
- Journal / session handoffs / ideas: `journal/`
- Agent patterns (user-editable prompts): `system/config/patterns/`
- Implementation progress tracker: `system/config/implementation-progress.json`
- Dashboard: `system/app/`
- MCP server: `system/mcp-server/`
- Config: `system/config/`
- Knowledge (library + domains + courses): `knowledge/`
- Outputs (reviews, articles, etc.): `outputs/`

---

## Per-project tracking: PLANNING.md

Each active project has a **PLANNING.md** file in its external project root. This is the single source of truth for what was done in the last session and what comes next. It is written by whoever worked last (Claude or the user directly) and read at the start of every session.

**When any project question arrives, read that project's PLANNING.md first — before answering.**

| Project | PLANNING.md path |
|---|---|
| HAT Dashboard | `C:/Users/sverschaeve/OneDrive - ITG/Documents/2. HAT disease/1. Epi Data/7. Dashboard/PLANNING.md` |
| HAT Clustering | `C:/Users/sverschaeve/OneDrive - ITG/Documents/2. HAT disease/1. Epi Data/4. Clustering/PLANNING.md` |
| MLM Course | `C:/Users/sverschaeve/OneDrive - ITG/Documents/9. Education/1. Multilevel Analysis/PLANNING.md` |

**Use `read_file()` to open the relevant PLANNING.md.** Update it at the end of each session with what was done and what the next step is.

**Planning tab** — The Metis dashboard Planning tab shows all PLANNING.md files together and tracks changes. Any file with `watch=1` in `tracked_files` is scanned for changes when the dashboard polls.

---

## Metis standing priorities

Every session, check:
1. **Read the relevant project's PLANNING.md** (paths above) — this is the fastest way to understand where things stand.
2. What is new in `inbox/`?
3. What tasks are overdue or blocked?
4. What does the PhD need this week?
5. Is there anything uncommitted or unpushed in the git projects?
6. What should the user be aware of that they have not asked about?

---

## Software stack

- **Python** — dashboard (FastAPI + HTMX), MCP server, scripting
- **R / RStudio** — statistical analysis
- **SQLite** — Metis metadata store (`system/app/data/metis.sqlite`)
- **FastAPI + HTMX** — dashboard (`system/app/`)
- **Docker** — containerization (planned)
- **Windows + WSL** — host OS
- **OneDrive** — file sync
- **GitHub** — version control (`SVerITG` account)
