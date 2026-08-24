"""evidence.py — answer a factual question from the evidence, not from one number.

WHY THIS EXISTS, AND WHY IT IS NOT `verification.py`
    `verification.py` checks PROVENANCE: does the cited page contain what the
    citation says it does. That is necessary and it is not fact-checking. A claim
    can be perfectly cited and still be the wrong answer, because the number that
    was cited is one of several the literature reports and the citation happened
    to land on one of them.

    Measured in this corpus on 2026-08-24: **438 quantified sensitivity /
    specificity statements**, with specificity for serological HAT tests ranging
    from **72% to 99.7%**. Ask "what is the specificity?" and a model returns one
    confident number. Which one is close to arbitrary, and the answer looks
    perfectly sourced either way. Citation checking cannot see this failure at
    all — the number IS on the page.

THE GOVERNING IDEA
    **For a quantitative claim the honest answer is a distribution across sources
    plus the qualifiers that explain why they differ — never a single value.**

    A specificity of 90% and a specificity of 99.7% are usually not a
    contradiction. They are two different tests, or two different populations, or
    two different reference standards. Collapsing them into one number destroys
    exactly the information an epidemiologist needs, and does so invisibly.

    So this module reports:
      · every quantified statement it can find, with document and page;
      · the SPREAD, stated as a spread;
      · the QUALIFIERS attached to each figure — sample size, CI, reference
        standard, population, setting, threshold — because those are what make
        two numbers comparable or not;
      · what is MISSING (no CI, no n, no reference standard named), since an
        unqualified estimate is not a better estimate;
      · sentences near the figure that COMPLICATE it ("varies with", "lower in",
        "however") — the related information that gets dropped first;
      · how OLD the evidence is, so "is there newer work?" is answerable.

WHY LEXICAL RETRIEVAL, NOT SEMANTIC
    Semantic search finds passages *about* specificity. This needs passages
    *containing a specificity number*, which is a lexical pattern, not a meaning.
    Keeping it lexical also keeps the module deterministic — no model, same
    discipline as `verification.py`. Judgement about which estimate applies to
    the researcher's question is theirs, and it should be made with the spread in
    front of them rather than instead of it.
"""
from __future__ import annotations

import re
from datetime import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# ---------------------------------------------------------------------------
# What kind of quantity is being asked about
# ---------------------------------------------------------------------------
# Grouped by family because the QUALIFIERS that matter differ by family: a
# diagnostic-accuracy figure is meaningless without its reference standard, a
# prevalence is meaningless without its population, an effect size is meaningless
# without its comparator.
METRIC_FAMILIES: dict[str, list[str]] = {
    "diagnostic accuracy": [
        "sensitivity", "specificity", "positive predictive", "negative predictive",
        "ppv", "npv", "likelihood ratio", "auc", "area under the curve",
        "youden", "accuracy", "false positive", "false negative",
    ],
    "burden": [
        "prevalence", "incidence", "seroprevalence", "attack rate",
        "cases per", "per 10 000", "per 100 000", "per 1000",
    ],
    "coverage": [
        "coverage", "uptake", "completeness", "reporting rate", "adherence",
        "screening rate", "treatment coverage",
    ],
    "effect": [
        "odds ratio", "risk ratio", "hazard ratio", "relative risk",
        "rate ratio", "incidence rate ratio", "efficacy", "effectiveness",
    ],
    "mortality": [
        "case fatality", "mortality", "lethality", "death rate", "survival",
    ],
    "duration": [
        "incubation", "median duration", "time to", "median survival",
        "delay", "turnaround",
    ],
}

# The qualifiers. Each one, when ABSENT, is a reason not to trust a figure — the
# "evaluation debt" framing from the AI in Public Health course, applied to the
# researcher's own literature.
_QUALIFIER_PATTERNS: dict[str, re.Pattern] = {
    # Both of the next two were far too strict on the first run and produced
    # FALSE "not stated" verdicts — "sample size absent in 466/471 estimates",
    # and a confidence interval reported as missing from a sentence that read
    # "a 95% confidence interval (CI) of 99.0% to 99.8". Overstating what the
    # sources fail to say is the same corrosive false positive as a wrong
    # citation verdict — it discredits the report in the other direction.
    "sample size": re.compile(
        r"\b[nN]\s?=\s?\d[\d,.\s]{0,8}"
        r"|\b\d[\d,.\s]{1,8}\s?(?:patients|participants|subjects|samples|"
        r"individuals|persons|cases|controls|sera|specimens)\b", re.I),
    # Anchored on CI, then ANY two numbers within a short window. The separator
    # zoo is real: "CI: 63.5%; 74.5%", "(CI) of 99.0% to 99.8",
    # "95% CI 1.2–3.4", "[CI: 51.8%-63.7%]".
    "confidence interval": re.compile(
        r"(?:\b\d{2}\s?%\s?)?(?:CI|confidence interval|credible interval)"
        r"[^\d\n]{0,18}\d[\d.]*\s?%?\s?(?:[-–—]|to|;|,)\s?\d[\d.]*", re.I),
    "reference standard": re.compile(
        r"reference standard|gold standard|trypanolysis|\bTL\b|parasitolog\w+|"
        r"confirmed by (?:PCR|microscopy|culture)|composite reference", re.I),
    "population": re.compile(
        r"passive (?:case )?(?:detection|screening)|active screening|"
        r"community[- ]based|hospital[- ]based|health[- ]facility|blood donors|"
        r"pregnant|children|adults|clinic attendees|febrile patients|"
        r"suspected cases|endemic (?:area|village|focus)", re.I),
    "setting": re.compile(
        r"\b(?:DRC|Democratic Republic|Congo|Guinea|Angola|Chad|Uganda|"
        r"C[oô]te d.Ivoire|Ivory Coast|Cameroon|Sudan|Malawi|Tanzania|"
        r"Central African Republic|field conditions|laboratory conditions)\b"),
    "threshold": re.compile(
        r"cut[- ]?off|threshold|titre|titer|dilution|1\s?:\s?\d+|\bOD\b", re.I),
}

# Words that change what a number IS, not merely how to read it.
#
# Found on the first real run: the lowest "specificity" values in the corpus were
# −0.33% ("the DIFFERENCE in specificity was minimal"), 0.5% ("required to
# estimate specificity at a PRECISION of 0.5%") and 0.5% ("with 95% specificity,
# at PREVALENCES of ... 0.5%"). None of those is a specificity. Left in, they
# dragged the reported range from 96–100% down to 0.33–100% — which is not a
# conservative error, it is a fabricated spread, and the spread is the whole
# output of this tool.
_NOT_THE_METRIC = re.compile(
    r"\b(difference|differences|change|changes|increase|decrease|reduction|"
    r"improvement|gain|loss|drop|delta|precision|margin|variation|"
    r"prevalence|prevalences|at a precision of)\b", re.I)

_COMPARATIVE = re.compile(
    r"\s*(?:points?\s+)?(?:lower|higher|greater|less|more|below|above|worse|better|than)\b", re.I)

# Sentences that COMPLICATE a figure. These are the "important related
# information" that gets dropped first when an answer is compressed to a number,
# and they are detectable lexically — no judgement required to notice that a
# paper said "specificity was lower in".
_CAVEAT = re.compile(
    r"\b(however|but |although|whereas|varies?\s+(?:with|by|between)|"
    r"depend(?:s|ing)?\s+on|lower in|higher in|limitation|caveat|"
    r"may not|cannot be|should be interpreted|heterogen\w+|"
    r"wide (?:range|variation)|inconsistent|conflicting|not validated|"
    r"small sample|selection bias|spectrum bias)\b", re.I)

# metric ... value%   |   metric ... = value   |   value% ... metric
_QUANT = re.compile(
    r"(?P<metric>%s)\b[^.\n;]{0,90}?(?<![\d?·.,])(?P<value>\d{1,3}(?:[.,]\d{1,2})?)\s?(?P<unit>%%|percent)"
    % "|".join(sorted({m for v in METRIC_FAMILIES.values() for m in v}, key=len, reverse=True)),
    re.I)
# The reverse form ("98% specificity") is inherently riskier than the forward one
# and is deliberately kept on a short leash: at most 22 characters, and none of
# them a comma, bracket or clause break. Without that it read
# "sensitivity ... (71%-89%) whereas specificity was very high" as
# `specificity = 71%` — the number belonged to the clause before it.
_QUANT_REV = re.compile(
    r"(?<![\d?·.,])(?P<value>\d{1,3}(?:[.,]\d{1,2})?)\s?(?P<unit>%%|percent)[^.\n;,()\[\]]{0,22}?(?P<metric>%s)\b"
    % "|".join(sorted({m for v in METRIC_FAMILIES.values() for m in v}, key=len, reverse=True)),
    re.I)

_YEAR = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
_WS = re.compile(r"\s+")


def _family_of(metric: str) -> str:
    m = metric.lower()
    for fam, terms in METRIC_FAMILIES.items():
        if any(t in m or m in t for t in terms):
            return fam
    return "other"


def _metrics_in(text: str) -> list[str]:
    """Which metric families the question is asking about."""
    low = (text or "").lower()
    hits = []
    for fam, terms in METRIC_FAMILIES.items():
        if any(t in low for t in terms):
            hits.append(fam)
    return hits


def _topic_terms(question: str, metric_terms: set[str]) -> list[str]:
    """The subject of the question, with metric words and stopwords removed.

    "what is the specificity of CATT in passive screening" -> ["catt","passive",
    "screening"]. These narrow retrieval to the thing being asked about; without
    them a question about one test returns every accuracy figure in the corpus.
    """
    stop = {
        "what", "whats", "which", "when", "where", "does", "do", "is", "are",
        "the", "of", "in", "for", "and", "or", "to", "a", "an", "on", "with",
        "how", "much", "many", "value", "values", "reported", "report", "about",
        "me", "give", "tell", "can", "you", "there", "any", "that", "this",
        "high", "good", "best", "typical", "average", "range", "evidence",
        # Generic research nouns are NOT topics. "specificity of the assay"
        # narrowed retrieval to chunks containing the word "assay" and dropped a
        # fully-qualified estimate whose sentence simply said "a specificity of
        # 99.5%". A term that appears in every paper discriminates nothing while
        # excluding everything that happens not to use it.
        "assay", "assays", "test", "tests", "testing", "study", "studies",
        "trial", "trials", "paper", "papers", "article", "literature", "data",
        "result", "results", "patient", "patients", "sample", "samples",
        "method", "methods", "analysis", "review", "reported", "estimate",
        "estimates", "diagnostic", "diagnosis",
    }
    out = []
    for w in re.findall(r"[a-z0-9][a-z0-9\-]{1,}", (question or "").lower()):
        if w in stop or len(w) < 3:
            continue
        if any(w in t or t in w for t in metric_terms):
            continue
        if w not in out:
            out.append(w)
    return out[:6]


def _sentence_of(text: str, start: int, end: int) -> str:
    left = max(text.rfind(". ", 0, start), text.rfind("\n", 0, start))
    left = 0 if left < 0 else left + 1
    m = re.search(r"[.!?](?:\s|$)", text[end:])
    right = end + (m.end() if m else 120)
    return _WS.sub(" ", text[left:min(right, len(text))]).strip()


def gather_quantities(
    question: str,
    layers: list[str] | None = None,
    max_chunks: int = 600,
) -> dict:
    """Find every quantified statement in the corpus that answers this question.

    Deterministic throughout: lexical retrieval, regex extraction, set membership
    for qualifiers. It can miss a figure phrased unusually; it cannot invent one.
    """
    families = _metrics_in(question) or list(METRIC_FAMILIES)
    metric_terms = {t for f in families for t in METRIC_FAMILIES[f]}
    topics = _topic_terms(question, metric_terms)

    with connect(paths.db) as con:
        sql = ["SELECT k.slug AS layer, p.title, p.source_file, p.page_start, "
               "       p.page_end, p.chunk_text "
               "FROM pdf_chunks p LEFT JOIN knowledge_databases k ON k.id = p.db_id "
               "WHERE ("]
        params: list = []
        sql.append(" OR ".join("lower(p.chunk_text) LIKE ?" for _ in metric_terms))
        params += [f"%{t.lower()}%" for t in metric_terms]
        sql.append(")")
        if topics:
            # Every topic term must be present — AND, not OR, or a question about
            # one test returns the whole corpus.
            #
            # But matched against the DOCUMENT, not just the chunk. A paper about
            # CATT does not repeat "CATT" in every paragraph: the sentence
            # "equivalent to a specificity of 99.5% (95% CI 99.0-99.8)" names no
            # test at all, and a chunk-only filter therefore dropped a perfectly
            # good, fully-qualified estimate. Topic is a property of the source,
            # not of the sentence.
            for t in topics:
                sql.append(" AND (lower(p.chunk_text) LIKE ? "
                           "OR lower(p.title) LIKE ? "
                           "OR lower(p.source_file) LIKE ?)")
                params += [f"%{t.lower()}%"] * 3
        if layers:
            sql.append(" AND k.slug IN (%s)" % ",".join("?" * len(layers)))
            params += layers
        sql.append(" LIMIT ?")
        params.append(max_chunks)
        rows = con.execute("".join(sql), tuple(params)).fetchall()

        # Relax to ANY topic term if the AND was too strict to return anything.
        # THREE STAGES, widening only when the previous one is too thin.
        #
        # Two estimates is not a spread, and a spread is this tool's entire
        # output — so returning one narrowly-matched figure is worse than
        # returning many broadly-matched ones, because it looks settled. Each
        # widening is recorded in `relaxed_match` and printed in the report, so
        # breadth is never silent.
        #
        #   1. every topic term present (above)
        #   2. any topic term present
        #   3. metric only — topic dropped entirely
        relaxed = False

        def _run(where_sql: str, extra: list) -> list:
            base = ("SELECT k.slug AS layer, p.title, p.source_file, p.page_start, "
                    "       p.page_end, p.chunk_text "
                    "FROM pdf_chunks p "
                    "LEFT JOIN knowledge_databases k ON k.id = p.db_id WHERE (")
            q = [base,
                 " OR ".join("lower(p.chunk_text) LIKE ?" for _ in metric_terms),
                 ")"]
            ps: list = [f"%{x.lower()}%" for x in metric_terms]
            if where_sql:
                q.append(where_sql)
                ps += extra
            if layers:
                q.append(" AND k.slug IN (%s)" % ",".join("?" * len(layers)))
                ps += layers
            q.append(" LIMIT ?")
            ps.append(max_chunks)
            return con.execute("".join(q), tuple(ps)).fetchall()

        if len(rows) < 3 and topics:
            relaxed = True
            any_sql = " AND (" + " OR ".join(
                "lower(p.chunk_text) LIKE ? OR lower(p.title) LIKE ? "
                "OR lower(p.source_file) LIKE ?" for _ in topics) + ")"
            any_params: list = []
            for x in topics:
                any_params += [f"%{x.lower()}%"] * 3
            wider = _run(any_sql, any_params)
            if len(wider) > len(rows):
                rows = wider
            if len(rows) < 3:
                rows = _run("", [])          # metric only — topic dropped

    findings: list[dict] = []
    seen: set[tuple] = set()
    for r in rows:
        text = r["chunk_text"] or ""
        for pat in (_QUANT, _QUANT_REV):
            for m in pat.finditer(text):
                metric = m.group("metric").lower().strip()
                if metric not in metric_terms:
                    continue
                # The REVERSE pattern (value first, metric after) is the risky
                # one. "Sensitivity was 100%, whereas specificity ranged from
                # 96.1%" gave `specificity = 100%` — the 100 belongs to the
                # metric BEFORE it, which the pattern cannot see. So if any
                # metric name sits just behind the value, the forward pattern
                # already owns this number and this match is spurious.
                if pat is _QUANT_REV:
                    behind = text[max(0, m.start() - 50):m.start()].lower()
                    if any(other in behind for other in metric_terms):
                        continue
                    # A modifier can sit on EITHER side of the figure. "would
                    # have resulted in a drop of 3.3% in sensitivity" is a change,
                    # and for the reverse form the word "drop" is behind the
                    # number where the inner-span check cannot reach it. Checking
                    # both sides is what makes the guard symmetric.
                    if _NOT_THE_METRIC.search(behind):
                        continue
                try:
                    value = float(m.group("value").replace(",", "."))
                except ValueError:
                    continue
                if not (0.0 <= value <= 100.0):
                    continue
                # Reject a match whose metric→value span crosses ANOTHER metric.
                # "RDT2 had the highest accuracy (69.3%), followed by CATT
                # (61.7%)" must not attach 61.7 to `accuracy`. The regex is
                # non-greedy so it takes the nearest percentage, but "nearest"
                # is not the same as "belonging to", and in a list of metrics it
                # silently is not.
                span = text[m.start():m.end()].lower()
                inner = span[len(metric):-len(m.group("unit"))]
                if any(other in inner for other in metric_terms if other != metric):
                    continue
                if _NOT_THE_METRIC.search(inner):
                    continue
                # A comparative just AFTER the number means the same thing —
                # "the specificity of the RDT was 4.3% lower than CATT" is a gap,
                # not a specificity, and the modifier sits on the far side of the
                # figure where `inner` cannot see it.
                if _COMPARATIVE.match(text[m.end():m.end() + 22]):
                    continue
                # A signed value is a change in the metric, not the metric.
                if text[max(0, m.start("value") - 1):m.start("value")] in ("-", "\u2212", "+"):
                    continue
                sentence = _sentence_of(text, m.start(), m.end())
                key = (r["source_file"], r["page_start"], metric, value)
                if key in seen:
                    continue
                seen.add(key)

                window = text[max(0, m.start() - 320):m.end() + 320]
                quals = {}
                for name, qp in _QUALIFIER_PATTERNS.items():
                    found = qp.findall(window)
                    if found:
                        flat = []
                        for f in found[:3]:
                            flat.append((f if isinstance(f, str) else " ".join(x for x in f if x)).strip())
                        quals[name] = sorted({x for x in flat if x})[:3]
                caveats = sorted({_WS.sub(" ", c).strip()
                                  for c in _CAVEAT.findall(window)})
                years = sorted({int(y) for y in _YEAR.findall(
                    f"{r['title']} {r['source_file']}")}, reverse=True)

                findings.append({
                    "metric": metric,
                    "family": _family_of(metric),
                    "value": value,
                    "document": r["title"] or "",
                    "layer": r["layer"] or "(unfiled)",
                    "page": r["page_start"],
                    "sentence": sentence[:300],
                    "qualifiers": quals,
                    "missing": [k for k in _QUALIFIER_PATTERNS if k not in quals],
                    "caveat_signals": caveats[:6],
                    "doc_year": years[0] if years else None,
                })

    return {
        "question": question,
        "families": families,
        "topic_terms": topics,
        "relaxed_match": relaxed,
        "chunks_scanned": len(rows),
        "findings": findings,
    }


def _spread(vals: list[float]) -> dict:
    vs = sorted(vals)
    n = len(vs)
    mid = vs[n // 2] if n % 2 else (vs[n // 2 - 1] + vs[n // 2]) / 2
    return {"n": n, "min": vs[0], "max": vs[-1], "median": round(mid, 1),
            "range": round(vs[-1] - vs[0], 1)}


@app.tool()
async def weigh_evidence(
    question: str,
    layers: str = "",
    show: int = 14,
) -> list[TextContent]:
    """What does the evidence in the corpus actually say about a quantity?

    Fact-checking a number is not the same as checking a citation. A figure can be
    correctly cited and still be one of many the literature reports — this corpus
    holds specificity estimates for HAT serology ranging from 72% to 99.7%, and a
    single confident answer hides that entirely.

    So this reports the SPREAD, never one value: every quantified statement found,
    with its document and page, the qualifiers attached to it (sample size,
    confidence interval, reference standard, population, setting, threshold), what
    is MISSING from each, sentences nearby that complicate the figure, and how old
    the evidence is. Deterministic — lexical retrieval and regex, no model, so it
    can miss an oddly-phrased figure but cannot invent one.

    Use it before answering any "what is the X of Y" question. Then use
    `check_for_newer_evidence` to find out whether the corpus is current.

    Args:
        question: The question as asked, e.g. "specificity of CATT in passive screening".
        layers: Comma-separated layer slugs to restrict to; omit to search all.
        show: How many individual findings to list (default 14).

    Returns:
        Per-metric spread, the individual estimates with provenance and
        qualifiers, the qualifier gaps, and the evidence date range.
    """
    want = [s.strip() for s in layers.split(",") if s.strip()] or None
    res = gather_quantities(question, want)
    f = res["findings"]

    if not f:
        return [TextContent(type="text", text=(
            f"**No quantified statement found** for `{question}`.\n\n"
            f"Searched {res['chunks_scanned']} chunk(s) for "
            f"{', '.join(res['families'])} figures"
            + (f" mentioning {', '.join(res['topic_terms'])}" if res["topic_terms"] else "")
            + ".\n\nThat absence is informative: the corpus does not carry a number "
            "for this. Answer from general knowledge and say so, or run "
            "`check_for_newer_evidence` to look outside."
        ))]

    by_metric: dict[str, list[dict]] = {}
    for x in f:
        by_metric.setdefault(x["metric"], []).append(x)

    # The metric NAMED in the question leads; everything else is related context.
    # A question about specificity that answers with sensitivity first has
    # technically retrieved the right passages and still failed to answer.
    asked = [m for m in by_metric if m in (question or "").lower()]
    def _rank(metric: str) -> tuple:
        return (0 if metric in asked else 1, -len(by_metric[metric]))

    out = [f"**Evidence on: {question}**", ""]
    if res["relaxed_match"]:
        out.append("⚠ No passage mentioned every term together, so this is a "
                   "broader match — check each estimate is about what you asked.\n")

    out.append("### The spread — not a single value")
    out.append("")
    out.append("| metric | n est. | min | median | max | span |")
    out.append("|---|---:|---:|---:|---:|---:|")
    for metric, items in sorted(by_metric.items(), key=lambda kv: _rank(kv[0])):
        s = _spread([i["value"] for i in items])
        flag = " ⚠" if s["range"] >= 10 else ""
        out.append(f"| {metric} | {s['n']} | {s['min']}% | {s['median']}% | "
                   f"{s['max']}% | {s['range']} pts{flag} |")

    others = [m for m in by_metric if m not in asked]
    if asked and others:
        out += ["", f"You asked about **{', '.join(asked)}**. The rest appear in the "
                    f"same passages and are shown because they change how the first "
                    f"should be read: {', '.join(others[:8])}."]

    wide = [m for m, i in by_metric.items()
            if _spread([x["value"] for x in i])["range"] >= 10]
    if wide:
        out += ["", f"⚠ **{', '.join(wide)}** span 10 points or more across sources. "
                    "That is usually not a contradiction — it is different tests, "
                    "populations or reference standards. Reporting one number here "
                    "would be a choice disguised as a fact."]

    years = [x["doc_year"] for x in f if x["doc_year"]]
    if years:
        out += ["", f"Evidence dates: **{min(years)}–{max(years)}** "
                    f"({len(set(years))} distinct year(s))."]

    out += ["", f"### Individual estimates ({min(show, len(f))} of {len(f)})", ""]
    for x in sorted(f, key=lambda i: (_rank(i["metric"]), -i["value"]))[:show]:
        out.append(f"**{x['metric']} = {x['value']}%** — {x['document'][:60]} "
                   f"p.{x['page']} `{x['layer']}`")
        out.append(f"> {x['sentence']}")
        if x["qualifiers"]:
            qs = "; ".join(f"{k}: {', '.join(v)[:70]}" for k, v in x["qualifiers"].items())
            out.append(f"  · qualifiers — {qs}")
        if x["missing"]:
            out.append(f"  · **not stated** — {', '.join(x['missing'])}")
        if x["caveat_signals"]:
            out.append(f"  · complicating language nearby — {', '.join(x['caveat_signals'])}")
        out.append("")

    # Qualifier debt across the whole set: which qualifier is missing most often.
    debt: dict[str, int] = {}
    for x in f:
        for k in x["missing"]:
            debt[k] = debt.get(k, 0) + 1
    out += ["### What the sources do not say", ""]
    for k, n in sorted(debt.items(), key=lambda kv: -kv[1]):
        out.append(f"- **{k}** absent in {n}/{len(f)} estimates")
    out += ["", "An unqualified estimate is not a better estimate. Two figures are "
                "only comparable when their reference standard and population are "
                "the same, so a missing qualifier is a missing precondition — not "
                "a detail."]
    return [TextContent(type="text", text="\n".join(out))]


# ---------------------------------------------------------------------------
# Is the corpus current? — the other half of fact-checking a quantity
# ---------------------------------------------------------------------------
# A spread computed from a library whose newest paper on the topic is from 2014
# is a spread from 2014. It may be perfectly correct and completely superseded,
# and nothing in the local corpus can tell you which — the corpus does not know
# what it does not contain.
#
# So recency is reported FIRST, from local data, before any network call. Then
# the search outside is a deliberate, narrow, asked-for step rather than a
# reflex. Local-first is not a slogan here: knowing how stale you are is itself
# a local computation, and it is the one that decides whether to go out at all.
#
# WHAT COMES BACK IS ATTRIBUTED, NEVER QUOTED
#   A search result is a title and a DOI. Nobody has read it. Presenting it
#   alongside corpus passages as though both were evidence would collapse the
#   distinction the whole verification layer exists to hold. It is labelled.
_TOPIC_STOP = {
    "what", "whats", "which", "when", "does", "the", "of", "in", "for", "and",
    "is", "are", "how", "much", "many", "about", "value", "values", "range",
    "evidence", "newer", "new", "recent", "latest", "any", "there", "on",
}


def _corpus_recency(question: str) -> dict:
    """Newest evidence the corpus holds on this topic, from local data only."""
    res = gather_quantities(question)
    years = [x["doc_year"] for x in res["findings"] if x["doc_year"]]
    docs = {x["document"] for x in res["findings"]}

    # `literature_metadata.year` is more reliable than a year scraped out of a
    # filename, so prefer it where the document is also a catalogued reference.
    meta_years: list[int] = []
    with connect(paths.db) as con:
        try:
            for d in list(docs)[:60]:
                toks = {w for w in re.findall(r"[a-z]{4,}", (d or "").lower())}
                if len(toks) < 2:
                    continue
                for row in con.execute(
                    "SELECT title, year FROM literature_metadata "
                    "WHERE COALESCE(year,'') <> '' LIMIT 4000"
                ):
                    mt = {w for w in re.findall(r"[a-z]{4,}", (row["title"] or "").lower())}
                    if mt and len(toks & mt) >= max(2, min(len(toks), len(mt)) // 2):
                        y = re.search(r"(19|20)\d{2}", str(row["year"]))
                        if y:
                            meta_years.append(int(y.group(0)))
                        break
        except Exception:
            pass

    allyears = sorted(set(years + meta_years))
    return {
        "estimates": len(res["findings"]),
        "documents": len(docs),
        "years": allyears,
        "newest": allyears[-1] if allyears else None,
        "oldest": allyears[0] if allyears else None,
    }


def _search_newer(question: str, since_year: int, limit: int = 8) -> dict:
    """PubMed + OpenAlex for work newer than the corpus. Metadata only."""
    terms = [w for w in re.findall(r"[a-z0-9][a-z0-9\-]{2,}", (question or "").lower())
             if w not in _TOPIC_STOP]
    query = " AND ".join(terms[:5]) if terms else (question or "")
    out: dict = {"query": query, "pubmed": [], "openalex": [], "errors": []}

    this_year = datetime.now().year
    reldate = max(365, (this_year - since_year + 1) * 365) if since_year else 1825

    try:
        from metis_mcp.tools.literature_monitor import (
            _pubmed_esearch, _pubmed_esummary, _openalex_search)
    except Exception as exc:
        out["errors"].append(f"search tools unavailable: {exc}")
        return out

    # FIELD NAMES ARE NOT GUESSABLE. The first version read `pub_date`, `date`,
    # `doi` and `journal` from the PubMed summaries and `year`/`journal` from
    # OpenAlex — none of which those helpers return, so every result printed its
    # year as "????" and the since-year filter never fired. Taken from the actual
    # helper bodies in literature_monitor.py: PubMed gives pmid/title/source/
    # authors/pubdate; OpenAlex gives title/doi/publication_date/primary_location.
    try:
        pmids = _pubmed_esearch(query, reldate=reldate, max_results=limit * 3)
        for s in (_pubmed_esummary(pmids) if pmids else []):
            y = re.search(r"(19|20)\d{2}", str(s.get("pubdate") or ""))
            yr = int(y.group(0)) if y else None
            if since_year and yr and yr <= since_year:
                continue
            out["pubmed"].append({
                "title": (s.get("title") or "")[:180], "year": yr,
                "pmid": s.get("pmid", ""), "doi": "",
                "journal": (s.get("source") or "")[:70],
            })
            if len(out["pubmed"]) >= limit:
                break
    except Exception as exc:
        out["errors"].append(f"PubMed: {type(exc).__name__}")

    try:
        frm = f"{(since_year or this_year - 5)}-01-01"
        # OpenAlex `search` is relevance-ranked, NOT boolean AND — passing
        # "a AND b AND c" returned papers on Taenia vaccines for a question about
        # HAT diagnostics. So ask broadly and filter LOCALLY on the title, which
        # is deterministic and inspectable.
        need = [w for w in terms[:5] if len(w) > 3]
        seen_doi: set[str] = set()
        for w in _openalex_search(" ".join(terms[:5]), from_date=frm,
                                  max_results=limit * 4) or []:
            title = (w.get("title") or "")
            low = title.lower()
            if need and sum(1 for x in need if x in low) < 2:
                continue                      # not actually about this topic
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            if doi and doi in seen_doi:
                continue                      # OpenAlex repeats records
            if doi:
                seen_doi.add(doi)
            y = re.search(r"(19|20)\d{2}", str(w.get("publication_date") or ""))
            yr = int(y.group(0)) if y else None
            if since_year and yr and yr < since_year:
                continue
            src = ((w.get("primary_location") or {}).get("source") or {})
            out["openalex"].append({
                "title": title[:180], "year": yr, "doi": doi,
                "journal": (src.get("display_name") or "")[:70],
            })
            if len(out["openalex"]) >= limit:
                break
    except Exception as exc:
        out["errors"].append(f"OpenAlex: {type(exc).__name__}")
    return out


@app.tool()
async def check_for_newer_evidence(
    question: str,
    search_online: bool = False,
    limit: int = 8,
) -> list[TextContent]:
    """How old is the corpus on this topic, and what has been published since?

    The second half of fact-checking a quantity. A spread computed from a library
    whose newest paper on the topic is from 2014 is a 2014 answer — possibly
    correct, possibly superseded, and the corpus cannot tell you which because it
    does not know what it lacks.

    Recency is computed LOCALLY first and reported whether or not you go online,
    because knowing how stale you are is what decides whether the search is worth
    making. Set `search_online=True` to query PubMed and OpenAlex for work newer
    than the corpus — metadata only, nothing of the researcher's is transmitted.

    Anything returned from a search is ATTRIBUTED, not quoted: a title and a DOI
    that nobody has read. Never present it beside a corpus passage as if the two
    were the same kind of evidence, and use `verify_doi` before citing one.

    Args:
        question: The question, e.g. "specificity of CATT in passive screening".
        search_online: Query PubMed + OpenAlex for newer work. Ask first.
        limit: Maximum results per source (default 8).

    Returns:
        The corpus date range for this topic and, if requested, newer candidate
        sources with their years and DOIs.
    """
    rec = _corpus_recency(question)
    out = [f"**Corpus recency — {question}**", ""]

    if not rec["estimates"]:
        out.append("No quantified statement on this topic in the corpus at all, so "
                   "there is no local baseline to be stale relative to.")
    else:
        span = (f"{rec['oldest']}–{rec['newest']}"
                if rec["oldest"] != rec["newest"] else str(rec["newest"]))
        out.append(f"{rec['estimates']} estimate(s) across {rec['documents']} "
                   f"document(s); evidence dated **{span}**.")
        if rec["newest"]:
            age = datetime.now().year - rec["newest"]
            out.append("")
            if age >= 5:
                out.append(f"⚠ The newest local evidence is **{age} years old**. For a "
                           "moving field that is a real risk of a superseded answer.")
            elif age >= 3:
                out.append(f"The newest local evidence is {age} years old — worth "
                           "checking for an update before relying on it.")
            else:
                out.append(f"The newest local evidence is {age} year(s) old.")

    if not search_online:
        out += ["", "_Not searched online._ Pass `search_online=True` to look for "
                    "newer work on PubMed and OpenAlex — ask the researcher first; Metis does "
                    "not reach the internet silently."]
        return [TextContent(type="text", text="\n".join(out))]

    since = rec["newest"] or (datetime.now().year - 5)
    found = _search_newer(question, since, limit)
    out += ["", f"### Published since {since}", "",
            f"Search: `{found['query']}`"]

    total = len(found["pubmed"]) + len(found["openalex"])
    if not total:
        out += ["", "Nothing newer found. That is weak evidence of currency, not "
                    "proof — a keyword search is not a systematic one."]
    else:
        for src in ("pubmed", "openalex"):
            if not found[src]:
                continue
            out += ["", f"**{src}** — {len(found[src])} item(s)"]
            for it in found[src]:
                ident = (f" · `{it['doi']}`" if it.get("doi")
                         else (f" · PMID {it['pmid']}" if it.get("pmid") else ""))
                out.append(f"- {it['year'] or 'year n/a'} — {it['title']}"
                           f"{(' · ' + it['journal']) if it.get('journal') else ''}{ident}")
        out += ["", "⚠ These are **attributed, not quoted** — a title and a DOI that "
                    "nobody has read. They do not update the spread until the paper "
                    "is read or indexed. Run `verify_doi` before citing one, and "
                    "`/background extend` to make one permanently quotable."]
    if found["errors"]:
        out += ["", "Search problems: " + "; ".join(found["errors"])]
    return [TextContent(type="text", text="\n".join(out))]
