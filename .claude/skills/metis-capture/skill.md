---
name: Metis Capture
description: "capture, quick capture, save this, capture a thought, capture idea, capture task, capture note, add to inbox, log this, I want to save, quick add, capture from terminal, save for later, remember this"
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
- `i:` → `save_idea(content, source="cli-capture", tags="cli")`
- `n:` → `save_personal_note(content, source="cli-capture")`
- `t:` → `create_task(title=content, project="inbox", priority="medium", source="cli-capture")`
- `q:` → `save_idea(content, source="cli-capture", tags="question,cli")`

**Step 3 — Confirm**
Return a single-line confirmation with what was saved and where.

**Step 4 — Do not log** (too lightweight to track as an agent run).

## Output format

```
✓ Captured [type]: "[first 60 chars of content]"
  Saved to [table] · [timestamp]
  
  To review: /metis_inbox | Dashboard capture: Today tab
```

Keep it one line if possible. Never show an error without a recovery path ("could not save — try /metis_ideas instead").
