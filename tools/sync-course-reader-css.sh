#!/usr/bin/env bash
# Copy the statistics course's stylesheet into the Metis course reader.
#
# the researcher's instruction was "copy the Statistics course exactly in terms of
# styling", so the reader does not approximate that palette — it serves the
# same stylesheet. That makes the statistics app the single source of truth,
# and this script is how the copy is refreshed when it changes.
#
# Everything below the APPENDED marker is written here, not copied: the
# statistics course renders structured JSON into cards and therefore has almost
# no element-level styles (only `a`). Our lessons are markdown, so h1..h4, p,
# lists, tables, blockquotes, callouts and the exercise ladder need rules — all
# written with the statistics course's own variables so they sit in the same
# visual language.
set -euo pipefail

SRC="${1:-$HOME/mlm-app/public/styles.css}"
DEST="$(dirname "$0")/../system/app-py/static/course-reader.css"
APPEND="$(dirname "$0")/course-reader-prose.css"

[ -f "$SRC" ]    || { echo "source stylesheet not found: $SRC" >&2; exit 1; }
[ -f "$APPEND" ] || { echo "prose additions not found: $APPEND" >&2; exit 1; }

# The source self-hosts its two variable fonts at /fonts/. That path does not
# exist on the dashboard, and an @font-face that 404s does not fall back to a
# same-named face loaded elsewhere — it falls back to the generic family, so
# every heading silently became Georgia. Copy the font files (and their OFL
# licences) next to the dashboard's other vendored fonts and point the copied
# rules there.
FONT_SRC="$(dirname "$SRC")/fonts"
FONT_DEST="$(dirname "$0")/../system/app-py/static/vendor/fonts"
if [ -d "$FONT_SRC" ]; then
  mkdir -p "$FONT_DEST"
  cp "$FONT_SRC"/*-variable.ttf "$FONT_SRC"/OFL-*.txt "$FONT_DEST"/ 2>/dev/null || true
fi

{
  echo "/* ============================================================="
  echo "   VERBATIM COPY of the statistics course stylesheet."
  # NOT $SRC: that is an absolute path under a developer home directory, and this
  # file is published. strip-identity.py would remove it, and the next sync would
  # put it back — so the generator must not write it in the first place.
  echo "   Source: the statistics course stylesheet (see tools/sync-course-reader-css.sh)"
  echo "   Copied: $(date -Iseconds)"
  echo "   Do not hand-edit this section — run tools/sync-course-reader-css.sh."
  echo "   ============================================================= */"
  sed "s#url('/fonts/#url('/static/vendor/fonts/#g" "$SRC"
  echo ""
  echo "/* ===================== APPENDED ============================== */"
  cat "$APPEND"
} > "$DEST"

echo "wrote $DEST"
echo "  copied  : $(wc -l < "$SRC") lines from the statistics course"
echo "  appended: $(wc -l < "$APPEND") lines of markdown prose rules"
