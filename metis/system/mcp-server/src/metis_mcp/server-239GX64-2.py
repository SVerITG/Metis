"""MCP server bootstrap, tool registration, and main entry point.

WhatsApp webhook runs as a separate FastAPI process (see webhook.py).
Start with: uvicorn metis_mcp.webhook:app --port 8000
"""

# Import the singleton RC app so all tool modules share the same instance.
# Do NOT create a new FastMCP here — tools register via app_instance.
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
)


def run():
    app.run()


if __name__ == "__main__":
    run()
