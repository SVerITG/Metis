#!/usr/bin/env python3
"""generate_desktop_instructions.py — the three always-on layers Claude Desktop has.

WHY THREE, NOT ONE
    Claude Code reads CLAUDE.md and that is the whole story. Claude Desktop has no
    equivalent single file, but it has three separate places that inject text into
    every conversation, and they have different reach and different budgets:

      1. ACCOUNT preferences   Settings → Profile. Applies to EVERY chat you ever
                               have, including the ones with nothing to do with
                               research. Must therefore be SHORT, about identity
                               and voice, and still sensible when Metis is not
                               connected at all.

      2. PROJECT instructions  Applies to every chat inside one project. Room to
                               be specific: the routing table, the workflow, the
                               output contract.

      3. MCP server            Already shipped in app_instance.py — arrives at
         `instructions`        connection, so it is the right home for anything
                               about the tools themselves.

    Putting the wrong content in the wrong tier is the failure to avoid. A wall
    of Metis machinery in the account preferences degrades every unrelated
    conversation the researcher ever has; a persona buried in one project is
    absent from all the others.

WHY GENERATE RATHER THAN HAND-WRITE
    The persona, the response contract and the learned-lesson ledger are the
    source of truth and they CHANGE — the ledger is append-only and grew four
    entries in a single day. Hand-copied instructions go stale silently, which is
    the same convention-not-construction failure this codebase keeps finding.
    Regenerate after any persona change; the files are written to
    `system/config/desktop/` ready to paste.

USAGE
    python3 tools/generate_desktop_instructions.py
    python3 tools/generate_desktop_instructions.py --print account
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "system" / "config" / "desktop"

# Claude's account-level preference box is modest. Keep well inside it — a
# truncated instruction is worse than a shorter one, because you cannot see
# where it was cut.
ACCOUNT_BUDGET = 1400


def read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def profile() -> dict:
    try:
        return json.loads(read("system/config/user-preferences.json"))
    except Exception:
        return {}


def corpus_size() -> tuple[int, int]:
    try:
        c = sqlite3.connect(str(Path.home() / ".local/share/metis" / "metis.sqlite"))
        d = c.execute("SELECT COALESCE(SUM(doc_count),0), COALESCE(SUM(chunk_count),0) "
                      "FROM knowledge_databases WHERE COALESCE(enabled,1)=1").fetchone()
        c.close()
        return int(d[0]), int(d[1])
    except Exception:
        return 0, 0


def recent_lessons(n: int = 6) -> list[str]:
    """The most recent learned lessons, as one-liners."""
    txt = read("system/config/metis-learned.md")
    out = []
    for m in re.finditer(r"^- \*\*\[(\w+)\]\*\*\s*(.+?)$", txt, re.M):
        out.append(f"({m.group(1)}) {m.group(2).strip()}")
    return out[-n:]


# ---------------------------------------------------------------------------

def build_account() -> str:
    p = profile()
    name = p.get("display_name", "the researcher")
    role = p.get("role", "")
    interests = ", ".join((p.get("interests") or [])[:6])
    docs, _ = corpus_size()

    text = f"""My name is {name}. {role}.
My work centres on {interests}.

How to talk to me: plain English, like a knowledgeable colleague — not a chatbot.
I am not a career software engineer, so when you explain code or system internals,
explain the reasoning, not just the change. Be concise. Challenge me when the
evidence warrants it, but frame critique constructively.

I use a personal research system called Metis. When its tools are available:
- Search my own indexed library before answering a question in my field, and cite
  what you find by title and page. My corpus is {docs} documents.
- My library is trusted ground to build on, never the limit of an answer — bring in
  outside literature too, and mark it as not yet in my library.
- Never claim you checked my whole library. A search returns the closest few
  passages. Say what was actually consulted, and if nothing relevant came back, say
  so — a gap is worth knowing about.
- Record decisions and session summaries as we go, rather than at the end.

If Metis is not connected, ignore the four points above and just answer well."""

    if len(text) > ACCOUNT_BUDGET:
        text = text[:ACCOUNT_BUDGET].rsplit("\n", 1)[0]
    return text


def build_project() -> str:
    p = profile()
    name = p.get("display_name", "the researcher")
    docs, chunks = corpus_size()
    lessons = recent_lessons()

    lesson_block = "\n".join(f"- {l}" for l in lessons) or "- (none recorded yet)"

    return f"""# Metis — working instructions

You are Metis, {name}'s research companion. You are a SILENT BACKGROUND LAYER:
never announce yourself, never narrate your own machinery. Your presence should
come from what the answer KNOWS — a genuine reference to a past session, a
decision already taken, a procedure that already covers the task.

Never invent continuity. If nothing relevant is stored, say nothing about the past.
A fabricated "as we discussed" makes the whole memory layer feel decorative.

## Start of every conversation
Call `get_user_profile()`. Read the `metis://persona`, `metis://learned` and
`metis://corpus` resources if your client supports attaching them.

## Grounding — the thing that makes this Metis and not a chatbot
Before answering anything in {name}'s field, call `search_pdf_knowledge(query=...)`.
The indexed corpus is {docs} documents / {chunks} passages.

Three rules:
1. Cite what comes back — title and page — so the source can be opened.
2. The corpus is ground to BUILD ON, not the limit of the answer. Bring in outside
   literature and mark it as not yet indexed, then offer to add it.
3. NEVER claim the whole library was read. State what was consulted, e.g.
   "6 passages from {docs} indexed documents". If nothing relevant came back, say
   that plainly — an absence is information.

## Reply shape
Use these markers inline, where the thing occurs:
🟢 decided/done · 🟡 needs your call · 🔵 saved to Metis · ↩ from your past ·
✱ insight · ⚠ caveat · 📚 grounded in the library

Never more than one 🟡 per reply unless genuinely blocked on several things.
🔵 is for things ACTUALLY written, never intentions. ↩ must name its source
concretely. No marker at all is fine and often right. Anything that must LINE UP
goes inside a code fence — Desktop renders prose in a proportional font.

## Routing
Use `run_metis(request=..., client="chat")` for substantive work: it handles
safety, intent and specialist selection, and grounds the answer in the corpus.
Announce it naturally — "let me look at this as an epi problem", never
"routing to agent X".

## Close the loop
End substantive work with `save_session_summary()`, `log_agent_run()` and
`update_project_memory()`. A session that isn't recorded is a session that never
happened.

## What {name} has taught Metis
{lesson_block}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="which", choices=["account", "project"])
    args = ap.parse_args()

    account, project = build_account(), build_project()

    if args.which:
        print(account if args.which == "account" else project)
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "account-preferences.md").write_text(account, encoding="utf-8")
    (OUT / "project-instructions.md").write_text(project, encoding="utf-8")

    docs, chunks = corpus_size()
    print("Generated the two Claude Desktop instruction layers.\n")
    print(f"  1. system/config/desktop/account-preferences.md   "
          f"{len(account):>5} chars  (budget {ACCOUNT_BUDGET})")
    print(f"     → Claude Desktop: Settings → Profile → personal preferences")
    print(f"     → applies to EVERY conversation, Metis or not\n")
    print(f"  2. system/config/desktop/project-instructions.md  "
          f"{len(project):>5} chars")
    print(f"     → Claude Desktop: create a project 'Metis' → custom instructions")
    print(f"     → applies to every conversation in that project\n")
    print(f"  3. MCP server instructions — already shipped, no action needed")
    print(f"     → arrives automatically when metis-rc connects\n")
    print(f"  Corpus figures baked in: {docs} documents, {chunks} passages.")
    print(f"  Re-run this after any persona or learned-lesson change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
