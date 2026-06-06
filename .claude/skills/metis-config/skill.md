---
name: Metis Config
description: "metis config, setup metis, configure metis, first time setup, onboard, reconfigure, setup wizard, initial configuration, personalise metis, set up agents"
model: claude-sonnet-4-6
effort: thorough
complexity: chain
---

## Input handling

`/metis-config` accepts an optional section name argument.

**No argument** → run the full wizard (all 13 sections, or resume from where the user left off).

**Section argument** → jump directly to that section and re-run it only. Then write the updated values and return. Supported shortcuts:

| Argument | Runs section |
|---|---|
| `identity` / `name` / `role` | Section 1 — Identity |
| `projects` | Section 2 — Active projects |
| `news` / `topics` | Section 3 — News topics |
| `data` / `privacy` / `security` | Sections 4 & 5 — Data protection + Cybersecurity |
| `writing` / `style` | Section 11 — Writing style |
| `schedule` / `hours` | Section 12 — Working hours |
| `notifications` | Section 13 — Notification preferences |
| `wizard` / `full` | Force full wizard from Section 0 |

After a section re-run, call:
- `write_user_config(yaml_content)` to write the updated YAML
- `write_user_preferences(json_content)` to write updated JSON preferences (sections 3, 5)

For a full re-run, call `remove_first_run_marker()` at the end if it still exists.

---

## Purpose

`/metis-config` is the Metis personalisation wizard. It runs once after install (or any time you want to reconfigure) and walks you through 13 short sections that turn the generic Metis system into your personal research cortex.

**This wizard is designed for first-time users who have never used Claude Code or built an AI workflow.** Every step is plain English. Where a technical decision is needed, the wizard explains the trade-off in researcher terms, not developer terms.

The wizard writes to two places:
- `metis/system/config/user-config.yaml` — your personalisation profile (read by every agent)
- The Metis SQLite database — your projects, news topics, and library configuration

Nothing changes on your system until each section is confirmed.

---

## Opening message

Before any questions, show this:

> "Welcome to Metis setup. I'm going to ask 13 short questions so I can configure your personal research assistant the way you actually work. This takes about 15 minutes. You can stop and resume at any time — answers are saved as you go. Nothing on your system changes until you confirm at the end of each section."

Then read `metis/system/config/user-config.yaml`. If it has values already, show them and ask whether to keep, update, or restart.

---

## Section 0 — Quick environment check

Show:

> "First, a 30-second check that the basics are in place. If anything is missing I'll tell you exactly what to do — no jargon."

Run these checks in parallel:

```bash
# Python 3.10+ in WSL
python3 --version 2>&1 || echo "PY-NOT-FOUND"

# The Metis MCP server venv
ls "$HOME/.local/share/metis-mcp/.venv/bin/python3" 2>/dev/null || echo "VENV-NOT-FOUND"

# Claude Desktop config (optional — only checked, not required)
test -f "/mnt/c/Users/$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n')/AppData/Roaming/Claude/claude_desktop_config.json" && echo "CD-OK" || echo "CD-NOT-FOUND"

# Anthropic API key (env var or .env)
test -n "$ANTHROPIC_API_KEY" && echo "KEY-ENV" || (test -f "metis/system/.env" && grep -q "ANTHROPIC_API_KEY" metis/system/.env && echo "KEY-ENV-FILE" || echo "KEY-NOT-FOUND")
```

Interpret:
- `PY-NOT-FOUND` → tell the user to run `bash metis/system/mcp-server/setup-mcp.sh` first.
- `VENV-NOT-FOUND` → same.
- `CD-NOT-FOUND` → not fatal. Tell them: "Claude Desktop is not installed. That's fine — Metis works with Claude Code alone too. If you want Claude Desktop later, install from claude.ai/download and re-run this wizard."
- `KEY-NOT-FOUND` → tell them: "I don't see an Anthropic API key. You'll need one for Metis to work. Get it from https://console.anthropic.com/settings/keys, then paste it here. I'll save it to `metis/system/.env` (gitignored)." Then prompt for the key, write it to `metis/system/.env` as `ANTHROPIC_API_KEY=...`, and continue.

If all four checks pass, say: "Environment is ready. Let's personalise Metis." and proceed.

---

## Section 0b — Claude integration mode

After the environment check passes, ask:

> "One quick setup decision before we personalise Metis. How do you want it to work in **Claude Code**?
>
> **Option A — Background layer (recommended):** Metis is active in every conversation from the first message. You never need to type `/metis` — it's just always there. When you want plain Claude for something unrelated, start that message with `direct:`.
>
> **Option B — Invoke mode:** Metis only activates when you type `/metis` at the start of a message. Better if you use Claude Code heavily for unrelated technical work and want a clear on/off switch.
>
> Most researchers choose A. Which fits you better?"

If they choose **A (background layer)**:
- Call `write_file("~/.claude/CLAUDE.md", ...)` with the standard Metis always-on CLAUDE.md template (populated with their name and role from Section 1 once collected, or with placeholders now)
- Tell them: "Done. From the next Claude Code session onwards, Metis will be active automatically. You don't need to do anything else."

If they choose **B (invoke mode)**:
- Write a minimal routing-only CLAUDE.md that lists the agent shortcuts
- Tell them: "Done. Use `/metis` when you want Metis. Everything else works as standard Claude Code."

Then ask about **Claude Desktop**:

> "Do you also use Claude Desktop (the desktop app at claude.ai)?
>
> - **Yes** — I'll give you a system prompt to paste into a Project. Every conversation in that project will have Metis active. Takes 2 minutes.
> - **No / not yet** — skip this for now."

If yes: output the full system prompt text (with their name/role/interests already filled in) and walk through the Project setup steps:

> "Here's what to do — takes about 2 minutes and you only do it once:
>
> 1. Open Claude Desktop
> 2. In the left panel, click **New Project**
> 3. Name it **Research Cortex** (or anything you like)
> 4. Click the pencil icon next to the project name → **Set project instructions**
> 5. Paste the text I've provided below, then click Save
> 6. Open any conversation inside this project — Metis is now active from the first message
>
> [paste the system prompt text here]"

Note: Claude Desktop does not have a global equivalent of CLAUDE.md. A Project is the closest option — it applies to all conversations inside it, but not to conversations outside it.

Write the user's choice to `user-config.yaml`:

```yaml
integration:
  claude_code_mode: "background"   # background | invoke
  claude_desktop_project: true     # whether they set up a Desktop project
```

---

## Section 1 — Identity & Research Background

This is the most important section. The answers do **two jobs**: they brief every Metis agent on who the user is, **and** they become the brief the **Background Maker** uses to build the user's field knowledge layer (the RAG corpus every agent retrieves from, with citations). Go slowly — ask **one question at a time**, in plain language, and let the user answer in their own words. Don't rush to the next question.

Explain first:

> "This is the heart of setup. Your answers do two things: they brief every Metis agent on who you are, and they tell the Background Maker exactly what to read — so Metis can ground its answers in *your* field's literature, with citations, instead of generic web text. The more you tell me here, the sharper Metis is from day one. I'll ask a handful of short questions."

Ask, **one at a time**, recording each:

1. **Name** — "What should Metis call you?"
2. **Language** — "What language do you primarily work in? (English, French, Dutch, Spanish, …)"
3. **Role & context** — "Your role and the kind of work you do, in a sentence or two."
4. **Field & subfields** — "Your research field, and the sub-areas within it you actually work on. (e.g. 'epidemiology — neglected tropical disease surveillance, spatial methods'.)"
5. **Core topics** — "The specific topics you follow — list as many as you like. These also drive your daily news + literature scans."
6. **Seminal works & key authors** — "Any foundational papers, books, or authors your field is built on that Metis should know? Name a few — these anchor the knowledge layer."
7. **Key journals & sources** — "Which journals, report series, or organisations publish the work you trust? (specific journals, an agency's report series, a society's guidelines …)"
8. **Methods & frameworks** — "The methods, frameworks or tools central to your work (statistical, lab, field, software)."
9. **Trusted organisations** — "Institutions or bodies whose output is authoritative in your field (so the Background Maker prioritises them and Data Guardian trusts them)."
10. **Depth** — "How deep should the knowledge layer go? **light** (a starter corpus, ~30 docs), **standard** (~100), or **deep** (~250+)?"

Write to `user-config.yaml`:

```yaml
user:
  name: "..."
  role: "..."
  general_context: "..."
  language: "en"
  active_contexts: ["general"]
  specialist_contexts: []
research:
  field: "..."
  subfields: ["..."]
  topics: ["..."]
  key_authors: ["..."]
  key_works: ["..."]
  journals: ["..."]
  methods: ["..."]
  organisations: ["..."]
  corpus_depth: "standard"   # light | standard | deep
```

Mention: "You can add specialist contexts later via `/add-context`, or grow the knowledge layer anytime with `/background build <topic>`."

### → Then build the background knowledge layer (the part that makes Metis *yours*)

As soon as the background is captured, hand it **straight to the Background Maker** so Metis reads the user's field before they even ask. This is the demonstration of how the RAG/background layer is wired into Metis — do it, don't just describe it.

> "Now the part that makes Metis actually yours: I'm going to have the **Background Maker** read your field. It harvests papers and reports from the sources you named, scrubs them for safety, and indexes them locally — so every agent can cite from them. It runs in the background; in a few minutes you'll have a searchable knowledge layer for **[field]**."

- **Claude Code:** invoke **`/background-maker`** and pass the assembled brief (field, subfields, topics, key authors/works, journals, organisations, depth). It scopes → harvests (Content Harvester) → scrubs (Data Guardian) → indexes into the RAG store (`create_knowledge_database` / `build_pdf_knowledge_db`).
- **Claude Desktop:** the same — pick the **Background Maker** prompt and paste the brief into your first message. (This whole wizard runs in Desktop too; it's the more accessible path for non-developers.)

Then confirm and **show it working**:

> "Done — Metis now has a **[depth]** knowledge layer for **[field]**. Try it: ask any agent a question in your field and it answers from *your* corpus, with citations — not generic web text. Grow it anytime with `/background build <topic>`."

---

## Section 2 — Active projects

Explain:

> "Metis tracks your projects so it can route work correctly and surface what's stale. A project is anything with its own scope and own deliverable — a paper you're writing, a course you're teaching, a tool you're building."

Ask: "Do you have a folder where your important working documents live (articles, scripts, notes)? If yes, paste the absolute path."

If they provide a path:
- List top-level subfolders.
- For each: "Is `[folder_name]` an active project? If yes, what does it do in one sentence?"
- For each confirmed project, call the MCP tool `create_project(title=..., description=..., path=..., status='active')`.

If no path: "No problem — you can register projects later from the Work tab or by saying `/new-project`."

---

## Section 3 — News topics and feeds

Explain:

> "News Radar can compile a daily morning briefing on the topics you care about. The same topic list also tells the Librarian which areas to scan for new academic papers. So topics here do double duty: news + literature."

Ask:
- "What topics should Metis follow? Plain English — e.g. 'antimicrobial resistance', 'AI governance', 'climate adaptation in cities'. List as many as you want, or skip if you'd rather configure later."
- "Optional: any specific RSS feeds, journal alert URLs, or watchlists you want to include?"

Write to `user-config.yaml`:

```yaml
news_radar:
  topics: ["..."]
  rss_feeds: ["..."]
  scan_interval: "daily_morning"
```

Mention: automated morning runs require a scheduler entry — Phase 10. Until then, click *Scan now* on the Today tab dateline, or use `/schedule` to set up a Windows Task Scheduler job.

---

## Section 4 — Data protection level

Explain:

> "Metis can send your content to the Claude API to do its work. The data protection level controls how much warning you get before that happens. Pick what matches the sensitivity of your typical work — you can change it any time."

Show as a numbered menu:

```
1. Light      — Metis works freely. No prompts before sending content.
2. Standard   — Warns you before sending content with possible PII or
                personal info. (Recommended for most researchers.)
3. Strict     — Asks every time before any outbound API call.
4. Very tight — Logs and gates everything. Best for clinical / patient-data work.
```

Write to `user-config.yaml`:

```yaml
data_protection:
  level: "standard"   # light | standard | strict | very_tight
```

> **Note:** the *level* setting is consumed by the Data Guardian agent's reasoning when it triages content. The hard red lines (no patient-level data leaves the machine, no API keys in output) are constitutional and apply at every level.

---

## Section 5 — Cybersecurity level

Explain:

> "Some Metis agents browse the web — Librarian, News Radar, News Aggregator. The cybersecurity level controls how strict the URL allowlist is."

Same 1–4 scale as Section 4. Default: standard.

```yaml
cybersecurity:
  level: "standard"
```

---

## Section 6 — Folder layout walkthrough

Tell the user how Metis organises files. Walk through each folder with a one-sentence explanation:

- `metis/inbox/` — drop anything here for Metis to process.
- `metis/journal/` — your handoff notes and session logs.
- `metis/agents/` — the specialist team. Each agent has a `skill.md` (how it thinks) and `*-context.md` overlay files (your personalisation, gitignored).
- `metis/knowledge/library/` — your processed literature and references.
- `metis/knowledge/domains/` — your knowledge domains (research areas, fields).
- `metis/knowledge/courses/` — courses you're taking or building.
- `metis/projects/active/` — per-project planning and notes.
- `metis/outputs/reviews/` — what agents produce, by agent slug.
- `metis/system/config/` — Metis configuration.
- `metis/system/app-py/` — the FastAPI dashboard.
- `metis/system/mcp-server/` — the MCP tool server (don't touch unless you mean to).

Ask: "Make sense? Anything you want renamed?" If they want a customisation, write it to `user-config.yaml` under `folder_overrides:` — but do not rename the actual folders without explicit confirmation, as several tools rely on the standard layout.

---

## Section 7 — Meet your agents

Explain:

> "Metis is a team. Metis itself is the coordinator: she takes your request, picks the right specialist (or specialists), executes, and records. You can also call any specialist directly with their slash command."

Walk through the active roster:

- **Metis** (`/metis`) — the coordinator. Default entry point for any request.
- **Librarian** (`/librarian`) — papers, citations, library search.
- **Writing Partner** (`/writing-partner`) — prose, argument flow, manuscript editing.
- **Methods Coach** (`/methods-coach`) — statistics, sampling, R/Python methodology.
- **Epidemiologist** (`/epidemiologist`) — study design review, methodological challenge.
- **Software Engineer** (`/software-engineer`) — code, debugging, scripts.
- **PhD Architect** (`/phd-architect`) — multi-year thesis structure (strategic).
- **Research Architect** (`/research-architect`) — single-article tracking (tactical).
- **Meeting Memory** (`/meeting-memory`) — meeting transcription and structured notes.
- **News Radar** (`/news-radar`) — editorial morning brief.
- **News Aggregator** (`/news-aggregator`) — RSS curation upstream of News Radar.
- **Data Guardian** (`/data-guardian`) — PII protection, data classification.
- **Cybersecurity** (`/cybersecurity`) — URL validation, prompt injection defence.
- **Data Analyst** (`/data-analyst`) — local CSV/Excel/SPSS profiling and cleaning.
- **Learning Coach** (`/learning-coach`) — course progress, skill gaps.
- **Career Coach** (`/career-coach`) — CV, interviews, career strategy.
- **Presentation Maker** (`/presentation-maker`) — slide decks, visual summaries.
- **Visualization Maker** (`/visualization-maker`) — charts, diagrams, figures.
- **Builder** (`/builder`) — building new external apps and tools.
- **RC Builder** (`/rc-builder`) — extending Metis itself.
- **Course Builder** (`/course-builder`) — orchestrator for end-to-end course building (in active development).
- **Content Harvester** (`/content-harvester`) — extract content from web/PDF/YouTube.
- **Learning Architect** (`/learning-architect`) — curriculum design.
- **Design Auditor** (`/design-auditor`) — UI critique.
- **Frontend Designer** (`/frontend-designer`) — UI implementation.
- **HR Talent Spotter** (`/hr-talent`) — decides when a new agent is needed.

Mention the **self-improvement loop**:
> "After every substantive run, agents write a brief reflexion. Themes are aggregated weekly into proposals you can review on the Metis tab. Approving a proposal stages a diff against the agent's skill file — you see the exact change before it lands. No agent rewrites itself silently."

No output for this section — informational only.

---

## Section 8 — Library setup

Ask: "Want to connect your literature library now? (Recommended — it makes the whole thing more useful immediately.)"

If yes: invoke `/metis-library-setup` (or guide the user to run it after this wizard).

If later: "OK — run `/metis-library-setup` whenever you're ready."

---

## Section 9 — Morning briefing schedule

Explain:

> "If you want a morning briefing waiting for you when you open the dashboard, Metis can schedule the News Radar and Librarian scans to run before you start work. This requires a Windows Task Scheduler entry (or a cron job on macOS / Linux)."

Ask:
```
1. Run morning scans automatically at 7:00 — register schedule now (recommended)
2. I'll trigger scans manually with the "Scan now" button
3. Configure later
```

If 1: invoke `/schedule` to register the Task Scheduler / cron entry.

---

## Section 10 — Dashboard tour

Tell the user the dashboard has 9 tabs:

- **Today** — morning briefing, focus block, activity feed, capture button.
- **Knowledge** — library cards, literature, domain notes, knowledge graph, memory search.
- **Meetings** — meeting list with structured notes and follow-ups.
- **Learning** — courses you're taking, spaced repetition, competency map.
- **Work** — tasks with priority, active projects, IDE launchers.
- **Thinking** — ideas, notes, open questions, brainstorm launcher.
- **Planner** — kanban (someday → active), focus board, timeline.
- **Teach** — courses you're teaching with literature/news alerts.
- **Metis** — agent runs, memory stream, self-improvement proposals, token usage.

Tell them: "Open the dashboard now via the Desktop shortcut, or run `bash metis/system/app-py/run.sh` and visit http://127.0.0.1:8000."

---

## Section 11 — Writing style

Ask: "Anything you want the Writing Partner to know about your style? (Voice, register, length preferences, journals you commonly target, words you dislike.)"

Write to `user-config.yaml`:

```yaml
writing:
  preferences: "..."
  target_journals: ["..."]
  avoid_words: ["..."]
```

---

## Section 12 — Working hours

Ask: "What's your typical working window, and what's the best time of day for deep work? Metis uses this to suggest *when* to schedule the morning briefing and to label your focus block."

```yaml
schedule:
  working_hours: "09:00–18:00"
  deep_work_window: "09:00–11:00"
  morning_brief_time: "07:00"
```

---

## Section 13 — Notification preferences

Ask: "Where should Metis put notifications when something needs your attention? (Dashboard only / desktop notification / email digest at end of day.)"

```yaml
notifications:
  channel: "dashboard"   # dashboard | desktop | email_digest
```

---

## Closing

Show:

> "Setup is done. Here's what to do next:
>
> 1. Open the Metis dashboard (Desktop shortcut, or http://127.0.0.1:8000).
> 2. The Today tab will be quiet at first — that's normal. Click *Scan now* on the dateline to populate it.
> 3. Try `/metis_morning` from Claude Code to get your first morning briefing.
> 4. Capture your first idea: Ctrl+K from the dashboard, or `/metis_ideas` from Claude Code.
> 5. If anything looks off, run `/metis_doctor` for a one-screen status check.
>
> Welcome to Metis."

Write all config via MCP tools — do not edit files directly:
- `write_user_config(yaml_content)` — writes `system/config/user-config.yaml`
- `write_user_preferences(json_content)` — writes `system/config/user-preferences.json`
- `remove_first_run_marker()` — clears the first-run marker if it exists
- `log_agent_run("metis-config", "Personalisation wizard completed", "", "system/config/user-config.yaml")` — logs the run
