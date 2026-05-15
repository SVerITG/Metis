<p align="center">
  <img src="system/app-py/static/metis-compass.svg" width="80" alt="Metis"/>
  <br/><br/>
  <img src="system/app-py/static/metis-wordmark.svg" width="220" alt="Metis"/>
  <br/>
  <sub><b>The Research Cortex — Public Health Edition</b></sub>
</p>

<h1 align="center">A local research companion for Claude.</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square" alt="Python"/>
  <img src="https://img.shields.io/badge/MCP-compatible-green?style=flat-square" alt="MCP"/>
  <img src="https://img.shields.io/badge/Claude-powered-orange?style=flat-square" alt="Claude"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="MIT"/>
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" alt="Active"/>
  <img src="https://img.shields.io/badge/edition-public--health-teal?style=flat-square" alt="Public Health"/>
</p>

---

> **Public Health Edition.** This repository is based on [SVerITG/Metis](https://github.com/SVerITG/Metis) and comes with a pre-built knowledge layer for public health researchers: WHO guidelines, NTD surveillance frameworks, epidemiological methods references, global health policy documents, and MPH/GH curriculum materials — indexed and ready to search. If you work in global health, epidemiology, or public health, this is the recommended starting point. If you want the empty base to build your own domain layer, start with [SVerITG/Metis](https://github.com/SVerITG/Metis) instead.

---

Every time you ask Claude a question about your work, you start from scratch. Metis fixes that. It runs on your own computer, holds your literature, meetings, ideas, and projects in one place, and hands the right pieces to Claude whenever you ask a question — so the answer is grounded in *your* research, not a generic one.

**In one sentence:** drop your papers, notes, and meeting transcripts into Metis, ask Claude anything from the dashboard or directly in Claude Code, and get answers shaped by what you already know and are working on.

### What you actually get

- A **local dashboard** with nine tabs — Today, Knowledge, Meetings, Learning, Work, Thinking, Planner, Teach, Metis — running at `http://127.0.0.1:8000`. No login. No cloud.
- A **morning brief**, generated daily by Claude from your RSS feeds and recent papers, calibrated to your stated topics and projects.
- A **quick-capture box** (Ctrl+K from anywhere on the dashboard, or a mobile-friendly `/capture` page on your phone). Type `i:` for idea, `t:` for task, `n:` for note, `q:` for question — it routes to the right place and immediately surfaces related items you already had.
- A **library** that imports from Zotero, BibTeX, or a folder of PDFs, and lets you search across abstracts, full text, and semantic similarity.
- **Twenty-something specialist agents** — a Librarian, an Epidemiologist, a Methods Coach, a Writing Partner, a Data Guardian, and so on — that you can invoke by name (`/librarian`, `/epidemiologist`) or leave to the orchestrator (`/metis`) to route for you.
- A **Data Guardian** that scans content for patient IDs, GPS coordinates, sensitive column names, and national IDs before anything is sent to the Claude API, and refuses to send what it shouldn't.

### What comes pre-loaded in this edition

The Public Health Edition includes a background knowledge layer built from publicly available sources:

| Domain | What is indexed |
|--------|----------------|
| **NTD surveillance** | WHO NTD roadmap, HAT/sleeping sickness elimination frameworks, lymphatic filariasis surveillance guides |
| **Epidemiological methods** | STROBE, CONSORT, PRISMA checklists; diagnostic test accuracy frameworks; multilevel modelling references |
| **Global health policy** | WHO global health targets, Sustainable Development Goals health indicators, GPEI frameworks |
| **Health information systems** | DHIS2 documentation, HMIS design guides, OpenMRS and FHIR references |
| **MPH/GH curriculum** | Core competency frameworks for Masters in Public Health and Global Health programmes |

This layer is searchable via the Knowledge tab, enriches every morning brief in the relevant domains, and is available to all agents as background context — without requiring you to load any PDFs yourself.

### What you need to run it

- **Windows 10/11 with WSL, macOS, or Linux.** A `.exe` installer is in active testing for Windows; on macOS and Linux you run a bash script.
- **Python 3.10 or newer.** The installer can fetch it for you on Windows.
- **An Anthropic API key**, or a Claude Pro/Max subscription with Claude Code. The agents call Claude — Metis itself is free and local.
- **About 30 minutes** for the first install and guided setup wizard. Less if you skip seeding the library.

### Honest about where it is

The author uses Metis daily for real research in epidemiology and global health. Several pieces are still maturing — the Windows installer needs a clean-machine test, the Teach tab's slide and assessment buttons are stubs, the mobile PWA does not yet cache offline, and a few agents (Course Builder, Meeting Memory live mode) are marked as in progress in the table below. The core daily loop — morning brief, capture, library search, agent routing, data protection — works. If you try it and something breaks or feels off, open an issue. Researcher feedback shapes this more than developer feedback ever could.

Contributions are very much appreciated — see [Contributing](#contributing) below. Whether you want to share how a feature worked (or didn't) in your research workflow, or you are a more experienced developer who sees something to improve in the architecture or code: both perspectives matter equally here.

### Quick look

1. Install — [Option 1 installer](#quick-start) on Windows, or `bash system/mcp-server/setup-mcp.sh` on macOS/Linux.
2. Run `/metis_config` in Claude Code. The 13-section wizard takes ~10 minutes.
3. Drop your reference library (Zotero export or PDFs) into `inbox/`. Connect Zotero with `/metis-library-setup` if you use it.
4. Open the dashboard. Read the morning brief. Press Ctrl+K and capture your first idea.

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

Meeting Memory structures the transcript, extracts action items and decisions, and cross-references the discussion with your literature and open projects.

### Local data analyst — profile and clean datasets without uploading them

The Data Analyst agent profiles, cleans, and compares tabular datasets entirely on your machine — CSV, Excel, SPSS, Stata. Returns a full structured profile (shape, dtypes, null %, unique counts, distributions, top categorical values), suggests cleaning operations with rationale, applies them to a new file (the original is never modified), and diffs the before/after profiles.

Critically: **no dataset path is ever URL-based, and column names are scanned against the PII pattern list before profiling**. Sensitive columns are surfaced before any analysis touches them.

### Knowledge graph

The Knowledge tab renders a force-directed graph (D3) of your library, ideas, and projects. Edges show co-occurrence, citation links, and cross-pollination matches.

### Semantic memory search

Beyond keyword search, Metis indexes your literature, notes, ideas, and meeting transcripts as 384-dim vectors using `sqlite-vec` and BAAI's `bge-small-en` embedding model. The search bar in the Knowledge tab returns semantic matches. Embeddings are computed and stored locally — nothing is sent to a remote vector service.

### Encrypted backup and export

A single MCP tool (`backup_db`) writes an AES-256-GCM encrypted snapshot of the entire Metis database to disk on demand.

### Project tracking with one-click launchers

Each project in the Work tab has a card with status, next-step note, linked papers, linked outputs, and a launcher rail. One click opens the project in **VS Code**, **RStudio**, **Claude Code**, **Claude Desktop**, **File Explorer**, or directly to its **GitHub** page.

### Health check — `/metis_doctor`

A one-screen self-test that verifies Python version, the SQLite database, your Anthropic API key, your `user-config.yaml`, agent and skill folders, folder-rename hygiene, MCP imports, and `.env` git safety.

### Continuity across your research

Research projects span years. Metis tracks the full arc: project cards, article drafts, agent review history, session handoffs.

### Morning briefing

Every morning, the News Radar compiles a briefing calibrated to your field and current projects: new publications, relevant news, preprint activity, funding announcements.

### Full data protection — nothing leaves without your permission

Every piece of content that passes through Metis is classified before any external action is taken. Patient data is blocked unconditionally. Unpublished manuscripts require your explicit confirmation.

### Efficient token use

Each task is routed to the smallest model capable of handling it (Haiku → Sonnet → Opus). A token pulse in the dashboard shows usage in real time. A handoff brief is generated when a session approaches its context limit.

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
git clone https://github.com/SVerITG/Metis_PH.git
cd Metis_PH

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

---

## Agent Team

| Agent | Role |
|-------|------|
| **Metis** | Orchestrator — routes requests, coordinates agents, maintains context across the session |
| **Librarian** | Manages your literature library, searches papers, tracks new publications |
| **PhD Architect** | Maintains thesis structure, tracks article alignment, surfaces gaps |
| **Writing Partner** | Drafts, edits, and improves written work — calibrated to your style over time |
| **Methods Coach** | Epidemiological methods, statistics, sampling, R methodology |
| **Epidemiologist** | Study design review, Socratic methodology challenge, peer-review simulation |
| **Presentation Maker** | Builds slide decks from your content and agent outputs |
| **News Radar** | Compiles daily briefing on your topics and field |
| **Meeting Memory** 🟡 | Transcribes meetings; structured action-item extraction in progress |
| **Learning Coach** | Tracks skill progress, surfaces what to review, identifies gaps |
| **Data Analyst** | Profiles, cleans, and compares tabular datasets — local only, no upload |
| **Data Guardian** | Intercepts before any sensitive content leaves your machine — silent, always active |
| **Cybersecurity** | Validates internet-facing actions, defends against prompt injection |
| **Software Engineer** | Code review, debugging, R and Python scripts, FastAPI |

All agents are plain Markdown files in `agents/`. You can read, edit, or extend any agent's skill file — no code required.

---

## Data Protection

Every piece of content that passes through Metis is classified before any external action is taken.

| Classification | What it covers | What happens |
|---------------|---------------|--------------|
| **SENSITIVE** | Patient/individual records, medical data, GPS coordinates of cases | **BLOCKED** — never reaches the API under any circumstances |
| **CONFIDENTIAL** | Unpublished work, personal files, original drafts | **WARN + confirm** — you must approve before anything leaves your machine |
| **INTERNAL** | Code, metadata, aggregated outputs | **INFORM** once, then proceed |
| **PUBLIC** | Published papers, public datasets, public URLs | OK — free to use |

The Data Guardian runs 14 PII checks automatically. See `system/config/red-lines.md` for the full data policy.

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
