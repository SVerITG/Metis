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

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import RELEVANCE_CLOSE, db_execute, db_query, db_scalar
from ui import (clip, count_since, delta_count, last_seen, mark_seen,  # noqa: E402
                nothing, peek, zone)
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
            # Papers must never appear on the News surface. `source_type` already
            # tags them ('article' vs 'news') and the literature panel above filters
            # ON it — but these queries never did, so 53 journal articles kept
            # surfacing as news. The data-model half of the fix shipped; this is the
            # half that was missing.
            "SELECT brief_id, title, summary, domain, created_at, source_url "
            "FROM news_briefs WHERE created_at >= ? "
            "AND COALESCE(source_type,'news') != 'article' "
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
                "summary": clip(r.get("summary") or "", 140),
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
                "summary": clip(r.get("task_summary") or "", 140),
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
                "summary": clip(r.get("text") or "", 140),
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
        dt = datetime.datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except Exception:
        return ""
    # Timestamps may be tz-aware (…+00:00) or naive. datetime.now(dt.tzinfo)
    # matches the parsed value's awareness, avoiding "can't subtract
    # offset-naive and offset-aware datetimes".
    delta = datetime.datetime.now(dt.tzinfo) - dt
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
            "summary": clip(r.get("summary") or "", 180),
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


async def render_news_rail(request: Request, category: str = "",
                           period: str = "week") -> str:
    """The Today news rail, as a string, so a triage click can give it back.

    Extracted 2026-08-26 alongside the reading stack: pressing "read later" on a
    headline has to return the rail it came from, and a route that can only
    answer HTTP cannot be reused for that.

    `async`, and awaited by the caller. The first draft called
    `run_until_complete` on the running loop, which raises — a route already runs
    inside that loop, so there is nothing to run it from.
    """
    resp = await today_news_rail(request, category, period)
    return resp.body.decode("utf-8")


@router.get("/api/partial/today/news-rail", response_class=HTMLResponse)
async def today_news_rail(
    request: Request, category: str = "", period: str = "week", folded: int = 0
):
    """News surface — topic slipcases with per-topic Haiku summaries.

    `folded=1` is Today asking for the rail without its own heading, because
    there the <summary> of the fold IS the heading and two would read as a
    stutter. The counts it would have shown are sent back out-of-band into
    that summary instead, so the closed fold still states what is inside it.
    The News surface passes nothing and keeps its heading.
    """
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
            # Same reason as the news rail: a topic chip counting journal articles
            # sends the reader to a "news" topic made of papers.
            "SELECT domain, COUNT(*) as n, MAX(created_at) as last_ts "
            "FROM news_briefs WHERE created_at >= ? AND domain IS NOT NULL AND domain != '' "
            "AND COALESCE(source_type,'news') != 'article' "
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
                "COALESCE(relevance,0) as relevance, seen_at "
                "FROM news_briefs WHERE domain = ? AND created_at >= ? "
                "AND COALESCE(source_type,'news') != 'article' "
                "ORDER BY COALESCE(relevance,0) DESC, created_at DESC LIMIT 5",
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
                "open": topic == category,  # only open if user clicked into it
            })

        # "Closest to your work" — top items by semantic relevance across all topics,
        # prepended as a personalised section (the pattern pro feeds use).
        try:
            top_rows = db_query(
                "SELECT brief_id, title, domain, summary, signal_strength, source_url, created_at, "
                "COALESCE(relevance,0) as relevance FROM news_briefs "
                "WHERE created_at >= ? AND COALESCE(relevance,0) >= " + str(RELEVANCE_CLOSE) + " "
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

    # Cap visible slipcases: "Closest to your work" (always first) + top 7 topics.
    # The rest are hidden behind "Show all N topics".
    show_all_topics = request.query_params.get("all_topics") == "1"
    total_topics = len(slipcases)
    if not show_all_topics and total_topics > 8:
        slipcases = slipcases[:8]

    # One lookup for every headline across every slipcase.
    _ids = [i["id"] for sc in slipcases for i in sc.get("items") or []]
    try:
        from metis_mcp.tools import stack as _stack
        _states = _stack.states_for("news", _ids)
        _tags = _stack.all_tags()
    except Exception as _exc:
        _log.warning("news rail: stack state unavailable: %s", _exc)
        _states, _tags = {}, []

    return templates.TemplateResponse(
        request,
        "partials/today_news_rail.html",
        {
            "states": _states,
            "all_tags": _tags,
            "slipcases": slipcases,
            "all_topics": all_topics,
            "active_topic": category,
            "period": period,
            "folded": bool(folded),
            "last_updated": last_updated,
            "total_topics": total_topics,
            "show_all_topics": show_all_topics,
            # "What is new since I last looked" — the one thing that turns a feed
            # into something readable rather than an undifferentiated wall. 859
            # briefs with no seen-state showed the same items every visit.
            "unseen_count": db_scalar(
                "SELECT COUNT(*) FROM news_briefs WHERE seen_at IS NULL "
                "AND COALESCE(source_type,'news') != 'article' AND created_at >= ?",
                (cutoff,), default=0,
            ) or 0,
        },
    )


@router.post("/api/news/mark-seen", response_class=HTMLResponse)
async def news_mark_seen(request: Request, period: str = "week", folded: int = 0):
    """Mark everything currently in view as seen, then redraw the rail."""
    import datetime as _dt

    db_execute(
        "UPDATE news_briefs SET seen_at = ? WHERE seen_at IS NULL "
        "AND COALESCE(source_type,'news') != 'article'",
        (_dt.datetime.now().isoformat(timespec="seconds"),),
    )
    return await today_news_rail(request, category="", period=period, folded=folded)


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


@router.get("/api/build")
async def api_build():
    """The build this server is serving, so a tab can tell it is out of date.

    An open tab has no way to know the dashboard restarted under it. It asks
    this on focus and compares with the stamp it loaded, which is what turns
    "an old Metis is still open" from something you have to notice into
    something the page says.
    """
    from main import ASSET_V
    return JSONResponse({"ok": True, "build": ASSET_V})


@router.get("/api/update/api-available")
async def api_update_available():
    """Is the paid update path usable at all? Asked BEFORE the chain starts.

    Without this the full update discovers a missing key on step 5, having
    already spent four steps and several minutes getting there. One cheap
    question first is the difference between "no API key is configured" and
    "four things failed and here is the last error".
    """
    return JSONResponse({"ok": True, "has_key": bool(_get_api_key())})


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


import logging as _logging
import threading as _threading
import time as _time

_log = _logging.getLogger("metis")
_brief_gen_inflight: set = set()
_brief_gen_lock = _threading.Lock()
_brief_last_attempt: dict = {}   # period -> monotonic ts of the last generation attempt
_brief_last_error: dict = {}     # period -> error string for display


def _get_cached_brief(period: str = "daily") -> str | None:
    """Cache-only read of the brief — NEVER calls the API, so the Today page can
    render instantly. Background generation fills the cache (see
    _kick_brief_generation)."""
    import sqlite3 as _sqlite3

    db_path_str = _get_db_path()
    if not db_path_str:
        return None
    today = datetime.date.today().isoformat()
    try:
        conn = _sqlite3.connect(db_path_str)
        conn.row_factory = _sqlite3.Row
        if period == "weekly":
            row = conn.execute(
                "SELECT content, model FROM daily_insights "
                "WHERE model='claude-haiku-weekly' AND content IS NOT NULL "
                "ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()
            accepted = {"claude-haiku-weekly"}
        elif period == "catchup":
            row = conn.execute(
                "SELECT content, model FROM daily_insights "
                "WHERE model='claude-sonnet-catchup' AND content IS NOT NULL "
                "ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()
            accepted = {"claude-sonnet-catchup"}
        else:
            row = conn.execute(
                "SELECT content, model FROM daily_insights WHERE insight_date=? LIMIT 1",
                (today,),
            ).fetchone()
            accepted = {"claude-haiku-brief", "desktop-brief"}
        conn.close()
        if row and row["content"] and row["model"] in accepted:
            return row["content"]
    except Exception:
        pass
    return None


def _kick_brief_generation(period: str = "daily") -> None:
    """Generate the brief on a daemon thread (idempotent; concurrent calls are
    deduped). The caller rate-limits retries (~90s) so a transient failure
    self-heals on the next poll instead of giving up. Failures are logged."""
    with _brief_gen_lock:
        if period in _brief_gen_inflight:
            return
        _brief_gen_inflight.add(period)
        _brief_last_attempt[period] = _time.monotonic()

    def _run():
        try:
            result = _get_or_generate_brief(period=period)
            if result:
                _brief_last_error.pop(period, None)
            else:
                # _get_or_generate_brief swallows exceptions and returns None;
                # surface a diagnostic so the template shows the error instead
                # of polling forever with "Brewing…".
                _brief_last_error[period] = (
                    "Brief generation returned empty — check the server log. "
                    "Common causes: missing API key, no news data, or import error."
                )
                _log.warning("morning-brief generation returned None for period=%s", period)
        except Exception as e:
            _brief_last_error[period] = f"{type(e).__name__}: {str(e)[:200]}"
            _log.warning("morning-brief background generation failed", exc_info=True)
        finally:
            _brief_gen_inflight.discard(period)

    _threading.Thread(target=_run, daemon=True, name="brief-gen").start()


def _last_brief_generated_at(db_path_str: str = "") -> datetime.datetime | None:
    """Return the datetime of the last daily brief, or None."""
    import sqlite3 as _sqlite3
    if not db_path_str:
        db_path_str = _get_db_path()
    if not db_path_str:
        return None
    try:
        conn = _sqlite3.connect(db_path_str)
        row = conn.execute(
            "SELECT generated_at FROM daily_insights "
            "WHERE model IN ('claude-haiku-brief','desktop-brief') AND content IS NOT NULL "
            "ORDER BY insight_date DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row and row[0]:
            return datetime.datetime.fromisoformat(row[0])
    except Exception:
        pass
    return None


def _brief_system_prompt(
    period: str,
    name: str,
    field: str,
    interests: str,
    topics: str,
    period_desc: str,
    gap_label: str = "",
) -> str:
    """Build the system prompt for the daily/weekly/catchup brief."""

    guardrail = (
        "IMPORTANT: Write about external developments only — never about the "
        "researcher's own tools, software, or AI systems. Projects and ideas "
        "are provided as framing context only — they are relevance anchors, "
        "not briefing topics."
    )

    # Anti-repetition contract. The context groups news into story threads and
    # labels each with what the researcher has already been told; without these rules the
    # model still leads with the biggest story every day, which is exactly the
    # behaviour the thread layer exists to stop. See tools/news_threads.py.
    freshness = (
        "FRESHNESS CONTRACT — this brief is read every day, so repetition is the "
        "main failure mode:\n"
        "- Lead ONLY with a thread listed under 'ELIGIBLE TO LEAD'. Never lead with "
        "a thread under 'ALREADY DELIVERED', however large it is.\n"
        "- A long-running story that has not changed deserves silence, not a "
        "paragraph. Saying nothing about it is correct, not an omission.\n"
        "- If an already-delivered thread genuinely escalated (its line says "
        "ESCALATION), you may lead with it — say plainly what changed since last "
        "time rather than re-describing the story.\n"
        "- Take the ANGLE offered for the thread you lead with. The angles already "
        "used are listed; do not reuse them. Same story, new lens.\n"
        "- Never open with a phrase you would have used yesterday. No 'continues to', "
        "'remains a concern', 'ongoing situation' as a lead.\n"
    )

    preamble = (
        f"You are writing a research intelligence brief for {name}, "
        f"a senior researcher in {field}.\n\n"
        f"Their specific research interests: {interests}\n"
        f"Topics they monitor: {topics}\n"
        f"Briefing period: {period_desc}\n\n"
        f"{guardrail}\n\n"
        f"{freshness}\n"
    )

    # Appended to every period so coverage is recorded and cooldowns advance.
    # The path insert is defensive: without the footer no coverage is recorded,
    # nothing ever goes on cooldown, and the repetition returns silently — so
    # this must not depend on another function having set sys.path first.
    footer = ""
    try:
        _src = str(Path(__file__).parent.parent.parent / "mcp-server" / "src")
        if _src not in sys.path:
            sys.path.insert(0, _src)
        from metis_mcp.tools.news_threads import COVERAGE_FOOTER_INSTRUCTION as _footer_txt
        footer = f"\n\n{_footer_txt}"
    except Exception as _exc:
        _log.warning("morning-brief: coverage footer unavailable (%s) — "
                     "threads will not be recorded and the brief may repeat", _exc)

    if period == "weekly":
        return preamble + (
            "Write exactly four paragraphs, 400–500 words total:\n\n"
            "Paragraph 1 — THE WEEK: The two or three most significant developments "
            "in global health, science, or AI this week. State what happened and why "
            "it matters. Be specific — name papers, organisations, numbers.\n\n"
            "Paragraph 2 — PATTERNS: Step back from individual items and identify "
            "one or two emerging patterns, policy shifts, or methodological trends "
            "across the week's signals. Cross-reference items when connected.\n\n"
            "Paragraph 3 — THE BRIDGE: One concrete connection between an external "
            f"signal and {name}'s active research or interests. Be explicit about "
            "why it matters and what opportunity or risk it creates.\n\n"
            "Paragraph 4 — ONE THING: A single paper, report, or question worth "
            f"following up on next week. Name it precisely and say why {name} "
            "should prioritise it.\n\n"
            "WEEKLY-SPECIFIC RULE — this overrides the daily freshness contract "
            "above. The weekly is COMPLETE on purpose: it must cover the week's "
            "significant threads even where the dailies held them back, because "
            f"{name} reads it as an overview rather than a diff. So do not suppress "
            "anything here. What changes is the treatment:\n"
            "- A thread marked ALREADY SEEN: give its TRAJECTORY across the week — "
            "where it started, what moved, where it stands now. Never restate the "
            "daily item he already read.\n"
            "- A thread marked NOT YET SEEN: report it properly and completely. He "
            "has never been told, so this is new information however old the story.\n"
            "- Prefer a never-seen thread for Paragraph 4 (ONE THING) when one is "
            "of comparable importance.\n\n"
            f"Tone: warm, direct, occasionally dry. Like a smart colleague giving the "
            f"5-minute week-in-review. Plain language. Field-standard terms fine; "
            f"unexplained jargon is not.\n\n"
            "No greeting. No sign-off. No headers. No bullet points. Continuous prose only."
            + footer
        )

    if period == "catchup":
        gap_note = f" ({gap_label})" if gap_label else ""
        return preamble + (
            f"The researcher has been away{gap_note}. Write exactly four paragraphs, "
            "400–500 words total:\n\n"
            "Paragraph 1 — WHAT YOU MISSED: The two or three most important developments "
            "since the last brief. Lead with the highest-impact item. State facts, not "
            "opinions.\n\n"
            "Paragraph 2 — WHAT CHANGED: Any shifts in policy, emerging patterns, or "
            "new publications that alter the landscape of their field. Reference the "
            "previous brief (provided) to highlight what's genuinely new vs. continuing.\n\n"
            "Paragraph 3 — CONNECTIONS: One or two concrete links between missed signals "
            f"and {name}'s active research. Be specific about implications.\n\n"
            "Paragraph 4 — START HERE: The single most important thing to read, review, "
            "or act on first. Name it and say why it's the priority re-entry point.\n\n"
            "CATCH-UP-SPECIFIC RULE — draw your content from the threads marked "
            "NEVER DELIVERED. Those are what he actually missed. Threads marked "
            "ALREADY SEEN are for continuity: give their current state in a clause, "
            "never a paragraph.\n\n"
            f"Tone: warm, efficient. Like a trusted colleague bringing you up to speed "
            f"after time away. No filler.\n\n"
            "No greeting. No sign-off. No headers. No bullet points. Continuous prose only."
            + footer
        )

    # Default: daily
    return preamble + (
        "Write exactly three paragraphs, 270–320 words total:\n\n"
        "Paragraph 1 — THE LEAD: The most important development from a thread listed "
        "as ELIGIBLE TO LEAD. State what happened and why it matters. "
        f"If it touches {name}'s specific interests, draw that connection explicitly "
        "and plainly. Don't hint: say it directly. If the only eligible threads are "
        "modest, lead with a modest story — a smaller genuinely-new lead is better "
        "than a large one he has already read.\n\n"
        "Paragraph 2 — THE FIELD: Two or three other notable developments, grouped "
        "thematically. Cross-reference items when they are connected. Be specific — "
        "name papers, organisations, or numbers. Group by theme. This is where an "
        "already-delivered thread may earn one clause, and only if it has moved.\n\n"
        "Paragraph 3 — THE THREAD: One specific paper, news item, or open question "
        f"from the context that {name} should follow up on today. Name it precisely "
        "and say exactly why it matters for their work right now — concretely.\n\n"
        f"Tone: warm, direct, occasionally dry. Like a smart colleague who read "
        f"everything during {period_desc} and is giving you the 90-second version. "
        "Plain language. Field-standard terms fine; unexplained jargon is not.\n\n"
        "No greeting. No sign-off. No headers. No bullet points. Continuous prose only."
        + footer
    )


def _get_or_generate_brief(force: bool = False, period: str = "daily") -> str | None:
    """Return the AI-generated research brief, generating it if needed.

    period='daily'   → today's brief (keyed by today's date, Haiku).
    period='weekly'  → a week-in-review synthesis (Sonnet).
    period='catchup' → catch-up after absence (Sonnet).

    Checks daily_insights, assembles context via the appropriate assembly function,
    and calls Claude to synthesize the brief. Stores the result so subsequent
    page loads are free (no API call).

    force=True regenerates. Returns the narrative string, or None if unavailable.
    """
    import json as _json
    import sqlite3 as _sqlite3

    db_path_str = os.environ.get("METIS_DB", "")
    if not db_path_str:
        try:
            from db import get_db_path
            db_path_str = str(get_db_path())
        except Exception:
            pass
    if not db_path_str:
        _log.warning("morning-brief: no database path found (METIS_DB unset)")
        return None

    today = datetime.date.today().isoformat()
    _model_tags = {
        "daily": "claude-haiku-brief",
        "weekly": "claude-haiku-weekly",
        "catchup": "claude-sonnet-catchup",
    }
    model_tag = _model_tags.get(period, "claude-haiku-brief")
    # Each period uses a distinct storage key so they can coexist for the same day.
    _key_suffixes = {"weekly": "-weekly", "catchup": "-catchup"}
    insight_key = today + _key_suffixes.get(period, "")

    # Check cache — also used as fallback if force-regen fails
    cached_content: str | None = None
    try:
        conn = _sqlite3.connect(db_path_str)
        conn.row_factory = _sqlite3.Row
        if period in ("weekly", "catchup"):
            row = conn.execute(
                "SELECT content, model FROM daily_insights "
                "WHERE model = ? AND content IS NOT NULL "
                "ORDER BY generated_at DESC LIMIT 1",
                (model_tag,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT content, model FROM daily_insights WHERE insight_date = ? LIMIT 1",
                (today,),
            ).fetchone()
        conn.close()
        # Accept the dashboard's own brief, or a brief composed from Claude Desktop/Code.
        accepted_tags = {model_tag}
        if period == "daily":
            accepted_tags.add("desktop-brief")
        if row and row["content"] and row["model"] in accepted_tags:
            cached_content = row["content"]
    except Exception:
        pass

    # In demo mode the canned brief is always served, even on an explicit
    # "Update" (force=True) — so the demo never makes a live API call.
    if cached_content and (not force or os.environ.get("METIS_DEMO") == "1"):
        return cached_content

    # Compute how many days since the last brief was generated
    days_since_last = 1
    last_brief_dt = _last_brief_generated_at(db_path_str)
    if last_brief_dt:
        days_since_last = max(1, (datetime.datetime.now() - last_brief_dt).days)

    # Gap label for catch-up display (e.g. "3 DAYS", "1 WEEK")
    gap_label = ""
    if days_since_last >= 14:
        gap_label = f"{days_since_last // 7} WEEKS"
    elif days_since_last >= 7:
        gap_label = "1 WEEK"
    elif days_since_last >= 2:
        gap_label = f"{days_since_last} DAYS"

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

    # Assemble context — route to the right function based on period
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent /
                               "mcp-server" / "src"))
        from metis_mcp.tools.intelligence import (
            assemble_daily_context,
            assemble_weekly_context,
            assemble_catchup_context,
        )
        if period == "weekly":
            ctx = assemble_weekly_context(db_path_str)
        elif period == "catchup":
            # Load previous brief content for contrast
            prev_brief = ""
            try:
                conn_pb = _sqlite3.connect(db_path_str)
                pb_row = conn_pb.execute(
                    "SELECT content FROM daily_insights "
                    "WHERE model IN ('claude-haiku-brief','desktop-brief') "
                    "AND content IS NOT NULL ORDER BY insight_date DESC LIMIT 1"
                ).fetchone()
                conn_pb.close()
                if pb_row and pb_row[0]:
                    prev_brief = pb_row[0]
            except Exception:
                pass
            since_iso = last_brief_dt.isoformat() if last_brief_dt else ""
            ctx = assemble_catchup_context(db_path_str, since_iso, prev_brief)
        else:
            ctx = assemble_daily_context(db_path_str)
    except Exception as _ctx_exc:
        _log.warning("morning-brief: context assembly failed: %s", _ctx_exc, exc_info=False)
        return None

    if not ctx.get("context"):
        _log.warning("morning-brief: assembled context is empty (no news/papers in DB?)")
        return None

    api_key = _get_api_key()
    if not api_key:
        _log.warning("morning-brief: no API key available")
        return None

    # Build period description
    name = _user_name()
    if period == "weekly":
        period_desc = "the past week"
    elif period == "catchup":
        period_desc = f"the last {days_since_last} days" if days_since_last <= 7 else f"the last {days_since_last // 7} week{'s' if days_since_last >= 14 else ''}"
    elif days_since_last <= 1:
        period_desc = "today"
    elif days_since_last <= 7:
        period_desc = f"the last {days_since_last} days"
    else:
        period_desc = f"the last {days_since_last // 7} week{'s' if days_since_last >= 14 else ''}"

    field_str = research_field or "public health and epidemiology"
    interests_str = ", ".join(interests[:8]) if interests else "global health, infectious diseases, epidemiology, public health surveillance, health systems"
    topics_str = ", ".join(news_topics[:6]) if news_topics else "WHO surveillance, global health emergencies, disease control, AI in research"

    system_preamble = _brief_system_prompt(
        period=period,
        name=name,
        field=field_str,
        interests=interests_str,
        topics=topics_str,
        period_desc=period_desc,
        gap_label=gap_label,
    )

    # Route to the right model: daily → Haiku, weekly/catchup → Sonnet
    _model_aliases = {
        "daily": "brief",
        "weekly": "brief_weekly",
        "catchup": "brief_catchup",
    }
    api_model = model_for(_model_aliases.get(period, "brief"))
    max_tok = 800 if period == "daily" else 1200

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
                "model": api_model,
                "max_tokens": max_tok,
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
                        f"{ctx['context'][:6000]}"
                    ),
                }],
            },
            timeout=60.0,
        )
        if resp.status_code == 200:
            _payload = resp.json()
            narrative = _payload["content"][0]["text"].strip()

            # Split off the model's self-reported coverage footer and record it.
            # Self-reporting rather than inference: the model may reasonably lead
            # with the second-ranked thread, and guessing from the ranking would
            # then put the WRONG thread on cooldown — reintroducing the exact
            # repetition bug one level up. The footer is stripped before display.
            _coverage: list[dict] = []
            try:
                from metis_mcp.tools.news_threads import parse_coverage_footer
                narrative, _coverage = parse_coverage_footer(narrative)
                if not _coverage:
                    _log.warning("morning-brief: no coverage footer in %s brief — "
                                 "nothing goes on cooldown, tomorrow may repeat", period)
            except Exception as _cov_exc:
                _log.warning("morning-brief: coverage parse failed: %s", _cov_exc)

            # Record REAL token usage so the dashboard monitor reflects actual spend
            # (Keystone B6.3). Background call → session_id="" (feeds totals, not
            # per-session "who did what"). Cached-input tokens count as input.
            try:
                from db import record_token_usage
                _u = _payload.get("usage", {}) or {}
                record_token_usage(
                    "metis", api_model,
                    (_u.get("input_tokens", 0) or 0) + (_u.get("cache_read_input_tokens", 0) or 0),
                    _u.get("output_tokens", 0),
                    task_summary=f"Morning brief ({period_desc})",
                )
            except Exception:
                pass

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
                        "title": clip(r["title"] or "", 80),
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

            # Record thread coverage against this brief's key. Keyed on
            # insight_key so the cooldown join can ask "was the brief that led
            # with this thread ever marked read?" — the whole mechanism rests on
            # that link, so it is written immediately after the brief is stored.
            if _coverage:
                try:
                    from metis_mcp.tools.news_threads import record_coverage
                    conn5 = _sqlite3.connect(db_path_str)
                    conn5.row_factory = _sqlite3.Row
                    n = record_coverage(conn5, insight_key, period, _coverage)
                    conn5.close()
                    _log.info("morning-brief: recorded %d thread(s) for %s (%s)",
                              n, insight_key, period)
                except Exception as _rec_exc:
                    _log.warning("morning-brief: coverage record failed: %s", _rec_exc)
            return narrative
        else:
            _log.warning("morning-brief: API returned status %s: %s",
                         resp.status_code, resp.text[:300] if hasattr(resp, 'text') else "")
    except Exception as _api_exc:
        _log.warning("morning-brief: API call failed: %s", _api_exc, exc_info=True)
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


def _load_brief_coverage(db_path_str: str, insight_key: str, period: str) -> dict:
    """Story-thread coverage for the brief on screen.

    Returns {led, held, escalated} — the threads this brief led with (which go
    quiet once it is marked read), the threads currently held back because they
    were already delivered, and any that broke their silence because something
    changed. Surfacing this is what makes the read button's effect legible: with
    read as the only cooldown trigger, "why did Ebola disappear?" and "why is it
    still here?" both need an answer visible on the page.
    """
    import sqlite3 as _sqlite3
    out: dict = {"led": [], "held": [], "escalated": []}
    if not db_path_str:
        return out
    try:
        _src = str(Path(__file__).parent.parent.parent / "mcp-server" / "src")
        if _src not in sys.path:
            sys.path.insert(0, _src)
        from metis_mcp.tools import news_threads as _nt

        conn = _sqlite3.connect(db_path_str)
        conn.row_factory = _sqlite3.Row
        _nt.ensure_tables(conn)

        # What this brief actually led with / mentioned.
        led_rows = conn.execute(
            "SELECT m.thread_id, m.role, COALESCE(t.label, m.thread_id) AS label "
            "FROM news_thread_mentions m "
            "LEFT JOIN news_threads t ON t.thread_id = m.thread_id "
            "WHERE m.insight_key = ? AND m.role = 'lead'",
            (insight_key,),
        ).fetchall()
        out["led"] = [{"label": r["label"], "days": None} for r in led_rows]

        # What is being held back right now, and what broke through.
        since = (datetime.datetime.now() - datetime.timedelta(days=3)).isoformat()
        for t in _nt.thread_window(conn, since):
            if t["blocked_from_lead"]:
                out["held"].append({
                    "label": t["label"],
                    "days": t["days_since_read_lead"] or t["days_since_read_mention"],
                })
            elif t["material"] and t["read_leads"]:
                out["escalated"].append({"label": t["label"], "days": None})
        conn.close()
    except Exception as _exc:
        _log.debug("morning-brief: coverage panel unavailable: %s", _exc)
    out["held"] = out["held"][:6]
    out["escalated"] = out["escalated"][:3]
    return out


def _get_db_path() -> str:
    db = os.environ.get("METIS_DB", "")
    if not db:
        try:
            from db import get_db_path
            db = str(get_db_path())
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
    if period not in ("daily", "weekly", "catchup"):
        period = "daily"

    # Compute gap label for catch-up button
    db_path = _get_db_path()
    last_gen = _last_brief_generated_at(db_path) if db_path else None
    gap_days = 0
    gap_label = ""
    if last_gen:
        gap_days = max(0, (datetime.datetime.now() - last_gen).days)
        if gap_days >= 14:
            gap_label = f"{gap_days // 7} WEEKS"
        elif gap_days >= 7:
            gap_label = "1 WEEK"
        elif gap_days >= 2:
            gap_label = f"{gap_days} DAYS"

    ai_brief = None
    brief_date_label = None
    pending = False
    if period in ("weekly", "catchup"):
        try:
            ai_brief = _get_or_generate_brief(period=period)
        except Exception:
            pass
    else:
        # Non-blocking daily brief: serve from cache instantly so the Today page
        # opens with no wait. If today's brief isn't written yet, generate it on a
        # background thread and tell the template to show a "brewing…" card that
        # polls until it's ready — the dashboard never blocks on a Claude API call.
        try:
            ai_brief = _get_cached_brief("daily")
        except Exception:
            ai_brief = None
        if (not ai_brief and _get_brief_mode() != "manual"
                and os.environ.get("METIS_DEMO") != "1"):
            # Kick generation in the background, but no more than once every ~90s,
            # so a transient failure self-heals on the next poll without hammering
            # the API. The card shows "brewing" while there's no cached brief.
            _since = _time.monotonic() - _brief_last_attempt.get("daily", 0)
            if "daily" not in _brief_gen_inflight and _since > 90:
                _kick_brief_generation("daily")
            pending = True

    # Surface errors: missing API key or a failed generation attempt
    brief_error = ""
    if pending and not _get_api_key() and _get_brief_mode() != "manual":
        brief_error = "no-api-key"  # sentinel — template shows setup guidance
        pending = False  # stop the polling spinner — it won't resolve without a key
    elif _brief_last_error.get(period):
        brief_error = _brief_last_error[period]

    # Not waiting (manual mode, or generation gave up) and still nothing cached:
    # fall back to the most recent brief from any date for continuity.
    if not ai_brief and not pending and period == "daily":
        try:
            import sqlite3 as _sqlite
            db_path = _get_db_path()
            if db_path:
                _conn = _sqlite.connect(db_path)
                _conn.row_factory = _sqlite.Row
                _last = _conn.execute(
                    "SELECT insight_date, content FROM daily_insights "
                    "WHERE model IN ('claude-haiku-brief','desktop-brief') AND content IS NOT NULL "
                    "ORDER BY insight_date DESC LIMIT 1"
                ).fetchone()
                _conn.close()
                if _last and _last["content"]:
                    ai_brief = _last["content"]
                    brief_date_label = _last["insight_date"]
        except Exception:
            pass

    sources: list[dict] = []
    coverage: dict = {}
    if ai_brief and not brief_date_label:
        db_path = _get_db_path()
        if db_path:
            sources = _load_brief_sources(db_path)
            _suffix = {"weekly": "-weekly", "catchup": "-catchup"}.get(period, "")
            coverage = _load_brief_coverage(
                db_path, datetime.date.today().isoformat() + _suffix, period)

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
                        "title": clip(r["title"] or "", 100),
                        "domain": r.get("domain") or "",
                        "url": r.get("source_url") or "",
                    })
        except Exception:
            pass

    _bid, _bdate, _bread = _latest_brief_meta()
    return templates.TemplateResponse(
        request,
        "partials/today_morning_brief.html",
        {
            "brief": ai_brief,
            "pending": pending,
            "brief_date_label": brief_date_label,
            "brief_error": brief_error,
            "sources": sources,
            "coverage": coverage,
            "fallback_headlines": fallback_headlines,
            "open_threads": open_threads,
            "time_of_day": time_of_day,
            "brief_mode": _get_brief_mode(),
            "period": period,
            "brief_id": _bid,
            "brief_date": _bdate,
            "brief_read": _bread,
            "gap_label": gap_label,
        },
    )


@router.get("/api/partial/today/threads", response_class=HTMLResponse)
async def today_threads(request: Request):
    """Active threads — the 3 warmest ideas/drafts/questions, as editorial cards.
    Reference: TodaySurface > Active threads in the Metis design system."""
    rows = db_query(
        "SELECT idea_id, text, idea_type, tags, domain, created_at FROM ideas "
        "WHERE tags NOT LIKE '%archived%' ORDER BY created_at DESC LIMIT 3"
    ) or []
    threads = []
    for r in rows:
        tags = (r.get("tags") or "").lower()
        itype = (r.get("idea_type") or "").lower()
        if "question" in tags or "question" in itype:
            kind, kicker = "question", "QUESTION · LEFT FOR METIS"
        elif "draft" in tags or itype in ("draft", "article"):
            kind, kicker = "draft", "DRAFT · TEACH"
        else:
            kind, kicker = "thinking", "THINKING · ACTIVE"
        threads.append({
            "title": (r.get("text") or "").strip()[:90],
            "kind": kind,
            "kicker": kicker,
            "domain": (r.get("domain") or "").upper(),
            "age": _age_label(r.get("created_at") or ""),
        })
    return templates.TemplateResponse(
        request, "partials/today_threads.html", {"threads": threads}
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
    if period not in ("daily", "weekly", "catchup"):
        period = "daily"

    # Compute gap label
    db_path = _get_db_path()
    last_gen = _last_brief_generated_at(db_path) if db_path else None
    gap_label = ""
    if last_gen:
        gap_days = max(0, (datetime.datetime.now() - last_gen).days)
        if gap_days >= 14:
            gap_label = f"{gap_days // 7} WEEKS"
        elif gap_days >= 7:
            gap_label = "1 WEEK"
        elif gap_days >= 2:
            gap_label = f"{gap_days} DAYS"

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
    coverage: dict = {}
    if ai_brief:
        db_path = _get_db_path()
        if db_path:
            sources = _load_brief_sources(db_path)
            _suffix = {"weekly": "-weekly", "catchup": "-catchup"}.get(period, "")
            coverage = _load_brief_coverage(
                db_path, datetime.date.today().isoformat() + _suffix, period)

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
                        "title": clip(r["title"] or "", 100),
                        "domain": r.get("domain") or "",
                        "url": r.get("source_url") or "",
                    })
        except Exception:
            pass

    _bid, _bdate, _bread = _latest_brief_meta()
    return templates.TemplateResponse(
        request,
        "partials/today_morning_brief.html",
        {
            "brief": ai_brief,
            "brief_date_label": None,
            "brief_error": "",
            "sources": sources,
            "coverage": coverage,
            "fallback_headlines": fallback_headlines,
            "open_threads": open_threads,
            "time_of_day": time_of_day,
            "brief_mode": _get_brief_mode(),
            "period": period,
            "brief_id": _bid,
            "brief_date": _bdate,
            "brief_read": _bread,
            "gap_label": gap_label,
        },
    )


def _focus_item_from_task(row) -> dict:
    """Normalize a task row into a unified focus card dict."""
    status = row.get("status") or "open"
    # A task's status IS a state — true now, false later — so it earns a pill,
    # and the colour follows the urgency ladder in styles.css rather than a
    # hand-picked var(). "OPEN" is the modal value across the whole board, so
    # it takes .is-quiet: the most common state must be the quietest one, or
    # the loud treatments stop carrying information.
    if status == "blocked":
        badge, badge_class = "BLOCKED", "stat is-warn"
    elif row.get("starred"):
        badge, badge_class = "STARRED", "stat is-info"
    elif status == "in_progress":
        badge, badge_class = "IN PROGRESS", "stat is-info"
    else:
        badge, badge_class = "OPEN", "stat is-quiet"
    return {
        "item_type": "task",
        "item_id": str(row.get("task_id") or ""),
        "title": (row.get("title") or "Untitled task")[:90],
        "subtitle": row.get("project_title") or row.get("project_id") or "",
        "badge": badge,
        "badge_class": badge_class,
    }


def _focus_item_from_idea(row) -> dict:
    """Normalize an idea row into a unified focus card dict."""
    tags = (row.get("tags") or "").lower()
    itype = (row.get("idea_type") or "").lower()
    # An idea's TYPE is a category, not a state: an idea captured as a question
    # is still a question next week. Categories get .tag — no pill, no colour —
    # which is what stops the Today grid reading as six equally urgent alarms.
    if "question" in tags or "question" in itype:
        badge, badge_class = "question", "tag"
    elif "draft" in tags or itype in ("draft", "article"):
        badge, badge_class = "draft", "tag"
    else:
        badge, badge_class = "idea", "tag"
    return {
        "item_type": "idea",
        "item_id": str(row.get("idea_id") or ""),
        "title": (row.get("text") or "").strip()[:90],
        "subtitle": (row.get("domain") or "").upper(),
        "badge": badge,
        "badge_class": badge_class,
    }


@router.get("/api/partial/today/focus", response_class=HTMLResponse)
async def today_focus(request: Request):
    """Merged focus section — dismissable cards from 4 pools in priority order."""
    _ensure_focus_dismissed_table()
    today_str = datetime.date.today().isoformat()

    # Load today's dismissed items
    dismissed: set[tuple[str, str]] = set()
    try:
        rows = db_query(
            "SELECT item_type, item_id FROM focus_dismissed WHERE dismissed_date = ?",
            (today_str,),
        ) or []
        for r in rows:
            dismissed.add((r["item_type"], r["item_id"]))
    except Exception:
        pass

    items: list[dict] = []
    seen_ids: set[str] = set()

    def _add(item: dict):
        key = (item["item_type"], item["item_id"])
        if key in dismissed or item["item_id"] in seen_ids or len(items) >= 6:
            return
        seen_ids.add(item["item_id"])
        items.append(item)

    # Pool 1: Starred tasks
    try:
        for r in db_query(
            "SELECT t.task_id, t.title, t.status, t.starred, t.project_id, "
            "p.title AS project_title "
            "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
            "WHERE t.starred = 1 AND t.status NOT IN ('done','completed','cancelled','deleted') "
            "ORDER BY CASE t.status WHEN 'in_progress' THEN 1 WHEN 'blocked' THEN 2 ELSE 3 END, "
            "t.created_at DESC LIMIT 6"
        ) or []:
            _add(_focus_item_from_task(r))
    except Exception:
        pass

    # Pool 2: Blocked tasks
    try:
        for r in db_query(
            "SELECT t.task_id, t.title, t.status, t.starred, t.project_id, "
            "p.title AS project_title "
            "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
            "WHERE t.status = 'blocked' "
            "ORDER BY t.created_at ASC LIMIT 6"
        ) or []:
            _add(_focus_item_from_task(r))
    except Exception:
        pass

    # Pool 3: Active ideas/drafts/questions
    try:
        for r in db_query(
            "SELECT idea_id, text, idea_type, tags, domain, created_at FROM ideas "
            "WHERE tags NOT LIKE '%archived%' "
            "ORDER BY created_at DESC LIMIT 6"
        ) or []:
            _add(_focus_item_from_idea(r))
    except Exception:
        pass

    # Pool 4: Open/in-progress tasks (fills remaining)
    try:
        for r in db_query(
            "SELECT t.task_id, t.title, t.status, t.starred, t.project_id, "
            "p.title AS project_title "
            "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
            "WHERE t.status IN ('open','in_progress') AND t.starred = 0 "
            "ORDER BY CASE t.status WHEN 'in_progress' THEN 1 ELSE 2 END, "
            "t.created_at ASC LIMIT 10"
        ) or []:
            _add(_focus_item_from_task(r))
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_focus.html",
        {"items": items},
    )


@router.post("/api/today/focus/dismiss", response_class=HTMLResponse)
async def focus_dismiss(request: Request):
    """Dismiss a focus item for today, then re-render the section."""
    _ensure_focus_dismissed_table()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    item_type = payload.get("item_type", "")
    item_id = payload.get("item_id", "")
    if item_type and item_id:
        now = datetime.datetime.now().isoformat()
        today_str = datetime.date.today().isoformat()
        try:
            db_execute(
                "INSERT INTO focus_dismissed (item_type, item_id, dismissed_date, dismissed_at) "
                "VALUES (?, ?, ?, ?)",
                (item_type, item_id, today_str, now),
            )
        except Exception:
            pass
    return await today_focus_with_memory(request)


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
                "summary": clip(r.get("summary") or "", 100),
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
            "  AND p.project_id NOT IN ('personal') "
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
            idea = {"text": clip(r.get("text") or "", 500),
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
            "SELECT id, title, authors, year, source, tags, abstract, doi, url, item_type, created_at, "
            "COALESCE(is_read, 0) as is_read "
            "FROM literature_metadata WHERE created_at >= ? ORDER BY created_at DESC LIMIT 4",
            (since_month,),
        ) or []
        if not rows:
            rows = db_query(
                "SELECT id, title, authors, year, source, tags, abstract, doi, url, item_type, created_at, "
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
                "item_type": r.get("item_type") or "",
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
                    "content": clip(r.get("content") or "", 200),
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


@router.get("/api/partial/today/day-at-hand", response_class=HTMLResponse)
async def today_day_at_hand(request: Request):
    """Block 4 — 'The day at hand' (ordered tasks, no invented clock times) +
    'Today's one intention' (the single top priority). Design: TodaySurface."""
    rows = []
    try:
        rows = db_query(
            "SELECT t.task_id, t.title, t.status, t.starred, t.project_id, "
            "p.title AS project_title "
            "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
            "WHERE t.status IN ('open','in_progress','blocked') "
            "ORDER BY t.starred DESC, (t.status='blocked') DESC, "
            "(t.status='in_progress') DESC, t.created_at ASC LIMIT 3"
        ) or []
    except Exception:
        pass

    def _label(r):
        if r.get("status") == "blocked":
            return "BLOCKED", "var(--m-alert)"
        if r.get("starred"):
            return "STARRED", "var(--m-ochre)"
        if r.get("status") == "in_progress":
            return "IN PROGRESS", "var(--m-accent)"
        return "OPEN", "var(--m-muted)"

    items = []
    for r in rows:
        label, color = _label(r)
        items.append({
            "title": (r.get("title") or "Untitled task")[:90],
            "project": r.get("project_title") or "",
            "project_id": r.get("project_id") or "",
            "label": label,
            "color": color,
        })
    intention = items[0] if items else None
    return templates.TemplateResponse(
        request,
        "partials/today_day_at_hand.html",
        {"items": items, "intention": intention},
    )


@router.get("/api/partial/today/assistant-notes", response_class=HTMLResponse)
async def today_assistant_notes(request: Request):
    """Block 5 — 'From the assistant': 2 margin notes from real signals
    (latest daily insight + a portfolio observation). Design: TodaySurface."""
    notes = []
    try:
        ins = db_query(
            "SELECT insight_date, content FROM daily_insights "
            "WHERE content IS NOT NULL ORDER BY insight_date DESC LIMIT 1"
        ) or []
        if ins and ins[0].get("content"):
            notes.append({
                "title": "From your recent days.",
                "body": (ins[0]["content"] or "").strip()[:260],
                "model": "haiku",
                "meta": ins[0].get("insight_date") or "",
            })
    except Exception:
        pass
    try:
        n_ideas = db_scalar(
            "SELECT COUNT(*) FROM ideas WHERE tags NOT LIKE '%archived%'"
        ) or 0
        n_lib = db_scalar("SELECT COUNT(*) FROM library_inventory") or 0
        oldest = db_query(
            "SELECT created_at FROM ideas WHERE tags NOT LIKE '%archived%' "
            "ORDER BY created_at ASC LIMIT 1"
        ) or []
        age = _age_label(oldest[0]["created_at"]) if oldest else ""
        body = f"{n_ideas} open thread{'s' if n_ideas != 1 else ''}, and {n_lib} sources on the shelves."
        if age:
            body += f" The oldest thread has been waiting {age}."
        notes.append({
            "title": "Where things stand.",
            "body": body,
            "model": "sonnet",
            "meta": "",
        })
    except Exception:
        pass
    return templates.TemplateResponse(
        request,
        "partials/today_assistant_notes.html",
        {"notes": notes},
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
            from db import get_db_path
            db_p = get_db_path()
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
                    title = clip(data.get("title") or "", 500)
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
                             doi,clip(data.get("abstractNote","") or "", 2000),
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
            # ── PII output rail — scan the brief before it leaves the machine ──
            # FAIL CLOSED. This used to swallow any failure and "send as-is", so a
            # broken import meant patient-adjacent text went to the API unmasked —
            # the precise thing the rail exists to prevent. If we cannot prove the
            # text is clean, we do not send it.
            import logging as _logging

            _safety_log = _logging.getLogger("metis.safety")
            try:
                from metis_mcp.tools.anonymization import mask_pii

                _brief_to_send, _pii_found = mask_pii(brief_content[:6000])
                if _pii_found:
                    _safety_log.warning(
                        "output rail: masked %s in brief before API call", _pii_found
                    )
            except Exception as _exc:
                _safety_log.error(
                    "output rail UNAVAILABLE (%s: %s) — refusing to send the brief "
                    "to the API. Nothing left the machine.",
                    type(_exc).__name__, _exc,
                )
                raise RuntimeError(
                    "PII output rail unavailable — brief not sent (fail-closed)."
                ) from _exc

            prompt = (
                "You are summarising a researcher's session handoff brief for their "
                "long-term memory. Read the brief below and return a JSON object with "
                "exactly three keys:\n"
                '  "summary": one-or-two-sentence prose summary of what happened (≤ 250 chars)\n'
                '  "topics":  a JSON array of 3–6 short topic strings (project names, themes)\n'
                '  "decisions": a JSON array of 3–8 short decision strings (≤ 120 chars each, '
                'concrete next steps or outcomes)\n\n'
                "Respond with ONLY the JSON. No commentary.\n\n"
                "BRIEF:\n" + _brief_to_send
            )
            msg = client.messages.create(
                model=model_for("brief"),
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            try:  # record real token usage for the monitor (Keystone B6.3)
                from db import record_token_usage
                _u = getattr(msg, "usage", None)
                if _u is not None:
                    record_token_usage("memory-curator", model_for("brief"),
                                       getattr(_u, "input_tokens", 0), getattr(_u, "output_tokens", 0),
                                       task_summary="Session consolidation summary")
            except Exception:
                pass
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
    # `research_milestones` has zero rows and NO writer anywhere in the codebase —
    # a feature that was given a table and a reader and never built (one of the
    # fossil tables in Keystone Appendix D). Kept as a read rather than deleted,
    # because the table and this query are the only remaining description of what
    # was intended; if milestones are ever built, this is where they surface. It
    # costs one empty query and is documented rather than mysterious.
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


# ── Morning-brief read-state + history ────────────────────────────────────────
# A brief stays the "current" one until a new scan generates a fresh one — so the
# same brief can show two days running. Read-tracking lets the user mark one read
# (it then collapses + shows "read"), and the history endpoint exposes every past
# brief, so nothing is lost between scans.
def _ensure_brief_read_col():
    import sqlite3
    try:
        con = sqlite3.connect(_get_db_path())
        con.execute("ALTER TABLE daily_insights ADD COLUMN read_at TEXT")
        con.commit(); con.close()
    except Exception:
        pass  # column already exists (additive migration)


_FOCUS_DISMISSED_DDL = """
CREATE TABLE IF NOT EXISTS focus_dismissed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    dismissed_date TEXT NOT NULL,
    dismissed_at TEXT NOT NULL
)
"""


def _ensure_focus_dismissed_table():
    try:
        db_execute(_FOCUS_DISMISSED_DDL)
    except Exception:
        pass


def _latest_brief_meta():
    """(id, insight_date, read_bool) of the most recent brief, or (None, None, False)."""
    import sqlite3
    _ensure_brief_read_col()
    try:
        con = sqlite3.connect(_get_db_path()); con.row_factory = sqlite3.Row
        r = con.execute(
            "SELECT id, insight_date, read_at FROM daily_insights "
            "WHERE content IS NOT NULL AND model IN ('claude-haiku-brief','desktop-brief') "
            "ORDER BY insight_date DESC LIMIT 1").fetchone()
        con.close()
        if r:
            return r["id"], r["insight_date"], bool(r["read_at"])
    except Exception:
        pass
    return None, None, False


@router.post("/api/today/morning-brief/read", response_class=HTMLResponse)
async def mark_brief_read(request: Request):
    import sqlite3
    _ensure_brief_read_col()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    bid = payload.get("id")
    now = datetime.datetime.now().isoformat()
    try:
        con = sqlite3.connect(_get_db_path())
        if bid:
            con.execute("UPDATE daily_insights SET read_at=? WHERE id=?", (now, bid))
        else:
            con.execute(
                "UPDATE daily_insights SET read_at=? WHERE id=("
                "SELECT id FROM daily_insights WHERE content IS NOT NULL "
                "ORDER BY insight_date DESC LIMIT 1)", (now,))
        con.commit(); con.close()
    except Exception:
        pass
    return await today_morning_brief(request)  # re-render the brief, now marked read


@router.get("/api/partial/today/morning-brief/history", response_class=HTMLResponse)
async def morning_brief_history(request: Request):
    import sqlite3
    _ensure_brief_read_col()
    briefs = []
    try:
        con = sqlite3.connect(_get_db_path()); con.row_factory = sqlite3.Row
        briefs = con.execute(
            "SELECT id, insight_date, read_at, content FROM daily_insights "
            "WHERE content IS NOT NULL AND model IN ('claude-haiku-brief','desktop-brief') "
            "ORDER BY insight_date DESC LIMIT 30").fetchall()
        con.close()
    except Exception:
        pass
    return templates.TemplateResponse(
        request, "partials/today_brief_history.html", {"briefs": briefs})


# ---------------------------------------------------------------------------
# Board boxes — Outbreaks · Events · Funding on the Today surface
# ---------------------------------------------------------------------------

_VALID_BOARDS = {"outbreaks", "events", "funding"}


def _ensure_board_table():
    """Create today_board_items if it doesn't exist yet (safe, idempotent)."""
    try:
        db_execute(
            "CREATE TABLE IF NOT EXISTS today_board_items ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  board TEXT NOT NULL,"
            "  title TEXT NOT NULL,"
            "  url TEXT DEFAULT '',"
            "  description TEXT DEFAULT '',"
            "  source TEXT DEFAULT '',"
            "  starred INTEGER DEFAULT 0,"
            "  dismissed INTEGER DEFAULT 0,"
            "  auto_added INTEGER DEFAULT 1,"
            "  start_date TEXT DEFAULT '',"
            "  end_date TEXT DEFAULT '',"
            "  seen_at TEXT DEFAULT '',"
            "  created_at TEXT NOT NULL DEFAULT (datetime('now')),"
            "  updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
            ")"
        )
    except Exception:
        pass
    # Migration for databases created before seen_at existed. Guarded by a
    # PRAGMA rather than a try/except on the ALTER, because this runs on every
    # board render and a swallowed exception per request hides real failures.
    try:
        cols = {r["name"] for r in (db_query("PRAGMA table_info(today_board_items)") or [])}
        if "seen_at" not in cols:
            db_execute("ALTER TABLE today_board_items ADD COLUMN seen_at TEXT DEFAULT ''")
            _log.info("today_board_items: added seen_at column")
    except Exception as exc:
        _log.warning("today_board_items: seen_at migration skipped: %s", exc)


# ── A PIN IS A SUBJECT YOU FOLLOW, NOT A ROW YOU KEPT ────────────────────────
# Asked for 2026-09-04: "i want to follow a certain outbreak like Ebola, I pin
# it and so every day it can show the newest report of it, but so there will be
# multiple pinned outbreaks that I have pinned from the new ones that you have
# shown me. I can also chose their order and see which one I put on top."
#
# Starring already existed and already sorted to the top, so two things were
# missing: an order the reader sets, and the newest report. `freshness.collapse`
# folds a running story when several instalments are ON THE BOARD, but a pinned
# subject has to watch the news stream — the board holds two rows and the stream
# holds four thousand.
_FOLLOW_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "報", "disease", "virus",
    "outbreak", "cases", "case", "report", "situation", "update", "republic",
    "democratic", "national", "annual", "meeting", "call", "calls", "proposals",
    "award", "development", "programme", "program", "research", "health",
    "global", "international", "conference", "congress", "grant", "grants",
}


def _follow_terms(item: dict) -> list[str]:
    """What to watch for. Explicit terms win; otherwise the title's own nouns.

    Deriving from the title is the common case: a pin is made on an item already
    on screen, and the expectation is that it follows itself. Generic words are
    dropped because "outbreak" or "annual meeting" would match the whole stream
    and the pin would report noise as news.
    """
    raw = str(item.get("follow_terms") or "").strip()
    if raw:
        return [w.strip().lower() for w in raw.split(",") if w.strip()]
    title = str(item.get("title") or "")
    words = re.findall(r"[A-Za-z][A-Za-z'-]{3,}", title)
    keep = [w for w in words if w.lower() not in _FOLLOW_STOP]
    # Proper nouns first — a place or a pathogen identifies a story; a common
    # word does not. Two terms, ANDed, is tight enough to stay on subject.
    proper = [w for w in keep if w[:1].isupper()]
    return [w.lower() for w in (proper or keep)[:2]]


def _latest_report(item: dict) -> dict | None:
    """The newest brief matching this pinned subject, or None."""
    terms = _follow_terms(item)
    if not terms:
        return None
    where = " AND ".join(["LOWER(title || ' ' || COALESCE(summary,'')) LIKE ?"] * len(terms))
    rows = db_query(
        "SELECT brief_id, title, brief_date, source_url, domain "
        f"FROM news_briefs WHERE {where} "
        "ORDER BY brief_date DESC, created_at DESC LIMIT 1",
        tuple(f"%{t}%" for t in terms), default=[]) or []
    if not rows:
        return None
    r = dict(rows[0])
    r["_terms"] = terms
    # How many reports the subject has produced, so "newest" carries its own
    # denominator rather than implying it is the only one.
    r["_n"] = db_scalar(
        f"SELECT COUNT(*) FROM news_briefs WHERE {where}",
        tuple(f"%{t}%" for t in terms), default=0) or 0
    return r


@router.post("/api/today/board/{board}/item/{item_id}/pin-move")
async def board_pin_move(board: str, item_id: int, request: Request,
                         direction: str = Form("up")):
    """Move a pin up or down. Order is the reader's, so it is stored, not derived."""
    _ensure_board_table()
    pins = db_query(
        "SELECT id, COALESCE(pin_order, 0) AS po FROM today_board_items "
        "WHERE board=? AND dismissed=0 AND COALESCE(pin_order,0)>0 "
        "ORDER BY CASE WHEN COALESCE(pin_order,0)=0 THEN 1 ELSE 0 END, "
        "         COALESCE(pin_order,0), created_at DESC",
        (board,), default=[]) or []
    ids = [r["id"] for r in pins]
    if item_id not in ids:
        return await today_board_box(request, board)
    i = ids.index(item_id)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
    # Rewrite the whole sequence from 1: a swap of two stored values leaves
    # every unset pin at 0 and the order half-derived, which is how "which one
    # I put on top" stops being answerable.
    for pos, pid in enumerate(ids, start=1):
        db_execute("UPDATE today_board_items SET pin_order=?, updated_at=datetime('now') "
                   "WHERE id=?", (pos, pid))
    return await today_board_box(request, board)


def _board_context(board: str, show_all: bool = False) -> dict:
    """Build template context for a single board box."""
    _ensure_board_table()
    # Ten, not five. Every row is one line now, so the box holds twice the
    # board in the same height — "always just 1 line so there is space for
    # more" was the whole point of the change. Asked for 2026-09-05.
    limit = 50 if show_all else 10

    # Fetch WIDE, then fold. Collapsing after a LIMIT 5 would show five rows
    # that turn out to be two stories — which is precisely what the researcher was seeing
    # with Ebola: WHO publishes a weekly situation report, so three of the five
    # slots were instalments of one running story.
    raw = db_query(
        "SELECT id, title, url, source, starred, auto_added, created_at, "
        "       seen_at, start_date, end_date, description, "
        "       COALESCE(pin_order, 0) AS pin_order, "
        "       COALESCE(follow_terms, '') AS follow_terms "
        "FROM today_board_items "
        "WHERE board=? AND dismissed=0 "
        "ORDER BY starred DESC, created_at DESC LIMIT 120",
        (board,),
    ) or []
    try:
        import freshness
        folded = freshness.collapse([dict(r) for r in raw])
    except Exception as _exc:
        _log.warning("board %s: freshness unavailable: %s", board, _exc)
        folded = [dict(r) for r in raw]
    # THREE TIERS, because pin and follow are now separate verbs. A pin is a
    # position the reader chose, so it outranks everything and keeps its own
    # order. Following is about content, not placement, so a followed row sits
    # above the unread pile but does not jump the pins. Everything else keeps
    # the recency order the query returned.
    folded.sort(key=lambda r: (
        0 if (r.get("pin_order") or 0) else (1 if r.get("starred") else 2),
        r.get("pin_order") or 0,
        ))
    # A pin follows its subject: attach the newest matching report from the
    # news stream. Only for pins — doing it for every row would run a LIKE
    # query per row on a board that shows fifty.
    for it in folded:
        it["_latest"] = _latest_report(it) if it.get("starred") else None
    pinned_ids = [r["id"] for r in folded if (r.get("pin_order") or 0)]
    for r in folded:
        r["_pinned"] = bool(r.get("pin_order") or 0)
        if r["_pinned"]:
            r["_pin_pos"] = pinned_ids.index(r["id"]) + 1
            r["_pin_of"] = len(pinned_ids)
    # UNSEEN, not RECENT, is what earns the highlight (2026-09-02).
    # freshness.band() sets _fresh from created_at age, which meant the tint
    # cleared after seven days whether it had been read or not — and because the
    # default view is the five newest rows, all five were always tinted. A mark
    # on 100% of rows carries no information. The age band is kept for the
    # SHADE (this morning reads differently from last Tuesday) but an item that
    # has been seen goes quiet regardless of how new it is.
    for it in folded:
        it["_unseen"] = not str(it.get("seen_at") or "").strip()
        if not it["_unseen"]:
            it["_fresh"] = ""
        # The date a reader cares about is the event's, not the scrape's.
        it["_when"] = str(it.get("start_date") or "").strip()
    n_unseen = sum(1 for it in folded if it["_unseen"])

    items = folded[:limit]
    n_folded = len(raw) - len(folded)
    total = db_scalar(
        "SELECT COUNT(*) FROM today_board_items WHERE board=? AND dismissed=0",
        (board,),
        default=0,
    ) or 0
    return {
        "board": board,
        "items": items,
        "total": total,
        "n_unseen": n_unseen,
        "shown": len(folded),
        "n_folded": n_folded,
        "show_all": show_all,
    }


@router.get("/api/partial/today/board/{board}", response_class=HTMLResponse)
async def today_board_box(request: Request, board: str):
    """Render one board box (outbreaks | events | funding)."""
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    show_all = request.query_params.get("all") == "1"
    ctx = _board_context(board, show_all)
    return templates.TemplateResponse(
        request, "partials/today_board_box.html", ctx,
    )


@router.post("/api/today/board/{board}/add", response_class=HTMLResponse)
async def board_add_item(request: Request, board: str):
    """Manually add an item to a board box."""
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    _ensure_board_table()
    form = await request.form()
    title = (form.get("title") or "").strip()
    url = (form.get("url") or "").strip()
    if title:
        now = datetime.datetime.now().isoformat()
        db_execute(
            "INSERT INTO today_board_items (board, title, url, source, auto_added, created_at, updated_at) "
            "VALUES (?, ?, ?, 'manual', 0, ?, ?)",
            (board, title[:300], url, now, now),
        )
    ctx = _board_context(board)
    return templates.TemplateResponse(
        request, "partials/today_board_box.html", ctx,
    )


@router.delete("/api/today/board/{board}/item/{item_id}", response_class=HTMLResponse)
async def board_dismiss_item(request: Request, board: str, item_id: int):
    """Soft-delete (dismiss) a board item."""
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    _ensure_board_table()
    db_execute(
        "UPDATE today_board_items SET dismissed=1, updated_at=? WHERE id=? AND board=?",
        (datetime.datetime.now().isoformat(), item_id, board),
    )
    ctx = _board_context(board, request.query_params.get("all") == "1")
    return templates.TemplateResponse(
        request, "partials/today_board_box.html", ctx,
    )


@router.post("/api/today/board/{board}/item/{item_id}/pin", response_class=HTMLResponse)
async def board_pin_item(request: Request, board: str, item_id: int):
    """Pin an item to the top of its board, or unpin it.

    PIN AND FOLLOW ARE DIFFERENT VERBS and used to be one control. Pin is about
    POSITION — this one stays at the top, in the order I chose. Follow is about
    CONTENT — bring me its newest report. Welding them meant you could not keep
    a congress date in view without also asking for a news lookup it will never
    match, and could not follow a subject without it jumping the queue.

    A new pin goes to the END of the sequence rather than the front: the reader
    put the existing order there on purpose.
    """
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    _ensure_board_table()
    cur = db_scalar(
        "SELECT COALESCE(pin_order,0) FROM today_board_items WHERE id=? AND board=?",
        (item_id, board), default=0) or 0
    if cur:
        db_execute(
            "UPDATE today_board_items SET pin_order=0, updated_at=? WHERE id=? AND board=?",
            (datetime.datetime.now().isoformat(), item_id, board))
        # Close the gap, so positions stay 1..n and "which one is on top" keeps
        # meaning what it says.
        rest = db_query(
            "SELECT id FROM today_board_items WHERE board=? AND dismissed=0 "
            "AND COALESCE(pin_order,0)>0 ORDER BY pin_order",
            (board,), default=[]) or []
        for pos, r in enumerate(rest, start=1):
            db_execute("UPDATE today_board_items SET pin_order=? WHERE id=?", (pos, r["id"]))
    else:
        nxt = (db_scalar(
            "SELECT MAX(COALESCE(pin_order,0)) FROM today_board_items "
            "WHERE board=? AND dismissed=0", (board,), default=0) or 0) + 1
        db_execute(
            "UPDATE today_board_items SET pin_order=?, updated_at=? WHERE id=? AND board=?",
            (nxt, datetime.datetime.now().isoformat(), item_id, board))
    ctx = _board_context(board, request.query_params.get("all") == "1")
    return templates.TemplateResponse(request, "partials/today_board_box.html", ctx)


@router.post("/api/today/board/{board}/item/{item_id}/star", response_class=HTMLResponse)
async def board_star_item(request: Request, board: str, item_id: int):
    """Toggle the star on a board item."""
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    _ensure_board_table()
    db_execute(
        "UPDATE today_board_items SET starred = CASE WHEN starred=1 THEN 0 ELSE 1 END, "
        "updated_at=? WHERE id=? AND board=?",
        (datetime.datetime.now().isoformat(), item_id, board),
    )
    ctx = _board_context(board, request.query_params.get("all") == "1")
    return templates.TemplateResponse(
        request, "partials/today_board_box.html", ctx,
    )


@router.post("/api/today/board/{board}/item/{item_id}/seen", response_class=HTMLResponse)
async def board_seen_item(request: Request, board: str, item_id: int):
    """Toggle 'I have seen this' on one board item.

    The gesture the boards were missing. Before this the only way to make an
    item stop looking new was to DELETE it — a destructive action offered as the
    only acknowledgement, behind a confirm dialog, one row at a time. Marking
    seen keeps the item and its link; dismissing it is still there for things
    that should go away.

    A toggle rather than a one-way flag, so an accidental click is recoverable
    without touching the database.
    """
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    _ensure_board_table()
    now = datetime.datetime.now().isoformat()
    db_execute(
        "UPDATE today_board_items "
        "SET seen_at = CASE WHEN COALESCE(seen_at,'') = '' THEN ? ELSE '' END, "
        "    updated_at = ? "
        "WHERE id=? AND board=?",
        (now, now, item_id, board),
    )
    ctx = _board_context(board, request.query_params.get("all") == "1")
    return templates.TemplateResponse(
        request, "partials/today_board_box.html", ctx,
    )


@router.post("/api/today/board/{board}/seen-all", response_class=HTMLResponse)
async def board_seen_all(request: Request, board: str):
    """Mark every visible item on one board as seen.

    The news rail has had this for weeks; the boards never got it, so clearing
    a morning's arrivals meant one confirm dialog per row. Marks only rows that
    are actually live (not dismissed), and does not touch already-seen rows, so
    the timestamps stay honest about when each was first acknowledged.
    """
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    _ensure_board_table()
    now = datetime.datetime.now().isoformat()
    db_execute(
        "UPDATE today_board_items SET seen_at=?, updated_at=? "
        "WHERE board=? AND dismissed=0 AND COALESCE(seen_at,'') = ''",
        (now, now, board),
    )
    ctx = _board_context(board, request.query_params.get("all") == "1")
    return templates.TemplateResponse(
        request, "partials/today_board_box.html", ctx,
    )


# ---------------------------------------------------------------------------
# Board refresh via Claude web search — Events (congresses) & Funding (calls).
# These boards have no RSS feeds (congresses/funders publish on web pages, not
# feeds), so we ask Claude to web-search for current, real items relevant to the
# user's topics. Triggered by the box's Refresh button and a monthly cron job.
# ---------------------------------------------------------------------------

_SEARCHABLE_BOARDS = {"outbreaks", "events", "funding"}


def _extract_json_array(text: str) -> list | None:
    """Pull the JSON array of items out of a model reply. None if there isn't one.

    The old version was one greedy regex, `\\[\\s*\\{.*\\}\\s*\\]` with DOTALL, and
    greedy is exactly wrong here. A web-search reply is a CONCATENATION of text
    blocks — usually a sentence of preamble, the array, then a closing sentence or
    citation list. The moment a second bracketed structure appears anywhere in that
    text, the match runs from the first `[{` to the LAST `}]` and swallows the prose
    in between, producing a string that cannot parse. Both boards failed that way
    (`events:0(bad-json) funding:0(bad-json)`, 2026-08-24) — the model had answered
    correctly and the parser threw the answer away.

    So: find every plausible array by walking brackets (respecting strings and
    escapes, so a `]` inside a title cannot end it early), parse each, and take the
    first one that actually yields a list of objects. Longest first, because the
    real payload is the substantial one, not a stray `[]` in a sentence.
    """
    import json as _json

    # A fenced block, if present, is the most reliable signal — take it first.
    fenced = re.findall(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)

    candidates: list[str] = list(fenced)
    for start in (i for i, ch in enumerate(text) if ch == "["):
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:i + 1])
                    break

    for cand in sorted(set(candidates), key=len, reverse=True):
        try:
            parsed = _json.loads(cand)
        except Exception:
            continue
        if isinstance(parsed, list) and any(isinstance(x, dict) for x in parsed):
            return parsed
    return None


def _board_search_prompt(board: str, topics: str) -> str:
    who = topics or "tropical medicine, neglected tropical diseases, global health, epidemiology"
    if board == "outbreaks":
        what = ("current, active disease outbreaks and public-health emergencies "
                "(each with the location and a recent date) — prioritise neglected "
                "tropical diseases, sleeping sickness / HAT, malaria, and other "
                "epidemic-prone diseases, especially in West and Central Africa")
    elif board == "events":
        what = ("upcoming scientific congresses, conferences, symposia and short courses "
                "(each with a future or recently-announced date) in tropical medicine, "
                "neglected tropical diseases, global health and epidemiology")
    else:
        what = ("open or upcoming research funding calls, grant opportunities and fellowships "
                "(each with an application deadline) relevant to tropical medicine, neglected "
                "tropical diseases, global health and epidemiology")
    if board == "outbreaks":
        sources = ("Prefer authoritative sources — WHO Disease Outbreak News, WHO AFRO, "
                   "Africa CDC, ProMED, ReliefWeb and national ministries of health.")
    else:
        sources = ("Prefer authoritative sources — society/congress sites "
                   "(ASTMH, FESTMIH/ECTMIH), funder portals (EDCTP / Global Health EDCTP3, "
                   "Horizon Europe, Wellcome, NIH, WHO/TDR) and the Institute of Tropical "
                   "Medicine Antwerp (ITM).")
    return (
        f"Use web search to find current, real {what}, especially anything relevant to a "
        f"researcher working on: {who}. {sources} "
        "Return ONLY a JSON array (no other prose) of up to 8 items, each object exactly: "
        '{"title": string, "url": string, "date": string, "description": string}. '
        "url must be the direct official page and start with http; date = the event date, "
        'application deadline or report date if known else ""; description = one short '
        "factual sentence. Only include items you actually found with a real working URL. "
        "End with the JSON array."
    )


def _refresh_board_via_search(board: str) -> tuple[int, str]:
    """Repopulate a board from a live Claude web search. Returns (count, error).

    Replaces only the previously web-searched rows (source='web-search'); curated
    and manually-added items are left untouched.
    """
    if board not in _SEARCHABLE_BOARDS:
        return 0, "not-searchable"
    api_key = _get_api_key()
    if not api_key:
        return 0, "no-api-key"

    topics = ""
    try:
        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            prefs = Path(rc) / "system" / "config" / "user-preferences.json"
            if prefs.exists():
                p = _json.loads(prefs.read_text(encoding="utf-8"))
                topics = ", ".join((p.get("interests") or [])[:10]) or (p.get("role") or "")
    except Exception:
        pass

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
                "max_tokens": 2500,
                # Keep searches few: web-search tool results are injected as INPUT
                # tokens, and a low API tier (10k input tokens/min) 429s quickly.
                "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}],
                "messages": [{"role": "user", "content": _board_search_prompt(board, topics)}],
            },
            timeout=90.0,
        )
        if resp.status_code != 200:
            return 0, f"api-{resp.status_code}"
        blocks = resp.json().get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except Exception as e:
        return 0, f"{type(e).__name__}"

    raw = _extract_json_array(text)
    if raw is None:
        # Log what actually came back. The previous version returned a bare
        # "bad-json" and discarded the reply, so a recurring parse failure could
        # only ever be guessed at. 600 chars is enough to see the shape.
        _log.warning("[board_refresh] %s: could not parse an item array from the "
                     "model reply (%d chars). Head: %s",
                     board, len(text), text[:600].replace("\n", " "))
        return 0, "bad-json" if "[" in text else "no-items"

    clean: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for it in raw if isinstance(raw, list) else []:
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or "").strip()
        url = (it.get("url") or "").strip()
        if not title or not url.lower().startswith("http") or url in seen:
            continue
        seen.add(url)
        date = (it.get("date") or "").strip()
        desc = (it.get("description") or "").strip()
        if date:
            desc = (desc + f" · {date}").strip(" ·")
        clean.append((title[:300], url[:500], desc[:400]))

    if not clean:
        return 0, "no-valid-items"

    _ensure_board_table()
    now = datetime.datetime.now().isoformat()
    # Refresh = replace the previous search results, keep curated/manual items.
    db_execute("DELETE FROM today_board_items WHERE board=? AND source='web-search'", (board,))
    added = 0
    for title, url, desc in clean:
        # Don't duplicate a curated/manual item that already points at this URL.
        if db_query("SELECT 1 FROM today_board_items WHERE board=? AND url=? LIMIT 1", (board, url)):
            continue
        db_execute(
            "INSERT INTO today_board_items (board, title, url, description, source, auto_added, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'web-search', 1, ?, ?)",
            (board, title, url, desc, now, now),
        )
        added += 1
    return added, ""


@router.post("/api/today/board/{board}/refresh", response_class=HTMLResponse)
async def board_refresh(request: Request, board: str):
    """Refresh a searchable board (Events / Funding) via a live web search."""
    if board not in _VALID_BOARDS:
        return HTMLResponse("")
    if board in _SEARCHABLE_BOARDS:
        # Best-effort: on error the box simply re-renders with its current items.
        # Run the blocking web-search call off the event loop.
        import asyncio as _asyncio
        await _asyncio.to_thread(_refresh_board_via_search, board)
    ctx = _board_context(board)
    return templates.TemplateResponse(
        request, "partials/today_board_box.html", ctx,
    )


# ===========================================================================
# Memory-aware dashboard features (A–E)
# ===========================================================================

def _memory_depth(title_or_topic: str) -> dict:
    """Count memories related to a topic across layers. Returns {total, level, layers}."""
    like = f"%{title_or_topic}%"
    counts = {}
    for table, col in [
        ("episodic_memory", "content"),
        ("semantic_memory", "definition"),
        ("procedural_memory", "steps"),
        ("session_summaries", "summary"),
    ]:
        try:
            n = db_scalar(
                f"SELECT COUNT(*) FROM {table} WHERE {col} LIKE ?", (like,)
            ) or 0
            counts[table.split("_")[0]] = n
        except Exception:
            counts[table.split("_")[0]] = 0
    total = sum(counts.values())
    level = "deep" if total >= 10 else "moderate" if total >= 3 else "shallow"
    return {"total": total, "level": level, "layers": counts}


# ── A: Session Thread Strip ─────────────────────────────────────────────

@router.get("/api/partial/today/session-thread", response_class=HTMLResponse)
async def today_session_thread(request: Request):
    """Thread view — groups recent sessions by topic/project and shows the narrative arc."""
    import json as _json

    threads: dict[str, dict] = {}  # key → {sessions, topic, first_date, last_date, ...}

    try:
        rows = db_query(
            "SELECT session_id, summary, key_topics, decisions, created_at "
            "FROM session_summaries "
            "WHERE (archived IS NULL OR archived = 0) "
            "ORDER BY created_at DESC LIMIT 60"
        ) or []

        for r in rows:
            raw = (r.get("summary") or "").strip()
            if ("Handoff brief:" in raw and "Stop reason:" in raw) or len(raw) < 30:
                continue
            topics = []
            try:
                topics = [t for t in _json.loads(r.get("key_topics") or "[]") if t][:6]
            except Exception:
                pass
            decisions = []
            try:
                decisions = [d for d in _json.loads(r.get("decisions") or "[]") if d]
            except Exception:
                pass

            # Group by primary topic (first topic, or 'general')
            thread_key = topics[0].lower().strip() if topics else "general"
            created = r.get("created_at") or ""
            date = created[:10]

            if thread_key not in threads:
                threads[thread_key] = {
                    "topic": topics[0] if topics else "General",
                    "sessions": [],
                    "first_date": date,
                    "last_date": date,
                    "total_decisions": 0,
                    "all_topics": set(),
                }
            t = threads[thread_key]
            t["sessions"].append({
                "date": date,
                "summary": _clean_handoff_text(raw)[:180],
                "decisions": decisions[:3],
                "topics": topics,
            })
            t["last_date"] = max(t["last_date"], date)
            t["first_date"] = min(t["first_date"], date)
            t["total_decisions"] += len(decisions)
            t["all_topics"].update(topics)
    except Exception:
        pass

    # Sort threads by most recent activity, take top 5
    sorted_threads = sorted(
        threads.values(),
        key=lambda t: t["last_date"],
        reverse=True,
    )[:5]

    # Add memory depth for each thread
    for t in sorted_threads:
        t["all_topics"] = list(t["all_topics"])[:8]
        t["memory"] = _memory_depth(t["topic"])
        t["session_count"] = len(t["sessions"])
        # Calculate span
        try:
            d1 = datetime.datetime.fromisoformat(t["first_date"])
            d2 = datetime.datetime.fromisoformat(t["last_date"])
            t["span_days"] = max(1, (d2 - d1).days)
        except Exception:
            t["span_days"] = 0

    # Also get the "last session" for the traditional view at top
    last_session = None
    last_did = []
    if sorted_threads and sorted_threads[0]["sessions"]:
        s = sorted_threads[0]["sessions"][0]
        last_session = s

    try:
        last_did = db_query(
            "SELECT agent_slug, task_summary FROM agent_runs "
            "WHERE COALESCE(task_summary,'') != '' "
            "ORDER BY created_at DESC LIMIT 4"
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

    return templates.TemplateResponse(
        request,
        "partials/today_session_thread.html",
        {
            "threads": sorted_threads,
            "last_session": last_session,
            "last_did": last_did,
            "total_sessions": total_sessions,
        },
    )


# ── B: Memory Pulse heatmap ─────────────────────────────────────────────

@router.get("/api/partial/today/memory-pulse", response_class=HTMLResponse)
async def today_memory_pulse(request: Request):
    """8-week heatmap of memory creation intensity, broken down by topic."""
    now = datetime.datetime.now()
    weeks: list[dict] = []

    for w in range(7, -1, -1):
        week_start = now - datetime.timedelta(weeks=w, days=now.weekday())
        week_end = week_start + datetime.timedelta(days=6)
        ws = week_start.strftime("%Y-%m-%d")
        we = week_end.strftime("%Y-%m-%d")
        week_label = week_start.strftime("W%U")

        total = 0
        by_type: dict[str, int] = {}

        for table, col, type_col in [
            ("episodic_memory", "created_at", "event_type"),
            ("semantic_memory", "created_at", None),
            ("session_summaries", "created_at", None),
        ]:
            try:
                if type_col:
                    rows = db_query(
                        f"SELECT {type_col} as t, COUNT(*) as n FROM {table} "
                        f"WHERE {col} >= ? AND {col} < ? "
                        f"GROUP BY {type_col}",
                        (ws, we + "T23:59:59"),
                    ) or []
                    for r in rows:
                        typ = r["t"] or "other"
                        by_type[typ] = by_type.get(typ, 0) + r["n"]
                        total += r["n"]
                else:
                    n = db_scalar(
                        f"SELECT COUNT(*) FROM {table} WHERE {col} >= ? AND {col} < ?",
                        (ws, we + "T23:59:59"),
                    ) or 0
                    by_type[table.split("_")[0]] = n
                    total += n
            except Exception:
                pass

        # Intensity level for heatmap color
        intensity = 0 if total == 0 else 1 if total <= 3 else 2 if total <= 8 else 3 if total <= 20 else 4

        weeks.append({
            "label": week_label,
            "date_range": f"{ws} – {we}",
            "total": total,
            "intensity": intensity,
            "by_type": by_type,
        })

    # Overall stats
    total_all = sum(w["total"] for w in weeks)
    peak_week = max(weeks, key=lambda w: w["total"]) if weeks else None
    trend = ""
    if len(weeks) >= 4:
        first_half = sum(w["total"] for w in weeks[:4])
        second_half = sum(w["total"] for w in weeks[4:])
        if second_half > first_half * 1.2:
            trend = "rising"
        elif second_half < first_half * 0.8:
            trend = "cooling"
        else:
            trend = "steady"

    return templates.TemplateResponse(
        request,
        "partials/today_memory_pulse.html",
        {"weeks": weeks, "total": total_all, "peak": peak_week, "trend": trend},
    )


# ── C: Focus items with memory depth ─────────────────────────────────────

@router.get("/api/partial/today/focus-memory", response_class=HTMLResponse)
async def today_focus_with_memory(request: Request, bare: int = 0):
    """Same as today_focus but enriches each item with memory depth + connections."""
    # Re-use the existing focus logic
    _ensure_focus_dismissed_table()
    today_str = datetime.date.today().isoformat()

    dismissed: set[tuple[str, str]] = set()
    try:
        rows = db_query(
            "SELECT item_type, item_id FROM focus_dismissed WHERE dismissed_date = ?",
            (today_str,),
        ) or []
        for r in rows:
            dismissed.add((r["item_type"], r["item_id"]))
    except Exception:
        pass

    items: list[dict] = []
    seen_ids: set[str] = set()

    def _add(item: dict):
        key = (item["item_type"], item["item_id"])
        if key in dismissed or item["item_id"] in seen_ids or len(items) >= 6:
            return
        seen_ids.add(item["item_id"])
        # Enrich with memory depth
        item["memory"] = _memory_depth(item["title"])
        items.append(item)

    # DATED TASKS ARE NOT HERE ANY MORE. They were, and the due strip mounted
    # beside this one on Today showed them too, so "Draft Angola risk-mapping
    # parameters" appeared twice on the same screen — once as a focus card and
    # once as an overdue row. Two panels answering one question is what the
    # merge was supposed to remove, not create.
    #
    # The division now: anything with a DATE belongs to the due strip, anything
    # you STARRED belongs here. Both sit under one heading on Today, so they
    # read as one answer to "what needs me today".
    starred_only = True

    # ── CHOSEN, then SUGGESTED — and the difference is the whole point ──────
    #
    # This list used to draw from five pools: deadlines, starred, blocked,
    # ideas, and finally ANY open task. That last pool is why Today could never
    # be finished — clear an item and the next of 53 open tasks slides in, so
    # the surface refills exactly as fast as you empty it and "done" is a state
    # it cannot express.
    #
    # Reported 2026-08-29: "Expand on the Today surface and that it should be
    # finisheable."
    #
    # So only two pools now reach the cards: things with a DEADLINE (added
    # above) and things you STARRED. Both are commitments — one made by the
    # calendar, one made by you. Everything else becomes a count on one quiet
    # line at the foot, which keeps it available and stops it demanding.
    try:
        for r in db_query(
            "SELECT t.task_id, t.title, t.status, t.starred, t.project_id, "
            "p.title AS project_title "
            "FROM tasks t LEFT JOIN projects p ON t.project_id = p.project_id "
            "WHERE t.starred = 1 AND t.status NOT IN ('done','completed','cancelled','deleted') "
            "ORDER BY CASE t.status WHEN 'in_progress' THEN 1 WHEN 'blocked' THEN 2 ELSE 3 END, "
            "t.created_at DESC LIMIT 6"
        ) or []:
            _add(_focus_item_from_task(r))
    except Exception:
        pass

    # What is NOT on the cards, counted rather than shown.
    def _count(sql: str) -> int:
        try:
            return int(db_scalar(sql, default=0) or 0)
        except Exception:
            return 0

    suggested = {
        "blocked": _count(
            "SELECT COUNT(*) FROM tasks WHERE status = 'blocked'"),
        "open": _count(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('open','in_progress') "
            "AND COALESCE(starred,0) = 0"),
        "ideas": _count(
            "SELECT COUNT(*) FROM ideas WHERE COALESCE(tags,'') NOT LIKE '%archived%'"),
        "reviews": _count(
            "SELECT COUNT(*) FROM spaced_repetition WHERE next_review <= date('now')"),
    }

    # Cleared TODAY, so the surface can say "3 done" rather than only "0 left".
    done_today = _count(
        "SELECT COUNT(*) FROM tasks WHERE status IN ('done','completed') "
        "AND date(COALESCE(updated_at, created_at)) = date('now')")

    return templates.TemplateResponse(
        request,
        "partials/today_focus_memory.html",
        {"items": items, "suggested": suggested, "done_today": done_today,
         "bare": bool(bare)},
    )


# ── D: Connection Bridges for Morning Brief ──────────────────────────────

@router.get("/api/partial/today/brief-bridges", response_class=HTMLResponse)
async def today_brief_bridges(request: Request):
    """Find memory connections to the current morning brief content."""
    bridges: list[dict] = []

    # Get today's brief content
    brief_text = ""
    try:
        today_str = datetime.date.today().isoformat()
        row = db_query(
            "SELECT content FROM daily_insights "
            "WHERE insight_date = ? ORDER BY id DESC LIMIT 1",
            (today_str,),
        )
        if row:
            brief_text = row[0].get("content", "")[:1000]
    except Exception:
        pass

    if not brief_text:
        return HTMLResponse("")

    # Extract key phrases (simple approach: sentences with research-relevant terms)
    import re as _re
    sentences = _re.split(r'[.!?\n]+', brief_text)
    research_terms = [
        "hat", "sleeping sickness", "surveillance", "elimination",
        "dhis2", "diagnostic", "multilevel", "spatial", "ntd",
        "burden", "outbreak", "resistance", "who",
    ]

    key_phrases = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15:
            continue
        lower = s.lower()
        hit = next((t for t in research_terms if t in lower), None)
        if hit:
            # Keep the TERM that made this sentence relevant, alongside the
            # sentence itself. The term is what memory can actually be searched
            # on; the sentence is only what the reader is shown.
            key_phrases.append((hit, s[:120]))
        if len(key_phrases) >= 3:
            break

    # For each key phrase, search episodic+semantic memory for connections.
    #
    # Search on the TERM, not the sentence. This previously built its query as
    # `%{phrase[:40]}%` — the first 40 characters of a whole sentence, matched as a
    # literal substring — so it looked for things like
    #   %The humanitarian crisis in Central African%
    # in episodic memory. Nothing there contains verbatim sentences from today's
    # brief, so the panel could never produce a single bridge, however much memory
    # existed. It identified the term that made the sentence relevant and then threw
    # it away. (Found 2026-08-12: "surveillance" alone matches 21 episodic rows.)
    for term, phrase in key_phrases:
        like = f"%{term}%"
        # Check if we have related episodic memories
        try:
            matches = db_query(
                "SELECT content, created_at, event_type FROM episodic_memory "
                "WHERE content LIKE ? AND (archived IS NULL OR archived = 0) "
                "ORDER BY created_at DESC LIMIT 1",
                (like,),
            ) or []
            if matches:
                m = matches[0]
                bridges.append({
                    "brief_phrase": phrase[:80],
                    "memory_type": "episodic",
                    "memory_preview": clip(m["content"] or "", 120),
                    "memory_date": (m["created_at"] or "")[:10],
                    "event_type": m["event_type"] or "note",
                })
        except Exception:
            pass

        # Also check semantic memory
        try:
            matches = db_query(
                "SELECT concept, definition, created_at FROM semantic_memory "
                "WHERE concept LIKE ? OR definition LIKE ? "
                "ORDER BY updated_at DESC LIMIT 1",
                (like, like),
            ) or []
            if matches:
                m = matches[0]
                bridges.append({
                    "brief_phrase": phrase[:80],
                    "memory_type": "semantic",
                    "memory_preview": f"{m['concept']}: {(m['definition'] or '')[:100]}",
                    "memory_date": (m["created_at"] or "")[:10],
                    "event_type": "concept",
                })
        except Exception:
            pass

    # Deduplicate and limit
    seen = set()
    unique = []
    for b in bridges:
        key = b["memory_preview"][:60]
        if key not in seen:
            seen.add(key)
            unique.append(b)
        if len(unique) >= 3:
            break

    return templates.TemplateResponse(
        request,
        "partials/today_brief_bridges.html",
        {"bridges": unique},
    )


# ── E: Memory Landscape ─────────────────────────────────────────────────

# ── WHAT METIS KNOWS, SMALL ──────────────────────────────────────────────────
# The memory landscape drew twenty TOPICS as sized bubbles in 30 KB of markup
# and most of a screen. Asked for a much smaller thing on 2026-09-04: how many
# memories exist in each KIND, and a click through to the full surface.
#
# The counts come from `memory_health.memory_layer_counts()` so the strip and
# the full cards on the system surface cannot disagree about what is in there.
@router.get("/api/partial/today/recent-projects", response_class=HTMLResponse)
async def today_recent_projects(request: Request):
    """The last three projects that were actually worked on.

    Replaces the thread view that stood here, which grouped `session_summaries`
    by their first key topic. That answered "what subjects have come up lately",
    which is a different question from "what have I been working on" — and it
    could not name a project, because a session summary carries topics and no
    project. Reported 2026-09-05: a fortnight of work in Claude Desktop on one
    project was invisible here while the panel filled with topic threads.

    `projects.last_session_at` is the column that already knew. It is written
    whenever a session touches a project, from Claude Desktop as readily as from
    the CLI, and it had the missing project sitting second in the list the whole
    time. No new bookkeeping — just asking the table that was already keeping
    the answer.
    """
    from main import templates
    rows = db_query(
        "SELECT project_id, title, next_step, last_session_at, accent_color, status "
        "FROM projects "
        "WHERE COALESCE(status,'') NOT IN ('archived','done') "
        "  AND COALESCE(last_session_at,'') <> '' "
        "ORDER BY last_session_at DESC LIMIT 3",
        default=[]) or []

    today = datetime.date.today()
    items = []
    for r in rows:
        d = dict(r)
        stamp = str(d.get("last_session_at") or "")[:10]
        try:
            days = (today - datetime.date.fromisoformat(stamp)).days
        except Exception:
            days = None
        # Say it the way a person would. An ISO date makes the reader do the
        # subtraction, and the whole point of this strip is to be read at a
        # glance.
        if days is None:
            d["_when"] = ""
        elif days <= 0:
            d["_when"] = "today"
        elif days == 1:
            d["_when"] = "yesterday"
        elif days < 7:
            d["_when"] = f"{days} days ago"
        elif days < 14:
            d["_when"] = "last week"
        else:
            d["_when"] = f"{days // 7} weeks ago"
        items.append(d)

    return templates.TemplateResponse(
        request, "partials/today_recent_projects.html", {"items": items},
    )


@router.get("/api/partial/today/knows", response_class=HTMLResponse)
async def today_knows(request: Request):
    """One row per kind of memory, linking to the memory surface."""
    from main import templates
    try:
        from routers.memory_health import memory_layer_counts
        layers = memory_layer_counts()
    except Exception:
        layers = []
    # THE LIBRARY IS NOT A KIND OF MEMORY, and putting it in the same bar chart
    # said otherwise. It holds ~47,000 indexed passages of other people's
    # writing; the seven memory kinds hold tens to a thousand each of what this
    # system worked out. Charted together — even scaled to the largest — the
    # library was the only visible bar and every real memory kind was a
    # hairline. That is a chart that hides its own subject.
    #
    # So it is reported beside the strip as context, and the bars compare the
    # seven kinds against each other, which is the comparison worth drawing.
    library = next((l for l in layers if l["table"] == "pdf_chunks"), None)
    kinds = [l for l in layers if l["table"] != "pdf_chunks"]
    total = sum(l["count"] for l in kinds)
    top = max([l["count"] for l in kinds] or [0]) or 1
    for l in kinds:
        l["pct"] = round(l["count"] / top * 100, 1)
    return templates.TemplateResponse(
        request, "partials/today_knows.html",
        {"layers": kinds, "total": total, "library": library})


@router.get("/api/partial/today/memory-landscape", response_class=HTMLResponse)
async def today_memory_landscape(request: Request):
    """Topic map — circles sized by memory density, colored by recency, with relation edges."""
    import json as _json

    topics: dict[str, dict] = {}

    # Gather topic stats from episodic memory metadata
    try:
        rows = db_query(
            "SELECT metadata, created_at, event_type FROM episodic_memory "
            "WHERE (archived IS NULL OR archived = 0) "
            "ORDER BY created_at DESC LIMIT 500"
        ) or []
        for r in rows:
            try:
                meta = _json.loads(r.get("metadata") or "{}")
                tag_list = meta.get("topics") or []
                if isinstance(tag_list, str):
                    tag_list = [t.strip() for t in tag_list.split(",") if t.strip()]
            except Exception:
                tag_list = []

            created = r.get("created_at") or ""
            for tag in tag_list:
                tag_lower = tag.lower().strip()
                if not tag_lower or len(tag_lower) < 2:
                    continue
                if tag_lower not in topics:
                    topics[tag_lower] = {
                        "name": tag,
                        "count": 0,
                        "last_seen": created[:10],
                        "types": {},
                    }
                topics[tag_lower]["count"] += 1
                topics[tag_lower]["last_seen"] = max(
                    topics[tag_lower]["last_seen"], created[:10]
                )
                et = r.get("event_type") or "other"
                topics[tag_lower]["types"][et] = topics[tag_lower]["types"].get(et, 0) + 1
    except Exception:
        pass

    # Also pull from session key_topics
    try:
        rows = db_query(
            "SELECT key_topics, created_at FROM session_summaries "
            "WHERE (archived IS NULL OR archived = 0) "
            "ORDER BY created_at DESC LIMIT 200"
        ) or []
        for r in rows:
            try:
                tag_list = _json.loads(r.get("key_topics") or "[]")
            except Exception:
                tag_list = []
            created = r.get("created_at") or ""
            for tag in tag_list:
                if not tag or not isinstance(tag, str):
                    continue
                tag_lower = tag.lower().strip()
                if tag_lower not in topics:
                    topics[tag_lower] = {
                        "name": tag,
                        "count": 0,
                        "last_seen": created[:10],
                        "types": {},
                    }
                topics[tag_lower]["count"] += 1
                topics[tag_lower]["last_seen"] = max(
                    topics[tag_lower]["last_seen"], created[:10]
                )
    except Exception:
        pass

    # Get memory relations for edges
    edges: list[dict] = []
    try:
        rows = db_query(
            "SELECT source_layer, source_id, target_layer, target_id, relation "
            "FROM memory_relations LIMIT 100"
        ) or []
        for r in rows:
            edges.append({
                "source": f"{r['source_layer']}:{r['source_id']}",
                "target": f"{r['target_layer']}:{r['target_id']}",
                "relation": r["relation"],
            })
    except Exception:
        pass

    # Sort topics by count, take top 20
    sorted_topics = sorted(topics.values(), key=lambda t: t["count"], reverse=True)[:20]

    # Calculate recency (days since last seen)
    now = datetime.date.today()
    for t in sorted_topics:
        try:
            last = datetime.date.fromisoformat(t["last_seen"])
            t["age_days"] = (now - last).days
            t["recency"] = "fresh" if t["age_days"] <= 7 else "recent" if t["age_days"] <= 30 else "aging" if t["age_days"] <= 90 else "stale"
        except Exception:
            t["age_days"] = 999
            t["recency"] = "stale"

    # Get project connections
    projects: list[dict] = []
    try:
        rows = db_query(
            "SELECT project_id, title, status FROM projects "
            "WHERE status NOT IN ('archived','removed') "
            "ORDER BY CASE status WHEN 'active' THEN 1 ELSE 2 END, title "
            "LIMIT 10"
        ) or []
        for r in rows:
            pid = r["project_id"]
            mem = _memory_depth(r["title"])
            projects.append({
                "id": pid,
                "title": r["title"],
                "status": r["status"],
                "memory": mem,
            })
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_memory_landscape.html",
        {
            "topics": sorted_topics,
            "edges": edges,
            "projects": projects,
            "topics_json": _json.dumps([
                {"name": t["name"], "count": t["count"], "recency": t["recency"],
                 "age_days": t["age_days"]}
                for t in sorted_topics
            ]),
        },
    )


# ── E: Resume Card — "Where we left off" ─────────────────────────────────

@router.get("/api/partial/today/resume-card", response_class=HTMLResponse)
async def today_resume_card(request: Request):
    """First-class card showing the most recent session with a Continue button."""
    import json as _json
    import urllib.parse as _up

    session = None
    agents: list[dict] = []
    time_label = ""
    total_sessions = 0

    try:
        rows = db_query(
            "SELECT session_id, summary, key_topics, decisions, created_at "
            "FROM session_summaries "
            "WHERE (archived IS NULL OR archived = 0) "
            "AND COALESCE(summary, '') != '' "
            "ORDER BY created_at DESC LIMIT 1"
        ) or []
        if rows:
            r = rows[0]
            raw = (r.get("summary") or "").strip()
            # Skip handoff-only entries
            if not ("Handoff brief:" in raw and "Stop reason:" in raw) and len(raw) >= 30:
                decisions = []
                try:
                    decisions = [d for d in _json.loads(r.get("decisions") or "[]") if d][:5]
                except Exception:
                    pass
                session = {
                    "summary": _clean_handoff_text(raw)[:400],
                    "decisions": decisions,
                    "created_at": r.get("created_at", ""),
                }
                time_label = _age_label(r.get("created_at", ""))
                if time_label:
                    time_label += " ago"
    except Exception:
        pass

    # Agent work from the last session
    try:
        agents = db_query(
            "SELECT agent_slug, task_summary FROM agent_runs "
            "WHERE COALESCE(task_summary,'') != '' "
            "ORDER BY created_at DESC LIMIT 4"
        ) or []
    except Exception:
        pass

    # Total sessions for the "All sessions" button
    try:
        total_sessions = db_scalar(
            "SELECT COUNT(DISTINCT DATE(created_at)) FROM session_summaries"
        ) or 0
    except Exception:
        pass

    # Build Claude Desktop deeplink
    deeplink = ""
    if session:
        context = f"Continue from where we left off: {session['summary'][:200]}"
        deeplink = "https://claude.ai/new?q=" + _up.quote(context, safe="")

    return templates.TemplateResponse(
        request,
        "partials/today_resume_card.html",
        {
            "session": session,
            "agents": agents,
            "time_label": time_label,
            "total_sessions": total_sessions,
            "deeplink": deeplink,
        },
    )


# ── F: Learning Nudge ────────────────────────────────────────────────────

@router.get("/api/partial/today/pick-focus", response_class=HTMLResponse)
async def today_pick_focus(request: Request):
    """Where you left off — folded, and every row can become today's focus.

    The resume card described yesterday in a paragraph you could not act on.
    This carries the same information plus the one thing that was missing: each
    project's top open task, and a button that stars it so it appears in
    today's focus. Reading about yesterday is only useful if it shortens the
    decision about today.
    """
    today_d = datetime.date.today()
    rows = db_query(
        "SELECT p.project_id AS id, p.title, p.next_step, p.last_session_at, "
        "  (SELECT t.task_id FROM tasks t WHERE t.project_id = p.project_id "
        "     AND t.status NOT IN ('done','completed','cancelled','deleted') "
        "     AND COALESCE(t.starred,0) = 0 ORDER BY t.created_at LIMIT 1) AS task_id, "
        "  (SELECT t.title FROM tasks t WHERE t.project_id = p.project_id "
        "     AND t.status NOT IN ('done','completed','cancelled','deleted') "
        "     AND COALESCE(t.starred,0) = 0 ORDER BY t.created_at LIMIT 1) AS task_title "
        "FROM projects p WHERE p.status = 'active' "
        "ORDER BY COALESCE(p.last_session_at, p.created_at) DESC LIMIT 5"
    ) or []
    for r in rows:
        r["quiet_days"] = None
        stamp = (r.get("last_session_at") or "")[:10]
        if stamp:
            try:
                r["quiet_days"] = (today_d - datetime.date.fromisoformat(stamp)).days
            except ValueError:
                pass

    last_summary, last_when = "", ""
    try:
        row = db_query(
            "SELECT summary, created_at FROM session_summaries "
            "ORDER BY created_at DESC LIMIT 1")
        if row:
            last_summary = clip(row[0].get("summary") or "", 260)
            last_when = _fmt_relative_time(row[0].get("created_at") or "")
    except Exception:
        pass

    return templates.TemplateResponse(
        request, "partials/today_pick_focus.html",
        {"projects": rows, "last_summary": last_summary, "last_when": last_when},
    )


# ── ONE BOX FOR "WHAT IS NEW IN MY FIELD" ────────────────────────────────────
# There were three, and two of them were the same data.
#
#   "What changed in your field yesterday"  news_threads     (0 new)
#   "New in your field"                     new_publications (306 new)
#   "Publication scan"                      new_publications (368) ← same table
#
# Asked on 2026-09-04: "what is the difference between 'New in the field' and
# 'what changed in your field yesterday', it should only be one of these and
# only on a weekly basis... Also integrate Publication scan in this. Its one
# advanced box where i see everything, well organized because Publication Scan
# takes up too much white space for what it does." Measured: the scan panel was
# 23,505 bytes of HTML against the other's 1,619.
#
# A WEEK OF THIS FIELD IS 1,232 UNJUDGED ITEMS (940 news · 292 papers, measured
# 2026-09-04). So this is a ranked digest, not a list — everything is reachable,
# but the box shows what a person can actually act on and says how much it is
# standing in front of.
#
# Both streams share ONE verdict mechanism, `reading_stack`, which already has
# exactly the verbs asked for: read · later (stack) · declined (not interested),
# for kinds 'news' and 'paper'. Nothing new was needed to record a decision.
FIELD_WEEK_DAYS = 7
# Five and four, not eight and six. Fourteen rows came to 1,039px — a full
# screen, which is the complaint this merge existed to answer. A digest earns
# its place by being scannable in one look and honest about what it is standing
# in front of; the counts in each group header do the second part.
FIELD_NEWS_SHOWN = 5
FIELD_PAPERS_SHOWN = 4


def _field_week_data(days: int = FIELD_WEEK_DAYS) -> dict:
    """The week's unjudged news and papers, ranked, plus the totals behind them."""
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()

    # `reading_stack` is the shared verdict table; a judged item leaves the box
    # whichever verb was used, so a decision never has to be made twice.
    #
    # THE COMMENT ABOVE WAS TRUE OF THE INTENT AND FALSE OF THE CODE. This listed
    # only ('read','declined'), so pressing Stack — the one verb that exists
    # because the researcher asked for it — filed the item and left it sitting in
    # the box, to be judged again tomorrow. A verdict that does not clear the row
    # reads as a button that did nothing.
    #
    # The set is now imported from the store that owns it rather than retyped
    # here, because this is the second queue to disagree with it and a literal
    # copied into a query is a copy that stops being updated.
    try:
        from metis_mcp.tools.stack import JUDGED as _JUDGED
    except Exception:
        _JUDGED = ("read", "declined", "dismissed", "later", "saved")
    _judged_sql = ",".join("'" + j.replace("'", "") + "'" for j in _JUDGED)
    NOT_JUDGED = ("NOT EXISTS (SELECT 1 FROM reading_stack s WHERE s.kind=? "
                  "AND s.item_id = CAST({id} AS TEXT) AND s.state IN (" + _judged_sql + "))")

    news = db_query(
        "SELECT b.brief_id AS id, b.title, b.summary, b.source_url, b.domain, "
        "       b.brief_date AS on_date, COALESCE(b.signal_strength,'medium') AS signal, "
        "       COALESCE(b.relevance, 0) AS rel, COALESCE(b.image_url,'') AS image_url "
        "FROM news_briefs b "
        "WHERE COALESCE(b.brief_date,'') >= ? AND COALESCE(b.seen_at,'') = '' "
        "  AND " + NOT_JUDGED.format(id="b.brief_id") + " "
        # Signal first, relevance second: a 'high' signal is a judgement about
        # the item, relevance only about its distance from a keyword.
        "ORDER BY CASE COALESCE(b.signal_strength,'medium') "
        "           WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "
        "         rel DESC, b.brief_date DESC LIMIT ?",
        (since, "news", FIELD_NEWS_SHOWN), default=[]) or []

    papers = db_query(
        "SELECT p.id, p.title, p.journal, p.doi, p.source_url, p.authors, "
        "       COALESCE(NULLIF(p.pub_iso,''), NULLIF(p.pub_date,''), p.discovered_at) AS on_date, "
        "       COALESCE(p.relevance, 0) AS rel, COALESCE(p.lane,'field') AS lane, "
        "       COALESCE(p.relevance_note,'') AS why "
        "FROM new_publications p "
        "WHERE COALESCE(p.read_at,'') = '' AND COALESCE(p.dismissed_at,'') = '' "
        "  AND COALESCE(NULLIF(p.pub_iso,''), NULLIF(p.pub_date,''), p.discovered_at) >= ? "
        "  AND " + NOT_JUDGED.format(id="p.id") + " "
        "ORDER BY CASE COALESCE(p.lane,'field') WHEN 'field' THEN 0 ELSE 1 END, "
        "         rel DESC, on_date DESC LIMIT ?",
        (since, "paper", FIELD_PAPERS_SHOWN), default=[]) or []

    n_news = db_scalar(
        "SELECT COUNT(*) FROM news_briefs b WHERE COALESCE(b.brief_date,'') >= ? "
        "AND COALESCE(b.seen_at,'') = '' AND " + NOT_JUDGED.format(id="b.brief_id"),
        (since, "news"), default=0) or 0
    n_papers = db_scalar(
        "SELECT COUNT(*) FROM new_publications p WHERE COALESCE(p.read_at,'') = '' "
        "AND COALESCE(p.dismissed_at,'') = '' "
        "AND COALESCE(NULLIF(p.pub_iso,''), NULLIF(p.pub_date,''), p.discovered_at) >= ? "
        "AND " + NOT_JUDGED.format(id="p.id"),
        (since, "paper"), default=0) or 0

    # Name the source on every news row. `_source_of` maps a host to its
    # masthead and is what the News surface cards already use; the digest was
    # printing the topic beat instead, so the two surfaces named the same item
    # differently.
    for it in news:
        it["source"] = _source_of(it.get("source_url") or "")

    return {
        "news": news, "papers": papers,
        "n_news": n_news, "n_papers": n_papers,
        "days": days, "since": since,
        # What the digest is standing in front of. Never a count without the
        # denominator it came from.
        "more_news": max(0, n_news - len(news)),
        "more_papers": max(0, n_papers - len(papers)),
    }


async def render_field_week(request: Request) -> str:
    from main import templates
    return templates.get_template("partials/today_field_week.html").render(
        request=request, **_field_week_data())


@router.get("/api/partial/today/field-week", response_class=HTMLResponse)
async def today_field_week(request: Request):
    """News and new papers for the week, in one ranked box."""
    return HTMLResponse(await render_field_week(request))


@router.get("/api/partial/today/whats-new", response_class=HTMLResponse)
async def today_whats_new(request: Request):
    """News and Library arrivals, side by side.

    Three lines each and no more. This answers "is there anything worth going
    to look at" — it is not a place to read from, and making it longer would
    turn Today back into the thing the reordering was meant to stop it being.
    """
    # UNSEEN, not merely RECENT. Reported 2026-09-01: "there are still a lot of
    # 'new' items, we would reset ... and start from zero today."
    #
    # These counts were `discovered_at >= date('now','-1 day')` — a rolling
    # 24-hour window that consults no read state at all. Marking everything read
    # therefore could not move them, and no reset ever would: the panel was
    # reporting what the SCANNER did, under a heading that promises what is left
    # for the READER. Twenty-four hours is still the window — "yesterday" is in
    # the heading — but a row inside it only counts while it is unseen.
    news = db_query(
        "SELECT t.label, COUNT(*) AS item_count FROM news_threads t "
        "JOIN news_thread_items ti ON ti.thread_id = t.thread_id "
        "JOIN news_briefs b ON b.brief_id = ti.brief_ref "
        "WHERE COALESCE(t.last_seen, t.first_seen) >= date('now','-1 day') "
        "AND b.seen_at IS NULL AND COALESCE(b.source_type,'news') != 'article' "
        "GROUP BY t.thread_id HAVING COUNT(*) > 1 "
        "ORDER BY item_count DESC LIMIT 3"
    ) or []
    # `doi` and `source_url` come along so each line can open the PAPER.
    # Every row here linked to `/knowledge` — the tab, not the item — so three
    # different papers were three links to the same page, which is the defect
    # that made the top-bar search results useless too. A glance panel may be
    # short; its links still have to go somewhere specific.
    papers = db_query(
        "SELECT title, journal, feed_name, doi, source_url FROM new_publications "
        "WHERE discovered_at >= date('now','-1 day') AND COALESCE(read_at,'') = '' "
        "ORDER BY COALESCE(relevance,0) DESC, discovered_at DESC LIMIT 3"
    ) or []
    for r in papers:
        doi = str(r.get("doi") or "").strip()
        r["link"] = (f"https://doi.org/{doi}" if doi
                     else str(r.get("source_url") or "").strip())
    news_new = db_scalar(
        "SELECT COUNT(DISTINCT t.thread_id) FROM news_threads t "
        "JOIN news_thread_items ti ON ti.thread_id = t.thread_id "
        "JOIN news_briefs b ON b.brief_id = ti.brief_ref "
        "WHERE COALESCE(t.last_seen, t.first_seen) >= date('now','-1 day') "
        "AND b.seen_at IS NULL AND COALESCE(b.source_type,'news') != 'article'",
        default=0) or 0
    lib_new = db_scalar(
        "SELECT COUNT(*) FROM new_publications "
        "WHERE discovered_at >= date('now','-1 day') AND COALESCE(read_at,'') = ''",
        default=0) or 0
    for r in papers:
        r["title"] = clip(r.get("title") or "", 88)
    return templates.TemplateResponse(
        request, "partials/today_whats_new.html",
        {"news": news, "papers": papers, "news_new": news_new, "lib_new": lib_new},
    )


@router.get("/api/partial/today/reading", response_class=HTMLResponse)
async def today_reading(request: Request):
    """The single reading suggestion for the start of the day.

    Returns an EMPTY body when nothing is flagged crucial, and that is
    deliberate — HTMX swaps the mount away and the surface shows no trace of a
    section that has nothing to say. An empty panel here would be worse than
    none: it would recreate, on Today, the empty Stack surface we just removed
    from the navbar.
    """
    rows = db_query(
        "SELECT kind, item_id, title, url, source FROM reading_stack "
        "WHERE COALESCE(crucial, 0) = 1 AND state != 'read' "
        "ORDER BY state_at DESC LIMIT 3"
    ) or []
    return templates.TemplateResponse(
        request,
        "partials/today_reading.html",
        {"items": rows[:2], "more": max(0, len(rows) - 2)},
    )


# ── G: Literature Discovery ──────────────────────────────────────────────

async def render_literature_discovery(request: Request) -> str:
    """The Today literature panel, as a string — see `render_news_rail`."""
    resp = await today_literature_discovery(request)
    return resp.body.decode("utf-8")


@router.get("/api/partial/today/literature-discovery", response_class=HTMLResponse)
async def today_literature_discovery(request: Request):
    """Unread papers discovered by the weekly literature scan."""
    period = request.query_params.get("period", "week")
    if period == "month":
        cutoff = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    else:
        cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        period = "week"

    # Fetch what is DISPLAYED and count the rest, rather than loading every
    # unread paper to render ten of them. The panel was pulling 1,433 rows to
    # show 10 and using len() as the badge (audit 2026-08-25).
    _SHOWN = 12
    papers: list[dict] = []
    total = 0
    newer = 0
    seen_key = "today.literature"
    try:
        total = int(db_scalar(
            "SELECT COUNT(*) FROM new_publications "
            "WHERE (read_at IS NULL OR read_at = '') AND discovered_at >= ?",
            (cutoff,), default=0) or 0)
        papers = db_query(
            "SELECT id, title, journal, pub_date, doi, topic_tag, "
            "relevance_note, source_url, discovered_at "
            "FROM new_publications "
            "WHERE (read_at IS NULL OR read_at = '') "
            "AND discovered_at >= ? "
            "ORDER BY discovered_at DESC LIMIT ?",
            (cutoff, _SHOWN),
        ) or []
    except Exception:
        pass

    # THE COUNTER RULE. "1433 UNREAD" is not information — nobody reads 1,433
    # papers, so past a certain size the number's only job is to make the panel
    # feel like a debt. What is actionable is what arrived since the last visit.
    _prev = last_seen(seen_key)
    newer = count_since("new_publications", "discovered_at", _prev,
                        where="(read_at IS NULL OR read_at = '')")
    delta_html = delta_count(seen_key, total, newer)
    mark_seen(seen_key)

    topics: list[dict] = []
    try:
        topics = db_query(
            "SELECT topic, description FROM user_topics WHERE active = 1 "
            "ORDER BY topic"
        ) or []
    except Exception:
        pass

    try:
        from metis_mcp.tools import stack as _stack
        _states = _stack.states_for("paper", [p["id"] for p in papers])
        _tags = _stack.all_tags()
    except Exception:
        _states, _tags = {}, []

    return templates.TemplateResponse(
        request,
        "partials/today_literature_discovery.html",
        {"papers": papers, "total": total, "topics": topics, "period": period,
         "delta_html": delta_html, "newer": newer,
         "states": _states, "all_tags": _tags},
    )


@router.post("/api/today/literature-discovery/scan")
async def literature_discovery_scan():
    """Trigger an immediate literature discovery scan."""
    import asyncio
    try:
        from scheduler import job_literature_discovery
        found = await asyncio.to_thread(job_literature_discovery)
        return JSONResponse({"ok": True, "message": "Scan complete"})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:200]}, status_code=500)


@router.post("/api/today/literature-discovery/add")
async def literature_discovery_add(request: Request):
    """Add a discovered paper to the library (literature_metadata)."""
    body = await request.json()
    pub_id = body.get("pub_id")
    if not pub_id:
        return JSONResponse({"ok": False, "error": "Missing pub_id"}, status_code=400)
    try:
        rows = db_query(
            "SELECT title, journal, pub_date, doi, source_url FROM new_publications WHERE id = ?",
            (pub_id,),
        ) or []
        if not rows:
            return JSONResponse({"ok": False, "error": "Paper not found"}, status_code=404)
        p = rows[0]
        year = (p.get("pub_date") or "")[:4]
        now = datetime.datetime.now().isoformat(timespec="seconds")
        db_execute(
            "INSERT INTO literature_metadata (title, authors, year, doi, url, journal, created_at, library_source) "
            "VALUES (?, '', ?, ?, ?, ?, ?, 'discovery')",
            (p["title"], year, p.get("doi", ""), p.get("source_url", ""), p.get("journal", ""), now),
        )
        db_execute(
            "UPDATE new_publications SET read_at = ? WHERE id = ?",
            (now, pub_id),
        )
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:200]}, status_code=500)


@router.post("/api/today/literature-discovery/dismiss")
async def literature_discovery_dismiss(request: Request):
    """Mark paper(s) as read/dismissed."""
    body = await request.json()
    pub_ids = body.get("pub_ids") or []
    if body.get("pub_id"):
        pub_ids.append(body["pub_id"])
    if not pub_ids:
        return JSONResponse({"ok": False, "error": "No pub_ids"}, status_code=400)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        for pid in pub_ids:
            db_execute(
                "UPDATE new_publications SET read_at = ? WHERE id = ?",
                (now, pid),
            )
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:200]}, status_code=500)


# ── H: System Health Footer ──────────────────────────────────────────────

@router.get("/api/partial/today/system-health", response_class=HTMLResponse)
async def today_system_health(request: Request):
    """Compact system health status line."""
    job_count = 0
    last_scan_label = ""
    memory_count = 0
    api_status = "no key"

    # Scheduled jobs
    try:
        from scheduler import scheduler as _sched
        job_count = len(_sched.get_jobs())
    except Exception:
        pass

    # Last scan (morning_scan job)
    try:
        rows = db_query(
            "SELECT created_at FROM jobs_log "
            "WHERE job_type = 'morning_scan' "
            "ORDER BY created_at DESC LIMIT 1"
        ) or []
        if rows:
            last_scan_label = _age_label(rows[0]["created_at"]) + " ago"
    except Exception:
        pass

    # Memory count
    try:
        total = 0
        for table in ("session_summaries", "episodic_memory", "semantic_memory", "memory_entries"):
            try:
                total += db_scalar(f"SELECT COUNT(*) FROM {table}") or 0
            except Exception:
                pass
        memory_count = total
    except Exception:
        pass

    # API key check
    try:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            rc = os.environ.get("METIS_RC_ROOT", "")
            if rc:
                import json as _json
                kp = Path(rc) / "system" / "config" / "api-keys.json"
                if kp.exists():
                    keys = _json.loads(kp.read_text(encoding="utf-8"))
                    key = keys.get("anthropic", "")
        api_status = "healthy" if key else "no key"
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/today_system_health.html",
        {
            "job_count": job_count,
            "last_scan_label": last_scan_label,
            "memory_count": memory_count,
            "api_status": api_status,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS FRONT PAGE
#
# The old /news was three stacked lists (topic slipcases → flat feed → library).
# That is an RSS READER's model: group by category, treat every item as equal.
# A newspaper does the opposite — it RANKS, then groups. Nothing on the old page
# was bigger than anything else, so nothing invited a click.
#
# The ranking signal already existed and was being wasted: `relevance` is a real
# embedding score of each item against the user's own corpus. It was rendered as a
# small chip. Here it chooses the lead story.
#
# THE IMAGE PROBLEM (measured 2026-07-14, and it drives the whole layout):
#     policy / world-news ......... 100% have thumbnails
#     surveillance ................  15%
#     tropical-medicine ...........  13%
#     epidemiology ................   0%
# The domains he actually cares about have NO pictures; generic wire news has all
# of them. So a thumbnail-led grid would systematically bury his own field beneath
# BBC headlines. Photo cards and TYPOGRAPHIC cards are therefore equal citizens:
# an item without a picture must never look like a degraded one with a picture.
# ═══════════════════════════════════════════════════════════════════════════════

_SOURCE_NAMES = {
    "who.int": "WHO", "thelancet.com": "The Lancet", "nature.com": "Nature",
    "bbc.co.uk": "BBC", "bbc.com": "BBC", "theguardian.com": "The Guardian",
    "nejm.org": "NEJM", "science.org": "Science", "pubmed.ncbi.nlm.nih.gov": "PubMed",
    "cidrap.umn.edu": "CIDRAP", "reliefweb.int": "ReliefWeb", "bmj.com": "BMJ",
    "plos.org": "PLOS", "cdc.gov": "CDC", "reuters.com": "Reuters",
}


def _source_of(url: str) -> str:
    """Human source name from a URL — the wordmark on a typographic card."""
    if not url:
        return "—"
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()
    for domain, name in _SOURCE_NAMES.items():
        if host.endswith(domain):
            return name
    parts = host.split(".")
    return (parts[-2] if len(parts) >= 2 else host).replace("-", " ").title()


def _news_card(r: dict) -> dict:
    rel = r.get("relevance") or 0
    img = (r.get("image_url") or "").strip()
    return {
        # `brief_id`, never `rowid`. rowid is the surface's join key for thread
        # subjects and is fine for that inside one request, but a verdict OUTLIVES
        # the request — and rowid is reassigned by VACUUM. Keyed on rowid, a
        # "not for me" would silently reattach itself to a different story the
        # first time the database was compacted.
        "id": r.get("brief_id") or "",
        "title": r.get("title") or "Untitled",
        "summary": (r.get("summary") or "").strip(),
        "url": r.get("source_url") or "",
        "image": img,
        "has_image": bool(img),
        "source": _source_of(r.get("source_url") or ""),
        "domain": r.get("domain") or "general",
        "relevance": rel,
        # The qualitative band, not a raw %: the embedding baseline sits ~0.5,
        # so "62%" would read as a coin-flip when it is in fact a strong match.
        # 0.72, and the number was READ OFF THE DATA rather than reasoned to.
        # After the scorer was fixed (max similarity to the closest project /
        # idea / note, not a centroid of everything), the top of the news file
        # sorted like this:
        #
        #   0.808  Measuring elimination of gambiense HAT
        #   0.800  Modelling the role of animals in gambiense HAT
        #   0.787  Health economic evaluation of gambiense HAT elimination
        #   0.758  DR Congo: Ebola outbreak situation report
        #   0.750  World: Start Fund Monthly Risk Bulletin      <- quality falls off
        #   0.694  COVID rates low but increasing across the US
        #   0.687  Albania: UNHCR Western Balkans factsheet
        #   0.681  Dogs may hold clues to human longevity
        #
        # A first attempt at 0.68 admitted the last three. 0.72 was then too
        # tight: the highest scorers overall are PAPERS, and News excludes those
        # (source_type='article'), so within the news stream alone 0.72 left one
        # item in a month. Calibrated again on news only, where the top reads
        # DRC / Ebola / avian influenza / zoonotic-AI and holds to ~0.743:
        #
        #   >= 0.70   258 items   COVID-US (0.694), Albania (0.687) and
        #                         dog-longevity (0.681) all fall below
        #   >= 0.72   101 items   too few per week to be a daily tab
        #
        # This is a FLOOR, not the ranking. The tab already sorts by relevance
        # and caps at 60, so the floor's only job is to keep obvious noise out
        # while leaving enough for the sort to be worth doing.
        #
        # 0.68 after the anchor set was broadened on 2026-08-31. Reported: "It can be
        # sleeping sickness, NTDs, elimination of diseases, epidemiology,
        # digitalisation of health care. There are many topics close to my work."
        # Ten specific prose anchors were added for those, and the floor came
        # down to let them through: 675 of 2,939 news items, against 358 at 0.70.
        #
        # ACCEPTED LIMIT, stated rather than tuned around: "COVID rates
        # increasing across the United States" scores 0.685 and gets in. It IS
        # topically a disease-surveillance story; what makes it irrelevant to him
        # is the setting — US, COVID — and an embedding treats geography and
        # pathogen as minor next to the dominant topic. No threshold separates
        # those two, which is why the sort matters more than the cut.
        "close": rel >= RELEVANCE_CLOSE,
        "signal": (r.get("signal_strength") or "").strip(),
        "when": _age_label(r["created_at"]) if r.get("created_at") else "",
        # Raw timestamp for correct chronological sorting (the "when" label is not
        # sortable — "2d" vs "10h" would sort lexically).
        "_ts": r.get("created_at") or "",
    }


# ---------------------------------------------------------------------------
# News surface — tabs
# ---------------------------------------------------------------------------
# Category is the SPINE of this surface (it is a filter on the Today rail). One
# undifferentiated feed made it impossible to answer "what is happening in the
# world" separately from "what touches my work", so each question gets a tab.
#
# Tabs are matched on thread SUBJECT first, DOMAIN as fallback. Measured
# 2026-08-19: only 41% of items match a subject, so domain is carrying most of
# the load today — but subject is the better signal and grows as the user
# declares interests (see news_threads.user_subjects), so it is checked first.
#
# `domains` are lowercased on both sides at match time: the stored values are
# inconsistent ('NTD' 52 rows vs 'ntd' 48; 'SURVEILLANCE' vs 'surveillance'),
# and a case-sensitive tab would silently show half a category.
_NEWS_TABS: list[dict] = [
    {"key": "overview", "label": "Overview", "kind": "overview",
     "blurb": "Today's mix across every beat, then the stories still running."},
    {"key": "work", "label": "Related to my work", "kind": "work",
     "blurb": "Ranked by closeness to your library, with your own subjects first."},
    {"key": "outbreaks", "label": "Outbreaks", "kind": "filter",
     "subjects": {"ebola", "marburg", "mpox", "cholera", "measles", "polio", "dengue",
                  "yellow-fever", "lassa", "diphtheria", "meningitis", "influenza",
                  "covid", "outbreak-response", "sleeping-sickness", "malaria",
                  "tuberculosis", "hiv", "ntd", "vaccination"},
     "domains": {"surveillance", "outbreaks", "infectious-disease", "hat", "ntd",
                 "tropical-medicine", "drc", "malaria", "vectors"},
     "blurb": "Surveillance, alerts and disease events."},
    {"key": "world", "label": "World news", "kind": "filter",
     "subjects": {"conflict-health", "climate-health"},
     # Disasters belong here: outbreaks happen inside emergencies, so flood and
     # earthquake alerts are epidemiological context rather than a separate topic.
     "domains": {"world-news", "africa", "disasters"},
     "blurb": "The wider world, newest first."},
    {"key": "policy", "label": "Policy & funding", "kind": "filter",
     "subjects": {"health-financing", "pandemic-treaty", "health-workforce"},
     "domains": {"policy", "health-financing", "public-health"},
     "blurb": "Decisions, money and governance."},
    {"key": "science", "label": "Science & methods", "kind": "filter",
     "subjects": {"surveillance", "antimicrobial-resistance"},
     "domains": {"science", "methods", "epidemiology", "spatial-epi", "epi-methods",
                 "biomedical", "field-research"},
     "blurb": "Findings and methodology."},
    {"key": "ai", "label": "AI", "kind": "filter",
     "subjects": {"ai-in-health"}, "domains": {"ai"},
     "blurb": "Artificial intelligence, in health and generally."},
]

_NEWS_TABS_BY_KEY = {t["key"]: t for t in _NEWS_TABS}

# Period windows. Read against COALESCE(published_at, created_at) — see the
# 20260819 migration: created_at is the SCAN time, so filtering on it reports
# the scanner's uptime rather than the news.
_NEWS_PERIODS = {
    "day":   (1,  "Today"),
    "week":  (7,  "This week"),
    "month": (30, "This month"),
}


def _news_rows(period: str = "week", limit: int = 400) -> list[dict]:
    """News items in the period, newest-published first. Never papers.

    `source_type='article'` is the literature stream. It is excluded here rather
    than filtered per-tab so that no tab can ever reintroduce it: papers belong
    to the Library surface, and when they were mixed in the relevance ranking
    promoted them above real news (a paper is by definition closer to a
    researcher's corpus than a BBC headline).
    """
    days, _ = _NEWS_PERIODS.get(period, _NEWS_PERIODS["week"])
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    return db_query(
        """SELECT b.rowid AS ref, b.brief_id, b.title, b.summary, b.domain,
                  b.signal_strength, b.source_url, b.created_at, b.relevance,
                  COALESCE(b.image_url,'') AS image_url,
                  COALESCE(NULLIF(b.published_at,''), b.created_at) AS when_at
           FROM news_briefs b
           WHERE COALESCE(NULLIF(b.published_at,''), b.created_at) > ?
             AND COALESCE(b.source_type,'news') != 'article'
           ORDER BY when_at DESC
           LIMIT ?""",
        (cutoff, limit),
    ) or []


def _subject_for_refs(refs: list[int]) -> dict[int, str]:
    """rowid → thread subject, for the items on screen."""
    if not refs:
        return {}
    out: dict[int, str] = {}
    # Chunked so a large window cannot exceed SQLite's variable limit (999).
    for i in range(0, len(refs), 400):
        chunk = refs[i:i + 400]
        marks = ",".join("?" * len(chunk))
        rows = db_query(
            f"SELECT i.brief_ref ref, COALESCE(t.subject,'') subj, "
            f"       COALESCE(t.label,'') label, t.thread_id "
            f"FROM news_thread_items i JOIN news_threads t ON t.thread_id = i.thread_id "
            f"WHERE i.brief_ref IN ({marks})", tuple(chunk)) or []
        for r in rows:
            out[r["ref"]] = r["subj"] or ""
    return out


def _tab_matches(tab: dict, card: dict, subject: str) -> bool:
    """Subject first, domain as fallback — the declared matching rule."""
    if subject and subject in tab.get("subjects", ()):
        return True
    dom = (card.get("domain") or "").strip().lower()
    return bool(dom) and dom in {d.lower() for d in tab.get("domains", ())}


# The three ways to look at the same list. the researcher asked for "list, detailed list
# or thumbnails" — the density control every reader of a long feed expects, and
# the one thing that makes 60 items skimmable instead of a wall.
#
# The view is a QUERY PARAMETER, not a client-side class toggle: the row markup
# genuinely differs (a compact row has no summary and no thumbnail to download),
# so switching view in the browser alone would still pay for images nobody sees.
NEWS_VIEWS = {
    "list":     "List",
    "detailed": "Detailed",
    "cards":    "Thumbnails",
}


def render_news_tab(request: Request, tab: str = "overview", period: str = "week",
                    view: str = "detailed") -> str:
    """One News tab, as a string, so any surface can re-render it.

    Extracted from the route on 2026-08-26 when triage buttons arrived: pressing
    "read later" on a card has to give back the list it came from, and a route
    that can only answer HTTP cannot be reused for that.
    """
    resp = _news_tab_response(request, tab, period, view)
    return resp.body.decode("utf-8")


@router.get("/api/partial/news/tab", response_class=HTMLResponse)
async def news_tab(request: Request, tab: str = "overview", period: str = "week",
                   view: str = "detailed"):
    """Render one News tab. Overview is thread-based; the rest are card grids."""
    return _news_tab_response(request, tab, period, view)


# ── THE OVERVIEW IS A NEWS PAGE ──────────────────────────────────────────────
# Asked for 2026-09-04: "Overview tab needs to show thumbnails and only a mix of
# all categories not three per category like it is currently. It needs to feel
# like a news website. So overview has max 20 news items that refresh every day
# regardless if i logged on or read them."
#
# It was running stories: each thread showed three items and a "+64 more", which
# is the three-per-category shape. Those threads answer a real question and the
# reasoning for them is worth keeping, so they move BELOW this, folded — the tab
# opens as a news page and the grouping is still one click away.
#
# THE DAY IS THE UNIT and read state is ignored, which rules out both easy
# implementations: a feed reshuffled per request never settles, and one that
# hides what you have read empties itself as you use it. The domain rotation is
# seeded by TODAY'S DATE — identical all day, different tomorrow, indifferent to
# what was opened.
def _overview_feed(days: int, limit: int = 20) -> dict:
    """One mixed feed of `limit` items, dealt round-robin across beats."""
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    rows = db_query(
        "SELECT title, summary, domain, signal_strength, source_url, created_at, "
        "       relevance, COALESCE(image_url,'') AS image_url "
        "FROM news_briefs WHERE created_at > ? "
        # Papers belong in the Library, not the front page.
        "  AND COALESCE(source_type,'news') != 'article' "
        "ORDER BY relevance DESC, created_at DESC", (cutoff,), default=[]) or []
    cards = [_news_card(r) for r in rows]

    # De-duplicate before dealing, or one story on three wires takes three slots.
    seen, unique = set(), []
    for c in cards:
        k = (c.get("url") or c.get("title") or "").strip().lower()
        if k and k not in seen:
            seen.add(k)
            unique.append(c)

    buckets: dict[str, list] = {}
    for c in unique:
        buckets.setdefault((c.get("domain") or "other").strip() or "other", []).append(c)
    order = sorted(buckets)
    if order:
        order = order[int(datetime.date.today().strftime("%Y%m%d")) % len(order):] + \
                order[:int(datetime.date.today().strftime("%Y%m%d")) % len(order)]

    feed = []
    while len(feed) < limit:
        added = False
        for dom in order:
            if buckets[dom]:
                feed.append(buckets[dom].pop(0))
                added = True
                if len(feed) == limit:
                    break
        if not added:
            break
    return {"feed": feed, "lead": feed[0] if feed else None, "rest": feed[1:],
            "feed_total": len(unique),
            "feed_beats": len({(c.get("domain") or "other") for c in feed}),
            "feed_images": sum(1 for c in feed if c.get("has_image"))}


def _news_tab_response(request: Request, tab: str, period: str, view: str):
    if tab not in _NEWS_TABS_BY_KEY:
        tab = "overview"
    if period not in _NEWS_PERIODS:
        period = "week"
    if view not in NEWS_VIEWS:
        view = "detailed"
    spec = _NEWS_TABS_BY_KEY[tab]
    try:
        from metis_mcp.tools import stack as _stack
        stack_counts = _stack.counts()
    except Exception:
        stack_counts = {"later": 0, "saved": 0}
    try:
        import ui as _ui
        whatsnew_news = _ui.whats_new(
            "news", "news_briefs", "COALESCE(NULLIF(published_at,''), created_at)",
            where="COALESCE(source_type,'news') != 'article'")
    except Exception as _exc:
        _log.warning("news: whats_new unavailable: %s", _exc)
        whatsnew_news = None

    # ---- Overview: running stories, not a link list -----------------------
    if spec["kind"] == "overview":
        days, plabel = _NEWS_PERIODS.get(period, _NEWS_PERIODS["week"])
        threads: list[dict] = []
        try:
            import sqlite3 as _sq
            _src = str(Path(__file__).parent.parent.parent / "mcp-server" / "src")
            if _src not in sys.path:
                sys.path.insert(0, _src)
            from metis_mcp.tools import news_threads as _nt
            conn = _sq.connect(_get_db_path())
            conn.row_factory = _sq.Row
            since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            for t in _nt.thread_window(conn, since):
                # Buckets are incoherent by construction ('who' mixes crime with
                # health) — useless as an overview row.
                if t["is_bucket"]:
                    continue
                threads.append(t)
            conn.close()

        except Exception as _exc:
            _log.warning("news overview: thread window failed: %s", _exc)

        # A ONE-ITEM THREAD IS NOT A RUNNING STORY. This tab's own standfirst
        # promises "running stories, not a list of links", and then 93% of the
        # threads it drew held exactly one item — a single link wearing a story's
        # clothes, under a name the fallback tokeniser invented for it. That is
        # what put "Approves treatment", "Agency approves" and "Approves · Mali"
        # on screen as three separate developing stories when they were three
        # write-ups of one FDA decision.
        #
        # The clustering is not going to reach every item: the vocabulary is
        # subject + place, and most world news is neither a listed disease nor
        # in a listed country. So the honest presentation is to STOP CLAIMING
        # it did. Threads that genuinely accumulated coverage lead; everything
        # else is listed plainly underneath as what it is — single reports.
        singles = [t for t in threads if len(t.get("items") or []) < 2]
        threads = [t for t in threads if len(t.get("items") or []) >= 2]

        # A SERIES IS NOT THREE STORIES. Inside the Ebola · DR Congo thread the
        # first three headlines were "…Uganda Weekly External Situation Report
        # 13", "…Report 14" and "…Report 15" — one weekly bulletin, three
        # instalments, filling the whole thread with the same sentence. This is
        # what the researcher meant by seeing Ebola over and over: not a bug in the
        # clustering, which correctly put them together, but a bug in showing
        # every instalment as though it were new information.
        #
        # `collapse()` keeps the NEWEST instalment and hangs the rest off it as
        # `_earlier`; nothing is dropped, so the count under the thread still
        # adds up and the older editions are still reachable.
        try:
            import freshness as _fresh
            for _t in threads:
                _t["items"] = _fresh.collapse(
                    _t.get("items") or [], title_field="title", ts_field="created_at")
        except Exception as _exc:
            _log.warning("news overview: series collapse unavailable: %s", _exc)

        # One lookup across every item in every thread on screen.
        _ov_ids = ([i.get("id") for t in threads[:24] for i in t.get("items") or []]
                   + [i.get("id") for t in singles[:30] for i in t.get("items") or []])
        try:
            from metis_mcp.tools import stack as _stack
            _ov_states = _stack.states_for("news", _ov_ids)
            _ov_tags = _stack.all_tags()
        except Exception:
            _ov_states, _ov_tags = {}, []

        return templates.TemplateResponse(
            request, "partials/news_overview.html",
            {"threads": threads[:24], "tabs": _NEWS_TABS, "active": tab,
             "period": period, "periods": _NEWS_PERIODS, "period_label": plabel,
             "view": view, "views": NEWS_VIEWS, "stack_counts": stack_counts,
         "whatsnew_news": whatsnew_news,
             "states": _ov_states, "all_tags": _ov_tags,
             "singles": singles[:30], "singles_total": len(singles),
             "total_items": sum(len(t["items"]) for t in threads),
             **_overview_feed(days)},
        )

    # ---- Category / work tabs: card grids --------------------------------
    rows = _news_rows(period)
    cards = [_news_card(r) for r in rows]
    subjects = _subject_for_refs([r["ref"] for r in rows])
    for c, r in zip(cards, rows):
        c["subject"] = subjects.get(r["ref"], "")
        c["when_at"] = r["when_at"]

    if spec["kind"] == "work":
        # "Related to my work" must NOT depend on embeddings alone.
        #
        # `close` is relevance >= db.RELEVANCE_CLOSE, from the embedding model — and
        # that model is optional (the MCP smoke test currently reports
        # "embedding model unavailable: ConnectError"). With relevance stuck at 0
        # this tab rendered completely empty, which is the worst possible failure
        # for the one tab that justifies the surface existing. So proximity is
        # now one of three independent routes in, and any of them is enough:
        #   1. embedding proximity to the library (best signal, when available)
        #   2. the item's thread subject is one the user declared as an interest
        #   3. its domain or subject matches a profile interest / news topic by name
        try:
            from metis_mcp.tools.news_threads import user_subjects, SUBJECTS, _slugify
            declared = set(user_subjects()) - set(SUBJECTS)
        except Exception:
            declared, _slugify = set(), None

        interest_slugs: set[str] = set()
        try:
            import json as _json
            _p = Path(os.environ.get("METIS_RC_ROOT", "")) / "system" / "config" / "user-preferences.json"
            if _p.exists():
                _prefs = _json.loads(_p.read_text(encoding="utf-8"))
                for _f in ("interests", "news_topics"):
                    for _v in (_prefs.get(_f) or []):
                        s = _slugify(str(_v)) if _slugify else str(_v).lower().replace(" ", "-")
                        if s:
                            interest_slugs.add(s)
                            # SINGLE WORDS ARE NO LONGER INDEXED. the researcher,
                            # 2026-08-31: "when it says 'related to your work'
                            # it is not so close actually."
                            #
                            # This split every interest into its words, so
                            # "neglected tropical diseases" contributed
                            # "diseases" and "AI in global health" contributed
                            # "health". A domain of `health` or `global-health`
                            # then counted as related to his work — which, in a
                            # set of health feeds, is nearly everything. The tab
                            # was not ranking badly; it was matching on a word
                            # as generic as "health".
                            #
                            # Multi-word fragments are still useful, because a
                            # subject slug may carry only part of an interest:
                            # "sleeping sickness elimination" should still reach
                            # a 'sleeping-sickness' subject.
                            _parts = [w for w in re.split(r"[^a-z0-9]+", s) if len(w) > 3]
                            for _i in range(len(_parts) - 1):
                                interest_slugs.add("-".join(_parts[_i:_i + 2]))
        except Exception:
            pass

        def _is_mine(c: dict) -> bool:
            if c["close"]:
                return True
            subj = (c.get("subject") or "").lower()
            if subj and (subj in declared or subj in interest_slugs):
                return True
            dom = (c.get("domain") or "").strip().lower()
            return bool(dom) and dom in interest_slugs

        picked = [c for c in cards if _is_mine(c)]
        # Relevance first where it exists, then recency — so the ordering degrades
        # gracefully to chronological rather than collapsing when relevance is 0.
        picked.sort(key=lambda c: (-(c["relevance"] or 0), c["when_at"]))
        # Sub-filters inside the tab: one chip per subject actually present.
        groups: dict[str, int] = {}
        for c in picked:
            if c.get("subject"):
                groups[c["subject"]] = groups.get(c["subject"], 0) + 1
        subfilters = sorted(groups.items(), key=lambda kv: -kv[1])[:12]
    else:
        picked = [c for c, r in zip(cards, rows)
                  if _tab_matches(spec, c, subjects.get(r["ref"], ""))]
        subfilters = []

    counts = _news_tab_counts(period)

    # Fold BEFORE the cap. Collapsing after slicing would show sixty rows that
    # turn out to be forty stories, which is the same mistake the boards were
    # making with WHO's weekly Ebola situation reports.
    try:
        import freshness
        picked = freshness.collapse(picked, title_field="title", ts_field="_ts")
    except Exception as _exc:
        _log.warning("news tab: freshness unavailable: %s", _exc)
    shown = picked[:60]

    # One query for all 60 cards, not one per card. Without this the grid would
    # make sixty round trips just to decide which button to draw.
    states, tag_list = {}, []
    try:
        from metis_mcp.tools import stack as _stack
        states = _stack.states_for("news", [c.get("id") for c in shown])
        tag_list = _stack.all_tags()
    except Exception as _exc:
        _log.warning("news tab: stack state unavailable: %s", _exc)

    return templates.TemplateResponse(
        request, "partials/news_tab.html",
        {"cards": shown, "tabs": _NEWS_TABS, "active": tab, "spec": spec,
         "period": period, "periods": _NEWS_PERIODS, "counts": counts,
         "subfilters": subfilters, "total": len(picked),
         "view": view, "views": NEWS_VIEWS, "stack_counts": stack_counts,
         "whatsnew_news": whatsnew_news,
         "states": states, "all_tags": tag_list},
    )


@router.get("/api/partial/news/thread-items", response_class=HTMLResponse)
async def news_thread_items(request: Request, thread: str, period: str = "week",
                            skip: int = 3):
    """The rest of one story thread, fetched when its fold is opened.

    Exists because rendering every thread's every item inline cost 669 KB on a
    tab where 72 of 233 items are visible. The reader who opens a story pays for
    that story; nobody else does.
    """
    import sqlite3 as _sq
    days, _ = _NEWS_PERIODS.get(period, _NEWS_PERIODS["week"])
    items: list[dict] = []
    try:
        _src = str(Path(__file__).parent.parent.parent / "mcp-server" / "src")
        if _src not in sys.path:
            sys.path.insert(0, _src)
        from metis_mcp.tools import news_threads as _nt
        conn = _sq.connect(_get_db_path())
        conn.row_factory = _sq.Row
        since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        for t in _nt.thread_window(conn, since):
            if t.get("thread_id") == thread:
                items = (t.get("items") or [])[max(0, skip):]
                break
        conn.close()
    except Exception as _exc:
        _log.warning("thread-items %s: %s", thread, _exc)

    try:
        from metis_mcp.tools import stack as _stack
        states = _stack.states_for("news", [i.get("id") for i in items])
    except Exception:
        states = {}

    return templates.TemplateResponse(
        request, "partials/news_thread_items.html",
        {"items": items, "states": states,
         "T": "#news-tab-body",
         "BACK": f"news:overview:{period}:detailed"},
    )


def _news_tab_counts(period: str) -> dict[str, int]:
    """Item count per tab, so a tab that would open empty says so up front."""
    rows = _news_rows(period)
    if not rows:
        return {t["key"]: 0 for t in _NEWS_TABS}
    cards = [_news_card(r) for r in rows]
    subjects = _subject_for_refs([r["ref"] for r in rows])
    counts: dict[str, int] = {}
    for t in _NEWS_TABS:
        if t["kind"] == "overview":
            counts[t["key"]] = len(rows)
        elif t["kind"] == "work":
            # Count only the cheap embedding signal here — recomputing the full
            # three-route match for the strip on every request is not worth it,
            # and the tab body shows the true total when opened.
            counts[t["key"]] = sum(1 for c in cards if c["close"]) or None
        else:
            counts[t["key"]] = sum(
                1 for c, r in zip(cards, rows)
                if _tab_matches(t, c, subjects.get(r["ref"], "")))
    return counts


@router.get("/api/partial/news/front", response_class=HTMLResponse)
async def news_front(request: Request, days: int = 7):
    """The curated front page: lead → your beat → top stories → wire."""
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()

    rows = db_query(
        """SELECT title, summary, domain, signal_strength, source_url,
                  created_at, relevance, COALESCE(image_url,'') AS image_url
           FROM news_briefs
           WHERE created_at > ?
             -- Papers belong in the Library, not the front page. The Today rail and
             -- the topic counts were filtered earlier the same day; THIS query is the
             -- actual /news surface and was missed, so the fix was only half applied.
             AND COALESCE(source_type,'news') != 'article'
           ORDER BY relevance DESC, created_at DESC""",
        (cutoff,),
    ) or []

    cards = [_news_card(r) for r in rows]
    seen: set[str] = set()

    def take(pool, n):
        """Pull the next n unseen cards — so a story never appears twice."""
        out = []
        for c in pool:
            key = c["url"] or c["title"]
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
            if len(out) == n:
                break
        return out

    # 1. THE LEAD — single highest-relevance item. Prefer one with a picture, but
    #    only among the genuinely top-relevance items: a pretty photo must never
    #    outrank a Lancet paper that is actually about his work.
    top_band = [c for c in cards if c["close"]] or cards
    lead_pool = [c for c in top_band[:6] if c["has_image"]] or top_band
    lead = (take(lead_pool, 1) or [None])[0]

    # 1b. WORLD — a compact band of what's happening in the world, so the page
    #     isn't only your niche. Ranked by RECENCY, not corpus proximity: for world
    #     news you want what just happened, not what's closest to your library.
    #     Pulled from a SEPARATE pool so it never competes with the curated lead.
    world = sorted(
        [c for c in cards if c["domain"] in ("world-news", "policy")],
        key=lambda c: c["_ts"], reverse=True,
    )
    world = [c for c in world if c["url"] != (lead or {}).get("url")][:6]

    # 2. CLOSEST TO YOUR WORK — the section that justifies Metis existing.
    #    Ranked by corpus proximity, NOT recency.
    closest = take([c for c in cards if c["close"]], 4)

    # 3. TOP STORIES — the next tier.
    top = take(cards, 6)

    # 4. THE WIRE — everything else, dense and chronological (newest first).
    wire = sorted(
        [c for c in cards if (c["url"] or c["title"]) not in seen],
        key=lambda c: c["_ts"], reverse=True,
    )[:40]

    return templates.TemplateResponse(
        request,
        "partials/news_front.html",
        {
            "lead": lead,
            "world": world,
            "closest": closest,
            "top": top,
            "wire": wire,
            "total": len(cards),
            "days": days,
            "with_images": sum(1 for c in cards if c["has_image"]),
        },
    )


# ---------------------------------------------------------------------------
# News digest — "what happened this week", at the top of the News surface
# ---------------------------------------------------------------------------
# `news_topic_summaries` has existed with zero rows: a summary feature that was
# given a table and never fed. The surface opened straight into a lead story, so
# the reader had to infer the shape of the week from the cards themselves.
#
# Written to work WITHOUT an API call. The counts, the busiest beats and the
# strongest story are all in the database already, and a digest that needs credit
# to render is one that is missing on the days the key is unset or the quota is
# spent. Prose from a model can be added on top later; the skeleton should never
# depend on it.

_DIGEST_PERIODS = {"day": (1, "today"), "week": (7, "this week")}


@router.get("/api/partial/news/digest", response_class=HTMLResponse)
async def news_digest(request: Request, period: str = "week"):
    days, label = _DIGEST_PERIODS.get(period, _DIGEST_PERIODS["week"])
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()

    total = db_scalar(
        "SELECT COUNT(*) FROM news_briefs WHERE created_at >= ? "
        "AND COALESCE(source_type,'news') != 'article'",
        (cutoff,), default=0,
    ) or 0
    unseen = db_scalar(
        "SELECT COUNT(*) FROM news_briefs WHERE created_at >= ? AND seen_at IS NULL "
        "AND COALESCE(source_type,'news') != 'article'",
        (cutoff,), default=0,
    ) or 0
    beats = db_query(
        "SELECT domain, COUNT(*) AS n FROM news_briefs "
        "WHERE created_at >= ? AND domain IS NOT NULL AND domain != '' "
        "AND COALESCE(source_type,'news') != 'article' "
        "GROUP BY domain ORDER BY n DESC LIMIT 4",
        (cutoff,), default=[],
    ) or []
    # "Closest to your work" rather than "most recent": the reason this surface
    # exists is proximity to the researcher's corpus, so the digest leads on that.
    # GROUP BY title: the same wire story arrives from several feeds, so without
    # deduplication the digest led with one headline and then listed it again two
    # lines later — which reads as a bug in the summary rather than in the data.
    closest = db_query(
        "SELECT title, domain, MAX(COALESCE(relevance,0)) AS relevance FROM news_briefs "
        "WHERE created_at >= ? AND COALESCE(source_type,'news') != 'article' "
        "GROUP BY title ORDER BY relevance DESC LIMIT 3",
        (cutoff,), default=[],
    ) or []

    if not total:
        return HTMLResponse(
            '<div class="panel panel-pad" style="margin-bottom:22px;">'
            '<div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;'
            'color:var(--m-muted);">NOTHING NEW ' + label.upper() + '</div></div>'
        )

    beat_txt = ", ".join(f"{b['domain']} ({b['n']})" for b in beats)
    lead = closest[0]["title"] if closest else ""
    others = "".join(
        f'<li style="margin:2px 0;">{c["title"][:110]}</li>' for c in closest[1:]
    )
    toggle = "".join(
        f'<button hx-get="/api/partial/news/digest?period={p}" hx-target="#news-digest" '
        f'hx-swap="outerHTML" style="font-family:var(--m-mono);font-size:9px;'
        f'letter-spacing:0.1em;padding:2px 8px;border:1px solid var(--m-line);'
        f'border-radius:10px;cursor:pointer;background:'
        f'{"var(--m-accent)" if p == period else "transparent"};'
        f'color:{"var(--m-bg)" if p == period else "var(--m-muted)"};">{p.upper()}</button>'
        for p in ("day", "week")
    )

    return HTMLResponse(f"""
    <div id="news-digest" class="panel" style="padding:18px 22px;margin-bottom:22px;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;">
        <span style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.14em;
                     color:var(--m-muted);">THE BRIEFING · {label.upper()}</span>
        <span style="display:flex;gap:6px;">{toggle}</span>
      </div>
      <p style="margin:0 0 8px;font-size:14px;line-height:1.5;color:var(--m-ink);">
        <strong>{total}</strong> item{'s' if total != 1 else ''} {label}{f', <strong>{unseen}</strong> you have not seen' if unseen else ''}.
        {f'Busiest: {beat_txt}.' if beat_txt else ''}
      </p>
      {f'<p style="margin:0;font-size:13px;color:var(--m-muted);line-height:1.5;">Closest to your work: <span style="color:var(--m-ink);">{lead[:150]}</span></p>' if lead else ''}
      {f'<ul style="margin:6px 0 0 16px;padding:0;font-size:12px;color:var(--m-muted);">{others}</ul>' if others else ''}
    </div>""")


# ---------------------------------------------------------------------------
# Nature Briefing — editions, not a feed
# ---------------------------------------------------------------------------
# the researcher asked for the Daily and AI & Robotics briefings to have "special places
# in the news surface, in the beginning collapsed of course". They are editions:
# someone decided what mattered today and in what order, and that running order
# is the value. Shredding them into `news_briefs` would add their stories to a
# feed already carrying 3,700 and lose exactly that.

def _briefing_panels() -> list[dict]:
    """The surfaced briefings, newest edition first.

    English only by default — Nature publishes translated editions on the same
    list, and the Arabic Briefing arriving in a panel the researcher reads in English is
    noise, not reach. `briefings.editions(lang="")` still returns everything.
    """
    try:
        from metis_mcp.tools import briefings as B
    except Exception as exc:
        _log.warning("briefings module unavailable: %s", exc)
        return []
    names = {slug: name for _needle, slug, name in B.KINDS}
    out = []
    for kind in B.SURFACED:
        eds = B.editions(kind, 6)
        out.append({
            "kind": kind,
            "name": names.get(kind, kind),
            "editions": eds,
            "n_editions": len(eds),
            "latest": eds[0]["published_at"][:10] if eds else "",
        })
    return out


@router.get("/api/partial/news/briefings", response_class=HTMLResponse)
async def news_briefings(request: Request):
    return templates.TemplateResponse(
        request, "partials/news_briefings.html",
        {"briefings": _briefing_panels()})


@router.get("/api/partial/news/briefing/{edition_id}", response_class=HTMLResponse)
async def news_briefing_items(request: Request, edition_id: str):
    """One edition's stories, fetched when the reader opens it."""
    from metis_mcp.tools import briefings as B
    items = B.items_of(edition_id)
    try:
        from metis_mcp.tools import stack as _stack
        states = _stack.states_for("news", [i["item_id"] for i in items])
    except Exception:
        states = {}
    return templates.TemplateResponse(
        request, "partials/news_briefing_items.html",
        {"items": items, "states": states, "edition_id": edition_id})


@router.post("/api/news/briefings/refresh", response_class=HTMLResponse)
async def news_briefings_refresh(request: Request):
    """Pull the archive feed now, then redraw both panels."""
    try:
        from metis_mcp.tools import briefings as B
        r = B.scan()
        _log.info("briefings: %s", r)
    except Exception as exc:
        _log.warning("briefings refresh failed: %s", exc)
    return templates.TemplateResponse(
        request, "partials/news_briefings.html",
        {"briefings": _briefing_panels()})
