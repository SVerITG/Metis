---
name: Metis Ideas
description: "capture idea, new idea, quick idea, add idea, idea capture, save idea, I had an idea, I just thought of, log idea, metis ideas"
model: claude-sonnet-4-6
effort: normal
complexity: quick
---

## Purpose

Quick idea capture with optional automatic connection detection. Works from Claude Code and Claude Desktop.

## What to do when invoked

**Usage:** `/metis_ideas [idea text]` or `/metis_ideas` (opens capture flow)

**If text is provided after the command:**
1. Capture immediately: `capture_idea(content=text, source="claude_desktop")`
2. Run `cross_pollinate(content=text)` to find 2–3 quick connections
3. Show the connections and ask if the user wants to explore any further

**If no text:**
1. Ask: "What's the idea?"
2. After they share it, capture + show connections as above

**Quick fields to infer** (don't ask unless unclear):
- `idea_type`: infer from content (research question / method idea / analysis approach / collaboration / paper concept / policy implication)
- `tags`: extract 2–3 key terms from the text automatically

**Show recent ideas** (if user says "what ideas have I had" or "show my ideas"):
- Call `get_ideas(limit=10)` and present a compact list with date + type

## Output format

```
Idea captured ✓
────────────────────────────────────
"[idea text]"
Type: [inferred type]
Tags: [auto-extracted]

Connections found:
  → [connection 1 — 1 sentence]
  → [connection 2 — 1 sentence]
────────────────────────────────────
```

## Edge cases
- Very long text: capture the first 500 chars, note truncation, offer to split
- Duplicate sounding idea: note it and ask if this is an update or a new angle
