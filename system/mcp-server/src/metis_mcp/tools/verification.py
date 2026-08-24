"""verification.py — check a claim against the corpus, deterministically.

WHY THIS EXISTS
    Metis tells every client: "Knowledge answers are cited from the researcher's
    own indexed library, never invented." That promise has two halves and, until
    now, only one had machinery behind it.

    RETRIEVAL was enforced. `.claude/hooks/user-prompt-submit.mjs` searches the
    corpus on every domain question, injects passages with page provenance, and
    says so plainly when it finds nothing.

    VERIFICATION was enforced nowhere. `constitution.md` carries the right rules —
    `no-hallucination`, `confidence-flag`, `cite-sources` — but `load_constitution()`
    prepends them as TEXT, and only for deep/chain runs. The Critic agent has to be
    remembered. Six agent prompts say "do not hallucinate". Nothing anywhere checked
    a citation after it was written.

    That is the same shape as every other defect this project keeps finding:
    a control that depends on being remembered is not a control. The live
    consequence is on record — the AI in Public Health course ships 16 lessons with
    the note "every citation is an unverified lead".

THE CONSTRAINT THAT SHAPES EVERYTHING HERE
    **The checker must be less fallible than the thing it checks.**

    This rules out the obvious design. An LLM-judge fact-checker hallucinates its
    own verdicts, and a hallucinated VERDICT is worse than a hallucinated CLAIM
    because it launders the claim into something that looks audited.

    So this module contains NO MODEL. Every check in it is a set membership test,
    a range comparison, or a substring match. It can be wrong about relevance; it
    cannot invent a result. Judgement — "does this passage actually SUPPORT the
    claim" — is Tier C and belongs to Critic, deliberately not here.

THE THREE TIERS
    A  local, deterministic, free      — this module. Does the document exist, does
                                         the page exist, do the claim's numbers and
                                         quoted strings appear on that page?
    B  external, deterministic, meta   — `verify_doi`. Does the DOI resolve, do
                                         author/year/title match, IS IT RETRACTED?
    C  entailment, judgement, invoked  — Critic. Not in this file, on purpose.

WHAT A VERDICT MEANS — and what it does not
    `supported` means every deterministic check passed: the page exists and the
    numbers are on it. It does NOT mean the passage supports the claim. Letting
    Tier A's success imply Tier C would recreate exactly the overclaim this whole
    layer exists to prevent, so the verdict vocabulary keeps them separate.
"""
from __future__ import annotations

import re
from datetime import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------
# Every check gets a row. Without this, a verification result exists for the
# length of one reply and then evaporates — which is why "which of my outputs
# rest on unverified citations?" was an archaeology problem rather than a query.
#
# Kept in step with `system/installer/schema.sql`. That file is the only
# mechanism that carries a schema change to the OTHER computer on its own
# (learned the hard way on 2026-08-24, when 15 columns never made the trip).
_DDL = """
CREATE TABLE IF NOT EXISTS citation_checks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    claim         TEXT NOT NULL,
    source_cited  TEXT DEFAULT '',
    page_cited    INTEGER,
    quote_cited   TEXT DEFAULT '',
    doi           TEXT DEFAULT '',
    tier          TEXT DEFAULT 'A',
    verdict       TEXT NOT NULL,
    detail        TEXT DEFAULT '',
    artifact_path TEXT DEFAULT '',
    session_id    TEXT DEFAULT '',
    checked_at    TEXT NOT NULL
)
"""
_DDL_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_citation_checks_verdict "
    "ON citation_checks(verdict, checked_at)",
    "CREATE INDEX IF NOT EXISTS idx_citation_checks_artifact "
    "ON citation_checks(artifact_path)",
)

# Verdicts, ordered worst → best. A caller deciding whether to block reads
# HARD_FAILURES; a caller deciding whether to annotate reads the rest.
HARD_FAILURES = ("page_out_of_range", "quote_absent", "numerals_absent")
SOFT_VERDICTS = ("source_not_indexed", "source_ambiguous", "no_checkable_content")
VERDICT_MEANING = {
    "supported":           "page exists and every checkable number/quote is on it",
    "numerals_absent":     "the cited page does not contain the claim's figures",
    "quote_absent":        "the quoted text is not on the cited page",
    "page_out_of_range":   "the document is indexed but has no such page",
    "source_not_indexed":  "not in the corpus — cannot be quoted, only attributed",
    "source_ambiguous":    "several indexed documents match that title",
    "no_checkable_content": "no figure or quotation to test deterministically",
}


def ensure_ledger(con) -> None:
    """Create the ledger and its indexes. Safe to call repeatedly."""
    con.execute(_DDL)
    for sql in _DDL_IDX:
        con.execute(sql)


# ---------------------------------------------------------------------------
# Normalisation — the part that decides whether the checker is any good
# ---------------------------------------------------------------------------
_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s.%-]")


def _norm(s: str) -> str:
    """Lowercase, collapse whitespace, drop punctuation that PDF extraction mangles.

    Deliberately keeps `.`, `%` and `-`: they carry meaning in "0.5%" and
    "TRS-984", and stripping them would make a numeric check pass on text that
    says something different.
    """
    return _WS.sub(" ", _PUNCT.sub(" ", (s or "").lower())).strip()


# Numbers as written in journals and as extracted from PDFs are not the same
# string: "10,000" / "10 000" / "10000" are one number with three spellings, and
# a naive substring test on the claim's spelling fails on a document that used
# another. So both sides are reduced to a canonical digit form before comparison.
_NUM = re.compile(r"\d[\d,.   ]*\d|\d")


def _canon_number(tok: str) -> str:
    """'10 000' / '10,000' -> '10000'; '0.5' stays '0.5'; '1.5%' -> '1.5'."""
    t = tok.replace(" ", "").replace(" ", "").replace(" ", "").replace(",", "")
    t = t.rstrip(".")
    if t.count(".") > 1:                      # '1.234.567' is a separator style
        t = t.replace(".", "")
    return t


def _significant_numbers(text: str) -> list[str]:
    """The numbers in a claim that are worth testing.

    A bare '1' or '5' appears on almost every page of almost every document, so
    checking it proves nothing and would make every verdict `supported`. Only
    figures with real discriminating power are tested: two or more digits, or a
    decimal point. This is why a verdict names WHICH numbers it checked — a
    check whose scope is invisible is indistinguishable from no check.
    """
    out, seen = [], set()
    for m in _NUM.finditer(text or ""):
        c = _canon_number(m.group(0))
        if not c or c in seen:
            continue
        digits = c.replace(".", "")
        if len(digits) < 2 and "." not in c:
            continue
        seen.add(c)
        out.append(c)
    return out


def _number_bag(text: str) -> set[str]:
    """Every number in a passage, canonicalised, for membership testing."""
    return {_canon_number(m.group(0)) for m in _NUM.finditer(text or "")}


# ---------------------------------------------------------------------------
# Source resolution
# ---------------------------------------------------------------------------
def _resolve_source(con, source: str) -> list[dict]:
    """Find indexed documents matching a cited title or filename.

    RANKED, not thresholded — and that distinction is the whole correctness of
    this function. The first version scored every candidate with one loose test
    ("share all but one token") and returned everything that passed. Given
    "WHO Global Report NTDs 2023" it also returned "WHO UHC Global Monitoring
    Report 2023": four shared tokens out of five, so it reported the citation as
    AMBIGUOUS and refused to check it.

    That is the false-positive failure this whole layer must avoid. A spurious
    "could not verify" trains the reader to ignore the report, which is worse
    than not checking at all — the same lesson as the permanently-wrong
    user-config warning found on 2026-08-24.

    So: match at three descending strengths and keep only the BEST tier that has
    any hits. A citation that matches one document exactly is not made ambiguous
    by a second document that merely shares vocabulary with it.

      3  exact — normalised title or filename stem equals the citation
      2  containment — one string contains the other
      1  subset — every meaningful token of the citation appears in the candidate

    Ambiguity is reported only when several DIFFERENT files tie at the best tier.
    """
    want = _norm(source)
    if not want:
        return []
    want_tokens = {t for t in want.split() if len(t) > 2}

    rows = con.execute(
        "SELECT k.slug AS layer, p.title, p.source_file, p.domain, "
        "       MIN(p.page_start) AS first_page, MAX(p.page_end) AS last_page, "
        "       COUNT(*) AS chunks "
        "FROM pdf_chunks p LEFT JOIN knowledge_databases k ON k.id = p.db_id "
        "GROUP BY p.title, p.source_file"
    ).fetchall()

    scored: list[tuple[int, dict]] = []
    for r in rows:
        stem = (r["source_file"] or "").rsplit("/", 1)[-1].rsplit(".", 1)[0]
        best = 0
        for c in (_norm(r["title"] or ""), _norm(stem)):
            if not c:
                continue
            if c == want:
                best = max(best, 3)
            elif want in c or c in want:
                best = max(best, 2)
            else:
                ctokens = {t for t in c.split() if len(t) > 2}
                if want_tokens and want_tokens <= ctokens:
                    best = max(best, 1)
        if best:
            scored.append((best, dict(r)))

    if not scored:
        return []
    top = max(s for s, _ in scored)
    return [d for s, d in scored if s == top]


def _chunks_on_page(con, source_file: str, page: int | None) -> list[dict]:
    """Chunks covering a page, or every chunk of the document when page is None."""
    if page is None:
        rows = con.execute(
            "SELECT page_start, page_end, chunk_text FROM pdf_chunks "
            "WHERE source_file = ? ORDER BY chunk_idx", (source_file,)
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT page_start, page_end, chunk_text FROM pdf_chunks "
            "WHERE source_file = ? AND page_start <= ? AND page_end >= ? "
            "ORDER BY chunk_idx", (source_file, page, page)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Tier A
# ---------------------------------------------------------------------------
def check_claim(
    claim: str,
    source: str = "",
    page: int | None = None,
    quote: str = "",
) -> dict:
    """Tier A: verify a claim against the indexed corpus. No model involved.

    Returns a dict with `verdict`, `detail`, and the evidence the verdict rests
    on — including which numbers were tested, so the scope of the check is always
    visible rather than implied.
    """
    result = {
        "claim": claim, "source": source, "page": page, "quote": quote,
        "tier": "A", "verdict": "no_checkable_content", "detail": "",
        "numbers_tested": [], "numbers_missing": [],
        "matched_document": None, "page_range": None, "layer": None,
    }
    if not (claim or "").strip():
        result["detail"] = "empty claim"
        return result

    with connect(paths.db) as con:
        if not source.strip():
            result["verdict"] = "source_not_indexed"
            result["detail"] = ("no source cited — the claim is unsourced and "
                                "cannot be verified locally")
            return result

        hits = _resolve_source(con, source)
        if not hits:
            result["verdict"] = "source_not_indexed"
            result["detail"] = (
                f"'{source[:80]}' matches no indexed document. It may still exist — "
                "this says only that Metis cannot quote it. Use verify_doi for "
                "external existence."
            )
            return result
        if len(hits) > 1:
            # Prefer an exact-ish title match before declaring ambiguity, so a
            # document indexed twice under one title does not defeat the check.
            files = {h["source_file"] for h in hits}
            if len(files) > 1:
                result["verdict"] = "source_ambiguous"
                result["detail"] = (
                    f"{len(files)} indexed documents match '{source[:60]}': "
                    + "; ".join(sorted(h["title"] or "?" for h in hits)[:4])
                )
                return result

        doc = hits[0]
        result["matched_document"] = doc["title"]
        result["layer"] = doc["layer"]
        result["page_range"] = [doc["first_page"], doc["last_page"]]

        chunks = _chunks_on_page(con, doc["source_file"], page)
        if page is not None and not chunks:
            result["verdict"] = "page_out_of_range"
            result["detail"] = (
                f"'{doc['title']}' is indexed at pp. {doc['first_page']}–"
                f"{doc['last_page']}; no chunk covers p.{page}"
            )
            return result

        haystack = " ".join(c["chunk_text"] or "" for c in chunks)

        # Quoted text is the strongest available check — verify it first.
        if quote.strip():
            if _norm(quote) not in _norm(haystack):
                result["verdict"] = "quote_absent"
                where = f"p.{page}" if page is not None else "anywhere in the document"
                result["detail"] = f"the quoted text does not appear at {where}"
                return result

        nums = _significant_numbers(claim)
        result["numbers_tested"] = nums
        if nums:
            bag = _number_bag(haystack)
            missing = [n for n in nums if n not in bag]
            result["numbers_missing"] = missing
            if missing:
                result["verdict"] = "numerals_absent"
                where = f"p.{page}" if page is not None else "the document"
                result["detail"] = (
                    f"{', '.join(missing)} not found on {where} "
                    f"(tested {len(nums)}: {', '.join(nums)})"
                )
                return result

        if not nums and not quote.strip():
            result["verdict"] = "no_checkable_content"
            result["detail"] = (
                "the source is indexed and the page exists, but the claim carries "
                "no figure or quotation to test. Existence of the page is NOT "
                "support for the claim — escalate to Critic for entailment."
            )
            return result

        result["verdict"] = "supported"
        bits = []
        if quote.strip():
            bits.append("quoted text present")
        if nums:
            bits.append(f"all {len(nums)} figures present ({', '.join(nums)})")
        where = f"p.{page}" if page is not None else "the document"
        result["detail"] = (
            f"{'; '.join(bits)} on {where} of '{doc['title']}'. "
            "Deterministic checks only — this is not a judgement that the passage "
            "supports the claim."
        )
        return result


def record_check(entry: dict, artifact_path: str = "", session_id: str = "") -> int:
    """Append one verdict to the ledger. Returns the row id."""
    with connect(paths.db) as con:
        ensure_ledger(con)
        cur = con.execute(
            "INSERT INTO citation_checks (claim, source_cited, page_cited, "
            "quote_cited, doi, tier, verdict, detail, artifact_path, session_id, "
            "checked_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                (entry.get("claim") or "")[:1200],
                (entry.get("source") or "")[:400],
                entry.get("page"),
                (entry.get("quote") or "")[:600],
                (entry.get("doi") or "")[:120],
                entry.get("tier") or "A",
                entry.get("verdict") or "unknown",
                (entry.get("detail") or "")[:800],
                artifact_path[:400],
                session_id[:80],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return int(cur.lastrowid or 0)


# ---------------------------------------------------------------------------
# Citation extraction — finding the checkable claims in a block of prose
# ---------------------------------------------------------------------------
# Deliberately conservative. A false positive here costs a spurious "unverified"
# warning, which trains the reader to ignore the whole layer — the exact failure
# mode of the permanently-wrong user-config check found on 2026-08-24. So these
# patterns match citations that state a source explicitly, and nothing cleverer.
_CITE_PATTERNS = (
    # "Title, p.21" / "Title (p. 21)" / "Title — p.21"
    re.compile(r"(?P<src>[A-Z][^.\n(]{6,90}?)\s*[—,(]?\s*p{1,2}\.\s?(?P<page>\d{1,4})\)?"),
    # "(Author 2023, p.4)"
    re.compile(r"\((?P<src>[A-Z][^)\n]{4,70}?\s(?:19|20)\d{2})\s*,\s*p{1,2}\.\s?(?P<page>\d{1,4})\)"),
)
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>,;)\]]+", re.I)
_QUOTE_RE = re.compile(r"[\"“]([^\"“”]{12,300})[\"”]")


# A citation carries numbers of its own — the page, and usually a year in the
# title — and those must never be tested as if they were claims. The first
# version window'd 320 characters back from the citation and tested everything
# numeric in it, which produced "57 not found on p.57" and pulled the figure from
# a NEIGHBOURING sentence into this citation's claim. A nonsense failure is worse
# than a missed one: it is the false positive that teaches you to ignore the tool.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"“])")


def _sentence_around(text: str, start: int, end: int) -> str:
    """The single sentence containing a span — not a fixed character window.

    Sentence bounds are what make a claim attributable to ITS citation. Two
    sentences each citing the same page make two different claims, and a window
    wide enough to hold both would test each against the other's figures.
    """
    left = text.rfind(". ", 0, start)
    left = 0 if left < 0 else left + 2
    for br in ("\n\n", "\n- ", "\n* "):
        b = text.rfind(br, 0, start)
        if b >= 0 and b + len(br) > left:
            left = b + len(br)
    m = re.search(r"[.!?](?:\s|$)", text[end:])
    right = end + (m.end() if m else 0) if m else min(len(text), end + 160)
    return text[left:right]


def extract_citations(text: str) -> list[dict]:
    """Pull checkable (source, page) pairs and DOIs out of prose.

    The claim attached to a citation is the SENTENCE it sits in, with the
    citation itself removed — so the page number and the year in the source
    title are never mistaken for figures the claim asserts.
    """
    found, seen = [], set()
    for pat in _CITE_PATTERNS:
        for m in pat.finditer(text or ""):
            src = _WS.sub(" ", m.group("src")).strip(" —,–-")
            page = int(m.group("page"))
            sentence = _sentence_around(text, m.start(), m.end())
            # Strip the citation's own text out of the claim. What remains is
            # what the sentence ASSERTS, which is the only thing worth testing.
            claim = _WS.sub(" ", sentence.replace(m.group(0), " ")).strip()
            key = (_norm(src), page, _norm(claim)[:120])
            if not src or key in seen:
                continue
            seen.add(key)
            q = _QUOTE_RE.search(sentence)
            found.append({
                "source": src, "page": page,
                "claim": claim,
                "quote": (q.group(1) if q else ""),
            })
    for m in _DOI_RE.finditer(text or ""):
        d = m.group(0).rstrip(".")
        if d.lower() in seen:
            continue
        seen.add(d.lower())
        found.append({
            "source": "", "page": None, "doi": d,
            "claim": _WS.sub(" ", _sentence_around(text, m.start(), m.end())).strip(),
            "quote": "",
        })
    return found


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------
@app.tool()
async def verify_claim(
    claim: str,
    source: str = "",
    page: int = 0,
    quote: str = "",
    record: bool = True,
) -> list[TextContent]:
    """Tier A — check a claim against the indexed corpus, deterministically.

    Verifies what can be verified WITHOUT a model: that the cited document is
    indexed, that the cited page exists, that the claim's figures appear on that
    page, and that any quoted string is actually present. It cannot hallucinate a
    verdict because it contains no model.

    A `supported` verdict means the deterministic checks passed. It does NOT mean
    the passage supports the claim — that is entailment (Tier C, Critic's job).
    For a source that is not in the corpus, use `verify_doi` to establish whether
    it exists at all.

    Args:
        claim: The sentence or statement being checked.
        source: Cited document title or filename, as written in the answer.
        page: Cited page number; 0 or omitted searches the whole document.
        quote: An exact quotation to locate, if the claim contains one.
        record: Append the verdict to the citation ledger (default True).

    Returns:
        The verdict, what was tested, and which figures (if any) were missing.
    """
    res = check_claim(claim, source, page or None, quote)
    if record:
        res["ledger_id"] = record_check(res)

    lines = [
        f"**{res['verdict']}** — {VERDICT_MEANING.get(res['verdict'], '')}",
        "",
        res["detail"],
    ]
    if res.get("matched_document"):
        lines.append(
            f"\nMatched: {res['matched_document']} "
            f"(layer `{res['layer']}`, pp. {res['page_range'][0]}–{res['page_range'][1]})"
        )
    if res["numbers_tested"]:
        lines.append(f"Figures tested: {', '.join(res['numbers_tested'])}")
    if res["numbers_missing"]:
        lines.append(f"Figures NOT on the page: {', '.join(res['numbers_missing'])}")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def verify_text_citations(
    text: str,
    artifact_path: str = "",
    record: bool = True,
) -> list[TextContent]:
    """Tier A — find every citation in a block of prose and check each one.

    Use this on a draft, a lesson, a report section, or anything about to be
    written to disk. Extraction is deliberately conservative: it matches
    citations that name a source and a page, plus bare DOIs. A false "unverified"
    warning is more corrosive than a missed one, because it trains the reader to
    ignore the report.

    Args:
        text: The prose to scan.
        artifact_path: File this text belongs to, recorded in the ledger so
            "which of my outputs rest on unverified citations?" is a query.
        record: Append each verdict to the citation ledger (default True).

    Returns:
        A per-citation verdict table and a summary count.
    """
    cites = extract_citations(text)
    if not cites:
        return [TextContent(type="text", text=(
            "No checkable citations found. This is not a clean bill of health: "
            "prose with no source-and-page citation has nothing Tier A can test."
        ))]

    rows, counts = [], {}
    for c in cites:
        if c.get("doi"):
            res = {**c, "tier": "B", "verdict": "doi_unchecked",
                   "detail": "DOI found; run verify_doi to resolve it",
                   "numbers_tested": [], "numbers_missing": []}
        else:
            res = check_claim(c["claim"], c["source"], c["page"], c.get("quote", ""))
        counts[res["verdict"]] = counts.get(res["verdict"], 0) + 1
        if record:
            record_check({**c, **res}, artifact_path=artifact_path)
        rows.append(res)

    hard = sum(counts.get(v, 0) for v in HARD_FAILURES)
    out = [
        f"**{len(rows)} citation(s) checked** · {hard} hard failure(s)",
        "",
        "| verdict | source | page | detail |",
        "|---|---|---|---|",
    ]
    for r in rows:
        src = (r.get("source") or r.get("doi") or "—")[:44]
        pg = r.get("page") or "—"
        out.append(f"| `{r['verdict']}` | {src} | {pg} | {(r.get('detail') or '')[:90]} |")
    out.append("")
    for v, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        out.append(f"- {n}× `{v}` — {VERDICT_MEANING.get(v, '')}")
    if hard:
        out.append(
            f"\n⚠ {hard} citation(s) point at a page that does not contain what "
            "was claimed. Those are fabrications, not disagreements."
        )
    return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def library_coverage() -> list[TextContent]:
    """What fraction of the library can Metis actually QUOTE?

    The honest denominator for every grounding claim. There are three states, not
    two: verified against text, known-but-unquotable (metadata only, no indexed
    full text), and genuinely absent. Without this number, "not found in your
    corpus" reads as "not in your literature" when it may only mean "not indexed"
    — and a verification rate reported against an unknown denominator is itself
    the kind of overclaim this whole layer exists to prevent.

    Returns:
        Per-layer document and chunk counts, plus the quotable fraction of the
        reference library.
    """
    with connect(paths.db) as con:
        layers = con.execute(
            "SELECT COALESCE(k.slug,'(unfiled)') AS layer, "
            "       COUNT(DISTINCT p.source_file) AS docs, COUNT(*) AS chunks "
            "FROM pdf_chunks p LEFT JOIN knowledge_databases k ON k.id = p.db_id "
            "GROUP BY 1 ORDER BY 3 DESC"
        ).fetchall()
        try:
            meta = con.execute("SELECT COUNT(*) FROM literature_metadata").fetchone()[0]
        except Exception:
            meta = 0
        try:
            quotable = con.execute(
                "SELECT COUNT(DISTINCT p.source_file) FROM pdf_chunks p "
                "JOIN knowledge_databases k ON k.id = p.db_id "
                "WHERE k.slug = 'my-library'"
            ).fetchone()[0]
        except Exception:
            quotable = 0

    total_docs = sum(r["docs"] for r in layers)
    total_chunks = sum(r["chunks"] for r in layers)
    pct = (100.0 * quotable / meta) if meta else 0.0

    out = [
        f"**{total_docs} documents · {total_chunks:,} chunks quotable across "
        f"{len(layers)} layer(s)**", "",
        "| layer | documents | chunks |", "|---|---:|---:|",
    ]
    for r in layers:
        out.append(f"| `{r['layer']}` | {r['docs']} | {r['chunks']:,} |")
    out += [
        "",
        f"Reference library: **{quotable} of {meta}** papers have indexed full text "
        f"— {pct:.0f}% quotable.",
        f"The other {max(0, meta - quotable)} are known but **not quotable**: Metis "
        "can name them and cannot cite a page in them.",
    ]
    return [TextContent(type="text", text="\n".join(out))]


@app.tool()
async def citation_debt(limit: int = 25, artifact: str = "") -> list[TextContent]:
    """Which outputs rest on citations that were never verified?

    Reads the ledger. This is the question the AI in Public Health course raised
    and nothing could answer — 16 lessons shipped with "every citation is an
    unverified lead" because verification results had nowhere to accumulate.

    Args:
        limit: Maximum rows to list (default 25).
        artifact: Restrict to one artifact path; omit for everything.

    Returns:
        Counts by verdict, and the worst offenders first.
    """
    with connect(paths.db) as con:
        ensure_ledger(con)
        where, params = "", []
        if artifact:
            where = "WHERE artifact_path LIKE ?"
            params = [f"%{artifact}%"]
        counts = con.execute(
            f"SELECT verdict, COUNT(*) n FROM citation_checks {where} "
            "GROUP BY verdict ORDER BY n DESC", params
        ).fetchall()
        if not counts:
            return [TextContent(type="text", text=(
                "The citation ledger is empty — nothing has been checked yet. "
                "Run `verify_text_citations` on an artifact, or "
                "`python3 tools/verify_citations.py <path>`."
            ))]
        order = ",".join("?" * len(HARD_FAILURES))
        worst = con.execute(
            f"SELECT verdict, source_cited, page_cited, detail, artifact_path, "
            f"checked_at FROM citation_checks {where} "
            f"{'AND' if where else 'WHERE'} verdict IN ({order}) "
            "ORDER BY checked_at DESC LIMIT ?",
            params + list(HARD_FAILURES) + [limit]
        ).fetchall()

    total = sum(r["n"] for r in counts)
    out = [f"**{total} check(s) on record**", ""]
    for r in counts:
        flag = " ⚠" if r["verdict"] in HARD_FAILURES else ""
        out.append(f"- {r['n']}× `{r['verdict']}`{flag} — "
                   f"{VERDICT_MEANING.get(r['verdict'], '')}")
    if worst:
        out += ["", f"### Hard failures ({len(worst)} shown)", ""]
        for r in worst:
            loc = f" p.{r['page_cited']}" if r["page_cited"] else ""
            art = f" — `{r['artifact_path']}`" if r["artifact_path"] else ""
            out.append(f"- **{r['verdict']}** · {r['source_cited'][:60]}{loc}{art}  \n"
                       f"  {(r['detail'] or '')[:160]}")
    else:
        out += ["", "No hard failures recorded."]
    return [TextContent(type="text", text="\n".join(out))]


# ---------------------------------------------------------------------------
# Tier B — external, deterministic, metadata only
# ---------------------------------------------------------------------------
# No new integrations: Crossref is already the reference resolver used by
# ref_miner.py and services/acquire.py. Reusing its conventions (same base URL,
# same User-Agent) keeps one identity for the project at the API's rate limiter.
#
# WHY THIS TIER EXISTS SEPARATELY FROM A
#   Tier A answers "is this on that page of a document I hold". Tier B answers a
#   different question — "does the cited work exist at all, and is it still
#   standing". Those fail independently: a paper can be perfectly real and
#   unindexed, or indexed and since retracted.
#
# RETRACTION IS THE PART NOTHING ELSE COVERED
#   Metis could not tell you a cited paper had been retracted. Crossref carries
#   it: a retraction is a separate record that points back at the original via
#   `relation.is-retraction-of`, and the original gains an `update-to` entry of
#   type `retraction`. Citing a retracted paper in a manuscript is a worse
#   failure than a wrong page number and it was completely invisible, so the
#   check is unconditional here rather than an option.
_CROSSREF = "https://api.crossref.org/works"
_UA = {"User-Agent": "MetisResearchCortex/1.0 (https://github.com/SVerITG/Metis)"}

# Crossref labels these under `update-to[].type`. Only `retraction` and
# `withdrawal` invalidate a citation; a correction or erratum is worth surfacing
# but does not mean "do not cite this".
_INVALIDATING = {"retraction", "withdrawal", "removal"}
_CAUTION = {"correction", "corrigendum", "erratum", "expression_of_concern",
            "expression of concern", "addendum"}

# Anchored at the start of the title: publishers prefix "RETRACTED: " / "WITHDRAWN: ".
# Anchoring matters — a methods paper titled "Detecting retracted citations in
# systematic reviews" must not be flagged as retracted itself.
_TITLE_RETRACTED = re.compile(
    r"^\s*[\[(]?\s*(retracted|withdrawn|retraction(?:\s+notice)?|removed)\b\s*[\])]?\s*[:.\-—]",
    re.I,
)


def _strip_doi(doi: str) -> str:
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").strip(), flags=re.I).rstrip(".")


def _crossref(doi: str) -> dict | None:
    """Fetch one Crossref record. Returns None if it does not resolve."""
    try:
        import urllib.parse
        import requests
        url = f"{_CROSSREF}/{urllib.parse.quote(_strip_doi(doi), safe='')}"
        r = requests.get(url, headers=_UA, timeout=15)
        if r.status_code == 200:
            return r.json().get("message", {})
    except Exception:
        return None
    return None


def _year_of(msg: dict) -> str:
    for key in ("published-print", "published-online", "issued", "created"):
        parts = (msg.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0])
    return ""


def _authors_of(msg: dict) -> list[str]:
    out = []
    for a in msg.get("author") or []:
        fam = (a.get("family") or "").strip()
        if fam:
            out.append(fam)
    return out


def check_doi(doi: str, expect_author: str = "", expect_year: str = "",
              expect_title: str = "") -> dict:
    """Tier B: does this DOI exist, is it what was cited, and is it retracted?"""
    res = {
        "doi": _strip_doi(doi), "tier": "B", "verdict": "doi_unresolved",
        "detail": "", "title": "", "year": "", "authors": [],
        "retracted": False, "flags": [],
    }
    if not res["doi"]:
        res["detail"] = "no DOI supplied"
        return res

    msg = _crossref(res["doi"])
    if msg is None:
        res["detail"] = (
            "Crossref returned no record for this DOI. Either it does not exist "
            "(a fabricated citation) or the network call failed — those are "
            "different, so treat this as UNKNOWN, not as proof of fabrication."
        )
        return res

    res["title"] = (msg.get("title") or [""])[0]
    res["year"] = _year_of(msg)
    res["authors"] = _authors_of(msg)

    # ── Retraction: FOUR independent signals, because Crossref is inconsistent ──
    #
    # Found while testing (2026-08-24): the single most famous retraction in
    # medicine — Wakefield et al., Lancet 1998, 10.1016/S0140-6736(97)11096-0 —
    # carries NO `update-to` entry at all. Elsevier marked it only by prefixing
    # the title with "RETRACTED:". Checking `update-to` alone therefore returned
    # `doi_resolved` for it: a false negative on the textbook case, which is the
    # worst possible place to have one.
    #
    # So every signal a publisher might use is checked, and any one is enough.
    # A false positive here costs a spurious warning the reader can dismiss in
    # seconds; a false negative silently blesses a retracted citation.
    for u in msg.get("update-to") or []:
        t = (u.get("type") or "").lower().replace("-", "_")
        if t in _INVALIDATING:
            res["retracted"] = True
            res["flags"].append(f"{t} ({u.get('DOI', '')})")
        elif t in _CAUTION:
            res["flags"].append(f"{t} ({u.get('DOI', '')})")

    # 2) The record IS the retraction notice.
    if (msg.get("type") or "").lower() in ("retraction", "withdrawal"):
        res["retracted"] = True
        res["flags"].append("this record IS a retraction notice")

    # 3) A relation pointing at the notice that retracted it.
    for rel_name, rels in (msg.get("relation") or {}).items():
        if "retract" in rel_name.lower() or "withdraw" in rel_name.lower():
            if "is-retraction-of" in rel_name.lower():
                res["retracted"] = True
                res["flags"].append("this record IS a retraction notice")
            else:
                res["retracted"] = True
                dois = [x.get("id", "") for x in (rels if isinstance(rels, list) else [rels])]
                res["flags"].append(f"{rel_name} ({', '.join(d for d in dois if d)})")

    # 4) The publisher's title prefix — the Wakefield case. Anchored to the START
    #    of the title so a paper legitimately *about* retractions is not flagged.
    if _TITLE_RETRACTED.match(res["title"] or ""):
        res["retracted"] = True
        res["flags"].append("title is marked retracted/withdrawn by the publisher")

    if res["retracted"]:
        res["verdict"] = "doi_retracted"
        res["detail"] = (
            f"RETRACTED — {'; '.join(res['flags'])}. The work exists but must not "
            "be cited as evidence."
        )
        return res

    # Does the record match what was cited?
    mism = []
    if expect_year and res["year"] and expect_year.strip() != res["year"]:
        mism.append(f"year cited {expect_year}, Crossref says {res['year']}")
    if expect_author and res["authors"]:
        want = _norm(expect_author).split()
        if want and not any(_norm(a) in want or _norm(a) == _norm(expect_author)
                            for a in res["authors"]):
            mism.append(f"author cited '{expect_author}', Crossref lists "
                        f"{', '.join(res['authors'][:3])}")
    if expect_title and res["title"]:
        a, b = _norm(expect_title), _norm(res["title"])
        if a not in b and b not in a:
            ta, tb = {t for t in a.split() if len(t) > 3}, {t for t in b.split() if len(t) > 3}
            if not ta or len(ta & tb) < max(2, len(ta) // 2):
                mism.append(f"title cited '{expect_title[:50]}', Crossref has "
                            f"'{res['title'][:50]}'")

    if mism:
        res["verdict"] = "doi_mismatch"
        res["detail"] = "; ".join(mism)
    else:
        res["verdict"] = "doi_resolved"
        res["detail"] = (
            f"'{res['title'][:90]}' ({res['year']}) — exists and matches. "
            "Existence is NOT support: Crossref confirms the paper is real, not "
            "that it says what the claim says."
        )
    if res["flags"]:
        res["detail"] += f" · flagged: {'; '.join(res['flags'])}"
    return res


VERDICT_MEANING.update({
    "doi_resolved":   "the DOI exists and matches what was cited",
    "doi_mismatch":   "the DOI exists but author/year/title differ from the citation",
    "doi_retracted":  "the work has been RETRACTED — do not cite as evidence",
    "doi_unresolved": "Crossref has no such record, or the lookup failed",
    "doi_unchecked":  "a DOI was found but not yet resolved",
})
HARD_FAILURES = HARD_FAILURES + ("doi_retracted", "doi_mismatch")


@app.tool()
async def verify_doi(doi: str, expect_author: str = "", expect_year: str = "",
                     expect_title: str = "", record: bool = True) -> list[TextContent]:
    """Tier B — does this DOI exist, match the citation, and is it RETRACTED?

    Catches the classic fabricated citation: plausible authors, plausible journal,
    no such paper. And the failure nothing in Metis could see before — citing a
    paper that has since been retracted, which is worse than a wrong page number
    because the claim looks perfectly sourced.

    Metadata only: a DOI goes out, bibliographic fields come back. Nothing of the
    researcher's leaves the machine, so this stays inside the local-first rule.

    A `doi_resolved` verdict means the paper is real, NOT that it supports the
    claim. That distinction is the whole point of tiering.

    Args:
        doi: The DOI as cited (a full https://doi.org/… URL is fine).
        expect_author: Surname as cited, to check against the record.
        expect_year: Year as cited.
        expect_title: Title as cited.
        record: Append the verdict to the citation ledger (default True).

    Returns:
        The verdict, the resolved record, and any retraction or correction flags.
    """
    res = check_doi(doi, expect_author, expect_year, expect_title)
    if record:
        record_check({"claim": expect_title or doi, "source": res.get("title", ""),
                      "doi": res["doi"], "tier": "B", "verdict": res["verdict"],
                      "detail": res["detail"]})
    lines = [f"**{res['verdict']}** — {VERDICT_MEANING.get(res['verdict'], '')}", "",
             res["detail"]]
    if res["title"]:
        lines.append(f"\nResolved: {res['title']}")
        lines.append(f"Authors: {', '.join(res['authors'][:6]) or '—'} · Year: {res['year'] or '—'}")
    if res["retracted"]:
        lines.append("\n⚠ **RETRACTED.** Remove this citation or cite it explicitly "
                     "as a retracted work.")
    return [TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# The denominator — citations that CANNOT be checked as written
# ---------------------------------------------------------------------------
# Added immediately after the first real run (2026-08-24). Checking the AI in
# Public Health course reported "18 citations checked, no hard failures" — and
# the course contains roughly 187 reference-shaped lines. So the report covered
# about a tenth of the bibliography and read like a clean bill of health.
#
# That is precisely the overclaim this layer exists to prevent, committed by the
# layer itself. A verification count without its denominator is not a weaker
# result, it is a misleading one.
#
# A reference with no DOI and no page pointer is not necessarily wrong — it is
# UNCHECKABLE AS WRITTEN. But one more deterministic thing can still be said
# about it: whether the cited work is in the library at all. That converts
# "unknown" into two useful states, and both are honest.
_REF_LINE = re.compile(
    r"^[\s\-*>|\d.]*"                       # list bullets, numbering, table pipes
    r"(?P<body>[A-Z][^|\n]{18,300}?"        # begins like an author or a title
    r"\b(?:19|20)\d{2}\b[^|\n]{0,120})$",   # and carries a year
    re.M,
)
_HAS_ID = re.compile(r"\b10\.\d{4,9}/|\bp{1,2}\.\s?\d|\bPMID\b|\barXiv\b", re.I)


def find_unverifiable_references(text: str) -> list[str]:
    """Reference-shaped lines that carry no DOI, page pointer, PMID or arXiv id."""
    out, seen = [], set()
    for m in _REF_LINE.finditer(text or ""):
        body = _WS.sub(" ", m.group("body")).strip(" .;,")
        if len(body) < 24 or _HAS_ID.search(body):
            continue
        # Prose sentences also carry years. A reference names a work: require a
        # comma or a title-case run, which ordinary sentences rarely both have.
        if "," not in body and not re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", body):
            continue
        k = _norm(body)[:80]
        if k in seen:
            continue
        seen.add(k)
        out.append(body)
    return out


def reference_in_library(reference: str) -> dict:
    """Is this cited work in the library at all? Deterministic title lookup.

    Not a verification of the claim — only of the work's presence. Three states,
    which is the point: quotable (indexed full text, so Tier A can check a page),
    known (metadata only, so it can be attributed but never quoted), or absent.
    """
    res = {"reference": reference, "verdict": "reference_absent", "detail": "",
           "matched": ""}
    words = [w for w in _norm(reference).split() if len(w) > 3]
    if len(words) < 3:
        res["verdict"] = "reference_untestable"
        res["detail"] = "too little text to match on"
        return res

    with connect(paths.db) as con:
        hits = _resolve_source(con, reference)
        if hits:
            res["verdict"] = "reference_quotable"
            res["matched"] = hits[0]["title"] or ""
            res["detail"] = f"indexed as '{res['matched'][:70]}' — a page can be checked"
            return res
        # Metadata-only: known, but no full text to quote.
        #
        # Token overlap, NOT an ordered LIKE. The same mistake was made twice in
        # this file and caught twice: a `LIKE '%paper only reference%'` needs
        # those words contiguous, and a real title ("A paper only in the
        # reference library") has other words between them. Both sides are also
        # routinely truncated, so a prefix match is no better.
        row = None
        try:
            probe = set(words)
            best = 0.0
            for r in con.execute(
                "SELECT title FROM literature_metadata WHERE COALESCE(title,'') <> ''"
            ):
                toks = {t for t in _norm(r["title"]).split() if len(t) > 3}
                if not toks:
                    continue
                shared = probe & toks
                if len(shared) < 2:
                    continue
                cover = len(shared) / min(len(probe), len(toks))
                if cover > best and cover >= 0.6:
                    best, row = cover, r
        except Exception:
            row = None
        if row:
            res["verdict"] = "reference_known_unquotable"
            res["matched"] = row["title"] or ""
            res["detail"] = ("in your reference library but with no indexed full "
                             "text — attributable, not quotable")
            return res
    res["detail"] = "not found in the corpus or the reference library"
    return res


VERDICT_MEANING.update({
    "reference_quotable":         "the cited work is indexed — a page can be checked",
    "reference_known_unquotable": "in your library, but no full text to quote",
    "reference_absent":           "not in the corpus or the reference library",
    "reference_untestable":       "too little text to match on",
})


# ---------------------------------------------------------------------------
# Provenance of the backgrounds — verify at ingest, trust at read
# ---------------------------------------------------------------------------
# Background Maker's instructions already require it: "every document in the
# layer must have a real, verifiable URL or DOI. If a source can't be verified,
# skip it." Nothing verified it, and — found 2026-08-24 — there was nowhere to
# record the answer either: `pdf_index_state` held title and filename and no
# identifier at all. A layer could not state where its own documents came from.
#
# WHY THIS MATTERS MORE THAN ANSWER-TIME CHECKING
#   A known-good corpus turns verification from a TRUTH problem into a
#   CONTAINMENT problem. If every document in a layer is a real document, the
#   only remaining question at answer time is whether the answer stayed inside
#   it — and that is Tier A, which is free. Provenance is the cheaper place to
#   spend the effort, and it is spent once per document rather than once per
#   claim.
#
# LOCAL FIRST, AS ALWAYS
#   766 of the reference library's 1,016 records already carry a DOI. Matching an
#   indexed document's title against that costs no network call, so the sweep
#   resolves most of the corpus offline and only reaches Crossref for the rest —
#   and only when explicitly asked.
def _library_doi_index(con) -> list[tuple[set[str], str]]:
    """(title token-set, DOI) for every reference-library record that has a DOI.

    Built once per sweep and matched in memory. An ordered `LIKE` on the first
    few words — the obvious approach, and the first one tried — resolved only 39
    of 550 documents, because BOTH sides are truncated and neither is canonical:
    `literature_metadata.title` is cut at ~60 characters by the Zotero import,
    and `pdf_index_state.title` is derived from a filename that was already
    shortened ("The Natural Progression Of Gambiense Sleeping"). Two truncations
    of the same title rarely share a prefix, but they share most of their words.
    """
    out = []
    try:
        rows = con.execute(
            "SELECT title, doi FROM literature_metadata "
            "WHERE COALESCE(doi,'') <> '' AND COALESCE(title,'') <> ''"
        ).fetchall()
    except Exception:
        return out
    for r in rows:
        toks = {t for t in _norm(r["title"]).split() if len(t) > 3}
        if len(toks) >= 2:
            out.append((toks, str(r["doi"])))
    return out


def _provenance_from_library(index, title: str, source_file: str) -> tuple[str, str]:
    """Match an indexed document to a library DOI by title token overlap.

    STRICT ON PURPOSE. A wrong DOI stamped onto a document is worse than no DOI:
    it makes an unverified provenance look verified, which is the exact class of
    failure this whole layer exists to remove. So a match needs three shared
    meaningful words AND to cover most of the shorter title, and any ambiguity
    (two library records matching equally well) is rejected rather than guessed.
    """
    stem = (source_file or "").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    probe = {t for t in _norm(f"{title} {stem}").split() if len(t) > 3}
    if len(probe) < 3:
        return "", ""

    best: list[tuple[float, str]] = []
    for toks, doi in index:
        shared = probe & toks
        if len(shared) < 3:
            continue
        cover = len(shared) / min(len(probe), len(toks))
        if cover >= 0.6:
            best.append((cover, doi))
    if not best:
        return "", ""
    best.sort(reverse=True)
    # Two different DOIs fitting equally well means we cannot tell them apart.
    if len(best) > 1 and best[1][0] >= best[0][0] - 0.01 and best[1][1] != best[0][1]:
        return "", ""
    return best[0][1], "verified"


@app.tool()
async def audit_background_provenance(
    layer: str = "",
    resolve_online: bool = False,
    limit: int = 400,
) -> list[TextContent]:
    """Where did the documents in the knowledge layers actually come from?

    Sweeps `pdf_index_state` and records a DOI for every indexed document it can
    identify, so a layer can state its own provenance. Matches against the local
    reference library first — that is free and covers most of the corpus — and
    only calls Crossref when `resolve_online` is set.

    This is the "verify at ingest, trust at read" half of the verification layer.
    A corpus of known-real documents makes answer-time checking a containment
    problem rather than a truth problem, and the cost is paid once per document
    instead of once per claim.

    Args:
        layer: Restrict to one layer slug (e.g. 'hat-specialist'); omit for all.
        resolve_online: Also query Crossref by title for documents the local
            library cannot identify. Metadata only; costs one request each.
        limit: Maximum documents to process in one pass (default 400).

    Returns:
        Per-layer provenance counts and what changed in this pass.
    """
    updated = verified = unresolved = 0
    with connect(paths.db) as con:
        where, params = "", []
        if layer:
            where = ("WHERE s.db_id IN (SELECT id FROM knowledge_databases "
                     "WHERE slug = ?)")
            params = [layer]
        rows = con.execute(
            "SELECT s.id, s.title, s.source_file, s.doi, s.provenance, "
            "       COALESCE(k.slug,'(unfiled)') AS layer "
            f"FROM pdf_index_state s "
            f"LEFT JOIN knowledge_databases k ON k.id = s.db_id {where} "
            "ORDER BY (COALESCE(s.provenance,'') <> '') , s.id LIMIT ?",
            tuple(params + [limit]),
        ).fetchall()

        now = datetime.now().isoformat(timespec="seconds")
        lib_index = _library_doi_index(con)
        for r in rows:
            if (r["provenance"] or ""):
                continue                      # already settled; leave it alone
            doi, verdict = _provenance_from_library(lib_index, r["title"],
                                                    r["source_file"])
            if not doi and resolve_online:
                try:
                    import requests
                    q = (r["title"] or "")[:180]
                    if q:
                        resp = requests.get(
                            _CROSSREF, headers=_UA, timeout=15,
                            params={"query.bibliographic": q, "rows": 1,
                                    "select": "DOI,title"},
                        )
                        if resp.status_code == 200:
                            items = (resp.json().get("message") or {}).get("items") or []
                            if items:
                                cand_title = (items[0].get("title") or [""])[0]
                                # Only accept a strong title agreement. A search
                                # API always returns SOMETHING; accepting the top
                                # hit unconditionally would stamp a wrong DOI onto
                                # a document, which is worse than no DOI at all.
                                a = {t for t in _norm(q).split() if len(t) > 3}
                                b = {t for t in _norm(cand_title).split() if len(t) > 3}
                                if a and b and len(a & b) >= max(3, len(a) // 2):
                                    doi, verdict = items[0].get("DOI", ""), "verified"
                except Exception:
                    pass
            if doi:
                con.execute(
                    "UPDATE pdf_index_state SET doi=?, provenance=?, "
                    "provenance_checked_at=? WHERE id=?",
                    (doi, verdict or "verified", now, r["id"]),
                )
                verified += 1
            else:
                con.execute(
                    "UPDATE pdf_index_state SET provenance='unresolved', "
                    "provenance_checked_at=? WHERE id=?", (now, r["id"]),
                )
                unresolved += 1
            updated += 1

        summary = con.execute(
            "SELECT COALESCE(k.slug,'(unfiled)') AS layer, "
            "       SUM(CASE WHEN s.provenance='verified' THEN 1 ELSE 0 END) AS ok, "
            "       SUM(CASE WHEN s.provenance='unresolved' THEN 1 ELSE 0 END) AS no, "
            "       SUM(CASE WHEN COALESCE(s.provenance,'')='' THEN 1 ELSE 0 END) AS unchecked, "
            "       COUNT(*) AS total "
            "FROM pdf_index_state s "
            "LEFT JOIN knowledge_databases k ON k.id = s.db_id "
            "GROUP BY 1 ORDER BY 5 DESC"
        ).fetchall()

    out = [
        f"**{updated} document(s) processed** — {verified} identified, "
        f"{unresolved} unresolved", "",
        "| layer | verified | unresolved | unchecked | total |",
        "|---|---:|---:|---:|---:|",
    ]
    for s in summary:
        out.append(f"| `{s['layer']}` | {s['ok']} | {s['no']} | "
                   f"{s['unchecked']} | {s['total']} |")
    out += [
        "",
        "`verified` — a DOI is on record, so the document is a real published work.",
        "`unresolved` — no identifier found. NOT a judgement that it is fake: many "
        "legitimate layer documents (WHO reports, own notes, meeting records) have "
        "no DOI. It means provenance cannot be asserted.",
    ]
    if not resolve_online and any(s["no"] for s in summary):
        out.append("\nRe-run with `resolve_online=True` to query Crossref by title "
                   "for the unresolved ones.")
    return [TextContent(type="text", text="\n".join(out))]
