---
name: Metis Help
description: "help, what can you do, how does metis work, how to use metis, available commands, guide, FAQ, get started, what is metis, I don't know where to start, explain metis, metis help"
model: claude-sonnet-4-6
effort: normal
complexity: quick
---

## Purpose

Provide a friendly, non-technical guide to using Metis — written for researchers who may be new to AI tools and are using Metis through Claude Desktop. No coding knowledge required to understand this.

## What to do when invoked

Generate the help guide below. Do NOT call any tools — this is pure documentation. Adapt the tone to be warm and accessible, as if explaining to a smart colleague who is not a tech person.

## Output

Produce the following guide in full, formatted with clear headers and short paragraphs:

---

# Welcome to Metis 👋

**Metis is your personal research assistant.** She lives inside Claude Desktop and knows your projects, your tasks, your literature, your notes, and your research context. You don't need to explain who you are or what you're working on — she already knows.

---

## How Metis works

Metis connects to your Research Context (RC) — a structured folder on your computer that stores everything: your projects, literature, meeting notes, ideas, and more. When you ask Metis something, she reads your actual files and database to give you relevant, personalised answers.

You interact with Metis in two ways:
1. **Plain conversation** — Just type naturally. "What am I working on this week?" or "Summarise my HAT Dashboard tasks."
2. **Commands** — Type a `/command` to trigger a specific workflow.

---

## Quick-start: your first 5 minutes

1. **Check your projects:** Ask *"What are my active projects?"*
2. **See your tasks:** Ask *"What tasks do I have open right now?"*
3. **Get a weekly overview:** Type `/metis_weekly`
4. **Open the dashboard:** [Open Metis Dashboard](http://localhost:3939) *(requires the dashboard to be running — double-click `launch_metis.bat`)*

---

## Commands you can use

These commands trigger structured workflows. Type them exactly as shown.

| Command | What it does |
|---|---|
| `/metis_morning` | Morning briefing: news signals, top tasks, PhD priority, overnight activity |
| `/metis_status` | Quick snapshot: blocked tasks, what's in progress, PhD status |
| `/metis_projects` | All active projects with status, open tasks, and next steps |
| `/metis_agents` | Agent directory: who does what, when to use each, last run date |
| `/metis_info` | Full command reference for power users (Claude Code) |
| `/metis_weekly` | Full week in review: ideas captured, papers found, meetings, progress |
| `/metis_research` | Research session: load article context, check tracked files, suggest next steps |
| `/metis_brainstorm` | Explore connections between your ideas and your literature |
| `/metis_ideas` | Capture a new idea quickly |
| `/metis_notes` | Add a personal note or journal entry |
| `/metis_help` | Show this guide |
| `/metis_handoff` | Generate a portable context brief for switching AI or device |

---

## What Metis can access

Metis can read and work with:

- **Your projects** — titles, statuses, tasks, next steps
- **Your tasks** — all open, in-progress, blocked, or completed tasks
- **Your literature** — the sleeping-sickness paper database, filtered by topic, method, or year
- **Your notes** — markdown files across domains, projects, and library
- **Your ideas** — everything captured via Metis or the dashboard
- **Your meetings** — structured notes and action items
- **Your agents** — any specialised agent (Epidemiologist, Writing Partner, etc.) can be loaded on demand

---

## Connecting your project files

If you want Metis to be able to read the actual files in one of your projects (e.g. R scripts, course lessons, manuscript drafts), use the `connect_project_folder` tool:

> *"Connect my MLM course folder at `C:/Users/.../9. Education/1. Multilevel Analysis`"*

Metis will register all the relevant files and can then read them when you ask about the project.

---

## Tracking changes between sessions

Each project has a **PLANNING.md** file at its root. This is the project's working memory:

- **Metis updates it** at the end of every session (what was done, next steps)
- **You update it** when you work directly in the project outside of Metis — a 1–2 line note is enough

> *"2026-04-07: Updated Risk_Mapping_Script_2025_KC.R with new population data"*

When you start a new session, Metis reads PLANNING.md automatically and knows exactly where you left off. This replaces scanning thousands of files — lightweight and precise.

**PLANNING.md locations:**
- HAT Dashboard: `2. HAT disease/1. Epi Data/7. Dashboard/PLANNING.md`
- HAT Clustering: `2. HAT disease/1. Epi Data/4. Clustering/PLANNING.md`
- MLM Course: `9. Education/1. Multilevel Analysis/PLANNING.md`

---

## The Metis Dashboard

The dashboard is a separate visual interface — a browser-based app that shows your projects, tasks, library, ideas, notes, and more in a structured layout.

- **Start it:** Double-click `launch_metis.bat` in the dashboard folder
- **Open it:** [http://localhost:3939](http://localhost:3939)
- **It's optional:** Everything the dashboard shows, you can also ask Metis directly in Claude Desktop

---

## Getting the most out of Metis

**Be conversational.** You don't need to use commands for everything. "What should I work on today?" works just as well as `/metis_status`.

**Context is automatic.** Metis knows your research area, your projects, your PhD articles. You don't need to re-explain yourself every session.

**Metis routes to specialists.** If you ask a methods question, she'll answer as the Epidemiologist. If you need writing help, she'll answer as the Writing Partner. You don't need to know which agent to use.

**Your data stays local.** Everything is stored on your own computer. No cloud sync, no external databases. Your research stays private.

---

## Frequently asked questions

**Q: Do I need to know how to code?**
No. Metis is designed to be used entirely through plain conversation in Claude Desktop.

**Q: What if I ask something Metis doesn't know?**
She'll tell you what she can't access and suggest how to provide that information (e.g. tracking a new file or adding a project).

**Q: Can I use Metis without the dashboard?**
Yes. The dashboard is a visual helper, but Metis through Claude Desktop has access to the same information.

**Q: How do I add a new project?**
Ask Metis: *"Add a new project called X in domain Y"* — or use the Projects tab in the dashboard.

**Q: How do I add a task?**
Ask Metis: *"Add a task: review the HAT passive screening paper, linked to the phd-framework project"*

**Q: How do I connect my project files so Metis can read them?**
Ask: *"Connect my project folder at [path]"* — Metis will register the files and can read them in future conversations.

---

*Metis is built on Claude by Anthropic. Your research context is managed locally and never sent to the cloud.*
