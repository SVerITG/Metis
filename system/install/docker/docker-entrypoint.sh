#!/bin/bash
# Metis Docker entrypoint — starts MCP server or dashboard based on CMD argument

set -e

case "$1" in
  mcp)
    echo "Starting Metis MCP server…"
    exec python -m metis_mcp.server
    ;;
  dashboard)
    echo "Starting Metis dashboard on port 8080…"
    cd /app/dashboard
    exec python -m uvicorn main:app --host 0.0.0.0 --port 8080
    ;;
  both)
    echo "Starting Metis MCP server + dashboard…"
    python -m metis_mcp.server &
    cd /app/dashboard
    exec python -m uvicorn main:app --host 0.0.0.0 --port 8080
    ;;
  *)
    echo "Usage: docker run metis-rc [mcp|dashboard|both]"
    exit 1
    ;;
esac
