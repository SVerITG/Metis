"""
routers/metis_tab.py — Metis tab routes.
"""

import datetime
import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar

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
# Stats
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/stats", response_class=HTMLResponse)
async def metis_stats(request: Request):
    today = str(datetime.date.today())
    runs_today = db_scalar(
        "SELECT COUNT(*) FROM agent_runs WHERE DATE(started_at) = ?",
        (today,),
        default=0,
    )
    tokens_today = db_scalar(
        "SELECT COALESCE(SUM(tokens_used), 0) FROM agent_runs WHERE DATE(started_at) = ?",
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
# Agent runs list
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/agent-runs", response_class=HTMLResponse)
async def metis_agent_runs(request: Request, days: int = 1):
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    runs = db_query(
        "SELECT agent_slug, task_summary, started_at, tokens_used, status "
        "FROM agent_runs WHERE started_at >= ? "
        "ORDER BY started_at DESC LIMIT 50",
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
            "rc_root": rc_root,
            "db_path": db_path,
            "db_size_kb": db_size_kb,
        },
    )
