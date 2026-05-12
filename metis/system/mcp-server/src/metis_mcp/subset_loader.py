"""Domain-specific tool loading for Metis MCP server.

When METIS_TOOL_SUBSETS=1 and METIS_AGENT_SUBSET=<slug> are set, the MCP
server exposes only the tools relevant to that agent rather than all ~80.

Estimated token savings: 50–80% on the tools/list response, which Claude
Code includes in every API call context when using an MCP server.

Usage — set before starting the MCP server:
  export METIS_TOOL_SUBSETS=1
  export METIS_AGENT_SUBSET=librarian

Or per-session in run.sh:
  METIS_TOOL_SUBSETS=1 METIS_AGENT_SUBSET="$1" exec "$VENV_DIR/bin/python3" -m metis_mcp.server

The ALWAYS_ALLOWED set is never filtered — it contains infrastructure tools
that every agent needs (profile, logging, handoff, pipeline).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

log = logging.getLogger("metis.subset_loader")

# Tools these modules provide are always exposed — every agent needs them.
ALWAYS_ALLOWED_MODULES = {
    "agents",
    "pipeline",
    "user_profile",
    "observability",
    "handoff",
    "improvement",
    "self_improvement",
    "safety",
    "guardrails",
    "config_tools",
}


def _load_config() -> dict:
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if not rc_root:
        return {}
    p = Path(rc_root) / "system" / "config" / "tool-subsets.json"
    if not p.exists():
        log.warning("tool-subsets.json not found at %s", p)
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Failed to read tool-subsets.json: %s", exc)
        return {}


def apply_tool_subset(app: FastMCP, agent_slug: str) -> int:
    """Remove tools not in the agent's declared subset from the tool manager.

    Modifies app._tool_manager._tools in-place. Tools in ALWAYS_ALLOWED_MODULES
    are never removed. Returns the number of tools removed.

    Args:
        app: The FastMCP application instance.
        agent_slug: Agent slug from tool-subsets.json agents map (e.g. "librarian").

    Returns:
        Number of tools removed.
    """
    config = _load_config()
    if not config:
        return 0

    agents_map: dict = config.get("agents", {})
    groups_map: dict = config.get("groups", {})

    agent_groups = agents_map.get(agent_slug)
    if agent_groups is None:
        agent_groups = agents_map.get("_default", "all")

    if agent_groups == "all":
        log.info("subset_loader: agent '%s' maps to 'all' — no filtering", agent_slug)
        return 0

    # Flatten group names → set of allowed module short-names
    allowed_modules: set[str] = set(ALWAYS_ALLOWED_MODULES)
    for group_name in agent_groups:
        group_modules = groups_map.get(group_name, [])
        allowed_modules.update(group_modules)

    tool_manager = app._tool_manager
    to_remove: list[str] = []

    for tool_name, tool in tool_manager._tools.items():
        fn = getattr(tool, "fn", None)
        if fn is None:
            continue
        module_path: str = getattr(fn, "__module__", "") or ""
        # module_path is e.g. "metis_mcp.tools.literature"
        # Short name is the last component
        short = module_path.split(".")[-1] if "." in module_path else module_path
        if short not in allowed_modules:
            to_remove.append(tool_name)

    for name in to_remove:
        del tool_manager._tools[name]

    total_before = len(tool_manager._tools) + len(to_remove)
    log.info(
        "subset_loader: agent '%s' — kept %d/%d tools (removed %d). "
        "Allowed modules: %s",
        agent_slug,
        len(tool_manager._tools),
        total_before,
        len(to_remove),
        ", ".join(sorted(allowed_modules)),
    )
    return len(to_remove)
