"""
routers/today.py — Today tab routes and editorial-layout partials (v7.0).

Layout: dateline → hero (greeting + stats) → 2-col canvas (focus / activity) → question prompt.
"""

import datetime
import os
import subprocess
import sys
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


@router.get("/news", response_class=HTMLResponse)
async def news_page(request: Request):
    return templates.TemplateResponse(
        request, "news.html", {"active_tab": "news"}
    )


@router.get("/api/tab/news", response_class=HTMLResponse)
async def news_tab_partial(request: Request):
    return templates.TemplateResponse(
        request, "news.html", {"active_tab": "news"}
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
        if row and row[0].get("value"):
            return row[0]["value"]
    except Exception:
        pass
    try:
        import yaml
        from pathlib import Path as _P
        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            cfg = _P(rc) / "system" / "config" / "user-config.yaml"
            if cfg.exists():
                data = yaml.safe_load(cfg.read_text())
                name = (data or {}).get("user", {}).get("name", "")
                if name:
                    return name
    except Exception:
        pass
    return "Researcher"


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

    # Recent field-relevant articles alert
    field_articles: list[dict] = []
    _field_terms = ("neglected tropical", "ntd", "epidemiology", "surveillance",
                    "global health", "public health", "outbreak")
    # extend with user-configured interests at runtime via get_user_profile()
    since_48h = (datetime.datetime.now() - datetime.timedelta(hours=48)).isoformat()
    try:
        rows = db_query(
            "SELECT brief_id, title, created_at FROM news_briefs "
            "WHERE source_type='article' AND created_at >= ? "
            "ORDER BY created_at DESC LIMIT 20",
            (since_48h,),
        ) or []
        for r in rows:
            t = (r.get("title") or "").lower()
            if any(term in t for term in _field_terms):
                field_articles.append({
                    "id": r["brief_id"],
                    "title": r.get("title") or "Untitled",
                    "time": _fmt_relative_time(r["created_at"]),
                })
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_focus_thread.html",
        {
            "focus": focus,
            "scan": {"text": scan_text},
            "field_articles": field_articles,
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


def _build_news_items(qrows) -> list[dict]:
    items = []
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
    return items


@router.get("/api/partial/today/news-rail", response_class=HTMLResponse)
async def today_news_rail(request: Request, category: str = ""):
    last_updated = None

    try:
        ts_row = db_query(
            "SELECT MAX(created_at) as last_ts FROM news_briefs"
        ) or []
        if ts_row and ts_row[0].get("last_ts"):
            last_updated = _age_label(ts_row[0]["last_ts"]) + " ago"
    except Exception:
        pass

    # General news items (source_type='news' or NULL/'news')
    news_items: list[dict] = []
    try:
        if category:
            qrows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at "
                "FROM news_briefs WHERE (source_type IS NULL OR source_type='news') AND domain=? "
                "ORDER BY created_at DESC LIMIT 10",
                (category,),
            )
        else:
            qrows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at "
                "FROM news_briefs WHERE (source_type IS NULL OR source_type='news') "
                "ORDER BY created_at DESC LIMIT 10"
            )
        news_items = _build_news_items(qrows)
    except Exception:
        pass

    # Scientific articles (source_type='article')
    article_items: list[dict] = []
    try:
        if category:
            qrows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at "
                "FROM news_briefs WHERE source_type='article' AND domain=? "
                "ORDER BY created_at DESC LIMIT 8",
                (category,),
            )
        else:
            qrows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at "
                "FROM news_briefs WHERE source_type='article' "
                "ORDER BY created_at DESC LIMIT 8"
            )
        article_items = _build_news_items(qrows)
    except Exception:
        pass

    # Category chips — only from news items
    categories: list[dict] = []
    total_count = 0
    try:
        rows = db_query(
            "SELECT domain, COUNT(*) as n, MAX(created_at) as last_ts "
            "FROM news_briefs WHERE (source_type IS NULL OR source_type='news') "
            "GROUP BY domain ORDER BY last_ts DESC"
        ) or []
        for r in rows:
            dom = r.get("domain") or "General"
            cnt = r.get("n") or 0
            total_count += cnt
            categories.append({
                "domain": dom,
                "count": cnt,
                "age_label": _age_label(r["last_ts"]) if r.get("last_ts") else "",
            })
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_news_rail.html",
        {
            "categories": categories,
            "total_count": total_count,
            "news_items": news_items,
            "article_items": article_items,
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


def _get_or_generate_brief() -> str | None:
    """Return today's AI-generated morning brief, generating it if needed.

    Checks daily_insights for today. If absent (or only raw context without a
    narrative paragraph), assembles context via assemble_daily_context() and
    calls Claude Haiku to synthesize a 2-3 sentence brief. Stores the result
    so subsequent page loads are free (no API call).

    Returns the narrative string, or None if generation is unavailable.
    """
    import sqlite3 as _sqlite3

    db_path_str = os.environ.get("METIS_DB", "")
    if not db_path_str:
        try:
            from pathlib import Path as _P
            rc = os.environ.get("METIS_RC_ROOT", "")
            if rc:
                db_path_str = str(_P(rc) / "system" / "app" / "data" / "metis.sqlite")
        except Exception:
            pass
    if not db_path_str:
        return None

    today = datetime.date.today().isoformat()

    # Check cache first
    try:
        conn = _sqlite3.connect(db_path_str)
        conn.row_factory = _sqlite3.Row
        row = conn.execute(
            "SELECT content, model FROM daily_insights WHERE insight_date = ? LIMIT 1",
            (today,),
        ).fetchone()
        conn.close()
        if row and row["model"] == "claude-haiku-brief" and row["content"]:
            return row["content"]
    except Exception:
        pass

    # Assemble context
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent /
                               "mcp-server" / "src"))
        from metis_mcp.tools.intelligence import assemble_daily_context
        ctx = assemble_daily_context(db_path_str)
    except Exception:
        return None

    if not ctx.get("context"):
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    # Call Claude Haiku to write the brief — IHP Newsletter pattern
    try:
        import httpx as _httpx
        name = _user_name()
        # Stable system preamble (eligible for prompt caching on repeated calls)
        system_preamble = (
            f"You are writing the daily morning brief for {name}, a senior researcher. "
            "Your voice is like a knowledgeable friend: warm, direct, no corporate language, no bullet lists. "
            "Structure the brief as three short paragraphs:\n"
            "1. ONE LEADING INSIGHT — the single most important development from today's context. "
            "State it plainly and say why it matters.\n"
            "2. TWO OR THREE ITEMS GROUPED BY THEME — briefly note related developments, grouped "
            "by whether they are research findings, policy news, or operational tasks. "
            "Cross-reference items when they connect.\n"
            "3. ONE RESEARCH THREAD — a specific paper, idea, or open question worth returning to today. "
            "Name it and say why now is a good moment.\n"
            "No greeting. No sign-off. No headers. Three paragraphs of prose, total ~150 words."
        )
        resp = _httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "prompt-caching-2024-07-31",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "system": [
                    {
                        "type": "text",
                        "text": system_preamble,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [{
                    "role": "user",
                    "content": (
                        "Today's research context:\n\n"
                        f"{ctx['context'][:3500]}"
                    ),
                }],
            },
            timeout=30.0,
        )
        if resp.status_code == 200:
            narrative = resp.json()["content"][0]["text"].strip()
            # Cache in daily_insights
            try:
                conn = _sqlite3.connect(db_path_str)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS daily_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        insight_date TEXT NOT NULL UNIQUE,
                        content TEXT NOT NULL,
                        sources TEXT DEFAULT '',
                        generated_at TEXT NOT NULL,
                        model TEXT DEFAULT ''
                    )"""
                )
                conn.execute(
                    """INSERT INTO daily_insights (insight_date, content, sources, generated_at, model)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(insight_date) DO UPDATE SET
                           content = excluded.content, model = excluded.model,
                           generated_at = excluded.generated_at""",
                    (today, narrative, ctx["sources"],
                     datetime.datetime.now().isoformat(), "claude-haiku-brief"),
                )
                conn.commit()
                conn.close()
            except Exception:
                pass
            return narrative
    except Exception:
        pass
    return None


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

    # Try AI-generated brief first
    ai_brief = None
    try:
        import sys
        ai_brief = _get_or_generate_brief()
    except Exception:
        pass

    # AI brief is the primary content — show it in the main large slot.
    # Fall back to a static greeting only when the AI brief is unavailable.
    if ai_brief:
        greeting = ai_brief
        narrative = None
    elif project_title:
        greeting = (
            f"{greeting_word}, {_user_name()}. "
            f"Your focus project is <em>{project_title}</em>. "
            f"{'%d thread%s from yesterday are still warm.' % (open_threads, 's' if open_threads != 1 else '') if open_threads else 'The desk is clear — a good moment to push forward.'}"
        )
        narrative = "If you'll take one thing first, take the most urgent thread." if open_threads > 0 else None
    else:
        greeting = None
        narrative = None

    return templates.TemplateResponse(
        request,
        "partials/today_morning_brief.html",
        {
            "greeting": greeting,
            "narrative": narrative,
            "open_threads": open_threads,
            "ai_brief": bool(ai_brief),
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
    """Comprehensive Metis update: news scan + Zotero sync + project staleness check."""
    results: dict = {"status": "ok", "steps": []}

    # ── Step 1: News feeds + literature folder scan
    news_added = 0
    papers_added = 0
    try:
        from metis_mcp.tools.content_scan import scan_literature_folder, scan_news_feeds
        news_r = scan_news_feeds(max_per_feed=10)
        lit_r  = scan_literature_folder()
        news_added   = news_r.get("news_added", 0)
        papers_added = lit_r.get("papers_added", 0)
        results["steps"].append(f"News: {news_added} new signals")
        results["steps"].append(f"Literature folder: {papers_added} new items")
    except Exception as e:
        results["steps"].append(f"News/lit scan error: {e!s:.80}")

    # ── Step 2: Zotero incremental sync
    zotero_added = 0
    try:
        import os, re, sqlite3 as _sq3, urllib.request as _ur, urllib.parse as _up
        from datetime import datetime as _dt
        from pathlib import Path as _P

        rc = os.environ.get("METIS_RC_ROOT", "")
        env_p = _P(rc) / "system" / ".env" if rc else None
        if env_p and env_p.exists():
            for line in env_p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

        api_key = os.environ.get("ZOTERO_API_KEY", "")
        user_id = os.environ.get("ZOTERO_USER_ID", "")
        if api_key and user_id:
            from pyzotero import zotero as _pyz
            zot = _pyz.Zotero(user_id, "user", api_key)
            db_p = _P(rc) / "system" / "app" / "data" / "metis.sqlite" if rc else None
            if db_p and db_p.exists():
                con = _sq3.connect(str(db_p))
                con.row_factory = _sq3.Row
                _SYNC_DDL = ("CREATE TABLE IF NOT EXISTS zotero_sync_state "
                             "(id INTEGER PRIMARY KEY, last_version INTEGER DEFAULT 0, "
                             "last_synced TEXT, item_count INTEGER DEFAULT 0)")
                con.execute(_SYNC_DDL)
                row = con.execute("SELECT last_version FROM zotero_sync_state LIMIT 1").fetchone()
                last_ver = row["last_version"] if row else 0
                items = zot.everything(zot.items(since=last_ver, itemType="-attachment || -note")) if last_ver else []
                added = 0
                for item in items:
                    data = item.get("data", {})
                    if data.get("itemType") in ("attachment", "note"): continue
                    title = (data.get("title") or "")[:500]
                    if not title: continue
                    zk = data.get("key") or ""
                    ex = con.execute("SELECT id FROM literature_metadata WHERE zotero_key=?", (zk,)).fetchone()
                    if not ex:
                        creators = data.get("creators", [])
                        authors = "; ".join(
                            (c["lastName"] + (f", {c['firstName'][0]}." if c.get("firstName") else ""))
                            if c.get("lastName") else c.get("name","")
                            for c in creators[:8] if c.get("lastName") or c.get("name")
                        )[:300]
                        raw_d = data.get("date","") or ""
                        ym = re.search(r"\b(19|20)\d{2}\b", raw_d)
                        yr = int(ym.group()) if ym else None
                        doi = data.get("DOI","")
                        con.execute(
                            "INSERT INTO literature_metadata "
                            "(title,authors,year,source,journal,doi,abstract,url,item_type,zotero_key,zotero_version,library_source,created_at) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (title,authors,yr,data.get("publicationTitle",""),data.get("publicationTitle",""),
                             doi,(data.get("abstractNote","") or "")[:2000],
                             data.get("url","") or (f"https://doi.org/{doi}" if doi else ""),
                             data.get("itemType",""),zk,item.get("version",0),"zotero",_dt.now().isoformat())
                        )
                        added += 1
                if items:
                    try:
                        nv = zot.last_modified_version()
                        tc = con.execute("SELECT COUNT(*) FROM literature_metadata WHERE library_source='zotero'").fetchone()[0]
                        con.execute("DELETE FROM zotero_sync_state")
                        con.execute("INSERT INTO zotero_sync_state (last_version,last_synced,item_count) VALUES (?,?,?)",
                                    (nv, _dt.now().isoformat(), tc))
                    except Exception: pass
                con.commit(); con.close()
                zotero_added = added
                results["steps"].append(f"Zotero: {added} new papers synced")
            else:
                results["steps"].append("Zotero: DB not found")
        else:
            results["steps"].append("Zotero: not configured (no API key)")
    except Exception as e:
        results["steps"].append(f"Zotero sync error: {e!s:.80}")

    # ── Step 3: Project staleness check
    stale_projects = []
    try:
        import os as _os
        from pathlib import Path as _P2
        rc2 = _os.environ.get("METIS_RC_ROOT","")
        proj_rows = db_query("SELECT title, external_path, updated_at FROM projects WHERE status='active'") or []
        import datetime as _dtt
        now = _dtt.datetime.now()
        for pr in proj_rows:
            ext = pr.get("external_path","")
            if not ext: continue
            # Convert Windows path to WSL
            if ":" in ext and not ext.startswith("/mnt/"):
                drive = ext[0].lower(); rest = ext[2:].replace("\\","/")
                ext = f"/mnt/{drive}{rest}"
            planning = _P2(ext) / "PLANNING.md"
            if planning.exists():
                mtime = _dtt.datetime.fromtimestamp(planning.stat().st_mtime)
                days_since = (now - mtime).days
                if days_since > 7:
                    stale_projects.append(f"{pr.get('title','?')} (last updated {days_since}d ago)")
    except Exception:
        pass
    if stale_projects:
        results["steps"].append(f"Projects needing update: {', '.join(stale_projects[:3])}")
    else:
        results["steps"].append("Projects: all up to date")

    # ── Log the run
    try:
        db_execute(
            "INSERT INTO agent_runs (agent_slug,task_summary,input_path,output_path,status,created_at,model) VALUES (?,?,?,?,?,?,?)",
            ("metis-update",
             f"Update: {news_added} news, {papers_added} lit, {zotero_added} Zotero",
             "rss+zotero+projects", "news_briefs+literature_metadata",
             "completed", datetime.datetime.now(datetime.timezone.utc).isoformat(), "none"),
        )
    except Exception:
        pass

    results["news_added"]    = news_added
    results["papers_added"]  = papers_added
    results["zotero_added"]  = zotero_added
    results["summary"]       = " · ".join(results["steps"])
    return results


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


# ---------------------------------------------------------------------------
# /api/doctor — health check (calls metis_mcp.tools.doctor.run_doctor)
# ---------------------------------------------------------------------------


@router.get("/api/doctor")
async def doctor_endpoint():
    """Run metis_doctor and return a structured report for the dashboard."""
    try:
        from metis_mcp.tools.doctor import run_doctor
        return JSONResponse(run_doctor())
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Doctor failed: {e}"},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# /api/schedule/register-morning — manual scheduler entry registration
# ---------------------------------------------------------------------------


@router.post("/api/schedule/register-morning")
async def register_morning_schedule():
    """Register Windows Task Scheduler entries for the morning brief.

    On Windows + WSL: shells out to `schtasks /Create` for News Radar and
    Librarian scans. On non-Windows hosts: returns instructions for `cron`.

    This is an explicit, one-off action triggered by the user from the
    dashboard. It is idempotent — re-running replaces the existing tasks.
    """
    import os
    import subprocess

    if os.name != "nt" and not Path("/mnt/c/Windows").exists():
        # Pure Linux / macOS — give the user the cron line to add.
        cron = (
            "0 7 * * *  cd ~/.local/share/metis-mcp && "
            "./.venv/bin/python -m metis_mcp.cli scan-news\n"
            "30 7 * * *  cd ~/.local/share/metis-mcp && "
            "./.venv/bin/python -m metis_mcp.cli scan-literature"
        )
        return JSONResponse({
            "status": "warn",
            "message": (
                "On Linux/macOS, run `crontab -e` and add:\n\n" + cron
            ),
        })

    # Windows path: register two scheduled tasks via schtasks.exe (called
    # through cmd.exe so it works whether or not we're inside WSL).
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if not rc_root:
        return JSONResponse({
            "status": "error",
            "message": "METIS_RC_ROOT not set — cannot register Task Scheduler entries.",
        }, status_code=500)

    run_script = str(Path.home() / ".local" / "share" / "metis-mcp" / "run.sh")
    actions = [
        ("Metis_NewsRadar", "07:00", "scan-news"),
        ("Metis_LibrarianScan", "07:30", "scan-literature"),
    ]
    results = []
    for name, time_str, sub in actions:
        cmd = (
            f'schtasks /Create /F /SC DAILY /TN "{name}" /ST {time_str} '
            f'/TR "wsl.exe -e bash -lc \\"{run_script} {sub}\\""'
        )
        try:
            proc = subprocess.run(
                ["cmd.exe", "/c", cmd],
                capture_output=True, text=True, timeout=15,
            )
            results.append({
                "task": name,
                "ok": proc.returncode == 0,
                "stdout": proc.stdout.strip()[-200:],
                "stderr": proc.stderr.strip()[-200:],
            })
        except Exception as e:
            results.append({"task": name, "ok": False, "stderr": str(e)})

    failed = [r for r in results if not r["ok"]]
    if failed:
        return JSONResponse({
            "status": "warn",
            "message": (
                "Registration partially failed. Run `/schedule` from Claude "
                "Code for an interactive setup."
            ),
            "results": results,
        })
    return JSONResponse({
        "status": "ok",
        "message": "Morning brief scheduled. First run tomorrow at 07:00.",
        "results": results,
    })
