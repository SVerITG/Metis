#!/usr/bin/env bash
#
# Build an EDITION of Metis (e.g. "Metis for ITM") from the development
# repository, and push it to the edition's own repository only when every
# check passes.
#
# An edition is the same software with a smaller promise, plus an institution
# pack. It is built, never edited by hand, so it cannot drift from the code it
# came from:
#
#   1. the last COMMIT of development (never the working tree)
#   2. minus system/release/public-export.gitignore   (what is personal)
#   3. minus editions/<id>/exclude.gitignore          (what this edition leaves out)
#   4. plus  editions/<id>/overlay/                    (README, CLAUDE.md, the pack)
#   5. plus  editions/<id>/edition.json  → system/config/edition.json
#   6. gate: editions/scan_edition.py (the owner's subject, places, identity)
#            and tools/check_publish_clean.py (the public checker)
#
# Usage
#   editions/export-edition.sh itm            build and check; nothing is pushed
#   editions/export-edition.sh itm --push     build, check, commit and push
#
# Where it publishes, and as whom, comes from system/config/accounts.json: the
# project named "<edition name> (edition copy)".
set -euo pipefail

ID="${1:-}"; [ -n "$ID" ] || { echo "usage: $0 <edition-id> [--push]"; exit 1; }
PUSH=0; [ "${2:-}" = "--push" ] && PUSH=1
DEV="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
ED="$DEV/editions/$ID"
die() { echo; echo "STOPPED: $*"; exit 1; }
[ -f "$ED/edition.json" ] || die "no edition at $ED"
NAME="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$ED/edition.json")"
EXPORT="${METIS_EDITION_DIR:-$HOME/metis-$ID}"

REGISTRY="$DEV/system/config/accounts.json"
[ -f "$REGISTRY" ] || die "no accounts registry at $REGISTRY"
read -r REPO_URL WORK_NAME WORK_EMAIL < <(python3 - "$REGISTRY" "$NAME (edition copy)" <<'PY'
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
proj = next(p for p in reg["projects"] if p["name"] == sys.argv[2])
gh = reg["accounts"][proj["account"]]["github"]
host, repo = proj["git_remotes"][0].split(":", 1)
print(f"git@{host}:{repo}.git", gh["user"], gh["commit_emails"][-1])
PY
)
[ -n "${WORK_EMAIL:-}" ] || die "no project '$NAME (edition copy)' in $REGISTRY"

cd "$DEV"
HEAD_SHA="$(git rev-parse --short HEAD)"

# ── 1. The edition copy, up to date with its repository ─────────────────────
if [ ! -d "$EXPORT/.git" ]; then
  echo "Cloning $REPO_URL into $EXPORT ..."
  git clone -q "$REPO_URL" "$EXPORT"
fi
git -C "$EXPORT" config user.name "$WORK_NAME"
git -C "$EXPORT" config user.email "$WORK_EMAIL"
python3 "$DEV/system/release/account_guard.py" install "$EXPORT" >/dev/null
git -C "$EXPORT" fetch -q origin 2>/dev/null || true
if git -C "$EXPORT" rev-parse -q --verify origin/main >/dev/null; then
  git -C "$EXPORT" checkout -q main 2>/dev/null || git -C "$EXPORT" checkout -q -b main origin/main
  git -C "$EXPORT" reset -q --hard origin/main
  BASE_SHA="$(git -C "$EXPORT" rev-parse HEAD)"
else
  # A brand-new, empty repository: the first export creates main.
  git -C "$EXPORT" checkout -q --orphan main 2>/dev/null || true
  BASE_SHA=""
fi

# ── 2–5. Filtered copy of the committed tree, then the overlay ──────────────
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git archive HEAD | tar -x -C "$TMP"
n_out=0
# -z: names travel raw. Without it git quotes any name with a non-ASCII
# character ("\342\200\224" for an em dash), rm is handed a path that does not
# exist, and the file it should have removed ships.
while IFS= read -r -d '' f; do
  [ -n "$f" ] || continue
  rm -f "$TMP/$f"; n_out=$((n_out + 1))
done < <(git ls-files -z --cached -i \
           --exclude-from="$DEV/system/release/public-export.gitignore" \
           --exclude-from="$ED/exclude.gitignore")
find "$TMP" -type d -empty -delete
cp -a "$ED/overlay/." "$TMP/"
mkdir -p "$TMP/system/config"
cp "$ED/edition.json" "$TMP/system/config/edition.json"
# Lists that name a left-out specialist or module are made to agree with the copy.
python3 "$DEV/editions/prune_edition.py" "$TMP"
# The copy's .gitignore: the public rules, and then the pack's files back in —
# the public rules ignore *.docx, which is exactly what an institution's
# letterhead template is.
{ cat "$DEV/system/release/public-export.gitignore"; printf '\n# The institution pack ships its templates.\n!packs/\n!packs/**\n'; } > "$TMP/.gitignore"
# The same for Docker: the full build keeps every .docx/.pptx out of its images,
# and the test image needs the pack's templates to fill them.
[ -f "$TMP/.dockerignore" ] && printf '\n# The institution pack ships its templates.\n!packs/**\n' >> "$TMP/.dockerignore"
rsync -a --delete --exclude '.git/' "$TMP"/ "$EXPORT"/
echo "Development commit $HEAD_SHA → $NAME: $(git ls-files | wc -l) tracked, $n_out left out."

# ── 6. Gate ──────────────────────────────────────────────────────────────────
set +e
python3 "$DEV/editions/scan_edition.py" "$EXPORT" "$ED"; scan=$?
set -e
[ "$scan" -eq 0 ] || die "the edition scan returned $scan (2 hits, 4 refused to judge). Nothing was committed."

cd "$EXPORT"
git add -A
if git diff --cached --quiet; then
  echo "$NAME already matches development $HEAD_SHA. Nothing to export."
  exit 0
fi
echo; echo "Changes for $NAME:"; git diff --cached --stat | tail -15
python3 "$DEV/tools/check_publish_clean.py" --self-test >/dev/null \
  || die "the publish checker failed its self-test; it cannot certify anything"
git commit -q --no-verify -m "$NAME, built from development $HEAD_SHA"
# The pack's templates are published by decision (an institute's letterhead is
# a .docx, which the checker otherwise refuses). Exactly the files each pack's
# manifest declares are exempt, and the checker lists them in its report.
ALLOW=()
while IFS= read -r -d '' f; do ALLOW+=(--allow-file "$f"); done < <(python3 - "$EXPORT" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
for m in sorted(root.glob("packs/*/pack.json")):
    for t in json.loads(m.read_text(encoding="utf-8")).get("templates") or []:
        if t.get("file"):
            sys.stdout.write((m.parent / t["file"]).relative_to(root).as_posix() + "\0")
PY
)
set +e
if [ -n "$BASE_SHA" ]; then
  python3 "$DEV/tools/check_publish_clean.py" --repo "$EXPORT" --since "$BASE_SHA" "${ALLOW[@]}"; verdict=$?
else
  python3 "$DEV/tools/check_publish_clean.py" --repo "$EXPORT" "${ALLOW[@]}"; verdict=$?
fi
set -e
undo() { if [ -n "$BASE_SHA" ]; then git reset -q "$1" "$BASE_SHA"; else git update-ref -d refs/heads/main; fi; }
if [ "$verdict" -ne 0 ]; then
  undo --hard
  die "the publish checker returned $verdict (2 block, 3 warn, 4 refused to judge). Nothing was pushed."
fi
if [ "$PUSH" -eq 0 ]; then
  undo --soft
  echo; echo "Checked, not pushed. Run with --push to publish."
  exit 0
fi
git push -u origin main
echo; echo "Published development $HEAD_SHA as $NAME to $REPO_URL."
