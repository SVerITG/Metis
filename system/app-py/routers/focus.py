"""focus.py — the dashboard surface for a focus area.

ONE TEMPLATE, MANY SURFACES
    Every other surface in Metis is a bespoke template: `today.html`,
    `knowledge.html`, `work.html`. A focus surface cannot work that way — the
    whole point is that the researcher adds and removes them himself, and a surface that
    needs a developer to exist is not a surface a user can add.

    So there is exactly one template, driven by one row. `/focus/ai-in-health-
    epidemiology` and `/focus/anything-else` render the same file against
    different data. That is what makes "custom pages a user can add or remove"
    a real feature rather than a promise.

THE FIVE COMPONENTS
    Taken from what the researcher asked for, and each one reads a table that already owns
    its rows — the focus writes no copies:

      pulse     what is new since the last visit, and how stale the feed is
      overview  the standing narrative — the orientation that survives the feed
      feed      news through the lens              (news_briefs)
      reading   literature through the lens        (new_publications)
      thinking  notes and ideas written here       (personal_notes, ideas)

    `pulse` is first on purpose. Opening a focus you have not seen for a week,
    the first question is "what happened", not "what is this".
"""
from __future__ import annotations

import datetime
import logging
import uuid

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter()
log = logging.getLogger("metis.focus")


def _f():
    """Import the shared focus logic lazily so a broken MCP tree cannot break boot."""
    from metis_mcp.tools import focus as F
    return F


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------
@router.get("/focus/{slug}", response_class=HTMLResponse)
async def focus_page(request: Request, slug: str):
    """One template, rendered against one focus row."""
    from main import templates
    F = _f()
    area = F.get_focus(slug)
    if not area:
        return RedirectResponse(url="/", status_code=302)

    # Read the pulse BEFORE stamping the visit, or "new since last visit" is
    # always zero — the surface would mark everything read by being opened.
    pulse = F.focus_pulse(slug)
    F.touch_visit(slug)

    # A wider window than the 14 the surface shows: the sift needs the whole
    # catch to report honest counts, and "38 unjudged" is only true if 38 were
    # actually looked at. The template slices for display, not the query.
    ctx = _ctx(request, slug)
    ctx.update({
        "active_tab": f"focus:{slug}",
        "pulse": pulse,
        "brief": F.latest_brief(slug),
        "deeplink": "",
        "shelf": F.list_focus("active"),
        "all_areas": F.list_focus(),
        "max_shelf": F.MAX_SHELF,
    })
    return templates.TemplateResponse(request, "focus.html", ctx)


# ---------------------------------------------------------------------------
# Shelf management
# ---------------------------------------------------------------------------
@router.post("/api/focus/{slug}/state")
async def set_state(slug: str, state: str = Form(...)):
    """Put a focus on the shelf, take it off, or archive it."""
    F = _f()
    import asyncio
    res = await F.set_focus_state(slug, state)
    return JSONResponse({"ok": True, "message": res[0].text})


@router.get("/api/focus/shelf")
async def shelf():
    """The active shelf — what the navbar renders."""
    F = _f()
    return JSONResponse({
        "ok": True,
        "max": F.MAX_SHELF,
        "active": [
            {"slug": a["slug"], "title": a["title"], "slot": a["shelf_slot"]}
            for a in F.list_focus("active")
        ],
    })


# ---------------------------------------------------------------------------
# Writing on a focus — the "brainstorm" half
# ---------------------------------------------------------------------------
# Notes and ideas are tagged `focus:<slug>` and written to the tables that own
# them. That tag is the ONLY association, and it is why archiving a focus loses
# nothing: the row stays in `personal_notes` / `ideas` with its tag intact,
# findable by search whether or not the lens still exists.
@router.post("/api/focus/{slug}/note", response_class=HTMLResponse)
async def add_note(request: Request, slug: str, content: str = Form(...),
                   title: str = Form("")):
    """Record a note against this focus."""
    from db import db_execute
    from main import templates
    F = _f()
    if content.strip():
        db_execute(
            "INSERT INTO personal_notes (note_id, content, title, tags, created_at, "
            "updated_at) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4())[:8], content.strip(), title.strip(),
             f"focus:{slug}", _now(), _now()))
    ctx = _ctx(request, slug)
    body = templates.get_template("partials/focus_thinking.html").render(**ctx)
    return HTMLResponse(body + _counts_oob(request, slug, ctx))


@router.post("/api/focus/{slug}/idea", response_class=HTMLResponse)
async def add_idea(request: Request, slug: str, text: str = Form(...)):
    """Capture an idea against this focus."""
    from db import db_execute
    from main import templates
    F = _f()
    if text.strip():
        db_execute(
            "INSERT INTO ideas (idea_id, text, idea_type, tags, created_at, domain) "
            "VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4())[:8], text.strip(), "focus", f"focus:{slug}",
             _now(), slug))
    ctx = _ctx(request, slug)
    body = templates.get_template("partials/focus_thinking.html").render(**ctx)
    return HTMLResponse(body + _counts_oob(request, slug, ctx))


# ---------------------------------------------------------------------------
# Partials — so a refresh does not reload the page
# ---------------------------------------------------------------------------
# Both go through `_ctx`, the same builder the page and every verdict route use.
# These used to hand-roll their own two-key context, and that is precisely how a
# partial drifts out of step with the page it belongs to: the template gained
# `counts` and the sift, and a hand-rolled dict would have rendered a blank
# header on refresh while the full page looked fine.
@router.get("/api/partial/focus/{slug}/feed", response_class=HTMLResponse)
async def feed_partial(request: Request, slug: str):
    from main import templates
    return templates.TemplateResponse(request, "partials/focus_feed.html",
                                      _ctx(request, slug))


@router.get("/api/partial/focus/{slug}/reading", response_class=HTMLResponse)
async def reading_partial(request: Request, slug: str):
    from main import templates
    return templates.TemplateResponse(request, "partials/focus_reading.html",
                                      _ctx(request, slug))


@router.post("/api/focus/{slug}/refresh", response_class=HTMLResponse)
async def refresh(request: Request, slug: str):
    """Re-scan the sources this focus reads, then re-render the pulse.

    Deliberately reuses the SAME scan jobs the rest of Metis uses rather than
    fetching on its own — a focus is a lens over the shared collection, so a
    focus-specific fetch path would produce items only this surface could see.
    """
    from main import templates
    F = _f()
    errors = []
    try:
        from metis_mcp.tools.content_scan import scan_news_feeds
        scan_news_feeds(max_per_feed=8)
    except Exception as exc:
        errors.append(f"news: {type(exc).__name__}")
    try:
        from db import db_execute
        db_execute("UPDATE focus_areas SET last_refreshed_at=? WHERE slug=?",
                   (_now(), slug))
    except Exception as exc:
        errors.append(f"stamp: {type(exc).__name__}")
    if errors:
        log.warning("[focus] refresh %s: %s", slug, "; ".join(errors))
    return templates.TemplateResponse(request, "partials/focus_pulse.html", {
        "area": F.get_focus(slug), "pulse": F.focus_pulse(slug),
        "corpus": F.focus_corpus(slug),
        "today": datetime.date.today().isoformat()})


# ---------------------------------------------------------------------------
# The index — where focus areas are created, and where the non-active ones live
# ---------------------------------------------------------------------------
# Two gaps this closes.
#
# 1. THERE WAS NO WAY TO CREATE A FOCUS FROM THE DASHBOARD. It took an MCP call,
#    which quietly contradicts the whole premise: a surface is not one a user
#    can add if adding one requires a tool call.
#
# 2. `following` AND `archived` AREAS WERE UNREACHABLE. Only active areas appear
#    in the navbar, so anything taken off the shelf could be opened only by typing
#    its URL. An interest you set aside is exactly the one you will not remember
#    the slug for.
#
# The form asks for keyword GROUPS as separate fields — "must mention one of" AND
# "and one of" — rather than asking for JSON. That teaches the conjunction by
# construction, which matters because the conjunction is the one thing a user has
# to understand for the lens to behave.
def _suggest_link() -> str:
    """A deeplink that asks Claude to propose a focus, seeded with real work.

    Seeded, and that is the whole difference. "Suggest a research focus" produces
    a plausible-sounding subject anybody could have named. Handed the projects
    this researcher actually has open, the ideas he has captured and what he has
    been reading, it proposes something he might not have thought to cross — which
    is the only version of this feature worth the click.

    Nothing is sent anywhere by building this string: it becomes an href, and the
    researcher chooses whether to follow it.
    """
    import urllib.parse as _up

    from db import db_query

    def _rows(sql, n=6):
        try:
            return [dict(r) for r in (db_query(sql) or [])][:n]
        except Exception:
            return []

    # `projects` has no `updated_at` — it has `last_session_at` and `created_at`.
    # The first draft ordered by `updated_at`, and db_query swallowed the
    # OperationalError and returned []: the deeplink silently shipped without any
    # projects in it and looked perfectly fine. Caught 2026-08-26 only by reading
    # the generated prompt.
    projects = _rows("SELECT title, COALESCE(next_step,'') AS next_step FROM projects "
                     "WHERE COALESCE(status,'') NOT IN ('archived','done','completed') "
                     "ORDER BY COALESCE(last_session_at, created_at) DESC LIMIT 6")
    ideas = _rows("SELECT text FROM ideas WHERE COALESCE(tags,'') NOT LIKE "
                  "'%archived%' ORDER BY created_at DESC LIMIT 8")
    papers = _rows("SELECT title FROM new_publications ORDER BY discovered_at "
                   "DESC LIMIT 10")
    existing = _rows("SELECT title, keyword_groups FROM focus_areas LIMIT 10", 10)

    L = ["I want to set up a new focus area in Metis — a lens that keeps me current "
         "on one subject.", "",
         "A focus is TWO SUBJECTS CROSSED. It is defined by keyword groups: an item "
         "must mention something from EVERY group. So group 1 might be "
         "{artificial intelligence, machine learning} and group 2 {health, clinical, "
         "epidemiology}.", "",
         "Two things I have learned the hard way about these keywords:",
         "- Keywords match as SUBSTRINGS, so anything shorter than four letters is "
         "dangerous. 'ai' matches 'said' and 'maintain'; 'gis' matches "
         "'radiologists'. Give me words of four letters or more.",
         "- A deliberate stem is fine and useful: 'epidemi' catches both "
         "'epidemiology' and 'epidemic'.", ""]

    if existing:
        L += ["Focus areas I already have (do not duplicate these):"]
        L += [f"- {e['title']}" for e in existing] + [""]
    if projects:
        L += ["Projects I have open:"]
        L += [f"- {p['title']}" + (f" — next: {p['next_step'][:90]}"
                                   if p["next_step"] else "") for p in projects] + [""]
    if ideas:
        L += ["Ideas I have captured recently:"]
        L += [f"- {i['text'][:160]}" for i in ideas] + [""]
    if papers:
        L += ["Papers that reached me lately:"]
        L += [f"- {p['title'][:120]}" for p in papers] + [""]

    L += ["Propose THREE focus areas I could set up, each as:",
          "  Title · one line on what it is for · group 1 keywords · group 2 keywords",
          "",
          "Pick crossings that my own work suggests and that I have not already "
          "covered. Then say which one you would start with, and why. Keep it short "
          "— I am going to paste the keywords straight into a form."]

    return "claude://claude.ai/new?q=" + _up.quote("\n".join(L)[:7000], safe="")


@router.get("/focus", response_class=HTMLResponse)
async def focus_index(request: Request):
    from main import templates
    F = _f()
    areas = F.list_focus()
    enriched = []
    for a in areas:
        t = F.focus_thinking(a["slug"])
        enriched.append({**a,
                         "n_news": len(F.focus_news(a["slug"], limit=500)),
                         "n_reading": len(F.focus_reading(a["slug"], limit=500)),
                         "n_thinking": len(t["notes"]) + len(t["ideas"])})
    return templates.TemplateResponse(request, "focus_index.html", {
        "active_tab": "focus-index",
        "areas": enriched,
        "n_active": sum(1 for a in areas if a["state"] == "active"),
        "max_shelf": F.MAX_SHELF,
        "layers": _layer_slugs(),
        "suggest_link": _suggest_link(),
    })


def _layer_slugs() -> list[dict]:
    try:
        from db import db_query
        return [dict(r) for r in (db_query(
            "SELECT k.slug, k.name, COUNT(DISTINCT p.source_file) AS docs "
            "FROM knowledge_databases k "
            "LEFT JOIN pdf_chunks p ON p.db_id = k.id "
            "GROUP BY k.slug ORDER BY 3 DESC") or [])]
    except Exception:
        return []


def _parse_group(raw: str) -> list[str]:
    """A comma-separated field becomes one keyword group."""
    return [w.strip().lower() for w in (raw or "").split(",") if w.strip()]


@router.post("/api/focus/preview", response_class=HTMLResponse)
async def preview(request: Request, group1: str = Form(""), group2: str = Form(""),
                  group3: str = Form("")):
    """Live preview of a candidate lens — the answer to blind lens tuning.

    Fires as the form is typed. Before this, the only way to learn a lens caught
    nothing was to create the focus, open the surface and find it empty.
    """
    from main import templates
    F = _f()
    groups = [g for g in (_parse_group(group1), _parse_group(group2),
                          _parse_group(group3)) if g]
    return templates.TemplateResponse(request, "partials/focus_preview.html",
                                      {"p": F.preview_lens(groups) if groups else None})


@router.post("/api/focus/create")
async def create(request: Request, title: str = Form(...), subtitle: str = Form(""),
                 group1: str = Form(""), group2: str = Form(""),
                 group3: str = Form(""), layers: str = Form(""),
                 activate: str = Form("")):
    """Create a focus from the form, then open it."""
    import json as _json
    F = _f()
    groups = [g for g in (_parse_group(group1), _parse_group(group2),
                          _parse_group(group3)) if g]
    if not title.strip() or not groups:
        return RedirectResponse(url="/focus", status_code=302)
    res = await F.create_focus_area(
        title=title.strip(), keyword_groups=_json.dumps(groups),
        subtitle=subtitle.strip(), layers=layers.strip(),
        activate=bool(activate))
    slug = F.slugify(title)
    if F.get_focus(slug):
        return RedirectResponse(url=f"/focus/{slug}", status_code=302)
    log.warning("[focus] create failed: %s", res[0].text[:160])
    return RedirectResponse(url="/focus", status_code=302)


# ---------------------------------------------------------------------------
# The safe — keep, decline, undo
# ---------------------------------------------------------------------------
# Every one of these re-renders the SECTION the click came from, not the page.
# The counts strip is swapped out-of-band alongside it, because a "keep" that
# leaves the header saying 3 while the safe shows 4 teaches the researcher not to
# trust the header.

def _ctx(request, slug):
    """Everything a focus partial can need, built once."""
    F = _f()
    area = F.get_focus(slug)
    news = F.sift(slug, F.focus_news(slug, 120), "news", "title", "brief_id")
    reading = F.sift(slug, F.focus_reading(slug, 120), "reading", "title", "id")
    return {
        "area": area,
        "news": news,
        "reading": reading,
        "counts": F.focus_counts(slug),
        "kept": F.focus_verdicts(slug, "kept"),
        "taste": F.focus_taste(slug),
        "mute_at": F.MUTE_AT,
        "questions": F.focus_questions(slug),
        "thinking": F.focus_thinking(slug),
        "noise": _lens_noise(slug),
        # `corpus` belongs here, not only on the page: the counts strip renders it
        # and the strip is swapped out-of-band on every verdict. Left in the page
        # handler alone, the unknown-layer warning would appear on load and then
        # silently vanish the first time you pressed Keep.
        "corpus": F.focus_corpus(slug),
        "today": datetime.date.today().isoformat(),
    }


def _counts_oob(request, slug, ctx=None):
    """The counts strip, marked for an out-of-band swap."""
    from main import templates
    ctx = ctx or _ctx(request, slug)
    html = templates.get_template("partials/focus_counts.html").render(**ctx)
    return f'<div id="focus-counts" hx-swap-oob="innerHTML">{html}</div>'


@router.post("/api/focus/{slug}/judge", response_class=HTMLResponse)
async def judge_item(request: Request, slug: str, kind: str = Form(...),
                     item_id: str = Form(...), verdict: str = Form(...),
                     title: str = Form(""), url: str = Form("")):
    """Keep an item in the safe, or say it is not for you."""
    from main import templates
    F = _f()
    try:
        F.judge(slug, kind, item_id, verdict, title, url)
    except ValueError:
        pass
    ctx = _ctx(request, slug)
    tpl = "partials/focus_feed.html" if kind == "news" else "partials/focus_reading.html"
    body = templates.get_template(tpl).render(**ctx)
    return HTMLResponse(body + _counts_oob(request, slug, ctx))


@router.post("/api/focus/{slug}/unjudge", response_class=HTMLResponse)
async def unjudge_item(request: Request, slug: str, kind: str = Form(...),
                       item_id: str = Form(...)):
    """Undo a verdict — back to undecided.

    Undo is reachable from two places: the "Judged" fold inside a list, and the
    safe itself. HTMX names the element it is about to swap in the `HX-Target`
    header, so the caller does not have to say which partial it wants — the
    request already carries it, and one source of truth beats two.
    """
    from main import templates
    F = _f()
    F.unjudge(slug, kind, item_id)
    ctx = _ctx(request, slug)
    target = request.headers.get("HX-Target", "")
    tpl = ("partials/focus_safe.html" if target == "focus-safe"
           else "partials/focus_feed.html" if kind == "news"
           else "partials/focus_reading.html")
    body = templates.get_template(tpl).render(**ctx)
    return HTMLResponse(body + _counts_oob(request, slug, ctx))


# ---------------------------------------------------------------------------
# Questions and Explore
# ---------------------------------------------------------------------------
@router.post("/api/focus/{slug}/question", response_class=HTMLResponse)
async def add_question(request: Request, slug: str, text: str = Form(...)):
    """Record a question against this focus.

    Stored as an idea with `idea_type='question'` — the same table, so a question
    the researcher later answers stays findable by idea search whatever happens to
    this surface.
    """
    from db import db_execute
    from main import templates
    if text.strip():
        db_execute(
            "INSERT INTO ideas (idea_id, text, idea_type, tags, created_at, domain) "
            "VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4())[:8], text.strip(), "question", f"focus:{slug}",
             _now(), slug))
    ctx = _ctx(request, slug)
    body = templates.get_template("partials/focus_thinking.html").render(**ctx)
    return HTMLResponse(body + _counts_oob(request, slug, ctx))


@router.post("/api/focus/{slug}/forget", response_class=HTMLResponse)
async def forget_entry(request: Request, slug: str, kind: str = Form(...),
                       entry_id: str = Form(...)):
    """Remove a note, idea or question written on this focus.

    Added 2026-08-26 to close a gap this session opened: questions could be
    asked and never removed. Shipping a control that creates rows without one
    that removes them leaves the researcher stuck with his own typos.

    Extended to notes and ideas for the same reason, and scoped so it cannot
    reach further than this surface: the WHERE clause requires the row to carry
    this focus's tag. A note written somewhere else that happens to share an id
    is not this surface's to delete.
    """
    from db import db_execute
    from main import templates
    tag = f"%focus:{slug}%"
    if kind == "note":
        db_execute("DELETE FROM personal_notes WHERE note_id = ? "
                   "AND COALESCE(tags,'') LIKE ?", (entry_id, tag))
    else:
        db_execute("DELETE FROM ideas WHERE idea_id = ? "
                   "AND COALESCE(tags,'') LIKE ?", (entry_id, tag))
    ctx = _ctx(request, slug)
    body = templates.get_template("partials/focus_thinking.html").render(**ctx)
    return HTMLResponse(body + _counts_oob(request, slug, ctx))


def _ask_claude_link(title: str, body: str) -> str:
    """A deeplink that carries the material, so nothing has to be retyped."""
    import urllib.parse as _up
    prompt = f"{title}\n\n{body}"[:6000]
    return "claude://claude.ai/new?q=" + _up.quote(prompt, safe="")


@router.post("/api/focus/{slug}/explore", response_class=HTMLResponse)
async def explore_question(request: Request, slug: str, question: str = Form(...)):
    """Answer a question from this focus's own corpus, literature and thinking.

    Retrieval only. The dashboard composes nothing — see the docstring on
    `focus.explore` for why that division is the honest one.
    """
    from main import templates
    F = _f()
    area = F.get_focus(slug)
    result = F.explore(slug, question, limit=6)

    lines = [f"Question on my focus area \"{area['title']}\": {question}", ""]
    if result["passages"]:
        lines += ["From my indexed corpus:"]
        lines += [f"- {p['title'] or p['source_file']} (p.{p['page_start']}): "
                  f"{(p['chunk_text'] or '')[:300]}" for p in result["passages"][:4]]
    if result["papers"]:
        lines += ["", "Papers in my library:"]
        lines += [f"- {r['title']}" + (f" (doi:{r['doi']})" if r.get("doi") else "")
                  for r in result["papers"][:5]]
    if result["ideas"] or result["notes"]:
        lines += ["", "What I already wrote:"]
        lines += [f"- {i['text'][:200]}" for i in result["ideas"][:4]]
        lines += [f"- {n['title'] or n['content'][:200]}" for n in result["notes"][:4]]
    lines += ["", "Answer using this material. Say clearly which parts my own "
              "sources support and which they do not."]

    return templates.TemplateResponse(request, "partials/focus_explore.html", {
        "area": area,
        "result": result,
        "deeplink": _ask_claude_link("", "\n".join(lines)),
    })


# ---------------------------------------------------------------------------
# The brief
# ---------------------------------------------------------------------------
@router.post("/api/focus/{slug}/brief", response_class=HTMLResponse)
async def generate_brief(request: Request, slug: str):
    """Assemble a brief for this focus and keep it."""
    from main import templates
    F = _f()
    area = F.get_focus(slug)
    body = F.build_brief(slug)
    p = F.focus_pulse(slug)
    F.save_brief(slug, body, p.get("total_news", 0), p.get("total_reading", 0))
    return templates.TemplateResponse(request, "partials/focus_brief.html", {
        "area": area,
        "brief": F.latest_brief(slug),
        "deeplink": _ask_claude_link(
            "", f"Here is today's brief on my focus area \"{area['title']}\". "
                f"Write it up as a short narrative I can read in two minutes, and "
                f"tell me what you think I should look at first.\n\n{body}"),
    })


# ---------------------------------------------------------------------------
# Lens diagnosis
# ---------------------------------------------------------------------------
# Why this lives here and not in the lens itself: changing how the lens MATCHES
# would change what every existing focus contains, silently, without the
# researcher asking for it. So the surface reports the problem with a number and
# leaves the decision where it belongs. Measured 2026-08-26 on the AI-in-health
# lens: 70 of 388 briefs (18%) matched only inside longer words — 'ai' in
# "saison", 'gis' in "radiologists", 'gis' in "législateur".
def _lens_noise(slug: str) -> dict:
    """How much of this lens's catch is substring accident rather than subject."""
    import re as _re
    F = _f()
    f = F.get_focus(slug)
    if not f:
        return {}
    groups = F._groups(f)
    if not groups:
        return {}
    items = F.focus_news(slug, 400)
    if not items:
        return {}

    def _boundary(kw, text):
        return _re.search(r"\b" + _re.escape(kw.lower()), text) is not None

    bad, examples = 0, []
    for it in items:
        blob = f"{it['title']} {it.get('summary') or ''}".lower()
        if all(any(_boundary(k, blob) for k in g) for g in groups):
            continue
        bad += 1
        if len(examples) < 4:
            for g in groups:
                for k in g:
                    k = k.lower()
                    if k in blob and not _boundary(k, blob):
                        m = _re.search(r"\w*" + _re.escape(k) + r"\w*", blob)
                        if m and m.group(0) != k:
                            examples.append({"kw": k, "word": m.group(0)})
                            break
                else:
                    continue
                break
    seen, uniq = set(), []
    for e in examples:
        if e["kw"] not in seen:
            seen.add(e["kw"])
            uniq.append(e)
    return {"total": len(items), "false_positives": bad,
            "pct": round(100 * bad / len(items)), "examples": uniq}
