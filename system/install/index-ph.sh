#!/bin/bash
# Run the PH background knowledge indexer using the Linux-side venv.
# Usage: bash system/install/index-ph.sh [--batch-size 2] [--sleep 1.0]
VENV="/home/sverschaeve/.local/share/metis-mcp/.venv/bin/python3"
SCRIPT="system/install/build_knowledge_db.py"
"$VENV" "$SCRIPT" --database ph-background "$@"
