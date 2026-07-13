"""User profile tool — returns identity, interests, style, and preferences.

Agents call this at the start of personalised runs to understand the user's
research topics, news signals, and communication style to adopt.
"""

import json

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths


def _read_prefs() -> dict:
    prefs_path = paths.root / "system" / "config" / "user-preferences.json"
    if prefs_path.exists():
        try:
            return json.loads(prefs_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _read_style() -> dict:
    """Load communication-style settings from user-config.yaml (style: block)
    and user-preferences.json (persona_* keys). YAML is the canonical source
    (set by /metis_config wizard); JSON overrides let the dashboard panel
    update individual settings without touching the YAML."""
    style: dict = {}
    # 1. YAML base (user-config.yaml → style: block)
    yaml_path = paths.root / "system" / "config" / "user-config.yaml"
    if yaml_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            raw = cfg.get("style") or {}
            if isinstance(raw, dict):
                style.update(raw)
        except Exception:
            pass
    # 2. JSON overlay (user-preferences.json → persona_* keys)
    prefs = _read_prefs()
    for key in ("response_length", "feedback_style", "challenge_level",
                "warmth", "detail_level", "routing_verbosity"):
        pkey = f"persona_{key}"
        if pkey in prefs:
            style[key] = prefs[pkey]
        elif key in prefs:
            style[key] = prefs[key]
    return style


@app.tool()
async def get_user_profile() -> list[TextContent]:
    """Return the user's identity, interests, style, and model preference.

    Call this at the start of any personalised run to understand the user's
    topics, news signals, and communication preferences.

    Returns JSON with:
    - display_name: user's display name (set via /metis_config)
    - role: professional role (e.g. "Senior researcher")
    - interests: list of research interest tags
    - news_topics: list of news monitoring topics
    - active_model: current default model slug (haiku / sonnet / opus)
    - style: dict of communication preferences:
        - response_length: "concise" | "moderate" | "detailed"
        - feedback_style: "gentle" | "direct" | "challenging"
        - challenge_level: "supportive" | "balanced" | "rigorous"
        - warmth: "warm" | "neutral" | "formal" (default: "warm")
        - detail_level: "brief" | "balanced" | "thorough" (default: "balanced")
        - routing_verbosity: "silent" | "natural" | "detailed" (default: "natural")

    Usage pattern:
      profile = json.loads((await get_user_profile())[0].text)
      interests = profile['interests']
      style = profile['style']  # → {"response_length": "concise", "warmth": "warm", ...}
    """
    prefs = _read_prefs()
    style = _read_style()
    # Apply defaults for new persona keys
    style.setdefault("warmth", "warm")
    style.setdefault("detail_level", "balanced")
    style.setdefault("routing_verbosity", "natural")
    style.setdefault("response_length", "concise")
    style.setdefault("feedback_style", "gentle")
    style.setdefault("challenge_level", "balanced")

    profile = {
        "display_name": prefs.get("display_name") or "Researcher",
        "role": prefs.get("role") or "",
        "interests": prefs.get("interests") or [],
        "news_topics": prefs.get("news_topics") or [],
        "active_model": prefs.get("active_model") or "sonnet",
        "style": style,
    }
    return [TextContent(type="text", text=json.dumps(profile, ensure_ascii=False, indent=2))]
