# Manual test — live meeting + voice capture

Two workflows that cannot be fully automated (require a real microphone) but should be exercised manually before any release. Endpoint health is automated by `tests/functional/run_metis_promises.sh`; only the **audio-touching** steps need a human.

---

## Pre-flight (always run first — automated)

```bash
# Dashboard up
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/
# → 200

# Transcription backend ready
curl -s http://127.0.0.1:8080/api/transcription/status
# → {"available":true,"model":"base","mode":"faster-whisper", ...}

# Cross-pollination ready (no audio needed)
curl -s -X POST -d "text=Disease surveillance field study" http://127.0.0.1:8080/api/meeting/live-connections | head -c 200
# → HTML with "CONNECTIONS SURFACED"
```

If any of the three fail, **do not attempt the manual steps below** — fix the broken endpoint first.

---

## Workflow 1 — Live meeting (Whisper mode)

| # | Step | Verifies | Pass / fail criterion |
|---|---|---|---|
| 1 | Open `http://127.0.0.1:8080/meetings` | Tab loads | Page renders, no console error |
| 2 | Click **Start Live Meeting** | Setup modal renders | Modal shows title field, 4 speaker inputs, language picker, transcription mode picker, **microphone-permission hint card** (you should see "Allow microphone access when your browser asks") |
| 3 | Type a meeting title + 1 speaker name | Form validation | "Start Listening" button becomes the primary CTA |
| 4 | Leave mode as **Whisper — accurate, all browsers** | Backend will run | Hint card says "Transcribes every 8 seconds via the local Whisper model" |
| 5 | Click **Start Listening** | Mic permission prompt fires | Browser asks for microphone access |
| 6 | Click **Allow** | Live session pane appears | Setup modal swaps to the live transcript panel; red **recording dot pulses** (not static) |
| 7 | Speak for ~10 seconds, say something from your research domain | First Whisper chunk uploads | Within 8–12s, transcript text appears in the centre pane |
| 8 | Watch the right pane | Cross-pollination fires | "CONNECTIONS SURFACED" panel populates with links to your library / past meetings |
| 9 | Click **Pause** | Recording halts | Pulse stops, "PAUSED" label appears |
| 10 | Click **Stop and save** | Transcript saved | Toast appears: "Transcript saved to Meetings." Meeting appears in the meetings list. |

### Common failure modes + what they mean

| Symptom | Likely cause | Fix |
|---|---|---|
| No mic prompt | Browser blocks getUserMedia on non-HTTPS / non-localhost | Confirm URL is `127.0.0.1` or `localhost` |
| Mic prompt → "Allow" → no pulse | `lm-pulse` keyframe missing in CSS | `grep "@keyframes lm-pulse" system/app-py/static/styles.css` should return 1 |
| Pulse OK, no transcript after 30s | Whisper backend down | `curl /api/transcription/status` should be `available:true` |
| Transcript appears but no connections | `_cross_pollinate_core` failing silently | Check server log for `[live-meeting]` errors |
| Toast says "I need microphone access" | User denied permission | Browser address bar → mic icon → Allow |

### Browser-mode fallback (Chrome / Edge only)

If Whisper backend is unavailable, the setup mode picker has **Browser — instant, Chrome/Edge only**. Test:

1. Switch the mode picker to Browser
2. Hint card updates to "Transcribes instantly as you speak"
3. Start Listening → words appear in real time (not 8s chunks)
4. Firefox: should show toast "Live transcription needs Chrome or Edge — Firefox doesn't have the browser feature I use"

---

## Workflow 2 — Voice capture (inbox → transcribe → idea)

| # | Step | Verifies | Pass / fail criterion |
|---|---|---|---|
| 1 | Record a 5–10 second voice memo on your phone, save as `.m4a` | Source file ready | File plays back fine on your phone |
| 2 | Sync / copy the `.m4a` into `inbox/` folder | Drop works | `ls inbox/*.m4a` shows the file |
| 3 | From Claude Code (with Metis MCP active), run: `/metis check my inbox` | `scan_inbox` MCP tool fires | Returns text mentioning the audio file |
| 4 | Watch what happens next | Auto-transcription runs | Within 60s: `ls inbox/processed/` shows the file moved; new row in `ideas` table |
| 5 | Open Today tab → Thinking section | Idea visible | New idea card appears with the transcript as content |
| 6 | Check tags on the idea | Routing worked | Tags include "voice-note,inbox,auto-transcribed" |
| 7 | Open the idea | Cross-pollination ran | Connections panel shows related papers/notes |

### What if it doesn't work

| Symptom | Likely cause | Fix |
|---|---|---|
| `scan_inbox` doesn't detect the audio | Extension not in `AUDIO_EXTS` set | Check `system/mcp-server/src/metis_mcp/tools/content_scan.py` — should include `.m4a`, `.mp3`, `.wav`, `.ogg`, `.flac`, `.aac`, `.opus`, `.webm` |
| Detection works, transcription doesn't run | `auto_transcribe_audio=False` was passed | Run `scan_inbox(auto_transcribe_audio=True)` explicitly |
| Transcription runs, file not moved | Permission error on `inbox/processed/` | `mkdir -p inbox/processed && chmod 755 inbox/processed` |
| File moved, no idea created | `ideas` table write failed | Check server log for SQLite errors |

---

## Verification table for the test runner

When you finish each workflow, fill this in and commit it back to git (or paste into your audit notes):

```
Date: __________
Workflow 1 — Live meeting (Whisper mode):
  [ ] Setup modal renders with mic-permission hint
  [ ] Microphone permission prompt fires
  [ ] Recording dot pulses
  [ ] Transcript appears within 12s of speaking
  [ ] Cross-pollination connections surface
  [ ] Pause / Stop / Save flow works
  [ ] Meeting appears in list after save

Workflow 1b — Live meeting (Browser mode, Chrome/Edge):
  [ ] Mode hint updates correctly
  [ ] Words appear instantly as you speak

Workflow 1c — Firefox graceful failure:
  [ ] Toast (not alert) explains Chrome/Edge requirement

Workflow 2 — Voice capture:
  [ ] inbox/<file>.m4a recognised by scan_inbox
  [ ] File auto-transcribed
  [ ] File moved to inbox/processed/
  [ ] Idea row created with voice-note tag
  [ ] Cross-pollination connections surface

Notes / failures:
________________________________________________________________
```

---

## Re-run cadence

- **Before any release** (manual)
- **After every change to `live_meeting.js`, `meetings.py`, `transcription.py`, `content_scan.py`** (manual)
- **Quarterly** for drift detection (manual)

The automated endpoint health checks in `tests/functional/run_metis_promises.sh` cover everything except the audio steps — those need a human in the loop.
