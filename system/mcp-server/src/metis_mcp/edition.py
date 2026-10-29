"""Which edition of Metis this is, and what it leaves out.

An EDITION is the same software with a smaller promise. The full build carries
every surface and every tool; an institute's edition switches off what its
researchers would only trip over (a course builder, a platform-specific expert)
and adds an institution pack: templates, procedures and actions that belong to
one institute and to no other.

One file says all of it: `system/config/edition.json`. When that file is
absent — the development build — nothing is switched off and there is no pack,
so this module is inert unless an edition was installed on purpose.

    {
      "id": "itm",
      "name": "Metis for ITM",
      "update_repo": "SVerITG/Metis_ITM",
      "surfaces_off": ["learning"],
      "modules_off": ["course_builder"],
      "pack": "itm",
      "links": {"statistics_course": "https://..."}
    }

Read on every call rather than cached: the file is tiny, and a cached copy is
how a switched-off surface would keep appearing until a restart nobody knows
to do.
"""
from __future__ import annotations

import json
from pathlib import Path

from metis_mcp.config import get_root


def _config_path() -> Path:
    return get_root() / "system" / "config" / "edition.json"


def edition() -> dict:
    """The edition settings, or {} for the full development build."""
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def name(default: str = "Metis") -> str:
    return str(edition().get("name") or default)


def surface_on(key: str) -> bool:
    """False only when this edition switched the surface off."""
    return key not in (edition().get("surfaces_off") or [])


def module_on(module: str) -> bool:
    """False only when this edition switched the tool module off."""
    return module not in (edition().get("modules_off") or [])


def link(key: str) -> str:
    return str((edition().get("links") or {}).get(key) or "")


def update_repo(default: str) -> str:
    return str(edition().get("update_repo") or default)


def pack_dir() -> Path | None:
    """The folder of this edition's institution pack, when it has one."""
    pid = str(edition().get("pack") or "").strip()
    if not pid or "/" in pid or "\\" in pid or pid.startswith("."):
        return None
    d = get_root() / "packs" / pid
    return d if (d / "pack.json").is_file() else None


def pack() -> dict:
    """The institution pack's manifest, or {} when there is none.

    `dir` is added so callers can resolve the pack's own relative paths
    (templates, procedures) without knowing where packs live.
    """
    d = pack_dir()
    if d is None:
        return {}
    try:
        data = json.loads((d / "pack.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    data["dir"] = str(d)
    return data
