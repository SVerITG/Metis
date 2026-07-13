"""Memory Curator: consolidate session history into structured memory entries and surface past context.

Includes tiered retention (R3): decisions >90d are consolidated into monthly
project-level summaries; session summaries >180d are archived; reflexions are
consolidated monthly. This keeps recall() fast while preserving distilled knowledge.
"""

import datetime
import hashlib
import json
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_MEMORY_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
  entry_id TEXT PRIMARY KEY,
  entry_date TEXT,
  entry_type TEXT,
  topics TEXT,
  title TEXT,
  summary TEXT,
  file_path TEXT,
  computer TEXT,
  created_at TEXT
)
"""


def _slug(text: str, max_len: int = 40) -> str:
    s = text.lower()
    for ch in " /\\:*?\"<>|":
        s = s.replace(ch, "-")
    return "-".join(p for p in s.split("-") if p)[:max_len]


@app.tool()
async def consolidate_session_memory(
    n_runs: int = 20,
    min_quality: str = "high",
) -> list[TextContent]:
    """Scan recent agent runs and write structured memory entries for high-value work.

    Reads the n most recent agent_runs, identifies runs with output files and
    substantive task summaries, deduplicates against existing memory_entries,
    and writes new entries to the DB + markdown files.

    Args:
        n_runs: Number of recent agent runs to review (default 20).
        min_quality: 'high' = only runs with output files; 'all' = include run-only entries.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")

    high_value_agents = {
        "epidemiologist", "methods-coach", "writing-partner",
        "critic", "librarian", "data-analyst", "phd-architect",
        "software-engineer", "meeting-memory",
    }

    try:
        with connect(paths.db) as conn:
            conn.execute(_MEMORY_DDL)

            cur = conn.execute(
                """SELECT run_id, agent_slug, task_summary, output_path, input_path, created_at
                   FROM agent_runs
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (n_runs,),
            )
            runs = cur.fetchall()
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading agent_runs: {e}")]

    if not runs:
        return [TextContent(type="text", text="No agent runs found. Nothing to consolidate.")]

    written = []
    skipped_low = 0
    skipped_dup = 0

    for run in runs:
        slug = run["agent_slug"] or ""
        summary_text = run["task_summary"] or ""
        output_path = run["output_path"] or ""

        # Quality gate
        is_high_value = (
            slug in high_value_agents
            or (output_path and Path(paths.root / output_path).exists())
        )
        if min_quality == "high" and not is_high_value:
            skipped_low += 1
            continue

        if len(summary_text) < 20:
            skipped_low += 1
            continue

        title = f"[{slug}] {summary_text[:55]}"
        entry_summary = summary_text[:400]
        topic_map = {
            "epidemiologist": "methods,phd",
            "methods-coach": "statistics,methods",
            "writing-partner": "writing,phd",
            "critic": "review,quality",
            "librarian": "literature",
            "data-analyst": "data,analysis",
            "phd-architect": "phd",
            "software-engineer": "code,metis",
            "meeting-memory": "meetings",
        }
        topics = topic_map.get(slug, "metis")

        # Deduplicate check
        try:
            with connect(paths.db) as conn:
                conn.execute(_MEMORY_DDL)
                cur = conn.execute(
                    "SELECT entry_id FROM memory_entries WHERE title LIKE ? LIMIT 1",
                    (f"%{summary_text[:40]}%",),
                )
                existing = cur.fetchone()
        except Exception:
            existing = None

        if existing:
            skipped_dup += 1
            continue

        # Build entry
        entry_date = (run["created_at"] or today)[:10]
        entry_slug = _slug(summary_text[:40])
        entry_id = f"mem-{entry_date.replace('-', '')}-{entry_slug}"

        detail_lines = [
            f"# {title}",
            f"",
            f"**Agent:** {slug}",
            f"**Date:** {entry_date}",
            f"**Run ID:** {run['run_id']}",
            f"",
            f"## Summary",
            f"{summary_text}",
        ]
        if output_path:
            detail_lines += ["", f"**Output file:** `{output_path}`"]
        if run["input_path"]:
            detail_lines += [f"**Input:** `{run['input_path']}`"]
        detail = "\n".join(detail_lines)

        # Write markdown file
        mem_dir = paths.root / "journal" / "memory" / "sessions"
        mem_dir.mkdir(parents=True, exist_ok=True)
        md_path = mem_dir / f"{entry_date}-{entry_slug}.md"
        file_path_rel = ""
        try:
            md_path.write_text(detail, encoding="utf-8")
            file_path_rel = str(md_path.relative_to(paths.root))
        except Exception:
            pass

        try:
            with connect(paths.db) as conn:
                conn.execute(_MEMORY_DDL)
                conn.execute(
                    """INSERT OR IGNORE INTO memory_entries
                       (entry_id, entry_date, entry_type, topics, title, summary, file_path, computer, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (entry_id, entry_date, "session", topics, title, entry_summary,
                     file_path_rel, "", now.isoformat()),
                )
                conn.commit()
            written.append({"title": title, "type": "session", "topics": topics, "id": entry_id})
        except Exception as e:
            skipped_low += 1
            continue

    # Write consolidation report
    report_lines = [
        f"## Memory Consolidation — {today}",
        f"Runs reviewed: {len(runs)} | High-value: {len(written) + skipped_dup} | "
        f"Entries written: {len(written)} | Duplicates skipped: {skipped_dup} | Low-value skipped: {skipped_low}",
        "",
        "### Entries written",
        "| Title | Type | Topics |",
        "|---|---|---|",
    ]
    for w in written:
        report_lines.append(f"| {w['title'][:60]} | {w['type']} | {w['topics']} |")

    if not written:
        report_lines.append("_(none)_")

    report_lines += [
        "",
        f"### Skipped",
        f"- Low-value / no output: {skipped_low}",
        f"- Duplicate: {skipped_dup}",
    ]

    report_md = "\n".join(report_lines)

    report_dir = paths.root / "outputs" / "reviews" / "memory-curator"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{today}_consolidation.md"
    try:
        report_path.write_text(report_md, encoding="utf-8")
    except Exception:
        pass

    return [TextContent(type="text", text=report_md)]


# ── Tiered retention and consolidation (R3) ────────────────────────────────

_RETENTION_DDL_ARCHIVED = """
ALTER TABLE episodic_memory ADD COLUMN archived INTEGER DEFAULT 0
"""

_RETENTION_DDL_SESSION = """
ALTER TABLE session_summaries ADD COLUMN archived INTEGER DEFAULT 0
"""


def _ensure_archived_col(conn, table: str, ddl: str) -> None:
    """Add 'archived' column if it doesn't exist."""
    try:
        conn.execute(ddl)
    except Exception:
        pass  # already exists


@app.tool()
async def consolidate_old_memories(
    decision_age_days: int = 90,
    session_age_days: int = 180,
    dry_run: bool = False,
) -> list[TextContent]:
    """Consolidate old memories into monthly summaries and archive originals.

    Tiered retention keeps recall() fast by compressing old raw entries into
    distilled summaries while preserving the knowledge:

    1. **Episodic decisions** older than decision_age_days (default 90) are
       grouped by month and project, summarised into a single consolidated
       entry per group, and the originals are marked archived=1 (excluded
       from default recall but still queryable).

    2. **Session summaries** older than session_age_days (default 180) are
       marked archived=1 so they don't clutter keyword search.

    3. **Reflexions** are consolidated monthly — patterns are distilled
       into a single "what we learned in month X" entry.

    Run with dry_run=True first to see what would happen without changes.

    Args:
        decision_age_days: Archive episodic decisions older than this (default 90).
        session_age_days: Archive session summaries older than this (default 180).
        dry_run: If True, report what would be done without making changes.

    Returns:
        A report of consolidation actions taken (or planned if dry_run).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    decision_cutoff = (now - datetime.timedelta(days=decision_age_days)).isoformat()
    session_cutoff = (now - datetime.timedelta(days=session_age_days)).isoformat()

    report_lines = [
        f"## Memory Consolidation {'(DRY RUN)' if dry_run else ''} — {now.strftime('%Y-%m-%d')}",
        f"Decision age threshold: {decision_age_days}d | Session age threshold: {session_age_days}d",
        "",
    ]

    consolidated_decisions = 0
    archived_sessions = 0
    consolidated_reflexions = 0

    try:
        with connect(paths.db) as conn:
            _ensure_archived_col(conn, "episodic_memory", _RETENTION_DDL_ARCHIVED)
            _ensure_archived_col(conn, "session_summaries", _RETENTION_DDL_SESSION)

            # ── 1. Consolidate old episodic decisions ──────────────────
            try:
                old_decisions = conn.execute(
                    """SELECT id, content, metadata, created_at, project_id
                       FROM episodic_memory
                       WHERE event_type = 'decision'
                         AND created_at < ?
                         AND (archived IS NULL OR archived = 0)
                       ORDER BY created_at""",
                    (decision_cutoff,),
                ).fetchall()
            except Exception:
                old_decisions = []

            if old_decisions:
                # Group by month + project
                groups: dict[str, list] = {}
                for row in old_decisions:
                    month = (row["created_at"] or "")[:7]  # YYYY-MM
                    proj = row["project_id"] or "general"
                    key = f"{month}|{proj}"
                    groups.setdefault(key, []).append(row)

                report_lines.append(f"### Episodic decisions: {len(old_decisions)} entries → {len(groups)} groups")

                for key, rows in groups.items():
                    month, proj = key.split("|", 1)
                    contents = [r["content"] for r in rows]
                    summary = f"Consolidated {len(rows)} decisions from {month} (project: {proj}):\n"
                    summary += "\n".join(f"- {c[:200]}" for c in contents)

                    report_lines.append(f"- **{month} / {proj}**: {len(rows)} decisions → 1 consolidated entry")

                    if not dry_run:
                        # Write consolidated entry
                        meta = json.dumps({
                            "source": "consolidation",
                            "original_count": len(rows),
                            "original_ids": [r["id"] for r in rows],
                            "month": month,
                            "project_id": proj,
                        })
                        conn.execute(
                            """INSERT INTO episodic_memory
                               (session_id, event_type, content, metadata, created_at,
                                project_id, scope)
                               VALUES (?, 'consolidated_decisions', ?, ?, ?, ?, 'global')""",
                            (f"consolidation-{month}", summary[:4000], meta,
                             now.isoformat(), proj),
                        )
                        # Mark originals as archived
                        ids = [r["id"] for r in rows]
                        placeholders = ",".join("?" * len(ids))
                        conn.execute(
                            f"UPDATE episodic_memory SET archived = 1 WHERE id IN ({placeholders})",
                            ids,
                        )
                        consolidated_decisions += len(rows)
            else:
                report_lines.append("### Episodic decisions: nothing to consolidate")

            # ── 2. Archive old session summaries ───────────────────────
            try:
                old_sessions = conn.execute(
                    """SELECT COUNT(*) as n FROM session_summaries
                       WHERE created_at < ?
                         AND (archived IS NULL OR archived = 0)""",
                    (session_cutoff,),
                ).fetchone()
                session_count = old_sessions["n"] if old_sessions else 0
            except Exception:
                session_count = 0

            if session_count > 0:
                report_lines.append(f"\n### Session summaries: {session_count} entries to archive")
                if not dry_run:
                    conn.execute(
                        """UPDATE session_summaries SET archived = 1
                           WHERE created_at < ?
                             AND (archived IS NULL OR archived = 0)""",
                        (session_cutoff,),
                    )
                    archived_sessions = session_count
            else:
                report_lines.append("\n### Session summaries: nothing to archive")

            # ── 3. Consolidate old reflexions ──────────────────────────
            try:
                old_reflexions = conn.execute(
                    """SELECT id, agent_slug, went_well, could_improve,
                              missing_context, tool_wishes, created_at
                       FROM reflexion_log
                       WHERE created_at < ?
                         AND (archived IS NULL OR archived = 0)
                       ORDER BY created_at""",
                    (decision_cutoff,),
                ).fetchall()
            except Exception:
                old_reflexions = []

            if old_reflexions:
                # Group by month
                reflex_groups: dict[str, list] = {}
                for row in old_reflexions:
                    month = (row["created_at"] or "")[:7]
                    reflex_groups.setdefault(month, []).append(row)

                report_lines.append(f"\n### Reflexions: {len(old_reflexions)} entries → {len(reflex_groups)} monthly summaries")

                for month, rows in reflex_groups.items():
                    # Distil patterns
                    well = [r["went_well"] for r in rows if r["went_well"]]
                    improve = [r["could_improve"] for r in rows if r["could_improve"]]
                    agents = list({r["agent_slug"] for r in rows if r["agent_slug"]})

                    summary_parts = [f"Reflexion patterns for {month} ({len(rows)} sessions, agents: {', '.join(agents[:5])}):\n"]
                    if well:
                        summary_parts.append("**Went well:** " + "; ".join(w[:100] for w in well[:10]))
                    if improve:
                        summary_parts.append("**Could improve:** " + "; ".join(i[:100] for i in improve[:10]))

                    report_lines.append(f"- **{month}**: {len(rows)} reflexions from {len(agents)} agents")

                    if not dry_run:
                        content = "\n".join(summary_parts)
                        meta = json.dumps({
                            "source": "reflexion_consolidation",
                            "original_count": len(rows),
                            "month": month,
                            "agents": agents,
                        })
                        conn.execute(
                            """INSERT INTO episodic_memory
                               (session_id, event_type, content, metadata, created_at, scope)
                               VALUES (?, 'consolidated_reflexions', ?, ?, ?, 'global')""",
                            (f"reflexion-{month}", content[:4000], meta, now.isoformat()),
                        )
                        # Mark reflexions as archived
                        try:
                            conn.execute("ALTER TABLE reflexion_log ADD COLUMN archived INTEGER DEFAULT 0")
                        except Exception:
                            pass
                        ids = [r["id"] for r in rows]
                        placeholders = ",".join("?" * len(ids))
                        conn.execute(
                            f"UPDATE reflexion_log SET archived = 1 WHERE id IN ({placeholders})",
                            ids,
                        )
                        consolidated_reflexions += len(rows)
            else:
                report_lines.append("\n### Reflexions: nothing to consolidate")

            if not dry_run:
                conn.commit()

    except Exception as e:
        return [TextContent(type="text", text=f"Error during consolidation: {e}")]

    # Summary
    report_lines += [
        "",
        "### Summary",
        f"- Decisions consolidated: {consolidated_decisions}",
        f"- Sessions archived: {archived_sessions}",
        f"- Reflexions consolidated: {consolidated_reflexions}",
    ]
    if dry_run:
        report_lines.append("\n_This was a dry run — no changes were made._")

    return [TextContent(type="text", text="\n".join(report_lines))]


@app.tool()
async def surface_relevant_context(
    topic: str,
    tags: str = "",
    top_n: int = 5,
) -> list[TextContent]:
    """Retrieve past memory entries relevant to a topic and return a structured context brief.

    Searches memory_entries by topic keyword and optional tag list, ranks by
    relevance, and formats the top N entries for injection into the current
    agent's working context.

    Args:
        topic: The topic or task description to search for.
        tags: Optional comma-separated topic tags to include (e.g. 'methods,phd').
        top_n: Maximum number of entries to return (default 5).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_MEMORY_DDL)

            like = f"%{topic}%"
            cur = conn.execute(
                """SELECT entry_id, entry_date, entry_type, topics, title, summary, file_path
                   FROM memory_entries
                   WHERE title LIKE ? OR summary LIKE ? OR topics LIKE ?
                   ORDER BY entry_date DESC
                   LIMIT 30""",
                (like, like, like),
            )
            rows = cur.fetchall()

            tag_rows = []
            if tags:
                for tag in [t.strip() for t in tags.split(",") if t.strip()]:
                    cur2 = conn.execute(
                        """SELECT entry_id, entry_date, entry_type, topics, title, summary, file_path
                           FROM memory_entries
                           WHERE topics LIKE ?
                           ORDER BY entry_date DESC
                           LIMIT 10""",
                        (f"%{tag}%",),
                    )
                    tag_rows.extend(cur2.fetchall())
    except Exception as e:
        return [TextContent(type="text", text=f"Error searching memory: {e}")]

    # Merge and deduplicate by entry_id
    seen = set()
    merged = []
    for row in list(rows) + tag_rows:
        eid = row["entry_id"]
        if eid not in seen:
            seen.add(eid)
            merged.append(row)

    if not merged:
        return [TextContent(type="text", text=f"No memory entries found for topic: '{topic}'.\n\nThis may be a gap — consider running consolidate_session_memory() after relevant agent runs complete.")]

    top = merged[:top_n]

    lines = [
        f"## Relevant past context for: {topic}",
        "",
        "| Entry | Date | Type | Key insight |",
        "|---|---|---|---|",
    ]
    for row in top:
        insight = (row["summary"] or "")[:80].replace("\n", " ")
        lines.append(f"| {row['title'][:50]} | {row['entry_date']} | {row['entry_type']} | {insight} |")

    if top:
        lines += ["", "### Detail — highest relevance entry", ""]
        best = top[0]
        lines.append(f"**{best['title']}** ({best['entry_date']})")
        lines.append(f"Topics: {best['topics']}")
        lines.append(f"\n{best['summary']}")
        if best["file_path"]:
            lines.append(f"\n_Full record: {best['file_path']}_")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool(name="get_memory_health")
async def memory_health_report() -> list[TextContent]:
    """Generate a health report for the memory palace.

    Returns: entry counts by type, topic coverage map, coverage gaps vs active
    projects, duplicate candidates, and entries without output file provenance.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_MEMORY_DDL)

            total_cur = conn.execute("SELECT COUNT(*) as n FROM memory_entries")
            total = total_cur.fetchone()["n"]

            type_cur = conn.execute(
                "SELECT entry_type, COUNT(*) as n FROM memory_entries GROUP BY entry_type ORDER BY n DESC"
            )
            by_type = type_cur.fetchall()

            topic_cur = conn.execute(
                "SELECT topics, COUNT(*) as n FROM memory_entries GROUP BY topics ORDER BY n DESC LIMIT 20"
            )
            by_topic = topic_cur.fetchall()

            oldest_cur = conn.execute(
                "SELECT entry_date, title FROM memory_entries ORDER BY entry_date ASC LIMIT 1"
            )
            oldest = oldest_cur.fetchone()

            no_file_cur = conn.execute(
                "SELECT COUNT(*) as n FROM memory_entries WHERE file_path IS NULL OR file_path = ''"
            )
            no_file = no_file_cur.fetchone()["n"]

    except Exception as e:
        return [TextContent(type="text", text=f"Error generating health report: {e}")]

    core_topics = ["phd", "methods", "statistics", "hat", "ntd", "surveillance",
                   "writing", "code", "metis", "learning", "global-health", "ai"]

    covered_topics = set()
    for row in by_topic:
        for t in (row["topics"] or "").split(","):
            covered_topics.add(t.strip())

    gaps = [t for t in core_topics if t not in covered_topics]

    lines = [
        "## Memory Health Report",
        f"Total entries: **{total}**",
        f"Oldest entry: {oldest['entry_date'] if oldest else 'none'} — {oldest['title'][:50] if oldest else ''}",
        f"Entries without file provenance: {no_file}",
        "",
        "### By type",
        "| Type | Count |",
        "|---|---|",
    ]
    for row in by_type:
        lines.append(f"| {row['entry_type']} | {row['n']} |")

    lines += [
        "",
        "### Topic coverage (top 20 tags)",
        "| Topics | Count |",
        "|---|---|",
    ]
    for row in by_topic:
        lines.append(f"| {row['topics']} | {row['n']} |")

    lines += [
        "",
        "### Coverage gaps (core topics with 0 entries)",
    ]
    if gaps:
        for g in gaps:
            lines.append(f"- `{g}` — no entries")
    else:
        lines.append("No gaps — all core topics covered.")

    lines += [
        "",
        "### Recommendations",
    ]
    if no_file > 0:
        lines.append(f"- {no_file} entries have no linked output file — consider running consolidation with output-linked runs only")
    if gaps:
        lines.append(f"- Run consolidation after completing work in: {', '.join(gaps[:5])}")
    if total == 0:
        lines.append("- Memory palace is empty — run consolidate_session_memory() after any substantial agent session")

    return [TextContent(type="text", text="\n".join(lines))]
