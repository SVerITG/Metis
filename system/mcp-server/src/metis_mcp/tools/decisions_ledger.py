"""decisions_ledger.py — promote decisions out of session summaries and let them be closed.

THE DEFECT THIS FIXES
    Measured 2026-08-14: 675 of 731 session_summaries rows carry a non-empty
    `decisions` field. `user_decisions` holds 2 rows. Nothing ever read the first
    into the second — a write path with no reader, the same class of defect this
    audit keeps finding, and the most consequential instance of it.

    The visible symptom is duplication. "Fix launcher sync design" and "Resolve the
    INLA dependency" were each recorded six times over three days, because a
    decision nobody closes gets re-stated every session. That is not memory; it is
    an echo. The question a researcher actually asks weeks later — "what did we
    decide, and why?" — cannot be answered from it.

TWO DIFFERENT OBJECTS
    `user_decisions` holds STANDING preferences: "always use tidyverse style". They
    have no lifecycle; they apply until changed.
    `open_decisions` holds a question awaiting a call. It has a lifecycle — open,
    agreed, rejected, deferred, dropped — and a resolution. Cramming both into one
    table behind a flag would have made every query ambiguous, so they stay apart.

DEDUPLICATION IS THE POINT
    A fingerprint (lowercased, punctuation stripped, stopwords removed, sorted) means
    the same decision restated in slightly different words updates `times_seen`
    instead of creating a row. `times_seen` then becomes the useful signal: a
    decision seen nine times is one you keep circling and have never made.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "with", "that",
    "this", "it", "is", "be", "we", "i", "should", "will", "would", "can", "do",
}
_STATES = ("open", "agreed", "rejected", "deferred", "dropped")


# The `decisions` column has been used as a dumping ground for project next-steps
# and task titles. Promoting it wholesale produced 582 "open decisions" of which 21
# were decisions — "HAT Dashboard — _next: Review reactive architecture" had been
# restated 551 times. A restated TASK is not an unmade decision, and mixing them
# makes the ledger exactly the thing the review is meant to replace: a wall you
# cannot act on. So the filter runs at promotion, not as a one-off cleanup.
_NEXT_STEP = re.compile(r"_next:|^\s*\d+\.\d+\s", re.I)
_DECISION_SHAPED = re.compile(
    r"\b(decided|decision|chose|chosen|instead of|rather than|agreed|will use|"
    r"opted|settled on|going with|switch(?:ed)? to|keep|drop(?:ped)?|stays?|"
    r"not to|no longer|deliberately|on purpose)\b", re.I)


def _is_decision(s: str) -> bool:
    """A decision states a CHOICE. A task states work. Only the first belongs here."""
    if _NEXT_STEP.search(s):
        return False
    return bool(_DECISION_SHAPED.search(s))


def _fingerprint(s: str) -> str:
    """Normalise a decision so a re-statement collides with the original.

    Sorted token set, not the raw string: "Resolve INLA for spatial lessons 43, 46"
    and "Resolve the INLA dependency for spatial lessons 43, 46" must be one row.
    """
    words = [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in _STOP]
    return " ".join(sorted(set(words)))[:400]


def _iter_decisions(raw) -> list[str]:
    """A decisions column may hold JSON list, JSON string, or plain text."""
    if raw is None:
        return []
    txt = str(raw).strip()
    if not txt or txt in ("[]", "null", "{}"):
        return []
    try:
        val = json.loads(txt)
        if isinstance(val, list):
            return [str(v).strip() for v in val if str(v).strip()]
        if isinstance(val, str):
            return [val.strip()] if val.strip() else []
        if isinstance(val, dict):
            return [str(v).strip() for v in val.values() if str(v).strip()]
    except Exception:
        pass
    return [p.strip(" -•\t") for p in txt.splitlines() if p.strip(" -•\t")]


@app.tool()
async def promote_session_decisions(limit: int = 2000) -> list[TextContent]:
    """Pull decisions out of session summaries into the open-decisions ledger.

    Deduplicates by normalised fingerprint, so a decision restated across many
    sessions becomes ONE row with a times_seen count rather than many rows. Rows
    already resolved are left alone — re-running this never reopens a closed call.

    Args:
        limit: How many recent session summaries to scan.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    added = bumped = skipped_resolved = not_a_decision = 0
    with connect(paths.db) as con:
        rows = con.execute(
            "SELECT created_at, decisions FROM session_summaries "
            "WHERE decisions IS NOT NULL AND TRIM(decisions) NOT IN ('','[]','null') "
            "ORDER BY created_at DESC LIMIT ?", (limit,),
        ).fetchall()
        for r in rows:
            when = str(r[0] or now)[:19]
            for stmt in _iter_decisions(r[1]):
                if len(stmt) < 8:
                    continue
                if not _is_decision(stmt):
                    not_a_decision += 1
                    continue
                fp = _fingerprint(stmt)
                if not fp:
                    continue
                cur = con.execute(
                    "SELECT od_id, state, times_seen, first_seen FROM open_decisions "
                    "WHERE fingerprint = ?", (fp,)).fetchone()
                if cur:
                    if cur[1] != "open":
                        skipped_resolved += 1
                        continue
                    con.execute(
                        "UPDATE open_decisions SET times_seen = times_seen + 1, "
                        "last_seen = MAX(last_seen, ?) WHERE od_id = ?", (when, cur[0]))
                    bumped += 1
                else:
                    con.execute(
                        "INSERT INTO open_decisions "
                        "(statement, fingerprint, first_seen, last_seen, times_seen, state, source) "
                        "VALUES (?,?,?,?,1,'open','session_summary')",
                        (stmt[:500], fp, when, when))
                    added += 1
        con.commit()
        total = con.execute("SELECT COUNT(*) FROM open_decisions WHERE state='open'").fetchone()[0]

    return [TextContent(type="text", text="\n".join([
        f"Promoted decisions from {len(rows)} session summaries.",
        f"  {added} new · {bumped} restatements folded into an existing decision"
        + (f" · {skipped_resolved} already resolved, left closed" if skipped_resolved else "")
        + (f"\n  {not_a_decision} entries skipped — task titles and project next-steps, "
           f"not decisions" if not_a_decision else ""),
        f"  {total} decision(s) now open and awaiting a call.",
        "",
        "Use review_open_decisions() to walk them, and resolve_decision() to close one.",
    ]))]


@app.tool()
async def review_open_decisions(limit: int = 12, state: str = "open") -> list[TextContent]:
    """Walk the decisions waiting on you, most-repeated first.

    Ordered by how often a decision has been restated, because the one you keep
    circling is the one costing you most.

    Args:
        limit: How many to show.
        state: open | agreed | rejected | deferred | dropped | all
    """
    q = ("SELECT od_id, statement, times_seen, first_seen, last_seen, state, resolution "
         "FROM open_decisions")
    args: tuple = ()
    if state != "all":
        q += " WHERE state = ?"
        args = (state,)
    q += " ORDER BY times_seen DESC, last_seen DESC LIMIT ?"

    with connect(paths.db) as con:
        rows = con.execute(q, args + (limit,)).fetchall()
        counts = dict(con.execute(
            "SELECT state, COUNT(*) FROM open_decisions GROUP BY state").fetchall())

    if not rows:
        return [TextContent(type="text", text=(
            "No decisions in that state. If you expected some, run "
            "promote_session_decisions() first."))]

    out = [f"**{len(rows)} decision(s)** — " + " · ".join(f"{k}: {v}" for k, v in sorted(counts.items())), ""]
    for r in rows:
        age = f"{r[3][:10]} → {r[4][:10]}" if r[3][:10] != r[4][:10] else r[3][:10]
        seen = f" · restated {r[2]}×" if r[2] > 1 else ""
        out.append(f"**#{r[0]}** {r[1]}")
        out.append(f"   {age}{seen}" + (f" · {r[5]}" if r[5] != "open" else ""))
        if r[6]:
            out.append(f"   → {r[6]}")
    out += ["", "To close one: resolve_decision(od_id, 'agreed'|'rejected'|'deferred'|'dropped', why)"]
    return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def resolve_decision(od_id: int, state: str, why: str = "") -> list[TextContent]:
    """Close an open decision: agreed, rejected, deferred or dropped.

    An agreed decision that reads as a standing rule is also copied into
    user_decisions, so it starts being honoured rather than merely recorded.

    Args:
        od_id: From review_open_decisions().
        state: agreed | rejected | deferred | dropped
        why:   One line on the reasoning — this is the part you cannot reconstruct later.
    """
    if state not in _STATES or state == "open":
        return [TextContent(type="text", text=(
            f"'{state}' is not a resolution. Use: agreed, rejected, deferred or dropped."))]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connect(paths.db) as con:
        row = con.execute("SELECT statement, state FROM open_decisions WHERE od_id = ?",
                          (od_id,)).fetchone()
        if not row:
            return [TextContent(type="text", text=f"No decision #{od_id}.")]
        con.execute(
            "UPDATE open_decisions SET state=?, resolution=?, resolved_at=? WHERE od_id=?",
            (state, why.strip() or None, now, od_id))
        promoted = False
        if state == "agreed" and re.search(r"\b(always|never|from now on|by default)\b",
                                           (row[0] + " " + why).lower()):
            con.execute(
                "INSERT OR IGNORE INTO user_decisions (category, decision, context, scope, source, created_at) "
                "VALUES ('workflow', ?, ?, 'always', 'decision-ledger', ?)",
                (row[0][:400], (why or "Agreed from the decision ledger")[:400], now))
            promoted = True
        con.commit()
        left = con.execute("SELECT COUNT(*) FROM open_decisions WHERE state='open'").fetchone()[0]

    msg = [f"#{od_id} marked **{state}**." + (f" — {why}" if why else ""),
           f"{left} decision(s) still open."]
    if promoted:
        msg.append("It reads as a standing rule, so it was also recorded as a preference "
                   "Metis will honour without asking again.")
    return [TextContent(type="text", text="\n".join(msg))]
