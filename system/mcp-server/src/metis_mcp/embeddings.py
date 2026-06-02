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


def _l2_normalize(vec: List[float]) -> List[float]:
    """Scale a vector to unit length so L2 distance maps cleanly to cosine
    similarity (cos = 1 - L2^2 / 2). nomic-embed outputs are NOT unit-length by
    default, which is why an unnormalized index makes the `1 - distance` score
    collapse to 0. Callers that compare with cosine semantics pass normalize=True."""
    import numpy as np

    arr = np.asarray(vec, dtype="float32")
    n = float(np.linalg.norm(arr))
    return arr.tolist() if n == 0.0 else (arr / n).tolist()


def embed(
    texts: List[str], prefix: str = "search_document: ", normalize: bool = False
) -> List[List[float]]:
    """Embed a list of texts and return list of float vectors (dim=768).

    Args:
        texts: List of text strings to embed.
        prefix: Task prefix prepended before embedding (nomic-embed-text-v1.5 style).
        normalize: L2-normalize each vector to unit length (default False, to keep
            existing callers and indexes unchanged). The knowledge layer passes True
            so index and query vectors are unit-length and cosine scoring is valid.
    """
    model = _get_model()
    prefixed = [prefix + t for t in texts]
    embeddings = list(model.embed(prefixed))
    out = [e.tolist() for e in embeddings]
    if normalize:
        out = [_l2_normalize(v) for v in out]
    return out


def embed_one(text: str, prefix: str = "search_document: ", normalize: bool = False) -> List[float]:
    """Embed a single text and return a float vector."""
    return embed([text], prefix=prefix, normalize=normalize)[0]


def embed_query(text: str, normalize: bool = False) -> List[float]:
    """Embed a query string using the query task prefix."""
    return embed_one(text, prefix="search_query: ", normalize=normalize)


def embed_document(text: str, normalize: bool = False) -> List[float]:
    """Embed a document string using the document task prefix."""
    return embed_one(text, prefix="search_document: ", normalize=normalize)
