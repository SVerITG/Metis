# Session Handoff — 2026-04-07

Pick up from here on the other computer.

---

## What happened in this session (summary)

### Bugs fixed

**1. `self_improvement.py` — all four self-improvement MCP tools would crash at runtime**

File: `08_system/mcp-server/src/metis_mcp/tools/self_improvement.py`
- `connect()` was called without `db_path` in 7 places → fixed to `connect(paths.db)`
- `paths.pkm_root` doesn't exist as an attribute → fixed to `paths.root`

**2. `check_setup.R` — false folder-name warning**

File: `07_outputs/apps/metis-dashboard/check_setup.R`
- Was checking for `"metis-second-brain"` (old name) → fixed to `"metis"`

**3. `pyproject.toml` — incompatible build backend**

File: `08_system/mcp-server/pyproject.toml`
- `setuptools.backends._legacy:_Backend` not available in isolated build env → changed to `setuptools.build_meta`
- Heavy optional deps (`google-genai`, `fastapi`, `uvicorn`, `twilio`) moved to optional extras `[webhook]` and `[images]` — only needed for WhatsApp webhook (deferred)

### MCP server installed ✅

The MCP server is now installed in a virtual environment at:
```
08_system/mcp-server/.venv/bin/metis-mcp
```

And registered in Claude Code's global settings at `~/.claude/settings.json`.

**You need to restart Claude Code on THIS computer** to load the MCP server.
After restart, `metis-pkm` tools will be available (get_tasks, search_literature, log_agent_run, etc.).

---

## What still needs to be done on the OTHER computer

### Part 1 — Install the MCP server

The venv lives inside the repo (OneDrive-synced), so it is already on the other computer.
But you still need to register it with Claude Code there.

**Step 1 — Edit `~/.claude/settings.json`** on the other computer.
Add the `mcpServers` block (same as this computer):

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/08_system/mcp-server/.venv/bin/metis-mcp",
      "env": {
        "METIS_PKM_ROOT": "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis"
      }
    }
  }
}
```

If the username on the other computer is different, adjust `sverschaeve` in both paths.

**Step 2 — Restart Claude Code** on the other computer.

**Step 3 — Verify in terminal:**
```bash
/mnt/c/Users/sverschaeve/OneDrive\ -\ ITG/Documents/7.\ Software/PKM/metis/08_system/mcp-server/.venv/bin/metis-mcp --help
```
Should print the MCP server help without error.

### Part 2 — Claude Desktop setup (to use Metis from Claude Desktop)

Claude Desktop uses a different config file than Claude Code.

**Step 1 — Find the config file:**
On Windows: `C:\Users\sverschaeve\AppData\Roaming\Claude\claude_desktop_config.json`
(Press Win+R, type `%APPDATA%\Claude`, press Enter)

**Step 2 — Add the MCP server entry:**

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "C:\\Users\\sverschaeve\\OneDrive - ITG\\Documents\\7. Software\\PKM\\metis\\08_system\\mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "metis_mcp.server"],
      "env": {
        "METIS_PKM_ROOT": "C:\\Users\\sverschaeve\\OneDrive - ITG\\Documents\\7. Software\\PKM\\metis"
      }
    }
  }
}
```

**Why different from Claude Code?** Claude Desktop runs on Windows, so paths use backslashes and the Windows Python executable (`.venv\Scripts\python.exe`), not the WSL one.

**Step 3 — Restart Claude Desktop** (quit fully from system tray, reopen).

**Step 4 — Verify:** In Claude Desktop, start a new conversation and ask:
> "Use the metis-pkm tools to show me all open tasks."

If it replies with your actual tasks from the SQLite DB, the connection is working.

### Part 3 — Windows Start menu entry and desktop icon

**Option A — Desktop shortcut (quick)**

1. Right-click the desktop → New → Shortcut
2. Location: `C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\PKM\metis\07_outputs\apps\metis-dashboard\launch_monia.bat`
3. Name it: `Research Cortex`
4. Right-click the shortcut → Properties → Change Icon
5. Browse to: `C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\PKM\Metis_github.png`
   (Note: Windows shortcut icons require `.ico` format — see ICO conversion below)

**Option B — Start menu shortcut (cleaner)**

1. Press Win+R → type `shell:programs` → Enter (opens Start Menu\Programs folder)
2. Create a new shortcut there pointing to `launch_monia.bat`
3. Same icon as above

**Converting the PNG to ICO (one-time):**

Run in PowerShell:
```powershell
# Install ImageMagick if not present (or use an online converter like convertio.co)
# Then:
magick convert "C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\PKM\Metis_github.png" -resize 256x256 "C:\Users\sverschaeve\OneDrive - ITG\Documents\7. Software\PKM\metis_icon.ico"
```

Or just use https://convertio.co/png-ico/ — upload the PNG, download the ICO, save it to the PKM root.

---

## MLM Course workflow — end-to-end walkthrough

This is what to test on the other computer to confirm everything is wired up.

### Context
The MLM Course project exists in the DB (seeded via `seed_projects.R`).
Repo: `SVerITG/MLM_course` on GitHub.

### Step 1 — Open Claude Desktop with Metis connected

Start Claude Desktop. The `metis-pkm` MCP tools should be available.
Confirm by asking: "What are the open tasks for the MLM course project?"

### Step 2 — Work on the project via `/metis`

In Claude Desktop, type:
```
/metis What's the current status of the MLM course project and what should I focus on next?
```

Metis will:
1. Call `get_project_status()` → pulls from SQLite
2. Call `get_tasks(project_id="mlm-course")` → lists tasks
3. Route to the appropriate agent (likely Learning Coach or Software Engineer)
4. Return a prioritised work plan

### Step 3 — Upload meeting notes through the Shiny dashboard

First, make sure the dashboard is running:
- Double-click `launch_monia.bat` in the metis-dashboard folder
- Or double-click the desktop shortcut once created
- Opens at `http://localhost:3838`

To upload a meeting note:
1. Go to the **Meetings** tab
2. Click **Import Meeting**
3. Fill in: title, date, domain (`MLM Course`), project
4. Paste or upload the meeting transcript/notes
5. Click **Save** — stored in `05_sources/meetings/` and logged in SQLite

The Meeting Memory agent then structures it:
```
/meeting-memory structure the MLM course meeting from [date]
```
It will read the raw file, produce a structured note with action items, decisions, and follow-ups, and save it to `07_outputs/reviews/meeting-memory/`.

### Step 4 — Record a meeting (live)

Current state: **Whisper transcription is not yet fully working** (noted in dashboard README).
The infrastructure is in place (`transcribe_meeting.R`, `import_meeting.R`) but the local
Whisper engine install is incomplete.

What works today:
- Record the meeting externally (phone, Teams, any recorder)
- Save the audio file to `05_sources/meetings/audio/`
- In the Meetings tab → Import Meeting → set `transcript_status` to `pending`
- The transcript placeholder is stored; you can paste a manual transcript later

What will work once Whisper is set up:
- Drop audio file into `00_inbox/`
- Dropzone tab picks it up → routes to Meeting Memory
- Whisper transcribes locally → structured note generated automatically

**To finish Whisper setup** (separate task):
```bash
pip3 install openai-whisper
# or the faster version:
pip3 install faster-whisper
```
Then test: `whisper your_audio.mp3 --model base`

---

## "Research Cortex" — reflection on the name

You mentioned you like **Research Cortex**. Here is a fuller reflection, keeping in mind
that English is not your native language and you need to be comfortable using this name.

### What it communicates

**"Cortex"** is the Latin word for "bark" (as in tree bark, the outer layer), and in
neuroscience it refers to the outer layer of the brain — specifically the part responsible
for higher-order thinking: planning, reasoning, language, memory, and decision-making.
This is precise and accurate for what Metis does.

**"Research"** is immediately clear — it anchors the system to its purpose and audience.
No explanation needed.

Together: **Research Cortex** says "this is the thinking layer for your research."

### How it would be perceived

**By academics and researchers:** Immediately understood and positively received.
"Cortex" signals scientific literacy without being jargony — it is a word researchers
encounter constantly in their domain. It would feel natural coming from a researcher.

**By non-technical people:** "Research" is universal. "Cortex" sounds sophisticated but
not intimidating — most people associate it with the brain even if they can't define it.
It signals intelligence without sounding like a product name from a tech company.

**In English specifically:** It is clean, two syllables each, easy to say, memorable.
It does not sound like a startup name ("Cortex.ai") — it sounds like a serious tool.

**Potential confusion:** There is a company called "Cortex" in the DevOps space, and
"Cortex" is also used in some AI products. "Research Cortex" as a compound is distinctive
enough to avoid confusion in your context (academic research / public health).

### Compared to the other candidates

| Name | Strength | Weakness |
|---|---|---|
| **Research Cortex** | Precise, scientific, memorable, dignified | "Cortex" slightly clinical |
| Cognitive OS | Conceptually accurate | "OS" feels technical/product-y |
| Mindframe | Compact and original | Abstract — doesn't signal research |
| Agentic Mind | Descriptive of mechanism | "Agentic" is still jargon to many |
| Living Archive | Poetic | Undersells the active/agent nature |

### Recommendation

Use **Research Cortex** as the name for *your personal instance* of this kind of system —
the thing you would describe to a colleague: "I have a system called Research Cortex that
routes tasks to specialised AI agents."

Keep **Metis** as the name of the routing agent inside it — she is the intelligence at
the centre.

So the framing becomes: "Research Cortex is my second brain. Metis is the agent that runs it."

---

## Remaining known gaps (deferred)

| Item | Priority | Notes |
|---|---|---|
| Security event logging | High | No `security_events` table yet; Cybersecurity + Data Guardian decisions are not persisted |
| `update_threat_intel.R` | High | Cybersecurity has frozen threat patterns; needs daily feed from CISA/URLhaus |
| Whisper transcription | Medium | Infrastructure exists; `faster-whisper` pip install needed |
| Dark theme CSS | Low | Config in `user-config.yaml`; CSS not wired |
| WhatsApp webhook | Low | Deferred; needs separate FastAPI server + Twilio |
| Perplexity MCP | Low | Referenced in token-guardrails; not yet set up |

---

## Quick reference — how to start a session

**On any computer, once MCP is configured:**

1. Open Claude Code terminal in the metis folder:
   ```
   cd "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis"
   ```
2. Run `/metis_status` to see what's open, blocked, or overdue
3. Drop files into `00_inbox/` and run `/metis` to route them
4. All agent outputs go to `07_outputs/reviews/{agent-slug}/`
5. Dashboard at `http://localhost:3838` (launch via `launch_monia.bat`)

---

*Session: 2026-04-07 | Generated by Claude Code (claude-sonnet-4-6)*
