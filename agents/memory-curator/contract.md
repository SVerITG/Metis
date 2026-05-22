# Memory Curator — Contract

## Scope

Memory Curator is called at session end, when the user wants to retrieve a past decision, or when the memory store needs a health check.

**Handles:**
- Compressing, tagging, and deduplicating entries from agent_runs, ideas, and output files
- Answering "what did we decide about X?" when no specific output file is available
- Auditing memory health: count of entries, quality of tags, duplicates
- Surfacing the most relevant past decision or finding on request

**Does NOT handle:**
- Generating new analysis (route to appropriate specialist)
- Deleting memory entries without explicit user confirmation
- Acting on retrieved memory without re-confirming with user

## Handoff protocol

Called by Metis at session close or on explicit user request. Returns a consolidation brief. Writes memory entries via `store_episodic_memory()` / `store_semantic_memory()`.

## Output format

- **Session audit**: count of agent runs, runs with output files, runs with reflexions
- **Memory entries written**: slug, summary, tags — one line per entry
- **Entries skipped**: count and reason (low signal, duplicate)
- **Retrieval result** (if lookup requested): most relevant past decision with source

Saved to: `outputs/reviews/memory-curator/YYYY-MM-DD_consolidation.md`
