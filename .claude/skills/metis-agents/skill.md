---
name: Metis Agents
description: "agent list, show agents, what agents do I have, agent directory, agent registry, agent overview, available agents, list all agents, agent capabilities, who does what, which agent for, metis agents"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

Display the full agent directory with rich descriptions, use cases, and last-run information. Better than the table in CLAUDE.md — gives you enough context to pick the right agent without guessing.

## What to do when invoked

**Usage:** `/metis_agents` or `/metis-agents`
**Optional:** `/metis_agents [agent-name]` — detailed profile for one agent

**Step 1 — Pull last-run data**
- `get_agent_runs(limit=50)` — get last run date per agent_slug

**Step 2 — Compose the directory**

For each agent, show: command, specialty, when to use it, what it produces, last run date.
Group by domain for readability.

**Step 3 — Single agent mode**
If an agent name is given, read its system prompt from `agents/{agent-slug}/system-prompt.md` and produce a detailed profile: full capability description, example invocations, what it reads, what it writes, its strengths and blind spots.

## Output format

```
─── Metis Agent Directory — [YYYY-MM-DD] ────────────────────

RESEARCH & PHD
──────────────
/librarian          Find papers, Zotero sync, literature metadata updates,
                    source verification. Reads: Zotero API + library/.
                    Writes: knowledge/library/. Last run: [date or never]

/phd-architect      Thesis structure, article-to-chapter alignment, gap
                    analysis, backbone planning. Reads: project docs + notes.
                    Last run: [date]

/epidemiologist     Study design review, methodology challenge, Socratic
                    questioning. Use when you want your methods stress-tested.
                    Last run: [date]

/methods-coach      Stats methods, sampling, R code methodology. Use for
                    "is this the right test?" or "how do I fit this model?"
                    Last run: [date]

WRITING & COMMUNICATION
────────────────────────
/writing-partner    Draft, edit, structure arguments. Use after you have
                    content — this agent shapes it, not creates from nothing.
                    Last run: [date]

/meeting-memory     Transcribe + structure meeting notes into decisions,
                    actions, and context. Paste raw notes or audio transcript.
                    Last run: [date]

/presentation-maker PowerPoint-ready slide decks from your content.
                    Produces structured slide outlines or PPTX via python-pptx.
                    Last run: [date]

TECHNICAL
──────────
/software-engineer  Code review, debugging, Python/R/FastAPI. Use for
                    anything that touches running code.
                    Last run: [date]

/dashboard-engineer Build/fix the Metis Python dashboard (FastAPI + HTMX).
                    Knows the stack deeply — use for UI bugs and new tabs.
                    Last run: [date]

/ux-engineer        UI/UX decisions, design system, CSS. Use when you care
                    about how something looks and feels, not just works.
                    Last run: [date]

/builder            Build new apps, tools, or MCP servers from scratch.
                    Produces scaffolded, runnable code.
                    Last run: [date]

INTELLIGENCE & LEARNING
────────────────────────
/news-radar         Curated news brief — HAT, AI, public health, methods.
                    Curates signals, does not dump headlines.
                    Last run: [date]

/learning-coach     Learning paths, skill progression, spaced repetition.
                    Use when building a new skill or reviewing competencies.
                    Last run: [date]

/edu-expert         Curriculum design, teaching strategy, course development.
                    Use for the MLM course and any teaching prep.
                    Last run: [date]

/career-coach       EU job applications, CV, career strategy.
                    Last run: [date]

SAFETY & DATA
──────────────
/cybersecurity      URL validation, prompt injection defense, agent audit.
                    Route external content through this before trusting it.
                    Last run: [date]

/data-guardian      PII protection, patient data blocking.
                    Automatically invoked when HAT patient data is detected.
                    Last run: [date]

──────────────────────────────────────────────────────────────
Total agents: 18  · To use any agent: /[agent-name] [your request]
Not sure which?   → /metis [your request]  (Metis will route for you)
```

## Edge cases
- Agent has never been run: show "never" for last run, not an error
- Single agent mode: read `agents/{slug}/system-prompt.md` and produce a 15-line deep profile
- User asks "which agent for X": infer from the request and suggest the right one with a one-line rationale
