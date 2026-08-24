#!/usr/bin/env python3
"""generate-subagents.py — expose Metis' specialists as Claude Code subagents.

WHY THIS EXISTS
    Until now Metis' 33 specialists lived only as markdown read over MCP. That
    made "route to the Librarian" mean *read a file and role-play*, which is why
    it kept not happening: it cost tokens and delivered a persona.

    Registering them in `.claude/agents/` changes three things at once:

    1. THEY BECOME DISPATCHABLE. A real subagent, launched by the Agent tool,
       not a prompt I remembered to adopt.
    2. THE MODEL BINDS — for that subagent. This is the narrow, legitimate answer
       to a question settled on 2026-08-12 (`user_decisions` #2: "Metis does not
       make the answer's model call, the Claude client does"). That decision
       rejected server-side answer generation, and it stands. A subagent is a
       different mechanism: Claude Code still does the work, so the cost model
       does not change, but the per-agent `model` is honoured.
    3. CONTEXT IS ISOLATED — and this is the biggest token win, larger than the
       model choice. A librarian subagent can read twenty files and return one
       summary; the main conversation pays for the summary, not the twenty files.

THE DESIGN DECISION THAT MATTERS HERE
    These files are DELIBERATELY THIN — a dispatcher, not a copy of the prompt.

    The 33 agents carry ~98,000 tokens of prompt between them, and
    `methods-coach` alone is ~9,400. Inlining that would mean every subagent
    definition is a large static blob, duplicated from `agents/<slug>/`, going
    stale the moment the real prompt is edited — the two-copies-of-one-truth
    failure this project keeps paying for.

    So each generated file says: call `get_agent_context("<slug>")` first. That
    single call returns the system prompt, the contract, the project context
    files AND the standing decisions — assembled fresh, inside the subagent's own
    context window, where it is cheap.

    One source of truth (`agents/<slug>/`), loaded on demand, in isolation.

USAGE
    python3 tools/generate-subagents.py            # write .claude/agents/*.md
    python3 tools/generate-subagents.py --dry-run  # report only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"
OUT = ROOT / ".claude" / "agents"

# Claude Code's agent frontmatter takes a short model name, not a full API id.
MODEL_SHORT = {
    "claude-opus-5": "opus",
    "claude-sonnet-5": "sonnet",
    "claude-haiku-4-5": "haiku",
    "claude-fable-5": "fable",
}

# Tool grants, narrowest that still lets the agent work. This is a token lever as
# well as a safety one: every tool a subagent is granted costs schema tokens in
# its context, so a read-only specialist should not carry Write and Edit.
READ_ONLY = "Read, Grep, Glob, Bash, mcp__metis-rc__*"
WRITES = "Read, Write, Edit, Grep, Glob, Bash, mcp__metis-rc__*"
RESEARCH = "Read, Grep, Glob, Bash, WebSearch, WebFetch, mcp__metis-rc__*"

TOOLS_FOR = {
    # Build and edit code or documents.
    "software-engineer": WRITES, "rc-builder": WRITES, "builder": WRITES,
    "dashboard-engineer": WRITES, "frontend-designer-builder": WRITES,
    "writing-partner": WRITES, "presentation-maker": WRITES,
    "course-builder": WRITES, "visualization-maker": WRITES,
    "biostatistician": WRITES, "release-coordinator": WRITES,
    "authoring": WRITES,
    # Reach the internet within their remit.
    "librarian": RESEARCH, "news-radar": RESEARCH, "news-aggregator": RESEARCH,
    "content-harvester": RESEARCH, "background-maker": RESEARCH,
    "cybersecurity": RESEARCH, "career-coach": RESEARCH,
    # Everything else reads and reasons.
}


def frontmatter(text: str) -> dict:
    if not text.lstrip().startswith("---"):
        return {}
    try:
        body = text.split("---", 2)[1]
    except IndexError:
        return {}
    out = {}
    for line in body.splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def describe(slug: str, fm: dict) -> str:
    """A description the dispatcher can actually route on.

    Claude Code matches on this text, so it has to read like trigger phrases, not
    like a job title. An agent described only as "Librarian" is never selected.
    """
    d = (fm.get("description") or "").strip()
    if not d:
        d = slug.replace("-", " ")
    # Keep it one line and bounded — this text is loaded for every agent in the
    # picker, so it is a per-session cost paid 33 times (~1,800 tokens for all).
    #
    # Cut on a SEPARATOR, never mid-word: the first version ended the Librarian
    # at "what does ", which reads as a truncated thought and is exactly the kind
    # of half-phrase that makes a router pick the wrong agent.
    d = re.sub(r"\s+", " ", d)
    if len(d) > 280:
        cut = max(d.rfind(", ", 0, 280), d.rfind(". ", 0, 280),
                  d.rfind("; ", 0, 280), d.rfind("' ", 0, 280))
        d = d[:cut] if cut > 120 else d[:280].rsplit(" ", 1)[0]
        d = d.rstrip(" ,;.") + "…"
    return d


TEMPLATE = """---
name: {slug}
description: {desc}
tools: {tools}
model: {model}
---

You are Metis' **{title}** specialist.

## First, load who you are

Before doing anything else, call:

```
get_agent_context("{slug}")
```

That returns your full system prompt, your contract, any project-specific context
files, and — importantly — the **standing decisions** the researcher has already
made that you are expected to apply. Adopt all of it. Do not ask for preferences
that are already recorded there.

This indirection is deliberate: your real prompt lives in `agents/{slug}/` and is
edited there. Copying it into this file would create a second copy that goes stale.

## Then do the work

Work to your contract. Ground claims in the researcher's own indexed library
rather than general knowledge where the two differ — `search_pdf_knowledge` and
`weigh_evidence` are the tools for that, and `verify_claim` checks a citation
before you rely on it.

## Before you finish — record it

This is not bookkeeping, it is the point. Metis is a second brain: work that is
not recorded did not happen, and the next session starts blind.

1. `log_agent_run(agent_slug="{slug}", task_summary="<one line>")`
2. If the researcher stated or confirmed a standing preference — how something
   should be built, written, chosen or prioritised — record it so you carry it
   next time:
   `record_decision(decision="...", category="...", agent_slug="{slug}", context="why")`
3. If you followed a repeatable sequence worth reusing, store it as a procedure.
4. `write_reflexion(...)` on deep or multi-step work: what worked, what was
   missing, which tool you wished existed.

Return your findings, not a narration of your process. Your final message is the
result the main conversation receives — it does not see your intermediate steps,
so anything that matters must be in it.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not AGENTS.is_dir():
        print(f"no agents directory at {AGENTS}", file=sys.stderr)
        return 2

    written, skipped = [], []
    for d in sorted(AGENTS.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        slug = d.name
        if (d / "RETIRED.md").exists():
            skipped.append((slug, "retired"))
            continue
        src = None
        for fn in ("skill.md", "system-prompt.md"):
            if (d / fn).exists():
                src = d / fn
                break
        if src is None:
            skipped.append((slug, "no prompt file"))
            continue

        fm = frontmatter(src.read_text(encoding="utf-8", errors="ignore"))
        model_id = fm.get("model", "claude-sonnet-5")
        model = MODEL_SHORT.get(model_id, "sonnet")
        body = TEMPLATE.format(
            slug=slug,
            desc=describe(slug, fm),
            tools=TOOLS_FOR.get(slug, READ_ONLY),
            model=model,
            title=slug.replace("-", " ").title(),
        )
        if not args.dry_run:
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / f"{slug}.md").write_text(body, encoding="utf-8")
        written.append((slug, model, len(body)))

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {len(written)} subagent definition(s) to {OUT.relative_to(ROOT)}/\n")
    by_model: dict[str, int] = {}
    for slug, model, _ in written:
        by_model[model] = by_model.get(model, 0) + 1
    for m, n in sorted(by_model.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  model: {m}")
    total = sum(n for _, _, n in written)
    print(f"\n  definition payload: {total:,} chars = ~{total//4:,} tokens for all "
          f"{len(written)} — thin on purpose; the real prompts load on demand")
    if skipped:
        print("\n  skipped:")
        for slug, why in skipped:
            print(f"    {slug:28s} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
