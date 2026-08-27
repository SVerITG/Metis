#!/usr/bin/env bash
# Screenshot a dashboard surface, so it can actually be LOOKED at.
#
# WHY THIS EXISTS. Everything else in this repo checks the dashboard by reading
# it: status codes, element counts, rendered word counts, a 455-test suite. On
# 2026-08-27 every one of those passed while raw HTML was being printed across
# the top of every page — an accessibility codemod had spliced an aria-label
# into the middle of another attribute, and the leaked markup looked like
# content to a text comparison. It was found in one second by taking a picture.
#
# Headless Chrome on the Windows side; no Python browser driver needed.
#
#   bash tools/shoot.sh /news              → /tmp/metis-shot.png
#   bash tools/shoot.sh /work work.png     → /tmp/work.png
#   bash tools/shoot.sh /news x.png 2200   → taller viewport
#
# NOTE: this is a first-paint shot. HTMX panels that load after the page will be
# empty skeletons — that is honest, and it is what a slow connection sees.
set -euo pipefail

PATH_=${1:-/}
OUT=${2:-metis-shot.png}
HEIGHT=${3:-1400}
WIDTH=${4:-1600}
PORT=${PORT:-8080}

CHROME="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
[ -x "$CHROME" ] || CHROME="/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
if [ ! -x "$CHROME" ]; then
  echo "Chrome not found. Looked in Program Files and Program Files (x86)." >&2
  exit 1
fi

WINTMP="C:\\Users\\${USER}\\AppData\\Local\\Temp"
LINTMP="/mnt/c/Users/${USER}/AppData/Local/Temp"

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
          --virtual-time-budget=4000 \
          --window-size="${WIDTH},${HEIGHT}" \
          --screenshot="${WINTMP}\\${OUT}" \
          "http://127.0.0.1:${PORT}${PATH_}" 2>&1 \
  | grep -vE "cloud_policy|ERROR:.*policy" || true

sleep 1
if [ -f "${LINTMP}/${OUT}" ]; then
  cp "${LINTMP}/${OUT}" "/tmp/${OUT}"
  echo "/tmp/${OUT}  ($(stat -c%s "/tmp/${OUT}") bytes)  ${PATH_}"
else
  echo "no image produced for ${PATH_}" >&2
  exit 1
fi
