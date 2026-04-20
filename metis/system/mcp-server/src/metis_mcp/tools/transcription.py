"""Meeting transcription tool using Whisper with optional speaker diarization.

Requires:
  - openai-whisper: pip install openai-whisper
  - pyannote.audio (optional, for speaker diarization):
    pip install pyannote.audio
    Needs HF_TOKEN env var: export HF_TOKEN=hf_...
    Accept model terms at: https://hf.co/pyannote/speaker-diarization-3.1

If neither is installed, returns an informative message with install instructions.
"""

import datetime
import json
import os
import tempfile
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.server import app


def _check_whisper():
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _check_pyannote():
    try:
        import pyannote.audio  # noqa: F401
        return True
    except ImportError:
        return False


def _get_recording_row(recording_id: str) -> dict | None:
    """Fetch a meeting row by meeting_id (used as recording_id)."""
    with connect(paths.db) as con:
        row = con.execute(
            """
            SELECT meeting_id, title, stored_audio_path, transcript_path,
                   transcript_status, source_filename
              FROM meetings
             WHERE meeting_id = ?
            """,
            (recording_id,),
        ).fetchone()
    return dict(row) if row else None


def _update_transcript(recording_id: str, transcript_text: str,
                       speaker_labels: dict | None, transcript_path: str) -> None:
    with connect(paths.db) as con:
        con.execute(
            """
            UPDATE meetings
               SET transcript_path = ?,
                   transcript_status = 'complete'
             WHERE meeting_id = ?
            """,
            (transcript_path, recording_id),
        )
        # Store speaker labels as JSON in decisions field if available
        if speaker_labels:
            con.execute(
                "UPDATE meetings SET decisions = ? WHERE meeting_id = ?",
                (json.dumps({"speaker_labels": speaker_labels}), recording_id),
            )
        con.commit()


@app.tool()
async def transcribe_recording(recording_id: str) -> list[TextContent]:
    """Transcribe a meeting recording using Whisper.

    Optionally applies speaker diarization with pyannote.audio if installed
    and HF_TOKEN is set. Saves the transcript alongside the audio file and
    updates the meetings table.

    Args:
        recording_id: The meeting_id from the meetings table (shown in Meetings tab)

    Returns:
        Transcript text (with speaker labels if diarization succeeded) and
        the path where it was saved.
    """
    if not _check_whisper():
        return [TextContent(
            type="text",
            text=(
                "Whisper is not installed.\n\n"
                "Install it with:\n"
                "  pip install openai-whisper\n\n"
                "Then restart the MCP server and try again."
            ),
        )]

    import whisper  # type: ignore

    row = _get_recording_row(recording_id)
    if not row:
        return [TextContent(
            type="text",
            text=f"Recording '{recording_id}' not found in the meetings table.",
        )]

    audio_path = row.get("stored_audio_path") or ""
    if not audio_path or not Path(audio_path).exists():
        return [TextContent(
            type="text",
            text=(
                f"Audio file not found: {audio_path!r}\n"
                "Make sure the recording was saved correctly from the Meetings tab."
            ),
        )]

    # ── Step 1: Whisper transcription ──────────────────────────────────────
    model_size = os.environ.get("METIS_WHISPER_MODEL", "base")
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path, fp16=False)
    whisper_segments = result.get("segments", [])
    raw_text = result.get("text", "").strip()

    # ── Step 2: Speaker diarization (optional) ─────────────────────────────
    speaker_labels: dict | None = None
    final_transcript = raw_text

    if _check_pyannote():
        hf_token = os.environ.get("HF_TOKEN", "")
        if hf_token:
            try:
                from pyannote.audio import Pipeline  # type: ignore

                pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=hf_token,
                )
                diarization = pipeline(audio_path)

                # Align Whisper segments with diarization turns
                speaker_labels = {}
                lines = []
                for segment in whisper_segments:
                    seg_start = segment["start"]
                    seg_end   = segment["end"]
                    seg_text  = segment["text"].strip()

                    # Find which speaker owns the majority of this segment
                    speaker_votes: dict[str, float] = {}
                    for turn, _, speaker in diarization.itertracks(yield_label=True):
                        overlap_start = max(seg_start, turn.start)
                        overlap_end   = min(seg_end,   turn.end)
                        if overlap_end > overlap_start:
                            speaker_votes[speaker] = (
                                speaker_votes.get(speaker, 0.0)
                                + (overlap_end - overlap_start)
                            )

                    assigned = max(speaker_votes, key=speaker_votes.get) if speaker_votes else "?"
                    ts = f"[{seg_start:05.1f}s]"
                    lines.append(f"{ts} {assigned}: {seg_text}")
                    speaker_labels[ts] = {"speaker": assigned, "text": seg_text}

                final_transcript = "\n".join(lines)

            except Exception as exc:
                # Diarization failed — fall back to plain transcript with a note
                final_transcript = (
                    f"[Diarization failed: {exc}]\n\n"
                    f"{raw_text}"
                )
        else:
            final_transcript = (
                "[Speaker diarization skipped — set HF_TOKEN env var to enable]\n\n"
                + raw_text
            )
    # else: pyannote not installed — use plain Whisper output

    # ── Step 3: Save transcript ────────────────────────────────────────────
    audio_dir  = Path(audio_path).parent
    title_slug = row.get("title", recording_id).replace(" ", "_").lower()[:40]
    ts_stamp   = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    transcript_path = str(audio_dir / f"transcript_{title_slug}_{ts_stamp}.txt")

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(f"Meeting: {row.get('title', '')}\n")
        f.write(f"Transcribed: {datetime.datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"Audio: {audio_path}\n")
        f.write(f"Model: whisper-{model_size}")
        if _check_pyannote() and os.environ.get("HF_TOKEN"):
            f.write(" + pyannote diarization")
        f.write("\n\n")
        f.write(final_transcript)

    _update_transcript(recording_id, final_transcript, speaker_labels, transcript_path)

    summary_len = min(500, len(final_transcript))
    return [TextContent(
        type="text",
        text=(
            f"Transcription complete.\n"
            f"Recording: {row.get('title', recording_id)}\n"
            f"Saved to: {transcript_path}\n"
            f"Speakers detected: {'yes (pyannote)' if speaker_labels else 'no (whisper only)'}\n\n"
            f"--- Transcript preview ---\n"
            f"{final_transcript[:summary_len]}"
            + ("\n…" if len(final_transcript) > summary_len else "")
        ),
    )]
