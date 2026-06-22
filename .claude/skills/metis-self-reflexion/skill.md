---
name: Metis Self-Reflexion
description: "comprehensive self-audit of Metis; drift check; what did we lose; is everything still working; is Metis still future-proof; full system reflection; quarterly review; release readiness audit; persona consistency check; install experience check; memory health check; would-we-build-it-this-way-again"
model: claude-opus-4-7
effort: high
complexity: deep
---

# Metis Self-Reflexion — Comprehensive Audit

This is the canonical, deep audit of the entire Metis system. It exists because the
user fears **silent drift** and because earlier versions of this audit *read code and
curled one endpoint* — they never clicked a button, never submitted fake PII, never
tested a promise from a second angle. A broken button on a surface sailed straight
through. **This version actually tests.**

Treat it as a multi-hour, multi-stream investigation. Do not rush. Do not skim.
Every "it works" is a trap: the moment you write it, that is the moment to test it
**from another angle, and then another.**

---

## The doctrine (read before anything)

1. **Test, don't read.** Reading code proves intent, not behaviour. Fire the endpoint, click the button, submit the data, follow the link. A claim with no executed test is a hypothesis.
2. **Eleven real testers, not eleven readers.** The streams below are *roles* — pen-tester, UX researcher, accessibility auditor, performance engineer, first-time user, senior researcher, data-protection officer, QA engineer, DevOps engineer, evidence-base reviewer — plus an **architect** who asks "would we build it this way again?". Each does what that professional actually does.
3. **Multi-angle verification.** Every high/critical finding is re-tested from a *different* angle by a *different* role (UX clicks the button → pen-tester checks the same endpoint's auth → QA confirms it maps to a README promise → perf times it). A finding only survives if it holds across angles. The finder never grades itself; the verifier defaults to "refuted" on doubt.
4. **Use synthetic data.** Dummy ideas, projects, meetings, PII-tainted CSVs, injection-laden pages, one known-good paper — from `tests/fixtures/`. Run the real workflows on fake data and check the outputs.
5. **Look it up, don't invent.** Before testing, pull current references from the web (OWASP, WCAG, "what breaks", SOTA benchmarks, testing taxonomies). Each reference must yield a concrete test you then run.
6. **Reimagine, don't only verify.** For every surface and subsystem, ask: *knowing what we know now — and that Claude keeps shipping (connectors, tools, scheduled tasks, the phone app) and that Metis must also serve non-Claude AI — would we build this the same way?* Capture forward-looking redesign recommendations.
7. **Question yourself at the end.** A separate meta-pass asks "what did we NOT test? where did we say 'works' without a test? what angle is missing?" — and that becomes the next round.
8. **Only verified findings reach durable memory.** Deterministic signal beats opinion. Append to the drift time-series so regressions show across audits.

> Edge case — if a full cycle ran in the last 7 days, ask once: full audit or delta? If the app is mid-redesign, say so and do not score in-progress surfaces as "broken" — flag them "in progress".

The trustworthiness rules from the master prompt (`system/config/metis-self-reflexion-prompt.md`) still bind: run the external signal first; independent verifier per high/critical finding; executable acceptance test per finding; per-criterion scoring with file:line evidence; preconditions (dashboard up) before any HTTP claim.

---

## Step 0 — External knowledge refresh (web)

Use WebSearch/WebFetch to pull the **current** version of each, and turn each into concrete tests for this run:

| Source | Yields |
|---|---|
| OWASP Top 10 (latest) + OWASP LLM Top 10 | the cybersecurity probe list (SQLi, XSS, CSRF, IDOR, SSRF, broken auth, prompt-injection, insecure output handling, excessive agency) |
| WCAG 2.2 AA checklist | the accessibility test list (contrast, focus, keyboard, ARIA, semantics) |
| "Common web app / FastAPI / HTMX failure modes" (Sentry/Bugsnag/known-issues) | the "what usually breaks" checklist |
| SOTA benchmarks — MTEB (embeddings), RAGAS (RAG), agent-eval leaderboards | whether Metis's embedding model / RAG / agent design is current |
| Software-testing taxonomy — ISTQB / IEEE-829 categories | confirm coverage of functional, integration, security, usability, performance, compatibility, regression, recovery |
| Anthropic docs — newest Claude connectors, tools, scheduled tasks, MCP primitives (sampling/elicitation), Claude mobile | input to the Reimagine stream |

Record what you pulled and the date. If offline, note the gap and proceed with the last-known lists.

---

## Step 1 — Deterministic floor (run ALL three, read every report)

```bash
export METIS_RC_ROOT="$(pwd)"
bash tests/functional/run_metis_promises.sh          # promise/contract/compile/UI floor
python3 tests/functional/clickthrough.py             # EVERY surface, partial, button-endpoint, internal link
python3 tests/functional/button_intents.py           # onclick buttons → resolve to backend endpoints → fire them
python3 tests/functional/promise_runner.py           # every README promise, primary + 2nd-angle check
python3 tests/functional/orchestration.py            # does Metis CALL anyone? hooks fire · agents wired to logging · routing · liveness · MCP registers
"$HOME/.local/share/metis-mcp/.venv/bin/python3" tests/functional/routing_eval.py   # is the RIGHT agent chosen? routing accuracy · uncovered rate · unreachable agents
"$HOME/.local/share/metis-mcp/.venv/bin/python3" tests/security/probes.py   # PII + injection + XSS/traversal/headers
```

The **orchestration** harness is the antidote to the recurring "Metis renders but isn't calling anyone" failure: a surface audit (200s, real content) can be all-green while agents are never invoked, tools/skills never route, and hooks never fire. It tests that layer directly — feed synthetic tool-calls to the real pre-tool hook and assert deny/ask/allow; confirm every work agent calls `log_agent_run` (an agent that never logs is invisible); confirm the router + `run_metis` exist; check which agents have actually run; run the MCP smoke test so tools+prompts are proven to register.

- The harness self-starts the dashboard and SKIPs (never FAILs) HTTP checks if it can't. ⚪ SKIP ⇒ bring the dashboard up and re-run before judging UI.
- `clickthrough.py` is self-discovering: it crawls each page and fires every `hx-get`/`hx-post`/`href`/`onclick` target it finds, so **new buttons are covered automatically.** Its JSON report (`clickthrough-latest.json`) lists JS-only `onclick` buttons it could *not* fire — those are the **browser-click coverage gap** the UX stream must cover by hand (or via Playwright if available). Empty bodies are reported as WARN (verify intentional vs bug), error pages / 5xx / 404 / template leaks as FAIL.
- `security/probes.py` imports the real `safety`/`guardrails` modules and fires synthetic PII + the injection set through them (deterministic), plus HTTP traversal/XSS/header probes. Run it with the **venv python** so `metis_mcp` imports.

These three reports are your evidence base. Do not assert anything the deterministic floor can settle until you have run them.

---

## Step 2 — Load synthetic fixtures

Read `tests/fixtures/README.md` and the fixture set (dummy ideas, projects, meetings, a PII-tainted CSV, an injection-laden web snippet, a known-good paper, known-bad inputs). The workflow + data-protection streams must run the real flows on these fixtures and check outputs — never on the user's real data.

---

## Step 3 — The eleven tester-profile streams (parallel)

Spawn as parallel subagents (Agent tool, `subagent_type="Explore"` for read/probe, `"claude"` for synthesis). Brief every one with the skeptic framing: *ground every finding in a file:line / command output / DB query; run the external signal yourself; prefer "works" only after you have proven it; return `severity`, `evidence`, `acceptance_test`, and the `angle` you tested from.*

1. **Penetration tester** — run the OWASP + LLM-injection probe set against every input (search, capture, forms, agent inputs); confirm credential-deny blocks `.env`/`.ssh` reads live; confirm the network allowlist; attempt IDOR on `:id` routes; attempt SSRF via any URL input.
2. **UX researcher** — open every surface; click **every** button in the clickthrough report's `js_only_buttons` list; trace each; flag every dead button, silent failure, confusing copy, and modal that doesn't close.
3. **Accessibility auditor** — WCAG 2.2 AA: keyboard tab-order, focus-visible rings, contrast ratios, semantic HTML, ARIA labels, screen-reader-readability of empty states.
4. **Performance engineer** — wall-time per surface and per partial (from clickthrough timings); slow (>2s) endpoints; token budget per workflow; memory/leak after sustained use.
5. **First-time non-technical user** — install from the README verbatim on a clean target; log every step that assumes unstated knowledge; time-to-first-useful-screen.
6. **Senior researcher (the user)** — run the 7 daily workflows end-to-end *on the fixtures*; verify each produces the promised output (brief, cross-pollination, meeting note, course draft, reflexion→proposal).
7. **Data-protection officer** — push the fixture PII through every input path; verify all four protection layers fire (read-ask, write-ask, server-side guard, output rail); verify backups are actually encrypted; verify nothing real leaks to the API.
8. **QA engineer** — every README "What you get" promise and changelog line → one executed test (use `tests/promises.yaml`); every shortcut (Ctrl+K, desktop `.lnk`, `Win+R` targets); every documented endpoint exists; every internal link resolves.
9. **DevOps engineer** — installers current vs latest deps + CVE scan on pinned versions; `git` working-tree ↔ `origin/main` parity and tag/CHANGELOG freshness; `tools/reinstall-mcp.sh` + `tools/test-mcp.sh` pass; launcher recovery works.
10. **Evidence-base reviewer** — for every agent (`agents/*/skill.md`) and skill: is the description current and evidence-based? Are cited tools/models (PaperQA2, `nomic-embed-text-v1.5`, model IDs) still SOTA per Step 0? Has each agent run in 90d (`agent_runs`)? Is `log_agent_run` actually called?
11. **Architect / Reimagine** — see Step 4.

**Step 3b — multi-angle verification (mandatory).** For every high/critical finding, spawn an independent fresh-context refuter (ideally a different model) that re-runs the exact check *from a different angle* and returns `confirmed | refuted | partial` + proof + revised severity. Majority-refute kills it. A `pipeline(streams, investigate, verify)` Workflow is the clean way to run finder→verifier. Refuted findings appear only as "investigated, not confirmed."

**Logging:** Explore subagents can't call `log_agent_run`. After all streams, the orchestrator calls it once per stream — slugs: `metis-audit-pentest`, `-ux`, `-a11y`, `-perf`, `-install`, `-workflow`, `-dpo`, `-qa`, `-devops`, `-evidence`, `-architect`.

---

## Step 4 — Reimagine pass ("would we build it this way again?")

This is NOT a bug hunt. For **each of the 11 surfaces** and each major subsystem (memory, RAG, agents, scheduler, security), answer:

- Knowing what we know now, and given everything built so far — **would we build this the same way?** If not, how?
- **Claude is evolving** — connectors, tools, scheduled tasks, the mobile app, new MCP primitives (sampling, elicitation), computer use. Can this surface/subsystem integrate more deeply instead of reimplementing? (e.g. should the scheduler be a Claude scheduled task? should capture flow through the phone app? should memory use a native primitive?)
- **Metis is not Claude-only.** It is meant to serve other AI systems too. How would this integrate with non-Claude models / other agent runtimes / a provider-agnostic MCP layer? What is hard-coded to Claude that shouldn't be?

Output: one short "if we rebuilt it today" recommendation **per surface and per subsystem**, ranked by impact. These are the most valuable forward-looking artifact of the audit.

---

## Step 5 — Drift heatmap

| Feature | Promised in | First seen (git) | Last verified working | Status today | Action |

One row per major promise. Pull first-seen from `git log`. This answers "have we lost things we built?". Append the run to `outputs/reviews/metis-evaluation/promise-trend.jsonl`.

---

## Step 6 — Self-questioning meta-pass (do not skip)

Spawn a *separate* agent whose only job is to audit the audit, reading this run's logs + the three deterministic reports + the coverage ledger:

- What did we **not** test? (a surface? a button in `js_only_buttons` never clicked? a promise with no test? a workflow not run on fixtures?)
- Where did any stream say "works" **without an executed test or command output**?
- Which findings rest on a single angle and were never cross-verified?
- What new angle (a 12th profile? a test type from the ISTQB list we skipped?) would catch what we missed?

Its output is the **coverage gap list** and seeds the next audit. Only after this meta-pass do you write the report.

---

## Step 7 — Outputs (all mandatory)

1. Personal memory file: `~/.claude/projects/{hash}/memory/evaluations/YYYY-MM-DD_self-reflexion.md` (self-contained, readable months later). Use `ls ~/.claude/projects/` to find the hash.
2. Project mirror: `outputs/reviews/metis-evaluation/YYYY-MM-DD_self-reflexion.md`.
3. Append a row to `memory/evaluations/INDEX.md`.
4. `remember(memory_type="semantic", …)` for the top 3 systemic findings + the top 3 reimagine recommendations, tagged `metis-audit,drift`.
5. `write_reflexion(agent_slug="metis-self-reflexion", …)` — honest: what was hard, what evidence was missing, what tool would have made it faster.

Include a **coverage ledger** in the report: buttons exercised / total, promises tested / total, OWASP categories probed / total, surfaces reimagined / 11. The audit is only as good as its coverage — state it explicitly; silent gaps read as "covered" when they aren't.

---

## Voice
The drift table and coverage ledger are for the record. The closing summary is for Stan — plain language: not "6 endpoints 500", but "six things the dashboard promises don't actually happen; here are the two that matter most." Refer to him by name (`get_user_profile()`).
