"""
scheduler.py — APScheduler background jobs for the Metis dashboard.

Jobs registered here run automatically on their cron schedules when the
dashboard is running. They are the same operations as the manual scan
buttons — APScheduler just calls them without user interaction.

Default schedule (all overridable via user-config.yaml → jobs: section):
  morning_scan           09:00 daily — news feeds + PubMed + OpenAlex
  library_index          09:05 daily — library file inventory
  inbox_process          09:10 daily — process pending inbox items
  literature_discovery   Mon 09:15   — PubMed + OpenAlex paper discovery by topic
  brief_synthesis        09:20 daily — pre-generate AI morning brief (runs AFTER scans)
  dataset_monitor        09:30 daily — check data triggers, fire if conditions met
  board_refresh          Mon 09:35   — Events & Funding boards via web search
  evening_reflexion      09:40 daily — aggregate reflexions for self-improvement
  memory_consolidation   09:45 daily — distil recent agent runs into memory_entries
  weekly_summary         Mon 09:50   — generate weekly summary
  nightly_backup         09:55 daily — copy metis.sqlite to backups/
"""

import asyncio
import datetime
import inspect
import logging
import os
import shutil
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger("metis.scheduler")

# Run cron jobs in the USER'S timezone, not UTC.
#
# Job times in user-config.yaml ("09:00") are what the user means locally, and the
# catch-up logic below compares against datetime.now() (local). With timezone="UTC"
# the CronTrigger fired at 09:00 UTC = 11:00 Brussels in summer — so the "morning"
# brief arrived at 11:00 and the catch-up disagreed with the cron by two hours.
try:
    from tzlocal import get_localzone  # ships with APScheduler

    _LOCAL_TZ = get_localzone()
except Exception:  # pragma: no cover — fall back to APScheduler's own detection
    _LOCAL_TZ = None

scheduler = AsyncIOScheduler(timezone=_LOCAL_TZ) if _LOCAL_TZ else AsyncIOScheduler()

# In-memory last-run cache (keyed by job_id)
_last_results: dict[str, dict] = {}


def _ran_today(job_id: str) -> bool:
    """Has this job already completed today?

    The daily catch-up had NO such check (the weekly path did), so every restart
    after the scheduled time re-fired every daily job. With a 5-minute supervision
    heartbeat now restarting the dashboard, that means repeatedly re-running
    `memory_consolidation` (writing duplicate memory rows) and `brief_synthesis`
    (a BILLABLE Claude API call). Observed 2026-07-14: 7-8 runs of every daily job
    in a single morning.

    'skip' counts as done — the job ran and decided there was nothing to do.
    'error' does NOT count, so a genuinely failed job is still retried.
    """
    try:
        from db import db_query

        rows = db_query(
            "SELECT 1 FROM jobs_log "
            "WHERE job_type = ? AND status IN ('ok', 'skip') "
            "AND date(created_at) = date('now', 'localtime') LIMIT 1",
            (job_id,),
        )
        return bool(rows)
    except Exception as exc:
        # Fail SAFE: if we cannot tell, assume it ran. Re-running costs money and
        # corrupts memory; skipping one day of a job costs nothing that matters.
        log.warning("[scheduler] could not check if '%s' ran today: %s", job_id, exc)
        return True


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
    """Read preferred morning scan hour from user-config.yaml, default 9."""
    cfg = _load_job_settings()
    try:
        t = cfg.get("morning_scan", {}).get("time", "09:00")
        return int(str(t).split(":")[0])
    except Exception:
        pass
    return 9


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
    """Parse 'HH:MM' → (hour, minute). Returns (9, 0) on failure."""
    try:
        parts = str(time_str).split(":")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return 9, 0


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


def job_library_scan() -> None:
    """Daily: scan every LIBRARY source and put the results in new_publications.

    WHY THIS JOB EXISTS
        `scan_library_feeds()` — the function that reads the journal and preprint
        table-of-contents feeds — had NO SCHEDULED CALLER anywhere in the repo.
        `job_morning_scan` calls `scan_news_feeds` and `scan_literature_folder`,
        and reports the latter as "Lit: N items", which reads like the literature
        feeds ran when in fact it counted new PDFs in a local folder. So the
        surface said "Lit: 0" every morning and looked like a quiet week in the
        journals, while 21 healthy feeds were simply never being read. The last
        rows in new_publications came from a hand-run scan.

        That is the mirror image of the write-path-with-no-reader bug already
        recorded in this codebase: a reader with no caller. Both are invisible by
        eye, because the surface still renders and still shows old data.

    WHAT "SEARCHED UPON UPDATE" MEANS HERE
        the researcher asked that all sources be searched on update, so this job covers all
        three routes literature can arrive by, and reports them separately:
          1. Journal + preprint feeds  → new_publications  (breadth, no query)
          2. Zotero                    → literature_metadata (his own catalogue)
          3. PubMed + OpenAlex         → new_publications  (targeted by topic)

        Zotero belongs in this job rather than on a button: it had gone THREE
        MONTHS without a sync (last 2026-05-21) because a manual button is only
        pressed by someone who already suspects it is stale.

    Each route is independently guarded. A publisher 403 must not stop the Zotero
    sync, and a missing Zotero key must not stop the feeds.
    """
    log.info("[scheduler] library_scan starting")
    parts: list[str] = []

    # ── 1. Journal + preprint feeds ─────────────────────────────────────────
    try:
        from metis_mcp.tools.content_scan import scan_library_feeds
        r = scan_library_feeds(max_per_feed=12)
        papers = r.get("papers_added", 0)
        errs = r.get("errors") or []
        parts.append(f"Feeds: {papers} papers")
        if errs:
            # Surfaced, not swallowed: a feed that starts 403ing must become
            # visible the day it happens, not at the next manual audit.
            parts.append(f"{len(errs)} feed error(s)")
            for e in errs[:6]:
                log.warning("[scheduler] library feed: %s", e)
    except Exception as exc:
        log.warning("[scheduler] library feed scan failed: %s", exc)
        parts.append("Feeds: error")

    # ── 2. Zotero ───────────────────────────────────────────────────────────
    try:
        n, route = _sync_zotero_incremental()
        # The ROUTE is reported, not just the count. "Zotero: 506 (local)" tells
        # you write-back is unavailable; a bare "506" hides that entirely.
        parts.append(f"Zotero: {n} ({route})" if n >= 0
                     else f"Zotero: unavailable — {route}")
    except Exception as exc:
        log.warning("[scheduler] zotero sync failed: %s", exc)
        parts.append(f"Zotero: error — {str(exc)[:80]}")

    # ── 3. Targeted topic search ────────────────────────────────────────────
    try:
        found = _topic_literature_search(days=2, per_topic=10)
        parts.append(f"Topics: {found} papers")
    except Exception as exc:
        log.warning("[scheduler] topic literature search failed: %s", exc)
        parts.append("Topics: error")

    msg = " · ".join(parts)
    _log_job("library_scan", "ok", msg)
    log.info("[scheduler] library_scan done: %s", msg)


def _sync_zotero_incremental() -> tuple[int, str]:
    """Pull Zotero into literature_metadata. Returns (items_touched, route).

    TWO ROUTES, and which one is available is not a detail:

      · LOCAL — read `zotero.sqlite` directly. No credentials, works offline,
        and it is the route that actually imported the existing 506 items.
      · WEB   — the Zotero API. Needed for WRITING back to Zotero; nothing can
        push an item without it.

    Measured 2026-08-21: `ZOTERO_API_KEY` and `ZOTERO_USER_ID` in this install
    were still the literal placeholders from .env.example, so every web call
    returned 403 and the error was swallowed several frames up. The surface then
    reported "last synced 21 May" as though a schedule had lapsed, when in fact
    the web sync had never once run.

    So: prefer local, because it works with no setup, and report the route used
    so a stale library can never again look like a scheduling problem.
    """
    import sqlite3 as _sq
    from metis_mcp.config import paths as _p
    from metis_mcp.tools.zotero import (
        zotero_credential_state, sync_zotero_into_db,
    )

    state = zotero_credential_state()

    # Web first when genuinely configured — it is the only route that sees group
    # libraries and remote edits made from another machine.
    if state["web"]:
        con = _sq.connect(str(_p.db))
        try:
            return sync_zotero_into_db(con, full=False), "web"
        except Exception as exc:
            log.warning("[scheduler] Zotero web sync failed (%s); trying local", exc)
        finally:
            con.close()

    if state["local"]:
        from metis_mcp.tools.zotero import _read_local_zotero, _upsert_lit_row
        con = _sq.connect(str(_p.db))
        con.row_factory = _sq.Row
        try:
            rows = _read_local_zotero(state["local"])
            for row in rows:
                _upsert_lit_row(con, row)
            con.commit()
            return len(rows), "local"
        finally:
            con.close()

    return -1, state["reason"] or "no Zotero found"


def _topic_literature_search(days: int = 7, per_topic: int = 15) -> int:
    """PubMed + OpenAlex, one query per active topic, into new_publications.

    Extracted from job_literature_discovery so the daily library scan and the
    weekly deep sweep share one implementation. They differ only in window and
    depth — duplicating the insert logic is how the two drift apart.
    """
    import sqlite3 as _sq
    from metis_mcp.config import paths as _p

    topics: list[str] = []
    try:
        con = _sq.connect(str(_p.db))
        con.row_factory = _sq.Row
        topics = [r["topic"] for r in
                  con.execute("SELECT topic FROM user_topics WHERE active = 1")
                  if r["topic"]]
        con.close()
    except Exception:
        pass
    if not topics:
        return 0

    from metis_mcp.tools.content_scan import classify_publication
    from_date = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    added = 0

    con = _sq.connect(str(_p.db))
    try:
        for topic in topics[:12]:
            try:
                from metis_mcp.tools.literature_monitor import (
                    _pubmed_esearch, _pubmed_esummary,
                )
                pmids = _pubmed_esearch(f"{topic}[Title/Abstract]",
                                        reldate=days, max_results=per_topic)
                for item in (_pubmed_esummary(pmids) if pmids else []):
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{item['pmid']}/"
                    if con.execute("SELECT 1 FROM new_publications WHERE source_url=? LIMIT 1",
                                   (url,)).fetchone():
                        continue
                    kind, lane = classify_publication(
                        item.get("title", ""), "", item.get("source", ""),
                        topic, url, 1.0,   # a topic hit is by definition his field
                    )
                    con.execute(
                        "INSERT INTO new_publications (title, journal, pub_date, doi, "
                        "topic_tag, source_url, discovered_at, authors, abstract, "
                        "feed_name, entry_kind, lane, relevance) "
                        "VALUES (?,?,?,'',?,?,?,?,?,?,?,?,?)",
                        (item.get("title", "")[:500], item.get("source", ""),
                         item.get("pubdate", ""), topic[:60], url, now,
                         item.get("authors", "")[:400], "", "PubMed",
                         kind, lane, 0.9),
                    )
                    added += 1
            except Exception as exc:
                log.warning("[scheduler] PubMed '%s': %s", topic, exc)

            try:
                from metis_mcp.tools.literature_monitor import (
                    _openalex_search, _reconstruct_abstract,
                )
                for item in (_openalex_search(topic, from_date=from_date,
                                              max_results=per_topic) or []):
                    doi = item.get("doi") or ""
                    src = doi or item.get("id") or ""
                    if not src:
                        continue
                    if con.execute(
                        "SELECT 1 FROM new_publications WHERE source_url=? "
                        "OR (doi != '' AND doi = ?) LIMIT 1", (src, doi)
                    ).fetchone():
                        continue
                    journal = ((item.get("primary_location") or {})
                               .get("source") or {}).get("display_name", "")
                    authors = "; ".join(
                        (a.get("author") or {}).get("display_name", "")
                        for a in (item.get("authorships") or [])[:8]
                    )
                    # OpenAlex stores abstracts as an inverted index; reconstructing
                    # it is the only way to show one without a second API call.
                    abstract = _reconstruct_abstract(
                        item.get("abstract_inverted_index")) or ""
                    title = item.get("title") or "Untitled"
                    kind, lane = classify_publication(
                        title, abstract, journal, topic, src, 1.0,
                    )
                    con.execute(
                        "INSERT INTO new_publications (title, journal, pub_date, doi, "
                        "topic_tag, source_url, discovered_at, authors, abstract, "
                        "feed_name, entry_kind, lane, relevance) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (title[:500], journal, item.get("publication_date", ""), doi,
                         topic[:60], src, now, authors[:400], abstract[:4000],
                         "OpenAlex", kind, lane, 0.9),
                    )
                    added += 1
            except Exception as exc:
                log.warning("[scheduler] OpenAlex '%s': %s", topic, exc)
        con.commit()
    finally:
        con.close()
    return added


def job_download_pickup() -> None:
    """File the PDFs the researcher downloaded through his browser.

    The other half of acquisition. Metis fetches what is legally open; anything
    behind ITM's OpenAthens login has to be opened in a browser, because a
    federated SSO session cannot be held by a background process. This closes the
    loop on that: he clicks, the browser downloads, and this puts the file where
    it belongs and marks the paper obtained.

    Runs often (hourly) rather than daily — the value is that a paper is filed
    while he still remembers downloading it.
    """
    import sqlite3 as _sq
    from metis_mcp.config import paths as _p

    try:
        from services.download_pickup import scan_downloads
    except ImportError as exc:
        _log_job("download_pickup", "skip", f"unavailable: {exc}")
        return

    con = _sq.connect(str(_p.db))
    try:
        r = scan_downloads(con)
    except Exception as exc:
        log.warning("[scheduler] download_pickup failed: %s", exc)
        _log_job("download_pickup", "error", str(exc)[:200])
        return
    finally:
        con.close()

    if r.get("error"):
        _log_job("download_pickup", "skip", r["error"])
        return

    msg = (f"Filed {r['filed']}, unmatched {r['unmatched']}, "
           f"skipped {r['skipped']} — {r.get('folder', '?')}")
    _log_job("download_pickup", "ok", msg)
    log.info("[scheduler] download_pickup: %s", msg)


def job_library_index() -> None:
    """Library file inventory scan."""
    log.info("[scheduler] library_index starting")
    try:
        from metis_mcp.tools.content_scan import scan_literature_folder
        r = scan_literature_folder()
        msg = f"Indexed {r.get('papers_added', 0)} papers."
        _log_job("library_index", "ok", msg)
        log.info("[scheduler] library_index done: %s", msg)
    except Exception as exc:
        _log_job("library_index", "error", str(exc)[:300])
        log.error("[scheduler] library_index failed: %s", exc)


def job_background_index() -> None:
    """Index papers added to a knowledge background since its last build.

    Closes the other half of Keystone M6. Adding a PDF to a background folder used
    to do nothing at all: no rebuild was scheduled, nothing detected the new file,
    and no screen said the layer had fallen behind — so a layer last built in June
    was indistinguishable from one built this morning, and a paper the researcher
    had clearly decided to keep stayed unsearchable indefinitely.

    Only ENABLED layers are indexed, and only layers with pending files, so this
    normally costs one cheap directory walk per layer and exits.
    """
    log.info("[scheduler] background_index starting")
    try:
        from metis_mcp.tools.knowledge_db import (
            pending_pdf_count, build_pdf_knowledge_db,
        )
        import asyncio as _asyncio
        from db import db_query

        layers = db_query(
            "SELECT slug FROM knowledge_databases WHERE COALESCE(enabled,1)=1"
        ) or []
        done, total = [], 0
        for row in layers:
            slug = row["slug"]
            pending = pending_pdf_count(slug)
            if not pending:
                continue
            _asyncio.run(build_pdf_knowledge_db(database=slug))
            done.append(f"{slug} (+{pending})")
            total += pending
        msg = ("Indexed " + ", ".join(done)) if done else "All backgrounds up to date."
        _log_job("background_index", "ok", msg)
        log.info("[scheduler] background_index done: %s", msg)
    except Exception as exc:
        _log_job("background_index", "error", str(exc)[:300])
        log.error("[scheduler] background_index failed: %s", exc)


def job_office_sync() -> None:
    """Re-read Office documents that changed on disk since Metis last saw them.

    This is the half of the round trip that makes the integration bidirectional.
    Metis could write a deck and, since P5.2, read one back — but only when asked.
    A deck edited in PowerPoint stayed stale in Metis until someone remembered to
    re-ingest it, which is the same convention-not-construction gap that left
    session memory empty for months.

    Compares each ingested document's stored file_mtime against the file on disk.
    Missing files are recorded rather than deleted: the row is the provenance, and
    a file that is merely on an unmounted drive must not erase its own history.
    """
    log.info("[scheduler] office_sync starting")
    try:
        import asyncio as _asyncio
        from pathlib import Path as _Path
        from db import db_query, db_execute
        from metis_mcp.tools.office import ingest_office_document

        rows = db_query("SELECT path, file_mtime FROM office_documents WHERE kind='pptx'") or []
        updated, missing = [], 0
        for r in rows:
            f = _Path(r["path"])
            if not f.is_file():
                missing += 1
                continue
            import datetime as _dt
            disk = _dt.datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")
            if disk != (r["file_mtime"] or ""):
                _asyncio.run(ingest_office_document(str(f)))
                updated.append(f.name)
        msg = ("Re-read " + ", ".join(updated[:5]) + (f" (+{len(updated)-5} more)" if len(updated) > 5 else "")) \
            if updated else f"All {len(rows)} document(s) current."
        if missing:
            msg += f" {missing} file(s) not found on disk."
        _log_job("office_sync", "ok", msg)
        log.info("[scheduler] office_sync done: %s", msg)
    except Exception as exc:
        _log_job("office_sync", "error", str(exc)[:300])
        log.error("[scheduler] office_sync failed: %s", exc)


def job_nightly_backup() -> None:
    """Safe online backup of metis.sqlite using the SQLite backup API (WAL-safe)."""
    log.info("[scheduler] nightly_backup starting")
    try:
        import sqlite3 as _sq3
        rc = os.environ.get("METIS_RC_ROOT", "")
        # Source = the LIVE database (now on local disk, off OneDrive — see db.py).
        try:
            from db import get_db_path
            db_path = get_db_path()
        except Exception:
            db_path = Path(rc) / "system" / "app" / "data" / "metis.sqlite" if rc else None
        if not db_path or not db_path.exists():
            _log_job("nightly_backup", "skip", "DB file not found")
            return
        # Destination = OneDrive (system/app/data/backups), so backups sync
        # off-machine even though the live DB lives on local disk.
        backup_dir = (
            Path(rc) / "system" / "app" / "data" / "backups"
            if rc
            else db_path.parent / "backups"
        )
        backup_dir.mkdir(parents=True, exist_ok=True)
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
        # PowerShell escapes a single quote by doubling it. Without this an
        # apostrophe ends the string early: "the researcher's meeting" produced no toast at
        # all, and any text reaching here became executable PowerShell.
        title = str(title).replace("'", "''")
        message = str(message).replace("'", "''")
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


def _db_exec(sql: str, args: tuple = ()) -> None:
    """Use the app's own db helpers, as every other job here does, so the
    reminder path shares connection handling rather than opening its own."""
    try:
        from db import db_execute
        db_execute(sql, args)
    except Exception as exc:
        log.debug("[reminders] write failed: %s", exc)


def _db_scalar(sql: str, args: tuple = ()):
    try:
        from db import db_scalar
        return db_scalar(sql, args, default=None)
    except Exception:
        return None


def job_nature_briefings() -> None:
    """Pull new Nature Briefing editions from the public campaign archive.

    Scheduled because the alternative is the pattern this project keeps hitting:
    working code with no path to it. `empty_state.html` was used once in months,
    `ui_seen` by one surface, `tasks.due_date` on 1 of 71 rows — every one of
    them correct and unreached. A scanner nobody calls is the same failure.

    07:40 local: after Nature's overnight send (the archive lags the email by
    minutes, not hours) and before the morning brief at 08:00, so today's
    briefing is already in place when the brief is composed.
    """
    if _ran_today("nature_briefings"):
        _log_job("nature_briefings", "skip", "already ran today")
        return
    try:
        from metis_mcp.tools import briefings as B
        r = B.scan()
        msg = (f"{r['added']} new edition(s): "
               + ", ".join(f"{k} x{n}" for k, n in r["by_kind"].items()))             if r["added"] else "nothing new"
        _log_job("nature_briefings", "ok", msg)
        log.info("[scheduler] nature briefings — %s", msg)
    except Exception as exc:
        _log_job("nature_briefings", "error", f"{type(exc).__name__}: {exc}")
        log.warning("[scheduler] nature briefings failed: %s", exc)


def job_reminder_due() -> None:
    """Fire Windows toasts for reminders whose time has come.

    Until this existed, `remind_at` was stored and read by nothing: a reminder
    set for 14:30 was only ever seen if the calendar happened to be open at 14:30,
    which is the one moment you are least likely to be looking at it.

    Occurrences come from the calendar's own `_plans_between`, not a second copy
    of the recurrence maths — a notifier that disagrees with the calendar about
    which days a repeat falls on is worse than no notifier.

    Scope is deliberately TODAY only. Firing a week of missed reminders at once
    because the dashboard was off is noise, not a service.
    """
    import datetime as _d
    try:
        from routers.calendar_plan import _plans_between
    except Exception as exc:
        log.warning("[reminders] calendar unavailable: %s", exc)
        return

    today = _d.date.today()
    now = _d.datetime.now()
    try:
        plans = _plans_between(today, today).get(today.isoformat(), [])
    except Exception as exc:
        log.warning("[reminders] could not read the plan: %s", exc)
        return

    _db_exec(
        "CREATE TABLE IF NOT EXISTS day_plan_occurrence ("
        "plan_id INTEGER NOT NULL, occurred_on TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT '', moved_to TEXT, notified_at TEXT, "
        "updated_at TEXT NOT NULL DEFAULT (datetime('now')), "
        "PRIMARY KEY (plan_id, occurred_on))")

    sent = 0
    for pl in plans:
        if (pl.get("kind") or "") != "reminder" or pl.get("done"):
            continue
        if not pl.get("_is_start", True):
            continue  # a continuation day of a span is not a fresh reminder

        # Its identity is the RULE date for a repeat, the start date otherwise.
        occ = pl.get("_occ") or str(pl.get("start_date") or today.isoformat())

        at = (pl.get("remind_at") or "").strip()
        if at:
            try:
                hh, mm = (int(x) for x in at.split(":")[:2])
                if now < _d.datetime.combine(today, _d.time(hh, mm)):
                    continue  # not yet
            except (ValueError, TypeError):
                pass  # an unreadable time should still notify, not vanish

        pid = pl.get("plan_id")
        already = _db_scalar(
            "SELECT notified_at FROM day_plan_occurrence "
            "WHERE plan_id=? AND occurred_on=?", (pid, occ))
        if already:
            continue

        _notify_windows("Metis reminder", str(pl.get("text") or "")[:180])
        _db_exec(
            "INSERT INTO day_plan_occurrence (plan_id, occurred_on, notified_at, updated_at) "
            "VALUES (?,?,datetime('now'),datetime('now')) "
            "ON CONFLICT(plan_id, occurred_on) DO UPDATE SET "
            "notified_at=datetime('now'), updated_at=datetime('now')",
            (pid, occ))
        sent += 1

    if sent:
        log.info("[reminders] %d reminder(s) notified", sent)
        _log_job("reminder_due", "ok", f"{sent} notified")


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

        # The table and its column names are owned by inbox_watcher — the module
        # that watches this same folder. This job used to spell them differently
        # (source_path / type / logged_at) and never create the table, so it
        # reported "0 new items — ok" forever while writing nothing at all.
        # Borrow the owner's schema rather than restating it.
        import sqlite3 as _sqlite3
        from db import get_db_path
        from inbox_watcher import ensure_inbox_table
        with _sqlite3.connect(str(get_db_path())) as _con:
            ensure_inbox_table(_con)

        # Load already-logged paths to avoid double-processing
        logged_paths = set()
        try:
            rows = db_query("SELECT filepath FROM inbox_items")
            logged_paths = {r.get("filepath") for r in rows}
        except Exception:
            pass

        processed = 0
        failed = 0
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
                    "INSERT OR IGNORE INTO inbox_items "
                    "(filename, filepath, file_type, status, created_at) "
                    "VALUES (?, ?, ?, 'new', ?)",
                    (f.name, str(f), ftype, now_iso),
                )
                processed += 1
            except Exception as exc:
                # Count and report write failures. Swallowing them is what let a
                # wrong-column INSERT report success indefinitely.
                failed += 1
                if failed == 1:
                    log.warning("[scheduler] inbox_process write failed for %s: %s",
                                f.name, exc)

        if failed:
            _log_job("inbox_process", "error",
                     f"Logged {processed} item(s); {failed} write(s) FAILED.")
            log.error("[scheduler] inbox_process: %d logged, %d failed",
                      processed, failed)
        else:
            _log_job("inbox_process", "ok", f"Processed {processed} new inbox item(s).")
            log.info("[scheduler] inbox_process: %d new items", processed)
    except Exception as exc:
        _log_job("inbox_process", "error", str(exc)[:300])
        log.error("[scheduler] inbox_process failed: %s", exc)


def job_evening_reflexion() -> None:
    """Aggregate today's reflexions into themes for the self-improvement loop."""
    log.info("[scheduler] evening_reflexion starting")
    try:
        # aggregate_reflexions() is SYNCHRONOUS and returns a dict — it must NOT be
        # wrapped in asyncio.run() (that raises "a coroutine was expected").
        from metis_mcp.tools.improvement import aggregate_reflexions, consolidate_reflexions
        result = aggregate_reflexions()
        agents = result.get("agents", []) if isinstance(result, dict) else []
        total = (result.get("totals", {}) or {}).get("reflexions", 0) if isinstance(result, dict) else 0
        # Close the loop: distil recurring themes into semantic memory + prune working memory.
        cons = consolidate_reflexions()
        # Schedule the drafting step (Keystone P3.3): when themes accumulate, auto-create a
        # DRAFT proposal for one-click human review — previously this never ran, so themes
        # reached semantic memory but never became an actionable proposal. Guarded so we
        # don't pile up duplicate drafts for an agent that already has one open.
        drafted = 0
        try:
            from metis_mcp.tools.improvement import draft_self_improvement_proposal
            import sqlite3 as _sq
            from metis_mcp.config import paths as _paths
            _con = _sq.connect(str(_paths.db))
            try:
                open_slugs = {r[0] for r in _con.execute(
                    "SELECT DISTINCT agent_slug FROM skill_improvement_proposals "
                    "WHERE status IN ('draft', 'pending')"
                ).fetchall()}
            except Exception:
                open_slugs = set()
            _con.close()
            for _a in (agents or [])[:8]:
                slug = (_a.get("agent_slug") or _a.get("slug") or _a.get("agent")
                        or _a.get("name")) if isinstance(_a, dict) else None
                if not slug or slug in open_slugs:
                    continue
                res = draft_self_improvement_proposal(slug)
                if isinstance(res, dict) and res.get("status") not in ("empty", None, "error"):
                    drafted += 1
        except Exception as _exc:
            log.warning("[scheduler] proposal drafting skipped: %s", _exc)
        msg = (f"Aggregated {total} reflexion(s) across {len(agents)} agent(s); "
               f"consolidated {cons['semantic_written']} new semantic node(s), "
               f"pruned {cons['working_memory_pruned']} stale working-memory row(s); "
               f"drafted {drafted} improvement proposal(s).")
        _log_job("evening_reflexion", "ok", msg)
        log.info("[scheduler] evening_reflexion done: %s", msg)
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


# ---------------------------------------------------------------------------
# Dataset monitor — check data triggers
# ---------------------------------------------------------------------------

async def job_dataset_monitor() -> None:
    """Poll file-based data triggers and fire any that match."""
    _log_job("dataset_monitor", "running", "Checking data triggers…")
    try:
        # Import the trigger engine from the MCP tools
        import sys
        mcp_src = str(Path(__file__).resolve().parent.parent / "mcp-server" / "src")
        if mcp_src not in sys.path:
            sys.path.insert(0, mcp_src)

        from metis_mcp.tools.data_automation import check_file_triggers, _execute_trigger, _connect, _ensure_tables

        fired_ids = check_file_triggers()
        if not fired_ids:
            _log_job("dataset_monitor", "ok", "No triggers fired")
            return

        # Execute each fired trigger
        results = []
        with _connect() as conn:
            _ensure_tables(conn)
            for tid in fired_ids:
                row = conn.execute(
                    "SELECT * FROM data_triggers WHERE trigger_id = ?", (tid,)
                ).fetchone()
                if row:
                    msg = await _execute_trigger(dict(row))
                    results.append(msg)

        _log_job("dataset_monitor", "ok", f"{len(fired_ids)} triggers fired: {'; '.join(results)}")
    except ImportError:
        _log_job("dataset_monitor", "ok", "Data automation tools not installed — skipping")
    except Exception as exc:
        _log_job("dataset_monitor", "error", str(exc)[:300])
        log.error("[scheduler] dataset_monitor failed: %s", exc)


# Exported map so the jobs router can trigger them by name
def job_board_refresh() -> None:
    """Monthly: refresh the Events & Funding boards via Claude web search.

    These two boards have no RSS source (congresses/funders publish on web pages,
    not feeds), so once a month we ask Claude to web-search for current items. The
    dashboard's per-box Refresh buttons run the same search on demand.
    """
    log.info("[scheduler] board_refresh starting")
    try:
        from routers.today import _refresh_board_via_search
        parts = []
        for b in ("events", "funding"):
            n, err = _refresh_board_via_search(b)
            parts.append(f"{b}:{n}" + (f"({err})" if err else ""))
        msg = " ".join(parts)
        log.info("[scheduler] board_refresh done: %s", msg)
        _log_job("board_refresh", "ok", msg)
    except Exception as e:
        log.warning("[scheduler] board_refresh failed: %s", e)
        _log_job("board_refresh", "error", str(e)[:200])


def job_literature_discovery() -> None:
    """Weekly: search PubMed + OpenAlex for new papers matching user topics.

    Inserts into new_publications (not news_briefs) so they appear in the
    Today surface's literature discovery widget with add/dismiss actions.
    """
    log.info("[scheduler] literature_discovery starting")
    import sqlite3 as _sq
    from metis_mcp.config import paths as _p

    # Load active topics from user_topics
    topics: list[str] = []
    try:
        con = _sq.connect(str(_p.db))
        con.row_factory = _sq.Row
        rows = con.execute(
            "SELECT topic FROM user_topics WHERE active = 1"
        ).fetchall()
        topics = [r["topic"] for r in rows if r["topic"]]
        con.close()
    except Exception:
        pass

    # Fall back to user-config.yaml research.topics
    if not topics:
        try:
            import yaml
            rc = os.environ.get("METIS_RC_ROOT", "")
            if rc:
                cfg_path = Path(rc) / "system" / "config" / "user-config.yaml"
                if cfg_path.exists():
                    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                    topics = cfg.get("research", {}).get("topics", [])
        except Exception:
            pass

    if not topics:
        _log_job("literature_discovery", "ok", "No topics configured — skipping")
        return

    total_found = 0
    total_new = 0
    from_date = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    now = datetime.datetime.now().isoformat(timespec="seconds")

    try:
        con = _sq.connect(str(_p.db))
        con.row_factory = _sq.Row
        # Ensure table exists
        con.execute(
            "CREATE TABLE IF NOT EXISTS new_publications ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, journal TEXT DEFAULT '', "
            "pub_date TEXT DEFAULT '', doi TEXT DEFAULT '', "
            "topic_tag TEXT DEFAULT '', relevance_note TEXT DEFAULT '', "
            "source_url TEXT DEFAULT '', read_at TEXT DEFAULT '', "
            "discovered_at TEXT NOT NULL)"
        )

        for topic in topics[:6]:
            # PubMed search
            try:
                from metis_mcp.tools.literature_monitor import (
                    _pubmed_esearch, _pubmed_esummary,
                )
                query = f"{topic}[Title/Abstract]"
                pmids = _pubmed_esearch(query, reldate=7, max_results=20)
                summaries = _pubmed_esummary(pmids) if pmids else []
                for item in summaries:
                    total_found += 1
                    pmid = item["pmid"]
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    # Dedup by source_url
                    exists = con.execute(
                        "SELECT id FROM new_publications WHERE source_url = ? LIMIT 1",
                        (url,),
                    ).fetchone()
                    if exists:
                        continue
                    con.execute(
                        "INSERT INTO new_publications "
                        "(title, journal, pub_date, doi, topic_tag, source_url, discovered_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            item.get("title", "")[:500],
                            item.get("source", ""),
                            item.get("pubdate", ""),
                            "",  # PubMed doesn't always return DOI in esummary
                            topic[:60],
                            url,
                            now,
                        ),
                    )
                    total_new += 1
            except Exception as exc:
                log.warning("[scheduler] lit_discovery PubMed '%s': %s", topic, exc)

            # OpenAlex search
            try:
                from metis_mcp.tools.literature_monitor import _openalex_search
                items = _openalex_search(topic, from_date=from_date, max_results=15)
                for item in (items or []):
                    total_found += 1
                    doi = item.get("doi") or ""
                    source_url = doi or item.get("id") or ""
                    if not source_url:
                        continue
                    exists = con.execute(
                        "SELECT id FROM new_publications "
                        "WHERE source_url = ? OR (doi != '' AND doi = ?) LIMIT 1",
                        (source_url, doi),
                    ).fetchone()
                    if exists:
                        continue
                    title = item.get("title") or "Untitled"
                    pub_date = item.get("publication_date", "")
                    journal = (
                        (item.get("primary_location") or {})
                        .get("source", {})
                        .get("display_name", "")
                    )
                    con.execute(
                        "INSERT INTO new_publications "
                        "(title, journal, pub_date, doi, topic_tag, source_url, discovered_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (title[:500], journal, pub_date, doi, topic[:60], source_url, now),
                    )
                    total_new += 1
            except Exception as exc:
                log.warning("[scheduler] lit_discovery OpenAlex '%s': %s", topic, exc)

        con.commit()
        con.close()
    except Exception as exc:
        log.error("[scheduler] literature_discovery DB error: %s", exc)
        _log_job("literature_discovery", "error", str(exc)[:300])
        return

    msg = f"Found {total_found}, added {total_new} new papers across {len(topics)} topics"
    _log_job("literature_discovery", "ok", msg)
    log.info("[scheduler] literature_discovery done: %s", msg)


def job_embedding_backfill() -> None:
    """Embed any memory row that has no vector — keeps cross-pollination honest.

    episodic_memory has many writers (session events, agent runs, auto-capture,
    meeting import); only `remember()` embeds on write. So the semantic index
    silently rotted to 1.8% coverage (33 of 1,858 rows) and cross-pollination —
    the feature Metis is *for* — quietly degraded to a keyword LIKE.

    Reconciling on a schedule is the fix that survives a new writer being added:
    we never have to remember to embed at the call site.
    """
    import subprocess

    root = os.environ.get("METIS_RC_ROOT")
    if not root:
        _log_job("embedding_backfill", "skip", "METIS_RC_ROOT not set")
        return
    script = Path(root) / "tools" / "backfill-embeddings.py"
    if not script.exists():
        _log_job("embedding_backfill", "skip", "backfill-embeddings.py not found")
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=1800,
        )
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        summary = tail[-1] if tail else "no output"
        if proc.returncode == 0:
            _log_job("embedding_backfill", "ok", summary[:300])
        else:
            _log_job("embedding_backfill", "error", summary[:300])
    except Exception as exc:
        _log_job("embedding_backfill", "error", str(exc)[:300])


def job_db_sync() -> None:
    """Converge this machine's memory with the other computer's.

    The live DB stays on the native filesystem forever — OneDrive corrupted it in
    June by syncing the .sqlite/-wal/-shm trio mid-write. But a FINISHED, static
    snapshot has no writer and no WAL, so it is safe to put on OneDrive. This job
    exports one, and merges the snapshots the other machine left behind.

    Append-only union, deduped by content fingerprint (ids collide across
    machines), so it is idempotent. Mutable state (tasks/projects) is deliberately
    not merged. See tools/metis-sync-db.py for the full reasoning.
    """
    import subprocess

    root = os.environ.get("METIS_RC_ROOT")
    if not root:
        _log_job("db_sync", "skip", "METIS_RC_ROOT not set")
        return
    script = Path(root) / "tools" / "metis-sync-db.py"
    if not script.exists():
        _log_job("db_sync", "skip", "metis-sync-db.py not found")
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=1800,
        )
        out = (proc.stdout or "").strip().splitlines()
        merged = next((ln.strip() for ln in reversed(out) if "merged" in ln), "no changes")
        _log_job("db_sync", "ok" if proc.returncode == 0 else "error", merged[:300])
    except Exception as exc:
        _log_job("db_sync", "error", str(exc)[:300])


def job_promise_harness() -> None:
    """Run the promise harness weekly and record the score to promise-trend.jsonl, so
    "have we lost what we built?" becomes a live drift indicator instead of a manual
    investigation (Keystone 3.8). Counts the harness's PASS/FAIL/WARN markers."""
    import subprocess
    import json as _json
    import datetime as _dt
    root = os.environ.get("METIS_RC_ROOT")
    if not root:
        _log_job("promise_harness", "skip", "METIS_RC_ROOT not set"); return
    script = Path(root) / "tests" / "functional" / "run_metis_promises.sh"
    if not script.exists():
        _log_job("promise_harness", "skip", "harness not found"); return
    try:
        out = subprocess.run(["bash", str(script)], capture_output=True, text=True,
                             cwd=root, timeout=300).stdout
        p, f, w = out.count("✅ PASS"), out.count("🔴 FAIL"), out.count("🟡 WARN")
        trend = Path(root) / "system" / "config" / "promise-trend.jsonl"
        with open(trend, "a", encoding="utf-8") as fh:
            fh.write(_json.dumps({"ts": _dt.datetime.now().isoformat(timespec="seconds"),
                                  "pass": p, "fail": f, "warn": w}) + "\n")
        _log_job("promise_harness", "ok", f"{p} pass / {f} fail / {w} warn")
    except Exception as exc:
        _log_job("promise_harness", "error", str(exc)[:200])


def job_citation_backfill() -> None:
    """Resolve the DOI backlog in the citation ledger — Tier B, while the researcher sleeps.

    The per-turn hook and the artifact gate both record DOIs as `doi_unchecked`
    rather than resolving them inline: Tier B costs a network round trip, and a
    check that makes a reply feel slow is a check that gets switched off. So the
    backlog accumulates and this job works it overnight.

    This is also the only place a RETRACTION is ever noticed. Citing a retracted
    paper looks perfectly sourced, so nothing about the citation itself would ever
    prompt a re-check — it has to be swept for.
    """
    log.info("[scheduler] citation_backfill starting")
    try:
        from db import db_query, db_execute, get_db_path
        import datetime as _dt
        import sqlite3 as _sq
        from metis_mcp.tools.verification import check_doi, ensure_ledger

        with _sq.connect(str(get_db_path())) as _con:
            ensure_ledger(_con)

        rows = db_query(
            "SELECT id, doi FROM citation_checks "
            "WHERE verdict = 'doi_unchecked' AND COALESCE(doi,'') <> '' "
            "ORDER BY id LIMIT 60"
        ) or []
        if not rows:
            _log_job("citation_backfill", "skip", "no unresolved DOIs in the ledger")
            log.info("[scheduler] citation_backfill: nothing to resolve")
            return

        # De-duplicate: the same DOI cited in six lessons is one lookup, not six.
        by_doi: dict[str, list[int]] = {}
        for r in rows:
            by_doi.setdefault((r["doi"] or "").strip().lower(), []).append(r["id"])

        resolved = retracted = unresolved = 0
        for doi, ids in by_doi.items():
            try:
                res = check_doi(doi)
            except Exception as exc:
                log.warning("[scheduler] citation_backfill %s failed: %s", doi, exc)
                continue
            if res["verdict"] == "doi_retracted":
                retracted += 1
            elif res["verdict"] == "doi_resolved":
                resolved += 1
            else:
                unresolved += 1
            for rid in ids:
                db_execute(
                    "UPDATE citation_checks SET verdict=?, detail=?, tier='B', "
                    "checked_at=? WHERE id=?",
                    (res["verdict"], (res["detail"] or "")[:800],
                     _dt.datetime.now().isoformat(timespec="seconds"), rid),
                )

        msg = (f"{len(by_doi)} unique DOI(s): {resolved} resolved, "
               f"{retracted} RETRACTED, {unresolved} unresolved")
        # A retraction is not routine bookkeeping — surface it as an error so it
        # shows up amber on the dashboard rather than scrolling past as "ok".
        _log_job("citation_backfill", "error" if retracted else "ok", msg)
        log.info("[scheduler] citation_backfill: %s", msg)
    except Exception as exc:
        _log_job("citation_backfill", "error", str(exc)[:300])
        log.error("[scheduler] citation_backfill failed: %s", exc)


def job_focus_refresh() -> None:
    """Keep every ACTIVE focus area current — the "regular updating" half.

    It deliberately does NOT fetch anything itself. `morning_scan` (09:00) and
    `library_scan` (09:03) already pull news and literature into the shared
    collection; a focus is a lens over that collection, so a focus-specific fetch
    path would create items only one surface could ever see, and would re-request
    the same feeds once per focus.

    What this job does is the part nothing else can: stamp each active focus as
    refreshed and record how much arrived through its lens, so the pulse on the
    surface reflects a real scan rather than the last time someone opened the page.

    A focus whose lens returns nothing for a week is reported as such. An empty
    lens looks identical to a quiet field and is far more likely to be the cause.
    """
    log.info("[scheduler] focus_refresh starting")
    try:
        import datetime as _dt
        from db import db_execute
        from metis_mcp.tools.focus import list_focus, focus_news, focus_reading

        active = list_focus("active")
        if not active:
            _log_job("focus_refresh", "skip", "no active focus areas")
            return

        now = _dt.datetime.now().isoformat(timespec="seconds")
        week_ago = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()
        parts, quiet = [], []
        for a in active:
            slug = a["slug"]
            try:
                n_news = len(focus_news(slug, limit=300, since=week_ago))
                n_read = len(focus_reading(slug, limit=300, since=week_ago))
            except Exception as exc:
                log.warning("[scheduler] focus_refresh %s failed: %s", slug, exc)
                continue
            db_execute("UPDATE focus_areas SET last_refreshed_at=? WHERE slug=?",
                       (now, slug))
            parts.append(f"{slug}: {n_news} briefs / {n_read} papers (7d)")
            if n_news == 0 and n_read == 0:
                quiet.append(slug)

        msg = " · ".join(parts) or "nothing to refresh"
        if quiet:
            msg += f" · WARN nothing through the lens for: {', '.join(quiet)}"
        _log_job("focus_refresh", "ok", msg)
        log.info("[scheduler] focus_refresh: %s", msg)
    except Exception as exc:
        _log_job("focus_refresh", "error", str(exc)[:300])
        log.error("[scheduler] focus_refresh failed: %s", exc)


JOB_FUNCS: dict[str, callable] = {
    "db_sync":               job_db_sync,
    "citation_backfill":     job_citation_backfill,
    "focus_refresh":         job_focus_refresh,
    "embedding_backfill":    job_embedding_backfill,
    "brief_synthesis":       job_brief_synthesis,
    "morning_scan":          job_morning_scan,
    "library_scan":          job_library_scan,
    "download_pickup":       job_download_pickup,
    "library_index":         job_library_index,
    "background_index":      job_background_index,
    "office_sync":           job_office_sync,
    "inbox_process":         job_inbox_process,
    "evening_reflexion":     job_evening_reflexion,
    "promise_harness":       job_promise_harness,
    "memory_consolidation":  job_memory_consolidation,
    "weekly_summary":        job_weekly_summary,
    "nightly_backup":        job_nightly_backup,
    "dataset_monitor":       job_dataset_monitor,
    "board_refresh":         job_board_refresh,
    "literature_discovery":  job_literature_discovery,
}

# Human-readable labels for the UI
JOB_LABELS: dict[str, str] = {
    "db_sync":              "Two-computer memory sync",
    "embedding_backfill":   "Memory embedding reconcile",
    "brief_synthesis":      "Morning brief synthesis",
    "morning_scan":         "Morning scan (news + papers)",
    "library_scan":         "Library scan (journals + Zotero + topics)",
    "download_pickup":      "File PDFs downloaded in the browser",
    "library_index":        "Library index",
    "background_index":     "Knowledge backgrounds — index new papers",
    "office_sync":          "Office documents — re-read what changed",
    "inbox_process":        "Inbox processing",
    "citation_backfill":    "Citation checks — resolve DOIs + find retractions",
    "focus_refresh":        "Focus areas — refresh what came through each lens",
    "evening_reflexion":    "Evening reflexion",
    "promise_harness":      "Promise harness (drift)",
    "memory_consolidation": "Nightly memory consolidation",
    "weekly_summary":       "Weekly summary",
    "nightly_backup":       "Nightly DB backup",
    "dataset_monitor":      "Dataset trigger monitor",
    "board_refresh":        "Board refresh (Events & Funding)",
    "literature_discovery": "Literature discovery (weekly papers)",
}

# Default schedule (used when no user-config entry exists)
# Order intentional: scans first, brief synthesis last (it reads what the scans produced)
# Memory consolidation runs at 22:00 — after the day's work, before the 23:00 backup.
# Dataset monitor runs every 2 hours during working hours.
JOB_DEFAULTS: dict[str, dict] = {
    # Runs late, after the day's memory has been written. Purely local (no API
    # cost) — it only reconciles rows that are missing an embedding.
    # Sync first, then embed — so memory merged from the other computer is
    # searchable the same night rather than a day later.
    "db_sync":              {"enabled": True, "time": "22:15"},
    "embedding_backfill":   {"enabled": True, "time": "22:30"},
    "morning_scan":         {"enabled": True, "time": "09:00"},
    # Before library_index (09:05), so a paper discovered this morning is in
    # new_publications by the time the inventory and background indexers run.
    "library_scan":         {"enabled": True, "time": "09:03"},
    # Hourly: a paper downloaded at 14:00 should be filed by 15:00,
    # while the reason for downloading it is still fresh.
    "download_pickup":      {"enabled": True, "every_hours": 1},
    "library_index":        {"enabled": True, "time": "09:05"},
    # Right after the library scan, so a paper that arrived overnight is both
    # catalogued AND searchable by the time the morning brief is written. Without a
    # schedule entry the job would exist and never run — the exact failure this job
    # was written to fix.
    "background_index":     {"enabled": True, "time": "09:07"},
    # Hourly, not daily: a deck edited during the working day should be current
    # in Metis the same afternoon, and the check is a stat() per document.
    "office_sync":          {"enabled": True, "every_hours": 1},
    "inbox_process":        {"enabled": True, "time": "09:10"},
    "brief_synthesis":      {"enabled": True, "time": "09:20"},
    "dataset_monitor":      {"enabled": True, "time": "09:30"},
    "board_refresh":        {"enabled": True, "time": "09:35", "day": "mon"},
    "literature_discovery": {"enabled": True, "time": "09:15", "day": "mon"},
    "evening_reflexion":    {"enabled": True, "time": "09:40"},
    "promise_harness":      {"enabled": True, "time": "10:10", "day": "sun"},
    "memory_consolidation": {"enabled": True, "time": "09:45"},
    "weekly_summary":       {"enabled": True, "time": "09:50", "day": "mon"},
    "nightly_backup":       {"enabled": True, "time": "09:55"},
    # After the backup, so a retraction found tonight is in tomorrow's
    # database and not only in a log line.
    "citation_backfill":    {"enabled": True, "time": "10:00"},
    # After morning_scan (09:00) and library_scan (09:03), so the counts
    # reflect the arrivals from today rather than from yesterday.
    "focus_refresh":        {"enabled": True, "time": "09:12"},
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

        # Repeating jobs: `every_hours: N` → run at minute M of every Nth hour.
        #
        # Added because a config key this loop does not recognise is SILENTLY
        # IGNORED — the job still registers, at the default 07:00, and looks
        # scheduled. A job that runs on a schedule nobody asked for is harder to
        # notice than one that fails, so unknown keys must either work or be loud.
        every_hours = cfg.get("every_hours")
        if every_hours:
            try:
                n = max(1, min(int(every_hours), 23))
                trigger_kwargs = {"hour": f"*/{n}", "minute": minute}
            except (TypeError, ValueError):
                log.warning("[scheduler] job '%s' has an unusable every_hours=%r — "
                            "falling back to the daily time", job_id, every_hours)

        unknown = set(cfg) - {"enabled", "time", "day", "every_hours"}
        if unknown:
            log.warning("[scheduler] job '%s' has unrecognised schedule key(s): %s "
                        "— they do nothing", job_id, ", ".join(sorted(unknown)))

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

    # Reminders are checked every few minutes rather than on the daily cron the
    # other jobs use: a reminder set for 14:30 that fires at the next daily run
    # is not a reminder. Five minutes is close enough to feel prompt and far
    # enough apart to cost nothing.
    try:
        from apscheduler.triggers.interval import IntervalTrigger
        scheduler.add_job(
            job_nature_briefings,
            CronTrigger(hour=7, minute=40),
            id="nature_briefings",
            name="Nature Briefing archive",
            replace_existing=True,
            misfire_grace_time=3600,
            coalesce=True,
        )
        scheduler.add_job(
            job_reminder_due,
            IntervalTrigger(minutes=5),
            id="reminder_due",
            name="Due reminders",
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
        )
        registered.append("reminder_due@5min")
    except Exception as exc:
        log.warning("[scheduler] could not register the reminder check: %s", exc)

    log.info("[scheduler] jobs registered: %s", ", ".join(registered))

    # Catch-up: if the dashboard starts after the scheduled time, fire all
    # missed daily jobs immediately in a background thread (ordered so scans
    # run before the brief synthesis, which needs their data).
    import threading as _threading
    import datetime as _dt
    now_local = _dt.datetime.now()
    settings_cu = _load_job_settings()

    # Catch-up order: data-collection first, then analysis, then housekeeping.
    catchup_sequence = [
        ("morning_scan",        job_morning_scan),
        ("library_scan",        job_library_scan),
        ("download_pickup",     job_download_pickup),
        ("library_index",       job_library_index),
        ("inbox_process",       job_inbox_process),
        ("brief_synthesis",     job_brief_synthesis),
        ("dataset_monitor",     job_dataset_monitor),
        ("evening_reflexion",   job_evening_reflexion),
        ("memory_consolidation", job_memory_consolidation),
        ("db_sync",             job_db_sync),
        ("embedding_backfill",  job_embedding_backfill),
        ("nightly_backup",      job_nightly_backup),
    ]
    missed = []
    for catch_job_id, catch_func in catchup_sequence:
        cfg = {**JOB_DEFAULTS.get(catch_job_id, {}), **settings_cu.get(catch_job_id, {})}
        if not cfg.get("enabled", True):
            continue
        if cfg.get("day"):
            continue  # Weekly jobs are handled separately below
        sched_h, sched_m = _parse_time(cfg.get("time", "10:00"))
        sched_today = now_local.replace(hour=sched_h, minute=sched_m,
                                        second=0, microsecond=0)
        if now_local <= sched_today:
            continue  # not due yet today — the cron will fire it
        # "Missed" means the scheduled time has passed AND it has not run today.
        # Without this second half, every restart re-ran every daily job — 7-8×
        # a morning once a 5-minute heartbeat started restarting the dashboard.
        if _ran_today(catch_job_id):
            log.info("[scheduler] catch-up: '%s' already ran today — skipping", catch_job_id)
            continue
        missed.append((catch_job_id, catch_func))

    # Weekly catch-up: weekly jobs (summary, board_refresh) only fire on their
    # scheduled day — easy to miss on a laptop. Run on startup if they haven't
    # succeeded in the last 6 days.
    weekly_jobs = [
        ("weekly_summary", job_weekly_summary),
        ("board_refresh",  job_board_refresh),
    ]
    for wk_id, wk_func in weekly_jobs:
        wk_cfg = {**JOB_DEFAULTS.get(wk_id, {}), **settings_cu.get(wk_id, {})}
        if not wk_cfg.get("enabled", True):
            continue
        try:
            from db import db_query
            rows = db_query(
                f"SELECT created_at FROM jobs_log WHERE job_type='{wk_id}' "
                "AND status='ok' ORDER BY created_at DESC LIMIT 1"
            )
            due = True
            if rows:
                last_dt = _dt.datetime.fromisoformat(rows[0]["created_at"])
                due = (now_local - last_dt).days >= 6
            if due:
                missed.append((wk_id, wk_func))
        except Exception as exc:
            log.warning("[scheduler] weekly catch-up check for %s failed: %s", wk_id, exc)

    if missed:
        def _run_catchup(jobs):
            for jid, jfunc in jobs:
                log.info("[scheduler] catch-up: running %s", jid)
                try:
                    # Most jobs are plain functions, but `dataset_monitor` is a
                    # coroutine. Calling it here only BUILT the coroutine and threw
                    # it away — "coroutine 'job_dataset_monitor' was never awaited",
                    # a RuntimeWarning in the log and a job that never caught up.
                    # The cron path is fine (AsyncIOScheduler awaits coroutines);
                    # this thread has no event loop, so it needs its own.
                    if inspect.iscoroutinefunction(jfunc):
                        asyncio.run(jfunc())
                    else:
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
