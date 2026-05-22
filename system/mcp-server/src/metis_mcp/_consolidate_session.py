#!/usr/bin/env python3
"""Standalone session consolidator.

Called by the stop hook when the dashboard is not running. Reads the JSONL
session log and writes directly to SQLite — no dashboard or MCP server needed.

Usage: python3 _consolidate_session.py <rc_root> [brief_content_file]
"""
import collections
import datetime
import json
import sqlite3
import sys
from pathlib import Path


def main() -> None:
    rc_root = sys.argv[1] if len(sys.argv) > 1 else ""
    if not rc_root:
        return

    root = Path(rc_root)
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ── Read JSONL session log ────────────────────────────────────────────────
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

    # ── Read brief content if provided ────────────────────────────────────────
    brief_content = ""
    if len(sys.argv) > 2:
        brief_file = Path(sys.argv[2])
        if brief_file.exists():
            brief_content = brief_file.read_text(encoding="utf-8")

    if not tool_calls and not brief_content:
        return  # Nothing to record

    # ── Build summary ─────────────────────────────────────────────────────────
    tools_used = [t.get("tool", "") for t in tool_calls]
    agents = sorted(set(t["agent"] for t in tool_calls if t.get("agent")))
    top_tools = collections.Counter(tools_used).most_common(5)

    if brief_content and len(brief_content) > 100:
        summary = brief_content[:2000].strip()
    else:
        parts = [f"Session {today}: {len(tool_calls)} tool calls."]
        if agents:
            parts.append(f"Agents: {', '.join(agents)}.")
        if top_tools:
            parts.append("Tools: " + ", ".join(f"{t}×{n}" for t, n in top_tools) + ".")
        summary = " ".join(parts)

    # ── Extract decisions from brief ──────────────────────────────────────────
    extracted: list[str] = []
    if brief_content:
        in_section = False
        for line in brief_content.splitlines():
            lower = line.lower()
            if any(h in lower for h in ["## what happened", "## decision", "## key decision"]):
                in_section = True
                continue
            if in_section and line.startswith("##"):
                in_section = False
            if in_section and line.strip().startswith("- ") and len(line.strip()) > 10:
                extracted.append(line.strip()[2:].strip())
        extracted = extracted[:10]

    # ── Write to SQLite ───────────────────────────────────────────────────────
    db_path = root / "system" / "app" / "data" / "metis.sqlite"
    if not db_path.exists():
        return

    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    summary    TEXT NOT NULL,
                    key_topics TEXT,
                    decisions  TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                """INSERT INTO session_summaries
                   (session_id, summary, key_topics, decisions, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (today, summary, json.dumps(agents), json.dumps(extracted), now),
            )

            # Also write each extracted decision to episodic_memory
            if extracted:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS episodic_memory (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT    DEFAULT '',
                        event_type TEXT    DEFAULT 'decision',
                        content    TEXT    NOT NULL,
                        metadata   TEXT    DEFAULT '{}',
                        created_at TEXT    NOT NULL
                    )
                """)
                meta = json.dumps({"session_id": today, "source": "stop_hook_fallback"})
                for decision in extracted:
                    conn.execute(
                        """INSERT INTO episodic_memory
                           (session_id, event_type, content, metadata, created_at)
                           VALUES (?, 'decision', ?, ?, ?)""",
                        (today, decision, meta, now),
                    )

            conn.commit()
        print(f"ok: {len(tool_calls)} tool calls, {len(extracted)} decisions")
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
