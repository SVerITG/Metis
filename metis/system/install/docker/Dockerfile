# Metis Research Cortex — Docker image
# Runs the MCP server + dashboard in a single container.
# Your research data is mounted from the host — never inside the image.
#
# Usage:
#   docker build -t metis-rc .
#   docker run -p 8000:8000 \
#     -v /path/to/your/metis:/metis \
#     -e ANTHROPIC_API_KEY=sk-ant-... \
#     metis-rc

FROM python:3.11-slim

LABEL maintainer="Metis Project"
LABEL description="Metis Research Cortex — AI assistant for researchers"

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsqlite3-dev \
    libffi-dev \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python environment ────────────────────────────────────────────────────────
WORKDIR /app

# Install MCP server package
COPY metis/system/mcp-server/pyproject.toml .
COPY metis/system/mcp-server/src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[voice]" && \
    pip install --no-cache-dir \
        "fastapi>=0.110.0" \
        "uvicorn[standard]>=0.29.0" \
        "feedparser>=6.0" \
        "pyzotero>=1.5"

# Copy dashboard
COPY metis/system/app-py ./dashboard

# Copy agents, skills, config (no personal data)
COPY metis/agents ./metis/agents
COPY metis/.claude ./metis/.claude
COPY metis/knowledge/courses ./metis/knowledge/courses
COPY metis/knowledge/library/concepts ./metis/knowledge/library/concepts
COPY metis/knowledge/library/methods ./metis/knowledge/library/methods
COPY metis/system/config ./metis/system/config

# ── Runtime configuration ─────────────────────────────────────────────────────
# METIS_RC_ROOT must point to the mounted volume containing personal data.
# Set this to the path of your mounted research directory.
ENV METIS_RC_ROOT=/metis
ENV PYTHONPATH=/app/src
ENV METIS_DOCKER=1

# Expose dashboard port
EXPOSE 8000

# ── Entrypoint ────────────────────────────────────────────────────────────────
# Runs both MCP server and dashboard via a supervisor script.
COPY metis/system/install/docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
