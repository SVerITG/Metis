"""Is a newer Metis published, and install it — for installs made by MetisSetup.exe.

The installed version is the one MetisSetup.exe wrote to
system/config/install-state.json; the published one is the latest GitHub
release of the public repository. Used by the daily self-check (to say an
update exists) and by the update_metis tool (to install it from Claude).

Only the Windows installer can update itself this way. Other installs (a git
checkout, Linux) have no install-state.json and are left alone.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from metis_mcp.edition import update_repo as _update_repo

# An edition updates from its own repository: an institute's copy must never
# be "updated" to the full build, which would bring back what it left out.
REPO = _update_repo("SVerITG/Metis")
API = f"https://api.github.com/repos/{REPO}/releases/latest"


def installed_version(root: Path) -> str | None:
    try:
        state = json.loads((root / "system" / "config" / "install-state.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    # Only a copy installed by the setup program can be updated by it. A git
    # checkout may carry an install-state.json of its own (without this mark).
    if state.get("installed_by") != "MetisSetup":
        return None
    v = str(state.get("version") or "").strip()
    return v or None


def _key(v: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", v)[:4])


def is_newer(candidate: str, current: str) -> bool:
    return _key(candidate) > _key(current)


def latest_release(timeout: float = 8.0) -> dict | None:
    """{'version', 'url', 'name', 'sha256', 'notes'} for the newest release, or None
    when it cannot be reached or carries no installer."""
    req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "metis-update-check"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "")
        if name.lower().startswith("metissetup") and name.lower().endswith(".exe"):
            digest = str(asset.get("digest") or "")
            return {"version": str(data.get("tag_name") or "").lstrip("vV"),
                    "url": asset.get("browser_download_url"),
                    "name": name,
                    "sha256": digest.split(":", 1)[1] if digest.startswith("sha256:") else "",
                    "notes": str(data.get("body") or "")[:1500]}
    return None


def download_and_launch(release: dict) -> Path:
    """Download the installer, check its checksum when GitHub publishes one, and
    start it in update mode: a progress window, no questions (answers already
    given are kept). Returns the downloaded file. Raises on any failure.

    The installer stops the running copy of Metis — including the server that
    called this — so it is started detached and outlives it.
    """
    if os.name != "nt":
        raise RuntimeError("Self-update is for the Windows installer only.")
    dest = Path(tempfile.gettempdir()) / release["name"]
    req = urllib.request.Request(release["url"], headers={"User-Agent": "metis-update"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            h.update(chunk)
            f.write(chunk)
    if release.get("sha256") and h.hexdigest().lower() != release["sha256"].lower():
        dest.unlink(missing_ok=True)
        raise RuntimeError("The downloaded installer does not match its published checksum; it was deleted.")
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([str(dest), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                     creationflags=flags, close_fds=True)
    return dest
