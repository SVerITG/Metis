# Metis Second Brain — Claude Code Configuration

This is the Metis second-brain system for a Senior Researcher / Epidemiologist / Public Health Methodologist
working on sleeping sickness (HAT), PhD planning, AI development, and personal learning.

**Owner:** sverschaeve
**Root:** This folder
**Dashboard:** `07_outputs/apps/metis-dashboard/`
**Agents:** `02_agents/`

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

**Default: just call `/metis`** with any request. Metis will analyze it, pick the right agent(s), choose the complexity level, execute the work, and record everything to the PKM. You don't need to know which agent to use.

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
| `/software-engineer` | Software Engineer | Code review, debugging, Shiny features, R scripts |
| `/dashboard-engineer` | Dashboard Engineer | UI/UX decisions, visualization design |
| `/meeting-memory` | Meeting Memory | Transcribe, structure, and brief meeting notes |
| `/news-radar` | News Radar | What happened in the world, brief generation |
| `/builder` | Builder | Build new apps, tools, MCP servers |
| `/presentation-maker` | Presentation Maker | PowerPoint slides, visual summaries |
| `/learning-coach` | Learning Coach | Skill progression, learning paths, statistics competencies |
| `/career-coach` | Career Coach | EU job prep, CV support, career strategy |

| `/news-aggregator` | News Aggregator | Automated RSS collection, feed curation, signal tagging |
| `/ux-engineer` | UX Engineer | Design system, UI/UX standards, accessibility, responsive layout |
| `/epidemiologist` | Epidemiologist | Study design review, methodology challenge, Socratic questioning |
| `/cybersecurity` | Cybersecurity | URL validation, prompt injection defense, threat intel, agent audit |
| `/data-guardian` | Data Guardian | PII protection, patient data blocking, file transmission approval |

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
I will load `02_agents/librarian/system-prompt.md`, act as the Librarian, do the work, record the output, then return to general coordination.

You can switch agents mid-conversation by invoking a new one.

### The complete workflow: dashboard + Claude Code

```
Dashboard (browser)          Claude Code (terminal)
─────────────────            ──────────────────────
See tasks & priorities  →    /metis [any request]
                             Metis routes → agent(s)
                             Agent does the work
                             Writes to 07_outputs/reviews/
                             Logs to agent_runs table
See results in Agents tab ←  Done. Summary returned.
```

**Output convention:** Every substantive agent output goes to:
```
07_outputs/reviews/{agent-slug}/{YYYY-MM-DD}_{task-slug}.md
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
| R script, code, bug | Software Engineer | Dashboard Engineer |
| PhD structure, article fit | PhD Architect | Writing Partner |
| Statistical method question | Methods Coach | PhD Architect |
| News, world events, briefing | News Radar | Metis |
| New app, tool, MCP server | Builder | Software Engineer |
| Slide deck, figure | Presentation Maker | Dashboard Engineer |
| Idea, brainstorm | Metis (capture → route) | — |
| RSS/feed automation, news curation | News Aggregator | News Radar |
| UI/UX review, design system, CSS | UX Engineer | Dashboard Engineer |
| Study design, epi methods, surveillance | Epidemiologist | Methods Coach |
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
- Literature: `05_sources/literature/sleeping-sickness/`
- Code staging: `05_sources/code/` (copy scripts here for review)
- Project cards: `04_projects/active/`
- Inbox: `00_inbox/` (drop anything here for Metis to route)
- Dashboard: `07_outputs/apps/metis-dashboard/`

---

## Metis standing priorities

Every session, check:
1. What is new in `00_inbox/`?
2. What tasks are overdue or blocked?
3. What does the PhD need this week?
4. Is there anything uncommitted or unpushed in the git projects?
5. What should the user be aware of that they have not asked about?

---

## Software stack

- **R / RStudio** — primary analysis and dashboard
- **Python** — scripting, MCP servers
- **SQLite** — Metis metadata store (`07_outputs/apps/metis-dashboard/data/metis.sqlite`)
- **R Shiny** — dashboard (`metis-dashboard` app)
- **Docker** — containerization (planned)
- **Windows + WSL** — host OS
- **OneDrive** — file sync
- **GitHub** — version control (`SVerITG` account)
