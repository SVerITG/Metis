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
import logging
import sqlite3
import time
from pathlib import Path

from metis_mcp.config import paths

_CACHE = paths.db.parent / "interest_centroid.json"
_TTL = 86400  # rebuild the profile at most once per day


# ── BANDS ────────────────────────────────────────────────────────────────────
# What each anchor's best match is worth. A hit on the reader's OWN work is the
# only thing worth its full similarity; everything else is discounted, and the
# discount is the statement of how close "close to my work" should mean.
#
# NO SUBJECT NAMES LIVE HERE, deliberately. The first version of this carried
# two lists of phrases naming one researcher's specialty — which compiled a
# single person's field into a general-purpose tool that ships publicly, and
# handed anyone else who installed it an interest profile tilted towards a
# subject they may not work on. The weighting is a mechanism and belongs in the
# code; which subjects get which weight is data and lives in `user_topics.band`.
#
# 'field'  — a standing subject, counting almost as much as an active project.
# 'method' — worth surfacing occasionally: a strong paper can win a slot, but it
#            has to beat the reader's own work by a margin rather than tie.
BAND_WEIGHTS = {
    "project": 1.00,   # what is actually being worked on
    "course":  1.00,   # what is actually being studied
    "field":   0.95,   # a standing subject, declared by the reader
    "topic":   0.88,   # stated interests — theirs, but broad by nature
    "idea":    0.80,   # ideas and notes: live thinking, noisier
    "method":  0.72,   # declared as occasional
    "task":    0.62,   # tasks and meetings: the most tooling-polluted band
}

# Which values of `user_topics.band` map to a weighted band of their own.
# Anything else — including the empty default — is an ordinary stated topic.
_TOPIC_BANDS = ("field", "method")


def _corpus_texts(con: sqlite3.Connection) -> tuple[list[str], list[str], list[str]]:
    """Return (topic_texts, work_texts, library_texts).

    THREE bands, not two, and the split is the whole point. The researcher, 2026-08-31:
    "It should be close to things and topics in my projects, ideas and notes."

    topic_texts   the EXPLICIT stated focus (configured topics / field / methods)
    work_texts    what he is ACTUALLY DOING — projects, ideas, notes, meetings
    library_texts what he has COLLECTED — 400 literature titles

    These were previously one bucket, averaged together, and that is why results
    felt off: 400 library titles against ~16 projects means the library decides
    the centroid by weight of numbers alone. His library is broad public-health
    material — WHO reports, epidemiology textbooks, methods papers — so the
    profile drifted toward "public health in general" and happily scored a paper
    on spiritual-care teaching as close to his work.

    Notes were missing entirely, which is why a note recording a live line of
    thinking could never influence the ranking.

    semantic_memory stays EXCLUDED: it is full of Metis-engineering concepts
    from build sessions and pulls unrelated AI/CS papers up the ranking.
    """
    # ── STATED FOCUS, from the DATABASE first ─────────────────────────────
    # This band was silently EMPTY. It read `paths.config / "user-config.yaml"`,
    # and paths.config resolves inside the venv
    # (~/.local/share/metis-mcp/.venv/system/config) where no such file exists —
    # so the read raised, the bare `except` swallowed it, and the profile has
    # never had the anchor it was designed around. Nothing failed loudly; the
    # ranking was simply library-dominated for as long as this has existed.
    #
    # `user_topics` is the live, authoritative source — it is what the scheduler
    # already queries, it carries a description as well as a name, and the
    # researcher edits it through Metis rather than by hand. The yaml is kept as
    # a fallback and now read from the repo, not from inside the venv.
    topic_texts: list[str] = []
    try:
        for topic, desc in con.execute(
            "SELECT topic, COALESCE(description,'') FROM user_topics WHERE active = 1"
        ):
            if topic and str(topic).strip():
                topic_texts.append(" ".join(x for x in (str(topic), str(desc)) if x).strip())
    except Exception:
        pass

    if not topic_texts:
        try:
            import yaml
            for base in (Path(__file__).resolve().parents[4] / "system" / "config",
                         paths.config):
                f = base / "user-config.yaml"
                if not f.exists():
                    continue
                cfg = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
                research = cfg.get("research", {}) if isinstance(cfg.get("research"), dict) else {}
                for t in (research.get("topics") or []):
                    if str(t).strip():
                        topic_texts.append(str(t).strip())
                for k in ("field", "methods"):
                    if research.get(k):
                        topic_texts.append(str(research[k]))
                break
        except Exception:
            pass

    library_texts: list[str] = []
    try:
        for row in con.execute(
            "SELECT title, COALESCE(tags,'') FROM literature_metadata ORDER BY id DESC LIMIT 400"
        ):
            t = " ".join(str(x) for x in row if x).strip()
            if t:
                library_texts.append(t)
    except Exception:
        pass

    # What he is actually working on. Projects carry their description and next
    # step as well as their title, because the next step is the most current
    # sentence about a project that exists anywhere.
    work_texts: list[str] = []
    for sql in (
        # TOOLING PROJECTS ARE EXCLUDED, on `domain` rather than on `category`.
        # A project for building this application has a next_step full of build
        # notes, and feeding those into a RESEARCH interest profile pulls
        # unrelated software-engineering papers up the ranking — the same
        # pollution semantic_memory was excluded for. A project whose CATEGORY
        # is software but whose DOMAIN is a research subject stays: the domain
        # is what says whether a project is about the reader's field.
        "SELECT title || ' ' || COALESCE(domain,'') || ' ' || COALESCE(description,'') "
        "|| ' ' || COALESCE(next_step,'') FROM projects "
        "WHERE status IN ('active','incubating') "
        "AND LOWER(COALESCE(domain,'')) NOT IN ('software','tooling','personal')",
        "SELECT text FROM ideas WHERE COALESCE(tags,'') NOT LIKE '%archived%' "
        "ORDER BY created_at DESC LIMIT 120",
        "SELECT content FROM personal_notes ORDER BY created_at DESC LIMIT 120",
        "SELECT title FROM tasks WHERE status NOT IN ('done','completed','cancelled','deleted') "
        "ORDER BY created_at DESC LIMIT 120",
        "SELECT title FROM meetings ORDER BY meeting_date DESC LIMIT 50",
    ):
        try:
            for (t,) in con.execute(sql):
                if t and str(t).strip():
                    work_texts.append(str(t).strip())
        except Exception:
            pass

    def _dedup(xs):
        seen, out = set(), []
        for t in xs:
            t = t[:300]
            if t and t not in seen:
                seen.add(t); out.append(t)
        return out

    return _dedup(topic_texts), _dedup(work_texts), _dedup(library_texts)


def build_centroid(con: sqlite3.Connection, force: bool = False) -> list[float] | None:
    """Return the cached interest-profile centroid, rebuilding if stale/missing.

    WEIGHTED, because the three bands are not equally informative about what he
    is working on THIS WEEK:

        0.35 · stated topics   what he says his field is
        0.45 · work            projects, ideas, notes, open tasks, meetings
        0.20 · library         what he has collected

    Work carries the most weight because it is the only band that moves. The
    previous version averaged work and library into one bucket, where 400
    library titles outvoted ~16 projects by weight of numbers and the profile
    drifted toward general public health.

    The library is not dropped, only quietened: it is real evidence of his
    interests, just slower-moving and much broader than his current work.

    Returns None if there is nothing to build from, or embeddings are missing.
    """
    if not force:
        try:
            if _CACHE.exists() and (time.time() - _CACHE.stat().st_mtime) < _TTL:
                return json.loads(_CACHE.read_text())["centroid"]
        except Exception:
            pass

    topic_texts, work_texts, library_texts = _corpus_texts(con)
    if not (topic_texts or work_texts or library_texts):
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

        bands = [(0.35, _centroid(topic_texts)),
                 (0.45, _centroid(work_texts)),
                 (0.20, _centroid(library_texts))]
        present = [(w, v) for w, v in bands if v is not None]
        if not present:
            return None
        # Re-normalise the weights over the bands that actually exist, so a
        # missing band shifts emphasis rather than silently shrinking the
        # profile toward the origin.
        total_w = sum(w for w, _ in present)
        blended = sum((w / total_w) * v for w, v in present)
        n = np.linalg.norm(blended)
        centroid = (blended / n).tolist() if n else blended.tolist()
        try:
            _CACHE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE.write_text(json.dumps(
                {"centroid": centroid, "n_topic": len(topic_texts),
                 "n_work": len(work_texts), "n_library": len(library_texts),
                 "built": time.time()}))
        except Exception:
            pass
        return centroid
    except Exception:
        return None


_PROFILE_CACHE = paths.db.parent / "interest_profile.json"


def _corpus_bands(con: sqlite3.Connection) -> list[tuple[str, str]]:
    """Every anchor as (band, text). The band decides what a match is worth.

    WHAT CHANGED AND WHY. `_corpus_texts` returned one flat list of anchors, all
    counting the same, so the profile could not distinguish a paper that matches
    an active project from one that matches a five-year-old task title. Two
    consequences the researcher could see: general public-health writing scored
    like his own subject, and COURSES — the five he is actually studying — were
    never consulted at all, by any band, in any version of this file.

    A course is an unusually good anchor: it is a subject he chose, described in
    his own framing, and it stays stable for months. That it was missing is the
    single biggest omission this rewrite fixes.
    """
    out: list[tuple[str, str]] = []

    def _pull(band: str, sql: str) -> None:
        """Read one band. A FAILURE IS LOGGED, never swallowed in silence.

        The bare `except: pass` that used to stand here is how the stated-focus
        band spent months empty — it read a path that did not exist, raised, and
        the profile simply ranked without it. The same thing happened again the
        first time the course band was written: it selected a `description`
        column `learning_courses` does not have, so the band that was the point
        of the change contributed nothing and said nothing.

        A band is still allowed to fail — an older install has a different
        column set and the profile must survive that. What it is not allowed to
        do is fail quietly.
        """
        try:
            n0 = len(out)
            for row in con.execute(sql):
                t = " ".join(str(x) for x in row if x).strip()
                if t:
                    out.append((band, t))
            if len(out) == n0:
                _log.info("relevance: band %r returned no rows", band)
        except Exception as exc:
            _log.warning("relevance: band %r could not be read (%s) — "
                         "the profile is ranking without it", band, exc)

    # HIS OWN WORK — the two bands that count for their full similarity.
    _pull("project",
          "SELECT title, COALESCE(domain,''), COALESCE(description,''), "
          "       COALESCE(next_step,'') FROM projects "
          "WHERE status IN ('active','incubating') "
          "AND LOWER(COALESCE(domain,'')) NOT IN ('software','tooling','personal')")
    # Courses: only the ones that exist. An 'idea' course is a title with no
    # content behind it, and anchoring on a subject he has not started would
    # rank papers for a course that may never be built.
    # Columns verified against the live schema: `learning_courses` has no
    # `description`. What it does carry is the course's own framing (title,
    # category) and where the reader is in it, and the current/next lesson
    # titles are the most specific sentences about the subject in the row.
    _pull("course",
          "SELECT title, COALESCE(category,''), COALESCE(current_lesson,''), "
          "       COALESCE(next_lesson,'') FROM learning_courses "
          "WHERE status IN ('active','in_progress','building','paused')")

    # STATED TOPICS, each in the band the reader gave it. A topic with no band
    # is an ordinary interest; one marked 'field' or 'method' is weighted
    # accordingly. This is what replaced the hardcoded subject lists.
    try:
        for row in con.execute(
                "SELECT topic, COALESCE(description,'') AS d, "
                "       COALESCE(band,'') AS band FROM user_topics WHERE active = 1"):
            text = " ".join(x for x in (str(row["topic"]), str(row["d"])) if x).strip()
            if not text:
                continue
            band = str(row["band"] or "").strip().lower()
            out.append((band if band in _TOPIC_BANDS else "topic", text))
    except Exception as exc:
        _log.warning("relevance: stated topics could not be read (%s) — "
                     "the profile is ranking without them", exc)
    _pull("idea",
          "SELECT text FROM ideas WHERE COALESCE(tags,'') NOT LIKE '%archived%' "
          "ORDER BY created_at DESC LIMIT 120")
    _pull("idea", "SELECT content FROM personal_notes ORDER BY created_at DESC LIMIT 120")
    _pull("task",
          "SELECT title FROM tasks WHERE status NOT IN ('done','completed','cancelled','deleted') "
          "ORDER BY created_at DESC LIMIT 120")
    _pull("task", "SELECT title FROM meetings ORDER BY meeting_date DESC LIMIT 50")

    # Deduplicate on the text, keeping the HIGHEST-weighted band that produced
    # it. The same sentence can arrive as a project's next step and as a task;
    # keeping the cheaper copy would silently discount his own work.
    best: dict[str, str] = {}
    for band, t in out:
        t = t[:300]
        prev = best.get(t)
        if prev is None or BAND_WEIGHTS.get(band, 0) > BAND_WEIGHTS.get(prev, 0):
            best[t] = band
    return [(b, t) for t, b in best.items()]


def build_profile(con: sqlite3.Connection, force: bool = False) -> dict | None:
    """The interest profile as a CENTROID **and** the individual vectors behind it.

    WHY BOTH. A centroid answers "is this close to the average of everything he
    does". Averaging 5 stated topics, ~100 work items and ~390 library titles
    produces a vector that means "the reader's discipline in general" — and on
    that measure a well-written paper on an unrelated topic in the same
    discipline scored 0.723 while a paper squarely on the reader's own subject
    scored 0.709. A centroid can separate a discipline from obvious noise
    (phenomenology, LED lighting) but not from the enormous middle ground of
    competent writing inside that discipline.

    The question that actually matters is different: **is this close to ANY ONE
    of their projects, ideas or notes?** A paper should be ranked by its
    similarity to the one project it speaks to, not diluted by its distance
    from an unrelated course and 390 library titles.

    So the profile keeps the per-item vectors for the STATED TOPICS and the WORK
    band and scores on the maximum. The centroid survives as a minority term,
    because a general fit is weak evidence and should count for something —
    just not for everything.

    The library band contributes to the centroid only. It is real evidence of
    his interests but far too broad to justify a max-similarity hit.
    """
    if not force:
        try:
            if (_PROFILE_CACHE.exists()
                    and (time.time() - _PROFILE_CACHE.stat().st_mtime) < _TTL):
                return json.loads(_PROFILE_CACHE.read_text())
        except Exception:
            pass

    centroid = build_centroid(con, force=force)
    banded = _corpus_bands(con)
    anchors = [t for _b, t in banded]
    weights = [BAND_WEIGHTS.get(b, 0.80) for b, _t in banded]
    if not anchors:
        return {"centroid": centroid, "anchors": [], "weights": []} if centroid else None
    try:
        from metis_mcp.embeddings import embed
        vectors = embed(anchors, prefix="search_document: ", normalize=True)
        tally: dict = {}
        for b, _t in banded:
            tally[b] = tally.get(b, 0) + 1
        profile = {"centroid": centroid,
                   "anchors": [list(map(float, v)) for v in vectors],
                   # Parallel to `anchors` by index. Stored rather than
                   # recomputed so a cached profile keeps the weights it was
                   # built with — otherwise editing BAND_WEIGHTS would silently
                   # re-rank everything scored before the next rebuild.
                   "weights": weights,
                   "bands": tally,
                   "built": time.time()}
        try:
            _PROFILE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            _PROFILE_CACHE.write_text(json.dumps(profile))
        except Exception:
            pass
        return profile
    except Exception:
        return {"centroid": centroid, "anchors": [], "weights": []} if centroid else None


def score_batch_profile(texts: list[str], profile: dict | None) -> list[float]:
    """0.75 · closest single anchor + 0.25 · centroid fit.

    The weights say what the evidence is worth: a strong match to one real
    project or note is the signal; a general resemblance to the whole corpus is
    a weak prior. With anchors missing this degrades to the centroid alone,
    which is the previous behaviour rather than a failure.
    """
    if not profile or not texts:
        return [0.0] * len(texts)
    centroid = profile.get("centroid")
    anchors = profile.get("anchors") or []
    if not anchors:
        return score_batch(texts, centroid)
    try:
        from metis_mcp.embeddings import embed
        import numpy as np
        v = np.array(embed([t[:500] for t in texts], prefix="search_query: ", normalize=True))
        A = np.array(anchors)
        # WEIGHTED max, not bare max. Scaling each anchor's similarity by its
        # band before taking the maximum is what makes "occasionally
        # epidemiology" expressible: a general methods paper can still win a
        # slot, but it has to beat the researcher's own work by a margin rather
        # than tie with it.
        w = profile.get("weights") or []
        if len(w) == len(anchors):
            best = (v @ A.T * np.array(w)).max(axis=1)
        else:
            # A profile cached before weights existed. Score it the old way
            # rather than guessing weights for anchors whose bands are unknown.
            best = (v @ A.T).max(axis=1)
        if centroid:
            gen = v @ np.array(centroid)
            return [float(0.75 * b + 0.25 * g) for b, g in zip(best, gen)]
        return [float(b) for b in best]
    except Exception:
        return [0.0] * len(texts)


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
