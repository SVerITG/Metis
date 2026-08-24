"""Tests for the citation checker.

A verification layer that is itself unverified would be the joke version of this
feature, so these tests exist to hold the two properties the design rests on:

  1. It CATCHES a fabrication — a real document, a real page, a number that is
     not on it.
  2. It does not cry wolf. Every false positive spends the reader's trust, and a
     checker nobody trusts is switched off. Most of these tests are therefore
     about what must NOT be flagged.

Tier A runs against a purpose-built fixture corpus rather than the researcher's real one,
so the assertions stay true as the real library grows. Tier B (Crossref) is not
exercised here — it needs the network — but the retraction TITLE test is, because
that is pure string logic and it is the signal that caught the Wakefield case.
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

from metis_mcp.tools import verification as V  # noqa: E402


# ── Fixture corpus ────────────────────────────────────────────────────────────
# Paraphrased content, not copied source, so this file carries no third-party text.
_DOCS = [
    # (title, source_file, page_start, page_end, text)
    ("Elimination Verification Criteria", "/fix/verify-crit.pdf", 21, 21,
     "Verification requires fewer than 1 case per 10 000 people per year, "
     "averaged over the preceding five years, in each endemic health district."),
    ("Elimination Verification Criteria", "/fix/verify-crit.pdf", 22, 22,
     "Reporting completeness of at least 85% is expected before a dossier "
     "is reviewed."),
    ("Regional Progress Summary", "/fix/regional.pdf", 57, 57,
     "The population requiring mass drug administration for lymphatic "
     "filariasis decreased by 10.4 million in 2021."),
]


@pytest.fixture()
def corpus(tmp_path, monkeypatch):
    """A tiny pdf_chunks database, wired in place of the real one."""
    db = tmp_path / "fixture.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("""CREATE TABLE knowledge_databases (
        id INTEGER PRIMARY KEY, slug TEXT, name TEXT)""")
    con.execute("INSERT INTO knowledge_databases (id, slug, name) "
                "VALUES (1, 'fixture', 'Fixture layer')")
    con.execute("""CREATE TABLE pdf_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, db_id INTEGER, source_file TEXT,
        domain TEXT, title TEXT, page_start INTEGER, page_end INTEGER,
        chunk_idx INTEGER, chunk_text TEXT, char_count INTEGER, created_at TEXT)""")
    for i, (title, src, p0, p1, text) in enumerate(_DOCS):
        con.execute(
            "INSERT INTO pdf_chunks (db_id, source_file, domain, title, "
            "page_start, page_end, chunk_idx, chunk_text, char_count, created_at) "
            "VALUES (1,?,'fixture',?,?,?,?,?,?, '2026-01-01')",
            (src, title, p0, p1, i, text, len(text)))
    con.execute("""CREATE TABLE literature_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, doi TEXT)""")
    con.execute("INSERT INTO literature_metadata (title, doi) "
                "VALUES ('A paper only in the reference library', '10.1000/xyz')")
    con.commit()
    con.close()
    monkeypatch.setattr(V.paths, "db", db, raising=False)
    return db


# ── Tier A: it must catch a fabrication ──────────────────────────────────────
def test_number_on_the_cited_page_is_supported(corpus):
    r = V.check_claim("fewer than 1 case per 10 000 people per year",
                      "Elimination Verification Criteria", 21)
    assert r["verdict"] == "supported"
    assert "10000" in r["numbers_tested"]


def test_fabricated_number_is_caught(corpus):
    """The core promise: real document, real page, number that is not on it."""
    r = V.check_claim("fewer than 1 case per 47 500 people per year",
                      "Elimination Verification Criteria", 21)
    assert r["verdict"] == "numerals_absent"
    assert "47500" in r["numbers_missing"]


def test_right_number_wrong_page_is_caught(corpus):
    """A figure that exists in the document but not where it was cited."""
    r = V.check_claim("completeness of at least 85%",
                      "Elimination Verification Criteria", 21)
    assert r["verdict"] == "numerals_absent"


def test_page_outside_the_document_is_caught(corpus):
    r = V.check_claim("some claim with 10 000 in it",
                      "Elimination Verification Criteria", 9000)
    assert r["verdict"] == "page_out_of_range"


def test_absent_quote_is_caught(corpus):
    r = V.check_claim("It says the following",
                      "Elimination Verification Criteria", 21,
                      quote="tsetse have been eradicated continent-wide")
    assert r["verdict"] == "quote_absent"


def test_present_quote_is_supported(corpus):
    r = V.check_claim("It says the following",
                      "Elimination Verification Criteria", 21,
                      quote="averaged over the preceding five years")
    assert r["verdict"] == "supported"


# ── Number spelling: the same figure written three ways ──────────────────────
@pytest.mark.parametrize("spelling", ["10 000", "10,000", "10000"])
def test_number_separators_do_not_matter(corpus, spelling):
    """A claim written '10,000' must match a document that printed '10 000'."""
    r = V.check_claim(f"fewer than 1 case per {spelling} people",
                      "Elimination Verification Criteria", 21)
    assert r["verdict"] == "supported"


# ── It must not cry wolf ─────────────────────────────────────────────────────
def test_source_not_in_corpus_is_not_called_a_failure(corpus):
    """Absent from the corpus is NOT evidence of fabrication."""
    r = V.check_claim("Prevalence was 34.2%", "Journal Of Nowhere 2029", 12)
    assert r["verdict"] == "source_not_indexed"
    assert r["verdict"] not in V.HARD_FAILURES


def test_claim_with_no_figures_is_not_called_supported(corpus):
    """An indexed page is not support. Refusing to say so is the point."""
    r = V.check_claim("This document discusses elimination in general terms",
                      "Elimination Verification Criteria", 21)
    assert r["verdict"] == "no_checkable_content"


def test_small_numbers_are_not_tested(corpus):
    """Single digits appear on every page; testing them would pass everything."""
    assert V._significant_numbers("about 5 of them") == []
    assert "10.4" in V._significant_numbers("a decrease of 10.4 million")


def test_similar_titles_do_not_make_a_citation_ambiguous(corpus):
    """Ranked resolution, not thresholded.

    The first implementation returned every candidate sharing all-but-one token,
    so 'WHO Global Report NTDs 2023' also matched 'WHO UHC Global Monitoring
    Report 2023' and the citation was reported ambiguous. A spurious "cannot
    verify" is the false positive that teaches you to ignore the tool.
    """
    r = V.check_claim("a decrease of 10.4 million", "Regional Progress Summary", 57)
    assert r["verdict"] == "supported"


# ── Extraction: one claim per sentence, and never the citation's own numbers ──
def test_two_sentences_citing_one_page_are_two_claims():
    text = ("The summary notes a decrease of 10.4 million people "
            "(Regional Progress Summary, p.57). A separate analysis found "
            "87.3 million cases (Regional Progress Summary, p.57).")
    cites = V.extract_citations(text)
    assert len(cites) == 2


def test_page_number_is_not_treated_as_a_claim_figure():
    """'57 not found on p.57' was a real, nonsensical finding. Never again."""
    text = "Uptake reached 10.4 million (Regional Progress Summary, p.57)."
    claim = V.extract_citations(text)[0]["claim"]
    nums = V._significant_numbers(claim)
    assert "10.4" in nums
    assert "57" not in nums


def test_dois_are_extracted():
    text = "See the trial report (doi:10.1016/S0140-6736(17)32758-7) for detail."
    dois = [c["doi"] for c in V.extract_citations(text) if c.get("doi")]
    assert any(d.startswith("10.1016/S0140-6736") for d in dois)


# ── Retraction by title prefix — the signal that caught Wakefield ────────────
@pytest.mark.parametrize("title", [
    "RETRACTED: Ileal-lymphoid-nodular hyperplasia and pervasive developmental disorder",
    "WITHDRAWN: A study of something",
    "Retraction Notice: A trial of an intervention",
])
def test_publisher_title_prefix_flags_retraction(title):
    assert V._TITLE_RETRACTED.match(title)


@pytest.mark.parametrize("title", [
    "Detecting retracted citations in systematic reviews",
    "Retractions in the biomedical literature: a bibliometric review",
    "Withdrawal symptoms after treatment cessation",
])
def test_papers_about_retraction_are_not_flagged(title):
    """Anchoring matters: a paper ABOUT retractions has not been retracted."""
    assert not V._TITLE_RETRACTED.match(title)


# ── The denominator ──────────────────────────────────────────────────────────
def test_references_without_an_identifier_are_reported_as_uncheckable():
    text = ("- Smith J, Jones A. Something about surveillance systems. "
            "Lancet Global Health, 2021.\n"
            "- Brown K. Another paper with a DOI. BMJ 2020. doi:10.1136/bmj.12345\n")
    refs = V.find_unverifiable_references(text)
    assert any("Smith" in r for r in refs)
    assert not any("10.1136" in r for r in refs)   # the one with an id is excluded


def test_reference_lookup_distinguishes_quotable_from_merely_known(corpus):
    known = V.reference_in_library("A paper only in the reference library")
    assert known["verdict"] == "reference_known_unquotable"
    quotable = V.reference_in_library("Elimination Verification Criteria")
    assert quotable["verdict"] == "reference_quotable"
    absent = V.reference_in_library("Some completely unrelated invented title here")
    assert absent["verdict"] == "reference_absent"


# ── The ledger ───────────────────────────────────────────────────────────────
def test_a_check_is_recorded(corpus):
    entry = V.check_claim("fewer than 1 case per 47 500 people",
                          "Elimination Verification Criteria", 21)
    rid = V.record_check(entry, artifact_path="tests/fixture.md")
    assert rid > 0
    con = sqlite3.connect(str(corpus))
    row = con.execute(
        "SELECT verdict, artifact_path FROM citation_checks WHERE id = ?", (rid,)
    ).fetchone()
    con.close()
    assert row[0] == "numerals_absent"
    assert row[1] == "tests/fixture.md"


def test_hard_failures_are_the_fabrication_verdicts():
    """The list a caller reads to decide whether to block."""
    for v in ("numerals_absent", "quote_absent", "page_out_of_range"):
        assert v in V.HARD_FAILURES
    # Not being in the corpus is not a fabrication.
    assert "source_not_indexed" not in V.HARD_FAILURES
    assert "no_checkable_content" not in V.HARD_FAILURES
