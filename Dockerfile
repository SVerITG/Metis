# Root Dockerfile — lets Glama (and any MCP host) build + run the Metis MCP server
# for its introspection check. It starts the FastMCP stdio server and responds to
# `initialize` + `tools/list` (verified locally: 175 tools). No dashboard, DB, or
# populated library needed — just the server registering its tools/prompts.
#
# (The full multi-service install images live in system/install/docker/.)

FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

# Just what the MCP server needs to register + introspect its tools/prompts.
COPY system/mcp-server /app/system/mcp-server
COPY agents            /app/agents
COPY .claude           /app/.claude
COPY system/config     /app/system/config

# [embedding] keeps the knowledge tools registerable; the ONNX model is fetched
# lazily at first use (never during introspection), so the build stays light.
RUN pip install --no-cache-dir -e "system/mcp-server/.[embedding]"

ENV METIS_RC_ROOT=/app
ENV METIS_TOOL_SUBSETS=0
ENV METIS_DOCKER=1

# FastMCP stdio server — what Glama introspects.
CMD ["python", "-m", "metis_mcp.server"]
