"""User profile tool — returns identity, interests, style, and preferences.

Agents call this at the start of personalised runs to understand the user's
research topics, news signals, and communication style to adopt.
"""

import json

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths


def _read_prefs() -> dict:
    prefs_path = paths.root / "system" / "config" / "user-preferences.json"
    if prefs_path.exists():
        try:
            return json.loads(prefs_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _read_style() -> dict:
    """Load communication-style settings from user-config.yaml (style: block)
    and user-preferences.json (persona_* keys). YAML is the canonical source
    (set by /metis_config wizard); JSON overrides let the dashboard panel
    update individual settings without touching the YAML."""
    style: dict = {}
    # 1. YAML base (user-config.yaml → style: block)
    yaml_path = paths.root / "system" / "config" / "user-config.yaml"
    if yaml_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            raw = cfg.get("style") or {}
            if isinstance(raw, dict):
                style.update(raw)
        except Exception:
            pass
    # 2. JSON overlay (user-preferences.json → persona_* keys)
    prefs = _read_prefs()
    for key in ("response_length", "feedback_style", "challenge_level",
                "warmth", "detail_level", "routing_verbosity"):
        pkey = f"persona_{key}"
        if pkey in prefs:
            style[key] = prefs[pkey]
        elif key in prefs:
            style[key] = prefs[key]
    return style


# ═══════════════════════════════════════════════════════════════════════════════
# NEWS INTERESTS AND LIBRARY INTERESTS ARE TWO DIFFERENT THINGS.
#
# They serve different purposes and either may sit outside the person's actual
# work:
#
#   news_interests    — what they want to know is HAPPENING. Drives the story-
#                       thread vocabulary, the News category tabs, and what the
#                       daily/weekly briefings monitor. Can be pure curiosity:
#                       someone may follow AI policy or a conflict closely
#                       without ever publishing on it.
#   library_interests — what they want a SCIENTIFIC BACKGROUND on. Drives
#                       literature relevance, which journal feeds matter, and the
#                       background/RAG corpus. This is a slower, deeper list, and
#                       it can also reach past their current projects — a method
#                       they intend to learn belongs here long before it appears
#                       in their work.
#
# They overlap often and are not the same, so Metis stores them separately.
# `interests` is kept as the union for the many callers that just want "who is
# this person", and `news_topics` as an alias of news_interests, so nothing that
# reads the old fields breaks.
#
# Crucially, NEITHER is derived from having projects. Someone can sign up to
# Metis with no projects and no articles at all, and both lists must still be
# fillable — the interview asks, it does not infer.
# ═══════════════════════════════════════════════════════════════════════════════

# Legacy → new field mapping, applied lazily on read so existing installs need no
# migration step: the old `interests` was in practice a research-subject list
# (library-shaped) and the old `news_topics` was a monitoring list (news-shaped).
_LEGACY_LIBRARY = ("interests",)
_LEGACY_NEWS = ("news_topics",)


def read_interest_lists() -> dict:
    """Return {news: [...], library: [...], union: [...]} from all sources.

    Reads the new fields first and falls back to the legacy ones, so this is safe
    on an install that has never been through the interview. Also folds in
    user-config.yaml `research.*` (written by the /metis-config wizard) on the
    LIBRARY side, because a declared research field is background material rather
    than a news signal.
    """
    prefs = _read_prefs()

    def _lst(d, key):
        v = d.get(key) or []
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []

    news = _lst(prefs, "news_interests")
    library = _lst(prefs, "library_interests")

    if not news:
        for k in _LEGACY_NEWS:
            news += _lst(prefs, k)
    if not library:
        for k in _LEGACY_LIBRARY:
            library += _lst(prefs, k)

    # The install wizard's research block is background, not news.
    try:
        import yaml as _yaml
        cfg_path = paths.root / "system" / "config" / "user-config.yaml"
        if cfg_path.exists():
            cfg = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            research = cfg.get("research") or {}
            for field in ("topics", "subfields", "methods"):
                library += _lst(research, field)
    except Exception:
        pass

    def _dedupe(xs):
        seen, out = set(), []
        for x in xs:
            k = x.lower()
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out

    news, library = _dedupe(news), _dedupe(library)
    # `declared` means the person actually chose these, as opposed to them being
    # inherited from the install wizard's research block. The difference matters:
    # inherited topics are a reasonable default but nobody confirmed them, so a
    # caller deciding whether to OFFER the interview should look at this rather
    # than at whether the lists happen to be non-empty.
    declared_news = bool(prefs.get("news_interests") or prefs.get("news_topics"))
    declared_library = bool(prefs.get("library_interests") or prefs.get("interests"))
    return {
        "news": news,
        "library": library,
        "union": _dedupe(news + library),
        "declared_news": declared_news,
        "declared_library": declared_library,
        "declared": declared_news and declared_library,
    }


INTEREST_INTERVIEW = """\
Interview the person to work out TWO SEPARATE interest lists, then save them.

Do NOT ask them to produce a list — that is the part people find hard, and it is
why the interests field sits empty. Ask questions, one or two at a time, and keep
going until the terms are specific enough to actually filter with.

THE TWO LISTS ARE DIFFERENT THINGS. Explain this early, in plain language,
because it changes their answers:

  NEWS interests    — what they want to know is happening. Drives what the News
                      surface tracks and groups, and what the daily and weekly
                      briefings monitor. This is allowed to be pure curiosity:
                      following AI policy, a conflict, or a country closely
                      without ever working on it is a perfectly good reason.

  LIBRARY interests — what they want a real scientific background on. Drives
                      which literature is collected and what the knowledge layer
                      is built from. Slower and deeper. Also allowed outside
                      their current work: a method they intend to learn belongs
                      here long before it shows up in a project.

They overlap — a core subject is usually in both — but they are not the same, and
the differences are the useful part. Someone may want daily news on an outbreak
they will never publish on, and a deep library on a statistical method that never
makes the news.

## Start where they are

Call get_user_profile(). Then, ONLY if it is likely to help, look at
get_project_status() and get_ideas().

**Do not depend on any of that existing.** A person may be brand new to Metis with
no projects, no articles and no library — that is a completely normal starting
point, not an incomplete setup. If there is nothing to draw on, do not comment on
the absence or ask them to set projects up first. Just ask them directly what they
work on, or what they are training in, or what they are simply interested in.
Someone can be a student, between jobs, or exploring a new field.

If there IS existing work, say what you inferred from it and check it with them
rather than assuming. Frame it as a proposal: "based on your projects it looks
like X and Y — is that right, and what's missing?"

## What to ask

Adapt the order and skip what does not apply.

1. What do they spend their time on — or want to? Diseases, methods, places,
   systems. Push for concrete: a specific disease and a specific country beats a
   field name.
2. **What would they want to hear about even if it were nothing to do with their
   work?** This is the most important question and the one nobody volunteers.
   It is where most NEWS interests come from.
3. What do they want to understand properly, rather than just hear about? Methods
   they keep meaning to learn, a field they are moving into, a debate they want
   the primary literature on. These are LIBRARY interests.
4. What do they NOT want in a briefing? What they would skim past. Knowing what
   to leave out matters as much as what to include.
5. Which places matter, and at what level — country, region, continent?
6. Anything outside their field entirely that they follow?

Propose candidate terms back as you go and let them correct you. If they offer
something broad like "global health", push back: ask what specifically within it,
because a term that broad cannot filter anything.

## Finish

Show BOTH lists separately for confirmation and let them move terms between them.
Aim for roughly 6-15 news interests and 6-20 library interests — enough to be
specific, few enough to mean something. Either list may be short; a person with
three sharp news interests is better served than one with twenty vague ones.

Then call:
  set_research_interests(
      news_interests=[...],
      library_interests=[...],
      role="..."          # optional, only if they gave you one
  )

Say plainly what changes as a result: the News surface tabs and briefings follow
the news list, the literature collection and knowledge layer follow the library
list.

Finally: interests drift. Suggest when they should do this again, and mention they
can re-run it any time from the "refine" link on the Metis Systems surface.
"""


def _mine_work_terms(limit: int = 40) -> list[tuple[str, int, str]]:
    """Terms that recur across the researcher's own work, with where they came from.

    Interests should not depend on the person being able to articulate them. Their
    work already states them: project titles and descriptions, ideas they captured,
    what their papers are about, and what their sessions keep returning to. This
    counts recurring domain terms across those sources so Metis can propose
    interests instead of waiting to be told.

    Returns [(term, weight, source_summary)], strongest first. Weight is the number
    of distinct places the term appears — a term in one project title is a guess, a
    term in four projects and twenty sessions is a fact about them.
    """
    import sqlite3 as _sq
    import re as _re
    from collections import Counter

    if not paths.db.exists():
        return []

    STOP = {
        "the", "and", "for", "with", "from", "that", "this", "have", "has", "was",
        "are", "its", "into", "over", "what", "when", "where", "which", "how",
        "why", "you", "your", "can", "should", "would", "could", "about", "there",
        "their", "make", "made", "does", "did", "not", "but", "all", "any", "get",
        "metis", "project", "analysis", "data", "using", "based", "study", "paper",
        "article", "draft", "review", "session", "work", "working", "new", "add",
        "added", "fix", "fixed", "build", "built", "update", "updated", "test",
        "tests", "file", "files", "code", "script", "scripts", "dashboard",
        "surface", "tool", "tools", "user", "claude", "memory", "system",
        # Words that scored highly but name a FORMAT or an activity rather than a
        # subject. "framework", "course" and "statistics" all ranked top-15 on a
        # real corpus and none of them is an interest — they describe what the researcher is
        # making, not what it is about. Compound terms survive this list, so
        # "scan statistics" (a genuine spatial method) still comes through while
        # bare "statistics" does not.
        "framework", "course", "courses", "report", "reports", "chapter",
        "results", "methods", "method", "approach", "model", "models",
        "statistics", "statistical", "protocol", "manuscript", "thesis",
        "scan", "scans", "plan", "planning", "notes", "meeting", "meetings",
        "human", "african", "people", "patients", "cases", "control",
        "health", "disease", "diseases", "public", "global", "national",
        "based", "level", "levels", "high", "low", "large", "small",
        "first", "second", "third", "week", "month", "year", "years",
    }

    # (sql, column, source label, weight per hit) — sessions are weighted lower
    # because they are numerous and describe process as much as subject.
    SOURCES = [
        ("SELECT title || ' ' || COALESCE(description,'') t FROM projects "
         "WHERE status='active'", "projects", 3),
        ("SELECT text t FROM ideas ORDER BY created_at DESC LIMIT 60", "ideas", 2),
        ("SELECT title t FROM literature_metadata ORDER BY created_at DESC LIMIT 300",
         "library", 2),
        ("SELECT COALESCE(key_topics,'') t FROM session_summaries "
         "WHERE COALESCE(archived,0)=0 ORDER BY created_at DESC LIMIT 200",
         "sessions", 1),
    ]

    scores: Counter = Counter()
    origins: dict[str, set[str]] = {}
    conn = _sq.connect(str(paths.db))
    conn.row_factory = _sq.Row
    try:
        for sql, label, weight in SOURCES:
            try:
                rows = conn.execute(sql).fetchall()
            except _sq.Error:
                continue
            for r in rows:
                text = str(r["t"] or "").lower()
                # Some stored text is JSON-escaped, so a literal "\u2014" (an em
                # dash) survives into the word stream and mined as a term
                # ("clinique u2014"). Decode the escapes, then drop any residue.
                if "\\u" in text or "u20" in text:
                    try:
                        text = text.encode().decode("unicode_escape")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass
                    text = _re.sub(r"\bu[0-9a-f]{4}\b", " ", text)
                # Two-word phrases first: "sleeping sickness" and "passive
                # screening" are the useful units, and single words lose them.
                words = [w for w in _re.findall(r"[a-z][a-z0-9\-]{2,}", text)
                         if w not in STOP and len(w) > 3]
                seen_here: set[str] = set()
                for i, w in enumerate(words):
                    for term in ([w] + ([f"{w} {words[i+1]}"] if i + 1 < len(words) else [])):
                        if term in seen_here:
                            continue
                        seen_here.add(term)
                        scores[term] += weight
                        origins.setdefault(term, set()).add(label)
    finally:
        conn.close()

    # A single word has to appear across at least TWO source kinds to count — one
    # project title mentioning it is a coincidence, the same word in projects and
    # the library and the sessions is a fact about them. Two-word phrases are held
    # to a lower bar because a phrase is already strong evidence of a real subject.
    ranked: list[tuple[str, int, str]] = []
    for t, s in scores.most_common(600):
        srcs = origins.get(t, set())
        is_phrase = " " in t
        if is_phrase:
            if s < 6:
                continue
        else:
            if s < 8 or len(srcs) < 2:
                continue
        ranked.append((t, s, ", ".join(sorted(srcs))))

    # Drop a phrase's component words when the phrase itself made the cut:
    # "passive screening" is the interest, "passive" on its own is not.
    phrases = {t for t, _, _ in ranked if " " in t}
    covered = {w for p in phrases for w in p.split()}
    ranked = [r for r in ranked if " " in r[0] or r[0] not in covered]

    # Phrases first, then weight.
    ranked.sort(key=lambda x: (0 if " " in x[0] else 1, -x[1], x[0]))
    return ranked[:limit]


@app.tool()
async def suggest_interests_from_work(apply: bool = False, top: int = 12) -> list[TextContent]:
    """Read the researcher's own work and propose interests they have not declared.

    Interests should not depend on someone being able to articulate them from a
    blank field. Their work already states them — project titles, captured ideas,
    what their papers are about, what their sessions keep returning to. This mines
    those sources for recurring domain terms and proposes the ones missing from
    their declared lists.

    Proposals go to the LIBRARY list by default: what recurs in someone's own
    papers and projects is what they want a background on. What they want to hear
    about in the NEWS is a different question, frequently outside their work
    entirely, and cannot be mined from it — that one has to be asked. See
    `start_interest_interview()`.

    Args:
        apply: False (default) proposes only, so the researcher decides. True adds
            the suggestions to `library_interests` directly — use when they have
            said to go ahead, or for a silent top-up during onboarding.
        top: How many suggestions to consider. Default 12.

    Returns:
        Suggested terms with what evidence supports each, and what was already
        declared so nothing is proposed twice.
    """
    lists = read_interest_lists()
    known = {t.lower() for t in lists["union"]}
    # Also treat a declared multi-word term as covering its words, so "sleeping
    # sickness" already being declared does not surface "sickness" as new.
    for t in list(known):
        for w in t.split():
            if len(w) > 3:
                known.add(w)

    mined = _mine_work_terms(limit=60)
    fresh = [(t, s, src) for t, s, src in mined
             if t.lower() not in known
             and not any(t.lower() in k or k in t.lower() for k in known if len(k) > 5)]
    fresh = fresh[:top]

    if not fresh:
        return [TextContent(type="text", text=(
            "Nothing new to suggest — everything recurring in your projects, ideas, "
            "library and sessions is already covered by your declared interests.\n\n"
            f"Declared: {len(lists['library'])} library, {len(lists['news'])} news."
        ))]

    lines = [f"**{len(fresh)} interest(s) your work suggests but you have not declared**", ""]
    for t, s, src in fresh:
        lines.append(f"  · **{t}** — appears across {src} (weight {s})")
    lines += [
        "",
        f"Already declared — library ({len(lists['library'])}): "
        + (", ".join(lists["library"][:12]) or "none"),
        f"Already declared — news ({len(lists['news'])}): "
        + (", ".join(lists["news"][:12]) or "none"),
    ]

    if apply:
        added = [t for t, _, _ in fresh]
        res = await set_research_interests(library_interests=added, mode="add")
        lines += ["", "---", "Added to your **library** interests:",
                  "  " + ", ".join(added),
                  "",
                  "News interests are deliberately untouched — what you want to hear "
                  "about is a separate question from what your work is about, and it "
                  "cannot be mined from your projects."]
    else:
        lines += [
            "",
            "These are proposals, not changes. To accept them, run this again with "
            "`apply=True`, or say which ones you want. They would go to your "
            "**library** list; news interests have to be asked about separately.",
        ]
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def start_interest_interview() -> list[TextContent]:
    """Get the script for interviewing the researcher about their interests.

    Call this when the researcher wants help defining their research interests or
    news topics — typically arriving from the "Set up my interests" button on the
    Metis Systems surface, which opens a conversation asking for exactly this.

    Returns the full interview to follow. It lives here rather than in the button's
    deep link because a `claude://` URL carrying the whole script came to 3,222
    characters, over the ~2,048-character limit Windows protocol handlers accept —
    it would have been truncated or dropped silently. Keeping the script here also
    means it is maintained in one place instead of duplicated in a template.
    """
    return [TextContent(type="text", text=INTEREST_INTERVIEW)]


def _write_prefs(prefs: dict) -> None:
    """Write user-preferences.json atomically.

    Atomic because this file is the single source of truth for identity,
    interests and news topics, and it is read by the dashboard, the briefing
    generator and the news thread vocabulary. A half-written file would degrade
    all three at once, and a crash mid-write would leave no valid copy at all.
    """
    import os as _os

    prefs_path = paths.root / "system" / "config" / "user-preferences.json"
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = prefs_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8")
    _os.replace(tmp, prefs_path)


def _clean_terms(values, limit: int = 60) -> list[str]:
    """Normalise a list of interest terms: trimmed, de-duplicated, order kept."""
    out: list[str] = []
    seen: set[str] = set()
    for v in values or []:
        term = " ".join(str(v).replace("\n", " ").split()).strip(" ,;.")
        if not term or len(term) < 2 or len(term) > 80:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(term)
        if len(out) >= limit:
            break
    return out


@app.tool()
async def set_research_interests(
    news_interests: list[str] | None = None,
    library_interests: list[str] | None = None,
    role: str = "",
    mode: str = "replace",
    interests: list[str] | None = None,
    news_topics: list[str] | None = None,
) -> list[TextContent]:
    """Save the two interest lists after interviewing the person.

    NEWS AND LIBRARY INTERESTS ARE SEPARATE THINGS, and either may sit entirely
    outside the person's work:

      - `news_interests`    → what they want to know is HAPPENING. Drives the
        story-thread vocabulary (Metis groups news into persistent running
        stories, and a declared interest becomes a subject it can recognise), the
        News surface category tabs, and what the daily and weekly briefings
        monitor. Legitimately includes pure curiosity — following AI policy or a
        conflict closely without ever publishing on it.
      - `library_interests` → what they want a real SCIENTIFIC BACKGROUND on.
        Drives literature relevance and the knowledge layer. Slower and deeper,
        and also allowed beyond current projects: a method they intend to learn
        belongs here before it appears in any of their work.

    They overlap, but the differences are the useful part. Do not collapse them.

    Neither list requires the person to have any projects or articles. Someone can
    join Metis with nothing set up and still have clear interests — ask, do not
    infer. Call `start_interest_interview()` for the full interview.

    Prefer specific, searchable terms: "sleeping sickness" and "DHIS2" work,
    "global health" is too broad to filter anything.

    Args:
        news_interests: What the News surface and briefings should track.
            Omit to leave unchanged.
        library_interests: What the literature collection and knowledge layer
            should build on. Omit to leave unchanged.
        role: Optional one-line role description.
        mode: "replace" (default) overwrites; "add" merges into what is there.
        interests: DEPRECATED alias for `library_interests` — the old combined
            field. Accepted so existing callers keep working.
        news_topics: DEPRECATED alias for `news_interests`.

    Returns:
        What was saved per list, and what each one now affects.
    """
    # Fold the deprecated aliases onto the new fields.
    if library_interests is None and interests is not None:
        library_interests = interests
    if news_interests is None and news_topics is not None:
        news_interests = news_topics

    if news_interests is None and library_interests is None and not role:
        return [TextContent(type="text", text=(
            "Nothing to save — pass `news_interests`, `library_interests`, "
            "or `role`."
        ))]
    if mode not in ("replace", "add"):
        mode = "replace"

    prefs = _read_prefs()
    current = read_interest_lists()

    if news_interests is not None:
        new_n = _clean_terms(news_interests)
        prefs["news_interests"] = (
            _clean_terms(current["news"] + new_n) if mode == "add" else new_n)
    if library_interests is not None:
        new_l = _clean_terms(library_interests)
        prefs["library_interests"] = (
            _clean_terms(current["library"] + new_l) if mode == "add" else new_l)
    if role:
        prefs["role"] = role.strip()[:120]

    # Keep the legacy fields in sync so the ~8 existing readers of `interests`
    # and `news_topics` (dashboard identity card, brief prompt builder, setup
    # completeness check, handoff brief) keep working unchanged. `interests` is
    # the UNION — callers using it want "who is this person", not one channel.
    final_news = prefs.get("news_interests", current["news"])
    final_lib = prefs.get("library_interests", current["library"])
    prefs["news_topics"] = list(final_news)
    prefs["interests"] = _clean_terms(list(final_lib) + list(final_news), limit=120)

    import datetime as _dt
    prefs["interests_updated_at"] = _dt.datetime.now().isoformat()

    try:
        _write_prefs(prefs)
    except Exception as e:
        return [TextContent(type="text", text=f"Could not save: {e}")]

    # Drop the cached thread vocabulary so the change takes effect on the next
    # scan rather than the next server restart.
    try:
        from metis_mcp.tools.news_threads import reset_subject_cache
        reset_subject_cache()
    except Exception:
        pass

    lines = ["**Saved.**", ""]
    if news_interests is not None:
        lines.append(f"**News interests** ({len(final_news)}) — what Metis watches "
                     f"for and briefs you on:")
        lines.append("  " + (", ".join(final_news) or "(none)"))
    if library_interests is not None:
        lines.append(f"**Library interests** ({len(final_lib)}) — what the "
                     f"literature and knowledge layer are built on:")
        lines.append("  " + (", ".join(final_lib) or "(none)"))
    if role:
        lines.append(f"Role: {prefs.get('role')}")
    lines += [
        "",
        "The news list shapes the News surface tabs, how stories are grouped, and "
        "what the daily and weekly briefings treat as worth reporting — from the "
        "next news scan. The library list shapes which literature is collected and "
        "what the knowledge layer is built from.",
    ]
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def get_user_profile() -> list[TextContent]:
    """Return the user's identity, interests, style, and model preference.

    Call this at the start of any personalised run to understand the user's
    topics, news signals, and communication preferences.

    Returns JSON with:
    - display_name: user's display name (set via /metis_config)
    - role: professional role (e.g. "Senior researcher")
    - news_interests: what they want to know is HAPPENING — drives the News
      surface and the briefings. May include things outside their work.
    - library_interests: what they want a scientific BACKGROUND on — drives
      literature collection and the knowledge layer. Also may sit outside their
      current projects.
    - has_declared_interests: False if neither list is set. A new user may have
      no projects, articles or interests yet; that is a normal starting point,
      and `start_interest_interview()` is how to fill it in.
    - interests: DEPRECATED — the union of both lists, kept for older callers
    - news_topics: DEPRECATED — mirrors news_interests
    - active_model: current default model slug (haiku / sonnet / opus)
    - style: dict of communication preferences:
        - response_length: "concise" | "moderate" | "detailed"
        - feedback_style: "gentle" | "direct" | "challenging"
        - challenge_level: "supportive" | "balanced" | "rigorous"
        - warmth: "warm" | "neutral" | "formal" (default: "warm")
        - detail_level: "brief" | "balanced" | "thorough" (default: "balanced")
        - routing_verbosity: "silent" | "natural" | "detailed" (default: "natural")

    Usage pattern:
      profile = json.loads((await get_user_profile())[0].text)
      interests = profile['interests']
      style = profile['style']  # → {"response_length": "concise", "warmth": "warm", ...}
    """
    prefs = _read_prefs()
    style = _read_style()
    # Apply defaults for new persona keys
    style.setdefault("warmth", "warm")
    style.setdefault("detail_level", "balanced")
    style.setdefault("routing_verbosity", "natural")
    style.setdefault("response_length", "concise")
    style.setdefault("feedback_style", "gentle")
    style.setdefault("challenge_level", "balanced")

    lists = read_interest_lists()
    profile = {
        "display_name": prefs.get("display_name") or "Researcher",
        "role": prefs.get("role") or "",
        # Two separate channels — see read_interest_lists(). `news_interests` is
        # what they want to hear is happening; `library_interests` is what they
        # want a scientific background on. Either may sit outside their work.
        "news_interests": lists["news"],
        "library_interests": lists["library"],
        # Legacy keys, kept so existing callers and prompts keep working:
        # `interests` is the union, `news_topics` mirrors news_interests.
        "interests": lists["union"],
        "news_topics": lists["news"],
        # True only when the person actually chose these, not when they were
        # inherited from the install wizard's research block.
        "has_declared_interests": lists.get("declared", False),
        "has_declared_news_interests": lists.get("declared_news", False),
        "has_declared_library_interests": lists.get("declared_library", False),
        "active_model": prefs.get("active_model") or "sonnet",
        "style": style,
    }
    return [TextContent(type="text", text=json.dumps(profile, ensure_ascii=False, indent=2))]
