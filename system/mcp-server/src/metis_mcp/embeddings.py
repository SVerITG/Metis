"""Lazy-loaded embedding engine for Metis vector memory.

Uses fastembed (ONNX-based) to avoid PyTorch dependency.
Model: nomic-ai/nomic-embed-text-v1.5-Q — 768 dims, ~130MB, supports task prefixes.
Fallback: BAAI/bge-base-en-v1.5 — 768 dims, ~210MB.
Model files are cached in ~/.cache/fastembed/ on first use.

Task prefixes (nomic-embed-text-v1.5):
  "search_document: " — for stored content
  "search_query: "    — for queries
"""

from __future__ import annotations

from typing import List

_model = None
EMBEDDING_DIM = 768
MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5-Q"
_FALLBACK_MODEL = "BAAI/bge-base-en-v1.5"


def _get_model():
    """Return the singleton embedding model, loading it on first call."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        try:
            _model = TextEmbedding(model_name=MODEL_NAME)
        except Exception:
            _model = TextEmbedding(model_name=_FALLBACK_MODEL)
    return _model


def embed(texts: List[str], prefix: str = "search_document: ") -> List[List[float]]:
    """Embed a list of texts and return list of float vectors (dim=768).

    Args:
        texts: List of text strings to embed.
        prefix: Task prefix prepended before embedding (nomic-embed-text-v1.5 style).
    """
    model = _get_model()
    prefixed = [prefix + t for t in texts]
    embeddings = list(model.embed(prefixed))
    return [e.tolist() for e in embeddings]


def embed_one(text: str, prefix: str = "search_document: ") -> List[float]:
    """Embed a single text and return a float vector."""
    return embed([text], prefix=prefix)[0]


def embed_query(text: str) -> List[float]:
    """Embed a query string using the query task prefix."""
    return embed_one(text, prefix="search_query: ")


def embed_document(text: str) -> List[float]:
    """Embed a document string using the document task prefix."""
    return embed_one(text, prefix="search_document: ")
