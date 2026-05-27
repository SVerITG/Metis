#!/usr/bin/env bash
# tools/install-hooks.sh — install Metis git hooks into .git/hooks/
#
# Run after `git clone` to enable the persona linter pre-commit hook.
# Idempotent — safe to re-run.
#
# Usage:
#   bash tools/install-hooks.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_SRC="$SCRIPT_DIR/git-hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "✗ Not a git repository. Run this from inside a Metis clone."
  exit 1
fi

if [[ ! -d "$HOOKS_SRC" ]]; then
  echo "✗ Hook source dir missing: $HOOKS_SRC"
  exit 1
fi

mkdir -p "$HOOKS_DST"

installed=0
for hook in "$HOOKS_SRC"/*; do
  name=$(basename "$hook")
  dst="$HOOKS_DST/$name"
  cp "$hook" "$dst"
  chmod +x "$dst"
  echo "  ✓ installed $name"
  installed=$((installed + 1))
done

echo ""
echo "✅ $installed Metis git hooks active. They will run on every commit."
echo "   Skip a hook one time with: git commit --no-verify"
