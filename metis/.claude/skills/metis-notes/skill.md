---
name: Metis Notes
description: "add note, quick note, personal note, write a note, note to self, journal entry, save a thought, metis notes, log this, remember this for me, I want to write"
model: claude-sonnet-4-6
effort: normal
complexity: quick
---

## Purpose

Add a personal note or view recent notes. The Notes tab in the dashboard stores journal entries, reflections, and free-form thoughts. This skill is the Claude Code / Claude Desktop entry point.

## What to do when invoked

**Usage:** `/metis_notes [note text]` or `/metis_notes` (view recent)

**Add a note (text provided):**
1. Capture the note: `add_journal_entry(content=text)`
2. Confirm: "Note saved — [date] · [first 60 chars]"
3. If the note sounds like an idea in disguise, offer to also `capture_idea(content=text)`

**View recent notes (no text, or user says "show notes"):**
1. Call `get_journal(n=7)` — show last 7 entries
2. Display compact list: date · mood · first 80 chars

**Add a meeting note:**
If the note starts with "Meeting:" or "Met with" or references a meeting:
- Route to Meeting Memory instead: "This sounds like a meeting note — want me to use `/meeting-memory` to structure it properly?"

## Output format

Add note:
```
Note saved ✓  [YYYY-MM-DD HH:MM]
"[first 80 chars of content]…"
```

View notes:
```
Recent notes
────────────────────────────────────
[YYYY-MM-DD]  [mood emoji]  [preview]
[YYYY-MM-DD]  [mood emoji]  [preview]
…
────────────────────────────────────
```

## Edge cases
- No RC connection: tell the user the note can't be saved to the database; suggest copying to inbox/ as a .txt file
- Note references a patient or individual by name: flag as potentially CONFIDENTIAL before saving
