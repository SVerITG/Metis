"""Singleton FastMCP application instance.

Kept in a separate module so that both server.py and the tool modules
can import `app` without triggering a circular import.

Auto-titling: wraps app.tool() so every Metis tool gets a human-readable
title prefixed with "Metis . Agent — Tool Name".  Uses inspect.stack()
to detect which tool module is registering each tool, then maps module
filename to agent name — zero changes needed in any existing tool file.
Individual tools can still override with an explicit title= argument.
"""
from __future__ import annotations

import inspect
import os
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

app = FastMCP(
    "metis-rc",
    instructions=(
        "You ARE Metis — a personal research companion. Everything stays on the "
        "researcher's machine. You follow their work across sessions and bring the "
        "right expertise to each question.\n\n"

        "## Your voice\n"
        "You are a warm, knowledgeable colleague — not a chatbot, not a tool. "
        "Speak in plain English. Use the researcher's name (from `get_user_profile()`). "
        "Adapt to their `style` preferences returned by that call:\n"
        "- `warmth`: warm (default) / neutral / formal\n"
        "- `response_length`: concise / moderate / detailed\n"
        "- `feedback_style`: gentle / direct / challenging\n"
        "- `challenge_level`: supportive / balanced / rigorous\n"
        "- `detail_level`: brief / balanced / thorough\n\n"

        "## CRITICAL: Never expose internals\n"
        "The researcher should feel like they're talking to a knowledgeable person, "
        "not operating an MCP server. NEVER:\n"
        "- Mention tool names (don't say 'calling search_literature' — say "
        "'let me check your library')\n"
        "- Show function signatures, parameter names, or JSON\n"
        "- Say 'routing to agent X' — instead say something natural like "
        "'Let me think about this from an epidemiology angle' or "
        "'I'll pull in some writing expertise for this'\n"
        "- Use terms like 'MCP', 'tool', 'agent_slug', 'session_id', 'pipeline'\n"
        "- Show raw error traces — translate them into plain language\n\n"

        "## At session start\n"
        "1. Call `get_user_profile()` to load name, field, interests, and style.\n"
        "2. Greet naturally. If this is a continuing conversation, pick up where "
        "you left off.\n\n"

        "## How you work (invisible to the researcher)\n"
        "For substantive requests, bring in the right expertise:\n"
        "1. Call `run_metis(request=..., client=\"chat\")` — this handles safety, "
        "intent, and specialist selection behind the scenes.\n"
        "2. Announce naturally: instead of 'Routing to: epidemiologist', say "
        "something like 'Good question — let me look at this as an epi problem' "
        "or 'I'll check what your library has on this'.\n"
        "3. Load the specialist context with `get_agent_context(agent_slug=...)` "
        "and adopt that perspective to do the work.\n"
        "4. Ground answers in the researcher's own indexed library. Never invent "
        "citations.\n\n"

        "## Routing guide\n"
        "Paper/source → librarian | Study design/epi → epidemiologist | "
        "Stats method → methods-coach | Manuscript/writing → writing-partner | "
        "DHIS2 → dhis2-expert | Code/R/Python → software-engineer | "
        "PhD structure → phd-architect | Meeting notes → meeting-memory | "
        "News/briefing → news-radar | Dataset/cleaning → data-analyst | "
        "New app/tool → builder | Extend Metis → rc-builder | "
        "Course/teaching → course-builder | Unclear → ask one question\n\n"

        "## After finishing work — save it (silently)\n"
        "Record in all three memory layers without announcing it:\n"
        "1. `log_agent_run(...)` — what the specialist did\n"
        "2. `save_session_summary(...)` — what happened this session\n"
        "3. If it touched a tracked project: `update_project_memory(...)` — "
        "what changed and what's next\n"
        "Also: `write_reflexion(...)` for continuous improvement.\n\n"

        "## Projects\n"
        "If the work describes new or ongoing research, check `get_project_status()`. "
        "Offer to track it if it's not already. Capture next steps with "
        "`create_task(...)`. This keeps the dashboard current.\n\n"

        "## Discovery\n"
        "At natural moments, call `next_discovery_tip(context=...)` and weave any "
        "tip into your reply conversationally. It self-limits and never repeats."
    ),
    website_url="https://github.com/SVerITG/Metis_PH",
)


# ── Agent-aware auto-title wrapper ────────────────────────────────────────
# Monkey-patch app.tool() so every registered tool automatically receives a
# human-readable title like "Metis . Librarian — Search Literature" unless
# one is already set.  The agent label is detected from the calling module
# filename via inspect.stack() — no tool file needs any changes.

_original_tool = app.tool

# Module filename stem → agent display name.
# Modules not listed here fall through to plain "Metis" (core tools).
_MODULE_AGENT: dict[str, str] = {
    # Librarian
    "literature":         "Librarian",
    "library":            "Librarian",
    "zotero":             "Librarian",
    "ref_miner":          "Librarian",
    "fulltext_index":     "Librarian",
    "literature_monitor": "Librarian",
    "paperqa_search":     "Librarian",
    "knowledge_db":       "Librarian",
    # Data Guardian
    "safety":             "Data Guardian",
    "guardrails":         "Data Guardian",
    "anonymization":      "Data Guardian",
    # Memory Curator
    "memory":             "Memory Curator",
    "vector_memory":      "Memory Curator",
    "session_memory":     "Memory Curator",
    "memory_curator":     "Memory Curator",
    "memory_gateway":     "Memory Curator",
    # Data Analyst
    "data_tools":         "Data Analyst",
    # Software Engineer
    "script_analyzer":    "Software Engineer",
    "code_repository":    "Software Engineer",
    # Meeting Memory
    "transcription":      "Meeting Memory",
    "meetings":           "Meeting Memory",
    # News Radar
    "intelligence":       "News Radar",
    "content_scan":       "News Radar",
    # Course Builder
    "course_builder":     "Course Builder",
    # DHIS2 Expert
    "dhis2":              "DHIS2 Expert",
    # Metis (explicit — brainstorm is a Metis-core feature)
    "brainstorm":         "Metis",
}


def _caller_agent() -> str:
    """Detect which agent owns the tool being registered.

    Scans stack frames 1-6 looking for a module filename that matches
    our _MODULE_AGENT mapping.  Returns the agent name, or empty string
    for core Metis tools (no agent suffix needed).
    """
    try:
        frames = inspect.stack()
        for frame_info in frames[1:7]:
            filename = os.path.basename(frame_info.filename)
            stem = os.path.splitext(filename)[0]
            if stem in _MODULE_AGENT:
                agent = _MODULE_AGENT[stem]
                # "Metis" in the map means the tool is explicitly Metis-core
                return "" if agent == "Metis" else agent
        return ""
    except Exception:
        return ""


def _prettify_name(func_name: str) -> str:
    """Convert snake_case function name to Title Case label.

    Examples:
        search_memory       -> Search Memory
        get_agent_context   -> Get Agent Context
        recall              -> Recall
        kg_index_memory     -> KG Index Memory
    """
    return func_name.replace("_", " ").title().replace("Kg ", "KG ").replace("Dhis2", "DHIS2")


def _build_title(func_name: str) -> str:
    """Build a full title like 'Metis . Librarian — Search Literature'."""
    agent = _caller_agent()
    label = _prettify_name(func_name)
    if agent:
        return f"Metis \u00b7 {agent} \u2014 {label}"
    return f"Metis \u2014 {label}"


def _auto_titled_tool(
    *args: Any, **kwargs: Any
) -> Callable:
    """Wrapper around FastMCP.tool() that injects a Metis-prefixed title."""

    def _decorator(fn: Callable) -> Callable:
        if "title" not in kwargs or kwargs["title"] is None:
            kwargs["title"] = _build_title(fn.__name__)
        return _original_tool(*args, **kwargs)(fn)

    # If called as @app.tool (no parens), args[0] is the function itself
    if args and callable(args[0]) and not kwargs:
        fn = args[0]
        title = _build_title(fn.__name__)
        return _original_tool(title=title)(fn)

    return _decorator


app.tool = _auto_titled_tool  # type: ignore[method-assign]
