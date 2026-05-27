"""
routers/speakers.py — Speaker voice profile management.

Stores per-person embedding vectors in the `speakers` table.
On enroll: accepts an audio upload, extracts a mean embedding via resemblyzer,
serialises it as a numpy bytes blob, stores it.
On identify: loads all stored embeddings, returns the closest match above a
cosine-similarity threshold (0.75 by default).

resemblyzer produces 256-d GE2E embeddings; cosine distance works well for
speaker verification at this dimensionality.
"""

import datetime
import io
import os
import struct
import tempfile
from pathlib import Path

import numpy as np
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import _connect, db_execute, db_query

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)

SIMILARITY_THRESHOLD = 0.75   # cosine similarity floor for a confirmed match
_encoder = None               # resemblyzer VoiceEncoder — lazy-loaded


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _ensure_table():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS speakers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            embedding    BLOB,
            sample_count INTEGER DEFAULT 1,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


_ensure_table()


def _emb_to_blob(emb: np.ndarray) -> bytes:
    return emb.astype(np.float32).tobytes()


def _blob_to_emb(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Embedding extraction
# ---------------------------------------------------------------------------

def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from resemblyzer import VoiceEncoder
            _encoder = VoiceEncoder(device="cpu")
        except Exception as exc:
            raise RuntimeError(
                f"resemblyzer not available ({exc}). "
                "Install it: python3 -m pip install resemblyzer"
            )
    return _encoder


def extract_embedding(audio_path: str) -> np.ndarray:
    """Return a 256-d speaker embedding for the audio file at audio_path."""
    from resemblyzer import preprocess_wav
    wav = preprocess_wav(Path(audio_path))
    encoder = _get_encoder()
    return encoder.embed_utterance(wav)


# ---------------------------------------------------------------------------
# Identify speaker from an audio path — public helper used by transcription.py
# ---------------------------------------------------------------------------

def identify_speaker(audio_path: str, threshold: float = SIMILARITY_THRESHOLD) -> dict | None:
    """Return {id, name, similarity} for the closest enrolled speaker, or None.

    Returns None when:
    - no speakers are enrolled
    - resemblyzer is not installed
    - best similarity is below threshold
    """
    rows = db_query("SELECT id, name, embedding FROM speakers WHERE embedding IS NOT NULL")
    if not rows:
        return None
    try:
        emb = extract_embedding(audio_path)
    except Exception:
        return None

    best_sim, best_row = -1.0, None
    for r in rows:
        stored = _blob_to_emb(r["embedding"])
        if stored.shape != emb.shape:
            continue
        sim = _cosine(emb, stored)
        if sim > best_sim:
            best_sim, best_row = sim, r

    if best_row is None or best_sim < threshold:
        return None
    return {"id": best_row["id"], "name": best_row["name"], "similarity": round(best_sim, 3)}


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@router.get("/api/speakers", response_class=JSONResponse)
async def list_speakers():
    rows = db_query(
        "SELECT id, name, sample_count, created_at, updated_at FROM speakers ORDER BY name"
    )
    return JSONResponse(rows)


@router.post("/api/speakers/enroll")
async def enroll_speaker(
    audio: UploadFile = File(...),
    name: str = Form(...),
):
    """Upload an audio sample (≥5 s of clean speech) and enroll the speaker."""
    name = name.strip()
    if not name:
        return JSONResponse({"ok": False, "error": "Name is required."}, status_code=400)

    suffix = Path(audio.filename or "sample.wav").suffix.lower() or ".wav"
    raw = await audio.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        emb = extract_embedding(tmp_path)
    except RuntimeError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Could not process audio: {exc}"}, status_code=422)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    now = datetime.datetime.now().isoformat(timespec="seconds")
    blob = _emb_to_blob(emb)

    # If a speaker with this name already exists, update their embedding (average).
    existing = db_query("SELECT id, embedding, sample_count FROM speakers WHERE name = ?", (name,))
    if existing:
        row = existing[0]
        count = (row.get("sample_count") or 1)
        old_emb = _blob_to_emb(row["embedding"])
        # Running mean of embeddings
        new_emb = (old_emb * count + emb) / (count + 1)
        new_blob = _emb_to_blob(new_emb)
        db_execute(
            "UPDATE speakers SET embedding = ?, sample_count = ?, updated_at = ? WHERE id = ?",
            (new_blob, count + 1, now, row["id"]),
        )
        return JSONResponse({"ok": True, "id": row["id"], "name": name, "updated": True, "sample_count": count + 1})
    else:
        conn = _connect()
        cur = conn.execute(
            "INSERT INTO speakers (name, embedding, sample_count, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
            (name, blob, now, now),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return JSONResponse({"ok": True, "id": new_id, "name": name, "updated": False, "sample_count": 1})


@router.delete("/api/speakers/{speaker_id}")
async def delete_speaker(speaker_id: int):
    db_execute("DELETE FROM speakers WHERE id = ?", (speaker_id,))
    return JSONResponse({"ok": True})


@router.post("/api/speakers/identify")
async def identify_speaker_endpoint(
    audio: UploadFile = File(...),
    threshold: float = Form(SIMILARITY_THRESHOLD),
):
    """Identify which enrolled speaker is in an audio clip. Returns JSON."""
    suffix = Path(audio.filename or "chunk.wav").suffix.lower() or ".wav"
    raw = await audio.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        result = identify_speaker(tmp_path, threshold=threshold)
        if result:
            return JSONResponse({"matched": True, **result})
        return JSONResponse({"matched": False})
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# UI partials
# ---------------------------------------------------------------------------

@router.get("/api/partial/speakers", response_class=HTMLResponse)
async def speakers_panel(request: Request):
    rows = db_query(
        "SELECT id, name, sample_count, updated_at FROM speakers ORDER BY name"
    )
    # Check resemblyzer availability
    available = True
    try:
        _get_encoder()
    except Exception:
        available = False

    return templates.TemplateResponse(
        request,
        "partials/speakers_panel.html",
        {"speakers": rows, "available": available},
    )
