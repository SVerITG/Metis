"""MCP prompts — make Metis routing and agents reachable in Claude Desktop.

Claude Desktop does not read CLAUDE.md and has no access to the Claude Code
skills in `.claude/skills/`. It only sees what the MCP server exposes. Tools
alone make Metis a toolbox, not an orchestrator — Desktop has no instruction
telling it to route, announce the chosen agent(s), adopt the agent persona, or
log the run.

This module closes that gap by registering MCP **prompts**. Claude Desktop
surfaces prompts in its prompt menu (the `+` / "Add from Metis" picker). Each
prompt returns an instruction block that drives the same workflow Claude Code
gets from CLAUDE.md + the skills:

  * `metis`           — master router. Calls run_metis(), states the routing
                        line, loads + adopts the chosen agent(s), logs the run.
  * one per agent     — e.g. `epidemiologist`, `librarian` … loads that agent's
                        system prompt via get_agent_context() and adopts it.
  * workflow prompts  — morning briefing, research session, capture, handoff,
                        weekly — the high-traffic Code skills, mirrored.

Registration is defensive: a malformed agent folder is skipped, never fatal.
The module is loaded by server.py exactly like a tool module.
"""

from __future__ import annotations

import logging

from metis_mcp.app_instance import app
from metis_mcp.config import paths

_log = logging.getLogger("metis")


# ── Shared workflow contract ────────────────────────────────────────────────
# The discipline every routed turn follows, so Desktop behaves like Code.
_EXECUTE_CONTRACT = (
    "After you finish the work, close the loop the way Metis expects:\n"
    "- `save_session_event(session_id, 'result', <your output>)` — persist the result\n"
    "- `log_agent_run(agent_slug=<slug>, task_summary=<one line>, session_id=session_id)` "
    "— audit trail (this is also what keeps the dashboard's Agents tab and run-coverage accurate)\n"
    "- `write_reflexion(session_id=session_id, agent_slug=<slug>, ...)` — brief self-critique"
)


def _metis_router(request: str = "") -> str:
    """Master router — the Desktop equivalent of typing `/metis …` in the terminal."""
    return (
        "You are operating inside the **Metis Research Cortex** for the researcher. "
        "The user has a request and wants Metis to "
        "route it to the right specialist agent(s), exactly as the `/metis` command "
        "does in Claude Code.\n\n"
        "**Do this in order:**\n"
        f"1. Call `run_metis(request=\"{request}\", client=\"chat\")`. It runs the "
        "11-stage pipeline (safety + injection checks, intent parsing, agent "
        "selection, model/budget, surgical context) and returns a session_id plus a "
        "line like `**Routing:** epidemiologist, writing-partner | complexity=chain`.\n"
        "2. **Tell the user that routing line** — name the agent(s) and complexity "
        "before doing the work, so they can see who is handling it.\n"
        "3. For **each** agent named, call `get_agent_context(agent_slug=<slug>)` to "
        "load that agent's system prompt + contract, then **adopt that persona** and "
        "do the work, using the Metis MCP tools (search_library, ask_library, "
        "search_pdf_knowledge, semantic_search, etc.) for grounding.\n"
        "4. " + _EXECUTE_CONTRACT + "\n\n"
        "Never invent facts the knowledge base does not support — ground answers in "
        "the library and say so when evidence is thin.\n\n"
        f"**Request:** {request}"
    )


def _read_agent_description(slug: str) -> str:
    """Pull the `description:` line from an agent's skill.md frontmatter (best effort)."""
    skill = paths.agents / slug / "skill.md"
    try:
        text = skill.read_text(encoding="utf-8")
    except Exception:
        return f"Invoke the {slug} agent."
    in_fm = False
    for line in text.splitlines():
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and line.lower().startswith("description:"):
            desc = line.split(":", 1)[1].strip().strip('"').strip("'")
            # Keep the menu entry short — first sentence is plenty.
            first = desc.split(". ")[0].strip()
            return (first[:240] + "…") if len(first) > 241 else first
    return f"Invoke the {slug} agent."


def _make_agent_prompt(slug: str):
    """Build a prompt fn that loads + adopts a specific agent (closure over slug)."""

    def _fn(request: str = "") -> str:
        return (
            f"You are operating inside the **Metis Research Cortex** for the researcher. "
            f"Act as the **{slug}** agent.\n\n"
            f"1. Call `get_agent_context(agent_slug=\"{slug}\")` to load this agent's "
            "system prompt and contract, then fully adopt that persona, voice, and "
            "method.\n"
            "2. (Optional but recommended) call `run_metis(request=..., client=\"chat\")` "
            "first if you want a session_id, safety screening, and surgical context.\n"
            "3. Do the work, grounding in the Metis library / knowledge tools.\n"
            "4. " + _EXECUTE_CONTRACT + "\n\n"
            f"**Request:** {request}"
        )

    _fn.__name__ = "agent_" + slug.replace("-", "_")
    _fn.__doc__ = _read_agent_description(slug)
    return _fn


# ── Workflow prompts — the high-traffic Code skills, mirrored for Desktop ────
def _morning(focus: str = "") -> str:
    return (
        "Produce the **morning briefing** inside the Metis Research Cortex.\n\n"
        "1. Call `session_bootstrap(client=\"chat\")` for a session_id + recent context.\n"
        "2. Pull together: `get_tasks` (overdue / blocked / in-progress), "
        "`scan_inbox`, `get_news_briefs`, `get_new_publications`, and "
        "`get_project_status`.\n"
        "3. Synthesise a concise briefing: what's pressing today, what's new "
        "overnight (news + literature), what's blocked, and one suggested focus.\n"
        + (f"\nUser's stated focus for today: {focus}\n" if focus else "")
    )


def _research(article: str = "") -> str:
    return (
        "Start a **research session** inside the Metis Research Cortex.\n\n"
        "1. `session_bootstrap(client=\"chat\")`, then `get_research_context` and "
        "`scan_tracked_files` to load article state and detect changes.\n"
        "2. Summarise where the work stands and suggest the next concrete step.\n"
        "3. If the user names an article, load its context and continue the draft.\n"
        + (f"\nArticle / focus: {article}\n" if article else "")
    )


def _capture(note: str = "") -> str:
    return (
        "**Quick capture** into the Metis Research Cortex. Decide whether this is an "
        "idea, a task, or a note, then route it:\n"
        "- idea → `capture_idea` (and `find_connections` to surface links)\n"
        "- task → `create_task`\n"
        "- note/journal → `add_journal_entry`\n"
        "Confirm back to the user what was captured and where.\n\n"
        f"**Capture:** {note}"
    )


def _handoff(reason: str = "") -> str:
    return (
        "Generate a **portable handoff brief** for the current Metis session so work "
        "can continue in another AI or device.\n\n"
        "Call `generate_handoff_brief_tool(write_to_journal=True)` and present the "
        "brief. Include current state, open decisions, and the next concrete step.\n"
        + (f"\nReason for handoff: {reason}\n" if reason else "")
    )


def _weekly(period: str = "") -> str:
    return (
        "Produce the **weekly summary** from the Metis Research Cortex: ideas "
        "captured, papers added, meetings, project movement, and active research. "
        "Pull from `get_ideas`, `get_new_publications`, `get_project_status`, "
        "`get_journal`, and `get_agent_runs`, then synthesise a tight digest."
    )


_WORKFLOW_PROMPTS = {
    "metis-morning": ("Morning briefing — tasks, inbox, news, new papers, today's focus", _morning),
    "metis-research": ("Start/continue a research session on an article", _research),
    "metis-capture": ("Quick-capture an idea, task, or note into Metis", _capture),
    "metis-handoff": ("Generate a portable context handoff brief", _handoff),
    "metis-weekly": ("Weekly digest — ideas, papers, meetings, projects", _weekly),
}


def register_prompts() -> dict:
    """Register all Metis prompts on the FastMCP app. Returns a small summary dict."""
    from mcp.server.fastmcp.prompts.base import Prompt

    registered: list[str] = []
    failed: dict[str, str] = {}

    # 1) Master router
    try:
        app.add_prompt(Prompt.from_function(
            _metis_router,
            name="metis",
            title="Metis — route any request",
            description=(
                "Default entry point. Routes your request to the right specialist "
                "agent(s), announces the routing, does the work, and logs it."
            ),
        ))
        registered.append("metis")
    except Exception as exc:  # noqa: BLE001
        failed["metis"] = f"{type(exc).__name__}: {exc}"

    # 2) One prompt per agent (read dynamically from agents/)
    try:
        agent_slugs = sorted(
            d.name for d in paths.agents.iterdir()
            if d.is_dir() and not d.name.startswith(".")
            and (d / "system-prompt.md").exists()
        )
    except Exception as exc:  # noqa: BLE001
        agent_slugs = []
        failed["_agent_enumeration"] = f"{type(exc).__name__}: {exc}"

    for slug in agent_slugs:
        if slug == "metis":
            continue  # the router already covers Metis herself
        try:
            fn = _make_agent_prompt(slug)
            app.add_prompt(Prompt.from_function(
                fn,
                name=slug,
                title=slug.replace("-", " ").title(),
                description=_read_agent_description(slug),
            ))
            registered.append(slug)
        except Exception as exc:  # noqa: BLE001
            failed[slug] = f"{type(exc).__name__}: {exc}"

    # 3) Workflow prompts
    for name, (desc, fn) in _WORKFLOW_PROMPTS.items():
        try:
            app.add_prompt(Prompt.from_function(
                fn, name=name, title=desc.split(" — ")[0], description=desc,
            ))
            registered.append(name)
        except Exception as exc:  # noqa: BLE001
            failed[name] = f"{type(exc).__name__}: {exc}"

    if failed:
        _log.warning("prompts: %d registered, %d failed: %s",
                     len(registered), len(failed), ", ".join(failed))
    else:
        _log.info("prompts: %d registered", len(registered))

    return {"registered": registered, "failed": failed}


# Register on import (mirrors how tool modules self-register via @app.tool()).
_SUMMARY = register_prompts()
