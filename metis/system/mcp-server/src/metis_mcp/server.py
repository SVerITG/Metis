"""MCP server bootstrap, tool registration, and main entry point.

WhatsApp webhook runs as a separate FastAPI process (see webhook.py).
Start with: uvicorn metis_mcp.webhook:app --port 8000
"""

# Use the shared app instance to avoid split registrations across tool modules.
# All tool modules should import `app` from either server.py or app_instance.py —
# both now point to the same object.
from metis_mcp.app_instance import app  # noqa: F401

# Import tool modules -- each registers handlers via @app.tool()
from metis_mcp.tools import (  # noqa: E402, F401
    agents,
    literature,
    notes,
    research,
    projects,
    reviews,
    tasks,
    ideas,
    safety,
    files,
    intelligence,
    library,
    config_tools,
    images,
    thinking_profile,
    self_improvement,
    transcription,
    memory,
    pipeline,
    vector_memory,
    guardrails,
    knowledge_graph,
    observability,
    anonymization,
    backup,
    brainstorm,
    data_tools,
    handoff,
    improvement,
    observation,
    content_scan,
    zotero,
    doctor,
    ref_miner,
    fulltext_index,
    user_profile,
    literature_monitor,
    meetings,
    course_builder,
    paperqa_search,
    voice_capture,
    knowledge_db,
    session_memory,
)


# ── Domain-specific tool loading ─────────────────────────────────────────────
# When METIS_TOOL_SUBSETS=1 and METIS_AGENT_SUBSET=<slug> are set, strip tools
# not in the agent's declared subset. This reduces the tools/list token cost
# by 50–80% for targeted agent sessions.
#
# Example (from run.sh or a per-agent launcher):
#   METIS_TOOL_SUBSETS=1 METIS_AGENT_SUBSET=librarian python -m metis_mcp.server
import os as _os

if _os.environ.get("METIS_TOOL_SUBSETS") == "1":
    _agent = _os.environ.get("METIS_AGENT_SUBSET", "").strip()
    if _agent:
        from metis_mcp.subset_loader import apply_tool_subset
        _removed = apply_tool_subset(app, _agent)
        if _removed:
            import logging as _logging
            _logging.getLogger("metis").info(
                "Tool subset active: agent=%s, %d tools removed", _agent, _removed
            )


def run():
    app.run()


if __name__ == "__main__":
    run()
