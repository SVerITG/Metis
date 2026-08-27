"""ui.py — the shared presentation primitives the dashboard was missing.

WHY THIS EXISTS
    Audited 2026-08-25. The Today surface rendered 14 panels, 4,894 visible words
    and roughly 19.6 screens in one column, with no collapse anywhere — there were
    exactly four `<details>` elements in the whole application. Every panel showed
    everything it had because there was no established way to show less.

    Three primitives fix that, and they belong in one place so the vocabulary
    stays consistent as panels are added:

      peek()        a list shows 3-5 items and a control for the rest
      delta_count() a number you can act on today, not a total that only grows
      nothing()     an empty panel occupies no space at all

THE COUNTER RULE
    The news rail said "1491 NEW" and literature "1433 UNREAD". A number that can
    only go up stops being information the moment it passes what a person could
    act on; after that its only job is to make the surface feel like a debt. So
    the surface shows what arrived since the last visit, and the total moves
    behind the expand where it belongs.

THE EMPTY RULE
    `learning-nudge` rendered zero words inside a full-height wrapper and
    `system-health` rendered sixteen. A panel that holds its slot while saying
    nothing teaches the reader to skip that region of the page — a habit that
    then applies on the days it does have something. Empty renders nothing.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import uuid as _uuid

from db import db_execute, db_query, db_scalar

# ── empty ────────────────────────────────────────────────────────────────────

def nothing() -> str:
    """What a panel with nothing to say should render.

    HTMX swaps this in with `outerHTML`, so the placeholder div is replaced by
    an empty comment and the panel leaves no gap. A zero-height element rather
    than a styled "nothing here yet" box is the point.
    """
    return "<!--empty-->"


# ── seen markers, for honest deltas ──────────────────────────────────────────

_SEEN_DDL = """
CREATE TABLE IF NOT EXISTS ui_seen (
    key      TEXT PRIMARY KEY,
    seen_at  TEXT NOT NULL
)
"""


def last_seen(key: str) -> str:
    """When this surface was last looked at, ISO, or '' the first time."""
    try:
        db_execute(_SEEN_DDL)
        return db_scalar("SELECT seen_at FROM ui_seen WHERE key=?", (key,), default="") or ""
    except Exception:
        return ""


def mark_seen(key: str) -> None:
    try:
        db_execute(_SEEN_DDL)
        db_execute(
            "INSERT INTO ui_seen (key, seen_at) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET seen_at=excluded.seen_at",
            (key, _dt.datetime.now().isoformat(timespec="seconds")),
        )
    except Exception:
        pass


def since_label(iso: str) -> str:
    """'since Friday' / 'since yesterday' / 'in the last hour' — never a raw date.

    A delta is only useful if the reader knows what it is a delta FROM, and a
    timestamp makes them do arithmetic. Words do not.
    """
    if not iso:
        return "so far"
    try:
        then = _dt.datetime.fromisoformat(iso)
    except ValueError:
        return "so far"
    now = _dt.datetime.now()
    secs = (now - then).total_seconds()
    if secs < 3600:
        return "in the last hour"
    if secs < 8 * 3600:
        return "since this morning"
    days = (now.date() - then.date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "since yesterday"
    if days < 7:
        return f"since {then.strftime('%A')}"
    if days < 30:
        return f"in {days} days"
    return "in a while"


def delta_count(key: str, total: int, newer: int) -> str:
    """The count line for a list panel: a delta first, the total demoted."""
    when = since_label(last_seen(key))
    if newer > 0:
        head = (f'<span class="ui-delta">{newer} {_html.escape(when)}</span>')
    else:
        head = f'<span class="ui-delta ui-delta--quiet">nothing new {_html.escape(when)}</span>'
    if total > newer:
        head += f'<span class="ui-total">{total:,} in all</span>'
    return head


# ── peek / expand ────────────────────────────────────────────────────────────

def peek(items: list[str], key: str, limit: int = 5,
         more_label: str = "more", collapsed_note: str = "") -> str:
    """Show the first `limit` items; put the rest behind one control.

    `items` are pre-rendered HTML strings. The open/closed state is remembered
    per `key` in localStorage, so the shape of the page is the reader's and
    survives a reload — a panel that re-expands on every visit is not collapsed,
    it is annoying.

    Never produces an inner scrollbar. A scroll region inside a page that also
    scrolls is the thing the audit was called about.
    """
    if not items:
        return ""
    head, tail = items[:limit], items[limit:]
    out = ['<div class="ui-peek" data-peek-key="%s">' % _html.escape(key, quote=True)]
    out.append('<div class="ui-peek-head">')
    out.extend(head)
    out.append("</div>")
    if tail:
        gid = "peek-" + _uuid.uuid4().hex[:8]
        note = f' · {_html.escape(collapsed_note)}' if collapsed_note else ""
        out.append(f'<div class="ui-peek-rest" id="{gid}" hidden>')
        out.extend(tail)
        out.append("</div>")
        out.append(
            f'<button type="button" class="ui-peek-toggle" aria-expanded="false" '
            f'aria-controls="{gid}" data-peek-count="{len(tail)}" '
            f'data-peek-more="{len(tail)} {_html.escape(more_label, quote=True)}">'
            f'<span class="ui-chev" aria-hidden="true">▸</span>'
            f'<span class="ui-peek-text">{len(tail)} {_html.escape(more_label)}{note}</span>'
            f"</button>"
        )
    out.append("</div>")
    return "".join(out)


def zone(title: str, body: str, key: str, tail: str = "",
         open_by_default: bool = False) -> str:
    """A whole panel that can be folded away, remembered per `key`.

    Used for the groups the audit found were answering one question in four
    places. The summary line stays visible when closed, so folding a zone costs
    the reader nothing — it is the detail that hides, never the fact.
    """
    if not body:
        return nothing()
    gid = "zone-" + _uuid.uuid4().hex[:8]
    op = "true" if open_by_default else "false"
    chev = "▾" if open_by_default else "▸"
    hidden = "" if open_by_default else " hidden"
    return (
        f'<section class="ui-zone" data-zone-key="{_html.escape(key, quote=True)}">'
        f'<button type="button" class="ui-zone-head" aria-expanded="{op}" aria-controls="{gid}">'
        f'<span class="ui-chev" aria-hidden="true">{chev}</span>'
        f'<span class="ui-zone-title">{_html.escape(title)}</span>'
        f'{f"<span class=ui-zone-tail>{tail}</span>" if tail else ""}'
        f"</button>"
        f'<div class="ui-zone-body" id="{gid}"{hidden}>{body}</div>'
        f"</section>"
    )


def count_since(table: str, ts_col: str, iso: str, where: str = "") -> int:
    """How many rows in `table` are newer than `iso`. 0 on any problem —
    a delta that errors should read as 'nothing new', never crash the panel."""
    if not iso:
        return 0
    clause = f" AND {where}" if where else ""
    try:
        return int(db_scalar(
            f"SELECT COUNT(*) FROM {table} WHERE {ts_col} > ?{clause}", (iso,), default=0) or 0)
    except Exception:
        return 0


# ── "what changed since I last looked", for any surface ─────────────────────
# The last item from the design audit: Today answered this, News, Library and
# Work each answered it differently or not at all — and the machinery to answer
# it properly (`ui_seen`, `count_since`, `since_label`) had been sitting here
# used by one surface since it was written.
#
# THE RULE THIS ENCODES. The delta leads and the total is demoted, because a
# number that only grows stops being information past the point a person can act
# on it. 1,433 unread papers is not a call to action; 6 since Friday is.
#
# `mark_seen` is deliberately NOT called on render. A surface that marks itself
# read by being looked at can never tell you what you missed — which was the
# original news-rail bug, where 859 briefs showed the same items every visit
# because nothing recorded the visit, and the naive fix (stamp on render) would
# have hidden them all instead.

def whats_new(key: str, table: str, ts_col: str, where: str = "") -> dict:
    """How much has arrived in `table` since this surface was last marked seen."""
    since = last_seen(key)
    # `count_since("")` returns 0 by design — an empty timestamp means "no delta
    # to compute", not "count everything". The total needs its own query.
    clause = f" WHERE {where}" if where else ""
    try:
        total = int(db_scalar(f"SELECT COUNT(*) FROM {table}{clause}", default=0) or 0)
    except Exception:
        total = 0
    newer = count_since(table, ts_col, since, where) if since else total
    return {
        "key": key,
        "since": since,
        "when": since_label(since),
        "newer": newer,
        "total": total,
        "first_visit": not since,
    }


def clip(text, n: int = 120, ellipsis: str = "…") -> str:
    """Shorten to `n` characters, cutting at a WORD boundary.

    Lives here rather than in main.py because truncation happens on BOTH sides:
    templates slice with `{{ title[:80] }}` and routers slice with
    `(t.get("content") or "")[:45]`. Two implementations would drift, and the
    router half is the one that produced the worst example on the Reflection
    surface — "Memory write-backs belong on the tool-dispatc".

    Backs up to the last space inside the limit, unless that would throw away
    more than 40% of the text (a single very long word). The ellipsis is added
    only when something was actually removed: a string exactly at the limit
    should not claim to continue.
    """
    if text is None:
        return ""
    t = str(text)
    if len(t) <= n:
        return t
    cut = t[:n]
    space = cut.rfind(" ")
    if space > n * 0.6:
        cut = cut[:space]
    return cut.rstrip(" ,;:.-–—") + ellipsis
