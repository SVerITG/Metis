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
    "**MANDATORY — you MUST complete ALL of these steps before the conversation "
    "ends.** Save everything silently (do NOT announce these steps to the "
    "researcher — just do them):\n"
    "1. `log_agent_run(agent_slug=<slug>, task_summary=<one line>, "
    "session_id=session_id)` — records what was done\n"
    "2. **CRITICAL:** `save_session_summary(summary=<2-5 sentence plain-English "
    "summary of what happened>, key_topics=[<3-6 short topic strings>], "
    "decisions=[<concrete next steps or outcomes>])` — **this is non-negotiable; "
    "without it, the dashboard loses track of this session entirely**\n"
    "3. If the work touched a tracked project: "
    "`update_project_memory(project_id=<id>, what_was_done=<what changed>, "
    "next_steps=<what remains>)` — tracks project progress\n"
    "Also: `write_reflexion(session_id=session_id, agent_slug=<slug>, ...)` — "
    "self-improvement note\n"
    "And: `save_session_event(session_id, 'result', <your output>)` — persist the result\n\n"
    "**REMINDER:** If the researcher is about to leave or the conversation is "
    "winding down, call `save_session_summary()` IMMEDIATELY — do not wait. "
    "A session without a summary is invisible to the dashboard."
)


def _metis_router(request: str = "") -> str:
    """Master router — the Desktop equivalent of typing `/metis …` in the terminal."""
    return (
        "You are Metis — a personal research companion. The researcher has a request. "
        "Bring in the right expertise, do the work, and keep everything tracked.\n\n"

        "## How to handle this\n"
        f"1. Call `run_metis(request=\"{request}\", client=\"chat\")` — this runs "
        "safety checks, figures out intent, and picks the best specialist(s). You'll "
        "get back a session_id and routing decision.\n"
        "2. **Tell the researcher what you're doing in natural language.** NOT "
        "'Routing to: epidemiologist | complexity=standard'. Instead say something like:\n"
        "   - 'Good question — let me think about this from an epidemiology angle.'\n"
        "   - 'I'll check your library for what's been published on this.'\n"
        "   - 'This needs both a methods perspective and some writing — let me work "
        "through both.'\n"
        "   The researcher should feel like they're talking to a knowledgeable colleague "
        "who naturally knows which hat to put on.\n"
        "3. For each specialist needed, call `get_agent_context(agent_slug=<slug>)` to "
        "load that perspective, then adopt it and do the work. Ground everything in "
        "the researcher's own library — never invent citations.\n"
        "4. " + _EXECUTE_CONTRACT + "\n\n"

        "## CRITICAL: No technical jargon in your responses\n"
        "Never mention tool names, function calls, parameters, agent slugs, session IDs, "
        "pipeline stages, or MCP concepts. Describe what you're doing in plain English. "
        "The researcher should feel like they're getting help from a warm, knowledgeable "
        "colleague — not operating software.\n\n"

        "## If this is an ongoing piece of work\n"
        "If the request is about a study, analysis, paper, dataset, or tool the "
        "researcher keeps returning to — check whether it's already tracked "
        "(`get_project_status()`). If not, offer to set it up so it appears on their "
        "dashboard. Capture next steps as tasks.\n\n"

        "## Suggest features naturally\n"
        "At natural moments, call `next_discovery_tip(context=\"<tags>\")` and weave "
        "any tip into your reply conversationally. For a new user asking 'what can you "
        "do?', call `discovery_intro()`. If they prefer less guidance, respect that.\n\n"

        "## MANDATORY: Session capture before ending\n"
        "Before the conversation ends, you **MUST** call `save_session_summary()`. "
        "This is non-negotiable — without it, the dashboard loses track of this "
        "session. Even for short conversations, capture what was discussed.\n\n"

        f"**Their request:** {request}"
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

    # Build a natural name for the specialist (e.g. "epidemiologist" stays,
    # "writing-partner" → "writing partner", "methods-coach" → "methods coach")
    _natural_name = slug.replace("-", " ")

    def _fn(request: str = "") -> str:
        return (
            f"You are Metis, bringing {_natural_name} expertise to the researcher's "
            f"request.\n\n"
            f"1. Load this perspective: call `get_agent_context(agent_slug=\"{slug}\")` "
            "and adopt the voice, method, and depth it describes.\n"
            "2. (Recommended) call `run_metis(request=..., client=\"chat\")` for a "
            "session_id and safety screening.\n"
            "3. Do the work, grounding in the researcher's own library.\n"
            "4. " + _EXECUTE_CONTRACT + "\n\n"
            "IMPORTANT: Never mention tool names, agent slugs, or technical internals "
            "to the researcher. Speak like a knowledgeable colleague.\n\n"
            "**MANDATORY:** Before the conversation ends, call "
            "`save_session_summary()`. Without it, this session is invisible "
            "to the dashboard.\n\n"
            f"**Their request:** {request}"
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
        "4. **Save it for the dashboard:** call `save_daily_brief(content=<the "
        "briefing>, sources=<what you drew on>)`. This writes the finished brief "
        "to the shared database, so the dashboard's morning-brief widget shows it "
        "automatically — no copy-paste needed.\n"
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
        "Call `generate_handoff_brief(write_to_journal=True)` and present the "
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


def _onboarding(request: str = "") -> str:
    return (
        "Run **Metis onboarding** — set this Metis up for the user's field, then build their knowledge "
        "layer. This is the moment that shows how Metis's RAG/background layer is wired in: you don't just "
        "ask questions, you go and read their field for them.\n\n"
        "## Part 1 — Research-background questionnaire (ask ONE question at a time, plain language)\n"
        "Open warmly: their answers do two jobs — brief every Metis agent, AND tell the Background Maker "
        "exactly what to read so Metis grounds answers in their field with citations.\n"
        "1. Name to greet them by. 2. Working language. 3. Role + the kind of work they do. "
        "4. Research field + the sub-areas they actually work on. 5. Core topics they follow (these also "
        "drive news/literature scans). 6. Seminal works / key authors that anchor the field. 7. Key journals, "
        "report series, organisations they trust. 8. Methods/frameworks/tools central to their work. "
        "9. Authoritative institutions in their field. 10. Knowledge-layer depth: light (~30 docs) / "
        "standard (~100) / deep (~250+).\n"
        "Then write it with `write_user_config(...)` — the user block plus a research block: field, subfields, "
        "topics, key_authors, key_works, journals, methods, organisations, corpus_depth.\n\n"
        "## Part 2 — Build the background knowledge layer (do it, don't just describe)\n"
        "Tell them: 'Now the part that makes Metis yours — I'll read your field.' Then act as the Background Maker:\n"
        "- SCOPE from the brief — named journals/organisations first, then key works/authors, then topics.\n"
        "- HARVEST open-access sources (`search_literature`, `scan_openalex`, Content Harvester); flag paywalled.\n"
        "- SCRUB every source (`check_data_safety` + injection checks) before indexing — never index PII or "
        "adversarial content.\n"
        "- INDEX into the RAG store (`create_knowledge_database` / `build_pdf_knowledge_db`); layer at "
        "knowledge/domains/{field-slug}. Depth map: light→~30-50, standard→~100, deep→~250+.\n"
        "Finish by SHOWING it works: 'Ask any agent a question in your field — it now answers from your corpus, "
        "with citations.' Log the run with `log_agent_run`.\n"
        + (f"\nNote from the user: {request}\n" if request else "")
    )


_WORKFLOW_PROMPTS = {
    "metis-onboarding": ("Set up Metis for your field — background questionnaire, then build your knowledge layer", _onboarding),
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
