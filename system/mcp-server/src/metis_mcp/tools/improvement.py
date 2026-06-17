"""Self-improvement loop — Phase 9b.

Reads recent ``reflexion_log`` entries, themes them per agent, and drafts
``skill_improvement_proposals`` rows. The user remains in the loop: drafts
land in ``status='draft'`` until they review and approve via the existing
``approve_proposal`` tool or the Metis-tab dashboard surface.

Pure functions (callable from the FastAPI dashboard) plus ``@app.tool()``
wrappers for MCP / Claude Code.
"""

import datetime
import os
import re
from collections import Counter
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.models import model_for


# Words too generic to be useful as a "theme"
_STOP_WORDS = frozenset("""
a an and the of to for in on at by with as is was are were be been being it
this that these those i me my we our you your they them their he she him
her his hers but or if so not no yes do does did done can could should would
will may might must have has had having there here when where why how what
which who whom whose all any some many few more most less least other
another such same own about into onto off out over under up down before
after during while because since though although however therefore thus
also too very just only than then now once just like only really still
even ever already always usually often sometimes rarely never each any
both either neither none all every some many few much such ahead back
"""
.split())


def _ensure_tables() -> None:
    """Mirror the DDL from self_improvement.py + reflexion_log."""
    with connect(paths.db) as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS reflexion_log (
                reflexion_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                agent_slug      TEXT NOT NULL,
                went_well       TEXT DEFAULT '',
                could_improve   TEXT DEFAULT '',
                missing_context TEXT DEFAULT '',
                tool_wishes     TEXT DEFAULT '',
                created_at      TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS skill_improvement_proposals (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_slug        TEXT NOT NULL,
                proposed_at       TEXT NOT NULL,
                rationale         TEXT DEFAULT '',
                current_content   TEXT DEFAULT '',
                proposed_content  TEXT NOT NULL,
                status            TEXT DEFAULT 'pending',
                reviewer_note     TEXT DEFAULT ''
            )"""
        )
        con.commit()


def _skill_path(agent_slug: str) -> Path | None:
    """Locate the skill file for an agent. Tries .claude/skills then agents/."""
    candidates = [
        paths.root / ".claude" / "skills" / agent_slug / "skill.md",
        paths.root / "agents" / agent_slug / "skill.md",
        paths.root / "agents" / agent_slug / "system-prompt.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _theme_from(texts: list[str], top_n: int = 3) -> list[tuple[str, int]]:
    """Return top N semantic themes from a list of reflexion texts.

    Uses Claude Haiku for semantic extraction when ANTHROPIC_API_KEY is set
    (produces meaningful themes like "agent lacks NTD domain knowledge" rather
    than token frequencies). Falls back to word-frequency counting otherwise.
    """
    if not texts:
        return []

    non_empty = [t for t in texts if t and t.strip()]
    if not non_empty:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key and len(non_empty) >= 2:
        try:
            import json as _json
            import httpx as _httpx

            combined = "\n---\n".join(non_empty)
            resp = _httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model_for("brief"),
                    "max_tokens": 256,
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Read these {len(non_empty)} reflexion notes written after AI agent runs. "
                            f"Identify the top {top_n} recurring semantic themes — short descriptive phrases "
                            "(not single words). Return ONLY a JSON array: "
                            '[[\"theme description\", occurrence_count], ...]. '
                            "No explanation, no markdown, just the array.\n\n"
                            f"Reflexions:\n{combined[:3000]}"
                        ),
                    }],
                },
                timeout=20.0,
            )
            if resp.status_code == 200:
                raw = resp.json()["content"][0]["text"].strip()
                start, end = raw.find("["), raw.rfind("]") + 1
                if start >= 0 and end > start:
                    parsed = _json.loads(raw[start:end])
                    if isinstance(parsed, list) and parsed:
                        return [
                            (str(item[0]), int(item[1]))
                            for item in parsed[:top_n]
                            if isinstance(item, (list, tuple)) and len(item) >= 2
                        ]
        except Exception:
            pass  # fall through to word-frequency

    # Word-frequency fallback
    counter: Counter[str] = Counter()
    for t in non_empty:
        tokens = re.findall(r"[a-z][a-z\-]{2,}", t.lower())
        for tok in tokens:
            if tok not in _STOP_WORDS:
                counter[tok] += 1
    return counter.most_common(top_n)


def aggregate_reflexions(agent_slug: str | None = None,
                         days: int = 14) -> dict:
    """Theme recent reflexions per agent.

    Returns a dict like::

        {
            "window_days": 14,
            "agents": [
                {
                    "agent_slug": "librarian",
                    "n_reflexions": 12,
                    "could_improve_themes":   [["sources", 5], ...],
                    "missing_context_themes": [...],
                    "tool_wishes_themes":     [...],
                    "samples": {
                        "could_improve":   [..first 3 raw entries..],
                        "missing_context": [...],
                        "tool_wishes":     [...],
                    },
                },
                ...
            ],
            "totals": {"reflexions": 47, "agents": 5},
        }
    """
    _ensure_tables()
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=days)
    ).isoformat()

    where = "WHERE created_at >= ?"
    params: list = [cutoff]
    if agent_slug:
        where += " AND agent_slug = ?"
        params.append(agent_slug)

    with connect(paths.db) as con:
        rows = con.execute(
            f"""SELECT agent_slug, went_well, could_improve, missing_context,
                       tool_wishes, created_at
                FROM reflexion_log {where}
                ORDER BY agent_slug, created_at DESC""",
            params,
        ).fetchall()

    rows = [dict(r) for r in rows]
    by_agent: dict[str, list[dict]] = {}
    for r in rows:
        by_agent.setdefault(r["agent_slug"], []).append(r)

    agents_out: list[dict] = []
    for slug, entries in by_agent.items():
        could_improve = [e["could_improve"] for e in entries if e["could_improve"]]
        missing_context = [e["missing_context"] for e in entries if e["missing_context"]]
        tool_wishes = [e["tool_wishes"] for e in entries if e["tool_wishes"]]
        agents_out.append({
            "agent_slug": slug,
            "n_reflexions": len(entries),
            "could_improve_themes":   _theme_from(could_improve),
            "missing_context_themes": _theme_from(missing_context),
            "tool_wishes_themes":     _theme_from(tool_wishes),
            "samples": {
                "could_improve":   could_improve[:3],
                "missing_context": missing_context[:3],
                "tool_wishes":     tool_wishes[:3],
            },
        })

    # Sort agents by reflexion count, busiest first
    agents_out.sort(key=lambda a: -a["n_reflexions"])

    return {
        "window_days": days,
        "agents": agents_out,
        "totals": {"reflexions": len(rows), "agents": len(by_agent)},
    }


def _format_themes(themes: list[tuple[str, int]]) -> str:
    if not themes:
        return "—"
    return ", ".join(f"`{t}` ({c})" for t, c in themes)


def draft_self_improvement_proposal(agent_slug: str,
                                    days: int = 14) -> dict:
    """Build a draft skill-improvement proposal grounded in reflexion themes.

    Inserts the draft into ``skill_improvement_proposals`` with
    ``status='draft'`` so the user reviews before promoting to ``pending`` or
    approving directly.

    Returns the proposal id and a preview.
    """
    _ensure_tables()
    agg = aggregate_reflexions(agent_slug=agent_slug, days=days)
    if not agg["agents"]:
        return {
            "status": "empty",
            "message": (
                f"No reflexions for `{agent_slug}` in the last {days} days. "
                "Run more agent jobs first, or pick a busier agent."
            ),
        }

    a = agg["agents"][0]
    skill_file = _skill_path(agent_slug)
    current = skill_file.read_text(encoding="utf-8") if skill_file else ""

    rationale = (
        f"Drafted from {a['n_reflexions']} reflexions in the last {days} days. "
        f"Recurring 'could improve' themes: {_format_themes(a['could_improve_themes'])}. "
        f"Recurring 'missing context' themes: {_format_themes(a['missing_context_themes'])}. "
        f"Recurring 'tool wishes': {_format_themes(a['tool_wishes_themes'])}."
    )

    addendum_lines = [
        "",
        "",
        "## Self-improvement notes (draft — review before keeping)",
        "",
        f"_Auto-drafted on {datetime.date.today().isoformat()} from "
        f"{a['n_reflexions']} reflexions over the last {days} days._",
        "",
    ]
    if a["could_improve_themes"]:
        addendum_lines.append(
            f"- **Recurring weaknesses to address**: "
            f"{_format_themes(a['could_improve_themes'])}"
        )
    if a["missing_context_themes"]:
        addendum_lines.append(
            f"- **Context I keep wishing I had**: "
            f"{_format_themes(a['missing_context_themes'])}"
        )
    if a["tool_wishes_themes"]:
        addendum_lines.append(
            f"- **Tools I keep wishing I had**: "
            f"{_format_themes(a['tool_wishes_themes'])}"
        )

    if a["samples"]["could_improve"]:
        addendum_lines.append("")
        addendum_lines.append("Recent verbatim examples:")
        for e in a["samples"]["could_improve"]:
            addendum_lines.append(f"  - {e[:160]}")

    proposed_content = current + "\n".join(addendum_lines)

    now = datetime.datetime.now().isoformat(timespec="seconds")
    with connect(paths.db) as con:
        cur = con.execute(
            """INSERT INTO skill_improvement_proposals
               (agent_slug, proposed_at, rationale, current_content,
                proposed_content, status)
               VALUES (?, ?, ?, ?, ?, 'draft')""",
            (agent_slug, now, rationale, current, proposed_content),
        )
        proposal_id = cur.lastrowid
        con.commit()

    return {
        "status": "ok",
        "proposal_id": proposal_id,
        "agent_slug": agent_slug,
        "rationale": rationale,
        "n_reflexions": a["n_reflexions"],
        "preview": "\n".join(addendum_lines).strip()[:400],
    }


# ── Consolidation: reflexion themes → semantic memory ────────────────────────


def consolidate_reflexions(days: int = 14, min_count: int = 3,
                           prune_working_days: int = 7) -> dict:
    """Distil recurring reflexion themes into semantic memory + prune working memory.

    Closes the loop the 2026-05-30 self-reflexion flagged: reflexions were logged
    but never fed back into the searchable semantic layer, and working_memory
    grew without bound. This is the nightly consolidation step.

    For every (agent, theme) that recurs >= min_count times across could_improve /
    missing_context / tool_wishes, writes ONE semantic_memory node (deduped by
    concept, so re-running nightly is idempotent). Then deletes working_memory
    rows older than prune_working_days.

    VERIFIED-ONLY MEMORY: the ``min_count`` recurrence threshold IS the verification
    gate. A single self-critique is unreliable (LLMs can't intrinsically self-correct
    — Huang et al. 2310.01798), so only a theme *corroborated* by recurring across
    >= min_count independent runs is promoted to the durable, searchable semantic
    layer. Un-corroborated reflexions stay in reflexion_log (the audit trail) but
    never pollute retrieval — i.e. unconfirmed self-critique is not promoted.

    Returns a summary dict. Embedding is best-effort (skipped if fastembed absent).
    """
    agg = aggregate_reflexions(days=days)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    written, skipped, pruned = 0, 0, 0

    # Best-effort embedding
    def _embed(text: str):
        try:
            from metis_mcp.embeddings import embed_document
            return embed_document(text)
        except Exception:
            return None

    try:
        from metis_mcp.tools.vector_memory import _encode_vec  # type: ignore
    except Exception:
        _encode_vec = None

    with connect(paths.db) as con:
        existing = {
            r[0] for r in con.execute(
                "SELECT concept FROM semantic_memory WHERE source_type='reflexion'"
            ).fetchall()
        }
        for a in agg.get("agents", []):
            slug = a.get("agent_slug", "?")
            for category, label in (
                ("could_improve_themes", "could improve"),
                ("missing_context_themes", "often lacks context on"),
                ("tool_wishes_themes", "wants tooling for"),
            ):
                for theme, count in a.get(category, []):
                    if count < min_count:
                        continue
                    concept = f"self-improvement: {slug} · {theme}"
                    if concept in existing:
                        skipped += 1
                        continue
                    definition = (
                        f"Across recent sessions, the {slug} agent repeatedly "
                        f"{label} '{theme}' ({count}× in {days} days). "
                        f"Consider addressing this in the agent's skill or context."
                    )
                    cur = con.execute(
                        """INSERT INTO semantic_memory
                           (concept, definition, related_concepts, source_type, source_id, created_at, updated_at)
                           VALUES (?, ?, ?, 'reflexion', ?, ?, ?)""",
                        (concept, definition, slug, f"reflexion:{slug}", now, now),
                    )
                    vec = _embed(f"{concept}: {definition}")
                    if vec is not None and _encode_vec is not None:
                        try:
                            con.execute(
                                "INSERT INTO vec_semantic (rowid, embedding) VALUES (?, ?)",
                                (cur.lastrowid, _encode_vec(vec)),
                            )
                        except Exception:
                            pass
                    existing.add(concept)
                    written += 1

        # Prune stale working memory
        try:
            cutoff = (datetime.datetime.now(datetime.timezone.utc)
                      - datetime.timedelta(days=prune_working_days)).isoformat()
            cur = con.execute("DELETE FROM working_memory WHERE created_at < ?", (cutoff,))
            pruned = cur.rowcount or 0
        except Exception:
            pruned = 0
        con.commit()

    return {
        "semantic_written": written,
        "semantic_skipped_existing": skipped,
        "working_memory_pruned": pruned,
        "agents_reviewed": len(agg.get("agents", [])),
    }


# ── MCP tool wrappers ────────────────────────────────────────────────────────


@app.tool(name="consolidate_reflexions")
async def consolidate_reflexions_tool(days: int = 14, min_count: int = 3) -> list[TextContent]:
    """Distil recurring reflexion themes into semantic memory and prune working memory.

    Runs the nightly self-improvement consolidation: every theme an agent raised
    >= min_count times in the last `days` becomes a searchable semantic-memory
    node (deduped), and working_memory older than 7 days is pruned. Idempotent.
    """
    r = consolidate_reflexions(days=days, min_count=min_count)
    return [TextContent(type="text", text=(
        f"Consolidation complete — {r['semantic_written']} new semantic node(s) from "
        f"{r['agents_reviewed']} agent(s), {r['semantic_skipped_existing']} already known, "
        f"{r['working_memory_pruned']} stale working-memory row(s) pruned."
    ))]


@app.tool(name="aggregate_reflexions")
async def aggregate_reflexions_tool(agent_slug: str = "",
                                    days: int = 14) -> list[TextContent]:
    """Theme recent reflexions per agent (Phase 9b).

    Reads ``reflexion_log`` entries from the last ``days`` days (default 14)
    and returns the top recurring 'could improve', 'missing context', and
    'tool wishes' themes, ordered by busiest agent.

    Pass ``agent_slug`` to limit the scope; leave blank for all agents.
    """
    result = aggregate_reflexions(
        agent_slug=agent_slug or None,
        days=days,
    )
    if result["totals"]["reflexions"] == 0:
        return [TextContent(
            type="text",
            text=f"No reflexions in the last {days} days. "
                 "Agents need to call write_reflexion to feed this loop.",
        )]
    lines = [
        f"Reflexion themes — last {result['window_days']} days "
        f"({result['totals']['reflexions']} entries across "
        f"{result['totals']['agents']} agents)",
        "",
    ]
    for a in result["agents"]:
        lines.append(f"## {a['agent_slug']}  ({a['n_reflexions']} reflexions)")
        lines.append(
            f"- could_improve:   {_format_themes(a['could_improve_themes'])}"
        )
        lines.append(
            f"- missing_context: {_format_themes(a['missing_context_themes'])}"
        )
        lines.append(
            f"- tool_wishes:     {_format_themes(a['tool_wishes_themes'])}"
        )
        lines.append("")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool(name="draft_self_improvement_proposal")
async def draft_self_improvement_proposal_tool(
        agent_slug: str,
        days: int = 14) -> list[TextContent]:
    """Draft a skill-improvement proposal from recent reflexions (Phase 9b).

    Reads themed reflexions for ``agent_slug``, appends a 'Self-improvement
    notes' section to the agent's current skill.md, and queues the result in
    ``skill_improvement_proposals`` with status='draft'.

    The draft is NOT applied. Use ``apply_proposal(id)`` to write it to disk.
    """
    result = draft_self_improvement_proposal(agent_slug, days=days)
    if result["status"] != "ok":
        return [TextContent(type="text", text=result.get("message", "draft failed"))]
    return [TextContent(
        type="text",
        text=(
            f"Draft proposal #{result['proposal_id']} queued for `{agent_slug}` "
            f"(grounded in {result['n_reflexions']} reflexions).\n\n"
            f"Rationale:\n{result['rationale']}\n\n"
            f"Preview of the new section:\n\n{result['preview']}\n\n"
            "Review with `get_pending_proposals()` (also lists drafts) and "
            "apply with `apply_proposal({pid})`.".format(pid=result["proposal_id"])
        ),
    )]


def apply_proposal(proposal_id: int) -> dict:
    """Apply an approved/promoted proposal: write proposed_content to disk.

    Behaviour:
      1. Look up the proposal. Must exist and be in status 'pending'/'draft'/'approved'.
      2. Resolve the agent's skill.md path (uses _skill_path).
      3. Back up the current file to `<file>.bak.<timestamp>` next to it.
      4. Write proposed_content to the file.
      5. Update the proposal row to status='applied' with applied_at timestamp.

    Returns a dict with status, the backup path, and a one-line summary so the
    caller (dashboard or CLI) can display what happened.
    """
    _ensure_tables()
    with connect(paths.db) as con:
        row = con.execute(
            "SELECT id, agent_slug, proposed_content, status "
            "FROM skill_improvement_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()

    if row is None:
        return {"status": "error", "message": f"Proposal #{proposal_id} not found."}

    row = dict(row)
    if row["status"] not in ("pending", "draft", "approved"):
        return {
            "status": "error",
            "message": (
                f"Proposal #{proposal_id} is in status '{row['status']}'; "
                "only 'pending', 'draft', or 'approved' proposals can be applied."
            ),
        }

    skill_file = _skill_path(row["agent_slug"])
    if skill_file is None:
        return {
            "status": "error",
            "message": (
                f"No skill.md found for agent '{row['agent_slug']}'. "
                "Looked in .claude/skills/<slug>/ and agents/<slug>/."
            ),
        }

    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = skill_file.with_suffix(f".md.bak.{timestamp}")
    try:
        backup_path.write_text(skill_file.read_text(encoding="utf-8"), encoding="utf-8")
        skill_file.write_text(row["proposed_content"], encoding="utf-8")
    except Exception as e:
        return {"status": "error", "message": f"Filesystem error: {e}"}

    applied_at = datetime.datetime.now().isoformat(timespec="seconds")
    with connect(paths.db) as con:
        # Some installs may not yet have the applied_at column; ALTER if missing.
        cols = {r[1] for r in con.execute(
            "PRAGMA table_info(skill_improvement_proposals)"
        )}
        if "applied_at" not in cols:
            try:
                con.execute(
                    "ALTER TABLE skill_improvement_proposals ADD COLUMN applied_at TEXT"
                )
            except Exception:
                pass
        if "backup_path" not in cols:
            try:
                con.execute(
                    "ALTER TABLE skill_improvement_proposals ADD COLUMN backup_path TEXT"
                )
            except Exception:
                pass
        con.execute(
            "UPDATE skill_improvement_proposals SET status='applied', "
            "applied_at = ?, backup_path = ? WHERE id = ?",
            (applied_at, str(backup_path), proposal_id),
        )
        con.commit()

    return {
        "status": "ok",
        "proposal_id": proposal_id,
        "agent_slug": row["agent_slug"],
        "skill_file": str(skill_file),
        "backup_path": str(backup_path),
        "applied_at": applied_at,
    }


@app.tool(name="apply_proposal")
async def apply_proposal_tool(proposal_id: int) -> list[TextContent]:
    """Apply a self-improvement proposal: writes the proposed change to disk.

    The previous skill.md content is backed up alongside as
    ``skill.md.bak.<timestamp>`` so a revert is always possible. Updates the
    proposal row to status='applied' with the applied_at timestamp and the
    backup path.

    Args:
        proposal_id: the id from skill_improvement_proposals.
    """
    result = apply_proposal(proposal_id)
    if result["status"] != "ok":
        return [TextContent(type="text", text=result.get("message", "apply failed"))]
    return [TextContent(
        type="text",
        text=(
            f"Proposal #{result['proposal_id']} applied to `{result['agent_slug']}`.\n"
            f"- Wrote: {result['skill_file']}\n"
            f"- Backup: {result['backup_path']}\n"
            f"- Applied at: {result['applied_at']}\n"
            "If the change is wrong, restore from the backup and set status back to 'rejected'."
        ),
    )]
