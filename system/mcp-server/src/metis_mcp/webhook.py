"""WhatsApp webhook for Metis PKM — receives Twilio messages and captures them as ideas.

Run standalone:
    uvicorn metis_mcp.webhook:app --host 0.0.0.0 --port 8000

Environment variables required:
    TWILIO_ACCOUNT_SID    — your Twilio account SID
    TWILIO_AUTH_TOKEN     — used to validate incoming Twilio signatures
    TWILIO_PHONE_NUMBER   — the Twilio WhatsApp-enabled number (e.g. whatsapp:+14155238886)
"""

import logging
import os
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request, Response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Twilio signature validator
# ---------------------------------------------------------------------------

_TWILIO_AUTH_TOKEN: str | None = os.environ.get("TWILIO_AUTH_TOKEN")

try:
    from twilio.request_validator import RequestValidator as _TwilioValidator

    _validator: _TwilioValidator | None = (
        _TwilioValidator(_TWILIO_AUTH_TOKEN) if _TWILIO_AUTH_TOKEN else None
    )
    if not _TWILIO_AUTH_TOKEN:
        logger.warning(
            "TWILIO_AUTH_TOKEN is not set — Twilio signature validation is DISABLED. "
            "Set this variable before exposing the webhook publicly."
        )
except ImportError:
    _validator = None
    logger.warning(
        "twilio package not installed — signature validation is DISABLED. "
        "Install with: pip install twilio"
    )

# ---------------------------------------------------------------------------
# Lazy import of capture_idea / cross_pollinate
# We import lazily to give a clear error rather than crashing at startup if
# the metis_mcp package is misconfigured, while still keeping the import path
# simple (same Python environment as the MCP server).
# ---------------------------------------------------------------------------

def _get_idea_functions():
    """Return (capture_idea, cross_pollinate) or (None, None) on failure."""
    try:
        # Importing this module registers the tools on the MCP Server object,
        # which is a harmless side-effect when running as a standalone process.
        from metis_mcp.tools.ideas import capture_idea, cross_pollinate  # noqa: PLC0415

        return capture_idea, cross_pollinate
    except Exception as exc:  # pragma: no cover
        logger.error("Could not import idea functions: %s", exc)
        return None, None


# ---------------------------------------------------------------------------
# TwiML helpers
# ---------------------------------------------------------------------------

def _twiml_response(message: str) -> Response:
    """Wrap a plain text message in minimal TwiML and return as XML response."""
    # Escape the handful of characters that matter in XML attribute/text context.
    safe = (
        message
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"  <Message>{safe}</Message>\n"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Metis WhatsApp Webhook",
    description="Receives Twilio WhatsApp messages and stores them as ideas in the Metis PKM.",
    version="0.1.0",
)


@app.get("/webhook/health")
async def health() -> dict:
    """Health check — returns 200 OK with basic status information."""
    return {
        "status": "ok",
        "signature_validation": _validator is not None,
        "twilio_auth_token_set": bool(_TWILIO_AUTH_TOKEN),
    }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: Annotated[str, Form()] = "",
    From: Annotated[str, Form()] = "",
) -> Response:
    """Receive an incoming WhatsApp message from Twilio and capture it as an idea.

    Twilio sends a POST with application/x-www-form-urlencoded form data.
    The two key fields are:
        Body  — the message text sent by the user
        From  — the sender's WhatsApp number (e.g. whatsapp:+32498...)
    """
    # ------------------------------------------------------------------
    # 1. Twilio signature validation
    # ------------------------------------------------------------------
    if _validator is not None:
        signature = request.headers.get("X-Twilio-Signature", "")
        # Build the full URL Twilio signed (scheme + host + path + query)
        url = str(request.url)
        # Twilio signs against the raw POST params as a flat dict
        form_data = dict(await request.form())
        if not _validator.validate(url, form_data, signature):
            logger.warning("Invalid Twilio signature from %s — request rejected.", From)
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    else:
        logger.warning(
            "Twilio signature validation skipped (no validator configured). "
            "From=%s", From
        )

    # ------------------------------------------------------------------
    # 2. Basic input validation
    # ------------------------------------------------------------------
    body = Body.strip()
    if not body:
        logger.info("Empty message body received from %s — ignoring.", From)
        return _twiml_response("Empty message — nothing captured.")

    logger.info("Incoming WhatsApp message from %s: %r", From, body[:120])

    # ------------------------------------------------------------------
    # 3. Capture the idea
    # ------------------------------------------------------------------
    capture_idea, cross_pollinate = _get_idea_functions()

    capture_result: str = ""
    if capture_idea is None:
        logger.error("capture_idea unavailable — idea NOT stored.")
        capture_result = "Error: idea storage unavailable."
    else:
        try:
            results = await capture_idea(content=body, source="whatsapp")
            capture_result = results[0].text if results else "Idea captured."
            logger.info("capture_idea result: %s", capture_result)
        except Exception as exc:
            logger.exception("capture_idea raised an exception: %s", exc)
            capture_result = f"Error capturing idea: {exc}"

    # ------------------------------------------------------------------
    # 4. Cross-pollinate (best-effort — never block the response)
    # ------------------------------------------------------------------
    if cross_pollinate is not None:
        try:
            cp_results = await cross_pollinate(content=body)
            cp_text = cp_results[0].text if cp_results else ""
            if cp_text:
                logger.info("cross_pollinate result: %s", cp_text[:300])
        except Exception as exc:
            logger.warning("cross_pollinate failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # 5. Reply to the sender
    # ------------------------------------------------------------------
    return _twiml_response("Got it. Idea captured.")
