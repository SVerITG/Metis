#!/bin/bash
# build-installer.sh — Compile Metis-Installer.exe from WSL
# Run once (or after any change to metis-installer.nsi or install.ps1):
#   bash build-installer.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NSI_FILE="$SCRIPT_DIR/metis-installer.nsi"
OUT_FILE="$SCRIPT_DIR/Metis-Installer.exe"

# Install makensis if not present
if ! command -v makensis >/dev/null 2>&1; then
    echo "makensis not found — installing..."
    sudo apt-get update -q
    sudo apt-get install -y nsis
fi

echo "Building $OUT_FILE ..."
makensis -V2 "$NSI_FILE"

if [ -f "$OUT_FILE" ]; then
    WIN_PATH=$(wslpath -w "$OUT_FILE" 2>/dev/null || echo "$OUT_FILE")
    echo ""
    echo "Done: $WIN_PATH"
    echo "Double-click to install Metis on any Windows machine with WSL."
else
    echo "ERROR: Output file not created."
    exit 1
fi
