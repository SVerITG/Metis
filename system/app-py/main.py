"""
main.py — Metis Dashboard FastAPI application.
"""

import datetime
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import (
    capture,
    jobs,
    knowledge,
    learning,
    meetings,
    memory_health,
    metis_tab,
    planner,
    setup,
    speakers,
    teach,
    thinking,
    today,
    transcription,
    work,
)

log = logging.getLogger("metis")


class _SkipBootScan(Exception):
    """Internal sentinel: skip the startup news/literature scan (e.g. demo mode)."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    from db import run_migrations
    applied = run_migrations()
    if applied:
        log.info("DB migrations applied: %s", ", ".join(applied))

    # Per-feature table init — fail-soft. Each runs in its own try/except so a DB
    # problem disables only that feature instead of crashing the whole app. These
    # used to run at module-import time, which meant any DB error took the entire
    # dashboard down (the 2026-06-19 outage). See stability evaluation.
    for _mod, _fn in (("routers.speakers", "_ensure_table"),
                      ("routers.meetings", "_ensure_columns")):
        try:
            import importlib
            getattr(importlib.import_module(_mod), _fn)()
        except Exception as exc:
            log.warning("[startup] %s.%s skipped (feature degraded): %s", _mod, _fn, exc)

    # Startup health check — runs after migrations so tables exist
    try:
        from startup_eval import run_startup_eval
        run_startup_eval()
    except Exception as exc:
        log.warning("Startup eval skipped: %s", exc)

    # Ensure MCP tools are findable — add src to sys.path at startup
    import sys as _sys
    _rc = os.environ.get("METIS_RC_ROOT", "")
    if _rc:
        _mcp_src = str(Path(_rc) / "system" / "mcp-server" / "src")
        if _mcp_src not in _sys.path:
            _sys.path.insert(0, _mcp_src)
        del _mcp_src
    del _rc
    # In demo mode the scheduler is NOT started: its catch-up sequence would
    # immediately run the morning news/literature scan, pulling the real user's
    # feeds and library folder into the demo database and overwriting the
    # curated demo data. The demo is a static, self-contained snapshot.
    if os.environ.get("METIS_DEMO") == "1":
        log.info("[startup] Demo mode — scheduler not started (no background scans)")
    else:
        try:
            from scheduler import scheduler, setup_jobs
            setup_jobs()
            scheduler.start()
            log.info("APScheduler started")
        except Exception as exc:
            log.warning("Scheduler could not start: %s", exc)
    try:
        from inbox_watcher import start_inbox_watcher
        start_inbox_watcher()
    except Exception as exc:
        log.warning("Inbox watcher could not start: %s", exc)
    # On startup: run news scan if last scan was more than 4 hours ago,
    # then pre-generate today's morning brief.
    #
    # In demo mode this is skipped entirely: a live scan would pull the real
    # user's news feeds and literature folder into the demo database (breaking
    # the curated, coherent demo data) and try to generate a brief via the API.
    _demo_mode = os.environ.get("METIS_DEMO") == "1"
    if _demo_mode:
        log.info("[startup] Demo mode — skipping boot scan + brief generation")
    try:
        if _demo_mode:
            raise _SkipBootScan()
        import sqlite3 as _sq3
        import threading

        def _hours_since_last_scan() -> float:
            """Return hours since last successful news scan (jobs_log), or 999 if never."""
            try:
                import datetime as _dt
                from db import get_db_path
                db_p = str(get_db_path())
                conn = _sq3.connect(db_p, timeout=5)
                row = conn.execute(
                    "SELECT created_at FROM jobs_log WHERE job_type IN ('morning_scan','news_scan') "
                    "AND status='ok' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                conn.close()
                if row and row[0]:
                    last = _dt.datetime.fromisoformat(row[0])
                    return (_dt.datetime.now() - last).total_seconds() / 3600
            except Exception:
                pass
            return 999.0

        def _boot_scan_and_brief():
            try:
                if _hours_since_last_scan() > 4:
                    log.info("[startup] Running news scan (last scan >4 h ago)")
                    from metis_mcp.tools.content_scan import scan_literature_folder, scan_news_feeds
                    scan_news_feeds(max_per_feed=10)
                    scan_literature_folder()
                    # Log success so the scheduler doesn't double-scan today
                    try:
                        import datetime as _dt
                        from db import get_db_path
                        db_p = str(get_db_path())
                        conn = _sq3.connect(db_p, timeout=5)
                        conn.execute(
                            "INSERT INTO jobs_log (job_type, status, details, created_at) VALUES (?,?,?,?)",
                            ("morning_scan", "ok", "startup scan", _dt.datetime.now().isoformat()),
                        )
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
            except Exception as exc:
                log.debug("Startup news scan skipped: %s", exc)
            # Pre-generate morning brief after scan
            try:
                from routers.today import _get_or_generate_brief
                _get_or_generate_brief()
            except Exception as exc:
                log.debug("Startup brief generation skipped: %s", exc)

        threading.Thread(target=_boot_scan_and_brief, daemon=True, name="boot-scan").start()
    except _SkipBootScan:
        pass  # demo mode — intentionally no scan
    except Exception as exc:
        log.debug("Could not start boot scan thread: %s", exc)
    yield
    try:
        from scheduler import scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Metis Dashboard", docs_url=None, redoc_url=None, lifespan=lifespan)

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Global error handler — catch unhandled 500s so the dashboard never shows a
# blank page or drops the connection silently. HTMX partials get a styled error
# snippet; full page requests get a redirect to root with an error toast.
@app.exception_handler(500)
async def _handle_500(request: Request, exc: Exception):
    log.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    # HTMX partial requests: return an error snippet the page can display
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            '<div class="panel panel-pad" role="alert" '
            'style="margin:12px 0;border-left:3px solid var(--m-alert);">'
            "Something went wrong loading this section — I'll try again in a moment."
            '</div>',
            status_code=200,  # 200 so HTMX swaps it into the page
        )
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'><title>Metis</title></head>"
        "<body style=\"font-family:'Newsreader',Georgia,serif;background:#f5f2ea;"
        "color:#2c3a33;max-width:560px;margin:80px auto;padding:0 24px;line-height:1.65;\">"
        "<h3 style='font-weight:500;color:#1f2a24;'>Something went wrong loading this view.</h3>"
        "<p>The page hit an error and couldn&#39;t render. Nothing was lost — "
        "try again, or return to the dashboard.</p>"
        "<p><a href='/' style='color:#2d4a3a;'>Back to dashboard</a></p>"
        "</body></html>",
        status_code=500,
    )

# Inject user name into every template so today.html greeting JS can use it
try:
    from routers.today import _user_name as _get_metis_user_name
    templates.env.globals["_metis_user_name"] = _get_metis_user_name
except Exception:
    templates.env.globals["_metis_user_name"] = lambda: "Researcher"

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

# Tab routers — all live under /tab prefix for the full-page variants;
# the partials/api routes are registered without prefix via the router itself.
app.include_router(today.router)
app.include_router(knowledge.router)
app.include_router(meetings.router)
app.include_router(learning.router)
app.include_router(work.router)
app.include_router(thinking.router)
app.include_router(planner.router)
app.include_router(teach.router)
app.include_router(metis_tab.router)
app.include_router(memory_health.router)
app.include_router(capture.router, prefix="/api")
app.include_router(transcription.router)
app.include_router(speakers.router)
app.include_router(jobs.router)
app.include_router(setup.router)

# ── PWA capture page — standalone mobile-friendly route ─────────────────────
@app.get("/capture", response_class=HTMLResponse)
async def pwa_capture_page(request: Request):
    """Standalone capture page — add to phone home screen for one-tap access."""
    return templates.TemplateResponse(request, "capture.html", {})

@app.get("/manifest.json")
async def pwa_manifest():
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "name": "Metis Capture",
        "short_name": "Capture",
        "description": "Capture ideas, notes, tasks, and questions for your Research Cortex",
        "start_url": "/capture",
        "display": "standalone",
        "background_color": "#1a1a1a",
        "theme_color": "#3b82f6",
        "icons": [
            {"src": "/static/metis-icon.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/metis-icon.png", "sizes": "512x512", "type": "image/png"},
        ],
    })

# ---------------------------------------------------------------------------
# Root + named tab full-page routes
# ---------------------------------------------------------------------------

_TAB_TEMPLATES = {
    "today": "today.html",
    "knowledge": "knowledge.html",
    "meetings": "meetings.html",
    "learning": "learning.html",
    "work": "work.html",
    "thinking": "thinking.html",
    "planner": "planner.html",
    "teach": "teach.html",
    "metis": "metis_tab.html",
}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
     request, "today.html", {"active_tab": "today"}
 )


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.post("/api/restart")
async def restart_dashboard():
    """Restart the dashboard process. Returns 202 immediately; server comes back in ~3 s."""
    import threading, os, sys

    def _do_restart():
        import time
        time.sleep(0.6)  # Let the HTTP response be sent first
        os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=_do_restart, daemon=False, name="restart").start()
    return JSONResponse({"status": "restarting"}, status_code=202)


@app.get("/{tab}", response_class=HTMLResponse)
async def tab_page(request: Request, tab: str):
    template_name = _TAB_TEMPLATES.get(tab)
    if template_name is None:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request, template_name, {"active_tab": tab}
    )


# ---------------------------------------------------------------------------
# API utilities
# ---------------------------------------------------------------------------


@app.get("/api/check-db-mtime")
async def check_db_mtime():
    """Return the mtime of the SQLite database file."""
    try:
        from db import get_db_path

        db_path = get_db_path()
        mtime = db_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    return JSONResponse({"mtime": mtime})


@app.get("/api/trust-badge", response_class=HTMLResponse)
async def trust_badge():
    """Return an HTML snippet with today's agent call count + network policy."""
    today = str(datetime.date.today())
    try:
        from db import db_scalar

        count = db_scalar(
            f"SELECT COUNT(*) FROM sessions WHERE started_at LIKE '{today}%'",
            default=0,
        )
    except Exception:
        count = 0

    # Read network policy
    policy = "normal"
    try:
        rc_root = os.environ.get("METIS_RC_ROOT", "")
        if rc_root:
            p = Path(rc_root) / "system" / "config" / "network-policy.json"
            if p.exists():
                import json
                data = json.loads(p.read_text(encoding="utf-8"))
                policy = data.get("policy", "normal")
    except Exception:
        pass

    policy_icon = {"strict": "bi-shield-lock", "offline": "bi-wifi-off", "normal": "bi-shield-check"}.get(policy, "bi-shield-check")
    policy_cls  = {"strict": "text-warning", "offline": "text-danger", "normal": ""}.get(policy, "")

    label = f"{count} calls today" if count else "Data stays local"
    return HTMLResponse(
        f'<i class="bi {policy_icon} {policy_cls}"></i>'
        f'<span class="trust-badge-text">{label}</span>'
    )


@app.get("/api/session/touch-planning")
async def touch_planning_files():
    """Append last-session timestamp to active project PLANNING.md files.

    Called by the stop hook at session end. Queries active projects with an
    external_path, finds PLANNING.md there, and appends a dated marker line
    (idempotent — no duplicate markers on the same day).
    """
    import json
    from pathlib import Path as _Path

    today = str(datetime.date.today())
    marker = f"\n\n---\n_Last Metis session: {today}_\n"
    updated = []

    try:
        from db import db_query

        rows = db_query(
            "SELECT project_id, title, external_path FROM projects "
            "WHERE status = 'active' AND external_path IS NOT NULL AND external_path != ''"
        )
        for row in rows:
            ext = (row.get("external_path") or "").strip()
            if not ext:
                continue
            planning = _Path(ext) / "PLANNING.md"
            if planning.exists():
                content = planning.read_text(encoding="utf-8")
                if f"_Last Metis session: {today}_" not in content:
                    planning.write_text(content + marker, encoding="utf-8")
                    updated.append(str(planning))
    except Exception:
        pass

    return JSONResponse({"updated": updated, "date": today})


# ---------------------------------------------------------------------------
# MCP server status — used by the offline banner in base.html
# ---------------------------------------------------------------------------

@app.get("/api/mcp/status")
async def mcp_status():
    """Returns 200 if the metis_mcp package is importable (i.e. venv is active)."""
    import sys
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        mcp_src = str(Path(rc_root) / "system" / "mcp-server" / "src")
        if mcp_src not in sys.path:
            sys.path.insert(0, mcp_src)
    # Clear a broken partial import — a module with no __file__ is a sign of a failed load
    mod = sys.modules.get("metis_mcp")
    if mod is not None and not getattr(mod, "__file__", None):
        del sys.modules["metis_mcp"]
    try:
        import metis_mcp  # noqa: F401
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        return JSONResponse({"status": "offline", "reason": str(exc)}, status_code=503)


@app.post("/api/mcp/reload")
async def mcp_reload():
    """Try to connect to the MCP tools layer. Called by the Reconnect button."""
    import sys, importlib
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        mcp_src = str(Path(rc_root) / "system" / "mcp-server" / "src")
        if mcp_src not in sys.path:
            sys.path.insert(0, mcp_src)
    try:
        # Force re-import in case a previous attempt left a broken partial import
        if "metis_mcp" in sys.modules:
            importlib.reload(sys.modules["metis_mcp"])
        else:
            import metis_mcp  # noqa: F401
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        return JSONResponse(
            {"status": "offline",
             "reason": "Metis tools couldn't load. Make sure you opened Metis using the desktop shortcut, then try again.",
             "detail": str(exc)},
            status_code=503,
        )
