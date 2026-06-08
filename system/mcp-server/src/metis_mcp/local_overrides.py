"""Optional, gitignored local overrides for domain/personal patterns.

The public source ships GENERIC defaults so Metis is domain-agnostic. A user who
works in a specific field or institution can keep their own sensitive patterns
PRIVATE by creating:

    system/config/domain-overrides.local.json

That file is gitignored, so it is never published to any repository or edition —
yet the PII scanner and the text anonymiser load it at runtime, so the user keeps
full, field-specific protection on their own machine.

Expected shape (all keys optional):

    {
      "extra_pii_patterns": [
        {"regex": "...", "label": "Case/registry identifier",
         "flags": "i", "level": "SENSITIVE"}
      ],
      "extra_sensitive_columns": ["my_case_id"],
      "extra_institutions": ["My Institute", "My Programme"]
    }
"""

import json

from metis_mcp.config import paths

_CACHE: dict | None = None


def load_overrides() -> dict:
    """Return the local overrides dict (cached). Empty dict if none/invalid."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    data: dict = {}
    try:
        p = paths.root / "system" / "config" / "domain-overrides.local.json"
        if p.exists():
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
    except Exception:
        data = {}
    _CACHE = data
    return _CACHE
