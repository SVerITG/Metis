"""
persona_growth.py — the persona that learns.

THE GAP THIS CLOSES
-------------------
Audited 2026-08-19. Metis' MEMORY grows continuously: 835 session summaries,
2,217 episodic memories, 77 semantic concepts, 22 procedures, 44 reflexions, all
written on every session. But her PERSONA never did. `metis-persona.md` is
written only by the setup wizard or by hand — nothing had ever appended a learned
preference to it. So Metis accumulated facts about the work and never updated how
she behaves.

That is the difference between a filing cabinet and an assistant. If the researcher corrects
how something should be done, that correction has to survive into how the next
session behaves, not merely be recorded as having happened.

HOW IT WORKS
------------
`metis-learned.md` is an append-only ledger of confirmed behavioural lessons,
read alongside `metis-persona.md` at the start of every session. The persona file
stays hand-authored and stable; the learned file is where accumulation happens, so
a bad automatic write can never corrupt the deliberate description of who the researcher is.
(That matters here: a 2026-05-28 wizard run once wrote "jon is a k working in ntd"
into the persona and every agent addressed him as 'jon' until it was found.)

WHAT BELONGS HERE — and what does not
-------------------------------------
Only durable, behavioural, confirmed lessons. "Prefers X over Y", "always do Z
before W", "do not offer P". Not facts about the work (those are memory), not
one-off task details, not anything the user has not actually confirmed.

Every entry carries its evidence and date, so a lesson can be audited and revoked
rather than accreting forever as unexplained rules.
"""
from __future__ import annotations

import datetime
import re

try:
    from mcp.types import TextContent
except ImportError:                                     # pragma: no cover
    TextContent = None                                  # type: ignore[assignment,misc]

from metis_mcp.config import paths

try:
    from metis_mcp.app_instance import app
except ImportError:                                     # pragma: no cover
    class _NoopApp:                                     # type: ignore[no-redef]
        def tool(self, *a, **kw):
            def _dec(fn): return fn
            return _dec
    app = _NoopApp()                                    # type: ignore[assignment]


CATEGORIES = {
    "voice": "how to speak — register, length, structure",
    "workflow": "how to do things — order of operations, what to check first",
    "preference": "what the researcher prefers, chosen between real alternatives",
    "avoid": "something the researcher does not want done, or wants done differently",
    "domain": "a standing fact about his field that changes how to answer",
}

_HEADER = """# What Metis has learned

Append-only. Read together with `metis-persona.md` at the start of every session:
that file says who the researcher is and is hand-authored; this one accumulates what he has
actually confirmed about how Metis should behave.

Written by `record_persona_learning()`. Each entry carries its evidence and date so
it can be audited and revoked rather than accreting as an unexplained rule. Kept
separate from the persona file on purpose — an automatic write must never be able
to corrupt the deliberate description of who the researcher is.

---
"""


def _path():
    return paths.root / "system" / "config" / "metis-learned.md"


def _read() -> str:
    p = _path()
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def read_learned(limit: int = 0) -> str:
    """The learned-lessons text, for inclusion in a session preamble."""
    body = _read()
    if not body:
        return ""
    if limit and len(body) > limit:
        # Keep the most RECENT lessons when truncating: newer corrections
        # supersede older ones, so the tail is the part that matters.
        return body[:len(_HEADER)] + "\n…(older entries elided)…\n" + body[-limit:]
    return body


@app.tool()
async def record_persona_learning(
    lesson: str,
    category: str = "preference",
    evidence: str = "",
    supersedes: str = "",
) -> list[TextContent]:
    """Record a lasting lesson about how Metis should behave, so it survives the session.

    Use this when the researcher corrects how something should be done, states a preference
    between real alternatives, or confirms an approach — anything that should change
    Metis' behaviour in FUTURE sessions rather than only this one.

    This is what makes the persona grow. Metis' memory already accumulates facts
    about the work; without this, none of it changed how she behaves. A correction
    that is only remembered as having happened is not learned.

    WHAT BELONGS HERE:
      - "Prefers the explicit mark-read button over auto-marking" (a real choice)
      - "Wants feed URLs verified live before being added" (a workflow rule)
      - "Do not use ANSI colour; emoji survive copy-paste" (an avoid)

    WHAT DOES NOT:
      - Facts about the research or the code — that is memory (`remember`,
        `save_session_summary`).
      - One-off task details that will not recur.
      - Anything the researcher has not actually confirmed. Do not record an inference as a
        lesson; if unsure whether it is durable, ask, or leave it.

    Args:
        lesson: The behavioural rule, stated imperatively and briefly — how Metis
            should act from now on. One or two sentences.
        category: One of voice, workflow, preference, avoid, domain.
        evidence: Why this is believed — quote or paraphrase what the researcher said, and
            when. An unexplained rule cannot be audited later.
        supersedes: Optional. Text from an earlier lesson this replaces, so the
            older one is marked rather than silently contradicted.

    Returns:
        Confirmation, and how many lessons are now on record.
    """
    lesson = " ".join((lesson or "").split()).strip()
    if len(lesson) < 12:
        return [TextContent(type="text", text=(
            "Nothing recorded — `lesson` needs to be a real behavioural rule. "
            "State how Metis should act from now on."
        ))]
    if category not in CATEGORIES:
        category = "preference"

    body = _read() or _HEADER
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # Don't record the same lesson twice — the ledger is append-only, so a
    # duplicate is permanent noise.
    norm = re.sub(r"[^a-z0-9 ]", "", lesson.lower())
    for line in body.splitlines():
        if line.strip().startswith("- **") and norm[:60] in re.sub(r"[^a-z0-9 ]", "", line.lower()):
            return [TextContent(type="text", text=(
                f"Already on record, not duplicated:\n  {line.strip()[:200]}"
            ))]

    if supersedes:
        key = re.sub(r"[^a-z0-9 ]", "", supersedes.lower())[:50]
        out_lines = []
        for line in body.splitlines():
            if key and key in re.sub(r"[^a-z0-9 ]", "", line.lower()) and "SUPERSEDED" not in line:
                out_lines.append(line + f"  _(SUPERSEDED {today})_")
            else:
                out_lines.append(line)
        body = "\n".join(out_lines)

    entry = f"\n- **[{category}]** {lesson}"
    if evidence:
        entry += f"\n  - _evidence:_ {' '.join(evidence.split())[:400]}"
    entry += f"\n  - _recorded:_ {today}\n"

    try:
        p = _path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.rstrip() + "\n" + entry, encoding="utf-8")
    except OSError as e:
        return [TextContent(type="text", text=f"Could not write: {e}")]

    count = _read().count("\n- **[")
    return [TextContent(type="text", text=(
        f"Learned and recorded ({category}):\n  {lesson}\n\n"
        f"{count} lesson(s) now on record in system/config/metis-learned.md. "
        f"This is read at the start of every session, so it applies from the next "
        f"one onward — not retroactively to this conversation."
    ))]


@app.tool()
async def get_persona_learnings(category: str = "") -> list[TextContent]:
    """Show what Metis has learned about how to behave.

    Read this at the start of a session, alongside `metis-persona.md`, so
    corrections the researcher made previously actually apply. Also useful when he asks what
    Metis has learned, or to audit whether a rule still holds.

    Args:
        category: Optionally filter — voice, workflow, preference, avoid, domain.

    Returns:
        The recorded lessons with their evidence and dates.
    """
    body = _read()
    if not body or "\n- **[" not in body:
        return [TextContent(type="text", text=(
            "Nothing learned yet. Metis' memory grows on every session, but no "
            "behavioural lessons have been recorded — use "
            "`record_persona_learning()` when the researcher confirms a preference or "
            "corrects how something should be done."
        ))]

    if category and category in CATEGORIES:
        kept = [b for b in body.split("\n- **[") [1:] if b.startswith(category + "]")]
        if not kept:
            return [TextContent(type="text", text=f"No lessons recorded under '{category}'.")]
        return [TextContent(type="text", text=(
            f"**Lessons — {category}** ({CATEGORIES[category]})\n\n- **["
            + "\n- **[".join(kept)))]

    n = body.count("\n- **[")
    superseded = body.count("SUPERSEDED")
    note = (f"\n\n({n} lesson(s) on record"
            + (f", {superseded} superseded" if superseded else "")
            + ". Applies from the start of each session.)")
    return [TextContent(type="text", text=body.strip() + note)]
