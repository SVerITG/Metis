---
name: Metis PhD
description: "PhD, thesis, article status, PhD progress, dissertation, article alignment, PhD plan, next PhD milestone, thesis structure, research program, article 1, article 2, article 3, phd framework, elimination, post-elimination, HAT"
model: claude-sonnet-4-6
effort: normal
complexity: standard
---

## Purpose

A focused PhD status brief: article progress, thesis alignment, next milestone, and open questions. Equivalent to the Planner PhD focus board in the CLI. Designed to give a clear-headed summary of where the PhD stands without needing to open any dashboard.

## What to do when invoked

**Usage:** `/metis_phd`
**Optional:** `/metis_phd article-1` (or `article-2`, `article-3`) — deep-dive on one article

**Step 1 — Pull PhD data**
- `get_project_status()` — find `phd-framework` project
- `get_tasks(project="phd-framework")` — PhD-tagged tasks
- `get_tasks(project="passive-screening-drc")` — passive screening article tasks
- `get_tasks(project="hat-dashboard")` — HAT dashboard article tasks
- `get_notes(tags="phd")` — any PhD-tagged notes from the last 14 days

**Step 2 — Read the PhD framework PLANNING.md**
Path: `C:/Users/sverschaeve/OneDrive - ITG/Documents/5. Scientific/20. Framework/PLANNING.md`
Extract: thesis topic summary, article titles, alignment status per article, most time-pressured item.

**Step 3 — Check PhD domain notes**
Read `knowledge/domains/phd/` for any thesis backbone, article alignment, or gap notes. Surface anything updated in the last 7 days.

**Step 4 — Compose the brief**

Structure:
1. **Thesis headline** — one sentence on what the PhD argues
2. **Articles status** — for each of the 3 articles: title snippet + status (draft / submitted / in-review / published) + next concrete action
3. **Most urgent item** — single call-to-action for the next work session
4. **Open questions** — at most 3 unresolved methodological or structural questions worth addressing soon
5. **PhD-tagged tasks** — any open tasks relevant to PhD work

**Step 5 — Log**
`log_agent_run([], "phd-architect", "PhD status brief", "phd-framework/PLANNING.md", "outputs/reviews/phd-architect/...")`

## Output format

```
─── PhD Status — [YYYY-MM-DD] ──────────────────────────────

THESIS: Post-elimination surveillance of HAT — [one-line argument]

ARTICLE 1  [passive-screening-drc]
  Status: DRAFT
  Next: [concrete next step from PLANNING.md]

ARTICLE 2  [hat-dashboard]
  Status: IN PROGRESS
  Next: [next step]

ARTICLE 3  [hat-clustering]
  Status: PLANNED
  Next: [next step]

MOST URGENT
  → [one clear call to action for today's session]

OPEN QUESTIONS
  1. [methodological or structural question]
  2. [question]

PHD TASKS  (n open)
  · [task title]  [priority]
─────────────────────────────────────────────────────────
```

Do not invent article titles or thesis arguments. Read them from PLANNING.md and domain notes. If PLANNING.md cannot be read, say so and report only what the DB yields.
