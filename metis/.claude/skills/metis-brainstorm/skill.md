---
name: Metis Brainstorm
description: "brainstorm, cross-pollinate, connect ideas, find connections, brainstorm about, explore connections, what connects, metis brainstorm, start a brainstorm, brainstorm session"
model: claude-sonnet-4-6
effort: thorough
complexity: standard
---

## Purpose

Activate a cross-pollination brainstorm session. Load rich context from the RC (ideas, papers, meetings, news) and surface non-obvious connections around a topic.

This is the manual entry point for cross-pollination — it does NOT run automatically. Call it when you want to think out loud with Metis.

## What to do when invoked

**Usage:** `/metis_brainstorm [topic or idea]`

**Step 1 — Clarify scope** (if no topic given)
Ask: "What would you like to brainstorm about? Or paste an idea and I'll find connections."

**Step 2 — Load context from RC**

Pull from the following sources via MCP tools:
- `search_notes(query=topic, limit=10)` — relevant ideas
- `search_literature(query=topic, limit=8)` — relevant papers
- `get_research_context()` — active research articles
- `get_project_status()` — active projects
- Recent meetings (last 30 days) from `get_daily_insight()`

**Step 3 — Cross-pollinate**

Analyse all loaded context together. Produce:
1. **3–5 non-obvious connections** — what does this topic share with something unexpected?
2. **Open tensions** — what contradictions or gaps does this topic reveal in your current work?
3. **Actionable next steps** — specific things to explore, write, or test
4. **One wild card** — a connection that seems unlikely but might be generative

**Step 4 — Capture**

If the user finds a connection interesting:
- Offer to `capture_idea(content=...)` to save it
- Offer to `cross_pollinate(content=...)` to go deeper

## Output format

```
─── Brainstorm: [topic] ─────────────────────
Date: YYYY-MM-DD

Context loaded:
  Ideas: N  · Papers: N  · Articles: N  · Projects: N

Connections
───────────
1. [Connection name]
   [2-3 sentences explaining the link]

2. …

Tensions
────────
[What this topic pushes against in your current work]

Next steps
──────────
- …

Wild card
─────────
[The unexpected one]
─────────────────────────────────────────────
```

## Edge cases
- No MCP connection: work from what the user has shared in the conversation; note that RC context wasn't loaded
- Very broad topic ("everything"): ask to narrow to a research question, project, or paper
- User asks for a saved brainstorm: check `get_brainstorm_sessions()` and summarise the last relevant one
