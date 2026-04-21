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
)


def run():
    app.run()


if __name__ == "__main__":
    run()
