"""Prompt caching helpers for tools that call the Anthropic API directly.

Usage:
    from metis_mcp.cache_helpers import build_system_with_cache, load_user_context

    # Build a cached system block:
    system_blocks = build_system_with_cache(
        stable_text="You are the Metis Librarian...",
        dynamic_text="Today's date: 2026-04-03",
    )

    # Then pass to the Anthropic client:
    client.messages.create(
        model="claude-sonnet-4-6",
        system=system_blocks,
        messages=[...],
    )

Prompt caching marks the end of the stable block with cache_control=ephemeral.
Cached blocks cost ~90% less than standard input tokens.
See: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
"""

from __future__ import annotations

from pathlib import Path

import yaml

from metis_mcp.config import paths


def _cache_block(text: str) -> dict:
    """Return a content block with ephemeral cache_control applied."""
    return {
        "type": "text",
        "text": text,
        "cache_control": {"type": "ephemeral"},
    }


def _text_block(text: str) -> dict:
    """Return a plain text content block (no caching)."""
    return {"type": "text", "text": text}


def build_system_with_cache(
    stable_text: str,
    dynamic_text: str = "",
) -> list[dict]:
    """Build a system message block list with caching on the stable portion.

    The stable_text block gets cache_control applied (cheap on repeated calls).
    The dynamic_text block (if given) is appended without caching.

    Args:
        stable_text: The stable, rarely-changing system context
        dynamic_text: Dynamic context that changes per call (today's date, task-specific info)

    Returns:
        List of content blocks for the `system` parameter of messages.create()
    """
    blocks = [_cache_block(stable_text)]
    if dynamic_text:
        blocks.append(_text_block(dynamic_text))
    return blocks


def load_user_context() -> str:
    """Load user-config.yaml as a formatted string for injection into agent contexts.

    Returns empty string if the file doesn't exist or can't be parsed.
    This is a stable block — safe to cache.
    """
    config_path = Path(paths.pkm_root) / "08_system" / "user-config.yaml"
    if not config_path.exists():
        return ""
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not data:
            return ""
        user = data.get("user", {})
        lines = [
            "USER CONTEXT",
            "============",
            f"Name: {user.get('name', '')}",
            f"Role: {user.get('role', '')}",
            f"Language: {user.get('language', 'English')}",
            f"Context: {user.get('general_context', '')}",
        ]
        contexts = user.get("specialist_contexts", [])
        if contexts:
            lines.append(f"Specialist contexts: {', '.join(contexts)}")
        return "\n".join(lines)
    except Exception:
        return ""


def load_agent_system_prompt(agent_slug: str) -> str:
    """Load an agent's skill.md content for use as a cached system prompt.

    Tries .claude/skills/<slug>/skill.md first, then 02_agents/<slug>/skill.md.
    Returns empty string if neither exists.
    """
    candidates = [
        Path(paths.pkm_root) / ".claude" / "skills" / agent_slug / "skill.md",
        Path(paths.pkm_root) / "02_agents" / agent_slug / "skill.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def build_agent_system(agent_slug: str, dynamic_context: str = "") -> list[dict]:
    """Build a full cached system message for a Metis agent.

    Combines user context + agent skill prompt into a single cached block,
    with optional dynamic context (un-cached) appended.

    Args:
        agent_slug: Agent slug (e.g., 'librarian', 'writing-partner')
        dynamic_context: Task-specific context added per call (not cached)

    Returns:
        List of content blocks for messages.create(system=...)
    """
    user_ctx    = load_user_context()
    agent_skill = load_agent_system_prompt(agent_slug)

    stable_parts = []
    if user_ctx:
        stable_parts.append(user_ctx)
    if agent_skill:
        stable_parts.append(f"\nAGENT SKILL\n===========\n{agent_skill}")

    stable = "\n".join(stable_parts) if stable_parts else "You are a helpful Metis agent."
    return build_system_with_cache(stable, dynamic_context)
