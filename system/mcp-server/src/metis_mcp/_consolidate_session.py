#!/usr/bin/env python3
"""Standalone session consolidator — and the one place a session record is written.

Called by the stop hook when the dashboard is not running, and imported by the
dashboard's /api/session/consolidate. Writes directly to SQLite — no dashboard
or MCP server needed.

ONE ROW PER SESSION. Claude Code fires its Stop hook after every reply, and
each call used to INSERT a new row — dozens of near-identical summaries a day,
which crowded real decisions out of memory search. The row is keyed on Claude
Code's session id (prefixed, so it never collides with the rows the
save_session_summary tool writes) and updated in place.

Usage:
    python3 _consolidate_session.py <rc_root> --payload <json_file>
        payload: {session_id, conversation, brief_content}
    python3 _consolidate_session.py <rc_root> [brief_content_file]   (older hooks)
"""
import collections
import datetime
import json
import sqlite3
import sys
from pathlib import Path

SESSION_KEY_PREFIX = "auto:"

_DDL = """
    CREATE TABLE IF NOT EXISTS session_summaries (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        summary    TEXT NOT NULL,
        key_topics TEXT,
        decisions  TEXT,
        created_at TEXT NOT NULL
    )
"""

# Real handoff briefs use sections like "Active projects", "Open tasks",
# "Recent agent runs", not "## What happened" — so match broadly.
DECISION_HEADINGS = (
    "what happened", "decision", "key decision",
    "active project", "open task", "recent agent run",
    "next step", "follow-up", "follow up", "outcome",
)


def session_key(session_id: str) -> str:
    """The session_summaries.session_id for an automatically recorded session."""
    sid = (session_id or "").strip()
    return SESSION_KEY_PREFIX + (sid or datetime.date.today().isoformat())


def extract_from_brief(brief_content: str) -> tuple[list[str], list[str]]:
    """(topics, decisions) pulled from a handoff brief's markdown sections."""
    decisions: list[str] = []
    topics: list[str] = []
    in_decision = in_projects = False
    for line in (brief_content or "").splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if stripped.startswith("##"):
            in_decision = any(h in low for h in DECISION_HEADINGS)
            in_projects = "project" in low
            continue
        if in_decision and stripped.startswith("- ") and len(stripped) > 4:
            item = stripped[2:].strip().replace("**", "").replace("__", "").lstrip("*_ ").rstrip()
            if item and item not in decisions:
                decisions.append(item)
        if in_projects and stripped.startswith("- "):
            txt = stripped[2:].strip()
            bold = txt.split("**")
            topic = (bold[1] if len(bold) >= 3 else txt.split(" — ")[0]).strip().rstrip(":").strip()
            if topic and topic not in topics:
                topics.append(topic)
    return topics[:8], decisions[:10]


def compose_summary(conversation: str, brief_content: str, fallback: str = "") -> str:
    """The record's text: the conversation first — it is what the session was
    about — then the day's context from the handoff brief, within 4000 chars."""
    conversation = (conversation or "").strip()
    brief = (brief_content or "").strip()
    if conversation:
        text = conversation
        if brief and len(text) < 3000:
            text += "\n\n## The day's context\n" + brief[: 3800 - len(text)]
        return text[:4000]
    if len(brief) > 100:
        return brief[:2000]
    return fallback


def upsert_session_summary(conn: sqlite3.Connection, session_id: str, summary: str,
                           topics: list | None, decisions: list | None) -> str:
    """Write the session's single record, updating it if it exists. Returns
    'inserted' or 'updated'. topics/decisions of None keep what the row has —
    the quick per-reply update must not wipe what the last AI pass extracted."""
    conn.execute(_DDL)
    key = session_key(session_id)
    # Naive local time, like the rest of the dashboard's tables.
    now = datetime.datetime.now().isoformat(timespec="seconds")
    row = conn.execute(
        "SELECT id FROM session_summaries WHERE session_id = ? ORDER BY id DESC LIMIT 1", (key,)
    ).fetchone()
    if row:
        sets, args = ["summary = ?", "created_at = ?"], [summary, now]
        if topics is not None:
            sets.append("key_topics = ?"); args.append(json.dumps(topics))
        if decisions is not None:
            sets.append("decisions = ?"); args.append(json.dumps(decisions))
        conn.execute(f"UPDATE session_summaries SET {', '.join(sets)} WHERE id = ?", (*args, row[0]))
        return "updated"
    conn.execute(
        "INSERT INTO session_summaries (session_id, summary, key_topics, decisions, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (key, summary, json.dumps(topics or []), json.dumps(decisions or []), now),
    )
    return "inserted"


def _tool_call_summary(root: Path, today: str) -> tuple[str, list[str]]:
    jsonl_path = root / "journal" / "sessions" / f"session-{today}.jsonl"
    tool_calls: list[dict] = []
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    tool_calls.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if not tool_calls:
        return "", []
    agents = sorted(set(t["agent"] for t in tool_calls if t.get("agent")))
    top_tools = collections.Counter(t.get("tool", "") for t in tool_calls).most_common(5)
    parts = [f"Session {today}: {len(tool_calls)} tool calls."]
    if agents:
        parts.append(f"Agents: {', '.join(agents)}.")
    if top_tools:
        parts.append("Tools: " + ", ".join(f"{t}×{n}" for t, n in top_tools) + ".")
    return " ".join(parts), agents


def main() -> None:
    rc_root = sys.argv[1] if len(sys.argv) > 1 else ""
    if not rc_root:
        return
    root = Path(rc_root)
    today = datetime.date.today().isoformat()

    session_id, conversation, brief_content = "", "", ""
    if len(sys.argv) > 3 and sys.argv[2] == "--payload":
        try:
            payload = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
            session_id = str(payload.get("session_id") or "")
            conversation = payload.get("conversation") or ""
            brief_content = payload.get("brief_content") or ""
        except Exception as e:
            print(f"error: unreadable payload: {e}", file=sys.stderr)
            return
    elif len(sys.argv) > 2:
        brief_file = Path(sys.argv[2])
        if brief_file.exists():
            brief_content = brief_file.read_text(encoding="utf-8")

    tools_summary, agents = _tool_call_summary(root, today)
    summary = compose_summary(conversation, brief_content, tools_summary)
    if not summary:
        return  # Nothing to record
    topics, decisions = extract_from_brief(brief_content)
    topics = topics or agents

    # Resolve the live DB the same way the server does (local disk, off OneDrive).
    try:
        from metis_mcp.config import resolve_live_db
        db_path = resolve_live_db(root)
    except Exception:
        db_path = root / "system" / "app" / "data" / "metis.sqlite"
    if not db_path.exists():
        return

    try:
        with sqlite3.connect(str(db_path)) as conn:
            how = upsert_session_summary(conn, session_id, summary, topics, decisions)
            conn.commit()
        print(f"ok: session record {how}")
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
