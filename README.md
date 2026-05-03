<p align="center">
  <img src="metis/system/app-py/static/metis-mark.svg" alt="Metis" width="140"/>
</p>

<h1 align="center">Metis — The Research Cortex</h1>

<p align="center">
  <em>A second brain, configured for AI. Built for researchers, not developers.</em>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#what-it-does">What it does</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#features">Features</a> ·
  <a href="#project-status">Status</a>
</p>

> **Status:** Actively used daily. Core features are stable. Packaging (installer, Docker) is in progress. Feedback on the concept and the user experience is very welcome — open an issue.

---

## The underlying idea

Not every researcher has the time to keep up with AI. Metis is a second brain configured for AI use — it places every question you ask an AI into the context of *your* research domain, your ideas, your notes, your literature, your projects, and your recent world.

Under the hood: a collection of specialist agents with safety guardrails that watch each other, a multi-layered memory that connects your thoughts with past work and recent developments, and a local-first dashboard that gives you one place to see what you're working on and what's new.

**The innovation is not in the components. It's in how the components interact with each other — and how you interact with them.**

---

## Quick start

Choose the installation method that fits you:

### Option 1 — Single command (recommended, WSL/Ubuntu)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SVerITG/Metis_pers/main/metis/system/mcp-server/setup-mcp.sh)
```

This detects your Python version (supports Ubuntu 20/22/24), creates a dedicated virtual environment, installs all dependencies, writes the MCP launcher script, and prints the registration lines to add to Claude Code and Claude Desktop.

### Option 2 — Manual (WSL/Ubuntu, Python 3.10+)

```bash
git clone git@github.com:SVerITG/Metis_pers.git
cd Metis_pers/metis/system/mcp-server
bash setup-mcp.sh            # creates ~/.local/share/metis-mcp/.venv
```

Then start the dashboard:

```bash
cd ../app-py
./run.sh                     # → http://127.0.0.1:8000
```

### Option 3 — Docker (coming soon)

```bash
docker run -p 8000:8000 \
  -v /path/to/your/data:/metis/data \
  -e METIS_RC_ROOT=/metis \
  ghcr.io/sveritg/metis:latest
```

> Docker image is not yet published. In progress for v1.0.

### Option 4 — Windows installer (coming soon)

A `.exe` installer that handles everything — Python, virtual environment, MCP registration, Windows shortcut. No terminal needed.

---

### Register with Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "/home/your-user/.local/share/metis-mcp/run.sh"
    }
  }
}
```

### Register with Claude Desktop (Windows + WSL)

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "wsl.exe",
      "args": ["-e", "bash", "/home/your-user/.local/share/metis-mcp/run.sh"]
    }
  }
}
```

> The `-e` flag always uses your default WSL distro, so it keeps working if you upgrade Ubuntu.

---

## What it does

Metis connects everything you're working on as a researcher into a single intelligent system:

| Tab | What you see |
|---|---|
| **Today** | Morning briefing — what's new, what needs attention, your current focus thread |
| **Knowledge** | Your library (cards, literature), domain notes, knowledge graph, memory search |
| **Meetings** | Meeting history with structured notes and follow-ups |
| **Learning** | Courses you're taking or building, spaced repetition, competency map |
| **Work** | Task list with priorities, active projects, open in VS Code / RStudio / Claude |
| **Thinking** | Ideas, notes, questions, brainstorm launcher |
| **Planner** | Kanban (someday → active), PhD focus board, timeline |
| **Teach** | Courses you teach — literature alerts, news signals, course build buttons |
| **Metis** | Agent runs, memory stream, self-improvement proposals, token usage |

---

## How it works

```mermaid
flowchart LR
    U([You\nresearcher])
    subgraph Platform
        DASH[Dashboard\nFastAPI + HTMX]
        MCP[MCP Server\n103 tools]
        DB[(SQLite\nlocal-first)]
    end
    subgraph Agents
        META[Metis\nrouter]
        WORK[Specialist agents\nLibrarian · Writing Partner\nMethods Coach · Epidemiologist\nCourse Builder · …]
        WATCH{{Watchers\nData Guardian\nCybersecurity}}
        LOOP[(Self-improvement\nreflexion log)]
    end
    Skills[/CLI Skills\n/metis_morning · /metis_handoff · …/]
    U -->|asks| META
    U -->|clicks| DASH
    DASH --> MCP
    META -->|routes to| WORK
    WORK -->|uses| MCP
    MCP --> DB
    WATCH -.watches.-> WORK
    WATCH -.watches.-> U
    WORK -->|writes to| LOOP
    LOOP -->|refines| WORK
    Skills --> META

    style U fill:#f5f2ea,stroke:#2d4a3a,stroke-width:2px
    style WATCH fill:#fff4e6,stroke:#9a7b3c
    style LOOP fill:#eef4f1,stroke:#2d4a3a,stroke-dasharray:3 3
    style DB fill:#f5f2ea,stroke:#555
```

*Your questions are routed by Metis to the right specialist agent. Every call passes under the Data Guardian (PII, data protection) and the Cybersecurity agent (prompt injection, URL validation). Agents read and write to shared local memory. A self-improvement loop captures what worked and what didn't so agents become more personalized with use.*

---

## How tokens are saved

Metis is designed to be expensive only when the work warrants it. Several layers work together:

| Layer | How it saves tokens |
|---|---|
| **Agent-specific models** | Haiku for quick tagging and summaries; Sonnet for most work; Opus for long reasoning and deep analysis |
| **Surgical context assembly** | Each agent receives only the context it needs — not the entire memory |
| **Observation classification** | Observations (discovery / decision / implementation / issue) are tagged and retrieved by type, not by dumping the whole log |
| **Progressive disclosure** | `get_context(budget_tokens=N)` returns index-level detail for small budgets, full content for large ones |
| **Token pulse** | Today tab shows today's token total with tier colours (green < 500k / ochre 500k–1M / red > 1M) |
| **Handoff brief** | At the end of a session, a compact briefing (< 3 KB) captures state so the next session starts without re-reading history |
| **Max-turns guardrail** | The pipeline stops at 20 turns and prompts you to `/clear` rather than letting context balloon silently |

---

## Features

- **Cross-pollination** between your ideas, literature, old notes, research, news, and meetings
- **Build your own courses** — the Course Builder Agent scrapes sources, designs curriculum with proven pedagogy (Bloom's taxonomy, spaced repetition), and publishes into your Learning tab
- **Full library organisation** with Zotero-style metadata and a force-directed knowledge graph (D3)
- **Idea capture** — Ctrl+K from anywhere on the dashboard, prefix-routed (`i:` idea · `n:` note · `t:` task · `q:` question)
- **Meeting assistant** that records, structures, and gives you feedback
- **Project tracking** — per-project PLANNING.md files, open in VS Code / RStudio / Claude from one click
- **Memory search** — semantic search across everything Metis has learned (sqlite-vec + fastembed)
- **Self-improvement loop** — agents write reflexions after every run; a themed aggregation proposes skill improvements for your approval
- **Data protection** — PII anonymisation, consent ledger, network policy controls
- **Backup and encryption** — AES-256-GCM encrypted database exports on demand

---

## Who it is for

Metis is designed for **researchers who want to use AI seriously without spending weeks setting it up**. The target user:

- Has a research domain (public health, law, economics, climate, education — anything)
- Uses Claude, ChatGPT, or similar tools but finds the sessions don't connect to each other
- Has papers, notes, and projects scattered across tools
- Is not necessarily technical — the installer handles Python, the dashboard handles the rest

You don't need to know what an MCP server is. You don't need to write prompts. You ask Metis and Metis routes.

---

## Claude Code vs. Claude Desktop

| | Claude Code (terminal) | Claude Desktop (app) |
|---|---|---|
| How to use Metis | `/metis your request` | Talk naturally — Claude calls the tools |
| Skills (slash commands) | `/metis_morning`, `/metis_brainstorm`, `/librarian`, … | Not available (CLI only) |
| Best for | Deep work sessions, coding, PhD writing | Quick captures, briefings, lookups |
| Both have access to | All 103 MCP tools, full memory, all agents | All 103 MCP tools, full memory, all agents |

### Making Metis the default in Claude Desktop (recommended for non-technical users)

Create a **Claude Desktop Project** and paste project instructions so every conversation
automatically routes through Metis — no command needed, no special syntax, just talk:

1. Open Claude Desktop → **Projects** → **New project**
2. Name it "Metis" and click **Add instructions**
3. Paste:

```
You are acting as Metis, a research intelligence system connected to my personal
knowledge base, task list, literature library, meeting notes, and research projects.

You have access to Metis tools (via MCP). For every question I ask:
- Use the Metis tools to pull relevant context before answering.
- Ground answers in what I have already captured, not just general knowledge.
- When I mention a paper, idea, task, or project, look it up in my library first.
- When I say something worth remembering, use capture_observation() to store it.
- When I finish a session, offer to run generate_handoff_brief().

My name is [your name]. I am a researcher working on [your field].
```

After this one-time setup, every message in the Metis project — including all follow-up
questions — is automatically handled in your research context. You never type "Metis" again.

The full instructions file is at `metis/system/config/claude-desktop-project-instructions.md`.

---

## Workflows

Three modes, all first-class:

1. **Dashboard-first morning** — open the dashboard, see what needs attention, click a launcher to jump into Claude Code / VS Code / RStudio with context already loaded.
2. **External → dashboard during work** — Claude Desktop or Claude Code with MCP tools writes to the Metis DB every tool call. The dashboard polls for updates.
3. **Files → dashboard via scan** — after editing externally, click "Scan now" on the dateline to re-check git status and file changes.

---

## Context configuration

Everything is configurable without code:

| File | What it controls |
|---|---|
| `system/config/constitution.md` | 12 hard rules that apply to every agent run (clinical safety, stats integrity, data protection, PhD protection) |
| `system/config/user-config.yaml` | Your domain, thinking style, preferences — Metis uses this to personalise responses |
| `agents/<name>/skill.md` | Behavioural contract for each agent — edit directly to change how an agent works |
| `system/config/token-guardrails.md` | Which model each agent uses, when to trigger handoff |

The self-improvement loop surfaces proposals to update `skill.md` files based on agent reflexions — you approve or reject each one from the Metis tab.

---

## How it works with other AI providers

Currently Claude-only (Anthropic API). The architecture supports multi-provider but this is not yet implemented. Planned for a future release: Gemini models for specific agents, OpenAI as fallback.

---

## Under the hood

- **MCP server** — 103 tools, FastMCP framework, SQLite WAL mode, runs in a WSL venv
- **Dashboard** — FastAPI + HTMX, Jinja2 templates, no JavaScript framework
- **Memory** — 5 layers: episodic · semantic · procedural · working · reflexive; vector search via sqlite-vec (BAAI/bge-small-en-v1.5, 384 dims)
- **Observation system** — agents classify observations (discovery / decision / implementation / issue) with auto-extracted concept tags; recalled by type via `get_context(budget_tokens=N)`
- **Self-improvement** — `write_reflexion()` → `aggregate_reflexions()` → `draft_self_improvement_proposal()` → user approves via dashboard
- **Safety** — injection probe on all external content, constitutional policy loader, multi-agent trust validation, PII anonymisation at boundary

---

## Project status

See [metis/system/config/implementation-progress.json](metis/system/config/implementation-progress.json) for the full milestone tracker.

**Done:** Phases 0–9b — foundations · dashboard (9 tabs) · 20+ agents · CLI skill layer · multi-layered memory · knowledge graph · self-improvement loop · token efficiency · handoff brief · content scan · observation classification · memory search.

**In progress:** Phase 10 (automated daily tasks), Phase 11 (installer), Phase 12 (test suite).

---

## Contributing

Single-researcher project for now, but feedback, issues, and PRs are welcome. Especially useful: your workflows, what agents you'd want, and how you'd use Metis in your own field.

---

## License

*MIT for the codebase · CC-BY-SA for course content. LICENSE file coming with v1.0.*
