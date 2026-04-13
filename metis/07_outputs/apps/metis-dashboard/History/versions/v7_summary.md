# Version 7.0 — 2026-03-28

## Theme: Metis as Universal Router

## Overview

v7.0 establishes Metis as the single, explicit entry point for the entire agent ecosystem. Prior to this version, using an agent required the user to know which agent to call — a 18-agent taxonomy that added cognitive overhead before any real work could begin. This version removes that barrier: `/metis [anything]` is now the documented default. Metis analyzes the request, selects agents, assesses complexity, announces her plan, executes, and records everything to the PKM automatically.

Two foundational infrastructure pieces are added: an `agent_runs` database table and a `log_agent_run()` function make every agent output traceable from the dashboard. Seventeen output directories under `07_outputs/reviews/` create a persistent, organized filesystem for all agent work products.

## New Features

- **Metis Routing Protocol**: Five-step protocol — analyze request, select agent(s), assess complexity, announce plan, execute and record. Metis now announces "Routing: [Agent]. Complexity: [level]." before any work begins, giving users the opportunity to correct routing before execution.
- **Routing table**: Full input-type to primary/secondary agent mapping encoded in Metis's system prompt. All 18 agents covered.
- **Complexity model**: Four levels with model hints — quick (haiku), standard (sonnet), deep (opus), chain (opus + subagents). Complexity is determined by Metis, not specified by the user.
- **Recording Protocol**: Output file template (`07_outputs/reviews/{agent-slug}/{YYYY-MM-DD}_{task-slug}.md`), DB logging rules, and a "never skip recording" mandate for reviews, analyses, and searches.
- **`agent_runs` SQLite table**: Schema — agent_slug, task_summary, input_path, output_path, status, created_at. One row per agent invocation.
- **`log_agent_run()` function**: CRUD helper in data_store.R. Called by Metis after every substantive run.
- **17 output directories**: `07_outputs/reviews/{agent-slug}/` — one per agent, pre-created and ready to receive output files.
- **Expanded Metis quick-invoke templates** (R/mod_agents.R): six templates — general request, morning briefing, full paper review chain, triage, weekly review, "what am I overlooking?".

## Files Changed

| File | Change type |
|------|-------------|
| 02_agents/metis/system-prompt.md | Full rewrite — Routing Protocol, routing table, complexity model, Recording Protocol |
| 02_agents/metis/contract.md | Rewrite — routing ownership, complexity table, recording mandate |
| CLAUDE.md | Default entry point documentation, workflow diagram, Option A/B invocation model, complexity levels table |
| R/mod_agents.R | Metis quick-invoke templates expanded (6 templates) |
| R/data_store.R | `agent_runs` table + `log_agent_run()` function |
| 07_outputs/reviews/ | 17 subdirectories created (one per agent slug) |

## Breaking Changes

None. Direct agent calls (`/librarian`, `/epidemiologist`, etc.) continue to work unchanged. The routing infrastructure is additive.

## Architectural Decisions

- ADR-018: Metis as single default entry point (see DECISIONS.md)
- ADR-019: Filesystem + database dual recording for agent runs (see DECISIONS.md)

## Known Limitations

- `log_agent_run()` must be called explicitly by Metis in each conversation — there is no automatic hook. If Metis forgets to call it, a run goes unrecorded. (Addressed by the recording mandate in Metis's system prompt, but not technically enforced.)
- The Agents tab in the dashboard reads output files from `07_outputs/reviews/` — it will correctly surface files as soon as they appear, with no dashboard changes required.

## Upgrade Notes

No cache rebuild required. No R module syntax changes. The `agent_runs` table will be auto-created on next app load via `init_db()` in data_store.R (assuming `init_db()` uses `CREATE TABLE IF NOT EXISTS` — standard pattern).
