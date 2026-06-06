#!/bin/bash
# build-base-shell.sh — generate the domain-agnostic "Metis (base)" shell from
# the current main branch and push it to the `origin` remote (SVerITG/Metis).
#
# It strips the PH-specific content (README → generic base README, the filled
# domain courses, the PH demo GIFs) onto a `base` branch, then force-pushes that
# branch to origin/main. The full PH edition stays on `main` → `metis-ph`.
#
# Workflow once this exists:
#   - generic change → commit on main → `git push metis-ph main`
#                                      → `bash tools/build-base-shell.sh --push`
#   The script regenerates `base` from main and refreshes origin/main.
#   (Do NOT `git push origin main` directly anymore — origin holds the stripped shell.)
#
# Usage:  bash tools/build-base-shell.sh [--push]
#   without --push: builds the `base` branch locally and stops, for review.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PUSH=0; [ "${1:-}" = "--push" ] && PUSH=1

# Safety
[ -n "$(git status --porcelain)" ] && { echo "ERROR: working tree not clean — commit/stash first."; exit 1; }
SRC_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
[ "$SRC_BRANCH" = "main" ] || { echo "ERROR: run from 'main' (currently on '$SRC_BRANCH')."; exit 1; }

echo "▸ Rebuilding 'base' branch from main…"
git branch -f base main
git checkout -q base

echo "▸ Stripping PH-specific content for the clean shell…"
# 1) README: the canonical README is the full base README; strip the PH-only
#    blocks (the PH-edition note + pre-loaded-knowledge table) for the shell.
sed -i '/<!-- PH-ONLY:START -->/,/<!-- PH-ONLY:END -->/d' README.md
# Insert the base-only note (points readers to the PH edition to test the layer):
sed -i -e '/<!-- BASE-NOTE -->/r tools/base-shell/base-note.md' -e '/<!-- BASE-NOTE -->/d' README.md
# Point the status BADGES at this repo (Metis), not Metis_PH — without touching the
# intentional Metis_PH links (the base-note + editions table use the bare repo URL).
sed -i \
  -e 's#github/stars/SVerITG/Metis_PH#github/stars/SVerITG/Metis#g' \
  -e 's#github/last-commit/SVerITG/Metis_PH#github/last-commit/SVerITG/Metis#g' \
  -e 's#SVerITG/Metis_PH/stargazers#SVerITG/Metis/stargazers#g' \
  -e 's#SVerITG/Metis_PH/blob/main/LICENSE#SVerITG/Metis/blob/main/LICENSE#g' \
  README.md
git rm -r -q --ignore-unmatch knowledge/courses/epidemiology-foundations \
                              knowledge/courses/health-economics \
                              knowledge/courses/outbreak-investigation 2>/dev/null || true   # 2) filled domain courses
# NB: the docs/Scene*.gif demo GIFs are KEPT in the base shell — they demonstrate
# the universal features (dashboard, brainstorm, self-improvement); the persona is
# just example data, and the README "See it in action" section references them.
git add README.md

git commit -q -m "build: domain-agnostic base shell (generated from main by build-base-shell.sh)" \
  || echo "  (nothing changed)"

echo "▸ Base shell built on branch 'base'."
if [ "$PUSH" = "1" ]; then
  echo "▸ Force-pushing base → origin/main (SVerITG/Metis)…"
  git push -f origin base:main
  echo "  ✓ origin/main now holds the clean base shell."
else
  echo "  (dry run — re-run with --push to update origin/main)"
fi

git checkout -q "$SRC_BRANCH"
echo "▸ Back on '$SRC_BRANCH'. PH edition unchanged — push it with:  git push metis-ph main"
