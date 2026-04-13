"""User configuration tools for reading and updating user-config.yaml."""

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app

_CONFIG_PATH = paths.root / "08_system" / "user-config.yaml"

_DEFAULT_CONFIG = {
    "user": {
        "name": "",
        "role": "",
        "general_context": "",
        "language": "en",
        "specialist_contexts": [],
        "active_contexts": ["general"],
    }
}


def _load_config() -> dict:
    """Load user-config.yaml, creating it with defaults if it doesn't exist."""
    if not _CONFIG_PATH.exists():
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _CONFIG_PATH.open("w", encoding="utf-8") as f:
            yaml.dump(_DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)
        return dict(_DEFAULT_CONFIG)

    with _CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data if data is not None else dict(_DEFAULT_CONFIG)


def _save_config(data: dict) -> None:
    """Write data back to user-config.yaml."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


@app.tool()
async def get_user_profile() -> list[TextContent]:
    """Return the current Metis user profile from user-config.yaml.

    Returns the full YAML content as formatted text. Creates the file
    with defaults if it doesn't exist yet.
    """
    if not _YAML_AVAILABLE:
        return [TextContent(type="text", text="pyyaml not installed — run: pip install pyyaml")]

    try:
        data = _load_config()
        text = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        return [TextContent(type="text", text=f"# user-config.yaml\n\n{text}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading user profile: {e}")]


@app.tool()
async def add_specialist_context(
    name: str,
    description: str,
    active_by_default: bool = True,
) -> list[TextContent]:
    """Add a new specialist context to the user profile.

    Appends to specialist_contexts in user-config.yaml. Creates the file
    with defaults if it doesn't exist yet.

    Args:
        name: Short label, e.g. "Epidemiological dashboards"
        description: 1-2 sentences about what this context covers.
        active_by_default: Whether to add to active_contexts immediately.
    """
    if not _YAML_AVAILABLE:
        return [TextContent(type="text", text="pyyaml not installed — run: pip install pyyaml")]

    try:
        data = _load_config()
        user = data.setdefault("user", {})
        contexts: list = user.setdefault("specialist_contexts", [])
        active: list = user.setdefault("active_contexts", ["general"])

        # Check if name already exists — update instead of adding a duplicate
        for ctx in contexts:
            if isinstance(ctx, dict) and ctx.get("name") == name:
                ctx["description"] = description
                if active_by_default and name not in active:
                    active.append(name)
                elif not active_by_default and name in active:
                    active.remove(name)
                _save_config(data)
                return [
                    TextContent(
                        type="text",
                        text=f"Updated existing specialist context '{name}'.",
                    )
                ]

        # New entry
        contexts.append({"name": name, "description": description})
        if active_by_default and name not in active:
            active.append(name)

        _save_config(data)
        return [
            TextContent(
                type="text",
                text=f"Added specialist context '{name}'"
                + (" and activated it." if active_by_default else " (inactive)."),
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error adding specialist context: {e}")]


@app.tool()
async def toggle_context(name: str, active: bool) -> list[TextContent]:
    """Activate or deactivate a specialist context.

    Args:
        name: Context name to toggle (must exist in specialist_contexts).
        active: True to activate, False to deactivate.
    """
    if not _YAML_AVAILABLE:
        return [TextContent(type="text", text="pyyaml not installed — run: pip install pyyaml")]

    try:
        data = _load_config()
        user = data.setdefault("user", {})
        contexts: list = user.get("specialist_contexts", [])
        active_contexts: list = user.setdefault("active_contexts", ["general"])

        # Verify the context exists
        known_names = [
            ctx.get("name") for ctx in contexts if isinstance(ctx, dict)
        ]
        if name not in known_names:
            return [
                TextContent(
                    type="text",
                    text=f"Context '{name}' not found in specialist_contexts.\n"
                    + "Known contexts: "
                    + (", ".join(known_names) if known_names else "(none)"),
                )
            ]

        if active:
            if name not in active_contexts:
                active_contexts.append(name)
                _save_config(data)
                return [TextContent(type="text", text=f"Context '{name}' activated.")]
            return [TextContent(type="text", text=f"Context '{name}' was already active.")]
        else:
            if name in active_contexts:
                active_contexts.remove(name)
                _save_config(data)
                return [TextContent(type="text", text=f"Context '{name}' deactivated.")]
            return [TextContent(type="text", text=f"Context '{name}' was already inactive.")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error toggling context: {e}")]


@app.tool()
async def list_contexts() -> list[TextContent]:
    """List all user contexts (general + specialist) with active status."""
    if not _YAML_AVAILABLE:
        return [TextContent(type="text", text="pyyaml not installed — run: pip install pyyaml")]

    try:
        data = _load_config()
        user = data.get("user", {})
        specialist_contexts: list = user.get("specialist_contexts", [])
        active_contexts: list = user.get("active_contexts", [])

        lines = ["# Contexts\n"]

        # General context
        general_active = "general" in active_contexts
        lines.append(f"- general [{'active' if general_active else 'inactive'}]")
        general_text = user.get("general_context", "")
        if general_text:
            lines.append(f"  {general_text}")

        # Specialist contexts
        if specialist_contexts:
            lines.append("")
            for ctx in specialist_contexts:
                if not isinstance(ctx, dict):
                    continue
                ctx_name = ctx.get("name", "(unnamed)")
                ctx_desc = ctx.get("description", "")
                is_active = ctx_name in active_contexts
                lines.append(f"- {ctx_name} [{'active' if is_active else 'inactive'}]")
                if ctx_desc:
                    lines.append(f"  {ctx_desc}")
        else:
            lines.append("\n(no specialist contexts defined)")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing contexts: {e}")]
