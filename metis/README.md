<p align="center">
  <img src="system/app-py/static/metis-compass.svg" width="80" alt="Metis"/>
  <br/><br/>
  <img src="system/app-py/static/metis-wordmark.svg" width="220" alt="Metis"/>
  <br/>
  <sub><b>The Research Cortex</b></sub>
</p>

<h1 align="center">Your second brain. Built for science.</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square" alt="Python"/>
  <img src="https://img.shields.io/badge/MCP-compatible-green?style=flat-square" alt="MCP"/>
  <img src="https://img.shields.io/badge/Claude-powered-orange?style=flat-square" alt="Claude"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="MIT"/>
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" alt="Active"/>
</p>

---

> **Note from the author:** I currently use Metis for all my research work, but some functionalities are still under active development. This is an open-source project built for researchers, and I would genuinely welcome any kind of feedback — not just on specific features, but on the idea itself and your experience using it. If you try it, please open an issue or start a discussion. Your perspective as a researcher matters more than a developer's.

---

## The Underlying Idea

Not every researcher has the time — or the desire — to keep up with the rapidly changing landscape of AI tools. New models appear weekly. New workflows emerge daily. Meanwhile, your actual work continues: papers to read, methods to apply, meetings to run, grants to write, students to supervise.

**Metis is designed for that reality.**

It is a second brain, configured for AI use from the ground up. At its core is an MCP server — a protocol that lets Claude (and any compatible AI) access your entire research universe: your notes, your literature, your meetings, your ideas, your data. Every question you ask the AI is automatically enriched with context from your field, your history, and your current work.

But Metis goes further than retrieval. It is built around a principle that most productivity tools miss: **knowledge in isolation is inert.** A paper you read last year, a meeting note from last month, an idea you captured at 2am, and a news brief from this morning — these things are related. They connect to each other in ways you have not yet seen. Metis watches all of it and surfaces those connections automatically.

The result is not a smarter search engine. It is a system that thinks alongside you — remembering what you cannot, connecting what you have not had time to connect, and surfacing what is relevant before you know you need it.

**What makes this different from using Claude directly:**

When you ask Claude a question without Metis, you get a general answer from a model with general knowledge. When you ask Claude through Metis, the question is placed in the context of your field, your papers, your current projects, your open questions, and your recent work. The answer is calibrated to where you actually are, not where the average user is.

This matters more than it sounds. Epidemiology, ecology, economics, education research — every field has its own methods, terminology, standards, and debates. A researcher who has spent ten years in a field knows things that no general AI can know. Metis bridges that gap by making your accumulated knowledge available to the AI at the moment it needs it.

---

## Under the Hood

Metis is not a single application. It is a layered system of components that work together:

```
┌─────────────────────────────────────────────────────────────┐
│  You                                                        │
│  Claude Desktop · Claude Code · Any MCP client             │
├─────────────────────────────────────────────────────────────┤
│  Metis MCP Server  ·  120 tools  ·  local, always running  │
├────────────┬───────────┬──────────┬──────────┬─────────────┤
│  Library   │  Memory   │  Agents  │  Safety  │  Dashboard  │
│  Zotero    │  Ideas    │  26 spec │  Guardian│  FastAPI    │
│  BibTeX    │  Journal  │  ialists │  Cyber   │  9 tabs     │
│  Vector    │  Meetings │  routing │  guardrls│  local      │
└────────────┴───────────┴──────────┴──────────┴─────────────┘
│  SQLite (local)  ·  Your files  ·  Never leaves your machine│
└─────────────────────────────────────────────────────────────┘
```

**Local-first.** Your data never leaves your machine unless you explicitly send it. The database, the literature library, your notes and ideas — all stored locally in plain SQLite and Markdown files. You can open and read every file Metis creates.

**120 MCP tools.** From searching your literature to capturing an idea, from analysing a meeting transcript to profiling a dataset — each tool is a precise, callable operation that any MCP-compatible AI client can use. The exact count is printed by `setup-mcp.sh` at install time.

**26 specialist agents** (3 retired). Not one general-purpose AI, but a team of specialists: Librarians, Epidemiologists, Writing Partners, Data Guardians, Cybersecurity agents, Methods Coaches, Software Engineers, and more. Each agent has a defined role, a defined scope, and cannot exceed it. Metis routes your request to the right agent — or the right combination of agents — automatically.

**The innovation is not in the components.** Python, SQLite, FastAPI, the MCP protocol — none of these are new. The innovation is in how the components interact with each other and how you interact with them. A paper you read becomes context for the next meeting. An idea you capture becomes a search query against your literature. A news brief triggers a literature update. The connections happen without you doing anything.

**Self-improving.** Agents evaluate their own outputs and propose improvements. Those proposals queue in the dashboard until you review and approve them. No agent rewrites itself without your permission. Over time, Metis becomes more accurate, more relevant, and more personalised to how you think.

**Multi-layered memory.** Metis tracks context across five layers simultaneously:
- *Episodic* — every agent run, every session, every decision recorded with timestamp and outcome
- *Semantic* — your literature, notes, ideas, and meetings indexed for vector search (sqlite-vec + BAAI/bge-small-en, 384-dim embeddings)
- *Procedural* — the skill files that define how each agent thinks, edited and improved over time
- *Working* — the context of the current session, always visible in the dashboard's token pulse
- *Reflexive* — agent self-critiques after every run, themed weekly into self-improvement proposals you approve

Vector search across all five layers is exposed as `search_memory(query)` — ask "what have I read about X?" and get semantic matches from papers, meetings, ideas, and journal entries in one query.

**Claude-based. Claude-optimised.** Built for Claude Desktop and Claude Code using the MCP protocol. Agent skills are plain Markdown files — readable, editable, extensible, with no code required. As Claude improves, Metis improves with it.

**Regularly updated.** Tools, skills, and agents are added and refined continuously as research needs and AI capabilities evolve.

---

## Features

### Cross-pollination engine

The centrepiece of Metis. Every piece of knowledge you add — a paper, a meeting note, an idea, a news item — is indexed and cross-referenced with everything else.

When you capture a new idea, Metis automatically checks it against your literature, your recent meetings, and your open projects. When you read a new paper, Metis surfaces related work you already have, meeting discussions that touched the same topic, and ideas you recorded that connect to it. When a news story appears in your field, Metis links it to the papers that address the same question.

You do not manage these connections. They emerge from the structure of your knowledge.

### Literature management

Connect your full reference library in minutes:
- **Zotero**: API-based sync — Metis incrementally updates as you add papers
- **Mendeley**: Export as BibTeX (30 seconds) and import — all papers, all metadata
- **BibTeX / folder of PDFs**: Any source works

Once connected, your library is searchable by topic, author, journal, year, or abstract content. AI topic clustering groups papers into thematic collections automatically. Run `/metis-library-setup` for a guided 3-step connection.

### Idea capture and connection

Research happens everywhere — not just at your desk. Metis provides multiple entry points:
- **Reflection tab** in the dashboard — structured idea threads with context
- **Claude Desktop or Claude Code** — one command to capture anything
- **WhatsApp integration** — capture ideas from your phone; Metis logs them and cross-pollinates while you sleep

Every idea is stored with its connections: what papers it relates to, what meetings it appeared in, what other ideas it links to. Nothing gets lost. Everything is findable.

### Adaptive courses — learn what your research requires

This is one of Metis's most distinctive features. Tell Metis:
- What research question you are pursuing
- What methodology you plan to use

Metis designs a custom learning path that teaches you exactly the knowledge and statistical skills needed for that work. Not a generic course on statistics — a course built around your specific research needs, drawing on your existing knowledge level and filling precisely the gaps that stand between you and a rigorous, publishable result.

### Build and take courses

Beyond adaptive courses, Metis can build structured courses on any topic you choose — from biostatistics to qualitative methods to R programming. Each course includes lessons, exercises, and assessments. Your progress is tracked in the Learning tab. Spaced repetition surfaces what you need to review.

### Meeting intelligence

Three modes for different situations:
- **Record**: Transcribe audio directly into Metis during or after a meeting
- **Import**: Paste a transcript or meeting notes
- **Dictate**: Speak a summary after the meeting

Meeting Memory structures the transcript, extracts action items and decisions, and cross-references the discussion with your literature and open projects. "We discussed the sensitivity of the passive detection strategy" — Metis connects this to the three papers on case detection you have in your library, the project card you have for that study, and the idea you captured last week about the same topic.

### Local data analyst — profile and clean datasets without uploading them

The Data Analyst agent profiles, cleans, and compares tabular datasets entirely on your machine — CSV, Excel, SPSS, Stata. Returns a full structured profile (shape, dtypes, null %, unique counts, distributions, top categorical values), suggests cleaning operations with rationale, applies them to a new file (the original is never modified), and diffs the before/after profiles.

Critically: **no dataset path is ever URL-based, and column names are scanned against the PII pattern list before profiling**. Sensitive columns are surfaced before any analysis touches them. This makes Metis usable on patient-level CSVs that you cannot legally upload to a cloud API.

### Knowledge graph

The Knowledge tab renders a force-directed graph (D3) of your library, ideas, and projects. Edges show co-occurrence, citation links, and cross-pollination matches. Click any node to pivot the view to its neighbours. Useful when you sense that something connects but cannot articulate the link yet.

### Semantic memory search

Beyond keyword search, Metis indexes your literature, notes, ideas, and meeting transcripts as 384-dim vectors using `sqlite-vec` and BAAI's `bge-small-en` embedding model. The search bar in the Knowledge tab returns semantic matches: "papers about diagnostic accuracy in low-prevalence settings" surfaces the right work even when none of the words match exactly. Embeddings are computed and stored locally — nothing is sent to a remote vector service.

### Encrypted backup and export

A single MCP tool (`backup_db`) writes an AES-256-GCM encrypted snapshot of the entire Metis database to disk on demand. The passphrase is yours; the file is yours. Use this for off-site backup, for sharing a frozen state with a collaborator, or for migrating between machines without exposing the database in plain SQLite.

### Project tracking with one-click launchers

Each project in the Work tab has a card with status, next-step note, linked papers, linked outputs, and a launcher rail. One click opens the project in **VS Code**, **RStudio**, **Claude Code**, **Claude Desktop**, **File Explorer**, or directly to its **GitHub** page. The launcher uses the project's recorded path — no remembering which folder it was in.

### Health check — `/metis_doctor`

A one-screen self-test that verifies Python version, the SQLite database, your Anthropic API key, your `user-config.yaml`, agent and skill folders, folder-rename hygiene, MCP imports, and `.env` git safety. Run it whenever something feels off, after a `git pull`, or before sharing the repo. Each check returns OK / WARN / FAIL with a one-line plain-English explanation.

### Continuity across your research

Research projects span years. Metis tracks the full arc:
- Every project has a card: status, tasks, linked papers, linked outputs
- Every article draft is tracked: which version, which agents reviewed it, what feedback was given
- The PhD Architect maintains a bird's-eye view of how your articles align to your thesis backbone
- Session handoffs ensure nothing is lost when you return after days or weeks away

When you start a new session, Metis tells you where you left off, what is overdue, and what the next concrete step is.

### Weekly focus planning

Tell Metis your focus for the week — one research question, one article, one deadline. The Planner tab structures your tasks around that focus, surfacing what needs attention and putting everything else aside. Not a to-do list. A thinking tool.

### Morning briefing

Every morning, the News Radar compiles a briefing calibrated to your field and current projects: new publications, relevant news, preprint activity, funding announcements. The Librarian cross-references it with what you already have. By the time you open your laptop, Metis has already read the internet and filtered it for what matters to you.

### Full data protection — nothing leaves without your permission

Every piece of content that passes through Metis is classified before any external action is taken (see [Data Protection](#data-protection) below). Patient data is blocked unconditionally. Unpublished manuscripts require your explicit confirmation. No dataset is uploaded without your approval.

### Efficient token use

AI inference costs money and time. Metis manages this automatically:
- Each task is routed to the smallest model capable of handling it (Haiku → Sonnet → Opus)
- Context is cleared between sessions automatically
- A token pulse in the dashboard shows usage in real time
- A handoff brief is generated when a session approaches its context limit, so no work is lost

---

## Workflows

### Morning start

> You open your laptop. The dashboard is already running.

Metis has checked your RSS feeds, scanned for new papers matching your topics, and checked your tracked project files for changes. The Today tab shows you a briefing — what happened overnight, what is urgent today, what is coming up this week. You review it in 5 minutes and start work knowing you have not missed anything.

### Research session

> You are working on an article. You open Claude Code with `/metis-research`.

Metis loads the context for that article: which papers you have cited, what agent reviews have been done, what tasks are open, what your last session ended on. You write. You question. You ask Metis to challenge your methodology. The Epidemiologist agent applies the same critical lens a peer reviewer would. You get feedback before submission, not after.

### Idea capture

> You are reading a paper and something connects — a method from another field, a gap no one has addressed, a contradiction between this paper and one you read last year.

You type it into the Reflection tab, or dictate it into Claude Desktop. Metis logs it with a timestamp and immediately cross-pollinates: it surfaces the related paper, the meeting where you discussed the adjacent topic, and the project this might affect. The connection is recorded before you close the tab.

### Literature intake

> Someone emails you a paper. A colleague mentions a preprint. A search turns up twenty new results.

Drag the PDFs into the inbox folder, or paste DOIs into the Librarian. Metis processes them: extracts metadata, adds them to your library, checks for overlap with what you already have, and surfaces connections to your current projects. Your library stays current without manual management.

### Course building

> You are about to run an analysis you have never done before. You know the question but not the method.

Tell Metis: "I want to do a spatial cluster analysis of disease incidence for my article on district-level risk." Metis identifies the statistical skills you need (spatial autocorrelation, SaTScan, kernel density estimation), checks what you already know, and builds a short, focused course that gets you from here to a defensible methods section. You learn exactly what you need, not a textbook chapter.

### Meeting

> You are in a team meeting. Three topics come up that affect your current article.

After the meeting, you paste the notes into Metis or dictate a summary. Meeting Memory structures the transcript, extracts the three relevant decisions, links them to the project card, and adds follow-up tasks to your work list. Nothing gets lost in an email thread.

---

## Quick Start

**Prerequisites:** Windows with WSL, Python 3.10+, a Claude account (Pro recommended)

### Option 1 — Installer (recommended, no technical knowledge required)

```
1. Download or clone this repository
2. Open the folder
3. Double-click:  system/installer/install.bat
```

The installer handles everything:
- Installs the Python environment
- Registers Metis with Claude Code and Claude Desktop
- Creates a Desktop shortcut and Start Menu entry
- Guides you through first-time configuration

Restart Claude Desktop and Claude Code after installation.

### Option 2 — Manual (WSL terminal)

```bash
# Clone
git clone https://github.com/SVerITG/metis.git
cd metis

# Install MCP server + auto-register with Claude Code and Claude Desktop
bash system/mcp-server/setup-mcp.sh

# Personalise (follow the guided wizard)
# Open Claude Code in the metis/ folder, then run:
/metis_config
```

### After installation

1. Run `/metis_config` in Claude Code (or Claude Desktop after restart) for the 13-section setup wizard
2. Connect your reference library: `/metis-library-setup`
3. Open the dashboard: double-click **Metis** on your Desktop
4. Set your research focus for the week in the Planner tab
5. Let Metis run its first morning scan

From then on: use `/metis [any request]` from Claude Code or Claude Desktop. Metis routes it to the right agent, does the work, and logs the result.

---

## Personalising Metis

See [PERSONALIZE.md](PERSONALIZE.md) for a complete guide. The short version:

- **Your domain and research area** — set in `/metis_config`
- **Your literature** — connect via `/metis-library-setup`
- **Your news topics and RSS feeds** — set in `/metis_config` under "news"
- **Your projects** — add via the Work tab or Claude Code
- **Your agent team** — activate/deactivate agents in `/metis_config`
- **Your writing style** — the Writing Partner learns from feedback over time

Everything personal (your notes, ideas, outputs, project files) is stored locally and excluded from git by default. System improvements push to GitHub; your research stays private.

---

## Agent Team

| Agent | Role |
|-------|------|
| **Metis** | Orchestrator — routes requests, coordinates agents, maintains context across the session |
| **Librarian** | Manages your literature library, searches papers, tracks new publications |
| **PhD Architect** | Maintains thesis structure, tracks article alignment, surfaces gaps |
| **Research Architect** | Tracks article progress, reviews drafts against the research plan |
| **Writing Partner** | Drafts, edits, and improves written work — calibrated to your style over time |
| **Methods Coach** | Epidemiological methods, statistics, sampling, R methodology |
| **Epidemiologist** | Study design review, Socratic methodology challenge, peer-review simulation |
| **Presentation Maker** | Builds slide decks from your content and agent outputs |
| **Frontend Designer** | Design system, UI/UX standards, CSS, dashboard interface |
| **RC Builder** | Builds and extends Metis itself — new agents, tools, MCP server features |
| **Course Builder** 🔬 | Orchestrator for course-building: intake → curriculum → lessons → assessment. Prompt and 7-step workflow are in place; end-to-end automated pipeline is in active development |
| **Learning Architect** | Curriculum design, competency maps, spaced repetition scheduling |
| **News Radar** | Compiles daily briefing on your topics and field |
| **News Aggregator** | Automated RSS collection, feed curation, signal tagging |
| **Meeting Memory** 🟡 | Transcribes meetings; structured action-item extraction and project cross-linking are in progress |
| **Learning Coach** | Tracks skill progress, surfaces what to review, identifies gaps |
| **Career Coach** | Career direction, job preparation, CV development |
| **Content Harvester** | Extracts and structures content from web pages, PDFs, YouTube, GitHub |
| **Visualization Maker** | Charts, diagrams, system maps, ggplot2 and Plotly figures |
| **Data Analyst** | Profiles, cleans, and compares tabular datasets — local only, no upload |
| **Data Guardian** | Intercepts before any sensitive content leaves your machine — silent, always active |
| **Cybersecurity** | Validates internet-facing actions, defends against prompt injection |
| **Software Engineer** | Code review, debugging, R and Python scripts, FastAPI |
| **Design Auditor** | Audits existing UIs, reverse-engineers design decisions, prioritises improvements |

All agents are plain Markdown files in `agents/`. You can read, edit, or extend any agent's skill file from the dashboard — no code required.

---

## Data Protection

Every piece of content that passes through Metis is classified before any external action is taken.

| Classification | What it covers | What happens |
|---------------|---------------|--------------|
| **SENSITIVE** | Patient/individual records, medical data, GPS coordinates of cases | **BLOCKED** — never reaches the API under any circumstances |
| **CONFIDENTIAL** | Unpublished work, personal files, original drafts | **WARN + confirm** — you must approve before anything leaves your machine |
| **INTERNAL** | Code, metadata, aggregated outputs | **INFORM** once, then proceed |
| **PUBLIC** | Published papers, public datasets, public URLs | OK — free to use |

```
You → Metis → Data Guardian → [BLOCKED | WARN | INFORM | OK] → API
```

The Data Guardian runs 14 PII checks: 5 regex patterns covering email addresses, phone numbers, patient/case IDs, high-precision GPS coordinates, and Belgian national IDs; plus 9 sensitive column-name signals (`patient`, `patient_id`, `case_id`, `diagnosis`, `dob`, `date_of_birth`, `test_result`, `gps_lat`, `gps_lon`). Detection is automatic and silent. You do not need to tag or label your files. The pattern set is conservative — extend it for your domain in `metis/system/mcp-server/src/metis_mcp/tools/safety.py`.

**What this means in practice:**
- Drop a CSV with patient-level data into Metis → the Data Guardian blocks it from reaching the API
- Ask Metis to review your thesis draft → it warns you that the text will pass through the Claude API and asks for your confirmation first
- Run an analysis on aggregated statistics → proceeds without interruption

Claude's API does not use your data for model training. But data is retained on Anthropic servers for 30 days for safety monitoring. The Data Guardian ensures you are informed about this the first time it applies, so you can make an informed choice about what to send.

See `system/config/red-lines.md` for the full data policy.

---

## Constitution and red lines — the rules every agent obeys

Metis is governed by an explicit, machine-readable policy. Two files anchor it:

- **`system/config/constitution.md`** — 12 rules, loaded into every agent's context for `deep` and `chain` complexity runs. The rules cover **clinical safety** (cite at least one primary source for any clinical recommendation; flag limited-evidence claims), **statistical integrity** (state sample size; never imply causation from observational data outside an RCT), **data protection** (block patient-identifying output; redact secrets), **agent behaviour** (write a reflexion after deep runs; flag uncertainty explicitly; never fabricate items in lists), **routing & escalation** (ask one clarifying question if the routing is genuinely ambiguous; validate sub-agent output before passing it on), **research integrity** (full citations; no predatory journals), and **PhD protection** (any change to a thesis article must check thesis-backbone alignment first).

- **`system/config/red-lines.md`** — five non-overridable rules: never send patient/medical data externally; always confirm before destructive actions; log every agent run; ask when in doubt; never leak personal or unpublished work without explicit approval.

These are not suggestions. They are loaded as system context before every substantive run, and the most critical rules (no patient data, no API keys in output) are enforced at the code level by the Data Guardian and the pre-tool-use hook — agents cannot override them by reasoning their way around the rule.

You can read both files. You can edit them. The change applies to every agent on the next run.

---

## Working within your context

A senior epidemiologist asks Metis a methodology question and gets an answer calibrated to epidemiology. A researcher building dashboards asks the same question framed as a UI problem and gets an answer for that. Same Metis. Different context.

This is configured in `system/config/user-config.yaml`:

- **`general_context`** — your one-paragraph bio. Loaded into every agent run. The Methods Coach knows you're an epidemiologist; the Writing Partner knows your target journals; the Librarian knows your domain vocabulary.
- **`specialist_contexts`** — additional contexts you can activate when working on a specific area. *"Epidemiological dashboard development"* is a specialist context the user activates when working on a Shiny app, but not when reviewing an article draft. The Builder loads it; the Writing Partner does not.
- **`active_contexts`** — which contexts apply right now. Switchable at any time.

Each agent folder also accepts **`*-context.md` overlay files** (gitignored) where you can add domain-specific knowledge — your disease focus, your country surveillance system, your standard methods, your cohort. The agent loads any matching overlay automatically.

Add or update contexts via `/add-context` from Claude Code, or directly in `/metis_config`.

---

## Cybersecurity

Metis operates agentically — agents browse the web, process RSS feeds, and handle external content. Every external boundary has an active defence.

| Layer | Threat | Defence |
|-------|--------|---------|
| **URL allowlist** | Agents fetching from malicious domains | Only Librarian, News Radar, and News Aggregator have internet access. Every URL is validated against a domain allowlist before any request is made |
| **Injection probe** | RSS feeds or web pages containing hidden instructions to hijack agent behaviour | External content is scanned for **13 prompt injection patterns** plus zero-width Unicode characters. The same 13-pattern list is enforced both server-side (`tools/guardrails.py`) and in the Claude Code pre-tool-use hook (`.claude/hooks/pre-tool-use.mjs`) — the lists are kept in sync. Suspicious content is annotated and flagged, not silently dropped |
| **Agent scope enforcement** | Agents taking actions outside their defined role | Each agent declares its permitted actions. The Cybersecurity agent audits outputs for scope violations before execution |
| **File integrity** | Imported files containing embedded instructions or encoding anomalies | Files are checked before processing |
| **Security event log** | Undetected incidents | All security events are logged in the dashboard for review |

The Cybersecurity agent itself has no internet access, preventing it from becoming an attack vector.

---

## Self-Improving Agents

Agents do not stay static. They improve over time through a **bounded Reflexion loop**:

1. After completing a task, the agent writes a brief self-critique: what worked, what did not, what it would do differently
2. When you flag an issue (incorrect output, wrong tone, missed nuance), the agent reads its own skill file and the failed output, then proposes a specific, concrete change to its instructions
3. That proposal appears in the queue in the dashboard — you review it, approve or reject it
4. Approved proposals are applied to the agent's skill file immediately

**No agent can rewrite itself without your approval.** The loop is bounded: agents can reflect and propose, but humans decide.

Over time, this has two effects:
- **Quality** — agents become more accurate for tasks in your domain
- **Personalisation** — agents calibrate to your standards, your terminology, your expectations

---

## Token Efficiency

| Model | When Metis routes to it | Examples |
|-------|------------------------|---------|
| Haiku | Triage, formatting, classification, quick retrieval | News Radar, Meeting Memory, Data Guardian |
| Sonnet | Standard analysis, writing, routing | Metis orchestrator, Librarian, Writing Partner |
| Opus | Deep analysis, architecture, complex code | Software Engineer, RC Builder |

A token pulse widget in the dashboard shows real-time usage. When a session approaches its context limit, Metis generates a handoff brief automatically — a portable document summarising exactly where you are and what comes next — so you can continue seamlessly in a new session.

---

## Architecture

```
metis/
├── inbox/             Drop anything here — Librarian processes it
├── agents/            Agent team — one skill.md per agent (plain Markdown)
├── knowledge/         Your knowledge: literature, domains, courses
├── projects/          Your projects with status, tasks, linked papers
├── outputs/           Agent outputs — YYYY-MM-DD_task.md per run
├── system/
│   ├── app-py/        FastAPI + HTMX dashboard (9 tabs, local, port 8000)
│   ├── mcp-server/    Python MCP server (120 tools)
│   ├── config/        Guardrails, constitution, red-lines, token policy
│   └── .env           Your API keys — never committed to git
├── .claude/
│   ├── skills/        54 slash commands (/metis, /librarian, /methods-coach, /metis_doctor, …)
│   ├── hooks/         Pre-tool-use security hook (path patterns, injection guard)
│   └── CLAUDE.md      Agent routing guide (loaded by Claude Code automatically)
└── PERSONALIZE.md     How to make Metis yours
```

---

## Contributing

Metis is open-source and built to grow with the research community. Contributions are welcome:

- **New agents** — if you work in a field that needs a specialist (ecology, economics, qualitative methods, genomics), add one
- **New MCP tools** — extend the server with new capabilities
- **Bug reports** — open an issue with as much detail as possible
- **Workflow descriptions** — share how you use Metis; the best ideas come from actual research workflows
- **Design feedback** — the dashboard is designed for researchers, and researchers know best what they need

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and the personal↔public sync strategy.

---

## License

MIT — see `LICENSE`.

Built for researchers, by a researcher.
