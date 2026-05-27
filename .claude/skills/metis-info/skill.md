---
name: Metis Info
description: "metis info, help, commands, what can you do, what commands exist, show me all commands, command list, metis commands, list agents, how to use metis, what skills are available, what slash commands, what can metis do"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

Display a complete reference of all Metis commands, agents, and workflow tools. The single source of truth for what you can do with Metis from Claude Code.

## What to do when invoked

**Usage:** `/metis_info` or `/metis-info`

Print the full command reference below. Do not call any MCP tools. This is a fast static response.

## Output to print

```
╔══════════════════════════════════════════════════════════════════╗
║  METIS — Command Reference                                       ║
║  Your second-brain operating system for research & knowledge     ║
╚══════════════════════════════════════════════════════════════════╝

DEFAULT ENTRY POINT
───────────────────
/metis              Describe anything — Metis routes to the right agent(s),
                    executes the work, and records the output. Start here
                    when unsure.

────────────────────────────────────────────────────────────────────
DAILY WORKFLOW COMMANDS  (all start with /metis_)
────────────────────────────────────────────────────────────────────
/metis_morning      Morning briefing: news, top tasks, overnight activity,
                    PhD priority. Run this at the start of every work day.

/metis_status       Quick snapshot: blocked items, overdue tasks, in-progress
                    work, PhD article status. 30-second orientation.

/metis_projects     All active projects with status, open task counts, last
                    activity, and next steps.

/metis_tasks        Task list with optional filter: blocked / overdue /
                    [project-slug] / all. E.g. /metis_tasks blocked

/metis_phd          PhD article status, thesis alignment, next milestone, and
                    open methodological questions. Optional: /metis_phd article-1

/metis_literature   Library search and stats. E.g. /metis_literature [topic] 2024
                    No query = recent additions + library summary.

/metis_capture      One-command capture. Prefix routes to the right table:
                    i: idea  n: note  t: task  q: question
                    E.g. /metis_capture i: What if sample size affects detection threshold?

/metis_inbox        Scan inbox/ folder + inbox tasks. Proposes routing to
                    agents. Waits for your confirm before acting.

/metis_news         Latest news signals. Optional domain filter: [your-domain] /
                    AI / public-health / methods. E.g. /metis_news [your-domain]

/metis_agents       Agent directory: what each agent does, when to use them,
                    and their last run date.

/metis_weekly       Full week review: ideas, literature, meetings, projects,
                    PhD progress, and coming-up tasks.

/metis_brainstorm   Cross-pollinate an idea against your Research Cortex —
                    surfaces connections to existing notes, papers, projects.

/metis_research     Research session: loads article context, checks tracked
                    files, suggests next steps for active literature work.

/metis_ideas        Quick idea capture with automatic connection detection.

/metis_notes        Add or view personal notes and journal entries.

/metis_handoff      Generate a portable context brief for switching sessions,
                    hitting token limits, or continuing on another device.

────────────────────────────────────────────────────────────────────
SETUP & CONFIGURATION  (run once or when things change)
────────────────────────────────────────────────────────────────────
/metis_help         Friendly non-technical guide — for Claude Desktop users or
                    when onboarding someone to Metis.

/metis_config       First-time setup or full reconfiguration wizard (13 sections).

/add-context        Add a specialist context to your profile without re-running
                    /metis_config.

/new-project        Scaffold a new project (Shiny, R script, report, tool).

/schedule           Set up morning automation: 07:00 News Radar + 07:30
                    Librarian via Task Scheduler.

────────────────────────────────────────────────────────────────────
SPECIALIST AGENTS  (call directly when you know what you need)
────────────────────────────────────────────────────────────────────
RESEARCH & PhD
  /librarian        Find papers, update literature metadata, Zotero scan
  /phd-architect    Thesis structure, article alignment, chapter planning
  /epidemiologist   Study design review, methodology challenge, Socratic Q&A
  /methods-coach    Epidemiological stats, sampling, R methodology

WRITING & COMMUNICATION
  /writing-partner  Draft text, improve writing, structure arguments
  /meeting-memory   Transcribe, structure, and brief meeting notes
  /presentation-maker  PowerPoint slides, visual summaries

TECHNICAL
  /software-engineer   Code review, debugging, Python/R scripts, FastAPI
  /dashboard-engineer  Dashboard build/fix (FastAPI + HTMX stack)
  /ux-engineer         UI/UX decisions, design system, CSS, web interfaces
  /builder             Build new apps, tools, MCP servers

INTELLIGENCE & LEARNING
  /news-radar       World events briefing — curated, not dumped
  /learning-coach   Skill progression, learning paths, competency maps
  /edu-expert       Curriculum design, teaching strategy, course development
  /career-coach     EU job prep, CV support, career strategy

SAFETY & DATA
  /cybersecurity    URL validation, prompt injection defense, threat intel
  /data-guardian    PII protection, patient data blocking, file transmission

────────────────────────────────────────────────────────────────────
HOW ROUTING WORKS
────────────────────────────────────────────────────────────────────
  Quick      → Haiku   — factual Q, status checks, lookups
  Standard   → Sonnet  — single-agent analysis, literature search
  Deep       → Opus    — multi-file analysis, methodology challenge
  Chain      → Opus    — 2+ specialist perspectives needed

Every substantive output is saved to:
  outputs/reviews/{agent-slug}/YYYY-MM-DD_{task-slug}.md
Every run is logged to the agent_runs table in metis.sqlite.

────────────────────────────────────────────────────────────────────
DASHBOARD  →  http://127.0.0.1:8000
────────────────────────────────────────────────────────────────────
Start:  cd metis/system/app-py && bash run.sh
Tabs:   Today · Knowledge · Thinking · Planner · Work
        Meetings · Learning · Teach · Metis
```
