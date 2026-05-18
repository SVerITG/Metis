---
name: Metis Research
description: "research session, work on article, open article, research context, load article context, PhD article, article review, start writing, continue writing, metis research, work on my thesis"
model: claude-sonnet-4-6
effort: thorough
complexity: standard
---

## Purpose

Start or continue a research session. Load the full context for a specific article or research topic: methodology, tracked files, related papers, recent meetings, and open tasks.

## What to do when invoked

**Usage:** `/metis_research [article name or topic]` or `/metis_research` (shows active articles)

**If no article specified — show active articles:**
1. Call `get_research_context()` — list active articles with status + next steps
2. Ask: "Which article do you want to work on?"

**If article specified:**

**Step 1 — Load project context**
- `get_research_context(article=name)`
- `scan_tracked_files()` — checks only watched checkpoint files (PLANNING.md per project). Report any that changed since last session.
- Read the project's `PLANNING.md` via `read_file(path)`:
  - My Research Project: `/mnt/c/Users/{username}/[path-to-research-project]/PLANNING.md`
  - My Dataset Analysis: `/mnt/c/Users/{username}/[path-to-analysis]/PLANNING.md`
  - My Statistics Course: `/mnt/c/Users/{username}/[path-to-course]/PLANNING.md`
- `get_tasks(project=article_name, status="open")` — open tasks

**Step 2 — Check for new developments**
- Any changes flagged in PLANNING.md since the last session?
- Were any related papers published since the last session? (`get_new_publications()`)
- Were there recent meetings that mentioned this article?

**Step 3 — Present context**

Format: compact research brief the user can paste into their writing context or use directly in this conversation.

**Step 4 — Offer actions**
After presenting context, offer:
- "Want me to review your latest draft?"
- "Shall I check the methodology for gaps?"
- "Any specific section you're working on?"

**Step 5 — End of session: update PLANNING.md**
After completing meaningful work in a project session, update the project's PLANNING.md:
- Set "Last session" to a 2–3 line summary of what was done (date + key changes)
- Update "Key files recently changed" if files were modified
- Revise "Next steps" to reflect what's left
- Update the "Last updated" date at the bottom

Use `read_file()` to read it first, then use the Edit tool to update it.

---

## PLANNING.md workflow

**The PLANNING.md is the project's working memory.** It bridges sessions:
- Metis updates it at the end of every session
- You update it when working directly in the project (outside of Metis)
- `scan_tracked_files()` detects when it changed, so Metis knows to read it

**When you work outside Metis:** Add a brief note to PLANNING.md under "Last session" and "Key files recently changed". One or two lines is enough. Example:
> *2026-04-07: Updated analysis script with new dataset, revised key output figures.*

---

## Output format

```
─── Research Session: [Article title] ────────────────
Date: YYYY-MM-DD

STATUS: [draft / under review / revision / submitted]
LAST ACTIVITY: [date]

PLANNING NOTE (from last session)
───────────────────────────────────
[Summary from PLANNING.md — what was done, what changed]

METHODOLOGY SNAPSHOT
────────────────────
[2-3 key method details]

OPEN TASKS
──────────
[Task | Due]

NEW SINCE LAST SESSION
───────────────────────
[Publications / meetings / file changes]
──────────────────────────────────────────────────────
```

## Edge cases
- Article not in RC: ask if they want to add it first via Librarian
- Multiple articles with similar names: show a short list and ask which one
- User asks for a literature search: hand off to Librarian
- PLANNING.md not found: tell the user it should be at the project root, offer to create it
