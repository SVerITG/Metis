# Metis in PowerPoint and Excel

A taskpane that searches **your own indexed library** and drops a passage — with its
source — straight into the slide or sheet you're working on. It can also capture an
idea into Metis without leaving the document.

## What it does

- **Search library** — asks Metis the same question you'd ask in chat, over your
  indexed papers and background layers, and returns cited passages. Press
  **Insert into document** and the quote plus its source lands where your cursor is.
- **Capture idea** — saves a thought to Metis. It's vector-indexed like any other
  idea, so it turns up later in cross-pollination.

## What it deliberately does *not* do

It **never reads your document and sends it anywhere.** A deck can hold unpublished
results; an add-in that quietly uploads the active document is exactly what the rest
of Metis is built to prevent. Text only ever moves *into* the document, never out.

## Setting it up (about five minutes, once)

Everything runs on your own computer. Nothing here is exposed to the internet.

### 1. Create the HTTPS certificate

Office add-ins load over HTTPS. A page served over HTTPS **may not call
`http://localhost`** — the browser blocks it as mixed content, silently, with no
error you could act on. So Metis needs to answer over HTTPS too.

```bash
~/.local/share/metis-mcp/.venv/bin/python3 tools/make-localhost-cert.py
```

This is a self-signed certificate. It is **not** a security improvement — the
traffic never leaves your machine. It's a formality the webview demands.

### 2. Start Metis with HTTPS enabled

```bash
METIS_HTTPS=1 bash system/app-py/run.sh
```

It listens on **https://127.0.0.1:8443**, on a separate port, so the normal
dashboard on 8080 keeps working exactly as before.

### 3. Trust the certificate once

Open <https://127.0.0.1:8443> in your browser. It will warn that the certificate
isn't trusted — expected, because you just created it. Accept it once. Until you
do, PowerPoint will fail to load the taskpane with no useful message.

### 4. Sideload the add-in

**PowerPoint / Excel on Windows:**
1. Put `system/office-addin/manifest.xml` in a folder, e.g. `C:\MetisAddin\`.
2. Right-click the folder → **Properties → Sharing → Share** it.
3. In PowerPoint: **File → Options → Trust Center → Trust Center Settings →
   Trusted Add-in Catalogs**. Paste the folder's network path, tick
   **Show in Menu**, press **Add catalog**, then **OK** and restart PowerPoint.
4. **Insert → My Add-ins → Shared Folder → Metis**.

**On macOS:** copy `manifest.xml` into
`~/Library/Containers/com.microsoft.Powerpoint/Data/Documents/wef/` and restart
PowerPoint.

### 5. Connect it

The taskpane asks once for your API token. It's in:

```
system/config/api-token.txt
```

Paste it in. It's stored in the add-in's local storage on this computer and used
only to reach Metis on localhost. The token is **not** baked into the manifest —
the manifest is a shareable file, and a credential inside it would be handed to
anyone who copied it.

## If it doesn't work

| Symptom | Cause |
|---|---|
| Taskpane blank or won't load | Certificate not trusted yet — do step 3 |
| "Metis rejected the token" | Token mismatch; re-copy from `api-token.txt` |
| Search returns nothing | Metis has nothing indexed — check the Library surface |
| Add-in missing from the menu | Catalog folder not shared, or PowerPoint not restarted |

## Status

The **server side is built and verified**: HTTPS, CORS scoped to Office hosts only,
token auth, and search returning real cited passages over the encrypted channel.

The **add-in inside Office has not been run end-to-end** — that needs Windows with
PowerPoint, which the machine it was built on doesn't have. The sideload steps above
are the standard Microsoft procedure, but treat step 4 as untested until you've done
it once.
