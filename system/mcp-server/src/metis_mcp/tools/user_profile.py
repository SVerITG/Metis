"""User profile tool — returns identity, interests, and preferences from user-preferences.json.

Agents call this at the start of personalised runs to understand the user's
research topics and news signals to prioritise.
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


@app.tool()
async def get_user_profile() -> list[TextContent]:
    """Return the user's identity, interests, and active model preference.

    Call this at the start of any personalised run to understand the user's
    topics and news signals to prioritise.

    Returns JSON with:
    - display_name: user's display name (set via /metis_config)
    - role: professional role (e.g. "Senior researcher · public health")
    - interests: list of research interest tags (e.g. ["sleeping sickness", "multilevel models"])
    - news_topics: list of news monitoring topics (e.g. ["WHO surveillance", "AI governance"])
    - active_model: current default model slug (haiku / sonnet / opus)

    Usage pattern:
      profile = json.loads((await get_user_profile())[0].text)
      interests = profile['interests']   # → ["sleeping sickness", "multilevel models"]
      news_topics = profile['news_topics']  # → ["WHO surveillance", "AI governance"]
    """
    prefs = _read_prefs()
    profile = {
        "display_name": prefs.get("display_name") or "Researcher",
        "role": prefs.get("role") or "",
        "interests": prefs.get("interests") or [],
        "news_topics": prefs.get("news_topics") or [],
        "active_model": prefs.get("active_model") or "sonnet",
    }
    return [TextContent(type="text", text=json.dumps(profile, ensure_ascii=False, indent=2))]
