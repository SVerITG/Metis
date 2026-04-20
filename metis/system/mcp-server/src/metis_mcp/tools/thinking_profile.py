"""Thinking profile tools: record preference signals and maintain thinking-profile.yaml."""

import datetime
from collections import defaultdict

import yaml
from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_THINKING_PROFILE_DDL = """
CREATE TABLE IF NOT EXISTS thinking_profile_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    source_type TEXT DEFAULT '',
    content_id INTEGER DEFAULT 0,
    agent_slug TEXT DEFAULT '',
    context TEXT DEFAULT '',
    timestamp TEXT NOT NULL
)
"""

_VALID_EVENT_TYPES = {
    "brainstorm_acted_on",
    "brainstorm_ignored",
    "idea_rated_high",
    "idea_linked_project",
    "journal_revisited",
    "agent_output_accepted",
    "agent_output_flagged",
}

_PROFILE_PATH_RELATIVE = "system/config/thinking-profile.yaml"

_DEFAULT_PROFILE = {
    "version": 1,
    "last_updated": datetime.date.today().isoformat(),
    "connection_preferences": [],
    "preferred_idea_sources": {},
    "agent_feedback": {},
    "notes": "No profile data yet. Use Metis for a few weeks to build your thinking profile.",
}


def _profile_path():
    return paths.root / _PROFILE_PATH_RELATIVE


def _read_profile() -> dict:
    p = _profile_path()
    if not p.exists():
        return dict(_DEFAULT_PROFILE)
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return dict(_DEFAULT_PROFILE)
        return data
    except Exception:
        return dict(_DEFAULT_PROFILE)


def _write_profile(profile: dict) -> None:
    p = _profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(profile, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


@app.tool()
async def record_thinking_event(
    event_type: str,
    source_type: str = "",
    content_id: int = 0,
    agent_slug: str = "",
    context: str = "",
) -> list[TextContent]:
    """Log a single preference signal to the thinking_profile_events table.

    Args:
        event_type: One of: brainstorm_acted_on, brainstorm_ignored,
                    idea_rated_high, idea_linked_project, journal_revisited,
                    agent_output_accepted, agent_output_flagged.
        source_type: Domain or source category the signal belongs to (e.g. "biology").
        content_id: Optional ID of the related content record.
        agent_slug: Agent identifier, used for agent_output_* events.
        context: Free-text context or note for this event.
    """
    if event_type not in _VALID_EVENT_TYPES:
        valid = ", ".join(sorted(_VALID_EVENT_TYPES))
        return [TextContent(type="text", text=f"Invalid event_type '{event_type}'. Valid types: {valid}")]

    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as conn:
            conn.execute(_THINKING_PROFILE_DDL)
            conn.execute(
                """INSERT INTO thinking_profile_events
                   (event_type, source_type, content_id, agent_slug, context, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (event_type, source_type, content_id, agent_slug, context, now),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Thinking event recorded: {event_type}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error recording thinking event: {e}")]


@app.tool()
async def get_thinking_profile() -> list[TextContent]:
    """Read and return the current thinking profile from 08_system/thinking-profile.yaml.

    Falls back to default structure if the file does not exist.
    """
    profile = _read_profile()

    lines = [f"**Thinking Profile** (v{profile.get('version', 1)}, updated {profile.get('last_updated', 'unknown')})\n"]

    conn_prefs = profile.get("connection_preferences", [])
    if conn_prefs:
        lines.append("**Connection Preferences:**")
        for item in conn_prefs:
            pair = item.get("domain_pair", "?")
            rate = item.get("acted_on_rate", 0)
            count = item.get("total_events", 0)
            lines.append(f"  - {pair}: {rate:.0%} acted-on rate ({count} events)")
    else:
        lines.append("**Connection Preferences:** none yet")

    idea_sources = profile.get("preferred_idea_sources", {})
    if idea_sources:
        lines.append("\n**Preferred Idea Sources:**")
        for src, count in sorted(idea_sources.items(), key=lambda x: -x[1]):
            lines.append(f"  - {src}: {count} high-rated ideas")
    else:
        lines.append("\n**Preferred Idea Sources:** none yet")

    agent_fb = profile.get("agent_feedback", {})
    if agent_fb:
        lines.append("\n**Agent Feedback:**")
        for slug, stats in agent_fb.items():
            accepted = stats.get("accepted_rate", 0)
            flagged = stats.get("flagged_rate", 0)
            total = stats.get("total_events", 0)
            lines.append(f"  - {slug}: {accepted:.0%} accepted, {flagged:.0%} flagged ({total} events)")
    else:
        lines.append("\n**Agent Feedback:** none yet")

    notes = profile.get("notes", "")
    if notes:
        lines.append(f"\n_{notes}_")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def update_thinking_profile() -> list[TextContent]:
    """Recompute and update the thinking profile from the last 90 days of events.

    Computes:
    - connection_preferences: acted-on rates per domain_pair (source_type)
    - preferred_idea_sources: frequency of source_type in high-rated idea events
    - agent_feedback: accepted/flagged rates per agent_slug

    Writes updated 08_system/thinking-profile.yaml. Safe to call multiple times.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    cutoff = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
    ).isoformat()

    try:
        with connect(paths.db) as conn:
            conn.execute(_THINKING_PROFILE_DDL)
            cur = conn.execute(
                """SELECT event_type, source_type, agent_slug
                   FROM thinking_profile_events
                   WHERE timestamp >= ?""",
                (cutoff,),
            )
            rows = cur.fetchall()
    except Exception as e:
        return [TextContent(type="text", text=f"Error querying thinking_profile_events: {e}")]

    # --- connection_preferences ---
    acted_on_counts: dict[str, int] = defaultdict(int)
    ignored_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        et = row["event_type"]
        src = row["source_type"] or ""
        if not src:
            continue
        if et == "brainstorm_acted_on":
            acted_on_counts[src] += 1
        elif et == "brainstorm_ignored":
            ignored_counts[src] += 1

    all_pairs = set(acted_on_counts.keys()) | set(ignored_counts.keys())
    connection_preferences = []
    for pair in sorted(all_pairs):
        acted = acted_on_counts[pair]
        ignored = ignored_counts[pair]
        total = acted + ignored
        rate = acted / total if total > 0 else 0.0
        connection_preferences.append({
            "domain_pair": pair,
            "acted_on_rate": round(rate, 3),
            "total_events": total,
        })

    # Sort by rate descending
    connection_preferences.sort(key=lambda x: -x["acted_on_rate"])

    # --- preferred_idea_sources ---
    idea_source_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["event_type"] == "idea_rated_high":
            src = row["source_type"] or ""
            if src:
                idea_source_counts[src] += 1

    preferred_idea_sources = dict(
        sorted(idea_source_counts.items(), key=lambda x: -x[1])
    )

    # --- agent_feedback ---
    agent_accepted: dict[str, int] = defaultdict(int)
    agent_flagged: dict[str, int] = defaultdict(int)

    for row in rows:
        et = row["event_type"]
        slug = row["agent_slug"] or ""
        if not slug:
            continue
        if et == "agent_output_accepted":
            agent_accepted[slug] += 1
        elif et == "agent_output_flagged":
            agent_flagged[slug] += 1

    all_agents = set(agent_accepted.keys()) | set(agent_flagged.keys())
    agent_feedback = {}
    for slug in sorted(all_agents):
        accepted = agent_accepted[slug]
        flagged = agent_flagged[slug]
        total = accepted + flagged
        agent_feedback[slug] = {
            "accepted_rate": round(accepted / total, 3) if total > 0 else 0.0,
            "flagged_rate": round(flagged / total, 3) if total > 0 else 0.0,
            "total_events": total,
        }

    # --- Read current profile and merge ---
    old_profile = _read_profile()
    today = datetime.date.today().isoformat()

    new_profile = {
        "version": old_profile.get("version", 1),
        "last_updated": today,
        "connection_preferences": connection_preferences,
        "preferred_idea_sources": preferred_idea_sources,
        "agent_feedback": agent_feedback,
        "notes": (
            old_profile.get("notes", "")
            if (connection_preferences or preferred_idea_sources or agent_feedback)
            else "No profile data yet. Use Metis for a few weeks to build your thinking profile."
        ),
    }

    try:
        _write_profile(new_profile)
    except Exception as e:
        return [TextContent(type="text", text=f"Error writing thinking-profile.yaml: {e}")]

    total_events = len(rows)
    summary_lines = [
        f"Thinking profile updated ({today}, {total_events} events in last 90 days).",
        f"- Connection preferences: {len(connection_preferences)} domain pairs",
        f"- Preferred idea sources: {len(preferred_idea_sources)} source types",
        f"- Agent feedback: {len(agent_feedback)} agents",
    ]
    return [TextContent(type="text", text="\n".join(summary_lines))]


@app.tool()
async def reset_thinking_profile() -> list[TextContent]:
    """Clear all thinking_profile_events and reset thinking-profile.yaml to defaults.

    This erases all recorded preference signals and restores the default profile.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_THINKING_PROFILE_DDL)
            conn.execute("DELETE FROM thinking_profile_events")
            conn.commit()
    except Exception as e:
        return [TextContent(type="text", text=f"Error clearing thinking_profile_events: {e}")]

    default = dict(_DEFAULT_PROFILE)
    default["last_updated"] = datetime.date.today().isoformat()

    try:
        _write_profile(default)
    except Exception as e:
        return [TextContent(type="text", text=f"Error writing default thinking-profile.yaml: {e}")]

    return [TextContent(type="text", text="Thinking profile reset to defaults. All events cleared.")]
