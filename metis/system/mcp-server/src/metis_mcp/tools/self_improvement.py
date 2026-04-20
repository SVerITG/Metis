"""Self-improvement tools: agents propose changes to their own skill files.

Proposals sit in a queue (skill_improvement_proposals table) until the user
approves or rejects them via the System tab or these MCP tools.
No agent can rewrite itself without user approval.
"""

import datetime
import os
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.server import app

_DDL = """
CREATE TABLE IF NOT EXISTS skill_improvement_proposals (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_slug        TEXT NOT NULL,
    proposed_at       TEXT NOT NULL,
    rationale         TEXT DEFAULT '',
    current_content   TEXT DEFAULT '',
    proposed_content  TEXT NOT NULL,
    status            TEXT DEFAULT 'pending',
    reviewer_note     TEXT DEFAULT ''
)
"""

_REFLEXION_DDL = """
CREATE TABLE IF NOT EXISTS reflexion_log (
    reflexion_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    agent_slug      TEXT NOT NULL,
    went_well       TEXT DEFAULT '',
    could_improve   TEXT DEFAULT '',
    missing_context TEXT DEFAULT '',
    tool_wishes     TEXT DEFAULT '',
    created_at      TEXT NOT NULL
)
"""


def _ensure_table() -> None:
    with connect(paths.db) as con:
        con.execute(_DDL)
        con.commit()


def _skill_path(agent_slug: str) -> Path:
    """Resolve the skill.md path for an agent slug."""
    # Primary: .claude/skills/<slug>/skill.md
    skills_dir = paths.root / ".claude" / "skills" / agent_slug / "skill.md"
    if skills_dir.exists():
        return skills_dir
    # Fallback: 02_agents/<slug>/skill.md
    agents_dir = paths.root / "02_agents" / agent_slug / "skill.md"
    return agents_dir


# ── Tool: propose_skill_improvement ──────────────────────────────────────────

@app.tool()
async def propose_skill_improvement(
    agent_slug: str,
    proposed_content: str,
    rationale: str = "",
) -> list[TextContent]:
    """An agent proposes a change to its own skill file.

    The proposal is queued for human review. The skill file is NOT modified
    until the user calls approve_proposal().

    Args:
        agent_slug: The agent's slug (e.g. 'librarian', 'writing-partner')
        proposed_content: The full proposed replacement content of the skill file
        rationale: Why this change is being proposed (1–3 sentences)

    Returns:
        Confirmation with the proposal ID for the user to review
    """
    _ensure_table()

    skill_file = _skill_path(agent_slug)
    current_content = ""
    if skill_file.exists():
        current_content = skill_file.read_text(encoding="utf-8")

    now = datetime.datetime.now().isoformat(timespec="seconds")

    with connect(paths.db) as con:
        cur = con.execute(
            """
            INSERT INTO skill_improvement_proposals
                (agent_slug, proposed_at, rationale, current_content, proposed_content, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (agent_slug, now, rationale, current_content, proposed_content),
        )
        proposal_id = cur.lastrowid
        con.commit()

    return [TextContent(
        type="text",
        text=(
            f"Proposal #{proposal_id} queued for review.\n"
            f"Agent: {agent_slug}\n"
            f"Rationale: {rationale or '(none provided)'}\n\n"
            f"The skill file has NOT been changed. "
            f"Review in the System tab or call get_pending_proposals() / approve_proposal({proposal_id})."
        ),
    )]


# ── Tool: get_pending_proposals ───────────────────────────────────────────────

@app.tool()
async def get_pending_proposals() -> list[TextContent]:
    """List all skill improvement proposals awaiting review.

    Returns proposals sorted by most recent first, with agent slug, rationale,
    and a diff summary (first 200 chars of proposed content).
    """
    _ensure_table()

    with connect(paths.db) as con:
        rows = con.execute(
            """
            SELECT id, agent_slug, proposed_at, rationale,
                   SUBSTR(proposed_content, 1, 200) AS preview,
                   status
              FROM skill_improvement_proposals
             WHERE status = 'pending'
             ORDER BY proposed_at DESC
            """
        ).fetchall()

    if not rows:
        return [TextContent(type="text", text="No pending proposals.")]

    lines = [f"Pending skill improvement proposals ({len(rows)}):", ""]
    for row in rows:
        lines += [
            f"#{row['id']} — {row['agent_slug']}  [{row['proposed_at']}]",
            f"  Rationale: {row['rationale'] or '(none)'}",
            f"  Preview:   {row['preview']}…",
            "",
        ]
    lines.append("Call approve_proposal(id) or reject_proposal(id) to action them.")

    return [TextContent(type="text", text="\n".join(lines))]


# ── Tool: approve_proposal ────────────────────────────────────────────────────

@app.tool()
async def approve_proposal(proposal_id: int) -> list[TextContent]:
    """Approve a pending skill improvement proposal and apply it.

    Writes the proposed content to the agent's skill.md file and marks
    the proposal as approved. Creates a backup of the current skill file first.

    Args:
        proposal_id: The numeric ID from get_pending_proposals()
    """
    _ensure_table()

    with connect(paths.db) as con:
        row = con.execute(
            "SELECT * FROM skill_improvement_proposals WHERE id = ? AND status = 'pending'",
            (proposal_id,),
        ).fetchone()

    if not row:
        return [TextContent(
            type="text",
            text=f"Proposal #{proposal_id} not found or not in pending status.",
        )]

    agent_slug      = row["agent_slug"]
    proposed_content = row["proposed_content"]
    skill_file       = _skill_path(agent_slug)

    # Ensure parent directory exists
    skill_file.parent.mkdir(parents=True, exist_ok=True)

    # Back up current file before overwriting
    if skill_file.exists():
        backup_path = skill_file.with_suffix(
            f".backup-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        )
        backup_path.write_text(skill_file.read_text(encoding="utf-8"), encoding="utf-8")

    # Write proposed content
    skill_file.write_text(proposed_content, encoding="utf-8")

    # Mark as approved
    with connect(paths.db) as con:
        con.execute(
            "UPDATE skill_improvement_proposals SET status = 'approved' WHERE id = ?",
            (proposal_id,),
        )
        con.commit()

    return [TextContent(
        type="text",
        text=(
            f"Proposal #{proposal_id} approved and applied.\n"
            f"Skill file updated: {skill_file}\n"
            f"Backup saved alongside the file."
        ),
    )]


# ── Tool: reject_proposal ─────────────────────────────────────────────────────

@app.tool()
async def reject_proposal(proposal_id: int, reason: str = "") -> list[TextContent]:
    """Reject a pending skill improvement proposal without applying it.

    The skill file is not changed. The proposal is marked rejected with an
    optional reason.

    Args:
        proposal_id: The numeric ID from get_pending_proposals()
        reason: Optional note explaining why the proposal was rejected
    """
    _ensure_table()

    with connect(paths.db) as con:
        row = con.execute(
            "SELECT id, agent_slug FROM skill_improvement_proposals WHERE id = ? AND status = 'pending'",
            (proposal_id,),
        ).fetchone()

    if not row:
        return [TextContent(
            type="text",
            text=f"Proposal #{proposal_id} not found or not in pending status.",
        )]

    with connect(paths.db) as con:
        con.execute(
            "UPDATE skill_improvement_proposals SET status = 'rejected', reviewer_note = ? WHERE id = ?",
            (reason, proposal_id),
        )
        con.commit()

    return [TextContent(
        type="text",
        text=(
            f"Proposal #{proposal_id} rejected.\n"
            f"Agent: {row['agent_slug']}\n"
            f"Reason: {reason or '(none provided)'}\n"
            f"The skill file was not changed."
        ),
    )]


# ── Tool: write_reflexion ─────────────────────────────────────────────────────

@app.tool()
async def write_reflexion(
    session_id: str,
    agent_slug: str,
    went_well: str = "",
    could_improve: str = "",
    missing_context: str = "",
    tool_wishes: str = "",
) -> list[TextContent]:
    """Stage 11: Record an agent self-critique entry to the reflexion_log.

    Called at the end of every agent run to capture experience: what worked,
    what could be better, what context was missing, what tools were needed.
    Entries are reviewed by the weekly Coach loop for self-improvement proposals.

    Args:
        session_id: Pipeline session ID from session_bootstrap().
        agent_slug: Which agent is writing the reflexion (e.g. 'librarian').
        went_well: What went well in this run (1–2 sentences).
        could_improve: What could have been done better (1–2 sentences).
        missing_context: What context or data was unavailable but needed.
        tool_wishes: Tools or capabilities that would have helped.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as con:
            con.execute(_REFLEXION_DDL)
            con.execute(
                """INSERT INTO reflexion_log
                   (session_id, agent_slug, went_well, could_improve,
                    missing_context, tool_wishes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, agent_slug, went_well, could_improve,
                 missing_context, tool_wishes, now),
            )
            con.commit()

        return [TextContent(
            type="text",
            text=f"Reflexion recorded for '{agent_slug}' (session {session_id[:8]}…).",
        )]
    except Exception as e:
        return [TextContent(type="text", text=f"Error writing reflexion: {e}")]
