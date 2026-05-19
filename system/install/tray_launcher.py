"""
tray_launcher.py — Metis system tray launcher for Windows.

Starts the MCP server and dashboard as background processes, shows a tray icon,
and provides menu actions for opening the dashboard, viewing logs, and quitting.

Requirements: pip install pystray Pillow
Run:          pythonw tray_launcher.py    (no console window)

The script auto-detects the Metis install directory from its own location:
  tray_launcher.py lives at: {metis_root}/system/install/
  metis_root is two levels up from __file__
"""

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0,
        "Metis tray launcher requires pystray and Pillow.\n\n"
        "Run: pip install pystray Pillow",
        "Metis — Missing dependency",
        0x10,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_THIS_DIR   = Path(__file__).parent.resolve()
_METIS_ROOT = _THIS_DIR.parent.parent          # system/install → system → metis/
_VENV       = _METIS_ROOT / "system" / "mcp-server" / ".venv-win"
_PYTHON     = _VENV / "Scripts" / "pythonw.exe"
_MCP_SRC    = _METIS_ROOT / "system" / "mcp-server" / "src"
_APP_DIR    = _METIS_ROOT / "system" / "app-py"
_LOG_DIR    = _METIS_ROOT / "system" / "config" / "logs"

_DASHBOARD_URL = "http://127.0.0.1:{port}"
_STARTUP_WAIT  = 4   # seconds to wait before opening browser

# ---------------------------------------------------------------------------
# Port selection (M11.6 integrated here)
# ---------------------------------------------------------------------------

def _find_free_port(preferred: int = 8000, fallback_range: range = range(8001, 8020)) -> int:
    import socket
    for port in [preferred] + list(fallback_range):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range 8000–8019")


# ---------------------------------------------------------------------------
# Tray icon image (drawn with Pillow — no external asset needed)
# ---------------------------------------------------------------------------

def _make_icon(color: str = "#5B6EF5") -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Circle background
    d.ellipse([4, 4, 60, 60], fill=color)
    # Letter M
    d.polygon(
        [(14, 48), (14, 16), (22, 16), (32, 34), (42, 16), (50, 16), (50, 48), (42, 48),
         (42, 30), (35, 44), (29, 44), (22, 30), (22, 48)],
        fill="white",
    )
    return img


def _make_icon_grey() -> Image.Image:
    return _make_icon("#888888")


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

_procs: dict[str, subprocess.Popen] = {}
_port: int = 8000
_log_dir = _LOG_DIR


def _log_path(name: str) -> Path:
    _log_dir.mkdir(parents=True, exist_ok=True)
    return _log_dir / f"{name}.log"


def _start_mcp() -> None:
    global _procs
    if "mcp" in _procs and _procs["mcp"].poll() is None:
        return
    env = {**os.environ, "METIS_RC_ROOT": str(_METIS_ROOT), "PYTHONPATH": str(_MCP_SRC)}
    log = _log_path("mcp-server").open("w")
    _procs["mcp"] = subprocess.Popen(
        [str(_PYTHON), "-m", "metis_mcp.server"],
        env=env,
        stdout=log,
        stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _start_dashboard(port: int) -> None:
    global _procs
    if "dashboard" in _procs and _procs["dashboard"].poll() is None:
        return
    env = {**os.environ, "METIS_RC_ROOT": str(_METIS_ROOT)}
    log = _log_path("dashboard").open("w")
    _procs["dashboard"] = subprocess.Popen(
        [str(_PYTHON), "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(port), "--app-dir", str(_APP_DIR)],
        env=env,
        stdout=log,
        stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _stop_all() -> None:
    for name, proc in list(_procs.items()):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    _procs.clear()


def _is_running() -> bool:
    return any(p.poll() is None for p in _procs.values())


# ---------------------------------------------------------------------------
# Tray menu callbacks
# ---------------------------------------------------------------------------

def _open_dashboard(icon, item):
    webbrowser.open(_DASHBOARD_URL.format(port=_port))


def _open_logs(icon, item):
    os.startfile(str(_LOG_DIR))


def _restart(icon, item):
    icon.icon = _make_icon_grey()
    _stop_all()
    time.sleep(1)
    _launch_background()
    time.sleep(_STARTUP_WAIT)
    icon.icon = _make_icon()


def _quit(icon, item):
    _stop_all()
    icon.stop()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _launch_background() -> None:
    threading.Thread(target=_start_mcp, daemon=True).start()
    threading.Thread(target=lambda: _start_dashboard(_port), daemon=True).start()


def main() -> None:
    global _port
    _port = _find_free_port()

    icon = pystray.Icon(
        name="Metis",
        icon=_make_icon_grey(),
        title="Metis — starting…",
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", _open_dashboard, default=True),
            pystray.MenuItem("Open Logs Folder", _open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Restart Metis", _restart),
            pystray.MenuItem("Quit Metis", _quit),
        ),
    )

    def _startup():
        _launch_background()
        time.sleep(_STARTUP_WAIT)
        icon.icon = _make_icon()
        icon.title = f"Metis — running on :{_port}"
        webbrowser.open(_DASHBOARD_URL.format(port=_port))

    threading.Thread(target=_startup, daemon=True).start()
    icon.run()


if __name__ == "__main__":
    main()
