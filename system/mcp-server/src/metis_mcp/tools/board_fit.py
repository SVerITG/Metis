"""Which of the three Today boards does an item belong on — and why?

WHY THIS EXISTS
    The Outbreaks board was filling with things that are not outbreaks. Measured
    on 2026-09-21: of the twelve most recently harvested rows, four were an
    actual outbreak (and all four were instalments of the SAME one). The other
    eight were a regional committee session, a call-to-action declaration, a
    governance report, an infodemic trends report, an electronic surveillance
    bulletin and two country-office newsletters.

    A board that mixes those together cannot be followed, and the evidence that
    it could not be followed was already on screen: the pin machinery shipped on
    2026-09-04 and, two weeks later, `pin_order` was still 0 on every row of
    every board. Nobody pins a feed they have given up reading.

WHAT IT DOES
    One deterministic pass over the title and description. No network, no model
    call, no cost — so it can run on EVERY write path and a reader can always be
    told, in words, why a row was filed where it was.

    Three outcomes:
      * a board name  — file it there, which may not be the board it arrived on
      * ``None``      — it belongs on no board at all
    plus, always, a reason string. The reason is the point: a classifier whose
    verdict cannot be explained is one nobody will trust enough to leave on.

THE EDITORIAL BAR
    Taken from the board's own update prompt, which already stated it: mirror
    what WHO's Disease Outbreak News reports, "which lists only the outbreaks
    that matter rather than every regional press release". So an outbreak needs
    a pathogen NAMED IN ITS TITLE, plus a place, plus outbreak-signal
    vocabulary — with one exception for the bare "Disease – Country" headline
    form, which names no signal and does not need to. Fewer legs than that is a
    journal paper or a policy page, not an outbreak.

ORDER OF JUDGEMENT, and the one trade-off in it
    Document-type rejections are tested FIRST. That means a genuine outbreak
    written up as a monthly bulletin is rejected on its wrapper rather than kept
    on its contents. That is deliberate — periodicals are exactly what flooded
    the board — but it is the rule most likely to need revisiting, so it is
    stated here rather than buried.

NOTHING IS DELETED
    A rejected item is still written, with ``dismissed=1`` and its reason
    stored. A misfile therefore stays visible, auditable and reversible instead
    of vanishing between two scans with no record that it ever arrived.
"""
from __future__ import annotations

import re

BOARDS = ("outbreaks", "events", "funding")


def _alts(terms) -> re.Pattern:
    """Compile terms into one word-boundary alternation, plural-tolerant."""
    parts = [re.escape(t).replace(r"\ ", r"\s+") for t in sorted(terms, key=len, reverse=True)]
    return re.compile(r"\b(" + "|".join(parts) + r")(?:s|es)?\b", re.I)


# ── Document types that belong on no board ──────────────────────────────────
# Periodicals, governance papers and job adverts. Each entry is (regex, label);
# the label is what the reader is shown, so it says what KIND of thing it is
# rather than which word tripped.
_REJECT = [
    (r"\bnewsletter\b",                         "periodical: newsletter"),
    (r"\bbulletin\b",                           "periodical: bulletin"),
    (r"\binfodemic\b",                          "periodical: trends report"),
    (r"\btrends?\s+report\b",                   "periodical: trends report"),
    (r"\bannual\s+report\b",                    "governance: annual report"),
    (r"\breport\s+of\s+the\s+regional\s+director\b", "governance: director's report"),
    (r"\brapport\b",                            "governance: visit/activity report"),
    (r"\bcall\s+to\s+action\b",                 "advocacy: declaration"),
    (r"\bdeclaration\b",                        "advocacy: declaration"),
    (r"\bcommuniqu",                            "advocacy: communiqué"),
    (r"\bvacanc(y|ies)\b",                      "recruitment: job vacancy"),
    (r"\brecruitment\b",                        "recruitment: job vacancy"),
    (r"\bterms\s+of\s+reference\b",             "recruitment: terms of reference"),
    (r"\bstrateg(y|ic\s+plan)\b\s*,?\s*\d{4}",  "governance: strategy document"),
    (r"\bpress\s+release\b",                    "governance: press release"),
]
_REJECT_RX = [(re.compile(p, re.I), lab) for p, lab in _REJECT]

# ── Outbreaks: pathogen AND place AND signal ────────────────────────────────
_DISEASES = {
    "ebola", "bundibugyo", "sudan virus", "marburg", "lassa", "mpox", "monkeypox",
    "cholera", "measles", "rubella", "polio", "poliovirus", "poliomyelitis", "cvdpv",
    "malaria", "dengue", "chikungunya", "zika", "yellow fever", "oropouche",
    "rift valley fever", "crimean-congo", "meningitis", "meningococcal",
    "diphtheria", "pertussis", "plague", "anthrax", "rabies", "tetanus",
    "influenza", "avian influenza", "h5n1", "h5n5", "h1n1", "h7n9",
    "covid", "sars-cov-2", "sars", "mers", "nipah", "hendra", "hantavirus",
    "hepatitis", "typhoid", "salmonella", "listeria", "shigella", "botulism",
    "escherichia coli", "e. coli", "norovirus", "rotavirus", "legionella",
    "west nile", "japanese encephalitis", "encephalitis", "leptospirosis",
    "tuberculosis", "hiv", "aids", "trypanosomiasis", "sleeping sickness",
    "leishmaniasis", "kala-azar", "schistosomiasis", "onchocerciasis",
    "lymphatic filariasis", "buruli ulcer", "leprosy", "trachoma", "scabies",
    "dracunculiasis", "guinea worm", "chagas", "snakebite", "mycetoma",
    "acute watery diarrhoea", "acute watery diarrhea", "hand foot and mouth",
    "haemorrhagic fever", "hemorrhagic fever", "food poisoning", "anaemia",
}
# Places. Countries carry most of the weight; the regions are here because an
# outbreak is often reported at that scale — a pathogen named against a region
# rather than a country — and requiring a pathogen and a signal alongside keeps
# a region name from over-matching on its own.
_PLACES = {
    "afghanistan", "algeria", "angola", "argentina", "bangladesh", "benin",
    "bolivia", "botswana", "brazil", "burkina faso", "burundi", "cambodia",
    "cameroon", "canada", "central african republic", "chad", "chile", "china",
    "colombia", "comoros", "congo", "costa rica", "cuba", "côte d'ivoire",
    "cote d'ivoire", "ivory coast", "djibouti", "dominican republic", "drc",
    "dr congo", "democratic republic of the congo", "ecuador", "egypt",
    "el salvador", "equatorial guinea", "eritrea", "eswatini", "ethiopia",
    "france", "gabon", "gambia", "germany", "ghana", "guatemala", "guinea",
    "guinea-bissau", "haiti", "honduras", "india", "indonesia", "iran", "iraq",
    "italy", "jamaica", "japan", "jordan", "kenya", "laos", "lebanon", "lesotho",
    "liberia", "libya", "madagascar", "malawi", "malaysia", "mali", "mauritania",
    "mauritius", "mexico", "morocco", "mozambique", "myanmar", "namibia", "nepal",
    "netherlands", "nicaragua", "niger", "nigeria", "pakistan", "panama",
    "papua new guinea", "paraguay", "peru", "philippines", "portugal", "rwanda",
    "sao tome", "saudi arabia", "senegal", "seychelles", "sierra leone",
    "somalia", "south africa", "south sudan", "spain", "sri lanka", "sudan",
    "syria", "tanzania", "thailand", "timor-leste", "togo", "tunisia", "turkey",
    "uganda", "ukraine", "united kingdom", "united states", "uruguay",
    "uzbekistan", "venezuela", "vietnam", "yemen", "zambia", "zimbabwe",
    "africa", "west africa", "central africa", "east africa", "southern africa",
    "sahel", "horn of africa", "great lakes", "europe", "americas", "caribbean",
    "south-east asia", "southeast asia", "middle east", "western pacific",
    "eastern mediterranean", "latin america",
}
_SIGNALS = {
    "outbreak", "epidemic", "pandemic", "resurgence", "upsurge", "flare-up",
    "case", "confirmed case", "suspected case", "death", "fatality",
    "case fatality", "attack rate", "incidence", "cluster", "infection",
    "transmission", "spread", "emergence", "emerging", "re-emergence",
    "public health emergency", "emergency", "situation report", "flash update",
    "alert", "grade 3", "circulating", "imported case", "index case",
    "notification", "surveillance signal", "epi week",
}
_DISEASE_RX = _alts(_DISEASES)
_PLACE_RX = _alts(_PLACES)
_SIGNAL_RX = _alts(_SIGNALS)

# ── Events and funding ──────────────────────────────────────────────────────
_EVENT_TERMS = {
    "congress", "conference", "symposium", "colloquium", "summit", "session",
    "assembly", "committee meeting", "annual meeting", "meeting", "workshop",
    "short course", "training course", "summer school", "winter school",
    "webinar", "seminar", "forum", "convention", "expo", "hackathon",
    "world health assembly", "abstract deadline", "registration opens",
}
_FUNDING_TERMS = {
    "call for proposal", "call for application", "call for expression",
    "request for proposal", "funding call", "funding opportunity", "funding",
    "grant", "sub-grant", "award", "fellowship", "scholarship", "bursary",
    "prize", "seed fund", "work programme", "work program", "funding programme",
    "research programme", "application deadline", "deadline", "budget",
    "financed by", "co-funded", "letter of intent", "stipend",
}
_EVENT_RX = _alts(_EVENT_TERMS)
_FUNDING_RX = _alts(_FUNDING_TERMS)


def _hits(rx: re.Pattern, text: str) -> list[str]:
    """Distinct matched terms, lower-cased, in the order they appear."""
    out: list[str] = []
    for m in rx.finditer(text or ""):
        t = re.sub(r"\s+", " ", m.group(0).lower()).strip()
        if t not in out:
            out.append(t)
    return out


def _quote(terms: list[str], n: int = 3) -> str:
    return ", ".join("'%s'" % t for t in terms[:n])


def classify(title: str, description: str = "") -> tuple[str | None, str]:
    """Return ``(board_or_None, reason)`` for one candidate item.

    The board returned may differ from the one the item arrived on — that is
    the re-routing case, and it is the common one: a congress harvested from an
    outbreak feed is still a congress.
    """
    title = (title or "").strip()
    desc = (description or "").strip()
    if not title:
        return None, "rejected: no title"
    blob = f"{title} {desc}"

    for rx, label in _REJECT_RX:
        m = rx.search(blob)
        if m:
            return None, "rejected: %s (matched '%s')" % (
                label, re.sub(r"\s+", " ", m.group(0).lower()))

    # THE PATHOGEN MUST BE IN THE TITLE. Reading the conjunction across title
    # and description together let a funding work-programme onto the Outbreaks
    # board, because its blurb listed the diseases the money is for — every leg
    # satisfied, nothing about an outbreak. An item that IS an outbreak names
    # its pathogen up front; a description that merely mentions diseases does
    # not make the item one.
    dis = _hits(_DISEASE_RX, title)
    plc_t = _hits(_PLACE_RX, title)
    plc = _hits(_PLACE_RX, blob)
    sig = _hits(_SIGNAL_RX, blob)
    if dis and (plc_t or (plc and sig)):
        # "<Pathogen> - <Country>" is the Disease Outbreak News headline form,
        # and it carries no signal word at all, so pathogen-and-place in the
        # title is accepted on its own; anything looser needs a signal too.
        return "outbreaks", "outbreak: pathogen %s + place %s%s" % (
            _quote(dis, 1), _quote(plc, 1),
            (" + signal %s" % _quote(sig, 1)) if sig else " (both in title)")

    # A title hit counts double. The title is what the item declares itself to
    # be; a description mentions the surrounding furniture — an awards line in
    # a congress blurb should not turn the congress into a funding call.
    ev = _hits(_EVENT_RX, title)
    fu = _hits(_FUNDING_RX, title)
    ev_d = [t for t in _hits(_EVENT_RX, desc) if t not in ev]
    fu_d = [t for t in _hits(_FUNDING_RX, desc) if t not in fu]
    ev_score = 2 * len(ev) + len(ev_d)
    fu_score = 2 * len(fu) + len(fu_d)

    if ev_score or fu_score:
        # Ties go to Events: a congress with a submission deadline is still a
        # congress, whereas a funding call rarely describes itself as a meeting.
        if ev_score >= fu_score:
            where = "title" if ev else "description"
            return "events", "event: %s in %s" % (_quote(ev or ev_d), where)
        where = "title" if fu else "description"
        return "funding", "funding: %s in %s" % (_quote(fu or fu_d), where)

    # Say which leg was missing when it was nearly an outbreak — that is the
    # difference between a verdict and an excuse.
    if dis or sig:
        missing = [n for n, v in (("pathogen", dis), ("place", plc), ("signal", sig)) if not v]
        return None, "rejected: outbreak-shaped but no %s named" % " or ".join(missing)
    return None, "rejected: no board vocabulary matched"


def route(board: str, title: str, description: str = "") -> tuple[str, bool, str]:
    """Decide where an item harvested for ``board`` should actually be written.

    Returns ``(target_board, keep, reason)``. When ``keep`` is False the item is
    still written — to ``target_board``, dismissed, carrying ``reason`` — so the
    rejection stays on the record instead of disappearing between two scans.
    """
    board = (board or "").strip().lower()
    fit, reason = classify(title, description)
    if fit is None:
        return (board if board in BOARDS else "outbreaks"), False, reason
    if fit != board:
        reason = "re-routed from %s — %s" % (board, reason)
    return fit, True, reason
