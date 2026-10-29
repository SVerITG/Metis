"""The researcher's own subject matter, kept out of the source.

Metis is shipped to researchers in any field. Anything that belongs to ONE
researcher's subject — an extra Library tab for their disease, the feeds of
their specialist journals, the places their outbreak filter watches, an example
written in their vocabulary — must not be hard-coded, or every colleague
inherits it.

It lives in the owner's local configuration instead, which no published copy
carries (system/config/local/ is filtered out of every export, and a fresh
install has none):

    system/config/local/domain.d/<area>.json      one file per area of the app

Each file is a JSON object; the files are merged (later names win on a clash),
so different parts of the app can own their own file without editing a shared
one. With no files — every fresh install — `domain(key, default)` returns the
default, which must always be the generic behaviour.

    from metis_mcp.domain import domain
    tabs = domain("library_extra_tabs", [])

What a user TOLD Metis about their interests (user-preferences.json,
user_topics) is a different thing and stays where it is: that is the generic
way to be specific. This module is for the owner's hand-made extras that no
wizard collects.
"""
from __future__ import annotations

import json
from typing import Any

from metis_mcp.config import get_root


def _load() -> dict:
    d = get_root() / "system" / "config" / "local" / "domain.d"
    merged: dict = {}
    try:
        files = sorted(d.glob("*.json"))
    except OSError:
        return merged
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            merged.update(data)
    return merged


def domain(key: str, default: Any = None) -> Any:
    """A machine-local domain setting, or `default` (the generic behaviour)."""
    return _load().get(key, default)
