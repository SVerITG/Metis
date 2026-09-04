"""A short keyword is an acronym, not a stem.

WHY THIS TEST EXISTS
    The AI-in-health focus matched only the spelled-out "artificial
    intelligence". "AI" — overwhelmingly the commoner spelling — was not in the
    lens at all, because the word-START matching rule would have made it catch
    aid, AIDS, air and aim. Measured on 2026-09-04: the lens returned 23 of
    4,103 briefs, and another 21 said a standalone "AI" beside a health term and
    were dropped. Several were squarely on topic, so the surface was under-
    reporting its own subject by roughly half, silently.

    The fix matches a keyword of <= 3 characters as a whole word with an
    optional plural. These tests pin both halves: that "ai" now catches what it
    should, and that it still refuses the words it was excluded for.

THE REGRESSION THAT MATTERS
    'llm' was the only short keyword in existence when the rule landed. Under
    the old stem rule it matched "LLMs" for free; a naive whole-word rule would
    have broken exactly that. Hence the optional plural, and hence
    `test_llm_still_matches_its_plural`.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

SRC = (pathlib.Path(__file__).resolve().parents[2]
       / "system" / "mcp-server" / "src" / "metis_mcp" / "tools" / "focus.py")


def _lens():
    """Lift the matcher out of focus.py without importing the whole package.

    focus.py pulls in the MCP server's paths and DB helpers on import, which a
    unit test has no business needing to answer a question about a regex.
    """
    src = SRC.read_text(encoding="utf-8")
    ns: dict = {}
    exec("import re\n" + src[src.index("_SHORT_KW = 3"):src.index("def get_focus(")], ns)
    return ns["matches_lens"]


matches = _lens()

AI = [["ai"], ["health", "clinical", "patient", "disease", "hospital", "triage"]]
LLM = [["llm"], ["clinical", "triage", "notes", "extraction"]]


@pytest.mark.parametrize("text", [
    "AI triage in hospital",
    "AI-assisted diagnosis of disease",          # a hyphen is a word boundary
    "New AI, same clinical problem",             # trailing punctuation
    "Two AIs disagreed about the patient",       # the optional plural
    "ai models and patient care",                # lowercased source text
])
def test_ai_matches_the_common_spelling(text):
    assert matches(AI, text), text


@pytest.mark.parametrize("text", [
    "aid workers reach the clinic",
    "AIDS patients in care",
    "air quality and patient health",
    "aim to improve hospital triage",
    "the trial said patient outcomes improved",   # 'ai' inside 'said'
    "il avait des patients à l'hôpital",          # the French false positive
])
def test_ai_refuses_the_words_it_was_excluded_for(text):
    assert not matches(AI, text), text


@pytest.mark.parametrize("text", [
    "LLM performance in triage",
    "LLMs for clinical notes",        # the plural the old stem rule caught free
    "LLM-based extraction",
])
def test_llm_still_matches_its_plural(text):
    assert matches(LLM, text), text


def test_llm_does_not_match_a_longer_word():
    assert not matches(LLM, "the film LLMore had clinical notes")


def test_long_keywords_keep_stem_behaviour():
    """The generosity that makes 'epidemi' useful must survive untouched."""
    groups = [["epidemi"], ["ai"]]
    assert matches(groups, "AI in epidemiology")
    assert matches(groups, "AI and the epidemic")


def test_and_across_groups_still_holds():
    """A lens is a conjunction. One axis alone must not match."""
    assert not matches(AI, "AI beats humans at chess")        # no health term
    assert not matches(AI, "hospital triage improved")        # no AI term
