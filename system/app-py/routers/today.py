"""
routers/today.py — Today tab routes and editorial-layout partials (v7.0).

Layout: dateline → hero (greeting + stats) → 2-col canvas (focus / activity) → question prompt.
"""

import datetime
import html as _html
import os
import re
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar
from models import model_for  # Resolves Claude model IDs from system/config/models.yaml

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
        import json as _json
        from pathlib import Path as _P
        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            prefs = _P(rc) / "system" / "config" / "user-preferences.json"
            if prefs.exists():
                data = _json.loads(prefs.read_text())
                name = data.get("display_name", "")
                if name:
                    return name
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

    # News freshness check — warn if no content ingested in >24h
    news_stale = False
    news_stale_hours: int = 0
    try:
        since_24h = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()
        recent_news = db_scalar(
            "SELECT COUNT(*) FROM news_briefs WHERE created_at >= ?", (since_24h,)
        ) or 0
        if recent_news == 0:
            # Also check agent_runs for any news scan — could have run without producing briefs
            recent_scan = db_scalar(
                "SELECT MAX(created_at) FROM agent_runs "
                "WHERE agent_slug IN ('news-radar','news-aggregator')"
            )
            if recent_scan:
                delta = datetime.datetime.now() - datetime.datetime.fromisoformat(recent_scan)
                news_stale_hours = int(delta.total_seconds() / 3600)
            else:
                news_stale_hours = 999
            news_stale = True
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_focus_thread.html",
        {
            "focus": focus,
            "scan": {"text": scan_text},
            "field_articles": field_articles,
            "news_stale": news_stale,
            "news_stale_hours": news_stale_hours,
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
        rel = r.get("relevance") or 0
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
            # Semantic closeness to the user's corpus (relevance.py). Qualitative
            # chip, not a raw % — the embedding baseline sits ~0.5 so a % misleads.
            "relevance": rel,
            "match": "top" if rel >= 0.64 else ("yes" if rel >= 0.60 else ""),
        })
    return items


@router.get("/api/partial/today/news-rail", response_class=HTMLResponse)
async def today_news_rail(request: Request, category: str = "", period: str = "week"):
    """News surface — topic slipcases with per-topic Haiku summaries."""
    import sqlite3 as _sq3

    if period not in ("week", "month"):
        period = "week"
    days = 7 if period == "week" else 30
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()

    # Ensure the semantic-relevance column exists (the scanner adds it; guard older DBs).
    try:
        from db import db_execute
        db_execute("ALTER TABLE news_briefs ADD COLUMN relevance REAL DEFAULT 0")
    except Exception:
        pass

    last_updated = None
    try:
        ts_row = db_query("SELECT MAX(created_at) as last_ts FROM news_briefs") or []
        if ts_row and ts_row[0].get("last_ts"):
            last_updated = _age_label(ts_row[0]["last_ts"]) + " ago"
    except Exception:
        pass

    # Build per-topic slipcases
    slipcases: list[dict] = []
    all_topics: list[str] = []
    try:
        topic_rows = db_query(
            "SELECT domain, COUNT(*) as n, MAX(created_at) as last_ts "
            "FROM news_briefs WHERE created_at >= ? AND domain IS NOT NULL AND domain != '' "
            "GROUP BY domain ORDER BY last_ts DESC",
            (cutoff,),
        ) or []
        all_topics = [r["domain"] for r in topic_rows if r.get("domain")]

        # Load stored summaries
        summaries: dict[str, dict] = {}
        try:
            _ensure_news_summaries_table()
            sum_rows = db_query(
                "SELECT topic, summary, article_count, generated_at "
                "FROM news_topic_summaries WHERE period = ?",
                (period,),
            ) or []
            for sr in sum_rows:
                summaries[sr["topic"]] = {
                    "summary": sr.get("summary") or "",
                    "generated_at": sr.get("generated_at") or "",
                }
        except Exception:
            pass

        for tr in topic_rows:
            topic = tr["domain"]
            cnt = tr.get("n") or 0
            age = (_age_label(tr["last_ts"]) + " ago") if tr.get("last_ts") else ""

            # Articles for this topic — most relevant to the user's work first.
            art_rows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at, "
                "COALESCE(relevance,0) as relevance "
                "FROM news_briefs WHERE domain = ? AND created_at >= ? "
                "ORDER BY COALESCE(relevance,0) DESC, created_at DESC LIMIT 10",
                (topic, cutoff),
            ) or []
            items = _build_news_items(art_rows)

            topic_summary = summaries.get(topic, {})
            slipcases.append({
                "topic": topic,
                "count": cnt,
                "age_label": age,
                "items": items,
                "summary": topic_summary.get("summary", ""),
                "summary_age": (_age_label(topic_summary["generated_at"]) + " ago")
                               if topic_summary.get("generated_at") else "",
                "open": topic == category,
            })

        # "Closest to your work" — top items by semantic relevance across all topics,
        # prepended as a personalised section (the pattern pro feeds use).
        try:
            top_rows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at, "
                "COALESCE(relevance,0) as relevance FROM news_briefs "
                "WHERE created_at >= ? AND COALESCE(relevance,0) >= 0.60 "
                "ORDER BY COALESCE(relevance,0) DESC LIMIT 8",
                (cutoff,),
            ) or []
            if top_rows:
                slipcases.insert(0, {
                    "topic": "✦ Closest to your work",
                    "count": len(top_rows),
                    "age_label": "",
                    "items": _build_news_items(top_rows),
                    "summary": "Ranked by how close each item is to your library, projects and interests.",
                    "summary_age": "",
                    "open": True,
                })
        except Exception:
            pass
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_news_rail.html",
        {
            "slipcases": slipcases,
            "all_topics": all_topics,
            "active_topic": category,
            "period": period,
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
            scan_results.append({"type": "info", "message": "I couldn't run git status"})

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
# News topic summaries (C3) — Haiku-generated per-topic news digests
# ---------------------------------------------------------------------------

_NEWS_SUMMARIES_DDL = """
CREATE TABLE IF NOT EXISTS news_topic_summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    topic        TEXT NOT NULL,
    period       TEXT NOT NULL DEFAULT 'week',
    summary      TEXT,
    article_count INTEGER DEFAULT 0,
    generated_at TEXT,
    UNIQUE(topic, period) ON CONFLICT REPLACE
)
"""


def _ensure_news_summaries_table():
    try:
        db_execute(_NEWS_SUMMARIES_DDL)
    except Exception:
        pass


def _haiku_news_summary(topic: str, titles: list[str], period: str, api_key: str) -> str:
    """Call Haiku to summarise recent articles for a topic. Returns summary text."""
    period_label = "this week" if period == "week" else "this month"
    article_list = "\n".join(f"- {t}" for t in titles[:30])
    prompt = (
        f"Here are recent news headlines about '{topic}' from {period_label}:\n\n"
        f"{article_list}\n\n"
        f"Write a 2–3 sentence summary of the key developments. "
        f"Be specific: name diseases, countries, organisations, findings. "
        f"No headers. No bullet points. Plain prose."
    )
    try:
        import httpx as _httpx
        resp = _httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model_for("brief"),
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20.0,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"].strip()
    except Exception:
        pass
    return ""


@router.post("/api/news/summarize")
async def api_news_summarize(request: Request):
    """Generate Haiku summaries for selected topics. Body: {topics: [...], period: 'week'|'month'}"""
    import sqlite3 as _sq3

    try:
        body = await request.json()
    except Exception:
        body = {}
    topics: list[str] = body.get("topics") or []
    period: str = body.get("period", "week")
    if period not in ("week", "month"):
        period = "week"

    # API key
    api_key = _get_api_key()
    if not api_key:
        return JSONResponse({"ok": False, "error": "No API key configured"}, status_code=400)

    _ensure_news_summaries_table()
    db_path = _get_db_path()
    if not db_path:
        return JSONResponse({"ok": False, "error": "DB not found"}, status_code=500)

    days = 7 if period == "week" else 30
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()

    # If no explicit topics, use all available
    if not topics:
        try:
            rows = db_query(
                "SELECT DISTINCT domain FROM news_briefs WHERE created_at >= ? AND domain IS NOT NULL AND domain != ''",
                (cutoff,),
            ) or []
            topics = [r["domain"] for r in rows if r.get("domain")]
        except Exception:
            pass

    generated = 0
    errors = []
    try:
        conn = _sq3.connect(str(db_path))
        conn.row_factory = _sq3.Row
        conn.execute(_NEWS_SUMMARIES_DDL)

        for topic in topics[:15]:  # cap at 15 topics per call
            try:
                rows = conn.execute(
                    "SELECT title FROM news_briefs "
                    "WHERE domain = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 30",
                    (topic, cutoff),
                ).fetchall()
                titles = [r["title"] for r in rows if r["title"]]
                if not titles:
                    continue
                summary = _haiku_news_summary(topic, titles, period, api_key)
                if summary:
                    conn.execute(
                        "INSERT OR REPLACE INTO news_topic_summaries "
                        "(topic, period, summary, article_count, generated_at) VALUES (?,?,?,?,?)",
                        (topic, period, summary, len(titles),
                         datetime.datetime.now().isoformat(timespec="seconds")),
                    )
                    conn.commit()
                    generated += 1
            except Exception as e:
                errors.append(f"{topic}: {e!s:.60}")

        conn.close()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    return JSONResponse({
        "ok": True,
        "generated": generated,
        "topics": topics,
        "period": period,
        "errors": errors,
    })


def _get_brief_mode() -> str:
    """Return brief generation mode: 'auto' | 'auto+manual' | 'manual'."""
    try:
        import json as _json
        rc = os.environ.get("METIS_RC_ROOT", "")
        prefs_path = Path(rc) / "system" / "config" / "user-preferences.json" if rc else None
        if prefs_path and prefs_path.exists():
            mode = _json.loads(prefs_path.read_text()).get("brief_mode", "auto")
            if mode in ("auto", "auto+manual", "manual"):
                return mode
    except Exception:
        pass
    return "auto"


def _get_api_key() -> str:
    """Return the Anthropic API key from env or system/.env file."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        # Try system/.env (uncommented lines only)
        try:
            rc = os.environ.get("METIS_RC_ROOT", "")
            env_p = (Path(rc) / "system" / ".env") if rc else None
            if env_p and env_p.exists():
                for line in env_p.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                        key = line.split("=", 1)[1].strip()
                        os.environ["ANTHROPIC_API_KEY"] = key  # cache for subsequent calls
                        break
        except Exception:
            pass
    return key


# ---------------------------------------------------------------------------
# Archive-layout partials (v8.1 — Today surface redesign)
# ---------------------------------------------------------------------------


def _get_or_generate_brief(force: bool = False, period: str = "daily") -> str | None:
    """Return the AI-generated research brief, generating it if needed.

    period='daily'  → today's brief (keyed by today's date).
    period='weekly' → a week-in-review synthesis (kept as a separate, latest row).

    Checks daily_insights, assembles context via assemble_daily_context(), and
    calls Claude Haiku to synthesize the brief. Stores the result so subsequent
    page loads are free (no API call).

    force=True regenerates. Returns the narrative string, or None if unavailable.
    """
    import json as _json
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
    model_tag = "claude-haiku-weekly" if period == "weekly" else "claude-haiku-brief"
    # Weekly briefs use a distinct storage key so a daily and a weekly brief can
    # coexist for the same day (insight_date is UNIQUE).
    insight_key = f"{today}-weekly" if period == "weekly" else today

    # Check cache — also used as fallback if force-regen fails
    cached_content: str | None = None
    try:
        conn = _sqlite3.connect(db_path_str)
        conn.row_factory = _sqlite3.Row
        if period == "weekly":
            row = conn.execute(
                "SELECT content, model FROM daily_insights "
                "WHERE model = 'claude-haiku-weekly' AND content IS NOT NULL "
                "ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT content, model FROM daily_insights WHERE insight_date = ? LIMIT 1",
                (today,),
            ).fetchone()
        conn.close()
        if row and row["model"] == model_tag and row["content"]:
            cached_content = row["content"]
    except Exception:
        pass

    # In demo mode the canned brief is always served, even on an explicit
    # "Update" (force=True) — so the demo never makes a live API call.
    if cached_content and (not force or os.environ.get("METIS_DEMO") == "1"):
        return cached_content

    # Compute how many days since the last brief was generated
    days_since_last = 1
    try:
        conn2 = _sqlite3.connect(db_path_str)
        prev = conn2.execute(
            "SELECT generated_at FROM daily_insights "
            "WHERE insight_date < ? AND model = 'claude-haiku-brief' "
            "ORDER BY insight_date DESC LIMIT 1",
            (today,),
        ).fetchone()
        conn2.close()
        if prev and prev[0]:
            prev_dt = datetime.datetime.fromisoformat(prev[0])
            days_since_last = max(1, (datetime.datetime.now() - prev_dt).days)
    except Exception:
        pass

    # Load user profile — interests and monitored topics
    interests: list[str] = []
    news_topics: list[str] = []
    research_field = ""
    try:
        from pathlib import Path as _P
        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            prefs_path = _P(rc) / "system" / "config" / "user-preferences.json"
            if prefs_path.exists():
                prefs = _json.loads(prefs_path.read_text(encoding="utf-8"))
                interests = prefs.get("interests", [])
                news_topics = prefs.get("news_topics", [])
                research_field = prefs.get("role", "")
    except Exception:
        pass

    # Assemble context
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                               "mcp-server" / "src"))
        from metis_mcp.tools.intelligence import assemble_daily_context
        ctx = assemble_daily_context(db_path_str)
    except Exception:
        return None

    if not ctx.get("context"):
        return None

    api_key = _get_api_key()
    if not api_key:
        return None

    # Build period description
    name = _user_name()
    if period == "weekly":
        period_desc = "the past week"
    elif days_since_last <= 1:
        period_desc = "today"
    elif days_since_last <= 7:
        period_desc = f"the last {days_since_last} days"
    else:
        period_desc = f"the last {days_since_last // 7} week{'s' if days_since_last >= 14 else ''}"

    field_str = research_field or "public health and epidemiology"
    interests_str = ", ".join(interests[:8]) if interests else "global health, infectious diseases, epidemiology, public health surveillance, health systems"
    topics_str = ", ".join(news_topics[:6]) if news_topics else "WHO surveillance, global health emergencies, disease control, AI in research"

    system_preamble = (
        f"You are writing the daily research intelligence brief for {name}, "
        f"a senior researcher in {field_str}.\n\n"
        f"Their specific research interests: {interests_str}\n"
        f"Topics they monitor daily: {topics_str}\n"
        f"Briefing period: {period_desc}\n\n"
        "Write exactly three paragraphs, 270-320 words total:\n\n"
        "Paragraph 1 — THE LEAD: The single most important development in global health, "
        "science, or AI since the last brief. State what happened and why it matters. "
        f"If it touches {name}'s specific interests — NTDs, disease surveillance, "
        "health information systems, epidemiology methods, AI in research — draw that connection explicitly "
        "and plainly. Don't hint: say it directly.\n\n"
        "Paragraph 2 — THE REST: Two or three other notable developments, grouped thematically. "
        "Cross-reference items when they are connected. Be specific — name papers, organizations, "
        "or numbers when you have them from the context. Group by theme: research findings, "
        "policy news, or field operations.\n\n"
        "Paragraph 3 — THE THREAD: One specific paper, news item, or open question from the "
        f"context that {name} should follow up on today. Name it precisely and say exactly why "
        "it matters for their work right now — not generically, but concretely.\n\n"
        f"Tone: warm, direct, occasionally dry. Like a smart colleague who read everything during {period_desc} "
        "and is giving you the 90-second version before your first meeting. Plain language. "
        "Field-standard terms are fine; unexplained jargon is not. A wry observation is welcome "
        "when the situation calls for it.\n\n"
        "No greeting. No sign-off. No headers. No bullet points. Continuous prose only."
    )

    try:
        import httpx as _httpx
        resp = _httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "prompt-caching-2024-07-31",
                "content-type": "application/json",
            },
            json={
                "model": model_for("brief"),
                "max_tokens": 800,
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
                        f"Research context for {period_desc}:\n\n"
                        f"{ctx['context'][:4000]}"
                    ),
                }],
            },
            timeout=40.0,
        )
        if resp.status_code == 200:
            narrative = resp.json()["content"][0]["text"].strip()

            # Build source items from context — top news with URLs for the template
            source_items: list[dict] = []
            try:
                conn3 = _sqlite3.connect(db_path_str)
                conn3.row_factory = _sqlite3.Row
                since = (datetime.datetime.now() - datetime.timedelta(days=max(days_since_last, 3))).isoformat()
                src_rows = conn3.execute(
                    "SELECT title, domain, source_url FROM news_briefs "
                    "WHERE created_at >= ? ORDER BY "
                    "CASE WHEN signal_strength='high' THEN 1 WHEN signal_strength='medium' THEN 2 ELSE 3 END, "
                    "created_at DESC LIMIT 6",
                    (since,),
                ).fetchall()
                conn3.close()
                for r in src_rows:
                    source_items.append({
                        "title": (r["title"] or "")[:80],
                        "domain": r["domain"] or "",
                        "url": r["source_url"] or "",
                    })
            except Exception:
                pass

            sources_json = _json.dumps(source_items)

            # Cache in daily_insights
            try:
                conn4 = _sqlite3.connect(db_path_str)
                conn4.execute("PRAGMA journal_mode=WAL")
                conn4.execute(
                    """CREATE TABLE IF NOT EXISTS daily_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        insight_date TEXT NOT NULL UNIQUE,
                        content TEXT NOT NULL,
                        sources TEXT DEFAULT '',
                        generated_at TEXT NOT NULL,
                        model TEXT DEFAULT ''
                    )"""
                )
                conn4.execute(
                    """INSERT INTO daily_insights (insight_date, content, sources, generated_at, model)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(insight_date) DO UPDATE SET
                           content = excluded.content, model = excluded.model,
                           sources = excluded.sources,
                           generated_at = excluded.generated_at""",
                    (insight_key, narrative, sources_json,
                     datetime.datetime.now().isoformat(), model_tag),
                )
                conn4.commit()
                conn4.close()
            except Exception:
                pass
            return narrative
    except Exception:
        pass
    # Regeneration failed — return whatever was cached so the brief is never lost
    return cached_content


def _load_brief_sources(db_path_str: str) -> list[dict]:
    """Load today's stored source links from daily_insights.sources (JSON blob)."""
    import json as _json
    import sqlite3 as _sqlite3
    today = datetime.date.today().isoformat()
    try:
        conn = _sqlite3.connect(db_path_str)
        row = conn.execute(
            "SELECT sources FROM daily_insights WHERE insight_date = ? AND model = 'claude-haiku-brief'",
            (today,),
        ).fetchone()
        conn.close()
        if row and row[0]:
            items = _json.loads(row[0])
            if isinstance(items, list):
                return items
    except Exception:
        pass
    return []


def _get_db_path() -> str:
    db = os.environ.get("METIS_DB", "")
    if not db:
        try:
            rc = os.environ.get("METIS_RC_ROOT", "")
            if rc:
                db = str(Path(rc) / "system" / "app" / "data" / "metis.sqlite")
        except Exception:
            pass
    return db


@router.get("/api/partial/today/morning-brief", response_class=HTMLResponse)
async def today_morning_brief(request: Request):
    hour = datetime.datetime.now().hour
    if hour < 12:
        time_of_day = "morning"
    elif hour < 17:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"

    open_threads = 0
    try:
        open_threads = db_scalar(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('in_progress','blocked','open')"
        ) or 0
    except Exception:
        pass

    period = request.query_params.get("period", "daily")
    if period not in ("daily", "weekly"):
        period = "daily"

    ai_brief = None
    brief_date_label = None
    try:
        ai_brief = _get_or_generate_brief(period=period)
    except Exception:
        pass

    # If today's daily brief failed to generate, fall back to the most recent
    # cached brief from any date — the user gets continuity instead of empty space.
    if not ai_brief and period == "daily":
        try:
            import sqlite3 as _sqlite
            db_path = _get_db_path()
            if db_path:
                _conn = _sqlite.connect(db_path)
                _conn.row_factory = _sqlite.Row
                _last = _conn.execute(
                    "SELECT insight_date, content FROM daily_insights "
                    "WHERE model = 'claude-haiku-brief' AND content IS NOT NULL "
                    "ORDER BY insight_date DESC LIMIT 1"
                ).fetchone()
                _conn.close()
                if _last and _last["content"]:
                    ai_brief = _last["content"]
                    brief_date_label = _last["insight_date"]
        except Exception:
            pass

    sources: list[dict] = []
    if ai_brief and not brief_date_label:
        db_path = _get_db_path()
        if db_path:
            sources = _load_brief_sources(db_path)

    fallback_headlines: list[dict] = []
    if not ai_brief:
        try:
            rows = db_query(
                "SELECT title, domain, source_url FROM news_briefs "
                "ORDER BY created_at DESC LIMIT 5"
            ) or []
            for r in rows:
                if r.get("title"):
                    fallback_headlines.append({
                        "title": (r["title"] or "")[:100],
                        "domain": r.get("domain") or "",
                        "url": r.get("source_url") or "",
                    })
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "partials/today_morning_brief.html",
        {
            "brief": ai_brief,
            "brief_date_label": brief_date_label,
            "sources": sources,
            "fallback_headlines": fallback_headlines,
            "open_threads": open_threads,
            "time_of_day": time_of_day,
            "brief_mode": _get_brief_mode(),
            "period": period,
        },
    )


@router.post("/api/morning-brief/refresh", response_class=HTMLResponse)
async def morning_brief_refresh(request: Request):
    """Force regenerate the morning brief and return the updated partial."""
    hour = datetime.datetime.now().hour
    time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"

    try:
        _form = await request.form()
        period = _form.get("period") or request.query_params.get("period") or "daily"
    except Exception:
        period = request.query_params.get("period", "daily")
    if period not in ("daily", "weekly"):
        period = "daily"

    open_threads = 0
    try:
        open_threads = db_scalar(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('in_progress','blocked','open')"
        ) or 0
    except Exception:
        pass

    ai_brief = None
    try:
        ai_brief = _get_or_generate_brief(force=True, period=period)
    except Exception:
        pass

    sources: list[dict] = []
    if ai_brief:
        db_path = _get_db_path()
        if db_path:
            sources = _load_brief_sources(db_path)

    fallback_headlines: list[dict] = []
    if not ai_brief:
        try:
            rows = db_query(
                "SELECT title, domain, source_url FROM news_briefs "
                "ORDER BY created_at DESC LIMIT 5"
            ) or []
            for r in rows:
                if r.get("title"):
                    fallback_headlines.append({
                        "title": (r["title"] or "")[:100],
                        "domain": r.get("domain") or "",
                        "url": r.get("source_url") or "",
                    })
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "partials/today_morning_brief.html",
        {
            "brief": ai_brief,
            "brief_date_label": None,
            "sources": sources,
            "fallback_headlines": fallback_headlines,
            "open_threads": open_threads,
            "time_of_day": time_of_day,
            "brief_mode": _get_brief_mode(),
            "period": period,
        },
    )


@router.get("/api/partial/today/ledger", response_class=HTMLResponse)
async def today_ledger(request: Request):
    stats = {}

    # Papers added in last 7 days (new science signal, not anxiety number)
    try:
        week_ago_iso = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
        stats["unread_count"] = db_scalar(
            "SELECT COUNT(*) FROM literature_metadata "
            "WHERE created_at >= ? AND title IS NOT NULL AND title!=''",
            (week_ago_iso,),
            default=0,
        ) or 0
    except Exception:
        stats["unread_count"] = 0

    # Domain corpus size (core research literature)
    try:
        stats["hat_count"] = db_scalar(
            "SELECT COUNT(*) FROM library_seeded WHERE extension='pdf'", default=0
        ) or 0
    except Exception:
        stats["hat_count"] = 0

    # Open + in-progress tasks
    try:
        stats["open_tasks"] = db_scalar(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('open','in_progress')", default=0
        ) or 0
    except Exception:
        stats["open_tasks"] = 0

    # Blocked tasks (needs its own signal)
    try:
        stats["blocked_count"] = db_scalar(
            "SELECT COUNT(*) FROM tasks WHERE status='blocked'", default=0
        ) or 0
    except Exception:
        stats["blocked_count"] = 0

    # Ideas captured
    try:
        stats["idea_count"] = db_scalar("SELECT COUNT(*) FROM ideas", default=0) or 0
    except Exception:
        stats["idea_count"] = 0

    # Sessions this week (activity rhythm)
    try:
        week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
        stats["sessions_week"] = db_scalar(
            "SELECT COUNT(*) FROM session_summaries WHERE created_at >= ?",
            (week_ago,),
            default=0,
        ) or 0
    except Exception:
        stats["sessions_week"] = 0

    # Token pulse (today's usage)
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
        stats["token_tier"] = "alert"
        stats["token_label"] = f"{tokens_today / 1_000_000:.1f}M"
    elif tokens_today >= 500_000:
        stats["token_tier"] = "warn"
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


def _clean_handoff_text(raw: str) -> str:
    """Strip handoff-brief boilerplate (md headers, auto-gen notes, emphasis) to substance."""
    import re as _re
    out = []
    for ln in (raw or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            continue
        if "Auto-generated by" in s or "Read this first" in s:
            continue
        out.append(s)
    return _re.sub(r"[*_`]+", "", " ".join(out)).strip()


@router.get("/api/partial/today/session-handoff", response_class=HTMLResponse)
async def today_session_handoff(request: Request):
    """Last-session strip — WHAT WE DID (logged agent work) + decisions + an all-sessions link."""
    import json as _json
    import re as _re

    session = None
    try:
        rows = db_query(
            "SELECT session_id, summary, decisions, key_topics, created_at "
            "FROM session_summaries ORDER BY created_at DESC LIMIT 15"
        ) or []
        for r in rows:
            raw = (r.get("summary") or "").strip()
            if "Handoff brief:" in raw and "Stop reason:" in raw:
                continue
            topics, decisions = [], []
            try:
                topics = [t for t in _json.loads(r.get("key_topics") or "[]") if t][:6]
            except Exception:
                pass
            try:
                decisions = [_re.sub(r"[*_`]+", "", str(d)).strip()
                             for d in _json.loads(r.get("decisions") or "[]")
                             if d and len(str(d)) > 8][:4]
            except Exception:
                pass
            created = r.get("created_at") or ""
            session = {
                "date": created[:10],
                "age_label": _age_label(created) if created else "",
                "summary": _clean_handoff_text(raw)[:260],
                "topics": topics,
                "decisions": decisions,
            }
            break
    except Exception:
        pass

    # "What we did" — the most recent LOGGED work (agent runs). The real record,
    # far more informative than the auto-generated handoff header. Not date-locked
    # to the summary (sessions span midnight; logged runs are the truth).
    did = []
    try:
        did = db_query(
            "SELECT agent_slug, task_summary, DATE(created_at) as d FROM agent_runs "
            "WHERE COALESCE(task_summary,'') != '' "
            "ORDER BY created_at DESC LIMIT 6"
        ) or []
    except Exception:
        pass

    total_sessions = 0
    try:
        total_sessions = db_scalar(
            "SELECT COUNT(DISTINCT DATE(created_at)) FROM session_summaries"
        ) or 0
    except Exception:
        pass

    if not session and not did:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request,
        "partials/today_session_handoff.html",
        {"session": session, "did": did, "total_sessions": total_sessions},
    )


@router.get("/api/partial/today/all-sessions", response_class=HTMLResponse)
async def today_all_sessions(request: Request):
    """Overview of every past session — deduped, newest first, with topics + what was done."""
    import json as _json

    sessions = []
    seen = set()
    try:
        rows = db_query(
            "SELECT summary, key_topics, created_at FROM session_summaries "
            "ORDER BY created_at DESC LIMIT 300"
        ) or []
        for r in rows:
            raw = (r.get("summary") or "").strip()
            if ("Handoff brief:" in raw and "Stop reason:" in raw) or len(raw) < 40:
                continue
            day = (r.get("created_at") or "")[:10]
            topics = []
            try:
                topics = [t for t in _json.loads(r.get("key_topics") or "[]") if t][:6]
            except Exception:
                pass
            key = (day, tuple(topics[:3]))
            if key in seen:
                continue
            seen.add(key)
            did = []
            try:
                did = db_query(
                    "SELECT agent_slug, task_summary FROM agent_runs "
                    "WHERE DATE(created_at) = ? AND COALESCE(task_summary,'') != '' "
                    "ORDER BY created_at DESC LIMIT 4",
                    (day,),
                ) or []
            except Exception:
                pass
            sessions.append({
                "date": day,
                "summary": _clean_handoff_text(raw)[:200],
                "topics": topics,
                "did": did,
            })
    except Exception:
        pass

    return templates.TemplateResponse(
        request, "partials/today_all_sessions.html", {"sessions": sessions},
    )


@router.get("/api/partial/today/news-archive", response_class=HTMLResponse)
async def today_news_archive(request: Request):
    news_briefs = []
    try:
        # Compact Today-page rail: just the 4 most relevant signals, one per
        # domain so it doesn't crowd the bottom row. Full archive lives on the
        # News tab — this is just a glance.
        pool = db_query(
            "SELECT rowid as brief_id, title, domain, summary, signal_strength, source_url, created_at "
            "FROM news_briefs ORDER BY created_at DESC LIMIT 80"
        ) or []
        total_count = len(pool)
        seen: dict[str, int] = {}
        for r in pool:
            domain = r.get("domain") or "General"
            if seen.get(domain, 0) >= 1:
                continue
            seen[domain] = seen.get(domain, 0) + 1
            sig = (r.get("signal_strength") or "").lower()
            news_briefs.append({
                "brief_id": r.get("brief_id"),
                "title": r.get("title") or "Untitled",
                "domain": domain,
                "summary": (r.get("summary") or "")[:100],
                "source_url": r.get("source_url"),
                "age_label": _age_label(r["created_at"]) if r.get("created_at") else "",
                "signal": sig if sig in ("high", "medium", "low") else "",
            })
            if len(news_briefs) >= 4:
                break
    except Exception:
        pass

    # Categories derived from actually-displayed items only — no empty tabs
    categories = sorted({b["domain"].upper() for b in news_briefs if b.get("domain")})

    return templates.TemplateResponse(
        request,
        "partials/today_news_archive.html",
        {
            "news_briefs": news_briefs,
            "categories": categories,
            "total_count": total_count if "total_count" in locals() else len(news_briefs),
        },
    )


@router.get("/api/partial/today/resume", response_class=HTMLResponse)
async def today_resume(request: Request):
    """Where you left off — active course + top active project."""
    course = None
    try:
        rows = db_query(
            "SELECT title, current_lesson, next_lesson, progress_pct "
            "FROM learning_courses WHERE status='active' ORDER BY id LIMIT 1"
        )
        if rows:
            r = rows[0]
            course = {
                "title": r.get("title") or "Course",
                "current_lesson": r.get("current_lesson") or "—",
                "next_lesson": r.get("next_lesson") or "—",
                "progress_pct": int(r.get("progress_pct") or 0),
            }
    except Exception:
        pass

    project_rows = None
    try:
        project_rows = db_query(
            "SELECT p.project_id, p.title, p.next_step, "
            "MAX(COALESCE(t.updated_at, t.created_at)) as last_activity "
            "FROM projects p "
            "LEFT JOIN tasks t ON t.project_id = p.project_id "
            "WHERE p.status='active' AND COALESCE(p.domain,'') NOT LIKE '%phd%' "
            "  AND p.project_id NOT IN ('personal','phd-framework') "
            "GROUP BY p.project_id "
            "ORDER BY last_activity DESC NULLS LAST, p.created_at DESC LIMIT 3"
        )
    except Exception:
        pass

    # For each project, fetch the most recently completed task
    _last_tasks: dict[str, str] = {}
    try:
        for row in (project_rows or []):
            pid = (row.get("project_id") or "")
            if not pid:
                continue
            t = db_query(
                "SELECT title FROM tasks WHERE project_id=? AND status='done' "
                "ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 1",
                (pid,),
            )
            if t and t[0].get("title"):
                _last_tasks[pid] = t[0]["title"]
    except Exception:
        pass

    projects = []
    for r in (project_rows or []):
        pid = r.get("project_id") or ""
        last_act = r.get("last_activity") or ""
        projects.append({
            "title": r.get("title") or "Project",
            "next_step": (r.get("next_step") or "")[:180],
            "project_id": pid,
            "last_task": _last_tasks.get(pid, ""),
            "last_activity_label": _age_label(last_act) if last_act else "",
        })

    return templates.TemplateResponse(
        request,
        "partials/today_resume.html",
        {"course": course, "projects": projects},
    )


@router.get("/api/partial/today/idea-today", response_class=HTMLResponse)
async def today_idea_today(request: Request):
    """Single idea — rotates daily — to seed today's thinking, plus cross-pollination prompt."""
    day_idx = datetime.date.today().timetuple().tm_yday

    # Today's highlighted idea (rotating)
    idea = None
    try:
        rows = db_query("SELECT text, idea_type, created_at FROM ideas ORDER BY created_at DESC LIMIT 20") or []
        if rows:
            r = rows[day_idx % len(rows)]
            idea = {"text": (r.get("text") or "")[:500],
                    "idea_type": (r.get("idea_type") or "idea").upper(),
                    "age_label": _age_label(r["created_at"]).upper() if r.get("created_at") else "RECENT"}
    except Exception:
        pass

    # Cross-pollination: recent news × recent idea
    xpoll_news = None
    xpoll_idea = None
    try:
        news_rows = db_query("SELECT title, domain FROM news_briefs ORDER BY created_at DESC LIMIT 14") or []
        if news_rows:
            xpoll_news = news_rows[(day_idx + 3) % len(news_rows)]
    except Exception:
        pass
    try:
        idea_rows = db_query("SELECT text FROM ideas ORDER BY created_at DESC LIMIT 20") or []
        if len(idea_rows) > 1:
            xpoll_idea = idea_rows[(day_idx + 7) % len(idea_rows)]
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_idea_today.html",
        {"idea": idea, "xpoll_news": xpoll_news, "xpoll_idea": xpoll_idea},
    )


@router.get("/api/partial/today/library-archive", response_class=HTMLResponse)
async def today_library_archive(request: Request):
    items = []
    try:
        # Zotero / literature_metadata — most recent with unread flag
        since_month = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
        rows = db_query(
            "SELECT id, title, authors, year, source, tags, abstract, doi, url, created_at, "
            "COALESCE(is_read, 0) as is_read "
            "FROM literature_metadata WHERE created_at >= ? ORDER BY created_at DESC LIMIT 4",
            (since_month,),
        ) or []
        if not rows:
            rows = db_query(
                "SELECT id, title, authors, year, source, tags, abstract, doi, url, created_at, "
                "COALESCE(is_read, 0) as is_read "
                "FROM literature_metadata ORDER BY created_at DESC LIMIT 4"
            ) or []
        for r in rows:
            raw_authors = r.get("authors") or ""
            author_parts = [a.strip() for a in raw_authors.split(",") if a.strip()]
            if len(author_parts) > 2:
                authors_display = f"{author_parts[0]} et al."
            elif author_parts:
                authors_display = ", ".join(author_parts[:2])
            else:
                authors_display = ""
            doi = r.get("doi") or ""
            url = r.get("url") or ""
            item_url = f"https://doi.org/{doi}" if doi else url
            raw_abstract = _html.unescape(r.get("abstract") or "")
            clean_abstract = re.sub(r"<[^>]+>", " ", raw_abstract)
            clean_abstract = re.sub(r"\s+", " ", clean_abstract).strip()
            items.append({
                "title": r.get("title") or "Untitled",
                "authors": authors_display,
                "year": r.get("year") or "",
                "domain": r.get("source") or "",
                "card_type": r.get("source") or "ARTICLE",
                "abstract": clean_abstract[:200],
                "source": r.get("source") or "ARTICLE",
                "doi": doi,
                "url": item_url,
                "created_at": r.get("created_at") or "",
                "age_label": _age_label(r["created_at"]) if r.get("created_at") else "",
                "is_read": bool(r.get("is_read", 0)),
                "silo": "zotero",
            })
    except Exception:
        pass

    # Domain corpus — recent additions (by rowid as proxy for recency)
    try:
        hat_rows = db_query(
            "SELECT basename, top_folder, method, relevance_note, status "
            "FROM library_seeded WHERE extension='pdf' ORDER BY rowid DESC LIMIT 3"
        ) or []
        for r in hat_rows:
            title = (r.get("basename") or "").replace(".pdf", "").replace(".PDF", "")
            status = r.get("status") or "to_triage"
            items.append({
                "title": title[:120],
                "authors": "",
                "year": "",
                "domain": r.get("top_folder") or "Domain",
                "card_type": "DOMAIN CORPUS",
                "abstract": r.get("relevance_note") or r.get("method") or "",
                "source": "Domain",
                "doi": "",
                "url": "",
                "created_at": "",
                "age_label": "",
                "is_read": status not in ("to_triage",),
                "silo": "hat",
            })
    except Exception:
        pass

    if not items:
        try:
            rows = db_query(
                "SELECT id, title, authors, domain, card_type, content, created_at "
                "FROM library_cards ORDER BY created_at DESC LIMIT 4"
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
                    "is_read": True,
                    "silo": "card",
                })
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "partials/today_library_archive.html",
        {"items": items},
    )


# ---------------------------------------------------------------------------
# F-UP1 — Proactive paper surfacing: papers relevant to your ACTIVE work
# ---------------------------------------------------------------------------

_SURFACE_STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "your", "you", "are",
    "was", "were", "will", "into", "onto", "over", "under", "study", "review",
    "project", "analysis", "data", "draft", "article", "paper", "research",
    "work", "next", "step", "task", "using", "based", "new", "use", "via",
    "a", "an", "of", "in", "on", "to", "is", "it", "as", "by", "or", "at",
}


def _salient_terms() -> list[str]:
    """Terms describing the user's active work: project titles + next steps + topics."""
    import yaml as _yaml
    terms: dict[str, int] = {}

    def _add(text: str, weight: int = 1):
        # 3+ chars so domain acronyms (hat, ntd, drc) survive; stopwords filter noise.
        for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", (text or "").lower()):
            if w in _SURFACE_STOPWORDS:
                continue
            terms[w] = terms.get(w, 0) + weight

    try:
        rows = db_query(
            "SELECT title, next_step, domain FROM projects WHERE status='active'"
        ) or []
        for r in rows:
            _add(r.get("title"), 3)
            _add(r.get("next_step"), 2)
            _add(r.get("domain"), 1)
    except Exception:
        pass
    # User-configured research topics (strong signal)
    try:
        rc = os.environ.get("METIS_RC_ROOT", "")
        cfg_path = Path(rc) / "system" / "config" / "user-config.yaml" if rc else None
        if cfg_path and cfg_path.exists():
            cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            research = cfg.get("research", {}) if isinstance(cfg.get("research"), dict) else {}
            topics = research.get("topics") or cfg.get("topics") or []
            if isinstance(topics, str):
                topics = topics.split(",")
            for t in topics:
                _add(str(t), 3)
            _add(str(research.get("field") or ""), 2)
    except Exception:
        pass
    # Most-weighted terms first
    return [t for t, _ in sorted(terms.items(), key=lambda kv: -kv[1])][:25]


@router.get("/api/partial/today/relevant-papers", response_class=HTMLResponse)
async def today_relevant_papers(request: Request):
    """Surface library papers relevant to the user's current active work.

    This is the 'librarian who walks up to your desk' behaviour: it matches
    active-project context + research topics against the library and shows the
    top matches — proactively, without the user searching.
    """
    terms = _salient_terms()
    items: list[dict] = []
    if terms:
        try:
            rows = db_query(
                "SELECT id, title, authors, year, abstract, tags, doi, url, "
                "COALESCE(is_read,0) AS is_read FROM literature_metadata "
                "WHERE COALESCE(title,'') != '' LIMIT 1500"
            ) or []
            # Word-boundary patterns so short acronyms (hat, ntd) don't match
            # "what"/"into" etc.
            term_pats = [(t, re.compile(r"\b" + re.escape(t) + r"\b")) for t in terms]
            scored = []
            for r in rows:
                hay = " ".join([
                    (r.get("title") or ""), (r.get("abstract") or ""), (r.get("tags") or ""),
                ]).lower()
                matched = [t for t, pat in term_pats if pat.search(hay)]
                if not matched:
                    continue
                score = len(matched) + (1 if not r.get("is_read") else 0)
                scored.append((score, matched, r))
            scored.sort(key=lambda x: -x[0])
            for score, matched, r in scored[:4]:
                raw_authors = r.get("authors") or ""
                parts = [a.strip() for a in raw_authors.split(",") if a.strip()]
                authors_display = (f"{parts[0]} et al." if len(parts) > 2
                                   else ", ".join(parts[:2]) if parts else "")
                doi = r.get("doi") or ""
                items.append({
                    "title": r.get("title") or "Untitled",
                    "authors": authors_display,
                    "year": r.get("year") or "",
                    "url": (f"https://doi.org/{doi}" if doi else (r.get("url") or "")),
                    "why": ", ".join(matched[:3]),
                    "is_read": bool(r.get("is_read", 0)),
                })
        except Exception:
            pass

    return templates.TemplateResponse(
        request,
        "partials/today_relevant_papers.html",
        {"items": items, "terms": terms[:6]},
    )


@router.get("/api/partial/today/todos-archive", response_class=HTMLResponse)
async def today_todos_archive(request: Request):
    tasks = []
    try:
        def _fmt_task(r, section):
            return {
                "id": r.get("task_id"),
                "title": r.get("title") or "Untitled task",
                "project": r.get("project_title") or r.get("project_id") or "",
                "project_id": r.get("project_id") or "",
                "status": r.get("status") or "open",
                "starred": bool(r.get("starred", 0)),
                "section": section,
            }

        # Tier 1: blocked (highest urgency)
        blocked = db_query(
            "SELECT t.task_id, t.title, t.project_id, t.status, t.category, t.created_at, t.starred, "
            "p.title as project_title "
            "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
            "WHERE t.status = 'blocked' "
            "ORDER BY t.created_at ASC LIMIT 4"
        ) or []
        blocked_ids = {r["task_id"] for r in blocked}

        # Tier 2: starred non-blocked
        starred = db_query(
            "SELECT t.task_id, t.title, t.project_id, t.status, t.category, t.created_at, t.starred, "
            "p.title as project_title "
            "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
            "WHERE t.starred = 1 AND t.status NOT IN ('done','completed','cancelled','deleted','blocked') "
            "ORDER BY CASE t.status WHEN 'in_progress' THEN 1 ELSE 2 END, t.created_at DESC LIMIT 4"
        ) or []
        starred_ids = {r["task_id"] for r in starred}
        all_ids = blocked_ids | starred_ids

        # Tier 3: oldest open (fills remaining slots up to 6 total)
        oldest = []
        remaining = max(0, 6 - len(blocked) - len(starred))
        if remaining > 0:
            oldest_rows = db_query(
                "SELECT t.task_id, t.title, t.project_id, t.status, t.category, t.created_at, t.starred, "
                "p.title as project_title "
                "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
                "WHERE t.status IN ('open','in_progress') AND t.starred = 0 "
                "ORDER BY t.created_at ASC LIMIT ?",
                (remaining + 4,),
            ) or []
            for r in oldest_rows:
                if r["task_id"] not in all_ids:
                    oldest.append(r)
                    if len(oldest) >= remaining:
                        break

        for r in blocked:
            tasks.append(_fmt_task(r, "blocked"))
        for r in starred:
            tasks.append(_fmt_task(r, "starred"))
        for r in oldest:
            tasks.append(_fmt_task(r, "open"))
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

    # Trigger brief synthesis in background after scan completes
    import threading as _t
    def _synthesise():
        try:
            from scheduler import job_brief_synthesis
            job_brief_synthesis()
        except Exception:
            pass
    _t.Thread(target=_synthesise, daemon=True, name="brief-after-scan").start()

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
            {"status": "error", "message": f"I couldn't generate handoff: {e}"},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# /api/session/consolidate — auto-summarise session from JSONL log
# ---------------------------------------------------------------------------


@router.post("/api/session/consolidate")
async def api_session_consolidate(request: Request):
    """Read today's JSONL session log and write a structured summary to SQLite.

    Called automatically by the stop hook at session end. Accepts optional
    brief_content (the handoff brief markdown) so that the stored summary
    contains real session content, not just tool-call counts.
    """
    import collections
    import json
    import sqlite3

    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        pass
    brief_content: str = body.get("brief_content", "")

    rc_root = os.environ.get("METIS_RC_ROOT", str(Path(__file__).parent.parent.parent))
    today = datetime.date.today().isoformat()
    jsonl_path = Path(rc_root) / "journal" / "sessions" / f"session-{today}.jsonl"

    tool_calls: list[dict] = []
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    tool_calls.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not tool_calls and not brief_content:
        return JSONResponse({"status": "skipped", "reason": "no tool calls and no brief"})

    tools_used = [t.get("tool", "") for t in tool_calls]
    agents = sorted(set(t["agent"] for t in tool_calls if t.get("agent")))
    top_tools = collections.Counter(tools_used).most_common(5)

    # Build summary: prefer handoff brief content (rich) over tool-count summary (thin)
    if brief_content and len(brief_content) > 100:
        # Truncate to first 2000 chars of the brief — captures "What happened" section
        summary = brief_content[:2000].strip()
    else:
        summary_parts = [f"Session on {today}: {len(tool_calls)} tool calls."]
        if agents:
            summary_parts.append(f"Agents active: {', '.join(agents)}.")
        if top_tools:
            summary_parts.append(
                "Most used tools: " + ", ".join(f"{t}×{n}" for t, n in top_tools) + "."
            )
        summary = " ".join(summary_parts)

    # LLM enrichment — if the API key is set and the SDK is installed, ask
    # Claude Haiku to extract a 2-sentence prose summary + a structured
    # topics+decisions list from the brief. Heuristic results below are kept
    # as a safety net.
    llm_summary: str | None = None
    llm_topics: list[str] = []
    llm_decisions: list[str] = []
    try:
        if brief_content and len(brief_content) > 200 and os.environ.get("ANTHROPIC_API_KEY"):
            from anthropic import Anthropic
            client = Anthropic()
            prompt = (
                "You are summarising a researcher's session handoff brief for their "
                "long-term memory. Read the brief below and return a JSON object with "
                "exactly three keys:\n"
                '  "summary": one-or-two-sentence prose summary of what happened (≤ 250 chars)\n'
                '  "topics":  a JSON array of 3–6 short topic strings (project names, themes)\n'
                '  "decisions": a JSON array of 3–8 short decision strings (≤ 120 chars each, '
                'concrete next steps or outcomes)\n\n'
                "Respond with ONLY the JSON. No commentary.\n\n"
                "BRIEF:\n" + brief_content[:6000]
            )
            msg = client.messages.create(
                model=model_for("brief"),
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
            # Strip markdown fences if Haiku wrapped its JSON
            if text.startswith("```"):
                text = text.split("```", 2)[1] if "```" in text[3:] else text
                if text.startswith("json\n"):
                    text = text[5:]
            parsed = json.loads(text)
            llm_summary = (parsed.get("summary") or "").strip()
            llm_topics = [t.strip() for t in parsed.get("topics", []) if t and isinstance(t, str)][:6]
            llm_decisions = [d.strip() for d in parsed.get("decisions", []) if d and isinstance(d, str)][:8]
    except Exception:
        # Any failure here — silent. Heuristic extraction below still runs.
        llm_summary = None
        llm_topics = []
        llm_decisions = []

    if llm_summary:
        # Prepend the LLM's prose to the truncated brief
        summary = llm_summary + ("\n\n" + summary if summary else "")

    # Extract bullet-point content from any handoff-brief section.
    # Real briefs use headings like "Active projects", "Open tasks",
    # "Recent agent runs", "What happened", "Decisions". Capture bullets
    # from any of those — the previous regex only checked three exact
    # heading phrases that briefs never emit, so the field was always empty.
    DECISION_HEADINGS = (
        "what happened", "decision", "key decision",
        "active project", "open task", "recent agent run",
        "next step", "follow-up", "follow up", "outcome",
    )
    extracted_decisions: list[str] = []
    extracted_topics: list[str] = []
    if brief_content:
        in_decision_section = False
        in_projects_section = False
        for line in brief_content.splitlines():
            stripped = line.strip()
            low = stripped.lower()
            if stripped.startswith("##"):
                # Reset both flags on every new ##
                in_decision_section = any(h in low for h in DECISION_HEADINGS)
                in_projects_section = "active project" in low or "project" in low
                continue
            if in_decision_section and stripped.startswith("- ") and len(stripped) > 4:
                item = stripped[2:].strip()
                # Remove markdown bold/italic syntax markers so the stored text reads naturally
                item = item.replace("**", "").replace("__", "").lstrip("*_ ").rstrip()
                if item and item not in extracted_decisions:
                    extracted_decisions.append(item)
            if in_projects_section and stripped.startswith("- "):
                # Project bullets often start with **Name** — extract just the title
                txt = stripped[2:].strip()
                # First bold span = project name, fall back to whole line
                bold_match = txt.split("**")
                topic = bold_match[1] if len(bold_match) >= 3 else txt.split(" — ")[0]
                topic = topic.strip().rstrip(":").strip()
                if topic and topic not in extracted_topics:
                    extracted_topics.append(topic)
        extracted_decisions = extracted_decisions[:10]
        extracted_topics = extracted_topics[:8]

    # Priority order: LLM extraction > heuristic extraction > agent slugs.
    topics_payload = llm_topics or extracted_topics or agents
    decisions_payload = llm_decisions or extracted_decisions

    try:
        db_path = _get_db_path()
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    summary    TEXT NOT NULL,
                    key_topics TEXT,
                    decisions  TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                """INSERT INTO session_summaries
                   (session_id, summary, key_topics, decisions, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    today,
                    summary,
                    json.dumps(topics_payload),
                    json.dumps(decisions_payload),
                    datetime.datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        return JSONResponse({
            "status": "ok",
            "summary": summary[:200],
            "tool_calls": len(tool_calls),
            "agents": agents,
            "topics_extracted": len(extracted_topics),
            "decisions_extracted": len(extracted_decisions),
            "has_brief": bool(brief_content),
        })
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"I couldn't save session summary: {e}"},
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


# ---------------------------------------------------------------------------
# /api/partial/today/research-progress — PhD / research project progress widget
# ---------------------------------------------------------------------------


@router.get("/api/partial/today/research-progress", response_class=HTMLResponse)
async def today_research_progress(request: Request):
    """Research progress widget: article milestones + days since last commit."""
    milestones: list[dict] = []
    try:
        rows = db_query(
            "SELECT milestone_id, article_title, target_date, status, notes "
            "FROM research_milestones ORDER BY target_date ASC LIMIT 6"
        )
        milestones = [dict(r) for r in (rows or [])]
    except Exception:
        pass

    # Days since last git commit in any tracked research project
    days_since_commit: int | None = None
    last_commit_msg: str = ""
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        try:
            result = subprocess.run(
                ["git", "-C", rc_root, "log", "--oneline", "-1", "--format=%ar|%s"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("|", 1)
                rel_time = parts[0].strip()
                last_commit_msg = parts[1].strip() if len(parts) > 1 else ""
                # Parse "N days ago" → integer
                import re as _re
                m = _re.match(r"(\d+)\s+day", rel_time)
                if m:
                    days_since_commit = int(m.group(1))
                elif "hour" in rel_time or "minute" in rel_time or "second" in rel_time:
                    days_since_commit = 0
        except Exception:
            pass

    # Active research projects count
    active_projects = 0
    try:
        active_projects = db_scalar(
            "SELECT COUNT(*) FROM projects WHERE status='active' AND domain NOT IN ('software','personal')",
            default=0,
        ) or 0
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_research_progress.html",
        {
            "milestones": milestones,
            "days_since_commit": days_since_commit,
            "last_commit_msg": last_commit_msg,
            "active_projects": active_projects,
        },
    )
