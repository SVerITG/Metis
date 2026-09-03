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
  cat "$SRC"
  echo ""
  echo "/* ===================== APPENDED ============================== */"
  cat "$APPEND"
} > "$DEST"

echo "wrote $DEST"
echo "  copied  : $(wc -l < "$SRC") lines from the statistics course"
echo "  appended: $(wc -l < "$APPEND") lines of markdown prose rules"
