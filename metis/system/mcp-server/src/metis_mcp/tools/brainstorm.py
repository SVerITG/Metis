"""
tools/brainstorm.py — Phase 8: Brainstorm Plan Mode.

M8.1  brainstorm_turn(topic, steering, session_id, previous_turns)
        Look up relevant context (ideas, notes, questions, library notes)
        for a brainstorm topic. Returns structured context payload so the
        AI agent can generate connections and insights.  Saves each turn
        to brainstorm_sessions table.

M8.2  get_brainstorm_session(session_id)
        Retrieve all turns in a brainstorm session.

M8.3  list_brainstorm_sessions(limit)
        List recent brainstorm sessions with title + turn count.

M8.4  save_brainstorm_output(session_id, title, synthesis, action_items)
        Freeze a brainstorm session as a saved output in outputs/brainstorms/.
        Also writes a Markdown file and records it in the brainstorm table.

Steering modes:
  expand    — broaden the topic; surface tangential connections
  focus     — narrow to most relevant threads; eliminate noise
  challenge — find counter-arguments, weaknesses, alternative explanations
  synthesize — identify common themes; propose a unifying framework
  connect   — explicit cross-domain connections to library / literature
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS brainstorm_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid  TEXT    NOT NULL DEFAULT (lower(hex(randomblob(8)))),
    started_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    title         TEXT    NOT NULL DEFAULT '',
    status        TEXT    NOT NULL DEFAULT 'active',
    synthesis     TEXT    DEFAULT NULL,
    action_items  TEXT    DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_bs_uuid ON brainstorm_sessions(session_uuid);

CREATE TABLE IF NOT EXISTS brainstorm_turns (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_uuid  TEXT    NOT NULL,
    turn_number   INTEGER NOT NULL DEFAULT 1,
    topic         TEXT    NOT NULL,
    steering      TEXT    NOT NULL DEFAULT 'expand',
    context_json  TEXT    NOT NULL DEFAULT '{}',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bt_sess ON brainstorm_turns(session_uuid, turn_number);
"""


def _ensure_tables(conn):
    for stmt in _DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()


# ---------------------------------------------------------------------------
# Context retrieval helpers
# ---------------------------------------------------------------------------

def _fetch_ideas(conn, topic: str, limit: int = 5) -> list[dict]:
    words = [w for w in re.split(r"\W+", topic.lower()) if len(w) > 3]
    if not words:
        rows = conn.execute(
            "SELECT id, title, content, tags FROM ideas ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        like = f"%{words[0]}%"
        rows = conn.execute(
            "SELECT id, title, content, tags FROM ideas "
            "WHERE lower(title) LIKE ? OR lower(content) LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
    return [{"type": "idea", "id": r["id"], "title": r["title"], "excerpt": (r["content"] or "")[:120], "tags": r["tags"] or ""} for r in rows]


def _fetch_notes(conn, topic: str, limit: int = 5) -> list[dict]:
    words = [w for w in re.split(r"\W+", topic.lower()) if len(w) > 3]
    like = f"%{words[0]}%" if words else "%"
    rows = conn.execute(
        "SELECT id, content, category FROM personal_notes "
        "WHERE lower(content) LIKE ? ORDER BY created_at DESC LIMIT ?",
        (like, limit),
    ).fetchall()
    return [{"type": "note", "id": r["id"], "excerpt": (r["content"] or "")[:120], "category": r["category"] or ""} for r in rows]


def _fetch_questions(conn, topic: str, limit: int = 4) -> list[dict]:
    words = [w for w in re.split(r"\W+", topic.lower()) if len(w) > 3]
    like = f"%{words[0]}%" if words else "%"
    rows = conn.execute(
        "SELECT id, title, content FROM ideas "
        "WHERE idea_type='question' AND (lower(title) LIKE ? OR lower(content) LIKE ?) "
        "ORDER BY created_at DESC LIMIT ?",
        (like, like, limit),
    ).fetchall()
    return [{"type": "question", "id": r["id"], "title": r["title"], "excerpt": (r["content"] or "")[:120]} for r in rows]


def _fetch_library_notes(topic: str, limit: int = 5) -> list[dict]:
    """Scan library .md frontmatter for topic-related notes."""
    results = []
    if not paths.library.exists():
        return results
    words = {w.lower() for w in re.split(r"\W+", topic) if len(w) > 3}
    for md in paths.library.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
            title = md.stem.replace("-", " ").title()
            # Check if any topic word appears in file
            text_lower = text[:600].lower()
            if any(w in text_lower for w in words):
                # Extract title from frontmatter if available
                m = re.search(r"^title:\s*(.+)$", text[:400], re.MULTILINE)
                if m:
                    title = m.group(1).strip().strip('"')
                results.append({
                    "type": "library",
                    "path": str(md.relative_to(paths.root)),
                    "title": title,
                    "excerpt": text.replace("---", "").strip()[:120],
                })
                if len(results) >= limit:
                    break
        except Exception:
            pass
    return results


# Steering context prompts (returned to AI to guide its response)
_STEERING_PROMPTS = {
    "expand": [
        "What adjacent domains or disciplines touch this topic?",
        "What edge cases or unusual manifestations exist?",
        "Who else is working on related problems?",
    ],
    "focus": [
        "What is the single most important insight here?",
        "Which threads are noise vs. signal for the PhD?",
        "What is the minimum viable question I need to answer?",
    ],
    "challenge": [
        "What is the strongest counter-argument to this idea?",
        "What evidence would falsify this?",
        "What am I likely wrong about here?",
    ],
    "synthesize": [
        "What common thread unifies these ideas?",
        "Can I propose a 2×2 framework or taxonomy?",
        "What story would connect these disparate pieces?",
    ],
    "connect": [
        "How does this connect to the HAT surveillance work?",
        "Which library note is most directly relevant?",
        "What methodological parallel exists in other disease areas?",
    ],
}


# ---------------------------------------------------------------------------
# M8.1 — brainstorm_turn
# ---------------------------------------------------------------------------


@app.tool()
async def brainstorm_turn(
    topic: str,
    steering: str = "expand",
    session_uuid: str = "",
    turn_notes: str = "",
) -> list[TextContent]:
    """Run one turn of a brainstorm session, returning relevant context.

    Call this at the start of a brainstorm and after each steering action.
    The tool fetches relevant ideas, notes, questions, and library notes so
    you (the AI) can surface connections the user may not have considered.

    Steering modes:
      expand    — broaden; surface tangential connections
      focus     — narrow; find the most relevant threads
      challenge — find counter-arguments and weaknesses
      synthesize — identify themes; propose a unifying framework
      connect   — explicit cross-domain connections to library/literature

    Args:
        topic:        The brainstorm topic or question.
        steering:     One of expand|focus|challenge|synthesize|connect.
        session_uuid: Pass the UUID from the previous turn to continue a session.
                      Omit to start a new session.
        turn_notes:   Optional free-text notes from the previous turn to log.

    Returns JSON with: session_uuid, turn_number, context (ideas/notes/
    questions/library), steering_prompts, and instructions for the AI.
    """
    valid_steering = {"expand", "focus", "challenge", "synthesize", "connect"}
    if steering not in valid_steering:
        steering = "expand"

    with connect(paths.db) as conn:
        _ensure_tables(conn)

        # Resolve or create session
        if session_uuid:
            row = conn.execute(
                "SELECT id, session_uuid FROM brainstorm_sessions WHERE session_uuid = ?",
                (session_uuid,),
            ).fetchone()
            if not row:
                session_uuid = ""

        if not session_uuid:
            session_uuid = uuid.uuid4().hex[:16]
            conn.execute(
                "INSERT INTO brainstorm_sessions (session_uuid, title) VALUES (?, ?)",
                (session_uuid, topic[:80]),
            )
            conn.commit()

        # Count turns
        turn_count = conn.execute(
            "SELECT COUNT(*) FROM brainstorm_turns WHERE session_uuid = ?",
            (session_uuid,),
        ).fetchone()[0]
        turn_number = turn_count + 1

        # Fetch context
        try:
            ideas     = _fetch_ideas(conn, topic)
            notes     = _fetch_notes(conn, topic)
            questions = _fetch_questions(conn, topic)
        except Exception:
            ideas = notes = questions = []

    library_notes = _fetch_library_notes(topic)

    context = {
        "ideas":         ideas,
        "notes":         notes,
        "questions":     questions,
        "library_notes": library_notes,
    }

    # Save turn
    with connect(paths.db) as conn:
        conn.execute(
            "INSERT INTO brainstorm_turns "
            "(session_uuid, turn_number, topic, steering, context_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_uuid, turn_number, topic, steering,
             json.dumps(context, ensure_ascii=False)),
        )
        conn.execute(
            "UPDATE brainstorm_sessions SET updated_at=datetime('now') WHERE session_uuid=?",
            (session_uuid,),
        )
        conn.commit()

    result = {
        "session_uuid":    session_uuid,
        "turn_number":     turn_number,
        "topic":           topic,
        "steering":        steering,
        "context":         context,
        "steering_prompts": _STEERING_PROMPTS.get(steering, []),
        "instructions": (
            "You are in Brainstorm Plan Mode. Using the context above, generate "
            f"3-5 insights that connect the topic '{topic}' to the user's existing work. "
            "Highlight unexpected connections. End with 3 steering questions the user "
            "can pick from to deepen the brainstorm. Keep each insight to 2-3 sentences."
        ),
    }
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# M8.2 — get_brainstorm_session / list_brainstorm_sessions
# ---------------------------------------------------------------------------


@app.tool()
async def get_brainstorm_session(session_uuid: str) -> list[TextContent]:
    """Retrieve all turns in a brainstorm session.

    Args:
        session_uuid: The session identifier returned by brainstorm_turn().
    """
    with connect(paths.db) as conn:
        _ensure_tables(conn)
        session = conn.execute(
            "SELECT * FROM brainstorm_sessions WHERE session_uuid = ?",
            (session_uuid,),
        ).fetchone()
        if not session:
            return [TextContent(type="text", text=f"Session not found: {session_uuid}")]
        turns = conn.execute(
            "SELECT turn_number, topic, steering, context_json, created_at "
            "FROM brainstorm_turns WHERE session_uuid = ? ORDER BY turn_number ASC",
            (session_uuid,),
        ).fetchall()

    result = {
        "session": dict(session),
        "turns": [dict(t) for t in turns],
    }
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


@app.tool()
async def list_brainstorm_sessions(limit: int = 20) -> list[TextContent]:
    """List recent brainstorm sessions with title, turn count, and status.

    Args:
        limit: Maximum sessions to return (default 20).
    """
    with connect(paths.db) as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT bs.session_uuid, bs.title, bs.status, bs.started_at, bs.updated_at, "
            "COUNT(bt.id) as turn_count "
            "FROM brainstorm_sessions bs "
            "LEFT JOIN brainstorm_turns bt ON bs.session_uuid = bt.session_uuid "
            "GROUP BY bs.id ORDER BY bs.updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    sessions = [dict(r) for r in rows]
    return [TextContent(type="text", text=json.dumps(sessions, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# M8.4 — save_brainstorm_output
# ---------------------------------------------------------------------------


@app.tool()
async def save_brainstorm_output(
    session_uuid: str,
    title: str,
    synthesis: str,
    action_items: str = "",
) -> list[TextContent]:
    """Freeze a brainstorm session as a saved Markdown output.

    Writes to outputs/brainstorms/<date>_<slug>.md and updates the
    brainstorm_sessions table status to 'saved'.

    Args:
        session_uuid: The session identifier.
        title:        Short descriptive title for the brainstorm.
        synthesis:    The key insights and connections (Markdown-formatted).
        action_items: Bullet-point action items or follow-up questions.
    """
    with connect(paths.db) as conn:
        _ensure_tables(conn)
        turns = conn.execute(
            "SELECT turn_number, topic, steering, context_json, created_at "
            "FROM brainstorm_turns WHERE session_uuid = ? ORDER BY turn_number ASC",
            (session_uuid,),
        ).fetchall()

        conn.execute(
            "UPDATE brainstorm_sessions SET status='saved', title=?, synthesis=?, "
            "action_items=?, updated_at=datetime('now') WHERE session_uuid=?",
            (title, synthesis, action_items, session_uuid),
        )
        conn.commit()

    # Write Markdown file
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^\w]+", "-", title.lower())[:40].strip("-")
    output_dir = paths.root / "outputs" / "brainstorms"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_str}_{slug}.md"

    lines = [
        f"# Brainstorm: {title}",
        f"\n**Session:** {session_uuid}  ",
        f"**Date:** {date_str}  ",
        f"**Turns:** {len(turns)}\n",
        "---\n",
        "## Synthesis\n",
        synthesis,
        "\n",
    ]
    if action_items:
        lines += ["\n## Action items / follow-up\n", action_items, "\n"]

    if turns:
        lines.append("\n## Turn log\n")
        for t in turns:
            lines.append(f"\n### Turn {t['turn_number']} — {t['steering']} · {t['topic']}\n")
            lines.append(f"*{t['created_at']}*\n")

    output_path.write_text("".join(lines), encoding="utf-8")

    return [TextContent(
        type="text",
        text=json.dumps({
            "status":      "saved",
            "output_path": str(output_path),
            "session_uuid": session_uuid,
        }, indent=2),
    )]
