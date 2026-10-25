#!/usr/bin/env bash
#
# Build the PUBLIC Metis repository (SVerITG/Metis) from the private development
# repository, and push it only when every check passes.
#
# Why this exists
# ---------------
# Since 2026-10-16 development happens in a private repository that also holds
# the owner's personal content. The public repository must never receive that
# history, so it is not pushed to: it is a separate clone that receives a
# filtered COPY of the committed development tree.
#
#   filter   system/release/public-export.gitignore  (what the public never sees)
#   copy     $METIS_PUBLIC_DIR (default ~/metis-public), outside OneDrive
#   gate     tools/check_publish_clean.py --self-test, then --repo on the copy
#   account  the copy is the work account's project in system/config/accounts.json,
#            and its commits carry the work identity
#
# Usage
#   system/release/export-public.sh            build and check; nothing is pushed
#   system/release/export-public.sh --push     build, check, commit and push
#
# GitHub Releases and installers (MetisSetup.exe) are made on SVerITG/Metis
# after a push, by the release coordinator.
set -euo pipefail

PUSH=0; [ "${1:-}" = "--push" ] && PUSH=1
DEV="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
FILTER="$DEV/system/release/public-export.gitignore"
LAST="$DEV/system/release/last-export.txt"
EXPORT="${METIS_PUBLIC_DIR:-$HOME/metis-public}"
die() { echo; echo "STOPPED: $*"; exit 1; }
# Where to publish and as whom comes from the private accounts registry, so this
# (published) script names no person.
REGISTRY="$DEV/system/config/accounts.json"
[ -f "$REGISTRY" ] || die "no accounts registry at $REGISTRY"
read -r PUBLIC_URL WORK_NAME WORK_EMAIL < <(python3 - "$REGISTRY" <<'PY'
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
proj = next(p for p in reg["projects"] if p["name"] == "Metis (public release copy)")
gh = reg["accounts"][proj["account"]]["github"]
host, repo = proj["git_remotes"][0].split(":", 1)
print(f"git@{host}:{repo}.git", gh["user"], gh["commit_emails"][-1])
PY
)
[ -n "${WORK_EMAIL:-}" ] || die "could not read the public repository and work identity from $REGISTRY"

[ -f "$FILTER" ] || die "no export filter at $FILTER"
cd "$DEV"
[ -z "$(git diff --cached --name-only)" ] || die "the development repo has staged changes; commit or unstage them first (the export takes the last COMMIT, never the working tree)"
HEAD_SHA="$(git rev-parse --short HEAD)"

# ── 1. The public copy, up to date with the public repository ────────────────
if [ ! -d "$EXPORT/.git" ]; then
  echo "Cloning the public repository into $EXPORT ..."
  git clone -q "$PUBLIC_URL" "$EXPORT"
fi
git -C "$EXPORT" config user.name "$WORK_NAME"
git -C "$EXPORT" config user.email "$WORK_EMAIL"
# The copy's own push guard: accounts.json declares it as the work account's
# project, allowed to push to SVerITG/Metis only.
python3 "$DEV/system/release/account_guard.py" install "$EXPORT" >/dev/null
git -C "$EXPORT" fetch -q origin
git -C "$EXPORT" checkout -q main
git -C "$EXPORT" reset -q --hard origin/main
PUBLIC_SHA="$(git -C "$EXPORT" rev-parse HEAD)"

# ── 2. Nothing in the public repository that development does not have ───────
# A pull request merged on GitHub, or a push from elsewhere, would otherwise be
# silently undone by the next export.
KNOWN="$(cat "$LAST" 2>/dev/null || true)"
if [ "$PUBLIC_SHA" != "$KNOWN" ]; then
  git fetch -q public main 2>/dev/null || true
  if ! git merge-base --is-ancestor "$PUBLIC_SHA" HEAD 2>/dev/null; then
    die "the public repository has changes that are not in development (public main $PUBLIC_SHA, last export ${KNOWN:-none}).
  Bring them in first:   git fetch public && git merge public/main
  then run this again."
  fi
fi

# ── 3. Filtered copy of the committed development tree ───────────────────────
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git archive HEAD | tar -x -C "$TMP"
EXCLUDED="$(git ls-files --cached -i --exclude-from="$FILTER")"
n_excluded=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  rm -f "$TMP/$f"; n_excluded=$((n_excluded + 1))
done <<< "$EXCLUDED"
find "$TMP" -type d -empty -delete
cp "$FILTER" "$TMP/.gitignore"
# The development CLAUDE.md is instructions for building Metis (routing tests,
# graph tools, release rules). A colleague opening Claude Code in their Metis
# folder needs instructions for USING it, so the public copy gets those instead.
[ -f "$DEV/system/release/CLAUDE.public.md" ] && cp "$DEV/system/release/CLAUDE.public.md" "$TMP/CLAUDE.md"
rsync -a --delete --exclude '.git/' "$TMP"/ "$EXPORT"/
echo "Development commit $HEAD_SHA: $(git ls-files | wc -l) tracked files, $n_excluded kept private."

# ── 4. Gate ──────────────────────────────────────────────────────────────────
cd "$EXPORT"
git add -A
if git diff --cached --quiet; then
  echo "The public repository already matches development $HEAD_SHA. Nothing to export."
  git rev-parse HEAD > "$LAST"
  exit 0
fi
echo; echo "Changes for the public repository:"; git diff --cached --stat | tail -15
python3 "$DEV/tools/check_publish_clean.py" --self-test >/dev/null \
  || die "the publish checker failed its self-test; it cannot certify anything"
git commit -q --no-verify -m "Release export from development $HEAD_SHA"
set +e
# --since: trailers and tags already in the public history are published and
# not re-judged; everything this export adds is judged in full.
python3 "$DEV/tools/check_publish_clean.py" --repo "$EXPORT" --since "$PUBLIC_SHA"; verdict=$?
set -e
if [ "$verdict" -ne 0 ]; then
  git reset -q --hard "$PUBLIC_SHA"
  die "the publish checker returned $verdict (2 block, 3 warn, 4 refused to judge). Nothing was pushed; the public copy is back at $PUBLIC_SHA."
fi

if [ "$PUSH" -eq 0 ]; then
  git reset -q --soft "$PUBLIC_SHA"
  echo; echo "Checked, not pushed. Run with --push to publish."
  exit 0
fi
git push origin main
git rev-parse HEAD > "$LAST"
echo; echo "Published development $HEAD_SHA to $PUBLIC_URL."
echo "Record it in development: git add system/release/last-export.txt && git commit -m 'Record public export'"
