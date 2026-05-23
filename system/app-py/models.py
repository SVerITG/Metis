"""
Model registry loader for Metis.

Reads `system/config/models.yaml` and returns the appropriate Claude model ID
for a given role / alias. On API errors the loader advances down the fallback
chain so model deprecations don't break the app — they just degrade gracefully
to an older but still-available snapshot.

Usage:
    from models import model_for
    model_id = model_for("brief")          # → "claude-haiku-4-5-20251001"
    model_id = model_for("standard")       # → "claude-sonnet-4-6"
    model_id = model_for("opus_deep")      # → "claude-opus-4-6"
    model_id = model_for("unknown")        # → falls back to sonnet_default

The function is safe to call without any external dependency on Anthropic —
it returns IDs only. Probing happens inside `model_for_with_probe()` if the
caller wants strict deprecation handling (slower; requires the SDK).
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

_cache: dict[str, tuple[str, float]] = {}  # alias → (model_id, expires_at)
_config: dict[str, Any] | None = None


def _config_path() -> Path:
    """Locate models.yaml relative to METIS_RC_ROOT or repo root."""
    rc = os.environ.get("METIS_RC_ROOT", "")
    if rc:
        p = Path(rc) / "system" / "config" / "models.yaml"
        if p.exists():
            return p
    # Fallback: assume this file lives at system/app-py/models.py
    return Path(__file__).parent.parent / "config" / "models.yaml"


def _load_config() -> dict[str, Any]:
    """Load and cache models.yaml. Returns an empty-but-safe dict on any error."""
    global _config
    if _config is not None:
        return _config
    try:
        import yaml
        p = _config_path()
        if p.exists():
            _config = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        else:
            _config = {}
    except Exception:
        _config = {}
    return _config


def _resolve_alias(name: str) -> str:
    """Map an alias ('brief', 'standard') to a role ('haiku_synthesis')."""
    cfg = _load_config()
    aliases = cfg.get("aliases", {}) or {}
    return aliases.get(name, name)


def _chain_for(role: str) -> list[str]:
    """Return [primary] + fallback for a role. Falls back to claude-sonnet-4-6 if unknown."""
    cfg = _load_config()
    roles = cfg.get("roles", {}) or {}
    entry = roles.get(role)
    if not entry:
        return ["claude-sonnet-4-6", "claude-3-5-sonnet-latest"]
    chain: list[str] = []
    primary = entry.get("primary")
    if primary:
        chain.append(primary)
    chain.extend(entry.get("fallback", []) or [])
    return chain or ["claude-sonnet-4-6"]


def model_for(name: str) -> str:
    """Return the model ID for an alias or role.

    Simple version — returns the primary without probing. Use this for the
    common case where you just want a model ID for a Claude API call and don't
    need active deprecation handling.
    """
    role = _resolve_alias(name)
    cache_key = role
    cached = _cache.get(cache_key)
    if cached and cached[1] > time.time():
        return cached[0]
    chain = _chain_for(role)
    picked = chain[0]
    cfg = _load_config()
    ttl = (cfg.get("availability", {}) or {}).get("cache_minutes", 60) * 60
    _cache[cache_key] = (picked, time.time() + ttl)
    return picked


def model_for_with_probe(name: str) -> str:
    """Return the first model in the chain that responds to a probe call.

    Slower: makes an Anthropic API call. Use only when you suspect the primary
    might be deprecated and you need a guaranteed-working ID.

    Falls back to `model_for(name)` if the SDK is missing or no key is set.
    """
    role = _resolve_alias(name)
    cache_key = f"{role}_probed"
    cached = _cache.get(cache_key)
    if cached and cached[1] > time.time():
        return cached[0]
    chain = _chain_for(role)
    try:
        from anthropic import Anthropic
        client = Anthropic()
        for candidate in chain:
            try:
                # Tiny probe message — cheapest possible call
                client.messages.create(
                    model=candidate,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "ok"}],
                )
                cfg = _load_config()
                ttl = (cfg.get("availability", {}) or {}).get("cache_minutes", 60) * 60
                _cache[cache_key] = (candidate, time.time() + ttl)
                return candidate
            except Exception:
                continue
    except Exception:
        pass
    return model_for(name)


def reload_config() -> None:
    """Force re-read of models.yaml on next call. Useful after editing the file."""
    global _config
    _config = None
    _cache.clear()
