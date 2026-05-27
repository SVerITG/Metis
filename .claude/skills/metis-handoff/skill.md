---
name: Metis Handoff
description: "handoff, switch AI, context brief, I need to switch, token limit, continue in another AI, portable context, export context, continue on another device, context export"
model: claude-sonnet-4-6
effort: normal
complexity: quick
---

## Purpose

Generate a portable context brief that can be pasted into any AI (Gemini, GPT-4, another Claude session) or used to resume work on another device. Called when you hit a token limit, switch AI tools, or need to continue work elsewhere.

## What to do when invoked

**Usage:** `/metis_handoff` or `/metis_handoff [project]` (focused brief for one project)

Do NOT ask clarifying questions. Run tools immediately and generate the brief.

**Step 1 — Collect current state**
- `get_project_status()` — all active projects
- `get_tasks(status="open")` — open and in-progress tasks
- `scan_tracked_files()` — any files changed since last scan

**Step 2 — Read the relevant PLANNING.md**
If a specific project is named, read its PLANNING.md via `read_file()`.
If no project specified, read the PLANNING.md for the project with the most open tasks.

**Step 3 — Generate and output the brief**

## Output format

Produce the following block verbatim (filled in with real data). The user will copy-paste this into another AI.

```
═══════════════════════════════════════════════════
  METIS CONTEXT HANDOFF
  Generated: {YYYY-MM-DD HH:MM}
═══════════════════════════════════════════════════

## WHO YOU ARE TALKING TO
Researcher / [your role] working on [your research domain]. Active projects: [list from get_project_status()], Metis PKM system.

## ACTIVE PROJECTS
{list each project: ID | title | status | open task count}

## CURRENT FOCUS
{project being worked on, or most urgent based on tasks}

## LAST SESSION SUMMARY
{from PLANNING.md — what was done last session, key changes made}

## OPEN TASKS (top 8 by urgency)
{task title | project | due date if set}

## RECENTLY CHANGED FILES
{from scan_tracked_files — list changed PLANNING.md files}

## WHAT TO DO NEXT
{1-3 concrete next actions, derived from Planning.md + open tasks}

## CONTEXT FOR THIS AI
You are a research assistant continuing work started in Metis (a personal PKM system built on Claude). The user's Research Context (RC) is stored locally on OneDrive. You do not have access to the SQLite database or file tools in this session — rely on information above and what the user shares directly.

If the user wants to continue a specific task, ask them to paste the relevant file content or describe what they need. Keep responses concise and action-oriented.
═══════════════════════════════════════════════════
```

## After generating

One sentence outside the template block: "Copy everything between the lines and paste it at the start of your new session. Run `/metis_research [project]` to resume here."

No additional commentary. No closers.
