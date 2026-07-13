# Metis Research Cortex — Claude Code Configuration

**Project ID:** `metis-dashboard`
**Domain:** Public health research · Neglected Tropical Diseases
**App:** `system/app-py/`
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

## Contextual discovery — actively guide the user to features

Metis has many capabilities a new user can't find on their own. Don't make them hunt — surface the right one **at the moment it becomes useful** (the just-in-time pattern). At natural trigger moments, call `next_discovery_tip(context="<comma-separated tags>")`; if it returns a tip, **weave it into your reply as one natural sentence** (never a robotic dump). It returns at most one *unseen* tip and records it, so nothing repeats.

Trigger moments → tags to pass:
- User is building a library / background / knowledge layer → `library,background`
- User writes or shares R/Python code (esp. first time) → `r-code,coding,first-code`
- User starts or works on a project → `project,working-on-project`
- A dataset / patient / sensitive data appears → `data,sensitive`
- User asks a knowledge / literature question → `question,literature-question`
- A new paper / PDF appears → `paper,pdf`
- A meeting transcript / notes appear → `meeting,transcript`
- User just edited code → `code-change`
- First session / user seems unsure → `onboarding,first-session`

**First session / "what can you do?"** → call `discovery_intro()` once.

**Respect the user's control:**
- "stop the tips" / "don't show these" → `set_discovery_tips(enabled=False)`
- "remind me later" / "not now" → `set_discovery_tips(snooze_days=7)`
- "I'm a power user" / "I know my way around" → `set_discovery_tips(power_user=True)`

---

## How to invoke agents

**Default: just call `/metis`** with any request. Metis will analyze it, pick the right agent(s), choose the complexity level, execute the work, and record everything to the RC. You don't need to know which agent to use.

```
/metis Review my Article 1 draft for methodology and grammar
→ Metis routes to: Epidemiologist (methodology) + Writing Partner (grammar)
→ Complexity: chain (opus + subagents)
→ Output: outputs/reviews/epidemiologist/... + outputs/reviews/writing-partner/...
```

**Direct call:** If you already know which agent you want, call them directly:

| Invocation | Agent | When to use |
|---|---|---|
| `/metis` | Metis | **Default entry point.** Any request — she routes, executes, and records |
| `/librarian` | Librarian | Find papers, update literature metadata, search sources |
| `/phd-architect` | PhD Architect | Thesis structure, article alignment, chapter planning |
| `/writing-partner` | Writing Partner | Draft text, improve writing, structure arguments |
| `/methods-coach` | Methods Coach | Epidemiological methods, statistics, sampling, R methodology |
| `/dhis2-expert` | DHIS2 Expert | DHIS2 server, metadata, tracker programs, dashboards, NTD implementations |
| `/software-engineer` | Software Engineer | Code review, debugging, Python/R scripts, FastAPI |
| `/frontend-designer-builder` | Frontend Designer Builder | UI/UX decisions, design system, visualization design |
| `/meeting-memory` | Meeting Memory | Transcribe, structure, and brief meeting notes |
| `/news-radar` | News Radar | What happened in the world, brief generation |
| `/builder` | Builder | Build new apps, tools, MCP servers |
| `/rc-builder` | RC Builder | Modify/extend Metis itself — new agents, dashboard phases, MCP tools |
| `/presentation-maker` | Presentation Maker | PowerPoint slides, visual summaries |
| `/learning-coach` | Learning Coach | Skill progression, learning paths, statistics competencies |
| `/course-builder` | Course Builder | Build a course end-to-end: intake → harvest → curriculum → draft → review → publish |
| `/career-coach` | Career Coach | EU job prep, CV support, career strategy |
| `/news-aggregator` | News Aggregator | Automated RSS collection, feed curation, signal tagging |
| `/design-auditor` | Design Auditor | Audit existing UIs, reverse-engineer design decisions |
| `/visualization-maker` | Visualization Maker | Diagrams, charts, system maps, ggplot2, Plotly |
| `/content-harvester` | Content Harvester | Extract and structure content from web, PDFs, DOCX, YouTube, GitHub |
| `/background-maker` | Background Maker | Build permanent specialist knowledge layers (RAG corpus) |
| `/learning-architect` | Learning Architect | Curriculum design, learning paths, spaced repetition, competency maps |
| `/epidemiologist` | Epidemiologist | Study design review, methodology challenge, Socratic questioning |
| `/cybersecurity` | Cybersecurity | URL validation, prompt injection defense, threat intel, agent audit |
| `/data-guardian` | Data Guardian | PII protection, patient data blocking, file transmission approval |
| `/data-analyst` | Data Analyst | Profile, clean, and compare tabular datasets (CSV/Excel/SPSS/Stata) — local only |
| `/critic` | Critic | Verify, challenge, and quality-check outputs from other agents |
| `/memory-curator` | Memory Curator | Consolidate session history into permanent memory, retrieve past context |
| `/biostatistician` | Biostatistician | R package development, simulation studies, sample size/power, Monte Carlo |

**Phase 5 skills (automation & scaffolding):**

| Invocation | Skill | When to use |
|---|---|---|
| `/new-project` | New Project | Scaffold a new Shiny app, R script, report, or tool |
| `/add-context` | Add Context | Add a specialist context to your profile |
| `/metis-config` | Metis Config Wizard | First-time setup, reconfigure, or add context |
| `/safe-analysis` | Safe Analysis | Work with sensitive/patient data: Metis writes the script, you run it locally |
| `/metis-doctor` | Metis Doctor | Health check — is Metis working on this computer? |
| `/metis-customize` | Metis Customize | Change projects, look, tone, or behaviour |
| `/verify-work` | Verify Work | Generate→verify gate after code changes |
| `/basket` | Basket Intake | Drop documents in `basket/`, classify and route them |
| `/research-mode` | Research Mode | Library-first answers: search your indexed library first, complement from the internet |
| `/code-intake` | Code Intake | Scan R/Python scripts to extract metadata and build data dictionary |

**RC workflow commands:**

| Invocation | Skill | When to use |
|---|---|---|
| `/metis-brainstorm` | Metis Brainstorm | Activate cross-pollination for an idea; surfaces connections |
| `/metis-handoff` | Metis Handoff | Generate portable context brief for switching AI or device |
| `/metis-ideas` | Metis Ideas | Quick idea capture with automatic connection detection |
| `/metis-notes` | Metis Notes | Add or view personal notes and journal entries |
| `/metis-weekly` | Metis Weekly | Generate weekly summary: ideas, papers, meetings, projects |
| `/metis-research` | Metis Research | Research session: load article context, check tracked files |
| `/metis-status` | Metis Status | Quick project + task status overview |

### How invocation works

**Option A — Let Metis route (recommended):**
```
/metis Review my Article 1 draft
```
Metis will:
1. Analyze the request
2. Announce: "Routing to Epidemiologist (methodology) + Writing Partner (grammar). Complexity: chain."
3. Load each agent's system prompt, execute sequentially
4. Write output files to `outputs/reviews/{agent-slug}/`
5. Log each run to the `agent_runs` database table
6. Return a summary of what was done and where outputs are

**Option B — Call an agent directly:**
```
/librarian search sleeping sickness surveillance methods 2024
```

### Complexity levels Metis uses

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
| Build or plan a learning course | Course Builder | Learning Architect |
| Paper, article, source | Librarian | PhD Architect |
| Meeting note, audio, transcript | Meeting Memory | Metis |
| R script, code, bug, FastAPI | Software Engineer | Frontend Designer Builder |
| DHIS2 configuration, tracker, API | DHIS2 Expert | Software Engineer / Epidemiologist |
| PhD structure, article fit | PhD Architect | Writing Partner |
| Statistical method question | Methods Coach | PhD Architect |
| News, world events, briefing | News Radar | Metis |
| New app, tool, MCP server | Builder | RC Builder |
| Modify/extend Metis system | RC Builder | Software Engineer |
| Slide deck, figure | Presentation Maker | Frontend Designer Builder |
| Idea, brainstorm | Metis (capture → route) | — |
| RSS/feed automation, news curation | News Aggregator | News Radar |
| UI/UX build, design system, CSS | Frontend Designer Builder | Software Engineer |
| Existing UI audit, design critique | Design Auditor | Frontend Designer Builder |
| Diagrams, charts, visualizations | Visualization Maker | Frontend Designer Builder |
| Content extraction, web scraping | Content Harvester | Librarian |
| Knowledge layer / RAG corpus | Background Maker | Content Harvester + Librarian |
| Learning paths, curriculum | Learning Architect | Methods Coach |
| Study design, epi methods | Epidemiologist | Methods Coach |
| R package, simulation, power | Biostatistician | Methods Coach / Software Engineer |
| CSV, Excel, dataset, cleaning | Data Analyst | Data Guardian |
| Validate / quality-check output | Critic | — |
| Session consolidation, memory | Memory Curator | — |
| Unclear | Metis | Ask one clarifying question |

---

## ⚠️ Applying MCP server code changes

The MCP server runs an **installed copy** in the venv, not the source. Editing a tool's source does nothing until you reinstall:

```bash
bash tools/reinstall-mcp.sh     # reinstall package from current source
# then reconnect: Claude Code → /mcp → reconnect 'metis-rc'
bash tools/test-mcp.sh          # smoke-test (exit 0 = healthy)
```

The dashboard reads source directly — dashboard edits take effect on restart with no reinstall.

---

## Claude Desktop — how Metis is reachable there

Claude Desktop does **not** read this CLAUDE.md and has **no** access to the Claude Code skills in `.claude/skills/`. It only sees what the MCP server exposes:

- **MCP prompts** (`system/mcp-server/src/metis_mcp/tools/prompts.py`) — 42 prompts surface in Desktop's prompt picker: a `metis` router, one prompt per agent, and workflow prompts.
- **Full tool reachability** via progressive tool disclosure: ~80 everyday `core` tools load, the rest are retrieved on demand via `find_tools(query)` / `load_tool_group(name)`.

---

## Session tracking — three memory layers

Every session must record work in **all three layers**:

1. **Session memory** — what we did and changed this conversation:
   - `save_session_summary(summary=<2-5 sentences>, key_topics=[...], decisions=[...])`
   - Populates the "Last Session" strip on the Today surface
   - Searchable via `search_session_memory()`

2. **Agent memory** — summary of what each specialist did:
   - `log_agent_run(agent_slug=<slug>, task_summary=<one line>, session_id=<id>)`
   - Feeds the dashboard's Agents tab and run-coverage tracking

3. **Project memory** — what changed in the project and what's still to do:
   - `update_project_memory(project_id=<id>, what_was_done=<summary>, next_steps=<what remains>)`
   - Keeps the project card current on the dashboard's Work tab

Always close the loop at the end of substantive work — a session that isn't recorded is a session that never happened.

---

## Metis standing priorities

Every session, check:
1. **Read `system/config/feature-backlog.md`** — the persistent list of everything requested and not yet built. If the user asks for something already on the backlog, build it immediately.
2. What tasks are overdue or blocked?
3. What are the most pressing research priorities this week?

**Feature request rule:** When the user requests any new feature, write it to `system/config/feature-backlog.md` immediately — even if you are about to build it.

---

## Key paths

- Literature: `inputs/literature/`
- Code staging: `inputs/code/`
- Project cards: `projects/active/`
- Inbox: `inbox/`
- Journal: `journal/`
- Agent patterns: `system/config/patterns/`
- Dashboard: `system/app-py/` (FastAPI + HTMX)
- MCP server: `system/mcp-server/`
- Config: `system/config/`
- Knowledge: `knowledge/`
- Outputs: `outputs/`
- Basket: `basket/` (flat holding area; `basket/private/` is off-limits to all agents)

---

## Metis integration (project-level)

The Metis MCP server (`metis-rc`) is available. Use its tools to:
- `update_task` — mark tasks done or update status
- `add_task` — add new tasks to this project (project_id: `metis-dashboard`)
- `update_project` — update next_step or description

Changes made via these tools appear immediately in the Metis dashboard.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
