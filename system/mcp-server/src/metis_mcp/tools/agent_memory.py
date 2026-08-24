"""agent_memory.py — what makes invoking a specialist worth doing.

THE QUESTION THIS ANSWERS
    2026-08-24, the researcher: *"I don't see them mentioned in the outputs, where
    are my agents? ... if you are not using them they must not be good?"*

    The agents are not bad. They hold no memory, and that is a different problem
    with a different fix.

    Measured that day: `user_decisions` held **2 rows** while `session_summaries`
    held **7,578 decision entries**. Every decision the researcher ever made was
    written somewhere nothing reads — the same write-path-with-no-reader defect
    this project keeps finding, and the most consequential instance of it.

    The consequence is precisely the behaviour the researcher noticed. Invoking
    `frontend-designer-builder` returned a persona that could be inferred from its
    name. It did NOT return "the researcher wants a visual options studio with
    clickable mini-previews" or "position:fixed, to escape overflow clipping" —
    decisions actually taken, recorded in a session summary, and unreachable. So
    routing cost tokens and added nothing, and an assistant with any judgement
    stops routing. **The agent system was not being under-used; it was empty.**

WHAT A DECISION IS HERE
    A STANDING PREFERENCE, attributed to the specialist that should apply it:

      frontend-designer-builder  how a dashboard gets built
      writing-partner            how prose gets written
      librarian                  what matters in the library
      software-engineer          how code gets structured

    Not an open question — `open_decisions` already holds those, with a lifecycle.
    Not a fact — `semantic_memory` holds those. A standing preference has no
    lifecycle: it applies until superseded, and `supersedes` records that rather
    than deleting the history.

    `agent_slug = ''` means it applies to every agent — a project-wide rule.

WHY ATTRIBUTION AND NOT ONE FLAT LIST
    A flat list of 200 preferences injected into every agent is noise, and noise
    gets ignored. The Librarian does not need CSS decisions. Attribution is what
    keeps the injected context short enough to be read, which is the only thing
    that makes it change behaviour.
"""
from __future__ import annotations

from datetime import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# Categories exist so a decision can be routed and reviewed. Deliberately few —
# a taxonomy nobody can hold in their head gets one value used for everything.
CATEGORIES = (
    "design",        # how something should look or be laid out
    "writing",       # how prose should read
    "architecture",  # how the system should be built
    "coding",        # code style and structure
    "method",        # how analysis should be done
    "library",       # what matters in the literature
    "process",       # how work should flow
    "persona",       # how Metis should behave
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure(con) -> None:
    """The columns this module needs, for a DB that predates them."""
    for sql in (
        "ALTER TABLE user_decisions ADD COLUMN agent_slug TEXT DEFAULT ''",
        "ALTER TABLE user_decisions ADD COLUMN supersedes INTEGER",
        "ALTER TABLE user_decisions ADD COLUMN last_applied_at TEXT DEFAULT ''",
    ):
        try:
            con.execute(sql)
        except Exception:
            pass       # already present
    con.execute("CREATE INDEX IF NOT EXISTS idx_user_decisions_agent "
                "ON user_decisions(agent_slug, category)")


def decisions_for(agent_slug: str = "", limit: int = 25) -> list[dict]:
    """Standing decisions an agent should apply.

    Returns the agent's own decisions PLUS the project-wide ones (`agent_slug=''`),
    because a rule that applies to everything must reach the specialist too.
    Superseded rows are excluded — history is kept, not injected.
    """
    with connect(paths.db) as con:
        _ensure(con)
        superseded = {r[0] for r in con.execute(
            "SELECT supersedes FROM user_decisions WHERE supersedes IS NOT NULL")}
        rows = con.execute(
            "SELECT decision_id, category, decision, context, scope, agent_slug, "
            "       created_at, hits FROM user_decisions "
            "WHERE COALESCE(agent_slug,'') IN (?, '') "
            "ORDER BY (COALESCE(agent_slug,'') = '') , created_at DESC LIMIT ?",
            (agent_slug, limit * 2)).fetchall()
    out = [dict(r) for r in rows if r["decision_id"] not in superseded]
    return out[:limit]


def render_for_prompt(agent_slug: str, limit: int = 20) -> str:
    """The block `get_agent_context` injects. Empty string when there is nothing.

    Returning "" rather than a "no decisions on record" heading matters: a heading
    with nothing under it reads as a working feature and trains the reader to skip
    the section.
    """
    rows = decisions_for(agent_slug, limit)
    if not rows:
        return ""
    mine = [r for r in rows if (r["agent_slug"] or "") == agent_slug]
    shared = [r for r in rows if not (r["agent_slug"] or "")]
    out = ["# Standing decisions — apply these without being asked", ""]
    if mine:
        out.append(f"## Decided for {agent_slug}")
        for r in mine:
            out.append(f"- **[{r['category'] or 'general'}]** {r['decision']}"
                       + (f"  \n  *{r['context']}*" if r["context"] else "")
                       + f"  \n  *(decided {r['created_at'][:10]})*")
        out.append("")
    if shared:
        out.append("## Project-wide")
        for r in shared:
            out.append(f"- **[{r['category'] or 'general'}]** {r['decision']}")
        out.append("")
    out.append("These are settled. Do not re-litigate one without a new reason, "
               "and say so explicitly if you do.")
    return "\n".join(out)


def touch(decision_ids: list[int]) -> None:
    """Record that a decision was actually applied.

    `hits` is the signal that separates a decision doing work from one that was
    recorded and never mattered — the difference the 127 routing rules could not
    show (only 18 had ever matched).
    """
    if not decision_ids:
        return
    with connect(paths.db) as con:
        _ensure(con)
        con.executemany(
            "UPDATE user_decisions SET hits = hits + 1, last_applied_at = ? "
            "WHERE decision_id = ?", [(_now(), i) for i in decision_ids])


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------
# NOTE — there is deliberately NO record_decision here.
#
# One was written and it COLLIDED: FastMCP logged "Tool already exists:
# record_decision" because pipeline.py has registered that name since June,
# and middleware.py advertises it by name in its standing-procedure prompts.
# Two registrations of one tool name means one silently wins, which is the
# decorator-drift hazard in a new costume.
#
# So the WRITER stays in pipeline.py (extended there with agent_slug) and this
# module owns the READERS. One name, one registration.

@app.tool()
async def show_agent_decisions(agent_slug: str = "", limit: int = 30) -> list[TextContent]:
    """What standing decisions does an agent carry, and are they being applied?

    Pass no slug to see every decision and which specialist owns it. The `applied`
    count is the signal that matters: a decision recorded and never applied is
    indistinguishable from one that was never recorded.

    Args:
        agent_slug: Restrict to one specialist; omit for all.
        limit: Maximum rows.

    Returns:
        The decisions, grouped, with their categories and apply counts.
    """
    with connect(paths.db) as con:
        _ensure(con)
        if agent_slug:
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM user_decisions WHERE COALESCE(agent_slug,'') IN (?,'') "
                "ORDER BY created_at DESC LIMIT ?", (agent_slug, limit))]
        else:
            rows = [dict(r) for r in con.execute(
                "SELECT * FROM user_decisions ORDER BY "
                "COALESCE(agent_slug,'zzz'), created_at DESC LIMIT ?", (limit,))]
        total = con.execute("SELECT COUNT(*) FROM user_decisions").fetchone()[0]
        by_agent = con.execute(
            "SELECT COALESCE(NULLIF(agent_slug,''),'(project-wide)') a, COUNT(*) n "
            "FROM user_decisions GROUP BY 1 ORDER BY 2 DESC").fetchall()

    if not rows:
        return [TextContent(type="text", text=(
            "No standing decisions on record.\n\n"
            "That is why invoking a specialist adds nothing: it returns a persona "
            "with no knowledge of how you want things done. Record one with "
            "`record_decision(...)` the next time you choose between alternatives."))]

    out = [f"**{total} standing decision(s)**", "",
           "| agent | count |", "|---|---:|"]
    for r in by_agent:
        out.append(f"| {r['a']} | {r['n']} |")
    out += ["", "| category | decision | agent | applied |", "|---|---|---|---:|"]
    for r in rows:
        out.append(f"| `{r['category'] or '—'}` | {r['decision'][:88]} "
                   f"| {r['agent_slug'] or 'all'} | {r['hits']} |")
    unapplied = sum(1 for r in rows if not r["hits"])
    if unapplied:
        out += ["", f"{unapplied} of these have never been applied. Either they are "
                    "not reaching the agent's context, or they are not relevant to "
                    "the work being done — both worth knowing."]
    return [TextContent(type="text", text="\n".join(out))]
