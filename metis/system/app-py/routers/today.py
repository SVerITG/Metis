"""
routers/today.py — Today tab routes and editorial-layout partials (v7.0).

Layout: dateline → hero (greeting + stats) → 2-col canvas (focus / activity) → question prompt.
"""

import datetime
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


# ---------------------------------------------------------------------------
# Full-page
# ---------------------------------------------------------------------------


@router.get("/tab/today", response_class=HTMLResponse)
async def today_tab(request: Request):
    return templates.TemplateResponse(
        request, "today.html", {"active_tab": "today"}
    )


@router.get("/api/tab/today", response_class=HTMLResponse)
async def today_tab_partial(request: Request):
    return templates.TemplateResponse(
        request, "today.html", {"active_tab": "today"}
    )


# ---------------------------------------------------------------------------
# Dateline
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/dateline", response_class=HTMLResponse)
async def today_dateline(request: Request):
    today = datetime.date.today()
    week = today.isocalendar().week
    dateline = f"{today.strftime('%A')} · {today.strftime('%B %-d, %Y')} · Week {week}"

    # Last scan = latest news-radar/librarian/news-aggregator run
    last_scan = None
    try:
        rows = db_query(
            "SELECT created_at FROM agent_runs "
            "WHERE agent_slug IN ('news-radar','librarian','news-aggregator') "
            "ORDER BY created_at DESC LIMIT 1"
        )
        if rows:
            last_scan = _age_label(rows[0]["created_at"]) + " ago"
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_dateline.html",
        {"dateline": dateline, "last_scan": last_scan},
    )


# ---------------------------------------------------------------------------
# Hero: greeting + ambient stats
# ---------------------------------------------------------------------------


_NUMBER_WORDS = {
    0: "No threads",
    1: "One thread",
    2: "Two threads",
    3: "Three threads",
    4: "Four threads",
    5: "Five threads",
}


def _thread_narrative(count: int) -> str:
    if count == 0:
        return "The desk is quiet today."
    word = _NUMBER_WORDS.get(count, f"{count} threads")
    verb = "need" if count != 1 else "needs"
    return f"{word} {verb} you today."


def _user_name() -> str:
    try:
        row = db_query(
            "SELECT value FROM user_config WHERE key = 'user_name' LIMIT 1"
        )
        if row:
            return row[0]["value"]
    except Exception:
        pass
    return "Stef"


@router.get("/api/partial/today/hero", response_class=HTMLResponse)
async def today_hero(request: Request):
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting_word = "Good morning"
    elif hour < 17:
        greeting_word = "Good afternoon"
    else:
        greeting_word = "Good evening"
    greeting = f"{greeting_word}, {_user_name()}."

    today = datetime.date.today()
    since_24h = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()

    # Open threads = blocked + overdue + in_progress tasks
    open_threads = 0
    try:
        open_threads = db_scalar(
            "SELECT COUNT(*) FROM tasks "
            "WHERE status IN ('in_progress','blocked','open')"
        ) or 0
    except Exception:
        pass

    narrative = _thread_narrative(open_threads)

    # Tokens packed today
    total_tokens = 0
    try:
        total_tokens = db_scalar(
            "SELECT COALESCE(SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0)),0) "
            "FROM agent_runs WHERE DATE(created_at) = ?",
            (str(today),),
        ) or 0
    except Exception:
        pass

    if total_tokens >= 1_000_000:
        tokens_display = f"{total_tokens/1_000_000:.1f}M"
    elif total_tokens >= 1_000:
        tokens_display = f"{total_tokens/1_000:.1f}k".replace(".0k", "k")
    else:
        tokens_display = str(total_tokens)

    # Gathered today: news + agent runs + ideas
    gathered = 0
    try:
        n1 = db_scalar("SELECT COUNT(*) FROM news_briefs WHERE created_at >= ?", (since_24h,)) or 0
        n2 = db_scalar("SELECT COUNT(*) FROM agent_runs WHERE created_at >= ?", (since_24h,)) or 0
        n3 = db_scalar("SELECT COUNT(*) FROM ideas WHERE created_at >= ?", (since_24h,)) or 0
        gathered = n1 + n2 + n3
    except Exception:
        pass

    gathered_display = str(gathered)

    return templates.TemplateResponse(
        request,
        "partials/today_hero.html",
        {
            "greeting": greeting,
            "narrative": narrative,
            "open_threads": open_threads,
            "tokens_display": tokens_display,
            "gathered_display": gathered_display,
        },
    )


# ---------------------------------------------------------------------------
# Focus thread (left column)
# ---------------------------------------------------------------------------


def _fmt_relative_time(iso_ts: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso_ts.replace("Z", ""))
    except Exception:
        return "recently"
    now = datetime.datetime.now()
    delta = now - dt
    if delta.days > 1:
        return dt.strftime("%A · %H:%M")
    if delta.days == 1:
        return f"yesterday · {dt.strftime('%H:%M')}"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"today · {dt.strftime('%H:%M')}"
    minutes = delta.seconds // 60
    if minutes >= 1:
        return f"{minutes}m ago"
    return "just now"


@router.get("/api/partial/today/focus-thread", response_class=HTMLResponse)
async def today_focus_thread(request: Request):
    focus = None
    try:
        projects = db_query(
            "SELECT project_id, title, domain, priority, next_step, external_path "
            "FROM projects WHERE status='active' "
            "ORDER BY CASE priority "
            "  WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, "
            "created_at DESC LIMIT 1"
        )
        project = projects[0] if projects else None
    except Exception:
        project = None

    if project:
        pid = project["project_id"]
        # Last agent run timestamp for this project
        resumed_label = "earlier"
        try:
            runs = db_query(
                "SELECT created_at FROM agent_runs "
                "WHERE input_path LIKE ? OR output_path LIKE ? "
                "ORDER BY created_at DESC LIMIT 1",
                (f"%{pid}%", f"%{pid}%"),
            )
            if runs:
                resumed_label = _fmt_relative_time(runs[0]["created_at"])
        except Exception:
            pass

        # Most recent idea or personal_note on this project
        quote = None
        quote_source = None
        try:
            ideas = db_query(
                "SELECT text, created_at FROM ideas "
                "WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (pid,),
            )
            if ideas:
                quote = ideas[0]["text"][:280]
                quote_source = f"captured idea · {_fmt_relative_time(ideas[0]['created_at'])}"
        except Exception:
            pass

        if not quote:
            try:
                notes = db_query(
                    "SELECT content, created_at FROM personal_notes "
                    "ORDER BY created_at DESC LIMIT 1"
                )
                if notes:
                    quote = notes[0]["content"][:280]
                    quote_source = f"personal note · {_fmt_relative_time(notes[0]['created_at'])}"
            except Exception:
                pass

        focus = {
            "project_id": pid,
            "title": project["title"],
            "next_step": project.get("next_step") or "",
            "resumed_label": resumed_label,
            "quote": quote,
            "quote_source": quote_source,
        }

    # Continuous scan status
    scan_text = "Nothing new since the last scan."
    try:
        last_run = db_query(
            "SELECT created_at FROM agent_runs "
            "WHERE agent_slug IN ('news-radar','librarian','news-aggregator') "
            "ORDER BY created_at DESC LIMIT 1"
        )
        if last_run:
            scan_text = (
                f"Last scan {_fmt_relative_time(last_run[0]['created_at'])} — "
                "articles, literature, inbox folder."
            )
        else:
            scan_text = "No scans yet. Run /news-radar or /librarian to begin."
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_focus_thread.html",
        {
            "focus": focus,
            "scan": {"text": scan_text},
        },
    )


# ---------------------------------------------------------------------------
# Activity feed (right column)
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/activity-feed", response_class=HTMLResponse)
async def today_activity_feed(request: Request):
    since = (datetime.datetime.now() - datetime.timedelta(hours=48)).isoformat()
    items = []

    # News briefs
    try:
        for r in db_query(
            "SELECT brief_id, title, summary, domain, created_at, source_url "
            "FROM news_briefs WHERE created_at >= ? "
            "ORDER BY created_at DESC LIMIT 5",
            (since,),
        ) or []:
            items.append({
                "kind": "news",
                "icon": "◆",
                "id": r["brief_id"],
                "time": _hm(r["created_at"]),
                "_ts": r["created_at"],
                "title": (r.get("title") or "Untitled")[:110],
                "summary": (r.get("summary") or "")[:140],
                "href": r.get("source_url"),
            })
    except Exception:
        pass

    # Agent runs
    try:
        for r in db_query(
            "SELECT run_id, agent_slug, task_summary, created_at, output_path "
            "FROM agent_runs WHERE created_at >= ? "
            "ORDER BY created_at DESC LIMIT 5",
            (since,),
        ) or []:
            items.append({
                "kind": "agent",
                "icon": "●",
                "id": r["run_id"],
                "time": _hm(r["created_at"]),
                "_ts": r["created_at"],
                "title": r.get("agent_slug", "agent"),
                "summary": (r.get("task_summary") or "")[:140],
                "href": "/metis",
                "htmx_target": True,
            })
    except Exception:
        pass

    # Meetings
    try:
        for r in db_query(
            "SELECT meeting_id, title, meeting_date, created_at "
            "FROM meetings WHERE created_at >= ? "
            "ORDER BY created_at DESC LIMIT 3",
            (since,),
        ) or []:
            items.append({
                "kind": "meeting",
                "icon": "◉",
                "id": r["meeting_id"],
                "time": _hm(r["created_at"]),
                "_ts": r["created_at"],
                "title": (r.get("title") or "Meeting")[:110],
                "summary": r.get("meeting_date", ""),
                "href": "/meetings",
                "htmx_target": True,
            })
    except Exception:
        pass

    # Ideas (recent captures)
    try:
        for r in db_query(
            "SELECT idea_id, text, idea_type, created_at "
            "FROM ideas WHERE created_at >= ? "
            "ORDER BY created_at DESC LIMIT 3",
            (since,),
        ) or []:
            items.append({
                "kind": "task",
                "icon": "○",
                "id": r["idea_id"],
                "time": _hm(r["created_at"]),
                "_ts": r["created_at"],
                "title": f"Captured {r.get('idea_type') or 'idea'}",
                "summary": (r.get("text") or "")[:140],
                "href": "/thinking",
                "htmx_target": True,
            })
    except Exception:
        pass

    # Sort by timestamp desc
    items.sort(key=lambda x: x.get("_ts", ""), reverse=True)
    items = items[:10]

    return templates.TemplateResponse(
        request,
        "partials/today_activity_feed.html",
        {"items": items},
    )


def _hm(iso_ts: str) -> str:
    """Return HH:MM from an ISO timestamp, with weekday prefix if older than today."""
    try:
        dt = datetime.datetime.fromisoformat(iso_ts.replace("Z", ""))
    except Exception:
        return ""
    today = datetime.date.today()
    if dt.date() == today:
        return dt.strftime("%H:%M")
    return dt.strftime("%a %H:%M")


# ---------------------------------------------------------------------------
# News rail — categorized dispatch next to activity feed
# ---------------------------------------------------------------------------


def _age_label(iso_ts: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso_ts.replace("Z", ""))
    except Exception:
        return ""
    delta = datetime.datetime.now() - dt
    if delta.days >= 7:
        return f"{delta.days // 7}w"
    if delta.days >= 1:
        return f"{delta.days}d"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h"
    minutes = delta.seconds // 60
    if minutes >= 1:
        return f"{minutes}m"
    return "now"


def _signal_class(signal: str) -> str:
    if not signal:
        return "low"
    s = signal.upper()
    if s in ("HIGH", "H"):
        return "high"
    if s in ("MEDIUM", "MED", "M"):
        return "medium"
    return "low"


@router.get("/api/partial/today/news-rail", response_class=HTMLResponse)
async def today_news_rail(request: Request, category: str = ""):
    categories: list[dict] = []
    total_count = 0
    last_updated = None

    try:
        rows = db_query(
            "SELECT domain, COUNT(*) as n, MAX(created_at) as last_ts "
            "FROM news_briefs GROUP BY domain ORDER BY last_ts DESC"
        ) or []
        for r in rows:
            dom = r.get("domain") or "General"
            cnt = r.get("n") or 0
            total_count += cnt
            categories.append({
                "domain": dom,
                "count": cnt,
                "age_label": _age_label(r["last_ts"]) if r.get("last_ts") else "",
                "last_ts": r.get("last_ts"),
            })
        if rows:
            last_updated = _age_label(rows[0]["last_ts"]) + " ago"
    except Exception:
        pass

    # Items: optionally filtered by category
    items = []
    try:
        if category:
            qrows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at "
                "FROM news_briefs WHERE domain = ? ORDER BY created_at DESC LIMIT 8",
                (category,),
            )
        else:
            qrows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at "
                "FROM news_briefs ORDER BY created_at DESC LIMIT 8"
            )
        for r in (qrows or []):
            dom = r.get("domain") or "General"
            items.append({
                "id": r["brief_id"],
                "title": r.get("title") or "Untitled",
                "summary": (r.get("summary") or "")[:180],
                "domain": dom,
                "domain_slug": dom.lower().replace(" ", "-").replace("_", "-"),
                "signal": (r.get("signal_strength") or "").strip(),
                "signal_class": _signal_class(r.get("signal_strength") or ""),
                "source_url": r.get("source_url"),
                "time": _hm(r["created_at"]),
            })
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_news_rail.html",
        {
            "categories": categories,
            "total_count": total_count,
            "items": items,
            "active_category": category,
            "last_updated": last_updated,
        },
    )


# ---------------------------------------------------------------------------
# News summary modal (click-through from activity feed or news tab)
# ---------------------------------------------------------------------------


@router.get("/api/news/brief/{brief_id}", response_class=HTMLResponse)
async def news_brief_detail(request: Request, brief_id: int):
    try:
        rows = db_query(
            "SELECT brief_id, brief_date, title, domain, signal_strength, summary, "
            "source_url, tags, created_at "
            "FROM news_briefs WHERE brief_id = ?",
            (brief_id,),
        )
    except Exception:
        rows = []

    if not rows:
        return HTMLResponse(
            '<div class="news-modal-overlay" onclick="closeNewsModal(event)">'
            '<div class="news-modal-card" onclick="event.stopPropagation()">'
            '<div class="news-modal-body">News brief not found.</div>'
            '<div class="news-modal-footer">'
            '<button class="btn btn-primary btn-sm" onclick="closeNewsModal()">Close</button>'
            '</div></div></div>'
        )

    r = rows[0]
    domain = r.get("domain") or "general"
    domain_slug = domain.lower().replace(" ", "-").replace("_", "-")
    created_display = ""
    if r.get("created_at"):
        try:
            dt = datetime.datetime.fromisoformat(r["created_at"].replace("Z", ""))
            created_display = dt.strftime("%A · %d %B %Y · %H:%M")
        except Exception:
            created_display = r["created_at"]

    brief = {
        "title": r["title"],
        "domain": domain,
        "domain_slug": domain_slug,
        "signal_strength": r.get("signal_strength"),
        "summary": r.get("summary") or "",
        "source_url": r.get("source_url"),
        "tags": r.get("tags"),
        "created_at_display": created_display,
    }
    return templates.TemplateResponse(
        request,
        "partials/news_summary_modal.html",
        {"brief": brief},
    )


# ---------------------------------------------------------------------------
# Legacy/back-compat — kept in case other pages still call these endpoints
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/greeting", response_class=HTMLResponse)
async def today_greeting_legacy(request: Request):
    # Redirect to hero for any old cached callers
    return await today_hero(request)


@router.post("/api/partial/today/scan", response_class=HTMLResponse)
async def today_scan(request: Request):
    """Manual scan trigger — runs a local git status check."""
    scan_results = []
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=rc_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout.strip():
                scan_results.append({
                    "type": "git",
                    "message": "Uncommitted changes in Research Cortex",
                })
            else:
                scan_results.append({"type": "ok", "message": "Research Cortex is clean"})
        except Exception:
            scan_results.append({"type": "info", "message": "Could not run git status"})

    if not scan_results:
        scan_results.append({"type": "ok", "message": "Nothing to report"})

    return HTMLResponse(
        "".join(
            f'<div class="scan-result-row scan-{r["type"]}">{r["message"]}</div>'
            for r in scan_results
        )
    )


@router.get("/api/partial/today/news", response_class=HTMLResponse)
async def today_news(request: Request):
    try:
        briefs = db_query(
            "SELECT brief_id as id, title, domain, signal_strength, summary, source_url, surprise_flag "
            "FROM news_briefs ORDER BY created_at DESC LIMIT 8"
        )
    except Exception:
        briefs = []

    return templates.TemplateResponse(
        request,
        "partials/today_news.html",
        {"briefs": briefs},
    )


@router.get("/api/partial/today/token-footer", response_class=HTMLResponse)
async def today_token_footer(request: Request):
    today = str(datetime.date.today())
    try:
        total_tokens = db_scalar(
            "SELECT COALESCE(SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0)),0) "
            "FROM agent_runs WHERE DATE(created_at) = ?",
            (today,),
        )
        runs_today = db_scalar(
            "SELECT COUNT(*) FROM agent_runs WHERE DATE(created_at) = ?",
            (today,),
        )
    except Exception:
        total_tokens = 0
        runs_today = 0

    return HTMLResponse(
        f'<div class="token-footer">Today: {runs_today} runs · {total_tokens:,} tokens</div>'
    )


# ---------------------------------------------------------------------------
# Archive-layout partials (v8.1 — Today surface redesign)
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/morning-brief", response_class=HTMLResponse)
async def today_morning_brief(request: Request):
    hour = datetime.datetime.now().hour
    if hour < 12:
        greeting_word = "Good morning"
    elif hour < 17:
        greeting_word = "Good afternoon"
    else:
        greeting_word = "Good evening"

    open_threads = 0
    try:
        open_threads = db_scalar(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('in_progress','blocked','open')"
        ) or 0
    except Exception:
        pass

    # Get project focus
    project_title = None
    try:
        rows = db_query(
            "SELECT title FROM projects WHERE status='active' "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END LIMIT 1"
        )
        if rows:
            project_title = rows[0]["title"]
    except Exception:
        pass

    greeting = None
    if project_title:
        greeting = (
            f"{greeting_word}, {_user_name()}. "
            f"Your focus project is <em>{project_title}</em>. "
            f"{'%d thread%s from yesterday are still warm.' % (open_threads, 's' if open_threads != 1 else '') if open_threads else 'The desk is clear — a good moment to push forward.'}"
        )

    narrative = None
    if open_threads > 0:
        narrative = "If you'll take one thing first, take the most urgent thread."

    return templates.TemplateResponse(
        request,
        "partials/today_morning_brief.html",
        {
            "greeting": greeting,
            "narrative": narrative,
            "open_threads": open_threads,
        },
    )


@router.get("/api/partial/today/ledger", response_class=HTMLResponse)
async def today_ledger(request: Request):
    stats = {}
    try:
        stats["article_count"] = db_scalar(
            "SELECT COUNT(*) FROM literature_metadata WHERE source NOT IN ('book','Book') OR source IS NULL"
        ) or 0
    except Exception:
        stats["article_count"] = 0

    try:
        stats["book_count"] = db_scalar(
            "SELECT COUNT(*) FROM library_cards WHERE card_type IN ('book','Book')"
        ) or 0
        if stats["book_count"] == 0:
            stats["book_count"] = db_scalar(
                "SELECT COUNT(*) FROM literature_metadata WHERE source IN ('book','Book')"
            ) or 0
    except Exception:
        stats["book_count"] = 0

    try:
        stats["idea_count"] = db_scalar("SELECT COUNT(*) FROM ideas") or 0
    except Exception:
        stats["idea_count"] = 0

    try:
        stats["thread_count"] = db_scalar(
            "SELECT COUNT(DISTINCT project_id) FROM tasks WHERE status='in_progress'"
        ) or 0
    except Exception:
        stats["thread_count"] = 0

    try:
        stats["project_count"] = db_scalar(
            "SELECT COUNT(*) FROM projects WHERE status='active'"
        ) or 0
    except Exception:
        stats["project_count"] = 0

    try:
        import json as _json
        from pathlib import Path as _Path

        registry_path = (
            _Path(__file__).parent.parent.parent / "config" / "agent-registry.json"
        )
        if not registry_path.exists():
            rc_root = __import__("os").environ.get("METIS_RC_ROOT", "")
            if rc_root:
                registry_path = _Path(rc_root) / "system" / "config" / "agent-registry.json"
        if registry_path.exists():
            data = _json.loads(registry_path.read_text())
            agents = data.get("agents", data) if isinstance(data, dict) else data
            stats["agent_count"] = len(agents) if isinstance(agents, list) else len(agents)
        else:
            stats["agent_count"] = db_scalar("SELECT COUNT(DISTINCT agent_slug) FROM agent_runs") or 0
    except Exception:
        stats["agent_count"] = 0

    try:
        stats["course_count"] = db_scalar(
            "SELECT COUNT(*) FROM learning_courses WHERE status='active'"
        ) or 0
    except Exception:
        stats["course_count"] = 0

    # Phase 8.13 — token pulse (tokens used today across all agent runs)
    try:
        today_iso = datetime.date.today().isoformat()
        tokens_today = db_scalar(
            "SELECT COALESCE(SUM(COALESCE(input_tokens,0) + COALESCE(output_tokens,0)), 0) "
            "FROM agent_runs WHERE DATE(created_at) = ?",
            (today_iso,),
            default=0,
        ) or 0
    except Exception:
        tokens_today = 0
    stats["tokens_today"] = tokens_today
    if tokens_today >= 1_000_000:
        stats["token_tier"] = "alert"   # red
        stats["token_label"] = f"{tokens_today / 1_000_000:.1f}M"
    elif tokens_today >= 500_000:
        stats["token_tier"] = "warn"    # amber
        stats["token_label"] = f"{tokens_today // 1000}K"
    elif tokens_today >= 1000:
        stats["token_tier"] = "ok"
        stats["token_label"] = f"{tokens_today // 1000}K"
    else:
        stats["token_tier"] = "muted"
        stats["token_label"] = str(tokens_today) if tokens_today else "—"

    return templates.TemplateResponse(
        request,
        "partials/today_ledger.html",
        {"stats": stats},
    )


@router.get("/api/partial/today/news-archive", response_class=HTMLResponse)
async def today_news_archive(request: Request):
    news_briefs = []
    categories = set()
    try:
        rows = db_query(
            "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at "
            "FROM news_briefs ORDER BY created_at DESC LIMIT 10"
        ) or []
        for r in rows:
            domain = r.get("domain") or "General"
            categories.add(domain.upper())
            news_briefs.append({
                "brief_id": r.get("brief_id"),
                "title": r.get("title") or "Untitled",
                "domain": domain,
                "summary": (r.get("summary") or "")[:200],
                "source_url": r.get("source_url"),
                "age_label": _age_label(r["created_at"]) if r.get("created_at") else "",
            })
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_news_archive.html",
        {
            "news_briefs": news_briefs,
            "categories": sorted(categories),
        },
    )


@router.get("/api/partial/today/library-archive", response_class=HTMLResponse)
async def today_library_archive(request: Request):
    items = []
    try:
        # Try literature_metadata first
        rows = db_query(
            "SELECT id, title, authors, year, source, tags, abstract, created_at "
            "FROM literature_metadata ORDER BY created_at DESC LIMIT 6"
        ) or []
        for r in rows:
            items.append({
                "title": r.get("title") or "Untitled",
                "authors": r.get("authors") or "",
                "domain": r.get("source") or "",
                "card_type": r.get("source") or "ARTICLE",
                "abstract": (r.get("abstract") or "")[:200],
                "source": r.get("source") or "ARTICLE",
                "created_at": r.get("created_at") or "",
            })
    except Exception:
        pass

    if not items:
        try:
            rows = db_query(
                "SELECT id, title, authors, domain, card_type, content, created_at "
                "FROM library_cards ORDER BY created_at DESC LIMIT 6"
            ) or []
            for r in rows:
                items.append({
                    "title": r.get("title") or "Untitled",
                    "authors": r.get("authors") or "",
                    "domain": r.get("domain") or "",
                    "card_type": r.get("card_type") or "NOTE",
                    "content": (r.get("content") or "")[:200],
                    "source": r.get("card_type") or "NOTE",
                    "created_at": r.get("created_at") or "",
                })
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "partials/today_library_archive.html",
        {"items": items},
    )


@router.get("/api/partial/today/todos-archive", response_class=HTMLResponse)
async def today_todos_archive(request: Request):
    tasks = []
    try:
        rows = db_query(
            "SELECT task_id, title, project, priority, status, created_at "
            "FROM tasks WHERE status NOT IN ('done','completed','cancelled') "
            "ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, "
            "created_at DESC LIMIT 10"
        ) or []
        for r in rows:
            tasks.append({
                "id": r.get("task_id"),
                "title": r.get("title") or "Untitled task",
                "project": r.get("project") or "",
                "priority": r.get("priority") or "",
                "status": r.get("status") or "open",
            })
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_todos_archive.html",
        {"tasks": tasks},
    )


@router.get("/api/partial/today/notebook-archive", response_class=HTMLResponse)
async def today_notebook_archive(request: Request):
    notes = []
    try:
        rows = db_query(
            "SELECT id, content, source, created_at "
            "FROM personal_notes ORDER BY created_at DESC LIMIT 3"
        ) or []
        for r in rows:
            notes.append({
                "content": r.get("content") or "",
                "source": r.get("source") or "notebook",
                "age_label": _age_label(r["created_at"]).upper() + " AGO" if r.get("created_at") else "RECENTLY",
            })
    except Exception:
        pass

    # If no personal_notes, fall back to ideas
    if not notes:
        try:
            rows = db_query(
                "SELECT idea_id, text, idea_type, tags, created_at "
                "FROM ideas ORDER BY created_at DESC LIMIT 3"
            ) or []
            for r in rows:
                notes.append({
                    "content": r.get("text") or "",
                    "source": r.get("idea_type") or r.get("tags") or "idea",
                    "age_label": _age_label(r["created_at"]).upper() + " AGO" if r.get("created_at") else "RECENTLY",
                })
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "partials/today_notebook_archive.html",
        {"notes": notes},
    )


# ---------------------------------------------------------------------------
# Content scan — RSS feeds + literature folder
# ---------------------------------------------------------------------------

@router.post("/api/scan/content")
async def api_scan_content():
    try:
        from metis_mcp.tools.content_scan import scan_literature_folder, scan_news_feeds
        news = scan_news_feeds(max_per_feed=10)
        lit = scan_literature_folder()
    except Exception as e:
        return {"status": "error", "detail": str(e)}

    try:
        db_execute(
            """INSERT INTO agent_runs
               (agent_slug, task_summary, input_path, output_path, status, created_at, model)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "content-scan",
                f"Dashboard scan: {news['news_added']} news, {lit['papers_added']} papers",
                "rss+literature",
                "news_briefs+literature_metadata",
                "completed",
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "none",
            ),
        )
    except Exception:
        pass  # non-fatal — scan result still returned

    return {
        "status": "ok",
        "news_added": news["news_added"],
        "papers_added": lit["papers_added"],
        "news_errors": news.get("errors", []),
    }


# ---------------------------------------------------------------------------
# Handoff brief — Phase 8.13
# ---------------------------------------------------------------------------


@router.post("/api/handoff/generate")
async def api_handoff_generate():
    """Generate a session-handoff markdown via the MCP tools/handoff helper."""
    try:
        from metis_mcp.tools.handoff import generate_handoff_brief
        result = generate_handoff_brief(write_to_journal=True)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Could not generate handoff: {e}"},
            status_code=500,
        )
