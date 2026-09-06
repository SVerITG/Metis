"""
routers/metis_tab.py — Metis tab routes.
"""

import datetime
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ui import clip
from db import db_query, db_scalar, db_execute

log = logging.getLogger("metis.metis_tab")

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


def _surface_ctx() -> dict:
    """Shared context for the Metis surface — the saved model + theme so the
    selector and theme swatches render their ACTUAL persisted state on load
    (S.0b), instead of the previously hardcoded Sonnet / Archive defaults."""
    prefs = _read_user_prefs()
    return {
        "active_tab": "metis",
        "active_model": (prefs.get("active_model") or "sonnet"),
        "active_theme": (prefs.get("theme") or "archive"),
    }


@router.get("/tab/metis", response_class=HTMLResponse)
async def metis_tab(request: Request):
    return templates.TemplateResponse(request, "metis_tab.html", _surface_ctx())


@router.get("/api/tab/metis", response_class=HTMLResponse)
async def metis_tab_partial(request: Request):
    return templates.TemplateResponse(request, "metis_tab.html", _surface_ctx())


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
# Dashboard (S.1) — the "is Metis healthy right now?" one-glance board that
# leads the surface. Honest by design: it also states what ISN'T recorded.
# ---------------------------------------------------------------------------


def _scheduler_running() -> bool | None:
    """Best-effort read of the APScheduler state. None = unknown."""
    try:
        import scheduler as _sched  # app-py/scheduler.py
        sch = getattr(_sched, "scheduler", None) or getattr(_sched, "_scheduler", None)
        if sch is not None and hasattr(sch, "running"):
            return bool(sch.running)
    except Exception:
        pass
    return None


@router.get("/api/partial/metis/dashboard", response_class=HTMLResponse)
async def metis_dashboard(request: Request):
    """Compact health readout: connection, storage, activity — plus an honesty strip."""
    _m = "font-family:var(--m-mono);font-size:11px;color:var(--m-muted);"

    # Connection
    h = _mcp_health()

    # Storage
    db_path, db_size_kb = "unknown", 0
    try:
        from db import get_db_path
        p = get_db_path()
        db_path = _mask_home(str(p))
        db_size_kb = round(p.stat().st_size / 1024)
    except Exception:
        pass
    total_mem = sum(l["count"] for l in _memory_layers())

    # Activity
    today = str(datetime.date.today())
    runs_today = db_scalar("SELECT COUNT(*) FROM agent_runs WHERE DATE(created_at)=?", (today,), default=0) or 0
    total_runs = db_scalar("SELECT COUNT(*) FROM agent_runs", default=0) or 0
    last_session = ""
    try:
        rows = db_query("SELECT summary FROM session_summaries ORDER BY created_at DESC LIMIT 1", default=[]) or []
        if rows:
            last_session = (rows[0].get("summary") or "")[:220]
    except Exception:
        pass
    sched = _scheduler_running()

    def tile(kicker, value, sub, color="var(--m-ink)"):
        return (
            '<div class="panel" style="padding:16px 18px;">'
            f'<div class="kicker" style="padding:0;{_m}">{kicker}</div>'
            f'<div style="font-family:var(--m-display);font-size:24px;font-weight:500;color:{color};margin:6px 0 2px;">{value}</div>'
            f'<div style="{_m}">{sub}</div></div>'
        )

    conn_color = "var(--m-ok)" if h["ok"] else "var(--m-alert)"
    conn_value = "Connected" if h["ok"] else "Check setup"
    conn_sub = "Claude ↔ Metis" if h["ok"] else "see Integration & Keys"
    sched_txt = "Running" if sched else ("Off" if sched is False else "—")

    tiles = (
        '<div class="grid grid-4" style="gap:12px;margin-bottom:14px;">'
        + tile("CONNECTION", conn_value, conn_sub, conn_color)
        + tile("MEMORY", f"{total_mem:,}", "entries across 8 layers")
        + tile("ACTIVITY TODAY", f"{runs_today}", f"{total_runs:,} runs all-time")
        + tile("BACKGROUND JOBS", sched_txt, "scheduler")
        + '</div>'
    )

    storage = (
        f'<div class="panel" style="padding:14px 18px;margin-bottom:14px;{_m}">'
        f'Database · {db_size_kb:,} KB · <span style="color:var(--m-ink);">{db_path}</span></div>'
    )

    last = ""
    if last_session:
        from markupsafe import escape as _esc
        last = (
            '<div class="panel" style="padding:14px 18px;margin-bottom:14px;">'
            f'<div class="kicker" style="padding:0;{_m}">LAST SESSION</div>'
            f'<div style="font-size:13px;color:var(--m-ink);line-height:1.5;margin-top:6px;">{_esc(last_session)}</div></div>'
        )

    # Honesty strip — what is NOT captured yet, so the board never over-promises.
    caveats = []
    tok = db_scalar("SELECT COALESCE(SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0)),0) FROM agent_runs", default=0) or 0
    if not tok:
        caveats.append("token usage isn't being recorded yet")
    if sched is None:
        caveats.append("scheduler state couldn't be read")
    honesty = ""
    if caveats:
        honesty = (
            f'<div class="metis-note" style="{_m}">Being straight with you: '
            + "; ".join(caveats) + ".</div>"
        )

    return HTMLResponse(tiles + storage + last + honesty)


# ---------------------------------------------------------------------------
# Sessions — proof that session memory is active, openable to read each summary
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/sessions", response_class=HTMLResponse)
async def metis_sessions(request: Request, limit: int = 12):
    """Recorded-session count + memory-active status + recent sessions you can
    open to read what each did. Answers 'is session memory active, and what did
    each session do?' honestly, including the Code-vs-Desktop split where known."""
    from markupsafe import escape as _esc
    _m = "font-family:var(--m-mono);font-size:11px;color:var(--m-muted);"

    # The client column is added lazily by save_session_summary's migration; ensure
    # it exists so this read never fails on a DB that hasn't saved a summary yet.
    try:
        db_execute("ALTER TABLE session_summaries ADD COLUMN client TEXT DEFAULT ''")
    except Exception:
        pass

    total = db_scalar("SELECT COUNT(*) FROM session_summaries", default=0) or 0
    last = db_scalar("SELECT MAX(created_at) FROM session_summaries", default="") or ""
    # Client split — only meaningful for rows recorded since client capture was added.
    by_client_rows = db_query(
        "SELECT COALESCE(NULLIF(client,''),'(untagged)') AS client, COUNT(*) AS n "
        "FROM session_summaries GROUP BY COALESCE(NULLIF(client,''),'(untagged)') ORDER BY n DESC",
        default=[],
    ) or []
    tagged = {r["client"]: r["n"] for r in by_client_rows if r["client"] != "(untagged)"}

    # Is memory active? Fresh if the most-recent summary is within 14 days.
    active, when = False, ""
    if last:
        when = str(last)[:10]
        try:
            d = datetime.datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=datetime.timezone.utc)
            active = (datetime.datetime.now(datetime.timezone.utc) - d).days <= 14
        except Exception:
            active = True

    _label = {"code": "Claude Code", "chat": "Claude Desktop", "desktop": "Claude Desktop",
              "dashboard": "Dashboard"}
    status_color = "var(--m-ok)" if active else "var(--m-alert)"
    status_txt = (f"Session memory is active — {total:,} recorded, last {when}"
                  if active else
                  f"{total:,} recorded, but the last was {when} — recording may have stalled")

    # Client split line (honest about the coverage gap)
    if tagged:
        parts = [f"{_label.get(k, k)}: {v}" for k, v in tagged.items()]
        split = "By client: " + " · ".join(parts)
        n_untagged = sum(r["n"] for r in by_client_rows if r["client"] == "(untagged)")
        if n_untagged:
            split += f" · {n_untagged} recorded before client was tracked"
    else:
        split = ("Claude Code vs Claude Desktop isn't distinguished in the records yet — "
                 "client is tagged from now on, so this split will fill in going forward.")

    head = (
        '<div class="panel" style="padding:16px 18px;margin-bottom:14px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="color:{status_color};font-weight:600;">● {_esc(status_txt)}</span></div>'
        f'<div style="{_m}margin-top:6px;">{_esc(split)}</div></div>'
    )

    rows = db_query(
        "SELECT session_id, summary, key_topics, decisions, created_at, "
        "COALESCE(NULLIF(client,''),'') AS client "
        "FROM session_summaries ORDER BY created_at DESC LIMIT ?",
        (limit,),
        default=[],
    ) or []

    items = []
    for r in rows:
        d = dict(r)
        ts = str(d.get("created_at") or "")[:16].replace("T", " ")
        cli = _label.get(d.get("client"), d.get("client") or "")
        cli_chip = (f'<span style="{_m}border:1px solid var(--m-rule-soft);border-radius:999px;'
                    f'padding:1px 8px;margin-left:8px;">{_esc(cli)}</span>' if cli else "")
        summ = (d.get("summary") or "").strip()
        first_line = summ.split("\n", 1)[0][:120]
        # topics
        chips = ""
        try:
            for t in (json.loads(d.get("key_topics") or "[]"))[:6]:
                chips += (f'<span style="{_m}background:var(--m-surface);border-radius:3px;'
                          f'padding:1px 6px;margin:2px 4px 2px 0;display:inline-block;">{_esc(str(t))}</span>')
        except Exception:
            pass
        decisions_html = ""
        try:
            decs = json.loads(d.get("decisions") or "[]")
            if decs:
                lis = "".join(f'<li style="margin:2px 0;">{_esc(str(x)[:240])}</li>' for x in decs[:8])
                decisions_html = (f'<div style="{_m}margin-top:8px;">DECISIONS</div>'
                                  f'<ul style="margin:4px 0 0;padding-left:18px;font-size:12.5px;'
                                  f'color:var(--m-text);line-height:1.5;">{lis}</ul>')
        except Exception:
            pass
        body = _esc(summ[:2000])
        items.append(
            '<details style="border-bottom:1px solid var(--m-rule-soft);">'
            '<summary style="list-style:none;cursor:pointer;padding:11px 16px;display:flex;'
            'align-items:baseline;gap:10px;">'
            f'<span style="{_m}flex-shrink:0;min-width:120px;">{_esc(ts)}</span>'
            f'<span style="font-size:13px;color:var(--m-ink);line-height:1.4;flex:1;">{_esc(first_line)}{cli_chip}</span>'
            '</summary>'
            f'<div style="padding:0 16px 14px;">'
            f'<div style="font-size:13px;color:var(--m-text);line-height:1.6;white-space:pre-wrap;">{body}</div>'
            f'<div style="margin-top:8px;">{chips}</div>{decisions_html}</div>'
            '</details>'
        )

    listing = (
        '<div class="panel" style="overflow:hidden;">' + "".join(items) + '</div>'
        if items else
        f'<div class="panel" style="padding:16px 18px;{_m}">No sessions recorded yet.</div>'
    )
    return HTMLResponse(head + listing)


# ---------------------------------------------------------------------------
# Health check — friendly one-click run of the full doctor, in the dashboard
# ---------------------------------------------------------------------------


@router.get("/api/partial/metis/health-check", response_class=HTMLResponse)
async def metis_health_check(request: Request):
    """Run the full system doctor and render it in plain language — memory,
    dependencies, stale installs, projects registered, connection, and more —
    so a non-technical user can check everything with one click, no terminal."""
    _m = "font-family:var(--m-mono);font-size:11px;color:var(--m-muted);"
    try:
        from metis_mcp.tools.doctor import run_doctor
        report = run_doctor()
    except Exception as e:
        return HTMLResponse(
            f'<div class="panel" style="padding:16px 18px;{_m}">Couldn\'t run the health check '
            f'({_esc_str(e)}). Try reconnecting the Metis server, then run it again.</div>'
        )

    status = str(report.get("status") or "unknown").lower()
    checks = report.get("checks") or []
    overall_color = {"ok": "var(--m-ok)", "warn": "var(--m-warn)", "fail": "var(--m-alert)"}.get(status, "var(--m-muted)")
    overall_txt = {
        "ok": "Everything checks out — Metis is healthy.",
        "warn": "Metis works, but a few things are worth fixing.",
        "fail": "Something needs attention before relying on Metis.",
    }.get(status, "Health check complete.")

    from markupsafe import escape as _esc
    n_ok = sum(1 for c in checks if c.get("ok"))
    rows_html = []
    for c in checks:
        ok = bool(c.get("ok"))
        sev = str(c.get("severity") or "info")
        if ok:
            color, dot = "var(--m-ok)", "●"
        elif sev == "fail":
            color, dot = "var(--m-alert)", "✕"
        else:
            color, dot = "var(--m-warn)", "▲"
        rows_html.append(
            '<div style="display:flex;align-items:baseline;gap:10px;padding:7px 0;'
            'border-bottom:1px solid var(--m-rule-soft);">'
            f'<span style="color:{color};flex-shrink:0;width:14px;">{dot}</span>'
            f'<span style="font-size:13px;color:var(--m-ink);min-width:170px;flex-shrink:0;">{_esc(str(c.get("name") or ""))}</span>'
            f'<span style="{_m}line-height:1.5;">{_esc(str(c.get("detail") or ""))}</span></div>'
        )

    return HTMLResponse(
        '<div class="panel" style="padding:16px 18px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        f'<span style="color:{overall_color};font-weight:600;">● {_esc(overall_txt)}</span></div>'
        f'<div style="{_m}">{n_ok}/{len(checks)} checks passed · '
        f'<span style="cursor:pointer;text-decoration:underline;" '
        f'hx-get="/api/partial/metis/health-check" hx-target="#metis-health-body" hx-swap="innerHTML">run again</span></div>'
        '</div>'
        '<div class="panel" style="padding:12px 18px;">' + "".join(rows_html) + '</div>'
    )


def _esc_str(e) -> str:
    from markupsafe import escape
    return str(escape(str(e)))


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
    # News and library interests are separate entities. read_interest_lists()
    # resolves the new fields, falls back to the legacy `interests`/`news_topics`
    # for installs that predate the split, and folds the install wizard's
    # research block onto the library side.
    news_interests: list = []
    library_interests: list = []
    try:
        import sys as _sys
        _src = str(Path(__file__).parent.parent.parent / "mcp-server" / "src")
        if _src not in _sys.path:
            _sys.path.insert(0, _src)
        from metis_mcp.tools.user_profile import read_interest_lists
        _lists = read_interest_lists()
        news_interests = _lists["news"]
        library_interests = _lists["library"]
    except Exception:
        news_interests = prefs.get("news_interests") or prefs.get("news_topics") or []
        library_interests = prefs.get("library_interests") or prefs.get("interests") or []

    return templates.TemplateResponse(
        request,
        "partials/metis_identity_card.html",
        {
            "name": name,
            "initial": (name[:1].upper() if name else "S"),
            "role": role,
            "news_interests": news_interests,
            "library_interests": library_interests,
            # legacy names kept for any other consumer of this context
            "interests": library_interests,
            "news_topics": news_interests,
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
# (Removed S.0d) The `/api/partial/metis/agents` and `/api/partial/metis/traces`
# endpoints were dead code — referenced by no template. The agent directory is
# served by `/api/partial/metis/agent-directory`; the span-trace waterfall had no
# producer writing `agent_spans` so it always rendered empty. Both removed.
# ---------------------------------------------------------------------------


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


# ── Persona settings ──────────────────────────────────────────────────────

_PERSONA_KEYS = {
    "warmth":             {"warm", "neutral", "formal"},
    "response_length":    {"concise", "moderate", "detailed"},
    "feedback_style":     {"gentle", "direct", "challenging"},
    "challenge_level":    {"supportive", "balanced", "rigorous"},
    "detail_level":       {"brief", "balanced", "thorough"},
    "routing_verbosity":  {"silent", "natural", "detailed"},
}

_PERSONA_DEFAULTS = {
    "warmth": "warm",
    "response_length": "concise",
    "feedback_style": "gentle",
    "challenge_level": "balanced",
    "detail_level": "balanced",
    "routing_verbosity": "natural",
}


def _load_persona() -> dict:
    """Load persona settings from user-config.yaml (style: block) + user-preferences.json overlay."""
    persona = dict(_PERSONA_DEFAULTS)
    # 1. YAML base
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    yaml_path = Path(rc_root) / "system" / "config" / "user-config.yaml" if rc_root else None
    if yaml_path and yaml_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            raw = cfg.get("style") or {}
            if isinstance(raw, dict):
                for k in _PERSONA_KEYS:
                    if k in raw and raw[k] in _PERSONA_KEYS[k]:
                        persona[k] = raw[k]
        except Exception:
            pass
    # 2. JSON overlay (persona_* keys take precedence)
    prefs = _read_user_prefs()
    for k in _PERSONA_KEYS:
        pkey = f"persona_{k}"
        val = prefs.get(pkey) or prefs.get(k)
        if val and val in _PERSONA_KEYS[k]:
            persona[k] = val
    return persona


@router.get("/api/partial/metis/persona", response_class=HTMLResponse)
async def metis_persona(request: Request):
    """Persona settings panel — warmth, length, feedback style, etc."""
    persona = _load_persona()
    return templates.TemplateResponse(
        request,
        "partials/metis_persona.html",
        {"persona": persona},
    )


@router.post("/api/metis/persona", response_class=HTMLResponse)
async def set_persona(request: Request):
    """Save a single persona setting and re-render the panel."""
    try:
        payload = await request.form()
        key = payload.get("key", "").strip()
        value = payload.get("value", "").strip()
    except Exception:
        key, value = "", ""
    if key not in _PERSONA_KEYS or value not in _PERSONA_KEYS.get(key, set()):
        return HTMLResponse("<div class='metis-note' style='color:var(--m-alert);'>Unknown setting.</div>", status_code=400)
    # Save to user-preferences.json (persona_* namespace)
    prefs = _read_user_prefs()
    prefs[f"persona_{key}"] = value
    prefs[f"persona_{key}_set_at"] = datetime.datetime.now().isoformat()
    try:
        _write_user_prefs(prefs)
    except Exception:
        pass
    # Re-render the full panel with updated values
    persona = _load_persona()
    return templates.TemplateResponse(
        request,
        "partials/metis_persona.html",
        {"persona": persona},
    )


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
    # NO PAID API CALLS ON A RENDER PATH.
    #
    # `aggregate_reflexions` themes reflexions with Claude Haiku whenever
    # ANTHROPIC_API_KEY is set — one call per agent per category. Measured
    # 2026-09-06: opening this surface fired NINE POSTs to api.anthropic.com and
    # took 18.5s, every single view, with an idle control of zero. It looked fine
    # in every test because a test process has no key, so it silently took the
    # word-frequency fallback and returned in 0.01s.
    #
    # A GET that renders a panel must not spend money or block on a network
    # round-trip. Themes are now read from a machine-local cache written by the
    # explicit refresh below; the panel renders instantly and says when it last
    # computed. Same rule as never putting DDL on a render path.
    themes_cached_at = ""
    cache_fp = _themes_cache_path(days)
    if cache_fp.is_file():
        try:
            _c = json.loads(cache_fp.read_text(encoding="utf-8"))
            themes = _c.get("themes") or themes
            themes_cached_at = str(_c.get("computed_at") or "")[:19].replace("T", " ")
        except Exception:
            log.warning("reflexion theme cache unreadable: %s", cache_fp, exc_info=True)
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
            "themes_cached_at": themes_cached_at,
        },
    )


def _themes_cache_path(days: int):
    """Machine-local cache for the LLM-themed reflexions.

    Local, not in the repo: it is derived data, it differs per machine, and the
    repo tree is OneDrive-synced — the same reason the logs moved out.
    """
    base = Path(os.environ.get("METIS_STATE_DIR", "")
                or (Path.home() / ".local" / "state" / "metis" / "cache"))
    base.mkdir(parents=True, exist_ok=True)
    return base / f"reflexion-themes-{int(days)}d.json"


@router.post("/api/metis/improvement/refresh-themes", response_class=HTMLResponse)
async def metis_improvement_refresh_themes(request: Request, days: int = 14):
    """Compute the reflexion themes with Claude and cache them, then re-render.

    Explicit and user-initiated, because it costs money and takes ~17s. That is
    exactly why it must not sit on the render path.
    """
    try:
        from metis_mcp.tools.improvement import aggregate_reflexions
        themes = aggregate_reflexions(days=days)
        _themes_cache_path(days).write_text(json.dumps({
            "computed_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "window_days": days,
            "themes": themes,
        }, indent=2), encoding="utf-8")
    except Exception:
        log.warning("theme refresh failed", exc_info=True)
    return await metis_improvement(request, days=days)


@router.get("/api/partial/metis/startup-eval", response_class=HTMLResponse)
async def startup_eval_strip(request: Request):
    """Surface the boot self-check (system/config/eval-results.json), written on every
    dashboard start by startup_eval.run_startup_eval but previously read by nothing —
    so a fresh-user / drift signal at boot was invisible (Keystone P3.5)."""
    base = Path(os.environ.get("METIS_RC_ROOT", "") or Path(__file__).resolve().parents[3])
    fp = base / "system" / "config" / "eval-results.json"
    _muted = "font-family:var(--m-mono);font-size:11px;color:var(--m-muted);"
    if not fp.is_file():
        return HTMLResponse(f'<div class="panel" style="padding:14px 18px;margin-bottom:24px;{_muted}">No startup self-check recorded yet.</div>')
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return HTMLResponse(f'<div class="panel" style="padding:14px 18px;margin-bottom:24px;{_muted}">Startup self-check file is unreadable.</div>')
    overall = str(d.get("overall") or "UNKNOWN").upper()
    color = "var(--m-ok)" if overall == "PASS" else "var(--m-alert)"
    when = str(d.get("run_at") or "")[:19].replace("T", " ")
    chips = "".join(
        '<span style="display:inline-block;' + _muted + 'border:1px solid var(--m-rule-soft);'
        'border-radius:var(--m-radius-pill);padding:2px 8px;margin:2px 4px 2px 0;">'
        f'{c.get("name")}: <span style="color:'
        f'{"var(--m-ok)" if str(c.get("status")).upper() == "PASS" else "var(--m-alert)"};">'
        f'{c.get("status")}</span></span>'
        for c in (d.get("checks") or [])
    )
    return HTMLResponse(
        '<div class="panel" style="padding:14px 18px;margin-bottom:24px;">'
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        f'<span style="color:{color};font-weight:600;">● Startup self-check: {overall}</span>'
        f'<span style="{_muted}">{when}</span></div>'
        f'<div style="margin-top:8px;">{chips}</div></div>'
    )


@router.get("/api/partial/metis/promise-trend", response_class=HTMLResponse)
async def promise_trend(request: Request):
    """Drift heatmap (Keystone 3.8) — the promise-harness score over time, so
    "have we lost what we built?" is a LIVE indicator, not a manual investigation.
    Reads system/config/promise-trend.jsonl (written weekly by the scheduler)."""
    base = Path(os.environ.get("METIS_RC_ROOT", "") or Path(__file__).resolve().parents[3])
    fp = base / "system" / "config" / "promise-trend.jsonl"
    _m = "font-family:var(--m-mono);font-size:11px;color:var(--m-muted);"
    entries = []
    if fp.is_file():
        try:
            for line in fp.read_text(encoding="utf-8").splitlines()[-12:]:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        except Exception:
            entries = []
    if not entries:
        return HTMLResponse(
            f'<div class="panel" style="padding:16px 18px;{_m}">No promise-harness runs recorded yet — '
            'it runs weekly, or run <code>bash tests/functional/run_metis_promises.sh</code>.</div>'
        )
    latest = entries[-1]
    ok = int(latest.get("fail", 0)) == 0
    color = "var(--m-ok)" if ok else "var(--m-alert)"
    cells = "".join(
        f'<span title="{e.get("ts","")}: {e.get("pass",0)} pass / {e.get("fail",0)} fail / {e.get("warn",0)} warn" '
        'style="display:inline-block;width:10px;height:16px;margin-right:2px;border-radius:2px;'
        f'background:{"var(--m-ok)" if int(e.get("fail",0))==0 else "var(--m-alert)"};"></span>'
        for e in entries
    )
    return HTMLResponse(
        '<div class="panel" style="padding:14px 18px;margin-bottom:24px;">'
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        f'<span style="color:{color};font-weight:600;">● Promises: {latest.get("pass",0)} pass · '
        f'{latest.get("fail",0)} fail · {latest.get("warn",0)} warn</span>'
        f'<span style="{_m}">{str(latest.get("ts",""))[:16].replace("T", " ")}</span></div>'
        f'<div style="margin-top:8px;">{cells}</div>'
        f'<div style="{_m}margin-top:6px;">weekly drift — each cell is one run (green = zero hard-fails)</div>'
        "</div>"
    )


@router.get("/api/partial/metis/who-did-what", response_class=HTMLResponse)
async def who_did_what(request: Request, session_id: str = ""):
    """'Who did what' for a session (Keystone B6.2) — surface the agent_runs
    contributors so the user can SEE which specialists worked and what each did.
    Defaults to the most recent session. A 'running' status renders as "working…"
    (live indicator ready for B6.1's dispatch-write)."""
    from markupsafe import escape as _esc
    sid = (session_id or "").strip()
    if not sid:
        latest = db_query("SELECT session_id FROM sessions ORDER BY last_active DESC LIMIT 1", default=[]) or []
        sid = latest[0]["session_id"] if latest else ""
    runs = []
    if sid:
        runs = db_query(
            "SELECT agent_slug, task_summary, model, status, "
            "COALESCE(input_tokens,0)+COALESCE(output_tokens,0) AS tokens, created_at "
            "FROM agent_runs WHERE session_id=? ORDER BY created_at ASC, run_id ASC LIMIT 30",
            (sid,), default=[],
        ) or []
    _m = "font-family:var(--m-mono);font-size:11px;color:var(--m-muted);"
    if not runs:
        return HTMLResponse(
            f'<div class="panel" style="padding:16px 18px;{_m}">No agent activity recorded for your '
            'last session yet. When Metis routes a request to a specialist and the run is logged, the '
            'contributors appear here.</div>'
        )
    # A 'running' row older than this is treated as stale — the agent almost
    # certainly finished without its completion being logged (or the process
    # died), so we stop showing a perpetual "working…" (S.2).
    _stale_cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=15))
    rows_html = []
    for r in runs:
        pretty = str(r.get("agent_slug") or "metis").replace("-", " ").title()
        running = str(r.get("status")) == "running"
        stale = False
        if running:
            try:
                _ts = str(r.get("created_at") or "")
                _dt = datetime.datetime.fromisoformat(_ts)
                if _dt.tzinfo is None:
                    _dt = _dt.replace(tzinfo=datetime.timezone.utc)
                stale = _dt < _stale_cutoff
            except Exception:
                stale = False
        if running and not stale:
            dot = '<span style="color:var(--m-warn);font-weight:600;">● working…</span> '
        elif running and stale:
            dot = '<span style="color:var(--m-muted);">○ no result logged</span> '
        else:
            dot = ""
        meta = ""
        if r.get("model"):
            meta += f' · {_esc(str(r["model"]))}'
        if r.get("tokens"):
            meta += f' · {r["tokens"]} tok'
        rows_html.append(
            '<div style="display:flex;gap:10px;align-items:baseline;padding:7px 0;'
            'border-bottom:1px solid var(--m-rule-soft);">'
            f'<span style="font-family:var(--m-mono);font-size:11px;letter-spacing:0.06em;'
            f'color:var(--m-accent);flex-shrink:0;min-width:130px;">{_esc(pretty)}</span>'
            f'<span style="font-size:13px;color:var(--m-ink);line-height:1.4;">{dot}'
            f'{_esc(clip(r.get("task_summary") or "", 180))}<span style="{_m}">{meta}</span></span>'
            "</div>"
        )
    return HTMLResponse(
        '<div class="panel" style="padding:14px 18px;margin-bottom:0;">'
        f'<div style="{_m}margin-bottom:6px;">Session {_esc(sid[:8])}… — {len(runs)} contribution(s)</div>'
        + "".join(rows_html) + "</div>"
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


# ---------------------------------------------------------------------------
# MCP health (S.3) — is the metis-rc server installed + registered where Claude
# can actually reach it? This is the one thing a user most wants confirmed and
# the old surface never checked it.
# ---------------------------------------------------------------------------


def _claude_desktop_config_paths() -> list[Path]:
    """Candidate locations for Claude Desktop's config across WSL/Windows/macOS/Linux."""
    cands: list[Path] = []
    # WSL → Windows AppData, derived from METIS_RC_ROOT (…/mnt/<d>/Users/<user>/…)
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    import re as _re
    m = _re.match(r"(/mnt/[a-z])/Users/([^/]+)/", rc_root)
    if m:
        cands.append(Path(f"{m.group(1)}/Users/{m.group(2)}/AppData/Roaming/Claude/claude_desktop_config.json"))
    home = Path.home()
    cands += [
        home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",  # native Windows
        home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",  # macOS
        home / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
    ]
    return cands


def _registered_in(config_path: Path) -> bool:
    """True if any mcpServers key mentions metis in the given JSON config.

    Looks in BOTH places a server can be registered, which is the fix here
    (2026-09-02). Claude Desktop keeps one global `mcpServers` map; Claude Code
    registers PER PROJECT, under `projects["<path>"].mcpServers` in
    ~/.claude.json, and only writes the root map for a user-scoped server.
    Reading the root alone reported "Claude Code — not registered — run
    claude mcp add" on a machine where metis-rc was registered and working, and
    that panel exists precisely so a non-technical reader can trust it.
    """
    try:
        if not config_path.is_file():
            return False
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
        maps = [data.get("mcpServers") or {}]
        for proj in (data.get("projects") or {}).values():
            if isinstance(proj, dict):
                maps.append(proj.get("mcpServers") or {})
        return any("metis" in str(k).lower() for m in maps for k in m)
    except Exception:
        return False


def _mcp_health() -> dict:
    """Best-effort, read-only MCP reachability picture."""
    # 1. Is the server package importable (i.e. installed in the venv)?
    importable = False
    try:
        import importlib.util
        importable = importlib.util.find_spec("metis_mcp") is not None
    except Exception:
        importable = False

    # 2. Registered in Claude Desktop?
    desktop = False
    desktop_path = ""
    for p in _claude_desktop_config_paths():
        if _registered_in(p):
            desktop, desktop_path = True, str(p)
            break

    # 3. Registered in Claude Code (~/.claude.json)?
    code = _registered_in(Path.home() / ".claude.json")

    ok = importable and (desktop or code)
    return {
        "ok": ok,
        "importable": importable,
        "desktop": desktop,
        "desktop_path": _mask_home(desktop_path),
        "code": code,
    }


@router.get("/api/partial/metis/mcp-health", response_class=HTMLResponse)
async def metis_mcp_health(request: Request):
    h = _mcp_health()
    _m = "font-family:var(--m-mono);font-size:11px;color:var(--m-muted);"

    def row(label, good, good_txt, bad_txt):
        color = "var(--m-ok)" if good else "var(--m-alert)"
        dot = "●" if good else "○"
        return (
            '<div style="display:flex;align-items:baseline;gap:10px;padding:6px 0;'
            'border-bottom:1px solid var(--m-rule-soft);">'
            f'<span style="color:{color};flex-shrink:0;">{dot}</span>'
            f'<span style="font-size:13px;color:var(--m-ink);min-width:190px;">{label}</span>'
            f'<span style="{_m}">{good_txt if good else bad_txt}</span></div>'
        )

    overall_color = "var(--m-ok)" if h["ok"] else "var(--m-alert)"
    overall_txt = "Connected — Claude can reach Metis" if h["ok"] else "Not fully connected"
    body = (
        '<div class="panel" style="padding:16px 18px;margin-bottom:24px;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<span style="color:{overall_color};font-weight:600;">● {overall_txt}</span></div>'
        + row("Server installed", h["importable"], "importable in this environment", "metis_mcp not importable — reinstall")
        + row("Claude Desktop", h["desktop"], "registered", "not registered — add it in Integration")
        + row("Claude Code", h["code"], "registered", "not registered — run claude mcp add")
        + '</div>'
    )
    return HTMLResponse(body)


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


def _memory_layers() -> list[dict]:
    """Count every memory layer Metis holds (S.0c/S.4).

    The old overview counted only `memory_entries` (~67 rows) and so under-reported
    what Metis holds by two orders of magnitude. This counts all eight layers, the
    same set the (now-merged) Memory Health surface used, degrading each to 0 if a
    table is missing rather than failing the whole panel.
    """
    specs = [
        ("Memory Palace", "CURATED",       "memory_entries",    "Entries you and Metis chose to keep"),
        ("Episodic",      "EVENTS",        "episodic_memory",   "What happened, and what was found"),
        ("Semantic",      "CONCEPTS",      "semantic_memory",   "Settled facts and understanding"),
        ("Procedural",    "PRACTICE",      "procedural_memory", "How things are done here"),
        ("Sessions",      "CONVERSATIONS", "session_summaries", "The record of each working session"),
        ("Ideas",         "THREADS",       "ideas",             "Thoughts captured for later"),
        ("Reflexions",    "SELF-REVIEW",   "reflexion_log",     "Where the work could improve"),
        ("Library",       "INDEXED",       "pdf_chunks",        "Passages from your reading, searchable"),
    ]
    layers = []
    for name, kicker, table, desc in specs:
        try:
            cnt = db_scalar(f"SELECT COUNT(*) FROM {table}", default=0) or 0
        except Exception:
            cnt = 0
        layers.append({"name": name, "kicker": kicker, "table": table,
                       "count": int(cnt), "desc": desc})
    return layers


@router.get("/api/partial/metis/memory-overview", response_class=HTMLResponse)
async def metis_memory_overview(request: Request):
    """Full 8-layer memory picture + by-type breakdown + archive control."""
    layers = _memory_layers()
    total_all = sum(l["count"] for l in layers)
    max_layer = max((l["count"] for l in layers), default=1) or 1
    for l in layers:
        l["pct"] = round(100.0 * l["count"] / max_layer, 1)

    # Curated "Memory Palace" detail (memory_entries) — kept for the by-type chips
    total_memories = db_scalar("SELECT COUNT(*) FROM memory_entries", default=0) or 0
    week_cutoff = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    week_count = db_scalar(
        "SELECT COUNT(*) FROM memory_entries WHERE created_at >= ?",
        (week_cutoff,),
        default=0,
    ) or 0
    oldest = db_scalar("SELECT MIN(created_at) FROM memory_entries", default="") or ""

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
            "layers": layers,
            "total_all": total_all,
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
                        "content": clip(r["content"] or "", 200),
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
                        "content": clip(r.get("content") or "", 200),
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
    """Add or replace a key in system/.env.

    Requires ``X-Metis-Confirm: api-key`` header to prevent CSRF-driven key changes.
    """
    if request.headers.get("X-Metis-Confirm") != "api-key":
        return JSONResponse({"error": "confirmation header required"}, status_code=403)
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
async def delete_api_key(name: str, request: Request):
    """Remove a key from system/.env.

    Requires ``X-Metis-Confirm: api-key`` header to prevent CSRF-driven key removal.
    """
    if request.headers.get("X-Metis-Confirm") != "api-key":
        return JSONResponse({"error": "confirmation header required"}, status_code=403)
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
    # The REAL database path, resolved, not assumed.
    #
    # This generator hardcoded `{rc_root}/system/app/data/metis.sqlite` — the
    # OneDrive location the live DB was moved OFF in June 2026 because OneDrive
    # sync corrupts SQLite's WAL sidecars. That file does not exist. The generated
    # CLAUDE.md is read by every future Claude session, so the wrong path did not
    # just sit in a file: it propagated as a fact into every conversation, and
    # anyone backing up "the database" from it would have backed up nothing.
    try:
        from db import get_db_path
        db_display = str(get_db_path())
    except Exception:
        db_display = str(Path.home() / ".local" / "share" / "metis" / "metis.sqlite")
    interests_str = ", ".join(interests) if interests else "(not set)"
    news_str = ", ".join(news_topics) if news_topics else "(not set)"
    return f"""# Metis — Global Claude Code Configuration

**Owner:** {name}
**Research Cortex root:** `{rc_root}/`
**Database:** `{db_display}`

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
# (Removed S.0d) The content-packs endpoints (list/toggle/install/remove) were
# unreachable — no template GET them, and only one of two seed scripts ever
# registered a `content_packs` row, so install-state was never truthful. The
# packaged-background model is deferred to Phase 2 (backgrounds-as-plugins) and
# will be rebuilt against a proper manifest + registry rather than this scaffold.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Update Metis  (Keystone P2.4 — an update you are not afraid to run)
# ---------------------------------------------------------------------------
# `tools/metis-update.sh` could already update Metis, but only from a terminal —
# which fails the whole "non-technical by default" promise: the person Metis is
# built for cannot open a shell. It also backed up only the database and had no
# rollback, so a bad update left a half-updated system and no way back. An update
# the user is afraid to run is one that never happens, and a Metis that never
# updates quietly rots.
#
# The heavy lifting is tools/metis_update.py (record → back up → pull → migrate →
# verify → roll back on failure). This is the button and the progress it shows.

_UPDATE_STATUS = Path.home() / ".local/share/metis-mcp/update-status.json"


def _update_state() -> dict:
    try:
        return json.loads(_UPDATE_STATUS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _update_panel_html() -> str:
    st = _update_state()
    state = st.get("state", "")
    running = state == "running"
    colour = {
        "ok": "var(--m-ok)", "failed": "var(--m-warn)", "blocked": "var(--m-warn)",
        "rolled_back": "var(--m-warn)", "running": "var(--m-accent)",
    }.get(state, "var(--m-muted)")

    if st:
        headline = st.get("detail") or state or "—"
        when = (st.get("updated_at") or "")[:16].replace("T", " ")
        last = (f'<div style="font-family:var(--m-mono);font-size:10px;color:{colour};'
                f'margin-top:6px;">{headline}</div>'
                f'<div style="font-family:var(--m-mono);font-size:9px;color:var(--m-muted);">'
                f'last checked {when}</div>')
    else:
        last = ('<div style="font-family:var(--m-mono);font-size:10px;color:var(--m-muted);'
                'margin-top:6px;">Not checked yet.</div>')

    # While it runs, the panel re-fetches itself; the moment it stops, polling stops.
    poll = ('hx-get="/api/partial/metis/update" hx-trigger="load delay:3s" '
            'hx-swap="outerHTML"') if running else ''

    btn = ("Updating…" if running else "Update Metis")
    disabled = "opacity:0.5;pointer-events:none;" if running else ""

    return f"""
    <div id="metis-update" class="panel" style="padding:16px 18px;margin-bottom:16px;" {poll}>
      <div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;
                  color:var(--m-muted);margin-bottom:8px;">UPDATE</div>
      <div style="font-size:12px;color:var(--m-muted);">
        Brings in the newest Metis. Your work is backed up first, and if anything goes
        wrong the update undoes itself and puts everything back.
      </div>
      {last}
      <div style="display:flex;gap:8px;margin-top:10px;">
        <button hx-post="/api/metis/update/check" hx-target="#metis-update" hx-swap="outerHTML"
                style="font-family:var(--m-mono);font-size:10px;padding:5px 12px;
                       border:1px solid var(--m-line);border-radius:4px;cursor:pointer;
                       background:var(--m-surface);color:var(--m-ink);{disabled}">
          Check only
        </button>
        <button hx-post="/api/metis/update/run" hx-target="#metis-update" hx-swap="outerHTML"
                hx-confirm="Update Metis now? Your data is backed up first and restored automatically if anything fails."
                style="font-family:var(--m-mono);font-size:10px;padding:5px 12px;
                       border:1px solid var(--m-accent);border-radius:4px;cursor:pointer;
                       background:var(--m-accent);color:var(--m-bg);{disabled}">
          {btn}
        </button>
      </div>
    </div>"""


@router.get("/api/partial/metis/update", response_class=HTMLResponse)
async def metis_update_panel(request: Request):
    return HTMLResponse(_update_panel_html())


def _launch_update(dry: bool) -> None:
    """Run the updater detached — it reinstalls the server and can take minutes."""
    root = os.environ.get("METIS_RC_ROOT", str(Path(__file__).resolve().parents[3]))
    venv = Path.home() / ".local/share/metis-mcp/.venv/bin/python3"
    cmd = [str(venv) if venv.exists() else "python3", str(Path(root) / "tools/metis_update.py")]
    if dry:
        cmd.append("--dry-run")
    subprocess.Popen(cmd, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


@router.post("/api/metis/update/check", response_class=HTMLResponse)
async def metis_update_check(request: Request):
    _launch_update(dry=True)
    return HTMLResponse(_update_panel_html())


@router.post("/api/metis/update/run", response_class=HTMLResponse)
async def metis_update_run(request: Request):
    _launch_update(dry=False)
    return HTMLResponse(_update_panel_html())


# ---------------------------------------------------------------------------
# Settings map  (Keystone P2.5 — which files matter, and which you can ignore)
# ---------------------------------------------------------------------------
# ~40 files live in system/config/. Some are yours to change, some are power-user
# territory, some are internal state, and some are dead artefacts from an older
# mechanism that nothing reads any more. Nothing distinguished them, so the honest
# answer to "where do I change X?" was "read the source". This panel is the answer
# instead — and it names the orphans, because a settings-shaped file that nothing
# reads is worse than no file: editing it changes nothing and says nothing.

_SETTINGS_MAP = [
    # (filename, kind, what it controls, where to change it)
    ("user-preferences.json", "ui", "Your name, style, theme, library path",
     "Appearance & Settings, above"),
    ("user-config.yaml", "ui", "Identity, interests, news topics, projects",
     "Appearance & Settings, or the setup wizard"),
    (".env", "ui", "Your Anthropic and Zotero API keys", "API keys section, above"),
    ("models.yaml", "power", "Which model each task tier prefers (advisory — the "
     "Claude client makes the actual call)", "edit the file"),
    ("tool-subsets.json", "power", "Which tools load for which agent", "edit the file"),
    ("agent-registry.json", "power", "The agent catalogue", "edit the file"),
    ("network-policy.json", "power", "Which hosts Metis may reach", "edit the file"),
    ("domain-overrides.local.json", "power", "Your institution's own PII patterns "
     "(local only, never shared)", "edit the file"),
    ("implementation-progress.json", "state", "Build progress tracker", "don't edit"),
    ("install-state.json", "state", "What the installer did", "don't edit"),
    ("mcp-health.json", "state", "Last server start's health", "don't edit"),
    ("eval-results.json", "state", "Last self-evaluation run", "don't edit"),
]

_KIND_STYLE = {
    "ui":      ("var(--m-ok)",    "CHANGE IN METIS"),
    "power":   ("var(--m-accent)", "EDIT THE FILE"),
    "state":   ("var(--m-muted)", "INTERNAL"),
    "orphan":  ("var(--m-warn)",  "DEAD — SAFE TO DELETE"),
}


def _orphan_configs() -> list[str]:
    """Config files carrying another machine's name that nothing reads any more.

    They look like settings and are inert: written by a mechanism since removed,
    read by no current code. Detected rather than hardcoded so a NEW machine's
    leftovers surface the same way.
    """
    root = Path(os.environ.get("METIS_RC_ROOT", ".")) / "system" / "config"
    live = {m[0] for m in _SETTINGS_MAP}
    out = []
    try:
        import socket
        me = socket.gethostname().lower()
        for f in sorted(root.iterdir()):
            if not f.is_file() or f.name in live or f.suffix not in (".json", ".md"):
                continue
            stem = f.stem.lower()
            # "<known-setting>-<something>" where <something> is not this machine
            for known in ("user-preferences", "mcp-health", "eval-results", "setup"):
                if stem.startswith(known + "-") and me not in stem:
                    out.append(f.name)
                    break
    except Exception:
        pass
    return out


@router.get("/api/partial/metis/settings-map", response_class=HTMLResponse)
async def metis_settings_map(request: Request):
    root = Path(os.environ.get("METIS_RC_ROOT", ".")) / "system" / "config"
    rows = []
    for name, kind, what, where in _SETTINGS_MAP:
        path = root / name if name != ".env" else root.parent / ".env"
        exists = path.exists()
        # Skipping a missing file HIDES a setting the user may want to change:
        # `network-policy.json` does not exist until something writes it, so the
        # allowlist silently runs on defaults and the panel said nothing at all.
        # Internal state files are different — a missing one is not a setting.
        if not exists and kind == "state":
            continue
        colour, label = _KIND_STYLE[kind]
        rows.append((colour, label, name, what,
                     where if exists else f"{where} — not created yet, defaults apply"))
    for name in _orphan_configs():
        colour, label = _KIND_STYLE["orphan"]
        rows.append((colour, label, name,
                     "Left over from another computer — nothing reads it", "safe to delete"))

    body = "".join(f"""
      <div style="display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--m-rule-soft);">
        <span style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.08em;color:{c};
                     flex-shrink:0;width:136px;padding-top:2px;">{lbl}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-family:var(--m-mono);font-size:11px;">{n}</div>
          <div style="font-size:11px;color:var(--m-muted);">{w} · <em>{wh}</em></div>
        </div>
      </div>""" for c, lbl, n, w, wh in rows)

    return HTMLResponse(f"""
    <div class="panel" style="padding:16px 18px;">
      <div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;
                  color:var(--m-muted);margin-bottom:8px;">WHERE SETTINGS LIVE</div>
      <div style="font-size:12px;color:var(--m-muted);margin-bottom:8px;">
        Most things you'd want to change are above, in Metis itself. The rest are here so you
        never have to guess which file matters.
      </div>
      {body}
    </div>""")


# ---------------------------------------------------------------------------
# Procedural memory — the layer that was a number and nothing else
#
# The memory overview counted procedural_memory and stopped there. Twelve
# procedures existed, each one a worked-out way of doing something, and the only
# thing any surface said about them was "12". A layer you cannot read is a layer
# you cannot trust, correct, or reuse — and Metis volunteers these in
# conversation, so the researcher needs to see what it is working from.


def _procedure_family(name: str) -> str:
    """Group by the prefix before an em dash: 'Course making — write one lesson'.

    Families emerged naturally because procedures get written in sets. Without
    grouping, a flat list of a dozen unrelated steps reads as noise.
    """
    for sep in ("—", " - ", ":"):
        if sep in name:
            head = name.split(sep, 1)[0].strip()
            if 3 < len(head) < 40:
                return head
    return "General"


@router.get("/api/partial/metis/procedures", response_class=HTMLResponse)
async def metis_procedures(request: Request, q: str = "", open_id: int = 0):
    """List every stored procedure, grouped, with its trigger and steps readable."""
    rows = db_query(
        "SELECT id, procedure_name, trigger_context, steps, success_count, "
        "       last_used, created_at, scope, project_id "
        "FROM procedural_memory ORDER BY procedure_name",
        default=[],
    ) or []

    if q:
        needle = q.lower()
        rows = [r for r in rows
                if needle in (r.get("procedure_name") or "").lower()
                or needle in (r.get("trigger_context") or "").lower()
                or needle in (r.get("steps") or "").lower()]

    families: dict[str, list[dict]] = {}
    for r in rows:
        families.setdefault(_procedure_family(r.get("procedure_name") or ""), []).append(dict(r))

    # Largest family first, "General" last — it is the leftovers bucket.
    ordered = sorted(families.items(),
                     key=lambda kv: (kv[0] == "General", -len(kv[1]), kv[0]))

    return templates.TemplateResponse(
        request,
        "partials/metis_procedures.html",
        {"families": ordered, "total": len(rows), "q": q, "open_id": open_id},
    )
