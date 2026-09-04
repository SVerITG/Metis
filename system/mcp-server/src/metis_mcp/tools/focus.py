"""focus.py — a focus area is a LENS, not a container.

WHAT THIS IS FOR
    The researcher, 2026-08-24: the "AI in Public Health course" turned out not to be a
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
    last_refreshed_at TEXT DEFAULT '',
    sections          TEXT DEFAULT '',
    links             TEXT DEFAULT '',
    n_new             INTEGER DEFAULT 0,
    n_new_at          TEXT DEFAULT ''
)
"""


# A verdict is the researcher's judgement on ONE item seen through ONE lens.
#
# `title` is denormalised on purpose, and it is not laziness. It is read for two
# things the source row cannot guarantee: the taste model below needs the words
# even for rows that later get pruned from `news_briefs`, and the Safe must still
# render what you saved after the feed has moved on. A safe whose contents vanish
# when upstream tidies up is not a safe.
_DDL_VERDICT = """
CREATE TABLE IF NOT EXISTS focus_verdict (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    slug       TEXT NOT NULL,
    kind       TEXT NOT NULL,          -- 'news' | 'reading'
    item_id    TEXT NOT NULL,
    verdict    TEXT NOT NULL,          -- 'kept' | 'declined'
    title      TEXT DEFAULT '',
    url        TEXT DEFAULT '',
    note       TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(slug, kind, item_id)
)
"""

# A generated brief is kept, not recomputed on view. The morning brief works the
# same way, and for the same reason: a brief you read on Tuesday should still say
# on Friday what it said on Tuesday, or it is not a record of anything.
_DDL_BRIEF = """
CREATE TABLE IF NOT EXISTS focus_brief_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    slug       TEXT NOT NULL,
    body       TEXT NOT NULL,
    n_news     INTEGER DEFAULT 0,
    n_reading  INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
)
"""


def ensure_schema(con) -> None:
    con.execute(_DDL)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_focus_slug "
                "ON focus_areas(slug)")
    con.execute(_DDL_VERDICT)
    con.execute("CREATE INDEX IF NOT EXISTS idx_verdict_slug "
                "ON focus_verdict(slug, verdict)")
    con.execute(_DDL_BRIEF)
    con.execute("CREATE INDEX IF NOT EXISTS idx_focus_brief_slug "
                "ON focus_brief_log(slug, created_at)")


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


# ---------------------------------------------------------------------------
# How a keyword matches
# ---------------------------------------------------------------------------
# Changed 2026-08-26, on measured evidence and with the researcher's go-ahead.
#
# THE PROBLEM. Keywords matched as bare substrings (`LIKE '%kw%'`). On his
# AI-in-health lens that made 70 of 388 briefs (18%) false positives, and the
# examples are not marginal:
#
#     'ai'  inside 'avait'        -> Sénégal: le Conseil constitutionnel…
#     'gis' inside 'enregistre'   -> Ligue 1: à Nice, l'Ivoirien Wahi…
#     'gis' inside 'radiologists' -> AI won't replace radiologists…
#
# THE RULE. A keyword must now start at a WORD BOUNDARY. It may still run into a
# longer word from there, which is what keeps a deliberate stem working:
# 'epidemi' catches epidemiology and epidemic, while 'ai' stops catching 'said'.
#
# WHAT IT COSTS, STATED PLAINLY. That third example is a real loss: "AI won't
# replace radiologists" is genuinely relevant and reached group 2 only through
# 'gis' inside 'radiologists'. A lens is a filter, and any filter tightened
# enough to remove noise removes something worth keeping. The surface therefore
# reports what the change dropped rather than quietly banking the improvement.
#
# HOW, given SQLite has no word-boundary operator: LIKE stays as a cheap,
# index-friendly first pass, and a boundary regex confirms in Python. The SQL can
# only over-return, never under-return, so the confirmation is sound.
# ── SHORT KEYWORDS ARE ACRONYMS, NOT STEMS ───────────────────────────────────
# Added 2026-09-04, on measured evidence.
#
# THE PROBLEM. The word-start rule above is deliberately generous: a keyword may
# run on into a longer word, which is what makes 'epidemi' catch epidemiology
# and epidemic. That generosity makes a two-letter keyword unusable — as a stem,
# 'ai' matches aid, AIDS, air and aim, every one of them common in global
# health. So 'ai' was never added to the AI-in-health lens at all, and the
# focus matched only the spelled-out "artificial intelligence".
#
# WHAT THAT COST, MEASURED. On 2026-09-04 the lens returned 23 of 4,103 briefs.
# Another 21 said a standalone "AI" beside a health term and were silently
# dropped — among them "World's first patient to undergo live AI-assisted brain
# surgery" and "Context-aware AI assistance reduces diagnostic error in chest
# X-ray interpretation". Both are squarely the subject of that focus, and both
# were invisible on it. A focus that misses the most common spelling of its own
# subject is not a filter, it is a leak — and the failure is silent, because a
# lens reports what it caught and never what it passed over.
#
# THE RULE. A keyword of three characters or fewer is matched as a WHOLE WORD,
# with an optional plural 's'. Longer keywords keep the word-start stem
# behaviour, unchanged. The mode is chosen by the shape of the keyword, so no
# stored lens needs re-authoring.
#
#     'ai'  -> \bai(?:s)?\b   matches "AI", "AIs", "AI-assisted" (a hyphen is a
#                             word boundary); rejects aid, AIDS, air, aim.
#     'llm' -> \bllm(?:s)?\b  matches "LLM", "LLMs", "LLM-based" — the only
#                             short keyword that existed when this landed, and
#                             the optional plural is what keeps it working.
_SHORT_KW = 3

_WORD_START = {}


def _boundary_re(kw: str):
    """A cached compiled regex for one keyword.

    Short keywords match as whole words (see above); longer ones are anchored at
    a word start and may run into a longer word.
    """
    r = _WORD_START.get(kw)
    if r is None:
        k = re.escape(kw.lower())
        r = re.compile(rf"\b{k}(?:s)?\b" if len(kw) <= _SHORT_KW else rf"\b{k}")
        _WORD_START[kw] = r
    return r


def matches_lens(groups: list, text: str) -> bool:
    """AND across groups, OR within — with word-boundary matching."""
    if not groups:
        return False
    t = (text or "").lower()
    return all(any(_boundary_re(k).search(t) for k in grp) for grp in groups)


def confirm(groups: list, rows: list, fields: list) -> list:
    """Keep only rows whose lens match survives word-boundary checking.

    `fields` are the columns the SQL matched on, joined the same way, so this
    cannot disagree with the query about WHAT was searched — only about how
    strictly.
    """
    if not groups:
        return rows
    out = []
    for r in rows:
        blob = " ".join(str(r.get(f) or "") for f in fields)
        if matches_lens(groups, blob):
            out.append(r)
    return out


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
    # Over-fetch, then confirm: the boundary check can only REMOVE rows, so a
    # limit applied before it would silently return short.
    sql += " ORDER BY brief_date DESC, created_at DESC LIMIT ?"
    with connect(paths.db) as con:
        rows = [dict(r) for r in con.execute(sql, tuple(params + [limit * 3 + 30]))]
    return confirm(_groups(f), rows, ["title", "summary"])[:limit]


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
        rows = [dict(r) for r in con.execute(sql, tuple(params + [limit * 3 + 30]))]
    # `abstract` is matched by the SQL but not selected, so confirming on the
    # title alone would drop every row whose match lives in the abstract.
    ids = [r["id"] for r in rows]
    if ids and _groups(f):
        with connect(paths.db) as con:
            abstracts = {r["id"]: r["abstract"] or "" for r in con.execute(
                "SELECT id, abstract FROM new_publications WHERE id IN (%s)"
                % ",".join("?" * len(ids)), tuple(ids))}
        for r in rows:
            r["_abstract"] = abstracts.get(r["id"], "")
    return confirm(_groups(f), rows, ["title", "_abstract"])[:limit]


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


# ---------------------------------------------------------------------------
# Which knowledge layers a focus searches
# ---------------------------------------------------------------------------
# A trap worth naming, found 2026-08-26 on the researcher's own focus. The create form
# says "Knowledge layers to search (optional, comma-separated)" and lists the
# slugs available. He typed `all`, meaning "search everything" — the reading any
# person would give it. `all` is not a slug, so `k.slug IN ('all')` matched
# nothing and the surface reported **0 indexed documents** while sitting on a
# corpus of 27,428 chunks. Explore's corpus half returned nothing, silently.
#
# Empty meaning "everything" and `all` meaning "nothing" is exactly backwards.
# Two rules follow, and the second matters more than the first:
#   1. The obvious synonyms for "everything" mean everything.
#   2. A layer name that matches NO layer is reported, never silently applied. A
#      filter that quietly excludes the entire corpus is indistinguishable from
#      an empty corpus, and the reader has no way to tell which they are looking
#      at.
_ALL_LAYERS = {"all", "any", "*", "everything", "every", "-", "none"}


def layer_filter(f: dict) -> dict:
    """Resolve a focus's `layers` field against the layers that actually exist.

    Returns {"slugs": [...], "unknown": [...], "all": bool}. `slugs` is empty
    when nothing should be filtered — which is the safe default, because
    searching too much is a nuisance and searching nothing looks like an empty
    library.
    """
    raw = [s.strip().lower() for s in (f.get("layers") or "").split(",") if s.strip()]
    if not raw or all(r in _ALL_LAYERS for r in raw):
        return {"slugs": [], "unknown": [], "all": True}
    with connect(paths.db) as con:
        known = {r["slug"] for r in con.execute(
            "SELECT slug FROM knowledge_databases WHERE COALESCE(slug,'') != ''")}
    wanted = [r for r in raw if r not in _ALL_LAYERS]
    slugs = [r for r in wanted if r in known]
    unknown = [r for r in wanted if r not in known]
    # Every named layer was a typo: fall back to searching everything and SAY so,
    # rather than returning an empty corpus that looks like a missing library.
    return {"slugs": slugs, "unknown": unknown, "all": not slugs}


def focus_corpus(slug: str) -> dict:
    """How much of the indexed corpus this focus can actually quote."""
    f = get_focus(slug)
    if not f:
        return {"documents": 0, "layers": []}
    where, params = lens_sql(_groups(f), "p.chunk_text")
    lf = layer_filter(f)
    sql = ("SELECT COALESCE(k.slug,'(unfiled)') AS layer, "
           "COUNT(DISTINCT p.source_file) AS docs FROM pdf_chunks p "
           "LEFT JOIN knowledge_databases k ON k.id = p.db_id "
           f"WHERE {where}")
    if lf["slugs"]:
        sql += " AND k.slug IN (%s)" % ",".join("?" * len(lf["slugs"]))
        params = params + lf["slugs"]
    sql += " GROUP BY 1 ORDER BY 2 DESC"
    with connect(paths.db) as con:
        rows = [dict(r) for r in con.execute(sql, tuple(params))]
    return {"documents": sum(r["docs"] for r in rows), "layers": rows,
            "unknown_layers": lf["unknown"]}


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
# The safe, and the taste that grows out of it
# ---------------------------------------------------------------------------
# The researcher's brief, 2026-08-26: keep an item "in a safe, that will be used
# for further reflection"; decline one so "similar things are less (not entirely
# not) suggested in the future".
#
# THE PARENTHESIS IS THE SPECIFICATION. Declining must demote, never delete. In a
# research tool, silently stopping a whole literature from appearing is worse than
# showing too much, because an absence cannot be audited: you never learn what you
# stopped being shown. So a muted item stays on the surface, folded, counted, and
# one click from view — and every mute can be asked WHY, below.

# Words that carry no taste. Kept deliberately short: this filters function words,
# not domain vocabulary, because domain vocabulary is exactly the signal.
_TASTE_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "had",
    "are", "was", "were", "been", "will", "would", "could", "should", "can",
    "its", "their", "there", "these", "those", "then", "than", "such", "into",
    "over", "under", "after", "before", "between", "during", "about", "against",
    "new", "using", "used", "use", "study", "studies", "based", "results",
    "paper", "article", "report", "review", "analysis", "more", "most",
    "other", "also", "how", "why", "what", "when", "which", "who", "you", "your",
    "our", "not", "via", "per", "may", "might", "one", "two", "three",
}


def _taste_terms(text: str) -> set:
    """Content words, lowercased, four characters or more."""
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())
            if w not in _TASTE_STOP}


def _lens_terms(f: dict) -> set:
    """Every word the lens itself matches on.

    These are EXCLUDED from taste, and that exclusion is what stops the feature
    eating itself. Every item on an "AI in health" focus contains "ai" and
    "health" — they are why it is here. Learn from them and the first decline
    down-weights the whole subject, muting the focus with one click. Taste has to
    be learned from what varies WITHIN the lens, not from the lens.
    """
    out: set = set()
    for grp in _groups(f):
        for kw in grp:
            out |= {w for w in re.findall(r"[a-z]{3,}", kw.lower())}
    return out


def focus_verdicts(slug: str, verdict: str = "") -> list:
    """Everything judged on this focus, newest first."""
    sql = ("SELECT kind, item_id, verdict, title, url, note, created_at "
           "FROM focus_verdict WHERE slug = ?")
    params: list = [slug]
    if verdict:
        sql += " AND verdict = ?"
        params.append(verdict)
    sql += " ORDER BY created_at DESC"
    with connect(paths.db) as con:
        ensure_schema(con)
        return [dict(r) for r in con.execute(sql, tuple(params))]


def judge(slug: str, kind: str, item_id: str, verdict: str,
          title: str = "", url: str = "", note: str = "") -> None:
    """Record (or change) a verdict. Re-judging replaces, so nothing is stranded."""
    if verdict not in ("kept", "declined"):
        raise ValueError(f"verdict must be kept|declined, got {verdict!r}")
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute(
            "INSERT INTO focus_verdict (slug, kind, item_id, verdict, title, url, "
            "note, created_at) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(slug, kind, item_id) DO UPDATE SET "
            "verdict=excluded.verdict, note=excluded.note, created_at=excluded.created_at",
            (slug, kind, str(item_id), verdict, title[:400], url[:600], note[:400],
             _now()))


def unjudge(slug: str, kind: str, item_id: str) -> None:
    """Undo a verdict entirely — back to undecided."""
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute("DELETE FROM focus_verdict WHERE slug=? AND kind=? AND item_id=?",
                    (slug, kind, str(item_id)))


def focus_taste(slug: str) -> dict:
    """term -> (times kept) minus (times declined), lens words removed.

    Deliberately a plain count, not a learned weight. The researcher has to be
    able to read this table and recognise his own judgements in it; a score he
    cannot explain is one he cannot correct, and correcting it is the whole point
    of a surface that is supposed to be built over weeks.
    """
    f = get_focus(slug)
    if not f:
        return {}
    lens = _lens_terms(f)
    taste: dict = {}
    for v in focus_verdicts(slug):
        step = 1 if v["verdict"] == "kept" else -1
        for t in _taste_terms(v["title"]) - lens:
            taste[t] = taste.get(t, 0) + step
    return {k: v for k, v in taste.items() if v}


def taste_verdict(taste: dict, text: str) -> tuple:
    """Score one item against the taste, and say which words did it.

    Returning the reasons is not decoration. An item is only ever demoted, and a
    demotion the reader cannot interrogate is indistinguishable from a bug.
    """
    if not taste:
        return 0, []
    hits = [(t, taste[t]) for t in _taste_terms(text) if t in taste]
    if not hits:
        return 0, []
    score = sum(w for _, w in hits)
    reasons = [t for t, w in sorted(hits, key=lambda h: h[1]) if w < 0][:3]
    return score, reasons


# The bar for muting. One decline is an opinion about one item; it should not
# reshape the feed. Two independent declines sharing a word is a pattern.
MUTE_AT = -2


def sift(slug: str, items: list, kind: str, text_key: str, id_key: str) -> dict:
    """Split a lens result into decided, live and muted.

    Returns every input item — nothing is discarded here or anywhere downstream.
    """
    judged = {v["item_id"]: v for v in focus_verdicts(slug) if v["kind"] == kind}
    taste = focus_taste(slug)
    live, muted, decided = [], [], []
    for it in items:
        iid = str(it.get(id_key) or "")
        it = {**it, "_id": iid, "_kind": kind}
        if iid in judged:
            it["_verdict"] = judged[iid]["verdict"]
            decided.append(it)
            continue
        score, reasons = taste_verdict(taste, it.get(text_key) or "")
        it["_score"], it["_why"] = score, reasons
        (muted if score <= MUTE_AT else live).append(it)
    live.sort(key=lambda i: -i["_score"])
    return {"live": live, "muted": muted, "decided": decided,
            "n_live": len(live), "n_muted": len(muted)}




# ---------------------------------------------------------------------------
# Questions, and exploring them
# ---------------------------------------------------------------------------
# A question is an idea with `idea_type='question'`, tagged `focus:<slug>` like
# every other thought written here. It is NOT a new table, deliberately: the file
# header's rule is that a focus writes no copies, and a question the researcher
# later answers should surface in idea search like any other, not be trapped
# inside a surface he might archive.

def focus_questions(slug: str, limit: int = 30) -> list:
    tag = f"focus:{slug}"
    with connect(paths.db) as con:
        return [dict(r) for r in con.execute(
            "SELECT idea_id, text, created_at FROM ideas "
            "WHERE COALESCE(tags,'') LIKE ? AND idea_type = 'question' "
            "ORDER BY created_at DESC LIMIT ?", (f"%{tag}%", limit))]


def explore(slug: str, question: str, limit: int = 6) -> dict:
    """Answer a question from what the researcher already holds.

    "Explore ... will answer the questions in relationship with notes and ideas
    or it might look for specific literature of that topic" (2026-08-26).

    It does BOTH, in that order, and it composes nothing. The dashboard has no
    model; what it can do — and what a chat window cannot — is find the passage on
    page 12 of a PDF this researcher indexed himself, next to the note he wrote
    about it in March. Retrieval is the half worth automating. The composed answer
    is one deeplink away, carrying this material with it.

    Every search is scoped by the lens as well as the question, so exploring
    "what about resistance" on an AI focus cannot wander into drug resistance.
    """
    f = get_focus(slug)
    if not f or not question.strip():
        return {"question": question, "passages": [], "papers": [],
                "notes": [], "ideas": []}

    q_terms = sorted(_taste_terms(question), key=len, reverse=True)[:6]
    if not q_terms:
        q_terms = [w for w in re.findall(r"[a-z]{3,}", question.lower())][:6]
    lens_where, lens_params = lens_sql(_groups(f), "p.chunk_text")

    def _any(expr: str) -> tuple:
        if not q_terms:
            return "1", []
        return ("(" + " OR ".join(f"lower({expr}) LIKE ?" for _ in q_terms) + ")",
                [f"%{t}%" for t in q_terms])

    passages, papers, notes, ideas = [], [], [], []
    layers = layer_filter(f)["slugs"]

    with connect(paths.db) as con:
        ensure_schema(con)
        # 1. The indexed corpus — the part no chat window can reach.
        q_where, q_params = _any("p.chunk_text")
        sql = ("SELECT p.source_file, p.title, p.page_start, p.chunk_text, "
               "COALESCE(k.slug,'(unfiled)') AS layer "
               "FROM pdf_chunks p LEFT JOIN knowledge_databases k ON k.id = p.db_id "
               f"WHERE {lens_where} AND {q_where}")
        params = list(lens_params) + list(q_params)
        if layers:
            sql += " AND k.slug IN (%s)" % ",".join("?" * len(layers))
            params += layers
        sql += " LIMIT ?"
        try:
            _raw = [dict(r) for r in con.execute(sql, tuple(params + [limit * 4]))]
            # Boundary-confirmed like the feed and the reading list. The document
            # COUNT above is not confirmed and deliberately so: it is a scale
            # indicator ("how much of your corpus is in scope"), not a claim about
            # any one passage, and re-checking 8,211 chunks on every page load
            # would cost far more than the number is worth. What is SHOWN is
            # confirmed; what is counted is an estimate, and the two are used for
            # different things.
            passages = confirm(_groups(f), _raw, ["chunk_text"])[:limit]
        except Exception:
            passages = []

        # 2. Literature through the lens that also mentions the question.
        lit_lens, lit_params = lens_sql(_groups(f), 'title || " " || COALESCE(abstract,"")')
        lit_q, lit_qp = _any('title || " " || COALESCE(abstract,"")')
        try:
            papers = [dict(r) for r in con.execute(
                "SELECT id, title, journal, doi, source_url, "
                "COALESCE(NULLIF(pub_iso,''), NULLIF(pub_date,''), discovered_at) AS pub "
                f"FROM new_publications WHERE {lit_lens} AND {lit_q} "
                "ORDER BY pub DESC LIMIT ?",
                tuple(list(lit_params) + list(lit_qp) + [limit]))]
        except Exception:
            papers = []

        # 3. What he already thought about it — the "in relationship with" half.
        tag = f"focus:{slug}"
        n_q, n_p = _any("content || ' ' || COALESCE(title,'')")
        try:
            notes = [dict(r) for r in con.execute(
                "SELECT note_id, title, content, created_at FROM personal_notes "
                f"WHERE COALESCE(tags,'') LIKE ? AND {n_q} "
                "ORDER BY created_at DESC LIMIT ?",
                tuple([f"%{tag}%"] + list(n_p) + [limit]))]
        except Exception:
            notes = []
        i_q, i_p = _any("text")
        try:
            ideas = [dict(r) for r in con.execute(
                "SELECT idea_id, text, idea_type, created_at FROM ideas "
                f"WHERE COALESCE(tags,'') LIKE ? AND {i_q} "
                "ORDER BY created_at DESC LIMIT ?",
                tuple([f"%{tag}%"] + list(i_p) + [limit]))]
        except Exception:
            ideas = []

    return {"question": question.strip(), "terms": q_terms, "passages": passages,
            "papers": papers, "notes": notes, "ideas": ideas,
            "total": len(passages) + len(papers) + len(notes) + len(ideas)}


# ---------------------------------------------------------------------------
# A brief per focus, kept
# ---------------------------------------------------------------------------
def save_brief(slug: str, body: str, n_news: int = 0, n_reading: int = 0) -> None:
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute("INSERT INTO focus_brief_log (slug, body, n_news, n_reading, "
                    "created_at) VALUES (?,?,?,?,?)",
                    (slug, body, n_news, n_reading, _now()))


def latest_brief(slug: str) -> dict:
    with connect(paths.db) as con:
        ensure_schema(con)
        r = con.execute(
            "SELECT body, n_news, n_reading, created_at FROM focus_brief_log "
            "WHERE slug = ? ORDER BY created_at DESC LIMIT 1", (slug,)).fetchone()
        return dict(r) if r else {}


def focus_counts(slug: str) -> dict:
    """The header line: what is saved, and how much of everything there is.

    The one number a researcher actually acts on is the first: how many items are
    waiting to be judged. Totals that only grow are demoted behind it, which is
    the same rule the Today audit landed on — a counter that can only rise stops
    being information past what a person can do about it.
    """
    verdicts = focus_verdicts(slug)
    think = focus_thinking(slug)
    p = focus_pulse(slug)
    kept = [v for v in verdicts if v["verdict"] == "kept"]
    declined = [v for v in verdicts if v["verdict"] == "declined"]
    return {
        "saved": len(kept),
        "declined": len(declined),
        "ideas": len([i for i in think["ideas"] if i.get("idea_type") != "question"]),
        "questions": len(focus_questions(slug)),
        "notes": len(think["notes"]),
        "briefs": p.get("total_news", 0),
        "papers": p.get("total_reading", 0),
        "documents": focus_corpus(slug).get("documents", 0),
        "taste_terms": len(focus_taste(slug)),
        "last_brief": (latest_brief(slug) or {}).get("created_at", ""),
    }


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


def build_brief(slug: str, n: int = 8) -> str:
    """The brief for one focus, as markdown.

    Shared by the MCP tool (Claude Desktop, which has no dashboard) and the
    dashboard button, so the two can never drift into telling different stories
    about the same focus.

    It is assembled, not written: no model runs here. That is the honest division
    of labour — Metis knows what is in the safe, what is still unjudged and what
    questions are open; composing prose about it is what the deeplink at the
    bottom of the surface is for. A brief that claimed to be authored would be a
    template pretending, and this researcher would spot it in one reading.
    """
    f = get_focus(slug)
    if not f:
        return f"No focus `{slug}`."
    p, corp, c = focus_pulse(slug), focus_corpus(slug), focus_counts(slug)
    news = sift(slug, focus_news(slug, 60), "news", "title", "brief_id")
    read = sift(slug, focus_reading(slug, 60), "reading", "title", "id")
    think = focus_thinking(slug)
    kept = [v for v in focus_verdicts(slug, "kept")]
    questions = focus_questions(slug)

    out = [f"# {f['title']}", ""]
    if f["subtitle"]:
        out += [f"*{f['subtitle']}*", ""]
    out += [f"{datetime.now().strftime('%A %d %B %Y, %H:%M')}", ""]

    # What changed leads, because that is the question you open a focus with.
    if p.get("new_news") is not None:
        out += [f"**Since your last visit** ({p['last_visited_at'][:16]}): "
                f"{p['new_news']} new brief(s), {p['new_reading']} new paper(s).", ""]
    out += [f"{c['saved']} saved · {c['questions']} open question(s) · "
            f"{c['ideas']} idea(s) · {c['notes']} note(s) · "
            f"{news['n_live']} unjudged brief(s) · {corp['documents']} indexed documents",
            ""]

    if f["overview"]:
        out += ["## Overview", "", f["overview"], ""]

    if kept:
        out += ["## In the safe", ""]
        out += [f"- {k['title'][:140]}" + (f"\n  <{k['url']}>" if k["url"] else "")
                for k in kept[:12]]
        out += [""]

    if questions:
        out += ["## Open questions", ""]
        out += [f"- {q['text'][:180]}" for q in questions[:8]] + [""]

    if news["live"]:
        out += ["## Worth a look", ""]
        out += [f"- {i['brief_date']} — {i['title']}" for i in news["live"][:n]] + [""]
    if news["n_muted"]:
        out += [f"*{news['n_muted']} brief(s) muted by your declines — still on the "
                f"surface, folded.*", ""]

    if read["live"]:
        out += ["## Reading", ""]
        out += [f"- {(r['pub'] or '')[:10]} — {r['title'][:120]}"
                + (f" · `{r['doi']}`" if r.get("doi") else "")
                for r in read["live"][:n]] + [""]

    ideas = [i for i in think["ideas"] if i.get("idea_type") != "question"]
    if ideas or think["notes"]:
        out += ["## Your thinking", ""]
        out += [f"- 💡 {i['text'][:160]}" for i in ideas[:6]]
        out += [f"- 📝 {n_['title'] or n_['content'][:100]}" for n_ in think["notes"][:6]]
        out += [""]

    taste = focus_taste(slug)
    if taste:
        up = sorted((t for t in taste.items() if t[1] > 0), key=lambda x: -x[1])[:6]
        down = sorted((t for t in taste.items() if t[1] < 0), key=lambda x: x[1])[:6]
        out += ["## What this focus has learned", ""]
        if up:
            out += ["Drawn to: " + ", ".join(f"{t} (+{w})" for t, w in up)]
        if down:
            out += ["Cooling on: " + ", ".join(f"{t} ({w})" for t, w in down)]
        out += ["", "*Learned only from what you kept and declined — never from the "
                "lens words themselves, or one decline would mute the whole subject.*",
                ""]
    return "\n".join(out).rstrip() + "\n"


@app.tool()
async def focus_brief(slug: str) -> list[TextContent]:
    """Everything on one focus area: what is saved, what is new, what is open.

    The text form of the surface — for Claude Desktop, which has no dashboard.
    """
    return [TextContent(type="text", text=build_brief(slug))]


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


# ---------------------------------------------------------------------------
# The safe, from Claude Desktop
# ---------------------------------------------------------------------------
# Desktop has no dashboard, and a safe you can only fill by clicking is a safe
# that stays empty on the days the researcher works in Desktop. Same store, same
# taste model, same demotion rule — only the door is different.

@app.tool()
async def focus_keep(slug: str, title: str, item_id: str = "", kind: str = "news",
                     url: str = "", note: str = "") -> list[TextContent]:
    """Save an item to a focus area's safe, for further reflection."""
    if not get_focus(slug):
        return [TextContent(type="text", text=f"No focus `{slug}`.")]
    judge(slug, kind, item_id or slugify(title)[:40], "kept", title, url, note)
    c = focus_counts(slug)
    return [TextContent(type="text", text=(
        f"Kept on **{slug}**: {title[:120]}\n\n"
        f"{c['saved']} in the safe · this focus now recognises "
        f"{c['taste_terms']} term(s) from what you have kept and declined."))]


@app.tool()
async def focus_decline(slug: str, title: str, item_id: str = "",
                        kind: str = "news", note: str = "") -> list[TextContent]:
    """Say an item does not interest you, so similar ones rank lower in future.

    Lower, not gone: declining demotes and folds, it never deletes. Nothing stops
    being shown, or you could never audit what you were no longer being offered.
    """
    if not get_focus(slug):
        return [TextContent(type="text", text=f"No focus `{slug}`.")]
    judge(slug, kind, item_id or slugify(title)[:40], "declined", title, "", note)
    taste = focus_taste(slug)
    cooling = sorted((t for t in taste.items() if t[1] < 0), key=lambda x: x[1])[:5]
    msg = [f"Declined on **{slug}**: {title[:120]}", ""]
    if cooling:
        msg += ["Cooling on: " + ", ".join(f"{t} ({w})" for t, w in cooling)]
    msg += [f"Items scoring {MUTE_AT} or below are folded on the surface, not removed."]
    return [TextContent(type="text", text="\n".join(msg))]


@app.tool()
async def focus_safe(slug: str) -> list[TextContent]:
    """What is in a focus area's safe, and what it has learned to cool on."""
    if not get_focus(slug):
        return [TextContent(type="text", text=f"No focus `{slug}`.")]
    kept = focus_verdicts(slug, "kept")
    declined = focus_verdicts(slug, "declined")
    taste = focus_taste(slug)
    out = [f"# Safe — {slug}", "", f"{len(kept)} kept · {len(declined)} declined", ""]
    out += [f"- {k['created_at'][:10]} — {k['title'][:140]}" for k in kept[:30]] or \
           ["Nothing saved yet."]
    if taste:
        out += ["", "## Taste", ""]
        out += ["Drawn to: " + ", ".join(
            f"{t} (+{w})" for t, w in sorted(
                ((t, w) for t, w in taste.items() if w > 0), key=lambda x: -x[1])[:10])]
        out += ["Cooling on: " + ", ".join(
            f"{t} ({w})" for t, w in sorted(
                ((t, w) for t, w in taste.items() if w < 0), key=lambda x: x[1])[:10])]
    return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def focus_explore(slug: str, question: str) -> list[TextContent]:
    """Answer a question against a focus area's own corpus, notes and ideas.

    Retrieval only — this returns the material, it does not compose the answer.
    """
    if not get_focus(slug):
        return [TextContent(type="text", text=f"No focus `{slug}`.")]
    r = explore(slug, question, limit=8)
    if not r["total"]:
        return [TextContent(type="text", text=(
            f"Nothing in this focus touches that question yet — "
            f"which is itself worth knowing. Searched the indexed corpus, the "
            f"literature through this lens, and everything tagged `focus:{slug}`."))]
    out = [f"# {question}", "",
           f"From your own material only — {r['total']} item(s).", ""]
    if r["passages"]:
        out += ["## Indexed passages", ""]
        for p_ in r["passages"]:
            out += [f"**{p_['title'] or p_['source_file']}** · p.{p_['page_start']} "
                    f"· `{p_['layer']}`", f"> {(p_['chunk_text'] or '')[:400]}…", ""]
    if r["papers"]:
        out += ["## Literature", ""]
        out += [f"- {(x['pub'] or '')[:10]} — {x['title'][:130]}"
                + (f" · `{x['doi']}`" if x.get("doi") else "") for x in r["papers"]] + [""]
    if r["notes"] or r["ideas"]:
        out += ["## What you already thought", ""]
        out += [f"- 💡 {i['text'][:170]}" for i in r["ideas"]]
        out += [f"- 📝 {n_['title'] or n_['content'][:120]}" for n_ in r["notes"]]
    return [TextContent(type="text", text="\n".join(out))]
