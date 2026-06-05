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
import os
from pathlib import Path

import metis_mcp
from metis_mcp.app_instance import app
from metis_mcp.config import paths

_log = logging.getLogger("metis")


# ── Locate the agents/ directory robustly ───────────────────────────────────
def _dir_has_agents(d: Path) -> bool:
    """True if `d` holds at least one agent folder (a subdir with system-prompt.md)."""
    try:
        return any((c / "system-prompt.md").exists() for c in d.iterdir() if c.is_dir())
    except Exception:
        return False


def _resolve_agents_dir() -> Path:
    """Find the agents/ directory, preferring the user's RC but falling back to code.

    Primary is `METIS_RC_ROOT/agents`. When that is absent or empty — e.g. an
    unmounted Docker container where agents ship in the image but METIS_RC_ROOT
    points at an empty data volume — fall back to code-bundled locations so the
    per-agent prompts still register. Without this, only the router + workflow
    prompts appear (6 instead of the full set).
    """
    candidates: list[Path] = [paths.agents]
    code_root = os.environ.get("METIS_CODE_ROOT", "").strip()
    if code_root:
        candidates.append(Path(code_root) / "agents")
    # Package-relative: walk up from the installed package for a sibling agents/
    try:
        for parent in Path(metis_mcp.__file__).resolve().parents:
            candidates.append(parent / "agents")
    except Exception:
        pass
    # Known Docker code locations (Dockerfile COPYs agents here; test mounts at /opt/metis)
    candidates += [Path("/opt/metis/agents"), Path("/app/metis/agents")]
    for c in candidates:
        if c.is_dir() and _dir_has_agents(c):
            if c != paths.agents:
                _log.info("prompts: agents/ resolved to code fallback %s "
                          "(METIS_RC_ROOT/agents absent or empty)", c)
            return c
    return paths.agents  # last resort — primary path even if empty


_AGENTS_DIR = _resolve_agents_dir()


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
        "**If the request describes new or ongoing work** — a study, analysis, paper, "
        "dataset, or tool that the user will keep returning to — treat it as a candidate "
        "**tracked project**, exactly as Claude Code does:\n"
        "- First call `get_project_status()` to see whether it is already tracked (avoid duplicates).\n"
        "- If it is not, **offer to register it**, and on agreement call "
        "`create_project_full(title=..., folder_path=<absolute folder if known>, "
        "category=..., description=...)`. This creates the DB record, writes a CLAUDE.md, "
        "and links it into Claude Desktop — without this step the work is only saved as "
        "loose memory entries and never appears as a project on the dashboard.\n"
        "- Then capture the concrete next steps with `create_task(title=..., "
        "project_id=<id returned above>, notes=...)` so they show up in the Work tab.\n\n"
        "Never invent facts the knowledge base does not support — ground answers in "
        "the library and say so when evidence is thin.\n\n"
        f"**Request:** {request}"
    )


def _read_agent_description(slug: str) -> str:
    """Pull the `description:` line from an agent's skill.md frontmatter (best effort)."""
    skill = _AGENTS_DIR / slug / "skill.md"
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


def _doctor(area: str = "") -> str:
    return (
        "Run a **health check** on this Metis install. Call the `metis_doctor` tool and "
        "render its Metis-branded report verbatim (the `Metis · Research Cortex` block with "
        "✓ / ⚠ / ✗ rows). Then, for every ⚠ or ✗ row, add one plain-language sentence telling "
        "the researcher what it means and the exact next step (no developer jargon). It checks "
        "Python, the database, the Anthropic API key, the embedding/RAG engine, whether the "
        "knowledge layer has indexed docs, agents/skills, the dashboard on :8080, and whether "
        "Metis is registered with Claude Desktop."
    )


def _customize(request: str = "") -> str:
    return (
        "Help the researcher **make Metis their own** — no coding required. Show the "
        "`Metis · Research Cortex — Make It Yours` menu: 1) your projects, 2) the look & "
        "layout, 3) Metis's tone, 4) describe it freely. Route preferences (tone, projects) "
        "directly; route structural changes (look, behaviour, new features) through the RC "
        "Builder agent — but FIRST show the disclaimer that structural changes aren't "
        "guaranteed to keep everything working, it's their Metis, and they can run "
        "`metis_doctor` afterward / revert via git. Never bypass system/config/red-lines.md. "
        "Keep everything in plain language.\n"
        + (f"\nThe researcher already said: {request}\n" if request else "")
    )


def _safe_analysis(request: str = "") -> str:
    return (
        "Help the researcher analyse **sensitive data without ever sending it** — the "
        "'send code, not data' pattern. NON-NEGOTIABLE contract:\n"
        "1. NEVER ask them to paste raw data, individual records, or a file's contents.\n"
        "2. If they paste something that looks like raw/sensitive data, STOP — run "
        "`check_data_safety` on it; if CONFIDENTIAL/SENSITIVE, say so, discard it, and give "
        "them a script that emits only aggregates instead.\n"
        "3. Only request/accept aggregates: column names, types, value counts, ranges, "
        "missingness, summary tables, model coefficients.\n\n"
        "Steps: (a) clarify the goal and data *format* (not values); (b) generate a "
        "self-contained R or Python script they run locally that prints ONLY safe metadata "
        "(never row-level data); (c) when they paste that output, sanity-check it, then do the "
        "real work — dashboard, model interpretation, Table 1, cleaning plan — routing to the "
        "Dashboard Engineer / Biostatistician / Methods Coach / Data Analyst / Writing Partner "
        "as needed. All raw-data computation stays on their machine.\n"
        + (f"\nThe researcher wants to: {request}\n" if request else "")
    )


def _basket(request: str = "") -> str:
    return (
        "Process the researcher's **basket** — the drop-zone `basket/` where they toss "
        "documents without filing them. Steps: call `list_basket()` (NEVER touch `basket/private/`); "
        "for each item infer what it is from the name + a short `read_file()` peek; propose a "
        "destination (papers→`inputs/literature/<topic>/`, scripts→`inputs/code/`, meeting notes→"
        "`inputs/meetings/`, course material→`knowledge/courses/`, datasets→run `check_data_safety` "
        "first and if CONFIDENTIAL/SENSITIVE route to `basket/private/`). Ask a SHORT questionnaire "
        "(1–3 questions, batched by type) to confirm, then `promote_basket_item(source_path, target_path)` "
        "each confirmed file. Report what moved where, and offer the next step (index papers via Librarian, "
        "profile datasets via Data Analyst, structure notes via Meeting Memory)."
        + (f"\nContext: {request}\n" if request else "")
    )


def _research_mode(request: str = "") -> str:
    return (
        "Answer in **research mode — library first, then the web, linked to the researcher's work.**\n"
        "1. Recall their work: `surface_relevant_context(query=...)` (past sessions/findings/projects).\n"
        "2. Library first: `search_pdf_knowledge(...)` + `search_fulltext(...)` (route per rag-routing-rules). "
        "If the library answers it, answer from it with page-level citations, link to their work, and STOP.\n"
        "3. If the library is thin/stale, SAY SO and **ask permission before going to the internet** "
        "(Metis is local-first; never fetch silently, never send their data to look something up).\n"
        "4. On approval, complement via `search_literature`/`scan_openalex` (+ Content Harvester for open-access). "
        "Synthesise, clearly separating LIBRARY (cited, page-level) vs WEB (URL/DOI) vs inference, and tie it to "
        "their projects/findings. Offer to index useful new sources into a background layer so next time it's local.\n"
        + (f"\nQuestion: {request}\n" if request else "")
    )


_WORKFLOW_PROMPTS = {
    "metis-morning": ("Morning briefing — tasks, inbox, news, new papers, today's focus", _morning),
    "safe-analysis": ("Analyse sensitive data without sending it — send code, not data", _safe_analysis),
    "basket": ("Process the basket — classify dropped documents and file them into the right folders", _basket),
    "research-mode": ("Library-first answer, complemented from the web (with your OK), linked to your work", _research_mode),
    "metis-research": ("Start/continue a research session on an article", _research),
    "metis-capture": ("Quick-capture an idea, task, or note into Metis", _capture),
    "metis-handoff": ("Generate a portable context handoff brief", _handoff),
    "metis-weekly": ("Weekly digest — ideas, papers, meetings, projects", _weekly),
    "metis-doctor": ("Health check — is Metis working on this computer?", _doctor),
    "metis-customize": ("Make Metis yours — change projects, look, tone, or anything", _customize),
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
    if not _AGENTS_DIR.is_dir():
        # Expected in bare/standalone contexts — no RC root (e.g. the reinstall
        # verify subprocess) or a data-only Docker volume. Not a failure: there
        # are simply no agent prompts to register. Only the router + workflow
        # prompts will appear. See _resolve_agents_dir() for the fallback chain.
        agent_slugs = []
        _log.info("prompts: agents/ dir absent (%s) — registering router + "
                  "workflow prompts only", _AGENTS_DIR)
    else:
        try:
            agent_slugs = sorted(
                d.name for d in _AGENTS_DIR.iterdir()
                if d.is_dir() and not d.name.startswith(".")
                and (d / "system-prompt.md").exists()
            )
        except Exception as exc:  # noqa: BLE001
            # The dir exists but couldn't be read (permissions, races) — a genuine
            # problem worth surfacing.
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
