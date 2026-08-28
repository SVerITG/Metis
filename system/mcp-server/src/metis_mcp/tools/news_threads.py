"""
news_threads.py — story threads, coverage state, and rotation for the briefings.

WHY THIS EXISTS
---------------
Before this module, `assemble_daily_context()` picked the ten most recent /
highest-signal items from `news_briefs` and handed them to the model with a
prompt asking for "the single most important development". It had no memory of
what yesterday's brief said. A long-running story — the 2026 Ebola epidemic —
produces several genuinely new wire items every day, so it owned those ten slots
every morning and correctly won the "most important" question every morning.
the researcher reads the daily brief daily, so by day three the lead was old news to him
even though every underlying item was new.

The missing concept was a STORY. The system saw forty unrelated Ebola items, not
one Ebola thread running six weeks. You cannot put a story on cooldown if you
have never named the story. (`news_topics` in schema.sql was built for roughly
this in an earlier pass and no code ever wrote to it; this module supersedes it.)

THE MODEL
---------
1. Every news item is assigned to a persistent THREAD, identified by
   subject + place ("ebola-drc", "sleeping-sickness-drc", "who-funding").
   Identity is deliberately explainable — the researcher can read the thread labels and
   tell whether the clustering agrees with him.

2. Each time a brief goes out we record which threads it LED with and which it
   only MENTIONED, plus the ANGLE used (epidemiological, policy, operational…).

3. Cooldown is keyed on READ, not on GENERATED. A brief that was never marked
   read delivered nothing, so its threads do not go quiet. This is what makes
   "I was away for a week" behave correctly without a special case, and it is
   why the weekly brief can still carry a thread the dailies suppressed.

4. Cooldown ESCALATES rather than being a fixed interval: lead once → 3 days
   quiet, again → 5, again → 7, thereafter 7. A six-week epidemic drifts to
   roughly weekly on its own with no number for the researcher to tune.

5. MATERIALITY overrides cooldown. A new country, a step change in the figures,
   a vaccine or policy decision, an outbreak declared over — these break the
   silence immediately. Quiet by default, loud when it matters.

6. ANGLE ROTATION keeps insights fresh, not just topics. A thread records which
   lenses it has already been given; the next appearance excludes them.

No LLM calls in this module. Pure SQL and string work, so it is cheap enough to
run inside context assembly on every brief.
"""
from __future__ import annotations

import datetime
import json
import functools
import re
import sqlite3
import unicodedata

# ---------------------------------------------------------------------------
# Schema — this module owns its tables (migrations.py is for columns only)
# ---------------------------------------------------------------------------

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS news_threads (
        thread_id   TEXT PRIMARY KEY,
        label       TEXT NOT NULL,
        subject     TEXT DEFAULT '',
        place       TEXT DEFAULT '',
        keywords    TEXT DEFAULT '',
        domain      TEXT DEFAULT '',
        first_seen  TEXT,
        last_seen   TEXT,
        item_count  INTEGER DEFAULT 0,
        peak_signal TEXT DEFAULT 'low',
        max_number  INTEGER DEFAULT 0,
        status      TEXT DEFAULT 'active'
    )
    """,
    # Keyed on news_briefs.rowid, NOT brief_id. SQLite permits NULL in a
    # TEXT PRIMARY KEY (only INTEGER PRIMARY KEY is guaranteed non-null), and
    # 1958 of the 2021 existing news_briefs rows have brief_id IS NULL. Keying
    # on brief_id made INSERT OR IGNORE silently drop 97% of the corpus.
    """
    CREATE TABLE IF NOT EXISTS news_thread_items (
        thread_id   TEXT NOT NULL,
        brief_ref   INTEGER NOT NULL,
        assigned_at TEXT,
        PRIMARY KEY (thread_id, brief_ref)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS news_thread_mentions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id   TEXT NOT NULL,
        insight_key TEXT NOT NULL,
        period      TEXT NOT NULL DEFAULT 'daily',
        role        TEXT NOT NULL DEFAULT 'mention',
        angle       TEXT DEFAULT '',
        created_at  TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_thread_items_brief ON news_thread_items(brief_ref)",
    "CREATE INDEX IF NOT EXISTS idx_thread_mentions_thread ON news_thread_mentions(thread_id)",
    "CREATE INDEX IF NOT EXISTS idx_thread_mentions_key ON news_thread_mentions(insight_key)",
)


def ensure_tables(conn: sqlite3.Connection) -> None:
    """Create the thread tables and the read_at column this module depends on."""
    for stmt in _DDL:
        try:
            conn.execute(stmt)
        except sqlite3.Error:
            pass
    # daily_insights.read_at is normally added by the dashboard's
    # _ensure_brief_read_col(). The MCP side may run first on a fresh install,
    # and every cooldown decision depends on it, so ensure it here too.
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_insights)")}
        if cols and "read_at" not in cols:
            conn.execute("ALTER TABLE daily_insights ADD COLUMN read_at TEXT")
    except sqlite3.Error:
        pass


# ---------------------------------------------------------------------------
# Vocabulary — thread identity is subject + place
# ---------------------------------------------------------------------------
# Kept explicit rather than learned. The domain vocabulary is narrow (diseases,
# countries, health organisations) and an explainable thread label beats a
# marginally better clustering that nobody can audit. Aliases map surface forms
# onto one canonical subject so "HAT", "sleeping sickness" and "human african
# trypanosomiasis" are one thread, not three.

SUBJECTS: dict[str, tuple[str, ...]] = {
    "ebola": ("ebola", "ebola virus disease", "evd", "zaire ebolavirus", "sudan virus"),
    "marburg": ("marburg", "marburg virus"),
    "mpox": ("mpox", "monkeypox", "clade ib", "clade i mpox"),
    "cholera": ("cholera", "vibrio cholerae"),
    "sleeping-sickness": (
        "sleeping sickness", "human african trypanosomiasis", "trypanosomiasis",
        "hat elimination", "gambiense", "rhodesiense", "tsetse", "trypanosoma",
    ),
    "malaria": ("malaria", "plasmodium", "falciparum", "artemisinin"),
    "measles": ("measles", "rubeola"),
    "polio": ("polio", "poliovirus", "poliomyelitis", "cvdpv"),
    "dengue": ("dengue", "aedes aegypti"),
    "yellow-fever": ("yellow fever",),
    "lassa": ("lassa", "lassa fever"),
    "diphtheria": ("diphtheria",),
    "meningitis": ("meningitis", "meningococcal"),
    "tuberculosis": ("tuberculosis", "tb ", " tb", "mdr-tb", "drug-resistant tb"),
    "hiv": ("hiv", "aids", "antiretroviral", "prep "),
    "influenza": ("influenza", "h5n1", "avian flu", "bird flu", "h5n5"),
    "covid": ("covid", "sars-cov-2", "coronavirus"),
    "ntd": (
        "neglected tropical disease", "ntds", "ntd roadmap", "schistosomiasis",
        "onchocerciasis", "lymphatic filariasis", "leishmaniasis", "trachoma",
        "soil-transmitted helminth", "buruli", "leprosy", "chagas", "rabies",
        "guinea worm", "dracunculiasis", "snakebite", "mycetoma", "yaws",
    ),
    "dhis2": ("dhis2", "district health information software"),
    "health-financing": (
        "health financing", "aid cuts", "development assistance", "usaid",
        "global fund", "replenishment", "gavi", "budget cut", "funding cut",
        "pepfar", "official development assistance",
    ),
    "health-workforce": ("health workforce", "community health worker", "chw", "brain drain"),
    "ai-in-health": (
        "artificial intelligence", " ai ", "machine learning", "large language model",
        "llm", "foundation model", "deep learning", "algorithm", "chatbot",
    ),
    "surveillance": (
        "surveillance system", "early warning", "event-based surveillance",
        "genomic surveillance", "wastewater surveillance", "integrated disease surveillance",
    ),
    "climate-health": ("climate change", "climate and health", "heatwave", "el nino", "flooding"),
    "pandemic-treaty": ("pandemic treaty", "pandemic accord", "ihr amendment", "pandemic agreement"),
    "vaccination": ("immunisation", "immunization", "vaccination campaign", "vaccine rollout", "big catch-up"),
    "antimicrobial-resistance": ("antimicrobial resistance", "amr", "antibiotic resistance"),
    "conflict-health": ("conflict", "attack on health", "war ", "displacement", "refugee"),
    "outbreak-response": ("outbreak response", "emergency committee", "grade 3 emergency"),
}

def _slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", (text or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def user_subjects() -> dict[str, tuple[str, ...]]:
    """SUBJECTS extended with whatever the user declared as interests.

    The built-in vocabulary above is a STARTER SET, not the definition. What
    counts as a story depends on whose briefing it is, so the user's own
    `interests` and `news_topics` (set in the install wizard or the Metis Systems
    surface) are merged in as first-class subjects. A declared interest that
    already matches a built-in entry is folded into it rather than duplicated, so
    declaring "sleeping sickness" does not create a second HAT thread.

    Measured 2026-08-19 before this existed: 59% of items matched no subject and
    fell through to the coarse `domain` tag. Widening the vocabulary from the
    user's own words is the main lever on that number.
    """
    import json as _json

    merged: dict[str, list[str]] = {k: list(v) for k, v in SUBJECTS.items()}
    # Reverse index of every known alias → canonical subject, so a declared
    # interest can be recognised as an existing subject.
    alias_to_key: dict[str, str] = {}
    for key, aliases in SUBJECTS.items():
        alias_to_key[key.replace("-", " ")] = key
        for a in aliases:
            alias_to_key[a.strip()] = key

    # NEWS interests lead here, because this vocabulary decides what the News
    # surface treats as a trackable story. Library interests are included too but
    # they are a different list with a different purpose (building a scientific
    # background), and a term can legitimately be in one and not the other:
    # someone may follow a conflict daily without ever collecting literature on
    # it, or want a deep library on a statistical method that never makes news.
    # Both are admitted as *recognisable subjects* — the separation that matters
    # for ranking and briefing lives in read_interest_lists() and its callers.
    declared: list[str] = []
    try:
        from metis_mcp.tools.user_profile import read_interest_lists
        lists = read_interest_lists()
        declared = list(lists["news"]) + list(lists["library"])
    except Exception:
        # Fall back to reading the files directly, so the news vocabulary never
        # depends on another tool module importing cleanly.
        try:
            from metis_mcp.config import paths as _paths
            prefs = _paths.root / "system" / "config" / "user-preferences.json"
            if prefs.exists():
                data = _json.loads(prefs.read_text(encoding="utf-8"))
                for field in ("news_interests", "library_interests",
                              "interests", "news_topics"):
                    vals = data.get(field) or []
                    if isinstance(vals, list):
                        declared += [str(v) for v in vals if str(v).strip()]
        except Exception:
            pass

    if not declared:
        return {k: tuple(v) for k, v in merged.items()}

    for raw in declared:
        term = raw.strip().lower()
        if len(term) < 3:
            continue
        existing = alias_to_key.get(term)
        if existing:
            if term not in merged[existing]:
                merged[existing].append(term)
            continue
        slug = _slugify(term)
        if not slug:
            continue
        if slug in merged:
            if term not in merged[slug]:
                merged[slug].append(term)
        else:
            merged[slug] = [term]
            alias_to_key[term] = slug

    return {k: tuple(v) for k, v in merged.items()}


PLACES: dict[str, tuple[str, ...]] = {
    "drc": ("drc", "democratic republic of the congo", "dr congo", "congo-kinshasa",
            "kinshasa", "north kivu", "south kivu", "equateur", "kasai", "ituri", "bandundu"),
    "uganda": ("uganda", "kampala"),
    "tanzania": ("tanzania",),
    "kenya": ("kenya", "nairobi"),
    "ethiopia": ("ethiopia", "addis ababa", "tigray"),
    "sudan": ("sudan", "khartoum", "darfur"),
    "south-sudan": ("south sudan", "juba"),
    "nigeria": ("nigeria", "lagos", "abuja"),
    "ghana": ("ghana", "accra"),
    "guinea": ("guinea", "conakry"),
    "cote-divoire": ("cote d'ivoire", "côte d'ivoire", "ivory coast", "abidjan"),
    "angola": ("angola", "luanda", "uige", "zaire province"),
    "chad": ("chad", "n'djamena"),
    "cameroon": ("cameroon", "yaounde", "yaoundé"),
    "car": ("central african republic", "bangui"),
    "malawi": ("malawi", "lilongwe"),
    "mozambique": ("mozambique", "maputo"),
    "zambia": ("zambia", "lusaka"),
    "zimbabwe": ("zimbabwe", "harare"),
    "rwanda": ("rwanda", "kigali"),
    "burundi": ("burundi",),
    "mali": ("mali", "bamako"),
    "burkina-faso": ("burkina faso", "ouagadougou"),
    "niger": ("niger", "niamey"),
    "senegal": ("senegal", "dakar"),
    "benin": ("benin", "cotonou"),
    "togo": ("togo", "lome", "lomé"),
    "sierra-leone": ("sierra leone", "freetown"),
    "liberia": ("liberia", "monrovia"),
    "gabon": ("gabon", "libreville"),
    "congo": ("republic of congo", "brazzaville"),
    "west-africa": ("west africa", "sahel", "ecowas"),
    "east-africa": ("east africa", "horn of africa"),
    "central-africa": ("central africa",),
    "southern-africa": ("southern africa", "sadc"),
    "africa": ("africa", "african union", "africa cdc", "continental"),
    "europe": ("europe", "european union", "eu ", "ecdc", "belgium", "brussels"),
    "global": ("global", "worldwide", "world health assembly", "united nations"),
    "americas": ("latin america", "brazil", "paho", "united states", "washington"),
    "asia": ("asia", "india", "indonesia", "philippines", "china", "vietnam", "bangladesh"),
}

# Organisation mentions do not define a thread on their own (almost every item
# says "WHO"), but they sharpen the label when no place is found.
ORGS: dict[str, tuple[str, ...]] = {
    "who": ("world health organization", "world health organisation", "who "),
    "msf": ("msf", "medecins sans frontieres", "médecins sans frontières", "doctors without borders"),
    "africa-cdc": ("africa cdc",),
    "unicef": ("unicef",),
    "gavi": ("gavi",),
    "global-fund": ("global fund",),
    "itm": ("institute of tropical medicine", "itg antwerp", "itm antwerp"),
}

_PLACE_LABELS = {
    "drc": "DR Congo", "car": "Central African Republic", "cote-divoire": "Côte d'Ivoire",
    "south-sudan": "South Sudan", "burkina-faso": "Burkina Faso", "sierra-leone": "Sierra Leone",
    "west-africa": "West Africa", "east-africa": "East Africa", "central-africa": "Central Africa",
    "southern-africa": "Southern Africa", "africa": "Africa", "europe": "Europe",
    "global": "Global", "americas": "Americas", "asia": "Asia", "congo": "Rep. of Congo",
}

_ORG_LABELS = {
    "who": "WHO", "msf": "MSF", "africa-cdc": "Africa CDC", "unicef": "UNICEF",
    "gavi": "Gavi", "global-fund": "Global Fund", "itm": "ITM Antwerp",
}

_SUBJECT_LABELS = {
    "sleeping-sickness": "Sleeping sickness", "ntd": "Neglected tropical diseases",
    "ai-in-health": "AI in health", "health-financing": "Health financing",
    "health-workforce": "Health workforce", "climate-health": "Climate & health",
    "pandemic-treaty": "Pandemic treaty", "antimicrobial-resistance": "Antimicrobial resistance",
    "conflict-health": "Conflict & health", "outbreak-response": "Outbreak response",
    "dhis2": "DHIS2", "hiv": "HIV/AIDS", "covid": "COVID-19", "mpox": "Mpox",
    "yellow-fever": "Yellow fever", "tuberculosis": "Tuberculosis",
}

_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "have", "has", "will",
    "was", "were", "been", "are", "its", "into", "over", "after", "before",
    "more", "most", "than", "then", "they", "their", "there", "what", "when",
    "where", "which", "while", "would", "could", "should", "about", "amid",
    "says", "said", "new", "news", "report", "reports", "study", "studies",
    "first", "last", "year", "years", "week", "weeks", "day", "days", "month",
    "cases", "case", "people", "health", "public", "global", "world", "who",
    "may", "can", "one", "two", "three", "how", "why", "not", "but", "all",
    "amid", "against", "among", "under", "between", "during", "toward",
    # Ordinals and vague quantifiers leaked into fallback thread ids
    # ('second-malawi', 'second-sierra-leone').
    "second", "third", "fourth", "fifth", "another", "several", "many", "some",
    "thousands", "hundreds", "millions", "dozens", "number", "total", "around",
    # Report-boilerplate words that named threads after their document type
    # ('quarter-malawi' from "WHO Malawi Second Quarter 2026 Report").
    "quarter", "quarterly", "annual", "bulletin", "situation", "update",
    "summary", "review", "briefing", "release", "statement", "highlights",
    # Francophone feeds (WHO AFRO, RFI) put these in every headline. Listed
    # unaccented because _norm folds accents before matching.
    "sante", "publique", "ministere", "pays", "selon", "cette", "dans",
    "pour", "avec", "plus", "leur", "aux", "des", "les", "une", "sur",
    "par", "est", "ont", "nouveau", "nouvelle", "republique", "democratique",
    "mocratique", "congolaise", "provinces", "province", "region",
}


def _norm(text: str) -> str:
    """Lowercase, fold accents, collapse punctuation, pad so ' ai ' probes work.

    Accents must be FOLDED, not stripped. Stripping split "démocratique" into
    "d" + "mocratique" and produced the thread id 'mocratique-drc' — a French
    fragment as a story name. WHO AFRO and RFI feeds are francophone, so this
    affects a real slice of the corpus.
    """
    t = unicodedata.normalize("NFKD", text or "").lower()
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"[^a-z0-9'\-\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return f" {t} "


@functools.lru_cache(maxsize=4096)
def _alias_re(alias: str) -> "re.Pattern":
    """An alias must be a WHOLE WORD, bounded on both sides.

    THE BUG THIS FIXES, because it is not obvious from the code that was here:
    the old probe was `" " + alias` — a boundary on the LEFT only, with
    `f" {alias} "` as an alternative. A left-only boundary means the alias
    `mali` matches "MALIgnant", so a STAT article headlined "FDA approves new
    pancreatic cancer drug" was filed as a story about Mali. It also means
    `chad` matches "chadian" (fine) but equally "chadwick" (not fine), and
    `guinea` matches "guinea-pig".

    A trailing letter or digit now disqualifies a match; anything else —
    a space, an apostrophe in "congo's", a hyphen in "guinea-bissau" — still
    counts as a boundary, so the plural and possessive forms the loose probe
    was there to catch keep working.
    """
    return re.compile(r"(?<![a-z0-9])" + re.escape(alias.strip()) + r"(?![a-z0-9])")


def _match_vocab(haystack: str, vocab: dict[str, tuple[str, ...]]) -> list[str]:
    """Canonical keys whose aliases appear in `haystack`, longest alias first.

    Longest-first matters: "south sudan" must win over "sudan", and
    "west africa" over "africa".
    """
    hits: list[tuple[int, str]] = []
    for key, aliases in vocab.items():
        best = 0
        for alias in aliases:
            if _alias_re(alias).search(haystack):
                best = max(best, len(alias))
        if best:
            hits.append((best, key))
    hits.sort(reverse=True)
    return [k for _, k in hits]


#: Words that are grammatically available to name a thread and semantically
#: useless for it. A thread name answers "what is this story ABOUT", and a verb
#: answers "what happened" — which is the headline's job, not the thread's.
#:
#: This is why one FDA drug approval appeared on the News overview as THREE
#: separate running stories: the three headlines covering it shared no noun the
#: vocabulary knew, so each was named from its own leftover verbs — "Approves
#: treatment", "Agency approves", "Approves · Mali". Different names, so
#: different thread ids, so no grouping. Removing the verbs does not merge them
#: by itself, but it stops the fallback from manufacturing a name that LOOKS
#: like a subject and is not.
_NON_SUBJECT = {
    "approves", "approved", "approval", "announces", "announced", "launches",
    "launched", "declares", "declared", "confirms", "confirmed", "warns",
    "warned", "urges", "urged", "calls", "called", "backs", "backed",
    "expands", "expanded", "extends", "extended", "begins", "began",
    "unveils", "unveiled", "issues", "issued", "grants", "granted",
    "rejects", "rejected", "halts", "halted", "resumes", "resumed",
    "agency", "authority", "committee", "commission", "regulator",
    "treatment", "treatments", "breakthrough", "expected", "according",
    "researchers", "scientists", "officials", "experts", "leaders",
    "million", "billion", "percent", "despite", "following", "including",
}


def _distinctive_tokens(haystack: str, limit: int = 3) -> list[str]:
    """Fallback identity for items no vocabulary entry matches.

    Candidates are ranked by LENGTH, not by where they appear. Taking them in
    headline order sounds right — headlines front-load their subject — but the
    filler comes first just as often, and the loop stopped at `limit` before
    ever reaching the noun. "FDA approves new treatment for hard-to-treat
    pancreatic cancer" yielded "treat pancreatic", because `treat` appears
    first and `treat` is exactly five characters.

    Length is a crude specificity proxy and a good one here: `pancreatic` beats
    `treat`, `fungicide` beats `based`, `surveillance` beats `report`. Ties keep
    headline order, and the tokens finally chosen are returned in the order they
    appeared so the name still reads as English.
    """
    cands: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    pos = 0
    # Hyphenated compounds are SPLIT, not taken whole. "hard-to-treat" is one
    # whitespace token and eleven characters long, so it sailed past the length
    # floor as a single candidate — a modifier outranking the noun it modifies.
    for raw in haystack.split():
        for tok in raw.split("-"):
            tok = tok.strip("-'")
            if len(tok) < 5 or tok in _STOPWORDS or tok in _NON_SUBJECT or tok.isdigit():
                continue
            if tok in seen:
                continue
            seen.add(tok)
            cands.append((-len(tok), pos, tok))
            pos += 1
    cands.sort()
    chosen = sorted(cands[:limit], key=lambda c: c[1])
    return [t for _, _, t in chosen]


def _largest_number(text: str) -> int:
    """Largest plain integer in the text — a crude death-toll / case-count proxy."""
    best = 0
    for m in re.finditer(r"\b(\d[\d,\.]{0,12})\b", text or ""):
        raw = m.group(1).replace(",", "").replace(".", "")
        if raw.isdigit() and len(raw) <= 9:
            best = max(best, int(raw))
    return best


# Continental / global tags are too coarse to split a story on. Treating them
# as real places produced 'sleeping-sickness', 'sleeping-sickness-africa' and
# 'sleeping-sickness-drc' as three separate threads for one story, which
# defeats cooldown — each variant kept its own turn to lead. Only a country
# distinguishes a thread; a continent collapses into the subject alone.
_WEAK_PLACES = frozenset({
    "africa", "global", "europe", "americas", "asia",
    "west-africa", "east-africa", "central-africa", "southern-africa",
})


# Cached because classify() runs once per unassigned item — up to 2,000 in a
# backfill — and re-reading user-preferences.json each time would be 2,000 file
# reads for a value that cannot change mid-run. `reset_subject_cache()` is called
# by assign_threads() so an interests edit takes effect on the next scan.
_SUBJECT_CACHE: dict[str, tuple[str, ...]] | None = None


def _subject_vocab() -> dict[str, tuple[str, ...]]:
    global _SUBJECT_CACHE
    if _SUBJECT_CACHE is None:
        _SUBJECT_CACHE = user_subjects()
    return _SUBJECT_CACHE


def reset_subject_cache() -> None:
    """Drop the cached vocabulary so edited interests are picked up."""
    global _SUBJECT_CACHE
    _SUBJECT_CACHE = None


def classify(title: str, summary: str = "", domain: str = "") -> dict:
    """Derive a thread identity for one news item.

    Returns {thread_id, label, subject, place, keywords, max_number}.

    Identity rule, in order:
      subject + country  → 'ebola-drc'        (a specific story in a place)
      subject only       → 'sleeping-sickness' (continental/global coverage)
      country + token    → 'floods-mozambique' (event with no known subject)
      organisation       → 'who'               (announcement-type items)
      distinctive tokens → 'venezuela-earthquakes' (last resort)
    """
    hay = _norm(f"{title} {summary}")
    subjects = _match_vocab(hay, _subject_vocab())
    orgs = _match_vocab(hay, ORGS)

    # Place comes from the TITLE first. WHO summaries open with a "Countries:"
    # list, so matching places across the whole text filed a Central African
    # Republic story under DR Congo — 'democratic republic of the congo' is a
    # longer alias than 'central african republic' and won the longest-match
    # tie-break. The headline names the country the story is actually about.
    title_hay = _norm(title)
    places = _match_vocab(title_hay, PLACES)
    if not places and _match_vocab(hay, _subject_vocab()):
        # A place found only in the SUMMARY may REFINE a story the vocabulary
        # already recognises ("cholera" + a country named in the body). It may
        # not DEFINE one: a summary mentions countries in passing constantly —
        # datelines, author affiliations, "unlike in Mali" — and a story whose
        # only claim to a country is one passing mention is not about it.
        places = _match_vocab(hay, PLACES)

    subject = subjects[0] if subjects else ""
    # Prefer a country. A continental tag is recorded but never splits a thread.
    place = ""
    for p in places:
        if p not in _WEAK_PLACES:
            place = p
            break
    weak_place = places[0] if (not place and places) else ""

    if subject and place:
        thread_id = f"{subject}-{place}"
    elif subject:
        thread_id = subject
    elif place:
        # Exclude tokens that are just the place said again, or 'nigeria' →
        # 'nigeria-nigeria' and 'congo' → 'congo-drc'.
        place_words = {place, *place.split("-")}
        for alias in PLACES.get(place, ()):
            place_words.update(alias.split())
        toks = [t for t in _distinctive_tokens(hay, 4) if t not in place_words]
        thread_id = f"{toks[0]}-{place}" if toks else place
    elif orgs:
        # Org alone, never org+place: combining them produced who-zambia,
        # who-malawi, who-ethiopia … a thread per country office, all
        # single-item. One coarse 'who' thread is the useful unit here.
        thread_id = orgs[0]
    else:
        toks = _distinctive_tokens(hay, 2)
        thread_id = "-".join(toks) if toks else "unsorted"
    if not place:
        place = weak_place

    # Label is derived from what actually went into thread_id, so the label can
    # never disagree with the identity. ('congo-publique' previously displayed
    # as "DR Congo" because the label used a place the thread_id had ignored.)
    id_place = place if (place and place in thread_id and place not in _WEAK_PLACES) else ""
    subj_label = _SUBJECT_LABELS.get(subject) or (subject.replace("-", " ").capitalize() if subject else "")
    place_label = _PLACE_LABELS.get(id_place) or (id_place.replace("-", " ").title() if id_place else "")
    if subj_label and place_label:
        label = f"{subj_label} · {place_label}"
    elif subj_label:
        label = subj_label
    elif place_label:
        rest = thread_id.replace(f"-{id_place}", "").replace("-", " ").strip()
        label = f"{rest.capitalize()} · {place_label}" if rest and rest != id_place else place_label
    elif thread_id in _ORG_LABELS:
        label = _ORG_LABELS[thread_id]
    else:
        label = thread_id.replace("-", " ").capitalize()

    keywords = sorted(set(subjects[:3] + places[:2] + orgs[:2]))
    return {
        "thread_id": thread_id,
        "label": label,
        "subject": subject,
        "place": place,
        "keywords": keywords,
        "max_number": _largest_number(title),
        "domain": domain or "",
    }


# ---------------------------------------------------------------------------
# Assignment — cluster unassigned news_briefs rows into threads
# ---------------------------------------------------------------------------

def assign_threads(conn: sqlite3.Connection, limit: int = 2000) -> dict:
    """Assign every not-yet-threaded news item to a thread. Idempotent.

    Cheap enough (pure string work) to call at the top of context assembly, so
    threads are always current without a separate scheduled job.
    """
    ensure_tables(conn)
    reset_subject_cache()   # pick up any interests edited since the last scan
    try:
        rows = conn.execute(
            "SELECT b.rowid AS ref, b.title, b.summary, b.domain, b.created_at, "
            "       COALESCE(b.signal_strength,'low') AS signal_strength "
            "FROM news_briefs b "
            "LEFT JOIN news_thread_items i ON i.brief_ref = b.rowid "
            "WHERE i.brief_ref IS NULL "
            "ORDER BY b.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        return {"assigned": 0, "threads_touched": 0}

    _rank = {"high": 3, "medium": 2, "low": 1, "": 1}
    touched: set[str] = set()
    assigned = 0
    now = datetime.datetime.now().isoformat()

    for r in rows:
        info = classify(r["title"] or "", r["summary"] or "", r["domain"] or "")
        tid = info["thread_id"]
        created = r["created_at"] or now
        sig = (r["signal_strength"] or "low").lower()

        existing = conn.execute(
            "SELECT keywords, first_seen, last_seen, item_count, peak_signal, max_number "
            "FROM news_threads WHERE thread_id = ?", (tid,),
        ).fetchone()

        if existing is None:
            conn.execute(
                "INSERT INTO news_threads (thread_id, label, subject, place, keywords, "
                "domain, first_seen, last_seen, item_count, peak_signal, max_number, status) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,'active')",
                (tid, info["label"], info["subject"], info["place"],
                 json.dumps(info["keywords"]), info["domain"], created, created,
                 0, sig, info["max_number"]),
            )
        else:
            try:
                kw = set(json.loads(existing["keywords"] or "[]"))
            except (ValueError, TypeError):
                kw = set()
            kw.update(info["keywords"])
            old_sig = (existing["peak_signal"] or "low").lower()
            peak = sig if _rank.get(sig, 1) > _rank.get(old_sig, 1) else old_sig
            conn.execute(
                "UPDATE news_threads SET keywords=?, last_seen=MAX(COALESCE(last_seen,''),?), "
                "first_seen=MIN(COALESCE(NULLIF(first_seen,''),?),?), "
                "peak_signal=?, max_number=MAX(COALESCE(max_number,0),?) "
                "WHERE thread_id=?",
                (json.dumps(sorted(kw)), created, created, created, peak,
                 info["max_number"], tid),
            )

        conn.execute(
            "INSERT OR IGNORE INTO news_thread_items (thread_id, brief_ref, assigned_at) "
            "VALUES (?,?,?)", (tid, r["ref"], now),
        )
        touched.add(tid)
        assigned += 1

    # item_count is DERIVED, never incremented. An incrementing counter drifted
    # out of step with the link table the moment an insert was skipped, and a
    # counter that can lie about how big a story is corrupts every ranking
    # decision downstream. Recomputing is one cheap UPDATE.
    conn.execute(
        "UPDATE news_threads SET item_count = ("
        "  SELECT COUNT(*) FROM news_thread_items i WHERE i.thread_id = news_threads.thread_id)"
    )
    conn.commit()
    return {"assigned": assigned, "threads_touched": len(touched)}


# ---------------------------------------------------------------------------
# Cooldown ladder and materiality
# ---------------------------------------------------------------------------

# Quiet days after N *read* leads. Index = number of read leads so far.
COOLDOWN_LADDER = (0, 3, 5, 7)

ANGLES = (
    "epidemiological",   # transmission, incidence, geography, case data
    "operational",       # response capacity, logistics, workforce, supply
    "policy",            # decisions, guidance, governance, declarations
    "methodological",    # how it is measured, modelled, surveilled, evaluated
    "funding",           # money, donors, budgets, cost
    "regional-comparison",  # how this compares with neighbours or past outbreaks
)

# Phrases that mean something genuinely changed. These break cooldown.
MATERIAL_PHRASES = (
    "declares", "declared", "declares end", "declared over", "outbreak over",
    "public health emergency", "pheic", "emergency committee", "grade 3",
    "first case", "first death", "new country", "spreads to", "spread to",
    "crosses border", "cross-border", "imported case", "exported case",
    "vaccine approved", "approves", "authorised", "authorized", "emergency use",
    "trial results", "phase 3", "efficacy", "rollout begins", "campaign launched",
    "resurgence", "surge", "doubling", "record high", "sharp rise", "spike",
    "lockdown", "quarantine", "travel restriction", "border closure",
    "suspends", "withdraws", "resigns", "cuts funding", "funding cut",
    "eliminated", "elimination validated", "certified", "roadmap target",
    "contained", "under control", "response scaled",
)

# A figure jumping by this fraction counts as a step change.
_NUMBER_JUMP = 0.25

# Routine periodic publications. These are the feed's steady-state background:
# a quarterly country report or a monthly newsletter is published on a calendar,
# not because anything happened, yet the feed scorer often tags them 'high'.
#
# This matters more than it looks. Once cooldown correctly demoted the Ebola
# thread, the next-ranked thread became "WHO Sierra Leone Second Quarter 2026
# Report" — so the first live test would have replaced a repetitive real story
# with a repetitive non-story. Suppressing repetition is only a win if what
# replaces it is worth reading.
# NOTE what is deliberately ABSENT: "situation report" / "sitrep".
# The first version listed them and demoted the live Ebola thread from rank 1 to
# rank 39, because WHO reports an active outbreak *through* weekly sitreps. An
# outbreak sitrep carries this week's case counts — that is the news. A quarterly
# country newsletter carries the fact that a quarter ended. Only the second is
# calendar-driven paperwork, and only the second should be demoted.
_ROUTINE_PATTERNS = (
    r"\b(?:first|second|third|fourth|1st|2nd|3rd|4th|q[1-4])\s+quarter\b",
    r"\bquarterly\b",
    r"\bnewsletter\b",
    r"\bannual\s+report\b",
    r"\bmonthly\s+(?:report|bulletin|update|digest)\b",
    r"\bvacanc(?:y|ies)\b",
    r"\bcall\s+for\s+(?:applications|proposals|abstracts|papers)\b",
    r"\btenders?\b",
    r"\b(?:meeting\s+)?minutes\b",
    r"\bmedia\s+advisory\b",
    r"\bweek\s+in\s+review\b",
    r"\bcalendar\s+of\s+events\b",
)
_ROUTINE_RE = re.compile("|".join(_ROUTINE_PATTERNS), re.IGNORECASE)


def _is_routine(titles: list[str]) -> bool:
    """True when EVERY item in the window is a routine periodic publication.

    Requires all, not any: a thread holding one newsletter plus one real
    development still has something to say. Only a thread that is nothing but
    calendar-driven paperwork is demoted.
    """
    if not titles:
        return False
    return all(_ROUTINE_RE.search(_norm(t)) for t in titles)


def _is_material(titles: list[str], known_max: int) -> tuple[bool, str]:
    """Did something genuinely change? Returns (material, reason).

    TITLES ONLY, deliberately. Scanning summaries too made materiality fire on
    almost everything: phrases like "cross-border" and "record high" occur in
    ordinary background prose, so a routine single low-signal item read as an
    escalation. A real event announces itself in the headline.
    """
    blob = _norm(" ".join(titles))
    for phrase in MATERIAL_PHRASES:
        if f" {phrase} " in blob:
            return True, f"'{phrase}'"
    new_max = max((_largest_number(t) for t in titles), default=0)
    if known_max and new_max > known_max * (1 + _NUMBER_JUMP):
        return True, f"figure moved {known_max:,}→{new_max:,}"
    return False, ""


# ---------------------------------------------------------------------------
# Coverage state — the read-aware part
# ---------------------------------------------------------------------------

def _read_lead_state(conn: sqlite3.Connection) -> dict[str, dict]:
    """Per thread: how many times it has LED a brief the researcher actually marked read.

    Cooldown deliberately counts *read* leads only. A generated brief that was
    never marked read delivered nothing, so it must not silence a thread — this
    single choice is what makes the away-for-a-week case work without a special
    branch, and what lets the weekly brief still carry a suppressed thread.
    """
    out: dict[str, dict] = {}
    try:
        rows = conn.execute(
            "SELECT m.thread_id, COUNT(*) AS read_leads, MAX(m.created_at) AS last_read_lead "
            "FROM news_thread_mentions m "
            "JOIN daily_insights d ON d.insight_date = m.insight_key "
            "WHERE m.role = 'lead' AND m.period = 'daily' "
            "  AND d.read_at IS NOT NULL AND d.read_at != '' "
            "GROUP BY m.thread_id"
        ).fetchall()
    except sqlite3.Error:
        return out
    for r in rows:
        out[r["thread_id"]] = {
            "read_leads": r["read_leads"] or 0,
            "last_read_lead": r["last_read_lead"] or "",
        }
    return out


def _read_mention_state(conn: sqlite3.Connection) -> dict[str, str]:
    """Per thread: when it was last mentioned (any role) in a READ brief."""
    out: dict[str, str] = {}
    try:
        rows = conn.execute(
            "SELECT m.thread_id, MAX(m.created_at) AS last_read_mention "
            "FROM news_thread_mentions m "
            "JOIN daily_insights d ON d.insight_date = m.insight_key "
            "WHERE d.read_at IS NOT NULL AND d.read_at != '' "
            "GROUP BY m.thread_id"
        ).fetchall()
    except sqlite3.Error:
        return out
    for r in rows:
        out[r["thread_id"]] = r["last_read_mention"] or ""
    return out


def _angles_used(conn: sqlite3.Connection, lookback_days: int = 21) -> dict[str, list[str]]:
    """Per thread: angles already used in READ briefs recently.

    Bounded by a lookback so a long-running thread eventually recycles its
    lenses instead of running out of them and going permanently silent.
    """
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=lookback_days)).isoformat()
    out: dict[str, list[str]] = {}
    try:
        rows = conn.execute(
            "SELECT m.thread_id, m.angle FROM news_thread_mentions m "
            "JOIN daily_insights d ON d.insight_date = m.insight_key "
            "WHERE d.read_at IS NOT NULL AND d.read_at != '' "
            "  AND m.angle != '' AND m.created_at >= ? ",
            (cutoff,),
        ).fetchall()
    except sqlite3.Error:
        return out
    for r in rows:
        out.setdefault(r["thread_id"], [])
        if r["angle"] not in out[r["thread_id"]]:
            out[r["thread_id"]].append(r["angle"])
    return out


def _days_since(iso: str) -> float:
    if not iso:
        return 9999.0
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(iso[:26] if "." in iso else iso[:19], fmt)
            return (datetime.datetime.now() - dt).total_seconds() / 86400.0
        except ValueError:
            continue
    try:
        return (datetime.datetime.now() - datetime.datetime.fromisoformat(iso[:19])).total_seconds() / 86400.0
    except ValueError:
        return 9999.0


def thread_window(conn: sqlite3.Connection, since_iso: str,
                  source_type: str = "news") -> list[dict]:
    """Threads with items in the window, each carrying its items and coverage state.

    This is the single function context assembly needs. Every field the prompt
    builder uses is computed here so the assembly code stays declarative.
    """
    ensure_tables(conn)
    assign_threads(conn)

    lead_state = _read_lead_state(conn)
    mention_state = _read_mention_state(conn)
    angles = _angles_used(conn)

    try:
        rows = conn.execute(
            # `brief_id` is carried so the overview can offer triage on a
            # thread's items. rowid is the JOIN key here and stays that way, but
            # a verdict OUTLIVES the request and rowid is reassigned by VACUUM.
            "SELECT i.thread_id, b.brief_id, b.title, b.summary, b.domain, "
            "       COALESCE(b.signal_strength,'low') AS signal_strength, b.created_at, "
            "       b.source_url, t.label, t.first_seen, t.item_count, t.max_number "
            "FROM news_thread_items i "
            "JOIN news_briefs b ON b.rowid = i.brief_ref "
            "JOIN news_threads t ON t.thread_id = i.thread_id "
            "WHERE b.created_at >= ? AND COALESCE(b.source_type,'news') = ? "
            "ORDER BY b.created_at DESC",
            (since_iso, source_type),
        ).fetchall()
    except sqlite3.Error:
        return []

    grouped: dict[str, dict] = {}
    _rank = {"high": 3, "medium": 2, "low": 1}
    for r in rows:
        tid = r["thread_id"]
        g = grouped.setdefault(tid, {
            "thread_id": tid,
            "label": r["label"] or tid,
            "items": [],
            "first_seen": r["first_seen"] or "",
            "total_items": r["item_count"] or 0,
            "known_max": r["max_number"] or 0,
            "top_signal": "low",
            "newest": "",
        })
        g["items"].append({
            "id": r["brief_id"] or "",
            "title": r["title"] or "",
            "summary": (r["summary"] or "")[:220],
            "domain": r["domain"] or "",
            "signal": (r["signal_strength"] or "low").lower(),
            "created_at": r["created_at"] or "",
            "url": r["source_url"] or "",
        })
        if _rank.get((r["signal_strength"] or "low").lower(), 1) > _rank.get(g["top_signal"], 1):
            g["top_signal"] = (r["signal_strength"] or "low").lower()
        if (r["created_at"] or "") > g["newest"]:
            g["newest"] = r["created_at"] or ""

    threads: list[dict] = []
    for tid, g in grouped.items():
        ls = lead_state.get(tid, {})
        read_leads = ls.get("read_leads", 0)
        last_read_lead = ls.get("last_read_lead", "")
        days_since_lead = _days_since(last_read_lead)
        cooldown = COOLDOWN_LADDER[min(read_leads, len(COOLDOWN_LADDER) - 1)]

        material, reason = _is_material(
            [it["title"] for it in g["items"]], g["known_max"],
        )

        on_cooldown = bool(read_leads) and days_since_lead < cooldown and not material

        # Softer rule for a thread that only got a passing mention: repeating a
        # clause is fine, but it should not be promoted to today's lead the day
        # after the researcher already saw it. Without this, a thread cycles
        # mention→lead→mention→lead and reads as repetition even though the
        # lead cooldown was technically respected.
        days_since_mention = _days_since(mention_state.get(tid, ""))
        blocked_from_lead = on_cooldown or (days_since_mention < 1.0 and not material)

        routine = _is_routine([it["title"] for it in g["items"]])

        # Org-only threads ('who', 'msf') are BUCKETS, not stories: they collect
        # every item that matched an organisation and nothing more specific, so
        # they are internally incoherent by construction. The first live brief
        # said so unprompted — "the WHO thread also picked up non-health noise
        # (crime, celebrity) that has no bearing on your domain" — while sitting
        # at rank 1 once Ebola was correctly demoted. A bucket may be mentioned;
        # it must never be the lead, because there is no single story to lead on.
        is_bucket = tid in _ORG_LABELS or tid == "unsorted"

        used = angles.get(tid, [])
        fresh_angles = [a for a in ANGLES if a not in used] or list(ANGLES)

        # Thread age in days — a six-week-old story is described as such so the
        # model can write "still running" rather than "breaking".
        age_days = _days_since(g["first_seen"])

        threads.append({
            **g,
            "read_leads": read_leads,
            "days_since_read_lead": None if days_since_lead > 9000 else round(days_since_lead, 1),
            "days_since_read_mention": (
                None if _days_since(mention_state.get(tid, "")) > 9000
                else round(_days_since(mention_state.get(tid, "")), 1)
            ),
            "cooldown_days": cooldown,
            "on_cooldown": on_cooldown,
            "blocked_from_lead": blocked_from_lead,
            "material": material,
            "material_reason": reason,
            "routine": routine,
            "is_bucket": is_bucket,
            "angles_used": used,
            "fresh_angles": fresh_angles,
            "age_days": None if age_days > 9000 else round(age_days, 1),
            "never_delivered": read_leads == 0 and tid not in mention_state,
        })

    # Rank: lead-eligible first, then signal, then materiality as a tie-break
    # WITHIN a signal band, then volume.
    #
    # Materiality is deliberately NOT a global ranking boost. Ranking on it first
    # floated a single low-signal item whose headline happened to say "record
    # high" above a three-item high-signal Ebola thread. Materiality exists to
    # break a cooldown — to let a story speak again when it has genuinely moved —
    # not to make any escalation-flavoured wording outrank real signal.
    # Buckets and routine paperwork sort before signal: neither should outrank a
    # genuine development just because the feed scorer tagged it 'high'.
    _sig = {"high": 0, "medium": 1, "low": 2}
    threads.sort(key=lambda t: (
        t["blocked_from_lead"],
        t["is_bucket"],
        t["routine"],
        _sig.get(t["top_signal"], 2),
        not t["material"],
        -len(t["items"]),
    ))
    return threads


# ---------------------------------------------------------------------------
# Rendering the thread window into briefing context
# ---------------------------------------------------------------------------
# The context the model receives is where suppression actually happens. Rather
# than filter cooled-down threads OUT (which would hide a genuine escalation and
# make the brief unable to say "still no change in X"), they are included and
# explicitly labelled. The model gets the coverage history and the rules, and
# writes accordingly. This keeps one source of truth: the thread state.


def _fmt_age(days: float | None) -> str:
    if days is None:
        return "new"
    if days < 1:
        return "today"
    if days < 14:
        return f"{int(days)}d old"
    if days < 60:
        return f"{int(days / 7)}w old"
    return f"{int(days / 30)}mo old"


def render_daily_section(threads: list[dict], max_threads: int = 12,
                         max_items: int = 3) -> tuple[str, list[str]]:
    """Render the daily brief's news context. Returns (section_text, eligible_ids)."""
    fresh = [t for t in threads if not t["blocked_from_lead"]][:max_threads]
    cooled = [t for t in threads if t["blocked_from_lead"]][:max_threads]

    lines = ["## Field News — story threads (last 3 days)", ""]
    lines.append(
        "Every item belongs to a STORY THREAD with a coverage history. Threads are "
        "split by whether they may lead today. Use the thread ids in square brackets "
        "in your coverage footer. A thread flagged ROUTINE PERIODIC PUBLICATION is "
        "calendar-driven paperwork (a quarterly report, a newsletter, a sitrep) — do "
        "not build a lead on one unless there is genuinely nothing else, and say so "
        "plainly if the day is quiet. A thread flagged MIXED BUCKET holds unrelated "
        "items that merely mentioned the same organisation — pick a single item out "
        "of it if one is worth reporting, but never treat the bucket as one story. "
        "A quiet day honestly reported is better than a manufactured headline."
    )
    lines.append("")

    if fresh:
        lines.append("### ELIGIBLE TO LEAD — not yet covered, or genuinely changed")
        for t in fresh:
            bits = [f"{len(t['items'])} new item(s)", _fmt_age(t["age_days"]),
                    f"signal {t['top_signal']}"]
            if t["is_bucket"]:
                bits.append("MIXED BUCKET — unrelated items, never lead with this")
            if t["routine"]:
                bits.append("ROUTINE PERIODIC PUBLICATION — weak lead material")
            if t["material"]:
                bits.append(f"ESCALATION: {t['material_reason']}")
            if t["read_leads"]:
                bits.append(f"led {t['read_leads']}× before, last {t['days_since_read_lead']}d ago")
            lines.append(f"[{t['thread_id']}] {t['label']} — " + " · ".join(bits))
            angles = ", ".join(t["fresh_angles"][:3])
            used = ", ".join(t["angles_used"]) or "none"
            lines.append(f"    ANGLE: use one of {angles} (already used recently: {used})")
            for it in t["items"][:max_items]:
                lines.append(f"    - {it['title']}: {it['summary'][:180]}")
        lines.append("")

    if cooled:
        lines.append(
            "### ALREADY DELIVERED — do NOT lead with these and do NOT restate them. "
            "Mention one only if its new items tell the researcher something he has not been "
            "told. Silence about a thread is the correct output when nothing changed."
        )
        for t in cooled:
            why = (f"led {t['days_since_read_lead']}d ago, quiet for {t['cooldown_days']}d"
                   if t["read_leads"] else
                   f"mentioned {t['days_since_read_mention']}d ago")
            lines.append(f"[{t['thread_id']}] {t['label']} — {why} · {len(t['items'])} new item(s)")
            for it in t["items"][:2]:
                lines.append(f"    - {it['title']}")
        lines.append("")

    return "\n".join(lines), [t["thread_id"] for t in fresh]


def render_weekly_section(threads: list[dict], max_threads: int = 18,
                          max_items: int = 4) -> str:
    """Render the weekly brief's news context.

    The weekly is deliberately COMPLETE — it carries threads the dailies
    suppressed, because the researcher reads it as an overview rather than a diff. What
    changes is the treatment: a thread he already read daily gets its
    trajectory across the week, not the same paragraph again, and every thread
    is labelled with whether he has already seen it.
    """
    lines = ["## Field News — story threads (last 7 days)", ""]
    lines.append(
        "This is the WEEKLY overview: it is complete on purpose and includes threads "
        "the daily briefs held back. Each thread is labelled with what the researcher has "
        "already seen. For a thread marked ALREADY SEEN, write the week's TRAJECTORY "
        "— what changed across the seven days, where it stands now — not a repeat of "
        "the daily item. For a thread marked NOT YET SEEN, report it properly: he "
        "has never been told."
    )
    lines.append("")
    for t in threads[:max_threads]:
        if t["read_leads"]:
            seen = f"ALREADY SEEN (led a daily {t['days_since_read_lead']}d ago, {t['read_leads']}× total)"
        elif t["days_since_read_mention"] is not None:
            seen = f"ALREADY SEEN (mentioned in a daily {t['days_since_read_mention']}d ago)"
        else:
            seen = "NOT YET SEEN — never in a brief you read"
        bits = [f"{len(t['items'])} item(s) this week", _fmt_age(t["age_days"]),
                f"signal {t['top_signal']}"]
        if t["material"]:
            bits.append(f"ESCALATION: {t['material_reason']}")
        lines.append(f"[{t['thread_id']}] {t['label']} — {seen}")
        lines.append(f"    {' · '.join(bits)}")
        for it in t["items"][:max_items]:
            lines.append(f"    - {it['title']}: {it['summary'][:160]}")
    return "\n".join(lines)


def render_catchup_section(threads: list[dict], max_threads: int = 16,
                           max_items: int = 3) -> str:
    """Render the catch-up brief's news context — undelivered threads lead."""
    missed = [t for t in threads if t["never_delivered"]]
    seen = [t for t in threads if not t["never_delivered"]]
    lines = ["## Field News — what arrived while you were away", ""]
    lines.append(
        "Threads under NEVER DELIVERED were never in a brief the researcher read — they are "
        "the real content of a catch-up. Threads under ALREADY SEEN are for "
        "continuity only; give their current state in a clause, not a paragraph."
    )
    lines.append("")
    if missed:
        lines.append("### NEVER DELIVERED — lead with these")
        for t in missed[:max_threads]:
            bits = [f"{len(t['items'])} item(s)", _fmt_age(t["age_days"]), f"signal {t['top_signal']}"]
            if t["material"]:
                bits.append(f"ESCALATION: {t['material_reason']}")
            lines.append(f"[{t['thread_id']}] {t['label']} — " + " · ".join(bits))
            for it in t["items"][:max_items]:
                lines.append(f"    - {it['title']}: {it['summary'][:160]}")
        lines.append("")
    if seen:
        lines.append("### ALREADY SEEN — continuity only")
        for t in seen[:8]:
            lines.append(f"[{t['thread_id']}] {t['label']} — {len(t['items'])} new item(s) since")
    return "\n".join(lines)


# The instruction appended to the system prompt so coverage can be recorded.
COVERAGE_FOOTER_INSTRUCTION = (
    "COVERAGE FOOTER (required). After the prose, on its own final line, emit "
    "exactly one machine-readable line naming the threads you used:\n"
    "<<THREADS: thread-id(lead,angle=<angle>); other-id(mention); third-id(mention)>>\n"
    "Use the bracketed thread ids from the context verbatim. Mark exactly one as "
    "`lead` — the thread your opening paragraph is about — with the angle you took "
    "from its ANGLE line. Mark every other thread you referred to as `mention`. "
    "This line is stripped before display and is how Metis avoids repeating itself "
    "tomorrow; a brief without it will repeat today's lead."
)


# ---------------------------------------------------------------------------
# Recording what a brief actually covered
# ---------------------------------------------------------------------------

# The model reports its own coverage on a final line, which we strip before
# display. Self-reporting beats guessing from the ranking: the model may
# reasonably lead with the second-ranked thread, and an inferred record would
# then put the wrong thread on cooldown — the exact bug this module exists to
# fix, reintroduced one level up.
_FOOTER_RE = re.compile(r"<<\s*THREADS\s*:(.*?)>>", re.IGNORECASE | re.DOTALL)


def parse_coverage_footer(text: str) -> tuple[str, list[dict]]:
    """Split a generated brief into (display_text, coverage entries).

    Expected footer: <<THREADS: ebola-drc(lead,angle=policy); malaria-africa(mention)>>
    A missing or malformed footer yields an empty list — the caller falls back
    to the ranking rather than losing the brief.
    """
    m = _FOOTER_RE.search(text or "")
    if not m:
        return (text or "").strip(), []
    body = m.group(1)
    clean = _FOOTER_RE.sub("", text).strip()

    entries: list[dict] = []
    for chunk in re.split(r"[;\n]", body):
        chunk = chunk.strip().strip(".,")
        if not chunk:
            continue
        mm = re.match(r"^([a-z0-9\-]+)\s*(?:\((.*?)\))?$", chunk, re.IGNORECASE)
        if not mm:
            continue
        tid = mm.group(1).lower()
        attrs = (mm.group(2) or "").lower()
        role = "lead" if "lead" in attrs else "mention"
        angle = ""
        am = re.search(r"angle\s*=\s*([a-z\-]+)", attrs)
        if am:
            angle = am.group(1)
            if angle not in ANGLES:
                angle = ""
        entries.append({"thread_id": tid, "role": role, "angle": angle})
    return clean, entries


def record_coverage(conn: sqlite3.Connection, insight_key: str, period: str,
                    entries: list[dict]) -> int:
    """Record which threads a brief led with / mentioned. Replaces prior rows
    for this insight_key so a regenerated brief does not double-count."""
    ensure_tables(conn)
    if not insight_key:
        return 0
    now = datetime.datetime.now().isoformat()
    try:
        conn.execute("DELETE FROM news_thread_mentions WHERE insight_key = ? AND period = ?",
                     (insight_key, period))
        n = 0
        for e in entries:
            tid = (e.get("thread_id") or "").strip()
            if not tid:
                continue
            conn.execute(
                "INSERT INTO news_thread_mentions (thread_id, insight_key, period, role, angle, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (tid, insight_key, period, e.get("role") or "mention",
                 e.get("angle") or "", now),
            )
            n += 1
        conn.commit()
        return n
    except sqlite3.Error:
        return 0


# ---------------------------------------------------------------------------
# Missed news — items never delivered in a brief the researcher read
# ---------------------------------------------------------------------------

def missed_threads(conn: sqlite3.Connection, days: int = 14,
                   min_signal: str = "medium") -> list[dict]:
    """Threads with recent activity that never appeared in a brief marked read.

    This is the answer to "which news have I missed" — derived, not stored.
    Feeds the catch-up brief and the weekly's "new this week" labelling.
    """
    since = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    threads = thread_window(conn, since)
    rank = {"high": 3, "medium": 2, "low": 1}
    floor = rank.get(min_signal, 2)
    return [
        t for t in threads
        if t["never_delivered"] and rank.get(t["top_signal"], 1) >= floor
    ]
