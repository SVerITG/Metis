#!/usr/bin/env python3
"""Screenshot a dashboard surface, from inside Linux.

WHY THIS REPLACED THE CHROME-ON-WINDOWS VERSION
    The old tools/shoot.sh drove chrome.exe across the WSL boundary. On
    2026-08-31 WSL's binfmt interop registration dropped mid-session and every
    .exe began failing with "Exec format error" — so the ONE tool that catches
    layout defects went dark for a whole day of visual work, and the only
    documented fix (`wsl --shutdown`) would have killed the session doing the
    work.

    A screenshot tool that depends on a Windows bridge is a screenshot tool
    that is unavailable exactly when a long session has accumulated the most
    unverified change. This one runs entirely inside Linux, against a browser
    Playwright keeps in ~/.cache, and needs no root and no interop.

    The Windows path is kept as a fallback, because it costs nothing and works
    when this does not.

USAGE
    python3 tools/shoot.py /news                 -> /tmp/metis-shot.png
    python3 tools/shoot.py /work work.png
    python3 tools/shoot.py /work work.png 2200 1600
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PORT = os.environ.get("METIS_PORT", "8080")

# ── The one library Chromium wants and cannot find ───────────────────────────
# Playwright's headless shell links libasound.so.2 — ALSA sound, which a
# headless browser never uses — and Ubuntu 26.04 does not ship it by default.
# Installing it needs root; extracting the .deb into a user directory does not,
# and works just as well:
#
#   apt-get download libasound2t64        # no root
#   dpkg -x libasound2t64_*.deb root      # no root
#   cp root/usr/lib/x86_64-linux-gnu/libasound.so.2* ~/.local/lib/metis-shoot/
#
# Kept out of /tmp deliberately: /tmp is cleared on reboot, and a screenshot
# tool that quietly stops working after a restart is the failure this whole
# rewrite exists to prevent.
_LIBS = Path.home() / ".local/lib/metis-shoot"
if _LIBS.is_dir():
    _existing = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = f"{_LIBS}:{_existing}" if _existing else str(_LIBS)


def main() -> int:
    path   = sys.argv[1] if len(sys.argv) > 1 else "/"
    out    = sys.argv[2] if len(sys.argv) > 2 else "metis-shot.png"
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
    width  = int(sys.argv[4]) if len(sys.argv) > 4 else 1600
    dest   = Path("/tmp") / out
    url    = f"http://127.0.0.1:{PORT}{path}"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed in this interpreter — run:\n"
              "  ~/.local/share/metis-mcp/.venv/bin/python -m pip install playwright\n"
              "  ~/.local/share/metis-mcp/.venv/bin/python -m playwright install chromium",
              file=sys.stderr)
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(url, wait_until="load", timeout=30_000)
        # HTMX panels arrive after load. Wait for the network to settle, but do
        # not fail the shot if something polls forever — a partial page is still
        # worth looking at, and that is what a slow connection sees anyway.
        try:
            page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass
        page.screenshot(path=str(dest))
        browser.close()

    print(f"{dest}  ({dest.stat().st_size} bytes)  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
