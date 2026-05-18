"""
routers/capture.py — Quick-capture modal and POST handler.
Registered under prefix /api in main.py.
"""

import datetime
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


# ---------------------------------------------------------------------------
# Prefix parser
# ---------------------------------------------------------------------------


def _parse_prefix(text: str) -> tuple[str, str]:
    """Return (item_type, cleaned_text) based on leading prefix."""
    text = text.strip()
    if text.startswith("idea:"):
        return "idea", text.split(":", 1)[1].strip()
    if text.startswith("i:"):
        return "idea", text[2:].strip()
    if text.startswith("note:"):
        return "note", text.split(":", 1)[1].strip()
    if text.startswith("n:"):
        return "note", text[2:].strip()
    if text.startswith("task:"):
        return "task", text.split(":", 1)[1].strip()
    if text.startswith("t:"):
        return "task", text[2:].strip()
    if text.startswith("question:"):
        return "question", text.split(":", 1)[1].strip()
    if text.startswith("q:"):
        return "question", text[2:].strip()
    if text.startswith("journal:"):
        return "journal", text.split(":", 1)[1].strip()
    if text.startswith("j:"):
        return "journal", text[2:].strip()
    return "idea", text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/capture-modal", response_class=HTMLResponse)
async def get_capture_modal(request: Request):
    return templates.TemplateResponse(
     request, "partials/capture_modal.html"
 )


def _surface_connections(text: str) -> str:
    """Return an Archive-styled HTML fragment with cross-pollination matches."""
    try:
        from metis_mcp.tools.ideas import _cross_pollinate_core  # type: ignore
        matches = _cross_pollinate_core(text, max_results=5)
    except Exception:
        return ""
    if not matches:
        return (
            '<div style="margin-top:12px;font-family:var(--m-mono);font-size:10px;'
            'letter-spacing:0.12em;color:var(--m-muted);">'
            "NO CONNECTIONS YET — GROW YOUR LIBRARY TO SEE LINKS</div>"
        )
    source_colors = {
        "library": "var(--m-accent)",
        "meeting": "var(--m-ochre)",
        "news": "var(--m-ok)",
        "idea": "var(--m-muted)",
    }
    rows = "".join(
        '<div style="display:flex;align-items:baseline;gap:8px;padding:5px 0;'
        f'border-bottom:1px solid var(--m-rule-soft);">'
        f'<span style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.12em;'
        f'color:{source_colors.get(m["source"], "var(--m-muted)")};flex-shrink:0;width:48px;">'
        f'{m["source"].upper()}</span>'
        f'<span style="font-family:var(--m-display);font-size:13px;color:var(--m-ink);'
        f'line-height:1.3;">{m["title"][:80]}</span>'
        "</div>"
        for m in matches
    )
    label = f"{len(matches)} CONNECTION{'S' if len(matches) != 1 else ''}"
    return (
        f'<div style="margin-top:14px;border-top:1px solid var(--m-rule-soft);padding-top:10px;">'
        f'<div style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.14em;'
        f'color:var(--m-muted);margin-bottom:6px;">{label} SURFACED</div>'
        f'{rows}</div>'
    )


@router.post("/capture", response_class=HTMLResponse)
async def save_capture(request: Request, text: str = Form(...)):
    item_type, clean_text = _parse_prefix(text)
    now = datetime.datetime.now().isoformat(timespec="seconds")

    try:
        if item_type == "task":
            db_execute(
                "INSERT INTO tasks (title, status, created_at) VALUES (?, 'pending', ?)",
                (clean_text, now),
            )
        elif item_type == "note":
            # Auto-detect project linkage: check if any active project title appears in the text
            note_project_id = ""
            try:
                projects = db_query(
                    "SELECT project_id, title FROM projects WHERE status='active' AND COALESCE(tracked,1)=1"
                ) or []
                text_lower = clean_text.lower()
                for proj in projects:
                    pname = (proj.get("title") or "").lower()
                    if pname and len(pname) > 3 and pname in text_lower:
                        note_project_id = proj["project_id"]
                        break
            except Exception:
                pass
            note_id = uuid.uuid4().hex
            db_execute(
                "INSERT INTO personal_notes (note_id, content, title, tags, created_at, updated_at, project_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (note_id, clean_text, "", "", now, now, note_project_id),
            )
        elif item_type == "journal":
            db_execute(
                "INSERT INTO journal_entries (content, created_at) VALUES (?, ?)",
                (clean_text, now),
            )
        else:
            # idea or question — ideas table uses 'text' as the content column
            idea_type = "question" if item_type == "question" else "idea"
            db_execute(
                "INSERT INTO ideas (text, idea_type, created_at) VALUES (?, ?, ?)",
                (clean_text, idea_type, now),
            )

        # Cross-pollination — auto-surface for ideas and questions
        connections_html = ""
        if item_type in ("idea", "question"):
            connections_html = _surface_connections(clean_text)

        type_labels = {"idea": "IDEA", "question": "QUESTION", "note": "NOTE", "task": "TASK", "journal": "JOURNAL"}
        label = type_labels.get(item_type, item_type.upper())
        return HTMLResponse(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:8px 0;font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;">'
            f'<span style="color:var(--m-ok);">&#10003; SAVED AS {label}</span>'
            f'<a href="#" onclick="closeCapture(); return false;" '
            f'style="color:var(--m-muted);text-decoration:none;">CLOSE</a>'
            f'</div>'
            + connections_html
        )
    except Exception as e:
        return HTMLResponse(
            f'<div style="color:var(--m-alert);font-family:var(--m-mono);font-size:10px;'
            f'padding:8px 0;">ERROR: {e}</div>'
        )


# ---------------------------------------------------------------------------
# Voice transcription — browser records WAV, we transcribe and return text
# ---------------------------------------------------------------------------

_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


@router.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    """Receive browser-recorded audio (WAV), transcribe locally, delete temp file."""
    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        model = _get_whisper()
        segments, _ = model.transcribe(tmp_path, beam_size=5, language="en")
        text = " ".join(s.text.strip() for s in segments).strip()
        return JSONResponse({"ok": True, "text": text})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
