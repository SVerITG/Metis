"""Master /metis interaction pipeline.

Implements the 11-stage pipeline that runs on every /metis invocation:

  Stage  1 — session_bootstrap        Find or create a session
  Stage  2 — Content classification   Inline (PUBLIC/INTERNAL/CONFIDENTIAL/SENSITIVE)
  Stage  3 — Data Guardian intercept  Block SENSITIVE; warn CONFIDENTIAL
  Stage  4 — Cybersecurity intercept  Block prompt injection + suspicious URLs
  Stage  5 — Intent parsing           Deterministic agent + complexity routing
  Stage  6 — Token budget             Model selection per complexity level
  Stage  7 — Surgical context         Minimum context from memory_entries
  Stage  8 — save_session_event       Write-through persistence (also MCP tool)
  Stage  9 — Output red-line check    Runs inside evaluate_against_layers(), the only
                                      function that receives the drafted answer. (It
                                      previously lived here as its own stage and was
                                      never called by anything — see that function.)
  Stage 10 — Logging                  Delegated to log_agent_run() in agents.py
  Stage 11 — Self-improvement         Delegated to write_reflexion() in self_improvement.py

Public MCP tools: session_bootstrap, save_session_event, run_metis
"""

import datetime
import json
import logging
import re
import socket
import struct
from uuid import uuid4

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

# stderr logger — stdout belongs to the MCP stdio channel.
log = logging.getLogger("metis.pipeline")

# Single shared PII scanner from the safety module (no circular dependency).
# Importing scan_content (not the individual patterns) keeps the Data Guardian
# and the check_data_safety tool permanently in sync.
from metis_mcp.tools.safety import scan_content  # noqa: E402
from metis_mcp.models import model_for

# ── Table DDL (created on first use) ─────────────────────────────────────────

_SESSIONS_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
  session_id  TEXT PRIMARY KEY,
  client      TEXT DEFAULT 'code',
  computer    TEXT DEFAULT '',
  started_at  TEXT NOT NULL,
  last_active TEXT NOT NULL,
  summary     TEXT DEFAULT ''
)
"""

_SESSION_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS session_events (
  event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  content    TEXT NOT NULL,
  created_at TEXT NOT NULL
)
"""

_SESSION_CONTEXT_DDL = """
CREATE TABLE IF NOT EXISTS session_context (
  context_id   TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL,
  context_type TEXT NOT NULL,
  label        TEXT NOT NULL,
  updated_at   TEXT NOT NULL
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


def _ensure_pipeline_tables() -> None:
    with connect(paths.db) as con:
        con.execute(_SESSIONS_DDL)
        con.execute(_SESSION_EVENTS_DDL)
        con.execute(_SESSION_CONTEXT_DDL)
        con.execute(_REFLEXION_DDL)
        con.commit()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── Stage 8 helper: synchronous event write ───────────────────────────────────

def _write_event_sync(session_id: str, event_type: str, content: str) -> None:
    """Write an event synchronously. Used internally by pipeline stages.

    Never raises — a logging failure must not block the pipeline.
    """
    if not session_id:
        return
    try:
        with connect(paths.db) as con:
            con.execute(_SESSION_EVENTS_DDL)
            con.execute(
                """INSERT INTO session_events (session_id, event_type, content, created_at)
                   VALUES (?, ?, ?, ?)""",
                (session_id, event_type, content[:2000], _now()),
            )
            con.commit()
    except Exception as e:
        # Still never raises — but a dropped event is no longer invisible. The
        # 'redline' events written here ARE the Data Guardian / Cybersecurity
        # audit trail: losing them silently means the block happened and left no
        # record, which is indistinguishable from the guard never running.
        level = logging.ERROR if event_type == "redline" else logging.WARNING
        log.log(
            level,
            "SESSION EVENT NOT PERSISTED (type=%s, session=%s): %s: %s",
            event_type, session_id[:8], type(e).__name__, e,
        )


# ── Stage 1: session_bootstrap ───────────────────────────────────────────────

def _maybe_run_learning_loop() -> None:
    """S.6 — run the reflexion→improvement loop opportunistically, at most once
    per ~20h, from the MCP server. The nightly aggregation/consolidation/drafting
    normally lives in the dashboard's APScheduler, so a Claude-Desktop-only user
    who never opens the dashboard would accumulate reflexions that never became
    learning. Triggering it here (throttled, best-effort) closes that gap without
    blocking or ever failing a session bootstrap.
    """
    try:
        with connect(paths.db) as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS learning_loop_state "
                "(id INTEGER PRIMARY KEY CHECK(id=1), last_run TEXT)"
            )
            row = con.execute(
                "SELECT last_run FROM learning_loop_state WHERE id=1"
            ).fetchone()
            last_run = row["last_run"] if row else None
            if last_run:
                try:
                    lr = datetime.datetime.fromisoformat(last_run)
                    if lr.tzinfo is None:
                        lr = lr.replace(tzinfo=datetime.timezone.utc)
                    if (datetime.datetime.now(datetime.timezone.utc) - lr) < datetime.timedelta(hours=20):
                        return  # ran recently — skip
                except Exception:
                    pass
            # Claim the slot up front so concurrent bootstraps don't double-run.
            con.execute(
                "INSERT INTO learning_loop_state (id, last_run) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET last_run=excluded.last_run",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(),),
            )
            con.commit()
    except Exception:
        return

    # Heavy work outside the connection — mirrors the dashboard scheduler's
    # evening job so behaviour is identical whoever triggers it.
    try:
        from metis_mcp.tools.improvement import (
            aggregate_reflexions,
            consolidate_reflexions,
            draft_self_improvement_proposal,
        )
        # Same first step as the dashboard's evening job: turn what the session
        # summaries recorded into standing decisions the specialists actually
        # receive. A Claude-Desktop-only user never opens the dashboard, so
        # without this the learning loop ran and the learning never landed.
        try:
            from metis_mcp.tools.decisions_ledger import promote_standing_decisions
            promote_standing_decisions()
        except Exception as _exc:
            log.warning("[pipeline] decision promotion skipped: %s", _exc)
        result = aggregate_reflexions()
        agents = result.get("agents", []) if isinstance(result, dict) else []
        consolidate_reflexions()
        try:
            with connect(paths.db) as con:
                open_slugs = {
                    r[0] for r in con.execute(
                        "SELECT DISTINCT agent_slug FROM skill_improvement_proposals "
                        "WHERE status IN ('draft','pending')"
                    ).fetchall()
                }
        except Exception:
            open_slugs = set()
        for _a in (agents or [])[:8]:
            slug = (
                _a.get("agent_slug") or _a.get("slug") or _a.get("agent") or _a.get("name")
            ) if isinstance(_a, dict) else None
            if slug and slug not in open_slugs:
                try:
                    draft_self_improvement_proposal(slug)
                except Exception:
                    pass
    except Exception as exc:
        log.warning("[pipeline] opportunistic learning loop skipped: %s", exc)


@app.tool()
async def session_bootstrap(client: str = "code") -> list[TextContent]:
    """Stage 1: Find or create a session for the current computer.

    Checks for an active session (same computer, last active within 2 hours).
    If found: resumes it and returns the last 5 events.
    If not: creates a new session and seeds context from recent memory.

    Args:
        client: Which Claude client is calling ('code'|'chat'|'cowork'|'dashboard').
    """
    _ensure_pipeline_tables()
    # S.6 — Desktop-only users get the learning loop too. Started off-thread via
    # ambient rather than inline: this loop can call the Claude API to draft
    # proposals, and a bootstrap that blocks for seconds is a bootstrap the user
    # learns to avoid. (Ambient also starts it on the first tool call of any
    # session, so it no longer depends on bootstrap being reached at all.)
    try:
        from metis_mcp import ambient

        ambient._start_learning_loop_once()
    except Exception:
        _maybe_run_learning_loop()
    computer = socket.gethostname()
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    ).isoformat()

    with connect(paths.db) as con:
        row = con.execute(
            """SELECT session_id, started_at, last_active, summary
               FROM sessions
               WHERE computer = ? AND last_active > ?
               ORDER BY last_active DESC LIMIT 1""",
            (computer, cutoff),
        ).fetchone()

        if row:
            session_id = row["session_id"]
            is_new = False
            con.execute(
                "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                (_now(), session_id),
            )
            events = con.execute(
                """SELECT event_type, content, created_at FROM session_events
                   WHERE session_id = ? ORDER BY event_id DESC LIMIT 5""",
                (session_id,),
            ).fetchall()
            memory_snapshot = [
                {
                    "type": e["event_type"],
                    "content": e["content"][:200],
                    "at": e["created_at"],
                }
                for e in reversed(events)
            ]
            con.commit()
        else:
            session_id = str(uuid4())
            is_new = True
            con.execute(
                """INSERT INTO sessions (session_id, client, computer, started_at, last_active)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, client, computer, _now(), _now()),
            )
            con.commit()
            # Seed with recent memory entries
            try:
                mem_rows = con.execute(
                    """SELECT title, summary, entry_type FROM memory_entries
                       ORDER BY created_at DESC LIMIT 5""",
                ).fetchall()
                memory_snapshot = [
                    {
                        "type": m["entry_type"],
                        "title": m["title"],
                        "summary": (m["summary"] or "")[:150],
                    }
                    for m in mem_rows
                ]
            except Exception:
                memory_snapshot = []

    # ── Implementation-plan change detector ──────────────────────────────────
    plan_status: dict = {}
    try:
        plan_path = paths.root / "system" / "config" / "implementation-progress.json"
        if plan_path.exists():
            import time as _time
            plan_mtime = plan_path.stat().st_mtime

            # Find when the previous session ended (last_active before this one)
            with connect(paths.db) as _con:
                prev = _con.execute(
                    """SELECT last_active FROM sessions
                       WHERE computer = ? AND session_id != ?
                       ORDER BY last_active DESC LIMIT 1""",
                    (computer, session_id),
                ).fetchone()
            prev_ts = float(prev["last_active"].replace("Z", "+00:00").split("+")[0]
                            .replace("T", " ")) if prev else 0.0
            try:
                import datetime as _dt
                prev_dt = _dt.datetime.fromisoformat(prev["last_active"]) if prev else None
                prev_epoch = prev_dt.timestamp() if prev_dt else 0.0
            except Exception:
                prev_epoch = 0.0

            plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            meta = plan_data.get("_meta", {})

            plan_status = {
                "last_updated": meta.get("last_updated", ""),
                "last_phase_completed": meta.get("last_phase_completed", ""),
                "changed_since_last_session": plan_mtime > prev_epoch and prev_epoch > 0,
            }
    except Exception:
        pass

    # ── Deep memory context (recall-powered) ────────────────────────────────
    # Surface semantically relevant memories — not just the most recent ones.
    # This is what makes Claude Desktop sessions feel "deep" instead of shallow.
    deep_context: list[dict] = []
    recent_decisions: list[str] = []
    try:
        # Load user profile interests for semantic search
        profile_path = paths.root / "system" / "config" / "user-config.yaml"
        interests_query = ""
        if profile_path.exists():
            import yaml
            cfg = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
            interests = cfg.get("interests", [])
            if interests:
                interests_query = ", ".join(interests[:5])

        if interests_query:
            # Search across vector memory layers for relevant long-term context
            try:
                from metis_mcp.embeddings import embed_query
                query_vec = embed_query(interests_query)
                vec_bytes = struct.pack(f"{len(query_vec)}f", *query_vec)

                with connect(paths.db) as _con:
                    try:
                        import sqlite_vec
                        _con.enable_load_extension(True)
                        sqlite_vec.load(_con)
                        _con.enable_load_extension(False)
                    except Exception:
                        raise ImportError("sqlite_vec")

                    # Semantic memory (concepts)
                    sem_rows = _con.execute(
                        """SELECT s.concept, s.definition, s.created_at
                           FROM vec_semantic v
                           JOIN semantic_memory s ON s.id = v.rowid
                           WHERE v.embedding MATCH ? AND k = 3
                           ORDER BY v.distance""",
                        (vec_bytes,),
                    ).fetchall()
                    for r in sem_rows:
                        deep_context.append({
                            "layer": "semantic",
                            "title": r["concept"],
                            "preview": (r["definition"] or "")[:150],
                        })

                    # Episodic memory (recent events)
                    epi_rows = _con.execute(
                        """SELECT e.content, e.event_type, e.created_at
                           FROM vec_episodic v
                           JOIN episodic_memory e ON e.id = v.rowid
                           WHERE v.embedding MATCH ? AND k = 3
                           ORDER BY v.distance""",
                        (vec_bytes,),
                    ).fetchall()
                    for r in epi_rows:
                        deep_context.append({
                            "layer": "episodic",
                            "type": r["event_type"],
                            "preview": (r["content"] or "")[:150],
                        })
            except (ImportError, Exception):
                pass

        # Extract recent session decisions (avoid re-asking)
        with connect(paths.db) as _con:
            try:
                dec_rows = _con.execute(
                    """SELECT decisions, key_topics
                       FROM session_summaries
                       WHERE decisions != '' AND decisions IS NOT NULL
                       ORDER BY created_at DESC LIMIT 3""",
                ).fetchall()
                for r in dec_rows:
                    if r["decisions"]:
                        recent_decisions.append(r["decisions"][:200])
            except Exception:
                pass

    except Exception:
        pass

    result = {
        "session_id": session_id,
        "is_new": is_new,
        "computer": computer,
        "memory_snapshot": memory_snapshot,
        "deep_context": deep_context[:6],
        "recent_decisions": recent_decisions[:3],
        "plan_status": plan_status,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ── Stage 3: Data Guardian intercept ──────────────────────────────────────────

def _scan_safety(content: str) -> dict:
    """Run the shared PII scanner. Returns {safe, classification, warnings}.

    Delegates to safety.scan_content so the Data Guardian sees every pattern
    (names, DOB, passport, medical record numbers, national ID numbers,
    sensitive CSV headers, plus any field-specific patterns from the local
    override file) — not just the original five.
    """
    return scan_content(content)


async def _check_data_safety_stage(request: str, session_id: str) -> dict:
    """Stage 3: Data Guardian intercept."""
    result = _scan_safety(request)
    if result["classification"] in ("SENSITIVE", "CONFIDENTIAL"):
        _write_event_sync(
            session_id,
            "redline",
            f"Data Guardian: {result['classification']} — {result['warnings']}",
        )
    return result


# ── Stage 4: Cybersecurity intercept ──────────────────────────────────────────

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
# Override language — the part of an injection that tries to REPLACE the
# standing instructions. This is the signal; a persona request on its own is not.
_OVERRIDE_CUE = (r"(?:previous|prior|above|earlier|all)\s+(?:instructions?|prompts?|rules?)"
                 r"|system\s+prompt|your\s+(?:instructions?|rules?|guidelines?)"
                 r"|unfiltered|jailbreak|developer\s+mode|no\s+restrictions?"
                 r"|without\s+(?:any\s+)?(?:restrictions?|limits?|filters?)")

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(rf"you\s+are\s+now\s+a\s+.{{0,80}}?(?:{_OVERRIDE_CUE})", re.IGNORECASE),
    # A ROLE REQUEST IS NOT AN ATTACK (audit 2026-09-14).
    #
    # This pattern used to be a bare `act\s+as\s+a\s+`, and it matched "act as
    # a critic" — an ordinary thing to ask a research assistant, and one of the
    # few phrasings that would otherwise have reached the `critic` specialist.
    # The intercept is a HARD RETURN from run_metis, so the false positive did
    # not merely mislabel the request, it made an entire class of phrasing unable
    # to reach any agent at all.
    #
    # A persona request only looks like an injection when it also tries to
    # displace the standing instructions, so that co-occurrence is what is
    # matched now: "act as an unfiltered AI and ignore your guidelines" still
    # trips; "act as a critic and review my numbers" does not.
    re.compile(rf"act\s+as\s+(?:if\s+you\s+(?:were|are)\s+)?an?\s+.{{0,80}}?"
               rf"(?:{_OVERRIDE_CUE})", re.IGNORECASE),
    re.compile(rf"(?:{_OVERRIDE_CUE}).{{0,80}}?\bact\s+as\s+an?\s+", re.IGNORECASE),
]
# Zero-width chars commonly used to hide injection text
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")
_BLOCKLISTED_DOMAINS = frozenset({
    "pastebin.com", "hastebin.com", "ghostbin.com",
    "ngrok.io", "webhook.site", "requestbin.com",
})


async def _cybersecurity_stage(request: str, session_id: str) -> dict:
    """Stage 4: Scan for prompt injection patterns and suspicious URLs."""
    threats: list[str] = []

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(request):
            threats.append(f"Potential prompt injection: «{pattern.pattern}»")

    if _ZERO_WIDTH_RE.search(request):
        threats.append("Zero-width/invisible characters detected — possible hidden injection text")

    for url in _URL_RE.findall(request):
        try:
            domain = url.split("//", 1)[1].split("/")[0].lower().lstrip("www.")
        except IndexError:
            domain = ""
        if domain in _BLOCKLISTED_DOMAINS:
            threats.append(f"Blocklisted domain in URL: {domain}")

    if threats:
        _write_event_sync(session_id, "redline",
                          f"Cybersecurity intercept: {'; '.join(threats)}")

    return {"safe": len(threats) == 0, "threats": threats}


# ── Stage 5: Intent parsing ───────────────────────────────────────────────────

# Routing is DATA, not CODE. Rules live in `agent_routing_rules` (part of the
# user's institutional memory — persists across Metis CODE updates, stays on the
# user's machine). Metis ships EMPTY of user data; this table is SEEDED with
# sensible defaults on first run, then accumulates user-LEARNED rules via
# record_routing_preference() ("should I always route X to agent Y?"). Matching
# is word-boundary (so 'ui' no longer matches inside 'build') and most-specific
# first (low `priority` wins), so a broad keyword can't steal a specialist.
#
# (keywords, agent_slug, task_type, priority) — priority asc.
# ── Routing seeds ─────────────────────────────────────────────────────────────
#
# PRIORITY BELONGS TO THE KEYWORD, NOT THE AGENT  (audit 2026-09-14)
#
# Until now a priority was set per agent and every keyword in that agent's list
# inherited it. That put generic English words at specialist precedence, and it
# is the mechanism behind every mis-route the audit reproduced:
#
#   "clean"      sat at 12 — ahead of software-engineer (25), writing-partner (30)
#                and librarian (35). Any request about cleaning ANYTHING went to
#                the tabular-data agent: a paper to fetch, a slide background.
#   "curriculum" sat at 12 for course-builder, 33 points ahead of the
#                learning-architect whose own vocabulary it is.
#   "layout"     sat at 40 for ux-engineer, ahead of the frontend-designer-builder
#                that replaced it.
#
# So a keyword may now carry its own priority: write it as ("word", priority).
# A bare string keeps the group's default. Two bands do the work:
#
#   5-20   DISTINCTIVE — the word means this specialist and essentially nothing
#          else ("dhis2", "powerpoint", "satscan"). Safe to place first.
#   45-70  GENERIC — a common English word that merely CO-OCCURS with the domain
#          ("clean", "chart", "feed", "bug"). It must lose to any distinctive
#          word elsewhere in the request, and it exists only so that a request
#          containing nothing better still lands somewhere sensible.
#
# When editing: ask "would this word appear in a request that is NOT for this
# agent?". If yes, it belongs in the generic band however central it feels.
#
# (keywords, agent_slug, task_type, default_priority)
_DEFAULT_ROUTING_SEED: list[tuple[list, str, str, int]] = [
    # ── domain specialists ───────────────────────────────────────────────────
    (["dhis2", "tracker program", "data element", "org unit", "organisation unit",
      "program stage"], "dhis2-expert", "dhis2", 10),

    (["study design", "selection bias", "confounding", "case definition",
      "surveillance evaluation", "diagnostic accuracy", "satscan", "spatial scan",
      "case-control", "denominator", "loss to follow-up", "ltfu",
      ("outbreak", 25), ("surveillance", 35), ("screening", 45)],
     "epidemiologist", "epi", 10),

    (["monte carlo", "simulation study", "r package", "tolerance interval",
      "dose-response", "parametric bootstrap", "cran"],
     "biostatistician", "biostat", 12),

    # "clean"/"dataset"/"csv" are generic: a request mentioning them is usually
    # ABOUT something else. The distinctive ones are the file formats.
    (["spss", "stata", ("excel", 20), ("csv", 30), "data profiling", "record linkage",
      ("duplicates", 45), ("missing values", 30), ("outlier", 45),
      ("dataset", 55), ("clean", 65)],
     "data-analyst", "data", 20),

    (["build a course", "course outline", "module design", "lesson plan",
      "learning objectives", "curriculum", "competency map", "backward design",
      "instructional design", "bloom", "spaced repetition", "learning path",
      "study plan", "what to study", "learning progression", "lesson",
      ("competency", 45), ("course", 55)],
     "course-builder", "course", 14),

    (["ggplot", "plotly", "system map", "figure for", "visualise", "visualize",
      ("diagram", 25), ("chart", 45), ("map ", 55)],
     "visualization-maker", "viz", 12),

    (["scrape", "youtube", "github readme", "pdf content", "harvest",
      "extract the text", "pull the content", "full text", "full-text",
      ("fetch", 40)],
     "content-harvester", "harvest", 15),

    (["knowledge layer", "background corpus", "build corpus", "index domain",
      "background pack", "specialist knowledge", ("rag", 25)],
     "background-maker", "background", 15),

    (["powerpoint", "speaker notes", "slide deck", "master slide", "pptx",
      ("presentation", 20), ("slide", 25), ("deck", 30)],
     "presentation-maker", "slides", 10),

    (["cover letter", "job application", "fellowship", "interview prep",
      "job description", "vacancy", "postdoc", ("career", 25), ("my cv", 12)],
     "career-coach", "career", 18),

    # ── research / writing ───────────────────────────────────────────────────
    (["thesis", "dissertation", "article 1", "article 2", "article 3",
      ("chapter", 35), ("phd", 30), ("article", 55)],
     "phd-architect", "phd", 20),

    (["research programme", "research program", "article state",
      "journal-readiness", "target journal", "draft status", "article tracker",
      "planning.md", "tracked yet", ("tracked", 30)],
     "research-architect", "research", 18),

    (["meeting", "transcript", "attendee", "agenda", "minutes of",
      "we agree", "did we agree", "agreed with"],
     "meeting-memory", "meeting", 25),

    (["fastapi", "stack trace", "shiny", "r script", "python script", "refactor",
      "traceback", "unit test", "pytest", "gitignore", "untrack",
      ("debug", 35), ("bug", 45), ("git", 55)],
     "software-engineer", "code", 20),

    (["multilevel", "icc", "random effects", "poisson", "bayesian",
      "logistic regression", "survival analysis", "propensity score",
      "overdispersion", "sample size", "power calculation",
      ("regression", 35), ("sampling", 50), ("prevalence", 50), ("statistic", 55)],
     "methods-coach", "methods", 22),

    (["manuscript", "strobe", "consort", "prisma", "methods section",
      "argument flow", "grant writing", ("prose", 35), ("paragraph", 40),
      ("grammar", 35), ("abstract", 45), ("introduction", 50), ("revise", 50)],
     "writing-partner", "writing", 25),

    (["pubmed", "zotero", "systematic review", "annotated bibliography",
      "bibliography", "citation", "cite", "citing", "cited", "references for",
      ("literature", 30), ("paper", 45), ("reference", 50)],
     "librarian", "literature", 28),

    (["news alert", "outbreak news", "who announcement", "world events",
      "what happened", "policy shift", "rss", "news pipeline", "breaking",
      ("announcement", 40), ("briefing", 45), ("news", 45), ("feed", 65)],
     "news-radar", "news", 30),

    (["patient data", "pii", "gdpr", "de-identif", "anonymis", "identifiable",
      "personal data"],
     "data-guardian", "safety", 30),

    (["brainstorm", "connect ideas", "cross-pollinate", "explore connections"],
     "metis", "idea", 50),
]

# How many specialists one request may put to work. Three is the point past
# which a plain-English "who is on this" line stops being readable to someone
# who does not know the agent roster.
_MAX_ROUTED_AGENTS = 3

# Keywords in the GENERIC band. When one of these is the ONLY thing that routed a
# request, the embedding router is allowed to overrule it (stage 5). A word that
# merely co-occurs with a domain is a weak signal and should lose to a strong one.
_GENERIC_PRIORITY_FLOOR = 45

_DEEP_KEYWORDS = ["review", "critique", "analyse", "analyze", "evaluate", "challenge", "assess"]
_QUICK_KEYWORDS = ["find", "get", "what is", "list", "show", "check", "status", "how many"]
_CHAIN_KEYWORDS = ["and also", "then review", "both", "multiple agents", "all three"]

# Back-compat alias for older imports expecting (keywords, agent, task_type) triples.
_ROUTING_TABLE = [([k if isinstance(k, str) else k[0] for k in kws], agent, t)
                  for kws, agent, t, _p in _DEFAULT_ROUTING_SEED]


# Agents the original seed could not reach by keyword at all.
#
# PHRASES ARE WRITTEN THE WAY THE RESEARCHER TYPES, NOT THE WAY THE SYSTEM
# THINKS (audit 2026-09-14). The previous seeds for these agents were mostly
# DEMONSTRATIVES — "verify this", "challenge this", "do we need an agent" —
# phrases that presuppose an attached object. Nobody types "verify this" as a
# sentence; they type "verify whether the numbers in Article 4 hold up", which
# the keyword cannot match. That, not a missing rule, is why `critic` had four
# rules and zero lifetime matches.
_COVERAGE_ROUTING_SEED: list[tuple[list, str, str, int]] = [
    # build / extend
    (["extend metis", "modify metis", "new mcp tool", "dashboard phase", "new agent",
      "add a skill", "routing rule"], "rc-builder", "rc", 30),
    (["build an app", "mcp server", "scaffold", "new tool", "greenfield"],
     "builder", "build", 40),
    # ONE front-end agent. frontend-designer-builder/system-prompt.md states it
    # replaces the former dashboard-engineer and ux-engineer; those two kept
    # their rules anyway and outranked it (ux-engineer 40 vs 45), so the
    # successor lost requests to the agents it superseded. Their keywords move
    # here and the two are retired from routing by _RETIRED_ROUTING_SLUGS.
    (["frontend", "front end", "component design", "design system", "css",
      "responsive", "ui design", "htmx", "kpi panel", "blank panel",
      "dashboard tab", "dashboard bug", "jinja", "partial", ("layout", 50),
      ("ux", 45)],
     "frontend-designer-builder", "ui", 32),
    (["design audit", "ui critique", "design review", "audit the interface",
      "accessibility", "contrast ratio", "wcag"],
     "design-auditor", "ui", 30),
    # quality / safety — phrased as a researcher asks for a second pair of eyes
    (["double-check", "second opinion", "sanity check", "poke holes",
      "does this hold up", "is this supported", "internally consistent",
      "unsupported claim", "fact-check", "critique", "critic",
      ("challenge", 50), ("verify", 50)],
     "critic", "verify", 30),
    (["prompt injection", "malicious", "is this link safe", "phishing",
      "exfiltrat", "suspicious url", "security audit"],
     "cybersecurity", "security", 25),
    # knowledge / memory
    (["what did we decide", "consolidate session", "past context",
      "previous session", "what do we know about", "have we worked on",
      "memory health", "close the session", "session notes",
      ("consolidate", 40)],
     "memory-curator", "memory", 30),
    # people / capability
    (["capability gap", "missing specialist", "do we need an agent",
      "job description for", "hire", "recruit", "team assessment"],
     "hr-talent", "hr", 35),
    # research + release
    (["release", "publish", "version bump", "changelog", "push to", "sync repo",
      "pre-publish", "commit scan", "rollback", ("commit", 45)],
     "release-coordinator", "release", 35),
]

# Claude Code's own built-in agents. The researcher asked for these to be
# routable alongside the Metis specialists (2026-08-25). They are marked
# source='claude' so the audit can tell them apart from Metis's own roster, and
# they sit last: a built-in generalist should never outrank a domain specialist.
_CLAUDE_AGENT_SEED: list[tuple[list, str, str, int]] = [
    (["find where", "search the codebase", "where is", "locate the"], "Explore", "explore", 55),
    (["implementation plan", "plan the implementation", "how should i build",
      "architecture for"], "Plan", "plan", 55),
]

# Slugs routing must never return again, and why. Rules for these are DELETED on
# migration (see _migrate_routing_table) rather than left to lose quietly.
#
#   metis-audit-*          — 7 slugs, 14 rules, pointing at nothing. No agent
#                            folder, no .claude/agents file, no skill, no file of
#                            any kind anywhere in the repo.
#   metis-self-reflexion   — a SKILL, not an agent. Routing returned it as an
#   metis-update             agent, so dispatching the routing decision could
#                            only fail. Still reachable as /metis-self-reflexion.
#   ux-engineer            — superseded by frontend-designer-builder, and has no
#   dashboard-engineer       .claude/agents file at all in ux-engineer's case, so
#                            the Agent tool could not run what routing chose.
#   edu-expert             — merged into course-builder; also has no
#   learning-architect       .claude/agents file (edu-expert).
#   news-aggregator        — merged into news-radar; a pipeline, not a viewpoint.
#   learning-coach         — merged into course-builder for ROUTING only; still
#                            invoked directly by the learning surface.
#
# The agents/ folders and .claude/skills entries are deliberately LEFT IN PLACE:
# this retires them from automatic routing, which is reversible, rather than
# deleting work, which is not.
_RETIRED_ROUTING_SLUGS = frozenset({
    "metis-audit-features", "metis-audit-install", "metis-audit-memory",
    "metis-audit-security", "metis-audit-ui", "metis-audit-vision",
    "metis-audit-workflow", "metis-self-reflexion", "metis-update",
    "ux-engineer", "dashboard-engineer", "edu-expert", "learning-architect",
    "news-aggregator", "learning-coach",
})

# Bumped whenever the seeds above change in a way existing installs must adopt.
# The table is seeded ONCE (on an empty table), so without this a priority fix
# shipped in code would never reach a machine whose DB was already seeded — and
# the DB does not sync between the researcher's two computers.
_ROUTING_SEED_VERSION = 4


def _iter_seed(seed) -> list[tuple[str, str, str, int]]:
    """Flatten a seed table to (keyword, agent, task_type, priority).

    A keyword is either a bare string (inherits the group's default priority) or
    a ("word", priority) pair. Priority belongs to the WORD — see the seed header.
    """
    out: list[tuple[str, str, str, int]] = []
    for kws, agent, t, default_prio in seed:
        for kw in kws:
            if isinstance(kw, (tuple, list)):
                out.append((str(kw[0]).lower(), agent, t, int(kw[1])))
            else:
                out.append((str(kw).lower(), agent, t, int(default_prio)))
    return out


def _migrate_routing_table(con) -> None:
    """Bring an already-seeded install up to the current seed version.

    The table is seeded only when EMPTY, so before this existed a priority fix
    shipped in code reached a fresh install and no one else. That mattered more
    than it sounds: the routing DB is machine-local and does not sync, so the
    researcher's two computers would have diverged permanently.

    Three things happen, in this order, and each is idempotent:
      1. Rules for retired slugs are DELETED (they point at agents that no longer
         exist, or at skills that were never dispatchable as agents).
      2. Seed-sourced rules are re-priced and re-pointed to match the code.
      3. New seed keywords are inserted.

    `source='user'` rules are never touched. A preference the researcher taught
    Metis outranks anything shipped, which is the whole point of the table being
    data rather than code.
    """
    row = con.execute(
        "SELECT value FROM metis_meta WHERE key = 'routing_seed_version'"
    ).fetchone()
    current = int(row[0]) if row and str(row[0]).isdigit() else 0
    if current >= _ROUTING_SEED_VERSION:
        return

    if _RETIRED_ROUTING_SLUGS:
        placeholders = ",".join("?" * len(_RETIRED_ROUTING_SLUGS))
        con.execute(
            f"DELETE FROM agent_routing_rules WHERE agent_slug IN ({placeholders}) "
            "AND source <> 'user'",
            tuple(_RETIRED_ROUTING_SLUGS),
        )

    for seed, src in ((_DEFAULT_ROUTING_SEED, "seed"),
                      (_COVERAGE_ROUTING_SEED, "seed"),
                      (_CLAUDE_AGENT_SEED, "claude")):
        for kw, agent, t, prio in _iter_seed(seed):
            # A keyword may have moved to a different agent (ux-engineer's
            # "layout" now belongs to frontend-designer-builder), so re-point as
            # well as re-price. UNIQUE is (keyword, agent_slug), so the old row
            # is removed rather than updated in place.
            con.execute(
                "DELETE FROM agent_routing_rules WHERE keyword = ? "
                "AND agent_slug <> ? AND source <> 'user'", (kw, agent))
            con.execute(
                "INSERT INTO agent_routing_rules "
                "(keyword, agent_slug, task_type, priority, match_mode, source) "
                "VALUES (?, ?, ?, ?, 'word', ?) "
                "ON CONFLICT(keyword, agent_slug) DO UPDATE SET "
                "priority = excluded.priority, task_type = excluded.task_type "
                "WHERE agent_routing_rules.source <> 'user'",
                (kw, agent, t, prio, src),
            )

    con.execute(
        "INSERT INTO metis_meta (key, value) VALUES ('routing_seed_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(_ROUTING_SEED_VERSION),),
    )
    log.info("[pipeline] routing table migrated to seed version %s",
             _ROUTING_SEED_VERSION)
    _audit_routing_targets(con)


def _audit_routing_targets(con) -> None:
    """Warn about routing rules that name something the Agent tool cannot run.

    This check is worth more than the cleanup that prompted it. Three rosters
    had drifted apart and nothing compared them:

        system/config/agent-registry.json   35   what the embedding router sees
        .claude/agents/*.md                 33   what the Agent tool can dispatch
        agent_routing_rules                 46   what routing could return

    So routing could name `ux-engineer` (no subagent file), or one of seven
    `metis-audit-*` slugs that existed in no file anywhere. A routing decision
    that cannot be dispatched fails at the point of use, far from its cause.

    Warnings only, never fatal: an install may legitimately lack a folder, and a
    routing table that refuses to load is worse than one with a stale row.
    """
    try:
        registry: set[str] = set()
        reg_fp = paths.root / "system" / "config" / "agent-registry.json"
        if reg_fp.exists():
            data = json.loads(reg_fp.read_text(encoding="utf-8"))
            entries = data.get("agents", data) if isinstance(data, dict) else data
            registry = {str(a.get("slug", "")) for a in entries if isinstance(a, dict)}

        dispatchable = {fp.stem for fp in (paths.root / ".claude" / "agents").glob("*.md")}
        # An agent folder is the Claude Desktop path (prompts.py builds one MCP
        # prompt per agents/<slug>/system-prompt.md), so an agent reachable there
        # but not in .claude/agents is Desktop-only rather than broken.
        desktop = {d.name for d in paths.agents.iterdir() if d.is_dir()} \
            if paths.agents.is_dir() else set()

        rows = con.execute(
            "SELECT DISTINCT agent_slug, source FROM agent_routing_rules"
        ).fetchall()
        for slug, source in rows:
            if source == "claude":
                continue  # Claude Code built-ins have no Metis-side file by design
            if slug not in registry and slug not in desktop:
                log.warning("[routing] rule points at '%s', which exists in no "
                            "registry, agent folder or subagent file", slug)
            elif slug not in dispatchable and slug not in desktop:
                log.warning("[routing] '%s' is routable but has no .claude/agents "
                            "file — the Agent tool cannot dispatch it", slug)
    except Exception as exc:  # noqa: BLE001 — a check must never break routing
        log.debug("[routing] target audit skipped: %s", exc)


def _ensure_routing_table() -> None:
    """Create + seed the routing table on first run, then migrate it on upgrade.

    Ships empty of user data; seeds are default config. User-learned rules
    accumulate and persist across CODE updates (they live in the data layer,
    never the shipped code)."""
    with connect(paths.db) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS agent_routing_rules ("
            " rule_id INTEGER PRIMARY KEY,"
            " keyword TEXT NOT NULL,"
            " agent_slug TEXT NOT NULL,"
            " task_type TEXT,"
            " priority INTEGER DEFAULT 100,"
            " match_mode TEXT DEFAULT 'word',"
            " source TEXT DEFAULT 'seed',"
            " scope TEXT DEFAULT 'always',"
            " hits INTEGER DEFAULT 0,"
            " created_at TEXT DEFAULT (datetime('now')),"
            " UNIQUE(keyword, agent_slug))"
        )
        con.execute(
            "CREATE TABLE IF NOT EXISTS metis_meta ("
            " key TEXT PRIMARY KEY, value TEXT)"
        )
        # `matches` counts every time a rule's keyword was PRESENT, whether or
        # not it changed the routing. `hits` counts only when it put an agent on
        # the job. The pair is what separates a shadowed rule (matches > 0,
        # hits == 0) from one whose requests never arrive (matches == 0) — the
        # question the 2026-08-25 audit could not answer from `hits` alone.
        cols = {r[1] for r in con.execute("PRAGMA table_info(agent_routing_rules)")}
        if "matches" not in cols:
            con.execute("ALTER TABLE agent_routing_rules ADD COLUMN matches INTEGER DEFAULT 0")

        if con.execute("SELECT COUNT(*) FROM agent_routing_rules").fetchone()[0] == 0:
            for kw, agent, t, prio in _iter_seed(_DEFAULT_ROUTING_SEED):
                con.execute(
                    "INSERT OR IGNORE INTO agent_routing_rules "
                    "(keyword, agent_slug, task_type, priority, match_mode, source) "
                    "VALUES (?, ?, ?, ?, 'word', 'seed')",
                    (kw, agent, t, prio),
                )

        # Coverage top-up, for installs seeded before these agents were routable.
        # Only agents with NO rule at all are topped up, so a rule the user
        # deliberately deleted is never resurrected.
        covered = {r[0] for r in con.execute("SELECT DISTINCT agent_slug FROM agent_routing_rules")}
        for seed, src in ((_COVERAGE_ROUTING_SEED, "seed"), (_CLAUDE_AGENT_SEED, "claude")):
            for kw, agent, t, prio in _iter_seed(seed):
                if agent in covered or agent in _RETIRED_ROUTING_SLUGS:
                    continue
                con.execute(
                    "INSERT OR IGNORE INTO agent_routing_rules "
                    "(keyword, agent_slug, task_type, priority, match_mode, source) "
                    "VALUES (?, ?, ?, ?, 'word', ?)",
                    (kw, agent, t, prio, src),
                )

        _migrate_routing_table(con)
        con.commit()


def _load_routing_rules() -> list[tuple]:
    """(keyword, agent_slug, task_type, match_mode, rule_id, source), most-specific
    first. User-learned rules outrank seeds at equal priority."""
    try:
        _ensure_routing_table()
        with connect(paths.db) as con:
            rows = con.execute(
                "SELECT keyword, agent_slug, task_type, match_mode, rule_id, source, priority "
                "FROM agent_routing_rules WHERE scope = 'always' "
                "ORDER BY priority ASC, (source='user') DESC, length(keyword) DESC"
            ).fetchall()
            # Belt and braces: a retired slug must never route even if this
            # machine has not run the migration yet (Claude Desktop can start
            # the server before the dashboard ever opens).
            return [r for r in rows if r[1] not in _RETIRED_ROUTING_SLUGS]
    except Exception:
        # DB unavailable → fall back to the in-code seed so routing never dies.
        # Sorted by priority so the fallback ranks the same way the table does;
        # an unsorted fallback silently routed by declaration order instead.
        rows = [(kw, agent, t, "word", -1, "seed", prio)
                for kw, agent, t, prio in _iter_seed(_DEFAULT_ROUTING_SEED)]
        rows.sort(key=lambda r: (r[6], -len(r[0])))
        return rows


def _kw_match(keyword: str, text: str, mode: str) -> bool:
    import re
    if mode == "substring":
        return keyword in text
    # Leading word-boundary only: matches the keyword at the start of a word, so
    # "paper" matches "papers"/"papering" (inflections) but "ui" still does NOT
    # match inside "build" (no word-start before the 'ui'). Avoids both the
    # substring over-match and the strict-boundary plural under-match.
    return re.search(r"\b" + re.escape(keyword), text) is not None


_AGENT_ROUTE_VECS = None  # process cache: list[(slug, description_vector)]


def _load_agent_route_vecs():
    """Embed each specialist's registry description once per process (Keystone P3.7)."""
    global _AGENT_ROUTE_VECS
    if _AGENT_ROUTE_VECS is not None:
        return _AGENT_ROUTE_VECS
    vecs = []
    try:
        import json as _json
        from metis_mcp.embeddings import embed_document
        data = _json.loads((paths.root / "system" / "config" / "agent-registry.json").read_text(encoding="utf-8"))
        agents = data.get("agents", data) if isinstance(data, dict) else data
        for a in agents:
            slug = (a.get("slug") or "").strip()
            desc = (a.get("description") or "").strip()
            name = (a.get("name") or "").strip()
            if not slug or slug == "metis" or not desc:
                continue  # skip the generalist — it's the fallback, not a match target
            vecs.append((slug, embed_document(f"{name}. {desc}")))
    except Exception:
        vecs = []
    _AGENT_ROUTE_VECS = vecs
    return vecs


def _semantic_route(request: str, min_top: float = 0.62, rel_margin: float = 0.25):
    """Embedding route: the specialist whose description best matches the request.

    Returns (slug|None, score, ranking). Best-effort — never raises.

    WHY THE GATE IS RELATIVE TO THE SPREAD (audit 2026-09-14)
        These embeddings are anisotropic — random text sits ~0.5 cosine — so an
        absolute score threshold is meaningless on its own and the original code
        rightly added a margin test. But it made the margin an absolute constant
        (0.05), and agent DESCRIPTIONS are short, same-register text that clusters
        tightly: real inter-agent margins run 0.005-0.04. Measured over seven real
        requests, the constant blocked the CORRECT rank-1 agent three times
        (background-maker 0.005, rc-builder 0.030, learning-architect 0.025) and
        admitted exactly one request — which it then routed wrongly.

        A fixed cutoff in the tail of a distribution selects by luck. Same lesson
        as the field-week relevance floor. So the margin is now judged against the
        spread this particular request actually produced: rank-1 must stand clear
        of the pack by a fraction of (top - mean), not by a constant nobody can
        calibrate from outside.

    HOW THESE TWO NUMBERS WERE CHOSEN
        By sweeping both against the 29 labelled cases in
        tools/test_routing_regression.py, not by judgement. The sweep also
        settled a more important question: over this agent set the embedding
        router puts the right specialist at rank 1 only 13 times in 29, so it is
        NOT a good standalone router and must not be tuned as though it were.
        (0.62, 0.25) is the high-precision corner — 5 right, 1 wrong, 23
        abstentions. Abstaining is cheap: it falls to the generalist, who answers
        competently. A confidently wrong specialist is not cheap. Re-run the
        sweep before changing either number.
    """
    try:
        import math
        from metis_mcp.embeddings import embed_query
        cands = _load_agent_route_vecs()
        if len(cands) < 3:
            return None, 0.0, []
        q = embed_query(request)

        def _cos(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(y * y for y in b))
            return dot / (na * nb) if na and nb else 0.0

        scored = sorted(((_cos(q, v), slug) for slug, v in cands), reverse=True)
        scored = [(sc, sl) for sc, sl in scored if sl not in _RETIRED_ROUTING_SLUGS]
        if len(scored) < 3:
            return None, 0.0, scored
        top_score, top_slug = scored[0]
        second_score = scored[1][0]
        mean_score = sum(sc for sc, _ in scored) / len(scored)
        spread = top_score - mean_score
        if top_score >= min_top and (top_score - second_score) >= rel_margin * spread:
            return top_slug, top_score, scored
        return None, top_score, scored
    except Exception:
        return None, 0.0, []


# Slugs whose plain de-hyphenation reads badly in a sentence. Everything else
# de-hyphenates fine ("writing-partner" -> "writing partner"), so this stays
# small on purpose rather than becoming a second registry to maintain.
_AGENT_DISPLAY = {
    "metis": "Metis",
    "cybersecurity": "security specialist",
    "dhis2-expert": "DHIS2 expert",
    "rc-builder": "Metis builder",
    "hr-talent": "talent scout",
    "critic": "critic",
    "edu-expert": "education specialist",
    "Explore": "code explorer",
    "Plan": "planner",
}


def _friendly_agent_name(slug: str) -> str:
    """A name a non-technical reader recognises, usable inside "the ___"."""
    if slug in _AGENT_DISPLAY:
        return _AGENT_DISPLAY[slug]
    if slug.startswith("metis-audit-"):
        return f"{slug[len('metis-audit-'):].replace('-', ' ')} auditor"
    if slug.startswith("metis-"):
        return slug[len("metis-"):].replace("-", " ") + " specialist"
    return slug.replace("-", " ")


def _who_is_on_it(routed_because: list) -> str:
    """The line the assistant reads out to the researcher.

    Written for someone who does not know that an agent roster exists. It names
    each specialist in plain words and says WHY it was chosen — and the reason is
    honest rather than invented, because it is the keyword that actually did the
    routing. "Because you said 'study design'" is something a person can check,
    disagree with, and correct. "Based on your request" is not.
    """
    if not routed_because:
        return ""

    # The generalist fallback is not a specialist assignment and should not be
    # dressed up as one — saying "I've put Metis on it" to someone who thinks
    # Metis IS the assistant is confusing rather than informative.
    if len(routed_because) == 1 and routed_because[0][0] == "metis":
        return "No specialist fits this one, so I'll take it myself."

    if len(routed_because) == 1:
        slug, why = routed_because[0]
        return f"I've asked the {_friendly_agent_name(slug)} to look at this \u2014 {why}."
    count = {2: "two", 3: "three"}.get(len(routed_because), str(len(routed_because)))
    bullets = "\n".join(
        f"  \u2022 the {_friendly_agent_name(slug)} \u2014 {why}"
        for slug, why in routed_because
    )
    return f"I've asked {count} specialists to look at this:\n{bullets}"


def _parse_intent_stage(request: str, session_id: str) -> dict:
    """Stage 5: select agent(s) + complexity.

    TWO ROUTERS, ONE DECISION (audit 2026-09-14)
        Keyword rules and the embedding router were two disjoint lanes: the
        embedding router ran ONLY when no keyword matched, so it could never
        break a tie it would have won. Every mis-route the audit reproduced was
        decided by a keyword before the better judge was consulted.

        Now the embedding route always runs, and it is allowed to overrule the
        keyword winner in exactly one situation: when the ONLY rules that fired
        are in the GENERIC band (priority >= _GENERIC_PRIORITY_FLOOR) — words
        like "clean", "chart" or "feed" that merely co-occur with a domain. A
        distinctive keyword ("dhis2", "powerpoint") still wins outright, because
        it is a stronger signal than any similarity score and because the
        researcher can read, edit and trust it.
    """
    lower = request.lower()
    agents: list[str] = []
    task_type = "general"
    matched_rule_id = None
    contributing_rule_ids: list[int] = []
    routed_because: list[tuple[str, str]] = []
    all_matching_rule_ids: list[int] = []
    best_priority = 999  # the strongest (lowest) priority that actually routed

    # Collect up to MAX_AGENTS specialists rather than breaking on the first.
    # A real request often needs two perspectives ("review my methods AND the
    # grammar"), and the single-agent break made that impossible to express —
    # the second specialist was silently dropped. Order is preserved, so the
    # most-specific rule still leads.
    for row in _load_routing_rules():
        kw, agent, t_type, mode, rule_id, _src = row[0], row[1], row[2], row[3], row[4], row[5]
        prio = row[6] if len(row) > 6 and row[6] is not None else 100
        if not _kw_match(kw, lower, mode or "word"):
            continue

        # Every keyword that is PRESENT is recorded, whether or not it changed
        # the outcome. This is what makes the routing table auditable: a rule
        # with matches > 0 and hits == 0 was shadowed by an earlier rule, while
        # matches == 0 means the request never arrived. Those two call for
        # opposite fixes and were previously indistinguishable — see
        # tools/audit_routing.py and the 2026-08-25 routing audit.
        if rule_id and rule_id > 0 and rule_id not in all_matching_rule_ids:
            all_matching_rule_ids.append(rule_id)

        if agent in agents or len(agents) >= _MAX_ROUTED_AGENTS:
            continue
        agents.append(agent)
        routed_because.append((agent, f"you said \u201c{kw}\u201d"))
        best_priority = min(best_priority, int(prio))
        if not contributing_rule_ids:
            task_type = t_type          # the leading rule names the task type
            matched_rule_id = rule_id   # back-compat: the primary rule
        if rule_id and rule_id > 0:
            contributing_rule_ids.append(rule_id)

    uncovered = not agents

    # The embedding route ALWAYS runs now — it is the tie-breaker as well as the
    # backstop. Cheap after the first call: the agent vectors are cached for the
    # life of the process and only the request is embedded.
    sem_slug, sem_score, _sem_rank = _semantic_route(request)

    if uncovered:
        if sem_slug:
            agents = [sem_slug]
            routed_because = [(sem_slug, "the closest match to what you asked")]
            task_type = "semantic"  # not a keyword match → measurable as fallback-routed
            uncovered = False       # a specialist WAS found (via the semantic backstop)
        else:
            agents = ["metis"]
            routed_because = [("metis", "")]
            task_type = "uncovered"  # explicit: nothing matched → generalist
    elif (sem_slug and sem_slug not in agents
          and best_priority >= _GENERIC_PRIORITY_FLOOR):
        # Only a generic word routed this. Let the meaning of the sentence lead
        # and keep the keyword match as a second opinion rather than dropping it.
        agents.insert(0, sem_slug)
        routed_because.insert(0, (sem_slug, "what you're actually asking about"))
        agents = agents[:_MAX_ROUTED_AGENTS]
        routed_because = routed_because[:_MAX_ROUTED_AGENTS]
        task_type = "semantic+keyword"

    if all_matching_rule_ids:
        try:
            with connect(paths.db) as con:
                if contributing_rule_ids:
                    con.execute(
                        "UPDATE agent_routing_rules SET hits = hits + 1 WHERE rule_id IN "
                        f"({','.join('?' * len(contributing_rule_ids))})",
                        contributing_rule_ids,
                    )
                con.execute(
                    "UPDATE agent_routing_rules SET matches = matches + 1 WHERE rule_id IN "
                    f"({','.join('?' * len(all_matching_rule_ids))})",
                    all_matching_rule_ids,
                )
                con.commit()
        except Exception:
            pass

    # Both stages' outputs are recorded so the calibration above can be
    # re-MEASURED later rather than re-argued. Never fatal.
    try:
        _write_event_sync(
            session_id, "routing",
            json.dumps({"agents": agents, "task_type": task_type,
                        "keyword_priority": best_priority if best_priority < 999 else None,
                        "semantic": sem_slug, "semantic_score": round(sem_score, 3)}),
        )
    except Exception:
        pass

    word_count = len(lower.split())
    if any(kw in lower for kw in _CHAIN_KEYWORDS):
        complexity = "chain"
    elif any(kw in lower for kw in _DEEP_KEYWORDS) or word_count > 40:
        complexity = "deep"
    elif any(kw in lower for kw in _QUICK_KEYWORDS) or word_count < 10:
        complexity = "quick"
    else:
        complexity = "standard"

    return {"agents": agents, "complexity": complexity, "task_type": task_type,
            "uncovered": uncovered, "routed_because": routed_because}


@app.tool()
def record_routing_preference(phrase: str, agent_slug: str, scope: str = "always", priority: int = 5) -> str:
    """Active-learning routing. After Metis asks the user 'should I always route
    requests like this to <agent>, or just this once?', call this with their answer.

    scope='always' writes a permanent, high-priority rule (beats the built-in seeds)
    into the routing DB — part of institutional memory, persists across Metis updates.
    scope='once' is acknowledged but not stored.

    Args:
        phrase: the trigger word/phrase the user wants routed (e.g. "spatial scan").
        agent_slug: which agent to route it to (e.g. "epidemiologist").
        scope: 'always' (persist) or 'once' (don't store).
        priority: lower = more specific / checked first (default 5 beats all seeds).
    """
    phrase = (phrase or "").strip().lower()
    if not phrase or not agent_slug:
        return "Could not record: both a phrase and an agent_slug are required."
    if scope != "always":
        return f"Noted for this once — '{phrase}' → {agent_slug}. Not stored as a standing rule."
    _ensure_routing_table()
    with connect(paths.db) as con:
        con.execute(
            "INSERT INTO agent_routing_rules "
            "(keyword, agent_slug, task_type, priority, match_mode, source, scope) "
            "VALUES (?, ?, 'user-defined', ?, 'word', 'user', 'always') "
            "ON CONFLICT(keyword, agent_slug) DO UPDATE SET "
            "priority=excluded.priority, source='user', scope='always'",
            (phrase, agent_slug, priority),
        )
        con.commit()
    return f"Learned: I'll always route '{phrase}' to the {agent_slug} from now on. (Stored in your routing memory.)"


# ── Personalization layer — the decision/preference database ──────────────────
# Metis grows with the user: preferences (coding style, citation style, methods
# defaults), recurring references (articles, datasets), and explicit decisions are
# recorded here and recalled into context on every request. Part of institutional
# memory — persists across updates, stays on the user's machine.

def _ensure_decisions_table() -> None:
    with connect(paths.db) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS user_decisions ("
            " decision_id INTEGER PRIMARY KEY,"
            " category TEXT,"            # preference | coding | citation | methodology | writing | article-ref | dataset | routing | other
            " decision TEXT NOT NULL,"
            " context TEXT,"
            " scope TEXT DEFAULT 'always',"   # always | once
            " source TEXT DEFAULT 'user',"
            " hits INTEGER DEFAULT 0,"
            " created_at TEXT DEFAULT (datetime('now')))"
        )
        con.commit()


@app.tool()
def record_decision(decision: str, category: str = "preference",
                    context: str = "", scope: str = "always",
                    agent_slug: str = "") -> str:
    """Record a user preference or decision so Metis adapts to the user over time.

    Use this whenever the user states (or confirms) a standing preference or makes a
    decision worth remembering — coding style, citation format, a methods default, an
    article/dataset they keep returning to, a naming convention, a workflow choice.
    These are recalled into context on future requests (recall_decisions), so Metis
    personalizes instead of asking again.

    Args:
        decision: the preference/decision in plain language (e.g. "Always use tidyverse style in R, never base apply").
        category: preference | coding | citation | methodology | writing | article-ref | dataset | routing | other.
        context: optional — when/why it applies (e.g. "for HAT spatial analyses").
        scope: 'always' (persist) or 'once'.
        agent_slug: the specialist that should APPLY this decision — e.g.
            "frontend-designer-builder" for a layout rule, "writing-partner" for
            a prose rule, "librarian" for what matters in the library. Leave
            empty for a project-wide rule that every agent should carry.

            Attribution is what makes the decision reachable. `get_agent_context`
            injects an agent's own decisions plus the project-wide ones, and a
            flat list of every preference injected into every agent is noise that
            gets ignored. Measured 2026-08-24: user_decisions held 2 rows while
            session summaries held 7,578 decision entries — so invoking a
            specialist returned a persona and nothing about how the researcher
            wants things done, which is why routing to one stopped being worth it.
    """
    decision = (decision or "").strip()
    if not decision:
        return "Could not record: a decision/preference text is required."
    if scope != "always":
        return f"Noted for this once: {decision}"
    _ensure_decisions_table()
    with connect(paths.db) as con:
        try:
            con.execute("ALTER TABLE user_decisions ADD COLUMN agent_slug TEXT DEFAULT ''")
        except Exception:
            pass
        con.execute(
            "INSERT INTO user_decisions (category, decision, context, scope, source, "
            "agent_slug) VALUES (?, ?, ?, 'always', 'user', ?)",
            (category, decision, context, (agent_slug or "").strip()),
        )
        con.commit()
    who = (agent_slug or "").strip() or "every agent"
    return (f"Recorded ({category}) for {who}: {decision}. "
            f"It is injected into that agent's context from now on.")


@app.tool()
def recall_decisions(category: str = "", limit: int = 30) -> str:
    """Recall the user's recorded preferences/decisions to personalize a response.
    Called during context assembly (and any time Metis is about to act in a way a
    preference might govern). Empty category returns all categories.

    Args:
        category: filter to one category, or '' for all.
        limit: max rows.
    """
    try:
        _ensure_decisions_table()
        with connect(paths.db) as con:
            if category:
                rows = con.execute(
                    "SELECT category, decision, context FROM user_decisions "
                    "WHERE scope='always' AND category=? ORDER BY created_at DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT category, decision, context FROM user_decisions "
                    "WHERE scope='always' ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
    except Exception as e:
        return f"(could not read decisions: {e})"
    if not rows:
        return "No recorded preferences yet."
    lines = [f"- [{c}] {d}" + (f" — {ctx}" if ctx else "") for c, d, ctx in rows]
    return "Recorded preferences & decisions:\n" + "\n".join(lines)


@app.tool()
def evaluate_against_layers(answer: str, session_id: str = "", task_type: str = "") -> str:
    """Stage 6 — the evaluate gate. BEFORE you reply to the user, pass your drafted
    answer here. It checks the answer against the user's layers — recorded preferences,
    persona voice, institutional facts — and surfaces any conflict to fix first.

    Returns a verdict (OK / REVIEW), the preferences this answer must honor, and any
    detected conflicts (e.g. a 'never use base apply' preference when the answer shows
    `apply(`). Resolve REVIEW items before replying.

    Args:
        answer: your drafted answer text.
        session_id: current session (optional).
        task_type: optional routing task_type for narrower preference recall.
    """
    import re as _re
    issues: list[str] = []
    prefs: list[str] = []
    try:
        _ensure_decisions_table()
        with connect(paths.db) as con:
            rows = con.execute(
                "SELECT category, decision, context FROM user_decisions "
                "WHERE scope='always' ORDER BY created_at DESC LIMIT 30"
            ).fetchall()
        low = (answer or "").lower()
        for r in rows:
            d = r["decision"]
            prefs.append(f"[{r['category']}] {d}")
            # lint: a "never/avoid/don't X" preference whose key token appears in the answer
            for m in _re.finditer(r"(?:never|avoid|don'?t|do not|no)\s+(?:use\s+)?([a-z0-9_.()+ -]{3,40})", d.lower()):
                phrase = m.group(1).strip(" .")
                toks = [t for t in phrase.split() if len(t) >= 4]
                hit = next((t for t in toks if t in low), "")
                if hit:
                    issues.append(f"Possible conflict with '{d}' — the answer mentions '{hit}'.")
    except Exception as e:
        return f"(could not evaluate: {e})"

    # Red-line scan on the drafted answer.
    #
    # `_check_output_stage` was written as pipeline "Stage 9" and then never called
    # by anything — a security control that existed, looked structural, and had no
    # caller (found by the structural sweep, 2026-08-12). It could not simply be
    # wired into run_metis, because run_metis returns an INSTRUCTION SHEET, not an
    # answer; there was no output there to scan. This function is the only place in
    # the system that actually receives the model's drafted answer, so it is the
    # only place the check can mean anything.
    #
    # Advisory, not blocking: it surfaces SENSITIVE content and destructive command
    # patterns for the model to fix before replying, and records a `redline` event
    # so the scan leaves a trace even when nobody reads the verdict.
    try:
        _redline = _scan_safety(answer or "")
        if _redline["classification"] == "SENSITIVE":
            issues.append(
                "Red line — the drafted answer contains SENSITIVE content: "
                + "; ".join(_redline["warnings"])
            )
        if _DESTRUCTIVE_RE.search(answer or ""):
            issues.append(
                "Red line — the drafted answer contains a destructive command pattern "
                "(rm -rf / DROP TABLE / DELETE FROM / TRUNCATE). Confirm it is intended "
                "and clearly explained before replying."
            )
        if issues and session_id:
            _write_event_sync(session_id, "redline", "; ".join(issues)[:2000])
    except Exception:
        pass  # an advisory scan must never break the evaluate gate

    verdict = "REVIEW" if issues else "OK"
    out = [f"**Evaluation against your layers: {verdict}**"]
    if issues:
        out += ["", "Resolve before replying:"] + [f"- {i}" for i in issues]
    if prefs:
        out += ["", "Preferences this answer must honor:"] + [f"- {p}" for p in prefs[:10]]
    out += ["", "Also confirm: the answer is in the persona voice (warm, plain, addressed to the user) "
            "and does not contradict the institutional context you were given."]
    return "\n".join(out)


# ── Stage 6: Token budget allocation ──────────────────────────────────────────

_BUDGET_MAP = {
    "quick":    {"model": model_for("brief"), "max_tokens": 1024},
    "standard": {"model": model_for("default"),          "max_tokens": 4096},
    "deep":     {"model": model_for("deep"),            "max_tokens": 8192},
    "chain":    {"model": model_for("deep"),            "max_tokens": 8192},
}


def _web_line() -> str:
    """One line about complementing from the web, honouring a recorded preference.

    Keystone M5, generalised: the same offer→record→honour loop the procedure hints
    use, applied to a second recurring choice. "Should I also look outside your
    library?" is asked on every research turn, and until now the answer was never
    written down, so it was asked forever.

    Reads `user_decisions` (category 'research') before speaking: once the
    researcher has said always or never, this stops being a question.
    """
    try:
        from metis_mcp import ambient

        pref = ambient.standing_preference("research", "complement from the web")
    except Exception:
        pref = ""
    if pref == "always":
        return ("They have asked you to ALWAYS complement library grounding with current "
                "outside sources — do so without asking.")
    if pref == "never":
        return ("They have asked you NOT to go outside their library — answer from the "
                "grounding above and say plainly what it cannot cover.")
    return (
        "If the question needs sources beyond their library, say so and offer to look "
        "further afield — then record the answer so it is asked once, not every time: "
        "`record_decision(decision=\"always complement from the web when the library is "
        "thin\", category=\"research\")`, or \"never ...\" if they decline."
    )


def _allocate_budget(complexity: str) -> dict:
    """Stage 6: Select model and token ceiling based on complexity level."""
    return _BUDGET_MAP.get(complexity, _BUDGET_MAP["standard"])


# ── Stage 7: Surgical context assembly ────────────────────────────────────────

def _auto_reflexion(session_id: str, agent_slug: str, could_improve: str = "",
                    missing_context: str = "") -> None:
    """Server-side reflexion write-back (Keystone P3.2). The self-improvement loop
    starved because write_reflexion was voluntary; auto-log a reflexion for NOTABLE
    turns (e.g. uncovered routing) so recurring gaps accrue into nightly consolidation
    without depending on the model remembering. Targeted (not every turn) so it feeds
    signal, not noise. Best-effort; never raises."""
    try:
        with connect(paths.db) as con:
            con.execute(_REFLEXION_DDL)
            con.execute(
                "INSERT INTO reflexion_log (session_id, agent_slug, went_well,"
                " could_improve, missing_context, tool_wishes, created_at)"
                " VALUES (?, ?, '', ?, ?, '', ?)",
                (session_id or "", agent_slug or "metis",
                 could_improve[:400], missing_context[:400], _now()),
            )
            con.commit()
    except Exception:
        pass


def _assemble_context_stage(intent: dict, session_id: str) -> str:
    """Stage 7: Retrieve minimum needed context from memory_entries."""
    task_type = intent.get("task_type", "general")
    request_snippet = intent.get("_request", "")[:60]
    rows = []

    try:
        with connect(paths.db) as con:
            if task_type in ("literature", "phd", "methods"):
                rows = con.execute(
                    """SELECT title, summary FROM memory_entries
                       WHERE entry_type = 'literature'
                          OR topics LIKE ?
                       ORDER BY created_at DESC LIMIT 5""",
                    (f"%{request_snippet}%",),
                ).fetchall()
            elif task_type in ("code", "project"):
                rows = con.execute(
                    """SELECT title, summary FROM memory_entries
                       WHERE entry_type IN ('project', 'session')
                       ORDER BY created_at DESC LIMIT 5""",
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT title, summary FROM memory_entries ORDER BY created_at DESC LIMIT 5",
                ).fetchall()
    except Exception:
        pass

    parts = [
        f"- [{r['title']}] {(r['summary'] or '')[:120]}"
        for r in rows
        if r["title"]
    ]
    recent = "Recent context:\n" + "\n".join(parts) if parts else ""

    # Stage 3 woven into 7: the user's standing preferences/decisions, pulled in on
    # EVERY request so the answer respects them without re-asking. Personalization.
    pref_block = ""
    try:
        _ensure_decisions_table()
        cat_map = {
            "code": ("coding",), "project": ("coding",),
            "methods": ("methodology",), "epi": ("methodology",), "biostat": ("methodology",),
            "writing": ("writing", "citation"), "literature": ("citation", "article-ref"),
            "phd": ("writing", "methodology"),
        }
        cats = cat_map.get(task_type, ())
        with connect(paths.db) as con:
            if cats:
                ph = ",".join("?" * len(cats))
                prows = con.execute(
                    "SELECT category, decision, context FROM user_decisions "
                    f"WHERE scope='always' AND (category='preference' OR category IN ({ph})) "
                    "ORDER BY created_at DESC LIMIT 8",
                    tuple(cats),
                ).fetchall()
            else:
                prows = con.execute(
                    "SELECT category, decision, context FROM user_decisions "
                    "WHERE scope='always' ORDER BY created_at DESC LIMIT 8",
                ).fetchall()
        if prows:
            pref_block = "Your standing preferences (apply these):\n" + "\n".join(
                f"- [{r['category']}] {r['decision']}" + (f" — {r['context']}" if r['context'] else "")
                for r in prows
            )
    except Exception:
        pass

    # Question-conditioned recall over the REAL memory + work corpus (Keystone P3.1).
    # The `recent` block above is recency + LIKE only and never touches the 768-d
    # vector layers. Add the same hybrid vector+keyword engine used at ingestion
    # (_cross_pollinate_core), keyed on the ACTUAL request, so relevant prior papers,
    # notes, meetings, projects and ideas surface BY CONSTRUCTION — not only if the
    # model later chooses to call a recall tool. Degrades to keyword-only if the
    # embedding model is unavailable (the engine handles that internally).
    related = ""
    try:
        req = (intent.get("_request", "") or "").strip()
        if req:
            from metis_mcp.tools.ideas import _cross_pollinate_core
            matches = _cross_pollinate_core(req, max_results=5) or []
            lines = []
            for m in matches:
                title = (m.get("title") or m.get("text") or "").strip()
                src = (m.get("source") or m.get("type") or "").strip()
                if title:
                    lines.append(f"- {('[' + src + '] ') if src else ''}{title[:120]}")
            if lines:
                related = ("Related from your library & past work (recall — ground your "
                           "answer in these where relevant):\n" + "\n".join(lines))
    except Exception:
        pass

    # Token/char budget (Keystone P3.6): assemble in priority order — standing
    # preferences, then question-recall, then recency — and stop before a fixed
    # ceiling, so injected context stays "surgical" no matter how much matched.
    _BUDGET = 1800  # ~450 tokens of context
    out: list[str] = []
    used = 0
    for b in (pref_block, related, recent):
        if not b:
            continue
        if used + len(b) > _BUDGET:
            head = b[: max(0, _BUDGET - used)].rstrip()
            if head:
                out.append(head + "\n…(trimmed to fit context budget)")
            break
        out.append(b)
        used += len(b) + 2
    return "\n\n".join(out)


# ── Stage 8: save_session_event (MCP tool) ────────────────────────────────────

@app.tool()
async def save_session_event(
    session_id: str,
    event_type: str,
    content: str,
) -> list[TextContent]:
    """Stage 8: Persist one atomic event to session_events (write-through guarantee).

    Call this after every tool call, file write, and classification decision.
    Event types: 'turn' | 'tool_call' | 'result' | 'file_write' | 'redline' | 'classification'

    Args:
        session_id: Session ID from session_bootstrap().
        event_type: Category of event being recorded.
        content: Event content (truncated to 2000 chars).
    """
    _ensure_pipeline_tables()
    try:
        with connect(paths.db) as con:
            con.execute(
                """INSERT INTO session_events (session_id, event_type, content, created_at)
                   VALUES (?, ?, ?, ?)""",
                (session_id, event_type, content[:2000], _now()),
            )
            con.commit()
        return [TextContent(
            type="text",
            text=f"Event saved: [{event_type}] session={session_id[:8]}…",
        )]
    except Exception as e:
        return [TextContent(type="text", text=f"Error saving event: {e}")]


# ── Stage 9: Output red-line post-check ───────────────────────────────────────

_DESTRUCTIVE_RE = re.compile(
    r"\b(rm\s+-rf|DROP\s+TABLE|DELETE\s+FROM\s+\w+\s*;|TRUNCATE\s+TABLE)", re.IGNORECASE
)


# NOTE: the former `_check_output_stage` lived here — pipeline "Stage 9", an output
# red-line scan that was defined and then never called by anything. Its checks now
# run inside `evaluate_against_layers`, which is the only function that actually
# receives the model's drafted answer. Removed rather than left in place: an unused
# second copy of a security control is how the first one came to be trusted without
# being reached.


# ── Stage 12 (entry point): run_metis ────────────────────────────────────────

@app.tool()
async def run_metis(
    request: str,
    session_id: str = "",
    client: str = "code",
    max_turns: int = 20,
) -> list[TextContent]:
    """Master /metis entry point — runs the 11-stage pipeline and returns a routing decision.

    Every /metis invocation passes through here. The pipeline:
      1. Bootstraps or resumes the session
      2. Classifies content (PUBLIC/INTERNAL/CONFIDENTIAL/SENSITIVE)
      3. Data Guardian: blocks SENSITIVE requests outright
      4. Cybersecurity: blocks prompt injection and suspicious URLs
      5. Parses intent and selects the appropriate agent(s)
      6. Allocates model and token budget
      7. Assembles minimum surgical context from memory
      8. Persists the turn to session_events
      9. Returns routing decision — agents execute and then call:
           save_session_event(..., 'result', output)
           log_agent_run(..., session_id=session_id)
           write_reflexion(session_id, agent_slug, ...)

    Stages 10 (logging) and 11 (reflexion) are called by the executing agent
    after completing their work.

    Args:
        request: The researcher's request text.
        session_id: Existing session ID if resuming. Leave empty to auto-bootstrap.
        client: Which Claude client is calling ('code'|'chat'|'cowork'|'dashboard').
        max_turns: Maximum pipeline turns before graceful truncation (default 20).
    """
    _ensure_pipeline_tables()
    lines: list[str] = []
    _auto_handoff_note: str = ""

    # ── Turn cap guard ─────────────────────────────────────────────────────
    # Count existing turns in this session to enforce max_turns
    if session_id:
        try:
            with connect(paths.db) as con:
                turn_count = con.execute(
                    "SELECT COUNT(*) FROM session_events "
                    "WHERE session_id = ? AND event_type = 'turn'",
                    (session_id,),
                ).fetchone()[0]
            if turn_count >= max_turns:
                return [TextContent(type="text", text=(
                    f"**max_turns reached** ({turn_count}/{max_turns}).\n"
                    "**status:** truncated\n"
                    "This session has reached its turn limit. "
                    "Start a new session with `session_bootstrap()` to continue.\n\n"
                    "**Partial context preserved** — call `session_bootstrap()` "
                    "to resume with recent events."
                ))]
            # ── 80% threshold: auto-save handoff brief ─────────────────────
            if turn_count >= int(max_turns * 0.8):
                try:
                    from metis_mcp.tools.handoff import generate_handoff_brief as _gen_handoff
                    _gen_handoff(session_id=session_id, write_to_journal=True)
                    _auto_handoff_note = (
                        f"\n\n> **Auto-handoff saved** — session is at "
                        f"{turn_count}/{max_turns} turns (80%+). A handoff brief has been "
                        f"written to `journal/`. Run `/metis_handoff` or check the Metis tab "
                        f"to review it before this session ends."
                    )
                except Exception:
                    pass
        except Exception:
            pass  # Don't block if we can't check

    # ── Stage 1: Session bootstrap ─────────────────────────────────────────
    if not session_id:
        bootstrap = await session_bootstrap(client=client)
        try:
            data = json.loads(bootstrap[0].text)
            session_id = data["session_id"]
            is_new = data.get("is_new", True)
        except Exception:
            session_id = str(uuid4())
            is_new = True
    else:
        is_new = False

    lines.append(f"**Session:** `{session_id[:8]}…` ({'new' if is_new else 'resumed'})")

    # ── Stage 2: Persist the researcher's turn ─────────────────────────────
    _write_event_sync(session_id, "turn", request)

    # ── Stage 3: Data Guardian intercept ──────────────────────────────────
    safety = await _check_data_safety_stage(request, session_id)
    lines.append(f"**Classification:** {safety['classification']}")

    if safety["classification"] == "SENSITIVE":
        return [TextContent(type="text", text=(
            "**Data Guardian blocked this request.**\n"
            f"Classification: SENSITIVE\n"
            f"Warnings: {'; '.join(safety['warnings'])}\n\n"
            "This request contains patient-level or individually-identifying data. "
            "Metis will not process it. Please remove sensitive identifiers and try again."
        ))]

    if safety["classification"] == "CONFIDENTIAL":
        lines.append(
            f"⚠ Confidential content detected: {'; '.join(safety['warnings'])}. "
            "Anonymize before sharing externally."
        )

    # ── Stage 4: Cybersecurity intercept ──────────────────────────────────
    cyber = await _cybersecurity_stage(request, session_id)
    if not cyber["safe"]:
        threats_text = "\n".join(f"- {t}" for t in cyber["threats"])
        return [TextContent(type="text", text=(
            "**Cybersecurity intercept triggered.**\n"
            f"Threats detected:\n{threats_text}\n\n"
            "I am ignoring the suspicious content and not proceeding. "
            "The threats above are shown so you are aware."
        ))]

    # ── Stage 5: Intent parsing ────────────────────────────────────────────
    intent = _parse_intent_stage(request, session_id)
    intent["_request"] = request
    _who = _who_is_on_it(intent.get("routed_because") or [])
    if _who:
        lines.append("")
        lines.append("**Say this to the researcher in your own words. Never show "
                     "them the Routing/Model lines below \u2014 those are machinery.**")
        lines.append(_who)
        lines.append("")
    lines.append(
        f"**Routing:** {', '.join(intent['agents'])} | complexity={intent['complexity']}"
    )
    _write_event_sync(
        session_id, "classification",
        f"agents={intent['agents']} complexity={intent['complexity']} task={intent['task_type']}",
    )

    # ── Stage 6: Token budget ──────────────────────────────────────────────
    budget = _allocate_budget(intent["complexity"])
    lines.append(f"**Model:** {budget['model']} (max_tokens={budget['max_tokens']})")
    _write_event_sync(
        session_id, "classification",
        f"model={budget['model']} max_tokens={budget['max_tokens']}",
    )

    # ── Stage 6b: Live dispatch-write (S.2) ────────────────────────────────
    # Record a 'running' agent_runs row for EVERY routed agent the moment we
    # route, so the dashboard's "who's working now" shows the whole team rather
    # than only the first name. Each agent's later log_agent_run(session_id=...)
    # UPDATES its own row to a final status — matched on session_id AND
    # agent_slug, because with several rows open, matching on session alone
    # would complete whichever row happened to be newest and mislabel it.
    #
    # A stale-guard on the dashboard stops a perpetual "working…" if a
    # completion never arrives. Best-effort only: routing must not fail because
    # the activity surface could not be written.
    try:
        _routed = list(intent.get("agents") or ["metis"])
        _now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with connect(paths.db) as _con:
            for _agent in _routed:
                _con.execute(
                    """INSERT INTO agent_runs
                       (agent_slug, task_summary, input_path, output_path, status,
                        created_at, input_tokens, output_tokens, model, session_id)
                       VALUES (?, ?, '', '', 'running', ?, 0, 0, ?, ?)""",
                    (
                        _agent,
                        request[:200],
                        _now_iso,
                        budget.get("model", ""),
                        session_id,
                    ),
                )
            _con.commit()
    except Exception:
        pass

    # ── Stage 7: Surgical context assembly ────────────────────────────────
    context = _assemble_context_stage(intent, session_id)

    # Stage 7b — RAG grounding BY CONSTRUCTION (Keystone 3.0). Previously the pipeline
    # only TOLD the model to search the library; it never did. For research-oriented,
    # non-trivial turns, actually query the knowledge layers (library + backgrounds)
    # and inject the top cited chunks, so answers are grounded even if the model never
    # elects to call the RAG tool. Gated + bounded so quick turns stay fast; best-effort.
    _tt, _cx = intent.get("task_type"), intent.get("complexity")
    if _tt in ("literature", "methods", "phd") or (
        _tt in ("general", "semantic", "uncovered") and _cx in ("standard", "deep", "chain")
    ):
        try:
            from metis_mcp.tools.knowledge_db import search_pdf_knowledge as _rag_search
            _rag = await _rag_search(request, top_k=5)
            _rag_text = _rag[0].text if _rag else ""

            # RELEVANCE FLOOR — added 2026-08-21, matching the Claude Code hook.
            #
            # A top-k search ALWAYS returns k passages. For a question the corpus
            # knows nothing about, that means injecting the five least-bad
            # matches — which does not merely waste tokens, it makes unrelated
            # papers look like supporting evidence. Measured the same day: a
            # question about diagnostic algorithms pulled a 1978 general
            # epidemiology textbook at 0.74 simply because nothing better existed.
            #
            # Below the floor the honest output is "your library has nothing on
            # this", which is real information about a gap rather than a failure.
            import re as _re
            _scores = [float(s) for s in _re.findall(r"\(score:\s*([\d.]+)\)", _rag_text)]
            _kept = [s for s in _scores if s >= 0.62]
            _low = _rag_text.lower()[:80]
            _usable = (
                _rag_text and _kept
                and "nothing" not in _low and "no chunks" not in _low
                and "not indexed" not in _low
            )
            if _rag_text and not _kept:
                # Say so explicitly. Silence here would let the model imply corpus
                # support it does not have.
                context = ((context + "\n\n") if context else "") + (
                    "GROUNDING — the researcher's own indexed library was searched for "
                    "this question and returned NOTHING above the relevance threshold. "
                    "Answer from general knowledge and say plainly that their library "
                    "has nothing on this; that absence is itself worth knowing, and "
                    "worth offering to fix. Do not imply the answer is grounded in "
                    "their literature."
                )
            if _usable:
                # The framing matters as much as the retrieval.
                #
                # A bare "grounding from your library" header, next to the standing
                # instruction to ground answers in the indexed library, reads as a
                # BOUNDARY: answer only from these passages. That makes answers
                # narrower the better the library gets, which is exactly backwards.
                # The background exists to anchor an answer in what the researcher
                # already trusts — not to define the edge of what may be said.
                #
                # So the header states both halves explicitly, and asks for the
                # provenance to be visible, which also turns a gap into an action:
                # something worth citing that is missing from the library is a
                # paper worth adding.
                context = ((context + "\n\n") if context else "") + (
                    "GROUNDING — passages from the researcher's own indexed library and "
                    "background layers. Treat these as established, trusted ground: build on "
                    "them and cite them where they bear on the question.\n"
                    "They are NOT the limit of the answer. Bring in relevant recent literature, "
                    "news, guidelines and general knowledge as well — an answer restricted to "
                    "the indexed corpus is a worse answer, not a safer one.\n"
                    "Make the provenance clear: cite these passages as theirs, and mark anything "
                    "from outside their library as not (yet) indexed — then offer to add it.\n"
                    f"State what was consulted — '{len(_kept)} passages from the indexed "
                    f"corpus' — and NEVER claim the whole library was read or checked. This "
                    "is a top-k similarity search, not a literature review; overstating the "
                    "provenance makes the grounding worthless.\n"
                    + _web_line() + "\n"
                    + _rag_text[:1400]
                )
        except Exception:
            pass

    # 3.0 — inline the routed specialist's approach (hand-off BY CONSTRUCTION) so the
    # model adopts the persona even without electing to call get_agent_context. Bounded.
    _primary = (intent.get("agents") or ["metis"])[0]
    if _primary and _primary != "metis":
        try:
            _sp = paths.agents / _primary / "system-prompt.md"
            if _sp.exists():
                context = ((context + "\n\n") if context else "") + \
                    f"Adopt this specialist's approach ({_primary}):\n" + \
                    _sp.read_text(encoding="utf-8")[:1200]
        except Exception:
            pass

    if context:
        lines.append(f"**Context:** {len(context)} chars assembled")

    # ── Stage 7.5: Constitutional policy (deep/chain only) ────────────────
    try:
        from metis_mcp.tools.guardrails import load_constitution
        constitution = load_constitution(intent["complexity"])
    except Exception as e:
        # An empty constitution means the behavioural-policy layer is OFF for this
        # run. That is a security-relevant degradation — say so, do not swallow it.
        log.error(
            "CONSTITUTION NOT LOADED (%s: %s) — this run has NO constitutional "
            "policy in context.", type(e).__name__, e,
        )
        constitution = ""

    # ── Stage 8: Persist routing decision ─────────────────────────────────
    _write_event_sync(
        session_id, "result",
        f"Pipeline ready → route to {intent['agents']}",
    )

    # ── Return routing decision for the executing agent ────────────────────
    lines += [
        "",
        "**Pipeline ready.** Execute using the routing below, then call:",
        f"- `save_session_event('{session_id}', 'result', <output>)` — persist output",
        f"- `log_agent_run(agent_slug='{intent['agents'][0]}', ..., session_id='{session_id}')` — audit trail",
        f"- `write_reflexion(session_id='{session_id}', agent_slug='{intent['agents'][0]}', ...)` — self-critique",
        "",
        f"**Stage 6 — evaluate before returning:** pass your drafted answer to "
        f"`evaluate_against_layers(answer, session_id='{session_id}')` — it checks against the "
        f"persona voice, the institutional context, and the user's standing preferences and "
        f"flags conflicts. Resolve any REVIEW items before replying.",
    ]
    # ── Stage 7 — active learning: grow the routing + decision memory ──────
    if intent.get("uncovered"):
        # Enforce the reflexion write-back server-side (Keystone P3.2) — an uncovered
        # turn is a routing gap; logging it here means recurring gaps surface in the
        # improvement loop even if the model never calls write_reflexion.
        _auto_reflexion(
            session_id, "metis",
            could_improve=f"Uncovered request — no routing rule matched: {request[:120]}",
            missing_context="Consider adding a routing rule or specialist for this class of request.",
        )
        lines.append(
            "**No specialist matched (uncovered)** — handling directly. If requests like this "
            "should go to a specific agent in future, ask the user \"always or just this once?\" "
            "and call `record_routing_preference(phrase, agent_slug, scope)`."
        )
    lines.append(
        "**If the user states or confirms a standing preference** (coding/citation/methods style, "
        "a paper or dataset they rely on, a naming or workflow choice), record it with "
        "`record_decision(decision, category, scope='always')` so Metis applies it next time."
    )
    lines.append("")
    if context:
        lines += ["**Context for agent:**", context, ""]
    if constitution:
        lines += ["", constitution, ""]

    output = "\n".join(lines)
    if _auto_handoff_note:
        output += _auto_handoff_note
    return [TextContent(type="text", text=output)]
