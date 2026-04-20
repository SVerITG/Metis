"""MCP server bootstrap, tool registration, and main entry point.

WhatsApp webhook runs as a separate FastAPI process (see webhook.py).
Start with: uvicorn metis_mcp.webhook:app --port 8000
"""

from metis_mcp.app_instance import app  # noqa: F401  (re-exported for tools that import from here)

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
)


def run():
    app.run()


if __name__ == "__main__":
    run()
