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
  Stage  9 — Output red-line check    Post-execution safety verification
  Stage 10 — Logging                  Delegated to log_agent_run() in agents.py
  Stage 11 — Self-improvement         Delegated to write_reflexion() in self_improvement.py

Public MCP tools: session_bootstrap, save_session_event, run_metis
"""

import datetime
import json
import re
import socket
import struct
from uuid import uuid4

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

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
    except Exception:
        pass


# ── Stage 1: session_bootstrap ───────────────────────────────────────────────

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
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+(were|are)\s+)?a\s+", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
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
_DEFAULT_ROUTING_SEED: list[tuple[list[str], str, str, int]] = [
    # specialists first (low priority) so broad keywords can't grab them
    (["dhis2", "tracker program", "data element", "org unit", "organisation unit", "program stage"], "dhis2-expert", "dhis2", 10),
    (["study design", "selection bias", "confounding", "case definition", "outbreak", "surveillance evaluation", "diagnostic accuracy"], "epidemiologist", "epi", 10),
    (["power calculation", "monte carlo", "simulation study", "r package", "tolerance interval", "dose-response"], "biostatistician", "biostat", 12),
    (["clean", "duplicates", "missing values", "csv", "excel", "spss", "stata", "dataset", "outlier"], "data-analyst", "data", 12),
    (["build a course", "curriculum", "lesson plan", "learning objectives", "course outline", "module design"], "course-builder", "course", 12),
    (["diagram", "ggplot", "plotly", "chart", "figure for", "visualise", "visualize", "system map"], "visualization-maker", "viz", 15),
    (["harvest", "scrape", "extract from", "youtube", "github readme", "pdf content"], "content-harvester", "harvest", 15),
    (["knowledge layer", "background corpus", "rag", "build corpus", "index domain"], "background-maker", "background", 15),
    (["slide", "presentation", "powerpoint", "deck", "speaker notes"], "presentation-maker", "slides", 15),
    (["cover letter", "job application", "fellowship", "interview prep", "career"], "career-coach", "career", 18),
    (["learning path", "spaced repetition", "competency", "study plan", "what to study"], "learning-coach", "learning", 18),
    # the original specialists, now with priorities (broad ones last)
    (["thesis", "chapter", "article 1", "article 2", "article 3", "dissertation", "phd"], "phd-architect", "phd", 20),
    (["meeting", "transcript", "attendee", "agenda"], "meeting-memory", "meeting", 25),
    (["bug", "debug", "shiny", "r script", "python script", "stack trace", "refactor", "fastapi"], "software-engineer", "code", 25),
    (["sample size", "regression", "prevalence", "statistic", "sampling", "icc", "multilevel"], "methods-coach", "methods", 30),
    (["revise", "grammar", "paragraph", "abstract", "introduction", "manuscript", "prose"], "writing-partner", "writing", 30),
    (["paper", "literature", "pubmed", "citation", "reference", "bibliography"], "librarian", "literature", 35),
    (["news", "briefing", "world events", "what happened"], "news-radar", "news", 35),
    (["patient data", "pii", "gdpr", "de-identif", "anonymis"], "data-guardian", "safety", 35),
    (["css", "layout", "ux", "ui design", "design system", "responsive"], "ux-engineer", "ui", 40),
    (["brainstorm", "connect ideas", "cross-pollinate", "explore connections"], "metis", "idea", 50),
]

_DEEP_KEYWORDS = ["review", "critique", "analyse", "analyze", "evaluate", "challenge", "assess"]
_QUICK_KEYWORDS = ["find", "get", "what is", "list", "show", "check", "status", "how many"]
_CHAIN_KEYWORDS = ["and also", "then review", "both", "multiple agents", "all three"]

# Back-compat alias for older imports expecting (keywords, agent, task_type) triples.
_ROUTING_TABLE = [(kws, agent, t) for kws, agent, t, _p in _DEFAULT_ROUTING_SEED]


def _ensure_routing_table() -> None:
    """Create + seed the routing table on first run. Ships empty of user data;
    seeds are default config. User-learned rules accumulate and persist across
    CODE updates (they live in the data layer, never the shipped code)."""
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
        if con.execute("SELECT COUNT(*) FROM agent_routing_rules").fetchone()[0] == 0:
            for kws, agent, t, prio in _DEFAULT_ROUTING_SEED:
                for kw in kws:
                    con.execute(
                        "INSERT OR IGNORE INTO agent_routing_rules "
                        "(keyword, agent_slug, task_type, priority, match_mode, source) "
                        "VALUES (?, ?, ?, ?, 'word', 'seed')",
                        (kw.lower(), agent, t, prio),
                    )
        con.commit()


def _load_routing_rules() -> list[tuple]:
    """(keyword, agent_slug, task_type, match_mode, rule_id, source), most-specific
    first. User-learned rules outrank seeds at equal priority."""
    try:
        _ensure_routing_table()
        with connect(paths.db) as con:
            return con.execute(
                "SELECT keyword, agent_slug, task_type, match_mode, rule_id, source "
                "FROM agent_routing_rules WHERE scope = 'always' "
                "ORDER BY priority ASC, (source='user') DESC, length(keyword) DESC"
            ).fetchall()
    except Exception:
        # DB unavailable → fall back to the in-code seed so routing never dies.
        return [(kw.lower(), agent, t, "word", -1, "seed")
                for kws, agent, t, _p in _DEFAULT_ROUTING_SEED for kw in kws]


def _kw_match(keyword: str, text: str, mode: str) -> bool:
    import re
    if mode == "substring":
        return keyword in text
    # Leading word-boundary only: matches the keyword at the start of a word, so
    # "paper" matches "papers"/"papering" (inflections) but "ui" still does NOT
    # match inside "build" (no word-start before the 'ui'). Avoids both the
    # substring over-match and the strict-boundary plural under-match.
    return re.search(r"\b" + re.escape(keyword), text) is not None


def _parse_intent_stage(request: str, session_id: str) -> dict:
    """Stage 5: select agent(s) + complexity from the DB routing rules (seeded +
    user-learned), word-boundary matched, most-specific first. No match → the
    generalist 'metis', flagged as an explicit `uncovered` decision so the
    un-routed rate is measurable rather than a silent default."""
    lower = request.lower()
    agents: list[str] = []
    task_type = "general"
    matched_rule_id = None

    for kw, agent, t_type, mode, rule_id, _src in _load_routing_rules():
        if _kw_match(kw, lower, mode or "word"):
            agents.append(agent)
            task_type = t_type
            matched_rule_id = rule_id
            break  # most-specific first; first match wins

    uncovered = not agents
    if uncovered:
        agents = ["metis"]
        task_type = "uncovered"  # explicit: no specialist matched → generalist

    if matched_rule_id and matched_rule_id > 0:
        try:
            with connect(paths.db) as con:
                con.execute("UPDATE agent_routing_rules SET hits = hits + 1 WHERE rule_id = ?", (matched_rule_id,))
                con.commit()
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

    return {"agents": agents, "complexity": complexity, "task_type": task_type, "uncovered": uncovered}


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
def record_decision(decision: str, category: str = "preference", context: str = "", scope: str = "always") -> str:
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
    """
    decision = (decision or "").strip()
    if not decision:
        return "Could not record: a decision/preference text is required."
    if scope != "always":
        return f"Noted for this once: {decision}"
    _ensure_decisions_table()
    with connect(paths.db) as con:
        con.execute(
            "INSERT INTO user_decisions (category, decision, context, scope, source) "
            "VALUES (?, ?, ?, 'always', 'user')",
            (category, decision, context),
        )
        con.commit()
    return f"Recorded ({category}): {decision}. I'll apply this going forward."


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


def _allocate_budget(complexity: str) -> dict:
    """Stage 6: Select model and token ceiling based on complexity level."""
    return _BUDGET_MAP.get(complexity, _BUDGET_MAP["standard"])


# ── Stage 7: Surgical context assembly ────────────────────────────────────────

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

    return "\n\n".join(b for b in (pref_block, recent) if b)


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


async def _check_output_stage(output: str, session_id: str) -> dict:
    """Stage 9: Scan pipeline output for red-line violations."""
    violations: list[str] = []

    safety_result = _scan_safety(output)
    if safety_result["classification"] == "SENSITIVE":
        violations.append(
            f"Output contains SENSITIVE content: {'; '.join(safety_result['warnings'])}"
        )

    if _DESTRUCTIVE_RE.search(output):
        violations.append("Output contains a destructive command pattern")

    if violations:
        _write_event_sync(session_id, "redline",
                          f"Output red-line: {'; '.join(violations)}")

    return {"safe": len(violations) == 0, "violations": violations}


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

    # ── Stage 7: Surgical context assembly ────────────────────────────────
    context = _assemble_context_stage(intent, session_id)
    if context:
        lines.append(f"**Context:** {len(context)} chars assembled")

    # ── Stage 7.5: Constitutional policy (deep/chain only) ────────────────
    try:
        from metis_mcp.tools.guardrails import load_constitution
        constitution = load_constitution(intent["complexity"])
    except Exception:
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
