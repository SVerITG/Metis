<p align="center">
  <img src="Metis_github.png" alt="Metis — Research Cortex" width="420"/>
</p>

<h1 align="center">Metis — The Research Cortex (base shell)</h1>

<p align="center">
  <em>A research companion built on Claude that learns <strong>your</strong> field —
  then grounds every answer in your own literature, with citations.</em><br>
  <em>This is the domain-agnostic shell. Configure it for your discipline and it builds you a knowledge layer.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-v1.0-brightgreen" alt="v1.0"/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="License"/></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Claude-MCP-orange?logo=anthropic" alt="Claude MCP"/>
  <img src="https://img.shields.io/badge/data%20stays%20local-✓-green" alt="Data stays local"/>
</p>

---

## What this is

**Metis is a local-data research companion for Claude** (via MCP): persistent, project-aware memory, retrieval over *your own* indexed library with page-level citations, automatic cross-pollination across your papers/meetings/ideas/notes, 30+ routed specialist agents, and a weekly self-improvement loop. Your documents, notes, embeddings and memory stay on your machine; reasoning runs on the Claude API.

**This repository is the base shell** — full architecture, **no domain content**. It's the starting point for two things:

1. **Run it for your own field.** On first setup, the config wizard asks a short, thorough questionnaire about your research background — your field, sub-areas, core topics, the seminal works and key authors, the journals and organisations you trust, your methods, and how deep to go. Then the **Background Maker** reads that field for you: it harvests open-access papers and reports, scrubs them for safety, and indexes them locally — so from day one every agent answers from *your* discipline's literature, cited, instead of generic web text.

2. **Build a domain edition.** Fork this, add your field's curated knowledge library, specialist agents, journals and RSS feeds, and open a PR. See **[Metis_PH](https://github.com/SVerITG/Metis_PH)** — the Public Health & Epidemiology edition — as a worked example of a domain pack built on this shell.

---

## The core idea — the background layer is wired into everything

```
Setup wizard  ──►  "What's your field? key works? journals? trusted bodies? how deep?"
      │
      ▼
Background Maker  ──►  harvest (open-access)  ──►  Data Guardian scrub  ──►  local RAG index
      │
      ▼
Every agent now retrieves from YOUR corpus, with page-level citations — and refuses to invent
what it can't find.
```

Run it in **Claude Desktop** (pick the *Metis onboarding* prompt) or **Claude Code** (`/metis-config`, then `/background init`). Grow the layer anytime with `/background build <topic>`.

---

## Install

**macOS / Linux / WSL**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SVerITG/Metis/main/system/mcp-server/setup-mcp.sh)
```

**Windows** — download the installer from Releases, double-click, follow the wizard.

Requirements: Python 3.10–3.13 · a Claude (Anthropic) API key · Claude Desktop or Claude Code.

After install, **set it up for your field**: open Claude Desktop → *Metis onboarding* prompt (or in Claude Code, `/metis-config`). That's where the questionnaire runs and your knowledge layer gets built.

---

## Editions

| Repository | What it is |
|---|---|
| **[Metis](https://github.com/SVerITG/Metis)** | This — the domain-agnostic base shell. Fork to build your own edition. |
| **[Metis_PH](https://github.com/SVerITG/Metis_PH)** | Public Health & Epidemiology — a fully worked edition with a pre-loaded knowledge layer. |

**Build a domain pack:** fork this shell, add your field's knowledge library, agents, journals and feeds, and open a PR.

---

## For developers

The full architecture, security model, memory layers, RAG details, configuration, and installation options are documented in the **[Metis_PH README](https://github.com/SVerITG/Metis_PH#readme)** — the codebase is identical; only the domain content differs. In short: FastMCP server (Python) + FastAPI/HTMX dashboard + SQLite (WAL) + local `sqlite-vec` + `nomic-embed` embeddings, 30+ agents, six security layers, and a `/safe-analysis` "send code, not data" workflow for sensitive data.

---

## License

**AGPL-3.0** for the code. **CC-BY-SA 4.0** for course content. See [LICENSE](LICENSE) and [LICENSING.md](LICENSING.md).
