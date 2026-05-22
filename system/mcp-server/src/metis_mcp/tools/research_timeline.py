"""Temporal research timeline — track how beliefs and findings evolve over time.

Answers questions like: "What did I think about RDT sensitivity in January?
What changed? When did the evidence shift?" This is the core value of a temporal
knowledge graph, implemented directly in SQLite to avoid Neo4j/Docker overhead.

Each entry is a timestamped claim about an entity. When new evidence changes
your view, record a new claim with supersedes=<old_id>. The timeline then shows
the full chain of reasoning over time.
"""

from __future__ import annotations

import datetime
import json

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

_DDL = """
CREATE TABLE IF NOT EXISTS research_timeline (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entity       TEXT    NOT NULL,
    claim        TEXT    NOT NULL,
    confidence   TEXT    NOT NULL DEFAULT 'medium',
    evidence     TEXT    NOT NULL DEFAULT '',
    source_type  TEXT    NOT NULL DEFAULT 'session',
    source_ref   TEXT    NOT NULL DEFAULT '',
    supersedes   INTEGER          DEFAULT NULL,
    session_date TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    FOREIGN KEY (supersedes) REFERENCES research_timeline(id)
)
"""


def _ensure(conn) -> None:
    conn.execute(_DDL)
    conn.commit()


@app.tool()
async def record_research_finding(
    entity: str,
    claim: str,
    evidence: str = "",
    confidence: str = "medium",
    source_type: str = "session",
    source_ref: str = "",
    supersedes_id: int = 0,
) -> list[TextContent]:
    """Record a timestamped research belief or finding about an entity.

    Use this whenever you reach a conclusion, update a previous belief, or
    encounter evidence that changes your view. The timeline preserves the full
    chain of reasoning across sessions.

    Args:
        entity: What this claim is about. Use a consistent name across sessions
            (e.g. "RDT sensitivity in low-burden areas", "HAT elimination DRC",
            "DHIS2 tracker performance").
        claim: Your current belief or finding in 1-3 sentences.
        evidence: What supports this claim — paper citation, data result, meeting
            discussion. Brief reference is enough.
        confidence: "low", "medium", or "high".
        source_type: "session", "paper", "meeting", "data_analysis", "literature_review".
        source_ref: Specific reference — DOI, file path, meeting date.
        supersedes_id: If this replaces a previous claim, pass that claim's id.
            Set to 0 if this is a new claim with no predecessor.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    today = datetime.date.today().isoformat()

    try:
        with connect(paths.db) as conn:
            _ensure(conn)
            cur = conn.execute(
                """INSERT INTO research_timeline
                   (entity, claim, confidence, evidence, source_type, source_ref,
                    supersedes, session_date, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entity,
                    claim,
                    confidence,
                    evidence,
                    source_type,
                    source_ref,
                    supersedes_id if supersedes_id > 0 else None,
                    today,
                    now,
                ),
            )
            new_id = cur.lastrowid
            conn.commit()

        msg = f"Finding recorded (id={new_id}, entity='{entity}', confidence={confidence})."
        if supersedes_id > 0:
            msg += f" Supersedes claim #{supersedes_id}."
        return [TextContent(type="text", text=msg)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error recording finding: {e}")]


@app.tool()
async def query_research_timeline(
    entity: str = "",
    since_date: str = "",
    show_superseded: bool = False,
) -> list[TextContent]:
    """Query the temporal evolution of research beliefs.

    Returns all claims for an entity ordered by date, showing how thinking
    evolved. Superseded claims (older beliefs you updated) are hidden by default
    but can be shown to trace the full reasoning chain.

    Args:
        entity: Filter by entity name (partial match). Leave empty to see all
            recent entries across all entities.
        since_date: ISO date string (YYYY-MM-DD). Only show entries on or after
            this date. Leave empty for all time.
        show_superseded: If True, include claims that have been replaced by newer
            ones. Default False — shows only the current belief for each topic.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            _ensure(conn)

            # Build query
            conditions = []
            params: list = []

            if entity:
                conditions.append("entity LIKE ?")
                params.append(f"%{entity}%")

            if since_date:
                conditions.append("session_date >= ?")
                params.append(since_date)

            if not show_superseded:
                # Exclude claims that are superseded by a newer one
                conditions.append("""
                    id NOT IN (
                        SELECT supersedes FROM research_timeline
                        WHERE supersedes IS NOT NULL
                    )
                """)

            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            sql = f"""
                SELECT id, entity, claim, confidence, evidence,
                       source_type, source_ref, supersedes, session_date
                FROM research_timeline
                {where}
                ORDER BY session_date DESC, id DESC
                LIMIT 50
            """
            rows = conn.execute(sql, params).fetchall()

        if not rows:
            hint = f" for '{entity}'" if entity else ""
            return [TextContent(type="text", text=f"No research timeline entries found{hint}.")]

        lines = [f"## Research Timeline — {len(rows)} entries\n"]
        current_entity = None
        for r in reversed(rows):  # chronological order
            if r[1] != current_entity:
                current_entity = r[1]
                lines.append(f"\n### {current_entity}")
            sup_note = f" *(supersedes #{r[7]})*" if r[7] else ""
            lines.append(
                f"\n**{r[8]}** [{r[3]} confidence]{sup_note}  \n"
                f"{r[2]}  \n"
                f"*{r[5]}: {r[6] or '—'}*  \n"
                f"{('Evidence: ' + r[4]) if r[4] else ''}"
            )

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error querying timeline: {e}")]


@app.tool()
async def list_research_entities() -> list[TextContent]:
    """List all entities in the research timeline with their claim count and last update.

    Use this to get an overview of what topics have tracked beliefs, before
    drilling into a specific entity with query_research_timeline().
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            _ensure(conn)
            rows = conn.execute("""
                SELECT entity,
                       COUNT(*) AS total_claims,
                       MAX(session_date) AS last_updated,
                       SUM(CASE WHEN id NOT IN (
                           SELECT COALESCE(supersedes, -1) FROM research_timeline
                       ) THEN 1 ELSE 0 END) AS active_claims
                FROM research_timeline
                GROUP BY entity
                ORDER BY last_updated DESC
            """).fetchall()

        if not rows:
            return [TextContent(type="text", text="No research timeline entries yet.")]

        lines = ["## Research Entities\n", "| Entity | Active | Total | Last updated |",
                 "|--------|--------|-------|--------------|"]
        for r in rows:
            lines.append(f"| {r[0]} | {r[3]} | {r[1]} | {r[2]} |")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error listing entities: {e}")]
