"""Lazy-loaded embedding engine for Metis vector memory.

Uses fastembed (ONNX-based) to avoid PyTorch dependency.
Model: nomic-ai/nomic-embed-text-v1.5-Q — 768 dims, ~130MB, supports task prefixes.
Fallback: BAAI/bge-base-en-v1.5 — 768 dims, ~210MB.
Model files are cached in ~/.cache/fastembed/ on first use.

Corporate proxy note: fastembed checks HuggingFace for model updates on every
init. Behind a corporate proxy with a self-signed CA (e.g. ITG's pa-ca.itg.be),
this fails unless SSL_CERT_FILE points at the system CA bundle. The run.sh
launchers set this; _ensure_ssl_certs() is a safety net for any other entry point.

Task prefixes (nomic-embed-text-v1.5):
  "search_document: " — for stored content
  "search_query: "    — for queries
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

log = logging.getLogger("metis.embeddings")

_model = None
EMBEDDING_DIM = 768
MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5-Q"
_FALLBACK_MODEL = "BAAI/bge-base-en-v1.5"

_SYS_CA = "/etc/ssl/certs/ca-certificates.crt"


def _ensure_ssl_certs() -> None:
    """Point httpx/requests at the system CA bundle if not already set.

    On institutional networks (ITG) the proxy re-signs TLS traffic with a
    local root CA. Python's httpx uses certifi which doesn't include it.
    The run.sh launchers export SSL_CERT_FILE, but if someone imports this
    module from another entry point (tests, notebooks) this catches it.
    """
    if os.path.isfile(_SYS_CA):
        if not os.environ.get("SSL_CERT_FILE"):
            os.environ["SSL_CERT_FILE"] = _SYS_CA
        if not os.environ.get("REQUESTS_CA_BUNDLE"):
            os.environ["REQUESTS_CA_BUNDLE"] = _SYS_CA


# A PERSISTENT, EXPLICIT model cache.
#
# fastembed defaults to `$TMPDIR/fastembed_cache` — i.e. /tmp — which does not
# survive a reboot. Combined with `HF_HUB_OFFLINE=1`, which run.sh sets so the
# dashboard never phones home, that produced a failure with two faces and one
# cause (diagnosed 2026-08-21):
#
#   · the nightly `embedding_backfill` logged "0 embedded, 2238 failed" while
#     the same script run by hand from a shell worked perfectly, because a shell
#     has no HF_HUB_OFFLINE and could re-download into /tmp;
#   · semantic search over the HAT corpus failed inside the dashboard with
#     "Could not load any embedding model" while succeeding from the CLI.
#
# Both are the same thing: an offline process looking in a cache that a reboot
# had emptied. Pinning the cache somewhere durable, beside the database, fixes
# both and makes the offline guarantee actually hold.
MODEL_CACHE = Path.home() / ".local" / "share" / "metis" / "models"

# …but pinning ONE directory turned the fix into a second failure (diagnosed
# 2026-08-24). Metis runs on two computers whose code syncs over OneDrive while
# the model cache does NOT. So the *new* path arrived here in code while the
# 132 MB model stayed behind in the *old* cache, and with HF_HUB_OFFLINE=1 there
# was no way back: every embedding feature was dead on a machine that had a
# perfectly good copy of the model 30 cm away on the same disk.
#
# The lesson is that a cache location is not a constant, it is a search path.
# We look in every place a Metis install has ever put the model, use the first
# that loads, and only then give up. FASTEMBED_CACHE_PATH is honoured first so a
# user or launcher can always override.
def _cache_candidates() -> List[Path]:
    """Every directory a Metis install may have cached the model in, in order."""
    cands = []
    env = os.environ.get("FASTEMBED_CACHE_PATH", "").strip()
    if env:
        cands.append(Path(env))
    cands.append(MODEL_CACHE)                        # durable, beside the DB
    cands.append(Path.home() / ".cache" / "fastembed")  # fastembed/HF default
    seen, out = set(), []
    for c in cands:
        r = str(c)
        if r not in seen:
            seen.add(r)
            out.append(c)
    return out


def _get_model():
    """Return the singleton embedding model, loading it on first call.

    Tries each (model, cache-dir) pair and returns the first that loads, so a
    machine whose model sits in a legacy cache keeps working offline instead of
    failing with the model already on disk.
    """
    global _model
    if _model is None:
        _ensure_ssl_certs()
        try:
            MODEL_CACHE.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        from fastembed import TextEmbedding

        attempts: List[str] = []
        for model_name in (MODEL_NAME, _FALLBACK_MODEL):
            for cache in _cache_candidates():
                try:
                    _model = TextEmbedding(model_name=model_name,
                                           cache_dir=str(cache))
                except Exception as exc:
                    attempts.append(f"{model_name} @ {cache}: {exc}")
                    log.debug("Embedding load failed — %s", attempts[-1])
                    continue
                if cache != MODEL_CACHE:
                    log.warning(
                        "Embedding model loaded from %s, not the durable cache "
                        "%s. Copy it there (or run tools/warm_embedding_model.py) "
                        "so it survives a cache clear.", cache, MODEL_CACHE)
                return _model

        log.warning("Embedding models unavailable: %s", " | ".join(attempts))
        offline = os.environ.get("HF_HUB_OFFLINE", "")
        hint = (
            f"\n\nHF_HUB_OFFLINE={offline} and the model is in none of "
            f"{[str(c) for c in _cache_candidates()]}. Warm the cache once "
            f"with network access:\n"
            f"    python3 tools/warm_embedding_model.py"
        ) if offline else ""
        raise RuntimeError(
            "Could not load any embedding model. Tried:\n  "
            + "\n  ".join(attempts) + hint
        )
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
