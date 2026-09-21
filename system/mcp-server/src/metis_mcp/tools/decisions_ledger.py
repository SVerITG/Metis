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

# A decision NARRATED: someone reports the act of having chosen.
_DECISION_SHAPED = re.compile(
    r"\b(decided|decision|chose|chosen|instead of|rather than|agreed|will use|"
    r"opted|settled on|going with|switch(?:ed)? to|keep|drop(?:ped)?|stays?|"
    r"not to|no longer|deliberately|on purpose|replaces?|superseded?)\b", re.I)

# A decision STATED AS A RULE — and this is the form that was invisible.
#
# WHY THIS BRANCH EXISTS (audit 2026-09-14)
#     `_DECISION_SHAPED` requires a past-tense verb of deciding. But a standing
#     preference — the kind that is actually useful to inject into a specialist —
#     is almost always written as a rule in the imperative or present:
#
#         "Always put the takeaway in the slide title, never a topic label"
#         "Master slides use the teal band B variant for all RCA training decks"
#
#     Both were rejected. The filter was not selecting decisions, it was
#     selecting a WRITING STYLE, and it happened to select the style used for
#     engineering narration — which is why `user_decisions` filled with
#     architecture notes and held nothing about how the researcher wants his
#     work done. This is the single mechanism behind "Metis never learns my
#     preferences".
_NORMATIVE = re.compile(
    r"\b(always|never|by default|default(?:s)? to|prefer(?:s|red)?|"
    r"stick to|house style|convention|rule:|must (?:be|use|stay|go)|"
    r"should (?:always|never)|only ever|not the|, not\b)\b", re.I)

# A convention stated as a plain declarative, with no rule word and no verb of
# deciding: "Master slides use the teal band B variant FOR ALL RCA training
# decks". What makes it a standing rule rather than a report is the scope
# phrase, so that is what this matches — a state verb followed, close by, by a
# universal. Kept tight on purpose: the task gate runs first, so this only ever
# sees statements, but a loose version here would re-flood the ledger with
# narration and the standing-decisions block is injected into every agent.
_CONVENTION = re.compile(
    r"\b(?:uses?|stays?|remains?|goes?|lives?|sits?)\b[^.]{0,60}?"
    r"\b(?:for all|across all|throughout|everywhere|as standard|in every)\b", re.I)

# An imperative TASK — work to do, not a choice already made.
#
# The `decisions` column has been used as a dumping ground for project
# next-steps: "HAT Dashboard — _next: Review reactive architecture" had been
# restated 551 times. Loosening the filter above would let every one of those
# back in, so the task shape is now rejected explicitly rather than relied on
# to fail the decision test by accident. French included — the RCA/FOCAL
# sessions are written in it.
_TASK_SHAPED = re.compile(
    r"^\s*(?:to\s+)?(?:complete|finish|fill|obtain|validate|review|rewrite|"
    r"update|add|fix|write|send|check|provide|draft|prepare|create|build|"
    r"implement|investigate|follow up|revoir|valider|compl[ée]ter|obtenir|"
    r"fournir|r[ée]diger|v[ée]rifier|mettre)\b", re.I)


def _is_decision(s: str) -> bool:
    """A decision states a CHOICE — made, or standing. A task states work.

    Three gates, in this order: an imperative task is out however it is phrased,
    a next-step marker is out, and what remains qualifies if it either narrates
    a choice or states a rule.
    """
    if _TASK_SHAPED.search(s or ""):
        return False
    if _NEXT_STEP.search(s):
        return False
    return bool(_DECISION_SHAPED.search(s) or _NORMATIVE.search(s)
                or _CONVENTION.search(s))


# ── Attribution: which specialist should CARRY a promoted decision ───────────
#
# Moved here from tools/mine_decisions.py (2026-09-14) so there is ONE author.
# The miner was a manual CLI, so the promotion step ran only when someone
# remembered to type the command — which, in practice, was almost never. The
# logic now lives in the package, the CLI calls it, and so do the dashboard's
# evening job and the MCP server's opportunistic learning loop. A researcher who
# only ever opens Claude Desktop gets the same learning as one who opens the
# dashboard every day.
#
# Attribution is keyword-based and deliberately CONSERVATIVE. A decision is only
# useful if it reaches the specialist that acts on it, and a wrong attribution is
# worse than none: it hides the rule from the agent that needed it AND clutters
# one that does not. Anything that cannot be placed confidently becomes
# project-wide, where every agent sees it.
# ORDER IS THE WHOLE DESIGN HERE: first match wins, so a narrow rule must sit
# above the broad one that would otherwise swallow it. Several pairs below share
# vocabulary on purpose and are separated by what the decision is ABOUT, not by
# which words it uses:
#
#   sensitive data vs a dataset      · protection rule vs cleaning rule
#   implementing a method vs choosing one
#   building a knowledge layer vs curating the literature
#   what a panel measures vs how it looks
#
# Anything this table cannot name is filed project-wide, which sounds harmless
# and is not: a decision nobody owns is inherited by nobody. That was the state
# for eighteen specialists — unreachable by construction rather than for want of
# history — and it is why a third of the table had no owner.
#
# Deliberately absent: the router itself (a decision "for" it is project-wide by
# definition), specialists retired from automatic routing, and one domain that is
# reached by name only, by standing instruction, rather than on a keyword.
_ATTRIBUTION_ROUTE = [
    # ── narrow rules first ───────────────────────────────────────────────────
    (r"\bPII\b|patient data|sensitive data|de-identif|anonymis|anonymiz|gdpr|"
     r"confidential|personal data|identifiable", "data-guardian", "process"),
    (r"prompt injection|malicious|threat intel|allowlist|blocklist|credential|"
     r"\bsecret\b|exfiltrat|sandbox|vulnerab", "cybersecurity", "process"),
    (r"\bR package\b|CRAN|simulation study|monte carlo|bootstrap|tolerance "
     r"interval|dose-response|custom estimator", "biostatistician", "method"),
    (r"knowledge layer|\bRAG\b|embedding|corpus build|background pack|"
     r"specialist context|vector index", "background-maker", "architecture"),
    (r"scrape|harvest|extract from|youtube|web page|docx|crawl",
     "content-harvester", "process"),
    (r"\bKPI\b|indicator|coverage gap|positivity|case-finding rate|"
     r"surveillance panel|blank panel|data quality panel",
     "dashboard-engineer", "method"),
    (r"design audit|design critique|reverse-engineer the design|ui audit",
     "design-auditor", "design"),
    (r"\bCV\b|cover letter|fellowship|job application|EPSO|career|"
     r"interview prep", "career-coach", "process"),
    (r"capability gap|new agent needed|missing specialist|agent roster",
     "hr-talent", "process"),
    (r"verify the output|second opinion|challenge the|quality check|"
     r"fact-check|adversarial review", "critic", "process"),
    (r"consolidat|memory palace|episodic|semantic memory|memory health|"
     r"session summary", "memory-curator", "architecture"),
    (r"study plan|what to study|skill progression|competenc|learning path",
     "learning-coach", "process"),
    (r"new app|greenfield|scaffold a|multi-agent workflow|new project "
     r"architecture", "builder", "architecture"),
    # ── broader rules below ──────────────────────────────────────────────────
    (r"slide|deck\b|powerpoint|pptx|speaker note|master slide|title slide|"
     r"presentation|bandeau|template de", "presentation-maker", "design"),
    (r"figure|chart|ggplot|plotly|diagram|axis|legend|colour scale|color scale|"
     r"visualis|visualiz", "visualization-maker", "design"),
    (r"palette|css|colour|color|layout|macro|navbar|surface|tab\b|ui\b|"
     r"dashboard look|typograph|token|contrast|accessib|wcag",
     "frontend-designer-builder", "design"),
    (r"\bDB\b|database|sqlite|wal\b|onedrive|flock|lock|port |supervisor|"
     r"install|venv|schema|migration|hook|crash|restart", "software-engineer", "architecture"),
    (r"raster|cost-distance|vector|kriging|spatial|multilevel|model\b|"
     r"estimat|sample size|power|statistic", "methods-coach", "method"),
    (r"corpus|library|zotero|literature|paper|citation|doi|index", "librarian", "library"),
    (r"study design|case definition|surveillance|bias|epidemi|screening|"
     r"case-finding|denominator", "epidemiologist", "method"),
    (r"village|dataset|clean|column|one-row|record linkage|merge", "data-analyst", "method"),
    (r"repo|push|remote|base shell|release|changelog|version", "release-coordinator", "process"),
    (r"meeting|minutes|attendee|agenda|action item", "meeting-memory", "process"),
    (r"thesis|dissertation|article \d|chapter|backbone", "phd-architect", "process"),
    (r"news|feed|rss|brief|signal|outbreak alert", "news-radar", "process"),
    (r"prompt|persona|voice|tone|marker|reply|writing|prose", "writing-partner", "writing"),
    (r"\bMCP\b|tool|agent|routing|subset|token", "rc-builder", "architecture"),
    (r"course|lesson|quiz|curriculum|teach|flashcard|spaced repetition",
     "course-builder", "process"),
]


def attribute(text: str) -> tuple[str, str]:
    """(agent_slug, category) for a decision. Empty slug = project-wide."""
    low = (text or "").lower()
    for pat, slug, cat in _ATTRIBUTION_ROUTE:
        if re.search(pat, low, re.I):
            return slug, cat
    return "", "process"


def promote_standing_decisions(dry_run: bool = False) -> dict:
    """Promote decision-shaped statements out of session summaries into
    `user_decisions`, attributed to the specialist that should apply them.

    Idempotent: a statement already stored (by normalised fingerprint, and by its
    first eight meaningful tokens, which catches re-statements that differ only
    in trailing words) is skipped, so re-running is a no-op rather than a
    duplicator.

    Returns counts for the caller to log.
    """
    from metis_mcp.tools.agent_memory import _ensure as _ensure_user_decisions
    with connect(paths.db) as con:
        _ensure_user_decisions(con)   # one author for the table shape
        raw: list[str] = []
        for (d,) in con.execute(
                "SELECT decisions FROM session_summaries "
                "WHERE COALESCE(decisions,'') NOT IN ('','[]')"):
            raw += _iter_decisions(d)
        raw = [str(x).strip() for x in raw if str(x).strip()]

        existing = {_fingerprint(r[0]) for r in
                    con.execute("SELECT decision FROM user_decisions")}

        picked: dict[str, str] = {}
        for stmt in dict.fromkeys(raw):
            if len(stmt) < 8 or not _is_decision(stmt):
                continue
            fp = _fingerprint(stmt)
            if fp in existing or fp in picked:
                continue
            short = " ".join(fp.split()[:8])
            if any(" ".join(_fingerprint(v).split()[:8]) == short for v in picked.values()):
                continue
            picked[fp] = stmt

        by_agent: dict[str, int] = {}
        for stmt in picked.values():
            slug, cat = attribute(stmt)
            by_agent[slug or "(project-wide)"] = by_agent.get(slug or "(project-wide)", 0) + 1
            if not dry_run:
                con.execute(
                    "INSERT INTO user_decisions (category, decision, context, scope, "
                    "source, hits, created_at, agent_slug) "
                    "VALUES (?,?,?,'always','mined',0,datetime('now'),?)",
                    (cat, stmt[:900],
                     "Promoted from a session summary by promote_standing_decisions()",
                     slug))
        if not dry_run:
            con.commit()
        total = con.execute("SELECT COUNT(*) FROM user_decisions").fetchone()[0]

    return {"raw": len(raw), "unique": len(dict.fromkeys(raw)),
            "promoted": len(picked), "written": 0 if dry_run else len(picked),
            "by_agent": by_agent, "total_rows": total, "dry_run": dry_run}


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
