"""
routers/transcription.py — Audio transcription for the live meeting assistant.

Three backends (selectable via `backend` parameter on /api/transcription/chunk):
  1. WhisperX  — faster-whisper + pyannote speaker diarization (local GPU).
  2. faster-whisper — plain local transcription, no diarization (local GPU).
  3. Voxtral  — Mistral AI's speech API with native diarization (cloud).
                 Requires MISTRAL_API_KEY. Model: voxtral-mini-latest.

The live meeting JS sends 3.5-second WebM/OGG blobs via POST /api/transcription/chunk.
"""

import asyncio
import base64
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()

_fw_model = None          # faster-whisper WhisperModel
_wx_model = None          # whisperx model (wraps faster-whisper)
_diarize_pipeline = None  # pyannote diarization pipeline
_model_lock = asyncio.Lock()

WHISPER_MODEL    = os.environ.get("WHISPER_MODEL", "base")
HF_TOKEN         = os.environ.get("HF_TOKEN", "")          # needed for pyannote diarization
MISTRAL_API_KEY  = os.environ.get("MISTRAL_API_KEY", "")   # needed for Voxtral
VOXTRAL_MODEL    = os.environ.get("VOXTRAL_MODEL", "voxtral-mini-latest")
USE_WHISPERX     = None   # resolved on first load


def _detect_device():
    """Pick CUDA when available, else CPU."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _compute_type(device: str) -> str:
    """int8 for CPU, float16 for CUDA (faster + fits VRAM)."""
    return "float16" if device == "cuda" else "int8"


def _check_whisperx() -> bool:
    try:
        import whisperx  # noqa
        import shutil
        return shutil.which("ffmpeg") is not None
    except ImportError:
        return False


def _load_whisperx():
    global _wx_model, USE_WHISPERX
    import whisperx
    device = _detect_device()
    _wx_model = whisperx.load_model(
        WHISPER_MODEL,
        device=device,
        compute_type=_compute_type(device),
        download_root=str(Path.home() / ".cache" / "whisper"),
    )
    USE_WHISPERX = True


def _load_faster_whisper():
    global _fw_model, USE_WHISPERX
    from faster_whisper import WhisperModel
    device = _detect_device()
    _fw_model = WhisperModel(
        WHISPER_MODEL,
        device=device,
        compute_type=_compute_type(device),
        download_root=str(Path.home() / ".cache" / "whisper"),
    )
    USE_WHISPERX = False


def _load_diarize_pipeline():
    global _diarize_pipeline
    if not HF_TOKEN:
        return
    try:
        import whisperx
        device = _detect_device()
        _diarize_pipeline = whisperx.DiarizationPipeline(
            use_auth_token=HF_TOKEN, device=device
        )
    except Exception:
        _diarize_pipeline = None


def _ensure_model():
    global USE_WHISPERX
    if USE_WHISPERX is not None:
        return  # already loaded
    if _check_whisperx():
        try:
            _load_whisperx()
            return
        except Exception:
            pass
    # Fallback
    from faster_whisper import WhisperModel  # raises ImportError if missing
    _load_faster_whisper()


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/api/transcription/status")
async def transcription_status():
    wx_available = _check_whisperx()
    try:
        from faster_whisper import WhisperModel  # noqa
        fw_available = True
    except ImportError:
        fw_available = False

    if not fw_available and not wx_available:
        return JSONResponse({"available": False, "note": "faster-whisper not installed."})

    mode = "whisperx" if wx_available else "faster-whisper"
    diarize = bool(HF_TOKEN and wx_available)
    device = _detect_device()
    voxtral_ok = bool(MISTRAL_API_KEY)

    # Check voice-profile recognition availability
    voice_profiles = False
    try:
        from routers.speakers import _get_encoder
        _get_encoder()
        voice_profiles = True
    except Exception:
        pass

    # GPU name for display
    gpu_name = None
    if device == "cuda":
        try:
            import torch
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            gpu_name = "CUDA GPU"

    note_parts = []
    if wx_available and diarize:
        note_parts.append("WhisperX + diarization ready")
    elif wx_available:
        note_parts.append("WhisperX ready (no HF_TOKEN)")
    elif fw_available:
        note_parts.append(
            f"faster-whisper ready ({device.upper()}"
            + (f" · {gpu_name}" if gpu_name else "") + ")"
        )
    if voxtral_ok:
        note_parts.append(f"Voxtral ({VOXTRAL_MODEL}) ready")

    return JSONResponse({
        "available": True,
        "model": WHISPER_MODEL,
        "mode": mode,
        "device": device,
        "gpu": gpu_name,
        "diarization": diarize,
        "voice_profiles": voice_profiles,
        "voxtral": voxtral_ok,
        "voxtral_model": VOXTRAL_MODEL if voxtral_ok else None,
        "note": " · ".join(note_parts) + ".",
    })


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

@router.post("/api/transcription/chunk")
async def transcribe_chunk(
    audio:    UploadFile = File(...),
    language: str = Form(""),
    speaker:  str = Form("Speaker"),
    diarize:  str = Form("false"),
    backend:  str = Form("auto"),
):
    """
    Transcribe a 3.5-second audio chunk from MediaRecorder (WebM/OGG/WAV).

    backend: "auto" (WhisperX → faster-whisper), "voxtral" (Mistral API),
             "whisper" (force local faster-whisper).

    Returns:
      {text, language, segments: [{start, end, text, speaker?}], mode, speaker}
    """
    # ── Voxtral path — no local model needed ──
    if backend == "voxtral":
        if not MISTRAL_API_KEY:
            return JSONResponse(
                {"error": "MISTRAL_API_KEY not set", "text": ""},
                status_code=503,
            )
        ct = audio.content_type or ""
        suffix = ".ogg" if "ogg" in ct else ".mp4" if ("mp4" in ct or "m4a" in ct) else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(await audio.read())
        try:
            lang = language if language else None
            do_diarize = diarize.lower() == "true"
            return await _transcribe_voxtral(tmp_path, lang, speaker, do_diarize)
        except Exception as e:
            return JSONResponse({"error": str(e), "text": ""}, status_code=500)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # ── Local Whisper path ──
    async with _model_lock:
        try:
            _ensure_model()
        except Exception as e:
            return JSONResponse({"error": str(e), "text": ""}, status_code=503)

    # Determine file suffix from content-type
    ct = audio.content_type or ""
    suffix = ".ogg" if "ogg" in ct else ".mp4" if ("mp4" in ct or "m4a" in ct) else ".webm"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(await audio.read())

    try:
        lang = language if language else None
        do_diarize = diarize.lower() == "true" and bool(HF_TOKEN)

        if USE_WHISPERX:
            return await _transcribe_whisperx(tmp_path, lang, speaker, do_diarize)
        else:
            return await _transcribe_faster_whisper(tmp_path, lang, speaker)
    except Exception as e:
        return JSONResponse({"error": str(e), "text": ""}, status_code=500)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def _transcribe_whisperx(tmp_path, lang, speaker, do_diarize):
    import whisperx

    result = _wx_model.transcribe(tmp_path, language=lang, batch_size=8)
    detected_lang = result.get("language", lang or "")

    # Align word timestamps
    try:
        device = _detect_device()
        align_model, metadata = whisperx.load_align_model(
            language_code=detected_lang, device=device
        )
        result = whisperx.align(
            result["segments"], align_model, metadata, tmp_path, device=device
        )
    except Exception:
        pass  # alignment optional

    segments = result.get("segments", [])

    # Diarization
    if do_diarize and _diarize_pipeline is None:
        _load_diarize_pipeline()

    if do_diarize and _diarize_pipeline:
        try:
            diarize_result = _diarize_pipeline(tmp_path)
            result = whisperx.assign_word_speakers(diarize_result, result)
            segments = result.get("segments", [])
        except Exception:
            pass

    seg_list = []
    full_parts = []
    for seg in segments:
        text = seg.get("text", "").strip()
        seg_speaker = seg.get("speaker", speaker)
        seg_list.append({
            "start": round(float(seg.get("start", 0)), 2),
            "end":   round(float(seg.get("end", 0)), 2),
            "text":  text,
            "speaker": seg_speaker,
        })
        full_parts.append(text)

    return JSONResponse({
        "text": " ".join(full_parts),
        "language": detected_lang,
        "segments": seg_list,
        "speaker": speaker,
        "mode": "whisperx",
    })


async def _transcribe_faster_whisper(tmp_path, lang, speaker):
    segments_gen, info = _fw_model.transcribe(
        tmp_path, beam_size=3, language=lang
    )
    seg_list = []
    full_parts = []
    for seg in segments_gen:
        text = seg.text.strip()
        seg_list.append({
            "start":   round(seg.start, 2),
            "end":     round(seg.end, 2),
            "text":    text,
            "speaker": speaker,
        })
        full_parts.append(text)

    # Attempt voice-profile identification on the whole chunk.
    # Falls back silently if resemblyzer is not installed or no profiles exist.
    identified_speaker = speaker
    try:
        from routers.speakers import identify_speaker
        match = identify_speaker(tmp_path)
        if match:
            identified_speaker = match["name"]
            for seg in seg_list:
                seg["speaker"] = identified_speaker
                seg["speaker_confidence"] = match["similarity"]
    except Exception:
        pass

    return JSONResponse({
        "text": " ".join(full_parts),
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "segments": seg_list,
        "speaker": identified_speaker,
        "mode": "faster-whisper",
    })


# ---------------------------------------------------------------------------
# Voxtral (Mistral API) transcription
# ---------------------------------------------------------------------------

async def _transcribe_voxtral(tmp_path, lang, speaker, do_diarize):
    """Call the Mistral Audio Transcriptions API (voxtral-mini-latest)."""
    import httpx

    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()

    # Determine MIME type from extension
    ext = Path(tmp_path).suffix.lower()
    mime_map = {
        ".webm": "audio/webm", ".ogg": "audio/ogg", ".mp4": "audio/mp4",
        ".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    }
    mime = mime_map.get(ext, "audio/webm")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Mistral uses multipart form upload
        files = {"file": (f"chunk{ext}", audio_bytes, mime)}
        data = {
            "model": VOXTRAL_MODEL,
            "response_format": "verbose_json",
        }
        if lang:
            data["language"] = lang
        if do_diarize:
            data["diarize"] = "true"
            data["timestamp_granularities"] = "segment"

        resp = await client.post(
            "https://api.mistral.ai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
            files=files,
            data=data,
        )

    if resp.status_code != 200:
        error_detail = resp.text[:200]
        return JSONResponse(
            {"error": f"Voxtral API error ({resp.status_code}): {error_detail}", "text": ""},
            status_code=502,
        )

    result = resp.json()
    text = result.get("text", "").strip()
    detected_lang = result.get("language", lang or "")

    # Parse segments (Voxtral returns segments with optional speaker labels)
    seg_list = []
    for seg in result.get("segments", []):
        seg_speaker = seg.get("speaker", speaker)
        # Map Voxtral speaker IDs (SPEAKER_0, SPEAKER_1) to configured names
        if seg_speaker and seg_speaker.startswith("SPEAKER_"):
            try:
                idx = int(seg_speaker.split("_")[1])
                # The speaker name will be resolved by the JS using the configured list
                seg_speaker = f"SPEAKER_{idx:02d}"
            except (ValueError, IndexError):
                pass
        seg_list.append({
            "start": round(float(seg.get("start", 0)), 2),
            "end":   round(float(seg.get("end", 0)), 2),
            "text":  seg.get("text", "").strip(),
            "speaker": seg_speaker,
        })

    # If no segments returned, build a single segment from full text
    if not seg_list and text:
        seg_list = [{"start": 0, "end": 0, "text": text, "speaker": speaker}]

    return JSONResponse({
        "text": text,
        "language": detected_lang,
        "segments": seg_list,
        "speaker": speaker,
        "mode": "voxtral",
        "diarized": do_diarize,
    })


# ---------------------------------------------------------------------------
# File upload transcription (standalone — not live meeting)
# ---------------------------------------------------------------------------

@router.post("/api/transcription/file")
async def transcribe_file(
    audio:    UploadFile = File(...),
    language: str = Form(""),
    route_to: str = Form("raw"),
):
    """
    Transcribe an uploaded audio file (mp3, wav, m4a, ogg, webm).

    route_to controls what happens with the result:
      - 'raw'     → just return the text
      - 'idea'    → save as a captured idea
      - 'journal' → save as a journal entry
      - 'note'    → save as a voice note on today's capture
    """
    async with _model_lock:
        try:
            _ensure_model()
        except Exception as e:
            return JSONResponse({"error": str(e), "text": ""}, status_code=503)

    ct = audio.content_type or ""
    suffix = (
        ".mp3" if "mp3" in ct or "mpeg" in ct else
        ".wav" if "wav" in ct else
        ".m4a" if "m4a" in ct else
        ".ogg" if "ogg" in ct else
        ".webm"
    )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(await audio.read())

    try:
        lang = language if language else None
        if USE_WHISPERX:
            result = await _transcribe_whisperx(tmp_path, lang, "Speaker", False)
        else:
            result = await _transcribe_faster_whisper(tmp_path, lang, "Speaker")

        # Extract text from JSONResponse body
        import json as _json
        body = _json.loads(result.body)
        text = body.get("text", "")

        # Route the result
        saved_to = None
        if route_to == "idea" and text.strip():
            try:
                from db import db_execute
                db_execute(
                    "INSERT INTO ideas (content, source, status, created_at) "
                    "VALUES (?, 'voice', 'new', datetime('now'))",
                    (text.strip(),),
                )
                saved_to = "ideas"
            except Exception:
                pass
        elif route_to == "journal" and text.strip():
            try:
                from db import db_execute
                db_execute(
                    "INSERT INTO journal_entries (content, source, created_at) "
                    "VALUES (?, 'voice', datetime('now'))",
                    (text.strip(),),
                )
                saved_to = "journal"
            except Exception:
                pass

        return JSONResponse({
            "text": text,
            "language": body.get("language", ""),
            "mode": body.get("mode", ""),
            "route_to": route_to,
            "saved_to": saved_to,
        })
    except Exception as e:
        return JSONResponse({"error": str(e), "text": ""}, status_code=500)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
