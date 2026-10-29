#!/usr/bin/env bash
#
# Build a Windows installer from a PUBLISHED copy and attach it to a DRAFT
# GitHub release. Run from WSL on a Windows computer with Inno Setup.
#
#   tools/build-release.sh public 1.4     → MetisSetup-1.4.exe     on SVerITG/Metis
#   tools/build-release.sh itm    1.2     → MetisSetup-ITM-1.2.exe on SVerITG/Metis_ITM
#
# Why not system/install/build-windows-installers.ps1: that script compiles the
# copy of the code it sits in. Run from the development folder it would pack
# the development tree — everything the public filter exists to keep out —
# and it publishes the release at once. This one compiles only the export copy
# that check_publish_clean has passed, at the tag that names it, and leaves the
# release as a draft: "update Metis" reads releases/latest, which ignores
# drafts, so nobody is offered it until it is published on purpose:
#
#   gh release edit v<version> --repo <repo> --draft=false
#
# Needs: Inno Setup 6 (winget install JRSoftware.InnoSetup) and a gh login for
# the account that owns the repository (gh auth login -h github.com).
set -euo pipefail

TARGET="${1:-}"; VERSION="${2:-}"
case "$TARGET" in
  public) COPY="${METIS_PUBLIC_DIR:-$HOME/metis-public}"; REPO="SVerITG/Metis"
          ISS="system/install/installer/metis-setup.iss"; PREFIX="MetisSetup"
          NOTES="$(cd "$(dirname "$0")/.." && pwd)/system/release/notes/v$VERSION.md" ;;
  itm)    COPY="${METIS_ITM_DIR:-$HOME/metis-itm}";      REPO="SVerITG/Metis_ITM"
          # metis-setup.iss includes the edition.iss that sits beside it in an edition copy
          ISS="system/install/installer/metis-setup.iss"; PREFIX="MetisSetup-ITM"
          NOTES="$COPY/system/install/installer/release-notes.md" ;;
  *) echo "usage: $0 public|itm <version>" >&2; exit 2 ;;
esac
[ -n "$VERSION" ] || { echo "usage: $0 $TARGET <version>" >&2; exit 2; }
TAG="v$VERSION"

fail() { echo "✗ $*" >&2; exit 1; }

# 1. The copy is clean and sits exactly at the tag being released.
[ -d "$COPY/.git" ] || fail "no export copy at $COPY — run the export first"
[ -z "$(git -C "$COPY" status --porcelain)" ] || fail "$COPY has uncommitted changes"
git -C "$COPY" rev-parse -q --verify "refs/tags/$TAG" >/dev/null || fail "$COPY has no tag $TAG"
[ "$(git -C "$COPY" rev-parse HEAD)" = "$(git -C "$COPY" rev-parse "$TAG^{commit}")" ] \
  || fail "$COPY is not at $TAG — check out the tag or re-tag deliberately"
[ -f "$NOTES" ] || fail "release notes not found: $NOTES"
echo "✓ $COPY is clean and at $TAG"

# 2. A working gh login for the repository's owner.
gh api "repos/$REPO" --jq .full_name >/dev/null 2>&1 \
  || fail "gh cannot reach $REPO — run:  gh auth login -h github.com  (as ${REPO%%/*})"
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  fail "$REPO already has a release $TAG — edit it on github.com rather than overwrite"
fi
echo "✓ gh can reach $REPO"

# 3. Inno Setup, found the way Windows finds it.
ISCC_WIN="$(powershell.exe -NoProfile -Command \
  '$c = Get-Command ISCC.exe -ErrorAction SilentlyContinue; if ($c) { $c.Source } else {
     @("$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe","$env:ProgramFiles\Inno Setup 6\ISCC.exe",
       "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1 }' \
  | tr -d '\r')"
[ -n "$ISCC_WIN" ] || fail "Inno Setup not found — install it:  winget install JRSoftware.InnoSetup"
echo "✓ Inno Setup: $ISCC_WIN"

# 4. Compile into Windows temp (never onto OneDrive: it locks the exe mid-write).
OUT_WIN="$(powershell.exe -NoProfile -Command '[IO.Path]::Combine($env:TEMP, "metis-build")' | tr -d '\r')"
ISS_WIN="$(wslpath -w "$COPY/$ISS")"
echo "… compiling $PREFIX-$VERSION.exe from $TAG"
powershell.exe -NoProfile -Command "New-Item -ItemType Directory -Force -Path '$OUT_WIN' | Out-Null; & '$ISCC_WIN' '/O$OUT_WIN' '/DMyAppVersion=$VERSION' '$ISS_WIN'; exit \$LASTEXITCODE" \
  || fail "ISCC failed"
EXE="$(wslpath -u "$OUT_WIN")/$PREFIX-$VERSION.exe"
[ -f "$EXE" ] || fail "expected $EXE after the build"
echo "✓ built $(basename "$EXE") ($(du -h "$EXE" | cut -f1))"

# 5. A draft release with the installer; the tag already exists.
gh release create "$TAG" "$EXE" --repo "$REPO" --verify-tag --draft \
   --title "$( [ "$TARGET" = itm ] && echo "Metis for ITM $VERSION" || echo "Metis $VERSION" )" \
   --notes-file "$NOTES"
echo
echo "Draft created. Check it on github.com, then publish:"
echo "  gh release edit $TAG --repo $REPO --draft=false"
