"""Self-improvement loop — Phase 9b.

Reads recent ``reflexion_log`` entries, themes them per agent, and drafts
``skill_improvement_proposals`` rows. The user remains in the loop: drafts
land in ``status='draft'`` until they review and approve via the existing
``approve_proposal`` tool or the Metis-tab dashboard surface.

Pure functions (callable from the FastAPI dashboard) plus ``@app.tool()``
wrappers for MCP / Claude Code.
"""

import datetime
import os
import re
from collections import Counter
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect


# Words too generic to be useful as a "theme"
_STOP_WORDS = frozenset("""
a an and the of to for in on at by with as is was are were be been being it
this that these those i me my we our you your they them their he she him
her his hers but or if so not no yes do does did done can could should would
will may might must have has had having there here when where why how what
which who whom whose all any some many few more most less least other
another such same own about into onto off out over under up down before
after during while because since though although however therefore thus
also too very just only than then now once just like only really still
even ever already always usually often sometimes rarely never each any
both either neither none all every some many few much such ahead back
"""
.split())


def _ensure_tables() -> None:
    """Mirror the DDL from self_improvement.py + reflexion_log."""
    with connect(paths.db) as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS reflexion_log (
                reflexion_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                agent_slug      TEXT NOT NULL,
                went_well       TEXT DEFAULT '',
                could_improve   TEXT DEFAULT '',
                missing_context TEXT DEFAULT '',
                tool_wishes     TEXT DEFAULT '',
                created_at      TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS skill_improvement_proposals (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_slug        TEXT NOT NULL,
                proposed_at       TEXT NOT NULL,
                rationale         TEXT DEFAULT '',
                current_content   TEXT DEFAULT '',
                proposed_content  TEXT NOT NULL,
                status            TEXT DEFAULT 'pending',
                reviewer_note     TEXT DEFAULT ''
            )"""
        )
        con.commit()


def _skill_path(agent_slug: str) -> Path | None:
    """Locate the skill file for an agent. Tries .claude/skills then agents/."""
    candidates = [
        paths.root / ".claude" / "skills" / agent_slug / "skill.md",
        paths.root / "agents" / agent_slug / "skill.md",
        paths.root / "agents" / agent_slug / "system-prompt.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _theme_from(texts: list[str], top_n: int = 3) -> list[tuple[str, int]]:
    """Return the top N noun-ish phrases across a list of free-text reflexions.

    Naive: tokenise, drop stopwords + 1-character tokens, count, return most
    common. Good enough for surfacing recurring themes across a few dozen
    entries; not trying to be a topic model.
    """
    if not texts:
        return []
    counter: Counter[str] = Counter()
    for t in texts:
        if not t:
            continue
        # Lower-case, keep word boundaries
        tokens = re.findall(r"[a-z][a-z\-]{2,}", t.lower())
        for tok in tokens:
            if tok in _STOP_WORDS:
                continue
            counter[tok] += 1
    return counter.most_common(top_n)


def aggregate_reflexions(agent_slug: str | None = None,
                         days: int = 14) -> dict:
    """Theme recent reflexions per agent.

    Returns a dict like::

        {
            "window_days": 14,
            "agents": [
                {
                    "agent_slug": "librarian",
                    "n_reflexions": 12,
                    "could_improve_themes":   [["sources", 5], ...],
                    "missing_context_themes": [...],
                    "tool_wishes_themes":     [...],
                    "samples": {
                        "could_improve":   [..first 3 raw entries..],
                        "missing_context": [...],
                        "tool_wishes":     [...],
                    },
                },
                ...
            ],
            "totals": {"reflexions": 47, "agents": 5},
        }
    """
    _ensure_tables()
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=days)
    ).isoformat()

    where = "WHERE created_at >= ?"
    params: list = [cutoff]
    if agent_slug:
        where += " AND agent_slug = ?"
        params.append(agent_slug)

    with connect(paths.db) as con:
        rows = con.execute(
            f"""SELECT agent_slug, went_well, could_improve, missing_context,
                       tool_wishes, created_at
                FROM reflexion_log {where}
                ORDER BY agent_slug, created_at DESC""",
            params,
        ).fetchall()

    rows = [dict(r) for r in rows]
    by_agent: dict[str, list[dict]] = {}
    for r in rows:
        by_agent.setdefault(r["agent_slug"], []).append(r)

    agents_out: list[dict] = []
    for slug, entries in by_agent.items():
        could_improve = [e["could_improve"] for e in entries if e["could_improve"]]
        missing_context = [e["missing_context"] for e in entries if e["missing_context"]]
        tool_wishes = [e["tool_wishes"] for e in entries if e["tool_wishes"]]
        agents_out.append({
            "agent_slug": slug,
            "n_reflexions": len(entries),
            "could_improve_themes":   _theme_from(could_improve),
            "missing_context_themes": _theme_from(missing_context),
            "tool_wishes_themes":     _theme_from(tool_wishes),
            "samples": {
                "could_improve":   could_improve[:3],
                "missing_context": missing_context[:3],
                "tool_wishes":     tool_wishes[:3],
            },
        })

    # Sort agents by reflexion count, busiest first
    agents_out.sort(key=lambda a: -a["n_reflexions"])

    return {
        "window_days": days,
        "agents": agents_out,
        "totals": {"reflexions": len(rows), "agents": len(by_agent)},
    }


def _format_themes(themes: list[tuple[str, int]]) -> str:
    if not themes:
        return "—"
    return ", ".join(f"`{t}` ({c})" for t, c in themes)


def draft_self_improvement_proposal(agent_slug: str,
                                    days: int = 14) -> dict:
    """Build a draft skill-improvement proposal grounded in reflexion themes.

    Inserts the draft into ``skill_improvement_proposals`` with
    ``status='draft'`` so the user reviews before promoting to ``pending`` or
    approving directly.

    Returns the proposal id and a preview.
    """
    _ensure_tables()
    agg = aggregate_reflexions(agent_slug=agent_slug, days=days)
    if not agg["agents"]:
        return {
            "status": "empty",
            "message": (
                f"No reflexions for `{agent_slug}` in the last {days} days. "
                "Run more agent jobs first, or pick a busier agent."
            ),
        }

    a = agg["agents"][0]
    skill_file = _skill_path(agent_slug)
    current = skill_file.read_text(encoding="utf-8") if skill_file else ""

    rationale = (
        f"Drafted from {a['n_reflexions']} reflexions in the last {days} days. "
        f"Recurring 'could improve' themes: {_format_themes(a['could_improve_themes'])}. "
        f"Recurring 'missing context' themes: {_format_themes(a['missing_context_themes'])}. "
        f"Recurring 'tool wishes': {_format_themes(a['tool_wishes_themes'])}."
    )

    addendum_lines = [
        "",
        "",
        "## Self-improvement notes (draft — review before keeping)",
        "",
        f"_Auto-drafted on {datetime.date.today().isoformat()} from "
        f"{a['n_reflexions']} reflexions over the last {days} days._",
        "",
    ]
    if a["could_improve_themes"]:
        addendum_lines.append(
            f"- **Recurring weaknesses to address**: "
            f"{_format_themes(a['could_improve_themes'])}"
        )
    if a["missing_context_themes"]:
        addendum_lines.append(
            f"- **Context I keep wishing I had**: "
            f"{_format_themes(a['missing_context_themes'])}"
        )
    if a["tool_wishes_themes"]:
        addendum_lines.append(
            f"- **Tools I keep wishing I had**: "
            f"{_format_themes(a['tool_wishes_themes'])}"
        )

    if a["samples"]["could_improve"]:
        addendum_lines.append("")
        addendum_lines.append("Recent verbatim examples:")
        for e in a["samples"]["could_improve"]:
            addendum_lines.append(f"  - {e[:160]}")

    proposed_content = current + "\n".join(addendum_lines)

    now = datetime.datetime.now().isoformat(timespec="seconds")
    with connect(paths.db) as con:
        cur = con.execute(
            """INSERT INTO skill_improvement_proposals
               (agent_slug, proposed_at, rationale, current_content,
                proposed_content, status)
               VALUES (?, ?, ?, ?, ?, 'draft')""",
            (agent_slug, now, rationale, current, proposed_content),
        )
        proposal_id = cur.lastrowid
        con.commit()

    return {
        "status": "ok",
        "proposal_id": proposal_id,
        "agent_slug": agent_slug,
        "rationale": rationale,
        "n_reflexions": a["n_reflexions"],
        "preview": "\n".join(addendum_lines).strip()[:400],
    }


# ── MCP tool wrappers ────────────────────────────────────────────────────────


@app.tool()
async def aggregate_reflexions_tool(agent_slug: str = "",
                                    days: int = 14) -> list[TextContent]:
    """Theme recent reflexions per agent (Phase 9b).

    Reads ``reflexion_log`` entries from the last ``days`` days (default 14)
    and returns the top recurring 'could improve', 'missing context', and
    'tool wishes' themes, ordered by busiest agent.

    Pass ``agent_slug`` to limit the scope; leave blank for all agents.
    """
    result = aggregate_reflexions(
        agent_slug=agent_slug or None,
        days=days,
    )
    if result["totals"]["reflexions"] == 0:
        return [TextContent(
            type="text",
            text=f"No reflexions in the last {days} days. "
                 "Agents need to call write_reflexion to feed this loop.",
        )]
    lines = [
        f"Reflexion themes — last {result['window_days']} days "
        f"({result['totals']['reflexions']} entries across "
        f"{result['totals']['agents']} agents)",
        "",
    ]
    for a in result["agents"]:
        lines.append(f"## {a['agent_slug']}  ({a['n_reflexions']} reflexions)")
        lines.append(
            f"- could_improve:   {_format_themes(a['could_improve_themes'])}"
        )
        lines.append(
            f"- missing_context: {_format_themes(a['missing_context_themes'])}"
        )
        lines.append(
            f"- tool_wishes:     {_format_themes(a['tool_wishes_themes'])}"
        )
        lines.append("")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def draft_self_improvement_proposal_tool(
        agent_slug: str,
        days: int = 14) -> list[TextContent]:
    """Draft a skill-improvement proposal from recent reflexions (Phase 9b).

    Reads themed reflexions for ``agent_slug``, appends a 'Self-improvement
    notes' section to the agent's current skill.md, and queues the result in
    ``skill_improvement_proposals`` with status='draft'.

    The draft is NOT applied. Use ``approve_proposal(id)`` to promote it.
    """
    result = draft_self_improvement_proposal(agent_slug, days=days)
    if result["status"] != "ok":
        return [TextContent(type="text", text=result.get("message", "draft failed"))]
    return [TextContent(
        type="text",
        text=(
            f"Draft proposal #{result['proposal_id']} queued for `{agent_slug}` "
            f"(grounded in {result['n_reflexions']} reflexions).\n\n"
            f"Rationale:\n{result['rationale']}\n\n"
            f"Preview of the new section:\n\n{result['preview']}\n\n"
            "Review with `get_pending_proposals()` (also lists drafts) and "
            "promote with `approve_proposal({pid})`.".format(pid=result["proposal_id"])
        ),
    )]
