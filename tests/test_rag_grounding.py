"""
Automated RAG-grounding test — the one claim the whole system rests on.

The manual probe set lives in `tests/rag-pipeline-test.md` (run against a populated
library + an LLM). This file automates the *retrieval* core of that audit so it runs
in CI without an API key and without the user's real corpus:

  1. builds a tiny, self-contained vector index from KNOWN fixture passages
     (using the real schema, the real nomic embedder, and the real sqlite-vec table);
  2. asserts an in-corpus question retrieves the RIGHT document at rank 1, WITH its
     page provenance — i.e. the system can ground a claim (manual Q1–Q4);
  3. asserts a fabricated / out-of-corpus question produces a markedly WEAKER top
     match than a genuine one — the retrieval signal an LLM uses to refuse rather
     than hallucinate (manual Q7);
  4. asserts the empty-index guard and database scoping behave.

It exercises the real `search_pdf_knowledge` tool end to end (chunk → embed → vec0
ANN → provenance formatting). It is skipped only if the embedding stack
(fastembed + sqlite-vec) is unavailable, so it stays green wherever the knowledge
layer can actually run.
"""

import asyncio
import re
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent
_MCP_SRC = _REPO / "system" / "mcp-server" / "src"
if str(_MCP_SRC) not in sys.path:
    sys.path.insert(0, str(_MCP_SRC))

# Skip the whole module if the embedding / vector stack isn't installed.
_SKIP_REASON = None
try:
    import sqlite_vec  # noqa: F401
    from metis_mcp.embeddings import embed_document, embed_query
except Exception as exc:  # noqa: BLE001
    _SKIP_REASON = f"embedding/vector stack unavailable: {type(exc).__name__}: {exc}"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(_SKIP_REASON is not None, reason=_SKIP_REASON or ""),
]


# ── Fixture corpus — short, known passages with distinct topics ────────────────
# Each tuple: (title, page, domain, text). The text is paraphrased reference
# content, not copied source, so the file carries no third-party text.
_FIXTURE_DOCS = [
    (
        "gHAT Elimination Verification Criteria",
        21,
        "hat-specialist",
        "Verification of elimination of gambiense human African trypanosomiasis as a "
        "public health problem requires fewer than one reported case per ten thousand "
        "people per year, averaged over the previous five years, in each endemic health "
        "district, together with sustained passive and active case detection and a "
        "functioning post-validation surveillance system.",
    ),
    (
        "WHO NTD Roadmap 2021-2030",
        5,
        "ntd",
        "The neglected tropical disease road map sets a target to interrupt transmission "
        "of gambiense human African trypanosomiasis by 2030 and to reduce by ninety "
        "percent the number of people requiring interventions against neglected tropical "
        "diseases across the global elimination agenda.",
    ),
    (
        "Basic Epidemiology",
        110,
        "epi-methods",
        "Sensitivity is the proportion of true cases a test correctly identifies, while "
        "specificity is the proportion of non-cases correctly excluded. In a low-prevalence "
        "setting the positive predictive value of a screening test falls sharply even when "
        "specificity is high, which drives the diagnostic algorithm trade-off.",
    ),
]


def _build_index(conn) -> None:
    """Create the real knowledge schema on a temp DB and index the fixture corpus."""
    from metis_mcp.tools import knowledge_db as K

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_databases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT DEFAULT '',
            layer INTEGER DEFAULT 1, color TEXT DEFAULT '#6c757d',
            doc_count INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0,
            last_built TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS pdf_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, db_id INTEGER NOT NULL DEFAULT 0,
            source_file TEXT NOT NULL, domain TEXT DEFAULT '', title TEXT DEFAULT '',
            page_start INTEGER DEFAULT 0, page_end INTEGER DEFAULT 0,
            chunk_idx INTEGER NOT NULL, chunk_text TEXT NOT NULL,
            char_count INTEGER DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    # vec0 virtual table + extension load
    K._ensure_schema(conn)

    conn.execute(
        "INSERT INTO knowledge_databases (slug, name, description, layer) VALUES (?,?,?,?)",
        ("testkb", "Test KB", "hermetic fixture corpus", 4),
    )
    db_id = conn.execute(
        "SELECT id FROM knowledge_databases WHERE slug='testkb'"
    ).fetchone()[0]

    for idx, (title, page, domain, text) in enumerate(_FIXTURE_DOCS):
        cur = conn.execute(
            "INSERT INTO pdf_chunks (db_id, source_file, domain, title, page_start, "
            "chunk_idx, chunk_text, char_count) VALUES (?,?,?,?,?,?,?,?)",
            (db_id, f"{title}.pdf", domain, title, page, idx, text, len(text)),
        )
        rowid = cur.lastrowid
        vec = K._encode_vec(embed_document(text))  # real 768-dim passage embedding
        conn.execute(
            "INSERT INTO vec_pdf_chunks (rowid, embedding) VALUES (?,?)", (rowid, vec)
        )
    conn.commit()


@pytest.fixture(scope="module")
def rag_db(tmp_path_factory):
    """Point paths.db at a temp DB indexed with the fixture corpus (module-scoped:
    the embedding model loads once)."""
    from metis_mcp.config import paths

    db_path = tmp_path_factory.mktemp("rag") / "rag.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _build_index(conn)
    conn.close()

    _orig = paths.db
    paths.db = db_path
    yield db_path
    paths.db = _orig


def _search(query, databases=None, top_k=3):
    from metis_mcp.tools.knowledge_db import search_pdf_knowledge

    res = asyncio.run(search_pdf_knowledge(query, databases=databases, top_k=top_k))
    return res[0].text


def _top_score(text: str) -> float:
    m = re.search(r"score:\s*([0-9.]+)", text)
    return float(m.group(1)) if m else -1.0


def _best_distance(query: str) -> float:
    """Nearest vector distance for a query against the current paths.db corpus.

    This is the raw grounding signal (lower = closer match). We assert on this
    rather than the formatted 'score', because the tool's display score
    (max(0, 1 - L2_distance)) collapses to 0.0 for L2 distances >= 1.
    """
    from metis_mcp.config import paths
    from metis_mcp.tools import knowledge_db as K

    conn = sqlite3.connect(str(paths.db))
    import sqlite_vec

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    qv = K._encode_vec(embed_query(query))
    row = conn.execute(
        "SELECT min(distance) FROM vec_pdf_chunks WHERE embedding MATCH ? AND k = 3",
        (qv,),
    ).fetchone()
    conn.close()
    return float(row[0]) if row and row[0] is not None else 9999.0


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_in_corpus_query_retrieves_right_doc_with_provenance(rag_db):
    """A genuine question grounds: right document at rank 1, with page provenance."""
    text = _search(
        "What are the WHO criteria for verifying elimination of gambiense HAT as a "
        "public health problem, and what surveillance is required afterwards?",
        databases=["testkb"],
    )
    # rank-1 line is the elimination-criteria doc, not the roadmap or epi text
    first = text.split("**1.")[1].split("**2.")[0]
    assert "Elimination Verification Criteria" in first   # right doc at rank 1
    assert "p.21" in first                                # provenance is surfaced

def test_methods_query_routes_to_methods_doc(rag_db):
    """A distinct topic retrieves the distinct right doc (not the HAT/NTD chunks)."""
    text = _search(
        "How do sensitivity and specificity trade off, and why does positive predictive "
        "value fall in a low-prevalence screening setting?",
        databases=["testkb"],
    )
    first = text.split("**1.")[1].split("**2.")[0]
    assert "Basic Epidemiology" in first
    assert "p.110" in first

def test_roadmap_query_routes_to_roadmap_doc(rag_db):
    text = _search("What HAT and NTD targets does the WHO road map set for 2030?",
                   databases=["testkb"])
    first = text.split("**1.")[1].split("**2.")[0]
    assert "NTD Roadmap" in first

def test_fabricated_query_grounds_weakly(rag_db):
    """Hallucination signal (manual Q7): a fabricated protocol that is NOT in the
    corpus must produce a markedly weaker top match than a genuine question — the
    low-confidence signal an LLM uses to refuse rather than invent."""
    genuine_dist = _best_distance(
        "WHO criteria for verifying elimination of gambiense HAT as a public health problem"
    )
    fabricated_dist = _best_distance(
        "Summarise the WHO Fexinidazole-2 combination protocol for rhodesiense HAT 2025 "
        "dosing schedule and its recommended treatment duration"
    )
    # The invented protocol has no source in the corpus, so its nearest chunk is
    # measurably farther away than a genuine question's — the low-confidence signal
    # an LLM uses to refuse rather than fabricate.
    assert fabricated_dist > genuine_dist, (
        f"fabricated query (dist {fabricated_dist:.3f}) should be farther from the "
        f"corpus than genuine (dist {genuine_dist:.3f})"
    )

def test_empty_index_reports_no_chunks(tmp_path):
    """The guard path: an empty knowledge DB returns a clear 'nothing indexed' message,
    never a fabricated answer."""
    from metis_mcp.config import paths
    from metis_mcp.tools import knowledge_db as K

    db_path = tmp_path / "empty.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        "CREATE TABLE knowledge_databases (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "slug TEXT, name TEXT, description TEXT, layer INTEGER, color TEXT, "
        "doc_count INTEGER, chunk_count INTEGER, last_built TEXT, created_at TEXT);"
        "CREATE TABLE pdf_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, db_id INTEGER, "
        "source_file TEXT, domain TEXT, title TEXT, page_start INTEGER, page_end INTEGER, "
        "chunk_idx INTEGER, chunk_text TEXT, char_count INTEGER, created_at TEXT);"
    )
    K._ensure_schema(conn)
    conn.commit()
    conn.close()

    _orig = paths.db
    paths.db = db_path
    try:
        text = _search("anything at all")
        assert "No PDFs indexed" in text or "build_pdf_knowledge_db" in text
    finally:
        paths.db = _orig

def test_database_scoping_excludes_other_layers(rag_db):
    """Querying a non-existent database returns no fixture chunks (scoping holds)."""
    text = _search("elimination criteria", databases=["does-not-exist"])
    assert "No results" in text or "no results" in text.lower()
