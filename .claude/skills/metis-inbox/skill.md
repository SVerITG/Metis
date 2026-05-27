---
name: Metis Inbox
description: "inbox, check inbox, what's in inbox, process inbox, inbox items, route inbox, triage inbox, unprocessed items, metis inbox, inbox scan, what's waiting"
model: claude-sonnet-4-6
effort: normal
complexity: standard
---

## Purpose

Scans the `inbox/` folder for any unprocessed files or drops, and the `tasks` table for inbox-project items, then routes each one to the appropriate agent or surfaces it for user decision. The CLI equivalent of the "route inbox" Metis function.

## What to do when invoked

**Usage:** `/metis_inbox`

**Step 1 — Scan inbox folder**
`list_files(path="inbox/")` — list all files in `metis/inbox/`. For each file:
- Read the first 200 characters to classify content type
- Classify as: meeting note | paper/reference | idea | task | note | unclear

**Step 2 — Check DB inbox**
`get_tasks(project="inbox", status="open")` — any tasks captured to the inbox project (via `/metis_capture t:` or the dashboard modal).

**Step 3 — Route each item**

For each inbox file, propose a routing:
- `.md` meeting notes → Meeting Memory (`/meeting-memory`)
- PDF / `.bib` / citation text → Librarian (`/librarian`)
- Idea file or `.txt` brainstorm → Ideas table or Metis Brainstorm
- Code snippet or script → Software Engineer
- Unclear → ask one clarifying question

Do not auto-route without showing the user. Present the routing plan and confirm before acting.

**Step 4 — Process inbox tasks**
For each open inbox task:
- If it has a clear project → propose `update_task(project="[project-slug]")`
- If unclear → surface for user decision

**Step 5 — Log**
If any items were routed: `log_agent_run([], "metis", "Inbox scan and routing", "inbox/", "")`

## Output format

```
─── Inbox — [YYYY-MM-DD] ───────────────────────────────────

FILES IN inbox/  (n items)
  📄 meeting-notes-2026-04-24.md  → Route to /meeting-memory?  [y/skip]
  📄 passive-screening-notes.txt  → Route to /librarian?  [y/skip]
  ❓ misc-thoughts.md              → Unclear — what is this for?

INBOX TASKS  (n open)
  · "Review analysis script" → Assign to [project-slug]? [y/skip]
  · "Check citation"         → Assign to phd-framework?  [y/skip]

ACTIONS
  Reply with: y [number] to route, skip [number] to leave, or clear [number] to dismiss.
  
  Or: /metis_inbox route-all  — auto-route everything with obvious classification.
─────────────────────────────────────────────────────────
```

Do not auto-delete inbox files without explicit user confirmation. Propose the action and wait.
