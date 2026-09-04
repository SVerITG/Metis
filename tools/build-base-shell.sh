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
  -e 's#glama.ai/mcp/servers/SVerITG/Metis_PH#glama.ai/mcp/servers/SVerITG/Metis#g' \
  README.md
# 1b) server.json (official MCP registry): rewrite the PH identity → base identity.
if [ -f server.json ]; then
  sed -i \
    -e 's#io.github.SVerITG/metis-ph#io.github.SVerITG/metis#g' \
    -e 's#SVerITG/Metis_PH#SVerITG/Metis#g' \
    -e 's#Public-health research memory for Claude: cited answers from your library + 30+ specialist agents#Persistent research memory for Claude: cited answers from your library + 30+ specialist agents#g' \
    server.json
  git add server.json
fi
git rm -r -q --ignore-unmatch knowledge/courses/epidemiology-foundations \
                              knowledge/courses/health-economics \
                              knowledge/courses/outbreak-investigation 2>/dev/null || true   # 2) filled domain courses
# NB: the docs/Scene*.gif demo GIFs are KEPT in the base shell — they demonstrate
# the universal features (dashboard, brainstorm, self-improvement); the persona is
# just example data, and the README "See it in action" section references them.
git add README.md

# ── Safety net: scrub maintainer identity from every tracked text file, so even
#    if a personal reference slips into `main`, the public base shell never
#    carries the maintainer's home path, username, or name. Values are derived
#    dynamically (no personal literals live in this script); extra names come from
#    a gitignored list (tools/base-shell/scrub-names.txt), also never shipped.
echo "▸ Scrubbing maintainer identity from tracked text files…"
HOME_USER="$(id -un)"
NAME_PATTERNS=""
[ -f tools/base-shell/scrub-names.txt ] && NAME_PATTERNS="$(grep -vE '^\s*(#|$)' tools/base-shell/scrub-names.txt || true)"
# Build one regex of everything we scrub, then sed ONLY the files that actually
# match. git grep is a single fast pass; because main is already scrubbed this
# loop is usually empty — avoids sed-ing every file on a slow filesystem.
SCRUB_RE="/home/${HOME_USER}|/mnt/c/Users/${HOME_USER}|\\b${HOME_USER}\\b"
for pat in $NAME_PATTERNS; do SCRUB_RE="${SCRUB_RE}|\\b${pat}\\b"; done
MATCHED="$(git grep -lE "$SCRUB_RE" -- '*.py' '*.sh' '*.js' '*.mjs' '*.html' '*.css' '*.md' '*.json' '*.yaml' '*.yml' '*.txt' '*.toml' '*.cfg' 2>/dev/null | grep -vE '^(tools/build-base-shell\.sh|tools/base-shell/)' || true)"
for f in $MATCHED; do
  [ -f "$f" ] || continue
  sed -i \
    -e "s#/home/${HOME_USER}#\$HOME#g" \
    -e "s#/mnt/c/Users/${HOME_USER}#\$HOME#g" \
    -e "s#\b${HOME_USER}\b#user#g" \
    "$f"
  for pat in $NAME_PATTERNS; do
    sed -i -e "s#\b${pat}'s\b#the user's#g" -e "s#\b${pat}\b#the user#g" "$f"
  done
done
git add -A

# WHY THIS IS NOT `|| echo "(nothing changed)"` ANY MORE
#   It was, until 2026-09-04, and on that day it published the unstripped full
#   edition to the PUBLIC base repo. Another process held .git/index.lock for a
#   moment; `git commit` died with a fatal; `||` swallowed it AND disabled
#   `set -e` for that command; the script printed "(nothing changed)" — which is
#   also what it prints when the strip legitimately had nothing to do — and then
#   force-pushed a `base` branch still sitting at main's tip.
#
#   A failure indistinguishable from a trivial success is not a log line, it is a
#   silent publish. So a failing commit is fatal, and "nothing to commit" is
#   decided by asking the index rather than by ignoring an exit code.
if ! git diff --cached --quiet; then
  git commit -q -m "build: domain-agnostic base shell (generated from main by build-base-shell.sh)" \
    || { echo "ERROR: the base-shell commit failed. NOTHING was pushed." >&2; exit 1; }
else
  echo "  (nothing to commit — main was already free of everything the shell strips)"
fi

# ── Gate: assert the OUTCOME, never the steps ────────────────────────────────
# Every step above has, at least once, reported success while doing nothing. So
# the publish is gated on what the built tree actually CONTAINS — the only thing
# the public repo's readers will ever see.
echo "▸ Verifying the shell before publishing…"
FAIL=0
while read -r must_go; do
  [ -z "$must_go" ] && continue
  n="$(git ls-tree -r --name-only HEAD | grep -c "$must_go" || true)"
  if [ "$n" != "0" ]; then
    echo "  ✗ $must_go — $n file(s) still present" >&2; FAIL=1
  else
    echo "  ✓ $must_go absent"
  fi
done <<'MUSTGO'
knowledge/courses/health-economics
knowledge/courses/outbreak-investigation
knowledge/courses/epidemiology-foundations
MUSTGO
IDENT="$(git grep -lE "\b${HOME_USER}\b" -- '*.py' '*.sh' '*.md' '*.json' '*.html' 2>/dev/null \
        | grep -vE '^(tools/build-base-shell\.sh|tools/base-shell/)' | wc -l)"
if [ "$IDENT" != "0" ]; then
  echo "  ✗ maintainer identity still in $IDENT file(s)" >&2; FAIL=1
else
  echo "  ✓ no maintainer identity"
fi
if [ "$FAIL" != "0" ]; then
  echo "" >&2
  echo "ERROR: the shell is NOT clean. Nothing pushed; origin/main is untouched." >&2
  echo "       Fix the strip, then re-run. You are on branch 'base';" >&2
  echo "       'git checkout $SRC_BRANCH' to leave." >&2
  exit 1
fi

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
