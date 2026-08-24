"""focus.py — a focus area is a LENS, not a container.

WHAT THIS IS FOR
    the researcher, 2026-08-24: the "AI in Public Health course" turned out not to be a
    course. A course has an end; an ongoing interest does not. What he actually
    wanted was a surface that stays current on one subject — news, literature,
    an overview, and somewhere to put notes and ideas — and that can be pushed
    onto a shelf while it is live and taken off again when attention moves.

THE ARCHITECTURAL DECISION THAT MATTERS
    **A focus owns no content.** It owns a definition of a query.

    Every piece of content a focus shows already lives in a table that owns it:
    news in `news_briefs`, papers in `new_publications`, thinking in `ideas` and
    `personal_notes`, documents in `pdf_chunks`. The focus contributes only the
    lens through which they are read, plus a tag (`focus:<slug>`) on anything
    written while looking through it.

    That is what makes the question "what happens when I remove it?" have a good
    answer: **removing a lens cannot remove what you saw through it.** Archiving
    a focus leaves every note, idea, paper and brief exactly where it was, still
    tagged, still searchable. Nothing is orphaned because nothing was ever owned.

    The alternative — a focus that holds copies of its items — would make removal
    a data-loss decision, and would put the same paper in two places the moment
    two focuses overlapped. That is a container. This is a lens.

WHY KEYWORD *GROUPS* AND NOT A KEYWORD LIST
    Measured while building this. A flat list for "AI in health" returned
    "An AI job boom", "Can AI ever be conscious?" — real AI news, irrelevant to
    the focus. Because the subject is not one axis, it is a CONJUNCTION: something
    about AI *and* something about health.

    So the lens is a list of groups: OR within a group, AND across groups.
    Precision went from 56 loose news matches to 7 that are all genuinely on
    subject ("FDA plans to regulate generative AI", "AI model helps clinicians
    detect heart obstruction"). Recall drops, and that is the correct trade for a
    surface you open every day — a focus feed you have to filter by eye is a feed
    you stop opening.

THE THREE STATES
    active     on the shelf, in the navbar, refreshed on schedule. Max 3, because
               a shelf with ten things on it is not a focus.
    following  defined and queryable, off the navbar. Attention has moved but the
               lens is worth keeping.
    archived   read-only, no refresh, still openable. Never deleted — the
               definition is cheap and the history is the point.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

MAX_SHELF = 3          # a shelf with ten things on it is not a focus
STATES = ("active", "following", "archived")

# Kept in step with `system/installer/schema.sql`, which is the only mechanism
# that carries a schema change to the other computer on its own (2026-08-24).
_DDL = """
CREATE TABLE IF NOT EXISTS focus_areas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    slug              TEXT NOT NULL UNIQUE,
    title             TEXT NOT NULL,
    subtitle          TEXT DEFAULT '',
    state             TEXT DEFAULT 'following',
    shelf_slot        INTEGER,
    keyword_groups    TEXT DEFAULT '[]',
    layers            TEXT DEFAULT '',
    overview          TEXT DEFAULT '',
    created_at        TEXT NOT NULL,
    activated_at      TEXT DEFAULT '',
    archived_at       TEXT DEFAULT '',
    last_visited_at   TEXT DEFAULT '',
    last_refreshed_at TEXT DEFAULT ''
)
"""


def ensure_schema(con) -> None:
    con.execute(_DDL)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_focus_slug "
                "ON focus_areas(slug)")


def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")[:60]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# The lens
# ---------------------------------------------------------------------------
def _groups(row) -> list[list[str]]:
    try:
        g = json.loads(row["keyword_groups"] or "[]")
        return [[str(x).lower() for x in grp if str(x).strip()] for grp in g if grp]
    except Exception:
        return []


def lens_sql(groups: list[list[str]], expr: str) -> tuple[str, list]:
    """AND across groups, OR within. Returns (sql_fragment, params).

    An empty lens matches nothing rather than everything: a focus with no
    definition showing the entire library would look like a working surface and
    be pure noise.
    """
    if not groups:
        return "0", []
    parts, params = [], []
    for grp in groups:
        parts.append("(" + " OR ".join(f"lower({expr}) LIKE ?" for _ in grp) + ")")
        params += [f"%{k}%" for k in grp]
    return " AND ".join(parts), params


def get_focus(slug: str) -> dict | None:
    with connect(paths.db) as con:
        ensure_schema(con)
        r = con.execute("SELECT * FROM focus_areas WHERE slug = ?", (slug,)).fetchone()
        return dict(r) if r else None


def list_focus(state: str = "") -> list[dict]:
    with connect(paths.db) as con:
        ensure_schema(con)
        if state:
            rows = con.execute(
                "SELECT * FROM focus_areas WHERE state = ? "
                "ORDER BY COALESCE(shelf_slot, 99), title", (state,)).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM focus_areas ORDER BY "
                "CASE state WHEN 'active' THEN 0 WHEN 'following' THEN 1 ELSE 2 END, "
                "COALESCE(shelf_slot, 99), title").fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Content, read through the lens — five components
# ---------------------------------------------------------------------------
# These five are what the researcher asked for, and each maps to a table that already
# owns its rows. Nothing here writes a copy.
#
#   overview  the standing narrative      (focus_areas.overview)
#   feed      news                        (news_briefs)
#   reading   literature                  (new_publications) + corpus layers
#   thinking  notes + ideas               (personal_notes, ideas) tagged focus:<slug>
#   pulse     what is new since last visit
def focus_news(slug: str, limit: int = 12, since: str = "") -> list[dict]:
    f = get_focus(slug)
    if not f:
        return []
    where, params = lens_sql(_groups(f), 'title || " " || COALESCE(summary,"")')
    sql = (f"SELECT brief_id, brief_date, title, summary, source_url, domain, "
           f"signal_strength FROM news_briefs WHERE {where}")
    if since:
        sql += " AND brief_date >= ?"
        params = params + [since]
    sql += " ORDER BY brief_date DESC, created_at DESC LIMIT ?"
    with connect(paths.db) as con:
        return [dict(r) for r in con.execute(sql, tuple(params + [limit]))]


def focus_reading(slug: str, limit: int = 12, since: str = "") -> list[dict]:
    f = get_focus(slug)
    if not f:
        return []
    where, params = lens_sql(_groups(f), 'title || " " || COALESCE(abstract,"")')
    # NULLIF, not COALESCE. `pub_iso` is '' for a row the normaliser has not
    # reached, and COALESCE only falls through on NULL — so every date rendered
    # blank while `pub_date` sat populated in all 1302 rows. An empty string is
    # not a missing value to SQL, and treating it as one is a silent blank column.
    sql = (f"SELECT id, title, journal, "
           f"COALESCE(NULLIF(pub_iso,''), NULLIF(pub_date,''), discovered_at) AS pub, doi, "
           f"source_url, COALESCE(entry_kind,'article') AS kind, "
           f"COALESCE(added_at,'') AS added_at, COALESCE(read_at,'') AS read_at "
           f"FROM new_publications WHERE {where}")
    if since:
        sql += " AND COALESCE(discovered_at,'') >= ?"
        params = params + [since]
    # An IMPOSSIBLE date sorts by when Metis found the item, not by itself.
    #
    # Source metadata carries future dates — a preprint stamped 2030-01-01 and one
    # stamped 2027-01-01 both sit in this corpus. On a "stay current" surface they
    # take the top slot permanently and never age out.
    #
    # Clamping to today was the first attempt and was not enough: clamped, they tie
    # with today and still lead. So a future date falls back to `discovered_at` —
    # the same rule the date normaliser already applies to an undated item, and for
    # the same reason: when Metis found it is the only trustworthy date there is.
    # The raw `pub` is still returned, so the surface can show the claim and the
    # reader can see it is wrong.
    sql += (" ORDER BY CASE WHEN pub > date('now') THEN discovered_at ELSE pub END "
            "DESC, id DESC LIMIT ?")
    with connect(paths.db) as con:
        return [dict(r) for r in con.execute(sql, tuple(params + [limit]))]


def focus_thinking(slug: str, limit: int = 20) -> dict:
    """Notes and ideas WRITTEN on this focus.

    Matched on the `focus:<slug>` tag, not on keywords. A thought recorded here
    belongs to the focus explicitly; inferring it from words would drag in every
    unrelated note that happened to mention the subject.
    """
    tag = f"focus:{slug}"
    with connect(paths.db) as con:
        notes = [dict(r) for r in con.execute(
            "SELECT note_id, title, content, created_at FROM personal_notes "
            "WHERE COALESCE(tags,'') LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{tag}%", limit))]
        ideas = [dict(r) for r in con.execute(
            "SELECT idea_id, text, idea_type, created_at FROM ideas "
            "WHERE COALESCE(tags,'') LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{tag}%", limit))]
    return {"notes": notes, "ideas": ideas}


def focus_corpus(slug: str) -> dict:
    """How much of the indexed corpus this focus can actually quote."""
    f = get_focus(slug)
    if not f:
        return {"documents": 0, "layers": []}
    where, params = lens_sql(_groups(f), "p.chunk_text")
    layers = [s.strip() for s in (f["layers"] or "").split(",") if s.strip()]
    sql = ("SELECT COALESCE(k.slug,'(unfiled)') AS layer, "
           "COUNT(DISTINCT p.source_file) AS docs FROM pdf_chunks p "
           "LEFT JOIN knowledge_databases k ON k.id = p.db_id "
           f"WHERE {where}")
    if layers:
        sql += " AND k.slug IN (%s)" % ",".join("?" * len(layers))
        params = params + layers
    sql += " GROUP BY 1 ORDER BY 2 DESC"
    with connect(paths.db) as con:
        rows = [dict(r) for r in con.execute(sql, tuple(params))]
    return {"documents": sum(r["docs"] for r in rows), "layers": rows}


def focus_pulse(slug: str) -> dict:
    """What changed since the last visit, and how stale the focus is."""
    f = get_focus(slug)
    if not f:
        return {}
    since = f.get("last_visited_at") or ""
    new_news = len(focus_news(slug, limit=200, since=since[:10])) if since else None
    new_read = len(focus_reading(slug, limit=200, since=since)) if since else None
    latest = focus_news(slug, limit=1)
    return {
        "last_visited_at": since,
        "last_refreshed_at": f.get("last_refreshed_at") or "",
        "new_news": new_news,
        "new_reading": new_read,
        "newest_news_date": (latest[0]["brief_date"] if latest else ""),
        "total_news": len(focus_news(slug, limit=500)),
        "total_reading": len(focus_reading(slug, limit=500)),
    }


def touch_visit(slug: str) -> None:
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute("UPDATE focus_areas SET last_visited_at = ? WHERE slug = ?",
                    (_now(), slug))


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------
@app.tool()
async def create_focus_area(
    title: str,
    keyword_groups: str,
    subtitle: str = "",
    layers: str = "",
    overview: str = "",
    activate: bool = False,
) -> list[TextContent]:
    """Define a focus area — a lens over news, literature and your own thinking.

    A focus is for a subject you want to stay CURRENT on, as opposed to a course
    you finish or a project you deliver. It owns no content: it is a saved query
    plus a place to write, so removing it later cannot remove anything.

    `keyword_groups` is the important argument, and it is groups rather than a
    list on purpose: OR within a group, AND across groups. "AI in health" is a
    conjunction of two axes, and a flat list returns "Can AI ever be conscious?".

    Args:
        title: Human name, e.g. "AI in Health & Epidemiology".
        keyword_groups: JSON list of lists, e.g.
            '[["artificial intelligence","machine learning","llm"],
              ["health","clinical","epidemi","surveillance"]]'
        subtitle: One line on what this focus is for.
        layers: Comma-separated knowledge-layer slugs to search for documents.
        overview: The standing narrative — what matters here and why.
        activate: Put it on the shelf immediately (max 3 active).

    Returns:
        The created focus and its shelf state.
    """
    try:
        groups = json.loads(keyword_groups)
        assert isinstance(groups, list) and groups and all(isinstance(g, list) for g in groups)
    except Exception:
        return [TextContent(type="text", text=(
            "keyword_groups must be a JSON list of lists, e.g.\n"
            '[["artificial intelligence","machine learning"],["health","clinical"]]\n\n'
            "Groups matter: OR inside a group, AND across groups. A flat list for "
            '"AI in health" returns general AI news.'))]

    slug = slugify(title)
    with connect(paths.db) as con:
        ensure_schema(con)
        if con.execute("SELECT 1 FROM focus_areas WHERE slug = ?", (slug,)).fetchone():
            return [TextContent(type="text", text=f"A focus `{slug}` already exists.")]
        con.execute(
            "INSERT INTO focus_areas (slug, title, subtitle, state, keyword_groups, "
            "layers, overview, created_at) VALUES (?,?,?,'following',?,?,?,?)",
            (slug, title.strip(), subtitle.strip(), json.dumps(groups),
             layers.strip(), overview, _now()))

    msg = [f"Created focus **{title}** (`{slug}`) — state `following`."]
    if activate:
        res = await set_focus_state(slug, "active")
        msg.append(res[0].text)
    else:
        msg.append("Put it on the shelf with `set_focus_state(slug, 'active')`.")
    return [TextContent(type="text", text="\n\n".join(msg))]


@app.tool()
async def set_focus_state(slug: str, state: str) -> list[TextContent]:
    """Move a focus between the shelf, following, and the archive.

    `active`    on the shelf and in the left navbar. At most 3 — a shelf with
                ten things on it is not a focus.
    `following` defined and queryable, off the navbar. Attention moved on.
    `archived`  read-only, no refresh, still openable.

    Nothing is ever deleted, and nothing the focus SHOWED is affected by any of
    these transitions: notes, ideas, papers and briefs live in their own tables
    and keep their tags. Removing a lens cannot remove what you saw through it.

    Args:
        slug: The focus slug.
        state: active | following | archived.

    Returns:
        The new shelf layout, or an explanation of why the move was refused.
    """
    if state not in STATES:
        return [TextContent(type="text", text=f"state must be one of {STATES}")]
    with connect(paths.db) as con:
        ensure_schema(con)
        row = con.execute("SELECT * FROM focus_areas WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return [TextContent(type="text", text=f"No focus `{slug}`.")]

        if state == "active":
            active = con.execute(
                "SELECT slug, title, shelf_slot, last_visited_at FROM focus_areas "
                "WHERE state='active' AND slug <> ? ORDER BY COALESCE(shelf_slot,99)",
                (slug,)).fetchall()
            if len(active) >= MAX_SHELF:
                # Refuse rather than silently evicting. Which focus loses its slot
                # is a judgement about attention, and it is the researcher's to make.
                listing = "\n".join(
                    f"  {a['shelf_slot'] or '?'}. {a['title']} (`{a['slug']}`)"
                    f" — last opened {a['last_visited_at'] or 'never'}"
                    for a in active)
                return [TextContent(type="text", text=(
                    f"The shelf is full ({MAX_SHELF} of {MAX_SHELF}):\n{listing}\n\n"
                    "Move one to `following` first. Choosing which focus loses its "
                    "slot is a decision about your attention, so it is not made "
                    "automatically."))]
            used = {a["shelf_slot"] for a in active if a["shelf_slot"]}
            slot = next(i for i in range(1, MAX_SHELF + 1) if i not in used)
            con.execute(
                "UPDATE focus_areas SET state='active', shelf_slot=?, activated_at=?, "
                "archived_at='' WHERE slug=?", (slot, _now(), slug))
            detail = f"on the shelf in slot {slot}"
        elif state == "following":
            con.execute("UPDATE focus_areas SET state='following', shelf_slot=NULL, "
                        "archived_at='' WHERE slug=?", (slug,))
            detail = "following — off the navbar, still queryable"
        else:
            con.execute("UPDATE focus_areas SET state='archived', shelf_slot=NULL, "
                        "archived_at=? WHERE slug=?", (_now(), slug))
            detail = "archived — read-only, no refresh"

        shelf = con.execute(
            "SELECT shelf_slot, title FROM focus_areas WHERE state='active' "
            "ORDER BY COALESCE(shelf_slot,99)").fetchall()

    out = [f"**{row['title']}** is now {detail}.", ""]
    if state == "archived":
        out += ["Everything it showed is untouched: notes and ideas keep their "
                f"`focus:{slug}` tag, papers stay in your library, briefs stay in "
                "the news history. The lens is filed, not the contents.", ""]
    out.append(f"Shelf ({len(shelf)}/{MAX_SHELF}): "
               + (", ".join(f"{s['shelf_slot']}. {s['title']}" for s in shelf) or "empty"))
    return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def show_focus_areas() -> list[TextContent]:
    """List every focus area, its state, and what it currently holds."""
    areas = list_focus()
    if not areas:
        return [TextContent(type="text", text=(
            "No focus areas yet. Create one with `create_focus_area(...)` — a "
            "focus is for a subject you want to stay current on, unlike a course "
            "you finish."))]
    out = [f"**{len(areas)} focus area(s)**", "",
           "| state | slot | focus | news | reading | notes+ideas | last opened |",
           "|---|---:|---|---:|---:|---:|---|"]
    for a in areas:
        t = focus_thinking(a["slug"])
        out.append(
            f"| `{a['state']}` | {a['shelf_slot'] or '—'} | {a['title']} "
            f"| {len(focus_news(a['slug'], limit=500))} "
            f"| {len(focus_reading(a['slug'], limit=500))} "
            f"| {len(t['notes']) + len(t['ideas'])} "
            f"| {(a['last_visited_at'] or '—')[:10]} |")
    n_active = sum(1 for a in areas if a["state"] == "active")
    out += ["", f"Shelf: {n_active}/{MAX_SHELF} slots used."]
    return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def update_focus_overview(slug: str, overview: str) -> list[TextContent]:
    """Replace a focus area's standing overview — the "what matters here" narrative.

    This is the piece that was going to be the AI course's introduction: the
    orientation you want in front of you every time you open the subject, as
    opposed to the feed, which changes daily.

    Args:
        slug: The focus slug.
        overview: Markdown. Replaces the existing overview entirely.

    Returns:
        Confirmation and the new length.
    """
    with connect(paths.db) as con:
        ensure_schema(con)
        if not con.execute("SELECT 1 FROM focus_areas WHERE slug=?", (slug,)).fetchone():
            return [TextContent(type="text", text=f"No focus `{slug}`.")]
        con.execute("UPDATE focus_areas SET overview=? WHERE slug=?", (overview, slug))
    return [TextContent(type="text", text=
            f"Overview updated for `{slug}` ({len(overview)} chars).")]


@app.tool()
async def focus_brief(slug: str) -> list[TextContent]:
    """Everything on one focus area: pulse, news, reading, thinking, corpus.

    The text form of the surface — for Claude Desktop, which has no dashboard.
    """
    f = get_focus(slug)
    if not f:
        return [TextContent(type="text", text=f"No focus `{slug}`.")]
    p, corp = focus_pulse(slug), focus_corpus(slug)
    news, read, think = focus_news(slug, 8), focus_reading(slug, 8), focus_thinking(slug)

    out = [f"# {f['title']}", ""]
    if f["subtitle"]:
        out += [f"*{f['subtitle']}*", ""]
    out += [f"State `{f['state']}`"
            + (f" · shelf slot {f['shelf_slot']}" if f["shelf_slot"] else "")
            + f" · {p['total_news']} briefs · {p['total_reading']} papers · "
            f"{corp['documents']} indexed documents", ""]
    if p.get("new_news") is not None:
        out += [f"Since your last visit ({p['last_visited_at'][:16]}): "
                f"**{p['new_news']} new brief(s)**, **{p['new_reading']} new paper(s)**.", ""]
    if f["overview"]:
        out += ["## Overview", "", f["overview"], ""]
    if news:
        out += ["## Latest", ""] + [
            f"- {n['brief_date']} — {n['title']}" for n in news] + [""]
    if read:
        out += ["## Reading", ""] + [
            f"- {(r['pub'] or '')[:10]} — {r['title'][:110]}"
            + (f" · `{r['doi']}`" if r["doi"] else "") for r in read] + [""]
    if think["notes"] or think["ideas"]:
        out += ["## Your thinking", ""]
        out += [f"- 💡 {i['text'][:140]}" for i in think["ideas"]]
        out += [f"- 📝 {n['title'] or n['content'][:80]}" for n in think["notes"]]
    else:
        out += ["## Your thinking", "", "Nothing recorded on this focus yet."]
    return [TextContent(type="text", text="\n".join(out))]


# ---------------------------------------------------------------------------
# Lens preview — see what a lens catches BEFORE saving it
# ---------------------------------------------------------------------------
# The gap this closes: lens tuning was blind. A test DHIS2 focus returned 0 news
# and 0 papers, and the only way to discover that was to build the focus, open the
# surface and notice it was empty. A lens is the entire behaviour of the surface,
# so guessing at it and finding out later is the wrong loop.
#
# THE DIAGNOSTIC THAT MATTERS IS PER-GROUP, NOT TOTAL.
#   A conjunction returning zero tells you nothing about WHICH group is wrong. So
#   the preview reports each group alone as well as the combination. If group 1
#   matches 400 things, group 2 matches 3, and together they match 0, the answer is
#   unambiguous and needs no judgement: group 2 is the problem.
def preview_lens(groups: list[list[str]], sample: int = 4) -> dict:
    """What a candidate lens would catch, with a per-group breakdown."""
    out: dict = {"groups": groups, "per_group": [], "combined": {}, "samples": []}
    if not groups:
        return out

    news_expr = 'title || " " || COALESCE(summary,"")'
    pub_expr = 'title || " " || COALESCE(abstract,"")'

    with connect(paths.db) as con:
        def count(table, expr, gs):
            where, params = lens_sql(gs, expr)
            try:
                return con.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {where}", tuple(params)
                ).fetchone()[0]
            except Exception:
                return 0

        for i, grp in enumerate(groups):
            out["per_group"].append({
                "index": i + 1,
                "terms": grp,
                "news": count("news_briefs", news_expr, [grp]),
                "reading": count("new_publications", pub_expr, [grp]),
            })

        out["combined"] = {
            "news": count("news_briefs", news_expr, groups),
            "reading": count("new_publications", pub_expr, groups),
        }

        where, params = lens_sql(groups, news_expr)
        try:
            out["samples"] = [
                {"date": r["brief_date"], "title": r["title"]}
                for r in con.execute(
                    f"SELECT brief_date, title FROM news_briefs WHERE {where} "
                    "ORDER BY brief_date DESC LIMIT ?", tuple(params + [sample]))]
        except Exception:
            out["samples"] = []

    # The verdict, stated rather than left to be inferred from a table of numbers.
    # This sentence is the part a non-technical user actually reads, so it has to
    # be right about WHICH group is at fault and about EACH stream separately.
    #
    # Two wordings were wrong on the first run and are fixed here:
    #   · "Each group matches on its own but never together" was emitted for a
    #     group matching 0 news and 2 papers. Two is not "matches on its own", and
    #     the message sent the reader looking for a co-occurrence problem that did
    #     not exist. A group is now called the constraint when it is
    #     DISPROPORTIONATELY small, not only when it is exactly zero.
    #   · "Workable" was emitted for a lens returning 0 news and 8 papers. A feed
    #     with no news is not workable on a surface whose top section is news, so
    #     an empty stream is now named.
    c = out["combined"]
    groups_by_size = sorted(out["per_group"], key=lambda g: g["news"] + g["reading"])
    weakest = groups_by_size[0] if groups_by_size else None
    strongest = groups_by_size[-1] if groups_by_size else None

    def _terms(g):
        return ", ".join(g["terms"][:4]) + ("…" if len(g["terms"]) > 4 else "")

    def _tot(g):
        return g["news"] + g["reading"]

    # `strongest` must ACTUALLY match something, or a lens where every group is
    # empty gets reported as "group 1 is the constraint … against 0/0 for group 2",
    # which blames one group for a failure they all share.
    lopsided = bool(
        weakest and strongest and weakest is not strongest
        and _tot(strongest) > 0
        and _tot(weakest) < max(5, 0.05 * _tot(strongest)))
    all_empty = bool(groups_by_size and _tot(strongest) == 0)

    if c["news"] + c["reading"] == 0:
        if all_empty:
            out["verdict"] = (
                "Nothing matches, and no group matches anything on its own — none "
                "of these terms appear in the collection at all. Check the spelling "
                "and try broader words.")
        elif lopsided:
            out["verdict"] = (
                f"Nothing matches. Group {weakest['index']} ({_terms(weakest)}) is "
                f"the constraint — it finds "
                f"{weakest['news']} news and {weakest['reading']} papers on its own, "
                f"against {strongest['news']}/{strongest['reading']} for group "
                f"{strongest['index']}. Widen group {weakest['index']} or drop it.")
        else:
            out["verdict"] = ("Nothing matches, though each group works alone — the "
                              "two axes may simply not co-occur in this corpus yet.")
    else:
        bits = []
        if c["news"] == 0:
            bits.append("no NEWS matches, so the feed at the top of the surface "
                        "will be empty")
        if c["reading"] == 0:
            bits.append("no PAPER matches, so the reading list will be empty")
        if c["news"] + c["reading"] < 5:
            bits.append("very thin overall")
        if lopsided:
            bits.append(f"group {weakest['index']} ({_terms(weakest)}) is doing "
                        "nearly all the limiting")
        out["verdict"] = ("Workable — the conjunction returns a usable feed."
                          if not bits
                          else "Usable but " + "; ".join(bits) + ".")
    return out


@app.tool()
async def preview_focus_lens(keyword_groups: str) -> list[TextContent]:
    """Try a lens before creating a focus — how much does it catch, and where does
    it fail?

    Lens tuning was otherwise blind: the only way to learn a lens returned nothing
    was to build the focus, open it and find it empty. Worse, a conjunction that
    returns zero says nothing about WHICH group is at fault.

    So this reports each group's matches ALONE as well as combined. If group 1
    matches 400 and group 2 matches 3 and together they match 0, group 2 is the
    problem and no judgement is required to see it.

    Args:
        keyword_groups: JSON list of lists — OR within a group, AND across groups.
            e.g. '[["dhis2","hmis"],["surveillance","district"]]'

    Returns:
        Per-group and combined counts, sample matches, and a plain verdict.
    """
    try:
        groups = json.loads(keyword_groups)
        assert isinstance(groups, list) and groups and all(isinstance(g, list) for g in groups)
    except Exception:
        return [TextContent(type="text", text=(
            "keyword_groups must be a JSON list of lists, e.g.\n"
            '[["dhis2","hmis"],["surveillance","district"]]'))]

    p = preview_lens(groups)
    out = ["**Lens preview**", "",
           "| group | terms | news alone | papers alone |",
           "|---:|---|---:|---:|"]
    for g in p["per_group"]:
        out.append(f"| {g['index']} | {', '.join(g['terms'][:6])}"
                   f"{'…' if len(g['terms']) > 6 else ''} "
                   f"| {g['news']} | {g['reading']} |")
    out += ["", f"**Together (AND across groups): {p['combined']['news']} news · "
                f"{p['combined']['reading']} papers**", "",
            p["verdict"]]
    if p["samples"]:
        out += ["", "Sample matches:"] + [
            f"- {s['date']} — {s['title'][:100]}" for s in p["samples"]]
    return [TextContent(type="text", text="\n".join(out))]
