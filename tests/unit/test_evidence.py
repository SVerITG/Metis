"""Tests for the evidence weigher.

The extractor's job is to report what the literature says about a quantity. Its
whole output is a SPREAD, so a single bad extraction does not merely add noise —
it moves the minimum or the maximum and misreports the range. On the first real
run against the corpus, four artifact classes dragged a genuine 59–100%
specificity range down to 0.33–100%.

So most of these tests pin the artifact classes, each one taken from a real
sentence in the researcher's corpus:

  · a DIFFERENCE in a metric          "the difference in specificity was -0.33%"
  · a PRECISION or a PREVALENCE       "estimate specificity at a precision of 0.5%"
  · a COMPARATIVE                     "specificity of the RDT was 4.3% lower"
  · a MANGLED DECIMAL                 "96?1%" (a typographic middle dot)
  · a NEIGHBOURING metric's number    "Sensitivity was 100%, whereas specificity…"
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"
if str(_MCP_SRC) not in sys.path:
    sys.path.insert(0, str(_MCP_SRC))

from metis_mcp.tools import evidence as E  # noqa: E402


# Sentences paraphrased from real corpus text, not copied source.
_PASSAGES = [
    # A clean, well-qualified estimate — must be found.
    ("Serological Field Evaluation", "/fix/field.pdf", 3,
     "Of 953 samples tested none turned out positive; equivalent to a specificity "
     "of 99.5% (95% CI 99.0-99.8) against trypanolysis in active screening."),
    # A second clean estimate at a different value — the spread.
    ("Prospective RDT Evaluation", "/fix/rdt.pdf", 7,
     "In this cohort the specificity of the assay was 72% in passive screening, "
     "n = 410 participants, using parasitological confirmation."),
    # ARTIFACT: a difference, not a specificity.
    ("Prospective RDT Evaluation", "/fix/rdt.pdf", 8,
     "While the difference in specificity was minimal in active screening "
     "(-0.33%), it was more pronounced in passive screening."),
    # ARTIFACT: a precision, and a prevalence.
    ("Serological Field Evaluation", "/fix/field.pdf", 2,
     "A sample of this size was required to estimate specificity at a precision "
     "of 0.5%."),
    # ARTIFACT: a comparative.
    ("Head To Head Comparison", "/fix/h2h.pdf", 5,
     "However, the specificity of the RDT was 4.3% lower than that of the "
     "reference assay at the same dilution."),
    # ARTIFACT: mangled decimal — the middle dot arrives as '?'.
    ("Review Of Serology", "/fix/review.pdf", 4,
     "Across studies specificity is estimated at 96?1% to 99?2% for this assay."),
    # ARTIFACT: the number belongs to the metric BEFORE it.
    ("Diagnostic Accuracy Study", "/fix/acc.pdf", 2,
     "Sensitivity was 100%, whereas specificity ranged from 96.1% in one country "
     "to 97.6% in another."),
]


@pytest.fixture()
def corpus(tmp_path, monkeypatch):
    db = tmp_path / "ev.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE knowledge_databases (id INTEGER PRIMARY KEY, "
                "slug TEXT, name TEXT)")
    con.execute("INSERT INTO knowledge_databases (id, slug, name) "
                "VALUES (1,'fixture','Fixture')")
    con.execute("""CREATE TABLE pdf_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, db_id INTEGER, source_file TEXT,
        domain TEXT, title TEXT, page_start INTEGER, page_end INTEGER,
        chunk_idx INTEGER, chunk_text TEXT, char_count INTEGER, created_at TEXT)""")
    for i, (title, src, page, text) in enumerate(_PASSAGES):
        con.execute(
            "INSERT INTO pdf_chunks (db_id, source_file, domain, title, page_start,"
            " page_end, chunk_idx, chunk_text, char_count, created_at) "
            "VALUES (1,?,'fixture',?,?,?,?,?,?, '2026-01-01')",
            (src, title, page, page, i, text, len(text)))
    con.execute("CREATE TABLE literature_metadata (id INTEGER PRIMARY KEY "
                "AUTOINCREMENT, title TEXT, year TEXT, doi TEXT)")
    con.commit()
    con.close()
    monkeypatch.setattr(E.paths, "db", db, raising=False)
    return db


def _spec_values(question="specificity of the assay"):
    res = E.gather_quantities(question)
    return sorted(x["value"] for x in res["findings"] if x["metric"] == "specificity")


# ── It finds the real estimates ──────────────────────────────────────────────
def test_finds_the_genuine_estimates(corpus):
    vals = _spec_values()
    assert 99.5 in vals
    assert 72.0 in vals


def test_reports_a_spread_not_one_value(corpus):
    vals = _spec_values()
    assert len(vals) >= 2
    assert max(vals) - min(vals) > 10          # a real, wide spread


# ── Artifact classes, each from a real corpus sentence ───────────────────────
def test_a_difference_is_not_a_specificity(corpus):
    """'the difference in specificity was -0.33%' is a gap, not a value."""
    assert 0.33 not in _spec_values()


def test_a_precision_is_not_a_specificity(corpus):
    """'estimate specificity at a precision of 0.5%' is a design parameter."""
    assert 0.5 not in _spec_values()


def test_a_comparative_is_not_a_specificity(corpus):
    """'specificity ... was 4.3% lower than' is a difference on the far side."""
    assert 4.3 not in _spec_values()


def test_a_mangled_decimal_does_not_yield_a_tiny_value(corpus):
    """'96?1%' must not be read as 1%. The dot arrives as '?' from PDF text."""
    vals = _spec_values()
    assert 1.0 not in vals
    assert all(v >= 50 for v in vals), vals


def test_a_neighbouring_metrics_number_is_not_stolen(corpus):
    """'Sensitivity was 100%, whereas specificity ranged from 96.1%'.

    The 100 belongs to sensitivity. Attributing it to specificity would push the
    reported maximum to 100% on the strength of a different metric.
    """
    res = E.gather_quantities("specificity")
    stolen = [x for x in res["findings"]
              if x["metric"] == "specificity" and x["value"] == 100.0
              and "Sensitivity was 100%" in x["sentence"]]
    assert not stolen


# ── Qualifiers: the "important related information" ─────────────────────────
def test_qualifiers_are_attached_when_present(corpus):
    res = E.gather_quantities("specificity of the assay")
    got = [x for x in res["findings"] if x["value"] == 99.5]
    assert got, "the 99.5% estimate should be found"
    q = got[0]["qualifiers"]
    assert "confidence interval" in q, q      # "(95% CI 99.0-99.8)"
    assert "sample size" in q, q              # "953 samples"
    assert "reference standard" in q, q       # "trypanolysis"
    assert "population" in q, q               # "active screening"


def test_missing_qualifiers_are_reported_as_missing(corpus):
    """And only genuinely missing ones — a false 'not stated' is the worst case."""
    res = E.gather_quantities("specificity of the assay")
    got = [x for x in res["findings"] if x["value"] == 99.5][0]
    assert "confidence interval" not in got["missing"]
    assert "sample size" not in got["missing"]


def test_confidence_interval_separator_variants_are_recognised():
    """The separator zoo that produced false 'CI not stated' verdicts."""
    pat = E._QUALIFIER_PATTERNS["confidence interval"]
    for s in ["(95% CI 99.0-99.8)", "[CI: 63.5%; 74.5%]",
              "a 95% confidence interval (CI) of 99.0% to 99.8",
              "95% CI 1.2–3.4", "[CI: 51.8%-63.7%]"]:
        assert pat.search(s), s


def test_complicating_language_is_surfaced(corpus):
    """'However' and 'lower than' near a figure are the caveats that get dropped."""
    res = E.gather_quantities("specificity")
    assert any(x["caveat_signals"] for x in res["findings"])


# ── Question interpretation ─────────────────────────────────────────────────
def test_metric_family_is_detected_from_the_question():
    assert "diagnostic accuracy" in E._metrics_in("what is the specificity of CATT")
    assert "burden" in E._metrics_in("what is the prevalence in Kwilu")
    assert E._metrics_in("how does passive screening work") == []


def test_topic_terms_drop_metric_and_stopwords():
    terms = E._topic_terms("what is the specificity of CATT in passive screening",
                           {"specificity"})
    assert "catt" in terms
    assert "specificity" not in terms
    assert "what" not in terms


def test_no_findings_is_reported_as_absence_not_as_zero(corpus):
    res = E.gather_quantities("hazard ratio for an entirely unrelated exposure")
    assert res["findings"] == []
