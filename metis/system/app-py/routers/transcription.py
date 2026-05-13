"""
routers/transcription.py — Audio transcription for the live meeting assistant.

Two modes (auto-selected at startup):
  1. WhisperX  — faster-whisper transcription + pyannote speaker diarization.
                 Returns per-speaker segments when diarize=true.
                 Requires: whisperx, pyannote.audio, ffmpeg in PATH.
  2. faster-whisper — plain transcription, no diarization.
                 Fallback when whisperx unavailable.

The live meeting JS sends 25-second WebM/OGG blobs via POST /api/transcription/chunk.
"""

import asyncio
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

WHISPER_MODEL  = os.environ.get("WHISPER_MODEL", "base")
HF_TOKEN       = os.environ.get("HF_TOKEN", "")          # needed for pyannote diarization
USE_WHISPERX   = None   # resolved on first load


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
    _wx_model = whisperx.load_model(
        WHISPER_MODEL,
        device="cpu",
        compute_type="int8",
        download_root=str(Path.home() / ".cache" / "whisper"),
    )
    USE_WHISPERX = True


def _load_faster_whisper():
    global _fw_model, USE_WHISPERX
    from faster_whisper import WhisperModel
    _fw_model = WhisperModel(
        WHISPER_MODEL,
        device="cpu",
        compute_type="int8",
        download_root=str(Path.home() / ".cache" / "whisper"),
    )
    USE_WHISPERX = False


def _load_diarize_pipeline():
    global _diarize_pipeline
    if not HF_TOKEN:
        return
    try:
        import whisperx
        _diarize_pipeline = whisperx.DiarizationPipeline(
            use_auth_token=HF_TOKEN, device="cpu"
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
    return JSONResponse({
        "available": True,
        "model": WHISPER_MODEL,
        "mode": mode,
        "diarization": diarize,
        "note": (
            f"WhisperX + diarization ready." if diarize else
            f"WhisperX ready (no HF_TOKEN — diarization disabled)." if wx_available else
            f"faster-whisper ready (plain transcription)."
        ),
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
):
    """
    Transcribe a 25-second audio chunk from MediaRecorder (WebM/OGG/WAV).

    Returns:
      {text, language, segments: [{start, end, text, speaker?}], mode, speaker}
    """
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
        align_model, metadata = whisperx.load_align_model(
            language_code=detected_lang, device="cpu"
        )
        result = whisperx.align(
            result["segments"], align_model, metadata, tmp_path, device="cpu"
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

    return JSONResponse({
        "text": " ".join(full_parts),
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "segments": seg_list,
        "speaker": speaker,
        "mode": "faster-whisper",
    })
