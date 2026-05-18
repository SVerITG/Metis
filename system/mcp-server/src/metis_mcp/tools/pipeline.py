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
from uuid import uuid4

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

# Import PII patterns from safety module (no circular dependency)
from metis_mcp.tools.safety import (  # noqa: E402
    _EMAIL_RE,
    _PHONE_RE,
    _PATIENT_ID_RE,
    _GPS_RE,
    _BELGIAN_NID_RE,
    _classify,
)

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

    result = {
        "session_id": session_id,
        "is_new": is_new,
        "computer": computer,
        "memory_snapshot": memory_snapshot,
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ── Stage 3: Data Guardian intercept ──────────────────────────────────────────

def _scan_safety(content: str) -> dict:
    """Run PII detection. Returns {safe, classification, warnings}."""
    warnings: list[str] = []
    if _EMAIL_RE.search(content):
        warnings.append("Email address detected")
    if _PHONE_RE.search(content):
        warnings.append("Phone number detected")
    if _PATIENT_ID_RE.search(content):
        warnings.append("Patient/case ID pattern detected")
    if _GPS_RE.search(content):
        warnings.append("High-precision GPS coordinate detected")
    if _BELGIAN_NID_RE.search(content):
        warnings.append("Belgian national ID detected")
    classification = _classify(warnings, "")
    return {"safe": len(warnings) == 0, "classification": classification, "warnings": warnings}


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

# (keyword list, agent_slug, task_type) — first match wins
_ROUTING_TABLE: list[tuple[list[str], str, str]] = [
    (["paper", "article", "literature", "pubmed", "journal", "citation", "reference"],
     "librarian", "literature"),
    (["meeting", "transcript", "audio", "attendee", "agenda"],
     "meeting-memory", "meeting"),
    (["code", "bug", "script", "shiny", "function", "error", "debug", "r script", "python"],
     "software-engineer", "code"),
    (["phd", "thesis", "chapter", "article 1", "article 2", "article 3", "dissertation"],
     "phd-architect", "phd"),
    (["write", "draft", "revise", "grammar", "paragraph", "abstract", "introduction"],
     "writing-partner", "writing"),
    (["method", "statistic", "sample", "study design", "epidem", "regression", "prevalence"],
     "methods-coach", "methods"),
    (["news", "briefing", "world events", "what happened"],
     "news-radar", "news"),
    (["ui", "ux", "design", "css", "layout", "visual"],
     "ux-engineer", "ui"),
    (["pii", "patient data", "sensitive", "protect", "gdpr"],
     "data-guardian", "safety"),
    (["idea", "brainstorm", "connect", "explore", "think"],
     "metis", "idea"),
]

_DEEP_KEYWORDS = ["review", "critique", "analyse", "analyze", "evaluate", "challenge", "assess"]
_QUICK_KEYWORDS = ["find", "get", "what is", "list", "show", "check", "status", "how many"]
_CHAIN_KEYWORDS = ["and also", "then review", "both", "multiple agents", "all three"]


def _parse_intent_stage(request: str, session_id: str) -> dict:
    """Stage 5: Classify task type, select agent(s) and complexity level."""
    lower = request.lower()
    agents: list[str] = []
    task_type = "general"

    for keywords, agent, t_type in _ROUTING_TABLE:
        if any(kw in lower for kw in keywords):
            agents.append(agent)
            task_type = t_type
            break  # deterministic — first match wins

    if not agents:
        agents = ["metis"]

    word_count = len(lower.split())
    if any(kw in lower for kw in _CHAIN_KEYWORDS):
        complexity = "chain"
    elif any(kw in lower for kw in _DEEP_KEYWORDS) or word_count > 40:
        complexity = "deep"
    elif any(kw in lower for kw in _QUICK_KEYWORDS) or word_count < 10:
        complexity = "quick"
    else:
        complexity = "standard"

    return {"agents": agents, "complexity": complexity, "task_type": task_type}


# ── Stage 6: Token budget allocation ──────────────────────────────────────────

_BUDGET_MAP = {
    "quick":    {"model": "claude-haiku-4-5-20251001", "max_tokens": 1024},
    "standard": {"model": "claude-sonnet-4-6",          "max_tokens": 4096},
    "deep":     {"model": "claude-opus-4-6",            "max_tokens": 8192},
    "chain":    {"model": "claude-opus-4-6",            "max_tokens": 8192},
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

    if not rows:
        return ""

    parts = [
        f"- [{r['title']}] {(r['summary'] or '')[:120]}"
        for r in rows
        if r["title"]
    ]
    return "Recent context:\n" + "\n".join(parts) if parts else ""


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
    ]
    if context:
        lines += ["**Context for agent:**", context, ""]
    if constitution:
        lines += ["", constitution, ""]

    return [TextContent(type="text", text="\n".join(lines))]
