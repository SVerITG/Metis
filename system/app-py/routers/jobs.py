"""
routers/jobs.py — Scheduler management API endpoints.
"""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


@router.get("/api/scheduler/status")
async def scheduler_status():
    from scheduler import get_job_status, scheduler
    return JSONResponse({
        "running": scheduler.running,
        "jobs":    get_job_status(),
    })


@router.get("/api/scheduler/jobs")
async def list_jobs():
    from scheduler import get_job_status
    return JSONResponse({"status": "ok", "jobs": get_job_status()})


@router.post("/api/scheduler/jobs/{job_id}/run")
async def trigger_job(job_id: str):
    """Run a job immediately in the background (fire-and-forget)."""
    from scheduler import JOB_FUNCS
    func = JOB_FUNCS.get(job_id)
    if func is None:
        return JSONResponse({"status": "error", "message": f"Unknown job: {job_id}"}, status_code=404)
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, func)
    return JSONResponse({"status": "ok", "message": f"Job '{job_id}' triggered."})


@router.post("/api/scheduler/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    from scheduler import scheduler
    try:
        scheduler.pause_job(job_id)
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)


@router.post("/api/scheduler/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    from scheduler import scheduler
    try:
        scheduler.resume_job(job_id)
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=400)


@router.get("/api/partial/today/automation-next", response_class=HTMLResponse)
async def automation_next_inline():
    """Single-line next-run label for the dateline strip."""
    try:
        from scheduler import scheduler
        job = scheduler.get_job("morning_scan")
        if job and job.next_run_time:
            import datetime
            dt = job.next_run_time.astimezone()
            now = datetime.datetime.now().astimezone()
            diff = dt - now
            h = int(diff.total_seconds() // 3600)
            label = f"next scan in {h}h" if h >= 1 else f"next scan in {int(diff.total_seconds()//60)}m"
            return HTMLResponse(
                f'<span id="scheduler-next" style="margin-left:1rem;font-family:var(--m-mono);font-size:10px;'
                f'letter-spacing:0.1em;color:var(--m-muted);" '
                f'hx-get="/api/partial/today/automation-next" hx-trigger="every 60s" hx-swap="outerHTML">'
                f'<i class="bi bi-clock" style="margin-right:4px;"></i>{label}</span>'
            )
    except Exception:
        pass
    return HTMLResponse('<span id="scheduler-next"></span>')


@router.get("/api/scheduler/settings")
async def get_scheduler_settings():
    """Return current per-job settings merged with defaults."""
    from scheduler import JOB_DEFAULTS, JOB_LABELS, _load_job_settings
    saved = _load_job_settings()
    merged = {}
    for job_id, defaults in JOB_DEFAULTS.items():
        merged[job_id] = {**defaults, **saved.get(job_id, {}), "label": JOB_LABELS.get(job_id, job_id)}
    return JSONResponse(merged)


@router.post("/api/scheduler/settings")
async def save_scheduler_settings(request: Request):
    """Persist job settings and reschedule without restarting the dashboard."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "message": "Invalid JSON"}, status_code=400)

    from scheduler import apply_settings_and_reschedule, JOB_DEFAULTS
    # Validate: only accept known job IDs
    cleaned = {}
    for job_id in JOB_DEFAULTS:
        if job_id in body:
            entry = body[job_id]
            cleaned[job_id] = {
                "enabled": bool(entry.get("enabled", True)),
                "time": str(entry.get("time", JOB_DEFAULTS[job_id].get("time", "07:00"))),
            }
            if "day" in entry:
                cleaned[job_id]["day"] = str(entry["day"])

    apply_settings_and_reschedule(cleaned)
    return JSONResponse({"status": "ok", "saved": list(cleaned.keys())})


@router.get("/api/partial/metis/automation-log", response_class=HTMLResponse)
async def automation_log_partial():
    """HTMX partial: recent job run log for the Metis → Automation section."""
    import datetime
    try:
        from db import db_query
        rows = db_query(
            "SELECT job_type, status, details, created_at FROM jobs_log "
            "ORDER BY created_at DESC LIMIT 30"
        )
    except Exception:
        rows = []

    if not rows:
        return HTMLResponse(
            '<div style="padding:18px 22px;font-family:var(--m-display);font-style:italic;'
            'font-size:13px;color:var(--m-muted);">No jobs have run yet.</div>'
        )

    from scheduler import JOB_LABELS
    items_html = ""
    for r in rows:
        job_id  = r.get("job_type", "")
        status  = r.get("status", "")
        details = (r.get("details") or "")[:80]
        ran_at  = (r.get("created_at") or "")[:16].replace("T", " ")
        label   = JOB_LABELS.get(job_id, job_id)
        dot_col = {"ok": "var(--m-ok)", "error": "var(--m-alert)", "skip": "var(--m-muted)"}.get(status, "var(--m-line)")
        items_html += f"""
<div style="display:flex;align-items:baseline;gap:8px;padding:5px 0;border-bottom:1px solid var(--m-rule-soft);">
  <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{dot_col};flex-shrink:0;margin-top:4px;"></span>
  <span style="font-family:var(--m-mono);font-size:9px;color:var(--m-muted);min-width:120px;flex-shrink:0;">{ran_at}</span>
  <span style="font-family:var(--m-mono);font-size:10px;color:var(--m-ink);min-width:170px;flex-shrink:0;">{label}</span>
  <span style="font-size:11px;color:var(--m-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{details}</span>
</div>"""

    return HTMLResponse(f"""
<div id="automation-log"
     hx-get="/api/partial/metis/automation-log"
     hx-trigger="every 60s"
     hx-swap="outerHTML"
     style="padding:4px 0;">
  {items_html}
</div>""")


@router.get("/api/partial/today/automation", response_class=HTMLResponse)
async def automation_status_partial():
    """HTMX partial: scheduler job status strip with settings controls."""
    import datetime
    from scheduler import get_job_status, scheduler, JOB_DEFAULTS, JOB_LABELS, _load_job_settings

    jobs = get_job_status()
    running = scheduler.running
    saved = _load_job_settings()

    def _fmt_next(iso: str | None) -> str:
        if not iso:
            return "paused"
        try:
            dt = datetime.datetime.fromisoformat(iso).astimezone()
            now = datetime.datetime.now().astimezone()
            diff = dt - now
            h = int(diff.total_seconds() // 3600)
            if h < 1:
                return f"in {int(diff.total_seconds()//60)}m"
            if h < 24:
                return f"in {h}h"
            return dt.strftime("%a %H:%M")
        except Exception:
            return (iso or "")[:16]

    # Build job rows — include all defaults even if not yet registered
    job_map = {j["id"]: j for j in jobs}
    rows_html = ""
    for job_id, defaults in JOB_DEFAULTS.items():
        cfg = {**defaults, **saved.get(job_id, {})}
        j = job_map.get(job_id, {})
        status = j.get("last_status") or ""
        dot_col = {"ok": "var(--m-ok)", "error": "var(--m-alert)", "skip": "var(--m-muted)"}.get(status, "var(--m-line)")
        next_lbl = _fmt_next(j.get("next_run")) if j else cfg.get("time", "—")
        last_msg = (j.get("last_message") or "")[:55]
        enabled = cfg.get("enabled", True)
        toggle_col = "var(--m-accent)" if enabled else "var(--m-line)"
        toggle_title = "Disable" if enabled else "Enable"
        time_val = cfg.get("time", "07:00")
        label = JOB_LABELS.get(job_id, job_id)

        rows_html += f"""
<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--m-rule-soft);">
  <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{dot_col};flex-shrink:0;"></span>
  <span style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.10em;color:var(--m-ink);min-width:180px;flex-shrink:0;">{label}</span>
  <span style="font-family:var(--m-mono);font-size:10px;color:var(--m-muted);min-width:52px;">{next_lbl}</span>
  <span style="font-size:11px;color:var(--m-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;">{last_msg}</span>
  <input type="time" value="{time_val}"
         style="font-family:var(--m-mono);font-size:10px;padding:2px 4px;background:var(--m-surface);border:1px solid var(--m-line);border-radius:3px;color:var(--m-ink);width:72px;"
         onchange="updateJobTime('{job_id}', this.value)" title="Scheduled time">
  <button style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.1em;padding:2px 6px;border:1px solid {toggle_col};border-radius:3px;background:transparent;color:{toggle_col};cursor:pointer;flex-shrink:0;"
          onclick="toggleJob('{job_id}', {'false' if enabled else 'true'})" title="{toggle_title}">
    {'ON' if enabled else 'OFF'}</button>
  <button style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.1em;padding:2px 6px;border:1px solid var(--m-line);border-radius:3px;background:transparent;color:var(--m-muted);cursor:pointer;flex-shrink:0;"
          onclick="triggerJob('{job_id}')" title="Run now">RUN</button>
</div>"""

    status_label = "RUNNING" if running else "STOPPED"
    status_color = "var(--m-ok)" if running else "var(--m-alert)"

    return f"""
<div id="automation-panel"
     hx-get="/api/partial/today/automation"
     hx-trigger="every 120s"
     hx-swap="outerHTML">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
    <span style="font-family:var(--m-display);font-size:13px;font-weight:500;color:var(--m-ink);">Automation</span>
    <span style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.12em;color:{status_color};">{status_label}</span>
  </div>
  {rows_html if JOB_DEFAULTS else '<p style="font-size:12px;color:var(--m-muted);margin:0;">No jobs registered.</p>'}
  <p style="font-family:var(--m-mono);font-size:9px;color:var(--m-muted);margin-top:8px;letter-spacing:0.08em;">
    Changes to time/on-off are saved and applied immediately — no restart needed.
  </p>
</div>

<script>
(function() {{
  // In-memory settings state (keyed by job_id)
  if (!window._jobSettings) window._jobSettings = {{}};

  window.updateJobTime = function(jobId, timeVal) {{
    if (!window._jobSettings[jobId]) window._jobSettings[jobId] = {{}};
    window._jobSettings[jobId].time = timeVal;
    _saveJobSettings();
  }};

  window.toggleJob = function(jobId, enabledStr) {{
    const enabled = enabledStr === 'true';
    if (!window._jobSettings[jobId]) window._jobSettings[jobId] = {{}};
    window._jobSettings[jobId].enabled = enabled;
    _saveJobSettings();
    // Refresh panel to update button label/color
    htmx.trigger('#automation-panel', 'refresh');
  }};

  function _saveJobSettings() {{
    fetch('/api/scheduler/settings', {{
      method: 'POST',
      headers: {{'content-type': 'application/json'}},
      body: JSON.stringify(window._jobSettings),
    }}).then(r => r.json()).then(d => {{
      if (d.status !== 'ok') console.warn('Job settings save failed:', d);
    }}).catch(e => console.warn('Job settings error:', e));
  }}
}})();
</script>"""
