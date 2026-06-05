---
name: Research Mode
description: "research mode, look it up properly, check my library then the internet, deep answer, library first then web, complement with internet, research this question, what does the evidence say, answer from my library and the web, thorough answer linked to my work"
effort: normal
complexity: deep
---

## Purpose

The honest "library-first, then the web" answer. For a substantive question, Metis should **search your own library and work first**, and only **complement from the internet when there's a real gap — and with your OK** (Metis is local-first; the internet is not used silently). The answer is then **linked back to your work** — your projects, past findings, and indexed papers — and fully cited.

This packages the flow the platform *intends* but doesn't enforce automatically.

## The four moves (in order)

**1 — Recall your work (always).** Ground in what you already have:
```
surface_relevant_context(query="<question as a topic phrase>", limit=5)   # memory: past sessions, decisions, findings
```
Note any of the user's projects / ideas / prior findings the question touches — the answer will tie back to these.

**2 — Library first (the local floor).** Retrieve before answering, routing to the right layer (see `system/config/rag-routing-rules.md`):
```
search_pdf_knowledge(query="<specific phrase>", databases=[...], k=5)   # the indexed RAG library
search_fulltext("<terms>")                                              # keyword full-text over the library
# heavier, optional: ask_library("<question>")                          # PaperQA2 cited Q&A
```
Read what comes back. **If the library answers it well → answer from the library, cite page-level, link to the user's work, and stop.** No internet needed.

**3 — Assess the gap, then ASK before the internet.** If the library is thin, stale, or missing the specific point, say so plainly and **ask permission** before going online — e.g. *"Your library covers X but not the 2025 update on Y. Want me to pull that from the web (PubMed / open-access)?"* Do not fetch silently. (Red line: local-first; ask before general internet use. Never send the user's data to do a lookup.)

**4 — Complement, synthesise, link.** On approval, fill the gap with the real tools, then synthesise:
```
search_literature(query) / scan_openalex(query)     # find new papers/DOIs (Librarian)
# Content Harvester fetches + cleans open-access sources; respect paywalls (flag, don't bypass)
```
Write the answer so it **clearly separates** (a) what your **library** says — cited with page numbers, (b) what the **web** added — cited with URL/DOI, and (c) what is **inference**. Tie it to the user's own work: *"this bears on your Seroconversion record-linkage project / your 2026-06 finding on X."*

## After answering — close the loop

If the web turned up genuinely useful sources, offer to **make them permanent**:
> "These 3 papers filled a real gap — index them into your `hat-specialist` layer so they're in your library next time? (`/background extend`)"

This is the virtuous cycle: today's gap becomes tomorrow's library hit, so the internet is needed less over time.

## Non-negotiables
- **Local first, ask before web.** Never reach the internet without surfacing the gap and getting a yes.
- **Never send the user's data to look something up.** Queries are keywords/topics, not their documents (see `/safe-analysis`).
- **Cite everything; separate sources.** Library (page-level) vs web (URL/DOI) vs inference must be visible. Never present a web claim as if it came from the user's library.
- **No fabrication.** If neither the library nor an approved web search supports a point, say so.

## Collaboration
Librarian (literature search, indexing) · Content Harvester (fetch + clean web sources) · Background Maker (promote useful web finds into a permanent layer) · Critic (verify a synthesised claim) · Methods Coach / Epidemiologist (domain judgement).
