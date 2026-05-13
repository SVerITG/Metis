---
title: Metis Token Guardrails
type: policy
version: 1.0
created: 2026-04-03
---

# Metis Token Guardrails

## Why this exists

Frontier models are getting more capable and more expensive with each generation. The mistakes that are tolerable today at current pricing become costly at 10x pricing. Token waste is not a model problem — it is a habits problem. This document codifies the rules that keep Metis efficient, so that every token burned is a smart token.

---

## Rule 1 — Document format

**Always convert source documents to markdown before feeding them to any agent.**

Raw PDFs, DOCX, XLSX, and HTML carry formatting overhead that can inflate token count 10–20x. A 4,500-word PDF can become 100,000+ tokens if fed as a raw binary. The same content as clean markdown is 4,000–6,000 tokens.

- Use `claude` directly, or any free online converter to produce clean `.md` before adding to inbox
- Never drag raw PDFs into a conversation when text content is what you need
- Screenshots are also inefficient — copy-paste text when possible

---

## Rule 2 — Conversation freshness

**Start a fresh session every 10–15 turns.**

Every turn in a conversation resends the entire conversation history. Long-running conversations cause:
- Context window fill-up (compressing or losing earlier instructions)
- Model drift (anchoring on recent turns rather than original instructions)
- Silent token accumulation (each turn costs more than the last)

> If you need to think through something evolving, use a separate "thinking" chat. Once you have a conclusion, start a clean session to do the actual work.

---

## Rule 3 — Model selection

**Match the model to the cognitive load of the task. Never default to Opus for everything.**

| Task type | Model | Rationale |
|-----------|-------|-----------|
| Formatting, proofreading, polish | Haiku | Simple tasks; Opus is overkill |
| Standard research, analysis, writing | Sonnet | Best cost-quality balance for most work |
| Deep reasoning, PhD synthesis, complex architecture | Opus | Reserve for what genuinely needs it |
| Chain workflows (plan → execute → polish) | Opus → Sonnet → Haiku | Split by cognitive load per stage |

This matches the complexity tiers in the Metis routing contract (`complexity: quick | standard | deep`).

### Per-agent model assignments (reviewed 2026-04-03)

| Agent | Model | Rationale |
|-------|-------|-----------|
| **Metis** (routing) | claude-sonnet-4-6 | Routing needs reasoning but not deep synthesis |
| **Librarian** | claude-sonnet-4-6 | Complex paper analysis; Sonnet is sufficient |
| **News Radar** | claude-haiku-4-5-20251001 | Simple summarization of structured feed content |
| **News Aggregator** | claude-haiku-4-5-20251001 | Feed triage and signal tagging — fast + cheap |
| **Meeting Memory** | claude-haiku-4-5-20251001 | Transcript formatting; no deep reasoning needed |
| **Learning Coach** | claude-haiku-4-5-20251001 | Progress tracking and gap identification |
| **Career Coach** | claude-haiku-4-5-20251001 | Reflective prompts; Haiku handles well |
| **Data Guardian** | claude-haiku-4-5-20251001 | Pattern matching only — fast is correct |
| **Cybersecurity** | claude-haiku-4-5-20251001 | URL validation, injection patterns — rule-based |
| **HR/Talent** | claude-haiku-4-5-20251001 | Identifies missing agent slots — lightweight |
| **Writing Partner** | claude-sonnet-4-6 | Drafting quality; Sonnet produces good prose |
| **Research Architect** | claude-sonnet-4-6 | Article tracking; Sonnet sufficient |
| **Presentation Maker** | claude-sonnet-4-6 | Slide structure; Sonnet handles layout well |
| **UX Engineer** | claude-sonnet-4-6 | Design system; Sonnet for CSS/UI decisions |
| **Methods Coach** | claude-sonnet-4-6 | Statistical methods; upgrade to Opus for PhD-level synthesis |
| **Epidemiologist** | claude-sonnet-4-6 | Study design critique; upgrade to Opus for full Socratic depth |
| **Software Engineer** | claude-opus-4-6 | Code quality and architecture — Opus required |
| **RC Builder** | claude-opus-4-6 | Building Metis itself — architecture decisions |
| **Dashboard Engineer** | claude-opus-4-6 | Complex UI logic and React/Shiny patterns |

**Note on Methods Coach and Epidemiologist:** Sonnet is the default. For deep PhD-level methodology review or full Socratic dissertation critique, switch to Opus. These are the two agents most likely to benefit from Opus on complex requests.

---

## Rule 4 — Tool loading

**Load only the MCP tools an agent actually needs for the task at hand.**

Every MCP tool registered in a session contributes to context overhead. Loading 20 tools when 3 are needed means paying a silent tax on every turn.

- When calling an agent directly, pass only the `context` and `priority` it needs
- Audit the MCP tool list quarterly — drop tools that are not actively used
- Do not add new MCP connectors "because they might be useful" — add them when you have a concrete use case

---

## Rule 5 — Web search via dedicated MCP

**Use Perplexity MCP (or another dedicated search service) instead of native Claude web search.**

Native Claude web search tends to burn 10–50K more tokens per search session than a dedicated search MCP. Perplexity also returns structured citations, which saves post-processing work.

- Set up a Perplexity MCP connector for research-heavy sessions
- Use native Claude search only when the MCP is unavailable or the query requires browser navigation

---

## Rule 6 — Cache stable context

**All stable context must use prompt caching when calling the API.**

Prompt cache hits cost ~90% less than standard input tokens on Anthropic's API. Anything that does not change between sessions should be cached:

- Agent system prompts
- Tool definitions
- Reference documents (ontology, domain summaries, security policy)
- PhD backbone and thesis structure

If you are building or extending a pipeline that calls agents programmatically, set `cache_control: {"type": "ephemeral"}` on stable blocks. This is the highest-leverage, lowest-effort optimization available.

---

## The 5 Agent Commandments

These apply when building, modifying, or invoking any Metis agent:

### 1. Index your references
Never dump a raw document set into an agent's context. The MCP tools (`search_notes`, `search_literature`, `get_phd_context`) exist to retrieve only the relevant slice. Use them. An agent that starts by reading 50 files is failing before it begins.

### 2. Pre-process your context
Documents must arrive in an agent's context ready to be used — not ready to be read, cleaned, or processed. Pre-summarize, pre-chunk, pre-convert to markdown. If the first 2,000 tokens of an agent run are spent on housekeeping, something went wrong upstream.

### 3. Cache stable context
System prompts, tool definitions, persona instructions, and reference material that does not change between sessions must be cached. Making thousands of agent calls per week without caching is pouring money down the drain. (See Rule 6.)

### 4. Scope every agent's context to the minimum it needs
A planning agent does not need your full codebase. An editing agent does not need the project roadmap. An epidemiology agent does not need the cybersecurity allowlist. Pass context surgically. Models perform worse when drowning in irrelevant content — this is a quality issue, not just a cost issue.

### 5. Measure what you burn
Log `input_tokens`, `output_tokens`, and `model` for every agent run via `log_agent_run`. You cannot improve what you do not measure. The Metis dashboard can surface this over time — use it to spot drift.

---

## When you are unsure

If you are not sure whether a task warrants Opus vs Sonnet, start with Sonnet. Upgrade if the output quality is insufficient. Downgrading after the fact costs nothing.

If you are not sure how much context to pass, pass less. An agent can always ask for more. Passing too much can never be undone within the same turn.

If you are not sure whether a document needs markdown conversion, convert it anyway. The cost of conversion is seconds. The cost of skipping it compounds for the entire session.

---

## Audit checklist (run quarterly)

- [ ] Review all MCP tools — drop any unused in the past 90 days
- [ ] Prune agent system prompts — remove instructions that were written for older model generations
- [ ] Check `agent_runs` table — identify agents with unusually high token cost per run
- [ ] Verify prompt caching is active on all stable context in any programmatic pipelines
- [ ] Review `inbox` — ensure documents entering the RC are in markdown format

---

## Auto-handoff (Phase 8.13 — added 2026-04-25)

Long-running sessions with Opus risk silent context exhaustion: the conversation history fills, costs climb, and quality degrades before the user notices. Metis has two layers of defence.

### Layer 1 — Visible token pulse

The Today tab's ledger now includes a **TOKENS · TODAY** cell that surfaces the rolling 24-hour total of `input_tokens + output_tokens` across all `agent_runs`. The cell colour changes with budget tier:

| Tier  | Threshold       | Colour              | Behaviour                      |
|-------|-----------------|---------------------|--------------------------------|
| muted | < 1k            | muted               | "—" placeholder                |
| ok    | 1k – 500k       | info-blue           | normal                         |
| warn  | 500k – 1M       | ochre / amber       | visual warning                 |
| alert | > 1M            | alert / red         | gentle pulse animation         |

The pulse animation is decorative — no nagging modals — and respects `prefers-reduced-motion`.

### Layer 2 — `generate_handoff_brief` MCP tool

A handoff brief can be produced at any time (programmatically or via the user calling the `/metis_handoff` skill) by invoking `generate_handoff_brief(session_id?)`. The tool reads recent `session_events`, active projects, open tasks, files touched in the session, and the current `implementation-progress.json` state, and writes a portable markdown brief to `metis/journal/YYYY-MM-DD_session_handoff.md`. The next session can resume from that file without paying to re-load the full conversation history.

### Trigger policy

- The handoff is **manually callable** as of v8.2 — call it deliberately when a session approaches its end, when the token-pulse cell turns amber, or before `/clear`.
- An automatic trigger inside `pipeline.py` (fire `generate_handoff_brief` when `turn_count >= 0.8 * max_turns`) is the next planned step. It is not enabled yet because the pipeline change needs careful review against the existing turn counter.

### Best-practice interleave

Pair the handoff with `/clear`:

1. Watch the token cell. If it crosses 500k, finish the current task cleanly.
2. Call `generate_handoff_brief()` — it writes the brief and returns the path.
3. `/clear` the session.
4. The next session reads `metis/journal/YYYY-MM-DD_session_handoff.md` first, gets oriented in seconds, and continues with a clean context window.

This is how Metis stays affordable on Opus across multi-day workstreams.
