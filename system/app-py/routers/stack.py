"""The reading stack, on the dashboard.

Every route here re-renders the SECTION the click came from and swaps the stack
counters out-of-band alongside it. A "read later" that leaves the header saying
3 while the stack holds 4 teaches the researcher not to trust the header, and a
counter nobody trusts is worse than no counter.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
log = logging.getLogger("metis.stack")


def _s():
    """Import lazily so a broken MCP tree cannot stop the dashboard booting."""
    from metis_mcp.tools import stack as S
    return S


def _counts_oob() -> str:
    """The stack counters, marked for an out-of-band swap.

    Rendered as a bare string rather than a template because it is three numbers
    and a link; a partial file for that would be indirection with no payoff.
    """
    S = _s()
    c = S.counts()
    return (
        f'<span id="stack-counts" hx-swap-oob="outerHTML" class="stk-counts">'
        f'<a href="/stack" class="stk-link" title="Everything you filed for later">'
        f'<b>{c["later"]}</b> to read</a>'
        f'<span class="stk-sep">·</span>'
        f'<a href="/stack?state=saved" class="stk-link"><b>{c["saved"]}</b> saved</a>'
        f'</span>')


async def _rerender(request: Request, back: str, ctx_extra: dict | None = None) -> str:
    """Re-render whichever list the click came from.

    `back` names the surface, not the template, so a caller says where it is
    rather than knowing how that place is built.
    """
    from routers import today as T
    if back.startswith("news:"):
        parts = back.split(":")
        tab = parts[1] if len(parts) > 1 and parts[1] else "overview"
        period = parts[2] if len(parts) > 2 and parts[2] else "week"
        view = parts[3] if len(parts) > 3 and parts[3] else "detailed"
        return T.render_news_tab(request, tab, period, view)
    if back == "stack":
        return render_stack_body(request, **(ctx_extra or {}))
    if back == "today-news":
        return await T.render_news_rail(request)
    if back == "today-lit":
        return await T.render_literature_discovery(request)
    if back.startswith("lit-row:"):
        from routers import new_literature as L
        return await L.render_row(request, back.split(":", 1)[1])
    if back == "library":
        from routers import new_literature as L
        return (await L.new_literature_panel(request)).body.decode("utf-8")
    return ""


@router.post("/api/stack/set", response_class=HTMLResponse)
async def stack_set(request: Request, kind: str = Form(...), item_id: str = Form(...),
                    state: str = Form(...), title: str = Form(""),
                    url: str = Form(""), source: str = Form(""),
                    back: str = Form("")):
    """Save / read later / read / not for me."""
    S = _s()
    try:
        S.set_state(kind, item_id, state, title, url, source)
    except ValueError as e:
        log.warning("[stack] %s", e)
    body = await _rerender(request, back or _guess_back(request))
    return HTMLResponse(body + _counts_oob())


@router.post("/api/stack/clear", response_class=HTMLResponse)
async def stack_clear(request: Request, kind: str = Form(...),
                      item_id: str = Form(...), back: str = Form("")):
    S = _s()
    S.clear_state(kind, item_id)
    body = await _rerender(request, back or _guess_back(request))
    return HTMLResponse(body + _counts_oob())


@router.post("/api/stack/tags", response_class=HTMLResponse)
async def stack_tags(request: Request, kind: str = Form(...), item_id: str = Form(...),
                     tags: str = Form(""), title: str = Form(""),
                     url: str = Form(""), back: str = Form("")):
    S = _s()
    if title and not S.get_state(kind, item_id):
        S.set_state(kind, item_id, "later", title, url)
    S.set_tags(kind, item_id, tags)
    body = await _rerender(request, back or _guess_back(request))
    return HTMLResponse(body + _counts_oob())


def _guess_back(request: Request) -> str:
    """Fall back to the element HTMX is about to swap.

    Every triage button sets `hx-target`, and HTMX sends its id in `HX-Target`.
    That means a caller that forgets `back` still re-renders the right list
    instead of blanking it — one source of truth, already on the request.
    """
    t = request.headers.get("HX-Target", "")
    if t == "news-tab-body":
        # HX-Current-URL is the page the click happened on. The tab, period and
        # view live in the swapped body, not the address bar, so they are echoed
        # back by the buttons themselves via `back`; this is the fallback for a
        # control that did not.
        q = request.query_params
        return ":".join(["news", q.get("tab") or "overview",
                         q.get("period") or "week", q.get("view") or "detailed"])
    if t.startswith("nl-row-"):
        return "lit-row:" + t[len("nl-row-"):]
    return {"stack-body": "stack", "news-surface": "today-news",
            "today-lit-discovery": "today-lit",
            "new-literature": "library"}.get(t, "")


# ---------------------------------------------------------------------------
# The stack surface
# ---------------------------------------------------------------------------
def render_stack_body(request: Request, state: str = "later", tag: str = "") -> str:
    from main import templates
    S = _s()
    try:
        import ui as _ui
        wn = _ui.whats_new("stack", "reading_stack", "state_at")
    except Exception:
        wn = None
    return templates.get_template("partials/stack_body.html").render(
        items=S.stack(state=state, tag=tag, limit=300),
        state=state, tag=tag, counts=S.counts(), tags=S.all_tags(),
        whatsnew_stack=wn,
    )


@router.get("/stack", response_class=HTMLResponse)
async def stack_page(request: Request, state: str = "later", tag: str = ""):
    """Everything filed for later, in one place.

    This is the surface the researcher described — the pile the Today page feeds. It is
    NOT a fourth copy of the news list: it reads `reading_stack`, which is the
    only table that knows what he decided about an item.
    """
    from main import templates
    S = _s()
    return templates.TemplateResponse(request, "stack.html", {
        "active_tab": "stack",
        "items": S.stack(state=state, tag=tag, limit=300),
        "state": state,
        "tag": tag,
        "counts": S.counts(),
        "tags": S.all_tags(),
        "whatsnew_stack": (lambda: __import__("ui").whats_new(
            "stack", "reading_stack", "state_at"))(),
    })


@router.get("/api/partial/stack/body", response_class=HTMLResponse)
async def stack_body(request: Request, state: str = "later", tag: str = ""):
    return HTMLResponse(render_stack_body(request, state, tag))


@router.get("/api/partial/stack/nav-meta", response_class=HTMLResponse)
async def stack_nav_meta():
    """The navbar badge: how many things are waiting to be read.

    Note the belt-and-braces attributes on the element that calls this, in
    base.html — hx-target="this", hx-select="unset", hx-push-url="false". The
    nav items carry hx-disinherit="*" which already covers it, but this badge is
    the second self-fetching child in the navbar, and the FIRST one silently
    rewrote the address bar to /learning for weeks (fixed 2026-08-26). A repeat
    of that bug is not worth saving three attributes.
    """
    S = _s()
    c = S.counts()
    return HTMLResponse(f"{c['later']}" if c["later"] else "—")


# ---------------------------------------------------------------------------
# "Seen" markers, for any surface
# ---------------------------------------------------------------------------
_SEEN_SURFACES = {
    # key            → (what to re-render afterwards)
    "news":    "news",
    "library": "library",
    "stack":   "stack",
    "work":    "work",
}


@router.post("/api/seen/{key}", response_class=HTMLResponse)
async def mark_surface_seen(request: Request, key: str):
    """Mark a surface as looked at, then give back whatever it was showing.

    Marking is an ACT, never a side effect of rendering. A surface that stamps
    itself seen because you opened it can never tell you what you missed — which
    is exactly how the news rail once showed the same 859 briefs every visit.
    """
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    import ui
    if key.split(":")[0] not in _SEEN_SURFACES:
        return HTMLResponse("", status_code=204)
    ui.mark_seen(key)
    body = await _rerender(request, _guess_back(request))
    return HTMLResponse(body + _counts_oob())
