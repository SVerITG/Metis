"""Progressive tool disclosure ("tool search") for the Metis MCP server.

The server registers ~200 tools. Loading every definition into the client's
context on every session is expensive and degrades the model's tool-selection
accuracy. This module implements the same pattern Claude Code itself uses:

  * a small **core** set of everyday tools stays loaded and callable always;
  * every other tool is **parked** (removed from the live tool list but kept in
    a registry) until the model asks for it;
  * ``find_tools(query)`` and ``load_tool_group(name)`` move parked tools back
    into the live list on demand and fire a ``tools/list_changed`` notification
    so the client re-fetches and can call them natively.

Activated only when ``METIS_TOOL_SEARCH=1``. When the flag is unset this module
is inert (the meta-tools still register, but nothing is parked), so the server
behaves exactly as before. Core membership and groups live in
``system/config/tool-subsets.json`` (keys ``core`` and ``groups``), so the
everyday set can be tuned without code changes.

Design mirrors subset_loader.py: tools are stored in ``app._tool_manager._tools``
(a plain dict name -> Tool), so parking is a ``pop`` and activating is a
re-insert. No tool is ever lost — parked tools remain fully callable the moment
they are re-exposed.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import Context
from mcp.types import TextContent

from metis_mcp.app_instance import app

log = logging.getLogger("metis.tool_search")

# Modules whose tools must never be parked — the meta-tools themselves plus the
# minimum every session needs even before any find_tools call. This is a
# fallback; the authoritative list is the "core" key in tool-subsets.json.
_HARD_CORE = {"tool_search"}

# name -> Tool, for every parked (hidden) tool. Populated by partition_tools().
_PARKED: dict[str, object] = {}
# name -> short module name (e.g. "dhis2"), for search + group resolution.
_TOOL_MODULE: dict[str, str] = {}
# group name -> list of module short-names (from tool-subsets.json "groups").
_GROUPS: dict[str, list[str]] = {}
# whether partitioning actually ran (flag was on).
_ACTIVE = False


def _config_path() -> Path:
    return Path(os.environ.get("METIS_RC_ROOT", "")) / "system" / "config" / "tool-subsets.json"


def _load_config() -> dict:
    p = _config_path()
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("tool_search: could not read %s: %s", p, exc)
        return {}


def _short_module(tool) -> str:
    fn = getattr(tool, "fn", None)
    mod = getattr(fn, "__module__", "") or ""
    return mod.split(".")[-1] if "." in mod else mod


def partition_tools(app_) -> int:
    """Move all non-core tools into the parked registry. Returns parked count.

    Idempotent and safe: only runs when METIS_TOOL_SEARCH=1. Core modules come
    from tool-subsets.json ("core" key) plus _HARD_CORE. Everything else is
    popped from the live tool manager and held in _PARKED until requested.
    """
    global _ACTIVE
    if os.environ.get("METIS_TOOL_SEARCH", "0") != "1":
        return 0

    config = _load_config()
    core_modules = set(config.get("core") or []) | _HARD_CORE
    _GROUPS.update(config.get("groups") or {})

    mgr = app_._tool_manager
    # Snapshot first — we mutate the dict while iterating.
    for name, tool in list(mgr._tools.items()):
        short = _short_module(tool)
        _TOOL_MODULE[name] = short
        if short in core_modules:
            continue
        _PARKED[name] = mgr._tools.pop(name)

    _ACTIVE = True
    log.info(
        "tool_search: %d tools parked, %d kept as core (modules: %s)",
        len(_PARKED), len(mgr._tools), ", ".join(sorted(core_modules)),
    )
    return len(_PARKED)


def _groups_for_module(short: str) -> list[str]:
    return [g for g, mods in _GROUPS.items() if short in mods]


def _activate(names: list[str]) -> list[str]:
    """Move named tools from parked -> live. Returns the names actually moved."""
    moved = []
    mgr = app._tool_manager
    for n in names:
        if n in _PARKED and n not in mgr._tools:
            mgr._tools[n] = _PARKED.pop(n)
            moved.append(n)
    return moved


async def _notify(ctx: Context | None) -> None:
    """Best-effort tools/list_changed so the client re-fetches the tool list."""
    try:
        session = ctx.session if ctx is not None else app.get_context().session
        await session.send_tool_list_changed()
    except Exception as exc:  # notification is best-effort; never fail the call
        log.debug("tool_search: list_changed notify skipped: %s", exc)


def _score(query: str, name: str, desc: str) -> int:
    terms = [t for t in query.lower().split() if t]
    if not terms:
        return 0
    name_l, desc_l = name.lower(), (desc or "").lower()
    score = 0
    for t in terms:
        if t in name_l:
            score += 3          # name match is the strongest signal
        elif t in desc_l:
            score += 1
    return score


@app.tool()
async def find_tools(query: str, limit: int = 8, ctx: Context = None) -> list[TextContent]:
    """Search Metis's full tool catalogue and load the matching tools on demand.

    Most Metis tools are kept out of the active set to save context; this finds the
    ones you need by keyword (e.g. "dhis2 tracker", "clean dataset", "backup",
    "knowledge graph", "transcribe"), makes them callable, and returns their names.
    After calling this, call the returned tools directly as normal.

    Args:
        query: Keywords describing what you want to do.
        limit: Max tools to return/load (default 8).
    """
    if not _ACTIVE:
        return [TextContent(type="text", text=(
            "Tool search is not active (METIS_TOOL_SEARCH is off) — all tools are "
            "already loaded and callable directly."))]

    mgr = app._tool_manager
    # Search parked tools (hidden) and note already-active matches too.
    scored: list[tuple[int, str, str, bool]] = []
    for name, tool in _PARKED.items():
        s = _score(query, name, getattr(tool, "description", "") or "")
        if s > 0:
            scored.append((s, name, getattr(tool, "description", "") or "", False))
    for name, tool in mgr._tools.items():
        s = _score(query, name, getattr(tool, "description", "") or "")
        if s > 0:
            scored.append((s, name, getattr(tool, "description", "") or "", True))

    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[:max(1, limit)]
    if not top:
        groups = ", ".join(sorted(_GROUPS)) or "(none)"
        return [TextContent(type="text", text=(
            f"No tools matched '{query}'. Try broader keywords, or load a whole "
            f"group with load_tool_group(group=...). Groups: {groups}"))]

    to_load = [n for _, n, _, active in top if not active]
    moved = _activate(to_load)
    if moved:
        await _notify(ctx)

    lines = [f"Found {len(top)} tool(s) for '{query}'"
             + (f" — loaded {len(moved)}, now callable directly:" if moved else ":")]
    for s, name, desc, was_active in top:
        first = (desc or "").strip().splitlines()[0] if desc else ""
        if len(first) > 100:
            first = first[:97] + "..."
        tag = "already active" if was_active else "loaded"
        grp = _groups_for_module(_TOOL_MODULE.get(name, ""))
        grp_s = f" [{grp[0]}]" if grp else ""
        lines.append(f"  • {name}{grp_s} — {first} ({tag})")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def load_tool_group(group: str, ctx: Context = None) -> list[TextContent]:
    """Load every tool in a named group at once (see list_tool_groups for names).

    Use this when you know you'll do several related operations — e.g. group
    "data" for a full dataset-cleaning session, "specialist" for DHIS2 work.
    """
    if not _ACTIVE:
        return [TextContent(type="text", text="Tool search is off — all tools already loaded.")]
    mods = _GROUPS.get(group)
    if not mods:
        return [TextContent(type="text", text=(
            f"Unknown group '{group}'. Available: {', '.join(sorted(_GROUPS)) or '(none)'}"))]
    names = [n for n, short in _TOOL_MODULE.items() if short in mods and n in _PARKED]
    moved = _activate(names)
    if moved:
        await _notify(ctx)
    if not moved:
        return [TextContent(type="text", text=f"Group '{group}' is already fully loaded.")]
    return [TextContent(type="text", text=(
        f"Loaded {len(moved)} tool(s) from group '{group}', now callable directly:\n  "
        + "\n  ".join(sorted(moved))))]


@app.tool()
async def list_tool_groups(ctx: Context = None) -> list[TextContent]:
    """List the tool groups that can be loaded on demand, with how many are parked."""
    if not _ACTIVE:
        return [TextContent(type="text", text="Tool search is off — all tools already loaded.")]
    lines = [f"{len(_PARKED)} tool(s) currently parked (loadable on demand). Groups:"]
    for g in sorted(_GROUPS):
        mods = _GROUPS[g]
        parked = sum(1 for n, s in _TOOL_MODULE.items() if s in mods and n in _PARKED)
        total = sum(1 for n, s in _TOOL_MODULE.items() if s in mods)
        lines.append(f"  • {g}: {parked}/{total} parked  ({', '.join(mods)})")
    lines.append("\nUse find_tools(query=...) for keyword search, or "
                 "load_tool_group(group=...) to load a whole group.")
    return [TextContent(type="text", text="\n".join(lines))]
