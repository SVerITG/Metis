"""User configuration tools for reading and updating user-config.yaml."""

import json
import re

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app

_CONFIG_PATH = paths.root / "system" / "config" / "user-config.yaml"

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
async def get_user_config() -> list[TextContent]:
    """Return the full Metis user configuration from user-config.yaml.

    Returns the complete YAML content (research interests, data sensitivity,
    specialist contexts, etc.). For a lightweight profile summary (name,
    interests, news_topics), use get_user_profile() instead.
    Creates the config file with defaults if it does not exist yet.
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


# ---------------------------------------------------------------------------
# Phase J — Config Wizard tools
# ---------------------------------------------------------------------------

_PREFS_PATH = paths.root / "system" / "config" / "user-preferences.json"
_FIRST_RUN_MARKER = paths.root / "system" / "config" / ".first-run"


@app.tool()
async def write_user_config(yaml_content: str) -> list[TextContent]:
    """Write the full user-config.yaml produced by the first-run config wizard.

    Merges the provided YAML into the existing config so that specialist_contexts
    and active_contexts set by earlier tools are preserved.

    Args:
        yaml_content: Complete YAML string as produced by the wizard (all sections).
    """
    if not _YAML_AVAILABLE:
        return [TextContent(type="text", text="pyyaml not installed — run: pip install pyyaml")]

    try:
        new_data = yaml.safe_load(yaml_content)
        if not isinstance(new_data, dict):
            return [TextContent(type="text", text="Invalid YAML: top-level must be a mapping.")]

        # Preserve existing specialist_contexts / active_contexts if not provided
        existing = _load_config()
        existing_user = existing.get("user", {})
        new_user = new_data.setdefault("user", {})
        for key in ("specialist_contexts", "active_contexts"):
            if key not in new_user and key in existing_user:
                new_user[key] = existing_user[key]

        _save_config(new_data)
        return [TextContent(type="text", text="user-config.yaml saved successfully.")]
    except yaml.YAMLError as e:
        return [TextContent(type="text", text=f"YAML parse error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error writing user config: {e}")]


@app.tool()
async def write_user_preferences(json_content: str) -> list[TextContent]:
    """Write user-preferences.json produced by the first-run config wizard.

    Merges the provided JSON into any existing preferences so incremental wizard
    saves do not overwrite earlier sections.

    Args:
        json_content: JSON string with preference keys (news_topics, journals,
                      pubmed_query, openalex_query, theme, density, etc.).
    """
    try:
        new_prefs = json.loads(json_content)
        if not isinstance(new_prefs, dict):
            return [TextContent(type="text", text="Invalid JSON: top-level must be an object.")]

        existing: dict = {}
        if _PREFS_PATH.exists():
            try:
                existing = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass  # corrupt file — overwrite cleanly

        existing.update(new_prefs)
        _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _PREFS_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        return [TextContent(type="text", text="user-preferences.json saved successfully.")]
    except json.JSONDecodeError as e:
        return [TextContent(type="text", text=f"JSON parse error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error writing user preferences: {e}")]


@app.tool()
async def ingest_ideas_document(file_path: str) -> list[TextContent]:
    """Import an ideas document (Word/text/markdown) and capture each idea.

    Reads the file, splits it into discrete items (paragraphs, bullet points,
    or numbered items), and calls capture_idea() for each non-empty item.
    Supports .txt, .md, and .docx files.

    Args:
        file_path: Absolute or METIS_RC_ROOT-relative path to the ideas file.
    """
    from pathlib import Path

    target = Path(file_path)
    if not target.is_absolute():
        target = paths.root / file_path

    if not target.exists():
        return [TextContent(type="text", text=f"File not found: {target}")]

    # Read raw text
    raw_text = ""
    suffix = target.suffix.lower()
    try:
        if suffix == ".docx":
            try:
                import docx  # python-docx
                doc = docx.Document(str(target))
                raw_text = "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                return [TextContent(type="text", text="python-docx not installed — run: pip install python-docx")]
        else:
            raw_text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading file: {e}")]

    # Split into items: strip bullet/number prefixes, skip blank lines
    raw_items = re.split(r"\n{2,}", raw_text.strip())
    items: list[str] = []
    for block in raw_items:
        lines = [re.sub(r"^[\s\-\*\d\.]+", "", l).strip() for l in block.splitlines()]
        cleaned = " ".join(l for l in lines if l)
        if len(cleaned) > 10:
            items.append(cleaned)

    if not items:
        return [TextContent(type="text", text="No usable content found in the document.")]

    # Capture each idea via the ideas tool (import lazily to avoid circular imports)
    try:
        from metis_mcp.tools.ideas import capture_idea  # type: ignore
        captured = 0
        for item in items:
            result = await capture_idea(content=item, source=f"import:{target.name}")
            if result:
                captured += 1
        return [TextContent(type="text", text=f"Imported {captured} of {len(items)} ideas from '{target.name}'.")]
    except ImportError:
        # ideas tool not available — write to inbox as a fallback
        inbox = paths.root / "inbox" / f"ideas-import-{target.stem}.md"
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text("\n\n---\n\n".join(items), encoding="utf-8")
        return [TextContent(type="text", text=f"ideas tool unavailable — wrote {len(items)} items to inbox/{inbox.name}")]


@app.tool()
async def remove_first_run_marker() -> list[TextContent]:
    """Delete the .first-run marker file to signal that the config wizard is complete.

    Called at the end of the first-run wizard after all config files are written.
    Safe to call even if the marker does not exist.
    """
    try:
        if _FIRST_RUN_MARKER.exists():
            _FIRST_RUN_MARKER.unlink()
            return [TextContent(type="text", text="First-run marker removed. Wizard complete.")]
        return [TextContent(type="text", text="No first-run marker found (already removed).")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error removing first-run marker: {e}")]
