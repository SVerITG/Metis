# Metis Second Brain — Claude Code Configuration

This is the Metis Research Cortex — a second-brain for researchers in any field that keeps your data on your machine; reasoning runs on Claude (the Anthropic API).

**Owner:** [User] — address by their configured name (see `system/config/user-config.yaml`)
**Root:** This folder
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

The tool is **earned + rate-capped**: it already skips features the user uses, caps to ~1 tip / 20 min and a few per day, and respects snooze/mode — so just call it freely at trigger moments; it returns `''` when nothing should show.

**First session / "what can you do?"** → call `discovery_intro()` once (the 3-5 core capabilities), not the full list.

**Respect the user's control:**
- "stop the tips" / "don't show these" → `set_discovery_tips(enabled=False)`
- "remind me later" / "not now" → `set_discovery_tips(snooze_days=7)`
- "I'm a power user" / "I know my way around" → `set_discovery_tips(power_user=True)` (tips stay quiet)
- `discovery_status()` reports on/off, mode, and adoption. Always confirm the change in one line. Never stack tips or nag.

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
| `/dhis2-expert` | DHIS2 Expert | DHIS2 server, metadata, tracker programs, dashboards, app development, NTD implementations |
| `/software-engineer` | Software Engineer | Code review, debugging, Python/R scripts, FastAPI |
| `/frontend-designer-builder` | Frontend Designer Builder | UI/UX decisions, design system, visualization design, web interfaces |
| `/meeting-memory` | Meeting Memory | Transcribe, structure, and brief meeting notes |
| `/news-radar` | News Radar | What happened in the world, brief generation |
| `/builder` | Builder | Build new apps, tools, MCP servers |
| `/rc-builder` | RC Builder | Modify/extend Metis itself — new agents, dashboard phases, MCP tools |
| `/presentation-maker` | Presentation Maker | PowerPoint slides, visual summaries |
| `/learning-coach` | Learning Coach | Skill progression, learning paths, statistics competencies |
| `/course-builder` | Course Builder | Build a course end-to-end: intake questionnaire → harvest → curriculum → draft → review → publish |
| `/career-coach` | Career Coach | EU job prep, CV support, career strategy |

| `/news-aggregator` | News Aggregator | Automated RSS collection, feed curation, signal tagging |
| `/design-auditor` | Design Auditor | Audit existing UIs, reverse-engineer design decisions, prioritized improvements |
| `/visualization-maker` | Visualization Maker | Diagrams, charts, system maps, ggplot2 figures, Plotly |
| `/content-harvester` | Content Harvester | Extract and structure content from web, PDFs, DOCX, YouTube, GitHub |
| `/background-maker` | Background Maker | Build permanent specialist knowledge layers (RAG corpus) from papers, reports, web — scrubbed and indexed |
| `/learning-architect` | Learning Architect | Curriculum design, learning paths, spaced repetition, competency maps |
| `/epidemiologist` | Epidemiologist | Study design review, methodology challenge, Socratic questioning |
| `/cybersecurity` | Cybersecurity | URL validation, prompt injection defense, threat intel, agent audit |
| `/data-guardian` | Data Guardian | PII protection, patient data blocking, file transmission approval |
| `/data-analyst` | Data Analyst | Profile, clean, and compare tabular datasets (CSV/Excel/SPSS/Stata) — local only |
| `/critic` | Critic | Verify, challenge, and quality-check outputs from other agents before acting on them |
| `/memory-curator` | Memory Curator | Consolidate session history into permanent memory, retrieve past context, memory health check |
| `/biostatistician` | Biostatistician | R package development, simulation studies, sample size / power calculations, custom estimators |

**Phase 5 skills (automation & scaffolding):**

| Invocation | Skill | When to use |
|---|---|---|
| `/schedule` | Schedule Morning Agents | Set up 07:00 News Radar + 07:30 Librarian via Task Scheduler or RemoteTrigger |
| `/new-project` | New Project | Scaffold a new Shiny app, R script, report, or tool in Metis |
| `/add-context` | Add Context | Add a specialist context to your profile without re-running /metis_config |
| `/metis_config` | Metis Config Wizard | First-time setup, reconfigure, or add context — 13-section guided wizard |
| `/safe-analysis` | Safe Analysis | Work with sensitive/patient data without sending it: Metis writes the script, you run it locally, only derived metadata comes back ("send code, not data") |
| `/metis-doctor` | Metis Doctor | Health check — is Metis working on this computer? Plain-language diagnostic of Python, DB, API key, RAG engine, dashboard, Desktop registration |
| `/metis-customize` | Metis Customize | Make Metis yours — change projects, look, tone, or behaviour (routes structural changes to RC Builder; shows the safety disclaimer) |
| `/verify-work` | Verify Work | The in-the-moment generate→verify gate: after a code change, run the external signals (py_compile/tests/reinstall+smoke/harness) + an independent skeptic before trusting it's done. The working-loop tier of self-reflexion. |
| `/basket` | Basket Intake | Drop documents in `basket/`, then this lists + classifies them (infers what each is, scans datasets for sensitive data), asks a short questionnaire, and promotes each to the right input folder (`inputs/literature`, `inputs/code`, knowledge layers…). Never touches `basket/private/`. |
| `/research-mode` | Research Mode | Library-first answers: searches your indexed library + memory first, complements from the internet only on a real gap and with your OK (local-first), and links the cited answer back to your projects and work. |
| `/code-intake` | Code Intake | Scan R/Python scripts to extract metadata (packages, file paths, variables), generate safe profiling scripts, and build a per-project data dictionary — all without the AI seeing any data. |

**RC workflow commands:**

| Invocation | Skill | When to use |
|---|---|---|
| `/metis_brainstorm` | Metis Brainstorm | Activate cross-pollination for an idea; loads RC context and surfaces connections |
| `/metis_handoff` | Metis Handoff | Generate portable context brief for switching AI, hitting token limits, or continuing on another device |
| `/metis_ideas` | Metis Ideas | Quick idea capture with automatic connection detection |
| `/metis_notes` | Metis Notes | Add or view personal notes and journal entries |
| `/metis_weekly` | Metis Weekly | Generate weekly summary: ideas, papers, meetings, projects, active research |
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
4. Write output files to `outputs/reviews/{agent-slug}/`
5. Log each run to the `agent_runs` database table
6. Return a summary of what was done and where outputs are

**Option B — Call an agent directly:**
```
/librarian search [your topic] surveillance methods 2024
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
| Build or plan a learning course | Course Builder | Learning Architect |
| Paper, article, source | Librarian | PhD Architect |
| Meeting note, audio, transcript | Meeting Memory | Metis |
| R script, code, bug, FastAPI | Software Engineer | Frontend Designer Builder |
| DHIS2 configuration, tracker, dashboard, API, implementation | DHIS2 Expert | Software Engineer / Epidemiologist |
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
| Build a knowledge layer / RAG corpus for a domain | Background Maker | Content Harvester + Librarian |
| Learning paths, curriculum, competency maps | Learning Architect | Methods Coach |
| Study design, epi methods, surveillance | Epidemiologist | Methods Coach |
| R package development, simulation study, sample size, power analysis, Monte Carlo, CRAN | Biostatistician | Methods Coach / Software Engineer |
| CSV, Excel, dataset, cleaning, missing values, duplicates, outliers, data quality | Data Analyst | Data Guardian |
| Validate / challenge / quality-check an agent's output | Critic | — |
| Consolidate session into memory, retrieve past context, memory health | Memory Curator | — |
| Unclear | Metis | Ask one clarifying question |

---

## Project context

### Active projects (with git repos)
- **My Research Project** — `{your-github-username}/my-research-project`, branch `main`
- **My Dataset Analysis** — local git initialized, push pending
- **My Statistics Course** — `{your-github-username}/my-statistics-course`

### Key paths
- Literature: `inputs/literature/[your-topic]/`
- Code staging: `inputs/code/` (copy scripts here for review)
- Project cards: `projects/active/`
- Inbox: `inbox/` (drop anything here for Metis to route)
- Journal / session handoffs / ideas: `journal/`
- Agent patterns (user-editable prompts): `system/config/patterns/`
- Implementation progress tracker: `system/config/implementation-progress.json`
- Dashboard: `system/app-py/` (FastAPI + HTMX; the DB it uses lives in `system/app/data/`)
- MCP server: `system/mcp-server/`
- Config: `system/config/`
- Knowledge (library + domains + courses): `knowledge/`
- Outputs (reviews, articles, etc.): `outputs/`
- Basket (legacy inspiration docs): `basket/` — flat folder, drop anything here

### Basket — inspiration & legacy documents

`basket/` is a flat holding area for any old document kept as a reference for future work (presentations, meeting notes, scripts, reports — anything). Not indexed. Not categorised. `basket/private/` is the only subfolder — for personal or patient data that AI tools must never read.

**Agent rule:** Any agent producing new content (Presentation Maker, Writing Partner, Software Engineer) should call `list_basket()` first and read relevant files with `read_file()` to pick up style or content cues.
**No agent may access `basket/private/` under any circumstances.**
**MCP tools:** `list_basket()` — `promote_basket_item(source, target)` — `read_file(path)`
**Removable.** No DB rows. `rm -rf basket/` is safe.

---

## Per-project tracking: PLANNING.md

Each active project has a **PLANNING.md** file in its external project root. This is the single source of truth for what was done in the last session and what comes next. It is written by whoever worked last (Claude or the user directly) and read at the start of every session.

**When any project question arrives, read that project's PLANNING.md first — before answering.**

| Project | PLANNING.md path |
|---|---|
| My Research Project | `C:/Users/{username}/[path-to-project]/PLANNING.md` |
| My Dataset Analysis | `C:/Users/{username}/[path-to-analysis]/PLANNING.md` |
| My Statistics Course | `C:/Users/{username}/[path-to-course]/PLANNING.md` |

**Use `read_file()` to open the relevant PLANNING.md.** Update it at the end of each session with what was done and what the next step is.

**Planning tab** — The Metis dashboard Planning tab shows all PLANNING.md files together and tracks changes. Any file with `watch=1` in `tracked_files` is scanned for changes when the dashboard polls.

---

## Metis standing priorities

**First-run check (before anything else):** If `system/config/.first-run` exists, stop and run `/metis_config` immediately. Do not greet, do not check tasks — the config wizard takes priority. The wizard deletes the marker when complete.

Every session, check:
1. **Read `system/config/feature-backlog.md`** — the persistent list of everything requested and not yet built. Check what is open before starting any new work. If the user asks for something already on the backlog, build it immediately rather than acknowledging and deferring.
2. **Read the relevant project's PLANNING.md** (paths above) — this is the fastest way to understand where things stand.
3. What is new in `inbox/`?
4. What tasks are overdue or blocked?
5. What are the most pressing research priorities this week?
6. Is there anything uncommitted or unpushed in the git projects?
7. What should the user be aware of that they have not asked about?

**Feature request rule:** When the user requests any new feature or functionality during a session, write it to `system/config/feature-backlog.md` immediately — even if you are about to build it. This ensures it persists if the session ends before completion.

---

## Software stack

- **Python** — dashboard (FastAPI + HTMX), MCP server, scripting
- **R / RStudio** — statistical analysis
- **SQLite** — Metis metadata store (`system/app/data/metis.sqlite`)
- **FastAPI + HTMX** — dashboard (`system/app-py/`)
- **Docker** — containerization (planned)
- **Windows + WSL** — host OS
- **OneDrive** — file sync
- **GitHub** — version control (`{your-github-username}` account)

### ⚠️ Applying MCP server code changes (important)

The MCP server runs an **installed copy** of the package in the venv (`~/.local/share/metis-mcp/.venv/.../site-packages/metis_mcp/`), **not** the source in `system/mcp-server/src/`. Editing a tool's source does **nothing** to the running server until you reinstall **and** reconnect:

```bash
bash tools/reinstall-mcp.sh     # reinstall package from current source
# then reconnect: Claude Code → /mcp → reconnect 'metis-rc'  (Claude Desktop → quit & reopen)
bash tools/test-mcp.sh          # smoke-test the server on this system (exit 0 = healthy)
```

The dashboard (`system/app-py/`) reads source directly, so dashboard edits take effect on restart with no reinstall. The server self-checks at every start and writes `system/config/mcp-health.json`; it warns in its logs if it detects stale installed code.

### Claude Desktop — how Metis is reachable there

Claude Desktop does **not** read this CLAUDE.md and has **no** access to the Claude Code skills in `.claude/skills/`. It only sees what the MCP server exposes. So the routing/agent behavior you get from `/metis` in the terminal is delivered to Desktop two ways:

- **MCP prompts** (`system/mcp-server/src/metis_mcp/tools/prompts.py`) — 42 prompts surface in Desktop's prompt picker: a `metis` router (calls `run_metis`, announces the routing, loads + adopts the chosen agent via `get_agent_context`, logs via `log_agent_run`), one prompt per agent (33), and 8 workflow prompts (morning/safe-analysis/research/capture/handoff/weekly/doctor/customize). **Editing a prompt requires the same reinstall + reconnect** as any MCP code change.
- **Full tool reachability** — Desktop has ONE connection and ONE tool subset for the whole session (no per-agent relaunch). `_default` in `system/config/tool-subsets.json` stays `"all"` so the per-agent SUBSET mechanism never hides capability. The toolset is instead trimmed by **progressive tool disclosure** (`METIS_TOOL_SEARCH=1` in `run.sh`): only the ~80 everyday `core` tools load, and the rest are retrieved on demand via `find_tools(query)` / `load_tool_group(name)` (see `tools/tool_search.py` and the `core` key in `tool-subsets.json`). This cuts the loaded toolset ~60% while keeping everything reachable — so the routed knowledge layer, DHIS2, data tools and transcription are one `find_tools` call away, not gone. Per-agent subsets still apply only when `METIS_AGENT_SUBSET=<slug>` is set explicitly. Set `METIS_TOOL_SEARCH=0` to load all tools (developer mode).

The smoke test (`tools/test-mcp.sh`) verifies prompts register on every run.

---

## VS Code integration

Metis works alongside VS Code — Claude Code (the Metis terminal) runs in the integrated terminal panel.

**Recommended setup:**
1. Install the **Claude Code extension** from the VS Code marketplace (search "Claude Code" by Anthropic)
2. Open your Research Cortex folder as the VS Code workspace: `File → Open Folder → …/Research Cortex/`
3. Open the integrated terminal: `Ctrl+\`` — Claude Code starts here with Metis active
4. The Workbench panel on the Work tab has a **VS Code** launcher button that opens any project folder directly

**Session flow:** Work in VS Code for coding and writing, switch to the terminal for `/metis` requests. Agent outputs land in `outputs/reviews/` and are immediately visible on the dashboard.

---

## macOS install

On macOS, Metis installs entirely through the Bash installer — no Python or Node knowledge required.

```bash
# From Terminal, in the Research Cortex folder:
bash metis/system/mcp-server/setup-mcp.sh
```

This script:
- Detects your macOS Python (uses Homebrew or system Python 3.10+)
- Creates a venv at `~/.local/share/metis-mcp/`
- Installs all dependencies and the MCP server package
- Registers the server with Claude Code (`~/.claude/settings.json`) and Claude Desktop
- Writes a launch script at `~/.local/share/metis-mcp/run.sh`

**Start the dashboard:**
```bash
bash metis/system/app-py/run.sh
# Open: http://127.0.0.1:8080
```

**Dashboard runs on port 8080** (not 8000). The run.sh reads your `METIS_RC_ROOT` automatically — no manual path configuration needed.
