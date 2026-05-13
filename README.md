<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Metis_github.png"/>
    <img src="Metis_github.png" alt="Metis — Research Cortex" width="420"/>
  </picture>
</p>

<h1 align="center">Metis — The Research Cortex</h1>

<p align="center">
  <em>A gateway to AI for researchers. Not a tool — a way of working.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-under%20development-orange" alt="Under Development"/>
  <a href="https://github.com/SVerITG/Metis_pers/stargazers"><img src="https://img.shields.io/github/stars/SVerITG/Metis_pers?style=flat" alt="Stars"/></a>
  <a href="https://github.com/SVerITG/Metis_pers/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"/></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Claude-MCP-orange?logo=anthropic" alt="Claude MCP"/>
</p>

> **Work in progress.** The architecture and core features are stable and used daily. The one-click installer, Docker image, and polished onboarding are not yet complete. Expect rough edges.

---

## The idea behind Metis

Metis was built by a senior public health researcher with no technical background — and that is the whole point.

AI has advanced faster than most researchers can follow. The gap between what it can do and what a typical researcher actually gets from it is large — not because the tools are bad, but because using them well still requires a level of technical fluency that most researchers don't have, and shouldn't need to develop. Researchers are not software engineers.

**Metis is an exploration of what AI looks like when it is built around a research profile.** It is a working answer to the question: what does genuine AI support look like for a researcher who works with literature, data, ethics, and ideas over a multi-year timescale — and who wants it to work without technical setup?

The current version serves one researcher. The longer vision: **a research institute deploying its own Metis** — an AI layer tuned to the institute's literature, data systems, and ongoing projects, available to every staff member from day one.

---

## Table of Contents

- [For Researchers](#for-researchers) — what it is, what you get, how to install
- [For Developers](#for-developers) — architecture, stack, installation, configuration
- [Future Releases](#future-releases) — planned domain packs and edition structure
- [Contributing](#contributing) — how to add domains, agents, and skills
- [License](#license)

---

# For Researchers

*No technical knowledge required to read this section.*

---

## What is Metis?

Every AI conversation starts from zero. The tool doesn't know your research, your papers, your ongoing projects, or what you were thinking about last week. You spend ten minutes re-explaining your context — and when the session ends, it's gone.

Metis builds a **research cortex** — a persistent, connected layer underneath every AI conversation. It knows your literature, your ideas, your meetings, and your projects. When you ask a question, the answer comes in the context of everything you're actually working on.

You talk to Metis the way you'd talk to a brilliant colleague. It routes your question to the right specialist, does the work, records the result, and comes back with a plain answer. No prompts. No settings. No manual.

---

## What you get on day one

| Feature | What it does |
|---|---|
| **30 specialist agents** | Librarian, Epidemiologist, Writing Partner, Methods Coach, Meeting Memory, Course Builder, PhD Architect, Career Coach, and 22 others |
| **135 MCP tools** | Literature search, idea capture, meeting notes, PDF semantic search, data analysis, cross-pollination, knowledge graph, and more |
| **9-tab dashboard** | Runs locally in your browser. Today · Knowledge · Meetings · Learning · Work · Thinking · Planner · Teach · Metis |
| **Morning briefing** | Every day: new papers on your topics, WHO/surveillance updates, tasks due, a focus suggestion |
| **Identity that grows** | Metis builds a profile of you — your domain, interests, thinking style, active projects — and uses it to personalise every response |
| **Config wizard** | A 13-section guided setup that lets you configure your domain, research interests, news monitoring topics, and agent preferences — no files to edit |
| **Cross-pollination** | When you capture an idea, Metis automatically surfaces connections to your existing papers, past ideas, and meeting notes |
| **Semantic PDF search** | PaperQA2 indexes your entire PDF library and answers questions with citations — "what do my papers say about X?" |
| **Zotero / Mendeley sync** | Import your existing reference library on day one |
| **Self-improvement loop** | Every two weeks, Metis reviews its own performance, proposes changes to its own agents, and waits for your approval before applying them |
| **Local and private** | Everything runs on your machine. Your data never leaves. |

---

## How Metis knows you

When you first run Metis, the **config wizard** walks you through 13 topics: your research domain, specific interests, active projects, thinking style, news monitoring preferences, PhD or article status, and more. This creates your **identity card** — a living profile that Metis reads at the start of every task.

Over time, the identity card grows. Every agent run adds context. Every idea you capture tells Metis something about what you're thinking about. Reflexions after each task feed a self-improvement loop that shapes how agents respond to you specifically.

The result is that a question you ask six months into using Metis gets a much better answer than the same question on day one — not because the AI changed, but because Metis knows you better.

---

## The dashboard

<table>
<tr><td><strong>Today</strong></td><td>Morning briefing, overnight papers, task priorities, focus thread, news rail</td></tr>
<tr><td><strong>Knowledge</strong></td><td>PDF library, literature cards, domain notes, knowledge graph</td></tr>
<tr><td><strong>Meetings</strong></td><td>Structured notes with action items; import from Zoom/Teams transcript</td></tr>
<tr><td><strong>Learning</strong></td><td>Courses you're building or taking, spaced repetition, competency map</td></tr>
<tr><td><strong>Work</strong></td><td>Tasks and projects — open VS Code / RStudio / Claude with one click</td></tr>
<tr><td><strong>Thinking</strong></td><td>Ideas, notes, open questions, brainstorm launcher</td></tr>
<tr><td><strong>Planner</strong></td><td>Kanban board, PhD focus board, timeline</td></tr>
<tr><td><strong>Teach</strong></td><td>Courses you teach — literature alerts, course builder, assessment tools</td></tr>
<tr><td><strong>Metis</strong></td><td>Agent run history, self-improvement proposals, system health</td></tr>
</table>

---

## Who uses Metis

**The public health researcher**
Opens their computer in the morning. The dashboard shows a paragraph: two papers arrived overnight on their topic, one connects to their methodology question, WHO flagged a surveillance update. Their most urgent task is highlighted. An idea they captured last week has been connected to a paper from six months ago.

**The PhD student**
Three articles in progress that need to connect to a thesis backbone. Metis tracks all three simultaneously, flags when a new paper changes the argument, suggests where to focus this week, and remembers what the supervisor said in the last meeting.

**Any researcher (coming soon)**
The current version ships with a Public Health & Epidemiology domain pack. Domain packs for other fields are in development — see [Future Releases](#future-releases).

---

## Install

> **v1.0 (coming):** A `.exe` installer — download, double-click, done. Until then:

### Prerequisites (install once)

1. **WSL** — open PowerShell as Administrator, run `wsl --install`, restart
2. **Claude Desktop** ([claude.ai/download](https://claude.ai/download)) or Claude Code
3. **Anthropic API key** — from [console.anthropic.com](https://console.anthropic.com)

### Light install — AI assistant only (5 minutes)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SVerITG/Metis_pers/main/metis/system/mcp-server/setup-mcp.sh)
```

Gives you all 30 agents and 135 tools inside Claude Desktop or Claude Code. No dashboard.

### Full install — dashboard + assistant + automation

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SVerITG/Metis_pers/main/metis/system/mcp-server/setup-mcp.sh)
cd ~/Metis_pers/metis/system/app-py && bash run.sh
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Run the config wizard from the Metis tab.

---

# Future Releases

Metis will ship in distinct editions, each with its own GitHub repository:

| Edition | Status | What it is |
|---|---|---|
| **Metis Public Health & Epidemiology** | Current (v0.x) | This repository — fully working, used daily, rough edges |
| **Metis Public Health & Epidemiology v1.0** | In development | Stable installer, polished onboarding, complete domain pack |
| **Metis Empty Research Cortex** | Planned | Bare-bones framework — no domain pack, build your own |
| **Metis [Domain]** | Community | Domain packs as they are contributed |
| **Metis Institute Edition** | Future | Multi-user, shared knowledge base, institutional deployment |

The **Empty Research Cortex** is for developers and institutions who want to build their own domain pack from scratch. It ships the full architecture (MCP server, dashboard, agents, self-improvement loop) with no domain-specific content loaded.

Each domain edition includes pre-configured journals, RSS feeds, specialist agents, an ontology, and a curated knowledge library for that field.

---

# For Developers

*This section assumes familiarity with Python, Git, and the command line.*

---

## Architecture

```mermaid
flowchart LR
    U([Researcher])
    subgraph Harness["AI Harness (Claude Code / Desktop)"]
        METIS[Metis\nrouter agent]
        AGENTS[Specialist agents\n30 agents]
        WATCHERS{{Watchers\nData Guardian\nCybersecurity}}
    end
    subgraph Platform
        MCP[MCP Server\n135 tools\nFastMCP]
        DASH[Dashboard\nFastAPI + HTMX]
        DB[(SQLite\nWAL mode)]
    end
    subgraph Memory
        EPIS[Episodic]
        SEM[Semantic\nvector search]
        REFLEX[Reflexion log]
    end
    Skills[/CLI Skills\n/metis · /librarian · …/]

    U -->|asks| METIS
    U -->|clicks| DASH
    METIS -->|routes to| AGENTS
    AGENTS -->|uses| MCP
    MCP --- DB
    DASH --- DB
    WATCHERS -.guards.-> AGENTS
    AGENTS -->|writes| REFLEX
    REFLEX -->|proposes edits to| AGENTS
    MCP --- Memory
    Skills --> METIS

    style WATCHERS fill:#fff4e6,stroke:#9a7b3c
    style REFLEX fill:#eef4f1,stroke:#2d4a3a,stroke-dasharray:3 3
```

---

## Stack

| Layer | Technology |
|---|---|
| AI harness | Claude Code, Claude Desktop (primary); Gemini (experimental) |
| MCP server | Python 3.10+, FastMCP, runs in WSL venv |
| Dashboard | FastAPI + HTMX + Jinja2, no JavaScript framework |
| Database | SQLite WAL mode, 46 tables |
| Vector memory | sqlite-vec + nomic-embed-text-v1.5-Q (768 dims, local ONNX) |
| Semantic PDF search | PaperQA2 (FutureHouse) — indexes PDF library, answers with citations |
| Host OS | Windows + WSL2 (Ubuntu 20/22/24) |
| File sync | OneDrive / Dropbox (optional, transparent) |

---

## Under the hood

**Memory (5 layers)**

| Layer | What it stores |
|---|---|
| Episodic | Session events and observations (discovery · decision · implementation · issue) |
| Semantic | Vector-indexed content (sqlite-vec + nomic-embed-text-v1.5-Q, 768 dims) |
| Procedural | Skill files and agent contracts — the agent's persistent behaviour |
| Working | Active session context and current project focus |
| Reflexive | Reflexion log and improvement proposals |

**Self-improvement loop**
1. After every deep run: `write_reflexion()` logs what went well, what could improve, what was missing
2. Weekly: `aggregate_reflexions()` extracts themes via Claude Haiku
3. `draft_self_improvement_proposal()` writes a proposed `skill.md` edit with rationale
4. You review in the Metis tab → `apply_proposal()` writes to disk with timestamped backup

**Security layers**
1. `pre-tool-use.mjs` — 12 injection patterns, domain allowlist, path restrictions (every tool call)
2. `guardrails.py` — injection probe on all external content (same patterns)
3. `safety.py` — 14 PII checks, 4-level classification, hard block on sensitive data
4. `constitution.md` — 12 machine-readable rules for deep/chain runs
5. `red-lines.md` — 5 non-overridable rules enforced at code level

**Token efficiency**
- Model routing: Haiku for summaries, Sonnet for most work, Opus for deep reasoning
- Surgical context assembly per agent — not full history on every call
- Max-turns guardrail (stops at 20, prompts `/clear`)
- Handoff brief at session end (< 3 KB, state capture for next session)

---

## Installation options

### Option 1 — Single command

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SVerITG/Metis_pers/main/metis/system/mcp-server/setup-mcp.sh)
```

Detects Ubuntu 20/22/24, creates venv, installs all dependencies, registers with Claude Code and Claude Desktop. Idempotent.

### Option 2 — Manual

```bash
git clone https://github.com/SVerITG/Metis_pers.git
cd Metis_pers/metis/system/mcp-server && bash setup-mcp.sh
cd ../app-py && bash run.sh   # → http://127.0.0.1:8000
```

### Option 3 — Docker (planned for v1.0)

```bash
docker run -p 8000:8000 \
  -v /path/to/your/data:/metis/data \
  -e METIS_RC_ROOT=/metis \
  ghcr.io/sveritg/metis:latest
```

### Option 4 — Windows .exe installer (planned for v1.0)

No terminal needed. Download, double-click, answer configuration questions.

---

## Register with Claude Code

`~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "/home/<username>/.local/share/metis-mcp/run.sh"
    }
  }
}
```

## Register with Claude Desktop (Windows + WSL)

`%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "wsl.exe",
      "args": ["-e", "bash", "/home/<username>/.local/share/metis-mcp/run.sh"]
    }
  }
}
```

---

## Configuration

All configuration is file-based.

| File | Controls |
|---|---|
| `system/config/user-config.yaml` | Domain, interests, thinking style, preferences — generated by config wizard |
| `system/config/constitution.md` | 12 rules applied to every deep/chain agent run |
| `system/config/red-lines.md` | 5 non-overridable rules (sensitive data, API keys, etc.) |
| `system/config/token-guardrails.md` | Model routing per agent, handoff thresholds |
| `agents/<name>/skill.md` | Behavioural contract for each agent — directly editable |
| `.claude/hooks/pre-tool-use.mjs` | Security gate on all tool calls |

---

## Dependencies

**Python packages (auto-installed):**

| Package | Purpose |
|---|---|
| `mcp`, `fastmcp` | MCP protocol |
| `fastapi`, `uvicorn`, `starlette` | Dashboard |
| `sqlite-vec` | Local vector search |
| `fastembed` | nomic-embed-text-v1.5-Q embeddings (768 dims, ONNX) |
| `paper-qa` | PaperQA2 semantic PDF search |
| `feedparser` | RSS feed parsing |
| `pyyaml` | User config |
| `httpx` | Async HTTP |
| `pandas`, `openpyxl`, `pyreadstat` | Data analyst (CSV/Excel/SPSS/Stata) |
| `cryptography` | AES-256-GCM backup encryption |
| `pyzotero` | Zotero sync |
| `bibtexparser` | Mendeley BibTeX import |
| `twilio` | WhatsApp capture webhook (optional) |

**External tools:**

| Tool | Required for |
|---|---|
| WSL + Ubuntu | Everything on Windows |
| Claude Desktop or Claude Code | AI harness |
| R + RStudio | R statistical analysis |
| Quarto | Course Builder (lesson rendering) |
| Zotero | Reference manager sync |
| Ollama (optional) | Local LLM for offline PII screening |

---

## Cross-AI / harness support

| Harness | Status |
|---|---|
| Claude Code | ✅ Primary — full support (MCP + skills + hooks) |
| Claude Desktop | ✅ Primary — full MCP + memory; no CLI skills |
| Gemini 2.0+ | 🔬 Experimental |
| OpenAI Codex / Cursor | 🟡 Partial — MCP tools only |

---

## Project status

**Completed:** Phases 0–9b — foundations · 9-tab dashboard · 30 agents · CLI skills · 5-layer memory · knowledge graph · self-improvement loop · token efficiency · Zotero/Mendeley · meeting assistant · PaperQA2 PDF search · cross-pollination

**In progress:** Phase 10 (automated daily tasks), Phase 11 (.exe installer), Phase 12 (test suite)

---

# Contributing

Metis is designed to grow beyond one researcher and one domain. Contributions are welcome.

Most wanted:

- **Domain backgrounds** — knowledge packages for other research fields (see table below)
- **Agents and skills** — new specialists or improved behavioural contracts
- **Hooks** — security, automation, workflow improvements
- **Infrastructure** — installer improvements, Docker, platform support

See [CONTRIBUTING.md](metis/CONTRIBUTING.md) for guidelines.

---

## Domain backgrounds (most wanted)

A domain background consists of: key journals + RSS feeds, specialist agents or skill overlays, a domain ontology, and PubMed/OpenAlex query templates.

| Domain | Status |
|---|---|
| **Public Health & Epidemiology** | ✅ Included |
| Social Sciences | 🔬 Planned |
| Biomedical Sciences / Clinical Research | 🔬 Planned |
| Economics and Development Economics | 🔬 Planned |
| Environmental Science and Climate | 🔬 Planned |
| Psychology and Behavioral Sciences | 🔬 Planned |
| Law and Policy | 🔬 Planned |
| Education Research | 🔬 Planned |
| Nursing and Allied Health | 🔬 Planned |

---

## Infrastructure contributions

- ~~nomic-embed-text-v1.5-Q cross-pollination~~ ✅ Done
- ~~PaperQA2 semantic PDF search~~ ✅ Done
- ~~Mobile PWA capture page~~ ✅ Done
- ~~Domain-specific tool loading~~ ✅ Done (`METIS_AGENT_SUBSET`)
- Telegram bot for mobile idea capture — wanted
- Test suite (unit + integration + e2e) — wanted
- Windows `.exe` installer — in progress

---

## The vision

A research institute or department deploying Metis for their entire team — a shared AI infrastructure tuned to the institute's literature, data systems, and ongoing projects. Every researcher gets a pre-configured Metis on day one. Shared literature collections, internal database connections, and house style are built into the system prompt layer. The constitution and red-lines were designed with institutional patient data in mind.

If you are exploring this: the MCP architecture and skill/agent model are built for institutional deployment. We welcome conversations about adapting Metis for your department.

---

# License

MIT for the codebase. CC-BY-SA for course content and learning materials.

*LICENSE file ships with v1.0.*
