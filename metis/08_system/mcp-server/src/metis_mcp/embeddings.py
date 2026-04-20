"""Lazy-loaded embedding engine for Metis vector memory.

Uses fastembed (ONNX-based) to avoid PyTorch dependency.
Model: BAAI/bge-small-en-v1.5 — 384 dims, ~23MB, fast CPU inference.
Model files are cached in ~/.cache/fastembed/ on first use.
"""

from __future__ import annotations

from typing import List

_model = None
EMBEDDING_DIM = 384
MODEL_NAME = "BAAI/bge-small-en-v1.5"


def _get_model():
    """Return the singleton embedding model, loading it on first call."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


def embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts and return list of float vectors (dim=384)."""
    model = _get_model()
    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


def embed_one(text: str) -> List[float]:
    """Embed a single text and return a float vector."""
    return embed([text])[0]
