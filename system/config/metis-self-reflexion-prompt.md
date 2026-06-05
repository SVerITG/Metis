# Metis Self-Reflexion — Master Audit Prompt

> **Purpose.** This is the canonical, re-usable prompt for comprehensively questioning Metis: is it still future-proof, are all stated intentions followed, does it still make sense, is it actually usable, has functionality drifted or been silently lost?
>
> **When to run.** Quarterly. Before any major release. Whenever the user feels something has been "lost." After any large refactor.
>
> **How to run.** Invoke `/metis-self-reflexion` in Claude Code. Or copy this entire file as the prompt for a fresh Claude session in the Research Cortex root.
>
> **Outputs to produce.**
> 1. A dated evaluation file in `~/.claude/projects/{project}/memory/evaluations/YYYY-MM-DD_self-reflexion.md`
> 2. A summary in `outputs/reviews/metis-evaluation/YYYY-MM-DD_self-reflexion.md` (visible in dashboard)
> 3. A run of the functional test harness `tests/functional/run_metis_promises.sh`
> 4. An updated entry in `memory/evaluations/INDEX.md`

---

## Operating principle

Treat this as a **drift audit** as much as a feature audit. The deepest failure mode for a long-lived system like Metis is not that something never worked — it is that something *used to work*, no one noticed it broke, and the promise still sits in the README. For every section below, ask both:

- **Promise check** — does the README / changelog / persona promise this?
- **Reality check** — does it actually work end-to-end today?
- **Drift check** — when did it last work? Is there evidence it ever did? Is it referenced anywhere from a UI surface a user could reach?

If a feature is built but not reachable from the UI, the user has lost it. Count that as broken.

---

## Trustworthy self-evaluation — how not to fool ourselves

An LLM auditing its own project is, by default, an unreliable judge. The evidence:
- Models **cannot intrinsically self-correct reasoning** and often *degrade* after self-revision when there is no external signal — Huang et al., *"LLMs Cannot Self-Correct Reasoning Yet"* (arXiv:2310.01798).
- LLM-as-a-judge carries **self-preference, position and verbosity bias** (arXiv:2410.21819; llm-judge-bias.github.io).
- Even AI *verifiers* are noisy; **hand-written deterministic checks** have far lower error than model judgment (SWE-bench correctness work, UTBoost arXiv:2506.09289).
- What works is **external grounding**: tool/test execution, ground truth, and an **independent verifier** (Reflexion; CRITIC arXiv:2305.11738).

This was proven here on 2026-06-04: an unverified pass reported **25 "failures"** (all a down-dashboard artefact) and **4 false "broken"** findings the verifier later refuted. Therefore every run of this audit obeys these rules:

1. **Run the external signal before asserting.** The harness, the tests, `py_compile`, a real `curl`. Deterministic checks beat model opinion.
2. **Every high/critical finding gets an independent verifier** — a fresh-context agent (ideally a *different model*) instructed to REFUTE it. Default to "refuted" on doubt; majority-refute kills it. The finder never grades itself (self-preference bias).
3. **Every finding carries an executable acceptance test** — "how would we *prove* it's fixed?" No acceptance test → hypothesis, not result.
4. **Score per-criterion with written justification**, not one holistic number (de-biasing). Severity cites file:line / command output.
5. **Preconditions first.** Confirm the dashboard is up before any HTTP/UI assertion (down = SKIP, not FAIL). The harness self-guards this.
6. **Only verified findings reach durable memory** (`store_semantic_memory`, `record_research_finding`). Expire unconfirmed self-critique rather than promoting it.
7. **Track drift as a time series** (`outputs/reviews/metis-evaluation/promise-trend.jsonl`) so regressions are visible across audits, not just within one.

---

## Section A — Vision and intention alignment

Read these four files in full before anything else:

1. `README.md` — the public promise
2. `CLAUDE.md` — the operating rules
3. `system/config/metis-persona.md` — the voice contract
4. `system/config/constitution.md` and `system/config/red-lines.md` — the behaviour gate

For each, ask:

- Is the current build consistent with this document?
- Are there contradictions between these four documents?
- Does any line make a promise we cannot keep today? (List them.)
- Has the persona drifted? Open three dashboard pages and read the visible English text — does it sound like a "warm research companion" or like dev copy?
- Are the constitution rules actually applied somewhere in the code? `grep` for them.

---

## Section B — Feature inventory and drift detection

For each line in the README's "What you get on day one" table, the Key Workflows section, and the changelog "Post-v1.0 improvements" + "v1.0" tables:

- Locate the feature in code (router / template / MCP tool / agent skill).
- Curl or render the relevant UI surface.
- Decide: ✅ works · 🟡 partial (UI present but data path broken or vice versa) · 🔴 broken (404 / error / mock data) · ⚫ ghost (advertised but no code).

Then build the **drift list**: every feature classified 🟡, 🔴, or ⚫. For each ghost feature, also report whether it was ever implemented (search git log for the feature name).

**Specific subsystems to inventory:**

| Subsystem | Inventory question |
|---|---|
| **34 specialist agents** | List `agents/*/skill.md`. For each, does an MCP tool or a skill file call it? Has it run in the last 90 days (`SELECT agent_slug, MAX(created_at) FROM agent_runs GROUP BY agent_slug`)? |
| **76+ MCP tools** | Run `tools/list` against the MCP server. Cross-reference with `system/mcp-server/src/metis_mcp/tools/*.py`. For each tool, is it called from at least one router, skill, or agent prompt? |
| **9 dashboard tabs** | For each tab, list HTMX partials and their hx-get URLs. Curl each. Note 404s. |
| **5 memory layers** | Run `metis_doctor()` or directly query: are episodic, semantic, procedural, working, reflexive tables non-empty? Has each been written to in the last 30 days? |
| **Self-improvement loop** | Are reflexions being written? Are proposals being drafted? Has any proposal been approved? When? |
| **Knowledge layers** | List indexed PDF knowledge databases. For each, chunk count > 0? Last build time? Are they actually retrieved by `search_pdf_knowledge()`? |
| **Specialist agents that should run automatically** | News Radar, Librarian morning sync, scheduled tasks. Are cron jobs / APScheduler running? Last execution? |

---

## Section C — End-to-end workflow integrity

Run each workflow as a real user would. Each workflow is a sequence of dashboard clicks or commands. Note any step that fails, takes too long, or produces empty output.

### C.1 Morning workflow
1. Open `http://127.0.0.1:8080/` → does the morning brief paragraph render?
2. Is the 7-metric ledger populated with real counts?
3. Click "resume last session" — does the handoff strip have content from the previous session?
4. Are overnight news items shown? Are they fresh (< 24h)?
5. Ctrl+K → type "i: test idea" — does it save AND surface cross-pollination connections?

### C.2 Literature review workflow
1. Drop a fresh PDF in `inbox/`. Run `scan_inbox()`.
2. Does it appear in Knowledge tab "Recently added"?
3. Ask via /metis: "What do my papers say about X?" — does it call PaperQA2?
4. Are citations returned with page numbers?

### C.3 Live meeting workflow
1. Click "Start Live Meeting" — does the setup modal render?
2. Choose Whisper mode — does it actually record and transcribe every 8s?
3. Speak domain-relevant words — do cross-pollination connections surface live?
4. Stop → does a structured note get saved with action items + project links?

### C.4 Voice capture workflow
1. Drop an audio file in `inbox/`.
2. Run `scan_inbox()` — does it auto-transcribe? Move to `inbox/processed/`?
3. Does the transcript appear as a new idea with cross-pollination tags?

### C.5 Writing / thinking workflow
1. Ctrl+K capture an idea.
2. Open Thinking tab — is the idea visible? Are connections shown?
3. Click "Brainstorm" launcher — does it actually open a brainstorm session?

### C.6 Teaching workflow
1. Open Teach tab → Course Builder.
2. Fill the intake form and submit.
3. Does a curriculum draft appear?
4. Is the course logged to `learning_courses` table?

### C.7 Self-improvement workflow
1. Run any agent (`/epidemiologist`, `/methods-coach`).
2. Was a reflexion written?
3. Run `aggregate_reflexions_tool()`.
4. Was a proposal drafted? Is it visible in the Metis tab → Self-improvement section?
5. Approve a proposal — does `apply_proposal_tool()` actually edit the skill file with a backup?

---

## Section D — Memory system health and future-proofing

The README claims a 5-layer memory system. Verify and compare against the state of the art.

### D.1 Layer-by-layer health
For each layer, report:
- Schema: which tables / files?
- Volume: row counts, recent activity
- Read path: which code reads from it? (grep)
- Write path: which code writes to it? (grep)
- Decay strategy: is anything pruned, summarised, or archived?

### D.2 Comparison with state of the art
Briefly assess:
- **mem0** — hierarchical user / agent / session memory with auto-consolidation. Does Metis do this?
- **Letta / MemGPT** — virtual context paging with explicit memory operations. Does Metis do this?
- **Anthropic Claude memory features (2026)** — what's available natively? Does Metis duplicate it unnecessarily?
- **Hippocampal-inspired architectures** — episodic-to-semantic consolidation. Does Metis do this?

Identify the top 3 upgrades that would meaningfully improve Metis's memory in the next quarter.

### D.3 Future-proofing
- Are model IDs hardcoded anywhere that would break on deprecation?
- Is the embedding model (nomic-embed-text-v1.5-Q) still SOTA, or has it been superseded?
- Are there newer MCP primitives (sampling, elicitation, etc.) Metis should adopt?

---

## Section E — Install and onboarding from a fresh user's perspective

Pretend you have never seen Metis before. You are a senior researcher with no programming background.

1. Land on the GitHub README. Within 60 seconds, do you understand what Metis does?
2. Follow the install instructions exactly as written. Document every step that requires technical knowledge the README didn't anticipate.
3. After install, what is the first screen you see? Is there guidance? Or just an empty dashboard?
4. Run the config wizard. Are the 13 sections clear, optional where they should be, and saving correctly?
5. On day one, what is the first useful thing the dashboard tells you?

Report every friction point with timestamp and quote.

---

## Section F — UI/UX professional polish

Render each dashboard tab. For each, score these dimensions (1–5):

- Visual hierarchy
- Typography consistency
- Spacing rhythm
- Dark / light mode parity
- Empty-state quality (does an empty Today look intentional or broken?)
- Error-state quality (when an endpoint 404s, is the user told something useful?)
- Mobile breakpoint behaviour
- Persona voice (is the copy warm and researcher-friendly, or dev-flavored?)

Append concrete fix items per tab.

---

## Section G — Security and data protection verification

The README makes strong claims. Verify each one against code.

- PII detection — open `system/mcp-server/.../safety.py`. Are all 14 checks present? Run a test against synthetic patient data.
- Injection probe — feed a known-bad string through an agent call. Was it blocked?
- Constitution — is it loaded for deep / chain runs? Show the loader.
- Red lines — show the code-level enforcement (`grep -r "RED_LINE\|red_lines"`).
- AES-256-GCM backups — run `encrypt_backup` and check the file.
- Ollama optional offline — does it actually fall back, or silently fail when the API key is missing?

---

## Section H — Token efficiency and economics

- Is model routing still smart? (Haiku triage, Sonnet main, Opus only deep.) Sample 10 recent runs from `agent_runs`.
- Is context assembled surgically per agent? Show one example trace.
- Is the handoff brief generated automatically near context limits?
- What does the token monitor say about cost per day? Is it sustainable?

---

## Section I — Drift heatmap

This is the final synthesis. Build a table:

| Feature | Promise location | First seen (git) | Last verified working | Status today | Action |
|---|---|---|---|---|---|
| (one row per major promise) | | | | | |

This table is the single most important output of the entire self-reflexion. It is the answer to the user's recurring concern: *"have we lost a lot of what we built?"*

---

## Section J — Recommendations and next sprint

Top 10 actions ranked by impact / effort. For each:
- Why it matters
- Estimated effort (S/M/L)
- Owner
- Acceptance test (how we know it's fixed)

---

## Closing — write to memory

Before ending the session:

1. Save full report to `~/.claude/projects/{project}/memory/evaluations/YYYY-MM-DD_self-reflexion.md`
2. Append a row to `memory/evaluations/INDEX.md`
3. Save a project-side mirror to `outputs/reviews/metis-evaluation/YYYY-MM-DD_self-reflexion.md` (visible in dashboard)
4. Call `record_research_finding()` with the top 3 systemic observations so the research timeline captures the drift
5. Call `write_reflexion()` for this run with `agent_slug="metis-self-reflexion"`

This way every future self-reflexion is retrievable, comparable, and contributes to the long-term picture of how Metis is evolving.
