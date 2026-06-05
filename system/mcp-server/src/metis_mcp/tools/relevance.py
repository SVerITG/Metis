"""Semantic relevance — rank scanned items by closeness to the user's ACTUAL corpus.

The legacy relevance (content_scan._score_signal) was keyword-only against ~6
configured topic strings and ignored the user's library, projects, ideas and
meetings — which is why scans felt "not close to my work". This builds one
"interest profile" centroid from the user's real corpus (local nomic embeddings,
no API, no cost) and scores each new item by cosine similarity, so *close to what
you actually work on* beats *contains a keyword*.

Fails safe: if embeddings are unavailable the caller keeps its keyword score.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from metis_mcp.config import paths

_CACHE = paths.db.parent / "interest_centroid.json"
_TTL = 86400  # rebuild the profile at most once per day


def _corpus_texts(con: sqlite3.Connection) -> tuple[list[str], list[str]]:
    """Return (topic_texts, corpus_texts).

    topic_texts = the user's EXPLICIT stated research focus (configured topics /
    field / methods). corpus_texts = the accumulated body of work (library,
    projects, ideas, meetings). We deliberately EXCLUDE semantic_memory — it is
    polluted with Metis-engineering concepts from build/audit sessions, which
    otherwise pull unrelated AI/CS papers up the ranking.
    """
    topic_texts: list[str] = []
    try:
        import yaml
        cfg = yaml.safe_load((paths.config / "user-config.yaml").read_text(encoding="utf-8")) or {}
        research = cfg.get("research", {}) if isinstance(cfg.get("research"), dict) else {}
        for t in (research.get("topics") or []):
            if str(t).strip():
                topic_texts.append(str(t).strip())
        for k in ("field", "methods"):
            if research.get(k):
                topic_texts.append(str(research[k]))
    except Exception:
        pass

    corpus_texts: list[str] = []
    try:
        for row in con.execute(
            "SELECT title, COALESCE(tags,'') FROM literature_metadata ORDER BY id DESC LIMIT 400"
        ):
            s = " ".join(str(x) for x in row if x).strip()
            if s:
                corpus_texts.append(s)
    except Exception:
        pass
    for sql in (
        "SELECT title || ' ' || COALESCE(domain,'') || ' ' || COALESCE(next_step,'') FROM projects",
        "SELECT text FROM ideas ORDER BY created_at DESC LIMIT 50",
        "SELECT title FROM meetings ORDER BY meeting_date DESC LIMIT 50",
    ):
        try:
            for (s,) in con.execute(sql):
                if s and str(s).strip():
                    corpus_texts.append(str(s).strip())
        except Exception:
            pass

    def _dedup(xs):
        seen, out = set(), []
        for t in xs:
            t = t[:300]
            if t and t not in seen:
                seen.add(t); out.append(t)
        return out

    return _dedup(topic_texts), _dedup(corpus_texts)


def build_centroid(con: sqlite3.Connection, force: bool = False) -> list[float] | None:
    """Return the cached interest-profile centroid, rebuilding if stale/missing.

    The profile is a blend that anchors on the user's STATED focus so a broad
    library can't drown it out: ``normalize(0.5·topic_centroid + 0.5·corpus_centroid)``.
    Returns None if there is no corpus or embeddings are unavailable.
    """
    if not force:
        try:
            if _CACHE.exists() and (time.time() - _CACHE.stat().st_mtime) < _TTL:
                return json.loads(_CACHE.read_text())["centroid"]
        except Exception:
            pass

    topic_texts, corpus_texts = _corpus_texts(con)
    if not topic_texts and not corpus_texts:
        return None
    try:
        from metis_mcp.embeddings import embed
        import numpy as np

        def _centroid(texts):
            if not texts:
                return None
            v = np.array(embed(texts, prefix="search_document: ", normalize=True)).mean(axis=0)
            n = np.linalg.norm(v)
            return v / n if n else v

        tc = _centroid(topic_texts)
        cc = _centroid(corpus_texts)
        if tc is not None and cc is not None:
            blended = 0.5 * tc + 0.5 * cc            # equal weight: stated focus anchors the corpus
        else:
            blended = tc if tc is not None else cc
        n = np.linalg.norm(blended)
        centroid = (blended / n).tolist() if n else blended.tolist()
        try:
            _CACHE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE.write_text(json.dumps(
                {"centroid": centroid, "n_topic": len(topic_texts),
                 "n_corpus": len(corpus_texts), "built": time.time()}))
        except Exception:
            pass
        return centroid
    except Exception:
        return None


def score_batch(texts: list[str], centroid: list[float] | None) -> list[float]:
    """Cosine similarity of each text to the interest centroid. 0.0 per item on failure."""
    if not centroid or not texts:
        return [0.0] * len(texts)
    try:
        from metis_mcp.embeddings import embed
        import numpy as np
        v = np.array(embed([t[:500] for t in texts], prefix="search_query: ", normalize=True))
        sims = v @ np.array(centroid)
        return [float(x) for x in sims]
    except Exception:
        return [0.0] * len(texts)
