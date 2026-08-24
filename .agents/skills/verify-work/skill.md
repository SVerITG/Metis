---
name: Verify Work
description: "verify, verify last, verify my work, did that work, check the change, confirm the fix, verify the change, verify before pushing, self-verify, validate the change, did the fix work, check what I just did, generate verify gate, prove it works"
effort: normal
complexity: standard
---

## Purpose

The **in-the-moment generate→verify gate** — the working-loop version of `/metis-self-reflexion`. After a change is made, this runs the **external signals** on the work just done — deterministic checks first, then an independent skeptic — *before* trusting it's done.

This exists because the research is unambiguous: an LLM **cannot reliably judge its own work without an external signal** and often degrades when it tries ([Huang et al. 2310.01798](https://arxiv.org/abs/2310.01798)); the fix is to *run the signal* and have an *independent verifier* ([CRITIC 2305.11738](https://arxiv.org/abs/2305.11738); Reflexion). Metis's own 2026-06-04 audit proved it — an unverified pass reported 25 false failures.

## Metis's three-tier reflexion loop (where this fits)

1. **Always (cheap):** the post-tool hook syntax-checks every code edit; `write_reflexion()` after substantive runs.
2. **High-stakes (this skill):** code changes and factual claims get the full generate→verify gate below.
3. **Periodic (drift):** `/metis-self-reflexion` — the quarterly multi-stream audit.

## When to use

Before saying "done" or pushing, after any code change; when asked "did that actually work?"; or as the gate Metis runs on its own substantive output.

## What to do when invoked

**Step 1 — Identify the work.** `git status --porcelain` and `git --no-pager diff --stat` (staged + unstaged). Classify the changed files: Python (`.py`), shell (`.sh`), hook (`.mjs`), MCP-server code (`system/mcp-server/src/...`), dashboard/templates (`system/app-py/...`), docs/config only.

**Step 2 — Run the deterministic external signals (the floor).** Only the relevant ones; report each result verbatim:
- Changed `.py` → `python -m py_compile <file>` for each; if app/MCP logic, run nearby unit tests: `"$HOME/.local/share/metis-mcp/.venv/bin/python" -m pytest tests/unit -q`.
- Changed `.sh` → `bash -n <file>`.
- Changed `.mjs` → `node --check <file>`.
- **MCP-server code** → `bash tools/reinstall-mcp.sh` then `bash tools/test-mcp.sh` (expect `HEALTHY`); remind the user to `/mcp` reconnect.
- **Dashboard code / templates** → `export METIS_RC_ROOT="$(pwd)"; bash tests/functional/run_metis_promises.sh` (it self-starts the dashboard); expect **0 🔴 FAIL**.
- Docs/config only → skip the heavy checks; note that.
A failing signal means **NOT verified** — fix it and re-run. Do not proceed to Step 3 with a red signal.

**Step 3 — Independent skeptic pass (the verifier — do not self-grade).** Spawn ONE fresh sub-agent, ideally a **different model** (`Agent(subagent_type="Explore", model="sonnet", ...)`), with the diff and this brief:
> "Adversarially review this change. Try to find a real bug, an unhandled edge case, a regression, or a way it silently fails. Default to skeptical. Check the actual code, don't assume. Return concrete issues with file:line, OR 'no issues found' and exactly what you checked."

Relay only its *confirmed*, concrete issues. The agent that wrote the code never grades itself (self-preference bias).

**Step 4 — Verdict.**
- ✅ **VERIFIED** — every deterministic signal passed AND the skeptic found nothing real. State exactly what was run (the proof).
- ⚠️ **ISSUES** — list each with file:line and a one-line **acceptance test** ("how we'll know it's fixed"). Do **not** say "done".

**Step 5 — Record (when part of an agent run).** `write_reflexion()` with the verification outcome. Promote a lesson to memory only if a real issue was found and fixed (verified) — never promote unconfirmed self-critique.

## The one rule

**Never trust the first answer on anything that has an external signal available — run the signal.** That single principle is the whole of the self-correction literature, applied to the work you just did.

## Collaboration

Software Engineer (the fix), Critic (adversarial review), Cybersecurity / Data Guardian (security-sensitive diffs). Escalate to `/metis-self-reflexion` if the change is system-wide.
