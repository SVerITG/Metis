#!/usr/bin/env python3
"""warm_embedding_model.py — download the embedding model once, durably.

WHY
    Metis runs its dashboard with HF_HUB_OFFLINE=1 so it never phones home, and
    fastembed's default cache is $TMPDIR — which a reboot empties. Together those
    mean every embedding-dependent feature fails silently after a restart:
    semantic search over the corpus, cross-pollination, and the nightly
    embedding backfill (measured 2026-08-21: "0 embedded, 2238 failed" nightly,
    while the same script run by hand succeeded).

    This downloads the model into ~/.local/share/metis/models, beside the
    database, where it survives reboots and satisfies the offline mode.

RUN IT
    Once per machine, with network access. Safe to re-run.
"""
import os
import sys

# Explicitly ALLOW network for this one script — that is its whole purpose.
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "system", "mcp-server", "src"))

from metis_mcp.embeddings import MODEL_CACHE, MODEL_NAME, _ensure_ssl_certs

_ensure_ssl_certs()
MODEL_CACHE.mkdir(parents=True, exist_ok=True)
print(f"cache : {MODEL_CACHE}")
print(f"model : {MODEL_NAME}")
print("downloading (first run only — a few hundred MB)…")

from fastembed import TextEmbedding

m = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(MODEL_CACHE))
vec = list(m.embed(["trypanosome antigenic variation"]))[0]
files = sum(1 for _ in MODEL_CACHE.rglob("*") if _.is_file())
size = sum(f.stat().st_size for f in MODEL_CACHE.rglob("*") if f.is_file())
print(f"\n✓ model ready — {files} file(s), {size // (1024*1024)} MB")
print(f"✓ embedding dimension: {len(vec)}")
print("\nOffline processes (dashboard, scheduler) can now load it.")
