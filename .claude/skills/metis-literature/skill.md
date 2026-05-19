---
name: Metis Literature
description: "literature, library search, find paper, references, bibliography, search papers, search literature, library status, Zotero, what papers do I have, find citation, literature search, recent papers, literature query"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

Quick CLI access to the Metis literature library — search papers, check Zotero sync status, find citations. Equivalent to the Knowledge tab's literature table. Accepts a search query or returns a summary of recent additions if no query is given.

## What to do when invoked

**Usage:** `/metis_literature` or `/metis_literature [query]`

Examples:
- `/metis_literature` — recent additions, library stats
- `/metis_literature HAT passive screening` — search for papers matching these terms
- `/metis_literature 2024 surveillance` — filter by year and topic

**Step 1 — Pull library data**
- `get_library_cards(limit=5, order_by="created_at DESC")` — most recent additions (no query)
- OR: `search_library(query="{user_query}", limit=10)` — if a query was given
- `get_literature_metadata(limit=3, order_by="created_at DESC")` — recent literature records

**Step 2 — Library stats (no-query mode only)**
- Total `library_cards` count
- Total `literature_metadata` count  
- Most recent addition date
- Domain breakdown (top 3 domains by count)

**Step 3 — Compose output**

For search results: show each paper as title | authors | year | source | tags. Flag if no abstract/summary is available.
For no-query mode: show stats + 5 recent additions + a prompt to search.

**Step 4 — Do not log** (read-only, lightweight).

## Output format

**Search mode:**
```
─── Literature search: "[query]" — n results ───────────────

1. [Title]
   [Authors] · [Year] · [Source]
   Tags: [tags]
   [Summary snippet if available]

2. ...
─────────────────────────────────────────────────────────
Tip: use /librarian to run a full systematic search
```

**No-query mode:**
```
─── Literature library — [YYYY-MM-DD] ──────────────────────

Library cards:   n total · last added [date]
Literature refs: n total
Top domains:     HAT (n) · methods (n) · AI (n)

RECENT ADDITIONS
  [Title] — [Authors] ([Year])
  [Title] — [Authors] ([Year])
  ...

Search: /metis_literature [your query]
Full search: /librarian [query]
─────────────────────────────────────────────────────────
```

Do not hallucinate paper titles or authors. Only show what the DB returns.
