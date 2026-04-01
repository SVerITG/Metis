---
# Session Log — 2026-03-28

## Summary

Monia is promoted from a general coordinator to the explicit single entry point for the entire agent ecosystem. The session rewrites Monia's system prompt and contract to encode a formal five-step Routing Protocol, a full routing table, a complexity model (quick/standard/deep/chain), and a Recording Protocol. CLAUDE.md is updated so `/monia` is documented as the default entry point — users no longer need to know which agent handles what. The dashboard Agents tab gains expanded quick-invoke templates. The data layer gains an `agent_runs` table and `log_agent_run()` function so every substantive agent output is traceable from the dashboard. Seventeen output directories are created under `07_outputs/reviews/` to receive agent output files.

## Changes Made

| File | Type | Description |
|------|------|-------------|
| 02_agents/metis/system-prompt.md | MODIFIED | Full rewrite: 5-step Routing Protocol, routing table, complexity model (quick/standard/deep/chain), Recording Protocol with output file template and DB logging rules |
| 02_agents/metis/contract.md | MODIFIED | Rewrite: Monia now explicitly owns routing decisions, complexity assessment, and PKM recording; added complexity table with model hints; added recording mandate |
| CLAUDE.md | MODIFIED | `/monia` documented as default entry point; multi-agent routing example added; complete workflow diagram (Dashboard → Claude Code → Agent → Output → Dashboard); complexity levels table; "How invocation works" section replaced with Option A (Monia routes) / Option B (direct call) |
| R/mod_agents.R | MODIFIED | Monia quick-invoke templates expanded: general request, morning briefing, full paper review chain, triage, weekly review, "what am I overlooking?" |
| R/data_store.R | MODIFIED | `agent_runs` table added to DB schema (agent_slug, task_summary, input_path, output_path, status, created_at); `log_agent_run()` function added |
| 07_outputs/reviews/ | ADDED | 17 subdirectories created — one per agent slug — to receive output files written by agents during runs |

## Decisions Made

- Decision: `/monia` promoted to single default entry point for all agent requests
  Rationale: Users were required to know the agent taxonomy before they could delegate work. Making Monia the universal router removes that cognitive barrier — any request can be directed to `/monia` and she determines the right agent(s), complexity, and execution plan.
  Alternatives considered: Keeping direct-agent calls as the primary interface (rejected — required user to maintain mental model of 18 agents); adding a routing UI in the dashboard (rejected — adds a layer of indirection that slows the primary interaction loop).

- Decision: Every substantive agent output is recorded to filesystem + database
  Rationale: Without systematic recording, agent work becomes ephemeral — it exists in a conversation window but is not traceable, searchable, or surfaceable in the dashboard. The `agent_runs` table + output files create a persistent, queryable audit trail.
  Alternatives considered: Record only on explicit user request (rejected — users will not remember to request recording consistently); record to database only without files (rejected — loses the full output content, which is needed for the Agents tab file preview).

- Decision: Routing announcement before execution ("Routing: [Agent]. Complexity: [level].")
  Rationale: Transparency on routing decisions lets the user correct Monia before work is done, and builds intuition about how the routing table works over time.
  Alternatives considered: Silent routing with post-execution summary (rejected — user cannot intervene if routing is wrong).

## Issues Encountered

None — this session was a documentation and configuration pass with no R code syntax risk. No parse errors expected.

## Next Steps

- [ ] Validate that `log_agent_run()` is called correctly after the first real agent run
- [ ] Confirm the 17 `07_outputs/reviews/` directories are correctly named (must match agent slugs used in the routing table)
- [ ] First real end-to-end test: `/monia Review my Article 1 draft` — verify output file appears in reviews/, run logged in agent_runs table, and dashboard Agents tab surfaces it
- [ ] Consider adding a "Recent agent runs" widget to the Control Room morning brief

## Data Rules Validated

- [ ] CATT and RDT calculated separately — N/A (no data processing changes)
- [ ] Year boundaries respected — N/A
- [ ] PS_Cases checked before test-based classification — N/A
- [ ] Positivity only from active screening — N/A
