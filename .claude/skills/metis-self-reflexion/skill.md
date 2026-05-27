---
name: Metis Self-Reflexion
description: "comprehensive self-audit of Metis; drift check; what did we lose; is everything still working; is Metis still future-proof; full system reflection; quarterly review; release readiness audit; persona consistency check; install experience check; memory health check"
model: claude-opus-4-7
effort: high
complexity: deep
---

## What this skill does

You are running a comprehensive, multi-section audit of the entire Metis system. This is the canonical way the user reflects on Metis at depth — "are we still future-proof, are all intentions followed, did we lose anything we built?"

Treat this as a multi-hour, multi-stream investigation. Do not rush. Do not skim. The user explicitly asked for this to exist precisely because they fear silent drift.

## Step 1 — Load the master prompt

Read in full:
- `system/config/metis-self-reflexion-prompt.md` — the canonical audit questionnaire (10 sections A–J)

This is the contract for what you must produce.

## Step 2 — Run the functional test harness

Execute the concrete promise check first, so you have hard data before subjective evaluation:

```bash
bash tests/functional/run_metis_promises.sh
```

This produces:
- A markdown report at `outputs/reviews/metis-evaluation/YYYY-MM-DD_promise-check.md`
- A pass/fail/warn line on stdout

Read the produced report. It is your evidence base.

## Step 3 — Dispatch parallel investigation streams

Spawn these as parallel sub-agents in a single message (use the `Agent` tool with `subagent_type="Explore"` for read-only investigation, `subagent_type="claude"` for stream owners who must synthesise):

1. **Vision alignment stream** — read README, CLAUDE.md, metis-persona.md, constitution.md, red-lines.md. Identify promises vs reality.
2. **Feature inventory stream** — for each promised feature in the README "What you get on day one" table and the changelog, locate it in code, render the relevant UI surface, classify as ✅ works / 🟡 partial / 🔴 broken / ⚫ ghost.
3. **Workflow integrity stream** — run each of the 7 workflows listed in Section C of the master prompt and report friction points.
4. **Memory system stream** — Section D of master prompt. Compare with mem0, Letta, MemGPT, native Claude memory features. Identify top 3 upgrades.
5. **Install experience stream** — pretend to be a non-technical senior researcher. Walk through README → install → first 30 minutes. Document every friction point.
6. **UI/UX polish stream** — render each tab. Score 8 dimensions per Section F. Concrete fix items.
7. **Security verification stream** — Section G. Walk every claimed layer and prove or disprove it from code.

Each stream returns a report. You synthesise.

**IMPORTANT — Logging Explore streams:** Explore subagents do NOT have MCP tool access and cannot call `log_agent_run`. After all streams complete, the orchestrating session (you, not the subagents) must call `log_agent_run` once per stream, with the stream slug and a brief summary of what it found. Do this before writing the drift heatmap. Stream slugs: `metis-audit-vision`, `metis-audit-features`, `metis-audit-workflow`, `metis-audit-memory`, `metis-audit-install`, `metis-audit-ui`, `metis-audit-security`.

## Step 4 — Build the drift heatmap

This is the centrepiece. Section I of the master prompt. A table:

| Feature | Promised in | First seen (git) | Last verified working | Status today | Action |

One row per major promise. Pull `git log` for first-seen dates. This is what answers the user's recurring fear: "have we lost things we built?"

## Step 5 — Write outputs

Three artifacts, all mandatory:

1. **Personal memory file** at:
   `~/.claude/projects/-mnt-c-Users-sverschaeve-OneDrive---ITG-Documents-7--Software-Research-Cortex/memory/evaluations/YYYY-MM-DD_self-reflexion.md`

2. **Project-side mirror** at:
   `outputs/reviews/metis-evaluation/YYYY-MM-DD_self-reflexion.md`

3. **Index update** — append a row to:
   `~/.claude/projects/.../memory/evaluations/INDEX.md`

The personal memory file must be self-contained — readable months later without context.

## Step 6 — Record findings into semantic memory

For the top 3 systemic observations, call:

```
store_semantic_memory(
  content="[Self-reflexion YYYY-MM-DD] <observation in 2-3 sentences>",
  tags=["metis-audit", "drift", "<section-tag>"],
  source="self-reflexion YYYY-MM-DD"
)
```

This way drift becomes part of the long-term memory rather than a one-off note. Use `search_memory(query="metis audit drift")` in future sessions to retrieve these.

## Step 7 — Reflexion

End with `write_reflexion()` for `agent_slug="metis-self-reflexion"`. Honest. Specific. What was hard to investigate? What evidence was missing? What tools would have made this faster?

## Voice and tone

This skill produces a serious systems report — but it is still Metis speaking. Refer to the user by name (`get_user_profile()`). When delivering the verbal summary at the end, plain language. Not "404 errors detected" — "five things the dashboard claims to do don't actually do them. Here are the most important to fix."

The drift table is for the dashboard. The closing summary is for the human.

## Edge cases

- If the dashboard is not running, start it (`bash system/app-py/run.sh`) before running checks.
- If the MCP server is not reachable, fall back to direct file / DB inspection and flag the MCP gap.
- If a previous self-reflexion ran in the last 7 days, do a *delta* audit — what changed? — rather than starting from scratch.
- If the user did not say "comprehensive" explicitly, ask once: "Full audit (~30 min) or quick delta against last reflexion?"
