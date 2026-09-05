"""The reading stack — one triage store for everything that arrives.

WHY THIS EXISTS
    The researcher, 2026-08-26: "The today page is really to see what is new, open them if
    I want to see them straight away but often that they get categorized for
    future reading so they become a stack of things to read connected to the
    News and Library surfaces."

    That is one idea, and before this it had three different implementations and
    one hole:
      · papers   — `new_publications.added_at / dismissed_at / read_at`, with
                   working routes on the Library surface
      · focus    — `focus_verdict`, built earlier today, kept/declined per lens
      · news     — NOTHING. Seven tabs, 337 links, zero actions. The News surface
                   was entirely read-only, which is why it felt like clicking did
                   nothing: the links go out to the web, and nothing you do on the
                   page leaves a trace in Metis.

    A reading stack that only knows about papers is not a reading stack. So the
    state lives here, once, for every kind of thing that can arrive.

WRITE-THROUGH, NOT DUPLICATION
    `new_publications` already owns three of these states and the Library surface
    reads those columns directly. If this table shadowed them, the two surfaces
    would disagree the first time either was used alone. So a paper's verdict is
    written HERE and mirrored back to the columns that own it. One store to read
    from, no surface left stale.

THE FIVE VERBS
    saved     keep it — for papers, that means add it to the library
    later     the stack: read it, but not now. The state the researcher actually asked for
              and the one nothing implemented.
    dismissed seen, and cleared, without filing it anywhere. Asked for 2026-09-05:
              "still my interest but I do not want to read it now nor put in my
              stack or library."

              THIS IS NOT `declined`, AND THE DIFFERENCE IS NOT COSMETIC.
              `declined` is a statement about the SUBJECT — it does not interest
              me — and it is the only verdict that should ever be read as
              negative evidence about what to show next. `dismissed` is a
              statement about THIS ITEM ON THIS DAY. The subject still counts.
              Collapsing the two would teach the ranker that a topic is unwanted
              every time a busy morning cleared the queue, which is the fastest
              way to make a relevance model wrong about someone.

              It is also not `later`: the stack is a promise to read, and a
              promise nobody meant is what makes a stack stop being believed.
    declined  not interested. Demoted and folded, never deleted — same rule the
              focus safe follows, for the same reason: an absence you were never
              told about cannot be audited.
    read      done with it
"""
from __future__ import annotations

import re
from datetime import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# Order is the reading order of the verdict strip, and `dismissed` sits between
# the two it must not be confused with: it clears the row like `declined` but
# says nothing against the subject, and it is not the promise `later` makes.
STATES = ("saved", "later", "dismissed", "declined", "read")

# The verdicts that mean "this is behind me" — the set that clears an item from
# every unjudged queue. Named once, because the queue that forgot to include a
# verb is exactly the bug this constant exists to prevent: the field digest
# excluded only ('read','declined'), so pressing Stack left the row in place.
JUDGED = ("read", "declined", "dismissed", "later", "saved")

# The verdicts that carry NEGATIVE evidence about a subject. Only one does.
NEGATIVE = ("declined",)
KINDS = ("news", "paper")

# Kept in step with `system/installer/schema.sql`, the only mechanism that
# carries a schema change to the other computer on its own.
_DDL = """
CREATE TABLE IF NOT EXISTS reading_stack (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT NOT NULL,          -- 'news' | 'paper'
    item_id    TEXT NOT NULL,
    state      TEXT NOT NULL,          -- saved | later | dismissed | declined | read
    title      TEXT DEFAULT '',
    url        TEXT DEFAULT '',
    source     TEXT DEFAULT '',
    tags       TEXT DEFAULT '',
    note       TEXT DEFAULT '',
    added_at   TEXT NOT NULL,
    state_at   TEXT NOT NULL,
    UNIQUE(kind, item_id)
)
"""


def ensure_schema(con) -> None:
    con.execute(_DDL)
    con.execute("CREATE INDEX IF NOT EXISTS idx_stack_state "
                "ON reading_stack(state, state_at)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_stack_kind "
                "ON reading_stack(kind, item_id)")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean_tags(raw: str) -> str:
    """Normalise a tag string: lowercase, comma-separated, de-duplicated.

    Tags are stored as text rather than a join table on purpose. There is one
    user and a few hundred items; a join table would buy nothing and cost every
    read a second query. If this ever grows a tag browser with counts across
    100k rows, revisit it then and not before.
    """
    parts = [t.strip().lower() for t in re.split(r"[,;]", raw or "") if t.strip()]
    out: list[str] = []
    for t in parts:
        t = re.sub(r"\s+", " ", t)[:40]
        if t not in out:
            out.append(t)
    return ", ".join(out[:12])


# ---------------------------------------------------------------------------
# Reading and writing one item's state
# ---------------------------------------------------------------------------
def _twins(con, kind: str, item_id: str) -> list:
    """Other rows that are the SAME STORY under a different id.

    Measured 2026-08-26: `news_briefs` holds 3,734 rows, of which 17 stories
    appear more than once — 22 redundant rows. Different feeds carry the same
    wire copy, and each arrival gets its own `brief_id`.

    That matters here and nowhere else. A verdict is keyed on the id, so
    declining one copy left its twin unjudged and it came straight back — which
    reads as the button not working. Deduplicating upstream is the better fix and
    is not this module's to make; what this module can do is make one judgement
    cover the whole story.

    Titles are compared lowercased and trimmed, deliberately conservatively. A
    fuzzier match would fold together stories that merely share a headline
    pattern ("Green forest fire notification in Angola" / "...in Australia" are
    genuinely different events, and differ only in the last word).
    """
    if kind != "news":
        return []
    try:
        row = con.execute("SELECT title FROM news_briefs WHERE brief_id = ?",
                          (item_id,)).fetchone()
        if not row or not (row["title"] or "").strip():
            return []
        return [r["brief_id"] for r in con.execute(
            "SELECT brief_id FROM news_briefs "
            "WHERE LOWER(TRIM(title)) = LOWER(TRIM(?)) AND brief_id != ?",
            (row["title"], item_id))]
    except Exception:
        return []


def get_state(kind: str, item_id: str) -> dict:
    with connect(paths.db) as con:
        ensure_schema(con)
        r = con.execute("SELECT * FROM reading_stack WHERE kind=? AND item_id=?",
                        (kind, str(item_id))).fetchone()
        return dict(r) if r else {}


def states_for(kind: str, ids: list) -> dict:
    """State for many items at once — one query, not one per card.

    The news grid renders 60 cards. A per-card lookup would be 60 round trips to
    decide which button to draw.
    """
    ids = [str(i) for i in ids if str(i or "")]
    if not ids:
        return {}
    q = ",".join("?" * len(ids))
    with connect(paths.db) as con:
        ensure_schema(con)
        return {r["item_id"]: dict(r) for r in con.execute(
            f"SELECT * FROM reading_stack WHERE kind=? AND item_id IN ({q})",
            tuple([kind] + ids))}


def describe(kind: str, item_id: str) -> dict:
    """Title, url and source for an item, read from the table that owns it.

    The action bar used to POST all three back with every click, as six hidden
    inputs on every row. On a 60-item news tab that is the same strings sent to
    the server that had just sent them — measured at roughly 100 KB of the tab's
    weight, for data already sitting in the database.

    A control now carries only what the server cannot know: which item, and what
    the reader decided. Anything the caller DOES pass still wins, so an item that
    lives nowhere (a link pasted from Claude Desktop) can still be filed.
    """
    try:
        with connect(paths.db) as con:
            if kind == "news":
                r = con.execute(
                    "SELECT title, COALESCE(source_url,'') AS url, "
                    "COALESCE(domain,'') AS source FROM news_briefs "
                    "WHERE brief_id = ?", (item_id,)).fetchone()
            else:
                r = con.execute(
                    "SELECT title, COALESCE(NULLIF(source_url,''), "
                    "  CASE WHEN COALESCE(doi,'') != '' "
                    "       THEN 'https://doi.org/' || doi ELSE '' END) AS url, "
                    "COALESCE(journal,'') AS source FROM new_publications "
                    "WHERE id = ?", (item_id,)).fetchone()
            return dict(r) if r else {}
    except Exception:
        return {}


def set_state(kind: str, item_id: str, state: str, title: str = "",
              url: str = "", source: str = "", tags: str = "") -> dict:
    """Record a verdict. Re-stating replaces, so nothing is ever stranded."""
    if state not in STATES:
        raise ValueError(f"state must be one of {STATES}, got {state!r}")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    item_id = str(item_id)
    now = _now()
    # Fill in from the owning table anything the caller did not send.
    if not (title and url and source):
        d = describe(kind, item_id)
        title = title or d.get("title") or ""
        url = url or d.get("url") or ""
        source = source or d.get("source") or ""
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute(
            "INSERT INTO reading_stack (kind, item_id, state, title, url, source, "
            "tags, added_at, state_at) VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(kind, item_id) DO UPDATE SET "
            "state=excluded.state, state_at=excluded.state_at, "
            # Keep whatever we already knew if the caller sends nothing — a
            # button that only carries an id must not blank the title.
            "title=CASE WHEN excluded.title != '' THEN excluded.title ELSE reading_stack.title END, "
            "url=CASE WHEN excluded.url != '' THEN excluded.url ELSE reading_stack.url END, "
            "source=CASE WHEN excluded.source != '' THEN excluded.source ELSE reading_stack.source END, "
            "tags=CASE WHEN excluded.tags != '' THEN excluded.tags ELSE reading_stack.tags END",
            (kind, item_id, state, title[:400], url[:800], source[:120],
             _clean_tags(tags), now, now))
        _write_through(con, kind, item_id, state, now)

        # The same story under another id gets the same verdict, or declining a
        # headline leaves its twin in the feed and the button looks broken.
        for twin in _twins(con, kind, item_id):
            con.execute(
                "INSERT INTO reading_stack (kind, item_id, state, title, url, "
                "source, tags, added_at, state_at) VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(kind, item_id) DO UPDATE SET "
                "state=excluded.state, state_at=excluded.state_at",
                (kind, twin, state, title[:400], url[:800], source[:120],
                 _clean_tags(tags), now, now))
    return get_state(kind, item_id)


def clear_state(kind: str, item_id: str) -> None:
    """Back to undecided, including on the table that owns the item."""
    with connect(paths.db) as con:
        ensure_schema(con)
        for iid in [str(item_id)] + _twins(con, kind, str(item_id)):
            con.execute("DELETE FROM reading_stack WHERE kind=? AND item_id=?",
                        (kind, iid))
        if kind == "paper":
            try:
                con.execute("UPDATE new_publications SET dismissed_at='', read_at='' "
                            "WHERE id=?", (item_id,))
            except Exception:
                pass


def _write_through(con, kind: str, item_id: str, state: str, now: str) -> None:
    """Mirror a paper's verdict onto the columns the Library surface reads.

    Without this the two surfaces disagree: mark something read here and the
    Library still shows it unread, because that page queries `read_at` directly
    and has done since long before this table existed. `added_at` is deliberately
    NOT set from `saved` — on this schema that column means "acquired into the
    library", which is a real acquisition with a PDF behind it, and claiming it
    from a one-click save would make the library lie about what it holds.
    """
    if kind != "paper":
        return
    try:
        if state in ("declined", "dismissed"):
            # BOTH clear the row from the Library's new-literature queue, and
            # that is all `new_publications.dismissed_at` has ever meant here:
            # "not in the queue any more". The distinction between "the subject
            # does not interest me" and "not this one, not today" is finer than
            # that column can carry, so it lives in `reading_stack.state` —
            # which is the store the ranker reads. Writing the finer fact into
            # a coarser column is how the two would drift.
            con.execute("UPDATE new_publications SET dismissed_at=? WHERE id=?",
                        (now, item_id))
        elif state == "read":
            con.execute("UPDATE new_publications SET read_at=?, dismissed_at='' "
                        "WHERE id=?", (now, item_id))
        else:  # saved | later — un-dismiss, it is back in play
            con.execute("UPDATE new_publications SET dismissed_at='' WHERE id=?",
                        (item_id,))
    except Exception:
        # The column set differs on an older install; the stack still works.
        pass


def set_tags(kind: str, item_id: str, tags: str) -> dict:
    """Tag an item, creating a `later` row if it had no state yet.

    Tagging something is itself a decision to come back to it, so an untagged,
    unstated item that gets a tag lands in the stack rather than nowhere.
    """
    cur = get_state(kind, item_id)
    if not cur:
        return set_state(kind, item_id, "later", tags=tags)
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute("UPDATE reading_stack SET tags=?, state_at=? "
                    "WHERE kind=? AND item_id=?",
                    (_clean_tags(tags), _now(), kind, str(item_id)))
    return get_state(kind, item_id)


# ---------------------------------------------------------------------------
# Reading the stack
# ---------------------------------------------------------------------------
def stack(state: str = "later", kind: str = "", tag: str = "",
          limit: int = 200) -> list:
    sql = "SELECT * FROM reading_stack WHERE 1=1"
    params: list = []
    if state:
        sql += " AND state = ?"
        params.append(state)
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    if tag:
        sql += " AND ',' || tags || ',' LIKE ?"
        params.append(f"%,{tag.strip().lower()},%")
    sql += " ORDER BY state_at DESC LIMIT ?"
    params.append(limit)
    with connect(paths.db) as con:
        ensure_schema(con)
        return [dict(r) for r in con.execute(sql, tuple(params))]


def counts() -> dict:
    with connect(paths.db) as con:
        ensure_schema(con)
        rows = con.execute("SELECT state, COUNT(*) AS n FROM reading_stack "
                           "GROUP BY state").fetchall()
    out = {s: 0 for s in STATES}
    for r in rows:
        out[r["state"]] = r["n"]
    out["total"] = sum(out[s] for s in STATES)
    return out


def all_tags() -> list:
    """Every tag in use, with counts, most used first."""
    tally: dict = {}
    with connect(paths.db) as con:
        ensure_schema(con)
        for r in con.execute("SELECT tags FROM reading_stack "
                             "WHERE COALESCE(tags,'') != ''"):
            for t in (r["tags"] or "").split(","):
                t = t.strip()
                if t:
                    tally[t] = tally.get(t, 0) + 1
    return sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))


# ---------------------------------------------------------------------------
# MCP tools — the same stack from Claude Desktop
# ---------------------------------------------------------------------------
@app.tool()
async def reading_stack_show(state: str = "later", tag: str = "") -> list[TextContent]:
    """What is in the reading stack: saved, later, declined or read."""
    items = stack(state=state, tag=tag, limit=60)
    c = counts()
    head = (f"# Reading stack — {state}\n\n"
            f"{c['later']} to read · {c['saved']} saved · {c['read']} read · "
            f"{c['declined']} declined\n")
    if not items:
        return [TextContent(type="text", text=head + "\nNothing here.")]
    lines = [head]
    for i in items:
        bits = [f"- [{i['kind']}] {i['title'][:130]}"]
        if i["tags"]:
            bits.append(f"  tags: {i['tags']}")
        if i["url"]:
            bits.append(f"  <{i['url']}>")
        lines.append("\n".join(bits))
    tags = all_tags()
    if tags:
        lines.append("\n## Tags\n" + ", ".join(f"{t} ({n})" for t, n in tags[:20]))
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def reading_stack_add(title: str, kind: str = "news", item_id: str = "",
                            state: str = "later", url: str = "",
                            tags: str = "") -> list[TextContent]:
    """Put something in the reading stack, or change what state it is in."""
    if not item_id:
        item_id = "ext-" + re.sub(r"[^a-z0-9]+", "-", title.lower())[:48]
    try:
        r = set_state(kind, item_id, state, title, url, "", tags)
    except ValueError as e:
        return [TextContent(type="text", text=str(e))]
    c = counts()
    return [TextContent(type="text", text=(
        f"**{state}** — {r.get('title', title)[:120]}"
        + (f"\ntags: {r['tags']}" if r.get("tags") else "")
        + f"\n\n{c['later']} to read · {c['saved']} saved."))]
