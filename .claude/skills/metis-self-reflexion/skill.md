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

## Trustworthiness protocol (MANDATORY — read before dispatching anything)

Self-evaluation by an LLM is unreliable on its own: models cannot intrinsically self-correct reasoning and often *degrade* without an external signal ([Huang et al. 2310.01798](https://arxiv.org/abs/2310.01798)); LLM judges carry self-preference / position / verbosity bias ([2410.21819](https://arxiv.org/html/2410.21819v2)). The 2026-06-04 audit proved it: an unverified pass reported **25 "failures"** that were all a down-dashboard artefact, plus **4 false "broken"** findings the verifier refuted. So this audit is bound by seven rules (full text in the master prompt's "Trustworthy self-evaluation" section):

1. **Run the external signal before asserting** — harness, tests, `py_compile`, real `curl`. Deterministic > opinion.
2. **Every high/critical finding gets an independent verifier** — a fresh-context agent (ideally a *different model*) that tries to REFUTE it. Default to "refuted" on doubt; majority-refute kills it. The finder never grades itself.
3. **Every finding carries an executable acceptance test** ("how would we *prove* it's fixed?"). No acceptance test → it's a hypothesis, not a result.
4. **Score per-criterion with written justification**, not one holistic number. Severity must cite file:line / command output.
5. **Preconditions first** — confirm the dashboard is up before any HTTP/UI claim (down = SKIP, not FAIL). The harness now self-guards this.
6. **Only verified findings reach durable memory** (`store_semantic_memory` / `record_research_finding`). Expire unconfirmed self-critique.
7. **Append to the drift time-series** so regressions show across audits.

## Step 2 — Run the functional test harness

Execute the concrete promise check first, so you have hard data before subjective evaluation:

```bash
export METIS_RC_ROOT="$(pwd)"
bash tests/functional/run_metis_promises.sh
```

The harness now (a) **starts the dashboard if it's down** and SKIPs (never FAILs) HTTP/UI checks when it can't, (b) runs a deterministic **backend `py_compile`** floor and a **UI/a11y sanity** floor, and (c) appends this run to `outputs/reviews/metis-evaluation/promise-trend.jsonl`. It produces:
- A markdown report at `outputs/reviews/metis-evaluation/YYYY-MM-DD_promise-check.md`
- A ✅/🔴/🟡/⚪ summary line on stdout

Read the produced report. It is your evidence base. **If the summary shows ⚪ SKIP, the dashboard was down — do not treat those as failures; bring it up and re-run before judging UI.**

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

**Brief every investigator with the skeptic framing** (they over-claim otherwise — the 2026-06-04 streams rated four non-issues "critical/high broken"): *ground every finding in a file:line, command output, or DB query; severity must be defensible; run the external signal yourself before asserting; confirm the dashboard is up before any HTTP claim; prefer "works" unless you can prove otherwise.* Have each finding return a `severity`, an `evidence` (the exact command/file:line), and an **`acceptance_test`** ("how we'd prove it fixed").

**Step 3b — Mandatory verification pass (do NOT skip).** For every finding rated **high or critical**, spawn an *independent* fresh-context agent (ideally a different model) whose only job is to **REFUTE** it — re-run the exact check, default to "refuted" on uncertainty, return `confirmed | refuted | partial` + its own proof + a revised severity. A finding that is refuted (or majority-refuted if you use 3 voters) does **not** appear in the final report except as "investigated, not confirmed". This pass is the single most important quality control — it is what separates a trustworthy audit from a list of plausible-but-wrong claims. (A Workflow with `pipeline(streams, investigate, verify)` is the clean way to run it.)

**IMPORTANT — Logging Explore streams:** Explore subagents do NOT have MCP tool access and cannot call `log_agent_run`. After all streams complete, the orchestrating session (you, not the subagents) must call `log_agent_run` once per stream, with the stream slug and a brief summary of what it found. Do this before writing the drift heatmap. Stream slugs: `metis-audit-vision`, `metis-audit-features`, `metis-audit-workflow`, `metis-audit-memory`, `metis-audit-install`, `metis-audit-ui`, `metis-audit-security`.

## Step 4 — Build the drift heatmap

This is the centrepiece. Section I of the master prompt. A table:

| Feature | Promised in | First seen (git) | Last verified working | Status today | Action |

One row per major promise. Pull `git log` for first-seen dates. This is what answers the user's recurring fear: "have we lost things we built?"

## Step 5 — Write outputs

Three artifacts, all mandatory:

1. **Personal memory file** at:
   `~/.claude/projects/{project-hash}/memory/evaluations/YYYY-MM-DD_self-reflexion.md`
   *(The project hash is a machine-specific slug derived from your METIS_RC_ROOT path.
   Use `ls ~/.claude/projects/` to find the correct folder on your machine.)*

2. **Project-side mirror** at:
   `outputs/reviews/metis-evaluation/YYYY-MM-DD_self-reflexion.md`

3. **Index update** — append a row to:
   `~/.claude/projects/{project-hash}/memory/evaluations/INDEX.md`

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
