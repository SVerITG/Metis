"""PaperQA2 — semantic PDF search over Stan's library.

Indexes PDFs from knowledge/library/ using PaperQA2 (paper-qa) with
Claude Haiku via LiteLLM. Persists the Docs index as a pickle between calls.

Tools exposed:
  index_library_pdfs(force_reindex, topic_filter) — build/rebuild the PDF index
  ask_library(question, top_k)                     — answer with citations
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app

_INDEX_PATH: Path | None = None


def _index_path() -> Path:
    global _INDEX_PATH
    if _INDEX_PATH is None:
        d = paths.root / "system" / "app" / "data" / "paperqa_index"
        d.mkdir(parents=True, exist_ok=True)
        _INDEX_PATH = d / "docs.pkl"
    return _INDEX_PATH


def _library_dir() -> Path:
    return paths.root / "knowledge" / "library"


@app.tool()
async def index_library_pdfs(
    force_reindex: bool = False,
    topic_filter: str = "",
) -> list[TextContent]:
    """Build or rebuild a PaperQA2 index over Stan's PDF library.

    Walks knowledge/library/ (all subdirectories), collects PDFs, and indexes
    them with PaperQA2 + Claude Haiku. The index is persisted so that
    ask_library() can query it without re-reading every PDF.

    Run once after adding new papers, or with force_reindex=True to rebuild.

    Args:
        force_reindex: Rebuild from scratch even if an index already exists.
        topic_filter: If given, only index PDFs whose parent folder name
                      contains this string (e.g. "HAT", "NTD", "Epidemiology").
    """
    try:
        from paperqa import Docs, Settings
    except ImportError:
        return [TextContent(type="text", text="paper-qa not installed. Run: pip install paper-qa")]

    lib_dir = _library_dir()
    if not lib_dir.exists():
        return [TextContent(type="text", text=f"Library directory not found: {lib_dir}")]

    idx = _index_path()
    if idx.exists() and not force_reindex:
        import os as _os
        size_mb = _os.path.getsize(idx) / 1_048_576
        return [TextContent(type="text", text=(
            f"Index already exists ({size_mb:.1f} MB). "
            f"Call ask_library() to query it, or use force_reindex=True to rebuild."
        ))]

    pdfs = [
        p for p in lib_dir.rglob("*.pdf")
        if not topic_filter or topic_filter.lower() in p.parent.name.lower()
    ]
    if not pdfs:
        return [TextContent(type="text", text=f"No PDFs found in {lib_dir}.")]

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return [TextContent(type="text", text="ANTHROPIC_API_KEY not set — cannot call Claude Haiku for PaperQA.")]

    settings = Settings(
        llm="claude-haiku-4-5-20251001",
        summary_llm="claude-haiku-4-5-20251001",
    )

    docs = Docs()
    indexed, errors = 0, []

    for pdf in pdfs:
        try:
            await docs.aadd(str(pdf), settings=settings)
            indexed += 1
        except Exception as exc:
            errors.append(f"{pdf.name}: {exc}")

    try:
        import pickle
        with open(idx, "wb") as f:
            pickle.dump(docs, f)
    except Exception as exc:
        return [TextContent(type="text", text=f"Indexed {indexed} PDFs but failed to save index: {exc}")]

    msg = f"Indexed {indexed}/{len(pdfs)} PDFs. Index saved to {idx}."
    if errors:
        msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            msg += f"\n… and {len(errors) - 10} more."
    return [TextContent(type="text", text=msg)]


@app.tool()
async def ask_library(
    question: str,
    top_k: int = 5,
) -> list[TextContent]:
    """Answer a question using Stan's indexed PDF library via PaperQA2.

    Searches the pre-built index (see index_library_pdfs()) and returns
    a synthesised answer with citations from the source papers.

    Args:
        question: Natural language question to answer from the library.
        top_k: Number of source passages to retrieve before synthesis (default 5).
    """
    try:
        from paperqa import Docs, Settings
    except ImportError:
        return [TextContent(type="text", text="paper-qa not installed. Run: pip install paper-qa")]

    idx = _index_path()
    if not idx.exists():
        return [TextContent(type="text", text=(
            "No index found. Run index_library_pdfs() first to build the PDF index."
        ))]

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return [TextContent(type="text", text="ANTHROPIC_API_KEY not set.")]

    try:
        import pickle
        with open(idx, "rb") as f:
            docs: Docs = pickle.load(f)
    except Exception as exc:
        return [TextContent(type="text", text=f"Failed to load index: {exc}")]

    settings = Settings(
        llm="claude-haiku-4-5-20251001",
        summary_llm="claude-haiku-4-5-20251001",
    )

    try:
        answer = await docs.aquery(question, settings=settings)
    except Exception as exc:
        return [TextContent(type="text", text=f"Query failed: {exc}")]

    text = getattr(answer, "answer", None) or "No answer generated."
    refs = getattr(answer, "references", None) or ""

    output = f"**Answer:**\n{text}"
    if refs:
        output += f"\n\n**References:**\n{refs}"
    return [TextContent(type="text", text=output)]
