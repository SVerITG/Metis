# Metis RC — WhatsApp Capture via Twilio

Capture ideas directly into Metis by sending a WhatsApp message to a Twilio sandbox number. The message body is stored as a new idea (source: `whatsapp`) and cross-pollinated against the existing RC content.

---

## Prerequisites

1. A [Twilio](https://www.twilio.com) account (free trial is sufficient for development).
2. A Twilio phone number with the **WhatsApp sandbox** (or full WhatsApp sender) enabled.
   - In the Twilio Console go to **Messaging > Try it out > Send a WhatsApp message** to activate the sandbox.
3. The `metis-mcp-server` Python package installed in your environment (which now includes `fastapi`, `uvicorn`, `twilio`, and `python-multipart`).

---

## Environment variables

Set these before starting the webhook server. Add them to your shell profile or a `.env` file:

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_PHONE_NUMBER="whatsapp:+14155238886"   # your Twilio sandbox number
```

| Variable | Where to find it |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Console > Account Info |
| `TWILIO_AUTH_TOKEN` | Twilio Console > Account Info (click to reveal) |
| `TWILIO_PHONE_NUMBER` | Messaging > Senders > WhatsApp Senders |

> **Security note:** `TWILIO_AUTH_TOKEN` is used to validate every incoming request signature. Without it, any caller could inject fake messages. The webhook will warn in its logs if this variable is missing but will not crash.

---

## Running the webhook server

From the repo root (with your virtual environment activated):

```bash
uvicorn metis_mcp.webhook:app --host 0.0.0.0 --port 8000
```

Verify it is running:

```bash
curl http://localhost:8000/webhook/health
# {"status":"ok","signature_validation":true,"twilio_auth_token_set":true}
```

---

## Exposing the server publicly (development)

Twilio must be able to reach your webhook over the public internet. For local development use [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

ngrok prints a forwarding URL such as:

```
Forwarding  https://a1b2-203-0-113-42.ngrok-free.app -> http://localhost:8000
```

Copy the `https://...` URL — you will paste it into the Twilio Console in the next step.

---

## Configuring Twilio to call the webhook

1. Open the [Twilio Console](https://console.twilio.com).
2. Go to **Messaging > Try it out > Send a WhatsApp message** (sandbox) or your production WhatsApp sender configuration.
3. In the **Sandbox Configuration** section, set:
   - **When a message comes in:** `https://<your-ngrok-url>/webhook/whatsapp`
   - Method: `HTTP POST`
4. Click **Save**.

For a production sender (non-sandbox), the same URL goes in the **Inbound Settings** for your WhatsApp-enabled Messaging Service or phone number.

---

## Testing end-to-end

1. On your phone, open WhatsApp and send a message to the Twilio sandbox number (you may need to send the sandbox join code first — follow the on-screen instructions in the Twilio Console).
2. Send any text, e.g.: `Idea: knowledge graphs could model my literature review structure`.
3. You should receive an immediate reply: **"Got it. Idea captured."**
4. Open the Metis Dashboard and navigate to the **Ideas** tab — your message appears as the most recent idea with `source = whatsapp`.

---

## Architecture note

The WhatsApp webhook is intentionally a **separate FastAPI process**, not part of the MCP server. This keeps the MCP stdio transport clean and lets the webhook run as a persistent HTTP service independently.

```
WhatsApp user
    |  (HTTPS POST)
    v
Twilio cloud
    |  (HTTPS POST, signed)
    v
uvicorn metis_mcp.webhook:app   <-- this process
    |
    |-- validate Twilio signature
    |-- capture_idea(content, source="whatsapp")  --> metis.sqlite
    |-- cross_pollinate(content)                  --> logs connections
    |
    v
TwiML XML reply --> Twilio --> WhatsApp user ("Got it. Idea captured.")
```

---

## Production deployment

For permanent availability (no ngrok required), deploy to any Linux host that can run Python:

- **VPS** (Hetzner, DigitalOcean, etc.): run `uvicorn` behind an Nginx reverse proxy with a Let's Encrypt TLS certificate.
- **Cloud function / container**: package the FastAPI app in a Docker image and deploy to Cloud Run, Fly.io, Railway, or similar.
- **Systemd service**: add a `.service` file on the VPS so the webhook restarts automatically on reboot.

In all cases, set the three environment variables (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`) in the deployment environment rather than hardcoding them.
