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
        "Metis is a research companion for Claude that keeps your data on your machine. "
        "It gives Claude a persistent "
        "memory of your field, your papers, and your working history, and routes each "
        "request to one of 30+ specialist skills — Librarian, Methods Coach, Writing "
        "Partner, Meeting Memory, Epidemiologist, Course Builder, and more. Knowledge "
        "answers are cited from the researcher's own indexed library, never invented. "
        "Everything you capture — papers, meeting transcripts, ideas, notes, journal "
        "entries and tasks — is automatically cross-pollinated, so related work surfaces "
        "across time without you searching for it. Each week Metis also reviews its own "
        "performance and drafts behaviour improvements for your approval. "
        "Your documents, notes, embeddings and memory stay on your machine; reasoning "
        "runs on the Claude API."
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
