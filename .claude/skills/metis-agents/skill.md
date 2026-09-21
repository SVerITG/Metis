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
**Optional:** `/metis_agents [agent-name]` — detailed profile for one specialist

Nothing in this directory is a command to type. Every specialist is registered as
a subagent and is picked up from what the request is about; `@agent-name` insists
on a particular one, and `/metis` routes explicitly. The directory exists so the
researcher knows who is in the building, not so they can summon anyone by name.

**Step 1 — Pull last-run data**
- `get_agent_runs(limit=50)` — get last run date per agent_slug

**Step 2 — Compose the directory**

Read `.claude/agents/` for the live roster — that folder is the source of truth,
and its `description:` line is exactly what decides who picks a request up. Do NOT
hand-type a roster into this file; it went stale last time and listed specialists
that had been retired.

For each: name, what it is for, the kind of request that reaches it, last run date.
Group by domain for readability.

**Step 3 — Single agent mode**
If a name is given, read `agents/{agent-slug}/system-prompt.md` and produce a
detailed profile: full capability description, the kinds of request that reach it,
what it reads, what it writes, its strengths and blind spots.

## Output format

```
─── Metis Specialist Directory — [YYYY-MM-DD] ───────────────

RESEARCH & PHD
──────────────
Librarian           Find papers, reference metadata, source verification.
                    Reached by: "find papers on…", "is there a review of…"
                    Last run: [date or never]

PhD Architect       Thesis structure, article-to-chapter alignment, gap
                    analysis. Reached by: "help me structure my thesis"
                    Last run: [date]

[…one block per specialist found in .claude/agents/, grouped by domain…]

──────────────────────────────────────────────────────────────
Total specialists: [count from .claude/agents/]
To reach one: just describe the work — it picks itself up.
To insist:    @agent-name [your request]
Not sure?     /metis [your request]
```

## Edge cases
- Specialist has never been run: show "never" for last run, not an error
- Single agent mode: read `agents/{slug}/system-prompt.md` for a 15-line deep profile
- "which agent for X": infer from the request, name the specialist and say in one
  line why — then note that simply asking for X would have reached it anyway
