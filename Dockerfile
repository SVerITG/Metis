# Root Dockerfile — lets Glama (and any MCP host) build + run the Metis MCP server
# for its introspection check. It starts the FastMCP stdio server and responds to
# `initialize` + `tools/list` (verified: 185 tools). No dashboard, DB, or populated
# library needed — just the server registering its tools/prompts.
#
# (The full multi-service install images live in system/install/docker/.)

FROM python:3.12-slim

# uv installs into an isolated venv — fast, and avoids PEP-668 "externally managed"
# failures on base images that lock the system Python (e.g. Debian trixie).
RUN pip install --no-cache-dir uv

WORKDIR /app

# Just what the MCP server needs to register + introspect its tools/prompts.
COPY system/mcp-server /app/system/mcp-server
COPY agents            /app/agents
COPY .claude           /app/.claude
COPY system/config     /app/system/config

# Install into an isolated venv at /opt/venv. [embedding] keeps the knowledge tools
# registerable; the ONNX model is fetched lazily at first use (never during the
# introspection build), so the image stays light.
RUN uv venv /opt/venv --python 3.12 \
 && uv pip install --python /opt/venv/bin/python -e "system/mcp-server/.[embedding]"

ENV METIS_RC_ROOT=/app
ENV METIS_TOOL_SUBSETS=0
ENV METIS_DOCKER=1
ENV PATH="/opt/venv/bin:$PATH"

# FastMCP stdio server — what Glama introspects.
CMD ["/opt/venv/bin/python", "-m", "metis_mcp.server"]
