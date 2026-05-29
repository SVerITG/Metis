"""
scheduler.py — APScheduler background jobs for the Metis dashboard.

Jobs registered here run automatically on their cron schedules when the
dashboard is running. They are the same operations as the manual scan
buttons — APScheduler just calls them without user interaction.

Default schedule (all overridable via /api/scheduler/settings):
  morning_scan        07:00 daily  — news feeds + PubMed + OpenAlex
  library_index       07:30 daily  — library file inventory
  inbox_process       08:00 daily  — process pending inbox items
  brief_synthesis     08:30 daily  — pre-generate AI morning brief (runs AFTER scans)
  evening_reflexion   20:00 daily  — aggregate reflexions for self-improvement
  memory_consolidation 22:00 daily — distil recent agent runs into memory_entries
  weekly_summary      Sun 09:00    — generate weekly summary
  nightly_backup      23:00 daily  — copy metis.sqlite to backups/
"""

import asyncio
import datetime
import logging
import os
import shutil
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger("metis.scheduler")

scheduler = AsyncIOScheduler(timezone="UTC")

# In-memory last-run cache (keyed by job_id)
_last_results: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_job(job_id: str, status: str, message: str) -> None:
    ran_at = datetime.datetime.now().isoformat(timespec="seconds")
    _last_results[job_id] = {"job_id": job_id, "status": status, "message": message, "ran_at": ran_at}
    try:
        from db import db_execute
        db_execute(
            "INSERT INTO jobs_log (job_type, status, details, created_at) VALUES (?, ?, ?, ?)",
            (job_id, status, message[:500], ran_at),
        )
    except Exception as exc:
        log.warning("Could not write to jobs_log: %s", exc)


def _morning_hour() -> int:
    """Read preferred morning scan hour from user-config.yaml, default 7."""
    cfg = _load_job_settings()
    try:
        t = cfg.get("morning_scan", {}).get("time", "07:00")
        return int(str(t).split(":")[0])
    except Exception:
        pass
    return 7


def _load_job_settings() -> dict:
    """Load per-job schedule settings from user-config.yaml jobs section."""
    try:
        rc = os.environ.get("METIS_RC_ROOT", "")
        if not rc:
            return {}
        cfg_path = Path(rc) / "system" / "config" / "user-config.yaml"
        if cfg_path.exists():
            import yaml
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            # Support both old-style schedule.morning_brief_time and new jobs section
            jobs = cfg.get("jobs", {})
            if not jobs and "schedule" in cfg:
                t = cfg["schedule"].get("morning_brief_time", "07:00")
                jobs["morning_scan"] = {"enabled": True, "time": t}
            return jobs
    except Exception:
        pass
    return {}


def save_job_settings(jobs: dict) -> None:
    """Persist job settings to user-config.yaml."""
    try:
        import yaml
        rc = os.environ.get("METIS_RC_ROOT", "")
        if not rc:
            return
        cfg_path = Path(rc) / "system" / "config" / "user-config.yaml"
        cfg = {}
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        cfg["jobs"] = jobs
        cfg_path.write_text(yaml.dump(cfg, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    except Exception as exc:
        log.warning("Could not save job settings: %s", exc)


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' → (hour, minute). Returns (7, 0) on failure."""
    try:
        parts = str(time_str).split(":")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return 7, 0


# ---------------------------------------------------------------------------
# Job functions (synchronous — run in APScheduler's thread pool)
# ---------------------------------------------------------------------------

def job_morning_scan() -> None:
    """News feeds + literature folder scan + PubMed + OpenAlex alerts."""
    log.info("[scheduler] morning_scan starting")
    parts = []

    # RSS feeds and local literature folder
    try:
        from metis_mcp.tools.content_scan import scan_literature_folder, scan_news_feeds
        news_r = scan_news_feeds(max_per_feed=10)
        lit_r  = scan_literature_folder()
        parts.append(f"News: {news_r.get('news_added', 0)} signals")
        parts.append(f"Lit: {lit_r.get('papers_added', 0)} items")
    except Exception as exc:
        log.warning("[scheduler] news/lit scan error: %s", exc)
        parts.append("News/lit: error")

    # PubMed daily alerts
    try:
        from metis_mcp.tools.literature_monitor import _pubmed_esearch, _pubmed_esummary, _insert_article, _user_pubmed_query
        import sqlite3 as _sq, asyncio as _a
        from metis_mcp.config import paths as _p
        _pubmed_query = _user_pubmed_query()
        pmids = _pubmed_esearch(_pubmed_query, reldate=1, max_results=15)
        summaries = _pubmed_esummary(pmids) if pmids else []
        pub_added = 0
        if summaries:
            con = _sq.connect(str(_p.db))
            for item in summaries:
                pmid = item["pmid"]
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                authors = item.get("authors", "")
                journal = item.get("source", "PubMed")
                summary_text = f"{authors} ({item.get('pubdate', '')}). {journal}."
                if _insert_article(con, item["title"], summary_text, url, "PubMed", "pubmed,article"):
                    pub_added += 1
            con.commit()
            con.close()
        parts.append(f"PubMed: {pub_added} papers")
    except Exception as exc:
        log.warning("[scheduler] PubMed scan error: %s", exc)
        parts.append("PubMed: error")

    # OpenAlex daily alerts
    try:
        from metis_mcp.tools.literature_monitor import _openalex_search, _reconstruct_abstract, _insert_article, _user_openalex_query
        import sqlite3 as _sq
        from metis_mcp.config import paths as _p
        import datetime as _dt
        from_date = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        _alex_query = _user_openalex_query()
        items = _openalex_search(_alex_query, from_date=from_date, max_results=10)
        alex_added = 0
        if items:
            con = _sq.connect(str(_p.db))
            for item in items:
                title = item.get("title") or "Untitled"
                doi = item.get("doi") or item.get("id") or ""
                if not doi:
                    continue
                author_names = [
                    (a.get("author") or {}).get("display_name", "")
                    for a in (item.get("authorships") or [])[:4]
                ]
                authors = "; ".join(n for n in author_names if n)
                abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
                pub_date = item.get("publication_date", "")
                journal = ((item.get("primary_location") or {}).get("source") or {}).get("display_name", "")
                summary_text = f"{authors} ({pub_date}). {journal}. {abstract[:300]}".strip()
                if _insert_article(con, title, summary_text, doi, "OpenAlex", "openalex,article"):
                    alex_added += 1
            con.commit()
            con.close()
        parts.append(f"OpenAlex: {alex_added} papers")
    except Exception as exc:
        log.warning("[scheduler] OpenAlex scan error: %s", exc)
        parts.append("OpenAlex: error")

    msg = " · ".join(parts)
    _log_job("morning_scan", "ok", msg)
    log.info("[scheduler] morning_scan done: %s", msg)


def job_library_index() -> None:
    """Library file inventory scan."""
    log.info("[scheduler] library_index starting")
    try:
        from metis_mcp.tools.content_scan import scan_literature_folder
        r = scan_literature_folder()
        msg = f"Indexed {r.get('files_indexed', '?')} files."
        _log_job("library_index", "ok", msg)
        log.info("[scheduler] library_index done: %s", msg)
    except Exception as exc:
        _log_job("library_index", "error", str(exc)[:300])
        log.error("[scheduler] library_index failed: %s", exc)


def job_nightly_backup() -> None:
    """Safe online backup of metis.sqlite using the SQLite backup API (WAL-safe)."""
    log.info("[scheduler] nightly_backup starting")
    try:
        import sqlite3 as _sq3
        rc = os.environ.get("METIS_RC_ROOT", "")
        db_path = Path(rc) / "system" / "app" / "data" / "metis.sqlite" if rc else None
        # Fall back to db.get_db_path() if METIS_RC_ROOT not set
        if not db_path or not db_path.exists():
            try:
                from db import get_db_path
                db_path = get_db_path()
            except Exception:
                pass
        if not db_path or not db_path.exists():
            _log_job("nightly_backup", "skip", "DB file not found")
            return
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        dst = backup_dir / f"metis.{datetime.date.today().strftime('%Y%m%d')}.sqlite"
        if dst.exists():
            _log_job("nightly_backup", "skip", f"Backup {dst.name} already exists")
            return
        # SQLite online backup API — safe even while the database is open and in WAL mode
        src_conn = _sq3.connect(str(db_path))
        dst_conn = _sq3.connect(str(dst))
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        # Keep only last 7 backups to avoid filling OneDrive
        all_backups = sorted(backup_dir.glob("metis.????????.sqlite"))
        for old in all_backups[:-7]:
            try:
                old.unlink()
            except Exception:
                pass
        _log_job("nightly_backup", "ok", f"Backed up to backups/{dst.name}")
        log.info("[scheduler] nightly_backup: %s", dst.name)
    except Exception as exc:
        _log_job("nightly_backup", "error", str(exc)[:300])
        log.error("[scheduler] nightly_backup failed: %s", exc)


def _notify_windows(title: str, message: str) -> None:
    """Send a Windows toast notification via PowerShell BurntToast (if available).

    Falls back to a silent no-op on non-Windows or when PowerShell is absent.
    The notification fires in the Windows Action Center — no popup window, no focus steal.
    """
    import subprocess, shutil
    try:
        ps = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if not ps:
            return
        # Try BurntToast first; fall back to basic Windows notification API
        script = (
            f"if (Get-Module -ListAvailable -Name BurntToast -ErrorAction SilentlyContinue) {{"
            f"  Import-Module BurntToast -ErrorAction SilentlyContinue;"
            f"  New-BurntToastNotification -Text '{title}','{message}' -ErrorAction SilentlyContinue"
            f"}} else {{"
            f"  Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue;"
            f"  $notify = New-Object System.Windows.Forms.NotifyIcon;"
            f"  $notify.Icon = [System.Drawing.SystemIcons]::Information;"
            f"  $notify.Visible = $true;"
            f"  $notify.ShowBalloonTip(5000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info);"
            f"  Start-Sleep -Seconds 1;"
            f"  $notify.Dispose()"
            f"}}"
        )
        subprocess.Popen(
            [ps, "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
            creationflags=0x08000000 if os.name == "nt" else 0,  # CREATE_NO_WINDOW on Windows
        )
    except Exception:
        pass


def job_brief_synthesis() -> None:
    """Pre-generate AI morning brief — respects brief_mode setting."""
    log.info("[scheduler] brief_synthesis starting")
    # Honour brief_mode: skip scheduled synthesis when set to 'manual'
    try:
        import json as _json
        _rc = os.environ.get("METIS_RC_ROOT", "")
        _prefs_path = Path(_rc) / "system" / "config" / "user-preferences.json" if _rc else None
        if _prefs_path and _prefs_path.exists():
            _mode = _json.loads(_prefs_path.read_text()).get("brief_mode", "auto")
            if _mode == "manual":
                _log_job("brief_synthesis", "skip", "Manual mode — generate from the Today tab when ready")
                log.info("[scheduler] brief_synthesis skipped (manual mode)")
                return
    except Exception:
        pass
    try:
        from routers.today import _get_or_generate_brief
        result = _get_or_generate_brief()
        if result:
            _log_job("brief_synthesis", "ok", "Morning brief pre-generated.")
            _notify_windows("Metis — Morning Brief Ready", "Your morning brief is ready. Open the dashboard to read it.")
        else:
            _log_job("brief_synthesis", "skip", "Brief already cached or no context available.")
    except Exception as exc:
        _log_job("brief_synthesis", "error", str(exc)[:300])
        log.error("[scheduler] brief_synthesis failed: %s", exc)


def job_inbox_process() -> None:
    """Process pending inbox items — classify, log, and notify."""
    log.info("[scheduler] inbox_process starting")
    try:
        rc = os.environ.get("METIS_RC_ROOT", "")
        if not rc:
            _log_job("inbox_process", "skip", "METIS_RC_ROOT not set")
            return
        inbox_dir = Path(rc) / "inbox"
        if not inbox_dir.exists():
            _log_job("inbox_process", "skip", "Inbox directory not found")
            return

        from db import db_query, db_execute
        import datetime as _dt

        # Load already-logged paths to avoid double-processing
        logged_paths = set()
        try:
            rows = db_query("SELECT source_path FROM inbox_items")
            logged_paths = {r.get("source_path") for r in rows}
        except Exception:
            pass

        processed = 0
        for f in inbox_dir.rglob("*"):
            if not f.is_file():
                continue
            if str(f) in logged_paths:
                continue
            suffix = f.suffix.lower()
            ftype = {
                ".pdf": "literature", ".docx": "literature", ".epub": "literature",
                ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".ogg": "audio",
                ".png": "image", ".jpg": "image", ".jpeg": "image",
                ".csv": "data", ".xlsx": "data", ".dta": "data",
            }.get(suffix, "file")
            now_iso = _dt.datetime.now().isoformat(timespec="seconds")
            try:
                db_execute(
                    "INSERT OR IGNORE INTO inbox_items (filename, source_path, type, status, logged_at) VALUES (?, ?, ?, 'new', ?)",
                    (f.name, str(f), ftype, now_iso),
                )
                processed += 1
            except Exception:
                pass

        _log_job("inbox_process", "ok", f"Processed {processed} new inbox item(s).")
        log.info("[scheduler] inbox_process: %d new items", processed)
    except Exception as exc:
        _log_job("inbox_process", "error", str(exc)[:300])
        log.error("[scheduler] inbox_process failed: %s", exc)


def job_evening_reflexion() -> None:
    """Aggregate today's reflexions and generate self-improvement proposals."""
    log.info("[scheduler] evening_reflexion starting")
    try:
        from metis_mcp.tools.improvement import aggregate_reflexions
        import asyncio
        result = asyncio.run(aggregate_reflexions())
        # result is a list of TextContent — extract text
        text = result[0].text if result else ""
        count_line = next((l for l in text.splitlines() if "reflexion" in l.lower()), text[:80])
        _log_job("evening_reflexion", "ok", count_line or "Reflexions aggregated.")
        log.info("[scheduler] evening_reflexion done")
    except Exception as exc:
        _log_job("evening_reflexion", "error", str(exc)[:300])
        log.error("[scheduler] evening_reflexion failed: %s", exc)


def job_memory_consolidation() -> None:
    """Distil recent agent runs into structured memory entries (episodic → memory_entries)."""
    log.info("[scheduler] memory_consolidation starting")
    try:
        import asyncio
        from metis_mcp.tools.memory_curator import consolidate_session_memory
        result = asyncio.run(consolidate_session_memory(n_runs=50, min_quality="high"))
        text = result[0].text if result else ""
        # Extract the "Entries written" count from the report header
        for line in text.splitlines():
            if "Entries written:" in line or "Runs reviewed:" in line:
                _log_job("memory_consolidation", "ok", line.strip())
                log.info("[scheduler] memory_consolidation: %s", line.strip())
                return
        _log_job("memory_consolidation", "ok", "Consolidation complete.")
        log.info("[scheduler] memory_consolidation done")
    except Exception as exc:
        _log_job("memory_consolidation", "error", str(exc)[:300])
        log.error("[scheduler] memory_consolidation failed: %s", exc)


def job_weekly_summary() -> None:
    """Generate a weekly summary of ideas, meetings, papers, and progress."""
    log.info("[scheduler] weekly_summary starting")
    try:
        from db import db_query
        import datetime as _dt

        week_ago = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()

        ideas_count = 0
        papers_count = 0
        meetings_count = 0
        try:
            rows = db_query(f"SELECT COUNT(*) as n FROM ideas WHERE created_at >= '{week_ago}'")
            ideas_count = rows[0]["n"] if rows else 0
        except Exception:
            pass
        try:
            rows = db_query(f"SELECT COUNT(*) as n FROM news_briefs WHERE source_type='article' AND created_at >= '{week_ago}'")
            papers_count = rows[0]["n"] if rows else 0
        except Exception:
            pass
        try:
            rows = db_query(f"SELECT COUNT(*) as n FROM meetings WHERE created_at >= '{week_ago}'")
            meetings_count = rows[0]["n"] if rows else 0
        except Exception:
            pass

        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            today = _dt.date.today().isoformat()
            out_dir = Path(rc) / "outputs" / "reviews" / "metis"
            out_dir.mkdir(parents=True, exist_ok=True)
            summary = f"""# Weekly Summary — {today}

Generated automatically by Metis evening job.

## This week at a glance
- **Ideas captured:** {ideas_count}
- **Papers discovered:** {papers_count}
- **Meetings recorded:** {meetings_count}

## What's next
Open the Metis tab for agent run history, or run `/metis-weekly` for a full narrative summary.
"""
            (out_dir / f"{today}_weekly-auto.md").write_text(summary, encoding="utf-8")

        msg = f"Ideas: {ideas_count} · Papers: {papers_count} · Meetings: {meetings_count}"
        _log_job("weekly_summary", "ok", msg)
        log.info("[scheduler] weekly_summary done: %s", msg)
    except Exception as exc:
        _log_job("weekly_summary", "error", str(exc)[:300])
        log.error("[scheduler] weekly_summary failed: %s", exc)


# Exported map so the jobs router can trigger them by name
JOB_FUNCS: dict[str, callable] = {
    "brief_synthesis":       job_brief_synthesis,
    "morning_scan":          job_morning_scan,
    "library_index":         job_library_index,
    "inbox_process":         job_inbox_process,
    "evening_reflexion":     job_evening_reflexion,
    "memory_consolidation":  job_memory_consolidation,
    "weekly_summary":        job_weekly_summary,
    "nightly_backup":        job_nightly_backup,
}

# Human-readable labels for the UI
JOB_LABELS: dict[str, str] = {
    "brief_synthesis":      "Morning brief synthesis",
    "morning_scan":         "Morning scan (news + papers)",
    "library_index":        "Library index",
    "inbox_process":        "Inbox processing",
    "evening_reflexion":    "Evening reflexion",
    "memory_consolidation": "Nightly memory consolidation",
    "weekly_summary":       "Weekly summary",
    "nightly_backup":       "Nightly DB backup",
}

# Default schedule (used when no user-config entry exists)
# Order intentional: scans first, brief synthesis last (it reads what the scans produced)
# Memory consolidation runs at 22:00 — after the day's work, before the 23:00 backup.
JOB_DEFAULTS: dict[str, dict] = {
    "morning_scan":         {"enabled": True, "time": "07:00"},
    "library_index":        {"enabled": True, "time": "07:30"},
    "inbox_process":        {"enabled": True, "time": "08:00"},
    "brief_synthesis":      {"enabled": True, "time": "08:30"},
    "evening_reflexion":    {"enabled": True, "time": "20:00"},
    "memory_consolidation": {"enabled": True, "time": "22:00"},
    "weekly_summary":       {"enabled": True, "time": "09:00", "day": "sun"},
    "nightly_backup":       {"enabled": True, "time": "23:00"},
}


# ---------------------------------------------------------------------------
# Job status
# ---------------------------------------------------------------------------

def get_job_status() -> list[dict]:
    """Return all registered jobs with next run time and last result."""
    rows = []
    for job in scheduler.get_jobs():
        last = _last_results.get(job.id, {})
        rows.append({
            "id":           job.id,
            "name":         job.name,
            "next_run":     job.next_run_time.isoformat() if job.next_run_time else None,
            "paused":       job.next_run_time is None,
            "last_status":  last.get("status"),
            "last_message": last.get("message"),
            "last_ran":     last.get("ran_at"),
        })
    return rows


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_jobs() -> None:
    """Register all cron jobs from settings. Call once before scheduler.start()."""
    settings = _load_job_settings()
    registered = []

    for job_id, func in JOB_FUNCS.items():
        defaults = JOB_DEFAULTS.get(job_id, {"enabled": True, "time": "07:00"})
        cfg = {**defaults, **settings.get(job_id, {})}

        if not cfg.get("enabled", True):
            log.info("[scheduler] job '%s' disabled via settings", job_id)
            continue

        time_str = cfg.get("time", "07:00")
        hour, minute = _parse_time(time_str)
        day_of_week = cfg.get("day")  # e.g. "sun" for weekly jobs

        trigger_kwargs = {"hour": hour, "minute": minute}
        if day_of_week:
            trigger_kwargs["day_of_week"] = day_of_week

        scheduler.add_job(
            func,
            CronTrigger(**trigger_kwargs),
            id=job_id,
            name=JOB_LABELS.get(job_id, job_id),
            replace_existing=True,
            misfire_grace_time=None,  # never discard a missed fire
            coalesce=True,            # collapse multiple misfires into one run
        )
        registered.append(f"{job_id}@{time_str}" + (f"({day_of_week})" if day_of_week else ""))

    log.info("[scheduler] jobs registered: %s", ", ".join(registered))

    # Catch-up: if any morning jobs were missed (server started after their cron
    # time), fire them sequentially in one background thread — scan first, brief last.
    import threading as _threading
    import datetime as _dt
    now_local = _dt.datetime.now()
    settings_cu = _load_job_settings()

    # Ordered: scans before brief synthesis so brief has fresh data
    catchup_sequence = [
        ("morning_scan",    job_morning_scan),
        ("library_index",   job_library_index),
        ("inbox_process",   job_inbox_process),
        ("brief_synthesis", job_brief_synthesis),
    ]
    missed = []
    for catch_job_id, catch_func in catchup_sequence:
        cfg = {**JOB_DEFAULTS.get(catch_job_id, {}), **settings_cu.get(catch_job_id, {})}
        if not cfg.get("enabled", True):
            continue
        sched_h, sched_m = _parse_time(cfg.get("time", "07:00"))
        sched_today = now_local.replace(hour=sched_h, minute=sched_m,
                                        second=0, microsecond=0)
        if now_local > sched_today:
            missed.append((catch_job_id, catch_func))

    if missed:
        def _run_catchup(jobs):
            for jid, jfunc in jobs:
                log.info("[scheduler] catch-up: running %s", jid)
                try:
                    jfunc()
                except Exception as exc:
                    log.warning("[scheduler] catch-up %s failed: %s", jid, exc)
        _threading.Thread(target=_run_catchup, args=(missed,),
                          daemon=True, name="catchup-sequence").start()


def apply_settings_and_reschedule(new_settings: dict) -> None:
    """Persist new job settings and reschedule all jobs without restarting."""
    save_job_settings(new_settings)
    # Remove all current jobs and re-register with new settings
    for job_id in list(JOB_FUNCS.keys()):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
    setup_jobs()
