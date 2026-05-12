# Contributing to Metis

Metis is built for the research community. The current version reflects one researcher's domain (public health and epidemiology) — but the architecture is designed to support any research field. The best contributions are domain backgrounds, specialist agents, and workflows that make Metis genuinely useful in your field.

---

## What we are looking for

### Domain backgrounds (highest priority)

A domain background is a package of resources that configures Metis for a specific research field. It consists of:

- **`domains/<field>/feeds.yaml`** — curated RSS feeds and API endpoints for journals, databases, and news sources
- **`domains/<field>/vocabulary.md`** — key terms, standard classifications, MeSH/Thesaurus equivalents
- **`domains/<field>/agents/`** — one or two field-specific agent definitions (system-prompt.md)
- **`domains/<field>/setup.md`** — what external tools the domain requires and how to configure them

See `knowledge/domains/public-health-epidemiology/` as the reference implementation.

**Domains most needed:**

| Domain | Key resources to include |
|---|---|
| Social Sciences | SSRN, JSTOR, qualitative methods tools (ATLAS.ti, NVivo), sociology journals |
| Biomedical Sciences | ClinicalTrials.gov, UniProt, PDB, MeSH vocabulary, biostatistics workflows |
| Economics | NBER working papers, World Bank/IMF APIs, STATA workflows, econometrics methods |
| Environmental Science | NOAA, Copernicus, PANGAEA, climate data APIs, GIS tools |
| Psychology | PsycINFO queries, APA journals, behavioral assessment tools |
| Law & Policy | UN document monitoring, legal citation formats, treaty databases |
| Education Research | ERIC feeds, Bloom taxonomy, curriculum design frameworks |
| Nursing & Allied Health | CINAHL, Cochrane, clinical guideline databases |

### Agents

New specialist agents that fill gaps in the current team. Each agent needs:

```
agents/<agent-slug>/
├── system-prompt.md     # Role definition, scope, methodology, output format
├── skill.md             # Concise behavioural contract (loaded at invocation)
└── README.md            # What this agent does, when to use it, example inputs
```

Write `system-prompt.md` the way you would brief a specialist colleague you've just hired. Be specific about methodology, about what the agent should challenge or question, and about what it should never do.

**Agents most wanted:**
- RCT methods specialist — evaluates randomised controlled trial design and reporting
- Qualitative methods coach — thematic analysis, grounded theory, IPA, NVivo integration
- Economic evaluation expert — cost-effectiveness, HTA, budget impact
- Systematic review conductor — PRISMA workflow, screening, data extraction, meta-analysis
- Clinical trial GCP specialist — ICH-GCP, protocol review, regulatory compliance

### Skills (slash commands)

Skills are Claude Code slash commands that invoke specific workflows. The 11 currently missing:

`/course-builder`, `/content-harvester`, `/design-auditor`, `/frontend-designer-builder`,
`/hr-talent`, `/learning-architect`, `/news-aggregator`, `/rc-builder`,
`/research-architect`, `/visualization-maker`, `/data-analyst`

Each skill lives in `.claude/skills/<slug>/skill.md`. Minimum viable skill:

```markdown
---
description: One-line trigger description for auto-activation
---

## What this does
Brief description.

## Input
What the user should provide.

## Steps
Numbered steps the agent follows.

## Output
What the user gets back.
```

### Hooks

Claude Code hooks are JavaScript files that fire at specific lifecycle events. Most wanted:

- **`stop.mjs`** — auto-generate handoff brief at session end (fires when `/exit` is called)
- **`post-tool-use.mjs`** — session pulse logging (count tools called, track which agents active)
- **`pre-compact.mjs`** — snapshot working state before context compaction

See `.claude/hooks/pre-tool-use.mjs` for the existing pattern. Hooks receive tool call data as stdin JSON and can block execution by exiting non-zero.

### MCP tools

New tools for the 120-tool MCP server. Each tool is an `@app.tool()` function in `system/mcp-server/src/metis_mcp/tools/`. Add tools to an existing file or create a new module. Register new modules in `server.py`.

- PubMed E-utilities connector (`scan_pubmed_alerts()`)
- OpenAlex paper monitoring (`scan_openalex()`)
- SPECTER2 / nomic-embed embedding for cross-pollination
- Telegram bot message handler for mobile capture
- Reference manager connectors (EndNote, RefWorks, Paperpile)

### Infrastructure

- **Improved cross-pollination** — replace SQL LIKE matching with SPECTER2 or nomic-embed vector similarity
- **Domain-specific tool loading** — serve only relevant tools per agent (currently all 120 on every call)
- **Mobile PWA** — FastAPI `/capture` page + `manifest.json` + service worker for phone home screen
- **`.exe` installer** — Windows installer with no terminal requirement

---

## Before submitting a pull request

1. **Run the dashboard locally** and confirm the tab you changed still loads: `bash system/app-py/run.sh`
2. **Check for personal data**: `git status` — make sure `*-context.md`, `journal/`, `projects/`, `outputs/` are not staged
3. **No secrets in diff**: no API keys, email addresses, or patient identifiers
4. **MCP server still starts**: `~/.local/share/metis-mcp/run.sh` should print tool count without errors
5. For new agents: test by invoking the agent in Claude Code and checking that it follows its system-prompt

---

## Personal ↔ public sync

The repo is designed so your personal research data never touches GitHub.

```
GitHub (public)                    Your machine (personal)
──────────────────────────         ──────────────────────────────
system/                      ←→   system/
agents/ (generic)            ←→   agents/ (generic + *-context.md)
.claude/skills/              ←→   .claude/skills/
README, CONTRIBUTING         ←→   README, CONTRIBUTING
                                   journal/              (gitignored)
                                   projects/active/      (gitignored)
                                   outputs/reviews/      (gitignored)
                                   knowledge/library/    (gitignored)
                                   inbox/                (gitignored)
                                   system/.env           (gitignored)
                                   agents/**/*-context.md (gitignored)
```

`git pull origin main` updates system files without touching personal data.

---

## Development setup

```bash
# Clone
git clone https://github.com/SVerITG/Metis_pers.git
cd Metis_pers

# Install MCP server (auto-registers with Claude Code + Claude Desktop)
bash metis/system/mcp-server/setup-mcp.sh

# Start dashboard
bash metis/system/app-py/run.sh
# → http://127.0.0.1:8000
```

---

## Questions, ideas, feedback

Open a GitHub Discussion for questions, ideas, and field-specific feedback.
Open an Issue for bugs with full context: expected behaviour, what happened, and version (`metis-doctor` in Claude Code prints system info).

We especially want to hear: how are you using Metis in your field? What's missing? What's broken for your workflow? The best features come from real research practice.
