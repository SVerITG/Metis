"""
routers/capture.py — Quick-capture modal and POST handler.
Registered under prefix /api in main.py.
"""

import datetime
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_execute

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
    return "idea", text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/capture-modal", response_class=HTMLResponse)
async def get_capture_modal(request: Request):
    return templates.TemplateResponse(
        "partials/capture_modal.html", {"request": request}
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
            db_execute(
                "INSERT INTO personal_notes (content, created_at) VALUES (?, ?)",
                (clean_text, now),
            )
        else:
            # idea or question both go to ideas table
            idea_type = "question" if item_type == "question" else "idea"
            db_execute(
                "INSERT INTO ideas (title, idea_type, status, created_at) "
                "VALUES (?, ?, 'raw', ?)",
                (clean_text, idea_type, now),
            )

        return HTMLResponse(
            '<div class="alert alert-success py-1 mb-0">'
            "Saved! "
            '<a href="#" onclick="closeCapture(); return false;">Close</a>'
            "</div>"
        )
    except Exception as e:
        return HTMLResponse(
            f'<div class="alert alert-danger py-1 mb-0">Error: {e}</div>'
        )
