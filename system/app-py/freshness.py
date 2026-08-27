"""What is new, and what is the same running story told again.

the researcher, 2026-08-27: highlight new content and put it on top; and "in the lists
there is the same item though (outbreak I have seen Ebola multiple times for
example)".

WHAT THE EBOLA ROWS ACTUALLY ARE — and this changes the fix entirely:

    EBOLA BUNDIBUGYO … Weekly External Situation Report 13, data as of 09 August
    EBOLA BUNDIBUGYO … Weekly External Situation Report 14, data as of 16 August
    EBOLA BUNDIBUGYO … Weekly External Situation Report 15, data as of 23 August
    EBOLA BUNDIBUGYO … Weekly External Situation Report 15, data as of 23 August

Three of those are a WEEKLY SERIES: each report is genuinely new, and deleting
any of them would be deleting information. Exactly one is a true duplicate.
Seeing Ebola three times is not a bug in the data — it is a list showing every
instalment of one running story with equal weight.

So there are two different fixes, and confusing them is how you lose data:

  DUPLICATE   the same instalment twice → collapse, keep one
  SERIES      instalments of one story  → group under the newest, fold the rest

AND A TRAP WORTH NAMING. A naive similarity fingerprint merges these, which
would silently hide a second outbreak:

    WFP Bangladesh Country Brief, August 2026
    WFP Togo Country Brief, August 2026          ← different country
    Venezuela: Earthquakes - LTC Situation Report
    Colombia - Earthquake: LTC Telecoms Report   ← different country

The rule below only removes what VARIES BETWEEN INSTALMENTS — numbers, dates,
month names, "no. 4", "week 12". Everything else, including every place name,
is kept and must match. Bangladesh and Togo therefore stay apart, while
Report 13 and Report 14 come together.
"""
from __future__ import annotations

import datetime as _dt
import re

# Removed when building a series key: the parts that change between instalments
# of the same running story. Nothing else is touched — a place name is never a
# variable part, and treating it as one is how two outbreaks become one.
_MONTHS = ("january february march april may june july august september "
           "october november december jan feb mar apr jun jul aug sep sept oct "
           "nov dec").split()
_SERIAL = re.compile(
    r"\b(?:no|nr|num|number|issue|vol|volume|part|week|day|report|update|"
    r"situation\s+report|sitrep|edition|ed)\.?\s*#?\s*\d+\b", re.I)
# Both spellings. "The 3rd International Conference on PEN-Plus" and "Call to
# Action – Third International Conference for PEN-Plus" are one event announced
# by two sources; only the digit form was being stripped, so they stayed apart.
_ORDINAL = re.compile(
    r"\b(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|"
    r"eighth|ninth|tenth|eleventh|twelfth)\b", re.I)
_DATEISH = re.compile(r"\b\d{1,4}[-/.]\d{1,2}(?:[-/.]\d{1,4})?\b")
_BARE_NUM = re.compile(r"\b\d+\b")
_MONTH_RE = re.compile(r"\b(" + "|".join(_MONTHS) + r")\b", re.I)
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def series_key(title: str) -> str:
    """A fingerprint that ignores only the instalment, never the subject.

    'Ebola … Situation Report 13, data as of 09 August 2026' and the same with
    14 collapse to one key; 'WFP Bangladesh Country Brief' and 'WFP Togo Country
    Brief' do not, because the country is not a variable part.
    """
    t = (title or "").lower()
    t = _SERIAL.sub(" ", t)
    t = _ORDINAL.sub(" ", t)
    t = _DATEISH.sub(" ", t)
    t = _MONTH_RE.sub(" ", t)
    t = _BARE_NUM.sub(" ", t)
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    # Drop the words that carry no subject, so wording differences between
    # sources ("The 3rd International Conference on X" / "Call to Action –
    # Third International Conference for X") still land together.
    stop = {"the", "a", "an", "of", "in", "to", "and", "for", "on", "at", "as",
            "is", "are", "with", "from", "by", "data", "external", "weekly",
            "monthly", "daily", "call", "action"}
    words = [w for w in t.split() if w not in stop and len(w) > 2]
    return " ".join(sorted(set(words)))[:220]


def exact_key(title: str) -> str:
    """A true duplicate: the same instalment, arrived twice."""
    return _WS.sub(" ", _PUNCT.sub(" ", (title or "").lower())).strip()


# ── freshness ───────────────────────────────────────────────────────────────
# the researcher asked for new content to be highlighted AND on top. Three bands, because
# two would put a five-day-old item in the same bucket as this morning's, and
# four is more than anyone reads at a glance.
def band(iso: str, now: _dt.datetime | None = None) -> str:
    """'today' · 'week' · '' — the empty string meaning 'not new'."""
    if not iso:
        return ""
    try:
        d = _dt.datetime.fromisoformat(str(iso)[:19].replace("Z", ""))
    except ValueError:
        try:
            d = _dt.datetime.fromisoformat(str(iso)[:10])
        except ValueError:
            return ""
    now = now or _dt.datetime.now()
    if d.date() == now.date():
        return "today"
    if (now - d).days < 7:
        return "week"
    return ""


def collapse(rows: list, title_field: str = "title", ts_field: str = "created_at",
             fold_series: bool = True) -> list:
    """Fold duplicates and group series, newest and freshest first.

    Every input row comes back somewhere: a duplicate becomes `_dupes` on the
    row that survives, and an older instalment becomes `_earlier` on the newest.
    Nothing is discarded — the same rule the focus safe and the reading stack
    follow, and for the same reason. A list that quietly drops rows cannot be
    checked against the source.
    """
    def ts(r):
        return str(r.get(ts_field) or "")

    ordered = sorted(rows, key=ts, reverse=True)

    # 1. exact duplicates — the same instalment twice
    seen: dict[str, dict] = {}
    deduped: list = []
    for r in ordered:
        k = exact_key(r.get(title_field, ""))
        if k and k in seen:
            seen[k].setdefault("_dupes", []).append(r)
            continue
        r = dict(r)
        seen[k] = r
        deduped.append(r)

    if not fold_series:
        for r in deduped:
            r["_fresh"] = band(ts(r))
        return _fresh_first(deduped, ts)

    # 2. series — instalments of one running story
    heads: dict[str, dict] = {}
    out: list = []
    for r in deduped:
        k = series_key(r.get(title_field, ""))
        if k and k in heads:
            heads[k].setdefault("_earlier", []).append(r)
            continue
        heads[k] = r
        out.append(r)

    for r in out:
        r["_fresh"] = band(ts(r))
        r["_n_earlier"] = len(r.get("_earlier", []))
        r["_n_dupes"] = len(r.get("_dupes", []))
    return _fresh_first(out, ts)


def _fresh_first(rows: list, ts) -> list:
    """New on top, then newest first. the researcher asked for both, and they are not the
    same instruction: 'newest first' already orders by time, but a 3-day-old
    item and a 3-month-old item look identical in a list until something says
    which arrived this week."""
    rank = {"today": 0, "week": 1, "": 2}
    # Two keys, opposite directions: freshness ascending (today first) and time
    # descending (newest first) inside each band. Sorting twice, stably, is
    # clearer than inverting a string date arithmetically.
    rows = sorted(rows, key=ts, reverse=True)
    return sorted(rows, key=lambda r: rank.get(r.get("_fresh", ""), 2))
