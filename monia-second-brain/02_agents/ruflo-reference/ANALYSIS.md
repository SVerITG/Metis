# Ruflo Analysis for Monia Second Brain
*Analysed: 2026-03-27*

## What ruflo actually is

Ruflo (formerly Claude Flow) is a multi-agent orchestration framework for **software engineering** tasks, built on top of Claude Code and Codex. It is not a knowledge management system. Its intelligence, memory, and routing systems are optimised for code patterns, not personal knowledge.

The real substance of ruflo is in two files: `CLAUDE.md` (the operating configuration loaded into Claude Code sessions) and `AGENTS.md` (the coordination guide for Codex workers). The five `agents/*.yaml` files are thin stubs — they only declare agent type and capabilities. The framework itself is the thick layer.

---

## What is NOT applicable to Monia

| Ruflo Feature | Why not applicable |
|---|---|
| Byzantine/Raft/Gossip consensus | Designed for distributed system reliability across many concurrent processes. Monia is single-user, local-first. |
| HNSW vector search, SONA, EWC++ | Optimised for code pattern retrieval and neural self-learning. Monia's knowledge store is SQLite + filesystem, not a vector database. |
| Dual-mode Claude + Codex workers | Requires OpenAI Codex CLI. Not needed for a personal PKM. |
| IPFS plugin registry, Pinata | Decentralised distribution infrastructure. Not relevant to a local system. |
| Agent Booster (WASM) | Bypasses LLM for sub-millisecond code transforms. This is a cost-optimisation tool, not a knowledge tool. |
| 100+ specialised agent types | Most are GitHub, CI/CD, deployment, or distributed-systems agents. |
| 12 background workers (ultralearn, benchmark, etc.) | All are codebase-specific workers that scan and optimise source code. |
| Flash Attention, LoRA, Int8 quantisation | ML model-level optimisations. Not available in Claude Code context. |

---

## What IS valuable and applicable

### 1. Memory-before/after pattern (HIGH VALUE)
Ruflo's single most transferable idea: **always search memory before starting a task, always store what worked after success.**

```
BEFORE task → search memory for relevant past patterns
AFTER success → store what approach worked and why
```

This is directly applicable to every Monia agent. Implement with the existing SQLite `metis.sqlite` rather than AgentDB.

### 2. Pre/post task hooks (HIGH VALUE)
The hook lifecycle:
- `pre-task`: log what is being attempted, check for existing context
- `post-task`: record outcome, flag what was learned

Directly applicable to how Monia agents should operate. Already partially implemented in the Monia system-prompt ("what is new, what is blocked, what requires a decision").

### 3. 3-tier complexity routing (MEDIUM VALUE)
The principle of routing by complexity before invoking heavy machinery:

| Tier | Ruflo | Monia equivalent |
|---|---|---|
| 1 — trivial | WASM transform, no LLM | Direct file edit, no agent needed |
| 2 — medium | Haiku model | Single-agent task (Builder or Dashboard Engineer) |
| 3 — complex | Full swarm | Multi-agent coordination via Monia |

Apply to the software-engineer agent: route code review requests by complexity before deciding whether to spawn sub-roles.

### 4. Anti-drift swarm configuration (MEDIUM VALUE)
For complex multi-file tasks, ruflo uses:
- Hierarchical topology (coordinator → workers, not peers)
- Short task cycles with verification gates
- Shared memory namespace to prevent divergence

Applicable when Builder + Dashboard Engineer + R-specialist need to work on the same codebase simultaneously. Monia acts as the hierarchical coordinator.

### 5. Security practices (HIGH VALUE — apply selectively)
Ruflo's `@claude-flow/security` module defines practices at system boundaries:
- Input validation using schemas (Zod in JS; use `validate` functions in R)
- Path traversal prevention (PathValidator)
- Command injection protection (SafeExecutor)
- No secrets in code, no `.env` commits

Apply these as a **checklist** in the software-engineer agent's code review workflow, not as runtime middleware.

### 6. Swarm recipes as task templates (MEDIUM VALUE)
Ruflo's swarm recipes are essentially named task pipelines. This translates directly to the Monia agent workflow model:

| Ruflo recipe | Monia equivalent |
|---|---|
| Bug Fix: coordinator → researcher → coder → tester | Debug session: Monia → R-specialist → Builder → user verification |
| Feature: coordinator → architect → coder → tester → reviewer | New app: Monia → Dashboard Engineer → Builder → R-specialist review |
| Security audit: coordinator → security-architect → reviewer | Code review: software-engineer security checklist pass |

### 7. Agent YAML structure (LOW VALUE — already exceeded)
Ruflo's `agents/*.yaml` are thin stubs. Monia's agent folder structure (system-prompt, contract, workflows, output-spec, README) is already more complete and useful.

---

## When to call ruflo directly

Ruflo can be invoked via `npx ruflo@latest` if installed. Consider activating it for:

1. **Large-scale codebase reviews** — when you have a substantial existing app (e.g. the Shiny dashboard) and want a structured multi-agent security or quality audit beyond what a single agent can do.
2. **New app scaffolding** — when starting a greenfield app (Python, TypeScript) and want architecture + code + tests generated concurrently.
3. **Reviewing old R scripts** — potentially use the researcher + coder + reviewer swarm recipe on a batch of existing scripts.

Do NOT activate ruflo for: daily PKM operations, literature management, meeting transcription, writing, or PhD work.

**To activate (when needed):**
```bash
# Install once
npm install -g ruflo

# Add as MCP server to Claude Code
claude mcp add ruflo -- npx ruflo@latest mcp start

# Then from Claude Code, spawn a swarm
npx ruflo swarm init --topology hierarchical --max-agents 5
npx ruflo agent spawn --type reviewer --name code-reviewer
npx ruflo swarm start --objective "Review all R scripts in 05_sources/code"
```

---

## Recommended extraction for the Monia software-engineer agent

Build a single `02_agents/software-engineer/` agent that distils the following ruflo concepts:

1. Memory search before every code task (SQLite-backed)
2. Post-task pattern storage (append to a `patterns.md` in the agent folder)
3. Security checklist (simplified from `@claude-flow/security`)
4. Complexity routing (trivial / medium / complex decision tree)
5. Task templates for: bug fix, new feature, code review, R script audit
6. Anti-drift rule: always define scope before touching files

Security note: the full ruflo security module (CVE remediation, Zod validation, bcrypt, token generation) is relevant **only** when building production apps or MCP servers. It does not need to be embedded in every Monia agent. Apply it as a checklist item in the software-engineer agent and as a gate in Builder and Dashboard Engineer when they deploy anything external-facing.

Memory note: ruflo's AgentDB + HNSW is overkill. A simple `patterns.md` per agent plus the existing SQLite database is sufficient for Monia's scale. The *discipline* of the memory-before/after pattern matters more than the technology.

---

## Summary verdict

| Question | Answer |
|---|---|
| Use ruflo as PKM backbone? | No. Wrong tool for the job. |
| Use ruflo as agent repository format? | No. Monia's format is already better. |
| Extract patterns from ruflo? | Yes — memory discipline, hooks lifecycle, complexity routing, security checklist, swarm recipes as templates. |
| Keep ruflo reference folder? | Yes. Useful for large codebase work and as inspiration. |
| Call ruflo for specific tasks? | Yes, occasionally — large-scale code reviews and new app scaffolding. |
| Implement security module in Monia? | Partially — as a checklist in software-engineer and a gate in Builder, not as runtime middleware. |
