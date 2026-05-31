"""PaperQA2 — semantic PDF search over the user's library.

Indexes PDFs from knowledge/library/ using PaperQA2 (paper-qa) with
Claude Haiku via LiteLLM. Persists the Docs index as a pickle between calls.

Tools exposed:
  index_library_pdfs(force_reindex, topic_filter, scope) — build/rebuild the PDF index
  ask_library(question, top_k, scope)                     — answer with citations

Scopes:
  "default"    → knowledge/library/ (all PDFs) — index saved as docs.pkl
  "ph_library" → knowledge/library/ph-background/ — index saved as docs_ph_library.pkl
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app
from metis_mcp.models import model_for


def _get_api_key() -> str:
    """Return ANTHROPIC_API_KEY from env or metis/system/.env fallback."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    env_file = paths.root / "system" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    os.environ["ANTHROPIC_API_KEY"] = key
                    return key
    return ""


def _pdf_is_readable(path: Path) -> bool:
    """Quick pre-check using pypdf strict=False to skip malformed PDFs."""
    try:
        from pypdf import PdfReader
        with open(path, "rb") as f:
            reader = PdfReader(f, strict=False)
            _ = len(reader.pages)
        return True
    except Exception:
        return False


_SCOPE_DIRS = {
    "default": ("knowledge", "library"),
    "ph_library": ("knowledge", "library", "ph-background"),
}

_SCOPE_INDEX_NAMES = {
    "default": "docs.pkl",
    "ph_library": "docs_ph_library.pkl",
}


def _library_dir(scope: str = "default") -> Path:
    parts = _SCOPE_DIRS.get(scope, _SCOPE_DIRS["default"])
    return paths.root.joinpath(*parts)


def _index_path_for_scope(scope: str = "default") -> Path:
    global _INDEX_PATH
    d = paths.root / "system" / "app" / "data" / "paperqa_index"
    d.mkdir(parents=True, exist_ok=True)
    name = _SCOPE_INDEX_NAMES.get(scope, f"docs_{scope}.pkl")
    return d / name


@app.tool()
async def index_library_pdfs(
    force_reindex: bool = False,
    topic_filter: str = "",
    scope: str = "default",
) -> list[TextContent]:
    """Build or rebuild a PaperQA2 index over the user's PDF library.

    Walks knowledge/library/ (all subdirectories), collects PDFs, and indexes
    them with PaperQA2 + Claude Haiku. The index is persisted so that
    ask_library() can query it without re-reading every PDF.

    Run once after adding new papers, or with force_reindex=True to rebuild.

    Args:
        force_reindex: Rebuild from scratch even if an index already exists.
        topic_filter: If given, only index PDFs whose parent folder name
                      contains this string (e.g. "NTD", "Epidemiology", "Methods").
        scope: Which library to index. "default" = knowledge/library/ (all PDFs).
               "ph_library" = knowledge/library/ph-background/ (public health background).
    """
    try:
        from paperqa import Docs, Settings
    except ImportError:
        return [TextContent(type="text", text="paper-qa not installed. Run: pip install paper-qa")]

    lib_dir = _library_dir(scope)
    if not lib_dir.exists():
        return [TextContent(type="text", text=f"Library directory not found: {lib_dir}")]

    idx = _index_path_for_scope(scope)
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

    api_key = _get_api_key()
    if not api_key:
        return [TextContent(type="text", text=(
            "ANTHROPIC_API_KEY not set. Add it to metis/system/.env as:\n"
            "  ANTHROPIC_API_KEY=sk-ant-..."
        ))]

    settings = Settings(
        llm=model_for("paperqa"),
        summary_llm=model_for("paperqa"),
    )

    docs = Docs()
    indexed, errors, skipped = 0, [], []

    for pdf in pdfs:
        if not _pdf_is_readable(pdf):
            skipped.append(pdf.name)
            continue
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
    if skipped:
        msg += f"\n\nSkipped {len(skipped)} unreadable PDFs: " + ", ".join(skipped[:5])
        if len(skipped) > 5:
            msg += f" … and {len(skipped) - 5} more."
    if errors:
        msg += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            msg += f"\n… and {len(errors) - 10} more."
    return [TextContent(type="text", text=msg)]


@app.tool()
async def ask_library(
    question: str,
    top_k: int = 5,
    scope: str = "default",
) -> list[TextContent]:
    """Answer a question using the user's indexed PDF library via PaperQA2.

    Searches the pre-built index (see index_library_pdfs()) and returns
    a synthesised answer with citations from the source papers.

    Args:
        question: Natural language question to answer from the library.
        top_k: Number of source passages to retrieve before synthesis (default 5).
        scope: Which index to query. "default" = full library. "ph_library" = PH background only.
               Build the index first with index_library_pdfs(scope=<scope>).
    """
    try:
        from paperqa import Docs, Settings
    except ImportError:
        return [TextContent(type="text", text="paper-qa not installed. Run: pip install paper-qa")]

    idx = _index_path_for_scope(scope)
    if not idx.exists():
        hint = f"index_library_pdfs(scope='{scope}')" if scope != "default" else "index_library_pdfs()"
        return [TextContent(type="text", text=(
            f"No index found for scope '{scope}'. Run {hint} first to build the PDF index."
        ))]

    api_key = _get_api_key()
    if not api_key:
        return [TextContent(type="text", text=(
            "ANTHROPIC_API_KEY not set. Add it to metis/system/.env as:\n"
            "  ANTHROPIC_API_KEY=sk-ant-..."
        ))]

    try:
        import pickle
        with open(idx, "rb") as f:
            docs: Docs = pickle.load(f)
    except Exception as exc:
        return [TextContent(type="text", text=f"Failed to load index: {exc}")]

    settings = Settings(
        llm=model_for("paperqa"),
        summary_llm=model_for("paperqa"),
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


_DEFAULT_EXTRACT_FIELDS = [
    "Population / setting studied",
    "Study design",
    "Sample size",
    "Primary outcome measured",
    "Key finding or effect size",
    "Stated limitations",
]


@app.tool()
async def extract_structured(
    topic: str,
    fields: str = "",
    scope: str = "default",
) -> list[TextContent]:
    """Extract a structured, cited evidence brief on a topic from the PDF library.

    Elicit-style structured extraction: runs a fixed question set over the indexed
    library (PaperQA2) and assembles a markdown table — one row per field, each
    answer carrying its citations. Useful for systematic-review scaffolding.

    Args:
        topic: The subject to extract on (e.g. "HAT passive screening sensitivity").
        fields: Optional comma-separated fields to extract. Default set covers
                population, design, sample size, outcome, finding, limitations.
        scope: Which index to query ("default" or "ph_library"). Build it first
               with index_library_pdfs().
    """
    try:
        from paperqa import Docs, Settings
    except ImportError:
        return [TextContent(type="text", text="paper-qa not installed. Run: pip install paper-qa")]

    idx = _index_path_for_scope(scope)
    if not idx.exists():
        hint = f"index_library_pdfs(scope='{scope}')" if scope != "default" else "index_library_pdfs()"
        return [TextContent(type="text", text=f"No index found for scope '{scope}'. Run {hint} first.")]

    api_key = _get_api_key()
    if not api_key:
        return [TextContent(type="text", text="ANTHROPIC_API_KEY not set. Add it to metis/system/.env.")]

    field_list = [f.strip() for f in fields.split(",") if f.strip()] or _DEFAULT_EXTRACT_FIELDS

    try:
        import pickle
        with open(idx, "rb") as f:
            docs: Docs = pickle.load(f)
    except Exception as exc:
        return [TextContent(type="text", text=f"Failed to load index: {exc}")]

    settings = Settings(llm=model_for("paperqa"), summary_llm=model_for("paperqa"))

    rows = []
    all_refs: set = set()
    for field in field_list:
        q = (f"Regarding '{topic}': what is the {field.lower()}? "
             f"Answer in one or two sentences. If the library does not say, reply 'Not reported'.")
        try:
            answer = await docs.aquery(q, settings=settings)
            ans = (getattr(answer, "answer", None) or "Not reported").strip()
            ans = " ".join(ans.split())  # collapse whitespace for table cell
            refs = getattr(answer, "references", None) or ""
            if refs:
                for line in refs.splitlines():
                    line = line.strip()
                    if line:
                        all_refs.add(line)
        except Exception as exc:
            ans = f"(query failed: {exc})"
        rows.append((field, ans[:400]))

    out = [f"## Structured extraction — {topic}", "",
           "| Field | Finding |", "|---|---|"]
    for field, ans in rows:
        out.append(f"| {field} | {ans.replace('|', '/')} |")
    if all_refs:
        out += ["", "**Sources:**"] + [f"- {r}" for r in sorted(all_refs)[:15]]
    return [TextContent(type="text", text="\n".join(out))]
