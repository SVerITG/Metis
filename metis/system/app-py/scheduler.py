"""
scheduler.py — APScheduler background jobs for the Metis dashboard.

Jobs registered here run automatically on their cron schedules when the
dashboard is running. They are the same operations as the manual scan
buttons — APScheduler just calls them without user interaction.

Default schedule (overridden by schedule.morning_brief_time in user-config.yaml):
  morning_scan   07:00 daily  — news feeds + literature folder
  library_index  07:30 daily  — library file inventory
  nightly_backup 23:00 daily  — copy metis.sqlite to backups/
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
    try:
        rc = os.environ.get("METIS_RC_ROOT", "")
        if not rc:
            return 7
        cfg_path = Path(rc) / "system" / "config" / "user-config.yaml"
        if cfg_path.exists():
            import yaml
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            t = cfg.get("schedule", {}).get("morning_brief_time", "07:00")
            return int(str(t).split(":")[0])
    except Exception:
        pass
    return 7


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
        from metis_mcp.tools.literature_monitor import _pubmed_esearch, _pubmed_esummary, _insert_article
        import sqlite3 as _sq, asyncio as _a
        from metis_mcp.config import paths as _p
        pmids = _pubmed_esearch(
            "trypanosomiasis[Title/Abstract] OR sleeping sickness[Title/Abstract] "
            "OR neglected tropical diseases[Title/Abstract] OR HAT[Title/Abstract]",
            reldate=1, max_results=15,
        )
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
        from metis_mcp.tools.literature_monitor import _openalex_search, _reconstruct_abstract, _insert_article
        import sqlite3 as _sq
        from metis_mcp.config import paths as _p
        import datetime as _dt
        from_date = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        items = _openalex_search(
            "trypanosomiasis OR sleeping sickness OR neglected tropical diseases",
            from_date=from_date, max_results=10,
        )
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
        from metis_mcp.tools.library import scan_library_folder
        r = scan_library_folder()
        msg = f"Indexed {r.get('files_indexed', '?')} files."
        _log_job("library_index", "ok", msg)
        log.info("[scheduler] library_index done: %s", msg)
    except Exception as exc:
        _log_job("library_index", "error", str(exc)[:300])
        log.error("[scheduler] library_index failed: %s", exc)


def job_nightly_backup() -> None:
    """Copy metis.sqlite to a dated backup (skips if today's backup exists)."""
    log.info("[scheduler] nightly_backup starting")
    try:
        rc = os.environ.get("METIS_RC_ROOT", "")
        if not rc:
            _log_job("nightly_backup", "skip", "METIS_RC_ROOT not set")
            return
        db_path = Path(rc) / "system" / "app" / "data" / "metis.sqlite"
        if not db_path.exists():
            _log_job("nightly_backup", "skip", "DB file not found")
            return
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        dst = backup_dir / f"metis.{datetime.date.today().strftime('%Y%m%d')}.sqlite"
        if dst.exists():
            _log_job("nightly_backup", "skip", f"Backup {dst.name} already exists")
            return
        shutil.copy2(str(db_path), str(dst))
        _log_job("nightly_backup", "ok", f"Backed up to backups/{dst.name}")
        log.info("[scheduler] nightly_backup: %s", dst.name)
    except Exception as exc:
        _log_job("nightly_backup", "error", str(exc)[:300])
        log.error("[scheduler] nightly_backup failed: %s", exc)


# Exported map so the jobs router can trigger them by name
JOB_FUNCS: dict[str, callable] = {
    "morning_scan":   job_morning_scan,
    "library_index":  job_library_index,
    "nightly_backup": job_nightly_backup,
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
    """Register all cron jobs. Call once before scheduler.start()."""
    hour = _morning_hour()
    scheduler.add_job(
        job_morning_scan,
        CronTrigger(hour=hour, minute=0),
        id="morning_scan",
        name="Morning scan",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_library_index,
        CronTrigger(hour=hour, minute=30),
        id="library_index",
        name="Library index",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_nightly_backup,
        CronTrigger(hour=23, minute=0),
        id="nightly_backup",
        name="Nightly DB backup",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    log.info(
        "[scheduler] jobs registered: morning_scan@%02d:00, library_index@%02d:30, nightly_backup@23:00",
        hour, hour,
    )
