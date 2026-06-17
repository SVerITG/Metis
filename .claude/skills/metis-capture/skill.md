---
name: Metis Capture
description: "capture, quick capture, save this, capture a thought, capture idea, capture task, capture note, add to inbox, log this, I want to save, quick add, capture from terminal, save for later, remember this, new idea, add idea, save idea, I had an idea, I just thought of, log idea, add note, quick note, personal note, write a note, note to self, journal entry, save a thought, metis ideas, metis notes"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

One-command capture from the terminal — same prefix routing as the dashboard capture modal. Saves immediately to the correct table without opening any UI. The fastest way to not lose a thought while working in Claude Code.

## What to do when invoked

**Usage:** `/metis_capture [prefix:] [content]`

Prefix routing (same as the dashboard capture modal):
- `i: [text]` — idea → saves to `ideas` table
- `n: [text]` — note → saves to `personal_notes` table
- `t: [text]` — task → saves to `tasks` table (inbox project)
- `q: [text]` — question → saves to `ideas` table with tag `question`
- No prefix → treated as a note, saved to `personal_notes`

Examples:
- `/metis_capture i: What if the elimination threshold depends on population density?`
- `/metis_capture t: Review clustering script for Article 2 methods section`
- `/metis_capture n: Passive screening in the study region shows plateau effect since 2020`
- `/metis_capture q: Is the diagnostic test sensitivity adequate for post-elimination surveillance?`

**Step 1 — Parse prefix**
Extract the prefix (first 2 characters before `: `). Default to `n:` if none present.

**Step 2 — Route and save**
- `i:` → `capture_idea(content=content, source="cli-capture")` then optionally `cross_pollinate(content=content)` for 2–3 quick connections
- `n:` → `add_journal_entry(content=content)`
- `t:` → `create_task(title=content, project="inbox", priority="medium")`
- `q:` → `capture_idea(content=content, source="cli-capture")` (tag the entry as a question)

This skill is the single capture entry point — it replaces the former `/metis_ideas` (use `i:`) and `/metis_notes` (use `n:`).

**Step 3 — Confirm**
Return a single-line confirmation with what was saved and where.

**Step 4 — Do not log** (too lightweight to track as an agent run).

## Output format

```
✓ Captured [type]: "[first 60 chars of content]"
  Saved to [table] · [timestamp]
  
  To review: /metis_inbox | Dashboard capture: Today tab
```

Keep it one line if possible. Never show an error without a recovery path ("could not save — try the dashboard Today tab instead").
