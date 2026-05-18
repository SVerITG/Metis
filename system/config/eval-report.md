# Metis — Pre-Public Evaluation Report

**Date:** 2026-05-05
**Evaluator:** Claude Opus 4.7 (1M context)
**Scope:** Audit before making the public GitHub release. Judged from the perspective of a non-technical senior researcher (epidemiologist / public health scientist) who can use a computer but does not read tracebacks.

---

## Executive Summary

Metis is an ambitious, mostly-built system with genuinely impressive scaffolding — a 3,500-line FastAPI dashboard, ~118 MCP tools, ~26 active agents, a working self-improvement loop, an injection probe, and a real PII scanner. Daily use by the author has clearly produced something coherent.

It is **not yet ready for public release** for a non-technical audience. Three blockers dominate:

1. **The first-run config wizard (`/metis_config`) is dangerously out of date.** It checks for R, RStudio, and 17 R packages — none of which Metis now uses. The dashboard is FastAPI/Python; the R Shiny dashboard was retired. A new user runs the wizard and is immediately told to install software the system does not need. They will give up at Section 0.1.
2. **Public-repo hygiene is poor.** Nine OneDrive sync-conflict files (`*-239GX64.py`, `*-DL29GY3.py`) are tracked in `git` and will ship to GitHub. Counts in the README (103 tools, 76 tools in CONTRIBUTING.md, 24 agents) do not match each other or the code (~118 tools, ~26 active agents). Two key agent files (`epidemiologist/skill.md`, `phd-architect/system-prompt.md`) are gitignored, leaving those agents non-functional on a fresh clone.
3. **Most slash commands and skill files reference legacy folder paths** (`agents/`, `knowledge/library/`, `knowledge/library/`, `outputs/`, `system/`, `inbox/`). These were renamed in Phase 5.4 to `agents/`, `knowledge/`, `outputs/`, `system/`, `inbox/`. Agents instructed to "save to `outputs/reviews/...`" will create the wrong directory or fail silently. This affects almost every skill and the constitution.

**Top 3 strengths that will hold up scrutiny:**

- The MCP server is real, large, and the imports load: `setup-mcp.sh` is a careful, idempotent installer that detects Python, builds the venv on `~/.local/share/metis-mcp/.venv` (avoiding the OneDrive symlink trap), writes a launcher, and auto-registers with both Claude Code and Claude Desktop.
- The 9-tab FastAPI dashboard has 72 partial templates and routers totalling 3,556 lines — there is real content behind every tab, not stubs.
- The `pre-tool-use.mjs` security hook is wired up via `.claude/settings.json`, the injection probe in `guardrails.py` exists, and the PII scanner in `safety.py` covers the documented patterns. The architecture is sound — the gaps are in coverage and currency, not concept.

The fastest path to a credible public launch is to (a) rewrite `/metis_config` for the actual Python dashboard, (b) sweep the codebase for legacy folder paths, (c) clean out OneDrive sync conflicts and regenerate accurate README claim numbers, and (d) decide which gitignored agent files should ship in skeleton form. None of these is a deep architectural problem.

---

## Inventory Results

### 2.1 Agent completeness

29 folders exist in `metis/agents/`. 3 are RETIRED (`dashboard-engineer`, `edu-expert`, `ux-engineer` — each has a `RETIRED.md`). That leaves **26 active agents**, not 24 (CLAUDE.md) or "20+" (README) — both numbers are wrong, in different directions.

The `metis/.claude/skills/` folder ships 44 skill files (mix of agents + workflow `metis-*` skills), so the *invocability* count from a fresh clone is what matters. Discrepancies (declared in CLAUDE.md / README, but no `/<slug>` slash command exists in the repo's `.claude/skills/`):

| Agent slug | Declared in docs | Folder exists | `skill.md` tracked in git | Has `/<slug>` slash command in repo |
|---|---|---|---|---|
| metis | ✅ | ✅ | ✅ | ✅ |
| librarian | ✅ | ✅ | ✅ | ✅ |
| writing-partner | ✅ | ✅ | ✅ | ✅ |
| methods-coach | ✅ | ✅ | ✅ | ✅ |
| software-engineer | ✅ | ✅ | ✅ | ✅ |
| meeting-memory | ✅ | ✅ | ✅ | ✅ |
| news-radar | ✅ | ✅ | ✅ | ✅ |
| presentation-maker | ✅ | ✅ | ✅ | ✅ |
| learning-coach | ✅ | ✅ | ✅ | ✅ |
| career-coach | ✅ | ✅ | ✅ | ✅ |
| cybersecurity | ✅ | ✅ | ✅ | ✅ |
| data-guardian | ✅ | ✅ | ✅ | ✅ |
| builder | ✅ | ✅ | ✅ | ✅ |
| **course-builder** | ✅ ("Build your own courses…") | ✅ | **❌ — only `system-prompt.md`** | **❌ MISSING** |
| **epidemiologist** | ✅ | ✅ | **❌ — `skill.md` is gitignored** | ✅ (skill in `.claude/skills/`) |
| **phd-architect** | ✅ | ✅ | **❌ — `system-prompt.md` is gitignored** | ✅ |
| **research-architect** | ✅ | ✅ | **❌ — `system-prompt.md` is gitignored** | (no global skill) |
| **content-harvester** | ✅ (CLAUDE.md) | ✅ | ✅ | **❌ no slash command** |
| **design-auditor** | ✅ (CLAUDE.md) | ✅ | ✅ | **❌ no slash command** |
| **frontend-designer-builder** | ✅ (`/frontend-designer`) | ✅ | ✅ | **❌ no slash command** |
| **hr-talent** | ✅ (referenced as routing target in skill files and README) | ✅ | ✅ | **❌ no slash command** |
| **learning-architect** | ✅ (CLAUDE.md) | ✅ | ✅ | **❌ no slash command** |
| **news-aggregator** | ✅ (CLAUDE.md) | ✅ | ✅ | **❌ no slash command** |
| **rc-builder** | ✅ (CLAUDE.md, workflows.md) | ✅ | ✅ | **❌ no slash command** |
| **visualization-maker** | ✅ (CLAUDE.md) | ✅ | ✅ | **❌ no slash command** |
| **data-analyst** | ✅ (CLAUDE.md) | ✅ | **❌ no `skill.md`** | **❌ no slash command** |

**Net findings:**
- README says "20+ specialist agents" (accurate but vague), and elsewhere "Done: 20+ agents". CLAUDE.md lists ~21 agents in tables. Actual active agents: ~26. Be specific or stop counting.
- 11 agents declared in CLAUDE.md routing have no `/<slug>` slash command in the public repo. A user told "Metis routes to Course Builder" will see Metis fail to invoke Course Builder.
- Three agents (epidemiologist, phd-architect, research-architect) have core files gitignored — they will not load on a fresh clone. This is presumably intentional (per-user customisation) but the README does not warn users to seed these files, and there are no skeleton/template versions tracked.

### 2.2 MCP server tools

- README claim: **"103 tools"** (line 140), **"103 MCP tools"** (line 218), **"103 tools"** (line 276)
- CONTRIBUTING.md claim: **"76-tool server"** (line 11)
- Memory state: "76 registered (71+5 from data_tools)"
- Actual count of `@app.tool()` decorators in the 30 imported tool modules (excluding orphan `*-239GX64*` and `*-DL29GY3*` files): **~118**
- The dashboard's setup-mcp.sh prints the registered count at install time, so the *source of truth* should be that runtime number.

**Spot-check (verified all have substantive bodies, no `pass`/TODO stubs):**

| Tool | File | Real impl? |
|---|---|---|
| `search_literature` | `literature.py` | ✅ |
| `capture_idea` | `ideas.py` | ✅ |
| `cross_pollinate` | `ideas.py` | ✅ |
| `create_project` | `projects.py:30` | ✅ |
| `get_project_status` | `projects.py:117` | ✅ |
| `aggregate_reflexions` | `improvement.py:106` | ✅ |
| `generate_handoff_brief` | `handoff.py:117` | ✅ |
| `injection_probe` | `guardrails.py` | ✅ |
| `sync_zotero_library` | `zotero.py:169` | ✅ |
| `import_bibtex_library` | `zotero.py:419` | ✅ |
| `transcribe_recording` | `transcription.py:79` | ✅ |
| `log_agent_run` | `agents.py:84` | ✅ |
| `clean_dataset` | `data_tools.py` | ✅ |

**Tracked OneDrive sync-conflict orphans (will ship to public repo):**
- `metis/system/app/check_setup-239GX64.R`
- `metis/system/mcp-server/pyproject-DL29GY3.toml`
- `metis/system/mcp-server/src/metis_mcp/server-239GX64.py`
- `metis/system/mcp-server/src/metis_mcp/server-239GX64-2.py`
- `metis/system/mcp-server/src/metis_mcp/server-DL29GY3.py`
- `metis/system/mcp-server/src/metis_mcp/tools/agents-239GX64.py`
- `metis/system/mcp-server/src/metis_mcp/tools/agents-239GX64-2.py`
- `metis/system/mcp-server/src/metis_mcp/tools/self_improvement-239GX64.py`
- `metis/system/mcp-server/src/metis_mcp/tools/transcription-239GX64.py`

These contain divergent versions of real code and will confuse anyone reading the repo. **Delete before publishing.**

### 2.3 Slash commands / skills

Local `metis/.claude/skills/` ships 44 skill files. Most have substantive bodies. **Path-currency problems** (tracked, will ship):

- `news-radar/skill.md`: "Read `agents/news-radar/system-prompt.md`" → path is now `agents/`
- `meeting-memory/skill.md`: "Saved to: `outputs/meetings/...`" → no longer exists
- `metis/skill.md`: "Saved to: `outputs/reviews/...`" → now `outputs/`
- `librarian/skill.md`: same `agents/` and `outputs/` references (sampled)
- `metis-config/skill.md`: writes to `system/user-config.yaml` (now `system/`)
- `constitution.md` (footer): "Referenced by: `agents/data-guardian/skill.md`"

**Stubs / incoherence:**
- `metis-config/skill.md` is the worst offender — see Section 3 below. Demands R+RStudio+17 R packages before allowing the user to continue, then walks them through a 10-tab dashboard ("Control Room", "Ideas", "Research", "Dropzone", "Projects", "News", "System") that no longer exists. The actual dashboard has 9 different tabs. This file alone will make the wizard unusable.

### 2.4 Dashboard tabs

All 9 tabs verified. Routers in `system/app-py/routers/` and full-page templates in `templates/`:

| Tab | Router | Template | Partials | Substantive content |
|---|---|---|---|---|
| Today | today.py (1023 lines) | today.html | 18 partials | ✅ |
| Knowledge | knowledge.py (464) | knowledge.html | 11 partials | ✅ |
| Meetings | meetings.py (209) | meetings.html | 6 partials | ✅ |
| Learning | learning.py (176) | learning.html | 5 partials | ✅ |
| Work | work.py (432) | work.html | 4 partials | ✅ |
| Thinking | thinking.py (222) | thinking.html | 4 partials | ✅ |
| Planner | planner.py (235) | planner.html | 7 partials | ✅ |
| Teach | teach.py (208) | teach.html | 6 partials | ✅ |
| Metis | metis_tab.py (492) | metis_tab.html | 7 partials | ✅ |

All 9 tabs are real, have routers and partials, and the 72 partials together represent significant rendered content. This claim is **accurate**.

### 2.5 Configuration system

Critical finding: `system/config/user-config.yaml` is committed in **stub form**:

```yaml
user:
  active_contexts: [general]
  general_context: ''
  language: en
  name: ''
  role: ''
  specialist_contexts: []
```

That's it. The metis-config wizard says it will write 13 sections worth of keys (`news_radar.topics`, `data_protection.level`, `cybersecurity.level`, `librarian.scan_interval`, `dashboard:`, `folder_overrides:`, etc.). Of these, only the `user.*` keys are actually consumed by `cache_helpers.py:load_user_context_string()` and `tools/config_tools.py`. **None of the other keys (data_protection.level, cybersecurity.level, news_radar.*, librarian.*, dashboard.*) are read by any code in the codebase.**

This is dead config. A user who fills in the wizard expecting Metis to "personalize" based on their data-protection level and news topics will not see any behavioural change — those values are written and never read.

---

## Installation Assessment

### Installer script (`install.bat` → `install.ps1`)

What it does well:
- Single entry from `.bat`, calls PowerShell, clean output with coloured status lines.
- Detects WSL, prompts admin once if needed, exits cleanly if a restart is required.
- Detects Python in WSL; installs Python 3.12 via apt if missing.
- Calls `setup-mcp.sh` which is robust (deadsnakes PPA fallback, idempotent venv).
- Generates `launch-dashboard.bat` from a template (no hardcoded user paths in the generated file because it derives `$RunShWSL` at install time).
- Creates Desktop and Start Menu shortcuts.

What will fail:
- **Anthropic API key.** Neither `install.ps1` nor `setup-mcp.sh` ever asks for or writes one. The README does not mention setting it. Yet the system needs one to talk to Claude. (The MCP server itself does not need it, but Claude Desktop / Claude Code do — and the user needs to be told.)
- **The installer does not clone the repo.** It assumes you are already in `metis/system/installer/`. The README's Quick Start has the user `git clone` first, then run `bash setup-mcp.sh` — but the README never mentions `install.bat`. So the Windows installer is orphaned from the documented path.
- **No check that Claude Code is installed.** Only Claude Desktop is checked. A user with Claude Code only will appear to succeed but get no shortcut for the slash commands.
- `wsl --status` parses output; on some Windows builds this returns localised text. The check is fragile.
- `wsl --install` followed by "press Enter to exit" leaves the user without a hint that they must come back and re-run the *whole* installer after restart, not just `wsl --install`.

### `setup-mcp.sh`

Strong points:
- Idempotent venv creation, fallback Python detection, recreates broken venvs.
- Verifies the import succeeds and prints the tool count.
- Auto-registers with both Claude Code (`~/.claude/settings.json`) and Claude Desktop. This matches the README claim.
- Adds `mcp__metis-rc__*` to the Claude Code permission allowlist — silent tool calls.
- Skips Claude Desktop registration gracefully if the config file is missing.

Concerns:
- `cmd.exe /c "echo %USERNAME%"` to detect the Windows username; if WSL is run inside a non-graphical session (e.g. SSH), this returns garbage and the Claude Desktop config write silently writes to a nonsensical path.
- The shortcut generator assumes `metis/system/launch-dashboard.bat` exists, but `launch-dashboard.bat` is gitignored — so on first run it does **not** exist, and `wslpath -w` returns the path to a missing file. PowerShell's `New-Object` shortcut creation will succeed but point at nothing. Users see a Desktop icon that does nothing.

### First-run experience: `/metis_config`

This is the biggest single user-facing failure.

The skill begins:
```
Run in bash:
   Rscript --version 2>/dev/null || echo "NOT FOUND"
If NOT FOUND:
   "R is the statistical software that powers the Metis dashboard. You need to install it before anything else will work."
```

**This is wrong.** R does not power the Metis dashboard. The dashboard is FastAPI/Python (the R Shiny dashboard at `metis/system/app/` is the *legacy* implementation, kept "as reference" per memory).

The wizard then:
- Demands RStudio (still wrong).
- Installs 17 R packages including `shiny`, `bslib`, `DT`, `visNetwork` — none of which the Python dashboard uses.
- Asks the user to walk through a **10-tab dashboard** with names that no longer exist: "Control Room, Ideas, Research, Dropzone, Meetings, Projects, Learning, News, System, Dropzone." The actual tabs are: Today, Knowledge, Meetings, Learning, Work, Thinking, Planner, Teach, Metis.
- Writes to `system/user-config.yaml` (now `system/`).
- References `agents/`, `inbox/`, `inbox/`, `knowledge/domains/`, `knowledge/library/`, `outputs/` — all renamed in Phase 5.4.
- Configures keys (data_protection.level, cybersecurity.level, news_radar.topics, librarian.scan_interval, dashboard:*, folder_overrides:*) that **no code reads**.

A non-technical researcher running `/metis_config` will:
1. Be asked to install R (their first thought: "I don't do statistics in R, why?"),
2. If they comply, sit through a 5-10 minute apt install,
3. Then be walked through tabs that don't match what they see in their browser,
4. Then have their answers written to a file no consumer reads.

This is not a bug-fix item. It is a **rewrite** item.

### Library setup (`/metis-library-setup`)

Surprisingly clean. The skill is short, asks Zotero vs Mendeley vs neither, gives concrete steps for each, and calls real MCP tools (`configure_library_provider`, `sync_zotero_library`, `import_bibtex_library`, `propose_library_organization`, `scan_literature`). All of those tools exist in `tools/zotero.py` and `tools/literature.py` with substantive implementations. **Library setup is the strongest user-facing flow in the system.** Two minor gaps:
- No graceful error message if the Zotero API key is wrong (the underlying `configure_library_provider` will return an error from the Zotero API, but the skill does not tell the AI how to surface it nicely).
- "Mendeley desktop" is increasingly rare; the skill should mention that Mendeley Reference Manager (the new app) also exports BibTeX.

---

## Workflow Assessments

### 4.1 Morning start

**Promised in README and workflows.md:** open dashboard → see overnight news + literature briefing.

**Actual state:**
- The Today tab has a `today_morning_brief.html` partial and `/api/partial/today/morning-brief` endpoint that reads from `news_briefs` and recent agent runs. ✅
- News Radar and Librarian morning runs are **not automated**. There is no scheduler running. `Phase 10 (automated daily tasks): pending` per the implementation tracker. The `/schedule` skill exists and explains how to set up Windows Task Scheduler manually, but most users won't do this.
- A first-time user opens the dashboard and sees an empty morning brief because no agents have ever run. Empty-state copy: ledger cells say "Nothing yet" or just "0" — not actively unhelpful, but no nudge to "click Scan now to populate."
- `Scan now` button on the dateline does work — it triggers the `content_scan` MCP tool. So a user who clicks it gets content. But they don't know to click it.

**Verdict:** the underlying tools exist; the *automated* morning briefing (the headline workflow in the README) is **not implemented**. The README's "Today: Morning briefing — what's new..." reads as a description of an automated feature; in practice it is manual.

### 4.2 `/metis` routing

User types `/metis Review my Article 1 draft for methodology`.

**What actually happens:**
1. Claude Code invokes the `metis/skill.md` skill, which is a *prompt* — the model is told to "synthesize context, route to specialists, ensure recording." It is not code; the model has to infer everything else.
2. The skill says "Saved to: `outputs/reviews/[agent-slug]/...`" — the legacy path. So if Claude follows it literally, output goes to a directory that doesn't exist (or creates a new one parallel to the real `outputs/`).
3. There is an MCP tool `pipeline.run_metis()` that does the routing programmatically (with stages 1-10), but the `/metis` skill does not instruct the model to call it. The skill is freeform. So routing quality is entirely dependent on the model interpreting the prompt well, every time.
4. `log_agent_run()` exists and is real — but the model has to remember to call it.
5. There is no enforcement: a chain run with no reflexion, no DB log, no output file, would simply pass.

**Verdict:** the routing *can* work if Claude is well-behaved, but there are no guardrails. The "constitution" loaded via `load_constitution()` is only included on `deep`/`chain` complexity, and only if `include_constitution=True` is passed — which depends on the agent calling the right pipeline tool. This is fragile.

### 4.3 Idea capture

**Promised:** Ctrl+K from anywhere on the dashboard, prefix-routed (`i:` `n:` `t:` `q:`).

**Actual:**
- `templates/partials/capture_modal.html` exists. ✅
- `routers/capture.py` exists (94 lines). ✅
- `tools/ideas.py` has `capture_idea` (line 118) and `cross_pollinate` (line 536). ✅
- The dashboard JS (`app.js`) wires up the Ctrl+K shortcut.

What is **not** automated:
- After capture, `cross_pollinate()` exists as a tool but is not auto-invoked from `capture_idea()`. The user has to invoke it. The README says "Cross-pollination ... finds connections — Connections displayed in right panel" — this is the *desktop workflow* in workflows.md (Workflow 3), but in practice the right panel in the dashboard does not auto-populate after capture. The user sees their idea was saved; nothing else.

**Verdict:** Capture works. Cross-pollination is real but not automatic — the workflow promised in README/workflows.md is half-implemented.

### 4.4 Meeting intelligence

- `/meeting-memory` skill is solid (50 lines of real reasoning + edge cases).
- `meeting_memory` MCP tool: there is `transcribe_recording` (transcription.py:79) — one tool. There is no `extract_action_items`, no `cross_reference_to_projects`, no auto-link to literature.
- The Meetings tab in the dashboard shows a list, stats, follow-ups partial — these are **read-only views**: they query a `meetings` table that the user must populate themselves (or that `transcribe_recording` populates after a manual call).

**Verdict:** Meeting Memory is **described as more capable than it is.** The skill is good prose; the supporting infrastructure is one transcribe tool plus database tables. Cross-referencing to projects/literature is not implemented.

### 4.5 Course building

**Promised in README:** "Build your own courses — the Course Builder Agent scrapes sources, designs curriculum with proven pedagogy (Bloom's taxonomy, spaced repetition), and publishes into your Learning tab."

**Actual:**
- `metis/agents/course-builder/system-prompt.md` exists (568 words, describes a 7-step orchestration). ✅
- `metis/system/config/course-builder-questionnaire.md` exists (36 lines). ✅
- **No `skill.md` file** for course-builder — meaning there is no `/course-builder` slash command on a fresh clone.
- No MCP tool named `course_builder_run`, `harvest_course_sources`, `assemble_course`, etc. The system-prompt instructs the agent to "delegate to Content Harvester / Learning Architect / Writing Partner / Methods Coach / Visualization Maker" — none of which have slash commands either.
- The Teach tab has a "Build" button (`buildCourse` in `app.js`) that POSTs to `/api/teach/...`, but this calls placeholder endpoints. No course is actually generated.

**Verdict:** Course Builder is **aspirational, not implemented end-to-end.** The README markets it as a working feature. It is a system-prompt waiting for the orchestration code that doesn't exist yet.

### 4.6 Self-improvement loop

- `tools/improvement.py` has `aggregate_reflexions` (line 106) and `draft_self_improvement_proposal`. ✅
- `routers/metis_tab.py` has `/api/improvement/draft/{agent_slug}`, `/api/improvement/promote/{proposal_id}`, `/api/improvement/reject/{proposal_id}`. ✅
- `templates/partials/metis_improvement.html` exists, surfacing themed reflexions and pending proposals. ✅
- "Promote" — what does it do? Reading `metis_tab.py:434` shows it updates a `self_improvement_proposals` table row to `status='promoted'`. **It does not edit the agent's `skill.md` file on disk.** The proposed improvement is captured as text but never applied.

**Verdict:** The reflexion capture and dashboard surface are real; the *loop* that the README promises ("you approve or reject each one from the Metis tab" with the implication that approval updates the agent) is **half-built**. Approving a proposal records the approval; it does not change the agent.

---

## Data Protection & Security

### Data Guardian
- `agents/data-guardian/skill.md` is solid prose: 4-level classification, edge cases.
- The skill *advertises* a "pre-tool-use hook" that "fires automatically before every WebFetch, WebSearch, Bash, Write, and Edit call."
- The hook (`metis/.claude/hooks/pre-tool-use.mjs`) **exists and is wired up** via `metis/.claude/settings.json` (`"matcher": "WebFetch|WebSearch|Bash|Write|Edit"`).
- But the hook only fires inside **Claude Code** (it's a Claude Code hook). When Metis is used via **Claude Desktop** with the metis-rc MCP server, the hook does not fire. The README and the data-guardian skill imply the hook protects all Metis use — it does not.
- The hook's sensitive path patterns reference legacy folders (`knowledge/library`, `inbox/`). On a fresh clone with new folder names, the patterns will not match anything. Patient data dropped into `inbox/` (the new path) would not trigger the hook.
- The PII scanner in `tools/safety.py` covers email, phone, patient_id, GPS (high-precision), Belgian national ID, and 9 sensitive column names. The README's "40+ PII patterns" claim is **overstated** — there are 5 regex patterns and 9 sensitive column names, totalling 14 distinct checks. (The 40 might come from counting individual pattern alternations, but readers will count "patterns" as recognisably different categories.)
- I see no test that proves the scanner blocks a fake patient row end-to-end.

### Cybersecurity agent
- The hook has a domain allowlist of **17 entries** (pubmed, scholar, arxiv, biorxiv, medrxiv, who.int, github, raw.githubusercontent, api.anthropic, cran, pypi, rss.ncbi, feeds.bbci, reuters, reliefweb, dndi, msf).
- For unknown domains, the hook **warns but does not block**. The agent skill says "validates every internet-facing action before it happens" — in practice, it warns. README's "Cybersecurity URL validation is enforced at code level" is mostly true (it is a Claude Code hook in code), but the enforcement is advisory, not preventive.
- The injection-pattern set in the JS hook is 8 patterns; the Python `guardrails.py` set is 11 patterns. README says "11 prompt injection patterns" — **accurate for the MCP-side scanner**, **understated for the hook**, and the two pattern sets are not unified (drift over time is likely).

### Red lines
- Red Line 1 (no patient data externally): **partially enforced** — the hook flags sensitive paths (legacy paths only); `tools/safety.py` scans content; nothing blocks a patient CSV from being read into a prompt by a tool other than these.
- Red Line 2 (confirm before destructive actions): **enforced** — `rm -rf` in the metis tree is blocked by the hook.
- Red Line 3 (log all agent actions): **partially enforced** — `log_agent_run` exists and is in the constitution, but logging is up to the calling agent. There is no automatic logging for the freeform `/metis` route.
- Red Line 4 (when in doubt, ask): prompt-level only.
- Red Line 5 (never leak personal data): hook warns on outbound network calls in Bash; otherwise prompt-level only.

**Verdict:** the security posture is "advisory + scattered" rather than "enforced + central". For the documented user (clinical/PII-handling researcher), the Data Guardian story should be tightened before public release: at minimum, update the hook's path patterns to the current folder names, unify the injection pattern lists, and adjust the README to say "warns" not "blocks" where it warns.

---

## Researcher UX Findings

### Language clarity (priority order)

- **README opens with "MCP Server" and uses "FastMCP framework", "FastAPI + HTMX", "sqlite-vec", "BAAI/bge-small-en-v1.5, 384 dims", "OpenTelemetry"** without explanation. The README declares itself "for researchers, not developers" and then writes for developers. A senior epidemiologist will not know what an MCP server is, and the explanation never comes.
- **README's "How to use" path is unclear.** Quick Start says `bash <(curl -fsSL ...)`, then "Then start the dashboard: ./run.sh". A non-technical user does not know to (a) open WSL, (b) navigate to the cloned folder, (c) chmod +x the script, (d) recognise that `./run.sh` is gitignored and may not exist.
- **PERSONALIZE.md is lighter** but still drops "API key", "BibTeX", "API key" without explanation of where to put them.
- **Claude Code vs. Claude Desktop confusion.** The README's table is helpful, but a user who has only ever used the Claude.ai web interface will not understand why "Claude Code (terminal)" is even a thing. A one-paragraph "what these two products are" intro is missing.
- The phrase "second brain configured for AI use" (README line 25) is jargon researchers might not parse. "A research notebook your AI tools can actually read" or similar would land harder.

### Error states

For each scenario, what would a non-technical user actually experience:

| Scenario | Current behaviour | Researcher's understanding |
|---|---|---|
| Dashboard port 8000 in use | uvicorn errors to stderr in the WSL window, dashboard doesn't open in browser | They see the browser fail, no clear path to fix |
| API key invalid/missing | Claude Code session itself prompts for API key — Metis-side error is "tool call failed" | Confusing; the failure is at Claude Code, not Metis, but they will blame Metis |
| Zotero API key wrong | `configure_library_provider` returns an HTTP error from Zotero | The skill does not surface this — the user sees "Sync failed" with no detail |
| `/metis` request unmatched by any agent | The `metis` skill's "edge cases" tells Claude to "route to HR/Talent Spotter to assess the capability gap" — but `/hr-talent` has no slash command | Claude will likely improvise and the user will not know they hit an edge case |
| File dropped into `inbox/` and never processed | Nothing scans `inbox/` automatically (Phase 10 not implemented) | They drop a PDF and it sits there forever |

**Verdict:** error UX is uniformly weak. Most failures are silent or surfaced as Python exceptions in a WSL terminal window. Required for public: empty states with "click here to fix" copy, and a `metis_doctor` command that runs the obvious checks (API key set? venv intact? DB readable? scheduler registered?).

### Empty states

A first-run dashboard:
- Today: morning brief reads "0 news, 0 papers" — not "Click Scan now to start your first briefing."
- Knowledge: 0 cards, 0 literature — Knowledge tab does NOT prompt the user to run `/metis-library-setup`.
- Meetings: empty list, no nudge.
- Learning: a "placeholder courses" partial exists with 14 seeded courses (per memory) but they're not the user's — they're the author's. A new user sees someone else's course list.
- Work: 0 tasks, 0 projects — no nudge to register a project.
- Thinking: 0 ideas — capture button is in the sidebar but no inline guidance.
- Planner: empty kanban, no "drag your first task here."
- Teach: 0 courses — "Start building" button exists.
- Metis: empty agent runs — looks broken.

**Verdict:** the dashboard is built for someone who has been using it for weeks. A first-time user will see a sea of zeros and feel the system is broken. **Empty states are the single biggest UX gap.**

### The "day one" path

A non-technical researcher's path from "downloaded the repo" to "first useful output":

1. Clone repo (terminal — first friction; WSL not opened by default on Windows).
2. Run `bash setup-mcp.sh` — works *if* WSL is set up *and* Python 3.10+ exists *and* curl/git/sudo work. Will fail silently in many corporate environments.
3. Restart Claude Code & Claude Desktop — ok.
4. Open Claude Code, type `/metis_config` — wizard immediately demands R + RStudio + 17 R packages they don't need. **GAME OVER for most users.**

If they survive (4):
5. Wizard walks them through old tabs that don't match the dashboard.
6. Open dashboard via shortcut — empty.
7. They're now stuck: no agent has run, no idea has been captured, no library, no morning brief.

**Time to first useful output for a non-technical user, today: realistically, never** — without significant developer help. The good news: this is fixable in a focused 2-3 day rewrite of `/metis_config` plus empty-state copy.

---

## README Accuracy

| Claim | Status | Evidence |
|---|---|---|
| "76+ MCP tools" (CONTRIBUTING.md) | **Misleading** | Actual count ≈118; CONTRIBUTING text is stale |
| "103 MCP tools" (README, 3 places) | **Overstated** | Actual count of decorators in current code ≈118, but the runtime registered count per memory is 76. The two should be reconciled. |
| "20+ specialist agents" (README) | **Accurate but vague** | 26 active agents (29 minus 3 retired) |
| "24 named agents" (CLAUDE.md table) | **Inaccurate** | Counted ≈21 entries in the CLAUDE.md route table, doesn't match reality either way |
| "9 dashboard tabs, all functional" | **Accurate** | All 9 verified |
| "40+ PII patterns" | **Overstated** | 5 regex patterns + 9 sensitive column names = 14 distinct checks |
| "11 prompt injection patterns" | **Mixed** | Accurate for `guardrails.py` (11), understated for `pre-tool-use.mjs` hook (8) — and the lists differ |
| "WhatsApp integration" | **Aspirational** | `webhook.py` exists with Twilio integration; setup not in installer; no docs for users; not tested in CI |
| "Docker containerisation (planned)" | **Accurate** | Marked "coming soon" in README — fine |
| "Windows installer (coming soon)" | **Misleading** | `install.bat` exists; not "coming soon" — it ships, just not tested clean and not referenced in Quick Start |
| "Morning briefing — what's new" (Today tab) | **Misleading** | Manual; automated scan/scheduler is Phase 10 (pending) |
| "Idea capture — Ctrl+K from anywhere, prefix-routed" | **Accurate** | Verified |
| "Cross-pollination" | **Half-implemented** | Tool exists; not auto-triggered after capture |
| "Build your own courses" via Course Builder Agent | **Misleading** | System prompt exists; orchestration code does not; no slash command |
| "Self-improvement loop ... you approve or reject each one from the Metis tab" | **Misleading** | Promote endpoint exists; it sets a status flag, does not edit the agent's skill file |
| "Memory search — semantic search across everything Metis has learned (sqlite-vec + fastembed)" | **Accurate** | `vector_memory.py` has 6 tools; the partial `knowledge_memory_search.html` exists |
| "Backup and encryption — AES-256-GCM encrypted database exports on demand" | **Accurate** | `backup.py` has 7 tools; AES-GCM is implemented |
| "Data Guardian blocks patient-level data before it reaches the API" | **Misleading** | Guards Bash/Write/Edit/WebFetch in Claude Code via hook; does not protect Claude Desktop sessions or other paths |
| Phase status: "Phases 0-9b done, 10/11/12 pending" | **Accurate** | Matches `implementation-progress.json` |

**Counts to fix in one pass before publishing:**
- Tools: 103 / 76 → reconcile to a single number, ideally the runtime count printed by `setup-mcp.sh`
- Agents: 20+ / 24 → say "26 specialist agents (3 retired)"
- PII: "40+" → "14 PII checks (5 regex patterns + 9 sensitive column names)"
- Injection: 11 → say "11 server-side patterns + 8 client-side hook patterns" or unify the lists

---

## Public-Readiness Checklist

### Installation
- [BLOCKING] Installer works on a clean Windows + WSL machine without prior setup
  *Reason:* `/metis_config` blocks at R requirement; install.ps1 doesn't ask for API key; launch shortcut points at gitignored bat
- [NEEDS WORK] Setup script registers correctly with both Claude Code and Claude Desktop
  *Mostly works; brittle in non-graphical WSL sessions*
- [BLOCKING] First-run config wizard is complete and comprehensible to a non-technical user
  *`/metis_config` is fundamentally wrong: demands R, walks through wrong tabs, writes dead config*
- [READY] Library setup (Zotero / BibTeX) is guided and handles errors gracefully
  *`/metis-library-setup` is the cleanest user-facing flow; minor error-handling polish only*

### Core functionality
- [NEEDS WORK] `/metis` routing works end-to-end (request → agent → output → DB log)
  *Works in spirit; no enforcement; output paths in skill file are stale (outputs/)*
- [READY] Dashboard starts reliably and shows real content after first use
  *9 tabs all render; needs first-use seed data*
- [NEEDS WORK] At least one complete workflow works without developer intervention
  *Library import + literature search comes closest; needs documentation linking*
- [NEEDS WORK] Idea capture saves to DB and cross-pollination runs
  *Capture works; cross-pollination not auto-triggered*

### Safety
- [NEEDS WORK] Data Guardian blocks patient-level data before it reaches the API
  *Hook fires in Claude Code only; sensitive-path patterns reference legacy folders*
- [NEEDS WORK] Cybersecurity URL validation is enforced at code level
  *Hook warns but does not block; allowlist is short*
- [READY] No API keys or personal data are committed to git
  *`.env` is gitignored; `journal/`, `outputs/reviews/`, `inbox/`, `projects/active/` all gitignored*

### Documentation
- [NEEDS WORK] README is accurate (no misleading claims)
  *Multiple count mismatches; some features described as built when half-built*
- [BLOCKING] PERSONALIZE.md is sufficient for a first-time user to complete setup
  *Sends user to `/metis_config` which is broken*
- [NEEDS WORK] Every slash command documented in CLAUDE.md actually exists
  *11 of the routing-table agents have no slash command in the public repo*

### Researcher UX
- [BLOCKING] Non-technical researcher can install + run first workflow in <30 min
  *Realistically: cannot today. R-install detour alone burns 10+ min before failing*
- [BLOCKING] Empty states are informative, not blank
  *All 9 tabs show "0" without first-step guidance*
- [NEEDS WORK] Error messages are human-readable
  *Mostly Python exceptions or silent failures*
- [NEEDS WORK] All dashboard buttons and links are functional
  *Most are wired; some Teach and Metis-tab buttons are toast stubs*

### Repo hygiene (added category)
- [BLOCKING] No OneDrive sync-conflict files in the repo
  *9 `*-239GX64*` and `*-DL29GY3*` files are tracked and will publish*
- [NEEDS WORK] No hardcoded user paths or names in tracked files
  *`launch-dashboard.bat`/`launch-metis.bat` are gitignored, but `metis/.claude/skills/metis-config/skill.md` and others have `sverschaeve` paths in examples*
- [NEEDS WORK] LICENSE file present
  *README says "LICENSE file coming with v1.0" — should ship before public release*

---

## Prioritised Fix List

### MUST FIX before publishing (blocking)

1. **Rewrite `/metis_config` for the Python dashboard.** Drop R/RStudio sections entirely. Use the actual 9 tab names. Remove dead config keys (data_protection.level etc.) or wire them up to real consumers. Add an Anthropic API key prompt. ~1 day.
2. **Delete the 9 OneDrive sync-conflict files** (`*-239GX64*`, `*-DL29GY3*`) from `git rm` history before pushing public. ~30 min.
3. **Sweep all skill files and configs for legacy folder paths.** Replace `agents/` → `agents/`, `knowledge/library/` → `knowledge/library/`, `knowledge/library/` → `knowledge/library/`, `outputs/` → `outputs/`, `system/` → `system/`, `inbox/` → `inbox/`. Affected: `metis/.claude/skills/*/skill.md`, `agents/*/skill.md`, `agents/*/system-prompt.md`, `system/config/constitution.md`, `system/config/workflows.md`, `system/config/red-lines.md`, `metis/.claude/hooks/pre-tool-use.mjs`. ~2-3 hours with grep + sed.
4. **Decide what to do with the 3 gitignored agent files** (`epidemiologist/skill.md`, `phd-architect/system-prompt.md`, `research-architect/system-prompt.md`). Options: (a) ship a generic skeleton in git and gitignore only the `*-context.md` overlay; (b) document explicitly in PERSONALIZE.md that these agents need to be created from a template before use. ~1 hour each agent.
5. **Reconcile the count claims** in README and CONTRIBUTING.md (tools, agents, PII, injection). Use the runtime numbers, not aspirational ones. ~30 min.
6. **Add empty-state copy** to all 9 tabs. Each tab's first partial should detect zero state and emit "Run /metis_config to start" or "Click Scan now to populate" or similar. ~half day.
7. **Add a LICENSE file** (MIT for code, CC-BY-SA for course content as the README promises). ~10 min.
8. **Document the WSL/API-key prerequisites in README Quick Start.** Currently a user lands on `bash <(curl ...)` with no warning that WSL must be installed first and Anthropic API key configured. ~30 min.

### SHOULD FIX (needs work, ship-blocking for trust)

9. **Wire `cross_pollinate` automatically into `capture_idea`.** Either as a chained call inside the tool or as an HTMX trigger that updates a "Connections" panel in the modal. ~3 hours.
10. **Wire `promote_proposal` to actually edit the agent's skill file** (with backup, with confirmation). Otherwise the self-improvement loop is theatre. ~half day.
11. **Add 11 missing slash commands** for agents listed in CLAUDE.md (course-builder, content-harvester, design-auditor, frontend-designer-builder, hr-talent, learning-architect, news-aggregator, rc-builder, research-architect, visualization-maker, data-analyst). Each is ~50 lines. Or remove them from CLAUDE.md if you don't intend to ship them. ~half day total if generated from existing system-prompt.md files.
12. **Update the pre-tool-use hook's sensitive-path patterns** to current folder names. Unify the injection pattern list with `guardrails.py`. ~1 hour.
13. **Make Phase 10 (scheduler) at least *manual* with a clear "schedule morning brief"** button on the Today tab that calls into the existing `/schedule` skill. Otherwise the README's morning-brief promise is empty. ~half day.
14. **Tone the README down** wherever a feature is half-built: course-builder ("system prompt + orchestration in progress"), morning-briefing-automation ("manual today, scheduler in Phase 10"), self-improvement ("proposals are captured; auto-apply is in progress"), Data Guardian ("active in Claude Code; Claude Desktop coverage planned").
15. **Add a `metis_doctor` MCP tool / slash command** that runs: API key set? venv intact? DB readable? scheduler registered? folder-rename sweep clean? Outputs a one-screen status. ~half day. This single tool would make user-side debugging tractable.

### NICE TO HAVE (ship without; iterate later)

16. Test suite for PII detection (Phase 12). Even one positive test that "fake-patient.csv triggers BLOCK" is a credibility multiplier.
17. CI on push (lint + import + tool-count snapshot).
18. Real Docker image (the README already labels it "coming soon" — acceptable to defer).
19. Multi-provider AI support (the README labels Claude-only — acceptable).

---

## Verdict

**Do not publish today.** With ~3-5 focused days of work — primarily the metis_config rewrite, the legacy-path sweep, the OneDrive cleanup, the empty-state copy, and the README count fixes — Metis becomes credibly first-public-release-ready. The bones are good; the surface is scuffed by drift.

The most important question before launch is not "is everything implemented?" — most readers will accept that a single-researcher project has aspirations baked in. The question is "does the README's first-five-minutes promise survive a clean install?" Today: no. After the blocking fixes above: yes.
