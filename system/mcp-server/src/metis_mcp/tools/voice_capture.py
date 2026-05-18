"""Voice-to-text capture using faster-whisper.

Transcribes an audio file (or a live microphone recording) and routes
the transcript to the appropriate Metis capture function.

Requires:
  pip install faster-whisper

Optional (for live microphone recording):
  pip install sounddevice numpy scipy

If faster-whisper is not installed, returns install instructions.
All processing is local — no audio data leaves your machine.
"""

import datetime
import os
import tempfile
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths


def _check_faster_whisper() -> bool:
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        return True
    except ImportError:
        return False


def _check_sounddevice() -> bool:
    try:
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def _record_microphone(seconds: int, sample_rate: int = 16000) -> str:
    """Record from microphone for `seconds` seconds. Returns path to a temp WAV file."""
    import numpy as np
    import sounddevice as sd
    from scipy.io import wavfile

    recording = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wavfile.write(tmp.name, sample_rate, (recording * 32767).astype(np.int16))
    return tmp.name


def _transcribe_file(audio_path: str, model_size: str) -> str:
    """Transcribe an audio file with faster-whisper. Returns plain text."""
    from faster_whisper import WhisperModel  # type: ignore

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, beam_size=5)
    return " ".join(seg.text.strip() for seg in segments).strip()


@app.tool()
async def transcribe_voice(
    audio_path: str = "",
    route_to: str = "raw",
    record_seconds: int = 0,
    model_size: str = "",
) -> list[TextContent]:
    """Transcribe an audio file or live mic recording and optionally capture the result.

    Uses faster-whisper locally — entirely offline, no API calls, no data leaves
    your machine. Supports MP3, WAV, M4A, OGG, FLAC, and most other audio formats.

    Args:
        audio_path: Path to an audio file to transcribe. Leave empty when using
                    record_seconds for live mic capture.
        route_to:   What to do with the transcript after transcription:
                    - "raw"     → return the transcript text only (default)
                    - "idea"    → capture as an idea with cross-pollination
                    - "journal" → add as a journal entry (mood + energy auto-extracted)
                    - "note"    → append to today's voice-notes markdown file
        record_seconds: Seconds to record from the microphone. Requires sounddevice
                        and numpy. Only used when audio_path is empty.
        model_size: faster-whisper model size. Options: "tiny", "base", "small",
                    "medium", "large-v3". Defaults to METIS_WHISPER_MODEL env var,
                    or "base". Larger models are more accurate but slower to load.

    Returns:
        The transcript text and (if routed) confirmation of where it was saved.

    Examples:
        transcribe_voice(audio_path="/tmp/idea.m4a", route_to="idea")
        transcribe_voice(audio_path="/tmp/reflection.mp3", route_to="journal")
        transcribe_voice(audio_path="", record_seconds=30, route_to="idea")
        transcribe_voice(audio_path="/tmp/note.wav", route_to="note")
    """
    if not _check_faster_whisper():
        return [TextContent(
            type="text",
            text=(
                "faster-whisper is not installed.\n\n"
                "Install it with:\n"
                "  pip install faster-whisper\n\n"
                "Then restart the MCP server and try again.\n\n"
                "faster-whisper runs entirely locally — 4× faster than openai-whisper, "
                "no API calls, no audio data leaves your machine."
            ),
        )]

    resolved_model = model_size or os.environ.get("METIS_WHISPER_MODEL", "base")
    temp_to_delete: str | None = None

    # ── Step 1: Obtain audio ──────────────────────────────────────────────────
    if audio_path:
        if not Path(audio_path).exists():
            return [TextContent(
                type="text",
                text=f"Audio file not found: {audio_path}",
            )]
        source_path = audio_path
        source_label = Path(audio_path).name
    elif record_seconds > 0:
        if not _check_sounddevice():
            return [TextContent(
                type="text",
                text=(
                    "Live microphone recording requires additional packages.\n\n"
                    "Install with:\n"
                    "  pip install sounddevice numpy scipy\n\n"
                    "Then restart the MCP server and try again."
                ),
            )]
        try:
            source_path = _record_microphone(record_seconds)
            temp_to_delete = source_path
            source_label = f"microphone ({record_seconds}s)"
        except Exception as exc:
            return [TextContent(
                type="text",
                text=(
                    f"Microphone recording failed: {exc}\n\n"
                    "On WSL, make sure audio passthrough is enabled (Windows 11 + WSLg). "
                    "Alternatively, record a file on Windows and pass the path via audio_path."
                ),
            )]
    else:
        return [TextContent(
            type="text",
            text=(
                "Provide either:\n"
                "  audio_path — path to an audio file\n"
                "  record_seconds > 0 — seconds to record from the microphone"
            ),
        )]

    # ── Step 2: Transcribe ────────────────────────────────────────────────────
    try:
        transcript = _transcribe_file(source_path, resolved_model)
    except Exception as exc:
        return [TextContent(type="text", text=f"Transcription failed: {exc}")]
    finally:
        if temp_to_delete:
            try:
                Path(temp_to_delete).unlink(missing_ok=True)
            except Exception:
                pass

    if not transcript:
        return [TextContent(
            type="text",
            text=f"Transcription of '{source_label}' returned empty text. Check that the file contains audio.",
        )]

    # ── Step 3: Route ─────────────────────────────────────────────────────────
    if route_to == "raw":
        return [TextContent(
            type="text",
            text=f"Transcript ({source_label}, model={resolved_model}):\n\n{transcript}",
        )]

    elif route_to == "idea":
        from metis_mcp.tools.ideas import capture_idea  # lazy import
        result = await capture_idea(content=transcript, source="voice")
        header = f"Captured as **idea** from '{source_label}' (model={resolved_model}).\n\nTranscript: {transcript}\n\n---\n"
        return [TextContent(type="text", text=header + (result[0].text if result else ""))]

    elif route_to == "journal":
        from metis_mcp.tools.ideas import add_journal_entry  # lazy import
        result = await add_journal_entry(content=transcript)
        header = f"Added to **journal** from '{source_label}' (model={resolved_model}).\n\nTranscript: {transcript}\n\n---\n"
        return [TextContent(type="text", text=header + (result[0].text if result else ""))]

    elif route_to == "note":
        today = datetime.date.today().isoformat()
        ts = datetime.datetime.now().strftime("%H:%M")
        note_dir = paths.root / "journal"
        note_dir.mkdir(parents=True, exist_ok=True)
        note_file = note_dir / f"{today}_voice-notes.md"
        with open(note_file, "a", encoding="utf-8") as f:
            f.write(f"\n## Voice note — {ts}\n\n{transcript}\n")
        return [TextContent(
            type="text",
            text=(
                f"Saved as **note** ({ts}).\n\n"
                f"Transcript: {transcript}\n\n"
                f"File: {note_file}"
            ),
        )]

    else:
        return [TextContent(
            type="text",
            text=(
                f"Unknown route_to value '{route_to}'.\n"
                f"Valid options: raw, idea, journal, note\n\n"
                f"Transcript: {transcript}"
            ),
        )]
