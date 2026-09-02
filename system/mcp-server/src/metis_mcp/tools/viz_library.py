"""viz_library.py — a visualization library that ACCUMULATES.

WHAT THIS IS FOR
    the researcher, 2026-08-28: *"I think we should make like a database of beautiful
    visualizations... Every time i say i like a visualization the methodology,
    styling, ... will be saved so you can have multiple styles per type of
    visualization like charts, maps, ... how can we save the kind, methodology,
    styling if I ever want to reproduce any of these with other data?"*

THE PROBLEM THIS REPLACES
    Visualization Maker already advertised "7 visual styles" and "14 diagram
    types" — as PROSE, in `agents/visualization-maker/system-prompt.md`. Three
    consequences, all observable on 2026-08-28:

      1. Saying "I like this" could not add an 8th style. The list was editable
         only by hand-editing a markdown file.
      2. Nothing recorded which style was used for which figure.
         `outputs/visualizations/` held exactly ONE file after three months.
      3. Nothing was reproducible with other data, because the *method* was
         never separated from the *look*.

    A capability described in a prompt is a claim. A capability in a table is
    a capability.

WHY FOUR TABLES AND NOT ONE
    Because "multiple styles per type of visualization" is only expressible if
    kind, method and look vary independently. They do:

      viz_exemplars   what was admired, and WHERE IT CAME FROM.
                      Provenance is not decoration here — "reproduce this with
                      other data" is impossible if you cannot see what you were
                      imitating. An exemplar with no source is a rumour.

      viz_recipes     the METHOD. Survives a complete palette change.
                      The NYT mobility flow works because one dot is one
                      *person* rather than a rate — that choice is intact in
                      any colour scheme, and it is the half worth keeping.

      viz_styles      the LOOK. Reusable across recipes, and the reason the
                      same map can be rendered publication-austere for a paper
                      and editorial-bold for a briefing.

      viz_uses        every render: recipe x style x dataset x verdict.
                      This is the only table that can answer "styles that we
                      used", and it is what turns a liked figure into a ranked
                      default instead of a preference someone has to remember.

THE FIELD THAT DOES THE REAL WORK
    `viz_recipes.data_contract`. A JSON object of role -> what that role means:

        {"unit_id": "one row per person", "start_class": "origin quintile",
         "end_class": "adult quintile", "group": "comparison group"}

    Reproducing a figure with other data is mechanical ONLY if the recipe
    declares what SHAPE of data it needs. That contract is what `check_viz_fit`
    validates a real dataset against — the difference between a library and a
    scrapbook.

HOW FIT IS CHECKED, AND THE MISTAKE THAT SHAPED IT
    First attempt compared role names to column names by substring and reported
    a match score. The first honest test destroyed it: asked whether
    (patient_id, screening_mode, outcome, province) could feed a recipe needing
    (unit_id, start_class, end_class, group) — a dataset chosen BECAUSE it fits
    — it matched 0 of 4, the identical answer it gave for a dataset that cannot
    fit at all. Roles are abstract precisely so they do not carry any dataset's
    vocabulary, so that comparison could only ever fail.

    The damage was not the miss, it was answering the same way for a fit and a
    non-fit: a check that cannot fail differently is decoration.

    So the split is explicit, mirroring how `verification.py` is built. The
    MODEL proposes the role -> column mapping, because "screening_mode is the
    origin category here" is semantics. `check_viz_fit` contains no cleverness
    whatsoever — it only enforces that every role was accounted for, which is
    the part a model reliably forgets.

RETRIEVAL IS THE POINT, NOT STORAGE
    Eleven agent context files were once written and never read once
    (risk-mapping record, 2026-08). A library nothing reads is worse than no
    library, because it feels like progress. So `find_viz` is what the
    specialist is instructed to call BEFORE designing anything, and
    `viz_library_overview` backs an MCP resource so Claude Desktop sees the
    library with no client-specific work.

WHY THE LIBRARY LIVES HERE AND NOT IN A SKILL FILE
    Checked 2026-08-28: Anthropic's own `dataviz` / `artifact-design` /
    `artifact-diagramming` skills are delivered server-side to a Claude Code
    session. They are not in `~/.claude/plugins/` and not in the claude-code
    npm package, so they cannot be packaged for Desktop. Generic design sense
    is therefore NOT portable — but it is also not scarce, since every surface
    brings its own.

    What is irreplaceable is the researcher's accumulated taste. Putting that in the
    database rather than a skill file is what makes it reach Desktop, Cursor and
    anything else speaking MCP. The rule: never record a preference somewhere
    only one client can read.

NOT IN THIS MODULE, ON PURPOSE
    Rendering. A subagent's tool list is `Read, Write, Edit, Grep, Glob, Bash,
    mcp__metis-rc__*` — there is no Artifact tool below the main conversation,
    so the split is forced: this layer stores and retrieves, the specialist
    writes the file, and only the top-level session publishes it.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# The kinds are a closed list because an open one becomes 40 near-synonyms and
# then `find_viz(kind=...)` stops matching anything. "flow" is separate from
# "chart" because a transition between states is a different question from a
# comparison of magnitudes, and they are never styled the same way.
KINDS = ("chart", "map", "diagram", "flow", "table", "layout")

# What the researcher thought of the result. Three values, not five: the point is to rank
# defaults, and a scale with a comfortable middle collects everything.
VERDICTS = ("loved", "fine", "wrong")


_DDL_EXEMPLARS = """
CREATE TABLE IF NOT EXISTS viz_exemplars (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    source          TEXT DEFAULT '',      -- publication / author / team
    url             TEXT DEFAULT '',
    published       TEXT DEFAULT '',      -- date of the original, not of saving
    kind            TEXT DEFAULT '',      -- one of KINDS, best guess
    what_you_liked  TEXT DEFAULT '',      -- in the researcher's own words where possible
    screenshot_path TEXT DEFAULT '',
    unverified      TEXT DEFAULT '',      -- fields taken from memory, not read
    created_at      TEXT NOT NULL
)
"""

# `unverified` exists because the NYT page could not be fetched (it blocks
# automated requests) and the first record was written from knowledge of the
# piece. A field known to be unconfirmed must SAY so in the row, or the library
# quietly turns recollection into fact — the failure mode that cost nine
# corrected citations in the librarian pass of 2026-08-21.

_DDL_RECIPES = """
CREATE TABLE IF NOT EXISTS viz_recipes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    kind          TEXT NOT NULL,
    one_liner     TEXT DEFAULT '',
    encoding      TEXT DEFAULT '',        -- what maps to which channel
    mark_unit     TEXT DEFAULT '',        -- one dot = ? THE choice, usually
    data_contract TEXT DEFAULT '{}',      -- JSON: role -> meaning
    interaction   TEXT DEFAULT '',        -- static | hover | scroll-step | ...
    medium        TEXT DEFAULT '',        -- html/d3 | ggplot2 | plotly | svg
    code          TEXT DEFAULT '',
    caveats       TEXT DEFAULT '',        -- how this figure can mislead
    default_style TEXT DEFAULT '',        -- viz_styles.slug
    derived_from  TEXT DEFAULT '',        -- viz_exemplars.slug
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
)
"""

# `caveats` is mandatory in spirit even though SQLite cannot enforce it. Every
# recipe here is a persuasion device: the unit-dot flow implies individual
# trajectories the aggregate data does not license, and a choropleth of raw
# counts is a population map. Storing a method without storing how it lies would
# make this library a way to be confidently wrong faster. `check_viz_fit`
# therefore reprints the caveat at the moment of USE, which is when it matters —
# nobody rereads a caveat they wrote three months ago.

_DDL_STYLES = """
CREATE TABLE IF NOT EXISTS viz_styles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    one_liner       TEXT DEFAULT '',
    good_for        TEXT DEFAULT '',      -- paper | briefing | dashboard | talk
    palette         TEXT DEFAULT '',      -- hex values, sequence, role of each
    type_scale      TEXT DEFAULT '',      -- families, weights, sizes
    axis_treatment  TEXT DEFAULT '',      -- grid, ticks, spines
    annotation_rule TEXT DEFAULT '',      -- direct labels vs legend
    motion          TEXT DEFAULT '',      -- none | transition | scroll-driven
    theme_pair      TEXT DEFAULT '',      -- light/dark token pairs if any
    notes           TEXT DEFAULT '',
    derived_from    TEXT DEFAULT '',      -- viz_exemplars.slug
    unverified      TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
)
"""

_DDL_USES = """
CREATE TABLE IF NOT EXISTS viz_uses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe       TEXT NOT NULL,           -- viz_recipes.slug
    style        TEXT DEFAULT '',         -- viz_styles.slug
    dataset      TEXT DEFAULT '',         -- what it was rendered against
    project_id   TEXT DEFAULT '',
    output_path  TEXT DEFAULT '',
    artifact_url TEXT DEFAULT '',
    verdict      TEXT DEFAULT '',         -- one of VERDICTS, blank until judged
    note         TEXT DEFAULT '',
    created_at   TEXT NOT NULL
)
"""


def ensure_schema(con) -> None:
    con.execute(_DDL_EXEMPLARS)
    con.execute(_DDL_RECIPES)
    con.execute(_DDL_STYLES)
    con.execute(_DDL_USES)
    con.execute("CREATE INDEX IF NOT EXISTS idx_viz_recipes_kind "
                "ON viz_recipes(kind)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_viz_uses_recipe "
                "ON viz_uses(recipe, verdict)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_viz_uses_style "
                "ON viz_uses(style, verdict)")


def slugify(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")[:60]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_contract(raw: str) -> tuple[dict, str]:
    """Return (contract, error). An unparseable contract is refused, not stored.

    Storing '{bad json' would make the recipe look complete and fail only when
    someone tried to reuse it — months later, when the reason is forgotten.
    """
    if not (raw or "").strip():
        return {}, ""
    try:
        d = json.loads(raw)
    except Exception as exc:
        return {}, f"data_contract is not valid JSON ({exc})."
    if not isinstance(d, dict) or not all(isinstance(v, str) for v in d.values()):
        return {}, "data_contract must be a JSON object of role -> description."
    return d, ""


def _check_exemplar(con, slug: str) -> str:
    """Warn when `derived_from` points at no exemplar. Returns '' when fine.

    Found while seeding the first record: `slugify` truncates at 60 characters,
    so "…for-black-boys" became "…for-black-boy" and the four rows written
    against the hand-typed slug all pointed at nothing. Nothing complained.

    A dangling provenance link is the one failure this library cannot tolerate
    quietly — provenance is the entire reason the exemplar table exists, so a
    broken link turns a checkable record back into a rumour while still looking
    complete. Warns rather than refuses, and offers the near match, because the
    write is worth keeping and the fix is a one-line correction.
    """
    if not (slug or "").strip():
        return ""
    if con.execute("SELECT 1 FROM viz_exemplars WHERE slug = ?", (slug,)).fetchone():
        return ""
    near = con.execute(
        "SELECT slug FROM viz_exemplars WHERE slug LIKE ? LIMIT 1",
        (slug[:40] + "%",)).fetchone()
    hint = f" Did you mean `{near['slug']}`?" if near else ""
    return (f"\n\n⚠ `derived_from=\"{slug}\"` matches no exemplar, so this row's "
            f"provenance is dangling.{hint} Slugs are truncated to 60 chars — read "
            f"the slug back from save_viz_exemplar rather than retyping the title.")


def _validate_mapping(contract: dict, mapping: dict, columns: list[str]) -> dict:
    """Check an EXPLICIT role -> column mapping. Contains no guessing at all.

    See the module docstring for why name similarity was removed. This function
    enforces completeness and nothing else: every role accounted for, every
    mapped column actually present, nothing mapped that the recipe never asked
    for. The semantics are the model's job; the bookkeeping is this function's.
    """
    cols = {c.lower(): c for c in columns}
    unmapped = [r for r in contract
                if r not in mapping or not str(mapping[r]).strip()]
    absent = [f"{r} → {mapping[r]}" for r in mapping
              if r in contract and columns and str(mapping[r]).lower() not in cols]
    unknown = [r for r in mapping if r not in contract]
    used = {str(v).lower() for v in mapping.values()}
    spare = [cols[c] for c in cols if c not in used] if columns else []
    return {"unmapped": unmapped, "absent": absent, "unknown": unknown,
            "spare": spare, "ready": not unmapped and not absent}


def _fmt_recipe(row, con) -> str:
    contract, _ = _parse_contract(row["data_contract"])
    uses = con.execute(
        "SELECT verdict, COUNT(*) n FROM viz_uses WHERE recipe = ? GROUP BY verdict",
        (row["slug"],)).fetchall()
    tally = ", ".join(f"{u['n']} {u['verdict'] or 'unjudged'}" for u in uses) or "never used"
    lines = [
        f"### {row['name']}  ·  `{row['slug']}`  ·  {row['kind']}",
        row["one_liner"] or "",
        f"- **Mark unit:** {row['mark_unit']}" if row["mark_unit"] else "",
        f"- **Encoding:** {row['encoding']}" if row["encoding"] else "",
        f"- **Interaction:** {row['interaction']}" if row["interaction"] else "",
        f"- **Medium:** {row['medium']}" if row["medium"] else "",
        ("- **Needs:** " + ", ".join(f"`{k}` ({v})" for k, v in contract.items()))
        if contract else "",
        f"- **Caveat:** {row['caveats']}" if row["caveats"] else "",
        f"- **Default style:** `{row['default_style']}`" if row["default_style"] else "",
        f"- **From:** `{row['derived_from']}`" if row["derived_from"] else "",
        f"- **Track record:** {tally}",
    ]
    return "\n".join(x for x in lines if x)


def _fmt_style(row, con) -> str:
    hit = con.execute(
        "SELECT COUNT(*) n FROM viz_uses WHERE style = ? AND verdict = 'loved'",
        (row["slug"],)).fetchone()
    loved = hit["n"] if hit else 0
    lines = [
        f"### {row['name']}  ·  `{row['slug']}`",
        row["one_liner"] or "",
        f"- **Good for:** {row['good_for']}" if row["good_for"] else "",
        f"- **Palette:** {row['palette']}" if row["palette"] else "",
        f"- **Type:** {row['type_scale']}" if row["type_scale"] else "",
        f"- **Axes/grid:** {row['axis_treatment']}" if row["axis_treatment"] else "",
        f"- **Annotation:** {row['annotation_rule']}" if row["annotation_rule"] else "",
        f"- **Motion:** {row['motion']}" if row["motion"] else "",
        f"- **From:** `{row['derived_from']}`" if row["derived_from"] else "",
        f"- ⚠ **Unverified:** {row['unverified']}" if row["unverified"] else "",
        f"- **Loved renders:** {loved}",
    ]
    return "\n".join(x for x in lines if x)


def library_overview() -> str:
    """Markdown summary of the whole library. Also backs `metis://viz-styles`."""
    with connect(paths.db) as con:
        ensure_schema(con)
        styles = con.execute("SELECT * FROM viz_styles ORDER BY name").fetchall()
        recipes = con.execute("SELECT * FROM viz_recipes ORDER BY kind, name").fetchall()
        n_ex = con.execute("SELECT COUNT(*) n FROM viz_exemplars").fetchone()["n"]
        n_uses = con.execute("SELECT COUNT(*) n FROM viz_uses").fetchone()["n"]

        if not styles and not recipes:
            return ("# Visualization library\n\nEmpty. Nothing has been saved yet — "
                    "say what you liked about a figure and it gets recorded, rather "
                    "than the library inventing a house style nobody chose.")

        out = ["# Visualization library",
               f"{len(recipes)} recipes · {len(styles)} styles · "
               f"{n_ex} exemplars · {n_uses} recorded renders", ""]
        if styles:
            out += ["## Styles — the look", ""]
            out += [_fmt_style(s, con) + "\n" for s in styles]
        if recipes:
            out += ["## Recipes — the method", ""]
            out += [_fmt_recipe(r, con) + "\n" for r in recipes]
        out += ["---",
                "A recipe is reusable with new data when every role on its **Needs** "
                "line can be mapped to a column you have. Propose that mapping and "
                "confirm it with `check_viz_fit` — the contract is stored precisely "
                "so this stops being a judgement call."]
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

@app.tool()
async def save_viz_exemplar(
    title: str,
    what_you_liked: str,
    url: str = "",
    source: str = "",
    published: str = "",
    kind: str = "",
    screenshot_path: str = "",
    unverified: str = "",
) -> list[TextContent]:
    """Record a visualization you admired, and why. The provenance layer.

    Call this the moment the researcher says he likes something. It is the cheapest of the
    three writes and the one that makes the other two honest: a recipe whose
    origin is unrecorded cannot be checked against the thing it came from.

    Args:
        title: What the piece is called.
        what_you_liked: In his own words where possible. The most valuable field
            in the row — "I like it" is not reusable, "the labels sit on the
            marks instead of in a legend" is.
        url: Where it lives.
        source: Publication, team or author.
        published: Date of the ORIGINAL, not of saving.
        kind: chart | map | diagram | flow | table | layout.
        screenshot_path: Local image, if the page cannot be refetched later.
        unverified: Anything in this row written from memory rather than a read.
            Say so here; a library that launders recollection into fact is worse
            than an empty one.

    Returns:
        The stored exemplar and its slug — use that slug verbatim as
        `derived_from`, since slugs are truncated to 60 characters.
    """
    if kind and kind not in KINDS:
        return [TextContent(type="text", text=f"kind must be one of {', '.join(KINDS)}.")]
    slug = slugify(title)
    if not slug:
        return [TextContent(type="text", text="A title is required.")]
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute(
            "INSERT INTO viz_exemplars (slug, title, source, url, published, kind, "
            "what_you_liked, screenshot_path, unverified, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(slug) DO UPDATE SET title=excluded.title, "
            "source=excluded.source, url=excluded.url, published=excluded.published, "
            "kind=excluded.kind, what_you_liked=excluded.what_you_liked, "
            "screenshot_path=excluded.screenshot_path, unverified=excluded.unverified",
            (slug, title, source, url, published, kind, what_you_liked,
             screenshot_path, unverified, _now()))
    warn = f"\n\n⚠ Marked unverified: {unverified}" if unverified else ""
    return [TextContent(type="text", text=(
        f"Saved exemplar `{slug}` — {title}"
        f"{f' ({source})' if source else ''}.\n\n"
        f"What you liked: {what_you_liked}\n\n"
        f"Next: pull the METHOD out of it with save_viz_recipe(derived_from=\"{slug}\") "
        f"and the LOOK with save_viz_style(derived_from=\"{slug}\"). Keeping them "
        f"apart is what lets the method survive a palette change. Copy that slug "
        f"exactly — it is truncated, not the title.{warn}"))]


@app.tool()
async def save_viz_recipe(
    name: str,
    kind: str,
    one_liner: str = "",
    encoding: str = "",
    mark_unit: str = "",
    data_contract: str = "",
    interaction: str = "",
    medium: str = "",
    code: str = "",
    caveats: str = "",
    default_style: str = "",
    derived_from: str = "",
) -> list[TextContent]:
    """Store the METHOD of a visualization — the half that survives a restyle.

    A recipe is what makes a figure work: what the mark represents, what maps to
    which channel, and what data shape it demands. Not the colours.

    Args:
        name: Descriptive, e.g. "unit-dot transition flow".
        kind: chart | map | diagram | flow | table | layout.
        one_liner: What it shows, and why that framing beats the obvious one.
        encoding: What maps to position, colour, size, order.
        mark_unit: What ONE mark is. Usually the decisive choice — "one dot =
            one person" and "one bar = a percentage" are different arguments
            about the same numbers.
        data_contract: JSON object of role -> meaning, e.g.
            '{"unit_id":"one row per person","start_class":"origin group",
              "end_class":"destination group"}'
            The field that makes reuse mechanical. Without it the recipe is a
            description; with it, a dataset can be checked against it.
        interaction: static | hover | scroll-step | click-filter | animated.
        medium: html/d3 | ggplot2 | plotly | svg | leaflet.
        code: Working code if there is any. Never required — a recipe with a
            precise contract and no code is still reusable.
        caveats: How this figure can mislead. Please fill this in; a stored
            method with no stored failure mode is a way to be wrong faster.
        default_style: viz_styles.slug to use unless told otherwise.
        derived_from: viz_exemplars.slug this came from, copied verbatim.

    Returns:
        The stored recipe, plus warnings for anything left dangling.
    """
    if kind not in KINDS:
        return [TextContent(type="text", text=f"kind must be one of {', '.join(KINDS)}.")]
    contract, err = _parse_contract(data_contract)
    if err:
        return [TextContent(type="text", text=(
            err + "\n\nExpected shape:\n"
            '{"unit_id": "one row per person", "start_class": "origin group", '
            '"end_class": "destination group"}'))]
    slug = slugify(name)
    if not slug:
        return [TextContent(type="text", text="A name is required.")]
    now = _now()
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute(
            "INSERT INTO viz_recipes (slug, name, kind, one_liner, encoding, mark_unit, "
            "data_contract, interaction, medium, code, caveats, default_style, "
            "derived_from, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(slug) DO UPDATE SET name=excluded.name, kind=excluded.kind, "
            "one_liner=excluded.one_liner, encoding=excluded.encoding, "
            "mark_unit=excluded.mark_unit, data_contract=excluded.data_contract, "
            "interaction=excluded.interaction, medium=excluded.medium, "
            "code=excluded.code, caveats=excluded.caveats, "
            "default_style=excluded.default_style, derived_from=excluded.derived_from, "
            "updated_at=excluded.updated_at",
            (slug, name, kind, one_liner, encoding, mark_unit,
             json.dumps(contract), interaction, medium, code, caveats,
             default_style, derived_from, now, now))
        row = con.execute("SELECT * FROM viz_recipes WHERE slug = ?", (slug,)).fetchone()
        body = _fmt_recipe(row, con)
        dangling = _check_exemplar(con, derived_from)
    nudge = ("" if caveats else
             "\n\n⚠ No caveat recorded. Every recipe here is a persuasion device — "
             "note how this one can mislead before it gets reused on real data.")
    if not contract:
        nudge += ("\n\n⚠ No data_contract. Without it this recipe cannot be checked "
                  "against a dataset later, which is the whole point of storing it.")
    return [TextContent(type="text",
                        text=f"Saved recipe `{slug}`.\n\n{body}{nudge}{dangling}")]


@app.tool()
async def save_viz_style(
    name: str,
    one_liner: str = "",
    good_for: str = "",
    palette: str = "",
    type_scale: str = "",
    axis_treatment: str = "",
    annotation_rule: str = "",
    motion: str = "",
    theme_pair: str = "",
    notes: str = "",
    derived_from: str = "",
    unverified: str = "",
) -> list[TextContent]:
    """Store the LOOK of a visualization, reusable across recipes.

    Styles are rows here rather than prose in an agent prompt for one reason:
    prose cannot be added to by saying "I like this". Before this table, the
    seven styles Visualization Maker claimed were hand-edited markdown, and no
    eighth was ever added.

    Args:
        name: e.g. "Upshot editorial", "ITG paper austere".
        one_liner: The feel, in one sentence.
        good_for: paper | briefing | dashboard | talk | poster.
        palette: Hex values AND what each one means. A palette whose roles are
            unrecorded gets reused wrongly.
        type_scale: Families, weights, sizes.
        axis_treatment: Grid, ticks, spines — usually how much to erase.
        annotation_rule: Direct labels vs legend, and title voice. Often the
            most transferable single rule a style has.
        motion: none | transition | scroll-driven.
        theme_pair: Light/dark token pairs, if the style has both.
        notes: Anything else worth carrying.
        derived_from: viz_exemplars.slug, copied verbatim.
        unverified: Fields written from memory rather than measured off the
            original. Exact hex values are the usual case.

    Returns:
        The stored style.
    """
    slug = slugify(name)
    if not slug:
        return [TextContent(type="text", text="A name is required.")]
    now = _now()
    with connect(paths.db) as con:
        ensure_schema(con)
        con.execute(
            "INSERT INTO viz_styles (slug, name, one_liner, good_for, palette, "
            "type_scale, axis_treatment, annotation_rule, motion, theme_pair, notes, "
            "derived_from, unverified, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(slug) DO UPDATE SET name=excluded.name, "
            "one_liner=excluded.one_liner, good_for=excluded.good_for, "
            "palette=excluded.palette, type_scale=excluded.type_scale, "
            "axis_treatment=excluded.axis_treatment, "
            "annotation_rule=excluded.annotation_rule, motion=excluded.motion, "
            "theme_pair=excluded.theme_pair, notes=excluded.notes, "
            "derived_from=excluded.derived_from, unverified=excluded.unverified, "
            "updated_at=excluded.updated_at",
            (slug, name, one_liner, good_for, palette, type_scale, axis_treatment,
             annotation_rule, motion, theme_pair, notes, derived_from, unverified,
             now, now))
        row = con.execute("SELECT * FROM viz_styles WHERE slug = ?", (slug,)).fetchone()
        body = _fmt_style(row, con)
        dangling = _check_exemplar(con, derived_from)
    return [TextContent(type="text", text=f"Saved style `{slug}`.\n\n{body}{dangling}")]


# ---------------------------------------------------------------------------
# Retrieval — the half that decides whether any of this was worth writing
# ---------------------------------------------------------------------------

@app.tool()
async def find_viz(
    kind: str = "",
    intent: str = "",
    limit: int = 8,
) -> list[TextContent]:
    """Find saved recipes and styles before building anything. Call this FIRST.

    This is the tool the whole library exists to serve. Eleven agent context
    files were once written and never read once — a store nothing queries is
    worse than no store, because it looks like progress. So: consult this before
    designing a figure, not after.

    Each recipe prints a **Needs** line: the roles its data contract demands. To
    check a specific dataset against one, propose a role -> column mapping and
    confirm it with `check_viz_fit`. This tool deliberately will not guess that
    mapping — a name-similarity guess was tried here and could not tell a
    fitting dataset from an unfitting one.

    Args:
        kind: chart | map | diagram | flow | table | layout. Blank = all.
        intent: Free text matched against names, one-liners, encodings and
            media, e.g. "show dispersion not averages", "for a paper".
        limit: Max recipes to return.

    Returns:
        Matching recipes with their contracts and track records, plus candidate
        styles ranked by how often they were loved.
    """
    kind = (kind or "").strip()
    if kind and kind not in KINDS:
        return [TextContent(type="text", text=f"kind must be one of {', '.join(KINDS)}.")]
    terms = [t for t in re.split(r"[,\s]+", (intent or "").lower()) if len(t) > 2]

    with connect(paths.db) as con:
        ensure_schema(con)
        sql = "SELECT * FROM viz_recipes"
        params: list = []
        if kind:
            sql += " WHERE kind = ?"
            params.append(kind)
        rows = con.execute(sql, params).fetchall()
        if not rows:
            return [TextContent(type="text", text=(
                "Nothing saved for that yet."
                + (f" No `{kind}` recipes exist." if kind else "")
                + "\n\nThat is a real answer, not a failure — build it from first "
                  "principles, then save what worked so the next one starts here."))]

        def score(r) -> int:
            hay = " ".join(str(r[k] or "").lower() for k in
                           ("name", "one_liner", "encoding", "mark_unit",
                            "interaction", "medium"))
            return sum(1 for t in terms if t in hay)

        rows = sorted(rows, key=score, reverse=True)[:max(1, limit)]

        out = ["# Matches" + (f" · {kind}" if kind else "")]
        if intent:
            out.append(f"Intent: *{intent}*")
        out.append("")
        for r in rows:
            out.append(_fmt_recipe(r, con))
            out.append("")

        styles = con.execute(
            "SELECT s.*, (SELECT COUNT(*) FROM viz_uses u WHERE u.style = s.slug "
            "AND u.verdict = 'loved') loved FROM viz_styles s "
            "ORDER BY loved DESC, s.name").fetchall()
        if styles:
            out += ["## Styles to render these in", ""]
            out += [_fmt_style(s, con) + "\n" for s in styles[:6]]
        out += ["---",
                "To reuse one on real data: map every role on its **Needs** line to a "
                "column and confirm with `check_viz_fit(recipe=..., mapping=...)`."]
        return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def check_viz_fit(
    recipe: str,
    mapping: str,
    columns: str = "",
) -> list[TextContent]:
    """Check that a dataset can feed a saved recipe. YOU propose the mapping.

    The tool that makes "reproduce this with other data" a check rather than a
    hunch — and it contains no cleverness on purpose. Reading that
    `screening_mode` is the origin category in this dataset is semantics, which
    is your job. Confirming that every role was accounted for, that each column
    named actually exists, and that nothing was mapped which the recipe never
    asked for is bookkeeping, which is this tool's job.

    An earlier version guessed the mapping by comparing role names to column
    names. It reported the same "0 matched" for a dataset built to fit and one
    that could not fit at all, because roles are abstract precisely so they
    carry no dataset's vocabulary. A check that cannot fail differently is
    decoration, so it was removed.

    Args:
        recipe: viz_recipes.slug.
        mapping: JSON object of role -> column in YOUR data, e.g.
            '{"unit_id":"health_zone","start_class":"endemicity_2015",
              "end_class":"endemicity_2025","group":"province"}'
        columns: Optional comma-separated full column list. Supply it and the
            check also catches a column you named that does not exist, plus
            reports what is left unused.

    Returns:
        Ready or not-ready, what is missing, and the recipe's caveats — reprinted
        here because the moment of use is when a caveat is actually read.
    """
    with connect(paths.db) as con:
        ensure_schema(con)
        row = con.execute("SELECT * FROM viz_recipes WHERE slug = ?", (recipe,)).fetchone()
        if not row:
            have = [r["slug"] for r in
                    con.execute("SELECT slug FROM viz_recipes ORDER BY slug").fetchall()]
            return [TextContent(type="text", text=(
                f"No recipe `{recipe}`.\n\nSaved recipes: "
                + (", ".join(f"`{h}`" for h in have) if have else "none yet.")))]
        contract, _ = _parse_contract(row["data_contract"])
        caveats = row["caveats"]
        style = row["default_style"]

    if not contract:
        return [TextContent(type="text", text=(
            f"`{recipe}` has no data_contract, so there is nothing to check against. "
            f"Fill it in with save_viz_recipe — the contract is what makes a recipe "
            f"reusable rather than merely described."))]
    try:
        m = json.loads(mapping)
        assert isinstance(m, dict)
    except Exception:
        return [TextContent(type="text", text=(
            "mapping must be a JSON object of role -> column. Roles this recipe "
            "needs:\n" + "\n".join(f"  {k}: {v}" for k, v in contract.items())))]

    cols = [c for c in re.split(r"[,\s]+", columns or "") if c]
    v = _validate_mapping(contract, m, cols)

    out = [f"# {'✅ Ready' if v['ready'] else '⚠ Not ready'} — `{recipe}`", "", "**Mapping**"]
    for role, why in contract.items():
        got = m.get(role, "")
        ok = bool(str(got).strip()) and f"{role} → {got}" not in v["absent"]
        out.append(f"- {'✅' if ok else '❌'} `{role}` ({why}) ← "
                   f"**{got or 'UNMAPPED'}**")
    if v["absent"]:
        out += ["", "**Named but not in your column list:** "
                + ", ".join(f"`{a}`" for a in v["absent"])]
    if v["unknown"]:
        out += ["", "**Mapped but not required** (harmless, possibly a typo): "
                + ", ".join(f"`{u}`" for u in v["unknown"])]
    if v["spare"]:
        out += ["", "**Unused columns:** " + ", ".join(f"`{s}`" for s in v["spare"])]

    if v["ready"]:
        out += ["", f"This dataset can feed `{recipe}`."
                + (f" Default style: `{style}`." if style else "")]
    else:
        if v["unmapped"]:
            out += ["", "Unmapped roles: "
                    + ", ".join(f"`{u}`" for u in v["unmapped"])
                    + ". Either derive them from what you have, or this is the wrong "
                      "recipe for this data — both are fine answers, skipping them is not."]

    if caveats:
        out += ["", "## Read before rendering", caveats]
    return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def record_viz_use(
    recipe: str,
    style: str = "",
    dataset: str = "",
    project_id: str = "",
    output_path: str = "",
    artifact_url: str = "",
    verdict: str = "",
    note: str = "",
) -> list[TextContent]:
    """Log that a recipe was rendered — and what the researcher thought of it.

    The table that answers "styles that we used". Without it the library holds
    intentions and no evidence, so nothing can be ranked and every session
    re-argues which style to reach for.

    Args:
        recipe: viz_recipes.slug.
        style: viz_styles.slug.
        dataset: What it was rendered against, in plain words.
        project_id: e.g. "angola-hat-analysis".
        output_path: Local file written.
        artifact_url: If it was published as an Artifact.
        verdict: loved | fine | wrong. Leave blank until he has actually said —
            a guessed verdict poisons the ranking it feeds.
        note: What worked, or what went wrong.

    Returns:
        Confirmation plus the recipe's running track record.
    """
    if verdict and verdict not in VERDICTS:
        return [TextContent(type="text",
                            text=f"verdict must be one of {', '.join(VERDICTS)}.")]
    with connect(paths.db) as con:
        ensure_schema(con)
        if not con.execute("SELECT 1 FROM viz_recipes WHERE slug = ?", (recipe,)).fetchone():
            return [TextContent(type="text", text=(
                f"No recipe `{recipe}`. Save it with save_viz_recipe first — a use "
                f"logged against a recipe that does not exist is an orphan row."))]
        con.execute(
            "INSERT INTO viz_uses (recipe, style, dataset, project_id, output_path, "
            "artifact_url, verdict, note, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (recipe, style, dataset, project_id, output_path, artifact_url,
             verdict, note, _now()))
        tally = con.execute(
            "SELECT verdict, COUNT(*) n FROM viz_uses WHERE recipe = ? GROUP BY verdict",
            (recipe,)).fetchall()
    line = ", ".join(f"{t['n']} {t['verdict'] or 'unjudged'}" for t in tally)
    tip = ("" if verdict else
           "\n\nNo verdict yet — set it once he has said, since the verdict is what "
           "ranks defaults next time.")
    return [TextContent(type="text", text=(
        f"Logged: `{recipe}`"
        f"{f' in `{style}`' if style else ''}"
        f"{f' on {dataset}' if dataset else ''}.\n\n"
        f"Track record for this recipe: {line}.{tip}"))]


@app.tool()
async def viz_library_overview() -> list[TextContent]:
    """Show the whole visualization library — every style, every recipe.

    Read this when the researcher asks what styles exist, or before offering him a choice
    of look. The same text is served as the `metis://viz-styles` resource, so
    Claude Desktop sees it without any client-specific work.

    Returns:
        Markdown: styles with their loved-render counts, recipes with their data
        contracts and track records.
    """
    return [TextContent(type="text", text=library_overview())]


@app.resource("metis://viz-styles", name="Metis — visualization library",
              mime_type="text/markdown")
def viz_styles_resource() -> str:
    """Saved visual styles and reusable figure methods, with their track records.

    Exposed as a resource on purpose. Anthropic's design skills are Claude Code
    only; the researcher's accumulated taste has to reach every client, and a resource is
    the one primitive the CLIENT attaches without being asked.
    """
    return library_overview()
