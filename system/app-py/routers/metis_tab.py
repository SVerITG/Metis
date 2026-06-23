"""
routers/metis_tab.py — Metis tab routes.
"""

import datetime
import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar, db_execute

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/metis", response_class=HTMLResponse)
async def metis_tab(request: Request):
    return templates.TemplateResponse(
     request, "metis_tab.html", {"active_tab": "metis"}
 )


@router.get("/api/tab/metis", response_class=HTMLResponse)
async def metis_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "metis_tab.html", {"active_tab": "metis"}
 )


# ---------------------------------------------------------------------------
# Contextual discovery — settings surface (Tier 2)
# ---------------------------------------------------------------------------


def _discovery_ctx() -> dict:
    db_execute("CREATE TABLE IF NOT EXISTS discovery_state (key TEXT PRIMARY KEY, value TEXT)")
    db_execute("CREATE TABLE IF NOT EXISTS discovery_shown (tip_id TEXT PRIMARY KEY, shown_at TEXT)")
    en = db_query("SELECT value FROM discovery_state WHERE key='enabled'") or []
    enabled = True if not en else (en[0].get("value") != "0")
    md = db_query("SELECT value FROM discovery_state WHERE key='mode'") or []
    mode = md[0].get("value") if md else "guided"
    shown = db_scalar("SELECT COUNT(*) FROM discovery_shown", default=0) or 0
    try:
        from metis_mcp.tools.discovery import TIPS
        total = len(TIPS)
        adopted = 0
        shown_ids = [r["tip_id"] for r in (db_query("SELECT tip_id FROM discovery_shown") or [])]
        # lightweight adoption read (which discovered features now have data)
        for tid in shown_ids:
            a = TIPS.get(tid, {}).get("adopted_if")
            if a and (db_query(f"SELECT 1 FROM {a[0]} WHERE {a[1]} LIMIT 1") or []):
                adopted += 1
    except Exception:
        total, adopted = max(shown, 11), 0
    return {"d_enabled": enabled, "d_mode": mode, "d_shown": shown, "d_total": total, "d_adopted": adopted}


@router.get("/api/partial/metis/discovery", response_class=HTMLResponse)
async def metis_discovery(request: Request):
    return templates.TemplateResponse(request, "partials/metis_discovery.html", _discovery_ctx())


@router.post("/api/metis/discovery/toggle", response_class=HTMLResponse)
async def metis_discovery_toggle(request: Request):
    ctx = _discovery_ctx()
    new_val = "0" if ctx["d_enabled"] else "1"
    db_execute(
        "INSERT INTO discovery_state (key, value) VALUES ('enabled', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (new_val,),
    )
    return templates.TemplateResponse(request, "partials/metis_discovery.html", _discovery_ctx())


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/stats", response_class=HTMLResponse)
async def metis_stats(request: Request):
    today = str(datetime.date.today())
    runs_today = db_scalar(
        "SELECT COUNT(*) FROM agent_runs WHERE DATE(created_at) = ?",
        (today,),
        default=0,
    )
    tokens_today = db_scalar(
        "SELECT COALESCE(SUM(COALESCE(input_tokens,0) + COALESCE(output_tokens,0)), 0) "
        "FROM agent_runs WHERE DATE(created_at) = ?",
        (today,),
        default=0,
    )
    total_runs = db_scalar("SELECT COUNT(*) FROM agent_runs", default=0)
    active_agents = db_scalar(
        "SELECT COUNT(DISTINCT agent_slug) FROM agent_runs", default=0
    )
    return templates.TemplateResponse(
        request,
        "partials/metis_stats.html",
        {
            "runs_today": runs_today,
            "tokens_today": tokens_today,
            "total_runs": total_runs,
            "active_agents": active_agents,
        },
    )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/user", response_class=HTMLResponse)
async def metis_user(request: Request):
    today = datetime.date.today().strftime("%-d %b").upper()
    prefs = _read_user_prefs()
    display = (prefs.get("display_name") or "RESEARCHER").upper()
    return HTMLResponse(f"{display} · RESEARCH CORTEX<div style='margin-top:4px;color:var(--m-muted-soft);font-size:11px;'>SIGNED IN · {today}</div>")


@router.get("/api/partial/metis/identity", response_class=HTMLResponse)
async def metis_identity(request: Request):
    """Identity card — name, role, interests, news topics — rendered in left rail."""
    runs = db_scalar("SELECT COUNT(*) FROM agent_runs", default=0) or 0
    prefs = _read_user_prefs()
    name = prefs.get("display_name") or "Researcher"
    role = prefs.get("role") or "Senior researcher · public health"
    interests = prefs.get("interests") or []
    news_topics = prefs.get("news_topics") or []
    return templates.TemplateResponse(
        request,
        "partials/metis_identity_card.html",
        {
            "name": name,
            "initial": (name[:1].upper() if name else "S"),
            "role": role,
            "interests": interests,
            "news_topics": news_topics,
            "runs": runs,
        },
    )


# ---------------------------------------------------------------------------
# Agent runs list
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/agent-runs", response_class=HTMLResponse)
async def metis_agent_runs(request: Request, days: int = 1):
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    runs = db_query(
        "SELECT agent_slug, task_summary, created_at as started_at, "
        "COALESCE(input_tokens,0) + COALESCE(output_tokens,0) as tokens_used, status "
        "FROM agent_runs WHERE created_at >= ? "
        "ORDER BY created_at DESC LIMIT 50",
        (cutoff,),
    )
    return templates.TemplateResponse(
        request,
        "partials/metis_runs.html",
        {
            "runs": runs
        },
    )


# ---------------------------------------------------------------------------
# Registered agents (from agent-registry.json)
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/agents", response_class=HTMLResponse)
async def metis_agents(request: Request):
    agents: list[dict] = []
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        registry_path = (
            Path(rc_root) / "system" / "config" / "agent-registry.json"
        )
        if registry_path.exists():
            try:
                data = json.loads(registry_path.read_text(encoding="utf-8"))
                agents = data.get("agents", [])
            except Exception:
                pass
    return templates.TemplateResponse(
        request,
        "partials/metis_agents.html",
        {
            "agents": agents
        },
    )


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Span waterfall (Phase 5.9)
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/traces", response_class=HTMLResponse)
async def metis_traces(request: Request, hours: int = 24):
    """Return span waterfall partial for recent agent activity."""
    cutoff = (
        datetime.datetime.now() - datetime.timedelta(hours=hours)
    ).isoformat()

    # Recent runs (become root bars when no spans exist)
    runs = db_query(
        "SELECT run_id, agent_slug, task_summary, created_at, status "
        "FROM agent_runs WHERE created_at >= ? ORDER BY created_at DESC LIMIT 20",
        (cutoff,),
    )

    # All spans in window, grouped by run_id
    raw_spans = db_query(
        "SELECT span_id, parent_id, run_id, session_id, name, kind, "
        "status, start_ms, end_ms, duration_ms, error, created_at "
        "FROM agent_spans WHERE created_at >= ? ORDER BY start_ms ASC",
        (cutoff,),
        default=[],
    )

    # Group spans by run_id
    spans_by_run: dict = {}
    orphan_spans: list = []
    for s in (raw_spans or []):
        rid = s["run_id"] if s["run_id"] else None
        if rid:
            spans_by_run.setdefault(rid, []).append(dict(s))
        else:
            orphan_spans.append(dict(s))

    # Enrich runs with span data
    run_list = []
    for r in (runs or []):
        rd = dict(r)
        rd["spans"] = spans_by_run.get(r["run_id"], [])
        run_list.append(rd)

    total_spans = sum(len(v) for v in spans_by_run.values()) + len(orphan_spans)

    return templates.TemplateResponse(
        request,
        "partials/metis_traces.html",
        {
            "runs": run_list,
            "orphan_spans": orphan_spans,
            "total_spans": total_spans,
            "hours": hours,
        },
    )


@router.get("/api/partial/metis/network-policy", response_class=HTMLResponse)
async def metis_network_policy(request: Request):
    """Return an HTML badge showing current network policy; used by consent card header."""
    import json

    policy = "normal"
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        p = Path(rc_root) / "system" / "config" / "network-policy.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                policy = data.get("policy", "normal")
            except Exception:
                pass

    icons = {"strict": "bi-shield-lock text-warning", "offline": "bi-wifi-off text-danger", "normal": "bi-wifi text-success"}
    icon_cls = icons.get(policy, "bi-wifi text-success")
    label = {"strict": "Strict", "offline": "Offline", "normal": "Normal"}.get(policy, policy.title())

    html = (
        f'<span class="badge bg-light text-dark border" id="network-policy-badge" '
        f'hx-get="/api/partial/metis/network-policy" hx-trigger="every 30s" hx-swap="outerHTML">'
        f'<i class="bi {icon_cls} me-1"></i>{label}</span>'
    )
    return HTMLResponse(html)


@router.get("/api/partial/metis/consent", response_class=HTMLResponse)
async def metis_consent(request: Request, limit: int = 20):
    """Return consent ledger partial."""
    rows = db_query(
        "SELECT id, timestamp, action, data_classification, agent_slug, notes "
        "FROM consent_ledger ORDER BY timestamp DESC LIMIT ?",
        (limit,),
        default=[],
    )
    return templates.TemplateResponse(
        request,
        "partials/metis_consent.html",
        {"events": [dict(r) for r in (rows or [])]},
    )


def _user_prefs_path() -> Path:
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    base = Path(rc_root) / "system" / "config" if rc_root else Path("/tmp")
    base.mkdir(parents=True, exist_ok=True)
    return base / "user-preferences.json"


def _read_user_prefs() -> dict:
    p = _user_prefs_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_user_prefs(data: dict) -> None:
    p = _user_prefs_path()
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


@router.post("/api/model/active")
async def set_active_model(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    slug = (payload.get("slug") or "").strip().lower()
    if slug not in {"haiku", "sonnet", "opus"}:
        return JSONResponse(
            {"status": "error", "message": f"Unknown model slug: {slug}"},
            status_code=400,
        )
    prefs = _read_user_prefs()
    prefs["active_model"] = slug
    prefs["active_model_set_at"] = datetime.datetime.now().isoformat()
    try:
        _write_user_prefs(prefs)
        return JSONResponse({"status": "ok", "slug": slug})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/api/identity/rename")
async def identity_rename(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    name = (payload.get("name") or "").strip()
    if not name or len(name) > 80:
        return JSONResponse(
            {"status": "error", "message": "Name must be 1–80 characters."},
            status_code=400,
        )
    prefs = _read_user_prefs()
    prefs["display_name"] = name
    prefs["display_name_set_at"] = datetime.datetime.now().isoformat()
    try:
        _write_user_prefs(prefs)
        return JSONResponse({"status": "ok", "name": name})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/api/partial/metis/memory-stream", response_class=HTMLResponse)
async def metis_memory_stream(
    request: Request,
    limit: int = 40,
    days: int = 30,
    type: str = "all",
):
    """Chronological stream of typed observations from episodic memory + reflexions.

    `type` can be "all" or one of discovery/decision/implementation/issue/note/idea.
    """
    import json as _json

    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    type_norm = (type or "all").strip().lower()

    # Memory entries (discovery/decision/implementation/issue/note/idea)
    if type_norm in {"discovery", "decision", "implementation", "issue", "note", "idea"}:
        raw_episodic = db_query(
            "SELECT entry_id AS id, entry_type AS event_type, "
            "COALESCE(title, summary, '') AS content, topics AS metadata, created_at "
            "FROM memory_entries WHERE created_at >= ? AND entry_type = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (cutoff, type_norm, limit),
            default=[],
        ) or []
    else:
        raw_episodic = db_query(
            "SELECT entry_id AS id, entry_type AS event_type, "
            "COALESCE(title, summary, '') AS content, topics AS metadata, created_at "
            "FROM memory_entries WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
            (cutoff, limit),
            default=[],
        ) or []

    # Reflexion log (end-of-run self-critiques)
    raw_reflexions = db_query(
        "SELECT reflexion_id as id, agent_slug, could_improve as content, created_at "
        "FROM reflexion_log WHERE created_at >= ? AND could_improve != '' "
        "ORDER BY created_at DESC LIMIT 10",
        (cutoff,),
        default=[],
    ) or []

    entries: list[dict] = []
    for r in raw_episodic:
        row = dict(r)
        meta: dict = {}
        try:
            meta = _json.loads(row.get("metadata") or "{}")
        except Exception:
            pass
        row["classification"] = meta.get("classification") or row.get("event_type") or "note"
        row["agent_slug"]      = meta.get("agent_slug") or ""
        row["concepts"]        = meta.get("concepts") or []
        entries.append(row)

    for r in raw_reflexions:
        row = dict(r)
        row["classification"] = "note"
        row["event_type"]     = "note"
        row["concepts"]       = []
        row["source"]         = "reflexion"
        entries.append(row)

    # Sort all entries newest first
    entries.sort(key=lambda x: (x.get("created_at") or ""), reverse=True)
    entries = entries[:limit]

    return templates.TemplateResponse(
        request,
        "partials/metis_memory_stream.html",
        {"entries": entries, "days": days},
    )


@router.get("/api/partial/metis/improvement", response_class=HTMLResponse)
async def metis_improvement(request: Request, days: int = 14):
    """Self-improvement loop surface: applied learnings + themed reflexions + drafts."""
    themes: dict = {"window_days": days, "agents": [], "totals": {"reflexions": 0, "agents": 0}}
    proposals: list[dict] = []
    learned: list[dict] = []
    try:
        from metis_mcp.tools.improvement import aggregate_reflexions
        themes = aggregate_reflexions(days=days)
    except Exception:
        pass
    try:
        rows = db_query(
            "SELECT id, agent_slug, proposed_at, rationale, status, "
            "SUBSTR(proposed_content, 1, 280) AS preview "
            "FROM skill_improvement_proposals "
            "WHERE status IN ('draft','pending') "
            "ORDER BY proposed_at DESC LIMIT 12",
            default=[],
        ) or []
        proposals = [dict(r) for r in rows]
    except Exception:
        proposals = []
    # "What I've learned" — most recently applied proposals
    try:
        applied_rows = db_query(
            "SELECT id, agent_slug, rationale, applied_at, proposed_at "
            "FROM skill_improvement_proposals "
            "WHERE status = 'applied' "
            "ORDER BY COALESCE(applied_at, proposed_at) DESC LIMIT 8",
            default=[],
        ) or []
        learned = [dict(r) for r in applied_rows]
    except Exception:
        learned = []

    # Recent reflexion entries — the raw "went_well / could_improve" text Metis
    # has been recording. Surfacing these lets the user see the actual session
    # quality signal, not only the keyword themes.
    recent_reflexions: list[dict] = []
    try:
        rrows = db_query(
            "SELECT reflexion_id as id, agent_slug, went_well, could_improve, "
            "missing_context, tool_wishes, created_at "
            "FROM reflexion_log ORDER BY reflexion_id DESC LIMIT 5",
            default=[],
        ) or []
        recent_reflexions = [dict(r) for r in rrows]
    except Exception:
        recent_reflexions = []

    return templates.TemplateResponse(
        request,
        "partials/metis_improvement.html",
        {
            "themes": themes,
            "proposals": proposals,
            "learned": learned,
            "recent_reflexions": recent_reflexions,
            "days": days,
        },
    )


@router.post("/api/improvement/draft/{agent_slug}")
async def improvement_draft(agent_slug: str, request: Request):
    """Queue a self-improvement draft for an agent (status='draft')."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    days = int(payload.get("days") or 14)
    try:
        from metis_mcp.tools.improvement import draft_self_improvement_proposal
        result = draft_self_improvement_proposal(agent_slug, days=days)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/api/improvement/promote/{proposal_id}")
async def improvement_promote(proposal_id: int):
    """Promote a draft proposal to pending (review-staging step, no file write)."""
    from db import db_execute
    try:
        db_execute(
            "UPDATE skill_improvement_proposals SET status = 'pending' "
            "WHERE id = ? AND status = 'draft'",
            (proposal_id,),
        )
        return JSONResponse({"status": "ok", "proposal_id": proposal_id})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/api/improvement/preview/{proposal_id}")
async def improvement_preview(proposal_id: int):
    """Return the current vs proposed skill.md content as a unified diff.

    Used by the dashboard to show the user exactly what would change before
    they hit Apply.
    """
    import difflib
    from db import db_query
    rows = db_query(
        "SELECT id, agent_slug, status, current_content, proposed_content, rationale "
        "FROM skill_improvement_proposals WHERE id = ?",
        (proposal_id,),
    )
    if not rows:
        return JSONResponse({"status": "error", "message": "not found"}, status_code=404)
    p = rows[0]
    current = p.get("current_content") or ""
    proposed = p.get("proposed_content") or ""
    diff = "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            proposed.splitlines(),
            fromfile=f"{p['agent_slug']}/skill.md (current)",
            tofile=f"{p['agent_slug']}/skill.md (proposed)",
            lineterm="",
        )
    )
    return JSONResponse(
        {
            "status": "ok",
            "proposal_id": p["id"],
            "agent_slug": p["agent_slug"],
            "proposal_status": p["status"],
            "rationale": p.get("rationale") or "",
            "diff": diff,
            "added_lines": sum(
                1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
            ),
            "removed_lines": sum(
                1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")
            ),
        }
    )


@router.post("/api/improvement/apply/{proposal_id}")
async def improvement_apply(proposal_id: int):
    """Apply a promoted proposal: write to skill.md (with backup), mark applied.

    The previous skill.md is preserved as `skill.md.bak.<timestamp>` next to
    the original so the change is always reversible. Returns the new status,
    the backup path, and the applied_at timestamp.
    """
    try:
        from metis_mcp.tools.improvement import apply_proposal
        result = apply_proposal(proposal_id)
        status_code = 200 if result.get("status") == "ok" else 400
        return JSONResponse(result, status_code=status_code)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/api/improvement/reject/{proposal_id}")
async def improvement_reject(proposal_id: int, request: Request):
    """Mark a proposal rejected without applying it."""
    from db import db_execute
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    note = (payload.get("note") or "").strip()[:500]
    try:
        db_execute(
            "UPDATE skill_improvement_proposals SET status = 'rejected', reviewer_note = ? "
            "WHERE id = ? AND status IN ('draft','pending')",
            (note, proposal_id),
        )
        return JSONResponse({"status": "ok", "proposal_id": proposal_id})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


def _mask_home(p) -> str:
    """In demo mode, hide the real home directory + username in displayed paths
    so screenshots/recordings don't leak them. No-op outside demo mode."""
    s = str(p)
    if os.environ.get("METIS_DEMO") != "1":
        return s
    import re as _re
    home = str(Path.home())
    if home and s.startswith(home):
        s = "~" + s[len(home):]
    s = _re.sub(r"/home/[^/]+/", "~/", s)
    s = _re.sub(r"[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/]", "~/", s)
    return s


@router.get("/api/partial/metis/system-info", response_class=HTMLResponse)
async def metis_system_info(request: Request):
    rc_root = os.environ.get("METIS_RC_ROOT", "unknown")

    db_path = "unknown"
    db_size_kb = 0
    try:
        from db import get_db_path

        p = get_db_path()
        db_path = str(p)
        db_size_kb = round(p.stat().st_size / 1024)
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/metis_system_info.html",
        {
            "rc_root": _mask_home(rc_root),
            "db_path": _mask_home(db_path),
            "db_size_kb": db_size_kb,
        },
    )


# ---------------------------------------------------------------------------
# Token monitor — by agent, by model
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/token-monitor", response_class=HTMLResponse)
async def metis_token_monitor(request: Request, days: int = 7):
    """Token usage breakdown — totals, by agent, by model — over a window."""
    today = str(datetime.date.today())
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()

    runs_today = db_scalar(
        "SELECT COUNT(*) FROM agent_runs WHERE DATE(created_at) = ?",
        (today,),
        default=0,
    ) or 0
    tokens_today = db_scalar(
        "SELECT COALESCE(SUM(COALESCE(input_tokens,0) + COALESCE(output_tokens,0)), 0) "
        "FROM agent_runs WHERE DATE(created_at) = ?",
        (today,),
        default=0,
    ) or 0
    runs_window = db_scalar(
        "SELECT COUNT(*) FROM agent_runs WHERE created_at >= ?",
        (cutoff,),
        default=0,
    ) or 0
    tokens_window = db_scalar(
        "SELECT COALESCE(SUM(COALESCE(input_tokens,0) + COALESCE(output_tokens,0)), 0) "
        "FROM agent_runs WHERE created_at >= ?",
        (cutoff,),
        default=0,
    ) or 0

    by_agent_rows = db_query(
        "SELECT agent_slug, "
        "COALESCE(SUM(input_tokens),0) AS input_tokens, "
        "COALESCE(SUM(output_tokens),0) AS output_tokens, "
        "COUNT(*) AS runs "
        "FROM agent_runs WHERE created_at >= ? AND agent_slug IS NOT NULL "
        "GROUP BY agent_slug "
        "ORDER BY (COALESCE(SUM(input_tokens),0)+COALESCE(SUM(output_tokens),0)) DESC "
        "LIMIT 12",
        (cutoff,),
        default=[],
    ) or []

    by_agent = []
    for r in by_agent_rows:
        d = dict(r)
        d["total"] = int(d.get("input_tokens") or 0) + int(d.get("output_tokens") or 0)
        by_agent.append(d)

    max_agent_total = max((a["total"] for a in by_agent), default=1) or 1
    for a in by_agent:
        a["pct"] = round(100.0 * a["total"] / max_agent_total, 1)

    by_model_rows = db_query(
        "SELECT COALESCE(NULLIF(model,''),'unspecified') AS model, "
        "COALESCE(SUM(input_tokens),0) AS input_tokens, "
        "COALESCE(SUM(output_tokens),0) AS output_tokens, "
        "COUNT(*) AS runs "
        "FROM agent_runs WHERE created_at >= ? "
        "GROUP BY COALESCE(NULLIF(model,''),'unspecified') "
        "ORDER BY (COALESCE(SUM(input_tokens),0)+COALESCE(SUM(output_tokens),0)) DESC",
        (cutoff,),
        default=[],
    ) or []
    by_model = []
    for r in by_model_rows:
        d = dict(r)
        d["total"] = int(d.get("input_tokens") or 0) + int(d.get("output_tokens") or 0)
        by_model.append(d)
    max_model_total = max((m["total"] for m in by_model), default=1) or 1
    for m in by_model:
        m["pct"] = round(100.0 * m["total"] / max_model_total, 1)

    # Per-day breakdown for the last 7 days (fills missing days with 0)
    day_labels_list = []
    day_map: dict = {}
    today_dt = datetime.date.today()
    for i in range(6, -1, -1):
        d = today_dt - datetime.timedelta(days=i)
        day_str = str(d)
        day_labels_list.append(day_str)
        day_map[day_str] = {
            "day": day_str,
            "runs": 0,
            "tokens": 0,
            "label": d.strftime("%a"),
            "is_today": (d == today_dt),
        }
    day_rows = db_query(
        "SELECT DATE(created_at) AS day, COUNT(*) AS runs, "
        "COALESCE(SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0)),0) AS tokens "
        "FROM agent_runs WHERE DATE(created_at) >= ? "
        "GROUP BY DATE(created_at)",
        (day_labels_list[0],),
        default=[],
    ) or []
    for row in day_rows:
        dr = dict(row)
        dkey = dr.get("day") or ""
        if dkey in day_map:
            day_map[dkey]["runs"] = int(dr.get("runs") or 0)
            day_map[dkey]["tokens"] = int(dr.get("tokens") or 0)
    by_day = list(day_map.values())
    max_day_tokens = max((d["tokens"] for d in by_day), default=1) or 1
    for d in by_day:
        d["pct"] = round(100.0 * d["tokens"] / max_day_tokens, 1)

    prefs = _read_user_prefs()
    active_model = prefs.get("active_model") or "sonnet"

    return templates.TemplateResponse(
        request,
        "partials/metis_token_monitor.html",
        {
            "runs_today": runs_today,
            "tokens_today": tokens_today,
            "runs_window": runs_window,
            "tokens_window": tokens_window,
            "days": days,
            "by_agent": by_agent,
            "by_model": by_model,
            "by_day": by_day,
            "active_model": active_model,
        },
    )


# ---------------------------------------------------------------------------
# Agent directory — full descriptions + when to use
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/agent-directory", response_class=HTMLResponse)
async def metis_agent_directory(request: Request):
    """Read agent-registry.json and return rich agent cards with run history."""
    agents: list[dict] = []
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        registry_path = (
            Path(rc_root) / "system" / "config" / "agent-registry.json"
        )
        if registry_path.exists():
            try:
                data = json.loads(registry_path.read_text(encoding="utf-8"))
                agents = data.get("agents", [])
            except Exception:
                pass

    # Merge in run history so the template can show warm/dormant status
    try:
        run_rows = db_query(
            "SELECT agent_slug, COUNT(*) as runs, MAX(created_at) as last_run "
            "FROM agent_runs GROUP BY agent_slug"
        )
        run_map = {r["agent_slug"]: r for r in run_rows}
    except Exception:
        run_map = {}

    for a in agents:
        slug = a.get("slug", "")
        stats = run_map.get(slug)
        a["run_count"] = stats["runs"] if stats else 0
        a["last_run"] = (stats["last_run"] or "")[:10] if stats else ""

    return templates.TemplateResponse(
        request,
        "partials/metis_agent_directory.html",
        {"agents": agents, "agent_count": len(agents)},
    )


# ---------------------------------------------------------------------------
# Memory overview — stats + filter chips + archive control
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/memory-overview", response_class=HTMLResponse)
async def metis_memory_overview(request: Request):
    """Stats + filter chips + archive setting for the memory surface."""
    total_memories = db_scalar(
        "SELECT COUNT(*) FROM memory_entries", default=0
    ) or 0
    week_cutoff = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    week_count = db_scalar(
        "SELECT COUNT(*) FROM memory_entries WHERE created_at >= ?",
        (week_cutoff,),
        default=0,
    ) or 0
    oldest = db_scalar(
        "SELECT MIN(created_at) FROM memory_entries", default=""
    ) or ""

    by_type_rows = db_query(
        "SELECT entry_type AS event_type, COUNT(*) AS n FROM memory_entries GROUP BY entry_type",
        default=[],
    ) or []
    by_type = {(r.get("event_type") or "note"): int(r.get("n") or 0) for r in by_type_rows}

    prefs = _read_user_prefs()
    archive_days = prefs.get("memory_archive_days", 90)

    return templates.TemplateResponse(
        request,
        "partials/metis_memory_overview.html",
        {
            "total_memories": total_memories,
            "week_count": week_count,
            "oldest": (oldest or "")[:10],
            "by_type": by_type,
            "archive_days": archive_days,
        },
    )


# ---------------------------------------------------------------------------
# Memory retrieval debugger (M5.9 / B2)

@router.get("/api/partial/metis/memory-debug", response_class=HTMLResponse)
async def metis_memory_debug(request: Request, q: str = "", layers: str = "episodic,semantic,procedural,session"):
    """Retrieval debugger: run a query and show ranked results with scores."""
    import struct as _struct

    results: list[dict] = []
    error: str = ""
    has_vec = False

    requested = {l.strip() for l in layers.split(",") if l.strip()}
    # Map "session" → episodic filter
    session_only = "session" in requested and requested == {"session"}

    if q.strip():
        from db import get_db_path
        db_path = get_db_path()

        # Try vector search via sqlite-vec
        try:
            import sys as _sys
            import sqlite3 as _sqlite3
            import sqlite_vec as _svec

            def _encode(v: list) -> bytes:
                return _struct.pack(f"{len(v)}f", *v)

            conn = _sqlite3.connect(str(db_path))
            conn.row_factory = _sqlite3.Row
            conn.enable_load_extension(True)
            _svec.load(conn)
            conn.enable_load_extension(False)

            # Embed query
            _sys.path.insert(0, str(db_path.parent.parent.parent / "mcp-server" / "src"))
            from metis_mcp.embeddings import embed_query as _eq
            qvec = _eq(q)
            qbytes = _encode(qvec)
            has_vec = True
            TOP = 8

            if "episodic" in requested or "session" in requested:
                type_filter = "AND event_type = 'session_summary'" if session_only else ""
                rows = conn.execute(
                    f"""SELECT e.id, e.event_type, e.content, e.metadata, e.created_at,
                               v.distance, 'episodic' AS layer
                          FROM vec_episodic v
                          JOIN episodic_memory e ON e.id = v.rowid
                         WHERE v.embedding MATCH ? AND k = ?
                               {type_filter}
                         ORDER BY v.distance""",
                    (qbytes, TOP),
                ).fetchall()
                for r in rows:
                    results.append({
                        "layer": "session" if r["event_type"] == "session_summary" else "episodic",
                        "type": r["event_type"],
                        "content": (r["content"] or "")[:200],
                        "score": round(1 - float(r["distance"]), 4),
                        "date": (r["created_at"] or "")[:10],
                        "raw_distance": round(float(r["distance"]), 4),
                    })

            if "semantic" in requested:
                rows = conn.execute(
                    """SELECT s.id, s.concept, s.definition, s.created_at,
                              v.distance, 'semantic' AS layer
                         FROM vec_semantic v
                         JOIN semantic_memory s ON s.id = v.rowid
                        WHERE v.embedding MATCH ? AND k = ?
                        ORDER BY v.distance""",
                    (qbytes, TOP),
                ).fetchall()
                for r in rows:
                    results.append({
                        "layer": "semantic",
                        "type": "concept",
                        "content": f"{r['concept']}: {(r['definition'] or '')[:160]}",
                        "score": round(1 - float(r["distance"]), 4),
                        "date": (r["created_at"] or "")[:10],
                        "raw_distance": round(float(r["distance"]), 4),
                    })

            if "procedural" in requested:
                rows = conn.execute(
                    """SELECT p.id, p.procedure_name, p.steps, p.created_at,
                              v.distance, 'procedural' AS layer
                         FROM vec_procedural v
                         JOIN procedural_memory p ON p.id = v.rowid
                        WHERE v.embedding MATCH ? AND k = ?
                        ORDER BY v.distance""",
                    (qbytes, TOP),
                ).fetchall()
                for r in rows:
                    results.append({
                        "layer": "procedural",
                        "type": "procedure",
                        "content": f"{r['procedure_name']}: {(r['steps'] or '')[:160]}",
                        "score": round(1 - float(r["distance"]), 4),
                        "date": (r["created_at"] or "")[:10],
                        "raw_distance": round(float(r["distance"]), 4),
                    })

            conn.close()

        except Exception as exc:
            error = str(exc)
            has_vec = False

        # Keyword fallback if vec failed
        if not has_vec and not results:
            try:
                like = f"%{q}%"
                erows = db_query(
                    "SELECT id, event_type, content, created_at FROM episodic_memory "
                    "WHERE content LIKE ? ORDER BY created_at DESC LIMIT 8",
                    (like,), default=[],
                ) or []
                for r in erows:
                    results.append({
                        "layer": "session" if r.get("event_type") == "session_summary" else "episodic",
                        "type": r.get("event_type") or "note",
                        "content": (r.get("content") or "")[:200],
                        "score": None,
                        "date": (r.get("created_at") or "")[:10],
                        "raw_distance": None,
                    })
            except Exception:
                pass

        # Sort by score desc
        results.sort(key=lambda x: (x.get("score") or 0), reverse=True)

    return templates.TemplateResponse(
        request,
        "partials/metis_memory_debug.html",
        {
            "q": q,
            "layers": layers,
            "results": results,
            "has_vec": has_vec,
            "error": error,
        },
    )


# ---------------------------------------------------------------------------
# Settings — theme + memory archive
# ---------------------------------------------------------------------------


@router.post("/api/settings/theme")
async def set_theme(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    theme = (payload.get("theme") or "").strip().lower()
    if theme not in {"archive", "fieldwork", "paper", "observatory", "midnight", "cavern"}:
        return JSONResponse(
            {"status": "error", "message": f"Unknown theme: {theme}"},
            status_code=400,
        )
    prefs = _read_user_prefs()
    prefs["theme"] = theme
    prefs["theme_set_at"] = datetime.datetime.now().isoformat()
    try:
        _write_user_prefs(prefs)
        return JSONResponse({"status": "ok", "theme": theme})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/api/settings/memory")
async def set_memory_settings(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    raw = payload.get("archive_days")
    try:
        days = int(raw) if raw not in (None, "", "never") else 0
    except Exception:
        return JSONResponse(
            {"status": "error", "message": "archive_days must be an integer or 'never'"},
            status_code=400,
        )
    if days not in (0, 30, 60, 90, 180, 365):
        return JSONResponse(
            {"status": "error", "message": "archive_days must be one of 0, 30, 60, 90, 180, 365"},
            status_code=400,
        )
    prefs = _read_user_prefs()
    prefs["memory_archive_days"] = days
    prefs["memory_archive_set_at"] = datetime.datetime.now().isoformat()
    try:
        _write_user_prefs(prefs)
        return JSONResponse({"status": "ok", "archive_days": days})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Identity update — display name + interests + news topics
# ---------------------------------------------------------------------------


def _split_csv(raw) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()][:24]
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace("\n", ",").split(",")]
        return [p for p in parts if p][:24]
    return []


@router.post("/api/identity/update")
async def identity_update(request: Request):
    """Update name, role, interests, news_topics in user-preferences.json."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    prefs = _read_user_prefs()

    name = (payload.get("name") or "").strip()
    if name:
        if len(name) > 80:
            return JSONResponse(
                {"status": "error", "message": "Name must be 1–80 characters."},
                status_code=400,
            )
        prefs["display_name"] = name

    role = (payload.get("role") or "").strip()
    if "role" in payload:
        prefs["role"] = role[:120]

    if "interests" in payload:
        prefs["interests"] = _split_csv(payload.get("interests"))
    if "news_topics" in payload:
        prefs["news_topics"] = _split_csv(payload.get("news_topics"))

    prefs["identity_updated_at"] = datetime.datetime.now().isoformat()
    try:
        _write_user_prefs(prefs)
        return JSONResponse({
            "status": "ok",
            "display_name": prefs.get("display_name"),
            "role": prefs.get("role"),
            "interests": prefs.get("interests", []),
            "news_topics": prefs.get("news_topics", []),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# API keys — read/write the system/.env file
# ---------------------------------------------------------------------------

_KNOWN_KEY_LABELS: dict[str, str] = {
    "ANTHROPIC_API_KEY": "Anthropic",
    "ANTHROPIC_API_KEY_WORK": "Anthropic (work account)",
    "ZOTERO_API_KEY": "Zotero API key",
    "ZOTERO_USER_ID": "Zotero user ID",
}

_SENSITIVE_KEYS = {"ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY_WORK", "ZOTERO_API_KEY"}


def _env_path() -> Path:
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        return Path(rc_root) / "system" / ".env"
    return Path(__file__).resolve().parent.parent.parent.parent / "system" / ".env"


def _read_env() -> dict[str, str]:
    """Parse system/.env into {KEY: value}."""
    p = _env_path()
    if not p.exists():
        return {}
    result: dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_env(env: dict[str, str]) -> None:
    """Write dict back to system/.env (sorted, KEY=value format)."""
    p = _env_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in sorted(env.items())]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mask_value(name: str, value: str) -> str:
    """Mask sensitive key values for display; show non-sensitive values in full."""
    if not value:
        return ""
    if name in _SENSITIVE_KEYS or "KEY" in name or "SECRET" in name or "TOKEN" in name:
        if len(value) <= 8:
            return "·" * len(value)
        return value[:8] + "·" * min(len(value) - 8, 24)
    return value  # non-sensitive values (e.g. user IDs) shown in full


@router.get("/api/partial/metis/api-keys", response_class=HTMLResponse)
async def metis_api_keys(request: Request):
    """Return the API keys management panel."""
    env = _read_env()
    keys = []
    shown: set[str] = set()
    for k, label in _KNOWN_KEY_LABELS.items():
        shown.add(k)
        keys.append({
            "name": k,
            "label": label,
            "present": k in env,
            "masked": _mask_value(k, env.get(k, "")),
        })
    for k, v in sorted(env.items()):
        if k not in shown:
            keys.append({
                "name": k,
                "label": k,
                "present": True,
                "masked": _mask_value(k, v),
            })
    return templates.TemplateResponse(
        request,
        "partials/metis_api_keys.html",
        {"keys": keys},
    )


@router.post("/api/settings/api-key")
async def set_api_key(request: Request):
    """Add or replace a key in system/.env."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    name = (payload.get("name") or "").strip().upper().replace(" ", "_")
    value = (payload.get("value") or "").strip()
    if not name:
        return JSONResponse({"status": "error", "message": "Key name is required."}, status_code=400)
    if not value:
        return JSONResponse({"status": "error", "message": "Key value is required."}, status_code=400)
    if len(name) > 80 or len(value) > 512:
        return JSONResponse({"status": "error", "message": "Name or value too long."}, status_code=400)
    env = _read_env()
    env[name] = value
    try:
        _write_env(env)
        # Apply to the RUNNING process immediately so the key works without a
        # restart — otherwise the user pastes a key, nothing changes in this
        # process, and the banner keeps nagging ("it keeps asking for my key").
        import os as _os
        _os.environ[name] = value
        return JSONResponse({"status": "ok", "name": name, "masked": _mask_value(name, value)})
    except Exception as e2:
        return JSONResponse({"status": "error", "message": str(e2)}, status_code=500)


@router.delete("/api/settings/api-key/{name}")
async def delete_api_key(name: str):
    """Remove a key from system/.env."""
    name = name.strip().upper()
    if not name:
        return JSONResponse({"status": "error", "message": "Key name required."}, status_code=400)
    env = _read_env()
    if name not in env:
        return JSONResponse({"status": "error", "message": f"{name} not found."}, status_code=404)
    del env[name]
    try:
        _write_env(env)
        return JSONResponse({"status": "ok", "removed": name})
    except Exception as e2:
        return JSONResponse({"status": "error", "message": str(e2)}, status_code=500)


# ---------------------------------------------------------------------------
# Claude Code / Desktop integration — mode detection + CLAUDE.md management
# ---------------------------------------------------------------------------

_CLAUDE_MD_MARKER = "You are Metis — always, in every conversation"
_CLAUDE_MD_PATH = Path.home() / ".claude" / "CLAUDE.md"


def _detect_integration_mode() -> str:
    """Return 'background' if CLAUDE.md has always-on Metis, else 'invoke'."""
    try:
        if _CLAUDE_MD_PATH.exists():
            content = _CLAUDE_MD_PATH.read_text(encoding="utf-8")
            if _CLAUDE_MD_MARKER in content:
                return "background"
    except Exception:
        pass
    return "invoke"


def _build_claude_md(prefs: dict) -> str:
    """Build the always-on Metis CLAUDE.md content from current user profile."""
    name = prefs.get("display_name") or "Researcher"
    role = prefs.get("role") or "Senior researcher"
    interests = prefs.get("interests") or []
    news_topics = prefs.get("news_topics") or []
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    interests_str = ", ".join(interests) if interests else "(not set)"
    news_str = ", ".join(news_topics) if news_topics else "(not set)"
    return f"""# Metis — Global Claude Code Configuration

**Owner:** {name}
**Research Cortex root:** `{rc_root}/`
**Database:** `{rc_root}/system/app/data/metis.sqlite`

---

## You are Metis — always, in every conversation

You do not need to be invoked. You are Metis by default in every Claude Code conversation, from the first message, in every directory.

**Read `metis/system/config/metis-persona.md` before composing your first response in any session.** It is the complete guide to your voice and tone. The key principle: {name} is not a technical person. Speak to them like a warm, knowledgeable friend — plain English, patient, clear, never condescending. The user's name is **{name}**. Never call them anything else.

**To opt out:** If {name} starts a message with `/direct`, `direct:`, or `plain Claude`, respond as standard Claude Code without Metis routing or persona for that message only. The next message returns to Metis mode.

---

## At the start of every session

Call `get_user_profile()` as soon as you have a substantive task. Use the result to personalise routing, search context, and output framing.

{name}'s current profile (cached — `get_user_profile()` returns the live version):
- **Role:** {role}
- **Interests:** {interests_str}
- **News monitoring:** {news_str}

---

## How you work

You receive requests, identify which specialist handles it best, hand it off, and come back with the result. Explain what you're doing in one plain sentence. For quick questions and direct technical tasks, just answer — no overhead.

**Routing logic:**
1. Call `get_user_profile()` to load interests and news preferences
2. Identify what the request needs
3. Pick the right specialist — or chain two if genuinely needed
4. Execute, record the output, come back with the result

**Complexity guide:**
- Quick question → handle directly
- Single-domain task → one specialist
- Deep analysis → specialist at depth
- Ambiguous → ask one clarifying question

---

## Output contract

Every substantive piece of work: saved to `outputs/reviews/[agent-slug]/YYYY-MM-DD_[topic].md` and logged to `agent_runs`.

---

## After every agent run — write a reflexion

After any task involving an agent run (not simple Q&A), call `write_reflexion()` immediately:

```
write_reflexion(
  session_id="<uuid>",
  agent_slug="<primary agent slug>",
  went_well="<1 sentence>",
  could_improve="<1 sentence>",
  missing_context="<what was unavailable>",
  tool_wishes="<tools that would have helped>"
)
```

---

## MCP tools

The Metis MCP server (`metis-rc`) is registered globally. Always attempt tool calls immediately. Fall back gracefully only if a call actually fails.

---

## Agent routing

| Request type | Agent |
|---|---|
| Paper, article, source | `/librarian` |
| Meeting note, transcript | `/meeting-memory` |
| Code, bug, R/Python | `/software-engineer` |
| DHIS2 | `/dhis2-expert` |
| PhD structure | `/phd-architect` |
| Statistical method | `/methods-coach` |
| News, briefing | `/news-radar` |
| New app or tool | `/builder` |
| Extend Metis | `/rc-builder` |
| Study design, epi | `/epidemiologist` |
| Dataset, cleaning | `/data-analyst` |
| Morning briefing | `/metis-morning` |
| Status overview | `/metis-status` |
| Unclear | Ask one clarifying question |
"""


@router.get("/api/partial/metis/integration", response_class=HTMLResponse)
async def metis_integration(request: Request):
    """Claude Code + Desktop integration status and mode toggle."""
    mode = _detect_integration_mode()
    claude_md_exists = _CLAUDE_MD_PATH.exists()
    prefs = _read_user_prefs()

    # Build the Claude Desktop system prompt from current prefs
    name = prefs.get("display_name") or "Researcher"
    role = prefs.get("role") or "Senior researcher"
    interests = ", ".join(prefs.get("interests") or []) or "(not set)"
    news_topics = ", ".join(prefs.get("news_topics") or []) or "(not set)"
    desktop_prompt = f"""You are Metis — {name}'s research companion. You are active by default in every conversation in this project.

{name}'s name is {name}. Never call them anything else. Speak in plain English, warm and patient. No jargon without explanation. No corporate filler. No exclamation marks.

Profile:
- Role: {role}
- Interests: {interests}
- News monitoring: {news_topics}

How you work:
- For research requests: identify the right specialist lens (literature, methodology, writing, statistics, news), apply it, record the output
- For quick questions: answer directly, no overhead
- For ambiguous requests: ask one clarifying question
- If MCP tools are connected: call get_user_profile() at the start of personalised work for the live profile

To opt out of Metis mode for one message: start it with "direct:" and respond as plain Claude."""

    return templates.TemplateResponse(
        request,
        "partials/metis_integration.html",
        {
            "mode": mode,
            "claude_md_exists": claude_md_exists,
            "claude_md_path": _mask_home(str(_CLAUDE_MD_PATH)),
            "desktop_prompt": desktop_prompt,
            "user_name": name,
        },
    )


@router.post("/api/settings/claude-code-mode")
async def set_claude_code_mode(request: Request):
    """Activate background layer mode (write CLAUDE.md) or revert to invoke mode."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    mode = (payload.get("mode") or "").strip().lower()
    if mode not in {"background", "invoke"}:
        return JSONResponse({"status": "error", "message": "mode must be 'background' or 'invoke'"}, status_code=400)

    prefs = _read_user_prefs()

    if mode == "background":
        content = _build_claude_md(prefs)
        try:
            _CLAUDE_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CLAUDE_MD_PATH.write_text(content, encoding="utf-8")
            return JSONResponse({"status": "ok", "mode": "background", "path": str(_CLAUDE_MD_PATH)})
        except Exception as e3:
            return JSONResponse({"status": "error", "message": str(e3)}, status_code=500)
    else:
        # Invoke mode: remove the always-on marker by rewriting without it,
        # or write a minimal routing-only version
        minimal = f"""# Metis — Global Claude Code Configuration

**Research Cortex root:** `{os.environ.get('METIS_RC_ROOT', '')}/`

## Voice

{prefs.get('display_name', 'Researcher')} is the user. Always speak in plain English, warm and patient. The user's name is **{prefs.get('display_name', 'Researcher')}**. Never address them as anything else.

## MCP tools

The Metis MCP server (`metis-rc`) is registered globally. Always attempt MCP tool calls immediately.

## Routing

Use `/metis` for any research or knowledge task. Use project-specific skills directly when you know the right agent:
- `/librarian` — papers, literature, references
- `/epidemiologist` — study design, methods review
- `/methods-coach` — statistics, R code
- `/writing-partner` — manuscript, prose
- `/software-engineer` — code, debugging
- `/metis-morning` — daily briefing
- `/metis-status` — quick status overview
"""
        try:
            _CLAUDE_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CLAUDE_MD_PATH.write_text(minimal, encoding="utf-8")
            return JSONResponse({"status": "ok", "mode": "invoke", "path": str(_CLAUDE_MD_PATH)})
        except Exception as e3:
            return JSONResponse({"status": "error", "message": str(e3)}, status_code=500)


# ---------------------------------------------------------------------------
# Content packs — install / remove / list
# ---------------------------------------------------------------------------

@router.get("/api/partial/metis/content-packs", response_class=HTMLResponse)
async def content_packs_partial(request: Request):
    """Show installed content packs with toggle controls."""
    packs = db_query(
        "SELECT pack_id, name, version, pack_type, description, installed_at, enabled "
        "FROM content_packs ORDER BY pack_type, name"
    ) or []

    # Known packs not yet installed
    KNOWN_PACKS = [
        {
            "pack_id": "statistics-course",
            "name": "Statistics for Epidemiology",
            "pack_type": "course",
            "description": "Full statistics course: inference, regression, survival analysis, multilevel models.",
            "version": "1.0",
        },
        {
            "pack_id": "ph-content",
            "name": "Public Health Content Pack",
            "pack_type": "domain",
            "description": "50 library cards, NTD/specialist literature seeds, 20 PH courses.",
            "version": "1.0",
        },
    ]
    installed_ids = {p["pack_id"] for p in packs}
    available = [k for k in KNOWN_PACKS if k["pack_id"] not in installed_ids]

    return templates.TemplateResponse(
        request,
        "partials/metis_content_packs.html",
        {"packs": packs, "available": available},
    )


@router.post("/api/content-packs/{pack_id}/toggle")
async def toggle_content_pack(pack_id: str):
    """Enable or disable a content pack (toggle enabled flag)."""
    row = db_query(
        "SELECT pack_id, name, enabled FROM content_packs WHERE pack_id = ?",
        (pack_id,),
    )
    if not row:
        return JSONResponse({"status": "error", "message": "Pack not found."}, status_code=404)
    new_state = 0 if row[0]["enabled"] else 1
    db_execute(
        "UPDATE content_packs SET enabled = ? WHERE pack_id = ?",
        (new_state, pack_id),
    )
    return JSONResponse({"status": "ok", "pack_id": pack_id, "enabled": bool(new_state)})


@router.post("/api/content-packs/{pack_id}/install")
async def install_content_pack(pack_id: str):
    """Run the seed script for a known content pack."""
    import subprocess
    import os

    rc_root = os.environ.get("METIS_RC_ROOT", "")
    db_path = ""
    try:
        from db import get_db_path
        db_path = str(get_db_path())
    except Exception:
        pass

    seed_scripts = {
        "statistics-course": "seed_epi_base.py",
        "ph-content": "seed_ph_database.py",
    }
    script_name = seed_scripts.get(pack_id)
    if not script_name:
        return JSONResponse({"status": "error", "message": f"Unknown pack: {pack_id}"}, status_code=400)

    script_path = Path(rc_root) / "system" / "install" / script_name if rc_root else None
    if not script_path or not script_path.exists():
        return JSONResponse(
            {"status": "error", "message": f"Seed script not found: {script_name}"},
            status_code=500,
        )

    try:
        result = subprocess.run(
            ["python3", str(script_path), "--db", db_path, "--quiet"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return JSONResponse(
                {"status": "error", "message": result.stderr[:500]},
                status_code=500,
            )
        return JSONResponse({"status": "ok", "pack_id": pack_id, "installed": True})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/api/content-packs/{pack_id}")
async def remove_content_pack(pack_id: str):
    """Remove a content pack record (does not delete seeded rows)."""
    db_execute("DELETE FROM content_packs WHERE pack_id = ?", (pack_id,))
    return JSONResponse({"status": "ok", "pack_id": pack_id, "removed": True})


# ---------------------------------------------------------------------------
# Launcher endpoints — open external applications via PowerShell on Windows
# ---------------------------------------------------------------------------

import subprocess  # noqa: E402  (placed here to keep existing imports clean)


def _ps_launch(cmd: str):
    """Fire-and-forget PowerShell command to launch a Windows app."""
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


@router.post("/api/launcher/claude-code")
async def launcher_claude_code():
    ok = _ps_launch("Start-Process 'wt.exe' -ArgumentList 'new-tab' -ErrorAction SilentlyContinue")
    return JSONResponse({"status": "ok" if ok else "hint",
                         "hint": "Open a terminal and run: claude"})


@router.post("/api/launcher/claude-desktop")
async def launcher_claude_desktop():
    ok = _ps_launch("Start-Process 'Claude' -ErrorAction SilentlyContinue")
    return JSONResponse({"status": "ok" if ok else "error"})


@router.post("/api/launcher/rstudio")
async def launcher_rstudio():
    ok = _ps_launch(
        "Get-Command rstudio -ErrorAction SilentlyContinue | "
        "ForEach-Object { Start-Process $_.Source } ; "
        "if (-not $?) { Start-Process 'C:\\Program Files\\RStudio\\rstudio.exe' -ErrorAction SilentlyContinue }"
    )
    return JSONResponse({"status": "ok" if ok else "error"})


@router.post("/api/launcher/vscode")
async def launcher_vscode():
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        ok = _ps_launch(f"code '{rc_root}'")
    else:
        ok = _ps_launch("Start-Process 'Code' -ErrorAction SilentlyContinue")
    return JSONResponse({"status": "ok" if ok else "error"})


# ── Startup / autostart toggle (Windows Scheduled Task) ───────────────────────
# Lets the user choose, from the dashboard, whether Metis (dashboard + MCP +
# scheduled jobs) starts at login and persists, vs. only runs when opened.
# Registers/removes the "Metis Dashboard Autostart" task via the existing
# register-autostart.ps1 over WSL interop. No admin needed (RunLevel Limited).
_AUTOSTART_TASK = "Metis Dashboard Autostart"


def _win_path(p: str) -> str:
    """WSL path → Windows path (for powershell.exe args). Avoids hardcoding user paths."""
    import subprocess
    try:
        return subprocess.run(["wslpath", "-w", p], capture_output=True, text=True, timeout=5).stdout.strip() or p
    except Exception:
        return p


def _autostart_enabled() -> bool:
    import subprocess
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"if (Get-ScheduledTask -TaskName '{_AUTOSTART_TASK}' -ErrorAction SilentlyContinue) {{'yes'}} else {{'no'}}"],
            capture_output=True, text=True, timeout=15)
        return "yes" in (r.stdout or "").lower()
    except Exception:
        return False


@router.get("/api/partial/metis/startup", response_class=HTMLResponse)
async def metis_startup(request: Request):
    return templates.TemplateResponse(
        request, "partials/metis_startup.html",
        {"autostart_enabled": _autostart_enabled()},
    )


@router.post("/api/metis/autostart/enable", response_class=HTMLResponse)
async def metis_autostart_enable(request: Request):
    import os as _os
    import subprocess
    root = Path(_os.environ.get("METIS_RC_ROOT") or Path(__file__).resolve().parents[3])
    ps1 = root / "system" / "install" / "windows" / "register-autostart.ps1"
    if not ps1.exists():
        return templates.TemplateResponse(
            request, "partials/metis_startup.html",
            {"autostart_enabled": False, "error": "register-autostart.ps1 not found"})
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", _win_path(str(ps1))],
            capture_output=True, text=True, timeout=45)
    except Exception as e:
        return templates.TemplateResponse(
            request, "partials/metis_startup.html",
            {"autostart_enabled": _autostart_enabled(), "error": str(e)[:120]})
    return templates.TemplateResponse(
        request, "partials/metis_startup.html", {"autostart_enabled": _autostart_enabled()})


@router.post("/api/metis/autostart/disable", response_class=HTMLResponse)
async def metis_autostart_disable(request: Request):
    import subprocess
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             f"Unregister-ScheduledTask -TaskName '{_AUTOSTART_TASK}' -Confirm:$false -ErrorAction SilentlyContinue"],
            capture_output=True, text=True, timeout=20)
    except Exception:
        pass
    return templates.TemplateResponse(
        request, "partials/metis_startup.html", {"autostart_enabled": _autostart_enabled()})
